# EXP-BTC-005

Reproducibility harness for R0-C (rector v4.1 §3.12). **Not a trading edge.** Does not scan Calendar, Extreme, Breakout, or Vol. Does not read the live 1h CSV.

| Piece | Path |
|---|---|
| Spec | `SPEC.md` |
| Src | `src/run_synthetic.py` |
| Tests | `tests/test_repro.py` (also loaded by `tests/test_r0c_synthetic_repro.py` at repo root) |
| Hash-contract reference run | `RUN-BTC-005-20260902-01/` (immutable historical incident; see E-23) |
| Provenance reproduction run | `RUN-BTC-005-20260902-02/` (CODE_COMMIT must contain this harness) |

Third-party command (from repo root). Default `--verify` still checks RUN-01 hashes and must stay green:

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify --run-id RUN-BTC-005-20260902-01
```

From a checkout of a run's `CODE_COMMIT` (no later run folder required):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --compute-hashes
```

Verify a later run without breaking RUN-01:

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify --run-id RUN-BTC-005-20260902-02
```
