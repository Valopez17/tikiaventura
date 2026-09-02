# Expansion plan

Phase 3 Step A. No models. No metrics. Ranking uses expected information value, historical coverage, timestamp integrity, reproducibility, cost, and implementation complexity.

**Validation reminder:** 2024–2026 is already inspected. New specs may use 2015–2026 for walk-forward **development / robustness** only. The next clean test is **prospective (Phase 3H)** after freeze.

**Later evaluation rule:** same architecture for BASE vs BASE + family F. Question = does F add information? Not = can we retune until F looks good.

---

## Family ranking

Weights are qualitative, not a score model.

| Rank | Family | Information value | Historical coverage | Timestamp integrity | Reproducibility | Cost | Complexity | Net |
|---|---|---|---|---|---|---|---|---|
| 1 | Derivatives (funding, basis, perp volume; OI if Vision exists) | High: leverage and crowding are the main mechanism Phase 2’s price/macro set does **not** measure | Funding/basis/volume: from ~2019-09 if Vision is complete. OI: **UNKNOWN**, possibly only ~2023+ | High for Vision klines/funding; OI snapshot semantics to confirm | High (exchange archive) | Free | Medium (ZIP plumbing, 8h→daily, no look-ahead) | **Build first** |
| 2 | Flows — ETF + DefiLlama stables | High for *post-2024* institutional demand; moderate for stables (liquidity) | ETF: 2024-01-11 only (short, inside inspected window). Stables: ~2021+ | ETF: publish lag. Stables: possible Llama restatements | ETF HTML is fragile but public. Llama JSON is easy | Free | Low–medium | **Build second** |
| 3 | Expectations (Polymarket) | High *conditional on the right event*; low as a panel feature | Thin before ~2024; no 2015–2019 | Good per-market `t`,`p`; bad as a concatenated index | Per-market yes; panel no | Free | High (market mapping, no naive index) | **Do not build a dataset until derivatives+flows exist;** then event-aligned only |
| 4 | Sentiment | Fear & Greed: low incremental (collinear with existing vol/return/volume). Others: theoretically interesting, fatal data | F&G from 2018; Trends/news/Reddit not usable | F&G publish lag UNKNOWN | F&G easy; rest poor | F&G free; news paid | Low for F&G overlay | **Diagnostic overlay only** |
| 5 | Breadth daily | High in weekly observatory work; **daily true breadth needs a new universe** | Weekly 2015+ already exists | Friday convention is clean | Already in-house | Free | High if rebuilt daily | **Do not collect yet** |
| 6 | Microstructure | Weak for 60d decisions; RV collinear with `pctl_vol_20` | Paid L2 or large 5m files | Good if paid snapshots exist | Paid vendors | Paid / large | High | **Not yet** |

**Paid exchange-flow / liquidation vendors** rank as high mechanism, **fail** coverage/reproducibility/cost for this project as specified. They do not enter the build sequence unless a later decision explicitly buys a frozen extract.

This ranking **does not change** the intended phase letters. The audit’s only methodological pressure is: **OI coverage may start years after funding** — still collect OI in 3B if Vision metrics exist; if they start in 2023, tests use the overlap, not a fake 2019 OI series.

---

## Build sequence

### Phase 3B — Derivatives dataset

**Build first.**

- List Vision prefixes (fundingRate, premiumIndexKlines or mark/index, 1d klines, daily metrics). Read **one** sample header each.
- If prefixes exist: download **those** archives (1d klines and monthly funding are small; skip 1m/aggTrades).
- Construct daily UTC: funding level / 1d change / 7d mean / expanding pctl / 30d cumulative; perp volume; perp/spot volume ratio; basis level / 1d change / pctl; OI level / 1d / 7d % / pctl / ratios **only if** metrics history exists.
- Document first/last date per series. If OI starts late, **do not backfill** from Coinglass.
- No models.

### Phase 3C — Flow dataset

- Farside ETF daily net flows with an explicit **publish-lag** rule (no same-day leakage).
- 5d and 20d sums; optional flow/mcap if a frozen BTC mcap series is chosen.
- DefiLlama total stablecoin circulating USD: freeze JSON vintage; 7d and 30d changes.
- Do **not** pull Glassnode exchange flows.
- No models.

### Phase 3D — Expectations dataset

- **Not** a sentiment index.
- Optional: catalog Gamma markets in Fed / crypto-regulation families; document which have CLOB history, volume, resolution time.
- If — and only if — a **single repeating event type** has enough non-overlapping contracts (e.g. successive FOMC), design an event-aligned feature spec. Otherwise skip to 3E.
- No concatenation across unrelated questions.

### Phase 3E — Sentiment dataset

- Optional diagnostic: Alternative.me Fear & Greed daily, lag audit vs BTC close, collinearity note vs `pctl_vol_20` / `pctl_ret_*` / `pctl_rel_volume`.
- Do not scrape Reddit/X. Do not buy news NLP in this sequence.

### Phase 3F — Incremental predictive tests

- BASE = Phase 2 information set (six BTC pctl + four macro 12w), **same architecture as the Phase 2 comparator you freeze for this test** (recommended: the linear/logistic family that is simple enough that deltas are about features, e.g. M1-style L2 logistic — **choose once, write it down, do not switch to GBM “because the new features need nonlinearity”**).
- Compare BASE vs BASE+derivatives, then vs BASE+flows, on walk-forward **2015–2026 development/robustness** with mature 60d labels. **Do not call 2024–2026 clean OOS.**
- Few transforms only. Both `UP_60D` and `ADVERSE_60D`.

### Phase 3G — Candidate freeze

- Freeze which families/variables survive 3F (pre-registered metrics, not a fishing grid).
- Freeze code, sources, vintage dates.
- Write the prospective protocol.

### Phase 3H — Prospective evaluation

- True untouched window: dates **after freeze**.
- Not a replay of 2024–2026.

---

## Answers to the ten output questions

### 1. Which missing information family is most likely to improve prediction?

**Derivatives — funding, basis, and perp/spot activity** (and OI if Vision metrics cover enough years).

Phase 2 already has price-path percentiles and slow macro. It does not measure **leverage crowding** or **cost of being long perps**. That is the largest identified hole for ENTER / HOLD / REDUCE / EXIT / STAY OUT at a 60-day horizon.

ETF flows are the strongest *demand* family but only exist inside the inspected 2024–2026 sample, so they are unlikely to be the first **validated** improvement; they can still matter economically going forward.

### 2. Which variables have the best economic justification?

- Funding level / percentile / 30d cumulative carry (cost of crowded longs).
- Perp–spot basis (same crowding, different unit).
- OI vs market cap and OI vs volume (stock of leverage).
- Perp/spot volume ratio (where activity sits).
- ETF net creations (spot bid from APs).
- Stablecoin supply 7d/30d change (crypto-dollar liquidity).

Liquidations and exchange netflows are equally well motivated and **lose** on data quality.

### 3. Which have reliable historical data?

**Best (conditional on Vision files existing from listing):** funding, perp 1d volume, spot volume (already in Phase 1), likely premium-index basis.

**Good but short:** US spot ETF flows from 2024-01-11 (Farside public table).

**Usable with vintage freeze:** DefiLlama stablecoin mcap from ~2021-01-01.

**Unverified / possibly short:** Vision daily OI metrics (UNKNOWN start; example in 2023).

**Not reliable for this project:** liquidations, CEX BTC flows, Google Trends units, social text, naive Polymarket indexes, historical L2 books without a paid archive.

### 4. Which should be dropped because of data quality?

- All **liquidation** series (no free reconstructable tape; throttled live streams).
- **Exchange BTC in/out/netflow and reserves** (paid clustering, restatements).
- **Naive Polymarket sentiment index.**
- **Google Trends** (window-relative 0–100).
- **News sentiment** and **Reddit** (corpus, deletion, model version).
- **X/Twitter.**
- **Order-book imbalance** as a 60-day feature.

Fear & Greed is not DROP; it is **DIAGNOSTIC ONLY** (collinearity + opaque mix).

### 5. What should be built FIRST?

**Phase 3B — Binance Vision derivatives daily panel** (funding, basis, perp volume, perp/spot ratio; OI if metrics files exist).

### 6. Which data require payment / proprietary providers?

Required for a serious version of: multi-exchange OI, liquidations, exchange-wallet flows, exchange stablecoin balances, historical L2 depth, professional news sentiment, reconstructed Google Trends.

**Not required** for the KEEP list: Binance Vision, Phase 1 spot, Farside, DefiLlama, Alternative.me, Polymarket public APIs.

### 7. What information is likely useful for UP_60D?

Conceptual only:

- Persistent **ETF inflows** and stablecoin **expansion** (capital / liquidity in).
- **Depressed funding / cheap basis** after a washout (short crowding; fuel for a squeeze — also a risk feature).
- Rising OI with rising price (speculative participation) — dual, easy to confuse with crowding.

Do not estimate.

### 8. What information is likely useful for ADVERSE_60D?

Conceptual only:

- **High funding percentile**, rich basis, high OI/mcap, high perp/spot volume (crowded leverage).
- **ETF outflows** and stablecoin **contraction**.
- Liquidations / exchange inflows **if** a paid tape is ever frozen (not now).

Do not estimate.

### 9. What should NOT be collected yet?

- Liquidations and CEX flows.
- Polymarket panel / sentiment index.
- True daily breadth (new universe).
- Microstructure L2 and large 5m RV dumps.
- Social scrapes, news NLP, Google Trends.
- Hundreds of rolling windows.
- CME basis until a roll rule is specified.
- Anything that requires modifying Phase 1, Phase 2, `v1_weekly_core`, or MACRO_BASE_CANDIDATE_V1.

### 10. What is the exact next implementation phase?

**Phase 3B — Derivatives dataset.**

Scope: source listing + header confirmation + daily Binance USD-M panel for KEEP derivative variables. No models. No Phase 3F tests. No claim that 2024–2026 is clean OOS.

If Vision metrics OI is missing or starts too late, 3B still ships funding/basis/volume and **documents OI as unavailable**, rather than substituting Coinglass.
