# Segunda prueba — BTC momentum 30d y extremos

Confirmatorio, no exploratorio. Solo Binance BTCUSDT. Sin backtest.
Seed 42. Bootstrap 2000 réplicas. HAC daily lag=30, monthly lag=1.
FDR Benjamini-Hochberg **solo** sobre los 3 PRIMARY OOS.
PRIMARY = 3 tests OOS predefinidos. Mensual y extremos son SECONDARY. No se mezclan 30 tests secundarios en el FDR.

---

## Datos

- Fuente: Binance BTCUSDT spot 1d UTC (binance_api)
- Primera fecha: 2017-08-17
- Última fecha: 2026-08-25 (última vela UTC completa)
- N: 3296
- Timezone: UTC
- Duplicados: 0
- NaN: 0
- Días faltantes (no interpolados): 0 (ninguno)
- IS: 2017-08-17 → 2020-12-31 (señal t)
- OOS: 2021-01-01 → 2026-08-25 (prioridad)

## Thresholds IS de R30_past (congelados para OOS)

- p50 = 2.84%
- p75 = 24.43%  → STRONG empieza aquí
- p90 = 41.07%  → VERY STRONG
- p95 = 53.50%  → EXTREME por encima

Buckets: NORMAL/POSITIVE 50–75 · STRONG 75–90 · VERY STRONG 90–95 · EXTREME >p95.

---

## PRIMARY tests

| group | spec | sample | beta | SE | t | p | FDR | R² | N |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| PRIMARY | H1A_continuous | IS | 0.1301 | 0.1273 | 1.02 | 0.307 | NA | 0.0153 | 1203 |
| PRIMARY | H1A_continuous | OOS | 0.1173 | 0.0603 | 1.95 | 0.052 | 0.078 | 0.0169 | 2033 |
| PRIMARY | H1B_sign | IS | 0.0443 | 0.0301 | 1.47 | 0.141 | NA | 0.0220 | 1203 |
| PRIMARY | H1B_sign | OOS | 0.0154 | 0.0122 | 1.27 | 0.206 | 0.206 | 0.0082 | 2033 |
| PRIMARY | H1C_volscaled | IS | 0.3011 | 0.1278 | 2.36 | 0.018 | NA | 0.0606 | 1203 |
| PRIMARY | H1C_volscaled | OOS | 0.1229 | 0.0572 | 2.15 | 0.032 | 0.078 | 0.0151 | 2033 |

H1B — expectativas condicionales:

| sample | E[fut\|past>0] | E[fut\|past<0] | P(up\|past>0) | P(up\|past<0) | N+ | N− |
|---|---:|---:|---:|---:|---:|---:|
| IS | 12.96% | 4.11% | 58.1% | 56.4% | 669 | 534 |
| OOS | 3.81% | 0.73% | 53.1% | 51.3% | 1068 | 965 |

## SECONDARY — mensual (fin de mes, no solapado)

| group | spec | sample | beta | SE | t | p | FDR | R² | N |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| SECONDARY | monthly_continuous | IS | 0.2327 | 0.1542 | 1.51 | 0.131 | NA | 0.0546 | 40 |
| SECONDARY | monthly_continuous | OOS | 0.1062 | 0.1005 | 1.06 | 0.291 | NA | 0.0114 | 66 |
| SECONDARY | monthly_sign | IS | 0.0215 | 0.0414 | 0.52 | 0.603 | NA | 0.0077 | 40 |
| SECONDARY | monthly_sign | OOS | 0.0246 | 0.0217 | 1.13 | 0.257 | NA | 0.0213 | 66 |

N mensual es pequeño a propósito (un obs. por mes). Un t bajo aquí no es el mismo listón que el diario solapado.

## SECONDARY — extremos rolling (R30_past, umbrales IS)

### OOS, h=7

| bucket | N | mean | median | P(>0) | P(<0) | CI30 | CI60 | CI90 |
|---|---:|---:|---:|---:|---:|---|---|---|
| NORMAL_POSITIVE | 654 | 0.71% | 0.05% | 50.6% | 49.4% | [-0.51%, 2.04%] | [-0.65%, 1.77%] | [-0.66%, 1.70%] |
| STRONG | 168 | 3.94% | 2.64% | 73.8% | 26.2% | [2.12%, 6.10%] | [1.91%, 5.93%] | [2.02%, 5.62%] |
| VERY_STRONG | 48 | 1.45% | -0.57% | 47.9% | 52.1% | [-2.12%, 3.18%] | [-1.89%, 2.82%] | [-1.88%, 2.62%] |
| EXTREME | 28 | -3.08% | -2.91% | 46.4% | 53.6% | [-12.72%, 6.26%] | [-12.60%, 6.26%] | [-12.60%, 6.26%] |

### OOS, h=30

| bucket | N | mean | median | P(>0) | P(<0) | CI30 | CI60 | CI90 |
|---|---:|---:|---:|---:|---:|---|---|---|
| NORMAL_POSITIVE | 648 | 2.28% | -0.49% | 47.8% | 52.2% | [-2.35%, 7.15%] | [-3.03%, 6.84%] | [-3.22%, 6.95%] |
| STRONG | 168 | 7.80% | 5.55% | 66.7% | 33.3% | [2.48%, 12.86%] | [1.37%, 11.98%] | [1.62%, 11.37%] |
| VERY_STRONG | 48 | 3.90% | -0.07% | 50.0% | 50.0% | [-4.48%, 11.16%] | [-5.67%, 10.63%] | [-5.81%, 9.38%] |
| EXTREME | 28 | 14.30% | 8.14% | 78.6% | 21.4% | [0.08%, 30.45%] | [0.31%, 18.63%] | [0.31%, 18.00%] |

### IS, h=7

| bucket | N | mean | median | P(>0) | P(<0) | CI30 | CI60 | CI90 |
|---|---:|---:|---:|---:|---:|---|---|---|
| NORMAL_POSITIVE | 300 | 3.56% | 1.69% | 59.7% | 40.3% | [0.19%, 6.57%] | [-0.35%, 6.49%] | [-0.50%, 6.24%] |
| STRONG | 180 | 3.59% | 2.82% | 64.4% | 35.6% | [0.56%, 6.00%] | [-0.23%, 5.82%] | [-0.83%, 5.23%] |
| VERY_STRONG | 60 | 5.17% | 4.63% | 60.0% | 40.0% | [-2.20%, 11.01%] | [-4.57%, 12.69%] | [-7.14%, 12.33%] |
| EXTREME | 61 | 3.45% | 1.29% | 52.5% | 47.5% | [-6.39%, 12.60%] | [-9.23%, 8.63%] | [-9.69%, 8.50%] |

### IS, h=30

| bucket | N | mean | median | P(>0) | P(<0) | CI30 | CI60 | CI90 |
|---|---:|---:|---:|---:|---:|---|---|---|
| NORMAL_POSITIVE | 300 | 9.87% | 2.20% | 53.7% | 46.3% | [-1.61%, 20.01%] | [-4.19%, 18.53%] | [-5.41%, 17.23%] |
| STRONG | 180 | 19.92% | 13.83% | 63.9% | 36.1% | [1.38%, 35.37%] | [-1.56%, 35.31%] | [-5.25%, 30.30%] |
| VERY_STRONG | 60 | 23.18% | 23.18% | 73.3% | 26.7% | [1.56%, 43.00%] | [-3.67%, 43.80%] | [-8.88%, 42.39%] |
| EXTREME | 61 | 15.53% | 21.74% | 67.2% | 32.8% | [-6.67%, 40.60%] | [-8.37%, 38.19%] | [-14.58%, 27.18%] |

Una conclusión de cola que **solo** aparece con block=30 y se rompe en 60/90 se marca NO ROBUSTA.

## SECONDARY — eventos no solapados (cooldown 30 días)

### OOS

| bucket | h | N eventos | mean | median | P(>0) |
|---|---:|---:|---:|---:|---:|
| EXTREME | 7 | 4 | 3.29% | 2.90% | 75.0% |
| EXTREME | 30 | 4 | 1.68% | 2.93% | 75.0% |
| NORMAL_POSITIVE | 7 | 47 | 2.34% | 1.35% | 61.7% |
| NORMAL_POSITIVE | 30 | 46 | 4.49% | 2.04% | 58.7% |
| STRONG | 7 | 15 | 4.39% | 3.36% | 80.0% |
| STRONG | 30 | 15 | 12.79% | 6.36% | 73.3% |
| VERY_STRONG | 7 | 8 | 3.05% | -1.71% | 37.5% |
| VERY_STRONG | 30 | 8 | 1.23% | -1.79% | 37.5% |

### IS

| bucket | h | N eventos | mean | median | P(>0) |
|---|---:|---:|---:|---:|---:|
| EXTREME | 7 | 7 | 5.56% | 2.64% | 71.4% |
| EXTREME | 30 | 7 | 15.18% | 10.15% | 71.4% |
| NORMAL_POSITIVE | 7 | 29 | 3.27% | 2.67% | 55.2% |
| NORMAL_POSITIVE | 30 | 29 | 10.60% | 3.29% | 51.7% |
| STRONG | 7 | 16 | 7.08% | 5.22% | 75.0% |
| STRONG | 30 | 16 | 16.54% | 12.95% | 68.8% |
| VERY_STRONG | 7 | 11 | 2.11% | 4.50% | 54.5% |
| VERY_STRONG | 30 | 11 | 4.58% | 2.85% | 54.5% |

---

## Respuestas

1. ¿Se replica el momentum 30d→30d usando solo Binance?
**Parcialmente. H1A OOS beta=0.117, t=1.95, p=0.052, FDR=0.078, R²=0.0169, N=2033. IS beta=0.130, t=1.02. El empalme Bitstamp no era el driver del OOS (OOS 2021+ ya era Binance).**

2. ¿Sobrevive OOS?
**Sí el signo (IS y OOS beta>0). La significancia OOS es límite (p=0.052, FDR=0.078).**

3. ¿Qué ocurre con sign(Rpast)?
**H1B OOS beta=0.0154, t=1.27, p=0.206, R²=0.0082. E[fut|past>0]=3.81% vs E[fut|past<0]=0.73%. P(up|past>0)=53.1% vs P(up|past<0)=51.3%. El signo del mes pasado es una señal más débil que la magnitud continua.**

4. ¿Qué ocurre al ajustar por volatilidad?
**H1C OOS t=2.15, p=0.032, FDR=0.078, beta=0.123. IS t=2.36. El vol-scaling refuerza el indicio (como en la primera prueba).**

5. ¿Sobrevive usando observaciones mensuales?
**Mensual continuo: IS beta=0.233, t=1.51, N=40; OOS beta=0.106, t=1.06, N=66. Mensual sign: OOS t=1.13. Mismo signo que el diario, pero N mensual es pequeño y el t no confirma.**

6. ¿Los rallies fuertes continúan?
**STRONG (75–90) OOS h=30: mean=7.80%, N=168, CI>0 en 30/60/90.**

7. ¿Los rallies EXTREMOS se comportan distinto?
**Sí, de forma descriptiva, no como reversal robusto. VERY STRONG (p90–p95) es un limbo: OOS h=30 mean=3.90%, median≈0, CI cubre 0. EXTREME rolling h=7 mean=-3.08% (aparente reversal) pero CI cubre 0 en 30/60/90. EXTREME rolling h=30 mean=14.30% (aparente continuación, CI>0 en 30/60/90). El salto STRONG vs EXTREME no es monótono: STRONG > VERY STRONG, y EXTREME cambia de signo entre h=7 y h=30 en la versión rolling.**

8. ¿Los resultados extremos sobreviven block lengths 30/60/90?
**STRONG h=7 y h=30: CI>0 en 30/60/90 (robusto). VERY STRONG: CI cubre 0 en los tres. EXTREME h=30: CI>0 en 30/60/90 (el bound inferior está pegado a 0: ~0.1–0.3 pp). EXTREME h=7: CI cubre 0 en 30/60/90 — el reversal de 7d de la primera prueba **no es robusto** ni siquiera a block=30 con umbrales IS congelados.**

9. ¿Sobreviven cuando agrupamos episodios extremos y evitamos contar clusters?
**EXTREME OOS clustered N=4 eventos (vs 28 días rolling). h=7 clustered mean=3.29% (rolling era negativo: el reversal 7d era cluster). h=30 clustered mean=1.68% (rolling +14.3% se cae a ~+1.7%). STRONG clustered N=15, h=30 mean=12.79% (sigue positivo). Conclusión: la cola EXTREME rolling no es un conjunto de episodios independientes.**

10. ¿Qué hipótesis queda viva?
**H1 magnitud 30d→30d (débil, FDR 0.078); H1 vol-scaled 30d (el primary más serio; FDR 0.078); H1 sign: muerta; H2 STRONG continúa (robusto a block 30/60/90 y a de-cluster N=15); H2 EXTREME distinto de STRONG: no confirmado (N clustered=4; 7d reversal no robusto)**

---

## Decisión

# B — INTERESTING BUT WEAK

H1 no desaparece con solo Binance: IS y OOS beta>0, vol-scaling OOS t=2.15 p=0.032 FDR=0.078. Eso no basta para A: FDR no baja de 0.05, sign(Rpast) es nulo, el mensual conserva el signo pero t≈1, y H1A IS es débil (t=1.02). H2: STRONG continúa OOS (CI>0 en 30/60/90 y N=15 eventos). EXTREME 7d reversal y EXTREME 30d continuation rolling no sobreviven al de-cluster (N=4).
