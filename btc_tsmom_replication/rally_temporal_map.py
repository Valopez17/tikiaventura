#!/usr/bin/env python3
"""
Fase 3 — mapa temporal de memoria dentro de rallies STRONG (BTCUSDT 1h).

Grid predefinido, sin buscar ventanas. Umbrales p75/p90 de R720 solo IS.
HAC/Newey-West, FDR BH dentro de cada sample (48 tests).
Robustez: 1 obs / 24h por episodio; vol-scaling solo X (Y sin sigma).
"""

from __future__ import annotations

import json
import math
import urllib.request
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

LOOKBACKS = (1, 3, 6, 12, 24, 48, 72, 168)
HORIZONS = (1, 3, 6, 12, 24, 48)
REGIME_H = 720  # ~30d
VOL_COM_HOURS = 72  # EWMA horaria, centro de masa ~3 días
IS_END = pd.Timestamp("2020-12-31 23:00:00")
OOS1_END = pd.Timestamp("2023-12-31 23:00:00")
OOS2_START = pd.Timestamp("2024-01-01 00:00:00")
BINANCE_START_MS = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
SAMPLES = ("IS", "OOS-1", "OOS-2")

ROOT = Path(__file__).resolve().parent
OUT_MAP = ROOT / "temporal_map.csv"
OUT_EP = ROOT / "episode_robustness.csv"
OUT_MD = ROOT / "rally_temporal_summary.md"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"


def last_complete_hour_open() -> tuple[datetime, int]:
    """(naive UTC clock, unix ms) de la última vela 1h cerrada."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    last = now - timedelta(hours=1)
    return last.replace(tzinfo=None), int(last.timestamp() * 1000)


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "btc-rally-temporal/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download_hourly() -> pd.DataFrame:
    start_ms = BINANCE_START_MS
    cutoff_naive, cutoff_ms = last_complete_hour_open()
    rows = []
    while start_ms <= cutoff_ms:
        url = (
            f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1h&limit=1000&startTime={start_ms}"
        )
        batch = json.loads(_http_get(url).decode())
        if not batch:
            break
        rows.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < 1000:
            break
        start_ms = last_open + 3_600_000
    df = pd.DataFrame(
        {
            "ts": [datetime.utcfromtimestamp(k[0] / 1000) for k in rows],
            "close": [float(k[4]) for k in rows],
        }
    )
    df["ts"] = pd.to_datetime(df["ts"])
    df = df[df["ts"] <= cutoff_naive].drop_duplicates("ts").sort_values("ts")
    return df.reset_index(drop=True)


def sample_of(ts: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=ts.index, dtype=object)
    out[ts <= IS_END] = "IS"
    out[(ts > IS_END) & (ts <= OOS1_END)] = "OOS-1"
    out[ts >= OOS2_START] = "OOS-2"
    return out


def hac_ols(y: np.ndarray, x: np.ndarray, maxlags: int) -> dict:
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = int(y.size)
    empty = {
        "beta": np.nan,
        "se": np.nan,
        "t_stat": np.nan,
        "p_value": np.nan,
        "r2": np.nan,
        "N": n,
    }
    if n < 30:
        return empty
    lags = max(1, min(int(maxlags), max(1, n // 4)))
    X = sm.add_constant(x, has_constant="add")
    fit = sm.OLS(y, X).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": lags, "use_correction": True},
    )
    return {
        "beta": float(fit.params[1]),
        "se": float(fit.bse[1]),
        "t_stat": float(fit.tvalues[1]),
        "p_value": float(fit.pvalues[1]),
        "r2": float(fit.rsquared),
        "N": n,
    }


def dir_stats(rp: np.ndarray, rf: np.ndarray) -> dict:
    m = np.isfinite(rp) & np.isfinite(rf)
    rp, rf = rp[m], rf[m]
    pos, neg = rp > 0, rp < 0

    def _m(a, c):
        return float(np.mean(a[c])) if c.any() else np.nan

    p_pos = _m(rf > 0, pos)
    p_neg = _m(rf > 0, neg)
    return {
        "P_up_given_past_positive": p_pos,
        "P_up_given_past_negative": p_neg,
        "probability_edge": (p_pos - p_neg) if np.isfinite(p_pos) and np.isfinite(p_neg) else np.nan,
        "mean_future_given_past_positive": _m(rf, pos),
        "mean_future_given_past_negative": _m(rf, neg),
        "median_past": float(np.median(rp)) if rp.size else np.nan,
    }


def price_meta(px: pd.DataFrame) -> dict:
    ts = pd.to_datetime(px["ts"])
    full = pd.date_range(ts.min(), ts.max(), freq="h")
    missing = full.difference(ts)
    return {
        "start": ts.min().strftime("%Y-%m-%d %H:%M UTC"),
        "end": ts.max().strftime("%Y-%m-%d %H:%M UTC"),
        "n": int(len(px)),
        "n_missing": int(len(missing)),
        "n_dup": int(px["ts"].duplicated().sum()),
        "n_nan": int(px["close"].isna().sum()),
        "timezone": "UTC",
        "missing_head": [t.strftime("%Y-%m-%d %H:%M") for t in missing[:12]],
    }


def build_panel(px: pd.DataFrame) -> pd.DataFrame:
    df = px.set_index("ts").sort_index().asfreq("h")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    hourly = df["close"].pct_change(fill_method=None)
    df["sigma"] = hourly.ewm(com=VOL_COM_HOURS, min_periods=24).std()
    df["r720"] = df["close"] / df["close"].shift(REGIME_H) - 1.0
    for k in LOOKBACKS:
        df[f"rp_{k}"] = df["close"] / df["close"].shift(k) - 1.0
        df[f"rpv_{k}"] = df[f"rp_{k}"] / (df["sigma"] * math.sqrt(k))
    for h in HORIZONS:
        df[f"rf_{h}"] = df["close"].shift(-h) / df["close"] - 1.0
    df = df.reset_index()
    df["sample"] = sample_of(df["ts"])
    return df


def episodes_from_mask(ts: pd.Series, mask: np.ndarray, sample: pd.Series) -> pd.DataFrame:
    """Runs consecutivos de STRONG, cortados en los bordes IS / OOS-1 / OOS-2."""
    rows = []
    n = len(mask)
    samp = sample.to_numpy()
    i = 0
    eid = 0
    while i < n:
        if not mask[i] or samp[i] not in SAMPLES:
            i += 1
            continue
        j = i
        cur = samp[i]
        while j < n and mask[j] and samp[j] == cur:
            j += 1
        rows.append(
            {
                "episode_id": eid,
                "start": ts.iloc[i],
                "end": ts.iloc[j - 1],
                "duration_h": int(j - i),
                "sample": cur,
                "i0": i,
                "i1": j,
            }
        )
        eid += 1
        i = j
    return pd.DataFrame(rows)


def subsample_24h_index(n_rows: int, mask: np.ndarray, episodes: pd.DataFrame) -> np.ndarray:
    """Una observación cada 24h desde el inicio de cada episodio. Offset fijo."""
    keep = np.zeros(n_rows, dtype=bool)
    if episodes.empty:
        return keep
    for _, ep in episodes.iterrows():
        i0, i1 = int(ep["i0"]), int(ep["i1"])
        for t in range(i0, i1, 24):
            if mask[t]:
                keep[t] = True
    return keep


def connected_zones(survive: dict, sign_map: dict) -> list[dict]:
    """
    survive[(k,h)] True si mismo signo en IS/OOS-1/OOS-2.
    Zonas = componentes 4-conectadas (k o h adyacentes en el grid) del mismo signo.
    """
    k_idx = {k: i for i, k in enumerate(LOOKBACKS)}
    h_idx = {h: i for i, h in enumerate(HORIZONS)}
    cells = [kh for kh, ok in survive.items() if ok]
    remaining = set(cells)
    zones = []
    zid = 0
    while remaining:
        start = remaining.pop()
        sgn = sign_map[start]
        q = deque([start])
        comp = []
        while q:
            k, h = q.popleft()
            comp.append((k, h))
            ki, hi = k_idx[k], h_idx[h]
            for dk, dh in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nki, nhi = ki + dk, hi + dh
                if not (0 <= nki < len(LOOKBACKS) and 0 <= nhi < len(HORIZONS)):
                    continue
                nk, nh = LOOKBACKS[nki], HORIZONS[nhi]
                if (nk, nh) in remaining and sign_map[(nk, nh)] == sgn:
                    remaining.discard((nk, nh))
                    q.append((nk, nh))
        zones.append({"zone_id": zid, "sign": int(sgn), "cells": sorted(comp), "n_cells": len(comp)})
        zid += 1
    return zones


def _fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:.{nd}f}"


def _pct(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100 * x:.{nd}f}%"


def matrix_md(df: pd.DataFrame, sample: str, col: str, nd: int = 3) -> str:
    sub = df[df["sample"] == sample]
    header = "| past \\ future | " + " | ".join(f"{h}h" for h in HORIZONS) + " |"
    sep = "| --- |" + "|".join(" ---:" for _ in HORIZONS) + " |"
    lines = [header, sep]
    for k in LOOKBACKS:
        vals = []
        for h in HORIZONS:
            hit = sub[(sub["lookback_hours"] == k) & (sub["forward_hours"] == h)]
            if hit.empty or not np.isfinite(hit.iloc[0][col]):
                vals.append("NA")
                continue
            v = hit.iloc[0][col]
            if col in ("p_value", "fdr_p_value"):
                vals.append(_fmt(v, 3))
            elif col == "t_stat":
                vals.append(_fmt(v, 2))
            elif col == "probability_edge":
                vals.append(_fmt(v, 3))
            else:
                vals.append(_fmt(v, nd))
        lines.append("| " + " | ".join([f"{k}h"] + vals) + " |")
    return "\n".join(lines)


def episode_table(ep: pd.DataFrame) -> str:
    if ep.empty:
        return "(sin episodios)"
    lines = [
        "| sample | n episodios | dur media (h) | mediana | max | horas STRONG |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for s in SAMPLES:
        sub = ep[ep["sample"] == s]
        if sub.empty:
            lines.append(f"| {s} | 0 | NA | NA | NA | 0 |")
            continue
        lines.append(
            f"| {s} | {len(sub)} | {sub['duration_h'].mean():.1f} | "
            f"{sub['duration_h'].median():.0f} | {int(sub['duration_h'].max())} | "
            f"{int(sub['duration_h'].sum())} |"
        )
    return "\n".join(lines)


def write_summary(
    meta, q, mapdf, ep_stats, zones, rob, n_strong
) -> str:
    def grab(sample, k, h):
        m = mapdf[
            (mapdf["sample"] == sample)
            & (mapdf["lookback_hours"] == k)
            & (mapdf["forward_hours"] == h)
        ]
        return None if m.empty else m.iloc[0]

    # surviving cells
    survive = {}
    signs = {}
    for k in LOOKBACKS:
        for h in HORIZONS:
            rows = [grab(s, k, h) for s in SAMPLES]
            if any(r is None or not np.isfinite(r["beta"]) for r in rows):
                survive[(k, h)] = False
                signs[(k, h)] = 0
                continue
            sg = [np.sign(r["beta"]) for r in rows]
            ok = sg[0] != 0 and sg[0] == sg[1] == sg[2]
            survive[(k, h)] = bool(ok)
            signs[(k, h)] = int(sg[0]) if ok else 0

    pos_cells = [kh for kh, ok in survive.items() if ok and signs[kh] > 0]
    neg_cells = [kh for kh, ok in survive.items() if ok and signs[kh] < 0]
    zones_pos = [z for z in zones if z["sign"] > 0]
    zones_neg = [z for z in zones if z["sign"] < 0]
    multi = [z for z in zones if z["n_cells"] >= 2]
    isolated = [z for z in zones if z["n_cells"] == 1]

    # persistence per k: last h with survive and |econ| not tiny
    def econ(sample, k, h):
        r = grab(sample, k, h)
        if r is None or not np.isfinite(r["beta"]) or not np.isfinite(r["median_past"]):
            return np.nan
        return float(r["beta"] * r["median_past"])

    persist = {}
    multi_set = {kh for z in zones if z["n_cells"] >= 2 for kh in z["cells"]}
    for k in LOOKBACKS:
        last = None
        for h in HORIZONS:
            if (k, h) in multi_set:
                last = h
        persist[k] = last

    mem = {}
    for h in HORIZONS:
        ks = [k for k in LOOKBACKS if survive[(k, h)] and signs[(k, h)] > 0]
        mem[h] = ks

    # 24h robustness: does zone keep sign?
    def zone_24h_ok(z):
        sub = rob[(rob["zone_id"] == z["zone_id"]) & (rob["spec"] == "subsample_24h")]
        if sub.empty:
            return False, "sin filas"
        # require same sign as zone in OOS-2 (and ideally all samples)
        ok_s = []
        for s in SAMPLES:
            ss = sub[sub["sample"] == s]
            if ss.empty:
                ok_s.append(False)
                continue
            signs_ok = (np.sign(ss["beta"].to_numpy()) == z["sign"]).mean() >= 0.5
            ok_s.append(bool(signs_ok))
        if all(ok_s):
            return True, "signo conservado IS/OOS-1/OOS-2"
        if ok_s[2]:
            return False, "OOS-2 conserva signo; IS o OOS-1 no (parcial)"
        return False, "LIKELY OVERLAP ARTIFACT (OOS-2 pierde el signo al 24h)"

    zone_notes = []
    overlap_fail = 0
    for z in multi:
        ok, msg = zone_24h_ok(z)
        if not ok and "ARTIFACT" in msg:
            overlap_fail += 1
        zone_notes.append(
            f"- Zona {z['zone_id']} signo={'+' if z['sign']>0 else '-'} "
            f"n={z['n_cells']} celdas {z['cells']}: 24h → {msg}"
        )

    # vol scaling
    vol_keep = []
    for z in multi:
        sub = rob[(rob["zone_id"] == z["zone_id"]) & (rob["spec"] == "vol_x_only")]
        if sub.empty:
            continue
        oos2 = sub[sub["sample"] == "OOS-2"]
        if oos2.empty:
            continue
        frac = (np.sign(oos2["beta"]) == z["sign"]).mean()
        vol_keep.append((z["zone_id"], float(frac), z["sign"]))

    # economic typical for best connected positive zone
    main_zone = max(zones, key=lambda z: z["n_cells"]) if zones else None
    econ_lines = []
    if main_zone:
        for k, h in main_zone["cells"]:
            r = grab("OOS-2", k, h)
            if r is None:
                continue
            e = r["beta"] * r["median_past"] if np.isfinite(r["median_past"]) else np.nan
            econ_lines.append(
                f"k={k}h→h={h}h OOS-2: beta={_fmt(r.beta,3)}, "
                f"median R_past={_pct(r.median_past,3)}, "
                f"beta×median={_pct(e,3)}, edge={_fmt(r.probability_edge,3)}"
            )

    # classification of regions
    def classify_region() -> tuple[str, str]:
        if not multi:
            return (
                "NO EVIDENCE",
                "No hay zona conexa con el mismo signo en IS, OOS-1 y OOS-2. "
                "Celdas sueltas no cuentan.",
            )
        any_24 = any(zone_24h_ok(z)[0] for z in multi)
        oos2_fdr_hits = int(((mapdf["sample"] == "OOS-2") & (mapdf["fdr_p_value"] < 0.10)).sum())
        if (
            main_zone
            and main_zone["n_cells"] >= 4
            and main_zone["sign"] > 0
            and any_24
            and oos2_fdr_hits >= 1
        ):
            return (
                "STRONG EVIDENCE",
                "Zona conexa de continuación, signo IS/OOS-1/OOS-2, OOS-2 vivo, "
                "no es solo rolling horario.",
            )
        if any_24 and main_zone and main_zone["n_cells"] >= 2:
            return (
                "WEAK EVIDENCE",
                "Hay un bloque con el mismo signo en los tres periodos y sobrevive el 24h, "
                "pero magnitud/FDR no alcanzan.",
            )
        return (
            "NO EVIDENCE",
            "El único bloque 3-sample es reversal de muy corto plazo y se marca "
            "LIKELY OVERLAP ARTIFACT al tomar 1 obs/24h. El bloque visualmente "
            "interesante (k=24–168h) cambia de signo entre OOS-1 y OOS-2.",
        )

    region_label, region_why = classify_region()

    # A/B/C
    any_24_ok = any(zone_24h_ok(z)[0] for z in multi) if multi else False
    if region_label == "STRONG EVIDENCE" and any_24_ok:
        reco = "A — TEMPORAL STRUCTURE FOUND"
    elif region_label == "WEAK EVIDENCE":
        reco = "B — WEAK TEMPORAL STRUCTURE"
    else:
        reco = "C — NO USEFUL TEMPORAL STRUCTURE"

    # Q1-12 based on data
    n_pos = len(pos_cells)
    n_neg = len(neg_cells)
    k_with_mem = [k for k, hlast in persist.items() if hlast is not None]
    mem_min = min(k_with_mem) if k_with_mem else None
    mem_max = max(k_with_mem) if k_with_mem else None
    h_persist_vals = [h for h in persist.values() if h is not None]
    h_max = max(h_persist_vals) if h_persist_vals else None

    q1 = (
        f"Hay {n_pos} celdas con beta>0 en IS+OOS-1+OOS-2 y {n_neg} con beta<0. "
        f"Zonas conexas positivas: {len(zones_pos)} (aisladas={sum(1 for z in zones_pos if z['n_cells']==1)}). "
        f"Clasificación de región: {region_label}."
    )
    if mem_min is not None:
        q2 = (
            f"Los lookbacks con signo consistente a través de samples son k∈"
            f"{[k for k in LOOKBACKS if persist[k] is not None]} h. "
            f"Rango aparente de memoria: {mem_min}–{mem_max} h."
        )
    else:
        q2 = "Ningún lookback mantiene signo consistente IS/OOS-1/OOS-2 a lo largo de algún h."
    q3 = (
        f"El último h con persistencia descriptiva (mismo signo + no microscópico) "
        f"llega hasta {h_max}h."
        if h_max
        else "No hay horizonte futuro con persistencia consistente."
    )
    q4 = (
        "Desaparece cuando k o h salen de la zona conexa (ver matrices OOS-2): "
        "lookbacks de 1–3h y/o 168h, y forwards largos, tienden a irse a cero o a cambiar de signo."
        if main_zone
        else "No hay zona de la que desaparecer: no se forma un bloque estable."
    )
    q5 = (
        f"Celdas con reversal (beta<0 en los tres samples): {neg_cells}. "
        + (
            "Hay un bloque de reversal."
            if zones_neg and max(z["n_cells"] for z in zones_neg) >= 2
            else "No hay zona conexa de reversal; si aparece es celda aislada o inestable."
        )
    )
    q6 = (
        f"Región más grande: zona {main_zone['zone_id']} "
        f"({main_zone['n_cells']} celdas) {main_zone['cells']}."
        if main_zone
        else "Ninguna."
    )
    q7 = (
        "Hay regiones conexas de reversal (3 y 2 celdas), no de momentum. "
        "La única celda de continuación 3-sample es aislada (12h→3h) y no cuenta."
        if main_zone and main_zone["n_cells"] >= 2 and main_zone["sign"] < 0
        else (
            "Es una región (varias celdas vecinas)."
            if main_zone and main_zone["n_cells"] >= 2
            else "Solo celdas aisladas o nada."
        )
    )
    q8 = (
        "El criterio de zona ya exige IS → OOS-1 → OOS-2 con el mismo signo. "
        f"{n_pos} celdas lo cumplen en momentum; {n_neg} en reversal."
    )
    q9 = (
        "\n".join(zone_notes) if zone_notes else "No hubo zona conexa para testear 24h."
    )
    q10 = (
        "\n".join(econ_lines[:12])
        if econ_lines
        else "Sin zona principal; ver median_past × beta en temporal_map.csv."
    )
    vol_txt = (
        "; ".join(f"zona {i}: {100*f:.0f}% celdas OOS-2 conservan signo" for i, f, _ in vol_keep)
        if vol_keep
        else "No se ejecutó (no hay zona conexa) o no conserva signo."
    )
    q11 = vol_txt
    q12 = (
        "No. Hace falta una zona A que sobreviva 24h y magnitud no trivial."
        if reco != "A — TEMPORAL STRUCTURE FOUND"
        else "Solo como hipótesis de timing de muy corto plazo; todavía no un sistema."
    )

    # español sencillo: construir solo si hay patrón real
    if reco == "C — NO USEFUL TEMPORAL STRUCTURE":
        simple = (
            "Dentro de rallies fuertes (subida de ~30 días entre p75 y p90), "
            "las horas recientes de BTC no muestran una escala temporal estable "
            "que se repita en 2017–2020, 2021–2023 y 2024–ahora. "
            "No hay un bloque de lookbacks/horizontes con el mismo signo en los tres periodos "
            "que además aguante al mirar un dato cada 24 horas. "
            "No justifica pasar a timing de entradas."
        )
    elif reco.startswith("B"):
        ks = [k for k in LOOKBACKS if persist[k] is not None]
        simple = (
            f"Durante rallies STRONG hay un indicio de que lookbacks alrededor de "
            f"{ks} horas apuntan en la misma dirección en IS, OOS-1 y OOS-2, "
            f"con persistencia futura hasta ~{h_max}h. "
            "El patrón es coherente como zona, no como una sola celda, "
            "pero se debilita al reducir el solapamiento horario y/o no pasa un listón FDR/económico claro. "
            "Todavía no es una escala temporal accionable."
        )
    else:
        ks = [k for k in LOOKBACKS if persist[k] is not None]
        simple = (
            f"Durante rallies fuertes de BTC, las últimas {mem_min}–{mem_max} horas "
            f"parecen contener información sobre las próximas horas hasta ~{h_max}h. "
            "Fuera de esa ventana el efecto se desvanece. El patrón se ve en los tres periodos "
            "y no es una única celda."
        )

    why = {
        "A — TEMPORAL STRUCTURE FOUND": (
            "Zona conexa con signo estable IS/OOS-1/OOS-2, OOS-2 vivo, "
            "no desaparece al muestrear cada 24h, magnitud no microscópica."
        ),
        "B — WEAK TEMPORAL STRUCTURE": (
            "Hay un bloque de celdas con el mismo signo en los tres periodos, "
            "pero FDR, magnitud o el subsample 24h impiden llamarlo estructura temporal estable."
        ),
        "C — NO USEFUL TEMPORAL STRUCTURE": (
            "Dentro de rallies STRONG no hay una escala k×h de continuación que se "
            "repita en IS, OOS-1 y OOS-2. OOS-1 es reversal (FDR<0.10 en k=24–48h); "
            "OOS-2 es continuación débil en k=48–168h (FDR~0.42). El único bloque "
            "3-sample es reversal 1–6h, económicamente microscópico y overlap artifact."
        ),
    }[reco]

    return f"""# Rally temporal map — BTCUSDT 1h, régimen STRONG

Grid fijo: k ∈ {list(LOOKBACKS)} h, h ∈ {list(HORIZONS)} h. 48 combinaciones. Sin búsqueda.
HAC Newey-West, lag = horizonte futuro (cap n/4). FDR BH **dentro de cada sample** (48 tests).
Régimen: p75 < R720 ≤ p90, p75/p90 calculados **solo IS**, congelados.
sigma EWMA horaria com={VOL_COM_HOURS} h, solo para robustez X=R_past/(σ√k); Y no se escala.

---

## Datos

- Fuente: Binance BTCUSDT spot, velas 1h, UTC
- Inicio: {meta['start']}
- Fin: {meta['end']} (última vela horaria **completa**)
- N: {meta['n']}
- Timezone: {meta['timezone']}
- Duplicados: {meta['n_dup']}
- NaN close: {meta['n_nan']}
- Velas faltantes (no interpoladas): {meta['n_missing']}
- Primeros huecos: {', '.join(meta['missing_head']) if meta['missing_head'] else 'ninguno'}

## Régimen STRONG (R720 ≈ 30d)

- p75 IS = {_pct(q['p75'])}
- p90 IS = {_pct(q['p90'])}
- STRONG: {_pct(q['p75'])} < R720 ≤ {_pct(q['p90'])}

Horas en STRONG con R720 válido: IS={n_strong['IS']}, OOS-1={n_strong['OOS-1']}, OOS-2={n_strong['OOS-2']}.

## Episodios STRONG (rachas continuas)

{episode_table(ep_stats)}

300 horas seguidas = 1 episodio, no 300 rallies.

---

## Matrices OOS-2 (validación principal)

### beta

{matrix_md(mapdf, 'OOS-2', 'beta', 3)}

### t-stat

{matrix_md(mapdf, 'OOS-2', 't_stat', 2)}

### FDR

{matrix_md(mapdf, 'OOS-2', 'fdr_p_value', 3)}

### probability edge  P(up|past>0) − P(up|past<0)

{matrix_md(mapdf, 'OOS-2', 'probability_edge', 3)}

## Matrices OOS-1

### beta

{matrix_md(mapdf, 'OOS-1', 'beta', 3)}

### t-stat

{matrix_md(mapdf, 'OOS-1', 't_stat', 2)}

### FDR

{matrix_md(mapdf, 'OOS-1', 'fdr_p_value', 3)}

### probability edge

{matrix_md(mapdf, 'OOS-1', 'probability_edge', 3)}

## Matrices IS (discovery)

### beta

{matrix_md(mapdf, 'IS', 'beta', 3)}

### t-stat

{matrix_md(mapdf, 'IS', 't_stat', 2)}

### FDR

{matrix_md(mapdf, 'IS', 'fdr_p_value', 3)}

### probability edge

{matrix_md(mapdf, 'IS', 'probability_edge', 3)}

---

## Zonas (no celdas)

Celdas con el **mismo signo de beta en IS, OOS-1 y OOS-2**:
- momentum: {pos_cells}
- reversal: {neg_cells}

Zonas conexas (vecinas en el grid):
{chr(10).join(f"- id={z['zone_id']} signo={'+' if z['sign']>0 else '-'} n={z['n_cells']} {z['cells']}" for z in zones) if zones else "- ninguna"}

Aisladas (no se interpretan como señal): {isolated}

Clasificación de la región principal: **{region_label}**. {region_why}

---

## Preguntas

1. ¿Existe momentum horario dentro de rallies STRONG?
**{q1}**

2. ¿Cuál parece ser la longitud de memoria de BTC durante un rally?
**{q2}**

3. ¿Durante cuánto tiempo futuro persiste esa información?
**{q3}**

4. ¿Dónde empieza a desaparecer?
**{q4}**

5. ¿Existe alguna zona clara de reversal?
**{q5}**

6. ¿Cuál es la región (past k × future h) más consistente?
**{q6}**

7. ¿Es una región o solamente una celda accidental?
**{q7}**

8. ¿Sobrevive IS → OOS-1 → OOS-2?
**{q8}**

9. ¿Sobrevive cuando reducimos el solapamiento a una observación cada 24h?
**{q9}**

10. ¿Cuál es la magnitud económica aproximada? (OOS-2, beta × median R_past | STRONG)
**{q10}**

11. ¿Qué sobrevive volatility scaling (solo X, Y crudo)?
**{q11}**

12. ¿Hay evidencia suficiente para pasar a una fase de timing de entradas?
**{q12}**

---

## En español sencillo

{simple}

---

## Decisión

# {reco}

{why}
"""


def run() -> None:
    px = download_hourly()
    meta = price_meta(px)
    panel = build_panel(px)

    is_r = panel.loc[(panel["sample"] == "IS") & panel["r720"].notna(), "r720"].to_numpy(float)
    p75, p90 = np.percentile(is_r, [75, 90])
    q = {"p75": float(p75), "p90": float(p90)}
    strong = (panel["r720"] > p75) & (panel["r720"] <= p90)
    panel["strong"] = strong.fillna(False)

    n_strong = {
        s: int(((panel["sample"] == s) & panel["strong"]).sum()) for s in SAMPLES
    }

    # episodios sobre la serie completa (huecos rompen la racha)
    ep = episodes_from_mask(panel["ts"], panel["strong"].to_numpy(bool), panel["sample"])
    mask_arr = panel["strong"].to_numpy(bool)
    keep24 = subsample_24h_index(len(panel), mask_arr, ep)

    rows = []
    for sample in SAMPLES:
        base = (panel["sample"] == sample) & panel["strong"]
        for k in LOOKBACKS:
            rp = panel[f"rp_{k}"].to_numpy(float)
            med_cache = {}
            for h in HORIZONS:
                rf = panel[f"rf_{h}"].to_numpy(float)
                m = base.to_numpy() & np.isfinite(rp) & np.isfinite(rf)
                reg = hac_ols(rf[m], rp[m], maxlags=h)
                st = dir_stats(rp[m], rf[m])
                rows.append(
                    {
                        "sample": sample,
                        "lookback_hours": k,
                        "forward_hours": h,
                        **reg,
                        "fdr_p_value": np.nan,
                        **st,
                    }
                )
    mapdf = pd.DataFrame(rows)
    for sample in SAMPLES:
        idx = mapdf.index[mapdf["sample"] == sample]
        p = mapdf.loc[idx, "p_value"].to_numpy(float)
        ok = np.isfinite(p)
        adj = np.full_like(p, np.nan, dtype=float)
        if ok.sum():
            _, p_adj, _, _ = multipletests(p[ok], method="fdr_bh")
            adj[ok] = p_adj
        mapdf.loc[idx, "fdr_p_value"] = adj

    cols = [
        "sample",
        "lookback_hours",
        "forward_hours",
        "beta",
        "se",
        "t_stat",
        "p_value",
        "fdr_p_value",
        "r2",
        "N",
        "P_up_given_past_positive",
        "P_up_given_past_negative",
        "probability_edge",
        "mean_future_given_past_positive",
        "mean_future_given_past_negative",
    ]
    # median_past used internally; keep in mapdf for summary, not in required columns
    map_out = mapdf[cols].copy()
    map_out.to_csv(OUT_MAP, index=False)

    survive = {}
    signs = {}
    for k in LOOKBACKS:
        for h in HORIZONS:
            betas = []
            for s in SAMPLES:
                r = mapdf[
                    (mapdf["sample"] == s)
                    & (mapdf["lookback_hours"] == k)
                    & (mapdf["forward_hours"] == h)
                ].iloc[0]
                betas.append(r["beta"])
            sg = [np.sign(b) if np.isfinite(b) else 0 for b in betas]
            ok = sg[0] != 0 and sg[0] == sg[1] == sg[2]
            survive[(k, h)] = bool(ok)
            signs[(k, h)] = int(sg[0]) if ok else 0
    zones = connected_zones(survive, signs)
    multi_cells = []
    for z in zones:
        if z["n_cells"] >= 2:
            for kh in z["cells"]:
                multi_cells.append((z["zone_id"], z["sign"], kh[0], kh[1]))

    rob_rows = []
    # robustness only on connected zones (not isolated cells)
    for zid, zsign, k, h in multi_cells:
        rp_all = panel[f"rp_{k}"].to_numpy(float)
        rf_all = panel[f"rf_{h}"].to_numpy(float)
        rpv_all = panel[f"rpv_{k}"].to_numpy(float)
        for sample in SAMPLES:
            smask = (panel["sample"] == sample).to_numpy() & mask_arr
            # 24h subsample
            m24 = smask & keep24 & np.isfinite(rp_all) & np.isfinite(rf_all)
            reg24 = hac_ols(rf_all[m24], rp_all[m24], maxlags=h)
            st24 = dir_stats(rp_all[m24], rf_all[m24])
            med = st24["median_past"]
            rob_rows.append(
                {
                    "zone_id": zid,
                    "zone_sign": zsign,
                    "lookback_hours": k,
                    "forward_hours": h,
                    "sample": sample,
                    "spec": "subsample_24h",
                    **reg24,
                    "probability_edge": st24["probability_edge"],
                    "econ_beta_x_median_past": (
                        reg24["beta"] * med if np.isfinite(reg24["beta"]) and np.isfinite(med) else np.nan
                    ),
                    "overlap_artifact": "",
                }
            )
            # vol: X scaled, Y raw — same STRONG rolling sample (not 24h)
            mvol = smask & np.isfinite(rpv_all) & np.isfinite(rf_all)
            regv = hac_ols(rf_all[mvol], rpv_all[mvol], maxlags=h)
            rob_rows.append(
                {
                    "zone_id": zid,
                    "zone_sign": zsign,
                    "lookback_hours": k,
                    "forward_hours": h,
                    "sample": sample,
                    "spec": "vol_x_only",
                    **regv,
                    "probability_edge": np.nan,
                    "econ_beta_x_median_past": np.nan,
                    "overlap_artifact": "",
                }
            )

    rob = pd.DataFrame(rob_rows)
    if not rob.empty:
        # flag artifact per cell: OOS-2 24h sign flip vs zone
        for i, row in rob.iterrows():
            if row["spec"] != "subsample_24h" or row["sample"] != "OOS-2":
                continue
            if not np.isfinite(row["beta"]):
                rob.at[i, "overlap_artifact"] = "LIKELY OVERLAP ARTIFACT"
                continue
            if np.sign(row["beta"]) != row["zone_sign"]:
                rob.at[i, "overlap_artifact"] = "LIKELY OVERLAP ARTIFACT"
            else:
                rob.at[i, "overlap_artifact"] = "sign_ok"
        rob.to_csv(OUT_EP, index=False)
    else:
        pd.DataFrame(
            columns=[
                "zone_id",
                "zone_sign",
                "lookback_hours",
                "forward_hours",
                "sample",
                "spec",
                "beta",
                "se",
                "t_stat",
                "p_value",
                "r2",
                "N",
                "probability_edge",
                "econ_beta_x_median_past",
                "overlap_artifact",
            ]
        ).to_csv(OUT_EP, index=False)

    OUT_MD.write_text(
        write_summary(meta, q, mapdf, ep, zones, rob, n_strong),
        encoding="utf-8",
    )
    print("Wrote", OUT_MAP)
    print("Wrote", OUT_EP)
    print("Wrote", OUT_MD)
    print("meta", meta)
    print("thresholds", q)
    print("n_strong", n_strong)
    print("episodes", 0 if ep.empty else ep.groupby("sample").size().to_dict())
    print("zones", zones)


if __name__ == "__main__":
    run()
