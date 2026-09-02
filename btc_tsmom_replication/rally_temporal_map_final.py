#!/usr/bin/env python3
"""
Micro-auditoría Fase 3.

Únicas correcciones:
1) sample(t) == sample(t+h)  — sin futuros cross-boundary.
2) zonas candidatas congeladas con IS+OOS-1; OOS-2 es validación final.

Mismo dataset (btcusdt_1h.csv), mismos thresholds, grid, STRONG, HAC, FDR 48.
No vol-scaling nuevo, no nuevas ventanas, no re-descarga.
"""

from __future__ import annotations

import math
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

LOOKBACKS = (1, 3, 6, 12, 24, 48, 72, 168)
HORIZONS = (1, 3, 6, 12, 24, 48)
REGIME_H = 720
IS_END = pd.Timestamp("2020-12-31 23:00:00")
OOS1_END = pd.Timestamp("2023-12-31 23:00:00")
OOS2_START = pd.Timestamp("2024-01-01 00:00:00")
SAMPLES = ("IS", "OOS-1", "OOS-2")

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "btcusdt_1h.csv"
OLD_MAP = ROOT / "temporal_map.csv"
OUT_MAP = ROOT / "temporal_map_final.csv"
OUT_EP = ROOT / "episode_robustness_final.csv"
OUT_MD = ROOT / "rally_temporal_summary_final.md"


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
    empty = {"beta": np.nan, "se": np.nan, "t_stat": np.nan, "p_value": np.nan, "r2": np.nan, "N": n}
    if n < 30:
        return empty
    lags = max(1, min(int(maxlags), max(1, n // 4)))
    X = sm.add_constant(x, has_constant="add")
    fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True})
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

    p_pos, p_neg = _m(rf > 0, pos), _m(rf > 0, neg)
    return {
        "P_up_given_past_positive": p_pos,
        "P_up_given_past_negative": p_neg,
        "probability_edge": (p_pos - p_neg) if np.isfinite(p_pos) and np.isfinite(p_neg) else np.nan,
        "mean_future_given_past_positive": _m(rf, pos),
        "mean_future_given_past_negative": _m(rf, neg),
        "median_past": float(np.median(rp)) if rp.size else np.nan,
    }


def same_sample_mask(sample_arr: np.ndarray, h: int) -> np.ndarray:
    n = len(sample_arr)
    out = np.zeros(n, dtype=bool)
    if h <= 0 or h >= n:
        return out
    a, b = sample_arr[:-h], sample_arr[h:]
    out[:-h] = np.isin(a, SAMPLES) & (a == b)
    return out


def connected_zones(survive: dict, sign_map: dict) -> list[dict]:
    k_idx = {k: i for i, k in enumerate(LOOKBACKS)}
    h_idx = {h: i for i, h in enumerate(HORIZONS)}
    remaining = {kh for kh, ok in survive.items() if ok}
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


def episodes_from_mask(ts, mask, sample) -> pd.DataFrame:
    rows, n, samp, i, eid = [], len(mask), sample.to_numpy(), 0, 0
    while i < n:
        if not mask[i] or samp[i] not in SAMPLES:
            i += 1
            continue
        j, cur = i, samp[i]
        while j < n and mask[j] and samp[j] == cur:
            j += 1
        rows.append(
            {"episode_id": eid, "start": ts.iloc[i], "end": ts.iloc[j - 1],
             "duration_h": int(j - i), "sample": cur, "i0": i, "i1": j}
        )
        eid += 1
        i = j
    return pd.DataFrame(rows)


def subsample_24h_index(n_rows, mask, episodes) -> np.ndarray:
    keep = np.zeros(n_rows, dtype=bool)
    if episodes.empty:
        return keep
    for _, ep in episodes.iterrows():
        for t in range(int(ep["i0"]), int(ep["i1"]), 24):
            if mask[t]:
                keep[t] = True
    return keep


def _fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:.{nd}f}"


def _pct(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100 * x:.{nd}f}%"


def matrix_md(df, sample, col, nd=3) -> str:
    sub = df[df["sample"] == sample]
    lines = [
        "| past \\ future | " + " | ".join(f"{h}h" for h in HORIZONS) + " |",
        "| --- |" + "|".join(" ---:" for _ in HORIZONS) + " |",
    ]
    for k in LOOKBACKS:
        vals = []
        for h in HORIZONS:
            hit = sub[(sub["lookback_hours"] == k) & (sub["forward_hours"] == h)]
            if hit.empty or not np.isfinite(hit.iloc[0][col]):
                vals.append("NA")
                continue
            v = hit.iloc[0][col]
            nd_ = 3 if col in ("p_value", "fdr_p_value", "probability_edge") else (2 if col == "t_stat" else nd)
            vals.append(_fmt(v, nd_))
        lines.append("| " + " | ".join([f"{k}h"] + vals) + " |")
    return "\n".join(lines)


def grab(mapdf, sample, k, h):
    m = mapdf[(mapdf["sample"] == sample) & (mapdf["lookback_hours"] == k) & (mapdf["forward_hours"] == h)]
    return None if m.empty else m.iloc[0]


def write_summary(meta, q, mapdf, old, ep, cand_zones, isolated, rob, n_strong, n_drop) -> str:
    def cell(s, k, h):
        return grab(mapdf, s, k, h)

    # compare vs previous map (cross-boundary allowed)
    n_sign_flip = n_big_beta = n_fdr_flip = 0
    n_comp = 0
    if old is not None and len(old):
        for s in SAMPLES:
            for k in LOOKBACKS:
                for h in HORIZONS:
                    a = cell(s, k, h)
                    b = grab(old, s, k, h)
                    if a is None or b is None or not np.isfinite(a["beta"]) or not np.isfinite(b["beta"]):
                        continue
                    n_comp += 1
                    if np.sign(a["beta"]) != np.sign(b["beta"]) and a["beta"] != 0 and b["beta"] != 0:
                        n_sign_flip += 1
                    if abs(a["beta"] - b["beta"]) > 0.05 * max(abs(b["beta"]), 1e-6):
                        n_big_beta += 1
                    fa, fb = a["fdr_p_value"], b["fdr_p_value"]
                    if np.isfinite(fa) and np.isfinite(fb) and (fa < 0.10) != (fb < 0.10):
                        n_fdr_flip += 1

    selected = [z for z in cand_zones if z["n_cells"] >= 2]
    # OOS-2 verdict per selected zone (frozen; no substitution)
    oos2_notes = []
    n_surv, n_fail, n_24 = 0, 0, 0
    for z in selected:
        cell_ok = []
        lines = []
        for k, h in z["cells"]:
            r = cell("OOS-2", k, h)
            if r is None or not np.isfinite(r["beta"]):
                cell_ok.append(False)
                lines.append(f"  {k}h→{h}h: NA")
                continue
            same = np.sign(r["beta"]) == z["sign"]
            cell_ok.append(bool(same))
            e = r["beta"] * r["median_past"] if np.isfinite(r["median_past"]) else np.nan
            lines.append(
                f"  {k}h→{h}h: beta={_fmt(r.beta,4)} t={_fmt(r.t_stat,2)} p={_fmt(r.p_value,3)} "
                f"FDR={_fmt(r.fdr_p_value,3)} R²={_fmt(r.r2,4)} edge={_fmt(r.probability_edge,3)} "
                f"E[fut|+]={_pct(r.mean_future_given_past_positive,3)} "
                f"E[fut|-]={_pct(r.mean_future_given_past_negative,3)} "
                f"econ={_pct(e,3)} signo={'OK' if same else 'FAIL'}"
            )
            # 24h OOS-2
            sub = rob[
                (rob["zone_id"] == z["zone_id"])
                & (rob["lookback_hours"] == k)
                & (rob["forward_hours"] == h)
                & (rob["sample"] == "OOS-2")
                & (rob["spec"] == "subsample_24h")
            ]
            if len(sub):
                b24 = sub.iloc[0]["beta"]
                e24 = sub.iloc[0]["probability_edge"]
                if not np.isfinite(b24):
                    st24 = "NA"
                elif np.sign(b24) != z["sign"]:
                    st24 = "PIERDE SIGNO"
                elif abs(b24) < 0.25 * abs(r["beta"]) if abs(r["beta"]) > 1e-12 else abs(b24) < 1e-4:
                    st24 = "SIGNO OK, beta cerca de 0"
                else:
                    st24 = "CONSERVA SIGNO"
                    n_24 += 1
                edge24 = (
                    "edge misma dirección"
                    if np.isfinite(e24) and np.isfinite(r["probability_edge"])
                    and np.sign(e24) == np.sign(r["probability_edge"])
                    else "edge cambia/NA"
                )
                lines.append(f"    24h OOS-2: beta={_fmt(b24,4)} t={_fmt(sub.iloc[0].t_stat,2)} N={int(sub.iloc[0].N)} {st24}; {edge24}")
        survived = all(cell_ok) and len(cell_ok) == len(z["cells"])
        if survived:
            n_surv += 1
            tag = "SURVIVED FINAL OOS"
        else:
            n_fail += 1
            tag = "FAILED FINAL OOS"
        oos2_notes.append(
            f"- Zona {z['zone_id']} signo={'+' if z['sign']>0 else '-'} n={z['n_cells']} {z['cells']}: **{tag}**\n"
            + "\n".join(lines)
        )

    mom_sel = [z for z in selected if z["sign"] > 0]
    rev_sel = [z for z in selected if z["sign"] < 0]
    mom_surv = n_surv > 0 and any(z["sign"] > 0 for z in selected) and n_fail == 0
    # stricter: any selected momentum zone survived
    mom_any_surv = False
    rev_any_surv = False
    for z in selected:
        ok = True
        for k, h in z["cells"]:
            r = cell("OOS-2", k, h)
            if r is None or not np.isfinite(r["beta"]) or np.sign(r["beta"]) != z["sign"]:
                ok = False
        if ok and z["sign"] > 0:
            mom_any_surv = True
        if ok and z["sign"] < 0:
            rev_any_surv = True

    # 24h: zone survives 24h OOS-2 if majority of its cells keep sign
    def zone_24_oos2(z):
        sub = rob[(rob["zone_id"] == z["zone_id"]) & (rob["sample"] == "OOS-2") & (rob["spec"] == "subsample_24h")]
        if sub.empty:
            return False
        return bool((np.sign(sub["beta"].to_numpy()) == z["sign"]).mean() >= 0.5)

    n_24_zone = sum(1 for z in selected if zone_24_oos2(z))

    if mom_any_surv and n_24_zone >= 1 and any(z["sign"] > 0 and zone_24_oos2(z) for z in selected):
        reco = "A — TEMPORAL STRUCTURE FOUND"
        why = "Zona de continuación congelada en IS+OOS-1 sobrevive OOS-2 y el subsample 24h."
    elif (mom_any_surv or rev_any_surv) and n_24_zone >= 1:
        reco = "B — WEAK TEMPORAL STRUCTURE"
        why = (
            "Una zona congelada conserva signo en OOS-2 y en 24h, pero no es continuación "
            "robusta (reversal y/o magnitud/FDR débiles)."
        )
    elif mom_any_surv or rev_any_surv:
        reco = "B — WEAK TEMPORAL STRUCTURE"
        why = "Signo OOS-2 alineado en una zona congelada, pero el subsample 24h no lo sostiene."
    else:
        reco = "C — NO USEFUL TEMPORAL STRUCTURE"
        why = (
            "Tras vetar futuros cross-boundary y congelar zonas con IS+OOS-1, "
            "ninguna región sobrevive la validación final OOS-2 de forma útil "
            "(signo, 24h y magnitud). No se sustituyeron zonas por otras que lucieran mejor en OOS-2."
        )

    drop_txt = ", ".join(f"{s}: {n_drop.get(s, 0)}" for s in SAMPLES)

    q1 = (
        f"Comparadas {n_comp} celdas con el mapa previo. |Δbeta|>5% relativo en {n_big_beta}/ {n_comp}. "
        f"Obs. STRONG extra excluidas por sample(t)≠sample(t+h): IS={n_drop.get('IS',0)}, "
        f"OOS-1={n_drop.get('OOS-1',0)}, OOS-2={n_drop.get('OOS-2',0)} "
        "(0 = no había régimen STRONG en el borde temporal de cada sample)."
    )
    q2 = f"Cambios de signo vs mapa previo: {n_sign_flip} / {n_comp}."
    q3 = f"Celdas que cruzan FDR 0.10 vs mapa previo: {n_fdr_flip} / {n_comp}."
    q4 = (
        "Zonas conexas (≥2 celdas) con el mismo signo IS y OOS-1 (congeladas, sin OOS-2):\n"
        + ("\n".join(f"- id={z['zone_id']} signo={'+' if z['sign']>0 else '-'} {z['cells']}" for z in selected)
           if selected else "- ninguna región conexa")
        + "\nCeldas aisladas IS+OOS-1 (no seleccionadas): "
        + str([z["cells"][0] for z in isolated])
    )
    q5 = "\n".join(oos2_notes) if oos2_notes else "No había zona conexa que validar en OOS-2."
    q6 = (
        f"{n_24_zone} zona(s) conservan signo OOS-2 en el subsample 24h."
        if selected
        else "No aplica: no hubo zona congelada."
    )
    q7 = "Sí." if mom_any_surv else "No. No hay zona de continuación congelada que sobreviva OOS-2."
    q8 = "Sí, como hipótesis débil." if rev_any_surv else "No de forma útil (falla OOS-2 y/o 24h)."
    q9 = (
        "La corrección de post-selection impide promover el bloque k=48–168h de OOS-2, "
        "que no era candidato en IS+OOS-1. Eso era el riesgo de la fase anterior."
    )
    q10 = f"Decisión: {reco}."

    return f"""# Micro-auditoría Fase 3 — validación OOS estricta

Dataset: `{DATA_FILE.name}` (sin redescarga). Thresholds, grid, STRONG, HAC y FDR 48 **sin cambios**.
Correcciones: (1) `sample(t)==sample(t+h)`; (2) zonas congeladas con **IS+OOS-1**; OOS-2 no selecciona.

---

## Datos (idénticos)

- {meta['start']} → {meta['end']} UTC · N={meta['n']} · missing={meta['n_missing']} · dup={meta['n_dup']}
- p75 IS R720 = {_pct(q['p75'])} · p90 = {_pct(q['p90'])}
- STRONG horas: IS={n_strong['IS']}, OOS-1={n_strong['OOS-1']}, OOS-2={n_strong['OOS-2']}
- Filas extra excluidas por frontera t+h (suma sobre 8×6; una fila puede contar en varios h): {drop_txt}

Episodios STRONG (igual definición):

| sample | n | dur media | mediana | max |
|---|---:|---:|---:|---:|
{chr(10).join(
    (
        f"| {s} | {len(sub)} | {sub['duration_h'].mean():.1f} | "
        f"{sub['duration_h'].median():.0f} | {int(sub['duration_h'].max())} |"
        if len(sub)
        else f"| {s} | 0 | NA | NA | NA |"
    )
    for s in SAMPLES
    for sub in [ep[ep["sample"] == s] if not ep.empty else ep.iloc[0:0]]
)}

---

## Matrices OOS-2 (solo evaluación; no se usaron para elegir zonas)

### beta
{matrix_md(mapdf, 'OOS-2', 'beta')}

### t-stat
{matrix_md(mapdf, 'OOS-2', 't_stat')}

### FDR
{matrix_md(mapdf, 'OOS-2', 'fdr_p_value')}

### probability edge
{matrix_md(mapdf, 'OOS-2', 'probability_edge')}

## Matrices IS (discovery)

### beta
{matrix_md(mapdf, 'IS', 'beta')}

### t-stat
{matrix_md(mapdf, 'IS', 't_stat')}

### FDR
{matrix_md(mapdf, 'IS', 'fdr_p_value')}

## Matrices OOS-1 (discovery / freeze)

### beta
{matrix_md(mapdf, 'OOS-1', 'beta')}

### t-stat
{matrix_md(mapdf, 'OOS-1', 't_stat')}

### FDR
{matrix_md(mapdf, 'OOS-1', 'fdr_p_value')}

---

## Zonas congeladas (IS + OOS-1 only)

Selección: mismo signo de beta en IS y OOS-1; regiones 4-conectadas; **solo n≥2 celdas**.
Celdas aisladas no se promocionan. OOS-2 no entra aquí.

{q4}

---

## Validación OOS-2 (sin re-seleccionar)

{q5}

---

## Preguntas

1. ¿Cambian materialmente los coeficientes después de eliminar cross-boundary observations?
**{q1}**

2. ¿Cambian los signos?
**{q2}**

3. ¿Cambian las conclusiones FDR?
**{q3}**

4. ¿Qué zonas se seleccionan usando exclusivamente IS+OOS-1?
**Ver bloque de zonas congeladas arriba.**

5. ¿Cuáles sobreviven OOS-2?
**{n_surv} sobreviven, {n_fail} FAILED FINAL OOS. No se sustituyó ninguna.**

6. ¿Alguna zona sobrevive también al subsample 24h?
**{q6}**

7. ¿Existe momentum estable?
**{q7}**

8. ¿Existe reversal estable?
**{q8}**

9. ¿El resultado anterior era afectado materialmente por post-selection?
**{q9}**

10. ¿Se mantiene o cambia la decisión final?
**{q10}**

---

## Decisión

# {reco}

{why}
"""


def run() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Usar el snapshot {DATA_FILE} — no redescargar.")
    raw = pd.read_csv(DATA_FILE)
    px = pd.DataFrame(
        {
            "ts": pd.to_datetime(raw["timestamp_utc"]),
            "close": pd.to_numeric(raw["close"], errors="coerce"),
        }
    )
    px = px.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    ts = px["ts"]
    meta = {
        "start": ts.min().strftime("%Y-%m-%d %H:%M"),
        "end": ts.max().strftime("%Y-%m-%d %H:%M"),
        "n": int(len(px)),
        "n_missing": int(len(pd.date_range(ts.min(), ts.max(), freq="h").difference(ts))),
        "n_dup": int(px["ts"].duplicated().sum()),
        "n_nan": int(px["close"].isna().sum()),
    }

    df = px.set_index("ts").sort_index().asfreq("h")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["r720"] = df["close"] / df["close"].shift(REGIME_H) - 1.0
    for k in LOOKBACKS:
        df[f"rp_{k}"] = df["close"] / df["close"].shift(k) - 1.0
    for h in HORIZONS:
        df[f"rf_{h}"] = df["close"].shift(-h) / df["close"] - 1.0
    panel = df.reset_index()
    panel["sample"] = sample_of(panel["ts"])
    samp = panel["sample"].to_numpy()

    is_r = panel.loc[(panel["sample"] == "IS") & panel["r720"].notna(), "r720"].to_numpy(float)
    p75, p90 = np.percentile(is_r, [75, 90])
    q = {"p75": float(p75), "p90": float(p90)}
    panel["strong"] = ((panel["r720"] > p75) & (panel["r720"] <= p90)).fillna(False)
    n_strong = {s: int(((panel["sample"] == s) & panel["strong"]).sum()) for s in SAMPLES}
    mask_arr = panel["strong"].to_numpy(bool)
    ep = episodes_from_mask(panel["ts"], mask_arr, panel["sample"])
    keep24 = subsample_24h_index(len(panel), mask_arr, ep)

    same_h = {h: same_sample_mask(samp, h) for h in HORIZONS}

    rows = []
    n_drop = {s: 0 for s in SAMPLES}
    for sample in SAMPLES:
        base = ((panel["sample"] == sample) & panel["strong"]).to_numpy()
        for k in LOOKBACKS:
            rp = panel[f"rp_{k}"].to_numpy(float)
            for h in HORIZONS:
                rf = panel[f"rf_{h}"].to_numpy(float)
                finite = np.isfinite(rp) & np.isfinite(rf)
                m_old = base & finite
                m = m_old & same_h[h]
                n_drop[sample] += int(m_old.sum() - m.sum())
                reg = hac_ols(rf[m], rp[m], maxlags=h)
                st = dir_stats(rp[m], rf[m])
                rows.append({"sample": sample, "lookback_hours": k, "forward_hours": h, **reg, "fdr_p_value": np.nan, **st})
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
        "sample", "lookback_hours", "forward_hours", "beta", "se", "t_stat", "p_value",
        "fdr_p_value", "r2", "N", "P_up_given_past_positive", "P_up_given_past_negative",
        "probability_edge", "mean_future_given_past_positive", "mean_future_given_past_negative",
    ]
    mapdf[cols].to_csv(OUT_MAP, index=False)

    # --- freeze candidates on IS + OOS-1 only (no OOS-2) ---
    cand = {}
    signs = {}
    for k in LOOKBACKS:
        for h in HORIZONS:
            isr = grab(mapdf, "IS", k, h)
            o1 = grab(mapdf, "OOS-1", k, h)
            if isr is None or o1 is None or not np.isfinite(isr["beta"]) or not np.isfinite(o1["beta"]):
                cand[(k, h)] = False
                signs[(k, h)] = 0
                continue
            s0, s1 = np.sign(isr["beta"]), np.sign(o1["beta"])
            ok = s0 != 0 and s0 == s1
            cand[(k, h)] = bool(ok)
            signs[(k, h)] = int(s0) if ok else 0
    all_zones = connected_zones(cand, signs)
    selected = [z for z in all_zones if z["n_cells"] >= 2]
    isolated = [z for z in all_zones if z["n_cells"] == 1]
    # reindex zone_id on selected only so robustness rows map cleanly
    for i, z in enumerate(selected):
        z["zone_id"] = i

    rob_rows = []
    for z in selected:
        for k, h in z["cells"]:
            rp = panel[f"rp_{k}"].to_numpy(float)
            rf = panel[f"rf_{h}"].to_numpy(float)
            same = same_h[h]
            for sample in SAMPLES:
                smask = (panel["sample"] == sample).to_numpy() & mask_arr & same
                m24 = smask & keep24 & np.isfinite(rp) & np.isfinite(rf)
                reg24 = hac_ols(rf[m24], rp[m24], maxlags=h)
                st24 = dir_stats(rp[m24], rf[m24])
                r_oos2 = grab(mapdf, "OOS-2", k, h)
                oos2_ok = (
                    r_oos2 is not None
                    and np.isfinite(r_oos2["beta"])
                    and np.sign(r_oos2["beta"]) == z["sign"]
                )
                b24 = reg24["beta"]
                if sample != "OOS-2":
                    art = ""
                elif not np.isfinite(b24):
                    art = "NA"
                elif np.sign(b24) != z["sign"]:
                    art = "PIERDE SIGNO"
                elif np.isfinite(r_oos2["beta"]) and abs(r_oos2["beta"]) > 1e-12 and abs(b24) < 0.25 * abs(r_oos2["beta"]):
                    art = "SIGNO OK, beta cerca de 0"
                else:
                    art = "CONSERVA SIGNO"
                rob_rows.append(
                    {
                        "zone_id": z["zone_id"],
                        "zone_sign": z["sign"],
                        "lookback_hours": k,
                        "forward_hours": h,
                        "sample": sample,
                        "spec": "subsample_24h",
                        **reg24,
                        "probability_edge": st24["probability_edge"],
                        "mean_future_given_past_positive": st24["mean_future_given_past_positive"],
                        "mean_future_given_past_negative": st24["mean_future_given_past_negative"],
                        "econ_beta_x_median_past": (
                            reg24["beta"] * st24["median_past"]
                            if np.isfinite(reg24["beta"]) and np.isfinite(st24["median_past"])
                            else np.nan
                        ),
                        "oos2_cell_status": "SURVIVED FINAL OOS" if oos2_ok else "FAILED FINAL OOS",
                        "subsample_24h_status": art,
                    }
                )
    rob = pd.DataFrame(rob_rows)
    rob.to_csv(OUT_EP, index=False)

    old = pd.read_csv(OLD_MAP) if OLD_MAP.exists() else None
    OUT_MD.write_text(
        write_summary(meta, q, mapdf, old, ep, selected, isolated, rob, n_strong, n_drop),
        encoding="utf-8",
    )
    print("Wrote", OUT_MAP)
    print("Wrote", OUT_EP)
    print("Wrote", OUT_MD)
    print("thresholds", q)
    print("n_drop_boundary", n_drop)
    print("selected_zones", selected)
    print("isolated", [z["cells"] for z in isolated])


if __name__ == "__main__":
    run()
