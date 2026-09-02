# Candidate model spec — MACRO_BASE_CANDIDATE_V1

**Status: CANDIDATE — NOT YET CLEAN-OOS VALIDATED**

This specification is frozen so it cannot be quietly edited after further
inspection of 2015–2023 or after 2024–2026 is opened. It is **not** a
validated model. It is **not** a trading rule.

Do not declare this model validated.

---

## Name

`MACRO_BASE_CANDIDATE_V1`

## Purpose

Estimate the probability that the **future crypto market return is
positive**, using **current** (week t) macro conditions only.

## Features (exact)

- `DXY_CHG_12W`
- `US2Y_CHG_12W`
- `REAL10Y_CHG_12W`
- `NASDAQ_RET_12W`

No other macros. No M2. No HY spread. No Fed funds / Fed balance sheet
in this candidate (Phase 6B left those as diagnostic / sign-flip).

## Algorithm (exact)

- Logistic regression
- L2 penalty
- `C = 1.0`
- Train-only median imputation
- Train-only `StandardScaler`
- Expanding walk-forward
- Minimum training N = 100 (do not lower)

At week t, a training observation s is allowed only if its H-week
outcome was already observable: `s <= t - H`.

## Explicitly excluded

- No crypto features
- No regime interaction
- No lag (L = 0 only; outcome window `t+1 … t+H`)
- No feature selection
- No hyperparameter tuning
- No polynomial terms
- No threshold tuning on predicted probabilities

## Horizon policy

**Do not select one “optimal” horizon.**

Freeze evaluation horizons:

- 4 weeks
- 8 weeks
- 12 weeks

These were pre-specified. Phase 6D found no robust evidence that
justifies choosing one after inspecting 2015–2023.

For any later clean evaluation, **score all three**. Do **not** tune or
alter the model after seeing those results. Do not drop a horizon
because it looks worse.

Target at each H (unchanged):

`Y_H = 1` if `future_return_Hw > 0`, else 0.

## Baseline

Always report expanding mature **M0** (historical frequency) on the
**same eligible weeks**. Skill is Brier skill vs that M0, plus log loss,
AUC (secondary), balanced accuracy (secondary). Non-overlapping offsets
of length H remain a required robustness check.

## What 2021–2023 is not

2021–2023 is **PSEUDO-OOS / TEMPORAL ROBUSTNESS**.

It has been inspected during multiple earlier phases, including
descriptive work (Phase 6B) and model comparison (6C, 6D, 6E, 6F).
**Do not call it clean validation.** Positive BSS in that window is why
this spec is a *candidate*, not why it is *validated*.

## Final OOS policy

**2024–2026 remains the strongest untouched evaluation period.**

Before opening it:

- no new feature changes
- no new lags
- no new horizon search
- no regime interactions
- no threshold tuning
- no model substitution

The candidate specification must stay frozen first. Any change creates a
**new** named spec (not a silent v1 edit) and consumes the right to call
2024–2026 a test of `MACRO_BASE_CANDIDATE_V1`.

## Provenance (not a result)

- Features: Phase 6B move-forward list, walked in 6C.
- Same four features at 4w/8w/12w: Phase 6D.
- L = 0 retained after 6E.
- No Bull/Bear or transition terms after 6F.

Phase 6C label for this spec at 12w: **WEAK / CONDITIONAL**, not A.
That label is not upgraded by this freeze.
