# Final clean OOS — MACRO_BASE_CANDIDATE_V1

Exam of the **frozen** Phase 6G candidate on 2024–2026. Not a trading strategy. No spec changes after seeing results.

Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`. Logistic L2 `C=1.0`. L=0. Horizons 4/8/12.
Train: expanding, `s <= t - H`, min N=100. M0 is the expanding mature base rate on the same weeks.

## Data

| item | value |
|---|---|
| last crypto Friday | 2026-08-28 |
| last macro Friday | 2026-08-28 |
| CMC Fridays downloaded | 139 |
| V1 market_return splice max abs err | 9.714e-17 |
| 2015–2023 features | frozen Phase 6A (not re-estimated) |
| crypto source | CMC listings/historical (same as Hsieh tape) |
| dollar | Fed H.10 Nominal Broad Dollar Index (not ICE DXY) |
| 2Y | Fed H.15 |
| real 10Y | Treasury TIPS par real 10Y |
| Nasdaq | Yahoo `^IXIC` |

## Classification

| horizon | class |
|---:|---|
| 4w | FAIL |
| 8w | VALIDATION SUPPORT |
| 12w | VALIDATION SUPPORT |

VALIDATION SUPPORT: clean-OOS BSS>0 **and** non-overlap median BSS>0 with at least half of evaluated offsets BSS>0.
MIXED: BSS>0 but robustness fails, or AUC≥0.60 with BSS≤0 (ranking without good probability forecast).
FAIL: BSS≤0 on clean OOS and no convincing non-overlap support.

## Horizon 4w

### FINAL_CLEAN_OOS_2024_2026

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FINAL_CLEAN_OOS_2024_2026 | M0 | 135 | 0.519 | 0.2547 | 0.000 | 0.7028 | 0.399 | 0.500 |
| FINAL_CLEAN_OOS_2024_2026 | M_MACRO | 135 | 0.519 | 0.2599 | -0.020 | 0.7159 | 0.579 | 0.514 |

### Calendar subperiods (diagnostic only; not used to retune)

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CAL_2024 | M0 | 52 | 0.596 | 0.2420 | 0.000 | 0.6771 | 0.301 | 0.500 |
| CAL_2024 | M_MACRO | 52 | 0.596 | 0.2407 | 0.005 | 0.6780 | 0.598 | 0.546 |
| CAL_2025 | M0 | 52 | 0.442 | 0.2680 | 0.000 | 0.7296 | 0.165 | 0.500 |
| CAL_2025 | M_MACRO | 52 | 0.442 | 0.2748 | -0.025 | 0.7459 | 0.733 | 0.534 |
| CAL_2026_YTD | M0 | 31 | 0.516 | 0.2539 | 0.000 | 0.7010 | 0.146 | 0.500 |
| CAL_2026_YTD | M_MACRO | 31 | 0.516 | 0.2669 | -0.051 | 0.7293 | 0.446 | 0.477 |

### Non-overlapping offsets (clean OOS weeks)

Median BSS=-0.035; min=-0.087; max=0.073; BSS>0: 2/4 evaluated. Class: FAIL.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 34 | 0.2702 | 0.2485 | -0.087 |
| 01 | 33 | 0.2744 | 0.2558 | -0.073 |
| 02 | 34 | 0.2567 | 0.2573 | 0.002 |
| 03 | 34 | 0.2385 | 0.2573 | 0.073 |

## Horizon 8w

### FINAL_CLEAN_OOS_2024_2026

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FINAL_CLEAN_OOS_2024_2026 | M0 | 131 | 0.504 | 0.2620 | 0.000 | 0.7179 | 0.269 | 0.500 |
| FINAL_CLEAN_OOS_2024_2026 | M_MACRO | 131 | 0.504 | 0.2331 | 0.111 | 0.6459 | 0.744 | 0.563 |

### Calendar subperiods (diagnostic only; not used to retune)

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CAL_2024 | M0 | 52 | 0.558 | 0.2524 | 0.000 | 0.6984 | 0.162 | 0.500 |
| CAL_2024 | M_MACRO | 52 | 0.558 | 0.2000 | 0.208 | 0.5713 | 0.772 | 0.549 |
| CAL_2025 | M0 | 52 | 0.481 | 0.2679 | 0.000 | 0.7298 | 0.092 | 0.500 |
| CAL_2025 | M_MACRO | 52 | 0.481 | 0.2419 | 0.097 | 0.6582 | 0.859 | 0.556 |
| CAL_2026_YTD | M0 | 27 | 0.444 | 0.2694 | 0.000 | 0.7324 | 0.306 | 0.500 |
| CAL_2026_YTD | M_MACRO | 27 | 0.444 | 0.2798 | -0.039 | 0.7659 | 0.567 | 0.608 |

### Non-overlapping offsets (clean OOS weeks)

Median BSS=0.100; min=-0.056; max=0.241; BSS>0: 7/8 evaluated. Class: VALIDATION SUPPORT.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 17 | 0.2204 | 0.2575 | 0.144 |
| 01 | 16 | 0.2441 | 0.2756 | 0.114 |
| 02 | 16 | 0.2577 | 0.2759 | 0.066 |
| 03 | 16 | 0.2403 | 0.2630 | 0.086 |
| 04 | 16 | 0.2337 | 0.2366 | 0.012 |
| 05 | 16 | 0.2499 | 0.2366 | -0.056 |
| 06 | 17 | 0.2125 | 0.2801 | 0.241 |
| 07 | 17 | 0.2097 | 0.2697 | 0.223 |

## Horizon 12w

### FINAL_CLEAN_OOS_2024_2026

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FINAL_CLEAN_OOS_2024_2026 | M0 | 127 | 0.480 | 0.2669 | 0.000 | 0.7277 | 0.282 | 0.500 |
| FINAL_CLEAN_OOS_2024_2026 | M_MACRO | 127 | 0.480 | 0.2221 | 0.168 | 0.6203 | 0.831 | 0.611 |

### Calendar subperiods (diagnostic only; not used to retune)

| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CAL_2024 | M0 | 52 | 0.615 | 0.2399 | 0.000 | 0.6730 | 0.077 | 0.500 |
| CAL_2024 | M_MACRO | 52 | 0.615 | 0.1381 | 0.424 | 0.4345 | 0.916 | 0.753 |
| CAL_2025 | M0 | 52 | 0.423 | 0.2817 | 0.000 | 0.7580 | 0.114 | 0.500 |
| CAL_2025 | M_MACRO | 52 | 0.423 | 0.2797 | 0.007 | 0.7441 | 0.882 | 0.550 |
| CAL_2026_YTD | M0 | 23 | 0.304 | 0.2943 | 0.000 | 0.7829 | 0.616 | 0.500 |
| CAL_2026_YTD | M_MACRO | 23 | 0.304 | 0.2816 | 0.043 | 0.7605 | 0.732 | 0.513 |

### Non-overlapping offsets (clean OOS weeks)

Median BSS=0.153; min=-0.087; max=0.435; BSS>0: 9/12 evaluated. Class: VALIDATION SUPPORT.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 10 | 0.2626 | 0.3045 | 0.138 |
| 01 | 10 | 0.2806 | 0.3033 | 0.075 |
| 02 | 11 | 0.2418 | 0.2903 | 0.167 |
| 03 | 11 | 0.1572 | 0.2527 | 0.378 |
| 04 | 11 | 0.1498 | 0.2530 | 0.408 |
| 05 | 11 | 0.1431 | 0.2533 | 0.435 |
| 06 | 11 | 0.1563 | 0.2331 | 0.330 |
| 07 | 11 | 0.1774 | 0.2169 | 0.182 |
| 08 | 11 | 0.2386 | 0.2544 | 0.062 |
| 09 | 10 | 0.2645 | 0.2629 | -0.006 |
| 10 | 10 | 0.2904 | 0.2843 | -0.022 |
| 11 | 10 | 0.3316 | 0.3051 | -0.087 |

## Answers

1. Does MACRO_BASE_CANDIDATE_V1 beat M0 in 2024–2026? Yes on BSS at horizon(s) 8w, 12w.
2. At which horizons, if any?
   - 4w: BSS=-0.020 N=135 class=FAIL.
   - 8w: BSS=0.111 N=131 class=VALIDATION SUPPORT.
   - 12w: BSS=0.168 N=127 class=VALIDATION SUPPORT.
3. Does it survive non-overlapping evaluation?
   - 4w: median BSS=-0.035; 2/4 offsets BSS>0; survive=False.
   - 8w: median BSS=0.100; 7/8 offsets BSS>0; survive=True.
   - 12w: median BSS=0.153; 9/12 offsets BSS>0; survive=True.
4. Is the 2021–2023 signal replicated?
   Partially. 2021–2023 was PSEUDO-OOS: BSS>0 at 4/8/12w, but full-sample walk-forward and non-overlap failed. Clean OOS 2024–2026 replicates 8w and 12w (BSS>0 and non-overlap support) and does not replicate 4w (BSS≤0). 12w offset N is 10–11 (at the reporting floor); do not overinterpret those slices. Do not treat the 4w failure as a license to retune.
5. Is the macro block useful enough to retain as part of the future market-reading framework? Yes, as a market-reading block at the horizons with VALIDATION SUPPORT. It is not a trading signal. 4w remains unused as a predictive slice.
6. Should MACRO_BASE_CANDIDATE_V1 be: **RETAINED**

## Decision

**RETAINED**

Not a trading strategy. Entry/exit research is out of scope. The candidate spec was not changed after seeing these numbers.

## Guardrails

- no dropped features / C / lag / horizon / crypto / regime / cutoff
- 2015–2023 frozen history spliced, not rewritten
- no silent source substitution

