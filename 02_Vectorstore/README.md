# 02_Vectorstore

Corresponde al **Anexo A** y **Anexo B** del trabajo de grado.

Almacena la configuración y los artefactos de la base de datos vectorial ChromaDB utilizada por ambas arquitecturas (RAG Base y Agente CoT-CoV). Incluye:

- Fragmentos segmentados mediante `RecursiveCharacterTextSplitter`.
- Metadatos de trazabilidad de cada fragmento (fuente normativa/jurisprudencial, artículo, sección).
- Representaciones vectoriales generadas con el modelo `multilingual-e5-large`.
- Configuración de indexación y parámetros de recuperación por Relevancia Marginal Máxima (MMR, k = 5).

## Estructura sugerida

```
02_Vectorstore/
├── chroma_db/            # Artefactos persistidos de ChromaDB
├── chunks/                # Fragmentos segmentados + metadatos (JSON/CSV)
└── config/                # Parámetros de embedding, chunking y MMR (YAML/JSON)
```

> Si la base vectorial completa excede los límites de tamaño de GitHub, publicar una muestra representativa y documentar el enlace de acceso completo (Drive, Zenodo, etc.) en `06_Anexos/`.
