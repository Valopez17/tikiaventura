# Phase 3 — Information expansion

**Step A only: feature family registry + data-source audit.**
No `src/`. No datasets downloaded. No models. No signals.

This branch asks what *additional information* could improve economically
relevant crypto outcomes. Ultimate decisions: ENTER / HOLD / REDUCE /
EXIT / STAY OUT.

Do not collect a variable merely because it exists. Every candidate must
have a plausible economic mechanism. Data quality beats quantity.

---

## Critical validation note (read first)

**2024–2026 has already been inspected.**

Prior work that touched this window:

- Observatory Phase 6H final clean OOS (weekly macro, 2024-01-05 → 2026-08-28)
- Trade-signal Phase 1 (event study through 2026, including the 2024-08-05 case)
- Trade-signal Phase 2 chronological holdout from 2024-05-28

Therefore:

- **Do not call 2024–2026 clean out-of-sample** for any new model, feature
  family, or specification created after this point.
- For new models, **2015–2026 may be used for development and temporal
  robustness**, with strict walk-forward construction (mature labels only;
  no peeking at future transforms).
- The next genuinely untouched test is **PROSPECTIVE**: it starts only
  after the final expanded model is frozen, and it uses dates that did
  not exist at freeze time.

Phase 3H is that prospective evaluation. It is not a second look at 2024–2026.

---

## Current information set (do not redefine)

Already available from Phase 1 / Phase 2. Do not rebuild or rename.

**A. BTC price / state (expanding percentiles)**

- `pctl_ret_1d`
- `pctl_ret_3d`
- `pctl_ret_7d`
- `pctl_dd_30`
- `pctl_vol_20`
- `pctl_rel_volume`

**B. Macro (frozen MACRO_BASE_CANDIDATE_V1 12-week changes)**

- `DXY_CHG_12W`
- `US2Y_CHG_12W`
- `REAL10Y_CHG_12W`
- `NASDAQ_RET_12W`

Phase 3 asks whether *new families* add information beyond this set.

---

## What this step is

Architecture and data audit only.

| Allowed | Not allowed |
|---|---|
| Catalogue families and mechanisms | Train models |
| Audit sources, coverage, timestamps | Calculate predictive metrics |
| Rank a build sequence | Tune hyperparameters |
| Mark KEEP / DIAGNOSTIC / DEFER / DROP | Open a new holdout |
| Distinguish free vs paid | Pretend 2024–2026 is untouched |
| Separate X_UP vs X_RISK conceptually | Add hundreds of features |
| | Modify Phase 1, Phase 2, `v1_weekly_core`, or MACRO_BASE_CANDIDATE_V1 |
| | Download large datasets |
| | Build Polymarket sentiment indexes |
| | Scrape social media |
| | Create trading signals |

Later incremental tests (Phase 3F) must answer:

> Does adding family F improve the **existing** information set?

Not:

> Can we tune a new model until F looks useful?

Use the **same architecture** for BASE vs BASE + new family so that any
delta can be attributed to information, not algorithm complexity.

For each raw concept, later allow only a few transforms (level, short
change, historical percentile). Prefer 1d / 7d / 30d only when
economically justified. No exhaustive window searches.

---

## Families audited

| Priority | Family | Role |
|---|---|---|
| 1 | Derivatives | Positioning, crowding, forced unwind |
| 2 | Flows | Incremental demand / liquidity |
| 3 | Expectations | Event-implied probabilities (Polymarket) |
| 4 | Sentiment | Fear/greed, search, text |
| 5 | Crypto cross-section / breadth | Observatory concepts, daily feasibility only |
| 6 | Market microstructure | Optional / later |

---

## Outputs

| File | Contents |
|---|---|
| `results/FEATURE_FAMILY_REGISTRY.md` | Every candidate variable, mechanism, quality flags, status |
| `results/DATA_SOURCE_AUDIT.md` | Source protocol for every KEEP candidate |
| `results/EXPANSION_PLAN.md` | Ranked sequence and answers to the ten output questions |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| KEEP FOR DATA BUILD | Passes mechanism + reconstructable history well enough to collect in a later phase |
| DIAGNOSTIC ONLY | Useful for description / case studies; do not treat as a primary predictor family |
| DEFER | Mechanism exists, but history, cost, or methodology is not ready |
| DROP | Do not collect: fatal timestamp, survivorship, look-ahead, or no reproducible source |

A variable with excellent intuition but bad timestamps, severe
survivorship, unavailable history, or unavoidable look-ahead is **not**
promoted because it sounds useful.

---

## Location

`research/market_state_observatory/trade_signal_research/phase3_information_expansion/`

Do not place this inside `v1_weekly_core/` or `regime_quality_framework/`.

---

## Phase 3B

`phase3b_derivatives_dataset/` — daily Binance BTCUSDT derivatives panel
(funding, premium-index basis, perp/spot quote volume, OI). No models.
Do not modify this Step A `results/` tree from later phases.

---

## Phase 3B2

`phase3b2_derivatives_incremental_test/` — L2 logistic walk-forward:
does DERIV_CORE (and OI) add information beyond BASE? Historical
robustness only. Not clean OOS.
