#!/usr/bin/env python3
"""Phase 6D: CRYPTO vs MACRO vs COMBINED expanding walk-forward.

Frozen feature sets. No search. No 2024–2026. No interactions.
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

PHASE6D = Path(__file__).resolve().parents[1]
RESULTS = PHASE6D / "results"
RQF = PHASE6D.parent
MACRO_CSV = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
CATALOG_CSV = (
    RQF / "phase3_opportunity_episodes" / "results" / "opportunity_episode_catalog.csv"
)
PHASE4_CSV = RQF / "phase4_bull_quality_fragility" / "results" / "bull_quality_weekly.csv"

SAMPLE_END = pd.Timestamp("2023-12-29")
VAL_START = pd.Timestamp("2021-01-01")
HORIZON = 12
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
STRONG = 0.20

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
COMBINED_FEATURES = CRYPTO_FEATURES + MACRO_FEATURES
MODELS = {
    "CRYPTO": CRYPTO_FEATURES,
    "MACRO": MACRO_FEATURES,
    "COMBINED": COMBINED_FEATURES,
}


def add_dynamics(df: pd.DataFrame) -> pd.DataFrame:
    """Same 4-week change formula as Phase 4 / Phase 5. Applied on the full catalog."""
    out = df.copy()
    lag = 4
    out["MOM4_CHANGE_4W"] = out["MOM_4W"] - out["MOM_4W"].shift(lag)
    out["MOM12_CHANGE_4W"] = out["MOM_12W"] - out["MOM_12W"].shift(lag)
    out["BROAD_BREADTH_CHANGE_4W"] = (
        out["broad_breadth_4w"] - out["broad_breadth_4w"].shift(lag)
    )
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
    for col in ("MOM_4W", "MOM_12W", "MOM_12W_PERCENTILE", "broad_breadth_4w", "TURNOVER_RELATIVE", "VOL_PERCENTILE"):
        if col not in cat.columns:
            raise RuntimeError(f"catalog missing {col}")

    df = add_dynamics(cat)
    p4_dyn = [c for c in ("MOM4_CHANGE_4W", "MOM12_CHANGE_4W", "BROAD_BREADTH_CHANGE_4W") if c in p4.columns]
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
    r = pd.to_numeric(df["future_return_12w"], errors="coerce")
    df["y_pos"] = np.where(np.isfinite(r), (r > 0).astype(float), np.nan)
    df["y_strong"] = np.where(np.isfinite(r), (r > STRONG).astype(float), np.nan)
    df["ok12"] = np.isfinite(r)
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


def walkforward(df: pd.DataFrame, y: np.ndarray) -> dict[str, np.ndarray]:
    n = len(df)
    y_ok = np.isfinite(y)
    X = {name: df[cols].to_numpy(dtype=float) for name, cols in MODELS.items()}
    out = {name: np.full(n, np.nan) for name in ["C0", *MODELS]}
    ntr = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    for t in range(n):
        if not y_ok[t]:
            continue
        end = t - HORIZON
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
        out["C0"][t] = float(ytr.mean())
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
    if period == "validation_2021_2023":
        ok &= weeks >= VAL_START
    elif period != "full_wf":
        raise ValueError(period)
    return ok


def nonoverlap(y: np.ndarray, p_m: np.ndarray, p0: np.ndarray, enough: np.ndarray) -> dict:
    idx = np.arange(len(y))
    skills = []
    offsets = []
    for off in range(HORIZON):
        sel = enough & ((idx - off) % HORIZON == 0)
        if int(sel.sum()) < 10:
            continue
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skill = bss(st_m["brier"], st_0["brier"])
        skills.append(skill)
        offsets.append(
            {
                "offset": off,
                "N": st_m["N"],
                "brier": st_m["brier"],
                "brier_c0": st_0["brier"],
                "bss": skill,
            }
        )
    if not skills:
        return {
            "bss_median": np.nan,
            "bss_min": np.nan,
            "bss_max": np.nan,
            "n_pos": 0,
            "n_off": 0,
            "offsets": offsets,
        }
    arr = np.asarray(skills, dtype=float)
    return {
        "bss_median": float(np.median(arr)),
        "bss_min": float(np.nanmin(arr)),
        "bss_max": float(np.nanmax(arr)),
        "n_pos": int(np.nansum(arr > 0)),
        "n_off": int(len(arr)),
        "offsets": offsets,
    }


def empty_extra() -> dict:
    return {
        "delta_brier_vs_CRYPTO": np.nan,
        "delta_brier_vs_MACRO": np.nan,
        "delta_logloss_vs_CRYPTO": np.nan,
        "delta_logloss_vs_MACRO": np.nan,
        "bss_median": np.nan,
        "bss_min": np.nan,
        "bss_max": np.nan,
        "n_offsets_bss_gt0": np.nan,
        "n_offsets": np.nan,
        "brier_c0": np.nan,
    }


def metric_row(target, model, period, stats, base_brier, **extra) -> dict:
    rec = {
        "target": target,
        "model": model,
        "period": period,
        "N": stats["N"],
        "prevalence": stats["prevalence"],
        "brier": stats["brier"],
        "log_loss": stats["log_loss"],
        "auc": stats["auc"],
        "balanced_accuracy": stats["balanced_accuracy"],
        "brier_skill_vs_C0": 0.0 if model == "C0" else bss(stats["brier"], base_brier),
    }
    rec.update(empty_extra())
    rec.update(extra)
    return rec


def fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def lookup(metrics: pd.DataFrame, target, model, period) -> dict | None:
    q = metrics[
        (metrics["target"] == target)
        & (metrics["model"] == model)
        & (metrics["period"] == period)
    ]
    if q.empty:
        return None
    return q.iloc[0].to_dict()


def beats_c0(row: dict | None) -> bool:
    if row is None or int(row["N"] or 0) == 0:
        return False
    s = row.get("brier_skill_vs_C0")
    return bool(np.isfinite(s) and s > 0)


def write_report(df: pd.DataFrame, metrics: pd.DataFrame) -> str:
    def L(t, m, p):
        return lookup(metrics, t, m, p)

    def line(t, m, p) -> str:
        r = L(t, m, p)
        if r is None:
            return f"| {m} | — |"
        return (
            f"| {m} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['brier'], 4)} | "
            f"{fmt(r['brier_skill_vs_C0'], 3)} | {fmt(r['log_loss'], 4)} | "
            f"{fmt(r['auc'], 3)} | {fmt(r['balanced_accuracy'], 3)} |"
        )

    hdr = "| model | N | prevalence | brier | BSS vs C0 | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"

    def table(t, p):
        models = ["C0", "CRYPTO", "MACRO", "COMBINED"]
        return "\n".join([hdr, sep] + [line(t, m, p) for m in models])

    pri = "pos_12w"
    val = "validation_2021_2023"
    full = "full_wf"
    c_crypto_val = L(pri, "CRYPTO", val)
    c_macro_val = L(pri, "MACRO", val)
    c_comb_val = L(pri, "COMBINED", val)
    c_crypto_full = L(pri, "CRYPTO", full)
    c_macro_full = L(pri, "MACRO", full)
    c_comb_full = L(pri, "COMBINED", full)

    d_b_crypto = (
        c_comb_val["brier"] - c_crypto_val["brier"]
        if c_comb_val and c_crypto_val
        else np.nan
    )
    d_ll_crypto = (
        c_comb_val["log_loss"] - c_crypto_val["log_loss"]
        if c_comb_val and c_crypto_val
        else np.nan
    )
    d_b_macro = (
        c_comb_val["brier"] - c_macro_val["brier"]
        if c_comb_val and c_macro_val
        else np.nan
    )
    d_ll_macro = (
        c_comb_val["log_loss"] - c_macro_val["log_loss"]
        if c_comb_val and c_macro_val
        else np.nan
    )

    comb_beats_crypto = np.isfinite(d_b_crypto) and d_b_crypto < 0
    comb_beats_macro = np.isfinite(d_b_macro) and d_b_macro < 0
    crypto_beats = beats_c0(c_crypto_full) or beats_c0(c_crypto_val)
    macro_beats = beats_c0(c_macro_full) or beats_c0(c_macro_val)
    comb_beats = beats_c0(c_comb_full) or beats_c0(c_comb_val)

    nov = {
        m: L(pri, m, "nonoverlap_summary")
        for m in ("CRYPTO", "MACRO", "COMBINED")
    }

    def nov_ok(row):
        if row is None:
            return False
        return (
            np.isfinite(row.get("bss_median", np.nan))
            and row["bss_median"] > 0
            and int(row.get("n_offsets_bss_gt0") or 0) >= 7
        )

    def nov_any(row):
        if row is None:
            return False
        return np.isfinite(row.get("bss_median", np.nan)) and (
            row["bss_median"] > 0 or int(row.get("n_offsets_bss_gt0") or 0) >= 1
        )

    # Incremental = COMBINED improves on the better standalone block, not merely
    # on a CRYPTO spec that already loses to C0.
    crypto_works = beats_c0(c_crypto_val) or beats_c0(c_crypto_full)
    macro_works = beats_c0(c_macro_val) or beats_c0(c_macro_full)
    beats_better_block = (comb_beats_crypto and crypto_works) or (
        comb_beats_macro and macro_works
    )

    if (
        beats_c0(c_comb_full)
        and beats_c0(c_comb_val)
        and comb_beats_crypto
        and comb_beats_macro
        and nov_ok(nov["COMBINED"])
    ):
        verdict = "A"
        verdict_txt = "COMBINED HAS CLEAR INCREMENTAL SIGNAL"
    elif (
        comb_beats_crypto
        and comb_beats_macro
        and (beats_c0(c_comb_val) or nov_any(nov["COMBINED"]))
    ):
        verdict = "B"
        verdict_txt = "COMBINED HAS WEAK / CONDITIONAL INCREMENTAL SIGNAL"
    elif beats_better_block and not (comb_beats_crypto and comb_beats_macro):
        verdict = "B"
        verdict_txt = "COMBINED HAS WEAK / CONDITIONAL INCREMENTAL SIGNAL"
    else:
        verdict = "C"
        verdict_txt = "COMBINED DOES NOT ADD VALUE"

    lines = []
    lines.append("# Phase 6D — Incremental walk-forward (CRYPTO vs MACRO vs COMBINED)")
    lines.append("")
    lines.append("Question: does concatenating the frozen macro set to a reduced crypto set improve 12w probability forecasts versus crypto alone, macro alone, and an expanding base rate?")
    lines.append("")
    lines.append("No feature search. No interactions. No 2024–2026. Not a trading backtest. Not the old Phase 5 M3.")
    lines.append("")
    lines.append("Mature labels: train `s <= t - 12`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.")
    lines.append("")
    lines.append("CRYPTO: `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE`.")
    lines.append("MACRO: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.")
    lines.append("COMBINED: CRYPTO + MACRO, concatenated.")
    lines.append("")
    lines.append("## Sample")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| merged weeks | {len(df)} |")
    lines.append(f"| last week | {df['week'].max().strftime('%Y-%m-%d')} |")
    lines.append("| 2024+ | none |")
    lines.append(f"| complete 12w outcomes | {int(df['ok12'].sum())} |")
    lines.append("| crypto dynamics | Phase 4 formula on the catalog; Phase 4 values overlaid on Bull weeks |")
    lines.append("")
    lines.append("## Primary `future_return_12w > 0`")
    lines.append("")
    lines.append("### Full expanding walk-forward")
    lines.append("")
    lines.append(table(pri, full))
    lines.append("")
    lines.append("### 2021–2023 validation")
    lines.append("")
    lines.append(table(pri, val))
    lines.append("")
    lines.append("### Incremental test (2021–2023) — COMBINED minus comparator")
    lines.append("")
    lines.append("Negative delta means COMBINED is better. No significance test.")
    lines.append("")
    lines.append("| comparison | delta Brier | delta log loss | COMBINED better on Brier? |")
    lines.append("|---|---:|---:|---|")
    lines.append(
        f"| COMBINED vs CRYPTO | {fmt(d_b_crypto, 4)} | {fmt(d_ll_crypto, 4)} | {comb_beats_crypto} |"
    )
    lines.append(
        f"| COMBINED vs MACRO | {fmt(d_b_macro, 4)} | {fmt(d_ll_macro, 4)} | {comb_beats_macro} |"
    )
    lines.append("")
    lines.append("### Non-overlapping 12-week offsets (primary, full walk-forward)")
    lines.append("")
    lines.append("| model | offsets | median BSS | min | max | offsets BSS>0 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for m in ("CRYPTO", "MACRO", "COMBINED"):
        r = nov[m]
        if r is None or int(r.get("n_offsets") or 0) == 0:
            lines.append(f"| {m} | — | NA | NA | NA | — |")
        else:
            lines.append(
                f"| {m} | {int(r['n_offsets'])} | {fmt(r['bss_median'], 3)} | "
                f"{fmt(r['bss_min'], 3)} | {fmt(r['bss_max'], 3)} | "
                f"{int(r['n_offsets_bss_gt0'])}/{int(r['n_offsets'])} |"
            )
    lines.append("")
    for m in ("CRYPTO", "MACRO", "COMBINED"):
        off = metrics[
            (metrics["target"] == pri)
            & (metrics["model"] == m)
            & metrics["period"].astype(str).str.startswith("nonoverlap_off")
        ].sort_values("period")
        if off.empty:
            continue
        lines.append(f"#### {m} offsets")
        lines.append("")
        lines.append("| offset | N | brier | brier C0 | BSS |")
        lines.append("|---:|---:|---:|---:|---:|")
        for _, r in off.iterrows():
            lines.append(
                f"| {str(r['period']).replace('nonoverlap_off', '')} | {int(r['N'])} | "
                f"{fmt(r['brier'], 4)} | {fmt(r['brier_c0'], 4)} | {fmt(r['brier_skill_vs_C0'], 3)} |"
            )
        lines.append("")

    lines.append("## Secondary `future_return_12w > +20%`")
    lines.append("")
    lines.append("### Full expanding walk-forward")
    lines.append("")
    lines.append(table("strong_12w", full))
    lines.append("")
    lines.append("### 2021–2023 validation")
    lines.append("")
    lines.append(table("strong_12w", val))
    lines.append("")
    s_comb = L("strong_12w", "COMBINED", val)
    s_crypto = L("strong_12w", "CRYPTO", val)
    s_macro = L("strong_12w", "MACRO", val)
    if s_comb and s_crypto and s_macro:
        lines.append("Incremental on secondary, 2021–2023 (descriptive only):")
        lines.append("")
        lines.append("| comparison | delta Brier | delta log loss |")
        lines.append("|---|---:|---:|")
        lines.append(
            f"| COMBINED vs CRYPTO | {fmt(s_comb['brier'] - s_crypto['brier'], 4)} | "
            f"{fmt(s_comb['log_loss'] - s_crypto['log_loss'], 4)} |"
        )
        lines.append(
            f"| COMBINED vs MACRO | {fmt(s_comb['brier'] - s_macro['brier'], 4)} | "
            f"{fmt(s_comb['log_loss'] - s_macro['log_loss'], 4)} |"
        )
        lines.append("")

    lines.append("## Answers")
    lines.append("")
    lines.append(
        f"1. Does CRYPTO beat base rate? "
        f"Full BSS>0: {beats_c0(c_crypto_full)}. 2021–2023 BSS>0: {beats_c0(c_crypto_val)}."
    )
    lines.append(
        f"2. Does MACRO beat base rate? "
        f"Full BSS>0: {beats_c0(c_macro_full)}. 2021–2023 BSS>0: {beats_c0(c_macro_val)}."
    )
    lines.append(
        f"3. Does COMBINED beat base rate? "
        f"Full BSS>0: {beats_c0(c_comb_full)}. 2021–2023 BSS>0: {beats_c0(c_comb_val)}."
    )
    lines.append(
        f"4. Does COMBINED beat CRYPTO (2021–2023 Brier)? {comb_beats_crypto} "
        f"(Δbrier={fmt(d_b_crypto, 4)})."
    )
    lines.append(
        f"5. Does COMBINED beat MACRO (2021–2023 Brier)? {comb_beats_macro} "
        f"(Δbrier={fmt(d_b_macro, 4)})."
    )
    nov_c = nov["COMBINED"]
    if nov_c is None:
        lines.append("6. Non-overlapping: COMBINED offsets not available.")
    else:
        lines.append(
            f"6. Does any COMBINED advantage survive non-overlapping offsets? "
            f"Median BSS={fmt(nov_c['bss_median'], 3)}; "
            f"offsets BSS>0: {int(nov_c.get('n_offsets_bss_gt0') or 0)}/{int(nov_c.get('n_offsets') or 0)}. "
            f"Majority-and-median rule: {nov_ok(nov_c)}."
        )
    if comb_beats_crypto and comb_beats_macro:
        inc = "Macro looks incremental on 2021–2023 Brier: COMBINED beats both CRYPTO and MACRO."
    elif comb_beats_crypto and not comb_beats_macro:
        if not crypto_works:
            inc = (
                "COMBINED beats CRYPTO but loses to MACRO. CRYPTO itself does not beat C0. "
                "Concatenating macro onto a weak crypto block improves the weak block; it does not beat macro-only. "
                "That is replacing weak crypto information, not an incremental combined model."
            )
        else:
            inc = (
                "COMBINED beats CRYPTO but not MACRO on 2021–2023: the lift is not beyond the macro-only spec."
            )
    elif comb_beats_macro and not comb_beats_crypto:
        inc = "COMBINED beats MACRO but not CRYPTO on 2021–2023: crypto already dominates; adding macro does not help."
    else:
        inc = "COMBINED does not beat CRYPTO or MACRO on 2021–2023 Brier. Concatenation does not add value."
    lines.append(f"7. Is macro incremental, or is it just replacing weak crypto information? {inc}")
    freeze = (
        "No. Do not freeze a candidate Model A. Combined incremental signal is not clear "
        "on both the full walk-forward and the non-overlapping robustness layer."
    )
    if verdict == "A":
        freeze = "Yes, as a frozen *candidate* only: COMBINED beat C0, CRYPTO, and MACRO on 2021–2023 and the non-overlapping layer. Still not a trading model."
    elif verdict == "C":
        freeze = (
            "No. Do not freeze a candidate Model A. COMBINED is worse than MACRO on 2021–2023 Brier "
            "and worse than C0 on the full walk-forward and on all 12 non-overlapping offsets."
        )
    lines.append(f"8. Is there enough evidence to freeze a candidate Model A? {freeze}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{verdict} — {verdict_txt}**")
    lines.append("")
    lines.append("Rule:")
    lines.append("")
    lines.append("- A if COMBINED beats C0 on primary full **and** 2021–2023, beats CRYPTO and MACRO on 2021–2023 Brier, and non-overlapping median BSS>0 with at least 7 offsets BSS>0.")
    lines.append("- B if COMBINED beats the better standalone block on 2021–2023 Brier, or beats both blocks but fails the full-sample / non-overlap bar.")
    lines.append("- C if COMBINED does not beat the better standalone block (here: MACRO). Beating a CRYPTO spec that already loses to C0 is not incremental value.")
    lines.append("")
    lines.append("No Crypto+Macro interactions. No extra features. M2 and HY unused.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no added features / interactions / C search")
    lines.append("- no extra targets")
    lines.append("- no 2024–2026")
    lines.append("- Phase 3 / 4 / 6A not modified")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "INCREMENTAL_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict


def main() -> None:
    df = load_frame()
    weeks = df["week"]
    rows: list[dict] = []
    targets = [("pos_12w", df["y_pos"].to_numpy(dtype=float)), ("strong_12w", df["y_strong"].to_numpy(dtype=float))]
    for tname, y in targets:
        wf = walkforward(df, y)
        for period in ("full_wf", "validation_2021_2023"):
            sel = period_sel(weeks, wf["enough"], period)
            st0 = score_block(y[sel], wf["C0"][sel])
            rows.append(metric_row(tname, "C0", period, st0, st0["brier"]))
            scored = {"C0": st0}
            for name in MODELS:
                st = score_block(y[sel], wf[name][sel])
                scored[name] = st
                extra = {}
                if name == "COMBINED" and period == "validation_2021_2023":
                    extra = {
                        "delta_brier_vs_CRYPTO": st["brier"] - scored["CRYPTO"]["brier"],
                        "delta_brier_vs_MACRO": st["brier"] - scored["MACRO"]["brier"],
                        "delta_logloss_vs_CRYPTO": st["log_loss"] - scored["CRYPTO"]["log_loss"],
                        "delta_logloss_vs_MACRO": st["log_loss"] - scored["MACRO"]["log_loss"],
                    }
                rows.append(metric_row(tname, name, period, st, st0["brier"], **extra))

        if tname == "pos_12w":
            for name in MODELS:
                nov = nonoverlap(y, wf[name], wf["C0"], wf["enough"])
                for off in nov["offsets"]:
                    rows.append(
                        metric_row(
                            tname,
                            name,
                            f"nonoverlap_off{off['offset']:02d}",
                            {
                                "N": off["N"],
                                "prevalence": np.nan,
                                "brier": off["brier"],
                                "log_loss": np.nan,
                                "auc": np.nan,
                                "balanced_accuracy": np.nan,
                            },
                            off["brier_c0"],
                            brier_c0=off["brier_c0"],
                        )
                    )
                rows.append(
                    metric_row(
                        tname,
                        name,
                        "nonoverlap_summary",
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
                # store median BSS also on skill column for lookup
                rows[-1]["brier_skill_vs_C0"] = nov["bss_median"]

    metrics = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(RESULTS / "incremental_metrics.csv", index=False)
    verdict = write_report(df, metrics)
    print(f"wrote {RESULTS / 'incremental_metrics.csv'} rows={len(metrics)}")
    print(f"wrote {RESULTS / 'INCREMENTAL_ANALYSIS.md'}")
    print("verdict", verdict)


if __name__ == "__main__":
    main()
