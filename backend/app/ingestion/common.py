"""Numeric validity and document provenance shared by evidence readers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


def number(value: Any) -> float | None:
    """Missing, invalid and Excel error values are never interpreted as zero."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if math.isfinite(value) else None
    return None


def source(path: Path, root: Path, locator: str = "") -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "url": path.resolve().as_uri(),
        "locator": locator,
    }


def result(value: Any, lower: Any, upper: Any) -> str:
    if any(number(x) is None for x in (value, lower, upper)) or lower > upper:
        return "unknown"
    return "inside" if lower - 1e-9 <= value <= upper + 1e-9 else "outside"
