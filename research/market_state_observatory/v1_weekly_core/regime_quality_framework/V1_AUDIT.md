# V1 audit — Crypto Market State Observatory

Audit of the frozen v1 weekly core against `CANONICAL_INDICATORS.md` and `NORTHSTAR.md`.

**V1 is not overwritten.** This file is documentation only.

Code: `v1_weekly_core/src/build_market_state_v1.py`  
Panel: `research/papers/hsieh_2025_state_transition_momentum/data/processed/crypto_weekly_panel.csv` (read-only)  
Results: `v1_weekly_core/results/` (untouched)

Sample in the frozen outputs: Friday weeks **2015-01-02 → 2023-12-29** (470 weeks).  
2024–2026 is **not** in this panel and was not used to choose thresholds.

---

## Verdict

V1 is a usable **crypto-only baseline**. Return conversion, lagged market-return weights, eligibility (except size ranking), breadth, volatility, turnover, stablecoin construction, and forward alignment `t+1…t+h` match the canonical contract.

Two issues must be treated as known limitations in the next research layer (do **not** silently rewrite V1 outputs):

1. **Large-cap top 100 uses contemporaneous market cap**, not lagged. Canonical preferred implementation is lagged mcap.
2. **Historical analog z-scores use the full sample through the last week**, so they are not as-of-t for past weeks.

Neither contaminates the V1 **state labels** (direction + vol overlay). Both matter for later walk-forward and for analog interpretation.

Missing vs the next phases (expected): `MOM_4W_PERCENTILE`, `MOM_12W_PERCENTILE`. Not a V1 bug.

---

## 1. Weekly return convention

**Status: PASS**

Source `weekly_return` is a log return \(\ln(P_t/P_{t-1})\). V1 converts **before any aggregation**:

`simple_return = expm1(weekly_return)`

Market weights, MOM, index, coin 4w returns, volatility, and forward outcomes all use simple returns. Matches canonical §3.

---

## 2. Market weighting

**Status: PASS (with documented drop rule)**

`market_return_t = Σ w_{i,t-1} * r_{i,t}` among `observatory_eligible` at t.  
Weights = lagged market cap, renormalized to 1 among coins with finite positive lag mcap.

Coins eligible at t but missing lag mcap are dropped from the **weighted sum only**; they can still enter breadth. First calendar weeks have no lag → `market_return` NaN until **2015-06-26** (445 finite market-return weeks).

This is lagged-weight, contemporaneous-eligibility — the canonical formula.

---

## 3. Eligibility

**Status: PASS**

Week-t rule (all required):

1. not Observatory stablecoin (curated symbol list, **not** Hsieh `is_stablecoin`);
2. `market_cap_t >= 10_000_000` (PRIMARY; robustness $1M / $50M exist);
3. ≥ 26 Friday snapshots with `weekly_price > 0` through t;
4. finite simple return;
5. finite mcap > 0;
6. finite volume > 0;
7. finite price > 0.

No retroactive delisting. Hsieh `eligible` is unused.

**Note:** the $10M screen is contemporaneous mcap, same as canonical wording “at week t”. That is separate from the large-cap **ranking** issue in §5.

Consequence of the 26-week history rule: BTC itself is ineligible until it has 26 Fridays, so the value-weighted market starts later than the panel start. Correct under the contract; do not “fix” by shortening history.

---

## 4. Breadth

**Status: PASS**

Coin 4w return = product of four **calendar** Friday simple returns. Incomplete paths are omitted from the denominator.

`broad_breadth_4w` = equal-weight share with 4w return > 0 among eligible coins with a complete path.

Also stored: median / p25 / p75 coin 4w, `n_eligible_coins`, `n_breadth_coins`.

Matches canonical §6.

---

## 5. Large-cap definition

**Status: FAIL vs preferred canonical implementation; PASS vs V1’s own frozen README**

V1: top 100 eligible coins by **contemporaneous** market cap. If n_eligible < 100, use all (104 such weeks; 25 weeks with n_largecap = 0).

Canonical §7: *preferred predictive implementation uses lagged market cap*.

Contemporaneous ranking lets this week’s return affect who is “large cap” this week. That is a mild look-ahead relative to a lagged-size screen. V1 already documents it as a frozen choice.

**Do not rewrite V1 CSVs.** For the regime-quality layer, compute a lagged-mcap top 100 in parallel and compare. If results differ, the lagged version is the one to carry into walk-forward.

`breadth_gap = largecap_breadth_4w − broad_breadth_4w` is descriptive only. OK.

---

## 6. Volatility percentiles

**Status: PASS**

`VOL_12W` = sample std of the last 12 weekly **simple** market returns, `ddof=1`, not annualized. Requires 12 finite observations.

`VOL_PERCENTILE` = expanding empirical CDF using weeks ≤ t only (includes the current observation, which is the standard as-of-t CDF).

`HIGH_VOL` iff percentile ≥ 0.70. Frozen for V1.

Early-sample percentiles are mechanically noisy (few history points). Do not treat 2015 HIGH_VOL as comparable to 2021 HIGH_VOL without that caveat.

---

## 7. Turnover

**Status: PASS**

Coin turnover = volume / mcap among eligible. No winsorization.

`market_turnover` = cross-sectional median. `market_turnover_p75` stored.

`TURNOVER_RELATIVE` = current / trailing 12-week median of `market_turnover`, window **includes t**. That is “information through t”, not future.

`TURNOVER_PERCENTILE` = expanding CDF of the turnover **level**.

CMC volume can include wash trading. Unverified. Diagnostic, not executable liquidity.

---

## 8. Stablecoin construction

**Status: PASS, with known coverage limits**

Stables excluded from return/breadth via Observatory allowlist (USDT, USDC, DAI, BUSD, historical UST/USTC, wrapped USD aliases, etc.). Gold-pegged (PAXG, XAUT) excluded. Hsieh substring flag is **not** used (it false-positives APT, ATOM, UNI, TON, …).

`STABLECOIN_MCAP` = sum of those coins’ mcap.  
4w/12w changes = `S_t / S_{t-k} - 1`.  
`STABLECOIN_LIQ_PERCENTILE` = expanding CDF of the **level**.

Limitations already in V1 README: wrapper double-count, thin 2015–2017 (USDT-dominated), incomplete CMC coverage, allowlist incompleteness (an unlisted stable can enter the return universe).

Growth is **not** labeled bullish. Correct.

---

## 9. Forward-return alignment

**Status: PASS**

State at t uses data through t. Forward paths start at **t+1**:

- 1w = `market_return_{t+1}`
- 4w / 12w = cumulative simple return on `t+1 … t+h`
- max drawdown / run-up on that same exclusive-forward wealth path (`W_0 = 1` at t)

If any return in the horizon is non-finite, the horizon is NaN.

Counts: 442 weeks with finite 4w forward; 434 with finite 12w. Last week 2023-12-29 has NaN forwards (no future in the panel). Correct.

**V1 outcome tables do not adjust for overlapping 4w/12w windows.** Descriptive only. Walk-forward later must not treat overlapping weeks as independent tests.

---

## 10. Look-ahead contamination

**State construction (direction + vol overlay): PASS**

MOM, breadth, VOL percentile, turnover relative, stablecoin changes, and eligibility history counts use information dated ≤ t. Forward columns are computed after state and are not inputs to labels.

**Exceptions / later-layer issues:**

| item | leak? | action |
|---|---|---|
| Large-cap rank uses mcap_t | mild (size after this week’s move) | lagged mcap in quality layer |
| Analog z-score mean/std on **all weeks through last sample week** | yes, for *historical* analog distances | expanding or as-of-t z-score in walk-forward; V1 current-week analog (2023-12-29) is still a valid *descriptive* nearest-neighbor using the frozen panel |
| Analog vector for current week includes that week in μ/σ | trivial for N≈470 | ignore |
| Expanding percentiles include t | no (canonical through t) | keep |
| Outcome tables use full-sample grouping | descriptive, not a forecast | walk-forward must recompute conditionals on matured history only |

V1 already states that analog z-scores are not a purely expanding as-of-t distance for historical weeks.

---

## What V1 does not yet have (by design)

- `MOM_4W_PERCENTILE` / `MOM_12W_PERCENTILE` (Roadmap Phase 4)
- Momentum acceleration, trailing drawdown, cross-sectional dispersion
- Extreme-episode contribution attribution (Phase 3)
- Frozen quality taxonomy (Phases 6–7)
- Walk-forward scoring (Phase 8)
- Macro (Phase 10+) — correctly absent

---

## Why the North Star problem is real in V1

Both episodes below are internally **BULL_NORMAL_VOL** (or adjacent Neutral/Bull) and produce opposite 12-week futures. That is exactly why Direction alone is too coarse.

**Late 2020 (continuation):** e.g. 2020-11-27 `BULL_NORMAL_VOL`, MOM_4W +27.8%, MOM_12W +48.6%, broad breadth 0.74, large-cap breadth 0.83, **+12w ≈ +241%**.

**Late 2021 (failure):** e.g. 2021-10-29 `BULL_NORMAL_VOL`, MOM_4W +23.4%, MOM_12W +51.5%, broad breadth 0.73, large-cap breadth 0.84, **+12w ≈ −40%**.

Bull 12w mean in V1 is **+47%** vs median **+23%** (N=155). The mean is outlier-inflated. Phase 3 attribution is required before any “Strong Bull” threshold is chosen.

---

## Recommended next work (Roadmap immediate execution)

Do **not** add macro. Do **not** open 2024–2026.

1. Extreme-episode attribution (`extreme_episode_attribution.csv`, `EXTREME_EPISODE_ANALYSIS.md`)
2. Expanding `MOM_4W_PERCENTILE` / `MOM_12W_PERCENTILE` with pre-specified buckets
3. Breadth / vol / liquidity quality conditionals
4. Parallel lagged-mcap large-cap breadth (research column, leave V1 files unchanged)

---

## Freeze reminder

V1 thresholds remain frozen:

- BULL: MOM_4W>0, MOM_12W>0, broad_breadth>0.50
- BEAR: opposite signs and breadth<0.50
- HIGH_VOL: VOL_PERCENTILE ≥ 0.70
- PRIMARY universe: $10M

No result-driven retuning.
