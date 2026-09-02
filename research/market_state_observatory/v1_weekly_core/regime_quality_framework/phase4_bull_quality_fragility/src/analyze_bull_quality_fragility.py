#!/usr/bin/env python3
"""Phase 4: Bull quality & fragility.

Read-only V1 weekly state + Phase 3 catalog. Sample through 2023-12-29.
No macro. No 2024–2026. No ML. No trading. No threshold search.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PHASE4 = Path(__file__).resolve().parents[1]
RESULTS = PHASE4 / "results"
V1_WEEKLY = PHASE4.parents[1] / "results" / "weekly_market_state.csv"
PHASE3_CATALOG = (
    PHASE4.parent
    / "phase3_opportunity_episodes"
    / "results"
    / "opportunity_episode_catalog.csv"
)
SAMPLE_END = "2023-12-29"

# Frozen cuts — set before seeing results.
HIGH_MOM = 0.70
EXTREME_MOM = 0.90
BREADTH_PP = 0.05
PCTL_DELTA = 0.10
HEALTHY_MOM_FLOOR = 0.40
STRONG_UP_4W = 0.10
STRONG_UP_12W = 0.20
SEVERE_DOWN_4W = -0.10
SEVERE_DOWN_12W = -0.20

LEVEL_FEATURES = [
    "MOM_4W",
    "MOM_12W",
    "MOM_4W_PERCENTILE",
    "MOM_12W_PERCENTILE",
    "broad_breadth_4w",
    "largecap_breadth_4w_lagged",
    "breadth_gap_lagged",
    "median_coin_return_4w",
    "largecap_median_return_4w_lagged",
    "VOL_12W",
    "VOL_PERCENTILE",
    "TURNOVER_RELATIVE",
    "TURNOVER_PERCENTILE",
    "STABLECOIN_MCAP_4W_CHANGE",
    "STABLECOIN_MCAP_12W_CHANGE",
]
CHANGE_FEATURES = [
    "MOM4_CHANGE_4W",
    "MOM12_CHANGE_4W",
    "MOM4_PERCENTILE_CHANGE_4W",
    "MOM12_PERCENTILE_CHANGE_4W",
    "BROAD_BREADTH_CHANGE_4W",
    "LARGECAP_BREADTH_CHANGE_4W",
    "BREADTH_GAP_CHANGE_4W",
    "VOL_CHANGE_4W",
    "VOL_PERCENTILE_CHANGE_4W",
    "TURNOVER_CHANGE_4W",
    "STABLECOIN_GROWTH_CHANGE",
    "MARKET_DRAWDOWN_12W_HIGH",
    "MARKET_DRAWDOWN_26W_HIGH",
]


def decluster(mask: np.ndarray, cooldown: int) -> np.ndarray:
    """Consecutive runs of mask; keep first of each run if cooldown allows."""
    n = len(mask)
    keep = np.zeros(n, dtype=bool)
    last_kept = None
    run_start = None
    prev = None
    for i in range(n):
        if not mask[i]:
            prev = None
            continue
        if prev is None or i != prev + 1:
            run_start = i
        if i == run_start:
            if last_kept is None or (i - last_kept) >= cooldown:
                keep[i] = True
                last_kept = i
        prev = i
    return keep


def fmt(x, nd=4) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


def fmt_pct(x, nd=1) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{100.0 * x:.{nd}f}%"


def sample_quality(n: int, mode: str) -> str:
    if n <= 0:
        return "EMPTY"
    if mode == "ALL":
        return "LOW_SAMPLE" if n < 20 else "OK"
    return "VERY_LOW_SAMPLE" if n < 15 else "OK"


def rolling_drawdown_from_high(index: np.ndarray, window: int) -> np.ndarray:
    n = len(index)
    out = np.full(n, np.nan)
    for i in range(n):
        if i + 1 < window:
            continue
        w = index[i + 1 - window : i + 1]
        peak = np.nanmax(w)
        cur = index[i]
        if np.isfinite(peak) and peak > 0 and np.isfinite(cur):
            out[i] = cur / peak - 1.0
    return out


def cat_signed(x: pd.Series, thr: float, pos: str, mid: str, neg: str) -> pd.Series:
    out = np.full(len(x), "NA", dtype=object)
    v = pd.to_numeric(x, errors="coerce").to_numpy(dtype=float)
    fin = np.isfinite(v)
    out[fin & (v > thr)] = pos
    out[fin & (v >= -thr) & (v <= thr)] = mid
    out[fin & (v < -thr)] = neg
    return pd.Series(out, index=x.index)


def liquidity_category(sc12: pd.Series, tover: pd.Series) -> pd.Series:
    """Frozen 3-level flag. Expanding = SC12>0 and turnover>= recent median.
    Contracting = SC12<=0. Mixed = SC12>0 but turnover below median.
    """
    out = np.full(len(sc12), "NA", dtype=object)
    s = pd.to_numeric(sc12, errors="coerce").to_numpy(dtype=float)
    t = pd.to_numeric(tover, errors="coerce").to_numpy(dtype=float)
    fin = np.isfinite(s) & np.isfinite(t)
    out[fin & (s > 0) & (t >= 1.0)] = "expanding"
    out[fin & (s > 0) & (t < 1.0)] = "mixed"
    out[fin & (s <= 0)] = "contracting"
    return pd.Series(out, index=sc12.index)


def outcome_block(df: pd.DataFrame, mask: np.ndarray | pd.Series, horizon: int) -> dict:
    m = np.asarray(mask, dtype=bool)
    ret = pd.to_numeric(df.loc[m, f"future_return_{horizon}w"], errors="coerce")
    dd = pd.to_numeric(df.loc[m, f"max_drawdown_future_{horizon}w"], errors="coerce")
    ru = pd.to_numeric(df.loc[m, f"max_runup_future_{horizon}w"], errors="coerce")
    ok = ret.notna()
    r = ret[ok]
    n = int(len(r))
    strong = STRONG_UP_4W if horizon == 4 else STRONG_UP_12W
    severe = SEVERE_DOWN_4W if horizon == 4 else SEVERE_DOWN_12W
    if n == 0:
        return {
            "N": 0,
            "positive_frequency": np.nan,
            "mean_future_return": np.nan,
            "median_future_return": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "strong_up_frequency": np.nan,
            "severe_down_frequency": np.nan,
            "gt10_frequency": np.nan,
            "gt20_frequency": np.nan,
            "lt10_frequency": np.nan,
            "lt20_frequency": np.nan,
            "median_max_drawdown": np.nan,
            "p25_max_drawdown": np.nan,
            "median_max_runup": np.nan,
        }
    d = dd[ok]
    u = ru[ok]
    return {
        "N": n,
        "positive_frequency": float((r > 0).mean()),
        "mean_future_return": float(r.mean()),
        "median_future_return": float(r.median()),
        "p25": float(r.quantile(0.25)),
        "p75": float(r.quantile(0.75)),
        "strong_up_frequency": float((r > strong).mean()),
        "severe_down_frequency": float((r < severe).mean()),
        "gt10_frequency": float((r > 0.10).mean()),
        "gt20_frequency": float((r > 0.20).mean()),
        "lt10_frequency": float((r < -0.10).mean()),
        "lt20_frequency": float((r < -0.20).mean()),
        "median_max_drawdown": float(d.median()) if d.notna().any() else np.nan,
        "p25_max_drawdown": float(d.quantile(0.25)) if d.notna().any() else np.nan,
        "median_max_runup": float(u.median()) if u.notna().any() else np.nan,
    }


def conditional_row(
    family: str, group: str, horizon: int, mode: str, stats: dict
) -> dict:
    return {
        "analysis_family": family,
        "group": group,
        "horizon": horizon,
        "N": stats["N"],
        "sample_quality": sample_quality(stats["N"], mode),
        "positive_frequency": stats["positive_frequency"],
        "mean_future_return": stats["mean_future_return"],
        "median_future_return": stats["median_future_return"],
        "p25": stats["p25"],
        "p75": stats["p75"],
        "strong_up_frequency": stats["strong_up_frequency"],
        "severe_down_frequency": stats["severe_down_frequency"],
        "median_max_drawdown": stats["median_max_drawdown"],
        "median_max_runup": stats["median_max_runup"],
        "declustered_or_all": mode,
    }


def add_group_rows(
    rows: list,
    family: str,
    group: str,
    df: pd.DataFrame,
    mask: np.ndarray,
    emit_declustered: bool = True,
) -> None:
    mask = np.asarray(mask, dtype=bool)
    keep4 = decluster(mask, 4)
    keep12 = decluster(mask, 12)
    for horizon, keep in ((4, keep4), (12, keep12)):
        ok = df[f"ok{horizon}"].to_numpy()
        rows.append(
            conditional_row(
                family, group, horizon, "ALL", outcome_block(df, mask & ok, horizon)
            )
        )
        if not emit_declustered:
            continue
        rows.append(
            conditional_row(
                family,
                group,
                horizon,
                "DECLUSTERED",
                outcome_block(df, keep & ok, horizon),
            )
        )


def transition_stats(df: pd.DataFrame, mask: np.ndarray, directions: np.ndarray) -> dict:
    m = np.asarray(mask, dtype=bool)
    n = len(df)
    nxt = {"BULL": 0, "NEUTRAL": 0, "BEAR": 0, "NA": 0}
    n_next = 0
    t4 = {
        "remain_bull": 0,
        "touch_neutral": 0,
        "touch_bear": 0,
        "n": 0,
    }
    t12 = {
        "remain_bull": 0,
        "touch_neutral": 0,
        "touch_bear": 0,
        "n": 0,
    }
    for i in np.where(m)[0]:
        if i + 1 < n:
            d1 = directions[i + 1]
            n_next += 1
            if d1 in nxt:
                nxt[d1] += 1
            else:
                nxt["NA"] += 1
        if i + 4 < n:
            path = directions[i + 1 : i + 5]
            if all(p in ("BULL", "NEUTRAL", "BEAR") for p in path):
                t4["n"] += 1
                t4["remain_bull"] += int(all(p == "BULL" for p in path))
                t4["touch_neutral"] += int(any(p == "NEUTRAL" for p in path))
                t4["touch_bear"] += int(any(p == "BEAR" for p in path))
        if i + 12 < n:
            path = directions[i + 1 : i + 13]
            if all(p in ("BULL", "NEUTRAL", "BEAR") for p in path):
                t12["n"] += 1
                t12["remain_bull"] += int(all(p == "BULL" for p in path))
                t12["touch_neutral"] += int(any(p == "NEUTRAL" for p in path))
                t12["touch_bear"] += int(any(p == "BEAR" for p in path))

    def freq(count, den):
        return float(count / den) if den else np.nan

    return {
        "N": int(m.sum()),
        "N_next": n_next,
        "next_week_bull_freq": freq(nxt["BULL"], n_next),
        "next_week_neutral_freq": freq(nxt["NEUTRAL"], n_next),
        "next_week_bear_freq": freq(nxt["BEAR"], n_next),
        "touch_neutral_next4w": freq(t4["touch_neutral"], t4["n"]),
        "touch_bear_next4w": freq(t4["touch_bear"], t4["n"]),
        "remain_bull_all4w": freq(t4["remain_bull"], t4["n"]),
        "N_path4": t4["n"],
        "touch_neutral_next12w": freq(t12["touch_neutral"], t12["n"]),
        "touch_bear_next12w": freq(t12["touch_bear"], t12["n"]),
        "remain_bull_all12w": freq(t12["remain_bull"], t12["n"]),
        "N_path12": t12["n"],
    }


def load_inputs() -> pd.DataFrame:
    cat = pd.read_csv(PHASE3_CATALOG)
    v1 = pd.read_csv(V1_WEEKLY, usecols=["week", "market_index"])
    cat["week"] = pd.to_datetime(cat["week"])
    v1["week"] = pd.to_datetime(v1["week"])
    end = pd.Timestamp(SAMPLE_END)
    cat = cat.loc[cat["week"] <= end].copy()
    v1 = v1.loc[v1["week"] <= end].copy()
    df = cat.merge(v1, on="week", how="left")
    df = df.sort_values("week").reset_index(drop=True)
    if df["week"].max() > end:
        raise RuntimeError("sample leaked past SAMPLE_END")
    return df


def engineer(df: pd.DataFrame) -> pd.DataFrame:
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
    out["BREADTH_GAP_CHANGE_4W"] = (
        out["breadth_gap_lagged"] - out["breadth_gap_lagged"].shift(lag)
    )
    out["VOL_CHANGE_4W"] = out["VOL_12W"] - out["VOL_12W"].shift(lag)
    out["VOL_PERCENTILE_CHANGE_4W"] = (
        out["VOL_PERCENTILE"] - out["VOL_PERCENTILE"].shift(lag)
    )
    out["TURNOVER_CHANGE_4W"] = (
        out["TURNOVER_RELATIVE"] - out["TURNOVER_RELATIVE"].shift(lag)
    )
    out["STABLECOIN_GROWTH_CHANGE"] = (
        out["STABLECOIN_MCAP_4W_CHANGE"]
        - out["STABLECOIN_MCAP_4W_CHANGE"].shift(lag)
    )
    idx = out["market_index"].to_numpy(dtype=float)
    out["MARKET_DRAWDOWN_12W_HIGH"] = rolling_drawdown_from_high(idx, 12)
    out["MARKET_DRAWDOWN_26W_HIGH"] = rolling_drawdown_from_high(idx, 26)

    out["ok4"] = out["future_return_4w"].notna()
    out["ok12"] = out["future_return_12w"].notna()
    bull = out["state_direction"] == "BULL"
    out["is_bull"] = bull
    out["HIGH_MOM_BULL"] = bull & (out["MOM_12W_PERCENTILE"] >= HIGH_MOM)
    out["EXTREME_MOM_BULL"] = bull & (out["MOM_12W_PERCENTILE"] >= EXTREME_MOM)

    out["mom12_accel_cat"] = cat_signed(
        out["MOM12_PERCENTILE_CHANGE_4W"],
        PCTL_DELTA,
        "MOM_ACCELERATING",
        "MOM_STABLE",
        "MOM_DECELERATING",
    )
    out["mom4_accel_cat"] = cat_signed(
        out["MOM4_PERCENTILE_CHANGE_4W"],
        PCTL_DELTA,
        "MOM_ACCELERATING",
        "MOM_STABLE",
        "MOM_DECELERATING",
    )
    out["breadth_change_cat"] = cat_signed(
        out["BROAD_BREADTH_CHANGE_4W"],
        BREADTH_PP,
        "BREADTH_IMPROVING",
        "BREADTH_STABLE",
        "BREADTH_DETERIORATING",
    )
    out["largecap_breadth_change_cat"] = cat_signed(
        out["LARGECAP_BREADTH_CHANGE_4W"],
        BREADTH_PP,
        "BREADTH_IMPROVING",
        "BREADTH_STABLE",
        "BREADTH_DETERIORATING",
    )
    out["vol_change_cat"] = cat_signed(
        out["VOL_PERCENTILE_CHANGE_4W"],
        PCTL_DELTA,
        "VOL_RISING",
        "VOL_STABLE",
        "VOL_FALLING",
    )
    out["liquidity_cat"] = liquidity_category(
        out["STABLECOIN_MCAP_12W_CHANGE"], out["TURNOVER_RELATIVE"]
    )

    out["momentum_health"] = out["mom12_accel_cat"].map(
        {
            "MOM_ACCELERATING": "strengthening",
            "MOM_STABLE": "stable",
            "MOM_DECELERATING": "weakening",
            "NA": "NA",
        }
    )
    out["participation_health"] = out["breadth_change_cat"].map(
        {
            "BREADTH_IMPROVING": "broadening",
            "BREADTH_STABLE": "stable",
            "BREADTH_DETERIORATING": "narrowing",
            "NA": "NA",
        }
    )
    out["stress_health"] = out["vol_change_cat"].map(
        {
            "VOL_FALLING": "falling",
            "VOL_STABLE": "stable",
            "VOL_RISING": "rising",
            "NA": "NA",
        }
    )

    bb = out["BROAD_BREADTH_CHANGE_4W"]
    vc = out["VOL_PERCENTILE_CHANGE_4W"]
    mp = out["MOM_12W_PERCENTILE"]
    out["CANDIDATE_HEALTHY_BULL"] = (
        bull
        & (mp >= HEALTHY_MOM_FLOOR)
        & (bb >= -BREADTH_PP)
        & (vc <= PCTL_DELTA)
    )
    out["CANDIDATE_FRAGILE_BULL"] = bull & (mp >= HIGH_MOM) & (
        (bb < -BREADTH_PP) | (vc > PCTL_DELTA)
    )

    r4 = out["future_return_4w"]
    r12 = out["future_return_12w"]
    out["BULL_CONTINUATION_4W"] = np.where(bull & r4.notna(), r4 > 0, np.nan)
    out["BULL_FAILURE_4W"] = np.where(bull & r4.notna(), r4 <= 0, np.nan)
    out["BULL_CONTINUATION_12W"] = np.where(bull & r12.notna(), r12 > 0, np.nan)
    out["BULL_FAILURE_12W"] = np.where(bull & r12.notna(), r12 <= 0, np.nan)
    out["STRONG_UP_4W"] = np.where(bull & r4.notna(), r4 > STRONG_UP_4W, np.nan)
    out["STRONG_UP_12W"] = np.where(bull & r12.notna(), r12 > STRONG_UP_12W, np.nan)
    out["SEVERE_DOWN_4W"] = np.where(bull & r4.notna(), r4 < SEVERE_DOWN_4W, np.nan)
    out["SEVERE_DOWN_12W"] = np.where(bull & r12.notna(), r12 < SEVERE_DOWN_12W, np.nan)
    return out


def write_weekly(bull: pd.DataFrame) -> None:
    cols = [
        "week",
        "market_state",
        "state_direction",
        "breadth_quality",
        "volatility_state",
        "market_index",
        *LEVEL_FEATURES,
        *CHANGE_FEATURES,
        "HIGH_MOM_BULL",
        "EXTREME_MOM_BULL",
        "mom12_accel_cat",
        "mom4_accel_cat",
        "breadth_change_cat",
        "largecap_breadth_change_cat",
        "vol_change_cat",
        "liquidity_cat",
        "momentum_health",
        "participation_health",
        "stress_health",
        "CANDIDATE_HEALTHY_BULL",
        "CANDIDATE_FRAGILE_BULL",
        "future_return_4w",
        "future_return_12w",
        "max_drawdown_future_4w",
        "max_drawdown_future_12w",
        "max_runup_future_4w",
        "max_runup_future_12w",
        "BULL_CONTINUATION_4W",
        "BULL_FAILURE_4W",
        "BULL_CONTINUATION_12W",
        "BULL_FAILURE_12W",
        "STRONG_UP_4W",
        "STRONG_UP_12W",
        "SEVERE_DOWN_4W",
        "SEVERE_DOWN_12W",
    ]
    out = bull.loc[:, cols].copy()
    out["week"] = out["week"].dt.strftime("%Y-%m-%d")
    out.to_csv(RESULTS / "bull_quality_weekly.csv", index=False)


def build_conditionals(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    bull = df["is_bull"].to_numpy()
    hm = df["HIGH_MOM_BULL"].to_numpy()
    add_group_rows(
        rows,
        "context",
        "ALL_MARKET",
        df,
        df["state_direction"].isin(["BULL", "NEUTRAL", "BEAR"]).to_numpy(),
        emit_declustered=False,
    )
    add_group_rows(rows, "candidate_vs_generic", "GENERIC_BULL", df, bull)
    add_group_rows(
        rows,
        "candidate_vs_generic",
        "CANDIDATE_HEALTHY_BULL",
        df,
        df["CANDIDATE_HEALTHY_BULL"].to_numpy(),
    )
    add_group_rows(
        rows,
        "candidate_vs_generic",
        "CANDIDATE_FRAGILE_BULL",
        df,
        df["CANDIDATE_FRAGILE_BULL"].to_numpy(),
    )
    add_group_rows(rows, "high_mom_subset", "HIGH_MOM_BULL", df, hm)
    add_group_rows(
        rows, "high_mom_subset", "EXTREME_MOM_BULL", df, df["EXTREME_MOM_BULL"].to_numpy()
    )

    for cat, fam, col in (
        ("BREADTH_IMPROVING", "breadth_change", "breadth_change_cat"),
        ("BREADTH_STABLE", "breadth_change", "breadth_change_cat"),
        ("BREADTH_DETERIORATING", "breadth_change", "breadth_change_cat"),
        ("BREADTH_IMPROVING", "largecap_breadth_change", "largecap_breadth_change_cat"),
        ("BREADTH_STABLE", "largecap_breadth_change", "largecap_breadth_change_cat"),
        ("BREADTH_DETERIORATING", "largecap_breadth_change", "largecap_breadth_change_cat"),
        ("VOL_FALLING", "vol_change", "vol_change_cat"),
        ("VOL_STABLE", "vol_change", "vol_change_cat"),
        ("VOL_RISING", "vol_change", "vol_change_cat"),
        ("MOM_ACCELERATING", "mom12_acceleration", "mom12_accel_cat"),
        ("MOM_STABLE", "mom12_acceleration", "mom12_accel_cat"),
        ("MOM_DECELERATING", "mom12_acceleration", "mom12_accel_cat"),
        ("MOM_ACCELERATING", "mom4_acceleration", "mom4_accel_cat"),
        ("MOM_STABLE", "mom4_acceleration", "mom4_accel_cat"),
        ("MOM_DECELERATING", "mom4_acceleration", "mom4_accel_cat"),
    ):
        add_group_rows(rows, fam, cat, df, bull & (df[col] == cat).to_numpy())

    for cat in ("MOM_ACCELERATING", "MOM_STABLE", "MOM_DECELERATING"):
        add_group_rows(
            rows,
            "mom12_acceleration_high_mom",
            f"HIGH_MOM_{cat}",
            df,
            hm & (df["mom12_accel_cat"] == cat).to_numpy(),
        )
    for cat in ("BREADTH_IMPROVING", "BREADTH_STABLE", "BREADTH_DETERIORATING"):
        add_group_rows(
            rows,
            "highmom_x_breadth",
            f"HIGH_MOM_{cat}",
            df,
            hm & (df["breadth_change_cat"] == cat).to_numpy(),
        )
    for cat in ("VOL_FALLING", "VOL_STABLE", "VOL_RISING"):
        add_group_rows(
            rows,
            "highmom_x_vol",
            f"HIGH_MOM_{cat}",
            df,
            hm & (df["vol_change_cat"] == cat).to_numpy(),
        )

    sc = pd.to_numeric(df["STABLECOIN_MCAP_12W_CHANGE"], errors="coerce")
    to = pd.to_numeric(df["TURNOVER_RELATIVE"], errors="coerce")
    add_group_rows(
        rows, "highmom_x_stablecoin", "HIGH_MOM_SC12_POS", df, hm & (sc > 0).to_numpy()
    )
    add_group_rows(
        rows,
        "highmom_x_stablecoin",
        "HIGH_MOM_SC12_NONPOS",
        df,
        hm & sc.notna().to_numpy() & (sc <= 0).to_numpy(),
    )
    add_group_rows(
        rows, "highmom_x_turnover", "HIGH_MOM_TOVER_GE1", df, hm & (to >= 1).to_numpy()
    )
    add_group_rows(
        rows, "highmom_x_turnover", "HIGH_MOM_TOVER_LT1", df, hm & (to < 1).to_numpy()
    )

    det = (df["breadth_change_cat"] == "BREADTH_DETERIORATING").to_numpy()
    imp = (df["breadth_change_cat"] == "BREADTH_IMPROVING").to_numpy()
    vol_rise = (df["vol_change_cat"] == "VOL_RISING").to_numpy()
    vol_ok = df["vol_change_cat"].isin(["VOL_STABLE", "VOL_FALLING"]).to_numpy()
    add_group_rows(
        rows,
        "breadth_x_vol",
        "DETERIORATING_BREADTH_AND_RISING_VOL",
        df,
        bull & det & vol_rise,
    )
    add_group_rows(
        rows,
        "breadth_x_vol",
        "IMPROVING_BREADTH_AND_STABLE_OR_FALLING_VOL",
        df,
        bull & imp & vol_ok,
    )

    three = hm & det & vol_rise
    if int((three & df["ok4"].to_numpy()).sum()) >= 20:
        add_group_rows(
            rows,
            "three_way",
            "HIGH_MOM_DETERIORATING_BREADTH_RISING_VOL",
            df,
            three,
        )
    three_good = hm & imp & vol_ok
    if int((three_good & df["ok4"].to_numpy()).sum()) >= 20:
        add_group_rows(
            rows,
            "three_way",
            "HIGH_MOM_IMPROVING_BREADTH_VOL_NOT_RISING",
            df,
            three_good,
        )
    return rows


def write_transitions(df: pd.DataFrame) -> pd.DataFrame:
    directions = df["state_direction"].fillna("NA").astype(str).to_numpy()
    groups = [
        ("GENERIC_BULL", df["is_bull"].to_numpy()),
        ("CANDIDATE_HEALTHY_BULL", df["CANDIDATE_HEALTHY_BULL"].to_numpy()),
        ("CANDIDATE_FRAGILE_BULL", df["CANDIDATE_FRAGILE_BULL"].to_numpy()),
        ("HIGH_MOM_BULL", df["HIGH_MOM_BULL"].to_numpy()),
    ]
    recs = []
    for name, mask in groups:
        s = transition_stats(df, mask, directions)
        recs.append(
            {
                "group": name,
                "N": s["N"],
                "N_next_week": s["N_next"],
                "next_week_bull_freq": s["next_week_bull_freq"],
                "next_week_neutral_freq": s["next_week_neutral_freq"],
                "next_week_bear_freq": s["next_week_bear_freq"],
                "N_path4": s["N_path4"],
                "touch_neutral_next4w": s["touch_neutral_next4w"],
                "touch_bear_next4w": s["touch_bear_next4w"],
                "remain_bull_all4w": s["remain_bull_all4w"],
                "N_path12": s["N_path12"],
                "touch_neutral_next12w": s["touch_neutral_next12w"],
                "touch_bear_next12w": s["touch_bear_next12w"],
                "remain_bull_all12w": s["remain_bull_all12w"],
            }
        )
    tdf = pd.DataFrame.from_records(recs)
    tdf.to_csv(RESULTS / "bull_transition_analysis.csv", index=False)
    return tdf


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = load_inputs()
    df = engineer(df)
    bull = df.loc[df["is_bull"]].copy().reset_index(drop=True)
    if bull.empty:
        raise RuntimeError("no Bull weeks in sample")
    write_weekly(bull)
    cond_df = pd.DataFrame.from_records(build_conditionals(df))
    cond_df.to_csv(RESULTS / "bull_quality_conditionals.csv", index=False)
    write_transitions(df)
    print(f"Bull weeks={len(bull)} cond_rows={len(cond_df)} wrote {RESULTS}")


if __name__ == "__main__":
    main()
