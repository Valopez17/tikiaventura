# Derivatives data audit

Built: `2026-08-30T16:46:48Z`. Sanity only. **Do not retune definitions from stress dates.**

## Mechanical checks

- dates sorted: **True**
- dates unique: **True**
- complete UTC calendar (no missing index days): **True** N=2546
- timezone: index is naive UTC calendar dates (no DST). Funding/premium/klines converted with `tz=UTC`. OI `create_time` has no zone; treated as UTC.

- duplicate funding prints after merge: **0** (must be 0)
- funding prints per day: min=2 median=3 max=3
- funding settlement hours UTC (value counts): {0: 2545, 8: 2546, 16: 2546}

- funding prints after panel end 23:59:59 UTC: **0**
- basis last close times after panel end: **0**

- daily funding aggregation: `funding_rate_last` = last settlement with date t; `funding_mean_1d` = mean of settlements whose UTC date is t. 00:00 UTC print belongs to that calendar day, not the previous day.

- OI non-positive among finite: **0** (must be 0 after dropping trailing 0E-8 snapshots)
- OI max: 1.248e+10 min finite: 3.079e+08
- perp quote volume < 0: **0**
- spot quote volume < 0: **0**

- basis_last finite min/median/max: -0.00178963 / -0.00037136 / 0.00324793
- |basis_last| > 0.05 (5%): **0** — flagged, not dropped
- |basis_last| > 0.2: **0**
- basis implementation (single): `binance_premium_index_1h_close`. Mark/index not mixed. CME not used.

- spot/perp units: both Vision 1d kline **quote asset volume (USDT)**. Phase 1 `binance_btcusdt_1d.csv` volume is **base BTC** and was **not** used. Ratio omitted where either quote series is missing.
- perp_spot_volume_ratio finite min/median/max: 0.7457 / 7.187 / 12.64

- percentiles: `expanding_pctl` uses `hist = x[:t]` (strictly before t), `mean(hist <= xt)`, min 365 finite prior observations. Same as Phase 1 `MIN_HIST=365`. OI threshold was **not** shortened.

### Missing-data pattern

- Funding NaNs before first REST print and nowhere intended inside the funding span except true holes (see coverage).
- Basis NaNs before 2019-12-24.
- Perp NaNs before 2019-12-31.
- OI NaNs before 2020-09-01 by construction (not backfilled).
- `*_pctl` NaN until 365 prior finite observations.
- `funding_mean_7d` / `funding_cum_30d` NaN until 7 / 30 calendar days from first funding day.
- `perp_volume_rel_30d` NaN until 30 prior perp days (Phase 1-style prior median).

## Stress dates (descriptive only)

| date | funding_rate_last | funding_mean_1d | funding_pctl | basis_last | basis_pctl | perp_quote_volume | perp_volume_rel_30d | perp_spot_volume_ratio | oi_value | oi_change_1d | oi_pctl |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2020-03-12 | -0.00015149 | 1.80767e-05 | NA | -3.2e-07 | NA | 4.936e+09 | 3.21607 | 3.03065 | NA | NA | NA |
| 2021-05-19 | -0.00089697 | -0.00014628 | 0.1621 | 0.00097517 | 83.79 | 5.296e+10 | 3.31169 | 3.92945 | 9.102e+08 | -0.495309 | NA |
| 2021-11-10 | 0.00057535 | 0.000544753 | 88.64 | 0.00065098 | 74.16 | 2.315e+10 | 1.54526 | 5.33897 | 3.709e+09 | -0.0763433 | 99.31 |
| 2021-11-11 | 0.00021812 | 0.00018341 | 71.88 | 0.00092491 | 84.75 | 1.158e+10 | 0.772768 | 4.79225 | 3.565e+09 | -0.0387591 | 98.85 |
| 2021-11-12 | 0.00036867 | 0.000301393 | 79.47 | 0.00048959 | 64.86 | 1.692e+10 | 1.14384 | 5.94735 | 3.721e+09 | 0.0438293 | 99.31 |
| 2021-11-13 | 0.00021842 | 0.000230053 | 71.82 | 0.00058972 | 70.61 | 7.984e+09 | 0.539891 | 5.5353 | 3.684e+09 | -0.00994724 | 98.86 |
| 2021-11-14 | 0.00013059 | 0.000123403 | 67.21 | 0.00086793 | 82.63 | 9.45e+09 | 0.639026 | 5.69827 | 3.772e+09 | 0.023769 | 99.54 |
| 2021-11-15 | 0.00040989 | 0.000259533 | 81.56 | 0.00070214 | 76.09 | 1.366e+10 | 0.933405 | 5.54941 | 3.982e+09 | 0.0558168 | 99.55 |
| 2021-11-16 | 0.0001 | 0.00018666 | 65.66 | 0.00031512 | 56.91 | 2.886e+10 | 1.97266 | 6.13336 | 3.65e+09 | -0.0835685 | 98.19 |
| 2021-11-17 | 0.0001 | 0.000110517 | 65.71 | 0.00024062 | 53.34 | 1.718e+10 | 1.16181 | 6.20771 | 3.603e+09 | -0.0126377 | 97.96 |
| 2021-11-18 | 0.00011235 | 0.000104117 | 66.5 | 0.00082152 | 80.55 | 2.413e+10 | 1.63159 | 6.62016 | 3.467e+09 | -0.0379121 | 95.71 |
| 2021-11-19 | 0.0001 | 0.0001 | 65.67 | 0.00024901 | 53.33 | 1.4e+10 | 0.946783 | 4.83456 | 3.428e+09 | -0.0112939 | 95.27 |
| 2021-11-20 | 0.0001 | 0.0001 | 65.71 | 9.582e-05 | 46.89 | 1.019e+10 | 0.710122 | 5.13852 | 3.431e+09 | 0.000984212 | 95.51 |
| 2022-06-18 | 5.227e-05 | 5.71933e-05 | 20.65 | -0.00081201 | 3.108 | 2.404e+10 | 1.78458 | 6.45046 | 1.716e+09 | -0.10868 | 33.89 |
| 2022-11-08 | 9.446e-05 | 5.05767e-05 | 31.6 | -0.00030239 | 39.94 | 3.932e+10 | 3.96192 | 2.66405 | 2.221e+09 | -0.17087 | 48.75 |
| 2022-11-09 | -0.00032976 | -0.00013185 | 0.7785 | -0.00067651 | 6.986 | 3.544e+10 | 3.48997 | 2.78223 | 2.078e+09 | -0.0646991 | 44.18 |
| 2022-11-10 | -0.00023833 | -0.00084986 | 1.642 | -0.0002494 | 44.46 | 2.551e+10 | 2.5122 | 2.47115 | 2.151e+09 | 0.0354609 | 47.12 |
| 2024-08-05 | 5.967e-05 | 6.79867e-05 | 29.59 | -0.00029455 | 47.5 | 6.799e+10 | 4.17646 | 7.92339 | 4.06e+09 | -0.207308 | 87.73 |

These dates were not used to change formulas, windows, or inclusion rules.

## Source splice

Funding is the only spliced series: REST (2019-09-10–2019-12-31 and 2026-08-01–2026-08-29) + Vision monthly (2020-01–2026-07). Overlap on 2020-01-01: identical `fundingTime` and `fundingRate`. No other series is spliced across vendors.

## Disposition

**PASS WITH LIMITATIONS**

Funding, premium-index basis, and perp quote volume reconstruct without look-ahead and overlap for years. OI starts 2020-09-01 (later than funding), Vision funding files start 2020-01 (REST fills 2019-Q4 and 2026-08), and OI snapshot cadence changes over time. Percentiles burn 365 days. Not a FAIL: timestamps are usable.

Predictive value is **not** tested here. High funding is not a bearish rule; negative funding is not a bullish rule.
