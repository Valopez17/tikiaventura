# data/catalog

DATA_AUDIT artefacts for the legacy BTCUSDT 1h file. The CSV itself was not moved.

| File | Role |
|---|---|
| `DATA_AUDIT_SPEC.md` | spec frozen before the run |
| `src/audit_btcusdt_1h.py` | audit script (no imputation, no strategy) |
| `results/DATA_AUDIT.json` | machine-generated numbers |
| `results/GAP_REPORT.csv` | one row per missing expected UTC hour |
