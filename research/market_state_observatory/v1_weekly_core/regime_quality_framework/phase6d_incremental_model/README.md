# Phase 6D — Crypto vs Macro vs Combined (incremental walk-forward)

Compare three **frozen** logistic specs for 12w crypto outcomes against an
expanding base rate.

No feature search. No interactions. No 2024–2026. Not a trading backtest.

## Inputs (read-only)

- Phase 3 `opportunity_episode_catalog.csv`
- Phase 4 `bull_quality_weekly.csv` (Bull-week dynamics; catalog formula on other weeks)
- Phase 6A `macro_weekly.csv`

## Frozen specs

| model | features |
|---|---|
| C0 | expanding mature base rate |
| CRYPTO | `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE` |
| MACRO | `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` |
| COMBINED | CRYPTO + MACRO (concatenated; no interactions) |

Logistic L2 `C=1.0`. Train-only median imputation and standardization.
Mature labels: train `s <= t - 12`. Min train N=100.

Primary target: `future_return_12w > 0`. Secondary: `> +20%`.

## Run

```bash
python3 src/run_incremental_walkforward.py
```

## Outputs

- `results/incremental_metrics.csv`
- `results/INCREMENTAL_ANALYSIS.md`
