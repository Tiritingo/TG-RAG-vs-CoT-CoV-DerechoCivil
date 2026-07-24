# 05_Codigo_Fuente

Corresponde al **Anexo A** y **Anexo B** del trabajo de grado.

Alberga los scripts y notebooks de implementación de las dos arquitecturas evaluadas, así como los módulos compartidos de recuperación, orquestación, generación y verificación iterativa.

## Configuración técnica (Anexo B)

- Segmentación semántica: `RecursiveCharacterTextSplitter`.
- Embeddings: modelo `multilingual-e5-large`.
- Indexación: ChromaDB.
- Recuperación: Relevancia Marginal Máxima (MMR), k = 5.
- **RAG Base**: generación de paso único, temperatura = 0.
- **Agente CoT-CoV**: razonamiento estructurado Chain-of-Thought + verificación iterativa Chain-of-Verification, máximo 2 ciclos de corrección.

## Estructura sugerida

```
05_Codigo_Fuente/
├── 00_Scraping/            # Scripts de extracción del corpus (Anexo A)
├── 01_Preprocesamiento/    # Limpieza, segmentación e indexación vectorial
├── 02_RAG_Base/            # Arquitectura RAG Base (paso único, temperatura 0)
├── 03_Agente_CoT_CoV/      # Orquestación, generación CoT y verificación CoV
├── 04_Prompts/             # Plantillas de instrucciones y parámetros de ejecución
├── 05_Evaluacion/          # Notebooks de evaluación estadística (Wilcoxon, Krippendorff, Kappa)
├── requirements.txt        # Dependencias del entorno Python
└── .env.example            # Variables de entorno necesarias para la ejecución (sin llaves reales)
```
