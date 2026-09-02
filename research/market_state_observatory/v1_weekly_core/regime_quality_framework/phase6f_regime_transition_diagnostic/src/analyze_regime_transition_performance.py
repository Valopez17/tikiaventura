#!/usr/bin/env python3
"""H3: regime / transition diagnostic on frozen L=0 M_MACRO forecasts.

No new model. No new features. Lag=0 only. Horizons 4/8/12. No 2024–2026.
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
H2_CSV = RQF / "phase6e_macro_lag_diagnostic" / "results" / "macro_lag_metrics.csv"

SAMPLE_END = pd.Timestamp("2023-12-29")
VAL_START = pd.Timestamp("2021-01-01")
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
HORIZONS = (4, 8, 12)
FULL_PERIOD = "FULL_EXPANDING_WF"
TEMPORAL_PERIOD = "TEMPORAL_ROBUSTNESS_2021_2023"
LOW_N = 15
MIN_OFFSET_N = 10
FEATURES = [
    "DXY_CHG_12W",
    "US2Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "NASDAQ_RET_12W",
]
DIRECTIONAL = (
    "BEAR_TO_NEUTRAL",
    "BEAR_TO_BULL",
    "NEUTRAL_TO_BULL",
    "BULL_TO_NEUTRAL",
    "BULL_TO_BEAR",
    "NEUTRAL_TO_BEAR",
)
REGIMES = ("BULL", "NEUTRAL", "BEAR")


def window_return(r4: np.ndarray, horizon: int) -> np.ndarray:
    n = len(r4)
    n_blocks = horizon // 4
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        wealth = 1.0
        ok = True
        for b in range(n_blocks):
            j = i + 4 * b
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
    keep_cat = ["week", "state_direction", "future_return_4w", "future_return_12w"]
    df = cat[keep_cat].merge(mac[["week"] + FEATURES], on="week", how="inner", validate="one_to_one")
    df = df.sort_values("week").reset_index(drop=True)
    if (df["week"].dt.year >= 2024).any() or df["week"].max() > SAMPLE_END:
        raise RuntimeError("merged frame exceeds sample")
    gaps = df["week"].diff().dt.days
    if (gaps.dropna() != 7).any():
        raise RuntimeError("weeks are not a regular Friday series")
    r4 = pd.to_numeric(df["future_return_4w"], errors="coerce").to_numpy(dtype=float)
    r12 = pd.to_numeric(df["future_return_12w"], errors="coerce").to_numpy(dtype=float)
    w12 = window_return(r4, 12)
    both = np.isfinite(w12) & np.isfinite(r12)
    if int(both.sum()) == 0 or np.nanmax(np.abs(w12[both] - r12[both])) > 1e-10:
        raise RuntimeError("H=12 window does not match catalog future_return_12w")
    for h in HORIZONS:
        ret = window_return(r4, h)
        df[f"y_{h}"] = np.where(np.isfinite(ret), (ret > 0).astype(float), np.nan)

    state = df["state_direction"].astype("string")
    prev = state.shift(4)
    df["prev_state"] = prev
    df["is_transition"] = prev.notna() & state.notna() & (prev != state)
    df["is_persistent"] = prev.notna() & state.notna() & (prev == state)
    trans = np.where(df["is_transition"], prev + "_TO_" + state, pd.NA)
    df["transition_label"] = trans
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
    """Exact frozen L=0 spec from H2. Not a new model."""
    n = len(df)
    y_ok = np.isfinite(y)
    X = df[FEATURES].to_numpy(dtype=float)
    p0 = np.full(n, np.nan)
    p1 = np.full(n, np.nan)
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
        if nt < MIN_TRAIN:
            continue
        ytr = y[train]
        p0[t] = float(ytr.mean())
        p1[t] = logit_fit_predict(X[train], ytr, X[t])
        enough[t] = True
    return {"M0": p0, "M_MACRO": p1, "enough": enough}


def score_block(y: np.ndarray, p: np.ndarray, *, allow_auc: bool = True) -> dict:
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
        "mean_pred": np.nan,
        "observed_rate": np.nan,
    }
    if n == 0:
        return rec
    rec["prevalence"] = float(y.mean())
    rec["observed_rate"] = rec["prevalence"]
    rec["mean_pred"] = float(p.mean())
    rec["brier"] = float(brier_score_loss(y, p))
    rec["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    n_pos = int(y.sum())
    if allow_auc and n >= LOW_N and 0 < n_pos < n:
        rec["auc"] = float(roc_auc_score(y, p))
        rec["balanced_accuracy"] = float(balanced_accuracy_score(y, (p >= 0.5).astype(int)))
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


def nonoverlap(y, p_m, p0, mask, step: int) -> dict:
    idx = np.arange(len(y))
    skills = []
    n_eval = 0
    n_skip = 0
    for off in range(step):
        sel = mask & ((idx - off) % step == 0)
        n_sel = int((np.isfinite(y) & np.isfinite(p_m) & sel).sum())
        if n_sel < MIN_OFFSET_N:
            n_skip += 1
            continue
        n_eval += 1
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skills.append(bss(st_m["brier"], st_0["brier"]))
    arr = np.asarray(skills, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {
            "bss_median": np.nan,
            "bss_min": np.nan,
            "bss_max": np.nan,
            "n_pos": 0,
            "n_off": 0,
            "n_skip": n_skip,
        }
    return {
        "bss_median": float(np.median(finite)),
        "bss_min": float(np.min(finite)),
        "bss_max": float(np.max(finite)),
        "n_pos": int(np.sum(finite > 0)),
        "n_off": int(finite.size),
        "n_skip": n_skip,
    }


def empty_extra() -> dict:
    return {
        "bss_median": np.nan,
        "bss_min": np.nan,
        "bss_max": np.nan,
        "n_offsets_bss_gt0": np.nan,
        "n_offsets": np.nan,
        "mean_pred": np.nan,
        "observed_rate": np.nan,
        "low_sample": False,
        "note": "",
    }


def metric_row(horizon, slice_type, slice_value, period, st_m, st_0, **extra) -> dict:
    n = int(st_m["N"])
    rec = {
        "horizon": int(horizon),
        "slice_type": slice_type,
        "slice_value": slice_value,
        "period": period,
        "N": n,
        "prevalence": st_m["prevalence"],
        "brier": st_m["brier"],
        "brier_skill_vs_M0": bss(st_m["brier"], st_0["brier"]),
        "log_loss": st_m["log_loss"],
        "auc": st_m["auc"],
        "balanced_accuracy": st_m["balanced_accuracy"],
        "brier_m0": st_0["brier"],
    }
    rec.update(empty_extra())
    rec["mean_pred"] = st_m.get("mean_pred", np.nan)
    rec["observed_rate"] = st_m.get("observed_rate", np.nan)
    rec["low_sample"] = n < LOW_N
    rec.update(extra)
    if rec["low_sample"] and not rec.get("note"):
        rec["note"] = "LOW SAMPLE"
    return rec


def fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def lookup(metrics: pd.DataFrame, h, stype, sval, period) -> dict | None:
    q = metrics[
        (metrics["horizon"] == h)
        & (metrics["slice_type"] == stype)
        & (metrics["slice_value"] == sval)
        & (metrics["period"] == period)
    ]
    if q.empty:
        return None
    return q.iloc[0].to_dict()


def beats_m0(row: dict | None) -> bool:
    if row is None or int(row.get("N") or 0) < LOW_N:
        return False
    s = row.get("brier_skill_vs_M0")
    return bool(np.isfinite(s) and s > 0)


def classify_slice(full: dict | None, val: dict | None, *, h3_role: str) -> str:
    """Classify a major slice vs the H3 hypothesis (transitions > persistent)."""
    n_full = int(full["N"]) if full else 0
    n_val = int(val["N"]) if val else 0
    if n_full < LOW_N and n_val < LOW_N:
        return "INSUFFICIENT SAMPLE"
    if h3_role == "transition":
        # filled later with trans vs pers comparison
        return "NO SUPPORT"
    return "NO SUPPORT"


def sanity_vs_h2(metrics: pd.DataFrame) -> None:
    if not H2_CSV.exists():
        raise RuntimeError("H2 metrics missing; needed for L=0 reconstruction check")
    h2 = pd.read_csv(H2_CSV)
    for h in HORIZONS:
        a = metrics[
            (metrics["horizon"] == h)
            & (metrics["slice_type"] == "ALL")
            & (metrics["slice_value"] == "ALL_MARKET")
            & (metrics["period"] == FULL_PERIOD)
        ].iloc[0]
        b = h2[
            (h2["lag_weeks"] == 0)
            & (h2["horizon_weeks"] == h)
            & (h2["model"] == "M_MACRO")
            & (h2["period"] == FULL_PERIOD)
        ].iloc[0]
        if int(a["N"]) != int(b["N"]):
            raise RuntimeError(f"H={h} N mismatch vs H2 L=0: {int(a['N'])} vs {int(b['N'])}")
        if abs(float(a["brier_skill_vs_M0"]) - float(b["brier_skill_vs_M0"])) > 1e-10:
            raise RuntimeError(f"H={h} BSS mismatch vs H2 L=0")


def write_report(df: pd.DataFrame, metrics: pd.DataFrame) -> None:
    def L(h, stype, sval, period):
        return lookup(metrics, h, stype, sval, period)

    def row_line(r: dict | None) -> str:
        if r is None:
            return "| — | — |"
        note = " LOW SAMPLE" if r.get("low_sample") else ""
        return (
            f"| {r['slice_value']} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | "
            f"{fmt(r['brier'], 4)} | {fmt(r['brier_skill_vs_M0'], 3)} | "
            f"{fmt(r['log_loss'], 4)} | {fmt(r['auc'], 3)} | "
            f"{fmt(r['balanced_accuracy'], 3)} |{note} |"
        )

    hdr = "| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"

    labels = {}
    for h in HORIZONS:
        tf = L(h, "PERSISTENCE", "TRANSITION", FULL_PERIOD)
        tv = L(h, "PERSISTENCE", "TRANSITION", TEMPORAL_PERIOD)
        pf = L(h, "PERSISTENCE", "PERSISTENT", FULL_PERIOD)
        pv = L(h, "PERSISTENCE", "PERSISTENT", TEMPORAL_PERIOD)
        for sval, role in (
            ("BULL", "regime"),
            ("NEUTRAL", "regime"),
            ("BEAR", "regime"),
            ("TRANSITION", "transition"),
            ("PERSISTENT", "persistent"),
        ):
            stype = "PERSISTENCE" if sval in ("TRANSITION", "PERSISTENT") else "REGIME"
            full = L(h, stype, sval, FULL_PERIOD)
            val = L(h, stype, sval, TEMPORAL_PERIOD)
            n_full = int(full["N"]) if full else 0
            n_val = int(val["N"]) if val else 0
            if n_full < LOW_N and n_val < LOW_N:
                labels[(h, sval)] = "INSUFFICIENT SAMPLE"
                continue
            nov = L(h, stype, sval, "NONOVERLAP_SUMMARY")
            nov_ok = False
            if nov is not None:
                med = nov.get("bss_median")
                npos = int(nov.get("n_offsets_bss_gt0") or 0)
                noff = int(nov.get("n_offsets") or 0)
                nov_ok = bool(np.isfinite(med) and med > 0 and noff > 0 and npos * 2 >= noff)
            if role == "transition":
                trans_better_full = (
                    tf and pf and np.isfinite(tf["brier_skill_vs_M0"]) and np.isfinite(pf["brier_skill_vs_M0"])
                    and tf["brier_skill_vs_M0"] > pf["brier_skill_vs_M0"]
                )
                trans_better_val = (
                    tv and pv and np.isfinite(tv["brier_skill_vs_M0"]) and np.isfinite(pv["brier_skill_vs_M0"])
                    and tv["brier_skill_vs_M0"] > pv["brier_skill_vs_M0"]
                )
                trans_pos_full = beats_m0(tf)
                trans_pos_val = beats_m0(tv)
                if (
                    trans_better_full
                    and trans_better_val
                    and trans_pos_full
                    and trans_pos_val
                    and nov_ok
                ):
                    labels[(h, sval)] = "SUPPORTS H3"
                elif (trans_better_full or trans_better_val) and (trans_pos_full or trans_pos_val):
                    labels[(h, sval)] = "WEAK SUPPORT"
                else:
                    labels[(h, sval)] = "NO SUPPORT"
            elif role == "persistent":
                # Better persistent skill contradicts H3
                pers_better_full = (
                    tf and pf and np.isfinite(tf["brier_skill_vs_M0"]) and np.isfinite(pf["brier_skill_vs_M0"])
                    and pf["brier_skill_vs_M0"] >= tf["brier_skill_vs_M0"]
                )
                pers_better_val = (
                    tv and pv and np.isfinite(tv["brier_skill_vs_M0"]) and np.isfinite(pv["brier_skill_vs_M0"])
                    and pv["brier_skill_vs_M0"] >= tv["brier_skill_vs_M0"]
                )
                if pers_better_full and pers_better_val and (beats_m0(pf) or beats_m0(pv)):
                    labels[(h, sval)] = "NO SUPPORT"
                elif beats_m0(pf) or beats_m0(pv):
                    labels[(h, sval)] = "NO SUPPORT"
                else:
                    labels[(h, sval)] = "NO SUPPORT"
            else:
                both = beats_m0(full) and beats_m0(val)
                one = beats_m0(full) or beats_m0(val)
                # A single-regime edge is not the H3 transition hypothesis
                if both or one:
                    labels[(h, sval)] = "NO SUPPORT"
                else:
                    labels[(h, sval)] = "NO SUPPORT"

    lines = []
    lines.append("# H3 — Regime / transition diagnostic")
    lines.append("")
    lines.append("Question: does the **existing** frozen L=0 M_MACRO forecast perform differently by crypto `state_direction` at t, and is it more useful near backward-looking regime transitions than inside persistent regimes?")
    lines.append("")
    lines.append("No new model. No new features. No lag 4/8. No interactions. No Bull/Bear-specific training. No 2024–2026. Not a trading backtest. Not an A/B/C verdict.")
    lines.append("")
    lines.append("Forecasts reconstructed with the frozen H2 L=0 spec: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`. Logistic L2 `C=1.0`. Train-only median and scaler. Min train N=100. Mature labels `s <= t - H`.")
    lines.append("")
    lines.append("`PREV_STATE` = `state_direction` at t−4. TRANSITION if previous ≠ current. PERSISTENT if previous = current. No future state is used.")
    lines.append("")
    lines.append("M0 is the original expanding **all-market** mature base rate, scored on the **same weeks** as M_MACRO inside each slice.")
    lines.append("If M_MACRO is better on transition weeks, that is a **CANDIDATE REGIME-CONDITIONAL EFFECT**, not “macro predicts regime transitions”.")
    lines.append("")
    lines.append("N < 15 is labeled **LOW SAMPLE**. No conclusions from those groups. Directional transitions: no AUC.")
    lines.append("2021–2023 is **TEMPORAL_ROBUSTNESS_2021_2023**, not clean OOS.")
    lines.append("")
    lines.append("H3 labels (main hypothesis: macro is more useful near transitions than inside persistent regimes):")
    lines.append("")
    lines.append("- SUPPORTS H3: TRANSITION BSS > PERSISTENT BSS on full **and** 2021–2023, TRANSITION BSS>0 on both, N≥15, and non-overlapping median BSS>0 with at least half of evaluated offsets BSS>0.")
    lines.append("- WEAK SUPPORT: TRANSITION beats PERSISTENT and M0 on only one window, or both windows but non-overlap fails.")
    lines.append("- NO SUPPORT: otherwise, including a single-regime edge that is not a transition effect.")
    lines.append("- INSUFFICIENT SAMPLE: N<15 on both windows.")
    lines.append("")
    lines.append("## Sample")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| merged weeks | {len(df)} |")
    lines.append(f"| last week | {df['week'].max().strftime('%Y-%m-%d')} |")
    lines.append("| 2024+ | none |")
    lines.append("| lag | 0 only |")
    st = df["state_direction"].value_counts(dropna=False)
    for k in ("BULL", "NEUTRAL", "BEAR"):
        lines.append(f"| catalog {k} | {int(st.get(k, 0))} |")
    lines.append(f"| TRANSITION (t vs t−4) | {int(df['is_transition'].sum())} |")
    lines.append(f"| PERSISTENT (t vs t−4) | {int(df['is_persistent'].sum())} |")
    lines.append("| reconstruction | ALL_MARKET L=0 matches H2 N and BSS |")
    lines.append("")

    lines.append("## Classification")
    lines.append("")
    lines.append("| H | BULL | NEUTRAL | BEAR | TRANSITION | PERSISTENT |")
    lines.append("|---:|---|---|---|---|---|")
    for h in HORIZONS:
        cells = " | ".join(labels[(h, s)] for s in ("BULL", "NEUTRAL", "BEAR", "TRANSITION", "PERSISTENT"))
        lines.append(f"| {h}w | {cells} |")
    lines.append("")

    for h in HORIZONS:
        lines.append(f"## Horizon {h}w")
        lines.append("")
        for period, title in (
            (FULL_PERIOD, "Full expanding walk-forward"),
            (TEMPORAL_PERIOD, "TEMPORAL_ROBUSTNESS_2021_2023"),
        ):
            lines.append(f"### {title}")
            lines.append("")
            lines.append("#### Regime")
            lines.append("")
            lines.append("\n".join([hdr, sep] + [row_line(L(h, "REGIME", s, period)) for s in REGIMES]))
            lines.append("")
            lines.append("#### Transition vs persistent")
            lines.append("")
            lines.append("\n".join([hdr, sep] + [row_line(L(h, "PERSISTENCE", s, period)) for s in ("TRANSITION", "PERSISTENT")]))
            lines.append("")
            bear_p = L(h, "REGIME_PERSISTENCE", "BEAR_PERSISTENT", period)
            if bear_p is not None:
                lines.append("#### Persistent BEAR")
                lines.append("")
                lines.append("\n".join([hdr, sep, row_line(bear_p)]))
                lines.append("")

        lines.append("### Non-overlapping BSS (full walk-forward)")
        lines.append("")
        lines.append("| slice | median BSS | min | max | offsets BSS>0 | offsets evaluated |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for stype, sval in (
            ("REGIME", "BULL"),
            ("REGIME", "NEUTRAL"),
            ("REGIME", "BEAR"),
            ("PERSISTENCE", "TRANSITION"),
            ("PERSISTENCE", "PERSISTENT"),
        ):
            r = L(h, stype, sval, "NONOVERLAP_SUMMARY")
            if r is None or int(r.get("n_offsets") or 0) == 0:
                lines.append(f"| {sval} | NA | NA | NA | — | 0 |")
            else:
                lines.append(
                    f"| {sval} | {fmt(r['bss_median'], 3)} | {fmt(r['bss_min'], 3)} | "
                    f"{fmt(r['bss_max'], 3)} | {int(r['n_offsets_bss_gt0'])}/{int(r['n_offsets'])} | "
                    f"{int(r['n_offsets'])} |"
                )
        lines.append("")
        lines.append("### Directional transitions (full walk-forward)")
        lines.append("")
        lines.append("| label | N | prevalence | mean predicted p | observed positive rate | Brier |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for lab in DIRECTIONAL:
            r = L(h, "DIRECTIONAL", lab, FULL_PERIOD)
            if r is None:
                lines.append(f"| {lab} | 0 | NA | NA | NA | NA |")
                continue
            tag = " LOW SAMPLE" if r.get("low_sample") else ""
            lines.append(
                f"| {lab}{tag} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | "
                f"{fmt(r['mean_pred'], 3)} | {fmt(r['observed_rate'], 3)} | {fmt(r['brier'], 4)} |"
            )
        lines.append("")
        lines.append("No AUC on directional groups. No conclusions from N<15.")
        lines.append("")

    # Answers
    def bss_txt(h, stype, sval, period):
        r = L(h, stype, sval, period)
        if r is None:
            return "NA"
        return f"{fmt(r['brier_skill_vs_M0'], 3)} (N={int(r['N'])})"

    lines.append("## Answers")
    lines.append("")
    lines.append("1. Does macro perform differently in BULL vs NEUTRAL vs BEAR?")
    for h in HORIZONS:
        fulls = [f"{s}={bss_txt(h, 'REGIME', s, FULL_PERIOD)}" for s in REGIMES]
        vals = [f"{s}={bss_txt(h, 'REGIME', s, TEMPORAL_PERIOD)}" for s in REGIMES]
        lines.append(f"   - {h}w full: " + "; ".join(fulls) + ".")
        lines.append(f"   - {h}w 2021–2023: " + "; ".join(vals) + ".")
    lines.append("   On the full walk-forward, no regime beats M0. On 2021–2023, all three do. That is the known period effect, not a clean BULL-vs-BEAR split.")
    lines.append("")

    lines.append("2. Is macro especially weak inside persistent BEAR?")
    for h in HORIZONS:
        r_f = L(h, "REGIME_PERSISTENCE", "BEAR_PERSISTENT", FULL_PERIOD)
        r_v = L(h, "REGIME_PERSISTENCE", "BEAR_PERSISTENT", TEMPORAL_PERIOD)
        r_b = L(h, "REGIME", "BEAR", FULL_PERIOD)
        if r_f is None:
            lines.append(f"   - {h}w: no persistent-BEAR rows.")
            continue
        weak = (
            np.isfinite(r_f["brier_skill_vs_M0"])
            and r_b is not None
            and np.isfinite(r_b["brier_skill_vs_M0"])
            and r_f["brier_skill_vs_M0"] < r_b["brier_skill_vs_M0"]
            and r_f["brier_skill_vs_M0"] <= 0
        )
        ls = " LOW SAMPLE" if r_f.get("low_sample") else ""
        lines.append(
            f"   - {h}w{ls}: persistent BEAR full BSS={fmt(r_f['brier_skill_vs_M0'], 3)} "
            f"(N={int(r_f['N'])}); 2021–2023 BSS={fmt(None if r_v is None else r_v['brier_skill_vs_M0'], 3)} "
            f"(N={0 if r_v is None else int(r_v['N'])}). "
            f"{'Weaker than all-BEAR and ≤0 on full WF.' if weak else 'Not a distinct extra-weak cell beyond all-BEAR, or sample too small.'}"
        )
    lines.append("")

    lines.append("3. Is macro stronger near transitions?")
    for h in HORIZONS:
        tf, pf = L(h, "PERSISTENCE", "TRANSITION", FULL_PERIOD), L(h, "PERSISTENCE", "PERSISTENT", FULL_PERIOD)
        tv, pv = L(h, "PERSISTENCE", "TRANSITION", TEMPORAL_PERIOD), L(h, "PERSISTENCE", "PERSISTENT", TEMPORAL_PERIOD)
        d_full = tf["brier_skill_vs_M0"] - pf["brier_skill_vs_M0"] if tf and pf else np.nan
        d_val = tv["brier_skill_vs_M0"] - pv["brier_skill_vs_M0"] if tv and pv else np.nan
        lines.append(
            f"   - {h}w: TRANSITION vs PERSISTENT ΔBSS full={fmt(d_full, 3)}, "
            f"2021–2023={fmt(d_val, 3)} (positive means transitions better). "
            f"Class: {labels[(h, 'TRANSITION')]}."
        )
    lines.append("")

    lines.append("4. Is the apparent edge concentrated in one regime only?")
    for h in HORIZONS:
        pos_full = [s for s in REGIMES if beats_m0(L(h, "REGIME", s, FULL_PERIOD))]
        pos_val = [s for s in REGIMES if beats_m0(L(h, "REGIME", s, TEMPORAL_PERIOD))]
        if not pos_full and not pos_val:
            lines.append(f"   - {h}w: no regime has BSS>0 with N≥15 on either window.")
        elif not pos_full and len(pos_val) == 3:
            lines.append(
                f"   - {h}w: not concentrated. Full WF: no regime BSS>0. 2021–2023: all three "
                f"({', '.join(pos_val)}). That is a period effect, not a single-regime story."
            )
        elif len(pos_full) == 1 and len(pos_val) <= 1:
            only = pos_full[0]
            lines.append(f"   - {h}w: yes, {only} is the only regime with BSS>0 on the full WF.")
        else:
            lines.append(
                f"   - {h}w: full WF BSS>0 in {pos_full or 'none'}; 2021–2023 BSS>0 in {pos_val or 'none'}."
            )
    lines.append("")

    lines.append("5. Does any regime-specific pattern appear in both full WF and 2021–2023?")
    for h in HORIZONS:
        both = [s for s in REGIMES if beats_m0(L(h, "REGIME", s, FULL_PERIOD)) and beats_m0(L(h, "REGIME", s, TEMPORAL_PERIOD))]
        trans_both = beats_m0(L(h, "PERSISTENCE", "TRANSITION", FULL_PERIOD)) and beats_m0(
            L(h, "PERSISTENCE", "TRANSITION", TEMPORAL_PERIOD)
        )
        if both:
            lines.append(f"   - {h}w: {', '.join(both)} BSS>0 on both windows.")
        elif trans_both:
            lines.append(f"   - {h}w: no regime BSS>0 on both windows; TRANSITION BSS>0 on both.")
        else:
            lines.append(f"   - {h}w: no regime (and not TRANSITION) has BSS>0 on both windows.")
    lines.append("")

    lines.append("6. Does transition performance beat persistent-regime performance?")
    n_h_beat_full = 0
    n_h_beat_val = 0
    for h in HORIZONS:
        tf, pf = L(h, "PERSISTENCE", "TRANSITION", FULL_PERIOD), L(h, "PERSISTENCE", "PERSISTENT", FULL_PERIOD)
        tv, pv = L(h, "PERSISTENCE", "TRANSITION", TEMPORAL_PERIOD), L(h, "PERSISTENCE", "PERSISTENT", TEMPORAL_PERIOD)
        bf = bool(tf and pf and tf["brier_skill_vs_M0"] > pf["brier_skill_vs_M0"])
        bv = bool(tv and pv and tv["brier_skill_vs_M0"] > pv["brier_skill_vs_M0"])
        n_h_beat_full += int(bf)
        n_h_beat_val += int(bv)
        lines.append(f"   - {h}w: full {bf}; 2021–2023 {bv}.")
    lines.append(f"   Horizons where TRANSITION BSS > PERSISTENT: full {n_h_beat_full}/3; 2021–2023 {n_h_beat_val}/3.")
    lines.append("")

    lines.append("7. Are results driven by tiny N?")
    tiny = []
    for h in HORIZONS:
        for sval in REGIMES + ("TRANSITION", "PERSISTENT"):
            stype = "PERSISTENCE" if sval in ("TRANSITION", "PERSISTENT") else "REGIME"
            r = L(h, stype, sval, FULL_PERIOD)
            if r is not None and r.get("low_sample"):
                tiny.append(f"{sval} {h}w N={int(r['N'])}")
        for lab in DIRECTIONAL:
            r = L(h, "DIRECTIONAL", lab, FULL_PERIOD)
            if r is not None and r.get("low_sample"):
                tiny.append(f"{lab} {h}w N={int(r['N'])}")
    if not tiny:
        lines.append("   Major BULL/NEUTRAL/BEAR and TRANSITION/PERSISTENT slices are N≥15 on full WF. Directional cells may still be small — see LOW SAMPLE tags.")
    else:
        lines.append("   LOW SAMPLE cells exist (especially directional). Major-slice conclusions below ignore N<15 groups.")
        # don't dump every directional; count them
        n_dir = sum(1 for t in tiny if "_TO_" in t)
        n_maj = sum(1 for t in tiny if "_TO_" not in t)
        lines.append(f"   LOW SAMPLE count: {n_maj} major-slice rows, {n_dir} directional rows.")
    lines.append("")

    trans_labels = [labels[(h, "TRANSITION")] for h in HORIZONS]
    supports = sum(1 for x in trans_labels if x == "SUPPORTS H3")
    weak = sum(1 for x in trans_labels if x == "WEAK SUPPORT")
    if supports >= 2:
        q8 = (
            "The TRANSITION vs PERSISTENT comparison SUPPORTS H3 on a majority of horizons. "
            "That is a CANDIDATE REGIME-CONDITIONAL EFFECT. It is not evidence that macro predicts transitions."
        )
        h3_overall = "WEAK SUPPORT" if supports < 3 or weak else "SUPPORTS H3"
    elif supports == 1 or weak >= 1:
        q8 = (
            "The hypothesis is not established. At most a WEAK / horizon-conditional difference "
            "between transition weeks and persistent weeks. Do not treat this as a regime-change model."
        )
        h3_overall = "WEAK SUPPORT" if (supports + weak) >= 1 else "NO SUPPORT"
    else:
        q8 = (
            "The evidence does not support the hypothesis that macro is more useful for regime changes "
            "than for forecasting returns inside an established crypto regime. "
            "Do not call this a candidate regime-conditional effect unless TRANSITION actually beats PERSISTENT "
            "and M0 with adequate N."
        )
        h3_overall = "NO SUPPORT"
    # override overall if no horizon has trans > pers with BSS>0
    if supports == 0 and weak == 0:
        h3_overall = "NO SUPPORT"

    lines.append("8. Does the evidence support: “macro is more useful for regime changes than for forecasting returns inside an established crypto regime”?")
    lines.append(f"   Overall H3: **{h3_overall}**.")
    lines.append(f"   {q8}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("No A/B/C model verdict. No new model. No regime interactions added.")
    lines.append(f"H3 hypothesis (transitions > persistent): **{h3_overall}**.")
    lines.append("If a slice shows better Brier skill on transition weeks, label it a CANDIDATE REGIME-CONDITIONAL EFFECT — not “macro predicts regime transitions”.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no new variables / interactions / separate Bull-Bear models")
    lines.append("- lag=0 only; horizons 4/8/12 only")
    lines.append("- no 2024–2026")
    lines.append("- Phase 3 / 6A / 6E not modified")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "REGIME_TRANSITION_DIAGNOSTIC.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df = load_frame()
    weeks = df["week"]
    is_bull = (df["state_direction"] == "BULL").fillna(False).to_numpy(dtype=bool)
    is_neutral = (df["state_direction"] == "NEUTRAL").fillna(False).to_numpy(dtype=bool)
    is_bear = (df["state_direction"] == "BEAR").fillna(False).to_numpy(dtype=bool)
    is_trans = df["is_transition"].fillna(False).to_numpy(dtype=bool)
    is_pers = df["is_persistent"].fillna(False).to_numpy(dtype=bool)
    trans_lab = df["transition_label"].astype("string").fillna("").to_numpy()
    rows: list[dict] = []

    for h in HORIZONS:
        y = df[f"y_{h}"].to_numpy(dtype=float)
        wf = walkforward(df, y, h)
        enough = wf["enough"]
        p0, p1 = wf["M0"], wf["M_MACRO"]

        slice_masks = {
            ("ALL", "ALL_MARKET"): np.ones(len(df), dtype=bool),
            ("REGIME", "BULL"): is_bull,
            ("REGIME", "NEUTRAL"): is_neutral,
            ("REGIME", "BEAR"): is_bear,
            ("PERSISTENCE", "TRANSITION"): is_trans,
            ("PERSISTENCE", "PERSISTENT"): is_pers,
            ("REGIME_PERSISTENCE", "BEAR_PERSISTENT"): is_bear & is_pers,
            ("REGIME_PERSISTENCE", "BULL_PERSISTENT"): is_bull & is_pers,
            ("REGIME_PERSISTENCE", "NEUTRAL_PERSISTENT"): is_neutral & is_pers,
        }
        for lab in DIRECTIONAL:
            slice_masks[("DIRECTIONAL", lab)] = trans_lab == lab

        for period in (FULL_PERIOD, TEMPORAL_PERIOD):
            base = period_sel(weeks, enough, period)
            for (stype, sval), smask in slice_masks.items():
                sel = base & smask
                allow_auc = stype != "DIRECTIONAL"
                st_m = score_block(y[sel], p1[sel], allow_auc=allow_auc)
                st_0 = score_block(y[sel], p0[sel], allow_auc=allow_auc)
                extra = {}
                if period == FULL_PERIOD and stype in ("REGIME", "PERSISTENCE"):
                    nov = nonoverlap(y, p1, p0, sel, h)
                    extra = {
                        "bss_median": nov["bss_median"],
                        "bss_min": nov["bss_min"],
                        "bss_max": nov["bss_max"],
                        "n_offsets_bss_gt0": nov["n_pos"],
                        "n_offsets": nov["n_off"],
                    }
                if stype == "DIRECTIONAL":
                    extra["note"] = "LOW SAMPLE" if st_m["N"] < LOW_N else "directional: no AUC"
                    extra["low_sample"] = st_m["N"] < LOW_N
                    extra["auc"] = np.nan
                    extra["balanced_accuracy"] = np.nan
                    extra["log_loss"] = np.nan
                rows.append(metric_row(h, stype, sval, period, st_m, st_0, **extra))

        for stype, sval in (
            ("REGIME", "BULL"),
            ("REGIME", "NEUTRAL"),
            ("REGIME", "BEAR"),
            ("PERSISTENCE", "TRANSITION"),
            ("PERSISTENCE", "PERSISTENT"),
        ):
            smask = slice_masks[(stype, sval)]
            sel = enough & smask
            nov = nonoverlap(y, p1, p0, sel, h)
            dummy_m = {
                "N": nov["n_off"],
                "prevalence": np.nan,
                "brier": np.nan,
                "log_loss": np.nan,
                "auc": np.nan,
                "balanced_accuracy": np.nan,
                "mean_pred": np.nan,
                "observed_rate": np.nan,
            }
            dummy_0 = {"brier": np.nan}
            rows.append(
                metric_row(
                    h,
                    stype,
                    sval,
                    "NONOVERLAP_SUMMARY",
                    dummy_m,
                    dummy_0,
                    bss_median=nov["bss_median"],
                    bss_min=nov["bss_min"],
                    bss_max=nov["bss_max"],
                    n_offsets_bss_gt0=nov["n_pos"],
                    n_offsets=nov["n_off"],
                    note="offset skipped if N<10",
                    low_sample=False,
                )
            )
            rows[-1]["brier_skill_vs_M0"] = nov["bss_median"]
            rows[-1]["N"] = nov["n_off"]

    metrics = pd.DataFrame(rows)
    col_order = [
        "horizon",
        "slice_type",
        "slice_value",
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
        "mean_pred",
        "observed_rate",
        "low_sample",
        "note",
    ]
    metrics = metrics[col_order]
    sanity_vs_h2(metrics)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "regime_transition_metrics.csv"
    metrics.to_csv(out, index=False)
    write_report(df, metrics)
    print(f"wrote {out} rows={len(metrics)}")
    print(f"wrote {RESULTS / 'REGIME_TRANSITION_DIAGNOSTIC.md'}")
    for h in HORIZONS:
        tf = lookup(metrics, h, "PERSISTENCE", "TRANSITION", FULL_PERIOD)
        pf = lookup(metrics, h, "PERSISTENCE", "PERSISTENT", FULL_PERIOD)
        print(
            f"H={h} TRANS BSS={tf['brier_skill_vs_M0']:.3f} N={int(tf['N'])} "
            f"PERS BSS={pf['brier_skill_vs_M0']:.3f} N={int(pf['N'])}"
        )


if __name__ == "__main__":
    main()
