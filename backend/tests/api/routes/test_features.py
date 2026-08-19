import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import AssetKind, NoteKind
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_note,
    create_random_part,
)
from tests.utils.utils import random_lower_string


def test_create_feature(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"name": "Bolt Eye", "description": "agujero", "tags": ["3212", "N170"]}
    response = client.post(
        f"{settings.API_V1_STR}/features/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == data["name"]
    assert content["tags"] == data["tags"]
    assert "id" in content


def test_read_feature(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    create_random_note(db, feature, kind=NoteKind.warning)
    create_random_note(db, feature, kind=NoteKind.lesson)
    create_random_asset(db, feature)

    response = client.get(
        f"{settings.API_V1_STR}/features/{feature.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(feature.id)
    assert len(content["notes"]) == 2
    assert len(content["assets"]) == 1


def test_read_feature_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/features/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_read_features_search_by_related_content(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """La busqueda global tambien encuentra por el codigo de la pieza."""
    feature = create_random_feature(db)
    part = create_random_part(db)
    create_random_asset(db, feature, part=part)

    response = client.get(
        f"{settings.API_V1_STR}/features/",
        headers=superuser_token_headers,
        params={"q": part.code},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 1
    assert content["data"][0]["id"] == str(feature.id)


def test_read_features_filter_by_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """El filtro por pieza coge tanto los adjuntos como la pieza declarada."""
    part = create_random_part(db)
    with_asset = create_random_feature(db)
    create_random_asset(db, with_asset, part=part)
    declared = create_random_feature(db)
    create_random_feature(db)

    response = client.post(
        f"{settings.API_V1_STR}/features/{declared.id}/parts/{part.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert [p["code"] for p in response.json()["parts"]] == [part.code]

    response = client.get(
        f"{settings.API_V1_STR}/features/",
        headers=superuser_token_headers,
        params={"part_id": str(part.id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2
    assert {item["id"] for item in content["data"]} == {
        str(with_asset.id),
        str(declared.id),
    }

    response = client.delete(
        f"{settings.API_V1_STR}/features/{declared.id}/parts/{part.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    response = client.get(
        f"{settings.API_V1_STR}/features/",
        headers=superuser_token_headers,
        params={"part_id": str(part.id)},
    )
    assert response.json()["count"] == 1


def test_read_features_filter_by_tag(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    tag = random_lower_string()
    feature = create_random_feature(db, tags=[tag])
    create_random_feature(db, tags=[random_lower_string()])

    response = client.get(
        f"{settings.API_V1_STR}/features/",
        headers=superuser_token_headers,
        params={"tag": tag},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 1
    assert content["data"][0]["id"] == str(feature.id)


def test_read_feature_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    tag = random_lower_string()
    feature = create_random_feature(db, tags=[tag])
    part = create_random_part(db)
    create_random_asset(db, feature, kind=AssetKind.mold, part=part)
    # Una pieza que no usa ningun feature no debe salir en los desplegables
    unused = create_random_part(db)

    response = client.get(
        f"{settings.API_V1_STR}/features/filters", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert tag in content["tags"]
    codes = [item["code"] for item in content["parts"]]
    assert part.code in codes
    assert unused.code not in codes
    assert "hole" in content["categories"]


def test_update_feature(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    response = client.put(
        f"{settings.API_V1_STR}/features/{feature.id}",
        headers=superuser_token_headers,
        json={"name": "Nervio", "tags": ["nervio"]},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == "Nervio"
    assert content["tags"] == ["nervio"]
    # description no se toca al no venir en el payload
    assert content["description"] == feature.description


def test_delete_feature(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    response = client.delete(
        f"{settings.API_V1_STR}/features/{feature.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    response = client.get(
        f"{settings.API_V1_STR}/features/{feature.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_delete_feature_not_owner(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    response = client.delete(
        f"{settings.API_V1_STR}/features/{feature.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_features_require_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/features/")
    assert response.status_code == 401


def test_create_and_delete_note(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    response = client.post(
        f"{settings.API_V1_STR}/features/{feature.id}/notes",
        headers=superuser_token_headers,
        json={"kind": "lesson", "title": "Retoque 1.33", "body": "**funciono**"},
    )
    assert response.status_code == 200
    note = response.json()
    assert note["kind"] == "lesson"

    response = client.delete(
        f"{settings.API_V1_STR}/features/notes/{note['id']}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200


def test_create_and_update_asset(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    feature = create_random_feature(db)
    # Codigos aleatorios: un codigo fijo chocaria con el del seed si la BD de
    # desarrollo ya tiene datos, y la violacion de unicidad tumba la sesion.
    part = create_random_part(db)
    other = create_random_part(db)
    response = client.post(
        f"{settings.API_V1_STR}/features/{feature.id}/assets",
        headers=superuser_token_headers,
        json={"kind": "drawing", "name": "plano rev 07", "part_id": str(part.id)},
    )
    assert response.status_code == 200
    asset = response.json()
    assert asset["kind"] == "drawing"
    assert asset["file"] is None
    assert asset["part"]["code"] == part.code

    response = client.put(
        f"{settings.API_V1_STR}/features/assets/{asset['id']}",
        headers=superuser_token_headers,
        json={"part_id": str(other.id)},
    )
    assert response.status_code == 200
    assert response.json()["part"]["code"] == other.code

    response = client.post(
        f"{settings.API_V1_STR}/features/{feature.id}/assets",
        headers=superuser_token_headers,
        json={"kind": "scan", "name": "stl", "part_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_upload_and_read_file(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=superuser_token_headers,
        files={"file": ("bolt-eye.txt", b"contenido", "text/plain")},
    )
    assert response.status_code == 200
    stored = response.json()
    assert stored["filename"] == "bolt-eye.txt"
    assert stored["size"] == len(b"contenido")

    # Sin cabecera de autenticacion: el <img src> del frontend no la manda
    response = client.get(f"{settings.API_V1_STR}/files/{stored['id']}")
    assert response.status_code == 200
    assert response.content == b"contenido"

    response = client.delete(
        f"{settings.API_V1_STR}/files/{stored['id']}", headers=superuser_token_headers
    )
    assert response.status_code == 200
