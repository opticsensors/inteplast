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
    data = {"name": "Bolt Eye", "description": "agujero", "tags": ["Bosch", "agujero"]}
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


def test_read_features_selects_exact_feature_and_combines_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    tag = random_lower_string()
    selected = create_random_feature(db, tags=[tag])
    create_random_feature(db, tags=[tag])
    part = create_random_part(db)
    create_random_asset(db, selected, part=part)
    params = {"feature_id": str(selected.id), "tag": tag, "part_id": str(part.id)}
    url = f"{settings.API_V1_STR}/features/"
    response = client.get(url, params=params, headers=superuser_token_headers)
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 1
    assert [item["id"] for item in result["data"]] == [str(selected.id)]
    for mismatch in (
        {"feature_id": str(uuid.uuid4())},
        {"part_id": str(uuid.uuid4())},
        {"q": random_lower_string()},
        {"tag": random_lower_string()},
    ):
        result = client.get(
            url, params={**params, **mismatch}, headers=superuser_token_headers
        ).json()
        assert result["count"] == 0 and result["data"] == []
    result = client.get(
        url, params={**params, "skip": 1}, headers=superuser_token_headers
    ).json()
    assert result["count"] == 1 and result["data"] == []


def test_read_feature_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    tag = random_lower_string()
    feature = create_random_feature(db, tags=[tag])
    part = create_random_part(db)
    create_random_asset(db, feature, kind=AssetKind.mold, part=part)
    # Una pieza que no usa ningun feature no debe salir en los desplegables
    unused = create_random_part(db)
    unlinked_feature = create_random_feature(db)

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
    options = {item["id"]: item for item in content["features"]}
    assert options[str(feature.id)]["name"] == feature.name
    assert options[str(feature.id)]["part_ids"] == [str(part.id)]
    assert options[str(unlinked_feature.id)]["part_ids"] == []


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

    # Un UUID no autoriza la descarga; imagenes y visores usan un enlace firmado.
    response = client.get(f"{settings.API_V1_STR}/files/{stored['id']}")
    assert response.status_code == 401
    link = client.get(
        f"{settings.API_V1_STR}/files/{stored['id']}/access-url",
        headers=superuser_token_headers,
    )
    assert link.status_code == 200
    response = client.get(link.json()["url"])
    assert response.status_code == 200
    assert response.content == b"contenido"

    response = client.delete(
        f"{settings.API_V1_STR}/files/{stored['id']}", headers=superuser_token_headers
    )
    assert response.status_code == 200


def test_linked_asset_uses_filename_on_create_edit_and_replacement(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    base = settings.API_V1_STR
    features = [create_random_feature(db), create_random_feature(db)]
    filenames = [f"{uuid.uuid4()}_real file.step", f"{uuid.uuid4()}_new file.stp"]
    documents = [
        client.post(
            f"{base}/files/",
            headers=headers,
            files={"file": (name, b"synthetic", "model/step")},
        ).json()
        for name in filenames
    ]
    assets = []
    for feature in features:
        response = client.post(
            f"{base}/features/{feature.id}/assets",
            headers=headers,
            json={"kind": "part", "name": "Old alias", "file_id": documents[0]["id"]},
        )
        assert response.status_code == 200
        assert response.json()["name"] == filenames[0]
        assets.append(response.json())
    url = f"{base}/features/assets/{assets[0]['id']}"
    renamed = client.put(url, headers=headers, json={"name": "Outdated name"})
    assert renamed.json()["name"] == filenames[0]
    replaced = client.put(url, headers=headers, json={"file_id": documents[1]["id"]})
    assert replaced.status_code == 200
    assert replaced.json()["name"] == filenames[1]
    saved = [
        client.get(f"{base}/features/{feature.id}", headers=headers).json()
        for feature in features
    ]
    assert saved[0]["assets"][0]["file"]["id"] == documents[1]["id"]
    assert saved[1]["assets"][0]["file"]["id"] == documents[0]["id"]
    assert saved[1]["assets"][0]["name"] == filenames[0]
    found = client.get(
        f"{base}/features/", headers=headers, params={"q": filenames[1]}
    ).json()
    assert str(features[0].id) in [item["id"] for item in found["data"]]
