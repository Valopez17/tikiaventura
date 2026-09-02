"""DATA_AUDIT must reject NaN / +inf / -inf via numpy.isfinite, not pandas.notna()."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "data" / "catalog" / "src"))

from audit_btcusdt_1h import last_row_ohlc_complete, ohlc_volume_validity  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "ohlc_nonfinite.csv"


def load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


class NonfiniteAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = load_fixture()
        self.v = ohlc_volume_validity(self.df)

    def test_notna_misses_inf_isfinite_does_not(self) -> None:
        inf_open = self.df["open"].iloc[1]
        self.assertTrue(np.isposinf(inf_open))
        self.assertTrue(pd.notna(inf_open))
        self.assertFalse(bool(np.isfinite(inf_open)))

    def test_plus_inf_open_counted_nonfinite(self) -> None:
        self.assertGreaterEqual(self.v["n_posinf_ohlc"], 1)
        self.assertGreaterEqual(self.v["n_nonfinite_ohlc"], 1)

    def test_minus_inf_high_counted_nonfinite(self) -> None:
        self.assertGreaterEqual(self.v["n_neginf_ohlc"], 1)

    def test_nan_close_counted_nonfinite(self) -> None:
        self.assertGreaterEqual(self.v["n_nan_ohlc"], 1)

    def test_plus_inf_volume_invalid(self) -> None:
        self.assertGreaterEqual(self.v["n_posinf_volume"], 1)
        self.assertGreaterEqual(self.v["n_invalid_volume"], 1)

    def test_minus_inf_volume_invalid(self) -> None:
        self.assertGreaterEqual(self.v["n_neginf_volume"], 1)

    def test_finite_row_not_flagged_by_itself(self) -> None:
        clean = self.df.iloc[[0]].copy()
        v = ohlc_volume_validity(clean)
        self.assertEqual(v["n_nonfinite_ohlc"], 0)
        self.assertEqual(v["n_nan_ohlc"], 0)
        self.assertEqual(v["n_posinf_ohlc"], 0)
        self.assertEqual(v["n_neginf_ohlc"], 0)
        self.assertEqual(v["n_invalid_volume"], 0)

    def test_last_row_inf_is_not_complete(self) -> None:
        inf_row = self.df.iloc[1]
        self.assertFalse(last_row_ohlc_complete(inf_row))
        self.assertTrue(last_row_ohlc_complete(self.df.iloc[0]))

    def test_fixture_counts_expected(self) -> None:
        # rows 1,2,3 have non-finite OHLC; rows 4,5 have non-finite volume only.
        self.assertEqual(self.v["n_nonfinite_ohlc"], 3)
        self.assertEqual(self.v["n_posinf_ohlc"], 1)
        self.assertEqual(self.v["n_neginf_ohlc"], 1)
        self.assertEqual(self.v["n_nan_ohlc"], 1)
        self.assertEqual(self.v["n_nonfinite_volume"], 2)
        self.assertEqual(self.v["n_posinf_volume"], 1)
        self.assertEqual(self.v["n_neginf_volume"], 1)
        self.assertEqual(self.v["n_invalid_volume"], 2)


if __name__ == "__main__":
    unittest.main()
