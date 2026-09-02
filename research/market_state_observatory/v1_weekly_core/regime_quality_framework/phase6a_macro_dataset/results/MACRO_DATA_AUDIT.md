# Phase 6A — Macro data audit

Sample: Fridays **2015-01-02** through **2023-12-29** (calendar window 2015-01-01 … 2023-12-31).

Question answered: *Do we have a clean, temporally defensible macro dataset that could have been known week by week?*

This file is **not** a model, score, or crypto comparison. 2024–2026 was not downloaded or used.

## Hard cutoff

| bound | value |
|---|---|
| output first Friday | 2015-01-02 |
| output last Friday | 2023-12-29 |
| last raw observation allowed | 2023-12-31 |
| lookback raw start (daily/weekly) | 2014-10-01 |
| lookback Friday grid (not in output) | 2014-10-03 … 2014-12-26 |
| M2 raw start | 2014-01 |
| rows in `macro_weekly.csv` | 470 |

Pre-2015 observations are used **only** as lookback for 4-week / 12-week changes. They are not output rows.

## Lookahead scale

| rating | meaning in this file |
|---|---|
| LOW | Friday alignment uses a market or same-week official print; residual risk is vendor/revision, not month-scale lag. |
| MEDIUM | Timing is plausible but lag or revision is material. |
| HIGH | Monthly / delayed / revised history. Not true vintage. Do not treat as known in real time. |

No series is claimed as real-time unless the release convention was verified. None of these series are ALFRED vintages.

## Series

### DXY_LEVEL — Broad US dollar (Fed Nominal Broad Dollar Index)

| field | value |
|---|---|
| source | Board of Governors, H.10 Foreign Exchange Rates, Data Download Program |
| identifier | `H10/H10/JRXWTFB_N.B (Nominal Broad Dollar Index, Jan 1997=100)` |
| raw frequency | daily (business day) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2301 |
| raw missing (parsed rows) | 112 |
| weekly alignment | Last non-missing H.10 observation with calendar date on or before Friday; drop if older than 7 calendar days (holiday gap). No interpolation. |
| publication / release lag | H.10 daily indexes are typically available the same or next business day. Implementation uses observation date, not a verified same-day timestamp. |
| contemporaneously observable? | Approximately yes for Friday close of the index; official release timing not verified tick-by-tick. |
| revision / vintage | Current revised history from Board DDP. Not ALFRED vintage / real-time. |
| lookahead_risk | **LOW** |
| fallback | Requested ICE DXY was not used. This is the Fed trade-weighted broad dollar, not the ICE U.S. Dollar Index (DXY). |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Column prefix DXY_ is a project label for a dollar proxy. Do not interpret as ICE DXY. |

### FED_FUNDS — Effective federal funds rate

| field | value |
|---|---|
| source | Federal Reserve Bank of New York, Markets Data API (EFFR) |
| identifier | `NY Fed eventCodes=500, productCode=50, field Rate (%)` |
| raw frequency | daily (business day) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2323 |
| raw missing (parsed rows) | 0 |
| weekly alignment | EFFR for date D is treated as available on D+1 business day (~9:00 a.m. ET). Friday uses the last EFFR whose publication date is on or before Friday (typically Thursday's rate). Stale >7 calendar days → missing. Friday's own EFFR is not used at t. |
| publication / release lag | One New York business day (NY Fed published methodology). |
| contemporaneously observable? | No: Friday's EFFR prints Monday. This implementation uses the lagged print. |
| revision / vintage | Current NY Fed history. EFFR revisions are possible; this is not a vintage tape. |
| lookahead_risk | **LOW** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Not the target range; not H.15 monthly effective funds. |

### US2Y — US Treasury 2-year CMT yield

| field | value |
|---|---|
| source | Board of Governors, H.15 Selected Interest Rates, Data Download Program |
| identifier | `H15/H15/RIFLGFCY02_N.B` |
| raw frequency | daily (business day) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2313 |
| raw missing (parsed rows) | 100 |
| weekly alignment | Last non-missing yield on or before Friday; drop if older than 7 calendar days. No interpolation. ND codes treated as missing. |
| publication / release lag | H.15 daily yields are released on the same business day (afternoon). Implementation uses observation date. |
| contemporaneously observable? | Yes at daily close for a business-day Friday; holiday Fridays use prior session. |
| revision / vintage | Current Board DDP history, not ALFRED vintage. |
| lookahead_risk | **LOW** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes |  |

### US10Y — US Treasury 10-year CMT yield

| field | value |
|---|---|
| source | Board of Governors, H.15 Selected Interest Rates, Data Download Program |
| identifier | `H15/H15/RIFLGFCY10_N.B` |
| raw frequency | daily (business day) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2313 |
| raw missing (parsed rows) | 100 |
| weekly alignment | Last non-missing yield on or before Friday; drop if older than 7 calendar days. No interpolation. ND codes treated as missing. |
| publication / release lag | H.15 daily yields are released on the same business day (afternoon). Implementation uses observation date. |
| contemporaneously observable? | Yes at daily close for a business-day Friday; holiday Fridays use prior session. |
| revision / vintage | Current Board DDP history, not ALFRED vintage. |
| lookahead_risk | **LOW** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes |  |

### REAL10Y — US 10-year real yield (TIPS curve)

| field | value |
|---|---|
| source | U.S. Treasury, Daily Treasury Par Real Yield Curve Rates |
| identifier | `daily_treasury_real_yield_curve column 10 YR; yearly CSV 2014–2023` |
| raw frequency | daily (business day) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2313 |
| raw missing (parsed rows) | 0 |
| weekly alignment | Last non-missing 10Y real par yield on or before Friday; drop if older than 7 calendar days. |
| publication / release lag | Treasury publishes daily real par yields on the same business day. Implementation uses observation date. |
| contemporaneously observable? | Approximately yes on a business-day Friday. |
| revision / vintage | Current Treasury historical files (revised history), not a locked vintage. |
| lookahead_risk | **LOW** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Par real yield from the TIPS curve, not TIPS ETF price. |

### VIX — VIX

| field | value |
|---|---|
| source | Yahoo Finance chart API (CBOE Volatility Index close) |
| identifier | `^VIX daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31` |
| raw frequency | daily (session close) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2328 |
| raw missing (parsed rows) | 85 |
| weekly alignment | Last non-missing close on or before Friday; drop if older than 7 calendar days. |
| publication / release lag | Index close is known at the cash close. Vendor timestamp converted America/New_York calendar date. |
| contemporaneously observable? | Yes for Friday close, subject to vendor completeness. |
| revision / vintage | Vendor historical closes, not CBOE official CSV. Not a vintage tape. |
| lookahead_risk | **LOW** |
| fallback | CBOE's single-file VIX_History.csv extends past 2023; it was not used so 2024–2026 rows would never be requested. |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Public market source with a hard period2 cutoff. Not claimed as exchange-official. |

### HY_SPREAD — High yield credit spread

**OMITTED.** FRED graph CSV timed out / was unreachable from this environment. No FRED API key is present. No date-bounded official ICE CSV was used. Last error: The read operation timed out

- Intended source: ICE BofA US High Yield Index Option-Adjusted Spread via FRED (BAMLH0A0HYM2)
- Identifier: `BAMLH0A0HYM2`
- Fallback used: none
- Notes: Not invented. Not replaced with a different credit spread.

### NASDAQ — Nasdaq Composite (risk-asset proxy)

| field | value |
|---|---|
| source | Yahoo Finance chart API (NASDAQ Composite close) |
| identifier | `^IXIC daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31` |
| raw frequency | daily (session close) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-29 |
| raw observations (non-missing) | 2328 |
| raw missing (parsed rows) | 0 |
| weekly alignment | Last non-missing close on or before Friday; drop if older than 7 calendar days. |
| publication / release lag | Cash close known at session end. Vendor timestamp converted America/New_York calendar date. |
| contemporaneously observable? | Yes for Friday close, subject to vendor completeness. |
| revision / vintage | Vendor historical closes. Not CRSP. Not a vintage tape. |
| lookahead_risk | **LOW** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Price level; 4w/12w columns are simple returns, not point changes. |

### FED_BALANCE_SHEET — Federal Reserve balance-sheet proxy

| field | value |
|---|---|
| source | Board of Governors, H.4.1 Factors Affecting Reserve Balances, Data Download Program (single-series package) |
| identifier | `H41/H41/RESH4SC_N.WW — Reserve Bank credit, Wednesday level (USD millions)` |
| raw frequency | weekly (Wednesday level) |
| raw first date | 2014-10-01 |
| raw last date | 2023-12-27 |
| raw observations (non-missing) | 483 |
| raw missing (parsed rows) | 0 |
| weekly alignment | Wednesday level treated as available the next business day (typical Thursday H.4.1 release). Friday uses the last Wednesday print whose as-of date is on or before Friday. Stale >12 calendar days → missing. No interpolation. |
| publication / release lag | H.4.1 is released Thursday for the prior Wednesday. Friday of the same week can know that Wednesday level. |
| contemporaneously observable? | Wednesday level is not a Friday market print; it is known by Friday under the Thursday-release convention used here. |
| revision / vintage | Current Board DDP history. H.4.1 is occasionally revised. Not WALCL vintage from ALFRED. |
| lookahead_risk | **LOW** |
| fallback | FRED WALCL (Total Assets less eliminations) was not used: FRED CSV timed out. The wide H.4.1 Table 1 DDP package was empty on multi-year pulls, so RESH4S (total factors supplying) was not taken. This series is Reserve Bank credit, the main H.4.1 asset stock, not identical to WALCL. |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Units: millions of USD, as published (multiplier 1e6). Do not treat as FRED WALCL or as total assets including gold/SDR/Treasury currency. |

### M2 — US M2 money stock (seasonally adjusted)

| field | value |
|---|---|
| source | Board of Governors, H.6 Money Stock Measures, Data Download Program |
| identifier | `H6/H6_M2/M2.M (seasonally adjusted monthly; multiplier 1e9 USD)` |
| raw frequency | monthly |
| raw first date | 2014-01-31 |
| raw last date | 2023-12-31 |
| raw observations (non-missing) | 120 |
| raw missing (parsed rows) | 0 |
| weekly alignment | Month M is dated at month-end. Conservative availability = month-end + 21 calendar days. Friday receives the last monthly observation whose availability date is on or before Friday. The weekly series is a step function (held until the next conservatively dated release). Not interpolated. December 2023 M2 has availability in January 2024 and is therefore NOT assigned to any 2023 Friday. |
| publication / release lag | Assumed 21 days after month-end. This is an approximation of H.6 publication, not the actual historical release calendar and not ALFRED vintage. |
| contemporaneously observable? | No. Monthly, lagged, and revised. |
| revision / vintage | Current H.6 history (benchmark revisions). NOT true vintage/as-of money stock. |
| lookahead_risk | **HIGH** |
| fallback | none |
| weekly first non-missing | 2015-01-02 |
| weekly last non-missing | 2023-12-29 |
| weekly non-missing | 470 / 470 |
| weekly missing | 0 (0.00%) |
| notes | Units: billions of USD as published. Do not claim real-time M2. |

## A. Coverage

| series | included | source | identifier | raw freq | raw first | raw last | lookahead |
|---|---|---|---|---|---|---|---|
| DXY_LEVEL | yes | Board of Governors, H.10 Foreign Exchange Rates, Data Download Program | `H10/H10/JRXWTFB_N.B (Nominal Broad Dollar Index, Jan 1997=100)` | daily (business day) | 2014-10-01 | 2023-12-29 | LOW |
| FED_FUNDS | yes | Federal Reserve Bank of New York, Markets Data API (EFFR) | `NY Fed eventCodes=500, productCode=50, field Rate (%)` | daily (business day) | 2014-10-01 | 2023-12-29 | LOW |
| US2Y | yes | Board of Governors, H.15 Selected Interest Rates, Data Download Program | `H15/H15/RIFLGFCY02_N.B` | daily (business day) | 2014-10-01 | 2023-12-29 | LOW |
| US10Y | yes | Board of Governors, H.15 Selected Interest Rates, Data Download Program | `H15/H15/RIFLGFCY10_N.B` | daily (business day) | 2014-10-01 | 2023-12-29 | LOW |
| REAL10Y | yes | U.S. Treasury, Daily Treasury Par Real Yield Curve Rates | `daily_treasury_real_yield_curve column 10 YR; yearly CSV 2014–2023` | daily (business day) | 2014-10-01 | 2023-12-29 | LOW |
| VIX | yes | Yahoo Finance chart API (CBOE Volatility Index close) | `^VIX daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31` | daily (session close) | 2014-10-01 | 2023-12-29 | LOW |
| HY_SPREAD | NO | ICE BofA US High Yield Index Option-Adjusted Spread via FRED (BAMLH0A0HYM2) | `BAMLH0A0HYM2` | daily (business day) |  |  | n/a (omitted) |
| NASDAQ | yes | Yahoo Finance chart API (NASDAQ Composite close) | `^IXIC daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31` | daily (session close) | 2014-10-01 | 2023-12-29 | LOW |
| FED_BALANCE_SHEET | yes | Board of Governors, H.4.1 Factors Affecting Reserve Balances, Data Download Program (single-series package) | `H41/H41/RESH4SC_N.WW — Reserve Bank credit, Wednesday level (USD millions)` | weekly (Wednesday level) | 2014-10-01 | 2023-12-27 | LOW |
| M2 | yes | Board of Governors, H.6 Money Stock Measures, Data Download Program | `H6/H6_M2/M2.M (seasonally adjusted monthly; multiplier 1e9 USD)` | monthly | 2014-01-31 | 2023-12-31 | HIGH |

## B. Missingness (weekly output)

| column | n missing | pct missing | first non-missing | last non-missing |
|---|---|---|---|---|
| DXY_LEVEL | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| DXY_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| DXY_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_FUNDS | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_FUNDS_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_FUNDS_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US2Y | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US2Y_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US2Y_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US10Y | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US10Y_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| US10Y_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| REAL10Y | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| REAL10Y_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| REAL10Y_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| VIX | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| VIX_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| VIX_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| NASDAQ | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| NASDAQ_RET_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| NASDAQ_RET_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_BALANCE_SHEET | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_BALANCE_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| FED_BALANCE_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| M2 | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| M2_CHG_4W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |
| M2_CHG_12W | 0 | 0.00% | 2015-01-02 | 2023-12-29 |

## C. First 5 weekly rows

| week | DXY_LEVEL | FED_FUNDS | US2Y | US10Y | REAL10Y | VIX | NASDAQ | FED_BALANCE_SHEET | M2 |
|---|---|---|---|---|---|---|---|---|---|
| 2015-01-02 | 102.9027 | 0.06 | 0.66 | 2.12 | 0.41 | 17.79 | 4726.8101 | 4457837 | 11638.9 |
| 2015-01-09 | 103.1213 | 0.12 | 0.59 | 1.98 | 0.36 | 17.55 | 4704.0698 | 4459910 | 11638.9 |
| 2015-01-16 | 103.2189 | 0.12 | 0.49 | 1.83 | 0.23 | 20.95 | 4634.3799 | 4476465 | 11638.9 |
| 2015-01-23 | 104.3676 | 0.12 | 0.52 | 1.81 | 0.21 | 16.66 | 4757.8799 | 4473381 | 11721.2 |
| 2015-01-30 | 105.5884 | 0.11 | 0.47 | 1.68 | 0.03 | 20.97 | 4635.2402 | 4461085 | 11721.2 |

## D. Last 5 weekly rows

| week | DXY_LEVEL | FED_FUNDS | US2Y | US10Y | REAL10Y | VIX | NASDAQ | FED_BALANCE_SHEET | M2 |
|---|---|---|---|---|---|---|---|---|---|
| 2023-12-01 | 119.9424 | 5.33 | 4.56 | 4.22 | 2 | 12.63 | 14305.0303 | 7759408 | 20737.5 |
| 2023-12-08 | 120.7607 | 5.33 | 4.71 | 4.23 | 2.02 | 12.35 | 14403.9697 | 7700979 | 20737.5 |
| 2023-12-15 | 119.7382 | 5.33 | 4.44 | 3.91 | 1.69 | 12.28 | 14813.9199 | 7703394 | 20737.5 |
| 2023-12-22 | 119.0625 | 5.33 | 4.31 | 3.9 | 1.71 | 13.03 | 14992.9697 | 7687649 | 20749.7 |
| 2023-12-29 | 118.4208 | 5.33 | 4.23 | 3.88 | 1.72 | 12.45 | 15011.3496 | 7675996 | 20749.7 |

## E. Warnings

- HY_SPREAD omitted: FRED BAMLH0A0HYM2 could not be downloaded. Do not treat the panel as containing credit-spread information.
- DXY_LEVEL is the Fed Nominal Broad Dollar Index, not ICE DXY. Do not compare levels to DXY futures quotes.
- FED_BALANCE_SHEET is H.4.1 Reserve Bank credit (Wednesday), not FRED WALCL total assets.
- M2 lookahead_risk is HIGH: monthly SA, assumed 21-day lag, revised history, not vintage.
- VIX and NASDAQ closes come from Yahoo Finance with a unix period2 cutoff at 2023-12-31. Vendor data, not exchange official files.
- 4-week and 12-week changes at the start of 2015 use 2014 lookback. They are not out-of-sample relative to 2014 data; they are in-sample transformations.
- No interpolation. Daily holiday gaps use last-on-or-before with a short staleness cap.
- No 2024–2026 observations were requested from Fed DDP, NY Fed, Treasury year files, or Yahoo period2.

## Transformations

| group | columns | change definition |
|---|---|---|
| dollar index, VIX, Nasdaq, Fed BS, M2 | `*_CHG_*` / `NASDAQ_RET_*` | simple percent: `x_t / x_{t-n} - 1` on the Friday series |
| funds, 2Y, 10Y, real 10Y | `*_CHG_*` | percentage-point difference: `x_t - x_{t-n}` |

`n` is 4 or 12 **calendar weeks** on the Friday grid (`shift(4)` / `shift(12)`). No PCA, z-scores, or regimes.

## What this phase did not do

- logistic / any regression
- merge onto crypto outcomes
- inspect 2024–2026
- variable selection on returns
- macro score or Bull/Bear macro labels
- modify Phase 3 / 4 / 5 or V1

