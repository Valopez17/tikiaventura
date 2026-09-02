# Phase 3B2 — Derivatives incremental information test

**One objective:** does derivatives information add predictive value
beyond the Phase 2 BASE set?

This is **historical walk-forward / temporal robustness**. It is **not**
clean OOS, not an untouched holdout, and not final validation.
2024–2026 has already been inspected in this project. The next genuine
clean evaluation is prospective after candidate freeze.

Not a trading strategy. No PnL. No ENTER/EXIT rules.

## Comparison rule (non-negotiable)

Same dates, same target, same model, same preprocessing, same training
history, same scoring observations. The only change is the feature set.

Do not compare BASE on a longer sample against derivatives on a shorter one.

## Frozen architecture (declared before results)

- **M0:** expanding mature-label prevalence at t
- **Predictor:** L2 logistic, sklearn `LogisticRegression`, `penalty=l2`,
  `C=1.0`, `solver=lbfgs`, `max_iter=4000`, `random_state=0`
- Train-only median imputation; train-only `StandardScaler`
- Mature labels only: training date s satisfies `s + 60 calendar days <= t`
- Minimum train N = 100
- **Daily refit** on every eligible prediction date (same schedule for
  every feature set)
- No GBM, Probit, GAM, elastic net, or hyperparameter search

## Tests

**Test A** (identical dates with BASE + DERIV_CORE finite and target known):

- A0 = BASE
- A1 = BASE + DERIV_CORE

DERIV_CORE: `funding_pctl`, `funding_change_1d`, `funding_cum_30d`,
`basis_pctl`, `basis_change_1d`, `perp_volume_rel_30d`,
`perp_spot_volume_ratio`.

Diagnostic only (same dates, not for selection): BASE+FUNDING,
BASE+BASIS, BASE+PERP_ACTIVITY.

**Test B** (identical dates with BASE + CORE + OI_ADDON finite):

- B0 = BASE + DERIV_CORE
- B1 = BASE + DERIV_CORE + OI_ADDON

OI_ADDON: `oi_change_1d`, `oi_change_7d`, `oi_pctl`, `oi_over_volume`.

## Run

```bash
python3 src/run_derivatives_incremental_test.py
```

Needs network only if Phase 2’s Binance tape or 2024+ macro must be
refreshed. Does not write into Phase 1 / 2 / 3B.

## Language

Permitted: historical walk-forward evidence; incremental information;
ranking vs probability loss.

Not permitted: clean OOS; trading strategy; “this predicts the market”;
treating AUC as accuracy.
