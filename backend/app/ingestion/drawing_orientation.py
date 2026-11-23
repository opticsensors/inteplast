"""Clockwise correction to apply on top of a drawing page's PDF rotation."""

import math
import shutil
import subprocess
from collections import Counter

import fitz


def _dominant(scores: Counter[int]) -> int | None:
    best = scores.most_common(2)
    if not best or best[0][1] < 12:
        return None
    if len(best) > 1 and best[0][1] < 1.5 * best[1][1]:
        return None
    return best[0][0]


def _readable_letters(pixmap: fitz.Pixmap, executable: str) -> int:
    # Sparse text mode reads the title block despite the ruling and dimension lines.
    result = subprocess.run(
        [executable, "stdin", "stdout", "--dpi", "150", "--psm", "11", "tsv"],
        input=pixmap.tobytes("png"),
        capture_output=True,
        timeout=8,
    )
    score = 0
    for row in result.stdout.decode("utf-8", errors="replace").splitlines()[1:]:
        fields = row.split("\t", 11)
        if len(fields) == 12 and fields[0] == "5" and float(fields[10]) >= 65:
            letters = sum(ch.isalpha() for ch in fields[11])
            if letters >= 3:
                score += letters
    return score


def display_rotation(page: fitz.Page) -> int:
    """Prefer the text baseline; on scans compare readable text in the title block."""
    original = page.rotation
    scores: Counter[int] = Counter()
    blocks = page.get_text(
        "dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
    )["blocks"]
    for block in blocks:
        for line in block.get("lines", []):
            dx, dy = line["dir"]
            angle = math.degrees(math.atan2(dy, dx))
            cardinal = round(angle / 90) * 90
            if abs(cardinal - angle) < 5:
                for span in line["spans"]:
                    letters = sum(char.isalpha() for char in span["text"])
                    if letters >= 3:
                        scores[(-cardinal - original) % 360] += letters
    direction = _dominant(scores)
    if direction is not None:
        return direction

    executable = shutil.which("tesseract")
    if not executable:
        return 0
    # Compare the *displayed* lower-right corner in each candidate orientation.
    # Render just that area, at bounded resolution even on large-format sheets.
    scale = min(3.0, 2400 / max(page.rect.width, page.rect.height, 1))
    scores.clear()
    try:
        for angle in (0, 90, 180, 270):
            page.set_rotation((original + angle) % 360)
            rect = page.rect
            clip = fitz.Rect(rect.width * 0.55, rect.height * 0.70, rect.x1, rect.y1)
            crop = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale), clip=clip, colorspace=fitz.csGRAY
            )
            scores[angle] = _readable_letters(crop, executable)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    finally:
        page.set_rotation(original)
    return _dominant(scores) or 0
