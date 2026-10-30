"""Balloon numbers: RapidOCR and the own reader (ONNX), combined with one number per drawing.

Ported from the drawing-search prototype (prototypes/data-explorer: buscar_en_plano.py,
comparar_ocr_globos.py and entrenar_lector_globos.py), which documents how each step was measured.
The own reader is a small CRNN trained only on synthetic balloon numbers, exported to ONNX.
Readings remain automatic proposals: their score is not a calibrated probability.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from app.ingestion.drawing_version import MODEL, THRESHOLDS

logger = logging.getLogger(__name__)
# Five crops one pixel apart: with digits of a few pixels, one pixel changes every reader.
SHIFTS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
Readings = list[tuple[str, float]]


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


def luma(rgb: NDArray[Any]) -> NDArray[Any]:
    # JPEG scans keep colour at half resolution (4:2:0): luminance is the sharp channel.
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)[:, :, 0]


def ink_box(rgb: NDArray[Any], circle: list[float]) -> tuple[int, int, int, int] | None:
    """Box of the number inside the balloon: dark ink inside that does not touch the ring.

    Drawing lines and the ring itself cross the inner border and are discarded. Without isolated
    ink (for example, a line crossing the number) it returns None.
    """
    x, y, radius = round(circle[0]), round(circle[1]), circle[2]
    inner = int(radius * 0.82)
    if inner < 4 or y - inner < 0 or x - inner < 0:
        return None
    gray = luma(rgb[y - inner : y + inner + 1, x - inner : x + inner + 1])
    if gray.shape != (2 * inner + 1, 2 * inner + 1):
        return None
    yy, xx = np.mgrid[-inner : inner + 1, -inner : inner + 1]
    distance = np.hypot(xx, yy)
    inside = distance <= inner
    if np.median(gray[inside]) < 128:
        gray = 255 - gray
    threshold, _ = cv2.threshold(
        gray[inside].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    ink = ((gray <= threshold) & inside).astype(np.uint8)  # OpenCV Otsu: background > t
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    edge = np.unique(labels[(distance >= inner - 1.5) & inside])
    keep = [
        i for i in range(1, count) if i not in edge and stats[i, cv2.CC_STAT_AREA] >= 2
    ]
    if not keep:
        return None
    x0 = min(stats[i, 0] for i in keep)
    y0 = min(stats[i, 1] for i in keep)
    x1 = max(stats[i, 0] + stats[i, 2] for i in keep)
    y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
    return x - inner + x0, y - inner + y0, x - inner + x1, y - inner + y1


def text_crop(
    rgb: NDArray[Any], circle: list[float], shift: tuple[int, int] = (0, 0)
) -> NDArray[Any]:
    """Luminance crop of the number, centred on its ink and scaled to its height.

    The number fills 44 % of the crop height whatever its size relative to the balloon. Without
    isolated ink it falls back to the inner band of the balloon. Light-on-dark is inverted.
    """
    x, y, radius = circle
    width, height, scale = 0.84, 0.43, 4.0
    box = ink_box(rgb, circle)
    if box:
        text_h, text_w = box[3] - box[1], box[2] - box[0]
        crop_h = max(text_h / 0.44, text_w * 1.1 / 1.95)
        x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        width, height, radius = 0.975, 0.5, crop_h
        scale = scale * 12 / max(12.0, crop_h)
    x, y = round(x) + shift[0], round(y) + shift[1]
    half_w, half_h, margin = (
        max(3, int(radius * width)),
        max(3, int(radius * height)),
        2,
    )
    region = rgb[
        max(0, y - half_h - margin) : y + half_h + 1 + margin,
        max(0, x - half_w - margin) : x + half_w + 1 + margin,
    ]
    gray = luma(region)[margin:-margin, margin:-margin]
    if gray.size and np.median(gray) < 128:
        gray = 255 - gray
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(big, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(255,))


class OwnReader:
    """The own CRNN in ONNX: grey crops in, CTC character probabilities out."""

    def __init__(self, model: Path = MODEL) -> None:
        import onnxruntime as ort

        meta = json.loads(model.with_suffix(".json").read_text(encoding="utf-8"))
        self.characters: list[str] = meta["caracteres"]
        dimensions = meta["entrada"]
        if (
            not isinstance(self.characters, list)
            or not self.characters
            or any(not isinstance(c, str) or len(c) != 1 for c in self.characters)
            or len(set(self.characters)) != len(self.characters)
            or not isinstance(dimensions, list)
            or len(dimensions) != 2
            or any(type(n) is not int or n <= 0 for n in dimensions)
        ):
            raise ValueError("Metadatos del lector de globos no válidos")
        self.height, self.width = dimensions
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        try:
            self.session = ort.InferenceSession(
                str(model), options, providers=["CPUExecutionProvider"]
            )
        except Exception as error:
            # ONNX Runtime exposes several native exception types for missing/invalid models.
            raise ValueError("No se ha podido cargar el modelo de globos") from error
        if (
            self.session.get_inputs()[0].shape[2:] != dimensions
            or self.session.get_outputs()[0].shape[-1] != len(self.characters) + 1
        ):
            raise ValueError("Los metadatos no corresponden al modelo de globos")

    def probabilities(self, crops: list[NDArray[Any]]) -> NDArray[Any]:
        if not crops:
            return np.zeros((0, 0, len(self.characters) + 1), np.float32)
        images = np.stack(
            [
                cv2.resize(c, (self.width, self.height), interpolation=cv2.INTER_AREA)
                for c in crops
            ]
        )
        batch = ((images.astype(np.float32) / 255 - 0.5) / 0.5)[:, None]
        logits = np.concatenate(
            [
                self.session.run(None, {"imagen": batch[i : i + 256]})[0]
                for i in range(0, len(batch), 256)
            ]
        )
        exponent = np.exp(logits - logits.max(2, keepdims=True))
        probs: NDArray[Any] = exponent / exponent.sum(2, keepdims=True)
        return probs

    def greedy(self, probs: NDArray[Any]) -> tuple[str, float]:
        """CTC best path: text and mean probability of its characters."""
        best, score = probs.argmax(1), probs.max(1)
        text, chosen, previous = [], [], 0
        for t, k in enumerate(best):
            if k and k != previous:
                text.append(self.characters[k - 1])
                chosen.append(score[t])
            previous = k
        return "".join(text), float(np.mean(chosen)) if chosen else 0.0

    def read(self, crops: list[NDArray[Any]]) -> list[Readings]:
        return [[self.greedy(p)] for p in self.probabilities(crops)]


@lru_cache
def own_reader() -> OwnReader | None:
    """The shipped model, or None if it is missing or onnxruntime cannot load it."""
    try:
        return OwnReader()
    except (
        ImportError,
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
    ) as error:
        logger.warning("Lector propio de globos no disponible: %s", error)
        return None


def read_balloons(
    rgb: NDArray[Any], balloons: list[dict[str, Any]], engine: Any
) -> None:
    """RapidOCR on three views of each balloon; all complete identifiers, with their observations."""
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


def merge(runs: list[list[Readings]]) -> list[Readings]:
    """Several readings of the same balloons: mean score of each identifier, best first."""
    merged = []
    for options in zip(*runs, strict=True):
        totals: dict[str, float] = {}
        for candidates in options:
            for text, score in candidates:
                label = label_of(text)
                if label:
                    totals[label] = totals.get(label, 0.0) + score / len(options)
        merged.append(sorted(totals.items(), key=lambda kv: -kv[1]))
    return merged


def unique_assignment(
    predictions: list[Readings], floor: float = 1e-3
) -> list[Readings]:
    """Each identifier appears once per drawing: assignment of maximum joint probability.

    It does not use positions or neighbouring numbers. A balloon without a candidate above
    `floor` stays unread instead of receiving a spare number. One number per drawing holds in
    the 20 referenced drawings of the prototype; it is an assumption, not a guarantee.
    """
    from scipy.optimize import linear_sum_assignment

    labels = sorted({label for p in predictions for label, _ in p})
    column = {label: i for i, label in enumerate(labels)}
    n = len(predictions)
    cost = np.full((n, len(labels) + n), 50.0)
    cost[np.arange(n), len(labels) + np.arange(n)] = -np.log(floor)
    for i, candidates in enumerate(predictions):
        for label, score in candidates:
            cost[i, column[label]] = -np.log(max(score, 1e-12))
    out: list[Readings] = []
    for i, j in zip(*linear_sum_assignment(cost), strict=True):
        if j >= len(labels):
            out.append([])
            continue
        chosen = labels[j]
        out.append(
            [(chosen, dict(predictions[i])[chosen])]
            + [(label, s) for label, s in predictions[i] if label != chosen]
        )
    return out


def offer_readings(
    balloons: list[dict[str, Any]],
    choices: list[Readings],
    rapid: list[Readings],
    own: list[Readings],
    thresholds: dict[str, float] = THRESHOLDS,
) -> None:
    """Write the combined reading in each balloon if it reaches the threshold of its source."""
    for balloon, choice, by_rapid, by_own in zip(
        balloons, choices, rapid, own, strict=True
    ):
        balloon["candidates"] = []
        if choice and choice[0][1] >= thresholds[balloon.get("fuente", "imagen")]:
            label, value = choice[0]
            readings = [
                {"method": "Combinado", "text": label[1:], "score": round(value, 4)}
            ]
            readings += [
                {"method": "RapidOCR", "text": text[1:], "score": round(s, 4)}
                for text, s in by_rapid[:1]
            ]
            readings += [
                {"method": "Lector propio", "text": text[1:], "score": round(s, 4)}
                for text, s in by_own[:1]
            ]
            balloon["candidates"] = [{"label": label, "readings": readings}]


def read_balloons_combined(
    rgb: NDArray[Any],
    balloons: list[dict[str, Any]],
    engine: Any,
    reader: OwnReader,
    thresholds: dict[str, float] = THRESHOLDS,
) -> None:
    """RapidOCR and the own reader vote with their scores; then one number per drawing."""
    copies = [dict(b, candidates=[]) for b in balloons]
    read_balloons(rgb, copies, engine)
    rapid: list[Readings] = [
        [
            (
                b["candidates"][0]["label"],
                max(r["score"] for r in b["candidates"][0]["readings"]),
            )
        ]
        if b["candidates"]
        else []
        for b in copies
    ]
    own = merge(
        [
            reader.read([text_crop(rgb, b["circle"], shift) for b in balloons])
            for shift in SHIFTS
        ]
    )
    choices = unique_assignment(merge([rapid, own]))
    offer_readings(balloons, choices, rapid, own, thresholds)
