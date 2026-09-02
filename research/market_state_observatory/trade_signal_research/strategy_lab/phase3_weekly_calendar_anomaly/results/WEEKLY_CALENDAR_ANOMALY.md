# Weekly BTC calendar anomaly — Phase 3

Discovery candidate search over 28,056 weekly day/hour windows.
Not clean out-of-sample. Not a live trading system.
Do not read this as “we discovered the optimal BTC schedule.”
The real evidence is whether a **frozen** discovery candidate survives later periods.

## BEST DISCOVERY WINDOW

**BUY:** Friday 17:00 America/New_York

**SELL:** Friday 21:00 America/New_York

**Holding:** 4 hours

Exposure: 2.38% of each week. Ranked #1 by discovery **calendar-edge Sharpe** at 10 bps,
among windows with mean net trade > 0 and N ≥ 150.

## DISCOVERY (data start → 2021-12-31)
$10,000 → $23,470
Sharpe: 1.7785
mean trade (gross): 0.49%
mean net trade (10 bps): 0.39%
calendar edge (mean): 0.44%
calendar-edge Sharpe: 1.9776
win rate: 62.72%
max drawdown: -10.30%
CAGR: 21.51%
N trades: 228
exposure: 2.38% (4 / 168 hours)
BTC buy & hold same calendar range (10 bps, one round trip): $10,000 → $109,742 (net 997.42%). Buy & hold is a different exposure; it is not the anomaly benchmark.

## VALIDATION (2022-01-01 → 2024-12-31)
$10,000 → $10,117
Sharpe: 0.0914
mean trade (gross): 0.11%
mean net trade (10 bps): 0.01%
calendar edge (mean): 0.10%
calendar-edge Sharpe: 0.8338
win rate: 55.13%
max drawdown: -10.61%
CAGR: 0.39%
N trades: 156
exposure: 2.38% (4 / 168 hours)
BTC buy & hold same calendar range (10 bps, one round trip): $10,000 → $20,069 (net 100.69%). Buy & hold is a different exposure; it is not the anomaly benchmark.

## RECENT (2025-01-01 → latest complete bar)
$10,000 → $9,113
Sharpe: -1.7665
mean trade (gross): -0.01%
mean net trade (10 bps): -0.11%
calendar edge (mean): -0.00%
calendar-edge Sharpe: -0.0731
win rate: 48.84%
max drawdown: -10.30%
CAGR: -5.47%
N trades: 86
exposure: 2.38% (4 / 168 hours)
BTC buy & hold same calendar range (10 bps, one round trip): $10,000 → $8,363 (net -16.37%). Buy & hold is a different exposure; it is not the anomaly benchmark.

## FULL HISTORY (DESCRIPTIVE ONLY)

Not used for ranking or selection.

$10,000 → $21,637 after 10 bps.
Sharpe 0.9994; mean trade 0.27%; calendar edge 0.25%.

## Answers

1. What entry weekday/hour ranked #1 in discovery? **Friday 17:00 America/New_York.**
2. What exit weekday/hour ranked #1? **Friday 21:00 America/New_York.**
3. How long was the position held? **4 hours** (2.38% of the week).
4. What happened to $10,000 after 10 bps? Discovery $10,000 → $23,470. Validation $10,117. Recent $9,113.
5. Did the advantage survive 2022–2024? **Yes on the predeclared rule** (classification: SURVIVES). Validation mean net 0.01%, calendar edge 0.10%, Sharpe 0.0914. The rank-1 validation 95% CI for mean net includes zero, so the survival is statistical-sign, not economic size.
6. Did it survive 2025–latest? Recent mean net -0.11%, calendar edge -0.00%.
7. Was its calendar edge positive relative to same-duration windows? Discovery mean edge 0.44% (edge Sharpe 1.9776); fraction of weeks with positive edge 59.21%. Validation mean edge 0.10%.
8. Are neighboring entry/exit hours also strong? **NEIGHBORHOOD STABLE**
- Friday 16:00 → Friday 21:00: edge=0.0038 edge_Sharpe=1.5971 mean_net=0.0033 similar=True
- Friday 18:00 → Friday 21:00: edge=0.0024 edge_Sharpe=1.1791 mean_net=0.0018 similar=True
- Friday 17:00 → Friday 20:00: edge=0.0037 edge_Sharpe=1.9549 mean_net=0.0031 similar=True
- Friday 17:00 → Friday 22:00: edge=0.0053 edge_Sharpe=1.7927 mean_net=0.0048 similar=True
9. Does the result depend on one bull-market year? Not obviously concentrated. years_with_positive_edge=7/10; max_positive_year_share=0.44

| Year | N | Year return (10 bps) | Mean trade (gross) | Win rate | Sharpe | Mean calendar edge |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 20 | 2.44% | 0.24% | 55.00% | 0.5004 | 0.04% |
| 2018 | 52 | 50.12% | 0.90% | 71.15% | 3.4624 | 0.89% |
| 2019 | 52 | 23.17% | 0.51% | 67.31% | 2.0869 | 0.47% |
| 2020 | 52 | -2.93% | 0.05% | 50.00% | -0.2818 | -0.02% |
| 2021 | 52 | 27.65% | 0.58% | 65.38% | 2.1297 | 0.56% |
| 2022 | 52 | -2.89% | 0.05% | 53.85% | -0.4558 | 0.07% |
| 2023 | 52 | 10.27% | 0.29% | 61.54% | 1.3520 | 0.28% |
| 2024 | 52 | -5.53% | -0.01% | 50.00% | -0.9513 | -0.04% |
| 2025 | 52 | -6.78% | -0.03% | 46.15% | -2.1678 | -0.04% |
| 2026 | 34 | -2.24% | 0.03% | 52.94% | -1.1121 | 0.05% |

10. How sensitive is it to 20 and 50 bps? Discovery ending capital 0 bps $29,484, 10 bps $23,470, 20 bps $18,679, 50 bps $9,402. Discovery mean net 20 bps 0.29%, 50 bps -0.01%.
11. How many of the original TOP 20 survive validation? **4 SURVIVES** (of which **1 STRONG SURVIVOR**), 3 FRAGILE, 13 FAIL.
12. Is there an identifiable CLUSTER?
Top-20 entry→exit weekday pairs (count):
- 13 rules: BUY Friday → SELL Friday (entry hours 03–17)
- 4 rules: BUY Friday → SELL Saturday (entry hours 03–03)
- 2 rules: BUY Wednesday → SELL Wednesday (entry hours 01–01)
- 1 rule: BUY Friday → SELL Monday (entry hours 03–03)
Median discovery calendar-edge Sharpe among filter-passing windows, by entry weekday:
- Friday: 0.507
- Thursday: 0.338
- Sunday: 0.323
- Tuesday: 0.246
- Wednesday: 0.183
- Monday: 0.177
- Saturday: 0.136
Same, by exit weekday:
- Saturday: 0.397
- Wednesday: 0.347
- Monday: 0.269
- Friday: 0.249
- Tuesday: 0.199
- Sunday: 0.190
- Thursday: 0.153
Repeated weekday pairs in the top 20 are evidence of a cluster rather than a single isolated hour.
13. What is the strongest surviving executable rule? **Friday 03:00 → Monday 20:00 (89h hold, exposure 52.98%). Classification: STRONG SURVIVOR. Discovery $10,000 → $220,668; validation $10,000 → $17,357; recent $10,000 → $10,854. This is a frozen discovery candidate that passed the decision rule; it is not an optimized live schedule. (STRONG SURVIVOR (lowest discovery rank among strong).)**
14. Final classification: **STRONG CALENDAR EFFECT**

The label follows the predeclared rule (at least one STRONG SURVIVOR → STRONG CALENDAR EFFECT). It is not a claim that a unique tradable schedule was found. 13 of 20 frozen candidates FAIL validation. About 28,000 tests were run in discovery.

## Strongest surviving executable rule (frozen, not reselected)

**BUY:** Friday 03:00 America/New_York
**SELL:** Monday 20:00 America/New_York
**Holding:** 89 hours (52.98% of the week). Discovery rank 12.

- Discovery: $10,000 → $220,668; Sharpe 1.6476; mean net 1.62%; calendar edge 1.09%.
- Validation: $10,000 → $17,357; Sharpe 0.6450; mean net 0.53%; calendar edge 0.50%.
- Recent: $10,000 → $10,854; Sharpe 0.3200; mean net 0.16%; calendar edge 0.22%.
- Neighborhood: NEIGHBORHOOD STABLE. Year check: years_with_positive_edge=8/10; max_positive_year_share=0.29 (not concentrated).
- Discovery costs: 0 bps $276,655, 20 bps $175,971, 50 bps $89,116.

Calendar-year path for this frozen rule (descriptive; not used for ranking):

| Year | N | Year return (10 bps) | Mean trade (gross) | Win rate | Sharpe | Mean calendar edge |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 20 | 131.17% | 4.87% | 70.00% | 3.2843 | 1.89% |
| 2018 | 50 | -10.13% | 0.08% | 54.00% | -0.0180 | 1.24% |
| 2019 | 52 | 204.99% | 2.49% | 55.77% | 2.4847 | 1.73% |
| 2020 | 52 | 111.25% | 1.69% | 63.46% | 2.0977 | 0.65% |
| 2021 | 53 | 61.38% | 1.28% | 54.72% | 1.1288 | 0.42% |
| 2022 | 52 | -49.88% | -0.99% | 40.38% | -1.1779 | -0.05% |
| 2023 | 52 | 78.92% | 1.34% | 53.85% | 1.7797 | 0.69% |
| 2024 | 52 | 93.56% | 1.54% | 53.85% | 1.7982 | 0.85% |
| 2025 | 52 | -14.17% | -0.12% | 48.08% | -0.4278 | -0.13% |
| 2026 | 34 | 26.46% | 0.85% | 55.88% | 1.6269 | 0.72% |

Validation 95% CI mean net: [-0.27%, 1.44%]; mean calendar edge: [0.00%, 1.01%].

## Frozen top 20 — decision rule

| Rank | Window | Hold h | Class | Val $10k | Val Sharpe | Val mean net | Val edge | Recent mean net | Recent edge |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Friday 17:00 → Friday 21:00 | 4 | SURVIVES | $10,117 | 0.0914 | 0.011% | 0.103% | -0.107% | -0.005% |
| 2 | Friday 17:00 → Friday 20:00 | 3 | FAIL | $9,714 | -0.1311 | -0.015% | 0.074% | -0.139% | -0.039% |
| 3 | Friday 17:00 → Friday 23:00 | 6 | FAIL | $9,547 | -0.2217 | -0.026% | 0.055% | -0.104% | -0.008% |
| 4 | Friday 17:00 → Friday 22:00 | 5 | FAIL | $9,256 | -0.3758 | -0.046% | 0.040% | -0.131% | -0.032% |
| 5 | Friday 03:00 → Friday 21:00 | 18 | FRAGILE | $9,933 | 0.0831 | 0.031% | 0.123% | -0.071% | 0.042% |
| 6 | Friday 03:00 → Friday 23:00 | 20 | FAIL | $9,373 | -0.0182 | -0.007% | 0.067% | -0.068% | 0.040% |
| 7 | Friday 03:00 → Friday 20:00 | 17 | FRAGILE | $9,538 | 0.0118 | 0.004% | 0.095% | -0.104% | 0.006% |
| 8 | Friday 03:00 → Friday 22:00 | 19 | FAIL | $9,087 | -0.0700 | -0.026% | 0.065% | -0.095% | 0.024% |
| 9 | Friday 15:00 → Friday 21:00 | 6 | SURVIVES | $10,550 | 0.2401 | 0.042% | 0.124% | -0.124% | -0.029% |
| 10 | Wednesday 01:00 → Wednesday 03:00 | 2 | FAIL | $8,575 | -1.1548 | -0.097% | -0.005% | 0.001% | 0.097% |
| 11 | Wednesday 01:00 → Wednesday 02:00 | 1 | FAIL | $8,273 | -2.5924 | -0.121% | -0.026% | -0.050% | 0.051% |
| 12 | Friday 03:00 → Monday 20:00 | 89 | STRONG SURVIVOR | $17,357 | 0.6450 | 0.531% | 0.503% | 0.160% | 0.215% |
| 13 | Friday 16:00 → Friday 21:00 | 5 | FAIL | $9,581 | -0.1355 | -0.021% | 0.065% | -0.039% | 0.061% |
| 14 | Friday 15:00 → Friday 23:00 | 8 | SURVIVES | $9,956 | 0.0269 | 0.005% | 0.090% | -0.122% | -0.020% |
| 15 | Friday 03:00 → Saturday 00:00 | 21 | FRAGILE | $9,484 | 0.0019 | 0.001% | 0.072% | -0.054% | 0.060% |
| 16 | Friday 03:00 → Saturday 03:00 | 24 | FAIL | $8,843 | -0.1107 | -0.042% | 0.046% | -0.198% | -0.075% |
| 17 | Friday 15:00 → Friday 22:00 | 7 | FAIL | $9,652 | -0.0894 | -0.015% | 0.065% | -0.149% | -0.058% |
| 18 | Friday 17:00 → Friday 18:00 | 1 | FAIL | $8,690 | -1.2890 | -0.089% | 0.007% | -0.048% | 0.053% |
| 19 | Friday 03:00 → Saturday 04:00 | 25 | FAIL | $8,689 | -0.1411 | -0.053% | 0.024% | -0.239% | -0.101% |
| 20 | Friday 03:00 → Saturday 01:00 | 22 | FAIL | $9,286 | -0.0343 | -0.013% | 0.064% | -0.079% | 0.035% |

## Block bootstrap (4-week blocks, 2000 samples)

Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.

Rank-1 validation 95% CI mean net trade: [-0.13%, 0.17%]
Rank-1 validation 95% CI mean calendar edge: [-0.06%, 0.27%]

## Data audit

- File: `/Users/valeria/Documents/tikiaventura/btc_tsmom_replication/btcusdt_1h.csv`
- UTC start/end: 2017-08-17 04:00:00+00:00 → 2026-08-26 13:00:00+00:00
- NY start/end: 2017-08-17 00:00:00-04:00 → 2026-08-26 09:00:00-04:00
- Bars: 78986; unique UTC: True; chronological: True; OHLC valid: True
- Duplicated bars dropped: 0; invalid OHLC rows dropped: 0
- Missing hours in the UTC 1h grid (not filled): 128. Preview: 2017-09-06 17:00:00+00:00, 2017-09-06 18:00:00+00:00, 2017-09-06 19:00:00+00:00, 2017-09-06 20:00:00+00:00, 2017-09-06 21:00:00+00:00, 2017-09-06 22:00:00+00:00, 2018-01-04 04:00:00+00:00, 2018-02-08 01:00:00+00:00, ... (128 total)
- Monday-start NY weeks: 472 (2017-08-14 → 2026-08-24)
- DST nonexistent/ambiguous labeled slots skipped: 18
- Candidate-week observations skipped because entry or exit landed on a DST-invalid slot (discovery scan count): 3006
- Candidate-week observations skipped because a Binance bar was missing (discovery scan count): 41630

### DST rule

Schedules are America/New_York civil hours, not a fixed UTC offset. Each labeled slot is `tz_localize(..., ambiguous='NaT', nonexistent='NaT')`. Spring-forward missing hours and fall-back duplicated hours are skipped for that week. No fold is guessed.

## Research design

- Search space: 7×24 entry slots × 167 distinct future weekly exit slots = 28,056 windows.
- Execution: buy the **open** of the 1h candle whose open equals the NY civil hour; sell the matching exit open.
- Return = exit_open / entry_open − 1. No intra-candle information. Long only. No leverage. Cash outside the window.
- One trade per week. Holding hours ∈ [1, 167], so the next weekly entry cannot overlap the open position.
- Primary cost 10 bps round trip once per completed trade: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps. No extra slippage.
- Same-duration control: for each week and holding H, median return across valid entry slots with that H. Calendar edge = candidate week return − that median. Median requires ≥ 24 valid slots that week.
- Discovery / validation / recent splits are chronological and frozen. Full-history numbers are descriptive only.
- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.

## Multiple-testing warning

About 28,000 rules were ranked on discovery. The best in-sample calendar-edge Sharpe **will** be biased upward. A discovery winner is a **discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters.

## Audit assertions

- No future data in ranking: discovery metrics use only bars with NY time < 2022-01-01, and both entry and exit must fall in that window.
- Entry uses the entry-bar open only; the exit open is not used to decide whether to enter.
- Validation did not affect ranking. Top 20 were frozen from discovery, then scored unchanged.
- Full history was not used for candidate selection.
- New York conversion uses `America/New_York` (EST/EDT). DST invalid hours are skipped, not filled.
- Transaction costs applied once per completed trade.
- Equity compounds net trade returns from $10,000 with cash = 0 between trades.
- Positions do not overlap: holding_hours ≤ 167.
- Same-duration calendar benchmark is the weekly median across the 168 start slots with that H.
- Losing trades are retained; NaNs are skipped only for missing/DST-invalid timestamps.

Bootstrap seed=42, block=4 weeks, samples=2000.

Script runtime and environment are in the process log. Generated by `src/run_weekly_calendar_scan.py`.

