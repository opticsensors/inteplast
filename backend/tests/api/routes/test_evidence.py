import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.evidence import drawing_key, job_id, publish_study, queue
from app.knowledge_models import (
    DrawingLocation,
    EvidenceJob,
    PartDocument,
    PendingCharacteristic,
)
from app.models import StoredFile
from tests.utils.feature import create_random_feature, create_random_part

API = f"{settings.API_V1_STR}/evidence"


def test_characteristics_are_scoped_and_searchable(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    feature = create_random_feature(db)
    parts = [create_random_part(db), create_random_part(db)]
    headers = normal_user_token_headers
    ids = []
    for part, revision in [(parts[0], "06"), (parts[1], "06"), (parts[0], "07")]:
        response = client.put(
            f"{API}/features/{feature.id}/parts/{part.id}/characteristics",
            headers=headers,
            json={"code": "N87654", "revision": revision, "role": "reference"},
        )
        assert response.status_code == 200, response.text
        ids.append(response.json()["id"])
    assert len(set(ids)) == 3
    response = client.get(
        f"{API}/features/{feature.id}/parts/{parts[0].id}", headers=headers
    )
    assert len(response.json()["characteristics"]) == 2
    assert {c["revision"] for c in response.json()["characteristics"]} == {"06", "07"}
    response = client.get(
        f"{settings.API_V1_STR}/features/", headers=headers, params={"q": "N87654"}
    )
    assert str(feature.id) in [f["id"] for f in response.json()["data"]]
    client.delete(
        f"{settings.API_V1_STR}/features/{feature.id}/parts/{parts[0].id}",
        headers=headers,
    )
    assert (
        client.get(
            f"{API}/features/{feature.id}/parts/{parts[0].id}", headers=headers
        ).json()["characteristics"]
        == []
    )
    assert (
        len(
            client.get(
                f"{API}/features/{feature.id}/parts/{parts[1].id}", headers=headers
            ).json()["characteristics"]
        )
        == 1
    )


def test_pending_number_only_moves_on_assignment(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    feature, part = create_random_feature(db), create_random_part(db)
    db.add(PendingCharacteristic(feature_id=feature.id, code="N0"))
    db.commit()
    url = f"{API}/features/{feature.id}/parts/{part.id}"
    assert client.get(url, headers=normal_user_token_headers).json()["pending"] == [
        "N0"
    ]
    response = client.put(
        f"{url}/characteristics",
        headers=normal_user_token_headers,
        json={"code": "N0", "revision": "sin confirmar"},
    )
    assert response.status_code == 200
    assert client.get(url, headers=normal_user_token_headers).json()["pending"] == []


@pytest.fixture
def drawing(db: Session) -> StoredFile:
    document = StoredFile(
        filename="drawing.pdf", content_type="application/pdf", size=4
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    Path(settings.uploads_path / str(document.id)).write_bytes(b"%PDF")
    db.add(
        EvidenceJob(
            id=job_id("drawing", document.id),
            file_id=document.id,
            kind="drawing",
            cache_key=drawing_key(document),
            state="ready",
            payload={
                "signature": {"sha256": "a" * 64},
                "balloons": [
                    {
                        "id": "p1-b123",
                        "page": 1,
                        "box": [0.1, 0.2, 0.15, 0.25],
                        "candidates": [{"label": "N170"}],
                    }
                ],
                "words": [],
                "pages": [],
            },
        )
    )
    db.commit()
    return document


def test_review_is_shared_and_bound_to_bytes(
    client: TestClient,
    db: Session,
    drawing: StoredFile,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    url = f"{API}/drawings/{drawing.id}"
    body = {"candidate_id": "p1-b123", "label": "N170.1", "sha256": "a" * 64}
    response = client.put(f"{url}/review", headers=normal_user_token_headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["box"] == [0.1, 0.2, 0.15, 0.25]
    review = client.get(url, headers=superuser_token_headers).json()["reviews"][0]
    assert review["label"] == "N170.1" and review["reviewed_by"]
    assert (
        client.put(
            f"{url}/review",
            headers=normal_user_token_headers,
            json={**body, "sha256": "b" * 64},
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"{url}/review",
            headers=normal_user_token_headers,
            json={**body, "candidate_id": "invented"},
        ).status_code
        == 422
    )
    drawing.version = uuid.uuid4()
    db.add(drawing)
    db.commit()
    assert client.get(url, headers=normal_user_token_headers).json()["state"] == "empty"
    assert client.get(url, headers=normal_user_token_headers).json()["reviews"] == []
    assert (
        client.put(
            f"{url}/review", headers=normal_user_token_headers, json=body
        ).status_code
        == 409
    )
    assert (
        db.exec(
            select(DrawingLocation).where(DrawingLocation.file_id == drawing.id)
        ).first()
        is not None
    )


def test_authenticated_index_and_idempotent_queue(
    client: TestClient,
    db: Session,
    drawing: StoredFile,
    normal_user_token_headers: dict[str, str],
) -> None:
    url = f"{API}/drawings/{drawing.id}"
    assert client.get(url).status_code == 401
    assert client.post(f"{url}/index").status_code == 401
    assert (
        client.post(f"{url}/index", headers=normal_user_token_headers).json()["state"]
        == "ready"
    )
    job = queue(db, "drawing", drawing.id, "b" * 64)
    assert job.state == "queued"
    assert queue(db, "drawing", drawing.id, "b" * 64).id == job.id


def test_other_pieces_do_not_use_pilot_adapter(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    part = create_random_part(db)
    response = client.get(f"{API}/parts/{part.id}", headers=normal_user_token_headers)
    assert response.status_code == 200 and not response.json()["import_available"]
    assert (
        client.post(
            f"{API}/parts/{part.id}/import", headers=normal_user_token_headers
        ).status_code
        == 422
    )


def test_evidence_documents_cannot_be_deleted(
    client: TestClient,
    db: Session,
    drawing: StoredFile,
    superuser_token_headers: dict[str, str],
) -> None:
    part = create_random_part(db)
    db.add(PartDocument(part_id=part.id, file_id=drawing.id))
    db.commit()
    assert (
        client.delete(
            f"{settings.API_V1_STR}/files/{drawing.id}", headers=superuser_token_headers
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
        ).status_code
        == 409
    )


def test_numbers_are_not_global_tags(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/features/",
        headers=normal_user_token_headers,
        json={"name": "test", "tags": ["N170"]},
    )
    assert response.status_code == 422


def test_import_preserves_source_identity_without_local_urls(
    db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    source = root / "pilot"
    source.mkdir(parents=True)
    (source / "values.csv").write_text("original", encoding="utf-8")
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(root))
    part = create_random_part(db)
    part.folder_path = "pilot"
    db.add(part)
    db.commit()
    output = tmp_path / "output"
    (output / "assets").mkdir(parents=True)
    (output / "assets" / "action.png").write_bytes(b"derived image")
    data = {
        "catalog": {"entries": [{"numbers": ["N170"], "title": "Diameter"}]},
        "source": {
            "path": "values.csv",
            "url": "file:///private/path",
            "locator": "row 4",
        },
        "image": "assets/action.png",
        "value": 3.974,
    }
    result = publish_study(db, part, data, output)
    db.commit()
    assert result["value"] == 3.974
    assert result["source"]["locator"] == "row 4"
    assert "url" not in result["source"]
    document = db.get(StoredFile, uuid.UUID(result["source"]["file_id"]))
    assert document and document.source_path == "pilot/values.csv"
    assert (settings.uploads_path / result["image"]).read_bytes() == b"derived image"
    again = publish_study(db, part, data, output)
    db.commit()
    assert result == again
