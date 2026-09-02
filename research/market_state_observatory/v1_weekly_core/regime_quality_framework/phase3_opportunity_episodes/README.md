# Phase 3 — Opportunity episodes + extreme attribution

Learn, on **2015–2023 only**, what crypto-internal configurations at week `t`
preceded the best and worst 4-week and 12-week market windows.

This is **descriptive**. Outcome labels are retrospective. They are not predictors
and not trading rules.

V1 baseline is read-only. 2024–2026 is not used. Macro is not used.

## Inputs (read-only)

- `v1_weekly_core/results/weekly_market_state.csv`
- Hsieh `crypto_weekly_panel.csv` (attribution + lagged large-cap)

## Outputs

- `results/opportunity_episode_catalog.csv`
- `results/extreme_episode_attribution.csv`
- `results/OPPORTUNITY_EPISODE_ANALYSIS.md`

## Frozen research buckets (not retuned)

Momentum percentiles: `<40`, `40–70`, `70–90`, `>=90`  
Broad breadth: `<40%`, `40–50%`, `50–60%`, `60–70%`, `70–80%`, `>=80%`  
VOL percentile: same as momentum  
TURNOVER_RELATIVE: `<0.75`, `0.75–1.0`, `1.0–1.25`, `>1.25`  
STABLECOIN_MCAP_12W_CHANGE: `<0`, `0–5%`, `5–10%`, `>10%`

## Run

```bash
python3 src/analyze_opportunity_episodes.py
```
