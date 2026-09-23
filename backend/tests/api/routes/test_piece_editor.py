import uuid

import pytest
from sqlmodel import select

from app.core.config import settings
from app.evidence import job_id
from app.knowledge_models import EvidenceJob, PartDocument
from app.models import Part, StoredFile
from tests.api.routes.test_part_setup import API, csv, source, write
from tests.utils.feature import create_random_feature

# Reuse the isolated folder fixture; discovery must remain a read-only operation.
__all__ = ["source"]


def create(client, headers, folder, **extra):
    response = client.post(
        f"{API}/register",
        headers=headers,
        json={
            "folder_path": folder,
            "name": "Housing",
            "code": str(uuid.uuid4())[:12],
            "customer": "Company",
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_discovery_and_registration_never_overwrite_an_existing_piece(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    write(root, "part.step")
    headers = normal_user_token_headers
    proposal = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    ).json()
    assert proposal["name"] == folder
    assert proposal["code"] == folder.split()[0]
    assert proposal["existing_part"] is None
    assert db.exec(select(Part).where(Part.folder_path == folder)).first() is None
    part = create(client, headers, folder, description="Description")
    proposal = client.post(
        f"{API}/discover", headers=headers, json={"folder_path": folder}
    ).json()
    assert proposal["existing_part"]["id"] == part["id"]
    response = client.post(
        f"{API}/register",
        headers=headers,
        json={
            "folder_path": folder,
            "name": "Must not overwrite",
            "code": "another",
            "customer": "other",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["part_id"] == part["id"]
    assert (
        client.get(f"{API}/{part['id']}/detail", headers=headers).json()["part"][
            "description"
        ]
        == "Description"
    )


def test_named_multiple_files_primary_switch_and_removal_keep_sources(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    for path in ("one.step", "two.step", "drawing.pdf", "notes.txt", "sub/report.xlsx"):
        write(root, path)
    headers = normal_user_token_headers
    feature = create_random_feature(db)
    part = create(
        client,
        headers,
        folder,
        files=[
            {
                "path": f"{folder}/one.step",
                "kind": "part",
                "name": "First",
                "primary": True,
            },
            {"path": f"{folder}/two.step", "kind": "part", "name": "Second"},
            {"path": f"{folder}/notes.txt", "kind": "document", "name": "Notes"},
            {"path": f"{folder}/drawing.pdf", "kind": "drawing", "name": "Drawing"},
        ],
        feature_ids=[str(feature.id)],
    )
    url = f"{API}/{part['id']}"
    detail = client.get(f"{url}/detail", headers=headers).json()
    assert len(detail["files"]) == 4
    assert detail["features"][0]["id"] == str(feature.id)
    assert detail["part"]["cad"]["filename"] == "one.step"
    original = detail["files"][0]["file"]["id"]
    choices = [
        {
            "file_id": item["file"]["id"],
            "name": item["name"],
            "kind": item["kind"],
            "primary": item["name"] == "Second",
        }
        for item in detail["files"]
        if item["name"] != "Drawing"
    ]
    choices.append(
        {"path": f"{folder}/sub/report.xlsx", "kind": "document", "name": "Report"}
    )
    response = client.put(
        url,
        headers=headers,
        json={
            "name": "Edited",
            "description": "Optional",
            "customer": "Client",
            "files": choices,
        },
    )
    assert response.status_code == 200, response.text
    updated = client.get(f"{url}/detail", headers=headers).json()
    assert updated["part"]["cad"]["filename"] == "two.step"
    assert updated["part"]["customer"] == "Client"
    assert updated["files"][-1]["name"] == "Report"
    evidence = client.get(
        f"{settings.API_V1_STR}/evidence/parts/{part['id']}", headers=headers
    ).json()
    assert evidence["drawing_file_id"] is None
    assert client.put(url, headers=headers, json={"files": []}).status_code == 200
    assert client.get(f"{url}/detail", headers=headers).json()["files"] == []
    assert client.get(f"{url}/detail", headers=headers).json()["part"]["cad"] is None
    assert db.get(StoredFile, uuid.UUID(original)) is not None
    assert (
        db.get(PartDocument, (uuid.UUID(part["id"]), uuid.UUID(original))) is not None
    )
    assert (root / "one.step").read_bytes() == b"reference"


@pytest.mark.parametrize(
    "invalid", ["outside", "duplicate", "primary", "extension", "missing", "foreign"]
)
def test_invalid_files_rollback_header_and_registration(
    client, db, normal_user_token_headers, source, invalid
):
    folder, root = source
    write(root, "part.step")
    write(root.parent, "Other/file.step")
    headers = normal_user_token_headers
    choice = {"path": f"{folder}/part.step", "kind": "part", "name": "CAD"}
    part = create(client, headers, folder, files=[choice])
    url = f"{API}/{part['id']}"
    before = client.get(f"{url}/detail", headers=headers).json()
    choices = [choice.copy()]
    if invalid == "outside":
        choices[0]["path"] = "Other/file.step"
    elif invalid == "duplicate":
        choices.append(choice.copy())
    elif invalid == "primary":
        write(root, "second.step")
        choices[0]["primary"] = True
        choices.append({**choice, "path": f"{folder}/second.step", "primary": True})
    elif invalid == "extension":
        choices[0]["kind"] = "drawing"
    elif invalid == "missing":
        choices[0]["path"] = f"{folder}/missing.step"
    else:
        choices = [{"file_id": str(uuid.uuid4()), "kind": "part", "name": "Foreign"}]
    response = client.put(
        url, headers=headers, json={"name": "Must not save", "files": choices}
    )
    assert response.status_code in {404, 409, 422}, response.text
    assert client.get(f"{url}/detail", headers=headers).json() == before
    empty = f"{folder}-empty"
    (root.parent / empty).mkdir()
    response = client.post(
        f"{API}/register",
        headers=headers,
        json={
            "folder_path": empty,
            "code": str(uuid.uuid4()),
            "name": "Invalid",
            "customer": "Client",
            "files": choices,
        },
    )
    assert response.status_code in {404, 409, 422}, response.text
    assert db.exec(select(Part).where(Part.folder_path == empty)).first() is None


def test_read_report_lists_only_used_sources_and_polling_does_not_reimport(
    client, normal_user_token_headers, source
):
    folder, root = source
    measurement = "rev.A/intern.01/c1/measurement.csv"
    write(root, measurement, csv())
    write(root, "unrelated.txt", b"Not a measurement")
    headers = normal_user_token_headers
    part = create(client, headers, folder)
    url = f"{API}/{part['id']}"
    assert client.get(f"{url}/read-data", headers=headers).json() is None
    assert (
        client.get(f"{url}/detail", headers=headers).json()["part"][
            "characteristic_count"
        ]
        == 0
    )
    result = client.post(f"{url}/read-data", headers=headers)
    assert result.status_code == 200, result.text
    report = result.json()
    assert report["state"] == "ready"
    assert report["imported"] == 1
    assert report["files"] == [
        {"path": measurement, "group": "measurements", "status": "imported"}
    ]
    write(root, measurement, csv("9.960"))
    assert client.get(f"{url}/read-data", headers=headers).json() == report
    reread = client.post(f"{url}/read-data", headers=headers).json()
    assert reread["imported"] == 1
    unchanged = client.post(f"{url}/read-data", headers=headers).json()
    assert unchanged["skipped"] == 1
    assert unchanged["files"][0]["status"] == "unchanged"


def test_corrections_report_tracks_job_without_rereading(
    client, db, normal_user_token_headers, source
):
    folder, _ = source
    headers = normal_user_token_headers
    public = create(client, headers, folder)
    part = db.get(Part, uuid.UUID(public["id"]))
    part.last_read = {
        "state": "processing",
        "measurements": {"context_key": "test", "files": []},
        "corrections_key": "test",
        "files": [
            {"path": "corrections.pptx", "group": "corrections", "status": "queued"}
        ],
    }
    job = EvidenceJob(
        id=job_id("study", part.id),
        kind="study",
        part_id=part.id,
        cache_key="test",
        state="ready",
        payload={"source_files": ["corrections.pptx", "measure.csv"]},
    )
    db.add(part)
    db.add(job)
    db.commit()
    url = f"{API}/{part.id}/read-data"
    result = client.get(url, headers=headers).json()
    assert result["state"] == "ready"
    assert [item["status"] for item in result["files"]] == ["used", "used"]
    job.state, job.message = "error", "Could not read corrections"
    db.add(job)
    db.commit()
    result = client.get(url, headers=headers).json()
    assert result["state"] == "partial"
    assert job.message in result["notices"]


def test_folder_change_checks_files_and_resets_read_report(
    client, normal_user_token_headers, source
):
    folder, root = source
    write(root, "part.step")
    next_folder = f"{folder}-next"
    write(root.parent, f"{next_folder}/next.step")
    headers = normal_user_token_headers
    part = create(
        client,
        headers,
        folder,
        files=[{"path": f"{folder}/part.step", "name": "CAD", "kind": "part"}],
    )
    url = f"{API}/{part['id']}"
    client.post(f"{url}/read-data", headers=headers)
    item = client.get(f"{url}/detail", headers=headers).json()["files"][0]
    bad = client.put(
        url,
        headers=headers,
        json={
            "folder_path": next_folder,
            "files": [
                {"file_id": item["file"]["id"], "name": "Old CAD", "kind": "part"}
            ],
        },
    )
    assert bad.status_code == 422
    good = client.put(
        url,
        headers=headers,
        json={
            "folder_path": next_folder,
            "name": "Kept name",
            "files": [
                {"path": f"{next_folder}/next.step", "name": "New CAD", "kind": "part"}
            ],
        },
    )
    assert good.status_code == 200, good.text
    assert client.get(f"{url}/read-data", headers=headers).json() is None


def test_legacy_reference_update_keeps_managed_file_list_consistent(
    client, normal_user_token_headers, source
):
    folder, root = source
    for filename in ("first.step", "second.step", "replacement.step"):
        write(root, filename)
    headers = normal_user_token_headers
    part = create(
        client,
        headers,
        folder,
        files=[
            {
                "path": f"{folder}/first.step",
                "kind": "part",
                "name": "Main CAD",
                "primary": True,
            },
            {"path": f"{folder}/second.step", "kind": "part", "name": "Additional CAD"},
        ],
    )
    url = f"{API}/{part['id']}"
    result = client.put(
        url,
        headers=headers,
        json={"references": [{"kind": "part", "path": f"{folder}/replacement.step"}]},
    )
    assert result.status_code == 200, result.text
    detail = client.get(f"{url}/detail", headers=headers).json()
    assert {item["file"]["filename"] for item in detail["files"]} == {
        "second.step",
        "replacement.step",
    }
    assert detail["part"]["cad"]["filename"] == "replacement.step"


def test_read_error_is_persisted_and_does_not_read_the_assets_root(
    client, db, normal_user_token_headers, monkeypatch
):
    from app import part_reading

    part = Part(code=str(uuid.uuid4()), name="No folder")
    db.add(part)
    db.commit()

    def forbidden(*_args):
        raise AssertionError("An unlinked piece must not scan the asset root")

    monkeypatch.setattr(part_reading, "refresh", forbidden)
    url = f"{API}/{part.id}/read-data"
    response = client.post(url, headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["state"] == "error"
    assert response.json()["files"] == []
    assert client.get(url, headers=normal_user_token_headers).json() == response.json()
