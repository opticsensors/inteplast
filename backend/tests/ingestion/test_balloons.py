"""Balloon detection, vector layer, combined reading and thresholds with generated drawings."""

import importlib.util
import json
from functools import partial
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytest

from app.ingestion import balloon_reader as reading
from app.ingestion import drawing, drawing_version

NUMBERS = ["12", "345", "7", "208", "1560", "33", "91"]


def balloon_pdf(
    path: Path, vector: int = 0, single: int = 0, raster: int = 0, hidden: int = 0
) -> None:
    """A4 landscape page with a grey «scan» and blue balloons of radius 6 pt (1.5 % of the short side).

    `vector`: like infra-CONVERT, each ring drawn as many short segments (row y=100). `single`:
    vector circles of one stroke (y=150). `raster`: balloons inside the scanned image (y=300).
    `hidden`: vector balloons over a blue band of the scan (y=220): only visible in the layer.
    """
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=400)
        scan = np.full((400, 600, 3), 200, np.uint8)
        cv2.line(scan, (0, 350), (599, 350), (0, 0, 0), 3)
        for i in range(raster):
            cv2.circle(scan, (40 + 50 * i, 300), 6, (255, 0, 0), 1)  # BGR blue
        if hidden:
            cv2.rectangle(scan, (0, 200), (599, 240), (255, 0, 0), -1)
        page.insert_image(page.rect, stream=cv2.imencode(".png", scan)[1].tobytes())
        angles = np.linspace(0, 2 * np.pi, 40)
        for y, count in ((100, vector), (220, hidden)):
            for i in range(count):
                cx = 40 + 50 * i
                for a, b in zip(angles[:-1], angles[1:], strict=True):
                    page.draw_line(
                        (cx + 6 * np.cos(a), y + 6 * np.sin(a)),
                        (cx + 6 * np.cos(b), y + 6 * np.sin(b)),
                        color=(0, 0, 1),
                        width=1,
                    )
        for i in range(single):
            page.draw_circle((40 + 50 * i, 150), 6, color=(0, 0, 1), width=1)
        doc.save(path)


def source(path: Path, **kwargs: int) -> tuple[np.ndarray, list[dict], str, list[dict]]:
    balloon_pdf(path, **kwargs)
    with fitz.open(path) as doc:
        work, balloons, kind = drawing.balloon_source(path, doc[0])
        full = drawing.detect_balloons(drawing.page_raster(doc[0]))
    return work, balloons, kind, full


def no_duplicates(balloons: list[dict]) -> bool:
    centres = [b["circle"] for b in balloons]
    return all(
        np.hypot(a[0] - b[0], a[1] - b[1]) > 0.5 * max(a[2], b[2])
        for i, a in enumerate(centres)
        for b in centres[i + 1 :]
    )


def numbered_scan() -> np.ndarray:
    """Seven blue balloons with black numbers, in OpenCV's built-in font (RGB)."""
    image = np.full((1000, 1600, 3), 255, np.uint8)
    for i, text in enumerate(NUMBERS):
        cx = 120 + 200 * i
        cv2.circle(image, (cx, 500), 24, (0, 0, 255), 2)
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(
            image,
            text,
            (cx - w // 2, 500 + h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
    return image


def test_vector_balloons_are_read_without_the_scan(tmp_path: Path) -> None:
    work, balloons, kind, _ = source(tmp_path / "p.pdf", vector=9)
    assert (len(balloons), kind) == (9, "capa vectorial")
    x, y, _ = balloons[0]["circle"]
    assert work[round(y), round(x)].tolist() == [255, 255, 255]


def test_eight_vector_and_two_raster_balloons_give_ten(tmp_path: Path) -> None:
    _, balloons, kind, _ = source(tmp_path / "p.pdf", vector=8, raster=2)
    assert len(balloons) == 10 and no_duplicates(balloons)
    assert (
        sorted(b["fuente"] for b in balloons) == ["capa vectorial"] * 8 + ["imagen"] * 2
    )
    assert kind.startswith("mixta")


def test_balloon_only_in_the_vector_layer_is_kept(tmp_path: Path) -> None:
    _, balloons, kind, full = source(tmp_path / "p.pdf", vector=3, hidden=1)
    assert len(full) == 3  # the blue band hides it in the full page
    assert len(balloons) == 4 and no_duplicates(balloons) and kind == "capa vectorial"


def test_a_few_single_stroke_circles_are_not_lost(tmp_path: Path) -> None:
    _, balloons, kind, _ = source(tmp_path / "p.pdf", single=6)
    assert (len(balloons), kind) == (6, "capa vectorial")


def test_a_rejected_small_pair_does_not_stop_a_valid_large_one() -> None:
    circle = lambda x, r: {"circle": [x, 0, r]}  # noqa: E731
    assert drawing.pair_balloons(
        [circle(0, 4), circle(100, 40)], [circle(3, 4), circle(110, 40)]
    ) == [(1, 1)]


def test_holes_inside_the_numbers_do_not_set_the_balloon_size() -> None:
    image = np.full((700, 1300, 3), 255, np.uint8)
    for cx in range(110, 1200, 140):
        cv2.circle(image, (cx, 350), 24, (0, 0, 255), 2)
        for dx, dy in ((-13, 0), (13, 0), (0, -13)):
            cv2.circle(image, (cx + dx, 350 + dy), 5, (0, 0, 255), 2)
    radii = [b["circle"][2] for b in drawing.detect_balloons(image)]
    assert len(radii) == 8 and all(20 < r < 28 for r in radii)


def test_one_dominant_balloon_size_per_page() -> None:
    # Known limitation, kept visible: two very different families in similar numbers keep one.
    image = np.full((1000, 1600, 3), 255, np.uint8)
    for i in range(6):
        cv2.circle(image, (110 + 250 * i, 250), 10, (0, 0, 255), 2)
        cv2.circle(image, (110 + 250 * i, 700), 40, (0, 0, 255), 2)
    sizes = {round(b["circle"][2]) // 10 for b in drawing.detect_balloons(image)}
    assert len(sizes) == 1


def test_own_reader_reads_drawn_numbers() -> None:
    reader = reading.own_reader()
    assert reader is not None
    image = numbered_scan()
    found = sorted(drawing.detect_balloons(image), key=lambda b: b["circle"][0])
    probs = reader.probabilities([reading.text_crop(image, b["circle"]) for b in found])
    assert probs.shape[1:] == (16, len(reader.characters) + 1)
    assert [reader.greedy(p)[0] for p in probs] == NUMBERS


@pytest.mark.skipif(
    importlib.util.find_spec("rapidocr_onnxruntime") is None, reason="sin RapidOCR"
)
def test_index_offers_combined_readings_with_their_source(tmp_path: Path) -> None:
    pdf = tmp_path / "scan.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=1600 * 72 / 200, height=1000 * 72 / 200)
        bgr = cv2.cvtColor(numbered_scan(), cv2.COLOR_RGB2BGR)
        page.insert_image(page.rect, stream=cv2.imencode(".png", bgr)[1].tobytes())
        doc.save(pdf)
    data = drawing.build_index(pdf, tmp_path / "out", use_ocr=True)
    assert data["signature"]["lector"] == drawing_version.reader_id()
    balloons = sorted(data["balloons"], key=lambda b: b["box"][0])
    assert [b["candidates"][0]["label"] for b in balloons] == [f"N{n}" for n in NUMBERS]
    assert {b["fuente"] for b in balloons} == {"imagen"}
    methods = [r["method"] for r in balloons[0]["candidates"][0]["readings"]]
    assert methods == ["Combinado", "RapidOCR", "Lector propio"]


def test_mixed_page_uses_the_threshold_of_each_balloon_source() -> None:
    balloons = [
        {"fuente": "capa vectorial"},
        {"fuente": "imagen"},
        {"fuente": "imagen"},
    ]
    choices = [[("N12", 0.5)], [("N13", 0.5)], [("N14", 0.7)]]
    reading.offer_readings(
        balloons,
        choices,
        [[], [], []],
        [[], [], []],
        {"capa vectorial": 0.4, "imagen": 0.6},
    )
    offered = [
        b["candidates"][0]["label"] if b["candidates"] else None for b in balloons
    ]
    assert offered == ["N12", None, "N14"]


def test_one_number_per_drawing() -> None:
    predictions = [
        [("N155", 0.9), ("N156", 0.1)],
        [("N155", 0.6), ("N165", 0.4)],
        [("N155", 1e-5)],
    ]
    assigned = reading.unique_assignment(predictions)
    assert [p[0][0] if p else None for p in assigned] == ["N155", "N165", None]


def test_shifted_readings_are_averaged() -> None:
    assert reading.merge([[[("155", 0.8)]], [[("156", 0.6)]]]) == [
        [("N155", 0.4), ("N156", 0.3)]
    ]


def test_reader_identity_follows_model_and_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drawing_version.reader_id.cache_clear()
    first = drawing_version.reader_id()
    monkeypatch.setitem(drawing_version.THRESHOLDS, "imagen", 0.7)
    drawing_version.reader_id.cache_clear()
    assert drawing_version.reader_id() != first
    drawing_version.reader_id.cache_clear()


def test_reader_identity_follows_both_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = tmp_path / "reader.onnx"
    metadata = model.with_suffix(".json")
    monkeypatch.setattr(drawing_version, "MODEL", model)

    def identity() -> str:
        drawing_version.reader_id.cache_clear()
        return drawing_version.reader_id()

    try:
        missing = identity()
        model.write_bytes(b"model-a")
        missing_metadata = identity()
        metadata.write_text('{"caracteres": ["0", "1"], "entrada": [32, 64]}')
        first = identity()
        metadata.write_text('{"caracteres": ["1", "0"], "entrada": [32, 64]}')
        changed_metadata = identity()
        model.write_bytes(b"model-b")
        changed_model = identity()
        assert (
            len({missing, missing_metadata, first, changed_metadata, changed_model})
            == 5
        )
    finally:
        drawing_version.reader_id.cache_clear()


@pytest.mark.parametrize(
    "failure",
    [
        "missing-model",
        "invalid-model",
        "missing-metadata",
        "invalid-json",
        "missing-characters",
        "missing-dimensions",
        "invalid-characters",
        "invalid-dimensions",
        "wrong-dimensions",
        "wrong-alphabet-size",
        "null-metadata",
    ],
)
def test_unavailable_or_invalid_reader_returns_none(
    failure: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = tmp_path / "reader.onnx"
    metadata = model.with_suffix(".json")
    meta = json.loads(reading.MODEL.with_suffix(".json").read_text(encoding="utf-8"))
    model.write_bytes(reading.MODEL.read_bytes())
    if failure == "missing-model":
        model.unlink()
    elif failure == "invalid-model":
        model.write_bytes(b"not an ONNX model")
    elif failure == "missing-characters":
        del meta["caracteres"]
    elif failure == "missing-dimensions":
        del meta["entrada"]
    elif failure == "invalid-characters":
        meta["caracteres"] = "0123456789.T"
    elif failure == "invalid-dimensions":
        meta["entrada"] = [0, 64]
    elif failure == "wrong-dimensions":
        meta["entrada"] = [32, 32]
    elif failure == "wrong-alphabet-size":
        meta["caracteres"] = ["0"]
    elif failure == "null-metadata":
        meta = None
    if failure != "missing-metadata":
        metadata.write_text("{" if failure == "invalid-json" else json.dumps(meta))
    monkeypatch.setattr(reading, "OwnReader", partial(reading.OwnReader, model=model))
    reading.own_reader.cache_clear()
    try:
        assert reading.own_reader() is None
    finally:
        reading.own_reader.cache_clear()


def test_missing_reader_keeps_balloons_and_pdf_text_without_offering_numbers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = tmp_path / "page.pdf"
    balloon_pdf(pdf, vector=2)
    with fitz.open(pdf) as doc:
        doc[0].insert_text((50, 50), "N987")
        doc.saveIncr()
    monkeypatch.setattr(drawing, "own_reader", lambda: None)
    monkeypatch.setattr(drawing, "find_tesseract", lambda: None)
    monkeypatch.setattr(
        drawing, "read_balloons", lambda *_: pytest.fail("unvalidated fallback")
    )
    data = drawing.build_index(pdf, tmp_path / "out")
    assert len(data["balloons"]) == 2
    assert all(b["candidates"] == [] for b in data["balloons"])
    assert any(w["text"] == "N987" and w["method"] == "pdf" for w in data["words"])
    assert data["signature"]["lector"] is None
    assert any("sin lectura automática" in notice for notice in data["notices"])
