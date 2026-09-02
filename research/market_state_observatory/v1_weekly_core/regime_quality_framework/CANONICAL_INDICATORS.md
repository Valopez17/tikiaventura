# CANONICAL INDICATORS — Crypto Market State Observatory

## 0. Purpose

This document is the canonical specification for the indicators used by the Crypto Market State Observatory.

Its purpose is to define, before looking at new out-of-sample results:

- what each variable means;
- how it is constructed;
- what data it uses;
- what lookback windows are allowed;
- how it is normalized;
- what role it plays in market-state classification;
- what it must NOT be interpreted as;
- what horizons will be evaluated.

This document is a methodology contract. Any future implementation should either follow it or explicitly document a deviation.

Primary forecasting/evaluation horizons:

- **4 weeks**
- **12 weeks**

A 1-week horizon may remain as a diagnostic only, but it is not a primary objective.

---

# 1. Data frequency and timing convention

Primary frequency:

- Weekly
- Friday observations
- State at week `t` uses only information available through week `t`
- Forward outcomes start at `t+1`

No future information may enter state construction.

Primary analysis sample currently available:

- 2015–2023 frozen historical panel

Planned final OOS period:

- 2024–2026

The 2024–2026 period should remain untouched by threshold selection or model design until the framework is frozen.

---

# 2. Eligible crypto universe

Primary universe at week `t`:

A coin is eligible if:

1. it is not classified as a stablecoin;
2. market cap >= USD 10M;
3. it has at least 26 observed weekly price points;
4. current weekly return is finite;
5. market cap is finite and > 0;
6. volume is finite and > 0;
7. weekly price is finite and > 0.

No asset is removed retroactively because it later delists.

Robustness universes:

- >= USD 1M
- >= USD 10M — PRIMARY
- >= USD 50M

Thresholds must be frozen before evaluating future performance.

---

# 3. Market return

The aggregate crypto market return is value weighted.

For week `t`:

`market_return_t = Σ w_(i,t-1) * r_(i,t)`

where:

`w_(i,t-1) = lagged_market_cap_i / Σ lagged_market_cap`

Only assets eligible at `t` are considered.

Lagged market cap is used for weights to reduce contemporaneous weighting bias.

Input weekly log returns must be converted to simple returns before aggregation:

`simple_return = exp(log_return) - 1`

---

# 4. Market index

Initialize:

`MarketIndex = 100`

Then compound simple weekly market returns:

`Index_t = Index_(t-1) * (1 + market_return_t)`

The index is a research construct, not an investable benchmark unless later explicitly replicated as such.

---

# 5. Momentum

Momentum captures recent directional persistence in the value-weighted crypto market.

## 5.1 MOM_4W

Cumulative simple market return over the most recent 4 weeks through `t`.

`MOM_4W_t = Π(1 + market_return) - 1`

over weeks `t-3 ... t`.

Interpretation:

- positive = market has appreciated over the last ~1 month;
- negative = market has declined.

## 5.2 MOM_12W

Cumulative simple market return over the most recent 12 weeks through `t`.

Same construction over weeks `t-11 ... t`.

Interpretation:

- short/medium-term market direction over roughly 3 months.

## 5.3 Momentum intensity

Binary sign is insufficient.

Create expanding historical percentiles:

- `MOM_4W_PERCENTILE`
- `MOM_12W_PERCENTILE`

At time `t`, percentile must use only observations available through `t`.

Purpose:

distinguish weak positive momentum from historically extreme positive momentum.

Example conceptually:

- MOM > 0 = positive direction;
- high percentile = strong historical intensity.

Do NOT freeze a "Strong Bull" threshold simply because one value produces the best outcome in-sample.

---

# 6. Broad breadth

For each eligible coin calculate 4-week cumulative simple return:

`coin_return_4w_i,t = Π(1 + r_i) - 1`

over the current and prior 3 Friday weeks.

If the 4-week path is incomplete, that coin is omitted from the breadth denominator.

Then:

`broad_breadth_4w = count(coin_return_4w > 0) / count(finite coin_return_4w)`

All eligible coins receive equal weight.

Interpretation:

- 0.80 = 80% of eligible coins rose over the previous four weeks.
- 0.30 = only 30% participated positively.

Also retain:

- median coin 4w return;
- p25 coin 4w return;
- p75 coin 4w return;
- number of breadth-eligible coins.

---

# 7. Large-cap breadth

Each week rank eligible coins by size.

Primary large-cap universe:

- top 100 by market cap.

Preferred predictive implementation:

- use lagged market cap to define the top 100.

If fewer than 100 coins are eligible, use all eligible assets.

Then:

`largecap_breadth_4w = fraction of top-100 coins with positive 4w return`

Also retain:

- `largecap_median_return_4w`

Purpose:

distinguish:

- market-wide participation;
- large-cap-led rallies;
- small/mid-cap participation.

---

# 8. Breadth gap

`breadth_gap = largecap_breadth_4w - broad_breadth_4w`

Interpretation:

- positive: large caps are participating more broadly than the total universe;
- negative: participation is stronger outside the large-cap group.

Descriptive only. No causal interpretation.

---

# 9. Breadth quality

Existing diagnostic labels:

## BROAD

- broad breadth >= 0.60
- large-cap breadth >= 0.60

## NARROW_LARGECAP

- large-cap breadth >= 0.60
- broad breadth < 0.50

## WEAK

- broad breadth < 0.40
- large-cap breadth < 0.40

## MIXED

All other finite combinations.

These labels do not automatically define Bull or Bear. They describe participation quality.

---

# 10. Volatility

## 10.1 VOL_12W

Sample standard deviation of the last 12 weekly market returns:

`VOL_12W = std(last 12 weekly market returns, ddof=1)`

Primary measure is not annualized.

## 10.2 VOL_PERCENTILE

Expanding empirical percentile of `VOL_12W`, using only history available through `t`.

Current V1 overlay:

- NORMAL_VOL if percentile < 0.70
- HIGH_VOL if percentile >= 0.70

The 0.70 threshold is frozen for the V1 classification but may be tested as a research feature in the quality framework.

Volatility is not direction.

High volatility may occur in both bull and bear environments.

---

# 11. Turnover

At coin level:

`turnover_i,t = volume_i,t / market_cap_i,t`

Primary market summary:

`market_turnover = cross-sectional median turnover`

Also retain:

- p75 turnover.

## 11.1 TURNOVER_RELATIVE

`TURNOVER_RELATIVE = current market_turnover / trailing 12-week median market_turnover`

Interpretation:

- >1 = activity above its recent median;
- <1 = activity below its recent median.

## 11.2 TURNOVER_PERCENTILE

Expanding historical percentile of market turnover.

Turnover is a liquidity/activity proxy, not a direct measure of true executable liquidity.

CMC-reported volume may contain wash trading or venue-quality noise.

---

# 12. Stablecoin liquidity

Stablecoins are excluded from return and breadth universes but may be used as a crypto-native liquidity proxy.

Construct:

- `STABLECOIN_MCAP`
- `STABLECOIN_MCAP_4W_CHANGE`
- `STABLECOIN_MCAP_12W_CHANGE`
- `STABLECOIN_LIQ_PERCENTILE`

Primary changes:

`S_t / S_(t-4) - 1`

and

`S_t / S_(t-12) - 1`

Stablecoin expansion must NOT automatically be labeled bullish.

It is a hypothesis to test.

Known limitations:

- wrappers may double-count;
- historical stablecoin coverage may be incomplete;
- classification must be deterministic and documented.

---

# 13. Current baseline direction state

The existing V1 state remains a baseline, not the final regime-quality model.

## BULL

- MOM_4W > 0
- MOM_12W > 0
- broad_breadth_4w > 0.50

## BEAR

- MOM_4W < 0
- MOM_12W < 0
- broad_breadth_4w < 0.50

## NEUTRAL

All other cases.

Then add volatility overlay:

- BULL_NORMAL_VOL
- BULL_HIGH_VOL
- NEUTRAL_NORMAL_VOL
- NEUTRAL_HIGH_VOL
- BEAR_NORMAL_VOL
- BEAR_HIGH_VOL

This is the benchmark classification to beat.

---

# 14. Regime intensity framework

The next research layer should represent five dimensions:

`Direction + Strength + Participation + Stress + Liquidity`

## 14.1 Direction

Inputs:

- MOM_4W
- MOM_12W

## 14.2 Strength

Inputs:

- MOM_4W_PERCENTILE
- MOM_12W_PERCENTILE
- optionally acceleration of momentum

Possible exploratory intensity buckets should be pre-specified rather than optimized after seeing outcomes.

Use either:

- fixed percentile buckets; or
- a small frozen grid.

Recommended percentile research buckets:

- Low: < 40th percentile
- Moderate: 40th–70th
- Strong: 70th–90th
- Extreme: >= 90th

These are research buckets, not yet final market-state thresholds.

## 14.3 Participation

Inputs:

- broad_breadth_4w
- largecap_breadth_4w
- breadth_gap
- breadth_quality

Possible frozen research grid:

- < 40%
- 40–50%
- 50–60%
- 60–70%
- 70–80%
- >= 80%

Purpose:

test whether forward distributions improve monotonically as participation broadens.

## 14.4 Stress

Inputs:

- VOL_PERCENTILE
- current drawdown from a trailing high, if added later
- cross-sectional dispersion, if added later

Initial stress dimension should remain parsimonious.

## 14.5 Liquidity

Inputs:

- TURNOVER_RELATIVE
- TURNOVER_PERCENTILE
- STABLECOIN_MCAP_4W_CHANGE
- STABLECOIN_MCAP_12W_CHANGE

Potential future inputs:

- funding
- open interest
- basis
- liquidations
- exchange flows
- bid/ask depth

These are not part of the current phase unless explicitly introduced later.

---

# 15. Bull quality concepts to test

Do not hard-code these as truths yet.

The following are hypotheses.

## Emerging Bull

Possible characteristics:

- MOM_4W turns positive;
- MOM_12W is weakly positive or improving;
- breadth moves above ~50%;
- large caps begin confirming;
- volatility not necessarily low.

## Confirmed Bull

Possible characteristics:

- MOM_4W positive;
- MOM_12W clearly positive;
- broad breadth > 50–60%;
- large-cap breadth confirms.

## Strong Bull

Possible characteristics:

- momentum percentiles high;
- broad breadth >= 60–70%;
- large-cap breadth >= 60–70%;
- no severe stress deterioration.

## Fragile / Late Bull

Possible characteristics:

- headline momentum remains positive;
- broad breadth weakens;
- large-cap breadth diverges from broad breadth;
- volatility rises;
- liquidity/activity weakens.

These are candidate descriptions to test, not conclusions.

---

# 16. Bear quality concepts to test

## Emerging Bear

Possible characteristics:

- MOM_4W negative;
- MOM_12W still positive or rolling over;
- breadth drops below 50%;
- participation deteriorates.

## Confirmed Bear

Possible characteristics:

- MOM_4W < 0;
- MOM_12W < 0;
- broad breadth < 50%.

## Strong Bear

Possible characteristics:

- momentum in low historical percentiles;
- breadth < 40%;
- large caps also weak;
- volatility/stress elevated.

## Bear Exhaustion

Possible characteristics:

- momentum remains negative;
- breadth stops worsening or begins improving;
- volatility remains high but starts declining;
- liquidity/participation improves.

Again: hypotheses, not labels to freeze before validation.

---

# 17. Optional new diagnostics to consider

Only add if they materially improve discrimination and remain simple.

## 17.1 Momentum acceleration

Example:

`MOM_ACCEL = MOM_4W - prior MOM_4W`

or a cleaner slope/change definition.

Purpose:

distinguish:

- strong but slowing bull;
- weak but accelerating bull.

## 17.2 Trailing drawdown

Example:

distance of market index from its trailing 12- or 26-week high.

Purpose:

distinguish:

- new breakout / near-high regime;
- rebound while still deeply below prior peak.

## 17.3 Cross-sectional dispersion

Standard deviation or robust dispersion of individual coin returns.

Purpose:

measure disagreement/fragmentation across the market.

Do not include automatically. Test incremental value.

---

# 18. Forward outcomes

Primary:

## 4 weeks

- future cumulative return;
- positive-return indicator;
- > +10% indicator;
- < -10% indicator;
- max drawdown;
- max run-up.

## 12 weeks

Same outputs.

Primary questions:

1. Does the state predict direction?
2. Does it change the magnitude distribution?
3. Does it change downside risk?
4. Does bull quality matter?
5. Does bear quality matter?

---

# 19. Historical attribution of extreme bull episodes

For major future-return episodes, add contribution decomposition.

At weekly level:

`contribution_i,t = weight_(i,t-1) * return_i,t`

Aggregate over a 4w or 12w horizon consistently.

For each major episode report:

- total market return;
- BTC contribution;
- ETH contribution;
- top-10 contributions;
- large-cap contribution;
- rest-of-market contribution;
- broad breadth;
- large-cap breadth.

Purpose:

determine whether an explosive bull outcome was:

- BTC-led;
- ETH/large-cap-led;
- broad-market;
- concentrated in a few assets.

---

# 20. Macro layer — later phase

Macro is not used to redefine the crypto state until tested.

Candidate variables:

- Global M2 or carefully constructed global liquidity proxy;
- US M2;
- Federal Reserve balance sheet;
- DXY / broad dollar;
- Fed Funds;
- US 2Y yield;
- 10Y real yield;
- VIX;
- high-yield credit spread;
- Nasdaq / risk-asset momentum;
- financial conditions index.

Important:

Levels and changes may both matter.

Test lags such as:

- 4 weeks
- 8 weeks
- 12 weeks

without optimizing excessively.

Main comparison:

`Crypto-only model` vs `Crypto + Macro model`

Macro survives only if it improves true OOS performance.

---

# 21. Validation rules

The goal is prediction over 4–12 weeks, not retrospective storytelling.

Required validation:

1. walk-forward;
2. information available only as of `t`;
3. minimum historical sample before forecast;
4. no threshold selection using final OOS;
5. 2024–2026 preserved as final untouched OOS;
6. compare against simple benchmarks.

Metrics:

- directional accuracy;
- balanced accuracy if classes become imbalanced;
- Brier score;
- log loss;
- calibration;
- AUC where appropriate;
- median future return;
- downside-tail frequency;
- max-drawdown distribution.

A state should be allowed to return:

`NO EDGE / UNCERTAIN`

rather than forcing Bull or Bear prediction.

---

# 22. Canonical principle

The final observatory should answer:

> Given the information observable today, what market regime are we in, how strong and healthy is that regime, what historically happened over the next 4–12 weeks in comparable states, and how uncertain is that evidence?

It should NOT claim certainty or long-horizon prophecy.
