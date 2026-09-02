# Simple strategy discovery

Executable test of three frozen BTC ideas. Historical backtest / temporal robustness.
**Not clean OOS.** 2024–2026 has already been inspected in this project. Not a live system.

Primary cost: **10 bps round trip** per completed trade. Start `$10,000`. Long only. Cash earns 0.

## Lead table (10 bps round trip)

| STRATEGY | ENDING $ FROM $10K | BUY&HOLD $ | CAGR | MAX DD | SHARPE | TRADES | VERDICT |
|---|---|---|---|---|---|---|---|
| A 20:00-24:00 | $3,764 | $191,169 | -10.26% | -78.95% | -0.27 | 3273 | NOT TRADEABLE |
| B hold_3d | $12,575 | $68,355 | 3.90% | -34.00% | 0.33 | 20 | INTERESTING BUT WEAK |
| B hold_7d | $9,968 | $68,355 | -0.05% | -34.53% | 0.09 | 20 | NOT TRADEABLE |
| B hold_14d | $9,320 | $68,355 | -1.17% | -37.53% | 0.08 | 20 | NOT TRADEABLE |
| B hold_30d | $17,727 | $68,355 | 10.03% | -47.79% | 0.44 | 20 | INTERESTING BUT WEAK |
| B hold_60d | $18,421 | $68,355 | 10.74% | -62.26% | 0.46 | 15 | INTERESTING BUT WEAK |
| C macro LONG/CASH | $1,474,846 | $737,554 | 68.86% | -83.77% | 1.15 | 16 | TRADEABLE CANDIDATE |

Buy & Hold is computed over the **same dates** as that row. Do not compare ending wealth across rows with different date ranges.

## Answers

### 1. Did any session anomaly produce economically meaningful returns?

Selected window `20:00-24:00` on the full available 1h sample: $10,000 → $3,764 (CAGR -10.26%, Sharpe -0.27, avg trade -0.020%, n=3273) vs Buy & Hold $191,169. 
After 10 bps round trip the selected session did **not** produce a positive average trade. A 4-hour window cannot absorb 10 bps/day unless the raw move is large.

### 2. Did it survive the later temporal period?

Discovery (first 70% of complete-window dates): ending $6,053, Sharpe -0.11, avg trade -0.010%.
Temporal robustness (last 30%): ending $6,218, Sharpe -0.98, avg trade -0.044%, vs Buy & Hold $18,411.
The frozen window did **not** keep a positive average trade on later dates. The discovery ranking did not survive.

### 3. Which fixed UTC window was selected in discovery?

**`20:00-24:00`**

Ranking rule, frozen before looking at the last 30%: highest Sharpe at 10 bps on discovery dates that have all six windows. Tie-break: total return, then average trade. No hour-grid search.

Discovery (10 bps), all six windows:

| WINDOW | ENDING $ | CAGR | SHARPE | AVG TRADE | N |
|---|---|---|---|---|---|
| 00:00-04:00 | $195 | -46.30% | -1.87 | -0.159% | 2291 |
| 04:00-08:00 | $2,073 | -22.00% | -0.87 | -0.060% | 2291 |
| 08:00-12:00 | $719 | -34.01% | -1.23 | -0.102% | 2291 |
| 12:00-16:00 | $3,037 | -17.15% | -0.33 | -0.034% | 2291 |
| 16:00-20:00 | $1,750 | -24.05% | -0.73 | -0.063% | 2291 |
| 20:00-24:00 ← SELECTED | $6,053 | -7.62% | -0.11 | -0.010% | 2291 |

The selected window was **not** changed after seeing the later period.

### 4. Did capitulation + deleveraging produce profitable trades?

Raw signals (all three filters): **21**. Taken under no-overlap (3d variant may differ by horizon): ignored overlapping prints: 1.

Signal dates (raw):

| date | ret_1d | oi_change_1d | perp_volume_rel_30d | taken_any_horizon |
|---|---:|---:|---:|---|
| 2020-09-03 | -10.96% | -27.13% | 2.23 | yes |
| 2020-11-26 | -8.39% | -28.74% | 2.32 | yes |
| 2021-01-11 | -7.20% | -18.62% | 3.30 | yes |
| 2021-02-23 | -9.61% | -19.55% | 3.12 | yes |
| 2021-04-18 | -6.43% | -25.02% | 2.19 | yes |
| 2021-05-19 | -14.38% | -49.53% | 3.31 | yes |
| 2021-09-07 | -11.01% | -37.26% | 2.07 | yes |
| 2021-12-04 | -8.30% | -40.15% | 2.09 | yes |
| 2022-01-21 | -10.41% | -16.11% | 2.59 | yes |
| 2022-05-09 | -11.64% | -14.51% | 2.81 | yes |
| 2022-05-11 | -6.17% | -10.34% | 2.55 | yes |
| 2022-06-13 | -15.38% | -18.73% | 3.21 | yes |
| 2022-09-13 | -9.92% | -24.32% | 2.34 | yes |
| 2022-11-08 | -9.93% | -17.09% | 3.96 | yes |
| 2023-08-17 | -7.33% | -15.61% | 3.54 | yes |
| 2023-12-11 | -5.79% | -14.30% | 2.41 | yes |
| 2024-03-05 | -6.63% | -17.45% | 5.28 | yes |
| 2024-08-05 | -7.12% | -20.73% | 4.18 | yes |
| 2025-03-03 | -8.54% | -17.66% | 2.63 | yes |
| 2025-10-10 | -7.31% | -30.40% | 3.32 | yes |
| 2026-02-05 | -14.02% | -15.03% | 3.24 | yes |

Independent holding-period results at 10 bps (no silent selection):

| HOLD | END $ | BH $ | CAGR | AVG TRADE | AVG MAE | AVG MFE | N | VERDICT |
|---|---|---|---|---|---|---|---|---|
| hold_3d | $12,575 | $68,355 | 3.90% | 1.34% | -6.05% | 6.58% | 20 | INTERESTING BUT WEAK |
| hold_7d | $9,968 | $68,355 | -0.05% | 0.23% | -8.56% | 7.45% | 20 | NOT TRADEABLE |
| hold_14d | $9,320 | $68,355 | -1.17% | -0.06% | -9.80% | 9.02% | 20 | NOT TRADEABLE |
| hold_30d | $17,727 | $68,355 | 10.03% | 3.94% | -10.59% | 15.14% | 20 | INTERESTING BUT WEAK |
| hold_60d | $18,421 | $68,355 | 10.74% | 7.40% | -15.15% | 26.92% | 15 | INTERESTING BUT WEAK |

None of the B variants beat Buy & Hold ending wealth. Milder max DD is mostly non-participation (low exposure), not a superior invested path.

### 5. Which predefined holding horizon looked strongest?

Among the five frozen horizons, **hold_60d** had the highest Sharpe (0.46; ending $18,421; n=15). This is a diagnostic ranking, not an optimized holding period.

### 6. Was that result supported by enough trades to be credible?

Weakly. N=15 is still a small event sample. Treat expectancy as fragile.

### 7. Did macro LONG/CASH beat BTC Buy & Hold?

$10,000 → $1,474,846 strategy vs $737,554 Buy & Hold on the same dates (CAGR 68.86% vs 57.02%). Yes, higher ending wealth.

### 8. Did macro timing materially reduce drawdown?

Strategy max DD -83.77% vs Buy & Hold -83.19%.
No material drawdown reduction.

Time invested 80.06%; time in cash 19.94%. BTC return while strategy LONG 14886.39%; BTC return while strategy CASH -50.79%.
Macro state separated environments in the intended direction (BTC did better while LONG than while CASH).

### 9. Which strategy had the best risk-adjusted return?

**C_macro_long_cash / p_ge_0.50** (Sharpe 1.15, 10 bps, full comparable row).

### 10. Which strategy produced the highest ending wealth from $10,000?

**C_macro_long_cash / p_ge_0.50** ended at $1,474,846 on its own date range. This is not a cross-range ranking; Buy & Hold on that same range is the fair comparator.

### 11. Which effects disappeared after fees?

Edge flipped from positive expectancy to non-positive after 10 bps: A `20:00-24:00` (positive at 0 bps, non-positive average trade at 10 bps); B hold_14d.
A `20:00-24:00` full sample: 0 bps ending $99,492 (avg trade 0.080%) vs 10 bps $3,764 (avg -0.020%) vs 20 bps $142.
Daily session trading pays the round-trip every day; that is the economically relevant stress.

### 12. Classification

| strategy | verdict |
|---|---|
| A session `20:00-24:00` | NOT TRADEABLE |
| B hold_3d | INTERESTING BUT WEAK |
| B hold_7d | NOT TRADEABLE |
| B hold_14d | NOT TRADEABLE |
| B hold_30d | INTERESTING BUT WEAK |
| B hold_60d | INTERESTING BUT WEAK |
| C macro LONG/CASH | TRADEABLE CANDIDATE |

Rules used here (not tuned on the fly): TRADEABLE CANDIDATE requires positive average trade after 10 bps, ending wealth above $10,000, Sharpe > 0, at least 5 trades, and ending wealth above Buy & Hold on the same dates. Milder drawdown from sitting in cash is not enough. B with N<5 cannot be TRADEABLE CANDIDATE. Win rate alone is ignored. Focus is expectancy, compounding, drawdown, robustness, fees.

### 13. Which ONE strategy deserves the next validation phase?

**C_macro_long_cash / p_ge_0.50** (TRADEABLE CANDIDATE). Next phase should freeze this rule and stress it (costs, year splits, implementation delays) — still not a clean OOS claim for 2024–2026.

## Method notes

- Strategy A: Binance BTCUSDT spot 1h. Return = close of last hour in the UTC window / open of first hour − 1. Buy window open, sell window end, cash otherwise. Incomplete last UTC day dropped.
- Discovery = first 70% of dates with all six windows complete. Temporal robustness = remaining 30%. Full-history numbers for the selected window are descriptive.
- Strategy B: expanding 5th percentile of BTC 1d return uses s < t, min 365, same splice as Phase 1. `oi_change_1d` and `perp_volume_rel_30d` from the Phase 3B daily panel. Entry at close t; exit at close t+H. Ignore new signals until exit. MAE/MFE from UTC daily high/low after entry (1h aggregation).
- Strategy C: features `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` unchanged. Expanding walk-forward logistic L2 C=1.0, train-only median + scaler, min train 100, mature labels s ≤ t−12. Target = BTC Friday-to-Friday 12-week return > 0. Threshold 0.50 is frozen. Rebalance Fridays only. Same model class as `MACRO_BASE_CANDIDATE_V1`; the original observatory scored crypto-market return, this lab applies the model to the BTC vehicle.
- Fees: 10 bps round trip = 5 bps at entry and 5 bps at exit for multi-day trades; all 10 bps on same-day session round trips. Sensitivity at 0 and 20 bps. No slippage beyond that.
- Sharpe / vol use daily equity returns × √365. Cash days are zeros.
- Overlapping B signals: ignored until the current hold ends. Documented in `data/processed/strategy_b_signals.csv`.

## Calendar years (10 bps; partial years kept)

| STRATEGY | VARIANT | PERIOD | RETURN | TRADES | WIN RATE | MAX DD |
|---|---|---|---|---|---|---|
| A_session | 20:00-24:00 | year_2017 | 42.60% | 135 | 53.33% | -11.00% |
| A_session | 20:00-24:00 | year_2018 | -37.27% | 358 | 48.88% | -48.80% |
| A_session | 20:00-24:00 | year_2019 | -10.78% | 360 | 49.72% | -16.86% |
| A_session | 20:00-24:00 | year_2020 | 11.18% | 362 | 53.31% | -25.88% |
| A_session | 20:00-24:00 | year_2021 | -6.64% | 360 | 49.17% | -34.48% |
| A_session | 20:00-24:00 | year_2022 | -28.47% | 365 | 45.48% | -29.98% |
| A_session | 20:00-24:00 | year_2023 | -1.19% | 365 | 45.75% | -14.97% |
| A_session | 20:00-24:00 | year_2024 | -10.95% | 366 | 50.82% | -18.68% |
| A_session | 20:00-24:00 | year_2025 | -18.44% | 365 | 46.85% | -23.07% |
| A_session | 20:00-24:00 | year_2026 | -16.44% | 237 | 40.93% | -22.45% |
| B_capitulation_deleveraging | hold_3d | year_2020 | 7.03% | 2 | 100.00% | -2.68% |
| B_capitulation_deleveraging | hold_3d | year_2021 | 0.19% | 6 | 50.00% | -13.17% |
| B_capitulation_deleveraging | hold_3d | year_2022 | -20.82% | 5 | 20.00% | -28.66% |
| B_capitulation_deleveraging | hold_3d | year_2023 | 2.38% | 2 | 50.00% | -2.19% |
| B_capitulation_deleveraging | hold_3d | year_2024 | 21.83% | 2 | 100.00% | -1.58% |
| B_capitulation_deleveraging | hold_3d | year_2025 | 6.30% | 2 | 100.00% | -2.72% |
| B_capitulation_deleveraging | hold_3d | year_2026 | 11.68% | 1 | 100.00% | -1.83% |
| B_capitulation_deleveraging | hold_7d | year_2020 | 15.21% | 2 | 100.00% | -4.73% |
| B_capitulation_deleveraging | hold_7d | year_2021 | -3.80% | 6 | 66.67% | -23.70% |
| B_capitulation_deleveraging | hold_7d | year_2022 | -20.22% | 5 | 20.00% | -30.13% |
| B_capitulation_deleveraging | hold_7d | year_2023 | 1.48% | 2 | 50.00% | -3.83% |
| B_capitulation_deleveraging | hold_7d | year_2024 | 22.94% | 2 | 100.00% | -4.82% |
| B_capitulation_deleveraging | hold_7d | year_2025 | -14.14% | 2 | 0.00% | -18.26% |
| B_capitulation_deleveraging | hold_7d | year_2026 | 5.24% | 1 | 100.00% | -6.15% |
| B_capitulation_deleveraging | hold_14d | year_2020 | 14.60% | 2 | 100.00% | -7.36% |
| B_capitulation_deleveraging | hold_14d | year_2021 | -13.13% | 6 | 50.00% | -24.53% |
| B_capitulation_deleveraging | hold_14d | year_2022 | -16.16% | 5 | 20.00% | -31.24% |
| B_capitulation_deleveraging | hold_14d | year_2023 | 2.72% | 2 | 50.00% | -6.50% |
| B_capitulation_deleveraging | hold_14d | year_2024 | 6.73% | 2 | 50.00% | -15.32% |
| B_capitulation_deleveraging | hold_14d | year_2025 | -4.28% | 2 | 0.00% | -13.26% |
| B_capitulation_deleveraging | hold_14d | year_2026 | 6.40% | 1 | 100.00% | -6.10% |
| B_capitulation_deleveraging | hold_30d | year_2020 | 60.28% | 2 | 100.00% | -8.42% |
| B_capitulation_deleveraging | hold_30d | year_2021 | 6.17% | 6 | 50.00% | -45.88% |
| B_capitulation_deleveraging | hold_30d | year_2022 | -17.83% | 5 | 40.00% | -36.62% |
| B_capitulation_deleveraging | hold_30d | year_2023 | 2.10% | 2 | 50.00% | -9.21% |
| B_capitulation_deleveraging | hold_30d | year_2024 | 21.49% | 2 | 100.00% | -15.24% |
| B_capitulation_deleveraging | hold_30d | year_2025 | -11.31% | 2 | 0.00% | -18.24% |
| B_capitulation_deleveraging | hold_30d | year_2026 | 6.81% | 1 | 100.00% | -9.24% |
| B_capitulation_deleveraging | hold_60d | year_2020 | 125.01% | 2 | 100.00% | -8.42% |
| B_capitulation_deleveraging | hold_60d | year_2021 | 19.77% | 4 | 50.00% | -40.85% |
| B_capitulation_deleveraging | hold_60d | year_2022 | -53.85% | 2 | 0.00% | -56.27% |
| B_capitulation_deleveraging | hold_60d | year_2023 | 9.56% | 2 | 100.00% | -9.21% |
| B_capitulation_deleveraging | hold_60d | year_2024 | 22.63% | 2 | 100.00% | -20.13% |
| B_capitulation_deleveraging | hold_60d | year_2025 | -7.84% | 2 | 50.00% | -26.42% |
| B_capitulation_deleveraging | hold_60d | year_2026 | 9.34% | 1 | 100.00% | -11.85% |
| C_macro_long_cash | p_ge_0.50 | year_2017 | 1199.56% | 1 | 100.00% | -35.09% |
| C_macro_long_cash | p_ge_0.50 | year_2018 | -73.28% | 1 | 100.00% | -81.83% |
| C_macro_long_cash | p_ge_0.50 | year_2019 | 89.49% | 0 | NA | -49.41% |
| C_macro_long_cash | p_ge_0.50 | year_2020 | 301.67% | 0 | NA | -53.60% |
| C_macro_long_cash | p_ge_0.50 | year_2021 | 79.40% | 1 | 0.00% | -53.14% |
| C_macro_long_cash | p_ge_0.50 | year_2022 | -15.22% | 2 | 50.00% | -17.20% |
| C_macro_long_cash | p_ge_0.50 | year_2023 | 101.04% | 5 | 60.00% | -18.89% |
| C_macro_long_cash | p_ge_0.50 | year_2024 | 80.35% | 3 | 66.67% | -26.52% |
| C_macro_long_cash | p_ge_0.50 | year_2025 | -16.46% | 1 | 0.00% | -32.02% |
| C_macro_long_cash | p_ge_0.50 | year_2026 | 8.67% | 2 | 50.00% | -35.11% |

Win rate in the year table is by **entry year**. A multi-week hold can lose inside a calendar year and still be a winning completed trade, or the reverse.

Bad years are not removed.

