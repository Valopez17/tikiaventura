#!/usr/bin/env python3
"""H1: CRYPTO vs MACRO expanding walk-forward at 4w / 8w / 12w.

Frozen feature sets. No combined model. No search. No 2024–2026.
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
PHASE4_CSV = RQF / "phase4_bull_quality_fragility" / "results" / "bull_quality_weekly.csv"

SAMPLE_END = pd.Timestamp("2023-12-29")
VAL_START = pd.Timestamp("2021-01-01")
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
HORIZONS = (4, 8, 12)
FULL_PERIOD = "FULL_EXPANDING_WF"
TEMPORAL_PERIOD = "TEMPORAL_ROBUSTNESS_2021_2023"

CRYPTO_FEATURES = [
    "MOM_12W_PERCENTILE",
    "MOM4_CHANGE_4W",
    "MOM12_CHANGE_4W",
    "BROAD_BREADTH_CHANGE_4W",
    "TURNOVER_RELATIVE",
    "VOL_PERCENTILE",
]
MACRO_FEATURES = [
    "DXY_CHG_12W",
    "US2Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "NASDAQ_RET_12W",
]
MODELS = {
    "M_CRYPTO": CRYPTO_FEATURES,
    "M_MACRO": MACRO_FEATURES,
}


def add_dynamics(df: pd.DataFrame) -> pd.DataFrame:
    """Same 4-week change formula as Phase 4 / 5 / 6D. Applied on the full catalog."""
    out = df.copy()
    lag = 4
    out["MOM4_CHANGE_4W"] = out["MOM_4W"] - out["MOM_4W"].shift(lag)
    out["MOM12_CHANGE_4W"] = out["MOM_12W"] - out["MOM_12W"].shift(lag)
    out["BROAD_BREADTH_CHANGE_4W"] = (
        out["broad_breadth_4w"] - out["broad_breadth_4w"].shift(lag)
    )
    return out


def add_future_8w(df: pd.DataFrame) -> pd.DataFrame:
    """Exclusive t+1…t+8 from catalog 4w compounds. No new crypto data."""
    out = df.copy()
    r4 = pd.to_numeric(out["future_return_4w"], errors="coerce").to_numpy(dtype=float)
    r8 = np.full(len(out), np.nan, dtype=float)
    for i in range(len(out) - 4):
        a, b = r4[i], r4[i + 4]
        if np.isfinite(a) and np.isfinite(b):
            r8[i] = (1.0 + a) * (1.0 + b) - 1.0
    out["future_return_8w"] = r8
    return out


def load_frame() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG_CSV, parse_dates=["week"])
    mac = pd.read_csv(MACRO_CSV, parse_dates=["week"])
    p4 = pd.read_csv(PHASE4_CSV, parse_dates=["week"])
    for name, d in ("catalog", cat), ("macro", mac), ("phase4", p4):
        if d["week"].duplicated().any():
            raise RuntimeError(f"duplicated weeks in {name}")
        if (d["week"].dt.year >= 2024).any() or d["week"].max() > SAMPLE_END:
            raise RuntimeError(f"2024+ or past sample end in {name}")
    cat = cat.loc[cat["week"] <= SAMPLE_END].copy().sort_values("week")
    mac = mac.loc[mac["week"] <= SAMPLE_END].copy()
    p4 = p4.loc[p4["week"] <= SAMPLE_END].copy()
    miss_mac = [c for c in MACRO_FEATURES if c not in mac.columns]
    if miss_mac:
        raise RuntimeError(f"macro missing {miss_mac}")
    needed = (
        "MOM_4W",
        "MOM_12W",
        "MOM_12W_PERCENTILE",
        "broad_breadth_4w",
        "TURNOVER_RELATIVE",
        "VOL_PERCENTILE",
        "future_return_4w",
        "future_return_12w",
    )
    for col in needed:
        if col not in cat.columns:
            raise RuntimeError(f"catalog missing {col}")

    df = add_dynamics(cat)
    p4_dyn = [
        c
        for c in ("MOM4_CHANGE_4W", "MOM12_CHANGE_4W", "BROAD_BREADTH_CHANGE_4W")
        if c in p4.columns
    ]
    df = df.merge(p4[["week"] + p4_dyn], on="week", how="left", suffixes=("", "_p4"))
    for c in p4_dyn:
        pc = f"{c}_p4"
        if pc in df.columns:
            df[c] = df[pc].combine_first(df[c])
            df.drop(columns=[pc], inplace=True)

    df = df.merge(mac[["week"] + MACRO_FEATURES], on="week", how="inner", validate="one_to_one")
    df = df.sort_values("week").reset_index(drop=True)
    if (df["week"].dt.year >= 2024).any() or df["week"].max() > SAMPLE_END:
        raise RuntimeError("merged frame exceeds sample")
    df = add_future_8w(df)
    gaps = df["week"].diff().dt.days
    if (gaps.dropna() != 7).any():
        raise RuntimeError("catalog weeks are not a regular Friday series; 8w chain invalid")
    for h in HORIZONS:
        r = pd.to_numeric(df[f"future_return_{h}w"], errors="coerce")
        df[f"y_{h}"] = np.where(np.isfinite(r), (r > 0).astype(float), np.nan)
        df[f"ok_{h}"] = np.isfinite(r)
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


def walkforward(df: pd.DataFrame, y: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    n = len(df)
    y_ok = np.isfinite(y)
    X = {name: df[cols].to_numpy(dtype=float) for name, cols in MODELS.items()}
    out = {name: np.full(n, np.nan) for name in ["M0", *MODELS]}
    ntr = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    for t in range(n):
        if not y_ok[t]:
            continue
        end = t - horizon
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
        out["M0"][t] = float(ytr.mean())
        for name, mat in X.items():
            out[name][t] = logit_fit_predict(mat[train], ytr, mat[t])
        enough[t] = True
    out["n_train"] = ntr
    out["enough"] = enough
    return out


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
    y: np.ndarray, p_m: np.ndarray, p0: np.ndarray, enough: np.ndarray, horizon: int
) -> dict:
    idx = np.arange(len(y))
    skills = []
    offsets = []
    for off in range(horizon):
        sel = enough & ((idx - off) % horizon == 0)
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
            "n_off": int(horizon),
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


def metric_row(horizon, model, period, stats, base_brier, **extra) -> dict:
    rec = {
        "horizon": int(horizon),
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


def lookup(metrics: pd.DataFrame, horizon, model, period) -> dict | None:
    q = metrics[
        (metrics["horizon"] == horizon)
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


def strongest_source(h: int, metrics: pd.DataFrame) -> str:
    c_full = lookup(metrics, h, "M_CRYPTO", FULL_PERIOD)
    m_full = lookup(metrics, h, "M_MACRO", FULL_PERIOD)
    c_val = lookup(metrics, h, "M_CRYPTO", TEMPORAL_PERIOD)
    m_val = lookup(metrics, h, "M_MACRO", TEMPORAL_PERIOD)
    c_cls = classify(c_full, c_val, lookup(metrics, h, "M_CRYPTO", "NONOVERLAP_SUMMARY"))
    m_cls = classify(m_full, m_val, lookup(metrics, h, "M_MACRO", "NONOVERLAP_SUMMARY"))
    rank = {"NO EDGE": 0, "WEAK": 1, "PROMISING": 2}
    if rank[m_cls] > rank[c_cls]:
        return f"MACRO ({m_cls}) over CRYPTO ({c_cls})"
    if rank[c_cls] > rank[m_cls]:
        return f"CRYPTO ({c_cls}) over MACRO ({m_cls})"
    c_bss = c_val["brier_skill_vs_M0"] if c_val else np.nan
    m_bss = m_val["brier_skill_vs_M0"] if m_val else np.nan
    if c_cls == "NO EDGE" and m_cls == "NO EDGE":
        return (
            f"neither beats M0 (both {c_cls}). "
            f"2021–2023 BSS CRYPTO={fmt(c_bss, 3)}, MACRO={fmt(m_bss, 3)} — do not treat the less-bad Brier as an edge."
        )
    if np.isfinite(m_bss) and np.isfinite(c_bss) and m_bss > c_bss:
        return f"tie on class ({c_cls}); MACRO has higher 2021–2023 BSS ({fmt(m_bss, 3)} vs {fmt(c_bss, 3)})"
    if np.isfinite(c_bss) and np.isfinite(m_bss) and c_bss > m_bss:
        return f"tie on class ({c_cls}); CRYPTO has higher 2021–2023 BSS ({fmt(c_bss, 3)} vs {fmt(m_bss, 3)})"
    return f"tie ({c_cls}); 2021–2023 BSS indistinguishable"


def monotonicity(metrics: pd.DataFrame, model: str) -> str:
    bss_full = []
    bss_val = []
    for h in HORIZONS:
        f = lookup(metrics, h, model, FULL_PERIOD)
        v = lookup(metrics, h, model, TEMPORAL_PERIOD)
        bss_full.append(np.nan if f is None else f["brier_skill_vs_M0"])
        bss_val.append(np.nan if v is None else v["brier_skill_vs_M0"])

    def pattern(vals: list[float], label: str) -> str:
        if not all(np.isfinite(v) for v in vals):
            return f"{label}: incomplete"
        a, b, c = vals
        if a < b < c:
            return f"{label}: improves as horizon lengthens (4→8→12)"
        if a > b > c:
            return f"{label}: degrades as horizon lengthens (4→8→12)"
        return (
            f"{label}: not monotonic "
            f"(4w={fmt(a, 3)}, 8w={fmt(b, 3)}, 12w={fmt(c, 3)})"
        )

    return f"{pattern(bss_full, 'full BSS')}; {pattern(bss_val, '2021–2023 BSS')}"


def write_report(df: pd.DataFrame, metrics: pd.DataFrame) -> None:
    def L(h, m, p):
        return lookup(metrics, h, m, p)

    def line(h, m, p) -> str:
        r = L(h, m, p)
        if r is None:
            return f"| {m} | — |"
        return (
            f"| {m} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['brier'], 4)} | "
            f"{fmt(r['brier_skill_vs_M0'], 3)} | {fmt(r['log_loss'], 4)} | "
            f"{fmt(r['auc'], 3)} | {fmt(r['balanced_accuracy'], 3)} |"
        )

    hdr = "| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"

    def table(h, p):
        return "\n".join([hdr, sep] + [line(h, m, p) for m in ("M0", "M_CRYPTO", "M_MACRO")])

    labels = {}
    notes = {}
    for h in HORIZONS:
        for m in ("M_CRYPTO", "M_MACRO"):
            full = L(h, m, FULL_PERIOD)
            val = L(h, m, TEMPORAL_PERIOD)
            nov = L(h, m, "NONOVERLAP_SUMMARY")
            labels[(h, m)] = classify(full, val, nov)
            bits = []
            if ranking_without_brier(full):
                bits.append("full WF: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST")
            if ranking_without_brier(val):
                bits.append("2021–2023: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST")
            notes[(h, m)] = bits

    lines = []
    lines.append("# H1 — Horizon diagnostic (CRYPTO vs MACRO at 4w / 8w / 12w)")
    lines.append("")
    lines.append("Question: does frozen crypto-only or frozen macro-only information improve the probability that the subsequent H-week market return is positive, versus an expanding mature base rate, and does that pattern change with horizon?")
    lines.append("")
    lines.append("No combined model. No feature search. No lag search. No regime slices. No 2024–2026. Not a trading backtest. Not a model A/B/C verdict.")
    lines.append("")
    lines.append("Mature labels: train `s <= t - H`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.")
    lines.append("")
    lines.append("M_CRYPTO: `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE`.")
    lines.append("M_MACRO: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.")
    lines.append("Same features at every horizon.")
    lines.append("")
    lines.append("Only target: `Y_H = 1` if `future_return_Hw > 0`.")
    lines.append("")
    lines.append("`future_return_8w` is derived from catalog `future_return_4w` as `(1+r4_t)*(1+r4_{t+4})-1` (exclusive t+1…t+8). No new crypto download.")
    lines.append("")
    lines.append("2021–2023 is labeled **TEMPORAL_ROBUSTNESS_2021_2023**. It is not clean OOS. Prior phases already inspected this window.")
    lines.append("")
    lines.append("Classification (no A/B/C):")
    lines.append("")
    lines.append("- PROMISING: BSS>0 on full expanding WF **and** 2021–2023, and non-overlapping median BSS>0 with at least half of offsets BSS>0.")
    lines.append("- WEAK: BSS>0 on full **or** 2021–2023, but not both, or both but the non-overlapping layer fails.")
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
    for h in HORIZONS:
        lines.append(f"| complete {h}w outcomes | {int(df[f'ok_{h}'].sum())} |")
    lines.append("| crypto dynamics | Phase 4 formula on the catalog; Phase 4 values overlaid on Bull weeks |")
    lines.append("| common eval set | M0 / M_CRYPTO / M_MACRO scored on the same mature weeks per horizon |")
    lines.append("")

    for h in HORIZONS:
        lines.append(f"## Horizon {h}w — `future_return_{h}w > 0`")
        lines.append("")
        lines.append("### Full expanding walk-forward")
        lines.append("")
        lines.append(table(h, FULL_PERIOD))
        lines.append("")
        lines.append("### TEMPORAL_ROBUSTNESS_2021_2023")
        lines.append("")
        lines.append(table(h, TEMPORAL_PERIOD))
        lines.append("")
        lines.append(f"### Non-overlapping {h}-week offsets (full walk-forward)")
        lines.append("")
        lines.append("| model | offsets | median BSS | min | max | offsets BSS>0 | class |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for m in ("M_CRYPTO", "M_MACRO"):
            r = L(h, m, "NONOVERLAP_SUMMARY")
            cls = labels[(h, m)]
            if r is None or int(r.get("n_offsets") or 0) == 0:
                lines.append(f"| {m} | — | NA | NA | NA | — | {cls} |")
            else:
                lines.append(
                    f"| {m} | {int(r['n_offsets'])} | {fmt(r['bss_median'], 3)} | "
                    f"{fmt(r['bss_min'], 3)} | {fmt(r['bss_max'], 3)} | "
                    f"{int(r['n_offsets_bss_gt0'])}/{int(r['n_offsets'])} | {cls} |"
                )
        lines.append("")
        for m in ("M_CRYPTO", "M_MACRO"):
            off = metrics[
                (metrics["horizon"] == h)
                & (metrics["model"] == m)
                & metrics["period"].astype(str).str.startswith("NONOVERLAP_OFF")
            ].sort_values("period")
            if off.empty:
                continue
            lines.append(f"#### {m} offsets")
            lines.append("")
            lines.append("| offset | N | brier | brier M0 | BSS |")
            lines.append("|---:|---:|---:|---:|---:|")
            for _, r in off.iterrows():
                lines.append(
                    f"| {str(r['period']).replace('NONOVERLAP_OFF', '')} | {int(r['N'])} | "
                    f"{fmt(r['brier'], 4)} | {fmt(r['brier_m0'], 4)} | {fmt(r['brier_skill_vs_M0'], 3)} |"
                )
            lines.append("")
        for m in ("M_CRYPTO", "M_MACRO"):
            for bit in notes[(h, m)]:
                lines.append(f"- {m}: {bit}")
        if any(notes[(h, m)] for m in ("M_CRYPTO", "M_MACRO")):
            lines.append("")

    lines.append("## Classification")
    lines.append("")
    lines.append("| horizon | M_CRYPTO | M_MACRO |")
    lines.append("|---:|---|---|")
    for h in HORIZONS:
        lines.append(f"| {h}w | {labels[(h, 'M_CRYPTO')]} | {labels[(h, 'M_MACRO')]} |")
    lines.append("")

    def beat_txt(h, model):
        full = L(h, model, FULL_PERIOD)
        val = L(h, model, TEMPORAL_PERIOD)
        cls = labels[(h, model)]
        return (
            f"Full BSS>0: {beats_m0(full)} ({fmt(None if full is None else full['brier_skill_vs_M0'], 3)}). "
            f"TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: {beats_m0(val)} "
            f"({fmt(None if val is None else val['brier_skill_vs_M0'], 3)}). "
            f"Class: {cls}."
        )

    lines.append("## Answers")
    lines.append("")
    lines.append(f"1. At 4w, does CRYPTO beat M0? {beat_txt(4, 'M_CRYPTO')}")
    lines.append(f"2. At 4w, does MACRO beat M0? {beat_txt(4, 'M_MACRO')}")
    lines.append(f"3. At 8w, does CRYPTO beat M0? {beat_txt(8, 'M_CRYPTO')}")
    lines.append(f"4. At 8w, does MACRO beat M0? {beat_txt(8, 'M_MACRO')}")
    lines.append(f"5. At 12w, does CRYPTO beat M0? {beat_txt(12, 'M_CRYPTO')}")
    lines.append(f"6. At 12w, does MACRO beat M0? {beat_txt(12, 'M_MACRO')}")
    lines.append("")
    lines.append("7. Which source of information is strongest at each horizon?")
    for h in HORIZONS:
        lines.append(f"   - {h}w: {strongest_source(h, metrics)}")
    lines.append("")
    lines.append("8. Does either model show a monotonic degradation or improvement as horizon increases?")
    lines.append(f"   - M_CRYPTO: {monotonicity(metrics, 'M_CRYPTO')}")
    lines.append(f"   - M_MACRO: {monotonicity(metrics, 'M_MACRO')}")
    lines.append("   No horizon is selected as 'best' from a single pretty metric.")
    lines.append("")

    nov_bits = []
    any_survive = False
    for h in HORIZONS:
        for m in ("M_CRYPTO", "M_MACRO"):
            nov = L(h, m, "NONOVERLAP_SUMMARY")
            full = L(h, m, FULL_PERIOD)
            val = L(h, m, TEMPORAL_PERIOD)
            if nov is None:
                continue
            med = nov.get("bss_median")
            npos = int(nov.get("n_offsets_bss_gt0") or 0)
            noff = int(nov.get("n_offsets") or 0)
            survive = bool(
                (beats_m0(full) or beats_m0(val))
                and np.isfinite(med)
                and med > 0
                and npos * 2 >= noff
            )
            any_survive = any_survive or survive
            nov_bits.append(
                f"{m} {h}w: median BSS={fmt(med, 3)}, {npos}/{noff} offsets BSS>0, "
                f"survives majority-and-median rule: {survive}"
            )
    lines.append("9. Does apparent performance survive the non-overlapping check?")
    if not any_survive:
        lines.append("   No. No horizon/source clears majority-and-median BSS>0 together with a positive skill window.")
    else:
        lines.append("   Partially — see per cell:")
    for b in nov_bits:
        lines.append(f"   - {b}")
    lines.append("")

    c4, c8, c12 = (labels[(h, "M_CRYPTO")] for h in HORIZONS)
    m4, m8, m12 = (labels[(h, "M_MACRO")] for h in HORIZONS)
    c_val_bss = [L(h, "M_CRYPTO", TEMPORAL_PERIOD)["brier_skill_vs_M0"] for h in HORIZONS]
    m_val_bss = [L(h, "M_MACRO", TEMPORAL_PERIOD)["brier_skill_vs_M0"] for h in HORIZONS]
    m_full_bss = [L(h, "M_MACRO", FULL_PERIOD)["brier_skill_vs_M0"] for h in HORIZONS]
    crypto_beats_any = any(c in {"PROMISING", "WEAK"} for c in (c4, c8, c12))
    macro_val_all_pos = all(np.isfinite(x) and x > 0 for x in m_val_bss)
    macro_full_all_neg = all(np.isfinite(x) and x <= 0 for x in m_full_bss)
    if (not crypto_beats_any) and macro_val_all_pos and macro_full_all_neg:
        q10 = (
            "Neither pattern is supported as a horizon effect. "
            "CRYPTO never beats M0 at 4w, 8w, or 12w (NO EDGE). "
            "Its Brier is least bad at 4w; that is not a short-term crypto edge. "
            "MACRO is WEAK at every horizon: 2021–2023 BSS is positive at 4w, 8w, and 12w, "
            "while full-sample BSS and non-overlapping median BSS are negative at every horizon. "
            "That is a 2021–2023 period effect, not evidence that macro works better at medium term."
        )
    elif (not crypto_beats_any) and rank_better(m12, m4) and m12 in {"PROMISING", "WEAK"}:
        q10 = (
            "Crypto-better-short-term is not supported (CRYPTO is NO EDGE at every horizon). "
            "Macro class is stronger at longer horizons than at 4w, but that is not PROMISING "
            "unless full WF and non-overlap also clear — they do not."
        )
    else:
        q10 = (
            "Neither pattern is supported. Frozen crypto does not beat M0 at short horizon "
            "with robustness. Frozen macro does not establish a clean medium-term edge "
            "across full WF, 2021–2023, and non-overlapping offsets together."
        )
    lines.append("10. Is there evidence that crypto works better short-term, macro works better medium-term, or neither pattern is supported?")
    lines.append(f"    {q10}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("No A/B/C model verdict. Horizon/source classes are in the table above.")
    lines.append("Do not freeze a candidate from this diagnostic alone.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no combined Crypto+Macro model")
    lines.append("- no lag search / interactions / extra features / extra targets")
    lines.append("- no Bull/Bear slices")
    lines.append("- no 2024–2026")
    lines.append("- Phase 3 / 4 / 6A not modified")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "HORIZON_DIAGNOSTIC.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def rank_better(a: str, b: str) -> bool:
    order = {"NO EDGE": 0, "WEAK": 1, "PROMISING": 2}
    return order[a] > order[b]


def main() -> None:
    df = load_frame()
    weeks = df["week"]
    all_feat = CRYPTO_FEATURES + MACRO_FEATURES
    rows: list[dict] = []
    for h in HORIZONS:
        y = df[f"y_{h}"].to_numpy(dtype=float)
        wf = walkforward(df, y, h)
        enough = wf["enough"]
        # Fairness: same weeks for every model. Imputation keeps X from dropping rows.
        # Still require at least one finite feature somewhere in train; eval mask is `enough`.
        n_common = int(enough.sum())
        if n_common == 0:
            raise RuntimeError(f"horizon {h}: no eligible weeks")
        for name in ("M0", *MODELS):
            miss = ~np.isfinite(wf[name]) & enough
            if miss.any():
                raise RuntimeError(f"horizon {h} {name}: predictions missing on common eval set")
        x_ok = np.isfinite(df[all_feat].to_numpy(dtype=float)).any(axis=1)
        if not bool(x_ok[enough].all()):
            # still score the intersection explicitly
            enough = enough & x_ok
            wf["enough"] = enough

        for period in (FULL_PERIOD, TEMPORAL_PERIOD):
            sel = period_sel(weeks, enough, period)
            st0 = score_block(y[sel], wf["M0"][sel])
            rows.append(metric_row(h, "M0", period, st0, st0["brier"]))
            for name in MODELS:
                st = score_block(y[sel], wf[name][sel])
                if st["N"] != st0["N"]:
                    raise RuntimeError(
                        f"sample mismatch h={h} {name} {period}: {st['N']} vs M0 {st0['N']}"
                    )
                extra = {}
                if period == FULL_PERIOD:
                    nov = nonoverlap(y, wf[name], wf["M0"], enough, h)
                    extra = {
                        "bss_median": nov["bss_median"],
                        "bss_min": nov["bss_min"],
                        "bss_max": nov["bss_max"],
                        "n_offsets_bss_gt0": nov["n_pos"],
                        "n_offsets": nov["n_off"],
                    }
                rows.append(metric_row(h, name, period, st, st0["brier"], **extra))

        for name in MODELS:
            nov = nonoverlap(y, wf[name], wf["M0"], enough, h)
            for off in nov["offsets"]:
                rows.append(
                    metric_row(
                        h,
                        name,
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
                    h,
                    name,
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
        "horizon",
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
    RESULTS.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(RESULTS / "horizon_metrics.csv", index=False)
    write_report(df, metrics)
    print(f"wrote {RESULTS / 'horizon_metrics.csv'} rows={len(metrics)}")
    print(f"wrote {RESULTS / 'HORIZON_DIAGNOSTIC.md'}")
    for h in HORIZONS:
        for m in ("M_CRYPTO", "M_MACRO"):
            full = lookup(metrics, h, m, FULL_PERIOD)
            val = lookup(metrics, h, m, TEMPORAL_PERIOD)
            nov = lookup(metrics, h, m, "NONOVERLAP_SUMMARY")
            print(h, m, classify(full, val, nov))


if __name__ == "__main__":
    main()
