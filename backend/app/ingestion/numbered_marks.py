"""Conservative No./N° proposals for scanned drawings, independent of balloon OCR.

These readings are never verified identities. Context rejection is intentionally local:
it reduces view-list matches, and can also omit a real dimension near an annotation.
"""

import hashlib
import re
from typing import Any

import fitz
import numpy as np

PREFIX = re.compile(r"N(?:[o0]\s*[.,．]|[°º])\s*(\d{3,4})(\s*[ΦφØø±\dR(].*)?", re.I)
CONTEXT = re.compile(
    r"\b(VIEW|SECTION|DETAIL|GENERAL NOTES?|REVISION|ADDED|DELETED)\b", re.I
)
MIN_MARKS = 20


def dimension_label(text: str) -> str | None:
    match = PREFIX.fullmatch(text.strip())
    # The supported style has three or four significant digits. 001–099 are
    # commonly note references in these documents, not the measured cota labels.
    if not match or int(match[1]) < 100 or "no" in (match[2] or "").lower():
        return None
    return "N" + str(int(match[1]))


def proposals(tokens: list[dict[str, Any]], page: int) -> list[dict[str, Any]]:
    parsed = []
    contexts = []
    for token in tokens:
        text = token["text"].strip()
        polygon = np.asarray(token["polygon"], dtype=float)
        center = polygon.mean(axis=0)
        match = PREFIX.fullmatch(text)
        if match and dimension_label(text):
            parsed.append((token, match, polygon, center))
        if context := CONTEXT.search(text):
            contexts.append((center, context[1].upper()))
    candidates: list[dict[str, Any]] = []
    for token, match, polygon, center in parsed:
        paired = any(
            other_match[1] != match[1]
            and abs(other_center[0] - center[0]) < 0.012
            and 0.003 < abs(other_center[1] - center[1]) < 0.015
            for _, other_match, _, other_center in parsed
        )
        if any(
            abs(point[0] - center[0]) < 0.045
            and -0.03 < point[1] - center[1] < 0.005
            and (paired or name not in {"VIEW", "SECTION", "DETAIL"})
            for point, name in contexts
        ):
            continue
        # Locate the prefix within a token that may also contain the dimension value.
        start = (polygon[0] + polygon[3]) / 2
        end = (polygon[1] + polygon[2]) / 2
        end = start + (end - start) * match.end(1) / max(1, len(token["text"].strip()))
        padding = np.abs(polygon[3] - polygon[0]).max() * 0.15
        box = [
            float(min(start[0], end[0]) - padding),
            float(min(start[1], end[1]) - padding),
            float(max(start[0], end[0]) + padding),
            float(max(start[1], end[1]) + padding),
        ]
        box = [round(min(1.0, max(0.0, v)), 5) for v in box]
        label = "N" + str(int(match[1]))
        candidates.append(
            {
                "page": page,
                "box": box,
                "method": "numbered",
                "candidates": [
                    {
                        "label": label,
                        "readings": [
                            {
                                "method": "No. OCR",
                                "text": token["text"],
                                "score": float(token.get("score", 0.0)),
                            }
                        ],
                    }
                ],
            }
        )
    output: list[dict[str, Any]] = []
    for candidate in sorted(
        candidates,
        key=lambda c: (
            -len(c["candidates"][0]["label"]),
            -c["candidates"][0]["readings"][0]["score"],
        ),
    ):
        x, y, x1, y1 = candidate["box"]
        center = ((x + x1) / 2, (y + y1) / 2)
        if any(
            abs((other["box"][0] + other["box"][2]) / 2 - center[0]) < 0.012
            and abs((other["box"][1] + other["box"][3]) / 2 - center[1]) < 0.012
            and other["candidates"][0]["label"].startswith(
                candidate["candidates"][0]["label"]
            )
            for other in output
        ):
            continue
        candidate["id"] = (
            f"p{page}-no-"
            + hashlib.sha256(repr(candidate["box"]).encode()).hexdigest()[:12]
        )
        output.append(candidate)
    return output


def read_page(page: Any, engine: Any) -> list[dict[str, Any]]:
    scale = min(6.0, max(3.0, 4700 / max(1.0, page.rect.width)))
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
    )
    rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, 3
    )
    tokens = []
    for rotated in (False, True):
        pixels = np.rot90(rgb, -1) if rotated else rgb
        for top in range(0, max(1, pixels.shape[0] - 240), 1360):
            for left in range(0, max(1, pixels.shape[1] - 240), 1360):
                tile = np.ascontiguousarray(
                    pixels[top : top + 1600, left : left + 1600]
                )
                if (tile < 200).mean() < 0.002:
                    continue
                result, _ = engine(tile)
                for box, text, score in result or []:
                    polygon = np.asarray(box, dtype=float) + (left, top)
                    if rotated:
                        polygon = np.column_stack(
                            (polygon[:, 1], pixmap.height - 1 - polygon[:, 0])
                        )
                    polygon /= (pixmap.width, pixmap.height)
                    tokens.append(
                        {
                            "text": text,
                            "score": float(score),
                            "polygon": polygon.round(5).tolist(),
                        }
                    )
    return proposals(tokens, page.number + 1)
