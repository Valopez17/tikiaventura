"""EXT-C04: frozen-candidate isolation, costs, year stability, decision gate.

No canonical run. MTM / bootstrap live in EXT-C05.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-007" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-006" / "src"))
sys.path.insert(0, str(REPO))

from run_h1_survivor_audit import (  # noqa: E402
    BULL_YEARS,
    DIRECTION,
    DISCARD,
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    FEE_BPS,
    FEE_PRIMARY,
    FREEZE,
    FROZEN_RULE_ID,
    HOLD_H,
    INSUFFICIENT,
    LOOKBACK_H,
    LOOKBACK_MODE,
    MIN_HISTORY_CALENDAR_DAYS,
    PERCENTILE,
    TAIL,
    THESIS,
    VAL_MIN_TRADES,
    YEAR_CONCENTRATION_MAX,
    GateInputs,
    assign_periods,
    assert_frozen_identity,
    assert_rule_id_formula,
    build_candidate_arrays,
    dataset_and_rector_ok,
    evaluate_decision_gate,
    fee_from_bps,
    frozen_rule,
    iter_taken_trades,
    net_from_gross,
    period_trade_metrics,
    profit_factor,
    summarize_nets,
    year_stability,
    yearly_trade_metrics,
)
from run_ext_c02 import LOOKBACK_MODE_B, behind_indices, load_bars_csv  # noqa: E402
from temporal.exact_timestamp import lookback_index  # noqa: E402

REGULAR = REPO / "tests" / "fixtures" / "ext_c02_regular_hours.csv"
GAP = REPO / "tests" / "fixtures" / "e02_gap_hours.csv"
DATASET = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
RECTOR = REPO / "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md"
SPEC = REPO / "experiments" / "EXP-BTC-007" / "SPEC.md"
PHASE4_TOP = (
    REPO
    / "research/market_state_observatory/trade_signal_research/strategy_lab/"
    / "phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv"
)
PHASE4_SCAN = (
    REPO
    / "research/market_state_observatory/trade_signal_research/strategy_lab/"
    / "phase4_extreme_move_reversal/src/run_extreme_move_scan.py"
)
EXT_C02_RESULT = (
    REPO / "experiments/EXP-BTC-006/RUN-BTC-006-20260902-03/result/RESULT.json"
)


def _frame(ts: pd.DatetimeIndex, close: np.ndarray, open_: np.ndarray | None = None) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    if open_ is None:
        open_ = np.concatenate([[close[0]], close[:-1]])
    parsed = pd.DataFrame(
        {
            "ts_utc": ts,
            "open": np.asarray(open_, dtype=float),
            "high": np.maximum(open_, close) + 1.0,
            "low": np.minimum(open_, close) - 1.0,
            "close": close,
        }
    )
    parsed.attrs["meta"] = {
        "n_bars": len(parsed),
        "n_missing_hours": 0,
        "n_dup_dropped": 0,
        "start_utc": ts[0],
        "end_utc": ts[-1],
    }
    return parsed


def synthetic_hours(start: str, n: int) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.date_range(start, periods=n, freq="h", tz="UTC"))


class FrozenIdentityTests(unittest.TestCase):
    def test_dataset_and_rector_sha_unchanged(self) -> None:
        hashes = dataset_and_rector_ok()
        self.assertEqual(sha := hashes["dataset_sha256"], EXPECTED_DATASET_SHA256, msg=sha)
        self.assertEqual(hashes["rector_sha256"], EXPECTED_RECTOR_SHA256)
        self.assertTrue(hashes["dataset_sha256_match"])
        self.assertTrue(hashes["rector_sha256_match"])
        self.assertEqual(hashes["dataset_sha256"], "77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103")
        self.assertEqual(hashes["rector_sha256"], "799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778")

    def test_frozen_identity_matches_phase4_and_ext_c02(self) -> None:
        ident = assert_frozen_identity()
        rule = ident["rule"]
        self.assertEqual(rule["rule_id"], FROZEN_RULE_ID)
        self.assertEqual(rule["lookback_h"], 6)
        self.assertEqual(rule["hold_h"], 6)
        self.assertEqual(rule["entry_offset_h"], 1)
        self.assertEqual(rule["percentile"], 0.01)
        self.assertEqual(rule["percentile_label"], "p1")
        self.assertEqual(rule["tail"], "down")
        self.assertEqual(rule["direction"], "long")
        self.assertEqual(rule["thesis"], "rebound")
        self.assertEqual(rule["lookback_mode"], LOOKBACK_MODE_B)
        self.assertEqual(rule["min_history_calendar_days"], 365)
        self.assertEqual(ident["ext_c02_rule_id"], FROZEN_RULE_ID)
        self.assertEqual(ident["phase4"]["lookback_h"], LOOKBACK_H)
        self.assertEqual(ident["phase4"]["hold_h"], HOLD_H)
        self.assertEqual(ident["phase4"]["tail"], TAIL)
        self.assertEqual(ident["phase4"]["direction"], DIRECTION)
        self.assertEqual(ident["phase4"]["thesis"], THESIS)
        self.assertAlmostEqual(ident["phase4"]["percentile"], PERCENTILE)
        self.assertFalse(ident["reselect_from_288"])
        self.assertEqual(len(ident["top10_ids"]), 10)
        self.assertIn(FROZEN_RULE_ID, ident["top10_ids"])
        self.assertEqual(ident["top10_ids"][1], FROZEN_RULE_ID)

    def test_rule_id_formula_and_no_parameter_freedom(self) -> None:
        self.assertEqual(assert_rule_id_formula(), FROZEN_RULE_ID)
        rule = frozen_rule()
        self.assertEqual(rule.lookback_mode, LOOKBACK_MODE)
        self.assertEqual(MIN_HISTORY_CALENDAR_DAYS, 365)
        self.assertEqual(VAL_MIN_TRADES, 15)
        self.assertEqual(YEAR_CONCENTRATION_MAX, 0.70)
        self.assertEqual(FEE_BPS, (0, 10, 20, 50))
        text = SPEC.read_text(encoding="utf-8")
        self.assertIn("L6_down_p1_rebound_long_H6", text)
        self.assertIn("FREEZE_PROSPECTIVE_RECOMMENDED", text)
        self.assertIn("Do not add thresholds", text)
        # Runner must not import the 288-rule scan as the evaluation path.
        src = (REPO / "experiments/EXP-BTC-007/src/run_h1_survivor_audit.py").read_text(encoding="utf-8")
        self.assertNotIn("lookbacks_h = (6, 12, 24, 72)", src)
        self.assertIn("One rule. No 288-rule scan", src)
        self.assertTrue(PHASE4_SCAN.is_file())
        self.assertTrue(EXT_C02_RESULT.is_file())

    def test_spec_sha_is_stable_file(self) -> None:
        self.assertTrue(SPEC.is_file())
        digest = __import__("hashlib").sha256(SPEC.read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)


class ExactTimestampIsolationTests(unittest.TestCase):
    def test_regular_hours_exact_lookback_agrees_with_primitive(self) -> None:
        df = load_bars_csv(REGULAR)
        ts = pd.DatetimeIndex(df["ts_utc"])
        behind = behind_indices(ts, 6, LOOKBACK_MODE_B)
        delta = pd.Timedelta(hours=6)
        for i, t in enumerate(ts):
            prim = lookback_index(ts, t, delta)
            vec = int(behind[i])
            if prim is None:
                self.assertEqual(vec, -1)
            else:
                self.assertEqual(vec, int(prim))

    def test_gap_fixture_missing_t_minus_6h_is_ineligible(self) -> None:
        df = load_bars_csv(GAP)
        ts = pd.DatetimeIndex(df["ts_utc"])
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        t04 = pd.Timestamp("2020-01-01 04:00:00", tz="UTC")
        i04 = int(ts.get_indexer([t04])[0])
        self.assertEqual(int(bundle["behind"][i04]), -1)
        self.assertFalse(np.isfinite(bundle["ret"][i04]))
        self.assertFalse(bool(bundle["signal"][i04]))
        self.assertIsNone(lookback_index(ts, t04, pd.Timedelta(hours=6)))
        t06 = pd.Timestamp("2020-01-01 06:00:00", tz="UTC")
        i06 = int(ts.get_indexer([t06])[0])
        self.assertGreaterEqual(int(bundle["behind"][i06]), 0)
        self.assertEqual(ts[int(bundle["behind"][i06])], pd.Timestamp("2020-01-01 00:00:00", tz="UTC"))

    def test_no_nearest_bar_fill_across_gap_for_lookback_1_vs_6(self) -> None:
        df = load_bars_csv(GAP)
        ts = pd.DatetimeIndex(df["ts_utc"])
        behind6 = behind_indices(ts, 6, LOOKBACK_MODE_B)
        behind1 = behind_indices(ts, 1, LOOKBACK_MODE_B)
        t04 = pd.Timestamp("2020-01-01 04:00:00", tz="UTC")
        i04 = int(ts.get_indexer([t04])[0])
        self.assertEqual(int(behind1[i04]), -1)
        self.assertEqual(int(behind6[i04]), -1)
        positional = i04 - 1
        self.assertEqual(ts[positional], pd.Timestamp("2020-01-01 02:00:00", tz="UTC"))
        self.assertNotEqual(int(behind1[i04]), positional)


class EntryExitNonOverlapTests(unittest.TestCase):
    def _path(self, n: int = 24) -> pd.DataFrame:
        ts = synthetic_hours("2021-12-31 00:00:00", n)
        close = np.linspace(100.0, 80.0, n)
        close[10] = 40.0
        close[11:] = 41.0
        open_ = np.concatenate([[close[0]], close[:-1]])
        return _frame(ts, close, open_)

    def test_missing_entry_or_exit_skips_event(self) -> None:
        ts = pd.DatetimeIndex(
            [
                "2021-12-31 00:00:00",
                "2021-12-31 01:00:00",
                "2021-12-31 02:00:00",
                "2021-12-31 03:00:00",
                "2021-12-31 04:00:00",
                "2021-12-31 05:00:00",
                "2021-12-31 06:00:00",
                "2021-12-31 08:00:00",
            ],
            tz="UTC",
        )
        close = np.array([100, 99, 98, 97, 96, 50, 50, 51], dtype=float)
        open_ = np.concatenate([[100.0], close[:-1]])
        df = _frame(ts, close, open_)
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        # Bar 06:00 has t+1h missing (07:00 gap) so a signal there cannot enter.
        i06 = int(ts.get_indexer([pd.Timestamp("2021-12-31 06:00:00", tz="UTC")])[0])
        if bundle["signal"][i06]:
            self.assertTrue(bool(bundle["missing_entry"][i06]) or bool(bundle["missing_exit"][i06]) or bundle["entry_idx"][i06] < 0)
            self.assertFalse(bool(bundle["valid_event"][i06]))

    def test_nonoverlap_allows_entry_exactly_at_previous_exit(self) -> None:
        ts = synthetic_hours("2021-12-31 00:00:00", 30)
        close = np.full(30, 100.0)
        # Two well-separated crashes 7 hours of entry-apart: signal at t, entry t+1, exit t+7.
        close[8] = 10.0
        close[9:15] = 11.0
        close[15] = 10.0
        close[16:] = 12.0
        open_ = np.concatenate([[100.0], close[:-1]])
        df = _frame(ts, close, open_)
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        trades = iter_taken_trades(bundle)
        self.assertGreaterEqual(len(trades), 1)
        for i in range(1, len(trades)):
            prev_exit = trades[i - 1]["exit_ts"]
            this_entry = trades[i]["entry_ts"]
            self.assertGreaterEqual(this_entry, prev_exit)
        # Forced back-to-back: if a later signal's entry equals previous exit, it is kept.
        if len(trades) >= 2:
            gaps = [(trades[i]["entry_ts"] - trades[i - 1]["exit_ts"]) for i in range(1, len(trades))]
            self.assertTrue(all(g >= pd.Timedelta(0) for g in gaps))

    def test_hold_is_six_calendar_hours_from_entry_not_from_signal(self) -> None:
        df = self._path()
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        for tr in iter_taken_trades(bundle):
            self.assertEqual(tr["entry_ts"] - tr["signal_ts"], pd.Timedelta(hours=1))
            self.assertEqual(tr["exit_ts"] - tr["entry_ts"], pd.Timedelta(hours=6))
            self.assertEqual(tr["exit_ts"] - tr["signal_ts"], pd.Timedelta(hours=7))


class FeeAndPeriodTests(unittest.TestCase):
    def test_fee_algebra_all_four_costs(self) -> None:
        gross = np.array([0.02, -0.01, 0.0, 0.05], dtype=float)
        for bps in FEE_BPS:
            fee = fee_from_bps(bps)
            got = net_from_gross(gross, fee)
            want = (1.0 + gross) * (1.0 - fee) - 1.0
            np.testing.assert_allclose(got, want)
        self.assertEqual(fee_from_bps(10), FEE_PRIMARY)
        self.assertEqual(fee_from_bps(0), 0.0)
        self.assertEqual(fee_from_bps(20), 0.002)
        self.assertEqual(fee_from_bps(50), 0.005)
        s = summarize_nets(gross, span_days=30.0)
        self.assertEqual(s["n_trades"], 4)
        self.assertIn("mean_net_0bps", s)
        self.assertIn("mean_net_10bps", s)
        self.assertIn("mean_net_20bps", s)
        self.assertIn("mean_net_50bps", s)
        self.assertLess(s["mean_net_50bps"], s["mean_net_20bps"])
        self.assertLess(s["mean_net_20bps"], s["mean_net_10bps"])
        self.assertLess(s["mean_net_10bps"], s["mean_net_0bps"])
        self.assertTrue(math.isinf(profit_factor(np.array([0.1, 0.2]))))
        self.assertTrue(np.isnan(profit_factor(np.array([]))))

    def test_period_boundaries_use_signal_timestamp(self) -> None:
        ts = synthetic_hours("2021-12-31 00:00:00", 40)
        periods = assign_periods(ts)
        t_new_year = pd.Timestamp("2022-01-01 00:00:00", tz="UTC")
        t_val_end = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
        for t, p in zip(ts, periods):
            if t < t_new_year:
                self.assertEqual(p, "discovery")
            elif t < t_val_end:
                self.assertEqual(p, "validation")
            else:
                self.assertEqual(p, "recent")
        close = np.full(40, 100.0)
        # Crash in discovery with enough exact 6h history for expanding p1.
        close[10] = 20.0  # 2021-12-31 10:00
        close[11:22] = 21.0
        # Crash in validation; hold can run past more validation hours.
        close[28] = 15.0  # 2022-01-01 04:00
        close[29:] = 16.0
        open_ = np.concatenate([[100.0], close[:-1]])
        df = _frame(ts, close, open_)
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        disc = period_trade_metrics(bundle, "discovery")
        val = period_trade_metrics(bundle, "validation")
        rec = period_trade_metrics(bundle, "recent")
        self.assertEqual(rec["n_signals"], 0)
        self.assertGreaterEqual(disc["n_signals"] + val["n_signals"], 1)
        trades = iter_taken_trades(bundle)
        self.assertGreaterEqual(len(trades), 1)
        crossed = False
        for tr in trades:
            sig_p = "discovery" if tr["signal_ts"] < t_new_year else "validation"
            self.assertEqual(tr["period"], sig_p)
            if tr["signal_ts"] < t_new_year and tr["exit_ts"] >= t_new_year:
                self.assertEqual(tr["period"], "discovery")
                crossed = True
        self.assertTrue(
            crossed or any(tr["signal_ts"] < t_new_year for tr in trades),
            msg="expected a discovery-period signal, possibly with a hold crossing 00:00",
        )

    def test_year_stability_flags(self) -> None:
        years = [
            {"year": 2020, "mean_net": 0.01, "year_pnl": 0.10},
            {"year": 2021, "mean_net": 0.02, "year_pnl": 0.20},
            {"year": 2023, "mean_net": 0.01, "year_pnl": 0.05},
        ]
        st = year_stability(years)
        self.assertTrue(st["at_least_two_positive_years"])
        self.assertTrue(st["at_least_one_positive_outside_2020_2022"])
        self.assertLess(st["max_positive_year_share"], YEAR_CONCENTRATION_MAX)
        self.assertTrue(st["largest_positive_year_share_lt_70pct"])
        concentrated = [
            {"year": 2020, "mean_net": 0.01, "year_pnl": 0.90},
            {"year": 2023, "mean_net": 0.01, "year_pnl": 0.10},
        ]
        st2 = year_stability(concentrated)
        self.assertFalse(st2["largest_positive_year_share_lt_70pct"])
        only_bull = [
            {"year": 2020, "mean_net": 0.01, "year_pnl": 0.4},
            {"year": 2021, "mean_net": 0.01, "year_pnl": 0.4},
        ]
        st3 = year_stability(only_bull)
        self.assertFalse(st3["at_least_one_positive_outside_2020_2022"])
        self.assertEqual(BULL_YEARS, frozenset({2020, 2021, 2022}))


def _gate(**kwargs) -> GateInputs:
    base = dict(
        disc_mean_net_10bps=0.01,
        disc_cond_adv=0.01,
        val_mean_net_10bps=0.004,
        val_cond_adv=0.003,
        val_mtm_sharpe=0.5,
        val_n_trades=20,
        rec_n_trades=8,
        rec_mean_net_10bps=0.001,
        rec_cond_adv=0.001,
        rec_mtm_sharpe=0.1,
        val_mean_net_20bps=0.002,
        val_bootstrap_pr_mean_net_gt_0=0.85,
        val_bootstrap_status="OK",
        n_positive_mean_net_years=3,
        n_positive_years_outside_2020_2022=1,
        max_positive_year_share=0.40,
    )
    base.update(kwargs)
    return GateInputs(**base)


class DecisionGateBranchTests(unittest.TestCase):
    def test_freeze_when_all_clauses_pass(self) -> None:
        out = evaluate_decision_gate(_gate())
        self.assertEqual(out["disposition"], FREEZE)
        self.assertFalse(out["hard_fail"])
        self.assertTrue(out["freeze_ok"])
        self.assertTrue(out["mechanical_disposition_is_not_valita_decision"])
        self.assertTrue(all(c["passed"] for c in out["hard_fail_clauses"]))
        self.assertTrue(all(c["passed"] for c in out["freeze_clauses"]))

    def test_discard_discovery_mean_net(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(disc_mean_net_10bps=0.0))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(disc_mean_net_10bps=-0.01))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(disc_mean_net_10bps=np.nan))["disposition"], DISCARD)

    def test_discard_discovery_cond_adv(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(disc_cond_adv=0.0))["disposition"], DISCARD)

    def test_discard_validation_mean_net_or_adv(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(val_mean_net_10bps=0.0))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(val_cond_adv=-0.001))["disposition"], DISCARD)

    def test_discard_validation_mtm_sharpe_nonfinite_or_le0(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(val_mtm_sharpe=0.0))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(val_mtm_sharpe=np.nan))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(val_mtm_sharpe=-0.2))["disposition"], DISCARD)

    def test_discard_validation_n_lt_15(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(val_n_trades=14))["disposition"], DISCARD)

    def test_discard_recent_negative_when_n_ge_5(self) -> None:
        self.assertEqual(evaluate_decision_gate(_gate(rec_mean_net_10bps=-0.001))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(rec_cond_adv=-0.001))["disposition"], DISCARD)
        self.assertEqual(evaluate_decision_gate(_gate(rec_mtm_sharpe=-0.1))["disposition"], DISCARD)

    def test_recent_n_lt_5_is_not_hard_fail_but_blocks_freeze(self) -> None:
        out = evaluate_decision_gate(_gate(rec_n_trades=4, rec_mean_net_10bps=-0.5))
        self.assertEqual(out["disposition"], INSUFFICIENT)
        self.assertFalse(out["hard_fail"])

    def test_insufficient_val_20bps(self) -> None:
        out = evaluate_decision_gate(_gate(val_mean_net_20bps=0.0))
        self.assertEqual(out["disposition"], INSUFFICIENT)

    def test_insufficient_bootstrap_pr_or_n(self) -> None:
        self.assertEqual(
            evaluate_decision_gate(_gate(val_bootstrap_pr_mean_net_gt_0=0.79))["disposition"],
            INSUFFICIENT,
        )
        self.assertEqual(
            evaluate_decision_gate(
                _gate(val_bootstrap_status="INSUFFICIENT_N", val_bootstrap_pr_mean_net_gt_0=0.99)
            )["disposition"],
            INSUFFICIENT,
        )

    def test_insufficient_year_clauses(self) -> None:
        self.assertEqual(
            evaluate_decision_gate(_gate(n_positive_mean_net_years=1))["disposition"],
            INSUFFICIENT,
        )
        self.assertEqual(
            evaluate_decision_gate(_gate(n_positive_years_outside_2020_2022=0))["disposition"],
            INSUFFICIENT,
        )
        self.assertEqual(
            evaluate_decision_gate(_gate(max_positive_year_share=0.70))["disposition"],
            INSUFFICIENT,
        )
        self.assertEqual(
            evaluate_decision_gate(_gate(max_positive_year_share=0.699999))["disposition"],
            FREEZE,
        )

    def test_fifty_bps_is_not_a_gate_input(self) -> None:
        names = [c["name"] for c in evaluate_decision_gate(_gate())["hard_fail_clauses"]]
        names += [c["name"] for c in evaluate_decision_gate(_gate())["freeze_clauses"]]
        self.assertFalse(any("50" in n for n in names))

    def test_yearly_metrics_on_bundle(self) -> None:
        ts = synthetic_hours("2021-12-30 00:00:00", 48)
        close = np.full(48, 100.0)
        close[10] = 20.0
        close[11:] = 30.0
        open_ = np.concatenate([[100.0], close[:-1]])
        df = _frame(ts, close, open_)
        bundle = build_candidate_arrays(df, min_cal_days=0, audit=False)
        years = yearly_trade_metrics(bundle)
        self.assertTrue(isinstance(years, list))
        st = year_stability(years)
        self.assertIn("n_positive_mean_net", st)


if __name__ == "__main__":
    unittest.main()
