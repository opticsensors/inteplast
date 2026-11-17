from app.automatic_measurements import collect
from app.ingestion.measurement_tables import omitted_sheet_review
from tests.ingestion.test_measurement_tables import walked


def test_sheet_exclusion_uses_content_not_the_word_template():
    empty = [["Number", "Target", "Cav_1"]]
    filled = [*empty, [16, 10, 9.95]]
    assert omitted_sheet_review(empty) == "empty_dimensional_template"
    assert omitted_sheet_review(filled) == "unclassified_dimensional_table"
    assert (
        omitted_sheet_review([*empty, [16, "See note", "OK"]])
        == "unclassified_dimensional_table"
    )
    assert omitted_sheet_review([["Photo", "Caption"]]) is None


def test_pending_sheets_and_rejected_rows_remain_visible_alongside_imported_rows(
    tmp_path, monkeypatch
):
    path = tmp_path / "report.xls"
    path.write_bytes(b"synthetic workbook")
    header = ["Nr", "Nominal", "Tol+", "Tol-", "Cav.1"]
    monkeypatch.setattr(
        "app.automatic_measurements.workbook",
        lambda _: [
            ("Template", [header]),
            ("Comparison", [header, [12, 10, 0.1, -0.1, 9.95]]),
            (
                "DR",
                [
                    header,
                    [12, 10, 0.1, -0.1, 9.95],
                    ["A4", 1, 0.1, -0.1, 1.01],
                    [13, 10, -0.2, 0.1, 10],
                ],
            ),
        ],
    )
    issues = {}
    groups = collect(*walked(tmp_path, [path]), file_issues=issues)
    assert sum(map(len, groups.values())) == 1
    assert any("Excluida:" in value for value in issues.values())
    assert any("falta clasificar" in value for value in issues.values())
    assert any(
        "2 filas descartadas" in value and "3, 4" in value for value in issues.values()
    )
