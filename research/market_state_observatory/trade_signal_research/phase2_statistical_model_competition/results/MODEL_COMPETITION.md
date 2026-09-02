# Statistical model competition — Phase 2

Chronological 80/20 holdout. Expanding walk-forward on development. Not a trading strategy. Holdout was not used to choose features, targets, models, or thresholds.

Brier = mean squared probability error (lower better).
BSS = 1 − Brier_model / Brier_M0. BSS>0 means improvement on the expanding base rate.
AUC = ranking probability, not accuracy.
Log loss penalizes confident wrong probabilities (lower better).
Balanced accuracy uses a frozen 0.5 cutoff (not optimized).

## 1. Split

Last development date: **2024-05-27**. First holdout date: 2024-05-28.
Eligible N=3819 (dev 3055 / holdout 764).
Walk-forward N is slightly smaller than eligible development N because the first dates lack min-train=100 mature labels.

## 2. Eligible counts by target

| target | development N | holdout N | development prevalence | holdout prevalence |
|---|---:|---:|---:|---:|
| UP_60D | 2896 | 764 | 0.386 | 0.164 |
| ADVERSE_60D | 2896 | 764 | 0.381 | 0.360 |

## Development walk-forward — UP_60D

| model | N | prev | brier | BSS | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 2896 | 0.386 | 0.2502 | 0.000 | 0.6941 | 0.373 | 0.496 |
| M1 | 2896 | 0.386 | 0.2600 | -0.039 | 0.7510 | 0.585 | 0.555 |
| M2 | 2896 | 0.386 | 0.2609 | -0.043 | 0.7729 | 0.585 | 0.553 |
| M3 | 2896 | 0.386 | 0.2599 | -0.039 | 0.7507 | 0.585 | 0.555 |
| M4 | 2896 | 0.386 | 0.3173 | -0.268 | 1.4502 | 0.504 | 0.500 |
| M5 | 2896 | 0.386 | 0.2644 | -0.057 | 0.7560 | 0.560 | 0.541 |

Models with BSS>0 vs M0: none.
Selected candidate: **NONE**.

## Development walk-forward — ADVERSE_60D

| model | N | prev | brier | BSS | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 2896 | 0.381 | 0.2516 | 0.000 | 0.7094 | 0.385 | 0.500 |
| M1 | 2896 | 0.381 | 0.2450 | 0.026 | 0.7218 | 0.591 | 0.557 |
| M2 | 2896 | 0.381 | 0.2458 | 0.023 | 0.7324 | 0.590 | 0.557 |
| M3 | 2896 | 0.381 | 0.2448 | 0.027 | 0.7207 | 0.591 | 0.557 |
| M4 | 2896 | 0.381 | 0.2918 | -0.160 | 1.0665 | 0.557 | 0.535 |
| M5 ← selected | 2896 | 0.381 | 0.2437 | 0.031 | 0.7058 | 0.597 | 0.568 |

Models with BSS>0 vs M0: M1, M2, M3, M5.
Selected candidate: **M5**.

## Holdout (untouched 20%)

### UP_60D — class **NO CANDIDATE**

NO CANDIDATE. Holdout was not used to rescue a development failure.

### ADVERSE_60D — class **MIXED**

| model | N | prev | brier | BSS | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 764 | 0.360 | 0.2326 | 0.000 | 0.6581 | 0.314 | 0.500 |
| M5 | 764 | 0.360 | 0.2351 | -0.011 | 0.6634 | 0.630 | 0.508 |
Non-overlap median BSS=-0.022; min=-0.214; max=0.197; BSS>0: 28/60 evaluable.

Canonical logistic calibration on holdout: intercept=0.083, slope=0.585 (ideal ~0 and ~1). Not OLS on probabilities.

| bin | N | mean predicted | mean actual |
|---|---:|---:|---:|
| [0.0,0.1) | 119 | 0.076 | 0.101 |
| [0.1,0.2) | 208 | 0.150 | 0.337 |
| [0.2,0.3) | 129 | 0.257 | 0.527 |
| [0.3,0.4) | 132 | 0.349 | 0.394 |
| [0.4,0.5) | 123 | 0.431 | 0.415 |
| [0.5,0.6) | 47 | 0.551 | 0.340 |
| [0.6,0.7) | 6 | 0.618 | 1.000 |

## Answers

1. Exact chronological 80/20 split date: last development date **2024-05-27**.
2. Eligible observations: UP_60D dev N=2896, holdout N=764; ADVERSE_60D dev N=2896, holdout N=764.
3. Which models beat M0 during development (BSS>0)? UP_60D: none | ADVERSE_60D: M1, M2, M3, M5.
4. Candidate for UP_60D: **NONE**.
5. Candidate for ADVERSE_60D: **M5**.
6. Untouched 20%: UP_60D: no candidate; ADVERSE_60D M5 BSS=-0.011 AUC=0.630 class=MIXED.
7. Did more sophisticated models improve on logistic (M1)? UP_60D: M3 beat M1 on Brier in development | ADVERSE_60D: M3, M5 beat M1 on Brier in development.
8. Probability calibration (holdout logistic, selected only): UP_60D: n/a; ADVERSE_60D intercept=0.083 slope=0.585.
9. Non-overlapping evaluation: UP_60D: n/a; ADVERSE_60D median BSS=-0.022 (28/60) survive=False.
10. Continue toward a formal entry decision framework? **WEAK**

## Decision

**WEAK**

Predictive research only. Not ENTER/EXIT rules. Spec was not changed after seeing holdout numbers.

