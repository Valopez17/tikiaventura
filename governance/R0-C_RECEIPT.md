# R0-C receipt

TASK_ID: R0-C  
ENDED: 2026-09-02  
OBJECTIVE: Minimum manifest, minimum receipt, reproducible synthetic run; legacy evidence referenced by IDs/links without recalculating.

## Preconditions

- start commit: `426ca78062aaf600076182d6dab6daf98e200472` (R0-B-AUDIT-FIX)
- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778` (must remain unchanged)

## Done

- Synthetic harness EXP-BTC-005 / RUN-BTC-005-20260902-01 exists (not a strategy scan).
- Machine-generated run manifest covers Appendix C fields that exist.
- Canonical run receipt exists at `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/receipt.md`.
- Third-party command reproduces output hashes (`--verify`).
- Calendar, Extreme, Breakout, Vol have HYP/EXP IDs pointing at live paths (or NOT FOUND) + rector §5. Classifications copied as labels only.
- E-12 superseded to FIXED_PENDING_VERIFICATION (harness only; legacy strategy runs still lack manifests).

## Not done (out of scope)

- R1, EXT-C02, any Calendar / Extreme / Breakout / Vol rerun
- Wiring `temporal/exact_timestamp.py` into strategy_lab
- Closing E-02 economic impact, E-18, E-19, DEC-007
- Moving or rewriting `btc_tsmom_replication/btcusdt_1h.csv`
- Inventing historical RUN-IDs or Vol artefacts
- Experiment-tracking platform, database, dashboard, orchestration, agents, alerts, queues, ML, multi-coin

## Synthetic run (numeric truth)

Third-party command (repo root):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
```

| Object | Path | SHA-256 |
|---|---|---|
| Spec | `experiments/EXP-BTC-005/SPEC.md` | `b17c120b015632167b5663d603f757cff8d8c878410a8ff5b6c60b5514697ff4` |
| Fixture | `tests/fixtures/e02_gap_hours.csv` | `44f72413970da754428e887cfd068e26866f8e2058b17c4b42abab4b1350bffd` |
| Returns | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/outputs/SYNTHETIC_RETURNS.csv` | `919a80c3148fbdbc13935871e7c67d8761bee29e8ecf939a92ca042c013e6bab` |
| Gaps | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/outputs/SYNTHETIC_GAPS.csv` | `e5b4a65c34225c36f052f1dfda0fccaefb4d6deb97018968edfbefa8db78cb79` |
| Result | `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/result/RESULT.json` | `3199e508cc1a868d31bb28db453a206d11c572351c57d9f52dbc560da4c2c7e9` |

Manifest (wall-clock / environment; not in the hash contract): `experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/MANIFEST.json`

CODE_COMMIT recorded in that manifest is `426ca78062aaf600076182d6dab6daf98e200472` (HEAD when the canonical run was materialized; harness files were then uncommitted). Output hashes do not depend on CODE_COMMIT.

MECHANICAL_GATE: PASS. RANDOM_SEED: none. Live 1h CSV not read.

## Legacy IDs (labels only)

| ID | Points to | Classification (v4.1 §5, unchanged) |
|---|---|---|
| HYP-BTC-001 / EXP-BTC-001 | `research/market_state_observatory/trade_signal_research/strategy_lab/phase3_weekly_calendar_anomaly/` + §5.1 | L2 CALCULATED; DEEPEN_METHOD / UNFROZEN; selection_contaminated |
| HYP-BTC-002 / EXP-BTC-002 | `.../phase4_extreme_move_reversal/` and `.../phase4b_extreme_move_audit_fix/` + §5.2 | L2 CALCULATED, afectado; INVALIDATED |
| HYP-BTC-003 / EXP-BTC-003 | `.../phase5_breakout_continuation/` + §5.3 | L0 IDEA / spec draft; BACKLOG; not authorized; artefacts not promoted |
| HYP-BTC-004 / EXP-BTC-004 | no implementation folder (NOT FOUND) + §5.4 | L0 IDEA / spec draft; BACKLOG |
| HYP-BTC-005 / EXP-BTC-005 / RUN-BTC-005-20260902-01 | `experiments/EXP-BTC-005/` + §3.12 | reproducibility harness; not a trading edge; not L5 |

No historical RUN-IDs invented for the four families. No numbers copied into new result CSVs.

## Tests

```
python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids -v
python3 registries/validate_registries.py
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
```

Existing 25 tests must remain OK. New tests cover the hash contract and legacy ID labels.

## Mechanical notes

- No backtest executed.
- No dataset modified.
- No historical figure recalculated.
- v4.1 file hash unchanged (verify after the task).
- Breakout artefacts exist on disk; classification remains L0.
- Vol remains NOT FOUND.
- E-02 primitive still not wired into strategy_lab.
- DATA_AUDIT remains PASS; live 1h SHA-256 `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`.

## Errors

- E-12: harness manifest exists; superseded to FIXED_PENDING_VERIFICATION. Not CLOSED (legacy strategy provenance still absent).
- E-02 economic impact: not closed.
- E-18, E-19, DEC-007: not closed.
