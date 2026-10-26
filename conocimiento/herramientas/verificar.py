"""Verifica la biblioteca: integridad y una muestra al azar contra los originales.

Cada comprobacion usa un metodo distinto del lector que extrajo el dato (Excel por COM para hojas,
XML crudo para PPTX/DOCX, pdfplumber para PDF, bytes crudos para CSV/TXT/STEP/STL). Guarda el
resultado en la tabla `auditoria` (se acumula: una fila por comprobacion y ejecucion).

Con --hallazgos comprueba en cambio `hallazgos.jsonl`: rutas y SHA-256 de las evidencias, ids frente a
`incongruencias.md` y la `comprobacion` (SQL + resultado esperado) de los hallazgos que la llevan.

    python conocimiento/herramientas/verificar.py [--n 6] [--semilla 7] [--ext xls]
    python conocimiento/herramientas/verificar.py --hallazgos
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import posixpath
import random
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ahora, cerrar_registro, conectar, original, registrar  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS auditoria (
  id INTEGER PRIMARY KEY, ejecutada TEXT, documento_id INTEGER, ext TEXT, comprobacion TEXT,
  esperado TEXT, obtenido TEXT, ok INTEGER
);
"""


# Excel por COM devuelve los errores de celda como enteros (CVErr).
ERRORES_COM = {
    -2146826281: "#DIV/0!", -2146826246: "#N/A", -2146826259: "#NAME?", -2146826288: "#NULL!",
    -2146826252: "#NUM!", -2146826265: "#REF!", -2146826273: "#VALUE!",
}


def mismo(a: str, b: object) -> bool:
    """Igualdad tolerante: numeros con tolerancia relativa, fechas por dia, texto sin espacios."""
    if isinstance(b, bool):
        return str(a).strip().upper() == str(b).upper()
    if isinstance(b, int) and b in ERRORES_COM:
        return str(a).strip().upper() in (ERRORES_COM[b], str(b))
    if isinstance(b, dt.datetime) or hasattr(b, "year"):
        return str(a)[:10] == f"{b.year:04d}-{b.month:02d}-{b.day:02d}"
    try:
        x, y = float(str(a).replace(",", ".")), float(str(b).replace(",", "."))
        return math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return re.sub(r"\s+", " ", str(a)).strip() == re.sub(r"\s+", " ", str(b if b is not None else "")).strip()


def celdas_por_excel(path: str, celdas: list[tuple[str, int, int]]) -> list[object]:
    import pythoncom
    import win32com.client

    carpeta = tempfile.mkdtemp(prefix="inteplast-verificar-")
    copia = os.path.join(carpeta, "copia" + Path(path).suffix)
    shutil.copyfile(path, copia)
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        libro = excel.Workbooks.Open(copia, 0, True)
        try:
            return [libro.Worksheets(h).Cells(f, c).Value for h, f, c in celdas]
        finally:
            libro.Close(False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
        shutil.rmtree(carpeta, ignore_errors=True)


def texto_xml(path: str, patron: str) -> str:
    """Texto del XML: los trozos de un mismo parrafo se unen sin espacio (Word parte palabras en runs)."""
    with zipfile.ZipFile(path) as z:
        partes = [z.read(n).decode("utf-8", "ignore") for n in z.namelist() if re.fullmatch(patron, n)]
    xml = re.sub(r"<w:instrText\b[^>]*>.*?</w:instrText>", "", " ".join(partes), flags=re.S)  # codigos de campo
    xml = re.sub(r"</(?:a|w):p>|<(?:a|w):(?:br|tab)\b[^>]*/>|</w:tc>|</a:tc>", " ", xml)
    texto = re.sub(r"<[^>]+>", "", xml)
    for entidad, caracter in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        texto = texto.replace(entidad, caracter)
    return re.sub(r"\s+", " ", texto)


def muestra_sql(con, rnd: random.Random, sql: str, parametros: tuple, n: int) -> list:
    """Muestreo reproducible y acotado en memoria. La consulta debe tener ORDER BY estable."""
    muestra = []
    for i, fila in enumerate(con.execute(sql, parametros)):
        if i < n:
            muestra.append(fila)
        else:
            j = rnd.randrange(i + 1)
            if j < n:
                muestra[j] = fila
    return muestra


def comprobar_formulas_xml(con, doc_id: int, path: str, rnd: random.Random) -> list:
    """Contrasta clasificacion y ausencia de cache con XML, sin recalcular ni usar el lector."""
    muestra = []
    for condicion in ("formula IS NOT NULL AND valor IS NULL",
                      "formula IS NOT NULL AND valor IS NOT NULL",
                      "formula IS NULL AND valor LIKE '=%'"):
        muestra.extend(muestra_sql(con, rnd,
            "SELECT hoja, fila, col, formula, valor FROM celda WHERE documento_id=? AND "
            + condicion + " ORDER BY hoja, fila, col", (doc_id,), 2))
    if not muestra:
        return []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relacion = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    salida = []
    with zipfile.ZipFile(path) as paquete:
        # Un XLS OLE puede contener un ZIP de dibujos: is_zipfile no demuestra que sea OOXML.
        if not {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}.issubset(paquete.namelist()):
            return []
        relaciones = {r.attrib["Id"]: r.attrib["Target"]
                      for r in ET.fromstring(paquete.read("xl/_rels/workbook.xml.rels"))}
        hojas = {}
        for h in ET.fromstring(paquete.read("xl/workbook.xml")).iter(ns + "sheet"):
            destino = relaciones[h.attrib[relacion]]
            hojas[h.attrib["name"]] = (destino.lstrip("/") if destino.startswith("/")
                                      else posixpath.normpath(posixpath.join("xl", destino)))
        for nombre in sorted({h for h, *_ in muestra}):
            celdas = {c.attrib["r"]: c for c in ET.fromstring(paquete.read(hojas[nombre])).iter(ns + "c")}
            for hoja, fila, col, formula, valor in muestra:
                if hoja != nombre:
                    continue
                letras, indice = "", col
                while indice:
                    indice, resto = divmod(indice - 1, 26)
                    letras = chr(65 + resto) + letras
                celda = celdas.get(f"{letras}{fila}")
                f = celda.find(ns + "f") if celda is not None else None
                v = celda.find(ns + "v") if celda is not None else None
                es_formula = f is not None
                ok = celda is not None and es_formula == (formula is not None)
                if formula is not None:
                    ok = ok and ((valor is None) == (v is None or not v.text))
                if f is not None and f.text:
                    ok = ok and formula == "=" + f.text
                esperado = {"formula": formula, "sin_valor": valor is None}
                obtenido = {"formula_xml": es_formula, "texto": f.text if f is not None else None,
                            "cache": v.text if v is not None else None}
                salida.append((f"formula/cache XML {hoja}!{letras}{fila}",
                               json.dumps(esperado), json.dumps(obtenido), bool(ok)))
    return salida


def comprobar(con: sqlite3.Connection, doc: tuple, rnd: random.Random) -> list[tuple[str, str, str, bool]]:
    doc_id, ruta, ext = doc
    path = original(ruta)
    salida = []
    # El formato detectado tiene prioridad sobre la extension (I-004).
    formato = con.execute("SELECT lector FROM documento WHERE id=?", (doc_id,)).fetchone()
    if formato and formato[0] == "pdf":
        ext = "pdf"
    if ext in ("xls", "xlsx", "xlsm"):
        # Las celdas con RAND() cambian al abrir el libro: no se pueden comparar.
        # Las formulas sin cache se verifican en XML, no contra Excel que las recalcula.
        muestra = muestra_sql(con, rnd,
            "SELECT hoja, fila, col, valor FROM celda c WHERE documento_id=? AND valor IS NOT NULL AND NOT EXISTS (SELECT 1 FROM "
            "celda_aleatoria a WHERE a.documento_id=c.documento_id AND a.hoja=c.hoja AND a.fila=c.fila "
            "AND a.col=c.col) ORDER BY hoja, fila, col", (doc_id,), 8)
        if muestra:
            obtenidos = celdas_por_excel(path, [(h, f, c) for h, f, c, _ in muestra])
            for (h, f, c, v), o in zip(muestra, obtenidos):
                salida.append((f"celda {h}!R{f}C{c}", v, str(o), mismo(v, o)))
        if zipfile.is_zipfile(path):
            salida.extend(comprobar_formulas_xml(con, doc_id, path, rnd))
    elif ext == "csv":
        lineas = Path(path).read_bytes().decode("cp1252", "replace").splitlines()
        # El separador lo eligio el lector (la coma tambien es el decimal); aqui se corta sin modulo csv.
        sep = json.loads(con.execute(
            "SELECT valor FROM estructura WHERE documento_id=? AND clave='delimitador'", (doc_id,)).fetchone()[0])
        for f, c, v in muestra_sql(con, rnd,
            "SELECT fila, col, valor FROM celda WHERE documento_id=? ORDER BY fila, col", (doc_id,), 8):
            campos = [x.strip('"') for x in lineas[f - 1].split(sep)] if f <= len(lineas) else []
            salida.append((f"linea {f} campo {c}", v, campos[c - 1] if c <= len(campos) else "",
                           c <= len(campos) and v.strip() == campos[c - 1].strip()))
    elif ext in ("pptx", "docx"):
        patron = r"ppt/slides/slide\d+\.xml" if ext == "pptx" else r"word/document\.xml"
        crudo = texto_xml(path, patron)
        if ext == "pptx":
            with zipfile.ZipFile(path) as z:
                n = sum(1 for x in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", x))
            guardadas = con.execute("SELECT count(*) FROM elemento WHERE documento_id=? AND tipo='diapositiva'", (doc_id,)).fetchone()[0]
            salida.append(("numero de diapositivas", str(guardadas), str(n), guardadas == n))
        for loc, texto in muestra_sql(con, rnd,
            "SELECT localizador, texto FROM elemento WHERE documento_id=? AND length(texto)>20 ORDER BY orden, id", (doc_id,), 3):
            trozo = re.sub(r"\s+", " ", rnd.choice([l for l in texto.splitlines() if len(l.strip()) > 8] or [texto])).strip()[:40]
            # Las celdas de tabla se guardaron separadas por " | ": cada trozo tiene que estar.
            partes = [p for p in re.split(r"\s*\|\s*", trozo) if p]
            salida.append((f"texto presente en el XML: {loc}", trozo, "", all(p in crudo for p in partes)))
    elif ext == "pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            paginas = len(pdf.pages)
            guardadas = con.execute("SELECT count(*) FROM elemento WHERE documento_id=? AND tipo='pagina'", (doc_id,)).fetchone()[0]
            salida.append(("numero de paginas", str(guardadas), str(paginas), guardadas == paginas))
            candidatas = muestra_sql(con, rnd,
                "SELECT localizador, texto FROM elemento WHERE documento_id=? AND length(texto)>30 ORDER BY orden, id", (doc_id,), 1)
            fila = candidatas[0] if candidatas else None
            if fila:
                n = int(fila[0].split()[-1])
                palabras = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", fila[1])]
                if palabras:
                    w = rnd.choice(palabras)
                    texto = pdf.pages[n - 1].extract_text() or ""
                    salida.append((f"palabra de la pagina {n}", w, "", w in texto))
    elif ext in ("stp", "step"):
        datos = Path(path).read_bytes()
        caras = len(re.findall(rb"=\s*ADVANCED_FACE\s*\(", datos))
        guardado = json.loads(con.execute(
            "SELECT valor FROM estructura WHERE documento_id=? AND clave='entidades'", (doc_id,)).fetchone()[0]).get("ADVANCED_FACE", 0)
        salida.append(("caras ADVANCED_FACE", str(guardado), str(caras), guardado == caras))
    elif ext == "stl":
        with open(path, "rb") as f:
            f.seek(80)
            n = int.from_bytes(f.read(4), "little")
        guardado = json.loads(con.execute(
            "SELECT valor FROM estructura WHERE documento_id=? AND clave='triangulos'", (doc_id,)).fetchone()[0])
        salida.append(("triangulos", str(guardado), str(n), guardado == n))
    elif ext == "txt":
        crudo = Path(path).read_bytes().decode("utf-8", "replace") + Path(path).read_bytes().decode("cp1252", "replace")
        for loc, texto in muestra_sql(con, rnd,
            "SELECT localizador, texto FROM elemento WHERE documento_id=? AND tipo='lineas' ORDER BY orden, id", (doc_id,), 2):
            linea = rnd.choice([l for l in texto.splitlines() if l.strip()] or [""]).strip()
            salida.append((f"linea presente: {loc}", linea[:60], "", linea in crudo))
        est = con.execute("SELECT valor FROM estructura WHERE documento_id=? AND clave='puntos'", (doc_id,)).fetchone()
        if est:
            n = sum(1 for l in crudo[: len(crudo) // 2].splitlines() if l.strip())
            salida.append(("puntos de la nube", est[0], str(n), int(est[0]) == n))
    return salida


def comprobar_hallazgos(con: sqlite3.Connection) -> list[str]:
    """hallazgos.jsonl: JSON valido, ids unicos, evidencias que existen en la biblioteca y con su SHA-256,
    y los mismos ids I-xxx que en incongruencias.md."""
    carpeta = Path(__file__).resolve().parent.parent
    problemas, ids = [], []
    for n, linea in enumerate((carpeta / "hallazgos.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            registro = json.loads(linea)
        except json.JSONDecodeError as error:
            problemas.append(f"linea {n}: JSON invalido ({error})")
            continue
        ids.append(registro["id"])
        # Cifra clave del hallazgo recalculada desde la biblioteca (campo opcional).
        if "comprobacion" in registro:
            obtenido = list(con.execute(registro["comprobacion"]["sql"]).fetchone() or [])
            if obtenido != registro["comprobacion"]["esperado"]:
                problemas.append(f"{registro['id']}: la comprobacion da {obtenido}, se esperaba {registro['comprobacion']['esperado']}")
        for evidencia in registro.get("evidencia", []):
            ruta = evidencia.get("ruta", "")
            if ruta.startswith("http"):
                continue
            fila = con.execute("SELECT sha256 FROM documento WHERE ruta=?", (ruta.rstrip("/"),)).fetchone()
            if fila is None:
                prefijo = ruta.rstrip("/") + "/"
                if not con.execute("SELECT 1 FROM documento WHERE substr(ruta, 1, ?) = ?", (len(prefijo), prefijo)).fetchone():
                    problemas.append(f"{registro['id']}: la ruta no esta en la biblioteca: {ruta}")
            elif evidencia.get("sha256") and not fila[0].startswith(evidencia["sha256"]):
                problemas.append(f"{registro['id']}: SHA-256 distinto en {ruta}")
    problemas += [f"id repetido: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    en_md = set(re.findall(r"^\| (I-\d{3}) \|", (carpeta / "incongruencias.md").read_text(encoding="utf-8"), re.M))
    en_jsonl = {i for i in ids if i.startswith("I-")}
    problemas += [f"{i} en incongruencias.md y no en hallazgos.jsonl" for i in sorted(en_md - en_jsonl)]
    problemas += [f"{i} en hallazgos.jsonl y no en incongruencias.md" for i in sorted(en_jsonl - en_md)]
    return problemas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=6, help="documentos por extension")
    parser.add_argument("--semilla", type=int, default=7)
    parser.add_argument("--ext")
    parser.add_argument("--hallazgos", action="store_true", help="solo comprobar hallazgos.jsonl")
    args = parser.parse_args()
    rnd = random.Random(args.semilla)
    con = conectar()
    if args.hallazgos:
        problemas = comprobar_hallazgos(con)
        print("\n".join(problemas) or "hallazgos.jsonl: sin problemas")
        con.close()
        if problemas:
            raise SystemExit(1)
        return
    con.executescript(ESQUEMA)
    extensiones = [args.ext] if args.ext else ["xls", "xlsx", "xlsm", "csv", "pptx", "docx", "pdf", "stp", "step", "stl", "txt"]
    marca = ahora()
    ejecucion = registrar(con, "verificar", {**vars(args), "auditoria_ejecutada": marca})
    resumen = {}
    cobertura = {}
    for ext in extensiones:
        ids = [r for r in con.execute(
            "SELECT id, ruta, ext FROM documento WHERE ext=? AND estado='extraido' ORDER BY id", (ext,)).fetchall()]
        if ext in ("stp", "step", "stl"):
            ids = [r for r in ids if con.execute("SELECT tamano FROM documento WHERE id=?", (r[0],)).fetchone()[0] < 120e6]
        for doc in rnd.sample(ids, min(args.n, len(ids))):
            try:
                resultados = comprobar(con, doc, rnd)
            except Exception as error:  # se registra como fallo de la verificacion
                resultados = [("error al verificar", "", f"{type(error).__name__}: {error}"[:200], False)]
            seleccionados, con_muestra = cobertura.get(ext, (0, 0))
            cobertura[ext] = (seleccionados + 1, con_muestra + int(bool(resultados)))
            for nombre, esperado, obtenido, ok in resultados:
                con.execute("INSERT INTO auditoria(ejecutada, documento_id, ext, comprobacion, esperado, obtenido, ok) VALUES (?,?,?,?,?,?,?)",
                            (marca, doc[0], ext, nombre, str(esperado)[:300], str(obtenido)[:300], int(bool(ok))))
                total, buenos = resumen.get(ext, (0, 0))
                resumen[ext] = (total + 1, buenos + int(bool(ok)))
            con.commit()
    for ext, (total, buenos) in resumen.items():
        print(f"{ext:<5} {buenos}/{total} comprobaciones correctas")
    for ext, (seleccionados, con_muestra) in cobertura.items():
        print(f"{ext:<5} {seleccionados} documentos seleccionados; {con_muestra} con comprobaciones; "
              f"{seleccionados - con_muestra} sin muestra")
    for fila in con.execute("SELECT documento_id, ext, comprobacion, esperado, obtenido FROM auditoria WHERE ejecutada=? AND ok=0", (marca,)):
        print("FALLO", *fila, sep=" | ")
    cerrar_registro(con, ejecucion, {"comprobaciones": resumen, "documentos_seleccionados_y_con_muestra": cobertura})
    con.close()
    if any(total != buenos for total, buenos in resumen.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
