# Phase 4b — Extreme-move audit fix

Read-only audit of frozen Phase 4 rules. Not a new search. Not a live
system. Not clean OOS.

Phase 4 files are not overwritten. The Phase 3 calendar candidate is
not used or modified. No new lookbacks, percentiles, or holds.

## What is corrected

1. **Exact-timestamp lookbacks.** `ret_L(t) = close(t)/close(t−L hours)−1` only when both timestamps exist. No positional `close[i]/close[i−L]`, no fill.
2. **Hourly mark-to-market equity.** Sharpe, vol, MaxDD, Calmar from the hourly path, including intra-trade losses. Trade-return Sharpe is diagnostic only.
3. **Stricter STRONG SURVIVOR rule**, including recent conditional advantage.

## Frozen candidate under decision

`L6_down_p1_rebound_long_H6` — exact 6h close-to-close ≤ expanding p1, LONG next hourly open, exit 6h later, 10 bps round trip.

## Run

```bash
python3 src/audit_extreme_move_candidates.py
```

## Outputs

- `results/OLD_VS_CORRECTED.csv`
- `results/CORRECTED_TOP10.csv`
- `results/CANDIDATE_V1_TRADES.csv`
- `results/CANDIDATE_V1_EQUITY.csv`
- `results/EXTREME_MOVE_AUDIT_FIX.md`
