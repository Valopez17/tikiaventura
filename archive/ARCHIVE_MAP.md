# Archive map

R0-A locates historical rectors and legacy strategy evidence. It does not copy, move, or recalculate them.

Classifications below are those of `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md` §5. They are not restated as new results.

## Rectors

| Version | Authority | Location in this repo | Notes |
|---|---|---|---|
| v4.1 | **ACTIVE** | `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md` | Pointer: `governance/ACTIVE_RECTOR.md` |
| v4 | historical | `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4.md` | SHA-256 `899e6ce33c3014cfde5111922c6011bc76f0141b5fd63ac7c5f1dfd5337afa84` |
| v3 | historical | **NOT FOUND** | Expected name `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v3.md`. Do not invent. Place a byte-identical copy in `archive/rectors/` when recovered. |
| v2 | historical | **NOT FOUND** | Same recovery rule. No v2 alert contract is active. |
| v1 | historical | **NOT FOUND** | Same recovery rule. |
| v4→v4.1 changelog | historical | `V4_TO_V4_1_CHANGELOG.md` | |

`archive/rectors/` is the destination for recovered historical rector files. R0-A does not duplicate v4 there, because a second copy can drift. The root file is the archival copy.

## Dataset (not moved)

| Object | Live path | Canonical destination (not migrated) | Hash |
|---|---|---|---|
| BTCUSDT spot 1h | `btc_tsmom_replication/btcusdt_1h.csv` | `data/raw/` (later, named task) | TBC — E-01 / R0-B |

## Legacy strategy evidence (not moved, not recalculated)

| Family | v4.1 classification (unchanged) | Live path | Canonical destination |
|---|---|---|---|
| Weekly Calendar | L2 CALCULATED; DEEPEN_METHOD / UNFROZEN; selection_contaminated | `research/market_state_observatory/trade_signal_research/strategy_lab/phase3_weekly_calendar_anomaly/` | `experiments/EXP-ID/` later; no ID assigned in R0-A |
| Extreme Move | L2 CALCULATED, afectado; INVALIDATED (E-02, E-03, E-04) | `.../phase4_extreme_move_reversal/` and `.../phase4b_extreme_move_audit_fix/` | same rule |
| Breakout | L0 IDEA / spec draft; BACKLOG; not authorized | `.../phase5_breakout_continuation/` | artefacts exist; classification is not promoted by R0-A |
| Volatility Compression | L0 IDEA / spec draft; BACKLOG | **no implementation folder** | none |

IDs such as HYP-BTC-001 / EXP-BTC-001 are **not** invented here. Assigning them to legacy work is R0-C.

## R0-C ID assignment (references only; numbers not recalculated)

Classifications below are labels copied from v4.1 §5. They are not new results. No historical RUN-IDs are invented. No family was rerun.

| Family | Hypothesis | Experiment | v4.1 classification (label only) | Points to |
|---|---|---|---|---|
| Weekly Calendar | HYP-BTC-001 | EXP-BTC-001 | L2 CALCULATED; DEEPEN_METHOD / UNFROZEN; selection_contaminated | `research/market_state_observatory/trade_signal_research/strategy_lab/phase3_weekly_calendar_anomaly/` + rector §5.1 |
| Extreme Move | HYP-BTC-002 | EXP-BTC-002 | L2 CALCULATED, afectado; INVALIDATED (E-02, E-03, E-04) | `.../phase4_extreme_move_reversal/` and `.../phase4b_extreme_move_audit_fix/` + rector §5.2 |
| Breakout | HYP-BTC-003 | EXP-BTC-003 | L0 IDEA / spec draft; BACKLOG; not authorized | `.../phase5_breakout_continuation/` + rector §5.3. Artefacts exist; not promoted. |
| Volatility Compression | HYP-BTC-004 | EXP-BTC-004 | L0 IDEA / spec draft; BACKLOG | **NOT FOUND** (no implementation folder). No artefacts invented. Rector §5.4. |

Synthetic reproducibility harness (not a trading edge; not a §5 family): HYP-BTC-005 / EXP-BTC-005 / RUN-BTC-005-20260902-01 under `experiments/EXP-BTC-005/`.

## Known tension (not resolved in R0-A)

v4.1 §5.3 classifies Breakout as L0 / SPEC next, not SCAN. Laboratory artefacts already exist under `phase5_breakout_continuation/`. R0-A records both facts and does not reclassify, recalculate, or delete.
