# R0-B receipt

TASK_ID: R0-B  
ENDED: 2026-09-02  
OBJECTIVE: DATA_AUDIT of legacy BTCUSDT 1h + exact calendar-time lookup (E-02). No strategy rerun.

## Preconditions

- start commit: `9823726c982a96ae556618d4df3cce7ef340230e`
- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778` (unchanged)

## DATA_AUDIT

- spec: `data/catalog/DATA_AUDIT_SPEC.md`
- result: `data/catalog/results/DATA_AUDIT.json` SHA-256 `d3f0acf82229f0d77ce68c340b4ff495cd4ba5653e544a893f6559567851c347`
- gap report: `data/catalog/results/GAP_REPORT.csv` SHA-256 `b717a9516ddb5a6ecf204c00714f2827a9fa0c27a2407d20995bfe40b1065abc`
- mechanical_gate: PASS
- dataset path: `btc_tsmom_replication/btcusdt_1h.csv`
- dataset SHA-256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- n_rows: 78986
- period: 2017-08-17 04:00 UTC → 2026-08-26 13:00 UTC
- missing hours: 128 (28 gap runs). Not imputed.

Inherited v3/v4.1 claims for n, start, end, uniqueness, OHLC, missing-hour count: reproduced.

UNKNOWN (not invented): provider endpoint, retrieved_at, transform commit.

## E-02

- fixture: `tests/fixtures/e02_gap_hours.csv`
- legacy row-offset fails the 2h lookback across a missing 03:00 bar
- exact timestamp lookup finds t−2h = 02:00; t−1h is ineligible
- no nearest-bar fallback

## Tests

`python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants -v`

15 tests OK.

## Not done

- no Calendar / Extreme / Breakout / Vol rerun
- Extreme strategy code still uses its own copies; economic impact of E-02 is a later named task
- dataset file not moved or rewritten

## Errors

- E-01: hash is KNOWN in DATA_AUDIT.json; provenance still UNKNOWN (OPEN)
- E-02: primitive fixed and tested; strategy rerun not done (FIXED_PENDING_VERIFICATION)
