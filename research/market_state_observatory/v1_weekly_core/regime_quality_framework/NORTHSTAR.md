# NORTHSTAR — Crypto Market State Observatory

## 1. North Star

Build a quantitative market-state system capable of answering:

> **Given everything observable today, what is the current crypto market regime, how strong and healthy is it, and what does the historical evidence imply for the next 4–12 weeks?**

The objective is not to predict an exact future BTC price.

The objective is not to forecast a multi-year crypto cycle.

The objective is to create a disciplined, statistically validated framework for differentiating:

- emerging bull;
- confirmed bull;
- strong bull;
- fragile / late bull;
- emerging bear;
- confirmed bear;
- strong bear;
- bear exhaustion;
- neutral / uncertain states.

The system must be allowed to say:

> **NO EDGE / UNCERTAIN**

when the evidence is weak.

---

# 2. Primary decision horizon

The system is optimized for research and decision support over:

- **4 weeks**
- **12 weeks**

A 1-week view may be retained as a secondary diagnostic.

Long-term cycle prediction is outside the North Star.

---

# 3. Core research problem

The existing V1 can identify a simple state such as:

`BULL_NORMAL_VOL`

but that label is too coarse.

Historically, two weeks can both look like healthy Bull states internally while producing radically different futures.

Examples already observed include:

- late 2020 Bull-like states followed by extremely strong 12-week returns;
- late 2021 Bull-like states followed by large negative 12-week outcomes.

Therefore the central research question is:

> **What observable characteristics distinguish a Bull with room to continue from a Bull that is becoming fragile or approaching regime transition?**

The symmetric question applies to Bear states.

---

# 4. Core architecture

The market state should be decomposed into:

`Direction + Strength + Participation + Stress + Liquidity`

## Direction

Is the market moving up, down, or mixed?

## Strength

How strong is that momentum relative to its own history?

## Participation

How much of the crypto universe is participating?

## Stress

Is volatility / market instability low, normal, elevated, or extreme?

## Liquidity

Is crypto-native liquidity/activity expanding or contracting?

Later, a macro layer is added separately.

---

# 5. Crypto-only state

The first predictive system must use only crypto-native information.

Core inputs:

- MOM_4W
- MOM_12W
- momentum percentiles
- broad breadth
- large-cap breadth
- breadth gap
- breadth quality
- VOL_12W
- VOL_PERCENTILE
- turnover
- turnover relative
- stablecoin market-cap growth

Potential additions must earn their place statistically.

Avoid adding indicators because they sound plausible.

---

# 6. Regime quality

The Observatory should not stop at:

`Bull / Neutral / Bear`

It should quantify quality.

Target conceptual output:

> BULL — Strong Momentum — Broad Participation — Normal Stress — Liquidity Expanding

versus:

> BULL — Strong Momentum — Narrowing Participation — Rising Stress — Liquidity Contracting

Both may be Bull directionally.

Their future 4–12 week distributions may be very different.

That difference must be tested.

---

# 7. Main hypotheses

## H1 — Bull strength matters

Higher momentum intensity should be associated with different forward-return distributions than weak positive momentum.

## H2 — Breadth matters

Bull states with broad participation should differ from large-cap-only or narrow participation states.

## H3 — Stress matters

Bull states under normal volatility may behave differently from Bull states under high or rising volatility.

## H4 — Liquidity matters

Bull states with expanding crypto-native liquidity/activity may differ from Bull states with contracting liquidity/activity.

## H5 — Quality interactions matter

A combined state such as:

`Strong + Broad + Normal Stress + Liquidity Up`

may have a different 4–12 week distribution from:

`Strong + Narrow + High Stress + Liquidity Down`.

## H6 — Macro may distinguish otherwise similar crypto states

Crypto-only variables may fail to distinguish episodes such as late 2020 from late 2021.

A macro layer may improve discrimination.

This must be proven OOS.

---

# 8. What success looks like

Success is NOT:

- one high in-sample accuracy number;
- one spectacular historical episode;
- finding the threshold with the best historical result;
- a chart that looks convincing.

Success means:

1. state definitions are known before final OOS;
2. forward outcomes differ economically and statistically across states;
3. results survive walk-forward evaluation;
4. results are reasonably stable across time;
5. results are not driven by a few bull-run outliers;
6. the model adds value over simple unconditional/base-rate benchmarks;
7. 2024–2026 final OOS remains credible;
8. uncertainty is explicitly reported.

---

# 9. Required outputs from the final observatory

For any week `t`, the system should eventually output something like:

## Current state

- Direction: Bull
- Strength: Strong
- Participation: Broad
- Stress: Normal
- Liquidity: Expanding
- Macro environment: Supportive / Neutral / Restrictive
- Confidence / evidence quality: High / Moderate / Low

## 4-week historical evidence

- historical conditional frequency positive;
- median return;
- p25 / p75;
- probability of > +10%;
- probability of < -10%;
- typical max drawdown.

## 12-week historical evidence

Same metrics.

## Regime transition risk

- probability/frequency of remaining in same state;
- frequency of moving to Neutral;
- frequency of moving to Bear;
- objective deterioration indicators.

## Historical analogs

- nearest historical episodes;
- their state characteristics;
- what happened 4 and 12 weeks later.

## Uncertainty

- sample size;
- calibration quality;
- OOS performance;
- whether the signal is actionable or NO EDGE.

---

# 10. Extreme episode attribution

The Observatory must explain where extreme market returns came from.

For major 4w/12w episodes, report:

- BTC contribution;
- ETH contribution;
- top large-cap contribution;
- rest-of-market contribution;
- broad participation.

This prevents a market-wide return from being misread as broad-based if it was concentrated in a small number of large assets.

---

# 11. Macro North Star

Macro is a second layer, not a replacement for crypto internals.

Target comparison:

`Model A = Crypto Only`

vs

`Model B = Crypto + Macro`

Question:

> Does macro materially improve 4- and 12-week OOS discrimination?

Candidate macro dimensions:

- global liquidity;
- dollar;
- rates;
- real yields;
- volatility/risk;
- credit;
- equity risk appetite.

If macro does not improve OOS performance, it is excluded.

---

# 12. Final validation philosophy

The final model should be designed so that a hypothetical analyst standing at week `t` could have produced the same output using only information available at `t`.

No future information.

No retrospective threshold tuning.

No choosing the best model after observing 2024–2026.

Preferred development structure:

- Research / design: 2015–2020
- Validation / freeze: 2021–2023
- Final untouched OOS: 2024–2026

Exact split may be adjusted only before final OOS is examined, with rationale documented.

---

# 13. Final target

The project succeeds when it can make a statement like:

> “The market is currently in a strong Bull regime with broad participation and normal stress. Historically, comparable states had favorable 4-week and 12-week distributions, but liquidity is weakening and the macro layer resembles historical transition periods. Evidence is therefore positive but deteriorating.”

Or:

> “The market is technically Bull, but participation is narrow, volatility is rising, and liquidity is contracting. Historical evidence does not provide a reliable directional edge over the next 4–12 weeks. Classification: NO EDGE / transition risk elevated.”

That is the North Star.
