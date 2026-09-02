# EXP-BTC-005 — Reproducibility harness (not a strategy)

EXPERIMENT_ID: EXP-BTC-005  
HYPOTHESIS_ID/VERSION: HYP-BTC-005 / 1  
EXPERIMENT_TYPE: REPRODUCTION  
SPEC_STATUS: APPROVED for R0-C  
ROLE: REPRODUCIBILITY_HARNESS  
NOT_A_TRADING_EDGE: true  
EVIDENCE CLAIM: none for economic utility; no L5; no Calendar/Extreme/Breakout/Vol scan

This spec exists to prove rector v4.1 §3.12 on a tiny deterministic fixture. It is not a trading-edge hypothesis.

## Pregunta

Can a third party identify this spec, identify the same data bytes, run one command, and obtain the same output hashes (byte-identical; no numeric tolerance)?

## Signal / entry / exit / side / search space

None. No positions, no ranking, no scan.

## Dataset

- DATA_PATH: `tests/fixtures/e02_gap_hours.csv` (existing E-02 fixture; not the live 1h dataset)
- DATA_SHA256: `44f72413970da754428e887cfd068e26866f8e2058b17c4b42abab4b1350bffd`
- Do not read `btc_tsmom_replication/btcusdt_1h.csv`.
- Do not impute, fill, or rewrite the fixture.

## Procedure (frozen)

1. Identify this file as the spec. Hash its bytes (SHA-256).
2. Identify the fixture bytes. SHA-256 must equal DATA_SHA256. If not, MECHANICAL_GATE = FAIL and stop.
3. Parse `timestamp_utc` as naive UTC `YYYY-MM-DD HH:MM:SS`. Parse `close` as base-10 float.
4. Count input rows (header excluded). Expected: 6.
5. Count duplicate timestamps. Expected: 0.
6. Build the inclusive hourly grid from min timestamp to max timestamp. List missing hours. Expected: 1 missing hour (`2020-01-01 03:00:00`), 1 gap run.
7. For each pair of consecutive *present* bars (no fill), emit `elapsed_hours` and `simple_return = close_curr / close_prev - 1` formatted to 12 decimal places (Python `f"{x:.12f}"`).
8. Write outputs with Unix newlines (`\n`). JSON: `indent=2`, `sort_keys=True`, `ensure_ascii=True`, trailing newline.

## RANDOM_SEED

None. Fully deterministic. No RNG.

## Cost / boundaries / N floor / ranking / selection-bias method

Not applicable (n_trials = 1 predeclared harness; no rule, no search).

## Metrics

Row counts, gap counts, duplicate counts, and SHA-256 of output files. No economic metrics.

## Mechanical gates

PASS only if all hold:

- fixture SHA-256 equals DATA_SHA256
- input_rows = 6
- duplicates = 0
- gaps = 1
- missing hour list is exactly `2020-01-01 03:00:00`
- output files are written
- on `--verify`: SHA-256 of `SYNTHETIC_RETURNS.csv`, `SYNTHETIC_GAPS.csv`, and `RESULT.json` equal the canonical run

FAIL otherwise. No tolerance.

## Outputs (byte-identical contract)

Inside the run folder:

- `outputs/SYNTHETIC_RETURNS.csv`
- `outputs/SYNTHETIC_GAPS.csv`
- `result/RESULT.json`

Wall-clock times, `CODE_COMMIT`, and `ENVIRONMENT` live in `MANIFEST.json` / `receipt.md` and **may differ** across machines. They are not part of the hash contract.

## Canonical run (reference hashes)

`experiments/EXP-BTC-005/RUN-BTC-005-20260902-01/`

Expected output SHA-256 values are those recorded in that run’s `MANIFEST.json` field `OUTPUT_FILES` (machine-generated). Markdown never overrides them.

## Third-party command

From the repository root:

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --verify
```

This recomputes outputs in a temporary directory and compares SHA-256 to the canonical run. Exit code 0 means hashes match.

To write a *new* run folder (never overwrite):

```
python3 experiments/EXP-BTC-005/src/run_synthetic.py --run-id RUN-BTC-005-<UTC-date>-<nn>
```

## Stop conditions

- would require reading or rewriting the live 1h CSV
- would require running strategy_lab or scanning Calendar / Extreme / Breakout / Vol
- would require a numeric tolerance, RNG, or network

## Approved

R0-C named by Valita. Harness only.
