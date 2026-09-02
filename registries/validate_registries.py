#!/usr/bin/env python3
"""Validate registry JSONL files against local schemas. No extra packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT / "schemas"

FILES = {
    "ideas.jsonl": "idea.schema.json",
    "hypotheses.jsonl": "hypothesis.schema.json",
    "experiments.jsonl": "experiment.schema.json",
    "runs.jsonl": "run.schema.json",
    "decisions.jsonl": "decision.schema.json",
    "errors.jsonl": "error.schema.json",
}


def load_schema(name: str) -> dict:
    path = SCHEMAS / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema.get("type") != "object":
        raise ValueError(f"{name}: type must be object")
    if "required" not in schema or not schema["required"]:
        raise ValueError(f"{name}: missing required fields")
    return schema


def check_pattern(value: str, pattern: str) -> bool:
    return re.search(pattern, value) is not None


def validate_record(record: dict, schema: dict, where: str) -> None:
    for field in schema["required"]:
        if field not in record:
            raise ValueError(f"{where}: missing required field {field}")
    props = schema.get("properties", {})
    for key, spec in props.items():
        if key not in record:
            continue
        value = record[key]
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            raise ValueError(f"{where}: {key} must be string")
        if expected == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{where}: {key} must be boolean")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"{where}: {key}={value!r} not in enum")
        if "const" in spec and value != spec["const"]:
            raise ValueError(f"{where}: {key} must be {spec['const']!r}")
        if "pattern" in spec and isinstance(value, str) and not check_pattern(value, spec["pattern"]):
            raise ValueError(f"{where}: {key} does not match {spec['pattern']}")
        if spec.get("minLength") and isinstance(value, str) and len(value) < spec["minLength"]:
            raise ValueError(f"{where}: {key} too short")


def validate_jsonl(filename: str, schema: dict) -> int:
    path = ROOT / filename
    text = path.read_text(encoding="utf-8")
    n = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"{filename}:{i}: record must be an object")
        validate_record(record, schema, f"{filename}:{i}")
        n += 1
    return n


def main() -> int:
    total = 0
    for jsonl, schema_name in FILES.items():
        schema = load_schema(schema_name)
        n = validate_jsonl(jsonl, schema)
        print(f"OK {jsonl} ({n} records) schema={schema_name}")
        total += n
    print(f"OK {len(FILES)} schemas, {total} records")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — report and fail the task
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
