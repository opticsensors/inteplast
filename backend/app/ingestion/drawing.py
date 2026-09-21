"""PDF text, balloon detection and fallible OCR candidates for the web drawing index."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np
from numpy.typing import NDArray
from PIL import Image

logger = logging.getLogger(__name__)
INDEX_VERSION = 2


def build_index(
    pdf: Path, destination: Path, *, use_ocr: bool = True
) -> dict[str, Any]:
    """Read one PDF version. EvidenceJob owns caching and human reviews.

    Coordinates and candidate IDs retain the existing web contract so that a
    reviewed location remains attached to the same bytes after this refactor.
    OCR readings are proposals, never verified characteristic identities.
    """
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    engine = None
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
        if not tesseract:
            notices.append(
                "Sin Tesseract: no se ha extraído el texto general de páginas escaneadas."
            )
    data: dict[str, Any] = {
        "signature": {
            "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "version": INDEX_VERSION,
            "ocr": use_ocr,
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
            balloons = detect_balloons(rgb)
            for balloon in balloons:
                position = hashlib.sha256(
                    json.dumps(balloon["box"]).encode()
                ).hexdigest()[:12]
                balloon.update(id=f"p{number}-b{position}", page=number)
            if engine is not None and balloons:
                read_balloons(rgb, balloons, engine)
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
                }
            )
    return data


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
    """Preserve a full-page source raster when possible; otherwise render the PDF."""
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


def color_mask(rgb: NDArray[Any]) -> NDArray[Any]:
    r, g, b = [c.astype(np.int16) for c in cv2.split(rgb)]
    green = ((g - r) > 14) & ((g - b) > 14)
    blue = ((b - r) > 40) & ((b - g) > 25)
    return (green | blue).astype(np.uint8) * 255


def detect_balloons(rgb: NDArray[Any]) -> list[dict[str, Any]]:
    """Circular annotation candidates, not whole connected clusters or known N locations."""
    height, width = rgb.shape[:2]
    factor = min(1.0, 3600 / max(width, height))
    small = cv2.resize(rgb, None, fx=factor, fy=factor) if factor < 1 else rgb
    mask = color_mask(small)
    if np.count_nonzero(mask) < 40:
        return []
    size = min(mask.shape)
    min_r, max_r = max(6, round(size * 0.004)), max(10, round(size * 0.011))
    circles = cv2.HoughCircles(
        cv2.GaussianBlur(mask, (3, 3), 0.7),
        cv2.HOUGH_GRADIENT,
        1,
        max(12, min_r * 1.5),
        param1=80,
        param2=17,
        minRadius=min_r,
        maxRadius=max_r,
    )
    if circles is None:
        return []
    near_color = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    accepted = []
    for x, y, radius in circles[0]:
        xs = np.clip(
            np.round(x + radius * np.cos(angles)).astype(int), 0, mask.shape[1] - 1
        )
        ys = np.clip(
            np.round(y + radius * np.sin(angles)).astype(int), 0, mask.shape[0] - 1
        )
        support = float(np.mean(near_color[ys, xs] > 0))
        if support >= 0.65:
            accepted.append(
                (support, float(x / factor), float(y / factor), float(radius / factor))
            )
    deduped: list[tuple[float, float, float, float]] = []
    for support, x, y, radius in sorted(accepted, reverse=True):
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


def read_balloons(
    rgb: NDArray[Any], balloons: list[dict[str, Any]], engine: Any
) -> None:
    height, width = rgb.shape[:2]
    for i, balloon in enumerate(balloons):
        x, y, radius = balloon["circle"]
        x, y = round(x), round(y)
        half_w, half_h = max(3, round(radius * 0.86)), max(3, round(radius * 0.43))
        roi = rgb[
            max(0, y - half_h) : min(height, y + half_h + 1),
            max(0, x - half_w) : min(width, x + half_w + 1),
        ]
        r, g, b = [c.astype(np.int16) for c in cv2.split(roi)]
        # Second view removes black drawing lines; it remains a fallible OCR observation.
        strength = np.maximum(np.minimum(g - r, g - b), np.minimum(b - r, b - g))
        ink = (255 - np.clip(strength * 4, 0, 255)).astype(np.uint8)
        narrow_w, narrow_h = max(3, int(radius * 0.84)), max(3, int(radius * 0.43))
        narrow = rgb[
            max(0, y - narrow_h) : min(height, y + narrow_h + 1),
            max(0, x - narrow_w) : min(width, x + narrow_w + 1),
            0,
        ]
        readings: dict[str, list[dict[str, Any]]] = {}
        for method, gray in (
            ("Canal rojo", roi[:, :, 0]),
            ("Tinta de color", ink),
            ("Canal rojo · interior", narrow),
        ):
            expanded = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            expanded = cv2.copyMakeBorder(
                expanded, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(255,)
            )
            raw, _ = engine(
                cv2.cvtColor(expanded, cv2.COLOR_GRAY2BGR), use_det=False, use_cls=False
            )
            for text, score, *_ in raw or []:
                label = ocr_number(text)
                if label and score >= 0.35:
                    readings.setdefault(label, []).append(
                        {
                            "method": method,
                            "text": text,
                            "score": round(float(score), 4),
                        }
                    )
        balloon["candidates"] = [
            {"label": label, "readings": observations}
            for label, observations in sorted(
                readings.items(),
                key=lambda item: (-len(item[1]), -max(r["score"] for r in item[1])),
            )
        ]
        if (i + 1) % 50 == 0:
            logger.info(f"  Globos procesados: {i + 1}/{len(balloons)}")
