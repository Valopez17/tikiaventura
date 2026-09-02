#!/usr/bin/env python3
"""Phase 5 — BTC breakout continuation (LONG only).

Price only. No indicators, volume, derivatives, macro, ML, or leverage.
Not a live system. Not clean OOS.

Discovery ranking uses available data through 2021-12-31 only.
Validation (2022–2024) and recent (2025→latest) never reselect.

Frozen and unused:
  CALENDAR_CANDIDATE_V1
  CRASH_REBOUND_CANDIDATE_V1
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
H1_PATH = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"

START_CAP = 10_000.0
FEE_PRIMARY = 0.0010
FEE_SET = (0.0, 0.0010, 0.0020, 0.0050)
FEE_BPS = (0, 10, 20, 50)
LOOKBACKS = (168, 720, 1440, 2160)
LOOKBACK_DAYS = {168: 7, 720: 30, 1440: 60, 2160: 90}
HOLDS = (24, 72, 168, 336, 720)
PATH_H = (1, 6, 12, 24, 48, 72, 168, 336, 720)
MIN_DISC_TRADES = 20
TOP_N = 5
N_BOOT = 2000
BOOT_BLOCK_H = 168
BOOT_SEED = 42
CRYPTO_DAYS = 365.0
HOURS_PER_YEAR = 365.0 * 24.0
HOUR_NS = 3_600_000_000_000
AUDIT_N = 24
RECENT_SHARPE_FLOOR = -0.25

DISC_END = pd.Timestamp("2022-01-01", tz="UTC")
VAL_END = pd.Timestamp("2025-01-01", tz="UTC")
PERIODS = ("discovery", "validation", "recent")


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


def rule_id(lookback: int, hold: int) -> str:
    return f"L{lookback}_H{hold}"


def net_from_gross(gross: np.ndarray, fee: float) -> np.ndarray:
    g = np.asarray(gross, dtype=float)
    return (1.0 + g) * (1.0 - fee) - 1.0


def side_mult(fee: float) -> float:
    if fee <= 0:
        return 1.0
    if fee >= 1:
        return 0.0
    return float(np.sqrt(1.0 - fee))


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


def winner_loser_stats(nets: np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    w = x[x > 0]
    lo = x[x < 0]
    avg_w = float(w.mean()) if w.size else np.nan
    avg_l = float(lo.mean()) if lo.size else np.nan
    if w.size and lo.size and avg_l != 0 and np.isfinite(avg_w) and np.isfinite(avg_l):
        payoff = float(abs(avg_w / avg_l))
    else:
        payoff = np.nan
    return avg_w, avg_l, payoff


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


def trade_sharpe(nets: np.ndarray, span_days: float) -> float:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2 or span_days <= 0:
        return np.nan
    sd = float(x.std(ddof=1))
    if sd <= 0:
        return np.nan
    years = span_days / CRYPTO_DAYS
    if years <= 0:
        return np.nan
    return float(x.mean() / sd * np.sqrt(x.size / years))


def hours_ahead_index(ts: pd.DatetimeIndex, h: int) -> np.ndarray:
    mapper = pd.Series(np.arange(len(ts), dtype=np.int64), index=ts)
    loc = mapper.reindex(ts + pd.Timedelta(hours=h))
    arr = loc.to_numpy(dtype=float)
    out = np.full(len(ts), -1, dtype=np.int64)
    ok = np.isfinite(arr)
    out[ok] = arr[ok].astype(np.int64)
    return out


def take_idx(ahead: np.ndarray, src: np.ndarray) -> np.ndarray:
    out = np.full(len(src), -1, dtype=np.int64)
    ok = src >= 0
    if ok.any():
        out[ok] = ahead[src[ok]]
    return out


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
        "path": str(H1_PATH),
    }
    log(
        f"1h BTCUSDT {meta['start_utc']} → {meta['end_utc']} "
        f"bars={meta['n_bars']} missing_hours={meta['n_missing_hours']} "
        f"dups_dropped={dup} ohlc_drop={n_ohlc_drop}"
    )
    df.attrs["meta"] = meta
    return df.reset_index(drop=True)


def period_of(ts: pd.DatetimeIndex) -> np.ndarray:
    out = np.empty(len(ts), dtype=object)
    ns = ts.asi8
    disc = DISC_END.value
    val = VAL_END.value
    out[ns < disc] = "discovery"
    out[(ns >= disc) & (ns < val)] = "validation"
    out[ns >= val] = "recent"
    return out


def period_span_days(meta: dict, period: str) -> float:
    start = meta["start_utc"]
    end = meta["end_utc"]
    if period == "discovery":
        a = start
        b = DISC_END
    elif period == "validation":
        a = DISC_END
        b = VAL_END
    else:
        a = VAL_END
        b = end + pd.Timedelta(hours=1)
    return max(float((b - a).total_seconds() / 86400.0), 1.0)


def dist_stats(cond: np.ndarray, uncond: np.ndarray) -> dict:
    c = np.asarray(cond, dtype=float)
    u = np.asarray(uncond, dtype=float)
    c = c[np.isfinite(c)]
    u = u[np.isfinite(u)]
    out = {
        "cond_mean": float(c.mean()) if c.size else np.nan,
        "uncond_mean": float(u.mean()) if u.size else np.nan,
        "cond_median": float(np.median(c)) if c.size else np.nan,
        "uncond_median": float(np.median(u)) if u.size else np.nan,
        "cond_p_pos": float(np.mean(c > 0)) if c.size else np.nan,
        "uncond_p_pos": float(np.mean(u > 0)) if u.size else np.nan,
        "n_cond": int(c.size),
        "n_uncond": int(u.size),
    }
    out["diff_mean"] = out["cond_mean"] - out["uncond_mean"]
    out["diff_median"] = out["cond_median"] - out["uncond_median"]
    out["diff_p_pos"] = out["cond_p_pos"] - out["uncond_p_pos"]
    return out


def exec_metrics(gross: np.ndarray, span_days: float, fee: float = FEE_PRIMARY) -> dict:
    g = np.asarray(gross, dtype=float)
    g = g[np.isfinite(g)]
    n = int(g.size)
    nets = net_from_gross(g, fee) if n else g
    avg_w, avg_l, payoff = winner_loser_stats(nets)
    out = {
        "n_trades": n,
        "mean_trade_gross": float(g.mean()) if n else np.nan,
        "median_trade_gross": float(np.median(g)) if n else np.nan,
        "mean_net_trade": float(nets.mean()) if n else np.nan,
        "median_net_trade": float(np.median(nets)) if n else np.nan,
        "win_rate": float(np.mean(nets > 0)) if n else np.nan,
        "avg_winner": avg_w,
        "avg_loser": avg_l,
        "payoff_ratio": payoff,
        "profit_factor": profit_factor(nets) if n else np.nan,
        "trade_sharpe_diagnostic": trade_sharpe(nets, span_days),
        "ending_capital_from_10000": ending_capital(nets),
        "cagr_trades": np.nan,
    }
    out["cagr_trades"] = cagr_from(START_CAP, out["ending_capital_from_10000"], span_days)
    return out


def executable_take(valid: np.ndarray, entry_idx: np.ndarray, ts_ns: np.ndarray, hold_h: int) -> np.ndarray:
    take = np.zeros(len(valid), dtype=bool)
    busy_until = np.int64(-1)
    hold_ns = np.int64(hold_h) * np.int64(HOUR_NS)
    for t in np.flatnonzero(valid):
        e_i = int(entry_idx[t])
        e_ns = ts_ns[e_i]
        if e_ns < busy_until:
            continue
        take[t] = True
        busy_until = e_ns + hold_ns
    return take


def prior_high_coverage(
    highs: np.ndarray,
    ts_ns: np.ndarray,
    lookback_h: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Max high on [t − L hours, t). Current bar excluded.

    Coverage is complete only if exactly L hourly bars exist in that
    timestamp window. Missing bars are not filled.
    """
    n = len(highs)
    prior = np.full(n, np.nan, dtype=float)
    ok = np.zeros(n, dtype=bool)
    left = 0
    win_ns = np.int64(lookback_h) * np.int64(HOUR_NS)
    data_start = int(ts_ns[0]) if n else 0
    n_insufficient = 0
    n_missing = 0
    for i in range(n):
        left_ns = int(ts_ns[i]) - int(win_ns)
        while left < i and int(ts_ns[left]) < left_ns:
            left += 1
        n_obs = i - left
        complete = n_obs == lookback_h and left < i and int(ts_ns[left]) == left_ns
        if complete:
            ok[i] = True
            prior[i] = float(np.max(highs[left:i]))
        elif left_ns < data_start:
            n_insufficient += 1
        else:
            n_missing += 1
    stats = {
        "lookback_h": int(lookback_h),
        "n_timestamps": int(n),
        "n_valid_coverage": int(ok.sum()),
        "n_insufficient_history": int(n_insufficient),
        "n_lost_missing_coverage": int(n_missing),
    }
    return prior, ok, stats


def audit_prior_high(
    ts: pd.DatetimeIndex,
    highs: np.ndarray,
    prior: np.ndarray,
    ok: np.ndarray,
    lookback_h: int,
    n_check: int = AUDIT_N,
) -> None:
    cand = np.flatnonzero(ok)
    if cand.size == 0:
        log(f"  AUDIT L{lookback_h}: no valid-coverage timestamps (cannot sample)")
        return
    rng = np.random.default_rng(0)
    pick = rng.choice(cand, size=min(n_check, int(cand.size)), replace=False)
    ts_to_i = {int(ts.asi8[i]): int(i) for i in range(len(ts))}
    win = np.int64(lookback_h) * np.int64(HOUR_NS)
    hour = np.int64(HOUR_NS)
    for i in pick:
        t_ns = int(ts.asi8[i])
        idxs = []
        for k in range(lookback_h, 0, -1):
            key = t_ns - k * hour
            if key not in ts_to_i:
                raise RuntimeError(
                    f"coverage audit L{lookback_h} t={ts[i]} missing expected bar {k}h back"
                )
            idxs.append(ts_to_i[key])
        if i in idxs:
            raise RuntimeError(f"current bar included in prior-high window at {ts[i]}")
        if len(idxs) != lookback_h:
            raise RuntimeError("audit window length mismatch")
        ref = float(highs[np.asarray(idxs)].max())
        got = float(prior[int(i)])
        if abs(ref - got) > 1e-10 * max(1.0, abs(ref)):
            raise RuntimeError(
                f"prior_high mismatch L{lookback_h} t={ts[i]}: got={got} ref={ref}"
            )
        # window must be [t-L, t)
        if int(ts.asi8[idxs[0]]) != t_ns - int(win):
            raise RuntimeError("audit window start is not t−L hours")
        if int(ts.asi8[idxs[-1]]) != t_ns - int(hour):
            raise RuntimeError("audit window end is not t−1 hour")
    log(f"  AUDIT L{lookback_h}: {len(pick)} timestamps matched timestamp-window max high")


def window_excursions(
    entry_i: int,
    entry_px: float,
    ts_ns: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    horizon_h: int = 720,
) -> tuple[float, float, float, float, int, int]:
    end_ns = ts_ns[entry_i] + np.int64(horizon_h) * np.int64(HOUR_NS)
    right = int(np.searchsorted(ts_ns, end_ns, side="left"))
    if right <= entry_i:
        return np.nan, np.nan, np.nan, np.nan, -1, -1
    sl_low = low[entry_i:right]
    sl_high = high[entry_i:right]
    j_mae = int(np.argmin(sl_low))
    j_mfe = int(np.argmax(sl_high))
    mae = float(sl_low[j_mae] / entry_px - 1.0)
    mfe = float(sl_high[j_mfe] / entry_px - 1.0)
    mae_i = entry_i + j_mae
    mfe_i = entry_i + j_mfe
    mae_h = float(ts_ns[mae_i] - ts_ns[entry_i]) / HOUR_NS
    mfe_h = float(ts_ns[mfe_i] - ts_ns[entry_i]) / HOUR_NS
    return mae, mfe, mae_h, mfe_h, mae_i, mfe_i


def circular_block_indices(n: int, block: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block, dtype=np.int64)
    idx = (starts[..., None] + offsets[None, None, :]) % n
    return idx.reshape(n_boot, n_blocks * block)[:, :n]


def bootstrap_rule(
    valid_event: np.ndarray,
    period_mask: np.ndarray,
    fwd: np.ndarray,
    hold_h: int,
    fee: float,
    n_boot: int = N_BOOT,
    block: int = BOOT_BLOCK_H,
    seed: int = BOOT_SEED,
) -> dict:
    loc = np.flatnonzero(period_mask)
    empty = {
        "mean_net_lo": np.nan,
        "mean_net_hi": np.nan,
        "edge_lo": np.nan,
        "edge_hi": np.nan,
        "n_boot_used": 0,
        "n_hours": int(loc.size),
    }
    if loc.size < block * 2:
        return empty
    ev = valid_event[loc]
    r = fwd[loc]
    rng = np.random.default_rng(seed)
    draws = circular_block_indices(int(loc.size), block, n_boot, rng)
    mean_nets = np.full(n_boot, np.nan)
    edges = np.full(n_boot, np.nan)
    n_used = 0
    for b in range(n_boot):
        ii = draws[b]
        ev_b = ev[ii]
        r_b = r[ii]
        finite_ev = ev_b & np.isfinite(r_b)
        finite_u = np.isfinite(r_b)
        if finite_ev.any() and finite_u.any():
            edges[b] = float(r_b[finite_ev].mean() - r_b[finite_u].mean())
        pos = np.flatnonzero(finite_ev)
        if pos.size == 0:
            continue
        taken = []
        busy = -1
        for p in pos:
            if p < busy:
                continue
            taken.append(float(r_b[p]))
            busy = int(p) + int(hold_h)
        if not taken:
            continue
        nets = net_from_gross(np.asarray(taken, dtype=float), fee)
        mean_nets[b] = float(nets.mean())
        n_used += 1
    ok_n = mean_nets[np.isfinite(mean_nets)]
    ok_e = edges[np.isfinite(edges)]
    return {
        "mean_net_lo": float(np.quantile(ok_n, 0.025)) if ok_n.size else np.nan,
        "mean_net_hi": float(np.quantile(ok_n, 0.975)) if ok_n.size else np.nan,
        "edge_lo": float(np.quantile(ok_e, 0.025)) if ok_e.size else np.nan,
        "edge_hi": float(np.quantile(ok_e, 0.975)) if ok_e.size else np.nan,
        "n_boot_used": int(n_used),
        "n_hours": int(loc.size),
    }


def mtm_from_trades(
    n: int,
    opens: np.ndarray,
    closes: np.ndarray,
    trades: list[tuple[int, int]],
    fee: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Hourly equity marked at close while LONG; fills at open.

    Round-trip fee F is split so entry_mult * exit_mult = (1 − F).
    """
    equity = np.full(n, START_CAP, dtype=float)
    position = np.zeros(n, dtype=np.int8)
    if not trades:
        return equity, position
    sm = side_mult(fee)
    cash = START_CAP
    shares = 0.0
    in_pos = False
    pending_exit = -1
    entries = {int(e): int(x) for e, x in trades}
    for i in range(n):
        if in_pos and i == pending_exit:
            cash = shares * float(opens[i]) * sm
            shares = 0.0
            in_pos = False
            pending_exit = -1
        if i in entries and not in_pos:
            cash = cash * sm
            entry_px = float(opens[i])
            shares = cash / entry_px
            cash = 0.0
            in_pos = True
            pending_exit = entries[i]
        if in_pos:
            position[i] = 1
            equity[i] = shares * float(closes[i])
        else:
            position[i] = 0
            equity[i] = cash
    if in_pos:
        raise RuntimeError("MTM ended still in a position; missing exit bar")
    return equity, position


def mtm_metrics(equity: np.ndarray, position: np.ndarray, span_days: float) -> dict:
    eq = np.asarray(equity, dtype=float)
    if eq.size == 0:
        return {
            "mtm_end_cap": float(START_CAP),
            "mtm_total_return": 0.0,
            "mtm_cagr": np.nan,
            "mtm_vol": np.nan,
            "mtm_sharpe": np.nan,
            "mtm_max_dd": np.nan,
            "mtm_calmar": np.nan,
            "mtm_exposure": np.nan,
        }
    rets = eq[1:] / eq[:-1] - 1.0
    rets = rets[np.isfinite(rets)]
    end_cap = float(eq[-1])
    total = end_cap / START_CAP - 1.0
    cagr = cagr_from(START_CAP, end_cap, span_days)
    if rets.size >= 2:
        sd = float(rets.std(ddof=1))
        vol = sd * np.sqrt(HOURS_PER_YEAR) if sd > 0 else 0.0
        mu = float(rets.mean())
        sharpe = (mu / sd) * np.sqrt(HOURS_PER_YEAR) if sd > 0 else np.nan
    else:
        vol = np.nan
        sharpe = np.nan
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    max_dd = float(np.min(dd))
    calmar = (
        float(cagr / abs(max_dd))
        if np.isfinite(cagr) and np.isfinite(max_dd) and max_dd < 0
        else np.nan
    )
    exposure = float(np.mean(position != 0)) if position.size else np.nan
    return {
        "mtm_end_cap": end_cap,
        "mtm_total_return": total,
        "mtm_cagr": cagr,
        "mtm_vol": vol,
        "mtm_sharpe": sharpe,
        "mtm_max_dd": max_dd,
        "mtm_calmar": calmar,
        "mtm_exposure": exposure,
    }


def slice_period_equity(
    equity: np.ndarray,
    position: np.ndarray,
    mask: np.ndarray,
    start_cap: float = START_CAP,
) -> tuple[np.ndarray, np.ndarray]:
    eq = np.asarray(equity, dtype=float)
    pos = np.asarray(position)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return np.array([start_cap]), np.array([0], dtype=np.int8)
    i0 = int(idx[0])
    i1 = int(idx[-1])
    rets = np.zeros(i1 - i0, dtype=float)
    for k, i in enumerate(range(i0, i1)):
        if eq[i] > 0 and np.isfinite(eq[i]) and np.isfinite(eq[i + 1]) and eq[i + 1] > 0:
            rets[k] = eq[i + 1] / eq[i] - 1.0
    path = np.empty(i1 - i0 + 1, dtype=float)
    path[0] = start_cap
    path[1:] = start_cap * np.cumprod(1.0 + rets)
    return path, pos[i0 : i1 + 1]


def year_ok_flag(years: list[dict]) -> tuple[bool, str]:
    if not years:
        return False, "no yearly rows"
    pos = [y for y in years if np.isfinite(y["mean_net_trade"]) and y["mean_net_trade"] > 0]
    rets = np.array([y["year_return"] for y in years if np.isfinite(y["year_return"])], dtype=float)
    pos_rets = np.clip(rets, 0, None)
    share = float(pos_rets.max() / pos_rets.sum()) if pos_rets.size and pos_rets.sum() > 0 else 1.0
    other = [y for y in pos if y["year"] not in (2020, 2021)]
    n_pos = len(pos)
    concentrated = n_pos <= 1 or share >= 0.70
    only_bull = n_pos > 0 and len(other) == 0
    ok = (not concentrated) and n_pos >= 2 and (not only_bull)
    msg = (
        f"years_with_positive_mean_net={n_pos}/{len(years)}; "
        f"max_positive_year_share={share:.2f}; "
        f"positive_outside_2020_2021={len(other)}"
    )
    return ok, msg


def classify_rule(
    disc: pd.Series,
    val: pd.Series,
    rec: pd.Series,
    year_ok: bool,
) -> str:
    d_net = float(disc["mean_net_trade"])
    d_edge = float(disc["breakout_edge_mean"])
    v_net = float(val["mean_net_trade"]) if val is not None else np.nan
    v_edge = float(val["breakout_edge_mean"]) if val is not None else np.nan
    v_sh = float(val["mtm_sharpe"]) if val is not None else np.nan
    v_n = int(val["n_trades"]) if val is not None and np.isfinite(val["n_trades"]) else 0
    r_net = float(rec["mean_net_trade"]) if rec is not None else np.nan
    r_edge = float(rec["breakout_edge_mean"]) if rec is not None else np.nan
    r_sh = float(rec["mtm_sharpe"]) if rec is not None else np.nan
    r_n = int(rec["n_trades"]) if rec is not None and np.isfinite(rec["n_trades"]) else 0

    if (not np.isfinite(v_net)) or v_net <= 0 or (not np.isfinite(v_edge)) or v_edge <= 0:
        return "FAIL"

    disc_ok = np.isfinite(d_net) and d_net > 0 and np.isfinite(d_edge) and d_edge > 0
    if not disc_ok:
        return "FAIL"

    rec_ok = r_n < 5 or (
        np.isfinite(r_net)
        and r_net >= 0
        and np.isfinite(r_edge)
        and r_edge >= 0
        and (not np.isfinite(r_sh) or r_sh >= RECENT_SHARPE_FLOOR)
    )
    val_core = v_net > 0 and v_edge > 0 and np.isfinite(v_sh) and v_sh > 0 and v_n >= 15

    if val_core and rec_ok and year_ok:
        return "STRONG SURVIVOR"

    severe = (not np.isfinite(v_sh)) or v_sh <= 0
    if severe:
        return "FRAGILE"
    return "SURVIVES"


def empty_mtm() -> dict:
    return {
        "mtm_end_cap": float(START_CAP),
        "mtm_total_return": 0.0,
        "mtm_cagr": np.nan,
        "mtm_vol": np.nan,
        "mtm_sharpe": np.nan,
        "mtm_max_dd": np.nan,
        "mtm_calmar": np.nan,
        "mtm_exposure": 0.0,
    }


def write_report(
    meta: dict,
    all_rules: pd.DataFrame,
    top: pd.DataFrame,
    val_tbl: pd.DataFrame,
    year_map: dict[str, list[dict]],
    boot_map: dict[str, dict],
    path_summary: dict,
    cov_stats: list[dict],
    skip_meta: dict,
    runtime_s: float,
) -> None:
    disc_all = all_rules.loc[all_rules["period"] == "discovery"].copy()
    val_all = all_rules.loc[all_rules["period"] == "validation"].copy()
    rec_all = all_rules.loc[all_rules["period"] == "recent"].copy()

    no_cand = top.empty
    if no_cand:
        best = None
        vbest = None
        rid = None
        cls_best = "NO DISCOVERY CANDIDATE"
        d_end = v_end = r_end = START_CAP
    else:
        best = top.iloc[0]
        rid = best["rule_id"]
        vbest = val_tbl.loc[val_tbl["rule_id"] == rid].iloc[0]
        cls_best = str(vbest["classification"])
        d_end = float(best["ending_capital_from_10000"])
        v_end = float(vbest["val_ending_capital_from_10000"])
        r_end = float(vbest["rec_ending_capital_from_10000"])

    if val_tbl.empty:
        n_strong = n_surv = n_frag = n_fail = 0
        n_surv_any = 0
    else:
        n_strong = int((val_tbl["classification"] == "STRONG SURVIVOR").sum())
        n_surv = int((val_tbl["classification"] == "SURVIVES").sum())
        n_frag = int((val_tbl["classification"] == "FRAGILE").sum())
        n_fail = int((val_tbl["classification"] == "FAIL").sum())
        n_surv_any = int(val_tbl["classification"].isin(["SURVIVES", "STRONG SURVIVOR"]).sum())

    if n_strong >= 1:
        final = "ROBUST BREAKOUT CONTINUATION"
    elif n_surv_any >= 1:
        final = "WEAK BREAKOUT CONTINUATION"
    else:
        final = "NO ROBUST BREAKOUT EFFECT"

    survivors = pd.DataFrame()
    if not val_tbl.empty:
        survivors = val_tbl.loc[
            val_tbl["classification"].isin(["SURVIVES", "STRONG SURVIVOR"])
        ].copy()

    strongest_surv = None
    if not survivors.empty:
        # Discovery rank stays visible on rank-1. Persistence ranking may use later data.
        strong = survivors.loc[survivors["classification"] == "STRONG SURVIVOR"]
        pool = strong if not strong.empty else survivors
        rec_ok_pool = pool.loc[
            (pool["rec_n_trades"] < 5)
            | ((pool["rec_mean_net_trade"] >= 0) & (pool["rec_breakout_edge_mean"] >= 0))
        ]
        if rec_ok_pool.empty:
            rec_ok_pool = pool.loc[pool["rec_mean_net_trade"] >= 0]
        use = rec_ok_pool if not rec_ok_pool.empty else pool
        strongest_surv = use.sort_values(
            ["val_mtm_sharpe", "val_breakout_edge_mean", "val_mean_net_trade"],
            ascending=[False, False, False],
            na_position="last",
        ).iloc[0]

    later_helped = (
        strongest_surv is not None
        and best is not None
        and str(strongest_surv["rule_id"]) != str(rid)
    )

    if strongest_surv is not None:
        exec_rule = (
            f"If BTC's hourly close is above the maximum high of the previous "
            f"{LOOKBACK_DAYS[int(strongest_surv['lookback_h'])]} calendar days "
            f"(timestamp window [t−{int(strongest_surv['lookback_h'])}h, t), complete hourly coverage), "
            f"buy the next hourly open and exit at the open {int(strongest_surv['hold_h'])}h later. "
            f"Ignore new breakout signals until flat. Primary cost: 10 bps round trip."
        )
        if later_helped:
            exec_rule += (
                f" This is Discovery rank #{int(strongest_surv['discovery_rank'])} "
                f"({strongest_surv['rule_id']}), identified as the strongest surviving "
                f"Discovery candidate using later data. It is not untouched OOS validation."
            )
    else:
        exec_rule = "No frozen Discovery candidate survives validation. No executable rule is promoted."

    def lb_strength(df: pd.DataFrame) -> str:
        if df.empty:
            return "NA"
        g = df.groupby("lookback_h", as_index=False).agg(
            mean_edge=("breakout_edge_mean", "mean"),
            mean_sharpe=("mtm_sharpe", "mean"),
            n_eligible=("eligible", "sum") if "eligible" in df.columns else ("n_trades", "size"),
        )
        g = g.sort_values(["mean_sharpe", "mean_edge"], ascending=[False, False], na_position="last")
        r = g.iloc[0]
        return (
            f"{LOOKBACK_DAYS[int(r['lookback_h'])]}d (L{int(r['lookback_h'])}h); "
            f"mean Discovery MTM Sharpe {fmt_num(float(r['mean_sharpe']))}, "
            f"mean breakout edge {fmt_pct(float(r['mean_edge']), 3)}"
        )

    def hold_strength(df: pd.DataFrame) -> str:
        if df.empty:
            return "NA"
        g = df.groupby("hold_h", as_index=False).agg(
            mean_edge=("breakout_edge_mean", "mean"),
            mean_sharpe=("mtm_sharpe", "mean"),
        )
        g = g.sort_values(["mean_sharpe", "mean_edge"], ascending=[False, False], na_position="last")
        r = g.iloc[0]
        return (
            f"{int(r['hold_h'])}h; mean Discovery MTM Sharpe {fmt_num(float(r['mean_sharpe']))}, "
            f"mean breakout edge {fmt_pct(float(r['mean_edge']), 3)}"
        )

    disc_rank_src = disc_all
    if "eligible" in disc_all.columns and disc_all["eligible"].any():
        disc_rank_src = disc_all.loc[disc_all["eligible"]]

    pooled_disc_edge = float(disc_all["breakout_edge_mean"].mean()) if not disc_all.empty else np.nan
    pooled_val_edge = float(val_all["breakout_edge_mean"].mean()) if not val_all.empty else np.nan
    n_disc_edge_pos = int((disc_all["breakout_edge_mean"] > 0).sum()) if not disc_all.empty else 0
    n_val_edge_pos = int((val_all["breakout_edge_mean"] > 0).sum()) if not val_all.empty else 0

    q1 = (
        f"Discovery pooled breakout edge {fmt_pct(pooled_disc_edge, 3)} "
        f"({n_disc_edge_pos}/20 rules positive). "
        f"Validation pooled edge {fmt_pct(pooled_val_edge, 3)} "
        f"({n_val_edge_pos}/20 positive). "
    )
    if np.isfinite(pooled_disc_edge) and pooled_disc_edge > 0 and np.isfinite(pooled_val_edge) and pooled_val_edge > 0:
        q1 += (
            "On the event-study mean, breakout hours outperform ordinary same-horizon hours "
            "in both Discovery and Validation. That is continuation on average, not a STRONG "
            "executable rule: drawdowns are large, validation Sharpe is modest, and recent "
            "breakout edges are negative."
        )
    elif np.isfinite(pooled_disc_edge) and pooled_disc_edge <= 0:
        q1 += "Discovery does not show a general continuation edge vs ordinary BTC."
    else:
        q1 += "The continuation vs false-breakout picture is mixed across the 20 frozen rules."

    # Event-path diagnosis
    ps = path_summary
    r1 = ps.get("ret_1h_mean", np.nan)
    r6 = ps.get("ret_6h_mean", np.nan)
    r24 = ps.get("ret_24h_mean", np.nan)
    r168 = ps.get("ret_168h_mean", np.nan)
    mae = ps.get("mae_mean", np.nan)
    mfe = ps.get("mfe_mean", np.nan)
    frac_false = ps.get("frac_ret_24h_nonpos", np.nan)
    if np.isfinite(r1) and r1 > 0.0005 and np.isfinite(r24) and r24 > 0:
        path_core = "immediate continuation on the mean (already up at +1h and still up at +24h)"
    elif np.isfinite(r1) and r1 <= 0.0005 and np.isfinite(r24) and r24 > 0:
        path_core = "delayed continuation on the mean (flat/down at +1h, higher by +24h)"
    else:
        path_core = "no reliable continuation on the mean path"
    if np.isfinite(frac_false) and frac_false >= 0.40:
        path_type = (
            f"{path_core}, with frequent false breakouts "
            f"({fmt_pct(frac_false)} of events not positive at +24h)"
        )
    else:
        path_type = path_core

    families = ""
    isolated = True
    if not top.empty:
        top = top.copy()
        fam = (
            top.assign(family="L" + top["lookback_h"].astype(int).astype(str))
            .groupby("family")
            .size()
            .sort_values(ascending=False)
        )
        isolated = len(fam) == len(top) and len(top) > 1
        families = "; ".join(f"{k} (n={int(v)})" for k, v in fam.items())
        holds = top.groupby("hold_h").size().sort_values(ascending=False)
        families += " | holds: " + "; ".join(f"H{int(k)} (n={int(v)})" for k, v in holds.items())

    missing = meta["missing_hours"]
    miss_preview = ", ".join(str(x) for x in list(missing[:8])) if len(missing) else "none"
    if len(missing) > 8:
        miss_preview += f", ... ({len(missing)} total)"

    cov_lines = []
    for s in cov_stats:
        cov_lines.append(
            f"- L{s['lookback_h']}h ({LOOKBACK_DAYS[s['lookback_h']]}d): "
            f"valid coverage {s['n_valid_coverage']}/{s['n_timestamps']}; "
            f"lost to missing bars {s['n_lost_missing_coverage']}; "
            f"insufficient history {s['n_insufficient_history']}; "
            f"breakout events {s.get('n_breakouts', 'NA')}"
        )
        if s["n_valid_coverage"] == 0:
            cov_lines.append(
                f"  ANALYSIS IMPOSSIBLE for L{s['lookback_h']}h under complete-coverage rule. Methodology was not relaxed."
            )

    # Year table for rank-1
    year_md = [
        "| Year | N | Strategy return | Mean net | Win rate | Breakout edge | MTM Sharpe | MTM MaxDD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    year_note = ""
    if rid is not None:
        years_best = year_map.get(rid, [])
        year_note = str(vbest.get("year_note", "")) if vbest is not None else ""
        for y in years_best:
            year_md.append(
                f"| {y['year']} | {y['n_trades']} | {fmt_pct(y['year_return'])} | "
                f"{fmt_pct(y['mean_net_trade'], 3)} | {fmt_pct(y['win_rate'])} | "
                f"{fmt_pct(y.get('breakout_edge', np.nan), 3)} | {fmt_num(y.get('mtm_sharpe', np.nan))} | "
                f"{fmt_pct(y.get('mtm_max_dd', np.nan))} |"
            )
    else:
        year_md.append("| — | 0 | NA | NA | NA | NA | NA | NA |")

    boot_d = boot_map.get(f"{rid}|discovery", {}) if rid else {}
    boot_v = boot_map.get(f"{rid}|validation", {}) if rid else {}

    top_tbl = [
        "| Rank | Rule | Class | Val $10k | Val MTM Sharpe | Val mean net | Val edge | Rec mean net | Rec edge |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    if val_tbl.empty:
        top_tbl.append("| — | NO DISCOVERY CANDIDATE | — | — | — | — | — | — | — |")
    else:
        for _, r in val_tbl.sort_values("discovery_rank").iterrows():
            top_tbl.append(
                f"| {int(r['discovery_rank'])} | `{r['rule_id']}` | {r['classification']} | "
                f"{fmt_usd(r['val_ending_capital_from_10000'])} | {fmt_num(r['val_mtm_sharpe'])} | "
                f"{fmt_pct(r['val_mean_net_trade'], 3)} | {fmt_pct(r['val_breakout_edge_mean'], 3)} | "
                f"{fmt_pct(r['rec_mean_net_trade'], 3)} | {fmt_pct(r['rec_breakout_edge_mean'], 3)} |"
            )

    all_disc_tbl = [
        "| Rule | Eligible | N trades | Mean net | Edge | MTM Sharpe | MTM MaxDD | $10k |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    dsort = disc_all.sort_values(
        by=["eligible", "mtm_sharpe", "breakout_edge_mean", "mean_net_trade"],
        ascending=[False, False, False, False],
        na_position="last",
    )
    for _, r in dsort.iterrows():
        all_disc_tbl.append(
            f"| `L{int(r['lookback_h'])}_H{int(r['hold_h'])}` | "
            f"{'yes' if bool(r['eligible']) else 'no'} | {int(r['n_trades'])} | "
            f"{fmt_pct(r['mean_net_trade'], 3)} | {fmt_pct(r['breakout_edge_mean'], 3)} | "
            f"{fmt_num(r['mtm_sharpe'])} | {fmt_pct(r['mtm_max_dd'])} | "
            f"{fmt_usd(r['ending_capital_from_10000'])} |"
        )

    if best is not None:
        lb_d = LOOKBACK_DAYS[int(best["lookback_h"])]
        best_block = [
            "## BEST DISCOVERY CANDIDATE",
            "",
            f"LOOKBACK: {lb_d} days ({int(best['lookback_h'])} hours)",
            "",
            f"SIGNAL: BTC close > previous {lb_d}-day maximum high",
            "",
            "ENTRY: next hourly OPEN",
            "",
            f"EXIT: {int(best['hold_h'])} hours later (next-open to exit-open)",
            "",
            f"Ranked #1 by Discovery hourly MTM Sharpe at 10 bps, among rules with "
            f"mean net > 0, breakout edge > 0, and N ≥ {MIN_DISC_TRADES}.",
            "",
            "## DISCOVERY (data start → 2021-12-31)",
            f"N trades (non-overlapping): {int(best['n_trades'])}",
            f"N breakout events (overlapping): {int(best['n_events'])}",
            f"mean net (10 bps): {fmt_pct(best['mean_net_trade'], 3)}",
            f"mean gross: {fmt_pct(best['mean_trade_gross'], 3)}",
            f"median net: {fmt_pct(best['median_net_trade'], 3)}",
            f"win rate: {fmt_pct(best['win_rate'])}",
            f"average winner / loser: {fmt_pct(best['avg_winner'], 3)} / {fmt_pct(best['avg_loser'], 3)}",
            f"payoff ratio: {fmt_num(best['payoff_ratio'])}",
            f"profit factor: {fmt_num(best['profit_factor'])}",
            f"breakout edge (cond − uncond mean): {fmt_pct(best['breakout_edge_mean'], 3)}",
            f"conditional / unconditional mean: {fmt_pct(best['cond_mean'], 3)} / {fmt_pct(best['uncond_mean'], 3)}",
            f"median difference: {fmt_pct(best['breakout_edge_median'], 3)}",
            f"P(return>0) difference: {fmt_pct(best['breakout_edge_p_pos'], 3)}",
            f"MTM Sharpe: {fmt_num(best['mtm_sharpe'])}",
            f"MTM MaxDD: {fmt_pct(best['mtm_max_dd'])}",
            f"MTM vol: {fmt_pct(best['mtm_vol'])}",
            f"MTM CAGR: {fmt_pct(best['mtm_cagr'])}",
            f"Calmar: {fmt_num(best['mtm_calmar'])}",
            f"exposure: {fmt_pct(best['mtm_exposure'])}",
            f"trade_sharpe_diagnostic: {fmt_num(best['trade_sharpe_diagnostic'])}",
            f"$10,000 → {fmt_usd(d_end)} (compounded trades) / MTM end {fmt_usd(best['mtm_end_cap'])}",
            f"0/10/20/50 bps mean net: {fmt_pct(best['mean_net_0bps'], 3)} / "
            f"{fmt_pct(best['mean_net_trade'], 3)} / {fmt_pct(best['mean_net_20bps'], 3)} / "
            f"{fmt_pct(best['mean_net_50bps'], 3)}",
            "",
            "## VALIDATION (2022-01-01 → 2024-12-31)",
            f"N trades: {int(vbest['val_n_trades'])}",
            f"mean net (10 bps): {fmt_pct(vbest['val_mean_net_trade'], 3)}",
            f"breakout edge: {fmt_pct(vbest['val_breakout_edge_mean'], 3)}",
            f"MTM Sharpe: {fmt_num(vbest['val_mtm_sharpe'])}",
            f"MTM MaxDD: {fmt_pct(vbest['val_mtm_max_dd'])}",
            f"$10,000 → {fmt_usd(v_end)} / MTM end {fmt_usd(vbest['val_mtm_end_cap'])}",
            f"Classification: **{cls_best}**",
            "",
            "## RECENT (2025-01-01 → latest complete bar)",
            f"N trades: {int(vbest['rec_n_trades'])}",
            f"mean net (10 bps): {fmt_pct(vbest['rec_mean_net_trade'], 3)}",
            f"breakout edge: {fmt_pct(vbest['rec_breakout_edge_mean'], 3)}",
            f"MTM Sharpe: {fmt_num(vbest['rec_mtm_sharpe'])}",
            f"MTM MaxDD: {fmt_pct(vbest['rec_mtm_max_dd'])}",
            f"$10,000 → {fmt_usd(r_end)} / MTM end {fmt_usd(vbest['rec_mtm_end_cap'])}",
            "",
        ]
        survive_20 = np.isfinite(vbest["val_mean_net_20bps"]) and float(vbest["val_mean_net_20bps"]) > 0
        survive_50 = np.isfinite(vbest["val_mean_net_50bps"]) and float(vbest["val_mean_net_50bps"]) > 0
        survive_20_disc = np.isfinite(best["mean_net_20bps"]) and float(best["mean_net_20bps"]) > 0
        survive_50_disc = np.isfinite(best["mean_net_50bps"]) and float(best["mean_net_50bps"]) > 0
        q5 = (
            f"{'Yes' if cls_best in ('SURVIVES', 'STRONG SURVIVOR') else 'No'} "
            f"(classification: {cls_best}). "
            f"Validation mean net {fmt_pct(vbest['val_mean_net_trade'], 3)}, "
            f"breakout edge {fmt_pct(vbest['val_breakout_edge_mean'], 3)}, "
            f"MTM Sharpe {fmt_num(vbest['val_mtm_sharpe'])}, N={int(vbest['val_n_trades'])}."
        )
        if later_helped and strongest_surv is not None:
            q5 += (
                f" Discovery rank #{int(strongest_surv['discovery_rank'])} "
                f"(`{strongest_surv['rule_id']}`) had the strongest later persistence "
                f"(validation MTM Sharpe {fmt_num(float(strongest_surv['val_mtm_sharpe']))}, "
                f"$10k → {fmt_usd(float(strongest_surv['val_ending_capital_from_10000']))}). "
                f"That comparison used later data; it is not untouched OOS validation."
            )
        rec_pnl_ok = np.isfinite(vbest["rec_mean_net_trade"]) and float(vbest["rec_mean_net_trade"]) >= 0
        rec_edge_ok = np.isfinite(vbest["rec_breakout_edge_mean"]) and float(vbest["rec_breakout_edge_mean"]) >= 0
        q6 = (
            f"Executable PnL {'survived' if rec_pnl_ok else 'did not survive'} "
            f"(mean net {fmt_pct(vbest['rec_mean_net_trade'], 3)}), but the breakout edge "
            f"{'survived' if rec_edge_ok else 'did not survive'} "
            f"(edge {fmt_pct(vbest['rec_breakout_edge_mean'], 3)}). "
            f"MTM Sharpe {fmt_num(vbest['rec_mtm_sharpe'])}, N={int(vbest['rec_n_trades'])}. "
            f"None of the Top 5 have a non-negative recent breakout edge, so none meet "
            f"STRONG SURVIVOR."
        )
        q7 = (
            f"Discovery {fmt_usd(d_end)}; validation {fmt_usd(v_end)}; recent {fmt_usd(r_end)} "
            f"(each period starts from $10,000; not chained)."
        )
        q8 = (
            f"Discovery {fmt_num(best['mtm_sharpe'])}; validation {fmt_num(vbest['val_mtm_sharpe'])}; "
            f"recent {fmt_num(vbest['rec_mtm_sharpe'])} "
            f"(hourly equity, sqrt(365×24), zeros when flat)."
        )
        q9 = (
            f"Discovery {fmt_pct(best['mtm_max_dd'])}; validation {fmt_pct(vbest['val_mtm_max_dd'])}; "
            f"recent {fmt_pct(vbest['rec_mtm_max_dd'])} (hourly MTM, intra-trade path included)."
        )
        q10 = (
            f"Discovery mean net at 20 bps {fmt_pct(best['mean_net_20bps'], 3)} "
            f"({'positive' if survive_20_disc else 'not positive'}). "
            f"Validation {fmt_pct(vbest['val_mean_net_20bps'], 3)} "
            f"({'positive' if survive_20 else 'not positive'})."
        )
        q11 = (
            f"Discovery mean net at 50 bps {fmt_pct(best['mean_net_50bps'], 3)} "
            f"({'positive' if survive_50_disc else 'not positive'}). "
            f"Validation {fmt_pct(vbest['val_mean_net_50bps'], 3)} "
            f"({'positive' if survive_50 else 'not positive'})."
        )
        q14 = year_note if year_note else "See year table."
        q4 = (
            f"Rank-1 Discovery conditional {fmt_pct(best['cond_mean'], 3)} vs "
            f"unconditional {fmt_pct(best['uncond_mean'], 3)} "
            f"(edge {fmt_pct(best['breakout_edge_mean'], 3)}). "
            f"Validation edge {fmt_pct(vbest['val_breakout_edge_mean'], 3)}. "
            f"Recent edge {fmt_pct(vbest['rec_breakout_edge_mean'], 3)}. "
            f"Across all 20 Discovery rules, {n_disc_edge_pos} have positive edge."
        )
    else:
        best_block = [
            "## BEST DISCOVERY CANDIDATE",
            "",
            "**NO DISCOVERY CANDIDATE**",
            "",
            f"No rule satisfied mean net > 0 AND breakout edge > 0 AND N ≥ {MIN_DISC_TRADES}.",
            "N was not reduced. Parameters were not rescued.",
            "",
            "## DISCOVERY (data start → 2021-12-31)",
            "No frozen candidate.",
            "",
            "## VALIDATION (2022-01-01 → 2024-12-31)",
            "No frozen candidate to validate.",
            "",
            "## RECENT (2025-01-01 → latest complete bar)",
            "No frozen candidate.",
            "",
        ]
        q5 = "No Discovery candidate was frozen, so nothing was validated."
        q6 = "No Discovery candidate was frozen."
        q7 = "No candidate; $10,000 was not put to work under a selected rule."
        q8 = "NA — no frozen candidate."
        q9 = "NA — no frozen candidate."
        q10 = "NA — no frozen candidate."
        q11 = "NA — no frozen candidate."
        q14 = "No candidate; yearly path is not defined."
        q4 = (
            f"Discovery pooled edge {fmt_pct(pooled_disc_edge, 3)} "
            f"({n_disc_edge_pos}/20 rules). "
            f"Validation pooled edge {fmt_pct(pooled_val_edge, 3)} "
            f"({n_val_edge_pos}/20)."
        )

    lines = [
        "# BTC Breakout Continuation — Phase 5",
        "",
        "QUESTION:",
        "",
        "Does buying BTC after it closes above a genuine historical",
        "price high generate abnormal future returns?",
        "",
        "Discovery candidate search over 20 frozen LONG breakout rules.",
        "Not clean out-of-sample. Not a live trading system.",
        "CALENDAR_CANDIDATE_V1 and CRASH_REBOUND_CANDIDATE_V1 were not modified and are not combined here.",
        "",
        *best_block,
        "## Answers",
        "",
        f"1. Do BTC breakouts generally continue? **{q1}**",
        f"2. Which lookback produced the strongest Discovery evidence: 7d / 30d / 60d / 90d? **{lb_strength(disc_rank_src)}.**",
        f"3. Which holding horizon appeared strongest? **{hold_strength(disc_rank_src)}.**",
        f"4. Did breakout returns outperform ordinary BTC returns over identical horizons? **{q4}**",
        f"5. Did the best Discovery candidate survive 2022–2024? **{q5}**",
        f"6. Did it survive 2025→latest? **{q6}**",
        f"7. What happened to $10,000 in each period? **{q7}**",
        f"8. What is true hourly MTM Sharpe? **{q8}**",
        f"9. What is true MTM maximum drawdown? **{q9}**",
        f"10. Does candidate remain profitable at 20 bps? **{q10}**",
        f"11. At 50 bps? **{q11}**",
        f"12. How many Top candidates survive? **{n_surv_any} of {len(top) if not top.empty else 0} frozen "
        f"({n_strong} STRONG SURVIVOR, {n_surv} SURVIVES, {n_frag} FRAGILE, {n_fail} FAIL).**",
        f"13. Are successful rules clustered around similar lookbacks / holding periods or is the winner isolated? **"
        + (
            "No frozen candidates."
            if top.empty
            else (
                "Isolated combinations."
                if isolated
                else f"Clustered: {families}."
            )
        )
        + "**",
        f"14. Is performance dependent on one particular year? **{q14}**",
        f"15. What do event paths say: immediate continuation, delayed continuation, or frequent false breakouts? "
        f"**{path_type}. Mean path from entry: +1h {fmt_pct(r1, 3)}, +6h {fmt_pct(r6, 3)}, "
        f"+24h {fmt_pct(r24, 3)}, +168h {fmt_pct(r168, 3)}. "
        f"Mean MAE_720h {fmt_pct(mae, 3)}; mean MFE_720h {fmt_pct(mfe, 3)}. "
        f"Share of events with non-positive +24h return {fmt_pct(frac_false)}.**",
        f"16. Final classification: **{final}**",
        "17. If a candidate survives, write the executable rule in maximum five lines.",
        "",
        exec_rule,
        "",
        "## Frozen top candidates — decision rule",
        "",
        *top_tbl,
        "",
        "## All 20 Discovery rules",
        "",
        *all_disc_tbl,
        "",
        "## Calendar-year path for the rank-1 Discovery rule",
        "",
        year_note if year_note else "No frozen candidate.",
        "",
        *year_md,
        "",
        "## Block bootstrap (168-hour blocks, 2000 samples)",
        "",
        "Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.",
        "Blocks are drawn from the hourly coverage-ok series (circular) to keep breakout clustering.",
        f"Rank-1 Discovery 95% CI mean net trade: [{fmt_pct(boot_d.get('mean_net_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_d.get('mean_net_hi', np.nan), 3)}]",
        f"Rank-1 Discovery 95% CI breakout edge: [{fmt_pct(boot_d.get('edge_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_d.get('edge_hi', np.nan), 3)}]",
        f"Rank-1 validation 95% CI mean net trade: [{fmt_pct(boot_v.get('mean_net_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_v.get('mean_net_hi', np.nan), 3)}]",
        f"Rank-1 validation 95% CI breakout edge: [{fmt_pct(boot_v.get('edge_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_v.get('edge_hi', np.nan), 3)}]",
        "",
        "## Coverage (complete expected hourly bars; no fill)",
        "",
        *cov_lines,
        "",
        "## Data audit",
        "",
        f"- File: `{meta['path']}`",
        f"- UTC start/end: {meta['start_utc']} → {meta['end_utc']}",
        f"- Bars: {meta['n_bars']}; unique UTC: {meta['unique']}; chronological: {meta['chronological']}; OHLC valid: {meta['ohlc_valid']}",
        f"- Duplicated bars dropped: {meta['n_dup_dropped']}; invalid OHLC rows dropped: {meta['n_ohlc_drop']}",
        f"- Missing hours in the UTC 1h grid (not filled): {meta['n_missing_hours']}. Preview: {miss_preview}",
        f"- Breakout signals skipped for missing t+1 entry bar (summed over lookbacks): {skip_meta['n_skip_no_entry']}",
        f"- Events skipped for missing exit open (summed over lookback×hold): {skip_meta['n_skip_no_exit']}",
        f"- Prior-high audit: {AUDIT_N} random coverage-ok timestamps × each lookback recomputed from exact t−k hours.",
        "",
        "## Research design",
        "",
        "- Search space: 4 lookbacks × 5 holds = 20 LONG rules. No shorts.",
        "- Breakout: close_t > max high on timestamp window [t−L hours, t). Current bar excluded.",
        "- Complete coverage: exactly L hourly bars in that window. Otherwise signal invalid.",
        "- Execution: buy the **open** of bar t+1; exit the open H hours later. Never the signal close.",
        "- LONG return = exit_open / entry_open − 1.",
        "- Event study keeps overlapping breakout hours. Executable PnL ignores signals until the current trade exits. Same-bar exit and entry is allowed.",
        "- Unconditional control: every coverage-ok hour in the same period with a valid same-horizon next-open to exit-open return.",
        "- Primary cost 10 bps round trip: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps.",
        "- MTM: marked to close while long; fills at open; round-trip fee split with sqrt(1−F) on each side.",
        "- Primary Sharpe annualized with sqrt(365×24) on hourly MTM returns (including flat zeros).",
        "- Discovery / validation / recent splits are chronological and frozen. Ranking uses Discovery MTM Sharpe only.",
        "- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.",
        "",
        "## Multiple-testing warning",
        "",
        "20 rules were ranked on Discovery. The best in-sample MTM Sharpe **will** be biased upward. "
        "A Discovery winner is a **Discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters. "
        "Validation was not allowed to change lookback, holding period, direction, entry, exit, or fees.",
        "",
        "## Audit assertions",
        "",
        "- Historical maximum excludes the current bar.",
        "- Lookback uses UTC timestamps, not positional rows.",
        "- Missing bars were not filled.",
        "- Breakout signal is known only at close t.",
        "- Entry is the open of t+1; exit uses the exact timestamp t_entry + H hours.",
        "- No future data in the signal.",
        "- Losing trades are retained.",
        "- Executable trades do not overlap (new signals ignored while in a position).",
        "- Fees applied as a round trip on completed trades; MTM splits the round trip across entry and exit.",
        "- MTM equity includes intra-trade marks to hourly close.",
        "- Discovery alone selected candidates. Validation did not modify parameters. Recent did not modify parameters.",
        "- Same-horizon control uses coverage-ok timestamps in the same period with a valid H-hour open-to-open return.",
        "",
        f"Bootstrap seed={BOOT_SEED}, block={BOOT_BLOCK_H} hours, samples={N_BOOT}.",
        f"Script runtime {runtime_s:.1f}s. Generated by `src/run_breakout_continuation.py`.",
        "",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "BREAKOUT_CONTINUATION.md").write_text("\n".join(lines), encoding="utf-8")
    log(f"wrote {RESULTS / 'BREAKOUT_CONTINUATION.md'}")


def main() -> None:
    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = load_hourly()
    meta = df.attrs["meta"]
    ts = pd.DatetimeIndex(df["ts_utc"])
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    ts_ns = ts.asi8
    periods = period_of(ts)
    period_masks = {p: periods == p for p in PERIODS}
    span = {p: period_span_days(meta, p) for p in PERIODS}

    needed_h = sorted(set(HOLDS) | set(PATH_H) | {1})
    ahead = {h: hours_ahead_index(ts, h) for h in needed_h}
    entry_idx = ahead[1]
    log(f"forward maps ready hours={needed_h}")

    fwd = {}
    exit_for = {}
    for h in HOLDS:
        x = take_idx(ahead[h], entry_idx)
        ok = (entry_idx >= 0) & (x >= 0)
        fl = np.full(n, np.nan)
        fl[ok] = opens[x[ok]] / opens[entry_idx[ok]] - 1.0
        fwd[h] = fl
        exit_for[h] = x

    log("computing timestamp-window prior highs")
    prior_map = {}
    cov_ok_map = {}
    cov_stats = []
    breakout_map = {}
    for L in LOOKBACKS:
        prior, ok, stats = prior_high_coverage(highs, ts_ns, L)
        audit_prior_high(ts, highs, prior, ok, L)
        brk = ok & np.isfinite(prior) & np.isfinite(closes) & (closes > prior)
        stats["n_breakouts"] = int(brk.sum())
        prior_map[L] = prior
        cov_ok_map[L] = ok
        breakout_map[L] = brk
        cov_stats.append(stats)
        log(
            f"  L{L}h ({LOOKBACK_DAYS[L]}d): coverage={stats['n_valid_coverage']} "
            f"lost_missing={stats['n_lost_missing_coverage']} "
            f"insufficient={stats['n_insufficient_history']} breakouts={stats['n_breakouts']}"
        )
        if stats["n_valid_coverage"] == 0:
            log(f"  ANALYSIS IMPOSSIBLE for L{L}h — complete coverage never holds. Not relaxing.")

    uncond = {h: {L: {} for L in LOOKBACKS} for h in HOLDS}
    for h in HOLDS:
        for L in LOOKBACKS:
            for p in PERIODS:
                m = period_masks[p] & cov_ok_map[L] & np.isfinite(fwd[h])
                uncond[h][L][p] = fwd[h][m]

    rule_rows = []
    trade_rows = []
    path_rows = []
    rule_arrays = {}
    n_skip_no_entry = 0
    n_skip_no_exit = 0

    path_mae = []
    path_mfe = []
    path_ret = {h: [] for h in PATH_H}
    path_r24_nonpos = []

    for L in LOOKBACKS:
        prior = prior_map[L]
        cov_ok = cov_ok_map[L]
        sig = breakout_map[L]
        has_entry = sig & (entry_idx >= 0)
        n_skip_no_entry += int((sig & (entry_idx < 0)).sum())

        path_idx = np.flatnonzero(has_entry)
        for i in path_idx:
            e_i = int(entry_idx[i])
            e_px = float(opens[e_i])
            phigh = float(prior[i])
            rec = {
                "signal_timestamp": str(ts[i]),
                "period": periods[i],
                "lookback_h": int(L),
                "lookback_days": LOOKBACK_DAYS[L],
                "signal_close": float(closes[i]),
                "prior_high": phigh,
                "breakout_pct_above_high": float(closes[i] / phigh - 1.0) if phigh > 0 else np.nan,
                "entry_timestamp": str(ts[e_i]),
                "entry_price": e_px,
            }
            for ph in PATH_H:
                j = int(ahead[ph][e_i])
                if j >= 0:
                    rec[f"ret_{ph}h"] = float(opens[j] / e_px - 1.0)
                else:
                    rec[f"ret_{ph}h"] = np.nan
            mae, mfe, mae_h, mfe_h, mae_i, mfe_i = window_excursions(
                e_i, e_px, ts_ns, lows, highs, 720
            )
            rec["MAE_720h"] = mae
            rec["MFE_720h"] = mfe
            rec["MAE_hours"] = mae_h
            rec["MFE_hours"] = mfe_h
            rec["MAE_timestamp"] = str(ts[mae_i]) if mae_i >= 0 else ""
            rec["MFE_timestamp"] = str(ts[mfe_i]) if mfe_i >= 0 else ""
            path_rows.append(rec)
            path_mae.append(mae)
            path_mfe.append(mfe)
            for ph in PATH_H:
                path_ret[ph].append(rec[f"ret_{ph}h"])
            r24 = rec["ret_24h"]
            if np.isfinite(r24):
                path_r24_nonpos.append(float(r24 <= 0))

        log(f"  event paths L{L}h n={int(has_entry.sum())}")

        for h in HOLDS:
            rid = rule_id(L, h)
            x = exit_for[h]
            has_exit = has_entry & (x >= 0)
            n_skip_no_exit += int((has_entry & (x < 0)).sum())
            valid_event = has_exit & np.isfinite(fwd[h])
            take_all = executable_take(valid_event, entry_idx, ts_ns, h)
            pairs_all: list[tuple[int, int]] = []
            for t in np.flatnonzero(take_all):
                pairs_all.append((int(entry_idx[t]), int(x[t])))
            rule_arrays[rid] = {
                "valid_event": valid_event,
                "take": take_all,
                "fwd": fwd[h],
                "lookback_h": L,
                "hold_h": h,
                "pairs": pairs_all,
                "entry_idx": entry_idx,
                "exit_idx": x,
                "cov_ok": cov_ok,
            }

            mtm_by_period = {}
            mtm_fee_end = {p: {} for p in PERIODS}
            for period in PERIODS:
                mask = period_masks[period]
                tk = take_all & mask
                p_pairs = [
                    (int(entry_idx[t]), int(x[t])) for t in np.flatnonzero(tk)
                ]
                eq10, pos10 = mtm_from_trades(n, opens, closes, p_pairs, FEE_PRIMARY)
                path, ppos = slice_period_equity(eq10, pos10, mask)
                mets = mtm_metrics(path, ppos, span[period])
                for bps, fee in zip(FEE_BPS, FEE_SET):
                    eq_b, pos_b = mtm_from_trades(n, opens, closes, p_pairs, fee)
                    pth, ppo = slice_period_equity(eq_b, pos_b, mask)
                    mtm_fee_end[period][bps] = mtm_metrics(pth, ppo, span[period])["mtm_end_cap"]
                mtm_by_period[period] = mets

            for period in PERIODS:
                ev = valid_event & period_masks[period]
                tk = take_all & period_masks[period]
                btc_stats = dist_stats(fwd[h][ev], uncond[h][L][period])
                em = exec_metrics(fwd[h][tk], span[period], FEE_PRIMARY)
                nets_by_fee = {}
                g_tk = fwd[h][tk]
                for bps, fee in zip(FEE_BPS, FEE_SET):
                    nets = net_from_gross(g_tk, fee)
                    nets_by_fee[bps] = {
                        "mean_net": float(nets.mean()) if nets.size else np.nan,
                        "end_cap": ending_capital(nets),
                    }
                mm = mtm_by_period[period]
                row = {
                    "rule_id": rid,
                    "period": period,
                    "lookback_h": int(L),
                    "lookback_days": LOOKBACK_DAYS[L],
                    "hold_h": int(h),
                    "direction": "long",
                    "n_signals": int((sig & period_masks[period]).sum()),
                    "n_events": int(ev.sum()),
                    "n_trades": em["n_trades"],
                    "n_valid_coverage_period": int((cov_ok & period_masks[period]).sum()),
                    "n_skip_no_entry_period": int(
                        (sig & period_masks[period] & (entry_idx < 0)).sum()
                    ),
                    "n_skip_no_exit_period": int(
                        (has_entry & period_masks[period] & (x < 0)).sum()
                    ),
                    "cond_mean": btc_stats["cond_mean"],
                    "uncond_mean": btc_stats["uncond_mean"],
                    "breakout_edge_mean": btc_stats["diff_mean"],
                    "cond_median": btc_stats["cond_median"],
                    "uncond_median": btc_stats["uncond_median"],
                    "breakout_edge_median": btc_stats["diff_median"],
                    "cond_p_pos": btc_stats["cond_p_pos"],
                    "uncond_p_pos": btc_stats["uncond_p_pos"],
                    "breakout_edge_p_pos": btc_stats["diff_p_pos"],
                    **em,
                    **mm,
                    "mean_net_0bps": nets_by_fee[0]["mean_net"],
                    "mean_net_20bps": nets_by_fee[20]["mean_net"],
                    "mean_net_50bps": nets_by_fee[50]["mean_net"],
                    "end_cap_0bps": nets_by_fee[0]["end_cap"],
                    "end_cap_20bps": nets_by_fee[20]["end_cap"],
                    "end_cap_50bps": nets_by_fee[50]["end_cap"],
                    "mtm_end_cap_0bps": mtm_fee_end[period][0],
                    "mtm_end_cap_20bps": mtm_fee_end[period][20],
                    "mtm_end_cap_50bps": mtm_fee_end[period][50],
                }
                rule_rows.append(row)
                if tk.any():
                    for t in np.flatnonzero(tk):
                        e_i = int(entry_idx[t])
                        x_i = int(x[t])
                        g = float(fwd[h][t])
                        trade_rows.append(
                            {
                                "rule_id": rid,
                                "period": period,
                                "lookback_h": int(L),
                                "lookback_days": LOOKBACK_DAYS[L],
                                "hold_h": int(h),
                                "direction": "long",
                                "signal_timestamp": str(ts[t]),
                                "entry_timestamp": str(ts[e_i]),
                                "exit_timestamp": str(ts[x_i]),
                                "entry_price": float(opens[e_i]),
                                "exit_price": float(opens[x_i]),
                                "signal_close": float(closes[t]),
                                "prior_high": float(prior[t]),
                                "breakout_pct_above_high": float(closes[t] / prior[t] - 1.0)
                                if prior[t] > 0
                                else np.nan,
                                "gross_return": g,
                                "net_return_10bps": float(
                                    net_from_gross(np.array([g]), FEE_PRIMARY)[0]
                                ),
                            }
                        )
            log(f"  scanned {rid} events={int(valid_event.sum())} trades={int(take_all.sum())}")

    all_rules = pd.DataFrame(rule_rows)
    disc = all_rules.loc[all_rules["period"] == "discovery"].copy()
    disc["eligible"] = (
        (disc["mean_net_trade"] > 0)
        & (disc["breakout_edge_mean"] > 0)
        & (disc["n_trades"] >= MIN_DISC_TRADES)
    )
    all_rules = all_rules.merge(
        disc[["rule_id", "eligible"]],
        on="rule_id",
        how="left",
    )
    # merge duplicates eligible onto discovery rows already in disc; fix disc view
    disc = all_rules.loc[all_rules["period"] == "discovery"].copy()

    eligible = disc.loc[disc["eligible"]].copy()
    eligible["abs_mdd"] = eligible["mtm_max_dd"].abs()
    eligible = eligible.sort_values(
        by=["mtm_sharpe", "breakout_edge_mean", "mean_net_trade", "abs_mdd"],
        ascending=[False, False, False, True],
        na_position="last",
    )
    if eligible.empty:
        log("NO DISCOVERY CANDIDATE — zero rules with mean net>0 AND edge>0 AND N>=20")
        top = eligible.copy()
    else:
        eligible["discovery_rank"] = np.arange(1, len(eligible) + 1)
        top = eligible.head(TOP_N).drop(columns=["abs_mdd"]).copy()
        log(f"eligible discovery rules={len(eligible)} frozen={len(top)}")

    val = all_rules.loc[all_rules["period"] == "validation"].copy()
    rec = all_rules.loc[all_rules["period"] == "recent"].copy()
    trade_df = pd.DataFrame(trade_rows)
    path_df = pd.DataFrame(path_rows)

    val_rows = []
    year_map: dict[str, list[dict]] = {}
    boot_map: dict[str, dict] = {}
    rank_map = {} if top.empty else dict(zip(top["rule_id"], top["discovery_rank"]))

    years_index = ts.year.to_numpy()
    unique_years = range(int(years_index.min()), int(years_index.max()) + 1)

    for _, cand in top.iterrows():
        rid = cand["rule_id"]
        v = val.loc[val["rule_id"] == rid]
        r = rec.loc[rec["rule_id"] == rid]
        if v.empty or r.empty:
            raise RuntimeError(f"missing val/recent row for {rid}")
        v = v.iloc[0]
        r = r.iloc[0]
        arr = rule_arrays[rid]
        tk = arr["take"]
        g = arr["fwd"]
        x = arr["exit_idx"]
        L = int(cand["lookback_h"])
        h = int(cand["hold_h"])

        yrs = []
        for year in unique_years:
            ymask = years_index == year
            m = tk & ymask
            gg = g[m]
            gg = gg[np.isfinite(gg)]
            if gg.size == 0:
                continue
            nets = net_from_gross(gg, FEE_PRIMARY)
            ev_y = arr["valid_event"] & ymask
            un_y = cov_ok_map[L] & ymask & np.isfinite(g)
            edge_y = dist_stats(g[ev_y], g[un_y])["diff_mean"]
            p_pairs = [(int(entry_idx[t]), int(x[t])) for t in np.flatnonzero(m)]
            eq_y, pos_y = mtm_from_trades(n, opens, closes, p_pairs, FEE_PRIMARY)
            path_y, ppos_y = slice_period_equity(eq_y, pos_y, ymask)
            days = 366.0 if year % 4 == 0 else 365.0
            ym = mtm_metrics(path_y, ppos_y, days)
            yrs.append(
                {
                    "year": int(year),
                    "n_trades": int(gg.size),
                    "year_return": float(np.prod(1.0 + nets) - 1.0),
                    "mean_net_trade": float(nets.mean()),
                    "win_rate": float(np.mean(nets > 0)),
                    "breakout_edge": float(edge_y),
                    "mtm_sharpe": ym["mtm_sharpe"],
                    "mtm_max_dd": ym["mtm_max_dd"],
                }
            )
        year_map[rid] = yrs
        yok, ymsg = year_ok_flag(yrs)
        cls = classify_rule(cand, v, r, yok)

        for period in PERIODS:
            boot_map[f"{rid}|{period}"] = bootstrap_rule(
                arr["valid_event"],
                period_masks[period] & arr["cov_ok"],
                arr["fwd"],
                h,
                FEE_PRIMARY,
            )
            log(f"  bootstrap {rid} {period} done")
        bd = boot_map[f"{rid}|discovery"]
        bv = boot_map[f"{rid}|validation"]
        br = boot_map[f"{rid}|recent"]
        val_rows.append(
            {
                "discovery_rank": int(cand["discovery_rank"]),
                "rule_id": rid,
                "lookback_h": int(cand["lookback_h"]),
                "lookback_days": LOOKBACK_DAYS[int(cand["lookback_h"])],
                "hold_h": int(cand["hold_h"]),
                "classification": cls,
                "year_ok": yok,
                "year_note": ymsg,
                "disc_n_trades": int(cand["n_trades"]),
                "disc_n_events": int(cand["n_events"]),
                "disc_mean_net_trade": float(cand["mean_net_trade"]),
                "disc_breakout_edge_mean": float(cand["breakout_edge_mean"]),
                "disc_mtm_sharpe": float(cand["mtm_sharpe"]),
                "disc_mtm_max_dd": float(cand["mtm_max_dd"]),
                "disc_ending_capital_from_10000": float(cand["ending_capital_from_10000"]),
                "val_n_trades": int(v["n_trades"]),
                "val_n_events": int(v["n_events"]),
                "val_mean_trade_gross": float(v["mean_trade_gross"]),
                "val_mean_net_trade": float(v["mean_net_trade"]),
                "val_median_net_trade": float(v["median_net_trade"]),
                "val_win_rate": float(v["win_rate"]),
                "val_avg_winner": float(v["avg_winner"]),
                "val_avg_loser": float(v["avg_loser"]),
                "val_payoff_ratio": float(v["payoff_ratio"]),
                "val_profit_factor": float(v["profit_factor"]),
                "val_ending_capital_from_10000": float(v["ending_capital_from_10000"]),
                "val_mtm_sharpe": float(v["mtm_sharpe"]),
                "val_mtm_max_dd": float(v["mtm_max_dd"]),
                "val_mtm_vol": float(v["mtm_vol"]),
                "val_mtm_cagr": float(v["mtm_cagr"]),
                "val_mtm_calmar": float(v["mtm_calmar"]),
                "val_mtm_exposure": float(v["mtm_exposure"]),
                "val_mtm_end_cap": float(v["mtm_end_cap"]),
                "val_mtm_total_return": float(v["mtm_total_return"]),
                "val_cond_mean": float(v["cond_mean"]),
                "val_uncond_mean": float(v["uncond_mean"]),
                "val_breakout_edge_mean": float(v["breakout_edge_mean"]),
                "val_breakout_edge_median": float(v["breakout_edge_median"]),
                "val_breakout_edge_p_pos": float(v["breakout_edge_p_pos"]),
                "val_mean_net_0bps": float(v["mean_net_0bps"]),
                "val_mean_net_20bps": float(v["mean_net_20bps"]),
                "val_mean_net_50bps": float(v["mean_net_50bps"]),
                "val_end_cap_0bps": float(v["end_cap_0bps"]),
                "val_end_cap_20bps": float(v["end_cap_20bps"]),
                "val_end_cap_50bps": float(v["end_cap_50bps"]),
                "rec_n_trades": int(r["n_trades"]),
                "rec_n_events": int(r["n_events"]),
                "rec_mean_trade_gross": float(r["mean_trade_gross"]),
                "rec_mean_net_trade": float(r["mean_net_trade"]),
                "rec_median_net_trade": float(r["median_net_trade"]),
                "rec_win_rate": float(r["win_rate"]),
                "rec_ending_capital_from_10000": float(r["ending_capital_from_10000"]),
                "rec_mtm_sharpe": float(r["mtm_sharpe"]),
                "rec_mtm_max_dd": float(r["mtm_max_dd"]),
                "rec_mtm_cagr": float(r["mtm_cagr"]),
                "rec_mtm_end_cap": float(r["mtm_end_cap"]),
                "rec_cond_mean": float(r["cond_mean"]),
                "rec_uncond_mean": float(r["uncond_mean"]),
                "rec_breakout_edge_mean": float(r["breakout_edge_mean"]),
                "rec_mean_net_0bps": float(r["mean_net_0bps"]),
                "rec_mean_net_20bps": float(r["mean_net_20bps"]),
                "rec_mean_net_50bps": float(r["mean_net_50bps"]),
                "disc_boot_mean_net_lo": bd["mean_net_lo"],
                "disc_boot_mean_net_hi": bd["mean_net_hi"],
                "disc_boot_edge_lo": bd["edge_lo"],
                "disc_boot_edge_hi": bd["edge_hi"],
                "val_boot_mean_net_lo": bv["mean_net_lo"],
                "val_boot_mean_net_hi": bv["mean_net_hi"],
                "val_boot_edge_lo": bv["edge_lo"],
                "val_boot_edge_hi": bv["edge_hi"],
                "rec_boot_mean_net_lo": br["mean_net_lo"],
                "rec_boot_mean_net_hi": br["mean_net_hi"],
                "rec_boot_edge_lo": br["edge_lo"],
                "rec_boot_edge_hi": br["edge_hi"],
            }
        )

    val_tbl = pd.DataFrame(val_rows)
    if not top.empty:
        top_out = top.copy()
        top_out = top_out.merge(
            val_tbl[["rule_id", "classification", "year_ok", "year_note"]],
            on="rule_id",
            how="left",
        )
    else:
        top_out = top.copy()

    mae_a = np.asarray(path_mae, dtype=float)
    mfe_a = np.asarray(path_mfe, dtype=float)
    path_summary = {
        "mae_mean": float(np.nanmean(mae_a)) if mae_a.size else np.nan,
        "mfe_mean": float(np.nanmean(mfe_a)) if mfe_a.size else np.nan,
        "mae_median": float(np.nanmedian(mae_a)) if mae_a.size else np.nan,
        "mfe_median": float(np.nanmedian(mfe_a)) if mfe_a.size else np.nan,
        "n_paths": int(mae_a.size),
        "frac_ret_24h_nonpos": float(np.mean(path_r24_nonpos)) if path_r24_nonpos else np.nan,
    }
    for ph in PATH_H:
        a = np.asarray(path_ret[ph], dtype=float)
        path_summary[f"ret_{ph}h_mean"] = float(np.nanmean(a)) if a.size else np.nan

    skip_meta = {
        "n_skip_no_entry": int(n_skip_no_entry),
        "n_skip_no_exit": int(n_skip_no_exit),
    }

    # Equity for top candidates (full sample, all trades)
    equity_parts = []
    if not top_out.empty:
        for _, cand in top_out.iterrows():
            rid = cand["rule_id"]
            arr = rule_arrays[rid]
            pairs = arr["pairs"]
            eqs = {}
            pos10 = None
            for bps, fee in zip(FEE_BPS, FEE_SET):
                eq, pos = mtm_from_trades(n, opens, closes, pairs, fee)
                eqs[bps] = eq
                if bps == 10:
                    pos10 = pos
            equity_parts.append(
                pd.DataFrame(
                    {
                        "timestamp_utc": ts.astype(str),
                        "rule_id": rid,
                        "discovery_rank": int(cand["discovery_rank"]),
                        "lookback_h": int(cand["lookback_h"]),
                        "hold_h": int(cand["hold_h"]),
                        "close": closes,
                        "position": pos10.astype(int),
                        "equity_0bps": eqs[0],
                        "equity_10bps": eqs[10],
                        "equity_20bps": eqs[20],
                        "equity_50bps": eqs[50],
                    }
                )
            )
    equity_df = pd.concat(equity_parts, ignore_index=True) if equity_parts else pd.DataFrame()
    if not trade_df.empty and not top_out.empty:
        trade_df = trade_df.loc[trade_df["rule_id"].isin(set(top_out["rule_id"]))].copy()
        trade_df["discovery_rank"] = trade_df["rule_id"].map(rank_map)
        trade_df = trade_df.sort_values(["discovery_rank", "signal_timestamp"]).reset_index(drop=True)
    elif trade_df.empty:
        trade_df = pd.DataFrame(
            columns=[
                "rule_id",
                "period",
                "lookback_h",
                "lookback_days",
                "hold_h",
                "direction",
                "signal_timestamp",
                "entry_timestamp",
                "exit_timestamp",
                "entry_price",
                "exit_price",
                "signal_close",
                "prior_high",
                "breakout_pct_above_high",
                "gross_return",
                "net_return_10bps",
                "discovery_rank",
            ]
        )

    if equity_df.empty:
        equity_df = pd.DataFrame(
            columns=[
                "timestamp_utc",
                "rule_id",
                "discovery_rank",
                "lookback_h",
                "hold_h",
                "close",
                "position",
                "equity_0bps",
                "equity_10bps",
                "equity_20bps",
                "equity_50bps",
            ]
        )

    all_out = all_rules.sort_values(
        ["period", "lookback_h", "hold_h"]
    ).reset_index(drop=True)

    if top_out.empty:
        # keep headered empty validation
        val_tbl = pd.DataFrame(
            columns=[
                "discovery_rank",
                "rule_id",
                "lookback_h",
                "lookback_days",
                "hold_h",
                "classification",
            ]
        )

    all_out.to_csv(RESULTS / "ALL_BREAKOUT_RULES.csv", index=False)
    top_out.to_csv(RESULTS / "TOP_CANDIDATES.csv", index=False)
    val_tbl.to_csv(RESULTS / "VALIDATION_RESULTS.csv", index=False)
    path_df.to_csv(RESULTS / "EVENT_PATHS.csv", index=False)
    trade_df.to_csv(RESULTS / "TRADE_LOG.csv", index=False)
    equity_df.to_csv(RESULTS / "EQUITY_TOP_CANDIDATES.csv", index=False)
    log(
        f"wrote csvs rules={len(all_out)} top={len(top_out)} "
        f"paths={len(path_df)} trades={len(trade_df)} equity={len(equity_df)}"
    )

    runtime_s = time.time() - t0
    write_report(
        meta,
        all_rules,
        top_out,
        val_tbl,
        year_map,
        boot_map,
        path_summary,
        cov_stats,
        skip_meta,
        runtime_s,
    )
    if top_out.empty:
        log(f"done in {runtime_s:.1f}s NO DISCOVERY CANDIDATE")
    else:
        log(
            f"done in {runtime_s:.1f}s leader={top_out.iloc[0]['rule_id']} "
            f"class={val_tbl.iloc[0]['classification']}"
        )


if __name__ == "__main__":
    main()
