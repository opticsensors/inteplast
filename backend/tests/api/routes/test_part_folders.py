import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Part
from tests.utils.feature import create_random_part

BASE = settings.API_V1_STR


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    return tmp_path


def test_concurrent_folder_selection_reuses_one_piece_and_preserves_edits(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    source: Path,
) -> None:
    code = str(uuid.uuid4().int)[:12]
    folder = f"{code} Pump Housing"
    (source / folder).mkdir()
    original = source / folder / "mold.step"
    original.write_bytes(b"synthetic original")

    def choose(_: int):
        return client.post(
            f"{BASE}/parts/from-folder",
            headers=superuser_token_headers,
            json={"folder_path": folder},
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(choose, range(4)))
    assert all(response.status_code == 200 for response in responses)
    part = responses[0].json()
    assert {response.json()["id"] for response in responses} == {part["id"]}
    assert part["code"] == code
    assert part["name"] == folder
    assert len(db.exec(select(Part).where(Part.folder_path == folder)).all()) == 1
    assert (
        client.put(
            f"{BASE}/parts/{part['id']}",
            headers=superuser_token_headers,
            json={"code": f"EDIT-{code}", "name": "Custom label"},
        ).status_code
        == 200
    )
    again = choose(0).json()
    assert again["id"] == part["id"]
    assert again["name"] == "Custom label"
    assert again["code"] == f"EDIT-{code}"
    assert original.read_bytes() == b"synthetic original"


def test_folder_binds_legacy_piece_without_overwriting_its_name(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    source: Path,
) -> None:
    part = create_random_part(db, name="Existing custom name")
    part.code = str(uuid.uuid4().int)[:12]
    db.add(part)
    db.commit()
    folder = f"{part.code} Housing"
    (source / folder).mkdir()
    response = client.post(
        f"{BASE}/parts/from-folder",
        headers=superuser_token_headers,
        json={"folder_path": folder},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(part.id)
    assert response.json()["name"] == "Existing custom name"
    assert response.json()["folder_path"] == folder
    other = f"{part.code} Different housing"
    (source / other).mkdir()
    conflict = client.post(
        f"{BASE}/parts/from-folder",
        headers=superuser_token_headers,
        json={"folder_path": other},
    )
    assert conflict.status_code == 409


def test_folder_without_numeric_prefix_gets_stable_editable_code(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path
) -> None:
    folder = f"Housing {uuid.uuid4()}"
    (source / folder).mkdir()
    pieces = [
        client.post(
            f"{BASE}/parts/from-folder",
            headers=superuser_token_headers,
            json={"folder_path": folder},
        ).json()
        for _ in range(2)
    ]
    assert pieces[0]["code"].startswith("PIEZA-")
    assert pieces[0]["name"] == folder
    assert pieces[0]["id"] == pieces[1]["id"]


def test_same_folder_cannot_be_assigned_through_create_or_edit(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    source: Path,
) -> None:
    folder = f"Housing {uuid.uuid4()}"
    (source / folder).mkdir()
    registered = client.post(
        f"{BASE}/parts/from-folder",
        headers=superuser_token_headers,
        json={"folder_path": folder},
    )
    assert registered.status_code == 200
    other = create_random_part(db)
    assert (
        client.put(
            f"{BASE}/parts/{other.id}",
            headers=superuser_token_headers,
            json={"folder_path": folder},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{BASE}/parts/",
            headers=superuser_token_headers,
            json={"code": str(uuid.uuid4()), "folder_path": folder},
        ).status_code
        == 409
    )
    db.refresh(other)
    assert other.folder_path is None


def test_only_existing_direct_child_folders_can_register_pieces(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path
) -> None:
    (source / "piece" / "cad").mkdir(parents=True)
    (source / "drawing.pdf").write_bytes(b"synthetic")
    for path, status in [
        ("", 422),
        ("piece/cad", 400),
        ("../escape", 400),
        ("/absolute", 400),
        ("piece/", 400),
        ("missing", 404),
        ("drawing.pdf", 404),
    ]:
        response = client.post(
            f"{BASE}/parts/from-folder",
            headers=superuser_token_headers,
            json={"folder_path": path},
        )
        assert response.status_code == status, response.text
