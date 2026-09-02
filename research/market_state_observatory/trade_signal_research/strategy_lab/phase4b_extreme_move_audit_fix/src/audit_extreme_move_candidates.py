#!/usr/bin/env python3
"""Phase 4b — audit/correction of frozen Phase 4 extreme-move rules.

Does not overwrite Phase 4 outputs. Does not reselect. Does not add
parameters. Not a live system. Not clean OOS.

Corrections:
1. Trailing returns use exact timestamps t and t−L hours (NaN if either
   bar is missing). No positional close[i]/close[i−L].
2. Primary Sharpe / MaxDD come from hourly mark-to-market equity.
3. Stricter STRONG SURVIVOR rule, including recent conditional advantage.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
PHASE4 = PHASE.parent / "phase4_extreme_move_reversal"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
H1_PATH = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"

CANDIDATE_ID = "L6_down_p1_rebound_long_H6"
START_CAP = 10_000.0
FEE_PRIMARY = 0.0010
FEE_SET = (0.0, 0.0010, 0.0020, 0.0050)
FEE_BPS = (0, 10, 20, 50)
LOOKBACKS = (6, 12, 24, 72)
DOWN_PCTS = (0.01, 0.025, 0.05)
UP_PCTS = (0.95, 0.975, 0.99)
HOLDS = (6, 12, 24, 48, 72, 168)
MIN_CAL_DAYS = 365
AUDIT_EXPANDING_N = 30
CRYPTO_DAYS = 365.0
HOURS_PER_YEAR = 365.0 * 24.0
HOUR_NS = 3_600_000_000_000

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


def pct_label(p: float) -> str:
    mapping = {
        0.01: "p1",
        0.025: "p2.5",
        0.05: "p5",
        0.95: "p95",
        0.975: "p97.5",
        0.99: "p99",
    }
    for k, v in mapping.items():
        if abs(p - k) < 1e-12:
            return v
    return f"p{p}"


def thesis_name(tail: str, direction: str) -> str:
    if tail == "down" and direction == "long":
        return "rebound"
    if tail == "down" and direction == "short":
        return "continuation"
    if tail == "up" and direction == "long":
        return "continuation"
    return "reversal"


def rule_id(lookback: int, tail: str, p: float, direction: str, hold: int) -> str:
    return (
        f"L{lookback}_{tail}_{pct_label(p)}_{thesis_name(tail, direction)}"
        f"_{direction}_H{hold}"
    )


def net_from_gross(gross: np.ndarray, fee: float) -> np.ndarray:
    g = np.asarray(gross, dtype=float)
    return (1.0 + g) * (1.0 - fee) - 1.0


def side_mult(fee: float) -> float:
    """Each side so (entry × exit) equals the requested round-trip factor."""
    if fee <= 0:
        return 1.0
    if fee >= 1:
        return 0.0
    return float(np.sqrt(1.0 - fee))


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


def hours_behind_index(ts: pd.DatetimeIndex, h: int) -> np.ndarray:
    mapper = pd.Series(np.arange(len(ts), dtype=np.int64), index=ts)
    loc = mapper.reindex(ts - pd.Timedelta(hours=h))
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


def exact_trailing_return(closes: np.ndarray, behind: np.ndarray) -> np.ndarray:
    n = len(closes)
    ret = np.full(n, np.nan, dtype=float)
    ok = behind >= 0
    prev = closes[behind[ok]]
    cur = closes[ok]
    good = (prev > 0) & (cur > 0)
    idx = np.flatnonzero(ok)
    ret[idx[good]] = cur[good] / prev[good] - 1.0
    return ret


def positional_trailing_return(closes: np.ndarray, lookback: int) -> np.ndarray:
    ret = np.full(len(closes), np.nan, dtype=float)
    if lookback <= 0 or lookback >= len(closes):
        return ret
    prev = closes[:-lookback]
    cur = closes[lookback:]
    good = (prev > 0) & (cur > 0)
    ret[lookback:][good] = cur[good] / prev[good] - 1.0
    return ret


class FenwickOS:
    def __init__(self, n: int):
        self.n = int(n)
        self.bit = np.zeros(self.n + 1, dtype=np.int64)
        self.max_pow = 1 << (self.n.bit_length() - 1) if self.n else 1

    def add(self, rank: int, delta: int = 1) -> None:
        i = int(rank) + 1
        bit = self.bit
        n = self.n
        while i <= n:
            bit[i] += delta
            i += i & -i

    def kth(self, k: int) -> int:
        idx = 0
        bit = self.max_pow
        tree = self.bit
        n = self.n
        k = int(k)
        while bit:
            t = idx + bit
            if t <= n and tree[t] < k:
                idx = t
                k -= int(tree[t])
            bit >>= 1
        return idx


def expanding_quantiles(ret: np.ndarray, ts: pd.DatetimeIndex, probs: tuple[float, ...]) -> dict[float, np.ndarray]:
    n = len(ret)
    out = {p: np.full(n, np.nan, dtype=float) for p in probs}
    valid = np.isfinite(ret)
    idx = np.flatnonzero(valid)
    m = int(idx.size)
    if m < 2:
        return out
    vals = ret[idx]
    order = np.argsort(vals, kind="mergesort")
    rank = np.empty(m, dtype=np.int64)
    rank[order] = np.arange(m, dtype=np.int64)
    sorted_vals = vals[order]
    first_ts = ts[int(idx[0])]
    min_ts = first_ts + pd.Timedelta(days=MIN_CAL_DAYS)
    min_i = int(ts.searchsorted(min_ts))
    bit = FenwickOS(m)
    inserted = 0
    j = 0
    for i in range(n):
        if inserted >= 2 and i >= min_i:
            n_ins = inserted
            for p in probs:
                h = (n_ins - 1) * p
                lo = int(np.floor(h))
                hi = int(np.ceil(h))
                vlo = float(sorted_vals[bit.kth(lo + 1)])
                if lo == hi:
                    out[p][i] = vlo
                else:
                    vhi = float(sorted_vals[bit.kth(hi + 1)])
                    out[p][i] = vlo + (h - lo) * (vhi - vlo)
        if valid[i]:
            bit.add(int(rank[j]), 1)
            inserted += 1
            j += 1
    return out


def audit_expanding(ret: np.ndarray, q: np.ndarray, p: float, n_check: int = AUDIT_EXPANDING_N) -> None:
    cand = np.flatnonzero(np.isfinite(q) & np.isfinite(ret))
    if cand.size == 0:
        raise RuntimeError(f"no expanding quantile observations for p={p}")
    rng = np.random.default_rng(0)
    pick = rng.choice(cand, size=min(n_check, int(cand.size)), replace=False)
    for i in pick:
        hist = ret[: int(i)]
        hist = hist[np.isfinite(hist)]
        if hist.size < 2:
            raise RuntimeError("expanding audit hit too-short history")
        ref = float(np.quantile(hist, p, method="linear"))
        got = float(q[int(i)])
        scale = max(1.0, abs(ref))
        if abs(ref - got) > 1e-10 * scale:
            raise RuntimeError(
                f"expanding percentile mismatch at t={i} p={p}: got={got} ref={ref}"
            )


def load_hourly() -> pd.DataFrame:
    if not H1_PATH.exists():
        raise RuntimeError(f"No local 1h BTCUSDT file at {H1_PATH}.")
    df = pd.read_csv(H1_PATH)
    df["ts_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["ts_utc", "open", "high", "low", "close"]).copy()
    df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="first")
    if not df["ts_utc"].is_monotonic_increasing or not df["ts_utc"].is_unique:
        raise RuntimeError("UTC timestamps are not unique/chronological.")
    ohlc_ok = bool(
        (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-12).all()
        and (df["low"] <= df[["open", "close"]].min(axis=1) + 1e-12).all()
        and (df["high"] >= df["low"]).all()
        and (df["open"] > 0).all()
        and (df["close"] > 0).all()
    )
    if not ohlc_ok:
        raise RuntimeError("OHLC validity check failed.")
    full = pd.date_range(df["ts_utc"].min(), df["ts_utc"].max(), freq="h", tz="UTC")
    missing = full.difference(pd.DatetimeIndex(df["ts_utc"]))
    meta = {
        "n_bars": int(len(df)),
        "n_missing_hours": int(len(missing)),
        "start_utc": df["ts_utc"].min(),
        "end_utc": df["ts_utc"].max(),
        "path": str(H1_PATH),
    }
    log(
        f"1h BTCUSDT {meta['start_utc']} → {meta['end_utc']} "
        f"bars={meta['n_bars']} missing_hours={meta['n_missing_hours']}"
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
        a, b = start, DISC_END
    elif period == "validation":
        a, b = DISC_END, VAL_END
    else:
        a, b = VAL_END, end + pd.Timedelta(hours=1)
    return max(float((b - a).total_seconds() / 86400.0), 1.0)


def dist_stats(cond: np.ndarray, uncond: np.ndarray) -> dict:
    c = np.asarray(cond, dtype=float)
    u = np.asarray(uncond, dtype=float)
    c = c[np.isfinite(c)]
    u = u[np.isfinite(u)]
    out = {
        "cond_mean": float(c.mean()) if c.size else np.nan,
        "uncond_mean": float(u.mean()) if u.size else np.nan,
        "n_cond": int(c.size),
        "n_uncond": int(u.size),
    }
    out["diff_mean"] = out["cond_mean"] - out["uncond_mean"]
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


def mtm_from_trades(
    n: int,
    opens: np.ndarray,
    closes: np.ndarray,
    trades: list[tuple[int, int]],
    direction: str,
    fee: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Hourly equity marked at close while in a trade; fills at open.

    Round-trip fee F is split so entry_mult * exit_mult = (1−F).
    """
    equity = np.full(n, START_CAP, dtype=float)
    position = np.zeros(n, dtype=np.int8)
    if not trades:
        return equity, position
    sm = side_mult(fee)
    sign = 1 if direction == "long" else -1
    cash = START_CAP
    shares = 0.0
    entry_px = np.nan
    in_pos = False
    pending_exit = -1
    entries = {int(e): int(x) for e, x in trades}
    for i in range(n):
        if in_pos and i == pending_exit:
            if direction == "long":
                gross_eq = shares * float(opens[i])
            else:
                gross_eq = shares * (entry_px / float(opens[i]))
            cash = gross_eq * sm
            shares = 0.0
            in_pos = False
            pending_exit = -1
            entry_px = np.nan
        if i in entries and not in_pos:
            cash = cash * sm
            entry_px = float(opens[i])
            if direction == "long":
                shares = cash / entry_px
            else:
                shares = cash
            cash = 0.0
            in_pos = True
            pending_exit = entries[i]
        if in_pos:
            position[i] = sign
            px = float(closes[i])
            if direction == "long":
                equity[i] = shares * px
            else:
                equity[i] = shares * (entry_px / px)
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
    calmar = float(cagr / abs(max_dd)) if np.isfinite(cagr) and np.isfinite(max_dd) and max_dd < 0 else np.nan
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


def trade_mae_mfe(
    entry_i: int,
    exit_i: int,
    entry_px: float,
    lows: np.ndarray,
    highs: np.ndarray,
    direction: str,
) -> tuple[float, float]:
    if exit_i <= entry_i:
        return np.nan, np.nan
    sl_low = lows[entry_i:exit_i]
    sl_high = highs[entry_i:exit_i]
    if direction == "long":
        mae = float(sl_low.min() / entry_px - 1.0)
        mfe = float(sl_high.max() / entry_px - 1.0)
    else:
        mae = float(entry_px / sl_high.max() - 1.0)
        mfe = float(entry_px / sl_low.min() - 1.0)
    return mae, mfe


def year_ok_flag(years: list[dict]) -> tuple[bool, str]:
    if not years:
        return False, "no yearly rows"
    pos = [y for y in years if np.isfinite(y["mean_net_trade"]) and y["mean_net_trade"] > 0]
    rets = np.array([y["year_return"] for y in years if np.isfinite(y["year_return"])], dtype=float)
    pos_rets = np.clip(rets, 0, None)
    share = float(pos_rets.max() / pos_rets.sum()) if pos_rets.size and pos_rets.sum() > 0 else 1.0
    other = [y for y in pos if y["year"] not in (2020, 2021, 2022)]
    n_pos = len(pos)
    concentrated = n_pos <= 1 or share >= 0.70
    only_bull = n_pos > 0 and len(other) == 0
    ok = (not concentrated) and n_pos >= 2 and (not only_bull)
    msg = (
        f"years_with_positive_mean_net={n_pos}/{len(years)}; "
        f"max_positive_year_share={share:.2f}; "
        f"positive_outside_2020_2022={len(other)}"
    )
    return ok, msg


def classify_strict(disc: dict, val: dict, rec: dict, year_ok: bool) -> str:
    d_net = disc["mean_net_trade"]
    d_adv = disc["strat_diff_mean"]
    v_net = val["mean_net_trade"]
    v_adv = val["strat_diff_mean"]
    v_sh = val["mtm_sharpe"]
    v_n = int(val["n_trades"])
    r_net = rec["mean_net_trade"]
    r_adv = rec["strat_diff_mean"]
    r_n = int(rec["n_trades"])

    val_fail = (not np.isfinite(v_net)) or v_net <= 0 or (not np.isfinite(v_adv)) or v_adv <= 0
    if val_fail:
        return "FAIL"
    disc_ok = np.isfinite(d_net) and d_net > 0 and np.isfinite(d_adv) and d_adv > 0
    if not disc_ok:
        return "FAIL"

    rec_pnl_ok = r_n < 5 or (np.isfinite(r_net) and r_net >= 0)
    rec_adv_ok = r_n < 5 or (np.isfinite(r_adv) and r_adv >= 0)
    rec_pnl_pos_adv_neg = r_n >= 5 and np.isfinite(r_net) and r_net > 0 and np.isfinite(r_adv) and r_adv < 0

    val_core = v_net > 0 and v_adv > 0 and np.isfinite(v_sh) and v_sh > 0 and v_n >= 15
    if (
        val_core
        and rec_pnl_ok
        and rec_adv_ok
        and year_ok
        and not rec_pnl_pos_adv_neg
    ):
        return "STRONG SURVIVOR"

    if rec_pnl_pos_adv_neg:
        return "SURVIVES"
    if val_core and (not rec_pnl_ok or not rec_adv_ok or not year_ok):
        return "SURVIVES"
    if v_net > 0 and v_adv > 0:
        if (not np.isfinite(v_sh) or v_sh <= 0) or v_n < 15:
            return "FRAGILE" if not (np.isfinite(v_sh) and v_sh > 0) else "SURVIVES"
        return "SURVIVES"
    return "FRAGILE"


def candidate_decision(disc: dict, val: dict, rec: dict, lookback_changed: bool) -> str:
    d_net = disc["mean_net_trade"]
    v_net = val["mean_net_trade"]
    v_adv = val["strat_diff_mean"]
    v_sh = val["mtm_sharpe"]
    r_net = rec["mean_net_trade"]
    r_adv = rec["strat_diff_mean"]
    r_n = int(rec["n_trades"])
    r_sh = rec["mtm_sharpe"]
    v_n = int(val["n_trades"])

    rec_net_ok = r_n < 5 or (np.isfinite(r_net) and r_net >= 0)
    rec_adv_ok = r_n < 5 or (np.isfinite(r_adv) and r_adv >= 0)
    rec_sh_ok = r_n < 5 or (not np.isfinite(r_sh)) or r_sh >= 0

    hard_fail = (
        (not np.isfinite(d_net) or d_net <= 0)
        or (not np.isfinite(v_net) or v_net <= 0)
        or (not np.isfinite(v_adv) or v_adv <= 0)
        or (not rec_net_ok)
        or (not rec_adv_ok)
        or lookback_changed
    )
    if hard_fail:
        return "FAIL"

    full_pass = (
        d_net > 0
        and v_net > 0
        and rec_net_ok
        and v_adv > 0
        and rec_adv_ok
        and np.isfinite(v_sh)
        and v_sh > 0
        and rec_sh_ok
        and v_n >= 15
    )
    if full_pass:
        return "PASS"
    return "PASS WITH LIMITATIONS"


def load_phase4_readonly() -> tuple[pd.DataFrame, pd.DataFrame]:
    top_path = PHASE4 / "results" / "TOP_CANDIDATES.csv"
    val_path = PHASE4 / "results" / "VALIDATION_RESULTS.csv"
    if not top_path.exists() or not val_path.exists():
        raise RuntimeError("Phase 4 result files are missing; cannot audit.")
    top = pd.read_csv(top_path)
    val = pd.read_csv(val_path)
    log(f"loaded frozen Phase 4 top10={len(top)} validation_rows={len(val)} (read-only)")
    return top, val


def write_report(
    meta: dict,
    cand: dict,
    old_row: pd.Series,
    old_val: pd.Series,
    ov: pd.DataFrame,
    top10: pd.DataFrame,
    sig_audit: dict,
    decision: str,
    runtime_s: float,
) -> None:
    freeze = (
        "CRASH_REBOUND_CANDIDATE_V1 = FROZEN"
        if decision in ("PASS", "PASS WITH LIMITATIONS")
        else "CRASH_REBOUND_CANDIDATE_V1 = REJECTED"
    )
    freeze_params = (
        "lookback = 6h\n"
        "threshold = expanding p1\n"
        "direction = LONG\n"
        "entry = next hourly open\n"
        "holding = 6h\n"
        "fee baseline = 10 bps"
    )
    if decision not in ("PASS", "PASS WITH LIMITATIONS"):
        freeze_params = "No freeze. Do not rescue-optimize."

    def block(title: str, old_n, new_n, old_net, new_net, old_end, new_end, old_sh, new_mtm_sh, old_dd, new_dd, old_adv, new_adv, extra=""):
        return [
            f"## {title}",
            f"N trades: old {old_n} → new {new_n}",
            f"mean net (10 bps): old {fmt_pct(old_net, 3)} → new {fmt_pct(new_net, 3)}",
            f"$10,000 → old {fmt_usd(old_end)} / new MTM {fmt_usd(new_end)}",
            f"Sharpe: old trade-Sharpe {fmt_num(old_sh)} → new MTM Sharpe {fmt_num(new_mtm_sh)}",
            f"MaxDD: old trade-path {fmt_pct(old_dd)} → new hourly MTM {fmt_pct(new_dd)}",
            f"conditional advantage: old {fmt_pct(old_adv, 3)} → new {fmt_pct(new_adv, 3)}",
            extra,
            "",
        ]

    cls_changes = []
    for _, r in ov.iterrows():
        if str(r["old_classification"]) != str(r["new_classification"]):
            cls_changes.append(
                f"- `{r['rule_id']}`: {r['old_classification']} → {r['new_classification']}"
            )
    if not cls_changes:
        cls_changes = ["- No classification changes among the frozen Top 10."]

    rally = ov.loc[ov["rule_id"] == "L12_up_p97.5_continuation_long_H168"]
    rally_cls = str(rally.iloc[0]["new_classification"]) if not rally.empty else "NA"
    rally_old = str(rally.iloc[0]["old_classification"]) if not rally.empty else "NA"

    d = cand["discovery"]
    v = cand["validation"]
    r = cand["recent"]
    lines = [
        "# Extreme-move audit fix — Phase 4b",
        "",
        "Read-only correction of Phase 4. No new search. Not clean OOS. Not a live system.",
        "Phase 4 files were not overwritten. The Phase 3 calendar candidate was not modified.",
        "",
        "## CANDIDATE",
        "",
        "Trailing exact 6h BTC return <= expanding p1",
        "→ LONG next hourly open",
        "→ EXIT 6h later.",
        "",
        f"Rule id: `{CANDIDATE_ID}`",
        "",
        *block(
            "DISCOVERY",
            int(old_val["disc_n_trades"]),
            int(d["n_trades"]),
            float(old_val["disc_mean_net_trade"]),
            d["mean_net_trade"],
            float(old_val["disc_ending_capital_from_10000"]),
            d["mtm_end_cap"],
            float(old_val["disc_sharpe"]),
            d["mtm_sharpe"],
            float(old_val["disc_max_drawdown"]),
            d["mtm_max_dd"],
            float(old_val["disc_strat_diff_mean"]),
            d["strat_diff_mean"],
            extra=(
                f"MTM vol {fmt_pct(d['mtm_vol'])}; Calmar {fmt_num(d['mtm_calmar'])}; "
                f"exposure {fmt_pct(d['mtm_exposure'])}; trade_sharpe_diagnostic {fmt_num(d['trade_sharpe'])}"
            ),
        ),
        *block(
            "VALIDATION",
            int(old_val["val_n_trades"]),
            int(v["n_trades"]),
            float(old_val["val_mean_net_trade"]),
            v["mean_net_trade"],
            float(old_val["val_ending_capital_from_10000"]),
            v["mtm_end_cap"],
            float(old_val["val_sharpe"]),
            v["mtm_sharpe"],
            float(old_val["val_max_drawdown"]),
            v["mtm_max_dd"],
            float(old_val["val_strat_diff_mean"]),
            v["strat_diff_mean"],
            extra=(
                f"MTM vol {fmt_pct(v['mtm_vol'])}; Calmar {fmt_num(v['mtm_calmar'])}; "
                f"exposure {fmt_pct(v['mtm_exposure'])}; trade_sharpe_diagnostic {fmt_num(v['trade_sharpe'])}"
            ),
        ),
        *block(
            "RECENT",
            int(old_val["rec_n_trades"]),
            int(r["n_trades"]),
            float(old_val["rec_mean_net_trade"]),
            r["mean_net_trade"],
            float(old_val["rec_ending_capital_from_10000"]),
            r["mtm_end_cap"],
            float(old_val["rec_sharpe"]),
            r["mtm_sharpe"],
            float(old_val["rec_max_drawdown"]),
            r["mtm_max_dd"],
            float(old_val["rec_btc_diff_mean"]),
            r["strat_diff_mean"],
            extra=(
                f"MTM vol {fmt_pct(r['mtm_vol'])}; Calmar {fmt_num(r['mtm_calmar'])}; "
                f"exposure {fmt_pct(r['mtm_exposure'])}; trade_sharpe_diagnostic {fmt_num(r['trade_sharpe'])}"
            ),
        ),
        "## Answers",
        "",
        f"1. Did exact timestamp lookbacks materially change the results? "
        f"**{'Yes' if sig_audit['material_change'] else 'No'}. "
        f"L6 p1 down signals: old {sig_audit['old_l6_p1_signals']} → new {sig_audit['new_l6_p1_signals']}; "
        f"disappeared {sig_audit['n_disappeared']}, appeared {sig_audit['n_appeared']}. "
        f"Candidate discovery mean net old {fmt_pct(float(old_val['disc_mean_net_trade']), 3)} → "
        f"new {fmt_pct(d['mean_net_trade'], 3)}; validation "
        f"{fmt_pct(float(old_val['val_mean_net_trade']), 3)} → {fmt_pct(v['mean_net_trade'], 3)}.**",
        f"2. How many previous signals disappeared because t-6h was genuinely missing? "
        f"**{sig_audit['n_old_signals_missing_t_minus_6']} of {sig_audit['old_l6_p1_signals']} "
        f"positional L6-down-p1 signals had no exact t−6h bar.**",
        f"3. Did any new signals appear? "
        f"**{'Yes' if sig_audit['n_appeared'] else 'No'}: {sig_audit['n_appeared']} new L6-down-p1 "
        f"signal hours after exact-timestamp returns + expanding p1.**",
        f"4. Does L6_down_p1_rebound_long_H6 remain profitable in Discovery? "
        f"**{'Yes' if d['mean_net_trade'] > 0 else 'No'} "
        f"(mean net {fmt_pct(d['mean_net_trade'], 3)}, N={int(d['n_trades'])}, "
        f"MTM $10k → {fmt_usd(d['mtm_end_cap'])}).**",
        f"5. Validation? "
        f"**{'Yes' if v['mean_net_trade'] > 0 else 'No'} "
        f"(mean net {fmt_pct(v['mean_net_trade'], 3)}, N={int(v['n_trades'])}, "
        f"MTM $10k → {fmt_usd(v['mtm_end_cap'])}).**",
        f"6. Recent? "
        f"**{'Yes' if np.isfinite(r['mean_net_trade']) and r['mean_net_trade'] >= 0 else 'No'} "
        f"(mean net {fmt_pct(r['mean_net_trade'], 3)}, N={int(r['n_trades'])}, "
        f"MTM $10k → {fmt_usd(r['mtm_end_cap'])}).**",
        f"7. Does conditional advantage remain positive in Validation? "
        f"**{'Yes' if v['strat_diff_mean'] > 0 else 'No'} "
        f"({fmt_pct(v['strat_diff_mean'], 3)}; cond {fmt_pct(v['strat_cond_mean'], 3)} vs "
        f"uncond {fmt_pct(v['strat_uncond_mean'], 3)}).**",
        f"8. Recent? "
        f"**{'Yes' if np.isfinite(r['strat_diff_mean']) and r['strat_diff_mean'] >= 0 else 'No'} "
        f"({fmt_pct(r['strat_diff_mean'], 3)}).**",
        f"9. What is the TRUE hourly mark-to-market Sharpe? "
        f"**Discovery {fmt_num(d['mtm_sharpe'])}; validation {fmt_num(v['mtm_sharpe'])}; "
        f"recent {fmt_num(r['mtm_sharpe'])} "
        f"(annualized with sqrt(365×24) on hourly equity returns, zeros when flat). "
        f"trade_sharpe_diagnostic: discovery {fmt_num(d['trade_sharpe'])}, "
        f"validation {fmt_num(v['trade_sharpe'])}, recent {fmt_num(r['trade_sharpe'])}.**",
        f"10. What is TRUE max drawdown? "
        f"**Discovery {fmt_pct(d['mtm_max_dd'])}; validation {fmt_pct(v['mtm_max_dd'])}; "
        f"recent {fmt_pct(r['mtm_max_dd'])} "
        f"(hourly MTM, intra-trade path included). Full-sample MTM MaxDD {fmt_pct(cand['full']['mtm_max_dd'])}.**",
        f"11. Does it survive 20 bps? "
        f"**Validation mean net 20 bps {fmt_pct(v['mean_net_20bps'], 3)} "
        f"({'positive' if np.isfinite(v['mean_net_20bps']) and v['mean_net_20bps'] > 0 else 'not positive'}); "
        f"MTM end cap 20 bps {fmt_usd(v['mtm_end_cap_20bps'])}.**",
        f"12. Does it survive 50 bps? "
        f"**Validation mean net 50 bps {fmt_pct(v['mean_net_50bps'], 3)} "
        f"({'positive' if np.isfinite(v['mean_net_50bps']) and v['mean_net_50bps'] > 0 else 'not positive'}); "
        f"MTM end cap 50 bps {fmt_usd(v['mtm_end_cap_50bps'])}.**",
        f"13. How did classifications of the original Top 10 change? "
        f"**{sum(ov['old_classification'] != ov['new_classification'])} of 10 changed.**",
        *cls_changes,
        f"14. Does the previous 168h rally-continuation winner still qualify as STRONG SURVIVOR "
        f"under the stricter rule? **{'Yes' if rally_cls == 'STRONG SURVIVOR' else 'No'} "
        f"(old {rally_old} → new {rally_cls}).**",
        f"15. Final decision for Crash Rebound Candidate: **{decision}**",
        "",
        f"## {freeze}",
        "",
        freeze_params,
        "",
        "Do not optimize this rule again. No p0.5 / 4h / 8h / extra indicators.",
        "",
        "## Frozen Top 10 — corrected classification",
        "",
        "| Rank | Rule | Old class | New class | Val mean net | Val MTM Sharpe | Val adv | Rec mean net | Rec adv |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in top10.sort_values("discovery_rank").iterrows():
        lines.append(
            f"| {int(row['discovery_rank'])} | `{row['rule_id']}` | {row['old_classification']} | "
            f"{row['new_classification']} | {fmt_pct(row['val_mean_net_trade'], 3)} | "
            f"{fmt_num(row['val_mtm_sharpe'])} | {fmt_pct(row['val_strat_diff_mean'], 3)} | "
            f"{fmt_pct(row['rec_mean_net_trade'], 3)} | {fmt_pct(row['rec_strat_diff_mean'], 3)} |"
        )
    lines += [
        "",
        "## Audit assertions",
        "",
        "- Phase 4 CSVs were read, not overwritten.",
        "- Trailing returns require both `t` and `t−L hours` to exist as exact timestamps.",
        "- Expanding percentiles use only finite returns with timestamp < t; 30 random checks vs NumPy passed.",
        "- Execution remains open of t+1; exit open t+1+H; overlapping signals ignored in PnL.",
        "- Hourly MTM uses close while in a position; fills at open; round-trip fee split so entry×exit = (1−fee).",
        "- Primary Sharpe is hourly MTM × sqrt(365×24). trade_sharpe_diagnostic is not used for STRONG SURVIVOR.",
        "- MaxDD is from the hourly equity path, including intra-trade marks.",
        "- Frozen Top 10 were not reselected.",
        "- Shorts remain theoretical unlevered.",
        "",
        f"Script runtime {runtime_s:.1f}s. Generated by `src/audit_extreme_move_candidates.py`.",
        "",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "EXTREME_MOVE_AUDIT_FIX.md").write_text("\n".join(lines), encoding="utf-8")
    log(f"wrote {RESULTS / 'EXTREME_MOVE_AUDIT_FIX.md'}")


def slice_period_equity(equity: np.ndarray, position: np.ndarray, mask: np.ndarray, start_cap: float = START_CAP) -> tuple[np.ndarray, np.ndarray]:
    """Rescale a full-sample equity path onto a period window starting at $10k.

    Uses hourly returns inside the mask so intra-trade MaxDD is preserved
    for trades that overlap the window.
    """
    eq = np.asarray(equity, dtype=float)
    pos = np.asarray(position)
    n = len(eq)
    out_eq = np.full(n, np.nan)
    out_pos = np.zeros(n, dtype=np.int8)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return np.array([start_cap]), np.array([0], dtype=np.int8)
    i0 = int(idx[0])
    # walk all hours from first masked bar through last masked bar, including
    # intra-period flats
    i1 = int(idx[-1])
    rets = np.zeros(i1 - i0, dtype=float)
    for k, i in enumerate(range(i0, i1)):
        if eq[i] > 0 and np.isfinite(eq[i]) and np.isfinite(eq[i + 1]) and eq[i + 1] > 0:
            rets[k] = eq[i + 1] / eq[i] - 1.0
    path = np.empty(i1 - i0 + 1, dtype=float)
    path[0] = start_cap
    path[1:] = start_cap * np.cumprod(1.0 + rets)
    return path, pos[i0 : i1 + 1]


def main() -> None:
    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    old_top, old_val_tbl = load_phase4_readonly()
    frozen_ids = list(old_top["rule_id"].astype(str))
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
    span = {p: period_span_days(meta, p) for p in PERIODS}

    needed_h = sorted(set(HOLDS) | set(LOOKBACKS) | {1})
    ahead = {h: hours_ahead_index(ts, h) for h in needed_h}
    behind = {h: hours_behind_index(ts, h) for h in LOOKBACKS}
    entry_idx = ahead[1]
    log(f"forward/back maps ready hours={needed_h}")

    fwd_long = {}
    fwd_short = {}
    exit_for = {}
    for h in HOLDS:
        x = take_idx(ahead[h], entry_idx)
        ok = (entry_idx >= 0) & (x >= 0)
        fl = np.full(n, np.nan)
        fs = np.full(n, np.nan)
        fl[ok] = opens[x[ok]] / opens[entry_idx[ok]] - 1.0
        fs[ok] = opens[entry_idx[ok]] / opens[x[ok]] - 1.0
        fwd_long[h] = fl
        fwd_short[h] = fs
        exit_for[h] = x

    uncond = {h: {} for h in HOLDS}
    for h in HOLDS:
        for p in PERIODS:
            m = (periods == p) & np.isfinite(fwd_long[h])
            uncond[h][p] = {"long": fwd_long[h][m], "short": fwd_short[h][m]}

    log("computing EXACT-timestamp trailing returns + expanding percentiles")
    ret_exact = {}
    ret_pos = {}
    q_map = {}
    q_pos = {}
    all_probs = tuple(sorted(set(DOWN_PCTS + UP_PCTS)))
    for L in LOOKBACKS:
        ret_exact[L] = exact_trailing_return(closes, behind[L])
        ret_pos[L] = positional_trailing_return(closes, L)
        n_exact = int(np.isfinite(ret_exact[L]).sum())
        n_pos = int(np.isfinite(ret_pos[L]).sum())
        n_pos_only = int((np.isfinite(ret_pos[L]) & ~np.isfinite(ret_exact[L])).sum())
        log(f"  L{L}h exact_finite={n_exact} positional_finite={n_pos} positional_but_missing_t-minus-L={n_pos_only}")
        q_map[L] = expanding_quantiles(ret_exact[L], ts, all_probs)
        q_pos[L] = expanding_quantiles(ret_pos[L], ts, all_probs)
        for p in all_probs:
            audit_expanding(ret_exact[L], q_map[L][p], p)
        log(f"  lookback {L}h expanding quantiles audited ({AUDIT_EXPANDING_N} timestamps)")

    # L6 down p1 signal comparison (positional old method vs exact)
    old_sig = np.isfinite(ret_pos[6]) & np.isfinite(q_pos[6][0.01]) & (ret_pos[6] <= q_pos[6][0.01])
    new_sig = np.isfinite(ret_exact[6]) & np.isfinite(q_map[6][0.01]) & (ret_exact[6] <= q_map[6][0.01])
    missing_t6 = (behind[6] < 0) & old_sig
    sig_audit = {
        "old_l6_p1_signals": int(old_sig.sum()),
        "new_l6_p1_signals": int(new_sig.sum()),
        "n_disappeared": int((old_sig & ~new_sig).sum()),
        "n_appeared": int((new_sig & ~old_sig).sum()),
        "n_old_signals_missing_t_minus_6": int(missing_t6.sum()),
        "n_overlap": int((old_sig & new_sig).sum()),
    }
    log(
        f"L6 down p1 signals old={sig_audit['old_l6_p1_signals']} new={sig_audit['new_l6_p1_signals']} "
        f"disappeared={sig_audit['n_disappeared']} appeared={sig_audit['n_appeared']} "
        f"old_missing_t-6h={sig_audit['n_old_signals_missing_t_minus_6']}"
    )

    rule_period: dict[tuple[str, str], dict] = {}
    rule_trades: dict[str, list[tuple[int, int, int]]] = {}
    rule_meta: dict[str, dict] = {}

    for L in LOOKBACKS:
        ret = ret_exact[L]
        for tail, pcts in (("down", DOWN_PCTS), ("up", UP_PCTS)):
            for p in pcts:
                q = q_map[L][p]
                finite = np.isfinite(ret) & np.isfinite(q)
                sig = finite & ((ret <= q) if tail == "down" else (ret >= q))
                has_entry = sig & (entry_idx >= 0)
                for h in HOLDS:
                    x = exit_for[h]
                    has_exit = has_entry & (x >= 0)
                    for direction in ("long", "short"):
                        rid = rule_id(L, tail, p, direction, h)
                        thesis = thesis_name(tail, direction)
                        fwd_s = fwd_long[h] if direction == "long" else fwd_short[h]
                        valid_event = has_exit & np.isfinite(fwd_s)
                        take_all = executable_take(valid_event, entry_idx, ts_ns, h)
                        rule_meta[rid] = {
                            "lookback_h": L,
                            "tail": tail,
                            "percentile": p,
                            "percentile_label": pct_label(p),
                            "direction": direction,
                            "thesis": thesis,
                            "hold_h": h,
                            "short_theoretical": direction == "short",
                        }
                        tlist = []
                        for t in np.flatnonzero(take_all):
                            tlist.append((int(t), int(entry_idx[t]), int(x[t])))
                        rule_trades[rid] = tlist
                        for period in PERIODS:
                            ev = valid_event & (periods == period)
                            tk = take_all & (periods == period)
                            st = dist_stats(fwd_s[ev], uncond[h][period][direction])
                            g = fwd_s[tk]
                            g = g[np.isfinite(g)]
                            nets10 = net_from_gross(g, FEE_PRIMARY)
                            row = {
                                "n_signals": int((sig & (periods == period)).sum()),
                                "n_events": int(ev.sum()),
                                "n_trades": int(g.size),
                                "mean_trade_gross": float(g.mean()) if g.size else np.nan,
                                "mean_net_trade": float(nets10.mean()) if g.size else np.nan,
                                "median_net_trade": float(np.median(nets10)) if g.size else np.nan,
                                "win_rate": float(np.mean(nets10 > 0)) if g.size else np.nan,
                                "trade_sharpe": trade_sharpe(nets10, span[period]),
                                "trade_end_cap": ending_capital(nets10),
                                "strat_cond_mean": st["cond_mean"],
                                "strat_uncond_mean": st["uncond_mean"],
                                "strat_diff_mean": st["diff_mean"],
                                "mean_net_0bps": float(net_from_gross(g, 0.0).mean()) if g.size else np.nan,
                                "mean_net_20bps": float(net_from_gross(g, 0.0020).mean()) if g.size else np.nan,
                                "mean_net_50bps": float(net_from_gross(g, 0.0050).mean()) if g.size else np.nan,
                            }
                            rule_period[(rid, period)] = row
                log(f"  scanned L{L} {tail} {pct_label(p)}")

    # MTM for frozen Top 10 + candidate
    need_mtm = set(frozen_ids)
    need_mtm.add(CANDIDATE_ID)
    mtm_store: dict[str, dict] = {}
    for rid in sorted(need_mtm):
        meta_r = rule_meta[rid]
        direction = meta_r["direction"]
        pairs = [(e, x) for _, e, x in rule_trades[rid]]
        eq10, pos10 = mtm_from_trades(n, opens, closes, pairs, direction, FEE_PRIMARY)
        mtm_fees = {}
        for bps, fee in zip(FEE_BPS, FEE_SET):
            eq, pos = mtm_from_trades(n, opens, closes, pairs, direction, fee)
            mtm_fees[bps] = (eq, pos)
        by_period = {}
        for period in PERIODS:
            p_pairs = [(e, x) for t, e, x in rule_trades[rid] if periods[t] == period]
            mask = periods == period
            if p_pairs:
                last_exit = max(x for _, x in p_pairs)
                first_entry = min(e for e, _ in p_pairs)
                ext = np.zeros(n, dtype=bool)
                ext[first_entry : last_exit + 1] = True
                mask = mask | ext
            eq_p, pos_p = mtm_from_trades(n, opens, closes, p_pairs, direction, FEE_PRIMARY)
            path, ppos = slice_period_equity(eq_p, pos_p, mask)
            mets = mtm_metrics(path, ppos, span[period])
            for bps, fee in zip(FEE_BPS, FEE_SET):
                eq_b, pos_b = mtm_from_trades(n, opens, closes, p_pairs, direction, fee)
                pth, ppo = slice_period_equity(eq_b, pos_b, mask)
                mets[f"mtm_end_cap_{bps}bps"] = mtm_metrics(pth, ppo, span[period])["mtm_end_cap"]
            by_period[period] = mets
        full_mets = mtm_metrics(eq10, pos10, max(float((meta["end_utc"] - meta["start_utc"]).total_seconds() / 86400.0), 1.0))
        mtm_store[rid] = {"eq10": eq10, "pos10": pos10, "fees": mtm_fees, "by_period": by_period, "full": full_mets}
        log(f"  MTM {rid} full_sharpe={fmt_num(full_mets['mtm_sharpe'])} maxdd={fmt_pct(full_mets['mtm_max_dd'])}")

    def packed(rid: str, period: str) -> dict:
        row = dict(rule_period[(rid, period)])
        row.update(mtm_store[rid]["by_period"][period])
        return row

    # yearly for candidate + top10
    def years_for(rid: str) -> list[dict]:
        rows = []
        direction = rule_meta[rid]["direction"]
        h = rule_meta[rid]["hold_h"]
        fwd_s = fwd_long[h] if direction == "long" else fwd_short[h]
        take_idx_sig = [t for t, _, _ in rule_trades[rid]]
        if not take_idx_sig:
            return rows
        years = ts.year.to_numpy()
        for year in sorted(set(int(years[t]) for t in take_idx_sig)):
            ts_year = [t for t in take_idx_sig if int(years[t]) == year]
            g = np.array([fwd_s[t] for t in ts_year], dtype=float)
            nets = net_from_gross(g, FEE_PRIMARY)
            rows.append(
                {
                    "year": year,
                    "n_trades": int(g.size),
                    "year_return": float(np.prod(1.0 + nets) - 1.0),
                    "mean_net_trade": float(nets.mean()),
                }
            )
        return rows

    corrected_rows = []
    ov_rows = []
    for _, ot in old_top.iterrows():
        rid = str(ot["rule_id"])
        ovl = old_val_tbl.loc[old_val_tbl["rule_id"] == rid]
        if ovl.empty:
            raise RuntimeError(f"Phase 4 validation row missing for {rid}")
        ovl = ovl.iloc[0]
        disc = packed(rid, "discovery")
        val = packed(rid, "validation")
        rec = packed(rid, "recent")
        yok, ymsg = year_ok_flag(years_for(rid))
        new_cls = classify_strict(disc, val, rec, yok)
        corrected_rows.append(
            {
                "discovery_rank": int(ot["discovery_rank"]),
                "rule_id": rid,
                **rule_meta[rid],
                "old_classification": str(ovl["classification"]),
                "new_classification": new_cls,
                "year_ok": yok,
                "year_note": ymsg,
                "disc_n_trades": disc["n_trades"],
                "disc_n_events": disc["n_events"],
                "disc_mean_net_trade": disc["mean_net_trade"],
                "disc_strat_diff_mean": disc["strat_diff_mean"],
                "disc_trade_sharpe": disc["trade_sharpe"],
                "disc_mtm_sharpe": disc["mtm_sharpe"],
                "disc_mtm_end_cap": disc["mtm_end_cap"],
                "disc_mtm_max_dd": disc["mtm_max_dd"],
                "disc_mtm_vol": disc["mtm_vol"],
                "disc_mtm_cagr": disc["mtm_cagr"],
                "disc_mtm_calmar": disc["mtm_calmar"],
                "disc_mtm_exposure": disc["mtm_exposure"],
                "val_n_trades": val["n_trades"],
                "val_n_events": val["n_events"],
                "val_mean_net_trade": val["mean_net_trade"],
                "val_strat_diff_mean": val["strat_diff_mean"],
                "val_strat_cond_mean": val["strat_cond_mean"],
                "val_strat_uncond_mean": val["strat_uncond_mean"],
                "val_trade_sharpe": val["trade_sharpe"],
                "val_mtm_sharpe": val["mtm_sharpe"],
                "val_mtm_end_cap": val["mtm_end_cap"],
                "val_mtm_max_dd": val["mtm_max_dd"],
                "val_mtm_vol": val["mtm_vol"],
                "val_mtm_cagr": val["mtm_cagr"],
                "val_mtm_calmar": val["mtm_calmar"],
                "val_mtm_exposure": val["mtm_exposure"],
                "val_mean_net_0bps": val["mean_net_0bps"],
                "val_mean_net_20bps": val["mean_net_20bps"],
                "val_mean_net_50bps": val["mean_net_50bps"],
                "rec_n_trades": rec["n_trades"],
                "rec_n_events": rec["n_events"],
                "rec_mean_net_trade": rec["mean_net_trade"],
                "rec_strat_diff_mean": rec["strat_diff_mean"],
                "rec_trade_sharpe": rec["trade_sharpe"],
                "rec_mtm_sharpe": rec["mtm_sharpe"],
                "rec_mtm_end_cap": rec["mtm_end_cap"],
                "rec_mtm_max_dd": rec["mtm_max_dd"],
                "rec_mtm_vol": rec["mtm_vol"],
                "rec_mtm_cagr": rec["mtm_cagr"],
                "rec_mtm_exposure": rec["mtm_exposure"],
            }
        )
        ov_rows.append(
            {
                "rule_id": rid,
                "discovery_rank": int(ot["discovery_rank"]),
                "old_discovery_N": int(ovl["disc_n_trades"]),
                "new_discovery_N": disc["n_trades"],
                "old_validation_N": int(ovl["val_n_trades"]),
                "new_validation_N": val["n_trades"],
                "old_recent_N": int(ovl["rec_n_trades"]),
                "new_recent_N": rec["n_trades"],
                "old_validation_mean_net": float(ovl["val_mean_net_trade"]),
                "new_validation_mean_net": val["mean_net_trade"],
                "old_recent_mean_net": float(ovl["rec_mean_net_trade"]),
                "new_recent_mean_net": rec["mean_net_trade"],
                "old_validation_sharpe": float(ovl["val_sharpe"]),
                "new_validation_MTM_sharpe": val["mtm_sharpe"],
                "old_recent_sharpe": float(ovl["rec_sharpe"]),
                "new_recent_MTM_sharpe": rec["mtm_sharpe"],
                "old_validation_conditional_advantage": float(ovl["val_strat_diff_mean"]),
                "new_validation_conditional_advantage": val["strat_diff_mean"],
                "old_recent_conditional_advantage": float(ovl["rec_btc_diff_mean"])
                if rule_meta[rid]["direction"] == "long"
                else float(ovl["rec_mean_net_trade"]),
                "new_recent_conditional_advantage": rec["strat_diff_mean"],
                "old_classification": str(ovl["classification"]),
                "new_classification": new_cls,
            }
        )

    top10 = pd.DataFrame(corrected_rows)
    ov = pd.DataFrame(ov_rows)

    # Candidate V1 trades + equity
    if CANDIDATE_ID not in rule_trades:
        raise RuntimeError(f"{CANDIDATE_ID} missing after exact-timestamp scan")
    ret6 = ret_exact[6]
    q1 = q_map[6][0.01]
    prev_i = behind[6]
    trade_rows = []
    for t, e_i, x_i in rule_trades[CANDIDATE_ID]:
        if prev_i[t] < 0:
            raise RuntimeError("candidate trade without exact t-6h close")
        g = float(opens[x_i] / opens[e_i] - 1.0)
        mae, mfe = trade_mae_mfe(e_i, x_i, float(opens[e_i]), lows, highs, "long")
        trade_rows.append(
            {
                "signal_timestamp": str(ts[t]),
                "exact_previous_timestamp": str(ts[int(prev_i[t])]),
                "signal_close": float(closes[t]),
                "previous_close": float(closes[int(prev_i[t])]),
                "trailing_6h_return": float(ret6[t]),
                "expanding_p1": float(q1[t]),
                "entry_timestamp": str(ts[e_i]),
                "entry_price": float(opens[e_i]),
                "exit_timestamp": str(ts[x_i]),
                "exit_price": float(opens[x_i]),
                "gross_return": g,
                "net_return_10bps": float(net_from_gross(np.array([g]), FEE_PRIMARY)[0]),
                "period": periods[t],
                "MAE": mae,
                "MFE": mfe,
            }
        )
    trades_df = pd.DataFrame(trade_rows)

    eq0, pos0 = mtm_store[CANDIDATE_ID]["fees"][0]
    eq10, pos10 = mtm_store[CANDIDATE_ID]["fees"][10]
    eq20, _ = mtm_store[CANDIDATE_ID]["fees"][20]
    eq50, _ = mtm_store[CANDIDATE_ID]["fees"][50]
    peak = np.maximum.accumulate(eq10)
    dd = eq10 / peak - 1.0
    equity_df = pd.DataFrame(
        {
            "timestamp": ts.astype(str),
            "BTC_price": closes,
            "position": pos10,
            "equity_0bps": eq0,
            "equity_10bps": eq10,
            "equity_20bps": eq20,
            "equity_50bps": eq50,
            "drawdown_10bps": dd,
        }
    )

    cand_pack = {
        "discovery": packed(CANDIDATE_ID, "discovery"),
        "validation": packed(CANDIDATE_ID, "validation"),
        "recent": packed(CANDIDATE_ID, "recent"),
        "full": mtm_store[CANDIDATE_ID]["full"],
    }
    old_cand_top = old_top.loc[old_top["rule_id"] == CANDIDATE_ID].iloc[0]
    old_cand_val = old_val_tbl.loc[old_val_tbl["rule_id"] == CANDIDATE_ID].iloc[0]

    rel_disc = abs(cand_pack["discovery"]["mean_net_trade"] - float(old_cand_val["disc_mean_net_trade"]))
    rel_val = abs(cand_pack["validation"]["mean_net_trade"] - float(old_cand_val["val_mean_net_trade"]))
    old_v = abs(float(old_cand_val["val_mean_net_trade"]))
    lookback_destroyed = (
        (not np.isfinite(cand_pack["validation"]["mean_net_trade"]))
        or cand_pack["validation"]["mean_net_trade"] <= 0
        or (old_v > 0 and rel_val / old_v > 0.75 and cand_pack["validation"]["mean_net_trade"] < 0.5 * float(old_cand_val["val_mean_net_trade"]))
    )
    sig_audit["material_change"] = bool(
        sig_audit["n_disappeared"] + sig_audit["n_appeared"] >= max(5, int(0.05 * max(sig_audit["old_l6_p1_signals"], 1)))
        or rel_disc > 0.002
        or rel_val > 0.002
    )
    decision = candidate_decision(
        cand_pack["discovery"],
        cand_pack["validation"],
        cand_pack["recent"],
        lookback_destroyed,
    )

    ov.to_csv(RESULTS / "OLD_VS_CORRECTED.csv", index=False)
    top10.to_csv(RESULTS / "CORRECTED_TOP10.csv", index=False)
    trades_df.to_csv(RESULTS / "CANDIDATE_V1_TRADES.csv", index=False)
    equity_df.to_csv(RESULTS / "CANDIDATE_V1_EQUITY.csv", index=False)
    log(f"wrote csvs top10={len(top10)} candidate_trades={len(trades_df)} equity_rows={len(equity_df)}")

    runtime_s = time.time() - t0
    write_report(
        meta,
        cand_pack,
        old_cand_top,
        old_cand_val,
        ov,
        top10,
        sig_audit,
        decision,
        runtime_s,
    )
    log(f"done in {runtime_s:.1f}s decision={decision}")


if __name__ == "__main__":
    main()
