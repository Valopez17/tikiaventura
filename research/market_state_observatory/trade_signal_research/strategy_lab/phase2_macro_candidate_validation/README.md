# Phase 2 — Macro LONG/CASH candidate validation

Try to **break** the frozen Phase 1 candidate `C_macro_long_cash`.

Not a live system. Not clean OOS. No retuning.

## Frozen rule (do not change)

- Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`
- Model: L2 logistic, `C=1.0`, train-only median + scaler, min train 100
- Target: BTC Friday-to-Friday 12-week return > 0
- Decision: `P_macro >= 0.50` → LONG BTC, else CASH
- Long only. No leverage. Weekly decisions. Cash earns 0.

## Question

Does the candidate remain economically interesting after realistic timing,
implementation delay, costs, and temporal stress?

## Predeclared execution variants

- **V0** — Phase 1 reconstruction (Friday UTC close). Not the validated strategy.
- **V1** — Friday information set; BTC execution Saturday 00:00 UTC (primary realistic).
- **V2** — V1 signal, +24h execution delay.
- **V3** — V1 signal, +72h execution delay.
- **V4** — one-week information lag (no current-Friday macro); execute at V1 timestamp.

Costs: 0 / 10 / 20 / 50 bps round trip. Not optimized.

## Run

```bash
python3 src/validate_macro_strategy.py
```

Uses existing Phase 1 daily BTC splice, 1h BTCUSDT, and cached weekly macro.
Needs network only if the macro cache is missing.

## Outputs

- `results/VALIDATION_SUMMARY.csv`
- `results/TIMING_AUDIT.csv`
- `results/ROBUSTNESS_TESTS.csv`
- `results/MACRO_STRATEGY_VALIDATION.md`
