"""Visor de `conocimiento/`: planos, piezas, grafo, esquema y revisión de enlaces.

Prototipo personal, no forma parte de la aplicación web. Lee la biblioteca en solo lectura y, como
única excepción, los PDF de plano originales para dibujarlos (comprobando antes OneDrive).

    python app.py                 # http://127.0.0.1:8765 (abre el navegador)
    python app.py --puerto 8800 --no-abrir
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import threading
import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402
import errores  # noqa: E402
import evolucion  # noqa: E402
import grafo  # noqa: E402
import revision  # noqa: E402

AQUI = Path(__file__).resolve().parent
app = FastAPI(title="Visor de conocimiento")


class SinCache(StaticFiles):
    """El navegador pregunta siempre si ha cambiado (304 si no): sin esto, tras tocar app.js seguía con la versión
    vieja contra la API nueva («Cannot read properties of undefined (reading 'map')», 09/11/2026)."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


app.mount("/static", SinCache(directory=AQUI / "static"), name="static")
# Capturas ya hechas por miniaturas_cad.py: el visor no lee STEP.
app.mount("/cad", StaticFiles(directory=datos.MINIATURAS, check_dir=False), name="cad")


@app.get("/")
def inicio():
    """Cada fichero de `static/` se pide con su fecha de modificación (`app.js?v=…`): al cambiar, la dirección es otra y
    el navegador no puede reutilizar la copia vieja, ni siquiera la guardada antes de `SinCache`."""
    estaticos = AQUI / "static"
    html = re.sub(r'"/static/([^"?]+)"', lambda m: f'"/static/{m[1]}?v={(estaticos / m[1]).stat().st_mtime_ns}"',
                  (estaticos / "index.html").read_text(encoding="utf-8"))
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- planos

@app.get("/api/planos")
def planos():
    return {"planos": datos.planos()}


@app.get("/api/plano/{doc}")
def plano(doc: int):
    p = datos.plano(doc)
    if not p:
        raise HTTPException(404, "No es un plano de la biblioteca")
    c = datos.con()
    local, estado = datos.estado_onedrive(p["ruta"])
    pags = [{k: v for k, v in x.items() if k != "texto"} | {"caracteres": len(x["texto"])} for x in datos.paginas(c, doc)]
    return {**p, "local": local, "onedrive": estado, "detalle_paginas": pags, "original": datos.original(p["ruta"])}


@app.get("/api/plano/{doc}/{pagina}/{tipo}.jpg")
def imagen(doc: int, pagina: int, tipo: str):
    if tipo not in ("mini", "grande"):
        raise HTTPException(404)
    path = datos.imagen(doc, pagina, tipo)
    if not path:
        p = datos.plano(doc)
        motivo = datos.estado_onedrive(p["ruta"])[1] if p else "no existe"
        raise HTTPException(409, motivo)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})


@app.get("/api/plano/{doc}/{pagina}/globos")
def globos(doc: int, pagina: int):
    return datos.globos(doc, pagina)


@app.get("/api/plano/{doc}/buscar")
def buscar_plano(doc: int, q: str = ""):
    if not datos.plano(doc):
        raise HTTPException(404)
    return datos.buscar_en_plano(doc, q)


# ---------------------------------------------------------------- piezas

@app.get("/api/piezas")
def piezas():
    return {"piezas": datos.piezas(), "tags": datos.TAGS_PIEZA, "familias": datos.FAMILIAS}


@app.get("/api/pieza/{codigo}")
def pieza(codigo: str):
    if not any(p["codigo"] == codigo for p in datos.piezas()):
        raise HTTPException(404)
    return datos.pieza(codigo)


@app.get("/api/pieza/{codigo}/ficheros")
def ficheros_de_pieza(codigo: str):
    """Desglose por carpeta de la columna «Ficheros» de Números."""
    if not any(p["codigo"] == codigo for p in datos.piezas()):
        raise HTTPException(404)
    return datos.ficheros(codigo)


@app.get("/api/pieza/{codigo}/cota")
def cota(codigo: str, c: str = Query(...), hoja: str | None = None, elemento: str | None = None, componente: str | None = None):
    # La cabecera y la gráfica tienen que ser del mismo componente.
    s = evolucion.serie(codigo, c, hoja, elemento, componente)
    return {"info": datos.resumen_cota(codigo, c, s["componente"]), **s}


# ---------------------------------------------------------------- errores

@app.get("/api/errores")
def api_errores():
    return errores.lista()


@app.get("/api/errores/generales")
def api_errores_generales(pieza: str | None = None):
    """Con `pieza`, solo las generales que le afectan."""
    if pieza and pieza not in errores.catalogo():
        raise HTTPException(404)
    return errores.generales(pieza)


@app.get("/api/errores/pieza/{codigo}")
def api_errores_pieza(codigo: str):
    if codigo not in errores.catalogo():
        raise HTTPException(404)
    return errores.de_pieza(codigo)


@app.get("/api/revision/referencias")
def api_referencias():
    """Casos de referencia de los lectores y observaciones de estructura y formato."""
    return errores.tecnicos()


# ---------------------------------------------------------------- grafo, revisión, esquema

@app.get("/api/grafo")
def api_grafo():
    return grafo.construir()


@app.get("/api/grafo/piezas")
def grafo_piezas():
    return grafo.piezas_y_features()


@app.get("/api/nodo")
def nodo(id: str):
    return grafo.contenido(id)


_revision: dict = {}


@app.get("/api/revision")
def api_revision(recalcular: bool = False):
    fichero = datos.OUT / "revision.json"
    if recalcular or not _revision:
        guardado = json.loads(fichero.read_text(encoding="utf-8")) if fichero.is_file() and not recalcular else None
        # Un fichero anterior solo tiene una muestra de los casos: se rehace.
        if guardado and all("casos" in x for x in guardado["comprobaciones"]):
            _revision.update(guardado)
        else:
            r = revision.revisar()
            datos.OUT.mkdir(parents=True, exist_ok=True)
            fichero.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            (datos.OUT / "revision.md").write_text(revision.markdown(r), encoding="utf-8")
            _revision.clear()
            _revision.update(json.loads(json.dumps(r, default=str)))
    return JSONResponse(_revision)


# Relaciones lógicas (la biblioteca no declara claves ajenas salvo en documento).
RELACIONES = [
    ("documento", "elemento", "documento_id"), ("documento", "celda", "documento_id"),
    ("documento", "celda_aleatoria", "documento_id"), ("documento", "estructura", "documento_id"),
    ("documento", "lectura_dr", "documento_id"), ("documento", "medida_dr", "documento_id"),
    ("documento", "medida_cmm", "documento_id"), ("documento", "medida_contorno", "documento_id"),
    ("documento", "perfil_ppap", "documento_id"), ("documento", "perfil_correccion", "documento_id"),
    ("documento", "globo", "documento_id (.icp)"), ("documento", "auditoria", "documento_id"),
    ("documento", "cadena_correccion", "documento_id (PPTX), origen_ y validacion_documento_id"),
    ("documento", "documento", "duplicado_de"),
]
CLAVES = {"documento": ["id", "ruta", "feature", "pieza", "codigo", "carpeta_norm", "ext", "sha256", "estado", "duplicado_de"],
          "medida_dr": ["documento_id", "hoja", "fila", "col", "cota", "cavidad", "valor", "nominal", "marca"],
          "medida_cmm": ["documento_id", "pieza", "muestreo", "cavidad", "cota", "valor"],
          "cadena_correccion": ["pieza", "cota", "documento_id", "origen_muestreo", "origen_documento_id",
                                "validacion_muestreo", "validacion_documento_id", "validacion_estado"],
          "lectura_dr": ["documento_id", "hoja", "papel", "plantilla"], "globo": ["documento_id", "sello", "etiqueta", "x1", "y1"],
          "perfil_ppap": ["documento_id", "hoja", "pieza", "metadatos"], "perfil_correccion": ["documento_id", "diapositiva", "pieza", "cotas"],
          "celda": ["documento_id", "hoja", "fila", "col", "valor", "formula"], "celda_aleatoria": ["documento_id", "hoja", "fila", "col", "formula"],
          "elemento": ["id", "documento_id", "tipo", "localizador", "texto"], "estructura": ["documento_id", "clave", "valor"],
          "medida_contorno": ["documento_id", "pieza", "muestreo", "perfil"], "auditoria": ["documento_id", "comprobacion", "ok"]}


@app.get("/api/esquema")
def esquema():
    c = datos.con()
    tablas = []
    for (nombre,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'"
                               " AND name NOT LIKE '%fts%' ORDER BY name"):
        columnas = [r[1] for r in c.execute(f"PRAGMA table_info({nombre})")]
        filas = c.execute(f"SELECT count(*) FROM {nombre}").fetchone()[0]
        tablas.append({"nombre": nombre, "filas": filas, "columnas": columnas})
    er = ["erDiagram"]
    for t in tablas:
        cols = CLAVES.get(t["nombre"], t["columnas"][:6])
        er.append(f"  {t['nombre']} {{")
        er += [f"    x {col}" for col in cols if col in t["columnas"]]
        er.append("  }")
    for a, b, via in RELACIONES:
        if any(t["nombre"] == b for t in tablas):
            er.append(f'  {a} ||--o{{ {b} : "{via}"')
    rag = []
    indice = datos.CONOCIMIENTO / "datos" / "rag" / "indice.sqlite"
    if indice.is_file():
        r = sqlite3.connect(f"file:{indice.as_posix()}?mode=ro", uri=True)
        for (nombre,) in r.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'"
                                   " AND name NOT LIKE '%fts%_%' ORDER BY name"):
            try:
                rag.append({"nombre": nombre, "filas": r.execute(f'SELECT count(*) FROM "{nombre}"').fetchone()[0]})
            except sqlite3.Error:
                pass
        r.close()  # no dejar el índice abierto: rag.py construir tiene que poder sustituirlo
    ficheros = []
    for patron in ("*.jsonl", "datos/aceptacion/*.jsonl", "rag/*.jsonl", "rag/*.json"):
        for f in sorted(datos.CONOCIMIENTO.glob(patron)):
            lineas = sum(1 for x in f.read_text(encoding="utf-8").splitlines() if x.strip()) if f.suffix == ".jsonl" else None
            ficheros.append({"ruta": f.relative_to(datos.CONOCIMIENTO).as_posix(), "lineas": lineas, "bytes": f.stat().st_size})
    return {"tablas": tablas, "er": "\n".join(er), "rag": rag, "ficheros": ficheros,
            "md": len(grafo.ficheros_md())}


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--puerto", type=int, default=8765)
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()
    if not datos.BD.is_file():
        sys.exit(f"No está la biblioteca: {datos.BD}")
    url = f"http://127.0.0.1:{args.puerto}"
    if not args.no_abrir:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Visor de conocimiento en {url}  (Ctrl+C para parar)")
    uvicorn.run(app, host="127.0.0.1", port=args.puerto, log_level="warning")


if __name__ == "__main__":
    main()
