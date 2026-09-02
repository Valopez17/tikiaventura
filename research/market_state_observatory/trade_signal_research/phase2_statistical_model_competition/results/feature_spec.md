# Feature specification — Phase 2 (frozen before holdout scoring)

Written after computing the chronological split and **before** looking at holdout metrics.
Holdout is not used for feature, target, model, or threshold choices.

## Chronological split

| item | value |
|---|---|
| eligible N | 3819 |
| development N | 3055 |
| holdout N | 764 |
| split: last development date | **2024-05-27** |
| first holdout date | 2024-05-28 |
| last eligible date | 2026-06-30 |
| rule | first 80% of eligible dates by chronological order; last 20% untouched |

## Targets (frozen)

- `UP_60D` = 1 if P(t+60)/P(t) − 1 > +20%, else 0.
- `ADVERSE_60D` = 1 if MAE < −15%, else 0.
- MAE = min_{s=t+1,...,t+60} [P(s)/P(t) − 1]. Event day t is excluded from the path.
- Horizon 60 calendar days of BTC daily closes. No change after seeing results.

## Features (frozen)

### A. BTC percentiles (strictly expanding, s < t, min 365 finite observations)

- `pctl_ret_1d`
- `pctl_ret_3d`
- `pctl_ret_7d`
- `pctl_dd_30`
- `pctl_vol_20`
- `pctl_rel_volume`

Underlying raw series: ret_1d, ret_3d, ret_7d, dd_30 from trailing 30d high,
20d stdev of daily returns, volume / prior-20d median volume (Binance-era volume only).
2017-08-17 splice-day ret_1d is NaN (Bitstamp→Binance join).

### B. Frozen macro 12w changes

- `DXY_CHG_12W`
- `US2Y_CHG_12W`
- `REAL10Y_CHG_12W`
- `NASDAQ_RET_12W`

Weekly Friday series from Phase 6A through 2023-12-29 (spliced, not rewritten).
2024+ Fridays use the same sources as Phase 6H: Fed H.10 Nominal Broad Dollar,
Fed H.15 2Y, Treasury TIPS par real 10Y, Yahoo `^IXIC`.

### Daily alignment

For BTC date t, attach the latest Friday-week macro row with `week <= t`
(`merge_asof` backward). No future Friday is used. Typical lag is 0–6 days
(Friday itself through the following Thursday). Lag > 10 days is treated as missing
and later median-imputed on the training fold only.

Friday levels themselves were as-of constructed from daily prints with a 7-day
staleness cap at weekly construction time (Phase 6A/6H).

## Models (frozen)

| id | spec |
|---|---|
| M0 | expanding mature base rate |
| M1 | Logistic L2 C=1.0 |
| M2 | Probit (statsmodels) |
| M3 | Elastic-net logistic l1_ratio=0.5 C=1.0 saga |
| M4 | Additive natural cubic splines, df=4 per feature, Binomial GLM (patsy `cr` + statsmodels GLM). pygam was not installed. |
| M5 | sklearn GradientBoostingClassifier n_estimators=100 max_depth=2 learning_rate=0.05 |

Train-only median imputation. Train-only StandardScaler for M1–M3.
M4/M5: impute only. Min train N=100. Mature labels: s <= t − 60 days.
M0 is updated every prediction date. M1–M5 are refit every 7 eligible dates (coefficients held between refits). Training rows remain strictly mature. Complexity of each specification is unchanged.

## Selection (development walk-forward only)

A candidate must have BSS>0 **and** LogLoss < M0 **and** AUC>0.55.
If several qualify, pick highest BSS. If none qualify: NONE.

