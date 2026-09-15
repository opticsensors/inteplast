import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

BASE = f"{settings.API_V1_STR}/files"


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "drawings").mkdir()
    (root / "drawings" / "piece.pdf").write_bytes(b"%PDF-1.7 synthetic source")
    (root / "part.stp").write_text("ISO-10303-21;\nEND-ISO-10303-21;")
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(root))
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", str(uuid.uuid4()))
    return root


def test_local_source_browsing_and_reference(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path
) -> None:
    headers = superuser_token_headers
    assert client.get(f"{BASE}/source").status_code == 401
    listing = client.get(f"{BASE}/source", headers=headers, params={"limit": 1}).json()
    assert listing["count"] == 2
    assert listing["entries"][0]["path"] == "drawings"
    assert listing["entries"][0]["directory"]
    body = {"path": "drawings/piece.pdf", "revision": "07"}
    first = client.post(f"{BASE}/reference", headers=headers, json=body)
    assert first.status_code == 200
    document = first.json()
    assert document["source"] == "local"
    assert document["content_type"] == "application/pdf"
    assert document["revision"] == "07"
    assert (
        client.post(f"{BASE}/reference", headers=headers, json=body).json()["id"]
        == document["id"]
    )
    assert not (settings.uploads_path / document["id"]).exists()
    # Reusing an original must not silently ignore a conflicting revision label.
    assert (
        client.post(
            f"{BASE}/reference",
            headers=headers,
            json={"path": body["path"], "revision": "08"},
        ).status_code
        == 409
    )
    reused = client.post(
        f"{BASE}/reference", headers=headers, json={"path": body["path"]}
    ).json()
    assert reused["id"] == document["id"]
    assert reused["revision"] == "07"
    assert (
        client.get(f"{BASE}/{document['id']}/status", headers=headers).json()["state"]
        == "available"
    )
    url = client.get(f"{BASE}/{document['id']}/access-url", headers=headers).json()[
        "url"
    ]
    response = client.get(url)
    assert response.content == (source / body["path"]).read_bytes()
    assert response.headers["content-type"] == "application/pdf"
    part = client.get(url, headers={"Range": "bytes=0-3"})
    assert part.status_code == 206
    assert part.content == b"%PDF"
    assert (
        "attachment"
        in client.get(url + "&download=true").headers["content-disposition"]
    )
    assert client.delete(f"{BASE}/{document['id']}", headers=headers).status_code == 200
    assert (source / body["path"]).is_file()


@pytest.mark.parametrize(
    "path",
    [
        "../outside.pdf",
        "/etc/passwd",
        "drawings/../../outside.pdf",
        "drawings\\piece.pdf",
        "C:/secret",
        "//server/share",
        "part.stp:stream",
        ".hidden",
    ],
)
def test_source_rejects_escaping_paths(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path, path: str
) -> None:
    for method, endpoint, kwargs in [
        ("get", "source", {"params": {"path": path}}),
        ("post", "reference", {"json": {"path": path}}),
    ]:
        response = client.request(
            method, f"{BASE}/{endpoint}", headers=superuser_token_headers, **kwargs
        )
        assert response.status_code == 400
        assert str(source) not in response.text


def test_source_rejects_symlink_and_special_file(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path
) -> None:
    outside = source.parent / "secret.txt"
    outside.write_text("not shared")
    try:
        (source / "escape.txt").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink privileges unavailable")
    assert (
        client.post(
            f"{BASE}/reference",
            headers=superuser_token_headers,
            json={"path": "escape.txt"},
        ).status_code
        == 400
    )
    if hasattr(os, "mkfifo"):
        os.mkfifo(source / "pipe")
        assert (
            client.post(
                f"{BASE}/reference",
                headers=superuser_token_headers,
                json={"path": "pipe"},
            ).status_code
            == 404
        )


def test_relink_retains_identity_and_revokes_old_links(
    client: TestClient, superuser_token_headers: dict[str, str], source: Path
) -> None:
    headers = superuser_token_headers
    document = client.post(
        f"{BASE}/reference", headers=headers, json={"path": "part.stp"}
    ).json()
    endpoint = f"{BASE}/{document['id']}"
    old_url = client.get(endpoint + "/access-url", headers=headers).json()["url"]
    (source / "part.stp").rename(source / "renamed.stp")
    assert (
        client.get(endpoint + "/status", headers=headers).json()["state"] == "missing"
    )
    assert client.get(old_url).status_code == 404
    updated = client.put(
        endpoint + "/reference",
        headers=headers,
        json={
            "path": "renamed.stp",
            "expected_version": document["version"],
            "revision": "CAD A",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == document["id"]
    assert updated.json()["version"] != document["version"]
    assert updated.json()["content_type"] == "model/step"
    assert client.get(old_url).status_code == 401
    assert client.get(endpoint + "/access-url", headers=headers).status_code == 200
    assert (
        client.put(
            endpoint + "/reference",
            headers=headers,
            json={"path": "renamed.stp", "expected_version": document["version"]},
        ).status_code
        == 409
    )


def test_changed_original_is_not_silently_served(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = superuser_token_headers
    document = client.post(
        f"{BASE}/reference", headers=headers, json={"path": "part.stp"}
    ).json()
    endpoint = f"{BASE}/{document['id']}"
    url = client.get(endpoint + "/access-url", headers=headers).json()["url"]
    (source / "part.stp").write_text("changed geometry")
    assert (
        client.get(endpoint + "/status", headers=headers).json()["state"] == "changed"
    )
    assert client.get(endpoint + "/access-url", headers=headers).status_code == 409
    assert client.get(url).status_code == 409
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", "different-dataset")
    assert (
        client.get(endpoint + "/status", headers=headers).json()["state"]
        == "unavailable"
    )
    assert client.get(endpoint, headers=headers).status_code == 503


def test_source_disabled_and_large_reference(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = superuser_token_headers
    # Sparse synthetic file: registering a reference does not read its content.
    with (source / "large.stl").open("wb") as output:
        output.truncate(60 * 1024 * 1024)
    document = client.post(
        f"{BASE}/reference", headers=headers, json={"path": "large.stl"}
    )
    assert document.status_code == 200
    assert document.json()["size"] == 60 * 1024 * 1024
    monkeypatch.setattr(settings, "ASSETS_ROOT", None)
    assert client.get(f"{BASE}/source", headers=headers).json()["configured"] is False
    assert (
        client.post(
            f"{BASE}/reference", headers=headers, json={"path": "part.stp"}
        ).status_code
        == 503
    )
