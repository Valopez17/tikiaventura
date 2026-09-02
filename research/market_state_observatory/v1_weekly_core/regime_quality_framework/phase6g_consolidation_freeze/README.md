# Phase 6G — Consolidation / freeze

This phase **does not model**. It does not load 2024–2026. It does not
recompute metrics. It freezes what the current crypto+macro diagnostic
branch already showed, so the next step cannot silently retune.

## Purpose

Stop iterative inspection of 2015–2023. Document what is closed, what
remains a candidate, and what must not change before any later clean
evaluation period is opened.

## Inputs (read-only)

- Phase 5 crypto walk-forward
- Phase 6B macro forensics
- Phase 6C macro walk-forward
- Phase 6D horizon diagnostic
- Phase 6E macro lag diagnostic
- Phase 6F regime / transition diagnostic

Prior phases are not modified.

## Outputs

- `results/CONSOLIDATED_FINDINGS.md`
- `results/REJECTED_HYPOTHESES.md`
- `results/CANDIDATE_MODEL_SPEC.md`

The frozen candidate is **MACRO_BASE_CANDIDATE_V1**. Any later change
(features, lag, horizon search, regime interactions, C, imputation)
requires a **new research branch**, not an edit to that spec.

## What this phase does not do

- no retraining
- no new metrics or charts
- no 2024–2026
- no reinterpretation of WEAK / NO EDGE as validated skill
