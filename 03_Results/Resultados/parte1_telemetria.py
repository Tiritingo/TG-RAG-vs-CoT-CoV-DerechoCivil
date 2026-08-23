# -*- coding: utf-8 -*-
"""
PARTE 1 — TELEMETRÍA DEL EXPERIMENTO
=====================================
Extrae automáticamente, a partir de `resultados_comparativos.csv`, las
métricas de trazabilidad del experimento que NO requieren juicio jurídico:

  - Cobertura de cada arquitectura (¿produjo una respuesta sustantiva?)
  - Distribución del número de revisiones del bucle de verificación
    autónoma del Agente (Num_Revisiones_Agente)
  - Tasa de error técnico (fallas de API) del Agente
  - Longitud de las respuestas (proxy cuantitativo, no dogmático)

Este script NO evalúa la calidad jurídica de los textos (eso corresponde
a la matriz de calificaciones de expertos, construida por separado en
`matriz_calificaciones_expertos.csv`). Su única función es describir
CÓMO se comportó la infraestructura durante la generación de las 120
respuestas por arquitectura.

Salida: `telemetria_experimento.csv` (una fila por pregunta) +
        resumen impreso en consola.
"""

import pandas as pd
import numpy as np

INPUT_CSV = "/mnt/user-data/uploads/resultados_comparativos.csv"
OUTPUT_CSV = "/home/claude/work/telemetria_experimento.csv"

REFUSAL_STR = "No encontrado en el corpus"


def cargar_datos(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    columnas_esperadas = {
        "ID_Pregunta", "Pregunta", "Respuesta_RAG_Base",
        "Respuesta_Agente_CoT_CoV", "Num_Revisiones_Agente", "Error",
    }
    faltantes = columnas_esperadas - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas esperadas en el CSV: {faltantes}")
    return df


def construir_telemetria(df: pd.DataFrame) -> pd.DataFrame:
    t = df.copy()

    # --- Longitudes (proxy cuantitativo de extensión, no de calidad) ---
    t["Longitud_RAG"] = t["Respuesta_RAG_Base"].astype(str).str.len()
    t["Longitud_Agente"] = t["Respuesta_Agente_CoT_CoV"].astype(str).str.len()
    t.loc[t["Respuesta_Agente_CoT_CoV"].isna(), "Longitud_Agente"] = np.nan

    # --- Cobertura RAG_Base: ¿produjo una respuesta sustantiva? ---
    # El sistema RAG_Base emite el string fijo "No encontrado en el corpus..."
    # cuando el contexto recuperado no basta para responder. Se lo trata
    # como "sin cobertura" salvo que, además del rechazo, incluya
    # desarrollo adicional sustantivo (rechazo parcial).
    es_rechazo_puro = t["Respuesta_RAG_Base"].astype(str).str.strip() == (
        "No encontrado en el corpus. El contexto recuperado no contiene "
        "información suficiente para responder."
    )
    contiene_rechazo = t["Respuesta_RAG_Base"].astype(str).str.contains(
        REFUSAL_STR, na=False
    )
    t["RAG_cobertura"] = np.select(
        [es_rechazo_puro, contiene_rechazo & ~es_rechazo_puro],
        ["sin_cobertura", "cobertura_parcial"],
        default="cobertura_total",
    )

    # --- Cobertura Agente_CoT_CoV: ¿hubo error técnico de API? ---
    t["Agente_error_tecnico"] = t["Error"].notna()
    t["Agente_cobertura"] = np.where(
        t["Agente_error_tecnico"], "error_tecnico", "cobertura_total"
    )

    columnas_salida = [
        "ID_Pregunta", "Num_Revisiones_Agente",
        "RAG_cobertura", "Agente_cobertura", "Agente_error_tecnico",
        "Longitud_RAG", "Longitud_Agente",
    ]
    return t[columnas_salida]


def resumen_telemetria(t: pd.DataFrame, df_original: pd.DataFrame) -> None:
    n = len(t)
    print("=" * 70)
    print(f"TELEMETRÍA DEL EXPERIMENTO (n = {n} preguntas)")
    print("=" * 70)

    # --- Cobertura ---
    print("\n--- Cobertura por arquitectura ---")
    cov_rag = t["RAG_cobertura"].value_counts()
    cov_agent = t["Agente_cobertura"].value_counts()
    rag_ok = (t["RAG_cobertura"] != "sin_cobertura").sum()
    agent_ok = (t["Agente_cobertura"] == "cobertura_total").sum()
    print(f"RAG_Base:        {rag_ok}/{n} respuestas sustantivas "
          f"({rag_ok/n:.1%})  |  detalle: {cov_rag.to_dict()}")
    print(f"Agente_CoT_CoV:  {agent_ok}/{n} respuestas sin error técnico "
          f"({agent_ok/n:.1%})  |  detalle: {cov_agent.to_dict()}")

    # --- Distribución de revisiones del bucle de verificación ---
    print("\n--- Distribución de Num_Revisiones_Agente (bucle CoV) ---")
    revisiones = df_original["Num_Revisiones_Agente"]
    print(revisiones.value_counts().sort_index().to_string())
    print(f"\nMedia:   {revisiones.mean():.3f}")
    print(f"Mediana: {revisiones.median():.3f}")
    print(f"Moda:    {revisiones.mode().iloc[0]}")
    print(f"Desv.Est:{revisiones.std():.3f}")

    # Relación entre revisiones y si el RAG había fallado (variable de control)
    rag_fallo = t["RAG_cobertura"] == "sin_cobertura"
    print("\n--- Revisiones del Agente según si RAG_Base fue sin cobertura ---")
    print(t.groupby(rag_fallo)["Num_Revisiones_Agente"]
          .agg(["count", "mean", "std"])
          .rename(index={True: "RAG sin cobertura", False: "RAG con cobertura"}))

    # --- Longitudes ---
    print("\n--- Longitud de respuesta (caracteres) ---")
    print(t[["Longitud_RAG", "Longitud_Agente"]].describe().to_string())


def main():
    df = cargar_datos(INPUT_CSV)
    telemetria = construir_telemetria(df)
    telemetria.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    resumen_telemetria(telemetria, df)
    print(f"\nTelemetría guardada en: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
