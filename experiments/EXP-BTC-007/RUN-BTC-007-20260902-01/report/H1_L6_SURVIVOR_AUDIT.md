# H1 L6 survivor audit — mechanical report

Numeric truth is `result/RESULT.json` and the CSV outputs. This markdown does not override them.

Frozen rule: `L6_down_p1_rebound_long_H6`
Mechanical disposition: **FREEZE_PROSPECTIVE_RECOMMENDED**
mechanical_gate: **PASS** (separate from disposition and from Valita).

Not a trading edge. Not clean OOS. Does not authorize capital. Not a confirmed edge.
ChatGPT audit pending. Valita freeze/discard pending. HYP-BTC-002 remains INVALIDATED.
E-03 and E-04 are not CLOSED.

## Gate inputs (10 bps unless noted)

| Period | N trades | mean net 10bps | cond adv | MTM Sharpe | mean net 20bps |
|---|---:|---:|---:|---:|---:|
| discovery | 62 | 0.0151053 | 0.0139078 | 1.09794 | 0.0140892 |
| validation | 29 | 0.00462196 | 0.00423535 | 0.456385 | 0.00361633 |
| recent | 11 | 0.00459929 | 0.00296233 | 0.439671 | 0.00359369 |
| full | 102 | 0.0109918 | 0.0108274 | 0.827082 | 0.00997975 |

Validation bootstrap status: `OK`; Pr(mean_net>0)=0.9303; N=29; seed=0; expected block length=5; 10000 replications.

Year stability: years_with_positive_mean_net=9/9; max_positive_year_share=0.63; positive_outside_2020_2022=6

## Clause results

Hard-fail (any fail → DISCARD):
- `disc_mean_net_10bps_gt_0`: PASS
- `disc_cond_adv_gt_0`: PASS
- `val_mean_net_10bps_gt_0`: PASS
- `val_cond_adv_gt_0`: PASS
- `val_mtm_sharpe_finite_gt_0`: PASS
- `val_n_trades_ge_15`: PASS
- `recent_not_negative_when_n_ge_5`: PASS

Freeze clauses (all required, and no hard fail, for FREEZE_PROSPECTIVE_RECOMMENDED):
- `val_mean_net_20bps_gt_0`: PASS
- `val_bootstrap_pr_mean_net_gt_0_ge_0_80`: PASS
- `recent_n_ge_5_and_mean_net_cond_adv_mtm_sharpe_ge_0`: PASS
- `at_least_two_calendar_years_positive_mean_net`: PASS
- `at_least_one_positive_year_outside_2020_2022`: PASS
- `largest_positive_year_share_lt_70pct`: PASS

FREEZE_PROSPECTIVE_RECOMMENDED means only: freeze the exact rule and observe prospectively without capital.

## Annual table

| year | N | mean net | year PnL | MTM return | +PnL share |
|---:|---:|---:|---:|---:|---:|
| 2018 | 6 | 0.00701786 | 0.0376647 | 0.0376647 | 0.0285944 |
| 2019 | 13 | 0.00378875 | 0.0489628 | 0.0489628 | 0.0371718 |
| 2020 | 12 | 0.0173664 | 0.217423 | 0.217423 | 0.165064 |
| 2021 | 31 | 0.0205411 | 0.835881 | 0.835881 | 0.634587 |
| 2022 | 21 | 0.00270036 | 0.0524564 | 0.0524564 | 0.0398241 |
| 2023 | 2 | 0.0123892 | 0.0246315 | 0.0246315 | 0.0186998 |
| 2024 | 6 | 0.00875846 | 0.0524995 | 0.0524995 | 0.0398568 |
| 2025 | 5 | 0.0020196 | 0.00996669 | 0.00996669 | 0.00756655 |
| 2026 | 6 | 0.00674903 | 0.037718 | 0.037718 | 0.0286349 |

50 bps is stress only. MaxDD is reported without an invented risk-tolerance threshold.

