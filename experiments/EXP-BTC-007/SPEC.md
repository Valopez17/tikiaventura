# EXP-BTC-007 — H1 final survivor audit of frozen candidate L6_down_p1_rebound_long_H6

EXPERIMENT_ID: EXP-BTC-007  
HYPOTHESIS_ID/VERSION: HYP-BTC-002 / 1  
EXPERIMENT_TYPE: ROBUSTNESS  
ROLE: FIXED_CANDIDATE_SURVIVOR_AUDIT  
SPEC_STATUS: APPROVED for EXT-C03..C06  
TASK_IDS: EXT-C03 (this spec), EXT-C04 (gate implementation/tests), EXT-C05 (hourly MTM + uncertainty; CODE_COMMIT), EXT-C06 (canonical run, evidence, PR; do not merge)  
NOT_A_TRADING_EDGE: true  
DOES_NOT_AUTHORIZE_CAPITAL: true  
NOT_CLEAN_OOS: true  
HYP-BTC-002 lifecycle: remains INVALIDATED (this spec does not change it; freeze_status remains UNFROZEN until Valita decides)  
E-02 estado: remains CLOSED (do not append another E-02 row)  
E-03 estado: may advance only to FIXED_PENDING_VERIFICATION; do not mark CLOSED  
E-04 estado: may advance only to FIXED_PENDING_VERIFICATION; do not mark CLOSED  
EXT-H01 ChatGPT audit: pending; not executed here  
Valita freeze/discard decision: pending; not executed here  

Cursor reports mechanical disposition only. ChatGPT audits. Valita decides freeze/discard. This spec does not claim that either has already happened.

This spec freezes one candidate and one decision gate. It is not a new search, not a reselection from 288 rules, not a parameter sweep, not capital authorization, and not a claim of confirmed edge or clean OOS.

## Pregunta

Using exact timestamps and without changing any rule parameter, is the historical evidence strong and stable enough to justify freezing this candidate for prospective observation, or should it be discarded / labeled insufficient?

Allowed mechanical dispositions only:

- `DISCARD`
- `INSUFFICIENT`
- `FREEZE_PROSPECTIVE_RECOMMENDED`

`FREEZE_PROSPECTIVE_RECOMMENDED` means only: freeze the exact rule and observe prospectively without capital. It is not a confirmed edge, not clean OOS, and does not authorize capital.

## Frozen candidate (no degrees of freedom)

Identity is read from existing artefacts and asserted equal to this spec. Do not reselect from 288 rules.

Source artefacts (read-only):

- `research/market_state_observatory/trade_signal_research/strategy_lab/phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv` (Phase 4 frozen Top 10; discovery rank 2)
- `experiments/EXP-BTC-006/RUN-BTC-006-20260902-03/result/RESULT.json` field `l6_candidate_summary.rule_id` (canonical EXT-C02)

Frozen identity (must match those artefacts and this table):

| Field | Frozen value |
|---|---|
| `rule_id` | `L6_down_p1_rebound_long_H6` |
| asset / data | existing Binance BTCUSDT Spot 1h file only (`btc_tsmom_replication/btcusdt_1h.csv`) |
| lookback | 6 calendar hours |
| tail | down |
| percentile | 0.01 (label `p1`) |
| direction | LONG |
| thesis | rebound |
| hold | 6 calendar hours |
| lookback_mode | `EXACT_TIMESTAMP` only |

Signal / trade construction (frozen):

- Signal timestamp: close of bar `t`.
- Trailing return: `close(t) / close(t − 6 exact calendar hours) − 1`.
- Missing exact `t−6h`: ineligible. No nearest bar, fill, interpolation, or substitution.
- Semantics: reuse `temporal/exact_timestamp.py` (`lookup_exact` / `DatetimeIndex.get_indexer`). Vectorized behind-index must agree with that primitive.
- Threshold: lower expanding 1st percentile of finite trailing returns with timestamp strictly before `t`.
- Expanding interpolation: NumPy `quantile` linear equivalent (Fenwick k-th as in audited EXP-BTC-006 / Phase 4).
- Minimum history: 365 calendar days from the first valid trailing return. Before that, no signal.
- Direction: LONG rebound only.
- Entry: open at exact `t+1h`. Missing entry bar: skip the event (no fill).
- Exit: open exactly 6 calendar hours after entry. Missing exit bar: skip the event (no fill).
- Non-overlap: ignore a new signal while a trade is active. Entry exactly at the previous exit timestamp is allowed (`entry_ts < busy_until` blocks; `entry_ts == busy_until` does not).
- Unconditional same-horizon control: every hour in the same period with a valid same-horizon next-open to exit-open return.
- Conditional same-horizon return: eligible events (signal + entry + exit present, finite forward return) in that period.
- Conditional advantage: conditional mean − unconditional mean.

Do not add thresholds, filters, regimes, volume, vol scaling, derivatives, indicators, lookbacks, holds, models, or alternative entries/exits.

## Dataset

- DATA_PATH: `btc_tsmom_replication/btcusdt_1h.csv`
- DATA_SHA256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- Do not change, move, or redownload the file.
- Do not impute missing hours.
- Rector v4.1 SHA-256 must remain `799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778`.

## Splits (frozen)

Period is the calendar timestamp of the **signal** bar `t`.

- Discovery: dataset start through `2021-12-31` (signal `t < 2022-01-01T00:00:00+00:00`)
- Validation: `2022-01-01` through `2024-12-31` (signal `2022-01-01T00:00:00+00:00 <= t < 2025-01-01T00:00:00+00:00`)
- Recent: `2025-01-01` through latest complete bar in the dataset (`t >= 2025-01-01T00:00:00+00:00`)
- Full: all signals in the dataset after minimum history

Period metrics use trades whose **signal** belongs to that period and include their full predeclared 6h holding path (a Validation signal whose hold crosses into 2025 still belongs to Validation, and its intra-hold marks after the boundary are included in Validation MTM).

Compare DatetimeIndex values as timestamps, not mixed-unit `asi8` vs `Timestamp.value`.

## Costs (frozen)

Primary round-trip cost: 10 bps (`fee = 0.0010`).

Sensitivities (report all; do not retune): 0 bps, 20 bps, 50 bps.

Trade net: `net = (1 + gross) * (1 - fee) - 1`.

Hourly MTM fee algebra: split the round-trip fee across entry and exit so `entry_mult * exit_mult = (1 - fee_rt)`. For `fee_rt <= 0`, both multipliers are 1. For `0 < fee_rt < 1`, each side is `sqrt(1 - fee_rt)`. For `fee_rt >= 1`, each side is 0.

50 bps is stress only, not a hard gate.

Ending capital from $10,000 is illustration only. It is not a utility weight and does not authorize capital.

## Hourly MTM (frozen; implemented EXT-C05)

Primary path metrics come from hourly mark-to-market, not from concatenating trade returns.

- Fills at the entry open.
- Mark an open position with the hourly close.
- Exit at the exact exit open.
- Hourly returns are zero while flat.
- Intra-trade losses enter MaxDD.
- Annualization: `sqrt(365 * 24)` on hourly returns.
- Crypto year length for CAGR / trade-Sharpe span: 365 days.
- Start capital for the illustration path: $10,000.
- Do not commit another 9+ MB hourly equity CSV. Recompute deterministically. Commit compact trade / period / yearly / uncertainty outputs.
- Tests must prove MTM on a small fixture with an intra-trade drawdown that trade-only equity misses.

Reuse the audited Phase 4b MTM algebra (`mtm_from_trades` / `side_mult` / hourly marks) as a reference. Do not copy the 1600-line EXT-C02 288-rule runner. Prefer importing audited pure functions from EXP-BTC-006 (`behind_indices`, `expanding_quantiles`, `executable_take`, `hours_ahead_index`, exact-timestamp agreement) for the fixed candidate only.

## Uncertainty (frozen before results; implemented EXT-C05)

Input: chronological non-overlapping **net** trade returns at 10 bps, separately by period.

Method: Politis–Romano stationary bootstrap.

- Expected block length: 5 trades (`p = 1/5` geometric continuation).
- Replications: 10,000.
- Seed: 0 (`numpy.random.default_rng(0)`).
- Wrap-around (circular) index arithmetic.
- Report 90% and 95% percentile intervals for mean net, and `Pr(mean_net > 0)`.
- If `N < 5`: return `INSUFFICIENT_N`. Do not fabricate an interval.
- Diagnostic only. Not a license to tune.

## Metrics (Discovery, Validation, Recent, Full)

For each period:

- N signals, N eligible events, N non-overlapping trades
- N skip missing entry, N skip missing exit
- mean / median gross; mean / median net at 0 / 10 / 20 / 50 bps
- win rate (fraction of trades with net_10bps > 0)
- profit factor on net_10bps (sum of wins / abs(sum of losses); `inf` if losses are 0 and wins > 0)
- conditional same-horizon return, unconditional same-horizon control, conditional advantage
- trade-return Sharpe (diagnostic only; not a gate input except as reported)
- hourly MTM: total return, annualized vol, Sharpe, MaxDD, Calmar, exposure
- ending capital from $10,000 (trade-path illustration and MTM path; illustration only)
- MTM results at 0 / 10 / 20 / 50 bps (end cap / total return / Sharpe / MaxDD)

Annual table (calendar year of the **signal**):

- N trades
- mean net at 10 bps
- MTM return of that year's signal-trades (full 6h paths)
- yearly PnL = `prod(1 + net_10bps) - 1`
- contribution to positive cumulative PnL = that year's positive PnL / sum of positive yearly PnL (0 if the year is non-positive)
- frequency per calendar year = N trades that year

Also report the largest winning trade net and the largest losing trade net (10 bps), with each as a share of the sum of positive / negative trade nets.

Report MaxDD without inventing a risk-tolerance threshold Valita has not supplied.

## Predeclared decision gate (do not change after seeing results)

Evaluate on the metrics defined above. Mechanical disposition is not a scientific confirmation.

### Hard fail → `DISCARD` if any of:

1. Discovery mean net at 10 bps `<= 0` (or non-finite)
2. Discovery conditional advantage `<= 0` (or non-finite)
3. Validation mean net at 10 bps `<= 0` (or non-finite)
4. Validation conditional advantage `<= 0` (or non-finite)
5. Validation hourly MTM Sharpe non-finite or `<= 0`
6. Validation `< 15` trades
7. Recent has `>= 5` trades AND any of {mean net 10 bps, conditional advantage, MTM Sharpe} is `< 0`

### `FREEZE_PROSPECTIVE_RECOMMENDED` only if no hard fail AND all of:

1. Validation mean net `> 0` at 20 bps
2. Validation stationary-bootstrap `Pr(mean_net_10bps > 0) >= 0.80` (a `INSUFFICIENT_N` status fails this clause)
3. Recent `>= 5` trades AND mean net 10 bps, conditional advantage, and MTM Sharpe are all `>= 0` (and finite)
4. At least two calendar years with positive mean net (10 bps)
5. At least one positive-mean-net year outside `{2020, 2021, 2022}`
6. Largest positive year contributes `< 70%` of total positive yearly PnL, where yearly PnL = `prod(1 + net_10bps) - 1` and the share uses `max(clip(yearly_pnl, 0, None)) / sum(clip(yearly_pnl, 0, None))`

This means only: freeze the exact rule and observe prospectively without capital. Not confirmed edge.

### Otherwise `INSUFFICIENT`

50 bps is stress only, not a hard gate.

## Decision utility declaration (frozen)

- Horizon: 6 hours after entry.
- Reaction window: the next exact hourly open only.
- Frequency: measured by period and by calendar year; no frequency optimization.
- False-alarm cost: a realized losing 6h trade plus friction and adverse excursion (MTM intra-trade loss).
- Omission cost: a foregone positive net after an eligible event.
- No invented utility weights.
- Falsifier: any hard-fail condition, or failure to achieve the freeze clauses (stable retrospective evidence under this predeclared gate).
- Not a license to add parameters after seeing numbers.

## Mechanical gates (PASS / FAIL / BLOCKED)

Mechanical_gate is separate from `DISCARD` / `INSUFFICIENT` / `FREEZE_PROSPECTIVE_RECOMMENDED`. Do not alter scientific results to obtain PASS.

PASS only if all hold:

1. Dataset SHA-256 equals DATA_SHA256.
2. Rector v4.1 SHA-256 unchanged (`799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778`).
3. Fixed rule identity matches the frozen candidate in this spec and in the Phase 4 / EXP-BTC-006 artefacts.
4. Exact timestamps and missing-bar behaviour are tested; missing `t−6h` is ineligible.
5. No reselection and no parameter freedom (only `L6_down_p1_rebound_long_H6`).
6. Entry / exit and non-overlap are tested (including entry allowed exactly at previous exit).
7. Fee algebra is tested for all four costs (0 / 10 / 20 / 50 bps); MTM side multipliers multiply to `1 - fee_rt`.
8. MTM test captures an intra-trade drawdown missed by trade-only equity.
9. Period boundaries and a cross-boundary 6h hold are tested.
10. Bootstrap is deterministic under seed 0 and returns `INSUFFICIENT_N` when `N < 5`.
11. Decision-gate branch tests cover `DISCARD`, `INSUFFICIENT`, and `FREEZE_PROSPECTIVE_RECOMMENDED`.
12. Canonical file hashes and recomputed hashes agree (three-way `--verify`).
13. `MANIFEST.CODE_COMMIT` is the EXT-C05 commit SHA and contains runner, spec, tests, and fixtures. EXT-C06 adds the immutable run and must not rewrite CODE_COMMIT.
14. Registry schemas validate.
15. The complete existing suite plus new tests pass.
16. No historical artefact (EXP-BTC-005/006 runs, Phase 4 / 4b outputs) or dataset file is modified.
17. HYP-BTC-002 lifecycle/freeze status is unchanged. No extra E-02 row. E-03 and E-04 are not marked CLOSED.

FAIL if any scientific or hash check fails. BLOCKED if a precondition (EXP-BTC-007 already exists; dataset/rector hash mismatch at launch; missing CODE_COMMIT object) prevents a valid run. If code must be fixed after a run, that run cannot remain canonical: new CODE_COMMIT commit and new run-id.

`--verify` three-way integrity (fixes the EXT-H01 verifier weakness without rewriting EXP-BTC-006):

1. Hash checked-in canonical artefact files vs `MANIFEST.OUTPUT_FILES`.
2. Recompute in a temp dir vs the manifest hashes.
3. Canonical-file hashes vs recomputed hashes.

Never hardcode `canonical_run_unmodified=true`. Derive it from actual hash equality of (1) and (3).

## Procedure (frozen)

1. Identify this spec. Hash its bytes (SHA-256).
2. Identify the 1h dataset bytes. SHA-256 must equal DATA_SHA256. If not, MECHANICAL_GATE = FAIL.
3. Read frozen identity from Phase 4 `TOP_CANDIDATES.csv` and EXP-BTC-006 `RESULT.json`. Assert equality with this spec. If mismatch: MECHANICAL_GATE = FAIL. Do not rank or freeze a different candidate.
4. Load bars. Build exact `t−6h` trailing returns. Expanding p1 with history strictly before `t` and 365 calendar-day minimum.
5. Form LONG rebound signals, eligible events, and non-overlapping 6h trades.
6. Compute trade metrics at 0 / 10 / 20 / 50 bps for Discovery, Validation, Recent, Full.
7. Compute yearly table and concentration / outside-2020-2022 flags.
8. Compute hourly MTM (including intra-trade marks and cross-boundary holds) per period and per year.
9. Compute stationary bootstrap on chronological net_10bps trades per period.
10. Apply the predeclared decision gate. Record every clause pass/fail and the mechanical disposition.
11. Write compact outputs, RESULT.json, report, MANIFEST, receipt. Do not write a full hourly equity CSV.
12. Record the actual test command, exit code, number passed/failed/skipped, and SHA-256 of the test log.

## RANDOM_SEED

- Scientific trade/MTM numbers: none (deterministic given the dataset).
- Expanding-percentile audit sampling: seed 0 (does not enter hash-contract files if the audit passes).
- Stationary bootstrap: seed 0 (enters UNCERTAINTY.csv and RESULT.json; frozen).

## Outputs (byte-identical contract)

Canonical run folder: `experiments/EXP-BTC-007/RUN-BTC-007-<UTC-date>-01/`

Hash-contract files:

- `outputs/TRADES.csv`
- `outputs/PERIOD_METRICS.csv`
- `outputs/YEARLY_METRICS.csv`
- `outputs/UNCERTAINTY.csv`
- `result/RESULT.json`
- `report/H1_L6_SURVIVOR_AUDIT.md`

Wall-clock times, `CODE_COMMIT`, `ENVIRONMENT`, test-log SHA, and `receipt.md` / `MANIFEST.json` live beside the contract. STARTED_AT / ENDED_AT / CODE_COMMIT / ENVIRONMENT / TESTS evidence may differ across machines except that CODE_COMMIT must be the EXT-C05 SHA that contains the harness. They are not themselves the scientific hash contract.

Numeric truth is the machine-generated CSV/JSON. Markdown never overrides those files.

RESULT.json must contain: frozen rule, all gate inputs, pass/fail of every gate clause, disposition, disclaimers, and explicit separation of `mechanical_gate` from the scientific/Valita decision. Disclaimers must include `not_clean_oos`, `not_trading_edge`, `does_not_authorize_capital`, and that E-03 / E-04 are not CLOSED.

## Third-party commands

From the repository root:

```
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --run-id RUN-BTC-007-<UTC-date>-01
python3 experiments/EXP-BTC-007/src/run_h1_survivor_audit.py --verify --run-id RUN-BTC-007-<UTC-date>-01
```

Existing suite (must stay green):

```
python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro tests.test_ext_c02_isolation tests.test_ext_c02_reproducibility -v
python3 registries/validate_registries.py
```

A command string alone is not proof. Record actual exit code, passed/failed/skipped counts, and test-log SHA-256.

## Commit sequence (material; do not collapse)

1. EXT-C03: this spec + minimal README. No numerical run.
2. EXT-C04: fixed-candidate metrics, costs, year stability, decision function; targeted unit tests. No canonical run.
3. EXT-C05: hourly MTM, true drawdown, stationary bootstrap, runner CLI, tests, fixtures. This commit is `MANIFEST.CODE_COMMIT` if tests pass.
4. EXT-C06: execute from the clean EXT-C05 commit; immutable run outputs, manifest, receipt, append-only registry rows; open PR; do not merge.

Python 3.9.6 compatibility: never `tarfile.extractall(..., filter="data")`.

## Stop conditions / prohibitions

- reoptimize, reorder, reselect, or freeze a different candidate
- new lookbacks, thresholds, holds, indicators, data, coins, or models
- modify canonical EXP-BTC-005/006 run outputs, Phase 4 / 4b historical outputs, or the dataset
- edit rector v4.1 / v4
- dashboard, DB, experiment platform, alert engine, bot, or live orders
- unrelated refactors
- force-push, amend already-pushed commits, `--no-verify`, or `git config`
- declare promising, confirmed edge, clean OOS, or capital authorization
- claim that ChatGPT audit or Valita freeze/discard already happened
- change HYP-BTC-002 lifecycle or freeze status
- append another E-02 row
- mark E-03 or E-04 CLOSED
- commit a full hourly equity CSV
- hardcode `canonical_run_unmodified=true`

## Approved

EXT-C03 named as the survivor-gate specification freeze. Implementation, MTM/uncertainty, and the canonical run are subsequent named commits. Real capital remains $0.
