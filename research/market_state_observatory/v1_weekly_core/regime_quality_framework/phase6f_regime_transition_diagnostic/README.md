# H3 — Regime / transition diagnostic

Diagnostic only. **No new model.** Reconstruct frozen L=0 M_MACRO
walk-forward probabilities and score them by crypto `state_direction`
and a backward-looking 4-week transition flag.

No new features. No lag 4/8. No interactions. No 2024–2026.
Not a trading backtest. 2021–2023 is **temporal robustness**, not clean OOS.

## Inputs (read-only)

- Phase 3 catalog (`state_direction`, `future_return_4w` / `12w`)
- Phase 6A `macro_weekly.csv`
- Phase 6E `macro_lag_metrics.csv` (L=0 sanity check only)

Weekly probabilities are reconstructed with the frozen L=0 spec:

`DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`

Logistic L2 `C=1.0`, train-only median + scaler, min train N=100,
mature labels `s <= t - H`.

## Slices

- Regime at t: `BULL` / `NEUTRAL` / `BEAR` (catalog `state_direction`)
- Persistence: `PREV_STATE` = `state_direction` at t−4; TRANSITION vs PERSISTENT
- Directional transitions (N, prevalence, mean p, observed rate, Brier only)

M0 is the original expanding all-market base rate, **scored on the same
weeks** as M_MACRO inside each slice.

## Run

```bash
python3 src/analyze_regime_transition_performance.py
```

## Outputs

- `results/regime_transition_metrics.csv`
- `results/REGIME_TRANSITION_DIAGNOSTIC.md`
