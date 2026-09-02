# EXT-C02 receipt

TASK_ID: EXT-C02  
ENDED: 2026-09-02  
OBJECTIVE: Isolated measurement of E-02 lookback construction. Holding everything else identical, how much do signals and economic results change when positional lookback is replaced by exact calendar-timestamp lookback?

This is not a strategy selection, not a capital decision, and not EXT-H01.

## Preconditions

- start commit: `9c1c9f61af3b326e4596a13cad329341ee4c2d4c` (`origin/main`; unchanged at fetch)
- worktree clean at start
- EXP-BTC-006 absent from `experiments/` and `registries/experiments.jsonl`
- dataset SHA-256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- rector SHA-256: `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778` (must remain unchanged)
- HYP-BTC-002 remains INVALIDATED; E-03 and E-04 remain OPEN; E-02 remains FIXED_PENDING_VERIFICATION

## Provenance

Two-commit flow (avoid E-23):

- COMMIT_A (executed code): `e46b0a9ad0574a199bf59855220014cd5ab8acc9`
- Canonical run: `RUN-BTC-006-20260902-03`
- MANIFEST.CODE_COMMIT equals COMMIT_A and contains runner, spec, and required tests/fixtures
- COMMIT_B: this receipt, immutable run folder, registry appends, STATUS

Unregistered local attempts before COMMIT_A was stable are not canonical and were not registered.

## Done

- EXP-BTC-006 spec, runner, isolation tests, reproducibility tests
- Two-arm scan of the frozen Phase 4 design (`lookback_mode` is the only allowed difference)
- Frozen Top 10 read from `phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv` (no reselection)
- `--verify` reproduced contracted output hashes
- Registry appends: EXP-BTC-006, RUN-BTC-006-20260902-03, new E-02 line (still FIXED_PENDING_VERIFICATION)
- STATUS: last closed Cursor task EXT-C02; next none until Valita names a TASK-ID

## Not done (out of scope)

- EXT-H01 ChatGPT audit (pending; not presented as done)
- EXT-C03 / EXT-C04, R1, Calendar, Breakout, Vol
- Closing E-02, E-03, E-04, E-12, E-18, E-19, E-20, or E-23
- Changing HYP-BTC-002 lifecycle
- Equity MTM as primary metric
- Survivor-gate rewrite or reclassification
- Reselecting or freezing a new candidate

## Numeric truth (machine-generated)

Third-party commands (repo root):

```
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --run-id RUN-BTC-006-20260902-03
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --verify --run-id RUN-BTC-006-20260902-03
```

Canonical folder: `experiments/EXP-BTC-006/RUN-BTC-006-20260902-03/`

| Object | SHA-256 |
|---|---|
| Spec | `039f0de9763fd5dbfb6dc57e603da21ebae09800ff857c32ed4415d9964aeddc` |
| Dataset | `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103` |
| SIGNAL_IMPACT.csv | `999fa511c0618d65eb922260a6c381ce45d7cc88d587e540c0718e799c86a906` |
| RULE_IMPACT.csv | `7747eedd255934b05dde0a93b259e927661974449d9e5479e162fbd8353e7d2d` |
| FROZEN_TOP10_IMPACT.csv | `54bf32da134e887f48528010eb72e3c055d5edae54fd42b38c95abdf4c5f0e1f` |
| RESULT.json | `1d5b137d84da8b2934620228a20197bdfba3b3fee9116bcca87684555a52608c` |
| EXT_C02_E02_IMPACT.md | `058e9e868d502190e90f09db2ea64288af219b9ab17defd93fea067c412161a9` |

Markdown never overrides CSV/JSON.

From RESULT.json (not a capital decision):

- materiality: MATERIAL (predeclared Phase 4b criterion applied to all signal cells and all frozen rules in Discovery/Validation)
- mechanical_gate: PASS (separate)
- L6_down_p1_rebound_long_H6 in this pipeline: Discovery N 63→62, mean net 1.580%→1.511% (not economic-material); Validation N 29→29, mean net unchanged 0.462%; Top 10 Discovery/Validation mean-net cells did not trip 0.002
- Frozen Top 10 validation sign changes: 0
- Validation sign changes across all 288 rules: 4 (reported; not a reselection)

Phase 4b mixed exact timestamp, survivor gate, and MTM. That mixed report does not substitute this isolated contrast.

## Mechanical notes

- Dataset file not rewritten
- Rector v4.1 file hash unchanged
- Phase 4 / Phase 4b historical files not overwritten
- HYP-BTC-002 lifecycle unchanged (INVALIDATED)
- E-02 not CLOSED; EXT-H01 still pending
