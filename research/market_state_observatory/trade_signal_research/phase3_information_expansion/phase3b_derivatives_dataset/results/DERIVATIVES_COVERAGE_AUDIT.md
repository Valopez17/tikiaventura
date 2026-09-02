# Derivatives coverage audit

Built: `2026-08-30T16:46:48Z`. Decision time: end of UTC day t. Panel last date: **2026-08-29** (last complete Vision daily file).

No Coinglass / Glassnode / CryptoQuant / CME / Yahoo substitution.

## Raw source listing (Step 1)

| source | prefix | n_zip | first key | last key |
|---|---|---:|---|---|
| funding_monthly | `data/futures/um/monthly/fundingRate/BTCUSDT/` | 79 | `data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-01.zip` | `data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-07.zip` |
| funding_daily | `data/futures/um/daily/fundingRate/BTCUSDT/` | 0 | `None` | `None` |
| premium_1h_monthly | `data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1h/` | 79 | `data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip` | `data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2026-07.zip` |
| premium_1h_daily | `data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/` | 2435 | `data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2019-12-24.zip` | `data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2026-08-29.zip` |
| perp_1d_monthly | `data/futures/um/monthly/klines/BTCUSDT/1d/` | 79 | `data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2020-01.zip` | `data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2026-07.zip` |
| perp_1d_daily | `data/futures/um/daily/klines/BTCUSDT/1d/` | 2434 | `data/futures/um/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2019-12-31.zip` | `data/futures/um/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2026-08-29.zip` |
| metrics_daily | `data/futures/um/daily/metrics/BTCUSDT/` | 2189 | `data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-09-01.zip` | `data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-08-29.zip` |
| spot_1d_monthly | `data/spot/monthly/klines/BTCUSDT/1d/` | 108 | `data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2017-08.zip` | `data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2026-07.zip` |
| spot_1d_daily | `data/spot/daily/klines/BTCUSDT/1d/` | 3300 | `data/spot/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2017-08-17.zip` | `data/spot/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2026-08-29.zip` |
| mark_1h_monthly | `data/futures/um/monthly/markPriceKlines/BTCUSDT/1h/` | 79 | `data/futures/um/monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip` | `data/futures/um/monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-07.zip` |
| index_1h_monthly | `data/futures/um/monthly/indexPriceKlines/BTCUSDT/1h/` | 79 | `data/futures/um/monthly/indexPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip` | `data/futures/um/monthly/indexPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-07.zip` |

### Sample headers

- **funding** (`data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-01.zip`): columns `['calc_time', 'funding_interval_hours', 'last_funding_rate']`, n_rows=93
- **premium_1h** (`data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip`): columns `['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']`, n_rows=744
- **perp_1d** (`data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2020-01.zip`): columns `['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']`, n_rows=31
- **metrics** (`data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-09-01.zip`): columns `['create_time', 'symbol', 'sum_open_interest', 'sum_open_interest_value', 'count_toptrader_long_short_ratio', 'sum_toptrader_long_short_ratio', 'count_long_short_ratio', 'sum_taker_long_short_vol_ratio']`, n_rows=576
- **spot_1d** (`data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2017-08.zip`): columns `['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']`, n_rows=15
- **premium_1h_early_daily** (`data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-2019-12-24.zip`): columns `['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']`, n_rows=21
- **perp_1d_early_daily** (`data/futures/um/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2019-12-31.zip`): columns `['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']`, n_rows=1

### Timestamp semantics (from samples + full read)

- **Funding Vision:** `calc_time` milliseconds UTC = settlement instant. Header: `calc_time,funding_interval_hours,last_funding_rate`.
- **Funding REST:** `fundingTime` milliseconds UTC. Overlap with Vision on 2020-01-01 matches to the printed rate (including 2ms quirks).
- **Premium 1h:** kline `open_time`/`close_time` ms UTC. Daily `basis_last` = `close` of the last bar with `close_time` on UTC day t (the 23:00–23:59 bar, close_time 23:59:59.999).
- **1d klines:** `open_time` = 00:00:00 UTC of t; `close_time` = 23:59:59.999 UTC of t. Quote volume = USDT.
- **Metrics OI:** `create_time` naive datetime, treated as **UTC**. Last snapshot on calendar date t with time ≤ 23:59:59. File-day spill into t+1 dropped.

## REST gap fill (same Binance BTCUSDT, not a vendor switch)

- Pre-Vision: `data/raw/rest/funding_pre_vision.json` n=384 status=skipped_exists
- Aug 2026 tail: `data/raw/rest/funding_aug2026.json` n=181 status=skipped_exists
- Funding prints in panel: n=7637, vision=7212, rest_used=425
- REST vs Vision overlapping fundingTime rows: 139; |rate| mismatch > 1e-12: 0
- First funding print: 2019-09-10T08:00:00+00:00
- Last funding print: 2026-08-29T16:00:00.002000+00:00
- `funding_interval_hours` unique (Vision rows): [8.0]

Vision **daily** `fundingRate` prefix has **0** files. Current month funding cannot come from Vision.

## Download

- Vision ZIP attempts: 2624; downloaded=0; skipped_exists=2624; errors=0. Existing ZIPs are never overwritten.
- OI metrics files listed: 2189; days with a last snapshot: 2189
- Duplicate OI timestamps dropped (keep last): 75255
- Days where last snapshot was non-positive so an earlier same-day positive print was used: 3

## Feature coverage

| feature | first finite | last finite | N finite | % missing (panel) | missing days inside span | largest gap (days) |
|---|---|---|---:|---:|---:|---:|
| `funding_rate_last` | 2019-09-10 | 2026-08-29 | 2546 | 0.00 | 0 | 0 |
| `funding_mean_1d` | 2019-09-10 | 2026-08-29 | 2546 | 0.00 | 0 | 0 |
| `funding_change_1d` | 2019-09-11 | 2026-08-29 | 2545 | 0.04 | 0 | 0 |
| `funding_mean_7d` | 2019-09-16 | 2026-08-29 | 2540 | 0.24 | 0 | 0 |
| `funding_cum_30d` | 2019-10-09 | 2026-08-29 | 2517 | 1.14 | 0 | 0 |
| `funding_pctl` | 2020-09-09 | 2026-08-29 | 2181 | 14.34 | 0 | 0 |
| `basis_last` | 2019-12-24 | 2026-08-29 | 2435 | 4.36 | 6 | 6 |
| `basis_change_1d` | 2019-12-31 | 2026-08-29 | 2434 | 4.40 | 0 | 0 |
| `basis_pctl` | 2020-12-29 | 2026-08-29 | 2070 | 18.70 | 0 | 0 |
| `perp_quote_volume` | 2019-12-31 | 2026-08-29 | 2434 | 4.40 | 0 | 0 |
| `perp_volume_rel_30d` | 2020-01-30 | 2026-08-29 | 2404 | 5.58 | 0 | 0 |
| `perp_volume_pctl` | 2020-12-30 | 2026-08-29 | 2069 | 18.74 | 0 | 0 |
| `perp_spot_volume_ratio` | 2019-12-31 | 2026-08-29 | 2434 | 4.40 | 0 | 0 |
| `oi_value` | 2020-09-01 | 2026-08-29 | 2189 | 14.02 | 0 | 0 |
| `oi_change_1d` | 2020-09-02 | 2026-08-29 | 2188 | 14.06 | 0 | 0 |
| `oi_change_7d` | 2020-09-08 | 2026-08-29 | 2182 | 14.30 | 0 | 0 |
| `oi_pctl` | 2021-09-01 | 2026-08-29 | 1824 | 28.36 | 0 | 0 |
| `oi_over_volume` | 2020-09-01 | 2026-08-29 | 2189 | 14.02 | 0 | 0 |

Panel index is a complete UTC calendar from the earliest series start through `2026-08-29` (N=2546). Pre-history is left as NaN, not filled.

## Explicit questions

### 1. Does funding really start near 2019-09?

**On Binance REST, yes. On Binance Vision monthly archives, no.**

- USD-M BTCUSDT listing is 2019-09. REST first print in the pull: see first_ts above (expected **2019-09-10 08:00 UTC**).
- Vision monthly `fundingRate` first file: **2020-01**. 2019-09 and 2019-12 monthly URLs return **404**. Daily Vision fundingRate: **empty**.
- This build uses REST for 2019-09-10 through 2019-12-31 and Vision from 2020-01-01, after checking that 2020-01-01 prints match.

### 2. Does basis have the same start?

**No.** Premium-index 1h daily Vision starts **2019-12-24** (first bar 03:00 UTC — incomplete first day). Monthly 1h starts **2020-01**. Mark/index 1h also exist from ~2019-12 / 2020-01 but were **not** mixed in; basis is premium index only.

### 3. Does perp volume have complete history?

Vision daily 1d klines start **2019-12-31** (one day before monthly 2020-01). Monthly 2020-01 through 2026-07 plus daily 2026-08-01..29. No 1m/aggTrades. Quote-volume field present. Gaps inside that span are reported in the table above.

### 4. When does OI actually start?

**2020-09-01** through **2026-08-29**. File `BTCUSDT-metrics-2020-08-31.zip` is **404**. No backfill. REST `openInterestHist` was not used (30-day cap).

### 5. Is there enough overlap for later modeling?

Core funding + basis + perp quote volume overlap from **2020-01-01** (basis from 2019-12-24, perp from 2019-12-31, funding from 2019-09-10). Expanding percentiles need 365 prior finite days → funding/basis/volume percentiles from ~late 2020 / early 2021. OI levels from 2020-09-01; `oi_pctl` only after 365 OI days (~2021-09-01). That is shorter than Phase 2's 2015– BTC-percentile sample. Later 3F tests must restrict to the derivatives overlap, not pretend 2015–2019 has these features.

### 6. Are there structural source changes?

- **Funding packaging:** Vision monthly from 2020-01; REST elsewhere. Values match on overlap. Interval hours on Vision samples remain **8** through 2026-07; REST rows do not always carry interval.
- **Premium files:** early daily ZIPs include a header row; monthly 1h ZIPs often have no header. Same kline layout.
- **OI cadence:** 2020-09-01 metrics file is ~5-minute snapshots with **duplicate timestamps**. 2026-08-29 file is **irregular** (first snapshot 01:10, last 23:40, not a 5-minute grid). Median step is stored as `oi_median_step_sec`.
- **OI last snapshot:** three metrics files (2022-03-07, 2024-07-10, 2024-07-12) end at 23:55 with `0E-8` notional while earlier snapshots that day are large and positive. Daily `oi_value` uses the last **strictly positive** `sum_open_interest_value` ≤ 23:59:59 UTC, not the garbage trailing row.
- **Premium monthly holes:** some monthly 1h ZIPs omit days that still exist as daily Vision files (e.g. 2021-07-01, 2021-07-24–27). Those days are filled from the daily prefix when the ZIP exists. 2019-12-25 through 2019-12-30 daily URLs return **404** and stay missing.
- **Spot vs Phase 1:** Phase 1 volume is **base BTC**. This panel's ratio uses Vision spot **quote USDT** vs perp **quote USDT**.
- **Spot kline timestamps:** monthly/daily spot 1d files switch from **milliseconds** to **microseconds** beginning **2025-01**. This build divides values ≥ 1e14 by 1000 so dates stay on the UTC day. Perp/premium/funding samples remain milliseconds.

## Known source gaps

| gap | expected? |
|---|---|
| Vision funding 2019-09–2019-12 | Yes — files 404; filled from REST |
| Vision daily fundingRate | Yes — prefix empty; Aug 2026 from REST |
| Vision monthly files for 2026-08 | Yes — month incomplete; daily klines/metrics/premium used |
| OI before 2020-09-01 | Yes — metrics not published |
| Premium 2019-12-25–2019-12-30 | Yes — daily Vision 404; no fill |
| Perp 1d before 2019-12-31 | Yes — first daily file |
| Panel 2026-08-30 (build calendar today) | Yes — Vision daily lag; not included |

