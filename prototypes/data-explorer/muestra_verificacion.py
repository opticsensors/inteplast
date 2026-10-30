"""Hojas para verificar a ojo una lectura visual de referencia (por defecto, la del 3167).

    py -3.11 prototypes/data-explorer/muestra_verificacion.py

Dos muestras separadas, con semilla fija para poder repetirlas:

- **aleatoria**: 40 entradas al azar entre todas las juzgadas (globos con número y candidatos que no
  son globo). Es la que estima cuánto se puede fiar de la referencia.
- **racimos**: 20 al azar entre los globos con número cuyo círculo se solapa con otro candidato. Es
  la parte difícil; sirve para encontrar fallos, no para estimar la fiabilidad global.

Los errores del lector frente a la referencia están aparte, en errores-<plano>.png de
probar_lector_planos.py: tampoco son una muestra representativa.

Cada recorte lleva el número de candidato y la lectura de la referencia («no globo» si se juzgó que
no lo es). Junto a las hojas se guarda verificar.json. En cada fila, «verificado» es:
- vacío: pendiente;
- «ok»: la referencia es correcta;
- «corregido»: la referencia está mal; la lectura buena va en «lectura_correcta» (p. ej. «N1560.4» o
  «no globo»);
- «dudoso»: no se puede decidir a esta resolución.

Volver a ejecutar el script conserva las anotaciones. Si la muestra nueva dejara fuera filas ya
anotadas (otra semilla u otra referencia), no escribe nada salvo con --forzar. Con --estado solo
muestra el recuento y los errores de formato. Es para validar la referencia del prototipo; no es un
trabajo de los usuarios de la aplicación.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buscar_en_plano as finder

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "out" / "referencia-3167" / "chuleta-3167-2026-10-29.json"
PDF = finder.DEFAULT_PDF.parents[3] / "6- Pockets" / "3167" / "6- Método de medición" / "Drawing baloneed.pdf"


def circles(entries, size):
    height, width = size
    return [((e["box"][0] + e["box"][2]) / 2 * width, (e["box"][1] + e["box"][3]) / 2 * height,
             (e["box"][2] - e["box"][0]) / 2 * width) for e in entries]


def sheet(rgb, entries, size, path: Path):
    if not entries:
        blank = np.full((40, 240, 3), 255, np.uint8)
        cv2.putText(blank, "sin entradas", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 0), 1)
        cv2.imwrite(str(path), blank)
        return
    tiles = []
    for entry, (x, y, r) in zip(entries, circles(entries, size)):
        k = int(max(r * 1.6, 26))
        padded = cv2.copyMakeBorder(rgb, k, k, k, k, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        crop = cv2.resize(padded[int(y):int(y) + 2 * k, int(x):int(x) + 2 * k][:, :, ::-1], (190, 190),
                          interpolation=cv2.INTER_CUBIC)
        cv2.circle(crop, (95, 95), int(r * 190 / (2 * k)), (0, 0, 255), 1)
        tile = cv2.copyMakeBorder(crop, 0, 24, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        label = (entry["lectura_visual"] or "no globo").removeprefix("N")
        cv2.putText(tile, f"#{entry['candidato']}  {label}", (4, 207), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 1)
        tiles.append(tile)
    while len(tiles) % 8:
        tiles.append(np.full_like(tiles[0], 255))
    cv2.imwrite(str(path), np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))


STATES = ("", "ok", "corregido", "dudoso")


def problems(rows: list[dict]) -> list[str]:
    """Errores de formato en las anotaciones."""
    found = []
    for row in rows:
        state = row.get("verificado", "")
        if state not in STATES:
            found.append(f"#{row['candidato']} ({row['muestra']}): «{state}» no es {', '.join(s for s in STATES if s)} ni vacío")
        elif state == "corregido" and not row.get("lectura_correcta", "").strip():
            found.append(f"#{row['candidato']} ({row['muestra']}): «corregido» sin lectura_correcta")
    return found


def merge(new_rows: list[dict], old_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Copia las anotaciones existentes en las filas nuevas; devuelve (filas, anotadas que se perderían)."""
    key = lambda row: (row["muestra"], row["candidato"])
    annotated = {key(r): r for r in old_rows if r.get("verificado") or r.get("lectura_correcta")}
    merged = [dict(row, verificado=annotated[key(row)].get("verificado", ""),
                   lectura_correcta=annotated[key(row)].get("lectura_correcta", ""))
              if key(row) in annotated else row for row in new_rows]
    lost = [r for k, r in annotated.items() if k not in {key(row) for row in new_rows}]
    return merged, lost


def status(rows: list[dict]) -> str:
    lines = []
    for sample in ("aleatoria", "racimos"):
        states = [r.get("verificado", "") for r in rows if r["muestra"] == sample]
        counts = {s or "pendiente": states.count(s) for s in STATES}
        decided = counts["ok"] + counts["corregido"]
        estimate = f" · referencia correcta en {counts['ok']}/{decided}" if decided else ""
        lines.append(f"{sample}: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + estimate)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--referencia", type=Path, default=REFERENCE)
    parser.add_argument("--pdf", type=Path, default=PDF)
    parser.add_argument("--semilla", type=int, default=20261029)
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--n-racimos", type=int, default=20)
    parser.add_argument("--estado", action="store_true", help="Solo mostrar el recuento de anotaciones y salir")
    parser.add_argument("--forzar", action="store_true", help="Escribir aunque se pierdan filas ya anotadas")
    args = parser.parse_args()
    target = args.referencia.parent / "verificar.json"
    old = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {"filas": []}
    if args.estado:
        print(status(old["filas"]))
        print("\n".join(problems(old["filas"])) or "Sin errores de formato.")
        return
    reference = json.loads(args.referencia.read_text(encoding="utf-8"))
    with fitz.open(args.pdf) as doc:
        rgb = finder.page_raster(doc[0])
    merged = regenerate(reference, rgb, args.referencia, args.semilla, args.n, args.n_racimos, args.forzar)
    print(status(merged))


def regenerate(reference: dict, rgb: np.ndarray, reference_path: Path, seed: int, n: int, n_clusters: int,
               force: bool = False) -> list[dict]:
    """Elige las dos muestras y escribe las hojas y verificar.json, en ese orden y solo si se permite.

    Primero se comprueba que no se perderían filas ya anotadas; si se perderían (y no se fuerza),
    no se escribe ninguno de los tres ficheros, para que las anotaciones nunca queden junto a hojas
    de otra muestra.
    """
    folder = reference_path.parent
    target = folder / "verificar.json"
    old = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {"filas": []}
    size = rgb.shape[:2]
    judged = reference["globos"]
    centres = circles(judged + reference.get("dudosos", []), size)
    legible = [e for e in judged if e["lectura_visual"]]
    overlapping = [e for e, (x, y, r) in zip(legible, circles(legible, size))
                   if any(0 < np.hypot(x - a, y - b) < r + c for a, b, c in centres)]
    rng = random.Random(seed)
    random_sample = sorted(rng.sample(judged, min(n, len(judged))), key=lambda e: e["candidato"])
    clusters = sorted(rng.sample(overlapping, min(n_clusters, len(overlapping))), key=lambda e: e["candidato"])
    rows = lambda sample, kind: [{"muestra": kind, "candidato": e["candidato"], "referencia": e["lectura_visual"],
                                  "verificado": "", "lectura_correcta": ""} for e in sample]
    merged, lost = merge(rows(random_sample, "aleatoria") + rows(clusters, "racimos"), old["filas"])
    if lost and not force:
        raise SystemExit(f"No se escribe nada en {folder}: se perderían {len(lost)} filas ya anotadas "
                         f"({', '.join('#' + str(r['candidato']) for r in lost)}). Usa --forzar si es lo que quieres.")
    sheet(rgb, random_sample, size, folder / "verificar-aleatoria.png")
    sheet(rgb, clusters, size, folder / "verificar-racimos.png")
    target.write_text(json.dumps({
        "referencia": str(reference_path), "semilla": seed,
        "estados": "vacío = pendiente · ok · corregido (con lectura_correcta) · dudoso",
        "criterios": {"aleatoria": f"{n} al azar entre {len(judged)} entradas juzgadas",
                      "racimos": f"{n_clusters} al azar entre {len(overlapping)} globos solapados con otro candidato"},
        "filas": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Aleatoria: {len(random_sample)} de {len(judged)} · racimos: {len(clusters)} de {len(overlapping)} · {folder}")
    return merged


if __name__ == "__main__":
    main()
