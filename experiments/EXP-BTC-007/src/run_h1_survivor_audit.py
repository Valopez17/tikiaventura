#!/usr/bin/env python3
"""EXP-BTC-007 / H1 survivor audit of frozen L6_down_p1_rebound_long_H6.

EXT-C04: fixed-candidate metrics, costs, year stability, decision gate.
Not a trading edge. Does not authorize capital. Does not reselect.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = EXP_DIR / "SPEC.md"
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-006" / "src"))
sys.path.insert(0, str(REPO))

from run_ext_c02 import (  # noqa: E402
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    FROZEN_TOP10_REL,
    L6_CANDIDATE_ID,
    LOOKBACK_MODE_B,
    audit_expanding,
    behind_indices,
    exact_behind_matches_primitive,
    executable_take,
    expanding_quantiles,
    hours_ahead_index,
    load_bars_csv,
    load_frozen_top10,
    net_from_gross,
    pct_label,
    rule_id,
    sha256_file,
    sharpe_trades,
    take_idx,
    thesis_name,
    trailing_return_from_behind,
)
from temporal.exact_timestamp import as_utc_index, lookback_index  # noqa: E402

EXPERIMENT_ID = "EXP-BTC-007"
HYPOTHESIS_ID = "HYP-BTC-002"
HYPOTHESIS_VERSION = "1"
TASK_ID_SPEC = "EXT-C03"
TASK_ID_GATE = "EXT-C04"
FROZEN_RULE_ID = "L6_down_p1_rebound_long_H6"
LOOKBACK_H = 6
HOLD_H = 6
ENTRY_OFFSET_H = 1
PERCENTILE = 0.01
PERCENTILE_LABEL = "p1"
TAIL = "down"
DIRECTION = "long"
THESIS = "rebound"
LOOKBACK_MODE = LOOKBACK_MODE_B
MIN_HISTORY_CALENDAR_DAYS = 365
DISC_END_UTC = "2022-01-01T00:00:00+00:00"
VAL_END_UTC = "2025-01-01T00:00:00+00:00"
FEE_BPS = (0, 10, 20, 50)
FEE_PRIMARY_BPS = 10
FEE_PRIMARY = 0.0010
START_CAP = 10_000.0
CRYPTO_DAYS = 365.0
HOURS_PER_YEAR = 365.0 * 24.0
AUDIT_EXPANDING_N = 24
PERIODS = ("discovery", "validation", "recent", "full")
GATE_PERIODS = ("discovery", "validation", "recent")
BULL_YEARS = frozenset({2020, 2021, 2022})
VAL_MIN_TRADES = 15
RECENT_N_FLOOR = 5
BOOT_N_MIN = 5
BOOT_PR_THRESHOLD = 0.80
YEAR_POS_MIN = 2
YEAR_CONCENTRATION_MAX = 0.70
FEE_STRESS_BPS = 50

DATASET_REL = "btc_tsmom_replication/btcusdt_1h.csv"
RECTOR_REL = "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md"
EXT_C02_RESULT_REL = (
    "experiments/EXP-BTC-006/RUN-BTC-006-20260902-03/result/RESULT.json"
)

DISCARD = "DISCARD"
INSUFFICIENT = "INSUFFICIENT"
FREEZE = "FREEZE_PROSPECTIVE_RECOMMENDED"
DISPOSITIONS = (DISCARD, INSUFFICIENT, FREEZE)


@dataclass(frozen=True)
class FrozenRule:
    rule_id: str = FROZEN_RULE_ID
    lookback_h: int = LOOKBACK_H
    hold_h: int = HOLD_H
    entry_offset_h: int = ENTRY_OFFSET_H
    percentile: float = PERCENTILE
    percentile_label: str = PERCENTILE_LABEL
    tail: str = TAIL
    direction: str = DIRECTION
    thesis: str = THESIS
    lookback_mode: str = LOOKBACK_MODE
    min_history_calendar_days: int = MIN_HISTORY_CALENDAR_DAYS

    def identity_dict(self) -> dict:
        return asdict(self)


def frozen_rule() -> FrozenRule:
    return FrozenRule()


def assert_rule_id_formula(rule: FrozenRule | None = None) -> str:
    rule = rule if rule is not None else frozen_rule()
    built = rule_id(rule.lookback_h, rule.tail, rule.percentile, rule.direction, rule.hold_h)
    if built != rule.rule_id:
        raise RuntimeError(f"rule_id formula mismatch: built={built} frozen={rule.rule_id}")
    if pct_label(rule.percentile) != rule.percentile_label:
        raise RuntimeError("percentile_label mismatch")
    if thesis_name(rule.tail, rule.direction) != rule.thesis:
        raise RuntimeError("thesis mismatch")
    if rule.lookback_mode != LOOKBACK_MODE_B:
        raise RuntimeError("lookback_mode must be EXACT_TIMESTAMP")
    if rule.direction != "long" or rule.thesis != "rebound" or rule.tail != "down":
        raise RuntimeError("direction/thesis/tail are frozen to LONG rebound")
    return built


def read_phase4_l6_row(path: Path | None = None) -> dict:
    p = path if path is not None else REPO / FROZEN_TOP10_REL
    rows = pd.read_csv(p)
    hit = rows.loc[rows["rule_id"].astype(str) == FROZEN_RULE_ID]
    if hit.empty:
        raise RuntimeError(f"{FROZEN_RULE_ID} absent from {p}")
    r = hit.iloc[0]
    return {
        "rule_id": str(r["rule_id"]),
        "lookback_h": int(r["lookback_h"]),
        "tail": str(r["tail"]),
        "percentile": float(r["percentile"]),
        "percentile_label": str(r["percentile_label"]),
        "direction": str(r["direction"]),
        "thesis": str(r["thesis"]),
        "hold_h": int(r["hold_h"]),
        "discovery_rank": int(r["discovery_rank"]) if "discovery_rank" in r.index else None,
    }


def read_ext_c02_l6_id(path: Path | None = None) -> str:
    p = path if path is not None else REPO / EXT_C02_RESULT_REL
    payload = json.loads(p.read_text(encoding="utf-8"))
    rid = payload.get("l6_candidate_summary", {}).get("rule_id")
    if not rid:
        raise RuntimeError(f"EXP-BTC-006 RESULT.json missing l6_candidate_summary.rule_id: {p}")
    return str(rid)


def assert_frozen_identity(rule: FrozenRule | None = None) -> dict:
    """Read identity from artefacts and assert equality with the spec. No reselection."""
    rule = rule if rule is not None else frozen_rule()
    assert_rule_id_formula(rule)
    top = load_frozen_top10()
    ids = [r["rule_id"] for r in top]
    if FROZEN_RULE_ID not in ids:
        raise RuntimeError("frozen candidate missing from Phase 4 TOP_CANDIDATES.csv")
    if ids != [r["rule_id"] for r in load_frozen_top10()]:
        raise RuntimeError("TOP_CANDIDATES read is not stable")
    phase4 = read_phase4_l6_row()
    ext_c02_id = read_ext_c02_l6_id()
    mismatches = []
    if phase4["rule_id"] != rule.rule_id:
        mismatches.append(("phase4.rule_id", phase4["rule_id"], rule.rule_id))
    if ext_c02_id != rule.rule_id:
        mismatches.append(("ext_c02.rule_id", ext_c02_id, rule.rule_id))
    checks = (
        ("lookback_h", phase4["lookback_h"], rule.lookback_h),
        ("tail", phase4["tail"], rule.tail),
        ("percentile", phase4["percentile"], rule.percentile),
        ("percentile_label", phase4["percentile_label"], rule.percentile_label),
        ("direction", phase4["direction"], rule.direction),
        ("thesis", phase4["thesis"], rule.thesis),
        ("hold_h", phase4["hold_h"], rule.hold_h),
    )
    for name, got, want in checks:
        if name == "percentile":
            if abs(float(got) - float(want)) > 1e-12:
                mismatches.append((name, got, want))
        elif got != want:
            mismatches.append((name, got, want))
    if mismatches:
        raise RuntimeError(f"frozen identity mismatch vs artefacts: {mismatches}")
    if L6_CANDIDATE_ID != rule.rule_id:
        raise RuntimeError("EXP-BTC-006 L6_CANDIDATE_ID drifted")
    return {
        "rule": rule.identity_dict(),
        "phase4": phase4,
        "ext_c02_rule_id": ext_c02_id,
        "top10_ids": ids,
        "reselect_from_288": False,
    }


def _utc_timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    t = pd.Timestamp(value)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    return t


def assign_periods(ts: pd.DatetimeIndex) -> np.ndarray:
    ts = as_utc_index(ts)
    disc = _utc_timestamp(DISC_END_UTC)
    val = _utc_timestamp(VAL_END_UTC)
    out = np.empty(len(ts), dtype=object)
    out[ts < disc] = "discovery"
    out[(ts >= disc) & (ts < val)] = "validation"
    out[ts >= val] = "recent"
    return out


def period_span_days(meta: dict, period: str) -> float:
    start = meta["start_utc"]
    end = meta["end_utc"]
    disc = _utc_timestamp(DISC_END_UTC)
    val = _utc_timestamp(VAL_END_UTC)
    if period == "discovery":
        a, b = start, disc
    elif period == "validation":
        a, b = disc, val
    elif period == "recent":
        a, b = val, end + pd.Timedelta(hours=1)
    else:
        a, b = start, end + pd.Timedelta(hours=1)
    return max(float((b - a).total_seconds() / 86400.0), 1.0)


def fee_from_bps(bps: int) -> float:
    return float(bps) / 10_000.0


def profit_factor(nets: np.ndarray) -> float:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.nan
    gp = float(np.sum(x[x > 0]))
    gl = float(np.sum(np.abs(x[x < 0])))
    if gl > 0:
        return gp / gl
    if gp > 0:
        return float(np.inf)
    return np.nan


def ending_capital(nets: np.ndarray, start_cap: float = START_CAP) -> float:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float(start_cap)
    return float(start_cap * np.prod(1.0 + x))


def finite_gt(x: Any, thresh: float = 0.0) -> bool:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(xf) and xf > thresh)


def finite_ge(x: Any, thresh: float = 0.0) -> bool:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(xf) and xf >= thresh)


def finite_lt(x: Any, thresh: float = 0.0) -> bool:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(xf) and xf < thresh)


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


def summarize_nets(gross: np.ndarray, span_days: float) -> dict:
    g = np.asarray(gross, dtype=float)
    g = g[np.isfinite(g)]
    out: dict[str, Any] = {
        "n_trades": int(g.size),
        "mean_gross": float(g.mean()) if g.size else np.nan,
        "median_gross": float(np.median(g)) if g.size else np.nan,
    }
    for bps in FEE_BPS:
        fee = fee_from_bps(bps)
        nets = net_from_gross(g, fee) if g.size else g
        key = f"{bps}bps"
        out[f"mean_net_{key}"] = float(nets.mean()) if nets.size else np.nan
        out[f"median_net_{key}"] = float(np.median(nets)) if nets.size else np.nan
        out[f"end_cap_{key}"] = ending_capital(nets)
        if bps == FEE_PRIMARY_BPS:
            out["mean_net"] = out[f"mean_net_{key}"]
            out["median_net"] = out[f"median_net_{key}"]
            out["win_rate"] = float(np.mean(nets > 0)) if nets.size else np.nan
            out["profit_factor"] = profit_factor(nets)
            out["trade_sharpe"] = sharpe_trades(nets, span_days, CRYPTO_DAYS)
            if nets.size:
                i_win = int(np.argmax(nets))
                i_loss = int(np.argmin(nets))
                pos = nets[nets > 0]
                neg = nets[nets < 0]
                out["largest_win_net"] = float(nets[i_win])
                out["largest_loss_net"] = float(nets[i_loss])
                out["largest_win_share_of_positive"] = (
                    float(nets[i_win] / pos.sum()) if pos.size and pos.sum() != 0 else np.nan
                )
                out["largest_loss_share_of_negative"] = (
                    float(nets[i_loss] / neg.sum()) if neg.size and neg.sum() != 0 else np.nan
                )
            else:
                out["largest_win_net"] = np.nan
                out["largest_loss_net"] = np.nan
                out["largest_win_share_of_positive"] = np.nan
                out["largest_loss_share_of_negative"] = np.nan
    return out


def build_candidate_arrays(
    df: pd.DataFrame,
    rule: FrozenRule | None = None,
    min_cal_days: int | None = None,
    audit: bool = True,
) -> dict:
    """Exact-timestamp L6 down-p1 long rebound. One rule. No 288-rule scan."""
    rule = rule if rule is not None else frozen_rule()
    assert_rule_id_formula(rule)
    min_cal = int(rule.min_history_calendar_days if min_cal_days is None else min_cal_days)
    ts = as_utc_index(pd.DatetimeIndex(df["ts_utc"]))
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    periods = assign_periods(ts)
    meta = df.attrs.get("meta") or {
        "n_bars": n,
        "n_missing_hours": 0,
        "n_dup_dropped": 0,
        "start_utc": ts[0] if n else None,
        "end_utc": ts[-1] if n else None,
    }
    span = {p: period_span_days(meta, p) for p in PERIODS}
    behind = behind_indices(ts, rule.lookback_h, rule.lookback_mode)
    if not exact_behind_matches_primitive(ts, rule.lookback_h, behind):
        raise RuntimeError("vectorized exact behind disagrees with temporal.exact_timestamp")
    ret = trailing_return_from_behind(closes, behind)
    qmap = expanding_quantiles(ret, ts, (rule.percentile,), min_cal)
    q = qmap[rule.percentile]
    if audit and np.isfinite(q).any() and np.isfinite(ret).any():
        audit_expanding(ret, ts, q, rule.percentile, AUDIT_EXPANDING_N)
    finite = np.isfinite(ret) & np.isfinite(q)
    if rule.tail != "down":
        raise RuntimeError("only down-tail is frozen")
    signal = finite & (ret <= q)
    ahead_entry = hours_ahead_index(ts, rule.entry_offset_h)
    ahead_hold = hours_ahead_index(ts, rule.hold_h)
    entry_idx = ahead_entry
    exit_idx = take_idx(ahead_hold, entry_idx)
    has_entry = signal & (entry_idx >= 0)
    missing_entry = signal & (entry_idx < 0)
    has_exit = has_entry & (exit_idx >= 0)
    missing_exit = has_entry & (exit_idx < 0)
    fwd = np.full(n, np.nan, dtype=float)
    ok_px = (entry_idx >= 0) & (exit_idx >= 0)
    if ok_px.any():
        e_px = opens[entry_idx[ok_px]]
        x_px = opens[exit_idx[ok_px]]
        good = (e_px > 0) & (x_px > 0)
        tmp = np.full(int(ok_px.sum()), np.nan, dtype=float)
        tmp[good] = x_px[good] / e_px[good] - 1.0
        fwd[ok_px] = tmp
    valid_event = has_exit & np.isfinite(fwd)
    take = executable_take(valid_event, entry_idx, ts, rule.hold_h)
    uncond = {}
    for period in GATE_PERIODS:
        m = (periods == period) & np.isfinite(fwd)
        uncond[period] = fwd[m]
    uncond["full"] = fwd[np.isfinite(fwd)]
    return {
        "rule": rule,
        "ts": ts,
        "n": n,
        "opens": opens,
        "closes": closes,
        "periods": periods,
        "meta": meta,
        "span": span,
        "behind": behind,
        "ret": ret,
        "q": q,
        "signal": signal,
        "entry_idx": entry_idx,
        "exit_idx": exit_idx,
        "fwd": fwd,
        "has_entry": has_entry,
        "has_exit": has_exit,
        "missing_entry": missing_entry,
        "missing_exit": missing_exit,
        "valid_event": valid_event,
        "take": take,
        "uncond": uncond,
        "min_cal_days": min_cal,
    }


def iter_taken_trades(bundle: dict) -> list[dict]:
    ts = bundle["ts"]
    periods = bundle["periods"]
    take = bundle["take"]
    entry_idx = bundle["entry_idx"]
    exit_idx = bundle["exit_idx"]
    fwd = bundle["fwd"]
    rows = []
    for t in np.flatnonzero(take):
        t = int(t)
        e_i = int(entry_idx[t])
        x_i = int(exit_idx[t])
        gross = float(fwd[t])
        nets = {bps: float(net_from_gross(np.array([gross]), fee_from_bps(bps))[0]) for bps in FEE_BPS}
        rows.append(
            {
                "signal_idx": t,
                "signal_ts": ts[t],
                "entry_idx": e_i,
                "exit_idx": x_i,
                "entry_ts": ts[e_i],
                "exit_ts": ts[x_i],
                "period": str(periods[t]),
                "year": int(ts[t].year),
                "gross": gross,
                "net_0bps": nets[0],
                "net_10bps": nets[10],
                "net_20bps": nets[20],
                "net_50bps": nets[50],
            }
        )
    return rows


def period_mask_for(bundle: dict, period: str) -> np.ndarray:
    if period == "full":
        return np.ones(bundle["n"], dtype=bool)
    return bundle["periods"] == period


def period_trade_metrics(bundle: dict, period: str) -> dict:
    mask = period_mask_for(bundle, period)
    span = bundle["span"][period]
    sig = bundle["signal"] & mask
    ev = bundle["valid_event"] & mask
    tk = bundle["take"] & mask
    miss_e = bundle["missing_entry"] & mask
    miss_x = bundle["missing_exit"] & mask
    stats = dist_stats(bundle["fwd"][ev], bundle["uncond"][period])
    trade = summarize_nets(bundle["fwd"][tk], span)
    row = {
        "rule_id": bundle["rule"].rule_id,
        "period": period,
        "n_signals": int(sig.sum()),
        "n_events": int(ev.sum()),
        "n_trades": int(tk.sum()),
        "n_skip_no_entry": int(miss_e.sum()),
        "n_skip_no_exit": int(miss_x.sum()),
        "cond_mean": stats["cond_mean"],
        "uncond_mean": stats["uncond_mean"],
        "cond_adv": stats["diff_mean"],
        "span_days": span,
    }
    row.update(trade)
    return row


def yearly_trade_metrics(bundle: dict) -> list[dict]:
    ts = bundle["ts"]
    take = bundle["take"]
    fwd = bundle["fwd"]
    years = ts.year.to_numpy()
    rows = []
    if not take.any():
        return rows
    y_taken = years[take]
    for year in range(int(y_taken.min()), int(y_taken.max()) + 1):
        m = take & (years == year)
        g = fwd[m]
        g = g[np.isfinite(g)]
        if g.size == 0:
            continue
        nets = net_from_gross(g, FEE_PRIMARY)
        days = 366.0 if year % 4 == 0 else 365.0
        year_pnl = float(np.prod(1.0 + nets) - 1.0)
        rows.append(
            {
                "year": int(year),
                "n_trades": int(g.size),
                "mean_net": float(nets.mean()),
                "mean_gross": float(g.mean()),
                "year_pnl": year_pnl,
                "year_return": year_pnl,
                "win_rate": float(np.mean(nets > 0)),
                "trade_sharpe": sharpe_trades(nets, days, CRYPTO_DAYS),
                "ending_capital_from_10000": ending_capital(nets),
                "outside_2020_2022": int(year) not in BULL_YEARS,
            }
        )
    pos = np.array([r["year_pnl"] for r in rows], dtype=float)
    pos_clip = np.clip(pos, 0.0, None)
    denom = float(pos_clip.sum()) if pos_clip.size else 0.0
    for r, pclip in zip(rows, pos_clip):
        r["positive_pnl_contribution"] = float(pclip / denom) if denom > 0 else np.nan
    return rows


def year_stability(years: list[dict]) -> dict:
    if not years:
        return {
            "n_years": 0,
            "n_positive_mean_net": 0,
            "n_positive_outside_2020_2022": 0,
            "max_positive_year_share": np.nan,
            "at_least_two_positive_years": False,
            "at_least_one_positive_outside_2020_2022": False,
            "largest_positive_year_share_lt_70pct": False,
            "note": "no yearly rows",
        }
    pos = [y for y in years if np.isfinite(y["mean_net"]) and y["mean_net"] > 0]
    pnls = np.array([y["year_pnl"] for y in years if np.isfinite(y["year_pnl"])], dtype=float)
    pos_pnls = np.clip(pnls, 0.0, None)
    share = float(pos_pnls.max() / pos_pnls.sum()) if pos_pnls.size and pos_pnls.sum() > 0 else 1.0
    other = [y for y in pos if y["year"] not in BULL_YEARS]
    n_pos = len(pos)
    return {
        "n_years": len(years),
        "n_positive_mean_net": n_pos,
        "n_positive_outside_2020_2022": len(other),
        "max_positive_year_share": share,
        "at_least_two_positive_years": n_pos >= YEAR_POS_MIN,
        "at_least_one_positive_outside_2020_2022": len(other) >= 1,
        "largest_positive_year_share_lt_70pct": bool(
            pos_pnls.size and pos_pnls.sum() > 0 and share < YEAR_CONCENTRATION_MAX
        ),
        "note": (
            f"years_with_positive_mean_net={n_pos}/{len(years)}; "
            f"max_positive_year_share={share:.2f}; "
            f"positive_outside_2020_2022={len(other)}"
        ),
    }


@dataclass
class GateInputs:
    disc_mean_net_10bps: float
    disc_cond_adv: float
    val_mean_net_10bps: float
    val_cond_adv: float
    val_mtm_sharpe: float
    val_n_trades: int
    rec_n_trades: int
    rec_mean_net_10bps: float
    rec_cond_adv: float
    rec_mtm_sharpe: float
    val_mean_net_20bps: float
    val_bootstrap_pr_mean_net_gt_0: float
    val_bootstrap_status: str
    n_positive_mean_net_years: int
    n_positive_years_outside_2020_2022: int
    max_positive_year_share: float


def _clause(name: str, passed: bool, detail: Any = None) -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def evaluate_decision_gate(inp: GateInputs) -> dict:
    """Predeclared gate. Do not change thresholds after seeing results."""
    hard = []
    hard.append(
        _clause(
            "disc_mean_net_10bps_gt_0",
            finite_gt(inp.disc_mean_net_10bps, 0.0),
            inp.disc_mean_net_10bps,
        )
    )
    hard.append(_clause("disc_cond_adv_gt_0", finite_gt(inp.disc_cond_adv, 0.0), inp.disc_cond_adv))
    hard.append(
        _clause(
            "val_mean_net_10bps_gt_0",
            finite_gt(inp.val_mean_net_10bps, 0.0),
            inp.val_mean_net_10bps,
        )
    )
    hard.append(_clause("val_cond_adv_gt_0", finite_gt(inp.val_cond_adv, 0.0), inp.val_cond_adv))
    hard.append(
        _clause(
            "val_mtm_sharpe_finite_gt_0",
            finite_gt(inp.val_mtm_sharpe, 0.0),
            inp.val_mtm_sharpe,
        )
    )
    hard.append(
        _clause(
            "val_n_trades_ge_15",
            int(inp.val_n_trades) >= VAL_MIN_TRADES,
            inp.val_n_trades,
        )
    )
    rec_active = int(inp.rec_n_trades) >= RECENT_N_FLOOR
    rec_neg = rec_active and (
        finite_lt(inp.rec_mean_net_10bps, 0.0)
        or finite_lt(inp.rec_cond_adv, 0.0)
        or finite_lt(inp.rec_mtm_sharpe, 0.0)
    )
    hard.append(
        _clause(
            "recent_not_negative_when_n_ge_5",
            not rec_neg,
            {
                "rec_n_trades": inp.rec_n_trades,
                "rec_mean_net_10bps": inp.rec_mean_net_10bps,
                "rec_cond_adv": inp.rec_cond_adv,
                "rec_mtm_sharpe": inp.rec_mtm_sharpe,
            },
        )
    )
    hard_fail = not all(c["passed"] for c in hard)

    freeze = []
    freeze.append(
        _clause(
            "val_mean_net_20bps_gt_0",
            finite_gt(inp.val_mean_net_20bps, 0.0),
            inp.val_mean_net_20bps,
        )
    )
    boot_ok = (
        str(inp.val_bootstrap_status) != "INSUFFICIENT_N"
        and finite_ge(inp.val_bootstrap_pr_mean_net_gt_0, BOOT_PR_THRESHOLD)
    )
    freeze.append(
        _clause(
            "val_bootstrap_pr_mean_net_gt_0_ge_0_80",
            boot_ok,
            {
                "status": inp.val_bootstrap_status,
                "pr": inp.val_bootstrap_pr_mean_net_gt_0,
            },
        )
    )
    rec_freeze = rec_active and (
        finite_ge(inp.rec_mean_net_10bps, 0.0)
        and finite_ge(inp.rec_cond_adv, 0.0)
        and finite_ge(inp.rec_mtm_sharpe, 0.0)
    )
    freeze.append(
        _clause(
            "recent_n_ge_5_and_mean_net_cond_adv_mtm_sharpe_ge_0",
            rec_freeze,
            inp.rec_n_trades,
        )
    )
    freeze.append(
        _clause(
            "at_least_two_calendar_years_positive_mean_net",
            int(inp.n_positive_mean_net_years) >= YEAR_POS_MIN,
            inp.n_positive_mean_net_years,
        )
    )
    freeze.append(
        _clause(
            "at_least_one_positive_year_outside_2020_2022",
            int(inp.n_positive_years_outside_2020_2022) >= 1,
            inp.n_positive_years_outside_2020_2022,
        )
    )
    share = inp.max_positive_year_share
    freeze.append(
        _clause(
            "largest_positive_year_share_lt_70pct",
            finite_gt(share, 0.0) and float(share) < YEAR_CONCENTRATION_MAX,
            share,
        )
    )
    freeze_ok = (not hard_fail) and all(c["passed"] for c in freeze)
    if hard_fail:
        disposition = DISCARD
    elif freeze_ok:
        disposition = FREEZE
    else:
        disposition = INSUFFICIENT
    return {
        "disposition": disposition,
        "hard_fail": hard_fail,
        "freeze_ok": freeze_ok,
        "hard_fail_clauses": hard,
        "freeze_clauses": freeze,
        "fee_50bps_is_stress_only": True,
        "not_confirmed_edge": True,
        "does_not_authorize_capital": True,
        "mechanical_disposition_is_not_valita_decision": True,
    }


def gate_inputs_from_period_rows(
    by_period: dict[str, dict],
    stability: dict,
    val_bootstrap_pr: float = np.nan,
    val_bootstrap_status: str = "NOT_COMPUTED",
    val_mtm_sharpe: float = np.nan,
    rec_mtm_sharpe: float = np.nan,
) -> GateInputs:
    d = by_period["discovery"]
    v = by_period["validation"]
    r = by_period["recent"]
    return GateInputs(
        disc_mean_net_10bps=d["mean_net_10bps"],
        disc_cond_adv=d["cond_adv"],
        val_mean_net_10bps=v["mean_net_10bps"],
        val_cond_adv=v["cond_adv"],
        val_mtm_sharpe=val_mtm_sharpe,
        val_n_trades=int(v["n_trades"]),
        rec_n_trades=int(r["n_trades"]),
        rec_mean_net_10bps=r["mean_net_10bps"],
        rec_cond_adv=r["cond_adv"],
        rec_mtm_sharpe=rec_mtm_sharpe,
        val_mean_net_20bps=v["mean_net_20bps"],
        val_bootstrap_pr_mean_net_gt_0=val_bootstrap_pr,
        val_bootstrap_status=val_bootstrap_status,
        n_positive_mean_net_years=int(stability["n_positive_mean_net"]),
        n_positive_years_outside_2020_2022=int(stability["n_positive_outside_2020_2022"]),
        max_positive_year_share=stability["max_positive_year_share"],
    )


def evaluate_fixed_candidate(df: pd.DataFrame, min_cal_days: int | None = None, audit: bool = True) -> dict:
    identity = assert_frozen_identity()
    bundle = build_candidate_arrays(df, min_cal_days=min_cal_days, audit=audit)
    trades = iter_taken_trades(bundle)
    by_period = {p: period_trade_metrics(bundle, p) for p in PERIODS}
    years = yearly_trade_metrics(bundle)
    stability = year_stability(years)
    return {
        "identity": identity,
        "bundle": bundle,
        "trades": trades,
        "by_period": by_period,
        "years": years,
        "stability": stability,
    }


def dataset_and_rector_ok() -> dict:
    data_sha = sha256_file(REPO / DATASET_REL)
    rector_sha = sha256_file(REPO / RECTOR_REL)
    return {
        "dataset_sha256": data_sha,
        "dataset_sha256_match": data_sha == EXPECTED_DATASET_SHA256,
        "rector_sha256": rector_sha,
        "rector_sha256_match": rector_sha == EXPECTED_RECTOR_SHA256,
    }
