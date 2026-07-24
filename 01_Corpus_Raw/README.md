# 01_Corpus_Raw

Corresponde al **Anexo A** del trabajo de grado.

Contiene el corpus documental bruto extraído mediante el pipeline de web scraping, previo a los procesos de limpieza y segmentación. Incluye:

- Normas del Código Civil colombiano.
- Normas del Código de Comercio.
- Ley 1480 de 2011 (Estatuto del Consumidor).
- Providencias de la Corte Suprema de Justicia (Sala Civil).
- Providencias de la Corte Constitucional.

## Estructura sugerida

```
01_Corpus_Raw/
├── Codigo_Civil/
├── Codigo_Comercio/
├── Ley_1480_2011/
├── Jurisprudencia_CSJ/
└── Jurisprudencia_CConst/
```

Cada subcarpeta debe contener los archivos brutos (HTML, PDF o TXT) extraídos por los scripts de scraping ubicados en `05_Codigo_Fuente/`, junto con un archivo `metadata.csv` que documente fuente, fecha de descarga y URL original.

> Si algún archivo no puede publicarse completo por tamaño, privacidad o restricciones institucionales, indicarlo aquí y dejar la referencia en `06_Anexos/`.
