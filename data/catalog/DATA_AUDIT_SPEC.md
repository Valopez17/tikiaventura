# DATA_AUDIT spec — BTCUSDT Spot 1h legacy

**experiment_type:** REPRODUCTION (dataset audit, no strategy)  
**spec_status:** APPROVED for R0-B / R0-B-AUDIT-FIX  
**dataset_id:** BTCUSDT_SPOT_1H_LEGACY  
**path:** `btc_tsmom_replication/btcusdt_1h.csv`  
**do_not_move:** true  
**impute_prices:** false  
**fill_gaps:** false  

## Question

What is the actual byte identity, temporal integrity, and OHLC validity of the inherited 1h file, and which v3 documentary claims are KNOWN vs UNKNOWN?

## Not in this spec

- No strategy backtest.
- No Calendar / Extreme / Breakout / Vol rerun.
- No gap filling.
- No file rewrite.

## Checks (frozen before run)

1. path, byte size, SHA-256
2. row count (header excluded)
3. columns and dtypes as observed from the file. Numeric nature of OHLC/volume columns may be stated. Economic units (quote vs base, contract multiplier, etc.) are not KNOWN unless reconstructible from the file alone.
4. timestamp parse, timezone convention
5. min/max timestamp
6. uniqueness, chronological order
7. duplicate timestamps
8. expected hourly grid vs observed; gap list and length distribution
9. OHLC invalid: non-finite (not `numpy.isfinite`: NaN, +inf, −inf), finite and <= 0, high < low, open/close outside [low, high]
10. volume invalid if column exists: non-finite (NaN, +inf, −inf) or finite and < 0
11. last row present and OHLC-complete (closed-kline interpretation; completeness uses `isfinite`, not merely non-null)
12. comparison to v3/v4.1 documentary claims without rewriting those claims

## Provenance labels

| Label | Meaning |
|---|---|
| KNOWN | Measured from this file in this run |
| DOCUMENTED LEGACY CLAIM | Stated in v4.1 §3.1; reproduced or not by this run |
| UNKNOWN | Not reconstructible from the file (provider endpoint, retrieved_at, transform commit, economic units) |
| NOT_APPLICABLE | Comparison cannot be performed because the inherited claim has no value to compare (e.g. SHA-256 recorded as TBC) |

Do not invent UNKNOWN fields.

KNOWN must not assert volume/price economic units that cannot be reconstructed from the CSV bytes.

## SHA-256 vs inherited claim

The inherited claim records SHA-256 as **TBC**. Current file SHA-256 is KNOWN. The comparison to a prior hash is **NOT_APPLICABLE**. It is not a mismatch and must not be reported as `reproduced.sha256 = false`.

## Claim comparison — exact

Compare observed vs inherited claims with **exact equality**. No hidden numeric tolerance.

Always report, even when they match:

- `n_rows` claimed, observed, delta (`observed − claimed`)
- `missing_hours` claimed, observed, delta (`observed − claimed`)

Any nonzero delta on row count or missing-hour count is a **BLOCK**: stop the wider R0-B task and report the exact numbers. Do not continue to E-02 implementation in that case.

Start/end timestamp strings, uniqueness, order, and OHLC validity are also compared exactly (boolean reproduce flags).

## Stop

Stop the wider R0-B task (do not implement E-02) if this run finds:

- duplicate timestamps that cannot be ignored as a count of zero;
- unsorted time after a unique-timestamp check;
- OHLC corruption (invalid rows > 0) that would silently poison later tests;
- volume invalid rows > 0;
- `n_rows` ≠ inherited claim 78986 (exact);
- `n_missing_hours` ≠ inherited claim 128 (exact).

A documentation-only SHA TBC, or UNKNOWN provenance fields, is not a stop.

## Outputs

- `data/catalog/results/DATA_AUDIT.json` (canonical numbers)
- `data/catalog/results/GAP_REPORT.csv` (one row per missing expected hour)
- stdout summary only; markdown receipt may link these files

## Mechanical gate

- PASS: file readable; hash recorded; uniqueness/order/OHLC/volume checks completed with zero invalid rows; exact n_rows and missing_hours match inherited claims; gaps listed without imputation
- FAIL: unreadable file, or stop-condition corruption (duplicates, order, OHLC, volume)
- BLOCKED: exact mismatch of `n_rows` or `missing_hours` vs inherited claim (no corruption required)
