# Rally temporal map — BTCUSDT 1h, régimen STRONG

Grid fijo: k ∈ [1, 3, 6, 12, 24, 48, 72, 168] h, h ∈ [1, 3, 6, 12, 24, 48] h. 48 combinaciones. Sin búsqueda.
HAC Newey-West, lag = horizonte futuro (cap n/4). FDR BH **dentro de cada sample** (48 tests).
Régimen: p75 < R720 ≤ p90, p75/p90 calculados **solo IS**, congelados.
sigma EWMA horaria com=72 h, solo para robustez X=R_past/(σ√k); Y no se escala.

---

## Datos

- Fuente: Binance BTCUSDT spot, velas 1h, UTC
- Inicio: 2017-08-17 04:00 UTC
- Fin: 2026-08-26 13:00 UTC (última vela horaria **completa**)
- N: 78986
- Timezone: UTC
- Duplicados: 0
- NaN close: 0
- Velas faltantes (no interpoladas): 128
- Primeros huecos: 2017-09-06 17:00, 2017-09-06 18:00, 2017-09-06 19:00, 2017-09-06 20:00, 2017-09-06 21:00, 2017-09-06 22:00, 2018-01-04 04:00, 2018-02-08 01:00, 2018-02-08 02:00, 2018-02-08 03:00, 2018-02-08 04:00, 2018-02-08 05:00

## Régimen STRONG (R720 ≈ 30d)

- p75 IS = 24.49%
- p90 IS = 40.97%
- STRONG: 24.49% < R720 ≤ 40.97%

Horas en STRONG con R720 válido: IS=4298, OOS-1=2649, OOS-2=1243.

## Episodios STRONG (rachas continuas)

| sample | n episodios | dur media (h) | mediana | max | horas STRONG |
|---|---:|---:|---:|---:|---:|
| IS | 224 | 19.2 | 4 | 500 | 4298 |
| OOS-1 | 141 | 18.8 | 5 | 279 | 2649 |
| OOS-2 | 61 | 20.4 | 3 | 173 | 1243 |

300 horas seguidas = 1 episodio, no 300 rallies.

---

## Matrices OOS-2 (validación principal)

### beta

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | 0.008 | -0.034 | -0.025 | -0.046 | -0.030 | 0.127 |
| 3h | -0.015 | -0.037 | -0.025 | -0.035 | -0.017 | 0.123 |
| 6h | -0.002 | -0.002 | 0.001 | -0.014 | 0.032 | 0.174 |
| 12h | 0.001 | 0.011 | 0.017 | 0.037 | 0.046 | 0.189 |
| 24h | 0.001 | 0.007 | 0.014 | 0.010 | 0.085 | 0.228 |
| 48h | 0.008 | 0.023 | 0.042 | 0.077 | 0.160 | 0.204 |
| 72h | 0.007 | 0.021 | 0.034 | 0.052 | 0.091 | 0.134 |
| 168h | 0.005 | 0.013 | 0.021 | 0.036 | 0.074 | 0.107 |

### t-stat

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | 0.22 | -0.51 | -0.31 | -0.46 | -0.21 | 0.47 |
| 3h | -0.68 | -0.79 | -0.36 | -0.36 | -0.13 | 0.44 |
| 6h | -0.13 | -0.07 | 0.02 | -0.17 | 0.25 | 0.61 |
| 12h | 0.13 | 0.49 | 0.41 | 0.56 | 0.42 | 0.79 |
| 24h | 0.13 | 0.46 | 0.49 | 0.20 | 0.88 | 1.18 |
| 48h | 1.51 | 1.71 | 1.67 | 1.60 | 2.03 | 1.67 |
| 72h | 1.80 | 2.04 | 1.83 | 1.46 | 1.44 | 1.35 |
| 168h | 1.82 | 1.89 | 1.70 | 1.53 | 1.71 | 1.53 |

### FDR

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 |
| 3h | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 |
| 6h | 0.939 | 0.966 | 0.981 | 0.939 | 0.939 | 0.939 |
| 12h | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 | 0.939 |
| 24h | 0.939 | 0.939 | 0.939 | 0.939 | 0.911 | 0.600 |
| 48h | 0.417 | 0.417 | 0.417 | 0.417 | 0.417 | 0.417 |
| 72h | 0.417 | 0.417 | 0.417 | 0.424 | 0.424 | 0.473 |
| 168h | 0.417 | 0.417 | 0.417 | 0.417 | 0.417 | 0.417 |

### probability edge  P(up|past>0) − P(up|past<0)

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.068 | -0.074 | -0.037 | -0.028 | -0.029 | -0.055 |
| 3h | -0.078 | -0.068 | -0.056 | -0.037 | -0.028 | -0.043 |
| 6h | -0.080 | -0.056 | -0.077 | -0.032 | -0.026 | -0.023 |
| 12h | -0.070 | -0.003 | -0.051 | -0.025 | -0.030 | -0.066 |
| 24h | -0.038 | -0.044 | -0.057 | -0.041 | -0.093 | -0.057 |
| 48h | -0.046 | -0.059 | -0.093 | -0.021 | 0.000 | 0.043 |
| 72h | -0.002 | 0.027 | 0.004 | 0.063 | 0.088 | 0.028 |
| 168h | -0.027 | -0.014 | 0.012 | 0.018 | 0.069 | 0.119 |

## Matrices OOS-1

### beta

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.000 | 0.028 | -0.004 | 0.005 | -0.268 | -0.225 |
| 3h | -0.003 | 0.020 | -0.035 | -0.033 | -0.295 | -0.296 |
| 6h | -0.009 | -0.019 | -0.060 | -0.047 | -0.287 | -0.307 |
| 12h | -0.001 | 0.003 | -0.009 | -0.073 | -0.268 | -0.294 |
| 24h | -0.011 | -0.032 | -0.074 | -0.143 | -0.221 | -0.266 |
| 48h | -0.007 | -0.020 | -0.048 | -0.098 | -0.154 | -0.167 |
| 72h | -0.003 | -0.012 | -0.031 | -0.056 | -0.087 | -0.105 |
| 168h | -0.003 | -0.008 | -0.017 | -0.032 | -0.051 | -0.062 |

### t-stat

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.01 | 0.60 | -0.07 | 0.06 | -2.81 | -2.23 |
| 3h | -0.21 | 0.50 | -0.83 | -0.40 | -3.18 | -2.74 |
| 6h | -0.62 | -0.64 | -1.18 | -0.50 | -2.96 | -2.47 |
| 12h | -0.13 | 0.12 | -0.22 | -1.08 | -3.37 | -2.43 |
| 24h | -1.64 | -1.98 | -2.75 | -2.99 | -3.72 | -2.95 |
| 48h | -1.56 | -1.82 | -2.53 | -2.95 | -3.76 | -2.97 |
| 72h | -0.94 | -1.41 | -2.25 | -2.26 | -2.37 | -2.30 |
| 168h | -1.53 | -1.79 | -2.33 | -2.38 | -2.56 | -1.81 |

### FDR

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | 0.991 | 0.694 | 0.971 | 0.971 | 0.024 | 0.054 |
| 3h | 0.931 | 0.742 | 0.558 | 0.810 | 0.017 | 0.025 |
| 6h | 0.694 | 0.694 | 0.357 | 0.742 | 0.017 | 0.044 |
| 12h | 0.962 | 0.962 | 0.931 | 0.408 | 0.012 | 0.045 |
| 24h | 0.171 | 0.096 | 0.025 | 0.017 | 0.005 | 0.017 |
| 48h | 0.199 | 0.130 | 0.039 | 0.017 | 0.005 | 0.017 |
| 72h | 0.487 | 0.246 | 0.053 | 0.053 | 0.047 | 0.051 |
| 168h | 0.200 | 0.132 | 0.050 | 0.047 | 0.039 | 0.130 |

### probability edge

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.093 | -0.060 | -0.043 | -0.054 | -0.056 | -0.029 |
| 3h | -0.109 | -0.101 | -0.113 | -0.072 | -0.074 | -0.055 |
| 6h | -0.109 | -0.113 | -0.080 | -0.068 | -0.095 | -0.064 |
| 12h | -0.059 | -0.042 | -0.053 | -0.072 | -0.108 | -0.109 |
| 24h | -0.077 | -0.109 | -0.101 | -0.141 | -0.116 | -0.113 |
| 48h | -0.013 | -0.068 | -0.085 | -0.124 | -0.153 | -0.180 |
| 72h | -0.011 | -0.038 | -0.036 | -0.093 | -0.147 | -0.144 |
| 168h | -0.007 | -0.022 | -0.045 | -0.090 | -0.055 | -0.118 |

## Matrices IS (discovery)

### beta

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.068 | -0.111 | -0.144 | -0.083 | -0.014 | 0.075 |
| 3h | -0.037 | -0.067 | -0.075 | 0.019 | 0.026 | 0.112 |
| 6h | -0.019 | -0.035 | -0.007 | 0.074 | 0.048 | 0.116 |
| 12h | -0.004 | 0.000 | 0.041 | 0.108 | 0.076 | 0.087 |
| 24h | 0.001 | 0.010 | 0.029 | 0.054 | 0.050 | 0.036 |
| 48h | 0.001 | 0.008 | 0.018 | 0.034 | 0.045 | 0.060 |
| 72h | 0.002 | 0.009 | 0.020 | 0.041 | 0.063 | 0.044 |
| 168h | 0.000 | 0.003 | 0.008 | 0.019 | 0.020 | 0.019 |

### t-stat

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -2.85 | -3.48 | -3.39 | -1.22 | -0.17 | 0.79 |
| 3h | -2.76 | -2.59 | -1.95 | 0.29 | 0.31 | 1.14 |
| 6h | -1.87 | -1.63 | -0.21 | 1.32 | 0.62 | 1.19 |
| 12h | -0.55 | 0.01 | 1.54 | 2.62 | 1.14 | 1.03 |
| 24h | 0.20 | 0.85 | 1.54 | 1.65 | 0.83 | 0.50 |
| 48h | 0.29 | 1.09 | 1.36 | 1.53 | 1.15 | 1.05 |
| 72h | 0.79 | 1.54 | 2.04 | 2.25 | 1.91 | 0.83 |
| 168h | 0.11 | 0.78 | 1.22 | 1.72 | 0.95 | 0.59 |

### FDR

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | 0.069 | 0.017 | 0.017 | 0.467 | 0.904 | 0.581 |
| 3h | 0.069 | 0.076 | 0.267 | 0.865 | 0.865 | 0.467 |
| 6h | 0.271 | 0.339 | 0.894 | 0.448 | 0.696 | 0.467 |
| 12h | 0.719 | 0.991 | 0.339 | 0.076 | 0.467 | 0.499 |
| 24h | 0.894 | 0.581 | 0.339 | 0.339 | 0.581 | 0.739 |
| 48h | 0.865 | 0.487 | 0.438 | 0.339 | 0.467 | 0.499 |
| 72h | 0.581 | 0.339 | 0.250 | 0.168 | 0.267 | 0.581 |
| 168h | 0.935 | 0.581 | 0.467 | 0.339 | 0.551 | 0.704 |

### probability edge

| past \ future | 1h | 3h | 6h | 12h | 24h | 48h |
| --- | ---:| ---:| ---:| ---:| ---:| ---: |
| 1h | -0.083 | -0.052 | -0.055 | -0.030 | -0.019 | -0.025 |
| 3h | -0.074 | -0.072 | -0.102 | -0.050 | -0.027 | 0.004 |
| 6h | -0.058 | -0.084 | -0.075 | -0.019 | -0.018 | -0.009 |
| 12h | -0.035 | -0.039 | -0.020 | 0.029 | -0.040 | -0.024 |
| 24h | -0.019 | -0.029 | -0.015 | -0.019 | -0.063 | -0.051 |
| 48h | -0.004 | -0.004 | -0.008 | 0.000 | -0.022 | -0.021 |
| 72h | -0.003 | 0.013 | 0.033 | 0.027 | -0.018 | 0.005 |
| 168h | -0.004 | 0.004 | -0.023 | -0.043 | -0.078 | -0.150 |

---

## Zonas (no celdas)

Celdas con el **mismo signo de beta en IS, OOS-1 y OOS-2**:
- momentum: [(12, 3)]
- reversal: [(1, 6), (1, 24), (3, 1), (3, 6), (6, 1), (6, 3)]

Zonas conexas (vecinas en el grid):
- id=0 signo=- n=3 [(3, 1), (6, 1), (6, 3)]
- id=1 signo=- n=1 [(1, 24)]
- id=2 signo=+ n=1 [(12, 3)]
- id=3 signo=- n=2 [(1, 6), (3, 6)]

Aisladas (no se interpretan como señal): [{'zone_id': 1, 'sign': -1, 'cells': [(1, 24)], 'n_cells': 1}, {'zone_id': 2, 'sign': 1, 'cells': [(12, 3)], 'n_cells': 1}]

Clasificación de la región principal: **NO EVIDENCE**. El único bloque 3-sample es reversal de muy corto plazo y se marca LIKELY OVERLAP ARTIFACT al tomar 1 obs/24h. El bloque visualmente interesante (k=24–168h) cambia de signo entre OOS-1 y OOS-2.

---

## Preguntas

1. ¿Existe momentum horario dentro de rallies STRONG?
**Hay 1 celdas con beta>0 en IS+OOS-1+OOS-2 y 6 con beta<0. Zonas conexas positivas: 1 (aisladas=1). Clasificación de región: NO EVIDENCE.**

2. ¿Cuál parece ser la longitud de memoria de BTC durante un rally?
**Los lookbacks con signo consistente a través de samples son k∈[1, 3, 6] h. Rango aparente de memoria: 1–6 h.**

3. ¿Durante cuánto tiempo futuro persiste esa información?
**El último h con persistencia descriptiva (mismo signo + no microscópico) llega hasta 6h.**

4. ¿Dónde empieza a desaparecer?
**Desaparece cuando k o h salen de la zona conexa (ver matrices OOS-2): lookbacks de 1–3h y/o 168h, y forwards largos, tienden a irse a cero o a cambiar de signo.**

5. ¿Existe alguna zona clara de reversal?
**Celdas con reversal (beta<0 en los tres samples): [(1, 6), (1, 24), (3, 1), (3, 6), (6, 1), (6, 3)]. Hay un bloque de reversal.**

6. ¿Cuál es la región (past k × future h) más consistente?
**Región más grande: zona 0 (3 celdas) [(3, 1), (6, 1), (6, 3)].**

7. ¿Es una región o solamente una celda accidental?
**Hay regiones conexas de reversal (3 y 2 celdas), no de momentum. La única celda de continuación 3-sample es aislada (12h→3h) y no cuenta.**

8. ¿Sobrevive IS → OOS-1 → OOS-2?
**El criterio de zona ya exige IS → OOS-1 → OOS-2 con el mismo signo. 1 celdas lo cumplen en momentum; 6 en reversal.**

9. ¿Sobrevive cuando reducimos el solapamiento a una observación cada 24h?
**- Zona 0 signo=- n=3 celdas [(3, 1), (6, 1), (6, 3)]: 24h → LIKELY OVERLAP ARTIFACT (OOS-2 pierde el signo al 24h)
- Zona 3 signo=- n=2 celdas [(1, 6), (3, 6)]: 24h → LIKELY OVERLAP ARTIFACT (OOS-2 pierde el signo al 24h)**

10. ¿Cuál es la magnitud económica aproximada? (OOS-2, beta × median R_past | STRONG)
**k=3h→h=1h OOS-2: beta=-0.015, median R_past=0.083%, beta×median=-0.001%, edge=-0.078
k=6h→h=1h OOS-2: beta=-0.002, median R_past=0.176%, beta×median=-0.000%, edge=-0.080
k=6h→h=3h OOS-2: beta=-0.002, median R_past=0.176%, beta×median=-0.000%, edge=-0.056**

11. ¿Qué sobrevive volatility scaling (solo X, Y crudo)?
**zona 0: 67% celdas OOS-2 conservan signo; zona 3: 100% celdas OOS-2 conservan signo**

12. ¿Hay evidencia suficiente para pasar a una fase de timing de entradas?
**No. Hace falta una zona A que sobreviva 24h y magnitud no trivial.**

---

## En español sencillo

Dentro de rallies fuertes (subida de ~30 días entre p75 y p90), las horas recientes de BTC no muestran una escala temporal estable que se repita en 2017–2020, 2021–2023 y 2024–ahora. No hay un bloque de lookbacks/horizontes con el mismo signo en los tres periodos que además aguante al mirar un dato cada 24 horas. No justifica pasar a timing de entradas.

---

## Decisión

# C — NO USEFUL TEMPORAL STRUCTURE

Dentro de rallies STRONG no hay una escala k×h de continuación que se repita en IS, OOS-1 y OOS-2. OOS-1 es reversal (FDR<0.10 en k=24–48h); OOS-2 es continuación débil en k=48–168h (FDR~0.42). El único bloque 3-sample es reversal 1–6h, económicamente microscópico y overlap artifact.
