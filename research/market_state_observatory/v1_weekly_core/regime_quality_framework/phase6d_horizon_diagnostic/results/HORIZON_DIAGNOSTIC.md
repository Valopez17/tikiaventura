# H1 — Horizon diagnostic (CRYPTO vs MACRO at 4w / 8w / 12w)

Question: does frozen crypto-only or frozen macro-only information improve the probability that the subsequent H-week market return is positive, versus an expanding mature base rate, and does that pattern change with horizon?

No combined model. No feature search. No lag search. No regime slices. No 2024–2026. Not a trading backtest. Not a model A/B/C verdict.

Mature labels: train `s <= t - H`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.

M_CRYPTO: `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE`.
M_MACRO: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.
Same features at every horizon.

Only target: `Y_H = 1` if `future_return_Hw > 0`.

`future_return_8w` is derived from catalog `future_return_4w` as `(1+r4_t)*(1+r4_{t+4})-1` (exclusive t+1…t+8). No new crypto download.

2021–2023 is labeled **TEMPORAL_ROBUSTNESS_2021_2023**. It is not clean OOS. Prior phases already inspected this window.

Classification (no A/B/C):

- PROMISING: BSS>0 on full expanding WF **and** 2021–2023, and non-overlapping median BSS>0 with at least half of offsets BSS>0.
- WEAK: BSS>0 on full **or** 2021–2023, but not both, or both but the non-overlapping layer fails.
- NO EDGE: BSS≤0 on full **and** 2021–2023.
- If AUC≥0.60 and BSS<0: RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST.

## Sample

| item | value |
|---|---|
| merged weeks | 470 |
| last week | 2023-12-29 |
| 2024+ | none |
| complete 4w outcomes | 442 |
| complete 8w outcomes | 438 |
| complete 12w outcomes | 434 |
| crypto dynamics | Phase 4 formula on the catalog; Phase 4 values overlaid on Bull weeks |
| common eval set | M0 / M_CRYPTO / M_MACRO scored on the same mature weeks per horizon |

## Horizon 4w — `future_return_4w > 0`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 339 | 0.537 | 0.2644 | 0.000 | 0.7249 | 0.405 | 0.500 |
| M_CRYPTO | 339 | 0.537 | 0.2768 | -0.047 | 0.7691 | 0.491 | 0.494 |
| M_MACRO | 339 | 0.537 | 0.2716 | -0.027 | 0.7677 | 0.562 | 0.553 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 153 | 0.529 | 0.2573 | 0.000 | 0.7084 | 0.405 | 0.500 |
| M_CRYPTO | 153 | 0.529 | 0.2576 | -0.001 | 0.7092 | 0.525 | 0.463 |
| M_MACRO | 153 | 0.529 | 0.2284 | 0.112 | 0.6506 | 0.676 | 0.654 |

### Non-overlapping 4-week offsets (full walk-forward)

| model | offsets | median BSS | min | max | offsets BSS>0 | class |
|---|---:|---:|---:|---:|---:|---|
| M_CRYPTO | 4 | -0.048 | -0.073 | -0.018 | 0/4 | NO EDGE |
| M_MACRO | 4 | -0.030 | -0.059 | 0.008 | 1/4 | WEAK |

#### M_CRYPTO offsets

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 85 | 0.2711 | 0.2585 | -0.049 |
| 01 | 85 | 0.2758 | 0.2570 | -0.073 |
| 02 | 84 | 0.2720 | 0.2671 | -0.018 |
| 03 | 85 | 0.2880 | 0.2752 | -0.047 |

#### M_MACRO offsets

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 85 | 0.2702 | 0.2585 | -0.045 |
| 01 | 85 | 0.2721 | 0.2570 | -0.059 |
| 02 | 84 | 0.2709 | 0.2671 | -0.014 |
| 03 | 85 | 0.2731 | 0.2752 | 0.008 |

## Horizon 8w — `future_return_8w > 0`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 331 | 0.538 | 0.2748 | 0.000 | 0.7509 | 0.386 | 0.500 |
| M_CRYPTO | 331 | 0.538 | 0.3091 | -0.125 | 0.8523 | 0.385 | 0.453 |
| M_MACRO | 331 | 0.538 | 0.2888 | -0.051 | 0.8716 | 0.545 | 0.514 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 149 | 0.523 | 0.2634 | 0.000 | 0.7213 | 0.371 | 0.500 |
| M_CRYPTO | 149 | 0.523 | 0.2824 | -0.072 | 0.7640 | 0.328 | 0.449 |
| M_MACRO | 149 | 0.523 | 0.2286 | 0.132 | 0.6479 | 0.654 | 0.583 |

### Non-overlapping 8-week offsets (full walk-forward)

| model | offsets | median BSS | min | max | offsets BSS>0 | class |
|---|---:|---:|---:|---:|---:|---|
| M_CRYPTO | 8 | -0.129 | -0.208 | -0.023 | 0/8 | NO EDGE |
| M_MACRO | 8 | -0.047 | -0.156 | 0.081 | 1/8 | WEAK |

#### M_CRYPTO offsets

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 41 | 0.2822 | 0.2337 | -0.208 |
| 01 | 41 | 0.2905 | 0.2647 | -0.097 |
| 02 | 41 | 0.3252 | 0.2896 | -0.123 |
| 03 | 42 | 0.3291 | 0.2932 | -0.123 |
| 04 | 42 | 0.3173 | 0.2796 | -0.135 |
| 05 | 42 | 0.3272 | 0.2823 | -0.159 |
| 06 | 41 | 0.3175 | 0.2783 | -0.141 |
| 07 | 41 | 0.2827 | 0.2763 | -0.023 |

#### M_MACRO offsets

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

## Horizon 12w — `future_return_12w > 0`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 323 | 0.505 | 0.3014 | 0.000 | 0.8198 | 0.336 | 0.500 |
| M_CRYPTO | 323 | 0.505 | 0.3399 | -0.128 | 0.9635 | 0.392 | 0.390 |
| M_MACRO | 323 | 0.505 | 0.3247 | -0.077 | 1.1071 | 0.507 | 0.530 |

### TEMPORAL_ROBUSTNESS_2021_2023

| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.469 | 0.2806 | 0.000 | 0.7569 | 0.356 | 0.500 |
| M_CRYPTO | 145 | 0.469 | 0.3029 | -0.080 | 0.8133 | 0.385 | 0.401 |
| M_MACRO | 145 | 0.469 | 0.2327 | 0.170 | 0.6651 | 0.690 | 0.641 |

### Non-overlapping 12-week offsets (full walk-forward)

| model | offsets | median BSS | min | max | offsets BSS>0 | class |
|---|---:|---:|---:|---:|---:|---|
| M_CRYPTO | 12 | -0.147 | -0.243 | -0.010 | 0/12 | NO EDGE |
| M_MACRO | 12 | -0.092 | -0.173 | 0.048 | 1/12 | WEAK |

#### M_CRYPTO offsets

| offset | N | brier | brier M0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 27 | 0.3206 | 0.3110 | -0.031 |
| 01 | 27 | 0.3131 | 0.2993 | -0.046 |
| 02 | 26 | 0.3469 | 0.3277 | -0.059 |
| 03 | 27 | 0.3456 | 0.3039 | -0.137 |
| 04 | 27 | 0.3417 | 0.2880 | -0.186 |
| 05 | 27 | 0.3440 | 0.2797 | -0.230 |
| 06 | 27 | 0.3305 | 0.2658 | -0.243 |
| 07 | 27 | 0.3637 | 0.2961 | -0.228 |
| 08 | 27 | 0.3621 | 0.2995 | -0.209 |
| 09 | 27 | 0.3524 | 0.3044 | -0.158 |
| 10 | 27 | 0.3476 | 0.3349 | -0.038 |
| 11 | 27 | 0.3104 | 0.3073 | -0.010 |

#### M_MACRO offsets

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

## Classification

| horizon | M_CRYPTO | M_MACRO |
|---:|---|---|
| 4w | NO EDGE | WEAK |
| 8w | NO EDGE | WEAK |
| 12w | NO EDGE | WEAK |

## Answers

1. At 4w, does CRYPTO beat M0? Full BSS>0: False (-0.047). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: False (-0.001). Class: NO EDGE.
2. At 4w, does MACRO beat M0? Full BSS>0: False (-0.027). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.112). Class: WEAK.
3. At 8w, does CRYPTO beat M0? Full BSS>0: False (-0.125). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: False (-0.072). Class: NO EDGE.
4. At 8w, does MACRO beat M0? Full BSS>0: False (-0.051). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.132). Class: WEAK.
5. At 12w, does CRYPTO beat M0? Full BSS>0: False (-0.128). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: False (-0.080). Class: NO EDGE.
6. At 12w, does MACRO beat M0? Full BSS>0: False (-0.077). TEMPORAL_ROBUSTNESS_2021_2023 BSS>0: True (0.170). Class: WEAK.

7. Which source of information is strongest at each horizon?
   - 4w: MACRO (WEAK) over CRYPTO (NO EDGE)
   - 8w: MACRO (WEAK) over CRYPTO (NO EDGE)
   - 12w: MACRO (WEAK) over CRYPTO (NO EDGE)

8. Does either model show a monotonic degradation or improvement as horizon increases?
   - M_CRYPTO: full BSS: degrades as horizon lengthens (4→8→12); 2021–2023 BSS: degrades as horizon lengthens (4→8→12)
   - M_MACRO: full BSS: degrades as horizon lengthens (4→8→12); 2021–2023 BSS: improves as horizon lengthens (4→8→12)
   No horizon is selected as 'best' from a single pretty metric.

9. Does apparent performance survive the non-overlapping check?
   No. No horizon/source clears majority-and-median BSS>0 together with a positive skill window.
   - M_CRYPTO 4w: median BSS=-0.048, 0/4 offsets BSS>0, survives majority-and-median rule: False
   - M_MACRO 4w: median BSS=-0.030, 1/4 offsets BSS>0, survives majority-and-median rule: False
   - M_CRYPTO 8w: median BSS=-0.129, 0/8 offsets BSS>0, survives majority-and-median rule: False
   - M_MACRO 8w: median BSS=-0.047, 1/8 offsets BSS>0, survives majority-and-median rule: False
   - M_CRYPTO 12w: median BSS=-0.147, 0/12 offsets BSS>0, survives majority-and-median rule: False
   - M_MACRO 12w: median BSS=-0.092, 1/12 offsets BSS>0, survives majority-and-median rule: False

10. Is there evidence that crypto works better short-term, macro works better medium-term, or neither pattern is supported?
    Neither pattern is supported as a horizon effect. CRYPTO never beats M0 at 4w, 8w, or 12w (NO EDGE). Its Brier is least bad at 4w; that is not a short-term crypto edge. MACRO is WEAK at every horizon: 2021–2023 BSS is positive at 4w, 8w, and 12w, while full-sample BSS and non-overlapping median BSS are negative at every horizon. That is a 2021–2023 period effect, not evidence that macro works better at medium term.

## Decision

No A/B/C model verdict. Horizon/source classes are in the table above.
Do not freeze a candidate from this diagnostic alone.

## Guardrails

- no combined Crypto+Macro model
- no lag search / interactions / extra features / extra targets
- no Bull/Bear slices
- no 2024–2026
- Phase 3 / 4 / 6A not modified

