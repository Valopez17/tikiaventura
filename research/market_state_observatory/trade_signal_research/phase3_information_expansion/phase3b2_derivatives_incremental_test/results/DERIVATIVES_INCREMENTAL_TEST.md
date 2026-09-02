# Derivatives incremental information test

**Historical walk-forward / temporal robustness.** Not clean OOS. Not an untouched holdout. Not final validation.
2024–2026 has already been inspected in this research project. The next genuinely clean evaluation is prospective after candidate freeze.

Not a trading strategy. Not PnL. High funding is not a sell rule.

Brier / log loss: lower better. Delta vs the paired BASE (or BASE+CORE in Test B): **negative is better** for Brier and log loss; **positive is better** for AUC and BSS.
M0 is the expanding mature prevalence. Beating M0 is not the same as derivatives adding information.

## Design (frozen before looking at deltas)

- Model: L2 logistic, C=1.0, daily refit, train-only median + StandardScaler.
- Mature labels only (`s + 60d <= t`). Min train N=100.
- Test A dates require BASE construction (Phase 2: five BTC percentiles + both targets) **and** all DERIV_CORE finite.
- Test B dates are the subset where OI_ADDON is also finite.
- Test A eligible calendar: **2020-12-29 → 2026-07-01** (N=2011 before min-train burn-in).
- Test B eligible calendar: **2021-09-01 → 2026-07-01** (N=1765 before min-train burn-in).
- Block-bootstrap of mean daily Brier-loss difference: block length 60, 2000 draws, seed 0.
- Diagnostic sub-blocks (FUNDING / BASIS / PERP) use Test A dates and do **not** select features.
- On this overlap, BASE itself has BSS vs M0 below 0 for both targets. That does not change the family test, which is BASE vs BASE+new information.

## Full walk-forward

### TEST_A / UP_60D

| model | feature_set | N | prev | Brier | BSS vs M0 | LogLoss | AUC | bal_acc@0.5 | ΔBrier | ΔLogLoss | ΔAUC | ΔBSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | M0 | 1852 | 0.261 | 0.2077 | 0.000 | 0.6074 | 0.391 | 0.480 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE | 1852 | 0.261 | 0.2461 | -0.185 | 0.9035 | 0.603 | 0.624 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE | 1852 | 0.261 | 0.2620 | -0.262 | 1.0614 | 0.556 | 0.592 | 0.0160 | 0.1579 | -0.046 | -0.077 |

### TEST_A / ADVERSE_60D

| model | feature_set | N | prev | Brier | BSS vs M0 | LogLoss | AUC | bal_acc@0.5 | ΔBrier | ΔLogLoss | ΔAUC | ΔBSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | M0 | 1852 | 0.362 | 0.2484 | 0.000 | 0.6903 | 0.487 | 0.520 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE | 1852 | 0.362 | 0.2662 | -0.071 | 0.9744 | 0.624 | 0.573 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE | 1852 | 0.362 | 0.2660 | -0.071 | 1.1261 | 0.675 | 0.609 | -0.0002 | 0.1517 | 0.051 | 0.001 |

### TEST_B / UP_60D

| model | feature_set | N | prev | Brier | BSS vs M0 | LogLoss | AUC | bal_acc@0.5 | ΔBrier | ΔLogLoss | ΔAUC | ΔBSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | M0 | 1606 | 0.231 | 0.1913 | 0.000 | 0.5851 | 0.353 | 0.500 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE | 1606 | 0.231 | 0.2050 | -0.072 | 0.8796 | 0.625 | 0.614 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE_OI | 1606 | 0.231 | 0.1976 | -0.033 | 0.9922 | 0.568 | 0.573 | -0.0074 | 0.1126 | -0.057 | 0.038 |

### TEST_B / ADVERSE_60D

| model | feature_set | N | prev | Brier | BSS vs M0 | LogLoss | AUC | bal_acc@0.5 | ΔBrier | ΔLogLoss | ΔAUC | ΔBSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | M0 | 1606 | 0.336 | 0.2478 | 0.000 | 0.6902 | 0.479 | 0.569 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE | 1606 | 0.336 | 0.2564 | -0.034 | 1.0355 | 0.722 | 0.615 | NA | NA | NA | NA |
| L2_LOGISTIC | BASE_CORE_OI | 1606 | 0.336 | 0.2546 | -0.028 | 1.0309 | 0.718 | 0.621 | -0.0017 | -0.0046 | -0.004 | 0.007 |

## Calendar years (diagnostics, not selection)

| test | target | year | N | ΔBrier | ΔLogLoss | ΔAUC |
|---|---|---:|---:|---:|---:|---:|
| TEST_A | UP_60D | 2021 | 209 | -0.0729 | 0.3087 | 0.116 |
| TEST_A | UP_60D | 2022 | 365 | 0.0240 | 0.2082 | -0.039 |
| TEST_A | UP_60D | 2023 | 365 | 0.0807 | 0.3725 | -0.084 |
| TEST_A | UP_60D | 2024 | 366 | 0.0224 | 0.0563 | -0.044 |
| TEST_A | UP_60D | 2025 | 365 | 0.0027 | 0.0021 | 0.000 |
| TEST_A | UP_60D | 2026 | 182 | -0.0141 | -0.0293 | -0.008 |
| TEST_A | ADVERSE_60D | 2021 | 209 | -0.0819 | 0.4217 | 0.177 |
| TEST_A | ADVERSE_60D | 2022 | 365 | 0.0290 | 0.3965 | 0.015 |
| TEST_A | ADVERSE_60D | 2023 | 365 | -0.0175 | -0.0143 | -0.069 |
| TEST_A | ADVERSE_60D | 2024 | 366 | 0.0151 | 0.0904 | -0.025 |
| TEST_A | ADVERSE_60D | 2025 | 365 | 0.0141 | 0.0458 | 0.028 |
| TEST_A | ADVERSE_60D | 2026 | 182 | 0.0102 | 0.0195 | 0.044 |
| TEST_B | UP_60D | 2022 | 328 | 0.0272 | 0.5040 | -0.176 |
| TEST_B | UP_60D | 2023 | 365 | 0.0195 | 0.2233 | -0.048 |
| TEST_B | UP_60D | 2024 | 366 | 0.0167 | 0.0590 | -0.017 |
| TEST_B | UP_60D | 2025 | 365 | -0.0937 | -0.2343 | -0.002 |
| TEST_B | UP_60D | 2026 | 182 | 0.0012 | -0.0111 | 0.074 |
| TEST_B | ADVERSE_60D | 2022 | 328 | 0.0069 | 0.0213 | -0.002 |
| TEST_B | ADVERSE_60D | 2023 | 365 | -0.0160 | -0.0358 | 0.002 |
| TEST_B | ADVERSE_60D | 2024 | 366 | 0.0188 | 0.0499 | -0.038 |
| TEST_B | ADVERSE_60D | 2025 | 365 | -0.0108 | -0.0251 | -0.159 |
| TEST_B | ADVERSE_60D | 2026 | 182 | -0.0118 | -0.0567 | 0.074 |

## Non-overlapping 60-day offsets and block bootstrap

| test | target | median ΔBrier | frac ΔBrier<0 | median ΔAUC | boot mean d | boot 95% CI |
|---|---|---:|---:|---:|---:|---|
| TEST_A | UP_60D | 0.0160 | 0.23 | -0.045 | 0.01598 | [-0.02644, 0.05033] |
| TEST_A | ADVERSE_60D | 0.0019 | 0.43 | 0.053 | -0.00021 | [-0.02852, 0.03064] |
| TEST_B | UP_60D | -0.0101 | 0.63 | -0.040 | -0.00736 | [-0.04398, 0.02990] |
| TEST_B | ADVERSE_60D | -0.0004 | 0.52 | 0.009 | -0.00172 | [-0.01396, 0.01038] |

d_t = (p_aug − y)² − (p_base − y)². Negative favors the augmented information set.

## Diagnostic sub-blocks (Test A dates only)

| target | block | ΔBrier vs BASE | ΔLogLoss | ΔAUC |
|---|---|---:|---:|---:|
| UP_60D | FUNDING | 0.0043 | 0.0175 | 0.013 |
| UP_60D | BASIS | 0.0095 | 0.0590 | -0.010 |
| UP_60D | PERP_ACTIVITY | 0.0113 | 0.1139 | -0.065 |
| ADVERSE_60D | FUNDING | -0.0216 | 0.0178 | 0.038 |
| ADVERSE_60D | BASIS | -0.0080 | -0.0006 | 0.016 |
| ADVERSE_60D | PERP_ACTIVITY | 0.0011 | 0.1348 | 0.040 |

These do not replace Test A (BASE vs BASE+all DERIV_CORE).

## Collinearity (Test A eligible rows, not used to drop columns)

Correlation-matrix condition number: **9.49**.

| feature | VIF |
|---|---:|
| `funding_pctl` | 2.13 |
| `funding_change_1d` | 1.04 |
| `funding_cum_30d` | 1.67 |
| `basis_pctl` | 2.48 |
| `basis_change_1d` | 1.27 |
| `perp_volume_rel_30d` | 1.03 |
| `perp_spot_volume_ratio` | 1.15 |

Largest pairwise |corr| among DERIV_CORE:
**funding_pctl** vs **basis_pctl**: 0.658.

## Coefficient sign stability (standardized L2 logistic, Test A / Test B refits)

| test | target | feature | frac>0 | frac<0 | median | IQR |
|---|---|---|---:|---:|---:|---:|
| TEST_A | UP_60D | `funding_pctl` | 0.15 | 0.85 | -0.360 | 0.378 |
| TEST_A | UP_60D | `funding_change_1d` | 0.92 | 0.08 | 0.070 | 0.080 |
| TEST_A | UP_60D | `funding_cum_30d` | 0.00 | 1.00 | -0.368 | 0.508 |
| TEST_A | UP_60D | `basis_pctl` | 1.00 | 0.00 | 0.444 | 0.316 |
| TEST_A | UP_60D | `basis_change_1d` | 0.04 | 0.96 | -0.152 | 0.095 |
| TEST_A | UP_60D | `perp_volume_rel_30d` | 0.50 | 0.50 | -0.002 | 0.523 |
| TEST_A | UP_60D | `perp_spot_volume_ratio` | 0.35 | 0.65 | -0.215 | 0.753 |
| TEST_A | ADVERSE_60D | `funding_pctl` | 0.99 | 0.01 | 0.503 | 0.365 |
| TEST_A | ADVERSE_60D | `funding_change_1d` | 0.46 | 0.54 | -0.003 | 0.052 |
| TEST_A | ADVERSE_60D | `funding_cum_30d` | 0.68 | 0.32 | 0.460 | 0.730 |
| TEST_A | ADVERSE_60D | `basis_pctl` | 0.56 | 0.44 | 0.083 | 0.412 |
| TEST_A | ADVERSE_60D | `basis_change_1d` | 0.30 | 0.70 | -0.096 | 0.169 |
| TEST_A | ADVERSE_60D | `perp_volume_rel_30d` | 0.31 | 0.69 | -0.150 | 0.264 |
| TEST_A | ADVERSE_60D | `perp_spot_volume_ratio` | 0.11 | 0.89 | -0.206 | 0.421 |
| TEST_B | UP_60D | `oi_change_1d` | 0.60 | 0.40 | 0.052 | 0.272 |
| TEST_B | UP_60D | `oi_change_7d` | 0.03 | 0.97 | -0.149 | 0.268 |
| TEST_B | UP_60D | `oi_pctl` | 0.19 | 0.81 | -1.218 | 1.232 |
| TEST_B | UP_60D | `oi_over_volume` | 0.47 | 0.53 | -0.069 | 0.734 |
| TEST_B | ADVERSE_60D | `oi_change_1d` | 0.41 | 0.59 | -0.034 | 0.088 |
| TEST_B | ADVERSE_60D | `oi_change_7d` | 0.45 | 0.55 | -0.020 | 0.150 |
| TEST_B | ADVERSE_60D | `oi_pctl` | 0.95 | 0.05 | 1.011 | 0.752 |
| TEST_B | ADVERSE_60D | `oi_over_volume` | 0.44 | 0.56 | -0.153 | 0.651 |

Unstable sign is not an automatic DROP in this phase.

## Answers

1. **Does DERIV_CORE add predictive information for UP_60D?**
Historical walk-forward evidence does not show material incremental value for UP_60D (**NO INCREMENTAL VALUE**; ΔBrier=0.0160, ΔAUC=-0.046).

2. **Does DERIV_CORE add predictive information for ADVERSE_60D?**
Historical walk-forward evidence for ADVERSE_60D is **MIXED** (ΔBrier=-0.0002, ΔLogLoss=0.1517, ΔAUC=0.051).

3. **Does OI add information beyond DERIV_CORE?**
UP_60D: **MIXED** (ΔBrier=-0.0074, ΔAUC=-0.057). ADVERSE_60D: **SUPPORT** (ΔBrier=-0.0017, ΔAUC=-0.004).

4. **Probability forecasting vs ranking?**
Test A UP_60D: neither ranking nor probability loss improved materially. Test A ADVERSE_60D: ranking improved but probability loss did not. Test B UP_60D: Brier improved but log loss and ranking did not both improve. Test B ADVERSE_60D: probability loss improved but ranking did not.

5. **Stable across years?**
See the year table. Gains concentrated in a single year with N≥50 count as MIXED under the predeclared rule, not as a reason to retune.

6. **Non-overlapping evaluation?**
Test A UP median ΔBrier=0.0160 (frac favorable 0.23). Test A ADVERSE median ΔBrier=0.0019 (frac 0.43).

7. **Block-bootstrap uncertainty?**
Test A UP mean d=0.01598 CI [-0.02644, 0.05033]. Test A ADVERSE mean d=-0.00021 CI [-0.02852, 0.03064]. This is a robustness measure, not a publication-level proof.

8. **Which sub-block looks informative (diagnostic only)?**
On Test A dates, FUNDING has the most favorable diagnostic ΔBrier for ADVERSE_60D and is the only UP_60D block with a positive ΔAUC. BASIS slightly improves ADVERSE Brier. PERP_ACTIVITY does not improve Brier on either target. These diagnostics do not replace Test A: the frozen CORE bundle as a whole did not beat BASE on UP_60D and was MIXED on ADVERSE_60D.

9. **Coefficient stability?**
See the sign-stability table. Standardized coefficients are comparable across features; unstable sign is not treated as DROP here.

10. **Final predeclared classifications**

- CORE → UP_60D: **NO INCREMENTAL VALUE**
- CORE → ADVERSE_60D: **MIXED**
- OI ADDON → UP_60D: **MIXED**
- OI ADDON → ADVERSE_60D: **SUPPORT**

11. **Retain derivatives for the expanded information set?**
OI_ADDON shows support on its own comparison, but CORE did not; do not promote a larger derivatives set from a weak CORE. Revisit only as a new frozen experiment.

Specifications were not changed after seeing the numbers.
