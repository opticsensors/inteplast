"""Entrena un lector propio de números de globo con imágenes sintéticas, sin datos del cliente.

    py entrenar_lector_globos.py                  # genera, entrena y guarda out/lector-globos/modelo.pt
    py comparar_ocr_globos.py --lectores propio propio-lexico

Dibuja números de globo (1–999, con sufijo .1–.9 o .T) con tipografías de dibujo técnico
instaladas en Windows y a la escala de un plano escaneado: cifras de 4–7 px, aro, líneas que
cruzan, globos vecinos, desenfoque, ruido y JPEG 4:2:0. Después aplica el mismo recorte y la
misma vista que comparar_ocr_globos.py y entrena una CRNN pequeña con CTC en CPU (minutos).

Las lecturas de referencia del 3212 no se usan para entrenar ni para elegir la época: solo
para medir al final. Requiere torch (instalado en el Python del equipo).
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from functools import partial
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_ocr_globos as bench

OUTPUT = Path(__file__).resolve().parent / "out" / "lector-globos"
CHARACTERS = list("0123456789.T")
INPUT = (32, 64)  # alto, ancho de entrada a la red
FONTS = ["arial.ttf", "ARIALN.TTF", "tahoma.ttf", "verdana.ttf", "segoeui.ttf", "calibri.ttf",
         "isocpeur.ttf", "isocteur.ttf", "swisop1.ttf", "swisot1.ttf", "simplex_IV50.ttf",
         "romans_IV50.ttf", "txt_IV50.ttf", "GENISO.ttf", "consola.ttf"]
BOLD_FONTS = ["arialbd.ttf", "ariblk.ttf", "tahomabd.ttf", "verdanab.ttf", "segoeuib.ttf", "calibrib.ttf",
              "ARIALNB.TTF", "GOTHICB.TTF"]
SUPER = 8  # se dibuja a 8× y se reduce, como un escaneo con antialiasing
INKS = [(0, 128, 0), (0, 150, 40), (20, 110, 20), (0, 0, 255), (30, 30, 200), (0, 0, 0)]


def random_label(rng: np.random.Generator, digits: int = 3) -> str:
    if digits == 3:
        number = str(int(rng.integers(1, 1000)))
    else:  # mismo peso para cada longitud de 2 a 4 cifras: los planos grandes pasan de 999
        length = rng.choice(np.arange(1, digits + 1), p=[.1] + [.9 / (digits - 1)] * (digits - 1))
        number = str(int(rng.integers(10 ** (length - 1), 10 ** length)))
    roll = rng.random()
    return number + (f".{rng.integers(1, 10)}" if roll < .22 else ".T" if roll < .30 else "")


def font_digit_ratio(path: str) -> float:
    font = ImageFont.truetype(path, 100)
    box = font.getbbox("0123456789")
    return (box[3] - box[1]) / 100


_FONTS: dict[str, tuple[str, float]] = {}


def fonts(names: list[str] = FONTS) -> list[tuple[str, float]]:
    found = []
    for name in names:
        path = Path(r"C:\Windows\Fonts") / name
        if name not in _FONTS and path.is_file():
            _FONTS[name] = (str(path), font_digit_ratio(str(path)))
        if name in _FONTS:
            found.append(_FONTS[name])
    return found


PROFILES = {
    # Primer modelo (29/10/2026): cifras diminutas de escaneo, número a un tercio del globo, como el 3212.
    "3212": {"heights": [(1., 4.2, 7.)], "ratio": (2.3, 3.1), "filled": 0., "thick": 0., "pointer": 0.,
             "clean": 0., "fit_text": False},
    # Planos variados: escaneos con cifras de 4 px y rásteres nítidos con números grandes, aros
    # gruesos, globos rellenos con el número en blanco y con pico. El recorte se centra en el texto.
    "amplio": {"heights": [(.55, 4.2, 7.), (.45, 7., 28.)], "ratio": (1.25, 3.1), "filled": .2, "thick": .35,
               "pointer": .3, "clean": .3, "fit_text": True},
    # «amplio» más lo que falló en los planos de desarrollo y en la muestra visual: negritas y trazo
    # engrosado, números de hasta 4 cifras, número negro en un aro de color y texto negro del dibujo
    # encima del número.
    "general": {"heights": [(.5, 4.2, 7.), (.5, 7., 28.)], "ratio": (1.25, 3.1), "filled": .15, "thick": .35,
                "pointer": .3, "clean": .3, "fit_text": True, "digits": 4, "bold": .3, "stroke": .2,
                "black_text": .35, "overlay": .25},
}


def draw_balloon(draw: ImageDraw.ImageDraw, rng, cx, cy, radius, text, font, ink, ring, filled=False,
                 text_ink=None, stroke=0):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=ink, width=ring,
                 fill=ink if filled else None)
    if text:
        box = draw.textbbox((0, 0), text, font=font, anchor="ls", stroke_width=stroke)
        x = cx - (box[0] + box[2]) / 2 + rng.normal(0, radius * .04)
        y = cy - (box[1] + box[3]) / 2 + rng.normal(0, radius * .04)
        colour = (255, 255, 255) if filled else text_ink or ink
        draw.text((x, y), text, font=font, fill=colour, anchor="ls", stroke_width=stroke, stroke_fill=colour)


def synth(seed: int, profile: str = "3212") -> tuple[np.ndarray, str]:
    rng = np.random.default_rng(seed)
    p = PROFILES[profile]
    digits = p.get("digits", 3)
    label = random_label(rng, digits)
    choices = fonts(BOLD_FONTS) if p.get("bold") and rng.random() < p["bold"] else fonts()
    path, ratio = choices[rng.integers(len(choices))]
    weights = np.array([w for w, _, _ in p["heights"]])
    _, low, high = p["heights"][rng.choice(len(weights), p=weights / weights.sum())]
    digit_height = rng.uniform(low, high)
    font = ImageFont.truetype(path, max(8, int(round(digit_height * SUPER / ratio))))
    stroke = int(round(font.size * rng.uniform(.02, .07))) if p.get("stroke") and rng.random() < p["stroke"] else 0
    text_ink = (0, 0, 0) if p.get("black_text") and rng.random() < p["black_text"] else None
    text_width = (font.getbbox(label, stroke_width=stroke)[2] - font.getbbox(label, stroke_width=stroke)[0]) / SUPER
    radius = max(digit_height * rng.uniform(*p["ratio"]), text_width * .55 + 1)  # el número cabe en el globo
    size = int(np.ceil(radius * 2 + 14))
    ink = tuple(int(np.clip(c + rng.normal(0, 18), 0, 255)) for c in INKS[rng.integers(len(INKS))])
    image = Image.new("RGB", (size * SUPER, size * SUPER), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    centre = size / 2 + rng.uniform(-.5, .5, 2)
    cx, cy, r = centre[0] * SUPER, centre[1] * SUPER, radius * SUPER
    thick = rng.random() < p["thick"]
    ring = max(1, int(round((rng.uniform(.08, .18) * r) if thick else rng.uniform(.7, 1.5) * SUPER)))
    filled = rng.random() < p["filled"]
    if rng.random() < p["pointer"]:  # pico del globo hacia la cota, como en infra-CONVERT
        angle = rng.uniform(0, 2 * np.pi)
        tip = (cx + 1.5 * r * np.cos(angle), cy + 1.5 * r * np.sin(angle))
        side = [(cx + r * np.cos(angle + d), cy + r * np.sin(angle + d)) for d in (-.6, .6)]
        draw.polygon([side[0], tip, side[1]], fill=ink)
    for _ in range(rng.poisson(.5)):  # globos vecinos que se solapan, como los racimos 155.x
        angle, distance = rng.uniform(0, 2 * np.pi), rng.uniform(1.1, 2.0) * r
        draw_balloon(draw, rng, cx + distance * np.cos(angle), cy + distance * np.sin(angle), r,
                     random_label(rng, digits), font, ink, ring, filled, text_ink, stroke)
    for _ in range(rng.poisson(.9)):  # líneas del dibujo; a veces cruzan el texto
        angle = rng.uniform(0, np.pi) if rng.random() < .5 else rng.choice([0, np.pi / 2])
        offset = rng.normal(0, r * (.25 if rng.random() < .35 else .9))
        dx, dy = np.cos(angle), np.sin(angle)
        px, py = cx - dy * offset, cy + dx * offset
        colour = (0, 0, 0) if rng.random() < .6 else ink
        draw.line([px - dx * 3 * r, py - dy * 3 * r, px + dx * 3 * r, py + dy * 3 * r], fill=colour,
                  width=max(1, int(rng.uniform(.5, 1.6) * SUPER)))
    draw_balloon(draw, rng, cx, cy, r, label, font, ink, ring, filled, text_ink, stroke)
    if p.get("overlay") and rng.random() < p["overlay"]:  # cota o texto negro del plano sobre el número
        other_path, other_ratio = fonts()[rng.integers(len(fonts()))]
        other = ImageFont.truetype(other_path, max(8, int(font.size * rng.uniform(.8, 1.6))))
        words = [str(int(rng.integers(1, 100))), f"R{rng.uniform(.1, 9):.1f}", f"Ø{rng.uniform(1, 60):.1f}", "2X", "A"]
        draw.text((cx + rng.uniform(-.7, .3) * r, cy + rng.uniform(-.6, .2) * r), words[rng.integers(len(words))],
                  font=other, fill=(0, 0, 0))
    small = cv2.resize(np.array(image), (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    blur = rng.uniform(0, .75)
    if blur > .15:
        small = cv2.GaussianBlur(small, (0, 0), blur)
    small = np.clip(small + rng.normal(0, rng.uniform(0, 5), small.shape), 0, 255).astype(np.uint8)
    if rng.random() < p["clean"]:  # ráster nítido exportado del CAD, sin JPEG
        rgb = small
    else:
        buffer = io.BytesIO()
        Image.fromarray(small).save(buffer, "JPEG", quality=int(rng.integers(55, 96)), subsampling=2)
        rgb = np.array(Image.open(buffer).convert("RGB"))
    # El detector de círculos no da el centro exacto: el recorte se desplaza igual que en el plano.
    circle = (centre[0] + rng.normal(0, .6), centre[1] + rng.normal(0, .6), radius + rng.normal(0, .5))
    padded = cv2.copyMakeBorder(rgb, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    crop = bench.text_crop(padded, (circle[0] + 8, circle[1] + 8, circle[2]), "luma", fit_text=p["fit_text"])
    return to_input(crop), label


def to_input(gray: np.ndarray) -> np.ndarray:
    return cv2.resize(gray, INPUT[::-1], interpolation=cv2.INTER_AREA)


def build_model():
    import torch.nn as nn

    def block(a, b, pool):
        return [nn.Conv2d(a, b, 3, padding=1), nn.BatchNorm2d(b), nn.ReLU(inplace=True)] + \
               ([nn.MaxPool2d(pool)] if pool else [])

    class CRNN(nn.Module):
        # 0,24 M parámetros: suficiente para 12 caracteres y entrenable en minutos en un portátil.
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(*block(1, 16, (2, 2)), *block(16, 32, (2, 2)), *block(32, 64, None),
                                          *block(64, 64, (2, 1)), *block(64, 96, (2, 1)),
                                          nn.Conv2d(96, 128, (2, 1)), nn.ReLU(inplace=True))
            self.rnn = nn.LSTM(128, 64, bidirectional=True, batch_first=True)
            self.head = nn.Linear(128, len(CHARACTERS) + 1)

        def forward(self, x):  # B×1×32×64 → B×16×clases
            features = self.features(x).squeeze(2).transpose(1, 2)
            return self.head(self.rnn(features)[0])
    return CRNN()


def tensor(batch: np.ndarray):
    import torch
    return torch.from_numpy((batch.astype(np.float32) / 255 - .5) / .5)[:, None]


def generate(count: int, offset: int, workers: int, profile: str) -> tuple[np.ndarray, list[str]]:
    with Pool(workers) as pool:
        samples = pool.map(partial(synth, profile=profile), range(offset, offset + count), chunksize=256)
    return np.stack([s[0] for s in samples]), [s[1] for s in samples]


def model_path(profile: str) -> Path:
    return OUTPUT / "modelo.pt" if profile == "3212" else OUTPUT / profile / "modelo.pt"


def train(args):
    import torch
    torch.manual_seed(0)
    torch.set_num_threads(args.hilos)
    start = time.perf_counter()
    images, labels = generate(args.muestras, 0, args.hilos, args.perfil)
    check_images, check_labels = generate(2000, 10_000_000, args.hilos, args.perfil)
    print(f"{len(images)} imágenes sintéticas en {time.perf_counter() - start:.0f}s", flush=True)
    index = {c: i + 1 for i, c in enumerate(CHARACTERS)}
    targets = [torch.tensor([index[c] for c in label]) for label in labels]
    model = build_model()
    steps = args.epocas * (len(images) // args.lote)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=2e-3, total_steps=steps)
    ctc = torch.nn.CTCLoss(blank=0, zero_infinity=True)
    rng = np.random.default_rng(1)
    for epoch in range(args.epocas):
        model.train()
        order, losses = rng.permutation(len(images)), []
        for first in range(0, len(order) - args.lote + 1, args.lote):
            chosen = order[first:first + args.lote]
            x = tensor(images[chosen])
            # Variación de contraste por lote: tinta más clara u oscura que en la síntesis.
            x = x * torch.empty(len(x), 1, 1, 1).uniform_(.75, 1.15) + torch.empty(len(x), 1, 1, 1).uniform_(-.12, .12)
            y = [targets[i] for i in chosen]
            log_probs = model(x).log_softmax(2).transpose(0, 1)
            loss = ctc(log_probs, torch.cat(y), torch.full((len(y),), log_probs.shape[0], dtype=torch.long),
                       torch.tensor([len(t) for t in y]))
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5)
            optimizer.step()
            schedule.step()
            losses.append(loss.item())
        accuracy = synthetic_accuracy(model, check_images, check_labels)
        print(f"época {epoch + 1}/{args.epocas}: pérdida {np.mean(losses):.3f}, "
              f"acierto sintético {accuracy:.1%}, {time.perf_counter() - start:.0f}s", flush=True)
    destination = model_path(args.perfil)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state": model.state_dict(), "characters": CHARACTERS, "input": INPUT,
                "profile": args.perfil}, destination)
    print(f"Modelo: {destination}")


def greedy_text(probs: np.ndarray) -> str:
    best, out, previous = probs.argmax(1), [], 0
    for k in best:
        if k and k != previous:
            out.append(CHARACTERS[k - 1])
        previous = k
    return "".join(out)


def synthetic_accuracy(model, images, labels) -> float:
    import torch
    model.eval()
    with torch.no_grad():
        probs = model(tensor(images)).softmax(2).numpy()
    return float(np.mean([greedy_text(p) == label for p, label in zip(probs, labels)]))


class OwnRecognizer(bench.CTCRecognizer):
    """La CRNN entrenada aquí, con la misma interfaz que los reconocedores PP-OCR del banco."""

    def __init__(self, model_path: Path):
        import torch
        saved = torch.load(model_path, map_location="cpu")
        self.model = build_model()
        self.model.load_state_dict(saved["state"])
        self.model.eval()
        self.characters = ["<blank>"] + saved["characters"]
        self.allowed = np.arange(1, len(self.characters))

    def probabilities(self, gray: np.ndarray, min_width: int = 0) -> np.ndarray:
        import torch
        with torch.no_grad():
            return self.model(tensor(to_input(gray)[None])).softmax(2)[0].numpy()


def export_onnx(profile: str, destination: Path) -> None:
    """Exporta el modelo entrenado a ONNX (entrada lotes × 1 × 32 × 64, salida logits) con sus metadatos.

    La aplicación lo ejecuta con onnxruntime, sin torch. Se comprueba que ONNX y torch dan las mismas
    probabilidades en imágenes sintéticas antes de escribir los metadatos.
    """
    import onnxruntime as ort
    import torch
    source = model_path(profile)
    saved = torch.load(source, map_location="cpu")
    model = build_model()
    model.load_state_dict(saved["state"])
    model.eval()
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(model, torch.zeros(1, 1, *INPUT), str(destination), input_names=["imagen"],
                      output_names=["logits"], dynamic_axes={"imagen": {0: "lote"}, "logits": {0: "lote"}},
                      opset_version=17, dynamo=False)
    images = np.stack([synth(seed, profile)[0] for seed in range(20_000_000, 20_000_064)])
    with torch.no_grad():
        expected = model(tensor(images)).softmax(2).numpy()
    logits = ort.InferenceSession(str(destination), providers=["CPUExecutionProvider"]).run(
        None, {"imagen": tensor(images).numpy()})[0]
    exponent = np.exp(logits - logits.max(2, keepdims=True))
    difference = float(np.abs(exponent / exponent.sum(2, keepdims=True) - expected).max())
    if difference > 1e-4:
        raise SystemExit(f"ONNX y torch no coinciden (diferencia máxima {difference})")
    import hashlib
    import json
    destination.with_suffix(".json").write_text(json.dumps({
        "perfil": profile, "caracteres": saved["characters"], "entrada": list(INPUT),
        "normalizacion": "(gris / 255 - 0,5) / 0,5", "salida": "logits CTC; índice 0 = blanco",
        "modelo_torch_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "onnx_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "diferencia_max_probabilidades": difference,
        "entrenado_con": "solo imágenes sintéticas (entrenar_lector_globos.py); ningún dato del cliente",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destination} · diferencia máxima ONNX/torch {difference:.2e}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exportar-onnx", type=Path, metavar="DESTINO",
                        help="Exportar el modelo del perfil a ONNX (con metadatos .json) y salir")
    parser.add_argument("--muestras", type=int, default=80_000)
    parser.add_argument("--epocas", type=int, default=10)
    parser.add_argument("--lote", type=int, default=128)
    parser.add_argument("--hilos", type=int, default=8)
    parser.add_argument("--perfil", choices=sorted(PROFILES), default="amplio",
                        help="3212: el primer modelo; amplio: planos variados (por defecto)")
    parser.add_argument("--salida", type=Path, default=OUTPUT, help="Carpeta de la hoja de muestra")
    parser.add_argument("--muestra-png", action="store_true", help="Guardar una hoja con 64 imágenes sintéticas")
    args = parser.parse_args()
    if args.exportar_onnx:
        export_onnx(args.perfil, args.exportar_onnx)
        return
    if args.muestra_png:
        args.salida.mkdir(parents=True, exist_ok=True)
        tiles = [cv2.copyMakeBorder(cv2.resize(synth(i, args.perfil)[0], None, fx=3, fy=3,
                                               interpolation=cv2.INTER_NEAREST),
                                    2, 2, 2, 2, cv2.BORDER_CONSTANT, value=180) for i in range(64)]
        sheet = np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, 64, 8)])
        cv2.imwrite(str(args.salida / f"muestra-sintetica-{args.perfil}.png"), sheet)
        print(" ".join(synth(i, args.perfil)[1] for i in range(64)))
        return
    train(args)


if __name__ == "__main__":
    main()
