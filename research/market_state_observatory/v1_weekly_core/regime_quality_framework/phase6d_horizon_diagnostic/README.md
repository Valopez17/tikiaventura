# H1 — Horizon diagnostic (CRYPTO vs MACRO at 4w / 8w / 12w)

Compare frozen **M0**, **M_CRYPTO**, and **M_MACRO** logistic specs for the
sign of subsequent market return at three fixed horizons.

No combined model. No feature search. No lag search. No 2024–2026.
Not a trading backtest. 2021–2023 is **temporal robustness**, not clean OOS.

## Inputs (read-only)

- Phase 3 `opportunity_episode_catalog.csv`
- Phase 4 `bull_quality_weekly.csv` (Bull-week dynamics; catalog formula on other weeks)
- Phase 6A `macro_weekly.csv`

`future_return_8w` is not in the catalog. It is derived from catalog
`future_return_4w` as the exclusive window t+1…t+8:

`(1 + r4_t) * (1 + r4_{t+4}) - 1`

which equals compounding the existing weekly market-return series over
those eight weeks. No new crypto download.

## Frozen specs (same features at every horizon)

| model | features |
|---|---|
| M0 | expanding mature base rate |
| M_CRYPTO | `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE` |
| M_MACRO | `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` |

Only target: `Y_H = 1` if `future_return_Hw > 0`.

Logistic L2 `C=1.0`. Train-only median imputation and standardization.
Mature labels: train `s <= t - H`. Min train N=100.

## Run

```bash
python3 src/run_horizon_diagnostic.py
```

## Outputs

- `results/horizon_metrics.csv`
- `results/HORIZON_DIAGNOSTIC.md`
