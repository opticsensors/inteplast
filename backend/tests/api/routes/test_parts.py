import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import FeatureAsset
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


def test_delete_part_keeps_the_assets(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Borrar la pieza deja el adjunto huerfano, no lo borra."""
    feature = create_random_feature(db)
    part = create_random_part(db)
    asset = create_random_asset(db, feature, part=part)

    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 200

    db.expire_all()
    stored = db.get(FeatureAsset, asset.id)
    assert stored is not None
    assert stored.part_id is None
