"""Lectores de planos del prototipo: un solo código para el visor de `conocimiento/` y los scripts de medida.

Qué hay aquí. Todo son lecturas automáticas: pueden fallar sin avisar y no sustituyen a un `.icp`.

- **Globos de color** (verdes o azules). Se detectan en la capa vectorial si el PDF los trae como
  vectores (infra-CONVERT) y, si no, en la imagen; la fuente se decide globo a globo. Se elige la
  orientación de la página y se leen con el lector combinado: RapidOCR (tres vistas) y el lector
  propio (una CRNN entrenada solo con números sintéticos en entrenar_lector_globos.py, perfil
  «general», exportada a ONNX) votan con su puntuación. Después, cada número se asigna a un solo
  globo del plano y solo se ofrece la lectura que llega al umbral de la fuente de ese globo.
- **Marcas `[]210` y `No. 200`**: OCR por teselas del plano muy ampliado, en horizontal y en vertical.
- **Números en recuadros**, también girados: se detecta el rectángulo y se lee solo su interior.
- **`.icp` de infra-CONVERT**: calibración sello → página con RANSAC, su aplicación, el calco 1:1 y
  la calibración de la gemela.

Lo usan el visor (`conocimiento/leer_planos.py` y `conocimiento/datos.py`), el buscador
(`buscar_en_plano.py`) y los scripts de medida (`probar_lector_planos.py`, `comparar_ocr_globos.py`,
`entrenar_lector_globos.py`, `muestra_verificacion.py`): un cambio aquí vale para todos.

Los lectores de `[]`, `No.` y recuadros se ajustaron en el 2820, el 3174, el 3186 y el 3214, los
únicos planos de Exemples con esas marcas: no tienen validación independiente.

La aplicación final no importa este fichero (CLAUDE.md): tiene su propia copia del lector de globos
en `backend/app/ingestion/` (drawing.py y balloon_reader.py), hecha a partir de este código.

Unificado el 09/11/2026 desde buscar_en_plano.py, comparar_ocr_globos.py, probar_lector_planos.py,
conocimiento/leer_planos.py y conocimiento/datos.py, sin cambiar ninguna lectura. El lector propio
pasa de torch a ONNX: en las 68 páginas de los 56 planos del visor las dos versiones daban los mismos
globos, números y puntuaciones combinadas; solo 2 puntuaciones del lector propio, de 3.373, cambiaban
en 0,0001 (out/unificar-lectores-2026-11-09/, fuera de Git; detalle en README.md).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
from functools import lru_cache
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image

AQUI = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None  # rásteres de 300–800 ppp de hasta 14.000 px de lado

# Sube cuando cambia lo que lee cualquiera de los lectores: invalida las lecturas guardadas del visor
# y el índice del buscador.
VERSION = 1

# Lector propio: exportación ONNX del perfil «general». Se obtiene con
#   entrenar_lector_globos.py --perfil general --exportar-onnx out/lector-globos/general/lector_globos.onnx
# Fuera de Git, como el modelo torch del que sale. Es el mismo fichero que lleva la aplicación final.
MODELO = AQUI / "out" / "lector-globos" / "general" / "lector_globos.onnx"

# Calibración .icp → página que guarda probar_lector_planos.py y lee el visor.
CALIBRACION = AQUI / "out" / "probar-planos-calibracion.json"


# ================================================================ identificadores

def normalize_number(text: str) -> str | None:
    """Keep complete identifiers, including suffixes. Never guess a different digit."""
    text = text.upper().strip().replace(",", ".")
    match = re.fullmatch(r"N?\s*(\d{1,4})(?:\s*\.\s*(\d{1,2}|T))?", text)
    if not match:
        return None
    return "N" + str(int(match[1])) + ("." + match[2] if match[2] else "")


def ocr_number(text: str) -> str | None:
    # Only discard punctuation around the word, not ambiguous letters/digits inside it.
    return normalize_number(text.strip(" \t\r\n[](){}|:;!"))


def label_of(text: str) -> str | None:
    return ocr_number(text.replace(" ", ""))


def normalized_box(rect, width: float, height: float) -> list[float]:
    x0, y0, x1, y1 = rect
    return [round(max(0., min(1., v / size)), 7)
            for v, size in zip((x0, y0, x1, y1), (width, height, width, height))]


# ================================================================ imagen de la página

def page_raster(page, max_side: int = 10000) -> np.ndarray:
    """Imagen para detectar y leer: la original si la página es solo un ráster; si no, un render a
    la resolución de sus imágenes (más fina que la imagen de pantalla del buscador).

    La imagen original solo se usa si es lo único que hay en la página y la ocupa entera, sin girar
    ni voltear: si hubiera trazados encima (globos vectoriales), se perderían.
    """
    images = page.get_images(full=True)
    if len(images) == 1 and not page.rotation and not page.get_text().strip():
        info = page.get_image_info()
        drawn = [d for d in page.get_drawings() if d["rect"].get_area() < .99 * page.rect.get_area()]
        if len(info) == 1 and not drawn:
            a, b, c, d, _, _ = info[0]["transform"]
            tolerance = .01 * max(page.rect.width, page.rect.height)
            if (abs(b) < 1e-6 and abs(c) < 1e-6 and a > 0 and d > 0
                    and all(abs(u - v) < tolerance for u, v in zip(info[0]["bbox"], page.rect))):
                raw = page.parent.extract_image(images[0][0])
                return np.array(Image.open(io.BytesIO(raw["image"])).convert("RGB"))
    widest = max((im[2] / max(1., r.width) * 72 for im in images for r in page.get_image_rects(im[0])), default=200)
    dpi = min(max(200., widest), 600.)
    scale = min(dpi / 72, max_side / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3).copy()


def vector_layer(pdf: Path, number: int, max_side: int = 10000, min_paths: int = 1) -> np.ndarray | None:
    """La página sin sus imágenes, si tiene imágenes y trazados de color encima; si no, None.

    En los planos de infra-CONVERT los globos son vectores sobre un escaneo: sin las imágenes
    quedan solo los globos y sus números, nítidos y sin las líneas del plano detrás.
    """
    with fitz.open(pdf) as doc:
        page = doc[number]
        images = page.get_images(full=True)
        colour = lambda c: c is not None and len(c) == 3 and max(c) - min(c) > .3
        if not images or sum(colour(d.get("color")) or colour(d.get("fill")) for d in page.get_drawings()) < min_paths:
            return None
        for image in images:
            page.delete_image(image[0])  # solo en memoria: el original no se toca
        scale = min(600 / 72, max_side / max(page.rect.width, page.rect.height))
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3).copy()


# ================================================================ globos de color: detección

def color_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = [c.astype(np.int16) for c in cv2.split(rgb)]
    green = ((g - r) > 14) & ((g - b) > 14)
    blue = ((b - r) > 40) & ((b - g) > 25)
    return np.uint8(green | blue) * 255


def detect_balloons(rgb: np.ndarray) -> list[dict]:
    """Circular annotation candidates, not whole connected clusters or known N locations."""
    height, width = rgb.shape[:2]
    factor = min(1., 3600 / max(width, height))
    small = cv2.resize(rgb, None, fx=factor, fy=factor) if factor < 1 else rgb
    mask = color_mask(small)
    if np.count_nonzero(mask) < 40:
        return []
    blurred = cv2.GaussianBlur(mask, (3, 3), .7)
    near_color = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)

    def ring_circles(min_r: float, max_r: float, min_dist: float) -> list[tuple]:
        """Círculos de Hough cuyo contorno es, al menos en un 65 %, tinta de color: un aro."""
        found = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, min_dist, param1=80, param2=17,
                                 minRadius=int(round(min_r)), maxRadius=int(round(max_r)))
        accepted = []
        for x, y, radius in ([] if found is None else found[0]):
            xs = np.clip(np.round(x + radius * np.cos(angles)).astype(int), 0, mask.shape[1] - 1)
            ys = np.clip(np.round(y + radius * np.sin(angles)).astype(int), 0, mask.shape[0] - 1)
            support = float(np.mean(near_color[ys, xs] > 0))
            if support >= .65:
                accepted.append((support, float(x), float(y), float(radius)))
        return accepted

    # Dos pasadas. Primero, en un margen amplio (0,3–3 % del lado corto: globos pequeños de escaneo
    # como el 3212 y grandes de infra-CONVERT como el 3206), se mide el tamaño típico de los globos
    # de este plano. Después se buscan solo de ese tamaño, separados al menos un radio.
    size = min(mask.shape)
    accepted = ring_circles(max(5, size * .003), max(12, size * .03), 12)
    if len(accepted) >= 5:
        # Para medir el tamaño no cuentan los círculos que caen dentro de otro: los huecos de cifras
        # como «0» o «6» también parecen aros pequeños y, en un ráster pobre, arrastran la mediana (3167).
        x, y, r = (np.array([c[i] for c in accepted]) for i in (1, 2, 3))
        distance = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
        inside = ((r[None, :] > 1.25 * r[:, None]) & (distance + r[:, None] <= 1.05 * r[None, :])).any(axis=1)
        median = float(np.median(r[~inside]))
        accepted = ring_circles(max(5, .6 * median), 1.6 * median, max(8, median))
    accepted = [(s, x / factor, y / factor, r / factor) for s, x, y, r in accepted]
    deduped = []
    for support, x, y, radius in sorted(accepted, reverse=True):
        if any(np.hypot(x - a, y - b) < .9 * min(radius, r) for _, a, b, r in deduped):
            continue
        deduped.append((support, x, y, radius))
    return [{"box": normalized_box((x - r, y - r, x + r, y + r), width, height),
             "circle": [round(x, 2), round(y, 2), round(r, 2)], "candidates": []}
            for _, x, y, r in sorted(deduped, key=lambda c: (round(c[2] / 50), c[1]))]


def pair_balloons(first: list[dict], second: list[dict]) -> list[tuple[int, int]]:
    """Parejas uno a uno entre dos listas de globos en las mismas coordenadas: (índice, índice).

    Solo valen los pares con los centros a menos de medio radio (el mayor de los dos). Entre los
    válidos se empareja del más cercano al más lejano. El límite depende de los radios de cada par,
    así que se filtra antes de ordenar: un par pequeño rechazado no impide uno grande que sí vale.
    """
    valid = sorted((distance, i, j) for i, a in enumerate(first) for j, b in enumerate(second)
                   if (distance := np.hypot(a["circle"][0] - b["circle"][0], a["circle"][1] - b["circle"][1]))
                   < .5 * max(a["circle"][2], b["circle"][2]))
    pairs, used_first, used_second = [], set(), set()
    for _, i, j in valid:
        if i not in used_first and j not in used_second:
            pairs.append((i, j))
            used_first.add(i)
            used_second.add(j)
    return pairs


def balloon_source(pdf: Path, page) -> tuple[np.ndarray, list[dict], str]:
    """Imagen de trabajo y globos de la página, con la fuente decidida globo a globo.

    Si hay capa vectorial, se detecta en ella y en la página completa dibujada al mismo tamaño
    (mismas coordenadas). Cada globo de la capa se empareja como mucho con uno de la página
    completa (centros a menos de medio radio, del par más cercano al más lejano). Los emparejados y
    los que solo están en la capa se leen en la capa, sin el plano detrás; los que solo están en la
    página completa (globos dentro del escaneo), en la página. Cada globo lleva su «fuente»
    («capa vectorial» o «imagen»). Sin capa vectorial, todo sale de la imagen original.
    """
    layer = vector_layer(pdf, page.number)
    if layer is None:
        full = page_raster(page)
        return full, [dict(b, fuente="imagen") for b in detect_balloons(full)], "imagen"
    # Cada vista se detecta a su resolución natural: la capa, hasta 600 ppp (la misma que antes del
    # 29/10/2026); la página completa, a la de su escaneo, porque ampliada a 600 ppp los globos de un
    # escaneo pobre quedan en bloques y no se detectan. Después todo pasa a la escala de la capa.
    height, width = layer.shape[:2]
    native = page_raster(page)
    sx, sy = width / native.shape[1], height / native.shape[0]
    found = [dict(b, circle=[b["circle"][0] * sx, b["circle"][1] * sy, b["circle"][2] * (sx + sy) / 2])
             for b in detect_balloons(native)]
    pix = page.get_pixmap(matrix=fitz.Matrix(width / page.rect.width, height / page.rect.height),
                          colorspace=fitz.csRGB, alpha=False)
    full = np.full_like(layer, 255)
    rendered = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    full[:min(height, pix.height), :min(width, pix.width)] = rendered[:height, :width]
    in_layer = detect_balloons(layer)
    if not in_layer:
        return full, [dict(b, fuente="imagen") for b in found], "imagen"
    matched_full = {j for _, j in pair_balloons(in_layer, found)}
    # Imagen de trabajo: la capa hasta 1,6 radios alrededor de cada globo vectorial (todo lo que leen
    # los recortes, con sus desplazamientos), salvo el interior de los globos que solo están en la
    # imagen, que se conserva.
    image_only = [b for j, b in enumerate(found) if j not in matched_full]
    use_layer = np.zeros((height, width), np.uint8)
    for group, factor, value in ((in_layer, 1.6, 1), (image_only, 1.1, 0)):
        for b in group:
            x, y, r = b["circle"]
            cv2.circle(use_layer, (round(x), round(y)), round(factor * r), value, -1)
    work = np.where(use_layer[:, :, None] > 0, layer, full)
    balloons = ([dict(b, fuente="capa vectorial") for b in in_layer]
                + [dict(b, fuente="imagen") for b in image_only])
    balloons.sort(key=lambda b: (round(b["circle"][1] / 50), b["circle"][0]))
    vector = sum(b["fuente"] == "capa vectorial" for b in balloons)
    if vector == len(balloons):
        return work, balloons, "capa vectorial"
    return work, balloons, f"mixta ({vector} de la capa vectorial, {len(balloons) - vector} de la imagen)"


def rotate(rgb: np.ndarray, balloons: list[dict], quarter_turns: int) -> tuple[np.ndarray, list[dict]]:
    """Gira la página en sentido antihorario y recoloca los círculos (copias, mismo orden)."""
    rotated = []
    for b in balloons:
        (x, y, r), width = b["circle"], rgb.shape[1]
        height = rgb.shape[0]
        for _ in range(quarter_turns):
            x, y, width, height = y, width - 1 - x, height, width
        rotated.append(dict(b, circle=[x, y, r]))
    return np.ascontiguousarray(np.rot90(rgb, quarter_turns)), rotated


# ================================================================ globos de color: recortes
# El JPEG del 3212 guarda el color a media resolución (4:2:0): la luminancia es el canal más nítido.

def luma(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)[:, :, 0]


def colour_strength(rgb: np.ndarray) -> np.ndarray:
    r, g, b = [c.astype(np.int16) for c in cv2.split(rgb)]
    return np.maximum(np.minimum(g - r, g - b), np.minimum(b - r, b - g))


def channel(rgb: np.ndarray, name: str) -> np.ndarray:
    if name == "rojo":
        return rgb[:, :, 0]
    if name == "luma":
        return luma(rgb)
    if name == "luma-color":
        # Luminancia solo donde hay tinta de color cerca: quita líneas negras del dibujo.
        near = cv2.dilate(np.uint8(colour_strength(rgb) > 12), np.ones((3, 3), np.uint8))
        return np.where(near > 0, luma(rgb), 255).astype(np.uint8)
    raise ValueError(name)


def ink_box(rgb: np.ndarray, circle) -> tuple[float, float, float, float] | None:
    """Caja del número dentro del globo: tinta oscura del interior que no toca el aro.

    Las líneas del dibujo y el propio aro cruzan el borde interior y se descartan. Sin tinta
    aislada (por ejemplo, una línea que atraviesa el número) devuelve None.
    """
    x, y, radius = round(circle[0]), round(circle[1]), circle[2]
    inner = int(radius * .82)
    if inner < 4 or y - inner < 0 or x - inner < 0:
        return None
    gray = luma(rgb[y - inner:y + inner + 1, x - inner:x + inner + 1])
    if gray.shape != (2 * inner + 1, 2 * inner + 1):
        return None
    yy, xx = np.mgrid[-inner:inner + 1, -inner:inner + 1]
    distance = np.hypot(xx, yy)
    inside = distance <= inner
    if np.median(gray[inside]) < 128:
        gray = 255 - gray
    threshold, _ = cv2.threshold(gray[inside].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = ((gray <= threshold) & inside).astype(np.uint8)  # Otsu de OpenCV: fondo = valores > umbral
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    edge = np.unique(labels[(distance >= inner - 1.5) & inside])
    keep = [i for i in range(1, count) if i not in edge and stats[i, cv2.CC_STAT_AREA] >= 2]
    if not keep:
        return None
    x0 = min(stats[i, 0] for i in keep)
    y0 = min(stats[i, 1] for i in keep)
    x1 = max(stats[i, 0] + stats[i, 2] for i in keep)
    y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
    return x - inner + x0, y - inner + y0, x - inner + x1, y - inner + y1


def text_crop(rgb: np.ndarray, circle, view: str, scale: float = 4, pad: int = 8,
              width: float = .84, height: float = .43, shift: tuple[int, int] = (0, 0),
              fit_text: bool = False) -> np.ndarray:
    """Interior del globo, sin el aro, ampliado. Devuelve gris uint8.

    La geometría por defecto es la vista «Canal rojo · interior» de `read_balloons`: un píxel más
    o menos de recorte cambia mucho el resultado de los lectores con cifras de este tamaño. Con
    `fit_text` el recorte se centra en la tinta del número y se escala a su altura (el número ocupa
    el 44 % del alto, como en el 3212), sea cual sea la proporción entre número y globo. Es también
    el recorte con el que entrenar_lector_globos.py fabrica sus imágenes sintéticas.
    """
    x, y, radius = circle
    box = ink_box(rgb, circle) if fit_text else None
    if box:
        text_h, text_w = box[3] - box[1], box[2] - box[0]
        crop_h = max(text_h / .44, text_w * 1.1 / 1.95)
        x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        width, height, radius = .975, .5, crop_h  # mismo encuadre 1,95:1 que el recorte por defecto
        scale = scale * 12 / max(12., crop_h)  # recortes grandes: no se amplían más de lo necesario
    x, y = round(x) + shift[0], round(y) + shift[1]
    half_w, half_h, margin = max(3, int(radius * width)), max(3, int(radius * height)), 2
    region = rgb[max(0, y - half_h - margin):y + half_h + 1 + margin,
                 max(0, x - half_w - margin):x + half_w + 1 + margin]
    gray = channel(region, view)[margin:-margin, margin:-margin]
    if gray.size and np.median(gray) < 128:  # globo relleno con el número en claro: siempre tinta oscura
        gray = 255 - gray
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(big, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)


def own_crop(rgb: np.ndarray, circle, shift: tuple[int, int] = (0, 0)) -> np.ndarray:
    """El recorte que lee el lector propio: luminancia, centrado en la tinta del número."""
    return text_crop(rgb, circle, "luma", shift=shift, fit_text=True)


# ================================================================ globos de color: lectores

Readings = list[tuple[str, float]]
# Cinco recortes a un píxel unos de otros: con cifras de pocos píxeles, un píxel cambia cualquier lector.
SHIFTS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]


def read_balloons(rgb: np.ndarray, balloons: list[dict], engine) -> None:
    """RapidOCR sobre tres vistas de cada globo: todos los identificadores completos, con sus observaciones."""
    height, width = rgb.shape[:2]
    for i, balloon in enumerate(balloons):
        x, y, radius = balloon["circle"]
        x, y = round(x), round(y)
        half_w, half_h = max(3, round(radius * .86)), max(3, round(radius * .43))
        roi = rgb[max(0, y - half_h):min(height, y + half_h + 1),
                  max(0, x - half_w):min(width, x + half_w + 1)]
        r, g, b = [c.astype(np.int16) for c in cv2.split(roi)]
        # Second view removes black drawing lines; it remains a fallible OCR observation.
        strength = np.maximum(np.minimum(g - r, g - b), np.minimum(b - r, b - g))
        ink = np.uint8(255 - np.clip(strength * 4, 0, 255))
        narrow_w, narrow_h = max(3, int(radius * .84)), max(3, int(radius * .43))
        narrow = rgb[max(0, y - narrow_h):min(height, y + narrow_h + 1),
                     max(0, x - narrow_w):min(width, x + narrow_w + 1), 0]
        readings = {}
        for method, gray in (("Canal rojo", roi[:, :, 0]), ("Tinta de color", ink),
                             ("Canal rojo · interior", narrow)):
            expanded = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            expanded = cv2.copyMakeBorder(expanded, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
            raw, _ = engine(cv2.cvtColor(expanded, cv2.COLOR_GRAY2BGR), use_det=False, use_cls=False)
            for text, score, *_ in raw or []:
                label = ocr_number(text)
                if label and score >= .35:
                    readings.setdefault(label, []).append({"method": method, "text": text,
                                                          "score": round(float(score), 4)})
        balloon["candidates"] = [{"label": label, "readings": observations}
                                  for label, observations in sorted(readings.items(),
                                  key=lambda item: (-len(item[1]), -max(r["score"] for r in item[1])))]
        if (i + 1) % 50 == 0:
            print(f"  Globos procesados: {i + 1}/{len(balloons)}", flush=True)


class OwnReader:
    """El lector propio en ONNX: recortes en gris, probabilidades CTC por columna."""

    def __init__(self, model: Path = MODELO) -> None:
        import onnxruntime as ort

        meta = json.loads(model.with_suffix(".json").read_text(encoding="utf-8"))
        self.characters: list[str] = meta["caracteres"]
        dimensions = meta["entrada"]
        if (not isinstance(self.characters, list) or not self.characters
                or any(not isinstance(c, str) or len(c) != 1 for c in self.characters)
                or len(set(self.characters)) != len(self.characters)
                or not isinstance(dimensions, list) or len(dimensions) != 2
                or any(type(n) is not int or n <= 0 for n in dimensions)):
            raise ValueError("Metadatos del lector de globos no válidos")
        self.height, self.width = dimensions
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        try:
            self.session = ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
        except Exception as error:  # onnxruntime da varios tipos de error para un modelo ausente o roto
            raise ValueError("No se ha podido cargar el modelo de globos") from error
        if (self.session.get_inputs()[0].shape[2:] != dimensions
                or self.session.get_outputs()[0].shape[-1] != len(self.characters) + 1):
            raise ValueError("Los metadatos no corresponden al modelo de globos")

    def probabilities(self, crops: list[np.ndarray]) -> np.ndarray:
        if not crops:
            return np.zeros((0, 0, len(self.characters) + 1), np.float32)
        images = np.stack([cv2.resize(c, (self.width, self.height), interpolation=cv2.INTER_AREA) for c in crops])
        batch = ((images.astype(np.float32) / 255 - .5) / .5)[:, None]
        logits = np.concatenate([self.session.run(None, {"imagen": batch[i:i + 256]})[0]
                                 for i in range(0, len(batch), 256)])
        exponent = np.exp(logits - logits.max(2, keepdims=True))
        return exponent / exponent.sum(2, keepdims=True)

    def greedy(self, probs: np.ndarray) -> tuple[str, float]:
        """Mejor camino CTC: texto y probabilidad media de sus caracteres."""
        best, score = probs.argmax(1), probs.max(1)
        text, chosen, previous = [], [], 0
        for t, k in enumerate(best):
            if k and k != previous:
                text.append(self.characters[k - 1])
                chosen.append(score[t])
            previous = k
        return "".join(text), float(np.mean(chosen)) if chosen else 0.

    def read(self, crops: list[np.ndarray]) -> list[Readings]:
        return [[self.greedy(p)] for p in self.probabilities(crops)]


@lru_cache
def own_reader(model: Path = MODELO) -> OwnReader | None:
    """El lector propio, o None si falta el modelo o onnxruntime no lo puede cargar."""
    try:
        return OwnReader(model)
    except (ImportError, OSError, ValueError, RuntimeError, KeyError, TypeError):
        return None


def best_rotation(rgb: np.ndarray, balloons: list[dict], reader: OwnReader, sample: int = 60) -> int:
    """Orientación con la que el lector propio está más seguro: planos girados 90° o 180°."""
    chosen = balloons[::max(1, len(balloons) // sample)]
    confidence = []
    for turns in range(4):
        image, moved = rotate(rgb, chosen, turns) if turns else (rgb, chosen)
        probs = reader.probabilities([own_crop(image, b["circle"]) for b in moved])
        confidence.append(float(np.mean([reader.greedy(p)[1] for p in probs])))
    return int(np.argmax(confidence))


def merge(runs: list[list[Readings]]) -> list[Readings]:
    """Varias lecturas de los mismos globos: media de la puntuación de cada identificador, mejor primero."""
    merged = []
    for options in zip(*runs):
        totals = {}
        for candidates in options:
            for text, score in candidates:
                label = label_of(text)
                if label:
                    totals[label] = totals.get(label, 0.) + score / len(options)
        merged.append(sorted(totals.items(), key=lambda kv: -kv[1]))
    return merged


def unique_assignment(predictions: list[Readings], floor: float = 1e-3) -> list[Readings]:
    """Un identificador aparece una sola vez por plano: asignación de máxima probabilidad conjunta.

    No usa la posición ni la numeración vecina. Un globo sin candidato por encima de `floor`
    se queda sin lectura en vez de recibir un número sobrante. Que cada número salga una sola vez
    se cumple en los 20 planos con referencia: es un supuesto, no una garantía.
    """
    from scipy.optimize import linear_sum_assignment
    labels = sorted({label for p in predictions for label, _ in p})
    column = {label: i for i, label in enumerate(labels)}
    n = len(predictions)
    cost = np.full((n, len(labels) + n), 50.)
    cost[np.arange(n), len(labels) + np.arange(n)] = -np.log(floor)
    for i, candidates in enumerate(predictions):
        for label, score in candidates:
            cost[i, column[label]] = -np.log(max(score, 1e-12))
    out = []
    for i, j in zip(*linear_sum_assignment(cost)):
        if j >= len(labels):
            out.append([])
            continue
        chosen = labels[j]
        out.append([(chosen, dict(predictions[i])[chosen])] + [(l, s) for l, s in predictions[i] if l != chosen])
    return out


def rapid_predictions(rgb: np.ndarray, balloons: list[dict], engine) -> list[Readings]:
    """RapidOCR, tres vistas: el número con más vistas (y mejor puntuación) de cada globo."""
    copies = [dict(b, candidates=[]) for b in balloons]
    read_balloons(rgb, copies, engine)
    return [[(b["candidates"][0]["label"], max(r["score"] for r in b["candidates"][0]["readings"]))]
            if b["candidates"] else [] for b in copies]


def own_predictions(rgb: np.ndarray, balloons: list[dict], reader: OwnReader) -> list[Readings]:
    """Lector propio sobre cinco recortes desplazados de cada globo, promediados."""
    return merge([reader.read([own_crop(rgb, b["circle"], s) for b in balloons]) for s in SHIFTS])


def combine(rapid: list[Readings], own: list[Readings]) -> list[Readings]:
    """Los dos lectores votan con su puntuación; después, un número por plano."""
    return unique_assignment(merge([rapid, own]))


# Umbrales provisionales (29/10/2026), elegidos en el grupo de desarrollo con como mucho un 2 % de
# lecturas ofrecidas erróneas: capa vectorial, el de un solo umbral para todo (0,434; no se baja
# más porque saldría 0,0321 y el 3202 «G» pasaría de 10 a 22 errores); imagen, el elegido solo con
# globos de imagen (0,6072, de dos planos con referencia). No son probabilidades calibradas: se
# equivoca menos absteniéndose más, no leyendo mejor. probar_lector_planos.py avisa si dejan de coincidir.
COMBINED_THRESHOLDS = {"capa vectorial": .434, "imagen": .6072}


def offer_readings(balloons: list[dict], choices, rapid, own, thresholds: dict = COMBINED_THRESHOLDS) -> None:
    """Escribe en cada globo la lectura combinada si llega al umbral de su fuente; si no, ninguna."""
    for balloon, choice, by_rapid, by_own in zip(balloons, choices, rapid, own):
        balloon["candidates"] = []
        if choice and choice[0][1] >= thresholds[balloon.get("fuente", "imagen")]:
            label, value = choice[0]
            readings = [{"method": "Combinado", "text": label[1:], "score": round(value, 4)}]
            readings += [{"method": "RapidOCR", "text": text[1:], "score": round(s, 4)} for text, s in by_rapid[:1]]
            readings += [{"method": "Lector propio", "text": text[1:], "score": round(s, 4)} for text, s in by_own[:1]]
            balloon["candidates"] = [{"label": label, "readings": readings}]


def read_balloons_combined(rgb: np.ndarray, balloons: list[dict], engine, reader: OwnReader,
                           thresholds: dict = COMBINED_THRESHOLDS) -> None:
    """Lector combinado: escribe en cada globo la lectura ofrecida (o ninguna)."""
    rapid, own = rapid_predictions(rgb, balloons, engine), own_predictions(rgb, balloons, reader)
    offer_readings(balloons, combine(rapid, own), rapid, own, thresholds)


def read_page_balloons(pdf: Path, page, engine, reader: OwnReader, min_balloons: int = 1) -> tuple[list[dict], str]:
    """Globos de una página con su lectura ofrecida: detección, orientación y lector combinado.

    Con menos de `min_balloons` globos detectados no se lee ninguno (se devuelven sin lectura).
    Los círculos quedan en la imagen de trabajo sin girar.
    """
    work, balloons, source = balloon_source(pdf, page)
    if balloons and len(balloons) >= min_balloons:
        turns = best_rotation(work, balloons, reader)
        image, moved = rotate(work, balloons, turns) if turns else (work, balloons)
        read_balloons_combined(image, moved, engine, reader)
        for balloon, read in zip(balloons, moved):
            balloon["candidates"] = read["candidates"]
    return balloons, source


def model_hash(model: Path = MODELO) -> str | None:
    try:
        return hashlib.sha256(model.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def reader_id() -> str:
    """Identidad del lector de globos: versión, huellas del modelo y sus metadatos, y umbrales."""
    huellas = [model_hash(p) or "no-disponible" for p in (MODELO, MODELO.with_suffix(".json"))]
    umbrales = ",".join(f"{k}={v}" for k, v in sorted(COMBINED_THRESHOLDS.items()))
    return f"lectores-planos-v{VERSION}:{':'.join(huellas)}:{umbrales}"


# ================================================================ marcas `[]` y `No.`

TESELA, SOLAPE = 1600, 240
MARCA_CUADRO = re.compile(r"\[\]\s*(\d(?:\s?\d){1,3})(?!\d)")
MARCA_NO = re.compile(r"(?i)N[o0]\s*[.,．]\s*(\d{3,4})(\s*[Φφ±\dR(].*)?")


def marcas_en_token(texto: str) -> list[tuple[str, str, int, int]]:
    """Marcas de un texto del OCR: (estilo, número, inicio, fin).

    `[]` se busca en todo el texto, porque el OCR la junta con la cota vecina. `No.` tiene que
    abrir el texto, seguida como mucho de la cota: «ADDED No.15.», «No.100 - No.108» o «VIEW No. 1»
    son notas y tablas, no marcas de una cota.
    """
    texto = texto.strip()
    salida = [("[]", re.sub(r"\s", "", m.group(1)), m.start(), m.end()) for m in MARCA_CUADRO.finditer(texto)]
    m = MARCA_NO.fullmatch(texto)
    if m and "no" not in (m.group(2) or "").lower():
        salida.append(("No.", m.group(1), m.start(), m.end(1)))
    return salida


def sin_repetir(marcas: list[dict]) -> list[dict]:
    """Quita lo que se ha leído dos veces por el solape de teselas o por leer en los dos sentidos.

    Un número cortado por el borde de una tesela («27» de «271») cae junto al completo: gana el largo.
    """
    salida: list[dict] = []
    for m in sorted(marcas, key=lambda x: (-len(x["t"]), -x["s"])):
        cerca = [o for o in salida if o["p"] == m["p"] and abs(o["x"] - m["x"]) < .012 and abs(o["y"] - m["y"]) < .012]
        if not any(o["t"].startswith(m["t"]) for o in cerca):
            salida.append(m)
    return salida


def recorta_cuadros(marcas: list[dict]) -> list[dict]:
    """El OCR pega la marca con lo que la sigue: `[]198` y `0.005` salen como «1980».

    Si casi todas las marcas `[]` del plano tienen tres cifras, la cuarta no forma parte del número.
    """
    cuadros = [m for m in marcas if m["via"] == "[]"]
    if not cuadros or sum(len(m["t"]) == 3 for m in cuadros) < .8 * len(cuadros):
        return marcas
    return sin_repetir([{**m, "t": m["t"][:3]} if m["via"] == "[]" else m for m in marcas])


def ocr_teselas(page, engine) -> list[dict]:
    """Texto del OCR con su posición en la página (0–1). Muy ampliado, en horizontal y en vertical."""
    zoom = min(6., max(3., 4700 / max(1., page.rect.width)))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    alto0, ancho0 = rgb.shape[:2]
    salida = []
    for vertical in (False, True):
        imagen = np.rot90(rgb, -1) if vertical else rgb
        alto, ancho = imagen.shape[:2]
        for y in range(0, max(1, alto - SOLAPE), TESELA - SOLAPE):
            for x in range(0, max(1, ancho - SOLAPE), TESELA - SOLAPE):
                tesela = np.ascontiguousarray(imagen[y:y + TESELA, x:x + TESELA])
                if (tesela < 200).mean() < .002:
                    continue
                resultado, _ = engine(tesela)
                for caja, texto, score in resultado or []:
                    q = np.array(caja, float) + (x, y)
                    if vertical:  # a coordenadas de la página sin girar
                        q = np.stack([q[:, 1], alto0 - 1 - q[:, 0]], axis=1)
                    q = q / (ancho0, alto0)
                    salida.append({"texto": texto, "s": round(float(score), 3), "q": q.round(5).tolist()})
    return salida


def marcas_de_tokens(tokens: list[dict], pagina: int) -> list[dict]:
    """Sitúa cada marca dentro de su texto: el OCR puede juntarla con la cota de al lado."""
    salida = []
    for token in tokens:
        q = np.array(token["q"])
        izquierda, derecha = (q[0] + q[3]) / 2, (q[1] + q[2]) / 2
        n = max(1, len(token["texto"].strip()))
        for estilo, numero, ini, fin in marcas_en_token(token["texto"]):
            a, b = izquierda + (derecha - izquierda) * ini / n, izquierda + (derecha - izquierda) * fin / n
            alto = np.abs(q[3] - q[0]).max()
            x0, x1, y0, y1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
            salida.append({"p": pagina, "t": numero, "s": token["s"], "via": estilo,
                           "x": round(float((x0 + x1) / 2), 5), "y": round(float((y0 + y1) / 2), 5),
                           "w": round(float(x1 - x0 + alto * .3), 5), "h": round(float(y1 - y0 + alto * .3), 5)})
    return sin_repetir(salida)


def marcas_de_pagina(page, engine) -> list[dict]:
    """Marcas `[]` y `No.` de una página, sin repetir."""
    return marcas_de_tokens(ocr_teselas(page, engine), page.number + 1)


# ================================================================ números en recuadros

PUNTOS_POR_PT_RECUADRO = 5.54  # unos 400 ppp: en el 3214, recuadros de unos 57 px
ETIQUETA_RECUADRO = re.compile(r"\d{1,3}(?:\.\d{1,2})?|[A-Z]\d{1,2}")
LIMPIA_RECUADRO = re.compile(r"[\s|\[\]()_:;'`,-]")
MIN_SCORE_RECUADRO, MIN_SCORE_OTRO_SENTIDO = .8, .97


def rectangulos(gris: np.ndarray) -> list[tuple]:
    """Cuadriláteros casi perfectos, de tamaño de recuadro, sin contar dos veces sus dos bordes."""
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    contornos, _ = cv2.findContours(binaria, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    salida = []
    for k in contornos:
        area = cv2.contourArea(k)
        if not 700 <= area <= 40000:
            continue
        (cx, cy), (a, b), angulo = cv2.minAreaRect(k)
        if min(a, b) < 25 or max(a, b) > 260 or max(a, b) / max(1, min(a, b)) > 3.2 or area / max(1, a * b) < .86:
            continue
        poligono = cv2.approxPolyDP(k, .03 * cv2.arcLength(k, True), True)
        if len(poligono) == 4 and cv2.isContourConvex(poligono):
            salida.append((area, cx, cy, a, b, angulo))
    unicos: list[tuple] = []
    for r in sorted(salida, reverse=True):
        if not any(np.hypot(r[1] - u[1], r[2] - u[2]) < .4 * min(u[3], u[4]) for u in unicos):
            unicos.append(r)
    return unicos


def esquinas_prolongadas(binaria: np.ndarray, r: tuple) -> int:
    """Cuántas esquinas siguen en línea más allá del rectángulo: una celda de tabla, no un recuadro."""
    _, cx, cy, a, b, angulo = r
    t = np.radians(angulo)
    ex, ey = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
    margen = max(8., .25 * min(a, b))
    prolongadas = 0
    for sa in (-1, 1):
        for sb in (-1, 1):
            esquina = np.array([cx, cy]) + sa * ex * a / 2 + sb * ey * b / 2
            for paso in (sa * ex, sb * ey):  # los dos lados que salen de la esquina
                tinta = 0
                for d in np.linspace(.3, 1, 8) * margen:
                    x, y = (esquina + paso * d).round().astype(int)
                    if 0 <= y < binaria.shape[0] and 0 <= x < binaria.shape[1]:
                        tinta += int(binaria[max(0, y - 2):y + 3, max(0, x - 2):x + 3].any())
                if tinta >= 7:
                    prolongadas += 1
                    break
    return prolongadas


def sentido_admitido(angulo_total: float) -> bool:
    """Un plano se lee de abajo o de la derecha: el texto nunca está boca abajo (6 frente a 9)."""
    phi = (angulo_total + 180) % 360 - 180
    return -95 <= phi < 85  # con margen: un escaneo nunca queda a 90° exactos


def recorte_recuadro(gris: np.ndarray, r: tuple, giro: int) -> np.ndarray | None:
    _, cx, cy, a, b, angulo = r
    matriz = cv2.getRotationMatrix2D((cx, cy), angulo + giro, 1)
    derecha = cv2.warpAffine(gris, matriz, (gris.shape[1], gris.shape[0]), flags=cv2.INTER_CUBIC, borderValue=255)
    w, h = (a, b) if giro % 180 == 0 else (b, a)
    mx, my = max(5, w * .12), max(5, h * .12)
    x0, x1, y0, y1 = int(cx - w / 2 + mx), int(cx + w / 2 - mx), int(cy - h / 2 + my), int(cy + h / 2 - my)
    interior = derecha[max(0, y0):y1, max(0, x0):x1]
    if not interior.size:
        return None
    interior = cv2.resize(interior, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(interior, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)


def lee_recuadro(gris: np.ndarray, r: tuple, engine) -> tuple[str, float] | None:
    """Mejor lectura en sentido admitido; otro sentido solo si no hay ninguna y es casi segura.

    Entre las válidas gana la más larga: leído de lado, un «33» se queda en «3» con mucha confianza.
    """
    lecturas = []
    for giro in (0, 90, 180, 270):
        imagen = recorte_recuadro(gris, r, giro)
        if imagen is None:
            continue
        crudo, _ = engine(cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR), use_det=False, use_cls=False)
        for texto, score, *_ in crudo or []:
            limpio = LIMPIA_RECUADRO.sub("", texto).upper().strip(".")
            if ETIQUETA_RECUADRO.fullmatch(limpio):
                lecturas.append((limpio, float(score), sentido_admitido(r[5] + giro)))
    for admitido, minimo in ((True, MIN_SCORE_RECUADRO), (False, MIN_SCORE_OTRO_SENTIDO)):
        validas = [x for x in lecturas if x[2] == admitido and x[1] >= minimo]
        if validas:
            mejor = max(validas, key=lambda x: (len(x[0]), x[1]))
            return mejor[0], mejor[1]
    return None


def recuadros_de_pagina(page, engine) -> list[dict]:
    zoom = min(PUNTOS_POR_PT_RECUADRO, 9000 / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
    gris = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    # Una línea de cota puede tocar dos esquinas de un recuadro; una celda de tabla sigue por más.
    rects = [r for r in rectangulos(gris) if esquinas_prolongadas(binaria, r) < 3]
    salida = []
    for r in rects:
        leido = lee_recuadro(gris, r, engine)
        if leido:
            _, cx, cy, a, b, _ = r
            salida.append({"p": page.number + 1, "t": leido[0], "s": round(leido[1], 3), "via": "recuadro",
                           "x": round(cx / pix.width, 5), "y": round(cy / pix.height, 5),
                           "w": round(max(a, b) / pix.width, 5), "h": round(max(a, b) / pix.height, 5), "alto": min(a, b)})
    if salida:  # los recuadros de numeración de un plano tienen casi la misma altura; el ancho depende del número
        mediana = float(np.median([x["alto"] for x in salida]))
        salida = [x for x in salida if .7 * mediana <= x["alto"] <= 1.4 * mediana]
    return [{k: v for k, v in x.items() if k != "alto"} for x in salida]


# ================================================================ .icp de infra-CONVERT
# Cada sello del .icp trae su número y dos puntos en unidades del dibujo (mm, origen en el centro de
# la hoja): la cabeza del globo y la punta que señala la cota. La calibración es la transformación de
# esas unidades a la página, ajustada con los globos detectados.

MIN_DENTRO_HOJA = .95  # parte de los sellos que debe caer en la hoja para dar por bueno el calco 1:1


def lee_calibraciones(ruta: Path = CALIBRACION) -> dict:
    """Calibraciones guardadas, por «<documento>-p<página>»; {} si no hay fichero."""
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guarda_calibraciones(store: dict, ruta: Path = CALIBRACION) -> None:
    ruta.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")


def fit_stamps(balloons, readings: list[list[str | None]], stamps: list[dict]):
    """Transformación unidades del dibujo → píxeles. Devuelve (inliers, tentativos, matriz, punto, signo)."""
    by_label = {}
    for s in stamps:
        by_label.setdefault(s["label"], []).append(s)
    radius = float(np.median([b["circle"][2] for b in balloons]))
    best = None
    for which in (0, 1):
        for flip in (1, -1):
            src, dst = [], []
            for balloon, labels in zip(balloons, zip(*readings)):
                for label in {l for l in labels if l}:
                    if len(by_label.get(label, [])) == 1:
                        x, y = by_label[label][0]["points"][which]
                        src.append((x, flip * y))
                        dst.append(balloon["circle"][:2])
            if len(src) < 6:
                continue
            matrix, inliers = cv2.estimateAffinePartial2D(np.float32(src), np.float32(dst), method=cv2.RANSAC,
                                                          ransacReprojThreshold=radius * .6, maxIters=20000,
                                                          confidence=.999)
            count = int(inliers.sum()) if inliers is not None else 0
            if matrix is not None and (best is None or count > best[0]):
                best = (count, len(src), matrix, which, flip)
    return best


def stamps_digest(stamps) -> str:
    """Huella de la referencia extraída de un .icp: número y puntos de cada sello, sin depender del orden."""
    rows = sorted((s["label"], [list(p) for p in s["points"]]) for s in stamps)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def calibrate(key: str, balloons, readings, candidates: dict, size: tuple[int, int], store: dict,
              refresh: bool, pdf_digest: str = "", digests: dict | None = None,
              stamp_digests: dict | None = None) -> tuple[str, tuple] | None:
    """Transformación .icp → píxeles de la página, calculada una vez y guardada.

    La primera vez se ajusta con RANSAC usando como emparejamientos tentativos las lecturas de
    todos los lectores de esa ejecución. Se guarda en coordenadas normalizadas de la página sin
    girar, con la página y las huellas SHA-256 del PDF y del .icp, y las ejecuciones siguientes la
    reutilizan solo si coinciden: la referencia ya no depende de lo que se está evaluando.
    `refresh` la vuelve a calcular. Las calibraciones guardadas antes de registrar huellas
    (29/10/2026) adoptan las del PDF y el .icp en su primera reutilización.

    Con `stamp_digests` ({.icp: `stamps_digest`}) tampoco se reutiliza si cambian los sellos extraídos
    del .icp aunque el fichero sea el mismo (corrección del extractor, 09/11/2026). Una calibración
    sin esa huella es anterior y se vuelve a ajustar.
    """
    height, width = size
    digests = digests or {}
    saved = store.get(key)
    if saved and not refresh and saved["icp"] in candidates:
        same_pdf = saved.get("pdf_sha256", pdf_digest) == pdf_digest
        same_icp = saved.get("icp_sha256", digests.get(saved["icp"], "")) == digests.get(saved["icp"], "")
        same_stamps = stamp_digests is None or saved.get("sellos_sha256") == stamp_digests.get(saved["icp"])
        if same_pdf and same_icp and same_stamps:
            saved.setdefault("pdf_sha256", pdf_digest)
            saved.setdefault("icp_sha256", digests.get(saved["icp"], ""))
            matrix = np.array(saved["matriz"]) * np.array([[width], [height]])
            return saved["icp"], (saved["inliers"], saved["tentativos"], matrix, saved["punto"], saved["signo"])
    fits = {name: fit_stamps(balloons, readings, stamps) for name, stamps in candidates.items() if stamps}
    # Ajuste fiable: el RANSAC explica al menos el 30 % de los globos detectados (y 10 o más).
    fits = {k: v for k, v in fits.items() if v and v[0] >= max(10, .3 * len(balloons))}
    if not fits:
        return None
    icp = max(fits, key=lambda k: fits[k][0])
    inliers, putative, matrix, which, flip = fits[icp]
    store[key] = {"icp": icp, "inliers": inliers, "tentativos": putative, "punto": which, "signo": flip,
                  "matriz": (matrix / np.array([[width], [height]])).tolist(),
                  "pdf_sha256": pdf_digest, "icp_sha256": digests.get(icp, ""),
                  "sellos_sha256": (stamp_digests or {}).get(icp, ""), "fecha": time.strftime("%Y-%m-%d %H:%M")}
    return icp, fits[icp]


def stamps_on_page(stamps, fit) -> np.ndarray:
    """Posición en píxeles de la página de cada sello, con la transformación `fit` de `calibrate`."""
    _, _, matrix, which, flip = fit
    points = np.array([(s["points"][which][0], flip * s["points"][which][1]) for s in stamps], np.float64)
    return points @ matrix[:, :2].T + matrix[:, 2]


def match_stamps(balloons, stamps, fit) -> list[int | None]:
    """Índice del sello de cada globo detectado (el más cercano, uno a uno, a menos de un radio), o None."""
    mapped = stamps_on_page(stamps, fit)
    pairs = []
    for i, balloon in enumerate(balloons):
        x, y, radius = balloon["circle"]
        distance = np.hypot(mapped[:, 0] - x, mapped[:, 1] - y)
        for j in np.nonzero(distance < radius)[0]:
            pairs.append((distance[j], i, j))
    match, used = [None] * len(balloons), set()
    for _, i, j in sorted(pairs):
        if match[i] is None and j not in used:
            match[i] = int(j)
            used.add(j)
    return match


def truth_from_stamps(balloons, stamps, fit) -> tuple[list[str | None], int]:
    """Número del sello más cercano a cada globo detectado (uno a uno, a menos de un radio)."""
    match = match_stamps(balloons, stamps, fit)
    return [None if j is None else stamps[j]["label"] for j in match], sum(j is not None for j in match)


def sellos_calibrados(filas, cal: dict) -> list[dict]:
    """Sellos situados en la página (0–1, sin girar) con una calibración guardada.

    `filas`: sellos con `etiqueta`, `x1, y1` y `x2, y2`. `x, y` es la cabeza del globo y `px, py`
    su punta; cuál de los dos puntos del .icp es la cabeza lo dice la calibración.
    """
    m, cual, signo = cal["matriz"], cal["punto"], cal["signo"]

    def aplica(x: float, y: float) -> tuple[float, float]:
        y = signo * y
        return m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2]

    salida = []
    for f in filas:
        cabeza, punta = ((f["x1"], f["y1"]), (f["x2"], f["y2"])) if cual == 0 else ((f["x2"], f["y2"]), (f["x1"], f["y1"]))
        x, y = aplica(*cabeza)
        px, py = aplica(*punta)
        salida.append({"etiqueta": f["etiqueta"], "x": x, "y": y, "px": px, "py": py})
    return salida


def sellos_a_escala(filas, ancho_pt: float, alto_pt: float) -> list[dict] | None:
    """Calco 1:1 de los sellos sobre la hoja, con el origen en su centro (lo que cumplen las calibraciones).

    Devuelve los que caen en la hoja, o None si queda fuera más de un 5 %: el plano está a otra escala.
    """
    ancho_mm, alto_mm = ancho_pt * 25.4 / 72, alto_pt * 25.4 / 72
    todos = [{"etiqueta": f["etiqueta"], "x": .5 + f["x1"] / ancho_mm, "y": .5 - f["y1"] / alto_mm,
              "px": .5 + f["x2"] / ancho_mm, "py": .5 - f["y2"] / alto_mm} for f in filas]
    dentro = [g for g in todos if -.05 < g["x"] < 1.05 and -.05 < g["y"] < 1.05]
    return None if len(dentro) < MIN_DENTRO_HOJA * len(todos) else dentro


def calibracion_gemela(calibraciones: dict, nombre_icp: str, doc: int, forma: float, forma_de) -> dict | None:
    """Calibración de otro plano con el mismo .icp y la misma forma de hoja: el mismo dibujo globado.

    Sirve cuando el 1:1 falla porque la hoja está impresa a otra escala. Las calibraciones están
    normalizadas a la página, así que no dependen del tamaño. `forma` es ancho/alto de la hoja y
    `forma_de(documento, página)` da la de otra página, o None si no se conoce.
    """
    for clave, cal in calibraciones.items():
        otro, _, numero = clave.partition("-p")
        if cal["icp"] != nombre_icp or int(otro) == doc:
            continue
        otra = forma_de(int(otro), numero)
        if otra is not None and abs(otra - forma) < .01:
            return cal
    return None
