#!/usr/bin/env python3
"""Phase 3: opportunity episodes + extreme attribution.

Read-only V1 weekly state + Hsieh panel. Sample through 2023-12-29.
No macro. No 2024–2026. No ML. No trading.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PHASE3 = Path(__file__).resolve().parents[1]
RESULTS = PHASE3 / "results"
V1_DIR = PHASE3.parents[1]
V1_SRC = V1_DIR / "src"
V1_WEEKLY = V1_DIR / "results" / "weekly_market_state.csv"
SAMPLE_END = "2023-12-29"
LARGECAP_N = 100
CASE_WEEKS = ("2020-11-27", "2020-12-04", "2021-10-29", "2021-11-05")

sys.path.insert(0, str(V1_SRC))
from build_market_state_v1 import (  # noqa: E402
    MIN_HISTORY_WEEKS,
    PRIMARY_MIN_MCAP,
    calendar_wide,
    coin_cumret_wide,
    expanding_percentile,
    history_count_wide,
    load_panel,
)

# Frozen research buckets — set before seeing results.
MOM_BUCKETS = ((None, 0.40), (0.40, 0.70), (0.70, 0.90), (0.90, None))
BREADTH_BUCKETS = (
    (None, 0.40),
    (0.40, 0.50),
    (0.50, 0.60),
    (0.60, 0.70),
    (0.70, 0.80),
    (0.80, None),
)
TOVER_BUCKETS = ((None, 0.75), (0.75, 1.0), (1.0, 1.25), (1.25, None))
SC12_BUCKETS = ((None, 0.0), (0.0, 0.05), (0.05, 0.10), (0.10, None))

FEATURE_COLS = [
    "MOM_4W",
    "MOM_12W",
    "MOM_4W_PERCENTILE",
    "MOM_12W_PERCENTILE",
    "broad_breadth_4w",
    "largecap_breadth_4w",
    "largecap_breadth_4w_lagged",
    "breadth_gap",
    "breadth_gap_lagged",
    "median_coin_return_4w",
    "largecap_median_return_4w",
    "largecap_median_return_4w_lagged",
    "n_eligible_coins",
    "VOL_12W",
    "VOL_PERCENTILE",
    "market_turnover",
    "TURNOVER_RELATIVE",
    "TURNOVER_PERCENTILE",
    "STABLECOIN_MCAP",
    "STABLECOIN_MCAP_4W_CHANGE",
    "STABLECOIN_MCAP_12W_CHANGE",
    "STABLECOIN_LIQ_PERCENTILE",
]


def bucket_label(x: float, edges: tuple, names: list[str]) -> str:
    if not np.isfinite(x):
        return "NA"
    for (lo, hi), name in zip(edges, names):
        if lo is None and x < hi:
            return name
        if hi is None and x >= lo:
            return name
        if lo is not None and hi is not None and lo <= x < hi:
            return name
    last_lo = edges[-1][0]
    if last_lo is not None and x >= last_lo:
        return names[-1]
    return "NA"


def mom_bucket(p) -> str:
    return bucket_label(
        p, MOM_BUCKETS, ["<40", "40-70", "70-90", ">=90"]
    )


def breadth_bucket(x) -> str:
    return bucket_label(
        x,
        BREADTH_BUCKETS,
        ["<40%", "40-50%", "50-60%", "60-70%", "70-80%", ">=80%"],
    )


def vol_bucket(p) -> str:
    return mom_bucket(p)


def tover_bucket(x) -> str:
    return bucket_label(
        x, TOVER_BUCKETS, ["<0.75", "0.75-1.0", "1.0-1.25", ">1.25"]
    )


def sc12_bucket(x) -> str:
    return bucket_label(
        x, SC12_BUCKETS, ["<0", "0-5%", "5-10%", ">10%"]
    )


def outcome_rank_bucket(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p >= 0.95:
        return "TOP5"
    if p >= 0.90:
        return "TOP10_NOT_TOP5"
    if p >= 0.75:
        return "TOP25_NOT_TOP10"
    if p <= 0.05:
        return "BOTTOM5"
    if p <= 0.10:
        return "BOTTOM10_NOT_BOTTOM5"
    if p <= 0.25:
        return "BOTTOM25_NOT_BOTTOM10"
    return "MIDDLE"


def full_sample_percentile(values: np.ndarray) -> np.ndarray:
    """Retrospective catalog rank. Not a predictor. Complete-horizon rows only."""
    out = np.full(len(values), np.nan)
    m = np.isfinite(values)
    if not m.any():
        return out
    v = values[m]
    # empirical CDF among complete observations
    ranked = np.array([(v <= x).mean() for x in v], dtype=float)
    out[m] = ranked
    return out


def decluster(mask: np.ndarray, cooldown: int) -> tuple[np.ndarray, np.ndarray]:
    """Consecutive runs of mask; keep first of each run if cooldown allows."""
    n = len(mask)
    keep = np.zeros(n, dtype=bool)
    cluster = np.full(n, np.nan)
    cid = 0
    last_kept = None
    run_start = None
    prev = None
    for i in range(n):
        if not mask[i]:
            prev = None
            continue
        if prev is None or i != prev + 1:
            cid += 1
            run_start = i
        cluster[i] = cid
        if i == run_start:
            if last_kept is None or (i - last_kept) >= cooldown:
                keep[i] = True
                last_kept = i
        prev = i
    return keep, cluster


def summarize_num(s: pd.Series) -> dict:
    x = pd.to_numeric(s, errors="coerce").dropna()
    n = int(len(x))
    if n == 0:
        return {"N": 0, "mean": np.nan, "median": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "N": n,
        "mean": float(x.mean()),
        "median": float(x.median()),
        "p25": float(x.quantile(0.25)),
        "p75": float(x.quantile(0.75)),
    }


def fmt(x, nd=4) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


def fmt_pct(x, nd=1) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{100.0 * x:.{nd}f}%"


def build_eligibility_and_weights(panel: pd.DataFrame):
    simple_wide = calendar_wide(panel, "simple_return")
    mcap_wide = calendar_wide(panel, "market_cap").reindex_like(simple_wide)
    volume_wide = calendar_wide(panel, "volume").reindex_like(simple_wide)
    price_wide = calendar_wide(panel, "weekly_price").reindex_like(simple_wide)
    hist_wide = history_count_wide(price_wide)
    ret4_wide = coin_cumret_wide(simple_wide, 4)

    weeks = list(simple_wide.index)
    asset_ids = list(simple_wide.columns)
    simple = simple_wide.to_numpy(dtype=float)
    mcap = mcap_wide.to_numpy(dtype=float)
    volume = volume_wide.to_numpy(dtype=float)
    price = price_wide.to_numpy(dtype=float)
    hist = hist_wide.to_numpy(dtype=float)
    ret4 = ret4_wide.to_numpy(dtype=float)
    lag_mcap = np.vstack([np.full((1, len(asset_ids)), np.nan), mcap[:-1]])

    stable_ids = set(panel.loc[panel["obs_stablecoin"], "asset_id"].unique().tolist())
    is_stable = np.array([aid in stable_ids for aid in asset_ids], dtype=bool)
    eligible = (
        (~is_stable[None, :])
        & np.isfinite(mcap)
        & (mcap > 0)
        & (mcap >= PRIMARY_MIN_MCAP)
        & np.isfinite(simple)
        & np.isfinite(volume)
        & (volume > 0)
        & np.isfinite(price)
        & (price > 0)
        & (hist >= MIN_HISTORY_WEEKS)
    )

    n_w, n_a = simple.shape
    weights = np.full((n_w, n_a), np.nan)
    lc_lag_b = np.full(n_w, np.nan)
    lc_lag_med = np.full(n_w, np.nan)
    lc_lag_mask = np.zeros((n_w, n_a), dtype=bool)
    for t in range(n_w):
        elig = eligible[t]
        w_lag = np.where(elig, lag_mcap[t], np.nan)
        w_lag = np.where(np.isfinite(w_lag) & (w_lag > 0), w_lag, np.nan)
        w_sum = np.nansum(w_lag)
        if w_sum > 0:
            weights[t] = w_lag / w_sum
        rank_key = np.where(np.isfinite(w_lag), w_lag, -np.inf)
        order = np.argsort(-rank_key)
        n_elig = int(elig.sum())
        n_large = min(LARGECAP_N, int(np.isfinite(w_lag).sum()))
        if n_large > 0:
            lc = np.zeros(n_a, dtype=bool)
            picked = 0
            for j in order:
                if not np.isfinite(w_lag[j]):
                    break
                lc[j] = True
                picked += 1
                if picked >= n_large:
                    break
            lc_lag_mask[t] = lc
            r4 = np.where(lc, ret4[t], np.nan)
            fin = r4[np.isfinite(r4)]
            if fin.size:
                lc_lag_b[t] = float(np.mean(fin > 0))
                lc_lag_med[t] = float(np.median(fin))

    id_to_sym = (
        panel.drop_duplicates("asset_id")
        .set_index("asset_id")["symbol"]
        .to_dict()
    )
    symbols = [str(id_to_sym.get(a, a)) for a in asset_ids]
    btc_ix = next((i for i, s in enumerate(symbols) if s.upper() == "BTC"), None)
    eth_ix = next((i for i, s in enumerate(symbols) if s.upper() == "ETH"), None)
    return {
        "weeks": weeks,
        "asset_ids": asset_ids,
        "symbols": symbols,
        "simple": simple,
        "weights": weights,
        "eligible": eligible,
        "lag_mcap": lag_mcap,
        "ret4": ret4,
        "lc_lag_b": lc_lag_b,
        "lc_lag_med": lc_lag_med,
        "lc_lag_mask": lc_lag_mask,
        "btc_ix": btc_ix,
        "eth_ix": eth_ix,
    }


def add_opportunity_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for h in (4, 12):
        col = f"future_return_{h}w"
        r = out[col].to_numpy(dtype=float)
        p = full_sample_percentile(r)
        out[f"outcome_percentile_{h}w"] = p
        finite = r[np.isfinite(r)]
        p90 = float(np.quantile(finite, 0.90)) if finite.size else np.nan
        p95 = float(np.quantile(finite, 0.95)) if finite.size else np.nan
        p10 = float(np.quantile(finite, 0.10)) if finite.size else np.nan
        p05 = float(np.quantile(finite, 0.05)) if finite.size else np.nan
        out.attrs[f"p90_{h}w"] = p90
        out.attrs[f"p95_{h}w"] = p95
        out.attrs[f"p10_{h}w"] = p10
        out.attrs[f"p05_{h}w"] = p05
        out[f"opportunity_{h}w_bucket"] = [outcome_rank_bucket(x) for x in p]
        out[f"label_{h}w_positive"] = np.where(np.isfinite(r), r > 0, np.nan)
        out[f"label_{h}w_strong"] = np.where(np.isfinite(r), r > 0.10, np.nan)
        out[f"label_{h}w_extreme_opp"] = np.where(np.isfinite(r), r >= p90, np.nan)
        out[f"label_{h}w_exceptional_opp"] = np.where(np.isfinite(r), r >= p95, np.nan)
        out[f"label_{h}w_severe_fail"] = np.where(np.isfinite(r), r <= p10, np.nan)
        out[f"label_{h}w_extreme_fail"] = np.where(np.isfinite(r), r <= p05, np.nan)
        out[f"is_top5_{h}w"] = np.where(np.isfinite(p), p >= 0.95, False)
        out[f"is_top10_{h}w"] = np.where(np.isfinite(p), p >= 0.90, False)
        out[f"is_top25_{h}w"] = np.where(np.isfinite(p), p >= 0.75, False)
        out[f"is_bottom5_{h}w"] = np.where(np.isfinite(p), p <= 0.05, False)
        out[f"is_bottom10_{h}w"] = np.where(np.isfinite(p), p <= 0.10, False)
        out[f"is_bottom25_{h}w"] = np.where(np.isfinite(p), p <= 0.25, False)

    r4 = out["future_return_4w"].to_numpy(dtype=float)
    r12 = out["future_return_12w"].to_numpy(dtype=float)
    bull = (out["state_direction"] == "BULL").to_numpy()
    out["BULL_CONTINUATION_4W"] = np.where(bull & np.isfinite(r4), r4 > 0, np.nan)
    out["BULL_FAILURE_4W"] = np.where(bull & np.isfinite(r4), r4 <= 0, np.nan)
    out["BULL_STRONG_CONTINUATION_4W"] = np.where(
        bull & np.isfinite(r4), r4 > 0.10, np.nan
    )
    out["BULL_CONTINUATION_12W"] = np.where(bull & np.isfinite(r12), r12 > 0, np.nan)
    out["BULL_FAILURE_12W"] = np.where(bull & np.isfinite(r12), r12 <= 0, np.nan)
    out["BULL_STRONG_CONTINUATION_12W"] = np.where(
        bull & np.isfinite(r12), r12 > 0.20, np.nan
    )
    return out


def add_clusters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for h, cd in ((4, 4), (12, 12)):
        for lab in ("top5", "top10", "top25", "bottom5", "bottom10", "bottom25"):
            mask = out[f"is_{lab}_{h}w"].fillna(False).to_numpy(dtype=bool)
            keep, cluster = decluster(mask, cd)
            out[f"cluster_{lab}_{h}w"] = cluster
            out[f"decluster_keep_{lab}_{h}w"] = keep
    return out


def horizon_attribution(t: int, h: int, pack: dict, weekly_ret: np.ndarray):
    simple = pack["simple"]
    weights = pack["weights"]
    n_a = simple.shape[1]
    n_w = simple.shape[0]
    if t + h >= n_w:
        return None
    contrib_linked = np.zeros(n_a)
    contrib_unlinked = np.zeros(n_a)
    w_sum = np.zeros(n_a)
    w_n = np.zeros(n_a)
    start_w = np.full(n_a, np.nan)
    asset_log = np.zeros(n_a)
    asset_ok = np.ones(n_a, dtype=bool)
    wealth = 1.0
    mkt_weeks = []
    for k in range(1, h + 1):
        s = t + k
        r_m = weekly_ret[s]
        if not np.isfinite(r_m):
            return None
        mkt_weeks.append(r_m)
        w = weights[s]
        r = simple[s]
        cw = np.where(np.isfinite(w) & np.isfinite(r), w, 0.0)
        cr = np.where(np.isfinite(w) & np.isfinite(r), r, 0.0)
        if k == 1:
            start_w = np.where(np.isfinite(w), w, np.nan)
        w_sum += np.where(np.isfinite(w), w, 0.0)
        w_n += np.isfinite(w).astype(float)
        contrib_unlinked += cw * cr
        contrib_linked += wealth * cw * cr
        finite_r = np.isfinite(r)
        asset_ok &= finite_r
        asset_log = np.where(finite_r, asset_log + np.log1p(np.clip(r, -0.999999, None)), asset_log)
        wealth *= 1.0 + r_m
    avg_w = np.where(w_n > 0, w_sum / w_n, np.nan)
    asset_cum = np.expm1(asset_log)
    asset_cum = np.where(asset_ok, asset_cum, np.nan)
    mkt_cum = float(np.prod(1.0 + np.asarray(mkt_weeks)) - 1.0)
    mkt_sum = float(np.sum(mkt_weeks))
    return {
        "contrib_linked": contrib_linked,
        "contrib_unlinked": contrib_unlinked,
        "start_w": start_w,
        "avg_w": avg_w,
        "asset_cum": asset_cum,
        "mkt_cum": mkt_cum,
        "mkt_sum": mkt_sum,
        "identity_gap": mkt_cum - float(np.nansum(contrib_linked)),
    }


def group_slice(mask, attr):
    return float(np.nansum(attr["contrib_linked"][mask]))


def attribution_rows(df: pd.DataFrame, pack: dict) -> pd.DataFrame:
    week_to_i = {w: i for i, w in enumerate(pack["weeks"])}
    weekly_ret = df.set_index("week")["market_return"].reindex(pack["weeks"]).to_numpy(
        dtype=float
    )
    assets = pack["asset_ids"]
    symbols = pack["symbols"]
    btc_ix, eth_ix = pack["btc_ix"], pack["eth_ix"]
    rows = []
    mask = df["is_top10_12w"].fillna(False) | df["is_bottom10_12w"].fillna(False)
    sub = df.loc[mask].copy()
    for _, rec in sub.iterrows():
        t = week_to_i.get(rec["week"])
        if t is None:
            continue
        attr = horizon_attribution(t, 12, pack, weekly_ret)
        if attr is None:
            continue
        if rec["is_top5_12w"]:
            lab = "TOP5_12W"
        elif rec["is_top10_12w"]:
            lab = "TOP10_12W"
        elif rec["is_bottom5_12w"]:
            lab = "BOTTOM5_12W"
        else:
            lab = "BOTTOM10_12W"
        cid = rec.get("cluster_top10_12w") if "TOP" in lab else rec.get("cluster_bottom10_12w")
        start_w = attr["start_w"]
        # top 10 by starting weight
        order_w = np.argsort(-np.where(np.isfinite(start_w), start_w, -np.inf))
        top10_mask = np.zeros(len(assets), dtype=bool)
        picked = 0
        for j in order_w:
            if not np.isfinite(start_w[j]):
                break
            top10_mask[j] = True
            picked += 1
            if picked >= 10:
                break
        lc_mask = pack["lc_lag_mask"][t]
        btc_m = np.zeros(len(assets), dtype=bool)
        eth_m = np.zeros(len(assets), dtype=bool)
        if btc_ix is not None:
            btc_m[btc_ix] = True
        if eth_ix is not None:
            eth_m[eth_ix] = True
        rest = ~(btc_m | eth_m)
        groups = [
            ("BTC", btc_m, "BTC" if btc_ix is None else symbols[btc_ix], btc_ix),
            ("ETH", eth_m, "ETH" if eth_ix is None else symbols[eth_ix], eth_ix),
            ("TOP10_BY_START_WEIGHT", top10_mask, "TOP10", None),
            ("LARGECAP_LAGGED", lc_mask, "LARGECAP_LAGGED", None),
            ("REST_EX_BTC_ETH", rest, "REST", None),
        ]
        base = {
            "episode_week": rec["week"],
            "horizon": 12,
            "episode_label": lab,
            "cluster_id": cid if np.isfinite(cid) else np.nan,
            "market_future_return": attr["mkt_cum"],
            "market_sum_weekly_returns": attr["mkt_sum"],
            "contribution_identity_gap": attr["identity_gap"],
            "broad_breadth_at_start": rec["broad_breadth_4w"],
            "largecap_breadth_lagged_at_start": rec["largecap_breadth_4w_lagged"],
        }
        for gname, gmask, gsym, gix in groups:
            if not gmask.any():
                continue
            sw = float(np.nansum(start_w[gmask])) if gix is None else float(start_w[gix])
            aw = float(np.nansum(attr["avg_w"][gmask])) if gix is None else float(attr["avg_w"][gix])
            if gix is None:
                ac = np.nan
            else:
                ac = float(attr["asset_cum"][gix])
            rows.append(
                {
                    **base,
                    "row_type": "GROUP",
                    "asset_id": "" if gix is None else assets[gix],
                    "group": gname,
                    "symbol": gsym,
                    "starting_weight": sw,
                    "avg_weight": aw,
                    "asset_cumulative_return": ac,
                    "contribution": group_slice(gmask, attr),
                    "contribution_unlinked": float(np.nansum(attr["contrib_unlinked"][gmask])),
                }
            )
        linked = attr["contrib_linked"]
        top_c = np.argsort(-linked)[:10]
        bot_c = np.argsort(linked)[:10]
        for rank, j in enumerate(top_c, 1):
            rows.append(
                {
                    **base,
                    "row_type": "TOP_CONTRIBUTOR",
                    "asset_id": assets[j],
                    "group": f"TOP_CONTRIBUTOR_{rank}",
                    "symbol": symbols[j],
                    "starting_weight": float(start_w[j]) if np.isfinite(start_w[j]) else np.nan,
                    "avg_weight": float(attr["avg_w"][j]),
                    "asset_cumulative_return": float(attr["asset_cum"][j])
                    if np.isfinite(attr["asset_cum"][j])
                    else np.nan,
                    "contribution": float(linked[j]),
                    "contribution_unlinked": float(attr["contrib_unlinked"][j]),
                }
            )
        for rank, j in enumerate(bot_c, 1):
            rows.append(
                {
                    **base,
                    "row_type": "BOTTOM_CONTRIBUTOR",
                    "asset_id": assets[j],
                    "group": f"BOTTOM_CONTRIBUTOR_{rank}",
                    "symbol": symbols[j],
                    "starting_weight": float(start_w[j]) if np.isfinite(start_w[j]) else np.nan,
                    "avg_weight": float(attr["avg_w"][j]),
                    "asset_cumulative_return": float(attr["asset_cum"][j])
                    if np.isfinite(attr["asset_cum"][j])
                    else np.nan,
                    "contribution": float(linked[j]),
                    "contribution_unlinked": float(attr["contrib_unlinked"][j]),
                }
            )
    return pd.DataFrame(rows)


def cond_table(df: pd.DataFrame, mask: pd.Series, h: int) -> dict:
    sub = df.loc[mask]
    r = sub[f"future_return_{h}w"].dropna()
    dd = sub[f"max_drawdown_future_{h}w"].dropna()
    n = int(len(r))
    if n == 0:
        return {
            "N": 0,
            "pos": np.nan,
            "median": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "gt10": np.nan,
            "lt10": np.nan,
            "med_dd": np.nan,
        }
    return {
        "N": n,
        "pos": float((r > 0).mean()),
        "median": float(r.median()),
        "p25": float(r.quantile(0.25)),
        "p75": float(r.quantile(0.75)),
        "gt10": float((r > 0.10).mean()),
        "lt10": float((r < -0.10).mean()),
        "med_dd": float(dd.median()) if len(dd) else np.nan,
    }


def md_cond_row(name: str, d4: dict, d12: dict) -> str:
    def cells(d):
        return (
            f"{d['N']} | {fmt_pct(d['pos'])} | {fmt_pct(d['median'])} | "
            f"{fmt_pct(d['p25'])} | {fmt_pct(d['p75'])} | {fmt_pct(d['gt10'])} | "
            f"{fmt_pct(d['lt10'])} | {fmt_pct(d['med_dd'])}"
        )

    return f"| {name} | {cells(d4)} | {cells(d12)} |"


def feat_block(df: pd.DataFrame, mask_a, mask_b, name_a, name_b) -> str:
    lines = [
        f"| feature | {name_a} N/mean/median/p25/p75 | {name_b} N/mean/median/p25/p75 |",
        "|---|---|---|",
    ]
    for c in FEATURE_COLS:
        a = summarize_num(df.loc[mask_a, c])
        b = summarize_num(df.loc[mask_b, c])
        lines.append(
            f"| {c} | {a['N']} / {fmt(a['mean'])} / {fmt(a['median'])} / "
            f"{fmt(a['p25'])} / {fmt(a['p75'])} | {b['N']} / {fmt(b['mean'])} / "
            f"{fmt(b['median'])} / {fmt(b['p25'])} / {fmt(b['p75'])} |"
        )
    return "\n".join(lines)


def write_analysis(df, attr, pack, lagged_cmp) -> None:
    ok4 = df["future_return_4w"].notna()
    ok12 = df["future_return_12w"].notna()
    n4 = int(ok4.sum())
    n12 = int(ok12.sum())

    def cnt(col):
        return int(df[col].fillna(False).sum())

    def cnt_keep(col):
        return int(df[col].fillna(False).sum())

    top12 = df.loc[ok12].nlargest(10, "future_return_12w")
    bot12 = df.loc[ok12].nsmallest(10, "future_return_12w")

    def episode_list(frame):
        lines = []
        for _, r in frame.iterrows():
            lines.append(
                f"- {r['week']} {r['market_state']} {r['breadth_quality']}: "
                f"12w={fmt_pct(r['future_return_12w'])}, 4w={fmt_pct(r['future_return_4w'])}, "
                f"MOM4={fmt_pct(r['MOM_4W'])} (pctl {fmt(r['MOM_4W_PERCENTILE'], 3)}), "
                f"MOM12={fmt_pct(r['MOM_12W'])} (pctl {fmt(r['MOM_12W_PERCENTILE'], 3)}), "
                f"broad={fmt(r['broad_breadth_4w'], 3)}, "
                f"lc_lag={fmt(r['largecap_breadth_4w_lagged'], 3)}, "
                f"VOL pctl={fmt(r['VOL_PERCENTILE'], 3)}, "
                f"TOVER_REL={fmt(r['TURNOVER_RELATIVE'], 3)}, "
                f"SC12={fmt_pct(r['STABLECOIN_MCAP_12W_CHANGE'])}"
            )
        return "\n".join(lines)

    # attribution summary for top/bottom 10 12w
    def attr_summary(weeks, label_prefix):
        lines = []
        if attr.empty:
            return "No attribution rows."
        for w in weeks:
            sub = attr[(attr["episode_week"] == w) & (attr["row_type"] == "GROUP")]
            if sub.empty:
                continue
            mkt = sub["market_future_return"].iloc[0]
            gap = sub["contribution_identity_gap"].iloc[0]
            bits = [f"**{w}** market 12w={fmt_pct(mkt)} (identity gap {fmt(gap, 6)})"]
            for g in (
                "BTC",
                "ETH",
                "TOP10_BY_START_WEIGHT",
                "LARGECAP_LAGGED",
                "REST_EX_BTC_ETH",
            ):
                row = sub[sub["group"] == g]
                if row.empty:
                    continue
                rr = row.iloc[0]
                share = rr["contribution"] / mkt if np.isfinite(mkt) and mkt != 0 else np.nan
                bits.append(
                    f"{g}: contrib={fmt_pct(rr['contribution'])} "
                    f"({fmt_pct(share)} of cum), start_w={fmt(rr['starting_weight'], 3)}"
                )
            tops = attr[
                (attr["episode_week"] == w) & (attr["row_type"] == "TOP_CONTRIBUTOR")
            ].head(5)
            names = ", ".join(
                f"{x.symbol} {fmt_pct(x.contribution)}" for x in tops.itertuples()
            )
            bits.append(f"top contributors: {names}")
            lines.append("- " + "; ".join(bits))
        return "\n".join(lines) if lines else "NA"

    bull = df["state_direction"] == "BULL"
    bull4 = bull & ok4
    bull12 = bull & ok12
    n_bull_c4 = int((df["BULL_CONTINUATION_4W"] == True).sum())
    n_bull_f4 = int((df["BULL_FAILURE_4W"] == True).sum())
    n_bull_c12 = int((df["BULL_CONTINUATION_12W"] == True).sum())
    n_bull_f12 = int((df["BULL_FAILURE_12W"] == True).sum())

    header_cond = (
        "| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 "
        "| N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |"
    )
    sep_cond = "|" + "---|" * 17

    def bucket_md(series, labels_order, complete=df):
        lines = [header_cond, sep_cond]
        for lab in labels_order:
            m = series == lab
            d4 = cond_table(complete, m & ok4, 4)
            d12 = cond_table(complete, m & ok12, 12)
            lines.append(md_cond_row(lab, d4, d12))
        return "\n".join(lines)

    # bull quality combos
    df = df.copy()
    df["mom12_int"] = df["MOM_12W_PERCENTILE"].map(mom_bucket)
    df["part_broad"] = np.where(
        df["breadth_quality"] == "BROAD", "BROAD", "NOT_BROAD"
    )
    df["liq_sc"] = np.where(
        df["STABLECOIN_MCAP_12W_CHANGE"] > 0,
        "SC_EXPANDING",
        np.where(
            np.isfinite(df["STABLECOIN_MCAP_12W_CHANGE"]),
            "SC_CONTRACTING",
            "NA",
        ),
    )
    df["liq_to"] = np.where(
        df["TURNOVER_RELATIVE"] > 1.0,
        "TOVER_ABOVE_MED",
        np.where(np.isfinite(df["TURNOVER_RELATIVE"]), "TOVER_BELOW_MED", "NA"),
    )

    combo_lines = [header_cond, sep_cond]
    combo_defs = [
        ("BULL | MOM12 <40", bull & (df["mom12_int"] == "<40")),
        ("BULL | MOM12 40-70", bull & (df["mom12_int"] == "40-70")),
        ("BULL | MOM12 70-90", bull & (df["mom12_int"] == "70-90")),
        ("BULL | MOM12 >=90", bull & (df["mom12_int"] == ">=90")),
        ("BULL | BROAD", bull & (df["part_broad"] == "BROAD")),
        ("BULL | NOT_BROAD", bull & (df["part_broad"] == "NOT_BROAD")),
        ("BULL | NORMAL_VOL", bull & (df["volatility_state"] == "NORMAL_VOL")),
        ("BULL | HIGH_VOL", bull & (df["volatility_state"] == "HIGH_VOL")),
        ("BULL | SC_EXPANDING", bull & (df["liq_sc"] == "SC_EXPANDING")),
        ("BULL | SC_CONTRACTING", bull & (df["liq_sc"] == "SC_CONTRACTING")),
        ("BULL | TOVER_ABOVE", bull & (df["liq_to"] == "TOVER_ABOVE_MED")),
        ("BULL | TOVER_BELOW", bull & (df["liq_to"] == "TOVER_BELOW_MED")),
        (
            "BULL | MOM12>=70 | BROAD",
            bull & df["mom12_int"].isin(["70-90", ">=90"]) & (df["part_broad"] == "BROAD"),
        ),
        (
            "BULL | MOM12>=70 | NOT_BROAD",
            bull & df["mom12_int"].isin(["70-90", ">=90"]) & (df["part_broad"] == "NOT_BROAD"),
        ),
        (
            "BULL | MOM12>=70 | NORMAL_VOL",
            bull
            & df["mom12_int"].isin(["70-90", ">=90"])
            & (df["volatility_state"] == "NORMAL_VOL"),
        ),
        (
            "BULL | BROAD | NORMAL_VOL",
            bull & (df["part_broad"] == "BROAD") & (df["volatility_state"] == "NORMAL_VOL"),
        ),
        (
            "BULL | MOM12>=70 | BROAD | NORMAL_VOL",
            bull
            & df["mom12_int"].isin(["70-90", ">=90"])
            & (df["part_broad"] == "BROAD")
            & (df["volatility_state"] == "NORMAL_VOL"),
        ),
    ]
    for name, m in combo_defs:
        n_all = int((m & ok12).sum())
        flag = "" if n_all >= 20 else " *(N<20 ALL WEEKS)*"
        combo_lines.append(
            md_cond_row(name + flag, cond_table(df, m & ok4, 4), cond_table(df, m & ok12, 12))
        )

    # case study
    case_lines = []
    for w in CASE_WEEKS:
        row = df[df["week"] == w]
        if row.empty:
            case_lines.append(f"- {w}: not in sample")
            continue
        r = row.iloc[0]
        case_lines.append(
            f"- **{w}** {r['market_state']} / {r['breadth_quality']}: "
            f"MOM4={fmt_pct(r['MOM_4W'])} pctl={fmt(r['MOM_4W_PERCENTILE'], 3)}; "
            f"MOM12={fmt_pct(r['MOM_12W'])} pctl={fmt(r['MOM_12W_PERCENTILE'], 3)}; "
            f"broad={fmt(r['broad_breadth_4w'], 3)}; "
            f"lc_v1={fmt(r['largecap_breadth_4w'], 3)}; "
            f"lc_lag={fmt(r['largecap_breadth_4w_lagged'], 3)}; "
            f"VOL={fmt(r['VOL_12W'], 4)} pctl={fmt(r['VOL_PERCENTILE'], 3)} {r['volatility_state']}; "
            f"TOVER_REL={fmt(r['TURNOVER_RELATIVE'], 3)}; "
            f"SC4={fmt_pct(r['STABLECOIN_MCAP_4W_CHANGE'])} "
            f"SC12={fmt_pct(r['STABLECOIN_MCAP_12W_CHANGE'])}; "
            f"fut4={fmt_pct(r['future_return_4w'])} fut12={fmt_pct(r['future_return_12w'])}; "
            f"dd4={fmt_pct(r['max_drawdown_future_4w'])} dd12={fmt_pct(r['max_drawdown_future_12w'])}"
        )
        if not attr.empty:
            g = attr[(attr["episode_week"] == w) & (attr["row_type"] == "GROUP")]
            if not g.empty:
                bits = []
                for gn in ("BTC", "ETH", "TOP10_BY_START_WEIGHT", "LARGECAP_LAGGED", "REST_EX_BTC_ETH"):
                    rr = g[g["group"] == gn]
                    if rr.empty:
                        continue
                    bits.append(f"{gn}={fmt_pct(rr.iloc[0]['contribution'])}")
                case_lines.append("  - attribution 12w: " + ", ".join(bits))

    p90_12 = df.attrs.get("p90_12w", np.nan)
    md = f"""# Opportunity episode analysis (Phase 3)

Sample: weekly crypto state through **{SAMPLE_END}**. Forward outcomes require a complete 4w or 12w path. **2024–2026 not used. Macro not used.**

Outcome percentiles and P90/P95 labels are **retrospective catalog tools**. They are not features and not trading rules.

Expanding `MOM_*_PERCENTILE` uses only MOM history through t.

Attribution contribution is **wealth-path linked**: at each future week s, `W_{{s-1}} * w_{{i,s-1}} * r_{{i,s}}`. These sum to the exact cumulative market return. Unlinked `sum(w*r)` is also stored; it equals the sum of weekly market returns, not the compound return. Identity gap is documented per episode.

Lagged large-cap: top 100 among eligible-at-t by **mcap t-1**. V1 contemporaneous column is retained.

---

## DESCRIPTIVE FINDINGS

### 1–3. Episode counts

Complete 4w weeks: **{n4}**. Complete 12w weeks: **{n12}**.

| label | ALL 4w | de-clustered 4w (cooldown 4) | ALL 12w | de-clustered 12w (cooldown 12) |
|---|---:|---:|---:|---:|
| TOP25 | {cnt('is_top25_4w')} | {cnt_keep('decluster_keep_top25_4w')} | {cnt('is_top25_12w')} | {cnt_keep('decluster_keep_top25_12w')} |
| TOP10 | {cnt('is_top10_4w')} | {cnt_keep('decluster_keep_top10_4w')} | {cnt('is_top10_12w')} | {cnt_keep('decluster_keep_top10_12w')} |
| TOP5 | {cnt('is_top5_4w')} | {cnt_keep('decluster_keep_top5_4w')} | {cnt('is_top5_12w')} | {cnt_keep('decluster_keep_top5_12w')} |
| BOTTOM25 | {cnt('is_bottom25_4w')} | {cnt_keep('decluster_keep_bottom25_4w')} | {cnt('is_bottom25_12w')} | {cnt_keep('decluster_keep_bottom25_12w')} |
| BOTTOM10 | {cnt('is_bottom10_4w')} | {cnt_keep('decluster_keep_bottom10_4w')} | {cnt('is_bottom10_12w')} | {cnt_keep('decluster_keep_bottom10_12w')} |
| BOTTOM5 | {cnt('is_bottom5_4w')} | {cnt_keep('decluster_keep_bottom5_4w')} | {cnt('is_bottom5_12w')} | {cnt_keep('decluster_keep_bottom5_12w')} |

De-clustering keeps the **first** week of a consecutive run, then enforces cooldown so overlapping windows are not counted as independent episodes. Unfavorable episodes are not dropped preferentially.

12w Extreme Opportunity threshold (historical P90 of complete 12w returns): {fmt_pct(p90_12)}.

### 4. Ten best 12w episodes (ALL WEEKS)

{episode_list(top12)}

### 5. Ten worst 12w episodes (ALL WEEKS)

{episode_list(bot12)}

### 6–7. Who produced extreme 12w moves?

Wealth-linked group contributions for the ten best:

{attr_summary(list(top12['week']), 'TOP')}

Ten worst:

{attr_summary(list(bot12['week']), 'BOTTOM')}

Lagged vs V1 large-cap breadth (all weeks with both finite): N={lagged_cmp['N']}, median |Δ|={fmt(lagged_cmp['median_abs'])}, max |Δ|={fmt(lagged_cmp['max_abs'])}, share differing by >5pp={fmt_pct(lagged_cmp['share_gt5pp'])}.

### 8–13. What did extremes look like *before* they happened?

TOP10 vs rest (12w complete):

{feat_block(df, df['is_top10_12w'].fillna(False) & ok12, ok12 & ~df['is_top10_12w'].fillna(False), 'TOP10_12w', 'rest')}

BOTTOM10 vs rest (12w complete):

{feat_block(df, df['is_bottom10_12w'].fillna(False) & ok12, ok12 & ~df['is_bottom10_12w'].fillna(False), 'BOTTOM10_12w', 'rest')}

TOP5 vs rest and BOTTOM5 vs rest are in the catalog flags; distributions follow the same pattern as TOP10/BOTTOM10 at a smaller N.

### 14. Bull continuation vs Bull failure

Bull weeks with complete 4w: continuation N={n_bull_c4}, failure N={n_bull_f4}.  
Bull weeks with complete 12w: continuation N={n_bull_c12}, failure N={n_bull_f12}.

4w:

{feat_block(df, df['BULL_CONTINUATION_4W']==True, df['BULL_FAILURE_4W']==True, 'BULL_CONT_4W', 'BULL_FAIL_4W')}

12w:

{feat_block(df, df['BULL_CONTINUATION_12W']==True, df['BULL_FAILURE_12W']==True, 'BULL_CONT_12W', 'BULL_FAIL_12W')}

### 15. Monotonicity (frozen buckets)

MOM_4W_PERCENTILE:

{bucket_md(df['MOM_4W_PERCENTILE'].map(mom_bucket), ['<40','40-70','70-90','>=90'])}

MOM_12W_PERCENTILE:

{bucket_md(df['MOM_12W_PERCENTILE'].map(mom_bucket), ['<40','40-70','70-90','>=90'])}

Broad breadth:

{bucket_md(df['broad_breadth_4w'].map(breadth_bucket), ['<40%','40-50%','50-60%','60-70%','70-80%','>=80%'])}

VOL_PERCENTILE:

{bucket_md(df['VOL_PERCENTILE'].map(vol_bucket), ['<40','40-70','70-90','>=90'])}

TURNOVER_RELATIVE:

{bucket_md(df['TURNOVER_RELATIVE'].map(tover_bucket), ['<0.75','0.75-1.0','1.0-1.25','>1.25'])}

STABLECOIN_MCAP_12W_CHANGE:

{bucket_md(df['STABLECOIN_MCAP_12W_CHANGE'].map(sc12_bucket), ['<0','0-5%','5-10%','>10%'])}

### 16–17. Bull quality (univariate + limited 2–3 way)

Combinations with N<20 on ALL complete-12w weeks are flagged. De-clustered N is not used to promote sparse cells.

{chr(10).join(combo_lines)}

### 18. 2020 vs 2021 (crypto-only)

{chr(10).join(case_lines)}

These four dates are **not** the catalog. They illustrate the North Star problem: similar V1 Bull labels, opposite 12w outcomes.

---

## CANDIDATE HYPOTHESES (not predictors)

H1. Higher expanding MOM_12W percentile is associated with a better 4w/12w return distribution (check monotonicity table; do not freeze a “Strong Bull” cut from the best cell).

H2. Broader 4w participation is associated with better forward distributions than narrow participation, including inside V1 Bull.

H3. Inside Bull, HIGH_VOL does not automatically mean better continuation; it may mark late/fragile states. Treat as a hypothesis from the Bull×vol rows.

H4. Stablecoin 12w expansion and turnover above the recent median are liquidity/activity correlates, not sufficient bullish signals.

H5. Extreme 12w gains are often concentrated in BTC/large caps even when breadth looks broad. Attribution, not the headline breadth number, decides “broad vs concentrated.”

H6. Late-2020 vs late-2021 may **not** be separable on crypto internals alone. That is the reserved macro question, not answered here.

---

## 19. What crypto-only still cannot explain

- Why two BULL_NORMAL_VOL weeks with similar MOM and breadth produced +200% vs −40% 12w outcomes.
- Whether MOM/breadth gradients survive walk-forward and 2024–2026.
- Overlapping-window dependence (even de-clustered N is small in the tails).
- Wash-trading noise in CMC turnover.

## 20. What should move to Phase 4/6

KEEP as research features (not yet model thresholds):

- expanding MOM_4W / MOM_12W percentiles
- broad breadth level (not only the 0.50 Bull switch)
- lagged large-cap breadth (prefer over V1 contemporaneous if Δ is material)
- VOL_PERCENTILE overlay inside Bull
- stablecoin 12w change as a liquidity diagnostic
- extreme-episode concentration (BTC/top10 share)

DIAGNOSTIC ONLY until walk-forward:

- TURNOVER_RELATIVE
- 2020/2021 forensic dates
- +20% “strong continuation” label

DROP for now:

- using outcome percentiles as features
- sparse 3-way cells with N<20
- any macro series

---

No trading rule is implied. Descriptive findings ≠ candidate hypotheses ≠ validated predictors.
"""
    (RESULTS / "OPPORTUNITY_EPISODE_ANALYSIS.md").write_text(md, encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    weekly = pd.read_csv(V1_WEEKLY)
    weekly["week"] = pd.to_datetime(weekly["week"]).dt.strftime("%Y-%m-%d")
    weekly = weekly[weekly["week"] <= SAMPLE_END].copy()
    weekly = weekly.rename(
        columns={
            "market_return_future_4w": "future_return_4w",
            "market_return_future_12w": "future_return_12w",
        }
    )
    weekly["MOM_4W_PERCENTILE"] = expanding_percentile(
        weekly["MOM_4W"].to_numpy(dtype=float)
    )
    weekly["MOM_12W_PERCENTILE"] = expanding_percentile(
        weekly["MOM_12W"].to_numpy(dtype=float)
    )

    print("Loading panel for lagged large-cap + attribution...")
    panel = load_panel()
    panel = panel[panel["week"] <= SAMPLE_END].copy()
    pack = build_eligibility_and_weights(panel)
    lag_map = pd.DataFrame(
        {
            "week": pack["weeks"],
            "largecap_breadth_4w_lagged": pack["lc_lag_b"],
            "largecap_median_return_4w_lagged": pack["lc_lag_med"],
        }
    )
    weekly = weekly.merge(lag_map, on="week", how="left")
    weekly["breadth_gap_lagged"] = (
        weekly["largecap_breadth_4w_lagged"] - weekly["broad_breadth_4w"]
    )
    both = weekly.dropna(subset=["largecap_breadth_4w", "largecap_breadth_4w_lagged"])
    dlt = (both["largecap_breadth_4w"] - both["largecap_breadth_4w_lagged"]).abs()
    lagged_cmp = {
        "N": int(len(both)),
        "median_abs": float(dlt.median()) if len(dlt) else np.nan,
        "max_abs": float(dlt.max()) if len(dlt) else np.nan,
        "share_gt5pp": float((dlt > 0.05).mean()) if len(dlt) else np.nan,
    }
    print(
        f"lagged vs V1 largecap |Δ| median={lagged_cmp['median_abs']:.4f} "
        f"max={lagged_cmp['max_abs']:.4f}"
    )

    weekly = add_opportunity_labels(weekly)
    weekly = add_clusters(weekly)

    catalog_cols = [
        "week",
        "market_state",
        "state_direction",
        "breadth_quality",
        "MOM_4W",
        "MOM_12W",
        "MOM_4W_PERCENTILE",
        "MOM_12W_PERCENTILE",
        "broad_breadth_4w",
        "largecap_breadth_4w",
        "largecap_breadth_4w_lagged",
        "breadth_gap",
        "breadth_gap_lagged",
        "median_coin_return_4w",
        "largecap_median_return_4w",
        "largecap_median_return_4w_lagged",
        "n_eligible_coins",
        "VOL_12W",
        "VOL_PERCENTILE",
        "volatility_state",
        "market_turnover",
        "TURNOVER_RELATIVE",
        "TURNOVER_PERCENTILE",
        "STABLECOIN_MCAP",
        "STABLECOIN_MCAP_4W_CHANGE",
        "STABLECOIN_MCAP_12W_CHANGE",
        "STABLECOIN_LIQ_PERCENTILE",
        "future_return_4w",
        "future_return_12w",
        "max_drawdown_future_4w",
        "max_drawdown_future_12w",
        "max_runup_future_4w",
        "max_runup_future_12w",
        "outcome_percentile_4w",
        "outcome_percentile_12w",
        "opportunity_4w_bucket",
        "opportunity_12w_bucket",
        "label_4w_positive",
        "label_4w_strong",
        "label_4w_extreme_opp",
        "label_4w_exceptional_opp",
        "label_4w_severe_fail",
        "label_4w_extreme_fail",
        "label_12w_positive",
        "label_12w_strong",
        "label_12w_extreme_opp",
        "label_12w_exceptional_opp",
        "label_12w_severe_fail",
        "label_12w_extreme_fail",
        "is_top25_4w",
        "is_top10_4w",
        "is_top5_4w",
        "is_bottom25_4w",
        "is_bottom10_4w",
        "is_bottom5_4w",
        "is_top25_12w",
        "is_top10_12w",
        "is_top5_12w",
        "is_bottom25_12w",
        "is_bottom10_12w",
        "is_bottom5_12w",
        "BULL_CONTINUATION_4W",
        "BULL_FAILURE_4W",
        "BULL_STRONG_CONTINUATION_4W",
        "BULL_CONTINUATION_12W",
        "BULL_FAILURE_12W",
        "BULL_STRONG_CONTINUATION_12W",
        "cluster_top10_4w",
        "decluster_keep_top10_4w",
        "cluster_top5_4w",
        "decluster_keep_top5_4w",
        "cluster_bottom10_4w",
        "decluster_keep_bottom10_4w",
        "cluster_bottom5_4w",
        "decluster_keep_bottom5_4w",
        "cluster_top10_12w",
        "decluster_keep_top10_12w",
        "cluster_top5_12w",
        "decluster_keep_top5_12w",
        "cluster_bottom10_12w",
        "decluster_keep_bottom10_12w",
        "cluster_bottom5_12w",
        "decluster_keep_bottom5_12w",
        "cluster_top25_4w",
        "decluster_keep_top25_4w",
        "cluster_bottom25_4w",
        "decluster_keep_bottom25_4w",
        "cluster_top25_12w",
        "decluster_keep_top25_12w",
        "cluster_bottom25_12w",
        "decluster_keep_bottom25_12w",
    ]
    catalog = weekly[catalog_cols].copy()
    catalog.to_csv(RESULTS / "opportunity_episode_catalog.csv", index=False)
    print(f"catalog rows={len(catalog)}")

    print("Attribution for 12w TOP10/BOTTOM10...")
    attr = attribution_rows(weekly, pack)
    attr.to_csv(RESULTS / "extreme_episode_attribution.csv", index=False)
    print(f"attribution rows={len(attr)}")

    write_analysis(weekly, attr, pack, lagged_cmp)
    print("wrote", RESULTS / "OPPORTUNITY_EPISODE_ANALYSIS.md")


if __name__ == "__main__":
    main()
