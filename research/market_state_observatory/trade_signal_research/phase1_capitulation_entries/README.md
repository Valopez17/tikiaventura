# Phase 1 — Capitulation entry study

BTC only. Daily UTC closes. Event study, not a trading strategy.

Question: after an extreme selloff, is buying historically more attractive
than on an ordinary day?

## Frozen choices (not tuned)

- Expanding percentiles, min history 365 days, history strictly before t
- EXTREME_1D: daily return ≤ historical 5th percentile
- EXTREME_MULTI_DAY: 3d or 7d return ≤ historical 5th percentile
- CAPITULATION_PLUS_STRESS: (1D or multi-day) and 20d vol ≥ 80th percentile
- 7-calendar-day cooldown; keep the first event
- Primary statistical sample: event dates **before 2024-01-01**
- 2024-08-05 is a case study only; its thresholds use data through 2024-08-04

## Data

Binance BTCUSDT spot 1d UTC from 2017-08-17 (preferred).

Before Binance: trusted project splice
`btc_tsmom_replication/data/btcusd_daily.csv` (Bitstamp BTCUSD).

Do not change that price source. Volume is Binance BTC base volume from
listing date. Bitstamp CDD volume columns are inconsistent (BTC/USD swapped
in the early sample) and are not used.

## Run

```bash
python3 src/run_capitulation_entry_study.py
```

Needs network for Binance klines (and Bitstamp volume if CDD is up).

## Outputs

- `results/capitulation_events.csv`
- `results/CAPITULATION_ENTRY_STUDY.md`
