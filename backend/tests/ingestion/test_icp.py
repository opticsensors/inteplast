"""Stamps of an infra-CONVERT project: reading, placing on a page and choosing the project.

All data is generated here: no customer file is needed.
"""

import math
import struct
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from app.ingestion import drawing, icp
from app.ingestion.balloon_reader import label_of


def stamp_bytes(
    label: str,
    number: int,
    head: tuple[float, float],
    tip: tuple[float, float],
    *,
    z: float = 0.0,
) -> bytes:
    name = f"INFRA_CONVERT_STAMP_{number}".encode()
    text = label.encode("latin-1")
    return (
        struct.pack("<I", len(text))
        + text
        + struct.pack("<I", len(name))
        + name
        + struct.pack("<6d", head[0], head[1], z, tip[0], tip[1], z)
        + b"\x01\x00\x00\x00ELIASEMPTY"
    )


def project(stamps: list[icp.Stamp]) -> bytes:
    return b"HEADER\x00" + b"".join(
        stamp_bytes(s.label, s.number, s.points[0], s.points[1]) for s in stamps
    )


def grid(count: int = 24, *, first: int = 1) -> list[icp.Stamp]:
    """Stamps spread over an A3 sheet (420 x 297 mm, origin in the centre, Y up)."""
    stamps = []
    for i in range(count):
        x = -180 + 60 * (i % 6) + 7 * (i // 6)
        y = 110 - 55 * (i // 6) - 9 * (i % 6)
        # Leaders of different lengths and directions, as on a real drawing: with a
        # constant one, heads and tips would only differ by a shift of the page.
        tip = (x + 6 + 9 * (i % 4), y - 4 - 7 * (i % 3))
        stamps.append(icp.Stamp(first + i, str(first + i), ((x, y), tip)))
    return stamps


def on_page(
    stamps: list[icp.Stamp],
    size: tuple[int, int],
    *,
    scale: float,
    turn: float = 0.0,
    flip: int = 1,
    shift: tuple[float, float] = (0.0, 0.0),
    head: int = 0,
) -> list[tuple[float, float, float]]:
    """Balloon circles where the stamps are drawn on a page image, for a known print."""
    width, height = size
    circles = []
    for stamp in stamps:
        x, y = stamp.points[head]
        y = flip * y
        px = scale * (math.cos(turn) * x - math.sin(turn) * y) + width / 2 + shift[0]
        py = scale * (math.sin(turn) * x + math.cos(turn) * y) + height / 2 + shift[1]
        circles.append((px, py, 12.0))
    return circles


def readings(
    stamps: list[icp.Stamp], wrong: dict[int, str] | None = None
) -> list[set[str]]:
    wrong = wrong or {}
    return [
        {wrong.get(i, label_of(stamp.label) or "")} for i, stamp in enumerate(stamps)
    ]


def test_stamps_are_read_with_the_length_of_their_name() -> None:
    # The first byte of the coordinate after «…_128» is the ASCII digit 7: a reader that
    # takes every digit after the name would read stamp 1287 and shift the coordinates.
    x = struct.unpack("<d", b"7" + struct.pack("<d", 12.5)[1:])[0]
    data = project(
        [
            icp.Stamp(128, "128", ((x, 40.0), (20.0, 35.0))),
            icp.Stamp(129, "236.T", ((-15.0, -2.5), (-10.0, 0.0))),
        ]
    )
    stamps = icp.read_stamps(data)
    assert [(s.number, s.label) for s in stamps] == [(128, "128"), (129, "236.T")]
    assert stamps[0].points == ((x, 40.0), (20.0, 35.0))
    assert icp.read_stamps(b"no stamps here") == []
    assert icp.stamps_digest(stamps) == icp.stamps_digest(stamps[::-1])


@pytest.mark.parametrize(
    "data,message",
    [
        (stamp_bytes("7", 7, (0, 0), (1, 1)) * 2, "repetido"),
        (stamp_bytes("7", 7, (0, 0), (1, 1), z=3.0), "fuera de rango"),
        (stamp_bytes("7", 7, (1e9, 0), (1, 1)), "fuera de rango"),
        (stamp_bytes("7", 7, (0, 0), (1, 1))[:40], "sin coordenadas"),
        (b"\x18\x00\x00\x00INFRA_CONVERT_STAMP_ABCD" + bytes(60), "inesperado"),
        (b"\x00\x00\x00\x00" + stamp_bytes("7", 7, (0, 0), (1, 1))[5:], "sin texto"),
    ],
)
def test_an_unexpected_file_is_an_error_not_an_approximate_reading(
    data: bytes, message: str
) -> None:
    with pytest.raises(icp.IcpFormatError, match=message):
        icp.read_stamps(data)


@pytest.mark.parametrize(
    "turn,flip,head,scale",
    [
        (0.0, -1, 0, 8.0),  # usual print: the Y axis of the drawing points up
        (math.pi / 2, -1, 0, 5.5),  # page turned a quarter
        (0.03, 1, 1, 11.0),  # mirrored, slightly skewed scan; tip stored first
    ],
)
def test_fit_recovers_turn_scale_shift_and_mirror_from_the_drawn_balloons(
    turn: float, flip: int, head: int, scale: float
) -> None:
    stamps = grid()
    size = (5000, 3600)
    circles = on_page(
        stamps, size, scale=scale, turn=turn, flip=flip, shift=(40, -25), head=head
    )
    # A fifth of the readings are wrong; three balloons are extra and two are not drawn.
    read = readings(stamps, wrong={0: "N9", 5: "N7", 11: "N3", 17: "N20", 23: "N1"})
    circles = circles[:-2] + [(300.0, 300.0, 12.0), (900.0, 3300.0, 12.0)]
    read = read[:-2] + [set(), {"N555"}]
    labels = [label_of(s.label) for s in stamps]
    fit = icp.fit_to_balloons(stamps, circles, read, labels, size)
    assert fit is not None and fit.method == "balloons"
    assert (fit.head, fit.flip) == (head, flip)
    assert fit.inliers >= 17
    placed = icp.place(stamps, fit)
    expected = on_page(
        stamps, size, scale=scale, turn=turn, flip=flip, shift=(40, -25), head=head
    )
    for stamp, (x, y, _) in zip(placed, expected, strict=True):
        assert math.hypot(stamp["x"] * size[0] - x, stamp["y"] * size[1] - y) < 2
    # Wrongly read balloons still get their stamp: the match is by position.
    match = icp.match_balloons(placed, circles, size)
    assert match[:22] == list(range(22)) and match[22:] == [None, None]


def test_too_few_agreeing_balloons_do_not_place_anything() -> None:
    stamps = grid()
    size = (5000, 3600)
    circles = on_page(stamps, size, scale=8.0, flip=-1)
    labels = [label_of(s.label) for s in stamps]
    # Only 9 balloons read: below the minimum, however well they agree.
    read = [r if i < 9 else set() for i, r in enumerate(readings(stamps))]
    assert icp.fit_to_balloons(stamps, circles, read, labels, size) is None
    # Readings of another drawing: nothing consistent to fit.
    other = [{f"N{900 + i}"} for i in range(len(stamps))]
    assert icp.fit_to_balloons(stamps, circles, other, labels, size) is None


def test_one_to_one_is_only_accepted_when_the_stamps_fall_on_the_sheet() -> None:
    stamps = grid()
    a3 = (420 / icp.MM_PER_POINT, 297 / icp.MM_PER_POINT)
    fit = icp.fit_at_scale(stamps, *a3)
    assert fit is not None and fit.method == "scale"
    first = icp.place(stamps, fit)[0]
    assert first["x"] == pytest.approx(0.5 - 180 / 420)
    assert first["y"] == pytest.approx(0.5 - 110 / 297)  # Y up in the drawing
    # The same drawing printed on a sheet half the size: most stamps fall outside.
    assert icp.fit_at_scale(stamps, a3[0] / 2, a3[1] / 2) is None


def choose(
    projects, circles, read, *, single_page=True, stem="drawing", size=(5000, 3600)
):
    return icp.choose(
        projects,
        circles,
        read,
        label_of,
        size,
        (420 / icp.MM_PER_POINT, 297 / icp.MM_PER_POINT),
        single_page=single_page,
        stem=stem,
    )


def test_the_project_that_the_drawn_balloons_agree_with_is_chosen() -> None:
    right, other = grid(), grid(first=200)
    size = (5000, 3600)
    circles = on_page(right, size, scale=8.0, flip=-1)
    placement, notice = choose(
        {"other.icp": other, "right.icp": right}, circles, readings(right)
    )
    assert notice is None and placement is not None
    assert placement.file == "right.icp" and not placement.approximate
    assert placement.fit.method == "balloons"


def test_page_without_balloons_takes_the_only_project_that_fits_and_says_approximate() -> (
    None
):
    placement, notice = choose({"plan.icp": grid()}, [], [])
    assert notice is None and placement is not None
    assert placement.fit.method == "scale" and placement.approximate
    assert len(placement.stamps) == 24


def test_ambiguous_or_contradicted_projects_are_not_placed() -> None:
    two = {"a.icp": grid(), "b.icp": grid(first=200)}
    placement, notice = choose(two, [], [])
    assert placement is None and "varios .icp" in (notice or "")
    # The name of the PDF settles it only between projects that fit.
    placement, _ = choose(two, [], [], stem="B")
    assert placement is not None and placement.file == "b.icp"
    # A PDF with several pages cannot tell which page a project belongs to.
    placement, notice = choose({"plan.icp": grid()}, [], [], single_page=False)
    assert placement is None and "varias páginas" in (notice or "")
    # Twelve drawn balloons that are nowhere near the stamps contradict the 1:1 print.
    elsewhere = [(4500.0 + 10 * i, 3400.0, 12.0) for i in range(12)]
    placement, notice = choose(
        {"plan.icp": grid()}, elsewhere, [set() for _ in elsewhere]
    )
    assert placement is None and "no cuadra" in (notice or "")


def test_drawn_balloons_keep_their_identity_and_take_the_number_of_the_project() -> (
    None
):
    stamps = grid()
    size = (5000, 3600)
    circles = on_page(stamps, size, scale=8.0, flip=-1)
    balloons = [
        {
            "id": f"p1-b{i}",
            "page": 1,
            "box": [x / size[0], y / size[1], x / size[0], y / size[1]],
            "circle": [x, y, r],
            # OCR read the first one wrong and abstained on the second.
            "candidates": [{"label": "N999"}]
            if i == 0
            else []
            if i == 1
            else [{"label": f"N{i + 1}"}],
        }
        for i, (x, y, r) in enumerate(circles[:-1])  # the last stamp is not drawn
    ]
    notices: list[str] = []
    page = SimpleNamespace(
        number=0,
        rect=SimpleNamespace(
            width=420 / icp.MM_PER_POINT, height=297 / icp.MM_PER_POINT
        ),
    )
    summary = drawing.place_project(
        {"plan.icp": stamps},
        balloons,
        readings(stamps)[:-1],
        size,
        page,
        single_page=True,
        stem="plan",
        notices=notices,
    )
    assert notices == []
    assert summary is not None
    assert (summary["file"], summary["method"], summary["approximate"]) == (
        "plan.icp",
        "balloons",
        False,
    )
    assert (summary["stamps"], summary["on_balloons"], summary["not_drawn"]) == (
        24,
        23,
        1,
    )
    assert (summary["ocr_agree"], summary["ocr_differ"]) == (21, 1)
    assert [b["id"] for b in balloons[:23]] == [f"p1-b{i}" for i in range(23)]
    assert [b["candidates"][0]["label"] for b in balloons] == [
        f"N{i + 1}" for i in range(24)
    ]
    assert balloons[0]["ocr"] == [{"label": "N999"}] and balloons[1]["ocr"] == []
    assert all(b["method"] == "icp" for b in balloons)
    added = balloons[23]
    assert added["id"] == "p1-i24" and added["drawn"] is False
    assert "approximate" not in added
    expected_x = circles[23][0] / size[0]
    assert (added["box"][0] + added["box"][2]) / 2 == pytest.approx(
        expected_x, abs=1e-3
    )


def test_index_of_a_clean_drawing_offers_the_stamps_as_approximate(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "plan.pdf"
    with fitz.open() as document:
        page = document.new_page(
            width=420 / icp.MM_PER_POINT, height=297 / icp.MM_PER_POINT
        )
        page.insert_text((60, 60), "DRAWING WITHOUT BALLOONS")
        document.save(pdf)
    project_file = tmp_path / "cache-name.icp"
    project_file.write_bytes(project(grid()))
    broken = tmp_path / "broken.icp"
    broken.write_bytes(stamp_bytes("7", 7, (0, 0), (1, 1)) * 2)

    plain = drawing.build_index(pdf, tmp_path / "plain", use_ocr=False)
    assert "icp" not in plain["signature"] and plain["balloons"] == []
    assert "icp" not in plain["pages"][0]

    data = drawing.build_index(
        pdf,
        tmp_path / "out",
        use_ocr=False,
        icp={"plan.icp": project_file, "old.icp": broken},
    )
    assert [f["name"] for f in data["signature"]["icp"]] == ["plan.icp"]
    assert data["signature"]["icp"][0]["stamps"] == 24
    assert any("old.icp: .icp no reconocido" in n for n in data["notices"])
    assert data["pages"][0]["icp"]["method"] == "scale"
    assert data["pages"][0]["icp"]["approximate"] is True
    assert len(data["balloons"]) == 24
    assert {b["method"] for b in data["balloons"]} == {"icp"}
    assert all(b["approximate"] and not b["drawn"] for b in data["balloons"])
    assert data["balloons"][0]["candidates"][0]["label"] == "N1"
    # Everything else of the index is what it was without the project.
    for key in ("words", "filename"):
        assert data[key] == plain[key]


def test_converter_passes_the_projects_with_their_original_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import sys

    from app import evidence_converter

    seen = {}

    def fake_index(pdf: Path, output: Path, **options: object) -> dict[str, object]:
        seen.update(pdf=pdf, output=output, **options)
        return {"pages": []}

    monkeypatch.setattr(drawing, "build_index", fake_index)
    projects = json.dumps([["Plan.icp", str(tmp_path / "a1b2.icp")]])
    for extra in ([projects], []):
        monkeypatch.setattr(
            sys, "argv", ["converter", "drawing", "plan.pdf", str(tmp_path), *extra]
        )
        evidence_converter.main()
        expected = {"Plan.icp": tmp_path / "a1b2.icp"} if extra else {}
        assert seen["icp"] == expected and seen["use_ocr"] is True
    assert json.loads((tmp_path / "result.json").read_text()) == {"pages": []}
