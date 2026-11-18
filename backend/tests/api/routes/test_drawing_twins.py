"""`.icp` of a drawing: its own folder first, then byte-identical copies in its piece."""

import os
from pathlib import Path

import pytest
from sqlmodel import Session

from app.core.config import settings
from app.evidence import drawing_key, drawing_project_files
from app.file_sources import stamp
from app.knowledge_models import PartDocument
from app.models import StoredFile
from app.part_setup import discover
from tests.utils.feature import create_random_part

DRAWING = b"%PDF the drawing"


@pytest.fixture
def piece(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: Session):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", False)
    part = create_random_part(db)
    part.folder_path = f"Piece {part.code}"
    root = tmp_path / part.folder_path
    (root / "Ballooned").mkdir(parents=True)
    drawing = root / "Ballooned" / "plan_balloned.pdf"
    drawing.write_bytes(DRAWING)
    document = StoredFile(
        filename="plan_balloned.pdf",
        source="local",
        source_key=settings.ASSETS_SOURCE_ID,
        source_path=f"{part.folder_path}/Ballooned/plan_balloned.pdf",
        source_version=stamp(drawing),
        content_type="application/pdf",
    )
    db.add_all([part, document])
    db.flush()
    db.add(PartDocument(part_id=part.id, file_id=document.id))
    db.commit()
    return root, document


def test_a_drawing_inherits_the_projects_of_an_identical_copy(piece) -> None:  # type: ignore[no-untyped-def]
    root, document = piece
    alone = drawing_key(document)
    copy = root / "Ballooned" / "885253"
    copy.mkdir()
    (copy / "3202_balloned.pdf").write_bytes(DRAWING)
    (copy / "3202.icp").write_bytes(b"icp of the copy")
    ((name, path),) = drawing_project_files(document)
    assert name == "3202.icp"
    assert Path(path).read_bytes() == b"icp of the copy"
    inherited = drawing_key(document)
    assert inherited != alone

    # Different bytes are a different drawing, even with the same size.
    changed = copy / "3202_balloned.pdf"
    changed.write_bytes(DRAWING.replace(b"the", b"thE"))
    os.utime(changed, ns=(1, 1))  # Another version, whatever the clock resolution.
    assert drawing_project_files(document) == []
    assert drawing_key(document) == alone


def test_the_drawing_folder_keeps_priority_over_copies(piece) -> None:  # type: ignore[no-untyped-def]
    root, document = piece
    copy = root / "copy"
    copy.mkdir()
    (copy / "plan.pdf").write_bytes(DRAWING)
    (copy / "copy.icp").write_bytes(b"icp of the copy")
    (root / "Ballooned" / "own.icp").write_bytes(b"own icp")
    assert [name for name, _ in drawing_project_files(document)] == ["own.icp"]


def test_copies_outside_the_piece_or_unlinked_drawings_inherit_nothing(
    piece, db: Session, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    root, document = piece
    outside = tmp_path / "Other piece"
    outside.mkdir()
    (outside / "plan.pdf").write_bytes(DRAWING)
    (outside / "other.icp").write_bytes(b"icp elsewhere")
    assert drawing_project_files(document) == []
    # A drawing that no piece uses has no piece folder to look into.
    loose = StoredFile(
        filename="plan_balloned.pdf",
        source="local",
        source_key=settings.ASSETS_SOURCE_ID,
        source_path=document.source_path,
        source_version=document.source_version,
    )
    db.add(loose)
    db.commit()
    copy = root / "copy"
    copy.mkdir()
    (copy / "plan.pdf").write_bytes(DRAWING)
    (copy / "copy.icp").write_bytes(b"icp of the copy")
    assert drawing_project_files(loose) == []
    assert [name for name, _ in drawing_project_files(document)] == ["copy.icp"]


def test_projects_with_the_same_name_in_two_copies_are_both_kept(piece) -> None:  # type: ignore[no-untyped-def]
    root, document = piece
    for folder in ("A", "B"):
        (root / folder).mkdir()
        (root / folder / "copy.pdf").write_bytes(DRAWING)
        (root / folder / "plan.icp").write_bytes(folder.encode())
    names = [name for name, _ in drawing_project_files(document)]
    assert names == ["A/plan.icp", "B/plan.icp"]


def test_proposed_drawing_prefers_one_beside_an_icp(piece, db: Session) -> None:  # type: ignore[no-untyped-def]
    root, _document = piece
    folder = root.name
    clean = root / "1- 2D y 3D pieza"
    clean.mkdir()
    (clean / "A plano 2D.pdf").write_bytes(b"%PDF clean")
    proposal = {r.kind: r for r in discover(db, folder).references}
    assert proposal["drawing"].path is None
    (root / "Ballooned" / "plan.icp").write_bytes(b"icp")
    proposal = {r.kind: r for r in discover(db, folder).references}
    assert proposal["drawing"].path is None
    (clean / "A plano 2D.pdf").write_bytes(DRAWING)
    proposal = {r.kind: r for r in discover(db, folder).references}
    assert proposal["drawing"].path == f"{folder}/Ballooned/plan_balloned.pdf"
    # All drawings stay as candidates for the user to choose.
    assert len(proposal["drawing"].candidates) == 2


def test_projects_in_folders_with_the_same_name_reach_the_reader_apart(piece) -> None:  # type: ignore[no-untyped-def]
    root, document = piece
    for revision in ("REV1", "REV2"):
        (root / revision / "copy").mkdir(parents=True)
        (root / revision / "copy" / "copy.pdf").write_bytes(DRAWING)
        (root / revision / "copy" / "plan.icp").write_bytes(revision.encode())
    files = dict(drawing_project_files(document))
    assert sorted(files) == ["REV1/copy/plan.icp", "REV2/copy/plan.icp"]
    # The reader receives both projects, each with its own content.
    assert {Path(path).read_bytes() for path in files.values()} == {b"REV1", b"REV2"}


def test_distinct_names_add_folders_only_when_needed() -> None:
    from app.evidence import distinct_names

    assert distinct_names(["/a/x/p.icp", "/b/y/q.icp"]) == ["p.icp", "q.icp"]
    assert distinct_names(["/a/x/p.icp", "/b/x/p.icp", "/c/y/p.icp"]) == [
        "a/x/p.icp",
        "b/x/p.icp",
        "y/p.icp",
    ]
    assert distinct_names(["/x/p.icp", "/y/x/p.icp"]) == ["/x/p.icp", "y/x/p.icp"]
