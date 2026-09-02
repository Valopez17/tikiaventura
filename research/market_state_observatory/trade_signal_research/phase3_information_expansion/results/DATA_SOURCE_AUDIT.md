# Data source audit

Phase 3 Step A. Official/public sources first. No silent substitution. If historical availability is not verified by a listing or a documented first row, it is **UNKNOWN**.

This file covers every **KEEP FOR DATA BUILD** candidate from `FEATURE_FAMILY_REGISTRY.md`. DIAGNOSTIC / DEFER / DROP sources are noted only where they would otherwise be confused with KEEP.

**No large downloads were performed.** Binance USD-M REST from this environment returned **HTTP 451**; Vision HTML listings are JS-rendered and did not return file tables here. Coverage start dates that depend on those listings remain UNKNOWN.

**Validation reminder:** 2024–2026 is already inspected. Collecting a series that only exists in 2024–2026 does not create a clean OOS test.

---

## Shared conventions for later builds (not executed here)

- Decision time: end of UTC day *t* unless a source is explicitly US-session.
- Expanding percentiles: history through *t* only.
- Do not mix vendors for the same concept (e.g. Farside vs SoSoValue ETF flows) without a documented splice rule.
- Freeze raw files with download timestamp; do not “refresh” history in a way that restates past days without a revision log.

---

## D1. Binance USD-M funding rate

**KEEP variables:** `funding_rate`, `funding_change_1d`, `funding_mean_7d`, `funding_pctl`, `cumulative_funding_30d`

1. **Exact proposed source**  
   Binance Vision monthly ZIP:  
   `https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-YYYY-MM.zip`  
   Documented by Binance public-data tooling (`fundingRate` data type).  
   **Not** the REST `/fapi/v1/fundingRate` as the primary historical path (geo/legal blocks; pagination). REST may be used later only for the incomplete current month, after Vision listing is confirmed.

2. **Coverage start/end**  
   Contract listing ~**2019-09-08**. First Vision month: **UNKNOWN**. End: through last completed month; current month incomplete on Vision.

3. **Frequency**  
   One row per funding settlement (historically 8h; Binance has since allowed other intervals on some contracts — confirm whether BTCUSDT stayed 8h throughout). Daily features = last settlement on calendar day *t* and/or mean of settlements with `fundingTime` on day *t*.

4. **Timestamp semantics**  
   Settlement instant (`fundingTime` / `calc_time` in the CSV). UTC. The rate applies to the interval **ending** at that timestamp (confirm column order from the first file’s header in 3B; do not guess column names in code until the header is read).

5. **Historical availability**  
   Vision is designed as a complete monthly archive for listed symbols. **Not verified file-by-file in this step.** Treat first month as UNKNOWN until 3B lists objects under the prefix (listing is small; downloading all months is a 3B task).

6. **API / download method**  
   HTTPS GET of monthly ZIPs. Small files (8h prints). Checksums: `*.zip.CHECKSUM` on the same prefix.

7. **Revisions**  
   Exchange archives are generally final. **UNKNOWN** whether Binance has ever replaced a monthly ZIP.

8. **Missing-data issues**  
   Listing date vs first funding print; halt days; possible missing months (404). Current month not on monthly path.

9. **Contemporaneous existence**  
   Yes: funding was a live contract feature from listing. The Vision dump is a later packaging of that tape, not a reconstructed model.

10. **Cost / authentication**  
    Free, no key. Possible IP / geo restrictions (REST 451 observed). Vision may still be reachable when REST is not — **UNKNOWN** until 3B tries a single small ZIP.

---

## D2. Binance USD-M open interest (daily metrics)

**KEEP variables:** `oi_btc`, `oi_chg_*`, `oi_over_mcap`, `oi_over_volume`, `oi_pctl`

1. **Exact proposed source**  
   Binance Vision daily metrics:  
   `https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/`  
   Community documentation of columns: `create_time`, `symbol`, `sum_open_interest`, `sum_open_interest_value`, plus long/short ratios.  
   **Rejected as historical source:** `GET /futures/data/openInterestHist` (last **30 days** only).

2. **Coverage start/end**  
   **UNKNOWN.** A public example file is dated **2023-01-21**. Earlier years may or may not exist. End: next day after trading day (Vision daily lag).

3. **Frequency**  
   Daily files. Some tooling describes 5-minute rows **inside** the daily file; the GitHub example looks like **one row per day**. **UNKNOWN** until a sample header is read in 3B (one file, not the full history).

4. **Timestamp semantics**  
   `create_time` in the example is a date. If intraday rows exist, files can spill a few seconds into D+1. Rule for 3B: last observation with timestamp ≤ *t* 23:59:59 UTC.

5. **Historical availability**  
   **UNKNOWN** before 2023-01. This is the binding constraint on OI. If Vision only starts 2023, OI cannot join a 2015–2019 BTC-percentile sample; tests must be on the overlapping window only.

6. **API / download method**  
   HTTPS GET of daily ZIPs/CSVs. Many small files if daily; still not a “huge” tape compared with ticks. 3B should list years first, then download.

7. **Revisions**  
   **UNKNOWN.**

8. **Missing-data issues**  
   Gaps; weekend files; listing vs first metrics day. Long/short ratio columns are a different concept — do not treat them as OI.

9. **Contemporaneous existence**  
   OI existed on the contract from listing (2019). **Public historical packaging may start later.** Using only the public archive is honest; inventing 2019–2022 OI from a vendor is a different source.

10. **Cost / authentication**  
    Free, no key.

**BTC market cap for `oi_over_mcap`:** use the same BTC cap already implied by Phase 1 / CMC path used for the daily BTC tape. Do not mix CoinGecko and CMC on the same ratio. Exact series name to be frozen in 3B. If Phase 1 has no explicit mcap column, **UNKNOWN** and 3B must pick one public daily BTC mcap (CMC vs CoinGecko) and document it — that is a new auxiliary series, not a redefinition of the six percentiles.

---

## D3. Binance USD-M perpetual vs spot basis

**KEEP variables:** `perp_spot_basis`, `basis_change`, `basis_pctl`

1. **Exact proposed source**  
   Binance Vision premium index klines:  
   `https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/BTCUSDT/{interval}/`  
   Proposed interval: **1h** or **8h**, downsample to last bar of UTC day *t*.  
   Fallback if that prefix 404s: mark-price klines vs index-price klines, same Vision tree. **Do not substitute CME.**

2. **Coverage start/end**  
   Expected from BTCUSDT listing 2019-09. First month: **UNKNOWN**.

3. **Frequency**  
   Intraday bars → daily last.

4. **Timestamp semantics**  
   Kline `open_time` / `close_time` in ms UTC, same convention as Vision klines. Premium index ≈ (mark − index) / index as published by Binance.

5. **Historical availability**  
   Tooling lists `premiumIndexKlines` as a USD-M Vision type. **File existence from 2019-09 is UNKNOWN** until 3B lists the prefix.

6. **API / download method**  
   Monthly ZIPs per interval. 1h monthly files are moderate size, not tick-level. Do not pull 1m.

7. **Revisions**  
   **UNKNOWN.**

8. **Missing-data issues**  
   Missing months; interval folders empty. If premium index is missing but mark and index klines exist, basis can be rebuilt — that is still Binance, not a vendor switch.

9. **Contemporaneous existence**  
   Yes, mark/index were live from listing.

10. **Cost / authentication**  
    Free, no key.

---

## D4. Binance USD-M perp volume and spot volume

**KEEP variables:** `perp_volume`, `spot_volume`, `perp_spot_volume_ratio`

1. **Exact proposed source**  
   Perp: Vision `futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-YYYY-MM.zip` (quote volume column).  
   Spot: **existing Phase 1 tape** (`btc_tsmom_replication/data/btcusd_daily.csv` Binance segment from 2017-08-17). Do not re-download a second Binance spot history unless that file is missing quote volume — then Vision spot 1d klines, same dates.

2. **Coverage start/end**  
   Perp: 2019-09 (UNKNOWN first month). Spot: 2017-08-17 through the Phase 1 end date. Ratio: from perp start.

3. **Frequency**  
   Daily.

4. **Timestamp semantics**  
   Daily kline close. Phase 1 already documented UTC daily bars.

5. **Historical availability**  
   Vision 1d klines for BTCUSDT perp are widely used; **first file month UNKNOWN** here. Spot availability is verified in Phase 1 (do not modify Phase 1).

6. **API / download method**  
   Monthly 1d ZIPs (small). Spot: read existing CSV only.

7. **Revisions**  
   Vision **UNKNOWN**. Phase 1 spot tape is frozen for that project; 3B should copy/read, not rewrite Phase 1 outputs.

8. **Missing-data issues**  
   Perp vs spot calendar alignment (both 24/7). Quote vs base volume: freeze **quote USDT volume** on perp and **quote USD/USDT volume** on spot so the ratio is dimensionless activity, not coin units.

9. **Contemporaneous existence**  
   Yes.

10. **Cost / authentication**  
    Free. Spot already local.

---

## D5. US spot Bitcoin ETF net flows

**KEEP variables:** `etf_net_flow_usd`, `etf_flow_5d`, `etf_flow_20d`, `etf_flow_over_mcap`

1. **Exact proposed source**  
   **Primary:** Farside Investors public flow table, `https://farside.co.uk/BTC/` (issuer-by-issuer USD millions, daily).  
   **Cross-check only (not a silent substitute):** SoSoValue US BTC spot ETF dashboard.  
   **Spot check:** BlackRock IBIT holdings / shares outstanding on issuer pages.  
   There is no official SEC bulk “ETF flow” API for this panel.

2. **Coverage start/end**  
   **2024-01-11** (first US spot BTC ETF trading) through latest published row. Pre-2024 GBTC is **out of scope**.

3. **Frequency**  
   US equity trading days (no weekend flows). Crypto 24/7 dates without a flow print = 0 after the last published date is known, or NA until publish — freeze the rule in 3C.

4. **Timestamp semantics**  
   Table date = flow **activity date**, typically published **after** that US session (lag ~1 trading day is reported by aggregators). A Friday decision at UTC midnight may **not** yet have Friday’s Farside row.

5. **Historical availability**  
   The public HTML table currently shows a full daily history on the site (observed in search snippets through 2026-08). **Whether Farside has ever revised past rows is UNKNOWN.** No independent official archive.

6. **API / download method**  
   Parse HTML table (fragile). Optional community mirrors exist; **do not switch** without a reconciliation to Farside. No bulk download of “large” tick data.

7. **Revisions**  
   **UNKNOWN.** Possible late issuer corrections. Keep a dated snapshot of the table.

8. **Missing-data issues**  
   US holidays; delayed issuer reporting; fund list changes (freeze the issuer set as of a 3C date; document new listings as separate columns, not a changing total without a note).

9. **Contemporaneous existence**  
   The ETFs existed from Jan 2024. Farside is a **third-party scrape of issuer disclosures**, not the primary source. Contemporaneous traders saw issuer/AP data with the same lag, not necessarily Farside’s table.

10. **Cost / authentication**  
    Free, no key. Terms: Farside disclaims errors. Not a licensed data feed.

**Sample-length warning:** the entire series lives in the already-inspected 2024–2026 window. KEEP is about collectability, not about a new OOS test.

---

## D6. DefiLlama aggregate stablecoin market cap

**KEEP variables:** `stablecoin_mcap_total`, `stablecoin_issuance_7d_30d`

1. **Exact proposed source**  
   DefiLlama Stablecoins API:  
   `https://stablecoins.llama.fi/stablecoincharts/all`  
   (also documented under `api.llama.fi` stablecoin routes — **use one base URL and freeze it**; do not mix).  
   This is **not** the Observatory Friday `STABLECOIN_MCAP` (CMC curated symbols). Different name, different composition.

2. **Coverage start/end**  
   Documented example point **2021-01-01** (unix 1609459200). Earlier: **UNKNOWN**. End: latest API date.

3. **Frequency**  
   Daily (one unix `date` per point in the public examples).

4. **Timestamp semantics**  
   Unix date; typically 00:00 UTC for that calendar day. **Confirm** whether the figure is start-of-day or end-of-day circulating supply.

5. **Historical availability**  
   API returns an array of historical points. **Whether Llama restates history when chains or stables are added is UNKNOWN** and likely **yes** (methodology product). 3C must save a frozen JSON.

6. **API / download method**  
   Single GET (small JSON). No key for the public stablecoin routes used here.

7. **Revisions**  
   **Likely.** Treat as a vintage-dated series.

8. **Missing-data issues**  
   Depegs (UST): inclusion rules change the total. Wrapped / bridged double counting — Llama documents circulating vs minted; freeze `totalCirculatingUSD.peggedUSD` (or equivalent) after reading one payload in 3C.

9. **Contemporaneous existence**  
   USDT/USDC supply existed before 2021. Llama’s **aggregated chart** is a later dataset. Using it before Llama’s first date is not allowed. Using it from 2021 is using Llama’s reconstruction, not a 2015 on-chain node.

10. **Cost / authentication**  
    Free public API. Rate limits apply.

---

## Auxiliary source needed by KEEP ratios (not a new family)

**BTC market cap (daily)** for `oi_over_mcap` and `etf_flow_over_mcap`.

1. Proposed source: **UNKNOWN until 3B/3C** — pick one of: CoinMarketCap historical (same family as observatory listings, daily if available), CoinGecko, or a simple `price × circulating supply` from a frozen supply series.  
2–10. Cannot be filled honestly until the ticker is chosen. **Do not silently use Yahoo or a random website.**

If no clean daily mcap is available without a new paid product, **drop the ratio variables** and keep OI and ETF flows in native units. Data quality > quantity.

---

## Intentionally not KEEP — source notes (so they are not “substituted in”)

| Candidate | Why no KEEP audit row |
|---|---|
| Coinglass / Glassnode / CryptoQuant OI, liquidations, exchange flows | Paid; not assumed. Liquidations also fail free reconstruction (Binance USD-M liquidationSnapshot reported removed; REST not a tape). |
| CME annualized basis | Roll calendar + Yahoo `BTC=F` quality UNKNOWN; official CME often paid. DEFER. |
| Polymarket | Fields exist (t, p, metadata) but **no stationary series** for this project’s panel. DEFER/DROP as in the registry. |
| Alternative.me Fear & Greed | DIAGNOSTIC ONLY. Source would be `https://api.alternative.me/fng/?limit=0`, daily from ~2018-02-01, free. Publish lag and input collinearity not cleared for KEEP. |
| Google Trends / news / Reddit / X | DROP (units, corpus, or access). |
| Observatory daily breadth | Would require a new listings methodology. DEFER / DIAGNOSTIC step-function only. |
| Tardis / Kaiko L2 | Paid; DEFER. |

---

## Verification log (this step)

| Check | Result |
|---|---|
| Binance REST fundingRate | HTTP **451** from this environment |
| Binance Vision HTML prefix listing | Empty table (client-rendered); files **not** confirmed |
| Large dataset download | **Not done** (per spec) |
| Farside / SoSoValue / DefiLlama / Alternative.me / Polymarket CLOB | Documented from public docs and search; not bulk-pulled |

Phase 3B’s first job is a **file listing + one-sample header read** for Vision funding, metrics, premium index, and 1d klines — still not a full history download until those prefixes exist.
