"""Loader so repo-root unittest discovery runs the EXP-BTC-005 repro contract."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments" / "EXP-BTC-005" / "tests"))

from test_repro import SyntheticReproTests  # noqa: E402,F401
