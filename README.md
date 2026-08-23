# RAG vs. Agente CoT/CoV en derecho civil colombiano

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Licencia código](https://img.shields.io/badge/código-MIT-green)
![Licencia datos](https://img.shields.io/badge/datos-CC%20BY%204.0-orange)
![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow)

Trabajo de grado — Maestría en Ciencia de Datos, Universidad Pontificia Bolivariana, Medellín.

---

## Qué hace este proyecto

Compara dos arquitecturas de inteligencia artificial resolviendo las mismas 120 preguntas de derecho civil contractual colombiano: un **RAG básico**, que busca documentos y responde en un solo paso, frente a un **agente con razonamiento en cadena y autoverificación** (CoT/CoV), que razona por etapas y audita su propia respuesta antes de entregarla.

Ambas trabajan sobre el mismo corpus de 656 sentencias de la Corte Suprema de Justicia y la Corte Constitucional, más cuatro cuerpos normativos. Tres juristas evaluaron las respuestas con una rúbrica dogmática.

La pregunta de fondo: **¿la autoverificación mejora el rigor jurídico de una respuesta generada por IA, o solo la hace más larga?**

---

## Estructura del repositorio

```
TG_Maestria/
│
├── 01_Corpus_Raw/                    Corpus documental
│   ├── Codigo_Civil/                 Código Civil (markdown por artículos)
│   ├── Codigo_Comercio/              Código de Comercio
│   ├── Ley_1480/                     Estatuto del Consumidor
│   ├── Ley_222/                      Régimen societario
│   └── Sentencias/
│       ├── Corte_Suprema/
│       │   └── texto_plano/          245 sentencias .txt + manifiesto
│       └── Corte_Constitucional/
│           └── texto_plano/          411 sentencias .txt + manifiesto
│
├── 02_Vectorstore/                   (no versionado — se regenera)
│
├── 03_Results/Resultados/            Resultados experimentales
│   ├── resultados_comparativos.csv           corrida 1 (corpus original)
│   ├── resultados_comparativos_v2_*.csv      corrida 2 (corpus reparado)
│   ├── telemetria_experimento.csv
│   ├── METODOLOGIA_Y_HALLAZGOS.md
│   └── Matrices/                     calificaciones de los tres expertos
│       └── salidas_tres_expertos/    Wilcoxon, Spearman, kappa ponderado
│
├── 04_Golden_Set/
│   └── golden_set.md                 las 120 preguntas
│
└── 05_Codigo_Fuente/
    ├── RAG_COT_COV/
    │   ├── v2_...ipynb               notebook original
    │   ├── v3_...ipynb               notebook con corpus reparado
    │   └── celda_reindexacion.py     celda de carga limpia
    ├── SCRAPERS/                     descarga, validación, OCR
    └── Graficas/                     figuras del informe
```

**Qué no está aquí y por qué.** Los PDF y RTF originales (1,3 GB) y el índice vectorial (326 MB) quedan fuera: dos archivos de Chroma superan el límite de 100 MB de GitHub, y sus binarios no son portables entre versiones. El vectorstore se regenera en unos 8 minutos con el notebook. Lo que sí está es el corpus normalizado en texto plano, que es lo que un evaluador puede leer directamente en el navegador.

---

## Requisitos

- **Python 3.12**
- **GPU** para la indexación — el modelo `multilingual-e5-large` tarda más de 3 horas en CPU. El proyecto está pensado para Google Colab con T4.
- **Tesseract OCR con idioma español**, solo si vas a reprocesar el corpus. [Instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki) (marcar *Spanish* en «Additional language data»).
- **LibreOffice**, solo si vas a reprocesar Corte Constitucional (convierte 15 documentos en formato Word 97).
- **Clave de API de Google Gemini** para ejecutar la evaluación.

---

## Instalación

```bash
git clone https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil.git
cd TG-RAG-vs-CoT-CoV-DerechoCivil

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux o macOS

pip install -r requirements.txt
```

La clave de Gemini nunca se escribe en el código. En Colab se lee desde el gestor de secretos:

```python
from google.colab import userdata
GEMINI_API_KEY = userdata.get("Gemini_API_Key")
```

---

## Cómo reproducir el experimento

### Ruta corta — solo ver los resultados

No hace falta ejecutar nada. Los resultados están en `03_Results/Resultados/`, y `METODOLOGIA_Y_HALLAZGOS.md` explica la rúbrica y los hallazgos.

### Ruta completa — reproducir desde cero

**1. Reconstruir el corpus** (opcional, ya está incluido en texto plano)

```bash
cd 05_Codigo_Fuente/SCRAPERS
python reparar_corpus_cc.py      # descarga las 411 de Corte Constitucional
python extraer_texto_cc.py       # las normaliza a .txt
python ocr_corte_suprema.py      # OCR de las 143 escaneadas (~70 min)
python validar_corpus.py <carpeta>   # verifica integridad
```

**2. Indexar y evaluar**

Abre `05_Codigo_Fuente/RAG_COT_COV/v3_RAG_vs_CoT_CoV_DerechoCivil.ipynb` en Colab, activa la GPU T4 y ejecuta en orden. Las celdas 1-7 preparan el entorno, la 9 verifica la carga, la 10 construye el índice (~8 min) y la 25 corre la evaluación (~77 min).

**3. Analizar**

```bash
cd 03_Results/Resultados
python parte1_telemetria.py      # cobertura y longitudes
python parte2_estadistica.py     # Wilcoxon y Spearman
python Matrices/analisis_expertos.py   # concordancia interevaluador
```

---

## Los datos

**Fuentes.** Corte Suprema de Justicia y Corte Constitucional de Colombia, descargadas de sus portales oficiales mediante los scripts de `SCRAPERS/`. Códigos y leyes transcritos a markdown estructurado por artículos.

**Composición del corpus.**

| Fuente | Documentos | Texto |
|---|---:|---:|
| Corte Constitucional | 411 | 31,8 MB |
| Corte Suprema de Justicia | 245 | 22,8 MB |
| Código Civil, Código de Comercio, Ley 222, Ley 1480 | 4 (3.480 artículos) | 1,0 MB |
| **Total** | **660** | **55,6 MB** |

**Cómo se obtuvo cada documento.** 366 sentencias de Corte Constitucional venían en RTF, 30 en DOCX y 15 en DOC. De las 245 de Corte Suprema, 102 traían capa de texto aprovechable y **143 exigieron OCR** (Tesseract 5, español, 300 DPI). Los manifiestos en `texto_plano/manifiesto_*.csv` registran el método aplicado a cada archivo, sus páginas, caracteres y verificaciones.

**Documentos no disponibles.** 53 providencias de Corte Suprema devuelven el mensaje oficial `DOCUMENTO NO DISPONIBLE EN MEDIO MAGNETICO`: no están digitalizadas y no fue posible incorporarlas.

---

## Metodología

**Indexación.** Los documentos se trocean con `RecursiveCharacterTextSplitter` (900 caracteres, 120 de solapamiento) y se vectorizan con `intfloat/multilingual-e5-large` normalizado, sobre Chroma. El índice resultante tiene **62.784 chunks**.

**Arquitectura A — RAG_Base.** Recuperación por similitud y una sola llamada al modelo generador (Gemini 2.5 Flash).

**Arquitectura B — Agente CoT/CoV.** Grafo de estados en LangGraph con tres nodos: recuperador, razonador —que produce un silogismo jurídico explícito— y verificador, que audita la respuesta y puede devolverla al razonador. El campo `Num_Revisiones_Agente` registra cuántas pasadas necesitó.

**Evaluación.** 120 preguntas de derecho civil contractual, calificadas por tres juristas en escala 1-5 sobre consistencia silogística y fidelidad jurídica. Concordancia medida con kappa ponderado; diferencias entre arquitecturas con Wilcoxon pareado.

---

## Resultados

### Auditoría del corpus original

Una auditoría de integridad reveló que el corpus con el que se hizo la primera corrida estaba comprometido:

- Las **411 sentencias de Corte Constitucional eran el mismo archivo repetido**: un único hash MD5. El portal migró a una aplicación Angular que devuelve HTTP 200 con su página de inicio ante rutas no reconocidas, de modo que `raise_for_status()` nunca se activaba y el scraper guardó 411 veces la misma página.
- Ese contenido aportaba **4.521 chunks al índice, de los cuales 2.466 eran hojas de estilo de Bootstrap**. Ninguno tenía contenido jurídico.
- De 301 archivos de Corte Suprema, 53 eran páginas de error y **108 escaneos sin capa de texto quedaron fuera del índice en silencio**, porque el cargador devolvía texto vacío.

Es decir: el índice original contenía 24.760 chunks útiles, no 29.281, y **cero jurisprudencia constitucional**.

### Efecto de la reparación

| Métrica | Corpus original | Corpus reparado |
|---|---:|---:|
| Chunks totales | 29.281 | **62.784** |
| Chunks de hoja de estilo | 4.521 | **0** |
| Sentencias de Corte Constitucional indexadas | **0** | 411 |
| Sentencias de Corte Suprema indexadas | 139 | 245 |
| RAG_Base respondió | 53/120 | **65/120** |
| RAG_Base citó Corte Constitucional | **0** | **40** |
| Agente respondió | 88/120 | **93/120** |
| Longitud mediana de respuesta del RAG | 281 car. | **578 car.** |
| Ejecuciones con error | 3 | **0** |

### Hallazgo pendiente: sesgo de composición

Tras la reparación, Corte Constitucional aporta **34.247 de los 62.784 chunks (55 % del índice)**, mientras el Código Civil aporta 1.138 (1,8 %). En una recuperación por similitud sin balanceo, la jurisprudencia constitucional desplaza al articulado.

El efecto es medible: en las 120 respuestas, el RAG citó 109 veces a Corte Suprema, 71 a Corte Constitucional y **solo 6 al Código Civil**. Trece preguntas que antes se respondían pasaron a «no encontrado». La composición del corpus condiciona la recuperación tanto como su calidad, y ese es un resultado en sí mismo.

### Hipótesis descartada

Se planteó que un corpus de mejor calidad reduciría las revisiones del agente, al necesitar menos autocorrección. **No se confirma**: la media pasó de 1,11 a 1,19 revisiones, con Wilcoxon pareado p = 0,096. La hipótesis se descarta explícitamente.

---

## Limitaciones

**El texto por OCR no es una transcripción certificada.** 143 sentencias se reconstruyeron ópticamente desde escaneos. Cada una fue verificada por densidad de acentos, presencia de marcas jurídicas y ausencia de residuo binario, pero persisten errores típicos en nombres propios y números de radicado. Para uso con efectos jurídicos, consulte la fuente oficial.

**Faltan 53 providencias** que las corporaciones no han digitalizado.

**El índice está desbalanceado** a favor de la jurisprudencia constitucional, como se documenta arriba.

**Las calificaciones expertas corresponden a la primera corrida.** Están atadas a las respuestas generadas sobre el corpus original; la segunda corrida aún no ha sido evaluada por los juristas.

**Un solo modelo generador.** Todos los resultados usan Gemini 2.5 Flash. No se probó si el efecto de la autoverificación se sostiene con otros modelos.

---

## Trabajo futuro

- Recuperación balanceada por categoría, con cuotas para normativa y jurisprudencia
- Filtrar las sentencias de tutela sin relación con derecho contractual
- Recalificación experta de la segunda corrida
- Replicar con al menos otro modelo generador
- Publicar el corpus en Zenodo con DOI citable

---

## Autor

**Gerardo Aguilar Gómez**
Maestría en Ciencia de Datos — Universidad Pontificia Bolivariana, Medellín, Colombia
GitHub: [@Tiritingo](https://github.com/Tiritingo)

---

## Licencia

Código bajo **MIT** (ver `LICENSE`). Datos bajo **CC BY 4.0** (ver `LICENSE-DATA`).

Las decisiones judiciales colombianas son documentos públicos y, conforme al artículo 41 de la Ley 23 de 1982, carecen de derechos de autor propios. La licencia CC BY 4.0 aplica sobre el trabajo derivado: selección, descarga verificada, normalización y transcripción.

### Cómo citar

```bibtex
@misc{aguilar2026rag,
  author = {Aguilar Guerrero, Gerardo},
  title  = {RAG vs. Agente CoT/CoV en derecho civil colombiano},
  year   = {2026},
  school = {Universidad Pontificia Bolivariana},
  url    = {https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil}
}
```
