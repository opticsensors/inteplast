import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.models import FeatureAsset, FeatureCategory, FeaturePartLink
from tests.utils.feature import create_random_feature, create_random_part

API = f"{settings.API_V1_STR}/evidence"


def test_metrology_search_preserves_piece_feature_and_cota_scope(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    token = uuid.uuid4().hex[:12]
    bolt, other = create_random_feature(db), create_random_feature(db)
    bolt.name, other.name = f"Bolt Eye {token}", f"Rib {token}"
    bolt.category, bolt.tags = FeatureCategory.hole, ["critical"]
    other.category, other.tags = FeatureCategory.rib, ["stiffness"]
    parts = [create_random_part(db) for _ in range(3)]
    for i, part in enumerate(parts):
        part.name = f"Housing {token} {i}"
        db.add(part)
    db.add(bolt)
    db.add(other)
    db.flush()
    db.add(FeaturePartLink(feature_id=bolt.id, part_id=parts[0].id))
    # Asset-only membership also counts, including a feature without cota assignments.
    db.add(
        FeatureAsset(feature_id=bolt.id, part_id=parts[1].id, kind="mold", name="Tool")
    )
    db.add(FeaturePartLink(feature_id=other.id, part_id=parts[0].id))
    c1 = PartCharacteristic(part_id=parts[0].id, code="N170", revision="06")
    c2 = PartCharacteristic(part_id=parts[1].id, code="N170", revision="07")
    free = PartCharacteristic(part_id=parts[0].id, code="N240", revision="06")
    db.add_all([c1, c2, free])
    db.flush()
    db.add(FeatureCharacteristicLink(feature_id=bolt.id, characteristic_id=c1.id))
    db.add(FeatureCharacteristicLink(feature_id=other.id, characteristic_id=c1.id))
    db.commit()
    headers = normal_user_token_headers
    assert client.get(f"{API}/metrology/filters").status_code == 401
    choices = client.get(f"{API}/metrology/filters", headers=headers).json()
    option = next(f for f in choices["features"] if f["id"] == str(bolt.id))
    assert set(option["part_ids"]) == {str(p.id) for p in parts[:2]}
    assert len(option["part_ids"]) == 2
    assert option["category"] == "hole" and option["tags"] == ["critical"]
    assert "characteristics" not in option
    assert str(parts[2].id) in {p["id"] for p in choices["parts"]}
    feature_choices = client.get(
        f"{settings.API_V1_STR}/features/filters", headers=headers
    ).json()
    assert str(parts[2].id) not in {p["id"] for p in feature_choices["parts"]}
    assert client.get(f"{API}/metrology").status_code == 401
    response = client.get(f"{API}/metrology", params={"q": bolt.name}, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["count"] == 2
    by_part = {item["part"]["id"]: item for item in result["data"]}
    first = by_part[str(parts[0].id)]
    assert first["matched_feature_ids"] == [str(bolt.id)]
    matching = next(f for f in first["features"] if f["id"] == str(bolt.id))
    assert [(c["code"], c["revision"]) for c in matching["characteristics"]] == [
        ("N170", "06")
    ]
    second = by_part[str(parts[1].id)]
    assert second["features"][0]["characteristics"] == []
    assert str(parts[2].id) not in by_part
    scoped = client.get(
        f"{API}/metrology",
        params={"feature_id": str(bolt.id), "limit": 1},
        headers=headers,
    ).json()
    assert scoped["count"] == 2 and len(scoped["data"]) == 1
    assert {f["id"] for f in scoped["data"][0]["features"]} == {str(bolt.id)}
    next_page = client.get(
        f"{API}/metrology",
        params={"feature_id": str(bolt.id), "limit": 1, "skip": 1},
        headers=headers,
    ).json()
    assert next_page["data"][0]["part"]["id"] != scoped["data"][0]["part"]["id"]
    piece = client.get(
        f"{API}/metrology", params={"q": parts[0].code}, headers=headers
    ).json()
    assert piece["data"][0]["matched_feature_ids"] == []
    unknown = client.get(
        f"{API}/metrology", params={"feature_id": str(uuid.uuid4())}, headers=headers
    ).json()
    assert unknown["count"] == 0
    detail = client.get(f"{API}/parts/{parts[0].id}", headers=headers).json()
    assert {c["code"] for c in detail["characteristics"]} == {"N170", "N240"}
    assert {f["id"] for f in detail["features"]} == {str(bolt.id), str(other.id)}
    assert all(len(f["characteristics"]) == 1 for f in detail["features"])
    assert next(f for f in detail["features"] if f["id"] == str(bolt.id))["tags"] == [
        "critical"
    ]
    assert (
        client.get(f"{API}/metrology", params={"limit": 0}, headers=headers).status_code
        == 422
    )


def test_metrology_does_not_search_global_cota_numbers(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    feature, part = create_random_feature(db), create_random_part(db)
    code = "N987654.321"
    cota = PartCharacteristic(part_id=part.id, code=code, revision="06")
    db.add(cota)
    db.flush()
    db.add(FeatureCharacteristicLink(feature_id=feature.id, characteristic_id=cota.id))
    db.commit()
    result = client.get(
        f"{API}/metrology", params={"q": code}, headers=normal_user_token_headers
    ).json()
    assert not any(p["part"]["id"] == str(part.id) for p in result["data"])
    # A cota assignment alone also declares the feature's presence in a piece.
    by_feature = client.get(
        f"{API}/metrology",
        params={"feature_id": str(feature.id)},
        headers=normal_user_token_headers,
    ).json()
    assert by_feature["count"] == 1
    assert by_feature["data"][0]["part"]["id"] == str(part.id)
    assert by_feature["data"][0]["features"][0]["characteristics"][0]["code"] == code
    # Both selectors and the Features results agree on cota-only membership.
    for endpoint in ("features/filters", "evidence/metrology/filters"):
        choices = client.get(
            f"{settings.API_V1_STR}/{endpoint}", headers=normal_user_token_headers
        ).json()
        assert str(part.id) in {p["id"] for p in choices["parts"]}
    results = client.get(
        f"{settings.API_V1_STR}/features/",
        params={"part_id": str(part.id)},
        headers=normal_user_token_headers,
    ).json()
    assert [f["id"] for f in results["data"]] == [str(feature.id)]
