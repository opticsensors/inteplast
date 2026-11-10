"""Extractor de .icp (globos_icp.py) con registros sintéticos de la misma estructura. Sin ficheros del cliente.

    python -B -m unittest discover -s conocimiento/herramientas -p "test_globos_icp.py"
"""

import re
import sqlite3
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import globos_icp  # noqa: E402

GUID = "3F34ABB7-52B6-4E1F-8937-49457C6C8EB7"


def cadena(texto: bytes) -> bytes:
    return struct.pack("<I", len(texto)) + texto


def registro(numero: int, x1: float, y1: float, x2: float, y2: float, indice: int, texto: str | None = None) -> bytes:
    """Un sello como en los .icp de infra-CONVERT: texto, nombre, dos puntos, estilo, índice y GUID."""
    return (b"\x00\x00\xf4?" + cadena((texto or str(numero)).encode()) + cadena(b"INFRA_CONVERT_STAMP_%d" % numero)
            + struct.pack("<6d", x1, y1, 0., x2, y2, 0.) + b"\x01\x00\x00\x00" + cadena(b"ELIASEMPTY")
            + b"\xff\xff\xff\xff" + struct.pack("<i", indice) + b"\x24\x00\x00\x00" + GUID.encode() + b"\x00" * 16)


def con_primer_byte(valor: float, byte: int) -> float:
    """El mismo número con el primer byte (el menos significativo) cambiado: apenas cambia el valor."""
    return struct.unpack("<d", bytes([byte]) + struct.pack("<d", valor)[1:])[0]


class ExtractorTests(unittest.TestCase):
    def test_una_cifra_de_la_coordenada_no_se_suma_al_numero(self):
        x1 = con_primer_byte(-58.374, ord("7"))  # el primer byte de la coordenada es «7»
        data = b"cabecera" + registro(128, x1, 83.9, -58.3, 72.3, 17) + registro(30, 1., 2., 3., 4., 18)
        # La expresión de antes leía 1287 y las coordenadas con un byte de desfase.
        self.assertEqual(re.search(rb"INFRA_CONVERT_STAMP_(\d+)", data).group(1), b"1287")
        sellos = globos_icp.leer_icp(data)
        self.assertEqual([(g["sello"], g["texto"]) for g in sellos], [(128, "128"), (30, "30")])
        self.assertEqual((sellos[0]["x1"], sellos[0]["y1"], sellos[0]["indice"], sellos[0]["guid"]), (x1, 83.9, 17, GUID))

    def test_el_numero_es_el_del_icp_y_el_prf_solo_se_contrasta(self):
        # El .prf se salta las filas 17 y 18: con «fila = índice − 1» el sello 70 recibiría el 45.
        data = registro(70, -58.4, 83.9, -58.4, 72.3, 17) + registro(45, -123.9, 164.1, -120., 160., 19)
        prf = globos_icp.leer_prf("16\t1\t-1\t\t\t\t\t\t\t45\n19\t1\t-1\t\t\t\t\t\t\t50\n")
        filas = globos_icp.filas(7, globos_icp.leer_icp(data), prf)
        self.assertEqual([(f[1], f[8], f[9]) for f in filas], [(70, "70", "45"), (45, "45", None)])

    def test_sin_prf_todos_los_sellos_conservan_su_numero(self):
        filas = globos_icp.filas(7, globos_icp.leer_icp(registro(12, 1., 2., 3., 4., 2)), {})
        self.assertEqual([(f[8], f[9]) for f in filas], [("12", None)])

    def test_un_formato_inesperado_se_avisa_en_vez_de_descartar(self):
        sin_texto = cadena(b"INFRA_CONVERT_STAMP_5") + struct.pack("<6d", 1., 2., 0., 3., 4., 0.) + b"\x00" * 120
        with self.assertRaises(globos_icp.FormatoICP):
            globos_icp.leer_icp(b"\x00" * 8 + sin_texto)
        with self.assertRaises(globos_icp.FormatoICP):  # dos sellos con el mismo número: no se pisa uno
            globos_icp.leer_icp(registro(5, 1., 2., 3., 4., 2) + registro(5, 5., 6., 7., 8., 3))
        with self.assertRaises(globos_icp.FormatoICP):  # coordenadas absurdas: el registro no es lo que parece
            globos_icp.leer_icp(registro(6, 1e9, 2., 3., 4., 2))


ANTERIOR = (1, 12, 1., 2., 3., 4., 2, GUID, "12", "12")


class RegeneracionTests(unittest.TestCase):
    """Si falla cualquier fichero o la escritura, la tabla `globo` anterior queda intacta."""

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.raiz = Path(carpeta.name)
        parche = mock.patch.object(globos_icp, "original", lambda ruta: self.raiz / ruta)
        parche.start()
        self.addCleanup(parche.stop)
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.execute("CREATE TABLE documento (id INTEGER PRIMARY KEY, ruta TEXT, ext TEXT, estado TEXT)")
        self.con.executemany("INSERT INTO documento VALUES (?,?,'icp','extraido')", [(1, "a.icp"), (2, "b.icp")])
        self.con.commit()
        globos_icp.sustituir(self.con, [ANTERIOR])

    def tabla(self):
        return self.con.execute("SELECT * FROM globo ORDER BY documento_id, sello").fetchall()

    def test_un_icp_que_falla_no_borra_la_tabla_anterior(self):
        (self.raiz / "a.icp").write_bytes(registro(30, 1., 2., 3., 4., 2))  # el primero se lee bien
        (self.raiz / "b.icp").write_bytes(registro(5, 1., 2., 3., 4., 2) + registro(5, 5., 6., 7., 8., 3))
        with self.assertRaises(globos_icp.FormatoICP) as error:
            globos_icp.regenerar(self.con)
        self.assertIn("en b.icp", error.exception.__notes__)
        self.assertEqual(self.tabla(), [ANTERIOR])

    def test_un_icp_que_no_se_puede_leer_no_borra_la_tabla_anterior(self):
        (self.raiz / "a.icp").write_bytes(registro(30, 1., 2., 3., 4., 2))  # b.icp no existe
        with self.assertRaises(OSError):
            globos_icp.regenerar(self.con)
        self.assertEqual(self.tabla(), [ANTERIOR])

    def test_un_fallo_al_escribir_deshace_tambien_el_borrado(self):
        nueva = (2, 30, 1., 2., 3., 4., 2, GUID, "30", None)
        with self.assertRaises(sqlite3.IntegrityError):  # la segunda fila repite la clave
            globos_icp.sustituir(self.con, [nueva, nueva])
        self.assertEqual(self.tabla(), [ANTERIOR])
        self.assertFalse(self.con.in_transaction)

    def test_si_todo_se_lee_la_tabla_se_sustituye_entera(self):
        (self.raiz / "a.icp").write_bytes(registro(30, 1., 2., 3., 4., 2))
        (self.raiz / "b.icp").write_bytes(registro(7, 5., 6., 7., 8., 3))
        globos_icp.regenerar(self.con)
        self.assertEqual([(f[0], f[1], f[8]) for f in self.tabla()], [(1, 30, "30"), (2, 7, "7")])


if __name__ == "__main__":
    unittest.main()
