# Extreme BTC move — rebound vs continuation — Phase 4

Discovery candidate search over 288 frozen extreme-move rules.
Not clean out-of-sample. Not a live trading system.
Do not read this as “we found the optimal crash/rally trade.”
The real evidence is whether a **frozen** discovery candidate survives later periods.
The Phase 3 calendar candidate was not modified and is not combined here.

## BEST FROZEN DISCOVERY CANDIDATE

**SIGNAL:** trailing 12h return >= expanding p97.5

**ACTION:** LONG (continuation)

**ENTRY:** next hourly open (bar t+1 open; signal uses close t)

**EXIT:** open exactly 168 hours after entry

Ranked #1 by discovery executable Sharpe at 10 bps, among rules with mean net > 0 and N ≥ 30.

## DISCOVERY (data start → 2021-12-31)
$10,000 → $85,910
Sharpe: 1.6641
mean trade (gross): 5.159%
mean net trade (10 bps): 5.054%
median net trade: 3.594%
win rate: 68.75%
profit factor: 3.8695
max drawdown: -27.53%
CAGR: 63.44%
N trades (non-overlapping): 48
N events (overlapping): 488
BTC cond mean / uncond mean / diff: 3.195% / 1.694% / 1.501%
Strategy cond mean / uncond same-direction mean / diff: 3.195% / 1.694% / 1.501%

## VALIDATION (2022-01-01 → 2024-12-31)
$10,000 → $22,641
Sharpe: 1.0955
mean trade (gross): 2.853%
mean net trade (10 bps): 2.750%
median net trade: 2.358%
win rate: 55.88%
profit factor: 2.5081
max drawdown: -18.56%
CAGR: 31.28%
N trades (non-overlapping): 34
N events (overlapping): 273
BTC cond mean / uncond mean / diff: 2.533% / 0.793% / 1.741%
Strategy cond / uncond / diff: 2.533% / 0.793% / 1.741%
Classification: **STRONG SURVIVOR**

## RECENT (2025-01-01 → latest complete bar)
$10,000 → $10,254
Sharpe: 0.1915
mean trade (gross): 0.473%
mean net trade (10 bps): 0.373%
median net trade: 1.211%
win rate: 66.67%
max drawdown: -10.09%
CAGR: 1.53%
N trades (non-overlapping): 9
N events (overlapping): 65
BTC cond / uncond / diff: -2.820% / -0.124% / -2.696%

SHORT results use unlevered `entry/exit − 1` and the same round-trip fee. Borrow, funding, locate, and implementation costs are omitted. Shorts are theoretical research, not live-tradeable as specified.

## Answers

1. After extreme crashes, does BTC rebound or continue? **Pooled across lookbacks/holds, discovery BTC difference 1.230%, validation -0.012% (not a single crash effect). Rebound (subsequent BTC > ordinary) in both discovery and validation at lookback(s) 6h, 24h. Sign flips or is inconclusive at lookback(s) 12h, 72h. No stable short-after-crash pattern entered the Top 10.**
2. After extreme rallies, does BTC continue or reverse? **Pooled across lookbacks/holds, discovery BTC difference -0.060%, validation 0.657%. Continuation (subsequent BTC > ordinary) in both periods at lookback(s) 6h, 12h. Sign flips or is inconclusive at lookback(s) 24h, 72h.**
3. Does the answer depend on whether the original move occurred over 6h, 12h, 24h or 72h? **Yes, magnitudes differ by lookback; sign is reported below.**
- 6h lookback: crash BTC-diff discovery 1.069% / validation 0.323%; rally discovery 0.476% / validation 0.470%
- 12h lookback: crash BTC-diff discovery 0.788% / validation -0.053%; rally discovery 0.493% / validation 0.462%
- 24h lookback: crash BTC-diff discovery 1.589% / validation 0.118%; rally discovery -0.206% / validation 0.260%
- 72h lookback: crash BTC-diff discovery 1.475% / validation -0.436%; rally discovery -1.001% / validation 1.435%
4. At what future horizon is the strongest behavior visible? **Crashes: lookback 6h → hold 24h (validation BTC difference 0.796%; discovery 1.701%). Rallies: lookback 12h → hold 168h (validation BTC difference 1.463%; discovery 1.722%).**
5. Does price typically move against the eventual strategy before moving in its favor? **After downside extreme events, mean +1h BTC path is 0.096% and mean +6h is 0.302%, so the average crash path does not fall further first. MAE still prints because later lows in the 168h window are deep (mean MAE -10.291%). MAE occurs before MFE in 58.32% of crash events, only slightly above half — not strong TYPE-2 evidence.**
6. What are typical MAE and MFE? **Mean MAE_168h (from entry, using bar lows) -10.291%; mean MFE_168h (bar highs) 9.966%. Median MAE -7.144%; median MFE 7.843%.**
7. Does the conditional return differ materially from an ordinary same-horizon BTC return? **Rank-1 discovery BTC difference 1.501% (cond 3.195% vs uncond 1.694%); strategy-direction difference 1.501%. Validation BTC difference 1.741%. Recent event-study BTC difference -2.696%.**
8. Does the best rule survive 2022–2024? **Yes (classification: STRONG SURVIVOR). Validation mean net 2.750%, Sharpe 1.0955, strategy advantage 1.741%. Validation 95% CI for mean net is [-0.325%, 5.118%] and includes zero, so survival is a point-estimate call, not a tight interval.**
9. Does it survive 2025–latest? **Executable recent mean net 0.373%, Sharpe 0.1915, N=9. Overlapping event-study BTC difference is -2.696% (conditional below ordinary). Small N; not a contradiction on executable PnL, not a confirmation either.**
10. Does it survive 10/20/50 bps? **10 bps validation mean net positive; 20 bps positive; 50 bps positive. Discovery ending capital 0/10/20/50 bps: $90,137 / $85,910 / $81,878 / $70,861. Validation 0/10/20/50: $23,424 / $22,641 / $21,883 / $19,754.**
11. How many of the Top 10 survive? **5 SURVIVES** (of which **3 STRONG SURVIVOR**), 1 FRAGILE, 4 FAIL.
12. What happened to $10,000? **Discovery $85,910; validation $22,641; recent $10,254 (each period starts from $10,000; not chained).**
13. Is there one clear economic pattern or only isolated parameter combinations? **Top 10 clusters by family: down_rebound_L72 (n=3); down_rebound_L24 (n=2); up_continuation_L12 (n=2); up_continuation_L24 (n=2); down_rebound_L6 (n=1). Zero of the Top 10 are shorts. Two LONG families appear: crash rebound at short holds, and rally continuation at 168h.**
14. Final conclusion: **ROBUST EXTREME-MOVE EFFECT**

Crash paths at the lookbacks that keep a positive validation difference look closer to TYPE 1 (immediate rebound): mean +1h after downside events is not negative. Rally lookbacks that keep a positive difference in both periods are TYPE 3 (continued momentum), especially at the 168h hold that dominates the Top 10. No short rule is in the frozen Top 10 (short count=0). Point-estimate survivors exist, so this is not TYPE 5, but the effect is a handful of LONG parameter families (short-horizon crash rebound; 12h/24h rally continuation held ~7d), not a universal law of extremes.

15. If a candidate survives, write its exact executable rule in no more than five lines.

If BTC's trailing 12h close-to-close return is >= its expanding historical p97.5 (history s < t, ≥365 calendar days), buy the next hourly open and exit at the open 168h later. Ignore new signals until flat. Primary cost assumption: 10 bps round trip.

## Frozen top 10 — decision rule

| Rank | Rule | Class | Val $10k | Val Sharpe | Val mean net | Val BTC-diff | Rec mean net |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `L12_up_p97.5_continuation_long_H168` | STRONG SURVIVOR | $22,641 | 1.0955 | 2.750% | 1.741% | 0.373% |
| 2 | `L6_down_p1_rebound_long_H6` | STRONG SURVIVOR | $11,350 | 0.6361 | 0.462% | 0.424% | 0.563% |
| 3 | `L24_down_p1_rebound_long_H12` | FAIL | $9,390 | -0.3673 | -0.737% | 0.278% | 2.842% |
| 4 | `L24_up_p97.5_continuation_long_H168` | SURVIVES | $19,347 | 1.0101 | 3.273% | 2.606% | -3.235% |
| 5 | `L72_down_p2.5_rebound_long_H24` | SURVIVES | $11,515 | 0.3785 | 1.103% | 0.462% | 0.948% |
| 6 | `L72_down_p5_rebound_long_H12` | FAIL | $7,208 | -0.5409 | -0.493% | -0.171% | 0.338% |
| 7 | `L12_up_p95_continuation_long_H12` | FRAGILE | $11,584 | 0.3786 | 0.166% | 0.095% | -0.053% |
| 8 | `L24_down_p2.5_rebound_long_H72` | FAIL | $9,223 | -0.0596 | -0.163% | 0.105% | 2.432% |
| 9 | `L24_up_p95_continuation_long_H168` | STRONG SURVIVOR | $15,486 | 0.6142 | 1.351% | 1.833% | 1.466% |
| 10 | `L72_down_p5_rebound_long_H6` | FAIL | $7,098 | -0.6415 | -0.311% | -0.069% | 0.163% |

## Calendar-year path for the rank-1 discovery rule

years_with_positive_mean_net=8/9; max_positive_year_share=0.33; positive_outside_2020_2022=5

| Year | N | Year return (10 bps) | Mean net | Win rate | Sharpe |
|---|---:|---:|---:|---:|---:|
| 2018 | 4 | 1.39% | 0.718% | 50.00% | 0.1427 |
| 2019 | 12 | 65.83% | 4.534% | 75.00% | 2.1584 |
| 2020 | 14 | 143.14% | 6.842% | 78.57% | 3.0912 |
| 2021 | 18 | 110.15% | 4.972% | 61.11% | 1.6283 |
| 2022 | 13 | -0.26% | 0.134% | 46.15% | 0.0829 |
| 2023 | 10 | 22.30% | 2.506% | 50.00% | 0.7301 |
| 2024 | 11 | 85.61% | 6.063% | 72.73% | 2.4404 |
| 2025 | 5 | -2.68% | -0.430% | 60.00% | -0.1853 |
| 2026 | 4 | 5.36% | 1.376% | 75.00% | 0.6748 |

## Block bootstrap (168-hour blocks, 2000 samples)

Primary confirmatory interval is **validation**. Discovery intervals are biased upward by the search.
Blocks are drawn from the hourly signal series (circular) to keep crash clustering.
Rank-1 discovery 95% CI mean net trade: [1.429%, 6.528%]
Rank-1 discovery 95% CI strategy advantage vs unconditional: [-0.853%, 3.896%]
Rank-1 validation 95% CI mean net trade: [-0.325%, 5.118%]
Rank-1 validation 95% CI strategy advantage vs unconditional: [-1.488%, 5.402%]

## Data audit

- File: `/Users/valeria/Documents/tikiaventura/btc_tsmom_replication/btcusdt_1h.csv`
- UTC start/end: 2017-08-17 04:00:00+00:00 → 2026-08-26 13:00:00+00:00
- Bars: 78986; unique UTC: True; chronological: True; OHLC valid: True
- Duplicated bars dropped: 0; invalid OHLC rows dropped: 0
- Missing hours in the UTC 1h grid (not filled): 128. Preview: 2017-09-06 17:00:00+00:00, 2017-09-06 18:00:00+00:00, 2017-09-06 19:00:00+00:00, 2017-09-06 20:00:00+00:00, 2017-09-06 21:00:00+00:00, 2017-09-06 22:00:00+00:00, 2018-01-04 04:00:00+00:00, 2018-02-08 01:00:00+00:00, ... (128 total)
- Events skipped for missing t+1 entry bar (summed over lookback×tail×percentile): 8
- Events skipped for missing exit open (summed over lookback×tail×percentile×hold): 480
- Expanding-percentile audit: 24 random timestamps × each lookback/percentile matched `numpy.quantile(history s<t)`.

## Research design

- Search space: 4 lookbacks × 3 thresholds × 6 exits × 2 tails × 2 directions = 288 rules.
- Signal: close_t / close_(t−H) − 1 vs expanding percentile of {s < t}, after 365 calendar days.
- Execution: buy/short the **open** of bar t+1; exit the open H hours later. Never the signal close.
- LONG return = exit_open / entry_open − 1. SHORT return = entry_open / exit_open − 1 (theoretical).
- Event study keeps overlapping crash hours. Executable PnL ignores signals until the current trade exits. Same-bar exit and entry is allowed.
- Unconditional control: every hour in the same period with a valid same-horizon next-open to exit-open return.
- Primary cost 10 bps round trip: net = (1+gross)×(1−0.0010)−1. Also 0 / 20 / 50 bps.
- Discovery / validation / recent splits are chronological and frozen. Ranking uses discovery executable Sharpe only.
- Because this project has already looked at recent BTC, validation and recent are **not** clean OOS.

## Multiple-testing warning

288 rules were ranked on discovery. The best in-sample Sharpe **will** be biased upward. A discovery winner is a **discovery candidate**. Persistence in 2022–2024 (and 2025+) is the evidence that matters.
Validation was not allowed to change lookback, percentile, holding period, or direction.

## Audit assertions

- Expanding percentiles use only s < t (current return is inserted after the quantile is read).
- Signal uses close t; execution begins at open t+1; no future data in the signal.
- If t+1 or the required exit open is missing, the event is skipped (prices are not filled).
- Validation did not affect ranking. Top 10 were frozen from discovery, then scored unchanged.
- Full history was not used to choose the winner.
- Overlapping signals are removed from strategy PnL; they remain in EVENT_PATHS / event-study columns.
- Costs applied once per completed executable trade.
- Losing trades are retained.
- Unconditional comparison uses the identical holding horizon and the same period window.
- SHORT metrics are labeled theoretical.

Bootstrap seed=42, block=168 hours, samples=2000.
Script runtime 22.5s. Generated by `src/run_extreme_move_scan.py`.
