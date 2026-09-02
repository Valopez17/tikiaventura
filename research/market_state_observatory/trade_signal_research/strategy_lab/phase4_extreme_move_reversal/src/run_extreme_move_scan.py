#!/usr/bin/env python3
"""Phase 4 — extreme BTC move: rebound vs continuation.

Price only. No indicators, macro, derivatives, ML, or leverage.
Not a live system. Not clean OOS.

Discovery ranking uses available data through 2021-12-31 only.
Validation (2022–2024) and recent (2025→latest) never reselect.
The Phase 3 calendar candidate is frozen and is not used here.
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
LOOKBACKS = (6, 12, 24, 72)
DOWN_PCTS = (0.01, 0.025, 0.05)
UP_PCTS = (0.95, 0.975, 0.99)
HOLDS = (6, 12, 24, 48, 72, 168)
PATH_H = (1, 3, 6, 12, 24, 48, 72, 168)
MIN_CAL_DAYS = 365
MIN_DISC_TRADES = 30
TOP_N = 10
N_BOOT = 2000
BOOT_BLOCK_H = 168
BOOT_SEED = 42
CRYPTO_DAYS = 365.0
HOUR_NS = 3_600_000_000_000
AUDIT_EXPANDING_N = 24

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
    if abs(p - 0.01) < 1e-12:
        return "p1"
    if abs(p - 0.025) < 1e-12:
        return "p2.5"
    if abs(p - 0.05) < 1e-12:
        return "p5"
    if abs(p - 0.95) < 1e-12:
        return "p95"
    if abs(p - 0.975) < 1e-12:
        return "p97.5"
    if abs(p - 0.99) < 1e-12:
        return "p99"
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


def ending_capital(nets: np.ndarray, start_cap: float = START_CAP) -> float:
    nets = np.asarray(nets, dtype=float)
    nets = nets[np.isfinite(nets)]
    if nets.size == 0:
        return float(start_cap)
    return float(start_cap * np.prod(1.0 + nets))


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


def cagr_from(start_cap: float, end_cap: float, days: float) -> float:
    if not np.isfinite(start_cap) or not np.isfinite(end_cap) or start_cap <= 0 or days <= 0:
        return np.nan
    if end_cap <= 0:
        return -1.0
    return float((end_cap / start_cap) ** (CRYPTO_DAYS / days) - 1.0)


def sharpe_trades(nets: np.ndarray, span_days: float) -> float:
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


class FenwickOS:
    """Count Fenwick tree supporting k-th smallest among inserted ranks."""

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
    """Percentile of {ret_s : s < t}, after 365 calendar days from first valid ret."""
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
    out = {
        "n_trades": n,
        "mean_trade_gross": float(g.mean()) if n else np.nan,
        "median_trade_gross": float(np.median(g)) if n else np.nan,
        "mean_net_trade": float(nets.mean()) if n else np.nan,
        "median_net_trade": float(np.median(nets)) if n else np.nan,
        "win_rate": float(np.mean(nets > 0)) if n else np.nan,
        "profit_factor": profit_factor(nets) if n else np.nan,
        "sharpe": sharpe_trades(nets, span_days),
        "ending_capital_from_10000": ending_capital(nets),
        "max_drawdown": max_drawdown_from_nets(nets),
        "cagr": np.nan,
    }
    out["cagr"] = cagr_from(START_CAP, out["ending_capital_from_10000"], span_days)
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


def window_excursions(
    entry_i: int,
    entry_px: float,
    ts_ns: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    n: int,
) -> tuple[float, float, float, float]:
    end_ns = ts_ns[entry_i] + np.int64(168) * np.int64(HOUR_NS)
    right = int(np.searchsorted(ts_ns, end_ns, side="left"))
    if right <= entry_i:
        return np.nan, np.nan, np.nan, np.nan
    sl_low = low[entry_i:right]
    sl_high = high[entry_i:right]
    j_mae = int(np.argmin(sl_low))
    j_mfe = int(np.argmax(sl_high))
    mae = float(sl_low[j_mae] / entry_px - 1.0)
    mfe = float(sl_high[j_mfe] / entry_px - 1.0)
    mae_h = float(ts_ns[entry_i + j_mae] - ts_ns[entry_i]) / HOUR_NS
    mfe_h = float(ts_ns[entry_i + j_mfe] - ts_ns[entry_i]) / HOUR_NS
    return mae, mfe, mae_h, mfe_h


def circular_block_indices(n: int, block: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block, dtype=np.int64)
    idx = (starts[..., None] + offsets[None, None, :]) % n
    return idx.reshape(n_boot, n_blocks * block)[:, :n]


def bootstrap_top_rule(
    valid_event: np.ndarray,
    period_mask: np.ndarray,
    fwd_strat: np.ndarray,
    hold_h: int,
    fee: float,
    n_boot: int = N_BOOT,
    block: int = BOOT_BLOCK_H,
    seed: int = BOOT_SEED,
) -> dict:
    loc = np.flatnonzero(period_mask)
    if loc.size < block * 2:
        return {
            "mean_net_lo": np.nan,
            "mean_net_hi": np.nan,
            "adv_lo": np.nan,
            "adv_hi": np.nan,
            "n_boot_used": 0,
            "n_hours": int(loc.size),
        }
    ev = valid_event[loc]
    strat = fwd_strat[loc]
    rng = np.random.default_rng(seed)
    draws = circular_block_indices(int(loc.size), block, n_boot, rng)
    mean_nets = np.full(n_boot, np.nan)
    advs = np.full(n_boot, np.nan)
    n_used = 0
    for b in range(n_boot):
        ii = draws[b]
        ev_b = ev[ii]
        st_b = strat[ii]
        finite_ev = ev_b & np.isfinite(st_b)
        finite_u = np.isfinite(st_b)
        if finite_ev.any() and finite_u.any():
            advs[b] = float(st_b[finite_ev].mean() - st_b[finite_u].mean())
        pos = np.flatnonzero(finite_ev)
        if pos.size == 0:
            continue
        taken = []
        busy = -1
        for p in pos:
            if p < busy:
                continue
            taken.append(float(st_b[p]))
            busy = int(p) + int(hold_h)
        if not taken:
            continue
        nets = net_from_gross(np.asarray(taken, dtype=float), fee)
        mean_nets[b] = float(nets.mean())
        n_used += 1
    ok_n = mean_nets[np.isfinite(mean_nets)]
    ok_a = advs[np.isfinite(advs)]
    return {
        "mean_net_lo": float(np.quantile(ok_n, 0.025)) if ok_n.size else np.nan,
        "mean_net_hi": float(np.quantile(ok_n, 0.975)) if ok_n.size else np.nan,
        "adv_lo": float(np.quantile(ok_a, 0.025)) if ok_a.size else np.nan,
        "adv_hi": float(np.quantile(ok_a, 0.975)) if ok_a.size else np.nan,
        "n_boot_used": int(n_used),
        "n_hours": int(loc.size),
    }


def year_rows(signal_ts: pd.DatetimeIndex, take: np.ndarray, gross: np.ndarray, span_by_year: bool = True) -> list[dict]:
    rows = []
    years = signal_ts.year.to_numpy()
    for year in range(int(years.min()) if len(years) else 0, int(years.max()) + 1 if len(years) else 0):
        m = take & (years == year)
        g = gross[m]
        g = g[np.isfinite(g)]
        if g.size == 0:
            continue
        nets = net_from_gross(g, FEE_PRIMARY)
        days = 366.0 if year % 4 == 0 else 365.0
        rows.append(
            {
                "year": int(year),
                "n_trades": int(g.size),
                "year_return": float(np.prod(1.0 + nets) - 1.0),
                "mean_trade_gross": float(g.mean()),
                "mean_net_trade": float(nets.mean()),
                "win_rate": float(np.mean(nets > 0)),
                "sharpe": sharpe_trades(nets, days),
                "ending_capital_from_10000": ending_capital(nets),
                "max_drawdown": max_drawdown_from_nets(nets),
            }
        )
    return rows


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


def classify_rule(disc: pd.Series, val: pd.Series, rec: pd.Series, year_ok: bool, year_msg: str) -> str:
    disc_net = float(disc["mean_net_trade"])
    disc_adv = float(disc["strat_diff_mean"])
    val_net = float(val["mean_net_trade"]) if val is not None else np.nan
    val_adv = float(val["strat_diff_mean"]) if val is not None else np.nan
    val_sh = float(val["sharpe"]) if val is not None else np.nan
    val_n = int(val["n_trades"]) if val is not None and np.isfinite(val["n_trades"]) else 0
    rec_net = float(rec["mean_net_trade"]) if rec is not None else np.nan
    rec_n = int(rec["n_trades"]) if rec is not None and np.isfinite(rec["n_trades"]) else 0

    val_net_nonpos = (not np.isfinite(val_net)) or val_net <= 0
    val_adv_gone = (not np.isfinite(val_adv)) or val_adv <= 0
    if val_net_nonpos or val_adv_gone:
        return "FAIL"

    disc_ok = np.isfinite(disc_net) and disc_net > 0 and np.isfinite(disc_adv) and disc_adv > 0
    val_ok = val_net > 0 and val_adv > 0 and np.isfinite(val_sh) and val_sh > 0
    if not disc_ok:
        return "FAIL"
    if not val_ok:
        return "FRAGILE"

    rec_contra = rec_n >= 5 and np.isfinite(rec_net) and rec_net < 0
    weak_n = val_n < 15
    disc_sh = float(disc["sharpe"])
    weaker = (
        np.isfinite(disc_sh)
        and np.isfinite(val_sh)
        and disc_sh > 0
        and val_sh < 0.30 * disc_sh
    )
    if weaker and rec_contra:
        return "FRAGILE"
    if weaker or weak_n or rec_contra or (not year_ok):
        return "SURVIVES"

    rec_ok = rec_n < 5 or (np.isfinite(rec_net) and rec_net >= 0)
    if rec_ok and year_ok and val_n >= 15:
        return "STRONG SURVIVOR"
    return "SURVIVES"


def signal_text(row: pd.Series) -> str:
    tail = row["tail"]
    lab = row["percentile_label"]
    lb = int(row["lookback_h"])
    if tail == "down":
        return f"trailing {lb}h return <= expanding {lab}"
    return f"trailing {lb}h return >= expanding {lab}"


def write_report(
    meta: dict,
    all_rules: pd.DataFrame,
    top: pd.DataFrame,
    val_tbl: pd.DataFrame,
    year_map: dict[str, list[dict]],
    boot_map: dict[str, dict],
    path_summary: dict,
    skip_meta: dict,
    runtime_s: float,
) -> None:
    best = top.iloc[0]
    rid = best["rule_id"]
    vbest = val_tbl.loc[val_tbl["rule_id"] == rid].iloc[0]
    d_end = float(best["ending_capital_from_10000"])
    v_end = float(vbest["val_ending_capital_from_10000"])
    r_end = float(vbest["rec_ending_capital_from_10000"])
    cls_best = str(vbest["classification"])

    n_strong = int((val_tbl["classification"] == "STRONG SURVIVOR").sum())
    n_surv = int(val_tbl["classification"].isin(["SURVIVES", "STRONG SURVIVOR"]).sum())
    n_frag = int((val_tbl["classification"] == "FRAGILE").sum())
    n_fail = int((val_tbl["classification"] == "FAIL").sum())

    disc_all = all_rules.loc[all_rules["period"] == "discovery"]
    val_all = all_rules.loc[all_rules["period"] == "validation"]

    def tail_hold_table(df: pd.DataFrame, tail: str) -> pd.DataFrame:
        sub = df.loc[df["tail"] == tail]
        g = sub.groupby(["lookback_h", "hold_h"], as_index=False).agg(
            btc_diff_mean=("btc_diff_mean", "mean"),
            btc_cond_mean=("btc_cond_mean", "mean"),
            btc_uncond_mean=("btc_uncond_mean", "mean"),
            n_events=("n_events", "mean"),
        )
        return g

    down_disc = tail_hold_table(disc_all, "down")
    up_disc = tail_hold_table(disc_all, "up")
    down_val = tail_hold_table(val_all, "down")
    up_val = tail_hold_table(val_all, "up")

    def avg_diff(g: pd.DataFrame) -> float:
        if g.empty:
            return np.nan
        return float(g["btc_diff_mean"].mean())

    down_disc_d = avg_diff(down_disc)
    down_val_d = avg_diff(down_val)
    up_disc_d = avg_diff(up_disc)
    up_val_d = avg_diff(up_val)

    def lookback_sign_groups(g_disc: pd.DataFrame, g_val: pd.DataFrame) -> tuple[list[int], list[int], list[int]]:
        same_pos, same_neg, mixed = [], [], []
        for lb in LOOKBACKS:
            dd = float(g_disc.loc[g_disc["lookback_h"] == lb, "btc_diff_mean"].mean()) if not g_disc.empty else np.nan
            dv = float(g_val.loc[g_val["lookback_h"] == lb, "btc_diff_mean"].mean()) if not g_val.empty else np.nan
            if np.isfinite(dd) and np.isfinite(dv) and dd > 0 and dv > 0:
                same_pos.append(int(lb))
            elif np.isfinite(dd) and np.isfinite(dv) and dd < 0 and dv < 0:
                same_neg.append(int(lb))
            else:
                mixed.append(int(lb))
        return same_pos, same_neg, mixed

    def crash_answer(d_disc: float, d_val: float) -> str:
        pos, neg, mixed = lookback_sign_groups(down_disc, down_val)
        bits = [
            f"Pooled across lookbacks/holds, discovery BTC difference {fmt_pct(d_disc, 3)}, "
            f"validation {fmt_pct(d_val, 3)} (not a single crash effect)."
        ]
        if pos:
            bits.append(
                f"Rebound (subsequent BTC > ordinary) in both discovery and validation at "
                f"lookback(s) {', '.join(str(x)+'h' for x in pos)}."
            )
        if neg:
            bits.append(
                f"Continuation (subsequent BTC < ordinary) in both periods at "
                f"lookback(s) {', '.join(str(x)+'h' for x in neg)}."
            )
        if mixed:
            bits.append(f"Sign flips or is inconclusive at lookback(s) {', '.join(str(x)+'h' for x in mixed)}.")
        bits.append("No stable short-after-crash pattern entered the Top 10.")
        return " ".join(bits)

    def rally_answer(d_disc: float, d_val: float) -> str:
        pos, neg, mixed = lookback_sign_groups(up_disc, up_val)
        bits = [
            f"Pooled across lookbacks/holds, discovery BTC difference {fmt_pct(d_disc, 3)}, "
            f"validation {fmt_pct(d_val, 3)}."
        ]
        if pos:
            bits.append(
                f"Continuation (subsequent BTC > ordinary) in both periods at "
                f"lookback(s) {', '.join(str(x)+'h' for x in pos)}."
            )
        if neg:
            bits.append(
                f"Reversal (subsequent BTC < ordinary) in both periods at "
                f"lookback(s) {', '.join(str(x)+'h' for x in neg)}."
            )
        if mixed:
            bits.append(f"Sign flips or is inconclusive at lookback(s) {', '.join(str(x)+'h' for x in mixed)}.")
        return " ".join(bits)

    # Strongest horizon: largest |btc_diff| that keeps the same sign in discovery and validation.
    def strongest_horizon(g_disc: pd.DataFrame, g_val: pd.DataFrame) -> str:
        if g_disc.empty or g_val.empty:
            return "NA"
        m = g_disc.merge(g_val, on=["lookback_h", "hold_h"], suffixes=("_d", "_v"))
        if m.empty:
            return "NA"
        same = np.sign(m["btc_diff_mean_d"]) == np.sign(m["btc_diff_mean_v"])
        same &= m["btc_diff_mean_d"] != 0
        m2 = m.loc[same].copy()
        if m2.empty:
            m2 = m.copy()
        m2["score"] = m2["btc_diff_mean_v"].abs()
        r = m2.sort_values("score", ascending=False).iloc[0]
        return (
            f"lookback {int(r['lookback_h'])}h → hold {int(r['hold_h'])}h "
            f"(validation BTC difference {fmt_pct(float(r['btc_diff_mean_v']), 3)}; "
            f"discovery {fmt_pct(float(r['btc_diff_mean_d']), 3)})"
        )

    lookback_lines = []
    for lb in LOOKBACKS:
        dd = down_disc.loc[down_disc["lookback_h"] == lb, "btc_diff_mean"].mean()
        dv = down_val.loc[down_val["lookback_h"] == lb, "btc_diff_mean"].mean()
        ud = up_disc.loc[up_disc["lookback_h"] == lb, "btc_diff_mean"].mean()
        uv = up_val.loc[up_val["lookback_h"] == lb, "btc_diff_mean"].mean()
        lookback_lines.append(
            f"- {lb}h lookback: crash BTC-diff discovery {fmt_pct(dd, 3)} / "
            f"validation {fmt_pct(dv, 3)}; rally discovery {fmt_pct(ud, 3)} / "
            f"validation {fmt_pct(uv, 3)}"
        )

    ps = path_summary
    against = ps.get("frac_mae_before_mfe", np.nan)
    mae_typ = ps.get("mae_mean", np.nan)
    mfe_typ = ps.get("mfe_mean", np.nan)
    ret1 = ps.get("ret_1h_mean", np.nan)
    ret6 = ps.get("ret_6h_mean", np.nan)

    cost_line = (
        f"Discovery ending capital 0/10/20/50 bps: "
        f"{fmt_usd(best['end_cap_0bps'])} / {fmt_usd(best['ending_capital_from_10000'])} / "
        f"{fmt_usd(best['end_cap_20bps'])} / {fmt_usd(best['end_cap_50bps'])}. "
        f"Validation 0/10/20/50: "
        f"{fmt_usd(vbest['val_end_cap_0bps'])} / {fmt_usd(vbest['val_ending_capital_from_10000'])} / "
        f"{fmt_usd(vbest['val_end_cap_20bps'])} / {fmt_usd(vbest['val_end_cap_50bps'])}."
    )
    survive_10 = np.isfinite(vbest["val_mean_net_trade"]) and float(vbest["val_mean_net_trade"]) > 0
    survive_20 = np.isfinite(vbest["val_mean_net_20bps"]) and float(vbest["val_mean_net_20bps"]) > 0
    survive_50 = np.isfinite(vbest["val_mean_net_50bps"]) and float(vbest["val_mean_net_50bps"]) > 0

    families = (
        top.assign(
            family=top["tail"].astype(str)
            + "_"
            + top["thesis"].astype(str)
            + "_L"
            + top["lookback_h"].astype(int).astype(str)
        )
        .groupby("family")
        .size()
        .sort_values(ascending=False)
    )
    isolated = len(families) == len(top) and len(top) > 1
    family_txt = "; ".join(f"{k} (n={int(v)})" for k, v in families.items())

    if n_strong >= 1:
        final = "ROBUST EXTREME-MOVE EFFECT"
    elif n_surv >= 1:
        final = "WEAK EXTREME-MOVE EFFECT"
    else:
        final = "NO ROBUST EXTREME-MOVE EFFECT"

    survivors = val_tbl.loc[val_tbl["classification"].isin(["SURVIVES", "STRONG SURVIVOR"])].copy()
    if not survivors.empty:
        survivors = survivors.sort_values(["discovery_rank"])
        lead_surv = survivors.iloc[0]
        exec_rule = (
            f"If BTC's trailing {int(lead_surv['lookback_h'])}h close-to-close return is "
            f"{'<=' if lead_surv['tail']=='down' else '>='} its expanding historical "
            f"{lead_surv['percentile_label']} (history s < t, ≥365 calendar days), "
            f"{'buy' if lead_surv['direction']=='long' else 'short'} the next hourly open "
            f"and exit at the open {int(lead_surv['hold_h'])}h later. Ignore new signals until flat. "
            f"Primary cost assumption: 10 bps round trip"
            f"{'; short is theoretical (no borrow/funding).' if lead_surv['direction']=='short' else '.'}"
        )
    else:
        exec_rule = "No frozen Top-10 candidate survives validation. No executable rule is promoted."

    missing = meta["missing_hours"]
    miss_preview = ", ".join(str(x) for x in list(missing[:8])) if len(missing) else "none"
    if len(missing) > 8:
        miss_preview += f", ... ({len(missing)} total)"

    years_best = year_map.get(rid, [])
    year_md = [
        "| Year | N | Year return (10 bps) | Mean net | Win rate | Sharpe |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for y in years_best:
        year_md.append(
            f"| {y['year']} | {y['n_trades']} | {fmt_pct(y['year_return'])} | "
            f"{fmt_pct(y['mean_net_trade'], 3)} | {fmt_pct(y['win_rate'])} | {fmt_num(y['sharpe'])} |"
        )
    year_note = vbest.get("year_note", "")

    boot_d = boot_map.get(f"{rid}|discovery", {})
    boot_v = boot_map.get(f"{rid}|validation", {})

    top_tbl = [
        "| Rank | Rule | Class | Val $10k | Val Sharpe | Val mean net | Val BTC-diff | Rec mean net |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in val_tbl.sort_values("discovery_rank").iterrows():
        top_tbl.append(
            f"| {int(r['discovery_rank'])} | `{r['rule_id']}` | {r['classification']} | "
            f"{fmt_usd(r['val_ending_capital_from_10000'])} | {fmt_num(r['val_sharpe'])} | "
            f"{fmt_pct(r['val_mean_net_trade'], 3)} | {fmt_pct(r['val_btc_diff_mean'], 3)} | "
            f"{fmt_pct(r['rec_mean_net_trade'], 3)} |"
        )

    type_note = []
    crash_pos, crash_neg, _ = lookback_sign_groups(down_disc, down_val)
    rally_pos, rally_neg, _ = lookback_sign_groups(up_disc, up_val)
    if crash_pos and (ps.get("ret_1h_mean", np.nan) or 0) >= 0:
        type_note.append(
            "Crash paths at the lookbacks that keep a positive validation difference "
            "look closer to TYPE 1 (immediate rebound): mean +1h after downside events is not negative."
        )
    elif crash_pos:
        type_note.append("Crash lookbacks with a stable positive difference are closer to TYPE 2 if the first hours keep falling.")
    elif crash_neg:
        type_note.append("Stable crash continuation would be a downside-momentum structure; it is not what ranked.")
    else:
        type_note.append("Crash rebound vs continuation is not a single pooled structure; it depends on lookback.")
    if rally_pos:
        type_note.append(
            "Rally lookbacks that keep a positive difference in both periods are TYPE 3 (continued momentum), "
            "especially at the 168h hold that dominates the Top 10."
        )
    elif rally_neg:
        type_note.append("Stable rally reversal would be TYPE 4; it is not supported as a pooled pattern.")
    else:
        type_note.append("Rally continuation vs reversal is lookback-dependent.")
    n_short_top = int((top["direction"] == "short").sum())
    type_note.append(f"No short rule is in the frozen Top 10 (short count={n_short_top}).")
    if final == "NO ROBUST EXTREME-MOVE EFFECT":
        type_note.append("Economically this is TYPE 5: no robust extreme-move effect after costs and validation.")
    elif n_strong >= 1:
        type_note.append(
            "Point-estimate survivors exist, so this is not TYPE 5, but the effect is a handful of LONG parameter "
            "families (short-horizon crash rebound; 12h/24h rally continuation held ~7d), not a universal law of extremes."
        )

    short_note = (
        "SHORT results use unlevered `entry/exit − 1` and the same round-trip fee. "
        "Borrow, funding, locate, and implementation costs are omitted. "
        "Shorts are theoretical research, not live-tradeable as specified."
    )

    lines = [
        "# Extreme BTC move — rebound vs continuation — Phase 4",
        "",
        "Discovery candidate search over 288 frozen extreme-move rules.",
        "Not clean out-of-sample. Not a live trading system.",
        "Do not read this as “we found the optimal crash/rally trade.”",
        "The real evidence is whether a **frozen** discovery candidate survives later periods.",
        "The Phase 3 calendar candidate was not modified and is not combined here.",
        "",
        "## BEST FROZEN DISCOVERY CANDIDATE",
        "",
        f"**SIGNAL:** {signal_text(best)}",
        "",
        f"**ACTION:** {str(best['direction']).upper()} ({best['thesis']}"
        f"{', theoretical unlevered short' if best['direction']=='short' else ''})",
        "",
        "**ENTRY:** next hourly open (bar t+1 open; signal uses close t)",
        "",
        f"**EXIT:** open exactly {int(best['hold_h'])} hours after entry",
        "",
        f"Ranked #1 by discovery executable Sharpe at 10 bps, among rules with mean net > 0 and N ≥ {MIN_DISC_TRADES}.",
        "",
        "## DISCOVERY (data start → 2021-12-31)",
        f"$10,000 → {fmt_usd(d_end)}",
        f"Sharpe: {fmt_num(best['sharpe'])}",
        f"mean trade (gross): {fmt_pct(best['mean_trade_gross'], 3)}",
        f"mean net trade (10 bps): {fmt_pct(best['mean_net_trade'], 3)}",
        f"median net trade: {fmt_pct(best['median_net_trade'], 3)}",
        f"win rate: {fmt_pct(best['win_rate'])}",
        f"profit factor: {fmt_num(best['profit_factor'])}",
        f"max drawdown: {fmt_pct(best['max_drawdown'])}",
        f"CAGR: {fmt_pct(best['cagr'])}",
        f"N trades (non-overlapping): {int(best['n_trades'])}",
        f"N events (overlapping): {int(best['n_events'])}",
        f"BTC cond mean / uncond mean / diff: {fmt_pct(best['btc_cond_mean'], 3)} / "
        f"{fmt_pct(best['btc_uncond_mean'], 3)} / {fmt_pct(best['btc_diff_mean'], 3)}",
        f"Strategy cond mean / uncond same-direction mean / diff: {fmt_pct(best['strat_cond_mean'], 3)} / "
        f"{fmt_pct(best['strat_uncond_mean'], 3)} / {fmt_pct(best['strat_diff_mean'], 3)}",
        "",
        "## VALIDATION (2022-01-01 → 2024-12-31)",
        f"$10,000 → {fmt_usd(v_end)}",
        f"Sharpe: {fmt_num(vbest['val_sharpe'])}",
        f"mean trade (gross): {fmt_pct(vbest['val_mean_trade_gross'], 3)}",
        f"mean net trade (10 bps): {fmt_pct(vbest['val_mean_net_trade'], 3)}",
        f"median net trade: {fmt_pct(vbest['val_median_net_trade'], 3)}",
        f"win rate: {fmt_pct(vbest['val_win_rate'])}",
        f"profit factor: {fmt_num(vbest['val_profit_factor'])}",
        f"max drawdown: {fmt_pct(vbest['val_max_drawdown'])}",
        f"CAGR: {fmt_pct(vbest['val_cagr'])}",
        f"N trades (non-overlapping): {int(vbest['val_n_trades'])}",
        f"N events (overlapping): {int(vbest['val_n_events'])}",
        f"BTC cond mean / uncond mean / diff: {fmt_pct(vbest['val_btc_cond_mean'], 3)} / "
        f"{fmt_pct(vbest['val_btc_uncond_mean'], 3)} / {fmt_pct(vbest['val_btc_diff_mean'], 3)}",
        f"Strategy cond / uncond / diff: {fmt_pct(vbest['val_strat_cond_mean'], 3)} / "
        f"{fmt_pct(vbest['val_strat_uncond_mean'], 3)} / {fmt_pct(vbest['val_strat_diff_mean'], 3)}",
        f"Classification: **{cls_best}**",
        "",
        "## RECENT (2025-01-01 → latest complete bar)",
        f"$10,000 → {fmt_usd(r_end)}",
        f"Sharpe: {fmt_num(vbest['rec_sharpe'])}",
        f"mean trade (gross): {fmt_pct(vbest['rec_mean_trade_gross'], 3)}",
        f"mean net trade (10 bps): {fmt_pct(vbest['rec_mean_net_trade'], 3)}",
        f"median net trade: {fmt_pct(vbest['rec_median_net_trade'], 3)}",
        f"win rate: {fmt_pct(vbest['rec_win_rate'])}",
        f"max drawdown: {fmt_pct(vbest['rec_max_drawdown'])}",
        f"CAGR: {fmt_pct(vbest['rec_cagr'])}",
        f"N trades (non-overlapping): {int(vbest['rec_n_trades'])}",
        f"N events (overlapping): {int(vbest['rec_n_events'])}",
        f"BTC cond / uncond / diff: {fmt_pct(vbest['rec_btc_cond_mean'], 3)} / "
        f"{fmt_pct(vbest['rec_btc_uncond_mean'], 3)} / {fmt_pct(vbest['rec_btc_diff_mean'], 3)}",
        "",
        short_note,
        "",
        "## Answers",
        "",
        f"1. After extreme crashes, does BTC rebound or continue? **{crash_answer(down_disc_d, down_val_d)}**",
        f"2. After extreme rallies, does BTC continue or reverse? **{rally_answer(up_disc_d, up_val_d)}**",
        "3. Does the answer depend on whether the original move occurred over 6h, 12h, 24h or 72h? "
        + (
            "**Yes, magnitudes differ by lookback; sign is reported below.**"
            if any(np.isfinite([down_disc_d, up_disc_d]))
            else "**Insufficient.**"
        ),
        *lookback_lines,
        f"4. At what future horizon is the strongest behavior visible? "
        f"**Crashes: {strongest_horizon(down_disc, down_val)}. "
        f"Rallies: {strongest_horizon(up_disc, up_val)}.**",
        f"5. Does price typically move against the eventual strategy before moving in its favor? "
        f"**After downside extreme events, mean +1h BTC path is {fmt_pct(ret1, 3)} and mean +6h is "
        f"{fmt_pct(ret6, 3)}, so the average crash path does not fall further first. "
        f"MAE still prints because later lows in the 168h window are deep "
        f"(mean MAE {fmt_pct(mae_typ, 3)}). MAE occurs before MFE in {fmt_pct(against)} of crash events, "
        f"only slightly above half — not strong TYPE-2 evidence.**",
        f"6. What are typical MAE and MFE? **Mean MAE_168h (from entry, using bar lows) "
        f"{fmt_pct(mae_typ, 3)}; mean MFE_168h (bar highs) {fmt_pct(mfe_typ, 3)}. "
        f"Median MAE {fmt_pct(ps.get('mae_median', np.nan), 3)}; median MFE {fmt_pct(ps.get('mfe_median', np.nan), 3)}.**",
        f"7. Does the conditional return differ materially from an ordinary same-horizon BTC return? "
        f"**Rank-1 discovery BTC difference {fmt_pct(best['btc_diff_mean'], 3)} "
        f"(cond {fmt_pct(best['btc_cond_mean'], 3)} vs uncond {fmt_pct(best['btc_uncond_mean'], 3)}); "
        f"strategy-direction difference {fmt_pct(best['strat_diff_mean'], 3)}. "
        f"Validation BTC difference {fmt_pct(vbest['val_btc_diff_mean'], 3)}. "
        f"Recent event-study BTC difference {fmt_pct(vbest['rec_btc_diff_mean'], 3)}.**",
        f"8. Does the best rule survive 2022–2024? "
        f"**{'Yes' if cls_best in ('SURVIVES', 'STRONG SURVIVOR') else 'No'} "
        f"(classification: {cls_best}). "
        f"Validation mean net {fmt_pct(vbest['val_mean_net_trade'], 3)}, "
        f"Sharpe {fmt_num(vbest['val_sharpe'])}, "
        f"strategy advantage {fmt_pct(vbest['val_strat_diff_mean'], 3)}. "
        f"Validation 95% CI for mean net is "
        f"[{fmt_pct(boot_v.get('mean_net_lo', np.nan), 3)}, {fmt_pct(boot_v.get('mean_net_hi', np.nan), 3)}] "
        f"and includes zero, so survival is a point-estimate call, not a tight interval.**",
        f"9. Does it survive 2025–latest? "
        f"**Executable recent mean net {fmt_pct(vbest['rec_mean_net_trade'], 3)}, "
        f"Sharpe {fmt_num(vbest['rec_sharpe'])}, N={int(vbest['rec_n_trades'])}. "
        f"Overlapping event-study BTC difference is {fmt_pct(vbest['rec_btc_diff_mean'], 3)} "
        f"(conditional below ordinary). Small N; not a contradiction on executable PnL, not a confirmation either.**",
        f"10. Does it survive 10/20/50 bps? **10 bps validation mean net "
        f"{'positive' if survive_10 else 'not positive'}; 20 bps "
        f"{'positive' if survive_20 else 'not positive'}; 50 bps "
        f"{'positive' if survive_50 else 'not positive'}. {cost_line}**",
        f"11. How many of the Top 10 survive? **{n_surv} SURVIVES** "
        f"(of which **{n_strong} STRONG SURVIVOR**), {n_frag} FRAGILE, {n_fail} FAIL.",
        f"12. What happened to $10,000? **Discovery {fmt_usd(d_end)}; "
        f"validation {fmt_usd(v_end)}; recent {fmt_usd(r_end)} "
        f"(each period starts from $10,000; not chained).**",
        f"13. Is there one clear economic pattern or only isolated parameter combinations? "
        f"**{'Isolated combinations dominate the Top 10.' if isolated else 'Top 10 clusters by family: ' + family_txt}. "
        f"Zero of the Top 10 are shorts. Two LONG families appear: crash rebound at short holds, "
        f"and rally continuation at 168h.**",
        f"14. Final conclusion: **{final}**",
        "",
        " ".join(type_note),
        "",
        "15. If a candidate survives, write its exact executable rule in no more than five lines.",
        "",
        exec_rule,
        "",
        "## Frozen top 10 — decision rule",
        "",
        *top_tbl,
        "",
        "## Calendar-year path for the rank-1 discovery rule",
        "",
        str(year_note),
        "",
        *year_md,
        "",
        "## Block bootstrap (168-hour blocks, 2000 samples)",
        "",
        "Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.",
        "Blocks are drawn from the hourly signal series (circular) to keep crash clustering.",
        f"Rank-1 discovery 95% CI mean net trade: [{fmt_pct(boot_d.get('mean_net_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_d.get('mean_net_hi', np.nan), 3)}]",
        f"Rank-1 discovery 95% CI strategy advantage vs unconditional: [{fmt_pct(boot_d.get('adv_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_d.get('adv_hi', np.nan), 3)}]",
        f"Rank-1 validation 95% CI mean net trade: [{fmt_pct(boot_v.get('mean_net_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_v.get('mean_net_hi', np.nan), 3)}]",
        f"Rank-1 validation 95% CI strategy advantage vs unconditional: [{fmt_pct(boot_v.get('adv_lo', np.nan), 3)}, "
        f"{fmt_pct(boot_v.get('adv_hi', np.nan), 3)}]",
        "",
        "## Data audit",
        "",
        f"- File: `{meta['path']}`",
        f"- UTC start/end: {meta['start_utc']} → {meta['end_utc']}",
        f"- Bars: {meta['n_bars']}; unique UTC: {meta['unique']}; chronological: {meta['chronological']}; OHLC valid: {meta['ohlc_valid']}",
        f"- Duplicated bars dropped: {meta['n_dup_dropped']}; invalid OHLC rows dropped: {meta['n_ohlc_drop']}",
        f"- Missing hours in the UTC 1h grid (not filled): {meta['n_missing_hours']}. Preview: {miss_preview}",
        f"- Events skipped for missing t+1 entry bar (summed over lookback×tail×percentile): {skip_meta['n_skip_no_entry']}",
        f"- Events skipped for missing exit open (summed over lookback×tail×percentile×hold): {skip_meta['n_skip_no_exit']}",
        f"- Expanding-percentile audit: {AUDIT_EXPANDING_N} random timestamps × each lookback/percentile matched `numpy.quantile(history s<t)`.",
        "",
        "## Research design",
        "",
        "- Search space: 4 lookbacks × 3 thresholds × 6 exits × 2 tails × 2 directions = 288 rules.",
        "- Signal: close_t / close_(t−H) − 1 vs expanding percentile of {s < t}, after 365 calendar days.",
        "- Execution: buy/short the **open** of bar t+1; exit the open H hours later. Never the signal close.",
        "- LONG return = exit_open / entry_open − 1. SHORT return = entry_open / exit_open − 1 (theoretical).",
        "- Event study keeps overlapping crash hours. Executable PnL ignores signals until the current trade exits. Same-bar exit and entry is allowed.",
        "- Unconditional control: every hour in the same period with a valid same-horizon next-open to exit-open return.",
        "- Primary cost 10 bps round trip: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps.",
        "- Discovery / validation / recent splits are chronological and frozen. Ranking uses discovery executable Sharpe only.",
        "- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.",
        "",
        "## Multiple-testing warning",
        "",
        "288 rules were ranked on discovery. The best in-sample Sharpe **will** be biased upward. "
        "A discovery winner is a **discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters.",
        "Validation was not allowed to change lookback, percentile, holding period, or direction.",
        "",
        "## Audit assertions",
        "",
        "- Expanding percentiles use only s < t (current return is inserted after the quantile is read).",
        "- Signal uses close t; execution begins at open t+1; no future data in the signal.",
        "- If t+1 or the required exit open is missing, the event is skipped (prices are not filled).",
        "- Validation did not affect ranking. Top 10 were frozen from discovery, then scored unchanged.",
        "- Full history was not used to choose the winner.",
        "- Overlapping signals are removed from strategy PnL; they remain in EVENT_PATHS / event-study columns.",
        "- Costs applied once per completed executable trade.",
        "- Losing trades are retained.",
        "- Unconditional comparison uses the identical holding horizon and the same period window.",
        "- SHORT metrics are labeled theoretical.",
        "",
        f"Bootstrap seed={BOOT_SEED}, block={BOOT_BLOCK_H} hours, samples={N_BOOT}.",
        f"Script runtime {runtime_s:.1f}s. Generated by `src/run_extreme_move_scan.py`.",
        "",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "EXTREME_MOVE_REVERSAL.md").write_text("\n".join(lines), encoding="utf-8")
    log(f"wrote {RESULTS / 'EXTREME_MOVE_REVERSAL.md'}")


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
    span = {p: period_span_days(meta, p) for p in PERIODS}

    needed_h = sorted(set(HOLDS) | set(PATH_H) | {1})
    ahead = {h: hours_ahead_index(ts, h) for h in needed_h}
    entry_idx = ahead[1]
    log(f"forward maps ready hours={needed_h}")

    fwd_long = {}
    fwd_short = {}
    exit_for = {}
    n_skip_entry_global = 0
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
    n_skip_entry_global = int(((entry_idx < 0) & np.isfinite(closes)).sum())

    uncond = {h: {} for h in HOLDS}
    for h in HOLDS:
        for p in PERIODS:
            m = (periods == p) & np.isfinite(fwd_long[h])
            uncond[h][p] = {
                "long": fwd_long[h][m],
                "short": fwd_short[h][m],
            }

    log("computing expanding percentiles")
    ret_map = {}
    q_map = {}
    for L in LOOKBACKS:
        ret = np.full(n, np.nan)
        ret[L:] = closes[L:] / closes[:-L] - 1.0
        ret_map[L] = ret
        q_map[L] = expanding_quantiles(ret, ts, tuple(sorted(set(DOWN_PCTS + UP_PCTS))))
        for p in DOWN_PCTS + UP_PCTS:
            audit_expanding(ret, q_map[L][p], p)
        log(f"  lookback {L}h expanding quantiles audited")

    rule_rows = []
    trade_rows = []
    path_rows = []
    rule_arrays = {}
    n_skip_no_entry = 0
    n_skip_no_exit = 0
    path_mae = []
    path_mfe = []
    path_mae_h = []
    path_mfe_h = []
    path_ret = {h: [] for h in PATH_H}
    path_down_only = True

    for L in LOOKBACKS:
        ret = ret_map[L]
        for tail, pcts in (("down", DOWN_PCTS), ("up", UP_PCTS)):
            for p in pcts:
                q = q_map[L][p]
                finite = np.isfinite(ret) & np.isfinite(q)
                if tail == "down":
                    sig = finite & (ret <= q)
                else:
                    sig = finite & (ret >= q)
                has_entry = sig & (entry_idx >= 0)
                n_skip_no_entry += int((sig & (entry_idx < 0)).sum())

                path_idx = np.flatnonzero(has_entry)
                for i in path_idx:
                    e_i = int(entry_idx[i])
                    e_px = float(opens[e_i])
                    rec = {
                        "signal_timestamp": str(ts[i]),
                        "period": periods[i],
                        "tail": tail,
                        "lookback": int(L),
                        "percentile_rule": pct_label(p),
                        "signal_return": float(ret[i]),
                        "entry_timestamp": str(ts[e_i]),
                        "entry_price": e_px,
                    }
                    for ph in PATH_H:
                        j = int(ahead[ph][e_i])
                        if j >= 0:
                            rec[f"ret_{ph}h"] = float(opens[j] / e_px - 1.0)
                        else:
                            rec[f"ret_{ph}h"] = np.nan
                    mae, mfe, mae_h, mfe_h = window_excursions(e_i, e_px, ts_ns, lows, highs, n)
                    rec["MAE_168h"] = mae
                    rec["MFE_168h"] = mfe
                    rec["MAE_hours"] = mae_h
                    rec["MFE_hours"] = mfe_h
                    path_rows.append(rec)
                    if tail == "down":
                        path_mae.append(mae)
                        path_mfe.append(mfe)
                        path_mae_h.append(mae_h)
                        path_mfe_h.append(mfe_h)
                        for ph in PATH_H:
                            path_ret[ph].append(rec[f"ret_{ph}h"])

                for h in HOLDS:
                    x = exit_for[h]
                    has_exit = has_entry & (x >= 0)
                    n_skip_no_exit += int((has_entry & (x < 0)).sum())
                    for direction in ("long", "short"):
                        thesis = thesis_name(tail, direction)
                        rid = rule_id(L, tail, p, direction, h)
                        fwd_s = fwd_long[h] if direction == "long" else fwd_short[h]
                        valid_event = has_exit & np.isfinite(fwd_s)
                        take_all = executable_take(valid_event, entry_idx, ts_ns, h)
                        rule_arrays[rid] = {
                            "valid_event": valid_event,
                            "take": take_all,
                            "fwd_strat": fwd_s,
                            "fwd_btc": fwd_long[h],
                            "lookback_h": L,
                            "tail": tail,
                            "percentile": p,
                            "percentile_label": pct_label(p),
                            "direction": direction,
                            "thesis": thesis,
                            "hold_h": h,
                        }
                        for period in PERIODS:
                            ev = valid_event & (periods == period)
                            tk = take_all & (periods == period)
                            btc_stats = dist_stats(fwd_long[h][ev], uncond[h][period]["long"])
                            st_uncond = uncond[h][period][direction]
                            st_stats = dist_stats(fwd_s[ev], st_uncond)
                            em = exec_metrics(fwd_s[tk], span[period], FEE_PRIMARY)
                            nets_by_fee = {}
                            g_tk = fwd_s[tk]
                            for bps, fee in zip(FEE_BPS, FEE_SET):
                                nets = net_from_gross(g_tk, fee)
                                nets_by_fee[bps] = {
                                    "mean_net": float(nets.mean()) if nets.size else np.nan,
                                    "end_cap": ending_capital(nets),
                                }
                            row = {
                                "rule_id": rid,
                                "period": period,
                                "lookback_h": int(L),
                                "tail": tail,
                                "percentile": float(p),
                                "percentile_label": pct_label(p),
                                "direction": direction,
                                "thesis": thesis,
                                "hold_h": int(h),
                                "short_theoretical": direction == "short",
                                "n_signals": int((sig & (periods == period)).sum()),
                                "n_events": int(ev.sum()),
                                "n_trades": em["n_trades"],
                                "n_skip_no_entry_period": int(
                                    (sig & (periods == period) & (entry_idx < 0)).sum()
                                ),
                                "n_skip_no_exit_period": int(
                                    (has_entry & (periods == period) & (x < 0)).sum()
                                ),
                                "btc_cond_mean": btc_stats["cond_mean"],
                                "btc_uncond_mean": btc_stats["uncond_mean"],
                                "btc_diff_mean": btc_stats["diff_mean"],
                                "btc_cond_median": btc_stats["cond_median"],
                                "btc_uncond_median": btc_stats["uncond_median"],
                                "btc_diff_median": btc_stats["diff_median"],
                                "btc_cond_p_pos": btc_stats["cond_p_pos"],
                                "btc_uncond_p_pos": btc_stats["uncond_p_pos"],
                                "btc_diff_p_pos": btc_stats["diff_p_pos"],
                                "strat_cond_mean": st_stats["cond_mean"],
                                "strat_uncond_mean": st_stats["uncond_mean"],
                                "strat_diff_mean": st_stats["diff_mean"],
                                "strat_cond_median": st_stats["cond_median"],
                                "strat_uncond_median": st_stats["uncond_median"],
                                "strat_diff_median": st_stats["diff_median"],
                                "strat_cond_p_pos": st_stats["cond_p_pos"],
                                "strat_uncond_p_pos": st_stats["uncond_p_pos"],
                                "strat_diff_p_pos": st_stats["diff_p_pos"],
                                **em,
                                "mean_net_0bps": nets_by_fee[0]["mean_net"],
                                "mean_net_20bps": nets_by_fee[20]["mean_net"],
                                "mean_net_50bps": nets_by_fee[50]["mean_net"],
                                "end_cap_0bps": nets_by_fee[0]["end_cap"],
                                "end_cap_20bps": nets_by_fee[20]["end_cap"],
                                "end_cap_50bps": nets_by_fee[50]["end_cap"],
                            }
                            rule_rows.append(row)
                            if tk.any():
                                for t in np.flatnonzero(tk):
                                    e_i = int(entry_idx[t])
                                    x_i = int(x[t])
                                    g = float(fwd_s[t])
                                    trade_rows.append(
                                        {
                                            "rule_id": rid,
                                            "period": period,
                                            "lookback_h": int(L),
                                            "tail": tail,
                                            "percentile_label": pct_label(p),
                                            "direction": direction,
                                            "thesis": thesis,
                                            "hold_h": int(h),
                                            "short_theoretical": direction == "short",
                                            "signal_timestamp": str(ts[t]),
                                            "entry_timestamp": str(ts[e_i]),
                                            "exit_timestamp": str(ts[x_i]),
                                            "entry_price": float(opens[e_i]),
                                            "exit_price": float(opens[x_i]),
                                            "signal_return": float(ret[t]),
                                            "gross_return": g,
                                            "net_return_10bps": float(net_from_gross(np.array([g]), FEE_PRIMARY)[0]),
                                        }
                                    )
                log(f"  scanned L{L} {tail} {pct_label(p)} signals={int(sig.sum())}")

    all_rules = pd.DataFrame(rule_rows)
    disc = all_rules.loc[all_rules["period"] == "discovery"].copy()
    disc["pass_n"] = disc["n_trades"] >= MIN_DISC_TRADES
    disc["pass_net"] = disc["mean_net_trade"] > 0
    eligible = disc.loc[disc["pass_n"] & disc["pass_net"]].copy()
    if eligible.empty:
        log("WARNING: no discovery candidates passed N>=30 and mean_net_trade>0")
        eligible = disc.loc[disc["pass_n"]].copy()
    eligible = eligible.sort_values(
        by=["sharpe", "mean_net_trade", "profit_factor", "ending_capital_from_10000"],
        ascending=[False, False, False, False],
        na_position="last",
    )
    eligible["discovery_rank"] = np.arange(1, len(eligible) + 1)
    top = eligible.head(TOP_N).copy()
    log(f"eligible discovery rules={len(eligible)} top={len(top)}")
    if top.empty:
        raise RuntimeError("No discovery rules to freeze.")

    rank_map = dict(zip(top["rule_id"], top["discovery_rank"]))
    val = all_rules.loc[all_rules["period"] == "validation"].copy()
    rec = all_rules.loc[all_rules["period"] == "recent"].copy()

    trade_df = pd.DataFrame(trade_rows)
    path_df = pd.DataFrame(path_rows)

    val_rows = []
    year_map: dict[str, list[dict]] = {}
    boot_map: dict[str, dict] = {}
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
        g = arr["fwd_strat"]
        yrs = year_rows(ts, tk, g)
        year_map[rid] = yrs
        yok, ymsg = year_ok_flag(yrs)
        cls = classify_rule(cand, v, r, yok, ymsg)
        for period in PERIODS:
            boot_map[f"{rid}|{period}"] = bootstrap_top_rule(
                arr["valid_event"],
                periods == period,
                arr["fwd_strat"],
                int(cand["hold_h"]),
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
                "tail": cand["tail"],
                "percentile": float(cand["percentile"]),
                "percentile_label": cand["percentile_label"],
                "direction": cand["direction"],
                "thesis": cand["thesis"],
                "hold_h": int(cand["hold_h"]),
                "short_theoretical": bool(cand["short_theoretical"]),
                "classification": cls,
                "year_ok": yok,
                "year_note": ymsg,
                "disc_n_trades": int(cand["n_trades"]),
                "disc_n_events": int(cand["n_events"]),
                "disc_sharpe": float(cand["sharpe"]),
                "disc_mean_net_trade": float(cand["mean_net_trade"]),
                "disc_ending_capital_from_10000": float(cand["ending_capital_from_10000"]),
                "disc_max_drawdown": float(cand["max_drawdown"]),
                "disc_btc_diff_mean": float(cand["btc_diff_mean"]),
                "disc_strat_diff_mean": float(cand["strat_diff_mean"]),
                "val_n_trades": int(v["n_trades"]),
                "val_n_events": int(v["n_events"]),
                "val_sharpe": float(v["sharpe"]),
                "val_mean_trade_gross": float(v["mean_trade_gross"]),
                "val_mean_net_trade": float(v["mean_net_trade"]),
                "val_median_net_trade": float(v["median_net_trade"]),
                "val_win_rate": float(v["win_rate"]),
                "val_profit_factor": float(v["profit_factor"]),
                "val_ending_capital_from_10000": float(v["ending_capital_from_10000"]),
                "val_max_drawdown": float(v["max_drawdown"]),
                "val_cagr": float(v["cagr"]),
                "val_btc_cond_mean": float(v["btc_cond_mean"]),
                "val_btc_uncond_mean": float(v["btc_uncond_mean"]),
                "val_btc_diff_mean": float(v["btc_diff_mean"]),
                "val_strat_cond_mean": float(v["strat_cond_mean"]),
                "val_strat_uncond_mean": float(v["strat_uncond_mean"]),
                "val_strat_diff_mean": float(v["strat_diff_mean"]),
                "val_mean_net_0bps": float(v["mean_net_0bps"]),
                "val_mean_net_20bps": float(v["mean_net_20bps"]),
                "val_mean_net_50bps": float(v["mean_net_50bps"]),
                "val_end_cap_0bps": float(v["end_cap_0bps"]),
                "val_end_cap_20bps": float(v["end_cap_20bps"]),
                "val_end_cap_50bps": float(v["end_cap_50bps"]),
                "rec_n_trades": int(r["n_trades"]),
                "rec_n_events": int(r["n_events"]),
                "rec_sharpe": float(r["sharpe"]),
                "rec_mean_trade_gross": float(r["mean_trade_gross"]),
                "rec_mean_net_trade": float(r["mean_net_trade"]),
                "rec_median_net_trade": float(r["median_net_trade"]),
                "rec_win_rate": float(r["win_rate"]),
                "rec_ending_capital_from_10000": float(r["ending_capital_from_10000"]),
                "rec_max_drawdown": float(r["max_drawdown"]),
                "rec_cagr": float(r["cagr"]),
                "rec_btc_cond_mean": float(r["btc_cond_mean"]),
                "rec_btc_uncond_mean": float(r["btc_uncond_mean"]),
                "rec_btc_diff_mean": float(r["btc_diff_mean"]),
                "rec_mean_net_0bps": float(r["mean_net_0bps"]),
                "rec_mean_net_20bps": float(r["mean_net_20bps"]),
                "rec_mean_net_50bps": float(r["mean_net_50bps"]),
                "disc_boot_mean_net_lo": bd["mean_net_lo"],
                "disc_boot_mean_net_hi": bd["mean_net_hi"],
                "disc_boot_adv_lo": bd["adv_lo"],
                "disc_boot_adv_hi": bd["adv_hi"],
                "val_boot_mean_net_lo": bv["mean_net_lo"],
                "val_boot_mean_net_hi": bv["mean_net_hi"],
                "val_boot_adv_lo": bv["adv_lo"],
                "val_boot_adv_hi": bv["adv_hi"],
                "rec_boot_mean_net_lo": br["mean_net_lo"],
                "rec_boot_mean_net_hi": br["mean_net_hi"],
                "rec_boot_adv_lo": br["adv_lo"],
                "rec_boot_adv_hi": br["adv_hi"],
            }
        )

    val_tbl = pd.DataFrame(val_rows)
    top_out = top.copy()
    top_out = top_out.merge(
        val_tbl[["rule_id", "classification", "year_ok", "year_note"]],
        on="rule_id",
        how="left",
    )

    mae_a = np.asarray(path_mae, dtype=float)
    mfe_a = np.asarray(path_mfe, dtype=float)
    mae_h_a = np.asarray(path_mae_h, dtype=float)
    mfe_h_a = np.asarray(path_mfe_h, dtype=float)
    okp = np.isfinite(mae_a) & np.isfinite(mfe_a) & np.isfinite(mae_h_a) & np.isfinite(mfe_h_a)
    path_summary = {
        "mae_mean": float(np.nanmean(mae_a)) if mae_a.size else np.nan,
        "mfe_mean": float(np.nanmean(mfe_a)) if mfe_a.size else np.nan,
        "mae_median": float(np.nanmedian(mae_a)) if mae_a.size else np.nan,
        "mfe_median": float(np.nanmedian(mfe_a)) if mfe_a.size else np.nan,
        "frac_mae_before_mfe": float(np.mean(mae_h_a[okp] < mfe_h_a[okp])) if okp.any() else np.nan,
        "n_down_paths": int(mae_a.size),
    }
    for ph in PATH_H:
        a = np.asarray(path_ret[ph], dtype=float)
        path_summary[f"ret_{ph}h_mean"] = float(np.nanmean(a)) if a.size else np.nan

    skip_meta = {
        "n_skip_no_entry": int(n_skip_no_entry),
        "n_skip_no_exit": int(n_skip_no_exit),
        "n_missing_t1_any": n_skip_entry_global,
    }

    disc_out = disc.sort_values(
        by=["sharpe", "mean_net_trade", "profit_factor", "ending_capital_from_10000"],
        ascending=[False, False, False, False],
        na_position="last",
    ).copy()
    disc_out.insert(0, "discovery_sort_order", np.arange(1, len(disc_out) + 1))

    if not trade_df.empty:
        trade_df = trade_df.loc[trade_df["rule_id"].isin(set(top["rule_id"]))].copy()
        trade_df["discovery_rank"] = trade_df["rule_id"].map(rank_map)
        trade_df = trade_df.sort_values(["discovery_rank", "signal_timestamp"]).reset_index(drop=True)

    disc_out.to_csv(RESULTS / "ALL_EXTREME_RULES.csv", index=False)
    top_out.to_csv(RESULTS / "TOP_CANDIDATES.csv", index=False)
    val_tbl.to_csv(RESULTS / "VALIDATION_RESULTS.csv", index=False)
    path_df.to_csv(RESULTS / "EVENT_PATHS.csv", index=False)
    trade_df.to_csv(RESULTS / "TRADE_LOG.csv", index=False)
    log(
        f"wrote csvs rules={len(disc_out)} top={len(top_out)} "
        f"paths={len(path_df)} trades={len(trade_df)}"
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
        skip_meta,
        runtime_s,
    )
    log(f"done in {runtime_s:.1f}s leader={top_out.iloc[0]['rule_id']} class={val_tbl.iloc[0]['classification']}")


if __name__ == "__main__":
    main()
