# ROADMAP — Crypto Market State Observatory

## Phase 0 — Preserve the existing V1

Do not overwrite the current V1 outputs.

Existing folder:

`research/market_state_observatory/v1_weekly_core/`

Create a new research subfolder:

`research/market_state_observatory/v1_weekly_core/regime_quality_framework/`

This folder contains documentation and the next analytical stages.

The current V1 remains the baseline benchmark.

---

# Phase 1 — Freeze canonical definitions

Create / maintain:

- `CANONICAL_INDICATORS.md`
- `NORTHSTAR.md`
- `ROADMAP.md`

Goal:

lock terminology, formulas, horizons, and validation principles before running the next tests.

No result-driven threshold changes.

---

# Phase 2 — Audit the existing V1

Before extending the model, verify:

1. weekly return convention;
2. market weighting;
3. eligibility;
4. breadth;
5. large-cap definition;
6. volatility percentiles;
7. turnover;
8. stablecoin construction;
9. forward-return alignment;
10. no look-ahead contamination.

Correct large-cap ranking to use lagged market cap for predictive research if needed.

Output:

`V1_AUDIT.md`

---

# Phase 3 — Explain the extreme bull outcomes

Goal:

understand what produced the huge forward returns that inflate the Bull-state mean.

For major episodes such as late 2020:

calculate 4w and 12w contribution attribution.

Required decomposition:

- BTC;
- ETH;
- top 10 assets;
- large caps;
- rest of eligible market.

Also report:

- broad breadth;
- large-cap breadth;
- market return;
- median coin return.

Output:

`extreme_episode_attribution.csv`

and:

`EXTREME_EPISODE_ANALYSIS.md`

Key question:

> Were the extreme bull outcomes broad-market rallies or primarily large-cap concentration?

---

# Phase 4 — Build momentum intensity variables

Add:

- MOM_4W_PERCENTILE
- MOM_12W_PERCENTILE

Use expanding percentiles only.

Optionally add a simple momentum acceleration measure, but do not make it part of the state unless it adds value.

Create pre-specified research buckets.

Recommended first pass:

Momentum percentile:

- <40
- 40–70
- 70–90
- >=90

Do not optimize bucket boundaries.

Output:

`momentum_intensity_analysis.csv`

---

# Phase 5 — Test breadth intensity

Analyze forward outcomes across breadth levels.

Use frozen buckets such as:

- <40%
- 40–50%
- 50–60%
- 60–70%
- 70–80%
- >=80%

Analyze separately:

- broad breadth;
- large-cap breadth;
- breadth gap.

For each bucket report 4w and 12w:

- N;
- positive-return frequency;
- mean;
- median;
- p25;
- p75;
- > +10%;
- < -10%;
- max drawdown;
- max run-up.

Main test:

> Does broader participation correspond to a progressively better future distribution?

Do not select the bucket with the highest performance after the fact.

---

# Phase 6 — Build Bull/Bear quality matrix

Construct an analytical matrix using:

- Direction
- Momentum strength
- Participation
- Volatility/stress
- Liquidity

Do not immediately create dozens of hard-coded state names.

First measure conditional distributions.

Example comparisons:

- Bull + Strong Momentum
- Bull + Weak Momentum
- Bull + Broad
- Bull + Narrow
- Bull + Normal Vol
- Bull + High Vol
- Bull + Liquidity Expanding
- Bull + Liquidity Contracting

Then interactions:

- Bull + Strong + Broad
- Bull + Strong + Narrow
- Bull + Strong + Broad + Normal Vol
- Bull + Strong + Broad + High Vol
- Bull + Strong + Broad + Liquidity Up
- Bull + Strong + Broad + Liquidity Down

Only report combinations with adequate N.

Avoid sparse-state explosion.

Output:

`regime_quality_conditionals.csv`

and:

`REGIME_QUALITY_RESULTS.md`

---

# Phase 7 — Define provisional regime-quality taxonomy

Only after Phase 6.

Use the evidence to propose descriptive categories such as:

- Emerging Bull
- Confirmed Bull
- Strong Bull
- Fragile / Late Bull
- Emerging Bear
- Confirmed Bear
- Strong Bear
- Bear Exhaustion
- Neutral / Uncertain

Important:

Do not define thresholds solely by choosing the values with best historical returns.

Prefer:

- simple;
- monotonic;
- interpretable;
- stable;
- sufficiently populated regions.

Freeze a candidate taxonomy before validation.

Output:

`PROVISIONAL_REGIME_TAXONOMY.md`

---

# Phase 8 — True walk-forward crypto-only validation

Build a separate validation script.

At every historical week `t`:

1. compute features using data available through `t`;
2. construct state using frozen rules;
3. estimate any required historical conditional frequencies using only matured prior episodes;
4. issue 4w and 12w forecast/evidence;
5. wait for future outcome;
6. score prediction.

No future sample information in thresholds or standardization.

Primary metrics:

- accuracy;
- balanced accuracy;
- Brier score;
- log loss;
- calibration;
- AUC where meaningful;
- future-return distribution;
- downside risk.

Benchmarks:

- unconditional historical base rate;
- simple momentum sign;
- existing V1 Bull/Neutral/Bear;
- always-positive where appropriate.

Output:

`walk_forward_crypto_only.csv`

and:

`WALK_FORWARD_CRYPTO_ONLY.md`

---

# Phase 9 — Freeze the crypto-only model

Based on development/validation data only.

Suggested chronological architecture:

- development: 2015–2020
- validation/freeze: 2021–2023
- final untouched OOS: 2024–2026

Do not inspect final OOS to choose thresholds.

Record exact final feature list and state rules.

Output:

`CRYPTO_ONLY_MODEL_FREEZE.md`

---

# Phase 10 — Build macro dataset

Only after the crypto-only benchmark is frozen.

Potential macro variables:

## Liquidity

- Global M2 / global liquidity proxy
- US M2
- Fed balance sheet

## Dollar

- DXY or broad dollar index

## Rates

- Fed Funds
- US 2Y yield
- real yields

## Risk / stress

- VIX
- financial conditions index
- high-yield spreads

## Risk appetite

- Nasdaq
- S&P 500 if useful

Critical requirement:

respect publication/release timing.

No revised macro value may be used before it would have been known historically if real-time vintages are required.

---

# Phase 11 — 2020 vs 2021 forensic comparison

Build a dedicated case study.

Compare internally similar crypto states around:

- late 2020;
- late 2021.

For each date report:

Crypto:
- MOM4
- MOM12
- momentum percentiles
- broad breadth
- large-cap breadth
- volatility
- turnover
- stablecoin growth

Macro:
- liquidity growth
- DXY
- rate direction
- 2Y yield
- real yield
- VIX
- credit spreads
- Nasdaq
- policy direction

Future:
- +4w return
- +12w return
- max drawdown
- max run-up

Goal:

identify variables observable at the time that distinguished the two regimes.

This case study is diagnostic, not sufficient by itself to select a model.

Output:

`2020_VS_2021_FORENSIC.md`

---

# Phase 12 — Macro incremental-value test

Create:

`Model A = frozen crypto-only`

`Model B = crypto + macro`

Run identical walk-forward tests.

Primary question:

> Does macro improve OOS 4w and 12w forecasts?

Compare:

- Brier score;
- calibration;
- log loss;
- accuracy;
- drawdown-risk discrimination;
- regime-transition discrimination.

Macro variables survive only if incremental value is robust.

Do not keep them because the economic story sounds good.

Output:

`macro_incremental_value.csv`

and:

`MACRO_INCREMENTAL_VALUE.md`

---

# Phase 13 — Final untouched OOS: 2024–2026

After every important choice is frozen:

extend the crypto panel through the latest complete Friday in 2026.

Do not redesign the model after seeing these results.

Evaluate:

- crypto-only frozen model;
- crypto+macro frozen model;
- benchmarks.

Report:

- 4w performance;
- 12w performance;
- calibration;
- state-by-state performance;
- transition warnings;
- errors/failures.

Output:

`FINAL_OOS_2024_2026.md`

This is the decisive validation phase.

---

# Phase 14 — Decide what survives

Every variable must earn its place.

For each candidate indicator classify:

- KEEP
- DIAGNOSTIC ONLY
- DROP

Criteria:

- economic meaning;
- predictive contribution;
- stability;
- data quality;
- redundancy;
- OOS performance.

Avoid complexity that does not improve results.

---

# Phase 15 — Current live Observatory

Only after final OOS.

Refresh data through the latest complete Friday.

Generate current report:

## State

- Direction
- Strength
- Participation
- Stress
- Liquidity
- Macro

## 4-week evidence

- historical conditional frequency positive;
- median;
- downside risk;
- calibration.

## 12-week evidence

same.

## Transition risk

- persistence;
- deterioration signals;
- uncertainty.

## Historical analogs

nearest historical states with no future leakage.

---

# Phase 16 — Trading research comes later

Do NOT move automatically from predictive state to a trading strategy.

Only if the Observatory demonstrates robust OOS information should later work examine:

- entry rules;
- exits;
- fees;
- slippage;
- execution;
- position sizing;
- portfolio allocation;
- risk limits.

Research sequence remains:

`DATA → STATE → HYPOTHESIS → VALIDATION → OOS → TRADE`

---

# Immediate next execution

The next coding task after these documents should be:

1. audit the V1;
2. build extreme-episode attribution;
3. add momentum percentiles;
4. test momentum/breadth/volatility/liquidity quality conditional distributions;
5. do NOT add macro yet;
6. do NOT inspect 2024–2026 yet.

This keeps the experiment clean and preserves a valuable final OOS period.
