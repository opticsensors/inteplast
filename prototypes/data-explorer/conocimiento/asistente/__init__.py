"""Pestaña «Asistente» del visor: chat con Claude Haiku 5.5 sobre `conocimiento/` y `docs/` (demo, 12/11/2026).

Módulo autocontenido; ver README.md de esta carpeta.

- Usar en una app FastAPI:  `import asistente; asistente.instalar(app)`  y en el HTML
  `<script src="/asistente/asistente.js"></script>` (la pestaña se añade sola al menú).
- Quitarlo: borrar esta carpeta, esas dos líneas de `app.py` y el `<script>` de `static/index.html`.
- Solo Python, sin web: `from asistente.sesion import SesionClaude`.
"""

from .rutas import instalar, router, sesion
from .sesion import Config, SesionClaude

__all__ = ["instalar", "router", "sesion", "Config", "SesionClaude"]
