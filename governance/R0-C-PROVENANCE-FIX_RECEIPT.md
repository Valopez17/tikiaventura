# R0-C-PROVENANCE-FIX receipt

TASK_ID: R0-C-PROVENANCE-FIX  
ENDED: 2026-09-02  
OBJECTIVE: Register that RUN-BTC-005-20260902-01 MANIFEST.CODE_COMMIT does not contain executed harness code (E-23). Keep RUN-01 byte-identical. Execute a new synthetic reproduction run whose CODE_COMMIT is a commit that actually contains runner + SPEC + fixture.

## Commits (two-commit provenance; not inverted)

- COMMIT_A (code, before RUN-02 execution): `03306e70859b867750383d6e8c61950d5865e916`
- COMMIT_B (evidence): `9ee7dc402f36f396bf1f279d19ef54afe4a5767f`

COMMIT_A contains: `experiments/EXP-BTC-005/SPEC.md`, `experiments/EXP-BTC-005/src/run_synthetic.py`, `tests/fixtures/e02_gap_hours.csv`, preventive test `tests/test_r0c_code_commit_contains_harness.py`, reproduction test `tests/test_r0c_commit_a_repro.py`, and E-23. COMMIT_A does not contain RUN-02 outputs.

HEAD at RUN-02 execution: `03306e70859b867750383d6e8c61950d5865e916` (equals COMMIT_A).  
RUN-02 MANIFEST.CODE_COMMIT: `03306e70859b867750383d6e8c61950d5865e916`

## RUN-01 unchanged (must remain byte-identical)

| Object | Path | SHA-256 |
|---|---|---|
| Manifest | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/MANIFEST.json` | `ac9c52874e91121b678f88c30a483e025a5a38a956662098a2e5f585ae469097` |
| Returns | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/outputs/SYNTHETIC_RETURNS.csv` | `919a80c3148fbdbc13935871e7c67d8761bee29e8ecf939a92ca042c013e6bab` |
| Gaps | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/outputs/SYNTHETIC_GAPS.csv` | `e5b4a65c34225c36f052f1dfda0fccaefb4d6deb97018968edfbefa8db78cb79` |
| Result | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/result/RESULT.json` | `3199e508cc1a868d31bb28db453a206d11c572351c57d9f52dbc560da4c2c7e9` |

RUN-01 CODE_COMMIT remains `426ca78062aaf600076182d6dab6daf98e200472` (historical incident; grandfathered via E-23).

## RUN-02 (numeric truth)

Same scientific question as the harness: reproduce output hashes from spec + fixture bytes + one command. Live 1h CSV not used. `not_a_trading_edge`. Results were not changed to obtain PASS; hash-contract files match RUN-01.

Materialize (executed from COMMIT_A):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --run-id RUN-BTC-005-20260902-02
```

Third-party verify (final tree; does not break RUN-01 `--verify`):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify --run-id RUN-BTC-005-20260902-02
```

Reproduction from a clean checkout of COMMIT_A (no RUN-02 folder required):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --compute-hashes
```

| Object | Path | SHA-256 |
|---|---|---|
| Spec | `experiments/EXP-BTC-005/SPEC.md` | `b17c120b015632167b5663d603f757cff8d8c878410a8ff5b6c60b5514697ff4` |
| Fixture | `tests/fixtures/e02_gap_hours.csv` | `44f72413970da754428e887cfd068e26866f8e2058b17c4b42abab4b1350bffd` |
| Manifest | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-02/MANIFEST.json` | `0fe649af2a9fa3a646d35d067cddc268a5f1768cc042d79b3333b8113d09a7ec` |
| Returns | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-02/outputs/SYNTHETIC_RETURNS.csv` | `919a80c3148fbdbc13935871e7c67d8761bee29e8ecf939a92ca042c013e6bab` |
| Gaps | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-02/outputs/SYNTHETIC_GAPS.csv` | `e5b4a65c34225c36f052f1dfda0fccaefb4d6deb97018968edfbefa8db78cb79` |
| Result | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-02/result/RESULT.json` | `3199e508cc1a868d31bb28db453a206d11c572351c57d9f52dbc560da4c2c7e9` |

MECHANICAL_GATE: PASS. RANDOM_SEED: none.

Expected vs observed hash-contract (RUN-02 vs RUN-01 / `--compute-hashes`): identical for the three contract files.

## Commands / tests

```
python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro -v
python3 registries/validate_registries.py
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify --run-id RUN-BTC-005-20260902-01
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify --run-id RUN-BTC-005-20260902-02
python3 experiments/EXP-BTC-005/src/run_synthetic.py --compute-hashes
```

New test path: `tests/test_r0c_code_commit_contains_harness.py`  
Reproduction-from-COMMIT_A test: `tests/test_r0c_commit_a_repro.py`

## Unchanged rector / live 1h

- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778`
- live 1h CSV SHA-256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`

## Errors

- New error_id: **E-23** (append-only). MANIFEST.CODE_COMMIT does not contain executed harness code. Affected run: RUN-BTC-005-20260902-01. E-12 left as-is.
- RUN-01 grandfathered via E-23 so the suite does not fail solely on the known incident. New runs are not grandfathered.

## Not done

- R1, EXT-C02, any Calendar / Extreme / Breakout / Vol rerun or scan
- Rewriting RUN-01
- Closing E-02 economic impact, E-18, E-19, DEC-007, E-12 (strategy manifests still absent)
- Moving or rewriting `btc_tsmom_replication/btcusdt_1h.csv`
- Experiment-tracking platform
- Changing scientific outputs to obtain PASS
