# =============================================================================
# CELDA DE REEMPLAZO — carga del corpus limpio
#
# Sustituye a `cargar_corpus_mixto()` (celda 8 del notebook).
#
# POR QUE CAMBIA
# --------------
# El loader anterior hacia rglob("*") sobre 01_Corpus_Raw y tomaba TODO lo que
# encontrara. Hoy esa carpeta contiene tres copias del mismo corpus:
#
#   Corte_Constitucional/archivos/      411 .rtf  -> la SPA de error, inservibles
#   Corte_Constitucional/archivos_v3/   411 doc   -> descarga buena, formato mixto
#   Corte_Constitucional/texto_plano/   411 .txt  -> normalizado, ESTE es el bueno
#   Corte_Suprema/archivos/             301 .pdf  -> 53 corruptos, 143 sin OCR
#   Corte_Suprema/texto_plano/          245 .txt  -> normalizado, ESTE es el bueno
#
# Correr el loader viejo volveria a indexar el CSS de Bootstrap y a triplicar
# documentos. Este loader lee UNICAMENTE texto_plano/ y las 4 normas .md.
#
# QUE SE CONSERVA IGUAL
# ---------------------
# Prefijo "passage: " (convencion de e5), limpiar_sentencia(), el esquema de
# metadata (categoria, fuente, archivo, formato, tipo, page) y el splitter.
# Asi los resultados siguen siendo comparables con la corrida anterior.
#
# UN CAMBIO QUE DEBES CONOCER
# ---------------------------
# Antes los PDF entraban pagina por pagina, asi que limpiar_sentencia() se
# aplicaba a cada pagina por separado y casi nunca recortaba nada. Ahora cada
# sentencia entra como un documento completo, asi que el recorte
# CONSIDERACIONES -> Copiese/Notifiquese SI opera de verdad. Es el
# comportamiento que la funcion siempre busco, pero cambia el numero de chunks
# frente a la corrida anterior. Documentalo en la metodologia.
# =============================================================================

# -----------------------------------------------------------------------------
# ESTO NO ES UN SCRIPT: es una celda para pegar en el notebook de Colab.
# Depende de nombres definidos en celdas anteriores. Si lo ejecutas suelto,
# falla con ModuleNotFoundError o NameError.
# -----------------------------------------------------------------------------
_REQUISITOS = ["CORPUS_PATH", "emb", "VECTOR_LOCAL", "VECTOR_DRIVE",
               "parse_markdown_articulos", "limpiar_sentencia",
               "RecursiveCharacterTextSplitter", "Chroma", "os", "shutil"]
_faltan = [n for n in _REQUISITOS if n not in dir()]
if _faltan:
    raise SystemExit(
        "\n" + "=" * 70 + "\n"
        "NO EJECUTES ESTE ARCHIVO DIRECTAMENTE\n" + "=" * 70 + "\n"
        "Es el contenido de una celda del notebook\n"
        "v2_RAG_vs_CoT_CoV_DerechoCivil.ipynb, pensada para Colab con GPU.\n\n"
        "Faltan en el entorno: %s\n\n"
        "COMO USARLO\n"
        "  1. Abre el notebook en Google Colab (Entorno de ejecucion -> T4).\n"
        "  2. Ejecuta las celdas 1 a 7 tal como estan.\n"
        "  3. Copia TODO este archivo y pegalo reemplazando la celda 8\n"
        "     (cargar_corpus_mixto) y la celda 10 (build_vectorstore).\n"
        "  4. Ejecuta esa celda.\n\n"
        "Se corre en Colab porque el modelo multilingual-e5-large necesita\n"
        "GPU: en CPU, embeber ~50.000 chunks pasa de 3 horas.\n"
        % ", ".join(_faltan[:6]) + "=" * 70)

from pathlib import Path
from langchain_core.documents import Document

CORPUS = Path(CORPUS_PATH)

CARPETAS_TEXTO = [
    CORPUS / "Sentencias" / "Corte_Suprema" / "texto_plano",
    CORPUS / "Sentencias" / "Corte_Constitucional" / "texto_plano",
]

# marcas de que algo del corpus roto se colo pese a todo
CENTINELAS = [
    "--bs-blue", "data-beasties-container", "<style", "sharethis-js",
    "DOCUMENTO NO DISPONIBLE", "font-family:",
]


def _categoria_desde_ruta(archivo: Path) -> str:
    partes = {p.name for p in archivo.parents}
    if "Corte_Constitucional" in partes:
        return "Corte_Constitucional"
    if "Corte_Suprema" in partes:
        return "Sentencias"
    return archivo.parent.name


def cargar_corpus_limpio(verbose: bool = True):
    docs = []
    stats = {"normas": 0, "articulos": 0, "sentencias": 0,
             "vacias": 0, "contaminadas": 0}

    # ---------- 1) normas: los 4 markdown ----------
    for md in sorted(CORPUS.glob("*/*.md")):
        texto = md.read_text(encoding="utf-8")
        arts = parse_markdown_articulos(texto, str(md), md.parent.name)
        docs.extend(arts)
        stats["normas"] += 1
        stats["articulos"] += len(arts)
        if verbose:
            print(f"[MD ] {md.parent.name:<18} {md.name:<28} {len(arts)} articulos")

    # ---------- 2) sentencias: solo texto_plano ----------
    for carpeta in CARPETAS_TEXTO:
        if not carpeta.is_dir():
            print(f"AVISO: no existe {carpeta}")
            continue

        archivos = sorted(carpeta.glob("*.txt"))
        categoria = _categoria_desde_ruta(archivos[0]) if archivos else "?"
        n_ok = 0

        for f in archivos:
            texto = f.read_text(encoding="utf-8", errors="ignore")

            sucio = [c for c in CENTINELAS if c in texto[:4000]]
            if sucio:
                stats["contaminadas"] += 1
                print(f"  DESCARTADO {f.name[:45]} -> contiene {sucio[0]}")
                continue

            texto = limpiar_sentencia(texto).strip()
            if len(texto) <= 30:
                stats["vacias"] += 1
                continue

            docs.append(Document(
                page_content="passage: " + texto,
                metadata={
                    "categoria": categoria,
                    "fuente": f.stem,
                    "archivo": f.name,
                    "formato": "txt",
                    "tipo": "sentencia",
                    "page": 0,
                },
            ))
            n_ok += 1

        stats["sentencias"] += n_ok
        if verbose:
            print(f"[TXT] {categoria:<18} {carpeta.parent.name:<28} {n_ok} sentencias")

    print("\n" + "=" * 58)
    print(f"Normas          : {stats['normas']} archivos -> {stats['articulos']} articulos")
    print(f"Sentencias      : {stats['sentencias']}")
    print(f"Descartadas     : {stats['contaminadas']} contaminadas, {stats['vacias']} vacias")
    print(f"TOTAL documentos: {len(docs)}")
    print("=" * 58)

    if stats["contaminadas"]:
        raise RuntimeError(
            f"{stats['contaminadas']} documentos traian marcas del corpus roto. "
            "Revisa texto_plano/ antes de indexar."
        )
    return docs


def build_vectorstore_limpio():
    """Reemplaza a build_vectorstore(). Mismo splitter, corpus distinto."""
    docs = cargar_corpus_limpio()
    if not docs:
        print("No se cargo ningun documento")
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        separators=["\n## ", "\n---\n", "\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"\nChunks generados: {len(chunks)}")

    # ---------- red de seguridad antes de gastar GPU ----------
    malos = [c for c in chunks
             if any(s in c.page_content for s in CENTINELAS)]
    if malos:
        print(f"\nABORTADO: {len(malos)} chunks con marcas de basura. Ejemplo:")
        print(malos[0].page_content[:200])
        return None
    print("Verificacion: 0 chunks contaminados\n")

    print("Generando embeddings...")
    if os.path.exists(VECTOR_LOCAL):
        shutil.rmtree(VECTOR_LOCAL)
    os.makedirs(VECTOR_LOCAL, exist_ok=True)

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=emb,
        persist_directory=VECTOR_LOCAL,
    )

    if os.path.exists(VECTOR_DRIVE):
        shutil.rmtree(VECTOR_DRIVE)
    shutil.copytree(VECTOR_LOCAL, VECTOR_DRIVE)

    print(f"\n{len(chunks)} chunks indexados")
    print("Backup guardado en Drive")
    return vs


# =============================================================================
# EJECUTAR
# =============================================================================
vectorstore = build_vectorstore_limpio()

# ---------- comprobacion posterior ----------
if vectorstore is not None:
    import collections
    col = vectorstore._collection
    print(f"\nEmbeddings en el indice: {col.count()}")
    meta = col.get(include=["metadatas"])["metadatas"]
    print("Chunks por categoria:")
    for k, v in collections.Counter(m.get("categoria") for m in meta).most_common():
        print(f"   {k:<24} {v:6d}")
    print("Documentos distintos:",
          len({m.get("archivo") for m in meta}))
