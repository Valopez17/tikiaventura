# R0-B receipt

TASK_ID: R0-B / R0-B-AUDIT-FIX  
ENDED: 2026-09-02  
OBJECTIVE: DATA_AUDIT of legacy BTCUSDT 1h + exact calendar-time lookup (E-02). No strategy rerun.

## Preconditions (R0-B)

- start commit: `9823726c982a96ae556618d4df3cce7ef340230e`
- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778` (unchanged)

## R0-B-AUDIT-FIX

ChatGPT found three auditor bugs. Spec was updated **before** the rerun. Only DATA_AUDIT was rerun (not a strategy).

| Fix | Change |
|---|---|
| Non-finite | `numpy.isfinite` (NaN / +inf / −inf). `pandas.notna` is not used for this check. |
| Units | KNOWN = columns + dtypes. `price_economic_units` / `volume_economic_units` = UNKNOWN. |
| SHA | current SHA = KNOWN; comparison = NOT_APPLICABLE (legacy was TBC). Not a mismatch. |
| Counts | exact `n_rows` and `missing_hours` deltas always reported. Any nonzero delta → BLOCKED. |

- R0-B-AUDIT-FIX start commit: `9bfa2e837274fe5bc90ebfa3f95afc99a5af5511`
- dataset file not rewritten

## DATA_AUDIT

- spec: `data/catalog/DATA_AUDIT_SPEC.md`
- result: `data/catalog/results/DATA_AUDIT.json` SHA-256 `7b741f9e5c781e3d8c56dee204529ea03ac5cc559d501c7adeeb0961bc56d895`
- gap report: `data/catalog/results/GAP_REPORT.csv` SHA-256 `b717a9516ddb5a6ecf204c00714f2827a9fa0c27a2407d20995bfe40b1065abc`
- mechanical_gate: PASS
- dataset path: `btc_tsmom_replication/btcusdt_1h.csv`
- dataset SHA-256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- n_rows: 78986 (delta vs claim = 0)
- period: 2017-08-17 04:00 UTC → 2026-08-26 13:00 UTC
- missing hours: 128 (delta vs claim = 0); 28 gap runs. Not imputed.

Inherited v3/v4.1 claims for n, start, end, uniqueness, OHLC, missing-hour count: reproduced exactly.

UNKNOWN (not invented): provider endpoint, retrieved_at, transform commit, price/volume economic units.

SHA comparison: NOT_APPLICABLE.

## E-02

- fixture: `tests/fixtures/e02_gap_hours.csv`
- legacy row-offset fails the 2h lookback across a missing 03:00 bar
- exact timestamp lookup finds t−2h = 02:00; t−1h is ineligible
- no nearest-bar fallback
- not wired into legacy strategy code; economic impact not measured

## Tests

`python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite -v`

25 tests OK.

## Not done

- no Calendar / Extreme / Breakout / Vol rerun
- Extreme strategy code still uses its own copies; economic impact of E-02 is a later named task
- dataset file not moved or rewritten
- R0-C not started

## Errors

- E-01: hash is KNOWN in DATA_AUDIT.json; provenance still UNKNOWN (OPEN)
- E-02: primitive fixed and tested; strategy rerun not done (FIXED_PENDING_VERIFICATION)
