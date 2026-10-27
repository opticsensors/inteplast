"""Pruebas del RAG: fixtures temporales y embeddings simulados; nunca la biblioteca real ni Exemples.

    conocimiento/.venv/Scripts/python.exe -B -m unittest discover -s conocimiento/herramientas -p "test_*.py"
"""

import hashlib
import io
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stderr
from pathlib import Path

import numpy as np

import rag
import rag_fuentes as rf
from lector_dr import ESQUEMA as ESQUEMA_DR

AQUI = Path(__file__).resolve().parent
FILAS_TABLA = "\n".join(f"| fila {i} con texto suficiente para ocupar espacio en la tabla de ejemplo | valor {i} |" for i in range(40))
FICHA_3212 = f"""# 3212 Pump Housing

Texto inicial sobre el bolt eye: la cota N170 del muestreo intern.06 se lee en la hoja DR(SKETCH).

## Metrologia

| Col A | Col B |
|---|---|
{FILAS_TABLA}

## Pendiente

- ~~Errores de lectura~~: resueltos.

```
# no es encabezado
```

Cierre de la seccion pendiente con una frase final.
"""


INSERTAR_DOC = ("INSERT INTO documento(id, ruta, feature, pieza, codigo, carpeta_norm, nombre, ext, estado, lector, duplicado_de, "
                "sha256, tamano, mtime_ns, inventariado_el) VALUES (?,?,'0- Bolt Eye',?,?,?,?,?,?,?,?,?,1000,1,'2026-10-26')")


class Falso:
    """Bolsa de palabras con hash estable: reproducible y suficiente para ordenar por solapamiento."""

    def __init__(self, digest="d1", disponible=True):
        self.digest, self.disponible = digest, disponible
        self.fallar_tras = None
        self.llamadas = 0
        self.al_embeber = None

    def identidad(self):
        if not self.disponible:
            raise rag.EmbeddingsNoDisponibles("proveedor apagado (simulado)")
        return {"proveedor": "falso", "modelo": "bolsa", "digest": self.digest, "dimensiones": 64, "contexto": 2048}

    def embed(self, textos):
        if not self.disponible or (self.fallar_tras is not None and self.llamadas >= self.fallar_tras):
            raise rag.EmbeddingsNoDisponibles("caida simulada")
        self.llamadas += 1
        if self.al_embeber:
            self.al_embeber()
        salida = []
        for t in textos:
            v = np.full(64, 1e-3)
            for palabra in re.findall(r"\w+", t.lower()):
                if palabra not in ("title", "text", "none", "task", "search", "result", "query"):
                    v[int(hashlib.md5(palabra.encode()).hexdigest(), 16) % 64] += 1
            salida.append(v.tolist())
        return salida


def crear_biblioteca(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con:
        con.executescript((AQUI / "esquema.sql").read_text(encoding="utf-8"))
        con.executescript(ESQUEMA_DR)
        con.executescript("""
            CREATE TABLE perfil_ppap (documento_id INTEGER, hoja TEXT, feature TEXT, pieza TEXT, ruta TEXT, fila_cabecera INTEGER,
              metadatos TEXT, cavidades TEXT, col_nominal INTEGER, col_equipo INTEGER, col_nok INTEGER, filas_cota INTEGER,
              items TEXT, equipos TEXT, nok INTEGER, ceros INTEGER, vacias INTEGER);
            CREATE TABLE celda_aleatoria (documento_id INTEGER, hoja TEXT, fila INTEGER, col INTEGER, formula TEXT, valor TEXT);
        """)
        base = "0- Bolt Eye/3212 Pump Housing/"
        docs = [
            (1, base + "5- Retoques/correccion.pdf", "3212 Pump Housing", "3212", "retoques", "correccion.pdf", "pdf", "extraido", "pdf", None, "a" * 64),
            (2, "0- Bolt Eye/3051 Pump Housing/5- Retoques/correccion.pdf", "3051 Pump Housing", "3051", "retoques", "correccion.pdf", "pdf", "duplicado", None, 1, "a" * 64),
            (3, base + "4- Metrologia/3212_intern.06.xls", "3212 Pump Housing", "3212", "metrologia", "3212_intern.06.xls", "xls", "extraido", "xls", None, "b" * 64),
            (4, base + "1- 2D y 3D/pieza.stp", "3212 Pump Housing", "3212", "pieza_2d3d", "pieza.stp", "stp", "extraido", "step", None, "c" * 64),
            (5, base + "1- 2D y 3D/foto.jpg", "3212 Pump Housing", "3212", "pieza_2d3d", "foto.jpg", "jpg", "solo_metadatos", "imagen", None, "d" * 64),
            (6, base + "4- Metrologia/cav13.csv", "3212 Pump Housing", "3212", "metrologia", "cav13.csv", "csv", "extraido", "csv", None, "e" * 64),
        ]
        for d in docs:
            con.execute(INSERTAR_DOC, d)
        elementos = [
            (1, "pagina", "pagina 1", 1, "Plan de correccion del molde: ampliar el diametro del bolt eye N170 en la cavidad 13 con un postizo nuevo."),
            (1, "pagina", "pagina 2", 2, "123 456 789 0,1 0,2"),
            (3, "fila", "DR(SKETCH)!13", 1, "A13=Nr | D13=Nominal | H13=Cav.1"),
            (6, "fila", "csv!5", 1, "A5=N170 | B5=GX | C5=3.974"),
            (4, "productos", "productos", 1, "Pump housing insert"),
            (4, "cabecera", "cabecera", 2, "ISO-10303-21 HEADER FILE_NAME pieza"),
        ]
        con.executemany("INSERT INTO elemento(documento_id, tipo, localizador, orden, texto) VALUES (?,?,?,?,?)", elementos)
        estructura = [
            (3, "hojas", json.dumps([{"nombre": "DR(SKETCH)", "filas": 16, "columnas": 9, "celdas": 12}])),
            (3, "formulas", json.dumps("no disponibles en XLS BIFF")),
            (4, "entidades_total", "120"), (4, "entidades", json.dumps({"ADVANCED_FACE": 20})),
            (4, "caja", json.dumps({"min": [0, 0, 0], "max": [10, 20, 30], "dimensiones": [10, 20, 30], "base": "vertices"})),
            (4, "esquema", json.dumps("AP214")), (4, "unidades", json.dumps("mm")), (4, "sistema_origen", json.dumps("CATIA")),
            (5, "formato", json.dumps("JPEG")), (5, "ancho", "1600"), (5, "alto", "1200"),
            (6, "delimitador", json.dumps(";")), (6, "columnas_max", "12"),
        ]
        con.executemany("INSERT INTO estructura VALUES (?,?,?)", estructura)
        h = "DR(SKETCH)"
        celdas = [(3, h, 13, 1, "Nr", None), (3, h, 13, 4, "Nominal", None), (3, h, 13, 8, "Cav.1", None), (3, h, 13, 9, "Cav.2", None),
                  (3, h, 14, 1, "N170", None), (3, h, 14, 4, "4", 4.0), (3, h, 14, 8, "3.97", 3.97), (3, h, 14, 9, "0", 0.0),
                  (3, h, 15, 1, "N171", None), (3, h, 15, 8, None, None),
                  (3, h, 16, 1, "N172", None), (3, h, 16, 8, "5.01", 5.01)]
        con.executemany("INSERT INTO celda(documento_id, hoja, fila, col, valor, numero) VALUES (?,?,?,?,?,?)", celdas)
        con.execute("INSERT INTO celda_aleatoria VALUES (3, ?, 16, 8, '=RAND()*0.1+5', '5.01')", (h,))
        con.execute("INSERT INTO lectura_dr VALUES (3, ?, 'interna', 'con_correccion', 13, '{\"codigo\": 1}', '[\"c1\", \"c2\"]', 2, 3, 1, "
                    "'{\"tolerancias en orden inverso (corregidas)\": 1}', 1, 1, 0, '[0,0,0,0]', '{}', '{}')", (h,))
        con.executemany("INSERT INTO medida_dr VALUES (3, ?, ?, ?, ?, ?, ?, ?, 'CMM', ?, ?, ?)", [
            (h, 14, 8, "170", 4.0, 0.0, -0.1, "c1", 3.97, None), (h, 14, 9, "170", 4.0, 0.0, -0.1, "c2", 0.0, "cero"),
            (h, 16, 8, "172", 5.0, 0.1, -0.1, "c1", 5.01, "aleatoria")])
        con.execute("INSERT INTO perfil_ppap VALUES (3, ?, '0- Bolt Eye', '3212 Pump Housing', 'x', 13, ?, '[\"Cav.1\", \"Cav.2\"]', "
                    "4, 7, NULL, 3, '[]', '{\"CMM\": 3}', 0, 1, 0)", (h, json.dumps({"drawing_level": "07", "part_name": "PUMP"})))
        con.execute("INSERT INTO ejecucion(herramienta, inicio) VALUES ('fixture', '2026-10-26')")
        con.commit()


def escribir(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="inteplast-rag-")
        self.addCleanup(self.tmp.cleanup)
        raiz = Path(self.tmp.name)
        escribir(raiz / "conocimiento/README.md", "# Conocimiento\n\nEntrada general de la base de conocimiento de prueba.\n")
        escribir(raiz / "conocimiento/0-bolt-eye/3212/README.md", FICHA_3212)
        escribir(raiz / "conocimiento/AVANCE.md", "# Avance\n\n## Sesion antigua\n\nCobertura antigua del cincuenta por ciento.\n")
        escribir(raiz / "conocimiento/rag.md", "# RAG local\n\nReferencia de la herramienta: no es conocimiento de los datos.\n")
        escribir(raiz / "conocimiento/datos/notas.md", "# Artefacto\n\nNo debe indexarse.\n")
        hallazgos = [
            {"id": "I-003", "fecha": "2026-10-21", "feature": "*", "pieza": "3212", "tipo": "incongruencia", "relevancia": "alta",
             "estado": "abierta", "afirmacion": "Celdas con formulas aleatorias RAND en libros de medicion.",
             "evidencia": [{"ruta": "0- Bolt Eye/3212 Pump Housing/4- Metrologia/3212_intern.06.xls", "sha256": "b" * 64,
                            "localizador": "DR(SKETCH)!H16"}],
             "comprobacion": {"sql": "SELECT count(*) FROM celda_aleatoria", "esperado": [1]}},
            {"id": "H-001", "fecha": "2026-10-21", "feature": "0- Bolt Eye", "pieza": "3212,3197", "tipo": "leccion",
             "relevancia": "alta", "estado": "extraido", "afirmacion": "El diametro del bolt eye queda por debajo del objetivo.",
             "evidencia": []},
        ]
        escribir(raiz / "conocimiento/hallazgos.jsonl", "\n".join(json.dumps(h, ensure_ascii=False) for h in hallazgos) + "\n")
        escribir(raiz / "docs/README.md", "# Docs\n\n| Necesidad | Documento de referencia | Estado que describe |\n|---|---|---|\n"
                 "| Entender la app | [Aplicación web](app-web.md) | Implementado en el código |\n\n## Historial\n\n"
                 "- [Revisión del 26/10/2026](revision-2026-10-26.md): registro.\n")
        escribir(raiz / "docs/app-web.md", "# Aplicación\n\nEl backend FastAPI expone el catalogo de features.\n")
        escribir(raiz / "docs/revision-2026-10-26.md", "# Revisión\n\nTexto historico de una revision anterior.\n")
        self.raiz = raiz
        self.rutas = rag.Rutas(raiz=raiz, biblioteca=raiz / "conocimiento/datos/biblioteca.sqlite", rag=raiz / "conocimiento/datos/rag")
        crear_biblioteca(self.rutas.biblioteca)
        self.huella_biblioteca = sha_bytes(self.rutas.biblioteca)
        self.addCleanup(lambda: self.assertEqual(sha_bytes(self.rutas.biblioteca), self.huella_biblioteca,
                                                 "la biblioteca se modifico"))
        self.falso = Falso()

    def construir(self, **opciones):
        return rag.construir(self.rutas, self.falso, avisar=lambda *_: None, **opciones)

    def buscar(self, consulta, embedder=None, **opciones):
        filtros = rag.Filtros(**{k: opciones.pop(k) for k in list(opciones) if k in vars(rag.Filtros())})
        return rag.buscar(self.rutas, consulta, filtros=filtros, embedder=embedder or self.falso, **opciones)

    def recolectar(self):
        with closing(rag.abrir_biblioteca(self.rutas.biblioteca)) as bib:
            return rag.recolectar(self.rutas, bib)[0]

    def fragmentos_biblioteca(self):
        with closing(rag.abrir_biblioteca(self.rutas.biblioteca)) as bib:
            return {f.clave: f for f in rf.fuentes_biblioteca(bib)}

    def modificar_biblioteca(self, *sentencias):
        """Simula una actualizacion de la biblioteca (la hace la prueba, nunca el RAG) y renueva la huella de control."""
        with closing(sqlite3.connect(self.rutas.biblioteca)) as bib:
            for s in sentencias:
                sql, *parametros = s if isinstance(s, tuple) else (s,)
                bib.execute(sql, *parametros)
            bib.commit()
        self.huella_biblioteca = sha_bytes(self.rutas.biblioteca)

    # --- Segmentacion y procedencia ---

    def test_segmentacion_markdown_conserva_procedencia(self):
        fragmentos = rf.fuentes_markdown(self.raiz, {"0": "0- Bolt Eye"})
        claves = [f.clave for f in fragmentos]
        self.assertEqual(len(claves), len(set(claves)))
        self.assertFalse({"conocimiento/rag.md", "conocimiento/datos/notas.md"} & {f.ruta for f in fragmentos},
                         "ni la referencia del RAG ni datos/ se indexan")
        ficha = [f for f in fragmentos if f.ruta == "conocimiento/0-bolt-eye/3212/README.md"]
        lineas = FICHA_3212.splitlines()
        tablas = [f for f in ficha if f.seccion == "Metrologia"]
        self.assertGreater(len(tablas), 1, "la tabla larga debe partirse")
        for f in tablas:
            self.assertTrue(f.contenido.startswith("| Col A | Col B |\n|---|---|"), "cada parte conserva la cabecera")
            self.assertLessEqual(len(f.contenido), rf.LIMITE)
        for f in ficha:
            self.assertEqual((f.feature, f.codigos, f.vigencia, f.coleccion), ("0- Bolt Eye", ("3212",), "vigente", "conocimiento"))
            a, b = map(int, re.search(r"lineas (\d+)-(\d+)", f.localizador).groups())
            ultima = f.contenido.splitlines()[-1]
            self.assertIn(ultima, lineas[b - 1], f"el localizador {f.localizador} apunta a las lineas reales")
        self.assertFalse(any("no es encabezado" in (f.seccion or "") for f in ficha), "un # dentro de codigo no es encabezado")
        retirado = [f for f in ficha if f.retirado]
        self.assertEqual(len(retirado), 1)
        self.assertIn("[RETIRADO: Errores de lectura]", retirado[0].contenido)
        avance = [f for f in fragmentos if f.ruta == "conocimiento/AVANCE.md"]
        self.assertTrue(avance and all(f.coleccion == "historial" and f.vigencia == "historial" for f in avance))
        docs = {f.ruta: f for f in fragmentos if f.coleccion == "docs"}
        self.assertEqual(docs["docs/revision-2026-10-26.md"].vigencia, "historial")
        self.assertEqual(docs["docs/app-web.md"].estado_doc, "Implementado en el código")
        self.assertEqual(docs["docs/app-web.md"].naturaleza, "aplicacion")

    def test_biblioteca_metadatos_duplicados_cad_e_inventario(self):
        with closing(rag.abrir_biblioteca(self.rutas.biblioteca)) as bib:
            fragmentos = {f.clave: f for f in rf.fuentes_biblioteca(bib)}
            pagina = bib.execute("SELECT id FROM elemento WHERE localizador='pagina 1'").fetchone()[0]
        p = fragmentos[f"bib:e{pagina}"]
        self.assertEqual((p.documento_id, p.codigos, p.localizador, p.sha256_original, p.raiz),
                         (1, ("3212",), "pagina 1", "a" * 64, "exemples"))
        dup = fragmentos[f"bib:e{pagina}@d2"]
        self.assertEqual((dup.documento_id, dup.codigos, dup.contenido), (2, ("3051",), p.contenido))
        self.assertEqual(dup.duplicado_de, "0- Bolt Eye/3212 Pump Housing/5- Retoques/correccion.pdf")
        numerica = fragmentos[f"bib:e{pagina + 1}"]
        self.assertFalse(numerica.embeber)
        self.assertIn("poco texto", numerica.motivo_lexico)
        cad = fragmentos["cad:4"]
        self.assertIn("Caja", cad.contenido)
        self.assertIn("VERTEX_POINT", cad.contenido)
        self.assertIn("Pump housing insert", cad.contenido)
        self.assertFalse(any(f.documento_id == 4 and f.coleccion == "biblioteca" for f in fragmentos.values()),
                         "productos y cabecera del STEP van en la tarjeta CAD")
        hoja = fragmentos["hoja:3:DR(SKETCH)"]
        self.assertEqual(hoja.revision, "07")
        self.assertIn("drawing_level", hoja.revision_origen)
        self.assertIn("Nr | Nominal | Cav.1 | Cav.2", hoja.contenido)
        self.assertEqual(fragmentos["libro:3"].revision, "07")
        self.assertIn("libro:6", fragmentos, "el CSV tiene tarjeta de contexto")
        self.assertFalse(fragmentos["doc:5"].embeber)
        self.assertNotIn("doc:6", fragmentos)
        self.assertFalse(any(f.tipo_fuente == "elemento:fila" for f in fragmentos.values()))

    # --- Construccion ---

    def test_construccion_idempotente_y_reutiliza_embeddings(self):
        primero = self.construir()
        self.assertEqual(primero["resultado"], "ok")
        self.assertGreater(primero["embeddings"]["nuevos"], 0)
        mtime = self.rutas.indice.stat().st_mtime_ns
        self.assertEqual(self.construir()["resultado"], "sin_cambios")
        self.assertEqual(self.rutas.indice.stat().st_mtime_ns, mtime)
        with closing(rag.abrir_indice(self.rutas)) as con:
            claves = {r[0] for r in con.execute("SELECT clave FROM aparicion")}
        forzado = self.construir(forzar=True)
        self.assertEqual(forzado["embeddings"], {"nuevos": 0, "reutilizados": primero["embeddings"]["nuevos"]})
        with closing(rag.abrir_indice(self.rutas)) as con:
            self.assertEqual({r[0] for r in con.execute("SELECT clave FROM aparicion")}, claves)
            self.assertEqual(con.execute("SELECT count(*) FROM texto WHERE embeber=1 AND vector IS NULL").fetchone()[0], 0)

    def test_cambios_y_bajas_no_dejan_resultados_obsoletos(self):
        total = self.construir()["embeddings"]["nuevos"]
        ficha = self.raiz / "conocimiento/0-bolt-eye/3212/README.md"
        escribir(ficha, FICHA_3212.replace("Cierre de la seccion pendiente", "Nueva conclusion sobre el escariado del bolt eye. Cierre"))
        (self.raiz / "docs/app-web.md").unlink()
        segundo = self.construir()
        self.assertGreaterEqual(segundo["embeddings"]["nuevos"], 1)
        self.assertLess(segundo["embeddings"]["nuevos"], total)
        with closing(rag.abrir_indice(self.rutas)) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM aparicion WHERE ruta='docs/app-web.md'").fetchone()[0], 0)
        r = self.buscar("FastAPI catalogo", modo="lexico")
        self.assertFalse(any(x.get("ruta") == "docs/app-web.md" for x in r["resultados"]))
        r = self.buscar("escariado", modo="lexico")
        self.assertTrue(any("escariado" in x["extracto"] for x in r["resultados"]))

    def test_fallo_conserva_indice_cache_y_registro(self):
        self.construir()
        huella = sha_bytes(self.rutas.indice)
        for i in range(3):
            escribir(self.raiz / f"conocimiento/nueva-{i}.md", f"# Nueva {i}\n\nContenido distinto numero {i} sobre rebabas.\n")
        self.falso.fallar_tras = self.falso.llamadas + 1
        with self.assertRaises(rag.EmbeddingsNoDisponibles):
            self.construir(lote=1)
        self.assertEqual(sha_bytes(self.rutas.indice), huella, "el indice anterior sigue intacto")
        self.assertEqual(list(self.rutas.rag.glob("*.tmp*")), [])
        self.assertFalse(self.rutas.cerrojo.exists())
        ultimo = json.loads(self.rutas.registro.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(ultimo["resultado"], "error")
        self.assertIn("caida simulada", ultimo["error"])
        self.falso.fallar_tras = None
        reanudado = self.construir(lote=1)
        self.assertEqual(reanudado["resultado"], "ok")
        self.assertEqual(reanudado["embeddings"]["nuevos"], 2, "el vector calculado antes del fallo se reutiliza")

    def test_fuentes_cambiadas_durante_la_construccion(self):
        ficha = self.raiz / "conocimiento/README.md"
        self.falso.al_embeber = lambda: escribir(ficha, "# Conocimiento\n\nTexto cambiado durante la construccion.\n")
        with self.assertRaises(rag.FuentesCambiadas):
            self.construir()
        self.assertFalse(self.rutas.indice.exists())
        self.assertEqual(json.loads(self.rutas.registro.read_text(encoding="utf-8").splitlines()[-1])["resultado"], "error")

    def test_cerrojo_excluye_y_recupera_huerfanos(self):
        self.rutas.rag.mkdir(parents=True)
        self.rutas.cerrojo.write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname()}), encoding="utf-8")
        with self.assertRaises(rag.ConstruccionEnCurso):
            self.construir()
        terminado = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        self.rutas.cerrojo.write_text(json.dumps({"pid": int(terminado.stdout), "host": socket.gethostname()}), encoding="utf-8")
        self.assertEqual(self.construir()["resultado"], "ok")
        self.assertFalse(self.rutas.cerrojo.exists())

    # --- Busqueda ---

    def test_identificadores_exactos_y_filtros(self):
        self.construir()
        r = self.buscar("I-003")
        self.assertEqual(r["modo_efectivo"], "hibrido")
        self.assertEqual(r["resultados"][0]["id"], "hallazgo:I-003")
        self.assertEqual(r["resultados"][0]["estado_hallazgo"], "abierta")
        for consulta in ("DR(SKETCH)", "intern.06"):
            ids = [x["id"] for x in self.buscar(consulta)["resultados"]]
            self.assertTrue(any(i.startswith("md:conocimiento/0-bolt-eye/3212/README.md") for i in ids[:5]), (consulta, ids))
        sin_pieza = self.buscar("N170")
        self.assertIn("cota_local", [a["codigo"] for a in sin_pieza["avisos"]])
        con_pieza = self.buscar("N170", pieza="3212")
        self.assertNotIn("cota_local", [a["codigo"] for a in con_pieza["avisos"]])
        self.assertTrue(all("3212" in x["codigos"] for x in con_pieza["resultados"]))
        self.assertIn("bib:e4", [x["id"] for x in con_pieza["resultados"]], "fila literal delegada del CSV")
        dup = self.buscar("postizo diametro bolt eye", pieza="3051")
        self.assertTrue(dup["resultados"] and all(x["id"].endswith("@d2") for x in dup["resultados"]),
                        "un duplicado se encuentra filtrando por su propia pieza")
        solo_docs = self.buscar("features catalogo", colecciones=["docs"])
        self.assertTrue(solo_docs["resultados"] and all(x["coleccion"] == "docs" for x in solo_docs["resultados"]))
        vigente = self.buscar("cobertura antigua", vigencia=["vigente"])
        self.assertFalse(any(x.get("vigencia") == "historial" for x in vigente["resultados"]))
        transversal = self.buscar("formulas aleatorias", feature="0")
        self.assertIn("hallazgo:I-003", [x["id"] for x in transversal["resultados"]], "feature '*' entra en cualquier feature")
        vacio = self.buscar("bolt eye", pieza="9999")
        self.assertIn("filtros_sin_fuentes", [a["codigo"] for a in vacio["avisos"]])
        self.assertIn("sin_resultados", [a["codigo"] for a in vacio["avisos"]])

    def test_fusion_sin_duplicados_conserva_apariciones(self):
        self.construir()
        r = self.buscar("postizo diametro bolt eye cavidad", n=20)
        ids = [x["id"] for x in r["resultados"]]
        self.assertEqual(len(ids), len(set(ids)))
        pagina = [x for x in r["resultados"] if "postizo" in x.get("extracto", "")]
        self.assertEqual(len(pagina), 1, "el texto identico del original y su duplicado sale una vez")
        self.assertEqual(pagina[0]["total_otras_apariciones"], 1)
        self.assertEqual(pagina[0]["otras_apariciones"][0]["codigos"], ["3051"])
        self.assertFalse(r["completo"])

    def test_sin_embeddings_y_modelo_distinto(self):
        self.falso.disponible = False
        with self.assertRaises(rag.EmbeddingsNoDisponibles):
            self.construir()
        self.assertEqual(self.construir(solo_lexico=True)["resultado"], "ok")
        r = self.buscar("bolt eye")
        self.assertEqual(r["modo_efectivo"], "lexico")
        self.assertIn("embeddings_no_disponibles", [a["codigo"] for a in r["avisos"]])
        self.assertIn("SOLO lexico", next(a["mensaje"] for a in r["avisos"] if a["codigo"] == "embeddings_no_disponibles"))
        semantico = self.buscar("bolt eye", modo="semantico")
        self.assertEqual((semantico["resultados"], semantico["modo_efectivo"]), ([], None))
        self.assertGreater(rag.estado(self.rutas, self.falso)["textos_sin_vector"], 0)
        self.falso.disponible = True
        self.assertEqual(self.construir()["resultado"], "ok")
        self.assertEqual(self.buscar("bolt eye")["modo_efectivo"], "hibrido")
        apagado = self.buscar("bolt eye", embedder=Falso(disponible=False))
        self.assertEqual(apagado["modo_efectivo"], "lexico")
        otro = self.buscar("bolt eye", embedder=Falso(digest="d2"))
        self.assertEqual(otro["modo_efectivo"], "lexico")
        self.assertIn("no coincide", next(a["mensaje"] for a in otro["avisos"] if a["codigo"] == "embeddings_no_disponibles"))

    def test_desactualizacion_visible(self):
        self.construir()
        self.assertEqual(rag.estado(self.rutas, self.falso)["frescura"]["estado"], "ok")
        os.utime(self.rutas.biblioteca, ns=(1, 1))   # solo la fecha: misma firma
        self.assertEqual(self.buscar("bolt eye")["indice"]["frescura"]["estado"], "posiblemente_desactualizado")
        self.assertEqual(rag.estado(self.rutas, self.falso, verificar=True)["frescura"]["estado"], "ok")
        escribir(self.raiz / "conocimiento/README.md", "# Conocimiento\n\nOtro texto.\n")
        r = self.buscar("bolt eye")
        self.assertIn("indice_desactualizado", [a["codigo"] for a in r["avisos"]])

    def test_ver_amplia_contexto(self):
        self.construir()
        clave = next(x["id"] for x in self.buscar("Metrologia Col A", colecciones=["conocimiento"])["resultados"]
                     if "Col A" in x["extracto"])
        visto = rag.ver(self.rutas, clave, contexto=1)
        self.assertTrue(visto["contenido"].startswith("| Col A"))
        self.assertTrue(visto["contexto"] and all(c["id"] != clave for c in visto["contexto"]))
        with closing(sqlite3.connect(self.rutas.biblioteca)) as bib:
            pagina = bib.execute("SELECT id FROM elemento WHERE localizador='pagina 1'").fetchone()[0]
        visto = rag.ver(self.rutas, f"bib:e{pagina}", contexto=1)
        self.assertEqual([c["posicion"] for c in visto["contexto"]], ["resultado", "despues"])

    # --- Acceso exacto ---

    def test_exacto_es_de_solo_lectura(self):
        with self.assertRaises(rag.SoloLectura):
            rag.exacto_sql(self.rutas, "DELETE FROM documento")
        with self.assertRaises(rag.SoloLectura):
            rag.exacto_sql(self.rutas, "CREATE TABLE intrusa (x)")
        self.assertEqual(rag.exacto_sql(self.rutas, "SELECT count(*) FROM documento")["filas"], [[6]])
        self.assertEqual(rag.exacto_hallazgo(self.rutas, "I-003", comprobar=True)["comprobacion"]["estado"], "coincide")

    def test_celdas_ausentes_cero_y_formulas(self):
        r = rag.exacto_celdas(self.rutas, "3", hoja="DR(SKETCH)", filas="14-16")
        celdas = {c["celda"]: c for c in r["celdas"]}
        self.assertEqual(celdas["I14"]["estado"], "cero")
        self.assertEqual(celdas["H15"]["estado"], "sin_valor_guardado")
        self.assertTrue(celdas["H16"]["aleatoria"])
        self.assertEqual(celdas["H16"]["formula"], "=RAND()*0.1+5")
        self.assertFalse(r["formulas_disponibles"], "XLS BIFF: formula no disponible, no 'sin formula'")
        self.assertNotIn("I15", celdas, "celda vacia: no se inventa")
        duplicado = rag.exacto_celdas(self.rutas, "2")
        self.assertTrue(any("original identico" in a for a in duplicado["avisos"]))

    def test_medidas_distinguen_derivado_y_clasificacion(self):
        r = rag.exacto_medidas(self.rutas, pieza="3212", cota="N170")
        self.assertEqual(r["alcance"]["total"], 2)
        self.assertIn("170", r["alcance"]["filtros"]["cota"])
        for m in r["medidas"]:
            self.assertEqual(m["clasificacion"], "indeterminada")
            self.assertIn("con_correccion", m["motivo"])
            self.assertTrue(m["origen"].startswith("derivado"))
            self.assertIs(m["celda_original"]["formula_disponible"], False)
        cero = next(m for m in r["medidas"] if m["celda"] == "I14")
        self.assertEqual((cero["valor_lector"], cero["celda_original"]["valor"]), (0.0, "0"))
        self.assertIn("I-002", cero["motivo"])
        self.assertEqual(r["hojas"][0]["ajustes_y_rechazos"], {"tolerancias en orden inverso (corregidas)": 1})
        rand = rag.exacto_medidas(self.rutas, documento="3", cota="N172")["medidas"][0]
        self.assertEqual(rand["clasificacion"], "generada_rand")
        vacio = rag.exacto_medidas(self.rutas, pieza="3212", cota="N999")
        self.assertEqual(vacio["alcance"]["total"], 0)
        self.assertIn("no prueba", vacio["avisos"][0])
        with self.assertRaises(rag.RagError):
            rag.exacto_medidas(self.rutas, cota="N170")

    # --- Regresiones de la revision del 26/10/2026 ---

    def test_documento_ambiguo_exige_referencia_inequivoca(self):
        cliente = "0- Bolt Eye/3212 Pump Housing/4- Metrologia/Customer/3212_intern.06.xls"
        self.modificar_biblioteca(
            (INSERTAR_DOC, (8, cliente, "3212 Pump Housing", "3212", "metrologia", "3212_intern.06.xls", "xls", "extraido", "xls",
                            None, "f" * 64)),
            "INSERT INTO celda(documento_id, hoja, fila, col, valor, numero) VALUES (8, 'DR(SKETCH)', 14, 8, '3.95', 3.95)")
        with self.assertRaises(rag.DocumentoAmbiguo) as caso:
            rag.exacto_celdas(self.rutas, "3212_intern.06.xls")
        self.assertEqual({c["id"] for c in caso.exception.detalle["candidatos"]}, {3, 8})
        with self.assertRaises(rag.DocumentoAmbiguo):
            rag.exacto_medidas(self.rutas, documento="3212_intern.06.xls")
        r = rag.exacto_celdas(self.rutas, "Customer/3212_intern.06.xls", hoja="DR(SKETCH)", filas="14")
        self.assertEqual((r["documento"]["id"], [c["valor"] for c in r["celdas"] if c["celda"] == "H14"]), (8, ["3.95"]))
        r = rag.exacto_celdas(self.rutas, "Exemples\\0- Bolt Eye\\3212 Pump Housing\\4- Metrologia\\3212_intern.06.xls")
        self.assertEqual(r["documento"]["id"], 3)
        with self.assertRaises(rag.RagError, msg="% y _ no son comodines"):
            rag.exacto_celdas(self.rutas, "3212%intern.06.xls")

    def test_documentos_no_vigentes_no_aportan_contenido(self):
        self.construir()
        self.modificar_biblioteca("UPDATE documento SET estado='pendiente' WHERE id=1",
                                  "UPDATE documento SET estado='eliminado' WHERE id=6")
        self.construir()
        with closing(rag.abrir_indice(self.rutas)) as con:
            claves = dict(con.execute("SELECT documento_id, group_concat(clave) FROM aparicion WHERE documento_id IN (1, 2, 6) "
                                      "GROUP BY documento_id"))
            motivos = dict(con.execute("SELECT documento_id, motivo_lexico FROM aparicion WHERE documento_id IN (1, 2)"))
        self.assertEqual(claves, {1: "doc:1", 2: "doc:2"}, "pendiente y su duplicado: solo inventario; eliminado: fuera")
        self.assertIn("pendiente de extraer", motivos[1])
        self.assertIn("estado pendiente", motivos[2])
        r = self.buscar("postizo diametro bolt eye", modo="lexico")
        self.assertFalse(any("postizo" in x.get("extracto", "") for x in r["resultados"]))
        self.assertNotIn("bib:e4", [x["id"] for x in self.buscar("N170", pieza="3212")["resultados"]], "fila del CSV eliminado")
        for ref in ("6", "2"):   # eliminado; duplicado de un original pendiente
            with self.assertRaises(rag.DocumentoNoVigente):
                rag.exacto_celdas(self.rutas, ref)
        est = rag.estado(self.rutas, self.falso)
        self.assertEqual(est["frescura"]["estado"], "ok")
        self.assertEqual(est["cobertura"]["biblioteca"]["elementos"]["pagina"]["no_vigentes"], 2)

    def test_filas_literales_de_duplicados_conservan_su_procedencia(self):
        copia = "0- Bolt Eye/3051 Pump Housing/4- Metrologia/cav13.csv"
        self.modificar_biblioteca((INSERTAR_DOC, (7, copia, "3051 Pump Housing", "3051", "metrologia", "cav13.csv", "csv",
                                                  "duplicado", None, 6, "e" * 64)))
        self.construir()
        fila = next(x for x in self.buscar("N170", pieza="3051", modo="lexico")["resultados"] if x["id"].startswith("bib:e4"))
        self.assertEqual((fila["id"], fila["documento_id"], fila["codigos"], fila["ruta"]), ("bib:e4@d7", 7, ["3051"], f"Exemples/{copia}"))
        self.assertTrue(fila["duplicado_de"].endswith("3212 Pump Housing/4- Metrologia/cav13.csv"))
        self.assertEqual([o["documento_id"] for o in fila["otras_apariciones"]], [6])
        for documento, esperado in ((7, "bib:e4@d7"), (6, "bib:e4")):
            self.assertIn(esperado, [x["id"] for x in self.buscar("GX", documento=documento, modo="lexico")["resultados"]])
        cruzado = self.buscar("GX", pieza="3212", documento=7, modo="lexico")["resultados"]
        self.assertFalse(any(x["id"].startswith("bib:e4") for x in cruzado), "ninguna aparicion cumple ambos filtros")
        self.assertEqual(rag.ver(self.rutas, "bib:e4@d7")["procedencia"]["codigos"], ["3051"])

    def test_ver_no_mezcla_versiones_de_la_biblioteca(self):
        larga = " ".join(f"Frase {i} del informe de correccion con texto suficiente." for i in range(60))
        tabla = [(1, "tabla", f"tabla 1 fila {i}", 10 + i, "Cabecera A | Cabecera B" if i == 1 else
                  f"dato {i} de la tabla con texto de relleno suficiente para ocupar espacio | valor {i}") for i in range(1, 40)]
        insertar = "INSERT INTO elemento(documento_id, tipo, localizador, orden, texto) VALUES (?,?,?,?,?)"
        self.modificar_biblioteca((insertar, (1, "pagina", "pagina 3", 3, larga)), *[(insertar, t) for t in tabla])
        self.construir()
        with closing(rag.abrir_indice(self.rutas)) as con:
            filas = con.execute("SELECT clave, localizador FROM aparicion WHERE clave LIKE 'bib:e%' ORDER BY clave").fetchall()
        partida = next(c for c, _ in filas if c.endswith("#p2") and "@d" not in c)
        cabecera_repetida = next(c for c, loc in filas if loc.startswith("tabla 1") and not loc.startswith("tabla 1 fila 1 ")
                                 and "@d" not in c)
        pagina = next(c for c, loc in filas if loc == "pagina 1" and "@d" not in c)
        for clave in (partida, cabecera_repetida, pagina, f"{pagina}@d2"):
            visto = rag.ver(self.rutas, clave, contexto=1)
            self.assertNotIn("aviso_contexto", visto, clave)
            self.assertIn("resultado", [c["posicion"] for c in visto["contexto"]], clave)
        # Una reextraccion reutiliza el id del elemento con otro texto: no se combina con el fragmento indexado.
        self.modificar_biblioteca("UPDATE elemento SET texto='Contenido de otra version' WHERE localizador='pagina 1'")
        for clave in (pagina, f"{pagina}@d2"):
            visto = rag.ver(self.rutas, clave, contexto=1)
            self.assertEqual(visto["contexto"], [])
            self.assertIn("cambiaron", visto["aviso_contexto"])
            self.assertIn("Plan de correccion", visto["contenido"], "el texto indexado se conserva")
        self.modificar_biblioteca(("UPDATE documento SET sha256=? WHERE id=1", ("9" * 64,)))
        self.assertIn("documento de origen", rag.ver(self.rutas, partida)["aviso_contexto"])

    def test_cad_conserva_textos_completos(self):
        productos = "\n".join([f"Componente {i} del molde de inyeccion" for i in range(120)] + ["Postis sortida gasos"])
        self.modificar_biblioteca(("UPDATE elemento SET texto=? WHERE tipo='productos'", (productos,)),
                                  "INSERT INTO elemento(documento_id, tipo, localizador, orden, texto) "
                                  "VALUES (4, 'cabecera', 'cabecera 2', 3, 'SEGUNDA CABECERA global')")
        fragmentos = self.fragmentos_biblioteca()
        self.assertIn("ISO-10303-21 HEADER FILE_NAME pieza / SEGUNDA CABECERA global", fragmentos["cad:4"].contenido,
                      "varias cabeceras del mismo fichero, en orden")
        self.assertTrue(fragmentos["cad:4"].contenido.split("Productos: ")[1].split("\n")[0].endswith("…"))
        self.assertTrue(any("cad:4#productos1" in a for a in fragmentos["cad:4"].avisos))
        partes = sorted((f for c, f in fragmentos.items() if c.startswith("cad:4#productos")), key=lambda f: f.orden)
        self.assertGreater(len(partes), 1)
        self.assertEqual("\n".join(f.contenido for f in partes), productos, "el listado completo, sin perder nombres")
        self.construir()
        r = self.buscar("Postis sortida gasos", modo="lexico")
        self.assertTrue(r["resultados"][0]["id"].startswith("cad:4#productos"), r["resultados"][:1])
        cabecera = rag.estado(self.rutas, self.falso)["cobertura"]["biblioteca"]["elementos"]["cabecera"]
        self.assertEqual((cabecera["total"], cabecera["en_tarjeta_cad"]), (2, 2), "la cobertura cuenta elementos, no documentos")

    def test_filtro_de_tipo_conserva_la_busqueda_delegada(self):
        self.construir()
        fila = self.buscar("N170", pieza="3212", tipo_fuente="elemento:fila")
        self.assertEqual([x["id"] for x in fila["resultados"]], ["bib:e4"])
        self.assertEqual(self.buscar("N170", pieza="3212", tipo_fuente="elemento:lineas")["resultados"], [])
        self.assertFalse(any(x["id"].startswith("bib:") for x in self.buscar("N170", pieza="3212", tipo_fuente="cad")["resultados"]))

    def test_revision_con_error_de_excel_queda_desconocida(self):
        self.modificar_biblioteca(("UPDATE perfil_ppap SET metadatos=?", (json.dumps({"drawing_level": "#REF!"}),)))
        fragmentos = self.fragmentos_biblioteca()
        for clave in ("hoja:3:DR(SKETCH)", "libro:3"):
            self.assertIsNone(fragmentos[clave].revision, clave)
            self.assertTrue(any("#REF!" in a and "revision desconocida" in a for a in fragmentos[clave].avisos), clave)
        self.assertIn("ilegible", fragmentos["libro:3"].contenido)

    def test_limites_negativos_y_sql_sin_attach(self):
        for argv in (["buscar", "x", "--n", "-1"], ["buscar", "x", "--por-fuente", "0"], ["ver", "md:x", "--contexto", "-1"],
                     ["exacto", "sql", "SELECT 1", "--max", "-1"], ["exacto", "celdas", "3", "--max", "0"], ["construir", "--lote", "0"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                rag.main(argv)
        with self.assertRaises(rag.RagError):
            rag.exacto_sql(self.rutas, "SELECT 1", maximo=-1)
        with self.assertRaises(rag.RagError):
            rag.exacto_celdas(self.rutas, "3", filas="-5")
        intruso = self.raiz / "intruso.db"
        for sql in (f"ATTACH '{intruso.as_posix()}' AS x", "PRAGMA query_only=OFF"):
            with self.assertRaises(rag.SoloLectura, msg=sql):
                rag.exacto_sql(self.rutas, sql)
        self.assertFalse(intruso.exists(), "ATTACH no crea ficheros")
        self.assertTrue(any(f[1] == "ruta" for f in rag.exacto_sql(self.rutas, "PRAGMA table_info(documento)")["filas"]))
        self.assertEqual(rag.exacto_sql(self.rutas, "SELECT count(*) FROM elemento_fts WHERE elemento_fts MATCH 'GX'")["filas"], [[1]])
        recursiva = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 3) SELECT count(*) FROM n"
        self.assertEqual(rag.exacto_sql(self.rutas, recursiva)["filas"], [[3]])


if __name__ == "__main__":
    unittest.main()
