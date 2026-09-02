#!/usr/bin/env python3
"""Phase 5: crypto-only expanding walk-forward probability benchmark.

Read-only Phase 3 catalog + Phase 4 Bull dynamics + V1 weekly.
Sample through 2023-12-29. No macro. No 2024–2026. No HP search. No trading.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

PHASE5 = Path(__file__).resolve().parents[1]
RESULTS = PHASE5 / "results"
RQF = PHASE5.parent
V1_WEEKLY = RQF.parent / "results" / "weekly_market_state.csv"
PHASE3_CATALOG = RQF / "phase3_opportunity_episodes" / "results" / "opportunity_episode_catalog.csv"
PHASE4_WEEKLY = RQF / "phase4_bull_quality_fragility" / "results" / "bull_quality_weekly.csv"

SAMPLE_END = "2023-12-29"
DEV_END = "2020-12-31"
VAL_START = "2021-01-01"
HIGH_MOM = 0.70
LOGIT_C = 1.0
MIN_TRAIN = 100
MIN_TRAIN_M4 = 40
BLOCK_LEN = 12
N_BOOT = 1000
CLIP = 1e-6
COEF_STRIDE = 26
RNG_SEED = 0

LEVEL_FEATURES = [
    "MOM_12W_PERCENTILE",
    "MOM_4W_PERCENTILE",
    "broad_breadth_4w",
    "largecap_breadth_4w_lagged",
    "VOL_PERCENTILE",
    "TURNOVER_RELATIVE",
    "STABLECOIN_MCAP_12W_CHANGE",
]
DYN_FEATURES = [
    "MOM4_CHANGE_4W",
    "MOM12_CHANGE_4W",
    "MOM12_PERCENTILE_CHANGE_4W",
    "BROAD_BREADTH_CHANGE_4W",
    "LARGECAP_BREADTH_CHANGE_4W",
    "VOL_PERCENTILE_CHANGE_4W",
    "TURNOVER_CHANGE_4W",
]
M2_FEATURES = LEVEL_FEATURES
M3_FEATURES = LEVEL_FEATURES + DYN_FEATURES
M4_FEATURES = [
    "MOM_12W_PERCENTILE",
    "MOM4_CHANGE_4W",
    "MOM12_CHANGE_4W",
    "MOM12_PERCENTILE_CHANGE_4W",
    "BROAD_BREADTH_CHANGE_4W",
    "LARGECAP_BREADTH_CHANGE_4W",
    "TURNOVER_RELATIVE",
    "VOL_PERCENTILE_CHANGE_4W",
]
P4_DYN = DYN_FEATURES + ["MOM4_PERCENTILE_CHANGE_4W"]

SEVERE_4W = -0.10
SEVERE_12W = -0.20
STRONG_4W = 0.10
STRONG_12W = 0.20


def add_dynamics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    lag = 4
    out["MOM4_CHANGE_4W"] = out["MOM_4W"] - out["MOM_4W"].shift(lag)
    out["MOM12_CHANGE_4W"] = out["MOM_12W"] - out["MOM_12W"].shift(lag)
    out["MOM4_PERCENTILE_CHANGE_4W"] = (
        out["MOM_4W_PERCENTILE"] - out["MOM_4W_PERCENTILE"].shift(lag)
    )
    out["MOM12_PERCENTILE_CHANGE_4W"] = (
        out["MOM_12W_PERCENTILE"] - out["MOM_12W_PERCENTILE"].shift(lag)
    )
    out["BROAD_BREADTH_CHANGE_4W"] = (
        out["broad_breadth_4w"] - out["broad_breadth_4w"].shift(lag)
    )
    out["LARGECAP_BREADTH_CHANGE_4W"] = (
        out["largecap_breadth_4w_lagged"]
        - out["largecap_breadth_4w_lagged"].shift(lag)
    )
    out["VOL_PERCENTILE_CHANGE_4W"] = (
        out["VOL_PERCENTILE"] - out["VOL_PERCENTILE"].shift(lag)
    )
    out["TURNOVER_CHANGE_4W"] = (
        out["TURNOVER_RELATIVE"] - out["TURNOVER_RELATIVE"].shift(lag)
    )
    return out


def load_frame() -> tuple[pd.DataFrame, float]:
    cat = pd.read_csv(PHASE3_CATALOG)
    p4 = pd.read_csv(PHASE4_WEEKLY)
    v1 = pd.read_csv(V1_WEEKLY, usecols=["week", "market_state", "state_direction", "volatility_state"])
    cat["week"] = pd.to_datetime(cat["week"])
    p4["week"] = pd.to_datetime(p4["week"])
    v1["week"] = pd.to_datetime(v1["week"])
    end = pd.Timestamp(SAMPLE_END)
    cat = cat.loc[cat["week"] <= end].copy()
    p4 = p4.loc[p4["week"] <= end].copy()
    v1 = v1.loc[v1["week"] <= end].copy()
    df = cat.sort_values("week").reset_index(drop=True)
    df = add_dynamics(df)
    take = ["week"] + [c for c in P4_DYN if c in p4.columns]
    p4s = p4[take].copy()
    df = df.merge(p4s, on="week", how="left", suffixes=("", "_p4"))
    for c in P4_DYN:
        pc = f"{c}_p4"
        if pc in df.columns:
            df[c] = df[pc].combine_first(df[c])
            df.drop(columns=[pc], inplace=True)
    if df["market_state"].isna().all() or (df["market_state"] == "").all():
        df = df.drop(columns=["market_state"], errors="ignore")
        df = df.merge(v1, on="week", how="left", suffixes=("", "_v1"))
    df["HIGH_MOM"] = df["MOM_12W_PERCENTILE"] >= HIGH_MOM
    df["is_bull"] = df["state_direction"] == "BULL"
    df["has_state"] = df["state_direction"].isin(["BULL", "NEUTRAL", "BEAR"])

    r12 = pd.to_numeric(df["future_return_12w"], errors="coerce")
    dev = (df["week"] <= pd.Timestamp(DEV_END)) & r12.notna()
    juicy_thr = float(np.quantile(r12[dev].to_numpy(), 0.90))
    df.attrs["juicy_threshold"] = juicy_thr
    df.attrs["juicy_n_dev"] = int(dev.sum())
    return df, juicy_thr


def logit_fit_predict(X_train: np.ndarray, y_train: np.ndarray, x_t: np.ndarray):
    """Median-impute + train-only scaler + L2 logistic. Returns p, coef, intercept."""
    y = y_train.astype(int)
    if y.min() == y.max():
        p = float(y[0])
        coef = np.full(X_train.shape[1], np.nan)
        return p, coef, np.nan
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
    coef = clf.coef_[0].astype(float)
    intercept = float(clf.intercept_[0])
    return float(np.clip(p, CLIP, 1.0 - CLIP)), coef, intercept


def walkforward(
    df: pd.DataFrame,
    *,
    universe: str,
    u_mask: np.ndarray,
    y: np.ndarray,
    horizon: int,
    model: str,
    features: list[str] | None,
    min_train: int,
    states: np.ndarray,
) -> tuple[pd.DataFrame, list[dict]]:
    n = len(df)
    y_ok = np.isfinite(y)
    eval_mask = u_mask & y_ok
    X = None if not features else df[features].to_numpy(dtype=float)
    pred = np.full(n, np.nan)
    ntr = np.full(n, np.nan)
    prev = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    reason = np.full(n, "", dtype=object)
    coef_snaps: list[dict] = []
    for t in range(n):
        if not eval_mask[t]:
            continue
        end = t - horizon
        if end < 0:
            reason[t] = "INSUFFICIENT_HISTORY"
            continue
        train = np.zeros(n, dtype=bool)
        train[: end + 1] = True
        train &= y_ok & u_mask
        nt = int(train.sum())
        ntr[t] = nt
        if nt < min_train:
            reason[t] = "INSUFFICIENT_HISTORY"
            continue
        ytr = y[train]
        prev[t] = float(ytr.mean())
        enough[t] = True
        if model == "M0":
            pred[t] = prev[t]
        elif model == "M1":
            st = states[t]
            same = train & (states == st) & (st != "") & (st != "nan")
            if isinstance(st, float) and not np.isfinite(st):
                pred[t] = prev[t]
            elif (not isinstance(st, str) and pd.isna(st)) or str(st) in ("", "nan", "None"):
                pred[t] = prev[t]
            elif int(same.sum()) >= 1:
                pred[t] = float(y[same].mean())
            else:
                pred[t] = prev[t]
        else:
            p, coef, _ = logit_fit_predict(X[train], ytr, X[t])
            pred[t] = p
            if t % COEF_STRIDE == 0:
                snap = {
                    "week": df.at[t, "week"],
                    "universe": universe,
                    "model": model,
                    "horizon": horizon,
                    "n_train": nt,
                }
                for fname, cv in zip(features, coef):
                    snap[fname] = cv
                coef_snaps.append(snap)
    rows = []
    weeks = df["week"]
    fut_col = f"future_return_{horizon}w"
    dd_col = f"max_drawdown_future_{horizon}w"
    juicy_thr = df.attrs.get("juicy_threshold", np.nan)
    for t in range(n):
        if not eval_mask[t]:
            continue
        p = pred[t]
        ok = bool(enough[t]) and np.isfinite(p)
        w = weeks.iat[t]
        period = (
            "validation_2021_2023"
            if w >= pd.Timestamp(VAL_START)
            else "development_to_2020"
        )
        rec = {
            "week": w.strftime("%Y-%m-%d") if hasattr(w, "strftime") else str(w)[:10],
            "evaluation_period": period,
            "universe": universe,
            "target": None,
            "horizon": horizon,
            "model": model,
            "predicted_probability": p if ok else np.nan,
            "predicted_class": (1 if p >= 0.5 else 0) if ok else np.nan,
            "actual_class": int(y[t]) if np.isfinite(y[t]) else np.nan,
            "future_return": df.at[t, fut_col],
            "max_drawdown": df.at[t, dd_col],
            "n_train": ntr[t],
            "prevalence_train": prev[t],
            "enough_history": ok,
            "reason": reason[t] if not ok else "",
            "state_direction": df.at[t, "state_direction"],
            "market_state": df.at[t, "market_state"],
        }
        if horizon == 12:
            rec["frozen_juicy_threshold"] = juicy_thr
        rows.append(rec)
    return pd.DataFrame.from_records(rows), coef_snaps


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    y = y[m].astype(int)
    p = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    n = int(len(y))
    if n == 0:
        return {
            "N": 0,
            "prevalence": np.nan,
            "accuracy": np.nan,
            "balanced_accuracy": np.nan,
            "brier": np.nan,
            "log_loss": np.nan,
            "auc": np.nan,
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
        }
    yhat = (p >= 0.5).astype(int)
    n_pos = int(y.sum())
    out = {
        "N": n,
        "prevalence": float(y.mean()),
        "accuracy": float(accuracy_score(y, yhat)),
        "balanced_accuracy": np.nan,
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "auc": np.nan,
        "calibration_intercept": np.nan,
        "calibration_slope": np.nan,
    }
    if 0 < n_pos < n:
        out["balanced_accuracy"] = float(
            balanced_accuracy_score(y, yhat)
        )
        out["auc"] = float(roc_auc_score(y, p))
    if n >= 10 and np.nanstd(p) > 1e-12:
        lr = LinearRegression()
        lr.fit(p.reshape(-1, 1), y)
        out["calibration_intercept"] = float(lr.intercept_)
        out["calibration_slope"] = float(lr.coef_[0])
    return out


def metrics_row(universe, target, horizon, model, period, stats, base_brier, base_ll, m1_brier, m1_ll) -> dict:
    brier = stats["brier"]
    ll = stats["log_loss"]
    skill = (
        1.0 - brier / base_brier
        if np.isfinite(brier) and np.isfinite(base_brier) and base_brier > 0
        else np.nan
    )
    return {
        "universe": universe,
        "target": target,
        "horizon": horizon,
        "model": model,
        "period": period,
        "N": stats["N"],
        "prevalence": stats["prevalence"],
        "accuracy": stats["accuracy"],
        "balanced_accuracy": stats["balanced_accuracy"],
        "brier": brier,
        "brier_skill_vs_base": skill,
        "log_loss": ll,
        "auc": stats["auc"],
        "calibration_intercept": stats["calibration_intercept"],
        "calibration_slope": stats["calibration_slope"],
        "delta_brier_vs_M0": brier - base_brier if np.isfinite(brier) and np.isfinite(base_brier) else np.nan,
        "delta_brier_vs_M1": brier - m1_brier if np.isfinite(brier) and np.isfinite(m1_brier) else np.nan,
        "delta_logloss_vs_M0": ll - base_ll if np.isfinite(ll) and np.isfinite(base_ll) else np.nan,
        "delta_logloss_vs_M1": ll - m1_ll if np.isfinite(ll) and np.isfinite(m1_ll) else np.nan,
    }


def slice_pred(pred: pd.DataFrame, universe, target, model, period: str | None) -> pd.DataFrame:
    q = pred[
        (pred["universe"] == universe)
        & (pred["target"] == target)
        & (pred["model"] == model)
        & pred["enough_history"].astype(bool)
        & pred["predicted_probability"].notna()
    ]
    if period == "validation_2021_2023":
        q = q[q["evaluation_period"] == "validation_2021_2023"]
    elif period == "development_to_2020":
        q = q[q["evaluation_period"] == "development_to_2020"]
    return q


def block_bootstrap_diff(d: np.ndarray, block: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    n = len(d)
    if n < block:
        return np.array([np.nan, np.nan, np.nan])
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    max_start = n - block + 1
    for i in range(n_boot):
        starts = rng.integers(0, max_start, size=n_blocks)
        sample = np.concatenate([d[s : s + block] for s in starts])[:n]
        means[i] = sample.mean()
    return np.percentile(means, [2.5, 50.0, 97.5])


def calibration_table(pred: pd.DataFrame, severe_thr: float) -> pd.DataFrame:
    rows = []
    keys = pred.groupby(["universe", "target", "horizon", "model", "period_cal"], dropna=False)
    for (universe, target, horizon, model, period), g in keys:
        g = g[g["enough_history"].astype(bool) & g["predicted_probability"].notna()].copy()
        if g.empty:
            continue
        p = g["predicted_probability"].to_numpy(dtype=float)
        try:
            g["bin"] = pd.qcut(p, 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"], duplicates="drop")
        except ValueError:
            g["bin"] = "Q_ALL"
        for b, sg in g.groupby("bin", observed=True):
            r = pd.to_numeric(sg["future_return"], errors="coerce")
            dd = pd.to_numeric(sg["max_drawdown"], errors="coerce")
            y = pd.to_numeric(sg["actual_class"], errors="coerce")
            rows.append(
                {
                    "universe": universe,
                    "target": target,
                    "horizon": horizon,
                    "model": model,
                    "period": period,
                    "probability_bin": str(b),
                    "N": int(len(sg)),
                    "mean_predicted_probability": float(sg["predicted_probability"].mean()),
                    "observed_frequency": float(y.mean()) if y.notna().any() else np.nan,
                    "median_future_return": float(r.median()) if r.notna().any() else np.nan,
                    "p25_future_return": float(r.quantile(0.25)) if r.notna().any() else np.nan,
                    "p75_future_return": float(r.quantile(0.75)) if r.notna().any() else np.nan,
                    "severe_downside_frequency": float((r < severe_thr).mean()) if r.notna().any() else np.nan,
                    "median_max_drawdown": float(dd.median()) if dd.notna().any() else np.nan,
                }
            )
    return pd.DataFrame.from_records(rows)


def coef_summary(snaps: list[dict], features: list[str]) -> pd.DataFrame:
    if not snaps:
        return pd.DataFrame()
    sdf = pd.DataFrame(snaps)
    recs = []
    for f in features:
        if f not in sdf.columns:
            continue
        v = pd.to_numeric(sdf[f], errors="coerce").dropna()
        if v.empty:
            continue
        recs.append(
            {
                "feature": f,
                "n_snapshots": int(len(v)),
                "median": float(v.median()),
                "p25": float(v.quantile(0.25)),
                "p75": float(v.quantile(0.75)),
                "frac_positive": float((v > 0).mean()),
                "frac_negative": float((v < 0).mean()),
            }
        )
    return pd.DataFrame.from_records(recs)


def fmt(x, nd=4) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


def adds_value(m_row, m0_row, m1_row) -> bool:
    if m_row is None or m0_row is None:
        return False
    prev = m_row["prevalence"]
    if not np.isfinite(prev) or prev <= 0.0 or prev >= 1.0:
        return False
    if not np.isfinite(m_row["brier"]) or not np.isfinite(m0_row["brier"]):
        return False
    if not np.isfinite(m_row["log_loss"]) or not np.isfinite(m0_row["log_loss"]):
        return False
    brier_ok = m_row["brier"] < m0_row["brier"] and (
        m1_row is None
        or not np.isfinite(m1_row["brier"])
        or m_row["brier"] < m1_row["brier"]
    )
    ll_ok = m_row["log_loss"] < m0_row["log_loss"] and (
        m1_row is None
        or not np.isfinite(m1_row["log_loss"])
        or m_row["log_loss"] < m1_row["log_loss"]
    )
    return bool(brier_ok and ll_ok)


def lookup(mdf: pd.DataFrame, universe, target, model, period):
    q = mdf[
        (mdf["universe"] == universe)
        & (mdf["target"] == target)
        & (mdf["model"] == model)
        & (mdf["period"] == period)
    ]
    if q.empty:
        return None
    return q.iloc[0]


def write_report(
    df: pd.DataFrame,
    juicy_thr: float,
    metrics: pd.DataFrame,
    pred: pd.DataFrame,
    coefs: dict[str, pd.DataFrame],
    boot: dict,
    nonov: dict,
) -> None:
    def L(u, t, m, p="full_wf"):
        return lookup(metrics, u, t, m, p)

    def line(u, t, m, p="full_wf") -> str:
        r = L(u, t, m, p)
        if r is None:
            return f"| {m} | — |"
        return (
            f"| {m} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['accuracy'], 3)} | "
            f"{fmt(r['balanced_accuracy'], 3)} | {fmt(r['brier'], 4)} | {fmt(r['brier_skill_vs_base'], 3)} | "
            f"{fmt(r['log_loss'], 4)} | {fmt(r['auc'], 3)} | {fmt(r['calibration_intercept'], 3)} | "
            f"{fmt(r['calibration_slope'], 3)} | {fmt(r['delta_brier_vs_M0'], 4)} | {fmt(r['delta_logloss_vs_M0'], 4)} |"
        )

    hdr = (
        "| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | "
        "Δbrier vs M0 | Δll vs M0 |"
    )
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"

    def table(u, t, p="full_wf"):
        models = ["M0", "M1", "M2", "M3"]
        if u == "HIGH_MOM":
            models = ["M0", "M1", "M2", "M3", "M4"]
        return "\n".join([hdr, sep] + [line(u, t, m, p) for m in models])

    # verdict ingredients
    checks = []
    for tgt in ("sign_4w", "sign_12w"):
        for period in ("full_wf", "validation_2021_2023"):
            m3 = L("ALL_MARKET", tgt, "M3", period)
            m2 = L("ALL_MARKET", tgt, "M2", period)
            m0 = L("ALL_MARKET", tgt, "M0", period)
            m1 = L("ALL_MARKET", tgt, "M1", period)
            checks.append(
                {
                    "target": tgt,
                    "period": period,
                    "M3_vs_M0_M1": adds_value(m3, m0, m1),
                    "M2_vs_M0_M1": adds_value(m2, m0, m1),
                    "M1_vs_M0": adds_value(m1, m0, None) if m1 is not None and m0 is not None else False,
                    "m3_bss": None if m3 is None else m3["brier_skill_vs_base"],
                    "m2_bss": None if m2 is None else m2["brier_skill_vs_base"],
                    "m1_bss": None if m1 is None else m1["brier_skill_vs_base"],
                }
            )
    n_m3 = sum(1 for c in checks if c["M3_vs_M0_M1"])
    n_m2 = sum(1 for c in checks if c["M2_vs_M0_M1"])
    n_m1 = sum(1 for c in checks if c["M1_vs_M0"])
    juicy_m3 = adds_value(
        L("ALL_MARKET", "juicy_12w", "M3", "validation_2021_2023"),
        L("ALL_MARKET", "juicy_12w", "M0", "validation_2021_2023"),
        L("ALL_MARKET", "juicy_12w", "M1", "validation_2021_2023"),
    )
    bull_m3_12 = adds_value(
        L("BULL", "sign_12w", "M3", "validation_2021_2023"),
        L("BULL", "sign_12w", "M0", "validation_2021_2023"),
        L("BULL", "sign_12w", "M1", "validation_2021_2023"),
    )
    val_m3_sign = all(
        c["M3_vs_M0_M1"]
        for c in checks
        if c["period"] == "validation_2021_2023" and c["target"] in ("sign_4w", "sign_12w")
    )
    full_m3_sign = all(
        c["M3_vs_M0_M1"]
        for c in checks
        if c["period"] == "full_wf" and c["target"] in ("sign_4w", "sign_12w")
    )

    if val_m3_sign and full_m3_sign and juicy_m3:
        verdict = "A"
        verdict_txt = "CRYPTO-ONLY HAS CLEAR OOS SIGNAL"
    elif n_m3 >= 1 or n_m2 >= 1 or bull_m3_12 or juicy_m3:
        verdict = "B"
        verdict_txt = "CRYPTO-ONLY HAS WEAK / CONDITIONAL OOS SIGNAL"
    else:
        verdict = "C"
        verdict_txt = "CRYPTO-ONLY DOES NOT BEAT SIMPLE BENCHMARKS"

    def coef_md(key: str) -> str:
        c = coefs.get(key)
        if c is None or c.empty:
            return "_no snapshots_"
        lines = [
            "| feature | n | median | p25 | p75 | frac>0 | frac<0 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for _, r in c.iterrows():
            lines.append(
                f"| {r['feature']} | {int(r['n_snapshots'])} | {fmt(r['median'])} | "
                f"{fmt(r['p25'])} | {fmt(r['p75'])} | {fmt(r['frac_positive'], 2)} | "
                f"{fmt(r['frac_negative'], 2)} |"
            )
        return "\n".join(lines)

    boot_txt = []
    for k, v in boot.items():
        boot_txt.append(
            f"- {k}: mean ΔBrier (model−baseline) 2.5/50/97.5 = "
            f"{fmt(v[0])} / {fmt(v[1])} / {fmt(v[2])}  "
            f"(negative = model better)"
        )

    nonov_txt = []
    for k, v in nonov.items():
        nonov_txt.append(
            f"- {k}: BSS median {fmt(v['bss_median'], 3)} "
            f"(min {fmt(v['bss_min'], 3)}, max {fmt(v['bss_max'], 3)}), "
            f"offsets with BSS>0: {v['n_pos']}/{v['n_off']}"
        )

    m1_beats = n_m1
    m3_val_4 = L("ALL_MARKET", "sign_4w", "M3", "validation_2021_2023")
    m3_val_12 = L("ALL_MARKET", "sign_12w", "M3", "validation_2021_2023")
    m0_val_4 = L("ALL_MARKET", "sign_4w", "M0", "validation_2021_2023")
    m0_val_12 = L("ALL_MARKET", "sign_12w", "M0", "validation_2021_2023")

    freeze_note = (
        "Do not freeze M3 as Model A. Keep crypto variables as descriptive Observatory context. "
        "Phase 6 may test whether macro improves juicy-12w, Bull continuation, 2020 vs 2021, and downside."
        if verdict == "C"
        else (
            "Candidate Model A (not auto-frozen): expanding walk-forward logistic L2 C=1.0 on "
            + ("M3 levels+dynamics" if n_m3 >= n_m2 else "M2 levels")
            + " for sign targets. Re-evaluate on sealed 2024–2026 later. Do not tune C or features on 2021–2023."
        )
    )

    n_dev = df.attrs.get("juicy_n_dev", 0)
    md = f"""# Crypto-only walk-forward analysis (Phase 5)

Sample through **{SAMPLE_END}**. Expanding walk-forward. Training labels are **mature**: for horizon `h` at week `t`, only weeks `s <= t - h` enter the fit. Scaler and median imputation are training-window only. Logistic L2 with **C={LOGIT_C}** (not tuned). **2024–2026 not used. Macro not used.**

JUICY_12W frozen threshold (P90 of complete 12w returns, 2015–2020 only, N={n_dev}): **{100*juicy_thr:.1f}%** (`{juicy_thr:.6f}`). Not recomputed on 2021–2023.

Quintile calibration bins are descriptive (cut after the walk-forward). Primary metrics use every week. Non-overlapping offsets are the robustness layer.

---

## DESCRIPTIVE FINDINGS

### ALL_MARKET — sign 4w (full walk-forward)

{table("ALL_MARKET", "sign_4w", "full_wf")}

### ALL_MARKET — sign 12w (full walk-forward)

{table("ALL_MARKET", "sign_12w", "full_wf")}

### ALL_MARKET — 2021–2023 validation — sign 4w

{table("ALL_MARKET", "sign_4w", "validation_2021_2023")}

### ALL_MARKET — 2021–2023 validation — sign 12w

{table("ALL_MARKET", "sign_12w", "validation_2021_2023")}

### ALL_MARKET — JUICY_12W (future return ≥ frozen P90)

Full:

{table("ALL_MARKET", "juicy_12w", "full_wf")}

2021–2023:

{table("ALL_MARKET", "juicy_12w", "validation_2021_2023")}

### ALL_MARKET — strong / severe (full walk-forward)

Strong 4w (>10%):

{table("ALL_MARKET", "strong_4w", "full_wf")}

Strong 12w (>20%):

{table("ALL_MARKET", "strong_12w", "full_wf")}

Severe 4w (<−10%):

{table("ALL_MARKET", "severe_4w", "full_wf")}

Severe 12w (<−20%):

{table("ALL_MARKET", "severe_12w", "full_wf")}

### BULL-only — continuation = sign (full and 2021–2023)

BULL sign 4w full:

{table("BULL", "sign_4w", "full_wf")}

BULL sign 12w full:

{table("BULL", "sign_12w", "full_wf")}

BULL sign 12w 2021–2023:

{table("BULL", "sign_12w", "validation_2021_2023")}

BULL sign 4w 2021–2023:

{table("BULL", "sign_4w", "validation_2021_2023")}

### HIGH_MOM (`MOM_12W_PERCENTILE >= 0.70`) including M4

Sign 12w full:

{table("HIGH_MOM", "sign_12w", "full_wf")}

Sign 12w 2021–2023:

{table("HIGH_MOM", "sign_12w", "validation_2021_2023")}

Sign 4w full:

{table("HIGH_MOM", "sign_4w", "full_wf")}

### Coefficient stability (M3 snapshots every {COEF_STRIDE} weeks)

ALL_MARKET M3, sign_12w:

{coef_md("ALL_MARKET|M3|sign_12w")}

ALL_MARKET M3, sign_4w:

{coef_md("ALL_MARKET|M3|sign_4w")}

BULL M3, sign_12w (lateness test):

{coef_md("BULL|M3|sign_12w")}

HIGH_MOM M4, sign_12w:

{coef_md("HIGH_MOM|M4|sign_12w")}

### Block bootstrap (12-week blocks, {N_BOOT} draws)

ΔBrier = Brier(model) − Brier(baseline) on aligned weeks. Negative means the model is better.

{chr(10).join(boot_txt) if boot_txt else "_not computed_"}

### Non-overlapping offsets

Every 4th week (4 offsets) for 4w; every 12th week (12 offsets) for 12w. Metric: Brier skill vs M0 on that offset.

{chr(10).join(nonov_txt) if nonov_txt else "_not computed_"}

---

## ANSWERS

1. **Does V1 state beat the unconditional base rate?** M1 vs M0 on sign targets: Brier-skill M1 sign_4w full={fmt(None if L("ALL_MARKET","sign_4w","M1") is None else L("ALL_MARKET","sign_4w","M1")["brier_skill_vs_base"], 3)}, sign_12w full={fmt(None if L("ALL_MARKET","sign_12w","M1") is None else L("ALL_MARKET","sign_12w","M1")["brier_skill_vs_base"], 3)}. Hits the “adds value” rule (Brier **and** logloss vs M0) in {m1_beats} of 4 primary cells (sign 4w/12w × full/validation).
2. **Do crypto levels beat V1?** M2 vs M0 and M1: {n_m2} of 4 primary cells.
3. **Do dynamics improve levels?** Compare M3 vs M2 in the tables (Brier/logloss). M3 “adds value” vs M0 and M1 in {n_m3} of 4 primary cells.
4. **Strongest 4w improvement** is the model with the best (lowest) validation Brier among M1–M3: see 2021–2023 sign_4w table. M3 BSS={fmt(None if m3_val_4 is None else m3_val_4["brier_skill_vs_base"], 3)} vs M0 Brier={fmt(None if m0_val_4 is None else m0_val_4["brier"], 4)}.
5. **Strongest 12w improvement:** M3 BSS={fmt(None if m3_val_12 is None else m3_val_12["brier_skill_vs_base"], 3)} vs M0 Brier={fmt(None if m0_val_12 is None else m0_val_12["brier"], 4)}.
6. **Survives 2021–2023?** M3 adds value on both sign horizons in validation: **{val_m3_sign}**.
7. **Survives non-overlapping evaluation?** See offset summary. Do not treat weekly overlapping 12w scores as independent.
8. **Calibrated?** Read cal_a / cal_b (OLS `y ~ a + b p`). Ideal a≈0, b≈1. M0 is a slowly moving constant so slope is often unstable.
9. **Rank future return distributions?** See `walkforward_calibration.csv` quintiles: median future return and severe-down frequency by Q1–Q5.
10. **JUICY_12W vs base rate?** Validation adds-value for M3: **{juicy_m3}**. Frozen P90 = {100*juicy_thr:.1f}%.
11. **Severe downside?** See severe_4w / severe_12w tables. Low prevalence; AUC/Brier skill can look noisy.
12. **Inside Bull, continuation vs failure?** BULL universe sign tables. M3 validation 12w adds-value: **{bull_m3_12}**.
13. **MOM12 as lateness after dynamics?** BULL M3 sign_12w coefficient table: sign of `MOM_12W_PERCENTILE` vs `MOM12_PERCENTILE_CHANGE_4W`. Negative level + positive change would match Phase 4. This is not causal.
14. **Momentum-change coefficients stable?** frac>0 / frac<0 in the M3 snapshot tables.
15. **Breadth change stable?** `BROAD_BREADTH_CHANGE_4W` and `LARGECAP_BREADTH_CHANGE_4W` in the same tables.
16. **TURNOVER_RELATIVE stable?** Same.
17. **Which features improve forecasts consistently?** Those with stable sign in snapshots **and** M3/M2 beating M0/M1 on Brier+logloss in validation. If none, none.
18. **Which fail?** Features that flip sign across snapshots, or models that lose to M0 on 2021–2023.
19. **Freeze Model A before macro?** Verdict {verdict}. {freeze_note}
20. **Residual for macro:** juicy 12w detection, Bull continuation vs failure, late-2020 vs late-2021, downside-risk — if crypto-only does not already settle them.

---

## VERDICT

**{verdict} — {verdict_txt}**

Adds-value rule (frozen): Brier improves **and** log loss improves versus M0 (and versus M1 when claimed to beat V1). Accuracy alone does not count. Definitions were not retuned on 2021–2023.

Primary cells (sign 4w/12w × full/validation): M1 {n_m1}/4, M2 {n_m2}/4, M3 {n_m3}/4.

---

## WHAT REMAINS FOR MACRO (Phase 6)

Can macro improve:

- JUICY 12w opportunity detection?
- Bull continuation vs failure?
- 2020 vs 2021 discrimination?
- downside-risk prediction?

2024–2026 stays sealed as the final exam.
"""
    (RESULTS / "CRYPTO_WALKFORWARD_ANALYSIS.md").write_text(md, encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df, juicy_thr = load_frame()
    r4 = pd.to_numeric(df["future_return_4w"], errors="coerce").to_numpy()
    r12 = pd.to_numeric(df["future_return_12w"], errors="coerce").to_numpy()
    y_sign4 = np.where(np.isfinite(r4), (r4 > 0).astype(float), np.nan)
    y_sign12 = np.where(np.isfinite(r12), (r12 > 0).astype(float), np.nan)
    y_strong4 = np.where(np.isfinite(r4), (r4 > STRONG_4W).astype(float), np.nan)
    y_strong12 = np.where(np.isfinite(r12), (r12 > STRONG_12W).astype(float), np.nan)
    y_sev4 = np.where(np.isfinite(r4), (r4 < SEVERE_4W).astype(float), np.nan)
    y_sev12 = np.where(np.isfinite(r12), (r12 < SEVERE_12W).astype(float), np.nan)
    y_juicy = np.where(np.isfinite(r12), (r12 >= juicy_thr).astype(float), np.nan)

    targets = [
        ("sign_4w", 4, y_sign4),
        ("sign_12w", 12, y_sign12),
        ("strong_4w", 4, y_strong4),
        ("strong_12w", 12, y_strong12),
        ("severe_4w", 4, y_sev4),
        ("severe_12w", 12, y_sev12),
        ("juicy_12w", 12, y_juicy),
    ]
    states = df["market_state"].astype(str).to_numpy()
    u_all = df["has_state"].to_numpy()
    u_bull = df["is_bull"].to_numpy()
    u_hm = df["HIGH_MOM"].fillna(False).to_numpy() & u_all

    jobs = []
    for tname, h, y in targets:
        jobs.append(("ALL_MARKET", u_all, tname, h, y, "M0", None, MIN_TRAIN))
        jobs.append(("ALL_MARKET", u_all, tname, h, y, "M1", None, MIN_TRAIN))
        jobs.append(("ALL_MARKET", u_all, tname, h, y, "M2", M2_FEATURES, MIN_TRAIN))
        jobs.append(("ALL_MARKET", u_all, tname, h, y, "M3", M3_FEATURES, MIN_TRAIN))
        jobs.append(("BULL", u_bull, tname, h, y, "M0", None, MIN_TRAIN))
        jobs.append(("BULL", u_bull, tname, h, y, "M1", None, MIN_TRAIN))
        jobs.append(("BULL", u_bull, tname, h, y, "M2", M2_FEATURES, MIN_TRAIN))
        jobs.append(("BULL", u_bull, tname, h, y, "M3", M3_FEATURES, MIN_TRAIN))
        jobs.append(("HIGH_MOM", u_hm, tname, h, y, "M0", None, MIN_TRAIN_M4))
        jobs.append(("HIGH_MOM", u_hm, tname, h, y, "M1", None, MIN_TRAIN_M4))
        jobs.append(("HIGH_MOM", u_hm, tname, h, y, "M2", M2_FEATURES, MIN_TRAIN_M4))
        jobs.append(("HIGH_MOM", u_hm, tname, h, y, "M3", M3_FEATURES, MIN_TRAIN_M4))
        jobs.append(("HIGH_MOM", u_hm, tname, h, y, "M4", M4_FEATURES, MIN_TRAIN_M4))

    parts = []
    all_snaps: list[dict] = []
    print(f"jobs={len(jobs)} weeks={len(df)} juicy_thr={juicy_thr:.6f}")
    for universe, umask, tname, h, y, model, feats, min_n in jobs:
        block, snaps = walkforward(
            df,
            universe=universe,
            u_mask=umask,
            y=y,
            horizon=h,
            model=model,
            features=feats,
            min_train=min_n,
            states=states,
        )
        if block.empty:
            continue
        block["target"] = tname
        parts.append(block)
        for s in snaps:
            s["target"] = tname
            all_snaps.append(s)
        n_ok = int(block["enough_history"].sum())
        print(f"  {universe} {tname} {model}: preds={n_ok}")

    pred = pd.concat(parts, ignore_index=True)
    pred.to_csv(RESULTS / "walkforward_predictions.csv", index=False)

    # metrics
    mrows = []
    universes = pred["universe"].unique()
    targs = pred["target"].unique()
    models = pred["model"].unique()
    periods = ("full_wf", "validation_2021_2023")
    cache_stats = {}
    for u in universes:
        for tname in targs:
            h = int(pred.loc[pred["target"] == tname, "horizon"].iloc[0])
            for period in periods:
                stats = {}
                for model in models:
                    g = slice_pred(pred, u, tname, model, None if period == "full_wf" else period)
                    st = score_block(
                        g["actual_class"].to_numpy(dtype=float),
                        g["predicted_probability"].to_numpy(dtype=float),
                    )
                    stats[model] = st
                    cache_stats[(u, tname, model, period)] = st
                b0 = stats.get("M0", {}).get("brier", np.nan)
                l0 = stats.get("M0", {}).get("log_loss", np.nan)
                b1 = stats.get("M1", {}).get("brier", np.nan)
                l1 = stats.get("M1", {}).get("log_loss", np.nan)
                for model, st in stats.items():
                    if st["N"] == 0:
                        continue
                    mrows.append(
                        metrics_row(u, tname, h, model, period, st, b0, l0, b1, l1)
                    )
    metrics = pd.DataFrame.from_records(mrows)
    metrics.to_csv(RESULTS / "walkforward_metrics.csv", index=False)

    # calibration: full_wf + validation, ALL/BULL/HIGH_MOM
    cal_src = pred[pred["enough_history"].astype(bool)].copy()
    cal_src["period_cal"] = "full_wf"
    val = cal_src[cal_src["evaluation_period"] == "validation_2021_2023"].copy()
    val["period_cal"] = "validation_2021_2023"
    cal_all = pd.concat([cal_src, val], ignore_index=True)
    cal_all["severe_thr"] = np.where(cal_all["horizon"] == 4, SEVERE_4W, SEVERE_12W)
    # split by horizon for threshold
    cal_parts = []
    for h, thr in ((4, SEVERE_4W), (12, SEVERE_12W)):
        sub = cal_all[cal_all["horizon"] == h]
        if sub.empty:
            continue
        cal_parts.append(calibration_table(sub, thr))
    cal = pd.concat(cal_parts, ignore_index=True) if cal_parts else pd.DataFrame()
    cal.to_csv(RESULTS / "walkforward_calibration.csv", index=False)

    # coefficient summaries
    coefs: dict[str, pd.DataFrame] = {}
    snap_df = pd.DataFrame(all_snaps) if all_snaps else pd.DataFrame()
    wanted = [
        ("ALL_MARKET", "M3", "sign_12w", M3_FEATURES),
        ("ALL_MARKET", "M3", "sign_4w", M3_FEATURES),
        ("BULL", "M3", "sign_12w", M3_FEATURES),
        ("HIGH_MOM", "M4", "sign_12w", M4_FEATURES),
        ("ALL_MARKET", "M2", "sign_12w", M2_FEATURES),
    ]
    if not snap_df.empty:
        for u, model, tname, feats in wanted:
            sub = snap_df[
                (snap_df["universe"] == u)
                & (snap_df["model"] == model)
                & (snap_df["target"] == tname)
            ]
            coefs[f"{u}|{model}|{tname}"] = coef_summary(sub.to_dict("records"), feats)

    # bootstrap on ALL_MARKET sign, full_wf
    rng = np.random.default_rng(RNG_SEED)
    boot = {}
    for tname in ("sign_4w", "sign_12w"):
        g0 = slice_pred(pred, "ALL_MARKET", tname, "M0", None)
        for model, base in (("M3", "M0"), ("M3", "M1"), ("M2", "M0")):
            g1 = slice_pred(pred, "ALL_MARKET", tname, model, None)
            gb = slice_pred(pred, "ALL_MARKET", tname, base, None)
            m = g1.merge(gb, on="week", suffixes=("_m", "_b"))
            if m.empty:
                continue
            y = m["actual_class_m"].to_numpy(dtype=float)
            pm = np.clip(m["predicted_probability_m"].to_numpy(dtype=float), CLIP, 1 - CLIP)
            pb = np.clip(m["predicted_probability_b"].to_numpy(dtype=float), CLIP, 1 - CLIP)
            diff = (pm - y) ** 2 - (pb - y) ** 2
            boot[f"{tname} {model}-vs-{base} full_wf"] = block_bootstrap_diff(
                diff, BLOCK_LEN, N_BOOT, rng
            )

    # non-overlapping BSS vs M0
    nonov = {}
    week_index = {w: i for i, w in enumerate(df["week"].dt.strftime("%Y-%m-%d"))}
    for u, tname, model in (
        ("ALL_MARKET", "sign_4w", "M3"),
        ("ALL_MARKET", "sign_12w", "M3"),
        ("ALL_MARKET", "sign_4w", "M1"),
        ("ALL_MARKET", "sign_12w", "M1"),
        ("ALL_MARKET", "juicy_12w", "M3"),
    ):
        h = 4 if tname.endswith("4w") else 12
        g = slice_pred(pred, u, tname, model, None)
        g0 = slice_pred(pred, u, tname, "M0", None)
        m = g.merge(g0[["week", "predicted_probability"]], on="week", suffixes=("", "_m0"))
        if m.empty:
            continue
        idx = np.array([week_index.get(w, -1) for w in m["week"]])
        y = m["actual_class"].to_numpy(dtype=float)
        pm = m["predicted_probability"].to_numpy(dtype=float)
        p0 = m["predicted_probability_m0"].to_numpy(dtype=float)
        skills = []
        n_off = h
        for off in range(n_off):
            sel = (idx >= 0) & ((idx - off) % h == 0)
            if int(sel.sum()) < 10:
                continue
            st_m = score_block(y[sel], pm[sel])
            st_0 = score_block(y[sel], p0[sel])
            if st_0["brier"] and st_0["brier"] > 0 and np.isfinite(st_m["brier"]):
                skills.append(1.0 - st_m["brier"] / st_0["brier"])
        if skills:
            arr = np.array(skills)
            nonov[f"{u} {tname} {model}"] = {
                "bss_median": float(np.median(arr)),
                "bss_min": float(arr.min()),
                "bss_max": float(arr.max()),
                "n_pos": int((arr > 0).sum()),
                "n_off": int(len(arr)),
            }

    # Narrative KEEP/DROP / verdict is authored in CRYPTO_WALKFORWARD_ANALYSIS.md.
    print(f"wrote {RESULTS} pred_rows={len(pred)} metric_rows={len(metrics)}")


if __name__ == "__main__":
    main()
