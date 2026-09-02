# Feature family registry

Phase 3 Step A. No estimates. No models. Status is a **data-architecture** decision, not a predictive result.

**Validation reminder:** 2024–2026 is already inspected. No new specification created here may call that window clean OOS. Next genuine test is prospective (Phase 3H).

**Current information set (do not redefine):** six BTC expanding percentiles + four frozen macro 12w changes.

**Transform policy (later builds):** for each raw concept, at most level, short change (1d and/or 7d), historical expanding percentile. 30d only when the mechanism is a slow stock (OI, stablecoin mcap, cumulative flows). No window grids.

**X_UP / X_RISK:** conceptual only. X_UP = more relevant to P(BTC 60d return > +20%). X_RISK = more relevant to P(MAE_60d < −15%). A variable may be both.

**Status ∈** `KEEP FOR DATA BUILD` | `DIAGNOSTIC ONLY` | `DEFER` | `DROP`

Look-ahead: a variable is usable at date *t* only if its value would have been known by a close-of-day *t* decision. Expanding percentiles use history through *t* only.

---

## Family 1 — Derivatives (priority 1)

Venue default for KEEP candidates: **Binance USD-M BTCUSDT perpetual**, because (a) it is the liquid crypto-native perp, (b) Binance Vision publishes dated ZIP archives that can be reconstructed without the 30-day REST cap, and (c) Phase 1 already uses Binance spot from 2017-08-17. This is **exchange-specific**, not market-wide. Do not silently treat it as “the market.” Aggregated multi-exchange series (Coinglass, Glassnode, CryptoQuant) are paid and are not assumed available.

Binance USD-M BTCUSDT listed **2019-09-08** (widely documented onboard date). REST `/fapi/v1/fundingRate` from this environment returned HTTP 451; Vision archives are the reproducible path.

### Funding

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| derivatives | funding_rate | Perp longs pay shorts when funding > 0 (crowded long / bullish basis). Cost of leverage; mean-reverting crowding. | X_RISK at high positive extremes (crowded longs, unwind risk). Mild X_UP when deeply negative (shorts pay, capitulative positioning). Not a drift signal in the middle. | 8h settlements; daily last-print or daily mean | level; 1d change; expanding percentile. Optional 7d trailing mean as *one* extra, not a grid. | 2019-09 (BTCUSDT perp listing). Vision monthly files; first month **UNKNOWN** until listed, not downloaded. | Binance Vision `futures/um/monthly/fundingRate/BTCUSDT/` | free | High: `fundingTime` is the settlement instant (UTC). | Low if using last settlement ≤ t 16:00 UTC (or last 8h print on day t). Do not use next settlement. | Low: exchange archive, not a panel of names. | Yes (Binance) | 1 | KEEP FOR DATA BUILD |
| derivatives | funding_change_1d | Speed of crowding / de-crowding. | X_RISK if funding spikes up into already-high percentile. | daily | 1d difference of daily funding | same as funding_rate | derived | free | inherits funding | Low if both ends ≤ t | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | funding_mean_7d | Persistent carry, not one print. | Same as level, slower. | daily | 7d trailing mean of 8h prints, using only settlements ≤ t | same + 7d burn-in | derived | free | inherits funding | Low if window ends at t | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | funding_pctl | Where current carry sits in *this* contract’s history. | Extremes more informative than raw bps as the market’s “normal” funding drifted over 2019–2026. | daily | expanding percentile through t | same; percentile unstable in first ~1y | derived | free | inherits funding | Low if expanding through t | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | cumulative_funding_30d | Running cost of being long the perp. | X_RISK if 30d sum is extremely positive (longs have paid a lot). | daily | 30d sum of 8h rates (economically one stock of carry) | same + 30d burn-in | derived | free | inherits funding | Low | Low | Yes | 1 | KEEP FOR DATA BUILD |

### Open interest

REST `/futures/data/openInterestHist` is **last 30 days only**. Unusable for research history. Daily Vision **metrics** files include `sum_open_interest` / `sum_open_interest_value`. GitHub examples show files by 2023-01; **start date UNKNOWN** until Phase 3B lists the prefix. Intraday OI history is not public.

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| derivatives | oi_btc | Stock of leveraged positions. High OI = more fuel for squeezes and liquidations. | Both. Rising OI with rising price = trend fuel (X_UP). High OI into a drop = unwind risk (X_RISK). | daily snapshot | level; 1d/7d % change; expanding percentile | Vision metrics: UNKNOWN (documented ≥ 2023-01 examples; may start earlier). Not 2019. | Binance Vision `futures/um/daily/metrics/BTCUSDT/` | free | Medium: daily file `create_time` / snapshot time. Confirm whether stamp is EOD UTC. | Medium until timestamp semantics confirmed. If the file for date D includes D+1 early-morning rows, use last stamp ≤ D 23:59 UTC. | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | oi_chg_1d / 3d / 7d | Speed of position build/unwind. | Fast OI drop with negative returns → forced unwind (X_RISK). Fast OI rise with positive returns → speculative inflows (mixed). | daily | % change 1d and 7d only (skip 3d unless 1d/7d disagree in diagnostics) | same + 7d | derived | free | inherits OI | inherits OI | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | oi_over_mcap | Leverage relative to spot float / market cap. | X_RISK when OI is large vs BTC cap (crowded leverage). | daily | ratio; expanding percentile | max(OI start, BTC mcap start) | OI + BTC market cap (Phase 1 / CMC or CoinGecko — **same mcap source as used for flows; do not mix**) | free if mcap is public | Medium | Low if both known at t | Low | Yes (OI) | 1 | KEEP FOR DATA BUILD |
| derivatives | oi_over_volume | How much position vs trading activity (stickiness vs churn). | High OI / low volume = crowded, illiquid unwind (X_RISK). | daily | ratio; percentile | same | OI + perp quote volume | free | inherits | Low | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | oi_pctl | Historical crowding in this contract. | Extremes; X_RISK in the right tail. | daily | expanding percentile | same | derived | free | inherits | Low | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | oi_aggregated_multi_exchange | “Market-wide” OI. | Same mechanism, better coverage in theory. | daily | same transforms | vendor-dependent; often 2020+ | Coinglass / Glassnode / CryptoQuant | **paid** | vendor | UNKNOWN | Low | No (if vendor aggregates) | 1 | DEFER |

Do not use the 30-day REST OI endpoint as a historical series.

### Basis

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| derivatives | perp_spot_basis | (mark − index) / index, or perp last vs spot. Positive = perp rich (bullish leverage demand). | X_RISK at extreme rich basis (crowded longs). Mild X_UP at extreme cheap/negative (short crowding). | daily (from 1h or 8h bars) | level; 1d change; expanding percentile | 2019-09 if Vision `premiumIndexKlines` exists for BTCUSDT from listing. First month **UNKNOWN**. | Binance Vision `futures/um/monthly/premiumIndexKlines/BTCUSDT/` (prefer 1h or 8h, downsample to daily last ≤ t). Alternative: markPriceKlines vs spot. | free | High if kline open_time is used. Premium index is the exchange’s own basis. | Low if last bar close ≤ t | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | futures_annualized_basis | CME BTC futures vs spot, annualized by days to expiry. Pre-perp, the institutional carry. | Same crowding/cash-and-carry mechanism; different clientele (CME vs crypto-native). | daily (CME sessions) | front-month annualized; 7d change; percentile | CME BTC futures **2017-12-18**. Yahoo `BTC=F` is convenient but **adjustment/roll methodology UNKNOWN**. Official CME or Databento is cleaner and often paid. | Proposed: CME delayed / Databento (paid) or Yahoo `BTC=F` only as a diagnostic splice | mixed | Medium–low for Yahoo (session, splits, rolls). High for official. | Roll look-ahead if using “generic front” without a frozen roll calendar. | Low | CME vs crypto-native | 1 | DEFER |
| derivatives | basis_change / basis_pctl | Speed and rarity of richness. | Same as basis level. | daily | 1d change; expanding percentile | inherits perp basis | derived | free | inherits | Low | Low | Yes | 1 | KEEP FOR DATA BUILD |

Do not mix Binance perp basis and CME annualized basis into one series.

### Liquidations

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| derivatives | long_liquidations | Forced long unwind; cascade fuel and sometimes local exhaustion. | X_RISK contemporaneous with the cascade. Ambiguous for *forward* 60d UP (could be washout). | daily | level; vs volume; 7d sum | No public exchange archive for a full history. Binance Vision `liquidationSnapshot` for USD-M was reported **removed**. REST forceOrders is not a historical tape. Bybit never published history. | Coinglass liquidation history API; other vendors that recorded the websocket | **paid**; free reconstruction **not available** | Vendor aggregation; Binance force-order stream is throttled (~1/symbol/s) so even live tapes **undercount cascades**. | Low if daily bar is complete for t | Reconstruction from a vendor that started recording late = left-censored | If single venue, yes | 1 | DROP |
| derivatives | short_liquidations | Forced short unwind (squeeze). | Mixed: squeeze can extend UP short-term; 60d relation unknown. Same data problem. | daily | same | same | same | paid | same | same | same | yes/vendor | 1 | DROP |
| derivatives | total_liquidations | Intensity of forced flows. | X_RISK for adverse paths if clustering of liquidations predicts more stress. | daily | same | same | same | paid | same | same | same | vendor | 1 | DROP |
| derivatives | long_short_liq_ratio | Which side is being stopped out. | Directional colouring of the cascade. | daily | ratio | same | same | paid | same | same | same | vendor | 1 | DROP |
| derivatives | liq_intensity_vs_volume | Liquidations relative to traded size. | X_RISK when forced flow is large vs volume. | daily | ratio | same | same | paid | same | same | same | vendor | 1 | DROP |

**DROP is about free, reproducible history**, not about the economics. Economics are strong. If a paid Coinglass (or equivalent) subscription is later approved, re-open as DEFER → KEEP with an explicit vendor methodology note (throttling, exchange coverage, start date). Do not scrape vendor charts.

### Derivative volume

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| derivatives | perp_volume | Speculative / leveraged activity. | High perp volume with falling price → stress (X_RISK). High with rising price → participation (mixed X_UP). | daily | level; vs 30d median; expanding percentile | 2019-09 Vision 1d klines. First month UNKNOWN until listed. | Binance Vision `futures/um/monthly/klines/BTCUSDT/1d/` | free | High: kline close_time. | Low if using day t bar after it has closed. | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | spot_volume | Spot activity (already in Phase 1 as raw volume → `pctl_rel_volume`). | Already in the information set via percentile. Raw level only needed for ratios. | daily | reuse Phase 1 Binance spot from 2017-08-17 | 2017-08-17 | existing Phase 1 tape | free | High | Low (same as Phase 1) | Low | Yes | 1 | KEEP FOR DATA BUILD |
| derivatives | perp_spot_volume_ratio | Leverage intensity of trading. | X_RISK when perps dominate spot (casino vs cash). | daily | ratio; 7d change; percentile | 2019-09 (perp start) | derived from the two series | free | High | Low | Low | Yes | 1 | KEEP FOR DATA BUILD |

---

## Family 2 — Flows (priority 2)

**Do not assume Glassnode / CryptoQuant / CoinMetrics Flow / Kaiko.** Those are commercial. Free/reproducible first.

### BTC ETF

US spot Bitcoin ETFs began **2024-01-11**. History is short and sits **entirely inside the already-inspected 2024–2026 window**. Still collectable (good timestamps, real capital) but **cannot be validated as if that window were clean OOS**.

Do not splice pre-2024 GBTC (closed-end trust, premium/discount dynamics) onto spot-ETF creations.

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| flows | etf_net_flow_usd | Creations/redemptions = incremental spot demand (authorized participants). | X_UP when persistent inflows; X_RISK when persistent outflows (deleveraging of the “spot bid”). | US trading day | level; 5d sum; 20d sum; flow / BTC mcap | 2024-01-11 | **Farside Investors** public table `https://farside.co.uk/BTC/` (primary proposed). Cross-check **SoSoValue** dashboard. Issuer pages (IBIT) for spot checks. | free (HTML; no official bulk API) | Medium: published with ~1 trading-day lag; date is the flow date, not the publish date. Confirm lag in 3C. | **High if using same-day figures before issuers publish.** Use last *published* flow date ≤ t, or t−1. | Low (fixed issuer list; new funds appear — freeze the 11-issuer set and document additions) | N/A (funds, not exchanges) | 2 | KEEP FOR DATA BUILD |
| flows | etf_flow_5d / 20d | Slow institutional allocation, not one print. | Same, slower. 5d and 20d only. | daily | trailing sums, published dates only | 2024-01 + window | derived | free | inherits | inherits lag rule | Low | no | 2 | KEEP FOR DATA BUILD |
| flows | etf_flow_over_mcap | Size of flow vs the asset. | Same mechanism, scale-free. | daily | ratio | 2024-01 | derived | free | inherits | inherits | Low | no | 2 | KEEP FOR DATA BUILD |

### Stablecoins

Observatory **weekly** `STABLECOIN_MCAP_*` already exists on Friday CMC listings with a **curated symbol list**. Do not redefine it. A **daily** series for this branch must be a separately named source, not a silent substitute.

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| flows | stablecoin_mcap_total | Dry powder / crypto-dollar supply. Issuance often tracks demand for crypto exposure. | X_UP when 7d/30d change is positive (liquidity in). X_RISK when contracting (liquidity out). | daily | level; 7d % change; 30d % change | DefiLlama charts: examples from **2021-01-01** (`date=1609459200`). Earlier history UNKNOWN / incomplete. | DefiLlama `https://stablecoins.llama.fi/stablecoincharts/all` (free API) | free | Medium: unix date; typically one point per day. Confirm timezone (UTC date vs snapshot hour). Revisions possible as methodology/chains are added. | Medium if Llama backfills. Freeze a download date and store raw JSON. | Medium: new stables enter the sum; delisted/depegged names may drop. Document the composition rule (all peggedUSD vs USDT+USDC only). | no | 2 | KEEP FOR DATA BUILD |
| flows | stablecoin_issuance_7d_30d | Change in supply (issuance vs contraction). | Same as mcap change (they are the same object if price ~ $1). | daily | 7d and 30d log-diff | same | derived | free | inherits | inherits | inherits | no | 2 | KEEP FOR DATA BUILD |
| flows | exchange_stablecoin_balances | Dry powder *on exchanges* (immediately tradable). | Stronger X_UP / X_RISK than global mcap in theory. | daily | level; 7d change | Glassnode / CryptoQuant / similar | commercial on-chain analytics | **paid** | vendor | vendor | exchange-label survivorship | yes (exchange set) | 2 | DEFER |

### Exchange BTC flows

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| flows | btc_exchange_inflow | Coins moving to CEX → potential sell pressure. | X_RISK if persistent inflows. | daily | level; 7d; vs mcap | Glassnode, CryptoQuant, Coin Metrics | **paid** (free “samples” are not a full tape) | paid | vendor; cluster labeling is a model | Heuristic address clustering can be revised (look-ahead via restatement). | High: exchange wallets change; labels revised | yes | 2 | DROP |
| flows | btc_exchange_outflow | Coins leaving CEX → potential custody / HODL. | X_UP if persistent outflows. | daily | same | same | paid | paid | same | same | same | yes | 2 | DROP |
| flows | btc_exchange_netflow | In − out. | Combined pressure. | daily | same | same | paid | paid | same | same | same | yes | 2 | DROP |
| flows | exchange_reserve_change | Stock of BTC on exchanges. | Falling reserves often told as bullish; mechanically related to netflow. | daily | level; 7d | same | paid | paid | same | restatement | same | yes | 2 | DROP |

**DROP** = not available as a free, reproducible, non-restated series for this project. Mechanism is real. Re-open only with an approved paid provider and a frozen label version.

---

## Family 3 — Expectations / Polymarket (priority 3)

Polymarket CLOB `GET https://clob.polymarket.com/prices-history` returns `{t, p}` per outcome token. Gamma API supplies market metadata (`clobTokenIds`, volume, liquidity, resolution). Public, no key, rate-limited.

**Do not concatenate unrelated markets into one “sentiment index.”** Markets are event-specific, appear and resolve, and the set of listed questions is not a stationary panel.

Historically consistent series that *might* exist (each is a **construction project**, not a download):

| Event family | Can a consistent series be built? | Notes |
|---|---|---|
| Fed / rates | Only as **event-aligned** features around listed FOMC / “Fed decision” markets, not a 2015–2026 daily series | Each meeting is a new market. Stitching “P(25bp hike)” across meetings requires a mapping of contracts → calendar that did not exist as one ticker. |
| Recession | Weak | Question wording changes (“by date X”). Short, overlapping, not comparable. |
| Elections | One-off | 2024 US election is one market (or a few). 2020 was largely not Polymarket. N=1 event. |
| Regulation / crypto-legal | Sporadic | ETF-approval, case outcomes: useful as **event studies**, not as a panel feature. |
| Geopolitical | Unstable | Markets appear around crises; survivorship of which wars get a market. |

Platform history: Polymarket ~2020; Polygon / CLOB era is later (~2022–2023). Liquidity before ~2024 is often thin. **Too short and too nonstationary** for the same 2015–2026 walk-forward used on BTC percentiles.

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| expectations | event_prob_level | Market-implied P(event). Rates/regulation can move crypto discount rates and risk appetite. | Depends on the event (hawkish Fed → X_RISK; ETF approval → X_UP). Not a generic crypto sentiment. | market-specific; can resample hourly/daily | level at t | Per-market; platform useful liquidity ~2022–2024+ (**UNKNOWN** per family until Gamma catalog is listed, not scraped en masse) | Gamma + CLOB prices-history | free | High: unix `t` on the CLOB series | Low for price at t. **High if using resolution or “final” probability before resolution time is known.** | High: dead markets, relistings, question changes | Polymarket only | 3 | DEFER |
| expectations | prob_change_1d / 7d | Rapid repricing = news arrival. | Same event-dependence. | daily | 1d and 7d change | same | derived | free | High | Low | High | yes | 3 | DEFER |
| expectations | prob_volatility | Disagreement / unstable beliefs. | X_RISK if vol of P(recession) or P(regulation) spikes. | daily | 7d stdev of p | same | derived | free | High | Low | High | yes | 3 | DEFER |
| expectations | volume / liquidity | How much the probability is “backed.” Thin markets are noise. | Filter, not a BTC predictor by itself. | daily | level | same | Gamma metadata + CLOB | free | Medium (snapshot vs history of depth: **order-book history UNKNOWN**) | Low | High | yes | 3 | DEFER |
| expectations | naive_cross_market_sentiment_index | Average of whatever is listed. | None that is identified. Composition changes = look-ahead via which questions exist. | — | — | — | — | — | — | **Fatal** | **Fatal** | — | 3 | DROP |

Audit of data fields (platform):

| Field | Available? |
|---|---|
| timestamps on price history | Yes (`t`) |
| historical prices (implied prob) | Yes (`p`) |
| volume | Yes in Gamma market objects (current / reported); **full historical volume bars UNKNOWN** |
| liquidity / depth | Current CLOB book yes; **historical depth snapshots UNKNOWN** |
| market resolution timestamps | Yes in market metadata (`endDate` / resolution fields — confirm exact keys in 3D, do not invent) |

---

## Family 4 — Sentiment (priority 4)

### Crypto Fear & Greed

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sentiment | fear_greed_index | Composite of volatility, momentum/volume, social, dominance, Google Trends (Alternative.me methodology). Extreme fear as washout; extreme greed as crowding. | Contrarian folklore: low → X_UP, high → X_RISK. **Heavily collinear with existing `pctl_vol_20`, `pctl_ret_*`, `pctl_rel_volume`.** | daily | level; 7d change; expanding percentile | **2018-02-01** (widely documented) | `https://api.alternative.me/fng/?limit=0` | free | Medium: unix `timestamp`; publication time-of-day not a close auction. Confirm whether value for date D uses D’s or D−1’s inputs. | **Medium–high:** inputs include volatility and volume that overlap our X. If the index for calendar day D is published after D’s close using D’s data, same-day use at D close is OK; if it includes next-day social, not OK. Document publish lag in 3E. Methodology changes are not versioned. | Low for the published series; **input mix can change** | no | 4 | DIAGNOSTIC ONLY |

Not KEEP: collinearity + opaque mix + unversioned methodology. Fine as a case-study overlay, not as a new information family for BASE vs BASE+F tests until a versioned, lag-audited series is frozen — still then likely redundant.

### Google Trends

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sentiment | google_trends_bitcoin | Attention / retail search. Spikes at mania and crashes. | Mixed: attention at tops (X_RISK) and bottoms (X_UP). | weekly native; daily is scaled and **not fully reconstructable** | level within a fixed window; 7d change | Google Trends UI from ~2004, but **numbers are relative to the pull window** | Unofficial `pytrends`; official Google Trends; paid Google Ads / third parties | mixed; unofficial API is free and brittle | **Poor for research:** each request is renormalized to 0–100 over the requested range. Historical daily series from overlapping windows do not stitch. | High if the scale of past days changes when you re-pull. | Low | no | 4 | DROP |

Fatal: not a stable historical unit. Paid reconstructed series exist; not assumed.

### News sentiment

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sentiment | news_sentiment | Media tone as proxy for risk appetite / narrative. | X_UP if persistently positive; X_RISK if panic. | daily | mean tone; 7d | RavenPack, Bloomberg, etc. | commercial NLP | **paid** | vendor timestamps | **Timestamp leakage:** article `datetime` vs when a model could have read it (timezones, embargoes, corrections). **Model-version reproducibility:** embeddings/LLM versions change. | **Survivorship:** outlets die; paywalls; deleted articles. | no | 4 | DROP |

Text-specific risks (mandatory): timestamp leakage — high; source survivorship — high; deleted-post — n/a for wire news but corrections exist; model-version reproducibility — high unless a frozen dictionary on a frozen corpus.

### Reddit

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sentiment | reddit_sentiment_activity | Retail narrative and activity in r/Bitcoin, r/cryptocurrency. | Same attention mechanism as Trends. | daily | volume of posts/comments; optional frozen lexicon score | Pushshift historical dump **ended**; Arctic Shift / PullPush are incomplete. Official Reddit API is not a 2015–2026 archive. | no reliable free historical API | mixed / incomplete | Poor | Deleted-post bias (failed trades vanish). Moderators remove content. | **Severe** | no | 4 | DROP |

### X / Twitter

Not audited for KEEP. No demonstrated reliable historical firehose for this project. **DROP** by instruction unless access is proven — it is not.

---

## Family 5 — Crypto cross-section / breadth

Existing Observatory (weekly, Friday, CMC historical listings, frozen universe rules in `CANONICAL_INDICATORS.md`):

- broad breadth
- large-cap breadth
- breadth change
- dispersion
- concentration

**Do not rebuild them now.**

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breadth | daily_breadth_true | Share of coins up; risk-on vs concentrated leadership. | X_UP when breadth expands with BTC. X_RISK when BTC rises on narrowing leadership. | daily | same concepts as weekly | Would need **daily** listings + the same eligibility rules | CMC historical listings **daily** (API exists in Phase 6H as Friday-only usage) | free API but **new universe methodology** vs frozen Friday tape | Friday tape is the frozen observatory. Daily snapshots are a different object (intraday listing rank changes, different missingness). | High if daily universe is rebuilt with future knowledge of which coins “mattered.” | Must not drop delists retroactively (same rule as weekly). | no | 5 | DEFER |
| breadth | friday_breadth_mapped_to_daily | Carry Friday observatory values across the following week (step function). | Same as weekly breadth, **no new daily information**. | daily (stale within week) | none new | 2015 weekly observatory | existing `v1_weekly_core` — **read only, do not modify** | already in-house | High (Friday close convention) | Low if dated as Friday and used only after that Friday | Same as observatory | no | 5 | DIAGNOSTIC ONLY |

**Audit conclusion:** a *consistent* daily breadth series **without a new universe methodology** is only the Friday step-function. That adds almost no information vs lagging the weekly observatory. True daily breadth **does** introduce a new universe methodology. Do not build it in Phase 3.

---

## Family 6 — Market microstructure (optional / later)

These need **historical snapshots**, not live books.

| family | variable | economic mechanism | expected relation to UP / downside risk | frequency | desired transforms | earliest possible history | source candidate | free / paid | timestamp quality | look-ahead risk | survivorship risk | exchange-specific? | priority | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| microstructure | bid_ask_spread | Transaction cost / liquidity. Widens in stress. | X_RISK when spread percentile is high. | snapshot | daily median; percentile | Tardis, Kaiko, L2 archives | **paid** (Binance Vision has no historical L2 book) | paid | High if snapshot timestamps exist | Low | Low | yes | 6 | DEFER |
| microstructure | order_book_depth | Size at top of book. | X_RISK when depth collapses. | snapshot | same | same | paid | paid | High | Low | Low | yes | 6 | DEFER |
| microstructure | order_book_imbalance | Short-horizon pressure. | More relevant to minutes than 60d. Weak mechanism for UP_60D / ADVERSE_60D. | snapshot | same | same | paid | paid | High | Low | Low | yes | 6 | DROP |
| microstructure | realized_intraday_vol | Parkinson/RV from intraday bars. | X_RISK; **collinear with `pctl_vol_20`** if daily realized is close to 20d vol. | 5m/1h bars | daily RV; percentile | Binance Vision 1h or 5m klines (large files) | Vision klines | free but **large** — do not download in Step A | High | Low | Low | yes | 6 | DEFER |

Order-book imbalance is dropped for *this* decision horizon (60d), not because books are useless at HFT horizons.

---

## Status counts (this audit)

| Status | Count (approx.) | What it means for the build |
|---|---|---|
| KEEP FOR DATA BUILD | Funding block, OI (Vision daily), perp basis, perp/spot volume, ETF flows, DefiLlama stablecoin mcap | Phase 3B then 3C |
| DIAGNOSTIC ONLY | Fear & Greed; Friday-breadth-as-daily | Overlay, not a family test |
| DEFER | Multi-exchange OI, CME basis, Polymarket event features, exchange stablecoin balances, true daily breadth, microstructure | After 3B–3C, or never |
| DROP | Liquidations (free), exchange BTC flows (free), naive Polymarket index, Google Trends, news NLP, Reddit, X, book imbalance for 60d | Do not collect |

---

## Conceptual split for later tests (no estimation)

**More likely X_UP (liquidity / demand in):** ETF net inflows and 5d/20d sums; stablecoin mcap 7d/30d expansion; negative funding / cheap basis (short crowding washout — also a bottoming story, so dual); expanding breadth (when/if used).

**More likely X_RISK (crowding / forced unwind / liquidity out):** high funding percentile; high OI / OI-to-mcap / OI-to-volume; rich perp basis; rising perp/spot volume ratio; ETF outflows; stablecoin contraction; (if ever paid) liquidations and exchange inflows.

Several derivatives variables are **dual**: the same crowding that can precede a squeeze (UP path) can precede a long liquidation cascade (ADVERSE path). Incremental tests must look at **both** targets, not only the “intuitive” one.
