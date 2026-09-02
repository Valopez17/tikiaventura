# Phase 3B — Derivatives dataset

Build a daily UTC BTCUSDT derivatives panel and audit coverage /
timestamps. **No models. No signals. No window tuning.**

Question this phase answers:

> What derivatives information is actually available, from when, with
> what timestamp quality, and can it be constructed without look-ahead?

Decision time: **end of UTC day t**. Every feature on date t uses only
prints with timestamp ≤ 23:59:59 UTC on t.

**2024–2026 is already inspected** in prior phases. This dataset is not
a new clean OOS test.

## Layout

```
phase3b_derivatives_dataset/
├── README.md
├── src/build_derivatives_dataset.py
├── data/raw/          # Vision ZIPs + REST JSON + manifest
├── data/processed/btc_derivatives_daily.csv
└── results/
    ├── DERIVATIVES_COVERAGE_AUDIT.md
    ├── DERIVATIVES_DATA_AUDIT.md
    └── DERIVATIVES_FEATURE_DICTIONARY.md
```

Do not modify Phase 1, Phase 2, Phase 3A `results/`, `v1_weekly_core`,
or MACRO_BASE_CANDIDATE_V1.

## Sources (verified, then downloaded)

| Concept | Source | Notes |
|---|---|---|
| Funding | Binance Vision monthly `fundingRate` 2020-01–2026-07 | REST `/fapi/v1/fundingRate` **only** for Vision gaps (2019-09-10–2019-12-31 and 2026-08). Same exchange/contract; overlap checked. |
| Basis | Vision `premiumIndexKlines` 1h | Not CME. Mark/index fallback not used. |
| Perp volume | Vision USD-M BTCUSDT 1d klines | Quote USDT volume. |
| Spot quote volume | Vision **spot** BTCUSDT 1d klines | Phase 1 tape is **base BTC** volume — not used for the ratio. |
| Open interest | Vision daily `metrics` | `sum_open_interest_value`. Starts 2020-09-01. No backfill. |

Not built: liquidations, oi_over_mcap, Coinglass / Glassnode / CryptoQuant.

## Run

```bash
python3 src/build_derivatives_dataset.py
```

Needs network. Existing raw ZIPs are not overwritten. Re-run is safe.

## Percentiles

Same convention as Phase 1: expanding, history **strictly before t**,
minimum **365** finite prior observations. Do not shorten for OI.
