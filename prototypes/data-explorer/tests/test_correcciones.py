"""Regression cases for the pilot mappings; no customer files are opened."""

import importlib.util
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ver_correcciones", ROOT / "ver_correcciones.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class Sheet:
    nrows, ncols = 225, 19

    def __init__(self):
        self.values = {
            (224, 1): 240, (224, 4): 18.5, (224, 5): .2, (224, 6): 0,
            (224, 7): "CMM", (224, 8): 18.695,
            (224, 15): .02, (224, 16): 18.715,
            (225, 15): -.08, (225, 16): 18.635,
        }

    def cell_value(self, row, col):
        return self.values.get((row + 1, col + 1), "")

    def cell(self, row, col):
        value = self.cell_value(row, col)
        return SimpleNamespace(value=value, ctype=pilot.xlrd.XL_CELL_NUMBER
                               if isinstance(value, (int, float)) else pilot.xlrd.XL_CELL_TEXT)


class CorrectionTests(unittest.TestCase):
    def test_unknown_values_never_pass(self):
        for value in (None, math.nan, math.inf, True, "0"):
            self.assertEqual(pilot.result(value, 0, 1), "unknown")
        self.assertEqual(pilot.result(1, 0, None), "unknown")
        self.assertEqual(pilot.result(1, 2, 0), "unknown")
        self.assertEqual(pilot.result(4, 3.9, 4), "inside")
        self.assertEqual(pilot.result(4.018, 3.9, 4), "outside")

    def test_excel_error_code_is_not_a_measurement(self):
        sheet = Mock(nrows=1, ncols=1)
        sheet.cell.return_value = SimpleNamespace(ctype=pilot.xlrd.XL_CELL_ERROR, value=7)
        self.assertIsNone(pilot.cell_value(sheet, 1, 1))

    def test_repeated_wrong_bolt_header_uses_cmm_identity_for_both_evaluations(self):
        rows = []
        for occurrence, element in ((1, "15"), (2, "16")):
            for idx in (1, 2):
                rows.append(dict(bloque="N170 B1 H=5", ocurrencia=occurrence, idx=idx,
                                 id_cmm=element if idx == 1 else "", nominal=4.,
                                 tol_inf=-.1, tol_sup=0., medido=3.97 if idx == 1 else 4.02, nok=idx == 2))
        root = ROOT / "synthetic"
        files = [dict(muestreo="03", cavidad="c13", ruta=root / "synthetic.csv")]
        with patch.object(pilot.ver_csv, "descubrir", return_value=files), patch.object(
                pilot.ver_csv, "leer_csv_cavidad", return_value=pilot.ver_csv.pd.DataFrame(rows)):
            records, _ = pilot.load_csv(root)
        self.assertEqual(len(records), 4)
        for bolt in ("B1", "B2"):
            self.assertEqual(records[("03", "c13", "N170", bolt + "-H5.0", 1)]["status"], "inside")
            self.assertEqual(records[("03", "c13", "N170", bolt + "-H5.0", 2)]["status"], "outside")

    def test_global_is_separate_from_scan_and_local_points(self):
        keys = [pilot.csv_identity(dict(bloque=b, idx=1), "")
                for b in ("GLOBAL MIN/MAX", "N165 MIN/MAX", "POINT 1 MIN/MAX")]
        self.assertEqual(keys, [("N165", "main", 1), ("N165", "scan", 1), ("N165", "P01", 1)])

    def test_chained_prediction_and_missing_after_preserve_uncertainty(self):
        record = dict(value=18.695, lower=18.5, upper=18.7, status="inside")
        book = Mock()
        book.sheet_by_name.return_value = Sheet()
        comparison = pilot.compare({("03", "c13", "N240", "main", 1): record},
                                   {"2": book}, ROOT, "N240", "main", "c13")
        item = comparison["items"][0]
        self.assertAlmostEqual(item["prediction"], 18.635)
        self.assertEqual([s["delta"] for s in item["steps"]], [.02, -.08])
        self.assertIsNone(item["after"])
        self.assertTrue(any("falta la medición posterior" in w for w in comparison["warnings"]))
        self.assertFalse(any("suma" in w for w in comparison["warnings"]))

    def test_shifted_excel_mapping_is_rejected(self):
        sheet = Sheet()
        sheet.values[(224, 1)] = 241
        with self.assertRaisesRegex(ValueError, "Mapeo XLS obsoleto"):
            pilot.validate_excel_mapping(sheet, 224, "N240")


if __name__ == "__main__":
    unittest.main()
