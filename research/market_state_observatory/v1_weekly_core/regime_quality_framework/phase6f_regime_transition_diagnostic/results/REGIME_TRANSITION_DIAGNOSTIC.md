# H3 — Regime / transition diagnostic

Question: does the **existing** frozen L=0 M_MACRO forecast perform differently by crypto `state_direction` at t, and is it more useful near backward-looking regime transitions than inside persistent regimes?

No new model. No new features. No lag 4/8. No interactions. No Bull/Bear-specific training. No 2024–2026. Not a trading backtest. Not an A/B/C verdict.

Forecasts reconstructed with the frozen H2 L=0 spec: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`. Logistic L2 `C=1.0`. Train-only median and scaler. Min train N=100. Mature labels `s <= t - H`.

`PREV_STATE` = `state_direction` at t−4. TRANSITION if previous ≠ current. PERSISTENT if previous = current. No future state is used.

M0 is the original expanding **all-market** mature base rate, scored on the **same weeks** as M_MACRO inside each slice.
If M_MACRO is better on transition weeks, that is a **CANDIDATE REGIME-CONDITIONAL EFFECT**, not “macro predicts regime transitions”.

N < 15 is labeled **LOW SAMPLE**. No conclusions from those groups. Directional transitions: no AUC.
2021–2023 is **TEMPORAL_ROBUSTNESS_2021_2023**, not clean OOS.

H3 labels (main hypothesis: macro is more useful near transitions than inside persistent regimes):

- SUPPORTS H3: TRANSITION BSS > PERSISTENT BSS on full **and** 2021–2023, TRANSITION BSS>0 on both, N≥15, and non-overlapping median BSS>0 with at least half of evaluated offsets BSS>0.
- WEAK SUPPORT: TRANSITION beats PERSISTENT and M0 on only one window, or both windows but non-overlap fails.
- NO SUPPORT: otherwise, including a single-regime edge that is not a transition effect.
- INSUFFICIENT SAMPLE: N<15 on both windows.

## Sample

| item | value |
|---|---|
| merged weeks | 470 |
| last week | 2023-12-29 |
| 2024+ | none |
| lag | 0 only |
| catalog BULL | 155 |
| catalog NEUTRAL | 165 |
| catalog BEAR | 114 |
| TRANSITION (t vs t−4) | 229 |
| PERSISTENT (t vs t−4) | 201 |
| reconstruction | ALL_MARKET L=0 matches H2 N and BSS |

## Classification

| H | BULL | NEUTRAL | BEAR | TRANSITION | PERSISTENT |
|---:|---|---|---|---|---|
| 4w | NO SUPPORT | NO SUPPORT | NO SUPPORT | WEAK SUPPORT | NO SUPPORT |
| 8w | NO SUPPORT | NO SUPPORT | NO SUPPORT | NO SUPPORT | NO SUPPORT |
| 12w | NO SUPPORT | NO SUPPORT | NO SUPPORT | NO SUPPORT | NO SUPPORT |

## Horizon 4w

### Full expanding walk-forward

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 103 | 0.680 | 0.2364 | -0.010 | 0.7195 | 0.471 | 0.530 | |
| NEUTRAL | 125 | 0.472 | 0.2929 | -0.057 | 0.8128 | 0.545 | 0.544 | |
| BEAR | 111 | 0.477 | 0.2801 | -0.007 | 0.7616 | 0.497 | 0.521 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 187 | 0.497 | 0.2681 | 0.017 | 0.7472 | 0.598 | 0.547 | |
| PERSISTENT | 152 | 0.586 | 0.2757 | -0.086 | 0.7929 | 0.502 | 0.560 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 56 | 0.589 | 0.2637 | -0.061 | 0.7271 | 0.511 | 0.538 | |

### TEMPORAL_ROBUSTNESS_2021_2023

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 44 | 0.705 | 0.1857 | 0.153 | 0.5571 | 0.707 | 0.577 | |
| NEUTRAL | 56 | 0.464 | 0.2507 | 0.071 | 0.7003 | 0.627 | 0.649 | |
| BEAR | 53 | 0.453 | 0.2402 | 0.128 | 0.6756 | 0.609 | 0.591 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 82 | 0.451 | 0.2339 | 0.158 | 0.6605 | 0.647 | 0.659 | |
| PERSISTENT | 71 | 0.620 | 0.2220 | 0.050 | 0.6391 | 0.692 | 0.660 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 28 | 0.607 | 0.2512 | -0.053 | 0.7018 | 0.599 | 0.599 | |

### Non-overlapping BSS (full walk-forward)

| slice | median BSS | min | max | offsets BSS>0 | offsets evaluated |
|---|---:|---:|---:|---:|---:|
| BULL | -0.037 | -0.076 | 0.110 | 1/4 | 4 |
| NEUTRAL | -0.059 | -0.102 | -0.012 | 0/4 | 4 |
| BEAR | -0.033 | -0.107 | 0.089 | 2/4 | 4 |
| TRANSITION | -0.009 | -0.019 | 0.107 | 1/4 | 4 |
| PERSISTENT | -0.106 | -0.118 | -0.008 | 0/4 | 4 |

### Directional transitions (full walk-forward)

| label | N | prevalence | mean predicted p | observed positive rate | Brier |
|---|---:|---:|---:|---:|---:|
| BEAR_TO_NEUTRAL | 40 | 0.400 | 0.555 | 0.400 | 0.3060 |
| BEAR_TO_BULL | 15 | 0.667 | 0.704 | 0.667 | 0.1741 |
| NEUTRAL_TO_BULL | 34 | 0.706 | 0.700 | 0.706 | 0.2003 |
| BULL_TO_NEUTRAL | 43 | 0.535 | 0.734 | 0.535 | 0.2826 |
| BULL_TO_BEAR LOW SAMPLE | 6 | 0.333 | 0.360 | 0.333 | 0.3471 |
| NEUTRAL_TO_BEAR | 49 | 0.367 | 0.564 | 0.367 | 0.2907 |

No AUC on directional groups. No conclusions from N<15.

## Horizon 8w

### Full expanding walk-forward

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 95 | 0.632 | 0.2539 | -0.017 | 0.8572 | 0.575 | 0.512 | |
| NEUTRAL | 125 | 0.480 | 0.3196 | -0.107 | 0.9685 | 0.513 | 0.532 | |
| BEAR | 111 | 0.523 | 0.2841 | -0.011 | 0.7746 | 0.525 | 0.468 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 185 | 0.535 | 0.2928 | -0.076 | 0.8514 | 0.537 | 0.486 | |
| PERSISTENT | 146 | 0.541 | 0.2837 | -0.020 | 0.8971 | 0.561 | 0.550 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 56 | 0.536 | 0.2740 | 0.018 | 0.7510 | 0.540 | 0.465 | |

### TEMPORAL_ROBUSTNESS_2021_2023

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 40 | 0.625 | 0.2091 | 0.131 | 0.6018 | 0.712 | 0.547 | |
| NEUTRAL | 56 | 0.411 | 0.2519 | 0.129 | 0.7021 | 0.642 | 0.625 | |
| BEAR | 53 | 0.566 | 0.2188 | 0.136 | 0.6253 | 0.704 | 0.554 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 80 | 0.500 | 0.2441 | 0.100 | 0.6832 | 0.584 | 0.550 | |
| PERSISTENT | 69 | 0.551 | 0.2106 | 0.172 | 0.6069 | 0.732 | 0.624 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 28 | 0.679 | 0.2107 | 0.052 | 0.6057 | 0.766 | 0.596 | |

### Non-overlapping BSS (full walk-forward)

| slice | median BSS | min | max | offsets BSS>0 | offsets evaluated |
|---|---:|---:|---:|---:|---:|
| BULL | -0.012 | -0.272 | 0.238 | 4/8 | 8 |
| NEUTRAL | -0.104 | -0.257 | 0.005 | 1/8 | 8 |
| BEAR | -0.061 | -0.197 | 0.197 | 3/8 | 8 |
| TRANSITION | -0.088 | -0.172 | 0.122 | 1/8 | 8 |
| PERSISTENT | -0.007 | -0.136 | 0.048 | 3/8 | 8 |

### Directional transitions (full walk-forward)

| label | N | prevalence | mean predicted p | observed positive rate | Brier |
|---|---:|---:|---:|---:|---:|
| BEAR_TO_NEUTRAL | 40 | 0.450 | 0.570 | 0.450 | 0.3480 |
| BEAR_TO_BULL LOW SAMPLE | 14 | 0.643 | 0.739 | 0.643 | 0.1535 |
| NEUTRAL_TO_BULL | 33 | 0.667 | 0.712 | 0.667 | 0.2235 |
| BULL_TO_NEUTRAL | 43 | 0.512 | 0.774 | 0.512 | 0.3382 |
| BULL_TO_BEAR LOW SAMPLE | 6 | 0.333 | 0.415 | 0.333 | 0.3607 |
| NEUTRAL_TO_BEAR | 49 | 0.531 | 0.636 | 0.531 | 0.2861 |

No AUC on directional groups. No conclusions from N<15.

## Horizon 12w

### Full expanding walk-forward

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 93 | 0.624 | 0.2708 | -0.043 | 1.0895 | 0.536 | 0.503 | |
| NEUTRAL | 120 | 0.500 | 0.3323 | -0.131 | 1.1673 | 0.485 | 0.517 | |
| BEAR | 110 | 0.409 | 0.3619 | -0.049 | 1.0562 | 0.469 | 0.514 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 178 | 0.528 | 0.3164 | -0.089 | 1.0241 | 0.511 | 0.517 | |
| PERSISTENT | 145 | 0.476 | 0.3348 | -0.064 | 1.2089 | 0.501 | 0.543 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 56 | 0.375 | 0.3591 | -0.019 | 1.0124 | 0.491 | 0.529 | |

### TEMPORAL_ROBUSTNESS_2021_2023

#### Regime

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 38 | 0.526 | 0.2191 | 0.201 | 0.6210 | 0.858 | 0.556 | |
| NEUTRAL | 55 | 0.382 | 0.2712 | 0.097 | 0.7477 | 0.590 | 0.607 | |
| BEAR | 52 | 0.519 | 0.2021 | 0.235 | 0.6099 | 0.775 | 0.736 | |

#### Transition vs persistent

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRANSITION | 77 | 0.494 | 0.2442 | 0.113 | 0.6961 | 0.641 | 0.612 | |
| PERSISTENT | 68 | 0.441 | 0.2198 | 0.233 | 0.6299 | 0.741 | 0.673 | |

#### Persistent BEAR

| slice | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR_PERSISTENT | 28 | 0.571 | 0.1877 | 0.256 | 0.5690 | 0.823 | 0.812 | |

### Non-overlapping BSS (full walk-forward)

| slice | median BSS | min | max | offsets BSS>0 | offsets evaluated |
|---|---:|---:|---:|---:|---:|
| BULL | NA | NA | NA | — | 0 |
| NEUTRAL | -0.121 | -0.329 | 0.037 | 3/9 | 9 |
| BEAR | 0.011 | -0.149 | 0.115 | 3/5 | 5 |
| TRANSITION | -0.113 | -0.276 | 0.130 | 4/12 | 12 |
| PERSISTENT | -0.047 | -0.312 | 0.080 | 3/11 | 11 |

### Directional transitions (full walk-forward)

| label | N | prevalence | mean predicted p | observed positive rate | Brier |
|---|---:|---:|---:|---:|---:|
| BEAR_TO_NEUTRAL | 40 | 0.500 | 0.581 | 0.500 | 0.3133 |
| BEAR_TO_BULL LOW SAMPLE | 14 | 0.643 | 0.770 | 0.643 | 0.1539 |
| NEUTRAL_TO_BULL | 31 | 0.645 | 0.712 | 0.645 | 0.2556 |
| BULL_TO_NEUTRAL | 39 | 0.538 | 0.782 | 0.538 | 0.3593 |
| BULL_TO_BEAR LOW SAMPLE | 6 | 0.333 | 0.461 | 0.333 | 0.3039 |
| NEUTRAL_TO_BEAR | 48 | 0.458 | 0.649 | 0.458 | 0.3725 |

No AUC on directional groups. No conclusions from N<15.

## Answers

1. Does macro perform differently in BULL vs NEUTRAL vs BEAR?
   - 4w full: BULL=-0.010 (N=103); NEUTRAL=-0.057 (N=125); BEAR=-0.007 (N=111).
   - 4w 2021–2023: BULL=0.153 (N=44); NEUTRAL=0.071 (N=56); BEAR=0.128 (N=53).
   - 8w full: BULL=-0.017 (N=95); NEUTRAL=-0.107 (N=125); BEAR=-0.011 (N=111).
   - 8w 2021–2023: BULL=0.131 (N=40); NEUTRAL=0.129 (N=56); BEAR=0.136 (N=53).
   - 12w full: BULL=-0.043 (N=93); NEUTRAL=-0.131 (N=120); BEAR=-0.049 (N=110).
   - 12w 2021–2023: BULL=0.201 (N=38); NEUTRAL=0.097 (N=55); BEAR=0.235 (N=52).
   On the full walk-forward, no regime beats M0. On 2021–2023, all three do. That is the known period effect, not a clean BULL-vs-BEAR split.

2. Is macro especially weak inside persistent BEAR?
   - 4w: persistent BEAR full BSS=-0.061 (N=56); 2021–2023 BSS=-0.053 (N=28). Weaker than all-BEAR and ≤0 on full WF.
   - 8w: persistent BEAR full BSS=0.018 (N=56); 2021–2023 BSS=0.052 (N=28). Not a distinct extra-weak cell beyond all-BEAR, or sample too small.
   - 12w: persistent BEAR full BSS=-0.019 (N=56); 2021–2023 BSS=0.256 (N=28). Not a distinct extra-weak cell beyond all-BEAR, or sample too small.

3. Is macro stronger near transitions?
   - 4w: TRANSITION vs PERSISTENT ΔBSS full=0.103, 2021–2023=0.108 (positive means transitions better). Class: WEAK SUPPORT.
   - 8w: TRANSITION vs PERSISTENT ΔBSS full=-0.057, 2021–2023=-0.072 (positive means transitions better). Class: NO SUPPORT.
   - 12w: TRANSITION vs PERSISTENT ΔBSS full=-0.025, 2021–2023=-0.120 (positive means transitions better). Class: NO SUPPORT.

4. Is the apparent edge concentrated in one regime only?
   - 4w: not concentrated. Full WF: no regime BSS>0. 2021–2023: all three (BULL, NEUTRAL, BEAR). That is a period effect, not a single-regime story.
   - 8w: not concentrated. Full WF: no regime BSS>0. 2021–2023: all three (BULL, NEUTRAL, BEAR). That is a period effect, not a single-regime story.
   - 12w: not concentrated. Full WF: no regime BSS>0. 2021–2023: all three (BULL, NEUTRAL, BEAR). That is a period effect, not a single-regime story.

5. Does any regime-specific pattern appear in both full WF and 2021–2023?
   - 4w: no regime BSS>0 on both windows; TRANSITION BSS>0 on both.
   - 8w: no regime (and not TRANSITION) has BSS>0 on both windows.
   - 12w: no regime (and not TRANSITION) has BSS>0 on both windows.

6. Does transition performance beat persistent-regime performance?
   - 4w: full True; 2021–2023 True.
   - 8w: full False; 2021–2023 False.
   - 12w: full False; 2021–2023 False.
   Horizons where TRANSITION BSS > PERSISTENT: full 1/3; 2021–2023 1/3.

7. Are results driven by tiny N?
   LOW SAMPLE cells exist (especially directional). Major-slice conclusions below ignore N<15 groups.
   LOW SAMPLE count: 0 major-slice rows, 5 directional rows.

8. Does the evidence support: “macro is more useful for regime changes than for forecasting returns inside an established crypto regime”?
   Overall H3: **WEAK SUPPORT**.
   The hypothesis is not established. At most a WEAK / horizon-conditional difference between transition weeks and persistent weeks. Do not treat this as a regime-change model.

## Decision

No A/B/C model verdict. No new model. No regime interactions added.
H3 hypothesis (transitions > persistent): **WEAK SUPPORT**.
If a slice shows better Brier skill on transition weeks, label it a CANDIDATE REGIME-CONDITIONAL EFFECT — not “macro predicts regime transitions”.

## Guardrails

- no new variables / interactions / separate Bull-Bear models
- lag=0 only; horizons 4/8/12 only
- no 2024–2026
- Phase 3 / 6A / 6E not modified

