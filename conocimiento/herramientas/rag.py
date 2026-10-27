"""RAG local sobre conocimiento/: busqueda hibrida con procedencia y acceso exacto de solo lectura.

    PY=conocimiento/.venv/Scripts/python.exe
    $PY conocimiento/herramientas/rag.py construir [--solo-lexico] [--forzar]
    $PY conocimiento/herramientas/rag.py estado [--verificar] [--json]
    $PY conocimiento/herramientas/rag.py buscar "N170 bolt eye" [--modo hibrido|lexico|semantico]
        [--coleccion conocimiento] [--pieza 3212] [--feature 0] [--vigencia vigente] [--n 10] [--json]
    $PY conocimiento/herramientas/rag.py ver <id> [--contexto 2] [--json]
    $PY conocimiento/herramientas/rag.py exacto medidas --pieza 3212 --cota N170 [--json]
    $PY conocimiento/herramientas/rag.py exacto celdas <documento> --hoja "DR(100%)" --filas 10-20 [--json]
    $PY conocimiento/herramientas/rag.py exacto hallazgo I-003 [--comprobar] [--json]
    $PY conocimiento/herramientas/rag.py exacto sql "SELECT ..." [--json]
    $PY conocimiento/herramientas/rag.py consultar <argumentos de consultar.py>

Nunca escribe en la biblioteca ni en Exemples. El indice vive en conocimiento/datos/rag/.
Arquitectura, configuracion y limites: conocimiento/rag.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag_fuentes as rf  # noqa: E402
from comun import BD, CONOCIMIENTO, DATOS, ahora  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ESQUEMA_VERSION = 1
LOTE = 16
RRF_K = 60
PESOS = {"semantica": 1.0, "lexica": 1.0, "menciones": 2.0, "propio": 3.0, "filas": 0.6, "filas_mencion": 2.0}
FACTOR_VIGENCIA = {"vigente": 1.0, "no_aplica": 1.0, "revision_fechada": 0.8, "historial": 0.5}
FACTOR_COLECCION = {"inventario": 0.5}
COLECCIONES = ("conocimiento", "historial", "hallazgos", "docs", "biblioteca", "tablas", "cad", "inventario")
GEOMETRIA = re.compile(r"geometr|\bcad\b|step|\bstp\b|\bstl\b|\bigs\b|\bdxf\b|catia|malla|superficie|volumen|caja|"
                       r"plano|dibujo|drawing|imagen|foto|visual|escaneo|forma 3d|3d", re.I)
STOP = set(
    "a al algo ante bajo con como cual de del desde donde el en entre es esta este estos esa eso hay la las lo los me mi "
    "para por que qué se sin sobre su sus un una unos unas y o the of to in and for is are what how les els amb per dels "
    "quiero saber dime pregunta tiene tienen".split())
EXCLUSIONES = [
    "conocimiento/.venv, conocimiento/datos/ (incluidos biblioteca.sqlite como texto, revision-*/ y los propios artefactos RAG)",
    "codigo del repositorio (herramientas/, backend/, frontend/, prototypes/, scripts/), CLAUDE.md, .env y credenciales",
    "binarios originales de Exemples: solo se usa lo que la biblioteca ya extrajo",
    "filas de hoja, lineas de texto y cadenas de binarios: sin embeddings; busqueda literal delegada en elemento_fts",
    "documentos eliminados de Exemples; los pendientes de extraer o con error (y sus duplicados) quedan solo en "
    "inventario, sin el contenido de su extraccion anterior",
]
VIGENTES_SQL = ",".join(f"'{e}'" for e in rf.VIGENTES)


class RagError(Exception):
    codigo = "error"

    def __init__(self, mensaje: str, detalle=None) -> None:
        super().__init__(mensaje)
        self.detalle = detalle


class EmbeddingsNoDisponibles(RagError):
    codigo = "embeddings_no_disponibles"


class ExcedeContexto(RagError):
    codigo = "excede_contexto"


class ConstruccionEnCurso(RagError):
    codigo = "construccion_en_curso"


class FuentesCambiadas(RagError):
    codigo = "fuentes_cambiadas"


class IndiceAusente(RagError):
    codigo = "indice_ausente"


class SoloLectura(RagError):
    codigo = "solo_lectura"


class DocumentoAmbiguo(RagError):
    codigo = "documento_ambiguo"


class DocumentoNoVigente(RagError):
    codigo = "documento_no_vigente"


@dataclass
class Rutas:
    raiz: Path = CONOCIMIENTO.parent
    biblioteca: Path = BD
    rag: Path = DATOS / "rag"

    @property
    def indice(self) -> Path:
        return self.rag / "indice.sqlite"

    @property
    def cache(self) -> Path:
        return self.rag / "cache_embeddings.sqlite"

    @property
    def registro(self) -> Path:
        return self.rag / "registro.jsonl"

    @property
    def cerrojo(self) -> Path:
        return self.rag / "construir.lock"

    @property
    def hallazgos(self) -> Path:
        return self.raiz / "conocimiento" / "hallazgos.jsonl"


# --- Embeddings ---------------------------------------------------------------------------------

class Ollama:
    """embeddinggemma en Ollama local. Mismos prefijos que backend/app/assistant/embeddings.py."""

    def __init__(self, url: str | None = None, modelo: str | None = None) -> None:
        self.url = (url or os.environ.get("RAG_OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.modelo = modelo or os.environ.get("RAG_MODELO") or "embeddinggemma"
        self._http = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # localhost, sin proxy
        self._identidad: dict | None = None

    def _pedir(self, ruta: str, datos: dict | None = None, timeout: float = 10) -> dict:
        peticion = urllib.request.Request(
            self.url + ruta, data=None if datos is None else json.dumps(datos).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with self._http.open(peticion, timeout=timeout) as respuesta:
                return json.load(respuesta)
        except urllib.error.HTTPError as error:
            cuerpo = error.read().decode("utf-8", "replace")
            if "context length" in cuerpo:
                raise ExcedeContexto(cuerpo) from error
            raise EmbeddingsNoDisponibles(f"Ollama respondio {error.code}: {cuerpo[:200]}") from error
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise EmbeddingsNoDisponibles(f"Ollama no responde en {self.url}: {error}") from error

    def identidad(self) -> dict:
        if self._identidad is None:
            modelos = self._pedir("/api/tags", timeout=5).get("models", [])
            nombres = {self.modelo, f"{self.modelo}:latest"}
            modelo = next((m for m in modelos if m.get("name") in nombres or m.get("model") in nombres), None)
            if modelo is None:
                raise EmbeddingsNoDisponibles(f"El modelo {self.modelo} no esta descargado en Ollama")
            info = self._pedir("/api/show", {"model": modelo["name"]}).get("model_info", {})
            self._identidad = {
                "proveedor": "ollama", "modelo": modelo["name"], "digest": modelo["digest"],
                "dimensiones": next((v for k, v in info.items() if k.endswith(".embedding_length")), None),
                "contexto": next((v for k, v in info.items() if k.endswith(".context_length")), None),
                "cuantizacion": modelo.get("details", {}).get("quantization_level"),
                "parametros": modelo.get("details", {}).get("parameter_size"),
                "ollama": self._pedir("/api/version", timeout=5).get("version"),
            }
        return self._identidad

    def embed(self, textos: list[str]) -> list[list[float]]:
        # truncate=false: Ollama truncaria en silencio y el texto pareceria indexado sin estarlo.
        respuesta = self._pedir("/api/embed", {"model": self.modelo, "input": textos, "truncate": False,
                                               "keep_alive": "15m"}, timeout=600)
        vectores = respuesta.get("embeddings")
        if not isinstance(vectores, list) or len(vectores) != len(textos):
            raise EmbeddingsNoDisponibles("Respuesta de embeddings no valida")
        return vectores


def clave_modelo(identidad: dict) -> str:
    """Identifica el espacio vectorial: modelo, digest, dimensiones y receta de entrada."""
    return f"{identidad['proveedor']}:{identidad['modelo']}@{identidad['digest'][:16]}:{identidad['dimensiones']}:{rf.RECETA}"


def consulta_modelo(texto: str) -> str:
    return f"task: search result | query: {texto}"


def normalizar(vector, dimensiones: int) -> np.ndarray:
    v = np.asarray(vector, dtype=np.float32)
    norma = float(np.linalg.norm(v)) if v.size else 0.0
    if v.shape != (dimensiones,) or not np.all(np.isfinite(v)) or norma == 0:
        raise EmbeddingsNoDisponibles("Vector de embedding no valido (dimensiones, valores o norma)")
    return v / norma


# --- Conexiones -------------------------------------------------------------------------------

def abrir_biblioteca(path: Path) -> sqlite3.Connection:
    """Solo lectura doble: URI mode=ro y PRAGMA query_only."""
    if not path.exists():
        raise RagError(f"No existe la biblioteca {path}")
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
    con.execute("PRAGMA query_only=ON")
    return con


PRAGMAS_ESQUEMA = {"table_info", "table_xinfo", "table_list", "index_list", "index_info", "index_xinfo", "foreign_key_list"}


def autorizar_lectura(accion: int, arg1, arg2, base, disparador) -> int:
    """SQL escrito por el usuario: solo lectura. ATTACH crearia un fichero aunque la conexion sea de solo lectura.

    Un PRAGMA solo se admite si consulta (sin valor; FTS5 lee `data_version`) o describe el esquema."""
    if accion in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if accion == sqlite3.SQLITE_PRAGMA and (arg2 is None or (arg1 or "").lower() in PRAGMAS_ESQUEMA):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def ejecutar_lectura(bib: sqlite3.Connection, consulta: str) -> sqlite3.Cursor:
    bib.set_authorizer(autorizar_lectura)
    try:
        return bib.execute(consulta)
    except sqlite3.Error as error:
        if any(t in str(error) for t in ("not authorized", "readonly", "query_only")):
            raise SoloLectura("La biblioteca es de solo lectura: se admiten SELECT/WITH y PRAGMA de esquema "
                              f"({', '.join(sorted(PRAGMAS_ESQUEMA))}); ATTACH, escrituras y otros PRAGMA se rechazan: {error}") from error
        raise RagError(f"SQL no valido: {error}") from error


def abrir_indice(rutas: Rutas) -> sqlite3.Connection:
    if not rutas.indice.exists():
        raise IndiceAusente(f"No hay indice en {rutas.indice}: ejecutar `rag.py construir`")
    con = sqlite3.connect(f"{rutas.indice.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
    con.execute("PRAGMA query_only=ON")
    return con


def meta(con: sqlite3.Connection) -> dict:
    return {k: json.loads(v) for k, v in con.execute("SELECT clave, valor FROM meta")}


def meta_indice(rutas: Rutas) -> dict | None:
    if not rutas.indice.exists():
        return None
    try:
        with closing(abrir_indice(rutas)) as con:
            return meta(con)
    except sqlite3.Error:
        return None


# --- Huellas de las fuentes ---------------------------------------------------------------------

def sha_fichero(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def firma_biblioteca(con: sqlite3.Connection) -> str:
    """Cambia si cambia un documento, su extraccion o el volumen de las tablas derivadas."""
    h = hashlib.sha256()
    for fila in con.execute("SELECT id, ruta, sha256, estado, lector, version_extraida, extraido_el, duplicado_de, mensaje "
                            "FROM documento ORDER BY id"):
        h.update(repr(fila).encode())
    tablas = [n for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'elemento_fts%'")]
    for tabla in sorted(tablas):
        if tabla in ("celda",):   # 11 M filas: su cambio pasa por documento.version_extraida/extraido_el
            continue
        h.update(f"{tabla}:{con.execute(f'SELECT count(*) FROM [{tabla}]').fetchone()[0]}".encode())
    h.update(repr(con.execute("SELECT max(id) FROM ejecucion").fetchone()).encode())
    return h.hexdigest()


def fuentes_repo(rutas: Rutas) -> list[Path]:
    return [p for p, _ in rf.ficheros_markdown(rutas.raiz)] + ([rutas.hallazgos] if rutas.hallazgos.exists() else [])


def huellas(rutas: Rutas, bib: sqlite3.Connection) -> dict[str, str]:
    salida = {f"repo:{p.relative_to(rutas.raiz).as_posix()}": sha_fichero(p) for p in fuentes_repo(rutas)}
    st = rutas.biblioteca.stat()
    salida["biblioteca:fichero"] = f"{st.st_size}:{st.st_mtime_ns}"
    salida["biblioteca:firma"] = firma_biblioteca(bib)
    return salida


def estadisticas_repo(rutas: Rutas) -> dict[str, list[int]]:
    return {f"repo:{p.relative_to(rutas.raiz).as_posix()}": [p.stat().st_size, p.stat().st_mtime_ns] for p in fuentes_repo(rutas)}


def comprobar_frescura(rutas: Rutas, m: dict, completo: bool = False) -> dict:
    """Barata por defecto (stat y, si cambia, SHA-256 o firma); `completo` recolecta y compara fragmentos."""
    guardadas, stats = m.get("huellas", {}), m.get("estadisticas_repo", {})
    cambios = []
    actuales = estadisticas_repo(rutas)
    for clave in sorted(set(actuales) | {k for k in guardadas if k.startswith("repo:")}):
        if clave not in actuales:
            cambios.append(f"eliminado {clave[5:]}")
        elif clave not in guardadas:
            cambios.append(f"nuevo {clave[5:]}")
        elif actuales[clave] != stats.get(clave) and sha_fichero(rutas.raiz / clave[5:]) != guardadas[clave]:
            cambios.append(f"modificado {clave[5:]}")
    posible = []
    if rutas.biblioteca.exists():
        st = rutas.biblioteca.stat()
        if f"{st.st_size}:{st.st_mtime_ns}" != guardadas.get("biblioteca:fichero"):
            with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
                if firma_biblioteca(bib) != guardadas.get("biblioteca:firma"):
                    cambios.append("biblioteca.sqlite: cambiaron documentos, extracciones o tablas derivadas")
                else:
                    posible.append("biblioteca.sqlite modificada (fecha o tamano) con la misma firma; usar `estado --verificar`")
    else:
        cambios.append("biblioteca.sqlite no existe")
    detalle = {}
    if completo and not cambios and rutas.biblioteca.exists():
        with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
            fragmentos, _, _ = recolectar(rutas, bib)
        if huella_fragmentos(fragmentos) != m.get("huella_fragmentos"):
            with closing(abrir_indice(rutas)) as con:
                previos = dict(con.execute("SELECT a.clave, t.sha FROM aparicion a JOIN texto t ON t.id=a.texto_id"))
            nuevos = {f.clave: rf.sha(f.entrada()) for f in fragmentos}
            detalle = {"altas": len(set(nuevos) - set(previos)), "bajas": len(set(previos) - set(nuevos)),
                       "cambiados": sum(1 for k in set(nuevos) & set(previos) if nuevos[k] != previos[k])}
            cambios.append(f"los fragmentos recolectados difieren del indice: {detalle}")
        posible = []
    estado = "desactualizado" if cambios else "posiblemente_desactualizado" if posible else "ok"
    return {"estado": estado, "cambios": cambios + posible, "verificacion": "completa" if completo else "rapida", **detalle}


# --- Construccion -------------------------------------------------------------------------------

ESQUEMA = """
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE texto (
  id INTEGER PRIMARY KEY, sha TEXT NOT NULL UNIQUE, contenido TEXT NOT NULL, entrada TEXT NOT NULL,
  embeber INTEGER NOT NULL, vector BLOB, motivo_sin_vector TEXT);
CREATE TABLE aparicion (
  id INTEGER PRIMARY KEY, clave TEXT NOT NULL UNIQUE, texto_id INTEGER NOT NULL REFERENCES texto(id),
  coleccion TEXT NOT NULL, tipo_fuente TEXT NOT NULL, titulo TEXT, ruta TEXT, raiz TEXT, seccion TEXT,
  localizador TEXT, documento_id INTEGER, feature TEXT, pieza TEXT, codigos TEXT NOT NULL, carpeta TEXT,
  revision TEXT, revision_origen TEXT, vigencia TEXT NOT NULL, clasificacion TEXT, naturaleza TEXT NOT NULL,
  estado_hallazgo TEXT, estado_doc TEXT, sha256_original TEXT, duplicado_de TEXT, grupo TEXT NOT NULL,
  orden INTEGER NOT NULL, retirado INTEGER NOT NULL, motivo_lexico TEXT, identidad TEXT,
  avisos TEXT NOT NULL, datos TEXT NOT NULL);
CREATE INDEX aparicion_texto ON aparicion(texto_id);
CREATE INDEX aparicion_grupo ON aparicion(grupo, orden);
CREATE INDEX aparicion_documento ON aparicion(documento_id);
CREATE TABLE mencion (valor TEXT NOT NULL, aparicion_id INTEGER NOT NULL, tipo TEXT NOT NULL,
  PRIMARY KEY (valor, aparicion_id, tipo)) WITHOUT ROWID;
CREATE VIRTUAL TABLE fts USING fts5(contenido, contexto, tokenize='unicode61 remove_diacritics 2');
"""


class Cerrojo:
    """Excluye construcciones simultaneas en este equipo. OneDrive no coordina equipos distintos."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.tomado = False

    def __enter__(self) -> "Cerrojo":
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    info = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    info = {}
                if info.get("host") == socket.gethostname() and info.get("pid") and not proceso_vivo(int(info["pid"])):
                    self.path.unlink(missing_ok=True)   # cerrojo huerfano de un proceso que ya no existe
                    continue
                raise ConstruccionEnCurso(f"Construccion en curso o cerrojo ajeno: {self.path} {info}")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "host": socket.gethostname(), "inicio": ahora()}, f)
            self.tomado = True
            return self
        raise ConstruccionEnCurso(f"No se pudo tomar el cerrojo {self.path}")

    def __exit__(self, *exc) -> None:
        if self.tomado:
            self.path.unlink(missing_ok=True)


def proceso_vivo(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        manejador = kernel.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not manejador:
            return ctypes.get_last_error() == 5   # acceso denegado: existe
        codigo = ctypes.c_ulong()
        kernel.GetExitCodeProcess(manejador, ctypes.byref(codigo))
        kernel.CloseHandle(manejador)
        return codigo.value == 259   # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def recolectar(rutas: Rutas, bib: sqlite3.Connection) -> tuple[list[rf.Fragmento], list[str], dict]:
    features = rf.features_biblioteca(bib)
    hallazgos, errores = rf.fuentes_hallazgos(rutas.hallazgos)
    fragmentos = rf.fuentes_markdown(rutas.raiz, features) + hallazgos + rf.fuentes_biblioteca(bib)
    contexto = {
        "features": features,
        "codigos": sorted({c for (c,) in bib.execute("SELECT DISTINCT codigo FROM documento WHERE codigo IS NOT NULL")}),
        "documentos_por_estado": dict(bib.execute("SELECT estado, count(*) FROM documento GROUP BY estado")),
        "elementos_por_tipo": dict(bib.execute("SELECT tipo, count(*) FROM elemento GROUP BY tipo")),
        "elementos_vacios": dict(bib.execute("SELECT tipo, count(*) FROM elemento WHERE texto IS NULL OR trim(texto) = '' GROUP BY tipo")),
        "elementos_no_vigentes": dict(bib.execute(
            f"SELECT tipo, count(*) FROM elemento WHERE documento_id IN (SELECT id FROM documento WHERE estado NOT IN ({VIGENTES_SQL})) "
            "GROUP BY tipo")),
    }
    return fragmentos, errores, contexto


def huella_fragmentos(fragmentos: list[rf.Fragmento]) -> str:
    h = hashlib.sha256(f"{ESQUEMA_VERSION}:{rf.RECETA}:{rf.MENCIONES}".encode())
    for f in sorted(fragmentos, key=lambda x: x.clave):
        datos = {k: v for k, v in vars(f).items() if k != "contenido"}
        h.update(json.dumps([rf.sha(f.entrada()), datos], ensure_ascii=False, sort_keys=True, default=list).encode())
    return h.hexdigest()


def abrir_cache(rutas: Rutas) -> sqlite3.Connection:
    con = sqlite3.connect(rutas.cache, timeout=30)
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("CREATE TABLE IF NOT EXISTS vector (modelo TEXT NOT NULL, sha TEXT NOT NULL, vector BLOB NOT NULL, "
                "creado TEXT NOT NULL, PRIMARY KEY (modelo, sha)) WITHOUT ROWID")
    return con


def embeber_pendientes(rutas: Rutas, embedder, identidad: dict, textos: dict[str, dict], lote: int, avisar) -> tuple[dict, dict]:
    """Cache persistente por (espacio vectorial, SHA-256 de la entrada): un fallo no pierde lo ya calculado."""
    modelo, dim = clave_modelo(identidad), int(identidad["dimensiones"])
    necesarios = {s for s, t in textos.items() if t["embeber"]}
    sin_vector: dict[str, str] = {}
    nuevos = 0
    with closing(abrir_cache(rutas)) as cache:
        existentes = {s for (s,) in cache.execute("SELECT sha FROM vector WHERE modelo=?", (modelo,))}
        pendientes = sorted(necesarios - existentes)
        inicio, aviso = time.monotonic(), 0.0
        for i in range(0, len(pendientes), lote):
            bloque = pendientes[i:i + lote]
            try:
                vectores = embedder.embed([textos[s]["entrada"] for s in bloque])
            except ExcedeContexto:
                vectores = []
                for s in bloque:
                    try:
                        vectores.append(embedder.embed([textos[s]["entrada"]])[0])
                    except ExcedeContexto:
                        vectores.append(None)
                        sin_vector[s] = "la entrada excede el contexto del modelo"
            filas = [(modelo, s, normalizar(v, dim).tobytes(), ahora()) for s, v in zip(bloque, vectores) if v is not None]
            cache.executemany("INSERT OR REPLACE INTO vector VALUES (?,?,?,?)", filas)
            cache.commit()
            nuevos += len(filas)
            if time.monotonic() - aviso > 30:
                aviso = time.monotonic()
                avisar(f"  embeddings {i + len(bloque)}/{len(pendientes)} ({time.monotonic() - inicio:.0f} s)")
        vectores = {s: v for s, v in cache.execute("SELECT sha, vector FROM vector WHERE modelo=?", (modelo,)) if s in necesarios}
    return vectores, {"nuevos": nuevos, "reutilizados": len(necesarios & existentes), "sin_vector": sin_vector}


def cobertura(fragmentos: list[rf.Fragmento], textos: dict[str, dict], vectores: dict, contexto: dict) -> dict:
    colecciones: dict[str, dict] = {}
    for f in fragmentos:
        c = colecciones.setdefault(f.coleccion, {"apariciones": 0, "textos": set(), "con_vector": 0, "solo_lexico": {}})
        s = rf.sha(f.entrada())
        c["apariciones"] += 1
        c["textos"].add(s)
        if s in vectores:
            c["con_vector"] += 1
        else:
            motivo = f.motivo_lexico or textos[s].get("motivo_sin_vector") or "sin vector"
            c["solo_lexico"][motivo] = c["solo_lexico"].get(motivo, 0) + 1
    for c in colecciones.values():
        c["textos"] = len(c["textos"])
    elementos: dict[str, int] = {}
    en_cad: dict[str, int] = {}
    for f in fragmentos:
        if f.duplicado_de:
            continue
        if f.tipo_fuente.startswith("elemento:") and not re.search(r"#p[2-9]|#p\d\d", f.clave):
            tipo = f.tipo_fuente.split(":", 1)[1]
            elementos[tipo] = elementos.get(tipo, 0) + len(f.datos.get("elementos", []))
        for tipo, cuantos in f.datos.get("elementos_incluidos", {}).items() if f.coleccion == "cad" else ():
            en_cad[tipo] = en_cad.get(tipo, 0) + cuantos
    vacios, no_vigentes = contexto.get("elementos_vacios", {}), contexto.get("elementos_no_vigentes", {})
    representacion: dict[str, set] = {}
    for f in fragmentos:
        if f.documento_id is not None:
            representacion.setdefault(f.coleccion, set()).add(f.documento_id)
    return {
        "colecciones": colecciones,
        "biblioteca": {
            "documentos_por_estado": contexto["documentos_por_estado"],
            "documentos_por_coleccion": {k: len(v) for k, v in representacion.items()},
            "elementos": {t: {"total": n, "en_fragmentos": elementos.get(t, 0), "en_tarjeta_cad": en_cad.get(t, 0),
                              "vacios": vacios.get(t, 0), "no_vigentes": no_vigentes.get(t, 0),
                              "uso": "busqueda literal delegada (sin vector)" if t in rf.TIPOS_DELEGADOS else "indice"}
                          for t, n in sorted(contexto["elementos_por_tipo"].items())},
        },
        "exclusiones": EXCLUSIONES,
        "limite": "Inventariar los 4.530 originales no equivale a cobertura semantica: CAD, imagenes, videos, "
                  "comprimidos y PDF escaneados solo tienen metadatos o inventario.",
    }


def escribir_indice(destino: Path, fragmentos: list[rf.Fragmento], textos: dict[str, dict], vectores: dict,
                    datos_meta: dict, codigos: set[str]) -> None:
    with closing(sqlite3.connect(destino)) as con:
        con.execute("PRAGMA journal_mode=DELETE")
        con.executescript(ESQUEMA)
        ids = {}
        for i, (s, t) in enumerate(sorted(textos.items()), 1):
            ids[s] = i
            con.execute("INSERT INTO texto VALUES (?,?,?,?,?,?,?)",
                        (i, s, t["contenido"], t["entrada"], int(t["embeber"]), vectores.get(s), t.get("motivo_sin_vector")))
        for i, f in enumerate(sorted(fragmentos, key=lambda x: x.clave), 1):
            s = rf.sha(f.entrada())
            con.execute("INSERT INTO aparicion VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                i, f.clave, ids[s], f.coleccion, f.tipo_fuente, f.titulo, f.ruta, f.raiz, f.seccion, f.localizador,
                f.documento_id, f.feature, f.pieza, "," + ",".join(f.codigos) + ",", f.carpeta, f.revision,
                f.revision_origen, f.vigencia, f.clasificacion, f.naturaleza, f.estado_hallazgo, f.estado_doc,
                f.sha256_original, f.duplicado_de, f.grupo, f.orden, int(f.retirado), f.motivo_lexico, f.identidad,
                json.dumps(list(f.avisos), ensure_ascii=False), json.dumps(f.datos, ensure_ascii=False)))
            encontradas = rf.menciones("\n".join(filter(None, (f.contenido, f.seccion, f.titulo))), codigos)
            if f.identidad:
                encontradas.add(("propio", f.identidad))
            con.executemany("INSERT OR IGNORE INTO mencion VALUES (?,?,?)", [(v, i, t) for t, v in encontradas])
            contexto = " ".join(filter(None, (f.titulo, f.seccion, f.ruta, f.localizador)))
            con.execute("INSERT INTO fts(rowid, contenido, contexto) VALUES (?,?,?)", (i, f.contenido, contexto))
        con.executemany("INSERT INTO meta VALUES (?,?)",
                        [(k, json.dumps(v, ensure_ascii=False, default=list)) for k, v in datos_meta.items()])
        con.commit()
        resultado = con.execute("PRAGMA integrity_check").fetchone()[0]
        n_apar = con.execute("SELECT count(*) FROM aparicion").fetchone()[0]
        if resultado != "ok" or n_apar != len(fragmentos):
            raise RagError(f"Indice temporal no valido: integrity_check={resultado}, apariciones {n_apar}/{len(fragmentos)}")


def reemplazar(origen: Path, destino: Path, intentos: int = 6) -> None:
    """os.replace con reintentos acotados: Windows/OneDrive pueden retener el fichero un momento."""
    ultimo = None
    for i in range(intentos):
        try:
            os.replace(origen, destino)
            return
        except PermissionError as error:
            ultimo = error
            time.sleep(0.5 * 2 ** i)
    raise RagError(f"No se pudo sustituir el indice tras {intentos} intentos: {ultimo}")


def registrar(rutas: Rutas, entrada: dict) -> None:
    rutas.rag.mkdir(parents=True, exist_ok=True)
    with open(rutas.registro, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")


def construir(rutas: Rutas, embedder, solo_lexico: bool = False, forzar: bool = False, lote: int = LOTE,
              avisar=print) -> dict:
    """Recolecta, reutiliza vectores, escribe un temporal y solo lo publica si las fuentes no cambiaron."""
    rutas.rag.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    registro: dict = {"herramienta": "rag.construir", "inicio": ahora(),
                      "parametros": {"solo_lexico": solo_lexico, "forzar": forzar, "lote": lote, "receta": rf.RECETA}}
    temporal: Path | None = None
    try:
        with Cerrojo(rutas.cerrojo):
            with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
                antes = huellas(rutas, bib)
                fragmentos, errores, contexto = recolectar(rutas, bib)
            avisar(f"Recolectados {len(fragmentos)} fragmentos ({time.monotonic() - t0:.0f} s)")
            identidad = None if solo_lexico else embedder.identidad()
            modelo = clave_modelo(identidad) if identidad else None
            huella = huella_fragmentos(fragmentos)
            previo = meta_indice(rutas)
            # Con el mismo modelo, los textos sin vector son rechazos permanentes (exceden el contexto).
            if (previo and not forzar and previo.get("huella_fragmentos") == huella and previo.get("clave_modelo") == modelo
                    and previo.get("huellas") == antes):
                registro.update(resultado="sin_cambios", fragmentos=len(fragmentos))
                avisar("Sin cambios: el indice ya corresponde a las fuentes y al modelo.")
                return registro
            textos: dict[str, dict] = {}
            for f in fragmentos:
                t = textos.setdefault(rf.sha(f.entrada()), {"contenido": f.contenido, "entrada": f.entrada(), "embeber": False})
                t["embeber"] = t["embeber"] or f.embeber
            if identidad:
                avisar(f"Modelo {modelo}; {sum(t['embeber'] for t in textos.values())} textos con embedding")
                vectores, stats = embeber_pendientes(rutas, embedder, identidad, textos, lote, avisar)
            else:
                vectores, stats = {}, {"nuevos": 0, "reutilizados": 0, "sin_vector": {}}
            for s, motivo in stats["sin_vector"].items():
                textos[s]["motivo_sin_vector"] = motivo
            for s, t in textos.items():
                if t["embeber"] and s not in vectores and not t.get("motivo_sin_vector"):
                    t["motivo_sin_vector"] = "indice construido sin embeddings (--solo-lexico)"
            sin_vector = sum(1 for s, t in textos.items() if t["embeber"] and s not in vectores)
            datos_meta = {
                "esquema": ESQUEMA_VERSION, "receta": rf.RECETA, "limite_caracteres": rf.LIMITE,
                "clave_modelo": modelo, "identidad_modelo": identidad, "prefijo_consulta": consulta_modelo("…"),
                "prefijo_documento": "title: <titulo|none> | text: <contenido>",
                "fusion": {"metodo": "RRF", "k": RRF_K, "pesos": PESOS, "factor_vigencia": FACTOR_VIGENCIA,
                           "factor_coleccion": FACTOR_COLECCION},
                "construido_el": ahora(), "huella_fragmentos": huella, "huellas": antes,
                "estadisticas_repo": estadisticas_repo(rutas), "features": contexto["features"],
                "textos_sin_vector": sin_vector, "errores": errores + [f"{s[:12]}: {m}" for s, m in stats["sin_vector"].items()],
                "embeddings": {"nuevos": stats["nuevos"], "reutilizados": stats["reutilizados"]},
                "cobertura": cobertura(fragmentos, textos, vectores, contexto),
            }
            temporal = rutas.rag / f"indice.{uuid.uuid4().hex}.tmp"
            escribir_indice(temporal, fragmentos, textos, vectores, datos_meta, set(contexto["codigos"]))
            with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
                despues = huellas(rutas, bib)
            if despues != antes:
                distintas = sorted(k for k in set(antes) | set(despues) if antes.get(k) != despues.get(k))
                raise FuentesCambiadas(f"Las fuentes cambiaron durante la construccion: {distintas[:10]}")
            reemplazar(temporal, rutas.indice)
            temporal = None
            registro.update(resultado="ok", fragmentos=len(fragmentos), textos=len(textos), con_vector=len(vectores),
                            textos_sin_vector=sin_vector, embeddings=datos_meta["embeddings"], modelo=modelo,
                            tamano_mb=round(rutas.indice.stat().st_size / 1e6, 1))
            avisar(f"Indice publicado: {len(fragmentos)} apariciones, {len(textos)} textos, {len(vectores)} con vector.")
            return registro
    except Exception as error:
        registro.update(resultado="error", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        if temporal is not None:
            for sufijo in ("", "-journal"):
                Path(str(temporal) + sufijo).unlink(missing_ok=True)
        registro["fin"] = ahora()
        registro["duracion_s"] = round(time.monotonic() - t0, 1)
        registrar(rutas, registro)


# --- Busqueda -----------------------------------------------------------------------------------

def minimo(nombre: str, valor: int, limite: int) -> int:
    """SQLite lee `LIMIT -1` como «sin limite»: los limites se validan antes de llegar al SQL."""
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < limite:
        raise RagError(f"{nombre} debe ser un entero >= {limite} (recibido {valor!r})")
    return valor


@dataclass
class Filtros:
    colecciones: list[str] = field(default_factory=list)
    pieza: str | None = None
    feature: str | None = None
    vigencia: list[str] = field(default_factory=list)
    tipo_fuente: str | None = None
    documento: int | None = None
    estado_hallazgo: str | None = None

    def activos(self) -> dict:
        return {k: v for k, v in vars(self).items() if v not in (None, [], "")}


def resolver_feature(valor: str, features: dict[str, str]) -> str:
    if (m := re.match(r"\s*(\d+)", valor)) and m.group(1) in features:
        return features[m.group(1)]
    candidatos = [f for f in features.values() if valor.casefold().replace("-", " ").strip() in f.casefold()]
    if len(candidatos) != 1:
        raise RagError(f"Feature no reconocido o ambiguo: {valor!r}; opciones: {sorted(features.values())}")
    return candidatos[0]


def sql_filtros(filtros: Filtros, features: dict[str, str]) -> tuple[str, list]:
    condiciones, parametros = ["1=1"], []
    if filtros.colecciones:
        desconocidas = set(filtros.colecciones) - set(COLECCIONES)
        if desconocidas:
            raise RagError(f"Coleccion desconocida {sorted(desconocidas)}; opciones: {COLECCIONES}")
        condiciones.append(f"a.coleccion IN ({','.join('?' * len(filtros.colecciones))})")
        parametros += filtros.colecciones
    if filtros.pieza:
        condiciones.append("a.codigos LIKE ?")
        parametros.append(f"%,{filtros.pieza},%")
    if filtros.feature:
        condiciones.append("(a.feature = ? OR a.feature = '*')")
        parametros.append(resolver_feature(filtros.feature, features))
    if filtros.vigencia:
        condiciones.append(f"a.vigencia IN ({','.join('?' * len(filtros.vigencia))})")
        parametros += filtros.vigencia
    if filtros.tipo_fuente:
        condiciones.append("a.tipo_fuente LIKE ?")
        parametros.append(filtros.tipo_fuente + "%")
    if filtros.documento is not None:
        condiciones.append("a.documento_id = ?")
        parametros.append(filtros.documento)
    if filtros.estado_hallazgo:
        condiciones.append("a.estado_hallazgo = ?")
        parametros.append(filtros.estado_hallazgo)
    return " AND ".join(condiciones), parametros


def terminos(consulta: str) -> list[str]:
    return [t for t in dict.fromkeys(re.findall(r"\w+", consulta.casefold())) if t not in STOP and (len(t) > 1 or t.isdigit())]


def expresion_fts(consulta: str, operador: str = "OR") -> str | None:
    t = terminos(consulta)
    return f" {operador} ".join(f'"{x}"' for x in t) if t else None


def semantica_disponible(m: dict, embedder) -> tuple[bool, str | None]:
    if not m.get("clave_modelo"):
        return False, "el indice se construyo sin embeddings (--solo-lexico)"
    if embedder is None:
        return False, "no hay proveedor de embeddings configurado"
    try:
        identidad = embedder.identidad()
    except EmbeddingsNoDisponibles as error:
        return False, str(error)
    if clave_modelo(identidad) != m["clave_modelo"]:
        return False, f"el modelo activo ({clave_modelo(identidad)}) no coincide con el del indice ({m['clave_modelo']})"
    return True, None


COLUMNAS_DOC = ("id", "ruta", "feature", "pieza", "codigo", "sha256")


def filas_biblioteca(rutas: Rutas, consulta: str, filtros: Filtros, features: dict, fts_crudo: bool, limite: int = 30,
                     tipos: tuple[str, ...] = rf.TIPOS_DELEGADOS) -> list[dict]:
    """Coincidencias literales en filas, lineas y cadenas de la biblioteca actual (no estan en el indice).

    Solo documentos con extraccion vigente. Los duplicados no tienen elementos: se busca en su original y el
    resultado lleva la procedencia de la aparicion (original o duplicado) que cumple todos los filtros."""
    feature = resolver_feature(filtros.feature, features) if filtros.feature else None
    duplicado = "d.id IN (SELECT duplicado_de FROM documento WHERE estado='duplicado' AND {} = ?)"
    condiciones, parametros = [f"d.estado IN ({VIGENTES_SQL})", f"e.tipo IN ({','.join('?' * len(tipos))})"], list(tipos)
    for columna, valor in (("codigo", filtros.pieza), ("feature", feature), ("id", filtros.documento)):
        if valor is not None:
            condiciones.append(f"(d.{columna} = ? OR {duplicado.format(columna)})")
            parametros += [valor, valor]

    def cumple(a: dict) -> bool:
        return ((not filtros.pieza or a["codigo"] == filtros.pieza) and (not feature or a["feature"] == feature)
                and (filtros.documento is None or a["id"] == filtros.documento))

    salida: list[dict] = []
    expresiones = [consulta] if fts_crudo else [e for e in (expresion_fts(consulta, "AND"), expresion_fts(consulta, "OR")) if e]
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        for expresion in dict.fromkeys(expresiones):
            sql = ("SELECT e.id, e.tipo, e.localizador, snippet(elemento_fts, 0, '«', '»', '…', 20), e.texto, "
                   + ", ".join(f"d.{c}" for c in COLUMNAS_DOC) + " FROM elemento_fts JOIN elemento e ON e.id = elemento_fts.rowid "
                   "JOIN documento d ON d.id = e.documento_id WHERE elemento_fts MATCH ? "
                   + "".join(f"AND {c} " for c in condiciones) + "ORDER BY rank LIMIT ?")
            vistos = {r["elemento"] for r in salida}
            try:
                filas = bib.execute(sql, [expresion, *parametros, limite]).fetchall()
            except sqlite3.OperationalError as error:
                raise RagError(f"Expresion FTS no valida para la biblioteca: {error}") from error
            for fila in filas:
                if fila[0] in vistos:
                    continue
                original = dict(zip(COLUMNAS_DOC, fila[5:]))
                apariciones = [original] + [dict(zip(COLUMNAS_DOC, r)) for r in bib.execute(
                    f"SELECT {', '.join(COLUMNAS_DOC)} FROM documento WHERE duplicado_de=? AND estado='duplicado' ORDER BY id",
                    (original["id"],))]
                validas = [a for a in apariciones if cumple(a)]
                if not validas:   # cada filtro lo cumple una aparicion distinta, ninguna todos
                    continue
                a = validas[0]
                salida.append({
                    "clave": f"bib:e{fila[0]}" + ("" if a is original else f"@d{a['id']}"), "elemento": fila[0],
                    "tipo_fuente": f"elemento:{fila[1]}", "localizador": fila[2], "documento_id": a["id"], "ruta": a["ruta"],
                    "feature": a["feature"], "pieza": a["pieza"], "codigos": [a["codigo"]] if a["codigo"] else [],
                    "sha256_original": a["sha256"], "duplicado_de": None if a is original else original["ruta"],
                    "extracto": (fila[3] or "").replace("\n", " / "),
                    "otras_apariciones": [{"documento_id": o["id"], "ruta": f"Exemples/{o['ruta']}",
                                           "codigos": [o["codigo"]] if o["codigo"] else [],
                                           "duplicado_de": None if o is original else original["ruta"]}
                                          for o in apariciones if o is not a],
                    "menciones": sorted(v for _, v in rf.menciones(fila[4] or "", set()))})
            if len(salida) >= limite // 3:
                break
    return salida[:limite]


def aviso(codigo: str, mensaje: str) -> dict:
    return {"codigo": codigo, "mensaje": mensaje}


def buscar(rutas: Rutas, consulta: str, modo: str = "hibrido", filtros: Filtros | None = None, n: int = 10,
           por_fuente: int = 3, embedder=None, fts_crudo: bool = False) -> dict:
    minimo("--n", n, 1)
    minimo("--por-fuente", por_fuente, 1)
    filtros = filtros or Filtros()
    salida: dict = {"consulta": consulta, "modo_pedido": modo, "modo_efectivo": None, "filtros": filtros.activos(),
                    "indice": None, "avisos": [], "resultados": [], "completo": False,
                    "nota": "Resultados ordenados por relevancia (RRF), no por certeza. No es un inventario: "
                            "para recuentos o valores usar `rag.py exacto` y citar sus filtros."}
    with closing(abrir_indice(rutas)) as con:
        m = meta(con)
        frescura = comprobar_frescura(rutas, m)
        salida["indice"] = {"construido_el": m.get("construido_el"), "modelo": m.get("clave_modelo"), "frescura": frescura}
        if frescura["estado"] != "ok":
            salida["avisos"].append(aviso("indice_" + frescura["estado"], "; ".join(frescura["cambios"][:5])
                                          + ". Ejecutar `rag.py construir`. Las filas literales vienen de la biblioteca actual."))
        features = m.get("features", {})
        where, params = sql_filtros(filtros, features)
        lexico = modo in ("hibrido", "lexico")
        # Filas, lineas y cadenas no estan en el indice: un filtro de tipo que las nombra mantiene su busqueda.
        delegados = tuple(t for t in rf.TIPOS_DELEGADOS if f"elemento:{t}".startswith(filtros.tipo_fuente or ""))
        delegar = (lexico and bool(delegados) and (not filtros.colecciones or "biblioteca" in filtros.colecciones)
                   and (not filtros.vigencia or "no_aplica" in filtros.vigencia) and not filtros.estado_hallazgo)
        disponibles = con.execute(f"SELECT count(*) FROM aparicion a WHERE {where}", params).fetchone()[0]
        if disponibles == 0:
            salida["avisos"].append(aviso("filtros_sin_fuentes", "Ninguna fuente indexada cumple los filtros "
                                          f"{filtros.activos()}: no es lo mismo que no haya resultados para la consulta."
                                          + (f" Se buscan aparte {', '.join(delegados)} de la biblioteca (busqueda literal)."
                                             if delegar else "")))
        listas: dict[str, list] = {}
        semantica, motivo = (False, None)
        if modo in ("hibrido", "semantico"):
            semantica, motivo = semantica_disponible(m, embedder)
            if semantica:
                try:
                    q = normalizar(embedder.embed([consulta_modelo(consulta)])[0], int(m["identidad_modelo"]["dimensiones"]))
                except RagError as error:
                    semantica, motivo = False, str(error)
            if semantica:
                filas = con.execute(f"SELECT DISTINCT t.id, t.vector FROM texto t JOIN aparicion a ON a.texto_id = t.id "
                                    f"WHERE t.vector IS NOT NULL AND {where}", params).fetchall()
                if filas:
                    matriz = np.frombuffer(b"".join(v for _, v in filas), dtype=np.float32).reshape(len(filas), -1)
                    similitud = matriz @ q
                    orden = np.argsort(-similitud)[:max(60, n * 6)]
                    listas["semantica"] = [((filas[i][0], float(similitud[i])), r) for r, i in enumerate(orden, 1)]
                if m.get("textos_sin_vector"):
                    salida["avisos"].append(aviso("indice_incompleto", f"{m['textos_sin_vector']} textos no tienen vector; "
                                                  "la parte semantica no los cubre (ver `rag.py estado`)."))
            else:
                salida["avisos"].append(aviso("embeddings_no_disponibles", f"Busqueda semantica no disponible: {motivo}."
                                              + (" Resultado SOLO lexico, no hibrido." if modo == "hibrido" else "")))
        if modo == "semantico" and not semantica:
            salida["avisos"].append(aviso("sin_busqueda", "Modo semantico pedido y no disponible: usar --modo lexico."))
            return salida
        if lexico:
            expresion = consulta if fts_crudo else expresion_fts(consulta)
            if expresion:
                try:
                    filas = con.execute(f"SELECT a.texto_id, bm25(fts, 1.0, 0.5) FROM fts JOIN aparicion a ON a.id = fts.rowid "
                                        f"WHERE fts MATCH ? AND {where} ORDER BY bm25(fts, 1.0, 0.5) LIMIT 200",
                                        [expresion, *params]).fetchall()
                except sqlite3.OperationalError as error:
                    raise RagError(f"Expresion FTS no valida: {error}") from error
                unicos = list(dict.fromkeys(t for t, _ in filas))[:max(60, n * 6)]
                listas["lexica"] = [(t, r) for r, t in enumerate(unicos, 1)]
            buscadas = {v for _, v in rf.menciones(consulta, set(), consulta=True)}
            buscadas |= {t for t in re.findall(r"(?<!\d)\d{4}(?!\d)", consulta)}
            if buscadas:
                marcas = ",".join("?" * len(buscadas))
                filas = con.execute(f"SELECT a.texto_id, max(m.tipo = 'propio'), count(DISTINCT m.valor) FROM mencion m "
                                    f"JOIN aparicion a ON a.id = m.aparicion_id WHERE m.valor IN ({marcas}) AND {where} "
                                    f"GROUP BY a.texto_id", [*buscadas, *params]).fetchall()
                # Una mencion exacta es binaria: los empates comparten rango (rango denso por valores distintos).
                niveles = sorted({c for _, _, c in filas}, reverse=True)
                listas["propio"] = [(t, 1) for t, propio, _ in filas if propio]
                listas["menciones"] = [(t, niveles.index(c) + 1) for t, _, c in filas]
                if any(re.fullmatch(r"N\d+(\.\d+)*", b) for b in buscadas) and not filtros.pieza:
                    salida["avisos"].append(aviso("cota_local", "Los N-numbers son locales a cada plano y revision: "
                                                  "filtrar con --pieza antes de unir resultados."))
            if delegar:
                filas = filas_biblioteca(rutas, consulta, filtros, features, fts_crudo, tipos=delegados)
                listas["filas"] = [(x, r) for r, x in enumerate(filas, 1)]
                # Una fila que contiene el identificador exacto pesa como una mencion.
                exactos = {v for _, v in rf.menciones(consulta, set(), consulta=True)}
                listas["filas_mencion"] = [(x, 1) for x in filas if exactos & set(x["menciones"])]
        salida["modo_efectivo"] = "hibrido" if (semantica and lexico) else "semantico" if semantica else "lexico"
        salida["listas"] = {k: len(v) for k, v in listas.items()}
        resultados = fusionar(con, listas, where, params, n, por_fuente)
        salida["resultados"] = resultados
        if GEOMETRIA.search(consulta):
            salida["avisos"].append(aviso("geometria_parcial", "La biblioteca solo conserva metadatos y geometria parcial "
                                          "(recuentos de entidades, triangulos, vertices y algunas cajas). Consultas geometricas "
                                          "completas o calculos nuevos requieren el original; ver --coleccion cad."))
        if filtros.pieza:
            sin_texto = con.execute("SELECT count(*) FROM aparicion a WHERE a.coleccion='inventario' AND a.codigos LIKE ?",
                                    (f"%,{filtros.pieza},%",)).fetchone()[0]
            if sin_texto:
                salida["avisos"].append(aviso("datos_no_extraidos", f"La pieza {filtros.pieza} tiene {sin_texto} documentos sin "
                                              "contenido interpretado (imagenes, escaneos, binarios): ver --coleccion inventario."))
        if not resultados:
            salida["avisos"].append(aviso("sin_resultados", "Sin coincidencias en las fuentes indexadas con estos filtros. "
                                          "Probar otros terminos, --modo lexico o `rag.py consultar buscar` (FTS de la biblioteca)."))
    return salida


def fusionar(con: sqlite3.Connection, listas: dict[str, list], where: str, params: list, n: int, por_fuente: int) -> list[dict]:
    puntos: dict = {}
    detalle: dict = {}
    for nombre, lista in listas.items():
        for item, rango in lista:
            es_fila = nombre.startswith("filas")
            clave = ("fila", item["clave"]) if es_fila else ("texto", item[0] if nombre == "semantica" else item)
            puntos[clave] = puntos.get(clave, 0.0) + PESOS[nombre] / (RRF_K + rango)
            d = detalle.setdefault(clave, {})
            d[nombre] = rango
            if nombre == "semantica":
                d["similitud"] = round(item[1], 4)
            if es_fila:
                d["item"] = item
    resultados, por_grupo = [], {}
    columnas = [c[1] for c in con.execute("PRAGMA table_info(aparicion)")]
    candidatos = []
    for clave, puntuacion in puntos.items():
        if clave[0] == "texto":
            apar = [dict(zip(columnas, r)) for r in con.execute(
                f"SELECT a.* FROM aparicion a WHERE a.texto_id = ? AND {where} ORDER BY "
                "CASE a.vigencia WHEN 'vigente' THEN 0 WHEN 'no_aplica' THEN 1 WHEN 'revision_fechada' THEN 2 ELSE 3 END, a.clave",
                [clave[1], *params])]
            if not apar:
                continue
            factor = FACTOR_VIGENCIA.get(apar[0]["vigencia"], 1.0) * FACTOR_COLECCION.get(apar[0]["coleccion"], 1.0)
            candidatos.append((puntuacion * factor, clave, apar))
        else:
            candidatos.append((puntuacion, clave, None))
    candidatos.sort(key=lambda x: (-x[0], str(x[1])))
    for puntuacion, clave, apar in candidatos:
        if len(resultados) >= n:
            break
        info = detalle[clave]
        señales = {"rrf": round(puntuacion, 5), **{k: v for k, v in info.items() if k != "item"}}
        if apar is None:
            item = info["item"]
            grupo = f"doc:{item['documento_id']}"
            if por_grupo.get(grupo, 0) >= por_fuente:
                continue
            por_grupo[grupo] = por_grupo.get(grupo, 0) + 1
            resultados.append({
                "id": item["clave"], "coleccion": "biblioteca", "tipo_fuente": item["tipo_fuente"], "indexado": False,
                "origen": "elemento_fts de la biblioteca actual (sin embedding)", "naturaleza": "extraido",
                "vigencia": "no_aplica", "ruta": f"Exemples/{item['ruta']}", "localizador": item["localizador"],
                "documento_id": item["documento_id"], "feature": item["feature"], "pieza": item["pieza"],
                "codigos": item["codigos"], "sha256_original": item["sha256_original"], "extracto": item["extracto"],
                **({"duplicado_de": item["duplicado_de"]} if item["duplicado_de"] else {}),
                "otras_apariciones": item["otras_apariciones"], "total_otras_apariciones": len(item["otras_apariciones"]),
                "puntuacion": señales,
                "siguiente": {"ver": f"rag.py ver {item['clave']} --contexto 3",
                              "exacto": f"rag.py consultar ver {item['documento_id']}"}})
            continue
        principal = apar[0]
        # Un hallazgo largo se parte en trozos: basta el mejor; el registro completo sale con `exacto hallazgo`.
        if por_grupo.get(principal["grupo"], 0) >= (1 if principal["grupo"].startswith("hallazgo:") else por_fuente):
            continue
        por_grupo[principal["grupo"]] = por_grupo.get(principal["grupo"], 0) + 1
        contenido = con.execute("SELECT contenido FROM texto WHERE id=?", (principal["texto_id"],)).fetchone()[0]
        resultados.append(resultado(principal, contenido, señales, apar[1:]))
    return resultados


def resultado(a: dict, contenido: str, señales: dict | None, otras: list[dict]) -> dict:
    datos = json.loads(a["datos"])
    ruta = a["ruta"] if a["raiz"] == "repo" else f"Exemples/{a['ruta']}" if a["ruta"] else None
    salida = {
        "id": a["clave"], "coleccion": a["coleccion"], "tipo_fuente": a["tipo_fuente"], "indexado": True,
        "naturaleza": a["naturaleza"], "vigencia": a["vigencia"], "clasificacion": a["clasificacion"],
        "titulo": a["titulo"], "seccion": a["seccion"], "ruta": ruta, "localizador": a["localizador"],
        "documento_id": a["documento_id"], "feature": a["feature"], "pieza": a["pieza"],
        "codigos": [c for c in a["codigos"].split(",") if c], "revision": a["revision"], "revision_origen": a["revision_origen"],
        "estado_hallazgo": a["estado_hallazgo"], "estado_doc": a["estado_doc"], "retirado": bool(a["retirado"]),
        "duplicado_de": a["duplicado_de"], "sha256_original": a["sha256_original"],
        "sha_fragmento": rf.sha(contenido), "avisos": json.loads(a["avisos"]),
        "extracto": contenido if len(contenido) <= 900 else contenido[:900] + "…", "longitud": len(contenido),
        "otras_apariciones": [{"id": o["clave"], "ruta": o["ruta"], "localizador": o["localizador"],
                               "codigos": [c for c in o["codigos"].split(",") if c], "duplicado_de": o["duplicado_de"]}
                              for o in otras[:20]],
        "total_otras_apariciones": len(otras),
        "siguiente": {"ver": f"rag.py ver {a['clave']} --contexto 2"},
    }
    if señales is not None:
        salida["puntuacion"] = señales
    if datos.get("exacto"):
        salida["siguiente"]["exacto"] = datos["exacto"]
    if a["coleccion"] == "hallazgos":
        salida["evidencia"] = datos.get("evidencia")
        salida["siguiente"]["exacto"] = f"rag.py exacto hallazgo {a['identidad']}" + (" --comprobar" if datos.get("comprobacion") else "")
    if a["motivo_lexico"]:
        salida["motivo_sin_vector"] = a["motivo_lexico"]
    return {k: v for k, v in salida.items() if v not in (None, [], {})}


# --- Ver ----------------------------------------------------------------------------------------

def ver(rutas: Rutas, clave: str, contexto: int = 2) -> dict:
    minimo("--contexto", contexto, 0)
    with closing(abrir_indice(rutas)) as con:
        columnas = [c[1] for c in con.execute("PRAGMA table_info(aparicion)")]
        fila = con.execute("SELECT * FROM aparicion WHERE clave=?", (clave,)).fetchone()
        if fila:
            a = dict(zip(columnas, fila))
            contenido = con.execute("SELECT contenido FROM texto WHERE id=?", (a["texto_id"],)).fetchone()[0]
            otras = [dict(zip(columnas, r)) for r in con.execute(
                "SELECT * FROM aparicion WHERE texto_id=? AND id != ? ORDER BY clave", (a["texto_id"], a["id"]))]
            salida = resultado(a, contenido, None, otras)
            salida["contenido"] = contenido
            salida.pop("extracto", None)
            info = meta(con)
            salida["indice"] = {"construido_el": info.get("construido_el"), "frescura": comprobar_frescura(rutas, info)}
            datos = json.loads(a["datos"])
            if a["tipo_fuente"].startswith("elemento:") and datos.get("elementos"):
                # El texto sale del indice y los vecinos de la biblioteca actual: solo se combinan si son los mismos elementos.
                problema = identidad_cambiada(rutas, datos)
                if problema:
                    salida["contexto"] = []
                    salida["aviso_contexto"] = (f"{problema}: no se adjunta contexto de la biblioteca actual para no mezclar "
                                                "versiones. Ejecutar `rag.py construir`.")
                else:
                    salida["contexto"] = vecinos_biblioteca(rutas, datos["elementos"][0], datos["elementos"][-1], contexto)
            elif contexto:
                salida["contexto"] = [
                    {"id": r[0], "localizador": r[1], "seccion": r[2], "contenido": r[3], "posicion": "antes" if r[4] < a["orden"] else "despues"}
                    for r in con.execute(
                        "SELECT * FROM (SELECT a.clave, a.localizador, a.seccion, t.contenido, a.orden FROM aparicion a JOIN texto t ON t.id=a.texto_id "
                        "WHERE a.grupo=? AND a.orden < ? ORDER BY a.orden DESC LIMIT ?) UNION ALL "
                        "SELECT * FROM (SELECT a.clave, a.localizador, a.seccion, t.contenido, a.orden FROM aparicion a JOIN texto t ON t.id=a.texto_id "
                        "WHERE a.grupo=? AND a.orden > ? ORDER BY a.orden LIMIT ?) ORDER BY 5",
                        (a["grupo"], a["orden"], contexto, a["grupo"], a["orden"], contexto))]
            return salida
    if m := re.fullmatch(r"bib:e(\d+)(?:@d(\d+))?", clave):
        elemento = int(m.group(1))
        salida = {"id": clave, "indexado": False, "origen": "elemento de la biblioteca actual (busqueda literal delegada)"}
        if m.group(2):
            salida["procedencia"] = procedencia_duplicado(rutas, elemento, int(m.group(2)))
        salida["contexto"] = vecinos_biblioteca(rutas, elemento, elemento, contexto)
        return salida
    raise RagError(f"No existe el resultado {clave!r} en el indice")


def identidad_cambiada(rutas: Rutas, datos: dict) -> str | None:
    """None si los elementos del fragmento siguen igual en la biblioteca; si no, el motivo.

    Compara los elementos completos (id, documento, texto) guardados al construir, no el fragmento: asi no hay
    falsas discrepancias por partes, cabeceras de tabla repetidas o duplicados que heredan el contenido."""
    if not datos.get("huella_elementos"):
        return "el fragmento no guarda la identidad de sus elementos (indice anterior)"
    ids = datos["elementos"]
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        filas = {r[0]: r for r in bib.execute(
            f"SELECT id, documento_id, texto FROM elemento WHERE id IN ({','.join('?' * len(ids))})", ids)}
        doc = bib.execute("SELECT estado, sha256 FROM documento WHERE id=?", (datos["documento_elementos"],)).fetchone()
    if len(filas) != len(ids) or rf.huella_elementos(filas[i] for i in ids) != datos["huella_elementos"]:
        return "los elementos del fragmento cambiaron o ya no existen en la biblioteca actual"
    if doc is None or doc[0] not in rf.VIGENTES or doc[1] != datos.get("sha256_documento"):
        return f"el documento de origen cambio en la biblioteca actual ({'ya no existe' if doc is None else f'estado {doc[0]}'})"
    return None


def procedencia_duplicado(rutas: Rutas, elemento: int, duplicado: int) -> dict:
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        d = bib.execute("SELECT d.id, d.ruta, d.codigo, o.ruta FROM documento d JOIN documento o ON o.id = d.duplicado_de "
                        "JOIN elemento e ON e.documento_id = o.id WHERE d.id=? AND d.estado='duplicado' AND e.id=?",
                        (duplicado, elemento)).fetchone()
    if not d:
        raise RagError(f"El documento {duplicado} ya no es un duplicado del documento del elemento {elemento}: repetir la busqueda")
    return {"documento_id": d[0], "ruta": f"Exemples/{d[1]}", "codigos": [d[2]] if d[2] else [], "duplicado_de": f"Exemples/{d[3]}"}


def vecinos_biblioteca(rutas: Rutas, primero: int, ultimo: int, contexto: int) -> list[dict]:
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        fila = bib.execute("SELECT e.documento_id, e.orden, d.ruta, d.estado FROM elemento e JOIN documento d ON d.id=e.documento_id "
                           "WHERE e.id=?", (primero,)).fetchone()
        fin = bib.execute("SELECT orden FROM elemento WHERE id=?", (ultimo,)).fetchone()
        if not fila or not fin:
            raise RagError(f"El elemento {primero} ya no existe en la biblioteca: indice desactualizado")
        if fila[3] not in rf.VIGENTES:
            raise DocumentoNoVigente(f"El elemento {primero} es de un documento en estado {fila[3]} (Exemples/{fila[2]}): "
                                     "su contenido no es vigente")
        return [{"elemento": r[0], "tipo": r[1], "localizador": r[2], "texto": r[3], "ruta": f"Exemples/{fila[2]}",
                 "posicion": "antes" if r[4] < fila[1] else "despues" if r[4] > fin[0] else "resultado"}
                for r in bib.execute("SELECT id, tipo, localizador, texto, orden FROM elemento WHERE documento_id=? "
                                     "AND orden BETWEEN ? AND ? ORDER BY orden", (fila[0], fila[1] - contexto, fin[0] + contexto))]


# --- Consultas exactas --------------------------------------------------------------------------

def letra_columna(n: int) -> str:
    letras = ""
    while n:
        n, r = divmod(n - 1, 26)
        letras = chr(65 + r) + letras
    return letras


def resolver_documento(bib: sqlite3.Connection, ref: str) -> dict:
    """Por id, ruta completa o final de ruta inequivoco. Varios ficheros comparten nombre: nunca se elige uno."""
    columnas = ("id", "ruta", "codigo", "ext", "estado", "lector", "mensaje", "duplicado_de", "sha256")
    sql = f"SELECT {', '.join(columnas)} FROM documento WHERE "
    ref = str(ref).strip()
    if ref.isdigit():
        filas = bib.execute(sql + "id=?", (int(ref),)).fetchall()
    else:
        ruta = ref.replace("\\", "/").removeprefix("Exemples/").strip("/")
        filas = bib.execute(sql + "ruta=?", (ruta,)).fetchall()
        if not filas:   # final de ruta a partir de un separador; % y _ son literales
            patron = "%/" + ruta.replace("%", "\\%").replace("_", "\\_")
            filas = bib.execute(sql + "ruta LIKE ? ESCAPE '\\' ORDER BY ruta", (patron,)).fetchall()
    if not filas:
        raise RagError(f"Documento no encontrado: {ref}")
    if len(filas) > 1:
        candidatos = [{"id": f[0], "ruta": f"Exemples/{f[1]}", "estado": f[4]} for f in filas]
        raise DocumentoAmbiguo(f"{len(filas)} documentos coinciden con {ref!r}: indicar el id o una ruta inequivoca",
                               detalle={"candidatos": candidatos})
    return dict(zip(columnas, filas[0]))


def documento_vigente(bib: sqlite3.Connection, doc: dict) -> tuple[dict, list[str]]:
    """Documento cuyos datos se leen (el original si es un duplicado) y avisos; error si su extraccion no es vigente."""
    avisos = []
    if doc["estado"] == "duplicado" and doc["duplicado_de"]:
        original = resolver_documento(bib, str(doc["duplicado_de"]))
        avisos.append(f"Duplicado sin celdas propias: se leen las del original identico Exemples/{original['ruta']}")
        leido = original
    else:
        leido = doc
    if leido["estado"] not in rf.VIGENTES:
        raise DocumentoNoVigente(
            f"Exemples/{leido['ruta']} esta en estado {leido['estado']} ({rf.NO_VIGENTES.get(leido['estado'], 'sin extraccion')}): "
            "sus datos no corresponden al fichero actual. Para consultar la extraccion anterior como tal: `rag.py exacto sql`.")
    return leido, avisos


def formulas_documento(bib: sqlite3.Connection, doc_id: int, ext: str) -> tuple[bool | None, str]:
    fila = bib.execute("SELECT valor FROM estructura WHERE documento_id=? AND clave='formulas'", (doc_id,)).fetchone()
    valor = json.loads(fila[0]) if fila else None
    if ext == "csv":
        return None, "CSV: no hay formulas"
    if isinstance(valor, int) or valor == "via Excel COM":
        return True, f"texto de formula conservado ({valor})"
    return False, f"texto de formula no disponible ({valor or 'sin dato'}); solo constan las RAND de celda_aleatoria"


def exacto_celdas(rutas: Rutas, ref: str, hoja: str | None = None, filas: str | None = None, maximo: int = 500) -> dict:
    minimo("--max", maximo, 1)
    rango = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", filas) if filas else None
    if filas and (not rango or int(rango.group(2) or rango.group(1)) < int(rango.group(1))):
        raise RagError(f"--filas debe ser N o N-M con N <= M (recibido {filas!r})")
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        doc = resolver_documento(bib, ref)
        doc_celdas, avisos = documento_vigente(bib, doc)
        disponible, nota_formula = formulas_documento(bib, doc_celdas["id"], doc_celdas["ext"])
        condiciones, parametros = ["documento_id=?"], [doc_celdas["id"]]
        if hoja:
            condiciones.append("hoja=?")
            parametros.append(hoja)
        if rango:
            condiciones.append("fila BETWEEN ? AND ?")
            parametros += [int(rango.group(1)), int(rango.group(2) or rango.group(1))]
        where = " AND ".join(condiciones)
        total = bib.execute(f"SELECT count(*) FROM celda WHERE {where}", parametros).fetchone()[0]
        aleatorias = {(h, f, c): fo for h, f, c, fo in bib.execute(
            f"SELECT hoja, fila, col, formula FROM celda_aleatoria WHERE {where}", parametros)}
        celdas = []
        for h, f, c, valor, numero, formula in bib.execute(
                f"SELECT hoja, fila, col, valor, numero, formula FROM celda WHERE {where} ORDER BY hoja, fila, col LIMIT ?",
                [*parametros, maximo]):
            celdas.append({
                "hoja": h, "celda": f"{letra_columna(c)}{f}", "fila": f, "col": c, "valor": valor, "numero": numero,
                "formula": formula or aleatorias.get((h, f, c)),
                "estado": ("sin_valor_guardado" if valor is None else "cero" if numero == 0 else
                           "numero" if numero is not None else "texto"),
                "aleatoria": (h, f, c) in aleatorias})
        if doc_celdas["mensaje"]:
            avisos.append(f"Aviso del lector: {doc_celdas['mensaje']}")
        avisos += ["Celda no listada = vacia en el original o no extraida; `sin_valor_guardado` = formula sin valor cacheado; "
                   "`cero` es un valor 0, no una ausencia.",
                   "Que una celda no este en celda_aleatoria no certifica que sea una medicion (copias, previsiones)."]
        return {"documento": {**doc, "ruta": f"Exemples/{doc['ruta']}"}, "formulas_disponibles": disponible,
                "formulas": nota_formula, "alcance": {"hoja": hoja, "filas": filas, "total": total, "devueltas": len(celdas),
                                                      "truncado": total > len(celdas)},
                "avisos": avisos, "celdas": celdas}


AVISOS_MEDIDAS = [
    "medida_dr es la salida del prototipo heuristico lector_dr, no una copia integra: omite celdas vacias y no "
    "numericas, normaliza codigos de cota (N170 -> 170), ordena tolerancias invertidas y descarta bloques secundarios.",
    "Solo hojas XLS/XLSX/XLSM con cabecera Nominal: los CSV de la CMM no estan (preferibles cuando coinciden, "
    "trampas.md); consultarlos con `exacto celdas`.",
    "Las cotas son locales a cada plano y revision: no unir piezas por el numero.",
    "Clasificacion `indeterminada`: ni el papel de la hoja ni la ausencia en celda_aleatoria certifican que un valor "
    "sea medicion, prevision o copia.",
]


def exacto_medidas(rutas: Rutas, pieza: str | None = None, documento: str | None = None, cota: str | None = None,
                   hoja: str | None = None, cavidad: str | None = None, maximo: int = 200) -> dict:
    from lector_dr import codigo_normal
    if not pieza and not documento:
        raise RagError("Indicar --pieza o --documento: las cotas son locales a cada plano")
    minimo("--max", maximo, 1)
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        condiciones, parametros, filtros, avisos_doc = [], [], {}, []
        if pieza:
            condiciones.append("(d.codigo = ? OR d.id IN (SELECT duplicado_de FROM documento WHERE estado='duplicado' AND codigo = ?))")
            parametros += [pieza, pieza]
            filtros["pieza"] = pieza
        if documento:
            doc = resolver_documento(bib, documento)
            leido, avisos_doc = documento_vigente(bib, doc)
            condiciones.append("m.documento_id = ?")
            parametros.append(leido["id"])
            filtros["documento"] = doc["ruta"]
        if cota:
            normal = codigo_normal(cota) or cota.strip().upper()
            condiciones.append("m.cota = ?")
            parametros.append(normal)
            filtros["cota"] = f"{cota} (normalizada por lector_dr: {normal})"
        if hoja:
            condiciones.append("m.hoja = ?")
            parametros.append(hoja)
            filtros["hoja"] = hoja
        if cavidad:
            condiciones.append("m.cavidad = ?")
            parametros.append(cavidad)
            filtros["cavidad"] = cavidad
        where = " AND ".join(condiciones)
        no_vigentes = bib.execute(f"SELECT count(*) FROM medida_dr m JOIN documento d ON d.id = m.documento_id WHERE {where} "
                                  f"AND d.estado NOT IN ({VIGENTES_SQL})", parametros).fetchone()[0]
        where += f" AND d.estado IN ({VIGENTES_SQL})"
        base = "FROM medida_dr m JOIN documento d ON d.id = m.documento_id WHERE " + where
        total, n_docs, n_hojas = bib.execute(
            f"SELECT count(*), count(DISTINCT m.documento_id), count(DISTINCT m.documento_id || '|' || m.hoja) {base}", parametros).fetchone()
        filas = bib.execute(
            "SELECT d.id, d.ruta, d.ext, m.hoja, m.fila, m.col, m.cota, m.nominal, m.tol_sup, m.tol_inf, m.equipo, m.cavidad, "
            "m.valor, m.marca, l.papel, l.plantilla, c.valor, c.formula, a.formula "
            "FROM medida_dr m JOIN documento d ON d.id = m.documento_id "
            "LEFT JOIN lectura_dr l ON l.documento_id = m.documento_id AND l.hoja = m.hoja "
            "LEFT JOIN celda c ON c.documento_id = m.documento_id AND c.hoja = m.hoja AND c.fila = m.fila AND c.col = m.col "
            "LEFT JOIN celda_aleatoria a ON a.documento_id = m.documento_id AND a.hoja = m.hoja AND a.fila = m.fila AND a.col = m.col "
            f"WHERE {where} ORDER BY d.ruta, m.hoja, m.fila, m.col LIMIT ?", [*parametros, maximo]).fetchall()
        disponibles, hojas = {}, {}
        medidas = []
        for (doc_id, ruta, ext, h, f, c, cota_n, nominal, sup, inf, equipo, cav, valor, marca, papel, plantilla,
             c_valor, c_formula, a_formula) in filas:
            if doc_id not in disponibles:
                disponibles[doc_id] = formulas_documento(bib, doc_id, ext)[0]
            if (doc_id, h) not in hojas:
                l = bib.execute("SELECT cualitativos, rechazadas, columnas_descartadas FROM lectura_dr WHERE documento_id=? AND hoja=?",
                                (doc_id, h)).fetchone()
                hojas[(doc_id, h)] = {"documento": f"Exemples/{ruta}", "hoja": h, "papel": papel, "plantilla": plantilla,
                                      "no_numericos_omitidos": l[0] if l else None,
                                      "ajustes_y_rechazos": json.loads(l[1]) if l and l[1] else {},
                                      "columnas_descartadas": json.loads(l[2]) if l and l[2] else {}}
            marcas = (marca or "").split(",") if marca else []
            if "aleatoria" in marcas or a_formula:
                clasificacion, motivo = "generada_rand", "celda con formula aleatoria (I-003): no es una medida"
            else:
                clasificacion = "indeterminada"
                motivo = (f"papel de la hoja: {papel}" if papel and papel != "informe"
                          else "sin evidencia que certifique medicion (la ausencia en celda_aleatoria no lo prueba)")
            if "cero" in marcas:
                motivo += "; valor 0 con nominal distinto de 0 (puede ser no medida, I-002)"
            if "atipico" in marcas:
                motivo += "; desviacion > 10 veces el intervalo de tolerancia"
            medidas.append({
                "documento_id": doc_id, "ruta": f"Exemples/{ruta}", "hoja": h, "celda": f"{letra_columna(c)}{f}",
                "cota_lector": cota_n, "nominal": nominal, "tol_sup": sup, "tol_inf": inf, "equipo": equipo,
                "cavidad_lector": cav, "valor_lector": valor, "marca": marca,
                "celda_original": {"valor": c_valor, "formula": c_formula or a_formula,
                                   "formula_disponible": disponibles[doc_id]},
                "clasificacion": clasificacion, "motivo": motivo, "origen": "derivado: medida_dr (lector_dr heuristico)"})
        avisos = avisos_doc + list(AVISOS_MEDIDAS)
        if no_vigentes:
            avisos.insert(0, f"{no_vigentes} filas de documentos pendientes de extraer, con error o eliminados quedan fuera: "
                             "su extraccion no corresponde al fichero actual.")
        if not total:
            avisos.insert(0, "Sin filas en medida_dr con estos filtros: no prueba que la cota no exista. Puede estar en un CSV "
                             "de la CMM, en una hoja que el lector no reconoce o con otro codigo (`rag.py buscar` / `exacto celdas`).")
        return {"alcance": {"filtros": filtros, "total": total, "documentos": n_docs, "hojas": n_hojas,
                            "devueltas": len(medidas), "truncado": total > len(medidas), "excluidas_no_vigentes": no_vigentes},
                "avisos": avisos, "hojas": list(hojas.values()), "medidas": medidas}


def exacto_hallazgo(rutas: Rutas, ident: str, comprobar: bool = False) -> dict:
    for n, linea in enumerate(rutas.hallazgos.read_text(encoding="utf-8").splitlines(), 1):
        if linea.strip() and (r := json.loads(linea)).get("id", "").upper() == ident.upper():
            salida = {"registro": r, "localizador": f"conocimiento/hallazgos.jsonl:{n}"}
            if comprobar:
                if not r.get("comprobacion"):
                    salida["comprobacion"] = {"estado": "sin_comprobacion", "mensaje": "El hallazgo no tiene SQL registrado"}
                else:
                    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
                        obtenido = list(ejecutar_lectura(bib, r["comprobacion"]["sql"]).fetchone() or [])
                    salida["comprobacion"] = {"estado": "coincide" if obtenido == r["comprobacion"]["esperado"] else "difiere",
                                              "esperado": r["comprobacion"]["esperado"], "obtenido": obtenido}
            return salida
    raise RagError(f"Hallazgo no encontrado: {ident}")


def exacto_sql(rutas: Rutas, consulta: str, maximo: int = 200) -> dict:
    minimo("--max", maximo, 1)
    with closing(abrir_biblioteca(rutas.biblioteca)) as bib:
        cursor = ejecutar_lectura(bib, consulta)
        filas = cursor.fetchmany(maximo + 1) if cursor.description else []
        columnas = [d[0] for d in cursor.description or []]
    return {"columnas": columnas, "filas": [list(f) for f in filas[:maximo]], "devueltas": min(len(filas), maximo),
            "truncado": len(filas) > maximo,
            "aviso": "Resultado exacto de la biblioteca con la consulta indicada; citar el SQL como alcance."}


# --- Estado -------------------------------------------------------------------------------------

def estado(rutas: Rutas, embedder=None, verificar: bool = False) -> dict:
    ultimos = []
    if rutas.registro.exists():
        ultimos = [json.loads(l) for l in rutas.registro.read_text(encoding="utf-8").splitlines()[-3:] if l.strip()]
    m = meta_indice(rutas)
    if m is None:
        return {"indice": "ausente", "ruta": str(rutas.indice), "registro": ultimos,
                "mensaje": "Ejecutar `rag.py construir` (o --solo-lexico si Ollama no esta disponible)"}
    disponible, motivo = semantica_disponible(m, embedder)
    return {
        "indice": "presente", "ruta": str(rutas.indice), "tamano_mb": round(rutas.indice.stat().st_size / 1e6, 1),
        "construido_el": m.get("construido_el"), "esquema": m.get("esquema"), "receta": m.get("receta"),
        "modelo": m.get("identidad_modelo"), "clave_modelo": m.get("clave_modelo"),
        "semantica": {"disponible": disponible, "motivo": motivo},
        "frescura": comprobar_frescura(rutas, m, completo=verificar), "textos_sin_vector": m.get("textos_sin_vector"),
        "embeddings": m.get("embeddings"), "errores": m.get("errores"), "cobertura": m.get("cobertura"),
        "fusion": m.get("fusion"), "registro": ultimos,
    }


# --- Salida legible -------------------------------------------------------------------------------

def imprimir_busqueda(r: dict) -> None:
    modo = {"hibrido": "hibrido (lexico + semantico)", "lexico": "SOLO lexico", "semantico": "semantico"}.get(r["modo_efectivo"], "ninguno")
    fres = r["indice"]["frescura"]["estado"] if r.get("indice") else "?"
    print(f'Consulta: "{r["consulta"]}" · modo {modo} · indice {fres} ({(r.get("indice") or {}).get("construido_el")})')
    if r["filtros"]:
        print(f"Filtros: {r['filtros']}")
    for a in r["avisos"]:
        print(f"! {a['codigo']}: {a['mensaje']}")
    for i, x in enumerate(r["resultados"], 1):
        etiqueta = " · ".join(filter(None, (x["coleccion"], x.get("vigencia"), x.get("naturaleza"), x.get("estado_hallazgo"))))
        print(f"\n{i}. [{etiqueta}] {x.get('ruta') or ''} · {x.get('localizador') or ''}")
        extra = " ".join(filter(None, (f"piezas {','.join(x['codigos'])}" if x.get("codigos") else None,
                                       f"rev {x['revision']}" if x.get("revision") else None,
                                       "contiene texto RETIRADO" if x.get("retirado") else None)))
        print(f"   id: {x['id']}  {extra}  {x.get('puntuacion')}")
        print("   " + (x.get("extracto") or "")[:400].replace("\n", "\n   "))
        if x.get("total_otras_apariciones"):
            print(f"   + {x['total_otras_apariciones']} apariciones mas del mismo texto (ver JSON)")
        for av in x.get("avisos", []):
            print(f"   ⚠ {av}")
    print(f"\n{r['nota']}")


def imprimir_estado(r: dict) -> None:
    if r["indice"] == "ausente":
        print(f"Indice ausente ({r['ruta']}). {r['mensaje']}")
        return
    m = r.get("modelo") or {}
    print(f"Indice {r['ruta']} · {r['tamano_mb']} MB · construido {r['construido_el']} · esquema {r['esquema']} · receta {r['receta']}")
    print(f"Modelo: {m.get('modelo')} digest {str(m.get('digest'))[:16]} · {m.get('dimensiones')} dim · contexto {m.get('contexto')} "
          f"· Ollama {m.get('ollama')}" if m else "Modelo: ninguno (indice solo lexico)")
    sem = r["semantica"]
    print(f"Semantica: {'disponible' if sem['disponible'] else 'NO disponible: ' + str(sem['motivo'])}")
    fr = r["frescura"]
    print(f"Frescura ({fr['verificacion']}): {fr['estado']}" + "".join(f"\n  - {c}" for c in fr["cambios"]))
    print(f"Textos sin vector: {r['textos_sin_vector']} · embeddings {r['embeddings']}")
    cob = r["cobertura"] or {}
    print("\nColeccion       apariciones  textos  con vector  solo lexico")
    for nombre, c in cob.get("colecciones", {}).items():
        solo = sum(c["solo_lexico"].values())
        print(f"{nombre:<15} {c['apariciones']:>11} {c['textos']:>7} {c['con_vector']:>11} {solo:>12}")
        motivos = sorted(c["solo_lexico"].items(), key=lambda x: -x[1])
        for motivo, k in motivos[:3]:
            print(f"{'':<17}{k:>6} · {motivo}")
        if len(motivos) > 3:
            print(f"{'':<17}{sum(k for _, k in motivos[3:]):>6} · otros {len(motivos) - 3} motivos (detalle en estado --json)")
    bib = cob.get("biblioteca", {})
    print(f"\nBiblioteca: documentos por estado {bib.get('documentos_por_estado')}")
    print(f"Documentos representados por coleccion: {bib.get('documentos_por_coleccion')}")
    for tipo, e in bib.get("elementos", {}).items():
        print(f"  elemento {tipo:<12} total {e['total']:>7} · en fragmentos {e['en_fragmentos']:>6} · en tarjeta CAD "
              f"{e['en_tarjeta_cad']:>4} · vacios {e['vacios']:>5} · {e['uso']}"
              + (f" · {e['no_vigentes']} de documentos no vigentes (fuera)" if e.get("no_vigentes") else ""))
    print("\nExcluido: " + "; ".join(cob.get("exclusiones", [])))
    print(cob.get("limite", ""))
    for x in r.get("registro", []):
        print(f"Registro: {x.get('inicio')} {x.get('resultado')} {x.get('error') or ''} ({x.get('duracion_s')} s)")


def entero_desde(limite: int):
    def convertir(texto: str) -> int:
        try:
            return minimo("valor", int(texto), limite)
        except (ValueError, RagError):
            raise argparse.ArgumentTypeError(f"debe ser un entero >= {limite} (recibido {texto!r})") from None
    return convertir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG local de conocimiento/ (ver conocimiento/rag.md)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    positivo, natural = entero_desde(1), entero_desde(0)
    p = sub.add_parser("construir")
    p.add_argument("--solo-lexico", action="store_true", help="sin embeddings; la busqueda sera solo lexica")
    p.add_argument("--forzar", action="store_true", help="reescribir aunque no haya cambios")
    p.add_argument("--lote", type=positivo, default=LOTE)
    p = sub.add_parser("estado")
    p.add_argument("--verificar", action="store_true", help="recolectar y comparar todos los fragmentos")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("buscar")
    p.add_argument("consulta")
    p.add_argument("--modo", choices=("hibrido", "lexico", "semantico"), default="hibrido")
    p.add_argument("--coleccion", action="append", default=[], choices=COLECCIONES)
    p.add_argument("--pieza")
    p.add_argument("--feature")
    p.add_argument("--vigencia", action="append", default=[], choices=tuple(FACTOR_VIGENCIA))
    p.add_argument("--tipo-fuente")
    p.add_argument("--documento", type=int)
    p.add_argument("--estado-hallazgo")
    p.add_argument("--n", type=positivo, default=10)
    p.add_argument("--por-fuente", type=positivo, default=3, help="maximo de resultados por fichero o documento")
    p.add_argument("--fts", action="store_true", help="la consulta es una expresion FTS5 literal")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("ver")
    p.add_argument("id")
    p.add_argument("--contexto", type=natural, default=2)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("exacto")
    ex = p.add_subparsers(dest="exacto", required=True)
    q = ex.add_parser("medidas")
    q.add_argument("--pieza")
    q.add_argument("--documento")
    q.add_argument("--cota")
    q.add_argument("--hoja")
    q.add_argument("--cavidad")
    q.add_argument("--max", type=positivo, default=200)
    q.add_argument("--json", action="store_true")
    q = ex.add_parser("celdas")
    q.add_argument("documento")
    q.add_argument("--hoja")
    q.add_argument("--filas")
    q.add_argument("--max", type=positivo, default=500)
    q.add_argument("--json", action="store_true")
    q = ex.add_parser("hallazgo")
    q.add_argument("id")
    q.add_argument("--comprobar", action="store_true")
    q.add_argument("--json", action="store_true")
    q = ex.add_parser("sql")
    q.add_argument("consulta")
    q.add_argument("--max", type=positivo, default=200)
    q.add_argument("--json", action="store_true")
    p = sub.add_parser("consultar", help="pasa los argumentos a consultar.py (CLI existente, sin cambios)")
    p.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    rutas = Rutas()
    como_json = getattr(args, "json", False)
    try:
        if args.cmd == "consultar":
            import consultar
            sys.argv = ["consultar.py", *args.args]
            consultar.main()
            return 0
        if args.cmd == "construir":
            r = construir(rutas, Ollama(), solo_lexico=args.solo_lexico, forzar=args.forzar, lote=args.lote)
            print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
            return 0
        if args.cmd == "estado":
            r = estado(rutas, Ollama(), verificar=args.verificar)
            if not como_json:
                imprimir_estado(r)
                return 0
        elif args.cmd == "buscar":
            filtros = Filtros(args.coleccion, args.pieza, args.feature, args.vigencia, args.tipo_fuente, args.documento,
                              args.estado_hallazgo)
            r = buscar(rutas, args.consulta, args.modo, filtros, args.n, args.por_fuente, Ollama(), args.fts)
            if not como_json:
                imprimir_busqueda(r)
                return 0
        elif args.cmd == "ver":
            r = ver(rutas, args.id, args.contexto)
        elif args.exacto == "medidas":
            r = exacto_medidas(rutas, args.pieza, args.documento, args.cota, args.hoja, args.cavidad, args.max)
        elif args.exacto == "celdas":
            r = exacto_celdas(rutas, args.documento, args.hoja, args.filas, args.max)
        elif args.exacto == "hallazgo":
            r = exacto_hallazgo(rutas, args.id, args.comprobar)
        else:
            r = exacto_sql(rutas, args.consulta, args.max)
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return 0
    except RagError as error:
        mensaje = str(error)
        if isinstance(error, EmbeddingsNoDisponibles) and args.cmd == "construir":
            mensaje += ". Arrancar Ollama con embeddinggemma o construir con --solo-lexico (busqueda solo literal)."
        if como_json:
            print(json.dumps({"error": error.codigo, "mensaje": mensaje, **({"detalle": error.detalle} if error.detalle else {})},
                             ensure_ascii=False, indent=2))
        else:
            print(f"ERROR {error.codigo}: {mensaje}", file=sys.stderr)
            for c in (error.detalle or {}).get("candidatos", []):
                print(f"  {c['id']:>6}  {c['ruta']}  ({c['estado']})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
