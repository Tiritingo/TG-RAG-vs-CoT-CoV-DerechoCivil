# -*- coding: utf-8 -*-
"""
PARTE 2 — ANÁLISIS ESTADÍSTICO (Wilcoxon y Spearman)
======================================================
Cruza:
  (a) `telemetria_experimento.csv`         -> Parte 1 (automática)
  (b) `matriz_calificaciones_expertos.csv` -> evaluación cualitativa del
      jurista sobre Consistencia_Silogistica, Fidelidad_Juridica y
      Complejidad, para cada respuesta evaluable de cada arquitectura.

Pruebas ejecutadas:
  1. Wilcoxon (rangos con signo, pareado) RAG_Base vs Agente_CoT_CoV,
     para cada una de las 3 métricas dogmáticas, restringido a las
     preguntas en que AMBAS arquitecturas produjeron una respuesta
     evaluable (excluye rechazos puros del RAG y errores 503 del Agente).
  2. Spearman entre Num_Revisiones_Agente (bucle de verificación
     autónoma) y cada métrica dogmática del Agente, para explorar si
     más iteraciones de auto-verificación se asocian con mejor calidad.
  3. Spearman entre las tres métricas dogmáticas entre sí (validez
     convergente / independencia de los constructos evaluados).

IMPORTANTE: las calificaciones dogmáticas (Consistencia_Silogistica,
Fidelidad_Juridica, Complejidad) son juicios cualitativos de un jurista
experto en derecho civil colombiano sobre el texto de cada respuesta.
Este script NO las genera; solo las consume desde
`matriz_calificaciones_expertos.csv`.
"""

import pandas as pd
import numpy as np
from scipy import stats

TELEMETRIA_CSV = "/home/claude/work/telemetria_experimento.csv"
MATRIZ_CSV = "/home/claude/work/matriz_calificaciones_expertos.csv"

METRICAS = ["Consistencia_Silogistica", "Fidelidad_Juridica", "Complejidad"]


def cargar_y_cruzar():
    telemetria = pd.read_csv(TELEMETRIA_CSV)
    matriz = pd.read_csv(MATRIZ_CSV)

    # Formato ancho: una fila por pregunta, columnas *_RAG y *_Agente
    ancho = matriz.pivot(index="ID_Pregunta", columns="Sistema",
                          values=METRICAS)
    ancho.columns = [f"{m}_{sis.replace('Agente_CoT_CoV','Agente')}"
                      for m, sis in ancho.columns]
    ancho = ancho.reset_index()

    cruce = telemetria.merge(ancho, on="ID_Pregunta", how="left")
    return cruce


def prueba_wilcoxon(cruce: pd.DataFrame):
    print("=" * 70)
    print("1) WILCOXON (rangos con signo, pareado): RAG_Base vs Agente_CoT_CoV")
    print("=" * 70)
    resultados = []
    for metrica in METRICAS:
        col_rag = f"{metrica}_RAG_Base"
        col_agente = f"{metrica}_Agente"
        pares = cruce[[col_rag, col_agente]].dropna()
        n = len(pares)
        if n < 5:
            print(f"{metrica}: N insuficiente ({n}) para la prueba.")
            continue
        # Wilcoxon requiere excluir diferencias de cero o usar zero_method
        stat, p = stats.wilcoxon(pares[col_agente], pares[col_rag],
                                  zero_method="wilcox", alternative="two-sided")
        mediana_rag = pares[col_rag].median()
        mediana_agente = pares[col_agente].median()
        # Tamaño del efecto rank-biserial aproximado
        diffs = pares[col_agente] - pares[col_rag]
        r_rb = (np.sum(diffs > 0) - np.sum(diffs < 0)) / n
        print(f"\n{metrica} (N pares = {n}):")
        print(f"  Mediana RAG_Base = {mediana_rag:.1f} | "
              f"Mediana Agente_CoT_CoV = {mediana_agente:.1f}")
        print(f"  Estadístico W = {stat:.2f} | p-valor = {p:.6f}")
        print(f"  r rank-biserial (efecto) = {r_rb:.3f} "
              f"({'Agente > RAG' if r_rb > 0 else 'RAG > Agente'} en signo)")
        print(f"  Significativo a alpha=0.05: {'SI' if p < 0.05 else 'NO'}")
        resultados.append({
            "metrica": metrica, "n_pares": n,
            "mediana_RAG": mediana_rag, "mediana_Agente": mediana_agente,
            "W": stat, "p_valor": p, "r_rank_biserial": r_rb,
        })
    return pd.DataFrame(resultados)


def prueba_spearman_revisiones(cruce: pd.DataFrame):
    print("\n" + "=" * 70)
    print("2) SPEARMAN: Num_Revisiones_Agente vs métricas dogmáticas (Agente)")
    print("=" * 70)
    resultados = []
    for metrica in METRICAS:
        col = f"{metrica}_Agente"
        sub = cruce[["Num_Revisiones_Agente", col]].dropna()
        n = len(sub)
        rho, p = stats.spearmanr(sub["Num_Revisiones_Agente"], sub[col])
        print(f"\n{metrica} (N = {n}):")
        print(f"  rho de Spearman = {rho:.3f} | p-valor = {p:.6f}")
        print(f"  Significativo a alpha=0.05: {'SI' if p < 0.05 else 'NO'}")
        resultados.append({"metrica": metrica, "n": n, "rho": rho, "p_valor": p})
    return pd.DataFrame(resultados)


def prueba_spearman_intermetricas(cruce: pd.DataFrame):
    print("\n" + "=" * 70)
    print("3) SPEARMAN entre métricas dogmáticas del Agente (validez convergente)")
    print("=" * 70)
    cols = [f"{m}_Agente" for m in METRICAS]
    sub = cruce[cols].dropna()
    corr = sub.corr(method="spearman")
    corr.columns = METRICAS
    corr.index = METRICAS
    print(corr.round(3).to_string())
    return corr


def main():
    cruce = cargar_y_cruzar()
    cruce.to_csv("/home/claude/work/dataset_cruzado.csv", index=False)

    res_wilcoxon = prueba_wilcoxon(cruce)
    res_spearman_rev = prueba_spearman_revisiones(cruce)
    res_spearman_inter = prueba_spearman_intermetricas(cruce)

    res_wilcoxon.to_csv("/home/claude/work/resultados_wilcoxon.csv", index=False)
    res_spearman_rev.to_csv("/home/claude/work/resultados_spearman_revisiones.csv", index=False)

    print("\n\nArchivos generados: dataset_cruzado.csv, resultados_wilcoxon.csv, "
          "resultados_spearman_revisiones.csv")


if __name__ == "__main__":
    main()
