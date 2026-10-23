"""Rutas, conexion y clasificacion comunes de la biblioteca de Exemples.

Solo lee Exemples. Nunca escribe, mueve ni renombra un original.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

AQUI = Path(__file__).resolve().parent
CONOCIMIENTO = AQUI.parent
EXEMPLES = Path(
    os.environ.get(
        "INTEPLAST_EXEMPLES",
        r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples",
    )
)
DATOS = CONOCIMIENTO / "datos"
BD = DATOS / "biblioteca.sqlite"

# Atributos de Windows de un placeholder de OneDrive (Files On-Demand).
NUBE = 0x400000 | 0x40000 | 0x1000


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conectar() -> sqlite3.Connection:
    """Diario clasico (no WAL): la carpeta esta en OneDrive y no debe quedar un -wal suelto."""
    DATOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BD, timeout=30)
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript((AQUI / "esquema.sql").read_text(encoding="utf-8"))
    return con


def registrar(con: sqlite3.Connection, herramienta: str, parametros: dict) -> int:
    cur = con.execute(
        "INSERT INTO ejecucion(herramienta, parametros, inicio) VALUES (?,?,?)",
        (herramienta, json.dumps(parametros, ensure_ascii=False), ahora()),
    )
    con.commit()
    return int(cur.lastrowid or 0)


def cerrar_registro(con: sqlite3.Connection, ejecucion: int, resumen: dict) -> None:
    con.execute(
        "UPDATE ejecucion SET fin=?, resumen=? WHERE id=?",
        (ahora(), json.dumps(resumen, ensure_ascii=False), ejecucion),
    )
    con.commit()


def carpeta_normalizada(nombre: str) -> str:
    """Los dos esqueletos de carpetas (3212: 8 carpetas; entregas 2026-10: 7) en un vocabulario."""
    t = nombre.casefold()
    if "moldflow" in t:
        return "moldflow"
    if "retoq" in t:
        return "retoques"
    if "metrolog" in t:
        return "metrologia"
    if re.search(r"m[eéè]tod", t):
        return "metodo_medida"
    if "stl" in t or "real" in t:
        return "stl_real"
    if "molde" in t or "mold" in t:
        return "molde"
    if "2d" in t or "3d" in t:
        return "pieza_2d3d"
    return "otro"


def clasificar(ruta: str) -> dict:
    """feature / grupo / pieza / carpeta a partir de la ruta relativa a Exemples."""
    partes = PurePosixPath(ruta).parts
    info = {"feature": partes[0] if len(partes) > 1 else None, "grupo": None,
            "pieza": None, "codigo": None, "carpeta": None, "carpeta_norm": "raiz"}
    resto = list(partes[1:-1])  # carpetas entre el feature y el fichero
    if resto and re.match(r"tipo\b", resto[0], re.I):
        info["grupo"] = resto.pop(0)
    if resto:
        info["pieza"] = resto.pop(0)
        codigo = re.match(r"\d+", info["pieza"])
        info["codigo"] = codigo[0] if codigo else None
    if resto:
        info["carpeta"] = resto[0]
        info["carpeta_norm"] = carpeta_normalizada(resto[0])
    return info


def ruta_relativa(path: Path) -> str:
    return path.relative_to(EXEMPLES).as_posix()


def larga(path: Path | str) -> str:
    """Ruta utilizable aunque supere los 260 caracteres de Windows (hay rutas de WhatsApp asi)."""
    texto = os.path.abspath(str(path))
    if os.name == "nt" and not texto.startswith("\\\\?\\"):
        return "\\\\?\\" + texto
    return texto


def original(ruta: str) -> str:
    """Ruta larga del original a partir de su ruta relativa en la biblioteca."""
    return larga(EXEMPLES / PurePosixPath(ruta))
