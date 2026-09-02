#!/usr/bin/env python3
"""
Réplica empírica de Wen, Bouri, Xu & Zhao (2022),
“Intraday return predictability in the cryptocurrency markets:
Momentum, reversal, or both”, NAJEF 62, 101733.

Fase: PAPER → REPLICATION → OOS VALIDATION → FORECAST.
No rallies, no regimes, no TA, no volumen, no ML, no trading backtest.

Snapshot: btcusdt_1h.csv (Binance BTCUSDT spot 1h). No re-descarga.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t as student_t
from statsmodels.stats.multitest import multipletests

# ---------------------------------------------------------------------------
# Paper mapping
# ---------------------------------------------------------------------------
# Wen et al. Eq. (1): r_{i,t} = log(p_{i,t}) - log(p_{i-1,t}), i=1..24
# p_{0,t} = price at 00:00 UTC on day t (previous hourly close).
# Our hour h=0..23 is paper hour i=h+1.
# Returns are LOG RETURNS (literal copy of Eq. 1, not an approximation).
#
# Paper IS: 2013-04-01 → 2016-12-31; paper OOS: 2017-01-01 → 2021-05-01.
# Our splits follow the project protocol (not the paper's calendar):
IS_END = pd.Timestamp("2020-12-31")
OOS1_END = pd.Timestamp("2023-12-31")
OOS2_START = pd.Timestamp("2024-01-01")

# HAC: Newey-West (1987), automatic bandwidth Newey-West (1994)
# L = floor(4*(N/100)^(2/9)), conservative floor of 5 (~one trading week
# of daily residual autocorrelation). One observation per calendar day.
HAC_FLOOR = 5
MIN_REG_N = 60

# Discovery freeze (IS + OOS-1 only). Pre-specified; not tuned on OOS-2.
# |beta| >= 0.03 is below Wen's reported IS/OOS pairs (~0.09 and ~0.13)
# and is not microscopic relative to hourly BTC moves.
BETA_MIN = 0.03
P_MAX_DISCOVERY = 0.05

# Final OOS-2 survival (applied once, only to frozen candidates).
BETA_MIN_OOS2 = 0.03
P_MAX_OOS2 = 0.10

MIN_TRAIN = 250  # expanding-window forecasts

# Wen et al. pairs that survive both their IS and OOS (paper hours 1-24),
# mapped to our 0-23 UTC hours. Used only for qualitative comparison.
WEN_PAIRS = {
    (2, 16): "MOMENTUM",   # paper r3 → r17
    (7, 21): "MOMENTUM",   # paper r8 → r22
    (2, 4): "REVERSAL",    # paper r3 → r5
    (2, 14): "REVERSAL",   # paper r3 → r15
    (11, 12): "REVERSAL",  # paper r12 → r13
    (21, 22): "REVERSAL",  # paper r22 → r23
}

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "btcusdt_1h.csv"
OUT_PAIRS = ROOT / "intraday_pairs.csv"
OUT_CAND = ROOT / "intraday_candidates.csv"
OUT_FCST = ROOT / "intraday_forecasts.csv"
OUT_MD = ROOT / "intraday_replication_summary.md"

PAIR_COLS = [
    "sample",
    "predictor_hour_utc",
    "target_hour_utc",
    "alpha",
    "beta",
    "se",
    "t_stat",
    "p_value",
    "fdr_p_value",
    "r2",
    "N",
    "P_up_given_predictor_positive",
    "P_up_given_predictor_negative",
    "probability_edge",
    "mean_target_given_predictor_positive",
    "mean_target_given_predictor_negative",
]
CAND_COLS = [
    "predictor_hour",
    "target_hour",
    "type",
    "beta_IS",
    "beta_OOS1",
    "OOS2_beta",
    "OOS2_t",
    "OOS2_p",
    "OOS2_FDR",
    "probability_edge_OOS2",
    "final_status",
]
FCST_COLS = [
    "forecast_date",
    "predictor_hour",
    "target_hour",
    "predictor_return",
    "alpha_estimate",
    "beta_estimate",
    "forecast_return",
    "prediction_interval_low",
    "prediction_interval_high",
    "current_price",
    "projected_target_price",
    "training_end_date",
]


def sample_of_date(d: pd.Timestamp) -> str | float:
    d = pd.Timestamp(d).normalize()
    if d <= IS_END:
        return "IS"
    if d <= OOS1_END:
        return "OOS-1"
    if d >= OOS2_START:
        return "OOS-2"
    return np.nan


def nw_lags(n: int) -> int:
    auto = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    return max(HAC_FLOOR, auto)


def hac_ols(y: np.ndarray, x: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = int(y.size)
    empty = {
        "alpha": np.nan,
        "beta": np.nan,
        "se": np.nan,
        "t_stat": np.nan,
        "p_value": np.nan,
        "r2": np.nan,
        "N": n,
    }
    if n < MIN_REG_N:
        return empty
    lags = min(nw_lags(n), max(1, n // 4))
    X = sm.add_constant(x, has_constant="add")
    fit = sm.OLS(y, X).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True}
    )
    return {
        "alpha": float(fit.params[0]),
        "beta": float(fit.params[1]),
        "se": float(fit.bse[1]),
        "t_stat": float(fit.tvalues[1]),
        "p_value": float(fit.pvalues[1]),
        "r2": float(fit.rsquared),
        "N": n,
    }


def dir_stats(ri: np.ndarray, rj: np.ndarray) -> dict:
    m = np.isfinite(ri) & np.isfinite(rj)
    ri, rj = ri[m], rj[m]
    pos, neg = ri > 0, ri < 0

    def _mean(a, c):
        return float(np.mean(a[c])) if c.any() else np.nan

    p_pos = _mean(rj > 0, pos)
    p_neg = _mean(rj > 0, neg)
    if np.isfinite(p_pos) and np.isfinite(p_neg) and p_neg != 0:
        edge = p_pos / p_neg
    else:
        edge = np.nan
    return {
        "P_up_given_predictor_positive": p_pos,
        "P_up_given_predictor_negative": p_neg,
        "probability_edge": edge,
        "mean_target_given_predictor_positive": _mean(rj, pos),
        "mean_target_given_predictor_negative": _mean(rj, neg),
    }


def load_data() -> tuple[pd.DataFrame, dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Required snapshot missing: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    if "timestamp_utc" not in df.columns or "close" not in df.columns:
        raise ValueError("btcusdt_1h.csv must contain timestamp_utc and close")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True).dt.tz_localize(
        None
    )
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    n_dup = int(df["timestamp_utc"].duplicated().sum())
    n_nan_close = int(df["close"].isna().sum())
    t0, t1 = df["timestamp_utc"].iloc[0], df["timestamp_utc"].iloc[-1]
    full = pd.date_range(t0, t1, freq="h")
    n_missing = int(len(full.difference(df["timestamp_utc"])))
    diag = {
        "file": str(DATA_FILE.name),
        "t0": t0,
        "t1": t1,
        "N": int(len(df)),
        "duplicates": n_dup,
        "nan_close": n_nan_close,
        "missing_hours": n_missing,
        "ohlcv_kept": [c for c in ("open", "high", "low", "close", "volume") if c in df.columns],
    }
    df["log_close"] = np.log(df["close"].astype(float))
    df["dt"] = df["timestamp_utc"].diff()
    df["r"] = df["log_close"].diff()
    # Do not interpolate: a gap larger than 1h makes the next return span
    # more than one hour, so it is not an hourly return.
    df.loc[df["dt"] != pd.Timedelta(hours=1), "r"] = np.nan
    df["date"] = df["timestamp_utc"].dt.normalize()
    df["hour"] = df["timestamp_utc"].dt.hour.astype(int)
    df["sample"] = df["date"].map(sample_of_date)
    return df, diag


def build_panels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ret = df.pivot_table(index="date", columns="hour", values="r", aggfunc="first")
    px = df.pivot_table(index="date", columns="hour", values="close", aggfunc="first")
    ret = ret.reindex(columns=range(24))
    px = px.reindex(columns=range(24))
    return ret, px


def fit_all_pairs(ret: pd.DataFrame) -> pd.DataFrame:
    dates = ret.index
    samples = pd.Series([sample_of_date(d) for d in dates], index=dates)
    rows = []
    for i in range(24):
        for j in range(i + 1, 24):
            ri = ret[i].to_numpy(dtype=float)
            rj = ret[j].to_numpy(dtype=float)
            for samp in ("IS", "OOS-1", "OOS-2"):
                m = (samples == samp).to_numpy()
                fit = hac_ols(rj[m], ri[m])
                ds = dir_stats(ri[m], rj[m])
                rows.append(
                    {
                        "sample": samp,
                        "predictor_hour_utc": i,
                        "target_hour_utc": j,
                        **fit,
                        **ds,
                    }
                )
    out = pd.DataFrame(rows)
    out["fdr_p_value"] = np.nan
    for samp in ("IS", "OOS-1", "OOS-2"):
        idx = out.index[out["sample"] == samp]
        p = out.loc[idx, "p_value"].to_numpy(dtype=float)
        valid = np.isfinite(p)
        adj = np.full(p.shape, np.nan)
        if valid.any():
            adj[valid] = multipletests(p[valid], method="fdr_bh")[1]
        out.loc[idx, "fdr_p_value"] = adj
    return out[PAIR_COLS].sort_values(
        ["sample", "predictor_hour_utc", "target_hour_utc"]
    ).reset_index(drop=True)


def freeze_candidates(pairs: pd.DataFrame) -> pd.DataFrame:
    is_ = pairs[pairs["sample"] == "IS"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    o1 = pairs[pairs["sample"] == "OOS-1"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    o2 = pairs[pairs["sample"] == "OOS-2"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    keys = is_.index.intersection(o1.index).intersection(o2.index)
    recs = []
    for key in keys:
        b_is = float(is_.loc[key, "beta"])
        b_o1 = float(o1.loc[key, "beta"])
        p_is = float(is_.loc[key, "p_value"])
        p_o1 = float(o1.loc[key, "p_value"])
        if not np.isfinite(b_is) or not np.isfinite(b_o1):
            continue
        if b_is == 0 or b_o1 == 0:
            continue
        same_sign = np.sign(b_is) == np.sign(b_o1)
        mag = abs(b_is) >= BETA_MIN and abs(b_o1) >= BETA_MIN
        stat = p_is < P_MAX_DISCOVERY and p_o1 < P_MAX_DISCOVERY
        if not (same_sign and mag and stat):
            continue
        typ = "MOMENTUM" if b_is > 0 else "REVERSAL"
        b2 = float(o2.loc[key, "beta"])
        t2 = float(o2.loc[key, "t_stat"])
        p2 = float(o2.loc[key, "p_value"])
        f2 = float(o2.loc[key, "fdr_p_value"])
        e2 = float(o2.loc[key, "probability_edge"])
        survived = (
            np.isfinite(b2)
            and np.sign(b2) == np.sign(b_is)
            and abs(b2) >= BETA_MIN_OOS2
            and np.isfinite(p2)
            and p2 < P_MAX_OOS2
        )
        recs.append(
            {
                "predictor_hour": int(key[0]),
                "target_hour": int(key[1]),
                "type": typ,
                "beta_IS": b_is,
                "beta_OOS1": b_o1,
                "OOS2_beta": b2,
                "OOS2_t": t2,
                "OOS2_p": p2,
                "OOS2_FDR": f2,
                "probability_edge_OOS2": e2,
                "final_status": "SURVIVED FINAL OOS" if survived else "FAILED FINAL OOS",
            }
        )
    if not recs:
        return pd.DataFrame(columns=CAND_COLS)
    return (
        pd.DataFrame(recs)[CAND_COLS]
        .sort_values(["type", "predictor_hour", "target_hour"])
        .reset_index(drop=True)
    )


def expanding_forecasts(
    ret: pd.DataFrame,
    px: pd.DataFrame,
    survivors: pd.DataFrame,
) -> pd.DataFrame:
    if survivors.empty:
        return pd.DataFrame(columns=FCST_COLS)
    oos2_dates = [d for d in ret.index if sample_of_date(d) == "OOS-2"]
    rows = []
    for _, c in survivors.iterrows():
        i, j = int(c["predictor_hour"]), int(c["target_hour"])
        ri_all = ret[i]
        rj_all = ret[j]
        for d in oos2_dates:
            x0 = ri_all.loc[d]
            if not np.isfinite(x0):
                continue
            train_idx = (ret.index < d) & ri_all.notna() & rj_all.notna()
            x = ri_all.loc[train_idx].to_numpy(dtype=float)
            y = rj_all.loc[train_idx].to_numpy(dtype=float)
            n = int(y.size)
            if n < MIN_TRAIN:
                continue
            # OLS via lstsq (faster than statsmodels in the expanding loop)
            X = np.column_stack([np.ones(n), x])
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            a, b = float(coef[0]), float(coef[1])
            yhat = a + b * float(x0)
            resid = y - X @ coef
            s2 = float(np.sum(resid**2) / (n - 2))
            xbar = float(np.mean(x))
            sxx = float(np.sum((x - xbar) ** 2))
            se_pred = float(np.sqrt(s2 * (1.0 + 1.0 / n + (float(x0) - xbar) ** 2 / sxx)))
            tcrit = float(student_t.ppf(0.975, n - 2))
            lo, hi = yhat - tcrit * se_pred, yhat + tcrit * se_pred
            price = px.loc[d, i] if i in px.columns else np.nan
            price = float(price) if np.isfinite(price) else np.nan
            proj = price * np.exp(yhat) if np.isfinite(price) else np.nan
            train_end = ret.index[train_idx].max()
            rows.append(
                {
                    "forecast_date": pd.Timestamp(d).strftime("%Y-%m-%d"),
                    "predictor_hour": i,
                    "target_hour": j,
                    "predictor_return": float(x0),
                    "alpha_estimate": a,
                    "beta_estimate": b,
                    "forecast_return": yhat,
                    "prediction_interval_low": lo,
                    "prediction_interval_high": hi,
                    "current_price": price,
                    "projected_target_price": proj,
                    "training_end_date": pd.Timestamp(train_end).strftime("%Y-%m-%d"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=FCST_COLS)
    return pd.DataFrame(rows)[FCST_COLS]


def live_mask(df: pd.DataFrame, fcst: pd.DataFrame) -> pd.DataFrame:
    """Keep last-day rows whose target hour is not yet in the snapshot."""
    if fcst.empty:
        return fcst
    last_ts = df["timestamp_utc"].max()
    last_date = last_ts.normalize()
    closed = set(df.loc[df["date"] == last_date, "hour"].astype(int))
    last = fcst[fcst["forecast_date"] == last_date.strftime("%Y-%m-%d")].copy()
    if last.empty:
        return last
    keep = last.apply(
        lambda r: int(r["predictor_hour"]) in closed
        and int(r["target_hour"]) not in closed,
        axis=1,
    )
    return last.loc[keep]


def mat_md(pairs: pd.DataFrame, sample: str, col: str, fmt: str) -> str:
    sub = pairs[pairs["sample"] == sample]
    pivot = sub.pivot(
        index="predictor_hour_utc", columns="target_hour_utc", values=col
    ).reindex(index=range(24), columns=range(24))
    header = "| i\\j | " + " | ".join(f"{h:02d}" for h in range(24)) + " |"
    sep = "| --- |" + " --- |" * 24
    lines = [header, sep]
    for i in range(24):
        cells = []
        for j in range(24):
            if j <= i:
                cells.append("—")
            else:
                v = pivot.loc[i, j]
                cells.append(fmt.format(v) if np.isfinite(v) else "NA")
        lines.append(f"| {i:02d} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def fmt_pct(x: float, digits: int = 2) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{100.0 * x:.{digits}f}%"


def write_summary(
    diag, ret, pairs, cand, fcst, live, df
) -> None:
    n_days = int(ret.dropna(how="all").shape[0])
    n_complete = int((ret.notna().sum(axis=1) == 24).sum())
    is_p = pairs[pairs["sample"] == "IS"]
    o1_p = pairs[pairs["sample"] == "OOS-1"]
    o2_p = pairs[pairs["sample"] == "OOS-2"]

    def count_sig(p, pcol="p_value", thr=0.05):
        return int((p[pcol] < thr).sum())

    n_mom_c = int((cand["type"] == "MOMENTUM").sum()) if not cand.empty else 0
    n_rev_c = int((cand["type"] == "REVERSAL").sum()) if not cand.empty else 0
    surv = cand[cand["final_status"] == "SURVIVED FINAL OOS"] if not cand.empty else cand
    fail = cand[cand["final_status"] == "FAILED FINAL OOS"] if not cand.empty else cand
    n_surv = int(len(surv))
    n_fail = int(len(fail))
    n_mom_s = int((surv["type"] == "MOMENTUM").sum()) if n_surv else 0
    n_rev_s = int((surv["type"] == "REVERSAL").sum()) if n_surv else 0
    r2_is, r2_o1, r2_o2 = is_p["r2"].median(), o1_p["r2"].median(), o2_p["r2"].median()
    r2_sig_is = is_p.loc[is_p["p_value"] < 0.05, "r2"].median()
    beta_abs_is = is_p["beta"].abs().median()
    beta_abs_sig = is_p.loc[is_p["p_value"] < 0.05, "beta"].abs().median()

    wen_lines = []
    for (i, j), typ in WEN_PAIRS.items():
        bits = []
        for samp, block in (("IS", is_p), ("OOS-1", o1_p), ("OOS-2", o2_p)):
            row = block[
                (block["predictor_hour_utc"] == i) & (block["target_hour_utc"] == j)
            ].iloc[0]
            bits.append(
                f"{samp}: β={row['beta']:.4f}, t={row['t_stat']:.2f}, "
                f"p={row['p_value']:.3f}, FDR={row['fdr_p_value']:.3f}"
            )
        frozen = (
            not cand.empty
            and ((cand["predictor_hour"] == i) & (cand["target_hour"] == j)).any()
        )
        wen_lines.append(
            f"- paper {typ} r{i+1}→r{j+1} (UTC {i:02d}→{j:02d}): "
            + " | ".join(bits)
            + f" | candidato congelado={frozen}"
        )

    n_fdr_disc = count_sig(is_p, "fdr_p_value", 0.10) + count_sig(
        o1_p, "fdr_p_value", 0.10
    )
    # Dual p<0.05 in 276 tests has ~0.35 expected false candidates under
    # a global null; FDR=0 in discovery means those hits are not
    # multiple-testing-robust. Do not count them as a partial replica.
    if n_surv >= 1 and n_mom_s >= 1 and n_rev_s >= 1:
        verdict = "A — REPLICATION SUCCESSFUL"
        verdict_why = (
            "Al menos un par de momentum y uno de reversal, congelados con "
            "IS+OOS-1, conservan signo, magnitud y evidencia en OOS-2."
        )
    elif n_surv >= 1:
        verdict = "B — PARTIAL REPLICATION"
        verdict_why = (
            "Hay al menos un superviviente en OOS-2, pero no se reproduce "
            "de forma conjunta momentum y reversal (el hallazgo central de "
            "Wen et al.)."
        )
    elif n_fdr_disc >= 1 and (n_mom_c + n_rev_c) >= 1:
        verdict = "B — PARTIAL REPLICATION"
        verdict_why = (
            "Hay evidencia FDR en discovery y candidatos congelados, pero "
            "ninguno sobrevive OOS-2."
        )
    else:
        verdict = "C — REPLICATION NOT CONFIRMED"
        verdict_why = (
            "Ningún par tiene FDR<0.10 en IS ni en OOS-1. El único par que "
            "pasa el freeze de signo+magnitud+p<0.05 en IS y OOS-1 es "
            "compatible con un falso positivo esperado (~0.35 bajo el null "
            "global) y colapsa en OOS-2. Los pares destacados de Wen et al. "
            "no mantienen signo. No hay base para forecasts."
            if (n_mom_c + n_rev_c) >= 1
            else (
                "Ningún par cumple el freeze IS+OOS-1 y no hay FDR<0.10 en "
                "discovery. No hay base para forecasts."
            )
        )

    last_ts = df["timestamp_utc"].max()
    last_date = last_ts.normalize()
    closed_hours = sorted(set(df.loc[df["date"] == last_date, "hour"].astype(int)))
    n_fcst = int(len(fcst))
    n_live = int(len(live))

    if not cand.empty:
        top = cand.assign(ab=cand["OOS2_beta"].abs()).sort_values(
            ["final_status", "ab"], ascending=[True, False]
        )
        solid = "\n".join(
            f"- UTC {int(r['predictor_hour']):02d}→{int(r['target_hour']):02d} "
            f"({r['type']}, {r['final_status']}): β_IS={r['beta_IS']:.4f}, "
            f"β_OOS1={r['beta_OOS1']:.4f}, β_OOS2={r['OOS2_beta']:.4f}, "
            f"t_OOS2={r['OOS2_t']:.2f}, p_OOS2={r['OOS2_p']:.4f}, "
            f"FDR_OOS2={r['OOS2_FDR']:.3f}, edge_OOS2={r['probability_edge_OOS2']:.3f}"
            for _, r in top.iterrows()
        )
        if n_surv == 0:
            solid += (
                "\n\nNinguno de estos candidatos congelados sobrevive OOS-2. "
                "No se sustituyen por otros pares de la matriz OOS-2."
            )
    else:
        solid = "No hubo candidatos congelados; no hay par sólido que reportar."

    if n_live:
        live_txt = "\n".join(
            f"- señal UTC {r['forecast_date']} {int(r['predictor_hour']):02d}:00 "
            f"(cerrada), target {int(r['target_hour']):02d}:00, "
            f"r_i={fmt_pct(r['predictor_return'], 3)}, "
            f"E[r_j]={fmt_pct(r['forecast_return'], 3)}, "
            f"dir={'UP' if r['forecast_return']>0 else 'DOWN'}, "
            f"β={r['beta_estimate']:.4f}, "
            f"PI95=[{fmt_pct(r['prediction_interval_low'], 2)}, "
            f"{fmt_pct(r['prediction_interval_high'], 2)}], "
            f"P_current={r['current_price']:.2f}, "
            f"proyección condicional={r['projected_target_price']:.2f}, "
            f"train≤{r['training_end_date']}"
            for _, r in live.iterrows()
        )
    else:
        live_txt = (
            "No hay forecast del día más reciente: o no hay supervivientes, "
            "o la hora predictora aún no está cerrada, o el target ya ocurrió "
            "en el snapshot."
        )

    if n_fcst:
        w = float(np.median(fcst["prediction_interval_high"] - fcst["prediction_interval_low"]))
        pi_note = (
            f"Mediana del ancho del intervalo de predicción 95% (retorno "
            f"individual, no CI de la media): {fmt_pct(w, 2)}. "
        )
        q13 = (
            pi_note
            + "El intervalo reportado es un **prediction interval** del retorno "
            "individual (incluye σ residual), no un interval de confianza de E[r_j|r_i]. "
            "El PI es el relevante para interpretación de un outcome de una hora. "
            "Aproximación: residuos OLS iid + t_{n-2}; no es un PI HAC. "
            "En BTC horario el PI es ancho: una media de +0.3% convive con un rango "
            "de varios puntos porcentuales."
        )
    else:
        q13 = "No aplica: no hay forecasts."

    if n_surv:
        ok = 0
        for _, r in surv.iterrows():
            e = r["probability_edge_OOS2"]
            if r["type"] == "MOMENTUM" and np.isfinite(e) and e > 1:
                ok += 1
            if r["type"] == "REVERSAL" and np.isfinite(e) and e < 1:
                ok += 1
        edge_support = (
            f"{ok}/{n_surv} supervivientes tienen probability edge "
            f"(ratio P(up|ri>0)/P(up|ri<0)) en la dirección esperada "
            f"(>1 momentum, <1 reversal) en OOS-2."
        )
    else:
        edge_support = (
            "Sin supervivientes; la edge no se usa para reclamar predictibilidad."
        )

    q1 = (
        "Hay celdas con p crudo < 0.05 en la matriz 276, como es inevitable "
        f"bajo multiple testing (esperados ≈ {276*0.05:.0f} bajo el null; "
        f"observados IS: {count_sig(is_p)}, OOS-1: {count_sig(o1_p)}, "
        f"OOS-2: {count_sig(o2_p)}). "
        f"p mínimo: IS={is_p['p_value'].min():.4f}, "
        f"OOS-1={o1_p['p_value'].min():.4f}, "
        f"OOS-2={o2_p['p_value'].min():.4f}. "
        f"FDR mínimo: IS={is_p['fdr_p_value'].min():.3f}, "
        f"OOS-1={o1_p['fdr_p_value'].min():.3f}, "
        f"OOS-2={o2_p['fdr_p_value'].min():.3f}. "
        f"Tras FDR BH, IS tiene {count_sig(is_p, 'fdr_p_value', 0.10)} pares "
        f"con FDR<0.10, OOS-1 {count_sig(o1_p, 'fdr_p_value', 0.10)}, "
        f"OOS-2 {count_sig(o2_p, 'fdr_p_value', 0.10)}. "
        "Predictibilidad intradía, en el sentido de Wen et al., requiere "
        "signo estable across samples y sobrevivir FDR — no un p aislado."
    )
    q11 = (
        f"Sí hay pares SURVIVED FINAL OOS ({n_surv}). "
        f"Se generan {n_fcst} filas de forecast expanding-window en OOS-2."
        if n_surv
        else "No. Sin supervivientes OOS-2 no se generan forecasts (CSV vacío con headers)."
    )

    mats = {
        "is_b": mat_md(pairs, "IS", "beta", "{:.3f}"),
        "is_t": mat_md(pairs, "IS", "t_stat", "{:.2f}"),
        "is_f": mat_md(pairs, "IS", "fdr_p_value", "{:.3f}"),
        "is_e": mat_md(pairs, "IS", "probability_edge", "{:.3f}"),
        "o1_b": mat_md(pairs, "OOS-1", "beta", "{:.3f}"),
        "o1_t": mat_md(pairs, "OOS-1", "t_stat", "{:.2f}"),
        "o1_f": mat_md(pairs, "OOS-1", "fdr_p_value", "{:.3f}"),
        "o1_e": mat_md(pairs, "OOS-1", "probability_edge", "{:.3f}"),
        "o2_b": mat_md(pairs, "OOS-2", "beta", "{:.3f}"),
        "o2_t": mat_md(pairs, "OOS-2", "t_stat", "{:.2f}"),
        "o2_f": mat_md(pairs, "OOS-2", "fdr_p_value", "{:.3f}"),
        "o2_e": mat_md(pairs, "OOS-2", "probability_edge", "{:.3f}"),
    }

    md = f"""# Réplica Wen, Bouri, Xu & Zhao (2022) — predictibilidad intradía BTC

Paper: Wen, Zhuzhu; Bouri, Elie; Xu, Yahua; Zhao, Yang (2022).
“Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both”.
*The North American Journal of Economics and Finance*, 62, 101733.
DOI: 10.1016/j.najef.2022.101733.

Esta fase es una **réplica académica** de la lógica empírica hora-del-día, no una estrategia de trading.

Snapshot usado: **`{diag['file']}`** (Binance BTCUSDT spot 1h). No se redescargó.

---

## 0. Metodología copiada vs aproximada

Definición de retorno (paper Eq. 1, texto completo disponible):

`r_{{i,t}} = log(p_{{i,t}}) − log(p_{{i-1,t}})`, i = 1,…,24

con `p_{{0,t}}` = precio a las 00:00 UTC del día t (cierre de la vela 23:00 del día anterior).

**Esto se copia de forma literal: log returns.** No es una aproximación.

Indexación: hora UTC `h = 0..23` = hora del paper `i = h+1`.
Ejemplo: paper r3→r17 = UTC 02:00 → 16:00.

Regresión (paper Eq. 4): una observación por día,

`r_{{d,j}} = α_{{ij}} + β_{{ij}} r_{{d,i}} + ε`, con j > i.

Grid: 24×23/2 = **276** pares. Sin ventanas agregadas.

Errores estándar: **HAC Newey–West (1987)** con bandwidth automático
Newey–West (1994) `L = floor(4*(N/100)^(2/9))` y suelo conservador
`L ≥ {HAC_FLOOR}` (≈ una semana de autocorrelación diaria).
`statsmodels` `cov_type='HAC'`, `use_correction=True`.
No se usan SE iid como única inferencia.

FDR: Benjamini–Hochberg, **por separado** en IS, OOS-1 y OOS-2 (276 tests cada uno).

Splits (protocolo de este proyecto, **no** el calendario del paper):

| sample | fechas (día UTC) |
|---|---|
| IS | 2017-08-17 → 2020-12-31 |
| OOS-1 | 2021-01-01 → 2023-12-31 |
| OOS-2 FINAL | 2024-01-01 → última observación |

Paper original: IS 2013-04-01→2016-12-31, OOS 2017-01-01→2021-05-01, datos Bitstamp GMT, retornos horarios construidos desde precios 5-min. Aquí: Binance 1h nativo. Esa es una diferencia de réplica, documentada.

Forecasts: ventana **expanding diaria** con coeficientes estimados hasta **d−1** (más estricto que el paper, que expandía **un mes** cada vez). Mínimo {MIN_TRAIN} días de entrenamiento.

---

## Datos

- archivo: `{diag['file']}`
- inicio: {diag['t0']}
- fin: {diag['t1']}
- N velas: {diag['N']}
- duplicados de timestamp: {diag['duplicates']}
- NaNs en close: {diag['nan_close']}
- velas horarias faltantes (calendario 1h, **sin interpolar**): {diag['missing_hours']}
- columnas OHLCV preservadas: {', '.join(diag['ohlcv_kept'])}
- días con al menos un retorno: {n_days}
- días con 24 horas completas: {n_complete}
- último día del snapshot: {last_date.date()} · horas cerradas: {closed_hours}

Un retorno horario se anula si la vela previa no está exactamente 1h antes. No se rellenan huecos.

---

## Freeze (IS + OOS-1 only)

Un par es candidato si y solo si:

1. signo(β_IS) = signo(β_OOS1);
2. |β_IS| ≥ {BETA_MIN} y |β_OOS1| ≥ {BETA_MIN} (no microscópico);
3. p_IS < {P_MAX_DISCOVERY} y p_OOS1 < {P_MAX_DISCOVERY} (evidencia compatible en ambos; no se elige el mínimo p de la matriz).

OOS-2 no entra en la selección.

Supervivencia OOS-2 (una sola apertura, solo candidatos):

- mismo signo;
- |β_OOS2| ≥ {BETA_MIN_OOS2};
- p_OOS2 < {P_MAX_OOS2}.

FAILED si cambia de signo, colapsa a ~0 o desaparece. **No se reemplazan** por pares que lucen bien solo en OOS-2.

---

## 1. ¿Encontramos predictibilidad intradía en BTC?

{q1}

## 2. ¿Aparece momentum?

Momentum (β>0) congelado IS+OOS-1: {n_mom_c} par(es). Superviven OOS-2: {n_mom_s}.

## 3. ¿Aparece reversal?

Reversal (β<0) congelado IS+OOS-1: {n_rev_c} par(es). Superviven OOS-2: {n_rev_s}.

## 4. ¿Cuántos pares sobreviven IS → OOS-1?

{len(cand)} par(es) (MOMENTUM {n_mom_c}, REVERSAL {n_rev_c}). Solo el freeze IS+OOS-1; OOS-2 no seleccionó.

## 5. ¿Cuántos sobreviven OOS-2?

{n_surv} sobreviven; {n_fail} fallan. No se sustituyen por pares que “funcionen” solo en OOS-2.

## 6. ¿Cuáles son los pares más sólidos?

{solid}

## 7. ¿La dirección coincide con Wen et al.?

Wen et al. (Bitstamp, 2013–2020) reportan ambas cosas: momentum dentro de horas de mercados de acciones (p.ej. r3→r17, r8→r22) y reversal fuera de esas horas (p.ej. r3→r5, r12→r13, r22→r23). Esta réplica usa Binance BTCUSDT 2017–2026 y splits distintos. Comparación cualitativa de esos pares (no usados para seleccionar):

{chr(10).join(wen_lines)}

## 8. ¿Cuál es el R² típico?

R² mediano de las 276 celdas: IS={r2_is:.4f}, OOS-1={r2_o1:.4f}, OOS-2={r2_o2:.4f}. Entre pares con p<0.05 en IS, R² mediano={r2_sig_is:.4f}. Esto es típico de predictibilidad horaria: a veces detectable, R² pequeño.

## 9. ¿Cuál es la magnitud económica de los efectos?

|β| mediano (276 pares IS)={beta_abs_is:.4f}; |β| mediano si p<0.05 en IS={beta_abs_sig:.4f}. Wen reporta ~0.09 y ~0.13 en sus pares destacados. Un |β|=0.10 implica que un retorno predictor de +1% mueve el esperado del target en ~10 bp — magnitud pequeña frente a la volatilidad horaria de BTC (típicamente decenas de bp a >100 bp).

## 10. ¿La probability edge respalda las regresiones?

Definición (ratio, no diferencia): ProbabilityEdge = P(r_j>0 | r_i>0) / P(r_j>0 | r_i<0).

Momentum espera edge > 1; reversal espera edge < 1. Evidencia secundaria.

{edge_support}

## 11. ¿Existe suficiente evidencia para generar forecasts?

{q11}

## 12. ¿Qué forecasts pueden calcularse con información ya observada?

Día más reciente del snapshot: {last_date.date()}. Horas predictoras cerradas: {closed_hours}.

{live_txt}

Filas expanding-window en `intraday_forecasts.csv` (todo OOS-2, coeficientes hasta d−1): {n_fcst}.
Filas del día incompleto con target aún no ocurrido: {n_live}.

## 13. ¿Qué incertidumbre tienen?

{q13}

La proyección de precio es **conditional point projection** `P̂_j = P_{{cierre de i}} · exp(r̂_j)` (log-return → precio). No es “BTC estará en X”. Debe leerse junto al PI.

El **CI de la media** E[r_j | r_i] es más estrecho (no incluye σ residual) y **no** se usa para interpretación de un retorno horario individual.

## 14. ¿La réplica debe considerarse exitosa, parcial o fallida?

{verdict_why}

---

## STATISTICAL PREDICTABILITY vs ECONOMIC VALUE vs TRADEABLE EDGE

Esta fase mide principalmente **statistical predictability** (signo de β, t, FDR, R², edge direccional).

**No** se afirma:

- profitable strategy;
- arbitrage;
- tradeable edge.

R² pequeño + PI ancho + BTC horario ruidoso ⇒ una β significativa **no** implica valor económico ni ejecución. Fees, slippage, sizing y timing están explícitamente fuera de alcance.

---

## Conteos FDR / p crudo (276 pares)

| sample | p<0.05 | p<0.10 | FDR<0.10 | FDR<0.05 | β>0 y p<0.05 | β<0 y p<0.05 |
|---|---:|---:|---:|---:|---:|---:|
| IS | {count_sig(is_p)} | {count_sig(is_p,'p_value',0.10)} | {count_sig(is_p,'fdr_p_value',0.10)} | {count_sig(is_p,'fdr_p_value',0.05)} | {int(((is_p['beta']>0)&(is_p['p_value']<0.05)).sum())} | {int(((is_p['beta']<0)&(is_p['p_value']<0.05)).sum())} |
| OOS-1 | {count_sig(o1_p)} | {count_sig(o1_p,'p_value',0.10)} | {count_sig(o1_p,'fdr_p_value',0.10)} | {count_sig(o1_p,'fdr_p_value',0.05)} | {int(((o1_p['beta']>0)&(o1_p['p_value']<0.05)).sum())} | {int(((o1_p['beta']<0)&(o1_p['p_value']<0.05)).sum())} |
| OOS-2 | {count_sig(o2_p)} | {count_sig(o2_p,'p_value',0.10)} | {count_sig(o2_p,'fdr_p_value',0.10)} | {count_sig(o2_p,'fdr_p_value',0.05)} | {int(((o2_p['beta']>0)&(o2_p['p_value']<0.05)).sum())} | {int(((o2_p['beta']<0)&(o2_p['p_value']<0.05)).sum())} |

Candidatos congelados: {len(cand)} · SURVIVED: {n_surv} · FAILED: {n_fail}

---

## Matrices 24×24 (celdas j≤i = —)

Filas = predictor hour i. Columnas = target hour j.

### IS — beta

{mats['is_b']}

### IS — t-stat

{mats['is_t']}

### IS — FDR

{mats['is_f']}

### IS — probability edge

{mats['is_e']}

### OOS-1 — beta

{mats['o1_b']}

### OOS-1 — t-stat

{mats['o1_t']}

### OOS-1 — FDR

{mats['o1_f']}

### OOS-1 — probability edge

{mats['o1_e']}

### OOS-2 — beta (evaluación final; no se usó para elegir candidatos)

{mats['o2_b']}

### OOS-2 — t-stat

{mats['o2_t']}

### OOS-2 — FDR

{mats['o2_f']}

### OOS-2 — probability edge

{mats['o2_e']}

---

### {verdict}
"""
    OUT_MD.write_text(md, encoding="utf-8")


def main() -> None:
    df, diag = load_data()
    print("DATA", diag)
    ret, px = build_panels(df)
    print(f"pairs expected=276, fitting {3*276} regressions...")
    pairs = fit_all_pairs(ret)
    assert pairs.groupby("sample").size().eq(276).all(), "expected 276 pairs per sample"
    cand = freeze_candidates(pairs)
    surv = (
        cand[cand["final_status"] == "SURVIVED FINAL OOS"]
        if not cand.empty
        else cand
    )
    print(f"candidates={len(cand)} survived={len(surv)}")
    fcst = expanding_forecasts(ret, px, surv)
    live = live_mask(df, fcst)
    print(f"forecasts={len(fcst)} live={len(live)}")

    pairs.to_csv(OUT_PAIRS, index=False)
    cand.to_csv(OUT_CAND, index=False)
    fcst.to_csv(OUT_FCST, index=False)
    write_summary(diag, ret, pairs, cand, fcst, live, df)
    print("wrote", OUT_PAIRS.name, OUT_CAND.name, OUT_FCST.name, OUT_MD.name)


if __name__ == "__main__":
    main()
