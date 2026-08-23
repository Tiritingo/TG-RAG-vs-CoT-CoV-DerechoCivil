"""
ANÁLISIS COMPARABLE DE TRES MATRICES DE EVALUACIÓN EXPERTOS
----------------------------------------------------------
Entradas:
- matriz_calificaciones_experto_Franco.csv
- matriz_calificaciones_experto_Aristizabal.csv
- matriz_calificaciones_experto_Gonzalez.csv
- telemetria_experimento.csv

Salidas:
- matriz_expertos_larga_normalizada.csv
- auditoria_cobertura_expertos.csv
- matriz_comun_tres_expertos.csv
- matriz_pareada_agente_vs_rag.csv
- descriptivos_por_experto_y_sistema.csv
- confiabilidad_interevaluador.csv
- kappa_ponderado_pares.csv
- wilcoxon_consenso_agente_vs_rag.csv
- spearman_telemetria_calidad_agente.csv
"""

from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon, spearmanr
from sklearn.metrics import cohen_kappa_score

# CONFIGURACIÓN

ARCHIVOS = {
    "Franco": "matriz_calificaciones_experto_Franco.csv",
    "Aristizabal": "matriz_calificaciones_experto_Aristizabal.csv",
    "Gonzalez": "matriz_calificaciones_experto_Gonzalez.csv",
}

ARCHIVO_TELEMETRIA = "telemetria_experimento.csv"
CARPETA_SALIDA = Path("salidas_tres_expertos")
CARPETA_SALIDA.mkdir(exist_ok=True)

DIMENSIONES = [
    "Consistencia_Silogistica",
    "Fidelidad_Juridica",
    "Complejidad"
]

SISTEMAS = ["RAG_Base", "Agente_CoT_CoV"]

# FUNCIONES DE NORMALIZACIÓN

def estandarizar_columnas(df, experto):
    """
    Convierte cada matriz al esquema común:
    ID_Pregunta, Sistema, Experto,
    Consistencia_Silogistica, Fidelidad_Juridica, Complejidad.
    """
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    equivalencias = {
        "Consistencia_Silogistica_J2": "Consistencia_Silogistica",
        "Fidelidad_Juridica_J2": "Fidelidad_Juridica",
        "Complejidad_J2": "Complejidad",
    }
    
    df = df.rename(columns=equivalencias)

    columnas_requeridas = ["ID_Pregunta", "Sistema"] + DIMENSIONES
    faltantes = [c for c in columnas_requeridas if c not in df.columns]

    if faltantes:
        raise ValueError(
            f"La matriz del experto {experto} no contiene: {faltantes}"
        )

    df = df[columnas_requeridas].copy()
    df["Experto"] = experto

    df["ID_Pregunta"] = pd.to_numeric(
        df["ID_Pregunta"], errors="coerce"
    ).astype("Int64")

    for dimension in DIMENSIONES:
        df[dimension] = pd.to_numeric(df[dimension], errors="coerce")

    df["Sistema"] = df["Sistema"].astype(str).str.strip()

    df = df.dropna(subset=["ID_Pregunta", "Sistema"])
    df = df[df["Sistema"].isin(SISTEMAS)]

    duplicados = df.duplicated(
        subset=["ID_Pregunta", "Sistema", "Experto"],
        keep=False
    )

    if duplicados.any():
        filas = df.loc[
            duplicados,
            ["ID_Pregunta", "Sistema", "Experto"]
        ]
        raise ValueError(
            f"Hay calificaciones duplicadas para {experto}:\n{filas}"
        )

    for dimension in DIMENSIONES:
        fuera_de_rango = ~df[dimension].between(1, 5) & df[dimension].notna()

        if fuera_de_rango.any():
            raise ValueError(
                f"{experto}: hay valores fuera de la escala 1–5 "
                f"en {dimension}."
            )

    return df

def krippendorff_alpha_ordinal(matriz):
    """
    Calcula alfa de Krippendorff para datos ordinales.
    Filas: unidades evaluadas.
    Columnas: expertos.
    Se permiten faltantes, aunque el análisis principal
    se hará sobre el universo común de tres evaluadores.
    """
    valores = matriz.to_numpy(dtype=float)
    valores_validos = valores[~np.isnan(valores)]

    if len(valores_validos) < 2:
        return np.nan

    categorias = np.sort(np.unique(valores_validos))
    if len(categorias) < 2:
        return np.nan

    n_categorias = len(categorias)
    mapa = {categoria: i for i, categoria in enumerate(categorias)}

    def distancia_ordinal(a, b):
        ia = mapa[a]
        ib = mapa[b]
        return ((ia - ib) / (n_categorias - 1)) ** 2

    desacuerdo_observado_num = 0
    pares_observados = 0

    for fila in valores:
        fila = fila[~np.isnan(fila)]

        if len(fila) < 2:
            continue

        for a, b in combinations(fila, 2):
            desacuerdo_observado_num += distancia_ordinal(a, b)
            pares_observados += 1

    if pares_observados == 0:
        return np.nan

    do = desacuerdo_observado_num / pares_observados

    frecuencias = pd.Series(valores_validos).value_counts().to_dict()
    total = len(valores_validos)

    desacuerdo_esperado_num = 0
    pares_esperados = 0

    for a, b in combinations(categorias, 2):
        n_a = frecuencias.get(a, 0)
        n_b = frecuencias.get(b, 0)

        desacuerdo_esperado_num += (
            2 * n_a * n_b * distancia_ordinal(a, b)
        )
        pares_esperados += 2 * n_a * n_b

    if pares_esperados == 0:
        return np.nan

    de = desacuerdo_esperado_num / pares_esperados

    if de == 0:
        return np.nan

    return 1 - (do / de)


def interpretacion_alpha(alpha):
    if pd.isna(alpha):
        return "No estimable"

    if alpha < 0:
        return "Acuerdo inferior al esperado por azar"
    elif alpha < 0.50:
        return "Bajo"
    elif alpha < 0.67:
        return "Moderado; usar con cautela"
    elif alpha < 0.80:
        return "Aceptable/provisional"
    else:
        return "Alto"


def rank_biserial_from_wilcoxon(x, y):
    """
    Tamaño de efecto r biserial para comparación pareada.
    Se usa sobre diferencias no nulas.
    """
    diferencias = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    diferencias = diferencias[diferencias != 0]

    if len(diferencias) == 0:
        return np.nan

    rangos = pd.Series(np.abs(diferencias)).rank(method="average").to_numpy()
    w_mas = rangos[diferencias > 0].sum()
    w_menos = rangos[diferencias < 0].sum()

    return (w_mas - w_menos) / (w_mas + w_menos)

# 1. CARGA Y HOMOLOGACIÓN DE MATRICES

matrices = []

for experto, ruta in ARCHIVOS.items():
    archivo = Path(ruta)

    if not archivo.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo requerido: {archivo.resolve()}"
        )

    matriz_original = pd.read_csv(archivo, encoding="utf-8-sig")
    matriz_limpia = estandarizar_columnas(matriz_original, experto)
    matrices.append(matriz_limpia)

evaluaciones = pd.concat(matrices, ignore_index=True)

evaluaciones = evaluaciones.sort_values(
    ["ID_Pregunta", "Sistema", "Experto"]
).reset_index(drop=True)

evaluaciones.to_csv(
    CARPETA_SALIDA / "matriz_expertos_larga_normalizada.csv",
    index=False,
    encoding="utf-8-sig"
)

# 2. AUDITORÍA DE COBERTURA Y UNIVERSO COMÚN

cobertura = (
    evaluaciones
    .groupby(["Experto", "Sistema"])
    .agg(
        Registros=("ID_Pregunta", "count"),
        Preguntas_unicas=("ID_Pregunta", "nunique"),
        Min_ID=("ID_Pregunta", "min"),
        Max_ID=("ID_Pregunta", "max")
    )
    .reset_index()
)

cobertura.to_csv(
    CARPETA_SALIDA / "auditoria_cobertura_expertos.csv",
    index=False,
    encoding="utf-8-sig"
)

# Solo se comparan evaluaciones que existen en las tres matrices.
conteo_expertos_por_respuesta = (
    evaluaciones
    .groupby(["ID_Pregunta", "Sistema"])["Experto"]
    .nunique()
    .reset_index(name="N_Expertos")
)

unidades_comunes = conteo_expertos_por_respuesta.query(
    "N_Expertos == 3"
)[["ID_Pregunta", "Sistema"]]

evaluaciones_comunes = evaluaciones.merge(
    unidades_comunes,
    on=["ID_Pregunta", "Sistema"],
    how="inner"
)

evaluaciones_comunes.to_csv(
    CARPETA_SALIDA / "matriz_comun_tres_expertos.csv",
    index=False,
    encoding="utf-8-sig"
)

# 3. DESCRIPTIVOS POR EXPERTO Y ARQUITECTURA

descriptivos = (
    evaluaciones_comunes
    .melt(
        id_vars=["ID_Pregunta", "Sistema", "Experto"],
        value_vars=DIMENSIONES,
        var_name="Dimension",
        value_name="Puntaje"
    )
    .groupby(["Experto", "Sistema", "Dimension"])
    .agg(
        n=("Puntaje", "count"),
        media=("Puntaje", "mean"),
        mediana=("Puntaje", "median"),
        desviacion_estandar=("Puntaje", "std"),
        minimo=("Puntaje", "min"),
        maximo=("Puntaje", "max")
    )
    .reset_index()
    .round(3)
)

descriptivos.to_csv(
    CARPETA_SALIDA / "descriptivos_por_experto_y_sistema.csv",
    index=False,
    encoding="utf-8-sig"
)

# 4. CONFIABILIDAD INTEREVALUADOR

# Alfa de Krippendorff ordinal:
# - se calcula separadamente por dimensión y arquitectura;
# - se usan solo unidades con calificación de los 3 expertos.

resultados_alpha = []

for sistema in SISTEMAS:
    for dimension in DIMENSIONES:
        pivot = (
            evaluaciones_comunes
            .query("Sistema == @sistema")
            .pivot(
                index="ID_Pregunta",
                columns="Experto",
                values=dimension
            )
        )

        pivot = pivot.dropna()

        alpha = krippendorff_alpha_ordinal(pivot)

        resultados_alpha.append({
            "Sistema": sistema,
            "Dimension": dimension,
            "N_preguntas_tres_expertos": len(pivot),
            "Alfa_Krippendorff_ordinal": alpha,
            "Interpretacion": interpretacion_alpha(alpha)
        })

confiabilidad = pd.DataFrame(resultados_alpha).round(4)

confiabilidad.to_csv(
    CARPETA_SALIDA / "confiabilidad_interevaluador.csv",
    index=False,
    encoding="utf-8-sig"
)

# 5. KAPPA PONDERADO POR PARES DE EXPERTOS

# Complementa el alfa: muestra qué pares son más o menos concordantes.

resultados_kappa = []

for sistema in SISTEMAS:
    for dimension in DIMENSIONES:
        pivot = (
            evaluaciones_comunes
            .query("Sistema == @sistema")
            .pivot(
                index="ID_Pregunta",
                columns="Experto",
                values=dimension
            )
        )

        for experto_a, experto_b in combinations(pivot.columns, 2):
            datos_par = pivot[[experto_a, experto_b]].dropna()

            if len(datos_par) == 0:
                kappa = np.nan
            else:
                kappa = cohen_kappa_score(
                    datos_par[experto_a],
                    datos_par[experto_b],
                    weights="quadratic"
                )

            resultados_kappa.append({
                "Sistema": sistema,
                "Dimension": dimension,
                "Experto_A": experto_a,
                "Experto_B": experto_b,
                "N_preguntas": len(datos_par),
                "Kappa_ponderado_cuadratico": kappa
            })

kappa_pares = pd.DataFrame(resultados_kappa).round(4)

kappa_pares.to_csv(
    CARPETA_SALIDA / "kappa_ponderado_pares.csv",
    index=False,
    encoding="utf-8-sig"
)

# 6. CONSENSO Y COMPARACIÓN PAREADA ENTRE ARQUITECTURAS

# Se promedian las calificaciones de los tres expertos por
# pregunta y sistema. El promedio no sustituye las notas
# individuales: es una síntesis para comparar arquitecturas.

consenso = (
    evaluaciones_comunes
    .groupby(["ID_Pregunta", "Sistema"])[DIMENSIONES]
    .mean()
    .reset_index()
)

# Solo preguntas con RAG y Agente evaluados por los tres expertos.
pares = []

for dimension in DIMENSIONES:
    pivot = consenso.pivot(
        index="ID_Pregunta",
        columns="Sistema",
        values=dimension
    )

    pivot = pivot.dropna(subset=SISTEMAS).copy()
    pivot["Diferencia_Agente_menos_RAG"] = (
        pivot["Agente_CoT_CoV"] - pivot["RAG_Base"]
    )

    pivot = pivot.reset_index()
    pivot["Dimension"] = dimension
    pares.append(pivot)

matriz_pareada = pd.concat(pares, ignore_index=True)

matriz_pareada.to_csv(
    CARPETA_SALIDA / "matriz_pareada_agente_vs_rag.csv",
    index=False,
    encoding="utf-8-sig"
)

resultados_wilcoxon = []

for dimension in DIMENSIONES:
    datos = matriz_pareada.query("Dimension == @dimension").copy()

    x_agente = datos["Agente_CoT_CoV"]
    y_rag = datos["RAG_Base"]
    diferencias = x_agente - y_rag

    n_total = len(datos)
    n_no_nulas = int((diferencias != 0).sum())

    if n_no_nulas == 0:
        estadistico = np.nan
        p_valor = np.nan
        r_biserial = np.nan
    else:
        prueba = wilcoxon(
            x_agente,
            y_rag,
            alternative="two-sided",
            zero_method="wilcox",
            method="auto"
        )

        estadistico = prueba.statistic
        p_valor = prueba.pvalue
        r_biserial = rank_biserial_from_wilcoxon(x_agente, y_rag)

    resultados_wilcoxon.append({
        "Dimension": dimension,
        "N_pares": n_total,
        "N_diferencias_no_cero": n_no_nulas,
        "Media_consenso_Agente": x_agente.mean(),
        "Media_consenso_RAG": y_rag.mean(),
        "Diferencia_media_Agente_menos_RAG": diferencias.mean(),
        "Estadistico_Wilcoxon": estadistico,
        "p_valor": p_valor,
        "r_biserial": r_biserial
    })

wilcoxon_consenso = pd.DataFrame(resultados_wilcoxon).round(4)

wilcoxon_consenso.to_csv(
    CARPETA_SALIDA / "wilcoxon_consenso_agente_vs_rag.csv",
    index=False,
    encoding="utf-8-sig"
)

# 7. TELEMETRÍA Y CALIDAD DEL AGENTE: SPEARMAN

# Se correlaciona el número de revisiones con el consenso de
# calidad del Agente. Se ejecuta solo si existe telemetría.

archivo_telemetria = Path(ARCHIVO_TELEMETRIA)

if archivo_telemetria.exists():
    telemetria = pd.read_csv(archivo_telemetria, encoding="utf-8-sig")
    telemetria.columns = (
        telemetria.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    if "ID_Pregunta" in telemetria.columns:

        posibles_revision = [
            "Num_Revisiones_Agente",
            "Numero_Revisiones_Agente",
            "Num_Revisiones"
        ]

        columna_revision = next(
            (c for c in posibles_revision if c in telemetria.columns),
            None
        )

        if columna_revision is not None:
            consenso_agente = (
                consenso
                .query("Sistema == 'Agente_CoT_CoV'")
                [["ID_Pregunta"] + DIMENSIONES]
                .copy()
            )

            telemetria_reducida = telemetria[
                ["ID_Pregunta", columna_revision]
            ].copy()

            telemetria_reducida[columna_revision] = pd.to_numeric(
                telemetria_reducida[columna_revision],
                errors="coerce"
            )

            cruza_telemetria = consenso_agente.merge(
                telemetria_reducida,
                on="ID_Pregunta",
                how="inner"
            )

            resultados_spearman = []

            for dimension in DIMENSIONES:
                datos = cruza_telemetria[
                    [columna_revision, dimension]
                ].dropna()

                if len(datos) >= 3:
                    rho, p_valor = spearmanr(
                        datos[columna_revision],
                        datos[dimension]
                    )
                else:
                    rho, p_valor = np.nan, np.nan

                resultados_spearman.append({
                    "Variable_Telemetria": columna_revision,
                    "Dimension_Calidad_Agente": dimension,
                    "N": len(datos),
                    "Rho_Spearman": rho,
                    "p_valor": p_valor
                })

            pd.DataFrame(resultados_spearman).round(4).to_csv(
                CARPETA_SALIDA / "spearman_telemetria_calidad_agente.csv",
                index=False,
                encoding="utf-8-sig"
            )
            
# 8. REPORTE EJECUTIVO EN CONSOLA

print("\n" + "=" * 72)
print("ANÁLISIS FINALIZADO")
print("=" * 72)

print("\nCobertura por experto y sistema:")
print(cobertura.to_string(index=False))

print("\nUnidades comunes evaluadas por los tres expertos:")
print(
    unidades_comunes.groupby("Sistema")
    .size()
    .rename("N_respuestas")
    .to_string()
)

print("\nConfiabilidad interevaluador (alfa de Krippendorff ordinal):")
print(confiabilidad.to_string(index=False))

print("\nWilcoxon sobre consenso de los tres expertos:")
print(wilcoxon_consenso.to_string(index=False))

print(f"\nArchivos guardados en: {CARPETA_SALIDA.resolve()}")