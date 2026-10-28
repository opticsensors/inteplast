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
import cadena_correcciones
import perfil_correcciones
from lector_dr import ESQUEMA as ESQUEMA_DR
from perfil_correcciones import analizar_citas, citas_dim
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

    def test_citas_dim_de_las_plantillas_reales(self):
        """Formas de citar cotas encontradas en los PPTX (27/10/2026); los textos son reales."""
        casos = {
            "Tool correction 1.33 (DIM. Nr.170) Ø4-0,1": ["170"],
            "Correcció nr. 1.1 (DIM. Nr. 54, 57 and 60)": ["54", "57", "60"],
            "(DIM. Nr.06-7-8-83-101-102-103-106)  Centrar": ["6", "7", "8", "83", "101", "102", "103", "106"],
            "(DIM.3320)/(DIM.3320.1)/(DIM.3320.2)": ["3320", "3320.1", "3320.2"],
            "Tool correction DIM#6:   57,6   +0,45 -0,45": ["6"],
            "4 | . Dim Nº630 Ø66+0,1-0,03 | Dim Nº640 Ø37,8+0,15 | Flatness Nº680": ["630", "640"],
            "1 / . Dim 210Ø21,5-0,2": ["210"],
            "(DIM. Nr. 700,702,704 and 712)  6,8 ± 0,1": ["700", "702", "704", "712"],
            "(DIM. Nr.2801, 2800, )  X1 (Ø2,65 ±0,05": ["2801", "2800"],
            "(DIM. Nr. 62, 18, 191 104, 152  i 154) ": ["62", "18", "191", "104", "152", "154"],
            "(DIM. Nr.230 and Nr. 1330)   Flatness": ["230", "1330"],
            "(DIM. Nr.208+209)  4,87": ["208", "209"],
            "(DIM. Nr.137 11,5±0,2": ["137"],
            "(DIM. Nr. 1906 to 1912)": ["1906", "1912"],
            "Tool correction 1.7 (DIM. Nr.xx) ": ["XX"],
            "(DIM.Nr.4100/(DIM.Nr.4100,1)/(DIM.Nr.4100,2)/(DIM.Nr.4060) 1,1-0,1": ["4100", "4100.1", "4100.2", "4060"],
            "(DIM. Nr.3900) /(DIM. Nr.3900.1.2.3.4.5.6.7)reduce": ["3900"] + [f"3900.{i}" for i in range(1, 8)],
            "(DIM. Nr. 6, 7, 8,12, 19, 83, 84) ": ["6", "7", "8", "12", "19", "83", "84"],
            "Tool correction 5.3  dimension 3970  +0,10mm": ["3970"],
            "2 Korekce rozměru 210 odebráním oceli": ["210"],
            "Prosím posuňte rozměr 202 navařením o: Please move dim.: 202 by welding": ["202"],
            "apply an angle to improve dimension 0,3": [],
            "DIMENSIONS of the pin": [],
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(citas_dim(texto)[0], esperado)

    def test_citas_nominal_sin_cota_y_lista_o_subpunto(self):
        """Revision del 28/10/2026: `Dim 7,5+0,1` (3051, plan N4) es un nominal, no las cotas 7, 5, 0 y 1;
        `DIM. Nr.45,1` (3214) puede ser la lista 45, 1 o el subpunto 45.1: se guarda el literal y las dos lecturas."""
        codigos, _, ambiguas = analizar_citas("3 . Dim 7,5+0,1 Remove Steel increase the plastic in the red area")
        self.assertEqual(codigos, [])
        self.assertEqual([(x["literal"], x["tipo"]) for x in ambiguas], [("Dim 7,5+0,1", "nominal_sin_cota")])
        codigos, _, ambiguas = analizar_citas("Tool correction 1.3 (DIM. Nr.9)/(DIM. Nr.45,1)19,55±0,05/21,05±0,05")
        self.assertEqual(codigos, ["9"])
        self.assertEqual(ambiguas, [{"literal": "DIM. Nr.45,1", "tipo": "lista_o_subpunto", "lista": ["45", "1"],
                                     "subpunto": "45.1"}])
        for texto, esperado in {"(DIM. Nr. 700,702,704 and 712)": ["700", "702", "704", "712"],
                                "(DIM. Nr. 6, 7, 8,12, 19, 83, 84) ": ["6", "7", "8", "12", "19", "83", "84"],
                                "(DIM.Nr.4100,1)": ["4100.1"]}.items():
            with self.subTest(texto=texto):
                self.assertEqual(analizar_citas(texto)[0], esperado)
                self.assertEqual(analizar_citas(texto)[2], [])

    def bd_cadena(self, pieza, docs, diapositivas, medidas, fechas=None):
        """BD minima para la cadena. docs: (id, ruta, carpeta_norm, ext); diapositivas: (doc, texto, cotas[, ambiguas]);
        medidas: doc -> [(cota, fila, [(cavidad, valor, marca)], nominal, tol_sup, tol_inf[, etiqueta])];
        fechas: doc -> report_date."""
        con = sqlite3.connect(self.raiz / f"biblioteca-{pieza}.sqlite")
        self.addCleanup(con.close)
        con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
        con.executescript(ESQUEMA_DR)
        con.executescript(perfil_correcciones.ESQUEMA)
        con.executescript("CREATE TABLE perfil_ppap (documento_id INTEGER, hoja TEXT, metadatos TEXT);")
        for i, ruta, carpeta, ext in docs:
            con.execute("INSERT INTO documento(id, ruta, codigo, carpeta_norm, nombre, ext, tamano, mtime_ns, inventariado_el, "
                        "estado) VALUES (?,?,?,?,?,?,0,0,'test','extraido')", (i, ruta, pieza, carpeta, ruta.rsplit("/", 1)[1], ext))
        for doc, texto, cotas, *ambiguas in diapositivas:
            ruta = next(r for i, r, _, _ in docs if i == doc)
            con.execute("INSERT INTO perfil_correccion(documento_id, diapositiva, pieza, ruta, plan, cotas, texto, cotas_ambiguas) "
                        "VALUES (?, 1, ?, ?, NULL, ?, ?, ?)", (doc, pieza, ruta, json.dumps(cotas), texto,
                                                              json.dumps(ambiguas[0] if ambiguas else [])))
        for doc, filas in medidas.items():
            con.execute("INSERT INTO lectura_dr(documento_id, hoja, papel, columnas) VALUES (?, 'DR', 'informe', ?)",
                        (doc, json.dumps({"codigo": 1, "tipo": 3, "nominal": 4})))
            if fechas and doc in fechas:
                con.execute("INSERT INTO perfil_ppap VALUES (?, 'DR', ?)", (doc, json.dumps({"report_date": fechas[doc]})))
            for cota, fila, celdas, nominal, sup, inf, *etiqueta in filas:
                if etiqueta:
                    con.execute("INSERT INTO celda(documento_id, hoja, fila, col, valor) VALUES (?, 'DR', ?, 2, ?)",
                                (doc, fila, etiqueta[0]))
                for col, (cavidad, valor, marca) in enumerate(celdas, 8):
                    con.execute("INSERT INTO medida_dr VALUES (?, 'DR', ?, ?, ?, ?, ?, ?, 'CMM', ?, ?, ?)",
                                (doc, fila, col, cota, nominal, sup, inf, cavidad, valor, marca))
        return con

    @staticmethod
    def celdas(*valores, cavidades=4, marca=None):
        return [(f"c{i % cavidades + 1}", v, marca) for i, v in enumerate(valores)]

    def test_cadena_salta_bloques_heredados_y_usa_el_xls_de_la_carpeta(self):
        """Regla del 3212 (historial-molde, 2): origen = XLS de la carpeta; validacion = siguiente muestreo nuevo.
        Como en el 3212 real, intern.02 repite las filas de intern.01 en otra posicion y con el bloque de cavidades
        duplicado en columnas (8 valores por fila en vez de 4)."""
        base = "0- Bolt Eye/9999 Prueba/"
        docs = [(1, base + "5- Retoques/20240124-Mold correction_1_P9999.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques/9999-00_intern.01_mold_correction.xls", "retoques", "xls"),
                (3, base + "5- Retoques/9999-00_intern.04_correction02.xls", "retoques", "xls"),
                (4, base + "5- Retoques/Old/9999-00_intern.07.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/9999-00_intern.01.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/9999-00_intern.02.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/9999-00_intern.03.xls", "metrologia", "xls")]
        a1, a2 = (3.43, 3.42, 3.44, 3.43), (3.41, 3.40, 3.42, 3.41)
        tol = (4.0, 0.0, -0.1)
        medidas = {11: [("170", 119, self.celdas(*a1), *tol), ("170", 120, self.celdas(*a2), *tol)],
                   12: [("170", 130, self.celdas(*a1, *a1), *tol), ("170", 131, self.celdas(*a2, *a2), *tol)],
                   13: [("170", 123, self.celdas(3.97, 3.98, 3.97, 3.96), *tol),
                        ("170", 124, self.celdas(3.99, 3.98, 3.97, 3.98), *tol),
                        ("170", 125, [("c1", 5.5, "aleatoria")], *tol)]}
        con = self.bd_cadena("9999", docs, [(1, "Tool correction 1.33 (DIM. Nr.170) 24/01/2024", ["170"])], medidas,
                             {11: "2024-01-25", 12: "2024-02-25", 13: "2024-03-25"})
        self.assertEqual(cadena_correcciones.construir(con, "9999"), 1)
        fila = con.execute("SELECT origen_muestreo, fuente_origen, origen_fuera, validacion_muestreo, validacion_n, "
                           "validacion_fuera, validacion_estado, avisos FROM cadena_correccion").fetchone()
        self.assertEqual(fila[:7], (1, "xls_carpeta", 8, 3, 8, 0, "nueva"))
        avisos = json.loads(fila[7])
        self.assertTrue(any("intern.02 = intern.01" in a for a in avisos), avisos)
        self.assertTrue(any("RAND" in a for a in avisos), avisos)

    def test_cadena_series_filas_desplazadas_copias_y_valores_sin_tolerancia(self):
        """Revision del 28/10/2026: 3168-00 frente a 3168-10 (series), 3218 cota 2402 (valores contenidos en el
        bloque anterior pero distintos celda a celda), copia de intern.03 que repite intern.02 y filas sin tolerancia."""
        base = "7- Planitudes/9996/"
        docs = [(1, base + "5- Retoques/20230227-Mold correction_1_P9996.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques/9996-00_intern.01_correction.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9996-00_intern.01.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Interns/9996-10_intern.01.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9996-00_intern.02.xls", "metrologia", "xls"),
                (14, base + "4- Metrologia/Interns/9996-00_intern.03.xls", "metrologia", "xls"),
                (15, base + "4- Metrologia/Customer/9996-00_intern.03.xls", "metrologia", "xls")]
        tol = (0.2, 0.0, -0.05)
        f1, f2 = (0.15, 0.15, 0.17, 0.15), (0.12, 0.14, 0.16, 0.13)
        medidas = {11: [("230", 10, self.celdas(*f1), *tol), ("230", 11, self.celdas(*f2), *tol)],
                   12: [("230", 10 + k, self.celdas(0.3, 0.31, 0.32, 0.3), *tol) for k in range(3)],
                   13: [("230", 11, self.celdas(*f1), *tol), ("230", 12, self.celdas(*f2), *tol)],
                   14: [("230", 10, self.celdas(0.13, 0.13, 0.13, 0.13), *tol),
                        ("230", 11, self.celdas(0.14, 0.12, 0.14, 0.12), *tol),
                        ("230", 12, self.celdas(0.15, 0.15, 0.15, 0.15), None, None, None)],
                   15: [("230", 10, self.celdas(*f1), *tol), ("230", 11, self.celdas(*f2), *tol)]}
        con = self.bd_cadena("9996", docs, [(1, "Tool correction 1.1 (DIM. Nr.230) 27/02/2023", ["230"])], medidas,
                             {11: "2023-02-20", 12: "2025-03-14", 13: "2023-04-14", 14: "2023-05-10", 15: "2023-05-10"})
        cadena_correcciones.construir(con, "9996")
        fila = con.execute("SELECT serie, origen_muestreo, origen_documento_id, validacion_muestreo, validacion_documento_id, "
                           "validacion_n, validacion_evaluables, validacion_estado, avisos FROM cadena_correccion").fetchone()
        self.assertEqual(fila[:8], ("00", 1, 11, 3, 14, 12, 8, "nueva"))
        avisos = json.loads(fila[8])
        self.assertTrue(any("intern.02 = intern.01" in a for a in avisos), avisos)
        self.assertTrue(any("I-006" in a and "repite" in a for a in avisos), avisos)   # la copia de Customer repite .02
        self.assertTrue(any("sin nominal o tolerancia" in a for a in avisos), avisos)
        self.assertFalse(any("9996-10" in a for a in avisos), avisos)                  # la serie 10 no es una copia

    def test_cadena_contradiccion_de_orden_deja_indeterminado(self):
        """3167: el plan 3 (05/06/2024) no tiene XLS; por fecha saldria Int_02 (2023) y la validacion Int_03, que no
        tiene fecha valida y ya es el origen del plan 2 (14/02/2024)."""
        base = "6- Pockets/9995/"
        docs = [(1, base + "5- Retoques/2n loop/20240214_Mold correction_2_P9995.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques/2n loop/9995-00 Int_03_corr.xls", "retoques", "xls"),
                (3, base + "5- Retoques/3rd loop/20240605_Mold correction_3_P9995.pptx", "retoques", "pptx"),
                (11, base + "4- Metrologia/Interns/9995-00 Int_02.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Interns/9995-00 Int_03.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9995-00 Int_04.xls", "metrologia", "xls")]
        tol = (3.0, 0.1, -0.1)
        medidas = {doc: [("1320", 5, self.celdas(*(round(v + 0.01 * j, 3) for j in range(4))), *tol)]
                   for doc, v in ((11, 3.3), (12, 3.2), (13, 3.05))}
        con = self.bd_cadena("9995", docs, [(1, "Tool correction 2.1 (DIM. Nr.1320)", ["1320"]),
                                            (3, "Tool correction 3.1 (DIM. Nr.1320) 05/06/2024", ["1320"])], medidas,
                             {11: "2023-05-29", 12: "1899-12-31", 13: "2025-04-14"})
        cadena_correcciones.construir(con, "9995")
        filas = {doc: (o, v, e, json.loads(a)) for doc, o, v, e, a in con.execute(
            "SELECT documento_id, origen_muestreo, validacion_muestreo, validacion_estado, avisos FROM cadena_correccion")}
        self.assertEqual(filas[1][:3], (3, 4, "nueva"))
        self.assertEqual(filas[3][:3], (None, None, "indeterminada"))
        self.assertTrue(any("ya parte de intern.03" in a for a in filas[3][3]), filas[3][3])

    def test_cadena_resuelve_citas_ambiguas_con_las_medidas(self):
        """3214 `DIM. Nr.45,1`: se mide 45.1 y no 45, asi que es el subpunto; sin pista, quedan las dos lecturas."""
        base = "2- Nervios/9994/"
        docs = [(1, base + "5- Retoques/20231003-Mold correction_1_P9994.pptx", "retoques", "pptx"),
                (11, base + "4- Metrologia/9994-00_intern.01.xls", "metrologia", "xls")]
        ambigua = [{"literal": "DIM. Nr.45,1", "tipo": "lista_o_subpunto", "lista": ["45", "1"], "subpunto": "45.1"}]
        sin_pista = [{"literal": "DIM. Nr.7,2", "tipo": "lista_o_subpunto", "lista": ["7", "2"], "subpunto": "7.2"}]
        medidas = {11: [("45.1", 3, self.celdas(21.0, 21.1, 21.05, 21.02), 21.05, 0.05, -0.05),
                        ("9", 4, self.celdas(19.5, 19.6, 19.55, 19.5), 19.55, 0.05, -0.05)]}
        con = self.bd_cadena("9994", docs, [(1, "Tool correction 1.3 (DIM. Nr.9)/(DIM. Nr.45,1) (DIM. Nr.7,2)", ["9"],
                                             ambigua + sin_pista)], medidas)
        cadena_correcciones.construir(con, "9994")
        filas = {cota: json.loads(a) for cota, a in con.execute("SELECT cota, avisos FROM cadena_correccion")}
        self.assertEqual(sorted(filas), ["2", "45.1", "7", "7.2", "9"])
        self.assertTrue(any("subpunto 45.1" in a for a in filas["45.1"]), filas["45.1"])
        self.assertTrue(any("ambigua" in a for a in filas["7.2"]), filas["7.2"])

    def test_cadena_subcarpeta_del_plan_sin_retroceso_subpuntos_y_avisos(self):
        """3309: tres planes comparten carpeta con Int_01; el plan 2 tiene su XLS en `Mold Correction Loop 2/`."""
        con = sqlite3.connect(self.raiz / "biblioteca.sqlite")
        self.addCleanup(con.close)
        con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
        con.executescript(ESQUEMA_DR)
        con.executescript(perfil_correcciones.ESQUEMA)
        con.executescript("CREATE TABLE perfil_ppap (documento_id INTEGER, hoja TEXT, metadatos TEXT);")
        base = "1- Clips/9998/"
        docs = [(1, base + "5- Retoques molde/20260420-Mold correction_1_P9998.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20260619-Mold correction_2_P9998.pptx", "retoques", "pptx"),
                (3, base + "5- Retoques molde/20260821-P9998-T3_mold correction.pptx", "retoques", "pptx"),
                (4, base + "5- Retoques molde/Copia de 9998-00 Int_01.xls", "retoques", "xls"),
                (5, base + "5- Retoques molde/Loop 2/9998-00 Int_02_mold correction loop 2.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/9998-00 Int_01.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/9998-00 Int_02.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/9998-00 Int_03.xls", "metrologia", "xls"),
                (14, base + "4- Metrologia/Customer/P9998-00 Int_03.xls", "metrologia", "xls"),
                (15, base + "4- Metrologia/PPAP-9998-00_INF.01.xls", "metrologia", "xls")]
        for i, ruta, carpeta, ext in docs:
            con.execute("INSERT INTO documento(id, ruta, codigo, carpeta_norm, nombre, ext, tamano, mtime_ns, inventariado_el, "
                        "estado) VALUES (?,?,'9998',?,?,?,0,0,'test','extraido')", (i, ruta, carpeta, ruta.rsplit("/", 1)[1], ext))
        diapositivas = [(1, "Mold correction nº1 Tool correction DIM#14: 1 (+0,2 -0,2) XB – 20/04/2026", '["14"]'),
                        (2, "Mold correction nº2 Tool correction DIM#14: 1 (+0,2 -0,2) XB – 19/06/2026", '["14"]'),
                        (3, "For DIM #210 we suggest adding material on the two red surfaces to bring the dimension into tolerance.", '["210"]')]
        for doc, texto, cotas in diapositivas:
            con.execute("INSERT INTO perfil_correccion(documento_id, diapositiva, pieza, ruta, plan, cotas, texto) VALUES "
                        "(?, 1, '9998', ?, NULL, ?, ?)", (doc, docs[doc - 1][1], cotas, texto))
        con.execute("INSERT INTO perfil_correccion(documento_id, diapositiva, pieza, ruta, plan, cotas, texto) VALUES "
                    "(99, 1, '9997', 'otra/20260101-Mold correction_1_P9997.pptx', '1', '[]', ?)", (diapositivas[2][1] + " " * 3,))
        medidas = {11: {"14": (0.57, 0.66), "210.1": (3.2,), "210.2": (3.3,)},
                   12: {"14": (0.61, 0.66), "210.1": (3.25,), "210.2": (3.31,)},
                   13: {"14": (0.749, 0.879), "210.1": (3.4,), "210.2": (3.41,)},
                   14: {"14": (0.84, 0.90)},
                   15: {"14": (0.95, 0.96)}}
        for doc, cotas in medidas.items():
            con.execute("INSERT INTO lectura_dr(documento_id, hoja, papel) VALUES (?, 'DR', 'informe')", (doc,))
            for cota, valores in cotas.items():
                for fila, v in enumerate(valores):
                    con.execute("INSERT INTO medida_dr VALUES (?, 'DR', ?, 8, ?, 1.0, 0.2, -0.2, 'CT', 'c1', ?, NULL)",
                                (doc, fila, cota, v))
        cadena_correcciones.construir(con, "9998")
        filas = {doc: (o, v, json.loads(a)) for doc, o, v, a in con.execute(
            "SELECT documento_id, origen_muestreo, validacion_muestreo, avisos FROM cadena_correccion")}
        self.assertEqual(filas[1][:2], (1, 2))                      # plan 1: Int_01 de la carpeta
        self.assertEqual(filas[2][:2], (2, 3))                      # plan 2: la subcarpeta con su numero, no Int_01
        self.assertTrue(any("I-006" in a for a in filas[2][2]), filas[2][2])   # Int_03 con dos versiones
        self.assertIsNone(filas[3][0])                              # T3: Int_01 seria retroceder
        self.assertTrue(any("ya parte de intern.02" in a for a in filas[3][2]), filas[3][2])
        self.assertTrue(any("subpuntos 210.1, 210.2" in a for a in filas[3][2]), filas[3][2])
        self.assertTrue(any("I-309" in a and "pieza 9997" in a for a in filas[3][2]), filas[3][2])
        self.assertFalse(any("INF" in a for fila in filas.values() for a in fila[2]))   # el INF.01 no es intern.01

    def test_cadena_filas_reordenadas_y_etiquetas_de_elemento(self):
        """Revision 3 (28/10/2026), 3186 cota 103: Customer/intern.04 trae las dos filas de intern.03 intercambiadas y sin
        LEFT/RIGHT; es una copia. Con las etiquetas cambiadas (cota 104), la correspondencia es dudosa: indeterminada."""
        base = "1- Clips/9993/"
        docs = [(1, base + "5- Retoques molde/20230915_3rd loop/2023915-Mold correction_3_P9993.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20230915_3rd loop/9993-00_intern.03_corrections.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9993-00_intern.03.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Customer/9993-00_intern.04.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9993-00_intern.04.xls", "metrologia", "xls"),
                (14, base + "4- Metrologia/Interns/9993-00_intern.05.xls", "metrologia", "xls")]
        tol = (15.1, 0.05, -0.05)
        a, b = (15.174, 15.172, 15.17, 15.176), (15.175, 15.167, 15.168, 15.178)
        c, d = (15.12, 15.11, 15.13, 15.12), (15.1, 15.09, 15.11, 15.1)
        medidas = {11: [("103", 17, self.celdas(*a), *tol, "LEFT"), ("103", 18, self.celdas(*b), *tol, "RIGHT"),
                        ("104", 20, self.celdas(*a), *tol, "LEFT"), ("104", 21, self.celdas(*b), *tol, "RIGHT")],
                   12: [("103", 16, self.celdas(*b), *tol), ("103", 28, self.celdas(*a), *tol)],
                   13: [("103", 17, self.celdas(*a), *tol, "LEFT"), ("103", 18, self.celdas(*b), *tol, "RIGHT"),
                        ("104", 20, self.celdas(*b), *tol, "LEFT"), ("104", 21, self.celdas(*a), *tol, "RIGHT")],
                   14: [("103", 17, self.celdas(*c), *tol, "LEFT"), ("103", 18, self.celdas(*d), *tol, "RIGHT"),
                        ("104", 20, self.celdas(*c), *tol, "LEFT"), ("104", 21, self.celdas(*d), *tol, "RIGHT")]}
        con = self.bd_cadena("9993", docs, [(1, "Tool correction 2.2 (DIM. Nr. 103) / (DIM. Nr. 104)", ["103", "104"])],
                             medidas, {11: "2023-09-14", 12: "2023-10-10", 13: "2023-10-10", 14: "2023-11-10"})
        cadena_correcciones.construir(con, "9993")
        filas = {cota: (v, e, json.loads(x)) for cota, v, e, x in con.execute(
            "SELECT cota, validacion_muestreo, validacion_estado, avisos FROM cadena_correccion")}
        self.assertEqual(filas["103"][:2], (5, "nueva"))                  # intern.04 repite .03, aunque reordenado
        self.assertTrue(any("reordenad" in x for x in filas["103"][2]), filas["103"][2])
        self.assertEqual(filas["104"][:2], (4, "herencia_indeterminada"))  # mismos valores con LEFT/RIGHT cambiados

    def test_cadena_valores_excluidos_y_sin_medidas_validas(self):
        """3218 cota 2800: intern.26 = intern.21 mas dos filas de ceros, no es nueva. Un informe que solo trae valores
        excluidos no puede validar: sin medidas validas, con el aviso de los ceros."""
        base = "1- Clips/9992/"
        docs = [(1, base + "5- Retoques molde/20250905 9th/20250905-Mold correction_9_P9992.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20250905 9th/9992-00_intern.21_correction.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9992-00_intern.21.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Interns/9992-00_intern.26.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9992-00_intern.27.xls", "metrologia", "xls")]
        tol = (3.0, 0.05, -0.05)
        f1, f2 = (3.02, 3.03, 3.02, 3.01), (3.01, 3.01, 2.99, 3.01)
        cero = self.celdas(0.0, 0.0, marca="cero")
        medidas = {11: [("2800", 10, self.celdas(*f1), *tol), ("2800", 11, self.celdas(*f2), *tol)],
                   12: [("2800", 10, self.celdas(*f1), *tol), ("2800", 11, self.celdas(*f2), *tol),
                        ("2800", 12, cero, *tol), ("2800", 13, cero, *tol)],
                   13: [("2800", 10, cero, *tol), ("2800", 11, cero, *tol)]}
        con = self.bd_cadena("9992", docs, [(1, "Tool correction 9.7 (DIM. Nr.2800) 05/09/2025", ["2800"])], medidas,
                             {11: "2025-09-01", 12: "2025-10-01", 13: "2025-11-01"})
        cadena_correcciones.construir(con, "9992")
        v, e, avisos = con.execute("SELECT validacion_muestreo, validacion_estado, avisos FROM cadena_correccion").fetchone()
        avisos = json.loads(avisos)
        self.assertEqual((v, e), (None, "sin_medidas_validas"))
        self.assertTrue(any("intern.26 = intern.21" in x for x in avisos), avisos)
        self.assertTrue(any("intern.27 sin medidas validas" in x and "cero" in x for x in avisos), avisos)

    def test_cadena_copias_con_tolerancias_distintas(self):
        """3174 cota 504: mismas medidas en las dos copias de intern.26, tolerancia +-0,15 en la del cliente y +-0,07 en
        la interna. Son copias distintas a efectos de resultado: la conclusion depende de la copia."""
        base = "1- Clips/9991/"
        docs = [(1, base + "5- Retoques molde/20250213_8th/20250214-Mold correction_8_9991.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20250213_8th/9991-00_intern.25_korekce.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9991-00_intern.25.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Customer/9991-00_intern.26.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9991-00_intern.26.xls", "metrologia", "xls")]
        valores = (5.70, 5.74, 5.60, 5.66)
        medidas = {11: [("504", 5, self.celdas(5.9, 5.85, 5.88, 5.9), 5.65, 0.07, -0.07)],
                   12: [("504", 5, self.celdas(*valores), 5.65, 0.15, -0.15)],
                   13: [("504", 5, self.celdas(*valores), 5.65, 0.07, -0.07)]}
        con = self.bd_cadena("9991", docs, [(1, "Tool correction 2.1 (DIM. No.504) 14/02/2025", ["504"])], medidas,
                             {11: "2025-02-10", 12: "2025-03-18", 13: "2025-03-18"})
        cadena_correcciones.construir(con, "9991")
        depende, alternativas = con.execute("SELECT depende_copia, alternativas FROM cadena_correccion").fetchone()
        self.assertEqual(depende, 1)
        self.assertEqual(sorted(a["fuera"] for a in json.loads(alternativas) if a["papel"] == "validacion"), [0, 1])

    def test_cadena_fecha_del_plan_incoherente_con_su_xls(self):
        """3186 loop 2: el PPTX hereda el nombre del loop 1 (21/04/2023) y su XLS es del 20/06/2023; la carpeta dice
        21/06/2023. Se conserva la fecha original y se ordena con la de la carpeta, como estimada. Sin fecha en la
        carpeta (3195 N2, nombre de 2020) solo aviso y orden sin comprobar."""
        base = "1- Clips/9990/"
        docs = [(1, base + "5- Retoques molde/20230421_1st loop/20230421-Mold correction_1_P9990.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20230421_1st loop/9990-00_intern.01_corrections.xls", "retoques", "xls"),
                (3, base + "5- Retoques molde/20230621_2nd loop/20230421-Mold correction_1_P9990.pptx", "retoques", "pptx"),
                (4, base + "5- Retoques molde/20230621_2nd loop/9990-00_intern.02_corrections.xls", "retoques", "xls"),
                (5, base + "5- Retoques molde/N2/20200527-Mold correction_2_P9990.pptx", "retoques", "pptx"),
                (6, base + "5- Retoques molde/N2/9990-00_intern.03_correction.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9990-00_intern.01.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Interns/9990-00_intern.02.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9990-00_intern.03.xls", "metrologia", "xls"),
                (14, base + "4- Metrologia/Interns/9990-00_intern.04.xls", "metrologia", "xls")]
        tol = (2.0, 0.1, -0.1)
        medidas = {doc: [("300", 5, self.celdas(*(round(v + 0.01 * j, 3) for j in range(4))), *tol)]
                   for doc, v in ((11, 2.3), (12, 2.25), (13, 2.2), (14, 2.05))}
        con = self.bd_cadena("9990", docs, [(1, "Tool correction 1.6 (DIM. Nr.300)", ["300"]),
                                            (3, "Tool correction 2.7 (DIM. Nr.300)", ["300"]),
                                            (5, "Tool correction 2.10 (DIM. Nr.300)", ["300"])], medidas,
                             {11: "2023-04-20", 12: "2023-06-20", 13: "2023-10-16", 14: "2023-12-11"})
        cadena_correcciones.construir(con, "9990")
        filas = {doc: (f, fo, fu, json.loads(a)) for doc, f, fo, fu, a in con.execute(
            "SELECT documento_id, fecha_correccion, fecha_orden, fuente_fecha_orden, avisos FROM cadena_correccion")}
        self.assertEqual(filas[3][:2], ("2023-04-21", "2023-06-21"))
        self.assertIn("carpeta", filas[3][2])
        self.assertTrue(any("estimada" in x for x in filas[3][3]), filas[3][3])
        self.assertEqual(filas[5][:2], ("2020-05-27", "2020-05-27"))
        self.assertTrue(any("no fiable" in x and "sin comprobar" in x for x in filas[5][3]), filas[5][3])
        self.assertFalse(any("fiable" in x or "estimada" in x for x in filas[1][3]), filas[1][3])

    def test_cadena_copias_del_mismo_muestreo_con_fechas_distintas(self):
        """3205/3206 intern.17: copia del cliente del 23/04/2024 e interna del 09/06/2025. Para un plan del 25/04/2024 el
        origen por fecha es la copia coherente con esa fecha, y se avisa de la diferencia."""
        base = "2- Nervios/9989/"
        docs = [(1, base + "5- Retoques molde/20240425-Mold correction_1_P9989.pptx", "retoques", "pptx"),
                (11, base + "4- Metrologia/Interns/9989-00_intern.16.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Customer/9989-00_intern.17.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9989-00_intern.17.xls", "metrologia", "xls")]
        tol = (8.0, 0.1, -0.1)
        medidas = {11: [("50", 5, self.celdas(8.2, 8.21, 8.22, 8.2), *tol)],
                   12: [("50", 5, self.celdas(8.15, 8.16, 8.14, 8.15), *tol)],
                   13: [("50", 5, self.celdas(8.01, 8.02, 8.0, 8.01), *tol), ("50", 6, self.celdas(8.0, 8.03, 8.02, 8.01), *tol)]}
        con = self.bd_cadena("9989", docs, [(1, "Tool correction 1.1 (DIM. Nr.50)", ["50"])], medidas,
                             {11: "2024-03-01", 12: "2024-04-23", 13: "2025-06-09"})
        cadena_correcciones.construir(con, "9989")
        o, doc, fecha, avisos = con.execute(
            "SELECT origen_muestreo, origen_documento_id, origen_fecha, avisos FROM cadena_correccion").fetchone()
        self.assertEqual((o, doc, fecha), (17, 12, "2024-04-23"))
        self.assertTrue(any("fechas distintas" in x for x in json.loads(avisos)), avisos)
        # 3206 `intern.122`: version 2 de intern.12, no el muestreo 122
        self.assertEqual(cadena_correcciones.MUESTREO.search("3206-00_intern.122.xls").groups(), ("12", "2"))
        self.assertEqual(cadena_correcciones.MUESTREO.search("3174-00_intern09_corr..xls").groups(), ("9", None))

    def test_cadena_depende_copia_solo_con_origenes_admisibles(self):
        """Revision 4 (28/10/2026), 3174 cota 210: la copia del cliente de intern.26 (18/03/2025) es posterior a la
        correccion (14/02/2025); se conserva como descartada y no cuenta para depende_copia. Si ninguna copia de origen
        es anterior (plan con fecha no fiable), se comparan todas, sin darlas por validas, y los avisos se mantienen."""
        base = "1- Clips/9988/"
        docs = [(1, base + "5- Retoques molde/20250213_8th/20250214-Mold correction_8_9988.pptx", "retoques", "pptx"),
                (2, base + "5- Retoques molde/20250213_8th/9988-00_intern.26_korekce.xls", "retoques", "xls"),
                (3, base + "5- Retoques molde/Pla 1/Pla de correcio_1_P9988.pptx", "retoques", "pptx"),
                (4, base + "5- Retoques molde/Pla 1/9988-00_intern.10_correccio.xls", "retoques", "xls"),
                (11, base + "4- Metrologia/Interns/9988-00_intern.26.xls", "metrologia", "xls"),
                (12, base + "4- Metrologia/Customer/9988-00_intern.26.xls", "metrologia", "xls"),
                (13, base + "4- Metrologia/Interns/9988-00_intern.32.xls", "metrologia", "xls"),
                (21, base + "4- Metrologia/Interns/9988-00_intern.10.xls", "metrologia", "xls"),
                (22, base + "4- Metrologia/Customer/9988-00_intern.10.xls", "metrologia", "xls"),
                (23, base + "4- Metrologia/Interns/9988-00_intern.11.xls", "metrologia", "xls")]
        tol = (3.4, 0.05, -0.05)
        medidas = {11: [("210", 5, self.celdas(3.27, 3.33, 3.41, 3.3), *tol)],
                   12: [("210", 5, self.celdas(3.39, 3.4, 3.41, 3.38), *tol)],
                   13: [("210", 5, self.celdas(3.4, 3.39, 3.41, 3.4), *tol)],
                   21: [("19", 5, self.celdas(3.2, 3.25, 3.22, 3.21), *tol)],
                   22: [("19", 5, self.celdas(3.38, 3.4, 3.42, 3.41), *tol)],
                   23: [("19", 5, self.celdas(3.4, 3.41, 3.39, 3.4), *tol)]}
        con = self.bd_cadena("9988", docs, [(1, "Korekce rozměru 210 odebráním oceli 14/02/2025", ["210"]),
                                            (3, "Tool correction 6.1 (DIM. Nr.19) 21/03/2024", ["19"])], medidas,
                             {11: "2025-01-30", 12: "2025-03-18", 13: "2025-05-30", 21: "2024-04-05", 22: "2024-04-20",
                              23: "2024-03-01"})
        cadena_correcciones.construir(con, "9988")
        filas = {cota: (o, d, v, json.loads(a or "[]"), json.loads(x)) for cota, o, d, v, a, x in con.execute(
            "SELECT cota, origen_documento_id, depende_copia, validacion_muestreo, alternativas, avisos FROM cadena_correccion")}
        origen, depende, _, alternativas, _ = filas["210"]
        self.assertEqual((origen, depende), (11, 0))
        descartada = [a for a in alternativas if a["copias"] == ["Customer/9988-00_intern.26.xls"]]
        self.assertEqual(len(descartada), 1)
        self.assertIs(descartada[0]["admisible"], False)
        self.assertIn("posterior", descartada[0]["motivo"])
        # Revision 5: el plan del 21/03/2024 tiene una fecha no fiable (sus informes de origen son del 05/04 y del 20/04).
        # Ni el origen ni la validacion se filtran por esa fecha: validez temporal sin comprobar, ni valida ni invalida.
        _, _, validacion, alternativas, avisos = filas["19"]
        origenes = [a for a in alternativas if a["papel"] == "origen"]
        self.assertTrue(origenes and all(a["admisible"] is None and "sin comprobar" in a["motivo"] for a in origenes))
        self.assertEqual(validacion, 11)   # intern.11 (01/03/2024) no se descarta como anterior a una fecha no fiable
        for categorica in ("sin validez temporal", "ninguna copia de origen es anterior", "posterior a la correccion",
                           "anterior a la correccion"):
            self.assertFalse(any(categorica in x for x in avisos), (categorica, avisos))
        self.assertTrue(any("no fiable" in x and "sin comprobar" in x and "diapositiva 2024-03-21" in x for x in avisos),
                        avisos)

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
