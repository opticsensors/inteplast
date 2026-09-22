import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Part
from tests.utils.feature import create_random_feature

API = f"{settings.API_V1_STR}/parts"


def write(root: Path, relative: str, content: bytes = b"reference") -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def csv(value: str = "9.950") -> bytes:
    return f"N12 DIAMETRO\n11;Diameter;;10;0.1;-0.1;{value};-0.05;;\n".encode()


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    folder = f"{uuid.uuid4().int % 100000000} Housing"
    root = tmp_path / folder
    root.mkdir()
    return folder, root


def register_piece(client, headers, folder):
    discovery = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    )
    assert discovery.status_code == 200, discovery.text
    data = discovery.json()
    response = client.post(
        f"{API}/setup",
        headers=headers,
        json={
            "folder_path": folder,
            "name": data["name"],
            "references": data["references"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["part"], data


def test_registration_proposes_references_and_populates_feature_only_when_linked(
    client: TestClient,
    db: Session,
    normal_user_token_headers,
    source,
):
    folder, root = source
    originals = [
        "1-2D y 3D Pieza/part.step",
        "1-2D y 3D Pieza/DRW.pdf",
        "3- 3D Molde/tool.step",
        "8- STL peça real/scan.stl",
    ]
    for file in originals:
        write(root, file)
    write(root, "4- Metrologia/measurement.pdf")
    write(root, "4- Metrologia/points.igs")
    headers = normal_user_token_headers
    assert (
        client.post(f"{API}/discover", json={"folder_path": folder}).status_code == 401
    )
    discovery = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    ).json()
    assert {r["kind"] for r in discovery["references"] if r["path"]} == {
        "part",
        "mold",
        "scan",
        "drawing",
    }
    assert db.exec(select(Part).where(Part.folder_path == folder)).first() is None
    piece, _ = register_piece(client, headers, folder)
    assert piece["name"] == folder
    again, _ = register_piece(client, headers, folder)
    assert again["id"] == piece["id"]
    filters = client.get(
        f"{settings.API_V1_STR}/evidence/metrology/filters", headers=headers
    ).json()
    assert piece["id"] in {p["id"] for p in filters["parts"]}
    feature = create_random_feature(db)
    endpoint = f"{settings.API_V1_STR}/features/{feature.id}/parts/{piece['id']}"
    linked = client.post(endpoint, headers=headers).json()
    assert len(linked["assets"]) == 4
    assert {a["kind"] for a in linked["assets"]} == {"part", "mold", "scan", "drawing"}
    assert len(client.post(endpoint, headers=headers).json()["assets"]) == 4
    evidence = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{piece['id']}", headers=headers
    ).json()
    assert evidence["drawing_file_id"] in {d["id"] for d in evidence["documents"]}
    assert all((root / file).read_bytes() == b"reference" for file in originals)


def test_refresh_imports_unambiguous_exports_without_a_feature_and_keeps_history(
    client: TestClient,
    normal_user_token_headers,
    source,
):
    folder, root = source
    original = write(root, "rev.A/intern.01/c1/measurement.csv", csv())
    write(root, "intern.02/c2/unknown.csv", csv())
    write(root, "5- Retoques de molde/plan.pptx")
    headers = normal_user_token_headers
    piece, _ = register_piece(client, headers, folder)
    url = f"{API}/{piece['id']}/refresh"
    first = client.post(url, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["imported"] == 2
    assert first.json()["corrections_state"] == "needs_review"
    assert first.json()["measurements"]["files"] == []
    again = client.post(url, headers=headers).json()
    assert again["imported"] == 0 and again["skipped"] == 2
    original.write_bytes(csv("10.200"))
    changed = client.post(url, headers=headers).json()
    assert changed["imported"] == 1
    evidence = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{piece['id']}", headers=headers
    ).json()
    assert (
        evidence["study"]["payload"]["catalog"]["entries"][0]["series"][0]["records"][
            "c1"
        ]["01"]["value"]
        == 10.2
    )
    history = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{piece['id']}/measurements/history",
        headers=headers,
    )
    assert history.status_code == 200
    old = next(b for b in history.json() if b["sample"] == "01" and not b["active"])
    previous = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{piece['id']}",
        headers=headers,
        params={"snapshot_id": old["id"]},
    ).json()
    assert (
        previous["study"]["payload"]["catalog"]["entries"][0]["series"][0]["records"][
            "c1"
        ]["01"]["value"]
        == 9.95
    )
    # Reverting to previously seen bytes is a new current version, not an ignored import.
    original.write_bytes(csv())
    assert client.post(url, headers=headers).json()["imported"] == 1
    assert client.post(url, headers=headers).json()["imported"] == 0


def test_refresh_preserves_conflicting_exports_as_separate_series(
    client, normal_user_token_headers, source
):
    folder, root = source
    write(root, "rev.A/intern.01/c1/one.csv", csv())
    write(root, "rev.A/intern.01/c1/two.csv", csv("10.200"))
    piece, _ = register_piece(client, normal_user_token_headers, folder)
    result = client.post(
        f"{API}/{piece['id']}/refresh", headers=normal_user_token_headers
    ).json()
    assert result["imported"] == 1
    evidence = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{piece['id']}",
        headers=normal_user_token_headers,
    ).json()
    series = evidence["study"]["payload"]["catalog"]["entries"][0]["series"]
    assert {s["records"]["c1"]["01"]["value"] for s in series} == {9.95, 10.2}
    assert len({s["id"] for s in series}) == 2


def test_setup_rejects_other_piece_and_changed_original_before_registration(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    target = write(root, "part.step")
    other = root.parent / "Other"
    write(other, "part.step")
    headers = normal_user_token_headers
    discovery = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    ).json()
    body = {
        "folder_path": folder,
        "name": folder,
        "references": discovery["references"],
    }
    target.write_bytes(b"modified reference")
    assert client.post(f"{API}/setup", headers=headers, json=body).status_code == 409
    body["references"] = [{"kind": "part", "path": "Other/part.step"}]
    assert client.post(f"{API}/setup", headers=headers, json=body).status_code == 422
    assert db.exec(select(Part).where(Part.folder_path == folder)).first() is None
    assert (
        client.post(
            f"{API}/discover", headers=headers, json={"folder_path": "../outside"}
        ).status_code
        == 400
    )


def test_empty_piece_and_user_reference_choice_survive_discovery(
    client, normal_user_token_headers, source
):
    folder, root = source
    headers = normal_user_token_headers
    piece, _ = register_piece(client, headers, folder)
    empty = client.post(f"{API}/{piece['id']}/refresh", headers=headers).json()
    assert empty["imported"] == 0 and not empty["measurements"]["files"]
    write(root, "part-a.step")
    write(root, "part-b.step")
    choice = f"{folder}/part-b.step"
    assert (
        client.post(
            f"{API}/setup",
            headers=headers,
            json={
                "folder_path": folder,
                "name": "Custom",
                "references": [{"kind": "part", "path": choice}],
            },
        ).status_code
        == 200
    )
    discovery = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    ).json()
    assert discovery["name"] == "Custom"
    assert (
        next(r for r in discovery["references"] if r["kind"] == "part")["path"]
        == choice
    )


def test_explicit_study_refresh_advances_current_data_but_preserves_historical_snapshot(
    db, source
):
    from app import measurement_imports
    from app.evidence import job_id
    from app.knowledge_models import EvidenceJob
    from app.measurement_models import MeasurementImport

    folder, _ = source
    part = Part(code=folder.split()[0], name=folder, folder_path=folder)
    db.add(part)
    db.flush()
    old = {
        "measurement_revision": "06",
        "catalog": {"entries": []},
        "cases": {"N12": {"title": "Previous"}},
    }
    db.add(
        EvidenceJob(
            id=job_id("study", part.id),
            kind="study",
            part_id=part.id,
            cache_key="old",
            state="ready",
            payload=old,
        )
    )
    db.commit()
    measurement_imports.preserve_legacy(db, part, None)
    db.commit()
    previous = db.exec(
        select(MeasurementImport).where(MeasurementImport.part_id == part.id)
    ).first()
    current = {**old, "cases": {"N12": {"title": "Updated"}}}
    measurement_imports.save_refreshed_study(db, part, current, "new", None)
    db.commit()
    assert (
        measurement_imports.study(db, part, None)[0].payload["cases"]["N12"]["title"]
        == "Updated"
    )
    assert (
        measurement_imports.study(db, part, "06", previous.id)[0].payload["cases"][
            "N12"
        ]["title"]
        == "Previous"
    )
