# Opportunity episode analysis (Phase 3)

Sample: weekly crypto state through **2023-12-29**. Forward outcomes require a complete 4w or 12w path. **2024–2026 not used. Macro not used.**

Outcome percentiles and P90/P95 labels are **retrospective catalog tools**. They are not features and not trading rules.

Expanding `MOM_*_PERCENTILE` uses only MOM history through t.

Attribution contribution is **wealth-path linked**: at each future week s, `W_{s-1} * w_{i,s-1} * r_{i,s}`. These sum to the exact cumulative market return. Unlinked `sum(w*r)` is also stored; it equals the sum of weekly market returns, not the compound return. Identity gap is documented per episode.

Lagged large-cap: top 100 among eligible-at-t by **mcap t-1**. V1 contemporaneous column is retained.

---

## DESCRIPTIVE FINDINGS

### 1–3. Episode counts

Complete 4w weeks: **442**. Complete 12w weeks: **434**.

| label | ALL 4w | de-clustered 4w (cooldown 4) | ALL 12w | de-clustered 12w (cooldown 12) |
|---|---:|---:|---:|---:|
| TOP25 | 111 | 29 | 109 | 11 |
| TOP10 | 45 | 16 | 44 | 5 |
| TOP5 | 23 | 8 | 22 | 3 |
| BOTTOM25 | 110 | 31 | 108 | 13 |
| BOTTOM10 | 44 | 18 | 43 | 7 |
| BOTTOM5 | 22 | 8 | 21 | 6 |

De-clustering keeps the **first** week of a consecutive run, then enforces cooldown so overlapping windows are not counted as independent episodes. Unfavorable episodes are not dropped preferentially.

12w Extreme Opportunity threshold (historical P90 of complete 12w returns): 89.2%.

### 4. Ten best 12w episodes (ALL WEEKS)

- 2017-03-24 BULL_HIGH_VOL BROAD: 12w=340.5%, 4w=26.3%, MOM4=4.4% (pctl 0.416), MOM12=28.1% (pctl 0.630), broad=0.933, lc_lag=0.933, VOL pctl=0.716, TOVER_REL=3.014, SC12=351.6%
- 2017-03-31 BULL_HIGH_VOL BROAD: 12w=319.6%, 4w=32.4%, MOM4=4.1% (pctl 0.411), MOM12=49.2% (pctl 0.866), broad=0.946, lc_lag=0.946, VOL pctl=0.720, TOVER_REL=3.463, SC12=267.5%
- 2017-09-22 NEUTRAL_HIGH_VOL WEAK: 12w=313.0%, 4w=42.2%, MOM4=-18.1% (pctl 0.052), MOM12=13.2% (pctl 0.262), broad=0.324, lc_lag=0.320, VOL pctl=0.963, TOVER_REL=0.713, SC12=105.6%
- 2017-03-17 BULL_NORMAL_VOL BROAD: 12w=300.6%, 4w=11.8%, MOM4=24.9% (pctl 0.864), MOM12=45.1% (pctl 0.812), broad=0.875, lc_lag=0.875, VOL pctl=0.688, TOVER_REL=4.835, SC12=546.5%
- 2017-10-13 BULL_HIGH_VOL MIXED: 12w=295.5%, 4w=7.4%, MOM4=42.7% (pctl 0.881), MOM12=78.4% (pctl 0.855), broad=0.548, lc_lag=0.520, VOL pctl=0.900, TOVER_REL=1.153, SC12=37.2%
- 2017-03-10 NEUTRAL_NORMAL_VOL MIXED: 12w=294.3%, 4w=24.4%, MOM4=16.8% (pctl 0.805), MOM12=47.4% (pctl 0.835), broad=0.500, lc_lag=0.500, VOL pctl=0.696, TOVER_REL=2.790, SC12=402.7%
- 2017-10-06 NEUTRAL_HIGH_VOL WEAK: 12w=277.5%, 4w=34.7%, MOM4=1.0% (pctl 0.299), MOM12=70.6% (pctl 0.807), broad=0.361, lc_lag=0.370, VOL pctl=0.899, TOVER_REL=0.599, SC12=50.7%
- 2017-10-20 BULL_HIGH_VOL MIXED: 12w=253.7%, 4w=23.6%, MOM4=42.2% (pctl 0.874), MOM12=82.3% (pctl 0.856), broad=0.535, lc_lag=0.535, VOL pctl=0.892, TOVER_REL=1.022, SC12=36.7%
- 2017-09-15 BEAR_HIGH_VOL MIXED: 12w=248.5%, 4w=42.7%, MOM4=-10.2% (pctl 0.140), MOM12=-2.3% (pctl 0.142), broad=0.462, lc_lag=0.450, VOL pctl=0.981, TOVER_REL=1.061, SC12=205.7%
- 2017-04-07 BULL_NORMAL_VOL BROAD: 12w=242.3%, 4w=60.3%, MOM4=24.4% (pctl 0.857), MOM12=72.9% (pctl 0.964), broad=0.976, lc_lag=0.976, VOL pctl=0.663, TOVER_REL=1.295, SC12=267.5%

### 5. Ten worst 12w episodes (ALL WEEKS)

- 2018-01-05 BULL_HIGH_VOL BROAD: 12w=-67.4%, 4w=-46.8%, MOM4=61.9% (pctl 0.923), MOM12=295.5% (pctl 0.967), broad=0.916, lc_lag=0.940, VOL pctl=0.975, TOVER_REL=1.799, SC12=236.1%
- 2018-01-12 BULL_HIGH_VOL BROAD: 12w=-65.3%, 4w=-40.3%, MOM4=21.8% (pctl 0.695), MOM12=253.7% (pctl 0.943), broad=0.911, lc_lag=0.910, VOL pctl=1.000, TOVER_REL=1.015, SC12=238.3%
- 2022-04-08 NEUTRAL_NORMAL_VOL BROAD: 12w=-58.9%, 4w=-14.2%, MOM4=13.8% (pctl 0.636), MOM12=-9.6% (pctl 0.279), broad=0.777, lc_lag=0.900, VOL pctl=0.448, TOVER_REL=0.958, SC12=12.1%
- 2022-03-25 NEUTRAL_NORMAL_VOL BROAD: 12w=-58.6%, 4w=-8.2%, MOM4=12.0% (pctl 0.609), MOM12=-14.1% (pctl 0.246), broad=0.661, lc_lag=0.790, VOL pctl=0.433, TOVER_REL=1.150, SC12=14.5%
- 2022-04-01 BULL_NORMAL_VOL BROAD: 12w=-58.3%, 4w=-17.4%, MOM4=24.1% (pctl 0.769), MOM12=4.5% (pctl 0.397), broad=0.809, lc_lag=0.960, VOL pctl=0.397, TOVER_REL=1.134, SC12=16.6%
- 2018-09-21 NEUTRAL_NORMAL_VOL MIXED: 12w=-56.7%, 4w=-8.5%, MOM4=3.9% (pctl 0.437), MOM12=-10.2% (pctl 0.182), broad=0.467, lc_lag=0.440, VOL pctl=0.528, TOVER_REL=1.491, SC12=3.6%
- 2022-04-22 NEUTRAL_NORMAL_VOL WEAK: 12w=-52.1%, 4w=-32.7%, MOM4=-8.2% (pctl 0.260), MOM12=6.0% (pctl 0.402), broad=0.305, lc_lag=0.270, VOL pctl=0.208, TOVER_REL=0.954, SC12=8.4%
- 2022-04-15 BULL_NORMAL_VOL MIXED: 12w=-52.0%, 4w=-33.4%, MOM4=0.3% (pctl 0.385), MOM12=7.8% (pctl 0.420), broad=0.579, lc_lag=0.520, VOL pctl=0.200, TOVER_REL=0.756, SC12=12.8%
- 2018-09-14 BEAR_NORMAL_VOL WEAK: 12w=-48.0%, 4w=-0.6%, MOM4=-10.6% (pctl 0.229), MOM12=-22.5% (pctl 0.120), broad=0.219, lc_lag=0.150, VOL pctl=0.411, TOVER_REL=1.085, SC12=6.9%
- 2018-11-09 NEUTRAL_NORMAL_VOL BROAD: 12w=-47.9%, 4w=-50.2%, MOM4=5.2% (pctl 0.483), MOM12=-6.6% (pctl 0.241), broad=0.640, lc_lag=0.640, VOL pctl=0.235, TOVER_REL=0.916, SC12=-18.7%

### 6–7. Who produced extreme 12w moves?

Wealth-linked group contributions for the ten best:

- **2017-03-24** market 12w=340.5% (identity gap -0.000000); BTC: contrib=112.0% (32.9% of cum), start_w=0.674; ETH: contrib=125.4% (36.8% of cum), start_w=0.212; TOP10_BY_START_WEIGHT: contrib=304.8% (89.5% of cum), start_w=0.978; LARGECAP_LAGGED: contrib=327.1% (96.1% of cum), start_w=0.997; REST_EX_BTC_ETH: contrib=103.0% (30.3% of cum), start_w=0.115; top contributors: ETH 125.4%, BTC 112.0%, XRP 41.5%, LTC 7.0%, XEM 7.0%
- **2017-03-31** market 12w=319.6% (identity gap -0.000000); BTC: contrib=106.3% (33.3% of cum), start_w=0.691; ETH: contrib=103.8% (32.5% of cum), start_w=0.179; TOP10_BY_START_WEIGHT: contrib=281.9% (88.2% of cum), start_w=0.971; LARGECAP_LAGGED: contrib=309.6% (96.9% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=109.5% (34.3% of cum), start_w=0.130; top contributors: BTC 106.3%, ETH 103.8%, XRP 44.3%, LTC 8.1%, ETC 6.6%
- **2017-09-22** market 12w=313.0% (identity gap -0.000000); BTC: contrib=208.4% (66.6% of cum), start_w=0.545; ETH: contrib=35.7% (11.4% of cum), start_w=0.227; TOP10_BY_START_WEIGHT: contrib=290.6% (92.8% of cum), start_w=0.933; LARGECAP_LAGGED: contrib=302.9% (96.8% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=68.9% (22.0% of cum), start_w=0.228; top contributors: BTC 208.4%, ETH 35.7%, XRP 19.8%, LTC 12.0%, MIOTA 6.0%
- **2017-03-17** market 12w=300.6% (identity gap -0.000000); BTC: contrib=112.6% (37.5% of cum), start_w=0.734; ETH: contrib=86.0% (28.6% of cum), start_w=0.173; TOP10_BY_START_WEIGHT: contrib=264.9% (88.1% of cum), start_w=0.985; LARGECAP_LAGGED: contrib=280.6% (93.3% of cum), start_w=0.996; REST_EX_BTC_ETH: contrib=102.0% (33.9% of cum), start_w=0.093; top contributors: BTC 112.6%, ETH 86.0%, XRP 42.7%, XEM 7.4%, ETC 5.7%
- **2017-10-13** market 12w=295.5% (identity gap -0.000000); BTC: contrib=122.2% (41.4% of cum), start_w=0.598; ETH: contrib=38.9% (13.2% of cum), start_w=0.205; TOP10_BY_START_WEIGHT: contrib=252.4% (85.4% of cum), start_w=0.949; LARGECAP_LAGGED: contrib=278.3% (94.2% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=134.3% (45.5% of cum), start_w=0.197; top contributors: BTC 122.2%, XRP 65.7%, ETH 38.9%, XEM 7.6%, XLM 7.0%
- **2017-03-10** market 12w=294.3% (identity gap -0.000000); BTC: contrib=101.9% (34.6% of cum), start_w=0.849; ETH: contrib=85.2% (28.9% of cum), start_w=0.081; TOP10_BY_START_WEIGHT: contrib=266.8% (90.7% of cum), start_w=0.991; LARGECAP_LAGGED: contrib=276.3% (93.9% of cum), start_w=0.999; REST_EX_BTC_ETH: contrib=107.2% (36.4% of cum), start_w=0.070; top contributors: BTC 101.9%, ETH 85.2%, XRP 51.5%, XEM 9.0%, ETC 6.7%
- **2017-10-06** market 12w=277.5% (identity gap 0.000000); BTC: contrib=128.5% (46.3% of cum), start_w=0.552; ETH: contrib=31.7% (11.4% of cum), start_w=0.223; TOP10_BY_START_WEIGHT: contrib=242.2% (87.3% of cum), start_w=0.937; LARGECAP_LAGGED: contrib=264.0% (95.1% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=117.3% (42.3% of cum), start_w=0.225; top contributors: BTC 128.5%, XRP 55.9%, ETH 31.7%, LTC 7.8%, XEM 5.6%
- **2017-10-20** market 12w=253.7% (identity gap -0.000000); BTC: contrib=83.4% (32.9% of cum), start_w=0.634; ETH: contrib=56.8% (22.4% of cum), start_w=0.184; TOP10_BY_START_WEIGHT: contrib=208.6% (82.2% of cum), start_w=0.950; LARGECAP_LAGGED: contrib=235.3% (92.7% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=113.5% (44.7% of cum), start_w=0.183; top contributors: BTC 83.4%, ETH 56.8%, XRP 43.4%, XLM 7.0%, XEM 6.7%
- **2017-09-15** market 12w=248.5% (identity gap -0.000000); BTC: contrib=193.0% (77.7% of cum), start_w=0.551; ETH: contrib=17.8% (7.2% of cum), start_w=0.217; TOP10_BY_START_WEIGHT: contrib=229.9% (92.5% of cum), start_w=0.929; LARGECAP_LAGGED: contrib=237.7% (95.6% of cum), start_w=0.998; REST_EX_BTC_ETH: contrib=37.8% (15.2% of cum), start_w=0.233; top contributors: BTC 193.0%, ETH 17.8%, MIOTA 8.7%, LTC 3.7%, XEM 3.4%
- **2017-04-07** market 12w=242.3% (identity gap -0.000000); BTC: contrib=77.8% (32.1% of cum), start_w=0.713; ETH: contrib=84.5% (34.9% of cum), start_w=0.142; TOP10_BY_START_WEIGHT: contrib=215.4% (88.9% of cum), start_w=0.973; LARGECAP_LAGGED: contrib=233.9% (96.6% of cum), start_w=0.999; REST_EX_BTC_ETH: contrib=79.9% (33.0% of cum), start_w=0.145; top contributors: ETH 84.5%, BTC 77.8%, XRP 31.6%, LTC 5.8%, ETC 5.4%

Ten worst:

- **2018-01-05** market 12w=-67.4% (identity gap 0.000000); BTC: contrib=-25.2% (37.4% of cum), start_w=0.443; ETH: contrib=-7.7% (11.5% of cum), start_w=0.146; TOP10_BY_START_WEIGHT: contrib=-53.7% (79.7% of cum), start_w=0.878; LARGECAP_LAGGED: contrib=-61.0% (90.6% of cum), start_w=0.984; REST_EX_BTC_ETH: contrib=-34.5% (51.1% of cum), start_w=0.410; top contributors: JNS 0.1%, ECN 0.0%, DGD 0.0%, BTM 0.0%, KLC 0.0%
- **2018-01-12** market 12w=-65.3% (identity gap 0.000000); BTC: contrib=-18.9% (29.0% of cum), start_w=0.367; ETH: contrib=-13.5% (20.6% of cum), start_w=0.193; TOP10_BY_START_WEIGHT: contrib=-54.0% (82.7% of cum), start_w=0.855; LARGECAP_LAGGED: contrib=-58.0% (88.8% of cum), start_w=0.913; REST_EX_BTC_ETH: contrib=-32.9% (50.4% of cum), start_w=0.440; top contributors: ECN 0.0%, BTM 0.0%, DGD 0.0%, KLC 0.0%, UNY 0.0%
- **2022-04-08** market 12w=-58.9% (identity gap 0.000000); BTC: contrib=-24.1% (41.0% of cum), start_w=0.436; ETH: contrib=-14.2% (24.1% of cum), start_w=0.208; TOP10_BY_START_WEIGHT: contrib=-48.2% (81.8% of cum), start_w=0.794; LARGECAP_LAGGED: contrib=-58.3% (98.9% of cum), start_w=0.951; REST_EX_BTC_ETH: contrib=-20.6% (35.0% of cum), start_w=0.355; top contributors: ION 2.3%, YOUC 0.2%, TRX 0.0%, FRTS 0.0%, PLTC 0.0%
- **2022-03-25** market 12w=-58.6% (identity gap 0.000000); BTC: contrib=-24.5% (41.8% of cum), start_w=0.449; ETH: contrib=-13.2% (22.5% of cum), start_w=0.199; TOP10_BY_START_WEIGHT: contrib=-47.4% (81.0% of cum), start_w=0.794; LARGECAP_LAGGED: contrib=-57.8% (98.7% of cum), start_w=0.953; REST_EX_BTC_ETH: contrib=-20.9% (35.7% of cum), start_w=0.353; top contributors: ION 2.3%, YOUC 0.2%, SAFE 0.0%, COT 0.0%, BNX 0.0%
- **2022-04-01** market 12w=-58.3% (identity gap 0.000000); BTC: contrib=-23.7% (40.7% of cum), start_w=0.432; ETH: contrib=-13.4% (22.9% of cum), start_w=0.204; TOP10_BY_START_WEIGHT: contrib=-47.0% (80.6% of cum), start_w=0.788; LARGECAP_LAGGED: contrib=-57.0% (97.8% of cum), start_w=0.949; REST_EX_BTC_ETH: contrib=-21.2% (36.4% of cum), start_w=0.364; top contributors: ION 2.1%, YOUC 0.2%, TITAN 0.0%, FRTS 0.0%, BNX 0.0%
- **2018-09-21** market 12w=-56.7% (identity gap 0.000000); BTC: contrib=-27.5% (48.6% of cum), start_w=0.532; ETH: contrib=-7.6% (13.4% of cum), start_w=0.115; TOP10_BY_START_WEIGHT: contrib=-49.4% (87.1% of cum), start_w=0.880; LARGECAP_LAGGED: contrib=-56.0% (98.7% of cum), start_w=0.982; REST_EX_BTC_ETH: contrib=-21.6% (38.0% of cum), start_w=0.353; top contributors: MGO 0.0%, FCT 0.0%, VRS 0.0%, SWM 0.0%, PRL 0.0%
- **2022-04-22** market 12w=-52.1% (identity gap 0.000000); BTC: contrib=-21.2% (40.7% of cum), start_w=0.436; ETH: contrib=-12.3% (23.6% of cum), start_w=0.206; TOP10_BY_START_WEIGHT: contrib=-42.6% (81.8% of cum), start_w=0.790; LARGECAP_LAGGED: contrib=-52.0% (99.7% of cum), start_w=0.951; REST_EX_BTC_ETH: contrib=-18.6% (35.7% of cum), start_w=0.359; top contributors: ION 2.5%, YOUC 0.2%, FRTS 0.0%, TRX 0.0%, BTT 0.0%
- **2022-04-15** market 12w=-52.0% (identity gap 0.000000); BTC: contrib=-20.6% (39.7% of cum), start_w=0.436; ETH: contrib=-12.6% (24.3% of cum), start_w=0.207; TOP10_BY_START_WEIGHT: contrib=-42.4% (81.4% of cum), start_w=0.793; LARGECAP_LAGGED: contrib=-51.8% (99.5% of cum), start_w=0.952; REST_EX_BTC_ETH: contrib=-18.8% (36.1% of cum), start_w=0.357; top contributors: ION 2.4%, YOUC 0.2%, TRX 0.0%, FRTS 0.0%, BTT 0.0%
- **2018-09-14** market 12w=-48.0% (identity gap 0.000000); BTC: contrib=-27.5% (57.2% of cum), start_w=0.579; ETH: contrib=-6.2% (13.0% of cum), start_w=0.111; TOP10_BY_START_WEIGHT: contrib=-41.3% (86.0% of cum), start_w=0.876; LARGECAP_LAGGED: contrib=-47.4% (98.7% of cum), start_w=0.981; REST_EX_BTC_ETH: contrib=-14.3% (29.8% of cum), start_w=0.309; top contributors: XRP 0.5%, FCT 0.0%, MGO 0.0%, ODE 0.0%, SLT 0.0%
- **2018-11-09** market 12w=-47.9% (identity gap 0.000000); BTC: contrib=-24.6% (51.4% of cum), start_w=0.542; ETH: contrib=-5.2% (10.8% of cum), start_w=0.106; TOP10_BY_START_WEIGHT: contrib=-41.6% (86.9% of cum), start_w=0.880; LARGECAP_LAGGED: contrib=-47.1% (98.4% of cum), start_w=0.980; REST_EX_BTC_ETH: contrib=-18.1% (37.8% of cum), start_w=0.353; top contributors: TRX 0.1%, WAVES 0.0%, REPO 0.0%, PPP 0.0%, HOT 0.0%

Lagged vs V1 large-cap breadth (all weeks with both finite): N=445, median |Δ|=0.0100, max |Δ|=0.0600, share differing by >5pp=0.4%.

### 8–13. What did extremes look like *before* they happened?

TOP10 vs rest (12w complete):

| feature | TOP10_12w N/mean/median/p25/p75 | rest N/mean/median/p25/p75 |
|---|---|---|
| MOM_4W | 44 / 0.1804 / 0.1936 / 0.0668 / 0.2994 | 386 / 0.0600 / 0.0199 / -0.1046 / 0.1695 |
| MOM_12W | 44 / 0.4890 / 0.4371 / 0.2251 / 0.6633 | 378 / 0.2389 / 0.0412 / -0.1715 / 0.4063 |
| MOM_4W_PERCENTILE | 44 / 0.6718 / 0.7773 / 0.4856 / 0.8662 | 386 / 0.4696 / 0.4433 / 0.2158 / 0.7308 |
| MOM_12W_PERCENTILE | 44 / 0.6884 / 0.7246 / 0.5269 / 0.8702 | 378 / 0.4514 / 0.4050 / 0.1902 / 0.7215 |
| broad_breadth_4w | 44 / 0.6055 / 0.5607 / 0.4443 / 0.7661 | 389 / 0.4742 / 0.4360 / 0.2184 / 0.7610 |
| largecap_breadth_4w | 44 / 0.6362 / 0.5779 / 0.4850 / 0.8325 | 389 / 0.4863 / 0.4400 / 0.2000 / 0.8000 |
| largecap_breadth_4w_lagged | 44 / 0.6243 / 0.5779 / 0.4800 / 0.8025 | 389 / 0.4782 / 0.4300 / 0.2000 / 0.7900 |
| breadth_gap | 44 / 0.0306 / 0.0244 / 0.0000 / 0.0542 | 389 / 0.0121 / 0.0000 / -0.0176 / 0.0415 |
| breadth_gap_lagged | 44 / 0.0188 / 0.0038 / -0.0000 / 0.0328 | 389 / 0.0039 / 0.0000 / -0.0242 / 0.0308 |
| median_coin_return_4w | 44 / 0.1281 / 0.0453 / -0.0325 / 0.1398 | 389 / 0.0329 / -0.0267 / -0.1479 / 0.1361 |
| largecap_median_return_4w | 44 / 0.1472 / 0.0559 / -0.0094 / 0.1906 | 389 / 0.0428 / -0.0179 / -0.1416 / 0.1482 |
| largecap_median_return_4w_lagged | 44 / 0.1377 / 0.0500 / -0.0165 / 0.1794 | 389 / 0.0357 / -0.0217 / -0.1450 / 0.1436 |
| n_eligible_coins | 44 / 218.1818 / 177.0000 / 46.0000 / 385.7500 | 390 / 378.7231 / 285.0000 / 106.0000 / 702.0000 |
| VOL_12W | 44 / 0.0880 / 0.0812 / 0.0644 / 0.1196 | 378 / 0.0941 / 0.0913 / 0.0703 / 0.1202 |
| VOL_PERCENTILE | 44 / 0.5396 / 0.5785 / 0.2408 / 0.8190 | 378 / 0.5371 / 0.5023 / 0.2921 / 0.8127 |
| market_turnover | 44 / 0.0286 / 0.0318 / 0.0135 / 0.0404 | 389 / 0.0331 / 0.0333 / 0.0141 / 0.0481 |
| TURNOVER_RELATIVE | 44 / 1.2898 / 1.0636 / 0.8695 / 1.3067 | 378 / 1.1054 / 1.0009 / 0.8718 / 1.1943 |
| TURNOVER_PERCENTILE | 44 / 0.7787 / 0.7641 / 0.7120 / 0.8775 | 389 / 0.7543 / 0.7910 / 0.6250 / 0.9200 |
| STABLECOIN_MCAP | 44 / 10116704407.1820 / 1670189223.3527 / 57286442.7801 / 22134218619.5293 | 390 / 49858158579.4597 / 5118231702.3964 / 318902234.1707 / 125056689912.0302 |
| STABLECOIN_MCAP_4W_CHANGE | 44 / 0.2429 / 0.1261 / 0.0303 / 0.3652 | 390 / 0.1367 / 0.0254 / -0.0022 / 0.1424 |
| STABLECOIN_MCAP_12W_CHANGE | 44 / 1.2463 / 0.7800 / 0.3712 / 2.1442 | 390 / 0.5273 / 0.1727 / -0.0146 / 0.7159 |
| STABLECOIN_LIQ_PERCENTILE | 44 / 0.9853 / 1.0000 / 0.9855 / 1.0000 | 390 / 0.9401 / 0.9947 / 0.9128 / 1.0000 |

BOTTOM10 vs rest (12w complete):

| feature | BOTTOM10_12w N/mean/median/p25/p75 | rest N/mean/median/p25/p75 |
|---|---|---|
| MOM_4W | 43 / 0.1287 / 0.0567 / -0.0727 / 0.1908 | 387 / 0.0661 / 0.0309 / -0.0981 / 0.1972 |
| MOM_12W | 43 / 0.4380 / -0.0520 / -0.1945 / 0.7847 | 379 / 0.2453 / 0.1313 / -0.1358 / 0.4436 |
| MOM_4W_PERCENTILE | 43 / 0.4896 / 0.4828 / 0.2586 / 0.6990 | 387 / 0.4904 / 0.4722 / 0.2220 / 0.7658 |
| MOM_12W_PERCENTILE | 43 / 0.4289 / 0.2545 / 0.1391 / 0.8287 | 379 / 0.4814 / 0.4590 / 0.2287 / 0.7493 |
| broad_breadth_4w | 43 / 0.5244 / 0.5000 / 0.2492 / 0.7927 | 390 / 0.4835 / 0.4446 / 0.2328 / 0.7609 |
| largecap_breadth_4w | 43 / 0.5514 / 0.6400 / 0.2450 / 0.8650 | 390 / 0.4961 / 0.4700 / 0.2342 / 0.8000 |
| largecap_breadth_4w_lagged | 43 / 0.5398 / 0.6400 / 0.2300 / 0.8500 | 390 / 0.4879 / 0.4550 / 0.2200 / 0.7975 |
| breadth_gap | 43 / 0.0270 / 0.0000 / -0.0286 / 0.0608 | 390 / 0.0125 / 0.0000 / -0.0054 / 0.0422 |
| breadth_gap_lagged | 43 / 0.0154 / 0.0000 / -0.0438 / 0.0467 | 390 / 0.0043 / 0.0000 / -0.0191 / 0.0275 |
| median_coin_return_4w | 43 / 0.1690 / 0.0004 / -0.1435 / 0.2352 | 390 / 0.0286 / -0.0193 / -0.1381 / 0.1344 |
| largecap_median_return_4w | 43 / 0.1883 / 0.0313 / -0.1083 / 0.2657 | 390 / 0.0385 / -0.0116 / -0.1332 / 0.1465 |
| largecap_median_return_4w_lagged | 43 / 0.1724 / 0.0303 / -0.1119 / 0.2514 | 390 / 0.0321 / -0.0143 / -0.1385 / 0.1434 |
| n_eligible_coins | 43 / 516.2791 / 303.0000 / 283.0000 / 827.0000 | 391 / 345.5294 / 268.0000 / 51.0000 / 676.0000 |
| VOL_12W | 43 / 0.1061 / 0.0960 / 0.0832 / 0.1365 | 379 / 0.0920 / 0.0884 / 0.0683 / 0.1156 |
| VOL_PERCENTILE | 43 / 0.5699 / 0.4477 / 0.3639 / 0.8710 | 379 / 0.5337 / 0.5089 / 0.2774 / 0.8115 |
| market_turnover | 43 / 0.0303 / 0.0298 / 0.0182 / 0.0416 | 390 / 0.0329 / 0.0333 / 0.0132 / 0.0482 |
| TURNOVER_RELATIVE | 43 / 1.0825 / 0.9864 / 0.8851 / 1.0748 | 379 / 1.1294 / 1.0158 / 0.8686 / 1.2210 |
| TURNOVER_PERCENTILE | 43 / 0.7638 / 0.7558 / 0.6880 / 0.8412 | 390 / 0.7560 / 0.7975 / 0.6139 / 0.9232 |
| STABLECOIN_MCAP | 43 / 60052360246.7856 / 2952455378.4109 / 2339787833.7632 / 132433846113.4129 | 391 / 44264873016.0959 / 5089377484.0191 / 58848776.5405 / 122043699952.6098 |
| STABLECOIN_MCAP_4W_CHANGE | 43 / 0.1300 / 0.0430 / 0.0070 / 0.2129 | 391 / 0.1494 / 0.0295 / -0.0020 / 0.1634 |
| STABLECOIN_MCAP_12W_CHANGE | 43 / 0.5135 / 0.1450 / 0.0672 / 1.0250 | 391 / 0.6097 / 0.2315 / -0.0109 / 0.8099 |
| STABLECOIN_LIQ_PERCENTILE | 43 / 0.9810 / 1.0000 / 0.9948 / 1.0000 | 391 / 0.9407 / 0.9925 / 0.9173 / 1.0000 |

TOP5 vs rest and BOTTOM5 vs rest are in the catalog flags; distributions follow the same pattern as TOP10/BOTTOM10 at a smaller N.

### 14. Bull continuation vs Bull failure

Bull weeks with complete 4w: continuation N=106, failure N=45.  
Bull weeks with complete 12w: continuation N=105, failure N=40.

4w:

| feature | BULL_CONT_4W N/mean/median/p25/p75 | BULL_FAIL_4W N/mean/median/p25/p75 |
|---|---|---|
| MOM_4W | 106 / 0.2945 / 0.2412 / 0.1199 / 0.3367 | 45 / 0.3081 / 0.2464 / 0.1606 / 0.3775 |
| MOM_12W | 106 / 0.6918 / 0.4181 / 0.2363 / 0.9419 | 45 / 0.8347 / 0.4833 / 0.2886 / 0.8488 |
| MOM_4W_PERCENTILE | 106 / 0.7574 / 0.8159 / 0.6257 / 0.8957 | 45 / 0.7792 / 0.8333 / 0.6947 / 0.9231 |
| MOM_12W_PERCENTILE | 106 / 0.7213 / 0.7492 / 0.5363 / 0.9085 | 45 / 0.7278 / 0.7290 / 0.5923 / 0.8990 |
| broad_breadth_4w | 106 / 0.7764 / 0.7919 / 0.7000 / 0.9000 | 45 / 0.8212 / 0.8333 / 0.7704 / 0.9167 |
| largecap_breadth_4w | 106 / 0.8048 / 0.8450 / 0.7000 / 0.9355 | 45 / 0.8608 / 0.8900 / 0.8000 / 0.9600 |
| largecap_breadth_4w_lagged | 106 / 0.7965 / 0.8300 / 0.7000 / 0.9275 | 45 / 0.8499 / 0.8700 / 0.8000 / 0.9500 |
| breadth_gap | 106 / 0.0284 / 0.0131 / 0.0000 / 0.0538 | 45 / 0.0396 / 0.0110 / 0.0000 / 0.0820 |
| breadth_gap_lagged | 106 / 0.0201 / 0.0000 / 0.0000 / 0.0438 | 45 / 0.0287 / 0.0000 / 0.0000 / 0.0700 |
| median_coin_return_4w | 106 / 0.3033 / 0.1619 / 0.0877 / 0.3907 | 45 / 0.3904 / 0.2415 / 0.1282 / 0.4040 |
| largecap_median_return_4w | 106 / 0.3100 / 0.1801 / 0.0862 / 0.4110 | 45 / 0.4141 / 0.2726 / 0.1631 / 0.4095 |
| largecap_median_return_4w_lagged | 106 / 0.2984 / 0.1745 / 0.0769 / 0.3798 | 45 / 0.3970 / 0.2726 / 0.1436 / 0.4095 |
| n_eligible_coins | 106 / 307.0283 / 267.0000 / 38.0000 / 464.7500 | 45 / 360.7556 / 295.0000 / 19.0000 / 747.0000 |
| VOL_12W | 106 / 0.0893 / 0.0827 / 0.0625 / 0.1168 | 45 / 0.0921 / 0.0902 / 0.0687 / 0.1035 |
| VOL_PERCENTILE | 106 / 0.5410 / 0.5605 / 0.2831 / 0.8394 | 45 / 0.5800 / 0.6058 / 0.2747 / 0.9130 |
| market_turnover | 106 / 0.0351 / 0.0370 / 0.0136 / 0.0502 | 45 / 0.0339 / 0.0311 / 0.0152 / 0.0478 |
| TURNOVER_RELATIVE | 106 / 1.2964 / 1.1295 / 0.9748 / 1.4195 | 45 / 1.3142 / 1.0883 / 0.9594 / 1.2746 |
| TURNOVER_PERCENTILE | 106 / 0.8116 / 0.8269 / 0.7163 / 0.9482 | 45 / 0.8197 / 0.8209 / 0.7387 / 0.9234 |
| STABLECOIN_MCAP | 106 / 28493518348.9178 / 2828984354.7744 / 51488134.2823 / 35791674156.6152 | 45 / 41181754115.1989 / 2307262742.9872 / 9951743.9431 / 118775528715.9009 |
| STABLECOIN_MCAP_4W_CHANGE | 106 / 0.2176 / 0.1126 / 0.0058 / 0.3135 | 45 / 0.3726 / 0.0679 / 0.0077 / 0.7737 |
| STABLECOIN_MCAP_12W_CHANGE | 106 / 0.8909 / 0.5362 / 0.1193 / 1.1487 | 45 / 0.9449 / 0.2279 / 0.1045 / 1.8381 |
| STABLECOIN_LIQ_PERCENTILE | 106 / 0.9527 / 1.0000 / 0.9668 / 1.0000 | 45 / 0.9659 / 0.9972 / 0.9804 / 1.0000 |

12w:

| feature | BULL_CONT_12W N/mean/median/p25/p75 | BULL_FAIL_12W N/mean/median/p25/p75 |
|---|---|---|
| MOM_4W | 105 / 0.2910 / 0.2503 / 0.1107 / 0.3728 | 40 / 0.3305 / 0.2362 / 0.1551 / 0.3398 |
| MOM_12W | 105 / 0.6367 / 0.4037 / 0.2530 / 0.7382 | 40 / 1.0568 / 0.8050 / 0.3213 / 1.6571 |
| MOM_4W_PERCENTILE | 105 / 0.7695 / 0.8415 / 0.6186 / 0.9056 | 40 / 0.7495 / 0.7611 / 0.6408 / 0.8638 |
| MOM_12W_PERCENTILE | 105 / 0.7123 / 0.7115 / 0.5673 / 0.9094 | 40 / 0.7636 / 0.8588 / 0.5952 / 0.9103 |
| broad_breadth_4w | 105 / 0.7853 / 0.7964 / 0.7000 / 0.9032 | 40 / 0.7918 / 0.8153 / 0.7286 / 0.8867 |
| largecap_breadth_4w | 105 / 0.8115 / 0.8400 / 0.7000 / 0.9400 | 40 / 0.8317 / 0.8550 / 0.7800 / 0.9300 |
| largecap_breadth_4w_lagged | 105 / 0.8041 / 0.8200 / 0.7000 / 0.9302 | 40 / 0.8187 / 0.8450 / 0.7675 / 0.9300 |
| breadth_gap | 105 / 0.0262 / 0.0000 / 0.0000 / 0.0485 | 40 / 0.0399 / 0.0322 / 0.0000 / 0.0828 |
| breadth_gap_lagged | 105 / 0.0188 / 0.0000 / 0.0000 / 0.0396 | 40 / 0.0269 / 0.0230 / -0.0010 / 0.0723 |
| median_coin_return_4w | 105 / 0.2989 / 0.1610 / 0.0908 / 0.3621 | 40 / 0.4283 / 0.2682 / 0.1275 / 0.5613 |
| largecap_median_return_4w | 105 / 0.3136 / 0.1816 / 0.0934 / 0.4002 | 40 / 0.4290 / 0.2785 / 0.1619 / 0.4255 |
| largecap_median_return_4w_lagged | 105 / 0.3040 / 0.1786 / 0.0850 / 0.3747 | 40 / 0.4052 / 0.2752 / 0.1384 / 0.4146 |
| n_eligible_coins | 105 / 237.4667 / 124.0000 / 19.0000 / 397.0000 | 40 / 483.6250 / 312.0000 / 267.2500 / 780.5000 |
| VOL_12W | 105 / 0.0860 / 0.0813 / 0.0617 / 0.1061 | 40 / 0.1063 / 0.0979 / 0.0809 / 0.1346 |
| VOL_PERCENTILE | 105 / 0.5560 / 0.5769 / 0.2905 / 0.8445 | 40 / 0.6082 / 0.6918 / 0.3442 / 0.9012 |
| market_turnover | 105 / 0.0314 / 0.0259 / 0.0128 / 0.0483 | 40 / 0.0423 / 0.0436 / 0.0300 / 0.0557 |
| TURNOVER_RELATIVE | 105 / 1.3084 / 1.1075 / 0.9742 / 1.3902 | 40 / 1.2723 / 1.0937 / 0.9155 / 1.3677 |
| TURNOVER_PERCENTILE | 105 / 0.8110 / 0.8246 / 0.7314 / 0.9314 | 40 / 0.8447 / 0.8710 / 0.7308 / 0.9645 |
| STABLECOIN_MCAP | 105 / 20150602430.6556 / 437712071.3891 / 14951697.7673 / 23153739142.9129 | 40 / 50061140876.3096 / 5680187610.7905 / 1478043770.5485 / 88454584973.8396 |
| STABLECOIN_MCAP_4W_CHANGE | 105 / 0.2468 / 0.1016 / 0.0000 / 0.3488 | 40 / 0.3455 / 0.1741 / 0.0321 / 0.4374 |
| STABLECOIN_MCAP_12W_CHANGE | 105 / 0.9200 / 0.5157 / 0.1868 / 1.3271 | 40 / 1.0071 / 0.7317 / 0.1262 / 1.4091 |
| STABLECOIN_LIQ_PERCENTILE | 105 / 0.9542 / 0.9971 / 0.9667 / 1.0000 | 40 / 0.9879 / 1.0000 / 0.9972 / 1.0000 |

### 15. Monotonicity (frozen buckets)

MOM_4W_PERCENTILE:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <40 | 184 | 49.5% | -0.7% | -11.1% | 15.5% | 29.9% | 29.3% | -8.8% | 183 | 49.2% | -0.7% | -18.8% | 33.2% | 40.4% | 38.8% | -21.3% |
| 40-70 | 114 | 64.9% | 5.8% | -6.8% | 23.4% | 41.2% | 19.3% | -4.3% | 111 | 65.8% | 20.2% | -9.5% | 50.8% | 58.6% | 25.2% | -15.5% |
| 70-90 | 99 | 66.7% | 9.2% | -4.8% | 24.7% | 48.5% | 16.2% | -7.5% | 96 | 69.8% | 20.2% | -5.7% | 74.6% | 58.3% | 24.0% | -17.6% |
| >=90 | 41 | 63.4% | 4.4% | -11.5% | 32.9% | 41.5% | 26.8% | -10.9% | 40 | 72.5% | 31.1% | -3.3% | 70.1% | 65.0% | 20.0% | -26.2% |

MOM_12W_PERCENTILE:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <40 | 188 | 47.9% | -1.0% | -11.2% | 13.1% | 27.7% | 29.3% | -8.6% | 186 | 46.8% | -3.3% | -20.0% | 31.6% | 39.8% | 44.1% | -21.8% |
| 40-70 | 118 | 69.5% | 6.5% | -4.0% | 20.1% | 40.7% | 16.1% | -4.4% | 115 | 79.1% | 24.8% | 5.4% | 66.6% | 69.6% | 16.5% | -12.7% |
| 70-90 | 79 | 63.3% | 10.3% | -8.5% | 23.5% | 50.6% | 21.5% | -9.9% | 76 | 55.3% | 2.0% | -11.2% | 49.7% | 42.1% | 26.3% | -22.3% |
| >=90 | 45 | 73.3% | 21.7% | -1.0% | 50.7% | 60.0% | 20.0% | -10.3% | 45 | 75.6% | 37.4% | 0.8% | 83.5% | 66.7% | 15.6% | -29.9% |

Broad breadth:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <40% | 189 | 55.0% | 1.7% | -8.8% | 16.6% | 32.3% | 22.8% | -7.5% | 188 | 51.6% | 3.4% | -17.8% | 39.5% | 43.6% | 37.2% | -20.7% |
| 40-50% | 44 | 56.8% | 6.7% | -10.9% | 20.0% | 43.2% | 29.5% | -5.9% | 43 | 58.1% | 17.2% | -24.2% | 52.1% | 53.5% | 37.2% | -18.7% |
| 50-60% | 36 | 63.9% | 5.2% | -12.6% | 16.9% | 36.1% | 30.6% | -7.8% | 36 | 69.4% | 23.4% | -3.7% | 113.4% | 61.1% | 13.9% | -13.7% |
| 60-70% | 32 | 53.1% | 2.0% | -10.3% | 20.8% | 34.4% | 25.0% | -4.7% | 32 | 62.5% | 19.9% | -11.8% | 52.4% | 53.1% | 28.1% | -18.7% |
| 70-80% | 44 | 72.7% | 10.6% | -2.9% | 25.3% | 50.0% | 9.1% | -6.7% | 43 | 72.1% | 20.8% | -7.0% | 77.1% | 65.1% | 23.3% | -18.0% |
| >=80% | 96 | 60.4% | 6.0% | -9.6% | 21.8% | 43.8% | 25.0% | -8.3% | 91 | 67.0% | 12.7% | -7.2% | 46.6% | 53.8% | 24.2% | -21.2% |

VOL_PERCENTILE:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <40 | 173 | 62.4% | 5.3% | -6.6% | 20.2% | 38.2% | 20.8% | -4.5% | 165 | 67.3% | 22.5% | -11.9% | 48.6% | 60.0% | 27.3% | -14.0% |
| 40-70 | 114 | 56.1% | 2.0% | -7.9% | 14.7% | 33.3% | 20.2% | -9.9% | 114 | 42.1% | -5.2% | -19.8% | 22.1% | 30.7% | 41.2% | -22.3% |
| 70-90 | 72 | 56.9% | 6.2% | -10.1% | 24.9% | 47.2% | 25.0% | -8.8% | 72 | 66.7% | 26.4% | -5.2% | 53.2% | 59.7% | 22.2% | -18.2% |
| >=90 | 71 | 59.2% | 7.3% | -12.0% | 23.6% | 40.8% | 32.4% | -6.2% | 71 | 66.2% | 15.6% | -17.9% | 50.6% | 54.9% | 28.2% | -29.9% |

TURNOVER_RELATIVE:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <0.75 | 44 | 65.9% | 4.5% | -7.1% | 25.9% | 40.9% | 18.2% | -6.8% | 44 | 65.9% | 28.2% | -7.9% | 65.7% | 56.8% | 22.7% | -15.7% |
| 0.75-1.0 | 160 | 53.8% | 1.6% | -10.5% | 16.3% | 31.9% | 27.5% | -7.0% | 159 | 56.6% | 8.2% | -18.3% | 40.4% | 49.1% | 36.5% | -20.6% |
| 1.0-1.25 | 129 | 57.4% | 4.2% | -10.6% | 17.9% | 36.4% | 26.4% | -9.1% | 126 | 57.1% | 8.5% | -13.1% | 39.4% | 47.6% | 29.4% | -20.1% |
| >1.25 | 97 | 68.0% | 12.5% | -2.2% | 25.3% | 52.6% | 14.4% | -6.3% | 93 | 67.7% | 21.2% | -7.5% | 67.7% | 57.0% | 24.7% | -18.2% |

STABLECOIN_MCAP_12W_CHANGE:

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <0 | 121 | 55.4% | 1.5% | -7.3% | 12.8% | 28.1% | 19.8% | -7.7% | 117 | 59.8% | 6.0% | -11.0% | 32.5% | 45.3% | 27.4% | -16.2% |
| 0-5% | 27 | 59.3% | 5.2% | -8.7% | 15.3% | 33.3% | 18.5% | -5.6% | 23 | 69.6% | 26.9% | -4.0% | 47.7% | 65.2% | 21.7% | -14.0% |
| 5-10% | 20 | 50.0% | 0.2% | -7.1% | 11.9% | 30.0% | 20.0% | -9.2% | 20 | 30.0% | -13.9% | -38.9% | 7.9% | 25.0% | 65.0% | -46.9% |
| >10% | 274 | 60.9% | 5.8% | -10.2% | 24.0% | 43.8% | 25.5% | -7.8% | 274 | 60.9% | 17.6% | -15.7% | 52.5% | 54.0% | 29.9% | -20.9% |

### 16–17. Bull quality (univariate + limited 2–3 way)

Combinations with N<20 on ALL complete-12w weeks are flagged. De-clustered N is not used to promote sparse cells.

| bucket | N4 | pos4 | med4 | p25_4 | p75_4 | >10%_4 | <-10%_4 | medDD4 | N12 | pos12 | med12 | p25_12 | p75_12 | >10%_12 | <-10%_12 | medDD12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BULL | MOM12 <40 *(N<20 ALL WEEKS)* | 9 | 66.7% | 1.0% | -2.7% | 2.7% | 11.1% | 22.2% | -3.1% | 9 | 77.8% | 27.0% | 13.1% | 36.4% | 77.8% | 22.2% | -5.6% |
| BULL | MOM12 40-70 | 56 | 69.6% | 6.2% | -5.7% | 20.4% | 41.1% | 14.3% | -5.6% | 53 | 81.1% | 24.2% | 9.7% | 70.9% | 73.6% | 17.0% | -13.7% |
| BULL | MOM12 70-90 | 46 | 69.6% | 12.0% | -2.0% | 22.6% | 54.3% | 15.2% | -9.9% | 43 | 60.5% | 2.5% | -7.9% | 62.5% | 44.2% | 23.3% | -19.8% |
| BULL | MOM12 >=90 | 40 | 72.5% | 21.7% | -1.5% | 51.2% | 60.0% | 22.5% | -10.4% | 40 | 72.5% | 40.4% | -2.0% | 90.9% | 62.5% | 17.5% | -30.7% |
| BULL | BROAD | 128 | 68.0% | 8.9% | -4.4% | 26.1% | 48.4% | 17.2% | -8.2% | 122 | 72.1% | 21.0% | -4.0% | 70.7% | 60.7% | 19.7% | -19.5% |
| BULL | NOT_BROAD | 23 | 82.6% | 9.4% | 1.7% | 23.7% | 47.8% | 17.4% | -8.1% | 23 | 73.9% | 49.2% | -1.2% | 162.3% | 69.6% | 17.4% | -13.7% |
| BULL | NORMAL_VOL | 93 | 73.1% | 9.4% | -2.2% | 24.9% | 48.4% | 9.7% | -7.5% | 87 | 74.7% | 24.2% | -0.8% | 87.8% | 65.5% | 18.4% | -16.2% |
| BULL | HIGH_VOL | 58 | 65.5% | 8.6% | -11.6% | 31.7% | 48.3% | 29.3% | -11.0% | 58 | 69.0% | 19.3% | -5.8% | 70.4% | 56.9% | 20.7% | -29.9% |
| BULL | SC_EXPANDING | 134 | 70.1% | 11.3% | -3.7% | 26.2% | 51.5% | 18.7% | -8.2% | 130 | 70.8% | 25.2% | -5.1% | 82.6% | 62.3% | 20.8% | -18.2% |
| BULL | SC_CONTRACTING *(N<20 ALL WEEKS)* | 17 | 70.6% | 5.6% | -2.9% | 9.4% | 23.5% | 5.9% | -7.7% | 15 | 86.7% | 15.1% | 2.1% | 26.7% | 60.0% | 6.7% | -17.6% |
| BULL | TOVER_ABOVE | 105 | 71.4% | 11.6% | -2.2% | 26.1% | 51.4% | 14.3% | -8.3% | 99 | 73.7% | 29.9% | -2.0% | 91.8% | 64.6% | 17.2% | -18.2% |
| BULL | TOVER_BELOW | 46 | 67.4% | 3.2% | -9.7% | 23.9% | 41.3% | 23.9% | -4.4% | 46 | 69.6% | 17.0% | -8.6% | 43.0% | 56.5% | 23.9% | -21.2% |
| BULL | MOM12>=70 | BROAD | 76 | 68.4% | 13.1% | -2.7% | 31.4% | 56.6% | 19.7% | -10.3% | 73 | 65.8% | 13.2% | -6.1% | 73.8% | 50.7% | 20.5% | -22.5% |
| BULL | MOM12>=70 | NOT_BROAD *(N<20 ALL WEEKS)* | 10 | 90.0% | 14.9% | 5.1% | 23.8% | 60.0% | 10.0% | -9.3% | 10 | 70.0% | 146.9% | 6.0% | 197.4% | 70.0% | 20.0% | -14.6% |
| BULL | MOM12>=70 | NORMAL_VOL | 39 | 82.1% | 16.4% | 3.1% | 29.8% | 66.7% | 2.6% | -8.0% | 36 | 69.4% | 36.6% | -4.9% | 159.8% | 55.6% | 16.7% | -18.2% |
| BULL | BROAD | NORMAL_VOL | 76 | 71.1% | 9.1% | -2.6% | 25.0% | 48.7% | 7.9% | -6.0% | 70 | 74.3% | 23.1% | -1.2% | 79.5% | 64.3% | 20.0% | -16.2% |
| BULL | MOM12>=70 | BROAD | NORMAL_VOL | 33 | 78.8% | 17.8% | 1.5% | 28.4% | 66.7% | 3.0% | -7.5% | 30 | 66.7% | 13.5% | -5.1% | 156.1% | 50.0% | 20.0% | -18.5% |

### 18. 2020 vs 2021 (crypto-only)

- **2020-11-27** BULL_NORMAL_VOL / BROAD: MOM4=27.8% pctl=0.829; MOM12=48.6% pctl=0.755; broad=0.740; lc_v1=0.830; lc_lag=0.800; VOL=0.0580 pctl=0.198 NORMAL_VOL; TOVER_REL=1.025; SC4=11.5% SC12=43.3%; fut4=31.1% fut12=241.0%; dd4=-3.6% dd12=-10.4%
  - attribution 12w: BTC=148.8%, ETH=34.1%, TOP10_BY_START_WEIGHT=205.4%, LARGECAP_LAGGED=224.5%, REST_EX_BTC_ETH=58.1%
- **2020-12-04** BULL_NORMAL_VOL / BROAD: MOM4=21.7% pctl=0.755; MOM12=62.2% pctl=0.803; broad=0.708; lc_v1=0.790; lc_lag=0.780; VOL=0.0573 pctl=0.190 NORMAL_VOL; TOVER_REL=1.119; SC4=13.1% SC12=39.0%; fut4=40.9% fut12=158.4%; dd4=-3.6% dd12=-18.2%
  - attribution 12w: BTC=98.3%, ETH=19.2%, TOP10_BY_START_WEIGHT=132.4%, LARGECAP_LAGGED=144.6%, REST_EX_BTC_ETH=40.9%
- **2021-10-29** BULL_NORMAL_VOL / BROAD: MOM4=23.4% pctl=0.748; MOM12=51.5% pctl=0.729; broad=0.731; lc_v1=0.840; lc_lag=0.810; VOL=0.0766 pctl=0.299 NORMAL_VOL; TOVER_REL=0.959; SC4=2.3% SC12=12.1%; fut4=-9.8% fut12=-40.1%; dd4=-14.5% dd12=-43.2%
  - attribution 12w: BTC=-18.3%, ETH=-8.3%, TOP10_BY_START_WEIGHT=-33.4%, LARGECAP_LAGGED=-38.5%, REST_EX_BTC_ETH=-13.5%
- **2021-11-05** BULL_NORMAL_VOL / BROAD: MOM4=16.1% pctl=0.645; MOM12=32.6% pctl=0.590; broad=0.708; lc_v1=0.790; lc_lag=0.760; VOL=0.0661 pctl=0.236 NORMAL_VOL; TOVER_REL=0.998; SC4=4.3% SC12=14.3%; fut4=-10.1% fut12=-41.4%; dd4=-14.5% dd12=-43.5%
  - attribution 12w: BTC=-16.3%, ETH=-8.5%, TOP10_BY_START_WEIGHT=-32.8%, LARGECAP_LAGGED=-39.3%, REST_EX_BTC_ETH=-16.5%

These four dates are **not** the catalog. They illustrate the North Star problem: similar V1 Bull labels, opposite 12w outcomes.

**Crypto-native variables that look similar:** V1 state (`BULL_NORMAL_VOL` / `BROAD`), MOM_4W (~16–28%), MOM_12W (~33–62%), expanding MOM percentiles (roughly 0.59–0.83), broad breadth (~0.71–0.74), lagged large-cap breadth (~0.76–0.81), VOL percentile still NORMAL and not high (~0.19–0.30).

**Crypto-native variables that differ:** stablecoin 12w growth is much stronger in late 2020 (~39–43%) than late 2021 (~12–14%); turnover is slightly above its 12w median in 2020 and at/below it in 2021; 2021 MOM_12W percentile is a bit lower on 2021-11-05 (0.59 vs 0.75–0.80). Attribution of the *outcome* is large-cap/BTC-led in both cases (not a different market composition of the rally vs crash).

**Crypto-only fails to explain** why two internally similar Bull weeks produced +241% vs −40% over 12 weeks. The stablecoin-growth gap is a candidate internal difference, not a sufficient discriminator. Macro is reserved.

In 12w *losses*, GROUP rows (BTC/ETH/LARGECAP) are the economically meaningful negative contributions. `TOP_CONTRIBUTOR` ranks the most *positive* residual names and can look like dust (JNS, ECN, ION). Use BOTTOM_CONTRIBUTOR / GROUP rows for crash attribution.

---

## CANDIDATE HYPOTHESES (not predictors)

H1. Higher expanding MOM_4W percentile is associated with a better 12w distribution than the bottom bucket, but MOM_12W is **not strictly monotonic** (40–70 looks better than 70–90 in this sample). Do not freeze a “Strong Bull” cut from the best cell.

H2. Broader 4w participation is associated with better forward distributions than narrow participation, including inside V1 Bull.

H3. Inside Bull, HIGH_VOL does not automatically mean better continuation; it may mark late/fragile states. Treat as a hypothesis from the Bull×vol rows.

H4. Stablecoin 12w expansion and turnover above the recent median are liquidity/activity correlates, not sufficient bullish signals.

H5. Extreme 12w gains are often concentrated in BTC/large caps even when breadth looks broad. Attribution, not the headline breadth number, decides “broad vs concentrated.”

H6. Late-2020 vs late-2021 may **not** be separable on crypto internals alone. That is the reserved macro question, not answered here.

---

## 19. What crypto-only still cannot explain

- Why two BULL_NORMAL_VOL weeks with similar MOM and breadth produced +200% vs −40% 12w outcomes.
- Whether MOM/breadth gradients survive walk-forward and 2024–2026.
- Overlapping-window dependence (even de-clustered N is small in the tails).
- Wash-trading noise in CMC turnover.

## 20. What should move to Phase 4/6

KEEP as research features (not yet model thresholds):

- expanding MOM_4W / MOM_12W percentiles
- broad breadth level (not only the 0.50 Bull switch)
- lagged large-cap breadth (prefer over V1 contemporaneous if Δ is material)
- VOL_PERCENTILE overlay inside Bull
- stablecoin 12w change as a liquidity diagnostic
- extreme-episode concentration (BTC/top10 share)

DIAGNOSTIC ONLY until walk-forward:

- TURNOVER_RELATIVE
- 2020/2021 forensic dates
- +20% “strong continuation” label

DROP for now:

- using outcome percentiles as features
- sparse 3-way cells with N<20
- any macro series

---

No trading rule is implied. Descriptive findings ≠ candidate hypotheses ≠ validated predictors.
