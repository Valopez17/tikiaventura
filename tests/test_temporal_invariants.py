"""Temporal invariants for signal/entry/exit, rolling windows, percentiles, fees, blocks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from temporal.exact_timestamp import (  # noqa: E402
    expanding_values_before_t,
    rolling_high_excluding_t,
)
from temporal.trade_invariants import (  # noqa: E402
    build_trade,
    fully_inside_block,
    net_return,
)

FIXTURE = REPO / "tests" / "fixtures" / "e02_gap_hours.csv"
HOUR = pd.Timedelta(hours=1)


def load_fixture() -> tuple[pd.DatetimeIndex, pd.DataFrame]:
    df = pd.read_csv(FIXTURE)
    ts = pd.DatetimeIndex(pd.to_datetime(df["timestamp_utc"], utc=True))
    df = df.copy()
    df.index = ts
    return ts, df


class TemporalInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ts, self.df = load_fixture()
        self.t00 = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
        self.t02 = pd.Timestamp("2020-01-01 02:00:00", tz="UTC")
        self.t04 = pd.Timestamp("2020-01-01 04:00:00", tz="UTC")
        self.t05 = pd.Timestamp("2020-01-01 05:00:00", tz="UTC")
        self.opens = self.df["open"]
        self.highs = self.df["high"]
        self.closes = self.df["close"]

    def test_lookback_with_gap_ineligible_for_incomplete_window(self) -> None:
        # [02:00, 04:00) needs 02:00 and 03:00; 03:00 is missing.
        self.assertIsNone(rolling_high_excluding_t(self.highs, self.ts, self.t04, 2 * HOUR))

    def test_signal_uses_only_information_up_to_t(self) -> None:
        before = expanding_values_before_t(self.closes, self.ts, self.t04)
        self.assertTrue((before.index < self.t04).all())
        self.assertNotIn(self.t04, before.index)
        self.assertNotIn(self.t05, before.index)
        # 04:00 close must not leak into a threshold computed at 04:00.
        self.assertNotIn(float(self.closes.loc[self.t04]), list(before.astype(float)))

    def test_entry_strictly_after_signal(self) -> None:
        legs = build_trade(self.ts, self.opens, self.t04, HOUR)
        self.assertIsNotNone(legs)
        self.assertGreater(legs.entry_ts, legs.signal_ts)
        self.assertEqual(legs.entry_ts, pd.Timestamp("2020-01-01 05:00:00", tz="UTC"))

    def test_exit_exact_timestamp(self) -> None:
        legs = build_trade(self.ts, self.opens, self.t04, HOUR)
        self.assertEqual(legs.exit_ts, pd.Timestamp("2020-01-01 06:00:00", tz="UTC"))
        self.assertEqual(legs.exit_px, float(self.opens.loc[legs.exit_ts]))

    def test_missing_entry_omits_trade(self) -> None:
        # Signal at 02:00 would need entry at 03:00 (gap).
        self.assertIsNone(build_trade(self.ts, self.opens, self.t02, HOUR))

    def test_missing_exit_omits_trade(self) -> None:
        # Signal 05:00 → entry 06:00 → exit 07:00 missing.
        self.assertIsNone(build_trade(self.ts, self.opens, self.t05, HOUR))

    def test_rolling_high_excludes_t(self) -> None:
        rh = rolling_high_excluding_t(self.highs, self.ts, self.t02, 2 * HOUR)
        self.assertEqual(rh, 120.0)  # max(00:00=110, 01:00=120); 02:00 high 130 excluded
        self.assertLess(rh, float(self.highs.loc[self.t02]))

    def test_expanding_percentile_no_future(self) -> None:
        hist = expanding_values_before_t(self.closes, self.ts, self.t02)
        q = float(hist.quantile(0.5))
        self.assertNotIn(self.t02, hist.index)
        self.assertTrue((hist.index < self.t02).all())
        self.assertEqual(set(hist.index), {self.t00, pd.Timestamp("2020-01-01 01:00:00", tz="UTC")})
        self.assertEqual(q, float(hist.median()))

    def test_block_boundary_rejects_exit_on_boundary(self) -> None:
        legs = build_trade(self.ts, self.opens, self.t04, HOUR)
        start = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
        end = pd.Timestamp("2020-01-01 06:00:00", tz="UTC")
        self.assertFalse(fully_inside_block(legs, start, end))
        open_end = pd.Timestamp("2020-01-01 07:00:00", tz="UTC")
        self.assertTrue(fully_inside_block(legs, start, open_end))

    def test_fees_unchanged_by_timestamp_lookup(self) -> None:
        legs = build_trade(self.ts, self.opens, self.t04, HOUR)
        fee_e, fee_x = 0.001, 0.001
        net = net_return(legs.entry_px, legs.exit_px, fee_e, fee_x)
        expected = (1 - fee_e) * (legs.exit_px / legs.entry_px) * (1 - fee_x) - 1
        self.assertEqual(net, expected)
        # Gross path is independent of lookback arithmetic.
        self.assertAlmostEqual(net, (1 - 0.001) * (112.0 / 111.0) * (1 - 0.001) - 1)


if __name__ == "__main__":
    unittest.main()
