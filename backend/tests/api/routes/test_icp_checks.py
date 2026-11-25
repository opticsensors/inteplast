"""«Globos verificados con .icp» through the API, and «Documentación de retoques»."""

import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import icp_checks
from app.core.config import settings
from app.file_sources import stamp
from app.ingestion import icp
from app.knowledge_models import PartDocument
from app.models import StoredFile
from tests.ingestion.test_icp import grid, project
from tests.ingestion.test_icp_verification import sheet
from tests.utils.feature import create_random_part

API = settings.API_V1_STR


@pytest.fixture
def drawing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: Session
) -> dict[str, Any]:
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", False)
    part = create_random_part(db)
    part.folder_path = f"Piece {part.code}"
    folder = tmp_path / part.folder_path / "balloned"
    folder.mkdir(parents=True)
    stamps = grid()
    pdf = sheet(folder / "plan.pdf", stamps)
    (folder / "plan.icp").write_bytes(project(stamps))
    bare_folder = tmp_path / part.folder_path / "plain"
    bare_folder.mkdir()
    bare = sheet(bare_folder / "other.pdf", stamps)
    documents = {}
    for key, path in (("plan", pdf), ("bare", bare)):
        documents[key] = StoredFile(
            filename=path.name,
            source="local",
            source_key=settings.ASSETS_SOURCE_ID,
            source_path=path.relative_to(tmp_path).as_posix(),
            source_version=stamp(path),
            content_type="application/pdf",
        )
    db.add_all([part, *documents.values()])
    db.flush()
    for document in documents.values():
        db.add(PartDocument(part_id=part.id, file_id=document.id))
    db.commit()
    return {"part": part, "pdf": pdf, "folder": folder, **documents}


def check(client: TestClient, headers: dict[str, str], document: StoredFile) -> Any:
    response = client.post(f"{API}/files/{document.id}/icp-check", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_drawing_is_checked_once_per_version_of_it_and_its_projects(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    drawing: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = superuser_token_headers
    calls: list[Path] = []
    original = icp_checks.run

    def counted(pdf: Path, projects: list[list[str]], output: Path) -> None:
        calls.append(pdf)
        original(pdf, projects, output)

    monkeypatch.setattr(icp_checks, "run", counted)
    assert client.post(f"{API}/files/{drawing['plan'].id}/icp-check").status_code == 401
    assert check(client, headers, drawing["plan"]) == {
        "state": "ready",
        "verified": True,
    }
    assert check(client, headers, drawing["plan"])["verified"] is True
    assert len(calls) == 1  # The second answer comes from the cache.
    # A changed project is another check: here its stamps no longer fall on the rings.
    moved = [
        icp.Stamp(
            s.number, s.label, ((s.points[0][0] + 23, s.points[0][1] - 17), s.points[1])
        )
        for s in grid()
    ]
    (drawing["folder"] / "plan.icp").write_bytes(project(moved))
    later = (drawing["folder"] / "plan.icp").stat().st_mtime + 10
    os.utime(drawing["folder"] / "plan.icp", (later, later))
    assert check(client, headers, drawing["plan"])["verified"] is False
    assert len(calls) == 2
    folder = icp_checks.check_directory(drawing["plan"].id)
    assert len(list(folder.glob("*.json"))) == 1
    assert not list(folder.glob("*.part"))


def test_a_drawing_without_projects_is_answered_without_rendering(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    drawing: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def never(*_: Any) -> None:
        raise AssertionError("no project: nothing to render")

    monkeypatch.setattr(icp_checks, "run", never)
    assert check(client, superuser_token_headers, drawing["bare"]) == {
        "state": "ready",
        "verified": False,
    }


def test_busy_slots_and_a_slow_check_leave_the_drawing_free(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    drawing: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = superuser_token_headers
    taken = 0
    while icp_checks.SLOTS.acquire(blocking=False):
        taken += 1
    try:
        assert check(client, headers, drawing["plan"]) == {
            "state": "busy",
            "verified": None,
        }
    finally:
        for _ in range(taken):
            icp_checks.SLOTS.release()
    monkeypatch.setattr(icp_checks, "TIMEOUT_SECONDS", 0.001)
    url = f"{API}/files/{drawing['plan'].id}/icp-check"
    assert client.post(url, headers=headers).status_code == 504
    folder = icp_checks.check_directory(drawing["plan"].id)
    assert not list(folder.glob("*.part")) and not list(folder.glob("*.json"))
    monkeypatch.setattr(icp_checks, "TIMEOUT_SECONDS", 180)
    assert check(client, headers, drawing["plan"])["verified"] is True


def read(state: str, corrections: str) -> dict[str, Any]:
    return {
        "state": state,
        "imported": 0,
        "skipped": 0,
        "measurements": {"context_key": "", "files": []},
        "notices": [],
        "files": [],
        "corrections_state": corrections,
    }


@pytest.mark.parametrize(
    ("last_read", "expected", "missing"),
    [
        (None, False, False),
        (
            {"state": "ready", "measurements": {"context_key": "", "files": []}},
            False,
            False,
        ),
        (read("ready", "empty"), False, True),
        (read("error", "empty"), False, False),
        (read("partial", "needs_review"), True, False),
        (read("processing", "queued"), True, False),
        (read("partial", "error"), True, False),
    ],
)
def test_correction_documents_are_shown_as_available(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    last_read: dict[str, Any] | None,
    expected: bool,
    missing: bool,
) -> None:
    part = create_random_part(db)
    part.last_read = last_read
    db.add(part)
    db.commit()
    detail = client.get(
        f"{API}/parts/{part.id}/detail", headers=superuser_token_headers
    ).json()
    assert detail["part"]["corrections_documented"] is expected
    assert detail["part"]["corrections_missing"] is missing
    assert uuid.UUID(detail["part"]["id"]) == part.id


def test_a_project_arriving_during_the_check_discards_its_result(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    drawing: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The key and the check use the same projects; a change in between asks again."""
    headers = superuser_token_headers
    original = icp_checks.run

    def arriving(pdf: Path, projects: list[list[str]], output: Path) -> None:
        original(pdf, projects, output)
        # A second project, fitting as well, lands while the first one was being read.
        (drawing["folder"] / "copy.icp").write_bytes(project(grid()))

    monkeypatch.setattr(icp_checks, "run", arriving)
    first = check(client, headers, drawing["plan"])
    assert first == {"state": "busy", "verified": None}
    folder = icp_checks.check_directory(drawing["plan"].id)
    assert not list(folder.glob("*.json")) and not list(folder.glob("*.part"))
    monkeypatch.setattr(icp_checks, "run", original)
    # Checked from scratch with both projects: two fit, so nothing is verified.
    assert check(client, headers, drawing["plan"]) == {
        "state": "ready",
        "verified": False,
    }


def test_a_positive_cached_by_the_previous_rule_is_checked_again(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    drawing: Any,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    tmp_path: Path,
) -> None:
    """v1 accepted a multi-page sheet with other numbers; v2 must not reuse that answer."""
    from app.evidence import drawing_project_snapshot
    from tests.ingestion.test_icp_verification import renumbered

    folder = tmp_path / drawing["part"].folder_path / "two-pages"
    folder.mkdir()
    stamps = grid()
    pdf = sheet(folder / "set.pdf", stamps, pages=2)
    (folder / "set.icp").write_bytes(project(renumbered(stamps, 100)))
    document = StoredFile(
        filename=pdf.name,
        source="local",
        source_key=settings.ASSETS_SOURCE_ID,
        source_path=pdf.relative_to(tmp_path).as_posix(),
        source_version=stamp(pdf),
        content_type="application/pdf",
    )
    db.add(document)
    db.flush()
    db.add(PartDocument(part_id=drawing["part"].id, file_id=document.id))
    db.commit()
    # The answer the previous rule left on disk for this very drawing and project.
    current = icp_checks.RECIPE
    monkeypatch.setattr(icp_checks, "RECIPE", "icp-verification-v1")
    old_key = icp_checks.check_key(document, drawing_project_snapshot(document)[1])
    # Back to the version in the code: if it were still v1, the old answer would be used.
    monkeypatch.setattr(icp_checks, "RECIPE", current)
    directory = icp_checks.check_directory(document.id)
    directory.mkdir(parents=True, exist_ok=True)
    stale = directory / f"{old_key}.json"
    stale.write_text(
        '{"verified": true, "pages": [{"page": 1, "project": "set.icp"}],'
        ' "unreadable": []}',
        encoding="utf-8",
    )
    calls: list[Path] = []
    original = icp_checks.run

    def counted(pdf: Path, projects: list[list[str]], output: Path) -> None:
        calls.append(pdf)
        original(pdf, projects, output)

    monkeypatch.setattr(icp_checks, "run", counted)
    assert check(client, superuser_token_headers, document) == {
        "state": "ready",
        "verified": False,
    }
    assert len(calls) == 1  # Checked again, not read from the old answer.
    assert not stale.exists()
