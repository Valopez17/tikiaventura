# EXT-C03..C06 receipt — H1 L6 survivor audit

TASK_IDS: EXT-C03, EXT-C04, EXT-C05, EXT-C06  
ENDED: 2026-09-02  
OBJECTIVE: Using exact timestamps and without changing any rule parameter, is the historical evidence for frozen candidate `L6_down_p1_rebound_long_H6` strong and stable enough to justify freezing it for prospective observation, or should it be discarded / labeled insufficient?

Cursor reports mechanical disposition only. ChatGPT audits. Valita decides freeze/discard. This receipt does not claim that audit or that decision already happened.

This is not a strategy selection from 288 rules, not a confirmed edge, not clean OOS, and does not authorize capital. Real capital remains $0.

## Preconditions (verified at launch)

- start commit: `94ac3b265618b68380a9763c0a0511843b598225` (`origin/main`; unchanged at fetch)
- worktree clean at start
- EXP-BTC-007 absent from `experiments/` and `registries/experiments.jsonl`
- E-02 latest estado CLOSED
- dataset SHA-256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778`
- canonical EXT-C02 run: `RUN-BTC-006-20260902-03`
- HYP-BTC-002 remains INVALIDATED; no extra E-02 row

## Four commits (order is material)

1. EXT-C03 `36099f046511a586e56ed154777e29604b86ab33` — spec freeze only (`SPEC.md` + README). No numerical run.
2. EXT-C04 `54f78678902393033422f22397e39271b0b64680` — gate implementation + tests. No canonical run.
3. EXT-C05 `cf044946095da78a4f50720fdefa72412a3e814c` — hourly MTM, bootstrap, runner, tests, fixtures. **MANIFEST.CODE_COMMIT**.
4. EXT-C06 (this commit) — canonical run `RUN-BTC-007-20260902-01`, registries, STATUS, this receipt. Does not rewrite CODE_COMMIT.

Canonical run executed from the clean EXT-C05 commit.

## Provenance

- COMMIT EXT-C03: spec freeze only
- COMMIT EXT-C04: gate implementation + tests
- COMMIT EXT-C05 (CODE_COMMIT): `cf044946095da78a4f50720fdefa72412a3e814c` — runner, spec, tests, fixtures
- Canonical run: `RUN-BTC-007-20260902-01`
- MANIFEST.CODE_COMMIT equals EXT-C05 and contains runner/spec/tests/fixtures
- EXT-C06: this receipt, immutable run folder, registry appends, STATUS

## Done

- EXP-BTC-007 spec, gate, hourly MTM, stationary bootstrap, isolation tests, MTM tests
- Frozen identity asserted from Phase 4 TOP_CANDIDATES and EXP-BTC-006 RESULT.json (no reselection)
- `--verify` three-way hash agreement (checked-in vs manifest, recompute vs manifest, checked-in vs recompute); `canonical_run_unmodified` derived from hashes
- Registry appends: EXP-BTC-007, RUN-BTC-007-20260902-01, E-03 and E-04 as FIXED_PENDING_VERIFICATION
- STATUS: last closed Cursor package EXT-C03..C06 / H1 L6 audit; next none until Valita names a TASK-ID; EXT-H01/Valita decision pending; real capital $0

## Not done (out of scope)

- EXT-H01 ChatGPT audit (pending; not presented as done)
- Valita freeze/discard (pending; not presented as done)
- Closing E-03 or E-04
- Changing HYP-BTC-002 lifecycle or freeze status
- Extra E-02 row
- Dashboard / bot / live orders / capital

## Numeric truth (machine-generated)

Third-party commands (repo root):

```
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --run-id RUN-BTC-007-20260902-01
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --verify --run-id RUN-BTC-007-20260902-01
```

Canonical folder: `experiments/EXP-BTC-007/RUN-BTC-007-20260902-01/`

| Object | SHA-256 |
|---|---|
| Spec | `d90a1fc844cb966431723cae7966c28895d93bb853a797bfa340d6e109a5992d` |
| Dataset | `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103` |
| Rector v4.1 | `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778` |
| TRADES.csv | `eb1c54a5e7e390f5a7bb743497ac9c26f3c107971f6240402c0093cf4c09570e` |
| PERIOD_METRICS.csv | `2e99f85cbff25cd666e1db76485aa350f7837c54243698775baef8e4cf882f68` |
| YEARLY_METRICS.csv | `f5c7f6338446487899827d4c4d4f9712a61a21656246b23c0c6b9d6e7b17f6e9` |
| UNCERTAINTY.csv | `c051bd7b246b06e021407aa305c8c4a22b33587e5ae64bc46441a634c2261c0e` |
| RESULT.json | `d329ce9a11924f60c24b1b5e0ee1c4a3dd7cf9baed7ec492c11a2edc05f8a3db` |
| H1_L6_SURVIVOR_AUDIT.md | `17213428d598e923a9bbb03fb761596bb5c96033eaef042d8f97b67aa365437b` |
| unittest log | `5cc6658fbf8129c2fee4b66c7049018a35741c50d9378edae2b828625f33b3c2` |

Markdown never overrides CSV/JSON.

From RESULT.json (mechanical only; not a capital decision):

- mechanical_gate: PASS (separate from disposition)
- mechanical disposition: FREEZE_PROSPECTIVE_RECOMMENDED
- meaning of that disposition: freeze the exact rule and observe prospectively without capital; not a confirmed edge
- ChatGPT audit pending; Valita freeze/discard pending

## Tests (actual execution)

```
python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro tests.test_ext_c02_isolation tests.test_ext_c02_reproducibility tests.test_ext_c04_h1_gate tests.test_ext_c05_h1_mtm -v
```

- exit_code: 0
- passed: 101
- failed: 0
- skipped: 0
- log_sha256: `5cc6658fbf8129c2fee4b66c7049018a35741c50d9378edae2b828625f33b3c2`

```
python3 registries/validate_registries.py
```

OK 6 schemas.

## Mechanical notes

- Dataset file not rewritten
- Rector v4.1 file hash unchanged
- EXP-BTC-005/006 canonical runs and Phase 4 / 4b historical files not overwritten
- HYP-BTC-002 lifecycle unchanged (INVALIDATED)
- E-02: no extra row
- E-03 and E-04: FIXED_PENDING_VERIFICATION only; not CLOSED
