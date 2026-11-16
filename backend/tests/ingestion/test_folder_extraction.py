import pytest
from fastapi import HTTPException

from app import automatic_measurements as measurements
from app.core.config import settings
from app.ingestion.measurement_csv import UnsupportedMeasurementCsv, parse
from app.ingestion.measurement_tables import report_rows
from app.part_setup import reference_candidates, reference_kind
from app.source_types import SourceItem


@pytest.mark.parametrize(
    "path,kind",
    [
        ("1- 2D y 3D pieza/SUPPORT_FUEL_TANK.stp", "part"),
        ("6- Método de medición/balloned/REV.01/base.pdf", "drawing"),
        ("6- Métode de mesura/ballooned/tapa.pdf", "drawing"),
        ("6- Método de medición/REV.02/conjunto balonned.pdf", "drawing"),
        ("4- Metrologia/support intern.01/model.step", None),
        ("support/fixture.step", None),
        ("5- Retoques molde/balloned.pdf", None),
        ("1- 2D y 3D pieza/measurement report.pdf", None),
    ],
)
def test_reference_names_do_not_confuse_product_support_with_support_data(path, kind):
    assert reference_kind(path) == kind


def test_reference_discovery_keeps_all_drawings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", False)
    for name in ("base.pdf", "tapa.pdf"):
        path = tmp_path / "9000/6- Método de medición/balloned" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic PDF candidate")
    candidates, notices = reference_candidates("9000")
    assert len(candidates["drawing"]) == 2
    assert not notices


def test_methods_are_not_read_or_counted_towards_measurement_limits(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "AUTO_MEASUREMENT_MAX_FILE_MB", 1)
    monkeypatch.setattr(settings, "AUTO_MEASUREMENT_MAX_TOTAL_MB", 1)
    method = SourceItem(
        path="9000/6- Método de medición/MM.xls", size=100 * 1024**2, version="v1"
    )
    path = tmp_path / "intern.01.csv"
    path.write_bytes(b"N12 DIAMETRO\n11;Diameter;;10;0.1;-0.1;9.95;-0.05;;\n")
    csv = SourceItem(path="9000/4- Metrologia/intern.01.csv", local=path)
    diagnostics = []
    groups = measurements.collect("9000", [method, csv], diagnostics=diagnostics)
    assert sum(map(len, groups.values())) == 1
    assert (
        next(d for d in diagnostics if d["path"].endswith("MM.xls"))["reason"]
        == "measurement_method"
    )


@pytest.mark.parametrize("limit", ["file", "total"])
def test_configured_limits_still_stop_oversized_imports(limit, monkeypatch):
    monkeypatch.setattr(
        settings, "AUTO_MEASUREMENT_MAX_FILE_MB", 1 if limit == "file" else 4
    )
    monkeypatch.setattr(
        settings, "AUTO_MEASUREMENT_MAX_TOTAL_MB", 1 if limit == "total" else 4
    )
    item = SourceItem(
        path="9000/4- Metrologia/large.xls", size=2 * 1024**2, version="v1"
    )
    with pytest.raises(HTTPException, match="tamaño"):
        measurements.collect("9000", [item])


def test_diagnostics_explain_omissions_without_changing_readings():
    header = ["Nr", "Nominal", "Tol +", "Tol-", "CAV.1"]
    sheets = [
        ("315594", [header, [1, 2, 0.1, -0.1, 2.01]]),
        ("DR", [header, [1, 2, 0.1, -0.1, 2.01], ["D7", 2, 0.1, -0.1, 2.01]]),
        ("DR(base)", [["Nr", "Nominal", "Tol +", "Tol-", 1], [1, 2, 0.1, -0.1, 2.01]]),
    ]
    diagnostics = []
    expected = report_rows(sheets)
    assert report_rows(sheets, diagnostics=diagnostics) == expected
    assert diagnostics[0]["reason"] == "sheet_name_not_supported"
    assert diagnostics[0]["nominal_header_rows"] == [1]
    assert diagnostics[1]["rejected_rows"] == [
        {"row": 3, "code": "D7", "reason": "unsupported_characteristic_code"}
    ]
    assert diagnostics[2]["reason"] == "no_recognized_header_or_cavities"


def test_spc_export_is_recognized_without_guessing_its_measurement_columns():
    with pytest.raises(UnsupportedMeasurementCsv, match="SPC #P#"):
        parse(b"#P#;500;3;1.4;1.45;1.35;mm;1.423;1.423\n")


def test_pending_spc_does_not_abort_other_measurement_files(tmp_path):
    spc = tmp_path / "a.csv"
    spc.write_bytes(b"#P#;500;3;1.4;1.45;1.35;mm;1.423;1.423\n")
    cmm = tmp_path / "b.csv"
    cmm.write_bytes(b"N12 DIAMETRO\n11;Diameter;;10;0.1;-0.1;9.95;-0.05;;\n")
    files = [SourceItem(path=f"9000/{p.name}", local=p) for p in (spc, cmm)]
    issues, diagnostics = {}, []
    groups = measurements.collect(
        "9000", files, file_issues=issues, diagnostics=diagnostics
    )
    assert sum(map(len, groups.values())) == 1
    assert next(iter(groups.values()))[0]["value"] == 9.95
    assert "SPC #P#" in issues["a.csv"]
    assert diagnostics[0]["status"] == "unsupported"
    assert diagnostics[1]["status"] == "read"


def test_invalid_cmm_values_still_abort_instead_of_silently_skipping(tmp_path):
    cmm = tmp_path / "bad.csv"
    cmm.write_bytes(b"N12 DIAMETRO\n11;Diameter;;10;0.1;-0.1;mistake;-0.05;;\n")
    with pytest.raises(HTTPException, match="mistake"):
        measurements.collect(
            "9000", [SourceItem(path="9000/bad.csv", local=cmm)], file_issues={}
        )


def test_pilot_keeps_regular_excel_reports_and_excludes_correction_workbooks(
    tmp_path, monkeypatch
):
    report = tmp_path / "intern.01.xls"
    report.write_bytes(b"synthetic report")
    monkeypatch.setattr(
        measurements,
        "workbook",
        lambda _: [
            (
                "DR",
                [
                    ["Nr", "Nominal", "Tol +", "Tol-", "CAV.1"],
                    [12, 10, 0.1, -0.1, 9.95],
                ],
            )
        ],
    )
    files = [
        SourceItem(path="3212 Pump Housing/4- Metrologia/intern.01.xls", local=report),
        SourceItem(path="3212 Pump Housing/5- Retoques de molde/forecast.xls"),
    ]
    diagnostics = []
    groups = measurements.collect(
        "3212 Pump Housing", files, pilot=True, file_issues={}, diagnostics=diagnostics
    )
    assert sum(map(len, groups.values())) == 1
    row = next(iter(groups.values()))[0]
    assert row["numbers"] == ["N12"] and row["value"] == 9.95
    assert row["source"]["locator"] == "DR!E2"
    assert diagnostics[0]["status"] == "read"
    assert diagnostics[1]["reason"] == "correction_folder"


def test_empty_pilot_excel_is_reported_as_pending(tmp_path, monkeypatch):
    report = tmp_path / "intern.01.xls"
    report.write_bytes(b"synthetic report")
    monkeypatch.setattr(measurements, "workbook", lambda _: [("DR", [])])
    issues = {}
    measurements.collect(
        "3212 Pump Housing",
        [SourceItem(path="3212 Pump Housing/intern.01.xls", local=report)],
        pilot=True,
        file_issues=issues,
    )
    assert "Pendiente:" in issues["intern.01.xls"]


def test_completed_correction_job_does_not_hide_measurement_pending():
    from types import SimpleNamespace
    from unittest.mock import Mock

    from app.models import Part
    from app.part_reading import read_report

    part = Part(
        code="3212",
        name="Pilot",
        last_read={
            "state": "processing",
            "corrections_state": "queued",
            "corrections_key": "key",
            "measurements": {"context_key": "", "files": []},
            "files": [
                {
                    "path": "pending.csv",
                    "group": "measurements",
                    "status": "Pendiente: SPC",
                }
            ],
        },
    )
    session = Mock()
    session.get.return_value = SimpleNamespace(
        state="ready", cache_key="key", payload={}
    )
    result = read_report(session, part)
    assert result.state == "partial"
    assert result.corrections_state == "ready"
