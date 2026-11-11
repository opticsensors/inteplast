"""Compara dos bibliotecas, o dos carpetas de auditoría de aceptación, fila a fila y campo a campo. Solo lectura.

Sirve para saber si una tabla derivada está al día con su código: se regenera en una copia aislada de la
biblioteca y se compara con la actual (auditoria-derivadas-2026-11-11.md). No basta con contar filas.

    python comparar_derivadas.py tablas ACTUAL.sqlite NUEVA.sqlite [--tablas medida_dr,perfil_ppap] [--json salida.json]
    python comparar_derivadas.py aceptacion CARPETA_ACTUAL CARPETA_NUEVA [--json salida.json]

Tablas: compara el multiconjunto de filas completas y, por clave, qué campos cambian. `elemento` se compara sin su
`id` autonumérico, que cambia al reextraer aunque el contenido sea el mismo. Aceptación: documento a documento,
sin `huella_lectores`, que identifica la versión de los lectores y no el resultado.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# tabla -> clave para emparejar filas (None: solo multiconjunto)
TABLAS = {
    "documento": ("id",),
    "celda": ("documento_id", "hoja", "fila", "col"),
    "elemento": None,
    "estructura": None,
    "celda_aleatoria": ("documento_id", "hoja", "fila", "col"),
    "perfil_ppap": ("documento_id", "hoja"),
    "perfil_correccion": ("documento_id", "diapositiva"),
    "globo": ("documento_id", "sello"),
    "lectura_dr": ("documento_id", "hoja"),
    "medida_dr": ("documento_id", "hoja", "fila", "col"),
    "cadena_correccion": ("pieza", "documento_id", "diapositiva", "cota"),
    "medida_cmm": ("documento_id", "fila"),
    "medida_cmm_comparativa": ("documento_id", "fila", "columna"),
    "medida_contorno": ("documento_id", "indice", "perfil"),
    "punto_cmm": ("documento_id", "fila"),
}
SIN_COMPARAR = {"elemento": {"id"}, "documento": {"extraido_el", "version_extraida", "inventariado_el"}}
VOLATILES_ACEPTACION = {"huella_lectores"}


def comparar_tabla(c: sqlite3.Connection, tabla: str) -> dict:
    cols = [r[1] for r in c.execute(f"PRAGMA main.table_info({tabla})") if r[1] not in SIN_COMPARAR.get(tabla, set())]
    cols_n = [r[1] for r in c.execute(f"PRAGMA n.table_info({tabla})") if r[1] not in SIN_COMPARAR.get(tabla, set())]
    if cols != cols_n:
        return {"esquema_distinto": [cols, cols_n]}
    lista = ", ".join(f'"{x}"' for x in cols)
    q = (f"SELECT {lista}, count(*) FROM {{a}}.{tabla} GROUP BY {lista} "
         f"EXCEPT SELECT {lista}, count(*) FROM {{b}}.{tabla} GROUP BY {lista}")
    solo_a = c.execute(q.format(a="main", b="n")).fetchall()
    solo_b = c.execute(q.format(a="n", b="main")).fetchall()
    r = {"filas_actual": c.execute(f"SELECT count(*) FROM main.{tabla}").fetchone()[0],
         "filas_nueva": c.execute(f"SELECT count(*) FROM n.{tabla}").fetchone()[0],
         "distintas_actual": len(solo_a), "distintas_nueva": len(solo_b),
         "sin_comparar": sorted(SIN_COMPARAR.get(tabla, set()))}
    clave = TABLAS.get(tabla)
    if clave and (solo_a or solo_b):
        idx = [cols.index(k) for k in clave]
        a = {tuple(x[i] for i in idx): x for x in solo_a}
        b = {tuple(x[i] for i in idx): x for x in solo_b}
        cambios: Counter = Counter()
        ejemplos = []
        for k in a.keys() & b.keys():
            dif = [cols[i] for i in range(len(cols)) if a[k][i] != b[k][i]]
            cambios[",".join(dif)] += 1
            if len(ejemplos) < 8:
                ejemplos.append({"clave": k, **{d: [a[k][cols.index(d)], b[k][cols.index(d)]] for d in dif}})
        r.update({"campos_que_cambian": dict(cambios.most_common(20)), "claves_solo_actual": len(a.keys() - b.keys()),
                  "claves_solo_nueva": len(b.keys() - a.keys()), "ejemplos": ejemplos})
    return r


def tablas(actual: str, nueva: str, solo: list[str] | None) -> dict:
    c = sqlite3.connect(f"file:{Path(actual).resolve().as_posix()}?mode=ro", uri=True)
    try:
        c.execute("ATTACH DATABASE ? AS n", (f"file:{Path(nueva).resolve().as_posix()}?mode=ro",))
        return {t: comparar_tabla(c, t) for t in TABLAS if not solo or t in solo}
    finally:
        c.close()  # en Windows, una conexión abierta bloquea el fichero


def _diferencias(a, b, ruta=""):
    if isinstance(a, dict) and isinstance(b, dict):
        salida = []
        for k in sorted(set(a) | set(b)):
            if k not in VOLATILES_ACEPTACION:
                salida += _diferencias(a.get(k), b.get(k), f"{ruta}.{k}" if ruta else k)
        return salida
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _diferencias(x, y, f"{ruta}[{i}]")]
    return [] if a == b else [ruta]


def _cargar(p: Path) -> dict[object, list[dict]]:
    """Filas por `id`, en lista: un `id` repetido no pisa al anterior."""
    filas: dict[object, list[dict]] = {}
    for x in p.read_text(encoding="utf-8").splitlines():
        if x.strip():
            r = json.loads(x)
            filas.setdefault(r["id"], []).append(r)
    return filas


def _duplicados(carpeta: Path) -> dict[str, int]:
    """`id` que aparecen más de una vez en toda la carpeta, en un fichero o entre ficheros distintos."""
    vistos: Counter = Counter()
    for f in carpeta.glob("*.jsonl"):
        vistos.update({k: len(v) for k, v in _cargar(f).items()})
    return {str(k): n for k, n in sorted(vistos.items(), key=lambda kv: str(kv[0])) if n > 1}


def aceptacion(actual: str, nueva: str) -> dict:
    """Documento a documento. Recorre la unión de los ficheros de las dos carpetas (11/11/2026: antes solo los de
    `actual`, y un fichero añadido en `nueva` no se veía) y cuenta los `id` repetidos (antes un diccionario los ocultaba)."""
    a_dir, b_dir = Path(actual), Path(nueva)
    nombres_a = {f.name for f in a_dir.glob("*.jsonl")}
    nombres_b = {f.name for f in b_dir.glob("*.jsonl")}
    total: Counter = Counter()
    campos: Counter = Counter()
    for nombre in sorted(nombres_a | nombres_b):
        a = _cargar(a_dir / nombre) if nombre in nombres_a else {}
        b = _cargar(b_dir / nombre) if nombre in nombres_b else {}
        total["documentos"] += len(a)
        total["solo_actual"] += len(a.keys() - b.keys())
        total["solo_nueva"] += len(b.keys() - a.keys())
        for k in a.keys() & b.keys():
            if len(a[k]) != len(b[k]):
                total["con_cambios"] += 1
                campos["(número de filas con ese id)"] += 1
                continue
            d = [x for fa, fb in zip(a[k], b[k]) for x in _diferencias(fa, fb)]
            total["con_cambios"] += bool(d)
            campos.update(x.split("[")[0] for x in d)
    return {**total, "ficheros_solo_actual": sorted(nombres_a - nombres_b),
            "ficheros_solo_nueva": sorted(nombres_b - nombres_a),
            "duplicados_actual": _duplicados(a_dir), "duplicados_nueva": _duplicados(b_dir),
            "campos_que_cambian": dict(campos.most_common(20))}


def hay_diferencias(modo: str, r: dict) -> bool:
    if modo == "tablas":
        return any(x.get("distintas_actual") or x.get("distintas_nueva") or "esquema_distinto" in x for x in r.values())
    return bool(r.get("con_cambios") or r.get("solo_actual") or r.get("solo_nueva") or r.get("ficheros_solo_actual")
                or r.get("ficheros_solo_nueva") or r.get("duplicados_actual") or r.get("duplicados_nueva"))


def main(argv: list[str] | None = None) -> int:
    """Devuelve el código de salida: 0 si no hay diferencias, 1 si las hay."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modo", choices=("tablas", "aceptacion"))
    p.add_argument("actual")
    p.add_argument("nueva")
    p.add_argument("--tablas", help="lista separada por comas (por defecto, todas)")
    p.add_argument("--json", help="guardar el resultado completo")
    args = p.parse_args(argv)
    r = (tablas(args.actual, args.nueva, args.tablas.split(",") if args.tablas else None) if args.modo == "tablas"
         else aceptacion(args.actual, args.nueva))
    if args.json:
        Path(args.json).write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if args.modo == "tablas":
        for t, x in r.items():
            print(f"{t:24} {json.dumps({k: v for k, v in x.items() if k != 'ejemplos'}, ensure_ascii=False, default=str)}")
    else:
        print(json.dumps(r, ensure_ascii=False))
    return 1 if hay_diferencias(args.modo, r) else 0


if __name__ == "__main__":
    sys.exit(main())
