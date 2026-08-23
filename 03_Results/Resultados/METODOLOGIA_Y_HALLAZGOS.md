# Evaluación comparativa RAG_Base vs. Agente_CoT_CoV — derecho civil colombiano

## 1. Pipeline (dos partes, tal como se solicitó)

**Parte 1 — `parte1_telemetria.py`** (100% automática, sin juicio jurídico)
Extrae del CSV crudo: cobertura de cada arquitectura, distribución de
`Num_Revisiones_Agente` y longitud de respuesta. No evalúa calidad.

**Parte 2 — `parte2_estadistica.py`** (cruce estadístico)
Toma la telemetría de la Parte 1 y la cruza con
`matriz_calificaciones_expertos.csv` (evaluación cualitativa) para correr
Wilcoxon (pareado, RAG vs. Agente) y Spearman (revisiones vs. calidad;
correlación entre métricas).

**Matriz de calificaciones expertas** (`matriz_calificaciones_expertos.csv`)
Generada mediante lectura directa, actuando como jurista, de las 120
preguntas y sus respuestas bajo ambas arquitecturas, con la rúbrica del
§2. Total: 179 evaluaciones (62 de RAG_Base, 117 de Agente_CoT_CoV).

## 2. Rúbrica dogmática (escala 1-5)

| Métrica | Qué mide | 1 | 5 |
|---|---|---|---|
| **Consistencia Silogística** | Rigor premisa mayor → subsunción fáctica (premisa menor) → conclusión, sin saltos lógicos | Sin estructura reconocible / conclusión no se sigue | Silogismo completo y riguroso, con subsunción fáctica explícita |
| **Fidelidad Jurídica** | Exactitud normativa/jurisprudencial; ausencia de citas inventadas o extrapolaciones indebidas | Errores normativos graves o citas fabricadas | Riguroso, sin extrapolaciones indebidas |
| **Complejidad** | Profundidad argumentativa: tensiones interpretativas, matices, subcuestiones | Superficial o evasiva | Sofisticada, pondera criterios en conflicto |

Casos **no evaluables (NA)**: rechazos puros del RAG ("No encontrado en
el corpus...", sin desarrollo — 58 preguntas) y errores 503 de API del
Agente (3 preguntas: IDs 25, 114, 119). No hay texto jurídico sustantivo
que calificar en esos casos.

## 3. Hallazgos de telemetría (Parte 1)

- **Cobertura RAG_Base: 51.7%** (62/120). El 48.3% restante son rechazos
  ("No encontrado en el corpus"), casi todos puros (58/60).
- **Cobertura técnica Agente_CoT_CoV: 97.5%** (117/120); 3 fallas 503 no
  atribuibles al modelo sino a la infraestructura de API.
- **Revisiones del bucle CoV**: media 1.11, mediana 1, moda 1 (0 rev.: 3
  casos; 1 rev.: 101; 2 rev.: 16). Distribución de rango muy restringido.
- El número de revisiones **no varía** según si el RAG había fallado en
  esa misma pregunta (1.10 vs. 1.11) — el bucle de verificación no
  parece "compensar" activamente los vacíos del RAG.

## 4. Hallazgos dogmáticos (Parte 2)

### Wilcoxon pareado (mismas 61 preguntas respondidas por ambas arquitecturas)

| Métrica | Mediana RAG | Mediana Agente | p-valor | Efecto (r rank-biserial) |
|---|---|---|---|---|
| Consistencia Silogística | 3.0 | 4.0 | <0.0001 | 0.95 (grande) |
| Fidelidad Jurídica | 4.0 | 4.0 | 0.0455 | 0.07 (trivial) |
| Complejidad | 3.0 | 3.0 | <0.0001 | 0.57 (grande) |

### Spearman: revisiones del Agente vs. su propia calidad
Sin correlación significativa en ninguna métrica (ρ ≈ 0, p > 0.36). El
número de iteraciones del bucle de auto-verificación **no predice** la
calidad dogmática del resultado final, en este rango restringido (0-2).

### Spearman entre métricas dogmáticas (Agente)
Consistencia–Complejidad: ρ=0.57 (coherente: sub-criterios múltiples
producen más pasos silogísticos). Consistencia–Fidelidad: ρ=0.37
(moderada). **Fidelidad–Complejidad: ρ=-0.06** (prácticamente nula): un
desarrollo más elaborado no es garantía de mayor exactitud, y en la
lectura cualitativa esto se explica por varios casos (IDs 18, 19, 38, 56,
68, 75, 80, 102, 109) donde el Agente extendió una regla jurisprudencial
específica (p. ej. deber reforzado del fiduciario, doctrina de cláusulas
abusivas de consumo) a un supuesto general no claramente comparable —
"alucinación de autoridad" por extrapolación, no por invención de la cita.

## 5. Lectura jurídica de conjunto

- El Agente **domina de forma consistente** en estructura silogística y
  complejidad argumentativa: aplica sistemáticamente el esquema
  premisa mayor–subsunción–conclusión y desarrolla criterios múltiples
  (literal, sistemático, histórico) incluso cuando termina reconociendo
  que el contexto es insuficiente.
- En **fidelidad**, la ventaja del Agente sobre el RAG es marginal y
  estadísticamente frágil (57 de 61 pares empatados; el resultado
  significativo depende de solo 4 pares no empatados). Esto es coherente
  con que ambos sistemas citan del mismo corpus recuperado: el RAG, al
  limitarse a listar lo recuperado, comete pocos errores pero también
  responde a la mitad de las preguntas; el Agente responde casi siempre,
  pero al razonar más, introduce ocasionalmente extrapolaciones que
  compensan parte de la ganancia en cobertura y estructura.
- La **cobertura** es, en la práctica, la diferencia más grande y menos
  discutible entre arquitecturas (51.7% vs. 97.5%), y antecede
  lógicamente a cualquier comparación de calidad dogmática: en 58
  preguntas el RAG_Base simplemente no compite.

## 6. Limitaciones metodológicas (léase antes de citar estos resultados)

1. **Evaluador único y no cegado.** Las 179 calificaciones fueron
   producidas por un solo jurista (este análisis), sin cegamiento sobre
   qué arquitectura generó cada texto y sin segundo evaluador
   independiente. Para publicación o tesis, esto requiere validación con
   al menos 2-3 juristas adicionales, calculando confiabilidad
   inter-evaluador (p. ej. alfa de Krippendorff o ICC) antes de tratar
   estas cifras como definitivas.
2. **Patrón de dominancia perfecta.** En los 61 pares evaluados, el
   Agente nunca obtuvo una calificación *inferior* a la del RAG en
   ninguna métrica (solo empates o ventajas). Aunque explicable por las
   diferencias reales de diseño entre sistemas, este patrón también es
   compatible con un sesgo de expectativa del evaluador y debe
   contrastarse con evaluación ciega.
3. **Fidelidad Jurídica con alta proporción de empates** (57/61):
   la significancia estadística (p=0.045) es frágil y sensible a
   cambios menores en la calificación de pocos casos.
4. **Rango restringido en Num_Revisiones_Agente** (solo toma 0, 1 o 2,
   con 84% de los casos en el valor 1): limita la potencia de cualquier
   correlación de Spearman con esa variable.
5. **N distinto por arquitectura** (62 vs. 117 evaluables): las medias
   "globales" de la Parte 2 pueden estar sesgadas por selección, porque
   el RAG solo fue evaluado en el subconjunto de preguntas que decidió
   responder. El análisis pareado (mismas 61 preguntas) es la
   comparación válida; las medias sobre el total no lo son.

## 7. Archivos

- `parte1_telemetria.py`, `parte2_estadistica.py` — scripts
- `matriz_calificaciones_expertos.csv` — evaluación cualitativa (insumo)
- `telemetria_experimento.csv` — salida Parte 1
- `dataset_cruzado.csv`, `resultados_wilcoxon.csv`,
  `resultados_spearman_revisiones.csv` — salidas Parte 2
