# Phase 1 — Simple strategy discovery

Executable BTC strategy research. Not a live system. Not clean OOS.

Question: did any of three frozen simple ideas make money after costs?

## Strategies (exactly three)

- **A.** BTC time-of-day / session anomaly — six fixed UTC 4-hour windows, long only, cash otherwise.
- **B.** Capitulation + deleveraging — frozen rule: 1d return ≤ expanding 5th percentile, `oi_change_1d ≤ -10%`, `perp_volume_rel_30d ≥ 2.0`. Holding periods 3/7/14/30/60d reported independently.
- **C.** Macro LONG / CASH — frozen four-feature candidate, weekly Friday decision, threshold 0.50, no short.

No new feature families. No threshold search. No session-boundary search. No leverage.

## Frozen choices

- Starting capital `$10,000`. No contributions. Cash earns 0.
- Primary cost: **10 bps round trip** per completed trade. Sensitivity at 0 and 20 bps. Not optimized.
- Strategy A window selection: first 70% of dates = discovery; freeze the best window; last 30% = temporal robustness. Not clean OOS.
- Strategy B overlapping signals: ignore until the current trade exits.
- Strategy C uses `MACRO_BASE_CANDIDATE_V1` features and walk-forward algorithm. Decision: `P(BTC 12w return > 0) ≥ 0.50` → LONG else CASH.
- 2024–2026 is **historical backtest / temporal robustness**, not a clean holdout.

## Data (existing project files)

- Hourly: `btc_tsmom_replication/btcusdt_1h.csv` (Binance BTCUSDT spot 1h).
- Daily BTC: same splice as Phase 1 (Bitstamp trusted file until 2017-08-16; Binance 1d after).
- Derivatives: Phase 3B `btc_derivatives_daily.csv`.
- Macro: Phase 6A frozen weekly file through 2023-12-29; 2024+ extended with the same four sources as Phase 6H.

## Run

```bash
python3 src/run_simple_strategy_discovery.py
```

Needs network only if the 2024+ macro extension is not already cached under `data/processed/`.

## Outputs

- `results/STRATEGY_SUMMARY.csv`
- `results/TRADE_LOG.csv`
- `results/EQUITY_CURVES.csv`
- `results/SIMPLE_STRATEGY_DISCOVERY.md`
