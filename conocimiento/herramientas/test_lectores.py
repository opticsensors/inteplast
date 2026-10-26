"""Regresiones de I-003/I-004 y del muestreo; fixtures temporales, sin originales ni BD real.

    conocimiento/.venv/Scripts/python.exe -B -m unittest discover -s conocimiento/herramientas -p "test_*.py"
"""

import random
import json
import sqlite3
import subprocess
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import fitz
import openpyxl

from extraer import guardar
import formulas_aleatorias
from formulas_aleatorias import ALEATORIA, xls_sospechoso
from lectores import lector_para
from lector_dr import leer_hoja
from perfil_ppap import perfilar
from verificar import comprobar, comprobar_formulas_xml, muestra_sql


class LectoresTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="inteplast-test-")
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)

    def libro(self, extension=".xlsx"):
        """OOXML con cache, sin cache, formulas compartidas, texto literal y un error."""
        path = self.raiz / ("formulas" + extension)
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "INTRO"
        for fila, valor in enumerate(("=RAND()", "=RAND()", "=RAND()", "=RAND()", "=RAND()", "=#REF!+1", 42), 1):
            hoja.cell(fila, 1, valor)
        hoja["A4"].data_type = "s"
        libro.save(path)
        libro.close()
        with zipfile.ZipFile(path) as paquete:
            contenido = {n: paquete.read(n) for n in paquete.namelist()}
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        xml = ET.fromstring(contenido["xl/worksheets/sheet1.xml"])
        celdas = {c.attrib["r"]: c for c in xml.iter(ns + "c")}
        celdas["A1"].find(ns + "v").text = "0.125"
        # A2/A3 son una formula compartida sin cache, A5 una formula normal sin cache.
        celdas["A2"].find(ns + "f").attrib.update(t="shared", si="0", ref="A2:A3")
        celdas["A3"].find(ns + "f").attrib.update(t="shared", si="0")
        celdas["A3"].find(ns + "f").text = None
        celdas["A6"].attrib["t"] = "e"
        celdas["A6"].find(ns + "v").text = "#REF!"
        contenido["xl/worksheets/sheet1.xml"] = ET.tostring(xml)
        with zipfile.ZipFile(path, "w") as paquete:
            for nombre, data in contenido.items():
                paquete.writestr(nombre, data)
        return path

    def test_formulas_cache_textos_y_compartidas(self):
        path = self.libro()
        _, version, leer = lector_para(path.name, "xlsx", path.name)
        r = leer(str(path))
        celdas = {fila: (valor, numero, formula) for _, fila, _, valor, numero, formula in r.celdas}
        self.assertEqual(version, 2)
        self.assertEqual(celdas[1], ("0.125", 0.125, "=RAND()"))
        for fila in (2, 3, 5):
            self.assertEqual(celdas[fila], (None, None, "=RAND()"))
        self.assertEqual(celdas[4], ("=RAND()", None, None))
        self.assertEqual(celdas[6], ("#REF!", None, "=#REF!+1"))
        self.assertEqual(celdas[7], ("42", 42.0, None))
        self.assertEqual(r.estructura["formulas"], 5)
        self.assertEqual(sum(bool(f and ALEATORIA.search(f)) for _, _, f in celdas.values()), 4)
        self.assertEqual(r.estructura["hojas"][0]["celdas"], 7)

    def test_ooxml_con_extension_xls(self):
        path = self.libro(".xls")
        _, _, leer = lector_para(path.name, "xls", path.name)
        r = leer(str(path))
        self.assertEqual(len(r.celdas), 7)
        self.assertEqual(r.estructura["formulas"], 5)

    def test_auditoria_xml_detecta_texto_mal_marcado(self):
        path = self.libro()
        _, _, leer = lector_para(path.name, "xlsx", path.name)
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO documento(id,ruta,nombre,ext,tamano,mtime_ns,inventariado_el) VALUES (1,?,?,?,0,0,'test')",
                    (path.name, path.name, "xlsx"))
        guardar(con, 1, leer(str(path)), "0:0:xlsx@2", "xlsx", "test")
        controles = comprobar_formulas_xml(con, 1, str(path), random.Random(7))
        self.assertEqual(len(controles), 5)
        self.assertTrue(all(ok for _, _, _, ok in controles))
        for fila, cambio in ((4, "formula='=RAND()', valor=NULL"),
                             (5, "valor='0', numero=0"), (1, "valor=NULL, numero=NULL")):
            with self.subTest(fila=fila):
                guardar(con, 1, leer(str(path)), "0:0:xlsx@2", "xlsx", "test")
                con.execute(f"UPDATE celda SET {cambio} WHERE fila=?", (fila,))
                con.execute("DELETE FROM celda WHERE fila != ?", (fila,))
                controles = comprobar_formulas_xml(con, 1, str(path), random.Random(7))
                self.assertFalse(controles[0][3])

    def test_pdf_xls_se_regenera_y_verifica_como_pdf(self):
        path = self.raiz / "informe.xls"
        with fitz.open() as pdf:
            pdf.new_page().insert_text((72, 72), "Primera pagina")
            pdf.new_page().insert_text((72, 72), "Segunda pagina")
            pdf.save(path)
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO documento(id,ruta,nombre,ext,tamano,mtime_ns,inventariado_el) VALUES (1,?,?,?,0,0,'test')",
                    (path.name, path.name, "xls"))
        lector, version, leer = lector_para(path.name, "xls", path.name)
        # Dos extracciones completas no restauran las antiguas celdas falsas.
        with patch("lectores.xls_por_excel", side_effect=AssertionError("No abrir PDF con Excel")):
            for _ in range(2):
                guardar(con, 1, leer(str(path)), f"0:0:{lector}@{version}", lector, "test")
        self.assertEqual(con.execute("SELECT lector, version_extraida FROM documento").fetchone(), ("pdf", "0:0:xls@2"))
        self.assertEqual(con.execute("SELECT count(*) FROM celda").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT count(*) FROM elemento WHERE tipo='pagina'").fetchone()[0], 2)
        self.assertFalse(xls_sospechoso(str(path)))
        with patch("verificar.original", return_value=str(path)):
            controles = comprobar(con, (1, path.name, "xls"), random.Random(7))
        self.assertTrue(controles)
        self.assertTrue(all(ok for _, _, _, ok in controles))

    def test_muestreo_repetible_con_semilla(self):
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.execute("CREATE TABLE celdas(fila INTEGER, valor TEXT)")
        con.executemany("INSERT INTO celdas VALUES (?,?)", [(i, str(i)) for i in range(100)])
        consulta = "SELECT fila, valor FROM celdas ORDER BY fila"
        a = muestra_sql(con, random.Random(20261023), consulta, (), 8)
        b = muestra_sql(con, random.Random(20261023), consulta, (), 8)
        c = muestra_sql(con, random.Random(42), consulta, (), 8)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(set(a)), 8)

    def test_zip_de_dibujos_no_es_libro_ooxml(self):
        path = self.raiz / "dibujos.xls"
        path.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1"))
        with zipfile.ZipFile(path, "a") as paquete:
            paquete.writestr("xl/drawings/drawing1.xml", "<drawing/>")
        self.assertTrue(zipfile.is_zipfile(path))
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO celda VALUES (1,'DR',13,14,'= N3',NULL,NULL)")
        self.assertEqual(comprobar_formulas_xml(con, 1, str(path), random.Random(7)), [])

    def test_perfiles_no_convierten_cache_ausente_en_medicion(self):
        cabecera = {1: "Nr", 3: "Nominal", 4: "Tol. +", 5: "Tol. -", 6: "Equipment",
                    7: "Cav.1", 8: "Cav.2", 9: "NOK"}
        datos = {1: "170", 3: "4", 4: "0", 5: "-0.1", 6: "CMM", 7: "3.95", 8: None}
        celdas = {(12, col): v for col, v in cabecera.items()}
        celdas.update({(14, col): v for col, v in datos.items()})
        numeros = {3: 4.0, 4: 0.0, 5: -0.1, 7: 3.95}
        perfil = perfilar([(fila, col, v, numeros.get(col) if fila == 14 else None)
                           for (fila, col), v in celdas.items()])
        self.assertEqual(perfil["filas_cota"], 1)
        self.assertEqual(perfil["vacias"], 1)
        self.assertEqual(perfil["ceros"], 0)
        lectura = leer_hoja("DR", celdas, {(14, 8)})
        self.assertEqual(len(lectura["medidas"]), 1)
        self.assertEqual(lectura["medidas"][0][8], 3.95)
        self.assertEqual(lectura["cualitativos"], 0)

    def test_reconstruccion_fallida_conserva_tabla_anterior(self):
        path = self.raiz / "biblioteca.sqlite"
        with closing(sqlite3.connect(path)) as con, con:
            con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
            con.executescript(formulas_aleatorias.ESQUEMA)
            con.execute("INSERT INTO documento(id,ruta,nombre,ext,tamano,mtime_ns,inventariado_el,estado) "
                        "VALUES (1,'informe.xls','informe.xls','xls',0,0,'test','extraido')")
            con.execute("INSERT INTO celda VALUES (1,'INTRO',1,1,'0.125',0.125,NULL)")
            con.execute("INSERT INTO celda_aleatoria VALUES (999,'ANTERIOR',1,1,'=RAND()','0.5')")
        with patch("formulas_aleatorias.conectar", side_effect=lambda: sqlite3.connect(path)), \
             patch("formulas_aleatorias.original", return_value="original-no-se-abre.xls"), \
             patch("formulas_aleatorias.xls_sospechoso", return_value=True), \
             patch("formulas_aleatorias.celdas_xls") as leer, patch("builtins.print"):
            leer.side_effect = RuntimeError("Excel no disponible")
            with self.assertRaises(SystemExit) as error:
                formulas_aleatorias.main()
            self.assertEqual(error.exception.code, 1)
            with closing(sqlite3.connect(path)) as con:
                self.assertEqual(con.execute("SELECT documento_id FROM celda_aleatoria").fetchall(), [(999,)])
                self.assertFalse(json.loads(con.execute("SELECT resumen FROM ejecucion ORDER BY id DESC LIMIT 1").fetchone()[0])["publicada"])
            leer.side_effect = None
            leer.return_value = [("INTRO", 1, 1, "=RAND()")]
            formulas_aleatorias.main()
            with closing(sqlite3.connect(path)) as con:
                self.assertEqual(con.execute("SELECT documento_id,valor FROM celda_aleatoria").fetchall(), [(1, "0.125")])
                self.assertTrue(json.loads(con.execute("SELECT resumen FROM ejecucion ORDER BY id DESC LIMIT 1").fetchone()[0])["publicada"])

    def test_lectura_xls_reintenta_en_otro_proceso(self):
        respuestas = [subprocess.CompletedProcess([], 1, "", "Error Open"),
                      subprocess.CompletedProcess([], 0, '[["INTRO",1,1,"=RAND()"]]', "")]
        with patch("formulas_aleatorias.subprocess.run", side_effect=respuestas) as ejecutar:
            self.assertEqual(formulas_aleatorias.celdas_xls("copia.xls"), [("INTRO", 1, 1, "=RAND()")])
            self.assertEqual(ejecutar.call_count, 2)


if __name__ == "__main__":
    unittest.main()
