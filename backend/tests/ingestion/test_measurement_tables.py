from pathlib import Path

import pytest

from app.automatic_measurements import collect, path_context
from app.ingestion.measurement_tables import csv_rows, report_rows, workbook


@pytest.mark.parametrize("prefix", [";;;;;", ";;;;;;"])
def test_comparative_csv_reads_each_cavity_without_using_a_measurement_as_tolerance(
    prefix,
):
    data = (
        f"N720 diameter{prefix}c1-24;c3-24\n5;Diameter;;29.2;"
        + ("-0.05;-0.15;" if len(prefix) == 6 else ";")
        + "29.033;29.04\n"
    )
    rows = csv_rows(data.encode())
    assert [(r["_cavity"], r["_variant"], r["value"]) for r in rows] == [
        ("c1", "24", 29.033),
        ("c3", "24", 29.04),
    ]
    assert [r["tol_inf"] for r in rows] == (
        [-0.15, -0.15] if len(prefix) == 6 else [None, None]
    )
    assert all(r["line"] == 2 for r in rows)


@pytest.mark.parametrize(
    "path,sample,cavity,variant,condition",
    [
        (
            "Support_intern.02/140ºC/600bar/C4.2/3197.csv",
            "02",
            "c4",
            "2",
            "140c.600bar",
        ),
        ("Support_intern.03/c1-3197.csv", "03", "c1", "", ""),
        ("Support_intern.03/c5.1-3197.csv", "03", "c5", "1", ""),
        ("Support_intern.03/c5bis-3197.csv", "03", "c5", "bis", ""),
        ("Support_intern.06/3197_c1-24.csv", "06", "c1", "24", ""),
        ("Support_intern.08/3197_totes_nozzle 55.csv", "08", "", "", "nozzle55c"),
    ],
)
def test_context_separates_conditions_and_repetitions_without_confusing_part_number(
    path, sample, cavity, variant, condition
):
    context = path_context(path, "3197")
    assert (
        context["sample"],
        context["cavity"],
        context["variant"],
        context["condition"],
    ) == (sample, cavity, variant, condition)


def report():
    return [
        ["Drawing nº Level:", "'REV-ABC"],
        ["Nr", "", "", "", "", "", "", "135ºC 500bar", "", "140ºC 600bar", ""],
        [
            "",
            "LTR",
            "type",
            "Nominal",
            "Tol +",
            "Tol-",
            "Equipment",
            "CAV.1",
            "CAV.2",
            "CAV.1",
            "CAV.2",
        ],
        [720, "", "GX", 29.2, -0.05, -0.15, "CMM", 29.033, 29.04, 29.08, "-"],
        [740.3, "", "Rz", 10, 2, -10, "ROUGHNESS", 0, 8.2, "OK", "#REF!"],
        [750, "", "", 10, 0.1, -0.1, "IMPOSED", 10, 10, 10, 10],
    ]


def test_ppap_uses_header_columns_and_measured_cells_only():
    revision, rows = report_rows([("DR_PAR", report()), ("DR(100%)", report())])
    assert revision == "REV-ABC"
    assert [r["value"] for r in rows] == [29.033, 29.04, 29.08, 0, 8.2]
    assert rows[2]["_condition"] == "140c.600bar"
    assert rows[0]["_cell"] == "H4"
    assert rows[3]["numbers"] == ["N740.3"]
    assert rows[3]["unit"] == "µm"
    assert rows[0]["lower"] == pytest.approx(29.05)


def test_xlsx_reads_cached_values_and_ignores_excel_errors(tmp_path: Path):
    from zipfile import ZipFile

    path = tmp_path / "table.xlsx"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="DR" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="2"><c r="B2"><f>1+2</f><v>3</v></c><c r="C2" t="e"><v>#REF!</v></c></row></sheetData></worksheet>',
        )
    assert workbook(path) == [("DR", [[], ["", "3", None]])]


def test_collect_keeps_unidentified_context_explicit_and_skips_correction_forecasts(
    tmp_path: Path,
):
    data = b"N12 diameter\n1;Diameter;;10;0.1;-0.1;9.95;-0.05;;\n"
    (tmp_path / "report.csv").write_bytes(data)
    (tmp_path / "corrections.csv").write_bytes(data)
    groups = collect(tmp_path, list(tmp_path.iterdir()))
    assert len(groups) == 1
    (revision, sample, cavity), rows = next(iter(groups.items()))
    assert revision == "sin-revision" and cavity == "sin-cavidad"
    assert sample.startswith("archivo-")
    assert len(rows) == 1


def test_csv_priority_and_missing_comparative_tolerances_use_matching_report(
    tmp_path, monkeypatch
):
    import app.automatic_measurements as automatic

    root = tmp_path / "3197 Pot"
    directory = root / "intern.02" / "135ºC" / "500bar"
    directory.mkdir(parents=True)
    comparison = directory / "totes.csv"
    comparison.write_bytes(b"N720 diameter;;;;;c1;c2\n5;Diameter;;29.2;;29.01;29.04\n")
    report_file = root / "intern.02.xls"
    report_file.write_bytes(b"report fixture")
    monkeypatch.setattr(automatic, "workbook", lambda _: [("DR_PAR", report())])
    groups = collect(root, [comparison, report_file])
    row = groups["REV-ABC", "02.135c.500bar", "c1"][0]
    assert row["value"] == 29.01
    assert row["tol_inf"] == -0.15 and row["tol_sup"] == -0.05
    assert row["tolerance_source"]["locator"] == "DR_PAR!H4"
    individual = directory / "c1.csv"
    individual.write_bytes(
        b"N720 diameter\n5;Diameter;;29.2;-0.05;-0.15;29.08;-0.12;;\n"
    )
    rows = collect(root, [comparison, report_file, individual])[
        "REV-ABC", "02.135c.500bar", "c1"
    ]
    assert [r["value"] for r in rows if r["numbers"] == ["N720"]] == [29.08]


def test_changing_source_during_read_aborts_instead_of_publishing_mixed_values(
    tmp_path, monkeypatch
):
    from fastapi import HTTPException

    import app.automatic_measurements as automatic

    path = tmp_path / "test.csv"
    path.write_bytes(b"original")

    def changing_reader(*_args, **_kwargs):
        path.write_bytes(b"changed during read")
        return []

    monkeypatch.setattr(automatic, "csv_rows", changing_reader)
    with pytest.raises(HTTPException) as error:
        collect(tmp_path, [path])
    assert error.value.status_code == 409
