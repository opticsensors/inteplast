"""Globos de los planos «ballooned» (.icp + .prf de infra-CONVERT, en el PC de la CMM ZEISS).

Software: infra-CONVERT de ELIAS GmbH (planificacion de ensayos sobre el plano; los globos se llaman
«stamps»; exporta el plan en Excel, CSV, Q-DAS DFD/DFQ o JSON). Formato del .icp deducido el 2026-10-21
(no documentado publicamente), validado a ojo en BSG-296-02 (3288) y corregido el 2026-11-09:

  .icp  binario. Por globo, dos cadenas con su longitud delante (entero de 4 bytes, little endian):
          [n][texto visible del globo]  [n]['INFRA_CONVERT_STAMP_<numero>']
        seguidas de dos puntos en doble precision (x1, y1, z1=0) (x2, y2, z2=0), un entero, el estilo
        ('ELIASEMPTY'), un indice correlativo y el GUID del sello. Las coordenadas estan en unidades del
        dibujo (~mm), origen en el centro de la hoja, Y hacia arriba, no en pixeles del PDF.
  .prf  texto tabulado: columna 1 = id interno, columna 10 = numero visible del globo.

El numero del globo es el texto visible que guarda el propio .icp. En los 2.126 sellos de los 19 .icp
de Exemples coincide con el del nombre del sello, y en los 7 casos en que el .prf dice otro numero el
plano dibuja el del .icp (vistos el 2026-11-09). El .prf se guarda solo para contrastar
(`etiqueta_prf`, fila con id = indice - 1): esa regla falla cuando el .prf se salta filas, y 49 sellos
no tienen fila.

Hasta el 2026-11-09 el numero se tomaba con la expresion 'INFRA_CONVERT_STAMP_(\\d+)': si el primer byte
de la coordenada siguiente era una cifra ASCII, se la comia (1287 por 128) y leia las coordenadas con un
byte de desfase. Quedaban sellos en puntos sin globo y 51 con valores fuera de rango, que se guardaban
sin coordenadas; ademas, un numero mal leido podia pisar otro sello. Ahora el nombre se lee con su
longitud, y un sello repetido o sin las dos cadenas es un error, no se descarta en silencio.

Guarda la tabla derivada `globo` (se recalcula) y compara cada sello con su fila del .prf. Primero lee y
valida todos los ficheros y despues sustituye la tabla en una sola transaccion: si falla cualquier fichero
o la escritura, la tabla anterior queda intacta (antes se borraba al empezar).

    python conocimiento/herramientas/globos_icp.py
"""

from __future__ import annotations

import re
import struct
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import conectar, original  # noqa: E402

VERSION = 2  # 2 (2026-11-09): nombre del sello por su longitud; numero del .icp, .prf solo para contrastar
TABLA = """
CREATE TABLE globo (
  documento_id INTEGER, sello INTEGER, x1 REAL, y1 REAL, x2 REAL, y2 REAL, indice INTEGER,
  guid TEXT, etiqueta TEXT, etiqueta_prf TEXT, PRIMARY KEY (documento_id, sello)
)"""
NOMBRE = b"INFRA_CONVERT_STAMP_"
GUID = re.compile(rb"\x24\x00\x00\x00([0-9A-F-]{36})")
MAX_TEXTO = 40  # longitud maxima que se busca para el texto visible del globo


class FormatoICP(ValueError):
    """El .icp no tiene la estructura esperada: no se adivina, se avisa."""


def cadena_antes(data: bytes, fin: int) -> bytes | None:
    """La cadena con longitud delante que termina justo en `fin`, o None si no la hay."""
    for largo in range(1, MAX_TEXTO + 1):
        inicio = fin - largo
        if inicio - 4 >= 0 and struct.unpack_from("<I", data, inicio - 4)[0] == largo:
            return data[inicio:fin]
    return None


def leer_icp(data: bytes) -> list[dict]:
    globos, vistos = [], set()
    for m in re.finditer(re.escape(NOMBRE), data):
        inicio = m.start()
        if inicio < 4:
            raise FormatoICP(f"sello sin longitud en el byte {inicio}")
        largo = struct.unpack_from("<I", data, inicio - 4)[0]
        nombre = data[inicio:inicio + largo]
        numero = re.fullmatch(re.escape(NOMBRE) + rb"(\d+)", nombre)
        if not numero:
            raise FormatoICP(f"nombre de sello inesperado en el byte {inicio}: {nombre[:40]!r}")
        texto = cadena_antes(data, inicio - 4)
        if texto is None:
            raise FormatoICP(f"sello {numero.group(1).decode()} sin texto visible en el byte {inicio}")
        fin = inicio + largo
        x1, y1, z1, x2, y2, z2 = struct.unpack_from("<6d", data, fin)
        if z1 or z2 or max(abs(v) for v in (x1, y1, x2, y2)) > 1e4:
            raise FormatoICP(f"coordenadas fuera de rango en el sello {numero.group(1).decode()}")
        sello = int(numero.group(1))
        if sello in vistos:
            raise FormatoICP(f"sello {sello} repetido")
        vistos.add(sello)
        resto = data[fin + 48: fin + 160]
        guid = GUID.search(resto)
        indice = None
        marca = resto.find(b"\xff\xff\xff\xff")
        if marca >= 0:
            indice = struct.unpack_from("<i", resto, marca + 4)[0]
        globos.append({"sello": sello, "texto": texto.decode("latin-1"), "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                       "indice": indice, "guid": guid.group(1).decode() if guid else None})
    return globos


def leer_prf(texto: str) -> dict[int, str]:
    etiquetas = {}
    for linea in texto.splitlines():
        campos = linea.split("\t")
        if len(campos) > 9 and campos[0].strip().isdigit():
            etiquetas[int(campos[0])] = campos[9].strip()
    return etiquetas


def filas(doc_id: int, globos: list[dict], prf: dict[int, str]) -> list[tuple]:
    """Filas de la tabla `globo`: número del .icp como etiqueta y el del .prf aparte, para contrastar."""
    return [(doc_id, g["sello"], g["x1"], g["y1"], g["x2"], g["y2"], g["indice"], g["guid"], g["texto"],
             prf.get(g["indice"] - 1) if g["indice"] is not None else None) for g in globos]


def preparar(con) -> list[tuple[str, list[tuple], int]]:
    """Lee y valida todos los .icp con su .prf sin tocar la tabla: (ruta, filas, filas del .prf) por fichero.

    Un fichero que no se puede leer o con formato inesperado lo para todo, con su ruta en el error."""
    icps = con.execute("SELECT id, ruta FROM documento WHERE ext='icp' AND estado!='eliminado' ORDER BY ruta").fetchall()
    leidos = []
    for doc_id, ruta in icps:
        try:
            globos = leer_icp(Path(original(ruta)).read_bytes())
            prf_ruta = str(PurePosixPath(ruta).with_suffix(".prf"))
            prf = con.execute("SELECT ruta FROM documento WHERE ruta=?", (prf_ruta,)).fetchone()
            etiquetas = leer_prf(Path(original(prf[0])).read_text(encoding="utf-8-sig", errors="replace")) if prf else {}
        except Exception as e:
            e.add_note(f"en {ruta}")
            raise
        leidos.append((ruta, filas(doc_id, globos, etiquetas), len(etiquetas)))
    return leidos


def sustituir(con, nuevas: list[tuple]) -> None:
    """Cambia la tabla `globo` entera en una sola transaccion: si algo falla, queda la anterior."""
    con.execute("BEGIN")  # sin el, sqlite3 confirmaria el DROP al momento (no abre transaccion para DDL)
    try:
        con.execute("DROP TABLE IF EXISTS globo")
        con.execute(TABLA)
        con.executemany("INSERT INTO globo VALUES (?,?,?,?,?,?,?,?,?,?)", nuevas)
    except BaseException:
        con.rollback()
        raise
    con.commit()


def regenerar(con) -> list[tuple[str, list[tuple], int]]:
    leidos = preparar(con)
    sustituir(con, [f for _, nuevas, _ in leidos for f in nuevas])
    return leidos


def main() -> None:
    con = conectar()
    total = {"sellos": 0, "igual": 0, "distinto": 0, "sin_fila": 0}
    for ruta, nuevas, n_prf in regenerar(con):
        igual = sum(f[8] == f[9] for f in nuevas)
        sin_fila = sum(f[9] is None for f in nuevas)
        distinto = len(nuevas) - igual - sin_fila
        for k, v in (("sellos", len(nuevas)), ("igual", igual), ("distinto", distinto), ("sin_fila", sin_fila)):
            total[k] += v
        aviso = "; ".join(f"{f[8]} (.prf {f[9]})" for f in nuevas if f[9] is not None and f[8] != f[9])
        print(f"{len(nuevas):>4} sellos | prf {n_prf:>4} filas | igual {igual:>4} | sin fila {sin_fila:>3}"
              f" | {ruta[-80:]}" + (f"\n      distintos: {aviso}" if aviso else ""))
    print(f"Versión {VERSION}: {total['sellos']} sellos; el .prf coincide en {total['igual']}, discrepa en "
          f"{total['distinto']} y no tiene fila para {total['sin_fila']}")


if __name__ == "__main__":
    main()
