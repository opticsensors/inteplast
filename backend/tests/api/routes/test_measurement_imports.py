import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.evidence import job_id
from app.ingestion.measurement_csv import parse
from app.knowledge_models import (
    EvidenceJob,
    FeatureCharacteristicLink,
    PartCharacteristic,
)
from app.measurement_models import MeasurementImport
from app.models import FeaturePartLink
from tests.utils.feature import create_random_feature, create_random_part

API = f"{settings.API_V1_STR}/evidence/parts"


def csv_text(value: str = "3.950", code: str = "N170") -> bytes:
    return (
        f"************\n{code} DIAMETRO\n11;Diámetro;;4.000;0.000;-0.100;{value};-0.050;;--**--\n"
        f";Máximo;;4.000;0.000;-0.100;3.990;-0.010;;--**--\n"
    ).encode("cp1252")


@pytest.fixture
def piece(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    part = create_random_part(db)
    part.folder_path = f"{part.code} Housing"
    feature = create_random_feature(db)
    db.add(part)
    db.add(FeaturePartLink(feature_id=feature.id, part_id=part.id))
    db.commit()
    folder = tmp_path / part.folder_path
    folder.mkdir()
    return part, feature, folder


def write(folder: Path, path: str, content: bytes | None = None):
    file = folder / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(content or csv_text())
    return file


def request_file(file, **updates):
    return {
        k: v
        for k, v in {**file, **updates}.items()
        if k in {"path", "sha256", "revision", "sample", "cavity", "replace_existing"}
    }


def test_import_shared_piece_with_review_history_and_revisions(
    client: TestClient, db: Session, normal_user_token_headers, piece
):
    part, feature, folder = piece
    first = write(folder, "intern.01/c1/export.csv")
    url = f"{API}/{part.id}/measurements"
    headers = normal_user_token_headers
    assert client.post(f"{url}/preview", json={}).status_code == 401
    preview = client.post(f"{url}/preview", headers=headers, json={}).json()
    file = preview["files"][0]
    assert file["status"] == "needs_context" and file["revision"] == ""
    assert (file["sample"], file["cavity"]) == ("01", "c1")
    assert file["examples"][0]["value"] == 3.95
    assert file["examples"][0]["tol_inf"] == -0.1
    assert (
        db.exec(
            select(PartCharacteristic).where(PartCharacteristic.part_id == part.id)
        ).first()
        is None
    )
    body = {"context_key": preview["context_key"], "files": [request_file(file)]}
    assert client.post(f"{url}/import", headers=headers, json=body).status_code == 422
    body["files"][0]["revision"] = "A"
    response = client.post(f"{url}/import", headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1
    assert (
        client.post(f"{url}/import", headers=headers, json=body).json()["skipped"] == 1
    )
    detail = client.get(f"{API}/{part.id}", headers=headers).json()
    records = detail["study"]["payload"]["catalog"]["entries"][0]["series"][0][
        "records"
    ]
    assert records["c1"]["01"]["lower"] == 3.9
    assert records["c1"]["01"]["upper"] == 4
    assert records["c1"]["01"]["status"] == "inside"
    characteristic = detail["characteristics"][0]
    assert characteristic["revision"] == "A"
    assert (
        db.get(FeatureCharacteristicLink, (feature.id, uuid.UUID(characteristic["id"])))
        is None
    )
    history = client.get(f"{url}/history", headers=headers).json()
    old_id = history[0]["id"]
    first.write_bytes(csv_text("3.970"))
    assert client.post(f"{url}/import", headers=headers, json=body).status_code == 409
    updated = client.post(
        f"{url}/preview",
        headers=headers,
        json={
            "files": [
                {"path": file["path"], "revision": "A", "sample": "01", "cavity": "c1"}
            ]
        },
    ).json()
    assert updated["files"][0]["status"] == "replacement"
    body = {
        "context_key": updated["context_key"],
        "files": [request_file(updated["files"][0])],
    }
    assert client.post(f"{url}/import", headers=headers, json=body).status_code == 409
    body["files"][0]["replace_existing"] = True
    assert (
        client.post(f"{url}/import", headers=headers, json=body).json()["imported"] == 1
    )
    historical = client.get(
        f"{API}/{part.id}", headers=headers, params={"snapshot_id": old_id}
    ).json()
    assert (
        historical["study"]["payload"]["catalog"]["entries"][0]["series"][0]["records"][
            "c1"
        ]["01"]["value"]
        == 3.95
    )
    write(folder, "rev.A/intern.03/c1/new.csv", csv_text("3.980"))
    write(folder, "rev.B/intern.01/c1/new.csv", csv_text("3.990"))
    preview = client.post(f"{url}/preview", headers=headers, json={}).json()
    assert (
        next(f for f in preview["files"] if f["path"] == file["path"])["status"]
        == "imported"
    )
    files = [f for f in preview["files"] if f["status"] != "imported"]
    assert {f["status"] for f in files} == {"new_sample", "new_revision"}
    response = client.post(
        f"{url}/import",
        headers=headers,
        json={
            "context_key": preview["context_key"],
            "files": [request_file(f) for f in files],
        },
    )
    assert response.status_code == 200, response.text
    a = client.get(f"{API}/{part.id}", headers=headers, params={"revision": "A"}).json()
    b = client.get(f"{API}/{part.id}", headers=headers, params={"revision": "B"}).json()
    assert a["measurement_revisions"] == ["A", "B"]
    assert a["study"]["payload"]["samples"] == ["01", "03"]
    assert b["study"]["payload"]["samples"] == ["01"]
    assert len(a["characteristics"]) == 2
    # The same registered piece can be linked to a second feature, without an import.
    second = create_random_feature(db)
    db.add(FeaturePartLink(feature_id=second.id, part_id=part.id))
    db.commit()
    assert len(client.get(f"{url}/history", headers=headers).json()) == 4
    assert all(
        not f["characteristics"]
        for f in client.get(f"{API}/{part.id}", headers=headers).json()["features"]
    )


def test_import_validates_sources_and_is_atomic(
    client: TestClient, db: Session, normal_user_token_headers, piece
):
    part, _, folder = piece
    headers = normal_user_token_headers
    url = f"{API}/{part.id}/measurements"
    write(folder, "rev.A/intern.01/c2/a.csv")
    write(folder, "rev.A/intern.01/c2/copy.csv")
    write(folder, "bad.csv", b"id;value\n1;42\n")
    preview = client.post(f"{url}/preview", headers=headers, json={}).json()
    assert (
        next(f for f in preview["files"] if f["path"] == "bad.csv")["status"]
        == "unsupported"
    )
    usable = [request_file(f) for f in preview["files"] if f["status"] != "unsupported"]
    response = client.post(
        f"{url}/import",
        headers=headers,
        json={"context_key": preview["context_key"], "files": usable},
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1 and response.json()["skipped"] == 1
    assert (
        len(
            db.exec(
                select(MeasurementImport).where(MeasurementImport.part_id == part.id)
            ).all()
        )
        == 1
    )
    # Two different full exports of one sampling/cavity are not silently combined.
    write(folder, "rev.A/intern.03/c2/a.csv")
    write(folder, "rev.A/intern.03/c2/b.csv", csv_text("3.999"))
    preview = client.post(f"{url}/preview", headers=headers, json={}).json()
    usable = [request_file(f) for f in preview["files"] if f["sample"] == "03"]
    response = client.post(
        f"{url}/import",
        headers=headers,
        json={"context_key": preview["context_key"], "files": usable},
    )
    assert response.status_code == 409
    assert (
        len(
            db.exec(
                select(MeasurementImport).where(MeasurementImport.part_id == part.id)
            ).all()
        )
        == 1
    )
    escape = client.post(
        f"{url}/preview", headers=headers, json={"files": [{"path": "../outside.csv"}]}
    ).json()
    assert escape["files"][0]["status"] == "unsupported"
    old_key = preview["context_key"]
    part.folder_path = "another-folder"
    db.add(part)
    db.commit()
    assert (
        client.post(
            f"{url}/import",
            headers=headers,
            json={"context_key": old_key, "files": usable},
        ).status_code
        == 409
    )


def test_same_format_handles_another_piece_without_pilot_mappings(
    client: TestClient, normal_user_token_headers, piece
):
    part, _, folder = piece
    write(folder, "rev.C/intern.08/c99/data.csv", csv_text("3,950", "N161"))
    url = f"{API}/{part.id}/measurements"
    preview = client.post(
        f"{url}/preview", headers=normal_user_token_headers, json={}
    ).json()
    response = client.post(
        f"{url}/import",
        headers=normal_user_token_headers,
        json={
            "context_key": preview["context_key"],
            "files": [request_file(preview["files"][0])],
        },
    )
    assert response.status_code == 200, response.text
    study = client.get(f"{API}/{part.id}", headers=normal_user_token_headers).json()[
        "study"
    ]["payload"]
    series = study["catalog"]["entries"][0]["series"][0]
    assert series["element"] == "CMM 11" and series["evaluation"] == "Diámetro · 1"
    assert study["cases"] == {} and study["corrections"] == {}
    assert study["cavities"] == ["c99"]


def test_existing_pilot_is_preserved_before_first_csv_replacement(
    client: TestClient, db: Session, normal_user_token_headers, piece
):
    part, _, folder = piece
    headers = normal_user_token_headers
    url = f"{API}/{part.id}/measurements"
    rows, _ = parse(csv_text())
    payload = {
        "measurement_revision": "A",
        "samples": ["01"],
        "cavities": ["c1"],
        "catalog": {
            "row_count": 1,
            "entries": [
                {
                    "id": "N170",
                    "numbers": ["N170"],
                    "kind": "dimension",
                    "title": "N170 DIAMETRO",
                    "series": [
                        {
                            "id": rows[0]["series_id"],
                            "label": "Diámetro",
                            "block": "N170 DIAMETRO",
                            "idx": 1,
                            "unit": "mm",
                            "records": {
                                "c1": {"01": {"value": 3.8, "lower": 3.9, "upper": 4}}
                            },
                        }
                    ],
                }
            ],
        },
    }
    job = EvidenceJob(
        id=job_id("study", part.id),
        kind="study",
        part_id=part.id,
        cache_key="test",
        state="ready",
        payload=payload,
    )
    db.add(job)
    db.commit()
    write(folder, "rev.A/intern.01/c1/new.csv")
    preview = client.post(f"{url}/preview", headers=headers, json={}).json()
    assert preview["files"][0]["status"] == "replacement"
    response = client.post(
        f"{url}/import",
        headers=headers,
        json={
            "context_key": preview["context_key"],
            "files": [request_file(preview["files"][0], replace_existing=True)],
        },
    )
    assert response.status_code == 200, response.text
    history = client.get(f"{url}/history", headers=headers).json()
    baseline = next(row for row in history if row["baseline"])
    assert len(history) == 2
    # Even a later legacy worker publication cannot overwrite either saved dataset.
    job.payload = {**payload, "catalog": {"entries": [], "row_count": 0}}
    db.add(job)
    db.commit()

    def value(params):
        response = client.get(f"{API}/{part.id}", headers=headers, params=params)
        assert response.status_code == 200, response.text
        return response.json()["study"]["payload"]["catalog"]["entries"][0]["series"][
            0
        ]["records"]["c1"]["01"]["value"]

    assert value({"snapshot_id": baseline["id"]}) == 3.8
    assert value({}) == 3.95
    other = create_random_part(db)
    assert (
        client.get(
            f"{API}/{other.id}", headers=headers, params={"snapshot_id": baseline["id"]}
        ).status_code
        == 404
    )


def test_cmm_reader_keeps_elements_separate_and_reports_unidentified_rows():
    first, _ = parse(csv_text(code="N161"))
    changed, _ = parse(csv_text(code="N161").replace(b"11;", b"12;"))
    assert first[0]["series_id"] != changed[0]["series_id"]
    assert first[1]["element"] == "CMM 11"
    rows, issues = parse(csv_text() + b"Coordinates\n21;X;;4;0;-0.1;3.95;-0.05\n")
    assert len(rows) == 2 and "1 filas" in issues[0]
    for invalid in [b"nan", b"infinito", b"3.9.5"]:
        with pytest.raises(ValueError, match="Número"):
            parse(csv_text().replace(b"3.950", invalid))
    with pytest.raises(ValueError, match="Tolerancias invertidas"):
        parse(csv_text().replace(b";-0.100;", b";0.100;"))
    with pytest.raises(ValueError, match="comparativa"):
        parse(
            b"N178;;;;;;c13;c14;c15;c16\n11;Planitud;;0;0.1;0;0.061;0.073;0.079;0.069\n"
        )
    with pytest.raises(ValueError, match="comparativa"):
        parse(
            b"***********;;;;;c13;c14;c15;c16\nN178;;;;;;;;\n11;Planitud;;0;;0.038;0.037;0.036;0.038\n"
        )
