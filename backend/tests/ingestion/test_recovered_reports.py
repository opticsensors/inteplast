from app.ingestion.formula_flags import FormulaAudit
from app.ingestion.measurement_tables import (
    Workbook,
    flag_repeated_reports,
    report_rows,
)


def table(context="BATCH 123"):
    return [
        ["ITP Ref.", "790000000"],
        ["Nr", "", "", context],
        ["", "Nominal", "Equipment", "CAV.1", "CAV.2", "CAV.3", "CAV.4"],
        [10, 5, "CT-SCAN", 5.1, 5.2, 5.3, 5.4],
        [11, 6, "IMPOSED (reference)", 6.0],
        ["", 12, "CMM", 12.1],
        ["MIN", 1, "CMM", 1],
    ]


def test_recover_distinct_blocks_with_cell_context_and_explicit_numbers():
    grid = table()
    grid += table("80°C humidified")[1:]
    _, rows = report_rows([("trial", grid)], part_code="9000")
    assert {r["_cell"] for r in rows} == {
        "D4",
        "E4",
        "F4",
        "G4",
        "D5",
        "D10",
        "E10",
        "F10",
        "G10",
        "D11",
    }
    assert rows[0]["measurement_context"] == {"text": "BATCH 123", "cell": "D2"}
    new = next(r for r in rows if r["_cell"] == "D10")
    assert new["measurement_context"] == {"text": "80°C humidified", "cell": "D8"}
    assert (
        next(r for r in rows if r["_cell"] == "D5")["provenance_state"]
        == "sin_confirmar"
    )


def test_derived_conflicting_and_unlabelled_values_stay_out():
    numeric = table()
    numeric[2][3:] = [1, 2, 3, 4]
    grid = table()
    grid[3][2] = "CMM forecast"
    for name, data, part in [
        ("DIFFERENCES", table(), "9000"),
        ("trial", table("DIFFERENCES BATCH 123"), "9000"),
        ("trial", table(), "9001"),
        ("trial", numeric, "9000"),
        ("trial", table("mystery"), "9000"),
    ]:
        assert not report_rows([(name, data)], part_code=part)[1]
    assert not any(
        r["_cell"] == "D4" for r in report_rows([("trial", grid)], part_code="9000")[1]
    )


def test_repeated_vector_with_different_lot_preserves_both_sources():
    _, rows = report_rows(
        [("trial", table("BATCH 456")), ("100%", table())], part_code="9000"
    )
    new = next(r for r in rows if r["_sheet"] == "trial" and r["_cell"] == "D4")
    assert new["provenance_state"] == "sin_confirmar"
    assert new["comparison_origin"] == {"sheet": "100%", "cell": "D4"}
    assert (
        next(r for r in rows if r["_sheet"] == "100%" and r["_cell"] == "D4")[
            "provenance_state"
        ]
        == "medicion"
    )


def test_recovered_cached_formula_preserves_audit_and_stays_out_of_measured_values():
    audit = FormulaAudit(cells={("trial", 4, 4): {"formula": "=1+4.1", "flags": []}})
    book = Workbook([("trial", table())], audit)
    _, rows = report_rows(book, part_code="9000")
    formula = next(r for r in rows if r["_cell"] == "D4")
    assert formula["value"] == 5.1 and formula["formula"] == "=1+4.1"
    assert formula["provenance_state"] == "sin_confirmar"
    assert "formula_en_bloque_recuperado" in formula["flags"]


def test_recovered_series_in_distinct_books_and_lots_does_not_inflate_measurements():
    _, a = report_rows([("trial", table("BATCH 20"))], part_code="9000")
    _, b = report_rows([("trial", table("BATCH 21"))], part_code="9000")
    other = table("BATCH 22")
    other[3][-1] = 9.2
    _, c = report_rows([("trial", other)], part_code="9000")
    flag_repeated_reports({"one.xls": a, "two.xls": b, "three.xls": c})
    assert a[0]["comparison_origin"] == {
        "path": "two.xls",
        "sheet": "trial",
        "cell": "D4",
    }
    assert a[0]["provenance_state"] == b[0]["provenance_state"] == "sin_confirmar"
    assert c[0]["provenance_state"] == "medicion"
