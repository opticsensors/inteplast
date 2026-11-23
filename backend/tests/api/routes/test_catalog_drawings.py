"""Drawings in the catalogue: every drawing of the pieces, with a cached thumbnail."""

import os
import threading
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app import thumbnails
from app.core.config import settings
from app.file_sources import stamp
from app.ingestion.drawing_orientation import display_rotation
from app.knowledge_models import PartFile
from app.models import StoredFile
from tests.utils.feature import create_random_part

API = settings.API_V1_STR


def write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as pdf:
        page = pdf.new_page(width=420, height=297)
        page.insert_text((40, 60), text, fontsize=24)
        pdf.save(path)


@pytest.fixture
def pieces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> dict[str, Any]:
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", False)
    token = uuid.uuid4().hex[:8]
    family = client.post(
        f"{API}/families",
        headers=superuser_token_headers,
        json={"name": f"Housing {token}"},
    ).json()["id"]
    part, other = create_random_part(db), create_random_part(db)
    part.folder_path = f"Piece {part.code}"
    part.family_id = uuid.UUID(family)
    part.components = [
        {
            "key": "BASE",
            "name": "BASE",
            "sheets": [],
            "files": [{"path": "base/plan_base.pdf", "revision": "07"}],
        }
    ]
    other.folder_path = f"Piece {other.code}"
    # Pieces whose files were saved from their page: the app marks them as managed.
    part.files_managed = other.files_managed = True
    files = {}
    for owner, relative, _kind in [
        (part, "base/plan_base.pdf", "drawing"),
        (part, f"tapa_{token}.pdf", "drawing"),
        (part, "model.step", "part"),
        (other, "other.pdf", "drawing"),
    ]:
        full = tmp_path / owner.folder_path / relative
        if relative.endswith(".pdf"):
            write_pdf(full, relative)
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(b"step")
        files[relative] = StoredFile(
            filename=full.name,
            source="local",
            source_key=settings.ASSETS_SOURCE_ID,
            source_path=f"{owner.folder_path}/{relative}",
            source_version=stamp(full),
            content_type="application/pdf",
        )
    db.add_all([part, other, *files.values()])
    db.flush()
    for position, (relative, owner, kind, primary) in enumerate(
        [
            ("base/plan_base.pdf", part, "drawing", True),
            (f"tapa_{token}.pdf", part, "drawing", False),
            ("model.step", part, "part", True),
            ("other.pdf", other, "drawing", True),
        ]
    ):
        db.add(
            PartFile(
                part_id=owner.id,
                file_id=files[relative].id,
                kind=kind,
                name=relative.split("/")[-1],
                position=position,
                primary=primary,
            )
        )
    db.commit()
    return {
        "root": tmp_path,
        "part": part,
        "other": other,
        "family": family,
        "files": files,
        "token": token,
    }


def test_every_drawing_of_the_filtered_pieces_with_component_and_revision(
    client: TestClient, superuser_token_headers: dict[str, str], pieces: Any
) -> None:
    headers = superuser_token_headers
    url = f"{API}/catalog/drawings"
    assert client.get(url).status_code == 401
    data = client.get(url, headers=headers, params={"family_id": pieces["family"]})
    assert data.status_code == 200, data.text
    body = data.json()
    # Both drawings of the piece, not only the principal; the CAD is not a drawing.
    assert body["count"] == 2
    assert [card["name"] for card in body["data"]] == [
        "plan_base.pdf",
        f"tapa_{pieces['token']}.pdf",
    ]
    base, tapa = body["data"]
    assert base["primary"] is True and tapa["primary"] is False
    assert (base["component"], base["revision"]) == ("BASE", "07")
    assert (tapa["component"], tapa["revision"]) == (None, None)
    assert base["part"]["id"] == str(pieces["part"].id)
    found = client.get(
        url, headers=headers, params={"q": f"TAPA_{pieces['token']}"}
    ).json()
    assert [card["name"] for card in found["data"]] == [f"tapa_{pieces['token']}.pdf"]
    other = client.get(
        url, headers=headers, params={"part_id": str(pieces["other"].id)}
    ).json()
    assert [card["name"] for card in other["data"]] == ["other.pdf"]


def test_thumbnail_is_made_once_per_version_and_again_when_the_file_changes(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    pieces: Any,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
) -> None:
    headers = superuser_token_headers
    document = pieces["files"]["base/plan_base.pdf"]
    url = f"{API}/files/{document.id}/thumbnail"
    calls: list[Path] = []
    original = thumbnails.convert

    def counted(source: Path, partial: Path, page: int) -> None:
        calls.append(partial)
        original(source, partial, page)

    monkeypatch.setattr(thumbnails, "convert", counted)
    folder = thumbnails.thumbnail_directory(document.id)
    first = client.post(url, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "ready" and len(calls) == 1
    (before,) = folder.glob("*.png")
    image = client.get(first.json()["url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")
    # Same version: served from the cache, not drawn again.
    again = client.post(url, headers=headers)
    assert again.json()["state"] == "ready" and len(calls) == 1
    assert client.get(again.json()["url"]).status_code == 200

    # A new version of the original: a new thumbnail, the old one is removed.
    original_file = pieces["root"] / pieces["part"].folder_path / "base/plan_base.pdf"
    write_pdf(original_file, "revision 08")
    later = original_file.stat().st_mtime + 10
    os.utime(original_file, (later, later))
    # A changed original is linked again before use: its version moves on.
    document.source_version = stamp(original_file)
    db.add(document)
    db.commit()
    changed = client.post(url, headers=headers)
    assert changed.json()["state"] == "ready" and len(calls) == 2
    (after,) = folder.glob("*.png")
    assert after != before and not before.exists()
    assert not list(folder.glob("*.part"))
    # The old link names the old version and no longer serves anything.
    assert client.get(first.json()["url"]).status_code in {401, 409}
    assert client.get(changed.json()["url"]).status_code == 200


def test_rotation_is_per_sheet_and_preserves_portrait_drawings(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    pieces: Any,
    db: Session,
) -> None:
    document = pieces["files"]["base/plan_base.pdf"]
    source = pieces["root"] / document.source_path
    with fitz.open() as pdf:
        for native_rotation in (0, 90, 180, 270):
            sheet = pdf.new_page(width=300, height=500)
            sheet.insert_text((20, 40), "General drawing notes and specifications")
            sheet.set_rotation(native_rotation)
        pdf.save(source)
    original_bytes = source.read_bytes()
    document.source_version = stamp(source)
    db.add(document)
    db.commit()
    url = f"{API}/files/{document.id}/thumbnail"
    urls = []
    for page, expected in enumerate((0, 270, 180, 90), start=1):
        response = client.post(
            url, headers=superuser_token_headers, params={"page": page}
        )
        assert response.status_code == 200, response.text
        item = response.json()
        assert item["state"] == "ready" and item["rotation"] == expected
        urls.append(item["url"])
    for signed_url in urls:
        response = client.get(signed_url)
        assert response.status_code == 200
        with Image.open(BytesIO(response.content)) as image:
            assert image.size == (480, 800)
    assert client.get(urls[1].replace("page=2", "page=1")).status_code == 401
    assert source.read_bytes() == original_bytes


def test_scanned_title_block_and_sheet_without_readable_text() -> None:
    with fitz.open() as pdf:
        vector = pdf.new_page(width=600, height=400)
        vector.insert_text((380, 340), "Drawing specifications")
        vector.insert_text((380, 360), "General assembly notes")
        image = vector.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
        scan = pdf.new_page(width=600, height=400)
        scan.insert_image(scan.rect, stream=image)
        scan.set_rotation(270)
        assert display_rotation(scan) == 90
        assert scan.rotation == 270
        blank = pdf.new_page(width=300, height=500)
        assert display_rotation(blank) == 0


def test_thumbnails_are_drawn_a_few_at_a_time_and_only_for_pdfs(
    client: TestClient, superuser_token_headers: dict[str, str], pieces: Any
) -> None:
    headers = superuser_token_headers
    document = pieces["files"][f"tapa_{pieces['token']}.pdf"]
    url = f"{API}/files/{document.id}/thumbnail"
    taken = 0
    while thumbnails.SLOTS.acquire(blocking=False):
        taken += 1
    try:
        busy = client.post(url, headers=headers)
        assert busy.status_code == 200 and busy.json() == {
            "state": "busy",
            "url": None,
            "rotation": 0,
        }
    finally:
        for _ in range(taken):
            thumbnails.SLOTS.release()
    assert client.post(url, headers=headers).json()["state"] == "ready"
    step = pieces["files"]["model.step"]
    assert (
        client.post(f"{API}/files/{step.id}/thumbnail", headers=headers).status_code
        == 415
    )
    assert client.post(f"{API}/files/{document.id}/thumbnail").status_code == 401


def test_a_second_request_waits_while_the_same_drawing_is_being_drawn(
    pieces: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two requests of one PDF never meet in the middle of a drawing."""
    document = pieces["files"]["base/plan_base.pdf"]
    started, release = threading.Event(), threading.Event()
    original = thumbnails.convert

    def slow(source: Path, partial: Path, page: int) -> None:
        started.set()
        assert release.wait(10)
        original(source, partial, page)

    monkeypatch.setattr(thumbnails, "convert", slow)
    results: list[Any] = []
    first = threading.Thread(
        target=lambda: results.append(thumbnails.prepare(document))
    )
    first.start()
    assert started.wait(10)
    # Same document, generation in progress: "busy", not an error.
    assert thumbnails.prepare(document)[0] == "busy"
    release.set()
    first.join(10)
    assert results and results[0][0] == "ready"
    folder = thumbnails.thumbnail_directory(document.id)
    assert len(list(folder.glob("*.png"))) == 1
    assert not list(folder.glob("*.part"))
    assert thumbnails.prepare(document)[0] == "ready"


def test_a_failed_or_slow_drawing_does_not_leave_the_document_blocked(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    pieces: Any,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
) -> None:
    headers = superuser_token_headers
    document = pieces["files"][f"tapa_{pieces['token']}.pdf"]
    url = f"{API}/files/{document.id}/thumbnail"
    folder = thumbnails.thumbnail_directory(document.id)
    # Past the time limit the child process is stopped and the lock released.
    monkeypatch.setattr(thumbnails, "TIMEOUT_SECONDS", 0.001)
    slow = client.post(url, headers=headers)
    assert slow.status_code == 504, slow.text
    assert not list(folder.glob("*.part")) and not list(folder.glob("*.png"))
    monkeypatch.setattr(thumbnails, "TIMEOUT_SECONDS", 60)
    # A damaged PDF fails in the child process, with its message.
    original = (
        pieces["root"] / pieces["part"].folder_path / f"tapa_{pieces['token']}.pdf"
    )
    original.write_bytes(b"not a pdf")
    later = original.stat().st_mtime + 10
    os.utime(original, (later, later))
    document.source_version = stamp(original)
    db.add(document)
    db.commit()
    broken = client.post(url, headers=headers)
    assert broken.status_code == 422, broken.text
    assert "No se puede generar la miniatura" in broken.json()["detail"]
    assert not list(folder.glob("*.part"))
    # Repaired: the same document can be drawn at once.
    write_pdf(original, "repaired")
    os.utime(original, (later + 10, later + 10))
    document.source_version = stamp(original)
    db.add(document)
    db.commit()
    repaired = client.post(url, headers=headers)
    assert repaired.status_code == 200 and repaired.json()["state"] == "ready"
    assert len(list(folder.glob("*.png"))) == 1


def test_drawings_linked_as_reference_or_feature_file_are_listed(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pieces without a managed file list show the drawings their page shows."""
    from app.knowledge_models import PartReference
    from app.models import FeatureAsset
    from tests.utils.feature import create_random_feature

    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    token = uuid.uuid4().hex[:8]
    by_reference, by_feature = create_random_part(db), create_random_part(db)
    feature = create_random_feature(db)
    drawings = []
    for part, name in ((by_reference, "ref"), (by_feature, "asset")):
        part.files_managed = False
        drawing = StoredFile(
            filename=f"{name}_{token}.pdf",
            source="local",
            source_key=settings.ASSETS_SOURCE_ID,
            source_path=f"{name}_{token}.pdf",
            content_type="application/pdf",
        )
        db.add_all([part, drawing])
        drawings.append(drawing)
    db.flush()
    db.add_all(
        [
            PartReference(
                part_id=by_reference.id, kind="drawing", file_id=drawings[0].id
            ),
            FeatureAsset(
                feature_id=feature.id,
                part_id=by_feature.id,
                file_id=drawings[1].id,
                kind="drawing",
                name="Plano",
            ),
        ]
    )
    db.commit()
    headers = superuser_token_headers
    for part, drawing in zip((by_reference, by_feature), drawings, strict=True):
        page = client.get(f"{API}/parts/{part.id}/detail", headers=headers).json()
        assert drawing.filename in {item["file"]["filename"] for item in page["files"]}
        listed = client.get(
            f"{API}/catalog/drawings",
            headers=headers,
            params={"part_id": str(part.id)},
        ).json()
        assert [card["file"]["id"] for card in listed["data"]] == [str(drawing.id)]
        assert listed["data"][0]["primary"] is True
