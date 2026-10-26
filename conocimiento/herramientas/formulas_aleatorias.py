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
import json
import re
import shutil
import subprocess
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

    if not olefile.isOleFile(path):
        return False  # p. ej. PDF nombrado .xls (I-004)
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


def _celdas_xls_com(path: str) -> list[tuple[str, int, int, str]]:
    import pythoncom
    import win32com.client

    carpeta, copia = copia_temporal(path)
    pythoncom.CoInitialize()
    excel = None
    salida = []
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3  # no ejecutar macros al abrir la copia
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
        try:
            if excel is not None:
                excel.Quit()
        finally:
            pythoncom.CoUninitialize()
            shutil.rmtree(carpeta, ignore_errors=True)
    return salida


def celdas_xls(path: str) -> list[tuple[str, int, int, str]]:
    """Un proceso COM por libro evita propagar un fallo de Excel a los siguientes."""
    error = ""
    for _ in range(2):
        # Dejar que el hijo cierre su instancia de Excel y elimine la copia antes de reintentar.
        # Un timeout que solo mate Python impediria ejecutar ese finally y dejaria Excel abierto.
        salida = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--leer-xls", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if salida.returncode == 0:
            return [tuple(c) for c in json.loads(salida.stdout)]
        error = salida.stderr.strip()[-1000:] or f"Excel termino con codigo {salida.returncode}"
    raise RuntimeError(error)


def main() -> None:
    con = conectar()
    con.executescript(ESQUEMA)
    ejecucion = registrar(con, "formulas_aleatorias", {})
    # La tabla publicada permanece completa durante la reconstruccion y ante cualquier error.
    con.executescript(ESQUEMA.replace("CREATE TABLE IF NOT EXISTS celda_aleatoria",
                                    "CREATE TEMP TABLE celda_aleatoria_nueva"))
    filas = [
        (d, h, f, c, fo, v)
        for d, h, f, c, fo, v in con.execute(
            "SELECT c.documento_id, c.hoja, c.fila, c.col, c.formula, c.valor FROM celda c "
            "JOIN documento d ON d.id = c.documento_id WHERE d.ext IN ('xls','xlsx','xlsm') "
            "AND (upper(c.formula) LIKE '%RAND%' OR upper(c.formula) LIKE '%ALEATORIO%')"
        )
        if ALEATORIA.search(fo)
    ]
    con.executemany("INSERT OR IGNORE INTO celda_aleatoria_nueva VALUES (?,?,?,?,?,?)", filas)
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
            "INSERT OR IGNORE INTO celda_aleatoria_nueva SELECT ?,?,?,?,?,"
            "(SELECT valor FROM celda WHERE documento_id=? AND hoja=? AND fila=? AND col=?)",
            [(doc_id, h, f, c, fo, doc_id, h, f, c) for h, f, c, fo in celdas],
        )
        con.commit()
        if sospechosos % 10 == 0:
            print(f"XLS con token revisados: {sospechosos}; errores: {len(errores)}", flush=True)
    por_doc = collections.Counter(d for (d,) in con.execute("SELECT documento_id FROM celda_aleatoria_nueva"))
    resumen = {"celdas": sum(por_doc.values()), "documentos": len(por_doc), "xls_revisados": len(xls),
               "xls_con_token": sospechosos, "errores": errores, "publicada": not errores}
    if not errores:
        with con:
            con.execute("DELETE FROM celda_aleatoria")
            con.execute("INSERT INTO celda_aleatoria SELECT * FROM celda_aleatoria_nueva")
    cerrar_registro(con, ejecucion, resumen)
    con.close()
    print(json.dumps(resumen, ensure_ascii=False))
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--leer-xls":
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(_celdas_xls_com(sys.argv[2]), ensure_ascii=False))
    else:
        main()
