"""Buscador independiente de cotas en PDF, con plano ampliable y revisión local.

    py -3.11 prototypes/data-explorer/buscar_en_plano.py --buscar N170
    py -3.11 prototypes/data-explorer/buscar_en_plano.py --pdf "otro plano.pdf"

Texto PDF si existe; OCR de texto y lectura de globos de color en planos escaneados.
Los globos se buscan en la capa vectorial cuando el PDF los trae como vectores
(infra-CONVERT) y, si no, en la imagen. Se leen con el lector combinado (RapidOCR y el
lector propio de entrenar_lector_globos.py); solo se ofrece la lectura que llega al
umbral de confianza. Sigue siendo una lectura automática, no una verificación.
Las revisiones se guardan en el navegador, ligadas al SHA-256 del PDF, y se
pueden exportar/importar como JSON. Los originales y los visores no se cambian.

Dependencias: PyMuPDF, numpy, opencv-python, Pillow; OCR opcional con
pytesseract + Tesseract y rapidocr-onnxruntime (modelos locales del paquete). El
lector propio necesita torch y el modelo entrenado (out/lector-globos/general/); sin él,
solo RapidOCR.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import webbrowser
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image

DEFAULT_PDF = Path(
    r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast"
    r"\Exemples\0- Bolt Eye\3212 Pump Housing\1-2D y 3D Pieza\20250523_DRW 0140S00237_07.pdf"
)
OUTPUT = Path(__file__).resolve().parent / "out" / "buscar-en-plano"
VERSION = 5
MARKER = '<meta name="buscar-en-plano" content="1">'
Image.MAX_IMAGE_PIXELS = None  # rásteres de 300–800 ppp de hasta 14.000 px de lado


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


def number_matches(label: str, query: str, include_suffixes: bool = True) -> bool:
    label, query = normalize_number(label), normalize_number(query)
    return bool(label and query and (label == query or
                include_suffixes and "." not in query and label.startswith(query + ".")))


def normalized_box(rect, width: float, height: float) -> list[float]:
    x0, y0, x1, y1 = rect
    return [round(max(0., min(1., v / size)), 7)
            for v, size in zip((x0, y0, x1, y1), (width, height, width, height))]


def page_image(doc, page, assets: Path, number: int) -> tuple[np.ndarray, str, str]:
    """Preserve a full-page source raster when possible; otherwise render the PDF."""
    images = page.get_images(full=True)
    if not page.rotation and not page.get_text().strip() and len(images) == 1:
        placements = page.get_image_rects(images[0][0])
        drawings = page.get_drawings()
        if (len(placements) == 1 and max(abs(a - b) for a, b in zip(placements[0], page.rect)) < 1
                and all(d["rect"].get_area() > .99 * page.rect.get_area() for d in drawings)):
            raw = doc.extract_image(images[0][0])
            rgb = np.array(Image.open(io.BytesIO(raw["image"])).convert("RGB"))
            name = f"page-{number}.{raw['ext']}"
            (assets / name).write_bytes(raw["image"])
            return rgb, "assets/" + name, "Imagen original del PDF"
    scale = min(200 / 72, 4500 / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    name = f"page-{number}.png"
    pix.save(assets / name)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3), "assets/" + name, "Render del PDF"


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


def find_tesseract() -> str | None:
    candidates = [shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe")]
    return next((str(p) for p in candidates if p and Path(p).is_file()), None)


def read_scan_words(rgb: np.ndarray, page_no: int, executable: str) -> list[dict]:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = executable
    height, width = rgb.shape[:2]
    factor = min(2., 6600 / max(height, width))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    scaled = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    raw = pytesseract.image_to_data(scaled, config="--psm 11", output_type=pytesseract.Output.DICT,
                                   timeout=120)
    words = []
    for i, text in enumerate(raw["text"]):
        score = float(raw["conf"][i])
        if not text.strip() or score < 25:
            continue
        x, y, w, h = [raw[key][i] / factor for key in ("left", "top", "width", "height")]
        words.append({"id": f"p{page_no}-ocr{len(words)}", "page": page_no, "text": text.strip(),
                      "box": normalized_box((x, y, x + w, y + h), width, height),
                      "method": "ocr", "score": round(score / 100, 4)})
    return words


def read_balloons(rgb: np.ndarray, balloons: list[dict], engine) -> None:
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


def page_raster(page, max_side: int = 10000) -> np.ndarray:
    """Imagen para detectar y leer: la original si la página es solo un ráster; si no, un render a
    la resolución de sus imágenes (más fina que la imagen de pantalla de `page_image`).

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


def vector_layer(pdf: Path, number: int, max_side: int = 10000, min_paths: int = 1,
                 size: tuple[int, int] | None = None) -> np.ndarray | None:
    """La página sin sus imágenes, si tiene imágenes y trazados de color encima; si no, None.

    En los planos de infra-CONVERT los globos son vectores sobre un escaneo: sin las imágenes
    quedan solo los globos y sus números, nítidos y sin las líneas del plano detrás. Con `size`
    (alto, ancho) se dibuja a ese tamaño exacto, para compartir coordenadas con la página completa.
    """
    with fitz.open(pdf) as doc:
        page = doc[number]
        images = page.get_images(full=True)
        colour = lambda c: c is not None and len(c) == 3 and max(c) - min(c) > .3
        if not images or sum(colour(d.get("color")) or colour(d.get("fill")) for d in page.get_drawings()) < min_paths:
            return None
        for image in images:
            page.delete_image(image[0])  # solo en memoria: el original no se toca
        if size:
            matrix = fitz.Matrix(size[1] / page.rect.width, size[0] / page.rect.height)
        else:
            scale = min(600 / 72, max_side / max(page.rect.width, page.rect.height))
            matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        layer = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
        if size and layer.shape[:2] != tuple(size):  # redondeo de un píxel al dibujar
            fitted = np.full((size[0], size[1], 3), 255, np.uint8)
            h, w = min(size[0], layer.shape[0]), min(size[1], layer.shape[1])
            fitted[:h, :w] = layer[:h, :w]
            layer = fitted
        return layer.copy()


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


def best_rotation(rgb: np.ndarray, balloons: list[dict], recognizer, sample: int = 60) -> int:
    """Orientación con la que el lector propio está más seguro: planos girados 90° o 180°."""
    import comparar_ocr_globos as bench
    chosen = balloons[::max(1, len(balloons) // sample)]
    confidence = []
    for turns in range(4):
        image, moved = rotate(rgb, chosen, turns) if turns else (rgb, chosen)
        scores = [recognizer.greedy(recognizer.probabilities(bench.text_crop(image, b["circle"], "luma", fit_text=True)), True)[1]
                  for b in moved]
        confidence.append(float(np.mean(scores)))
    return int(np.argmax(confidence))


# Lector combinado (29/10/2026): RapidOCR, con sus tres vistas, y el lector propio entrenado con
# números sintéticos (entrenar_lector_globos.py, perfil «general»: cinco recortes desplazados
# centrados en la tinta) votan con su puntuación. Después, cada número se asigna a un solo globo
# del plano (supuesto que se cumple en los 20 planos con referencia, no una garantía). Solo se
# ofrece la lectura que llega al umbral de la fuente de ese globo; por debajo, queda «Sin lectura».
# Umbrales provisionales (29/10/2026), elegidos en el grupo de desarrollo con como mucho un 2 % de
# lecturas ofrecidas erróneas: capa vectorial, el de un solo umbral para todo (0,434; no se baja
# más porque saldría 0,0321 y el 3202 «G» pasaría de 10 a 22 errores); imagen, el elegido solo con
# globos de imagen (0,6072, de dos planos con referencia). No son probabilidades calibradas: se
# equivoca menos absteniéndose más, no leyendo mejor. El evaluador avisa si dejan de coincidir.
COMBINED_THRESHOLDS = {"capa vectorial": .434, "imagen": .6072}


def index_signature(digest: str, use_ocr: bool, model_hash: str | None) -> dict:
    """Firma de la caché: el índice se rehace si cambia el PDF, el código, el modelo o los umbrales."""
    reader = ({"tipo": "combinado", "modelo": model_hash, "umbrales": dict(COMBINED_THRESHOLDS)} if model_hash
              else "rapidocr" if use_ocr else None)
    return {"sha256": digest, "version": VERSION, "ocr": use_ocr, "lector": reader}


def own_recognizer() -> tuple[object | None, str | None]:
    """El lector propio (perfil «general») y la huella de su modelo; (None, None) si falta el
    modelo entrenado o torch."""
    try:
        from entrenar_lector_globos import OwnRecognizer, model_path
        path = model_path("general")
        if not path.is_file():
            return None, None
        return OwnRecognizer(path), hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except (ImportError, OSError, RuntimeError):  # torch se importa al cargar el modelo
        return None, None


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


def read_balloons_combined(rgb: np.ndarray, balloons: list[dict], engine, recognizer,
                           thresholds: dict = COMBINED_THRESHOLDS) -> None:
    import comparar_ocr_globos as bench
    rapid_copies = [dict(b, candidates=[]) for b in balloons]
    read_balloons(rgb, rapid_copies, engine)
    rapid = [[(b["candidates"][0]["label"], max(r["score"] for r in b["candidates"][0]["readings"]))]
             if b["candidates"] else [] for b in rapid_copies]
    read = bench.ctc_reader(recognizer, "digitos", [])
    own = bench.merge([read([bench.text_crop(rgb, b["circle"], "luma", shift=s, fit_text=True) for b in balloons])
                       for s in bench.SHIFTS])
    offer_readings(balloons, bench.unique_assignment(bench.merge([rapid, own])), rapid, own, thresholds)


def build_index(pdf: Path, destination: Path, use_ocr: bool, refresh: bool = False) -> dict:
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    recognizer, model_hash = own_recognizer() if use_ocr else (None, None)
    signature = index_signature(digest, use_ocr, model_hash if recognizer else None)
    cache = destination / "indice.json"
    if cache.is_file() and not refresh:
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if saved.get("signature") == signature and all((destination / p["image"]).is_file() for p in saved["pages"]):
                saved["source"] = pdf.as_uri()
                saved["filename"] = pdf.name
                print("Índice en caché: mismo PDF y configuración.", flush=True)
                return saved
        except (KeyError, ValueError):
            pass
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    engine, tesseract, notices = None, find_tesseract() if use_ocr else None, []
    if use_ocr:
        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
        except ImportError:
            notices.append("Sin rapidocr-onnxruntime: globos localizados, sin lectura específica.")
        if not recognizer:
            notices.append("Sin lector propio (entrenar_lector_globos.py --perfil general): solo RapidOCR, "
                           "sin umbral de confianza.")
        if not tesseract:
            notices.append("Sin Tesseract: no se ha extraído el texto general de páginas escaneadas.")
    data = {"signature": signature, "filename": pdf.name, "source": pdf.as_uri(),
            "pages": [], "words": [], "balloons": [], "notices": notices}
    with fitz.open(pdf) as doc:
        if doc.needs_pass:
            raise ValueError("El PDF está protegido por contraseña.")
        for page in doc:
            number = page.number + 1
            print(f"Página {number}/{len(doc)}: imagen y anotaciones...", flush=True)
            rgb, url, image_method = page_image(doc, page, assets, number)
            words = []
            for word in page.get_text("words"):
                rect = fitz.Rect(word[:4]) * page.rotation_matrix
                words.append({"id": f"p{number}-pdf{len(words)}", "page": number, "text": word[4],
                              "box": normalized_box(rect, page.rect.width, page.rect.height), "method": "pdf"})
            # Globos: sobre la capa vectorial si el PDF los trae como vectores; si no, sobre la imagen
            # a su resolución original. Las cajas se normalizan, así que encajan con la de pantalla.
            work, balloons, source = balloon_source(pdf, page)
            for i, balloon in enumerate(balloons):
                position_key = hashlib.sha256(json.dumps(balloon["box"]).encode()).hexdigest()[:12]
                balloon.update(id=f"p{number}-b{position_key}", page=number)
            if engine and balloons and recognizer:
                print(f"  {len(balloons)} globos ({source}): lector combinado.", flush=True)
                turns = best_rotation(work, balloons, recognizer)
                image, moved = rotate(work, balloons, turns) if turns else (work, balloons)
                read_balloons_combined(image, moved, engine, recognizer)
                for balloon, read in zip(balloons, moved):
                    balloon["candidates"] = read["candidates"]
            elif engine and balloons:
                print(f"  {len(balloons)} globos: tres lecturas de RapidOCR, pendientes de revisión.", flush=True)
                read_balloons(work, balloons, engine)
            if use_ocr and tesseract and len(words) < 20:
                print("  OCR del texto general...", flush=True)
                try:
                    data["words"].extend(read_scan_words(rgb, number, tesseract))
                except (RuntimeError, ImportError) as error:
                    notices.append(f"Página {number}: OCR de texto no disponible ({error}).")
            data["words"].extend(words)
            data["balloons"].extend(balloons)
            data["pages"].append({"number": number, "image": url, "width": rgb.shape[1], "height": rgb.shape[0],
                                   "pdf_width": page.rect.width, "pdf_height": page.rect.height,
                                   "native_words": len(words), "image_method": image_method})
    cache.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return data


PAGE = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="buscar-en-plano" content="1"><title>Buscar en plano · Inteplast</title>
<style>
:root{--ink:#173342;--muted:#6b7f89;--line:#dce5e9;--accent:#087d85;--ok:#1b7960;--amber:#9d650e;--paper:#f4f7f8}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 "Segoe UI",Arial,sans-serif}button,input,select{font:inherit;color:inherit}button{cursor:pointer}button,select,input{border:1px solid var(--line);border-radius:7px;background:white}button{padding:7px 11px}button:hover{border-color:#91b4be}button:disabled{opacity:.4;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #55b3bd;outline-offset:2px}[hidden]{display:none!important}a{color:var(--accent)}h1,h2,p{margin:0}.eyebrow{font-size:10px;letter-spacing:1.4px;text-transform:uppercase;font-weight:650;color:var(--muted)}.small{font-size:11px;color:var(--muted)}
header{height:68px;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:0 25px}.brand{font-weight:700;letter-spacing:2px;font-size:18px}.brand span{color:#71c8ce}header h1{font-weight:500;font-size:18px}header button{background:transparent;color:white;border-color:#ffffff45;font-size:12px}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);height:calc(100dvh - 68px)}aside{display:flex;flex-direction:column;min-height:0;background:white;border-right:1px solid var(--line)}.search-section{padding:23px 19px 15px;border-bottom:1px solid var(--line)}.search-section .eyebrow{margin-bottom:11px}.search-row{display:flex;gap:7px}#query{width:100%;min-width:0;padding:10px 11px;font-size:18px;background:#f7fafb}.search-row button{background:var(--accent);color:white;border-color:var(--accent);font-size:20px;padding:5px 12px}.search-options{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:10px}select{padding:5px 8px;font-size:12px;max-width:100%}.checkbox{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--muted)}.checkbox input{accent-color:var(--accent)}.chips{display:flex;gap:5px;margin-top:12px}.chips button{font-size:11px;padding:3px 8px;color:var(--accent)}.list-meta{padding:12px 20px 8px;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--muted)}.result-list{min-height:65px;overflow:auto;flex:1;padding:0 10px 12px}.result{width:100%;display:flex;align-items:center;gap:10px;text-align:left;border:1px solid transparent;padding:9px;margin-top:4px}.result[aria-current=true]{background:#eef7f7;border-color:#afd1d3}.result canvas{width:62px;height:48px;object-fit:contain;border-radius:4px;border:1px solid var(--line);background:white}.result-copy{flex:1;min-width:0}.result-copy b{font-size:15px;display:block;overflow-wrap:anywhere}.result-copy small{font-size:10px;color:var(--muted)}.tag{display:inline-block;font-size:10px;border-radius:4px;padding:3px 6px;white-space:nowrap}.ocr,.alt{background:#fff3dd;color:var(--amber)}.pdf{background:#edf3fb;color:#3a6b95}.reviewed{background:#e8f4ed;color:var(--ok)}.empty{padding:24px 12px;color:var(--muted);font-size:12px}.inspector{padding:14px 19px 16px;border-top:1px solid var(--line);max-height:47vh;overflow:auto}.inspector-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px}.inspector-head h2{font-size:15px;font-weight:600}#detail-preview{width:100%;height:125px;display:block;object-fit:contain;background:#fff;border:1px solid var(--line);border-radius:7px}.review-form{display:flex;gap:7px;margin-top:10px}.review-form input{min-width:0;width:90px;padding:7px 9px}.review-form button{flex:1;color:var(--accent);font-size:12px}.review-note{margin-top:7px;font-size:10px;color:var(--muted)}#forget{margin-top:7px;font-size:11px;color:#a34b3f;padding:4px 8px}.readings{margin-top:10px;font-size:11px;color:var(--muted)}.readings summary{cursor:pointer}.readings p{margin-top:5px}.sidebar-foot{padding:11px 19px;border-top:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:8px}.sidebar-foot button{font-size:10px;padding:4px 7px}
main{min-width:0;display:flex;flex-direction:column;min-height:0}.toolbar{padding:13px 17px;background:#fff;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.toolbar-group{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.toolbar button{font-size:12px}.toolbar button[aria-pressed=true]{border-color:var(--accent);color:var(--accent);background:#eaf6f6}.zoom-group{display:flex;align-items:center;gap:4px}.zoom-group button{width:31px;padding:5px}#zoom-label{min-width:43px;font-size:11px;text-align:center;color:var(--muted)}.canvas-wrap{position:relative;min-height:0;flex:1;background:#e3eaee;overflow:hidden}#plan{height:100%;width:100%;display:block;touch-action:none;cursor:grab}#plan.dragging{cursor:grabbing}#plan.marking{cursor:crosshair}#plan .mark{cursor:pointer;vector-effect:non-scaling-stroke;stroke-width:1.5;fill-opacity:.08}#plan .selected{stroke-width:3;fill-opacity:.12}.map-hint{position:absolute;left:17px;bottom:15px;font-size:11px;background:#ffffffeb;border:1px solid var(--line);border-radius:6px;padding:6px 10px;color:var(--muted);pointer-events:none}.map-location{position:absolute;left:17px;top:15px;background:#fffffff0;border:1px solid var(--line);padding:9px 12px;border-radius:7px;box-shadow:0 2px 9px #1733420a;max-width:calc(100% - 34px)}.map-location strong{margin-right:9px;font-size:17px}.map-location span{font-size:11px}.statusbar{background:#fff;padding:9px 17px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:14px;font-size:11px;color:var(--muted)}.statusbar #filename{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;max-width:58%}.result-navigation{display:flex;align-items:center;gap:4px}.result-navigation button{font-size:13px;padding:2px 8px}.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--ink);color:white;border-radius:8px;padding:10px 18px;font-size:13px;z-index:10;max-width:90vw;box-shadow:0 4px 25px #1234}dialog{width:min(620px,94vw);max-height:85vh;border:1px solid var(--line);border-radius:12px;padding:23px;color:var(--ink)}dialog::backdrop{background:#17334285;backdrop-filter:blur(3px)}.dialog-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}.dialog-head h2{font-size:20px}dialog p{font-size:13px;margin:10px 0;overflow-wrap:anywhere}dialog code{font-size:11px}.legend{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}
@media(max-width:850px){.layout{grid-template-columns:270px minmax(0,1fr)}header{padding:0 17px}.search-section{padding:16px 13px}.inspector{padding:12px 13px}.toolbar{padding:10px}.map-hint{display:none}.toolbar-group{gap:4px}.toolbar button{padding:6px 8px}.statusbar #filename{display:none}.statusbar{font-size:10px}.result-copy b{font-size:13px}.result{gap:6px;padding:6px}.result canvas{width:45px}.tag{font-size:9px}.sidebar-foot{padding:9px 12px}}
@media(max-width:600px){header{height:56px;gap:8px}.brand{font-size:15px}header h1{font-size:14px}.layout{height:auto;min-height:calc(100dvh - 56px);grid-template-columns:1fr}aside{border-right:0;display:contents}.search-section{grid-row:1}.list-meta{grid-row:3;background:white}.result-list{grid-row:4;max-height:220px;background:white}.inspector{grid-row:5;background:white;max-height:none}.sidebar-foot{grid-row:6;background:white}main{grid-row:2;height:62vh;min-height:380px}.search-options{justify-content:start;gap:18px}.chips{display:none}.toolbar{gap:6px}.toolbar button{font-size:11px}.map-location strong{font-size:15px}.map-location{top:9px;left:9px;padding:6px 8px}.result canvas{width:62px}#detail-preview{height:145px}.statusbar{padding:7px 10px}.result-list .empty{padding:10px}.search-section .eyebrow{margin-bottom:7px}}
</style></head><body>
<header><div class="brand">INTE<span>PLAST</span></div><h1>Buscar en plano</h1><button id="about-open">Fuentes ↗</button></header>
<div class="layout"><aside>
<section class="search-section"><div class="eyebrow">Localizar una cota</div><form id="search-form" class="search-row"><input id="query" aria-label="Número de cota o texto" placeholder="N170" autocomplete="off"><button aria-label="Buscar" title="Buscar">⌕</button></form><div class="search-options"><select id="mode" aria-label="Tipo de búsqueda"><option value="number">Número N</option><option value="text">Texto / valor</option></select><label class="checkbox" id="suffix-control"><input type="checkbox" id="suffixes" checked>Incluir subcotas</label></div><div class="chips"><button data-query="N170">N170</button><button data-query="N161">N161</button><button data-query="N240">N240</button><button data-query="N165">N165</button></div></section>
<div class="list-meta"><span id="count" aria-live="polite">Resultados</span><div class="result-navigation"><button id="previous" aria-label="Resultado anterior">‹</button><span id="position"></span><button id="next" aria-label="Resultado siguiente">›</button></div></div><div id="results" class="result-list"></div>
<section id="inspector" class="inspector" hidden><div class="inspector-head"><h2 id="detail-title"></h2><span id="detail-kind" class="tag"></span></div><canvas id="detail-preview" width="560" height="250" aria-label="Recorte original de la ubicación seleccionada"></canvas><div class="review-form"><input id="review-label" aria-label="Número leído en el plano" placeholder="N170"><button id="confirm">Confirmar ubicación</button></div><p class="review-note" id="review-note">Comprueba el número en el recorte antes de guardarlo.</p><button id="forget" hidden>Quitar revisión</button><details class="readings"><summary>Lecturas y procedencia</summary><div id="readings"></div></details></section>
<div class="sidebar-foot"><span id="review-count" class="small"></span><div><button id="export" title="Descargar las ubicaciones revisadas">Exportar</button> <button id="import" title="Cargar ubicaciones del mismo PDF">Importar</button><input type="file" id="import-file" accept=".json,application/json" hidden></div></div>
</aside><main><div class="toolbar"><div class="toolbar-group"><select id="pages" aria-label="Página del PDF"></select><button id="fit" title="Ver la página completa">Vista general</button><button id="show-balloons" aria-pressed="false">Globos</button><button id="mark" aria-pressed="false">Marcar zona</button></div><div class="zoom-group"><button id="zoom-out" aria-label="Alejar">−</button><span id="zoom-label"></span><button id="zoom-in" aria-label="Acercar">+</button></div></div><div id="canvas-wrap" class="canvas-wrap"><svg id="plan" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" role="img" aria-label="Plano, con zoom y ubicaciones de las cotas"><image id="page-image"></image><g id="marks"></g><rect id="draft" fill="#087d8520" stroke="#087d85" vector-effect="non-scaling-stroke" hidden></rect></svg><div id="location" class="map-location" hidden></div><div class="map-hint" id="map-hint">Rueda para ampliar · Arrastra para desplazar</div></div><div class="statusbar"><span id="filename"></span><span id="page-status"></span></div></main></div>
<dialog id="about"><div class="dialog-head"><h2>Plano y lecturas</h2><button id="about-close" aria-label="Cerrar">×</button></div><div id="about-content"></div></dialog><div id="toast" class="toast" role="status" hidden></div>
<script id="dataset" type="application/json">__DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('dataset').textContent),$=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalize=s=>{const m=String(s??'').trim().toUpperCase().replace(/,/g,'.').match(/^N?\s*(\d{1,4})(?:\s*\.\s*(\d{1,2}|T))?$/);return m?'N'+Number(m[1])+(m[2]?'.'+m[2]:''):null};
const ocrNumber=s=>normalize(String(s).replace(/^[\s\[\](){}|:;!]+|[\s\[\](){}|:;!]+$/g,''));
const numberMatches=(label,query,suffixes=true)=>{const l=normalize(label),q=normalize(query);return !!(l&&q&&(l===q||suffixes&&!q.includes('.')&&l.startsWith(q+'.')))};
const textNorm=s=>String(s).toLocaleLowerCase('es').replace(/,/g,'.').replace(/[øØ⌀]/g,'d').replace(/\s+/g,'').trim();
function findNumber(query,records,suffixes=true){
 // Lectura OCR principal antes que las alternativas. Solo coincidencias de lectura: sin propuestas por cercanía.
 const q=normalize(query);if(!q)return [];
 const matches=[];
 for(const r of records){
  const labels=r.kind==='reviewed'?[r.label]:(r.labels||[r.label]),hit=labels.filter(l=>numberMatches(l,q,suffixes));if(!hit.length)continue;
  const alternative=r.kind==='ocr'&&!numberMatches(labels[0],q,suffixes);
  matches.push({...r,label:hit[0],matchedLabels:hit,kind:alternative?'alt':r.kind,note:alternative?'Lectura principal '+labels[0]:''});
 }
 const tier={reviewed:0,pdf:1,ocr:2,alt:3};
 return matches.sort((a,b)=>(tier[a.kind]??4)-(tier[b.kind]??4)||Number(normalize(b.label)===q)-Number(normalize(a.label)===q)||a.page-b.page||a.box[1]-b.box[1]);
}
const kinds={ocr:'OCR · revisar',alt:'Otra lectura · revisar',pdf:'Texto PDF',reviewed:'Revisada',unread:'Sin lectura',manual:'Zona manual'};
const colors={ocr:'#c9841d',alt:'#b5781c',pdf:'#427fad',reviewed:'#21896e',unread:'#718c96',manual:'#087d85'};
const storageKey='inteplast-plan-reviews-v1:'+data.signature.sha256;
const state={page:1,matches:[],selected:null,all:false,marking:false,view:{x:0,y:0,w:100,h:100},reviews:{},images:{}};
let toastTimer,drag=null;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500)}
function validReview(r){return r&&typeof r.id==='string'&&/^(p\d+-(b[a-f0-9]+|(ocr|pdf)\d+)|manual-[\w-]+)$/.test(r.id)&&r.id.length<120&&normalize(r.label)&&data.pages.some(p=>p.number===r.page)&&Array.isArray(r.box)&&r.box.length===4&&r.box.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1)&&r.box[2]>r.box[0]&&r.box[3]>r.box[1]}
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(saved))for(const r of saved)if(validReview(r))state.reviews[r.id]=r}catch{toast('Revisiones solo en esta sesión. Puedes exportarlas.')}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(Object.values(state.reviews)))}catch{toast('No se pudo guardar en el navegador. Exporta las revisiones.')}$('review-count').textContent=Object.keys(state.reviews).length+' revisadas'}
function imageFor(pageNo){if(!state.images[pageNo]){const im=new Image();im.onload=()=>{drawThumbnails();drawDetail()};im.src=data.pages.find(p=>p.number===pageNo).image;state.images[pageNo]=im}return state.images[pageNo]}
function page(){return data.pages.find(p=>p.number===state.page)}
function inside(box,outer){const x=(box[0]+box[2])/2,y=(box[1]+box[3])/2;return x>=outer[0]&&x<=outer[2]&&y>=outer[1]&&y<=outer[3]}
function withReview(record){const review=state.reviews[record.id];return review?{...record,...review,label:review.label,kind:'reviewed'}:record}
function numberRecords(){
 const records=data.balloons.map(b=>withReview({...b,kind:b.candidates.length?'ocr':'unread',labels:b.candidates.map(c=>c.label),label:b.candidates[0]?.label||'Globo'}));
 for(const word of data.words){if(word.method==='ocr'&&!/^N\s*\d/i.test(word.text))continue;const label=word.method==='pdf'?normalize(word.text):ocrNumber(word.text);if(!label)continue;
  if(word.method==='ocr'&&data.balloons.some(b=>b.page===word.page&&inside(word.box,b.box)))continue;
  records.push(withReview({...word,label,labels:[label],kind:word.method}));
 }
 for(const review of Object.values(state.reviews))if(!records.some(r=>r.id===review.id))records.push({...review,label:review.label,kind:'reviewed'});
 return records;
}
function textMatches(query){
 const parts=query.trim().split(/\s+/).map(textNorm),results=[];
 const wordMatch=(text,q)=>{const t=textNorm(text);if(t===q||t===('d'+q))return true;return !/^\d/.test(q)&&q.length>=3&&t.includes(q)};
 for(let i=0;i<data.words.length;i++){
  const first=data.words[i];if(!wordMatch(first.text,parts[0]))continue;
  const chain=[first];let last=first;
  for(let n=1;n<parts.length;n++){
   const next=data.words.slice(i+1,i+12).find(w=>w.page===last.page&&w.method===last.method&&wordMatch(w.text,parts[n])&&w.box[0]>=last.box[2]-.002&&w.box[0]-last.box[2]<.04&&Math.abs(w.box[1]-last.box[1])<Math.max(.003,last.box[3]-last.box[1]));
   if(!next)break;chain.push(next);last=next;
  }
  if(chain.length===parts.length)results.push({...first,label:chain.map(w=>w.text).join(' '),kind:first.method,box:[Math.min(...chain.map(w=>w.box[0])),Math.min(...chain.map(w=>w.box[1])),Math.max(...chain.map(w=>w.box[2])),Math.max(...chain.map(w=>w.box[3]))]});
 }
 return results;
}
function search(focus=true){
 const query=$('query').value.trim(),mode=$('mode').value;state.selected=null;
 $('suffix-control').hidden=mode!=='number';
 if(!query)state.matches=[];
 else if(mode==='number')state.matches=findNumber(query,numberRecords(),$('suffixes').checked);
 else state.matches=textMatches(query).sort((a,b)=>({pdf:1,ocr:2}[a.kind]??3)-({pdf:1,ocr:2}[b.kind]??3)||a.page-b.page||a.box[1]-b.box[1]);
 renderResults();$('inspector').hidden=true;$('location').hidden=true;
 if(state.matches.length)selectResult(0,focus);else{renderMarks();if(focus)fit()}
}
function renderResults(){
 const query=$('query').value.trim();$('count').textContent=state.matches.length+' coincidencias';
 $('results').innerHTML=state.matches.length?state.matches.map((r,i)=>`<button class="result" data-result="${i}" aria-current="false"><canvas width="124" height="96" data-thumb="${i}" aria-hidden="true"></canvas><span class="result-copy"><b>${esc(r.label)}</b><small>Página ${r.page}${r.note?' · '+esc(r.note):r.matchedLabels?.length>1?' · lecturas distintas':''}</small></span><span class="tag ${r.kind}">${kinds[r.kind]}</span></button>`).join(''):`<div class="empty">${!query?'Busca un número N o cambia a Texto / valor.':$('mode').value==='number'&&!normalize(query)?'Introduce un número como N170 o 170.2.':'Sin coincidencias en el índice. Puedes mostrar los globos o marcar una zona.'}</div>`;
 $('previous').disabled=$('next').disabled=state.matches.length<2;$('position').textContent='';drawThumbnails();
}
function crop(canvas,record,padding){
 const im=imageFor(record.page);if(!im.complete||!im.naturalWidth)return;
 const p=data.pages.find(p=>p.number===record.page),[x0,y0,x1,y1]=record.box;
 const w=(x1-x0)*p.width,h=(y1-y0)*p.height,cx=(x0+x1)*p.width/2,cy=(y0+y1)*p.height/2;
 const scale=Math.min(canvas.width/(w*padding),canvas.height/(h*padding));
 const sw=canvas.width/scale,sh=canvas.height/scale,ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
 ctx.drawImage(im,cx-sw/2,cy-sh/2,sw,sh,0,0,canvas.width,canvas.height);
 if(canvas.id==='detail-preview'){ctx.strokeStyle=colors[record.kind]||colors.unread;ctx.lineWidth=2;ctx.strokeRect((canvas.width-w*scale)/2-3,(canvas.height-h*scale)/2-3,w*scale+6,h*scale+6)}
}
function drawThumbnails(){document.querySelectorAll('[data-thumb]').forEach(c=>{const r=state.matches[Number(c.dataset.thumb)];if(r)crop(c,r,1.6)})}
function drawDetail(){if(state.selected)crop($('detail-preview'),state.selected,2.4)}
function selectResult(index,focus=true){const r=state.matches[index];if(!r)return;selectLocation(r,focus);$('position').textContent=(index+1)+' / '+state.matches.length;document.querySelectorAll('[data-result]').forEach(b=>b.setAttribute('aria-current',String(Number(b.dataset.result)===index)))}
function selectLocation(record,focus=true){
 state.selected=withReview(record);const r=state.selected;if(r.page!==state.page)setPage(r.page,false);
 $('inspector').hidden=false;$('detail-title').textContent=r.label||'Globo';$('detail-kind').className='tag '+r.kind;$('detail-kind').textContent=kinds[r.kind];
 $('review-label').value=normalize(r.label)||normalize($('query').value)||'';
 $('review-note').textContent=r.kind==='reviewed'?'Ubicación revisada y guardada para este PDF.':'Comprueba el número en el recorte antes de guardarlo.';
 $('forget').hidden=!state.reviews[r.id];
 $('readings').innerHTML=`<p>Página ${r.page} · ${esc(r.id)}</p>`+(r.candidates?.flatMap(c=>c.readings.map(o=>`<p>${esc(c.label)} · ${esc(o.method)}: «${esc(o.text)}»</p>`)).join('')||`<p>${esc(r.text||r.label||'Sin lectura disponible')}</p>`);
 if(r.kind==='ocr'||r.kind==='alt')$('readings').innerHTML+='<p>Lectura automática sin verificar. Dos lecturas coincidentes tampoco confirman el número.</p>'; $('location').innerHTML=`<strong>${esc(r.label||'Globo')}</strong><span class="tag ${r.kind}">${kinds[r.kind]}</span>`;$('location').hidden=false;
 drawDetail();renderMarks();if(focus)focusBox(r.box);
}
function setPage(number,reset=true){state.page=Number(number);const p=page();$('pages').value=String(number);$('page-image').setAttribute('href',p.image);$('page-image').setAttribute('width',p.width);$('page-image').setAttribute('height',p.height);imageFor(number);$('page-status').textContent=`${p.native_words?'Texto PDF':'Sin texto PDF'} · ${data.balloons.filter(b=>b.page===state.page).length} globos · ${p.width} × ${p.height} px`;renderMarks();if(reset)fit()}
function applyView(){const v=state.view;$('plan').setAttribute('viewBox',`${v.x} ${v.y} ${v.w} ${v.h}`);$('zoom-label').textContent=Math.round($('plan').clientWidth/v.w*100)+'%'}
function fit(){const p=page(),ratio=$('plan').clientWidth/Math.max(1,$('plan').clientHeight);let w=p.width*1.06,h=w/ratio;if(h<p.height*1.06){h=p.height*1.06;w=h*ratio}state.view={x:(p.width-w)/2,y:(p.height-h)/2,w,h};applyView()}
function focusBox(box){const p=page(),ratio=$('plan').clientWidth/Math.max(1,$('plan').clientHeight);let w=Math.max((box[2]-box[0])*p.width*8,200),h=w/ratio;const minH=(box[3]-box[1])*p.height*6;if(h<minH){h=minH;w=h*ratio}state.view={x:(box[0]+box[2])*p.width/2-w/2,y:(box[1]+box[3])*p.height/2-h/2,w,h};applyView()}
function zoom(factor,anchor={x:.5,y:.5}){const v=state.view,ratio=$('plan').clientWidth/Math.max(1,$('plan').clientHeight),w=Math.max(80,Math.min(page().width*4,v.w*factor)),h=w/ratio;state.view={x:v.x+anchor.x*(v.w-w),y:v.y+anchor.y*(v.h-h),w,h};applyView()}
function renderMarks(){
 const p=page(),records=new Map();if(state.all)for(const r of numberRecords().filter(r=>r.page===state.page))if(r.circle||r.kind==='reviewed')records.set(r.id,r);
 for(const r of state.matches.filter(r=>r.page===state.page))records.set(r.id,r);
 if(state.selected?.page===state.page)records.set(state.selected.id,state.selected);
 $('marks').innerHTML=[...records.values()].map(r=>{const [x0,y0,x1,y1]=r.box,selected=state.selected?.id===r.id;return `<rect data-location="${esc(r.id)}" class="mark ${selected?'selected':''}" x="${x0*p.width}" y="${y0*p.height}" width="${(x1-x0)*p.width}" height="${(y1-y0)*p.height}" rx="2" fill="${colors[r.kind]}" stroke="${colors[r.kind]}"><title>${esc(r.label||'Globo')} · ${kinds[r.kind]}</title></rect>`}).join('');
}
function pointer(e){const rect=$('plan').getBoundingClientRect();return {x:(e.clientX-rect.left)/rect.width,y:(e.clientY-rect.top)/rect.height}}
function world(point){const v=state.view;return {x:v.x+point.x*v.w,y:v.y+point.y*v.h}}
function markMode(active){state.marking=active;$('mark').setAttribute('aria-pressed',String(active));$('plan').classList.toggle('marking',active);$('map-hint').textContent=active?'Arrastra un recuadro alrededor del número':'Rueda para ampliar · Arrastra para desplazar'}
$('plan').addEventListener('pointerdown',e=>{if(e.button!==0)return;const pt=pointer(e);drag={start:pt,view:{...state.view},world:world(pt),moved:false,id:e.target.dataset.location};$('plan').setPointerCapture(e.pointerId);$('plan').classList.add('dragging')});
$('plan').addEventListener('pointermove',e=>{if(!drag)return;const pt=pointer(e);drag.moved ||= Math.hypot((pt.x-drag.start.x)*$('plan').clientWidth,(pt.y-drag.start.y)*$('plan').clientHeight)>4;if(state.marking){const cur=world(pt),x=Math.min(cur.x,drag.world.x),y=Math.min(cur.y,drag.world.y);for(const [key,value] of Object.entries({x,y,width:Math.abs(cur.x-drag.world.x),height:Math.abs(cur.y-drag.world.y)}))$('draft').setAttribute(key,value);$('draft').toggleAttribute('hidden',false)}else{state.view={...drag.view,x:drag.view.x-(pt.x-drag.start.x)*drag.view.w,y:drag.view.y-(pt.y-drag.start.y)*drag.view.h};applyView()}});
$('plan').addEventListener('pointerup',e=>{if(!drag)return;const action=drag;drag=null;$('plan').classList.remove('dragging');$('draft').toggleAttribute('hidden',true);
 if(state.marking&&action.moved){const end=world(pointer(e)),p=page(),box=[Math.min(action.world.x,end.x)/p.width,Math.min(action.world.y,end.y)/p.height,Math.max(action.world.x,end.x)/p.width,Math.max(action.world.y,end.y)/p.height].map(v=>Math.max(0,Math.min(1,v)));if(box[2]-box[0]>.0002&&box[3]-box[1]>.0002)selectLocation({id:'manual-'+Date.now(),page:state.page,box,label:normalize($('query').value)||'Zona',kind:'manual'},false);markMode(false)
 }else if(!action.moved&&action.id){const record=state.matches.find(r=>r.id===action.id)||numberRecords().find(r=>r.id===action.id);if(record)selectLocation(record)}
});
$('plan').addEventListener('pointercancel',()=>{drag=null;$('draft').toggleAttribute('hidden',true);$('plan').classList.remove('dragging')});
$('plan').addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY>0?1.18:1/1.18,pointer(e))},{passive:false});
$('plan').addEventListener('dblclick',e=>{if(!state.marking)zoom(.5,pointer(e))});
$('search-form').addEventListener('submit',e=>{e.preventDefault();search()});
$('mode').addEventListener('change',()=>search());$('suffixes').addEventListener('change',()=>search());
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.query){$('query').value=b.dataset.query;$('mode').value='number';search()}if(b.dataset.result!=null)selectResult(Number(b.dataset.result))});
function moveResult(delta){if(!state.matches.length)return;const i=state.matches.findIndex(r=>r.id===state.selected?.id);selectResult((i+delta+state.matches.length)%state.matches.length)}
$('previous').onclick=()=>moveResult(-1);$('next').onclick=()=>moveResult(1);
$('pages').onchange=()=>{state.selected=null;$('inspector').hidden=true;$('location').hidden=true;setPage($('pages').value)};
$('fit').onclick=fit;$('zoom-in').onclick=()=>zoom(.7);$('zoom-out').onclick=()=>zoom(1/.7);
$('show-balloons').onclick=()=>{state.all=!state.all;$('show-balloons').setAttribute('aria-pressed',String(state.all));renderMarks()};
$('mark').onclick=()=>markMode(!state.marking);
$('confirm').onclick=()=>{const label=normalize($('review-label').value),r=state.selected;if(!r)return;if(!label){toast('Introduce un número válido, por ejemplo N170.2.');return}const reviewed={id:r.id,page:r.page,box:r.box,label,reviewed_at:new Date().toISOString()};state.reviews[r.id]=reviewed;persist();search(false);selectLocation({...r,...reviewed,kind:'reviewed'},false);toast('Ubicación revisada guardada en este navegador.')};
$('forget').onclick=()=>{const r=state.selected;if(!r)return;delete state.reviews[r.id];persist();search(false);toast('Revisión eliminada. El plano original no cambia.')};
$('export').onclick=()=>{const payload={schema:1,pdf_sha256:data.signature.sha256,filename:data.filename,reviews:Object.values(state.reviews)},url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='cotas-revisadas-'+data.signature.sha256.slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('import').onclick=()=>$('import-file').click();
$('import-file').onchange=async()=>{try{const file=$('import-file').files[0];if(!file)return;if(file.size>5e6)throw Error('Archivo demasiado grande.');const payload=JSON.parse(await file.text());if(payload.schema!==1||payload.pdf_sha256!==data.signature.sha256)throw Error('Las revisiones pertenecen a otro PDF o revisión.');if(!Array.isArray(payload.reviews)||payload.reviews.length>10000||!payload.reviews.every(validReview))throw Error('Formato de revisiones no válido.');for(const r of payload.reviews)state.reviews[r.id]=r;persist();search(false);toast(payload.reviews.length+' revisiones importadas.')}catch(error){toast(error.message||'No se pudo importar.')}finally{$('import-file').value=''}};
$('about-open').onclick=()=>{$('about-content').innerHTML=`<p><a href="${esc(data.source)}" target="_blank" rel="noopener">${esc(data.filename)} ↗</a></p><p>${data.pages.length} página(s) · ${data.words.filter(w=>w.method==='pdf').length} palabras del PDF · ${data.balloons.length} globos detectados.</p><div class="legend"><span class="tag pdf">Texto PDF</span><span class="tag ocr">OCR · revisar</span><span class="tag reviewed">Revisada</span></div><p>El texto PDF se busca tal como está almacenado. Las lecturas OCR son propuestas: pueden confundir dígitos o no detectar una cota. Su confianza no confirma su identidad.</p><p>Los recortes y el zoom conservan la imagen del documento. Las revisiones se guardan en este navegador y pueden exportarse. Se vinculan al contenido exacto del PDF; no se trasladan automáticamente a otra revisión.</p><p>Se buscan números y sus sufijos. No se interpreta automáticamente el requisito geométrico al que apunta la flecha.</p>${data.notices.map(n=>`<p>${esc(n)}</p>`).join('')}<p class="small">SHA-256: <code>${data.signature.sha256}</code></p>`;$('about').showModal()};
$('about-close').onclick=()=>$('about').close();
$('filename').textContent=data.filename;$('filename').title=data.filename;
$('pages').innerHTML=data.pages.map(p=>`<option value="${p.number}">Página ${p.number}</option>`).join('');
new ResizeObserver(()=>{const v=state.view,ratio=$('plan').clientWidth/Math.max(1,$('plan').clientHeight),w=v.h*ratio;state.view={...v,x:v.x+(v.w-w)/2,w};applyView()}).observe($('canvas-wrap'));
persist();setPage(data.pages[0].number);$('query').value=data.query||'';$('mode').value=data.query&&!normalize(data.query)?'text':'number';search(Boolean(data.query));
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="PDF que se quiere consultar")
    parser.add_argument("--buscar", default="", help="Consulta inicial: N170, 170.2 o un texto")
    parser.add_argument("--salida", type=Path, default=OUTPUT, help="Carpeta exclusiva del buscador")
    parser.add_argument("--sin-ocr", action="store_true", help="Solo texto PDF y ubicación de globos")
    parser.add_argument("--reindexar", action="store_true", help="Regenerar las lecturas OCR")
    parser.add_argument("--no-abrir", action="store_true", help="Generar sin abrir el navegador")
    args = parser.parse_args()
    pdf, destination = args.pdf.resolve(), args.salida.resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        parser.error(f"No se encuentra el PDF: {pdf}")
    if destination == pdf.parent or pdf.parent in destination.parents:
        parser.error("La salida debe estar fuera de la carpeta de originales")
    page = destination / "index.html"
    if page.is_file() and MARKER not in page.read_text(encoding="utf-8"):
        parser.error("La carpeta contiene otra vista. Usar una salida exclusiva del buscador")
    destination.mkdir(parents=True, exist_ok=True)
    data = build_index(pdf, destination, not args.sin_ocr, args.reindexar)
    data["query"] = args.buscar
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace("&", "\\u0026")
    page.write_text(PAGE.replace("__DATA__", encoded), encoding="utf-8")
    count = sum(bool(b["candidates"]) for b in data["balloons"])
    print(f"{len(data['pages'])} páginas; {len(data['balloons'])} globos; {count} con propuestas OCR.")
    for notice in data["notices"]:
        print(notice)
    print(f"Buscador: {page}")
    print("Las lecturas OCR requieren revisión; no se identifican como cotas confirmadas.")
    if not args.no_abrir:
        webbrowser.open(page.as_uri())


if __name__ == "__main__":
    main()
