# Phase 6C — Limited macro walk-forward

Test whether **four frozen macro 12w changes, alone**, improve real-time
12-week crypto probability forecasts versus an expanding base rate.

**No crypto features. No feature search. No threshold tuning. No 2024–2026.**

This is not a trading backtest. It does not combine macro with crypto.

## Inputs (read-only)

- Phase 6A `macro_weekly.csv`
- Phase 3 `opportunity_episode_catalog.csv`

## Frozen spec

| item | value |
|---|---|
| features | `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` |
| M0 | expanding base rate of mature labels |
| M_MACRO | logistic L2, `C=1.0` |
| imputation / scale | train-window median, train-window `StandardScaler` |
| mature label | at t, train on `s <= t - 12` |
| min train N | 100 (not lowered for Bull) |

Primary target: `future_return_12w > 0`.  
Secondary: `> +20%`, `< -20%`.  
Bull check: primary target only, `state_direction == BULL`.

## Run

```bash
python3 src/run_macro_walkforward.py
```

## Outputs

- `results/macro_walkforward_metrics.csv`
- `results/MACRO_WALKFORWARD_ANALYSIS.md`
