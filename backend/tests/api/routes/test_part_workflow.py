import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import FeatureAsset, Part, StoredFile
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_part,
)

BASE = settings.API_V1_STR


def test_folder_default_name_is_shared_but_custom_name_is_kept(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("3212 Pump Housing", "Other housing"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    part = create_random_part(db, name="Nueva pieza")
    features = [create_random_feature(db), create_random_feature(db)]
    for feature in features:
        client.post(
            f"{BASE}/features/{feature.id}/parts/{part.id}",
            headers=superuser_token_headers,
        )
    url = f"{BASE}/parts/{part.id}"
    response = client.put(
        url, headers=superuser_token_headers, json={"folder_path": "3212 Pump Housing"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "3212 Pump Housing"
    for feature in features:
        saved = client.get(
            f"{BASE}/features/{feature.id}", headers=superuser_token_headers
        ).json()
        assert saved["parts"][0]["folder_path"] == "3212 Pump Housing"
        assert saved["assets"] == []
    client.put(url, headers=superuser_token_headers, json={"name": "Custom name"})
    response = client.put(
        url, headers=superuser_token_headers, json={"folder_path": "Other housing"}
    )
    assert response.json()["name"] == "Custom name"
    assert (
        client.put(
            url, headers=superuser_token_headers, json={"folder_path": "../escape"}
        ).status_code
        == 400
    )
    assert (
        client.put(
            url, headers=superuser_token_headers, json={"folder_path": "missing"}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"{BASE}/features/{features[0].id}", headers=superuser_token_headers
        ).json()["parts"][0]["folder_path"]
        == "Other housing"
    )


def test_remove_card_removes_only_its_feature_assets_and_keeps_originals(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    first, second = create_random_feature(db), create_random_feature(db)
    part, other = create_random_part(db), create_random_part(db)
    deleted = create_random_asset(db, first, part=part)
    kept = create_random_asset(db, second, part=part)
    unrelated = create_random_asset(db, first, part=other)
    document = StoredFile(
        filename="original.pdf", content_type="application/pdf", size=1
    )
    db.add(document)
    db.commit()
    deleted.file_id = kept.file_id = document.id
    db.add(deleted)
    db.add(kept)
    db.commit()
    deleted_id, kept_id, unrelated_id, part_id, document_id = (
        deleted.id,
        kept.id,
        unrelated.id,
        part.id,
        document.id,
    )
    # The card may exist only through assets, without an explicit part link.
    response = client.delete(
        f"{BASE}/features/{first.id}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.get(FeatureAsset, deleted_id) is None
    assert db.get(FeatureAsset, kept_id) is not None
    assert db.get(FeatureAsset, unrelated_id) is not None
    assert db.get(Part, part_id) is not None
    assert db.get(StoredFile, document_id) is not None
    saved = client.get(
        f"{BASE}/features/{first.id}", headers=superuser_token_headers
    ).json()
    assert all(asset["part"]["id"] != str(part.id) for asset in saved["assets"])
    client.post(
        f"{BASE}/features/{first.id}/parts/{part.id}", headers=superuser_token_headers
    )
    assert (
        len(
            client.get(
                f"{BASE}/features/{first.id}", headers=superuser_token_headers
            ).json()["assets"]
        )
        == 1
    )


def test_order_is_per_feature_persistent_and_rejects_stale_or_invalid_lists(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    first, second = create_random_feature(db), create_random_feature(db)
    parts = [create_random_part(db), create_random_part(db)]
    for feature in (first, second):
        for part in parts:
            client.post(
                f"{BASE}/features/{feature.id}/parts/{part.id}",
                headers=superuser_token_headers,
            )
    original = [str(part.id) for part in parts]
    wanted = original[::-1]
    url = f"{BASE}/features/{first.id}/parts/order"
    response = client.put(
        url, headers=superuser_token_headers, json={"part_ids": wanted}
    )
    assert response.status_code == 200
    assert response.json()["part_order"] == wanted
    assert (
        client.get(
            f"{BASE}/features/{first.id}", headers=superuser_token_headers
        ).json()["part_order"]
        == wanted
    )
    assert (
        client.get(
            f"{BASE}/features/{second.id}", headers=superuser_token_headers
        ).json()["part_order"]
        == original
    )
    for invalid in (
        [original[0]],
        [original[0], original[0]],
        [original[0], str(uuid.uuid4())],
    ):
        assert (
            client.put(
                url, headers=superuser_token_headers, json={"part_ids": invalid}
            ).status_code
            == 409
        )
    client.delete(
        f"{BASE}/features/{first.id}/parts/{parts[0].id}",
        headers=superuser_token_headers,
    )
    saved = client.get(
        f"{BASE}/features/{first.id}", headers=superuser_token_headers
    ).json()
    assert saved["part_order"] == [original[1]]
    assert saved["parts"][0]["id"] == original[1]


def test_folder_listing_filters_before_pagination(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    (tmp_path / "first").mkdir()
    (tmp_path / "second").mkdir()
    (tmp_path / "file.pdf").write_bytes(b"synthetic")
    response = client.get(
        f"{BASE}/files/source",
        headers=superuser_token_headers,
        params={"directories_only": True, "skip": 1, "limit": 1},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["entries"][0]["path"] == "second"
