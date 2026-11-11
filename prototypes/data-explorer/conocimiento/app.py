"""Visor de `conocimiento/`: planos, piezas (con su grafo) y errores.

La revisión de enlaces pieza ↔ muestreo (`revision.py`) se ejecuta desde la consola; su pestaña se quitó el 11/11/2026
(destino de cada comprobación en `conocimiento/revision-comprobaciones.md`).

Prototipo personal, no forma parte de la aplicación web. Lee la biblioteca en solo lectura y, como
única excepción, los PDF de plano originales para dibujarlos (comprobando antes OneDrive).

    python app.py                 # http://127.0.0.1:8765 (abre el navegador)
    python app.py --puerto 8800 --no-abrir
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402
import errores  # noqa: E402
import evolucion  # noqa: E402
import grafo  # noqa: E402

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
    con_datos = evolucion.datos_de_planos()  # tag «Cotas con / sin datos»
    return {"planos": [{**p, **con_datos.get(p["id"], {})} for p in datos.planos()]}


@app.get("/api/plano/{doc}")
def plano(doc: int):
    p = datos.plano(doc)
    if not p:
        raise HTTPException(404, "No es un plano de la biblioteca")
    c = datos.con()
    local, estado = datos.estado_onedrive(p["ruta"])
    pags = [{k: v for k, v in x.items() if k != "texto"} | {"caracteres": len(x["texto"])} for x in datos.paginas(c, doc)]
    return {**p, **evolucion.datos_de_planos().get(doc, {}), "local": local, "onedrive": estado, "detalle_paginas": pags,
            "original": datos.original(p["ruta"])}


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


@app.get("/api/plano/{doc}/cotas-con-datos")
def cotas_con_datos(doc: int):
    """Para «Marcar cotas con datos»: qué números del plano tienen algo en su ficha (medidas o correcciones)."""
    p = datos.plano(doc)
    if not p:
        raise HTTPException(404)
    if not p["codigo"]:
        return {"cotas": [], "pieza_con_datos": False}
    # El plano de una pieza del libro (3288) mira esa pieza; el del conjunto, cualquiera de las dos, como su ficha.
    componente = p["componente"] if p["componente"] in datos.COMPONENTES.get(p["codigo"], {}) else None
    return evolucion.cotas_con_datos(p["codigo"], componente)


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
    return {"info": {**datos.resumen_cota(codigo, c, s["componente"]), "csv": evolucion.resumen_csv(codigo, c)}, **s}


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


# ---------------------------------------------------------------- grafo de piezas

@app.get("/api/grafo/piezas")
def grafo_piezas():
    return grafo.piezas_y_features()


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
    # El tag de datos de los 56 planos tarda unos segundos: se calcula ya, mientras se abre el navegador.
    threading.Thread(target=evolucion.datos_de_planos, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=args.puerto, log_level="warning")


if __name__ == "__main__":
    main()
