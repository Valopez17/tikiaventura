# EXT-H01 / EXT-H02 closeout — H1 audit and freeze

TASK_ID: EXT-C07  
Date: 2026-09-03  
Base: `85df43b57e3a87c5e95412cd7c70bc456e0924fb` (PR #4 merged)  
OBJECTIVE: Append-only record of EXT-H01 audit result and human decision EXT-H02. Governance closeout; not a new experiment.

This record does not claim a confirmed edge, does not authorize capital, does not change HYP-BTC-002, and does not modify the canonical run.

## ChatGPT audit (EXT-H01)

RESULT: PASS_WITH_NOTES.

Independent evidence recorded (this task did not re-run the 101 tests or `--verify`; it records what was independently verified):

- 101/101 tests passed.
- `run_h1_survivor_audit.py --verify` PASS.
- Zero discrepancies checked-in vs manifest vs recomputed.
- Hashes, CODE_COMMIT EXT-C05 `cf044946095da78a4f50720fdefa72412a3e814c`, and C05/C06 separation correct (EXT-C06 `5a54b9f7e020ecd744cda94cab415ec2cb43ec66`).
- Registries validated.

Canonical run `RUN-BTC-007-20260902-01` is untouched.

## Valita decision 2026-09-03 (EXT-H02)

- FREEZE_PROSPECTIVE.
- Exact rule: `L6_down_p1_rebound_long_H6`.
- Prospective observation only.
- Real capital: $0.

Limits (must remain visible):

- Not a confirmed edge.
- Not clean OOS.
- HYP-BTC-002 remains INVALIDATED.
- `registries/hypotheses.jsonl` is not modified.

## Audit note / E-24

- `RESULT.json` `mechanical_gate` is derived from only a subset of the 17 conditions in `SPEC.md`.
- All 17 conditions DID pass for the current run via independent evidence.
- The defect does not invalidate current numbers or the current disposition, but a future run could emit PASS without integrating all operational checks.
- Recorded as E-24 OPEN. Do not fix code and do not recalculate the run in EXT-C07.

## Registry closeout (append-only)

- DEC-017: R0-H01 approved (alert types + supported decisions; no result authorizes capital).
- DEC-018: Valita accepts FREEZE_PROSPECTIVE for `L6_down_p1_rebound_long_H6`, capital $0, without reviving HYP-BTC-002.
- E-18 CLOSED, E-03 CLOSED, E-04 CLOSED, E-24 OPEN.

## Next

- Next ChatGPT: write H2 SPEC "abnormal volume as incremental information after a price move".
- Next Cursor: none until ChatGPT provides and Valita approves the H2 SPEC.
