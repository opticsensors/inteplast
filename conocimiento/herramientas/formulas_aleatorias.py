"""Celdas con formulas aleatorias (RAND, RANDBETWEEN, NORM.INV(RAND()...)) en los libros de Exemples.

Su valor no es una medicion: lo genera Excel y cambia en cada recalculo. Hallado el 2026-10-21 al auditar
la biblioteca (ver `incongruencias.md`, I-003). Guarda la tabla derivada `celda_aleatoria` (se recalcula),
con el valor guardado en el fichero (el ultimo que calculo Excel antes de guardar):

  xlsx/xlsm  desde `celda.formula` (ya extraida por openpyxl).
  xls        xlrd no da formulas: se filtran los libros cuyo flujo BIFF contiene el token de RAND
             (ptgFunc 0x003F) o el nombre RANDBETWEEN, y en esos se leen las formulas con Excel por COM
             sobre una copia temporal.

    python conocimiento/herramientas/formulas_aleatorias.py
"""

from __future__ import annotations

import collections
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import cerrar_registro, conectar, original, registrar  # noqa: E402
from lectores import copia_temporal  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS celda_aleatoria (
  documento_id INTEGER, hoja TEXT, fila INTEGER, col INTEGER, formula TEXT, valor TEXT,
  PRIMARY KEY (documento_id, hoja, fila, col)
);
"""
# ALEATORIO(.ENTRE) es el nombre en castellano: aparece tal cual (y da #NAME?) cuando se escribio en un
# Excel en castellano sin el complemento de analisis (3218-00_intern.33 – kopie.xls).
ALEATORIA = re.compile(r"\b(RAND(BETWEEN)?|ALEATORIO(\.ENTRE)?)\s*\(", re.IGNORECASE)
NOMBRES = (b"RANDBETWEEN", b"ALEATORIO")
# ptgFunc (clases referencia, valor y matriz) con el indice de RAND = 63.
TOKEN_RAND = re.compile(rb"[\x21\x41\x61]\x3f\x00")


def xls_sospechoso(path: str) -> bool:
    import olefile

    with olefile.OleFileIO(path) as ole:
        flujo = next((n for n in ("Workbook", "Book") if ole.exists(n)), None)
        if flujo is None:
            return False
        datos = ole.openstream(flujo).read()
    mayusculas = datos.upper()
    if any(n in mayusculas or n.decode().encode("utf-16-le") in mayusculas for n in NOMBRES):
        return True
    # Los tokens solo cuentan dentro de registros FORMULA (0x0006) o SHRFMLA (0x04BC).
    i = 0
    while i + 4 <= len(datos):
        tipo, largo = int.from_bytes(datos[i:i + 2], "little"), int.from_bytes(datos[i + 2:i + 4], "little")
        if tipo in (0x0006, 0x04BC) and TOKEN_RAND.search(datos, i + 4, i + 4 + largo):
            return True
        i += 4 + largo
    return False


def celdas_xls(path: str) -> list[tuple[str, int, int, str]]:
    import pythoncom
    import win32com.client

    carpeta, copia = copia_temporal(path)
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    salida = []
    try:
        libro = excel.Workbooks.Open(copia, 0, True)
        try:
            for hoja in libro.Worksheets:
                rango = hoja.UsedRange
                fila0, col0 = rango.Row, rango.Column
                formulas = rango.Formula
                if not isinstance(formulas, tuple):
                    formulas = ((formulas,),)
                for i, fila in enumerate(formulas):
                    for j, formula in enumerate(fila):
                        if isinstance(formula, str) and formula.startswith("=") and ALEATORIA.search(formula):
                            salida.append((hoja.Name, fila0 + i, col0 + j, formula))
        finally:
            libro.Close(False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
        shutil.rmtree(carpeta, ignore_errors=True)
    return salida


def main() -> None:
    con = conectar()
    con.executescript(ESQUEMA)
    ejecucion = registrar(con, "formulas_aleatorias", {})
    con.execute("DELETE FROM celda_aleatoria")
    filas = [
        (d, h, f, c, fo, v)
        for d, h, f, c, fo, v in con.execute(
            "SELECT c.documento_id, c.hoja, c.fila, c.col, c.formula, c.valor FROM celda c "
            "JOIN documento d ON d.id = c.documento_id WHERE d.ext IN ('xls','xlsx','xlsm') "
            "AND (upper(c.formula) LIKE '%RAND%' OR upper(c.formula) LIKE '%ALEATORIO%')"
        )
        if ALEATORIA.search(fo)
    ]
    con.executemany("INSERT OR IGNORE INTO celda_aleatoria VALUES (?,?,?,?,?,?)", filas)
    # XLS leidos con xlrd: sin formulas en la BD.
    xls = con.execute(
        "SELECT id, ruta FROM documento d WHERE ext='xls' AND estado='extraido' "
        "AND NOT EXISTS (SELECT 1 FROM celda c WHERE c.documento_id=d.id AND c.formula IS NOT NULL)"
    ).fetchall()
    sospechosos, errores = 0, []
    for doc_id, ruta in xls:
        try:
            if not xls_sospechoso(original(ruta)):
                continue
            sospechosos += 1
            celdas = celdas_xls(original(ruta))
        except Exception as error:  # se anota y se sigue
            errores.append(f"{ruta}: {type(error).__name__}: {error}"[:300])
            continue
        # Al abrir, Excel recalcula RAND: el valor que vale es el guardado en el fichero (el de xlrd).
        con.executemany(
            "INSERT OR IGNORE INTO celda_aleatoria SELECT ?,?,?,?,?,"
            "(SELECT valor FROM celda WHERE documento_id=? AND hoja=? AND fila=? AND col=?)",
            [(doc_id, h, f, c, fo, doc_id, h, f, c) for h, f, c, fo in celdas],
        )
        con.commit()
    por_doc = collections.Counter(d for (d,) in con.execute("SELECT documento_id FROM celda_aleatoria"))
    resumen = {"celdas": sum(por_doc.values()), "documentos": len(por_doc), "xls_revisados": len(xls),
               "xls_con_token": sospechosos, "errores": errores}
    cerrar_registro(con, ejecucion, resumen)
    print(resumen)


if __name__ == "__main__":
    main()
