"""PDF geometry and content identity using generated documents."""

import tempfile
import unittest
from pathlib import Path

from app.ingestion import drawing as finder


class PDFIndexTests(unittest.TestCase):
    def make_pdf(self, path, first="N170"):
        with finder.fitz.open() as doc:
            page = doc.new_page(width=420, height=297)
            page.insert_text((50, 65), first + " N170.2 N1700")
            page = doc.new_page(width=420, height=297)
            page.insert_text((80, 100), "N240")
            page.set_rotation(90)
            doc.save(path)

    def test_text_and_rotated_page_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, output = root / "drawing.pdf", root / "out"
            self.make_pdf(pdf)
            data = finder.build_index(pdf, output, use_ocr=False)
            self.assertEqual(len(data["pages"]), 2)
            self.assertEqual(
                [w["text"] for w in data["words"]], ["N170", "N170.2", "N1700", "N240"]
            )
            self.assertTrue(all(w["method"] == "pdf" for w in data["words"]))
            word = data["words"][-1]
            with finder.fitz.open(pdf) as doc:
                page = doc[1]
                rect = (
                    finder.fitz.Rect(page.get_text("words")[0][:4])
                    * page.rotation_matrix
                )
                expected = finder.normalized_box(
                    rect, page.rect.width, page.rect.height
                )
            self.assertEqual(word["box"], expected)
            self.assertGreater(word["box"][0], 0.6)
            self.assertLess(word["box"][1], 0.3)
            self.assertTrue(all((output / p["image"]).is_file() for p in data["pages"]))

    def test_reindex_reflects_changed_pdf_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, output = root / "drawing.pdf", root / "out"
            self.make_pdf(pdf)
            first = finder.build_index(pdf, output, use_ocr=False)
            same = finder.build_index(pdf, output, use_ocr=False)
            self.assertEqual(first["signature"], same["signature"])
            pdf.unlink()
            self.make_pdf(pdf, first="N165")
            changed = finder.build_index(pdf, output, use_ocr=False)
            self.assertNotEqual(
                first["signature"]["sha256"], changed["signature"]["sha256"]
            )
            self.assertEqual(changed["words"][0]["text"], "N165")
