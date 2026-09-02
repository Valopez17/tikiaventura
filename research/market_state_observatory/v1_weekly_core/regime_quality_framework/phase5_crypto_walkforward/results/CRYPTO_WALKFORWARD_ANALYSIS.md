# Crypto-only walk-forward analysis (Phase 5)

Sample through **2023-12-29**. Expanding walk-forward. Training labels are **mature**: for horizon `h` at week `t`, only weeks `s <= t - h` enter the fit. Scaler and median imputation are training-window only. Logistic L2 with **C=1.0** (not tuned). **2024–2026 not used. Macro not used.**

JUICY_12W frozen threshold (P90 of complete 12w returns, 2015–2020 only, N=289): **133.8%** (`1.338163`). Not recomputed on 2021–2023.

Quintile calibration bins are descriptive (cut after the walk-forward). Primary metrics use every week. Non-overlapping offsets are the robustness layer.

---

## DESCRIPTIVE FINDINGS

### ALL_MARKET — sign 4w (full walk-forward)

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 327 | 0.538 | 0.538 | 0.500 | 0.2659 | 0.000 | 0.7287 | 0.406 | 1.078 | -0.847 | 0.0000 | 0.0000 |
| M1 | 327 | 0.538 | 0.483 | 0.462 | 0.2850 | -0.072 | 0.8894 | 0.468 | 0.636 | -0.157 | 0.0191 | 0.1607 |
| M2 | 327 | 0.538 | 0.492 | 0.465 | 0.2823 | -0.062 | 0.7840 | 0.489 | 0.616 | -0.121 | 0.0164 | 0.0552 |
| M3 | 327 | 0.538 | 0.523 | 0.500 | 0.2946 | -0.108 | 0.8330 | 0.484 | 0.609 | -0.111 | 0.0287 | 0.1043 |

### ALL_MARKET — sign 12w (full walk-forward)

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 311 | 0.486 | 0.486 | 0.500 | 0.3228 | 0.000 | 0.8887 | 0.302 | 1.670 | -1.739 | 0.0000 | 0.0000 |
| M1 | 311 | 0.486 | 0.479 | 0.486 | 0.3366 | -0.043 | 1.3677 | 0.459 | 0.555 | -0.111 | 0.0137 | 0.4790 |
| M2 | 311 | 0.486 | 0.424 | 0.435 | 0.3661 | -0.134 | 1.1341 | 0.346 | 1.017 | -0.789 | 0.0433 | 0.2455 |
| M3 | 311 | 0.486 | 0.424 | 0.432 | 0.3651 | -0.131 | 1.2110 | 0.406 | 0.790 | -0.463 | 0.0423 | 0.3223 |

### ALL_MARKET — 2021–2023 validation — sign 4w

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 153 | 0.529 | 0.529 | 0.500 | 0.2584 | 0.000 | 0.7107 | 0.407 | 1.794 | -2.069 | 0.0000 | 0.0000 |
| M1 | 153 | 0.529 | 0.503 | 0.489 | 0.2617 | -0.013 | 0.7203 | 0.493 | 0.477 | 0.090 | 0.0032 | 0.0096 |
| M2 | 153 | 0.529 | 0.484 | 0.462 | 0.2640 | -0.022 | 0.7238 | 0.490 | 0.815 | -0.492 | 0.0056 | 0.0131 |
| M3 | 153 | 0.529 | 0.529 | 0.515 | 0.2656 | -0.028 | 0.7323 | 0.507 | 0.581 | -0.089 | 0.0072 | 0.0216 |

### ALL_MARKET — 2021–2023 validation — sign 12w

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.469 | 0.469 | 0.500 | 0.2834 | 0.000 | 0.7631 | 0.359 | 2.313 | -2.894 | 0.0000 | 0.0000 |
| M1 | 145 | 0.469 | 0.428 | 0.438 | 0.3097 | -0.093 | 0.8286 | 0.444 | 0.589 | -0.211 | 0.0263 | 0.0656 |
| M2 | 145 | 0.469 | 0.434 | 0.452 | 0.2919 | -0.030 | 0.7850 | 0.418 | 0.804 | -0.566 | 0.0085 | 0.0219 |
| M3 | 145 | 0.469 | 0.421 | 0.434 | 0.3118 | -0.100 | 0.8672 | 0.428 | 0.757 | -0.484 | 0.0284 | 0.1041 |

### ALL_MARKET — JUICY_12W (future return ≥ frozen P90)

Full:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 311 | 0.039 | 0.961 | 0.500 | 0.0425 | 0.000 | 0.1981 | 0.170 | 0.165 | -1.298 | 0.0000 | 0.0000 |
| M1 | 311 | 0.039 | 0.942 | 0.490 | 0.0499 | -0.174 | 0.2678 | 0.526 | 0.039 | -0.002 | 0.0074 | 0.0697 |
| M2 | 311 | 0.039 | 0.961 | 0.500 | 0.0401 | 0.057 | 0.1892 | 0.455 | 0.055 | -0.323 | -0.0024 | -0.0090 |
| M3 | 311 | 0.039 | 0.961 | 0.500 | 0.0438 | -0.030 | 0.2108 | 0.303 | 0.054 | -0.301 | 0.0013 | 0.0127 |

2021–2023:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 145 | 0.000 | 1.000 | NA | 0.0074 | 0.000 | 0.0895 | NA | 0.000 | 0.000 | 0.0000 | 0.0000 |
| M1 | 145 | 0.000 | 1.000 | NA | 0.0096 | -0.299 | 0.0744 | NA | 0.000 | -0.000 | 0.0022 | -0.0151 |
| M2 | 145 | 0.000 | 1.000 | NA | 0.0029 | 0.605 | 0.0462 | NA | 0.000 | -0.000 | -0.0045 | -0.0433 |
| M3 | 145 | 0.000 | 1.000 | NA | 0.0025 | 0.658 | 0.0425 | NA | 0.000 | 0.000 | -0.0049 | -0.0470 |

### ALL_MARKET — strong / severe (full walk-forward)

Strong 4w (>10%):

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 327 | 0.364 | 0.615 | 0.483 | 0.2381 | 0.000 | 0.6694 | 0.422 | 1.002 | -1.522 | 0.0000 | 0.0000 |
| M1 | 327 | 0.364 | 0.587 | 0.519 | 0.2487 | -0.044 | 0.7280 | 0.483 | 0.396 | -0.080 | 0.0105 | 0.0586 |
| M2 | 327 | 0.364 | 0.609 | 0.513 | 0.2399 | -0.007 | 0.6753 | 0.534 | 0.310 | 0.140 | 0.0018 | 0.0059 |
| M3 | 327 | 0.364 | 0.584 | 0.515 | 0.2600 | -0.092 | 0.7333 | 0.500 | 0.379 | -0.038 | 0.0219 | 0.0639 |

Strong 12w (>20%):

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 311 | 0.350 | 0.408 | 0.471 | 0.2868 | 0.000 | 0.7714 | 0.343 | 1.124 | -1.428 | 0.0000 | 0.0000 |
| M1 | 311 | 0.350 | 0.457 | 0.491 | 0.3174 | -0.107 | 1.1499 | 0.445 | 0.467 | -0.227 | 0.0306 | 0.3785 |
| M2 | 311 | 0.350 | 0.405 | 0.411 | 0.3115 | -0.086 | 0.8591 | 0.402 | 0.609 | -0.497 | 0.0247 | 0.0877 |
| M3 | 311 | 0.350 | 0.479 | 0.464 | 0.3124 | -0.089 | 0.8839 | 0.433 | 0.498 | -0.296 | 0.0256 | 0.1125 |

Severe 4w (<−10%):

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 327 | 0.263 | 0.737 | 0.500 | 0.2009 | 0.000 | 0.5980 | 0.348 | 0.786 | -2.326 | 0.0000 | 0.0000 |
| M1 | 327 | 0.263 | 0.737 | 0.500 | 0.2155 | -0.073 | 0.8741 | 0.429 | 0.308 | -0.205 | 0.0146 | 0.2761 |
| M2 | 327 | 0.263 | 0.728 | 0.505 | 0.2161 | -0.076 | 0.6710 | 0.446 | 0.310 | -0.228 | 0.0152 | 0.0731 |
| M3 | 327 | 0.263 | 0.725 | 0.507 | 0.2236 | -0.113 | 0.7232 | 0.407 | 0.325 | -0.309 | 0.0227 | 0.1252 |

Severe 12w (<−20%):

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 311 | 0.254 | 0.746 | 0.500 | 0.2170 | 0.000 | 0.9887 | 0.226 | 0.676 | -2.550 | 0.0000 | 0.0000 |
| M1 | 311 | 0.254 | 0.733 | 0.491 | 0.2426 | -0.118 | 1.6611 | 0.341 | 0.391 | -0.779 | 0.0255 | 0.6724 |
| M2 | 311 | 0.254 | 0.723 | 0.485 | 0.2515 | -0.159 | 1.1743 | 0.267 | 0.453 | -1.111 | 0.0344 | 0.1856 |
| M3 | 311 | 0.254 | 0.711 | 0.476 | 0.2607 | -0.201 | 1.2150 | 0.257 | 0.431 | -1.011 | 0.0437 | 0.2264 |

### BULL-only — continuation = sign (full and 2021–2023)

BULL sign 4w full:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 51 | 0.745 | 0.745 | 0.500 | 0.1968 | 0.000 | 0.5843 | 0.270 | 6.716 | -8.442 | 0.0000 | 0.0000 |
| M1 | 51 | 0.745 | 0.745 | 0.500 | 0.2173 | -0.104 | 0.6322 | 0.288 | 2.012 | -1.770 | 0.0205 | 0.0478 |
| M2 | 51 | 0.745 | 0.706 | 0.474 | 0.2356 | -0.197 | 0.6997 | 0.350 | 1.329 | -0.837 | 0.0388 | 0.1154 |
| M3 | 51 | 0.745 | 0.549 | 0.394 | 0.3009 | -0.529 | 0.9199 | 0.322 | 1.097 | -0.531 | 0.1041 | 0.3355 |

BULL sign 12w full:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 44 | 0.591 | 0.591 | 0.500 | 0.2766 | 0.000 | 0.7648 | 0.368 | 2.669 | -2.717 | 0.0000 | 0.0000 |
| M1 | 44 | 0.591 | 0.591 | 0.500 | 0.2816 | -0.018 | 0.7820 | 0.417 | 1.463 | -1.125 | 0.0050 | 0.0173 |
| M2 | 44 | 0.591 | 0.591 | 0.500 | 0.3219 | -0.164 | 0.9282 | 0.233 | 2.493 | -2.442 | 0.0453 | 0.1634 |
| M3 | 44 | 0.591 | 0.545 | 0.462 | 0.4092 | -0.479 | 1.4860 | 0.075 | 2.390 | -2.274 | 0.1326 | 0.7212 |

BULL sign 12w 2021–2023:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 38 | 0.526 | 0.526 | 0.500 | 0.3127 | 0.000 | 0.8463 | 0.311 | 3.797 | -4.290 | 0.0000 | 0.0000 |
| M1 | 38 | 0.526 | 0.526 | 0.500 | 0.3210 | -0.027 | 0.8744 | 0.308 | 3.102 | -3.357 | 0.0084 | 0.0282 |
| M2 | 38 | 0.526 | 0.526 | 0.500 | 0.3679 | -0.177 | 1.0458 | 0.153 | 3.052 | -3.280 | 0.0553 | 0.1995 |
| M3 | 38 | 0.526 | 0.474 | 0.450 | 0.4616 | -0.476 | 1.6734 | 0.058 | 2.447 | -2.408 | 0.1490 | 0.8271 |

BULL sign 4w 2021–2023:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 44 | 0.705 | 0.705 | 0.500 | 0.2121 | 0.000 | 0.6166 | 0.331 | 6.114 | -7.607 | 0.0000 | 0.0000 |
| M1 | 44 | 0.705 | 0.705 | 0.500 | 0.2436 | -0.148 | 0.6914 | 0.232 | 2.368 | -2.353 | 0.0315 | 0.0749 |
| M2 | 44 | 0.705 | 0.659 | 0.468 | 0.2657 | -0.253 | 0.7748 | 0.283 | 1.588 | -1.298 | 0.0537 | 0.1582 |
| M3 | 44 | 0.705 | 0.477 | 0.361 | 0.3374 | -0.591 | 1.0229 | 0.290 | 1.150 | -0.691 | 0.1254 | 0.4063 |

### HIGH_MOM (`MOM_12W_PERCENTILE >= 0.70`) including M4

Sign 12w full:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 70 | 0.471 | 0.471 | 0.500 | 0.3316 | 0.000 | 0.8961 | 0.410 | 0.978 | -0.688 | 0.0000 | 0.0000 |
| M1 | 70 | 0.471 | 0.471 | 0.500 | 0.3650 | -0.101 | 1.6427 | 0.425 | 0.762 | -0.379 | 0.0334 | 0.7466 |
| M2 | 70 | 0.471 | 0.443 | 0.468 | 0.3905 | -0.178 | 1.1611 | 0.466 | 0.778 | -0.399 | 0.0589 | 0.2650 |
| M3 | 70 | 0.471 | 0.386 | 0.407 | 0.4123 | -0.243 | 1.3587 | 0.390 | 0.916 | -0.581 | 0.0807 | 0.4626 |
| M4 | 70 | 0.471 | 0.414 | 0.439 | 0.3690 | -0.113 | 1.0261 | 0.410 | 0.875 | -0.551 | 0.0374 | 0.1300 |

Sign 12w 2021–2023:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 30 | 0.400 | 0.400 | 0.500 | 0.3242 | 0.000 | 0.8526 | 0.391 | 2.184 | -2.611 | 0.0000 | 0.0000 |
| M1 | 30 | 0.400 | 0.400 | 0.500 | 0.3191 | 0.016 | 0.8462 | 0.498 | 0.319 | 0.120 | -0.0051 | -0.0064 |
| M2 | 30 | 0.400 | 0.367 | 0.458 | 0.3315 | -0.022 | 0.8679 | 0.514 | 0.990 | -0.872 | 0.0073 | 0.0153 |
| M3 | 30 | 0.400 | 0.300 | 0.361 | 0.4174 | -0.287 | 1.0971 | 0.125 | 1.856 | -2.200 | 0.0932 | 0.2445 |
| M4 | 30 | 0.400 | 0.367 | 0.458 | 0.3746 | -0.155 | 1.0089 | 0.255 | 1.747 | -2.005 | 0.0504 | 0.1563 |

Sign 4w full:

| model | N | prev | acc | bal_acc | brier | BSS vs M0 | logloss | AUC | cal_a | cal_b | Δbrier vs M0 | Δll vs M0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 81 | 0.716 | 0.716 | 0.500 | 0.2190 | 0.000 | 0.6304 | 0.381 | 2.491 | -2.893 | 0.0000 | 0.0000 |
| M1 | 81 | 0.716 | 0.531 | 0.384 | 0.2556 | -0.167 | 1.2660 | 0.426 | 0.866 | -0.230 | 0.0366 | 0.6356 |
| M2 | 81 | 0.716 | 0.654 | 0.522 | 0.2436 | -0.112 | 0.7176 | 0.462 | 0.856 | -0.229 | 0.0246 | 0.0872 |
| M3 | 81 | 0.716 | 0.556 | 0.480 | 0.2797 | -0.277 | 0.8109 | 0.477 | 0.744 | -0.048 | 0.0607 | 0.1805 |
| M4 | 81 | 0.716 | 0.654 | 0.549 | 0.2318 | -0.058 | 0.6758 | 0.508 | 0.633 | 0.133 | 0.0128 | 0.0453 |

### Coefficient stability (M3 snapshots every 26 weeks)

ALL_MARKET M3, sign_12w:

| feature | n | median | p25 | p75 | frac>0 | frac<0 |
|---|---:|---:|---:|---:|---:|---:|
| MOM_12W_PERCENTILE | 12 | 0.2914 | 0.0253 | 0.4888 | 0.83 | 0.17 |
| MOM_4W_PERCENTILE | 12 | 0.5591 | 0.4732 | 0.5927 | 1.00 | 0.00 |
| broad_breadth_4w | 12 | 0.3365 | 0.0377 | 0.4587 | 0.83 | 0.17 |
| largecap_breadth_4w_lagged | 12 | 0.0742 | -0.2165 | 0.3421 | 0.50 | 0.50 |
| VOL_PERCENTILE | 12 | -0.2415 | -0.4581 | -0.1628 | 0.08 | 0.92 |
| TURNOVER_RELATIVE | 12 | 0.0463 | 0.0235 | 0.0734 | 0.92 | 0.08 |
| STABLECOIN_MCAP_12W_CHANGE | 12 | -0.2110 | -0.8310 | 0.0941 | 0.33 | 0.67 |
| MOM4_CHANGE_4W | 12 | 0.2974 | 0.1866 | 0.3998 | 1.00 | 0.00 |
| MOM12_CHANGE_4W | 12 | -0.6278 | -0.9246 | -0.2054 | 0.00 | 1.00 |
| MOM12_PERCENTILE_CHANGE_4W | 12 | -0.0932 | -0.3786 | -0.0473 | 0.17 | 0.83 |
| BROAD_BREADTH_CHANGE_4W | 12 | -0.2835 | -0.6557 | 0.2531 | 0.42 | 0.58 |
| LARGECAP_BREADTH_CHANGE_4W | 12 | -0.1844 | -0.6490 | -0.0170 | 0.25 | 0.75 |
| VOL_PERCENTILE_CHANGE_4W | 12 | -0.0106 | -0.1947 | 0.0494 | 0.50 | 0.50 |
| TURNOVER_CHANGE_4W | 12 | 0.0458 | 0.0396 | 0.1248 | 0.92 | 0.08 |

ALL_MARKET M3, sign_4w:

| feature | n | median | p25 | p75 | frac>0 | frac<0 |
|---|---:|---:|---:|---:|---:|---:|
| MOM_12W_PERCENTILE | 12 | 0.3349 | 0.2798 | 0.4306 | 0.92 | 0.08 |
| MOM_4W_PERCENTILE | 12 | -0.0372 | -0.2489 | 0.0931 | 0.50 | 0.50 |
| broad_breadth_4w | 12 | -0.2924 | -0.4444 | 0.0925 | 0.42 | 0.58 |
| largecap_breadth_4w_lagged | 12 | -0.3005 | -0.4711 | 0.3740 | 0.42 | 0.58 |
| VOL_PERCENTILE | 12 | -0.3596 | -0.5646 | -0.2380 | 0.00 | 1.00 |
| TURNOVER_RELATIVE | 12 | 0.2182 | 0.2032 | 0.2456 | 1.00 | 0.00 |
| STABLECOIN_MCAP_12W_CHANGE | 12 | 0.2383 | 0.1775 | 0.2724 | 1.00 | 0.00 |
| MOM4_CHANGE_4W | 12 | 0.3798 | 0.2414 | 0.5074 | 1.00 | 0.00 |
| MOM12_CHANGE_4W | 12 | 0.0057 | -0.0121 | 0.0454 | 0.58 | 0.42 |
| MOM12_PERCENTILE_CHANGE_4W | 12 | 0.1235 | 0.0428 | 0.1631 | 0.83 | 0.17 |
| BROAD_BREADTH_CHANGE_4W | 12 | -0.7995 | -0.9406 | -0.5926 | 0.00 | 1.00 |
| LARGECAP_BREADTH_CHANGE_4W | 12 | 0.6410 | 0.1525 | 0.8805 | 0.92 | 0.08 |
| VOL_PERCENTILE_CHANGE_4W | 12 | -0.1583 | -0.1958 | -0.1121 | 0.00 | 1.00 |
| TURNOVER_CHANGE_4W | 12 | -0.0540 | -0.0790 | -0.0374 | 0.17 | 0.83 |

BULL M3, sign_12w (lateness test):

| feature | n | median | p25 | p75 | frac>0 | frac<0 |
|---|---:|---:|---:|---:|---:|---:|
| MOM_12W_PERCENTILE | 1 | 0.4400 | 0.4400 | 0.4400 | 1.00 | 0.00 |
| MOM_4W_PERCENTILE | 1 | 0.1715 | 0.1715 | 0.1715 | 1.00 | 0.00 |
| broad_breadth_4w | 1 | 0.3541 | 0.3541 | 0.3541 | 1.00 | 0.00 |
| largecap_breadth_4w_lagged | 1 | -1.0499 | -1.0499 | -1.0499 | 0.00 | 1.00 |
| VOL_PERCENTILE | 1 | 0.2183 | 0.2183 | 0.2183 | 1.00 | 0.00 |
| TURNOVER_RELATIVE | 1 | 0.2254 | 0.2254 | 0.2254 | 1.00 | 0.00 |
| STABLECOIN_MCAP_12W_CHANGE | 1 | -0.2143 | -0.2143 | -0.2143 | 0.00 | 1.00 |
| MOM4_CHANGE_4W | 1 | 1.0039 | 1.0039 | 1.0039 | 1.00 | 0.00 |
| MOM12_CHANGE_4W | 1 | -1.1558 | -1.1558 | -1.1558 | 0.00 | 1.00 |
| MOM12_PERCENTILE_CHANGE_4W | 1 | -0.3408 | -0.3408 | -0.3408 | 0.00 | 1.00 |
| BROAD_BREADTH_CHANGE_4W | 1 | -0.3915 | -0.3915 | -0.3915 | 0.00 | 1.00 |
| LARGECAP_BREADTH_CHANGE_4W | 1 | 0.0893 | 0.0893 | 0.0893 | 1.00 | 0.00 |
| VOL_PERCENTILE_CHANGE_4W | 1 | -1.0877 | -1.0877 | -1.0877 | 0.00 | 1.00 |
| TURNOVER_CHANGE_4W | 1 | -0.0634 | -0.0634 | -0.0634 | 0.00 | 1.00 |

HIGH_MOM M4, sign_12w:

| feature | n | median | p25 | p75 | frac>0 | frac<0 |
|---|---:|---:|---:|---:|---:|---:|
| MOM_12W_PERCENTILE | 3 | 0.5451 | 0.4425 | 0.7073 | 1.00 | 0.00 |
| MOM4_CHANGE_4W | 3 | 0.9744 | 0.8520 | 0.9781 | 1.00 | 0.00 |
| MOM12_CHANGE_4W | 3 | -1.2590 | -1.3312 | -1.0935 | 0.00 | 1.00 |
| MOM12_PERCENTILE_CHANGE_4W | 3 | 0.2822 | 0.2289 | 0.3598 | 1.00 | 0.00 |
| BROAD_BREADTH_CHANGE_4W | 3 | 0.2589 | 0.1664 | 0.3341 | 1.00 | 0.00 |
| LARGECAP_BREADTH_CHANGE_4W | 3 | 0.2642 | 0.1745 | 0.2722 | 1.00 | 0.00 |
| TURNOVER_RELATIVE | 3 | -0.0726 | -0.0802 | -0.0328 | 0.33 | 0.67 |
| VOL_PERCENTILE_CHANGE_4W | 3 | -0.6175 | -0.8556 | -0.5587 | 0.00 | 1.00 |

### Block bootstrap (12-week blocks, 1000 draws)

ΔBrier = Brier(model) − Brier(baseline) on aligned weeks. Negative means the model is better.

- sign_4w M3-vs-M0 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = -0.0006 / 0.0287 / 0.0645  (negative = model better)
- sign_4w M3-vs-M1 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = -0.0178 / 0.0108 / 0.0422  (negative = model better)
- sign_4w M2-vs-M0 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = -0.0036 / 0.0178 / 0.0430  (negative = model better)
- sign_12w M3-vs-M0 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = -0.0148 / 0.0438 / 0.1042  (negative = model better)
- sign_12w M3-vs-M1 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = -0.0022 / 0.0306 / 0.0673  (negative = model better)
- sign_12w M2-vs-M0 full_wf: mean ΔBrier (model−baseline) 2.5/50/97.5 = 0.0055 / 0.0455 / 0.0863  (negative = model better)

### Non-overlapping offsets

Every 4th week (4 offsets) for 4w; every 12th week (12 offsets) for 12w. Metric: Brier skill vs M0 on that offset.

- ALL_MARKET sign_4w M3: BSS median -0.109 (min -0.151, max -0.060), offsets with BSS>0: 0/4
- ALL_MARKET sign_12w M3: BSS median -0.125 (min -0.258, max -0.040), offsets with BSS>0: 0/12
- ALL_MARKET sign_4w M1: BSS median -0.067 (min -0.164, max 0.002), offsets with BSS>0: 1/4
- ALL_MARKET sign_12w M1: BSS median -0.032 (min -0.127, max 0.037), offsets with BSS>0: 3/12
- ALL_MARKET juicy_12w M3: BSS median -0.011 (min -0.585, max 0.643), offsets with BSS>0: 6/12

---

### Ranking is inverted (M3, sign 12w, full walk-forward)

Descriptive quintiles of predicted P(Y12=1). This is not a trading bucket.

| bin | N | mean p | observed freq | median 12w ret | severe-down (<−20%) | med DD |
|---|---:|---:|---:|---:|---:|---:|
| Q1 (lowest p) | 63 | 0.36 | **62%** | **+8.9%** | 8% | −16% |
| Q2 | 62 | 0.54 | 47% | −1.5% | 16% | −20% |
| Q3 | 62 | 0.65 | 50% | −1.1% | 32% | −21% |
| Q4 | 62 | 0.78 | 53% | +11.4% | 34% | −18% |
| Q5 (highest p) | 62 | 0.96 | **31%** | **−14.8%** | **37%** | **−37%** |

The model’s most confident “up” weeks had the worst subsequent 12w distribution. Calibration slope on sign targets is negative. That is the opposite of a usable probability forecast.

M0 expanding base rate also has AUC < 0.5 on sign targets: after 2017 the historical hit rate stays high while later outcomes are worse. M0 still **loses less** than M1–M3 because it does not add overconfident ranking.

---

## ANSWERS

1. **Does V1 state beat the unconditional base rate?** No. M1 BSS vs M0 is negative on sign 4w (−0.072) and sign 12w (−0.043) in the full walk-forward, and still negative in 2021–2023. Adds-value (Brier **and** logloss) in **0/4** primary cells.
2. **Do crypto levels beat V1?** No. M2 does not beat M0 (or M1) on Brier+logloss for sign 4w/12w. Full 12w BSS = −0.134.
3. **Do dynamics improve levels?** No as a forecast. M3 is slightly worse than M2 on 12w Brier in validation (0.312 vs 0.292) and worse than M0 everywhere that matters. Adds-value in **0/4** primary cells.
4. **Strongest 4w “improvement”:** none. The least-bad 2021–2023 Brier is M0 (0.258). M3 BSS = −0.028.
5. **Strongest 12w “improvement”:** none. M0 Brier 0.283 in 2021–2023; M3 BSS = −0.100. M2 is less bad than M3 but still worse than M0 (BSS −0.030).
6. **Survives 2021–2023?** No.
7. **Survives non-overlapping evaluation?** No. M3 BSS vs M0 is negative on **0/4** 4w offsets (median −0.109) and **0/12** 12w offsets (median −0.125).
8. **Are probabilities calibrated?** No. Sign-target calibration slopes are negative. Higher predicted P coincides with worse outcomes (see Q1 vs Q5).
9. **Can the model rank future return distributions?** Not in the useful direction. Q5 of M3 sign-12w has lower hit rate, worse median, and deeper drawdowns than Q1.
10. **JUICY_12W vs base rate?** Frozen development P90 = **+133.8%**. Full-sample prevalence among scored weeks = 3.9% (2017-style). **2021–2023 prevalence = 0.** M2’s small full-wf Brier edge (BSS +0.057) is a rare-event artefact, not a detector of 2021–2023 opportunities. Do not read validation BSS on an all-zero target as skill.
11. **Severe downside?** M1–M3 have **worse** Brier than M0 on severe_12w (full BSS −0.12 to −0.20; validation also worse). They do not identify left-tail weeks better than the base rate.
12. **Inside Bull, continuation vs failure?** No. BULL walk-forward only starts once 100 mature Bull labels exist (N=51 at 4w, N=44 at 12w, mostly 2021–2023). M3 does not beat M0. HIGH_MOM M4 also loses to M0 on sign 12w (full BSS −0.113).
13. **Does MOM12 act as lateness after controlling for dynamics?** Not in the expanding logistic. ALL_MARKET M3 sign_12w: `MOM_12W_PERCENTILE` median coef **+0.33** (92% of snapshots positive) — the opposite of a lateness penalty. `MOM12_PERCENTILE_CHANGE_4W` is mostly positive (+0.12, 83% >0). BULL snapshots are N=1 (too late in the sample). Do not treat Phase 4’s descriptive lateness split as a real-time coefficient.
14. **Momentum-change coefficients stable?** `MOM4_CHANGE_4W` is stable positive (100% of ALL_MARKET M3 sign_12w snapshots). `MOM12_CHANGE_4W` flips (58% >0). Stability ≠ forecast value: M3 still loses to M0.
15. **Breadth change stable?** No as a pair. `BROAD_BREADTH_CHANGE_4W` is 100% negative; `LARGECAP_BREADTH_CHANGE_4W` is 92% positive. Contradictory signs.
16. **TURNOVER_RELATIVE stable?** Yes, positive in 100% of ALL_MARKET M3 sign_12w snapshots. Still not enough to beat the base rate.
17. **Which features improve probability forecasts consistently?** None under the frozen adds-value rule. Snapshot sign-stability is not a substitute for OOS Brier/logloss.
18. **Which fail?** V1 `market_state` frequencies, crypto levels, levels+dynamics, and the HIGH_MOM conditional model all fail vs expanding base rate on primary sign targets. The inverted Q5 ranking is the operational failure mode.
19. **Is Model A strong enough to freeze before macro?** No. Do **not** freeze M2/M3/M4. Keep crypto internals as **descriptive Observatory context** (Phase 3–4). They are not a real-time 4w/12w probability model in 2015–2023 walk-forward.
20. **What exact residual remains for macro?** All of it: juicy-12w detection (the frozen crypto P90 never hits in 2021–2023), Bull continuation vs failure, late-2020 vs late-2021, and downside risk. Phase 6 may test whether macro adds what crypto-only did not.

---

## VERDICT

**C — CRYPTO-ONLY DOES NOT BEAT SIMPLE BENCHMARKS**

Adds-value rule (frozen, not retuned on 2021–2023): Brier **and** log loss must improve vs M0 (and vs M1 to claim “beats V1”). Accuracy does not count. Degenerate periods with prevalence 0 or 1 are not counted as skill.

Primary cells (sign 4w/12w × full/validation): M1 **0/4**, M2 **0/4**, M3 **0/4**.

Block bootstrap (12-week blocks, 1000 draws): median ΔBrier M3−M0 is **positive** (M3 worse) at both horizons; 95% intervals do not show a reliable improvement.

Do not freeze a crypto predictive Model A.

---

## WHAT REMAINS FOR MACRO (Phase 6)

Can macro improve:

- JUICY 12w opportunity detection?
- Bull continuation vs failure?
- 2020 vs 2021 discrimination?
- downside-risk prediction?

Crypto-only walk-forward did not solve these. 2024–2026 stays sealed as the final exam.
