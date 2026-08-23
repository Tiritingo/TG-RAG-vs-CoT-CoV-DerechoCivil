#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reparar_corpus_cc.py — Repara el corpus de Corte Constitucional en un solo paso.

Sondea patrones de URL, descarga con validacion estricta y verifica el resultado.
No recibe argumentos: edita el bloque CONFIG y ejecuta.

    pip install requests
    python reparar_corpus_cc.py

Es re-ejecutable: salta lo ya descargado, asi que puedes cortarlo y retomarlo.

Autor: Gerardo Aguilar — UPB, Maestría en Ciencia de Datos
"""
import csv, hashlib, random, re, sys, time
from collections import Counter
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Falta requests.  Instala con:  pip install requests")

# ============================== CONFIG ==============================
RAIZ = Path(__file__).resolve().parent.parent.parent
ORIGEN = RAIZ / "01_Corpus_Raw" / "Sentencias" / "Corte_Constitucional" / "archivos"
DESTINO = RAIZ / "01_Corpus_Raw" / "Sentencias" / "Corte_Constitucional" / "archivos_v3"
PAUSA = (1.0, 2.2)          # segundos entre peticiones
MIN_BYTES = 3000            # una sentencia real nunca pesa menos
# ====================================================================

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

# {y4}=ano 4 digitos  {y2}=ano 2 digitos  {id}=C-004 / T-012 / SU-029
# Validados en el sondeo del 2026-08: 1 sirve para casi todo, 3 como respaldo.
PATRONES = [
    "https://www.corteconstitucional.gov.co/sentencias/{y4}/{id}-{y2}.rtf",
    "https://www.corteconstitucional.gov.co/relatoria/{y4}/{id}-{y2}.htm",
]

# Firmas de "el servidor devolvio algo que no es el documento"
FIRMAS_ERROR = [
    b"data-beasties-container",                    # shell de Angular del portal
    b"CORTE CONSTITUCIONAL DE COLOMBIA</title>",
    b"DOCUMENTO NO DISPONIBLE",
    b"Object reference not set",
    b"Runtime Error",
]

# Formatos legitimos por magic bytes. El portal sirve .doc y .docx bajo URL .rtf.
FORMATOS = [
    (b"{\\rtf", ".rtf"),
    (b"%PDF", ".pdf"),
    (b"\xd0\xcf\x11\xe0", ".doc"),      # OLE2 / Word 97-2003
    (b"PK\x03\x04", ".docx"),           # ZIP / Word 2007+
]


def pausa():
    time.sleep(random.uniform(*PAUSA))


def parse_id(nombre):
    """
    'C-004_96.rtf'   -> ('C-004',  '1996', '96')
    'SU.029_24.rtf'  -> ('SU-029', '2024', '24')
    'T-154A_95.rtf'  -> ('T-154A', '1995', '95')   sufijo de letra (aclaraciones)
    """
    m = re.match(r"^(C|T|SU|A)[.\-](\d+[A-Z]?)_(\d{2})$", Path(nombre).stem, re.I)
    if not m:
        return None
    tipo, num, y2 = m.group(1).upper(), m.group(2).upper(), m.group(3)
    return "%s-%s" % (tipo, num), ("19" if int(y2) >= 90 else "20") + y2, y2


def variantes_id(sid):
    """El portal no es consistente con las SU. Devuelve las formas a intentar."""
    if sid.startswith("SU-"):
        num = sid[3:]
        return ["SU-" + num, "SU" + num, "SU." + num]
    return [sid]


def detectar_formato(contenido):
    """Devuelve la extension real segun magic bytes, o None."""
    cab = contenido[:8]
    for magic, ext in FORMATOS:
        if cab.startswith(magic):
            return ext
    inicio = contenido[:512].lstrip().lower()
    if inicio.startswith((b"<!doc", b"<html")):
        return ".htm"
    return None


def validar(contenido):
    """
    (es_valido, extension_real, motivo).
    Esta es la verificacion que faltaba en el scraper original: no basta
    con HTTP 200, hay que mirar los bytes.
    """
    if not contenido:
        return False, None, "respuesta vacia"
    if len(contenido) < MIN_BYTES:
        return False, None, "solo %d bytes" % len(contenido)

    cab = contenido[:2048]
    for firma in FIRMAS_ERROR:
        if firma in cab:
            return False, None, "pagina de error (%s)" % firma.decode("utf-8", "replace")[:30]

    ext = detectar_formato(contenido)
    if ext is None:
        return False, None, "formato no reconocido %r" % cab[:8]

    if ext == ".htm":
        visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                         contenido.decode("utf-8", "replace"))).strip()
        if len(visible) < 1500:
            return False, None, "HTML con solo %d chars visibles" % len(visible)

    return True, ext, ""


def pedir(url, ses):
    """(contenido|None, motivo). Nunca lanza."""
    try:
        r = ses.get(url, headers=HEADERS, timeout=90, allow_redirects=True)
        return r.content, "HTTP %s" % r.status_code
    except Exception as e:
        return None, str(e)[:70]


def rutas_existentes(sid, y2):
    return [DESTINO / ("%s-%s%s" % (sid, y2, e))
            for e in (".rtf", ".doc", ".docx", ".pdf", ".htm")]


# ------------------------------------------------------------------ sondeo

def sondear(objetivos, ses):
    muestra = objetivos[:5]
    print("=" * 74)
    print("PASO 1 — SONDEO DE PATRONES")
    print("=" * 74)
    print("Prueba: %s\n" % ", ".join(Path(n).stem for n in muestra))

    marcador = []
    for i, patron in enumerate(PATRONES):
        print("[%d] %s" % (i, patron))
        ok, hashes = 0, set()
        for nombre in muestra:
            p = parse_id(nombre)
            if not p:
                continue
            sid, y4, y2 = p
            url = patron.format(y4=y4, y2=y2, id=sid)
            contenido, nota = pedir(url, ses)
            if contenido is None:
                print("    --  %-9s %s" % (sid, nota))
            else:
                valido, ext, motivo = validar(contenido)
                hashes.add(hashlib.md5(contenido).hexdigest())
                print("    %s %-9s %8d B  %-6s %s"
                      % ("OK " if valido else "-- ", sid, len(contenido),
                         ext or "?", motivo))
                ok += valido
            pausa()
        idem = "  <-- TODAS IDENTICAS" if len(hashes) == 1 and len(muestra) > 1 else ""
        print("    => %d/%d validos%s\n" % (ok, len(muestra), idem))
        marcador.append((i, ok))

    return [i for i, n in sorted(marcador, key=lambda x: -x[1]) if n > 0] or None


# ---------------------------------------------------------------- descarga

def descargar(objetivos, patrones_ok, ses):
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("PASO 2 — DESCARGA (%d sentencias)" % len(objetivos))
    print("=" * 74)
    for n, i in enumerate(patrones_ok):
        print("%-10s %s" % ("Principal:" if n == 0 else "Respaldo :", PATRONES[i]))
    print("Destino  : %s\n" % DESTINO)

    manifiesto = []
    ok = fallidos = saltados = 0
    formatos = Counter()
    intentos = 0

    for n, nombre in enumerate(objetivos, 1):
        p = parse_id(nombre)
        if not p:
            continue
        sid, y4, y2 = p

        if any(r.exists() and r.stat().st_size > MIN_BYTES for r in rutas_existentes(sid, y2)):
            saltados += 1
            continue

        contenido = ext = None
        motivos, url_ok = [], ""

        # patron x variante de nomenclatura, hasta que algo valide
        for idx in patrones_ok:
            for vid in variantes_id(sid):
                url = PATRONES[idx].format(y4=y4, y2=y2, id=vid)
                cuerpo, nota = pedir(url, ses)
                intentos += 1
                if cuerpo is None:
                    motivos.append("%s: %s" % (vid, nota))
                else:
                    valido, e, motivo = validar(cuerpo)
                    if valido:
                        contenido, ext, url_ok = cuerpo, e, url
                        break
                    motivos.append("%s: %s" % (vid, motivo))
                pausa()
            if contenido is not None:
                break

        if contenido is not None:
            (DESTINO / ("%s-%s%s" % (sid, y2, ext))).write_bytes(contenido)
            ok += 1
            formatos[ext] += 1
            estado = "OK"
        else:
            fallidos += 1
            estado = "NO_DISPONIBLE"

        manifiesto.append({
            "id": sid, "anio": y4, "estado": estado, "formato": ext or "",
            "bytes": len(contenido) if contenido else 0,
            "url": url_ok, "motivo": "" if contenido else " | ".join(motivos[:3]),
            "md5": hashlib.md5(contenido).hexdigest() if contenido else "",
        })

        # cortafuegos por tasa, no por repeticion: aborta solo si nada sirve
        if intentos >= 40 and ok == 0:
            print("\nABORTADO: %d intentos sin una sola descarga valida." % intentos)
            break

        if n % 25 == 0:
            print("  %d/%d — %d ok, %d no disponibles  %s"
                  % (n, len(objetivos), ok, fallidos, dict(formatos)))
        pausa()

    with open(DESTINO / "manifiesto_descarga.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "anio", "estado", "formato",
                                          "bytes", "url", "motivo", "md5"])
        w.writeheader()
        w.writerows(manifiesto)

    print("\n" + "-" * 74)
    print("Descargadas OK : %d   %s" % (ok, dict(formatos)))
    print("No disponibles : %d" % fallidos)
    if saltados:
        print("Ya existian    : %d" % saltados)


# ------------------------------------------------------------- verificacion

def verificar(total):
    print("\n" + "=" * 74)
    print("PASO 3 — VERIFICACION")
    print("=" * 74)
    archivos = sorted(p for p in DESTINO.iterdir()
                      if p.is_file() and p.suffix in (".rtf", ".doc", ".docx", ".pdf", ".htm"))
    if not archivos:
        print("No se descargo ningun archivo.")
        return

    hashes, validos, por_ext = Counter(), 0, Counter()
    for p in archivos:
        b = p.read_bytes()
        hashes[hashlib.sha256(b).hexdigest()] += 1
        por_ext[p.suffix] += 1
        if validar(b)[0]:
            validos += 1

    dups = sum(c for c in hashes.values() if c > 1)
    print("Archivos      : %d de %d objetivos (%.1f%% de cobertura)"
          % (len(archivos), total, 100.0 * len(archivos) / total))
    print("Por formato   : %s" % dict(por_ext))
    print("Bien formados : %d (%.1f%%)" % (validos, 100.0 * validos / len(archivos)))
    print("Hashes unicos : %d" % len(hashes))
    print("Duplicados    : %d" % dups)

    if len(hashes) == 1 and len(archivos) > 1:
        print("\n*** TODOS IDENTICOS: la descarga sigue rota. ***")
        return
    if dups == 0 and validos == len(archivos):
        print("\nCorpus integro: todo archivo es unico y bien formado.")
        if len(archivos) < total:
            print("Faltan %d sentencias. Revisa manifiesto_descarga.csv" % (total - len(archivos)))
        if por_ext.get(".doc", 0) or por_ext.get(".docx", 0) or por_ext.get(".htm", 0):
            print("\nOJO: hay formatos mixtos. Al reindexar necesitas un loader")
            print("por extension, no solo striprtf:")
            print("  .rtf  -> striprtf")
            print("  .doc  -> antiword, o convertir con LibreOffice")
            print("  .docx -> python-docx")
            print("  .htm  -> BeautifulSoup")
    else:
        print("\nRevisa el manifiesto: %d problemas." % max(dups, len(archivos) - validos))


def main():
    if not ORIGEN.is_dir():
        sys.exit("No existe:\n  %s\nEdita RAIZ en el bloque CONFIG." % ORIGEN)

    objetivos = sorted(p.name for p in ORIGEN.glob("*.rtf"))
    if not objetivos:
        sys.exit("No hay .rtf en %s" % ORIGEN)

    print("Sentencias objetivo: %d\n" % len(objetivos))
    ses = requests.Session()

    patrones_ok = sondear(objetivos, ses)
    if not patrones_ok:
        print("=" * 74)
        print("Ningun patron funciono. El portal cambio otra vez.")
        print("Abre una sentencia en el navegador, mira DevTools > Network,")
        print("copia la URL real y agregala a PATRONES.")
        return

    print("=" * 74)
    print("Patrones validados: %s   (principal: %d)" % (patrones_ok, patrones_ok[0]))
    print("=" * 74 + "\n")

    descargar(objetivos, patrones_ok, ses)
    verificar(len(objetivos))


if __name__ == "__main__":
    main()
