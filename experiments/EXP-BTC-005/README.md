# EXP-BTC-005

Reproducibility harness for R0-C (rector v4.1 §3.12). **Not a trading edge.** Does not scan Calendar, Extreme, Breakout, or Vol. Does not read the live 1h CSV.

| Piece | Path |
|---|---|
| Spec | `SPEC.md` |
| Src | `src/run_synthetic.py` |
| Tests | `tests/test_repro.py` (also loaded by `tests/test_r0c_synthetic_repro.py` at repo root) |
| Canonical run | `RUN-BTC-005-20260902-01/` |

Third-party command (from repo root):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
```
