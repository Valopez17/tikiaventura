# DATA_AUDIT spec — BTCUSDT Spot 1h legacy

**experiment_type:** REPRODUCTION (dataset audit, no strategy)  
**spec_status:** APPROVED for R0-B  
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
3. columns, dtypes, units as observed
4. timestamp parse, timezone convention
5. min/max timestamp
6. uniqueness, chronological order
7. duplicate timestamps
8. expected hourly grid vs observed; gap list and length distribution
9. OHLC invalid: non-finite, <= 0, high < low, open/close outside [low, high]
10. volume invalid if column exists (non-finite or < 0)
11. last row present and OHLC-complete (closed-kline interpretation)
12. comparison to v3/v4.1 documentary claims without rewriting those claims

## Provenance labels

| Label | Meaning |
|---|---|
| KNOWN | Measured from this file in this run |
| DOCUMENTED LEGACY CLAIM | Stated in v4.1 §3.1; reproduced or not by this run |
| UNKNOWN | Not reconstructible from the file (provider endpoint, retrieved_at, transform commit) |

Do not invent UNKNOWN fields.

## Stop

Stop the wider R0-B task (do not implement E-02) if this run finds:

- duplicate timestamps that cannot be ignored as a count of zero;
- unsorted time after a unique-timestamp check;
- OHLC corruption (invalid rows > 0) that would silently poison later tests;
- a gap count or row count that materially contradicts the inherited claim in a way that changes the scientific meaning of the dataset.

A one-line documentation mismatch that is explained (e.g. header vs body) is not a stop.

## Outputs

- `data/catalog/results/DATA_AUDIT.json` (canonical numbers)
- `data/catalog/results/GAP_REPORT.csv` (one row per missing expected hour)
- stdout summary only; markdown receipt may link these files

## Mechanical gate

- PASS: file readable; hash recorded; uniqueness/order/OHLC/volume checks completed; gaps listed without imputation
- FAIL: unreadable file, or stop-condition corruption
- BLOCKED: unknown
