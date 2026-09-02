# Trade signal research

ENTRY / HOLD / REDUCE / EXIT / STAY OUT.

This branch is **not** market-state or macro research. The frozen
observatory lives in `../v1_weekly_core/` and must not be modified here.

Every calculation should connect to a decision at time t. This is not a
live trading system.

## Phase 1

`phase1_capitulation_entries/` — BTC-only daily event study:

after an extreme selloff, when historically did buying look attractive?

## Phase 2

`phase2_statistical_model_competition/` — chronological 80/20 holdout
competition of a small frozen model set on 60-day UP / ADVERSE targets.

No strategy, no PnL, no extra features, no tuning on the last 20%.

## Phase 3

`phase3_information_expansion/` — feature-family and data-source audit (Step A)
plus `phase3b_derivatives_dataset/` and `phase3b2_derivatives_incremental_test/`
(historical walk-forward incremental test; not clean OOS).

## Strategy lab

`strategy_lab/phase1_simple_strategy_discovery/` — executable test of three
frozen BTC ideas (session anomaly, capitulation+deleveraging, macro LONG/CASH).
Historical backtest / temporal robustness. Not clean OOS.

`strategy_lab/phase2_macro_candidate_validation/` — try to break frozen
`C_macro_long_cash` (timing audit, delays, costs, year/subperiod stress).
Not clean OOS.

`strategy_lab/phase3_weekly_calendar_anomaly/` — exhaustive weekly
day/hour entry×exit scan on BTCUSDT 1h, same-duration calendar-edge
control, frozen chronological discovery/validation/recent. Price + time
only. Not clean OOS. Frozen; not combined with later phases.

`strategy_lab/phase4_extreme_move_reversal/` — expanding-percentile
extreme 6/12/24/72h BTC moves, rebound vs continuation, next-hour open
entry, frozen discovery/validation/recent. Price only. Not clean OOS.

`strategy_lab/phase4b_extreme_move_audit_fix/` — audit/correction of
Phase 4 (exact-timestamp lookbacks, hourly MTM equity, stricter
survivor rule). No new search. Frozen Top 10 not reselected.

`strategy_lab/phase5_breakout_continuation/` — close vs prior-window
maximum high (7/30/60/90d), LONG breakout continuation, next-hour open
entry, frozen discovery/validation/recent. Price only. Not clean OOS.
Calendar and crash-rebound candidates are frozen and not combined.
