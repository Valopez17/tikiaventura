#!/usr/bin/env python3
"""H2: MACRO lag diagnostic. L in {0,4,8} × H in {4,8,12}.

Frozen four-feature macro set vs expanding base rate.
No crypto features. No extra lags/horizons. No 2024–2026.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
RQF = PHASE.parent
MACRO_CSV = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
CATALOG_CSV = (
    RQF / "phase3_opportunity_episodes" / "results" / "opportunity_episode_catalog.csv"
)

SAMPLE_END = pd.Timestamp("2023-12-29")
VAL_START = pd.Timestamp("2021-01-01")
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
LAGS = (0, 4, 8)
HORIZONS = (4, 8, 12)
FULL_PERIOD = "FULL_EXPANDING_WF"
TEMPORAL_PERIOD = "TEMPORAL_ROBUSTNESS_2021_2023"
FEATURES = [
    "DXY_CHG_12W",
    "US2Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "NASDAQ_RET_12W",
]


def window_return(r4: np.ndarray, lag: int, horizon: int) -> np.ndarray:
    """Compound catalog 4w returns over t+L+1 … t+L+H. No 2024+ weeks."""
    if horizon % 4 != 0 or lag % 4 != 0:
        raise ValueError("lag and horizon must be multiples of 4 for 4w chaining")
    n = len(r4)
    n_blocks = horizon // 4
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        wealth = 1.0
        ok = True
        for b in range(n_blocks):
            j = i + lag + 4 * b
            if j >= n or not np.isfinite(r4[j]):
                ok = False
                break
            wealth *= 1.0 + r4[j]
        if ok:
            out[i] = wealth - 1.0
    return out


def load_frame() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG_CSV, parse_dates=["week"])
    mac = pd.read_csv(MACRO_CSV, parse_dates=["week"])
    for name, d in ("catalog", cat), ("macro", mac):
        if d["week"].duplicated().any():
            raise RuntimeError(f"duplicated weeks in {name}")
        if (d["week"].dt.year >= 2024).any() or d["week"].max() > SAMPLE_END:
            raise RuntimeError(f"2024+ or past sample end in {name}")
    cat = cat.loc[cat["week"] <= SAMPLE_END].copy().sort_values("week")
    mac = mac.loc[mac["week"] <= SAMPLE_END].copy()
    miss = [c for c in FEATURES if c not in mac.columns]
    if miss:
        raise RuntimeError(f"macro missing {miss}")
    if "future_return_4w" not in cat.columns or "future_return_12w" not in cat.columns:
        raise RuntimeError("catalog missing future_return_4w / future_return_12w")
    df = cat.merge(mac[["week"] + FEATURES], on="week", how="inner", validate="one_to_one")
    df = df.sort_values("week").reset_index(drop=True)
    if (df["week"].dt.year >= 2024).any() or df["week"].max() > SAMPLE_END:
        raise RuntimeError("merged frame exceeds sample")
    gaps = df["week"].diff().dt.days
    if (gaps.dropna() != 7).any():
        raise RuntimeError("weeks are not a regular Friday series; 4w chain invalid")
    r4 = pd.to_numeric(df["future_return_4w"], errors="coerce").to_numpy(dtype=float)
    r12 = pd.to_numeric(df["future_return_12w"], errors="coerce").to_numpy(dtype=float)
    w04 = window_return(r4, 0, 4)
    w012 = window_return(r4, 0, 12)
    if np.nanmax(np.abs(w04 - r4)) > 1e-12:
        raise RuntimeError("L=0 H=4 window does not match catalog future_return_4w")
    both = np.isfinite(w012) & np.isfinite(r12)
    if int(both.sum()) == 0 or np.nanmax(np.abs(w012[both] - r12[both])) > 1e-10:
        raise RuntimeError("L=0 H=12 window does not match catalog future_return_12w")
    for L in LAGS:
        for H in HORIZONS:
            ret = window_return(r4, L, H)
            df[f"ret_L{L}_H{H}"] = ret
            df[f"y_L{L}_H{H}"] = np.where(np.isfinite(ret), (ret > 0).astype(float), np.nan)
            df[f"ok_L{L}_H{H}"] = np.isfinite(ret)
    return df


def logit_fit_predict(X_train: np.ndarray, y_train: np.ndarray, x_t: np.ndarray) -> float:
    y = y_train.astype(int)
    if y.min() == y.max():
        return float(np.clip(float(y[0]), CLIP, 1.0 - CLIP))
    med = np.nanmedian(X_train, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    X = np.where(np.isfinite(X_train), X_train, med)
    xt = np.where(np.isfinite(x_t), x_t, med).reshape(1, -1)
    scaler = StandardScaler()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Xs = scaler.fit_transform(X)
        xts = scaler.transform(xt)
    clf = LogisticRegression(
        penalty="l2",
        C=LOGIT_C,
        solver="lbfgs",
        max_iter=2000,
        random_state=0,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        clf.fit(Xs, y)
    classes = list(clf.classes_)
    proba = clf.predict_proba(xts)[0]
    p = float(proba[classes.index(1)]) if 1 in classes else 0.0
    return float(np.clip(p, CLIP, 1.0 - CLIP))


def walkforward(df: pd.DataFrame, y: np.ndarray, maturity: int) -> dict[str, np.ndarray]:
    n = len(df)
    y_ok = np.isfinite(y)
    X = df[FEATURES].to_numpy(dtype=float)
    p0 = np.full(n, np.nan)
    p1 = np.full(n, np.nan)
    ntr = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    for t in range(n):
        if not y_ok[t]:
            continue
        end = t - maturity
        if end < 0:
            continue
        train = np.zeros(n, dtype=bool)
        train[: end + 1] = True
        train &= y_ok
        nt = int(train.sum())
        ntr[t] = nt
        if nt < MIN_TRAIN:
            continue
        ytr = y[train]
        p0[t] = float(ytr.mean())
        p1[t] = logit_fit_predict(X[train], ytr, X[t])
        enough[t] = True
    return {"M0": p0, "M_MACRO": p1, "n_train": ntr, "enough": enough}


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    y = y[m].astype(int)
    p = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    n = int(len(y))
    rec = {
        "N": n,
        "prevalence": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
        "auc": np.nan,
        "balanced_accuracy": np.nan,
    }
    if n == 0:
        return rec
    yhat = (p >= 0.5).astype(int)
    n_pos = int(y.sum())
    rec["prevalence"] = float(y.mean())
    rec["brier"] = float(brier_score_loss(y, p))
    rec["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    if 0 < n_pos < n:
        rec["auc"] = float(roc_auc_score(y, p))
        rec["balanced_accuracy"] = float(balanced_accuracy_score(y, yhat))
    return rec


def bss(brier: float, base: float) -> float:
    if np.isfinite(brier) and np.isfinite(base) and base > 0:
        return 1.0 - brier / base
    return np.nan


def period_sel(weeks: pd.Series, enough: np.ndarray, period: str) -> np.ndarray:
    ok = enough.copy()
    if period == TEMPORAL_PERIOD:
        ok &= weeks >= VAL_START
    elif period != FULL_PERIOD:
        raise ValueError(period)
    return ok


def nonoverlap(
    y: np.ndarray, p_m: np.ndarray, p0: np.ndarray, enough: np.ndarray, step: int
) -> dict:
    """Non-overlapping H-week outcome windows: stride = H, H offsets."""
    idx = np.arange(len(y))
    skills = []
    offsets = []
    for off in range(step):
        sel = enough & ((idx - off) % step == 0)
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skill = bss(st_m["brier"], st_0["brier"])
        skills.append(skill)
        offsets.append(
            {
                "offset": off,
                "N": st_m["N"],
                "brier": st_m["brier"],
                "brier_m0": st_0["brier"],
                "bss": skill,
            }
        )
    arr = np.asarray(skills, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {
            "bss_median": np.nan,
            "bss_min": np.nan,
            "bss_max": np.nan,
            "n_pos": 0,
            "n_off": int(step),
            "offsets": offsets,
        }
    return {
        "bss_median": float(np.median(finite)),
        "bss_min": float(np.min(finite)),
        "bss_max": float(np.max(finite)),
        "n_pos": int(np.sum(finite > 0)),
        "n_off": int(finite.size),
        "offsets": offsets,
    }


def empty_nov() -> dict:
    return {
        "bss_median": np.nan,
        "bss_min": np.nan,
        "bss_max": np.nan,
        "n_offsets_bss_gt0": np.nan,
        "n_offsets": np.nan,
        "brier_m0": np.nan,
    }


def metric_row(lag, horizon, model, period, stats, base_brier, **extra) -> dict:
    rec = {
        "lag_weeks": int(lag),
        "horizon_weeks": int(horizon),
        "model": model,
        "period": period,
        "N": stats["N"],
        "prevalence": stats["prevalence"],
        "brier": stats["brier"],
        "brier_skill_vs_M0": 0.0 if model == "M0" else bss(stats["brier"], base_brier),
        "log_loss": stats["log_loss"],
        "auc": stats["auc"],
        "balanced_accuracy": stats["balanced_accuracy"],
    }
    rec.update(empty_nov())
    rec.update(extra)
    return rec


def fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def lookup(metrics: pd.DataFrame, lag, horizon, model, period) -> dict | None:
    q = metrics[
        (metrics["lag_weeks"] == lag)
        & (metrics["horizon_weeks"] == horizon)
        & (metrics["model"] == model)
        & (metrics["period"] == period)
    ]
    if q.empty:
        return None
    return q.iloc[0].to_dict()


def beats_m0(row: dict | None) -> bool:
    if row is None or int(row.get("N") or 0) == 0:
        return False
    s = row.get("brier_skill_vs_M0")
    return bool(np.isfinite(s) and s > 0)


def ranking_without_brier(row: dict | None) -> bool:
    if row is None:
        return False
    auc = row.get("auc")
    skill = row.get("brier_skill_vs_M0")
    return bool(np.isfinite(auc) and auc >= 0.60 and np.isfinite(skill) and skill < 0)


def classify(full: dict | None, val: dict | None, nov: dict | None) -> str:
    full_ok = beats_m0(full)
    val_ok = beats_m0(val)
    if nov is None:
        nov_ok = False
    else:
        med = nov.get("bss_median")
        npos = int(nov.get("n_offsets_bss_gt0") or 0)
        noff = int(nov.get("n_offsets") or 0)
        nov_ok = bool(np.isfinite(med) and med > 0 and noff > 0 and npos * 2 >= noff)
    if full_ok and val_ok and nov_ok:
        return "PROMISING"
    if full_ok or val_ok:
        return "WEAK"
    return "NO EDGE"


def write_report(df: pd.DataFrame, metrics: pd.DataFrame) -> None:
    def L(lag, h, m, p):
        return lookup(metrics, lag, h, m, p)

    def line(lag, h, m, p) -> str:
        r = L(lag, h, m, p)
        if r is None:
            return f"| {m} | — |"
        return (
            f"| {m} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['brier'], 4)} | "
            f"{fmt(r['brier_skill_vs_M0'], 3)} | {fmt(r['log_loss'], 4)} | "
            f"{fmt(r['auc'], 3)} | {fmt(r['balanced_accuracy'], 3)} |"
        )

    hdr = "| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"
    labels = {}
    for lag in LAGS:
        for h in HORIZONS:
            full = L(lag, h, "M_MACRO", FULL_PERIOD)
            val = L(lag, h, "M_MACRO", TEMPORAL_PERIOD)
            nov = L(lag, h, "M_MACRO", "NONOVERLAP_SUMMARY")
            labels[(lag, h)] = classify(full, val, nov)

    lines = []
    lines.append("# H2 — Macro lag diagnostic")
    lines.append("")
    lines.append("Question: is the frozen four-feature macro block at week t more useful for crypto returns that start immediately, after 4 weeks, or after 8 weeks?")
    lines.append("")
    lines.append("No crypto features. No extra lags. No extra horizons. No 2024–2026. Not a trading backtest. Not an A/B/C model verdict. This is not a lag *search*: the grid is pre-specified.")
    lines.append("")
    lines.append("Outcome window: exclusive `t+L+1 … t+L+H`. Target: return > 0.")
    lines.append("Train: `s <= t - (L+H)`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.")
    lines.append("Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.")
    lines.append("Windows chained from catalog `future_return_4w`. 2021–2023 is **TEMPORAL_ROBUSTNESS_2021_2023**, not clean OOS.")
    lines.append("")
    lines.append("Classification:")
    lines.append("")
    lines.append("- PROMISING: BSS>0 on full expanding WF **and** 2021–2023, and non-overlapping median BSS>0 with at least half of offsets BSS>0.")
    lines.append("- WEAK: BSS>0 on full **or** 2021–2023, but not both, or both but non-overlap fails.")
    lines.append("- NO EDGE: BSS≤0 on full **and** 2021–2023.")
    lines.append("- If AUC≥0.60 and BSS<0: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST.")
    lines.append("")
    lines.append("## Sample")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| merged weeks | {len(df)} |")
    lines.append(f"| last week | {df['week'].max().strftime('%Y-%m-%d')} |")
    lines.append("| 2024+ | none |")
    for lag in LAGS:
        for h in HORIZONS:
            lines.append(
                f"| complete L={lag} H={h} outcomes | {int(df[f'ok_L{lag}_H{h}'].sum())} |"
            )
    lines.append("| common eval set | M0 and M_MACRO scored on the same mature weeks per cell |")
    lines.append("")
    lines.append("## Classification grid")
    lines.append("")
    lines.append("| L \\ H | 4w | 8w | 12w |")
    lines.append("|---:|---|---|---|")
    for lag in LAGS:
        cells = " | ".join(labels[(lag, h)] for h in HORIZONS)
        lines.append(f"| {lag} | {cells} |")
    lines.append("")
    lines.append("## BSS grid — full expanding walk-forward")
    lines.append("")
    lines.append("| L \\ H | 4w | 8w | 12w |")
    lines.append("|---:|---:|---:|---:|")
    for lag in LAGS:
        cells = " | ".join(
            fmt(L(lag, h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"], 3) for h in HORIZONS
        )
        lines.append(f"| {lag} | {cells} |")
    lines.append("")
    lines.append("## BSS grid — TEMPORAL_ROBUSTNESS_2021_2023")
    lines.append("")
    lines.append("| L \\ H | 4w | 8w | 12w |")
    lines.append("|---:|---:|---:|---:|")
    for lag in LAGS:
        cells = " | ".join(
            fmt(L(lag, h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"], 3) for h in HORIZONS
        )
        lines.append(f"| {lag} | {cells} |")
    lines.append("")

    for lag in LAGS:
        for h in HORIZONS:
            lines.append(f"## L={lag}, H={h} — window t+{lag}+1 … t+{lag}+{h}")
            lines.append("")
            lines.append("### Full expanding walk-forward")
            lines.append("")
            lines.append("\n".join([hdr, sep, line(lag, h, "M0", FULL_PERIOD), line(lag, h, "M_MACRO", FULL_PERIOD)]))
            lines.append("")
            lines.append("### TEMPORAL_ROBUSTNESS_2021_2023")
            lines.append("")
            lines.append("\n".join([hdr, sep, line(lag, h, "M0", TEMPORAL_PERIOD), line(lag, h, "M_MACRO", TEMPORAL_PERIOD)]))
            lines.append("")
            nov = L(lag, h, "M_MACRO", "NONOVERLAP_SUMMARY")
            cls = labels[(lag, h)]
            lines.append(f"### Non-overlapping {h}-week offsets (full walk-forward)")
            lines.append("")
            if nov is None or int(nov.get("n_offsets") or 0) == 0:
                lines.append("No offsets.")
            else:
                lines.append(
                    f"Median BSS={fmt(nov['bss_median'], 3)}; min={fmt(nov['bss_min'], 3)}; "
                    f"max={fmt(nov['bss_max'], 3)}; offsets BSS>0: "
                    f"{int(nov['n_offsets_bss_gt0'])}/{int(nov['n_offsets'])}. Class: {cls}."
                )
            full = L(lag, h, "M_MACRO", FULL_PERIOD)
            val = L(lag, h, "M_MACRO", TEMPORAL_PERIOD)
            notes = []
            if ranking_without_brier(full):
                notes.append("full WF: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST")
            if ranking_without_brier(val):
                notes.append("2021–2023: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST")
            for n in notes:
                lines.append(f"- {n}")
            lines.append("")
            off = metrics[
                (metrics["lag_weeks"] == lag)
                & (metrics["horizon_weeks"] == h)
                & (metrics["model"] == "M_MACRO")
                & metrics["period"].astype(str).str.startswith("NONOVERLAP_OFF")
            ].sort_values("period")
            if not off.empty:
                lines.append("| offset | N | brier | brier M0 | BSS |")
                lines.append("|---:|---:|---:|---:|---:|")
                for _, r in off.iterrows():
                    lines.append(
                        f"| {str(r['period']).replace('NONOVERLAP_OFF', '')} | {int(r['N'])} | "
                        f"{fmt(r['brier'], 4)} | {fmt(r['brier_m0'], 4)} | {fmt(r['brier_skill_vs_M0'], 3)} |"
                    )
                lines.append("")

    lines.append("## Answers")
    lines.append("")
    n_prom = sum(1 for v in labels.values() if v == "PROMISING")
    n_weak = sum(1 for v in labels.values() if v == "WEAK")
    n_none = sum(1 for v in labels.values() if v == "NO EDGE")
    lines.append(
        f"Grid: {n_prom} PROMISING, {n_weak} WEAK, {n_none} NO EDGE out of {len(labels)} cells."
    )
    lines.append("")

    def beat_txt(lag, h):
        full = L(lag, h, "M_MACRO", FULL_PERIOD)
        val = L(lag, h, "M_MACRO", TEMPORAL_PERIOD)
        return (
            f"Full BSS>0: {beats_m0(full)} ({fmt(full['brier_skill_vs_M0'], 3)}). "
            f"TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: {beats_m0(val)} "
            f"({fmt(val['brier_skill_vs_M0'], 3)}). Class: {labels[(lag, h)]}."
        )

    q = 1
    for h in HORIZONS:
        for lag in LAGS:
            lines.append(f"{q}. L={lag}, H={h}: does M_MACRO beat M0? {beat_txt(lag, h)}")
            q += 1
    lines.append("")

    # Delayed vs contemporaneous: compare 2021-2023 and full BSS at same H
    lines.append("10. Does delayed macro (L=4 or L=8) beat contemporaneous macro (L=0) at the same H?")
    for h in HORIZONS:
        bits = []
        for lag in (4, 8):
            d_full = (
                L(lag, h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"]
                - L(0, h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"]
            )
            d_val = (
                L(lag, h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"]
                - L(0, h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"]
            )
            bits.append(
                f"L={lag} vs L=0: ΔBSS full={fmt(d_full, 3)}, ΔBSS 2021–2023={fmt(d_val, 3)} "
                f"(positive means delayed is better)"
            )
        lines.append(f"   - H={h}: " + "; ".join(bits))
    lines.append("")

    survive = []
    for lag in LAGS:
        for h in HORIZONS:
            nov = L(lag, h, "M_MACRO", "NONOVERLAP_SUMMARY")
            full = L(lag, h, "M_MACRO", FULL_PERIOD)
            val = L(lag, h, "M_MACRO", TEMPORAL_PERIOD)
            med = nov["bss_median"] if nov else np.nan
            npos = int(nov["n_offsets_bss_gt0"] or 0) if nov else 0
            noff = int(nov["n_offsets"] or 0) if nov else 0
            ok = bool(
                (beats_m0(full) or beats_m0(val))
                and np.isfinite(med)
                and med > 0
                and noff > 0
                and npos * 2 >= noff
            )
            survive.append((lag, h, ok, med, npos, noff))
    any_ok = any(x[2] for x in survive)
    lines.append("11. Does any lag/horizon survive the non-overlapping check?")
    if not any_ok:
        lines.append("    No. No cell clears majority-and-median BSS>0 together with a positive skill window.")
    else:
        lines.append("    Partially:")
    for lag, h, ok, med, npos, noff in survive:
        lines.append(
            f"    - L={lag} H={h}: median BSS={fmt(med, 3)}, {npos}/{noff} offsets BSS>0, survive={ok}"
        )
    lines.append("")

    delayed_helps = False
    delayed_hurts = False
    for h in HORIZONS:
        b0 = L(0, h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"]
        for lag in (4, 8):
            b = L(lag, h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"]
            f0 = L(0, h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"]
            f = L(lag, h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"]
            if (np.isfinite(b) and np.isfinite(b0) and b > b0) or (
                np.isfinite(f) and np.isfinite(f0) and f > f0
            ):
                delayed_helps = True
            if (np.isfinite(b) and np.isfinite(b0) and b < b0) and (
                np.isfinite(f) and np.isfinite(f0) and f < f0
            ):
                delayed_hurts = True
    if n_prom > 0:
        q12 = "At least one delayed cell is PROMISING on the pre-specified rule. Still not a trading model."
    elif delayed_helps and not any_ok:
        q12 = (
            "Delaying the crypto window does not create a PROMISING cell. "
            "Any 2021–2023 lift at L>0 is the same conditional/period pattern already seen at L=0: "
            "positive temporal BSS, negative full-sample BSS, negative non-overlapping median. "
            "Do not treat a delayed window as a discovered lag."
        )
    elif delayed_hurts:
        q12 = (
            "Delayed windows are not better than L=0. Macro at t is not more informative for crypto "
            "returns that start 4–8 weeks later than for returns that start immediately, under this frozen spec."
        )
    else:
        q12 = "No delayed cell improves on contemporaneous L=0 in a way that changes the class. Do not freeze a lag."
    lines.append("12. Is there evidence that macro works with a delay rather than contemporaneously?")
    lines.append(f"    {q12}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("No A/B/C model verdict. No lag is frozen. Classes are in the grid above.")
    lines.append("Do not pick a 'best' lag from a single pretty metric.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no crypto features")
    lines.append("- no extra lags / horizons / interactions / C search")
    lines.append("- no 2024–2026")
    lines.append("- H1 files not modified")
    lines.append("- Phase 3 / 6A not modified")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "MACRO_LAG_DIAGNOSTIC.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def assert_grid(metrics: pd.DataFrame) -> None:
    lags = set(int(x) for x in metrics["lag_weeks"].dropna().unique())
    hors = set(int(x) for x in metrics["horizon_weeks"].dropna().unique())
    if lags != {0, 4, 8}:
        raise RuntimeError(f"CSV lag_weeks={lags}, expected {{0,4,8}}")
    if hors != {4, 8, 12}:
        raise RuntimeError(f"CSV horizon_weeks={hors}, expected {{4,8,12}}")
    for L in LAGS:
        for H in HORIZONS:
            n = int(
                (
                    (metrics["lag_weeks"] == L)
                    & (metrics["horizon_weeks"] == H)
                    & (metrics["model"] == "M_MACRO")
                    & (metrics["period"] == FULL_PERIOD)
                ).sum()
            )
            if n != 1:
                raise RuntimeError(f"missing full-WF row for L={L} H={H}")


def main() -> None:
    df = load_frame()
    weeks = df["week"]
    rows: list[dict] = []
    for L in LAGS:
        for H in HORIZONS:
            y = df[f"y_L{L}_H{H}"].to_numpy(dtype=float)
            maturity = L + H
            wf = walkforward(df, y, maturity)
            enough = wf["enough"]
            if int(enough.sum()) == 0:
                raise RuntimeError(f"L={L} H={H}: no eligible weeks")
            for name in ("M0", "M_MACRO"):
                miss = ~np.isfinite(wf[name]) & enough
                if miss.any():
                    raise RuntimeError(f"L={L} H={H} {name}: missing predictions on common set")

            for period in (FULL_PERIOD, TEMPORAL_PERIOD):
                sel = period_sel(weeks, enough, period)
                st0 = score_block(y[sel], wf["M0"][sel])
                st1 = score_block(y[sel], wf["M_MACRO"][sel])
                if st0["N"] != st1["N"]:
                    raise RuntimeError(
                        f"sample mismatch L={L} H={H} {period}: M0 {st0['N']} vs MACRO {st1['N']}"
                    )
                extra = {}
                if period == FULL_PERIOD:
                    nov = nonoverlap(y, wf["M_MACRO"], wf["M0"], enough, H)
                    extra = {
                        "bss_median": nov["bss_median"],
                        "bss_min": nov["bss_min"],
                        "bss_max": nov["bss_max"],
                        "n_offsets_bss_gt0": nov["n_pos"],
                        "n_offsets": nov["n_off"],
                    }
                rows.append(metric_row(L, H, "M0", period, st0, st0["brier"]))
                rows.append(metric_row(L, H, "M_MACRO", period, st1, st0["brier"], **extra))

            nov = nonoverlap(y, wf["M_MACRO"], wf["M0"], enough, H)
            for off in nov["offsets"]:
                rows.append(
                    metric_row(
                        L,
                        H,
                        "M_MACRO",
                        f"NONOVERLAP_OFF{off['offset']:02d}",
                        {
                            "N": off["N"],
                            "prevalence": np.nan,
                            "brier": off["brier"],
                            "log_loss": np.nan,
                            "auc": np.nan,
                            "balanced_accuracy": np.nan,
                        },
                        off["brier_m0"],
                        brier_m0=off["brier_m0"],
                    )
                )
            rows.append(
                metric_row(
                    L,
                    H,
                    "M_MACRO",
                    "NONOVERLAP_SUMMARY",
                    {
                        "N": nov["n_off"],
                        "prevalence": np.nan,
                        "brier": np.nan,
                        "log_loss": np.nan,
                        "auc": np.nan,
                        "balanced_accuracy": np.nan,
                    },
                    np.nan,
                    bss_median=nov["bss_median"],
                    bss_min=nov["bss_min"],
                    bss_max=nov["bss_max"],
                    n_offsets_bss_gt0=nov["n_pos"],
                    n_offsets=nov["n_off"],
                )
            )
            rows[-1]["brier_skill_vs_M0"] = nov["bss_median"]

    metrics = pd.DataFrame(rows)
    col_order = [
        "lag_weeks",
        "horizon_weeks",
        "model",
        "period",
        "N",
        "prevalence",
        "brier",
        "brier_skill_vs_M0",
        "log_loss",
        "auc",
        "balanced_accuracy",
        "bss_median",
        "bss_min",
        "bss_max",
        "n_offsets_bss_gt0",
        "n_offsets",
        "brier_m0",
    ]
    metrics = metrics[col_order]
    assert_grid(metrics)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_csv = RESULTS / "macro_lag_metrics.csv"
    metrics.to_csv(out_csv, index=False)
    write_report(df, metrics)
    print(f"wrote {out_csv} rows={len(metrics)}")
    print(f"wrote {RESULTS / 'MACRO_LAG_DIAGNOSTIC.md'}")
    print("lag_weeks", sorted(set(int(x) for x in metrics["lag_weeks"].unique())))
    print("horizon_weeks", sorted(set(int(x) for x in metrics["horizon_weeks"].unique())))
    for L in LAGS:
        for H in HORIZONS:
            full = lookup(metrics, L, H, "M_MACRO", FULL_PERIOD)
            val = lookup(metrics, L, H, "M_MACRO", TEMPORAL_PERIOD)
            nov = lookup(metrics, L, H, "M_MACRO", "NONOVERLAP_SUMMARY")
            print(f"L={L} H={H}", classify(full, val, nov), "N", int(full["N"]))


if __name__ == "__main__":
    main()
