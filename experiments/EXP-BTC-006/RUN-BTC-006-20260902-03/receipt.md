# Run receipt — EXP-BTC-006 / EXT-C02

RUN_ID: RUN-BTC-006-20260902-03

DELTA / OBJETIVO VERIFICABLE: Isolated A vs B lookback-mode contrast for E-02. Not a strategy selection.

FILES CHANGED: this run folder only (spec/src live under EXP-BTC-006/).

COMMAND: `python3 experiments/EXP-BTC-006/src/run_ext_c02.py --run-id RUN-BTC-006-20260902-03`

CODE_COMMIT: `e46b0a9ad0574a199bf59855220014cd5ab8acc9`

TEST RESULT: see registries/runs.jsonl and EXT-C02 receipt after the unittest suite.

INPUT HASHES: btc_tsmom_replication/btcusdt_1h.csv SHA-256 77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103
SPEC_HASH: 039f0de9763fd5dbfb6dc57e603da21ebae09800ff857c32ed4415d9964aeddc

OUTPUT HASHES:
- `outputs/SIGNAL_IMPACT.csv` SHA-256 `999fa511c0618d65eb922260a6c381ce45d7cc88d587e540c0718e799c86a906`
- `outputs/RULE_IMPACT.csv` SHA-256 `7747eedd255934b05dde0a93b259e927661974449d9e5479e162fbd8353e7d2d`
- `outputs/FROZEN_TOP10_IMPACT.csv` SHA-256 `54bf32da134e887f48528010eb72e3c055d5edae54fd42b38c95abdf4c5f0e1f`
- `result/RESULT.json` SHA-256 `1d5b137d84da8b2934620228a20197bdfba3b3fee9116bcca87684555a52608c`
- `report/EXT_C02_E02_IMPACT.md` SHA-256 `058e9e868d502190e90f09db2ea64288af219b9ab17defd93fea067c412161a9`

PRIMARY METRICS: materiality=MATERIAL (separate from mechanical_gate=PASS).

CONTROL RESULT: unconditional same-horizon open-to-open return; identical across arms.

UNCERTAINTY: not a new interval estimate; inherited trade Sharpe is comparative only.

N/TRIALS: 2 arms x 288 frozen rules; no reselection.

MECHANICAL GATE: PASS

SPEC DEVIATIONS: none.

BLOCKERS: EXT-H01 ChatGPT audit not done. E-02 not CLOSED.

REGISTERS UPDATED: recorded separately in COMMIT_B.

not_a_trading_edge: true
does_not_authorize_capital: true
