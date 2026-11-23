"""Draw one upright PDF page as a PNG, in its own process.

PyMuPDF does not support use from several threads, and a damaged PDF can hang or crash
it: the API runs this module as a child process with a time limit.
Usage: python -m app.thumbnail_converter <source.pdf> <target> <width> [page]
"""

import sys

import fitz
from PIL import Image, PngImagePlugin

from app.ingestion.drawing_orientation import display_rotation


def render(source: str, target: str, width: int, page_number: int = 1) -> None:
    with fitz.open(source) as pdf:
        if pdf.needs_pass:
            raise ValueError("El PDF está protegido por contraseña.")
        if pdf.page_count == 0:
            raise ValueError("El PDF no tiene páginas.")
        if not 1 <= page_number <= pdf.page_count:
            raise ValueError("La página no existe en el PDF.")
        page = pdf[page_number - 1]
        rotation = display_rotation(page)
        page.set_rotation((page.rotation + rotation) % 360)
        scale = width / max(page.rect.width, 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("display_rotation", str(rotation))
        Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples).save(
            target, format="PNG", pnginfo=meta
        )


if __name__ == "__main__":
    try:
        render(
            sys.argv[1],
            sys.argv[2],
            int(sys.argv[3]),
            int(sys.argv[4]) if len(sys.argv) > 4 else 1,
        )
    except Exception as error:  # Reported to the parent through stderr and the code.
        sys.stderr.write((str(error) or type(error).__name__) + "\n")
        sys.exit(1)
