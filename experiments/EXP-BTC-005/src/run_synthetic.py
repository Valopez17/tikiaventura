#!/usr/bin/env python3
"""EXP-BTC-005 reproducibility harness. Not a strategy. Not a scan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = EXP_DIR / "SPEC.md"
DATA_PATH = REPO / "tests" / "fixtures" / "e02_gap_hours.csv"
CANONICAL_RUN_ID = "RUN-BTC-005-20260902-01"
CANONICAL_RUN_DIR = EXP_DIR / CANONICAL_RUN_ID
FORBIDDEN_DATA = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"

EXPECTED_DATA_SHA256 = "44f72413970da754428e887cfd068e26866f8e2058b17c4b42abab4b1350bffd"
EXPECTED_ROWS = 6
EXPECTED_DUPLICATES = 0
EXPECTED_GAPS = 1
EXPECTED_MISSING = ("2020-01-01 03:00:00",)

HASH_CONTRACT_FILES = (
    "outputs/SYNTHETIC_RETURNS.csv",
    "outputs/SYNTHETIC_GAPS.csv",
    "result/RESULT.json",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def fmt_ts(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "UNKNOWN"


def environment() -> dict:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def load_bars(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for raw in reader:
            rows.append(
                {
                    "timestamp_utc": raw["timestamp_utc"],
                    "ts": parse_ts(raw["timestamp_utc"]),
                    "close": float(raw["close"]),
                }
            )
    return rows


def compute(data_path: Path, spec_path: Path) -> dict:
    if data_path.resolve() == FORBIDDEN_DATA.resolve():
        raise RuntimeError("live 1h CSV is forbidden in EXP-BTC-005")

    data_sha = sha256_file(data_path)
    spec_sha = sha256_file(spec_path)
    bars = load_bars(data_path)
    timestamps = [b["ts"] for b in bars]
    n_rows = len(bars)
    n_duplicates = n_rows - len(set(timestamps))

    missing: list[str] = []
    n_gap_runs = 0
    if bars:
        t = timestamps[0]
        end = timestamps[-1]
        present = set(timestamps)
        in_run = False
        while t <= end:
            if t not in present:
                missing.append(fmt_ts(t))
                if not in_run:
                    n_gap_runs += 1
                    in_run = True
            else:
                in_run = False
            t = t + timedelta(hours=1)

    returns: list[dict] = []
    for prev, curr in zip(bars, bars[1:]):
        elapsed = int((curr["ts"] - prev["ts"]).total_seconds() // 3600)
        simple = curr["close"] / prev["close"] - 1.0
        returns.append(
            {
                "timestamp_prev_utc": prev["timestamp_utc"],
                "timestamp_curr_utc": curr["timestamp_utc"],
                "elapsed_hours": elapsed,
                "simple_return": f"{simple:.12f}",
            }
        )

    warnings: list[str] = []
    gates = {
        "fixture_sha256_match": data_sha == EXPECTED_DATA_SHA256,
        "input_rows": n_rows == EXPECTED_ROWS,
        "duplicates": n_duplicates == EXPECTED_DUPLICATES,
        "gaps": len(missing) == EXPECTED_GAPS,
        "missing_hours_exact": tuple(missing) == EXPECTED_MISSING,
    }
    if not all(gates.values()):
        warnings.append(f"spec checks failed: {gates}")
    mechanical_gate = "PASS" if all(gates.values()) else "FAIL"

    return {
        "data_path": str(data_path.relative_to(REPO)).replace("\\", "/"),
        "data_sha256": data_sha,
        "spec_path": str(spec_path.relative_to(REPO)).replace("\\", "/"),
        "spec_sha256": spec_sha,
        "input_rows": n_rows,
        "duplicates": n_duplicates,
        "gaps": len(missing),
        "gap_runs": n_gap_runs,
        "missing_hours": missing,
        "returns": returns,
        "n_returns": len(returns),
        "n_elapsed_eq_1h": sum(1 for r in returns if r["elapsed_hours"] == 1),
        "n_elapsed_gt_1h": sum(1 for r in returns if r["elapsed_hours"] > 1),
        "mechanical_gate": mechanical_gate,
        "gates": gates,
        "warnings": warnings,
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_returns_csv(returns: list[dict]) -> str:
    lines = ["timestamp_prev_utc,timestamp_curr_utc,elapsed_hours,simple_return"]
    for row in returns:
        lines.append(
            f"{row['timestamp_prev_utc']},{row['timestamp_curr_utc']},"
            f"{row['elapsed_hours']},{row['simple_return']}"
        )
    return "\n".join(lines) + "\n"


def render_gaps_csv(missing: list[str]) -> str:
    lines = ["timestamp_utc"]
    lines.extend(missing)
    return "\n".join(lines) + "\n"


def result_payload(computed: dict) -> dict:
    return {
        "data_path": computed["data_path"],
        "data_sha256": computed["data_sha256"],
        "duplicates": computed["duplicates"],
        "experiment_id": "EXP-BTC-005",
        "gap_runs": computed["gap_runs"],
        "gaps": computed["gaps"],
        "input_rows": computed["input_rows"],
        "mechanical_gate": computed["mechanical_gate"],
        "missing_hours": computed["missing_hours"],
        "n_elapsed_eq_1h": computed["n_elapsed_eq_1h"],
        "n_elapsed_gt_1h": computed["n_elapsed_gt_1h"],
        "n_returns": computed["n_returns"],
        "not_a_trading_edge": True,
        "role": "REPRODUCIBILITY_HARNESS",
        "spec_path": computed["spec_path"],
        "spec_sha256": computed["spec_sha256"],
    }


def write_run_tree(run_dir: Path, computed: dict) -> dict[str, str]:
    outputs_dir = run_dir / "outputs"
    result_dir = run_dir / "result"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    returns_path = outputs_dir / "SYNTHETIC_RETURNS.csv"
    gaps_path = outputs_dir / "SYNTHETIC_GAPS.csv"
    result_path = result_dir / "RESULT.json"

    write_text(returns_path, render_returns_csv(computed["returns"]))
    write_text(gaps_path, render_gaps_csv(computed["missing_hours"]))
    write_text(
        result_path,
        json.dumps(result_payload(computed), indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )

    return {
        "outputs/SYNTHETIC_RETURNS.csv": sha256_file(returns_path),
        "outputs/SYNTHETIC_GAPS.csv": sha256_file(gaps_path),
        "result/RESULT.json": sha256_file(result_path),
    }


def write_manifest(
    run_dir: Path,
    run_id: str,
    command: str,
    computed: dict,
    output_hashes: dict[str, str],
    started_at: str,
    ended_at: str,
) -> None:
    manifest = {
        "RUN_ID": run_id,
        "EXPERIMENT_ID": "EXP-BTC-005",
        "STARTED_AT": started_at,
        "ENDED_AT": ended_at,
        "SPEC_HASH": computed["spec_sha256"],
        "CODE_COMMIT": git_head(),
        "COMMAND": command,
        "ENVIRONMENT": environment(),
        "RANDOM_SEED": None,
        "RAW_DATA_ID": computed["data_path"],
        "RAW_DATA_HASH": computed["data_sha256"],
        "PROCESSED_DATA_ID": None,
        "PROCESSED_DATA_HASH": None,
        "INPUT_ROWS": computed["input_rows"],
        "GAPS": computed["gaps"],
        "DUPLICATES": computed["duplicates"],
        "OUTPUT_FILES": [
            {"path": rel, "sha256": digest} for rel, digest in output_hashes.items()
        ],
        "TESTS": "python3 -m unittest tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids -v",
        "WARNINGS": computed["warnings"],
        "MECHANICAL_GATE": computed["mechanical_gate"],
        "role": "REPRODUCIBILITY_HARNESS",
        "not_a_trading_edge": True,
        "hash_contract_files": list(HASH_CONTRACT_FILES),
        "hash_contract_note": (
            "Byte-identical contract covers SYNTHETIC_RETURNS.csv, "
            "SYNTHETIC_GAPS.csv, RESULT.json only. STARTED_AT/ENDED_AT, "
            "CODE_COMMIT, and ENVIRONMENT may differ across machines."
        ),
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
) -> None:
    lines = [
        "# Run receipt — RUN-BTC-005 harness",
        "",
        f"RUN_ID: {run_id}",
        "",
        "DELTA / OBJETIVO VERIFICABLE: Prove v4.1 §3.12 on a tiny fixture. Not a strategy.",
        "",
        "FILES CHANGED: this run folder only (spec/src live under EXP-BTC-005/).",
        "",
        f"COMMAND: `{command}`",
        "",
        "TEST RESULT: see registries/runs.jsonl and R0-C receipt after the unittest suite.",
        "",
        f"INPUT HASHES: {computed['data_path']} SHA-256 {computed['data_sha256']}",
        f"SPEC_HASH: {computed['spec_sha256']}",
        "",
        "OUTPUT HASHES:",
    ]
    for rel, digest in output_hashes.items():
        lines.append(f"- `{rel}` SHA-256 `{digest}`")
    lines.extend(
        [
            "",
            "PRIMARY METRICS: none (harness). Counts only: "
            f"rows={computed['input_rows']} gaps={computed['gaps']} "
            f"duplicates={computed['duplicates']} n_returns={computed['n_returns']}.",
            "",
            "CONTROL RESULT: not applicable.",
            "",
            "UNCERTAINTY: not applicable.",
            "",
            "N/TRIALS: 1 predeclared harness.",
            "",
            f"MECHANICAL GATE: {computed['mechanical_gate']}",
            "",
            "SPEC DEVIATIONS: none.",
            "",
            "BLOCKERS: none for this harness. Live 1h CSV not used. E-02 economic impact not measured.",
            "",
            "REGISTERS UPDATED: recorded separately in registries/runs.jsonl by R0-C.",
            "",
            "not_a_trading_edge: true",
            "",
        ]
    )
    write_text(run_dir / "receipt.md", "\n".join(lines))


def canonical_output_hashes() -> dict[str, str]:
    manifest_path = CANONICAL_RUN_DIR / "MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"canonical manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


def verify() -> int:
    started = utc_now_iso()
    computed = compute(DATA_PATH, SPEC_PATH)
    tmp = Path(tempfile.mkdtemp(prefix="exp-btc-005-verify-"))
    try:
        hashes = write_run_tree(tmp, computed)
        expected = canonical_output_hashes()
        mismatches = []
        for rel in HASH_CONTRACT_FILES:
            got = hashes.get(rel)
            want = expected.get(rel)
            if got != want:
                mismatches.append({"path": rel, "expected": want, "observed": got})
        ended = utc_now_iso()
        report = {
            "STARTED_AT": started,
            "ENDED_AT": ended,
            "MECHANICAL_GATE": "PASS" if not mismatches and computed["mechanical_gate"] == "PASS" else "FAIL",
            "mismatches": mismatches,
            "observed": hashes,
            "expected": expected,
            "spec_sha256": computed["spec_sha256"],
            "data_sha256": computed["data_sha256"],
        }
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
        return 0 if report["MECHANICAL_GATE"] == "PASS" else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def materialize(run_id: str, command: str) -> int:
    run_dir = EXP_DIR / run_id
    if run_dir.exists():
        print(
            f"REFUSE overwrite of existing run folder: {run_dir} (DEC-005 immutable outputs)",
            file=sys.stderr,
        )
        return 2
    started = utc_now_iso()
    computed = compute(DATA_PATH, SPEC_PATH)
    run_dir.mkdir(parents=True, exist_ok=False)
    hashes = write_run_tree(run_dir, computed)
    ended = utc_now_iso()
    write_manifest(run_dir, run_id, command, computed, hashes, started, ended)
    write_receipt(run_dir, run_id, command, computed, hashes)
    print(json.dumps({"run_dir": str(run_dir), "hashes": hashes, "MECHANICAL_GATE": computed["mechanical_gate"]}, indent=2))
    return 0 if computed["mechanical_gate"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-BTC-005 reproducibility harness (not a strategy)")
    parser.add_argument("--verify", action="store_true", help="recompute in temp dir and compare to canonical hashes")
    parser.add_argument("--run-id", help="write a new immutable run folder under experiments/EXP-BTC-005/")
    args = parser.parse_args(argv)

    if args.verify and args.run_id:
        print("use either --verify or --run-id, not both", file=sys.stderr)
        return 2
    if args.verify:
        return verify()
    if not args.run_id:
        print("required: --verify or --run-id RUN-...", file=sys.stderr)
        return 2
    if not args.run_id.startswith("RUN-"):
        print("run-id must start with RUN-", file=sys.stderr)
        return 2
    command = "python3 experiments/EXP-BTC-005/src/run_synthetic.py --run-id " + args.run_id
    return materialize(args.run_id, command)


if __name__ == "__main__":
    raise SystemExit(main())
