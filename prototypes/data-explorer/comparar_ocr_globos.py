"""Compara lectores de números de globo contra una lectura de referencia del mismo plano.

    py -3.11 prototypes/data-explorer/comparar_ocr_globos.py
    py -3.11 prototypes/data-explorer/comparar_ocr_globos.py --lectores ppocr-v4 tesseract

Usa los círculos del índice del buscador del 28/10 (out/buscar-en-plano/indice-2026-10-28.json) y la lectura
de referencia del 3212 (chuleta-2026-10-28.json, fuera de Git). Solo lee: no cambia el índice
ni el buscador. Cada lector se mide en globos reales: acierto, error o sin lectura.

Los lectores que no estén instalados se omiten y se avisa. Los opcionales se instalan en un
entorno aparte (ver README, «Comparativa de lectores de globos»).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buscar_en_plano as finder

HERE = Path(__file__).resolve().parent
# Índice del 28/10/2026, congelado: la lectura de referencia se hizo sobre sus círculos.
INDEX = HERE / "out" / "buscar-en-plano" / "indice-2026-10-28.json"
REFERENCE = HERE / "out" / "buscar-en-plano" / "chuleta-2026-10-28.json"
OUTPUT = HERE / "out" / "comparar-ocr"
# Fuera del repo y de OneDrive: son cientos de MB y se descargan del catálogo de RapidOCR.
MODELS = Path(os.environ.get("LOCALAPPDATA", "")) / "inteplast" / "ocr-models"
ALLOWED = "0123456789.T"


def load_balloons(index: Path, reference: Path) -> tuple[np.ndarray, list[dict]]:
    data = json.loads(index.read_text(encoding="utf-8"))
    truth = json.loads(reference.read_text(encoding="utf-8"))
    if truth["pdf_sha256"] != data["signature"]["sha256"]:
        raise SystemExit("La referencia corresponde a otro PDF.")
    labels = {g["id"]: g["lectura_visual"] for g in truth["globos"]}
    page = data["pages"][0]
    rgb = cv2.cvtColor(cv2.imread(str(index.parent / page["image"])), cv2.COLOR_BGR2RGB)
    balloons = [{"id": b["id"], "circle": b["circle"], "truth": labels.get(b["id"])}
                for b in data["balloons"] if b["page"] == page["number"]]
    return rgb, balloons


# --- Vistas del recorte -------------------------------------------------------------------------
# El JPEG del 3212 guarda el color a media resolución (4:2:0): la luminancia es el canal más nítido.

def luma(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)[:, :, 0]


def colour_strength(rgb: np.ndarray) -> np.ndarray:
    r, g, b = [c.astype(np.int16) for c in cv2.split(rgb)]
    return np.maximum(np.minimum(g - r, g - b), np.minimum(b - r, b - g))


def channel(rgb: np.ndarray, name: str) -> np.ndarray:
    if name == "rojo":
        return rgb[:, :, 0]
    if name == "luma":
        return luma(rgb)
    if name == "luma-color":
        # Luminancia solo donde hay tinta de color cerca: quita líneas negras del dibujo.
        near = cv2.dilate(np.uint8(colour_strength(rgb) > 12), np.ones((3, 3), np.uint8))
        return np.where(near > 0, luma(rgb), 255).astype(np.uint8)
    raise ValueError(name)


def ink_box(rgb: np.ndarray, circle) -> tuple[float, float, float, float] | None:
    """Caja del número dentro del globo: tinta oscura del interior que no toca el aro.

    Las líneas del dibujo y el propio aro cruzan el borde interior y se descartan. Sin tinta
    aislada (por ejemplo, una línea que atraviesa el número) devuelve None.
    """
    x, y, radius = round(circle[0]), round(circle[1]), circle[2]
    inner = int(radius * .82)
    if inner < 4 or y - inner < 0 or x - inner < 0:
        return None
    gray = luma(rgb[y - inner:y + inner + 1, x - inner:x + inner + 1])
    if gray.shape != (2 * inner + 1, 2 * inner + 1):
        return None
    yy, xx = np.mgrid[-inner:inner + 1, -inner:inner + 1]
    distance = np.hypot(xx, yy)
    inside = distance <= inner
    if np.median(gray[inside]) < 128:
        gray = 255 - gray
    threshold, _ = cv2.threshold(gray[inside].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = ((gray <= threshold) & inside).astype(np.uint8)  # Otsu de OpenCV: fondo = valores > umbral
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    edge = np.unique(labels[(distance >= inner - 1.5) & inside])
    keep = [i for i in range(1, count) if i not in edge and stats[i, cv2.CC_STAT_AREA] >= 2]
    if not keep:
        return None
    x0 = min(stats[i, 0] for i in keep)
    y0 = min(stats[i, 1] for i in keep)
    x1 = max(stats[i, 0] + stats[i, 2] for i in keep)
    y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
    return x - inner + x0, y - inner + y0, x - inner + x1, y - inner + y1


def text_crop(rgb: np.ndarray, circle, view: str, scale: float = 4, pad: int = 8,
              width: float = .84, height: float = .43, shift: tuple[int, int] = (0, 0),
              fit_text: bool = False) -> np.ndarray:
    """Interior del globo, sin el aro, ampliado. Devuelve gris uint8.

    La geometría por defecto es la vista «Canal rojo · interior» de buscar_en_plano.py: un píxel
    más o menos de recorte cambia mucho el resultado de los lectores con cifras de este tamaño.
    Con `fit_text` el recorte se centra en la tinta del número y se escala a su altura (el número
    ocupa el 44 % del alto, como en el 3212), sea cual sea la proporción entre número y globo.
    """
    x, y, radius = circle
    box = ink_box(rgb, circle) if fit_text else None
    if box:
        text_h, text_w = box[3] - box[1], box[2] - box[0]
        crop_h = max(text_h / .44, text_w * 1.1 / 1.95)
        x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        width, height, radius = .975, .5, crop_h  # mismo encuadre 1,95:1 que el recorte por defecto
        scale = scale * 12 / max(12., crop_h)  # recortes grandes: no se amplían más de lo necesario
    x, y = round(x) + shift[0], round(y) + shift[1]
    half_w, half_h, margin = max(3, int(radius * width)), max(3, int(radius * height)), 2
    region = rgb[max(0, y - half_h - margin):y + half_h + 1 + margin,
                 max(0, x - half_w - margin):x + half_w + 1 + margin]
    gray = channel(region, view)[margin:-margin, margin:-margin]
    if gray.size and np.median(gray) < 128:  # globo relleno con el número en claro: siempre tinta oscura
        gray = 255 - gray
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(big, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)


# --- Lectores ----------------------------------------------------------------------------------
# Cada lector recibe recortes en gris y devuelve, por recorte, una lista de (texto, puntuación).

def label_of(text: str) -> str | None:
    return finder.ocr_number(text.replace(" ", ""))


class CTCRecognizer:
    """Reconocedor CTC en ONNX (PP-OCR). Da acceso a las probabilidades por columna."""

    def __init__(self, model: Path, characters: list[str], height: int = 48):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        self.session = ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
        self.characters = ["<blank>"] + characters + [" "]
        self.height = height
        self.allowed = np.array([i for i, c in enumerate(self.characters) if c in ALLOWED])

    @classmethod
    def from_metadata(cls, model: Path) -> "CTCRecognizer":
        import onnxruntime as ort
        meta = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"]).get_modelmeta()
        return cls(model, meta.custom_metadata_map["character"].splitlines())

    def probabilities(self, gray: np.ndarray, min_width: int = 320) -> np.ndarray:
        # Igual que RapidOCR: alto 48 y lienzo de al menos 320 px. Sin ese relleno lee mucho peor.
        h, w = gray.shape
        width = max(16, int(np.ceil(w * self.height / h)))
        image = cv2.resize(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), (width, self.height),
                           interpolation=cv2.INTER_LINEAR)
        x = np.zeros((self.height, max(min_width, width), 3), np.float32)
        x[:, :width] = (image.astype(np.float32) / 255 - .5) / .5
        return self.session.run(None, {self.session.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0]

    def greedy(self, probs: np.ndarray, restrict: bool) -> tuple[str, float]:
        if restrict:
            keep = np.concatenate([[0], self.allowed])
            sub = probs[:, keep]
            best = keep[sub.argmax(1)]
            score = sub.max(1) / np.maximum(sub.sum(1), 1e-9)
        else:
            best, score = probs.argmax(1), probs.max(1)
        text, chosen, previous = [], [], 0
        for t, k in enumerate(best):
            if k and k != previous:
                text.append(self.characters[k])
                chosen.append(score[t])
            previous = k
        return "".join(text).strip(), float(np.mean(chosen)) if chosen else 0.


def ctc_log_likelihood(log_probs: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """log P(etiqueta | columnas) por el algoritmo forward de CTC, para varias etiquetas de igual longitud."""
    n, length = targets.shape
    steps = log_probs.shape[0]
    states = 2 * length + 1
    ext = np.zeros((n, states), dtype=int)
    ext[:, 1::2] = targets
    skip = np.zeros((n, states), dtype=bool)
    skip[:, 3::2] = targets[:, 1:] != targets[:, :-1]
    emit = log_probs[:, ext]  # steps × n × states
    alpha = np.full((n, states), -np.inf)
    alpha[:, 0], alpha[:, 1] = emit[0, :, 0], emit[0, :, 1]
    for t in range(1, steps):
        stay = alpha
        step = np.concatenate([np.full((n, 1), -np.inf), alpha[:, :-1]], 1)
        jump = np.concatenate([np.full((n, 2), -np.inf), alpha[:, :-2]], 1)
        jump = np.where(skip, jump, -np.inf)
        alpha = np.logaddexp(np.logaddexp(stay, step), jump) + emit[t]
    return np.logaddexp(alpha[:, -1], alpha[:, -2])


def lexicon(max_number: int = 999) -> list[str]:
    """Identificadores posibles de un globo: 1–999, con sufijo .1–.9 o .T opcional."""
    return [f"{n}{suffix}" for n in range(1, max_number + 1)
            for suffix in [""] + [f".{d}" for d in range(1, 10)] + [".T"]]


class LexiconScorer:
    def __init__(self, recognizer: CTCRecognizer, words: list[str]):
        index = {c: i for i, c in enumerate(recognizer.characters)}
        self.groups = {}
        for word in words:
            self.groups.setdefault(len(word), []).append(word)
        self.targets = {n: np.array([[index[c] for c in w] for w in ws]) for n, ws in self.groups.items()}

    def scores(self, probs: np.ndarray) -> dict[str, float]:
        # Las columnas de relleno son casi seguro «blanco»: recortarlas acelera sin cambiar el orden.
        active = np.nonzero(probs[:, 0] < .98)[0]
        if len(active):
            probs = probs[max(0, active[0] - 1):active[-1] + 2]
        log_probs = np.log(np.maximum(probs, 1e-12))
        out = {}
        for n, words in self.groups.items():
            if 2 * n + 1 > 2 * log_probs.shape[0] + 1:
                continue
            for word, value in zip(words, ctc_log_likelihood(log_probs, self.targets[n])):
                out[word] = float(value)
        return out


def ctc_reader(recognizer: CTCRecognizer, mode: str, words: list[str]):
    """libre: lo que lea el modelo; digitos: solo 0-9 . T; lexico: el identificador válido más probable."""
    scorer = LexiconScorer(recognizer, words) if mode == "lexico" else None

    def read(crops):
        results = []
        for gray in crops:
            probs = recognizer.probabilities(gray)
            if scorer:
                scored = scorer.scores(probs)
                best = sorted(scored.items(), key=lambda kv: -kv[1])[:20]
                total = np.logaddexp.reduce(np.array(list(scored.values())))
                results.append([(w, float(np.exp(s - total))) for w, s in best])
            else:
                results.append([recognizer.greedy(probs, restrict=mode == "digitos")])
        return results
    return read


def ppocr_reader(model: Path, mode: str, words: list[str]):
    return ctc_reader(CTCRecognizer.from_metadata(model), mode, words)


def own_reader(mode: str, words: list[str], profile: str = "3212"):
    from entrenar_lector_globos import OwnRecognizer, model_path
    path = model_path(profile)
    if not path.is_file():
        raise FileNotFoundError(f"{path}: ejecutar antes entrenar_lector_globos.py --perfil {profile}")
    return ctc_reader(OwnRecognizer(path), mode, words)


def tesseract_reader():
    import pytesseract
    executable = finder.find_tesseract()
    if not executable:
        raise ImportError("Tesseract no encontrado")
    pytesseract.pytesseract.tesseract_cmd = executable

    def read(crops):
        out = []
        for gray in crops:
            raw = pytesseract.image_to_data(gray, config=f"--psm 7 -c tessedit_char_whitelist={ALLOWED}",
                                            output_type=pytesseract.Output.DICT)
            words = [(t, float(c) / 100) for t, c in zip(raw["text"], raw["conf"]) if t.strip()]
            out.append([("".join(t for t, _ in words), min((c for _, c in words), default=0.))] if words else [])
        return out
    return read


def onnxtr_reader(architecture: str):
    from onnxtr.models import recognition_predictor
    predictor = recognition_predictor(architecture)

    def read(crops):
        images = [cv2.cvtColor(g, cv2.COLOR_GRAY2RGB) for g in crops]
        return [[(text, float(score))] for text, score in predictor(images)]
    return read


def easyocr_reader():
    import easyocr
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def read(crops):
        out = []
        for gray in crops:
            h, w = gray.shape
            found = reader.recognize(gray, horizontal_list=[[0, w, 0, h]], free_list=[],
                                     allowlist=ALLOWED, detail=1)
            out.append([(text, float(score)) for _, text, score in found])
        return out
    return read


def trocr_reader(name: str):
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    processor = TrOCRProcessor.from_pretrained(name)
    model = VisionEncoderDecoderModel.from_pretrained(name).eval()

    def read(crops):
        out = []
        with torch.no_grad():
            for start in range(0, len(crops), 16):
                batch = [cv2.cvtColor(g, cv2.COLOR_GRAY2RGB) for g in crops[start:start + 16]]
                pixels = processor(images=batch, return_tensors="pt").pixel_values
                generated = model.generate(pixels, max_new_tokens=8, output_scores=True,
                                           return_dict_in_generate=True)
                texts = processor.batch_decode(generated.sequences, skip_special_tokens=True)
                scores = model.compute_transition_scores(generated.sequences, generated.scores,
                                                         normalize_logits=True).exp()
                out.extend([(text, float(s[s > 0].mean()) if (s > 0).any() else 0.)]
                           for text, s in zip(texts, scores))
        return out
    return read


def ppocr_models(folder: Path) -> dict[str, Path]:
    """Reconocedores PP-OCR en ONNX (catálogo de RapidOCR 3), con su alfabeto en los metadatos."""
    import rapidocr_onnxruntime
    found = {"ppocr-v4": Path(rapidocr_onnxruntime.__file__).parent / "models" / "ch_PP-OCRv4_rec_infer.onnx"}
    for model in sorted(folder.glob("*rec*.onnx")):
        name = model.stem.lower().replace("_rec", "").replace("pp-ocr", "").replace("_", "-")
        found["ppocr-" + name] = model
    return found


def available_readers(words: list[str], models: Path) -> dict:
    """Nombre → constructor. Se construyen al usarse, para no cargar lo que no se pide."""
    readers = {"propio": lambda: own_reader("digitos", words), "propio-lexico": lambda: own_reader("lexico", words),
               "propio-amplio": lambda: own_reader("digitos", words, "amplio")}
    for name, model in ppocr_models(models).items():
        for mode, suffix in (("libre", ""), ("digitos", "-digitos"), ("lexico", "-lexico")):
            readers[name + suffix] = lambda m=model, mode=mode: ppocr_reader(m, mode, words)
    readers |= {
        "tesseract": tesseract_reader,
        "easyocr": easyocr_reader,
        "trocr-small-printed": lambda: trocr_reader("microsoft/trocr-small-printed"),
        "trocr-base-printed": lambda: trocr_reader("microsoft/trocr-base-printed"),
    }
    for arch in ("crnn_vgg16_bn", "crnn_mobilenet_v3_large", "parseq", "vitstr_base", "master", "sar_resnet31"):
        readers[f"doctr-{arch}"] = lambda arch=arch: onnxtr_reader(arch)
    return readers


# --- Combinación -------------------------------------------------------------------------------

SHIFTS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]


def merge(runs: list[list[list[tuple[str, float]]]]) -> list[list[tuple[str, float]]]:
    """Varios recortes del mismo globo (desplazados 1 px): media de la puntuación de cada identificador."""
    merged = []
    for options in zip(*runs):
        totals = {}
        for candidates in options:
            for text, score in candidates:
                label = label_of(text)
                if label:
                    totals[label] = totals.get(label, 0.) + score / len(options)
        merged.append(sorted(totals.items(), key=lambda kv: -kv[1]))
    return merged


def unique_assignment(predictions: list[list[tuple[str, float]]], floor: float = 1e-3):
    """Un identificador aparece una sola vez por plano: asignación de máxima probabilidad conjunta.

    No usa la posición ni la numeración vecina. Un globo sin candidato por encima de `floor`
    se queda sin lectura en vez de recibir un número sobrante.
    """
    from scipy.optimize import linear_sum_assignment
    labels = sorted({label for p in predictions for label, _ in p})
    column = {label: i for i, label in enumerate(labels)}
    n = len(predictions)
    cost = np.full((n, len(labels) + n), 50.)
    cost[np.arange(n), len(labels) + np.arange(n)] = -np.log(floor)
    for i, candidates in enumerate(predictions):
        for label, score in candidates:
            cost[i, column[label]] = -np.log(max(score, 1e-12))
    out = []
    for i, j in zip(*linear_sum_assignment(cost)):
        if j >= len(labels):
            out.append([])
            continue
        chosen = labels[j]
        out.append([(chosen, dict(predictions[i])[chosen])] + [(l, s) for l, s in predictions[i] if l != chosen])
    return out


class SynthesisVerifier:
    """Dibuja cada candidato con la tipografía del plano y lo compara con el globo original.

    Comparación de plantillas clásica, sin red: correlación normalizada sobre la luminancia a
    resolución nativa, con desplazamientos de un cuarto de píxel. Tipografía, altura de cifra y
    desenfoque se calibran con el propio plano y sin referencias: la combinación que mejor
    explica el candidato principal de una muestra de globos.
    """

    FONTS = ("arial.ttf", "ARIALN.TTF", "tahoma.ttf", "verdana.ttf", "isocpeur.ttf", "swisop1.ttf",
             "simplex_IV50.ttf")
    SUPER = 8

    def __init__(self, rgb: np.ndarray):
        self.ink = 255. - luma(rgb).astype(np.float32)
        self.fonts, self.cache, self.style = {}, {}, None

    def font(self, name: str, height: float):
        from PIL import ImageFont
        key = (name, height)
        if key not in self.fonts:
            path = str(Path(r"C:\Windows\Fonts") / name)
            probe = ImageFont.truetype(path, 100).getbbox("0123456789")
            ratio = (probe[3] - probe[1]) / 100
            self.fonts[key] = ImageFont.truetype(path, max(8, round(height * self.SUPER / ratio)))
        return self.fonts[key]

    def template(self, label: str, style: tuple, phase: tuple[int, int]) -> np.ndarray:
        from PIL import Image, ImageDraw
        key = (label, style, phase)
        if key not in self.cache:
            name, height, blur = style
            font, text, k = self.font(name, height), label.removeprefix("N"), self.SUPER
            box = font.getbbox(text)
            width = int(np.ceil((box[2] - box[0] + 3 * k) / k)) * k
            tall = int(np.ceil((box[3] - box[1] + 3 * k) / k)) * k
            image = Image.new("L", (width, tall), 0)
            ImageDraw.Draw(image).text((k + phase[0] - box[0], k + phase[1] - box[1]), text, font=font, fill=255)
            small = cv2.resize(np.asarray(image, np.float32), (width // k, tall // k), interpolation=cv2.INTER_AREA)
            self.cache[key] = cv2.GaussianBlur(small, (0, 0), blur) if blur else small
        return self.cache[key]

    def score(self, circle, label: str, style: tuple, phases=(0, 2, 4, 6)) -> float:
        x, y, radius = round(circle[0]), round(circle[1]), circle[2]
        half = int(radius * .95)
        window = self.ink[max(0, y - 8):y + 9, max(0, x - half):x + half + 1]
        best = -1.
        for px in phases:
            for py in phases:
                template = self.template(label, style, (px, py))
                if template.shape[0] > window.shape[0] or template.shape[1] > window.shape[1] or not template.any():
                    continue
                best = max(best, float(cv2.matchTemplate(window, template, cv2.TM_CCOEFF_NORMED).max()))
        return best

    def calibrate(self, balloons: list[dict], predictions, sample: int = 60) -> tuple:
        chosen = [(b, p[0][0]) for b, p in zip(balloons, predictions) if p][::max(1, len(balloons) // sample)]
        styles = [(f, h, b) for f in self.FONTS if (Path(r"C:\Windows\Fonts") / f).is_file()
                  for h in (4.5, 5., 5.5, 6., 6.5) for b in (0, .5, .8)]
        fit = {s: np.mean([self.score(b["circle"], label, s, phases=(0, 4)) for b, label in chosen]) for s in styles}
        self.style = max(fit, key=fit.get)
        return self.style

    def rerank(self, balloons: list[dict], predictions, top: int, temperature: float = .03, with_prior: bool = False):
        """Reordena los `top` primeros candidatos por su parecido con el dibujo (y su probabilidad previa)."""
        out = []
        for balloon, candidates in zip(balloons, predictions):
            candidates = candidates[:top]
            if not candidates:
                out.append([])
                continue
            logits = np.array([self.score(balloon["circle"], label, self.style) / temperature
                               + (np.log(max(score, 1e-12)) if with_prior else 0.) for label, score in candidates])
            posterior = np.exp(logits - np.logaddexp.reduce(logits))
            order = np.argsort(-posterior)
            out.append([(candidates[i][0], float(posterior[i])) for i in order])
        return out


# --- Medición ----------------------------------------------------------------------------------

def evaluate(balloons: list[dict], predictions: list[list[tuple[str, float]]]) -> dict:
    rows, counts = [], {"acierto": 0, "error": 0, "sin_lectura": 0, "en_top": 0}
    for balloon, candidates in zip(balloons, predictions):
        labels = [label_of(text) for text, _ in candidates]
        labels = [l for l in labels if l]
        first = labels[0] if labels else None
        score = next((s for t, s in candidates if label_of(t)), 0.)
        if balloon["truth"] is None:
            continue
        outcome = "sin_lectura" if not first else "acierto" if first == balloon["truth"] else "error"
        counts[outcome] += 1
        counts["en_top"] += balloon["truth"] in labels[:5]
        rows.append({"id": balloon["id"], "referencia": balloon["truth"], "lectura": first,
                     "alternativas": labels[1:5], "puntuacion": round(score, 4), "resultado": outcome})
    counts["globos"] = len(rows)
    return {"resumen": counts, "detalle": rows}


def precision_curve(rows: list[dict]) -> list[dict]:
    """Aciertos y errores si solo se aceptan lecturas por encima de cada umbral de puntuación."""
    read = sorted((r for r in rows if r["lectura"]), key=lambda r: -r["puntuacion"])
    curve, correct = [], 0
    for i, row in enumerate(read, 1):
        correct += row["resultado"] == "acierto"
        if i == len(read) or read[i]["puntuacion"] < row["puntuacion"]:
            curve.append({"umbral": row["puntuacion"], "aceptadas": i, "aciertos": correct, "errores": i - correct})
    return curve


def best_at_precision(curve: list[dict], max_error_rate: float) -> dict | None:
    ok = [c for c in curve if c["errores"] <= max_error_rate * c["aceptadas"]]
    return max(ok, key=lambda c: c["aciertos"]) if ok else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lectores", nargs="*", help="Lectores a medir (por defecto, todos los instalados)")
    parser.add_argument("--vistas", nargs="*", default=["rojo", "luma", "luma-color"])
    parser.add_argument("--escala", type=float, default=4)
    parser.add_argument("--desplazados", action="store_true",
                        help="Leer cinco recortes desplazados 1 px por globo y promediar")
    parser.add_argument("--texto", action="store_true",
                        help="Centrar el recorte en la tinta del número y escalarlo a su altura")
    parser.add_argument("--unicos", action="store_true",
                        help="Medir también la asignación con un identificador por globo")
    parser.add_argument("--sintesis", type=int, default=0, metavar="K",
                        help="Reordenar los K primeros candidatos comparándolos con su dibujo")
    parser.add_argument("--salida", type=Path, default=OUTPUT)
    parser.add_argument("--modelos", type=Path, default=MODELS, help="Carpeta con reconocedores PP-OCR en ONNX")
    parser.add_argument("--listar", action="store_true", help="Mostrar los lectores disponibles y salir")
    args = parser.parse_args()
    words = lexicon()
    readers = available_readers(words, args.modelos)
    if args.listar:
        print("\n".join(readers))
        return
    rgb, balloons = load_balloons(INDEX, REFERENCE)
    args.salida.mkdir(parents=True, exist_ok=True)
    results_file = args.salida / "resultados.json"
    results = json.loads(results_file.read_text(encoding="utf-8")) if results_file.is_file() else {}
    for name in args.lectores or readers:
        if name not in readers:
            print(f"{name}: desconocido. Usa --listar.")
            continue
        try:
            read = readers[name]()
        except (ImportError, OSError, FileNotFoundError) as error:
            print(f"{name}: no disponible ({error})")
            continue
        for view in args.vistas:
            start = time.perf_counter()
            runs = [read([text_crop(rgb, b["circle"], view, args.escala, shift=s, fit_text=args.texto)
                          for b in balloons])
                    for s in (SHIFTS if args.desplazados else SHIFTS[:1])]
            merged = merge(runs)
            seconds = time.perf_counter() - start
            key = (f"{name} · {view} · x{args.escala:g}" + (" · texto" if args.texto else "")
                   + (" · desplazados" if args.desplazados else ""))
            variants = [(key, merged)]
            if args.sintesis:
                verifier = SynthesisVerifier(rgb)
                print(f"  Tipografía calibrada: {verifier.calibrate(balloons, merged)}", flush=True)
                variants += [(f"{key} · síntesis top{args.sintesis}", verifier.rerank(balloons, merged, args.sintesis)),
                             (f"{key} · síntesis+previa top{args.sintesis}",
                              verifier.rerank(balloons, merged, args.sintesis, with_prior=True))]
            if args.unicos:
                variants += [(label + " · únicos", unique_assignment(p)) for label, p in variants]
            for label, predictions in variants:
                evaluation = evaluate(balloons, predictions)
                curve = precision_curve(evaluation["detalle"])
                summary = evaluation["resumen"]
                summary.update(segundos=round(seconds, 1), con_1pct_error=best_at_precision(curve, .01),
                               con_0_error=best_at_precision(curve, 0))
                results[label] = {"resumen": summary, "detalle": evaluation["detalle"]}
                safe = summary["con_1pct_error"] or {}
                print(f"{label:66} aciertos {summary['acierto']:3}  errores {summary['error']:3}  "
                      f"vacíos {summary['sin_lectura']:3}  top5 {summary['en_top']:3}  "
                      f"≤1% error: {safe.get('aciertos', 0):3}  {seconds:6.1f}s", flush=True)
            results_file.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
