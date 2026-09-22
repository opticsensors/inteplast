import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.models import FeaturePartLink, StoredFile
from tests.api.routes.test_cad_covers import cover_example
from tests.utils.feature import create_random_feature, create_random_part

BASE = settings.API_V1_STR


def test_catalog_shows_parts_without_features_and_cotas_only_when_searching(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    cota = PartCharacteristic(
        part_id=part.id, code="N170", revision="07", title="Diameter"
    )
    db.add(cota)
    db.commit()
    url = f"{BASE}/catalog"
    params = {"part_id": str(part.id)}
    result = client.get(url, headers=superuser_token_headers, params=params)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["cotas"] == []
    assert data["parts"][0]["characteristic_count"] == 1
    assert data["parts"][0]["feature_count"] == 0
    for query in ("170", "N 170", "Diameter"):
        data = client.get(
            url, headers=superuser_token_headers, params={**params, "q": query}
        ).json()
        assert data["part_count"] == 1
        assert data["cota_count"] == 1
        assert data["cotas"][0]["revision"] == "07"
        assert data["cotas"][0]["part"]["id"] == str(part.id)
    data = client.get(
        url,
        headers=superuser_token_headers,
        params={**params, "q": "170", "kind": "feature"},
    ).json()
    assert data["parts"] == data["cotas"] == []
    assert client.get(url).status_code == 401


def test_catalog_scopes_cotas_to_the_same_feature_and_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part, other = create_random_part(db), create_random_part(db)
    feature = create_random_feature(db)
    feature.category = "hole"
    feature.tags = ["critical"]
    db.add(feature)
    linked = PartCharacteristic(part_id=part.id, code="N170", revision="06")
    unlinked = PartCharacteristic(part_id=part.id, code="N171", revision="06")
    unrelated = PartCharacteristic(part_id=other.id, code="N170", revision="04")
    db.add_all([linked, unlinked, unrelated])
    db.commit()
    db.add(
        FeatureCharacteristicLink(feature_id=feature.id, characteristic_id=linked.id)
    )
    db.commit()
    params = {
        "q": "17",
        "feature_id": str(feature.id),
        "category": "hole",
        "tag": "critical",
    }
    result = client.get(
        f"{BASE}/catalog", headers=superuser_token_headers, params=params
    )
    assert result.status_code == 200, result.text
    data = result.json()
    assert [c["id"] for c in data["cotas"]] == [str(linked.id)]
    assert data["parts"][0]["feature_count"] == 1
    assert (
        client.get(
            f"{BASE}/catalog",
            headers=superuser_token_headers,
            params={**params, "tag": "different"},
        ).json()["cotas"]
        == []
    )


def test_part_detail_uses_the_existing_bidirectional_membership(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part, feature = create_random_part(db), create_random_feature(db)
    detail_url = f"{BASE}/parts/{part.id}/detail"
    link_url = f"{BASE}/features/{feature.id}/parts/{part.id}"
    assert client.post(link_url, headers=superuser_token_headers).status_code == 200
    data = client.get(detail_url, headers=superuser_token_headers).json()
    assert [f["id"] for f in data["features"]] == [str(feature.id)]
    assert data["part"]["feature_count"] == 1
    assert db.get(FeaturePartLink, (feature.id, part.id)) is not None
    assert client.delete(link_url, headers=superuser_token_headers).status_code == 200
    assert (
        client.get(detail_url, headers=superuser_token_headers).json()["features"] == []
    )
    assert client.get(detail_url).status_code == 401


def test_whole_part_cover_is_shared_and_invalidated_when_cad_changes(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, feature_cover = cover_example(client, superuser_token_headers, db)
    source = feature_cover["cover_3d"]
    part_id = source["part_id"]
    body = {key: source[key] for key in ("file_id", "file_version", "source_sha256")}
    body["image_id"] = feature_cover["image_id"]
    url = f"{BASE}/parts/{part_id}/cover"
    result = client.put(url, headers=superuser_token_headers, json=body)
    assert result.status_code == 200, result.text
    detail = client.get(
        f"{BASE}/parts/{part_id}/detail", headers=superuser_token_headers
    ).json()
    card = client.get(
        f"{BASE}/catalog", headers=superuser_token_headers, params={"part_id": part_id}
    ).json()["parts"][0]
    assert card["image"]["id"] == detail["part"]["image"]["id"] == body["image_id"]
    assert card["cad"]["id"] == body["file_id"]
    other = create_random_part(db)
    assert (
        client.put(
            f"{BASE}/parts/{other.id}/cover", headers=superuser_token_headers, json=body
        ).status_code
        == 409
    )
    document = db.get(StoredFile, uuid.UUID(body["file_id"]))
    assert document
    document.version = uuid.uuid4()
    db.add(document)
    db.commit()
    assert (
        client.get(
            f"{BASE}/parts/{part_id}/detail", headers=superuser_token_headers
        ).json()["part"]["image"]
        is None
    )
    assert (
        client.put(url, headers=superuser_token_headers, json=body).status_code == 409
    )
