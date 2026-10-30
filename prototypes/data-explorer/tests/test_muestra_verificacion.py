"""Las anotaciones de la verificación manual no se pierden al regenerar. Sin ficheros del cliente."""

import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import muestra_verificacion as verification

row = lambda sample, candidate, state="", correct="": {"muestra": sample, "candidato": candidate, "referencia": "N1",
                                                     "verificado": state, "lectura_correcta": correct}


class VerificationTests(unittest.TestCase):
    def test_annotations_survive_regeneration(self):
        old = [row("aleatoria", 3, "ok"), row("aleatoria", 5, "corregido", "N15"), row("racimos", 7)]
        merged, lost = verification.merge([row("aleatoria", 3), row("aleatoria", 5), row("racimos", 7)], old)
        self.assertEqual([(r["verificado"], r["lectura_correcta"]) for r in merged],
                         [("ok", ""), ("corregido", "N15"), ("", "")])
        self.assertEqual(lost, [])

    def test_rows_already_annotated_that_would_be_lost_are_reported(self):
        _, lost = verification.merge([row("aleatoria", 3)], [row("aleatoria", 9, "dudoso"), row("aleatoria", 4)])
        self.assertEqual([r["candidato"] for r in lost], [9])  # la 4 no estaba anotada: no se pierde nada

    def test_a_refused_regeneration_changes_none_of_the_three_files(self):
        import json
        import tempfile
        import numpy as np
        reference = {"globos": [{"candidato": i, "lectura_visual": f"N{i}", "box": [.05 * i, .1, .05 * i + .03, .14]}
                                for i in range(1, 15)]}
        rgb = np.full((400, 600, 3), 255, np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "chuleta.json"
            with unittest.mock.patch("builtins.print"):
                first = verification.regenerate(reference, rgb, path, seed=1, n=3, n_clusters=0)
            rows = json.loads((folder / "verificar.json").read_text(encoding="utf-8"))
            rows["filas"][0]["verificado"] = "ok"  # Eduard anota una fila
            (folder / "verificar.json").write_text(json.dumps(rows), encoding="utf-8")
            files = ("verificar.json", "verificar-aleatoria.png", "verificar-racimos.png")
            before = {name: (folder / name).read_bytes() for name in files}
            other = next(seed for seed in range(2, 100) if first[0]["candidato"] not in
                         [e["candidato"] for e in __import__("random").Random(seed).sample(reference["globos"], 3)])
            with self.assertRaises(SystemExit), unittest.mock.patch("builtins.print"):
                verification.regenerate(reference, rgb, path, seed=other, n=3, n_clusters=0)
            self.assertEqual({name: (folder / name).read_bytes() for name in files}, before)

    def test_format_problems(self):
        rows = [row("aleatoria", 1, "ok"), row("aleatoria", 2, "corregido"), row("aleatoria", 3, "bien")]
        self.assertEqual(len(verification.problems(rows)), 2)  # corregido sin lectura y un estado inválido


if __name__ == "__main__":
    unittest.main()
