"""Servidor MCP (stdio) que da al asistente las funciones de `conocimiento/herramientas/rag.py`.

Claude Code lo arranca una vez por sesión (`--mcp-config`) y lo mantiene vivo: el índice, el glosario y el modelo de
Ollama quedan cargados, y cada búsqueda tarda menos de un segundo. Llamando a `rag.py` por la consola Bash del
asistente tardaba 30–150 s por llamada (medido el 12/11/2026).

Solo lectura: son las mismas funciones que la CLI de `rag.py`, que nunca escriben en la biblioteca ni abren Exemples.
JSON-RPC por líneas, sin dependencias (no hace falta el paquete `mcp`). Se ejecuta con `conocimiento/.venv`.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "conocimiento" / "herramientas"))
SALIDA = sys.stdout.buffer        # canal del protocolo; cualquier print de rag va a stderr
sys.stdout = sys.stderr
import rag  # noqa: E402

MAX_CARACTERES = 40_000           # un resultado mayor se recorta con aviso, para no llenar el contexto
RUTAS = rag.Rutas()
EMBEDDER = rag.Ollama()
COLECCIONES = list(rag.COLECCIONES)


def _texto(v: dict | list) -> str:
    t = json.dumps(v, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(t) > MAX_CARACTERES:
        t = t[:MAX_CARACTERES] + f'… [recortado: {len(t)} caracteres; afina los filtros o baja "max"/"n"]'
    return t


def _buscar(a: dict) -> dict:
    filtros = rag.Filtros(colecciones=a.get("colecciones") or [], pieza=a.get("pieza"), feature=a.get("feature"),
                          vigencia=a.get("vigencia") or [], documento=a.get("documento"))
    r = rag.buscar(RUTAS, a["consulta"], a.get("modo", "hibrido"), filtros, a.get("n", 8), a.get("por_fuente", 3), EMBEDDER)
    for x in r.get("resultados", []):  # campos de control que no ayudan a responder
        for k in ("sha_fragmento", "indexado", "clasificacion"):
            x.pop(k, None)
    return r


HERRAMIENTAS = {
    "buscar": (
        "Búsqueda híbrida (semántica + literal) en conocimiento/, docs/, hallazgos e incidencias, y la biblioteca de los "
        "ficheros de Exemples. Devuelve fragmentos con `ruta` y `localizador` para citar, y su `id` para `ver`. "
        "Úsala primero. No es un inventario: para cifras usa medidas, cadena, celdas o sql. Los N-numbers son locales "
        "a cada plano: filtra por pieza.",
        {"consulta": {"type": "string", "description": "Texto libre; en castellano se amplía con un glosario"},
         "pieza": {"type": "string", "description": "Código de 4 cifras, p. ej. 3212"},
         "feature": {"type": "string", "description": "Número o nombre del feature, p. ej. 0 o «Bolt Eye»"},
         "colecciones": {"type": "array", "items": {"type": "string", "enum": COLECCIONES}},
         "vigencia": {"type": "array", "items": {"type": "string", "enum": list(rag.FACTOR_VIGENCIA)}},
         "documento": {"type": "integer", "description": "id de documento de la biblioteca"},
         "n": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Resultados (por defecto 8)"}},
        ["consulta"], _buscar),
    "ver": (
        "Fragmento completo de un resultado de `buscar`, con sus vecinos y otras apariciones.",
        {"id": {"type": "string"}, "contexto": {"type": "integer", "minimum": 0, "maximum": 5}},
        ["id"], lambda a: rag.ver(RUTAS, a["id"], a.get("contexto", 2))),
    "medidas": (
        "Medidas exactas de la biblioteca (informes DR y CSV de la CMM) por pieza, documento, cota, hoja o cavidad.",
        {"pieza": {"type": "string"}, "documento": {"type": "string"}, "cota": {"type": "string", "description": "p. ej. N170"},
         "hoja": {"type": "string"}, "cavidad": {"type": "string"}, "max": {"type": "integer", "minimum": 1, "maximum": 500}},
        [], lambda a: rag.exacto_medidas(RUTAS, a.get("pieza"), a.get("documento"), a.get("cota"), a.get("hoja"),
                                         a.get("cavidad"), a.get("max", 200))),
    "cadena": (
        "Qué pasó con una cota tras cada corrección de molde: muestreo de origen y de validación (secuencia, no causa).",
        {"pieza": {"type": "string"}, "cota": {"type": "string"}, "max": {"type": "integer", "minimum": 1, "maximum": 500}},
        ["pieza"], lambda a: rag.exacto_cadena(RUTAS, a["pieza"], a.get("cota"), a.get("max", 200))),
    "hallazgo": (
        "Una incidencia o hallazgo por su id (I-003, H-…), con su evidencia.",
        {"id": {"type": "string"}, "comprobar": {"type": "boolean"}},
        ["id"], lambda a: rag.exacto_hallazgo(RUTAS, a["id"], a.get("comprobar", False))),
    "celdas": (
        "Celdas literales de una hoja de cálculo de la biblioteca (id o ruta del documento), con fórmulas si las hay.",
        {"documento": {"type": "string"}, "hoja": {"type": "string"}, "filas": {"type": "string", "description": "p. ej. 10-40"},
         "max": {"type": "integer", "minimum": 1, "maximum": 500}},
        ["documento"], lambda a: rag.exacto_celdas(RUTAS, a["documento"], a.get("hoja"), a.get("filas"), a.get("max", 300))),
    "sql": (
        "SELECT de solo lectura sobre biblioteca.sqlite (recuentos, listas). Esquema: SELECT name, sql FROM sqlite_master.",
        {"consulta": {"type": "string"}, "max": {"type": "integer", "minimum": 1, "maximum": 500}},
        ["consulta"], lambda a: rag.exacto_sql(RUTAS, a["consulta"], a.get("max", 200))),
}


def _lista() -> dict:
    return {"tools": [{"name": n, "description": d, "annotations": {"readOnlyHint": True},
                       "inputSchema": {"type": "object", "properties": p, "required": r}}
                      for n, (d, p, r, _) in HERRAMIENTAS.items()]}


def _llamar(nombre: str, args: dict) -> dict:
    if nombre not in HERRAMIENTAS:
        return {"content": [{"type": "text", "text": f"Herramienta desconocida: {nombre}"}], "isError": True}
    try:
        return {"content": [{"type": "text", "text": _texto(HERRAMIENTAS[nombre][3](args or {}))}], "isError": False}
    except rag.RagError as e:
        error = {"error": e.codigo, "mensaje": str(e), **({"detalle": e.detalle} if e.detalle else {})}
        return {"content": [{"type": "text", "text": _texto(error)}], "isError": True}
    except Exception as e:  # noqa: BLE001 - el asistente debe ver el fallo, no perder la conexión
        return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}


def _enviar(m: dict) -> None:
    SALIDA.write(json.dumps(m, ensure_ascii=False).encode("utf-8") + b"\n")
    SALIDA.flush()


def _calentar() -> None:
    """Carga índice, glosario y modelo de Ollama mientras Claude arranca: la primera pregunta ya va rápida."""
    try:
        rag.buscar(RUTAS, "calentamiento", "hibrido", rag.Filtros(), 1, 1, EMBEDDER)
    except Exception as e:  # noqa: BLE001
        print(f"calentamiento fallido: {e}", file=sys.stderr)


def main() -> None:
    threading.Thread(target=_calentar, daemon=True).start()
    for linea in sys.stdin.buffer:
        if not linea.strip():
            continue
        m = json.loads(linea)
        metodo, ident = m.get("method"), m.get("id")
        if ident is None:          # notificación (initialized, cancelled…): sin respuesta
            continue
        if metodo == "initialize":
            version = (m.get("params") or {}).get("protocolVersion", "2025-06-18")
            res = {"protocolVersion": version, "capabilities": {"tools": {}},
                   "serverInfo": {"name": "conocimiento", "version": "1"}}
        elif metodo == "tools/list":
            res = _lista()
        elif metodo == "tools/call":
            p = m.get("params") or {}
            res = _llamar(p.get("name"), p.get("arguments"))
        elif metodo == "ping":
            res = {}
        else:
            _enviar({"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"Método no soportado: {metodo}"}})
            continue
        _enviar({"jsonrpc": "2.0", "id": ident, "result": res})


if __name__ == "__main__":
    main()
