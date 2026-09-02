# Extreme-move audit fix — Phase 4b

Read-only correction of Phase 4. No new search. Not clean OOS. Not a live system.
Phase 4 files were not overwritten. The Phase 3 calendar candidate was not modified.

## CANDIDATE

Trailing exact 6h BTC return <= expanding p1
→ LONG next hourly open
→ EXIT 6h later.

Rule id: `L6_down_p1_rebound_long_H6`

## DISCOVERY
N trades: old 63 → new 62
mean net (10 bps): old 1.580% → new 1.511%
$10,000 → old $25,766 / new MTM $24,328
Sharpe: old trade-Sharpe 1.6234 → new MTM Sharpe 1.0979
MaxDD: old trade-path -8.67% → new hourly MTM -17.04%
conditional advantage: old 1.408% → new 1.391%
MTM vol 20.43%; Calmar 1.3211; exposure 0.96%; trade_sharpe_diagnostic 1.5366

## VALIDATION
N trades: old 29 → new 29
mean net (10 bps): old 0.462% → new 0.462%
$10,000 → old $11,350 / new MTM $11,350
Sharpe: old trade-Sharpe 0.6361 → new MTM Sharpe 0.4564
MaxDD: old trade-path -6.00% → new hourly MTM -10.54%
conditional advantage: old 0.424% → new 0.424%
MTM vol 10.43%; Calmar 0.4086; exposure 0.66%; trade_sharpe_diagnostic 0.6361

## RECENT
N trades: old 11 → new 11
mean net (10 bps): old 0.563% → new 0.460%
$10,000 → old $10,599 / new MTM $10,481
Sharpe: old trade-Sharpe 0.5463 → new MTM Sharpe 0.4397
MaxDD: old trade-path -6.43% → new hourly MTM -7.98%
conditional advantage: old 0.275% → new 0.296%
MTM vol 7.03%; Calmar 0.3615; exposure 0.46%; trade_sharpe_diagnostic 0.4509

## Answers

1. Did exact timestamp lookbacks materially change the results? **No. L6 p1 down signals: old 237 → new 236; disappeared 2, appeared 1. Candidate discovery mean net old 1.580% → new 1.511%; validation 0.462% → 0.462%.**
2. How many previous signals disappeared because t-6h was genuinely missing? **0 of 237 positional L6-down-p1 signals had no exact t−6h bar.**
3. Did any new signals appear? **Yes: 1 new L6-down-p1 signal hours after exact-timestamp returns + expanding p1.**
4. Does L6_down_p1_rebound_long_H6 remain profitable in Discovery? **Yes (mean net 1.511%, N=62, MTM $10k → $24,328).**
5. Validation? **Yes (mean net 0.462%, N=29, MTM $10k → $11,350).**
6. Recent? **Yes (mean net 0.460%, N=11, MTM $10k → $10,481).**
7. Does conditional advantage remain positive in Validation? **Yes (0.424%; cond 0.449% vs uncond 0.026%).**
8. Recent? **Yes (0.296%).**
9. What is the TRUE hourly mark-to-market Sharpe? **Discovery 1.0979; validation 0.4564; recent 0.4397 (annualized with sqrt(365×24) on hourly equity returns, zeros when flat). trade_sharpe_diagnostic: discovery 1.5366, validation 0.6361, recent 0.4509.**
10. What is TRUE max drawdown? **Discovery -17.04%; validation -10.54%; recent -7.98% (hourly MTM, intra-trade path included). Full-sample MTM MaxDD -17.04%.**
11. Does it survive 20 bps? **Validation mean net 20 bps 0.362% (positive); MTM end cap 20 bps $11,025.**
12. Does it survive 50 bps? **Validation mean net 50 bps 0.060% (positive); MTM end cap 50 bps $10,103.**
13. How did classifications of the original Top 10 change? **3 of 10 changed.**
- `L12_up_p97.5_continuation_long_H168`: STRONG SURVIVOR → SURVIVES
- `L12_up_p95_continuation_long_H12`: FRAGILE → SURVIVES
- `L24_up_p95_continuation_long_H168`: STRONG SURVIVOR → SURVIVES
14. Does the previous 168h rally-continuation winner still qualify as STRONG SURVIVOR under the stricter rule? **No (old STRONG SURVIVOR → new SURVIVES).**
15. Final decision for Crash Rebound Candidate: **PASS**

## CRASH_REBOUND_CANDIDATE_V1 = FROZEN

lookback = 6h
threshold = expanding p1
direction = LONG
entry = next hourly open
holding = 6h
fee baseline = 10 bps

Do not optimize this rule again. No p0.5 / 4h / 8h / extra indicators.

## Frozen Top 10 — corrected classification

| Rank | Rule | Old class | New class | Val mean net | Val MTM Sharpe | Val adv | Rec mean net | Rec adv |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | `L12_up_p97.5_continuation_long_H168` | STRONG SURVIVOR | SURVIVES | 2.750% | 1.0820 | 1.770% | 0.373% | -2.696% |
| 2 | `L6_down_p1_rebound_long_H6` | STRONG SURVIVOR | STRONG SURVIVOR | 0.462% | 0.4564 | 0.424% | 0.460% | 0.296% |
| 3 | `L24_down_p1_rebound_long_H12` | FAIL | FAIL | -0.737% | -0.1490 | 0.278% | 2.842% | 3.562% |
| 4 | `L24_up_p97.5_continuation_long_H168` | SURVIVES | SURVIVES | 3.290% | 1.0415 | 2.657% | -3.235% | -5.473% |
| 5 | `L72_down_p2.5_rebound_long_H24` | SURVIVES | SURVIVES | 1.103% | 0.3583 | 0.462% | 0.833% | 3.270% |
| 6 | `L72_down_p5_rebound_long_H12` | FAIL | FAIL | -0.493% | -0.4613 | -0.167% | 0.338% | 0.254% |
| 7 | `L12_up_p95_continuation_long_H12` | FRAGILE | SURVIVES | 0.166% | 0.3560 | 0.091% | -0.039% | -0.138% |
| 8 | `L24_down_p2.5_rebound_long_H72` | FAIL | FAIL | -0.163% | -0.0103 | 0.153% | 2.432% | 4.915% |
| 9 | `L24_up_p95_continuation_long_H168` | STRONG SURVIVOR | SURVIVES | 1.241% | 0.5876 | 1.782% | 1.466% | -1.941% |
| 10 | `L72_down_p5_rebound_long_H6` | FAIL | FAIL | -0.311% | -0.5102 | -0.067% | 0.163% | 0.089% |

## Audit assertions

- Phase 4 CSVs were read, not overwritten.
- Trailing returns require both `t` and `t−L hours` to exist as exact timestamps.
- Expanding percentiles use only finite returns with timestamp < t; 30 random checks vs NumPy passed.
- Execution remains open of t+1; exit open t+1+H; overlapping signals ignored in PnL.
- Hourly MTM uses close while in a position; fills at open; round-trip fee split so entry×exit = (1−fee).
- Primary Sharpe is hourly MTM × sqrt(365×24). trade_sharpe_diagnostic is not used for STRONG SURVIVOR.
- MaxDD is from the hourly equity path, including intra-trade marks.
- Frozen Top 10 were not reselected.
- Shorts remain theoretical unlevered.

Script runtime 23.1s. Generated by `src/audit_extreme_move_candidates.py`.
