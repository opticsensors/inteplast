import hashlib
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import AssetKind
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_part,
)


def cover_example(
    client: TestClient, headers: dict[str, str], db: Session
) -> tuple[str, dict[str, Any]]:
    feature = create_random_feature(db)
    part = create_random_part(db)
    raw = b"ISO-10303-21; test source bytes; END-ISO-10303-21;"
    file = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=headers,
        files={"file": ("piece.stp", raw, "application/octet-stream")},
    ).json()
    image = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=headers,
        files={"file": ("cover.png", b"image fixture", "image/png")},
    ).json()
    asset = create_random_asset(db, feature, kind=AssetKind.part, part=part)
    asset.file_id = uuid.UUID(file["id"])
    db.add(asset)
    db.commit()
    return str(feature.id), {
        "image_id": image["id"],
        "cover_3d": {
            "asset_id": str(asset.id),
            "part_id": str(part.id),
            "file_id": file["id"],
            "file_version": file["version"],
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "geometry_key": "a" * 64,
            "recipe": "occt-import-js@0.0.23/cover-v1",
            "faces": [{"mesh": 0, "face": 3}, {"mesh": 0, "face": 8}],
            "camera": {"position": [20, -20, 20], "target": [0, 0, 0], "up": [0, 0, 1]},
        },
    }


def test_cover_persists_and_image_replacement_clears_annotation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature_id, body = cover_example(client, superuser_token_headers, db)
    url = f"{settings.API_V1_STR}/features/{feature_id}"
    result = client.put(url, headers=superuser_token_headers, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["cover_3d"] == body["cover_3d"]
    # An unrelated edit must retain the cover and source identity.
    result = client.put(
        url, headers=superuser_token_headers, json={"description": "New description"}
    )
    assert result.json()["cover_3d"] == body["cover_3d"]
    assert (
        client.get(url, headers=superuser_token_headers).json()["image"]["id"]
        == body["image_id"]
    )
    assert client.get(url).status_code == 401
    result = client.put(url, headers=superuser_token_headers, json={"image_id": None})
    assert result.status_code == 200
    assert result.json()["cover_3d"] is None
    assert result.json()["image"] is None


def test_cover_rejects_changed_source_without_partial_header_save(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature_id, body = cover_example(client, superuser_token_headers, db)
    url = f"{settings.API_V1_STR}/features/{feature_id}"
    before = client.get(url, headers=superuser_token_headers).json()
    source = settings.uploads_path / body["cover_3d"]["file_id"]
    source.write_bytes(b"new revision")
    result = client.put(
        url, headers=superuser_token_headers, json={**body, "name": "Must not save"}
    )
    assert result.status_code == 409
    after = client.get(url, headers=superuser_token_headers).json()
    assert after["name"] == before["name"]
    assert after["image"] == before["image"]
    assert after["cover_3d"] is None


def test_cover_rejects_another_features_cad(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, body = cover_example(client, superuser_token_headers, db)
    other = create_random_feature(db)
    result = client.put(
        f"{settings.API_V1_STR}/features/{other.id}",
        headers=superuser_token_headers,
        json=body,
    )
    assert result.status_code == 409


def test_cover_requires_valid_selection_camera_and_image(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature_id, body = cover_example(client, superuser_token_headers, db)
    url = f"{settings.API_V1_STR}/features/{feature_id}"
    annotation = body["cover_3d"]
    for changes in [
        {"faces": []},
        {"faces": [{"mesh": -1, "face": 0}]},
        {"faces": [{"mesh": 0, "face": 1}] * 2},
        {"camera": {"position": [0, 0, 0], "target": [0, 0, 0], "up": [0, 0, 1]}},
        {"recipe": "unknown renderer"},
    ]:
        result = client.put(
            url,
            headers=superuser_token_headers,
            json={**body, "cover_3d": {**annotation, **changes}},
        )
        assert result.status_code == 422, result.text
    assert (
        client.put(
            url, headers=superuser_token_headers, json={"cover_3d": annotation}
        ).status_code
        == 422
    )
