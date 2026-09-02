"""Reproduce RUN-02 output hashes from a clean checkout of MANIFEST.CODE_COMMIT.

Generating hashes uses COMMIT_A code only (git archive of CODE_COMMIT).
Expected hashes are read from the current tree's RUN-02 MANIFEST (COMMIT_B evidence).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-005" / "src"))

from run_synthetic import (  # noqa: E402
    CANONICAL_RUN_ID,
    CODE_COMMIT_RE,
    EXPECTED_DATA_SHA256,
    EXP_DIR,
    HASH_CONTRACT_FILES,
)

RUNNER_REL = "experiments/EXP-BTC-005/src/run_synthetic.py"
RUN02_ID = "RUN-BTC-005-20260902-02"
RUN01_ID = CANONICAL_RUN_ID


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_manifest(run_id: str) -> dict:
    return json.loads((EXP_DIR / run_id / "MANIFEST.json").read_text(encoding="utf-8"))


def output_hash_map(manifest: dict) -> dict[str, str]:
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


def archive_commit_to(sha: str, dest: Path) -> None:
    proc = subprocess.run(
        ["git", "archive", "--format=tar", sha],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with tarfile.open(fileobj=BytesIO(proc.stdout), mode="r:") as tar:
        tar.extractall(dest)


class CommitAReproTests(unittest.TestCase):
    def test_run02_reproduced_from_its_code_commit(self) -> None:
        run_dir = EXP_DIR / RUN02_ID
        if not (run_dir / "MANIFEST.json").is_file():
            self.skipTest("RUN-02 not yet materialized")

        manifest = load_manifest(RUN02_ID)
        sha = manifest["CODE_COMMIT"]
        self.assertRegex(sha, CODE_COMMIT_RE.pattern)
        self.assertTrue(CODE_COMMIT_RE.fullmatch(sha))
        self.assertEqual(manifest["RAW_DATA_HASH"], EXPECTED_DATA_SHA256)
        self.assertEqual(manifest["RAW_DATA_ID"], "tests/fixtures/e02_gap_hours.csv")
        self.assertTrue(manifest["not_a_trading_edge"])
        expected = output_hash_map(manifest)

        with tempfile.TemporaryDirectory(prefix="r0c-commit-a-repro-") as tmp:
            dest = Path(tmp)
            archive_commit_to(sha, dest)
            self.assertTrue((dest / RUNNER_REL).is_file(), msg="COMMIT_A must contain the runner")
            self.assertTrue((dest / "experiments/EXP-BTC-005/SPEC.md").is_file())
            self.assertTrue((dest / "tests/fixtures/e02_gap_hours.csv").is_file())
            self.assertFalse(
                (dest / "experiments/EXP-BTC-005" / RUN02_ID).exists(),
                msg="COMMIT_A must not contain RUN-02 outputs",
            )
            fixture_hash = sha256_file(dest / "tests/fixtures/e02_gap_hours.csv")
            self.assertEqual(fixture_hash, manifest["RAW_DATA_HASH"])

            proc = subprocess.run(
                [sys.executable, RUNNER_REL, "--compute-hashes"],
                cwd=dest,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["MECHANICAL_GATE"], "PASS")
            self.assertEqual(report["data_sha256"], manifest["RAW_DATA_HASH"])
            for rel in HASH_CONTRACT_FILES:
                self.assertEqual(
                    report["observed"][rel],
                    expected[rel],
                    msg=f"{rel} expected={expected[rel]} observed={report['observed'][rel]}",
                )

    def test_run02_hashes_match_run01_hash_contract(self) -> None:
        """Reproduction must not change scientific outputs to obtain PASS."""
        run02_dir = EXP_DIR / RUN02_ID
        if not (run02_dir / "MANIFEST.json").is_file():
            self.skipTest("RUN-02 not yet materialized")
        run01 = output_hash_map(load_manifest(RUN01_ID))
        run02 = output_hash_map(load_manifest(RUN02_ID))
        for rel in HASH_CONTRACT_FILES:
            self.assertEqual(run02[rel], run01[rel], msg=rel)


if __name__ == "__main__":
    unittest.main()
