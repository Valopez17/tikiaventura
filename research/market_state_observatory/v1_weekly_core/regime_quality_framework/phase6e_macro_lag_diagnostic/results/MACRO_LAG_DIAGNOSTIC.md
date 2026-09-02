# H2 — Macro lag diagnostic

Question: is the frozen four-feature macro block at week t more useful for crypto returns that start immediately, after 4 weeks, or after 8 weeks?

No crypto features. No extra lags. No extra horizons. No 2024–2026. Not a trading backtest. Not an A/B/C model verdict. This is not a lag *search*: the grid is pre-specified.

Outcome window: exclusive `t+L+1 … t+L+H`. Target: return > 0.
Train: `s <= t - (L+H)`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.
Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.
Windows chained from catalog `future_return_4w`. 2021–2023 is **TEMPORAL_ROBUSTNESS_2021_2023**, not clean OOS.

Classification:

- PROMISING: BSS>0 on full expanding WF **and** 2021–2023, and non-overlapping median BSS>0 with at least half of offsets BSS>0.
- WEAK: BSS>0 on full **or** 2021–2023, but not both, or both but non-overlap fails.
- NO EDGE: BSS≤0 on full **and** 2021–2023.
- If AUC≥0.60 and BSS<0: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST.

## Sample

| item | value |
|---|---|
| merged weeks | 470 |
| last week | 2023-12-29 |
| 2024+ | none |
| complete L=0 H=4 outcomes | 442 |
| complete L=0 H=8 outcomes | 438 |
| complete L=0 H=12 outcomes | 434 |
| complete L=4 H=4 outcomes | 442 |
| complete L=4 H=8 outcomes | 438 |
| complete L=4 H=12 outcomes | 434 |
| complete L=8 H=4 outcomes | 442 |
| complete L=8 H=8 outcomes | 438 |
| complete L=8 H=12 outcomes | 434 |
| common eval set | M0 and M_MACRO scored on the same mature weeks per cell |

## Classification grid

| L \ H | 4w | 8w | 12w |
|---:|---|---|---|
| 0 | WEAK | WEAK | WEAK |
| 4 | WEAK | WEAK | WEAK |
| 8 | WEAK | NO EDGE | NO EDGE |

## BSS grid — full expanding walk-forward

| L \ H | 4w | 8w | 12w |
|---:|---:|---:|---:|
| 0 | -0.027 | -0.051 | -0.077 |
| 4 | -0.075 | -0.110 | -0.159 |
| 8 | -0.096 | -0.199 | -0.254 |

## BSS grid — TEMPORAL_ROBUSTNESS_2021_2023

| L \ H | 4w | 8w | 12w |
|---:|---:|---:|---:|
| 0 | 0.112 | 0.132 | 0.170 |
| 4 | 0.082 | 0.070 | 0.031 |
| 8 | 0.019 | -0.077 | -0.098 |

## L=0, H=4 — window t+0+1 … t+0+4

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 339 | 0.537 | 0.2644 | 0.000 | 0.7249 | 0.405 | 0.500 |
| M_MACRO | 339 | 0.537 | 0.2716 | -0.027 | 0.7677 | 0.562 | 0.553 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 153 | 0.529 | 0.2573 | 0.000 | 0.7084 | 0.405 | 0.500 |
| M_MACRO | 153 | 0.529 | 0.2284 | 0.112 | 0.6506 | 0.676 | 0.654 |

### Non-overlapping 4-week offsets (full walk-forward)

Median BSS=-0.030; min=-0.059; max=0.008; offsets BSS>0: 1/4. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 85 | 0.2702 | 0.2585 | -0.045 |
| 01 | 85 | 0.2721 | 0.2570 | -0.059 |
| 02 | 84 | 0.2709 | 0.2671 | -0.014 |
| 03 | 85 | 0.2731 | 0.2752 | 0.008 |

## L=0, H=8 — window t+0+1 … t+0+8

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 331 | 0.538 | 0.2748 | 0.000 | 0.7509 | 0.386 | 0.500 |
| M_MACRO | 331 | 0.538 | 0.2888 | -0.051 | 0.8716 | 0.545 | 0.514 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 149 | 0.523 | 0.2634 | 0.000 | 0.7213 | 0.371 | 0.500 |
| M_MACRO | 149 | 0.523 | 0.2286 | 0.132 | 0.6479 | 0.654 | 0.583 |

### Non-overlapping 8-week offsets (full walk-forward)

Median BSS=-0.047; min=-0.156; max=0.081; offsets BSS>0: 1/8. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 41 | 0.2405 | 0.2337 | -0.029 |
| 01 | 41 | 0.3061 | 0.2647 | -0.156 |
| 02 | 41 | 0.3051 | 0.2896 | -0.054 |
| 03 | 42 | 0.3230 | 0.2932 | -0.102 |
| 04 | 42 | 0.2894 | 0.2796 | -0.035 |
| 05 | 42 | 0.3018 | 0.2823 | -0.069 |
| 06 | 41 | 0.2896 | 0.2783 | -0.040 |
| 07 | 41 | 0.2538 | 0.2763 | 0.081 |

## L=0, H=12 — window t+0+1 … t+0+12

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.505 | 0.3014 | 0.000 | 0.8198 | 0.336 | 0.500 |
| M_MACRO | 323 | 0.505 | 0.3247 | -0.077 | 1.1071 | 0.507 | 0.530 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.469 | 0.2806 | 0.000 | 0.7569 | 0.356 | 0.500 |
| M_MACRO | 145 | 0.469 | 0.2327 | 0.170 | 0.6651 | 0.690 | 0.641 |

### Non-overlapping 12-week offsets (full walk-forward)

Median BSS=-0.092; min=-0.173; max=0.048; offsets BSS>0: 1/12. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
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

## L=4, H=4 — window t+4+1 … t+4+4

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 335 | 0.543 | 0.2618 | 0.000 | 0.7191 | 0.413 | 0.500 |
| M_MACRO | 335 | 0.543 | 0.2814 | -0.075 | 0.8057 | 0.528 | 0.543 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 149 | 0.517 | 0.2606 | 0.000 | 0.7151 | 0.402 | 0.500 |
| M_MACRO | 149 | 0.517 | 0.2391 | 0.082 | 0.6719 | 0.638 | 0.585 |

### Non-overlapping 4-week offsets (full walk-forward)

Median BSS=-0.080; min=-0.118; max=-0.025; offsets BSS>0: 0/4. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 84 | 0.2863 | 0.2561 | -0.118 |
| 01 | 84 | 0.2801 | 0.2540 | -0.103 |
| 02 | 83 | 0.2705 | 0.2638 | -0.025 |
| 03 | 84 | 0.2887 | 0.2734 | -0.056 |

## L=4, H=8 — window t+4+1 … t+4+8

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 327 | 0.532 | 0.2789 | 0.000 | 0.7607 | 0.379 | 0.500 |
| M_MACRO | 327 | 0.532 | 0.3095 | -0.110 | 0.9245 | 0.457 | 0.497 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.510 | 0.2662 | 0.000 | 0.7270 | 0.400 | 0.500 |
| M_MACRO | 145 | 0.510 | 0.2476 | 0.070 | 0.6893 | 0.605 | 0.576 |

### Non-overlapping 8-week offsets (full walk-forward)

Median BSS=-0.110; min=-0.208; max=-0.056; offsets BSS>0: 0/8. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 41 | 0.3061 | 0.2876 | -0.064 |
| 01 | 41 | 0.3318 | 0.2905 | -0.142 |
| 02 | 40 | 0.3180 | 0.2851 | -0.115 |
| 03 | 41 | 0.2945 | 0.2790 | -0.056 |
| 04 | 41 | 0.2588 | 0.2337 | -0.108 |
| 05 | 41 | 0.3196 | 0.2647 | -0.208 |
| 06 | 41 | 0.3133 | 0.2904 | -0.079 |
| 07 | 41 | 0.3342 | 0.3004 | -0.113 |

## L=4, H=12 — window t+4+1 … t+4+12

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 319 | 0.498 | 0.3085 | 0.000 | 0.8394 | 0.325 | 0.500 |
| M_MACRO | 319 | 0.498 | 0.3577 | -0.159 | 1.2029 | 0.439 | 0.481 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 141 | 0.454 | 0.2850 | 0.000 | 0.7659 | 0.385 | 0.500 |
| M_MACRO | 141 | 0.454 | 0.2762 | 0.031 | 0.7696 | 0.591 | 0.537 |

### Non-overlapping 12-week offsets (full walk-forward)

Median BSS=-0.159; min=-0.294; max=0.008; offsets BSS>0: 1/12. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 26 | 0.3465 | 0.3021 | -0.147 |
| 01 | 26 | 0.3713 | 0.2934 | -0.265 |
| 02 | 26 | 0.3209 | 0.2783 | -0.153 |
| 03 | 27 | 0.3878 | 0.2996 | -0.294 |
| 04 | 27 | 0.3564 | 0.3026 | -0.178 |
| 05 | 27 | 0.3711 | 0.3071 | -0.208 |
| 06 | 27 | 0.3533 | 0.3395 | -0.041 |
| 07 | 27 | 0.3557 | 0.3114 | -0.142 |
| 08 | 27 | 0.3844 | 0.3152 | -0.220 |
| 09 | 27 | 0.3010 | 0.3033 | 0.008 |
| 10 | 26 | 0.3730 | 0.3306 | -0.128 |
| 11 | 26 | 0.3708 | 0.3185 | -0.164 |

## L=8, H=4 — window t+8+1 … t+8+4

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 331 | 0.538 | 0.2658 | 0.000 | 0.7281 | 0.395 | 0.500 |
| M_MACRO | 331 | 0.538 | 0.2912 | -0.096 | 0.8224 | 0.492 | 0.504 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.503 | 0.2637 | 0.000 | 0.7213 | 0.409 | 0.500 |
| M_MACRO | 145 | 0.503 | 0.2586 | 0.019 | 0.7147 | 0.574 | 0.502 |

### Non-overlapping 4-week offsets (full walk-forward)

Median BSS=-0.111; min=-0.124; max=-0.036; offsets BSS>0: 0/4. Class: WEAK.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 83 | 0.2893 | 0.2589 | -0.118 |
| 01 | 83 | 0.2842 | 0.2574 | -0.104 |
| 02 | 82 | 0.2780 | 0.2684 | -0.036 |
| 03 | 83 | 0.3131 | 0.2786 | -0.124 |

## L=8, H=8 — window t+8+1 … t+8+8

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.526 | 0.2830 | 0.000 | 0.7702 | 0.380 | 0.500 |
| M_MACRO | 323 | 0.526 | 0.3391 | -0.199 | 0.9887 | 0.370 | 0.432 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 141 | 0.496 | 0.2688 | 0.000 | 0.7321 | 0.452 | 0.500 |
| M_MACRO | 141 | 0.496 | 0.2894 | -0.077 | 0.7778 | 0.421 | 0.463 |

### Non-overlapping 8-week offsets (full walk-forward)

Median BSS=-0.204; min=-0.266; max=-0.150; offsets BSS>0: 0/8. Class: NO EDGE.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 40 | 0.2902 | 0.2390 | -0.214 |
| 01 | 40 | 0.3257 | 0.2715 | -0.200 |
| 02 | 40 | 0.3431 | 0.2984 | -0.150 |
| 03 | 41 | 0.3484 | 0.3016 | -0.155 |
| 04 | 41 | 0.3648 | 0.2881 | -0.266 |
| 05 | 41 | 0.3521 | 0.2913 | -0.209 |
| 06 | 40 | 0.3317 | 0.2854 | -0.162 |
| 07 | 40 | 0.3558 | 0.2876 | -0.237 |

## L=8, H=12 — window t+8+1 … t+8+12

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 315 | 0.492 | 0.3150 | 0.000 | 0.8573 | 0.321 | 0.500 |
| M_MACRO | 315 | 0.492 | 0.3950 | -0.254 | 1.2160 | 0.368 | 0.382 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 137 | 0.438 | 0.2894 | 0.000 | 0.7749 | 0.429 | 0.500 |
| M_MACRO | 137 | 0.438 | 0.3177 | -0.098 | 0.8417 | 0.408 | 0.379 |

### Non-overlapping 12-week offsets (full walk-forward)

Median BSS=-0.273; min=-0.356; max=-0.122; offsets BSS>0: 0/12. Class: NO EDGE.

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 26 | 0.4068 | 0.3179 | -0.280 |
| 01 | 26 | 0.4165 | 0.3220 | -0.294 |
| 02 | 26 | 0.4335 | 0.3553 | -0.220 |
| 03 | 27 | 0.4108 | 0.3140 | -0.308 |
| 04 | 27 | 0.4024 | 0.3171 | -0.269 |
| 05 | 27 | 0.3549 | 0.3048 | -0.164 |
| 06 | 26 | 0.3733 | 0.3328 | -0.122 |
| 07 | 26 | 0.3913 | 0.3208 | -0.220 |
| 08 | 26 | 0.3900 | 0.3052 | -0.278 |
| 09 | 26 | 0.4007 | 0.2955 | -0.356 |
| 10 | 26 | 0.3375 | 0.2815 | -0.199 |
| 11 | 26 | 0.4232 | 0.3139 | -0.348 |

## Answers

Grid: 0 PROMISING, 7 WEAK, 2 NO EDGE out of 9 cells.

1. L=0, H=4: does M_MACRO beat M0? Full BSS>0: False (-0.027). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.112). Class: WEAK.
2. L=4, H=4: does M_MACRO beat M0? Full BSS>0: False (-0.075). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.082). Class: WEAK.
3. L=8, H=4: does M_MACRO beat M0? Full BSS>0: False (-0.096). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.019). Class: WEAK.
4. L=0, H=8: does M_MACRO beat M0? Full BSS>0: False (-0.051). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.132). Class: WEAK.
5. L=4, H=8: does M_MACRO beat M0? Full BSS>0: False (-0.110). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.070). Class: WEAK.
6. L=8, H=8: does M_MACRO beat M0? Full BSS>0: False (-0.199). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: False (-0.077). Class: NO EDGE.
7. L=0, H=12: does M_MACRO beat M0? Full BSS>0: False (-0.077). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.170). Class: WEAK.
8. L=4, H=12: does M_MACRO beat M0? Full BSS>0: False (-0.159). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.031). Class: WEAK.
9. L=8, H=12: does M_MACRO beat M0? Full BSS>0: False (-0.254). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: False (-0.098). Class: NO EDGE.

10. Does delayed macro (L=4 or L=8) beat contemporaneous macro (L=0) at the same H?
   - H=4: L=4 vs L=0: ΔBSS full=-0.048, ΔBSS 2021–2023=-0.030 (positive means delayed is better); L=8 vs L=0: ΔBSS full=-0.069, ΔBSS 2021–2023=-0.093 (positive means delayed is better)
   - H=8: L=4 vs L=0: ΔBSS full=-0.059, ΔBSS 2021–2023=-0.062 (positive means delayed is better); L=8 vs L=0: ΔBSS full=-0.148, ΔBSS 2021–2023=-0.209 (positive means delayed is better)
   - H=12: L=4 vs L=0: ΔBSS full=-0.082, ΔBSS 2021–2023=-0.140 (positive means delayed is better); L=8 vs L=0: ΔBSS full=-0.177, ΔBSS 2021–2023=-0.268 (positive means delayed is better)

11. Does any lag/horizon survive the non-overlapping check?
    No. No cell clears majority-and-median BSS>0 together with a positive skill window.
    - L=0 H=4: median BSS=-0.030, 1/4 offsets BSS>0, survive=False
    - L=0 H=8: median BSS=-0.047, 1/8 offsets BSS>0, survive=False
    - L=0 H=12: median BSS=-0.092, 1/12 offsets BSS>0, survive=False
    - L=4 H=4: median BSS=-0.080, 0/4 offsets BSS>0, survive=False
    - L=4 H=8: median BSS=-0.110, 0/8 offsets BSS>0, survive=False
    - L=4 H=12: median BSS=-0.159, 1/12 offsets BSS>0, survive=False
    - L=8 H=4: median BSS=-0.111, 0/4 offsets BSS>0, survive=False
    - L=8 H=8: median BSS=-0.204, 0/8 offsets BSS>0, survive=False
    - L=8 H=12: median BSS=-0.273, 0/12 offsets BSS>0, survive=False

12. Is there evidence that macro works with a delay rather than contemporaneously?
    Delayed windows are not better than L=0. Macro at t is not more informative for crypto returns that start 4–8 weeks later than for returns that start immediately, under this frozen spec.

## Decision

No A/B/C model verdict. No lag is frozen. Classes are in the grid above.
Do not pick a 'best' lag from a single pretty metric.

## Guardrails

- no crypto features
- no extra lags / horizons / interactions / C search
- no 2024–2026
- H1 files not modified
- Phase 3 / 6A not modified

