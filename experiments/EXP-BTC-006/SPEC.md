# EXP-BTC-006 — Isolated lookback-mode robustness (EXT-C02)

EXPERIMENT_ID: EXP-BTC-006  
HYPOTHESIS_ID/VERSION: HYP-BTC-002 / 1  
ERROR_ID: E-02  
EXPERIMENT_TYPE: ROBUSTNESS  
SPEC_STATUS: APPROVED for EXT-C02  
TASK_ID: EXT-C02  
NOT_A_TRADING_EDGE: true  
DOES_NOT_AUTHORIZE_CAPITAL: true  
NOT_CLEAN_OOS: true  
HYP-BTC-002 lifecycle: remains INVALIDATED (this spec does not change it)  
E-02 estado: remains FIXED_PENDING_VERIFICATION (primitive tested; EXT-H01 ChatGPT audit still pending; do not mark CLOSED)  
E-03 estado: remains OPEN  
E-04 estado: remains OPEN

This spec isolates one causal contrast. It is not a new search, not a survivor-gate rewrite, not an equity-MTM repair, and not a capital decision.

## Pregunta

Holding everything else identical, how much do signals and economic results change when positional lookback is replaced by exact calendar-timestamp lookback?

This is not to prove an economic effect, select a strategy, or finish the Extreme sprint.

## Arms (frozen)

- A `LEGACY_POSITIONAL`: `close[i] / close[i-L] - 1`
- B `EXACT_TIMESTAMP`: `close(t) / close(t − L hours) - 1`, eligible only if the exact timestamp `t − L` exists. No nearest-bar, fill, interpolation, or substitution.

Arm B reuses `temporal/exact_timestamp.py` semantics (`DatetimeIndex.get_indexer` / `lookup_exact`). This spec does not create a third exact-timestamp definition.

The only allowed difference between A and B is trailing-return construction and the mechanical consequence for expanding percentiles, signals, events, and trades. Remaining configuration is one shared object. Tests assert the two arm configs differ only by `lookback_mode`.

## Dataset

- DATA_PATH: `btc_tsmom_replication/btcusdt_1h.csv`
- DATA_SHA256: `77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103`
- Do not change, move, or redownload the file.
- Do not impute missing hours.

## Frozen Phase 4 design (shared)

Inherited from `research/market_state_observatory/trade_signal_research/strategy_lab/phase4_extreme_move_reversal/` and not reopened:

- lookbacks `{6, 12, 24, 72}` hours
- tails/percentiles `{1, 2.5, 5, 95, 97.5, 99}` as applicable (down: 1 / 2.5 / 5; up: 95 / 97.5 / 99)
- holds `{6, 12, 24, 48, 72, 168}` hours
- original long/short and rebound/continuation theses
- expanding percentiles of finite trailing returns with timestamp strictly before `t`
- minimum history: 365 calendar days from the first finite trailing return
- entry: open of bar `t+1`; exit: open exactly H hours after entry
- missing entry or exit bar: skip the event (no fill)
- executable trades: ignore new signals until the current trade’s exit time
- unconditional control: every hour in the same period with a valid same-horizon next-open to exit-open return
- splits: discovery `data start → 2021-12-31`; validation `2022-01-01 → 2024-12-31`; recent `2025-01-01 → latest complete bar`
- primary fee: 10 bps round trip, `net = (1 + gross) * (1 - 0.0010) - 1`
- inherited trade Sharpe is comparative only
- Top 10 frozen exactly from `phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv` (read-only; no reselection)

Phase 4b (`phase4b_extreme_move_audit_fix/`) may be used as a function/reference source. Its mixed conclusion (exact timestamp + survivor gate + MTM) does not substitute this run.

## Procedure (frozen)

1. Identify this spec. Hash its bytes (SHA-256).
2. Identify the 1h dataset bytes. SHA-256 must equal DATA_SHA256. If not, MECHANICAL_GATE = FAIL.
3. Load the frozen Top 10 rule ids from `TOP_CANDIDATES.csv` in file order. Do not rank, reorder, or freeze a new candidate.
4. Build one shared `FrozenConfig`. Instantiate arm A and arm B that differ only by `lookback_mode`.
5. Walk the frozen 288-rule design twice (A then B). The only input that changes is trailing-return construction.
6. Measure signal impact per lookback × tail × percentile.
7. Measure economic impact per frozen rule and period (discovery / validation / recent).
8. Report impact on the originally frozen Top 10 (no reselection).
9. Report `L6_down_p1_rebound_long_H6` for both arms in this pipeline. Historical Phase 4 figures may be labeled; they are not the causal contrast.

## RANDOM_SEED

None for scientific outputs. Expanding-percentile audit sampling uses seed 0 and does not enter the hash-contract files if the audit passes.

## Metrics

1. Signal impact per lookback/tail/percentile: A vs B counts, overlap, disappeared, appeared, legacy signals whose exact `t−L` is missing, absolute and percent difference.
2. Economic impact per frozen rule and period: N events, N executable non-overlapping trades, mean gross, mean net (inherited 10 bps), inherited trade Sharpe (comparative only), inherited unconditional control and conditional advantage, deltas B−A, sign change of mean net.
3. Same economic fields for the frozen Top 10, using the original discovery rank from the frozen artifact.
4. L6 candidate: both arms in this pipeline; historical Phase 4 numbers are labels only.

Primary economic metric remains trade mean net. Hourly equity MTM is not a primary metric here (E-04 stays OPEN). Survivor-gate classifications are not recomputed (E-03 stays OPEN).

## Predeclared materiality (Phase 4b coded criterion; not optimized after seeing results)

Copied from `phase4b_extreme_move_audit_fix/src/audit_extreme_move_candidates.py` without retuning:

- signal: symmetric difference `n_disappeared + n_appeared >= max(5, int(0.05 * max(n_legacy, 1)))`
- economic: `abs(mean_net_B - mean_net_A) > 0.002` in Discovery or Validation

Application, declared before the run:

- evaluate the signal criterion on every lookback × tail × percentile cell on the pooled (all-period) signal set
- evaluate the economic criterion on every frozen rule in Discovery and in Validation
- global `MATERIAL` if any signal cell trips the signal criterion OR any frozen-rule Discovery/Validation mean-net change trips the economic criterion
- otherwise `NOT_MATERIAL`
- report any Validation mean-net sign change even if `NOT_MATERIAL`

Do not change these thresholds after seeing numbers. `MATERIAL` / `NOT_MATERIAL` is not a capital decision, not a strategy selection, and not a claim that a rule is operable.

## Mechanical gates

PASS only if all hold:

1. Dataset SHA-256 equals DATA_SHA256.
2. Both-arm configs are identical except `lookback_mode`.
3. Expanding percentiles use only timestamps `< t` (audit vs `numpy.quantile` on `{ret_s : s < t}`).
4. Top 10 ids are read from the frozen artifact; no reselection.
5. Exact-timestamp arm uses `temporal.exact_timestamp` semantics; missing `t−L` is ineligible (no substitute row).
6. `--verify` reproduces contracted output hashes.
7. `MANIFEST.CODE_COMMIT` is a 40-char git SHA of a commit that contains the executed runner, spec, and required tests/fixtures.
8. Runner/spec/test worktree is clean at materialize time.
9. No write to the dataset file or to Phase 4 / Phase 4b historical outputs.

FAIL otherwise. Mechanical_gate is separate from `MATERIAL` / `NOT_MATERIAL`.

## Outputs (byte-identical contract)

Inside the run folder:

- `outputs/SIGNAL_IMPACT.csv`
- `outputs/RULE_IMPACT.csv`
- `outputs/FROZEN_TOP10_IMPACT.csv`
- `result/RESULT.json`
- `report/EXT_C02_E02_IMPACT.md`

Wall-clock times, `CODE_COMMIT`, and `ENVIRONMENT` live in `MANIFEST.json` / `receipt.md` and may differ across machines. They are not part of the hash contract.

Numeric truth is the machine-generated CSV/JSON. Markdown never overrides those files.

Canonical run hashes are those recorded in that run’s `MANIFEST.json` field `OUTPUT_FILES`.

## Third-party command

From the repository root:

```
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --run-id RUN-BTC-006-<UTC-date>-01
python3 experiments/EXP-BTC-006/src/run_ext_c02.py --verify --run-id RUN-BTC-006-<UTC-date>-01
```

`--verify` recomputes in a temporary directory, compares contracted hashes, and does not modify the canonical run.

## Stop conditions / prohibitions

- reoptimize, reorder, reselect, or freeze a new candidate
- new lookbacks, thresholds, holds, indicators, data, coins, or models
- change survivor gate or classifications (E-03)
- introduce equity MTM as primary metric or repair E-04
- rewrite or overwrite Phase 4, Phase 4b, or prior runs
- change, move, or redownload the dataset
- close E-03, E-04, E-12, E-18, E-19, E-20, or E-23
- mark E-02 CLOSED
- update R0-H01 / E-18
- change HYP-BTC-002 lifecycle or add a new hypothesis
- declare a trading edge, operable signal, or capital authorization

## Approved

EXT-C02 named by Valita. Isolated E-02 economic-impact measurement only.
