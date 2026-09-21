"""Synthetic regressions; never discover, read or hydrate customer files."""

import importlib.util
import io
import math
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


csv = load("metrologia/ver_csv.py", "ver_csv")
pdf = load("metrologia/ver_pdf.py", "ver_pdf")


class SyntheticCSV:
    name = "synthetic.csv"

    def __init__(self, measured=-30.990, element="32", characteristic="Posición Z"):
        self.measured = measured
        self.element = element
        self.characteristic = characteristic

    def open(self, **kwargs):
        return io.StringIO(
            "*** POSICIONS X-Z B1/B2/B3 & B4 ***\n"
            f"{self.element};{self.characteristic};;31.000;0.100;-0.100;"
            f"{self.measured};{self.measured - 31};-61.890;<<---+-----\n"
        )


class CSVCorrectionTests(unittest.TestCase):
    def test_correction_updates_status_and_preserves_export(self):
        raw = csv.leer_csv_cavidad(SyntheticCSV())
        corrected = csv.corregir_signo(raw)
        row = corrected.iloc[0]
        self.assertAlmostEqual(row["medido"], 30.990)
        self.assertAlmostEqual(row["desviacion"], -0.010)
        self.assertFalse(row["nok"])
        self.assertTrue(math.isnan(row["fuera_tol"]))
        self.assertEqual(row["medido_original"], -30.990)
        self.assertEqual(row["fuera_tol_original"], -61.890)
        self.assertTrue(row["nok_original"])
        self.assertEqual(row["barra_original"], "<<---+-----")
        self.assertIn("dentro de tolerancia", csv.hover_medicion(corrected)[0])
        self.assertNotIn("FUERA DE TOLERANCIA", csv.hover_medicion(corrected)[0])
        self.assertEqual(csv.fig_fichero(corrected).data[0].marker.color[0], csv.VERDE)
        self.assertIn("medido original", csv.tabla_html(corrected))
        self.assertTrue(raw.iloc[0]["nok"])
        csv.pd.testing.assert_frame_equal(corrected, csv.corregir_signo(corrected))

    def test_real_excess_stays_nok_and_tolerance_boundary_is_ok(self):
        for measured, expected_nok, expected_excess in (
            (-30.8, True, -0.1), (-31.2, True, 0.1),
            (-30.9, False, None), (-31.1, False, None),
        ):
            with self.subTest(measured=measured):
                row = csv.corregir_signo(csv.leer_csv_cavidad(SyntheticCSV(measured))).iloc[0]
                self.assertEqual(row["nok"], expected_nok)
                if expected_excess is not None:
                    self.assertAlmostEqual(row["fuera_tol"], expected_excess)
                else:
                    self.assertTrue(math.isnan(row["fuera_tol"]))

    def test_only_known_b2_b4_z_export_rows_are_corrected(self):
        for element, characteristic in (("31", "Posición Z"), ("32", "Posición X")):
            with self.subTest(element=element, characteristic=characteristic):
                raw = csv.leer_csv_cavidad(SyntheticCSV(element=element, characteristic=characteristic))
                corrected = csv.corregir_signo(raw)
                self.assertFalse(corrected.iloc[0]["signo_corregido"])
                self.assertEqual(corrected.iloc[0]["medido"], -30.990)


class PDFExtractionTests(unittest.TestCase):
    def extract(self, lines):
        page = Mock()
        page.get_text.return_value = ""
        document = Mock()
        document.__getitem__ = Mock(return_value=page)
        with patch.object(pdf.fitz, "open", return_value=document), patch.object(
            pdf, "filas_por_y", return_value=lines
        ):
            return pdf.leer_pdf(Path("synthetic.pdf"), Path("unused"), 1, "synthetic")

    def test_complete_measurements_distinguish_pass_from_failure(self):
        for deviation, excess, expected in (("-0.242", "-0.217", True), ("-0.020", "0.000", False)):
            with self.subTest(expected=expected):
                data = self.extract([
                    f"Contorno (21) -0.025 {deviation} {excess}",
                    "CONTORN (10) 0.025 0.020 0.000",
                ])
                self.assertEqual(pdf.hay_infraccion(data), expected)
                self.assertAlmostEqual(pdf.peor_infraccion(data), abs(float(excess)))

    def test_missing_or_unparseable_table_never_becomes_a_pass(self):
        for lines in ([], ["Contorno (21) -0.025 -0.242 -0.217"], ["Contorno (21) ilegible"]):
            with self.subTest(lines=lines):
                data = self.extract(lines)
                self.assertIsNone(pdf.hay_infraccion(data))
                self.assertIsNone(pdf.peor_infraccion(data))
                self.assertIn("Estado desconocido", pdf.estado_html(data))
                self.assertNotIn("Dentro de tolerancia", pdf.estado_html(data))
                self.assertNotIn("class='dentro'", pdf.barra_tolerancia(data))
                figure = pdf.fig_evolucion({"PA_1": {"01": data}})
                self.assertIsNone(figure.data[0].y[0])

    def test_nonfinite_fields_are_unknown(self):
        data = dict(tol_inf=-0.025, tol_sup=0.025, desv_inf=0, desv_sup=0, infr_inf=0, infr_sup=0)
        for bad in (None, float("nan"), float("inf"), "0"):
            with self.subTest(bad=bad):
                data["infr_inf"] = bad
                self.assertIsNone(pdf.hay_infraccion(data))

    def test_incomplete_pdf_stays_unknown_in_page_and_folder_summary(self):
        source = dict(ruta=Path("synthetic.pdf"), muestreo="01", cavidad="c13",
                      perfil="A", indice=1, rel="synthetic.pdf")
        with patch.object(pdf.sys, "argv", ["ver_pdf.py", "--no-abrir"]), \
             patch.object(pdf, "descubrir", return_value=[source]), \
             patch.object(pdf, "leer_pdf", return_value={"png": "synthetic.png"}), \
             patch.object(pdf, "get_plotlyjs", return_value=""), \
             patch.object(Path, "mkdir"), patch.object(Path, "glob", return_value=[]), \
             patch.object(Path, "write_text") as write, patch("sys.stdout", new=io.StringIO()):
            pdf.main()
        html = "\n".join(call.args[0] for call in write.call_args_list)
        self.assertIn("Estado desconocido", html)
        self.assertIn("1 sin evaluar", html)
        self.assertNotIn("todas dentro", html)
        self.assertNotIn("Dentro de tolerancia", html)


if __name__ == "__main__":
    unittest.main()
