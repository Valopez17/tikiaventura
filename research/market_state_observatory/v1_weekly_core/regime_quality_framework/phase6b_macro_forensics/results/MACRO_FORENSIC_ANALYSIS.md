# Phase 6B — Macro forensic analysis

**DESCRIPTIVE ONLY. NOT PREDICTIVE. NOT CAUSAL.**

Question: at week t, do macro *conditions already on the tape* differ between weeks that later printed strong 12w crypto returns and weeks that printed weak or failing 12w returns?

No logistic. No ML. No score. No regimes. No 2024–2026. No threshold search.

## Merge audit

| check | result |
|---|---|
| macro rows | 470 |
| catalog rows | 470 |
| inner-merged rows | 470 |
| join | Friday `week`, one-to-one |
| duplicated weeks | none |
| sample | 2015-01-02 … 2023-12-29 |
| 2024+ | none |
| forward macro | **no** — every macro column is the Phase 6A value at the same Friday t; nothing is shifted from t+h |

Universe for group tables: weeks with a **complete** 12w crypto path (`future_return_12w` finite).

Complete 12w weeks: **434**. TOP10 N=44. BOTTOM10 N=43. OTHER N=347. REST (not TOP10) N=390.
Bull continuation 12w N=105. Bull failure 12w N=40.

`M2_CHG_12W` is **DIAGNOSTIC ONLY** (Phase 6A lookahead HIGH, monthly, revised, not vintage).
`HY_SPREAD` is absent and unused.

## 1. TOP10 vs BOTTOM10 vs OTHER

| feature | TOP10 | BOTTOM10 | OTHER |
|---|---|---|---|
| DXY_CHG_12W | N=44; mean=-1.84%; median=-1.99%; p25=-3.01%; p75=-1.14% | N=43; mean=+1.17%; median=+1.10%; p25=+0.41%; p75=+1.89% | N=347; mean=+0.58%; median=+0.64%; p25=-1.36%; p75=+2.26% |
| FED_FUNDS_CHG_12W | N=44; mean=+0.071 pp; median=+0.000 pp; p25=+0.000 pp; p75=+0.220 pp | N=43; mean=+0.187 pp; median=+0.250 pp; p25=+0.000 pp; p75=+0.270 pp | N=347; mean=+0.147 pp; median=+0.030 pp; p25=-0.010 pp; p75=+0.250 pp |
| US2Y_CHG_12W | N=44; mean=+0.032 pp; median=+0.020 pp; p25=-0.022 pp; p75=+0.080 pp | N=43; mean=+0.463 pp; median=+0.290 pp; p25=+0.180 pp; p75=+0.455 pp | N=347; mean=+0.089 pp; median=+0.060 pp; p25=-0.115 pp; p75=+0.310 pp |
| US10Y_CHG_12W | N=44; mean=+0.041 pp; median=+0.050 pp; p25=-0.053 pp; p75=+0.155 pp | N=43; mean=+0.350 pp; median=+0.260 pp; p25=+0.140 pp; p75=+0.480 pp | N=347; mean=+0.026 pp; median=-0.010 pp; p25=-0.255 pp; p75=+0.280 pp |
| REAL10Y_CHG_12W | N=44; mean=-0.072 pp; median=-0.075 pp; p25=-0.162 pp; p75=+0.035 pp | N=43; mean=+0.198 pp; median=+0.190 pp; p25=+0.035 pp; p75=+0.320 pp | N=347; mean=+0.043 pp; median=+0.010 pp; p25=-0.210 pp; p75=+0.230 pp |
| VIX_CHG_12W | N=44; mean=-6.29%; median=-5.71%; p25=-19.28%; p75=+2.53% | N=43; mean=+7.82%; median=+2.48%; p25=-14.39%; p75=+22.94% | N=347; mean=+9.97%; median=-4.35%; p25=-20.37%; p75=+20.24% |
| NASDAQ_RET_12W | N=44; mean=+8.43%; median=+7.82%; p25=+4.64%; p75=+11.24% | N=43; mean=-0.06%; median=+2.02%; p25=-5.01%; p75=+5.47% | N=347; mean=+2.93%; median=+3.88%; p25=-1.43%; p75=+7.63% |
| FED_BALANCE_CHG_12W | N=44; mean=+0.84%; median=+0.43%; p25=-0.18%; p75=+2.57% | N=43; mean=+0.33%; median=-0.36%; p25=-2.03%; p75=+2.16% | N=347; mean=+2.41%; median=-0.13%; p25=-1.72%; p75=+2.64% |
| M2_CHG_12W | N=44; mean=+1.66%; median=+1.48%; p25=+1.22%; p75=+2.34% | N=43; mean=+1.51%; median=+1.13%; p25=+0.92%; p75=+1.80% | N=347; mean=+1.57%; median=+1.23%; p25=+0.58%; p75=+1.87% |

Ranked by `|median gap| / IQR(OTHER)` so percentage changes and yield changes are not mixed in raw units. Not a test.

| rank | feature | median TOP10 | median BOTTOM10 | gap | |gap|/IQR(OTHER) | IQR overlap | role |
|---|---|---|---|---|---|---|---|
| 1 | FED_FUNDS_CHG_12W | +0.000 pp | +0.250 pp | -0.250 pp | 0.96 | yes | core |
| 2 | DXY_CHG_12W | -1.99% | +1.10% | -3.09% | 0.85 | no | core |
| 3 | NASDAQ_RET_12W | +7.82% | +2.02% | +5.80% | 0.64 | yes | core |
| 4 | US2Y_CHG_12W | +0.020 pp | +0.290 pp | -0.270 pp | 0.64 | no | core |
| 5 | REAL10Y_CHG_12W | -0.075 pp | +0.190 pp | -0.265 pp | 0.60 | yes | core |
| 6 | US10Y_CHG_12W | +0.050 pp | +0.260 pp | -0.210 pp | 0.39 | yes | core |
| 7 | M2_CHG_12W | +1.48% | +1.13% | +0.36% | 0.28 | yes | DIAGNOSTIC ONLY |
| 8 | VIX_CHG_12W | -5.71% | +2.48% | -8.19% | 0.20 | yes | core |
| 9 | FED_BALANCE_CHG_12W | +0.43% | -0.36% | +0.78% | 0.18 | yes | core |

## 2. Bull continuation vs Bull failure

| feature | BULL_CONTINUATION | BULL_FAILURE |
|---|---|---|
| DXY_CHG_12W | N=105; mean=-1.02%; median=-1.39%; p25=-2.95%; p75=+0.89% | N=40; mean=+0.51%; median=+0.89%; p25=-0.30%; p75=+1.45% |
| FED_FUNDS_CHG_12W | N=105; mean=+0.129 pp; median=+0.040 pp; p25=+0.000 pp; p75=+0.250 pp | N=40; mean=+0.074 pp; median=+0.000 pp; p25=-0.020 pp; p75=+0.250 pp |
| US2Y_CHG_12W | N=105; mean=+0.024 pp; median=+0.000 pp; p25=-0.080 pp; p75=+0.090 pp | N=40; mean=+0.123 pp; median=+0.040 pp; p25=-0.122 pp; p75=+0.357 pp |
| US10Y_CHG_12W | N=105; mean=-0.012 pp; median=-0.040 pp; p25=-0.240 pp; p75=+0.150 pp | N=40; mean=+0.140 pp; median=+0.160 pp; p25=-0.250 pp; p75=+0.432 pp |
| REAL10Y_CHG_12W | N=105; mean=-0.097 pp; median=-0.090 pp; p25=-0.280 pp; p75=+0.070 pp | N=40; mean=+0.041 pp; median=+0.020 pp; p25=-0.117 pp; p75=+0.230 pp |
| VIX_CHG_12W | N=105; mean=-10.20%; median=-12.36%; p25=-24.83%; p75=+2.48% | N=40; mean=+1.21%; median=-2.23%; p25=-14.36%; p75=+11.23% |
| NASDAQ_RET_12W | N=105; mean=+7.83%; median=+6.72%; p25=+3.90%; p75=+11.30% | N=40; mean=+5.21%; median=+4.81%; p25=+2.00%; p75=+7.94% |
| FED_BALANCE_CHG_12W | N=105; mean=+2.00%; median=+0.02%; p25=-0.34%; p75=+2.19% | N=40; mean=+1.54%; median=+1.72%; p25=-0.47%; p75=+3.93% |
| M2_CHG_12W | N=105; mean=+2.44%; median=+1.51%; p25=+1.20%; p75=+2.29% | N=40; mean=+1.70%; median=+1.56%; p25=+1.09%; p75=+2.50% |

Ranked by `|median gap| / IQR(OTHER)`. Not a test.

| rank | feature | median CONT | median FAIL | gap | |gap|/IQR(OTHER) | IQR overlap | role |
|---|---|---|---|---|---|---|---|
| 1 | DXY_CHG_12W | -1.39% | +0.89% | -2.28% | 0.63 | yes | core |
| 2 | FED_BALANCE_CHG_12W | +0.02% | +1.72% | -1.70% | 0.39 | yes | core |
| 3 | US10Y_CHG_12W | -0.040 pp | +0.160 pp | -0.200 pp | 0.37 | yes | core |
| 4 | REAL10Y_CHG_12W | -0.090 pp | +0.020 pp | -0.110 pp | 0.25 | yes | core |
| 5 | VIX_CHG_12W | -12.36% | -2.23% | -10.13% | 0.25 | yes | core |
| 6 | NASDAQ_RET_12W | +6.72% | +4.81% | +1.91% | 0.21 | yes | core |
| 7 | FED_FUNDS_CHG_12W | +0.040 pp | +0.000 pp | +0.040 pp | 0.15 | yes | core |
| 8 | US2Y_CHG_12W | +0.000 pp | +0.040 pp | -0.040 pp | 0.09 | yes | core |
| 9 | M2_CHG_12W | +1.51% | +1.56% | -0.05% | 0.04 | yes | DIAGNOSTIC ONLY |

## 3. Directional checks (medians only)

No p-values. No thresholds. `>` means the left group median is larger.

### TOP10 vs REST

| feature | direction | left median | right median | role |
|---|---|---|---|---|
| DXY_CHG_12W | TOP10 < REST | -1.99% | +0.82% | core |
| FED_FUNDS_CHG_12W | TOP10 < REST | +0.000 pp | +0.040 pp | core |
| US2Y_CHG_12W | TOP10 < REST | +0.020 pp | +0.080 pp | core |
| US10Y_CHG_12W | TOP10 > REST | +0.050 pp | +0.035 pp | core |
| REAL10Y_CHG_12W | TOP10 < REST | -0.075 pp | +0.030 pp | core |
| VIX_CHG_12W | TOP10 < REST | -5.71% | -3.59% | core |
| NASDAQ_RET_12W | TOP10 > REST | +7.82% | +3.69% | core |
| FED_BALANCE_CHG_12W | TOP10 > REST | +0.43% | -0.15% | core |
| M2_CHG_12W | TOP10 > REST | +1.48% | +1.20% | DIAGNOSTIC ONLY |

### BULL_CONTINUATION vs BULL_FAILURE

| feature | direction | left median | right median | role |
|---|---|---|---|---|
| DXY_CHG_12W | CONTINUATION < FAILURE | -1.39% | +0.89% | core |
| FED_FUNDS_CHG_12W | CONTINUATION > FAILURE | +0.040 pp | +0.000 pp | core |
| US2Y_CHG_12W | CONTINUATION < FAILURE | +0.000 pp | +0.040 pp | core |
| US10Y_CHG_12W | CONTINUATION < FAILURE | -0.040 pp | +0.160 pp | core |
| REAL10Y_CHG_12W | CONTINUATION < FAILURE | -0.090 pp | +0.020 pp | core |
| VIX_CHG_12W | CONTINUATION < FAILURE | -12.36% | -2.23% | core |
| NASDAQ_RET_12W | CONTINUATION > FAILURE | +6.72% | +4.81% | core |
| FED_BALANCE_CHG_12W | CONTINUATION < FAILURE | +0.02% | +1.72% | core |
| M2_CHG_12W | CONTINUATION < FAILURE | +1.51% | +1.56% | DIAGNOSTIC ONLY |

## 4. Late-2020 vs late-2021 case weeks

These four Fridays are the Phase 3 North Star pair: similar crypto-internal Bull states, opposite 12w outcomes. Crypto internals below are copied from the catalog for context; they are not re-estimated.

### Crypto-internal reminder

| week | V1 state | MOM12 pctl | broad 4w | VOL pctl | TOVER_REL | SC12 | fut12w |
|---|---|---|---|---|---|---|---|
| 2020-11-27 | BULL_NORMAL_VOL | 0.755 | 0.740 | 0.198 | 1.025 | 43.3% | +241.0% |
| 2020-12-04 | BULL_NORMAL_VOL | 0.803 | 0.708 | 0.190 | 1.119 | 39.0% | +158.4% |
| 2021-10-29 | BULL_NORMAL_VOL | 0.729 | 0.731 | 0.299 | 0.959 | 12.1% | -40.1% |
| 2021-11-05 | BULL_NORMAL_VOL | 0.590 | 0.708 | 0.236 | 0.998 | 14.3% | -41.4% |

### Macro 12w changes at t

| week | fut12w | DXY_CHG_12W | FED_FUNDS_CHG_12W | US2Y_CHG_12W | US10Y_CHG_12W | REAL10Y_CHG_12W | VIX_CHG_12W | NASDAQ_RET_12W | FED_BALANCE_CHG_12W | M2_CHG_12W |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020-11-27 | +241.0% | -2.46% | -0.010 pp | +0.020 pp | +0.120 pp | +0.070 pp | -32.23% | +7.89% | +2.86% | +2.34% |
| 2020-12-04 | +158.4% | -3.71% | +0.000 pp | +0.030 pp | +0.300 pp | +0.060 pp | -22.63% | +14.84% | +3.03% | +2.34% |
| 2021-10-29 | -40.1% | +0.73% | -0.020 pp | +0.270 pp | +0.240 pp | +0.100 pp | +0.68% | +4.47% | +3.92% | +2.50% |
| 2021-11-05 | -41.4% | +0.89% | -0.020 pp | +0.160 pp | +0.160 pp | -0.010 pp | +6.67% | +7.75% | +3.87% | +2.50% |

Technical separation = both late-2020 values sit entirely above or entirely below both late-2021 values. Clear gap = that, plus at least 10 bp for yield/funds changes or 3 percentage points for index/credit/M2 changes. Tiny technical separations (1–2 bp Fed funds; ~0.1% Nasdaq pair gap) are not treated as material.

| feature | 2020-11-27 | 2020-12-04 | 2021-10-29 | 2021-11-05 | technically separated | clear gap | role |
|---|---|---|---|---|---|---|---|
| DXY_CHG_12W | -2.46% | -3.71% | +0.73% | +0.89% | yes | yes | core |
| FED_FUNDS_CHG_12W | -0.010 pp | +0.000 pp | -0.020 pp | -0.020 pp | yes | no | core |
| US2Y_CHG_12W | +0.020 pp | +0.030 pp | +0.270 pp | +0.160 pp | yes | yes | core |
| US10Y_CHG_12W | +0.120 pp | +0.300 pp | +0.240 pp | +0.160 pp | no | no | core |
| REAL10Y_CHG_12W | +0.070 pp | +0.060 pp | +0.100 pp | -0.010 pp | no | no | core |
| VIX_CHG_12W | -32.23% | -22.63% | +0.68% | +6.67% | yes | yes | core |
| NASDAQ_RET_12W | +7.89% | +14.84% | +4.47% | +7.75% | yes | no | core |
| FED_BALANCE_CHG_12W | +2.86% | +3.03% | +3.92% | +3.87% | yes | no | core |
| M2_CHG_12W | +2.34% | +2.34% | +2.50% | +2.50% | yes | no | DIAGNOSTIC ONLY |

### Macro levels at t

Levels of trending series (Nasdaq, Fed credit, M2) are **not** a clean 2020-vs-2021 backdrop comparison; they mix time trend with conditions. 12w changes above are the relevant contrast.

| week | DXY_LEVEL | FED_FUNDS | US2Y | US10Y | REAL10Y | VIX | NASDAQ | FED_BALANCE_SHEET | M2 |
|---|---|---|---|---|---|---|---|---|---|
| 2020-11-27 | 113.18 | 0.080 | 0.160 | 0.840 | -0.910 | 20.84 | 12,205.8 | 7,176,567.0 | 18,759.9 |
| 2020-12-04 | 111.78 | 0.090 | 0.160 | 0.970 | -0.920 | 20.79 | 12,464.2 | 7,181,887.0 | 18,759.9 |
| 2021-10-29 | 114.13 | 0.080 | 0.480 | 1.550 | -0.960 | 16.26 | 15,498.4 | 8,517,364.0 | 20,985.5 |
| 2021-11-05 | 114.07 | 0.080 | 0.390 | 1.450 | -1.090 | 16.48 | 15,971.6 | 8,536,560.0 | 20,985.5 |

## Answers

### 1. Which macro variables differ most between TOP10 and BOTTOM10?

Largest standardized median gaps among **core** series: `FED_FUNDS_CHG_12W`, `DXY_CHG_12W`, `NASDAQ_RET_12W`. See the ranked table. IQR overlap is a descriptive flag, not a test. IQRs do not overlap for: `DXY_CHG_12W`, `US2Y_CHG_12W`. `FED_FUNDS_CHG_12W` ranks high here but **flips direction** on Bull continuation vs failure, so it is not a move-forward candidate. `M2_CHG_12W` is excluded from this ranking’s interpretation even if the gap is large.

### 2. Which differ between Bull continuation and Bull failure?

Largest standardized median gaps among **core** series: `DXY_CHG_12W`, `FED_BALANCE_CHG_12W`, `US10Y_CHG_12W`. Continuation vs failure is the more relevant split for the North Star (already-Bull weeks that then worked vs failed). Every IQR overlaps here.

### 3. What clearly separates late-2020 from late-2021?

On 12w **changes**, a **clear** 2020-vs-2021 pair gap exists for: `DXY_CHG_12W`, `US2Y_CHG_12W`, `VIX_CHG_12W`.
Technically separated but **not** a clear gap: `FED_FUNDS_CHG_12W`, `NASDAQ_RET_12W`, `FED_BALANCE_CHG_12W`.

Do **not** read this as: macro caused the 2020 rally or the 2021 drawdown.

### 4. What does NOT separate them?

Core 12w changes whose 2020 pair overlaps the 2021 pair: `US10Y_CHG_12W`, `REAL10Y_CHG_12W`. Technically separated-but-tiny gaps (Fed funds, Nasdaq pair edge, Fed credit still expanding in both years) are **not** treated as what separated the episodes. Trending **levels** (Nasdaq index, Fed credit stock, M2 stock) differ across years partly because time passed; they are not treated as separators.

### 5. Does macro look promising enough to justify a walk-forward test?

Only as a **limited** walk-forward test, not as a model and not as a trading rule. TOP10 vs BOTTOM10 IQRs do **not** overlap for: `DXY_CHG_12W`, `US2Y_CHG_12W`. Every Bull continuation vs failure IQR **does** overlap. Phase 5 already showed crypto-only does not beat simple benchmarks. The only honest next question is whether dollar / yield-backup 12w changes add anything **out of sample**. `FED_FUNDS_CHG_12W` and `FED_BALANCE_CHG_12W` change sign across splits and should not be walked forward from this file.

### 6. Which variables should move forward?

`DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`; plus `NASDAQ_RET_12W` as a risk-on control

Move-forward here means **eligible for a later walk-forward specification**, not selected on 12w returns in this file. No coefficients. No frozen cut.

### 7. Which remain diagnostic only?

- `FED_FUNDS_CHG_12W` and `FED_BALANCE_CHG_12W` — sign flips across TOP10/BOTTOM10 vs Bull continuation/failure.
- `M2_CHG_12W` — HIGH lookahead, monthly lag, revised history, not vintage.
- `HY_SPREAD` — absent in Phase 6A; not invented here.
- Nasdaq **level** and Fed **balance-sheet level** — trending stocks; use 12w changes if used at all.
- `NASDAQ_RET_12W` — usable as a risk-on control, not as independent ‘macro policy’ information.

## Guardrails honored

- no threshold optimization
- no macro regimes / scores
- no regression / logistic / ML
- no 2024–2026
- Phase 3 catalog and Phase 6A panel were not modified

## Summary file

`macro_forensic_summary.csv` is long format: comparison, group, feature, N, mean, median, p25, p75.

Comparisons: `future_12w_extremes` (TOP10 / BOTTOM10 / OTHER), `top10_vs_rest` (TOP10 / REST), `bull_12w` (BULL_CONTINUATION / BULL_FAILURE). Rows=63.

