# Phase 6B — Macro forensics (descriptive only)

Test whether **macro conditions at week t** differ between strong and weak
**12-week crypto outcomes**.

**DESCRIPTIVE ONLY. NOT PREDICTIVE. NOT CAUSAL.**

No logistic, no ML, no scores, no regimes, no thresholds, no 2024–2026.
Phases 3, 4, 5, 6A and V1 are not modified.

## Inputs (read-only)

- Phase 6A `macro_weekly.csv` (macro at t)
- Phase 3 `opportunity_episode_catalog.csv` (12w outcomes and Bull flags)

Merge is inner on Friday `week`. Macro is never taken from a later week than t.

## Groups (12w complete weeks only)

| group | definition (Phase 3, unchanged) |
|---|---|
| TOP10 | `is_top10_12w` (outcome percentile ≥ 0.90) |
| BOTTOM10 | `is_bottom10_12w` (outcome percentile ≤ 0.10) |
| OTHER | complete 12w, neither TOP10 nor BOTTOM10 |
| REST | complete 12w, not TOP10 (used for the directional check) |
| BULL_CONTINUATION | Bull at t and `future_return_12w > 0` |
| BULL_FAILURE | Bull at t and `future_return_12w ≤ 0` |

`M2_CHG_12W` is reported as **diagnostic only** (Phase 6A lookahead HIGH).
`HY_SPREAD` is absent and unused.

## Run

```bash
python3 src/analyze_macro_forensics.py
```

## Outputs

- `results/macro_forensic_summary.csv`
- `results/MACRO_FORENSIC_ANALYSIS.md`
