# Time-series momentum en Bitcoin — réplica mínima

Inspirado en Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*.
Este documento responde las ocho preguntas del protocolo. **No** es una estrategia.

Fecha de ejecución: 2026-08-26 06:50 UTC
Seed: 42. Block bootstrap: 2000 réplicas, block length = horizonte futuro h.
Newey-West / HAC: maxlags = h (solapamiento de R_future).
FDR: Benjamini-Hochberg sobre las 8 combinaciones (k,h) **dentro de cada sample**.

---

## Datos

- **Serie usada:** `data/btcusd_daily.csv`
- **Fuente:** Empalme: Bitstamp BTCUSD (CryptoDataDownload) hasta 2017-08-16; Binance BTCUSDT spot klines 1d desde 2017-08-17. Cierre diario. Timezone: UTC (vela 00:00–00:00 UTC).
- **Fecha inicial:** 2014-11-28
- **Fecha final:** 2026-08-25 (última vela UTC **completa**; la vela del día en curso se descarta)
- **N observaciones:** 4289
- **Timezone:** UTC
- **Duplicados de fecha:** 0
- **Cierres NaN:** 0
- **Días calendario faltantes (no rellenados):** 0
- **Primeros huecos:** (ninguno en la muestra usada)
- **Conteo por fuente:** binance_btcusdt=3296, bitstamp_btcusd=993
- **Salto Bitstamp vs Binance el 2017-08-17:** 0.20%
- **IS:** t ≤ 2020-12-31. **OOS:** t ≥ 2021-01-01. Split por fecha de la **señal**.
- **Look-ahead:** R_future(h,t) = P_(t+h)/P_t − 1 es solo target. Percentiles OOS congelados con la distribución IS de R_past. Vol EWMA (com=60 días) usa retornos hasta t.

No se interpoló ningún precio. Si falta P_(t-k) o P_(t+h), esa fila se excluye del (k,h) correspondiente.

---

## 1. ¿Existe momentum estadístico en BTC?

**No hay momentum estadístico robusto en el sentido del paper (t HAC + FDR). Sí hay un sesgo de signo: casi todas las betas OOS son positivas, el R² es bajo, y el único indicio decente es k=30. La especificación vol-scaled del paper refuerza ese lookback corto y no resucita el de 365 días.**

Betas OOS > 0: 8/8. p-value HAC < 0.05 (sin corregir): 0/8.
FDR < 0.10: 0/8. Cambio de signo IS→OOS: 1/8.

Interpretación: beta > 0 en `R_future(h) = alpha + beta * R_past(k) + e` es continuación.
Los errores no son iid; los t-stats son HAC/Newey-West. Un p < 0.05 crudo **no** se lee como “predictivo”.

### IS

| k | h | beta | t | p | FDR | R² | P(up) | P(up\|past>0) | edge | N |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 7 | 0.023 | 0.89 | 0.371 | 0.960 | 0.003 | 57.6% | 60.1% | 2.6% | 2196 |
| 30 | 30 | 0.054 | 0.62 | 0.532 | 0.960 | 0.003 | 62.8% | 62.3% | -0.5% | 2196 |
| 90 | 7 | 0.011 | 0.88 | 0.376 | 0.960 | 0.004 | 57.8% | 57.9% | 0.2% | 2136 |
| 90 | 30 | 0.038 | 0.66 | 0.511 | 0.960 | 0.007 | 62.7% | 62.9% | 0.1% | 2136 |
| 180 | 7 | 0.002 | 0.35 | 0.727 | 0.960 | 0.001 | 58.1% | 57.1% | -0.9% | 2046 |
| 180 | 30 | 0.016 | 0.45 | 0.651 | 0.960 | 0.005 | 63.9% | 64.1% | 0.2% | 2046 |
| 365 | 7 | 0.000 | 0.06 | 0.953 | 0.960 | 0.000 | 57.7% | 57.0% | -0.6% | 1861 |
| 365 | 30 | -0.001 | -0.05 | 0.960 | 0.960 | 0.000 | 63.0% | 61.1% | -1.8% | 1861 |

### OOS (prioridad)

| k | h | beta | t | p | FDR | R² | P(up) | P(up\|past>0) | edge | N |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 7 | 0.024 | 1.16 | 0.244 | 0.562 | 0.003 | 51.8% | 53.5% | 1.7% | 2056 |
| 30 | 30 | 0.117 | 1.95 | 0.052 | 0.414 | 0.017 | 52.2% | 53.1% | 0.9% | 2033 |
| 90 | 7 | 0.012 | 1.08 | 0.281 | 0.562 | 0.005 | 51.8% | 52.2% | 0.4% | 2056 |
| 90 | 30 | 0.049 | 1.37 | 0.171 | 0.562 | 0.018 | 52.2% | 50.2% | -2.1% | 2033 |
| 180 | 7 | 0.000 | 0.04 | 0.965 | 0.996 | 0.000 | 51.8% | 52.2% | 0.4% | 2056 |
| 180 | 30 | 0.000 | 0.01 | 0.996 | 0.996 | 0.000 | 52.2% | 49.8% | -2.4% | 2033 |
| 365 | 7 | 0.001 | 0.20 | 0.838 | 0.996 | 0.000 | 51.8% | 54.3% | 2.6% | 2056 |
| 365 | 30 | 0.002 | 0.18 | 0.856 | 0.996 | 0.000 | 52.2% | 53.9% | 1.7% | 2033 |

### FULL (descriptivo)

| k | h | beta | t | p | FDR | R² | P(up) | P(up\|past>0) | edge | N |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 7 | 0.026 | 1.44 | 0.150 | 0.370 | 0.004 | 54.8% | 57.2% | 2.4% | 4252 |
| 30 | 30 | 0.093 | 1.43 | 0.151 | 0.370 | 0.009 | 57.7% | 58.2% | 0.5% | 4229 |
| 90 | 7 | 0.013 | 1.48 | 0.138 | 0.370 | 0.006 | 54.8% | 55.4% | 0.6% | 4192 |
| 90 | 30 | 0.051 | 1.33 | 0.185 | 0.370 | 0.014 | 57.6% | 57.2% | -0.4% | 4169 |
| 180 | 7 | 0.003 | 0.61 | 0.544 | 0.726 | 0.001 | 54.9% | 54.8% | -0.1% | 4102 |
| 180 | 30 | 0.016 | 0.67 | 0.500 | 0.726 | 0.005 | 58.1% | 57.5% | -0.6% | 4079 |
| 365 | 7 | 0.001 | 0.39 | 0.696 | 0.766 | 0.001 | 54.6% | 55.8% | 1.3% | 3917 |
| 365 | 30 | 0.003 | 0.30 | 0.766 | 0.766 | 0.001 | 57.4% | 57.9% | 0.6% | 3894 |

---

## 2. ¿Existe reversal?

**No en la regresión lineal: 0/8 betas OOS negativas. El único beta IS negativo (k=365, h=30) es ruido (t≈0) y no se replica OOS. Hay indicios de reversal solo en colas extremas (sección 3), distinto del reversal post-12 meses del paper.**

beta < 0 OOS: 0/8. Combinaciones clasificadas REVERSAL: 0/8.

El paper encuentra reversión **después** de ~12 meses, no dentro del primer año. Aquí k≤365 y h≤30, así que un beta negativo sería reversal de corto plazo (distinto del reversal de largo plazo del paper).

---

## 3. ¿Qué ocurre después de subidas extremas?

**No es uniforme. El cuerpo de la distribución (sobre todo 75–90) suele continuar. Tras un rally extremo de 30 días, los 7 días siguientes en el top 5% OOS tienden a revertir (mean −3.1%, P(up)=44%, N=25, CI cruza 0). El mismo bucket a 30 días vista continúa (mean +13.8%, P(up)=76%, N=25, CI también cruza 0). Tras un año extremo, la continuación del IS no sobrevive OOS (bucket 90–95, h=30: mean −10%, P(up)=14%, N=35).**

Percentiles: IS y FULL usan ventana **expanding** (mín. 120 obs. de R_past). OOS usa umbrales **congelados** en el IS (p50, p75, p90, p95 de R_past IS). No se usa 2021+ para definir cortes históricos.

CI 95% del retorno medio: moving block bootstrap, block = h, 2000 réplicas.

Prioridad: top 10% (90–100) y top 5% (95–100), sample OOS.

### OOS, k=30, h=7

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1271 | 0.15% | -0.02% | 49.9% | [-0.9%, 1.0%] |
| 50-75 | 513 | 0.63% | -0.13% | 49.3% | [-0.6%, 1.8%] |
| 75-90 | 186 | 3.68% | 2.58% | 71.0% | [1.9%, 5.5%] |
| 90-95 | 61 | 1.57% | 1.36% | 55.7% | [-1.6%, 3.6%] |
| 95-100 | 25 | -3.11% | -5.09% | 44.0% | [-12.2%, 2.9%] |

### OOS, k=30, h=30

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1252 | 1.38% | 0.52% | 52.2% | [-2.6%, 5.3%] |
| 50-75 | 509 | 2.12% | -1.29% | 46.2% | [-2.8%, 7.2%] |
| 75-90 | 186 | 7.12% | 4.45% | 65.6% | [1.6%, 12.1%] |
| 90-95 | 61 | 4.85% | 0.78% | 54.1% | [-2.9%, 12.7%] |
| 95-100 | 25 | 13.82% | 7.47% | 76.0% | [-2.3%, 28.0%] |

### OOS, k=90, h=7

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1326 | -0.05% | -0.02% | 49.8% | [-0.9%, 0.8%] |
| 50-75 | 402 | 2.09% | 0.82% | 56.5% | [0.4%, 3.8%] |
| 75-90 | 236 | -0.02% | -0.05% | 49.6% | [-1.5%, 1.5%] |
| 90-95 | 13 | 5.43% | 4.35% | 76.9% | [-1.0%, 15.3%] |
| 95-100 | 79 | 4.76% | 3.94% | 62.0% | [-2.3%, 10.6%] |

### OOS, k=90, h=30

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1303 | 0.59% | -0.17% | 49.6% | [-3.3%, 4.4%] |
| 50-75 | 402 | 7.20% | 7.10% | 61.2% | [0.1%, 13.8%] |
| 75-90 | 236 | -2.69% | -1.55% | 41.9% | [-8.2%, 1.8%] |
| 90-95 | 13 | 2.44% | -2.43% | 15.4% | [-7.4%, 52.4%] |
| 95-100 | 79 | 21.68% | 18.57% | 87.3% | [2.0%, 39.9%] |

### OOS, k=180, h=7

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1451 | 0.85% | 0.55% | 54.4% | [0.0%, 1.7%] |
| 50-75 | 387 | -0.87% | -1.04% | 40.8% | [-2.1%, 0.6%] |
| 75-90 | 100 | 1.90% | 1.74% | 53.0% | [-2.4%, 6.7%] |
| 90-95 | 30 | 3.64% | 5.35% | 63.3% | [-8.4%, 14.6%] |
| 95-100 | 88 | 0.21% | 0.82% | 51.1% | [-3.8%, 4.2%] |

### OOS, k=180, h=30

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1428 | 3.05% | 1.80% | 57.0% | [-0.9%, 6.7%] |
| 50-75 | 387 | -0.79% | -3.59% | 36.4% | [-5.8%, 5.0%] |
| 75-90 | 100 | 5.50% | -2.20% | 45.0% | [-8.5%, 26.4%] |
| 90-95 | 30 | 7.22% | 15.21% | 63.3% | [-35.3%, 40.0%] |
| 95-100 | 88 | -0.42% | -0.58% | 48.9% | [-23.2%, 16.5%] |

### OOS, k=365, h=7

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1226 | 0.20% | 0.11% | 50.9% | [-0.7%, 1.0%] |
| 50-75 | 483 | 1.00% | 0.37% | 52.6% | [-0.2%, 2.3%] |
| 75-90 | 304 | 1.78% | 1.36% | 54.9% | [-1.1%, 4.3%] |
| 90-95 | 35 | -0.65% | -0.22% | 48.6% | [-7.4%, 4.6%] |
| 95-100 | 8 | -4.16% | -3.62% | 25.0% | [-8.9%, 2.6%] |

### OOS, k=365, h=30

| bucket | N | mean | median | P(fut>0) | CI 95% |
|---|---:|---:|---:|---:|---|
| 0-50 | 1203 | 0.75% | 0.43% | 51.6% | [-3.1%, 4.5%] |
| 50-75 | 483 | 4.02% | 1.52% | 54.7% | [-1.2%, 9.6%] |
| 75-90 | 304 | 7.36% | 4.16% | 54.6% | [-6.0%, 19.0%] |
| 90-95 | 35 | -10.04% | -4.25% | 14.3% | [-27.6%, 3.5%] |
| 95-100 | 8 | 4.76% | 4.49% | 75.0% | [-4.8%, 6.2%] |

N del top 5% OOS por (k,h): 25, 25, 79, 79, 88, 88, 8, 8.
P(fut>0) top 5% OOS: 44%, 76%, 62%, 87%, 51%, 49%, 25%, 75%.

---

## 4. ¿Cuál es el efecto más fuerte encontrado?

**Regresión cruda OOS: k=30, h=30, beta=0.1173, t=1.95, p=0.052, FDR=0.414, R²=0.0169, N=2033. El edge de signo no es el efecto fuerte (máximo 2.6 pp en k=365, h=7; los IC block-bootstrap del edge cubren 0). Vol-scaled (paper): k=30, h=30 OOS t≈2.15, p≈0.032 — el más serio, todavía no sobrevive FDR sobre 8 tests.**

---

## 5. ¿Sobrevive out-of-sample?

**El signo de beta sí (7/8 sin cambio IS→OOS). La significancia no (0/8 FDR<0.10; 0/8 p<0.05 en crudo OOS). El lookback de 365 días —el análogo del TSMOM(12,1) del paper— es plano. Los extremos a 12 meses se invierten entre IS (continuación) y OOS (reversión en 90–95). Sobrevive como hipótesis débil solo k=30.**

Clasificación automática por (k,h), usando IS y OOS **juntos** (una señal no es PROMISING si el OOS no acompaña):

| k | h | label |
|---:|---:|---|
| 30 | 7 | WEAK |
| 30 | 30 | PROMISING |
| 90 | 7 | WEAK |
| 90 | 30 | WEAK |
| 180 | 7 | WEAK |
| 180 | 30 | WEAK |
| 365 | 7 | WEAK |
| 365 | 30 | NO EVIDENCE |

Conteo: PROMISING=1, WEAK=6, NO EVIDENCE=1, REVERSAL=0.

Reglas PROMISING (todas): beta IS y OOS > 0, |t_OOS| ≥ 1.64 (~10%), R² OOS ≥ 0.01 o edge ≥ 2 pp, top 10% OOS no peor que el bucket 0–50, y el edge de signo no apunta al lado opuesto. No se usa p<0.05 como criterio único. REVERSAL es el espejo.

---

## 6. ¿Cuál es la magnitud económica del efecto?

**Beta media OOS = 0.026. Edge medio de probabilidad OOS = 0.40 pp (IC típico cubre 0). Lectura de la celda más fuerte: un +100% en 30 días predice ≈+11.7% extra a 30 días (beta=0.117). Eso sería material si fuera estable; R²=1.7% y FDR=0.41 dicen que no lo es. Buy-and-hold OOS (2021-01-01→último close) ≈ +168%. Long/cash parece rentable porque BTC sube y P(R_past>0)≈53–63%; long/short k=30,h=30 OOS cum net ≈ +147% no supera al buy-and-hold. 10 bps/lado no son el cuello de botella a h=30; la señal sí.**

Probabilidad condicional extra (P(fut<0 | past>0) e IC del edge):

| k | h | sample | P(fut<0 \| past>0) | edge CI 95% |
|---:|---:|---|---:|---|
| 30 | 7 | IS | 39.8% | [-0.4%, 5.5%] |
| 30 | 7 | OOS | 46.5% | [-2.0%, 5.1%] |
| 30 | 7 | FULL | 42.8% | [0.2%, 4.6%] |
| 30 | 30 | IS | 37.7% | [-5.4%, 3.4%] |
| 30 | 30 | OOS | 46.9% | [-5.5%, 6.3%] |
| 30 | 30 | FULL | 41.8% | [-3.5%, 4.2%] |
| 90 | 7 | IS | 42.1% | [-2.8%, 3.0%] |
| 90 | 7 | OOS | 47.8% | [-3.4%, 4.1%] |
| 90 | 7 | FULL | 44.6% | [-1.7%, 2.9%] |
| 90 | 30 | IS | 37.1% | [-5.9%, 5.1%] |
| 90 | 30 | OOS | 49.8% | [-9.3%, 4.2%] |
| 90 | 30 | FULL | 42.8% | [-5.0%, 3.9%] |
| 180 | 7 | IS | 42.8% | [-3.7%, 1.5%] |
| 180 | 7 | OOS | 47.8% | [-2.5%, 3.7%] |
| 180 | 7 | FULL | 45.1% | [-2.1%, 2.1%] |
| 180 | 30 | IS | 35.9% | [-4.9%, 5.6%] |
| 180 | 30 | OOS | 50.2% | [-8.5%, 3.7%] |
| 180 | 30 | FULL | 42.5% | [-4.7%, 3.6%] |
| 365 | 7 | IS | 42.9% | [-2.2%, 1.0%] |
| 365 | 7 | OOS | 45.7% | [-0.4%, 5.7%] |
| 365 | 7 | FULL | 44.1% | [-0.4%, 3.0%] |
| 365 | 30 | IS | 38.9% | [-5.2%, 1.5%] |
| 365 | 30 | OOS | 46.1% | [-4.3%, 8.0%] |
| 365 | 30 | FULL | 42.1% | [-2.6%, 4.2%] |

### Traducción mínima a posición (no es un backtest)

Supuestos declarados:

- Spot only, sin derivados ni funding.
- Fee taker **10 bps por lado** (0.20% round-trip). Sin descuento BNB, sin rebate.
- Rebalance **no solapado** cada h días (si se usaran ventanas diarias solapadas se inflaría el N y el PnL).
- Long/cash: BTC si R_past>0, cash si no (retorno 0 en cash).
- Long/short: signo(R_past) × R_future.

| k | h | sample | rule | mean gross | mean net | cum gross | cum net | rebalances |
|---:|---:|---|---|---:|---:|---:|---:|---:|
| 30 | 7 | IS | long_cash | 1.85% | 1.83% | 11632.2% | 10908.4% | 314 |
| 30 | 7 | IS | long_short | 1.64% | 1.60% | 2706.8% | 2371.0% | 314 |
| 30 | 7 | OOS | long_cash | 0.59% | 0.57% | 263.5% | 241.1% | 294 |
| 30 | 7 | OOS | long_short | 0.53% | 0.49% | 78.8% | 57.3% | 294 |
| 30 | 30 | IS | long_cash | 6.23% | 6.18% | 1906.9% | 1827.3% | 74 |
| 30 | 30 | IS | long_short | 2.42% | 2.31% | -125.0% | -123.2% | 74 |
| 30 | 30 | OOS | long_cash | 2.67% | 2.62% | 259.1% | 247.9% | 68 |
| 30 | 30 | OOS | long_short | 2.84% | 2.75% | 163.2% | 146.7% | 68 |
| 90 | 7 | IS | long_cash | 1.89% | 1.88% | 8033.5% | 7796.8% | 306 |
| 90 | 7 | IS | long_short | 1.53% | 1.51% | 1642.1% | 1541.3% | 306 |
| 90 | 7 | OOS | long_cash | 0.43% | 0.42% | 103.8% | 97.1% | 294 |
| 90 | 7 | OOS | long_short | 0.20% | 0.18% | -30.4% | -35.0% | 294 |
| 90 | 30 | IS | long_cash | 8.57% | 8.55% | 3918.0% | 3855.1% | 72 |
| 90 | 30 | IS | long_short | 6.44% | 6.40% | 499.0% | 479.3% | 72 |
| 90 | 30 | OOS | long_cash | 1.37% | 1.35% | 40.0% | 37.7% | 68 |
| 90 | 30 | OOS | long_short | 0.25% | 0.21% | -55.4% | -56.8% | 68 |
| 180 | 7 | IS | long_cash | 1.96% | 1.96% | 8957.4% | 8886.7% | 293 |
| 180 | 7 | IS | long_short | 1.64% | 1.63% | 2227.9% | 2191.6% | 293 |
| 180 | 7 | OOS | long_cash | 0.49% | 0.48% | 140.1% | 135.0% | 294 |
| 180 | 7 | OOS | long_short | 0.32% | 0.30% | -4.7% | -8.8% | 294 |
| 180 | 30 | IS | long_cash | 9.18% | 9.17% | 5552.5% | 5508.7% | 69 |
| 180 | 30 | IS | long_short | 7.19% | 7.17% | 767.0% | 753.5% | 69 |
| 180 | 30 | OOS | long_cash | 1.71% | 1.69% | 90.7% | 88.5% | 68 |
| 180 | 30 | OOS | long_short | 0.93% | 0.90% | -34.3% | -36.0% | 68 |
| 365 | 7 | IS | long_cash | 2.04% | 2.04% | 5001.6% | 4952.8% | 266 |
| 365 | 7 | IS | long_short | 1.75% | 1.74% | 1774.6% | 1738.4% | 266 |
| 365 | 7 | OOS | long_cash | 0.73% | 0.73% | 366.8% | 365.1% | 294 |
| 365 | 7 | OOS | long_short | 0.80% | 0.80% | 300.8% | 297.7% | 294 |
| 365 | 30 | IS | long_cash | 8.42% | 8.41% | 2761.8% | 2745.9% | 63 |
| 365 | 30 | IS | long_short | 6.26% | 6.24% | 481.2% | 474.2% | 63 |
| 365 | 30 | OOS | long_cash | 3.08% | 3.07% | 321.5% | 319.9% | 68 |
| 365 | 30 | OOS | long_short | 3.66% | 3.65% | 382.2% | 378.2% | 68 |

El mean gross/net es el retorno **por tramo de h días**, no anualizado. Cum es producto de (1+r) en esos tramos. Con fees, long/cash a 7 días pierde más por rotación que a 30 días.

---

## 7. ¿Hay suficiente evidencia para profundizar?

**Solo para una segunda prueba acotada, no para construir una estrategia. El vol-scaling ya mejoró k=30. Lo que faltaría: muestreo mensual como el paper, sign(R_past) vs magnitud, y una sola fuente (solo Binance). Si k=30 vol-scaled sigue siendo el único indicio, parar.**

---

## 8. ¿Qué resultados contradicen el paper original?

**El resultado estrella del paper —pasado de 12 meses predice el mes siguiente, en cada instrumento, con t-stats grandes— no aparece en BTC spot: betas k=365 ≈ 0, t<0.3. Tampoco hay reversal lineal post-año dentro de h=7/30. Coincidencias parciales: (i) vol-scaling ayuda, como el paper argumenta; (ii) lookbacks cortos (1 mes) son el único rastro positivo, más cerca del lag 1 de su Figura 1 que de TSMOM(12,1). Diferencias de diseño que importan: un solo spot vs 58 futuros; 2014–2026 vs 1985–2009; drift alcista enorme de BTC (IS +7,587%, OOS +168%) que infla P(up) incondicional y hace que sign(R_past) ≈ estar largo; no hay panel ni cluster por tiempo.**

### Robustez mínima — Experimento 1 con retornos / σ

σ_daily = EWMA de retornos diarios, com=60 (centro de masa del paper), min_periods=30, sin información futura.
R_past_vol = R_past / (σ_daily √k), R_future_vol = R_future / (σ_daily √h).
Misma HAC con lag = h.

| k | h | sample | beta_vol | t_vol | p_vol | R² | N |
|---:|---:|---|---:|---:|---:|---:|---:|
| 30 | 7 | IS | 0.132 | 2.34 | 0.019 | 0.018 | 2196 |
| 30 | 7 | OOS | 0.069 | 1.65 | 0.098 | 0.005 | 2056 |
| 30 | 7 | FULL | 0.110 | 2.98 | 0.003 | 0.013 | 4252 |
| 30 | 30 | IS | 0.163 | 1.89 | 0.059 | 0.019 | 2196 |
| 30 | 30 | OOS | 0.123 | 2.15 | 0.032 | 0.015 | 2033 |
| 30 | 30 | FULL | 0.162 | 2.92 | 0.003 | 0.021 | 4229 |
| 90 | 7 | IS | 0.076 | 1.66 | 0.097 | 0.009 | 2136 |
| 90 | 7 | OOS | 0.036 | 0.96 | 0.337 | 0.002 | 2056 |
| 90 | 7 | FULL | 0.062 | 2.04 | 0.042 | 0.006 | 4192 |
| 90 | 30 | IS | 0.125 | 1.32 | 0.188 | 0.015 | 2136 |
| 90 | 30 | OOS | 0.085 | 1.42 | 0.155 | 0.011 | 2033 |
| 90 | 30 | FULL | 0.121 | 2.15 | 0.031 | 0.017 | 4169 |
| 180 | 7 | IS | 0.042 | 1.14 | 0.254 | 0.004 | 2046 |
| 180 | 7 | OOS | 0.002 | 0.05 | 0.957 | 0.000 | 2056 |
| 180 | 7 | FULL | 0.027 | 1.14 | 0.254 | 0.002 | 4102 |
| 180 | 30 | IS | 0.090 | 1.01 | 0.315 | 0.012 | 2046 |
| 180 | 30 | OOS | 0.005 | 0.09 | 0.928 | 0.000 | 2033 |
| 180 | 30 | FULL | 0.060 | 1.09 | 0.275 | 0.007 | 4079 |
| 365 | 7 | IS | 0.013 | 0.53 | 0.597 | 0.001 | 1861 |
| 365 | 7 | OOS | 0.006 | 0.29 | 0.775 | 0.000 | 2056 |
| 365 | 7 | FULL | 0.015 | 0.88 | 0.379 | 0.001 | 3917 |
| 365 | 30 | IS | 0.015 | 0.28 | 0.782 | 0.001 | 1861 |
| 365 | 30 | OOS | 0.015 | 0.31 | 0.753 | 0.001 | 2033 |
| 365 | 30 | FULL | 0.027 | 0.69 | 0.492 | 0.003 | 3894 |

Si las betas vol-scaled OOS se acercan a cero, el resultado crudo estaba concentrado en ventanas de alta volatilidad.

---

## Recomendación

# B. EVIDENCIA DÉBIL — HACER UNA SEGUNDA PRUEBA

El signo OOS no es ruido puro (casi todas las betas > 0) y hay un indicio en lookbacks cortos, sobre todo vol-scaled. No hay hit FDR, el análogo 12 meses del paper está muerto, y el edge de signo(R_past) es ~0. No justifica infraestructura de trading; sí una segunda prueba acotada (mensual, sign regression, solo Binance).

Qué **no** se hizo (a propósito): ML, indicadores técnicos, funding, OI, liquidaciones, walk-forward, optimización de k/h, backtester, dashboard.

Qué sería una segunda prueba razonable si la recomendación es B: (1) repetir con una sola fuente (solo Binance 2017+) para ver el empalme; (2) horizonte de holding de 1 mes calendario como el TSMOM(12,1) del paper; (3) sign(R_past) en vez de R_past continuo, que es la especificación de trading del paper.
