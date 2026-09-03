"""EXT-C05: hourly MTM, intra-trade drawdown, stationary bootstrap, verify contract.

Canonical run tests skip until EXT-C06 materializes RUN-BTC-007-*.
"""

from __future__ import annotations

import json
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
    BOOT_N_MIN,
    BOOT_REPLICATIONS,
    BOOT_SEED,
    DIRECTION,
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    EXP_DIR,
    FEE_BPS,
    HASH_CONTRACT_FILES,
    REQUIRED_HARNESS_PATHS,
    START_CAP,
    assign_periods,
    build_candidate_arrays,
    commit_has_path,
    dataset_and_rector_ok,
    fee_from_bps,
    git_object_exists,
    load_bars_csv,
    mtm_for_trades,
    mtm_from_trades,
    mtm_metrics,
    net_from_gross,
    paths_missing_from_commit,
    period_index_window,
    sha256_file,
    side_mult,
    slice_equity_window,
    stationary_bootstrap_mean,
    trade_only_equity_from_nets,
    verify,
)
from run_ext_c02 import CODE_COMMIT_RE  # noqa: E402

MTM_FIXTURE = REPO / "tests" / "fixtures" / "h1_mtm_intra_trade.csv"
DATASET = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
RECTOR = REPO / "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md"


def existing_runs() -> list[Path]:
    return sorted(p for p in EXP_DIR.glob("RUN-BTC-007-*") if (p / "MANIFEST.json").is_file())


class MtmIntraTradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = load_bars_csv(MTM_FIXTURE)
        self.opens = self.df["open"].to_numpy(dtype=float)
        self.closes = self.df["close"].to_numpy(dtype=float)
        self.n = len(self.df)
        # Entry at 05:00 (index 5, open 100), exit at 10:00 (index 10, open 110).
        self.pairs = [(5, 10)]

    def test_fee_split_product_equals_one_minus_fee_for_all_four_costs(self) -> None:
        for bps in FEE_BPS:
            fee = fee_from_bps(bps)
            sm = side_mult(fee)
            np.testing.assert_allclose(sm * sm, 1.0 - fee, rtol=0, atol=1e-15)
        self.assertEqual(side_mult(0.0), 1.0)
        self.assertEqual(side_mult(1.0), 0.0)

    def test_mtm_captures_intra_trade_drawdown_missed_by_trade_only_equity(self) -> None:
        eq, pos = mtm_from_trades(self.n, self.opens, self.closes, self.pairs, DIRECTION, 0.0)
        mets = mtm_metrics(eq, pos, span_days=1.0)
        gross = self.opens[10] / self.opens[5] - 1.0
        self.assertAlmostEqual(gross, 0.10)
        trade_eq = trade_only_equity_from_nets(np.array([gross]))
        trade_peak = np.maximum.accumulate(trade_eq)
        trade_dd = float(np.min(trade_eq / trade_peak - 1.0))
        self.assertEqual(trade_dd, 0.0)
        # Intra-trade trough: shares=100 at 0 bps, close=70 → equity 7000; MaxDD -30%.
        self.assertLess(mets["mtm_max_dd"], -0.25)
        self.assertLess(mets["mtm_max_dd"], trade_dd)
        self.assertAlmostEqual(float(np.min(eq)), 7000.0)
        self.assertTrue(np.any(pos[5:10] != 0))
        self.assertEqual(int(pos[10]), 0)
        self.assertAlmostEqual(float(eq[10]), START_CAP * (1.0 + gross))
        # Flat hours have zero hourly return.
        rets = eq[1:] / eq[:-1] - 1.0
        self.assertTrue(np.allclose(rets[:4], 0.0))
        self.assertTrue(np.allclose(rets[10:], 0.0))

    def test_mtm_10bps_fee_split_on_fixture(self) -> None:
        fee = 0.001
        eq, _pos = mtm_from_trades(self.n, self.opens, self.closes, self.pairs, DIRECTION, fee)
        gross = self.opens[10] / self.opens[5] - 1.0
        want_net = float(net_from_gross(np.array([gross]), fee)[0])
        got_net = float(eq[-1] / START_CAP - 1.0)
        self.assertAlmostEqual(got_net, want_net, places=12)
        sm = side_mult(fee)
        self.assertAlmostEqual(sm * sm, 1.0 - fee)


class CrossBoundaryHoldTests(unittest.TestCase):
    def test_period_window_extends_through_exit_after_boundary(self) -> None:
        ts = pd.DatetimeIndex(pd.date_range("2021-12-31 18:00:00", periods=12, freq="h", tz="UTC"))
        n = len(ts)
        opens = np.full(n, 100.0)
        closes = np.full(n, 100.0)
        closes[3] = 80.0  # 21:00 still discovery
        opens[4] = 100.0  # entry 22:00 Dec 31
        # exit 04:00 Jan 1 = index 10
        opens[10] = 102.0
        df = pd.DataFrame({"ts_utc": ts, "open": opens, "close": closes})
        periods = assign_periods(ts)
        trades = [
            {
                "period": "discovery",
                "year": 2021,
                "entry_idx": 4,
                "exit_idx": 10,
                "signal_idx": 3,
            }
        ]
        i0, i1 = period_index_window(ts, periods, trades, "discovery")
        self.assertEqual(ts[i0].year, 2021)
        self.assertGreaterEqual(ts[i1], pd.Timestamp("2022-01-01 04:00:00", tz="UTC"))
        bundle = {
            "n": n,
            "ts": ts,
            "opens": opens,
            "closes": closes,
            "periods": periods,
        }
        mets = mtm_for_trades(bundle, trades, "discovery", 0.0)
        self.assertEqual(mets["n_mtm_trades"], 1)
        self.assertGreaterEqual(mets["window_i1"], 10)
        eq, pos = mtm_from_trades(n, opens, closes, [(4, 10)], DIRECTION, 0.0)
        self.assertTrue(np.any(pos[4:10] != 0))
        self.assertEqual(int(pos[10]), 0)
        path, ppos = slice_equity_window(eq, pos, i0, i1)
        self.assertGreaterEqual(ppos.size, 10 - i0)
        self.assertTrue(np.any(ppos != 0))


class BootstrapTests(unittest.TestCase):
    def test_insufficient_n_below_5(self) -> None:
        out = stationary_bootstrap_mean(np.array([0.01, -0.02, 0.03, 0.00]), min_n=BOOT_N_MIN)
        self.assertEqual(out["status"], "INSUFFICIENT_N")
        self.assertTrue(np.isnan(out["pr_mean_gt_0"]))
        self.assertTrue(np.isnan(out["ci95_lo"]))
        self.assertEqual(out["n_replications"], 0)

    def test_deterministic_under_seed_0(self) -> None:
        x = np.array([0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.008], dtype=float)
        a = stationary_bootstrap_mean(x, n_replications=200, seed=BOOT_SEED)
        b = stationary_bootstrap_mean(x, n_replications=200, seed=BOOT_SEED)
        self.assertEqual(a["status"], "OK")
        self.assertEqual(a["pr_mean_gt_0"], b["pr_mean_gt_0"])
        self.assertEqual(a["ci95_lo"], b["ci95_lo"])
        self.assertEqual(a["ci95_hi"], b["ci95_hi"])
        c = stationary_bootstrap_mean(x, n_replications=200, seed=1)
        self.assertNotEqual(a["pr_mean_gt_0"], c["pr_mean_gt_0"])
        self.assertGreaterEqual(a["pr_mean_gt_0"], 0.0)
        self.assertLessEqual(a["pr_mean_gt_0"], 1.0)
        self.assertLessEqual(a["ci90_lo"], a["ci90_hi"])
        self.assertEqual(BOOT_REPLICATIONS, 10_000)
        self.assertEqual(BOOT_SEED, 0)


class HarnessPresenceTests(unittest.TestCase):
    def test_required_paths_exist(self) -> None:
        for rel in REQUIRED_HARNESS_PATHS:
            self.assertTrue((REPO / rel).is_file(), msg=rel)
        hashes = dataset_and_rector_ok()
        self.assertEqual(hashes["dataset_sha256"], EXPECTED_DATASET_SHA256)
        self.assertEqual(hashes["rector_sha256"], EXPECTED_RECTOR_SHA256)

    def test_hash_contract_does_not_include_equity_csv(self) -> None:
        joined = " ".join(HASH_CONTRACT_FILES)
        self.assertNotIn("equity", joined.lower())
        self.assertIn("outputs/TRADES.csv", HASH_CONTRACT_FILES)
        self.assertIn("outputs/UNCERTAINTY.csv", HASH_CONTRACT_FILES)


class ReproducibilitySkipUntilRunTests(unittest.TestCase):
    def test_verify_three_way_or_skip(self) -> None:
        runs = existing_runs()
        if not runs:
            self.skipTest("canonical EXP-BTC-007 run not yet materialized")
        run_id = runs[-1].name
        rc = verify(run_id)
        self.assertEqual(rc, 0)
        manifest = json.loads((runs[-1] / "MANIFEST.json").read_text(encoding="utf-8"))
        sha = manifest["CODE_COMMIT"]
        self.assertRegex(sha, CODE_COMMIT_RE.pattern)
        self.assertTrue(git_object_exists(sha))
        missing = paths_missing_from_commit(sha, REQUIRED_HARNESS_PATHS)
        self.assertEqual(missing, [])
        run_result_rel = f"experiments/EXP-BTC-007/{run_id}/result/RESULT.json"
        self.assertFalse(
            commit_has_path(sha, run_result_rel),
            msg="CODE_COMMIT must be EXT-C05 (run outputs belong in EXT-C06)",
        )
        # canonical_run_unmodified must be derived, not hardcoded in source as a true literal assigned blindly.
        src = (REPO / "experiments/EXP-BTC-007/src/run_h1_survivor_audit.py").read_text(encoding="utf-8")
        self.assertIn("canonical_run_unmodified", src)
        self.assertNotIn('canonical_run_unmodified": True', src)
        self.assertNotIn("canonical_run_unmodified=True", src)

    def test_source_never_hardcodes_unmodified_true(self) -> None:
        src = (REPO / "experiments/EXP-BTC-007/src/run_h1_survivor_audit.py").read_text(encoding="utf-8")
        self.assertIn("Never hardcode canonical_run_unmodified=true", src)
        self.assertNotIn('"canonical_run_unmodified": True', src)


if __name__ == "__main__":
    unittest.main()
