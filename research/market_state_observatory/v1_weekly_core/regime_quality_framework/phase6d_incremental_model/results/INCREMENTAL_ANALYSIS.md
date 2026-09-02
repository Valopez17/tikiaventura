# Phase 6D — Incremental walk-forward (CRYPTO vs MACRO vs COMBINED)

Question: does concatenating the frozen macro set to a reduced crypto set improve 12w probability forecasts versus crypto alone, macro alone, and an expanding base rate?

No feature search. No interactions. No 2024–2026. Not a trading backtest. Not the old Phase 5 M3.

Mature labels: train `s <= t - 12`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.

CRYPTO: `MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`, `BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE`.
MACRO: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.
COMBINED: CRYPTO + MACRO, concatenated.

## Sample

| item | value |
|---|---|
| merged weeks | 470 |
| last week | 2023-12-29 |
| 2024+ | none |
| complete 12w outcomes | 434 |
| crypto dynamics | Phase 4 formula on the catalog; Phase 4 values overlaid on Bull weeks |

## Primary `future_return_12w > 0`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs C0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 323 | 0.505 | 0.3014 | 0.000 | 0.8198 | 0.336 | 0.500 |
| CRYPTO | 323 | 0.505 | 0.3399 | -0.128 | 0.9635 | 0.392 | 0.390 |
| MACRO | 323 | 0.505 | 0.3247 | -0.077 | 1.1071 | 0.507 | 0.530 |
| COMBINED | 323 | 0.505 | 0.3557 | -0.180 | 1.3254 | 0.451 | 0.475 |

### 2021–2023 validation

| model | N | prevalence | brier | BSS vs C0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 145 | 0.469 | 0.2806 | 0.000 | 0.7569 | 0.356 | 0.500 |
| CRYPTO | 145 | 0.469 | 0.3029 | -0.080 | 0.8133 | 0.385 | 0.401 |
| MACRO | 145 | 0.469 | 0.2327 | 0.170 | 0.6651 | 0.690 | 0.641 |
| COMBINED | 145 | 0.469 | 0.2627 | 0.064 | 0.7362 | 0.601 | 0.559 |

### Incremental test (2021–2023) — COMBINED minus comparator

Negative delta means COMBINED is better. No significance test.

| comparison | delta Brier | delta log loss | COMBINED better on Brier? |
|---|---:|---:|---|
| COMBINED vs CRYPTO | -0.0402 | -0.0771 | True |
| COMBINED vs MACRO | 0.0299 | 0.0711 | False |

### Non-overlapping 12-week offsets (primary, full walk-forward)

| model | offsets | median BSS | min | max | offsets BSS>0 |
|---|---:|---:|---:|---:|---:|
| CRYPTO | 12 | -0.147 | -0.243 | -0.010 | 0/12 |
| MACRO | 12 | -0.092 | -0.173 | 0.048 | 1/12 |
| COMBINED | 12 | -0.222 | -0.370 | -0.032 | 0/12 |

#### CRYPTO offsets

| offset | N | brier | brier C0 | BSS |
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

#### MACRO offsets

| offset | N | brier | brier C0 | BSS |
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

#### COMBINED offsets

| offset | N | brier | brier C0 | BSS |
|---:|---:|---:|---:|---:|
| 00 | 27 | 0.3263 | 0.3110 | -0.049 |
| 01 | 27 | 0.3089 | 0.2993 | -0.032 |
| 02 | 26 | 0.3824 | 0.3277 | -0.167 |
| 03 | 27 | 0.3744 | 0.3039 | -0.232 |
| 04 | 27 | 0.3626 | 0.2880 | -0.259 |
| 05 | 27 | 0.3832 | 0.2797 | -0.370 |
| 06 | 27 | 0.3245 | 0.2658 | -0.221 |
| 07 | 27 | 0.3855 | 0.2961 | -0.302 |
| 08 | 27 | 0.3677 | 0.2995 | -0.228 |
| 09 | 27 | 0.3720 | 0.3044 | -0.222 |
| 10 | 27 | 0.3467 | 0.3349 | -0.035 |
| 11 | 27 | 0.3346 | 0.3073 | -0.089 |

## Secondary `future_return_12w > +20%`

### Full expanding walk-forward

| model | N | prevalence | brier | BSS vs C0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 323 | 0.375 | 0.2731 | 0.000 | 0.7414 | 0.392 | 0.482 |
| CRYPTO | 323 | 0.375 | 0.3121 | -0.143 | 0.8436 | 0.395 | 0.443 |
| MACRO | 323 | 0.375 | 0.3028 | -0.109 | 0.8887 | 0.557 | 0.556 |
| COMBINED | 323 | 0.375 | 0.3318 | -0.215 | 1.0548 | 0.493 | 0.524 |

### 2021–2023 validation

| model | N | prevalence | brier | BSS vs C0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 145 | 0.297 | 0.2529 | 0.000 | 0.6989 | 0.396 | 0.506 |
| CRYPTO | 145 | 0.297 | 0.2835 | -0.121 | 0.7643 | 0.305 | 0.394 |
| MACRO | 145 | 0.297 | 0.2153 | 0.149 | 0.6171 | 0.667 | 0.609 |
| COMBINED | 145 | 0.297 | 0.2521 | 0.003 | 0.6963 | 0.556 | 0.519 |

Incremental on secondary, 2021–2023 (descriptive only):

| comparison | delta Brier | delta log loss |
|---|---:|---:|
| COMBINED vs CRYPTO | -0.0313 | -0.0680 |
| COMBINED vs MACRO | 0.0368 | 0.0791 |

## Answers

1. Does CRYPTO beat base rate? Full BSS>0: False. 2021–2023 BSS>0: False.
2. Does MACRO beat base rate? Full BSS>0: False. 2021–2023 BSS>0: True.
3. Does COMBINED beat base rate? Full BSS>0: False. 2021–2023 BSS>0: True.
4. Does COMBINED beat CRYPTO (2021–2023 Brier)? True (Δbrier=-0.0402).
5. Does COMBINED beat MACRO (2021–2023 Brier)? False (Δbrier=0.0299).
6. Does any COMBINED advantage survive non-overlapping offsets? Median BSS=-0.222; offsets BSS>0: 0/12. Majority-and-median rule: False.
7. Is macro incremental, or is it just replacing weak crypto information? COMBINED beats CRYPTO but loses to MACRO. CRYPTO itself does not beat C0. Concatenating macro onto a weak crypto block improves the weak block; it does not beat macro-only. That is replacing weak crypto information, not an incremental combined model.
8. Is there enough evidence to freeze a candidate Model A? No. Do not freeze a candidate Model A. COMBINED is worse than MACRO on 2021–2023 Brier and worse than C0 on the full walk-forward and on all 12 non-overlapping offsets.

## Decision

**C — COMBINED DOES NOT ADD VALUE**

Rule:

- A if COMBINED beats C0 on primary full **and** 2021–2023, beats CRYPTO and MACRO on 2021–2023 Brier, and non-overlapping median BSS>0 with at least 7 offsets BSS>0.
- B if COMBINED beats the better standalone block on 2021–2023 Brier, or beats both blocks but fails the full-sample / non-overlap bar.
- C if COMBINED does not beat the better standalone block (here: MACRO). Beating a CRYPTO spec that already loses to C0 is not incremental value.

No Crypto+Macro interactions. No extra features. M2 and HY unused.

## Guardrails

- no added features / interactions / C search
- no extra targets
- no 2024–2026
- Phase 3 / 4 / 6A not modified

