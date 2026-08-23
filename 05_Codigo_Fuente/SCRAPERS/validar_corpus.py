#!/usr/bin/env python3
"""
validar_corpus.py — Validador de integridad para corpus documentales descargados.

Detecta el modo de falla que corrompió el corpus de Corte Constitucional:
un servidor que responde HTTP 200 con la SPA de su portal en lugar del
documento pedido, de modo que `raise_for_status()` nunca se dispara y el
scraper guarda silenciosamente la misma página de error N veces.

Uso:
    python validar_corpus.py <carpeta> [--ext .rtf] [--mover-invalidos]

Salida:
    - Reporte en consola
    - manifiesto_validacion.csv con una fila por archivo
    - Si se pasa --mover-invalidos, los archivos corruptos van a _INVALIDOS/

Autor: Gerardo Aguilar — UPB, Maestría en Ciencia de Datos
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- firmas

MAGIC = {
    ".rtf": [b"{\\rtf"],
    ".pdf": [b"%PDF"],
    ".doc": [b"\xd0\xcf\x11\xe0"],          # OLE2
    ".docx": [b"PK\x03\x04"],
    ".htm": [b"<!DOC", b"<html", b"<HTML"],
    ".html": [b"<!DOC", b"<html", b"<HTML"],
}

# marcas de "documento no entregado" observadas en los portales judiciales
FIRMAS_ERROR = [
    b"DOCUMENTO NO DISPONIBLE EN MEDIO MAGNETICO",
    b"DOCUMENTO NO DISPONIBLE",
    b"data-beasties-container",              # shell de Angular del portal CC
    b"CORTE CONSTITUCIONAL DE COLOMBIA</title>",
    b"Object reference not set",
    b"Runtime Error",
    b"503 Service",
    b"Access Denied",
]

UMBRAL_MINIMO_BYTES = 3000       # por debajo de esto, sospechoso para una sentencia


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def clasificar(path: Path, ext_esperada: str) -> tuple[str, str]:
    """Devuelve (estado, motivo). estado in {OK, CORRUPTO, SOSPECHOSO}."""
    tam = path.stat().st_size
    if tam == 0:
        return "CORRUPTO", "archivo vacio"

    with open(path, "rb") as f:
        cabecera = f.read(2048)

    # 1) firma de error explicita
    for firma in FIRMAS_ERROR:
        if firma in cabecera:
            return "CORRUPTO", "pagina de error: %s" % firma.decode("utf-8", "replace")[:45]

    # 2) magic bytes contra la extension esperada
    esperados = MAGIC.get(ext_esperada.lower())
    if esperados and not any(cabecera.startswith(m) for m in esperados):
        # es HTML disfrazado?
        if any(cabecera.startswith(m) for m in MAGIC[".htm"]):
            return "CORRUPTO", "es HTML con extension %s" % ext_esperada
        return "CORRUPTO", "cabecera %r no corresponde a %s" % (cabecera[:8], ext_esperada)

    # 3) tamano implausible
    if tam < UMBRAL_MINIMO_BYTES:
        return "SOSPECHOSO", "solo %d bytes" % tam

    return "OK", ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Valida integridad de un corpus descargado.")
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--ext", default=None,
                    help="Extension esperada (ej: .rtf). Por defecto usa la de cada archivo.")
    ap.add_argument("--mover-invalidos", action="store_true",
                    help="Mueve los archivos corruptos a _INVALIDOS/")
    args = ap.parse_args()

    if not args.carpeta.is_dir():
        print("ERROR: no existe la carpeta %s" % args.carpeta, file=sys.stderr)
        return 1

    archivos = sorted(p for p in args.carpeta.rglob("*") if p.is_file()
                      and p.name != "manifiesto_validacion.csv")
    if not archivos:
        print("La carpeta no contiene archivos.")
        return 1

    print("=" * 74)
    print("VALIDACION DE CORPUS: %s" % args.carpeta)
    print("=" * 74)
    print("Archivos encontrados: %d\n" % len(archivos))

    filas = []
    estados = Counter()
    motivos = Counter()
    por_hash: dict[str, list[str]] = defaultdict(list)

    for p in archivos:
        ext = args.ext or p.suffix
        estado, motivo = clasificar(p, ext)
        h = sha(p)
        por_hash[h].append(p.name)
        estados[estado] += 1
        if motivo:
            motivos[motivo] += 1
        filas.append({
            "archivo": p.name,
            "ruta_relativa": str(p.relative_to(args.carpeta)),
            "bytes": p.stat().st_size,
            "sha256": h,
            "estado": estado,
            "motivo": motivo,
        })

    # ---- duplicados exactos: la senal mas fuerte de scraper roto ----
    duplicados = {h: n for h, n in por_hash.items() if len(n) > 1}
    for fila in filas:
        if fila["sha256"] in duplicados:
            fila["duplicado_de"] = len(duplicados[fila["sha256"]])
        else:
            fila["duplicado_de"] = 1

    print("-" * 74)
    print("RESULTADO POR ESTADO")
    print("-" * 74)
    for e in ("OK", "SOSPECHOSO", "CORRUPTO"):
        if estados[e]:
            print("  %-12s %5d  (%.1f%%)" % (e, estados[e], 100.0 * estados[e] / len(archivos)))

    if motivos:
        print("\n" + "-" * 74)
        print("MOTIVOS DE RECHAZO")
        print("-" * 74)
        for m, c in motivos.most_common():
            print("  %5d  %s" % (c, m))

    print("\n" + "-" * 74)
    print("DUPLICADOS EXACTOS (mismo sha256)")
    print("-" * 74)
    if duplicados:
        print("  Grupos de duplicados: %d" % len(duplicados))
        for h, nombres in sorted(duplicados.items(), key=lambda x: -len(x[1]))[:5]:
            print("\n  %s...  %d archivos identicos" % (h[:16], len(nombres)))
            for n in nombres[:3]:
                print("      %s" % n)
            if len(nombres) > 3:
                print("      ... y %d mas" % (len(nombres) - 3))
        peor = max(duplicados.values(), key=len)
        if len(peor) > len(archivos) * 0.5:
            print("\n  *** ALERTA: %d de %d archivos son identicos." % (len(peor), len(archivos)))
            print("      Esto indica que el scraper guardo la misma respuesta")
            print("      repetidamente. El corpus no tiene contenido real.")
    else:
        print("  Ninguno. Todos los archivos son distintos entre si.")

    # ---- manifiesto ----
    manifiesto = args.carpeta / "manifiesto_validacion.csv"
    with open(manifiesto, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "ruta_relativa", "bytes",
                                          "sha256", "estado", "motivo", "duplicado_de"])
        w.writeheader()
        w.writerows(filas)
    print("\nManifiesto escrito en: %s" % manifiesto)

    # ---- cuarentena ----
    if args.mover_invalidos:
        destino = args.carpeta / "_INVALIDOS"
        destino.mkdir(exist_ok=True)
        movidos = 0
        for fila in filas:
            if fila["estado"] == "CORRUPTO":
                origen = args.carpeta / fila["ruta_relativa"]
                if origen.exists():
                    shutil.move(str(origen), str(destino / origen.name))
                    movidos += 1
        print("Archivos movidos a _INVALIDOS/: %d" % movidos)

    print("=" * 74)
    return 0 if estados["CORRUPTO"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
