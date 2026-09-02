# Capitulation entry study — Phase 1

BTC-only daily event study. Not a trading strategy. Not a backtest. Thresholds 5% / 80% were frozen before looking at 2024-08-05. Primary counts use event dates **before 2024-01-01**.

P(return > 0) is an empirical conditional frequency in this sample, not a true future probability.
Median + X% means half of qualifying historical events returned more than X%, half less.
Max drawdown after entry is the typical path pain after buying the event close.
Max runup is the best close-to-close upside available within the horizon.
Differences vs baseline are descriptive, not causal effects.

## Data

| item | value |
|---|---|
| source | Empalme: Bitstamp BTCUSD (CryptoDataDownload / trusted project file) until 2017-08-16; Binance BTCUSDT spot 1d UTC from 2017-08-17. Closes are not interpolated. Incomplete current UTC day dropped. |
| trusted prices | `btc_tsmom_replication/data/btcusd_daily.csv` |
| date range | 2014-11-28 → 2026-08-28 |
| N days | 4292 |
| missing calendar days | 0 |
| first missing dates | (none) |
| Bitstamp days | 993 |
| Binance days | 3299 |
| days with volume | 3299 |
| splice jump 2017-08-17 | NA (no Bitstamp print that day) |
| volume | Relative volume uses Binance BTC base volume only from 2017-08-17. Bitstamp CDD volume columns are internally inconsistent in the pre-listing sample (BTC/USD fields swapped) and were not used. |
| timezone | UTC daily close |
| splice-day return | 2017-08-17 `ret_1d` set to NaN (source join, not a market crash) |

## Definitions

- Features at t: 1d/3d/7d simple return, drawdown from trailing 30d high, 20d stdev of daily returns, volume / prior-20d median volume.
- Expanding percentiles use only s < t, min 365 finite observations.
- EXTREME_1D: 1d return ≤ historical 5th percentile.
- EXTREME_MULTI_DAY: 3d **or** 7d return ≤ historical 5th percentile.
- CAPITULATION_PLUS_STRESS: (EXTREME_1D or EXTREME_MULTI_DAY) **and** 20d vol ≥ historical 80th percentile.
- De-cluster: keep the first event, then 7 calendar-day cooldown. Raw flags are retained.
- Forward return over H days: P_{t+H}/P_t − 1 (event-day crash is excluded).
- Baseline: every eligible BTC day in the same era (pre-2024, enough history, finite H-day outcome).

## 1. How many capitulation events exist?

| definition | raw pre-2024 | declustered pre-2024 | raw full sample | declustered full sample |
|---|---:|---:|---:|---:|
| EXTREME_1D | 136 | 81 | 150 | 91 |
| EXTREME_MULTI_DAY | 222 | 71 | 244 | 80 |
| CAPITULATION_PLUS_STRESS | 134 | 40 | 135 | 41 |

Primary analysis below uses **declustered, pre-2024** events.

## EXTREME_1D — declustered pre-2024 vs baseline

### Horizon 1d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | -0.1% | 0.5% | -2.1% | 2.2% | 56.8% | 1.2% | 0.0% | 4.9% | 0.0% | 0.0% | 0.5% |
| baseline (all eligible days) | 2954 | 0.2% | 0.1% | -1.2% | 1.7% | 53.0% | 1.6% | 0.1% | 1.3% | 0.0% | 0.0% | 0.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 0.5% | 0.1% | 0.4% | 56.8% | 53.0% | 3.8% | 1.2% | 1.6% | 0.0% | 0.1% | 4.9% | 1.3% | 0.0% | 0.0% |

### Horizon 3d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | -0.3% | 0.3% | -5.0% | 4.3% | 51.9% | 6.2% | 1.2% | 7.4% | 1.2% | -3.6% | 2.3% |
| baseline (all eligible days) | 2954 | 0.7% | 0.5% | -2.4% | 3.9% | 55.3% | 7.0% | 0.6% | 4.9% | 0.5% | -1.8% | 1.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 0.3% | 0.5% | -0.2% | 51.9% | 55.3% | -3.5% | 6.2% | 7.0% | 1.2% | 0.6% | 7.4% | 4.9% | 1.2% | 0.5% |

### Horizon 7d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | -0.4% | 0.5% | -4.7% | 4.9% | 50.6% | 12.3% | 3.7% | 13.6% | 7.4% | -7.1% | 4.1% |
| baseline (all eligible days) | 2954 | 1.7% | 0.9% | -3.4% | 6.4% | 55.1% | 16.8% | 4.7% | 9.7% | 2.1% | -4.4% | 3.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 0.5% | 0.9% | -0.4% | 50.6% | 55.1% | -4.5% | 12.3% | 16.8% | 3.7% | 4.7% | 13.6% | 9.7% | 7.4% | 2.1% |

### Horizon 14d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | 0.5% | -0.3% | -9.4% | 7.9% | 46.9% | 21.0% | 11.1% | 22.2% | 7.4% | -10.9% | 7.6% |
| baseline (all eligible days) | 2954 | 3.4% | 1.7% | -5.0% | 10.3% | 57.2% | 25.4% | 12.6% | 15.4% | 4.3% | -7.6% | 6.2% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | -0.3% | 1.7% | -2.0% | 46.9% | 57.2% | -10.3% | 21.0% | 25.4% | 11.1% | 12.6% | 22.2% | 15.4% | 7.4% | 4.3% |

### Horizon 30d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | 5.6% | 1.7% | -7.2% | 12.0% | 51.9% | 28.4% | 19.8% | 23.5% | 14.8% | -16.9% | 9.7% |
| baseline (all eligible days) | 2954 | 7.5% | 3.8% | -8.3% | 20.0% | 58.4% | 38.0% | 24.9% | 22.5% | 8.8% | -13.4% | 11.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 1.7% | 3.8% | -2.1% | 51.9% | 58.4% | -6.5% | 28.4% | 38.0% | 19.8% | 24.9% | 23.5% | 22.5% | 14.8% | 8.8% |

### Horizon 60d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | 11.8% | 1.2% | -15.8% | 33.6% | 54.3% | 40.7% | 37.0% | 30.9% | 21.0% | -25.2% | 17.9% |
| baseline (all eligible days) | 2954 | 16.3% | 10.0% | -11.5% | 34.5% | 61.0% | 50.0% | 38.8% | 27.0% | 15.7% | -21.0% | 21.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 1.2% | 10.0% | -8.7% | 54.3% | 61.0% | -6.7% | 40.7% | 50.0% | 37.0% | 38.8% | 30.9% | 27.0% | 21.0% | 15.7% |

### Horizon 90d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 81 | 25.2% | 8.5% | -19.9% | 45.8% | 54.3% | 49.4% | 40.7% | 34.6% | 24.7% | -29.7% | 28.0% |
| baseline (all eligible days) | 2954 | 27.1% | 15.6% | -12.3% | 50.3% | 61.9% | 53.4% | 46.0% | 27.4% | 19.2% | -25.9% | 30.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 81 | 8.5% | 15.6% | -7.0% | 54.3% | 61.9% | -7.6% | 49.4% | 53.4% | 40.7% | 46.0% | 34.6% | 27.4% | 24.7% | 19.2% |

## EXTREME_MULTI_DAY — declustered pre-2024 vs baseline

### Horizon 1d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 0.2% | 0.6% | -1.8% | 3.1% | 63.4% | 4.2% | 0.0% | 7.0% | 0.0% | 0.0% | 0.6% |
| baseline (all eligible days) | 2954 | 0.2% | 0.1% | -1.2% | 1.7% | 53.0% | 1.6% | 0.1% | 1.3% | 0.0% | 0.0% | 0.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 0.6% | 0.1% | 0.5% | 63.4% | 53.0% | 10.4% | 4.2% | 1.6% | 0.0% | 0.1% | 7.0% | 1.3% | 0.0% | 0.0% |

### Horizon 3d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 0.7% | 1.0% | -3.8% | 5.3% | 56.3% | 12.7% | 1.4% | 12.7% | 1.4% | -3.3% | 2.8% |
| baseline (all eligible days) | 2954 | 0.7% | 0.5% | -2.4% | 3.9% | 55.3% | 7.0% | 0.6% | 4.9% | 0.5% | -1.8% | 1.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 1.0% | 0.5% | 0.5% | 56.3% | 55.3% | 1.0% | 12.7% | 7.0% | 1.4% | 0.6% | 12.7% | 4.9% | 1.4% | 0.5% |

### Horizon 7d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 1.5% | 1.3% | -4.8% | 8.3% | 56.3% | 21.1% | 8.5% | 15.5% | 7.0% | -7.1% | 4.5% |
| baseline (all eligible days) | 2954 | 1.7% | 0.9% | -3.4% | 6.4% | 55.1% | 16.8% | 4.7% | 9.7% | 2.1% | -4.4% | 3.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 1.3% | 0.9% | 0.4% | 56.3% | 55.1% | 1.2% | 21.1% | 16.8% | 8.5% | 4.7% | 15.5% | 9.7% | 7.0% | 2.1% |

### Horizon 14d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 2.4% | 0.5% | -5.9% | 11.9% | 52.1% | 28.2% | 9.9% | 15.5% | 8.5% | -11.1% | 8.2% |
| baseline (all eligible days) | 2954 | 3.4% | 1.7% | -5.0% | 10.3% | 57.2% | 25.4% | 12.6% | 15.4% | 4.3% | -7.6% | 6.2% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 0.5% | 1.7% | -1.2% | 52.1% | 57.2% | -5.1% | 28.2% | 25.4% | 9.9% | 12.6% | 15.5% | 15.4% | 8.5% | 4.3% |

### Horizon 30d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 7.7% | 3.2% | -10.0% | 18.6% | 54.9% | 32.4% | 22.5% | 25.4% | 12.7% | -16.2% | 13.8% |
| baseline (all eligible days) | 2954 | 7.5% | 3.8% | -8.3% | 20.0% | 58.4% | 38.0% | 24.9% | 22.5% | 8.8% | -13.4% | 11.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 3.2% | 3.8% | -0.6% | 54.9% | 58.4% | -3.4% | 32.4% | 38.0% | 22.5% | 24.9% | 25.4% | 22.5% | 12.7% | 8.8% |

### Horizon 60d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 15.4% | 3.8% | -13.6% | 37.9% | 54.9% | 42.3% | 36.6% | 28.2% | 18.3% | -25.2% | 21.5% |
| baseline (all eligible days) | 2954 | 16.3% | 10.0% | -11.5% | 34.5% | 61.0% | 50.0% | 38.8% | 27.0% | 15.7% | -21.0% | 21.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 3.8% | 10.0% | -6.2% | 54.9% | 61.0% | -6.1% | 42.3% | 50.0% | 36.6% | 38.8% | 28.2% | 27.0% | 18.3% | 15.7% |

### Horizon 90d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 71 | 28.0% | 10.1% | -20.1% | 42.1% | 54.9% | 50.7% | 42.3% | 36.6% | 25.4% | -30.0% | 28.0% |
| baseline (all eligible days) | 2954 | 27.1% | 15.6% | -12.3% | 50.3% | 61.9% | 53.4% | 46.0% | 27.4% | 19.2% | -25.9% | 30.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 71 | 10.1% | 15.6% | -5.5% | 54.9% | 61.9% | -7.0% | 50.7% | 53.4% | 42.3% | 46.0% | 36.6% | 27.4% | 25.4% | 19.2% |

## CAPITULATION_PLUS_STRESS — declustered pre-2024 vs baseline

### Horizon 1d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 0.7% | 0.6% | -2.1% | 2.3% | 57.5% | 5.0% | 0.0% | 5.0% | 0.0% | 0.0% | 0.6% |
| baseline (all eligible days) | 2954 | 0.2% | 0.1% | -1.2% | 1.7% | 53.0% | 1.6% | 0.1% | 1.3% | 0.0% | 0.0% | 0.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | 0.6% | 0.1% | 0.4% | 57.5% | 53.0% | 4.5% | 5.0% | 1.6% | 0.0% | 0.1% | 5.0% | 1.3% | 0.0% | 0.0% |

### Horizon 3d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | -0.3% | -0.0% | -5.5% | 4.2% | 50.0% | 15.0% | 2.5% | 12.5% | 2.5% | -5.8% | 1.8% |
| baseline (all eligible days) | 2954 | 0.7% | 0.5% | -2.4% | 3.9% | 55.3% | 7.0% | 0.6% | 4.9% | 0.5% | -1.8% | 1.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | -0.0% | 0.5% | -0.5% | 50.0% | 55.3% | -5.3% | 15.0% | 7.0% | 2.5% | 0.6% | 12.5% | 4.9% | 2.5% | 0.5% |

### Horizon 7d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 1.4% | -1.0% | -9.2% | 6.7% | 42.5% | 22.5% | 15.0% | 22.5% | 5.0% | -10.4% | 5.0% |
| baseline (all eligible days) | 2954 | 1.7% | 0.9% | -3.4% | 6.4% | 55.1% | 16.8% | 4.7% | 9.7% | 2.1% | -4.4% | 3.6% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | -1.0% | 0.9% | -1.8% | 42.5% | 55.1% | -12.6% | 22.5% | 16.8% | 15.0% | 4.7% | 22.5% | 9.7% | 5.0% | 2.1% |

### Horizon 14d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 2.8% | -0.6% | -6.3% | 6.7% | 42.5% | 22.5% | 12.5% | 12.5% | 5.0% | -12.4% | 6.7% |
| baseline (all eligible days) | 2954 | 3.4% | 1.7% | -5.0% | 10.3% | 57.2% | 25.4% | 12.6% | 15.4% | 4.3% | -7.6% | 6.2% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | -0.6% | 1.7% | -2.4% | 42.5% | 57.2% | -14.7% | 22.5% | 25.4% | 12.5% | 12.6% | 12.5% | 15.4% | 5.0% | 4.3% |

### Horizon 30d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 8.4% | 2.8% | -11.6% | 16.5% | 57.5% | 32.5% | 22.5% | 27.5% | 12.5% | -18.5% | 13.7% |
| baseline (all eligible days) | 2954 | 7.5% | 3.8% | -8.3% | 20.0% | 58.4% | 38.0% | 24.9% | 22.5% | 8.8% | -13.4% | 11.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | 2.8% | 3.8% | -1.0% | 57.5% | 58.4% | -0.9% | 32.5% | 38.0% | 22.5% | 24.9% | 27.5% | 22.5% | 12.5% | 8.8% |

### Horizon 60d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 18.3% | 8.3% | -13.4% | 51.7% | 60.0% | 47.5% | 42.5% | 30.0% | 20.0% | -24.5% | 21.4% |
| baseline (all eligible days) | 2954 | 16.3% | 10.0% | -11.5% | 34.5% | 61.0% | 50.0% | 38.8% | 27.0% | 15.7% | -21.0% | 21.3% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | 8.3% | 10.0% | -1.7% | 60.0% | 61.0% | -1.0% | 47.5% | 50.0% | 42.5% | 38.8% | 30.0% | 27.0% | 20.0% | 15.7% |

### Horizon 90d

| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | P(<-10%) | P(<-20%) | median max DD | median max runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capitulation | 40 | 34.1% | 19.5% | -17.7% | 56.4% | 57.5% | 57.5% | 50.0% | 27.5% | 22.5% | -28.9% | 30.2% |
| baseline (all eligible days) | 2954 | 27.1% | 15.6% | -12.3% | 50.3% | 61.9% | 53.4% | 46.0% | 27.4% | 19.2% | -25.9% | 30.1% |

| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap − base | 40 | 19.5% | 15.6% | 4.0% | 57.5% | 61.9% | -4.4% | 57.5% | 53.4% | 50.0% | 46.0% | 27.5% | 27.4% | 22.5% | 19.2% |

## 6. Bigger crash, better future return?

Within pre-2024 declustered EXTREME_1D, split by median event-day 1d return (more negative vs less negative). Same 60d outcome. Not a new threshold.

| half | N | median 1d return | median 60d future | P(60d > 0) |
|---|---:|---:|---:|---:|
| more severe 1d | 41 | -9.7% | 0.1% | 51.2% |
| less severe 1d | 40 | -6.8% | 5.4% | 57.5% |

In this split, the more severe half had a **lower** median 60d return. “The bigger the crash, the better the future return” is **not** supported here.

Bucket comparison, same 60d outcome, declustered pre-2024:

| definition | N | median 60d | P(60d > 0) |
|---|---:|---:|---:|
| EXTREME_1D | 81 | 1.2% | 54.3% |
| EXTREME_MULTI_DAY | 71 | 3.8% | 54.9% |
| CAPITULATION_PLUS_STRESS | 40 | 8.3% | 60.0% |

## 7. Do volatility and abnormal volume distinguish GOOD vs BAD 60d outcomes?

GOOD_60D = future 60d return > +20%. BAD_60D = future 60d return < 0%. OTHER = the rest. Labels are outcomes, not inputs. Sample: declustered pre-2024 CAPITULATION_PLUS_STRESS.

| outcome | N | median 1d ret | median 3d ret | median 7d ret | median 30d DD | median vol pctl | IQR vol pctl | median rel-vol pctl | IQR rel-vol pctl |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GOOD_60D | 17 | -6.3% | -8.9% | -4.1% | -16.7% | 89.2 | 12.5 | 48.9 | 34.1 |
| BAD_60D | 16 | -7.8% | -8.3% | -1.3% | -19.6% | 91.6 | 7.3 | 86.3 | 17.5 |
| OTHER | 7 | -7.4% | -9.3% | -10.8% | -19.5% | 85.9 | 7.3 | 73.4 | 22.3 |

Medians differ by at least 5 percentile points on relative volume — a candidate pattern, not a classifier.

## 8–9. Case study: 2024-08-05

Thresholds and percentiles use **only** data through 2024-08-04. Outcomes below were not known at t.

| observable | value | percentile vs history through 2024-08-04 |
|---|---:|---:|
| daily return | -7.1% | 2.9 |
| 3d return | -12.2% | 2.9 |
| 7d return | -19.1% | 2.2 |
| 30d drawdown | -20.9% | 12.1 |
| 20d volatility | 0.0273 | 40.7 |
| relative volume | 5.6271 | 99.9 |

| bucket | triggered? |
|---|---|
| EXTREME_1D | YES |
| EXTREME_MULTI_DAY | YES |
| CAPITULATION_PLUS_STRESS | no |

| horizon | future return | >0 | >+10% | >+20% | <-10% | <-20% | max DD | max runup |
|---:|---:|---|---|---|---|---|---:|---:|
| +1d | 3.7% | 1 | 0 | 0 | 0 | 0 | 0.0% | 3.7% |
| +3d | 14.2% | 1 | 1 | 0 | 0 | 0 | -1.6% | 14.2% |
| +7d | 9.9% | 1 | 0 | 0 | 0 | 0 | -4.8% | 14.2% |
| +14d | 10.0% | 1 | 1 | 0 | 0 | 0 | -6.7% | 14.2% |
| +30d | 7.3% | 1 | 0 | 0 | 0 | 0 | -10.8% | 18.9% |
| +60d | 14.9% | 1 | 1 | 0 | 0 | 0 | -16.0% | 21.9% |
| +90d | 27.3% | 1 | 1 | 1 | 0 | 0 | -16.0% | 34.7% |

Among pre-2024 declustered CAPITULATION_PLUS_STRESS events, the 2024-08-05 1d-return percentile sits at empirical rank 45.0% (0% = more extreme than every prior event's percentile).

Using only pre-event information, 2024-08-05 was an extreme return day but did not meet CAPITULATION_PLUS_STRESS (volatility gate). It is a case study, not a template.

## Answers

1. How many capitulation events exist? Pre-2024 declustered: EXTREME_1D N=81, EXTREME_MULTI_DAY N=71, CAPITULATION_PLUS_STRESS N=40.
2. After extreme selloffs, is BTC historically more likely to rise than on an unconditional day? On CAPITULATION_PLUS_STRESS, P(>0) exceeds baseline at horizons 1d.
3. At which horizons does the difference appear? Median future return above baseline at 1d (Δ 0.4%); 90d (Δ 4.0%).
4. How large is the median upside? CAPITULATION_PLUS_STRESS 30d median=2.8%, 60d=8.3%, 90d=19.5% (unconditional 60d median=10.0%).
5. What is the downside / max-drawdown risk after buying? CAPITULATION_PLUS_STRESS median max DD 30d=-18.5%, 60d=-24.5%, 90d=-28.9%; P(60d < −20%)=20.0% vs baseline 15.7%.
6. Does “the bigger the crash, the better the future return” appear true or false? False in this sample. More severe EXTREME_1D half median 60d=0.1% vs less severe 5.4%.
7. Do volatility and abnormal volume distinguish better vs worse capitulations? GOOD_60D N=17 median vol pctl=89.2, rel-vol pctl=48.9; BAD_60D N=16 median vol pctl=91.6, rel-vol pctl=86.3. Outcome labels only; no classifier.
8. Where does 2024-08-05 rank historically? 1d return -7.1% (pctl 2.9), 7d -19.1% (pctl 2.2), rel-volume pctl 99.9, 20d vol pctl 40.7 vs history through 2024-08-04.
9. Did 2024-08-05 look like an exceptional candidate entry using information that existed at the time? Using only pre-event information, 2024-08-05 was an extreme return day but did not meet CAPITULATION_PLUS_STRESS (volatility gate). It is a case study, not a template.
10. Does this evidence justify continuing toward a formal CAPITULATION ENTRY SETUP? **NO EDGE**

## Decision

**NO EDGE**

Research disposition only. This is not a validated trading signal. Macro is out of scope until a setup is economically meaningful. No thresholds were moved after seeing 2024-08-05.

