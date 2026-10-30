"""Search boundaries, page geometry and PDF cache isolation. No customer files."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


@unittest.skipUnless(shutil.which("node"), "Node.js no disponible")
class SearchCoreTests(unittest.TestCase):
    """The page's number search, run in Node with synthetic balloons."""

    def find(self, query):
        core = finder.PAGE[finder.PAGE.index("const normalize="):finder.PAGE.index("const kinds=")]
        balloon = lambda id_, x, labels: {"id": id_, "page": 1, "box": [x, .1, x + .02, .12], "circle": [0, 0, 1],
                                          "kind": "ocr" if labels else "unread", "labels": labels,
                                          "label": labels[0] if labels else "Globo"}
        records = [balloon("b176", .10, ["N176"]), balloon("near", .13, []), balloon("far", .80, []),
                   balloon("b133", .40, ["N133", "N132"]), balloon("alt", .50, ["N135", "N133"]),
                   balloon("partial", .16, ["N17"])]
        script = (core + f"\nconsole.log(JSON.stringify(findNumber({json.dumps(query)}, {json.dumps(records)})"
                  ".map(r => [r.id, r.kind])))")
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
        return [tuple(r) for r in json.loads(out.stdout)]

    def test_principal_reading_before_alternatives(self):
        self.assertEqual(self.find("133"), [("b133", "ocr"), ("alt", "alt")])

    def test_exact_reading_has_no_proposals(self):
        self.assertEqual(self.find("N176"), [("b176", "ocr")])

    def test_unread_or_partial_balloons_are_not_proposed(self):
        self.assertEqual(self.find("177"), [])
        self.assertEqual(self.find("177.1"), [])


class CombinedThresholdTests(unittest.TestCase):
    def test_mixed_page_uses_the_threshold_of_each_balloon_source(self):
        thresholds = {"capa vectorial": .4, "imagen": .6}
        balloons = [{"fuente": "capa vectorial"}, {"fuente": "imagen"}, {"fuente": "imagen"}]
        choices = [[("N12", .5)], [("N13", .5)], [("N14", .7)]]
        finder.offer_readings(balloons, choices, [[], [], []], [[], [], []], thresholds)
        offered = [b["candidates"][0]["label"] if b["candidates"] else None for b in balloons]
        self.assertEqual(offered, ["N12", None, "N14"])  # el 0,5 vale en la capa, no en la imagen

    def test_cache_signature_includes_both_thresholds(self):
        signature = finder.index_signature("abc", True, "modelo")
        self.assertEqual(signature["lector"]["umbrales"], finder.COMBINED_THRESHOLDS)
        with mock.patch.dict(finder.COMBINED_THRESHOLDS, {"imagen": .7}):
            self.assertNotEqual(finder.index_signature("abc", True, "modelo"), signature)


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
