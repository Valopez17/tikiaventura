# BTC Breakout Continuation — Phase 5

QUESTION:

Does buying BTC after it closes above a genuine historical
price high generate abnormal future returns?

Discovery candidate search over 20 frozen LONG breakout rules.
Not clean out-of-sample. Not a live trading system.
CALENDAR_CANDIDATE_V1 and CRASH_REBOUND_CANDIDATE_V1 were not modified and are not combined here.

## BEST DISCOVERY CANDIDATE

LOOKBACK: 7 days (168 hours)

SIGNAL: BTC close > previous 7-day maximum high

ENTRY: next hourly OPEN

EXIT: 168 hours later (next-open to exit-open)

Ranked #1 by Discovery hourly MTM Sharpe at 10 bps, among rules with mean net > 0, breakout edge > 0, and N ≥ 20.

## DISCOVERY (data start → 2021-12-31)
N trades (non-overlapping): 89
N breakout events (overlapping): 584
mean net (10 bps): 3.558%
mean gross: 3.662%
median net: 2.221%
win rate: 59.55%
average winner / loser: 9.768% / -5.583%
payoff ratio: 1.7494
profit factor: 2.5756
breakout edge (cond − uncond mean): 2.002%
conditional / unconditional mean: 3.825% / 1.822%
median difference: 1.988%
P(return>0) difference: 7.090%
MTM Sharpe: 1.4810
MTM MaxDD: -35.18%
MTM vol: 50.05%
MTM CAGR: 84.72%
Calmar: 2.4086
exposure: 39.01%
trade_sharpe_diagnostic: 1.5612
$10,000 → $146,806 (compounded trades) / MTM end $146,806
0/10/20/50 bps mean net: 3.662% / 3.558% / 3.455% / 3.144%

## VALIDATION (2022-01-01 → 2024-12-31)
N trades: 69
mean net (10 bps): 0.764%
breakout edge: 0.730%
MTM Sharpe: 0.4449
MTM MaxDD: -48.26%
$10,000 → $13,259 / MTM end $13,259
Classification: **SURVIVES**

## RECENT (2025-01-01 → latest complete bar)
N trades: 34
mean net (10 bps): 0.979%
breakout edge: -0.429%
MTM Sharpe: 0.8146
MTM MaxDD: -32.11%
$10,000 → $13,302 / MTM end $13,302

## Answers

1. Do BTC breakouts generally continue? **Discovery pooled breakout edge 5.267% (19/20 rules positive). Validation pooled edge 2.439% (20/20 positive). On the event-study mean, breakout hours outperform ordinary same-horizon hours in both Discovery and Validation. That is continuation on average, not a STRONG executable rule: drawdowns are large, validation Sharpe is modest, and recent breakout edges are negative.**
2. Which lookback produced the strongest Discovery evidence: 7d / 30d / 60d / 90d? **7d (L168h); mean Discovery MTM Sharpe 1.0381, mean breakout edge 3.070%.**
3. Which holding horizon appeared strongest? **168h; mean Discovery MTM Sharpe 1.1617, mean breakout edge 2.932%.**
4. Did breakout returns outperform ordinary BTC returns over identical horizons? **Rank-1 Discovery conditional 3.825% vs unconditional 1.822% (edge 2.002%). Validation edge 0.730%. Recent edge -0.429%. Across all 20 Discovery rules, 19 have positive edge.**
5. Did the best Discovery candidate survive 2022–2024? **Yes (classification: SURVIVES). Validation mean net 0.764%, breakout edge 0.730%, MTM Sharpe 0.4449, N=69. Discovery rank #4 (`L168_H336`) had the strongest later persistence (validation MTM Sharpe 1.0642, $10k → $27,900). That comparison used later data; it is not untouched OOS validation.**
6. Did it survive 2025→latest? **Executable PnL survived (mean net 0.979%), but the breakout edge did not survive (edge -0.429%). MTM Sharpe 0.8146, N=34. None of the Top 5 have a non-negative recent breakout edge, so none meet STRONG SURVIVOR.**
7. What happened to $10,000 in each period? **Discovery $146,806; validation $13,259; recent $13,302 (each period starts from $10,000; not chained).**
8. What is true hourly MTM Sharpe? **Discovery 1.4810; validation 0.4449; recent 0.8146 (hourly equity, sqrt(365×24), zeros when flat).**
9. What is true MTM maximum drawdown? **Discovery -35.18%; validation -48.26%; recent -32.11% (hourly MTM, intra-trade path included).**
10. Does candidate remain profitable at 20 bps? **Discovery mean net at 20 bps 3.455% (positive). Validation 0.663% (positive).**
11. At 50 bps? **Discovery mean net at 50 bps 3.144% (positive). Validation 0.361% (positive).**
12. How many Top candidates survive? **5 of 5 frozen (0 STRONG SURVIVOR, 5 SURVIVES, 0 FRAGILE, 0 FAIL).**
13. Are successful rules clustered around similar lookbacks / holding periods or is the winner isolated? **Clustered: L168 (n=3); L720 (n=2) | holds: H336 (n=2); H720 (n=2); H168 (n=1).**
14. Is performance dependent on one particular year? **years_with_positive_mean_net=9/10; max_positive_year_share=0.28; positive_outside_2020_2021=7**
15. What do event paths say: immediate continuation, delayed continuation, or frequent false breakouts? **delayed continuation on the mean (flat/down at +1h, higher by +24h), with frequent false breakouts (44.60% of events not positive at +24h). Mean path from entry: +1h -0.018%, +6h 0.181%, +24h 0.919%, +168h 3.060%. Mean MAE_720h -10.812%; mean MFE_720h 25.499%. Share of events with non-positive +24h return 44.60%.**
16. Final classification: **WEAK BREAKOUT CONTINUATION**
17. If a candidate survives, write the executable rule in maximum five lines.

If BTC's hourly close is above the maximum high of the previous 7 calendar days (timestamp window [t−168h, t), complete hourly coverage), buy the next hourly open and exit at the open 336h later. Ignore new breakout signals until flat. Primary cost: 10 bps round trip. This is Discovery rank #4 (L168_H336), identified as the strongest surviving Discovery candidate using later data. It is not untouched OOS validation.

## Frozen top candidates — decision rule

| Rank | Rule | Class | Val $10k | Val MTM Sharpe | Val mean net | Val edge | Rec mean net | Rec edge |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | `L168_H168` | SURVIVES | $13,259 | 0.4449 | 0.764% | 0.730% | 0.979% | -0.429% |
| 2 | `L168_H720` | SURVIVES | $14,583 | 0.4680 | 3.040% | 2.718% | -2.968% | -0.587% |
| 3 | `L720_H336` | SURVIVES | $12,158 | 0.3663 | 1.309% | 2.507% | -1.930% | -1.584% |
| 4 | `L168_H336` | SURVIVES | $27,900 | 1.0642 | 2.755% | 1.049% | 0.851% | -0.801% |
| 5 | `L720_H720` | SURVIVES | $20,664 | 0.7794 | 4.940% | 5.005% | -2.035% | -0.947% |

## All 20 Discovery rules

| Rule | Eligible | N trades | Mean net | Edge | MTM Sharpe | MTM MaxDD | $10k |
|---|---|---:|---:|---:|---:|---:|---:|
| `L168_H168` | yes | 89 | 3.558% | 2.002% | 1.4810 | -35.18% | $146,806 |
| `L168_H720` | yes | 40 | 9.264% | 6.702% | 1.2085 | -77.39% | $106,174 |
| `L720_H336` | yes | 27 | 8.046% | 9.637% | 1.0681 | -53.62% | $51,373 |
| `L168_H336` | yes | 66 | 4.314% | 4.913% | 0.9615 | -68.68% | $55,487 |
| `L720_H720` | yes | 20 | 13.219% | 14.149% | 0.9472 | -51.78% | $48,368 |
| `L168_H72` | yes | 135 | 1.193% | 0.890% | 0.8942 | -37.75% | $35,224 |
| `L720_H168` | yes | 37 | 3.299% | 3.861% | 0.8424 | -48.73% | $27,366 |
| `L720_H72` | yes | 54 | 1.760% | 1.774% | 0.7863 | -46.08% | $22,867 |
| `L1440_H24` | yes | 35 | 1.283% | 1.619% | 0.6476 | -24.27% | $14,985 |
| `L168_H24` | yes | 199 | 0.443% | 0.844% | 0.6452 | -33.26% | $19,477 |
| `L720_H24` | yes | 78 | 0.745% | 1.339% | 0.5955 | -38.55% | $16,106 |
| `L1440_H72` | yes | 24 | 1.972% | 1.229% | 0.5392 | -34.34% | $15,151 |
| `L2160_H24` | no | 15 | 3.221% | 2.734% | 1.0365 | -16.67% | $15,733 |
| `L1440_H720` | no | 8 | 25.647% | 20.407% | 0.9670 | -39.75% | $38,104 |
| `L2160_H336` | no | 4 | 17.567% | 3.472% | 0.7978 | -26.39% | $18,680 |
| `L1440_H168` | no | 16 | 5.126% | 5.481% | 0.7946 | -31.23% | $20,697 |
| `L2160_H720` | no | 3 | 32.982% | 8.180% | 0.7824 | -39.75% | $23,351 |
| `L1440_H336` | no | 11 | 10.301% | 14.791% | 0.7099 | -48.07% | $22,441 |
| `L2160_H72` | no | 11 | 2.998% | -0.484% | 0.5017 | -20.04% | $13,162 |
| `L2160_H168` | no | 6 | 4.549% | 1.805% | 0.2957 | -35.43% | $11,915 |

## Calendar-year path for the rank-1 Discovery rule

years_with_positive_mean_net=9/10; max_positive_year_share=0.28; positive_outside_2020_2021=7

| Year | N | Strategy return | Mean net | Win rate | Breakout edge | MTM Sharpe | MTM MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 10 | 142.40% | 10.045% | 80.00% | -0.526% | 3.0586 | -29.88% |
| 2018 | 15 | -0.83% | 0.353% | 53.33% | -1.802% | 0.1674 | -28.62% |
| 2019 | 19 | 73.92% | 3.470% | 47.37% | 3.629% | 1.4930 | -35.18% |
| 2020 | 24 | 100.78% | 3.179% | 70.83% | -0.250% | 1.8048 | -22.39% |
| 2021 | 21 | 74.89% | 3.272% | 52.38% | 1.172% | 1.3535 | -30.28% |
| 2022 | 17 | -31.57% | -1.992% | 47.06% | -1.471% | -0.9713 | -45.78% |
| 2023 | 24 | 84.58% | 2.811% | 66.67% | 0.980% | 2.1483 | -16.58% |
| 2024 | 28 | 4.97% | 0.683% | 57.14% | 0.937% | 0.3195 | -48.26% |
| 2025 | 21 | 8.69% | 0.494% | 57.14% | -0.201% | 0.4591 | -22.62% |
| 2026 | 13 | 22.39% | 1.763% | 53.85% | -0.998% | 1.3518 | -16.84% |

## Block bootstrap (168-hour blocks, 2000 samples)

Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.
Blocks are drawn from the hourly coverage-ok series (circular) to keep breakout clustering.
Rank-1 Discovery 95% CI mean net trade: [0.618%, 4.852%]
Rank-1 Discovery 95% CI breakout edge: [-0.190%, 4.027%]
Rank-1 validation 95% CI mean net trade: [-0.778%, 3.044%]
Rank-1 validation 95% CI breakout edge: [-0.948%, 2.343%]

## Coverage (complete expected hourly bars; no fill)

- L168h (7d): valid coverage 74405/78986; lost to missing bars 4413; insufficient history 168; breakout events 1117
- L720h (30d): valid coverage 62611/78986; lost to missing bars 15661; insufficient history 714; breakout events 500
- L1440h (60d): valid coverage 51415/78986; lost to missing bars 26137; insufficient history 1434; breakout events 308
- L2160h (90d): valid coverage 43656/78986; lost to missing bars 33176; insufficient history 2154; breakout events 215

## Data audit

- File: `/Users/valeria/Documents/tikiaventura/btc_tsmom_replication/btcusdt_1h.csv`
- UTC start/end: 2017-08-17 04:00:00+00:00 → 2026-08-26 13:00:00+00:00
- Bars: 78986; unique UTC: True; chronological: True; OHLC valid: True
- Duplicated bars dropped: 0; invalid OHLC rows dropped: 0
- Missing hours in the UTC 1h grid (not filled): 128. Preview: 2017-09-06 17:00:00+00:00, 2017-09-06 18:00:00+00:00, 2017-09-06 19:00:00+00:00, 2017-09-06 20:00:00+00:00, 2017-09-06 21:00:00+00:00, 2017-09-06 22:00:00+00:00, 2018-01-04 04:00:00+00:00, 2018-02-08 01:00:00+00:00, ... (128 total)
- Breakout signals skipped for missing t+1 entry bar (summed over lookbacks): 0
- Events skipped for missing exit open (summed over lookback×hold): 128
- Prior-high audit: 24 random coverage-ok timestamps × each lookback recomputed from exact t−k hours.

## Research design

- Search space: 4 lookbacks × 5 holds = 20 LONG rules. No shorts.
- Breakout: close_t > max high on timestamp window [t−L hours, t). Current bar excluded.
- Complete coverage: exactly L hourly bars in that window. Otherwise signal invalid.
- Execution: buy the **open** of bar t+1; exit the open H hours later. Never the signal close.
- LONG return = exit_open / entry_open − 1.
- Event study keeps overlapping breakout hours. Executable PnL ignores signals until the current trade exits. Same-bar exit and entry is allowed.
- Unconditional control: every coverage-ok hour in the same period with a valid same-horizon next-open to exit-open return.
- Primary cost 10 bps round trip: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps.
- MTM: marked to close while long; fills at open; round-trip fee split with sqrt(1−F) on each side.
- Primary Sharpe annualized with sqrt(365×24) on hourly MTM returns (including flat zeros).
- Discovery / validation / recent splits are chronological and frozen. Ranking uses Discovery MTM Sharpe only.
- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.

## Multiple-testing warning

20 rules were ranked on Discovery. The best in-sample MTM Sharpe **will** be biased upward. A Discovery winner is a **Discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters. Validation was not allowed to change lookback, holding period, direction, entry, exit, or fees.

## Audit assertions

- Historical maximum excludes the current bar.
- Lookback uses UTC timestamps, not positional rows.
- Missing bars were not filled.
- Breakout signal is known only at close t.
- Entry is the open of t+1; exit uses the exact timestamp t_entry + H hours.
- No future data in the signal.
- Losing trades are retained.
- Executable trades do not overlap (new signals ignored while in a position).
- Fees applied as a round trip on completed trades; MTM splits the round trip across entry and exit.
- MTM equity includes intra-trade marks to hourly close.
- Discovery alone selected candidates. Validation did not modify parameters. Recent did not modify parameters.
- Same-horizon control uses coverage-ok timestamps in the same period with a valid H-hour open-to-open return.

Bootstrap seed=42, block=168 hours, samples=2000.
Script runtime 16.3s. Generated by `src/run_breakout_continuation.py`.
