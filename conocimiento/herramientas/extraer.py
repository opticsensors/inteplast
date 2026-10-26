"""Extrae el contenido de los documentos inventariados y lo guarda en la biblioteca.

Procesa los documentos 'pendiente' (o los de un lector cuya version ha cambiado). Calcula el
SHA-256: un fichero identico a otro ya extraido queda como 'duplicado' sin volver a leerse.
Guarda cada documento en su propia transaccion: se puede interrumpir y reanudar.

    python conocimiento/herramientas/extraer.py --feature "2- Nervios de Soldadura"
    python conocimiento/herramientas/extraer.py --ext pptx --rehacer
    python conocimiento/herramientas/extraer.py --limite 50

Lee los originales, incluidos los que estan solo en la nube (OneDrive los descarga al leerlos).
No escribe en Exemples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ahora, cerrar_registro, conectar, original, registrar  # noqa: E402
from lectores import lector_para  # noqa: E402


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def guardar(con, doc_id: int, resultado, version: str, lector: str, sha: str) -> None:
    con.execute("DELETE FROM elemento WHERE documento_id=?", (doc_id,))
    con.execute("DELETE FROM celda WHERE documento_id=?", (doc_id,))
    con.execute("DELETE FROM estructura WHERE documento_id=?", (doc_id,))
    con.executemany(
        "INSERT INTO elemento(documento_id, tipo, localizador, orden, texto, datos) VALUES (?,?,?,?,?,?)",
        [(doc_id, tipo, loc, i, texto, json.dumps(datos, ensure_ascii=False) if datos else None)
         for i, (tipo, loc, texto, datos) in enumerate(resultado.elementos)],
    )
    con.executemany(
        "INSERT OR REPLACE INTO celda(documento_id, hoja, fila, col, valor, numero, formula) VALUES (?,?,?,?,?,?,?)",
        [(doc_id, *c) for c in resultado.celdas],
    )
    con.executemany(
        "INSERT INTO estructura(documento_id, clave, valor) VALUES (?,?,?)",
        [(doc_id, k, json.dumps(v, ensure_ascii=False, default=str)) for k, v in resultado.estructura.items()],
    )
    con.execute(
        "UPDATE documento SET estado=?, lector=?, mensaje=?, sha256=?, duplicado_de=NULL, "
        "extraido_el=?, version_extraida=? WHERE id=?",
        (resultado.estado, resultado.lector or lector, resultado.mensaje, sha, ahora(), version, doc_id),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--feature")
    parser.add_argument("--ext", help="solo esta extension (sin punto)")
    parser.add_argument("--ruta", help="filtro LIKE sobre la ruta relativa")
    parser.add_argument("--rehacer", action="store_true", help="vuelve a extraer aunque este hecho")
    parser.add_argument("--limite", type=int)
    args = parser.parse_args()

    con = conectar()
    condiciones = ["estado != 'eliminado'"]
    valores: list = []
    if args.feature:
        condiciones.append("feature = ?")
        valores.append(args.feature)
    if args.ext:
        condiciones.append("ext = ?")
        valores.append(args.ext.lower())
    if args.ruta:
        condiciones.append("ruta LIKE ?")
        valores.append(args.ruta)
    consulta = (
        "SELECT id, ruta, nombre, ext, tamano, mtime_ns, estado, version_extraida FROM documento "
        f"WHERE {' AND '.join(condiciones)} ORDER BY ruta"
    )
    documentos = []
    for doc_id, ruta, nombre, ext, tamano, mtime, estado, hecha in con.execute(consulta, valores):
        lector, version_lector, _ = lector_para(nombre, ext, ruta)
        al_dia = hecha == f"{tamano}:{mtime}:{lector}@{version_lector}" and estado not in ("pendiente", "error")
        if args.rehacer or not al_dia:
            documentos.append((doc_id, ruta, nombre, ext, tamano, mtime))
    if args.limite:
        documentos = documentos[: args.limite]
    ejecucion = registrar(con, "extraer", vars(args))
    cuentas: dict[str, int] = {}
    inicio = time.monotonic()
    for n, (doc_id, ruta, nombre, ext, tamano, mtime) in enumerate(documentos, 1):
        lector, version_lector, funcion = lector_para(nombre, ext, ruta)
        version = f"{tamano}:{mtime}:{lector}@{version_lector}"
        path = original(ruta)
        t0 = time.monotonic()
        try:
            sha = sha256(path)
            gemelo = con.execute(
                "SELECT id FROM documento WHERE sha256=? AND id!=? AND estado IN "
                "('extraido','solo_metadatos','sin_texto') ORDER BY id LIMIT 1",
                (sha, doc_id),
            ).fetchone()
            if gemelo and not args.rehacer:
                con.execute("DELETE FROM elemento WHERE documento_id=?", (doc_id,))
                con.execute("DELETE FROM celda WHERE documento_id=?", (doc_id,))
                con.execute("DELETE FROM estructura WHERE documento_id=?", (doc_id,))
                con.execute(
                    "UPDATE documento SET estado='duplicado', duplicado_de=?, sha256=?, lector=?, "
                    "mensaje=NULL, extraido_el=?, version_extraida=? WHERE id=?",
                    (gemelo[0], sha, lector, ahora(), version, doc_id),
                )
                estado = "duplicado"
            else:
                if tamano == 0:
                    from lectores import Resultado

                    resultado = Resultado(estado="sin_texto", mensaje="Fichero vacio (0 bytes).")
                else:
                    resultado = funcion(path)
                guardar(con, doc_id, resultado, version, lector, sha)
                estado = resultado.estado
        except Exception as error:  # se registra y se sigue con el siguiente
            con.rollback()
            detalle = f"{type(error).__name__}: {error}"[:500]
            con.execute(
                "UPDATE documento SET estado='error', lector=?, mensaje=?, extraido_el=? WHERE id=?",
                (lector, detalle, ahora(), doc_id),
            )
            estado = "error"
            traceback.print_exc(limit=1, file=sys.stderr)
        con.commit()
        cuentas[estado] = cuentas.get(estado, 0) + 1
        lento = time.monotonic() - t0
        if lento > 20 or estado == "error" or n % 100 == 0:
            print(f"[{n}/{len(documentos)}] {estado:<14} {lento:6.1f}s  {ruta[:120]}", flush=True)
    resumen = {"documentos": len(documentos), "estados": cuentas,
               "segundos": round(time.monotonic() - inicio)}
    cerrar_registro(con, ejecucion, resumen)
    print(json.dumps(resumen, ensure_ascii=False))
    con.close()


if __name__ == "__main__":
    main()
