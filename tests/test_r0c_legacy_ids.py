"""R0-C legacy family IDs are references. Classifications unchanged. No invented RUN-IDs."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HYP = REPO / "registries" / "hypotheses.jsonl"
EXP = REPO / "registries" / "experiments.jsonl"
RUNS = REPO / "registries" / "runs.jsonl"

CALENDAR_PATH = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase3_weekly_calendar_anomaly/"
)
EXTREME_PATHS = [
    "research/market_state_observatory/trade_signal_research/strategy_lab/phase4_extreme_move_reversal/",
    "research/market_state_observatory/trade_signal_research/strategy_lab/phase4b_extreme_move_audit_fix/",
]
BREAKOUT_PATH = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase5_breakout_continuation/"
)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def latest_by(rows: list[dict], key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        out[row[key]] = row
    return out


class LegacyIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hyp = latest_by(load_jsonl(HYP), "hypothesis_id")
        self.exp = latest_by(load_jsonl(EXP), "experiment_id")
        self.runs = load_jsonl(RUNS)

    def test_four_families_have_hyp_and_exp_ids(self) -> None:
        for hid, eid in (
            ("HYP-BTC-001", "EXP-BTC-001"),
            ("HYP-BTC-002", "EXP-BTC-002"),
            ("HYP-BTC-003", "EXP-BTC-003"),
            ("HYP-BTC-004", "EXP-BTC-004"),
        ):
            self.assertIn(hid, self.hyp)
            self.assertIn(eid, self.exp)
            self.assertEqual(self.exp[eid]["hypothesis_id"], hid)
            self.assertFalse(self.hyp[hid]["numbers_recalculated"])
            self.assertFalse(self.exp[eid]["numbers_recalculated"])
            self.assertEqual(self.exp[eid]["experiment_type"], "LANDSCAPE")
            self.assertEqual(self.exp[eid]["spec_status"], "LEGACY_REFERENCE_NOT_RERUN")

    def test_calendar_labels_match_section_5_1(self) -> None:
        h = self.hyp["HYP-BTC-001"]
        self.assertEqual(h["evidence_level"], "L2")
        self.assertEqual(h["evidence_label_rector"], "L2 CALCULATED")
        self.assertEqual(h["lifecycle_status"], "DEEPEN")
        self.assertEqual(h["lifecycle_label_rector"], "DEEPEN_METHOD / UNFROZEN")
        self.assertEqual(h["freeze_status"], "UNFROZEN")
        self.assertTrue(h["selection_contaminated"])
        self.assertEqual(h["live_path"], CALENDAR_PATH)
        self.assertEqual(h["rector_section"], "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md §5.1")
        self.assertTrue((REPO / CALENDAR_PATH).is_dir())

    def test_extreme_labels_match_section_5_2(self) -> None:
        h = self.hyp["HYP-BTC-002"]
        self.assertEqual(h["evidence_level"], "L2")
        self.assertEqual(h["evidence_label_rector"], "L2 CALCULATED, afectado")
        self.assertEqual(h["lifecycle_status"], "INVALIDATED")
        self.assertEqual(h["lifecycle_label_rector"], "INVALIDATED")
        self.assertEqual(h["rector_section"], "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md §5.2")
        self.assertEqual(h["live_paths"], EXTREME_PATHS)
        for p in EXTREME_PATHS:
            self.assertTrue((REPO / p).is_dir())

    def test_breakout_not_promoted(self) -> None:
        h = self.hyp["HYP-BTC-003"]
        self.assertEqual(h["evidence_level"], "L0")
        self.assertEqual(h["evidence_label_rector"], "L0 IDEA / spec draft")
        self.assertEqual(h["lifecycle_status"], "BACKLOG")
        self.assertEqual(h["lifecycle_label_rector"], "BACKLOG")
        self.assertFalse(h["authorized_for_cursor"])
        self.assertEqual(h["live_path"], BREAKOUT_PATH)
        self.assertTrue((REPO / BREAKOUT_PATH).is_dir())
        self.assertEqual(h["rector_section"], "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md §5.3")

    def test_vol_not_found_not_invented(self) -> None:
        h = self.hyp["HYP-BTC-004"]
        self.assertEqual(h["evidence_level"], "L0")
        self.assertEqual(h["evidence_label_rector"], "L0 IDEA / spec draft")
        self.assertEqual(h["lifecycle_status"], "BACKLOG")
        self.assertEqual(h["implementation_status"], "NOT_FOUND")
        self.assertIsNone(h["live_path"])
        self.assertEqual(h["rector_section"], "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md §5.4")
        self.assertEqual(self.exp["EXP-BTC-004"]["implementation_status"], "NOT_FOUND")

    def test_no_invented_historical_run_ids_for_legacy_families(self) -> None:
        banned = {"EXP-BTC-001", "EXP-BTC-002", "EXP-BTC-003", "EXP-BTC-004"}
        for row in self.runs:
            self.assertNotIn(row["experiment_id"], banned)

    def test_harness_is_not_an_edge(self) -> None:
        h = self.hyp["HYP-BTC-005"]
        e = self.exp["EXP-BTC-005"]
        self.assertTrue(h["not_a_trading_edge"])
        self.assertEqual(h["role"], "REPRODUCIBILITY_HARNESS")
        self.assertNotEqual(h["evidence_level"], "L5")
        self.assertEqual(e["experiment_type"], "REPRODUCTION")
        self.assertEqual(e["hypothesis_id"], "HYP-BTC-005")
        run_ids = [r["run_id"] for r in self.runs if r["experiment_id"] == "EXP-BTC-005"]
        self.assertIn("RUN-BTC-005-20260902-01", run_ids)


if __name__ == "__main__":
    unittest.main()
