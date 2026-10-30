"""Vía vectorial, detector de globos y evaluación, con PDF y dibujos sintéticos. Sin ficheros del cliente."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buscar_en_plano as finder
import probar_lector_planos as plans


def balloon_pdf(path: Path, vector: int = 0, single: int = 0, raster: int = 0, hidden: int = 0):
    """Página A4 apaisada con un «escaneo» gris de fondo y globos azules de radio 6 pt (1,5 % del lado corto).

    `vector`: como infra-CONVERT, cada aro en muchos segmentos cortos (fila y=100). `single`: círculos
    vectoriales de un solo trazado (y=150). `raster`: globos dentro de la imagen escaneada (y=300).
    `hidden`: globos vectoriales sobre una franja azul del escaneo (y=220): en la página completa no
    se distinguen, solo en la capa vectorial.
    """
    with finder.fitz.open() as doc:
        page = doc.new_page(width=600, height=400)
        scan = np.full((400, 600, 3), 200, np.uint8)
        cv2.line(scan, (0, 350), (599, 350), (0, 0, 0), 3)
        for i in range(raster):
            cv2.circle(scan, (40 + 50 * i, 300), 6, (255, 0, 0), 1)  # BGR: azul
        if hidden:
            cv2.rectangle(scan, (0, 200), (599, 240), (255, 0, 0), -1)
        page.insert_image(page.rect, stream=cv2.imencode(".png", scan)[1].tobytes())
        angles = np.linspace(0, 2 * np.pi, 40)
        for y, count in ((100, vector), (220, hidden)):
            for i in range(count):
                cx = 40 + 50 * i
                for a, b in zip(angles[:-1], angles[1:]):
                    page.draw_line((cx + 6 * np.cos(a), y + 6 * np.sin(a)), (cx + 6 * np.cos(b), y + 6 * np.sin(b)),
                                   color=(0, 0, 1), width=1)
        for i in range(single):
            page.draw_circle((40 + 50 * i, 150), 6, color=(0, 0, 1), width=1)
        doc.save(path)


def no_duplicates(balloons) -> bool:
    centres = [b["circle"] for b in balloons]
    return all(np.hypot(a[0] - b[0], a[1] - b[1]) > .5 * max(a[2], b[2])
               for i, a in enumerate(centres) for b in centres[i + 1:])


class VectorLayerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.pdf = Path(self.directory.name) / "plano.pdf"

    def tearDown(self):
        self.directory.cleanup()

    def source(self, **kwargs):
        balloon_pdf(self.pdf, **kwargs)
        with finder.fitz.open(self.pdf) as doc:
            work, balloons, kind = finder.balloon_source(self.pdf, doc[0])
            full = finder.detect_balloons(finder.page_raster(doc[0]))
        return work, balloons, kind, full

    def test_vector_balloons_are_kept_and_the_scan_removed(self):
        balloon_pdf(self.pdf, vector=9)
        layer = plans.vector_layer(self.pdf, 0, max_side=1800)
        self.assertIsNotNone(layer)
        self.assertGreater(np.median(layer), 250)  # sin el fondo gris del escaneo
        self.assertEqual(len(finder.detect_balloons(layer)), 9)

    def test_scan_without_vector_balloons_uses_the_image(self):
        balloon_pdf(self.pdf, raster=5)
        self.assertIsNone(plans.vector_layer(self.pdf, 0))

    def test_eight_vector_and_two_raster_balloons_give_ten(self):
        work, balloons, kind, _ = self.source(vector=8, raster=2)
        self.assertEqual(len(balloons), 10)
        self.assertTrue(no_duplicates(balloons))
        self.assertEqual(sorted(b["fuente"] for b in balloons), ["capa vectorial"] * 8 + ["imagen"] * 2)
        self.assertTrue(kind.startswith("mixta"))
        x, y, _ = next(b["circle"] for b in balloons if b["fuente"] == "capa vectorial")
        self.assertEqual(work[round(y), round(x)].tolist(), [255, 255, 255])  # interior tomado de la capa

    def test_balloon_only_in_the_vector_layer_is_kept(self):
        _, balloons, kind, full = self.source(vector=3, hidden=1)
        self.assertEqual(len(full), 3)  # en la página completa la franja azul lo oculta
        self.assertEqual(len(balloons), 4)
        self.assertTrue(no_duplicates(balloons))
        self.assertEqual(kind, "capa vectorial")

    def test_a_rejected_small_pair_does_not_stop_a_valid_large_one(self):
        # Par pequeño a 3 px con radio 4 (límite 2: no vale) y par grande a 10 px con radio 40 (límite 20:
        # vale). El pequeño va primero por distancia; antes cortaba la búsqueda y duplicaba el grande.
        circle = lambda x, r: {"circle": [x, 0, r]}
        layer = [circle(0, 4), circle(100, 40)]
        image = [circle(3, 4), circle(110, 40)]
        self.assertEqual(finder.pair_balloons(layer, image), [(1, 1)])

    def test_a_few_single_path_circles_are_not_lost(self):
        _, balloons, kind, _ = self.source(single=6)
        self.assertEqual((len(balloons), kind), (6, "capa vectorial"))


class DetectorTests(unittest.TestCase):
    def test_small_and_large_balloons_on_the_same_page(self):
        image = np.full((1000, 1400, 3), 255, np.uint8)
        for x, radius in ((150, 8), (400, 14), (800, 30), (1200, 45)):  # 0,8 % a 4,5 % del lado corto
            cv2.circle(image, (x, 500), radius, (0, 140, 0) if radius < 20 else (255, 0, 0), 2)
        found = sorted(round(b["circle"][2]) for b in finder.detect_balloons(image[:, :, ::-1]))
        self.assertEqual(len(found), 3, found)  # el de 45 px supera el 3 % del lado corto (30 px)

    def test_second_pass_keeps_sizes_around_the_typical_one(self):
        # Seis globos de 14 a 20 px (segunda pasada activa) y uno de 45: fuera de 0,6–1,6 veces la mediana.
        image = np.full((1000, 1600, 3), 255, np.uint8)
        for i, radius in enumerate((14, 15, 16, 17, 18, 20, 45)):
            cv2.circle(image, (110 + 210 * i, 500), radius, (255, 0, 0), 2)
        found = sorted(round(b["circle"][2]) for b in finder.detect_balloons(image[:, :, ::-1]))
        self.assertEqual(len(found), 6, found)
        self.assertLess(max(found), 30)

    def test_two_sizes_of_balloons_keep_only_one(self):
        # Limitación conocida: el detector supone un tamaño dominante por página. Con dos familias muy
        # distintas y en número parecido se queda con una; el test lo documenta para que no pase inadvertido.
        image = np.full((1000, 1600, 3), 255, np.uint8)
        for i in range(6):
            cv2.circle(image, (110 + 250 * i, 250), 10, (255, 0, 0), 2)
            cv2.circle(image, (110 + 250 * i, 700), 40, (255, 0, 0), 2)
        radii = {round(b["circle"][2]) // 10 for b in finder.detect_balloons(image[:, :, ::-1])}
        self.assertEqual(len(radii), 1, radii)

    def test_holes_inside_the_numbers_do_not_set_the_balloon_size(self):
        # Como el 3167: más «huecos» de cifras (anillos pequeños) que globos; dentro de cada globo hay tres.
        image = np.full((700, 1300, 3), 255, np.uint8)
        for cx in range(110, 1200, 140):
            cv2.circle(image, (cx, 350), 24, (255, 0, 0), 2)
            for dx, dy in ((-13, 0), (13, 0), (0, -13)):
                cv2.circle(image, (cx + dx, 350 + dy), 5, (255, 0, 0), 2)
        radii = [b["circle"][2] for b in finder.detect_balloons(image[:, :, ::-1])]
        self.assertEqual(len(radii), 8, radii)
        self.assertTrue(all(20 < r < 28 for r in radii), radii)


class ReaderSetupTests(unittest.TestCase):
    def test_without_torch_the_finder_falls_back_to_rapidocr(self):
        import entrenar_lector_globos as training
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "modelo.pt"
            model.write_bytes(b"no es un modelo")
            with mock.patch.object(training, "model_path", lambda profile: model), \
                    mock.patch.dict(sys.modules, {"torch": None}):
                self.assertEqual(finder.own_recognizer(), (None, None))


class EvaluationTests(unittest.TestCase):
    def test_pending_and_false_detections_are_counted_apart(self):
        predictions = [[("N12", .9)], [("N13", .9)], [("N7", .9)], [("N8", .9)], []]
        truth = ["N12", "N14", plans.NOT_A_BALLOON, None, "N20"]
        counts = plans.score(predictions, truth)
        self.assertEqual({k: counts[k] for k in ("acierto", "error", "sin_lectura", "falsas_con_lectura",
                                                 "pendientes", "pendientes_con_lectura")},
                         {"acierto": 1, "error": 1, "sin_lectura": 1, "falsas_con_lectura": 1,
                          "pendientes": 1, "pendientes_con_lectura": 1})
        # (bien, mal, pendientes ofrecidas): la pendiente no cuenta como error, pero se muestra aparte.
        self.assertEqual(plans.offered(counts["detalle"], .5), (1, 2, 1))

    def test_threshold_per_balloon_source(self):
        predictions = [[("N1", .5)], [("N2", .5)], [("N3", .9)]]
        counts = plans.score(predictions, ["N1", "N2", "N3"], ["capa vectorial", "imagen", "imagen"])
        policy = {"capa vectorial": .4, "imagen": .6}  # en una página mixta, cada globo con el de su fuente
        self.assertEqual(plans.offered(counts["detalle"], policy), (2, 0, 0))
        self.assertEqual(plans.offered(counts["detalle"], .4), (3, 0, 0))

    def test_declared_pages_and_pages_without_detections_in_the_summary(self):
        detail = lambda *items: {"combinado": {"acierto": len(items), "error": 0, "sin_lectura": 0,
                                               "detalle": [[.9, "acierto", "imagen"] for _ in items]}}
        development = {"1-p1": {"referencias": 10, "via": "imagen", "lectores": detail(*range(8))},
                       "2-p1": {"referencias": 5, "via": "imagen", "lectores": {}},  # sin detecciones: cuenta
                       "1935-p1": {"referencias": 91, "via": "imagen", "lectores": {}},  # declarada sin globos
                       "2184-p1": {"referencias": 0, "via": "imagen", "lectores": {"combinado": {  # sin globos,
                           "acierto": 0, "error": 0, "sin_lectura": 0, "detalle": [[.9, "falsa", "imagen"]]}}}}  # con un falso
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.json"
            path.write_text(json.dumps(development), encoding="utf-8")
            with mock.patch.dict(plans.finder.COMBINED_THRESHOLDS, {"capa vectorial": .5, "imagen": .5}), \
                    mock.patch("builtins.print"):
                result = plans.threshold_summary(path, Path(directory) / "falta.json", image_threshold=.5,
                                                 output=Path(directory) / "resumen.json")
            self.assertTrue((Path(directory) / "resumen.json").is_file())
        row = result["lectores"]["combinado · un umbral"]["desarrollo"]
        # 8 de 15: la página vacía penaliza; la declarada sin globos no suma referencias, pero su falso sí cuenta.
        self.assertEqual((row["referencias"], row["bien"], row["mal"]), (15, 8, 1))

    def test_visual_reference_is_matched_one_to_one(self):
        reference = {"globos": [{"box": [.09, .09, .11, .11], "lectura_visual": "N5"},
                                {"box": [.49, .49, .51, .51], "lectura_visual": None}]}
        balloons = [{"circle": [100, 100, 10]}, {"circle": [101, 100, 10]}, {"circle": [500, 500, 10]},
                    {"circle": [800, 800, 10]}]
        truth, matched = plans.visual_truth(reference, (1000, 1000), balloons)
        self.assertEqual(truth, ["N5", None, plans.NOT_A_BALLOON, None])
        self.assertEqual(matched, 1)

    def test_calibration_is_stored_normalised_and_reused(self):
        stamps = [{"label": f"N{i}", "points": ((10. * i, 5. * (i % 4)), (0., 0.))} for i in range(1, 13)]
        matrix = np.array([[2., 0., 100.], [0., -2., 300.]])
        balloons = [{"circle": [*(matrix[:, :2] @ (s["points"][0][0], -s["points"][0][1]) + matrix[:, 2]
                                  ) * 0 + matrix[:, :2] @ (s["points"][0][0], s["points"][0][1]) + matrix[:, 2], 6.]}
                    for s in stamps]
        readings = [[s["label"] for s in stamps]]
        store = {}
        first = plans.calibrate("x", balloons, readings, {"a.icp": stamps}, (400, 600), store, refresh=False)
        self.assertIsNotNone(first)
        json.dumps(store)  # se puede guardar
        # Misma página a doble resolución: se reutiliza la calibración, escalada, sin volver a ajustar.
        with mock.patch.object(plans, "fit_stamps", side_effect=AssertionError("no debería reajustar")):
            again = plans.calibrate("x", [], [], {"a.icp": stamps}, (800, 1200), store, refresh=False)
        np.testing.assert_allclose(again[1][2], first[1][2] * 2, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
