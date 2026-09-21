"""Evaluation identities and profile geometry, independent of exploration tools."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.ingestion import cmm, profile_pdf
from app.ingestion.pilot_3212 import actions, catalog


class CatalogueTests(unittest.TestCase):
    def test_shared_headers_are_not_split_or_confused_with_coordinates(self):
        self.assertEqual(
            catalog.catalog_group("N116/260 POS & N258"),
            ("N116/N260/N258", ["N116", "N260", "N258"], "dimension"),
        )
        self.assertEqual(catalog.catalog_group("POSICIONS N117")[2], "diagnostic")
        self.assertEqual(catalog.catalog_group("POINT 60 MIN/MAX")[0], "N165")

    def test_all_action_dimensions_exclude_action_number_and_nominals(self):
        title = (
            "Tool correction 1.6 (DIM. Nr.137)/(DIM. Nr.142)/(DIM. Nr.211) → 60±0,20"
        )
        self.assertEqual(actions.action_dimension_ids(title), ["N137", "N142", "N211"])
        self.assertEqual(
            actions.action_dimension_ids("DIM.Nr.N117 / N118 → 123"), ["N117", "N118"]
        )
        self.assertEqual(actions.action_dimension_ids("DIM. Nr.XX → 240"), [])
        self.assertEqual(actions.action_dimension_ids("DIM. Nr.137→11,5±0,2"), ["N137"])

    def test_catalogue_preserves_bolt_identity_units_and_missing_samples(self):
        root = Path(__file__).resolve().parent / "synthetic"
        files = [{"muestreo": "01", "cavidad": "c13", "ruta": root / "test.csv"}]
        rows = []
        for occurrence, element in ((1, "15"), (2, "16")):
            for idx in (1, 2):
                rows.append(
                    {
                        "bloque": "N170 BOLT 1 MIN/MAX H=5.0 mm",
                        "ocurrencia": occurrence,
                        "idx": idx,
                        "id_cmm": element if idx == 1 else "",
                        "caracteristica": "Diametro",
                        "nominal": 4.0,
                        "tol_inf": -0.1,
                        "tol_sup": 0.0,
                        "medido": 4.018,
                        "nok_original": True,
                        "signo_corregido": False,
                        "medido_original": 4.018,
                    }
                )
        rows.append(
            {
                "bloque": "N118 POS",
                "ocurrencia": 1,
                "idx": 1,
                "id_cmm": "9",
                "caracteristica": "Phi ZX",
                "nominal": 79.5,
                "tol_inf": -0.5,
                "tol_sup": 0.5,
                "medido": 79.49,
                "nok_original": False,
                "signo_corregido": False,
                "medido_original": 79.49,
            }
        )
        table = cmm.pd.DataFrame(rows)
        actions = {"1.33": {"id": "1.33", "features": ["N170"]}}
        with (
            patch.object(cmm, "discover", return_value=files),
            patch.object(cmm, "read_csv", return_value=table),
            patch.object(cmm, "correct_sign", side_effect=lambda t: t),
        ):
            catalogue = catalog.load_catalog(root, actions, {"N170": {}})
        entries = {e["id"]: e for e in catalogue["entries"]}
        self.assertEqual(catalogue["row_count"], 5)
        self.assertEqual(len(entries["N170"]["series"]), 4)
        self.assertEqual(
            {s["label"] for s in entries["N170"]["series"]},
            {
                f"B{bolt}-H5.0 · {metric}"
                for bolt in (1, 2)
                for metric in ("GX", "LP máximo")
            },
        )
        for series in entries["N170"]["series"]:
            self.assertEqual(set(series["records"]["c13"]), {"01"})
            self.assertEqual(series["records"]["c13"]["01"]["status"], "outside")
        self.assertEqual(entries["N170"]["actions"], ["1.33"])
        self.assertIsNone(entries["N118"]["reviewed_case"])
        self.assertEqual(entries["N118"]["series"][0]["unit"], "°")


class ProfileCropTests(unittest.TestCase):
    def page(self, frames):
        return SimpleNamespace(
            rect=profile_pdf.fitz.Rect(0, 0, 595, 842), get_drawings=lambda: frames
        )

    def test_crop_retains_margin_and_ignores_small_white_legend(self):
        frames = [
            {"fill": (1, 1, 1), "rect": profile_pdf.fitz.Rect(71, 151, 539, 502)},
            {"fill": (1, 1, 1), "rect": profile_pdf.fitz.Rect(100, 200, 130, 220)},
        ]
        self.assertEqual(
            list(profile_pdf.profile_crop(self.page(frames))), [63, 143, 547, 510]
        )

    def test_missing_or_ambiguous_plot_never_becomes_a_full_page_thumbnail(self):
        frame = {"fill": (1, 1, 1), "rect": profile_pdf.fitz.Rect(71, 151, 539, 502)}
        for frames in ([], [frame, frame]):
            with self.subTest(count=len(frames)), self.assertRaises(ValueError):
                profile_pdf.profile_crop(self.page(frames))
