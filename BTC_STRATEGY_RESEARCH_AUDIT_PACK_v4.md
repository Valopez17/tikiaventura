# BTC Strategy Research OS — Rector de descubrimiento

**v4.0 · 2026-09-02 · propuesta para aprobación · rector transitorio de un solo archivo**

## Estado y autoridad

Este archivo está propuesto para sustituir operativamente a BTC_STRATEGY_RESEARCH_AUDIT_PACK_v3.md. Entra en vigor cuando Valita apruebe v4; hasta entonces es un draft completo de migración.

Las versiones v1, v2 y v3 no se borran ni se reescriben: son evidencia histórica. No tienen autoridad normativa sobre trabajo nuevo. En particular, ningún contrato de alertas de v2 sigue activo por referencia implícita. Cuando el proyecto llegue a alertas paper se creará un North Star de producto nuevo.

v4 corrige cinco problemas de arquitectura:

1. El proyecto todavía está descubriendo qué alertas podrían servir, no construyendo el motor.
2. Un scan exploratorio no es una prueba confirmatoria.
3. Evidencia, estado de vida y freeze son dimensiones distintas.
4. Un hash identifica un archivo, pero no vuelve reproducible una corrida.
5. ChatGPT diseña y recomienda; Cursor ejecuta y reporta; Valita decide.

Este documento es transitorio: concentra las reglas mientras se crea la estructura canónica del repositorio. Después de la migración, permanecerá como índice y North Star del proyecto BTC; el protocolo común, los registros y los experimentos vivirán en archivos separados.

## Mapa del documento

| Sección | Autoridad | Contenido |
|---|---|---|
| §0 North Star | Valita aprueba; ChatGPT propone | Misión, utilidad, alcance, éxito y prohibiciones |
| §1 Modelo operativo | Valita / ChatGPT | Objetos, estados, tipos de experimento y autoridad |
| §2 Descubrimiento | ChatGPT propone; Valita prioriza | Cómo nacen, se registran y se eligen hipótesis |
| §3 Protocolo de research | ChatGPT mantiene; Cursor obedece | Datos, tests, tiempo, costos, métricas, selección y promoción |
| §4 Contrato de IA | Valita / ChatGPT | Handoff ChatGPT → Cursor, tareas atómicas y receipts |
| §5 Evidencia heredada | No reescribir resultados históricos | Calendar, Extreme, Breakout y Vol reclassificados |
| §6 Estado, decisiones y errores | Cursor reporta; ChatGPT interpreta | Snapshot, decisiones, errores y reglas permanentes |
| §7 Roadmap | Valita nombra el siguiente paso | Orden atómico del trabajo |
| §8 Etapa futura | Sin ejecución hoy | Freeze, paper alerts y eventual motor |
| Apéndices | Plantillas | Hipótesis, spec, task packet, manifest, receipt y error |

## Jerarquía de autoridad

En caso de conflicto, manda el elemento superior:

1. Rector global de operación, cuando exista.
2. §0 y §1 de este North Star.
3. Protocolo de research aprobado.
4. Spec de experimento aprobada y hasheada.
5. Task packet nombrado.
6. Artefactos machine-generated del run.
7. Resumen narrativo de un modelo.

Un resumen de ChatGPT o Cursor nunca corrige silenciosamente una spec, un CSV o un resultado. Si dos niveles chocan, el trabajo se detiene y se registra el blocker.

---

# §0 North Star

## 0.1 Misión

Construir un proceso de investigación auditable que permita a Valita:

- entender qué tipos de alertas de trading cripto existen;
- convertir ideas en hipótesis falsificables;
- probar una hipótesis a la vez sin consumir el futuro en silencio;
- descartar rápidamente lo débil;
- identificar qué reglas merecen freeze y observación prospectiva;
- aprender de cada error con trazabilidad completa.

El objetivo actual no es encontrar una estrategia ganadora. Es construir una fábrica confiable para producir y rechazar hipótesis.

## 0.2 Cadena de esta etapa

Fuente o intuición → idea registrada → utilidad declarada → hipótesis → spec aprobada → run reproducible → control + incertidumbre → decisión

Decisiones permitidas:

- DESCARTAR
- INSUFICIENTE
- PROFUNDIZAR
- FREEZE PARA PROSPECTIVO

Ninguna de esas palabras significa PROBADA.

## 0.3 Cadena futura

Regla frozen → stopping plan → observación con datos posteriores al freeze → alertas paper → bitácora prospectiva → revisión humana → mucho después, posible capital pequeño

## 0.4 Qué significa “alerta útil”

Una alerta solo es útil si apoya una decisión concreta. Antes de investigar una hipótesis se declara:

- quién la leerá;
- qué decisión apoya;
- qué acción podría provocar;
- horizonte;
- tiempo disponible para reaccionar;
- frecuencia tolerable;
- costo de falsa alarma;
- costo de omisión;
- qué resultado la vuelve inútil.

Tipos permitidos en el mapa de descubrimiento:

| Tipo | Pregunta |
|---|---|
| Trade trigger | ¿Existe una entrada o salida definida con expectativa neta? |
| Risk alert | ¿Aumentó de forma medible el riesgo de un movimiento adverso? |
| Regime/context | ¿Cambió una condición que modifica cómo leer otras señales? |
| Setup temprano | ¿Se está formando una condición que puede convertirse en trigger? |
| Research-only | ¿Existe un fenómeno histórico que aún no es accionable? |
| Data/system | ¿La información está incompleta, retrasada o inconsistente? |

No todos los tipos requieren una estrategia completa. Un trade trigger sí exige señal, entrada, salida, costos y PnL. Una alerta de riesgo exige target adverso, base rate, lead time, cobertura y falsas alarmas.

## 0.5 Definición de éxito de la fase de descubrimiento

La fase es utilizable cuando puede hacer lo siguiente consistentemente:

1. Registrar el origen y la utilidad de cada idea.
2. Formular una hipótesis falsificable.
3. Aprobar una spec antes de ver el resultado.
4. Reproducir un run desde datos, código, configuración y comando exactos.
5. Conservar todos los intentos y selecciones.
6. Medir efecto, incertidumbre, costos y control apropiado.
7. Emitir una decisión inequívoca sin retunear.
8. Convertir errores materiales en reglas y tests.
9. Permitir que Valita explique la regla, el control y el failure mode principal.
10. Funcionar sin memoria implícita de ChatGPT o Cursor.

## 0.6 Alcance activo

### Landscape documental

Puede catalogar, sin implementar, familias basadas en:

- precio y volumen;
- calendario y eventos;
- volatilidad;
- microestructura;
- derivados;
- cross-exchange;
- on-chain;
- macro y atención.

Catalogar no significa aprobar ni abrir un proyecto.

### Research computacional

Congelado hasta que una decisión lo cambie:

| Sí | No |
|---|---|
| BTCUSDT spot, Binance, 1h | Otras monedas |
| Datos históricos cerrados | Vela abierta |
| Price-based research | Funding, futures, options, on-chain |
| LONG ejecutable | Shorts operativos |
| Estudios SHORT claramente teóricos | Borrow, funding, liquidaciones |
| Una hipótesis o un fix por tarea | Familias combinadas |
| Capital simulado | Capital real |

## 0.7 No objetivos

- Predecir cada movimiento de BTC.
- Maximizar Sharpe in-sample.
- Encontrar “la mejor” de miles de reglas y llamarla edge.
- Construir el bot.
- Elegir Telegram, WhatsApp o dashboard.
- Añadir indicadores para rescatar una idea.
- Construir infraestructura para monedas que aún no son parte del proyecto.
- Operar con leverage.
- Convertir research-only en recomendación.

## 0.8 Guardrails permanentes

- Capital real = 0 durante este rector.
- El historial ya observado nunca vuelve a ser clean OOS.
- Predeclarar un scan no elimina multiple testing.
- Un scan genera hipótesis; no confirma su ganador.
- Todo cambio post-resultado crea nueva versión y nuevo registro de selección.
- Si falta un artefacto obligatorio, el run no existe.
- Si hay un bug material, el resultado queda INVALIDATED; no “provisionalmente bueno”.
- Ningún modelo transcribe manualmente números como fuente canónica.
- No se borran runs, ideas, errores ni decisiones.
- No se sobreescriben outputs de runs previos.
- Una tarea de Cursor tiene un solo delta conductual.
- Valita puede detener cualquier línea de investigación sin justificar sunk cost.

---

# §1 Modelo operativo

## 1.1 Objetos canónicos

| Objeto | ID ejemplo | Definición |
|---|---|---|
| Idea | IDEA-BTC-001 | Posible fenómeno; todavía puede ser vaga |
| Hipótesis | HYP-BTC-001 | Afirmación falsificable con observable, target y control |
| Experimento | EXP-BTC-001 | Spec predeclarada que prueba una hipótesis |
| Run | RUN-BTC-001-20260902-01 | Ejecución concreta con inputs y outputs inmutables |
| Finding | FIND-BTC-001 | Resultado descriptivo de uno o más runs |
| Rule candidate | RULE-BTC-001 | Lógica completa y determinista |
| Frozen rule | RULE-BTC-001-v1 | Versión inmutable desde freeze_date y dataset_hash |
| Alert instance | ALERT-BTC-... | Ocurrencia prospectiva de una frozen rule |
| Decision | DEC-001 | Aprobación, descarte, freeze o cambio de alcance |
| Error | E-XX | Falla, causa, impacto, arreglo y prevención |
| Task | TASK-... | Delta atómico autorizado para Cursor |

Una familia no es un candidato. Un run no es una estrategia. Un finding no es una alerta.

## 1.2 Tipo de experimento

Cada spec declara exactamente uno:

| Tipo | Propósito | Claim máximo permitido |
|---|---|---|
| LANDSCAPE | Mapear fuentes y familias | “Existe una idea investigable” |
| SCAN | Explorar un search space predeclarado | “Este scan generó candidatos” |
| CONFIRMATORY | Probar una regla fijada antes del bloque evaluado | “La regla sobrevivió esta prueba histórica” |
| ROBUSTNESS | Intentar romper una candidata sin retunearla | “No falló estos falsification checks” |
| PROSPECTIVE | Observar datos inexistentes al freeze | “Cumplió o no el stopping plan prospectivo” |
| REPRODUCTION | Replicar un resultado sin cambiar lógica | “El resultado es o no reproducible” |

Un SCAN jamás salta directamente a “validada”. Su salida es una nueva hipótesis o una rule candidate explícitamente selection-contaminated.

## 1.3 Nivel de evidencia

Evidence level y lifecycle status son campos separados.

| Nivel | Nombre | Requisito |
|---|---|---|
| L0 | IDEA | Idea registrada; cero valor operativo |
| L1 | SPECIFIED | Hipótesis, utilidad, control y spec aprobados antes del run |
| L2 | CALCULATED | Código, outputs, trade/event log y métricas existen |
| L3 | AUDITABLE | Datos, manifest, tests, hashes y reproducción suficiente |
| L4 | HISTORICAL ASSESSED | Selección, trials, controles, incertidumbre y robustez histórica evaluados |
| L5 | PROSPECTIVE | Datos posteriores al freeze cumplen el stopping plan |

L4 no significa prueba definitiva. L5 tampoco autoriza capital automáticamente.

## 1.4 Lifecycle status

Valores permitidos:

- BACKLOG
- ACTIVE
- BLOCKED
- INVALIDATED
- INSUFFICIENT
- DISCARDED
- DEEPEN
- FROZEN
- PROSPECTIVE_MONITORING
- RETIRED

Freeze status:

- UNFROZEN
- FROZEN

Una regla puede congelarse con evidencia histórica contaminada para empezar un test prospectivo. En ese caso conserva su nivel real y selection_contaminated = true. Freeze no blanquea el pasado.

## 1.5 Tres resultados diferentes

| Resultado | Lo produce | Autoridad |
|---|---|---|
| Métricas | Código | Machine-generated |
| Mechanical gate | Cursor aplica literalmente la spec | PASS / FAIL / INSUFFICIENT / BLOCKED |
| Decisión de research | ChatGPT recomienda; Valita aprueba | DESCARTAR / PROFUNDIZAR / FREEZE |

Cursor no decide que algo es prometedor.

## 1.6 Cambios post-resultado

Después de conocer resultados:

- no se modifica la spec original;
- no se sustituye el run;
- no se cambia el control;
- no se cambia un threshold para rescatar la idea;
- cualquier variante recibe nueva hypothesis_version, experiment_id y selection note;
- el resultado anterior permanece visible.

---

# §2 Descubrimiento

## 2.1 Entrada de ideas

Fuentes permitidas:

1. Pregunta o intuición de Valita.
2. Paper o working paper primario.
3. Documentación oficial de exchange o data provider.
4. Análisis público con código reproducible.
5. Idea de practitioner claramente marcada como no verificada.
6. Brainstorming de ChatGPT claramente marcado como propuesta.

ChatGPT nunca presenta una idea generada como hecho conocido. Toda afirmación externa lleva fuente, fecha y nivel de evidencia.

## 2.2 Hypothesis card obligatoria

Una idea no entra a la cola computacional sin:

- hypothesis_id;
- pregunta en una línea;
- tipo de alerta;
- decisión apoyada;
- fuente y fecha;
- mecanismo propuesto;
- información observable en t;
- target y horizonte;
- control;
- resultado que la falsificaría;
- datos necesarios;
- frecuencia esperada aproximada;
- riesgos de lookahead;
- complejidad prevista;
- relación con hipótesis ya probadas.

## 2.3 Priorización

Antes de código, Valita y ChatGPT puntúan de 1 a 3:

| Dimensión | Pregunta |
|---|---|
| Utilidad | ¿Cambiaría una decisión real de Valita? |
| Falsabilidad | ¿Puede salir claramente mal? |
| Data readiness | ¿Los datos existen y son auditables? |
| Distinctness | ¿Añade información distinta a lo ya probado? |
| Costo | ¿Puede resolverse con un experimento pequeño? |
| Evidencia previa | ¿Tiene mecanismo o fuente razonable? |

La prioridad no incluye performance histórica todavía.

Empates se resuelven por mayor información esperada y menor costo, no por entusiasmo.

## 2.4 Cola

- Máximo una hipótesis computacional ACTIVE.
- Puede existir una tarea LANDSCAPE en paralelo solo si no modifica código ni resultados.
- Ninguna hipótesis entra porque “el lab se aburrió”.
- Una familia no necesita terminarse si otra pregunta ofrece más información.
- Cada experimento declara presupuesto de tiempo, número de configuraciones y stop condition.

## 2.5 Qué medir según la pregunta

### Fenómeno

- N efectivo y definición de independencia;
- conditional mean y median;
- control mean y median;
- edge absoluto y relativo;
- P(resultado favorable) y lift sobre base;
- cuantiles, especialmente cola adversa;
- incertidumbre del edge;
- estabilidad temporal;
- tiempo hasta el efecto.

### Estrategia

- retorno neto;
- CAGR o medida comparable por tiempo;
- exposición;
- trades por año;
- turnover;
- average win, average loss y payoff;
- MaxDD MTM y duración;
- costo base y stress;
- comparación económica y de riesgo contra benchmark.

### Utilidad de alerta

- frecuencia;
- hora local;
- lead time;
- TTL;
- falsa alarma y omisión, cuando el target sea binario;
- claridad de why;
- acción posible dentro de la ventana disponible.

No se reporta una métrica porque “siempre se usa”. Se reporta porque responde la pregunta.

## 2.6 Resultado de aprendizaje para Valita

Cada experimento cerrado debe producir un resumen corto que ella pueda explicar:

1. ¿Qué se preguntó?
2. ¿Qué información existía en t?
3. ¿Qué control se usó?
4. ¿Qué se encontró?
5. ¿Cuál es la incertidumbre?
6. ¿Cuál es el principal failure mode?
7. ¿Qué decisión se tomó y por qué?

Si Valita no puede explicarlo sin repetir jerga del modelo, no se promueve.

---

# §3 Protocolo de research

## 3.1 Contrato de datos

### Dataset heredado, todavía no auditado

Claims conservados de v3:

- fuente declarada: Binance BTCUSDT Spot;
- intervalo: 1h;
- inicio declarado: 2017-08-17 04:00 UTC;
- fin declarado: 2026-08-26 13:00 UTC;
- barras declaradas: 78,986;
- timestamps únicos y ordenados: sí, según v3;
- OHLC válidos: sí, según v3;
- missing hours: 128;
- ruta legacy: btc_tsmom_replication/btcusdt_1h.csv;
- SHA-256: TBC.

Estos son claims documentales hasta que un DATA_AUDIT run los reproduzca.

### Requisitos por dataset

- provider y endpoint;
- retrieved_at UTC;
- parámetros exactos;
- timezone;
- start y end inclusivos/exclusivos;
- esquema, dtypes y unidades;
- raw file inmutable;
- processed file separado;
- hash de ambos;
- filas, duplicados, gaps y valores inválidos;
- transformación exacta;
- código/commit que transformó;
- última vela cerrada incluida.

Un hash identifica bytes; no acredita provenance ni calidad.

### Política de gaps

- No imputar precios.
- Lookbacks se resuelven por timestamp exacto.
- Si falta t−L, la observación no es elegible.
- Si falta signal bar, entry bar o exit bar exacta, el trade no existe.
- Cada exclusión se cuenta por motivo.
- Calendar reporta semanas perdidas y la razón.
- No se comprime el tiempo tratando filas consecutivas como horas consecutivas.

### Datos comunes

Los datos comunes no deben vivir dentro de una familia como btc_tsmom_replication. La migración futura separará:

- data/raw;
- data/processed;
- data/catalog;
- projects;
- experiments.

No se mueve ni renombra nada hasta que una tarea atómica lo autorice y preserve hashes.

## 3.2 Tests de invariantes

Antes de nuevos scans deben existir fixtures pequeños y tests para:

1. Timestamp lookback con una hora faltante.
2. Entry exclusivamente posterior a la señal.
3. Exit exacto por timestamp.
4. Trade omitido si falta una pierna.
5. Fees en entrada y salida.
6. No-overlap.
7. Percentiles usando exclusivamente s < t.
8. Rolling high/low excluyendo t.
9. DST ambiguo o inexistente.
10. Trades que cruzan fronteras.
11. Equity MTM durante la posición.
12. Reproducción manual de trades conocidos.
13. Mismo input + spec + code commit = mismo output.

Un error material se cierra solo con:

- arreglo;
- test que fallaba antes;
- test que pasa después;
- rerun nuevo;
- impacto documentado.

## 3.3 Diseño temporal

Las ventanas heredadas siguen siendo útiles para descripción:

| Bloque | Ventana |
|---|---|
| Discovery | inicio → 2021-12-31 |
| Historical validation | 2022-01-01 → 2024-12-31 |
| Historical recent | 2025-01-01 → corte |

Reglas:

- Las tres ventanas ya han sido observadas por el proyecto.
- Ninguna se llama clean OOS.
- Una regla escogida usando Validation o Recent marca selection_contaminated = true.
- Una prueba confirmatoria histórica solo es limpia respecto de una selección que no usó ese bloque.
- El test realmente nuevo es posterior a freeze_date.

### Fronteras

- Para métricas de un bloque, señal, entry y exit deben quedar totalmente contenidos en el bloque.
- Features pueden usar historia disponible anterior al inicio del bloque.
- Se purga el final del bloque por el horizonte máximo de salida aplicable.
- La spec declara la política exacta antes del run.
- Ningún PnL de Discovery usa precios de Validation.

## 3.4 Anatomía de una spec

Antes del run se congela:

- experiment_id;
- hypothesis_id y versión;
- experiment_type;
- dataset y hash;
- pregunta;
- información observable en t;
- target;
- side;
- signal;
- entry;
- exit;
- overlap/cooldown;
- search space completo;
- número de configuraciones;
- métrica de ranking, si es SCAN;
- controles;
- N floor de triage;
- definición de independencia;
- costos;
- fronteras;
- missing-data policy;
- métricas;
- mechanical gates;
- resultados permitidos;
- tests;
- archivos esperados;
- stop conditions.

El N floor vive en la spec aprobada de cada experimento. No se inventa durante el run ni se contradice desde otro documento.

## 3.5 Exploración, selección y multiple testing

Predeclarar el search space es obligatorio, pero no elimina selection bias.

Todo SCAN registra:

- número total de configuraciones;
- filtros aplicados;
- ranking completo;
- cuántas candidatas se observaron;
- qué información se usó para elegir;
- cuántas variantes anteriores relacionadas existieron;
- si hubo elección humana posterior al ranking.

Antes de recomendar freeze desde un SCAN se exige un diagnóstico predeclarado de selección, por ejemplo:

- distribución best-of-search bajo un null temporal apropiado;
- Deflated Sharpe;
- Probability of Backtest Overfitting;
- otra técnica aprobada que evalúe el proceso completo de selección.

Se escoge una metodología proporcional al experimento; no se implementan todas.

Una prueba con una sola regla predeclarada no necesita fingir que fue un scan.

## 3.6 Incertidumbre

- El signo del edge es necesario, no suficiente.
- N es filtro de triage, no prueba.
- Se reporta un intervalo o distribución de incertidumbre compatible con dependencia temporal.
- Eventos contiguos se agrupan o se declara su dependencia.
- Se reporta concentración por año o periodo.
- Un resultado dominado por pocos trades extremos no se resume solo con mean.
- No se usa p < 0.05 como gate universal.

## 3.7 Costos y fills

Los costos se identifican por profile_id.

Perfiles iniciales:

| Profile | Uso |
|---|---|
| COST_ZERO_DIAGNOSTIC | Diagnóstico, nunca promoción |
| COST_LAB_10_RT | Escenario histórico heredado de 10 bps round-trip |
| COST_STRESS_20_RT | Sensibilidad |
| COST_STRESS_50_RT | Sensibilidad fuerte |
| COST_ACCOUNT_ACTUAL | TBC; fee real por cuenta, par y order type |

Reglas:

- 10 bps RT es un escenario, no una afirmación sobre la comisión real.
- Entry y exit aplican fees por separado.
- La spec declara maker/taker.
- El fill base puede usar open siguiente como aproximación de lab.
- Candidatas a freeze requieren escenario de slippage/spread.
- No se rescata una regla escogiendo el costo más favorable.
- Shorts teóricos no se comparan como estrategias ejecutables sin borrow, funding y liquidación.

Forma conceptual:

net_return = (1 − fee_entry) × (exit_fill / entry_fill) × (1 − fee_exit) − 1

El profile añade slippage y spread cuando aplique.

## 3.8 Kit mínimo por run

Obligatorio:

- N y definición;
- número de trials;
- mean y median net;
- control mean y median;
- edge;
- incertidumbre;
- win probability y payoff;
- cuantiles adversos;
- fees/profile;
- trades por año;
- exposure;
- resultado por bloque;
- lista o hash del event/trade log;
- mechanical gate.

Para DEEPEN o FREEZE, además:

- equity horaria MTM;
- CAGR o retorno comparable por tiempo;
- vol y Sharpe desde serie homogénea;
- MaxDD y duración;
- Sortino/Calmar si aportan;
- turnover;
- profit factor;
- MAE/MFE cuando tenga sentido;
- estabilidad por subperiodo;
- vecinos de parámetros;
- selection-bias diagnostic;
- benchmark económico.

El valor final de $10k puede mostrarse como ilustración secundaria. Nunca es la métrica central ni se compara sin ajustar por longitud del periodo.

## 3.9 Controles canónicos

| Caso | Control |
|---|---|
| Calendar | Misma duración y misma semana; además Buy & Hold |
| Extreme | Retorno incondicional del mismo horizonte y periodo |
| Breakout | Retorno incondicional del mismo horizonte |
| Compression | Mismo breakout sin condición de compression |
| Trade intermitente | Benchmark económico y exposición/riesgo |
| Risk alert | Base rate del evento adverso |

El control se define antes del run y no se cambia porque el resultado decepcionó.

## 3.10 Promoción

| De | A | Gate mínimo |
|---|---|---|
| L0 IDEA | L1 SPECIFIED | Hypothesis card completa, utilidad y spec aprobadas |
| L1 | L2 CALCULATED | Run, outputs y logs completos |
| L2 | L3 AUDITABLE | Manifest, hashes, tests y reproducción suficiente |
| L3 | L4 HISTORICAL ASSESSED | Selección/trials, control, incertidumbre, costos y robustness evaluados |
| UNFROZEN | FROZEN | Spec inmutable, selection note, freeze_date, hashes y stopping plan |
| FROZEN | L5 PROSPECTIVE | Solo datos inexistentes al freeze; stopping plan cumplido |

Mechanical gate de PROFUNDIZAR requiere todos:

- sin error material abierto que invalide el run;
- efecto económicamente no trivial contra su control;
- costo base y stress declarados;
- incertidumbre compatible con un efecto útil;
- N floor de la spec;
- no contradicción material en el bloque predeclarado;
- estabilidad no limitada a un punto aislado;
- selección completamente declarada.

Si N es bajo: INSUFICIENTE.

Si el control mata el efecto: DESCARTAR.

Si existe bug material: INVALIDATED.

Freeze puede aprobarse para una hipótesis exploratoria contaminada, pero no se eleva artificialmente su evidence_level.

## 3.11 Artefactos y estructura objetivo

| Ruta conceptual | Contenido |
|---|---|
| governance | Rector global, protocolo y contrato de IA |
| archive/rectors | v1, v2, v3 y releases antiguas |
| data/raw | Descargas inmutables |
| data/processed | Transformaciones versionadas |
| data/catalog | Manifests y auditorías |
| projects/btc_spot_1h | North Star y estado actual |
| registries | Ideas, hipótesis, runs, decisiones y errores |
| experiments/EXP-ID | Spec, src, tests, outputs, result y receipt |
| products/alerts | Vacío hasta freeze |

Cada run escribe en una carpeta nueva. Nombres genéricos como TOP_CANDIDATES.csv solo existen dentro de RUN-ID; nunca en la raíz ni compartidos entre familias.

## 3.12 Reproducibilidad mínima

Un tercero debe poder:

1. identificar la spec exacta;
2. identificar y obtener los mismos bytes de datos;
3. instalar el entorno declarado;
4. ejecutar un comando;
5. obtener los mismos hashes de outputs o una tolerancia predeclarada;
6. reproducir una muestra de eventos/trades;
7. explicar cualquier diferencia.

---

# §4 Contrato ChatGPT → Cursor

## 4.1 Roles

| Quién | Hace | No hace |
|---|---|---|
| Valita | Aprueba norte, utilidad, prioridad, decisión y freeze | No retunea por decepción |
| ChatGPT | Landscape, hipótesis, spec, task packet, auditoría y recomendación | No inventa resultados ni cambia outputs |
| Cursor | Implementa un delta, prueba, ejecuta y entrega receipt | No elige próximo proyecto ni interpreta “prometedora” |
| Código | Calcula datos, métricas y mechanical gates | No toma decisiones |

## 4.2 Regla de tamaño

Una tarea de Cursor contiene exactamente uno:

- un cambio de estructura;
- un data audit;
- un test/invariante;
- un bug fix;
- un run;
- una reproducción;
- una migración de evidencia.

No se combina en una tarea:

- fix + nueva familia;
- tres errores independientes;
- implementación + cambio de spec;
- run + retune;
- resultados + motor de alertas;
- mover folders + cambiar lógica.

## 4.3 Definition of Ready

No se entrega una tarea a Cursor sin:

- task_id;
- objetivo único;
- archivos exactos a leer;
- precondiciones;
- inputs y hashes, si existen;
- paths permitidos;
- paths prohibidos;
- spec o regla aplicable;
- tests;
- outputs;
- acceptance criteria;
- stop conditions.

## 4.4 Definition of Done

Cursor entrega:

- archivos cambiados;
- diff summary;
- comandos ejecutados;
- tests y resultado;
- run_id, si aplica;
- manifest;
- outputs y hashes;
- mechanical gate;
- supuestos;
- blockers;
- actualizaciones autorizadas a registros.

ChatGPT audita artefactos, no solo el mensaje de Cursor.

## 4.5 Plantilla de task packet

TASK_ID:

TIPO:

OBJETIVO ÚNICO:

LEE SOLO:

PRECONDICIONES:

INPUTS Y HASHES:

PUEDES CAMBIAR:

NO PUEDES CAMBIAR:

IMPLEMENTA:

TESTS OBLIGATORIOS:

OUTPUTS:

ACEPTACIÓN:

AL TERMINAR:

STOP CONDITIONS:

Si una precondición falla o la tarea contradice el North Star, Cursor se detiene. No improvisa una solución lateral.

## 4.6 Verdad numérica

- CSV/JSON/Parquet machine-generated son canónicos.
- El Markdown resume y enlaza.
- ChatGPT no recalcula cifras mentalmente.
- Cursor no copia números manualmente entre tablas si puede generarlos.
- Un cambio narrativo no modifica el resultado.
- Si el resumen y el artefacto difieren, manda el artefacto y se abre error.

---

# §5 Evidencia heredada y reclassification

Los números completos permanecen en v3 y en sus artefactos originales. v4 no los duplica como verdad activa.

## 5.1 Weekly Calendar

### Pregunta

¿Alguna ventana semanal tiene retorno de calendario distinto a otras ventanas de la misma duración y utilidad económica frente a Buy & Hold?

### Rule heredada

- rule_id legacy: CALENDAR_V1
- BUY Friday 03:00 America/New_York
- SELL Monday 20:00 America/New_York
- schedule local aproximado: 89h, sujeto a definición DST
- exposición aproximada heredada: 52.98%

### Reclassification v4

| Campo | Estado |
|---|---|
| Evidence level | L2 CALCULATED |
| Lifecycle | DEEPEN_METHOD / UNFROZEN |
| Selection contaminated | Sí |
| Motivo | El horario concreto fue elegido entre Top 20 después de mirar Validation + Recent |
| Clean historical validation | No para esta regla exacta |
| HODL | Incompleto |
| Data hash | TBC |
| Audit manifest | No existe |
| Alerta viva | No |

Completar HODL mejora la interpretación económica; no elimina el peek.

Ruta válida:

1. auditar datos y outputs;
2. cerrar definición DST y fronteras;
3. evaluar selection bias del scan;
4. aprobar spec inmutable;
5. opcionalmente freeze como hipótesis exploratoria;
6. medir solo futuro para L5.

No se vuelve a escoger otro Top 20 usando los mismos bloques.

## 5.2 Extreme Move

### Pregunta

Tras un movimiento extremo, ¿el retorno posterior difiere del BTC ordinario del mismo horizonte?

### Reclassification v4

| Campo | Estado |
|---|---|
| Evidence level | L2 CALCULATED, afectado |
| Lifecycle | INVALIDATED |
| Error fatal | E-02: filas no equivalen a horas |
| Otros errores | E-03 y E-04 |
| N Recent heredado | No utilizable para promoción |
| Rule candidate | Ninguna activa |
| Alerta viva | No |

Todos los resultados pre-fix son evidencia histórica del proceso, no evidencia sobre el edge.

El próximo trabajo no es “rerun Extreme” como bloque. Se divide en tests, fix, rerun, gate y auditoría separados.

## 5.3 Breakout

| Campo | Estado |
|---|---|
| Evidence level | L0 IDEA / spec draft |
| Lifecycle | BACKLOG |
| Search space | Parcialmente definido |
| N floor | No aprobado |
| Cooldown/reentry | No definido |
| Fronteras 720h | No definidas |
| Autorizado para Cursor | No |

La próxima acción posible es SPEC, no SCAN.

## 5.4 Volatility Compression

| Campo | Estado |
|---|---|
| Evidence level | L0 IDEA / spec draft |
| Lifecycle | BACKLOG |
| Pregunta incremental | Bien definida |
| RV exacta | No definida |
| Search space | Incompleto |
| Matched control | Conceptual, no implementado |
| Autorizado para Cursor | No |

Primero debe existir un baseline Breakout comparable o una justificación explícita para otro diseño.

## 5.5 Qué no se hereda como norma

- La etiqueta Nivel 4 de método.
- La idea de que hash + freeze_date arreglan la contaminación.
- Los mínimos N globales contradictorios.
- Recent “no contradictorio” sin definición.
- El contrato de alerta de v2.
- El roadmap A como sprint combinado.
- 10 bps RT como fee real.

---

# §6 Estado, decisiones y errores

## 6.1 Estado vivo

**Corte:** 2026-09-02

| Campo | Valor |
|---|---|
| Etapa | R0 — reparar sistema operativo de research |
| Active computational experiment | Ninguno |
| Active live alert | Ninguna |
| Frozen rule | Ninguna |
| Prospective rule | Ninguna |
| Capital real | $0 |
| Dataset | Legacy BTCUSDT 1h; claims de v3; hash TBC |
| Próxima decisión humana | Aprobar v4 y el alcance de alert utility |
| Próxima tarea Cursor | Solo cuando §7 nombre un TASK-ID |

El snapshot no sustituye el futuro RUNS registry.

## 6.2 Decisiones v4

| ID | Decisión | Estado |
|---|---|---|
| DEC-001 | v4 es rector de descubrimiento, no de producto | PENDIENTE DE APROBACIÓN v4 |
| DEC-002 | Evidence level, lifecycle y freeze se separan | PENDIENTE DE APROBACIÓN v4 |
| DEC-003 | Scan y confirmatory son tipos distintos | PENDIENTE DE APROBACIÓN v4 |
| DEC-004 | Cursor reporta mechanical gate; Valita decide | PENDIENTE DE APROBACIÓN v4 |
| DEC-005 | Outputs de runs son inmutables | PENDIENTE DE APROBACIÓN v4 |
| DEC-006 | v1–v3 son evidencia sin autoridad normativa | PENDIENTE DE APROBACIÓN v4 |
| DEC-007 | Otras coins reutilizarán protocolo global; no copiarán rectores divergentes | PENDIENTE DE ARQUITECTURA |

## 6.3 Errores heredados

| ID | Tema | Estado v4 |
|---|---|---|
| E-01 | Hash/provenance del dataset ausente | OPEN |
| E-02 | Extreme lookback por filas ≠ horas | OPEN |
| E-03 | Survivor gate permisivo | OPEN |
| E-04 | Extreme sin equity MTM | OPEN |
| E-05 | Calendar elegido con peek | PERMANENT_DISCLOSURE |
| E-06 | Uso de PROBADA/OOS | CLOSED |
| E-07 | Folklore distinto a regla Calendar | PERMANENT_DISCLOSURE |
| E-08 | N=11 interpretado con exceso | OPEN |
| E-09 | Producto adelantado al descubrimiento | FIXED_PENDING_VERIFICATION |

## 6.4 Nuevos errores de arquitectura

| ID | Tema | Estado |
|---|---|---|
| E-10 | Scan exploratorio confundido con confirmación | FIXED_PENDING_VERIFICATION |
| E-11 | Niveles 2/3 omitidos y Nivel 4 de método inventado | FIXED_PENDING_VERIFICATION |
| E-12 | Manifest, environment y run provenance ausentes | OPEN |
| E-13 | Roadmap con tareas demasiado grandes | FIXED_PENDING_VERIFICATION |
| E-14 | Documento superseded conservaba norma de alertas | FIXED_PENDING_VERIFICATION |
| E-15 | Fronteras/purge no definidos | OPEN |
| E-16 | 10 bps RT tratado como supuesto canónico | FIXED_PENDING_VERIFICATION |
| E-17 | Estado mutable sin registry append-only | OPEN |
| E-18 | Utilidad de alerta no declarada | OPEN |
| E-19 | Dataset común vive bajo proyecto tsmom | OPEN |
| E-20 | Outputs genéricos pueden colisionar/sobrescribirse | OPEN |

## 6.5 Regla de cierre de errores

Estado permitido:

- OPEN
- FIXED_PENDING_VERIFICATION
- CLOSED
- PERMANENT_DISCLOSURE

Todo error enlaza:

- fecha;
- affected ids;
- severidad;
- síntoma;
- causa;
- por qué no se vio;
- impacto;
- arreglo;
- test preventivo;
- rerun;
- decisión final.

---

# §7 Roadmap atómico

Cursor no avanza por número. Valita nombra exactamente un TASK-ID.

## R0 — Operating system

| Task | Dueño | Delta único | Aceptación |
|---|---|---|---|
| R0-H01 | Valita + ChatGPT | Aprobar tipos de alerta, decisiones y alcance | E-18 cerrado |
| R0-C01 | Cursor | Crear estructura canónica vacía y archive map | Sin mover datos ni código |
| R0-C02 | Cursor | Registrar IDs y schemas de registries | Validación de campos |
| R0-C03 | Cursor | Migrar v1–v3 a archive y establecer un único puntero activo | Hashes preservados |
| R0-C04 | Cursor | Crear DATA_AUDIT spec, sin ejecutar | Spec aprobable |
| R0-C05 | Cursor | Ejecutar DATA_AUDIT y hash | Manifest + gap report |
| R0-C06 | Cursor | Crear fixture/test de E-02 | Test falla con lógica legacy |
| R0-C07 | Cursor | Implementar exact timestamp lookup | Test E-02 pasa |
| R0-C08 | Cursor | Crear tests de fill/exit/gaps | Suite pasa |
| R0-C09 | Cursor | Crear run manifest y receipt generator mínimo | Run sintético reproducible |
| R0-C10 | Cursor | Migrar evidencia heredada sin recalcular | IDs y links, números intactos |

No se necesita base de datos, dashboard, orchestration ni ML para cerrar R0.

## R1 — Landscape y priorización

| Task | Dueño | Delta |
|---|---|---|
| R1-H01 | ChatGPT | Landscape documental de familias y fuentes |
| R1-H02 | Valita + ChatGPT | Registrar hypothesis cards, incluso descartadas |
| R1-H03 | Valita | Elegir una sola hipótesis por utilidad e información esperada |
| R1-H04 | ChatGPT | Escribir su SPEC; Cursor aún no ejecuta |

El landscape no promete ninguna estrategia y no añade fuentes de datos al research activo.

## R2 — Resolver evidencia heredada

Calendar y Extreme compiten por prioridad con nuevas hipótesis; no avanzan por sunk cost.

### Calendar, si se nombra

| Task | Delta |
|---|---|
| CAL-C01 | Reproduction spec |
| CAL-C02 | Reproducir scan/resultados con manifest |
| CAL-C03 | Completar HODL por bloque |
| CAL-C04 | Definir/testear DST y fronteras |
| CAL-C05 | Ejecutar selection-bias diagnostic predeclarado |
| CAL-H01 | Auditoría ChatGPT |
| CAL-H02 | Valita descarta, profundiza o congela prospectivamente |

### Extreme, si se nombra

| Task | Delta |
|---|---|
| EXT-C01 | Fix E-02 ya testado |
| EXT-C02 | Rerun solo para medir impacto de E-02 |
| EXT-C03 | Spec exacta de survivor gate E-03 |
| EXT-C04 | Implementar/testear E-03 |
| EXT-C05 | Implementar/testear equity MTM E-04 |
| EXT-C06 | Rerun final con manifest |
| EXT-H01 | Auditoría ChatGPT |
| EXT-H02 | Decisión Valita |

No se llama “un sprint Extreme”.

## R3 — Nuevos experimentos

Por cada hipótesis:

1. Hypothesis card.
2. Spec.
3. Tests.
4. Implementación.
5. Dry run.
6. Run oficial inmutable.
7. Receipt.
8. Auditoría.
9. Decisión.

Solo una activa.

## R4 — Freeze y prospectivo

Requisitos:

- rule spec inmutable;
- evidence_level honesto;
- selection contamination declarada;
- dataset y code hashes;
- freeze_date UTC;
- alert utility definida;
- stopping plan;
- mínimo de eventos o duración;
- política de data failures;
- no retune durante observación.

## R5 — Producto paper

Se crea otro North Star. Este rector no lo implementa.

---

# §8 Etapa futura: alertas paper

## 8.1 Gate de entrada

No se diseña motor hasta que exista al menos una frozen rule y DEC aprobada.

## 8.2 Contrato futuro mínimo

Una alerta paper tendrá:

- alert_id;
- rule_id y version;
- observed_at;
- source timestamps;
- candle_closed;
- signal values;
- threshold;
- why;
- expected horizon;
- expiry/TTL;
- status;
- dedupe key;
- data health;
- no capital action automática.

## 8.3 Requisitos operativos futuros

- consumir únicamente vela cerrada;
- reconectar streams;
- backfill por fuente histórica;
- detectar gaps;
- idempotencia;
- deduplicación;
- heartbeat;
- retry y dead-letter handling proporcional;
- clock/timezone explícito;
- audit log;
- separación señal/entrega;
- paper ledger;
- monitoreo de latencia;
- runbook de fallos;
- credenciales read-only cuando aplique.

## 8.4 Stopping plan prospectivo

Antes de la primera alerta se fija:

- fecha de inicio;
- N mínimo o duración mínima;
- métricas;
- regla para pausas por data outage;
- número máximo de revisiones;
- qué constituye fail;
- qué constituye insufficient;
- fecha de revisión;
- prohibición de retune.

Mirar resultados cada día no autoriza terminar cuando “ya se ve bien”.

## 8.5 Lo que L5 no significa

L5 no implica:

- capital;
- leverage;
- automatización;
- que funcionará en otra coin;
- que sobrevivirá cambios de régimen;
- que el costo live coincide con backtest.

Después de L5 habrá una evaluación separada de riesgo y producto.

---

# Apéndice A — Hypothesis card

HYPOTHESIS_ID:

VERSION:

FECHA:

FUENTE:

EVIDENCE SOURCE TIER:

PREGUNTA EN UNA LÍNEA:

TIPO DE ALERTA:

DECISIÓN APOYADA:

MECANISMO PROPUESTO:

OBSERVABLE EN t:

TARGET:

HORIZONTE:

CONTROL:

FALSIFICADOR:

DATOS:

FRECUENCIA ESPERADA:

RIESGO DE LOOKAHEAD:

RELACIÓN CON TRIALS ANTERIORES:

PRIORIDAD:

APROBACIÓN VALITA:

---

# Apéndice B — Experiment spec

EXPERIMENT_ID:

HYPOTHESIS_ID/VERSION:

EXPERIMENT_TYPE:

SPEC_STATUS:

SPEC_HASH:

DATASET_ID/HASH:

PREGUNTA:

SIGNAL:

ENTRY:

EXIT/TARGET:

SIDE:

OVERLAP/COOLDOWN:

SEARCH SPACE:

N_TRIALS:

RANKING:

CONTROLS:

N FLOOR:

INDEPENDENCE:

COST PROFILE:

BOUNDARIES:

MISSING POLICY:

METRICS:

UNCERTAINTY METHOD:

SELECTION-BIAS METHOD:

MECHANICAL GATES:

TESTS:

OUTPUTS:

STOP CONDITIONS:

APPROVED_BY/AT:

---

# Apéndice C — Run manifest

RUN_ID:

EXPERIMENT_ID:

STARTED_AT/ENDED_AT UTC:

SPEC_HASH:

CODE_COMMIT:

COMMAND:

ENVIRONMENT:

RANDOM_SEED:

RAW_DATA_ID/HASH:

PROCESSED_DATA_ID/HASH:

INPUT ROWS:

GAPS/DUPLICATES:

OUTPUT FILES/HASHES:

TESTS:

WARNINGS:

MECHANICAL_GATE:

---

# Apéndice D — Run receipt

RUN_ID:

DELTA:

FILES CHANGED:

COMMANDS:

TEST RESULT:

INPUT HASHES:

OUTPUT HASHES:

PRIMARY METRICS:

CONTROL RESULT:

UNCERTAINTY:

N/TRIALS:

MECHANICAL GATE:

SPEC DEVIATIONS:

BLOCKERS:

REGISTERS UPDATED:

---

# Apéndice E — Decision record

DECISION_ID:

FECHA:

OWNER:

AFFECTED IDS:

PREGUNTA:

EVIDENCIA:

ALTERNATIVAS:

DECISIÓN:

POR QUÉ:

CONSECUENCIAS:

REVIEW TRIGGER:

---

# Apéndice F — Error record

ERROR_ID:

FECHA:

ESTADO:

SEVERIDAD:

AFFECTED IDS:

SÍNTOMA:

CAUSA:

POR QUÉ NO SE VIO:

IMPACTO:

ARREGLO:

TEST PREVENTIVO:

RERUN:

REGLA PERMANENTE:

---

# Principio final

Antes de aceptar cualquier resultado:

1. ¿Qué pregunta fue aprobada antes del run?
2. ¿Qué podía saberse en t?
3. ¿Fue scan o confirmatory?
4. ¿Cuántos trials existieron?
5. ¿Qué información eligió esta regla?
6. ¿Contra qué control se midió?
7. ¿Cuál es la incertidumbre?
8. ¿El efecto sobrevive costos razonables?
9. ¿Los datos, código y outputs son reproducibles?
10. ¿Qué decisión ayuda a tomar?
11. ¿Qué la haría fallar?
12. ¿Qué evidencia es realmente posterior al freeze?

Si una respuesta material no puede reconstruirse, no hay candidato operativo. Hay trabajo pendiente.

---

# Referencias metodológicas y técnicas

- Binance Spot REST API — Kline/Candlestick data: https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data
- Binance Spot WebSocket — closed kline flag: https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#klinecandlestick-streams-for-utc
- Binance Spot Commission Rates: https://developers.binance.com/en/docs/products/spot/faqs/commission_faq
- Bailey, Borwein, López de Prado y Zhu — The Probability of Backtest Overfitting: https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Bailey y López de Prado — The Deflated Sharpe Ratio: https://www.pm-research.com/content/iijpormgmt/40/5/94.full.pdf
- BIS Working Paper 1087 — Crypto Carry: https://www.bis.org/publications/working-paper-1087-crypto-carry
