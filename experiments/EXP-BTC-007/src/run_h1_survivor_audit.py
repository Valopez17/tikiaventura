#!/usr/bin/env python3
"""EXP-BTC-007 / H1 survivor audit of frozen L6_down_p1_rebound_long_H6.

EXT-C04: fixed-candidate metrics, costs, year stability, decision gate.
Not a trading edge. Does not authorize capital. Does not reselect.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
    CODE_COMMIT_RE,
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    FROZEN_TOP10_REL,
    L6_CANDIDATE_ID,
    LOOKBACK_MODE_B,
    audit_expanding,
    behind_indices,
    commit_has_path,
    csv_cell,
    exact_behind_matches_primitive,
    executable_take,
    expanding_quantiles,
    git_head,
    git_object_exists,
    hours_ahead_index,
    json_num,
    load_bars_csv,
    load_frozen_top10,
    net_from_gross,
    paths_missing_from_commit,
    pct_label,
    rule_id,
    sha256_file,
    sharpe_trades,
    take_idx,
    thesis_name,
    trailing_return_from_behind,
    utc_now_iso,
    write_csv,
    write_text,
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

BOOT_EXPECTED_BLOCK = 5.0
BOOT_REPLICATIONS = 10_000
BOOT_SEED = 0

HASH_CONTRACT_FILES = (
    "outputs/TRADES.csv",
    "outputs/PERIOD_METRICS.csv",
    "outputs/YEARLY_METRICS.csv",
    "outputs/UNCERTAINTY.csv",
    "result/RESULT.json",
    "report/H1_L6_SURVIVOR_AUDIT.md",
)

REQUIRED_HARNESS_PATHS = (
    "experiments/EXP-BTC-007/src/run_h1_survivor_audit.py",
    "experiments/EXP-BTC-007/SPEC.md",
    "tests/test_ext_c04_h1_gate.py",
    "tests/test_ext_c05_h1_mtm.py",
    "tests/fixtures/h1_mtm_intra_trade.csv",
    "tests/fixtures/e02_gap_hours.csv",
    "tests/fixtures/ext_c02_regular_hours.csv",
)

EXISTING_SUITE_CMD = (
    "python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants "
    "tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids "
    "tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro "
    "tests.test_ext_c02_isolation tests.test_ext_c02_reproducibility "
    "tests.test_ext_c04_h1_gate tests.test_ext_c05_h1_mtm -v"
)

TRADES_FIELDS = (
    "trade_id",
    "rule_id",
    "signal_ts",
    "entry_ts",
    "exit_ts",
    "period",
    "year",
    "gross",
    "net_0bps",
    "net_10bps",
    "net_20bps",
    "net_50bps",
    "signal_idx",
    "entry_idx",
    "exit_idx",
)

PERIOD_FIELDS = (
    "rule_id",
    "period",
    "n_signals",
    "n_events",
    "n_trades",
    "n_skip_no_entry",
    "n_skip_no_exit",
    "mean_gross",
    "median_gross",
    "mean_net_0bps",
    "median_net_0bps",
    "mean_net_10bps",
    "median_net_10bps",
    "mean_net_20bps",
    "median_net_20bps",
    "mean_net_50bps",
    "median_net_50bps",
    "win_rate",
    "profit_factor",
    "trade_sharpe",
    "cond_mean",
    "uncond_mean",
    "cond_adv",
    "mtm_total_return",
    "mtm_vol",
    "mtm_sharpe",
    "mtm_max_dd",
    "mtm_calmar",
    "mtm_exposure",
    "mtm_end_cap",
    "mtm_total_return_0bps",
    "mtm_sharpe_0bps",
    "mtm_max_dd_0bps",
    "mtm_end_cap_0bps",
    "mtm_total_return_20bps",
    "mtm_sharpe_20bps",
    "mtm_max_dd_20bps",
    "mtm_end_cap_20bps",
    "mtm_total_return_50bps",
    "mtm_sharpe_50bps",
    "mtm_max_dd_50bps",
    "mtm_end_cap_50bps",
    "end_cap_0bps",
    "end_cap_10bps",
    "end_cap_20bps",
    "end_cap_50bps",
    "largest_win_net",
    "largest_loss_net",
    "span_days",
)

YEARLY_FIELDS = (
    "year",
    "n_trades",
    "mean_net",
    "mean_gross",
    "year_pnl",
    "mtm_return",
    "positive_pnl_contribution",
    "outside_2020_2022",
    "win_rate",
)

UNCERTAINTY_FIELDS = (
    "period",
    "n_trades",
    "status",
    "mean_obs_net_10bps",
    "pr_mean_net_gt_0",
    "ci90_lo",
    "ci90_hi",
    "ci95_lo",
    "ci95_hi",
    "expected_block_length",
    "n_replications",
    "seed",
)

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


def side_mult(fee: float) -> float:
    """Each side so entry_mult * exit_mult equals (1 - fee_rt). Audited Phase 4b algebra."""
    if fee <= 0:
        return 1.0
    if fee >= 1:
        return 0.0
    return float(np.sqrt(1.0 - fee))


def cagr_from(start_cap: float, end_cap: float, days: float) -> float:
    if not np.isfinite(start_cap) or not np.isfinite(end_cap) or start_cap <= 0 or days <= 0:
        return np.nan
    if end_cap <= 0:
        return -1.0
    return float((end_cap / start_cap) ** (CRYPTO_DAYS / days) - 1.0)


def mtm_from_trades(
    n: int,
    opens: np.ndarray,
    closes: np.ndarray,
    trades: list[tuple[int, int]],
    direction: str,
    fee: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Hourly equity: fill at open, mark at close, exit at exact exit open.

    Round-trip fee F is split so entry_mult * exit_mult = (1 - F).
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


def slice_equity_window(
    equity: np.ndarray,
    position: np.ndarray,
    i0: int,
    i1: int,
    start_cap: float = START_CAP,
) -> tuple[np.ndarray, np.ndarray]:
    eq = np.asarray(equity, dtype=float)
    pos = np.asarray(position)
    i0 = int(i0)
    i1 = int(i1)
    if i1 < i0:
        return np.array([start_cap], dtype=float), np.array([0], dtype=np.int8)
    n_steps = i1 - i0
    rets = np.zeros(n_steps, dtype=float)
    for k, i in enumerate(range(i0, i1)):
        if eq[i] > 0 and np.isfinite(eq[i]) and np.isfinite(eq[i + 1]) and eq[i + 1] > 0:
            rets[k] = eq[i + 1] / eq[i] - 1.0
    path = np.empty(n_steps + 1, dtype=float)
    path[0] = start_cap
    if n_steps:
        path[1:] = start_cap * np.cumprod(1.0 + rets)
    return path, pos[i0 : i1 + 1]


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
        float(cagr / abs(max_dd)) if np.isfinite(cagr) and np.isfinite(max_dd) and max_dd < 0 else np.nan
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


def trade_only_equity_from_nets(nets: np.ndarray, start_cap: float = START_CAP) -> np.ndarray:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.array([start_cap], dtype=float)
    return np.concatenate([[start_cap], start_cap * np.cumprod(1.0 + x)])


def period_index_window(
    ts: pd.DatetimeIndex,
    periods: np.ndarray,
    trades: list[dict],
    period: str,
) -> tuple[int, int]:
    n = len(ts)
    if period == "full":
        i0, i1 = 0, n - 1
        if trades:
            i1 = max(i1, max(int(tr["exit_idx"]) for tr in trades))
        return 0, min(i1, n - 1)
    mask = periods == period
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return 0, 0
    i0 = int(idx[0])
    i1 = int(idx[-1])
    if trades:
        i1 = max(i1, max(int(tr["exit_idx"]) for tr in trades))
    return i0, min(i1, n - 1)


def mtm_for_trades(
    bundle: dict,
    trades: list[dict],
    period: str,
    fee: float,
) -> dict:
    n = bundle["n"]
    ts = bundle["ts"]
    if period == "full":
        selected = list(trades)
    else:
        selected = [tr for tr in trades if tr["period"] == period]
    i0, i1 = period_index_window(ts, bundle["periods"], selected, period)
    pairs = [(int(tr["entry_idx"]), int(tr["exit_idx"])) for tr in selected]
    eq, pos = mtm_from_trades(n, bundle["opens"], bundle["closes"], pairs, DIRECTION, fee)
    path, ppos = slice_equity_window(eq, pos, i0, i1)
    span_days = max(float((ts[i1] - ts[i0]).total_seconds() / 86400.0), 1.0 / 24.0) if n else 1.0
    mets = mtm_metrics(path, ppos, span_days)
    mets["window_i0"] = i0
    mets["window_i1"] = i1
    mets["n_mtm_trades"] = len(selected)
    return mets


def yearly_mtm_return(bundle: dict, trades: list[dict], year: int, fee: float) -> float:
    selected = [tr for tr in trades if int(tr["year"]) == int(year)]
    if not selected:
        return np.nan
    ts = bundle["ts"]
    years = ts.year.to_numpy()
    idx = np.flatnonzero(years == int(year))
    i0 = int(idx[0]) if idx.size else 0
    i1 = int(idx[-1]) if idx.size else 0
    i1 = max(i1, max(int(tr["exit_idx"]) for tr in selected))
    i1 = min(i1, bundle["n"] - 1)
    pairs = [(int(tr["entry_idx"]), int(tr["exit_idx"])) for tr in selected]
    eq, pos = mtm_from_trades(
        bundle["n"], bundle["opens"], bundle["closes"], pairs, DIRECTION, fee
    )
    path, ppos = slice_equity_window(eq, pos, i0, i1)
    span = max(float((ts[i1] - ts[i0]).total_seconds() / 86400.0), 1.0 / 24.0)
    return mtm_metrics(path, ppos, span)["mtm_total_return"]


def stationary_bootstrap_mean(
    values: np.ndarray,
    expected_block_length: float = BOOT_EXPECTED_BLOCK,
    n_replications: int = BOOT_REPLICATIONS,
    seed: int = BOOT_SEED,
    min_n: int = BOOT_N_MIN,
) -> dict:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = int(x.size)
    mean_obs = float(x.mean()) if n else np.nan
    base = {
        "n": n,
        "mean_obs": mean_obs,
        "expected_block_length": float(expected_block_length),
        "n_replications": 0,
        "seed": int(seed),
        "pr_mean_gt_0": np.nan,
        "ci90_lo": np.nan,
        "ci90_hi": np.nan,
        "ci95_lo": np.nan,
        "ci95_hi": np.nan,
    }
    if n < int(min_n):
        base["status"] = "INSUFFICIENT_N"
        return base
    p = 1.0 / float(expected_block_length)
    rng = np.random.default_rng(int(seed))
    u = rng.random((int(n_replications), n - 1))
    starts = rng.integers(0, n, size=int(n_replications))
    idx = np.empty((int(n_replications), n), dtype=np.int64)
    idx[:, 0] = starts
    for t in range(1, n):
        cont = u[:, t - 1] >= p
        new_s = rng.integers(0, n, size=int(n_replications))
        idx[:, t] = np.where(cont, (idx[:, t - 1] + 1) % n, new_s)
    means = x[idx].mean(axis=1)
    base.update(
        {
            "status": "OK",
            "n_replications": int(n_replications),
            "pr_mean_gt_0": float(np.mean(means > 0.0)),
            "ci90_lo": float(np.quantile(means, 0.05)),
            "ci90_hi": float(np.quantile(means, 0.95)),
            "ci95_lo": float(np.quantile(means, 0.025)),
            "ci95_hi": float(np.quantile(means, 0.975)),
        }
    )
    return base


def nets_by_period(trades: list[dict], period: str) -> np.ndarray:
    if period == "full":
        return np.array([tr["net_10bps"] for tr in trades], dtype=float)
    return np.array([tr["net_10bps"] for tr in trades if tr["period"] == period], dtype=float)


def attach_mtm_uncertainty_gate(evaluated: dict) -> dict:
    bundle = evaluated["bundle"]
    trades = evaluated["trades"]
    by_period = evaluated["by_period"]
    years = evaluated["years"]
    for row in years:
        row["mtm_return"] = yearly_mtm_return(bundle, trades, int(row["year"]), FEE_PRIMARY)
    for period in PERIODS:
        row = by_period[period]
        selected = trades if period == "full" else [tr for tr in trades if tr["period"] == period]
        for bps in FEE_BPS:
            mets = mtm_for_trades(bundle, trades, period, fee_from_bps(bps))
            if bps == FEE_PRIMARY_BPS:
                row["mtm_total_return"] = mets["mtm_total_return"]
                row["mtm_vol"] = mets["mtm_vol"]
                row["mtm_sharpe"] = mets["mtm_sharpe"]
                row["mtm_max_dd"] = mets["mtm_max_dd"]
                row["mtm_calmar"] = mets["mtm_calmar"]
                row["mtm_exposure"] = mets["mtm_exposure"]
                row["mtm_end_cap"] = mets["mtm_end_cap"]
            row[f"mtm_total_return_{bps}bps"] = mets["mtm_total_return"]
            row[f"mtm_sharpe_{bps}bps"] = mets["mtm_sharpe"]
            row[f"mtm_max_dd_{bps}bps"] = mets["mtm_max_dd"]
            row[f"mtm_end_cap_{bps}bps"] = mets["mtm_end_cap"]
        row["n_mtm_trades"] = len(selected)
    uncertainty = {}
    for period in GATE_PERIODS + ("full",):
        uncertainty[period] = stationary_bootstrap_mean(nets_by_period(trades, period))
    val_boot = uncertainty["validation"]
    inp = gate_inputs_from_period_rows(
        by_period,
        evaluated["stability"],
        val_bootstrap_pr=val_boot["pr_mean_gt_0"],
        val_bootstrap_status=val_boot["status"],
        val_mtm_sharpe=by_period["validation"]["mtm_sharpe"],
        rec_mtm_sharpe=by_period["recent"]["mtm_sharpe"],
    )
    gate = evaluate_decision_gate(inp)
    evaluated["uncertainty"] = uncertainty
    evaluated["gate_inputs"] = inp
    evaluated["gate"] = gate
    return evaluated


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, GateInputs):
        return sanitize(asdict(obj))
    if isinstance(obj, FrozenRule):
        return sanitize(obj.identity_dict())
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return json_num(obj)


def fmt_num(x: Any, nd: int = 6) -> str:
    if x is None:
        return "NA"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not np.isfinite(xf):
        return "NA"
    return f"{xf:.{nd}g}"


def fmt_pct(x: Any, nd: int = 3) -> str:
    if x is None:
        return "NA"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return "NA"
    if not np.isfinite(xf):
        return "NA"
    return f"{100.0 * xf:.{nd}f}%"


def trade_rows_for_csv(evaluated: dict) -> list[dict]:
    rows = []
    for i, tr in enumerate(evaluated["trades"], start=1):
        rows.append(
            {
                "trade_id": i,
                "rule_id": FROZEN_RULE_ID,
                "signal_ts": pd.Timestamp(tr["signal_ts"]).isoformat(),
                "entry_ts": pd.Timestamp(tr["entry_ts"]).isoformat(),
                "exit_ts": pd.Timestamp(tr["exit_ts"]).isoformat(),
                "period": tr["period"],
                "year": tr["year"],
                "gross": tr["gross"],
                "net_0bps": tr["net_0bps"],
                "net_10bps": tr["net_10bps"],
                "net_20bps": tr["net_20bps"],
                "net_50bps": tr["net_50bps"],
                "signal_idx": tr["signal_idx"],
                "entry_idx": tr["entry_idx"],
                "exit_idx": tr["exit_idx"],
            }
        )
    return rows


def period_rows_for_csv(evaluated: dict) -> list[dict]:
    rows = []
    for period in PERIODS:
        row = evaluated["by_period"][period]
        out = {k: row.get(k) for k in PERIOD_FIELDS}
        out["rule_id"] = FROZEN_RULE_ID
        out["period"] = period
        rows.append(out)
    return rows


def yearly_rows_for_csv(evaluated: dict) -> list[dict]:
    rows = []
    for y in evaluated["years"]:
        rows.append({k: y.get(k) for k in YEARLY_FIELDS})
    return rows


def uncertainty_rows_for_csv(evaluated: dict) -> list[dict]:
    rows = []
    for period in GATE_PERIODS + ("full",):
        u = evaluated["uncertainty"][period]
        rows.append(
            {
                "period": period,
                "n_trades": u["n"],
                "status": u["status"],
                "mean_obs_net_10bps": u["mean_obs"],
                "pr_mean_net_gt_0": u["pr_mean_gt_0"],
                "ci90_lo": u["ci90_lo"],
                "ci90_hi": u["ci90_hi"],
                "ci95_lo": u["ci95_lo"],
                "ci95_hi": u["ci95_hi"],
                "expected_block_length": u["expected_block_length"],
                "n_replications": u["n_replications"],
                "seed": u["seed"],
            }
        )
    return rows


def clause_map(clauses: list[dict]) -> dict:
    return {c["name"]: {"passed": c["passed"], "detail": sanitize(c["detail"])} for c in clauses}


def result_payload(evaluated: dict, hashes_ok: dict, spec_sha: str, data_path: str) -> dict:
    gate = evaluated["gate"]
    inp = evaluated["gate_inputs"]
    meta = evaluated["bundle"]["meta"]
    mechanical = {
        "dataset_sha256_match": hashes_ok["dataset_sha256_match"],
        "rector_sha256_match": hashes_ok["rector_sha256_match"],
        "frozen_identity_match": True,
        "lookback_mode_exact_timestamp": True,
        "no_reselection": True,
        "min_history_calendar_days": MIN_HISTORY_CALENDAR_DAYS,
        "entry_offset_h": ENTRY_OFFSET_H,
        "hold_h": HOLD_H,
    }
    mech_pass = all(
        [
            hashes_ok["dataset_sha256_match"],
            hashes_ok["rector_sha256_match"],
            mechanical["frozen_identity_match"],
            mechanical["no_reselection"],
        ]
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_version": HYPOTHESIS_VERSION,
        "hypothesis_lifecycle_unchanged": "INVALIDATED",
        "experiment_type": "ROBUSTNESS",
        "role": "FIXED_CANDIDATE_SURVIVOR_AUDIT",
        "task_ids": ["EXT-C03", "EXT-C04", "EXT-C05", "EXT-C06"],
        "objective": (
            "Using exact timestamps and without changing any rule parameter, is the "
            "historical evidence strong and stable enough to justify freezing this "
            "candidate for prospective observation, or should it be discarded / labeled insufficient?"
        ),
        "frozen_rule": evaluated["identity"]["rule"],
        "frozen_rule_sources": {
            "phase4_top_candidates": FROZEN_TOP10_REL,
            "ext_c02_result": EXT_C02_RESULT_REL,
            "phase4_row": evaluated["identity"]["phase4"],
            "ext_c02_rule_id": evaluated["identity"]["ext_c02_rule_id"],
        },
        "dataset_path": data_path,
        "dataset_sha256": hashes_ok["dataset_sha256"],
        "rector_sha256": hashes_ok["rector_sha256"],
        "spec_path": "experiments/EXP-BTC-007/SPEC.md",
        "spec_sha256": spec_sha,
        "temporal_coverage": {
            "start_utc": str(meta.get("start_utc")),
            "end_utc": str(meta.get("end_utc")),
            "n_bars": int(meta.get("n_bars", evaluated["bundle"]["n"])),
            "n_missing_hours": int(meta.get("n_missing_hours", 0)),
        },
        "costs_bps": list(FEE_BPS),
        "primary_cost_bps": FEE_PRIMARY_BPS,
        "splits": {
            "discovery": "start through 2021-12-31 (t < 2022-01-01T00:00:00+00:00)",
            "validation": "2022-01-01 through 2024-12-31",
            "recent": "2025-01-01 through latest complete bar",
        },
        "period_metrics": {p: sanitize(evaluated["by_period"][p]) for p in PERIODS},
        "yearly_metrics": sanitize(evaluated["years"]),
        "year_stability": sanitize(evaluated["stability"]),
        "uncertainty": sanitize(evaluated["uncertainty"]),
        "n_trades_full": len(evaluated["trades"]),
        "gate_inputs": sanitize(inp),
        "gate_clauses": {
            "hard_fail": clause_map(gate["hard_fail_clauses"]),
            "freeze": clause_map(gate["freeze_clauses"]),
        },
        "disposition": gate["disposition"],
        "hard_fail": gate["hard_fail"],
        "freeze_ok": gate["freeze_ok"],
        "mechanical_gate": "PASS" if mech_pass else "FAIL",
        "mechanical_gate_checks": mechanical,
        "mechanical_gate_is_separate_from_scientific_decision": True,
        "mechanical_disposition_is_not_valita_decision": True,
        "chatgpt_audit": "pending; not executed in EXT-C03..C06",
        "valita_freeze_or_discard": "pending; not executed in EXT-C03..C06",
        "decision_utility": {
            "horizon": "6h after entry",
            "reaction_window": "next exact hourly open only",
            "frequency": "measured by period/year; no frequency optimization",
            "false_alarm_cost": "realized losing 6h trade plus friction and adverse excursion",
            "omission_cost": "foregone positive net after eligible event",
            "utility_weights": "none invented",
            "falsifier": "hard-fail conditions or failure to achieve freeze clauses",
        },
        "disclaimers": {
            "not_clean_oos": True,
            "not_trading_edge": True,
            "does_not_authorize_capital": True,
            "not_confirmed_edge": True,
            "E03_not_CLOSED": True,
            "E04_not_CLOSED": True,
            "E03_estado_ceiling": "FIXED_PENDING_VERIFICATION",
            "E04_estado_ceiling": "FIXED_PENDING_VERIFICATION",
            "HYP-BTC-002_lifecycle": "INVALIDATED",
            "freeze_prospective_means_observe_without_capital": True,
        },
        "fee_50bps_is_stress_only": True,
        "maxdd_no_risk_tolerance_threshold_invented": True,
        "reselect_from_288": False,
    }
    return sanitize(payload)


def render_report(payload: dict) -> str:
    d = payload["disposition"]
    pm = payload["period_metrics"]
    lines = [
        "# H1 L6 survivor audit — mechanical report",
        "",
        "Numeric truth is `result/RESULT.json` and the CSV outputs. This markdown does not override them.",
        "",
        f"Frozen rule: `{payload['frozen_rule']['rule_id']}`",
        f"Mechanical disposition: **{d}**",
        f"mechanical_gate: **{payload['mechanical_gate']}** (separate from disposition and from Valita).",
        "",
        "Not a trading edge. Not clean OOS. Does not authorize capital. Not a confirmed edge.",
        "ChatGPT audit pending. Valita freeze/discard pending. HYP-BTC-002 remains INVALIDATED.",
        "E-03 and E-04 are not CLOSED.",
        "",
        "## Gate inputs (10 bps unless noted)",
        "",
        "| Period | N trades | mean net 10bps | cond adv | MTM Sharpe | mean net 20bps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for p in PERIODS:
        r = pm[p]
        lines.append(
            f"| {p} | {r.get('n_trades')} | {fmt_num(r.get('mean_net_10bps'))} | "
            f"{fmt_num(r.get('cond_adv'))} | {fmt_num(r.get('mtm_sharpe'))} | "
            f"{fmt_num(r.get('mean_net_20bps'))} |"
        )
    u = payload["uncertainty"]["validation"]
    lines += [
        "",
        f"Validation bootstrap status: `{u.get('status')}`; "
        f"Pr(mean_net>0)={fmt_num(u.get('pr_mean_gt_0'))}; "
        f"N={u.get('n')}; seed=0; expected block length=5; 10000 replications.",
        "",
        f"Year stability: {payload['year_stability'].get('note')}",
        "",
        "## Clause results",
        "",
        "Hard-fail (any fail → DISCARD):",
    ]
    for name, c in payload["gate_clauses"]["hard_fail"].items():
        lines.append(f"- `{name}`: {'PASS' if c['passed'] else 'FAIL'}")
    lines.append("")
    lines.append("Freeze clauses (all required, and no hard fail, for FREEZE_PROSPECTIVE_RECOMMENDED):")
    for name, c in payload["gate_clauses"]["freeze"].items():
        lines.append(f"- `{name}`: {'PASS' if c['passed'] else 'FAIL'}")
    lines += [
        "",
        "FREEZE_PROSPECTIVE_RECOMMENDED means only: freeze the exact rule and observe prospectively without capital.",
        "",
        "## Annual table",
        "",
        "| year | N | mean net | year PnL | MTM return | +PnL share |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for y in payload["yearly_metrics"]:
        lines.append(
            f"| {y.get('year')} | {y.get('n_trades')} | {fmt_num(y.get('mean_net'))} | "
            f"{fmt_num(y.get('year_pnl'))} | {fmt_num(y.get('mtm_return'))} | "
            f"{fmt_num(y.get('positive_pnl_contribution'))} |"
        )
    lines += [
        "",
        "50 bps is stress only. MaxDD is reported without an invented risk-tolerance threshold.",
        "",
    ]
    return "\n".join(lines) + "\n"


def compute(data_path: Path, spec_path: Path) -> dict:
    hashes_ok = dataset_and_rector_ok()
    spec_sha = sha256_file(spec_path)
    data_sha = sha256_file(data_path)
    if data_sha != EXPECTED_DATASET_SHA256:
        hashes_ok["dataset_sha256_match"] = False
    df = load_bars_csv(data_path)
    evaluated = evaluate_fixed_candidate(df, min_cal_days=None, audit=True)
    evaluated = attach_mtm_uncertainty_gate(evaluated)
    payload = result_payload(
        evaluated,
        {
            **hashes_ok,
            "dataset_sha256": data_sha,
        },
        spec_sha,
        str(Path(data_path).as_posix().replace(str(REPO) + "/", "") if str(data_path).startswith(str(REPO)) else data_path),
    )
    rel = DATASET_REL
    payload["dataset_path"] = rel
    payload["dataset_sha256"] = data_sha
    warnings: list[str] = []
    if not hashes_ok["rector_sha256_match"]:
        warnings.append("rector hash mismatch")
        payload["mechanical_gate"] = "FAIL"
    if not hashes_ok["dataset_sha256_match"]:
        warnings.append("dataset hash mismatch")
        payload["mechanical_gate"] = "FAIL"
    return {
        "evaluated": evaluated,
        "payload": payload,
        "spec_sha256": spec_sha,
        "data_sha256": data_sha,
        "data_path": rel,
        "meta": evaluated["bundle"]["meta"],
        "warnings": warnings,
        "mechanical_gate": payload["mechanical_gate"],
        "disposition": payload["disposition"],
    }


def write_run_tree(run_dir: Path, run_id: str, computed: dict) -> dict[str, str]:
    ev = computed["evaluated"]
    payload = dict(computed["payload"])
    payload["run_id"] = run_id
    write_csv(run_dir / "outputs" / "TRADES.csv", trade_rows_for_csv(ev), TRADES_FIELDS)
    write_csv(run_dir / "outputs" / "PERIOD_METRICS.csv", period_rows_for_csv(ev), PERIOD_FIELDS)
    write_csv(run_dir / "outputs" / "YEARLY_METRICS.csv", yearly_rows_for_csv(ev), YEARLY_FIELDS)
    write_csv(run_dir / "outputs" / "UNCERTAINTY.csv", uncertainty_rows_for_csv(ev), UNCERTAINTY_FIELDS)
    write_text(
        run_dir / "result" / "RESULT.json",
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )
    write_text(run_dir / "report" / "H1_L6_SURVIVOR_AUDIT.md", render_report(payload))
    hashes = {}
    for rel in HASH_CONTRACT_FILES:
        hashes[rel] = sha256_file(run_dir / rel)
    return hashes


def environment() -> dict:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def harness_worktree_dirty() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", *REQUIRED_HARNESS_PATHS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git status failed: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def resolve_code_commit() -> str:
    sha = git_head()
    if not git_object_exists(sha):
        raise RuntimeError(f"CODE_COMMIT {sha} is not a git object")
    missing = paths_missing_from_commit(sha, REQUIRED_HARNESS_PATHS)
    if missing:
        raise RuntimeError(
            "CODE_COMMIT does not contain executed harness code: "
            + f"{sha} missing {missing}. Commit runner/spec/tests/fixtures before materializing a run."
        )
    dirty = harness_worktree_dirty()
    if dirty:
        raise RuntimeError(
            "refuse to materialize with uncommitted runner/spec/test/fixture changes: "
            + "; ".join(dirty)
        )
    return sha


def run_dir_for(run_id: str) -> Path:
    return EXP_DIR / run_id


def output_hashes_from_run(run_id: str) -> dict[str, str]:
    manifest = json.loads((run_dir_for(run_id) / "MANIFEST.json").read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


def hash_checked_in_files(run_id: str) -> dict[str, str]:
    run_dir = run_dir_for(run_id)
    return {rel: sha256_file(run_dir / rel) for rel in HASH_CONTRACT_FILES}


def write_manifest(
    run_dir: Path,
    run_id: str,
    command: str,
    computed: dict,
    output_hashes: dict[str, str],
    started_at: str,
    ended_at: str,
    code_commit: str,
    tests_evidence: dict | None = None,
) -> None:
    meta = computed["meta"]
    manifest = {
        "RUN_ID": run_id,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "STARTED_AT": started_at,
        "ENDED_AT": ended_at,
        "SPEC_HASH": computed["spec_sha256"],
        "CODE_COMMIT": code_commit,
        "COMMAND": command,
        "ENVIRONMENT": environment(),
        "RANDOM_SEED": {"bootstrap": BOOT_SEED, "expanding_audit": 0},
        "RAW_DATA_ID": DATASET_REL,
        "RAW_DATA_HASH": computed["data_sha256"],
        "PROCESSED_DATA_ID": None,
        "PROCESSED_DATA_HASH": None,
        "INPUT_ROWS": int(meta["n_bars"]),
        "GAPS": int(meta["n_missing_hours"]),
        "DUPLICATES": int(meta.get("n_dup_dropped", 0)),
        "OUTPUT_FILES": [{"path": rel, "sha256": digest} for rel, digest in output_hashes.items()],
        "TESTS": EXISTING_SUITE_CMD,
        "TESTS_EVIDENCE": tests_evidence,
        "WARNINGS": computed["warnings"],
        "MECHANICAL_GATE": computed["mechanical_gate"],
        "DISPOSITION": computed["disposition"],
        "TASK_IDS": ["EXT-C03", "EXT-C04", "EXT-C05", "EXT-C06"],
        "HYPOTHESIS_ID": HYPOTHESIS_ID,
        "hash_contract_files": list(HASH_CONTRACT_FILES),
        "hash_contract_note": (
            "Byte-identical contract covers TRADES.csv, PERIOD_METRICS.csv, YEARLY_METRICS.csv, "
            "UNCERTAINTY.csv, RESULT.json, H1_L6_SURVIVOR_AUDIT.md. "
            "STARTED_AT/ENDED_AT, CODE_COMMIT, ENVIRONMENT, and TESTS_EVIDENCE may differ across machines."
        ),
        "not_a_trading_edge": True,
        "does_not_authorize_capital": True,
        "not_clean_oos": True,
        "mechanical_gate_is_separate_from_scientific_decision": True,
        "CODE_COMMIT_IS_EXT_C05": True,
    }
    write_text(
        run_dir / "MANIFEST.json",
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )


def write_receipt(
    run_dir: Path,
    run_id: str,
    command: str,
    computed: dict,
    output_hashes: dict[str, str],
    code_commit: str,
    tests_evidence: dict | None = None,
) -> None:
    lines = [
        "# Run receipt — EXP-BTC-007 / H1 L6 survivor audit",
        "",
        f"RUN_ID: {run_id}",
        f"CODE_COMMIT (EXT-C05): `{code_commit}`",
        f"COMMAND: `{command}`",
        f"mechanical_gate: {computed['mechanical_gate']}",
        f"disposition: {computed['disposition']}",
        "",
        "Cursor reports mechanical disposition only. ChatGPT audit pending. Valita freeze/discard pending.",
        "Not a trading edge. Not clean OOS. Does not authorize capital. HYP-BTC-002 remains INVALIDATED.",
        "",
        "## Hashes",
        "",
        f"- spec: `{computed['spec_sha256']}`",
        f"- dataset: `{computed['data_sha256']}`",
    ]
    for rel, digest in output_hashes.items():
        lines.append(f"- {rel}: `{digest}`")
    if tests_evidence:
        lines += [
            "",
            "## Tests (actual execution, not a command string alone)",
            "",
            f"- command: `{tests_evidence.get('command')}`",
            f"- exit_code: {tests_evidence.get('exit_code')}",
            f"- passed: {tests_evidence.get('passed')}",
            f"- failed: {tests_evidence.get('failed')}",
            f"- skipped: {tests_evidence.get('skipped')}",
            f"- log_sha256: `{tests_evidence.get('log_sha256')}`",
        ]
    lines += [
        "",
        "Markdown never overrides CSV/JSON.",
        "",
    ]
    write_text(run_dir / "receipt.md", "\n".join(lines))


def materialize(run_id: str, command: str, tests_evidence: dict | None = None) -> int:
    run_dir = run_dir_for(run_id)
    if run_dir.exists():
        print(f"REFUSE overwrite of existing run folder: {run_dir}", file=sys.stderr)
        return 2
    try:
        code_commit = resolve_code_commit()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    started = utc_now_iso()
    computed = compute(REPO / DATASET_REL, SPEC_PATH)
    run_dir.mkdir(parents=True, exist_ok=False)
    hashes = write_run_tree(run_dir, run_id, computed)
    ended = utc_now_iso()
    write_manifest(run_dir, run_id, command, computed, hashes, started, ended, code_commit, tests_evidence)
    write_receipt(run_dir, run_id, command, computed, hashes, code_commit, tests_evidence)
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "run_id": run_id,
                "CODE_COMMIT": code_commit,
                "hashes": hashes,
                "MECHANICAL_GATE": computed["mechanical_gate"],
                "disposition": computed["disposition"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if computed["mechanical_gate"] == "PASS" else 1


def verify(run_id: str) -> int:
    """Three-way integrity. Never hardcode canonical_run_unmodified=true."""
    started = utc_now_iso()
    run_dir = run_dir_for(run_id)
    if not (run_dir / "MANIFEST.json").is_file():
        print(f"missing canonical run {run_dir}", file=sys.stderr)
        return 2
    manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}
    checked_in = hash_checked_in_files(run_id)
    mismatches_1 = []
    for rel in HASH_CONTRACT_FILES:
        if checked_in.get(rel) != expected.get(rel):
            mismatches_1.append({"path": rel, "checked_in": checked_in.get(rel), "manifest": expected.get(rel)})
    computed = compute(REPO / DATASET_REL, SPEC_PATH)
    tmp = Path(tempfile.mkdtemp(prefix="exp-btc-007-verify-"))
    try:
        recomputed = write_run_tree(tmp, run_id, computed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    mismatches_2 = []
    for rel in HASH_CONTRACT_FILES:
        if recomputed.get(rel) != expected.get(rel):
            mismatches_2.append({"path": rel, "recomputed": recomputed.get(rel), "manifest": expected.get(rel)})
    mismatches_3 = []
    for rel in HASH_CONTRACT_FILES:
        if checked_in.get(rel) != recomputed.get(rel):
            mismatches_3.append(
                {"path": rel, "checked_in": checked_in.get(rel), "recomputed": recomputed.get(rel)}
            )
    unmodified = (not mismatches_1) and (not mismatches_3)
    mech = "PASS" if unmodified and not mismatches_2 and computed["mechanical_gate"] == "PASS" else "FAIL"
    report = {
        "STARTED_AT": started,
        "ENDED_AT": utc_now_iso(),
        "RUN_ID": run_id,
        "MECHANICAL_GATE": mech,
        "canonical_run_unmodified": unmodified,
        "three_way": {
            "checked_in_vs_manifest": {"mismatches": mismatches_1, "ok": not mismatches_1},
            "recomputed_vs_manifest": {"mismatches": mismatches_2, "ok": not mismatches_2},
            "checked_in_vs_recomputed": {"mismatches": mismatches_3, "ok": not mismatches_3},
        },
        "checked_in": checked_in,
        "recomputed": recomputed,
        "expected": expected,
        "spec_sha256": computed["spec_sha256"],
        "data_sha256": computed["data_sha256"],
        "disposition": computed["disposition"],
    }
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if mech == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-BTC-007 H1 L6 frozen-candidate survivor audit")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--run-id", help="RUN-BTC-007-<UTC-date>-01")
    args = parser.parse_args(argv)
    if args.verify:
        if not args.run_id:
            print("--verify requires --run-id RUN-BTC-007-...", file=sys.stderr)
            return 2
        if not args.run_id.startswith("RUN-"):
            print("run-id must start with RUN-", file=sys.stderr)
            return 2
        return verify(args.run_id)
    if not args.run_id:
        print("required: --verify --run-id RUN-...  or  --run-id RUN-...", file=sys.stderr)
        return 2
    if not args.run_id.startswith("RUN-"):
        print("run-id must start with RUN-", file=sys.stderr)
        return 2
    command = "python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --run-id " + args.run_id
    return materialize(args.run_id, command)


if __name__ == "__main__":
    raise SystemExit(main())

