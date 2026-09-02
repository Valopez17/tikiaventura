# Phase 4 — Extreme move: rebound vs continuation

Pure price. Not a live system. Not clean OOS.

Question: after an unusually large BTC move, does price reverse or
continue, at which horizon, and is any effect tradeable after costs?

The Phase 3 weekly calendar candidate is frozen and is not used here.
This scan is independent. Strategies are not combined.

## Frozen design

- Binance BTCUSDT spot 1h (`btc_tsmom_replication/btcusdt_1h.csv`). No new download if that file is complete.
- Trailing returns at the **close** of bar `t` over **6 / 12 / 24 / 72** hours.
- Extremes vs **expanding** historical percentiles using only `s < t`. Minimum history: 365 calendar days. No full-sample quantiles.
- Downside: ≤ 1st / 2.5th / 5th percentile. Upside: ≥ 95th / 97.5th / 99th.
- Entry: **open of bar t+1**. Exit: open exactly H hours after entry. H ∈ {6, 12, 24, 48, 72, 168}. Missing exit bar → skip the event.
- After crashes: LONG rebound and SHORT continuation. After rallies: LONG continuation and SHORT reversal.
- Shorts are unlevered `entry/exit − 1` and theoretical (no borrow/funding).
- Event study (all signals) and executable non-overlapping trades. Economic metrics use the non-overlapping version.
- Control: same-horizon unconditional BTC open-to-open returns in the same period.
- Primary cost: **10 bps round trip**. Also 0 / 20 / 50 bps. Shorts use the same fee for comparability only.
- Discovery: data start → 2021-12-31. Rank executable 10 bps Sharpe among rules with mean net > 0 and N ≥ 30.
- Freeze top 10. Validation 2022–2024 and recent 2025→latest do **not** reselect.

Because this project has already inspected recent BTC, later periods are
historical / temporal robustness, not a clean holdout.

## Run

```bash
python3 src/run_extreme_move_scan.py
```

## Outputs

- `results/ALL_EXTREME_RULES.csv`
- `results/TOP_CANDIDATES.csv`
- `results/VALIDATION_RESULTS.csv`
- `results/EVENT_PATHS.csv`
- `results/TRADE_LOG.csv`
- `results/EXTREME_MOVE_REVERSAL.md`
