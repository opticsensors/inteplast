"""Search boundaries, page geometry and PDF cache isolation. No customer files."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buscar_en_plano as finder


class IdentifierTests(unittest.TestCase):
    def test_suffixes_and_whole_number_boundaries(self):
        self.assertTrue(finder.number_matches("170.2", "N170"))
        self.assertTrue(finder.number_matches("N170", "170"))
        self.assertTrue(finder.number_matches("161.T", "N161"))
        for label in ("N1700", "N1170", "N1702", "N17", "N171"):
            self.assertFalse(finder.number_matches(label, "170"))
        self.assertFalse(finder.number_matches("N170.2", "N170", False))
        self.assertFalse(finder.number_matches("N170.2", "N170.3"))

    def test_ocr_punctuation_does_not_guess_missing_digits(self):
        self.assertEqual(finder.ocr_number("[170]"), "N170")
        self.assertEqual(finder.ocr_number("(161.T)"), "N161.T")
        self.assertIsNone(finder.ocr_number("I70"))
        self.assertIsNone(finder.ocr_number("170 173"))
        self.assertIsNone(finder.normalize_number("170 mm"))


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
            self.assertEqual([w["text"] for w in data["words"]], ["N170", "N170.2", "N1700", "N240"])
            self.assertTrue(all(w["method"] == "pdf" for w in data["words"]))
            word = data["words"][-1]
            with finder.fitz.open(pdf) as doc:
                page = doc[1]
                rect = finder.fitz.Rect(page.get_text("words")[0][:4]) * page.rotation_matrix
                expected = finder.normalized_box(rect, page.rect.width, page.rect.height)
            self.assertEqual(word["box"], expected)
            self.assertGreater(word["box"][0], .6)
            self.assertLess(word["box"][1], .3)
            self.assertTrue(all((output / p["image"]).is_file() for p in data["pages"]))

    def test_cache_is_invalidated_by_pdf_content(self):
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
            self.assertNotEqual(first["signature"]["sha256"], changed["signature"]["sha256"])
            self.assertEqual(changed["words"][0]["text"], "N165")


if __name__ == "__main__":
    unittest.main()
