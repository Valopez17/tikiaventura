# BTC spot 1h — live snapshot

**As of:** 2026-09-02  
**Source of rules:** `governance/ACTIVE_RECTOR.md`  
**This file** holds mutable operational state so the rector document is not rewritten for routine status.

| Field | Value |
|---|---|
| Stage | R0 — operating system |
| Last closed Cursor task | EXT-C03..C06 / H1 L6 audit |
| Next Cursor task | none until Valita names a TASK-ID |
| Active computational experiment | none |
| Active live alert | none |
| Frozen rule | none (Valita freeze/discard pending; EXT-H01 pending) |
| Prospective rule | none |
| Real capital | $0 |
| Dataset | legacy `btc_tsmom_replication/btcusdt_1h.csv`; SHA-256 `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103` |
| PRICE-ONLY | current-phase restriction |
| R0-H01 / E-18 alert utility | OPEN |
| DATA_AUDIT | PASS — `data/catalog/results/DATA_AUDIT.json` (isfinite; SHA NOT_APPLICABLE; exact count deltas = 0) |
| E-02 | CLOSED — primitive tested; EXT-C02 executed; Valita closed after PR #3 merge |
| E-03 | FIXED_PENDING_VERIFICATION — H1 survivor gate implemented/applied; not CLOSED |
| E-04 | FIXED_PENDING_VERIFICATION — hourly MTM implemented for frozen L6; not CLOSED |
