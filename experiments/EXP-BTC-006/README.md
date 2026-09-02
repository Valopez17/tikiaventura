# EXP-BTC-006

Isolated two-arm robustness run for **EXT-C02** (E-02 lookback construction). Linked to **HYP-BTC-002** version 1. **Not a trading edge.** Does not reselect. Does not close E-02. Does not start EXT-C03, EXT-C04, Calendar, Breakout, or Vol.

| Piece | Path |
|---|---|
| Spec | `SPEC.md` |
| Src | `src/run_ext_c02.py` |
| Tests | `tests/test_ext_c02_isolation.py`, `tests/test_ext_c02_reproducibility.py` (repo root) |
| Frozen Top 10 | `research/market_state_observatory/trade_signal_research/strategy_lab/phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv` (read-only) |
| Dataset | `btc_tsmom_replication/btcusdt_1h.csv` |

Arms:

- A `LEGACY_POSITIONAL`: `close[i]/close[i-L]-1`
- B `EXACT_TIMESTAMP`: `close(t)/close(t-L hours)-1` if exact `t-L` exists; else ineligible

The only allowed difference is `lookback_mode`.

```
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --run-id RUN-BTC-006-<UTC-date>-01
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --verify --run-id RUN-BTC-006-<UTC-date>-01
```
