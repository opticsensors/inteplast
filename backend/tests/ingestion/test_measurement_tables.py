from pathlib import Path

import pytest

from app.automatic_measurements import collect, path_context
from app.ingestion.measurement_tables import csv_rows, report_rows, workbook
from app.source_types import SourceItem


def walked(root: Path, paths: list[Path]) -> tuple[str, list[SourceItem]]:
    """A piece folder as `part_setup.folder_files` lists it locally."""
    return root.name, [
        SourceItem(path=f"{root.name}/{p.relative_to(root).as_posix()}", local=p)
        for p in paths
    ]


@pytest.mark.parametrize("unsupported", [True, False])
def test_unsupported_book_is_a_file_issue_but_programming_errors_are_not(
    tmp_path, monkeypatch, unsupported
):
    from fastapi import HTTPException

    from app.ingestion.formula_flags import UnsupportedWorkbook

    path = tmp_path / "example.xls"
    path.write_bytes(b"synthetic")

    def fail(_):
        raise (
            UnsupportedWorkbook("BIFF5 no soportado")
            if unsupported
            else ValueError("unexpected defect")
        )

    monkeypatch.setattr("app.automatic_measurements.workbook", fail)
    folder, items = walked(tmp_path, [path])
    issues = {}
    if unsupported:
        assert collect(folder, items, file_issues=issues) == {}
        assert "BIFF5" in issues["example.xls"]
    else:
        with pytest.raises(HTTPException, match="unexpected defect"):
            collect(folder, items, file_issues=issues)
        assert not issues


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


def test_comparative_title_on_its_first_value_line_does_not_inherit_the_previous_cota():
    # 3212 "totes": the individual export writes each POINT title on its own line.
    wide = (
        "N178 PLAN. 0.10 MAX.;;;;;;c13;c14\n"
        "11;Planitud;;0;0.1;0;0.061;0.073\n"
        "POINT 1 -> 1.35-0.05 MIN/MAX;Cálculo de fórmula;;1.35;0;-0.05;1.447;1.467\n"
        ";Cálculo de fórmula;;1.35;0;-0.05;1.467;1.478\n"
        "N165 MIN. / MAX.;;;;;;;\n"
        "2;Posición Y;;1.35;0;-0.05;1.427;1.43\n"
    ).encode("cp1252")
    individual = (
        "N178 PLAN. 0.10 MAX.\n"
        "11;Planitud;;0.000;0.100;0.000;0.061;0.061; ;--\n"
        "POINT 1 -> 1.35-0.05 MIN/MAX\n"
        ";Cálculo de fórmula;;1.350;0.000;-0.050;1.447;0.097;0.097;--\n"
        ";Cálculo de fórmula;;1.350;0.000;-0.050;1.467;0.117;0.117;--\n"
        "N165 MIN. / MAX.\n"
        "2;Posición Y;;1.350;0.000;-0.050;1.427;0.077;0.077;--\n"
    ).encode("cp1252")

    rows = csv_rows(wide)
    # Without a pilot mapping a POINT block has no cota: it is not attributed to N178.
    assert [(r["_cavity"], r["numbers"], r["value"], r["line"]) for r in rows] == [
        ("c13", ["N178"], 0.061, 2),
        ("c13", ["N165"], 1.427, 6),
        ("c14", ["N178"], 0.073, 2),
        ("c14", ["N165"], 1.43, 6),
    ]

    def identity(row):
        return row["series_id"], row["numbers"], row["title"], row["value"]

    pilot = [r for r in csv_rows(wide, pilot=True) if r["_cavity"] == "c13"]
    assert [(r["title"], r["value"]) for r in pilot if r["line"] in {3, 4}] == [
        ("POINT 1 -> 1.35-0.05 MIN/MAX", 1.447),
        ("POINT 1 -> 1.35-0.05 MIN/MAX", 1.467),
    ]
    # Same blocks, cotas and series as the individual export of that cavity.
    assert [identity(r) for r in pilot] == [
        identity(r) for r in csv_rows(individual, pilot=True)
    ]


@pytest.mark.parametrize(
    "header,row,tolerances",
    [
        # 3197 intern.03: second language and a blank separator before the cavities.
        (
            "N720 diameter;;;;;;;c1;c2",
            "5;Diámetro;Durchmesser;29.2;-0.05;-0.15;;29.036;29.047",
            (-0.15, -0.05),
        ),
        # 3197 intern.08 "nozzle": no second language; the first cavity is column 5.
        ("N720.1 diameter;;;;c1;c2", "6;Diámetro;29.2;;29.036;29.047", (None, None)),
        # One-sided limit.
        (
            "N720 diameter;;;;;;c1;c2",
            "5;Diámetro;;29.2;;-0.15;29.036;29.047",
            (-0.15, None),
        ),
    ],
)
def test_comparative_csv_locates_nominal_and_tolerances_in_each_layout(
    header, row, tolerances
):
    rows = csv_rows(f"{header}\n{row}\n".encode("cp1252"))
    assert [(r["_cavity"], r["nominal"], r["value"]) for r in rows] == [
        ("c1", 29.2, 29.036),
        ("c2", 29.2, 29.047),
    ]
    assert {(r["tol_inf"], r["tol_sup"]) for r in rows} == {tolerances}


def test_comparative_csv_with_unknown_leading_columns_is_pending_not_guessed(tmp_path):
    from app.ingestion.measurement_csv import UnsupportedMeasurementCsv

    data = (
        b"N720 diameter;;;;;;;;c1;c2\n5;Diameter;;29.2;-0.05;-0.15;0.3;;29.036;29.047\n"
    )
    with pytest.raises(UnsupportedMeasurementCsv, match="línea 2"):
        csv_rows(data)
    path = tmp_path / "totes.csv"
    path.write_bytes(data)
    issues: dict[str, str] = {}
    folder, items = walked(tmp_path, [path])
    assert collect(folder, items, file_issues=issues) == {}
    assert "columnas no reconocidas" in issues["totes.csv"]


def test_individual_export_never_treats_the_element_column_as_a_title():
    data = b"N12 DIAMETRO\nCIR 1;Diameter;;10;0.1;-0.1;9.95;-0.05;;\n"
    rows = csv_rows(data)
    assert [(r["numbers"], r["title"], r["value"]) for r in rows] == [
        (["N12"], "N12 DIAMETRO", 9.95)
    ]


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
    imposed = [r for r in rows if "valor_impuesto" in r["flags"]]
    assert len(imposed) == 8
    assert all(r["provenance_state"] == "sin_confirmar" for r in imposed)
    assert [r["value"] for r in rows if r not in imposed] == [
        29.033,
        29.04,
        29.08,
        0,
        8.2,
    ] * 2
    assert {r["_sheet"] for r in rows} == {"DR_PAR", "DR(100%)"}
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
    groups = collect(*walked(tmp_path, list(tmp_path.iterdir())))
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
    groups = collect(*walked(root, [comparison, report_file]))
    row = groups["REV-ABC", "02.135c.500bar", "c1"][0]
    assert row["value"] == 29.01
    assert row["tol_inf"] == -0.15 and row["tol_sup"] == -0.05
    assert row["tolerance_source"]["locator"] == "DR_PAR!H4"
    individual = directory / "c1.csv"
    individual.write_bytes(
        b"N720 diameter\n5;Diameter;;29.2;-0.05;-0.15;29.08;-0.12;;\n"
    )
    rows = collect(*walked(root, [comparison, report_file, individual]))[
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
        collect(*walked(tmp_path, [path]))
    assert error.value.status_code == 409
