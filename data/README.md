# data — destination only

Canonical destinations from v4.1 §3.11. **Nothing was moved in R0-A.**

| Canonical path | Role | Live legacy path today |
|---|---|---|
| `data/raw/` | immutable downloads | `btc_tsmom_replication/btcusdt_1h.csv` |
| `data/processed/` | versioned transforms | none for BTC 1h yet |
| `data/catalog/` | manifests / DATA_AUDIT | `data/catalog/results/DATA_AUDIT.json` (R0-B) |

Do not place new research outputs here until a named migration task preserves hashes.
