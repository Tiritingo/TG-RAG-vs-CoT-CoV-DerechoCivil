# 04_Golden_Set

Corresponde al **Anexo C** del trabajo de grado.

Contiene el conjunto de evaluación de referencia (golden set) de 120 preguntas de interpretación contractual utilizadas para comparar el RAG Base y el Agente CoT-CoV. Cada pregunta incluye:

- Respuesta esperada.
- Fuente normativa o jurisprudencial de respaldo.
- Nivel de complejidad hermenéutica asignado.

También debe incluir el instrumento de evaluación experta (Anexo C):

- Rúbrica de evaluación con las dimensiones de fidelidad jurídica, consistencia silogística y complejidad hermenéutica (escala ordinal de cinco niveles).
- Instrucciones suministradas a los evaluadores.
- Definición operativa de cada categoría de la rúbrica.

## Estructura sugerida

```
04_Golden_Set/
├── golden_set_120_preguntas.csv   # Preguntas, respuestas esperadas, fuentes y nivel de complejidad
├── rubrica_evaluacion.pdf         # o .docx / .md
└── instrucciones_evaluadores.pdf  # o .docx / .md
```
