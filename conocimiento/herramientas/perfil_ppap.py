"""Perfil de los informes dimensionales PPAP (plantilla INTEPLAST) de todas las piezas.

Por cada hoja con cabecera 'Nominal' + columnas de cavidad: metadatos de la cabecera, cavidades,
equipos de medida, numero de filas de cota, NOK y valores 0 en celdas de medida (sospechosos).
Lo guarda en la tabla derivada `perfil_ppap` (se recalcula entera en cada ejecucion).

    python conocimiento/herramientas/perfil_ppap.py [--feature "..."]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import conectar  # noqa: E402

ETIQUETAS = {  # la plantilla existe en ingles y en castellano
    "part_name": r"^(part name|nombre pieza)",
    "itp_ref": r"^itp ref",
    "part_no": r"^part n[ºo°]\s*:",
    "part_level": r"^part n[ºo°] level",
    "ppap_ref": r"^ppap ref",
    "drawing_no": r"^(drawing n[ºo°]|n[ºo°] plano)\s*:",
    "drawing_level": r"^drawing n[ºo°] level",
    "report_date": r"^(report date|fecha)",
    "batch": r"^(parts? batch|lote)",
    "responsible": r"^(metr?olo?gy respons|responsable)",
}
CAVIDAD = re.compile(r"^(?:cav(?:ity|idad)?\.?\s*|c)(\d+)\b", re.I)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfil_ppap (
  documento_id INTEGER, hoja TEXT, feature TEXT, pieza TEXT, ruta TEXT,
  fila_cabecera INTEGER, metadatos TEXT, cavidades TEXT, col_nominal INTEGER, col_equipo INTEGER,
  col_nok INTEGER, filas_cota INTEGER, items TEXT, equipos TEXT, nok INTEGER, ceros INTEGER,
  vacias INTEGER, PRIMARY KEY (documento_id, hoja)
);
"""


def perfilar(celdas: list[tuple[int, int, str | None, float | None]]) -> dict | None:
    por_fila: dict[int, dict[int, tuple[str, float | None]]] = defaultdict(dict)
    for fila, col, valor, num in celdas:
        if valor is not None:  # formula sin valor guardado: sigue siendo una medida ausente
            por_fila[fila][col] = (valor, num)
    cabecera = next(
        (f for f in sorted(por_fila)
         if any(v.strip().lower() == "nominal" for v, _ in por_fila[f].values())),
        None,
    )
    if cabecera is None:
        return None
    filas_cab = {**por_fila.get(cabecera - 1, {}), **por_fila[cabecera]}
    cols = {c: v.strip() for c, (v, _) in filas_cab.items()}
    col_nominal = next(c for c, v in cols.items() if v.lower() == "nominal")
    col_equipo = next((c for c, v in cols.items() if re.search(r"equip", v, re.I)), None)
    col_nok = next((c for c, v in cols.items() if v.upper() == "NOK"), None)
    inicio = (col_equipo or col_nominal + 2) + 1
    fin = col_nok or 10_000
    # 'Cav.13', 'C1', 'Cav 1' o un numero solo ('1'..'20') entre el equipo y la columna NOK
    cavidades = {c: v for c, v in cols.items()
                 if inicio <= c < fin and (CAVIDAD.match(v) or re.fullmatch(r"\d{1,3}", v))}
    if not cavidades:
        return None
    metadatos = {}
    for fila in sorted(por_fila):
        if fila >= cabecera - 1:
            break
        items = sorted(por_fila[fila].items())
        for i, (c, (v, _)) in enumerate(items):
            for clave, patron in ETIQUETAS.items():
                if clave not in metadatos and re.search(patron, v.strip(), re.I):
                    siguiente = next((x for cc, (x, _) in items[i + 1:] if x.strip()), "")
                    metadatos[clave] = siguiente
    equipos: Counter = Counter()
    items_vistos = []
    nok = ceros = vacias = filas_cota = 0
    for fila in sorted(f for f in por_fila if f > cabecera):
        datos = por_fila[fila]
        nominal = datos.get(col_nominal, ("", None))[1]
        medidas = [datos.get(c) for c in cavidades]
        if nominal is None and not any(m and m[1] is not None for m in medidas):
            continue
        filas_cota += 1
        if 1 in datos and datos[1][0].strip():
            items_vistos.append(datos[1][0].strip())
        if col_equipo and col_equipo in datos:
            equipos[datos[col_equipo][0].strip()] += 1
        if col_nok and col_nok in datos and datos[col_nok][0].strip().upper() == "X":
            nok += 1
        for m in medidas:
            if m is None or not m[0].strip():
                vacias += 1
            elif m[1] == 0 and nominal not in (0, None):
                ceros += 1
    return {
        "fila_cabecera": cabecera, "metadatos": metadatos,
        "cavidades": list(cavidades.values()), "col_nominal": col_nominal,
        "col_equipo": col_equipo, "col_nok": col_nok, "filas_cota": filas_cota,
        "items": items_vistos, "equipos": dict(equipos.most_common()),
        "nok": nok, "ceros": ceros, "vacias": vacias,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature")
    args = parser.parse_args()
    con = conectar()
    con.executescript(ESQUEMA)
    filtro = "AND d.feature = ?" if args.feature else ""
    hojas = con.execute(
        "SELECT DISTINCT c.documento_id, c.hoja, d.feature, d.pieza, d.ruta FROM celda c "
        f"JOIN documento d ON d.id = c.documento_id WHERE d.ext IN ('xls','xlsx','xlsm','ods') {filtro} "
        "AND lower(c.valor) = 'nominal'",
        [args.feature] if args.feature else [],
    ).fetchall()
    con.execute(f"DELETE FROM perfil_ppap WHERE feature = ?" if args.feature else "DELETE FROM perfil_ppap",
                [args.feature] if args.feature else [])
    n = 0
    for doc_id, hoja, feature, pieza, ruta in hojas:
        celdas = con.execute(
            "SELECT fila, col, valor, numero FROM celda WHERE documento_id=? AND hoja=?", (doc_id, hoja)
        ).fetchall()
        perfil = perfilar(celdas)
        if not perfil:
            continue
        n += 1
        con.execute(
            "INSERT OR REPLACE INTO perfil_ppap VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, hoja, feature, pieza, ruta, perfil["fila_cabecera"],
             json.dumps(perfil["metadatos"], ensure_ascii=False), json.dumps(perfil["cavidades"], ensure_ascii=False),
             perfil["col_nominal"], perfil["col_equipo"], perfil["col_nok"], perfil["filas_cota"],
             json.dumps(perfil["items"], ensure_ascii=False), json.dumps(perfil["equipos"], ensure_ascii=False),
             perfil["nok"], perfil["ceros"], perfil["vacias"]),
        )
    con.commit()
    print(f"Hojas perfiladas: {n}")


if __name__ == "__main__":
    main()
