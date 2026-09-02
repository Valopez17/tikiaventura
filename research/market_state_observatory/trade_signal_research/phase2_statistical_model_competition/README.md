# Phase 2 — Statistical model competition

Chronological 80/20 holdout. Expanding walk-forward on the first 80%.
The last 20% is opened once, after freeze.

Not a trading strategy. Not a PnL study.

## Frozen choices

- Targets: `UP_60D` (60d return > +20%), `ADVERSE_60D` (60d MAE < −15%)
- Features: six expanding BTC percentiles + four frozen macro 12w changes
- Models: M0 base rate, M1 L2 logistic, M2 probit, M3 elastic-net logistic,
  M4 additive spline GLM (GAM substitute), M5 shallow GBM
- Selection on development walk-forward only: BSS>0, LogLoss < M0, AUC>0.55
- If none qualify: **NONE** (do not pick the least-bad model)

## Run

```bash
python3 src/run_model_competition.py
```

Needs network for Binance daily klines and the four macro series (2024+).

## Outputs

- `results/feature_spec.md` (includes the split date)
- `results/model_metrics.csv`
- `results/MODEL_COMPETITION.md`
