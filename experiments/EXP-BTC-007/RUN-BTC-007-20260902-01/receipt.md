# Run receipt — EXP-BTC-007 / H1 L6 survivor audit

RUN_ID: RUN-BTC-007-20260902-01
CODE_COMMIT (EXT-C05): `cf044946095da78a4f50720fdefa72412a3e814c`
COMMAND: `python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --run-id RUN-BTC-007-20260902-01`
mechanical_gate: PASS
disposition: FREEZE_PROSPECTIVE_RECOMMENDED

Cursor reports mechanical disposition only. ChatGPT audit pending. Valita freeze/discard pending.
Not a trading edge. Not clean OOS. Does not authorize capital. HYP-BTC-002 remains INVALIDATED.

## Hashes

- spec: `d90a1fc844cb966431723cae7966c28895d93bb853a797bfa340d6e109a5992d`
- dataset: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- outputs/TRADES.csv: `eb1c54a5e7e390f5a7bb743497ac9c26f3c107971f6240402c0093cf4c09570e`
- outputs/PERIOD_METRICS.csv: `2e99f85cbff25cd666e1db76485aa350f7837c54243698775baef8e4cf882f68`
- outputs/YEARLY_METRICS.csv: `f5c7f6338446487899827d4c4d4f9712a61a21656246b23c0c6b9d6e7b17f6e9`
- outputs/UNCERTAINTY.csv: `c051bd7b246b06e021407aa305c8c4a22b33587e5ae64bc46441a634c2261c0e`
- result/RESULT.json: `d329ce9a11924f60c24b1b5e0ee1c4a3dd7cf9baed7ec492c11a2edc05f8a3db`
- report/H1_L6_SURVIVOR_AUDIT.md: `17213428d598e923a9bbb03fb761596bb5c96033eaef042d8f97b67aa365437b`

## Tests (actual execution, not a command string alone)

- command: `python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro tests.test_ext_c02_isolation tests.test_ext_c02_reproducibility tests.test_ext_c04_h1_gate tests.test_ext_c05_h1_mtm -v`
- exit_code: 0
- passed: 101
- failed: 0
- skipped: 0
- log_sha256: `5cc6658fbf8129c2fee4b66c7049018a35741c50d9378edae2b828625f33b3c2`

Markdown never overrides CSV/JSON.
