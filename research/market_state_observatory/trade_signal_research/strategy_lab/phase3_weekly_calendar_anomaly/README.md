# Phase 3 — Exhaustive weekly calendar anomaly search

Pure price + time. Not a live system. Not clean OOS.

Question: is there a recurring weekly BTC window (day + hour in
`America/New_York`) with an abnormal return **relative to other windows
with the same holding duration**?

This is not “which schedule made the most money.” BTC’s long-run drift
would favor long holds. The control is the same-week, same-duration median.

## Frozen design

- Binance BTCUSDT spot 1h (`btc_tsmom_replication/btcusdt_1h.csv`). No new download if that file is complete.
- Buy/sell at the **open** of the 1h candle whose open equals the NY civil hour.
- 168 entry slots × 167 future weekly exits = 28,056 candidates. Hours only. No shorts, no leverage, cash otherwise.
- Holding hours ∈ [1, 167]. At most one overlapping-free trade per week.
- Primary cost: **10 bps round trip**. Also 0 / 20 / 50 bps. Not optimized.
- Discovery: data start → 2021-12-31. Rank by **calendar-edge Sharpe** at 10 bps, among windows with mean net trade > 0 and N ≥ 150.
- Freeze top 20. Validation 2022–2024 and recent 2025→latest do **not** reselect.
- Full-history numbers are descriptive only.
- DST: nonexistent or ambiguous NY hours are skipped (`NaT`). No silent guess.

Because this project has already inspected recent BTC, later periods are
historical / temporal robustness, not a clean holdout.

## Run

```bash
python3 src/run_weekly_calendar_scan.py
```

## Outputs

- `results/ALL_WINDOWS_DISCOVERY.csv`
- `results/TOP_CANDIDATES.csv`
- `results/VALIDATION_RESULTS.csv`
- `results/CALENDAR_EDGE_MATRIX.csv`
- `results/TRADE_LOG_TOP_CANDIDATES.csv`
- `results/WEEKLY_CALENDAR_ANOMALY.md`
