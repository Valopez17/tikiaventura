#!/usr/bin/env python3
"""R0-B DATA_AUDIT for legacy BTCUSDT 1h. Does not rewrite the file. No strategy."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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

    o = df["open"].astype(float)
    h = df["high"].astype(float)
    low = df["low"].astype(float)
    c = df["close"].astype(float)
    vol = df["volume"].astype(float) if "volume" in df.columns else None

    finite_ohlc = o.notna() & h.notna() & low.notna() & c.notna()
    n_nonfinite_ohlc = int((~finite_ohlc).sum())
    n_nonpositive = int(((o <= 0) | (h <= 0) | (low <= 0) | (c <= 0)).sum())
    n_high_lt_low = int((h < low).sum())
    n_open_out = int(((o < low) | (o > h)).sum()) if n else 0
    n_close_out = int(((c < low) | (c > h)).sum()) if n else 0
    n_vol_invalid = int((~vol.notna() | (vol < 0)).sum()) if vol is not None else None

    unique = bool(ts.nunique(dropna=False) == n and n_unparsed == 0)
    chrono = bool(ts.is_monotonic_increasing) and unique
    n_dup_ts = int(n - ts.nunique(dropna=False))

    tmin = ts.min()
    tmax = ts.max()
    expected = pd.date_range(tmin, tmax, freq="h", tz="UTC")
    observed = pd.DatetimeIndex(ts)
    missing = expected.difference(observed)
    extra = observed.difference(expected)

    gaps = []
    if len(missing):
        miss = pd.DatetimeIndex(missing)
        # consecutive missing hours → runs
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
    for start, end, n_h in gaps:
        t = start
        hour = pd.Timedelta(hours=1)
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
    last_ohlc_complete = bool(
        pd.notna(last["open"])
        and pd.notna(last["high"])
        and pd.notna(last["low"])
        and pd.notna(last["close"])
        and float(last["open"]) > 0
        and float(last["close"]) > 0
        and float(last["high"]) >= float(last["low"])
    )

    start_match = str(tmin.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")) == CLAIM_START
    end_match = str(tmax.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")) == CLAIM_END
    n_match = n == CLAIM_N
    miss_match = int(len(missing)) == CLAIM_MISSING

    stop = False
    stop_reasons = []
    if n_dup_ts > 0:
        stop = True
        stop_reasons.append("duplicate timestamps")
    if n_unparsed > 0 or not chrono:
        stop = True
        stop_reasons.append("timestamp parse/order failure")
    if n_nonfinite_ohlc or n_nonpositive or n_high_lt_low or n_open_out or n_close_out:
        stop = True
        stop_reasons.append("OHLC corruption")
    if vol is not None and n_vol_invalid:
        stop = True
        stop_reasons.append("invalid volume")
    if not n_match or not miss_match:
        # row/gap count mismatch is documented; only stop if large
        if abs(n - CLAIM_N) > 1 or abs(int(len(missing)) - CLAIM_MISSING) > 5:
            stop = True
            stop_reasons.append("material count mismatch vs inherited claim")

    audit = {
        "spec": str(SPEC.relative_to(REPO)),
        "dataset_id": "BTCUSDT_SPOT_1H_LEGACY",
        "path": str(SRC.relative_to(REPO)),
        "mechanical_gate": "FAIL" if stop else "PASS",
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
            "n_missing_hours": int(len(missing)),
            "n_unexpected_timestamps": int(len(extra)),
            "n_gap_runs": int(len(gaps)),
            "gap_length_hours_distribution": {str(k): int(v) for k, v in sorted(length_dist.items())},
            "n_nonfinite_ohlc": n_nonfinite_ohlc,
            "n_nonpositive_ohlc": n_nonpositive,
            "n_high_lt_low": n_high_lt_low,
            "n_open_outside_low_high": int(n_open_out),
            "n_close_outside_low_high": int(n_close_out),
            "n_invalid_volume": n_vol_invalid,
            "last_row_timestamp_utc": str(ts.iloc[-1]),
            "last_row_ohlc_complete": last_ohlc_complete,
            "units_observed": "prices float; volume float (base-asset units if Binance kline)",
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
            "sha256": "TBC",
            "reproduced": {
                "n_bars": n_match,
                "t_min": start_match,
                "t_max": end_match,
                "unique_and_ordered": unique and chrono,
                "ohlc_valid": not (
                    n_nonfinite_ohlc or n_nonpositive or n_high_lt_low or n_open_out or n_close_out
                ),
                "missing_hours": miss_match,
                "sha256": False,
            },
        },
        "UNKNOWN": {
            "provider_endpoint": None,
            "retrieved_at_utc": None,
            "request_parameters": None,
            "transform_code_commit": None,
            "inclusive_exclusive_download_window": None,
            "whether_a_later_closed_bar_existed_at_retrieval": None,
        },
        "notes": [
            "Each CSV row is treated as a completed hourly bar (historical kline dump). That does not reconstruct retrieved_at.",
            "Naive timestamp_utc strings are interpreted as UTC clock time, not a local exchange timezone.",
            "Gaps are missing expected hours on the UTC hourly grid from t_min to t_max inclusive. Prices were not imputed.",
        ],
    }

    AUDIT_JSON.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(gap_rows).to_csv(GAP_CSV, index=False)
    print(json.dumps({"gate": audit["mechanical_gate"], "sha256": sha, "n_rows": n, "n_missing": int(len(missing)), "stop": stop_reasons}, indent=2))
    return 1 if stop else 0


if __name__ == "__main__":
    raise SystemExit(main())
