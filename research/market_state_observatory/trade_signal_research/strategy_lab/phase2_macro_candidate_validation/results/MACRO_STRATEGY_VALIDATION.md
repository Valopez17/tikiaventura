# Macro strategy validation

Frozen Phase 1 candidate `C_macro_long_cash`. **Try to break it.** Historical validation / robustness. **Not clean OOS.** 2024–2026 has already been inspected.

Primary cost shown below: **10 bps round trip**. Start `$10,000`. Long only. Cash = 0.

## ORIGINAL RESULT

V0 Phase 1 reconstruction (Friday UTC close): $10,000 → $1,474,846; Sharpe 1.15; CAGR 68.86%; maxDD -83.77%; vs BH $737,554 (CAGR 57.02%, Sharpe 1.00, maxDD -83.19%)

## REALISTIC RESULT

V1 timing-safe Saturday 00:00 UTC: $10,000 → $1,474,846; Sharpe 1.15; CAGR 68.86%; maxDD -83.77%; vs BH $737,554 (CAGR 57.02%, Sharpe 1.00, maxDD -83.19%)
V2 24h delay: $10,000 → $1,280,901; Sharpe 1.12; CAGR 66.41%; maxDD -83.88%; vs BH $736,898 (CAGR 57.03%, Sharpe 1.00, maxDD -83.19%)
V3 72h delay: $10,000 → $1,924,217; Sharpe 1.19; CAGR 73.72%; maxDD -83.08%; vs BH $718,135 (CAGR 56.64%, Sharpe 1.00, maxDD -83.19%)
V4 one-week information lag: $10,000 → $2,162,212; Sharpe 1.21; CAGR 75.98%; maxDD -79.12%; vs BH $659,633 (CAGR 55.33%, Sharpe 0.99, maxDD -83.19%)

V3/V4 can print *higher* ending wealth than V1. That is not a reason to prefer delay or lagged features. V2–V4 have different start dates (Buy & Hold is restated on each row). V4 also uses a different information set. Full-sample ranking stays with the frozen V1 rule.

## Answers

### 1. Was there any timestamp look-ahead in the original backtest?

Phase 1 executed at **Friday UTC daily close** (23:59 UTC). Nasdaq Friday cash close is 16:00 America/New_York (20:00 or 21:00 UTC), so **NASDAQ_RET_12W is available before that fill**. H.15 2Y and Treasury TIPS 10Y real are same-business-day afternoon prints; conservative 16:00 ET is also before Friday 23:59 UTC.

**DXY_CHG_12W is the residual look-ahead.** It is the Fed H.10 Nominal Broad Dollar Index, typically published the same **or next** business day. Same-day availability was never verified. Using Friday's H.10 print at Friday 23:59 UTC can be look-ahead. Revised (not vintage) history remains for all four series.

V1 `safe_at_execution` share across decision×feature rows: 75.00%. Nasdaq V1 safe=True. DXY V1 safe=False.

### 2. What is the earliest genuinely executable weekly timestamp?

**Saturday 00:00 UTC** after the Friday US cash close, for Nasdaq / US2Y / REAL10Y. That is V1.

For an **unquestionable** information set including H.10, wait until the next US business day's H.10 print (often Monday), or drop current-Friday macro entirely (V4). This file treats V1 as the primary realistic implementation and V4 as the conservative information-set stress.

### 3. Does the strategy still beat Buy & Hold using that timestamp?

V1 10 bps: $10,000 → $1,474,846 vs BH $737,554. CAGR gap 11.84%; Sharpe gap 0.14. Yes, higher ending wealth.

### 4. Does it survive a 24h delay?

V2: $1,280,901 vs BH $736,898; CAGR gap 9.38%; Sharpe gap 0.12.
Survives 24h

### 5. Does it survive a 72h delay?

V3: $1,924,217 vs BH $718,135; CAGR gap 17.08%; Sharpe gap 0.19.
Survives 72h

### 6. What happens with a full one-week information lag?

V4 uses only macro dated on or before the previous Friday, same model class, execute at Saturday 00:00 UTC. $10,000 → $2,162,212 vs BH $659,633; CAGR gap 20.65%; Sharpe gap 0.22.
The edge is **not** solely current-Friday prints.

### 7. Does it survive 10/20/50 bps costs?

- V1 0 bps: end $1,498,639 vs BH $737,554; CAGR gap 12.12%; Sharpe gap 0.14; fees $0.
- V1 10 bps: end $1,474,846 vs BH $737,554; CAGR gap 11.84%; Sharpe gap 0.14; fees $13,717.
- V1 20 bps: end $1,451,418 vs BH $737,554; CAGR gap 11.56%; Sharpe gap 0.14; fees $27,161.
- V1 50 bps: end $1,383,279 vs BH $737,554; CAGR gap 10.71%; Sharpe gap 0.13; fees $65,892.

### 8. How many calendar years beat Buy & Hold?

V1 10 bps: **3 / 10** years beat BH. Strategy lost money in **3** years. Exposure < 90% (meaningful cash) in **4** years.

| year | strategy | BH | excess | max DD | exposure | beats BH | lost money |
|---|---:|---:|---:|---:|---:|---|---|
| 2017 | 1199.56% | 1199.56% | 0.00% | -35.09% | 100.00% | no | no |
| 2018 | -73.28% | -72.33% | -0.95% | -81.83% | 94.25% | no | yes |
| 2019 | 89.49% | 89.49% | 0.00% | -49.41% | 100.00% | no | no |
| 2020 | 301.67% | 301.67% | -0.00% | -53.60% | 100.00% | no | no |
| 2021 | 79.40% | 57.57% | 21.83% | -53.14% | 96.16% | yes | no |
| 2022 | -15.22% | -65.34% | 50.12% | -17.20% | 7.95% | yes | yes |
| 2023 | 101.04% | 154.46% | -53.42% | -18.89% | 69.32% | no | no |
| 2024 | 80.35% | 111.81% | -31.46% | -26.52% | 71.86% | no | no |
| 2025 | -16.46% | -7.34% | -9.12% | -32.02% | 93.70% | no | yes |
| 2026 | 8.67% | -12.37% | 21.04% | -35.11% | 64.58% | yes | no |

### 9. Does the result depend heavily on 2017 or another single year?

Largest calendar-year strategy return: **2017**.
Excluding 2017 (restart $10k on remaining days, same dates for BH): end $101,819 vs BH $50,347; CAGR gap 10.21%; Sharpe gap 0.14.
Excluding 2017: end $101,819 vs BH $50,347; CAGR gap 10.21%; Sharpe gap 0.14.

### 10. Does LONG genuinely contain better BTC weeks than CASH?

| state | N weeks | mean weekly BTC | median | cumulative BTC | vol | frac positive |
|---|---:|---:|---:|---:|---:|---:|
| LONG | 398 | 1.75% | 0.91% | 14886.39% | 0.100 | 56.78% |
| CASH | 99 | -0.43% | -0.36% | -50.79% | 0.073 | 42.42% |
Yes: mean/cumulative BTC while LONG exceeded CASH. The classifier separates environments on this tape.

This uses the frozen weekly signal vs Friday-to-Friday BTC, not delayed fills.

### 11. What happens to Sharpe relative to Buy & Hold?

V1 10 bps Sharpe 1.15 vs BH 1.00 (gap 0.14).
V2 Sharpe gap 0.12; V3 0.19; V4 0.22.

### 12. What happens to maximum drawdown?

V1 max DD -83.77% vs BH -83.19% (difference -0.58%; more negative = worse).

Subperiods (restart $10k in each block, V1 10 bps):

| block | CAGR | Sharpe | max DD | end $ | BH $ | beats BH |
|---|---:|---:|---:|---:|---:|---|
| 2017-2019 | 92.89% | 1.20 | -83.77% | $65,828 | $68,172 | no |
| 2020-2022 | 85.64% | 1.30 | -53.60% | $63,972 | $22,973 | yes |
| 2023-2026 | 40.69% | 1.04 | -49.53% | $34,856 | $46,848 | no |

Only **2020–2022** beats Buy & Hold on ending wealth. 2017–2019 is a partial start (first signal 2017-02-17) and finishes slightly behind BH. **2023–2026 loses to BH**. A large part of the full-sample gap is 2022, when exposure was ~8% during the bear.

### 13. Final classification

**PASS WITH LIMITATIONS**

Rules (frozen before inspecting outputs): PASS requires no V1 look-ahead on **all** features, V1 10 bps superior to BH on CAGR and/or Sharpe, 24h delay still superior, not a single-year artefact, and at least two subperiods with evidence. PASS WITH LIMITATIONS if still economically interesting but timing, delay, lag, costs, or years weaken it. FAIL if the edge needs illegal timing, unrealistically immediate execution, one exceptional year, costs, or has no robust subperiod support.

### 14. Executable strategy

Each Friday after US cash close, compute frozen 12w changes of Fed H.10 broad dollar, H.15 2Y, Treasury 10Y real, Nasdaq Composite.
Fit expanding L2 logistic (C=1.0, train-only median+scaler, min N=100) on mature BTC 12w sign labels only (`s ≤ t−12`).
If P(BTC 12w > 0) ≥ 0.50, be long BTC from Saturday 00:00 UTC; else hold cash (0).
No short, no leverage, no intraweek switching. Budget at least 10 bps round trip per completed entry/exit.
Do not treat H.10 Friday prints as known before the next business day unless a vintage tape says so.

## Switch events (V1, 10 bps)

| decision | event | P | execution | BTC px | next 1w | next 4w | next 12w |
|---|---|---:|---|---:|---:|---:|---:|
| 2017-02-17 | CASH→LONG | 0.802 | 2017-02-17T23:59:00 | 1055.46 | 11.81% | 1.47% | 60.26% |
| 2018-06-15 | LONG→CASH | 0.347 | 2018-06-15T23:59:00 | 6388.90 | -5.38% | -2.73% | 0.10% |
| 2018-07-06 | CASH→LONG | 0.503 | 2018-07-06T23:59:00 | 6609.78 | -5.98% | 12.24% | 0.38% |
| 2021-11-26 | LONG→CASH | 0.490 | 2021-11-26T23:59:00 | 53726.53 | -0.23% | -5.41% | -25.60% |
| 2021-12-10 | CASH→LONG | 0.500 | 2021-12-10T23:59:00 | 47140.54 | -2.14% | -11.82% | -16.95% |
| 2022-01-07 | LONG→CASH | 0.452 | 2022-01-07T23:59:00 | 41566.48 | 3.59% | 0.02% | 11.35% |
| 2022-07-29 | CASH→LONG | 0.542 | 2022-07-29T23:59:00 | 23773.75 | -1.94% | -14.86% | -19.39% |
| 2022-08-05 | LONG→CASH | 0.342 | 2022-08-05T23:59:00 | 23312.42 | 4.68% | -14.42% | -11.67% |
| 2022-12-16 | CASH→LONG | 0.784 | 2022-12-16T23:59:00 | 16632.12 | 0.88% | 19.83% | 21.16% |
| 2023-06-09 | LONG→CASH | 0.463 | 2023-06-09T23:59:00 | 26477.81 | -0.50% | 14.60% | -2.54% |
| 2023-07-14 | CASH→LONG | 0.553 | 2023-07-14T23:59:00 | 30312.01 | -1.35% | -2.92% | -7.85% |
| 2023-07-21 | LONG→CASH | 0.429 | 2023-07-21T23:59:00 | 29901.72 | -1.97% | -12.87% | -10.17% |
| 2023-08-18 | CASH→LONG | 0.555 | 2023-08-18T23:59:00 | 26054.00 | 0.02% | 2.10% | 43.17% |
| 2023-08-25 | LONG→CASH | 0.468 | 2023-08-25T23:59:00 | 26060.01 | -0.98% | 2.00% | 40.50% |
| 2023-09-01 | CASH→LONG | 0.514 | 2023-09-01T23:59:00 | 25805.05 | 0.41% | 4.27% | 46.15% |
| 2023-09-08 | LONG→CASH | 0.436 | 2023-09-08T23:59:00 | 25910.50 | 2.66% | 7.80% | 49.29% |
| 2023-09-22 | CASH→LONG | 0.518 | 2023-09-22T23:59:00 | 26580.14 | 1.23% | 11.62% | 57.79% |
| 2023-10-06 | LONG→CASH | 0.305 | 2023-10-06T23:59:00 | 27931.09 | -3.83% | 24.29% | 50.61% |
| 2023-11-03 | CASH→LONG | 0.617 | 2023-11-03T23:59:00 | 34716.78 | 7.45% | 11.42% | 20.47% |
| 2024-03-15 | LONG→CASH | 0.498 | 2024-03-15T23:59:00 | 69499.85 | -8.21% | -3.43% | -0.21% |
| 2024-03-29 | CASH→LONG | 0.540 | 2024-03-29T23:59:00 | 69850.54 | -2.91% | -8.71% | -8.17% |
| 2024-04-05 | LONG→CASH | 0.417 | 2024-04-05T23:59:00 | 67820.62 | -1.04% | -7.28% | -10.90% |
| 2024-05-03 | CASH→LONG | 0.545 | 2024-05-03T23:59:00 | 62882.01 | -3.31% | 7.41% | 7.99% |
| 2024-05-31 | LONG→CASH | 0.483 | 2024-05-31T23:59:00 | 67540.01 | 2.69% | -10.53% | -5.19% |
| 2024-06-07 | CASH→LONG | 0.526 | 2024-06-07T23:59:00 | 69355.60 | -4.77% | -18.35% | -14.75% |
| 2024-11-08 | LONG→CASH | 0.486 | 2024-11-08T23:59:00 | 76509.78 | 18.98% | 30.36% | 33.88% |
| 2025-01-24 | CASH→LONG | 0.586 | 2025-01-24T23:59:00 | 104870.50 | -2.33% | -8.28% | -19.45% |
| 2026-05-01 | LONG→CASH | 0.468 | 2026-05-01T23:59:00 | 78231.13 | 2.51% | -6.10% | -18.01% |
| 2026-06-12 | CASH→LONG | 0.519 | 2026-06-12T23:59:00 | 63580.01 | -0.06% | 0.91% | NA |
| 2026-06-19 | LONG→CASH | 0.422 | 2026-06-19T23:59:00 | 63543.91 | -5.42% | 0.61% | NA |
| 2026-07-31 | CASH→LONG | 0.511 | 2026-07-31T23:59:00 | 62887.88 | 3.24% | 23.79% | NA |

Descriptive only. Threshold stays 0.50.

## Method

- V0 copies Phase 1: Friday UTC close fill, walk-forward contemporaneous Friday features.
- V1 fill is Saturday 00:00 UTC = that same Friday UTC close on daily bars.
- V2/V3 delay the **same** V0/V1 signal; no recalculation. Fill at Saturday close / Monday close (Sunday 00:00 / Tuesday 00:00 UTC).
- V4 refits the same model class on features dated ≤ previous Friday.
- Buy & Hold uses the exact same start/end as each row.
- Excluding a calendar year restarts $10k on the remaining dates only.
- 2017–2019 is partial: first probability week is when min train N=100 is met.
- Years with ~0% excess vs BH are 100% invested years, not timing skill. `beats_bh` requires >50 bps excess.

