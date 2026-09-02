# H2 — Macro lag diagnostic

Test whether the frozen four-feature **macro block at week t** is more
informative for crypto returns that start **now**, in **4 weeks**, or in
**8 weeks**.

No crypto features. No extra lags. No extra horizons. No 2024–2026.
Not a trading backtest. Not a lag search beyond the pre-specified grid.
2021–2023 is **temporal robustness**, not clean OOS.

## Grid (frozen)

Lags `L ∈ {0, 4, 8}`. Horizons `H ∈ {4, 8, 12}`.

Outcome at week t: compound crypto market return over the exclusive window

`t+L+1 … t+L+H`

Target: `Y = 1` if that return `> 0`.

Train maturity: `s <= t - (L + H)`. Min train N=100.

## Inputs (read-only)

- Phase 3 `opportunity_episode_catalog.csv` (`future_return_4w` chained into windows)
- Phase 6A `macro_weekly.csv`

Windows are compounds of catalog 4w returns (the existing weekly market-return
series already baked into those 4w paths). No new crypto download.

## Models

| model | spec |
|---|---|
| M0 | expanding mature base rate |
| M_MACRO | `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` |

Logistic L2 `C=1.0`. Train-only median imputation and standardization.

## Run

```bash
python3 src/run_macro_lag_diagnostic.py
```

## Outputs

- `results/macro_lag_metrics.csv`
- `results/MACRO_LAG_DIAGNOSTIC.md`
