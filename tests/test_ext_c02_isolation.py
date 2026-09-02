"""EXT-C02 isolation: lookback_mode is the only arm difference; fixtures prove A vs B."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-006" / "src"))
sys.path.insert(0, str(REPO))

from run_ext_c02 import (  # noqa: E402
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    FROZEN_TOP10_REL,
    LOOKBACK_MODE_A,
    LOOKBACK_MODE_B,
    L6_CANDIDATE_ID,
    REQUIRED_HARNESS_PATHS,
    arm_configs,
    audit_expanding,
    behind_indices,
    cell_signal_material,
    configs_identical_except_lookback_mode,
    economic_material,
    exact_behind_matches_primitive,
    expanding_quantiles,
    frozen_top10_ids,
    load_bars_csv,
    load_frozen_top10,
    make_config,
    sha256_file,
    shared_config_dict,
    trailing_return_from_behind,
)
from temporal.exact_timestamp import as_utc_index, lookback_index  # noqa: E402

REGULAR = REPO / "tests" / "fixtures" / "ext_c02_regular_hours.csv"
GAP = REPO / "tests" / "fixtures" / "e02_gap_hours.csv"
DATASET = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
RECTOR = REPO / "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md"
SPEC = REPO / "experiments" / "EXP-BTC-006" / "SPEC.md"
PHASE4_TOP = REPO / FROZEN_TOP10_REL
PHASE4_SCAN = (
    REPO
    / "research/market_state_observatory/trade_signal_research/strategy_lab/"
    / "phase4_extreme_move_reversal/src/run_extreme_move_scan.py"
)
PHASE4B_AUDIT = (
    REPO
    / "research/market_state_observatory/trade_signal_research/strategy_lab/"
    / "phase4b_extreme_move_audit_fix/src/audit_extreme_move_candidates.py"
)


def fixture_frame(path: Path) -> tuple[pd.DatetimeIndex, np.ndarray]:
    df = load_bars_csv(path)
    ts = as_utc_index(pd.DatetimeIndex(df["ts_utc"]))
    closes = df["close"].to_numpy(dtype=float)
    return ts, closes


class ExtC02IsolationTests(unittest.TestCase):
    def test_required_harness_paths_exist_on_disk(self) -> None:
        for rel in REQUIRED_HARNESS_PATHS:
            self.assertTrue((REPO / rel).is_file(), msg=rel)

    def test_dataset_and_rector_sha_unchanged(self) -> None:
        self.assertEqual(sha256_file(DATASET), EXPECTED_DATASET_SHA256)
        self.assertEqual(sha256_file(RECTOR), EXPECTED_RECTOR_SHA256)

    def test_arm_configs_identical_except_lookback_mode(self) -> None:
        a, b = arm_configs()
        self.assertTrue(configs_identical_except_lookback_mode(a, b))
        self.assertEqual(a.lookback_mode, LOOKBACK_MODE_A)
        self.assertEqual(b.lookback_mode, LOOKBACK_MODE_B)
        sa, sb = shared_config_dict(a), shared_config_dict(b)
        self.assertEqual(sa, sb)
        self.assertFalse(a.reselect_top)
        self.assertFalse(a.use_mtm_primary)
        self.assertFalse(a.change_survivor_gate)
        self.assertEqual(a.lookbacks_h, (6, 12, 24, 72))
        self.assertEqual(a.holds_h, (6, 12, 24, 48, 72, 168))
        self.assertEqual(a.down_percentiles, (0.01, 0.025, 0.05))
        self.assertEqual(a.up_percentiles, (0.95, 0.975, 0.99))
        self.assertEqual(a.fee_round_trip, 0.0010)
        self.assertEqual(a.min_history_calendar_days, 365)
        self.assertEqual(a.l6_candidate_id, L6_CANDIDATE_ID)
        self.assertEqual(make_config(LOOKBACK_MODE_A).lookback_mode, LOOKBACK_MODE_A)

    def test_regular_timestamp_fixture_arms_identical(self) -> None:
        ts, closes = fixture_frame(REGULAR)
        for L in (1, 2, 3):
            behind_a = behind_indices(ts, L, LOOKBACK_MODE_A)
            behind_b = behind_indices(ts, L, LOOKBACK_MODE_B)
            np.testing.assert_array_equal(behind_a, behind_b)
            ret_a = trailing_return_from_behind(closes, behind_a)
            ret_b = trailing_return_from_behind(closes, behind_b)
            np.testing.assert_allclose(ret_a, ret_b, equal_nan=True)
            self.assertTrue(exact_behind_matches_primitive(ts, L, behind_b))
            self.assertGreater(int(np.isfinite(ret_a).sum()), 0)

    def test_gap_fixture_exact_arm_does_not_use_substitute_row(self) -> None:
        ts, closes = fixture_frame(GAP)
        t04 = pd.Timestamp("2020-01-01 04:00:00", tz="UTC")
        i04 = int(ts.get_indexer([t04])[0])
        self.assertGreaterEqual(i04, 0)

        behind_a1 = behind_indices(ts, 1, LOOKBACK_MODE_A)
        behind_b1 = behind_indices(ts, 1, LOOKBACK_MODE_B)
        # Positional i-1 from 04:00 is 02:00 (the prior *row*), not the missing 03:00.
        self.assertEqual(ts[int(behind_a1[i04])], pd.Timestamp("2020-01-01 02:00:00", tz="UTC"))
        self.assertEqual(int(behind_b1[i04]), -1)
        self.assertIsNone(lookback_index(ts, t04, pd.Timedelta(hours=1)))

        ret_a1 = trailing_return_from_behind(closes, behind_a1)
        ret_b1 = trailing_return_from_behind(closes, behind_b1)
        self.assertTrue(np.isfinite(ret_a1[i04]))
        self.assertFalse(np.isfinite(ret_b1[i04]))
        expected_legacy = float(closes[i04] / closes[i04 - 1] - 1.0)
        self.assertAlmostEqual(float(ret_a1[i04]), expected_legacy)

        behind_a2 = behind_indices(ts, 2, LOOKBACK_MODE_A)
        behind_b2 = behind_indices(ts, 2, LOOKBACK_MODE_B)
        self.assertEqual(ts[int(behind_a2[i04])], pd.Timestamp("2020-01-01 01:00:00", tz="UTC"))
        self.assertEqual(ts[int(behind_b2[i04])], pd.Timestamp("2020-01-01 02:00:00", tz="UTC"))
        ret_a2 = trailing_return_from_behind(closes, behind_a2)
        ret_b2 = trailing_return_from_behind(closes, behind_b2)
        self.assertAlmostEqual(float(ret_a2[i04]), float(closes[i04] / closes[i04 - 2] - 1.0))
        self.assertAlmostEqual(float(ret_b2[i04]), float(closes[i04] / closes[2] - 1.0))
        self.assertNotAlmostEqual(float(ret_a2[i04]), float(ret_b2[i04]))
        self.assertTrue(exact_behind_matches_primitive(ts, 1, behind_b1))
        self.assertTrue(exact_behind_matches_primitive(ts, 2, behind_b2))

    def test_expanding_percentiles_use_only_timestamps_before_t(self) -> None:
        ts = pd.DatetimeIndex(pd.date_range("2020-01-01", periods=8, freq="h", tz="UTC"))
        ret = np.array([0.10, 0.20, 0.00, 0.30, -0.05, 0.40, 0.15, 0.25], dtype=float)
        q = expanding_quantiles(ret, ts, (0.5,), min_cal_days=0)
        audit_expanding(ret, ts, q[0.5], 0.5, n_check=5)
        for i in np.flatnonzero(np.isfinite(q[0.5])):
            i = int(i)
            hist = ret[:i]
            hist = hist[np.isfinite(hist)]
            self.assertTrue((ts[:i] < ts[i]).all())
            ref = float(np.quantile(hist, 0.5, method="linear"))
            self.assertAlmostEqual(float(q[0.5][i]), ref, places=12)
            self.assertFalse(np.any(ts[:i] >= ts[i]))
            # Current return is not in the history used for q[t].
            self.assertEqual(int(np.isfinite(hist).sum()), int(i))

    def test_frozen_top10_read_from_artifact_no_reselect(self) -> None:
        csv_ids = pd.read_csv(PHASE4_TOP)["rule_id"].astype(str).tolist()
        rows = load_frozen_top10(PHASE4_TOP)
        ids = frozen_top10_ids(rows)
        self.assertEqual(ids, csv_ids)
        self.assertEqual(len(ids), 10)
        self.assertEqual(ids[1], L6_CANDIDATE_ID)
        ranks = [r["discovery_rank"] for r in rows]
        self.assertEqual(ranks, list(range(1, 11)))
        self.assertEqual(ids, [r["rule_id"] for r in rows])

    def test_phase4_and_phase4b_and_dataset_not_rewritten_by_this_tree(self) -> None:
        # Isolation: those historical files still exist and the runner does not
        # point writes at them. Hash lock of dataset/rector is a separate test.
        self.assertTrue(PHASE4_SCAN.is_file())
        self.assertTrue(PHASE4B_AUDIT.is_file())
        self.assertTrue(PHASE4_TOP.is_file())
        runner = (REPO / "experiments/EXP-BTC-006/src/run_ext_c02.py").read_text(encoding="utf-8")
        self.assertNotIn("PHASE4_DIR.write", runner)
        self.assertNotIn("to_csv(RESULTS", runner)
        self.assertIn("reselect_top: bool = False", runner)

    def test_predeclared_materiality_matches_phase4b_coding(self) -> None:
        cfg = make_config(LOOKBACK_MODE_A)
        # Phase 4b: >= max(5, int(0.05 * max(n_legacy, 1)))
        self.assertTrue(cell_signal_material(5, 0, 10, cfg))
        self.assertFalse(cell_signal_material(4, 0, 10, cfg))
        self.assertTrue(cell_signal_material(12, 0, 200, cfg))  # threshold int(0.05*200)=10
        self.assertFalse(cell_signal_material(9, 0, 200, cfg))
        self.assertTrue(economic_material(0.0021, cfg))
        self.assertFalse(economic_material(0.002, cfg))
        self.assertTrue(economic_material(-0.003, cfg))
        spec = SPEC.read_text(encoding="utf-8")
        self.assertIn("max(5, int(0.05 * max(n_legacy, 1)))", spec)
        self.assertIn("0.002", spec)
        self.assertIn("FIXED_PENDING_VERIFICATION", spec)
        self.assertIn("do not mark CLOSED", spec)

    def test_hyp_btc_002_lifecycle_not_changed(self) -> None:
        rows = []
        for line in (REPO / "registries" / "hypotheses.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        latest = None
        for row in rows:
            if row.get("hypothesis_id") == "HYP-BTC-002":
                latest = row
        self.assertIsNotNone(latest)
        self.assertEqual(latest["lifecycle_status"], "INVALIDATED")
        self.assertEqual(latest["version"], "1")


if __name__ == "__main__":
    unittest.main()
