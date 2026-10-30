"""PDF text, balloon detection and fallible OCR readings for the web drawing index.

Balloons are found where they are drawn: in the vector layer when the PDF carries them as vectors
over a scan (infra-CONVERT), otherwise in the page image; the source is decided balloon by balloon.
Numbers are read by `balloon_reader` (RapidOCR and the own ONNX reader, combined) and offered only
above the threshold of their source. Measured in prototypes/data-explorer (README, «Comparativa de
lectores de globos» onwards); the limits documented there apply here too.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from app.ingestion.balloon_reader import (  # noqa: F401  (public names of this module)
    normalize_number,
    ocr_number,
    own_reader,
    read_balloons,
    read_balloons_combined,
    text_crop,
)
from app.ingestion.drawing_version import INDEX_VERSION, reader_id

logger = logging.getLogger(__name__)
Image.MAX_IMAGE_PIXELS = None  # 300–800 dpi rasters of up to 14,000 px per side


def build_index(
    pdf: Path, destination: Path, *, use_ocr: bool = True
) -> dict[str, Any]:
    """Read one PDF version. EvidenceJob owns caching and human reviews.

    Coordinates are normalised to the page and candidate IDs are derived from them, as in the
    existing web contract. OCR readings are proposals, never verified characteristic identities.
    """
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    engine = None
    reader = own_reader() if use_ocr else None
    tesseract = find_tesseract() if use_ocr else None
    notices: list[str] = []
    if use_ocr:
        try:
            from rapidocr_onnxruntime import RapidOCR

            engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
        except ImportError:
            notices.append(
                "Sin rapidocr-onnxruntime: globos localizados, sin lectura específica."
            )
        if reader is None:
            notices.append(
                "Lector de globos no disponible: globos localizados sin lectura automática. "
                "La búsqueda en el texto del plano sigue disponible."
            )
        if not tesseract:
            notices.append(
                "Sin Tesseract: no se ha extraído el texto general de páginas escaneadas."
            )
    data: dict[str, Any] = {
        "signature": {
            "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "version": INDEX_VERSION,
            "ocr": use_ocr,
            "lector": reader_id()
            if reader is not None and engine is not None
            else None,
        },
        "filename": pdf.name,
        "pages": [],
        "words": [],
        "balloons": [],
        "notices": notices,
    }
    with fitz.open(pdf) as document:
        if document.needs_pass:
            raise ValueError("El PDF está protegido por contraseña.")
        for page in document:
            number = page.number + 1
            rgb, image, method = page_image(document, page, assets, number)
            words: list[dict[str, Any]] = []
            for word in page.get_text("words"):
                rectangle = fitz.Rect(word[:4]) * page.rotation_matrix
                words.append(
                    {
                        "id": f"p{number}-pdf{len(words)}",
                        "page": number,
                        "text": word[4],
                        "box": normalized_box(
                            rectangle, page.rect.width, page.rect.height
                        ),
                        "method": "pdf",
                    }
                )
            # Balloons are detected and read on the working image (vector layer where it applies,
            # original raster otherwise). Boxes are normalised, so they match the display image.
            work, balloons, source = balloon_source(pdf, page)
            for balloon in balloons:
                position = hashlib.sha256(
                    json.dumps(balloon["box"]).encode()
                ).hexdigest()[:12]
                balloon.update(id=f"p{number}-b{position}", page=number)
            if reader is not None and engine is not None and balloons:
                logger.info(f"Página {number}: {len(balloons)} globos ({source})")
                turns = best_rotation(work, balloons, reader)
                image_, moved = (
                    rotate(work, balloons, turns) if turns else (work, balloons)
                )
                read_balloons_combined(image_, moved, engine, reader)
                for balloon, read in zip(balloons, moved, strict=True):
                    balloon["candidates"] = read["candidates"]
            else:
                for balloon in balloons:
                    balloon["candidates"] = []
            if use_ocr and tesseract and len(words) < 20:
                try:
                    data["words"].extend(read_scan_words(rgb, number, tesseract))
                except (RuntimeError, ImportError) as error:
                    notices.append(
                        f"Página {number}: OCR de texto no disponible ({error})."
                    )
            data["words"].extend(words)
            data["balloons"].extend(balloons)
            data["pages"].append(
                {
                    "number": number,
                    "image": image,
                    "width": rgb.shape[1],
                    "height": rgb.shape[0],
                    "pdf_width": page.rect.width,
                    "pdf_height": page.rect.height,
                    "native_words": len(words),
                    "image_method": method,
                    "balloon_source": source,
                }
            )
    return data


def normalized_box(rect: Any, width: float, height: float) -> list[float]:
    x0, y0, x1, y1 = rect
    return [
        round(max(0.0, min(1.0, v / size)), 7)
        for v, size in zip(
            (x0, y0, x1, y1), (width, height, width, height), strict=True
        )
    ]


def page_image(
    doc: Any, page: Any, assets: Path, number: int
) -> tuple[NDArray[Any], str, str]:
    """Display image: the full-page source raster when possible; otherwise a PDF render."""
    images = page.get_images(full=True)
    if not page.rotation and not page.get_text().strip() and len(images) == 1:
        placements = page.get_image_rects(images[0][0])
        drawings = page.get_drawings()
        if (
            len(placements) == 1
            and max(abs(a - b) for a, b in zip(placements[0], page.rect, strict=True))
            < 1
            and all(
                d["rect"].get_area() > 0.99 * page.rect.get_area() for d in drawings
            )
        ):
            raw = doc.extract_image(images[0][0])
            rgb = np.array(Image.open(io.BytesIO(raw["image"])).convert("RGB"))
            name = f"page-{number}.{raw['ext']}"
            (assets / name).write_bytes(raw["image"])
            return rgb, "assets/" + name, "Imagen original del PDF"
    scale = min(200 / 72, 4500 / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
    )
    name = f"page-{number}.png"
    pix.save(assets / name)
    return (
        np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3),
        "assets/" + name,
        "Render del PDF",
    )


def page_raster(page: Any, max_side: int = 10000) -> NDArray[Any]:
    """Image to detect and read on: the original if the page is only one raster; otherwise a render
    at the resolution of its images (finer than the display image of `page_image`).

    The original is used only if it is all there is on the page and covers it, unrotated and
    unflipped: with strokes on top (vector balloons) they would be lost.
    """
    images = page.get_images(full=True)
    if len(images) == 1 and not page.rotation and not page.get_text().strip():
        info = page.get_image_info()
        drawn = [
            d
            for d in page.get_drawings()
            if d["rect"].get_area() < 0.99 * page.rect.get_area()
        ]
        if len(info) == 1 and not drawn:
            a, b, c, d, _, _ = info[0]["transform"]
            tolerance = 0.01 * max(page.rect.width, page.rect.height)
            if (
                abs(b) < 1e-6
                and abs(c) < 1e-6
                and a > 0
                and d > 0
                and all(
                    abs(u - v) < tolerance
                    for u, v in zip(info[0]["bbox"], page.rect, strict=True)
                )
            ):
                raw = page.parent.extract_image(images[0][0])
                return np.array(Image.open(io.BytesIO(raw["image"])).convert("RGB"))
    widest = max(
        (
            im[2] / max(1.0, r.width) * 72
            for im in images
            for r in page.get_image_rects(im[0])
        ),
        default=200,
    )
    dpi = min(max(200.0, widest), 600.0)
    scale = min(dpi / 72, max_side / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
    )
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3).copy()


def vector_layer(
    pdf: Path, number: int, max_side: int = 10000, min_paths: int = 1
) -> NDArray[Any] | None:
    """The page without its images, if it has images and coloured strokes on top; else None.

    In infra-CONVERT drawings the balloons are vectors over a scan: without the images only the
    balloons and their numbers remain, sharp and without the drawing behind them.
    """
    with fitz.open(pdf) as doc:
        page = doc[number]
        images = page.get_images(full=True)

        def coloured(c: Any) -> bool:
            return c is not None and len(c) == 3 and max(c) - min(c) > 0.3

        if (
            not images
            or sum(
                coloured(d.get("color")) or coloured(d.get("fill"))
                for d in page.get_drawings()
            )
            < min_paths
        ):
            return None
        for image in images:
            page.delete_image(image[0])  # in memory only: the original is untouched
        scale = min(600 / 72, max_side / max(page.rect.width, page.rect.height))
        pix = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
        )
        return (
            np.frombuffer(pix.samples, np.uint8)
            .reshape(pix.height, pix.width, 3)
            .copy()
        )


def pair_balloons(
    first: list[dict[str, Any]], second: list[dict[str, Any]]
) -> list[tuple[int, int]]:
    """One-to-one pairs between two balloon lists in the same coordinates: (index, index).

    Only pairs whose centres are closer than half the larger radius are valid; valid pairs are
    taken from closest to farthest. The limit depends on each pair's radii, so pairs are filtered
    before sorting: a rejected small pair never prevents a valid large one.
    """
    valid = sorted(
        (distance, i, j)
        for i, a in enumerate(first)
        for j, b in enumerate(second)
        if (
            distance := float(
                np.hypot(
                    a["circle"][0] - b["circle"][0], a["circle"][1] - b["circle"][1]
                )
            )
        )
        < 0.5 * max(a["circle"][2], b["circle"][2])
    )
    pairs, used_first, used_second = [], set(), set()
    for _, i, j in valid:
        if i not in used_first and j not in used_second:
            pairs.append((i, j))
            used_first.add(i)
            used_second.add(j)
    return pairs


def balloon_source(
    pdf: Path, page: Any
) -> tuple[NDArray[Any], list[dict[str, Any]], str]:
    """Working image and balloons of the page, with the source decided balloon by balloon.

    With a vector layer, balloons are detected in it (up to 600 dpi) and in the page image at its
    own resolution (upscaled to 600 dpi, balloons of a poor scan turn blocky and are missed), then
    brought to the layer's scale and paired one to one. Paired and layer-only balloons are read on
    the layer, without the drawing behind; image-only ones (balloons inside the scan) on the page.
    Each balloon carries its «fuente» («capa vectorial» or «imagen»).
    """
    layer = vector_layer(pdf, page.number)
    if layer is None:
        full = page_raster(page)
        return full, [dict(b, fuente="imagen") for b in detect_balloons(full)], "imagen"
    height, width = layer.shape[:2]
    native = page_raster(page)
    sx, sy = width / native.shape[1], height / native.shape[0]
    found = [
        dict(
            b,
            circle=[
                b["circle"][0] * sx,
                b["circle"][1] * sy,
                b["circle"][2] * (sx + sy) / 2,
            ],
        )
        for b in detect_balloons(native)
    ]
    pix = page.get_pixmap(
        matrix=fitz.Matrix(width / page.rect.width, height / page.rect.height),
        colorspace=fitz.csRGB,
        alpha=False,
    )
    full = np.full_like(layer, 255)
    rendered = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    full[: min(height, pix.height), : min(width, pix.width)] = rendered[:height, :width]
    in_layer = detect_balloons(layer)
    if not in_layer:
        return full, [dict(b, fuente="imagen") for b in found], "imagen"
    matched_full = {j for _, j in pair_balloons(in_layer, found)}
    # Working image: the layer up to 1.6 radii around each vector balloon (everything the shifted
    # crops read), except the inside of image-only balloons, which is kept.
    image_only = [b for j, b in enumerate(found) if j not in matched_full]
    use_layer = np.zeros((height, width), np.uint8)
    for group, factor, value in ((in_layer, 1.6, 1), (image_only, 1.1, 0)):
        for b in group:
            x, y, r = b["circle"]
            cv2.circle(use_layer, (round(x), round(y)), round(factor * r), value, -1)
    work = np.where(use_layer[:, :, None] > 0, layer, full)
    balloons = [dict(b, fuente="capa vectorial") for b in in_layer] + [
        dict(b, fuente="imagen") for b in image_only
    ]
    balloons.sort(key=lambda b: (round(b["circle"][1] / 50), b["circle"][0]))
    vector = sum(b["fuente"] == "capa vectorial" for b in balloons)
    if vector == len(balloons):
        return work, balloons, "capa vectorial"
    return (
        work,
        balloons,
        f"mixta ({vector} de la capa vectorial, {len(balloons) - vector} de la imagen)",
    )


def color_mask(rgb: NDArray[Any]) -> NDArray[Any]:
    r, g, b = [c.astype(np.int16) for c in cv2.split(rgb)]
    green = ((g - r) > 14) & ((g - b) > 14)
    blue = ((b - r) > 40) & ((b - g) > 25)
    return (green | blue).astype(np.uint8) * 255


def detect_balloons(rgb: NDArray[Any]) -> list[dict[str, Any]]:
    """Green or blue rings: circle candidates, not whole clusters or known N locations.

    Two passes. First, in a wide range (radius 0.3–3 % of the short side: small scanned balloons
    and large infra-CONVERT ones), the typical balloon size of this page is measured, ignoring
    circles that lie inside another (the holes of «0» or «6» also look like small rings). Then
    balloons are searched only around that size (0.6–1.6 times), at least one radius apart.
    """
    height, width = rgb.shape[:2]
    factor = min(1.0, 3600 / max(width, height))
    small = cv2.resize(rgb, None, fx=factor, fy=factor) if factor < 1 else rgb
    mask = color_mask(small)
    if np.count_nonzero(mask) < 40:
        return []
    blurred = cv2.GaussianBlur(mask, (3, 3), 0.7)
    near_color = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)

    def ring_circles(
        min_r: float, max_r: float, min_dist: float
    ) -> list[tuple[float, float, float, float]]:
        """Hough circles whose contour is at least 65 % coloured ink: a ring."""
        found = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            1,
            min_dist,
            param1=80,
            param2=17,
            minRadius=int(round(min_r)),
            maxRadius=int(round(max_r)),
        )
        accepted = []
        for x, y, radius in [] if found is None else found[0]:
            xs = np.clip(
                np.round(x + radius * np.cos(angles)).astype(int), 0, mask.shape[1] - 1
            )
            ys = np.clip(
                np.round(y + radius * np.sin(angles)).astype(int), 0, mask.shape[0] - 1
            )
            support = float(np.mean(near_color[ys, xs] > 0))
            if support >= 0.65:
                accepted.append((support, float(x), float(y), float(radius)))
        return accepted

    size = min(mask.shape)
    accepted = ring_circles(max(5, size * 0.003), max(12, size * 0.03), 12)
    if len(accepted) >= 5:
        x, y, r = (np.array([c[i] for c in accepted]) for i in (1, 2, 3))
        distance = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
        inside = (
            (r[None, :] > 1.25 * r[:, None])
            & (distance + r[:, None] <= 1.05 * r[None, :])
        ).any(axis=1)
        median = float(np.median(r[~inside]))
        accepted = ring_circles(max(5, 0.6 * median), 1.6 * median, max(8, median))
    scaled = [(s, x / factor, y / factor, r / factor) for s, x, y, r in accepted]
    deduped: list[tuple[float, float, float, float]] = []
    for support, x, y, radius in sorted(scaled, reverse=True):
        if any(np.hypot(x - a, y - b) < 0.9 * min(radius, r) for _, a, b, r in deduped):
            continue
        deduped.append((support, x, y, radius))
    return [
        {
            "box": normalized_box((x - r, y - r, x + r, y + r), width, height),
            "circle": [round(x, 2), round(y, 2), round(r, 2)],
            "candidates": [],
        }
        for _, x, y, r in sorted(deduped, key=lambda c: (round(c[2] / 50), c[1]))
    ]


def rotate(
    rgb: NDArray[Any], balloons: list[dict[str, Any]], quarter_turns: int
) -> tuple[NDArray[Any], list[dict[str, Any]]]:
    """Rotate the page anticlockwise and move the circles along (copies, same order)."""
    rotated = []
    for b in balloons:
        (x, y, r), width = b["circle"], rgb.shape[1]
        height = rgb.shape[0]
        for _ in range(quarter_turns):
            x, y, width, height = y, width - 1 - x, height, width
        rotated.append(dict(b, circle=[x, y, r]))
    return np.ascontiguousarray(np.rot90(rgb, quarter_turns)), rotated


def best_rotation(
    rgb: NDArray[Any], balloons: list[dict[str, Any]], reader: Any, sample: int = 60
) -> int:
    """Orientation in which the own reader is most confident: drawings turned 90° or 180°."""
    chosen = balloons[:: max(1, len(balloons) // sample)]
    confidence = []
    for turns in range(4):
        image, moved = rotate(rgb, chosen, turns) if turns else (rgb, chosen)
        probs = reader.probabilities([text_crop(image, b["circle"]) for b in moved])
        confidence.append(float(np.mean([reader.greedy(p)[1] for p in probs])))
    return int(np.argmax(confidence))


def find_tesseract() -> str | None:
    candidates = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        str(
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs/Tesseract-OCR/tesseract.exe"
        ),
    ]
    return next((str(p) for p in candidates if p and Path(p).is_file()), None)


def read_scan_words(
    rgb: NDArray[Any], page_no: int, executable: str
) -> list[dict[str, Any]]:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = executable
    height, width = rgb.shape[:2]
    factor = min(2.0, 6600 / max(height, width))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    scaled = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    raw = pytesseract.image_to_data(
        scaled, config="--psm 11", output_type=pytesseract.Output.DICT, timeout=120
    )
    words: list[dict[str, Any]] = []
    for i, text in enumerate(raw["text"]):
        score = float(raw["conf"][i])
        if not text.strip() or score < 25:
            continue
        x, y, w, h = [
            raw[key][i] / factor for key in ("left", "top", "width", "height")
        ]
        words.append(
            {
                "id": f"p{page_no}-ocr{len(words)}",
                "page": page_no,
                "text": text.strip(),
                "box": normalized_box((x, y, x + w, y + h), width, height),
                "method": "ocr",
                "score": round(score / 100, 4),
            }
        )
    return words
