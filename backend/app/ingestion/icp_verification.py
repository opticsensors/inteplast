"""Strict check that an infra-CONVERT project (.icp) belongs to a drawing page.

Three conditions must hold on a page, as in the trial of 18/11/2026:

1. The project is placed on the sheet at 1:1 (`icp.fit_at_scale`), without using the
   balloons of the drawing to fit it.
2. A ring detector, independent of the drawing index, finds the drawn balloons: green or
   blue closed rings, detected by their hole so that a leader line touching the outside
   does not hide them. Exactly one candidate project must put its stamps on at least 10
   rings, half of the rings and half of its stamps; no candidate may be unreadable.
3. The drawing reader of the app associates that page with that project on its own
   (`drawing.balloon_source` and `icp.choose`, without OCR readings): one project, placed
   with the drawn balloons, not as an approximate position, and the verified numbers are
   among the ones it places. Without readings the reader only places a project on a
   single-page PDF, so a sheet of a multi-page PDF is never verified: two drawings can
   share balloon positions with different numbers, and nothing would tell them apart.

On the 21 pieces of Exemples this accepted 7 files and none of 283 projects of other
pieces. It is a positive label only: a page that does not pass is not proved wrong.
"""

import math
import re
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np

from app.ingestion import icp

# v2 (18/11/2026): the drawing reader must also associate the page. Bumping it
# invalidates every cached result of the previous rule.
RECIPE = "icp-verification-v2"
# Fixed resolution: at most 4 pixels per point and 3200 pixels on the long side.
MAX_SCALE = 4.0
MAX_SIDE = 3200
MIN_MATCHES = 10
MIN_SHARE = 0.5


def page_rings(page: Any) -> tuple[list[tuple[float, float, float]], tuple[int, int]]:
    """Centres and radii of the green or blue rings of a page, in pixels."""
    rect = page.rect
    scale = min(MAX_SCALE, MAX_SIDE / max(rect.width, rect.height))
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
    )
    image = np.frombuffer(pixmap.samples, np.uint8).reshape(
        pixmap.height, pixmap.width, 3
    )
    red, green, blue = cv2.split(image)
    greenish = (cv2.subtract(green, red) > 14) & (cv2.subtract(green, blue) > 14)
    bluish = (cv2.subtract(blue, red) > 40) & (cv2.subtract(blue, green) > 25)
    mask = ((greenish | bluish) * 255).astype("uint8")
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    rings: list[tuple[float, float, float]] = []
    if hierarchy is not None:
        shortest = min(mask.shape)
        for index, contour in enumerate(contours):
            # Only holes: the inner edge of a ring has a parent contour.
            if hierarchy[0, index, 3] < 0 or len(contour) < 7:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            minor, major = min(w, h), max(w, h)
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            if minor < 8 or not shortest * 0.0025 <= minor <= shortest * 0.066:
                continue
            if major / minor > 1.25 or perimeter == 0:
                continue
            if not 0.69 * w * h <= area <= 0.86 * w * h:
                continue
            if 4 * math.pi * area / perimeter**2 < 0.71:
                continue
            rings.append((x + (w - 1) / 2, y + (h - 1) / 2, (w + h) / 4))
    return rings, (pixmap.width, pixmap.height)


def page_matches(
    stamps: list[icp.Stamp],
    rings: list[tuple[float, float, float]],
    size: tuple[int, int],
    page_size_pt: tuple[float, float],
) -> list[str]:
    """Stamps of a project that fall on rings at 1:1, if enough of both agree."""
    fit = icp.fit_at_scale(stamps, *page_size_pt)
    if fit is None or len(rings) < MIN_MATCHES:
        return []
    placed = icp.place(stamps, fit)
    hits = [j for j in icp.match_balloons(placed, rings, size) if j is not None]
    needed = max(MIN_MATCHES, MIN_SHARE * len(rings), MIN_SHARE * len(stamps))
    return [placed[j]["text"] for j in hits] if len(hits) >= needed else []


def cota(text: str) -> str | None:
    match = re.fullmatch(r"N?\s*([1-9][0-9]*(?:\.[0-9]+)?)", text.strip(), re.I)
    return f"N{match[1]}" if match else None


def reader_association(
    pdf: Path, page: Any, projects: dict[str, list[icp.Stamp]], single_page: bool
) -> tuple[str, str | None, set[str]]:
    """How the drawing reader of the app associates the page, without OCR readings.

    Returns the reason (`scale_and_drawn_balloons`, `approximate_scale`, `ambiguous_icp`
    or `no_valid_fit`), the chosen project and the numbers it places.
    """
    from app.ingestion import drawing  # Heavy: only for pages that passed the check.
    from app.ingestion.balloon_reader import label_of

    image, balloons, _ = drawing.balloon_source(pdf, page)
    size = (image.shape[1], image.shape[0])
    del image
    circles = [tuple(b["circle"][:3]) for b in balloons]
    empty: list[set[str]] = [set() for _ in balloons]
    sheet = (page.rect.width, page.rect.height)

    def placed(name: str) -> Any:
        placement, _ = icp.choose(
            {name: projects[name]},
            circles,
            empty,
            label_of,
            size,
            sheet,
            single_page=single_page,
            stem=pdf.stem,
        )
        return placement

    options = [name for name in sorted(projects) if placed(name)]
    signatures = {icp.stamps_digest(projects[name]) for name in options}
    if len(signatures) != 1:
        return ("ambiguous_icp" if signatures else "no_valid_fit"), None, set()
    chosen = options[0]
    placement = placed(chosen)
    numbers = {n for stamp in placement.stamps if (n := cota(stamp["text"]))}
    reason = (
        "approximate_scale" if placement.approximate else "scale_and_drawn_balloons"
    )
    return reason, chosen, numbers


def verify(pdf: Path, projects: dict[str, Path]) -> dict[str, Any]:
    """Pages of the drawing verified by exactly one of its candidate projects."""
    read: dict[str, list[icp.Stamp] | None] = {}
    for name, path in projects.items():
        try:
            read[name] = icp.read_stamps(path.read_bytes()) or None
        except (ValueError, OSError):
            read[name] = None
    readable = {name: stamps for name, stamps in read.items() if stamps}
    pages = []
    with fitz.open(pdf) as document:
        single_page = len(document) == 1
        for page in document:
            record: dict[str, Any] = {"page": page.number + 1, "rings": 0}
            if readable and len(readable) == len(read):
                rings, size = page_rings(page)
                record["rings"] = len(rings)
                valid = {
                    name: matches
                    for name, stamps in sorted(readable.items())
                    if (
                        matches := page_matches(
                            stamps, rings, size, (page.rect.width, page.rect.height)
                        )
                    )
                }
                if len(valid) == 1:
                    name, matches = next(iter(valid.items()))
                    record.update(strict=name, matched=len(matches))
                    reason, chosen, numbers = reader_association(
                        pdf, page, readable, single_page
                    )
                    exact = {n for text in matches if (n := cota(text))}
                    record["association"] = reason
                    if (
                        reason == "scale_and_drawn_balloons"
                        and chosen is not None
                        and icp.stamps_digest(readable[chosen])
                        == icp.stamps_digest(readable[name])
                        and exact
                        and exact <= numbers
                    ):
                        record["project"] = name
            pages.append(record)
    verified = [page for page in pages if page.get("project")]
    return {
        "verified": bool(verified),
        "pages": pages,
        "unreadable": sorted(name for name, stamps in read.items() if not stamps),
    }
