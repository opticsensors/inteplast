"""Synthetic books only: no client documents or cached client measurements."""

import struct
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.ingestion.formula_flags import biff_stream, inspect_formulas, token_flags
from app.ingestion.measurement_tables import report_rows, workbook


def record(code, payload=b""):
    return struct.pack("<HH", code, len(payload)) + payload


def formula(row, col, tokens, cache=0.75):
    return record(
        6, struct.pack("<HHHdHIH", row, col, 0, cache, 0, 0, len(tokens)) + tokens
    )


def book_stream(body):
    bof = record(0x0809, struct.pack("<HH", 0x0600, 5) + bytes(12))
    name = b"DR"
    bound = struct.pack("<IBBB", 0, 0, 0, len(name)) + b"\x00" + name
    offset = len(bof) + 4 + len(bound) + 4
    bound = struct.pack("<I", offset) + bound[4:]
    return (
        bof
        + record(0x85, bound)
        + record(10)
        + record(0x0809, struct.pack("<HH", 0x0600, 0x10) + bytes(12))
        + body
        + record(10)
    )


@pytest.mark.parametrize("token", [0x21, 0x41, 0x61])
def test_direct_rand_uses_tokens_not_incidental_bytes(token):
    a = biff_stream(
        book_stream(
            formula(2, 8, bytes([token, 63, 0]))
            + formula(2, 9, b"\x1f\x41\x3f\x00" + bytes(5))
        )
    )
    assert a.cells["DR", 3, 9]["provenance_state"] == "generado"
    assert "aleatoria" not in a.cells["DR", 3, 10]["flags"]
    assert a.cells["DR", 3, 10]["provenance_state"] == "medicion"


@pytest.mark.parametrize("code,size_offset", [(0x04BC, 8), (0x0221, 12)])
def test_shared_and_array_formulas_follow_anchor_not_entire_row(code, size_offset):
    anchor = b"\x01" + struct.pack("<HH", 4, 9)
    rand = b"\x41\x3f\x00"
    shared = (
        struct.pack("<HHBB", 4, 4, 9, 10)
        + bytes(size_offset - 6)
        + struct.pack("<H", len(rand))
        + rand
    )
    a = biff_stream(
        book_stream(
            formula(4, 9, anchor) + record(code, shared) + formula(4, 10, anchor)
        )
    )
    assert {k for k, v in a.cells.items() if v["provenance_state"] == "generado"} == {
        ("DR", 5, 10),
        ("DR", 5, 11),
    }
    assert ("DR", 5, 9) not in a.cells  # the original measurement is untouched


def test_external_random_function_requires_name_and_function_call():
    name = b"\x39" + struct.pack("<HI", 0, 1)
    args = b"\x1e\x01\x00\x1e\x02\x00"
    call = b"\x42\x03\xff\x00"
    assert token_flags(name + args + call, {}, {(0, 1): "RANDBETWEEN"}) == ["aleatoria"]
    assert token_flags(b"\x17\x06\x00RAND()", {}, {}) == []
    assert token_flags(b"\x18", {}, {}) == ["formula_no_interpretada"]


def write_xlsx(path: Path, body: str):
    with ZipFile(path, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="CAV_1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + body
            + "</sheetData></worksheet>",
        )


def test_ooxml_shared_random_missing_cache_and_literal_text(tmp_path):
    path = tmp_path / "synthetic.xlsm"
    write_xlsx(
        path,
        '<row r="1"><c r="A1"><f t="shared" si="0" ref="A1:B1">RAND()</f><v>0.5</v></c><c r="B1"><f t="shared" si="0"/><v/></c><c r="C1" t="inlineStr"><is><t>=RAND()</t></is></c><c r="D1"><f>"RAND()"</f><v>5</v></c></row>',
    )
    a = inspect_formulas(path)
    assert a.cells["CAV_1", 1, 1]["provenance_state"] == "generado"
    assert a.cells["CAV_1", 1, 2]["flags"] == ["aleatoria", "formula_sin_valor"]
    assert ("CAV_1", 1, 3) not in a.cells
    assert "aleatoria" not in a.cells["CAV_1", 1, 4]["flags"]


def test_array_output_cells_are_not_mistaken_for_literal_measurements(tmp_path):
    path = tmp_path / "array.xlsx"
    write_xlsx(
        path,
        '<row r="1"><c r="A1"><f t="array" ref="A1:B1">RAND()</f><v>0.1</v></c><c r="B1"><v>0.2</v></c><c r="C1"><v>3</v></c></row>',
    )
    audit = inspect_formulas(path)
    assert audit.cells["CAV_1", 1, 2]["provenance_state"] == "generado"
    assert ("CAV_1", 1, 3) not in audit.cells


def test_named_formulas_are_unconfirmed_until_their_definition_is_resolved():
    assert token_flags(b"\x23\x01\x00\x00\x00", {1: "HiddenGenerator"}, {}) == [
        "nombre_o_funcion_no_resuelto"
    ]


def test_dependencies_follow_references_and_shared_offsets(tmp_path):
    path = tmp_path / "dependencies.xlsx"
    write_xlsx(
        path,
        """<row r="1">
      <c r="A1"><f>RAND()</f><v>0.1</v></c>
      <c r="B1"><f>A1*2</f><v>0.2</v></c>
      <c r="C1"><f>B1+1</f><v>1.2</v></c>
      <c r="D1"><f>F1</f><v>7</v></c><c r="F1"><v>7</v></c>
      <c r="G1"><f>INDIRECT("A1")</f><v>0.1</v></c>
      <c r="H1"><f>I1</f><v>1</v></c><c r="I1"><f>H1</f><v>1</v></c>
      <c r="J1"><f t="shared" si="0" ref="J1:K1">A1</f><v>0.1</v></c>
      <c r="K1"><f t="shared" si="0"/><v>0.2</v></c>
    </row>""",
    )
    a = inspect_formulas(path)
    assert a.cells["CAV_1", 1, 4]["provenance_state"] == "medicion"
    for c in (2, 3, 7, 8, 9, 10, 11):
        assert a.cells["CAV_1", 1, c]["provenance_state"] == "sin_confirmar"


def test_biff_empty_cache_has_precise_label():
    body = bytearray(formula(0, 0, b"\x1e\x01\x00"))
    body[10:18] = b"\x03\x00\x00\x00\x00\x00\xff\xff"
    a = biff_stream(book_stream(bytes(body)))
    assert a.cells["DR", 1, 1]["flags"] == ["resultado_vacio"]


def test_generator_copy_requires_all_three_conditions():
    from app.ingestion.formula_flags import FormulaAudit
    from app.ingestion.measurement_provenance import possible_generator_copies

    grid = [
        ["", "", "", 1, 2, "NOK", "", "", 2],
        [0, 0, 0, 10, 10.04, "", 0.1, 2, 10.04],
    ]
    audit = FormulaAudit(
        cells={
            ("CAV_1", 2, 9): {
                "flags": ["aleatoria"],
                "formula": "ROUND($D2-$G2+2*$G2*RAND(),$H2)",
            }
        }
    )

    def check():
        return possible_generator_copies("CAV_1", grid, 0, [3, 4], audit)

    assert (2, 5) in check()
    grid[1][4] = 11
    assert not check()
    grid[1][4] = 10.041
    assert not check()
    grid[1][4] = 10.04
    grid[0][8] = 3
    assert not check()
    grid[0][8] = 2
    audit.cells["CAV_1", 2, 5] = {"flags": []}
    assert not check()


def test_copies_preserve_differences_and_never_deduplicate_other_coordinates():
    from copy import deepcopy

    from app.ingestion.measurement_provenance import usable_measurement

    header = ["Nr", "Nominal", "Tol +", "Tol-", "CAV.1", "CAV.2"]
    base = [header, [10, 4, 0.1, -0.1, 3.95, 3.96], [20, 4, 0.1, -0.1, 3.94, 3.96]]
    copy = deepcopy(base)
    copy[1][5] = 3.97
    _, rows = report_rows([("DR", base), ("DR (2)", copy)])
    copied = [r for r in rows if r["_sheet"] == "DR (2)"]
    assert [usable_measurement(r) for r in copied] == [False, True, False, False]
    assert copied[0]["duplicate_of"] == {"sheet": "DR", "cell": "E2"}
    assert copied[1]["flags"] == ["difiere_de_hoja_origen"]
    assert copied[2]["duplicate_of"]["cell"] == "E3"
    copy.append([30, 4, 0.1, -0.1, 3.95, 3.96])
    _, rows = report_rows([("DR", base), ("DR (2)", copy)])
    assert not any("copia" in r["flags"] for r in rows)
    assert any("no se deduplica" in w for r in rows for w in r["warnings"])


@pytest.mark.parametrize("itp", ["732180000", 732180000, 732180000.0, "732180000.0"])
def test_identity_warning_distinguishes_foreign_itp_from_ppap_typo(itp):
    from app.ingestion.measurement_tables import identity_flags

    assert identity_flags(
        [["ITP Ref:", "732470000", "PPAP Ref:", "3247-00_int.01"]], "3288"
    )[0] == ["identidad_otra_pieza"]
    flags, warnings = identity_flags(
        [["ITP Ref:", itp, "PPAP Ref:", "3281-00_int.04"]], "3218"
    )
    assert not flags and warnings
    assert identity_flags([["Part Number:", "11/12/2018"]], "3288")[0] == [
        "cabecera_desplazada"
    ]


def test_customer_template_preserves_degrees_and_each_sample():
    grid = [
        [
            "e_Type",
            "Number",
            "Kind",
            "Type",
            "Target",
            "Tol +",
            "Tol -",
            "Units",
            "Measuring Device",
            1,
            2,
            "NOK",
        ],
        [3, "1-2", "", "min", 11.5, 1, -1, "°", "CT", 11.95, 11.94, 0],
    ]
    _, rows = report_rows([("cav_1", grid)])
    assert [r["value"] for r in rows] == [11.95, 11.94]
    assert {r["unit"] for r in rows} == {"°"}
    assert {r["_variant"] for r in rows} == {"muestra1", "muestra2"}


def test_secondary_forecast_block_is_preserved_but_not_a_measurement():
    labels = [
        "Nr",
        "Nominal",
        "Tol +",
        "Tol-",
        "CAV.1",
        "CAV.2",
        "Retoc",
        "CAV.1",
        "CAV.2",
    ]
    values = [10, 4, 0.1, -0.1, 3.95, 3.96, 0.1, 4.05, 4.06]
    _, rows = report_rows([("DR_100%", [labels, values])])
    assert [r["value"] for r in rows] == [3.95, 3.96, 4.05, 4.06]
    assert [r["provenance_state"] for r in rows] == [
        "medicion",
        "medicion",
        "sin_confirmar",
        "sin_confirmar",
    ]
    assert "bloque_secundario_sin_contexto" in rows[-1]["flags"]


def test_secondary_block_with_explicit_condition_remains_measured():
    titles = ["", "", "", "", "600 bar", "", "", "750 bar", ""]
    labels = ["Nr", "Nominal", "Tol +", "Tol-", "CAV.1", "CAV.2", "", "CAV.1", "CAV.2"]
    values = [10, 4, 0.1, -0.1, 3.95, 3.96, "", 4.05, 4.06]
    _, rows = report_rows([("DR_100%", [titles, labels, values])])
    assert all(r["provenance_state"] == "medicion" for r in rows)
    assert [r["_condition"] for r in rows] == ["600bar", "600bar", "750bar", "750bar"]


def test_forecast_headers_do_not_replace_measured_nominal_or_tolerance():
    labels = [
        "Nr",
        "Nominal",
        "Tol +",
        "Tol-",
        "CAV.1",
        "",
        "Nominal",
        "Tol +",
        "Tol-",
        "CAV.1",
    ]
    values = [10, 2, 0, -0.05, 1.956, "", 1.975, 2, 1.95, 1.98]
    _, rows = report_rows([("DR_100%", [labels, values])])
    assert rows[0]["nominal"] == 2
    assert rows[0]["lower"] == 1.95
    assert rows[0]["upper"] == 2
    assert rows[1]["provenance_state"] == "sin_confirmar"


def test_contiguous_repeated_cavities_without_conditions_are_not_new_measurements():
    labels = ["Nr", "Nominal", "Tol +", "Tol-", "CAV.1", "CAV.2", "CAV.1", "CAV.2"]
    values = [10, 4, 0.1, -0.1, 3.95, 3.96, 4.05, 4.06]
    _, rows = report_rows([("DR_100%", [labels, values])])
    assert [r["provenance_state"] for r in rows] == [
        "medicion",
        "medicion",
        "sin_confirmar",
        "sin_confirmar",
    ]


def test_import_keeps_original_cell_and_marks_only_generated_observations(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    labels = [
        "Nr",
        "",
        "type",
        "Nominal",
        "class",
        "Tol +",
        "Tol-",
        "Equipment",
        "Nr.1",
        "Nr.2",
        "Nr.3",
    ]
    header = "".join(
        f'<c r="{chr(65 + i)}1" t="inlineStr"><is><t>{s}</t></is></c>'
        for i, s in enumerate(labels)
    )
    body = (
        '<row r="1">'
        + header
        + '</row><row r="2"><c r="A2"><v>12</v></c><c r="D2"><v>10</v></c><c r="F2"><v>1</v></c><c r="G2"><v>-1</v></c><c r="I2"><v>9.9</v></c><c r="J2"><f>RAND()+9</f><v>9.8</v></c><c r="K2"><f>J2*2</f><v>19.6</v></c></row>'
    )
    write_xlsx(path, body)
    _, rows = report_rows(workbook(path))
    assert [r["value"] for r in rows] == [9.9, 9.8, 19.6]
    assert [r["provenance_state"] for r in rows] == [
        "medicion",
        "generado",
        "sin_confirmar",
    ]
    assert all(r["warnings"] for r in rows)
    assert len({r["_variant"] for r in rows}) == 3


def test_signature_is_checked_before_selecting_excel_reader(tmp_path):
    path = tmp_path / "disguised.xls"
    path.write_bytes(b"%PDF-1.7\nsynthetic")
    with pytest.raises(ValueError, match="Contenido PDF"):
        workbook(path)
    path.write_bytes(b"PK\x03\x04")
    with pytest.raises(ValueError, match="firma ooxml"):
        workbook(path)


def test_assistant_keeps_exclusion_count_and_never_aggregates_generated_values():
    from app.assistant.summaries import measurements

    records = {
        "01": {"value": 2.0, "provenance_state": "medicion"},
        "02": {"value": 999.0, "provenance_state": "generado", "flags": ["aleatoria"]},
        "03": {"value": 1000.0, "provenance_state": "sin_confirmar"},
        "04": {
            "value": 2.0,
            "provenance_state": "medicion",
            "flags": ["copia"],
            "duplicate_of": {"sheet": "DR", "cell": "I15"},
        },
    }
    summary, aggregates, rows = measurements(
        [{"id": "N12", "series": [{"id": "s", "records": {"c1": records}}]}],
        cavity=None,
        sample=None,
    )
    assert aggregates[0]["mean"] == 2
    assert aggregates[0]["numeric_count"] == 1
    assert summary["excluded_count"] == 3
    assert summary["duplicate_count"] == 1
    assert summary["measurement_count"] == 1
    assert [r["value"] for r in rows] == [2.0, None, None, None]
    assert rows[-1]["duplicate_of"] == {"sheet": "DR", "cell": "I15"}
    from app.assistant.answers import measurement_answer

    answer = measurement_answer(
        "Qué mediciones hay", {"part": "synthetic", "summary": summary, "rows": []}
    )
    assert "3 valores excluidos" in answer
    assert "999" not in answer
