# Replication summary — Hsieh, Huang & Liu (2025)

Phase: core academic replication after reading the published PDF.
Script: `src/replicate_hsieh_2025.py`
Date written: 2026-08-28
Primary reported slice below: **J=2, K=1, equal-weighted, Table-3 1-week Asem–Tian states**.

## Answers

1. **¿Pudimos reconstruir correctamente el universo del paper?**
   Partially. Source is CoinMarketCap, period 2015–2023, Friday log returns,
   stablecoins excluded, mcap ≥ $1m, zero volume dropped, <20-week histories
   dropped. We observe Friday snapshots rather than the authors’ daily file,
   so the zero-volume filter uses Friday volume, not every day of the week.

2. **¿Cuál fue el número de criptomonedas?**
   Raw unique `asset_id` on Friday snapshots: **23685**.
   Unique coins ever passing Appendix A screens: **3898**.
   Paper Table 1 full sample: **2130**.
   Weeks in market-state file: **451**.

3. **¿Coincide aproximadamente con el paper?**
   NO:
   replica eligible unique coins = 3898 vs paper 2130.

4. **¿Pudimos reconstruir el market return value-weighted?**
   Yes, using lagged market cap of eligible coins. Replica difference: Friday
   snapshots, not daily-to-Friday aggregation from a daily file.

5. **¿Pudimos reproducir UP/DOWN?**
   Two definitions, because the PDF contradicts itself:
   - Section 3.1 Cooper 4-week: UP=243, DOWN=204.
   - Tables 2–3 notes / Asem–Tian 1-week prior vs subsequent:
     {'UP->UP': 146, 'DOWN->UP': 108, 'UP->DOWN': 108, 'DOWN->DOWN': 88}.
   Primary table uses the Table 3 note (1-week prior and subsequent).

6. **¿Existe momentum unconditional?**
   W=-0.0509 L=-0.0090 WML=-0.0419 t=-8.26 p=0.000 N=451

7. **¿Existe momentum en UP→UP?**
   K=1: W=0.0139 L=0.0448 WML=-0.0309 t=-3.85 p=0.000 N=146
   K=2: W=0.0319 L=0.0428 WML=-0.0109 t=-1.92 p=0.055 N=146
   Paper Table 3 K=1 WML=0.0119 (t=2.31); K=2 WML=0.0101 (t=2.45).

8. **¿Existe momentum en UP→DOWN?**
   W=-0.1235 L=-0.0727 WML=-0.0508 t=-5.60 p=0.000 N=108
   Paper Table 3 K=1 WML=0.0094 (t=0.93).

9. **¿Existe momentum en DOWN→UP?**
   W=-0.0092 L=0.0419 WML=-0.0511 t=-4.26 p=0.000 N=108
   Paper Table 3 K=1 WML=-0.0082 (t=-0.56).

10. **¿Existe momentum en DOWN→DOWN?**
    W=-0.1203 L=-0.0849 WML=-0.0355 t=-4.98 p=0.000 N=88
    Paper Table 3 K=1 WML=0.0071 (t=1.06).

11. **¿Los signos coinciden con el paper?**
    UNCONDITIONAL/Table2 UP K=1 paper WML=0.0089: replica W=-0.0446 L=-0.0052 WML=-0.0394 t=-6.21 p=0.000 N=254
    Table2 DOWN K=1 paper WML=0.0065: replica W=-0.0591 L=-0.0150 WML=-0.0441 t=-5.55 p=0.000 N=196
    UP→UP sign match: NO
    UP→DOWN paper +0.0094: replica sign NO
    DOWN→UP paper -0.0082: replica sign YES
    DOWN→DOWN paper +0.0071: replica sign NO

12. **¿Las magnitudes son similares?**
    UP→UP K=1 paper 0.0119 vs replica -0.0309.
    50% relative band: NO.

13. **¿Los t-stats/significance son similares?**
    UP→UP paper t=2.31 (5%): replica t=-3.85 (significant at 5%).
    Other transitions paper all insignificant at 5%: 
    UP→DOWN significant at 5%;
    DOWN→UP significant at 5%;
    DOWN→DOWN significant at 5%.

14. **¿Cuál es la principal diferencia frente al paper?**
    (a) Eligible unique coins **3898 vs 2130** — Appendix A screens were
    applied, but the universe is still much larger (Friday snapshots, our
    stablecoin list, $1m applied on lagged mcap).
    (b) Equal-weighted WML is a **short-term reversal** (losers >> winners),
    driven by small coins. Paper Table 3 has Winner > Loser in UP–UP
    (0.0145 vs 0.0026). Our EW UP–UP is Winner 0.0139 vs Loser 0.0448.
    (c) Value-weighted (not stated in the PDF) restores a positive UP–UP WML
    of 0.0377 (t=3.17) vs paper 0.0119 (t=2.31): same sign/significance,
    about 3× the magnitude. Other VW transitions are insignificant at 5%
    except UP–DOWN at 10% (t=1.73).
    (d) Friday CMC listings snapshots, not the authors’ daily tape.
    (e) Newey–West lags = 4 (not stated).
    (f) Body text Cooper 4-week vs Table 3 1-week Asem–Tian notes.

15. **¿Podemos afirmar que replicamos la conclusión central?**
    Central claim: WML significant only in UP→UP. This replica:
    UP→UP significant at 5%;
    others as above.

## Comparison with the paper’s conclusions

Primary slice: J=2, K=1, equal-weighted, Table-3 1-week transitions.
Returns are weekly decimals, as in the paper.

| Hallazgo | Paper | Nuestra réplica | Match |
| --- | --- | --- | --- |
| Momentum unconditional | not a numbered main-text claim; Table 2 UP K=1 WML=0.0089 (t=1.80) | W=-0.0509 L=-0.0090 WML=-0.0419 t=-8.26 p=0.000 N=451 | NO |
| UP→UP momentum | 0.0119 (t=2.31), significant 5% | W=0.0139 L=0.0448 WML=-0.0309 t=-3.85 p=0.000 N=146 | NO |
| UP→DOWN momentum | 0.0094 (t=0.93), not significant | W=-0.1235 L=-0.0727 WML=-0.0508 t=-5.60 p=0.000 N=108 | NO |
| DOWN→UP momentum | -0.0082 (t=-0.56), not significant | W=-0.0092 L=0.0419 WML=-0.0511 t=-4.26 p=0.000 N=108 | NO |
| DOWN→DOWN momentum | 0.0071 (t=1.06), not significant | W=-0.1203 L=-0.0849 WML=-0.0355 t=-4.98 p=0.000 N=88 | NO |

Table 2 UP vs DOWN (past 1-week note), J=2 K=1 equal-weighted:

| Hallazgo | Paper | Nuestra réplica |
| --- | --- | --- |
| UP markets WML | 0.0089 (t=1.80) | W=-0.0446 L=-0.0052 WML=-0.0394 t=-6.21 p=0.000 N=254 |
| DOWN markets WML | 0.0065 (t=1.39) | W=-0.0591 L=-0.0150 WML=-0.0441 t=-5.55 p=0.000 N=196 |

Same slice, **value-weighted** (weighting not stated in the PDF; not used to
flip the verdict):

| Hallazgo | Paper | Nuestra réplica VW | Match vs paper sig |
| --- | --- | --- | --- |
| UP→UP K=1 | 0.0119 (t=2.31) sig 5% | W=0.0666 L=0.0289 WML=0.0377 t=3.17 p=0.002 N=146 | YES on sign/sig, NO on magnitude |
| UP→DOWN K=1 | 0.0094 (t=0.93) ns | WML=0.0224 t=1.73 p=0.084 N=108 | YES at 5% (ns), NO at 10% |
| DOWN→UP K=1 | −0.0082 (t=−0.56) ns | WML=−0.0092 t=−0.70 p=0.484 N=108 | YES |
| DOWN→DOWN K=1 | 0.0071 (t=1.06) ns | WML=−0.0396 t=−0.97 p=0.334 N=88 | YES on ns; sign differs |

### C — REPLICATION NOT CONFIRMED
