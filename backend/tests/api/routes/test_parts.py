import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import FeatureAsset, FeaturePartLink, Part, StoredFile
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_part,
)
from tests.utils.utils import random_lower_string


def test_create_part_and_reject_duplicate_code(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    code = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"code": code, "name": "Pump Housing"},
    )
    assert response.status_code == 200
    assert response.json()["code"] == code

    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"code": code, "name": "otra cosa"},
    )
    assert response.status_code == 409


def test_read_parts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.get(
        f"{settings.API_V1_STR}/parts/", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert part.code in [item["code"] for item in content["data"]]


def test_update_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    other = create_random_part(db)

    response = client.put(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
        json={"name": "Pump Housing"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Pump Housing"

    response = client.put(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
        json={"code": other.code},
    )
    assert response.status_code == 409


def test_update_part_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.put(
        f"{settings.API_V1_STR}/parts/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json={"name": "x"},
    )
    assert response.status_code == 404


def test_delete_part_needs_superuser(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403


def test_delete_part_rejects_implicit_asset_usage(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Assets alone count as usage, even without an explicit feature link."""
    feature = create_random_feature(db)
    part = create_random_part(db)
    asset = create_random_asset(db, feature, part=part)

    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 409

    db.expire_all()
    stored = db.get(FeatureAsset, asset.id)
    assert stored is not None
    assert stored.part_id == part.id
    assert db.get(Part, part.id) is not None


def test_usage_counts_distinct_features_and_blocks_explicit_links(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part, unused = create_random_part(db), create_random_part(db)
    first, second = create_random_feature(db), create_random_feature(db)
    db.add(FeaturePartLink(feature_id=first.id, part_id=part.id))
    db.add(FeaturePartLink(feature_id=second.id, part_id=part.id))
    db.commit()
    create_random_asset(db, first, part=part)
    create_random_asset(db, first, part=part)
    listed = client.get(
        f"{settings.API_V1_STR}/parts/", headers=superuser_token_headers
    ).json()["data"]
    counts = {row["id"]: row["feature_count"] for row in listed}
    assert counts[str(part.id)] == 2
    assert counts[str(unused.id)] == 0
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 409
    assert "2 features" in response.json()["detail"]
    assert db.get(FeaturePartLink, (second.id, part.id)) is not None


def test_delete_unused_part_removes_only_catalog_entry(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    part = create_random_part(db)
    part.folder_path = "Trial piece"
    db.add(part)
    folder = tmp_path / part.folder_path
    folder.mkdir()
    original = folder / "drawing.pdf"
    original.write_bytes(b"synthetic original")
    document = StoredFile(
        filename="drawing.pdf", size=18, content_type="application/pdf"
    )
    db.add(document)
    db.commit()
    part_id, document_id = part.id, document.id
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part_id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.get(Part, part_id) is None
    assert db.get(StoredFile, document_id) is not None
    assert original.read_bytes() == b"synthetic original"
    listed = client.get(
        f"{settings.API_V1_STR}/parts/", headers=superuser_token_headers
    ).json()["data"]
    assert str(part_id) not in {row["id"] for row in listed}
    assert (
        client.delete(
            f"{settings.API_V1_STR}/parts/{part_id}", headers=superuser_token_headers
        ).status_code
        == 404
    )
