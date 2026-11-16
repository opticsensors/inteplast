"""Rutas web del asistente: `/api/asistente/*` y la interfaz en `/asistente/*`.

Una sola conversación para todo el servidor: el visor lo usa una persona en su equipo.
"""

from __future__ import annotations

import atexit
import json
import threading
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .sesion import Ocupada, SesionClaude
from .sesion import _claude as claude

AQUI = Path(__file__).resolve().parent
sesion = SesionClaude()
router = APIRouter(prefix="/api/asistente", tags=["asistente"])


class Pregunta(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


@router.get("/estado")
def estado():
    return sesion.estado()


@router.post("/preparar")
def preparar():
    """Al abrir la pestaña: arranca Claude y su servidor de herramientas para que la primera pregunta no espere."""
    try:
        claude()  # comprobación rápida aquí: un fallo dentro del hilo no llegaría a la interfaz
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    threading.Thread(target=sesion.preparar, daemon=True).start()
    return sesion.estado()


@router.post("/preguntar")
def preguntar(p: Pregunta):
    if sesion.ocupada:
        raise HTTPException(409, "Ya hay una pregunta en curso")

    def lineas():
        try:
            for evento in sesion.preguntar(p.texto.strip()):
                yield json.dumps(evento, ensure_ascii=False) + "\n"
        except Ocupada:
            yield json.dumps({"tipo": "error", "texto": "Ya hay una pregunta en curso"}, ensure_ascii=False) + "\n"
        except FileNotFoundError as e:
            yield json.dumps({"tipo": "error", "texto": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(lineas(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


@router.post("/parar")
def parar():
    sesion.parar()
    return sesion.estado()


@router.post("/nueva")
def nueva():
    sesion.nueva()
    return sesion.estado()


class _SinCache(StaticFiles):
    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


def instalar(app: FastAPI) -> None:
    """Todo lo que el programa anfitrión necesita: rutas, ficheros de la interfaz y cierre del proceso al salir."""
    app.include_router(router)
    app.mount("/asistente", _SinCache(directory=AQUI / "static"), name="asistente")
    atexit.register(sesion.cerrar)
