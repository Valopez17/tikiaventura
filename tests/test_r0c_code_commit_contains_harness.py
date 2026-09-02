"""Prevent MANIFEST.CODE_COMMIT from pointing at a commit that lacks executed harness code.

RUN-BTC-005-20260902-01 is the documented incident (E-23) and stays byte-identical.
That run is grandfathered via error_id E-23. New runs are not.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-005" / "src"))

from run_synthetic import (  # noqa: E402
    CODE_COMMIT_RE,
    EXP_DIR,
    GRANDFATHER_ERROR_ID,
    INCIDENT_CODE_COMMIT,
    REQUIRED_HARNESS_PATHS,
    commit_has_path,
    git_object_exists,
    paths_missing_from_commit,
)

ERRORS = REPO / "registries" / "errors.jsonl"
RUN01_ID = "RUN-BTC-005-20260902-01"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def grandfathered_run_ids() -> set[str]:
    ids: set[str] = set()
    for row in load_jsonl(ERRORS):
        if row.get("error_id") != GRANDFATHER_ERROR_ID:
            continue
        affected = row.get("affected_run_id")
        if isinstance(affected, str) and affected:
            ids.add(affected)
        extra = row.get("grandfathered_run_ids")
        if isinstance(extra, list):
            ids.update(str(x) for x in extra)
    return ids


def iter_run_manifests() -> list[tuple[str, dict]]:
    out = []
    for run_dir in sorted(EXP_DIR.glob("RUN-*")):
        manifest_path = run_dir / "MANIFEST.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        out.append((run_dir.name, manifest))
    return out


class CodeCommitContainsHarnessTests(unittest.TestCase):
    def test_e23_exists_and_names_run01(self) -> None:
        rows = [r for r in load_jsonl(ERRORS) if r.get("error_id") == GRANDFATHER_ERROR_ID]
        self.assertTrue(rows, msg="E-23 must be appended; do not reuse E-12")
        latest = rows[-1]
        self.assertEqual(latest["affected_run_id"], RUN01_ID)
        self.assertIn("CODE_COMMIT", latest["tema"])
        self.assertNotEqual(latest["error_id"], "E-12")
        self.assertIn(RUN01_ID, grandfathered_run_ids())

    def test_incident_sha_fails_containment_for_harness_paths(self) -> None:
        """Negative check: 426ca78 exists but does not contain runner/spec."""
        self.assertTrue(CODE_COMMIT_RE.fullmatch(INCIDENT_CODE_COMMIT))
        self.assertTrue(git_object_exists(INCIDENT_CODE_COMMIT))
        missing = paths_missing_from_commit(INCIDENT_CODE_COMMIT, REQUIRED_HARNESS_PATHS)
        self.assertIn("experiments/EXP-BTC-005/src/run_synthetic.py", missing)
        self.assertIn("experiments/EXP-BTC-005/SPEC.md", missing)
        self.assertFalse(
            commit_has_path(
                INCIDENT_CODE_COMMIT,
                "experiments/EXP-BTC-005/src/run_synthetic.py",
            )
        )
        self.assertFalse(
            commit_has_path(INCIDENT_CODE_COMMIT, "experiments/EXP-BTC-005/SPEC.md")
        )
        # Fixture predates the harness; containment must require runner/spec, not fixture alone.
        self.assertTrue(
            commit_has_path(INCIDENT_CODE_COMMIT, "tests/fixtures/e02_gap_hours.csv")
        )

    def test_run01_is_the_known_incident_and_is_grandfathered(self) -> None:
        manifest = json.loads((EXP_DIR / RUN01_ID / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["CODE_COMMIT"], INCIDENT_CODE_COMMIT)
        self.assertIn(RUN01_ID, grandfathered_run_ids())
        missing = paths_missing_from_commit(manifest["CODE_COMMIT"], REQUIRED_HARNESS_PATHS)
        self.assertTrue(missing, msg="RUN-01 CODE_COMMIT must still fail containment")

    def test_non_grandfathered_runs_code_commit_contains_harness(self) -> None:
        grandfathered = grandfathered_run_ids()
        manifests = iter_run_manifests()
        self.assertTrue(manifests)
        checked = 0
        for run_id, manifest in manifests:
            sha = manifest.get("CODE_COMMIT")
            self.assertIsInstance(sha, str)
            self.assertRegex(sha, r"^[0-9a-f]{40}$")
            self.assertTrue(git_object_exists(sha), msg=f"{run_id} CODE_COMMIT is not a git object: {sha}")
            if run_id in grandfathered:
                continue
            missing = paths_missing_from_commit(sha, REQUIRED_HARNESS_PATHS)
            self.assertEqual(
                missing,
                [],
                msg=(
                    f"{run_id} MANIFEST.CODE_COMMIT={sha} does not contain executed harness code: "
                    f"missing {missing}"
                ),
            )
            checked += 1
        # After RUN-02 exists this is >= 1. Before that, grandfathered-only is allowed.
        if any(run_id not in grandfathered for run_id, _ in manifests):
            self.assertGreaterEqual(checked, 1)

    def test_incident_sha_would_fail_if_used_on_a_new_run(self) -> None:
        """Same function new runs use: 426ca78 must not pass as a CODE_COMMIT."""
        missing = paths_missing_from_commit(INCIDENT_CODE_COMMIT, REQUIRED_HARNESS_PATHS)
        self.assertTrue(missing)
        fake_new_run_would_fail = bool(missing) or not git_object_exists(INCIDENT_CODE_COMMIT)
        self.assertTrue(fake_new_run_would_fail)


if __name__ == "__main__":
    unittest.main()
