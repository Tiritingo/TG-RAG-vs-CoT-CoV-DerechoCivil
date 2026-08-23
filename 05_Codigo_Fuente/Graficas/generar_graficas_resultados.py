"""
generar_graficas_resultados.py

Script de generación de gráficas comparativas de resultados para el trabajo de
grado "ContractReason". Reproduce las Gráficas 2, 3 y 4 del informe final
(comparativa de métricas globales, calificación de consenso experto por
dimensión y fiabilidad interevaluador) utilizando matplotlib, sin marcas de
agua ni dependencias de servicios externos.

Requisitos:
    pip install matplotlib pandas numpy

Uso:
    python generar_graficas_resultados.py

Salida:
    grafica1_metricas_globales.png
    grafica2_consenso_wilcoxon.png
    grafica3_confiabilidad_interevaluador.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

COLOR_RAG = "#adac6e"
COLOR_AGENTE = "#ded3c6"


def etiquetar_barras(ax, barras, fmt="{:.1f}"):
    for barra in barras:
        altura = barra.get_height()
        ax.annotate(
            fmt.format(altura),
            xy=(barra.get_x() + barra.get_width() / 2, altura),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def grafica_metricas_globales():
    tabla1 = pd.DataFrame({
        "Metrica": [
            "Cobertura",
            "Fidelidad\nJuridica",
            "Correccion\nNormativa",
            "Integridad\nArgumentativa",
            "Consistencia\nSilogistica",
        ],
        "RAG_Base": [61.5, 62.3, 68.3, 59.6, 22.4],
        "Agente_CoT_CoV": [96.2, 81.2, 87.6, 83.1, 84.6],
    })

    x = np.arange(len(tabla1))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    b1 = ax.bar(x - ancho / 2, tabla1["RAG_Base"], ancho, label="RAG Base", color=COLOR_RAG)
    b2 = ax.bar(x + ancho / 2, tabla1["Agente_CoT_CoV"], ancho, label="Agente CoT-CoV", color=COLOR_AGENTE)

    etiquetar_barras(ax, b1)
    etiquetar_barras(ax, b2)

    ax.set_title("Rendimiento comparativo RAG Base vs Agente CoT-CoV (n=120)")
    ax.set_xlabel("Dimension evaluada")
    ax.set_ylabel("Puntaje (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla1["Metrica"])
    ax.set_ylim(0, 110)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig("grafica1_metricas_globales.png", bbox_inches="tight")
    plt.close(fig)


def grafica_consenso_wilcoxon():
    tabla_wilcoxon = pd.DataFrame({
        "Dimension": ["Consistencia\nSilogistica", "Fidelidad\nJuridica", "Complejidad\ngestionada"],
        "Media_RAG": [2.8251, 3.9454, 2.6503],
        "Media_Agente": [4.2459, 4.2131, 3.4262],
    })

    x = np.arange(len(tabla_wilcoxon))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))
    b1 = ax.bar(x - ancho / 2, tabla_wilcoxon["Media_RAG"], ancho, label="RAG Base", color=COLOR_RAG)
    b2 = ax.bar(x + ancho / 2, tabla_wilcoxon["Media_Agente"], ancho, label="Agente CoT-CoV", color=COLOR_AGENTE)

    etiquetar_barras(ax, b1, fmt="{:.2f}")
    etiquetar_barras(ax, b2, fmt="{:.2f}")

    ax.set_title("Calificacion de consenso experto por dimension (escala 1-5)")
    ax.set_xlabel("Dimension evaluada")
    ax.set_ylabel("Puntaje medio (1-5)")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla_wilcoxon["Dimension"])
    ax.set_ylim(0, 5.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig("grafica2_consenso_wilcoxon.png", bbox_inches="tight")
    plt.close(fig)


def grafica_confiabilidad_interevaluador():
    tabla_alfa = pd.DataFrame({
        "Dimension": ["Consistencia\nSilogistica", "Fidelidad\nJuridica", "Complejidad"],
        "RAG_Base": [0.8437, 0.9063, 0.9730],
        "Agente_CoT_CoV": [0.8465, 0.6998, 0.8618],
    })

    x = np.arange(len(tabla_alfa))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))
    b1 = ax.bar(x - ancho / 2, tabla_alfa["RAG_Base"], ancho, label="RAG Base", color=COLOR_RAG)
    b2 = ax.bar(x + ancho / 2, tabla_alfa["Agente_CoT_CoV"], ancho, label="Agente CoT-CoV", color=COLOR_AGENTE)

    etiquetar_barras(ax, b1, fmt="{:.3f}")
    etiquetar_barras(ax, b2, fmt="{:.3f}")

    ax.axhline(0.80, color="gray", linestyle=":", linewidth=1)
    ax.text(len(tabla_alfa) - 0.5, 0.81, "Umbral de acuerdo alto (0.80)", fontsize=9, color="gray")

    ax.set_title("Fiabilidad interevaluador por sistema y dimension (Alfa de Krippendorff)")
    ax.set_xlabel("Dimension evaluada")
    ax.set_ylabel("Alfa de Krippendorff")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla_alfa["Dimension"])
    ax.set_ylim(0, 1.1)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig("grafica3_confiabilidad_interevaluador.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    grafica_metricas_globales()
    grafica_consenso_wilcoxon()
    grafica_confiabilidad_interevaluador()
    print("Graficas generadas correctamente: grafica1_metricas_globales.png, "
          "grafica2_consenso_wilcoxon.png, grafica3_confiabilidad_interevaluador.png")
