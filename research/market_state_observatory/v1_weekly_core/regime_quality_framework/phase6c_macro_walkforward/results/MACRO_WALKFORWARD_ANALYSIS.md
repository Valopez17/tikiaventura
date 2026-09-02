# Phase 6C — Macro walk-forward analysis

Question: does a **frozen four-feature macro set, alone**, improve 12w crypto probability forecasts versus an expanding base rate?

No crypto features. No search. No combined model. No 2024–2026. Not a trading backtest.

Mature labels: at week t, training uses only weeks `s <= t - 12`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.

Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.

## Sample

| item | value |
|---|---|
| merged weeks | 470 |
| last week | 2023-12-29 |
| 2024+ | none |
| complete 12w outcomes | 434 |
| Bull weeks with complete 12w | 145 |
| min train N | 100 |

## ALL_MARKET — primary `future_return_12w > 0`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.505 | 0.3014 | 0.000 | 0.8198 | 0.336 | 0.500 |
| M_MACRO | 323 | 0.505 | 0.3247 | -0.077 | 1.1071 | 0.507 | 0.530 |

### 2021–2023 validation

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.469 | 0.2806 | 0.000 | 0.7569 | 0.356 | 0.500 |
| M_MACRO | 145 | 0.469 | 0.2327 | 0.170 | 0.6651 | 0.690 | 0.641 |

### Non-overlapping 12-week offsets (primary, full walk-forward)

Offsets used: 12/12. Median BSS=-0.092; min=-0.173; max=0.048; offsets with BSS>0: 1/12.

| offset | N | brier M_MACRO | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 27 | 0.3249 | 0.3110 | -0.045 |
| 01 | 27 | 0.2850 | 0.2993 | 0.048 |
| 02 | 26 | 0.3587 | 0.3277 | -0.095 |
| 03 | 27 | 0.3377 | 0.3039 | -0.111 |
| 04 | 27 | 0.3164 | 0.2880 | -0.098 |
| 05 | 27 | 0.3280 | 0.2797 | -0.173 |
| 06 | 27 | 0.2740 | 0.2658 | -0.031 |
| 07 | 27 | 0.3251 | 0.2961 | -0.098 |
| 08 | 27 | 0.3176 | 0.2995 | -0.060 |
| 09 | 27 | 0.3530 | 0.3044 | -0.160 |
| 10 | 27 | 0.3423 | 0.3349 | -0.022 |
| 11 | 27 | 0.3347 | 0.3073 | -0.089 |

## ALL_MARKET — secondary targets

### `future_return_12w > +20%`

Full:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.375 | 0.2731 | 0.000 | 0.7414 | 0.392 | 0.482 |
| M_MACRO | 323 | 0.375 | 0.3028 | -0.109 | 0.8887 | 0.557 | 0.556 |

2021–2023:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.297 | 0.2529 | 0.000 | 0.6989 | 0.396 | 0.506 |
| M_MACRO | 145 | 0.297 | 0.2153 | 0.149 | 0.6171 | 0.667 | 0.609 |

### `future_return_12w < -20%`

Full:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.245 | 0.2097 | 0.000 | 0.9575 | 0.269 | 0.500 |
| M_MACRO | 323 | 0.245 | 0.2167 | -0.033 | 1.0772 | 0.532 | 0.537 |

2021–2023:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.234 | 0.1878 | 0.000 | 0.5721 | 0.286 | 0.500 |
| M_MACRO | 145 | 0.234 | 0.1930 | -0.028 | 0.5621 | 0.711 | 0.593 |

## BULL-only — primary `future_return_12w > 0`

Bull walk-forward ran with min train N=100 (not lowered). Evaluation weeks with enough history: 44.

Full:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 44 | 0.591 | 0.2766 | 0.000 | 0.7648 | 0.368 | 0.500 |
| M_MACRO | 44 | 0.591 | 0.2804 | -0.014 | 0.7753 | 0.669 | 0.500 |

2021–2023:

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 38 | 0.526 | 0.3127 | 0.000 | 0.8463 | 0.311 | 0.500 |
| M_MACRO | 38 | 0.526 | 0.3222 | -0.030 | 0.8768 | 0.589 | 0.500 |

## Decision

**B — MACRO HAS WEAK / CONDITIONAL SIGNAL**

Rule (not softened):

- A if M_MACRO beats M0 on Brier for the primary target on **both** full walk-forward and 2021–2023, **and** non-overlapping median BSS>0 with at least 7 offsets BSS>0.
- B if it beats M0 on some but not all of those primary checks, or only on a secondary / Bull slice.
- C if it does not beat M0 on the primary target in the expanding and validation windows.

Primary full BSS>0: False. Primary 2021–2023 BSS>0: True. Nonoverlap median>0 and ≥7 offsets>0: False. Secondary BSS>0 slices: ['strong_12w/validation_2021_2023']. Bull primary BSS>0: False.

Macro was not combined with crypto. Verdict B is not a license to build a large Crypto+Macro model. A later Crypto vs Macro vs Crypto+Macro test is optional and must stay restricted; this file does not support A.

## Guardrails

- no feature search / no extra macros
- no threshold optimization
- no logistic C search
- no 2024–2026
- min train N not lowered
- Phase 3 / 6A not modified

