# Phase 5 — Crypto-only walk-forward benchmark

Temporal validation, **2015–2023 only**. Question: using information available at week `t`,
do crypto-only variables improve 4w/12w probability forecasts beyond simple baselines?

This is **not** a trading backtest. No macro. No 2024–2026. No hyperparameter search.

## Inputs (read-only)

- Phase 3 `opportunity_episode_catalog.csv` (levels, outcomes, V1 state)
- Phase 4 `bull_quality_weekly.csv` (dynamics on Bull weeks; same convention)
- V1 `weekly_market_state.csv` (join only if a state column is missing)

Dynamics on non-Bull weeks use the Phase 4 formula (4-week change on the catalog).
Bull-week dynamics are taken from Phase 4 when present.

## Frozen model specs

| model | method |
|---|---|
| M0 | expanding base rate of mature outcomes |
| M1 | V1 `market_state` conditional frequency |
| M2 | logistic L2, crypto levels |
| M3 | logistic L2, levels + dynamics |
| M4 | logistic L2, HIGH_MOM (`MOM_12W_PERCENTILE >= 0.70`) only |

Logistic: `C=1.0` L2, scaler and median imputation fit on the **training** window only.
Mature label at `t` for horizon `h`: training week `s` satisfies `s <= t - h`.

JUICY_12W threshold = P90 of `future_return_12w` on **2015–2020** complete-horizon weeks. Frozen.

## Run

```bash
python3 src/run_crypto_walkforward.py
```

## Outputs

- `results/walkforward_predictions.csv`
- `results/walkforward_metrics.csv`
- `results/walkforward_calibration.csv`
- `results/CRYPTO_WALKFORWARD_ANALYSIS.md`
