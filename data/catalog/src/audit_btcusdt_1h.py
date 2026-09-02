#!/usr/bin/env python3
"""R0-B DATA_AUDIT for legacy BTCUSDT 1h. Does not rewrite the file. No strategy."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "data" / "catalog" / "DATA_AUDIT_SPEC.md"
SRC = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
OUT_DIR = REPO / "data" / "catalog" / "results"
AUDIT_JSON = OUT_DIR / "DATA_AUDIT.json"
GAP_CSV = OUT_DIR / "GAP_REPORT.csv"

CLAIM_N = 78986
CLAIM_START = "2017-08-17 04:00:00"
CLAIM_END = "2026-08-26 13:00:00"
CLAIM_MISSING = 128
CLAIM_SOURCE = "Binance BTCUSDT Spot"
CLAIM_INTERVAL = "1h"
CLAIM_SHA256 = "TBC"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_float_array(s: pd.Series) -> np.ndarray:
    return np.asarray(s, dtype=float)


def finiteness_breakdown(arr: np.ndarray) -> dict[str, int]:
    """Row-or-element counts using real finiteness, not pandas notna()."""
    a = np.asarray(arr, dtype=float)
    return {
        "n_nonfinite": int(np.count_nonzero(~np.isfinite(a))),
        "n_nan": int(np.count_nonzero(np.isnan(a))),
        "n_posinf": int(np.count_nonzero(np.isposinf(a))),
        "n_neginf": int(np.count_nonzero(np.isneginf(a))),
    }


def ohlc_volume_validity(df: pd.DataFrame) -> dict:
    """Validity counters. Non-finite = NaN / +inf / -inf via numpy.isfinite."""
    o = _as_float_array(df["open"])
    h = _as_float_array(df["high"])
    low = _as_float_array(df["low"])
    c = _as_float_array(df["close"])
    ohlc = np.column_stack([o, h, low, c])
    row_finite = np.isfinite(ohlc).all(axis=1)
    ohlc_break = {
        "n_nonfinite_ohlc": int(np.count_nonzero(~row_finite)),
        "n_nan_ohlc": int(np.count_nonzero(np.isnan(ohlc).any(axis=1))),
        "n_posinf_ohlc": int(np.count_nonzero(np.isposinf(ohlc).any(axis=1))),
        "n_neginf_ohlc": int(np.count_nonzero(np.isneginf(ohlc).any(axis=1))),
    }
    n_nonpositive = int(np.count_nonzero(row_finite & ((o <= 0) | (h <= 0) | (low <= 0) | (c <= 0))))
    n_high_lt_low = int(np.count_nonzero(row_finite & (h < low)))
    n_open_out = int(np.count_nonzero(row_finite & ((o < low) | (o > h))))
    n_close_out = int(np.count_nonzero(row_finite & ((c < low) | (c > h))))

    vol_out: dict = {
        "n_invalid_volume": None,
        "n_nonfinite_volume": None,
        "n_nan_volume": None,
        "n_posinf_volume": None,
        "n_neginf_volume": None,
        "n_negative_volume": None,
    }
    if "volume" in df.columns:
        v = _as_float_array(df["volume"])
        v_finite = np.isfinite(v)
        vb = finiteness_breakdown(v)
        n_neg = int(np.count_nonzero(v_finite & (v < 0)))
        vol_out = {
            "n_invalid_volume": int(vb["n_nonfinite"] + n_neg),
            "n_nonfinite_volume": vb["n_nonfinite"],
            "n_nan_volume": vb["n_nan"],
            "n_posinf_volume": vb["n_posinf"],
            "n_neginf_volume": vb["n_neginf"],
            "n_negative_volume": n_neg,
        }

    return {
        **ohlc_break,
        "n_nonpositive_ohlc": n_nonpositive,
        "n_high_lt_low": n_high_lt_low,
        "n_open_outside_low_high": n_open_out,
        "n_close_outside_low_high": n_close_out,
        **vol_out,
    }


def last_row_ohlc_complete(row: pd.Series) -> bool:
    o = float(row["open"])
    h = float(row["high"])
    low = float(row["low"])
    c = float(row["close"])
    vals = np.array([o, h, low, c], dtype=float)
    if not bool(np.isfinite(vals).all()):
        return False
    return o > 0 and h > 0 and low > 0 and c > 0 and h >= low and low <= o <= h and low <= c <= h


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SRC.is_file():
        raise SystemExit(f"FAIL unreadable {SRC}")

    sha = sha256_file(SRC)
    size = SRC.stat().st_size
    df = pd.read_csv(SRC)
    n = int(len(df))
    cols = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in cols}

    ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    n_unparsed = int(ts.isna().sum())
    naive_has_z = bool(df["timestamp_utc"].astype(str).str.contains("Z|\\+", regex=True).any())

    validity = ohlc_volume_validity(df)
    n_nonfinite_ohlc = validity["n_nonfinite_ohlc"]
    n_nonpositive = validity["n_nonpositive_ohlc"]
    n_high_lt_low = validity["n_high_lt_low"]
    n_open_out = validity["n_open_outside_low_high"]
    n_close_out = validity["n_close_outside_low_high"]
    n_vol_invalid = validity["n_invalid_volume"]

    unique = bool(ts.nunique(dropna=False) == n and n_unparsed == 0)
    chrono = bool(ts.is_monotonic_increasing) and unique
    n_dup_ts = int(n - ts.nunique(dropna=False))

    tmin = ts.min()
    tmax = ts.max()
    expected = pd.date_range(tmin, tmax, freq="h", tz="UTC")
    observed = pd.DatetimeIndex(ts)
    missing = expected.difference(observed)
    extra = observed.difference(expected)
    n_missing = int(len(missing))

    gaps = []
    if len(missing):
        miss = pd.DatetimeIndex(missing)
        hour = pd.Timedelta(hours=1)
        run_start = miss[0]
        prev = miss[0]
        for t in miss[1:]:
            if t == prev + hour:
                prev = t
                continue
            n_h = int((prev - run_start) / hour) + 1
            gaps.append((run_start, prev, n_h))
            run_start = t
            prev = t
        n_h = int((prev - run_start) / hour) + 1
        gaps.append((run_start, prev, n_h))

    gap_rows = []
    hour = pd.Timedelta(hours=1)
    for start, end, n_h in gaps:
        t = start
        while t <= end:
            gap_rows.append(
                {
                    "missing_timestamp_utc": str(t),
                    "gap_run_start_utc": str(start),
                    "gap_run_end_utc": str(end),
                    "gap_length_hours": int(n_h),
                }
            )
            t = t + hour

    length_dist = Counter(int(g[2]) for g in gaps)
    last = df.iloc[-1]
    last_complete = last_row_ohlc_complete(last)

    start_match = str(tmin.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")) == CLAIM_START
    end_match = str(tmax.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")) == CLAIM_END
    n_match = n == CLAIM_N
    miss_match = n_missing == CLAIM_MISSING
    n_rows_delta = int(n - CLAIM_N)
    missing_hours_delta = int(n_missing - CLAIM_MISSING)

    corruption = []
    if n_dup_ts > 0:
        corruption.append("duplicate timestamps")
    if n_unparsed > 0 or not chrono:
        corruption.append("timestamp parse/order failure")
    if n_nonfinite_ohlc or n_nonpositive or n_high_lt_low or n_open_out or n_close_out:
        corruption.append("OHLC corruption")
    if n_vol_invalid:
        corruption.append("invalid volume")

    claim_mismatch = []
    if not n_match:
        claim_mismatch.append(f"n_rows mismatch claimed={CLAIM_N} observed={n} delta={n_rows_delta}")
    if not miss_match:
        claim_mismatch.append(
            f"missing_hours mismatch claimed={CLAIM_MISSING} observed={n_missing} delta={missing_hours_delta}"
        )

    if corruption:
        gate = "FAIL"
        stop_reasons = corruption + claim_mismatch
    elif claim_mismatch:
        gate = "BLOCKED"
        stop_reasons = claim_mismatch
    else:
        gate = "PASS"
        stop_reasons = []

    ohlc_valid = not (
        n_nonfinite_ohlc or n_nonpositive or n_high_lt_low or n_open_out or n_close_out
    )

    audit = {
        "spec": str(SPEC.relative_to(REPO)),
        "dataset_id": "BTCUSDT_SPOT_1H_LEGACY",
        "path": str(SRC.relative_to(REPO)),
        "mechanical_gate": gate,
        "stop_reasons": stop_reasons,
        "KNOWN": {
            "sha256": sha,
            "size_bytes": int(size),
            "n_rows": n,
            "n_header_lines_on_disk": 1,
            "columns": cols,
            "dtypes": dtypes,
            "timestamp_column": "timestamp_utc",
            "timestamp_parsed_as": "UTC (pandas utc=True); naive strings have no Z/offset"
            if not naive_has_z
            else "offset present in strings",
            "naive_strings_contain_offset": naive_has_z,
            "n_unparsed_timestamps": n_unparsed,
            "t_min_utc": str(tmin),
            "t_max_utc": str(tmax),
            "unique_timestamps": unique,
            "chronological": chrono,
            "n_duplicate_timestamps": n_dup_ts,
            "n_expected_hourly_bars_inclusive": int(len(expected)),
            "n_missing_hours": n_missing,
            "n_unexpected_timestamps": int(len(extra)),
            "n_gap_runs": int(len(gaps)),
            "gap_length_hours_distribution": {str(k): int(v) for k, v in sorted(length_dist.items())},
            "n_nonfinite_ohlc": n_nonfinite_ohlc,
            "n_nan_ohlc": validity["n_nan_ohlc"],
            "n_posinf_ohlc": validity["n_posinf_ohlc"],
            "n_neginf_ohlc": validity["n_neginf_ohlc"],
            "n_nonpositive_ohlc": n_nonpositive,
            "n_high_lt_low": n_high_lt_low,
            "n_open_outside_low_high": int(n_open_out),
            "n_close_outside_low_high": int(n_close_out),
            "n_invalid_volume": n_vol_invalid,
            "n_nonfinite_volume": validity["n_nonfinite_volume"],
            "n_nan_volume": validity["n_nan_volume"],
            "n_posinf_volume": validity["n_posinf_volume"],
            "n_neginf_volume": validity["n_neginf_volume"],
            "n_negative_volume": validity["n_negative_volume"],
            "last_row_timestamp_utc": str(ts.iloc[-1]),
            "last_row_ohlc_complete": last_complete,
        },
        "DOCUMENTED_LEGACY_CLAIM": {
            "source": CLAIM_SOURCE,
            "interval": CLAIM_INTERVAL,
            "n_bars": CLAIM_N,
            "t_min": CLAIM_START + " UTC",
            "t_max": CLAIM_END + " UTC",
            "unique_and_ordered": True,
            "ohlc_valid": True,
            "missing_hours": CLAIM_MISSING,
            "sha256": CLAIM_SHA256,
            "reproduced": {
                "n_bars": n_match,
                "t_min": start_match,
                "t_max": end_match,
                "unique_and_ordered": unique and chrono,
                "ohlc_valid": ohlc_valid,
                "missing_hours": miss_match,
                "sha256": None,
            },
        },
        "claim_comparison": {
            "n_rows": {
                "claimed": CLAIM_N,
                "observed": n,
                "delta": n_rows_delta,
                "match": n_match,
            },
            "missing_hours": {
                "claimed": CLAIM_MISSING,
                "observed": n_missing,
                "delta": missing_hours_delta,
                "match": miss_match,
            },
        },
        "sha256_comparison": {
            "status": "NOT_APPLICABLE",
            "legacy_recorded_value": CLAIM_SHA256,
            "current_sha256": sha,
            "reason": "inherited claim recorded SHA-256 as TBC; no prior hash exists to compare",
        },
        "UNKNOWN": {
            "provider_endpoint": None,
            "retrieved_at_utc": None,
            "request_parameters": None,
            "transform_code_commit": None,
            "inclusive_exclusive_download_window": None,
            "whether_a_later_closed_bar_existed_at_retrieval": None,
            "price_economic_units": None,
            "volume_economic_units": None,
        },
        "notes": [
            "Each CSV row is treated as a completed hourly bar (historical kline dump). That does not reconstruct retrieved_at.",
            "Naive timestamp_utc strings are interpreted as UTC clock time, not a local exchange timezone.",
            "Gaps are missing expected hours on the UTC hourly grid from t_min to t_max inclusive. Prices were not imputed.",
            "Non-finite checks use numpy.isfinite (NaN, +inf, -inf). pandas.notna does not treat inf as missing.",
            "KNOWN records observed columns and dtypes only. Economic units of price/volume are UNKNOWN.",
            "SHA-256 comparison is NOT_APPLICABLE because the inherited claim was TBC, not a mismatch.",
        ],
    }

    AUDIT_JSON.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(gap_rows).to_csv(GAP_CSV, index=False)
    print(
        json.dumps(
            {
                "gate": audit["mechanical_gate"],
                "sha256": sha,
                "n_rows": n,
                "n_missing": n_missing,
                "n_rows_delta": n_rows_delta,
                "missing_hours_delta": missing_hours_delta,
                "stop": stop_reasons,
            },
            indent=2,
        )
    )
    return 1 if gate != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
