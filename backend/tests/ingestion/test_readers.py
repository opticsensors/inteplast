"""Exercise real file parsing and the converter with no exploratory code available."""

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import fitz
import numpy as np
import pytest

from app.ingestion import cmm, drawing, profile_pdf
from app.ingestion.pilot_3212 import actions, catalog, measurements, study


def test_csv_sign_correction_keeps_original_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "intern.03" / "c13" / "3212_c13.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "POSICIONS N117\n"
        "32;Posición Z;;31.000;0.100;-0.100;-30.990;-61.990;-61.890;<<---+-----\n"
        "31;Posición Z;;31.000;0.100;-0.100;-30.990;-61.990;-61.890;<<---+-----\n",
        encoding="cp1252",
    )
    raw = cmm.read_csv(path)
    corrected = cmm.correct_sign(raw)
    row = corrected.iloc[0]
    assert row["medido"] == pytest.approx(30.990)
    assert row["desviacion"] == pytest.approx(-0.010)
    assert not row["nok"]
    assert row["medido_original"] == -30.990
    assert row["nok_original"]
    assert corrected.iloc[1]["medido"] == -30.990
    assert raw.iloc[0]["medido"] == -30.990
    cmm.pd.testing.assert_frame_equal(corrected, cmm.correct_sign(corrected))
    assert cmm.discover(tmp_path)[0]["muestreo"] == "03"
    assert cmm.discover(tmp_path)[0]["cavidad"] == "c13"


def test_repeated_csv_headers_keep_cmm_identity_in_real_catalog(tmp_path: Path) -> None:
    path = tmp_path / "4- Metrologia" / "intern.01" / "3212_c13.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "N170 BOLT 1 MIN/MAX H=5.0 mm\n"
        "15;Diametro;;4.000;0.000;-0.100;3.970;-0.030;;\n"
        ";Cálculo de fórmula;;4.000;0.000;-0.100;4.020;0.020;0.020;>>\n"
        "N170 BOLT 1 MIN/MAX H=5.0 mm\n"
        "16;Diametro;;4.000;0.000;-0.100;3.980;-0.020;;\n"
        ";Cálculo de fórmula;;4.000;0.000;-0.100;4.010;0.010;0.010;>>\n",
        encoding="cp1252",
    )
    data = catalog.load_catalog(tmp_path, {}, {"N170": {}})
    assert data["row_count"] == 4
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert len(entry["series"]) == 4
    assert {series["label"] for series in entry["series"]} == {
        f"B{bolt}-H5.0 · {metric}" for bolt in (1, 2) for metric in ("GX", "LP máximo")
    }
    records, _ = measurements.load_csv(tmp_path)
    assert records[("01", "c13", "N170", "B2-H5.0", 2)]["value"] == 4.010
    assert records[("01", "c13", "N170", "B2-H5.0", 2)]["status"] == "outside"
    assert "CMM 16" in records[("01", "c13", "N170", "B2-H5.0", 2)]["source"]["locator"]
    duplicate = path.with_name("13_3212.csv")
    duplicate.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="CSV duplicado"):
        catalog.load_catalog(tmp_path, {}, {})


@pytest.mark.parametrize("complete", [True, False])
def test_profile_pdf_table_and_unknown_state(tmp_path: Path, complete: bool) -> None:
    path = tmp_path / "PA_1.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((40, 60), "Contorno (21) -0.025 -0.242 -0.217")
        if complete:
            page.insert_text((40, 80), "CONTORN (10) 0.025 0.020 0.000")
        document.save(path)
    result = profile_pdf.read_pdf(path, tmp_path, 1, "profile")
    assert result["infr_inf"] == -0.217
    assert (tmp_path / result["png"]).is_file()
    if complete:
        assert profile_pdf.measurement_errors(result) == []
        assert profile_pdf.worst_excess(result) == 0.217
    else:
        assert profile_pdf.measurement_errors(result)
        assert profile_pdf.worst_excess(result) is None


def test_pptx_actions_keep_sources_and_skip_external_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slide = """<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <a:p><a:r><a:t>Tool correction 1.33 (DIM. Nr.170)</a:t></a:r></a:p>
        <a:p><a:r><a:t>Acción revisada</a:t></a:r></a:p>
        <a:p><a:r><a:t>OK</a:t></a:r></a:p>
        <p:pic><a:blip r:embed="local"/></p:pic>
        <p:pic><a:blip r:embed="remote"/></p:pic>
        </p:sld>"""
    relationships = """<Relationships>
        <Relationship Id="local" Target="../media/image.png"/>
        <Relationship Id="remote" Target="https://example.invalid/image.png" TargetMode="External"/>
        </Relationships>"""
    path = tmp_path / "correction.pptx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", relationships)
        archive.writestr("ppt/media/image.png", b"embedded-image")
    monkeypatch.setattr(actions, "CORRECTIONS", {"1": {"pptx": path.name}})
    monkeypatch.setattr(actions, "CASES", {"N170": {"actions": ["1.33"]}})
    assets = tmp_path / "assets"
    assets.mkdir()
    index = actions.extract_action_index(tmp_path, assets)
    entry = index["1.33"]
    assert entry["features"] == ["N170"]
    assert len(entry["images"]) == 1
    assert (tmp_path / entry["images"][0]["url"]).read_bytes() == b"embedded-image"
    assert entry["source"]["path"] == path.name
    assert "diapositiva 1" in entry["source"]["locator"]
    case = actions.extract_actions(tmp_path, assets)["1.33"]
    assert case["marker"] == "OK"
    assert case["paragraphs"] == ["Acción revisada"]
    assert len(case["images"]) == 1


def test_balloon_ocr_keeps_complete_identifiers_and_observations() -> None:
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    balloons = [{"circle": [50, 50, 15], "candidates": []}]

    def engine(
        *_args: object, **_kwargs: object
    ) -> tuple[list[tuple[str, float]], None]:
        return [("[170]", 0.9), ("I70", 0.99), ("170.2", 0.8)], None

    drawing.read_balloons(image, balloons, engine)
    assert {candidate["label"] for candidate in balloons[0]["candidates"]} == {
        "N170",
        "N170.2",
    }
    assert all(
        len(candidate["readings"]) == 3 for candidate in balloons[0]["candidates"]
    )


def test_drawing_candidate_ids_remain_compatible_with_saved_reviews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = tmp_path / "drawing.pdf"
    with fitz.open() as document:
        document.new_page()
        document.save(pdf)
    box = [0.1, 0.2, 0.3, 0.4]
    monkeypatch.setattr(
        drawing,
        "detect_balloons",
        lambda _rgb: [{"box": box, "circle": [50, 50, 15], "candidates": []}],
    )
    result = drawing.build_index(pdf, tmp_path, use_ocr=False)
    expected = hashlib.sha256(json.dumps(box).encode()).hexdigest()[:12]
    assert result["balloons"][0]["id"] == f"p1-b{expected}"
    assert result["balloons"][0]["box"] == box
    assert result["signature"]["sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()


def test_converter_runs_with_only_backend_readers(tmp_path: Path) -> None:
    """Copy only production modules: no repository root, prototype scripts or viewers."""
    source = Path(drawing.__file__).resolve().parents[1]
    sandbox = tmp_path / "standalone"
    app = sandbox / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    shutil.copytree(
        source / "ingestion",
        app / "ingestion",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copyfile(source / "evidence_converter.py", app / "evidence_converter.py")
    pdf = tmp_path / "drawing.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((40, 50), "N170 N170.2 " + "note " * 23)
        document.save(pdf)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); "
            "from app.ingestion.pilot_3212.study import build_data; "
            "runpy.run_module('app.evidence_converter',run_name='__main__')",
            str(sandbox),
            "drawing",
            str(pdf),
            str(tmp_path / "output"),
        ],
        cwd=sandbox,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "output/result.json").read_text(encoding="utf-8"))
    assert payload["words"][0]["text"] == "N170"
    assert payload["signature"]["ocr"] is True
    assert payload["notices"] == []


def test_study_releases_open_workbooks_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    book = Mock()
    monkeypatch.setattr(study, "load_csv", lambda _root: ({}, []))
    monkeypatch.setattr(
        study.xlrd,
        "open_workbook",
        Mock(side_effect=[book, ValueError("bad workbook")]),
    )
    with pytest.raises(ValueError, match="bad workbook"):
        study.build_data(tmp_path, tmp_path / "assets")
    book.release_resources.assert_called_once_with()
