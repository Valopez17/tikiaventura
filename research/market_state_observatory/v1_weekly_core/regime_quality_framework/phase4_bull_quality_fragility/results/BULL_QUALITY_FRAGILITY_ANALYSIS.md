# Bull quality & fragility (Phase 4)

Sample: weekly crypto state through **2023-12-29**. Primary universe: `state_direction == BULL`. Forward outcomes require a complete 4w or 12w path. **2024–2026 not used. Macro not used.**

Question: when the market is already Bull, do **dynamics** (change / deterioration / stress) distinguish continuation from failure better than **levels**?

Cuts below are **pre-specified and frozen**. They are not a trading rule and were not searched.

- HIGH_MOM: `MOM_12W_PERCENTILE >= 0.70`
- EXTREME_MOM: `>= 0.90`
- Breadth change buckets: ±5pp over 4 weeks
- Vol / MOM-percentile change buckets: ±0.10 over 4 weeks
- Candidate Healthy: Bull + MOM12 pctl ≥ 0.40 + breadth change ≥ −0.05 + vol-pctl change ≤ +0.10
- Candidate Fragile: Bull + MOM12 pctl ≥ 0.70 + (breadth change < −0.05 **or** vol-pctl change > +0.10)
- Liquidity flag: expanding = SC12>0 and TURNOVER_RELATIVE≥1; contracting = SC12≤0; mixed = SC12>0 and turnover below its recent median

De-clustering: first week of a consecutive group run, cooldown 4 / 12 weeks. ALL WEEKS is primary. N<20 ALL → `LOW_SAMPLE`. N<15 de-clustered → `VERY_LOW_SAMPLE`.

Healthy ∩ Fragile overlap: **0**.

| universe | N |
|---|---:|
| Bull weeks | 155 |
| complete 4w | 151 (continuation 106 / failure 45) |
| complete 12w | 145 (continuation 105 / failure 40) |
| de-clustered Bull, cooldown 4 | 25 |
| de-clustered Bull, cooldown 12 | 19–20 |

**De-cluster bias (important).** Keeping the *first* week of a Bull run systematically drops late-Bull weeks — exactly where Phase 3 said failures live. De-clustered continuation-vs-failure therefore compares early-Bull weeks and is **not** a fair robustness check of late-Bull fragility. Treat DECLUSTERED as a check on overlapping windows, not as the preferred sample for “is this Bull getting tired.”

---

## DESCRIPTIVE FINDINGS

### Continuation vs failure — levels and changes (ALL WEEKS)

Δmedian = continuation − failure. Negative means failures already looked *stronger* on that feature.

**4w** (N=106 vs 45):

| feature | med cont | med fail | Δmedian |
|---|---:|---:|---:|
| MOM_4W | 24.1% | 24.6% | −0.5pp |
| MOM_12W | 41.8% | 48.3% | −6.5pp |
| MOM_12W_PERCENTILE | 0.749 | 0.729 | +0.020 |
| broad_breadth_4w | 0.792 | 0.833 | −0.041 |
| VOL_PERCENTILE | 0.561 | 0.606 | −0.045 |
| STABLECOIN_MCAP_12W_CHANGE | 53.6% | 22.8% | +30.8pp |
| MOM12_CHANGE_4W | 23.1% | 22.9% | +0.2pp |
| MOM12_PERCENTILE_CHANGE_4W | 0.097 | 0.061 | +0.036 |
| BROAD_BREADTH_CHANGE_4W | 0.162 | 0.194 | −0.032 |
| VOL_PERCENTILE_CHANGE_4W | 0.016 | 0.000 | +0.016 |
| MARKET_DRAWDOWN_12W_HIGH | 0.0% | 0.0% | 0 |

**12w** (N=105 vs 40):

| feature | med cont | med fail | Δmedian |
|---|---:|---:|---:|
| MOM_4W | 25.0% | 23.6% | +1.4pp |
| MOM_12W | 40.4% | 80.5% | **−40.1pp** |
| MOM_12W_PERCENTILE | 0.712 | 0.859 | **−0.147** |
| broad_breadth_4w | 0.796 | 0.815 | −0.019 |
| VOL_PERCENTILE | 0.577 | 0.692 | −0.115 |
| STABLECOIN_MCAP_12W_CHANGE | 51.6% | 73.2% | −21.6pp |
| MOM4_CHANGE_4W | 14.5% | 5.0% | +9.5pp |
| MOM12_CHANGE_4W | 22.9% | 21.6% | +1.3pp |
| MOM12_PERCENTILE_CHANGE_4W | 0.094 | 0.066 | +0.029 |
| BROAD_BREADTH_CHANGE_4W | 0.200 | 0.134 | +0.066 |
| VOL_PERCENTILE_CHANGE_4W | 0.000 | 0.016 | −0.016 |
| MARKET_DRAWDOWN_12W_HIGH | 0.0% | −0.1% | ~0 |

Static MOM12 at 12w is the loudest split, and it goes the “wrong” way for a strength-is-health story: failures already had much higher 12-week momentum. Breadth *level* is also slightly higher in failures. Most Bulls sit on a 12-week high, so drawdown-from-high barely moves.

Momentum *change* among all Bulls is small. MOM4_CHANGE at 12w is the only change contrast that is economically visible (+9.5pp). Breadth is still rising in both groups; failures are not, on average, a narrowing-participation state at the median.

### High-momentum Bulls only (`MOM_12W_PERCENTILE >= 0.70`)

HIGH_MOM 4w N=86 (cont 61 / fail 25); 12w N=83 (cont 55 / fail 28).

Inside this slice, **levels of MOM12 percentile are already capped** (both groups ~0.89–0.90). What still differs at 12w:

| feature (HIGH_MOM, 12w) | med cont | med fail | Δmedian |
|---|---:|---:|---:|
| MOM_12W | 72.9% | 108.5% | −35.6pp |
| MOM4_CHANGE_4W | 15.6% | 0.9% | +14.8pp |
| MOM12_CHANGE_4W | 39.4% | 25.0% | +14.5pp |
| MOM12_PERCENTILE_CHANGE_4W | 0.126 | 0.027 | +0.099 |
| BROAD_BREADTH_CHANGE_4W | 0.149 | 0.055 | +0.093 |
| VOL_PERCENTILE_CHANGE_4W | 0.088 | 0.043 | +0.045 (cont *more* rising) |
| STABLECOIN_MCAP_12W_CHANGE | 96.6% | 112.4% | −15.8pp |

When momentum is already extreme, **deceleration of MOM4 / MOM12 change and slower breadth gains** line up more with 12w failure than raw MOM12 percentile does. That is the Phase 4 mechanism working — but only *inside* HIGH_MOM, and it is still descriptive.

### Breadth deterioration (frozen ±5pp)

| group | h | N | quality | pos | median | >10% / >20% | severe-down | med DD |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BREADTH_IMPROVING | 4 | 100 | OK | 73.0% | 12.0% | 53.0% | 15.0% | −7.9% |
| BREADTH_STABLE | 4 | 27 | OK | 63.0% | 9.2% | 48.1% | 25.9% | −10.9% |
| BREADTH_DETERIORATING | 4 | 24 | OK | 66.7% | 2.2% | 29.2% | 16.7% | −7.6% |
| BREADTH_IMPROVING | 12 | 95 | OK | 73.7% | 20.2% | 50.5% | 12.6% | −18.2% |
| BREADTH_STABLE | 12 | 26 | OK | 69.2% | 25.0% | 65.4% | 15.4% | −31.5% |
| BREADTH_DETERIORATING | 12 | 24 | OK | 70.8% | 26.3% | 54.2% | 12.5% | −14.8% |

At **4w**, deteriorating breadth has a worse median and fewer strong-up weeks. At **12w** the median is *not* worse. Lagged large-cap breadth change looks the same: 4w deteriorating median +2.0% vs improving +11.4%; 12w ~21–20%. De-clustered 4w deteriorating median goes to −0.6% (N=16). Horizon-specific, not a 12w law.

HIGH_MOM × deteriorating breadth: 4w N=12 `LOW_SAMPLE` median +4.9% vs improving +16.3% (N=52); 12w median −3.6% vs +22.3%. Direction matches the 4w breadth story. Do not promote N=12.

### Volatility change (frozen ±0.10)

| group | h | N | pos | median | severe-down | med DD |
|---|---:|---:|---:|---:|---:|---:|
| VOL_FALLING | 4 | 35 | 65.7% | 2.0% | 17.1% | −8.0% |
| VOL_STABLE | 4 | 68 | 70.6% | 13.2% | 22.1% | −8.3% |
| VOL_RISING | 4 | 48 | 72.9% | 13.3% | 10.4% | −7.7% |
| VOL_FALLING | 12 | 35 | 68.6% | 13.1% | 25.7% | −16.2% |
| VOL_STABLE | 12 | 64 | 73.4% | 28.2% | 9.4% | −21.2% |
| VOL_RISING | 12 | 46 | 73.9% | 29.0% | 8.7% | −18.2% |

Rising vol does **not** mark fragile Bulls. It looks better than falling vol at both horizons.

HIGH_MOM × vol — the pre-specified hypothesis was HighMom + rising vol = worse:

| group | h | N | quality | pos | median |
|---|---:|---:|---|---:|---:|
| HIGH_MOM_VOL_FALLING | 4 | 12 | LOW_SAMPLE | 58.3% | 1.1% |
| HIGH_MOM_VOL_STABLE | 4 | 39 | OK | 71.8% | 16.4% |
| HIGH_MOM_VOL_RISING | 4 | 35 | OK | 74.3% | 21.7% |
| HIGH_MOM_VOL_FALLING | 12 | 12 | LOW_SAMPLE | 33.3% | **−15.2%** |
| HIGH_MOM_VOL_STABLE | 12 | 36 | OK | 69.4% | 30.4% |
| HIGH_MOM_VOL_RISING | 12 | 35 | OK | 74.3% | **45.1%** |

The ugly cell is HighMom + **falling** vol, and it is `LOW_SAMPLE`. HighMom + rising vol is the *better* 2017-style continuation cell. Frozen hypothesis H3 as stated is not supported.

### Momentum acceleration (MOM12 percentile change ±0.10)

Among all Bulls, MOM_DECELERATING 4w median +4.5% vs ACCELERATING +9.0% vs STABLE +11.8%. At 12w, decelerating is not worse (median +25.6%).

Inside HIGH_MOM:

| group | h | N | quality | pos | median |
|---|---:|---:|---|---:|---:|
| HIGH_MOM_MOM_ACCELERATING | 4 | 41 | OK | 78.0% | 15.9% |
| HIGH_MOM_MOM_STABLE | 4 | 41 | OK | 65.9% | 14.3% |
| HIGH_MOM_MOM_DECELERATING | 4 | 4 | LOW_SAMPLE | 50.0% | −2.4% |
| HIGH_MOM_MOM_ACCELERATING | 12 | 38 | OK | 76.3% | 24.4% |
| HIGH_MOM_MOM_STABLE | 12 | 41 | OK | 56.1% | 8.2% |
| HIGH_MOM_MOM_DECELERATING | 12 | 4 | LOW_SAMPLE | 75.0% | 21.4% |

HIGH_MOM + still-accelerating is the cleaner 4w/12w continuation cell. HIGH_MOM + stable (percentile no longer rising) has a weaker 12w distribution. True deceleration N=4 — do not interpret.

MOM4 decelerating (all Bull): 4w median +4.2% vs stable +16.4%. Same 4w-only pattern.

### Liquidity

HIGH_MOM × SC12>0 vs ≤0: NONPOS N=5 `LOW_SAMPLE`. Almost every high-momentum Bull already has expanding stablecoins. Cannot test the sign split.

HIGH_MOM × TURNOVER_RELATIVE:

| group | h | N | quality | pos | median | p25 | severe-down | med DD |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| HIGH_MOM_TOVER_GE1 | 4 | 62 | OK | 74.2% | 15.4% | 0.8% | 16.1% | −9.9% |
| HIGH_MOM_TOVER_LT1 | 4 | 24 | OK | 62.5% | 5.6% | −10.0% | 25.0% | −13.4% |
| HIGH_MOM_TOVER_GE1 | 12 | 59 | OK | 69.5% | 45.1% | −4.7% | 10.2% | −21.2% |
| HIGH_MOM_TOVER_LT1 | 12 | 24 | OK | 58.3% | 4.6% | −18.7% | 25.0% | −29.9% |

This is one of the cleaner pre-specified 2-ways at both horizons. De-clustered 12w GE1 median collapses (N=12) — overlapping 2017 weeks. Keep as diagnostic, not a rule: high relative turnover can also be late-cycle churn.

Breadth × vol “deteriorating + rising” N=5 `LOW_SAMPLE` — ignore. Three-way HighMom + improving breadth + vol not rising: 4w N=29 median +16.4% (OK); 12w median +6.2% with a fat right tail (mean +60%). Not a clean 12w upgrade vs generic Bull.

### Candidate Healthy vs generic vs Candidate Fragile

| group | h | N | pos | mean | median | p25 | p75 | >10% | >20% | <−10% | <−20% | med DD | p25 DD | med runup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GENERIC_BULL | 4 | 151 | 70.2% | 15.1% | 9.2% | −3.4% | 25.9% | 48.3% | 33.1% | 17.2% | 6.6% | −8.1% | −15.6% | 14.8% |
| CANDIDATE_HEALTHY | 4 | 79 | 69.6% | 16.4% | 11.1% | −7.1% | 25.4% | 50.6% | 34.2% | 20.3% | 10.1% | −8.3% | −16.0% | 16.1% |
| CANDIDATE_FRAGILE | 4 | 43 | 69.8% | 19.0% | 13.6% | −1.7% | 34.0% | 58.1% | 44.2% | 16.3% | 2.3% | −10.4% | −13.2% | 26.1% |
| GENERIC_BULL | 12 | 145 | 72.4% | 47.1% | 22.5% | −4.6% | 76.9% | 62.1% | 53.8% | 19.3% | 13.1% | −18.2% | −31.5% | 38.8% |
| CANDIDATE_HEALTHY | 12 | 75 | 72.0% | 46.3% | 21.2% | −3.7% | 84.9% | 61.3% | 52.0% | 20.0% | 14.7% | −19.8% | −32.0% | 37.5% |
| CANDIDATE_FRAGILE | 12 | 43 | 67.4% | 51.1% | 17.5% | −5.8% | 81.7% | 55.8% | 48.8% | 18.6% | 11.6% | −21.2% | −31.5% | 48.0% |

(`>20%` / `<−20%` on 4w and `<−10%` on 12w are extra descriptive columns; primary strong/severe in the conditionals file use +10%/−10% at 4w and +20%/−20% at 12w.)

Candidate Healthy does **not** outperform generic Bull in a way that survives both horizons. Positive frequency is the same. 4w median is slightly higher; 12w median is slightly lower; 4w left tail is not better.

Candidate Fragile does **not** underperform at 4w (median *higher*). At 12w the median is a bit lower (17.5% vs 22.5%) but the mean is higher (2017 right tail). The fragile rule OR-s in “rising vol,” which this sample treats as a continuation state, so the group is contaminated.

De-clustered fragile N=14 / 10 → `VERY_LOW_SAMPLE`.

### Transitions

| group | N | P(BULL t+1) | P(NEUTRAL t+1) | P(BEAR t+1) | remain Bull 4w | touch N 4w | touch Bear 4w | remain Bull 12w | touch N 12w | touch Bear 12w |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GENERIC_BULL | 155 | 80.5% | 18.8% | 0.6% | 44.4% | 55.6% | 7.3% | 11.0% | 89.0% | 29.0% |
| CANDIDATE_HEALTHY | 79 | 87.3% | 12.7% | 0.0% | 48.1% | 51.9% | 8.9% | 6.7% | 93.3% | 30.7% |
| CANDIDATE_FRAGILE | 47 | 82.6% | 17.4% | 0.0% | 48.8% | 51.2% | 0.0% | 20.9% | 79.1% | 25.6% |
| HIGH_MOM_BULL | 90 | 85.4% | 14.6% | 0.0% | 47.7% | 52.3% | 2.3% | 15.7% | 84.3% | 31.3% |

Fragile does **not** leak into Bear faster over 4 weeks (0% touch Bear vs 7% generic). Over 12 weeks it actually *more often remains Bull throughout* (21% vs 11%). The frozen fragile flag is not a leading indicator of V1 regime breakdown.

### 2020 vs 2021 forensic update

| date | MOM12 pctl (Δ) | breadth Δ | vol Δ | TOVER Δ | SC growth Δ | SC12 | DD12 high | healthy | fragile | high_mom | fut12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2020-11-27 | 0.755 (**+0.323**) | +0.367 improving | +0.086 stable | +0.199 | +0.106 | **43.3%** | −2.9% | True | False | True | **+241%** |
| 2020-12-04 | 0.803 (**+0.329**) | +0.287 improving | −0.032 stable | +0.138 | +0.104 | **39.0%** | 0% | True | False | True | **+158%** |
| 2021-10-29 | 0.729 (−0.019) | +0.499 improving | **−0.225 falling** | −0.060 | −0.032 | **12.1%** | 0% | True | False | True | **−40%** |
| 2021-11-05 | 0.590 (**−0.246**) | +0.194 improving | **−0.207 falling** | +0.123 | +0.008 | **14.3%** | 0% | True | False | False | **−41%** |

What crypto-only **dynamics** add beyond Phase 3 levels:

- Late-2020: MOM12 percentile still accelerating hard; SC 4w growth accelerating; SC12 ~40%.
- Late-2021: MOM12 percentile flat then decelerating; SC growth change ~0; SC12 ~12%; vol percentile **falling** (not rising).
- Breadth is improving in **both** episodes. Drawdown-from-high is ~0 in both. Candidate Healthy/Fragile flags are **the same** on all four dates (healthy, not fragile). 2021-11-05 even fails HIGH_MOM (pctl 0.59).

The frozen fragile rule (narrowing breadth **or** rising vol) **does not fire** on late-2021. Vol is falling. Breadth is broadening.

**CRYPTO-ONLY DYNAMICS STILL INSUFFICIENT** as a classifier of these two episodes. They are not identical internally (SC12 and MOM12 acceleration differ), but the pre-specified health/fragility taxonomy does not separate them, and the vol path goes the opposite way of the rising-vol hypothesis.

---

## ANSWERS

1. **Static momentum.** Yes they differ, especially at 12w — failures have *higher* MOM12 (median 80.5% vs 40.4%). High momentum is a late-Bull marker, not health.
2. **Momentum change.** Among all Bulls, MOM12 change barely differs. MOM4_CHANGE and MOM12 percentile change help more **inside HIGH_MOM**. Dynamics do not dominate the huge static MOM12 gap; they add a second layer once you already condition on high MOM.
3. **Breadth deterioration.** Yes at **4w** (median +2% vs +12% improving; fewer >10% weeks). Not at 12w.
4. **Large-cap breadth deterioration.** Same pattern as broad breadth. Keep as the lagged twin, not as a separate discovery.
5. **Rising volatility.** No. Rising vol looks better. The weak HIGH_MOM cell is *falling* vol, and it is `LOW_SAMPLE`.
6. **Momentum deceleration.** Weakly, at 4w and inside HIGH_MOM (accelerating vs stable). True HIGH_MOM decelerating N=4.
7. **Stablecoin growth.** Inconsistent: 4w continuations have higher SC12; 12w failures have higher SC12. HIGH_MOM NONPOS is empty. Useful in the 2020 vs 2021 case study, not as a Bull-failure separator.
8. **Turnover.** HIGH_MOM + TURNOVER_RELATIVE<1 has worse 4w and 12w medians than ≥1. One of the cleaner 2-ways. Still diagnostic (churn vs sponsorship).
9. **Drawdown-from-high.** No. Almost every Bull week is at the 12w high (median 0).
10. **HighMom + breadth deterioration.** Worse directionally (12w median −3.6% vs +22.3%) but N=12 `LOW_SAMPLE`.
11. **HighMom + rising vol.** Performs **better**, not worse.
12. **Candidate Healthy vs generic.** Does not outperform in a material, two-horizon way.
13. **Candidate Fragile vs generic.** Does not cleanly underperform. Contaminated by the rising-vol OR.
14. **Economically meaningful?** The MOM12 level gap at 12w is large. 4w breadth deterioration and HIGH_MOM turnover<1 are noticeable. Candidate flags are not.
15. **De-cluster stable?** Partial. First-of-run de-clustering **removes late Bulls**, so it cannot confirm late-Bull fragility. Sparse cells after de-cluster are not evidence.
16. **Both horizons?** Almost nothing is. Breadth deterioration is 4w. MOM12 level is 12w. HIGH_MOM turnover<1 is the rare both-horizon split.
17. **2020 vs 2021.** Dynamics add SC12 and MOM12 acceleration. Frozen flags still collide. CRYPTO-ONLY DYNAMICS STILL INSUFFICIENT to classify the pair.
18–20. See disposition below.
21. Macro still has late-2020 continuation vs late-2021 failure to explain, especially given matching V1 labels, matching Healthy flags, and improving breadth in both.

---

## CANDIDATE HYPOTHESES (not predictors)

H1. A Bull can be strong in **level** and weakening in **dynamics**. Inside HIGH_MOM, slower MOM4/MOM12 change and slower breadth gains sit nearer 12w failure. Not a rule.

H2. Breadth falling while the index is still Bull is a 4w headwind. It is not a 12w failure law in this sample.

H3. High relative turnover inside HIGH_MOM is associated with better 4w/12w distributions than HIGH_MOM with turnover below its recent median. Mechanism untested (sponsorship vs late churn).

H4. Stablecoin 12w growth remains a candidate internal difference for 2020 vs 2021, not a general continuation/failure splitter.

---

## NOT SUPPORTED (this sample, these frozen cuts)

- High momentum = healthy Bull.
- High breadth level = healthy Bull.
- Rising vol-percentile = fragile Bull. Sign is the other way.
- HighMom + rising vol = worse. It is better (and includes 2017).
- Candidate Healthy outperforms generic Bull.
- Candidate Fragile underperforms generic Bull, or precedes Bear.
- Drawdown from the 12-week high separates Bull failures (everyone is at the high).
- Breadth deterioration predicts worse **12w** medians.
- De-clustered first-of-Bull-run as a test of late-Bull fragility.

---

## FEATURE DISPOSITION

Uses: continuation/failure separation, 4w+12w consistency, sample size, de-cluster caveats, interpretability. **Not** the largest historical mean.

| feature | disposition | note |
|---|---|---|
| MOM_12W / MOM_12W_PERCENTILE (level) | **KEEP** | Inverted: extreme level flags late Bull, not health. Carry as a *lateness* diagnostic. |
| MOM_4W / MOM_4W_PERCENTILE (level) | DIAGNOSTIC ONLY | Little continuation/failure gap. |
| MOM4_CHANGE_4W, MOM12_CHANGE_4W, MOM12_PERCENTILE_CHANGE_4W | **KEEP** | Useful once conditioned on HIGH_MOM. |
| broad_breadth_4w / largecap lagged (level) | DIAGNOSTIC ONLY | Failures as high as continuations. |
| BROAD_BREADTH_CHANGE_4W | **KEEP** | 4w only; frozen ±5pp. |
| LARGECAP_BREADTH_CHANGE_4W | **KEEP** | Lagged twin of the above. |
| BREADTH_GAP_CHANGE_4W | DIAGNOSTIC ONLY | No median gap. |
| VOL_12W / VOL_PERCENTILE (level) | DIAGNOSTIC ONLY | Failures a bit higher vol pctl at 12w; already in V1 HIGH_VOL. |
| VOL_PERCENTILE_CHANGE_4W | DIAGNOSTIC ONLY | Sign opposite the pre-specified fragility story. Do not drop yet — the HIGH_MOM+falling-vol cell is sparse and odd. |
| TURNOVER_RELATIVE inside HIGH_MOM | **KEEP** | Cleaner 2-way; still not a trading cut. |
| TURNOVER_CHANGE_4W | DIAGNOSTIC ONLY | Noisy. |
| STABLECOIN_MCAP_12W_CHANGE | DIAGNOSTIC ONLY | 2020 vs 2021; not a general failure splitter. |
| STABLECOIN_GROWTH_CHANGE | DIAGNOSTIC ONLY | Same case-study role. |
| MARKET_DRAWDOWN_12W_HIGH | **DROP** | No variation among Bulls. |
| MARKET_DRAWDOWN_26W_HIGH | DROP | Same. |
| Candidate Healthy flag | DIAGNOSTIC ONLY | Did not beat generic Bull. |
| Candidate Fragile flag | **DROP** as specified | Contaminated by rising-vol OR. Rebuild later without that OR, without fitting. |

---

## WHAT REMAINS FOR MACRO TO EXPLAIN?

Reserved. No M2, Fed, DXY, yields, VIX, HY, Nasdaq, or financial conditions were used.

The live question for a later layer:

> Model A = crypto only vs Model B = crypto + macro. Does macro improve OOS discrimination of 4w/12w opportunity **and** of Bull continuation vs failure?

Especially: late-2020 continuation vs late-2021 failure, where V1 says `BULL_NORMAL_VOL` / BROAD, breadth is improving, the frozen Healthy flag is on, and crypto dynamics only offer SC12 + MOM12 acceleration as internal gaps — not a taxonomy that actually labels 2021 as fragile.

---

## WRAP-UP

The target concept is **health of the regime**, not level of the regime. In 2015–2023 that is only half-true:

- Level of MOM12 *does* contain information, but as **lateness**, not as health.
- Dynamics (MOM change, breadth change, turnover vs recent median) add something **inside already-high momentum**, mainly at 4w or in sparse cells.
- The first frozen Healthy/Fragile templates do not beat generic Bull and do not flag late-2021.

No score was optimized. No thresholds were moved after seeing results. 2024–2026 remains the final exam.
