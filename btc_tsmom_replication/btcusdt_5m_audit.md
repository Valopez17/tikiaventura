# BTCUSDT 5-minute snapshot audit

Exchange: Binance Spot `BTCUSDT`. Interval: 5m. Timezone: UTC.
Source: binance_spot_klines_5m
File: `btcusdt_5m.csv`

## Integrity

- SHA256: `119ee73d9211cd829e5d84d622989cc15aab4df4086bcb2e1ea1856731f07396`
- N rows: 947823
- timestamp inicial: 2017-08-17 04:00:00
- timestamp final: 2026-08-27 04:05:00
- duplicated timestamps: 0
- NaN OHLCV rows: 0
- missing 5m intervals (calendar 5m, not interpolated): 1715

Missing examples (first 20): 2017-09-06 16:05:00, 2017-09-06 16:10:00, 2017-09-06 16:15:00, 2017-09-06 16:20:00, 2017-09-06 16:25:00, 2017-09-06 16:30:00, 2017-09-06 16:35:00, 2017-09-06 16:40:00, 2017-09-06 16:45:00, 2017-09-06 16:50:00, 2017-09-06 16:55:00, 2017-09-06 17:00:00, 2017-09-06 17:05:00, 2017-09-06 17:10:00, 2017-09-06 17:15:00, 2017-09-06 17:20:00, 2017-09-06 17:25:00, 2017-09-06 17:30:00, 2017-09-06 17:35:00, 2017-09-06 17:40:00

Gaps are documented only. Execution is not stopped for small real exchange holes.

## Hour reconstruction (not a resample black box)

Binance 5m timestamp = bar **open**.

Hour `h` on date `d` covers `[h:00, h+1:00)`.

The 12 bars are:

`h:00, h:05, h:10, h:15, h:20, h:25, h:30, h:35, h:40, h:45, h:50, h:55`.

**`p` at the end of hour h = close of the `h:55`–`(h+1):00` bar.**

`source_5m_timestamp` in `hourly_prices_from_5m.csv` is that `h:55` open time.

The close of the `h:00` bar is the price at `h:05`. It is **not** the hourly close.

`complete_hour = True` iff `n_5m_bars_in_hour == 12`. Incomplete hours are kept as flags; prices are not interpolated. If the `h:55` bar is missing, `hourly_close` is NaN.

Hourly prices written: 79129. Incomplete hours: 159.

Return: `r_{d,h} = log(P_{d,h}) - log(P_{d,h-1})`. Hour 0 uses the previous day's hour-23 close (price at 00:00). If the required previous price is missing, return is NaN.
