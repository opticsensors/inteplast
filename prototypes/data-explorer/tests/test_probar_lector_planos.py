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
import lectores_planos as lectores
import probar_lector_planos as plans


def balloon_pdf(path: Path, vector: int = 0, single: int = 0, raster: int = 0, hidden: int = 0):
    """Página A4 apaisada con un «escaneo» gris de fondo y globos azules de radio 6 pt (1,5 % del lado corto).

    `vector`: como infra-CONVERT, cada aro en muchos segmentos cortos (fila y=100). `single`: círculos
    vectoriales de un solo trazado (y=150). `raster`: globos dentro de la imagen escaneada (y=300).
    `hidden`: globos vectoriales sobre una franja azul del escaneo (y=220): en la página completa no
    se distinguen, solo en la capa vectorial.
    """
    with lectores.fitz.open() as doc:
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
        with lectores.fitz.open(self.pdf) as doc:
            work, balloons, kind = lectores.balloon_source(self.pdf, doc[0])
            full = lectores.detect_balloons(lectores.page_raster(doc[0]))
        return work, balloons, kind, full

    def test_vector_balloons_are_kept_and_the_scan_removed(self):
        balloon_pdf(self.pdf, vector=9)
        layer = lectores.vector_layer(self.pdf, 0, max_side=1800)
        self.assertIsNotNone(layer)
        self.assertGreater(np.median(layer), 250)  # sin el fondo gris del escaneo
        self.assertEqual(len(lectores.detect_balloons(layer)), 9)

    def test_scan_without_vector_balloons_uses_the_image(self):
        balloon_pdf(self.pdf, raster=5)
        self.assertIsNone(lectores.vector_layer(self.pdf, 0))

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
        self.assertEqual(lectores.pair_balloons(layer, image), [(1, 1)])

    def test_a_few_single_path_circles_are_not_lost(self):
        _, balloons, kind, _ = self.source(single=6)
        self.assertEqual((len(balloons), kind), (6, "capa vectorial"))


class DetectorTests(unittest.TestCase):
    def test_small_and_large_balloons_on_the_same_page(self):
        image = np.full((1000, 1400, 3), 255, np.uint8)
        for x, radius in ((150, 8), (400, 14), (800, 30), (1200, 45)):  # 0,8 % a 4,5 % del lado corto
            cv2.circle(image, (x, 500), radius, (0, 140, 0) if radius < 20 else (255, 0, 0), 2)
        found = sorted(round(b["circle"][2]) for b in lectores.detect_balloons(image[:, :, ::-1]))
        self.assertEqual(len(found), 3, found)  # el de 45 px supera el 3 % del lado corto (30 px)

    def test_second_pass_keeps_sizes_around_the_typical_one(self):
        # Seis globos de 14 a 20 px (segunda pasada activa) y uno de 45: fuera de 0,6–1,6 veces la mediana.
        image = np.full((1000, 1600, 3), 255, np.uint8)
        for i, radius in enumerate((14, 15, 16, 17, 18, 20, 45)):
            cv2.circle(image, (110 + 210 * i, 500), radius, (255, 0, 0), 2)
        found = sorted(round(b["circle"][2]) for b in lectores.detect_balloons(image[:, :, ::-1]))
        self.assertEqual(len(found), 6, found)
        self.assertLess(max(found), 30)

    def test_two_sizes_of_balloons_keep_only_one(self):
        # Limitación conocida: el detector supone un tamaño dominante por página. Con dos familias muy
        # distintas y en número parecido se queda con una; el test lo documenta para que no pase inadvertido.
        image = np.full((1000, 1600, 3), 255, np.uint8)
        for i in range(6):
            cv2.circle(image, (110 + 250 * i, 250), 10, (255, 0, 0), 2)
            cv2.circle(image, (110 + 250 * i, 700), 40, (255, 0, 0), 2)
        radii = {round(b["circle"][2]) // 10 for b in lectores.detect_balloons(image[:, :, ::-1])}
        self.assertEqual(len(radii), 1, radii)

    def test_holes_inside_the_numbers_do_not_set_the_balloon_size(self):
        # Como el 3167: más «huecos» de cifras (anillos pequeños) que globos; dentro de cada globo hay tres.
        image = np.full((700, 1300, 3), 255, np.uint8)
        for cx in range(110, 1200, 140):
            cv2.circle(image, (cx, 350), 24, (255, 0, 0), 2)
            for dx, dy in ((-13, 0), (13, 0), (0, -13)):
                cv2.circle(image, (cx + dx, 350 + dy), 5, (255, 0, 0), 2)
        radii = [b["circle"][2] for b in lectores.detect_balloons(image[:, :, ::-1])]
        self.assertEqual(len(radii), 8, radii)
        self.assertTrue(all(20 < r < 28 for r in radii), radii)


class ReaderSetupTests(unittest.TestCase):
    def test_without_a_usable_model_the_finder_falls_back_to_rapidocr(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "lector_globos.onnx"
            self.assertIsNone(lectores.own_reader(model))  # no existe
            model.write_bytes(b"no es un modelo")
            model.with_suffix(".json").write_text('{"caracteres": ["0", "1"], "entrada": [32, 64]}', encoding="utf-8")
            self.assertIsNone(lectores.own_reader(model))  # existe, pero onnxruntime no lo carga
            self.assertIsNone(lectores.model_hash(Path(directory) / "falta.onnx"))

    def test_combined_reading_in_the_benchmark_is_the_one_the_viewer_offers(self):
        class Reader:  # lector propio de mentira: siempre lee «12» con 0,9
            def read(self, crops):
                return [[("12", .9)] for _ in crops]
        image = np.full((60, 120, 3), 255, np.uint8)
        balloons = [{"circle": [30, 30, 12], "fuente": "imagen"}, {"circle": [90, 30, 12], "fuente": "imagen"}]
        rapid = [[("N12", .8)], [("N13", .7)]]
        with mock.patch.object(lectores, "rapid_predictions", return_value=rapid):
            out = plans.read_all(image, balloons, {"buscador": None}, Reader())
            offered = [dict(b) for b in balloons]
            lectores.read_balloons_combined(image, offered, None, Reader())
        self.assertEqual(out["combinado"], lectores.combine(rapid, lectores.own_predictions(image, balloons, Reader())))
        # El banco guarda también lo que queda bajo el umbral (se aplica al resumir); el visor solo ofrece lo
        # que llega: N13 (0,7 de RapidOCR y nada del lector propio, media 0,35) no se ofrece.
        threshold = lectores.COMBINED_THRESHOLDS["imagen"]
        self.assertEqual([c[0][0] if c and c[0][1] >= threshold else None for c in out["combinado"]],
                         [b["candidates"][0]["label"] if b["candidates"] else None for b in offered])
        self.assertEqual([b["candidates"][0]["label"] if b["candidates"] else None for b in offered], ["N12", None])


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

    def test_the_threshold_uses_the_full_score_like_the_viewer(self):
        scores = [.60718, .6072, .60725, .5]
        predictions = [[(f"N{i}", s)] for i, s in enumerate(scores, 1)]
        counts = plans.score(predictions, [f"N{i}" for i in range(1, 5)], ["imagen"] * 4)
        self.assertEqual([d[0] for d in counts["detalle"]], scores)  # sin redondear
        policy = {"capa vectorial": .434, "imagen": .6072}
        self.assertEqual(plans.offered(counts["detalle"], policy), (2, 0, 0))  # 0,60718 no se ofrece
        balloons = [{"fuente": "imagen"} for _ in scores]
        lectores.offer_readings(balloons, predictions, [[]] * 4, [[]] * 4, policy)
        self.assertEqual([bool(b["candidates"]) for b in balloons], [d[0] >= .6072 for d in counts["detalle"]])

    def test_threshold_warning_rounds_only_for_the_comparison(self):
        def summary(capa, imagen):
            entries = {"1-p1": {"referencias": 2, "via": "imagen", "lectores": {"combinado": {
                "acierto": 2, "error": 0, "sin_lectura": 0,
                "detalle": [[capa, "acierto", "capa vectorial"], [imagen, "acierto", "imagen"]]}}}}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "a.json"
                path.write_text(json.dumps(entries), encoding="utf-8")
                with mock.patch("builtins.print") as printed:
                    plans.threshold_summary(path, Path(directory) / "falta.json")
            return [c.args[0] for c in printed.call_args_list if c.args and "AVISO" in str(c.args[0])]
        self.assertEqual(summary(.43401, .60721), [])  # con puntuaciones completas: los mismos umbrales a 4 decimales
        self.assertTrue(summary(.43401, .61))  # otro umbral de imagen: avisa

    def test_failures_are_what_the_viewer_offers_against_the_reference(self):
        balloons = [{"circle": [100, 50, 5], "fuente": "imagen"} for _ in range(6)]
        combined = [[("N1", .9)], [("N2", .9)], [("N3", .5)], [], [("N7", .9)], [("N8", .9)]]
        truth = ["N1", "N9", "N3", "N4", plans.NOT_A_BALLOON, None]
        out = plans.failures(balloons, combined, truth, (100, 200), [("N5", 20., 10.)])
        self.assertEqual(out["no_detectados"], [{"numero": "N5", "x": .1, "y": .1}])
        self.assertEqual([(e["numero"], e["leido"]) for e in out["erroneos"]], [("N9", "N2")])
        # N3 quedó bajo el umbral de la imagen (0,6072): sin lectura, con su propuesta; N4, sin nada.
        self.assertEqual([(e["numero"], e["propuesta"]) for e in out["sin_lectura"]], [("N3", "N3"), ("N4", None)])
        self.assertEqual([e["leido"] for e in out["en_falso"]], ["N7"])
        self.assertEqual([e["leido"] for e in out["sin_referencia"]], ["N8"])
        self.assertEqual((out["erroneos"][0]["x"], out["erroneos"][0]["y"]), (.5, .5))

    def test_new_results_are_not_mixed_with_rounded_or_other_reader_ones(self):
        config = {"puntuaciones": "completas", "lector_combinado": "lectores-planos-v1:a:b:umbrales"}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.assertIsNone(plans.mixing_problem(folder, config))  # carpeta nueva
            (folder / "resultados.json").write_text("{}", encoding="utf-8")
            (folder / "configuracion.json").write_text(json.dumps({"lector_combinado": "x"}), encoding="utf-8")
            self.assertIn("redondeadas", plans.mixing_problem(folder, config))  # histórico
            (folder / "configuracion.json").write_text(json.dumps(dict(config, lector_combinado="otro")), encoding="utf-8")
            self.assertIn("otro lector", plans.mixing_problem(folder, config))
            (folder / "configuracion.json").write_text(json.dumps(config), encoding="utf-8")
            self.assertIsNone(plans.mixing_problem(folder, config))  # misma medición: se puede completar

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
            with mock.patch.dict(lectores.COMBINED_THRESHOLDS, {"capa vectorial": .5, "imagen": .5}), \
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
        first = lectores.calibrate("x", balloons, readings, {"a.icp": stamps}, (400, 600), store, refresh=False)
        self.assertIsNotNone(first)
        json.dumps(store)  # se puede guardar
        # Misma página a doble resolución: se reutiliza la calibración, escalada, sin volver a ajustar.
        with mock.patch.object(lectores, "fit_stamps", side_effect=AssertionError("no debería reajustar")):
            again = lectores.calibrate("x", [], [], {"a.icp": stamps}, (800, 1200), store, refresh=False)
        np.testing.assert_allclose(again[1][2], first[1][2] * 2, atol=1e-6)

    def test_calibration_is_redone_when_the_extracted_stamps_change(self):
        # Mismo PDF y mismo .icp, pero otros sellos extraídos (p. ej., tras corregir globos_icp.py).
        stamps = [{"label": f"N{i}", "points": ((10. * i, 5. * (i % 4)), (0., 0.))} for i in range(1, 13)]
        balloons = [{"circle": [2. * s["points"][0][0] + 100, -2. * s["points"][0][1] + 300, 6.]} for s in stamps]
        readings = [[s["label"] for s in stamps]]
        store, digest = {}, {"a.icp": lectores.stamps_digest(stamps)}
        lectores.calibrate("x", balloons, readings, {"a.icp": stamps}, (400, 600), store, False, stamp_digests=digest)
        self.assertEqual(store["x"]["sellos_sha256"], digest["a.icp"])
        with mock.patch.object(lectores, "fit_stamps", side_effect=AssertionError("no debería reajustar")):
            lectores.calibrate("x", [], [], {"a.icp": stamps}, (400, 600), store, False, stamp_digests=digest)
        moved = [dict(stamps[0], points=((99., 99.), (0., 0.)))] + stamps[1:]
        self.assertNotEqual(lectores.stamps_digest(moved), digest["a.icp"])
        with mock.patch.object(lectores, "fit_stamps", wraps=lectores.fit_stamps) as fit:
            lectores.calibrate("x", balloons, readings, {"a.icp": moved}, (400, 600), store, False,
                               stamp_digests={"a.icp": lectores.stamps_digest(moved)})
        self.assertTrue(fit.called)
        old = dict(store["x"])
        old.pop("sellos_sha256")  # calibración anterior a la huella: se reajusta
        store["x"] = old
        with mock.patch.object(lectores, "fit_stamps", wraps=lectores.fit_stamps) as fit:
            lectores.calibrate("x", balloons, readings, {"a.icp": moved}, (400, 600), store, False,
                               stamp_digests={"a.icp": lectores.stamps_digest(moved)})
        self.assertTrue(fit.called)


if __name__ == "__main__":
    unittest.main()
