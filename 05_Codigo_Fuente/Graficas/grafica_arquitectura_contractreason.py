"""
Anexo técnico: generación programática de la Figura 1 de ContractReason.
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

OUT = Path(__file__).with_name("figura_1_diseno_comparativo_contractreason.png")

COLORS = {
    "blue": "#2878B5", "orange": "#C75C1E", "green": "#4B7026",
    "purple": "#7C3D9C", "amber": "#F18E22", "navy": "#233C53",
    "text": "#1F2937", "muted": "#5B6573", "red": "#D7261E"
}


def box(ax, x, y, w, h, text, color, fontsize=10):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color="white",
            fontsize=fontsize, fontweight="bold", wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#6B7280", lw=1.4):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, linewidth=lw, color=color))


def panel(ax, x, title, border, steps, step_colors):
    y0, w, h = 1.5, 2.55, 0.58
    ax.add_patch(Rectangle((x, 1.42), 3.0, 5.95, fill=False, linewidth=1.5,
                           linestyle=(0, (4, 3)), edgecolor=border))
    ax.text(x + 1.5, 7.12, title, ha="center", va="bottom", fontsize=11,
            fontweight="bold", color=COLORS["text"])
    ys = [6.12, 5.10, 4.08, 3.06, 2.04]
    for i, (label, color) in enumerate(zip(steps, step_colors)):
        box(ax, x + 0.22, ys[i], w, h, label, color, fontsize=9)
        if i < len(steps) - 1:
            arrow(ax, x + 1.5, ys[i], x + 1.5, ys[i + 1] + h)


def main():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    fig.text(0.5, 0.955, "Figura 1. Diseño comparativo de la solución experimental — ContractReason",
             ha="center", va="top", fontsize=15, fontweight="bold", color=COLORS["text"])
    fig.text(0.5, 0.915, "Ambos sistemas comparten corpus y base vectorial; divergen en procesamiento de consulta y generación",
             ha="center", va="top", fontsize=10.5, color=COLORS["muted"])

    panel(ax, 0.60, "Sistema RAG Base", "#8DB9D7",
          ["Consulta + Embedding", "Recuperación k=5", "Prompt contextualizado", "GPT-4-turbo (1 llamada)", "Respuesta final"],
          [COLORS["blue"]] * 5)
    panel(ax, 10.40, "Agente Cognitivo CoT-CoV", "#CFA4D9",
          ["Consulta + Embedding", "Recuperación k=5", "CoT: silogismo jurídico", "Borrador + extracción CoV", "Verificación CoV (1-2 ciclos)"],
          [COLORS["blue"], COLORS["blue"], COLORS["purple"], COLORS["purple"], COLORS["amber"]])
    box(ax, 10.62, 2.04, 2.55, 0.58, "Respuesta final validada", COLORS["navy"], fontsize=9)

    box(ax, 4.92, 5.73, 4.16, 1.60,
        "Corpus jurídico\nDerecho Contractual Civil Colombiano\nC.C., C. Co., Ley 1480 y jurisprudencia CSJ\n1.368 fragmentos · chunking 512t",
        COLORS["orange"], fontsize=9)
    box(ax, 4.92, 4.38, 4.16, 0.68,
        "Base vectorial Chroma\ntext-embedding-3-large · 1.536d · similitud coseno",
        COLORS["green"], fontsize=8.5)
    arrow(ax, 4.92, 4.72, 3.60, 4.72, color=COLORS["green"], lw=1.8)
    arrow(ax, 9.08, 4.72, 10.40, 4.72, color=COLORS["green"], lw=1.8)

    ax.text(7.0, 3.85, "Diferencias clave →", ha="center", va="center", fontsize=9.5,
            color=COLORS["red"], fontweight="bold")
    ax.text(7.0, 3.35, "RAG: 1 llamada LLM · sin verificación\nAgente: 2-4 llamadas · CoV iterativo\nLatencia: 2.8 s vs 11.4 s (p50)",
            ha="center", va="center", fontsize=8.5, color=COLORS["text"])
    fig.text(0.5, 0.055, "Nota. El corpus y la base vectorial son idénticos para ambos sistemas, garantizando comparabilidad experimental.",
             ha="center", va="bottom", fontsize=8, color="#707070")

    fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
