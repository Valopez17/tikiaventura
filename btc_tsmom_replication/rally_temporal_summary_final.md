# Micro-auditoría Fase 3 — validación OOS estricta

Dataset: `btcusdt_1h.csv` (sin redescarga). Thresholds, grid, STRONG, HAC y FDR 48 **sin cambios**.
Correcciones: (1) `sample(t)==sample(t+h)`; (2) zonas congeladas con **IS+OOS-1**; OOS-2 no selecciona.

---

## Datos (idénticos)

- 2017-08-17 04:00 → 2026-08-26 13:00 UTC · N=78986 · missing=128 · dup=0
- p75 IS R720 = 24.49% · p90 = 40.97%
- STRONG horas: IS=4298, OOS-1=2649, OOS-2=1243
- Filas extra excluidas por frontera t+h (suma sobre 8×6; una fila puede contar en varios h): IS: 0, OOS-1: 0, OOS-2: 0

Episodios STRONG (igual definición):

| sample | n | dur media | mediana | max |
|---|---:|---:|---:|---:|
| IS | 224 | 19.2 | 4 | 500 |
| OOS-1 | 141 | 18.8 | 5 | 279 |
| OOS-2 | 61 | 20.4 | 3 | 173 |

---

## Matrices OOS-2 (solo evaluación; no se usaron para elegir zonas)

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

### probability edge
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

## Matrices OOS-1 (discovery / freeze)

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

---

## Zonas congeladas (IS + OOS-1 only)

Selección: mismo signo de beta en IS y OOS-1; regiones 4-conectadas; **solo n≥2 celdas**.
Celdas aisladas no se promocionan. OOS-2 no entra aquí.

Zonas conexas (≥2 celdas) con el mismo signo IS y OOS-1 (congeladas, sin OOS-2):
- id=0 signo=- [(1, 1), (1, 6), (3, 1), (3, 6), (6, 1), (6, 3), (6, 6), (12, 1)]
Celdas aisladas IS+OOS-1 (no seleccionadas): [(1, 24), (12, 3)]

---

## Validación OOS-2 (sin re-seleccionar)

- Zona 0 signo=- n=8 [(1, 1), (1, 6), (3, 1), (3, 6), (6, 1), (6, 3), (6, 6), (12, 1)]: **FAILED FINAL OOS**
  1h→1h: beta=0.0077 t=0.22 p=0.829 FDR=0.939 R²=0.0001 edge=-0.068 E[fut|+]=0.015% E[fut|-]=0.043% econ=0.000% signo=FAIL
    24h OOS-2: beta=0.0985 t=1.47 N=98 PIERDE SIGNO; edge cambia/NA
  1h→6h: beta=-0.0255 t=-0.31 p=0.759 FDR=0.939 R²=0.0001 edge=-0.037 E[fut|+]=0.152% E[fut|-]=0.205% econ=-0.001% signo=OK
    24h OOS-2: beta=0.1810 t=1.04 N=98 PIERDE SIGNO; edge cambia/NA
  3h→1h: beta=-0.0153 t=-0.68 p=0.494 FDR=0.939 R²=0.0008 edge=-0.078 E[fut|+]=0.011% E[fut|-]=0.049% econ=-0.001% signo=OK
    24h OOS-2: beta=0.0186 t=0.37 N=98 PIERDE SIGNO; edge misma dirección
  3h→6h: beta=-0.0254 t=-0.36 p=0.719 FDR=0.939 R²=0.0004 edge=-0.056 E[fut|+]=0.143% E[fut|-]=0.217% econ=-0.002% signo=OK
    24h OOS-2: beta=0.1980 t=1.41 N=98 PIERDE SIGNO; edge misma dirección
  6h→1h: beta=-0.0019 t=-0.13 p=0.897 FDR=0.939 R²=0.0000 edge=-0.080 E[fut|+]=0.011% E[fut|-]=0.051% econ=-0.000% signo=OK
    24h OOS-2: beta=0.0084 t=0.17 N=98 PIERDE SIGNO; edge misma dirección
  6h→3h: beta=-0.0023 t=-0.07 p=0.946 FDR=0.966 R²=0.0000 edge=-0.056 E[fut|+]=0.083% E[fut|-]=0.111% econ=-0.000% signo=OK
    24h OOS-2: beta=0.0019 t=0.02 N=98 PIERDE SIGNO; edge misma dirección
  6h→6h: beta=0.0014 t=0.02 p=0.981 FDR=0.981 R²=0.0000 edge=-0.077 E[fut|+]=0.154% E[fut|-]=0.208% econ=0.000% signo=FAIL
    24h OOS-2: beta=0.0889 t=0.67 N=98 PIERDE SIGNO; edge misma dirección
  12h→1h: beta=0.0013 t=0.13 p=0.894 FDR=0.939 R²=0.0000 edge=-0.070 E[fut|+]=0.028% E[fut|-]=0.028% econ=0.000% signo=FAIL
    24h OOS-2: beta=0.0170 t=0.53 N=98 PIERDE SIGNO; edge misma dirección

---

## Preguntas

1. ¿Cambian materialmente los coeficientes después de eliminar cross-boundary observations?
**Comparadas 144 celdas con el mapa previo. |Δbeta|>5% relativo en 0/ 144. Obs. STRONG extra excluidas por sample(t)≠sample(t+h): IS=0, OOS-1=0, OOS-2=0 (0 = no había régimen STRONG en el borde temporal de cada sample).**

2. ¿Cambian los signos?
**Cambios de signo vs mapa previo: 0 / 144.**

3. ¿Cambian las conclusiones FDR?
**Celdas que cruzan FDR 0.10 vs mapa previo: 0 / 144.**

4. ¿Qué zonas se seleccionan usando exclusivamente IS+OOS-1?
**Ver bloque de zonas congeladas arriba.**

5. ¿Cuáles sobreviven OOS-2?
**0 sobreviven, 1 FAILED FINAL OOS. No se sustituyó ninguna.**

6. ¿Alguna zona sobrevive también al subsample 24h?
**0 zona(s) conservan signo OOS-2 en el subsample 24h.**

7. ¿Existe momentum estable?
**No. No hay zona de continuación congelada que sobreviva OOS-2.**

8. ¿Existe reversal estable?
**No de forma útil (falla OOS-2 y/o 24h).**

9. ¿El resultado anterior era afectado materialmente por post-selection?
**La corrección de post-selection impide promover el bloque k=48–168h de OOS-2, que no era candidato en IS+OOS-1. Eso era el riesgo de la fase anterior.**

10. ¿Se mantiene o cambia la decisión final?
**Decisión: C — NO USEFUL TEMPORAL STRUCTURE.**

---

## Decisión

# C — NO USEFUL TEMPORAL STRUCTURE

Tras vetar futuros cross-boundary y congelar zonas con IS+OOS-1, ninguna región sobrevive la validación final OOS-2 de forma útil (signo, 24h y magnitud). No se sustituyeron zonas por otras que lucieran mejor en OOS-2.
