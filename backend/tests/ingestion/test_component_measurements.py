from app.automatic_measurements import collect
from tests.ingestion.test_measurement_tables import walked


def test_unassigned_component_csv_keeps_the_actionable_pending_reason(tmp_path):
    path = tmp_path / "intern.01_c1.csv"
    path.write_bytes(b"N16 diameter\n1;Diameter;;10;0.1;-0.1;9.95;0;;\n")
    issues = {}
    groups = collect(
        *walked(tmp_path, [path]),
        components=[{"key": "BASE", "sheets": ["DR(base)"]}],
        file_issues=issues,
    )
    assert not groups
    assert "asigna esta fuente a un componente" in issues[path.name]


def test_each_component_keeps_its_sheet_revision(tmp_path, monkeypatch):
    path = tmp_path / "intern.01.xls"
    path.write_bytes(b"fixture")

    def grid(revision):
        return [
            ["Drawing level", revision],
            ["Nr", "Nominal", "Tol+", "Tol-", "Cav.1"],
            [16, 10, 0.1, -0.1, 9.95],
        ]

    monkeypatch.setattr(
        "app.automatic_measurements.workbook",
        lambda _: [("DR(base)", grid("A")), ("DR(tapa)", grid("B"))],
    )
    groups = collect(
        *walked(tmp_path, [path]),
        components=[
            {"key": "BASE", "sheets": ["DR(base)"]},
            {"key": "TAPA", "sheets": ["DR(tapa)"]},
        ],
    )
    assert {
        (key[0], row["component"]) for key, rows in groups.items() for row in rows
    } == {("A", "BASE"), ("B", "TAPA")}


def test_shared_workbook_keeps_base_cover_and_their_graph_series_separate(
    tmp_path, monkeypatch
):
    path = tmp_path / "intern.01.xls"
    path.write_bytes(b"fixture")
    base = [["Nr", "Nominal", "Tol+", "Tol-", 1, 2], [16, 10, 0.1, -0.1, 9.95, 10.02]]
    cover = [
        ["Nr", "Nominal", "Tol+", "Tol-", "Cav.1", "Cav.2"],
        [16, 20, 0.2, -0.2, 19.9, 20.1],
    ]
    monkeypatch.setattr(
        "app.automatic_measurements.workbook",
        lambda _: [("DR(base)", base), ("DR(tapa)", cover)],
    )
    components = [
        {"key": "BASE", "sheets": ["DR(base)"]},
        {"key": "TAPA", "sheets": ["DR(tapa)"]},
    ]
    groups = collect(*walked(tmp_path, [path]), components=components)
    rows = [row for group in groups.values() for row in group]
    assert len(rows) == 4
    assert {tuple(r["numbers"]) for r in rows} == {("BASE:N16",), ("TAPA:N16",)}
    assert {tuple(r["original_numbers"]) for r in rows} == {("N16",)}
    for group in groups.values():
        assert len({r["series_id"] for r in group}) == 2
    issues = {}
    partial = collect(
        *walked(tmp_path, [path]), components=components[:1], file_issues=issues
    )
    assert all(r["component"] == "BASE" for group in partial.values() for r in group)
    assert any("componente" in message for message in issues.values())
    # The initial safety guard still applies to an unconfigured piece.
    simple = collect(*walked(tmp_path, [path]))
    assert all(r["value"] > 19 for group in simple.values() for r in group)
