"""EXT-C02 reproducibility: CODE_COMMIT containment and --verify hash contract.

Skips until a RUN-BTC-006-* folder exists (COMMIT_A tests must pass before the run).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import unittest
from io import BytesIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-006" / "src"))

from run_ext_c02 import (  # noqa: E402
    CODE_COMMIT_RE,
    EXPECTED_DATASET_SHA256,
    EXPECTED_RECTOR_SHA256,
    EXP_DIR,
    HASH_CONTRACT_FILES,
    REQUIRED_HARNESS_PATHS,
    commit_has_path,
    git_object_exists,
    paths_missing_from_commit,
    sha256_file,
)

RECTOR = REPO / "BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md"
DATASET = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
PHASE4_TOP = (
    REPO
    / "research/market_state_observatory/trade_signal_research/strategy_lab/"
    / "phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv"
)


def existing_runs() -> list[Path]:
    return sorted(p for p in EXP_DIR.glob("RUN-BTC-006-*") if (p / "MANIFEST.json").is_file())


def load_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))


def output_hash_map(manifest: dict) -> dict[str, str]:
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


class ExtC02ReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runs = existing_runs()
        if not self.runs:
            self.skipTest("canonical EXT-C02 run not yet materialized")
        self.run_dir = self.runs[-1]
        self.manifest = load_manifest(self.run_dir)
        self.result = json.loads((self.run_dir / "result" / "RESULT.json").read_text(encoding="utf-8"))

    def test_code_commit_contains_runner_spec_and_tests(self) -> None:
        sha = self.manifest["CODE_COMMIT"]
        self.assertRegex(sha, CODE_COMMIT_RE.pattern)
        self.assertTrue(CODE_COMMIT_RE.fullmatch(sha))
        self.assertTrue(git_object_exists(sha), msg=sha)
        missing = paths_missing_from_commit(sha, REQUIRED_HARNESS_PATHS)
        self.assertEqual(missing, [], msg=f"{sha} missing {missing}")
        for rel in REQUIRED_HARNESS_PATHS:
            self.assertTrue(commit_has_path(sha, rel), msg=rel)
        run_result_rel = f"experiments/EXP-BTC-006/{self.run_dir.name}/result/RESULT.json"
        self.assertFalse(
            commit_has_path(sha, run_result_rel),
            msg="CODE_COMMIT must be COMMIT_A (run outputs belong in COMMIT_B)",
        )

    def test_result_json_contract_fields(self) -> None:
        r = self.result
        for key in (
            "objective",
            "task_id",
            "experiment_id",
            "run_id",
            "hypothesis_id",
            "error_id",
            "dataset_path",
            "dataset_sha256",
            "temporal_coverage",
            "frozen_config",
            "arm_definitions",
            "only_lookback_mode_differs",
            "global_summary",
            "top10_summary",
            "l6_candidate_summary",
            "predeclared_materiality_criterion",
            "materiality",
            "mechanical_gate",
            "disclaimers",
        ):
            self.assertIn(key, r)
        self.assertEqual(r["task_id"], "EXT-C02")
        self.assertEqual(r["experiment_id"], "EXP-BTC-006")
        self.assertEqual(r["hypothesis_id"], "HYP-BTC-002")
        self.assertEqual(r["error_id"], "E-02")
        self.assertEqual(r["dataset_sha256"], EXPECTED_DATASET_SHA256)
        self.assertTrue(r["only_lookback_mode_differs"])
        self.assertIn(r["materiality"], ("MATERIAL", "NOT_MATERIAL"))
        self.assertIn(r["mechanical_gate"], ("PASS", "FAIL"))
        self.assertTrue(r["mechanical_gate_is_separate_from_scientific_decision"])
        d = r["disclaimers"]
        self.assertTrue(d["not_clean_oos"])
        self.assertTrue(d["not_trading_edge"])
        self.assertTrue(d["does_not_authorize_capital"])
        self.assertTrue(d["E03_open"])
        self.assertTrue(d["E04_open"])
        self.assertTrue(r["e02_not_closed"])
        self.assertEqual(r["error_e02_estado"], "FIXED_PENDING_VERIFICATION")
        self.assertEqual(r["hypothesis_lifecycle_unchanged"], "INVALIDATED")
        self.assertFalse(r["reselect_top"])
        self.assertEqual(len(r["frozen_top10_ids"]), 10)
        self.assertIn("pending", r["ext_h01_chatgpt_audit"])

    def test_manifest_appendix_c_and_dataset_sha(self) -> None:
        m = self.manifest
        for key in (
            "RUN_ID",
            "EXPERIMENT_ID",
            "STARTED_AT",
            "ENDED_AT",
            "SPEC_HASH",
            "CODE_COMMIT",
            "COMMAND",
            "ENVIRONMENT",
            "RANDOM_SEED",
            "RAW_DATA_ID",
            "RAW_DATA_HASH",
            "PROCESSED_DATA_ID",
            "PROCESSED_DATA_HASH",
            "INPUT_ROWS",
            "GAPS",
            "DUPLICATES",
            "OUTPUT_FILES",
            "TESTS",
            "WARNINGS",
            "MECHANICAL_GATE",
        ):
            self.assertIn(key, m)
        self.assertEqual(m["RAW_DATA_HASH"], EXPECTED_DATASET_SHA256)
        self.assertEqual(m["EXPERIMENT_ID"], "EXP-BTC-006")
        self.assertTrue(m["not_a_trading_edge"])
        self.assertTrue(m["does_not_authorize_capital"])
        self.assertEqual(sha256_file(DATASET), EXPECTED_DATASET_SHA256)
        self.assertEqual(sha256_file(RECTOR), EXPECTED_RECTOR_SHA256)
        self.assertTrue(PHASE4_TOP.is_file())

    def test_verify_reproduces_contracted_hashes(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "experiments/EXP-BTC-006/src/run_ext_c02.py",
                "--verify",
                "--run-id",
                self.run_dir.name,
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        json_start = proc.stdout.find("{")
        self.assertGreaterEqual(json_start, 0, msg=proc.stdout + proc.stderr)
        report = json.loads(proc.stdout[json_start:])
        self.assertEqual(report["MECHANICAL_GATE"], "PASS")
        self.assertEqual(report["mismatches"], [])
        expected = output_hash_map(self.manifest)
        for rel in HASH_CONTRACT_FILES:
            self.assertEqual(report["observed"][rel], expected[rel], msg=rel)
        self.assertTrue((self.run_dir / "MANIFEST.json").is_file())

    def test_code_commit_archive_contains_harness_not_run(self) -> None:
        sha = self.manifest["CODE_COMMIT"]
        proc = subprocess.run(
            ["git", "archive", "--format=tar", sha],
            cwd=REPO,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with tarfile.open(fileobj=BytesIO(proc.stdout), mode="r:") as tar:
            names = set(tar.getnames())
        self.assertIn("experiments/EXP-BTC-006/src/run_ext_c02.py", names)
        self.assertIn("experiments/EXP-BTC-006/SPEC.md", names)
        self.assertIn("tests/test_ext_c02_isolation.py", names)
        self.assertNotIn(
            f"experiments/EXP-BTC-006/{self.run_dir.name}/result/RESULT.json",
            names,
        )


if __name__ == "__main__":
    unittest.main()
