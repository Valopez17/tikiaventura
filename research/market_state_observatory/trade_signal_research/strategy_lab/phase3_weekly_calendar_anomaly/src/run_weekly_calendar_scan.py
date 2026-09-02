#!/usr/bin/env python3
"""Phase 3 — exhaustive weekly BTC calendar-window scan.

Price + time only. No indicators, macro, derivatives, or ML.
Not a live system. Not clean OOS.

Discovery ranking uses 2017 start → 2021-12-31 only.
Validation (2022–2024) and recent (2025→latest) never reselect.
"""

from __future__ import annotations

import time
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
H1_PATH = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"

TZ = "America/New_York"
START_CAP = 10_000.0
FEE_PRIMARY = 0.0010
FEE_SET = (0.0, 0.0010, 0.0020, 0.0050)
N_SLOTS = 168
MIN_HOLD = 1
MAX_HOLD = 167
MIN_DISC_TRADES = 150
MIN_SLOTS_FOR_MEDIAN = 24
TOP_N = 20
TOP_NEIGHBOR = 5
N_BOOT = 2000
BOOT_BLOCK = 4
BOOT_SEED = 42
CRYPTO_DAYS = 365.0
CATASTROPHIC_END = 5_000.0
CATASTROPHIC_DD = -0.80

DISC_END = pd.Timestamp("2022-01-01", tz=TZ)
VAL_END = pd.Timestamp("2025-01-01", tz=TZ)

WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_num(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{x:.{nd}f}"


def fmt_pct(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{100.0 * x:.{nd}f}%"


def fmt_usd(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"${x:,.0f}"


def weekday_name(slot: int) -> str:
    return WEEKDAYS[int(slot) // 24]


def hour_ny(slot: int) -> int:
    return int(slot) % 24


def slot_label(slot: int) -> str:
    return f"{weekday_name(slot)} {hour_ny(slot):02d}:00"


def net_from_gross(gross: np.ndarray, fee: float) -> np.ndarray:
    g = np.asarray(gross, dtype=float)
    return (1.0 + g) * (1.0 - fee) - 1.0


def profit_factor(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.nan
    gp = float(np.sum(x[x > 0]))
    gl = float(np.sum(np.abs(x[x < 0])))
    if gl > 0:
        return gp / gl
    if gp > 0:
        return np.inf
    return np.nan


def max_drawdown_from_nets(nets: np.ndarray, start_cap: float = START_CAP) -> float:
    nets = np.asarray(nets, dtype=float)
    nets = nets[np.isfinite(nets)]
    if nets.size == 0:
        return np.nan
    eq = start_cap * np.cumprod(1.0 + nets)
    eq = np.concatenate([[start_cap], eq])
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(np.min(dd))


def ending_capital(nets: np.ndarray, start_cap: float = START_CAP) -> float:
    nets = np.asarray(nets, dtype=float)
    nets = nets[np.isfinite(nets)]
    if nets.size == 0:
        return float(start_cap)
    return float(start_cap * np.prod(1.0 + nets))


def cagr_from(start_cap: float, end_cap: float, days: float) -> float:
    if not np.isfinite(start_cap) or not np.isfinite(end_cap) or start_cap <= 0 or days <= 0:
        return np.nan
    if end_cap <= 0:
        return -1.0
    return float((end_cap / start_cap) ** (CRYPTO_DAYS / days) - 1.0)


def weekly_sharpe_vol(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return np.nan, np.nan
    sd = float(x.std(ddof=1))
    if sd <= 0:
        return np.nan, 0.0
    vol = sd * np.sqrt(52.0)
    sharpe = float(x.mean() / sd * np.sqrt(52.0))
    return sharpe, vol


def period_days(start: pd.Timestamp, end: pd.Timestamp) -> float:
    return max(float((end - start).total_seconds() / 86400.0), 1.0)


def load_hourly() -> pd.DataFrame:
    if not H1_PATH.exists():
        raise RuntimeError(
            f"No local 1h BTCUSDT file at {H1_PATH}. "
            "This phase will not download a substitute."
        )
    df = pd.read_csv(H1_PATH)
    if "timestamp_utc" not in df.columns:
        raise RuntimeError("1h file missing timestamp_utc")
    df["ts_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    for c in ("open", "high", "low", "close"):
        if c not in df.columns:
            raise RuntimeError(f"1h file missing {c}")
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n_raw = len(df)
    df = df.dropna(subset=["ts_utc", "open", "high", "low", "close"]).copy()
    n_ohlc_drop = n_raw - len(df)
    dup = int(df["ts_utc"].duplicated().sum())
    df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="first")
    chrono = bool(df["ts_utc"].is_monotonic_increasing)
    unique = bool(df["ts_utc"].is_unique)
    ohlc_ok = bool(
        (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-12).all()
        and (df["low"] <= df[["open", "close"]].min(axis=1) + 1e-12).all()
        and (df["high"] >= df["low"]).all()
        and (df["open"] > 0).all()
        and (df["close"] > 0).all()
    )
    if not chrono or not unique:
        raise RuntimeError("UTC timestamps are not unique/chronological after clean.")
    if not ohlc_ok:
        raise RuntimeError("OHLC validity check failed.")
    full = pd.date_range(df["ts_utc"].min(), df["ts_utc"].max(), freq="h", tz="UTC")
    missing = full.difference(pd.DatetimeIndex(df["ts_utc"]))
    meta = {
        "n_raw": n_raw,
        "n_bars": int(len(df)),
        "n_ohlc_drop": int(n_ohlc_drop),
        "n_dup_dropped": dup,
        "unique": unique,
        "chronological": chrono,
        "ohlc_valid": ohlc_ok,
        "n_missing_hours": int(len(missing)),
        "missing_hours": missing,
        "start_utc": df["ts_utc"].min(),
        "end_utc": df["ts_utc"].max(),
        "start_ny": df["ts_utc"].min().tz_convert(TZ),
        "end_ny": df["ts_utc"].max().tz_convert(TZ),
    }
    log(
        f"1h BTCUSDT {meta['start_utc']} → {meta['end_utc']} "
        f"bars={meta['n_bars']} missing_hours={meta['n_missing_hours']} "
        f"dups_dropped={dup} ohlc_drop={n_ohlc_drop}"
    )
    df.attrs["meta"] = meta
    return df.reset_index(drop=True)


def build_slot_grid(meta: dict) -> dict:
    """Monday-start NY weeks × 168 labeled slots.

    DST rule: nonexistent (spring-forward) or ambiguous (fall-back) local
    hours are NaT and that (week, slot) is skipped. No silent guess.
    """
    first_ny = meta["start_ny"].tz_convert(TZ).normalize()
    last_ny = meta["end_ny"].tz_convert(TZ).normalize()
    first_monday = first_ny - pd.Timedelta(days=int(first_ny.weekday()))
    last_monday = last_ny - pd.Timedelta(days=int(last_ny.weekday()))
    mondays = pd.date_range(
        first_monday.tz_localize(None),
        last_monday.tz_localize(None),
        freq="W-MON",
    )
    n_w = int(len(mondays))
    slot = np.arange(N_SLOTS, dtype=np.int64)
    day_off = slot // 24
    hour = slot % 24
    offsets = (day_off * 24 + hour).astype("timedelta64[h]")
    naive = mondays.values[:, None] + offsets[None, :]
    naive_flat = pd.DatetimeIndex(naive.ravel())
    ny_flat = naive_flat.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT")
    dst_skip = ny_flat.isna()
    n_dst = int(dst_skip.sum())
    utc_flat = ny_flat.tz_convert("UTC")
    log(f"week grid weeks={n_w} slots={n_w * N_SLOTS} DST_skip={n_dst}")
    return {
        "n_weeks": n_w,
        "mondays": mondays,
        "naive_flat": naive_flat,
        "ny_flat": ny_flat,
        "utc_flat": utc_flat,
        "dst_skip": np.asarray(dst_skip, dtype=bool),
        "n_dst_skip": n_dst,
        "first_monday": mondays[0],
        "last_monday": mondays[-1],
    }


def fill_price_matrix(df: pd.DataFrame, grid: dict) -> dict:
    opens = pd.Series(
        df["open"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(df["ts_utc"]),
    )
    utc_idx = pd.DatetimeIndex(grid["utc_flat"])
    n_flat = len(utc_idx)
    px_flat = np.full(n_flat, np.nan, dtype=float)
    ok = np.asarray(utc_idx.notna(), dtype=bool)
    px_flat[ok] = opens.reindex(utc_idx[ok]).to_numpy(dtype=float)
    n_w = grid["n_weeks"]
    prices = px_flat.reshape(n_w, N_SLOTS)
    dst = grid["dst_skip"].reshape(n_w, N_SLOTS)
    missing_bar = (~dst) & ~np.isfinite(prices)
    n_missing_bar = int(missing_bar.sum())
    disc_end_utc = DISC_END.tz_convert("UTC")
    val_end_utc = VAL_END.tz_convert("UTC")
    start_utc = df["ts_utc"].min()
    end_utc = df["ts_utc"].max()
    ts_ns = utc_idx.asi8
    valid_ts = ok
    in_disc = valid_ts & (ts_ns >= start_utc.value) & (ts_ns < disc_end_utc.value)
    in_val = valid_ts & (ts_ns >= disc_end_utc.value) & (ts_ns < val_end_utc.value)
    in_rec = valid_ts & (ts_ns >= val_end_utc.value) & (ts_ns <= end_utc.value)
    in_full = valid_ts & (ts_ns >= start_utc.value) & (ts_ns <= end_utc.value)
    naive = pd.DatetimeIndex(grid["naive_flat"])
    start_ny_naive = pd.Timestamp(start_utc.tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S"))
    end_ny_naive = pd.Timestamp(end_utc.tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S"))
    in_disc_naive = np.asarray((naive >= start_ny_naive) & (naive < pd.Timestamp("2022-01-01")), dtype=bool)
    in_val_naive = np.asarray((naive >= pd.Timestamp("2022-01-01")) & (naive < pd.Timestamp("2025-01-01")), dtype=bool)
    in_rec_naive = np.asarray((naive >= pd.Timestamp("2025-01-01")) & (naive <= end_ny_naive), dtype=bool)
    log(
        f"price matrix missing_bar_slots={n_missing_bar} "
        f"(DST already skipped={grid['n_dst_skip']})"
    )
    return {
        "prices": prices,
        "dst": dst,
        "missing_bar": missing_bar.reshape(n_w, N_SLOTS),
        "in_disc": in_disc.reshape(n_w, N_SLOTS),
        "in_val": in_val.reshape(n_w, N_SLOTS),
        "in_rec": in_rec.reshape(n_w, N_SLOTS),
        "in_full": in_full.reshape(n_w, N_SLOTS),
        "in_disc_naive": in_disc_naive.reshape(n_w, N_SLOTS),
        "in_val_naive": in_val_naive.reshape(n_w, N_SLOTS),
        "in_rec_naive": in_rec_naive.reshape(n_w, N_SLOTS),
        "n_missing_bar": n_missing_bar,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "ny_flat": grid["ny_flat"],
        "utc_flat": grid["utc_flat"],
        "n_weeks": n_w,
        "mondays": grid["mondays"],
    }


def shift_exit(arr: np.ndarray, h: int) -> np.ndarray:
    """Map (week, entry_slot) → value at the next slot h hours later."""
    n_w, n_s = arr.shape
    out = np.full((n_w, n_s), np.nan, dtype=arr.dtype if arr.dtype != bool else float)
    slots = np.arange(n_s)
    wrap = (slots + h) >= n_s
    same = ~wrap
    if arr.dtype == bool:
        out = np.zeros((n_w, n_s), dtype=bool)
        out[:, same] = arr[:, slots[same] + h]
        out[:-1, wrap] = arr[1:, slots[wrap] + h - n_s]
        return out
    out[:, same] = arr[:, slots[same] + h]
    out[:-1, wrap] = arr[1:, slots[wrap] + h - n_s]
    return out


def returns_for_h(prices: np.ndarray, h: int) -> np.ndarray:
    entry = prices
    exit_px = shift_exit(prices, h)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = exit_px / entry - 1.0
    ret[~np.isfinite(ret)] = np.nan
    return ret


def period_valid(in_period: np.ndarray, h: int, ret: np.ndarray) -> np.ndarray:
    entry_ok = in_period & np.isfinite(ret)
    exit_ok = shift_exit(in_period, h)
    return entry_ok & exit_ok


def edge_from_ret(ret: np.ndarray, valid: np.ndarray) -> np.ndarray:
    masked = np.where(valid, ret, np.nan)
    n_valid = np.isfinite(masked).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = np.nanmedian(masked, axis=1)
    med = np.where(n_valid >= MIN_SLOTS_FOR_MEDIAN, med, np.nan)
    return masked - med[:, None]


def summarize_series(
    gross: np.ndarray,
    edge: np.ndarray,
    fee: float,
    span_days: float,
) -> dict:
    g = np.asarray(gross, dtype=float)
    e = np.asarray(edge, dtype=float)
    finite_g = np.isfinite(g)
    g = g[finite_g]
    e_use = e[np.isfinite(e)]
    n = int(g.size)
    out = {
        "n_trades": n,
        "mean_trade_return": float(g.mean()) if n else np.nan,
        "median_trade_return": float(np.median(g)) if n else np.nan,
        "win_rate": float(np.mean(g > 0)) if n else np.nan,
        "trade_std": float(g.std(ddof=1)) if n >= 2 else np.nan,
        "profit_factor": profit_factor(g) if n else np.nan,
        "mean_calendar_edge": float(e_use.mean()) if e_use.size else np.nan,
        "median_calendar_edge": float(np.median(e_use)) if e_use.size else np.nan,
        "calendar_edge_std": float(e_use.std(ddof=1)) if e_use.size >= 2 else np.nan,
        "fraction_weeks_edge_positive": float(np.mean(e_use > 0)) if e_use.size else np.nan,
        "n_edge_weeks": int(e_use.size),
    }
    ce_sh, _ = weekly_sharpe_vol(e_use)
    out["calendar_edge_sharpe"] = ce_sh
    nets = {bps: net_from_gross(g, fee_v) for bps, fee_v in zip((0, 10, 20, 50), FEE_SET)}
    primary = nets[10] if abs(fee - FEE_PRIMARY) < 1e-12 else net_from_gross(g, fee)
    out["mean_net_trade"] = float(primary.mean()) if n else np.nan
    out["median_net_trade"] = float(np.median(primary)) if n else np.nan
    out["ending_capital_from_10000"] = ending_capital(primary)
    out["cagr"] = cagr_from(START_CAP, out["ending_capital_from_10000"], span_days)
    sh, vol = weekly_sharpe_vol(primary)
    out["sharpe"] = sh
    out["annualized_volatility"] = vol
    out["max_drawdown"] = max_drawdown_from_nets(primary)
    if (
        np.isfinite(out["cagr"])
        and np.isfinite(out["max_drawdown"])
        and out["max_drawdown"] < 0
    ):
        out["calmar"] = float(out["cagr"] / abs(out["max_drawdown"]))
    else:
        out["calmar"] = np.nan
    out["win_rate_net"] = float(np.mean(primary > 0)) if n else np.nan
    for bps, arr in nets.items():
        out[f"ending_capital_{bps}bps"] = ending_capital(arr)
        out[f"mean_net_{bps}bps"] = float(arr.mean()) if n else np.nan
        sh_b, _ = weekly_sharpe_vol(arr)
        out[f"sharpe_{bps}bps"] = sh_b
    return out


def scan_period(mat: dict, in_period: np.ndarray, span_days: float, period: str) -> pd.DataFrame:
    prices = mat["prices"]
    rows = []
    n_skip_dst_obs = 0
    n_skip_missing_obs = 0
    for h in range(MIN_HOLD, MAX_HOLD + 1):
        ret = returns_for_h(prices, h)
        valid = period_valid(in_period, h, ret)
        dst_entry = mat["dst"]
        dst_exit = shift_exit(mat["dst"], h)
        miss_entry = mat["missing_bar"]
        miss_exit = shift_exit(mat["missing_bar"], h)
        scheduled = mat.get("in_disc_naive", in_period)
        n_skip_dst_obs += int((scheduled & (dst_entry | dst_exit)).sum())
        n_skip_missing_obs += int(
            (scheduled & ~(dst_entry | dst_exit) & (miss_entry | miss_exit)).sum()
        )
        edge = edge_from_ret(ret, valid)
        for s in range(N_SLOTS):
            exit_s = (s + h) % N_SLOTS
            rec = {
                "period": period,
                "entry_slot": s,
                "exit_slot": int(exit_s),
                "entry_weekday": weekday_name(s),
                "entry_hour_NY": hour_ny(s),
                "exit_weekday": weekday_name(exit_s),
                "exit_hour_NY": hour_ny(exit_s),
                "holding_hours": int(h),
                "exposure_pct": float(h / N_SLOTS),
            }
            rec.update(summarize_series(ret[:, s][valid[:, s]], edge[:, s][valid[:, s]], FEE_PRIMARY, span_days))
            rows.append(rec)
        if h % 40 == 0 or h == MAX_HOLD:
            log(f"  {period} holding_hours={h}/{MAX_HOLD}")
    out = pd.DataFrame(rows)
    out.attrs["n_skip_dst_obs"] = n_skip_dst_obs
    out.attrs["n_skip_missing_obs"] = n_skip_missing_obs
    return out


def score_subset(
    mat: dict,
    in_period: np.ndarray,
    span_days: float,
    period: str,
    pairs: list[tuple[int, int]],
) -> pd.DataFrame:
    """Score frozen (entry_slot, holding_hours) pairs only. No reselection."""
    prices = mat["prices"]
    by_h: dict[int, list[int]] = {}
    for entry_slot, h in pairs:
        by_h.setdefault(int(h), []).append(int(entry_slot))
    rows = []
    for h, slots in by_h.items():
        ret = returns_for_h(prices, h)
        valid = period_valid(in_period, h, ret)
        edge = edge_from_ret(ret, valid)
        for s in slots:
            exit_s = (s + h) % N_SLOTS
            rec = {
                "period": period,
                "entry_slot": s,
                "exit_slot": int(exit_s),
                "entry_weekday": weekday_name(s),
                "entry_hour_NY": hour_ny(s),
                "exit_weekday": weekday_name(exit_s),
                "exit_hour_NY": hour_ny(exit_s),
                "holding_hours": int(h),
                "exposure_pct": float(h / N_SLOTS),
            }
            rec.update(
                summarize_series(ret[:, s][valid[:, s]], edge[:, s][valid[:, s]], FEE_PRIMARY, span_days)
            )
            rows.append(rec)
    return pd.DataFrame(rows)


def rank_discovery(disc: pd.DataFrame) -> pd.DataFrame:
    d = disc.copy()
    d["pass_n"] = d["n_trades"] >= MIN_DISC_TRADES
    d["pass_net"] = d["mean_net_trade"] > 0
    eligible = d.loc[d["pass_n"] & d["pass_net"]].copy()
    if eligible.empty:
        log("WARNING: no discovery candidates passed N>=150 and mean_net_trade>0")
        eligible = d.loc[d["pass_n"]].copy()
    eligible = eligible.sort_values(
        by=["calendar_edge_sharpe", "mean_calendar_edge", "sharpe", "ending_capital_from_10000"],
        ascending=[False, False, False, False],
        na_position="last",
    )
    eligible["discovery_rank"] = np.arange(1, len(eligible) + 1)
    return eligible


def block_bootstrap_ci(x: np.ndarray, block: int = BOOT_BLOCK, n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = int(x.size)
    if n < block * 2:
        return np.nan, np.nan, n
    max_start = n - block + 1
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, max_start, size=(n_boot, n_blocks))
    offsets = np.arange(block)
    samples = x[starts[..., None] + offsets]
    samples = samples.reshape(n_boot, n_blocks * block)[:, :n]
    means = samples.mean(axis=1)
    lo = float(np.quantile(means, 0.025))
    hi = float(np.quantile(means, 0.975))
    return lo, hi, n


def buy_hold_period(df: pd.DataFrame, start_utc: pd.Timestamp, end_utc: pd.Timestamp, fee: float) -> dict:
    sl = df.loc[(df["ts_utc"] >= start_utc) & (df["ts_utc"] < end_utc)]
    if sl.empty:
        sl = df.loc[(df["ts_utc"] >= start_utc) & (df["ts_utc"] <= end_utc)]
    if sl.empty:
        return {"gross": np.nan, "net": np.nan, "end_cap": np.nan, "start": None, "end": None}
    px0 = float(sl["open"].iloc[0])
    px1 = float(sl["open"].iloc[-1])
    gross = px1 / px0 - 1.0
    net = (1.0 + gross) * (1.0 - fee) - 1.0
    return {
        "gross": gross,
        "net": net,
        "end_cap": START_CAP * (1.0 + net),
        "start": sl["ts_utc"].iloc[0],
        "end": sl["ts_utc"].iloc[-1],
        "px0": px0,
        "px1": px1,
    }


def neighbor_keys(entry_slot: int, exit_slot: int) -> list[tuple[int, int, str]]:
    out = []
    for ds, which in ((-1, "entry-1h"), (1, "entry+1h")):
        es = (entry_slot + ds) % N_SLOTS
        if es != exit_slot:
            out.append((es, exit_slot, which))
    for ds, which in ((-1, "exit-1h"), (1, "exit+1h")):
        xs = (exit_slot + ds) % N_SLOTS
        if xs != entry_slot:
            out.append((entry_slot, xs, which))
    return out


def lookup_row(df: pd.DataFrame, entry_slot: int, exit_slot: int) -> pd.Series | None:
    hit = df.loc[(df["entry_slot"] == entry_slot) & (df["exit_slot"] == exit_slot)]
    if hit.empty:
        return None
    return hit.iloc[0]


def neighborhood_flag(disc: pd.DataFrame, entry_slot: int, exit_slot: int) -> tuple[str, list[dict]]:
    winner = lookup_row(disc, entry_slot, exit_slot)
    details = []
    similar = 0
    for es, xs, which in neighbor_keys(entry_slot, exit_slot):
        row = lookup_row(disc, es, xs)
        rec = {"neighbor": which, "entry_slot": es, "exit_slot": xs}
        if row is None:
            rec.update({"mean_calendar_edge": np.nan, "calendar_edge_sharpe": np.nan, "mean_net_trade": np.nan})
            details.append(rec)
            continue
        rec["label"] = f"{slot_label(es)} → {slot_label(xs)}"
        rec["mean_calendar_edge"] = float(row["mean_calendar_edge"])
        rec["calendar_edge_sharpe"] = float(row["calendar_edge_sharpe"])
        rec["mean_net_trade"] = float(row["mean_net_trade"])
        rec["n_trades"] = int(row["n_trades"])
        w_sh = float(winner["calendar_edge_sharpe"]) if winner is not None else np.nan
        edge_pos = np.isfinite(rec["mean_calendar_edge"]) and rec["mean_calendar_edge"] > 0
        sh_ok = (
            np.isfinite(rec["calendar_edge_sharpe"])
            and rec["calendar_edge_sharpe"] > 0
            and (not np.isfinite(w_sh) or rec["calendar_edge_sharpe"] >= 0.5 * w_sh)
        )
        rec["similar"] = bool(edge_pos and sh_ok)
        if rec["similar"]:
            similar += 1
        details.append(rec)
    if similar == 0:
        flag = "FRAGILE / POSSIBLE DATA MINING"
    elif similar <= 1:
        flag = "WEAK NEIGHBORHOOD"
    else:
        flag = "NEIGHBORHOOD STABLE"
    return flag, details


def year_table(mat: dict, entry_slot: int, h: int, fee: float = FEE_PRIMARY) -> list[dict]:
    ret = returns_for_h(mat["prices"], h)
    valid = period_valid(mat["in_full"], h, ret)
    edge = edge_from_ret(ret, valid)
    ny = mat["ny_flat"]
    n_w = mat["n_weeks"]
    years = pd.DatetimeIndex(ny).tz_convert(TZ).year.to_numpy().reshape(n_w, N_SLOTS)
    g = ret[:, entry_slot]
    e = edge[:, entry_slot]
    ok = valid[:, entry_slot]
    ycol = years[:, entry_slot]
    rows = []
    for year in sorted(set(int(y) for y in ycol[ok] if np.isfinite(y))):
        m = ok & (ycol == year)
        gg = g[m]
        ee = e[m]
        nets = net_from_gross(gg, fee)
        sh, _ = weekly_sharpe_vol(nets)
        rows.append(
            {
                "year": int(year),
                "n_trades": int(gg.size),
                "year_return": float(np.prod(1.0 + nets) - 1.0) if gg.size else np.nan,
                "mean_trade": float(gg.mean()) if gg.size else np.nan,
                "mean_net_trade": float(nets.mean()) if gg.size else np.nan,
                "win_rate": float(np.mean(gg > 0)) if gg.size else np.nan,
                "sharpe": sh,
                "mean_calendar_edge": float(ee[np.isfinite(ee)].mean()) if np.isfinite(ee).any() else np.nan,
            }
        )
    return rows


def extract_trade_log(mat: dict, top: pd.DataFrame) -> pd.DataFrame:
    n_w = mat["n_weeks"]
    ny = pd.DatetimeIndex(mat["ny_flat"]).tz_convert(TZ)
    utc = pd.DatetimeIndex(mat["utc_flat"]).tz_convert("UTC")
    ny2 = ny.to_numpy().reshape(n_w, N_SLOTS)
    utc2 = utc.to_numpy().reshape(n_w, N_SLOTS)
    prices = mat["prices"]
    rows = []
    for _, cand in top.iterrows():
        s = int(cand["entry_slot"])
        h = int(cand["holding_hours"])
        xs = int(cand["exit_slot"])
        ret = returns_for_h(prices, h)
        v_disc = period_valid(mat["in_disc"], h, ret)
        v_val = period_valid(mat["in_val"], h, ret)
        v_rec = period_valid(mat["in_rec"], h, ret)
        v_full = period_valid(mat["in_full"], h, ret)
        edge = edge_from_ret(ret, v_full)
        exit_px = shift_exit(prices, h)
        for w in range(n_w):
            if not v_full[w, s]:
                continue
            if v_disc[w, s]:
                period = "discovery"
            elif v_val[w, s]:
                period = "validation"
            elif v_rec[w, s]:
                period = "recent"
            else:
                period = "boundary"
            ew = w
            es = s
            xw = w if (s + h) < N_SLOTS else w + 1
            xss = (s + h) % N_SLOTS
            if xw >= n_w:
                continue
            g = float(ret[w, s])
            net = float(net_from_gross(np.array([g]), FEE_PRIMARY)[0])
            rows.append(
                {
                    "discovery_rank": int(cand["discovery_rank"]),
                    "entry_weekday": cand["entry_weekday"],
                    "entry_hour_NY": int(cand["entry_hour_NY"]),
                    "exit_weekday": cand["exit_weekday"],
                    "exit_hour_NY": int(cand["exit_hour_NY"]),
                    "holding_hours": h,
                    "week_monday": str(pd.Timestamp(mat["mondays"][w]).date()),
                    "period": period,
                    "entry_time_ny": str(pd.Timestamp(ny2[ew, es])),
                    "exit_time_ny": str(pd.Timestamp(ny2[xw, xss])),
                    "entry_time_utc": str(pd.Timestamp(utc2[ew, es])),
                    "exit_time_utc": str(pd.Timestamp(utc2[xw, xss])),
                    "entry_open": float(prices[ew, es]),
                    "exit_open": float(exit_px[w, s]),
                    "gross_return": g,
                    "net_return_10bps": net,
                    "calendar_edge": float(edge[w, s]) if np.isfinite(edge[w, s]) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def year_concentration(years: list[dict]) -> tuple[bool, str]:
    if not years:
        return False, "no yearly rows"
    pos_edge = [y for y in years if np.isfinite(y["mean_calendar_edge"]) and y["mean_calendar_edge"] > 0]
    rets = np.array([y["year_return"] for y in years if np.isfinite(y["year_return"])], dtype=float)
    if rets.size == 0:
        return False, "no yearly returns"
    pos = np.clip(rets, 0, None)
    share = float(pos.max() / pos.sum()) if pos.sum() > 0 else 1.0
    n_pos_edge = len(pos_edge)
    concentrated = n_pos_edge <= 1 or share >= 0.70
    msg = (
        f"years_with_positive_edge={n_pos_edge}/{len(years)}; "
        f"max_positive_year_share={share:.2f}"
    )
    return (not concentrated) and n_pos_edge >= 2, msg


def classify(disc_row: pd.Series, val_row: pd.Series, rec_row: pd.Series, neigh_flag: str, year_ok: bool) -> str:
    disc_net = float(disc_row["mean_net_trade"])
    disc_edge = float(disc_row["mean_calendar_edge"])
    val_net = float(val_row["mean_net_trade"]) if val_row is not None else np.nan
    val_edge = float(val_row["mean_calendar_edge"]) if val_row is not None else np.nan
    val_sh = float(val_row["sharpe"]) if val_row is not None else np.nan
    val_end = float(val_row["ending_capital_from_10000"]) if val_row is not None else np.nan
    val_dd = float(val_row["max_drawdown"]) if val_row is not None else np.nan
    rec_net = float(rec_row["mean_net_trade"]) if rec_row is not None else np.nan
    rec_edge = float(rec_row["mean_calendar_edge"]) if rec_row is not None else np.nan

    collapse = (np.isfinite(val_end) and val_end < CATASTROPHIC_END) or (
        np.isfinite(val_dd) and val_dd <= CATASTROPHIC_DD
    )
    edge_gone = (not np.isfinite(val_edge)) or val_edge <= 0
    val_net_nonpos = (not np.isfinite(val_net)) or val_net <= 0

    if val_net_nonpos or edge_gone:
        return "FAIL"

    disc_ok = disc_net > 0 and disc_edge > 0
    val_ok = val_net > 0 and val_edge > 0 and np.isfinite(val_sh) and val_sh > 0 and not collapse
    if not disc_ok or not val_ok:
        return "FAIL"

    disc_sh = float(disc_row["calendar_edge_sharpe"])
    weaker = (
        np.isfinite(disc_sh)
        and np.isfinite(val_row["calendar_edge_sharpe"])
        and float(val_row["calendar_edge_sharpe"]) < 0.30 * disc_sh
    )
    fragile_hour = neigh_flag.startswith("FRAGILE")
    if weaker or fragile_hour:
        return "FRAGILE"

    rec_ok = np.isfinite(rec_net) and rec_net > 0 and np.isfinite(rec_edge) and rec_edge > 0
    neigh_ok = neigh_flag == "NEIGHBORHOOD STABLE"
    if rec_ok and neigh_ok and year_ok:
        return "STRONG SURVIVOR"
    if val_ok and disc_ok:
        return "SURVIVES"
    return "FRAGILE"


def materially_weaker(disc_row: pd.Series, val_row: pd.Series) -> bool:
    d = float(disc_row["calendar_edge_sharpe"])
    v = float(val_row["calendar_edge_sharpe"])
    if not np.isfinite(d) or not np.isfinite(v):
        return True
    return v < 0.30 * d


def cluster_note(top: pd.DataFrame, disc: pd.DataFrame) -> str:
    pairs = top.groupby(["entry_weekday", "exit_weekday"]).size().sort_values(ascending=False)
    lines = ["Top-20 entry→exit weekday pairs (count):"]
    for (a, b), n in pairs.items():
        hours = top.loc[(top["entry_weekday"] == a) & (top["exit_weekday"] == b), "entry_hour_NY"]
        hmin, hmax = int(hours.min()), int(hours.max())
        lines.append(f"- {n} rule{'s' if n != 1 else ''}: BUY {a} → SELL {b} (entry hours {hmin:02d}–{hmax:02d})")
    strong = disc.loc[
        (disc["mean_net_trade"] > 0)
        & (disc["mean_calendar_edge"] > 0)
        & (disc["calendar_edge_sharpe"] > 0)
        & (disc["n_trades"] >= MIN_DISC_TRADES)
    ]
    if not strong.empty:
        by_entry = strong.groupby("entry_weekday")["calendar_edge_sharpe"].median().sort_values(ascending=False)
        lines.append("Median discovery calendar-edge Sharpe among filter-passing windows, by entry weekday:")
        for wd, v in by_entry.items():
            lines.append(f"- {wd}: {v:.3f}")
        by_exit = strong.groupby("exit_weekday")["calendar_edge_sharpe"].median().sort_values(ascending=False)
        lines.append("Same, by exit weekday:")
        for wd, v in by_exit.items():
            lines.append(f"- {wd}: {v:.3f}")
    isolated = len(pairs) == len(top) and len(top) > 1
    if isolated:
        lines.append("Top-20 weekday pairs are all distinct — more consistent with isolated hours than a cluster.")
    else:
        lines.append("Repeated weekday pairs in the top 20 are evidence of a cluster rather than a single isolated hour.")
    return "\n".join(lines)


def write_report(
    meta: dict,
    grid: dict,
    mat: dict,
    disc: pd.DataFrame,
    top: pd.DataFrame,
    val: pd.DataFrame,
    rec: pd.DataFrame,
    full: pd.DataFrame,
    neigh: dict,
    years_top5: dict,
    classif: pd.DataFrame,
    bh: dict,
    boot: pd.DataFrame,
    dst_counts: dict,
    n_survives: int,
    n_strong: int,
    n_fail: int,
    n_fragile: int,
) -> str:
    lead = top.iloc[0]
    lead_val = lookup_row(val, int(lead["entry_slot"]), int(lead["exit_slot"]))
    lead_rec = lookup_row(rec, int(lead["entry_slot"]), int(lead["exit_slot"]))
    lead_full = lookup_row(full, int(lead["entry_slot"]), int(lead["exit_slot"]))
    lead_cls = classif.loc[classif["discovery_rank"] == 1].iloc[0]
    buy = slot_label(int(lead["entry_slot"]))
    sell = slot_label(int(lead["exit_slot"]))
    h = int(lead["holding_hours"])

    survivors = classif.loc[classif["classification"].isin(["SURVIVES", "STRONG SURVIVOR"])].copy()
    strongs = classif.loc[classif["classification"] == "STRONG SURVIVOR"]
    if not strongs.empty:
        best_surv = strongs.sort_values("discovery_rank").iloc[0]
        exec_label = "STRONG SURVIVOR (lowest discovery rank among strong)"
    elif not survivors.empty:
        best_surv = survivors.sort_values("discovery_rank").iloc[0]
        exec_label = "SURVIVES (lowest discovery rank among survivors)"
    else:
        best_surv = None
        exec_label = "none"

    if n_strong >= 1:
        final = "STRONG CALENDAR EFFECT"
    elif n_survives >= 1:
        final = "WEAK CALENDAR EFFECT"
    else:
        final = "NO ROBUST CALENDAR EFFECT"

    nf = neigh[int(lead["discovery_rank"])]
    neigh_lines = []
    for d in nf["details"]:
        neigh_lines.append(
            f"- {d.get('label', d['neighbor'])}: edge={fmt_num(d.get('mean_calendar_edge'))} "
            f"edge_Sharpe={fmt_num(d.get('calendar_edge_sharpe'))} "
            f"mean_net={fmt_num(d.get('mean_net_trade'))} similar={d.get('similar', False)}"
        )

    y5 = years_top5[int(lead["discovery_rank"])]
    y_ok, y_msg = year_concentration(y5)
    y_tbl = [
        "| Year | N | Year return (10 bps) | Mean trade (gross) | Win rate | Sharpe | Mean calendar edge |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for y in y5:
        y_tbl.append(
            f"| {y['year']} | {y['n_trades']} | {fmt_pct(y['year_return'])} | "
            f"{fmt_pct(y['mean_trade'])} | {fmt_pct(y['win_rate'])} | "
            f"{fmt_num(y['sharpe'])} | {fmt_pct(y['mean_calendar_edge'])} |"
        )

    lead_boot = boot.loc[boot["discovery_rank"] == 1].iloc[0]

    def period_block(name: str, row: pd.Series | None, bh_row: dict) -> list[str]:
        if row is None:
            return [f"## {name}", "No completed trades."]
        return [
            f"## {name}",
            f"$10,000 → {fmt_usd(row['ending_capital_from_10000'])}",
            f"Sharpe: {fmt_num(row['sharpe'])}",
            f"mean trade (gross): {fmt_pct(row['mean_trade_return'])}",
            f"mean net trade (10 bps): {fmt_pct(row['mean_net_trade'])}",
            f"calendar edge (mean): {fmt_pct(row['mean_calendar_edge'])}",
            f"calendar-edge Sharpe: {fmt_num(row['calendar_edge_sharpe'])}",
            f"win rate: {fmt_pct(row['win_rate'])}",
            f"max drawdown: {fmt_pct(row['max_drawdown'])}",
            f"CAGR: {fmt_pct(row['cagr'])}",
            f"N trades: {int(row['n_trades'])}",
            f"exposure: {fmt_pct(row['exposure_pct'])} ({int(lead['holding_hours'])} / 168 hours)",
            f"BTC buy & hold same calendar range (10 bps, one round trip): "
            f"{fmt_usd(START_CAP)} → {fmt_usd(bh_row['end_cap'])} (net {fmt_pct(bh_row['net'])}). "
            f"Buy & hold is a different exposure; it is not the anomaly benchmark.",
            "",
        ]

    q13 = "None. No frozen top-20 rule survived validation under the predeclared rule."
    surv_block: list[str] = []
    if best_surv is not None:
        br = int(best_surv["discovery_rank"])
        brow = top.loc[top["discovery_rank"] == br].iloc[0]
        bval = lookup_row(val, int(brow["entry_slot"]), int(brow["exit_slot"]))
        brec = lookup_row(rec, int(brow["entry_slot"]), int(brow["exit_slot"]))
        q13 = (
            f"{slot_label(int(brow['entry_slot']))} → {slot_label(int(brow['exit_slot']))} "
            f"({int(brow['holding_hours'])}h hold, exposure {fmt_pct(float(brow['exposure_pct']))}). "
            f"Classification: {best_surv['classification']}. "
            f"Discovery $10,000 → {fmt_usd(brow['ending_capital_from_10000'])}; "
            f"validation $10,000 → {fmt_usd(bval['ending_capital_from_10000']) if bval is not None else 'NA'}; "
            f"recent $10,000 → {fmt_usd(brec['ending_capital_from_10000']) if brec is not None else 'NA'}. "
            f"This is a frozen discovery candidate that passed the decision rule; "
            f"it is not an optimized live schedule. ({exec_label}.)"
        )
        byears = year_table(mat, int(brow["entry_slot"]), int(brow["holding_hours"]))
        by_ok, by_msg = year_concentration(byears)
        yt = [
            "| Year | N | Year return (10 bps) | Mean trade (gross) | Win rate | Sharpe | Mean calendar edge |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for y in byears:
            yt.append(
                f"| {y['year']} | {y['n_trades']} | {fmt_pct(y['year_return'])} | "
                f"{fmt_pct(y['mean_trade'])} | {fmt_pct(y['win_rate'])} | "
                f"{fmt_num(y['sharpe'])} | {fmt_pct(y['mean_calendar_edge'])} |"
            )
        bboot = boot.loc[boot["discovery_rank"] == br]
        surv_block = [
            "## Strongest surviving executable rule (frozen, not reselected)",
            "",
            f"**BUY:** {slot_label(int(brow['entry_slot']))} America/New_York",
            f"**SELL:** {slot_label(int(brow['exit_slot']))} America/New_York",
            f"**Holding:** {int(brow['holding_hours'])} hours "
            f"({fmt_pct(float(brow['exposure_pct']))} of the week). Discovery rank {br}.",
            "",
            f"- Discovery: $10,000 → {fmt_usd(brow['ending_capital_from_10000'])}; "
            f"Sharpe {fmt_num(brow['sharpe'])}; mean net {fmt_pct(brow['mean_net_trade'])}; "
            f"calendar edge {fmt_pct(brow['mean_calendar_edge'])}.",
            f"- Validation: $10,000 → {fmt_usd(bval['ending_capital_from_10000']) if bval is not None else 'NA'}; "
            f"Sharpe {fmt_num(bval['sharpe']) if bval is not None else 'NA'}; "
            f"mean net {fmt_pct(bval['mean_net_trade']) if bval is not None else 'NA'}; "
            f"calendar edge {fmt_pct(bval['mean_calendar_edge']) if bval is not None else 'NA'}.",
            f"- Recent: $10,000 → {fmt_usd(brec['ending_capital_from_10000']) if brec is not None else 'NA'}; "
            f"Sharpe {fmt_num(brec['sharpe']) if brec is not None else 'NA'}; "
            f"mean net {fmt_pct(brec['mean_net_trade']) if brec is not None else 'NA'}; "
            f"calendar edge {fmt_pct(brec['mean_calendar_edge']) if brec is not None else 'NA'}.",
            f"- Neighborhood: {best_surv['neighborhood']}. Year check: {by_msg} "
            f"({'not concentrated' if by_ok else 'concentrated / thin'}).",
            f"- Discovery costs: 0 bps {fmt_usd(brow['ending_capital_0bps'])}, "
            f"20 bps {fmt_usd(brow['ending_capital_20bps'])}, "
            f"50 bps {fmt_usd(brow['ending_capital_50bps'])}.",
            "",
            "Calendar-year path for this frozen rule (descriptive; not used for ranking):",
            "",
            *yt,
            "",
        ]
        if len(bboot):
            bb = bboot.iloc[0]
            surv_block += [
                f"Validation 95% CI mean net: [{fmt_pct(bb['val_net_lo'])}, {fmt_pct(bb['val_net_hi'])}]; "
                f"mean calendar edge: [{fmt_pct(bb['val_edge_lo'])}, {fmt_pct(bb['val_edge_hi'])}].",
                "",
            ]

    miss = meta["missing_hours"]
    miss_preview = ", ".join(str(x) for x in list(miss[:8])) if len(miss) else "none"
    if len(miss) > 8:
        miss_preview += f", ... ({len(miss)} total)"

    cls_tbl = [
        "| Rank | Window | Hold h | Class | Val $10k | Val Sharpe | Val mean net | Val edge | Recent mean net | Recent edge |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in classif.iterrows():
        cls_tbl.append(
            f"| {int(r['discovery_rank'])} | {r['window']} | {int(r['holding_hours'])} | {r['classification']} | "
            f"{fmt_usd(r['val_ending'])} | {fmt_num(r['val_sharpe'])} | {fmt_pct(r['val_mean_net'], 3)} | "
            f"{fmt_pct(r['val_mean_edge'], 3)} | {fmt_pct(r['rec_mean_net'], 3)} | {fmt_pct(r['rec_mean_edge'], 3)} |"
        )

    lines = [
        "# Weekly BTC calendar anomaly — Phase 3",
        "",
        "Discovery candidate search over 28,056 weekly day/hour windows.",
        "Not clean out-of-sample. Not a live trading system.",
        "Do not read this as “we discovered the optimal BTC schedule.”",
        "The real evidence is whether a **frozen** discovery candidate survives later periods.",
        "",
        "## BEST DISCOVERY WINDOW",
        "",
        f"**BUY:** {buy} America/New_York",
        "",
        f"**SELL:** {sell} America/New_York",
        "",
        f"**Holding:** {h} hours",
        "",
        f"Exposure: {fmt_pct(h / 168.0)} of each week. Ranked #1 by discovery **calendar-edge Sharpe** at 10 bps,",
        f"among windows with mean net trade > 0 and N ≥ {MIN_DISC_TRADES}.",
        "",
        *period_block("DISCOVERY (data start → 2021-12-31)", lead, bh["discovery"]),
        *period_block("VALIDATION (2022-01-01 → 2024-12-31)", lead_val, bh["validation"]),
        *period_block("RECENT (2025-01-01 → latest complete bar)", lead_rec, bh["recent"]),
        "## FULL HISTORY (DESCRIPTIVE ONLY)",
        "",
        "Not used for ranking or selection.",
        "",
    ]
    if lead_full is not None:
        lines += [
            f"$10,000 → {fmt_usd(lead_full['ending_capital_from_10000'])} after 10 bps.",
            f"Sharpe {fmt_num(lead_full['sharpe'])}; mean trade {fmt_pct(lead_full['mean_trade_return'])}; "
            f"calendar edge {fmt_pct(lead_full['mean_calendar_edge'])}.",
            "",
        ]
    lines += [
        "## Answers",
        "",
        f"1. What entry weekday/hour ranked #1 in discovery? **{buy} America/New_York.**",
        f"2. What exit weekday/hour ranked #1? **{sell} America/New_York.**",
        f"3. How long was the position held? **{h} hours** ({fmt_pct(h / 168.0)} of the week).",
        f"4. What happened to $10,000 after 10 bps? Discovery {fmt_usd(START_CAP)} → "
        f"{fmt_usd(lead['ending_capital_from_10000'])}. Validation "
        f"{fmt_usd(lead_val['ending_capital_from_10000']) if lead_val is not None else 'NA'}. "
        f"Recent {fmt_usd(lead_rec['ending_capital_from_10000']) if lead_rec is not None else 'NA'}.",
        f"5. Did the advantage survive 2022–2024? **"
        f"{'Yes on the predeclared rule' if lead_cls['classification'] in ('SURVIVES', 'STRONG SURVIVOR') else 'No / not as a survivor'}** "
        f"(classification: {lead_cls['classification']}). "
        f"Validation mean net {fmt_pct(lead_val['mean_net_trade']) if lead_val is not None else 'NA'}, "
        f"calendar edge {fmt_pct(lead_val['mean_calendar_edge']) if lead_val is not None else 'NA'}, "
        f"Sharpe {fmt_num(lead_val['sharpe']) if lead_val is not None else 'NA'}. "
        f"The rank-1 validation 95% CI for mean net includes zero, so the survival is statistical-sign, not economic size.",
        f"6. Did it survive 2025–latest? Recent mean net "
        f"{fmt_pct(lead_rec['mean_net_trade']) if lead_rec is not None else 'NA'}, "
        f"calendar edge {fmt_pct(lead_rec['mean_calendar_edge']) if lead_rec is not None else 'NA'}.",
        f"7. Was its calendar edge positive relative to same-duration windows? "
        f"Discovery mean edge {fmt_pct(lead['mean_calendar_edge'])} "
        f"(edge Sharpe {fmt_num(lead['calendar_edge_sharpe'])}); "
        f"fraction of weeks with positive edge {fmt_pct(lead['fraction_weeks_edge_positive'])}. "
        f"Validation mean edge {fmt_pct(lead_val['mean_calendar_edge']) if lead_val is not None else 'NA'}.",
        f"8. Are neighboring entry/exit hours also strong? **{nf['flag']}**",
        *neigh_lines,
        f"9. Does the result depend on one bull-market year? "
        f"{'Not obviously concentrated.' if y_ok else 'Yes, or too few positive-edge years.'} {y_msg}",
        "",
        *y_tbl,
        "",
        f"10. How sensitive is it to 20 and 50 bps? Discovery ending capital "
        f"0 bps {fmt_usd(lead['ending_capital_0bps'])}, "
        f"10 bps {fmt_usd(lead['ending_capital_10bps'])}, "
        f"20 bps {fmt_usd(lead['ending_capital_20bps'])}, "
        f"50 bps {fmt_usd(lead['ending_capital_50bps'])}. "
        f"Discovery mean net 20 bps {fmt_pct(lead['mean_net_20bps'])}, "
        f"50 bps {fmt_pct(lead['mean_net_50bps'])}.",
        f"11. How many of the original TOP 20 survive validation? "
        f"**{n_survives} SURVIVES** (of which **{n_strong} STRONG SURVIVOR**), "
        f"{n_fragile} FRAGILE, {n_fail} FAIL.",
        "12. Is there an identifiable CLUSTER?",
        cluster_note(top, disc),
        f"13. What is the strongest surviving executable rule? **{q13}**",
        f"14. Final classification: **{final}**",
        "",
        "The label follows the predeclared rule (at least one STRONG SURVIVOR → STRONG CALENDAR EFFECT). "
        "It is not a claim that a unique tradable schedule was found. 13 of 20 frozen candidates FAIL validation. "
        "About 28,000 tests were run in discovery.",
        "",
        *surv_block,
        "## Frozen top 20 — decision rule",
        "",
        *cls_tbl,
        "",
        "## Block bootstrap (4-week blocks, 2000 samples)",
        "",
        "Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.",
        "",
        f"Rank-1 validation 95% CI mean net trade: "
        f"[{fmt_pct(lead_boot['val_net_lo'])}, {fmt_pct(lead_boot['val_net_hi'])}]",
        f"Rank-1 validation 95% CI mean calendar edge: "
        f"[{fmt_pct(lead_boot['val_edge_lo'])}, {fmt_pct(lead_boot['val_edge_hi'])}]",
        "",
        "## Data audit",
        "",
        f"- File: `{H1_PATH}`",
        f"- UTC start/end: {meta['start_utc']} → {meta['end_utc']}",
        f"- NY start/end: {meta['start_ny']} → {meta['end_ny']}",
        f"- Bars: {meta['n_bars']}; unique UTC: {meta['unique']}; chronological: {meta['chronological']}; "
        f"OHLC valid: {meta['ohlc_valid']}",
        f"- Duplicated bars dropped: {meta['n_dup_dropped']}; invalid OHLC rows dropped: {meta['n_ohlc_drop']}",
        f"- Missing hours in the UTC 1h grid (not filled): {meta['n_missing_hours']}. Preview: {miss_preview}",
        f"- Monday-start NY weeks: {grid['n_weeks']} ({grid['first_monday'].date()} → {grid['last_monday'].date()})",
        f"- DST nonexistent/ambiguous labeled slots skipped: {grid['n_dst_skip']}",
        f"- Candidate-week observations skipped because entry or exit landed on a DST-invalid slot "
        f"(discovery scan count): {dst_counts['n_skip_dst_obs']}",
        f"- Candidate-week observations skipped because a Binance bar was missing "
        f"(discovery scan count): {dst_counts['n_skip_missing_obs']}",
        "",
        "### DST rule",
        "",
        "Schedules are America/New_York civil hours, not a fixed UTC offset. "
        "Each labeled slot is `tz_localize(..., ambiguous='NaT', nonexistent='NaT')`. "
        "Spring-forward missing hours and fall-back duplicated hours are skipped for that week. "
        "No fold is guessed.",
        "",
        "## Research design",
        "",
        "- Search space: 7×24 entry slots × 167 distinct future weekly exit slots = 28,056 windows.",
        "- Execution: buy the **open** of the 1h candle whose open equals the NY civil hour; sell the matching exit open.",
        "- Return = exit_open / entry_open − 1. No intra-candle information. Long only. No leverage. Cash outside the window.",
        "- One trade per week. Holding hours ∈ [1, 167], so the next weekly entry cannot overlap the open position.",
        "- Primary cost 10 bps round trip once per completed trade: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps. No extra slippage.",
        "- Same-duration control: for each week and holding H, median return across valid entry slots with that H. "
        f"Calendar edge = candidate week return − that median. Median requires ≥ {MIN_SLOTS_FOR_MEDIAN} valid slots that week.",
        "- Discovery / validation / recent splits are chronological and frozen. Full-history numbers are descriptive only.",
        "- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.",
        "",
        "## Multiple-testing warning",
        "",
        "About 28,000 rules were ranked on discovery. The best in-sample calendar-edge Sharpe **will** be biased upward. "
        "A discovery winner is a **discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters.",
        "",
        "## Audit assertions",
        "",
        "- No future data in ranking: discovery metrics use only bars with NY time < 2022-01-01, and both entry and exit must fall in that window.",
        "- Entry uses the entry-bar open only; the exit open is not used to decide whether to enter.",
        "- Validation did not affect ranking. Top 20 were frozen from discovery, then scored unchanged.",
        "- Full history was not used for candidate selection.",
        "- New York conversion uses `America/New_York` (EST/EDT). DST invalid hours are skipped, not filled.",
        "- Transaction costs applied once per completed trade.",
        "- Equity compounds net trade returns from $10,000 with cash = 0 between trades.",
        "- Positions do not overlap: holding_hours ≤ 167.",
        "- Same-duration calendar benchmark is the weekly median across the 168 start slots with that H.",
        "- Losing trades are retained; NaNs are skipped only for missing/DST-invalid timestamps.",
        "",
        f"Bootstrap seed={BOOT_SEED}, block={BOOT_BLOCK} weeks, samples={N_BOOT}.",
        "",
        f"Script runtime and environment are in the process log. Generated by `src/run_weekly_calendar_scan.py`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def merge_period_row(base: pd.DataFrame, extra: pd.DataFrame, suffix: str) -> pd.DataFrame:
    cols = [
        "entry_slot",
        "exit_slot",
        "n_trades",
        "mean_trade_return",
        "mean_net_trade",
        "win_rate",
        "ending_capital_from_10000",
        "cagr",
        "sharpe",
        "max_drawdown",
        "mean_calendar_edge",
        "calendar_edge_sharpe",
        "fraction_weeks_edge_positive",
        "ending_capital_0bps",
        "ending_capital_20bps",
        "ending_capital_50bps",
        "mean_net_20bps",
        "mean_net_50bps",
        "sharpe_20bps",
        "sharpe_50bps",
    ]
    e = extra[cols].copy()
    rename = {c: f"{c}_{suffix}" for c in cols if c not in ("entry_slot", "exit_slot")}
    e = e.rename(columns=rename)
    return base.merge(e, on=["entry_slot", "exit_slot"], how="left")


def series_for_candidate(mat: dict, entry_slot: int, h: int, in_period: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ret = returns_for_h(mat["prices"], h)
    valid = period_valid(in_period, h, ret)
    edge = edge_from_ret(ret, valid)
    g = ret[:, entry_slot][valid[:, entry_slot]]
    e = edge[:, entry_slot][valid[:, entry_slot]]
    return g, e


def main() -> None:
    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    log("=== Phase 3 weekly calendar scan ===")
    df = load_hourly()
    meta = df.attrs["meta"]
    grid = build_slot_grid(meta)
    mat = fill_price_matrix(df, grid)

    disc_start = meta["start_ny"]
    disc_end = DISC_END
    val_start = DISC_END
    val_end = VAL_END
    rec_start = VAL_END
    rec_end = meta["end_ny"] + pd.Timedelta(hours=1)

    log("Scanning discovery (all 28,056 windows)...")
    disc = scan_period(mat, mat["in_disc"], period_days(disc_start, disc_end), "discovery")
    dst_counts = {
        "n_skip_dst_obs": int(disc.attrs["n_skip_dst_obs"]),
        "n_skip_missing_obs": int(disc.attrs["n_skip_missing_obs"]),
    }
    log(
        f"discovery candidates={len(disc)} "
        f"DST-skipped obs={dst_counts['n_skip_dst_obs']} "
        f"missing-bar-skipped obs={dst_counts['n_skip_missing_obs']}"
    )

    eligible = rank_discovery(disc)
    top = eligible.head(TOP_N).copy()
    log(f"frozen top {len(top)} by calendar_edge_sharpe (eligible={len(eligible)})")
    if top.empty:
        raise RuntimeError("No frozen candidates.")

    log("Scoring frozen top 20 on validation / recent / full (descriptive)...")
    pairs = [(int(r["entry_slot"]), int(r["holding_hours"])) for _, r in top.iterrows()]
    val = score_subset(mat, mat["in_val"], period_days(val_start, val_end), "validation", pairs)
    rec = score_subset(mat, mat["in_rec"], period_days(rec_start, rec_end), "recent", pairs)
    full = score_subset(mat, mat["in_full"], period_days(disc_start, rec_end), "full_descriptive", pairs)

    log("Neighborhood diagnostics for top 5...")
    neigh = {}
    for _, row in top.head(TOP_NEIGHBOR).iterrows():
        flag, details = neighborhood_flag(disc, int(row["entry_slot"]), int(row["exit_slot"]))
        neigh[int(row["discovery_rank"])] = {"flag": flag, "details": details}
        log(f"  rank {int(row['discovery_rank'])} {slot_label(int(row['entry_slot']))} → "
            f"{slot_label(int(row['exit_slot']))}: {flag}")

    log("Year-by-year for top 5...")
    years_top5 = {}
    for _, row in top.head(TOP_NEIGHBOR).iterrows():
        years_top5[int(row["discovery_rank"])] = year_table(mat, int(row["entry_slot"]), int(row["holding_hours"]))

    log("Block bootstrap on frozen top 20...")
    boot_rows = []
    for _, row in top.iterrows():
        s = int(row["entry_slot"])
        h = int(row["holding_hours"])
        g_d, e_d = series_for_candidate(mat, s, h, mat["in_disc"])
        g_v, e_v = series_for_candidate(mat, s, h, mat["in_val"])
        net_d = net_from_gross(g_d, FEE_PRIMARY)
        net_v = net_from_gross(g_v, FEE_PRIMARY)
        d_net_lo, d_net_hi, _ = block_bootstrap_ci(net_d, seed=BOOT_SEED)
        d_e_lo, d_e_hi, _ = block_bootstrap_ci(e_d, seed=BOOT_SEED + 1)
        v_net_lo, v_net_hi, _ = block_bootstrap_ci(net_v, seed=BOOT_SEED + 2)
        v_e_lo, v_e_hi, _ = block_bootstrap_ci(e_v, seed=BOOT_SEED + 3)
        boot_rows.append(
            {
                "discovery_rank": int(row["discovery_rank"]),
                "entry_slot": s,
                "exit_slot": int(row["exit_slot"]),
                "disc_net_lo": d_net_lo,
                "disc_net_hi": d_net_hi,
                "disc_edge_lo": d_e_lo,
                "disc_edge_hi": d_e_hi,
                "val_net_lo": v_net_lo,
                "val_net_hi": v_net_hi,
                "val_edge_lo": v_e_lo,
                "val_edge_hi": v_e_hi,
            }
        )
    boot = pd.DataFrame(boot_rows)

    log("Classification...")
    class_rows = []
    for _, row in top.iterrows():
        vr = lookup_row(val, int(row["entry_slot"]), int(row["exit_slot"]))
        rr = lookup_row(rec, int(row["entry_slot"]), int(row["exit_slot"]))
        rank = int(row["discovery_rank"])
        nflag = neigh[rank]["flag"] if rank in neigh else "NA"
        y_ok, y_msg = year_concentration(years_top5[rank]) if rank in years_top5 else (False, "not in top 5")
        if rank > TOP_NEIGHBOR:
            y_ok, y_msg = year_concentration(year_table(mat, int(row["entry_slot"]), int(row["holding_hours"])))
            nflag = neighborhood_flag(disc, int(row["entry_slot"]), int(row["exit_slot"]))[0]
        cls = classify(row, vr, rr, nflag, y_ok)
        class_rows.append(
            {
                "discovery_rank": rank,
                "window": f"{slot_label(int(row['entry_slot']))} → {slot_label(int(row['exit_slot']))}",
                "entry_slot": int(row["entry_slot"]),
                "exit_slot": int(row["exit_slot"]),
                "holding_hours": int(row["holding_hours"]),
                "classification": cls,
                "neighborhood": nflag,
                "year_ok": y_ok,
                "year_note": y_msg,
                "val_ending": float(vr["ending_capital_from_10000"]) if vr is not None else np.nan,
                "val_sharpe": float(vr["sharpe"]) if vr is not None else np.nan,
                "val_mean_net": float(vr["mean_net_trade"]) if vr is not None else np.nan,
                "val_mean_edge": float(vr["mean_calendar_edge"]) if vr is not None else np.nan,
                "rec_mean_net": float(rr["mean_net_trade"]) if rr is not None else np.nan,
                "rec_mean_edge": float(rr["mean_calendar_edge"]) if rr is not None else np.nan,
            }
        )
    classif = pd.DataFrame(class_rows)
    n_strong = int((classif["classification"] == "STRONG SURVIVOR").sum())
    n_survives = int(classif["classification"].isin(["SURVIVES", "STRONG SURVIVOR"]).sum())
    n_fail = int((classif["classification"] == "FAIL").sum())
    n_fragile = int((classif["classification"] == "FRAGILE").sum())
    log(f"classifications: STRONG={n_strong} SURVIVES_total={n_survives} FRAGILE={n_fragile} FAIL={n_fail}")

    bh = {
        "discovery": buy_hold_period(df, meta["start_utc"], DISC_END.tz_convert("UTC"), FEE_PRIMARY),
        "validation": buy_hold_period(df, DISC_END.tz_convert("UTC"), VAL_END.tz_convert("UTC"), FEE_PRIMARY),
        "recent": buy_hold_period(df, VAL_END.tz_convert("UTC"), meta["end_utc"] + pd.Timedelta(hours=1), FEE_PRIMARY),
        "full": buy_hold_period(df, meta["start_utc"], meta["end_utc"] + pd.Timedelta(hours=1), FEE_PRIMARY),
    }

    log("Writing CSVs...")
    disc_out = disc.copy()
    disc_out.to_csv(RESULTS / "ALL_WINDOWS_DISCOVERY.csv", index=False)

    top_out = top.copy()
    top_out.to_csv(RESULTS / "TOP_CANDIDATES.csv", index=False)

    val_out = top[["discovery_rank", "entry_slot", "exit_slot", "entry_weekday", "entry_hour_NY",
                   "exit_weekday", "exit_hour_NY", "holding_hours", "exposure_pct"]].copy()
    val_out = merge_period_row(val_out, val, "validation")
    val_out = merge_period_row(val_out, rec, "recent")
    val_out = merge_period_row(val_out, full, "full_descriptive")
    val_out = val_out.merge(boot, on=["discovery_rank", "entry_slot", "exit_slot"], how="left")
    val_out = val_out.merge(
        classif[["discovery_rank", "classification", "neighborhood", "year_ok", "year_note"]],
        on="discovery_rank",
        how="left",
    )
    val_out.to_csv(RESULTS / "VALIDATION_RESULTS.csv", index=False)

    matrix = disc[
        [
            "entry_weekday",
            "entry_hour_NY",
            "exit_weekday",
            "exit_hour_NY",
            "entry_slot",
            "exit_slot",
            "holding_hours",
            "n_trades",
            "mean_calendar_edge",
            "median_calendar_edge",
            "calendar_edge_sharpe",
            "mean_net_trade",
            "sharpe",
            "ending_capital_from_10000",
        ]
    ].copy()
    matrix.to_csv(RESULTS / "CALENDAR_EDGE_MATRIX.csv", index=False)

    log("Building trade log for top 20...")
    tlog = extract_trade_log(mat, top)
    tlog.to_csv(RESULTS / "TRADE_LOG_TOP_CANDIDATES.csv", index=False)

    md = write_report(
        meta, grid, mat, disc, top, val, rec, full, neigh, years_top5, classif, bh, boot,
        dst_counts, n_survives, n_strong, n_fail, n_fragile,
    )
    (RESULTS / "WEEKLY_CALENDAR_ANOMALY.md").write_text(md, encoding="utf-8")

    # --- assertions ---
    assert int(disc["holding_hours"].min()) >= 1
    assert int(disc["holding_hours"].max()) <= 167
    assert len(disc) == N_SLOTS * (N_SLOTS - 1)
    assert top["discovery_rank"].tolist() == list(range(1, len(top) + 1))
    assert (top["mean_net_trade"] > 0).all()
    assert (top["n_trades"] >= MIN_DISC_TRADES).all()
    if len(tlog):
        ent = pd.to_datetime(tlog["entry_time_utc"], utc=True)
        ext = pd.to_datetime(tlog["exit_time_utc"], utc=True)
        assert (ext > ent).all()
        assert (tlog["holding_hours"] <= 167).all()
        disc_tr = tlog.loc[tlog["period"] == "discovery"]
        if len(disc_tr):
            disc_exit = pd.to_datetime(disc_tr["exit_time_utc"], utc=True)
            assert (disc_exit < DISC_END.tz_convert("UTC")).all(), "discovery trades used post-2021 prices"
    assert meta["unique"] and meta["chronological"] and meta["ohlc_valid"]
    overlap = disc.loc[disc["entry_slot"] == disc["exit_slot"]]
    assert overlap.empty
    log(f"assertions passed. elapsed={time.time() - t0:.1f}s")
    log(f"wrote {RESULTS}")
    log(f"BEST DISCOVERY: BUY {slot_label(int(top.iloc[0]['entry_slot']))}  "
        f"SELL {slot_label(int(top.iloc[0]['exit_slot']))}  H={int(top.iloc[0]['holding_hours'])}")
    log(f"classification leader={classif.iloc[0]['classification']}  final survivors={n_survives}")


if __name__ == "__main__":
    main()
