"""Check a PDF drawing identifier on its first page in a separate MuPDF process."""

import hashlib
import json
import re
import sys
from pathlib import Path


def matches_title_page(path: Path, filename: str) -> bool:
    import pymupdf

    identifiers = [
        term
        for term in re.findall(r"[A-Z0-9]+", filename.upper())
        if len(term) >= 6 and re.search("[A-Z]", term) and re.search(r"\d", term)
    ]
    if not identifiers:
        return False
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        if not doc.is_pdf or doc.needs_pass or not len(doc):
            return False
        text = doc[0].get_text().upper()
    compact = re.sub(r"\s+", "", text)
    return any(term in compact for term in identifiers) and bool(
        re.search(r"\b(?:TOLERANCES?|ZEICHNUNG|DRAWING|ISO\s*\d+|DIN\s*\d+)\b", text)
    )


def visible_pages(path: Path) -> str | None:
    """Corroborate drawing content across different PDF serializations."""
    import pymupdf

    digest = hashlib.sha256()
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        if not doc.is_pdf or doc.needs_pass or not 1 <= len(doc) <= 8:
            return None
        has_ink = False
        for page in doc:
            extent = max(page.rect.width, page.rect.height)
            if extent <= 0:
                return None
            zoom = min(1.0, 1500 / extent)
            image = page.get_pixmap(
                matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY  # type: ignore[no-untyped-call]
            )
            pixels = image.samples
            has_ink |= min(pixels) < 200 and max(pixels) > 230
            digest.update(repr((tuple(page.rect), image.width, image.height)).encode())
            digest.update(pixels)
    return digest.hexdigest() if has_ink else None


if __name__ == "__main__":
    path = Path(sys.argv[1])
    sys.stdout.write(
        json.dumps(
            visible_pages(path)
            if len(sys.argv) == 2
            else matches_title_page(path, sys.argv[2])
        )
    )
