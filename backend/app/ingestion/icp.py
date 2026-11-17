"""Balloons of a drawing taken from its infra-CONVERT project (`.icp`).

The `.icp` is the inspection plan made on the drawing: each balloon («stamp») keeps its
visible number and two points in drawing units, the balloon head and the tip that points
at the dimension. Read like this the number is exact: nothing is recognised by OCR.

What is not exact is where the stamps fall on a given PDF, because the PDF can be
printed at another scale, turned or mirrored. Three steps, kept apart:

1. `read_stamps`: number and points of each stamp.
2. `fit_to_balloons` or `fit_at_scale`: the transformation from drawing units to the
   page. The first uses the balloons drawn on the page; the second assumes a 1:1 print
   centred on the sheet and is only accepted when the stamps fall inside it.
3. `place`: stamps on the page, in normalised coordinates.

Format deduced from the files of the project (it is not documented publicly) and
described in conocimiento/planos-globos.md. A file that does not follow it raises
`IcpFormatError`: it is never read approximately.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

STAMP_NAME = b"INFRA_CONVERT_STAMP_"
MAX_LABEL = 40
MAX_COORDINATE = 1e4  # drawing units are about millimetres; an A0 sheet is 1189 mm wide
# A fit on drawn balloons is trusted when it explains this share of them, and at least
# this many. Below that the stamps are not placed: an approximate position would look verified.
MIN_INLIER_SHARE = 0.3
MIN_INLIERS = 10
MIN_TENTATIVE = 6
# Share of the stamps that must fall on the sheet to accept a 1:1 placement.
MIN_INSIDE_SHEET = 0.95
SHEET_MARGIN = 0.05
MM_PER_POINT = 25.4 / 72


class IcpFormatError(ValueError):
    """The file does not have the expected stamp structure."""


@dataclass(frozen=True)
class Stamp:
    number: int  # internal id of the stamp
    label: str  # text shown inside the balloon
    points: tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True)
class Fit:
    """Drawing units → page, in normalised coordinates of the unrotated page."""

    matrix: tuple[tuple[float, float, float], tuple[float, float, float]]
    head: int  # which of the two points of a stamp is the balloon head
    flip: int  # 1, or -1 when the Y axis of the drawing points down on the page
    method: str  # "balloons" (fitted on drawn balloons) or "scale" (1:1 on the sheet)
    inliers: int = 0
    tentative: int = 0

    def apply(self, point: tuple[float, float]) -> tuple[float, float]:
        x, y = point[0], self.flip * point[1]
        (a, b, c), (d, e, f) = self.matrix
        return a * x + b * y + c, d * x + e * y + f


def _prefixed_text_before(data: bytes, end: int) -> bytes | None:
    """The length-prefixed string that ends exactly at `end`."""
    for length in range(1, MAX_LABEL + 1):
        start = end - length
        if start >= 4 and struct.unpack_from("<I", data, start - 4)[0] == length:
            return data[start:end]
    return None


def read_stamps(data: bytes) -> list[Stamp]:
    """Every stamp of an `.icp`, in file order.

    Per stamp the file holds two length-prefixed strings (4-byte little-endian length):
    the visible text and the name `INFRA_CONVERT_STAMP_<n>`, followed by two points as
    six doubles (x1, y1, z1, x2, y2, z2) with z = 0.
    """
    stamps: list[Stamp] = []
    seen: set[int] = set()
    for found in re.finditer(re.escape(STAMP_NAME), data):
        start = found.start()
        if start < 4:
            raise IcpFormatError(f"sello sin longitud en el byte {start}")
        length = struct.unpack_from("<I", data, start - 4)[0]
        name = data[start : start + length]
        match = re.fullmatch(re.escape(STAMP_NAME) + rb"(\d+)", name)
        if not match:
            raise IcpFormatError(f"nombre de sello inesperado en el byte {start}")
        number = int(match[1])
        text = _prefixed_text_before(data, start - 4)
        if text is None:
            raise IcpFormatError(f"sello {number} sin texto visible")
        end = start + length
        if end + 48 > len(data):
            raise IcpFormatError(f"sello {number} sin coordenadas")
        x1, y1, z1, x2, y2, z2 = struct.unpack_from("<6d", data, end)
        values = (x1, y1, x2, y2)
        if (
            z1
            or z2
            or not all(math.isfinite(v) for v in values)
            or max(abs(v) for v in values) > MAX_COORDINATE
        ):
            raise IcpFormatError(f"coordenadas fuera de rango en el sello {number}")
        if number in seen:
            raise IcpFormatError(f"sello {number} repetido")
        seen.add(number)
        stamps.append(
            Stamp(number, text.decode("latin-1").strip(), ((x1, y1), (x2, y2)))
        )
    return stamps


def stamps_digest(stamps: list[Stamp]) -> str:
    """Identity of what was read from a file, independent of the order."""
    rows = sorted((s.label, s.number, [list(p) for p in s.points]) for s in stamps)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def fit_to_balloons(
    stamps: list[Stamp],
    balloons: list[tuple[float, float, float]],
    readings: list[set[str]],
    labels: list[str | None],
    size: tuple[int, int],
) -> Fit | None:
    """Transformation fitted on the balloons drawn on the page, or None if unreliable.

    `balloons` are circles (x, y, radius) in pixels of a page image of `size`
    (width, height); `readings` the numbers read in each one, used only as tentative
    pairs; `labels` the number of each stamp in the same notation, or None.

    A rotation, uniform scale and translation are estimated with RANSAC, trying both
    points of the stamps as head and both directions of the Y axis. Wrong readings are
    tolerated: they are simply not explained by the transformation. The result does not
    depend on how many readings were offered to the user.
    """
    import cv2

    if not balloons or not stamps:
        return None
    by_label: dict[str, list[Stamp]] = {}
    for stamp, label in zip(stamps, labels, strict=True):
        if label:
            by_label.setdefault(label, []).append(stamp)
    radius = float(np.median([b[2] for b in balloons]))
    width, height = size
    best: tuple[int, int, NDArray[Any], int, int] | None = None
    for head in (0, 1):
        for flip in (1, -1):
            source, target = [], []
            for (x, y, _), read in zip(balloons, readings, strict=True):
                for label in sorted(read):
                    unique = by_label.get(label, [])
                    if len(unique) == 1:  # a repeated number cannot anchor the fit
                        px, py = unique[0].points[head]
                        source.append((px, flip * py))
                        target.append((x, y))
            if len(source) < MIN_TENTATIVE:
                continue
            matrix, inliers = cv2.estimateAffinePartial2D(
                np.asarray(source, np.float32),
                np.asarray(target, np.float32),
                method=cv2.RANSAC,
                ransacReprojThreshold=radius * 0.6,
                maxIters=20000,
                confidence=0.999,
            )
            count = int(inliers.sum()) if inliers is not None else 0
            if matrix is not None and (best is None or count > best[0]):
                best = (count, len(source), matrix, head, flip)
    if best is None:
        return None
    count, tentative, matrix, head, flip = best
    if count < max(MIN_INLIERS, MIN_INLIER_SHARE * len(balloons)):
        return None
    scaled = matrix / np.array([[width], [height]], np.float64)
    return Fit(
        matrix=(tuple(map(float, scaled[0])), tuple(map(float, scaled[1]))),  # type: ignore[arg-type]
        head=head,
        flip=flip,
        method="balloons",
        inliers=count,
        tentative=tentative,
    )


def fit_at_scale(
    stamps: list[Stamp], page_width_pt: float, page_height_pt: float
) -> Fit | None:
    """1:1 placement with the origin in the centre of the sheet, for pages without balloons.

    Accepted only if nearly all stamps fall on the sheet: otherwise the page is printed
    at another scale and there is nothing on it to tell which. It is a placement by
    construction, not one checked against the drawing; callers must say so.
    """
    if not stamps or page_width_pt <= 0 or page_height_pt <= 0:
        return None
    width_mm, height_mm = page_width_pt * MM_PER_POINT, page_height_pt * MM_PER_POINT
    fit = Fit(
        matrix=((1 / width_mm, 0.0, 0.5), (0.0, -1 / height_mm, 0.5)),
        head=0,
        flip=1,
        method="scale",
    )
    inside = sum(
        -SHEET_MARGIN < x < 1 + SHEET_MARGIN and -SHEET_MARGIN < y < 1 + SHEET_MARGIN
        for x, y in (fit.apply(s.points[0]) for s in stamps)
    )
    return fit if inside >= MIN_INSIDE_SHEET * len(stamps) else None


def place(stamps: list[Stamp], fit: Fit) -> list[dict[str, Any]]:
    """Head and tip of every stamp on the page (0–1, unrotated page)."""
    placed = []
    for stamp in stamps:
        x, y = fit.apply(stamp.points[fit.head])
        tip_x, tip_y = fit.apply(stamp.points[1 - fit.head])
        placed.append(
            {
                "number": stamp.number,
                "text": stamp.label,
                "x": x,
                "y": y,
                "tip": [round(tip_x, 6), round(tip_y, 6)],
            }
        )
    return placed


def match_balloons(
    placed: list[dict[str, Any]],
    balloons: list[tuple[float, float, float]],
    size: tuple[int, int],
) -> list[int | None]:
    """Index of the stamp of each drawn balloon: the nearest, one to one, within a radius."""
    width, height = size
    pairs = []
    for i, (x, y, radius) in enumerate(balloons):
        for j, stamp in enumerate(placed):
            distance = math.hypot(stamp["x"] * width - x, stamp["y"] * height - y)
            if distance < radius:
                pairs.append((distance, i, j))
    match: list[int | None] = [None] * len(balloons)
    used: set[int] = set()
    for _, i, j in sorted(pairs):
        if match[i] is None and j not in used:
            match[i] = j
            used.add(j)
    return match


@dataclass(frozen=True)
class Placement:
    """The project chosen for a page, how it was placed and its stamps on the page."""

    file: str
    fit: Fit
    stamps: list[dict[str, Any]]
    # Placed by construction only: no drawn balloon confirms the position.
    approximate: bool = False


def choose(
    projects: dict[str, list[Stamp]],
    balloons: list[tuple[float, float, float]],
    readings: list[set[str]],
    normalise: Any,
    size: tuple[int, int],
    page_size_pt: tuple[float, float],
    *,
    single_page: bool,
    stem: str,
) -> tuple[Placement | None, str | None]:
    """Which `.icp` of the folder belongs to this page and where its stamps fall.

    Returns the placement, or None with the reason. Sharing a folder or a name does not
    prove that a project belongs to a drawing: it is only used when the drawn balloons
    agree with it or, on a page without balloons, when exactly one project fits the
    sheet at 1:1.
    """
    if not projects:
        return None, None
    fitted: dict[str, Fit] = {}
    for name, stamps in projects.items():
        fit = fit_to_balloons(
            stamps, balloons, readings, [normalise(s.label) for s in stamps], size
        )
        if fit:
            fitted[name] = fit
    if fitted:
        name = max(fitted, key=lambda key: (fitted[key].inliers, key))
        return Placement(name, fitted[name], place(projects[name], fitted[name])), None
    if not single_page:
        return None, (
            "hay un .icp junto al plano, pero no se ha podido situar: en un PDF de "
            "varias páginas hacen falta globos dibujados"
        )
    at_scale: dict[str, tuple[Fit, list[dict[str, Any]]]] = {}
    for name, stamps in projects.items():
        scale = fit_at_scale(stamps, *page_size_pt)
        if scale is None:
            continue
        placed = place(stamps, scale)
        matched = sum(j is not None for j in match_balloons(placed, balloons, size))
        # Drawn balloons that do not fall under the stamps contradict a 1:1 print.
        if len(balloons) >= MIN_INLIERS and matched < MIN_INLIER_SHARE * len(balloons):
            continue
        at_scale[name] = (scale, placed)
    if not at_scale:
        return None, (
            "hay un .icp junto al plano, pero no cuadra con esta hoja: no se han "
            "situado sus globos"
        )
    same_name = [
        name for name in at_scale if name.rsplit(".", 1)[0].lower() == stem.lower()
    ]
    if len(same_name) == 1:
        name = same_name[0]
    elif len(at_scale) == 1:
        name = next(iter(at_scale))
    else:
        return None, (
            "hay varios .icp que podrían corresponder a este plano y nada en la "
            "página permite elegir: no se han situado sus globos"
        )
    scale, placed = at_scale[name]
    return (
        Placement(name, scale, placed, approximate=len(balloons) < MIN_INLIERS),
        None,
    )
