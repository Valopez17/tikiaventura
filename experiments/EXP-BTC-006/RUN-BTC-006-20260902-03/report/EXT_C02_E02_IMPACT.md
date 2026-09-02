# EXT-C02 — Isolated economic impact of E-02

## Answer

Holding everything else identical, replacing positional lookback (`close[i]/close[i-L]-1`) with exact calendar-timestamp lookback (`close(t)/close(t-L hours)-1`, ineligible if exact t-L is missing) is **MATERIAL** under the predeclared Phase 4b criterion (symmetric signal difference >= max(5, int(5% of legacy N)), or absolute mean-net change > 0.002 in Discovery or Validation).

Pooled signal cells tripping the signal threshold: 1 / 24. Frozen-rule Discovery/Validation mean-net cells tripping the economic threshold: 38. Validation mean-net sign changes (reported even if NOT_MATERIAL): 4.

Numeric truth is `outputs/*.csv` and `result/RESULT.json`. This markdown does not override them.

This measurement is not a trading-edge claim, does not authorize capital, is not clean OOS, does not reselect, and does not close E-02. HYP-BTC-002 remains INVALIDATED. E-03 and E-04 remain OPEN. Mechanical_gate is separate from MATERIAL / NOT_MATERIAL.

## Discrepancy vs Phase 4b report

Phase 4b (`phase4b_extreme_move_audit_fix/`) mixed exact-timestamp lookback with a stricter survivor-gate rewrite and hourly mark-to-market equity, and it compared that mixed program to historical Phase 4 outputs. EXT-C02 does not do that. Both arms here walk the same Phase 4 design inside one shared config; the only allowed difference is `lookback_mode`. Survivor-gate classifications are not recomputed. Equity MTM is not a primary metric. Therefore Phase 4b's mixed L6 counts, MTM Sharpe/MaxDD, and classification changes are not the causal answer to this question, even when some trailing-return numbers are close.

## Frozen design (shared)

- Dataset: `btc_tsmom_replication/btcusdt_1h.csv` SHA-256 `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- Coverage: 2017-08-17 04:00:00+00:00 → 2026-08-26 13:00:00+00:00 (n_bars=78986, missing_hours=128)
- Lookbacks: [6, 12, 24, 72] h; percentiles down [0.01, 0.025, 0.05] / up [0.95, 0.975, 0.99]; holds [6, 12, 24, 48, 72, 168] h
- Fee: 0.001 round trip; expanding history 365 calendar days; information strictly before t
- Frozen Top 10 source: `research/market_state_observatory/trade_signal_research/strategy_lab/phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv` (read-only; no reselection)
- only_lookback_mode_differs: True

## Arm definitions

- A LEGACY_POSITIONAL: close[i]/close[i-L]-1
- B EXACT_TIMESTAMP: close(t)/close(t-L hours)-1; eligible only if exact t-L exists; semantics from temporal/exact_timestamp.py; no nearest-bar/fill/interpolation/substitution

## Materiality criterion (predeclared)

{
  "application": "signal criterion on every lookback x tail x percentile cell (period=all); economic criterion on every frozen rule in Discovery and Validation; global MATERIAL if any of those trip; Validation sign changes reported even if NOT_MATERIAL",
  "economic": "abs(mean_net_B - mean_net_A) > 0.002 in Discovery or Validation",
  "mean_net_abs": 0.002,
  "signal": "n_disappeared + n_appeared >= max(5, int(0.05 * max(n_legacy, 1)))",
  "signal_abs": 5,
  "signal_frac": 0.05,
  "source": "phase4b_extreme_move_audit_fix/src/audit_extreme_move_candidates.py (not retuned)"
}

Decision: **MATERIAL**

## L6_down_p1_rebound_long_H6 (both arms in this pipeline)

Phase 4 historical labels (not the causal contrast): discovery N=63 mean net=1.580%; validation N=29 mean net=0.462%; recent N=11 mean net=0.563%.

| Period | N events A/B | N trades A/B | Mean net A | Mean net B | Delta B-A | Sign change | Economic material |
|---|---:|---:|---:|---:|---:|---|---|
| discovery | 163/161 | 63/62 | 1.580% | 1.511% | -0.069% | False | False |
| validation | 56/56 | 29/29 | 0.462% | 0.462% | 0.000% | False | False |
| recent | 18/19 | 11/11 | 0.563% | 0.460% | -0.103% | False | False |

## Frozen Top 10 (original discovery rank; no reselection)

Top 10 economic-material Discovery/Validation rows: 0. Top 10 Validation sign changes: 0.

| Rank | Rule | Period | N trades A/B | Mean net A | Mean net B | Delta | Sign change |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | `L12_up_p97.5_continuation_long_H168` | discovery | 48/48 | 5.054% | 5.059% | 0.006% | False |
| 1 | `L12_up_p97.5_continuation_long_H168` | validation | 34/34 | 2.750% | 2.750% | 0.000% | False |
| 1 | `L12_up_p97.5_continuation_long_H168` | recent | 9/9 | 0.373% | 0.373% | 0.000% | False |
| 2 | `L6_down_p1_rebound_long_H6` | discovery | 63/62 | 1.580% | 1.511% | -0.069% | False |
| 2 | `L6_down_p1_rebound_long_H6` | validation | 29/29 | 0.462% | 0.462% | 0.000% | False |
| 2 | `L6_down_p1_rebound_long_H6` | recent | 11/11 | 0.563% | 0.460% | -0.103% | False |
| 3 | `L24_down_p1_rebound_long_H12` | discovery | 30/30 | 2.523% | 2.523% | 0.000% | False |
| 3 | `L24_down_p1_rebound_long_H12` | validation | 8/8 | -0.737% | -0.737% | 0.000% | False |
| 3 | `L24_down_p1_rebound_long_H12` | recent | 3/3 | 2.842% | 2.842% | 0.000% | False |
| 4 | `L24_up_p97.5_continuation_long_H168` | discovery | 35/35 | 4.142% | 3.989% | -0.153% | False |
| 4 | `L24_up_p97.5_continuation_long_H168` | validation | 23/23 | 3.273% | 3.290% | 0.017% | False |
| 4 | `L24_up_p97.5_continuation_long_H168` | recent | 6/6 | -3.235% | -3.235% | 0.000% | False |
| 5 | `L72_down_p2.5_rebound_long_H24` | discovery | 34/34 | 3.129% | 3.129% | 0.000% | False |
| 5 | `L72_down_p2.5_rebound_long_H24` | validation | 16/16 | 1.103% | 1.103% | 0.000% | False |
| 5 | `L72_down_p2.5_rebound_long_H24` | recent | 5/5 | 0.948% | 0.833% | -0.115% | False |
| 6 | `L72_down_p5_rebound_long_H12` | discovery | 122/122 | 0.926% | 0.877% | -0.049% | False |
| 6 | `L72_down_p5_rebound_long_H12` | validation | 57/57 | -0.493% | -0.493% | 0.000% | False |
| 6 | `L72_down_p5_rebound_long_H12` | recent | 29/29 | 0.338% | 0.338% | 0.000% | False |
| 7 | `L12_up_p95_continuation_long_H12` | discovery | 192/191 | 0.738% | 0.751% | 0.013% | False |
| 7 | `L12_up_p95_continuation_long_H12` | validation | 113/113 | 0.166% | 0.166% | 0.000% | False |
| 7 | `L12_up_p95_continuation_long_H12` | recent | 43/44 | -0.053% | -0.039% | 0.014% | False |
| 8 | `L24_down_p2.5_rebound_long_H72` | discovery | 44/44 | 3.201% | 3.320% | 0.119% | False |
| 8 | `L24_down_p2.5_rebound_long_H72` | validation | 20/20 | -0.163% | -0.163% | 0.000% | False |
| 8 | `L24_down_p2.5_rebound_long_H72` | recent | 10/10 | 2.432% | 2.432% | 0.000% | False |
| 9 | `L24_up_p95_continuation_long_H168` | discovery | 59/60 | 3.486% | 3.532% | 0.045% | False |
| 9 | `L24_up_p95_continuation_long_H168` | validation | 42/43 | 1.351% | 1.241% | -0.109% | False |
| 9 | `L24_up_p95_continuation_long_H168` | recent | 12/12 | 1.466% | 1.466% | 0.000% | False |
| 10 | `L72_down_p5_rebound_long_H6` | discovery | 195/193 | 0.703% | 0.676% | -0.027% | False |
| 10 | `L72_down_p5_rebound_long_H6` | validation | 98/98 | -0.311% | -0.311% | 0.000% | False |
| 10 | `L72_down_p5_rebound_long_H6` | recent | 47/47 | 0.163% | 0.163% | 0.000% | False |

## Signal cells that trip the predeclared threshold (period=all)

- L72 up p99: A=241 B=253 symmetric_diff=12

## Disclaimers

- not_clean_oos: true
- not_trading_edge: true
- does_not_authorize_capital: true
- E03_open: true
- E04_open: true
- E-02 remains FIXED_PENDING_VERIFICATION; EXT-H01 ChatGPT audit is not done in this task
