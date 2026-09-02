# Wen et al. (2022) — réplica 5m → hourly (Binance BTCUSDT)

Paper: Wen, Bouri, Xu & Zhao (2022), NAJEF 62, 101733.
DOI: 10.1016/j.najef.2022.101733.

**Methodological replication on a different exchange and later sample.**
No es una réplica exacta del dataset original.

| | Paper | Esta réplica |
|---|---|---|
| Exchange | Bitstamp (GMT) | Binance Spot BTCUSDT (UTC) |
| Sample | 2013-03-03 → 2020-05-31 (paper); IS 2013–2016 / OOS 2017–2021 | 2017-08-17 → latest; IS/OOS-1/OOS-2 propios |
| Frecuencia | 5-min high-frequency, hourly returns | 5-min Binance, hourly returns reconstruidos |
| Activo | Bitcoin | BTCUSDT spot |

No forecasts, no jumps, no liquidity, no vol conditioning, no trading.

Snapshot 5m: `btcusdt_5m.csv` · SHA256 `119ee73d9211cd829e5d84d622989cc15aab4df4086bcb2e1ea1856731f07396` · source `binance_spot_klines_5m`.
N=947823 · 2017-08-17 04:00:00 → 2026-08-27 04:05:00 · dups=0 · missing 5m=1715.

---

## Convención de precio horario (auditada)

Paper Eq. (1): `r_{i,t} = log(p_{i,t}) − log(p_{i-1,t})`, i=1..24, `p_{0,t}` = precio a las 00:00.

Binance 5m **open-labeled**:

- hora UTC `h` = intervalo `[h:00, h+1:00)`
- 12 velas: `h:00 … h:55`
- **`p` al cierre de la hora h = close de la vela `h:55`–`(h+1):00`**
- eso **no** es el close de `h:00` (precio a las `h:05`)

Indexación: `hour_utc` h=0..23 = paper hour i=h+1.

Mapping de los pares Wen (re-verificado, igual que la réplica 1h):

| paper | UTC |
|---|---|
| r3→r17 momentum | 02→16 |
| r8→r22 momentum | 07→21 |
| r3→r5 reversal | 02→04 |
| r3→r15 reversal | 02→14 |
| r12→r13 reversal | 11→12 |
| r22→r23 reversal | 21→22 |

HAC: Newey–West (1987) + bandwidth NW (1994) `L=floor(4*(N/100)^(2/9))`, suelo 5, `use_correction=True`. Idéntico a la réplica 1h. No se reoptimizó el lag.

Freeze (IS+OOS-1 only, umbrales **no** retocados tras ver OOS-2):

- mismo signo
- `|β| ≥ 0.03` en IS y OOS-1
- `p < 0.05` en IS y OOS-1

OOS-2 survival: mismo signo, `|β| ≥ 0.03`, `p < 0.1`.

Retornos horarios finitos: 78957. Días con 24 retornos finitos: 3265.
Horas incompletas (<12 barras 5m): 159 / 79129.

---

## 1. ¿Los precios horarios desde 5m coinciden con Binance 1h?

Overlap N=78974. max |Δclose|=0.0000000000, median |Δclose|=0.000000000000, % idénticos (rel≤1e-08)=100.0000, % |Δ|≤1e-6=100.0000.

La vela Binance 1h con open `h:00` cierra a las `h+1:00`, que es el close de la 5m `h:55`. Deben coincidir salvo huecos.

## 2. ¿Los seis pares Wen muestran la misma dirección?

- UTC 02→16 (MOMENTUM): dirección paper | FULL:YES(β=0.0252); IS:YES(β=0.0846); OOS-1:NO(β=-0.1208); OOS-2:NO(β=-0.0473) | raw p<0.05 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO
- UTC 07→21 (MOMENTUM): dirección paper | FULL:YES(β=0.0393); IS:YES(β=0.0554); OOS-1:YES(β=0.0208); OOS-2:NO(β=-0.0039) | raw p<0.05 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO
- UTC 02→04 (REVERSAL): dirección paper | FULL:YES(β=-0.0726); IS:YES(β=-0.1310); OOS-1:NO(β=0.0495); OOS-2:NO(β=0.0427) | raw p<0.05 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO
- UTC 02→14 (REVERSAL): dirección paper | FULL:YES(β=-0.0125); IS:YES(β=-0.0426); OOS-1:NO(β=0.0731); OOS-2:YES(β=-0.0013) | raw p<0.05 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO
- UTC 11→12 (REVERSAL): dirección paper | FULL:YES(β=-0.1079); IS:YES(β=-0.1233); OOS-1:YES(β=-0.1022); OOS-2:YES(β=-0.0222) | raw p<0.05 FULL:YES; IS:YES; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO
- UTC 21→22 (REVERSAL): dirección paper | FULL:YES(β=-0.1493); IS:YES(β=-0.2422); OOS-1:YES(β=-0.0105); OOS-2:YES(β=-0.0484) | raw p<0.05 FULL:YES; IS:YES; OOS-1:NO; OOS-2:NO | FDR<0.10 FULL:NO; IS:NO; OOS-1:NO; OOS-2:NO

## 3. ¿Alguno tiene significancia raw?

Dos pares Wen tienen p crudo < 0.05, solo en FULL e IS, nunca en OOS-1/OOS-2 y nunca tras FDR:

- UTC 11→12 (r12→r13 reversal): FULL p=0.0047, IS p=0.015
- UTC 21→22 (r22→r23 reversal): FULL p=0.022, IS p=0.011

Los cuatro pares restantes de Wen no alcanzan p<0.05 en ningún sample. p<0.05 no es “predictor” por sí solo (276 tests).

## 4. ¿Alguno sobrevive FDR?

FULL FDR<0.10: 0 / 276.
IS: 0; OOS-1: 0; OOS-2: 0.
FDR mínimo FULL=0.226, IS=0.373, OOS-1=0.589, OOS-2=0.185.

## 5. ¿Hay momentum intradía?

FULL pares β>0 y p<0.05: 7.
Candidatos momentum IS+OOS-1: 1. Superviven OOS-2: 0.

## 6. ¿Hay reversal intradía?

FULL pares β<0 y p<0.05: 15.
Candidatos reversal IS+OOS-1: 0. Superviven OOS-2: 0.

## 7. ¿Son estables IS → OOS-1?

- UTC 09→21 (MOMENTUM, FAILED FINAL OOS, SAME_SIGN): β_IS=0.1238, β_OOS1=0.1196, β_OOS2=0.0067, t=0.14, p=0.8908, FDR=0.987, R²=0.0000, N=969

## 8. ¿Sobreviven OOS-2?

SURVIVED=0, FAILED=1. No se reemplazan fallidos.

## 9. ¿Cambió algo importante respecto a 1h nativo?

Celdas comparadas (IS/OOS-1/OOS-2 × 276): 828. |Δβ| mediano=0.000000, |Δβ| máx=0.013145. Signos distintos 5m vs 1h: 3 (0.36%).

Comparación pares Wen 5m vs 1h:

- UTC 02→16 (MOMENTUM) | IS: β_5m=0.0846 vs β_1h=0.0845 (t 1.65 vs 1.65) | OOS-1: β_5m=-0.1208 vs β_1h=-0.1208 (t -1.92 vs -1.92) | OOS-2: β_5m=-0.0473 vs β_1h=-0.0474 (t -1.01 vs -1.01)
- UTC 07→21 (MOMENTUM) | IS: β_5m=0.0554 vs β_1h=0.0553 (t 0.93 vs 0.93) | OOS-1: β_5m=0.0208 vs β_1h=0.0208 (t 0.33 vs 0.33) | OOS-2: β_5m=-0.0039 vs β_1h=-0.0038 (t -0.07 vs -0.07)
- UTC 02→04 (REVERSAL) | IS: β_5m=-0.1310 vs β_1h=-0.1310 (t -1.59 vs -1.59) | OOS-1: β_5m=0.0495 vs β_1h=0.0496 (t 1.24 vs 1.24) | OOS-2: β_5m=0.0427 vs β_1h=0.0427 (t 1.13 vs 1.13)
- UTC 02→14 (REVERSAL) | IS: β_5m=-0.0426 vs β_1h=-0.0426 (t -0.79 vs -0.79) | OOS-1: β_5m=0.0731 vs β_1h=0.0731 (t 1.43 vs 1.43) | OOS-2: β_5m=-0.0013 vs β_1h=0.0000 (t -0.02 vs 0.00)
- UTC 11→12 (REVERSAL) | IS: β_5m=-0.1233 vs β_1h=-0.1226 (t -2.43 vs -2.42) | OOS-1: β_5m=-0.1022 vs β_1h=-0.1022 (t -1.47 vs -1.47) | OOS-2: β_5m=-0.0222 vs β_1h=-0.0222 (t -0.30 vs -0.30)
- UTC 21→22 (REVERSAL) | IS: β_5m=-0.2422 vs β_1h=-0.2422 (t -2.55 vs -2.56) | OOS-1: β_5m=-0.0105 vs β_1h=-0.0105 (t -0.20 vs -0.20) | OOS-2: β_5m=-0.0484 vs β_1h=-0.0484 (t -0.90 vs -0.89)

Top |t| 5m por sample:

- FULL: 09→21 (β=0.1119, t=3.16, FDR=0.226), 18→21 (β=-0.1080, t=-3.15, FDR=0.226), 00→02 (β=-0.1153, t=-2.87, FDR=0.276), 11→12 (β=-0.1079, t=-2.83, FDR=0.276), 03→18 (β=-0.1018, t=-2.81, FDR=0.276)
- IS: 04→05 (β=-0.1739, t=-2.93, FDR=0.373), 03→11 (β=-0.1171, t=-2.68, FDR=0.373), 03→18 (β=-0.1385, t=-2.59, FDR=0.373), 21→22 (β=-0.2422, t=-2.55, FDR=0.373), 18→21 (β=-0.1443, t=-2.55, FDR=0.373)
- OOS-1: 07→11 (β=-0.1479, t=-3.07, FDR=0.589), 17→23 (β=0.0882, t=2.63, FDR=0.592), 14→22 (β=0.0612, t=2.58, FDR=0.592), 09→19 (β=-0.1197, t=-2.57, FDR=0.592), 07→15 (β=-0.1574, t=-2.55, FDR=0.592)
- OOS-2: 12→23 (β=0.1066, t=3.40, FDR=0.185), 09→23 (β=-0.1159, t=-2.88, FDR=0.387), 01→08 (β=0.1114, t=2.74, FDR=0.387), 15→17 (β=0.0916, t=2.70, FDR=0.387), 19→21 (β=-0.1186, t=-2.65, FDR=0.387)

Los closes 5m→hourly vs Binance 1h son **idénticos** (max |Δ|=0). Los 3 flips de signo son celdas con |β|<0.005 y |t|<0.08 (ruido alrededor de cero). |Δβ| mediano=0. El par freeze 09→21 y los seis pares Wen son los mismos que en 1h. **El 5m no cambia la conclusión de la réplica 1h.**

## 10. ¿La réplica del paper mejora, empeora o queda igual?

Respecto a usar 1h nativo: **queda igual**. Reconstruir desde 5m confirma que el resultado anterior no era un artefacto de velas 1h nativas.
Respecto al paper Bitstamp 2013–2020: sigue sin confirmarse. El 5m acerca la *construcción* del retorno (alta frecuencia → hourly), no el exchange ni el calendario original.

## 11. Veredicto

No hay FDR<0.10 en IS ni OOS-1 (o los candidatos freeze no sobreviven OOS-2). Los pares destacados de Wen et al. no se confirman de forma estable en Binance 5m→hourly. Esto no es una réplica exacta del dataset Bitstamp 2013–2020.

---

## A. PAPER-LIKE / FULL Binance sample (descriptivo)

No finge el calendario 2013–2020 del paper.

| | p<0.05 | FDR<0.10 | FDR<0.05 | β>0 & p<0.05 | β<0 & p<0.05 | R² mediano |
|---|---:|---:|---:|---:|---:|---:|
| FULL | 22 | 0 | 0 | 7 | 15 | 0.0007 |

## B. Strict validation

| sample | p<0.05 | FDR<0.10 | min FDR | R² mediano |
|---|---:|---:|---:|---:|
| IS | 27 | 0 | 0.373 | 0.0015 |
| OOS-1 | 14 | 0 | 0.589 | 0.0016 |
| OOS-2 | 18 | 0 | 0.185 | 0.0007 |

## Pares Wen (todos los samples)

- MOMENTUM paper r3->r17 UTC 02→16 | FULL: β=0.0252, t=0.70, p=0.4839, FDR=0.903, R²=0.0005, N=3277
- MOMENTUM paper r3->r17 UTC 02→16 | IS: β=0.0846, t=1.65, p=0.0995, FDR=0.564, R²=0.0065, N=1216
- MOMENTUM paper r3->r17 UTC 02→16 | OOS-1: β=-0.1208, t=-1.92, p=0.0550, FDR=0.708, R²=0.0102, N=1092
- MOMENTUM paper r3->r17 UTC 02→16 | OOS-2: β=-0.0473, t=-1.01, p=0.3127, FDR=0.925, R²=0.0017, N=969
- MOMENTUM paper r8->r22 UTC 07→21 | FULL: β=0.0393, t=0.97, p=0.3338, FDR=0.851, R²=0.0012, N=3283
- MOMENTUM paper r8->r22 UTC 07→21 | IS: β=0.0554, t=0.93, p=0.3517, FDR=0.885, R²=0.0026, N=1221
- MOMENTUM paper r8->r22 UTC 07→21 | OOS-1: β=0.0208, t=0.33, p=0.7379, FDR=0.897, R²=0.0003, N=1093
- MOMENTUM paper r8->r22 UTC 07→21 | OOS-2: β=-0.0039, t=-0.07, p=0.9403, FDR=0.989, R²=0.0000, N=969
- REVERSAL paper r3->r5 UTC 02→04 | FULL: β=-0.0726, t=-1.18, p=0.2385, FDR=0.815, R²=0.0070, N=3276
- REVERSAL paper r3->r5 UTC 02→04 | IS: β=-0.1310, t=-1.59, p=0.1123, FDR=0.585, R²=0.0220, N=1217
- REVERSAL paper r3->r5 UTC 02→04 | OOS-1: β=0.0495, t=1.24, p=0.2160, FDR=0.748, R²=0.0034, N=1090
- REVERSAL paper r3->r5 UTC 02→04 | OOS-2: β=0.0427, t=1.13, p=0.2596, FDR=0.916, R²=0.0030, N=969
- REVERSAL paper r3->r15 UTC 02→14 | FULL: β=-0.0125, t=-0.31, p=0.7543, FDR=0.996, R²=0.0001, N=3276
- REVERSAL paper r3->r15 UTC 02→14 | IS: β=-0.0426, t=-0.79, p=0.4280, FDR=0.923, R²=0.0017, N=1216
- REVERSAL paper r3->r15 UTC 02→14 | OOS-1: β=0.0731, t=1.43, p=0.1526, FDR=0.708, R²=0.0025, N=1091
- REVERSAL paper r3->r15 UTC 02→14 | OOS-2: β=-0.0013, t=-0.02, p=0.9810, FDR=0.989, R²=0.0000, N=969
- REVERSAL paper r12->r13 UTC 11→12 | FULL: β=-0.1079, t=-2.83, p=0.0047, FDR=0.276, R²=0.0083, N=3290
- REVERSAL paper r12->r13 UTC 11→12 | IS: β=-0.1233, t=-2.43, p=0.0151, FDR=0.373, R²=0.0128, N=1227
- REVERSAL paper r12->r13 UTC 11→12 | OOS-1: β=-0.1022, t=-1.47, p=0.1425, FDR=0.708, R²=0.0053, N=1094
- REVERSAL paper r12->r13 UTC 11→12 | OOS-2: β=-0.0222, t=-0.30, p=0.7612, FDR=0.962, R²=0.0004, N=969
- REVERSAL paper r22->r23 UTC 21→22 | FULL: β=-0.1493, t=-2.29, p=0.0221, FDR=0.554, R²=0.0233, N=3294
- REVERSAL paper r22->r23 UTC 21→22 | IS: β=-0.2422, t=-2.55, p=0.0106, FDR=0.373, R²=0.0586, N=1230
- REVERSAL paper r22->r23 UTC 21→22 | OOS-1: β=-0.0105, t=-0.20, p=0.8393, FDR=0.939, R²=0.0001, N=1095
- REVERSAL paper r22->r23 UTC 21→22 | OOS-2: β=-0.0484, t=-0.90, p=0.3703, FDR=0.946, R²=0.0022, N=969

## STATISTICAL PREDICTABILITY vs ECONOMIC VALUE vs TRADEABLE EDGE

Esta fase mide construcción de retornos y **statistical predictability**.
No se afirma valor económico ni edge tradable. No hay forecasts.

---

### C — REPLICATION NOT CONFIRMED
