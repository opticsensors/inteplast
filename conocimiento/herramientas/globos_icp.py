"""Globos de los planos «ballooned» (.icp + .prf de infra-CONVERT, en el PC de la CMM ZEISS).

Software: infra-CONVERT de ELIAS GmbH (planificacion de ensayos sobre el plano; los globos se llaman
«stamps»; exporta el plan en Excel, CSV, Q-DAS DFD/DFQ o JSON). Formato del .icp deducido el 2026-10-21
(no documentado publicamente) y validado a ojo en BSG-296-02 (3288):

  .icp  binario. Por globo: 'INFRA_CONVERT_STAMP_<n>' seguido de dos puntos en doble precision
        (x1, y1, z1=0) (x2, y2, z2=0), un entero, el estilo ('ELIASEMPTY'), un indice correlativo y
        el GUID del sello. Las coordenadas estan en unidades del dibujo, no en pixeles del PDF.
  .prf  texto tabulado: columna 1 = id interno, columna 10 = numero visible del globo.
  El numero visible del globo es el de la fila del .prf con id = indice - 1 (y coincide con <n> del sello
  en los globos revisados). Coordenadas: unidades del dibujo (~mm), origen en el centro de la hoja, Y hacia
  arriba; en BSG-296-02 x_pt = 2.80*x + 592.5, y_pt = -2.80*y + 419.5 (pagina A3 1190x842 pt): el 99 % de
  los sellos cae a menos de 10 pt de un globo azul del PDF. Algunos sellos traen valores fuera de rango
  (desalineados): se guardan con coordenadas NULL.

Guarda la tabla derivada `globo` (se recalcula) y compara el numero de sellos con las filas del .prf.

    python conocimiento/herramientas/globos_icp.py
"""

from __future__ import annotations

import re
import struct
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import conectar, original  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS globo (
  documento_id INTEGER, sello INTEGER, x1 REAL, y1 REAL, x2 REAL, y2 REAL, indice INTEGER,
  guid TEXT, etiqueta TEXT, PRIMARY KEY (documento_id, sello)
);
"""
SELLO = re.compile(rb"INFRA_CONVERT_STAMP_(\d+)")
GUID = re.compile(rb"\x24\x00\x00\x00([0-9A-F-]{36})")


def leer_icp(data: bytes) -> list[dict]:
    globos = []
    for m in SELLO.finditer(data):
        x1, y1, _z1, x2, y2, _z2 = struct.unpack_from("<6d", data, m.end())
        if max(abs(v) for v in (x1, y1, x2, y2)) > 1e4:  # registro desalineado
            x1 = y1 = x2 = y2 = None
        resto = data[m.end() + 48: m.end() + 160]
        guid = GUID.search(resto)
        indice = None
        marca = resto.find(b"\xff\xff\xff\xff")
        if marca >= 0:
            indice = struct.unpack_from("<i", resto, marca + 4)[0]
        globos.append({"sello": int(m.group(1)), "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                       "indice": indice, "guid": guid.group(1).decode() if guid else None})
    return globos


def leer_prf(texto: str) -> dict[int, str]:
    etiquetas = {}
    for linea in texto.splitlines():
        campos = linea.split("\t")
        if len(campos) > 9 and campos[0].strip().isdigit():
            etiquetas[int(campos[0])] = campos[9].strip()
    return etiquetas


def main() -> None:
    con = conectar()
    con.executescript(ESQUEMA)
    con.execute("DELETE FROM globo")
    icps = con.execute("SELECT id, ruta FROM documento WHERE ext='icp' AND estado!='eliminado' ORDER BY ruta").fetchall()
    for doc_id, ruta in icps:
        globos = leer_icp(Path(original(ruta)).read_bytes())
        prf_ruta = str(PurePosixPath(ruta).with_suffix(".prf"))
        prf = con.execute("SELECT ruta FROM documento WHERE ruta=?", (prf_ruta,)).fetchone()
        etiquetas = leer_prf(Path(original(prf[0])).read_text(encoding="utf-8-sig", errors="replace")) if prf else {}
        for g in globos:
            etiqueta = etiquetas.get(g["indice"] - 1) if g["indice"] is not None else None
            con.execute("INSERT OR REPLACE INTO globo VALUES (?,?,?,?,?,?,?,?,?)",
                        (doc_id, g["sello"], g["x1"], g["y1"], g["x2"], g["y2"], g["indice"], g["guid"], etiqueta))
        con_etiqueta = sum(1 for g in globos if g["indice"] is not None and g["indice"] - 1 in etiquetas)
        print(f"{len(globos):>4} sellos | prf {len(etiquetas):>4} filas | con etiqueta {con_etiqueta:>4} | {ruta[-95:]}")
    con.commit()


if __name__ == "__main__":
    main()
