#!/usr/bin/env python3
"""Crypto Market State Observatory v1 — weekly core.

MEASURE STATE → COMPARE HISTORY → FORWARD OUTCOMES → AUDIT

Independent of Hsieh / Wen / Moskowitz / BTC rally-map code.
Reads the Hsieh weekly panel as a frozen input file. Does not modify it.
Does not download data. Does not implement trading, macro, or ML.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OBS_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = OBS_DIR / "results"
PANEL_PATH = (
    OBS_DIR.parents[1]
    / "papers"
    / "hsieh_2025_state_transition_momentum"
    / "data"
    / "processed"
    / "crypto_weekly_panel.csv"
)

PRIMARY_MIN_MCAP = 10_000_000.0
ROBUSTNESS_MIN_MCAP = {
    "universe_1m": 1_000_000.0,
    "universe_10m": 10_000_000.0,
    "universe_50m": 50_000_000.0,
}
MIN_HISTORY_WEEKS = 26
MOM_SHORT = 4
MOM_LONG = 12
VOL_WINDOW = 12
TURNOVER_WINDOW = 12
LARGECAP_N = 100
HIGH_VOL_PERCENTILE = 0.70
BREADTH_BULL_BEAR = 0.50
BREADTH_BROAD = 0.60
BREADTH_NARROW_BROAD = 0.50
BREADTH_WEAK = 0.40
ANALOG_K = 25
ANALOG_EXCLUDE_RECENT = 12
INDEX_START = 100.0

# Observatory-owned stablecoin screen. NOT the Hsieh is_stablecoin column
# (that heuristic false-positives APT, ATOM, UNI, TON, FTT, FXS, etc.).
# Gold-pegged tokens are excluded. Wrapped USD stables are included via alias.
STABLECOIN_SYMBOLS = frozenset(
    {
        "USDT",
        "USDC",
        "DAI",
        "SAI",
        "BUSD",
        "TUSD",
        "FDUSD",
        "USDP",
        "PAX",
        "GUSD",
        "FRAX",
        "LUSD",
        "USDD",
        "UST",
        "USTC",
        "FEI",
        "MIM",
        "SUSD",
        "USDJ",
        "CUSD",
        "USDN",
        "HUSD",
        "USDK",
        "PYUSD",
        "EURC",
        "EURT",
        "EURS",
        "EUROE",
        "USDE",
        "USDS",
        "CRVUSD",
        "GHO",
        "DOLA",
        "OUSD",
        "ALUSD",
        "USDQ",
        "USDH",
        "USDC.E",
        "USDCE",
        "USDT.E",
        "USDTE",
        "CUSDC",
        "EURT".upper(),
        "CNHT",
        "CNYT",
        "MXNT",
        "NZDS",
        "GUSD",
        "TUSD",
        "BUSD",
        "FDUSD",
        "PYUSD",
        "CRVFRAX",
        "FFRAX",
        "BABYTETHER",
    }
)

STABLECOIN_ALIASES = {
    "USDC(WORMHOLE)": "USDC",
    "USDC.E": "USDC",
    "USDCE": "USDC",
    "USDT.E": "USDT",
    "USDTE": "USDT",
    "EURT": "EURT",
    "EURT".upper(): "EURT",
}


def normalize_symbol(symbol) -> str:
    if pd.isna(symbol):
        return ""
    s = str(symbol).upper().strip().replace(" ", "")
    s = s.replace("(WORMHOLE)", "")
    return STABLECOIN_ALIASES.get(s, s)


def is_observatory_stablecoin(symbol) -> bool:
    s = normalize_symbol(symbol)
    return s in STABLECOIN_SYMBOLS


def expanding_percentile(values: np.ndarray) -> np.ndarray:
    """Empirical CDF at t using values with index <= t only. No future data."""
    out = np.full(len(values), np.nan, dtype=float)
    hist: list[float] = []
    for i, v in enumerate(values):
        if np.isfinite(v):
            hist.append(float(v))
            arr = np.asarray(hist, dtype=float)
            out[i] = float(np.mean(arr <= arr[-1]))
    return out


def rolling_window_ok(values: np.ndarray, window: int) -> np.ndarray:
    n = len(values)
    ok = np.zeros(n, dtype=bool)
    finite = np.isfinite(values)
    if n < window:
        return ok
    csum = np.concatenate([[0], np.cumsum(finite.astype(int))])
    for i in range(window - 1, n):
        ok[i] = (csum[i + 1] - csum[i + 1 - window]) == window
    return ok


def cumulative_simple(returns: np.ndarray, window: int) -> np.ndarray:
    """prod(1+r) - 1 over the last `window` observations, else NaN."""
    n = len(returns)
    out = np.full(n, np.nan, dtype=float)
    ok = rolling_window_ok(returns, window)
    log1p = np.full(n, np.nan, dtype=float)
    finite = np.isfinite(returns)
    log1p[finite] = np.log1p(np.clip(returns[finite], -0.999999, None))
    csum = np.nancumsum(np.where(finite, log1p, 0.0))
    for i in range(n):
        if not ok[i]:
            continue
        start = i - window + 1
        prev = csum[start - 1] if start > 0 else 0.0
        out[i] = float(np.expm1(csum[i] - prev))
    return out


def path_drawdown_runup(future_returns: np.ndarray) -> tuple[float, float, float]:
    """Wealth starts at 1 at t. Future path uses t+1, ..., t+h only.

    max_drawdown: min_k (W_k / running_peak_k - 1), peak includes W_0=1.
    max_runup: max_k (W_k - 1) vs the level at t.
    cumulative: W_h - 1.
    """
    if future_returns.size == 0 or not np.all(np.isfinite(future_returns)):
        return np.nan, np.nan, np.nan
    wealth = np.concatenate([[1.0], np.cumprod(1.0 + future_returns)])
    peak = np.maximum.accumulate(wealth)
    max_dd = float(np.min(wealth / peak - 1.0))
    max_ru = float(np.max(wealth - 1.0))
    cum = float(wealth[-1] - 1.0)
    return cum, max_dd, max_ru


def summarize_forward(df: pd.DataFrame, group_type: str, group_value: str) -> dict:
    row = {
        "group_type": group_type,
        "group_value": group_value,
    }
    for h, ret_col, dd_col, ru_col in (
        (1, "market_return_future_1w", None, None),
        (4, "market_return_future_4w", "max_drawdown_future_4w", "max_runup_future_4w"),
        (12, "market_return_future_12w", "max_drawdown_future_12w", "max_runup_future_12w"),
    ):
        r = df[ret_col].dropna()
        n = int(r.shape[0])
        row[f"n_{h}w"] = n
        if n == 0:
            for k in (
                f"mean_future_return_{h}w",
                f"median_future_return_{h}w",
                f"hist_freq_return_gt_0_{h}w",
                f"hist_freq_return_gt_10pct_{h}w",
                f"hist_freq_return_lt_m10pct_{h}w",
                f"p10_future_return_{h}w",
                f"p25_future_return_{h}w",
                f"p75_future_return_{h}w",
                f"p90_future_return_{h}w",
            ):
                row[k] = np.nan
            if dd_col is not None:
                row[f"median_max_drawdown_{h}w"] = np.nan
                row[f"hist_freq_drawdown_le_m10pct_{h}w"] = np.nan
                row[f"median_max_runup_{h}w"] = np.nan
            continue
        row[f"mean_future_return_{h}w"] = float(r.mean())
        row[f"median_future_return_{h}w"] = float(r.median())
        row[f"hist_freq_return_gt_0_{h}w"] = float((r > 0).mean())
        row[f"hist_freq_return_gt_10pct_{h}w"] = float((r > 0.10).mean())
        row[f"hist_freq_return_lt_m10pct_{h}w"] = float((r < -0.10).mean())
        row[f"p10_future_return_{h}w"] = float(r.quantile(0.10))
        row[f"p25_future_return_{h}w"] = float(r.quantile(0.25))
        row[f"p75_future_return_{h}w"] = float(r.quantile(0.75))
        row[f"p90_future_return_{h}w"] = float(r.quantile(0.90))
        if dd_col is not None:
            dd = df[dd_col].dropna()
            ru = df[ru_col].dropna()
            row[f"median_max_drawdown_{h}w"] = float(dd.median()) if len(dd) else np.nan
            row[f"hist_freq_drawdown_le_m10pct_{h}w"] = (
                float((dd <= -0.10).mean()) if len(dd) else np.nan
            )
            row[f"median_max_runup_{h}w"] = float(ru.median()) if len(ru) else np.nan
    return row


def load_panel() -> pd.DataFrame:
    if not PANEL_PATH.exists():
        raise FileNotFoundError(
            f"Frozen Hsieh panel not found (do not re-download): {PANEL_PATH}"
        )
    df = pd.read_csv(PANEL_PATH)
    required = {
        "week",
        "asset_id",
        "symbol",
        "weekly_price",
        "weekly_return",
        "market_cap",
        "volume",
        "is_stablecoin",
        "eligible",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Panel missing columns {sorted(missing)}")
    df["week"] = pd.to_datetime(df["week"]).dt.strftime("%Y-%m-%d")
    df = df.drop_duplicates(["week", "asset_id"], keep="last")
    # Source weekly_return is log return: ln(P_t / P_{t-1}). Convert to simple.
    df["simple_return"] = np.where(
        np.isfinite(df["weekly_return"].to_numpy(dtype=float)),
        np.expm1(df["weekly_return"].to_numpy(dtype=float)),
        np.nan,
    )
    df["obs_stablecoin"] = df["symbol"].map(is_observatory_stablecoin)
    return df


def calendar_wide(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    wide = panel.pivot(index="week", columns="asset_id", values=col)
    wide = wide.sort_index()
    return wide


def coin_cumret_wide(simple_wide: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calendar-week cumulative simple return. Gaps break the window."""
    logs = np.log1p(simple_wide.clip(lower=-0.999999))
    roll_sum = logs.rolling(window, min_periods=window).sum()
    roll_n = logs.rolling(window, min_periods=window).count()
    roll_sum = roll_sum.where(roll_n == window)
    return np.expm1(roll_sum)


def history_count_wide(price_wide: pd.DataFrame) -> pd.DataFrame:
    valid = price_wide.notna() & (price_wide > 0)
    return valid.cumsum()


def compute_weekly_core(
    panel: pd.DataFrame,
    min_mcap: float,
    simple_wide: pd.DataFrame,
    mcap_wide: pd.DataFrame,
    volume_wide: pd.DataFrame,
    price_wide: pd.DataFrame,
    hist_wide: pd.DataFrame,
    ret4_wide: pd.DataFrame,
    stable_asset_ids: set,
) -> pd.DataFrame:
    weeks = list(simple_wide.index)
    asset_ids = list(simple_wide.columns)
    n_w = len(weeks)
    n_a = len(asset_ids)

    simple = simple_wide.to_numpy(dtype=float)
    mcap = mcap_wide.to_numpy(dtype=float)
    volume = volume_wide.to_numpy(dtype=float)
    price = price_wide.to_numpy(dtype=float)
    hist = hist_wide.to_numpy(dtype=float)
    ret4 = ret4_wide.to_numpy(dtype=float)
    lag_mcap = np.vstack([np.full((1, n_a), np.nan), mcap[:-1]])

    is_stable = np.array(
        [aid in stable_asset_ids for aid in asset_ids], dtype=bool
    )

    finite_ret = np.isfinite(simple)
    mcap_ok = np.isfinite(mcap) & (mcap > 0) & (mcap >= min_mcap)
    vol_ok = np.isfinite(volume) & (volume > 0)
    price_ok = np.isfinite(price) & (price > 0)
    hist_ok = hist >= MIN_HISTORY_WEEKS
    eligible = (
        (~is_stable[None, :])
        & mcap_ok
        & finite_ret
        & vol_ok
        & price_ok
        & hist_ok
    )

    records = []
    largecap_lt_100_weeks = []
    for t in range(n_w):
        elig = eligible[t]
        n_elig = int(elig.sum())
        w_lag = np.where(elig, lag_mcap[t], np.nan)
        w_lag = np.where(np.isfinite(w_lag) & (w_lag > 0), w_lag, np.nan)
        w_sum = np.nansum(w_lag)
        if w_sum > 0 and np.isfinite(w_sum):
            weights = w_lag / w_sum
            mkt_r = float(np.nansum(weights * simple[t]))
        else:
            mkt_r = np.nan

        r4 = np.where(elig, ret4[t], np.nan)
        r4_fin = r4[np.isfinite(r4)]
        n_r4 = int(r4_fin.size)
        if n_r4 > 0:
            broad = float(np.mean(r4_fin > 0))
            med_r4 = float(np.median(r4_fin))
            p25_r4 = float(np.percentile(r4_fin, 25))
            p75_r4 = float(np.percentile(r4_fin, 75))
        else:
            broad = med_r4 = p25_r4 = p75_r4 = np.nan

        mcap_t = np.where(elig, mcap[t], np.nan)
        order = np.argsort(-np.where(np.isfinite(mcap_t), mcap_t, -np.inf))
        n_large = min(LARGECAP_N, n_elig)
        large_mask = np.zeros(n_a, dtype=bool)
        if n_elig > 0:
            large_mask[order[:n_large]] = True
            if n_elig < LARGECAP_N:
                largecap_lt_100_weeks.append(weeks[t])

        r4_lc = np.where(large_mask, ret4[t], np.nan)
        r4_lc_fin = r4_lc[np.isfinite(r4_lc)]
        n_lc_r4 = int(r4_lc_fin.size)
        if n_lc_r4 > 0:
            lc_broad = float(np.mean(r4_lc_fin > 0))
            lc_med = float(np.median(r4_lc_fin))
        else:
            lc_broad = lc_med = np.nan

        tover = np.full(n_a, np.nan, dtype=float)
        np.divide(
            volume[t],
            mcap[t],
            out=tover,
            where=elig
            & np.isfinite(volume[t])
            & np.isfinite(mcap[t])
            & (mcap[t] > 0),
        )
        tover = np.where(np.isfinite(tover), tover, np.nan)
        tover_fin = tover[np.isfinite(tover)]
        if tover_fin.size:
            mkt_tover = float(np.median(tover_fin))
            mkt_tover_p75 = float(np.percentile(tover_fin, 75))
        else:
            mkt_tover = mkt_tover_p75 = np.nan

        records.append(
            {
                "week": weeks[t],
                "market_return": mkt_r,
                "broad_breadth_4w": broad,
                "largecap_breadth_4w": lc_broad,
                "median_coin_return_4w": med_r4,
                "p25_coin_return_4w": p25_r4,
                "p75_coin_return_4w": p75_r4,
                "largecap_median_return_4w": lc_med,
                "market_turnover": mkt_tover,
                "market_turnover_p75": mkt_tover_p75,
                "n_eligible_coins": n_elig,
                "n_largecap_coins": int(n_large),
                "n_breadth_coins": n_r4,
            }
        )

    weekly = pd.DataFrame.from_records(records)
    r = weekly["market_return"].to_numpy(dtype=float)
    weekly["MOM_4W"] = cumulative_simple(r, MOM_SHORT)
    weekly["MOM_12W"] = cumulative_simple(r, MOM_LONG)

    idx = np.full(n_w, np.nan, dtype=float)
    level = INDEX_START
    started = False
    for i, ri in enumerate(r):
        if not np.isfinite(ri):
            idx[i] = level if started else INDEX_START
            continue
        level = level * (1.0 + ri)
        started = True
        idx[i] = level
    weekly["market_index"] = idx

    vol_ok = rolling_window_ok(r, VOL_WINDOW)
    vol = np.full(n_w, np.nan, dtype=float)
    for i in range(n_w):
        if vol_ok[i]:
            vol[i] = float(np.std(r[i - VOL_WINDOW + 1 : i + 1], ddof=1))
    weekly["VOL_12W"] = vol
    weekly["VOL_PERCENTILE"] = expanding_percentile(vol)
    weekly["volatility_state"] = np.where(
        np.isfinite(weekly["VOL_PERCENTILE"]),
        np.where(
            weekly["VOL_PERCENTILE"] >= HIGH_VOL_PERCENTILE,
            "HIGH_VOL",
            "NORMAL_VOL",
        ),
        None,
    )

    tover_s = weekly["market_turnover"].to_numpy(dtype=float)
    roll_ok = rolling_window_ok(tover_s, TURNOVER_WINDOW)
    roll_med = np.full(n_w, np.nan, dtype=float)
    for i in range(n_w):
        if roll_ok[i]:
            window = tover_s[i - TURNOVER_WINDOW + 1 : i + 1]
            roll_med[i] = float(np.median(window))
    rel = np.full(n_w, np.nan, dtype=float)
    good = np.isfinite(tover_s) & np.isfinite(roll_med) & (roll_med > 0)
    rel[good] = tover_s[good] / roll_med[good]
    weekly["TURNOVER_RELATIVE"] = rel
    weekly["TURNOVER_PERCENTILE"] = expanding_percentile(tover_s)

    weekly["breadth_gap"] = (
        weekly["largecap_breadth_4w"] - weekly["broad_breadth_4w"]
    )

    mom4 = weekly["MOM_4W"].to_numpy(dtype=float)
    mom12 = weekly["MOM_12W"].to_numpy(dtype=float)
    bb = weekly["broad_breadth_4w"].to_numpy(dtype=float)
    direction = np.array(["NEUTRAL"] * n_w, dtype=object)
    usable = np.isfinite(mom4) & np.isfinite(mom12) & np.isfinite(bb)
    direction[:] = None
    direction[usable] = "NEUTRAL"
    bull = usable & (mom4 > 0) & (mom12 > 0) & (bb > BREADTH_BULL_BEAR)
    bear = usable & (mom4 < 0) & (mom12 < 0) & (bb < BREADTH_BULL_BEAR)
    direction[bull] = "BULL"
    direction[bear] = "BEAR"
    weekly["state_direction"] = direction

    vol_state = weekly["volatility_state"].to_numpy()
    combined = np.array([None] * n_w, dtype=object)
    for i in range(n_w):
        if direction[i] is None or vol_state[i] is None:
            combined[i] = None
        else:
            combined[i] = f"{direction[i]}_{vol_state[i]}"
    weekly["market_state"] = combined

    lc = weekly["largecap_breadth_4w"].to_numpy(dtype=float)
    bq = np.array(["MIXED"] * n_w, dtype=object)
    bq_ok = np.isfinite(bb) & np.isfinite(lc)
    bq[:] = None
    bq[bq_ok] = "MIXED"
    bq[bq_ok & (bb >= BREADTH_BROAD) & (lc >= BREADTH_BROAD)] = "BROAD"
    bq[bq_ok & (lc >= BREADTH_BROAD) & (bb < BREADTH_NARROW_BROAD)] = (
        "NARROW_LARGECAP"
    )
    bq[bq_ok & (bb < BREADTH_WEAK) & (lc < BREADTH_WEAK)] = "WEAK"
    weekly["breadth_quality"] = bq

    weekly.attrs["largecap_lt_100_weeks"] = largecap_lt_100_weeks
    weekly.attrs["min_mcap"] = min_mcap
    return weekly


def add_stablecoin_liquidity(weekly: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    st = panel.loc[panel["obs_stablecoin"]].copy()
    agg = (
        st.groupby("week", as_index=False)["market_cap"]
        .sum()
        .rename(columns={"market_cap": "STABLECOIN_MCAP"})
    )
    weekly = weekly.merge(agg, on="week", how="left")
    sm = weekly["STABLECOIN_MCAP"].to_numpy(dtype=float)
    ch4 = np.full(len(sm), np.nan, dtype=float)
    ch12 = np.full(len(sm), np.nan, dtype=float)
    for i in range(len(sm)):
        if i >= 4 and np.isfinite(sm[i]) and np.isfinite(sm[i - 4]) and sm[i - 4] > 0:
            ch4[i] = sm[i] / sm[i - 4] - 1.0
        if i >= 12 and np.isfinite(sm[i]) and np.isfinite(sm[i - 12]) and sm[i - 12] > 0:
            ch12[i] = sm[i] / sm[i - 12] - 1.0
    weekly["STABLECOIN_MCAP_4W_CHANGE"] = ch4
    weekly["STABLECOIN_MCAP_12W_CHANGE"] = ch12
    weekly["STABLECOIN_LIQ_PERCENTILE"] = expanding_percentile(sm)
    return weekly


def add_forward_outcomes(weekly: pd.DataFrame) -> pd.DataFrame:
    r = weekly["market_return"].to_numpy(dtype=float)
    n = len(r)
    fut1 = np.full(n, np.nan)
    fut4 = np.full(n, np.nan)
    fut12 = np.full(n, np.nan)
    dd4 = np.full(n, np.nan)
    dd12 = np.full(n, np.nan)
    ru4 = np.full(n, np.nan)
    ru12 = np.full(n, np.nan)
    for i in range(n):
        if i + 1 < n and np.isfinite(r[i + 1]):
            fut1[i] = r[i + 1]
        if i + 4 < n:
            sl = r[i + 1 : i + 5]
            cum, dd, ru = path_drawdown_runup(sl)
            fut4[i], dd4[i], ru4[i] = cum, dd, ru
        if i + 12 < n:
            sl = r[i + 1 : i + 13]
            cum, dd, ru = path_drawdown_runup(sl)
            fut12[i], dd12[i], ru12[i] = cum, dd, ru
    weekly["market_return_future_1w"] = fut1
    weekly["market_return_future_4w"] = fut4
    weekly["market_return_future_12w"] = fut12
    weekly["max_drawdown_future_4w"] = dd4
    weekly["max_drawdown_future_12w"] = dd12
    weekly["max_runup_future_4w"] = ru4
    weekly["max_runup_future_12w"] = ru12
    return weekly


def transition_long(weekly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, matrix in (
        ("market_state", "combined"),
        ("state_direction", "direction"),
    ):
        cur = weekly[col]
        nxt = weekly[col].shift(-1)
        pair = pd.DataFrame({"from_state": cur, "to_state": nxt}).dropna()
        if pair.empty:
            continue
        ct = pair.groupby(["from_state", "to_state"], as_index=False).size()
        ct = ct.rename(columns={"size": "count"})
        tot = ct.groupby("from_state")["count"].transform("sum")
        ct["probability"] = ct["count"] / tot
        ct["matrix"] = matrix
        rows.append(ct)
    out = pd.concat(rows, ignore_index=True)
    return out.sort_values(["matrix", "from_state", "to_state"])


def forward_outcomes_table(weekly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for st, sub in weekly.groupby("market_state", dropna=True):
        rows.append(summarize_forward(sub, "market_state", str(st)))
    for bq, sub in weekly.groupby("breadth_quality", dropna=True):
        rows.append(summarize_forward(sub, "breadth_quality", str(bq)))
    tmp = weekly.dropna(subset=["state_direction", "breadth_quality"]).copy()
    tmp["dir_bq"] = tmp["state_direction"].astype(str) + "|" + tmp["breadth_quality"].astype(str)
    for key, sub in tmp.groupby("dir_bq"):
        rows.append(summarize_forward(sub, "state_direction_x_breadth_quality", str(key)))
    return pd.DataFrame(rows)


ANALOG_COLS = [
    "MOM_4W",
    "MOM_12W",
    "broad_breadth_4w",
    "largecap_breadth_4w",
    "VOL_PERCENTILE",
    "TURNOVER_RELATIVE",
    "STABLECOIN_MCAP_4W_CHANGE",
]


def historical_analogs(weekly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Z-score using history through the last sample week. Euclidean distance."""
    meta = {
        "vector": list(ANALOG_COLS),
        "stablecoin_in_vector": True,
        "standardization": "z-score using all finite observations through last week",
    }
    last_i = len(weekly) - 1
    hist = weekly.iloc[: last_i + 1]
    use_cols = list(ANALOG_COLS)
    # Keep stablecoin in the vector if it has non-trivial coverage through t.
    sc = hist["STABLECOIN_MCAP_4W_CHANGE"]
    sc_cov = float(sc.notna().mean()) if len(sc) else 0.0
    meta["stablecoin_4w_change_coverage"] = sc_cov
    if sc_cov < 0.50:
        use_cols = [c for c in use_cols if c != "STABLECOIN_MCAP_4W_CHANGE"]
        meta["stablecoin_in_vector"] = False
        meta["stablecoin_drop_reason"] = (
            f"STABLECOIN_MCAP_4W_CHANGE finite in only {sc_cov:.1%} of weeks"
        )
    meta["vector"] = use_cols

    mu = hist[use_cols].mean()
    sd = hist[use_cols].std(ddof=1)
    meta["zscore_mean"] = {k: float(mu[k]) for k in use_cols}
    meta["zscore_std"] = {k: (float(sd[k]) if np.isfinite(sd[k]) else np.nan) for k in use_cols}

    z = (weekly[use_cols] - mu) / sd.replace(0, np.nan)
    z_ok = z.notna().all(axis=1)
    current_ok = bool(z_ok.iloc[last_i])
    if not current_ok:
        meta["error"] = "current week analog vector has NaN after z-score"
        return pd.DataFrame(), meta

    z_cur = z.iloc[last_i].to_numpy(dtype=float)
    exclude = np.zeros(len(weekly), dtype=bool)
    exclude[last_i] = True
    start_ex = max(0, last_i - ANALOG_EXCLUDE_RECENT)
    exclude[start_ex:last_i] = True

    rows = []
    for i in range(len(weekly)):
        if exclude[i] or not bool(z_ok.iloc[i]):
            continue
        zi = z.iloc[i].to_numpy(dtype=float)
        dist = float(np.sqrt(np.sum((zi - z_cur) ** 2)))
        rec = weekly.iloc[i]
        rows.append(
            {
                "rank": 0,
                "week": rec["week"],
                "state": rec["market_state"],
                "breadth_quality": rec["breadth_quality"],
                "distance": dist,
                "MOM_4W": rec["MOM_4W"],
                "MOM_12W": rec["MOM_12W"],
                "broad_breadth_4w": rec["broad_breadth_4w"],
                "largecap_breadth_4w": rec["largecap_breadth_4w"],
                "VOL_PERCENTILE": rec["VOL_PERCENTILE"],
                "TURNOVER_RELATIVE": rec["TURNOVER_RELATIVE"],
                "STABLECOIN_MCAP_4W_CHANGE": rec["STABLECOIN_MCAP_4W_CHANGE"],
                "future_return_1w": rec["market_return_future_1w"],
                "future_return_4w": rec["market_return_future_4w"],
                "future_return_12w": rec["market_return_future_12w"],
                "max_drawdown_future_12w": rec["max_drawdown_future_12w"],
                "max_runup_future_12w": rec["max_runup_future_12w"],
            }
        )
    analogs = pd.DataFrame(rows)
    if analogs.empty:
        return analogs, meta
    analogs = analogs.sort_values("distance", kind="mergesort").head(ANALOG_K)
    analogs = analogs.reset_index(drop=True)
    analogs["rank"] = np.arange(1, len(analogs) + 1)
    meta["n_candidates"] = int(z_ok.sum() - int(z_ok.iloc[start_ex : last_i + 1].sum()))
    return analogs, meta


def fmt_pct(x, digits=2) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{100.0 * x:.{digits}f}%"


def fmt_num(x, digits=4) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.{digits}f}"


def write_current_report(
    weekly: pd.DataFrame,
    transitions: pd.DataFrame,
    outcomes: pd.DataFrame,
    analogs: pd.DataFrame,
    analog_meta: dict,
    panel: pd.DataFrame,
    robustness: pd.DataFrame,
    largecap_lt_100: list,
) -> str:
    last = weekly.iloc[-1]
    week = last["week"]
    state = last["market_state"]
    direction = last["state_direction"]
    vol_state = last["volatility_state"]
    mom4 = last["MOM_4W"]
    mom12 = last["MOM_12W"]
    bb = last["broad_breadth_4w"]
    lc = last["largecap_breadth_4w"]
    bq = last["breadth_quality"]
    gap = last["breadth_gap"]
    volp = last["VOL_PERCENTILE"]
    tover_rel = last["TURNOVER_RELATIVE"]
    sc4 = last["STABLECOIN_MCAP_4W_CHANGE"]
    sc12 = last["STABLECOIN_MCAP_12W_CHANGE"]
    scm = last["STABLECOIN_MCAP"]

    why = []
    why.append(
        f"Direction is {direction} because MOM_4W={fmt_pct(mom4)}, "
        f"MOM_12W={fmt_pct(mom12)}, broad_breadth_4w={fmt_num(bb, 3)}."
    )
    why.append(
        "BULL requires MOM_4W>0 AND MOM_12W>0 AND broad_breadth_4w>0.50. "
        "BEAR requires MOM_4W<0 AND MOM_12W<0 AND broad_breadth_4w<0.50. "
        "Any other combination is NEUTRAL."
    )
    why.append(
        f"Volatility overlay is {vol_state} because VOL_PERCENTILE={fmt_num(volp, 3)} "
        f"and HIGH_VOL is defined as VOL_PERCENTILE >= {HIGH_VOL_PERCENTILE:.2f}."
    )
    why.append(f"Combined market_state = {state}.")

    same = weekly.loc[weekly["market_state"] == state]
    n_same = int(same.shape[0])
    # Historical outcomes exclude the current week (no future path).
    same_hist = same.iloc[:-1] if same.index.max() == weekly.index.max() else same
    if last["week"] in set(same["week"]) and not np.isfinite(last["market_return_future_1w"]):
        same_hist = same.loc[same["week"] != last["week"]]

    oc_state = outcomes.loc[
        (outcomes["group_type"] == "market_state") & (outcomes["group_value"] == str(state))
    ]

    def oc_val(col):
        if oc_state.empty:
            return np.nan
        return oc_state.iloc[0][col]

    trans_cur = transitions.loc[
        (transitions["matrix"] == "combined") & (transitions["from_state"] == state)
    ].sort_values("probability", ascending=False)
    if trans_cur.empty:
        top_trans = "NA (no historical transitions from this state)"
    else:
        top = trans_cur.iloc[0]
        top_trans = (
            f"{top['to_state']} "
            f"(count={int(top['count'])}, historical frequency={fmt_pct(top['probability'])})"
        )

    # Objective proximity to frozen thresholds. Not a forecast.
    prox = []
    prox.append(
        f"MOM_4W is {fmt_pct(mom4)} vs the 0 sign threshold "
        f"(absolute distance {fmt_pct(abs(mom4) if np.isfinite(mom4) else np.nan)})."
    )
    prox.append(
        f"MOM_12W is {fmt_pct(mom12)} vs the 0 sign threshold "
        f"(absolute distance {fmt_pct(abs(mom12) if np.isfinite(mom12) else np.nan)})."
    )
    if np.isfinite(bb):
        prox.append(
            f"broad_breadth_4w is {fmt_num(bb, 3)} vs 0.50 "
            f"(absolute distance {fmt_num(abs(bb - 0.50), 3)})."
        )
    if np.isfinite(volp):
        prox.append(
            f"VOL_PERCENTILE is {fmt_num(volp, 3)} vs 0.70 "
            f"(absolute distance {fmt_num(abs(volp - 0.70), 3)})."
        )

    flip_notes = []
    if direction == "BULL" and np.isfinite(bb) and np.isfinite(mom4) and np.isfinite(mom12):
        if bb - 0.50 < 0.05:
            flip_notes.append(
                "broad_breadth_4w is close enough to 0.50 that a small drop would "
                "move direction from BULL to NEUTRAL under the frozen rule."
            )
        if mom4 > 0 and mom4 < 0.02:
            flip_notes.append(
                "MOM_4W is close to 0. A sign flip would move direction from BULL to NEUTRAL."
            )
        if mom12 > 0 and mom12 < 0.02:
            flip_notes.append(
                "MOM_12W is close to 0. A sign flip would move direction from BULL to NEUTRAL."
            )
    elif direction == "BEAR" and np.isfinite(bb) and np.isfinite(mom4) and np.isfinite(mom12):
        if 0.50 - bb < 0.05:
            flip_notes.append(
                "broad_breadth_4w is close enough to 0.50 that a small rise would "
                "move direction from BEAR to NEUTRAL under the frozen rule."
            )
        if mom4 < 0 and mom4 > -0.02:
            flip_notes.append(
                "MOM_4W is close to 0. A sign flip would move direction from BEAR to NEUTRAL."
            )
        if mom12 < 0 and mom12 > -0.02:
            flip_notes.append(
                "MOM_12W is close to 0. A sign flip would move direction from BEAR to NEUTRAL."
            )
    else:
        parts = []
        if np.isfinite(mom4):
            parts.append(f"MOM_4W {'>' if mom4 > 0 else '<' if mom4 < 0 else '='} 0")
        if np.isfinite(mom12):
            parts.append(f"MOM_12W {'>' if mom12 > 0 else '<' if mom12 < 0 else '='} 0")
        if np.isfinite(bb):
            parts.append(
                f"broad_breadth_4w {'>' if bb > 0.50 else '<' if bb < 0.50 else '='} 0.50"
            )
        flip_notes.append(
            "Current direction is NEUTRAL, so at least one BULL/BEAR condition fails: "
            + "; ".join(parts)
            + ". Reaching BULL or BEAR would require the missing condition(s) to flip."
        )
    if np.isfinite(volp) and abs(volp - HIGH_VOL_PERCENTILE) < 0.05:
        flip_notes.append(
            "VOL_PERCENTILE is close to 0.70, so the HIGH_VOL / NORMAL_VOL overlay "
            "could change without a direction change."
        )
    if not flip_notes:
        flip_notes.append(
            "No frozen threshold is unusually close; see the distances above. "
            "This is not a prediction that the state will persist or change."
        )

    rally_label = "MIXED"
    if np.isfinite(bb) and np.isfinite(lc):
        if bq == "BROAD":
            rally_label = "BROAD (both universes have breadth >= 0.60)"
        elif bq == "NARROW_LARGECAP":
            rally_label = "NARROW in the broad universe, stronger among large caps"
        elif bq == "WEAK":
            rally_label = "WEAK (both universes have breadth < 0.40)"
        else:
            rally_label = f"MIXED (breadth_quality={bq}, breadth_gap={fmt_num(gap, 3)})"

    analog_block = []
    if analogs.empty:
        analog_block.append("No historical analogs could be computed.")
    else:
        analog_block.append(
            "Standardization uses z-scores estimated on all finite weeks through "
            f"{week} (the last sample point). Distance is Euclidean in that z-space. "
            f"K=25 is frozen. Current week and the prior {ANALOG_EXCLUDE_RECENT} weeks "
            "are excluded. Weeks with any analog-vector NaN are excluded."
        )
        analog_block.append(
            "Stablecoin 4-week change "
            + (
                "IS in the analog vector."
                if analog_meta.get("stablecoin_in_vector")
                else "IS NOT in the analog vector: "
                + str(analog_meta.get("stablecoin_drop_reason", ""))
            )
        )
        top10 = analogs.head(10)
        analog_block.append("")
        analog_block.append(
            "| rank | week | state | breadth_quality | distance | "
            "future_1w | future_4w | future_12w | max_dd_12w | max_ru_12w |"
        )
        analog_block.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, a in top10.iterrows():
            analog_block.append(
                f"| {int(a['rank'])} | {a['week']} | {a['state']} | {a['breadth_quality']} | "
                f"{fmt_num(a['distance'], 3)} | {fmt_pct(a['future_return_1w'])} | "
                f"{fmt_pct(a['future_return_4w'])} | {fmt_pct(a['future_return_12w'])} | "
                f"{fmt_pct(a['max_drawdown_future_12w'])} | {fmt_pct(a['max_runup_future_12w'])} |"
            )
        t10 = top10.dropna(subset=["future_return_4w"])
        analog_block.append("")
        analog_block.append("Among the 10 nearest analogs with available forward paths:")
        if t10.empty:
            analog_block.append("- Forward outcomes are not available for these analog weeks.")
        else:
            analog_block.append(
                f"- 1w median future market return: {fmt_pct(t10['future_return_1w'].median())} "
                f"(historical frequency >0: {fmt_pct((t10['future_return_1w']>0).mean())}, n={len(t10)})"
            )
            analog_block.append(
                f"- 4w median future market return: {fmt_pct(t10['future_return_4w'].median())} "
                f"(historical frequency >0: {fmt_pct((t10['future_return_4w']>0).mean())})"
            )
            a12 = top10.dropna(subset=["future_return_12w"])
            if len(a12):
                analog_block.append(
                    f"- 12w median future market return: {fmt_pct(a12['future_return_12w'].median())} "
                    f"(historical frequency >0: {fmt_pct((a12['future_return_12w']>0).mean())}, n={len(a12)})"
                )
                analog_block.append(
                    f"- 12w median max drawdown: {fmt_pct(a12['max_drawdown_future_12w'].median())}"
                )
                analog_block.append(
                    f"- 12w median max runup: {fmt_pct(a12['max_runup_future_12w'].median())}"
                )
        analog_block.append(
            "These analog forward numbers are historical descriptions of similar weeks. "
            "They are not a forecast of the current week."
        )

    trans_lines = []
    if trans_cur.empty:
        trans_lines.append("No rows.")
    else:
        for _, trow in trans_cur.iterrows():
            trans_lines.append(
                f"- {state} → {trow['to_state']}: count={int(trow['count'])}, "
                f"historical frequency={fmt_pct(trow['probability'])}"
            )

    n_lt100 = len(largecap_lt_100)
    sample_start = weekly["week"].iloc[0]
    sample_end = weekly["week"].iloc[-1]

    rob_lines = []
    for _, rr in robustness.iterrows():
        rob_lines.append(
            f"- {rr['universe']}: state={rr['market_state']}, "
            f"MOM_4W={fmt_pct(rr['MOM_4W'])}, MOM_12W={fmt_pct(rr['MOM_12W'])}, "
            f"broad_breadth_4w={fmt_num(rr['broad_breadth_4w'], 3)}, "
            f"largecap_breadth_4w={fmt_num(rr['largecap_breadth_4w'], 3)}"
        )

    lines = f"""# Crypto Market State Observatory v1 — current market report

**As-of week (last Friday in the frozen panel): {week}**

This is **not** a live {pd.Timestamp.today().date()} snapshot. The input panel ends
{sample_end}. No new CoinMarketCap download was performed.

Sample in this file: {sample_start} → {sample_end} (Friday weeks).
Primary universe: observatory_eligible with market_cap >= $10,000,000.

Language note: frequencies below are **historical conditional frequencies**,
not “true probabilities” that the market will rise from the current week.

---

## 1. ¿Cuál es el estado actual?

**{state}**

- state_direction: **{direction}**
- volatility_state: **{vol_state}**
- breadth_quality (diagnostic only): **{bq}**
- n_eligible_coins: {int(last['n_eligible_coins'])}
- n_largecap_coins used: {int(last['n_largecap_coins'])}

## 2. ¿Por qué se clasifica así?

{why[0]}
{why[1]}
{why[2]}
{why[3]}

Thresholds are frozen and were not tuned on these results.

## 3. ¿Cuál es MOM_4W?

**{fmt_pct(mom4)}** (cumulative simple return of the value-weighted market index over the last 4 weeks through t).

## 4. ¿Cuál es MOM_12W?

**{fmt_pct(mom12)}** (cumulative simple return of the value-weighted market index over the last 12 weeks through t).

## 5. ¿Cuál es broad breadth?

**{fmt_num(bb, 4)}** = share of observatory_eligible coins with 4-week cumulative simple return > 0.
Equal-weight across coins. Coins without a complete 4-week calendar window are omitted from the denominator.

n coins in the breadth denominator this week: {int(last['n_breadth_coins'])}.

## 6. ¿Cuál es large-cap breadth?

**{fmt_num(lc, 4)}** = same 4-week up-share inside the current week’s top {LARGECAP_N} eligible coins by contemporaneous market cap.
If a week has fewer than {LARGECAP_N} eligible coins, all eligible coins are used.
Weeks with <100 eligible coins in this sample: {n_lt100}.

largecap_median_return_4w this week: {fmt_pct(last['largecap_median_return_4w'])}.

## 7. ¿El rally/caída es broad o narrow?

**{rally_label}**

- breadth_gap = largecap_breadth_4w − broad_breadth_4w = **{fmt_num(gap, 4)}**
- median_coin_return_4w (eligible, equal-weight) = {fmt_pct(last['median_coin_return_4w'])}
- Interpretation is descriptive: gap >> 0 means large caps had a higher up-share than the full eligible universe; gap << 0 means the opposite. No causal claim.

## 8. ¿Cuál es VOL_PERCENTILE?

**{fmt_num(volp, 4)}**

VOL_12W (sample std of last 12 weekly market simple returns, not annualized): {fmt_num(last['VOL_12W'], 4)}.
HIGH_VOL iff VOL_PERCENTILE >= 0.70. Expanding percentile uses VOL_12W history through t only.

## 9. ¿Cuál es TURNOVER_RELATIVE?

**{fmt_num(tover_rel, 4)}**

market_turnover (median volume/market_cap among eligible): {fmt_num(last['market_turnover'], 6)}.
TURNOVER_RELATIVE = market_turnover / trailing 12-week median of market_turnover (window includes t).
TURNOVER_PERCENTILE (expanding, on market_turnover): {fmt_num(last['TURNOVER_PERCENTILE'], 4)}.

## 10. ¿Cómo está cambiando stablecoin market cap?

STABLECOIN_MCAP (sum of observatory stablecoin market caps): **{fmt_num(scm / 1e9, 2) if np.isfinite(scm) else "NA"} billion USD** (raw {fmt_num(scm, 0)}).

- STABLECOIN_MCAP_4W_CHANGE = **{fmt_pct(sc4)}**
- STABLECOIN_MCAP_12W_CHANGE = **{fmt_pct(sc12)}**
- STABLECOIN_LIQ_PERCENTILE (expanding, on the level): {fmt_num(last['STABLECOIN_LIQ_PERCENTILE'], 4)}

Stablecoin growth is **measured**, not interpreted as bullish. The observatory uses a curated symbol list, not the Hsieh `is_stablecoin` flag. Wrapped listings can double-count some USD supply. See README limitations.

## 11. ¿Cuántas observaciones históricas existen en el mismo state?

**{n_same}** weeks have market_state = {state} in the sample (including the current week).
Forward-outcome statistics below use weeks in that state that still have a complete forward path, so N is smaller for 12-week outcomes.

## 12. ¿Qué retorno futuro tuvo históricamente ese state?

Historical conditional distribution of the **value-weighted market**, after weeks classified as **{state}**:

| horizon | N | mean | median |
|---|---|---|---|
| 1w | {int(oc_val('n_1w')) if np.isfinite(oc_val('n_1w')) else 'NA'} | {fmt_pct(oc_val('mean_future_return_1w'))} | {fmt_pct(oc_val('median_future_return_1w'))} |
| 4w | {int(oc_val('n_4w')) if np.isfinite(oc_val('n_4w')) else 'NA'} | {fmt_pct(oc_val('mean_future_return_4w'))} | {fmt_pct(oc_val('median_future_return_4w'))} |
| 12w | {int(oc_val('n_12w')) if np.isfinite(oc_val('n_12w')) else 'NA'} | {fmt_pct(oc_val('mean_future_return_12w'))} | {fmt_pct(oc_val('median_future_return_12w'))} |

These are in-sample historical frequencies. They are not a forecast.

## 13. ¿Cuál fue P(return > 0) históricamente?

Historical frequency of a **positive** subsequent market return after {state}:

- 1w: {fmt_pct(oc_val('hist_freq_return_gt_0_1w'))} (N={int(oc_val('n_1w')) if np.isfinite(oc_val('n_1w')) else 'NA'})
- 4w: {fmt_pct(oc_val('hist_freq_return_gt_0_4w'))} (N={int(oc_val('n_4w')) if np.isfinite(oc_val('n_4w')) else 'NA'})
- 12w: {fmt_pct(oc_val('hist_freq_return_gt_0_12w'))} (N={int(oc_val('n_12w')) if np.isfinite(oc_val('n_12w')) else 'NA'})

Also recorded (not a trading rule):

- 4w historical frequency of return > 10%: {fmt_pct(oc_val('hist_freq_return_gt_10pct_4w'))}
- 4w historical frequency of return < −10%: {fmt_pct(oc_val('hist_freq_return_lt_m10pct_4w'))}
- 12w historical frequency of return > 10%: {fmt_pct(oc_val('hist_freq_return_gt_10pct_12w'))}
- 12w historical frequency of return < −10%: {fmt_pct(oc_val('hist_freq_return_lt_m10pct_12w'))}

## 14. ¿Cuál fue el drawdown histórico típico después de ese state?

After weeks in {state}:

- 4w median max drawdown: {fmt_pct(oc_val('median_max_drawdown_4w'))}; historical frequency of max drawdown ≤ −10%: {fmt_pct(oc_val('hist_freq_drawdown_le_m10pct_4w'))}
- 12w median max drawdown: {fmt_pct(oc_val('median_max_drawdown_12w'))}; historical frequency of max drawdown ≤ −10%: {fmt_pct(oc_val('hist_freq_drawdown_le_m10pct_12w'))}
- 4w median max runup: {fmt_pct(oc_val('median_max_runup_4w'))}
- 12w median max runup: {fmt_pct(oc_val('median_max_runup_12w'))}

Max drawdown is peak-to-trough on the future wealth path starting at 1 at t. Max runup is the maximum of (wealth_k − 1) vs the level at t.

## 15. ¿Qué 10 semanas históricas son más similares a la actual?

{chr(10).join(analog_block)}

Full top 25: `results/current_historical_analogs.csv`.

## 16. ¿Qué ocurrió después de esos 10 episodios?

Covered in the analog table and summary bullets in section 15. Individual analog weeks can have missing 12-week outcomes near the sample end; those cells are NA.

## 17. ¿Cuál es la transición más frecuente desde el state actual?

Most frequent next combined state historically, given {state}: **{top_trans}**

Full empirical counts (no smoothing):

{chr(10).join(trans_lines)}

## 18. ¿Estamos cerca de algún threshold de cambio de estado?

No forecast. Objective distances to the **frozen** classification thresholds:

{chr(10).join('- ' + p for p in prox)}

{chr(10).join('- ' + p for p in flip_notes)}

---

## Universe robustness (current week only)

Primary diagnosis uses $10M. Same last week under $1M / $10M / $50M:

{chr(10).join(rob_lines)}

See `results/universe_robustness.csv`.

---

## Construction reminders (audit)

- Input weekly_return in the panel is a **log** return. Observatory converts to simple via exp(r)−1 before weighting, compounding, breadth, and volatility.
- market_return_t = sum(w_i,t−1 * simple_return_i,t) among observatory_eligible at t. Weights are lagged market cap, renormalized to 1.
- market_index starts at {INDEX_START:.0f} and compounds simple market_return.
- observatory_eligible is **not** Hsieh `eligible`. Rule is week-by-week, no future information, delisted coins kept while they appear.
- Forward-return columns are **not** inputs to state, breadth_quality, analogs’ feature vector construction, or volatility labels.
"""
    return lines


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading panel: {PANEL_PATH}")
    panel = load_panel()
    weeks = sorted(panel["week"].unique())
    print(
        f"Panel rows={len(panel):,} assets={panel['asset_id'].nunique():,} "
        f"weeks={len(weeks)} {weeks[0]} → {weeks[-1]}"
    )

    stable_ids = set(
        panel.loc[panel["obs_stablecoin"], "asset_id"].unique().tolist()
    )
    print(f"Observatory stablecoin asset_ids: {len(stable_ids)}")

    print("Pivoting calendar matrices...")
    simple_wide = calendar_wide(panel, "simple_return")
    mcap_wide = calendar_wide(panel, "market_cap").reindex_like(simple_wide)
    volume_wide = calendar_wide(panel, "volume").reindex_like(simple_wide)
    price_wide = calendar_wide(panel, "weekly_price").reindex_like(simple_wide)
    hist_wide = history_count_wide(price_wide)
    ret4_wide = coin_cumret_wide(simple_wide, MOM_SHORT)
    print(f"Wide shape weeks x assets: {simple_wide.shape}")

    print("Building PRIMARY universe (>= $10M)...")
    weekly = compute_weekly_core(
        panel,
        PRIMARY_MIN_MCAP,
        simple_wide,
        mcap_wide,
        volume_wide,
        price_wide,
        hist_wide,
        ret4_wide,
        stable_ids,
    )
    largecap_lt_100 = list(weekly.attrs.get("largecap_lt_100_weeks", []))
    weekly = add_stablecoin_liquidity(weekly, panel)
    weekly = add_forward_outcomes(weekly)

    out_cols = [
        "week",
        "market_return",
        "market_index",
        "MOM_4W",
        "MOM_12W",
        "broad_breadth_4w",
        "largecap_breadth_4w",
        "breadth_gap",
        "breadth_quality",
        "median_coin_return_4w",
        "largecap_median_return_4w",
        "VOL_12W",
        "VOL_PERCENTILE",
        "market_turnover",
        "TURNOVER_RELATIVE",
        "TURNOVER_PERCENTILE",
        "STABLECOIN_MCAP",
        "STABLECOIN_MCAP_4W_CHANGE",
        "STABLECOIN_MCAP_12W_CHANGE",
        "state_direction",
        "volatility_state",
        "market_state",
        "n_eligible_coins",
    ]
    extra = [
        "p25_coin_return_4w",
        "p75_coin_return_4w",
        "market_turnover_p75",
        "STABLECOIN_LIQ_PERCENTILE",
        "n_largecap_coins",
        "n_breadth_coins",
        "market_return_future_1w",
        "market_return_future_4w",
        "market_return_future_12w",
        "max_drawdown_future_4w",
        "max_drawdown_future_12w",
        "max_runup_future_4w",
        "max_runup_future_12w",
    ]
    weekly_out = weekly[out_cols + extra]
    weekly_path = RESULTS_DIR / "weekly_market_state.csv"
    weekly_out.to_csv(weekly_path, index=False)
    print(f"Wrote {weekly_path}")

    transitions = transition_long(weekly)
    trans_path = RESULTS_DIR / "state_transition_matrix.csv"
    transitions.to_csv(trans_path, index=False)
    print(f"Wrote {trans_path}")

    outcomes = forward_outcomes_table(weekly)
    oc_path = RESULTS_DIR / "state_forward_outcomes.csv"
    outcomes.to_csv(oc_path, index=False)
    print(f"Wrote {oc_path}")

    analogs, analog_meta = historical_analogs(weekly)
    an_path = RESULTS_DIR / "current_historical_analogs.csv"
    analogs.to_csv(an_path, index=False)
    print(f"Wrote {an_path} rows={len(analogs)} meta={analog_meta.get('stablecoin_in_vector')}")

    print("Universe robustness (full weekly series per threshold, last-week compare)...")
    rob_rows = []
    last_week = weekly["week"].iloc[-1]
    for uname, thresh in ROBUSTNESS_MIN_MCAP.items():
        if thresh == PRIMARY_MIN_MCAP:
            w = weekly
        else:
            w = compute_weekly_core(
                panel,
                thresh,
                simple_wide,
                mcap_wide,
                volume_wide,
                price_wide,
                hist_wide,
                ret4_wide,
                stable_ids,
            )
        last = w.loc[w["week"] == last_week].iloc[0]
        rob_rows.append(
            {
                "universe": uname,
                "min_market_cap": thresh,
                "week": last_week,
                "MOM_4W": last["MOM_4W"],
                "MOM_12W": last["MOM_12W"],
                "broad_breadth_4w": last["broad_breadth_4w"],
                "largecap_breadth_4w": last["largecap_breadth_4w"],
                "state_direction": last["state_direction"],
                "volatility_state": last["volatility_state"],
                "market_state": last["market_state"],
                "n_eligible_coins": last["n_eligible_coins"],
            }
        )
    robustness = pd.DataFrame(rob_rows)
    rob_path = RESULTS_DIR / "universe_robustness.csv"
    robustness.to_csv(rob_path, index=False)
    print(f"Wrote {rob_path}")

    report = write_current_report(
        weekly,
        transitions,
        outcomes,
        analogs,
        analog_meta,
        panel,
        robustness,
        largecap_lt_100,
    )
    report_path = RESULTS_DIR / "current_market_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {report_path}")

    last = weekly.iloc[-1]
    print(
        f"CURRENT {last['week']} state={last['market_state']} "
        f"MOM4={last['MOM_4W']:.4f} MOM12={last['MOM_12W']:.4f} "
        f"broad={last['broad_breadth_4w']:.3f} large={last['largecap_breadth_4w']:.3f} "
        f"n_elig={int(last['n_eligible_coins'])}"
    )
    print(f"Weeks with <100 eligible (primary): {len(largecap_lt_100)}")


if __name__ == "__main__":
    main()
