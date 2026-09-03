# EXP-BTC-007

H1 final survivor audit of the **frozen** candidate `L6_down_p1_rebound_long_H6`. Linked to **HYP-BTC-002** version 1. Type `ROBUSTNESS`. Role `FIXED_CANDIDATE_SURVIVOR_AUDIT`.

Not a trading edge. Not clean OOS. Does not authorize capital. Does not reselect from 288 rules. Does not change HYP-BTC-002 lifecycle (remains INVALIDATED). E-02 stays CLOSED (no extra row). E-03 and E-04 may move only to `FIXED_PENDING_VERIFICATION`. ChatGPT audit and Valita freeze/discard are pending; this folder does not claim they happened.

| Piece | Path |
|---|---|
| Spec | `SPEC.md` |
| Src | `src/run_h1_survivor_audit.py` (EXT-C05; absent in EXT-C03) |
| Tests | `tests/test_ext_c04_h1_gate.py`, `tests/test_ext_c05_h1_mtm.py` (repo root; added in later commits) |
| Frozen identity | Phase 4 `TOP_CANDIDATES.csv` + EXP-BTC-006 `RESULT.json` (read-only) |
| Dataset | `btc_tsmom_replication/btcusdt_1h.csv` |

Allowed mechanical dispositions: `DISCARD` | `INSUFFICIENT` | `FREEZE_PROSPECTIVE_RECOMMENDED`.

```
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --run-id RUN-BTC-007-<UTC-date>-01
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --verify --run-id RUN-BTC-007-<UTC-date>-01
```
