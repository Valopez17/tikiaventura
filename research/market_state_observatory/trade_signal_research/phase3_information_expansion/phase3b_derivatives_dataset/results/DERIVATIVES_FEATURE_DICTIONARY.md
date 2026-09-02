# Derivatives feature dictionary

Built: `2026-08-30T16:46:48Z`. Exchange: Binance USD-M **BTCUSDT** unless noted. Decision time: end of UTC day t.

Percentiles are in **[0, 100]**, same scale as Phase 1. Ranking rule: history strictly before t, min 365.

Do not treat high funding as deterministically bearish or negative funding as bullish. These series measure crowding, leverage, participation, and position build/unwind. Predictive value is for Phase 3F.

## `funding_rate_last`

- **Exact formula:** Last BTCUSDT USD-M funding settlement with fundingTime ≤ 23:59:59 UTC on t (UTC date of the settlement).
- **Units:** rate per 8h interval (not annualized)
- **Source:** Vision monthly fundingRate; REST for Vision gaps
- **First valid date (this build):** 2019-09-10
- **Expected economic interpretation:** Cost of being long the perp that interval. Positive → longs pay shorts (crowded long / bullish basis). Measures crowding / carry, not a directional rule.
- **Likely relevance to UP_60D:** Possibly after deeply negative funding (short crowding). Untested.
- **Likely relevance to ADVERSE_60D:** Possibly at high positive funding extremes (long crowding). Untested.
- **Timestamp rule:** Settlement instant UTC.
- **Known limitation:** Exchange-specific. 8h interval in this sample; do not annualize without documenting the interval. Vision missing 2019-Q4 and 2026-08.

## `funding_mean_1d`

- **Exact formula:** Mean of all settlements whose UTC calendar date is t.
- **Units:** rate per interval
- **Source:** same funding prints
- **First valid date (this build):** 2019-09-10
- **Expected economic interpretation:** Day's average carry, less noisy than a single 16:00 print.
- **Likely relevance to UP_60D:** Same as level, milder. Untested.
- **Likely relevance to ADVERSE_60D:** Same as level, milder. Untested.
- **Timestamp rule:** Only prints on day t.
- **Known limitation:** Typically 3 prints (00:00, 08:00, 16:00 UTC).

## `funding_change_1d`

- **Exact formula:** funding_rate_last(t) − funding_rate_last(t−1)
- **Units:** rate difference
- **Source:** derived
- **First valid date (this build):** 2019-09-11
- **Expected economic interpretation:** Speed of crowding / de-crowding.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Fast spike into already-high funding may coincide with stress. Untested.
- **Timestamp rule:** Both ends ≤ t.
- **Known limitation:** NaN on first funding day.

## `funding_mean_7d`

- **Exact formula:** Mean of all settlements with timestamp in [t 00:00 UTC − 6d, t 23:59:59.999 UTC]. NaN if t is within 6 days of first funding day.
- **Units:** rate per interval
- **Source:** derived
- **First valid date (this build):** 2019-09-16
- **Expected economic interpretation:** Persistent carry over a week.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Untested.
- **Timestamp rule:** Prints ≤ t only.
- **Known limitation:** Window is calendar 7d of prints, not 7 prints. Not tuned.

## `funding_cum_30d`

- **Exact formula:** Sum of all settlements in [t 00:00 UTC − 29d, t 23:59:59.999 UTC]. NaN if t is within 29 days of first funding day.
- **Units:** sum of interval rates (not $ PnL)
- **Source:** derived
- **First valid date (this build):** 2019-10-09
- **Expected economic interpretation:** Running cost of staying long for ~30d of 8h prints.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Large positive sum = longs have paid a lot. Untested.
- **Timestamp rule:** Prints ≤ t.
- **Known limitation:** Not dollar-weighted by OI. Not annualized.

## `funding_pctl`

- **Exact formula:** Expanding percentile of funding_rate_last:  mean(I(x_s ≤ x_t) for finite s < t). NaN if fewer than 365 finite prior observations.
- **Units:** percentile in [0, 100], Phase 1 scale
- **Source:** derived (Phase 1 convention)
- **First valid date (this build):** 2020-09-09
- **Expected economic interpretation:** Where today's last funding sits in this contract's history.
- **Likely relevance to UP_60D:** Low percentile (cheap/negative vs history). Untested.
- **Likely relevance to ADVERSE_60D:** High percentile. Untested.
- **Timestamp rule:** History strictly before t.
- **Known limitation:** Unstable early; 365-day gate.

## `basis_last`

- **Exact formula:** Close of the last USD-M BTCUSDT premium-index 1h kline with close_time on UTC date t.
- **Units:** (mark−index)/index as published in the premium index kline close
- **Source:** Vision premiumIndexKlines 1h
- **First valid date (this build):** 2019-12-24
- **Expected economic interpretation:** Perp richness vs spot index. Positive = perp premium (long demand / bullish basis).
- **Likely relevance to UP_60D:** Extreme cheap/negative basis (short crowding). Untested.
- **Likely relevance to ADVERSE_60D:** Extreme rich basis. Untested.
- **Timestamp rule:** Bar close_time 23:59:59.999 UTC on t.
- **Known limitation:** Binance-specific. First day 2019-12-24 starts 03:00 UTC. Not CME annualized basis.

## `basis_change_1d`

- **Exact formula:** basis_last(t) − basis_last(t−1)
- **Units:** premium-index difference
- **Source:** derived
- **First valid date (this build):** 2019-12-31
- **Expected economic interpretation:** Speed of richness change.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Untested.
- **Timestamp rule:** Both ≤ t.
- **Known limitation:** NaN on first basis day.

## `basis_pctl`

- **Exact formula:** Expanding percentile of basis_last, s < t, min 365 finite priors.
- **Units:** percentile in [0, 100], Phase 1 scale
- **Source:** derived
- **First valid date (this build):** 2020-12-29
- **Expected economic interpretation:** Historical rarity of today's premium.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Untested.
- **Timestamp rule:** History strictly before t.
- **Known limitation:** Same 365-day gate.

## `perp_quote_volume`

- **Exact formula:** USD-M BTCUSDT 1d kline quote asset volume for UTC day t.
- **Units:** USDT
- **Source:** Vision futures um 1d klines
- **First valid date (this build):** 2019-12-31
- **Expected economic interpretation:** Leveraged-market activity that day.
- **Likely relevance to UP_60D:** High volume with rising prices can be participation. Untested.
- **Likely relevance to ADVERSE_60D:** High volume with falling prices can be stress. Untested.
- **Timestamp rule:** Completed 1d bar, close_time 23:59:59.999 UTC t.
- **Known limitation:** Binance only. Starts 2019-12-31.

## `perp_volume_rel_30d`

- **Exact formula:** perp_quote_volume(t) / median(perp_quote_volume[t−30 .. t−1]). Prior window only (Phase 1 rel_volume style).
- **Units:** ratio
- **Source:** derived
- **First valid date (this build):** 2020-01-30
- **Expected economic interpretation:** Unusual perp activity vs the last 30 days.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Very high relative volume often coincides with liquidations/stress. Untested.
- **Timestamp rule:** Median uses s < t.
- **Known limitation:** NaN until 30 prior perp days. Window not tuned.

## `perp_volume_pctl`

- **Exact formula:** Expanding percentile of perp_quote_volume, s < t, min 365.
- **Units:** percentile in [0, 100], Phase 1 scale
- **Source:** derived
- **First valid date (this build):** 2020-12-30
- **Expected economic interpretation:** Historical rarity of today's perp USDT volume.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Untested.
- **Timestamp rule:** History strictly before t.
- **Known limitation:** Level percentiles mix secular growth in Binance volume; interpret with care.

## `perp_spot_volume_ratio`

- **Exact formula:** perp_quote_volume(t) / spot_quote_volume(t), both USDT quote volume from Vision 1d klines.
- **Units:** ratio (USDT/USDT)
- **Source:** Vision USD-M 1d + Vision spot 1d
- **First valid date (this build):** 2019-12-31
- **Expected economic interpretation:** How much activity sits in perps vs spot. High ratio = leverage-heavy tape.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Possibly when perps dominate. Untested.
- **Timestamp rule:** Both completed UTC day t bars.
- **Known limitation:** Phase 1 spot tape is base BTC volume and was not used. Ratio NaN if either quote series missing. Binance-specific.

## `oi_value`

- **Exact formula:** Last strictly positive `sum_open_interest_value` snapshot on UTC date t with create_time ≤ 23:59:59 UTC, after dropping duplicate timestamps (keep last) and dropping t+1 spill. Trailing 0E-8 rows are ignored.
- **Units:** USDT notional
- **Source:** Vision daily metrics BTCUSDT
- **First valid date (this build):** 2020-09-01
- **Expected economic interpretation:** Stock of leveraged positions (notional).
- **Likely relevance to UP_60D:** Rising OI with rising price can be fuel. Untested.
- **Likely relevance to ADVERSE_60D:** High OI into a drop can be unwind fuel. Untested.
- **Timestamp rule:** Last snapshot ≤ t 23:59:59 UTC. Late-sample last snapshot may be before 23:59 (e.g. 23:40).
- **Known limitation:** Starts 2020-09-01. Cadence changes (5m duplicates → irregular). No 2019 OI. No mcap ratio in 3B.

## `oi_change_1d`

- **Exact formula:** oi_value(t) / oi_value(t−1) − 1
- **Units:** fraction
- **Source:** derived
- **First valid date (this build):** 2020-09-02
- **Expected economic interpretation:** 1-day notional OI growth/contraction.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Fast OI drop with negative returns may be forced unwind. Untested.
- **Timestamp rule:** Both days' last snapshots ≤ their day ends.
- **Known limitation:** Percent change, not a dollar difference. NaN if prior day missing.

## `oi_change_7d`

- **Exact formula:** oi_value(t) / oi_value(t−7) − 1
- **Units:** fraction
- **Source:** derived
- **First valid date (this build):** 2020-09-08
- **Expected economic interpretation:** Week-scale position build/unwind.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Untested.
- **Timestamp rule:** t and t−7 last snapshots only.
- **Known limitation:** Calendar 7d, not 7 business days (crypto 24/7).

## `oi_pctl`

- **Exact formula:** Expanding percentile of oi_value, s < t, min 365 finite OI days. Not shortened.
- **Units:** percentile in [0, 100], Phase 1 scale
- **Source:** derived
- **First valid date (this build):** 2021-09-01
- **Expected economic interpretation:** Historical crowding of Binance BTCUSDT notional OI.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** Right tail. Untested.
- **Timestamp rule:** History strictly before t.
- **Known limitation:** First valid ~365 days after 2020-09-01. Secular growth in OI makes recent percentiles often high.

## `oi_over_volume`

- **Exact formula:** oi_value(t) / perp_quote_volume(t) if perp_quote_volume > 0
- **Units:** USDT OI per USDT daily perp volume (days of volume)
- **Source:** derived
- **First valid date (this build):** 2020-09-01
- **Expected economic interpretation:** How large the position stock is relative to that day's trading. High = sticky crowding / thin vs OI.
- **Likely relevance to UP_60D:** Untested.
- **Likely relevance to ADVERSE_60D:** High ratio may mean painful unwind. Untested.
- **Timestamp rule:** Both known at end of t.
- **Known limitation:** Optional; only where both clean. Not oi_over_mcap (no frozen BTC mcap series used).

