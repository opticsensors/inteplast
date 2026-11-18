"""Draw the first page of a PDF as a PNG, in its own process.

PyMuPDF does not support use from several threads, and a damaged PDF can hang or crash
it: the API runs this module as a child process with a time limit.
Usage: python -m app.thumbnail_converter <source.pdf> <target> <width>
"""

import sys

import fitz


def render(source: str, target: str, width: int) -> None:
    with fitz.open(source) as pdf:
        if pdf.needs_pass:
            raise ValueError("El PDF está protegido por contraseña.")
        if pdf.page_count == 0:
            raise ValueError("El PDF no tiene páginas.")
        page = pdf[0]
        scale = width / max(page.rect.width, 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        pixmap.save(target, output="png")


if __name__ == "__main__":
    try:
        render(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    except Exception as error:  # Reported to the parent through stderr and the code.
        sys.stderr.write((str(error) or type(error).__name__) + "\n")
        sys.exit(1)
