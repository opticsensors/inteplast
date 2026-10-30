"""Decodificación con léxico, combinación de recortes y asignación única. Sin ficheros del cliente."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comparar_ocr_globos as bench


class LexiconTests(unittest.TestCase):
    def test_identifiers(self):
        words = set(bench.lexicon())
        self.assertTrue({"1", "155", "155.T", "999.9"} <= words)
        self.assertFalse({"0", "1000", "155.0"} & words)

    @unittest.skipUnless(__import__("importlib").util.find_spec("torch"), "torch no disponible")
    def test_ctc_forward_matches_torch(self):
        import torch
        rng = np.random.default_rng(0)
        logits = rng.normal(size=(12, 6))
        log_probs = logits - np.logaddexp.reduce(logits, axis=1, keepdims=True)
        targets = np.array([[1, 2, 2], [3, 1, 4], [5, 5, 5]])
        ours = bench.ctc_log_likelihood(log_probs, targets)
        expected = -torch.nn.functional.ctc_loss(
            torch.tensor(log_probs)[:, None].repeat(1, 3, 1), torch.tensor(targets), torch.full((3,), 12),
            torch.full((3,), 3), reduction="none")
        np.testing.assert_allclose(ours, expected.numpy(), rtol=1e-6)


class CropTests(unittest.TestCase):
    def test_ink_box_ignores_ring_and_crossing_lines(self):
        import cv2
        image = np.full((80, 80, 3), 255, np.uint8)
        cv2.circle(image, (40, 40), 30, (0, 128, 0), 2)
        cv2.line(image, (0, 22), (79, 22), (0, 0, 0), 1)
        cv2.putText(image, "12", (29, 47), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 128, 0), 1)
        x0, y0, x1, y1 = bench.ink_box(image, (40, 40, 30))
        self.assertTrue(26 <= x0 < x1 <= 54 and 30 <= y0 < y1 <= 50, (x0, y0, x1, y1))

    def test_filled_balloon_is_read_as_dark_ink(self):
        import cv2
        image = np.full((80, 80, 3), 255, np.uint8)
        cv2.circle(image, (40, 40), 30, (0, 0, 200), -1)
        cv2.putText(image, "7", (34, 47), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
        crop = bench.text_crop(image, (40, 40, 30), "luma")
        self.assertGreater(np.median(crop), 128)

    def test_page_rotation_moves_circles_with_the_image(self):
        import probar_lector_planos as plans
        image = np.zeros((50, 100, 3), np.uint8)
        image[5, 10] = 255
        for turns in range(4):
            rotated, (moved,) = plans.rotate(image, [{"circle": [10, 5, 3]}], turns)
            x, y, _ = moved["circle"]
            self.assertEqual(rotated[y, x].tolist(), [255, 255, 255])


class CombinationTests(unittest.TestCase):
    def test_merge_averages_shifted_crops(self):
        merged = bench.merge([[[("155", .8)]], [[("156", .6)]]])
        self.assertEqual(merged, [[("N155", .4), ("N156", .3)]])

    def test_each_identifier_once(self):
        predictions = [[("N155", .9), ("N156", .1)], [("N155", .6), ("N165", .4)], [("N155", 1e-5)]]
        assigned = bench.unique_assignment(predictions)
        self.assertEqual([p[0][0] if p else None for p in assigned], ["N155", "N165", None])


if __name__ == "__main__":
    unittest.main()
