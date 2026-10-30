import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.evidence import attach_reviews
from app.core.config import settings
from app.evidence import drawing_key, job_id, publish_study, queue
from app.knowledge_models import (
    DrawingLocation,
    EvidenceJob,
    LocationPublic,
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


def test_new_reader_invalidates_the_index(
    client: TestClient,
    drawing: StoredFile,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{API}/drawings/{drawing.id}"
    assert client.get(url, headers=normal_user_token_headers).json()["state"] == "ready"
    monkeypatch.setattr("app.evidence.reader_id", lambda: "drawing-v99:otro")
    response = client.get(url, headers=normal_user_token_headers).json()
    assert response["state"] == "empty"
    assert "lector" in response["message"]


def test_review_follows_its_balloon_when_the_candidate_id_changes(
    client: TestClient,
    db: Session,
    drawing: StoredFile,
    normal_user_token_headers: dict[str, str],
) -> None:
    url = f"{API}/drawings/{drawing.id}"
    body = {"candidate_id": "p1-b123", "label": "N170", "sha256": "a" * 64}
    assert (
        client.put(
            f"{url}/review", headers=normal_user_token_headers, json=body
        ).status_code
        == 200
    )
    job = db.get(EvidenceJob, job_id("drawing", drawing.id))
    assert job is not None
    # Same bytes, improved detector: the balloon moved by a fraction of its size and got a new ID.
    job.payload = {
        **job.payload,
        "balloons": [
            {"id": "p1-bnuevo", "page": 1, "box": [0.101, 0.201, 0.151, 0.251]},
            {"id": "p1-blejos", "page": 1, "box": [0.6, 0.6, 0.65, 0.65]},
        ],
    }
    db.add(job)
    db.commit()
    reviews = client.get(url, headers=normal_user_token_headers).json()["reviews"]
    assert [r["candidate_id"] for r in reviews] == ["p1-bnuevo"]
    assert reviews[0]["box"] == [0.1, 0.2, 0.15, 0.25]  # the stored review is unchanged

    # Reviewing again creates the current-ID review, which must prevail over its predecessor.
    body = {**body, "candidate_id": "p1-bnuevo", "label": "N171"}
    response = client.put(f"{url}/review", headers=normal_user_token_headers, json=body)
    assert response.status_code == 200
    current_id = response.json()["id"]
    response = client.put(
        f"{url}/review",
        headers=normal_user_token_headers,
        json={**body, "label": "N172"},
    )
    assert response.status_code == 200 and response.json()["id"] == current_id
    reviews = client.get(url, headers=normal_user_token_headers).json()["reviews"]
    assert [(r["candidate_id"], r["label"]) for r in reviews] == [("p1-bnuevo", "N172")]
    stored = db.exec(
        select(DrawingLocation).where(DrawingLocation.file_id == drawing.id)
    ).all()
    assert {(r.candidate_id, r.label) for r in stored} == {
        ("p1-b123", "N170"),
        ("p1-bnuevo", "N172"),
    }


def saved_review(candidate_id: str, box: list[float], page: int = 1) -> LocationPublic:
    return LocationPublic.model_validate(
        DrawingLocation(
            file_id=uuid.uuid4(),
            sha256="a" * 64,
            candidate_id=candidate_id,
            label="N10",
            page=page,
            box=box,
        ),
        from_attributes=True,
    )


def test_competing_reviews_keep_their_own_positions() -> None:
    payload = {
        "balloons": [{"id": "current", "page": 1, "box": [0.1, 0.1, 0.16, 0.16]}]
    }
    reviews = [
        saved_review("old-a", [0.1, 0.1, 0.14, 0.14]),
        saved_review("old-b", [0.12, 0.1, 0.16, 0.14]),
    ]
    for ordered in (reviews, reviews[::-1]):
        assert attach_reviews(payload, ordered) == ordered


def test_ambiguous_review_does_not_move_to_the_next_free_balloon() -> None:
    payload = {
        "balloons": [
            {"id": "a", "page": 1, "box": [0.1, 0.1, 0.16, 0.16]},
            {"id": "b", "page": 1, "box": [0.14, 0.1, 0.2, 0.16]},
        ]
    }
    reviews = [
        saved_review("old", [0.13, 0.1, 0.17, 0.14]),
        saved_review("a", [0.1, 0.1, 0.16, 0.16]),
    ]
    for ordered in (reviews, reviews[::-1]):
        assert attach_reviews(payload, ordered) == ordered


def test_exact_review_supersedes_its_unique_predecessor_in_any_order() -> None:
    box = [0.1, 0.1, 0.16, 0.16]
    payload = {"balloons": [{"id": "current", "page": 1, "box": box}]}
    old, current = saved_review("old", box), saved_review("current", box)
    for ordered in ([old, current], [current, old]):
        assert attach_reviews(payload, ordered) == [current]
    assert old.candidate_id == "old"


@pytest.mark.parametrize(
    "page,box",
    [
        (1, [0.6, 0.6, 0.64, 0.64]),
        (2, [0.1, 0.1, 0.14, 0.14]),
    ],
)
def test_unmatched_review_remains_available(page: int, box: list[float]) -> None:
    payload = {
        "balloons": [{"id": "current", "page": 1, "box": [0.1, 0.1, 0.16, 0.16]}]
    }
    review = saved_review("old", box, page)
    assert attach_reviews(payload, [review]) == [review]


def test_separate_reviews_get_distinct_matches() -> None:
    boxes = [[0.1, 0.1, 0.16, 0.16], [0.6, 0.6, 0.66, 0.66]]
    payload = {
        "balloons": [
            {"id": f"current-{i}", "page": 1, "box": box} for i, box in enumerate(boxes)
        ]
    }
    reviews = [saved_review(f"old-{i}", box) for i, box in enumerate(boxes)]
    for ordered in (reviews, reviews[::-1]):
        attached = attach_reviews(payload, ordered)
        assert {r.candidate_id: r.box for r in attached} == {
            "current-0": boxes[0],
            "current-1": boxes[1],
        }


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
