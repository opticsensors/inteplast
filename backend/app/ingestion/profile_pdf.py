"""Profile report tables and source images; missing measurements remain unknown."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any

import fitz

from app.ingestion.cmm import sample_number

logger = logging.getLogger(__name__)


def cavity_number(ruta: Path) -> str | None:
    """Los PA/PB siempre viven dentro de la carpeta de su cavidad: c13/, C13/..."""
    for texto in (ruta.parent.name, ruta.stem):
        m = re.search(r"[cC](?:av)?[._\s]?(\d{2})", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
        m = re.search(r"^(\d{2})[_\s]", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
    return None


def discover(raiz: Path) -> list[dict[str, Any]]:
    ficheros = []
    for ruta in raiz.rglob("*.pdf"):
        m = re.match(r"^P([AB])_(\d+)$", ruta.stem)
        if not m:
            continue
        cavidad = cavity_number(ruta)
        if cavidad is None:
            logger.info(f"  [aviso] no se deduce la cavidad, se salta: {ruta}")
            continue
        ficheros.append(
            {
                "ruta": ruta,
                "muestreo": sample_number(ruta),
                "cavidad": cavidad,
                "perfil": m.group(1),
                "indice": int(m.group(2)),
                "rel": ruta.relative_to(raiz.parent).as_posix(),
            }
        )
    return sorted(
        ficheros, key=lambda f: (f["muestreo"], f["cavidad"], f["perfil"], f["indice"])
    )


def rows_by_y(pagina: Any, tolerancia: float = 3.0) -> list[str]:
    """Reconstruye las filas visuales de la tabla agrupando las palabras por su
    coordenada Y. Hace falta porque la tabla del PDF son celdas independientes: los
    bloques de texto de PyMuPDF no las agrupan por fila."""
    palabras = sorted(pagina.get_text("words"), key=lambda w: (w[1], w[0]))
    filas, actual, y_ref = [], [], None
    for x0, y0, _, _, palabra, *_ in palabras:
        if y_ref is None or abs(y0 - y_ref) <= tolerancia:
            actual.append((x0, palabra))
            y_ref = y0 if y_ref is None else y_ref
        else:
            filas.append(sorted(actual))
            actual, y_ref = [(x0, palabra)], y0
    if actual:
        filas.append(sorted(actual))
    return [" ".join(p for _, p in f) for f in filas]


def parse_float(texto: str) -> float | None:
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def read_pdf(
    ruta: Path, destino_img: Path, zoom: float, nombre_base: str
) -> dict[str, Any]:
    """Saca los 6 numeros de la tabla y renderiza la pagina a PNG.

    `nombre_base` tiene que identificar muestreo + cavidad + elemento: los 144 PDF se
    llaman solo PA_1..PB_6 y, si el nombre del PNG no lleva el muestreo, los de un
    muestreo sobrescriben a los de otro y cada pagina acaba mostrando la grafica de
    otra tanda.
    """
    doc = fitz.open(ruta)
    pagina = doc[0]
    filas = rows_by_y(pagina)
    datos: dict[str, Any] = {"fichero": ruta.name}

    for fila in filas:
        # 'Contorno (21) -0.025 -0.242 -0.217'
        m = re.match(r"Contorno \((\d+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", fila)
        if m:
            datos.update(
                contorno=m.group(1),
                tol_inf=parse_float(m.group(2)),
                desv_inf=parse_float(m.group(3)),
                infr_inf=parse_float(m.group(4)),
            )
        # 'CONTORN (10) 0.025 -0.038 0.000'
        m = re.match(r"CONTORN \((\d+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", fila)
        if m:
            datos.update(
                nominal=m.group(1),
                tol_sup=parse_float(m.group(2)),
                desv_sup=parse_float(m.group(3)),
                infr_sup=parse_float(m.group(4)),
            )
        m = re.match(r"YZ\(X\)\s+(-?[\d.]+)", fila)
        if m:
            datos["media"] = parse_float(m.group(1))
        m = re.match(r"Tolerancia:([\d.]+)", fila)
        if m:
            datos["banda"] = parse_float(m.group(1))
        m = re.search(r"(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2})", fila)
        if m:
            datos["hora"] = m.group(2)
        if fila.startswith("PERFIL_"):
            datos["perfil_nombre"] = fila.strip()

    texto = pagina.get_text()
    m = re.search(r"LD=(-?[\d.]+)", texto)
    datos["ld"] = parse_float(m.group(1)) if m else None

    nombre_png = re.sub(r"[^A-Za-z0-9._-]", "_", f"{nombre_base}.png")
    pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    pix.save(destino_img / nombre_png)
    datos["png"] = nombre_png
    doc.close()
    return datos


def measurement_errors(d: dict[str, Any]) -> list[str]:
    """No confundir una celda ausente/ilegible con un cero medido."""
    campos = ("tol_inf", "tol_sup", "desv_inf", "desv_sup", "infr_inf", "infr_sup")
    errores = [
        f"{campo} ausente o invalido"
        for campo in campos
        if not isinstance(d.get(campo), (int, float)) or not math.isfinite(d[campo])
    ]
    if not errores and d["tol_inf"] > d["tol_sup"]:
        errores.append("limites de tolerancia invertidos")
    return errores


def worst_excess(d: dict[str, Any]) -> float | None:
    if measurement_errors(d):
        return None
    return max(abs(float(d["infr_inf"])), abs(float(d["infr_sup"])))


def profile_crop(page: Any) -> fitz.Rect:
    """Locate the plot's white vector frame, not a pixel crop of the full-page thumbnail."""
    frames = [
        d["rect"]
        for d in page.get_drawings()
        if d.get("fill")
        and min(d["fill"]) > 0.98
        and d["rect"].width > 0.6 * page.rect.width
        and 0.2 * page.rect.height < d["rect"].height < 0.6 * page.rect.height
    ]
    if len(frames) != 1:
        raise ValueError(
            f"No se identifica de forma única el marco del perfil: {len(frames)} candidatos"
        )
    r = frames[0]
    return fitz.Rect(r.x0 - 8, r.y0 - 8, r.x1 + 8, r.y1 + 8) & page.rect
