# Phase 4 — Bull quality & fragility

When the market is **already Bull**, what distinguishes a healthy continuation
from a fragile / late Bull over the next 4–12 weeks?

This phase tests whether **change, deterioration, and stress** contain
information beyond **current levels**. Phase 3 showed that Bull failures can
already have very high momentum and breadth.

Descriptive only. Not a score, classifier, or trading rule.

V1 and Phase 3 are read-only. **2024–2026 is not used. Macro is not used.**

## Inputs (read-only)

- `v1_weekly_core/results/weekly_market_state.csv` (`market_index` for drawdown-from-high)
- Phase 3 `opportunity_episode_catalog.csv` (levels, expanding MOM percentiles, lagged breadth, outcomes)

Hsieh panel is not required for this phase.

## Frozen research cuts (not retuned)

- HIGH_MOM_BULL: `MOM_12W_PERCENTILE >= 0.70`
- EXTREME_MOM_BULL: `MOM_12W_PERCENTILE >= 0.90`
- Breadth change: ±5pp over 4 weeks
- Vol / MOM percentile change: ±0.10 over 4 weeks
- Candidate Healthy / Fragile: pre-specified in the script; not optimized

## Outputs

- `results/bull_quality_weekly.csv` — one row per Bull week
- `results/bull_quality_conditionals.csv` — group × horizon × ALL/DECLUSTERED
- `results/bull_transition_analysis.csv`
- `results/BULL_QUALITY_FRAGILITY_ANALYSIS.md`

## Run

```bash
python3 src/analyze_bull_quality_fragility.py
```
