#!/usr/bin/env python3
"""
rescrape_cc.py — Re-descarga del corpus de Corte Constitucional con validacion estricta.

CONTEXTO DEL FALLO ORIGINAL
---------------------------
El portal de la Corte Constitucional migro a una SPA de Angular. Cualquier ruta
bajo /relatoria/ que no coincida con el enrutador devuelve HTTP 200 con el
index.html de la aplicacion (8.607 bytes, Content-Type: text/html) en vez de un
404. El scraper anterior hacia:

    r = requests.get(url); r.raise_for_status(); open(path,"wb").write(r.content)

Como la respuesta era 200, raise_for_status() no lanzaba nada y el shell de
Angular quedo guardado 411 veces con extension .rtf. Verificado: los 411
archivos comparten un unico MD5.

QUE HACE ESTE SCRIPT DISTINTO
-----------------------------
1. Toma el indice oficial de datos.gov.co (Socrata) en vez de raspar el buscador.
2. Prueba varios patrones de URL antes de descargar en masa (modo --probe).
3. Valida CADA respuesta: Content-Type, magic bytes, firmas de error, tamano.
4. Detecta en vivo si las respuestas se repiten (hash igual) y aborta.
5. Escribe un manifiesto auditable con hash y estado por archivo.

MODOS
-----
    python rescrape_cc.py --probe
        Prueba los patrones de URL con 5 sentencias y reporta cual sirve.
        EJECUTA ESTO PRIMERO.

    python rescrape_cc.py --indice
        Descarga el indice oficial de datos.gov.co a indice_cc_oficial.csv

    python rescrape_cc.py --descargar --patron 2 --lista objetivos.txt
        Descarga usando el patron elegido.

REQUISITOS
----------
    pip install requests tqdm

Autor: Gerardo Aguilar — UPB, Maestría en Ciencia de Datos
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Falta requests. Instala con: pip install requests tqdm")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it

# ------------------------------------------------------------------ config

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

SOCRATA = "https://www.datos.gov.co/resource/v2k4-2t8s.json"

# Candidatos de URL. El indice se usa con --patron N.
# {y4} = ano 4 digitos, {y2} = ano 2 digitos, {id} = C-004, T-012, SU-029
PATRONES = [
    "https://www.corteconstitucional.gov.co/relatoria/{y4}/{id}-{y2}.rtf",
    "https://www.corteconstitucional.gov.co/sentencias/{y4}/{id}-{y2}.rtf",
    "https://www1.corteconstitucional.gov.co/relatoria/{y4}/{id}-{y2}.rtf",
    "https://www.corteconstitucional.gov.co/relatoria/{y4}/{id}-{y2}.htm",
    "https://www1.corteconstitucional.gov.co/relatoria/{y4}/{id}-{y2}.htm",
    "https://www.corteconstitucional.gov.co/sentencias/{y4}/{id}-{y2}.htm",
]

FIRMAS_ERROR = [
    b"data-beasties-container",
    b"CORTE CONSTITUCIONAL DE COLOMBIA</title>",
    b"DOCUMENTO NO DISPONIBLE",
    b"Object reference not set",
    b"Runtime Error",
]

MIN_BYTES = 3000

# ------------------------------------------------------------------ utils


def pausa(lo=1.2, hi=2.8):
    time.sleep(random.uniform(lo, hi))


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def parse_id(nombre: str) -> tuple[str, str, str] | None:
    """
    'C-004_96.rtf'   -> ('C-004', '1996', '96')
    'SU.029_24.rtf'  -> ('SU-029', '2024', '24')
    'T-012_92.rtf'   -> ('T-012', '1992', '92')
    """
    base = Path(nombre).stem
    m = re.match(r"^(C|T|SU|A)[\.\-](\d+[A-Z]?)_(\d{2})$", base, re.I)
    if not m:
        return None
    tipo, num, y2 = m.group(1).upper(), m.group(2).upper(), m.group(3)
    y4 = ("19" if int(y2) >= 90 else "20") + y2
    return ("%s-%s" % (tipo, num), y4, y2)


def validar(contenido: bytes, content_type: str, quiere_rtf: bool) -> tuple[bool, str]:
    """Devuelve (es_valido, motivo_rechazo)."""
    if not contenido:
        return False, "respuesta vacia"
    if len(contenido) < MIN_BYTES:
        return False, "solo %d bytes" % len(contenido)

    cab = contenido[:2048]
    for firma in FIRMAS_ERROR:
        if firma in cab:
            return False, "firma de error: %s" % firma.decode("utf-8", "replace")[:40]

    if quiere_rtf:
        if not cab.startswith(b"{\\rtf"):
            if cab.startswith((b"<!DOC", b"<html", b"<HTML")):
                return False, "HTML en vez de RTF (SPA fallback)"
            return False, "cabecera %r no es RTF" % cab[:8]
    else:
        # esperamos HTML de contenido real, no el shell de la SPA
        if b"data-beasties-container" in cab:
            return False, "shell de Angular"
        texto = contenido.decode("utf-8", "replace")
        visible = re.sub(r"<[^>]+>", " ", texto)
        visible = re.sub(r"\s+", " ", visible).strip()
        if len(visible) < 1500:
            return False, "solo %d chars de texto visible" % len(visible)

    if "text/html" in content_type.lower() and quiere_rtf:
        return False, "Content-Type text/html para un .rtf"

    return True, ""

# ------------------------------------------------------------------ probe


def modo_probe(objetivos: list[str], ses: requests.Session) -> None:
    muestra = objetivos[:5]
    print("=" * 76)
    print("PRUEBA DE PATRONES DE URL")
    print("=" * 76)
    print("Sentencias de prueba: %s\n" % ", ".join(muestra))

    resultados = []
    for i, patron in enumerate(PATRONES):
        quiere_rtf = patron.endswith(".rtf")
        print("-" * 76)
        print("[patron %d] %s" % (i, patron))
        print("-" * 76)
        ok = 0
        hashes = set()
        for nombre in muestra:
            p = parse_id(nombre)
            if not p:
                print("  %-14s SKIP (nombre no parseable)" % nombre)
                continue
            sid, y4, y2 = p
            url = patron.format(y4=y4, y2=y2, id=sid)
            try:
                r = ses.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
                ct = r.headers.get("Content-Type", "")
                valido, motivo = validar(r.content, ct, quiere_rtf)
                hashes.add(md5(r.content))
                marca = "OK " if valido else "NO "
                print("  %s%-14s HTTP %s  %8d B  %-28s %s"
                      % (marca, sid, r.status_code, len(r.content), ct[:26], motivo))
                if valido:
                    ok += 1
            except Exception as e:
                print("  NO %-14s EXCEPCION: %s" % (sid, str(e)[:55]))
            pausa(0.8, 1.6)

        dup = len(muestra) > 1 and len(hashes) == 1
        print("\n  --> validos: %d/%d%s" % (ok, len(muestra),
                                            "   *** TODAS LAS RESPUESTAS IDENTICAS ***" if dup else ""))
        resultados.append((i, ok, dup))
        print()

    print("=" * 76)
    print("CONCLUSION")
    print("=" * 76)
    buenos = [(i, ok) for i, ok, dup in resultados if ok > 0]
    if buenos:
        mejor = max(buenos, key=lambda x: x[1])
        print("Patron recomendado: %d  (%d/%d validos)" % (mejor[0], mejor[1], len(muestra)))
        print("\nSiguiente paso:")
        print("  python rescrape_cc.py --descargar --patron %d" % mejor[0])
    else:
        print("Ningun patron funciono. El portal probablemente exige")
        print("navegacion con JavaScript. Alternativas:")
        print("  a) Playwright: abrir la ficha y capturar la descarga real")
        print("     (ya tienes playwright en el proyecto)")
        print("  b) Abrir una sentencia a mano en el navegador, ver la peticion")
        print("     real en DevTools > Network, y agregar ese patron a PATRONES")
        print("  c) Usar el dataset de datos.gov.co si publica el texto completo")
    print("=" * 76)

# ------------------------------------------------------------------ indice


def modo_indice(salida: Path, ses: requests.Session) -> None:
    print("Descargando indice oficial de datos.gov.co ...")
    filas, offset, limite = [], 0, 1000
    while True:
        r = ses.get(SOCRATA, headers=HEADERS, timeout=60,
                    params={"$limit": limite, "$offset": offset,
                            "$order": "fecha_sentencia"})
        r.raise_for_status()
        lote = r.json()
        if not lote:
            break
        filas.extend(lote)
        print("  %d registros..." % len(filas))
        offset += limite
        if len(lote) < limite:
            break
        pausa(0.4, 0.9)

    if not filas:
        print("El API no devolvio registros.")
        return

    campos = sorted({k for f in filas for k in f})
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    print("\nTotal: %d sentencias -> %s" % (len(filas), salida))
    tipos = Counter(f.get("sentencia_tipo", "?") for f in filas)
    print("Por tipo: %s" % dict(tipos))

# ------------------------------------------------------------------ descarga


def modo_descargar(objetivos: list[str], patron_idx: int, destino: Path,
                   ses: requests.Session) -> None:
    patron = PATRONES[patron_idx]
    quiere_rtf = patron.endswith(".rtf")
    ext = ".rtf" if quiere_rtf else ".htm"
    destino.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("DESCARGA CON VALIDACION")
    print("=" * 76)
    print("Patron  : %s" % patron)
    print("Destino : %s" % destino)
    print("Objetivo: %d sentencias\n" % len(objetivos))

    manifiesto, vistos = [], Counter()
    ok = fallidos = 0

    for nombre in tqdm(objetivos, desc="Descargando"):
        p = parse_id(nombre)
        if not p:
            manifiesto.append({"objetivo": nombre, "url": "", "estado": "SKIP",
                               "motivo": "nombre no parseable", "bytes": 0, "md5": ""})
            continue
        sid, y4, y2 = p
        url = patron.format(y4=y4, y2=y2, id=sid)
        salida = destino / ("%s-%s%s" % (sid, y2, ext))

        if salida.exists() and salida.stat().st_size > MIN_BYTES:
            manifiesto.append({"objetivo": sid, "url": url, "estado": "YA_EXISTIA",
                               "motivo": "", "bytes": salida.stat().st_size, "md5": ""})
            continue

        try:
            r = ses.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            ct = r.headers.get("Content-Type", "")
            valido, motivo = validar(r.content, ct, quiere_rtf)
            h = md5(r.content)
            vistos[h] += 1

            # cortafuegos: si la misma respuesta se repite, el patron esta roto
            if vistos[h] >= 5 and not valido:
                print("\n\nABORTADO: la misma respuesta se repitio %d veces (md5 %s...)."
                      % (vistos[h], h[:12]))
                print("El patron %d no sirve. Corre --probe de nuevo." % patron_idx)
                break

            if valido:
                salida.write_bytes(r.content)
                ok += 1
                estado = "OK"
            else:
                fallidos += 1
                estado = "RECHAZADO"

            manifiesto.append({"objetivo": sid, "url": url, "estado": estado,
                               "motivo": motivo, "bytes": len(r.content), "md5": h})
        except Exception as e:
            fallidos += 1
            manifiesto.append({"objetivo": sid, "url": url, "estado": "ERROR",
                               "motivo": str(e)[:90], "bytes": 0, "md5": ""})
        pausa()

    ruta_man = destino / "manifiesto_descarga.csv"
    with open(ruta_man, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["objetivo", "url", "estado", "motivo", "bytes", "md5"])
        w.writeheader()
        w.writerows(manifiesto)

    print("\n" + "=" * 76)
    print("Descargados OK : %d" % ok)
    print("Rechazados     : %d" % fallidos)
    print("Manifiesto     : %s" % ruta_man)
    print("\nAhora valida el resultado:")
    print("  python validar_corpus.py %s --ext %s" % (destino, ext))
    print("=" * 76)

# ------------------------------------------------------------------ main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true", help="Prueba patrones de URL")
    g.add_argument("--indice", action="store_true", help="Baja el indice de datos.gov.co")
    g.add_argument("--descargar", action="store_true", help="Descarga las sentencias")
    ap.add_argument("--patron", type=int, default=None, help="Indice del patron a usar")
    ap.add_argument("--origen", type=Path,
                    default=Path("../../01_Corpus_Raw/Sentencias/Corte_Constitucional/archivos"),
                    help="Carpeta con los .rtf corruptos, para extraer la lista objetivo")
    ap.add_argument("--lista", type=Path, default=None,
                    help="Archivo de texto con un ID por linea (alternativa a --origen)")
    ap.add_argument("--destino", type=Path, default=Path("./CC_rtf_v3"))
    args = ap.parse_args()

    ses = requests.Session()

    if args.indice:
        modo_indice(Path("indice_cc_oficial.csv"), ses)
        return 0

    # lista de objetivos
    if args.lista and args.lista.exists():
        objetivos = [l.strip() for l in args.lista.read_text(encoding="utf-8").splitlines() if l.strip()]
    elif args.origen.is_dir():
        objetivos = sorted(p.name for p in args.origen.glob("*.rtf"))
    else:
        print("ERROR: no encuentro la lista de objetivos.", file=sys.stderr)
        print("Pasa --origen <carpeta con los .rtf> o --lista <archivo.txt>", file=sys.stderr)
        return 1

    if not objetivos:
        print("ERROR: lista de objetivos vacia.", file=sys.stderr)
        return 1

    print("Objetivos detectados: %d\n" % len(objetivos))

    if args.probe:
        modo_probe(objetivos, ses)
        return 0

    if args.descargar:
        if args.patron is None:
            print("ERROR: indica --patron N. Corre --probe primero.", file=sys.stderr)
            return 1
        if not 0 <= args.patron < len(PATRONES):
            print("ERROR: --patron debe estar entre 0 y %d" % (len(PATRONES) - 1), file=sys.stderr)
            return 1
        modo_descargar(objetivos, args.patron, args.destino, ses)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
