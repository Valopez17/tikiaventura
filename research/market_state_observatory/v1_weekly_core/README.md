# Crypto Market State Observatory v1 — weekly core

MEASURE STATE → COMPARE HISTORY → FORWARD OUTCOMES → AUDIT

This module is **independent** of the Hsieh replication, the Wen replication, the BTC rally map, and the Moskowitz work. Those folders are not modified.

v1 answers descriptive questions about **crypto market state** at weekly frequency. It does **not** forecast with ML, does **not** trade, and does **not** add macro series (M2, DXY, Fed, VIX, etc.).

## Data source

- **File (read-only):** `research/papers/hsieh_2025_state_transition_momentum/data/processed/crypto_weekly_panel.csv`
- **Origin:** CoinMarketCap public historical listings, Friday snapshots, assembled for the Hsieh 2025 replication.
- **This Observatory does not re-download CMC.**
- **This Observatory does not modify that CSV.**

### Sample period

Friday weeks **2015-01-02 → 2023-12-29** (470 weeks).

The “current” week in `results/current_market_report.md` is the **last Friday in this frozen panel**, not live calendar time. Live 2026 state is out of scope until a later data refresh.

### Columns used from the panel

`week`, `asset_id`, `symbol`, `weekly_price`, `weekly_return`, `market_cap`, `volume`, `is_stablecoin`, `eligible`

Hsieh’s `eligible` and Hsieh’s `is_stablecoin` are **not** used to define the Observatory universe. They are present only because they exist on the frozen file.

## Return convention

The panel’s `weekly_return` is a **log return**: \(\ln(P_t / P_{t-1})\).

The Observatory converts **before any aggregation**:

\[
\text{simple\_return}_{i,t} = \exp(\text{weekly\_return}_{i,t}) - 1
\]

All market weighting, compounding (MOM, index, coin 4-week returns), volatility, and forward outcomes use **simple** returns.

**Assumption (verifiable in the Hsieh README / script):** Friday log returns. If that source convention were wrong, every Observatory number would be wrong.

## Universe definition (`observatory_eligible`)

A coin is eligible in week **t** iff **all** of the following hold at t, using only information dated ≤ t:

1. Not an Observatory stablecoin (see below). Not Hsieh’s flag.
2. `market_cap_t >= 10,000,000` USD (PRIMARY). Contemporaneous Friday mcap, not lagged.
3. At least **26** weeks of observable price history **up to and including t** (count of Friday snapshots with `weekly_price > 0` for that `asset_id` on the calendar; gaps do not count).
4. `simple_return` finite.
5. `market_cap` finite and `> 0` (implied by 2).
6. `volume` finite and `> 0`.
7. `weekly_price` finite and `> 0`.

Delisted coins are **kept** in any week they still appear in the panel. Eligibility is **not** retroactively removed because a coin later disappears.

### Robustness universes (thresholds frozen)

| name | min market cap |
|---|---|
| `universe_1m` | $1,000,000 |
| `universe_10m` | $10,000,000 (PRIMARY) |
| `universe_50m` | $50,000,000 |

Only last-week MOM, breadth, and state are compared across universes (`results/universe_robustness.csv`). Thresholds will not be changed after seeing results.

## Stablecoin handling

**Return / breadth universe:** Observatory stablecoins are excluded.

**Liquidity layer:** the same coins’ market caps are **summed** each week into `STABLECOIN_MCAP`.

Hsieh’s `is_stablecoin` column is a substring/id heuristic and **false-positives** non-stables (e.g. APT, ATOM, UNI, TON, FTT, FXS). The Observatory therefore uses a **curated symbol allowlist** (USDT, USDC, DAI, BUSD, TUSD, FDUSD, and other USD/fiat stables present in CMC, plus Terra UST/USTC historically). Gold-pegged tokens (PAXG, XAUT) are excluded. Wrapped aliases (`USDC.e`, `USDT.e`, `USDC(WormHole)`) are treated as stables.

**Known limitations (not invented away):**

- Multiple listed wrappers can **double-count** USD supply in `STABLECOIN_MCAP`.
- Early sample (2015–2017) is dominated by USDT; USDC starts 2018 in this panel.
- CMC snapshots can miss a stable on some Fridays.
- Allowlist completeness is an **unverified assumption**: a stable not on the list is treated as a non-stable (could enter returns/breadth) and is omitted from `STABLECOIN_MCAP`.

Stablecoin **growth is not labeled bullish**. It is measured, then compared to historical forward outcomes later.

## Market weighting

\[
\text{market\_return}_t = \sum_{i \in E_t} w_{i,t-1}\, r_{i,t}, \qquad
w_{i,t-1} = \frac{\text{mcap}_{i,t-1}}{\sum_{j \in E_t} \text{mcap}_{j,t-1}}
\]

where \(E_t\) is `observatory_eligible` at t, \(r_{i,t}\) is simple return, and weights use **lagged** market cap. Coins eligible at t with missing or non-positive lag mcap are dropped from the **sum only** (they can still enter breadth). Weights among the remaining names sum to 1.

First sample week has no lag mcap → `market_return` is NaN.

`market_index` is initialized at **100** and compounds simple `market_return` thereafter.

## Breadth definitions

Coin 4-week return at t is the calendar 4-Friday cumulative simple return:

\[
\text{coin\_return\_4w}_{i,t} = \prod_{k=0}^{3} (1 + r_{i,t-k}) - 1
\]

If any of those four calendar weeks is missing for that coin, the 4-week return is NaN and the coin is omitted from that week’s breadth denominator.

\[
\text{broad\_breadth\_4w}_t = \frac{\#\{i \in E_t : \text{coin\_return\_4w}_{i,t} > 0\}}{\#\{i \in E_t : \text{coin\_return\_4w}_{i,t}\ \text{finite}\}}
\]

Equal-weight across coins. Also stored: median / p25 / p75 of `coin_return_4w`, and `n_eligible_coins`.

**Large-cap universe (dynamic each week):** top **100** `observatory_eligible` coins by contemporaneous market cap. If fewer than 100 eligible, **all** eligible coins are used. In this sample that happens in **104** early weeks (primary $10M universe); the current week 2023-12-29 uses a full top 100. `largecap_breadth_4w` is the same up-share inside that set. `breadth_gap = largecap_breadth_4w − broad_breadth_4w`. Descriptive only; no causal claim.

## Volatility definition

`VOL_12W` = sample standard deviation (`ddof=1`) of the last **12** weekly `market_return` observations, **not annualized**. Requires 12 finite market returns.

`VOL_PERCENTILE` = expanding empirical CDF of `VOL_12W` using weeks ≤ t only.

`HIGH_VOL` iff `VOL_PERCENTILE >= 0.70`; else `NORMAL_VOL`. Threshold frozen. Early-sample percentiles are noisy (few history points).

## Turnover definition

\[
\text{turnover}_{i,t} = \text{volume}_{i,t} / \text{market\_cap}_{i,t}
\]

for eligible coins with `market_cap > 0`. Infinities → NaN. **No winsorization.**

`market_turnover` = **median** cross-sectional turnover (PRIMARY). `market_turnover_p75` is also stored.

`TURNOVER_RELATIVE` = `market_turnover` / trailing 12-week **median** of `market_turnover` (window **includes** t). NaN if the denominator is 0 or the window is incomplete.

`TURNOVER_PERCENTILE` = expanding empirical CDF of `market_turnover` (level), weeks ≤ t.

## Stablecoin liquidity definition

`STABLECOIN_MCAP_t` = sum of market cap over Observatory stablecoins that week.

`STABLECOIN_MCAP_4W_CHANGE` = \(S_t / S_{t-4} - 1\) (simple percent change of the aggregate).

`STABLECOIN_MCAP_12W_CHANGE` analogously.

`STABLECOIN_LIQ_PERCENTILE` = expanding empirical CDF of the **level** `STABLECOIN_MCAP`.

## State thresholds (frozen)

**Direction**

- **BULL** if `MOM_4W > 0` AND `MOM_12W > 0` AND `broad_breadth_4w > 0.50`
- **BEAR** if `MOM_4W < 0` AND `MOM_12W < 0` AND `broad_breadth_4w < 0.50`
- **NEUTRAL** otherwise (including mixed-sign momentum)

`MOM_4W` / `MOM_12W` are cumulative simple returns of `market_return` over the last 4 / 12 weeks through t.

**Combined `market_state`:** `{BULL,NEUTRAL,BEAR}_{NORMAL,HIGH_VOL}`.

**`breadth_quality` (does not change `market_state`):**

- BROAD: both breadths ≥ 0.60
- NARROW_LARGECAP: large-cap breadth ≥ 0.60 AND broad breadth < 0.50
- WEAK: both < 0.40
- MIXED: any other finite case

## Forward outcomes

Computed **after** state construction. Never used as inputs to state, vol labels, or analog features.

From week t, exclusive forward:

- `market_return_future_1w` = `market_return_{t+1}`
- `market_return_future_4w` / `_12w` = cumulative simple return over t+1…t+h
- `max_drawdown_future_*` = min of peak-to-trough drawdown on the wealth path with \(W_0=1\) at t
- `max_runup_future_*` = \(\max_k (W_k - 1)\) vs the level at t

If any return in the horizon is non-finite, the horizon is NaN.

## Analog methodology

Vector (if stablecoin 4w change coverage ≥ 50% of weeks through last t):

\[
X_t = [\text{MOM\_4W},\ \text{MOM\_12W},\ \text{broad\_breadth\_4w},\ \text{largecap\_breadth\_4w},\ \text{VOL\_PERCENTILE},\ \text{TURNOVER\_RELATIVE},\ \text{STABLECOIN\_MCAP\_4W\_CHANGE}]
\]

Z-score mean/std estimated **once** on all finite observations **through the last sample week**. Euclidean distance in that z-space. K=25 frozen.

Excluded: current week; prior 12 weeks; any week with a NaN in the analog vector after z-score.

## Transition matrix

Unsmoothed counts and row-normalized historical frequencies:

- 6 combined states
- 3 direction states (BULL / NEUTRAL / BEAR)

These are empirical transition **frequencies**, not a Markov model of the true process.

## How to read probabilities

Do **not** call \(\mathbb{P}(R>0 \mid \text{state})\) the “true probability of going up.”

Correct language: *In historical weeks with the same state, the 4-week forward market return was positive in X% of cases.*

## Outputs

| file | content |
|---|---|
| `src/build_market_state_v1.py` | single pipeline |
| `results/weekly_market_state.csv` | weekly state + features (+ extra diagnostics / forward columns for audit) |
| `results/state_transition_matrix.csv` | from/to counts and frequencies |
| `results/state_forward_outcomes.csv` | state, breadth_quality, and direction×quality historical conditionals |
| `results/current_historical_analogs.csv` | top 25 analogs to the last week |
| `results/universe_robustness.csv` | last-week diagnosis at $1M / $10M / $50M |
| `results/current_market_report.md` | 18-question current-state report |

## Known limitations

- Panel ends **2023-12-29**. Not a live observatory.
- CMC listing coverage, especially small coins and some stables, is incomplete.
- Value-weighting with lagged mcap still uses contemporaneous eligibility at t (standard, but not identical to lagged eligibility).
- Expanding percentiles are mechanically extreme at the start of the sample.
- Analog z-scores use the **full sample through the last week**, so they are not a purely expanding “as-of-t” distance for historical weeks (only the *current* analog search is required in v1).
- No adjustment for overlapping 4w/12w windows in the outcome tables (descriptive, not inference).
- Turnover is CMC reported volume / mcap; wash trading can inflate volume. **Unverified.**
- Large-cap “top 100” uses contemporaneous mcap (look-ahead relative to a strict lagged-size screen). Documented choice, frozen.

## Explicitly out of v1

Global M2, DXY, Fed funds, yields, VIX, credit, Nasdaq, funding, open interest, basis, liquidations, HMM, clustering, Random Forest, XGBoost, neural nets, trading strategies, leverage, Sharpe, backtests, dashboards, APIs.
