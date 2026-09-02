"""EXP-BTC-005: third party can reproduce output hashes from spec + data + command."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-005" / "src"))

from run_synthetic import (  # noqa: E402
    CANONICAL_RUN_DIR,
    CANONICAL_RUN_ID,
    DATA_PATH,
    EXP_DIR,
    EXPECTED_DATA_SHA256,
    FORBIDDEN_DATA,
    HASH_CONTRACT_FILES,
    SPEC_PATH,
    compute,
    write_run_tree,
)

RUNNER = REPO / "experiments" / "EXP-BTC-005" / "src" / "run_synthetic.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def canonical_hashes() -> dict[str, str]:
    manifest = json.loads((CANONICAL_RUN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


class SyntheticReproTests(unittest.TestCase):
    def test_fixture_hash_is_the_declared_one(self) -> None:
        self.assertEqual(sha256_file(DATA_PATH), EXPECTED_DATA_SHA256)
        self.assertEqual(DATA_PATH, REPO / "tests" / "fixtures" / "e02_gap_hours.csv")

    def test_does_not_use_live_1h_csv(self) -> None:
        computed = compute(DATA_PATH, SPEC_PATH)
        self.assertNotIn("btcusdt_1h.csv", computed["data_path"])
        self.assertTrue(FORBIDDEN_DATA.is_file())
        self.assertNotEqual(sha256_file(DATA_PATH), sha256_file(FORBIDDEN_DATA))

    def test_in_process_write_matches_canonical_output_hashes(self) -> None:
        computed = compute(DATA_PATH, SPEC_PATH)
        self.assertEqual(computed["mechanical_gate"], "PASS")
        tmp = Path(tempfile.mkdtemp(prefix="exp-btc-005-test-"))
        hashes = write_run_tree(tmp, computed)
        expected = canonical_hashes()
        for rel in HASH_CONTRACT_FILES:
            self.assertEqual(hashes[rel], expected[rel], msg=rel)
            on_disk = sha256_file(CANONICAL_RUN_DIR / rel)
            self.assertEqual(on_disk, expected[rel], msg=f"canonical disk {rel}")

    def test_third_party_verify_command_exit_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--verify"],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["MECHANICAL_GATE"], "PASS")
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(report["data_sha256"], EXPECTED_DATA_SHA256)

    def test_canonical_run_id_and_manifest_appendix_c_fields(self) -> None:
        manifest = json.loads((CANONICAL_RUN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
        for field in (
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
            self.assertIn(field, manifest)
        self.assertEqual(manifest["RUN_ID"], CANONICAL_RUN_ID)
        self.assertEqual(manifest["EXPERIMENT_ID"], "EXP-BTC-005")
        self.assertEqual(manifest["MECHANICAL_GATE"], "PASS")
        self.assertIsNone(manifest["RANDOM_SEED"])
        self.assertEqual(manifest["not_a_trading_edge"], True)
        self.assertEqual(sha256_file(SPEC_PATH), manifest["SPEC_HASH"])

    def test_refuse_overwrite_of_canonical_run(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--run-id", CANONICAL_RUN_ID],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("REFUSE overwrite", proc.stderr)

    def test_verify_with_run_id_keeps_run01_green(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--verify", "--run-id", CANONICAL_RUN_ID],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["MECHANICAL_GATE"], "PASS")
        self.assertEqual(report["RUN_ID"], CANONICAL_RUN_ID)
        self.assertEqual(report["mismatches"], [])

    def test_compute_hashes_matches_canonical_contract(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--compute-hashes"],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        expected = canonical_hashes()
        for rel in HASH_CONTRACT_FILES:
            self.assertEqual(report["observed"][rel], expected[rel], msg=rel)
        self.assertEqual(report["data_sha256"], EXPECTED_DATA_SHA256)

    def test_verify_against_each_existing_run_folder(self) -> None:
        run_dirs = sorted(
            p for p in EXP_DIR.glob("RUN-*") if (p / "MANIFEST.json").is_file()
        )
        self.assertTrue(run_dirs, msg="expected at least RUN-01")
        for run_dir in run_dirs:
            with self.subTest(run_id=run_dir.name):
                proc = subprocess.run(
                    [sys.executable, str(RUNNER), "--verify", "--run-id", run_dir.name],
                    cwd=REPO,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
                report = json.loads(proc.stdout)
                self.assertEqual(report["MECHANICAL_GATE"], "PASS")
                self.assertEqual(report["RUN_ID"], run_dir.name)
                self.assertEqual(report["mismatches"], [])


if __name__ == "__main__":
    unittest.main()
