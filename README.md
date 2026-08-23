# De la Recuperación al Razonamiento

**Comparativa de Fidelidad Jurídica entre RAG y Agentes Cognitivos en la Interpretación de Derecho Contractual Privado**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Licencia código](https://img.shields.io/badge/código-MIT-green)
![Licencia datos](https://img.shields.io/badge/datos-CC%20BY%204.0-orange)

Trabajo de grado — Maestría en Ciencia de Datos
Escuela de Ingenierías · Facultad de Ingeniería en TIC
Universidad Pontificia Bolivariana · Medellín, junio de 2026

| | |
|---|---|
| **Autor** | Gerardo Aguilar Guerrero — gerardo.aguilarg@upb.edu.co |
| **Director** | Roberto Hincapié — roberto.hincapie@upb.edu.co |

---

## Qué hace este proyecto

Compara dos arquitecturas de inteligencia artificial resolviendo las mismas 120 preguntas de derecho contractual privado colombiano: un **RAG estándar** de paso único, que recupera fragmentos y responde directamente, frente a un **agente cognitivo CoT-CoV**, que construye un silogismo jurídico explícito y somete su borrador a un módulo de verificación antes de responder.

Tres abogados en ejercicio auditaron las respuestas con una rúbrica ordinal de cinco niveles sobre fidelidad jurídica, consistencia silogística y complejidad hermenéutica gestionada.

La pregunta de fondo: **¿el razonamiento explícito y la verificación iterativa mitigan la alucinación en la interpretación jurídica automatizada?**

---

## Estructura del repositorio

```
TG_Maestria/
│
├── 01_Corpus_Raw/                    Corpus documental
│   ├── Codigo_Civil/                 Código Civil colombiano
│   ├── Codigo_Comercio/              Código de Comercio
│   ├── Ley_1480/                     Estatuto del Consumidor
│   ├── Ley_222/                      Régimen societario  (ver nota abajo)
│   └── Sentencias/
│       ├── Corte_Suprema/texto_plano/          245 providencias .txt
│       └── Corte_Constitucional/texto_plano/   411 providencias .txt
│
├── 03_Results/Resultados/            Resultados y análisis
│   ├── resultados_comparativos.csv           corrida reportada al jurado
│   ├── resultados_comparativos_v2_*.csv      corrida posterior (ver §Trabajo posterior)
│   ├── telemetria_experimento.csv
│   ├── METODOLOGIA_Y_HALLAZGOS.md
│   └── Matrices/                     calificaciones de los tres expertos
│       └── salidas_tres_expertos/    Wilcoxon, Spearman, kappa ponderado
│
├── 04_Golden_Set/golden_set.md       las 120 preguntas
│
└── 05_Codigo_Fuente/
    ├── RAG_COT_COV/                  notebooks de indexación y evaluación
    ├── SCRAPERS/                     descarga, validación de integridad, OCR
    └── Graficas/                     figuras del informe
```

### Correspondencia con los anexos del informe

| Carpeta | Anexo |
|---|---|
| `01_Corpus_Raw/` | Anexo A — corpus documental |
| `04_Golden_Set/` | Anexo A — instrumento de evaluación |
| `05_Codigo_Fuente/` | Anexos A y B — implementación y configuración técnica |
| `03_Results/` | Anexo C — resultados y análisis estadístico |

**Qué no está versionado.** Los PDF y RTF originales (1,3 GB) y el índice vectorial de ChromaDB (326 MB): dos archivos superan el límite de 100 MB de GitHub y los binarios de Chroma no son portables entre versiones. Se publica el corpus normalizado en texto plano, que un evaluador puede leer directamente en el navegador. El índice se regenera con el notebook.

---

## Configuración reportada al jurado

Estos son los parámetros que declara el informe entregado en junio de 2026:

| Parámetro | Valor |
|---|---|
| Segmentación | `RecursiveCharacterTextSplitter`, 800 caracteres, 100 de solapamiento |
| Fragmentos indexados | 1.368 |
| Embeddings | `intfloat/multilingual-e5-large` |
| Base vectorial | ChromaDB |
| Recuperación | MMR, k = 5 |
| RAG Base | generación de paso único, temperatura 0 |
| Agente CoT-CoV | silogismo jurídico + verificación iterativa, máximo 2 ciclos |
| Golden Set | 120 preguntas |

---

## Resultados reportados al jurado

Sobre la calificación de consenso de los tres expertos, en 61 pares comunes:

| Dimensión | Agente CoT-CoV | RAG Base | Diferencia |
|---|---:|---:|---:|
| Consistencia silogística | 4,25 | 2,83 | **+1,42** |
| Complejidad hermenéutica gestionada | 3,43 | 2,65 | **+0,78** |
| Fidelidad jurídica | 4,21 | 3,95 | **+0,27** |

El informe concluye que la ventaja del agente no se concentra en la corrección normativa sino en la coherencia estructural del razonamiento, que es precisamente lo que Chain-of-Thought busca reforzar.

### Verificación de reproducibilidad

Las medias y diferencias anteriores se reproducen **exactamente** desde `Matrices/salidas_tres_expertos/`. Recalculando la prueba de Wilcoxon pareada sobre `matriz_pareada_agente_vs_rag.csv`:

| Dimensión | n | p recalculado | d de Cohen |
|---|---:|---:|---:|
| Consistencia silogística | 61 | 8,9 × 10⁻¹² | 2,82 |
| Complejidad | 61 | 1,4 × 10⁻¹⁰ | 1,31 |
| Fidelidad jurídica | 61 | 1,2 × 10⁻⁸ | 0,97 |

Las tres dimensiones confirman `p < .001` y la dirección del efecto reportada en el informe.

---

## Discrepancias abiertas

En aras de la trazabilidad se documentan las diferencias detectadas entre el informe entregado y los artefactos de este repositorio. **Ninguna afecta la conclusión sustantiva**, que se sostiene con los datos publicados.

### Estadísticos no reproducibles

| Estadístico | Informe | Recalculado desde el repositorio |
|---|---|---|
| Wilcoxon, fidelidad jurídica | W = 1262 | W = 0 (suma menor) · W⁺ = 780 |
| d de Cohen, fidelidad jurídica | 1,22 | 0,97 |
| IC 95 % de la diferencia de medias | [31,56 · 49,69] | no reproducible |
| Spearman, degradación del RAG | rho = −0,595, p < .001 | no aparece en los artefactos |

El intervalo de confianza merece atención particular: sobre una rúbrica ordinal de 1 a 5 con una diferencia de medias de 0,27 puntos, un intervalo entre 31,56 y 49,69 no corresponde a esa escala.

El archivo `resultados_spearman_revisiones.csv` mide una relación distinta —número de revisiones del agente contra calidad de la respuesta— y arroja coeficientes cercanos a cero.

### Parámetros técnicos

| Parámetro | Informe | Código publicado |
|---|---|---|
| Segmentación | 800 / 100 | 900 / 120 |
| Fragmentos | 1.368 | 62.784 |
| Recuperación MMR | k = 5 | k = 8, fetch_k = 20, λ = 0,7 |
| **Modelo generador** | **GPT-4-turbo** | **Gemini 2.5 Flash** |
| Ley 222 de 1995 | no se menciona | presente en el corpus indexado |

Sobre el modelo generador: el código publicado emplea `gemini-2.5-flash` mediante `langchain_google_genai`, y es el que produjo los resultados versionados en este repositorio. La mención a GPT-4-turbo en el informe es un error de redacción.

---

## Trabajo posterior a la entrega

Lo que sigue **no formó parte del informe evaluado**. Se documenta porque afecta la interpretación del corpus publicado.

### Auditoría de integridad del corpus

Una revisión posterior detectó que el corpus original estaba comprometido:

- Las **411 providencias de la Corte Constitucional eran el mismo archivo repetido**, con un único hash MD5. El portal migró a una aplicación Angular que responde HTTP 200 con su página de inicio ante rutas no reconocidas, de modo que `raise_for_status()` nunca se activaba y el scraper guardó 411 veces la misma página.
- Ese contenido aportaba **4.521 fragmentos al índice, de los cuales 2.466 eran hojas de estilo de Bootstrap**. Ninguno tenía contenido jurídico.
- De 301 archivos de la Corte Suprema, 53 eran páginas de error y **108 escaneos sin capa de texto quedaban fuera del índice en silencio**, porque el cargador devolvía texto vacío.

### Reparación y segunda corrida

| | Corpus original | Corpus reparado |
|---|---:|---:|
| Fragmentos indexados | 29.281 | 62.784 |
| Fragmentos de hoja de estilo | 4.521 | **0** |
| Providencias de Corte Constitucional | **0** | 411 |
| Providencias de Corte Suprema | 139 | 245 |
| RAG Base respondió | 53/120 | 65/120 |
| RAG Base citó Corte Constitucional | **0** | 40 |
| Agente respondió | 88/120 | 93/120 |

Los resultados de esta segunda corrida están en `resultados_comparativos_v2_corpus_reparado.csv`. **No han sido calificados por los expertos**, por lo que no son comparables con las métricas del informe.

### Hallazgo pendiente: sesgo de composición

Tras la reparación, la Corte Constitucional aporta 34.247 de los 62.784 fragmentos (55 %), mientras el Código Civil aporta 1.138 (1,8 %). MMR diversifica entre fragmentos pero no reserva cuota por fuente. En las 120 respuestas de la segunda corrida el RAG citó 109 veces a la Corte Suprema, 71 a la Corte Constitucional y **solo 6 al Código Civil**.

### Hipótesis descartada

Se planteó que un corpus de mejor calidad reduciría las revisiones del agente. **No se confirma**: la media pasó de 1,11 a 1,19, con Wilcoxon pareado p = 0,096.

---

## Requisitos

- **Python 3.12**
- **GPU** para la indexación — `multilingual-e5-large` supera las 3 horas en CPU. Pensado para Google Colab con T4.
- **Tesseract OCR con idioma español**, solo si se reprocesa el corpus. [Instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki), marcando *Spanish* en «Additional language data».
- **LibreOffice**, solo si se reprocesa la Corte Constitucional.
- **Clave de API** del modelo generador.

## Instalación

```bash
git clone https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil.git
cd TG-RAG-vs-CoT-CoV-DerechoCivil

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux o macOS

pip install -r requirements.txt
```

La clave nunca se escribe en el código. En Colab se lee del gestor de secretos:

```python
from google.colab import userdata
GEMINI_API_KEY = userdata.get("Gemini_API_Key")
```

## Cómo reproducir

**Solo consultar resultados.** No hace falta ejecutar nada: están en `03_Results/Resultados/`, y `METODOLOGIA_Y_HALLAZGOS.md` explica la rúbrica.

**Reconstruir el corpus** (opcional, ya viene normalizado):

```bash
cd 05_Codigo_Fuente/SCRAPERS
python reparar_corpus_cc.py      # descarga la Corte Constitucional
python extraer_texto_cc.py       # normaliza a texto plano
python ocr_corte_suprema.py      # OCR de las escaneadas (~70 min)
python validar_corpus.py <carpeta>
```

**Indexar y evaluar.** Abrir `05_Codigo_Fuente/RAG_COT_COV/v3_RAG_vs_CoT_CoV_DerechoCivil.ipynb` en Colab con GPU T4.

**Analizar.**

```bash
cd 03_Results/Resultados
python parte1_telemetria.py
python parte2_estadistica.py
python Matrices/analisis_expertos.py
```

---

## Los datos

**Fuentes.** Relatoría de la Corte Suprema de Justicia y portal de la Corte Constitucional de Colombia, mediante el pipeline de `SCRAPERS/`. Códigos y leyes transcritos a markdown estructurado por artículos.

| Fuente | Documentos | Texto |
|---|---:|---:|
| Corte Constitucional | 411 | 31,8 MB |
| Corte Suprema de Justicia | 245 | 22,8 MB |
| Cuerpos normativos | 4 (3.480 artículos) | 1,0 MB |
| **Total** | **660** | **55,6 MB** |

**Nota sobre la Ley 222 de 1995.** Está presente en el corpus indexado del repositorio pero no se menciona en el informe entregado. Aporta 248 fragmentos.

**Cómo se obtuvo cada documento.** De la Corte Constitucional, 366 providencias en RTF, 30 en DOCX y 15 en DOC. De la Corte Suprema, 102 con capa de texto aprovechable y **143 mediante OCR** (Tesseract 5, español, 300 DPI). Los manifiestos en `texto_plano/manifiesto_*.csv` registran el método aplicado a cada archivo.

**No disponibles.** 53 providencias de la Corte Suprema devuelven el mensaje oficial `DOCUMENTO NO DISPONIBLE EN MEDIO MAGNETICO`.

---

## Limitaciones

**El texto por OCR no es transcripción certificada.** 143 providencias se reconstruyeron ópticamente. Cada una fue verificada por densidad de acentos, presencia de marcas jurídicas y ausencia de residuo binario, pero persisten errores en nombres propios y números de radicado. Para uso con efectos jurídicos, consúltese la fuente oficial.

**Cobertura desigual de la evaluación experta.** Dos de los tres evaluadores calificaron 117 respuestas del agente frente a 62 del RAG; solo uno cubrió las 120 de ambos sistemas. El consenso se calculó sobre los 61 pares comunes.

**Un solo modelo generador.** No se probó si el efecto de la verificación se sostiene con otros modelos.

**Faltan 53 providencias** no digitalizadas por la corporación.

**El índice actual está desbalanceado** a favor de la jurisprudencia constitucional.

---

## Trabajo futuro

- Recuperación balanceada por categoría, con cuotas para normativa y jurisprudencia
- Filtrar las providencias de tutela sin relación con derecho contractual
- Calificación experta de la segunda corrida
- Replicar con al menos otro modelo generador
- Publicar el corpus en Zenodo con DOI citable

---

## Licencia

Código bajo **MIT** (`LICENSE`). Datos bajo **CC BY 4.0** (`LICENSE-DATA`).

Las decisiones judiciales colombianas son documentos públicos y, conforme al artículo 41 de la Ley 23 de 1982, carecen de derechos de autor propios. CC BY 4.0 aplica sobre el trabajo derivado: selección, descarga verificada, normalización y transcripción.

### Cómo citar

```bibtex
@mastersthesis{aguilar2026razonamiento,
  author = {Aguilar Guerrero, Gerardo},
  title  = {De la Recuperación al Razonamiento: Comparativa de Fidelidad
            Jurídica entre RAG y Agentes Cognitivos en la Interpretación
            de Derecho Contractual Privado},
  school = {Universidad Pontificia Bolivariana},
  year   = {2026},
  address = {Medellín, Colombia},
  url    = {https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil}
}
```
