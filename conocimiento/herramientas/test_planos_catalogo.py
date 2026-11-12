"""Catálogo de planos (planos_catalogo.py) con registros sintéticos. Sin ficheros del cliente ni la biblioteca.

    python -B -m unittest discover -s conocimiento/herramientas -p "test_planos_catalogo.py"
"""

import copy
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planos_catalogo as pc  # noqa: E402

SHA = "a" * 64


def plano(**cambios):
    p = dict(numero="0196S0000K", componente=None, paginas=[1], revision="02", tipo="DP/TD 000",
             fecha_cambio="2025-03-11", cambio="3E1014105160", fecha_emision=None, pieza="3233")
    p.update(cambios)
    return p


def registro(**cambios):
    r = dict(documento_id=10, ruta="3- Paredes muy Delgadas/3233/1- 2D y 3D pieza/x.pdf", sha256=SHA, carpeta_pieza="3233",
             copia_de=None, fecha_nombre="2025-03-16", papel="plano", globos=False, planos=[plano()],
             verificacion="capa de texto", procedencia={}, evidencia="p1, tabla", nota=None, revisado="2026-11-12")
    r.update(cambios)
    return r


class FechasDeCabecera(unittest.TestCase):
    def test_normaliza_sin_perder_el_literal(self):
        self.assertEqual(pc.normalizar_fecha("2026-09-23T00:00:00"), "2026-09-23")
        self.assertEqual(pc.normalizar_fecha("2026-09-23 00:00:00"), "2026-09-23")
        self.assertEqual(pc.normalizar_fecha("13/02/2024"), "2024-02-13")
        self.assertEqual(pc.normalizar_fecha("4.9.2024"), "2024-09-04")

    def test_rangos_texto_y_cero_de_excel_no_son_fecha(self):
        for literal in ("29.08.2024-4.9.2024", "13/02/2024 -10/04/2024", "TM April 2025", "xx", "1899-12-31",
                        "2025-99-99", "", None):
            self.assertIsNone(pc.normalizar_fecha(literal), literal)


class Registro(unittest.TestCase):
    def test_registro_valido(self):
        self.assertEqual(pc.comprobar_registro(registro()), [])

    def test_paginas(self):
        for paginas in ([], [0], [-1], [2, 1], [1, 1], ["1"], [True], None):
            with self.subTest(paginas=paginas):
                self.assertTrue(pc.comprobar_registro(registro(planos=[plano(paginas=paginas)])))

    def test_dos_planos_no_comparten_pagina(self):
        r = registro(planos=[plano(paginas=[1]), plano(numero="BSG-296-00", paginas=[1])])
        self.assertTrue(pc.comprobar_registro(r))

    def test_fechas(self):
        self.assertTrue(pc.comprobar_registro(registro(planos=[plano(fecha_cambio="2025-99-99")])))
        self.assertTrue(pc.comprobar_registro(registro(planos=[plano(fecha_cambio="2025-03")])))
        self.assertTrue(pc.comprobar_registro(registro(fecha_nombre="2025-02-30")))
        self.assertEqual(pc.comprobar_registro(registro(planos=[plano(fecha_emision="2023-04")])), [])
        self.assertTrue(pc.comprobar_registro(registro(planos=[plano(fecha_emision="2023-13")])))

    def test_procedencia_por_campo(self):
        self.assertEqual(pc.comprobar_registro(registro(procedencia={"revision": "nombre del fichero",
                                                                      "fecha_cambio": "inferido de 1941"})), [])
        self.assertTrue(pc.comprobar_registro(registro(procedencia={"revision": "de oídas"})))
        self.assertTrue(pc.comprobar_registro(registro(procedencia={"color": "visto"})))
        self.assertTrue(pc.comprobar_registro(registro(procedencia=None)))

    def test_falta_un_campo(self):
        r = registro()
        del r["procedencia"]
        self.assertTrue(pc.comprobar_registro(r))


class Copias(unittest.TestCase):
    def test_copia_coherente(self):
        original = registro()
        copia_ = registro(documento_id=11, ruta="otra/x.pdf", copia_de=10, verificacion="copia idéntica de 10")
        self.assertEqual(pc.comprobar_copias([original, copia_]), [])

    def test_copia_con_otra_revision(self):
        original = registro()
        copia_ = registro(documento_id=11, copia_de=10, planos=[plano(revision="01")])
        self.assertTrue(pc.comprobar_copias([original, copia_]))

    def test_copia_con_otra_procedencia_o_sin_original(self):
        original = registro()
        copia_ = registro(documento_id=11, copia_de=10, procedencia={"revision": "nombre del fichero"})
        self.assertTrue(pc.comprobar_copias([original, copia_]))
        self.assertTrue(pc.comprobar_copias([registro(documento_id=11, copia_de=99)]))


class ContraBiblioteca(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.execute("CREATE TABLE documento (id INTEGER, ruta TEXT, sha256 TEXT, codigo TEXT, duplicado_de INTEGER,"
                         " ext TEXT, estado TEXT, carpeta_norm TEXT)")
        self.con.executemany("INSERT INTO documento VALUES (?,?,?,?,?,?,?,?)", [
            (10, "3- Paredes muy Delgadas/3233/1- 2D y 3D pieza/x.pdf", SHA, "3233", None, "pdf", "extraido", "pieza_2d3d"),
            (11, "3- Paredes muy Delgadas/3233/6- Método/y_DRW.pdf", SHA, "3233", 10, "pdf", "duplicado", "metodo"),
            (12, "3- Paredes muy Delgadas/3233/4- Metrologia/z.pdf", "b" * 64, "3233", None, "pdf", "extraido", "metrologia"),
        ])

    def test_catalogo_completo(self):
        copia_ = registro(documento_id=11, ruta="3- Paredes muy Delgadas/3233/6- Método/y_DRW.pdf", copia_de=10,
                          verificacion="copia idéntica de 10")
        self.assertEqual(pc.comprobar_catalogo(self.con, [registro(), copia_]), [])

    def test_falta_un_pdf_y_sha_distinto(self):
        problemas = pc.comprobar_catalogo(self.con, [registro(sha256="c" * 64)])
        self.assertTrue(any("SHA-256" in p for p in problemas))
        self.assertTrue(any("no está en el catálogo" in p for p in problemas))

    def test_copia_mal_declarada(self):
        copia_ = registro(documento_id=11, ruta="3- Paredes muy Delgadas/3233/6- Método/y_DRW.pdf")
        self.assertTrue(any("duplicado_de" in p for p in pc.comprobar_catalogo(self.con, [registro(), copia_])))


class Cabecera(unittest.TestCase):
    def test_celda_del_valor(self):
        filas = {6: {7: "Drawing nº:", 9: "BSG-296-00", 27: "Drawing nº Level:", 28: "1"}}
        self.assertEqual(pc.celda_de_campo(filas, pc.ETIQUETAS["drawing_no"]), "I6")
        self.assertEqual(pc.celda_de_campo(filas, pc.ETIQUETAS["drawing_level"]), "AB6")

    def test_campo_vacio_seguido_de_otra_etiqueta(self):
        filas = {6: {1: "PPAP Ref.:", 3: "Nº Plano:", 5: "11206"}}
        self.assertIsNone(pc.celda_de_campo(filas, pc.ETIQUETAS["ppap_ref"]))

    def test_sustituir_bloques(self):
        texto = "a\n<!-- planos-resumen:inicio -->\n<!-- planos-resumen:fin -->\nb\n"
        uno = pc.sustituir(texto, {"resumen": "| x |"})
        self.assertEqual(uno, "a\n<!-- planos-resumen:inicio -->\n| x |\n<!-- planos-resumen:fin -->\nb\n")
        self.assertEqual(pc.sustituir(uno, {"resumen": "| y |"}).count("| y |"), 1)

    def test_tabla_de_cabeceras_conserva_el_rango_sin_fecha(self):
        base = dict(pieza="3237", ruta="3- Paredes muy Delgadas/3237/4- Metrologia/a.xls", plano="3130589019", revision="03",
                    celda_plano="I6", celda_revision="M6")
        hojas = [dict(base, hoja="DR", fecha_literal="13/02/2024 -10/04/2024", fecha=None),
                 dict(base, hoja="DR2", fecha_literal="2024-04-16T00:00:00", fecha="2024-04-16")]
        tabla = pc.tabla_cabeceras(copy.deepcopy(hojas))
        self.assertIn("2024-04-16 (1 sin fecha válida)", tabla)


if __name__ == "__main__":
    unittest.main()
