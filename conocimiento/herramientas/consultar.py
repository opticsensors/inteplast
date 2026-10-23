"""Consultas sobre la biblioteca de Exemples (solo lectura).

    python conocimiento/herramientas/consultar.py estado
    python conocimiento/herramientas/consultar.py arbol "2- Nervios de Soldadura" [--pieza 3205]
    python conocimiento/herramientas/consultar.py buscar "tool correction" [--feature ...] [--n 30]
    python conocimiento/herramientas/consultar.py ver <id | ruta> [--desde 0] [--n 20]
    python conocimiento/herramientas/consultar.py celdas <id> [--hoja DR] [--filas 1-40]
    python conocimiento/herramientas/consultar.py sql "SELECT ..."

`buscar` usa FTS5 (sin acentos; admite "frase exacta", prefijo*, AND/OR/NOT).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import BD  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def abrir() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{BD.as_posix()}?mode=ro", uri=True, timeout=30)


def documento(con: sqlite3.Connection, ref: str) -> tuple:
    fila = (con.execute("SELECT * FROM documento WHERE id=?", (int(ref),)).fetchone()
            if ref.isdigit() else
            con.execute("SELECT * FROM documento WHERE ruta=? OR ruta LIKE ?", (ref, f"%{ref}")).fetchone())
    if not fila:
        sys.exit(f"No encontrado: {ref}")
    return fila


def estructura_corta(con: sqlite3.Connection, doc_id: int, ancho: int = 160) -> str:
    partes = []
    for clave, valor in con.execute("SELECT clave, valor FROM estructura WHERE documento_id=?", (doc_id,)):
        if clave in ("primeras_lineas", "sistema_origen", "propiedades", "metadatos", "exif"):
            continue
        datos = json.loads(valor)
        if clave == "hojas":
            datos = [h["nombre"] for h in datos]
        partes.append(f"{clave}={json.dumps(datos, ensure_ascii=False)}")
    texto = " ".join(partes)
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def cmd_estado(con, args) -> None:
    for fila in con.execute(
        "SELECT feature, estado, count(*) FROM documento GROUP BY 1,2 ORDER BY 1,2"
    ):
        print(*fila, sep="\t")
    for fila in con.execute("SELECT id, ruta, mensaje FROM documento WHERE estado='error' LIMIT 50"):
        print("ERROR", *fila, sep="\t")


def cmd_arbol(con, args) -> None:
    sql = ("SELECT id, ruta, ext, tamano, estado, en_nube FROM documento WHERE feature=? "
           + ("AND (pieza=? OR codigo=?) " if args.pieza else "") + "ORDER BY ruta")
    parametros = [args.feature] + ([args.pieza, args.pieza] if args.pieza else [])
    for doc_id, ruta, ext, tamano, estado, nube in con.execute(sql, parametros):
        relativa = ruta.split("/", 1)[1] if "/" in ruta else ruta
        extra = estructura_corta(con, doc_id) if args.detalle else ""
        print(f"{doc_id:>5} {tamano/1e6:8.2f}MB {estado[:9]:<9}{' N' if nube else '  '} {relativa}"
              + (f"\n{'':>27}{extra}" if extra else ""))


def cmd_buscar(con, args) -> None:
    sql = ("SELECT d.id, d.ruta, e.localizador, snippet(elemento_fts, 0, '«', '»', '…', 24) "
           "FROM elemento_fts JOIN elemento e ON e.id = elemento_fts.rowid "
           "JOIN documento d ON d.id = e.documento_id WHERE elemento_fts MATCH ? ")
    parametros: list = [args.consulta]
    if args.feature:
        sql += "AND d.feature = ? "
        parametros.append(args.feature)
    sql += "ORDER BY rank LIMIT ?"
    parametros.append(args.n)
    for doc_id, ruta, loc, trozo in con.execute(sql, parametros):
        print(f"[{doc_id}] {ruta} · {loc}\n    {trozo.replace(chr(10), ' / ')}")


def cmd_ver(con, args) -> None:
    fila = documento(con, args.ref)
    print(f"[{fila[0]}] {fila[1]}  estado={fila[15]} lector={fila[16]} mensaje={fila[17]}")
    for clave, valor in con.execute("SELECT clave, valor FROM estructura WHERE documento_id=?", (fila[0],)):
        print(f"  {clave}: {valor[:600]}")
    for loc, texto, datos in con.execute(
        "SELECT localizador, texto, datos FROM elemento WHERE documento_id=? ORDER BY orden LIMIT ? OFFSET ?",
        (fila[0], args.n, args.desde),
    ):
        print(f"--- {loc}" + (f"  {datos[:300]}" if datos and args.datos else ""))
        print((texto or "")[: args.max])


def cmd_celdas(con, args) -> None:
    sql = "SELECT hoja, fila, col, valor, formula FROM celda WHERE documento_id=? "
    parametros: list = [int(args.id)]
    if args.hoja:
        sql += "AND hoja=? "
        parametros.append(args.hoja)
    if args.filas:
        a, b = (int(x) for x in args.filas.split("-"))
        sql += "AND fila BETWEEN ? AND ? "
        parametros += [a, b]
    actual = None
    for hoja, f, c, valor, formula in con.execute(sql + "ORDER BY hoja, fila, col", parametros):
        if (hoja, f) != actual:
            print(f"\n{hoja}!{f}:", end="")
            actual = (hoja, f)
        print(f"  [{c}] {valor}" + (f" {{{formula}}}" if formula else ""), end="")
    print()


def cmd_sql(con, args) -> None:
    cursor = con.execute(args.consulta)
    print("\t".join(d[0] for d in cursor.description))
    for fila in cursor:
        print("\t".join("" if v is None else str(v) for v in fila))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("estado")
    p = sub.add_parser("arbol")
    p.add_argument("feature")
    p.add_argument("--pieza")
    p.add_argument("--detalle", action="store_true")
    p = sub.add_parser("buscar")
    p.add_argument("consulta")
    p.add_argument("--feature")
    p.add_argument("--n", type=int, default=30)
    p = sub.add_parser("ver")
    p.add_argument("ref")
    p.add_argument("--desde", type=int, default=0)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--max", type=int, default=3000)
    p.add_argument("--datos", action="store_true")
    p = sub.add_parser("celdas")
    p.add_argument("id")
    p.add_argument("--hoja")
    p.add_argument("--filas")
    p = sub.add_parser("sql")
    p.add_argument("consulta")
    args = parser.parse_args()
    con = abrir()
    {"estado": cmd_estado, "arbol": cmd_arbol, "buscar": cmd_buscar, "ver": cmd_ver,
     "celdas": cmd_celdas, "sql": cmd_sql}[args.cmd](con, args)


if __name__ == "__main__":
    main()
