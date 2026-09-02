# Phase 5 — Breakout → continuation

Pure price. Not a live system. Not clean OOS.

Question: when BTC **closes above** the maximum **high** of a genuine
prior window, does price keep rising, and is that edge tradeable LONG
after costs?

Frozen and unused here:

1. `CALENDAR_CANDIDATE_V1` (Phase 3)
2. `CRASH_REBOUND_CANDIDATE_V1` (Phase 4b)

This scan is independent. Strategies are not combined.

## Frozen design

- Binance BTCUSDT spot 1h (`btc_tsmom_replication/btcusdt_1h.csv`). No download if that file exists.
- Lookback is a **timestamp window** `[t − L hours, t)`, not `L` positional rows. Current bar `t` is excluded from the prior high.
- Prior high = max **high** in that window. Breakout: `close_t > prior_high`.
- Complete expected hourly coverage is required: exactly `L` bars in the window. Missing bars → signal invalid. No fill.
- Lookbacks: 168h (7d), 720h (30d), 1440h (60d), 2160h (90d).
- Holds: 24h, 72h, 168h, 336h, 720h. Search space = 20 LONG rules.
- Entry: **open of bar t+1**. Exit: open exactly H hours after entry.
- Event study keeps every valid breakout. Executable PnL ignores new signals until the trade exits.
- Control: same-horizon unconditional BTC open-to-open return in the same period, among timestamps with complete lookback coverage.
- Primary cost: **10 bps round trip**. Also 0 / 20 / 50 bps. MTM splits the round trip across entry and exit.
- Primary Sharpe / MaxDD / vol / Calmar from **hourly mark-to-market** equity (`sqrt(365×24)`). Trade Sharpe is diagnostic only.
- Discovery: data start → 2021-12-31. Eligible if mean net > 0, breakout edge > 0, N ≥ 20. Rank by MTM Sharpe at 10 bps. Freeze at most top 5.
- Validation 2022–2024 and recent 2025→latest do **not** reselect.

Because this project has already inspected recent BTC, later periods are
historical / temporal robustness, not a clean holdout.

## Run

```bash
python3 src/run_breakout_continuation.py
```

## Outputs

- `results/ALL_BREAKOUT_RULES.csv`
- `results/TOP_CANDIDATES.csv`
- `results/VALIDATION_RESULTS.csv`
- `results/EVENT_PATHS.csv`
- `results/TRADE_LOG.csv`
- `results/EQUITY_TOP_CANDIDATES.csv`
- `results/BREAKOUT_CONTINUATION.md`
