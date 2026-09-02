"""E-02: row offset ≠ elapsed calendar time."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from temporal.exact_timestamp import lookback_index, lookup_exact  # noqa: E402
from temporal.legacy_row_offset import lookback_index_row_offset  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "e02_gap_hours.csv"
HOUR = pd.Timedelta(hours=1)


def load_fixture() -> tuple[pd.DatetimeIndex, pd.DataFrame]:
    df = pd.read_csv(FIXTURE)
    ts = pd.to_datetime(df["timestamp_utc"], utc=True)
    return pd.DatetimeIndex(ts), df


class E02ExactTimestampTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ts, self.df = load_fixture()
        self.t_04 = pd.Timestamp("2020-01-01 04:00:00", tz="UTC")
        self.i_04 = lookup_exact(self.ts, self.t_04)
        self.assertIsNotNone(self.i_04)

    def test_gap_exists_at_03(self) -> None:
        self.assertIsNone(lookup_exact(self.ts, pd.Timestamp("2020-01-01 03:00:00", tz="UTC")))

    def test_legacy_row_offset_fails_two_hour_lookback_across_gap(self) -> None:
        # Two rows back from 04:00 is 01:00, not 02:00.
        legacy = lookback_index_row_offset(self.i_04, 2)
        self.assertEqual(self.ts[legacy], pd.Timestamp("2020-01-01 01:00:00", tz="UTC"))
        self.assertNotEqual(self.ts[legacy], pd.Timestamp("2020-01-01 02:00:00", tz="UTC"))

    def test_exact_lookback_two_hours_from_04_is_02(self) -> None:
        exact = lookback_index(self.ts, self.t_04, 2 * HOUR)
        self.assertIsNotNone(exact)
        self.assertEqual(self.ts[exact], pd.Timestamp("2020-01-01 02:00:00", tz="UTC"))

    def test_exact_lookback_one_hour_from_04_ineligible(self) -> None:
        self.assertIsNone(lookback_index(self.ts, self.t_04, HOUR))

    def test_no_nearest_bar_fallback(self) -> None:
        # Missing 03:00 must not resolve to 02:00 or 04:00.
        self.assertIsNone(lookback_index(self.ts, self.t_04, HOUR))
        self.assertNotEqual(
            lookback_index(self.ts, self.t_04, 2 * HOUR),
            lookup_exact(self.ts, self.t_04),
        )


if __name__ == "__main__":
    unittest.main()
