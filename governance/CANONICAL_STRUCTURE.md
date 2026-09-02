# Canonical structure — destination map

Created by R0-A. This is the target layout from v4.1 §3.11.

Physical migration of datasets, experiment code, and historical outputs is **not** executed here. Legacy paths remain the live locations until a later named task moves them without breaking hashes.

```
tikiaventura/
├── BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md   # ACTIVE rector (see governance/ACTIVE_RECTOR.md)
├── BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4.md     # historical v4; do not overwrite
├── V4_TO_V4_1_CHANGELOG.md
├── governance/                                # this folder
├── archive/rectors/                           # destination for historical rector copies
├── data/raw/                                  # destination for immutable downloads
├── data/processed/                            # destination for versioned transforms
├── data/catalog/                              # destination for manifests / DATA_AUDIT
├── projects/btc_spot_1h/                      # BTC project status
├── registries/                                # append-only records + schemas
├── experiments/                               # future EXP-ID runs (empty)
├── products/alerts/                           # empty until freeze
├── btc_tsmom_replication/                     # LEGACY location; not moved
└── research/                                  # LEGACY location; not moved
```

The purpose/rent of each canonical area must be documented in its README or in another canonical governance file. A README is not required when that purpose is already documented unambiguously elsewhere. Do not add READMEs only to fill a folder template.

No database, dashboard, orchestration, agents, or alert engine.
