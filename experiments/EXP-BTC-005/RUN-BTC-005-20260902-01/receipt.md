# Run receipt — RUN-BTC-005 harness

RUN_ID: RUN-BTC-005-20260902-01

DELTA / OBJETIVO VERIFICABLE: Prove v4.1 §3.12 on a tiny fixture. Not a strategy.

FILES CHANGED: this run folder only (spec/src live under EXP-BTC-005/).

COMMAND: `python3 experiments/EXP-BTC-005/src/run_synthetic.py --run-id RUN-BTC-005-20260902-01`

TEST RESULT: see registries/runs.jsonl and R0-C receipt after the unittest suite.

INPUT HASHES: tests/fixtures/e02_gap_hours.csv SHA-256 44f72413970da754428e887cfd068e26866f8e2058b17c4b42abab4b1350bffd
SPEC_HASH: b17c120b015632167b5663d603f757cff8d8c878410a8ff5b6c60b5514697ff4

OUTPUT HASHES:
- `outputs/SYNTHETIC_RETURNS.csv` SHA-256 `919a80c3148fbdbc13935871e7c67d8761bee29e8ecf939a92ca042c013e6bab`
- `outputs/SYNTHETIC_GAPS.csv` SHA-256 `e5b4a65c34225c36f052f1dfda0fccaefb4d6deb97018968edfbefa8db78cb79`
- `result/RESULT.json` SHA-256 `3199e508cc1a868d31bb28db453a206d11c572351c57d9f52dbc560da4c2c7e9`

PRIMARY METRICS: none (harness). Counts only: rows=6 gaps=1 duplicates=0 n_returns=5.

CONTROL RESULT: not applicable.

UNCERTAINTY: not applicable.

N/TRIALS: 1 predeclared harness.

MECHANICAL GATE: PASS

SPEC DEVIATIONS: none.

BLOCKERS: none for this harness. Live 1h CSV not used. E-02 economic impact not measured.

REGISTERS UPDATED: recorded separately in registries/runs.jsonl by R0-C.

not_a_trading_edge: true
