# Phase 6H — Final clean OOS for MACRO_BASE_CANDIDATE_V1

Evaluate the **frozen** candidate on **2024–2026**. Evaluation only.

No feature changes. No C search. No lag. No regime filters. No threshold
tuning. Not a trading strategy.

## Frozen spec

`MACRO_BASE_CANDIDATE_V1` (Phase 6G):

- Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`
- Logistic L2 `C=1.0`, train-only median + `StandardScaler`, min train N=100
- L = 0; horizons 4w / 8w / 12w
- Target: subsequent H-week crypto market return > 0

## Data

Same sources and definitions as the 2015–2023 branch:

- Crypto: CoinMarketCap historical Friday listings (Hsieh tape) + V1
  observatory-eligible value-weighted `market_return`
- Macro: Fed H.10 broad dollar, H.15 2Y, Treasury TIPS 10Y real, Yahoo `^IXIC`

2015–2023 feature/return history is **spliced in from frozen files**, not
re-estimated. 2024+ is an extension of those series. If a required source
is unavailable, the script stops instead of substituting.

## Run

```bash
python3 src/run_final_clean_oos.py
```

Needs network for CMC listings and the four macro sources. Listings cache
under `data/raw/`.

## Outputs

- `results/final_oos_metrics.csv`
- `results/FINAL_CLEAN_OOS.md`
