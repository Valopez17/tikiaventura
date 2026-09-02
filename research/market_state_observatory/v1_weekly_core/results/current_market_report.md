# Crypto Market State Observatory v1 — current market report

**As-of week (last Friday in the frozen panel): 2023-12-29**

This is **not** a live 2026-08-28 snapshot. The input panel ends
2023-12-29. No new CoinMarketCap download was performed.

Sample in this file: 2015-01-02 → 2023-12-29 (Friday weeks).
Primary universe: observatory_eligible with market_cap >= $10,000,000.

Language note: frequencies below are **historical conditional frequencies**,
not “true probabilities” that the market will rise from the current week.

---

## 1. ¿Cuál es el estado actual?

**BULL_NORMAL_VOL**

- state_direction: **BULL**
- volatility_state: **NORMAL_VOL**
- breadth_quality (diagnostic only): **BROAD**
- n_eligible_coins: 878
- n_largecap_coins used: 100

## 2. ¿Por qué se clasifica así?

Direction is BULL because MOM_4W=13.88%, MOM_12W=54.50%, broad_breadth_4w=0.765.
BULL requires MOM_4W>0 AND MOM_12W>0 AND broad_breadth_4w>0.50. BEAR requires MOM_4W<0 AND MOM_12W<0 AND broad_breadth_4w<0.50. Any other combination is NEUTRAL.
Volatility overlay is NORMAL_VOL because VOL_PERCENTILE=0.233 and HIGH_VOL is defined as VOL_PERCENTILE >= 0.70.
Combined market_state = BULL_NORMAL_VOL.

Thresholds are frozen and were not tuned on these results.

## 3. ¿Cuál es MOM_4W?

**13.88%** (cumulative simple return of the value-weighted market index over the last 4 weeks through t).

## 4. ¿Cuál es MOM_12W?

**54.50%** (cumulative simple return of the value-weighted market index over the last 12 weeks through t).

## 5. ¿Cuál es broad breadth?

**0.7654** = share of observatory_eligible coins with 4-week cumulative simple return > 0.
Equal-weight across coins. Coins without a complete 4-week calendar window are omitted from the denominator.

n coins in the breadth denominator this week: 878.

## 6. ¿Cuál es large-cap breadth?

**0.9000** = same 4-week up-share inside the current week’s top 100 eligible coins by contemporaneous market cap.
If a week has fewer than 100 eligible coins, all eligible coins are used.
Weeks with <100 eligible coins in this sample: 104.

largecap_median_return_4w this week: 23.34%.

## 7. ¿El rally/caída es broad o narrow?

**BROAD (both universes have breadth >= 0.60)**

- breadth_gap = largecap_breadth_4w − broad_breadth_4w = **0.1346**
- median_coin_return_4w (eligible, equal-weight) = 15.02%
- Interpretation is descriptive: gap >> 0 means large caps had a higher up-share than the full eligible universe; gap << 0 means the opposite. No causal claim.

## 8. ¿Cuál es VOL_PERCENTILE?

**0.2327**

VOL_12W (sample std of last 12 weekly market simple returns, not annualized): 0.0642.
HIGH_VOL iff VOL_PERCENTILE >= 0.70. Expanding percentile uses VOL_12W history through t only.

## 9. ¿Cuál es TURNOVER_RELATIVE?

**1.0048**

market_turnover (median volume/market_cap among eligible): 0.040902.
TURNOVER_RELATIVE = market_turnover / trailing 12-week median of market_turnover (window includes t).
TURNOVER_PERCENTILE (expanding, on market_turnover): 0.6270.

## 10. ¿Cómo está cambiando stablecoin market cap?

STABLECOIN_MCAP (sum of observatory stablecoin market caps): **131.87 billion USD** (raw 131871664093).

- STABLECOIN_MCAP_4W_CHANGE = **2.83%**
- STABLECOIN_MCAP_12W_CHANGE = **6.72%**
- STABLECOIN_LIQ_PERCENTILE (expanding, on the level): 0.8447

Stablecoin growth is **measured**, not interpreted as bullish. The observatory uses a curated symbol list, not the Hsieh `is_stablecoin` flag. Wrapped listings can double-count some USD supply. See README limitations.

## 11. ¿Cuántas observaciones históricas existen en el mismo state?

**97** weeks have market_state = BULL_NORMAL_VOL in the sample (including the current week).
Forward-outcome statistics below use weeks in that state that still have a complete forward path, so N is smaller for 12-week outcomes.

## 12. ¿Qué retorno futuro tuvo históricamente ese state?

Historical conditional distribution of the **value-weighted market**, after weeks classified as **BULL_NORMAL_VOL**:

| horizon | N | mean | median |
|---|---|---|---|
| 1w | 96 | 3.40% | 1.93% |
| 4w | 93 | 13.47% | 9.40% |
| 12w | 87 | 50.96% | 24.18% |

These are in-sample historical frequencies. They are not a forecast.

## 13. ¿Cuál fue P(return > 0) históricamente?

Historical frequency of a **positive** subsequent market return after BULL_NORMAL_VOL:

- 1w: 62.50% (N=96)
- 4w: 73.12% (N=93)
- 12w: 74.71% (N=87)

Also recorded (not a trading rule):

- 4w historical frequency of return > 10%: 48.39%
- 4w historical frequency of return < −10%: 9.68%
- 12w historical frequency of return > 10%: 65.52%
- 12w historical frequency of return < −10%: 18.39%

## 14. ¿Cuál fue el drawdown histórico típico después de ese state?

After weeks in BULL_NORMAL_VOL:

- 4w median max drawdown: -7.47%; historical frequency of max drawdown ≤ −10%: 38.71%
- 12w median max drawdown: -16.24%; historical frequency of max drawdown ≤ −10%: 82.76%
- 4w median max runup: 13.25%
- 12w median max runup: 35.22%

Max drawdown is peak-to-trough on the future wealth path starting at 1 at t. Max runup is the maximum of (wealth_k − 1) vs the level at t.

## 15. ¿Qué 10 semanas históricas son más similares a la actual?

Standardization uses z-scores estimated on all finite weeks through 2023-12-29 (the last sample point). Distance is Euclidean in that z-space. K=25 is frozen. Current week and the prior 12 weeks are excluded. Weeks with any analog-vector NaN are excluded.
Stablecoin 4-week change IS in the analog vector.

| rank | week | state | breadth_quality | distance | future_1w | future_4w | future_12w | max_dd_12w | max_ru_12w |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2021-10-29 | BULL_NORMAL_VOL | BROAD | 0.497 | 1.64% | -9.82% | -40.08% | -43.17% | 5.44% |
| 2 | 2021-11-05 | BULL_NORMAL_VOL | BROAD | 0.535 | 3.74% | -10.12% | -41.35% | -43.47% | 3.74% |
| 3 | 2020-08-21 | BULL_NORMAL_VOL | BROAD | 0.577 | 0.25% | -6.28% | 26.13% | -10.98% | 26.13% |
| 4 | 2023-02-17 | BULL_NORMAL_VOL | BROAD | 0.596 | -5.05% | 5.59% | 0.28% | -17.64% | 16.50% |
| 5 | 2020-08-28 | BULL_NORMAL_VOL | BROAD | 0.603 | -8.33% | -9.52% | 40.37% | -10.98% | 40.37% |
| 6 | 2021-11-12 | BULL_NORMAL_VOL | BROAD | 0.612 | -8.02% | -24.56% | -37.33% | -43.47% | 0.00% |
| 7 | 2020-12-04 | BULL_NORMAL_VOL | BROAD | 0.629 | -3.61% | 40.89% | 158.41% | -18.23% | 216.03% |
| 8 | 2020-11-27 | BULL_NORMAL_VOL | BROAD | 0.637 | 7.90% | 31.11% | 240.99% | -10.38% | 240.99% |
| 9 | 2020-06-12 | BULL_NORMAL_VOL | BROAD | 0.638 | -2.08% | 0.76% | 20.82% | -11.12% | 35.93% |
| 10 | 2021-10-22 | BULL_NORMAL_VOL | BROAD | 0.700 | 4.68% | 1.53% | -21.94% | -32.46% | 10.38% |

Among the 10 nearest analogs with available forward paths:
- 1w median future market return: -0.92% (historical frequency >0: 50.00%, n=10)
- 4w median future market return: -2.76% (historical frequency >0: 50.00%)
- 12w median future market return: 10.55% (historical frequency >0: 60.00%, n=10)
- 12w median max drawdown: -17.94%
- 12w median max runup: 21.31%
These analog forward numbers are historical descriptions of similar weeks. They are not a forecast of the current week.

Full top 25: `results/current_historical_analogs.csv`.

## 16. ¿Qué ocurrió después de esos 10 episodios?

Covered in the analog table and summary bullets in section 15. Individual analog weeks can have missing 12-week outcomes near the sample end; those cells are NA.

## 17. ¿Cuál es la transición más frecuente desde el state actual?

Most frequent next combined state historically, given BULL_NORMAL_VOL: **BULL_NORMAL_VOL (count=71, historical frequency=73.96%)**

Full empirical counts (no smoothing):

- BULL_NORMAL_VOL → BULL_NORMAL_VOL: count=71, historical frequency=73.96%
- BULL_NORMAL_VOL → NEUTRAL_NORMAL_VOL: count=19, historical frequency=19.79%
- BULL_NORMAL_VOL → BULL_HIGH_VOL: count=6, historical frequency=6.25%

## 18. ¿Estamos cerca de algún threshold de cambio de estado?

No forecast. Objective distances to the **frozen** classification thresholds:

- MOM_4W is 13.88% vs the 0 sign threshold (absolute distance 13.88%).
- MOM_12W is 54.50% vs the 0 sign threshold (absolute distance 54.50%).
- broad_breadth_4w is 0.765 vs 0.50 (absolute distance 0.265).
- VOL_PERCENTILE is 0.233 vs 0.70 (absolute distance 0.467).

- No frozen threshold is unusually close; see the distances above. This is not a prediction that the state will persist or change.

---

## Universe robustness (current week only)

Primary diagnosis uses $10M. Same last week under $1M / $10M / $50M:

- universe_1m: state=BULL_NORMAL_VOL, MOM_4W=13.87%, MOM_12W=54.44%, broad_breadth_4w=0.724, largecap_breadth_4w=0.900
- universe_10m: state=BULL_NORMAL_VOL, MOM_4W=13.88%, MOM_12W=54.50%, broad_breadth_4w=0.765, largecap_breadth_4w=0.900
- universe_50m: state=BULL_NORMAL_VOL, MOM_4W=13.91%, MOM_12W=54.83%, broad_breadth_4w=0.796, largecap_breadth_4w=0.900

See `results/universe_robustness.csv`.

---

## Construction reminders (audit)

- Input weekly_return in the panel is a **log** return. Observatory converts to simple via exp(r)−1 before weighting, compounding, breadth, and volatility.
- market_return_t = sum(w_i,t−1 * simple_return_i,t) among observatory_eligible at t. Weights are lagged market cap, renormalized to 1.
- market_index starts at 100 and compounds simple market_return.
- observatory_eligible is **not** Hsieh `eligible`. Rule is week-by-week, no future information, delisted coins kept while they appear.
- Forward-return columns are **not** inputs to state, breadth_quality, analogs’ feature vector construction, or volatility labels.
