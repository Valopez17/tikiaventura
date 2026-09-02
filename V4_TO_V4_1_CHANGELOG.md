# Changelog v4 → v4.1

**Fecha:** 2026-09-02  
**Fuente intacta:** `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4.md` (SHA-256 `899e6ce33c3014cfde5111922c6011bc76f0141b5fd63ac7c5f1dfd5337afa84`)  
**Destino:** `BTC_STRATEGY_RESEARCH_AUDIT_PACK_v4_1.md`

Ningún resultado de Calendar, Extreme, Breakout o Volatility Compression fue recalculado. Ninguna cifra histórica cambió.

---

## ADOPTED

Protecciones de v4 conservadas sin debilitar:

- LANDSCAPE / SCAN / CONFIRMATORY / ROBUSTNESS / PROSPECTIVE / REPRODUCTION
- SCAN nunca equivale a confirmación
- `evidence_level` separado de `lifecycle_status`
- freeze separado de `evidence_level`
- `selection_contaminated`
- runs inmutables
- specs predeclaradas
- dataset provenance
- lookbacks por timestamp exacto
- gap policy (no imputar; exclusión si falta t−L, signal, entry o exit)
- entry posterior a la señal
- no lookahead
- boundaries / purge
- costs por `profile_id`; 10 bps RT es escenario, no fee real
- controles canónicos
- incertidumbre compatible con dependencia temporal
- multiple-testing awareness
- prospective stopping plan
- no retune prospectivo
- error registry
- reproducibilidad
- artefactos machine-generated como verdad numérica
- capital real = 0
- roles Valita / ChatGPT / Cursor / código
- hypothesis card, spec, manifest, receipt
- mechanical gate ≠ decisión de research
- claims documentales del dataset heredado (sin reauditoría en esta entrega)
- classifications de §5 idénticas a v4
- R0-H01 como decisión humana
- requisitos materiales de R0-C01…C10, reempaquetados
- R1–R4 en sustancia
- contrato futuro de alertas paper, sin implementarlo

---

## MODIFIED

- **North Star.** Se sustituye “el objetivo actual no es encontrar una estrategia ganadora; es construir una fábrica para producir y rechazar hipótesis” por un proceso capaz de descubrir, falsificar y validar reglas de trading económicamente útiles, sin abandonar la falsificación.
- **Cadena de propósito.** Queda explícita: research rigor → discovery → validation → prospective evidence → tradability assessment.
- **PRICE-ONLY.** Deja de leerse como alcance permanente. Queda como restricción de la fase actual para reducir dimensionalidad.
- **Tamaño de tarea.** “Una tarea contiene exactamente un delta” se sustituye por “una tarea = un objetivo científico o operativo verificable”. Pueden tocarse varios archivos si el significado científico es uno.
- **R0 Cursor.** R0-C01…R0-C10 dejan de ser el empaquetado por defecto. Pasan a tres paquetes: R0-A, R0-B, R0-C, con objetivo, aceptación y stop conditions. Los requisitos materiales no se eliminan.
- **Comprensión de Valita.** Sigue siendo obligatoria como comunicación y governance. Ya no convierte un resultado válido en FAIL científico por complejidad técnica. ChatGPT traduce.
- **Multiple testing.** El registro de trials, search space y contaminación se conserva. Deflated Sharpe, PBO y bootstrap best-of-search dejan de sugerirse como default de todo experimento; son proporcionales al search process.
- **R2.** Los ítems de Calendar/Extreme siguen siendo requisitos materiales; el empaquetado sigue §4.2 en lugar de atomización literal.
- **Snapshot y DECs.** Pendientes de aprobación v4.1, no v4.
- **Archive.** v4 se añade a la lista de rectores históricos.

---

## ADDED

- Principio “cada artefacto debe pagar renta” y lista explícita de lo que R0 no construye (database, dashboard, orchestration, agents, alert engine, queues, experiment-tracking platforms, ML framework, abstracciones multi-coin).
- Regla operativa time-to-information: el diseño más pequeño que falsifica correctamente.
- Etapa conceptual ECONOMIC / TRADABILITY ASSESSMENT, posterior a L5.
- Estados futuros `NOT_TRADEABLE` / `PAPER_TRADEABLE` / `SMALL_CAPITAL_CANDIDATE`, sin equivaler a autorización de capital.
- Preguntas finales 13, 14 y 15.
- DEC-008 a DEC-016.
- E-21 (atomización excesiva) y E-22 (tratar el OS documental como el producto).
- Lista de familias futuras (volume, perps, funding, basis, OI, liquidations, options, cross-exchange, on-chain, macro/attention) como decisiones separadas, no como trabajo actual.
- Nota en Apéndice B: selection-bias method proporcional; omitir aparato de scan si `n_trials = 1`.

---

## DEFERRED

No ejecutado y no autorizado en esta entrega:

- R0-A / R0-B / R0-C
- DATA_AUDIT computacional
- fix de Extreme / E-02 en código
- recálculo de Calendar, Extreme, Breakout, Vol
- nuevas hipótesis o scans
- alert engine, paper alerts, motor de producto
- implementación de tradability assessment
- volume, futures, funding, on-chain, macro u otras familias
- capital real
- database, dashboard, orchestration u otra infraestructura de plataforma
- Deflated Sharpe / PBO / best-of-search como librería general

---

## REMOVED

- La formulación North Star que presentaba la fábrica de hipótesis como fin, en lugar de medio para descubrir reglas económicamente útiles.
- La regla literal “una tarea contiene exactamente un delta” / “un solo delta conductual” como packing obligatorio.
- R0-C01…R0-C10 como secuencia por defecto de diez tareas Cursor. Los requisitos materiales no se borran; cambia el empaquetado.
- La lectura de que no poder explicar un resultado en jerga convierte el run en FAIL científico.
- La lectura de que PRICE-ONLY es una filosofía permanente del laboratorio.
- El default implícito de aplicar Deflated Sharpe / PBO / best-of-search a todo experimento, incluida una regla única predeclarada.
