# BTC spot 1h — live snapshot

**As of:** 2026-09-03  
**Source of rules:** `governance/ACTIVE_RECTOR.md`  
**This file** holds mutable operational state so the rector document is not rewritten for routine status.

| Field | Value |
|---|---|
| Stage | R1 — landscape and prioritization |
| Last closed Cursor task | EXT-C07 / EXT-H01-H02 closeout |
| Next Cursor task | none until ChatGPT provides and Valita approves the H2 SPEC |
| Next ChatGPT task | select and write the SPEC of H2, "abnormal volume as incremental information after a price move" |
| Active computational experiment | none |
| Active live alert | none |
| Frozen rule | L6_down_p1_rebound_long_H6 — prospective observation only |
| Prospective rule | L6_down_p1_rebound_long_H6 — prospective observation only |
| Real capital | $0 |
| Dataset | legacy `btc_tsmom_replication/btcusdt_1h.csv`; SHA-256 `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103` |
| PRICE-ONLY | current-phase restriction |
| R0-H01 / E-18 alert utility | CLOSED |
| DATA_AUDIT | PASS — `data/catalog/results/DATA_AUDIT.json` (isfinite; SHA NOT_APPLICABLE; exact count deltas = 0) |
| HYP-BTC-002 | INVALIDATED (unchanged) |
| E-02 | CLOSED — primitive tested; EXT-C02 executed; Valita closed after PR #3 merge |
| E-03 | CLOSED — survivor gate implemented, audited, applied; Valita accepted FREEZE_PROSPECTIVE |
| E-04 | CLOSED — equity MTM with intra-trade drawdown implemented, tested, audited |
| E-24 | OPEN — mechanical_gate subset of 17 SPEC conditions; does not block R1/H2 |
