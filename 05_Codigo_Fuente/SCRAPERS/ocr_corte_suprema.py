#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_corte_suprema.py — Normaliza el corpus de Corte Suprema a texto plano.

Diagnostico que motiva este script (verificado sobre los 245 PDF unicos):

    132 documentos CON capa de texto  ->  los 132 estan en el vectorstore
    113 documentos SIN capa de texto  ->  108 se cayeron del indice en silencio
                                          5 entraron con chunks casi vacios

Es decir: la indexacion no fallo. PyPDFLoader devolvia texto vacio para los
escaneos y LangChain los descartaba sin avisar. El unico arreglo es OCR.

    132 docs con texto  ->  extraccion directa, segundos
    113 docs escaneados ->  OCR, 5.513 paginas

REQUISITOS
----------
1) Tesseract con idioma espanol.
   Windows: https://github.com/UB-Mannheim/tesseract/wiki
            (en el instalador marca Spanish en "Additional language data")
   Verifica:  tesseract --list-langs      debe aparecer 'spa'

2) pip install pymupdf pytesseract pillow
   PyMuPDF rasteriza sin depender de poppler ni ghostscript: en Windows
   es mucho menos fragil que pdf2image.

USO
---
    python ocr_corte_suprema.py              # todo, con todos los nucleos
    python ocr_corte_suprema.py --workers 4  # limitar paralelismo
    python ocr_corte_suprema.py --solo-texto # saltar el OCR, solo los 132

Es re-ejecutable: salta lo ya hecho. Puedes cortarlo con Ctrl-C y retomarlo.

Autor: Gerardo Aguilar — UPB, Maestría en Ciencia de Datos
"""
import argparse, csv, hashlib, os, re, sys, time, warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

warnings.filterwarnings("ignore")


def cargar_pymupdf():
    """
    PyMuPDF moderno se importa como 'pymupdf'; 'fitz' es el alias antiguo
    y emite un aviso de deprecacion por cada subproceso. Preferimos el nuevo
    y caemos al viejo solo si hace falta.
    """
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz

# ============================== CONFIG ==============================
# La raiz se deduce de la ubicacion del script:
#   <RAIZ>/05_Codigo_Fuente/SCRAPERS/ocr_corte_suprema.py
# Asi el proyecto se puede mover de carpeta sin editar nada.
RAIZ = Path(__file__).resolve().parent.parent.parent
ORIGEN = RAIZ / "01_Corpus_Raw" / "Sentencias" / "Corte_Suprema" / "archivos"
DESTINO = RAIZ / "01_Corpus_Raw" / "Sentencias" / "Corte_Suprema" / "texto_plano"
DPI = 300                  # 300 es el punto dulce para texto impreso
IDIOMA = "spa"
UMBRAL_ESCANEO = 200       # chars/pagina por debajo de esto => sin capa de texto
MIN_CHARS = 1500           # salida minima aceptable
# ====================================================================

RE_JUR = re.compile(
    r"\b(corte suprema|sala de casaci[óo]n|magistrad[oa] ponente|recurso de casaci[óo]n|"
    r"demandante|demandado|sentencia|providencia|C[óo]digo Civil|contrato|obligaci[óo]n)\b",
    re.I)


def es_pdf(p):
    try:
        with open(p, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except OSError:
        return False


def preflight(necesita_ocr):
    """
    Verifica Tesseract ANTES de procesar. Fallar rapido y con instrucciones.
    Devuelve la ruta al ejecutable si hubo que resolverla a mano, o None si
    ya estaba en el PATH. Hay que propagarla a los workers: cada subproceso
    reimporta pytesseract limpio y no hereda tesseract_cmd del padre.
    """
    if not necesita_ocr:
        return None
    try:
        import pytesseract
    except ImportError:
        sys.exit("Falta pytesseract.  pip install pytesseract pillow")

    # en Windows el instalador no toca el PATH; buscamos las rutas tipicas
    candidatos = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    resuelto = None
    try:
        idiomas = pytesseract.get_languages(config="")
    except Exception:
        hallado = next((c for c in candidatos if Path(c).exists()), None)
        if not hallado:
            sys.exit(
                "\n" + "=" * 68 + "\n"
                "TESSERACT NO ESTA INSTALADO\n" + "=" * 68 + "\n"
                "pip instala el conector de Python, pero el motor de OCR es un\n"
                "programa aparte que hay que instalar a mano.\n\n"
                "Windows:\n"
                "  1. Descarga el instalador de UB Mannheim:\n"
                "     https://github.com/UB-Mannheim/tesseract/wiki\n"
                "  2. Durante la instalacion abre 'Additional language data'\n"
                "     y MARCA 'Spanish'. Sin esto el OCR sale sin acentos.\n"
                "  3. Vuelve a correr este script.\n\n"
                "Comprueba con:  tesseract --list-langs      (debe salir 'spa')\n"
                + "=" * 68)
        pytesseract.pytesseract.tesseract_cmd = hallado
        resuelto = hallado
        print("Tesseract hallado en: %s" % hallado)
        try:
            idiomas = pytesseract.get_languages(config="")
        except Exception as e:
            sys.exit("Tesseract existe pero no responde: %s" % e)

    if IDIOMA not in idiomas:
        sys.exit(
            "\n" + "=" * 68 + "\n"
            "FALTA EL IDIOMA ESPANOL EN TESSERACT\n" + "=" * 68 + "\n"
            "Idiomas disponibles: %s\n\n"
            "Reinstala Tesseract marcando 'Spanish' en 'Additional language\n"
            "data', o descarga spa.traineddata desde\n"
            "  https://github.com/tesseract-ocr/tessdata\n"
            "y copialo en la carpeta tessdata de tu instalacion.\n"
            "%s" % (", ".join(sorted(idiomas)), "=" * 68))

    print("Tesseract OK — idiomas: %s" % ", ".join(sorted(idiomas)))
    return resuelto


def salida_valida(ruta_txt):
    """
    Una salida previa solo cuenta si su contenido sirve.
    Comprobar solo el tamano deja pasar .txt llenos de mojibake escritos
    por una version anterior del clasificador.
    """
    try:
        t = Path(ruta_txt).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    if len(t) < MIN_CHARS:
        return False
    if mojibake(t) > 0.005:
        return False
    if densidad_acentos(t) < MIN_ACENTOS:
        return False
    return len(RE_JUR.findall(t)) >= 3


RE_HEXBLOB = re.compile(r"[0-9a-f]{200,}", re.I)
RE_ACENTO = re.compile(r"[áéíóúñÁÉÍÓÚÑ]")
MIN_ACENTOS = 3.0        # por cada 1000 caracteres


def limpiar(t):
    t = (t or "").replace("\x00", " ").replace("\r", "\n")
    t = RE_HEXBLOB.sub(" ", t)          # imagenes incrustadas volcadas en hex
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def densidad_acentos(t):
    """
    Acentos y enes por cada 1000 caracteres.
    Un texto juridico en espanol ronda 14-18 (medido sobre los 656 documentos
    del corpus). Algunas providencias traen una capa de texto producida por un
    OCR degradado de la propia Corte que pierde TODAS las tildes y confunde
    letras: 'Gone Suprema de Justioia', 'Sala de Casacibn'. Volumen y palabras
    clave pasan los filtros, pero el texto es inservible para embeddings.
    """
    if not t:
        return 0.0
    return len(RE_ACENTO.findall(t)) / len(t) * 1000


def texto_nativo(ruta, max_pag=None):
    """Extrae la capa de texto con PyMuPDF. Devuelve (texto, n_paginas)."""
    doc = cargar_pymupdf().open(ruta)
    try:
        n = doc.page_count
        lim = n if max_pag is None else min(n, max_pag)
        return "\n".join(doc[i].get_text() for i in range(lim)), n
    finally:
        doc.close()


def mojibake(t):
    """
    Proporcion de caracteres imposibles en un texto juridico en espanol.
    Algunos PDF traen una capa de texto producida por un OCR defectuoso cuyo
    CMap mapea los glifos a codepoints equivocados: salen katakana japoneses
    y anchos completos donde deberia haber letras. Ejemplo real del corpus:
        'Repdbl i cadeCol ombi a'  en vez de  'Republica de Colombia'
        'SaI a〃ecaSacl enc師i'     en vez de  'Sala de Casacion Civil'
    Volumen de texto hay de sobra, pero es ilegible: toca OCR igual.
    """
    if not t:
        return 0.0
    raros = sum(1 for c in t if ("　" <= c <= "鿿") or ("＀" <= c <= "￯"))
    return raros / len(t)


def clasificar(ruta):
    """
    (sirve_la_capa_de_texto, n_paginas).
    No basta con medir volumen: hay que comprobar que el texto sea legible.
    """
    try:
        t, n = texto_nativo(ruta, max_pag=10)
    except Exception:
        return False, 0

    muestreadas = max(1, min(n, 10))
    if (len(t) / muestreadas) < UMBRAL_ESCANEO:
        return False, n                      # escaneo puro, sin capa de texto
    if mojibake(t) > 0.005:
        return False, n                      # capa de texto con CMap roto
    if len(t) > 3000 and densidad_acentos(t) < MIN_ACENTOS:
        return False, n                      # OCR degradado: perdio todas las tildes
    if len(t) > 3000 and len(RE_JUR.findall(t)) < 2:
        return False, n                      # volumen alto sin una sola marca -> ilegible
    return True, n


# ------------------------------------------------------- worker (subproceso)

def procesar(args):
    ruta, salida, hacer_ocr, dpi, idioma, tess_cmd = args
    nombre = Path(ruta).name
    t0 = time.time()
    try:
        if not hacer_ocr:
            texto, n = texto_nativo(ruta)
            metodo = "nativo"
        else:
            import io, pytesseract
            from PIL import Image
            # cada worker es un proceso nuevo: no hereda tesseract_cmd del padre
            if tess_cmd:
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
            pmu = cargar_pymupdf()
            doc = pmu.open(ruta)
            n = doc.page_count
            partes = []
            try:
                zoom = dpi / 72.0
                mat = pmu.Matrix(zoom, zoom)
                for i in range(n):
                    pix = doc[i].get_pixmap(matrix=mat, colorspace=pmu.csGRAY)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    partes.append(pytesseract.image_to_string(img, lang=idioma, config="--psm 1"))
            finally:
                doc.close()
            texto = "\n".join(partes)
            metodo = "ocr"

        texto = limpiar(texto)
        hits = len(RE_JUR.findall(texto))
        if len(texto) < MIN_CHARS or hits < 3:
            return (nombre, metodo, n, len(texto), hits, "SOSPECHOSO",
                    "%d chars, %d marcas" % (len(texto), hits), time.time() - t0)
        Path(salida).write_text(texto, encoding="utf-8")
        return (nombre, metodo, n, len(texto), hits, "OK", "", time.time() - t0)
    except Exception as e:
        return (nombre, "", 0, 0, 0, "ERROR", str(e)[:110], time.time() - t0)


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--solo-texto", action="store_true", help="Omitir los escaneados")
    ap.add_argument("--dpi", type=int, default=DPI)
    args = ap.parse_args()

    try:
        cargar_pymupdf()
    except ImportError:
        sys.exit("Falta PyMuPDF.  pip install pymupdf pytesseract pillow")

    if not ORIGEN.is_dir():
        sys.exit("No existe:\n  %s" % ORIGEN)
    DESTINO.mkdir(parents=True, exist_ok=True)

    # --- inventario y deduplicacion por hash ---
    todos = sorted(ORIGEN.glob("*.pdf"))
    validos = [p for p in todos if es_pdf(p)]
    corruptos = len(todos) - len(validos)

    vistos, unicos = set(), []
    for p in validos:
        h = hashlib.md5(p.read_bytes()).hexdigest()
        if h not in vistos:
            vistos.add(h)
            unicos.append(p)

    print("=" * 72)
    print("CORTE SUPREMA — NORMALIZACION A TEXTO")
    print("=" * 72)
    print("Archivos .pdf : %d" % len(todos))
    print("Corruptos     : %d  (se ignoran)" % corruptos)
    print("Unicos validos: %d  (%d duplicados)" % (len(unicos), len(validos) - len(unicos)))

    print("\nClasificando por capa de texto...")
    con_texto, escaneos, paginas = [], [], {}
    for p in unicos:
        tiene, n = clasificar(p)
        paginas[str(p)] = n
        (con_texto if tiene else escaneos).append((p, n))

    pag_ocr = sum(n for _, n in escaneos)
    print("  Con capa de texto : %3d docs" % len(con_texto))
    print("  Escaneados (OCR)  : %3d docs, %d paginas" % (len(escaneos), pag_ocr))

    # --- construir cola: saltar solo lo que ya este BIEN hecho ---
    tareas, saltados, rehacer = [], 0, 0
    pendientes = [(p, False) for p, _ in con_texto]
    if not args.solo_texto:
        pendientes += [(p, True) for p, _ in escaneos]

    for p, con_ocr in pendientes:
        s = DESTINO / (p.stem[:120] + ".txt")
        if s.exists():
            if salida_valida(s):
                saltados += 1
                continue
            rehacer += 1
            s.unlink()                       # texto corrupto de una corrida previa
        tareas.append([str(p), str(s), con_ocr, args.dpi, IDIOMA])

    if saltados:
        print("\nYa procesados y validos: %d (se saltan)" % saltados)
    if rehacer:
        print("Salidas previas invalidas: %d (se rehacen)" % rehacer)
    if not tareas:
        print("\nNada por hacer.")
        return

    n_ocr = sum(1 for t in tareas if t[2])
    tess_cmd = preflight(n_ocr > 0)
    tareas = [tuple(t) + (tess_cmd,) for t in tareas]
    print("\nPor procesar: %d (%d con OCR)" % (len(tareas), n_ocr))
    print("Workers     : %d" % args.workers)
    if n_ocr:
        # solo las paginas realmente encoladas, no todas las escaneadas del corpus
        pag_cola = sum(paginas.get(t[0], 0) for t in tareas if t[2])
        # el paralelismo lo limita el numero de documentos, no el de nucleos:
        # con 8 documentos y 7 workers, el mas largo marca el ritmo
        efectivo = min(args.workers, max(1, n_ocr))
        lo = pag_cola * 1.5 / efectivo / 60.0
        hi = pag_cola * 5.0 / efectivo / 60.0
        print("Paginas a OCR: %d" % pag_cola)
        print("Estimado OCR : %.0f-%.0f min (%d docs en %d procesos)"
              % (lo, hi, n_ocr, efectivo))
        print("\nPuedes cortar con Ctrl-C y retomar; no se pierde lo hecho.")
    print()

    manifiesto, stats = [], Counter()
    t0 = time.time()
    hechas = 0

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futuros = {ex.submit(procesar, t): t[0] for t in tareas}
        for fut in as_completed(futuros):
            nombre, metodo, n, chars, hits, estado, detalle, dur = fut.result()
            stats[estado] += 1
            if estado == "OK":
                stats["m_" + metodo] += 1
            manifiesto.append({"archivo": nombre, "metodo": metodo, "paginas": n,
                               "chars": chars, "marcas_juridicas": hits,
                               "estado": estado, "detalle": detalle,
                               "segundos": round(dur, 1)})
            hechas += 1
            if hechas % 10 == 0 or hechas == len(tareas):
                trans = time.time() - t0
                print("  %3d/%d  ok=%d  sospechosos=%d  errores=%d   [%.0f min]"
                      % (hechas, len(tareas), stats["OK"], stats["SOSPECHOSO"],
                         stats["ERROR"], trans / 60.0))

    man = DESTINO / "manifiesto_ocr.csv"
    modo = "a" if man.exists() else "w"
    with open(man, modo, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "metodo", "paginas", "chars",
                                          "marcas_juridicas", "estado", "detalle", "segundos"])
        if modo == "w":
            w.writeheader()
        w.writerows(manifiesto)

    txts = list(DESTINO.glob("*.txt"))
    print("\n" + "=" * 72)
    print("RESULTADO")
    print("=" * 72)
    print("Procesados OK : %d  (nativo=%d, ocr=%d)"
          % (stats["OK"], stats["m_nativo"], stats["m_ocr"]))
    print("Sospechosos   : %d" % stats["SOSPECHOSO"])
    print("Errores       : %d" % stats["ERROR"])
    print("Total .txt    : %d de %d documentos unicos" % (len(txts), len(unicos)))
    print("Tiempo        : %.1f min" % ((time.time() - t0) / 60.0))
    print("Manifiesto    : %s" % man)

    if stats["SOSPECHOSO"] or stats["ERROR"]:
        print("\nRevisa el manifiesto: hay salidas cortas o fallidas.")
        print("Suele ser OCR de mala calidad; prueba --dpi 400 en esos casos.")
    if len(txts) >= len(unicos):
        print("\nCorpus de Corte Suprema normalizado. Listo para reindexar")
        print("junto con texto_plano de Corte Constitucional.")


if __name__ == "__main__":
    main()
