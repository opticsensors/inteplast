"""Strict .icp check: synthetic sheets with green rings drawn where the stamps fall."""

from pathlib import Path

import fitz

from app.ingestion import icp
from app.ingestion.icp_verification import verify
from tests.ingestion.test_icp import grid, project, stamp_bytes

A3 = (420 / icp.MM_PER_POINT, 297 / icp.MM_PER_POINT)


def sheet(
    path: Path,
    stamps: list[icp.Stamp],
    *,
    color=(0.0, 0.6, 0.0),
    pages: int = 1,
) -> Path:
    """A3 pages; the first with a ring at the head of every stamp, printed at 1:1."""
    width, height = A3
    with fitz.open() as document:
        page = document.new_page(width=width, height=height)
        for stamp in stamps:
            x, y = stamp.points[0]
            centre = fitz.Point((0.5 + x / 420) * width, (0.5 - y / 297) * height)
            page.draw_circle(centre, 3.5 / icp.MM_PER_POINT, color=color, width=1.5)
            page.insert_text(centre + (-3, 3), stamp.label, fontsize=7)
        for _ in range(pages - 1):
            document.new_page(width=width, height=height).insert_text(
                (60, 60), "OTHER SHEET"
            )
        document.save(path)
    return path


def projects(tmp_path: Path, **files: bytes) -> dict[str, Path]:
    paths = {}
    for name, data in files.items():
        paths[f"{name}.icp"] = tmp_path / f"{name}.icp"
        paths[f"{name}.icp"].write_bytes(data)
    return paths


def test_rings_on_the_stamps_of_the_only_project_verify_the_page(
    tmp_path: Path,
) -> None:
    stamps = grid()
    pdf = sheet(tmp_path / "plan.pdf", stamps)
    result = verify(pdf, projects(tmp_path, plan=project(stamps)))
    assert result["verified"] is True
    (page,) = result["pages"]
    assert page["project"] == "plan.icp"
    # The drawing reader of the app associates the page with it too.
    assert page["association"] == "scale_and_drawn_balloons"
    assert page["rings"] == 24 and page["matched"] == 24
    # Blue rings, the other infra-CONVERT colour, count the same.
    blue = sheet(tmp_path / "blue.pdf", stamps, color=(0.0, 0.2, 0.9))
    assert verify(blue, projects(tmp_path, plan=project(stamps)))["verified"]


def test_a_project_of_another_drawing_is_not_verified(tmp_path: Path) -> None:
    pdf = sheet(tmp_path / "plan.pdf", grid())
    other = grid(first=100)
    moved = [
        icp.Stamp(
            s.number, s.label, ((s.points[0][0] + 23, s.points[0][1] - 17), s.points[1])
        )
        for s in other
    ]
    assert not verify(pdf, projects(tmp_path, other=project(moved)))["verified"]


def test_two_fitting_projects_or_an_unreadable_one_prove_nothing(
    tmp_path: Path,
) -> None:
    stamps = grid()
    pdf = sheet(tmp_path / "plan.pdf", stamps)
    twins = projects(tmp_path, a=project(stamps), b=project(stamps))
    assert not verify(pdf, twins)["verified"]
    broken = projects(
        tmp_path, plan=project(stamps), old=stamp_bytes("7", 7, (0, 0), (1, 1)) * 2
    )
    result = verify(pdf, broken)
    assert not result["verified"] and result["unreadable"] == ["old.icp"]


def test_fewer_than_ten_rings_are_not_enough(tmp_path: Path) -> None:
    stamps = grid(count=8)
    pdf = sheet(tmp_path / "plan.pdf", stamps)
    result = verify(pdf, projects(tmp_path, plan=project(stamps)))
    assert not result["verified"] and result["pages"][0]["rings"] == 8


def test_without_projects_nothing_is_rendered(tmp_path: Path) -> None:
    pdf = sheet(tmp_path / "plan.pdf", grid())
    assert verify(pdf, {}) == {
        "verified": False,
        "pages": [{"page": 1, "rings": 0}],
        "unreadable": [],
    }


def renumbered(stamps: list[icp.Stamp], offset: int) -> list[icp.Stamp]:
    """Same positions, other numbers: another drawing with the same layout."""
    return [
        icp.Stamp(s.number + offset, str(int(s.label) + offset), s.points)
        for s in stamps
    ]


def test_a_multi_page_drawing_with_other_numbers_is_not_verified(
    tmp_path: Path,
) -> None:
    """Balloons 1-24 drawn; the project numbers 101-124 in the same places.

    The rings and the 1:1 fit agree, but without readings the drawing reader does not
    associate a page of a multi-page PDF, so nothing proves which drawing it is.
    """
    stamps = grid()
    pdf = sheet(tmp_path / "plan.pdf", stamps, pages=2)
    result = verify(pdf, projects(tmp_path, other=project(renumbered(stamps, 100))))
    assert not result["verified"]
    first = result["pages"][0]
    assert first["strict"] == "other.icp" and first["matched"] == 24
    assert first["association"] == "no_valid_fit" and "project" not in first
    # The same holds with the right numbers: multi-page PDFs are never verified.
    right = verify(pdf, projects(tmp_path, plan=project(stamps)))
    assert not right["verified"]
