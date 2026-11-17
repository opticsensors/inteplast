import uuid

from sqlmodel import select

from app.component_models import qualified
from app.knowledge_models import PartCharacteristic
from app.models import Part
from tests.api.routes.test_part_setup import API, source, write
from tests.api.routes.test_piece_editor import create
from tests.utils.feature import create_random_feature

__all__ = ["source"]


def test_changing_folder_requires_confirming_source_assignments_again(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    other = root.parent / (folder + " other")
    other.mkdir()
    headers = normal_user_token_headers
    pid = create(client, headers, folder)["id"]
    config = {"components": [{"key": "BASE", "name": "Base", "sheets": ["DR(base)"]}]}
    assert (
        client.put(f"{API}/{pid}/components", headers=headers, json=config).status_code
        == 200
    )
    response = client.put(
        f"{API}/{pid}", headers=headers, json={"folder_path": other.name, "files": []}
    )
    assert response.status_code == 200, response.text
    stored = db.get(Part, uuid.UUID(pid))
    db.refresh(stored)
    assert stored.components == [
        {"key": "BASE", "name": "Base", "sheets": [], "files": []}
    ]


def test_component_csvs_reach_separate_graphs_and_refresh_is_idempotent(
    client, normal_user_token_headers, source
):
    folder, root = source
    headers = normal_user_token_headers
    for name, value in [("base", "9.95"), ("cover", "10.05")]:
        write(
            root,
            f"{name}/intern.01_c1.csv",
            f"N16 diameter\n1;Diameter;;10;0.1;-0.1;{value};0;;\n".encode(),
        )
    pid = create(client, headers, folder)["id"]
    config = {
        "components": [
            {"key": key, "name": key, "files": [{"path": f"{name}/intern.01_c1.csv"}]}
            for key, name in [("BASE", "base"), ("TAPA", "cover")]
        ]
    }
    response = client.put(f"{API}/{pid}/components", headers=headers, json=config)
    assert response.status_code == 200, response.text
    response = client.post(f"{API}/{pid}/read-data", headers=headers)
    assert response.status_code == 200, response.text
    evidence = client.get(f"/api/v1/evidence/parts/{pid}", headers=headers).json()
    entries = evidence["study"]["payload"]["catalog"]["entries"]
    assert {e["id"] for e in entries} == {"BASE:N16", "TAPA:N16"}
    values = {
        e["id"]: [
            p["value"]
            for s in e["series"]
            for cavity in s["records"].values()
            for p in cavity.values()
        ]
        for e in entries
    }
    assert values == {"BASE:N16": [9.95], "TAPA:N16": [10.05]}
    second = client.post(f"{API}/{pid}/read-data", headers=headers)
    assert second.status_code == 200
    assert second.json()["imported"] == 0


def test_components_keep_same_number_separate_and_do_not_reassign_old_links(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    write(root, "base.pdf")
    write(root, "cover.pdf")
    headers = normal_user_token_headers
    part = create(client, headers, folder)
    pid = part["id"]
    old = PartCharacteristic(part_id=uuid.UUID(pid), code="N16", revision="01")
    db.add(old)
    db.commit()
    organization = {
        "components": [
            {
                "key": "BASE",
                "name": "Base",
                "sheets": ["DR(base)"],
                "files": [{"path": "base.pdf", "revision": "01"}],
            },
            {
                "key": "TAPA",
                "name": "Tapa",
                "sheets": ["DR(tapa)"],
                "files": [{"path": "cover.pdf", "revision": "01"}],
            },
        ]
    }
    response = client.put(f"{API}/{pid}/components", headers=headers, json=organization)
    assert response.status_code == 200, response.text
    feature = create_random_feature(db)
    ids = []
    for component in ["BASE", "TAPA"]:
        result = client.put(
            f"/api/v1/evidence/features/{feature.id}/parts/{pid}/characteristics",
            headers=headers,
            json={"code": qualified("N16", component), "revision": "01"},
        )
        assert result.status_code == 200, result.text
        assert result.json()["number"] == "N16"
        assert result.json()["component"] == component
        ids.append(result.json()["id"])
    assert len(set(ids)) == 2
    rows = db.exec(
        select(PartCharacteristic).where(PartCharacteristic.part_id == uuid.UUID(pid))
    ).all()
    assert {(c.component, c.code) for c in rows} == {
        ("", "N16"),
        ("BASE", "N16"),
        ("TAPA", "N16"),
    }
    result = client.get(f"/api/v1/evidence/parts/{pid}", headers=headers).json()
    assert {c["code"] for c in result["characteristics"]} == {
        "N16",
        "BASE:N16",
        "TAPA:N16",
    }
    assert len(result["components"]) == 2
    search = client.get("/api/v1/catalog", headers=headers, params={"q": "BASE:N16"})
    assert search.status_code == 200, search.text
    assert {c["code"] for c in search.json()["cotas"]} == {"BASE:N16"}
    assert {d["filename"] for d in result["documents"]} >= {"base.pdf", "cover.pdf"}
    # Removing a component with identities is a migration, not a display edit.
    assert (
        client.put(
            f"{API}/{pid}/components", headers=headers, json={"components": []}
        ).status_code
        == 409
    )
    options = client.get(f"{API}/{pid}/components", headers=headers).json()
    assert options["unassigned_characteristics"] == 1
    db.refresh(old)
    assert old.component == ""


def test_component_configuration_rejects_duplicate_owners_and_outside_paths(
    client, normal_user_token_headers, source
):
    folder, _ = source
    headers = normal_user_token_headers
    pid = create(client, headers, folder)["id"]
    duplicate = {
        "components": [{"key": k, "name": k, "sheets": ["DR"]} for k in ["A", "B"]]
    }
    assert (
        client.put(
            f"{API}/{pid}/components", headers=headers, json=duplicate
        ).status_code
        == 422
    )
    outside = {
        "components": [{"key": "A", "name": "A", "files": [{"path": "../other.pdf"}]}]
    }
    assert (
        client.put(f"{API}/{pid}/components", headers=headers, json=outside).status_code
        == 422
    )


def minimal_xlsx(sheets: list[str]) -> bytes:
    """A valid workbook with empty sheets, written without an Excel library."""
    import io
    import zipfile
    from xml.sax.saxutils import quoteattr

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Types>",
        )
        book.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        book.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(
                f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>'
                for i, name in enumerate(sheets, start=1)
            )
            + "</sheets></workbook>",
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Relationships>",
        )
        for i in range(1, len(sheets) + 1):
            book.writestr(
                f"xl/worksheets/sheet{i}.xml",
                '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>',
            )
    return buffer.getvalue()


def test_sheets_are_examined_before_any_import(
    client, db, normal_user_token_headers, source
):
    folder, root = source
    headers = normal_user_token_headers
    write(
        root, "4- Metrologia/rev.A/report.xlsx", minimal_xlsx(["DR(base)", "Resumen"])
    )
    write(root, "4- Metrologia/broken.xlsx", b"not a workbook")
    # Measurement methods are not measurements: their sheets are not offered.
    write(root, "6- Método de medición/MM.xlsx", minimal_xlsx(["Método"]))
    pid = create(client, headers, folder)["id"]
    options = client.get(f"{API}/{pid}/components", headers=headers)
    assert options.status_code == 200, options.text
    body = options.json()
    workbooks = {w["path"]: w["sheets"] for w in body["workbooks"]}
    assert workbooks["4- Metrologia/rev.A/report.xlsx"] == ["DR(base)", "Resumen"]
    assert workbooks["4- Metrologia/broken.xlsx"] == []
    assert "6- Método de medición/MM.xlsx" not in workbooks
    assert {"DR(base)", "Resumen"} <= set(body["sheet_names"])
    assert "Método" not in body["sheet_names"]
    # The DR(<name>) convention still suggests a component, without being required.
    assert [s["key"] for s in body["suggestions"]] == ["BASE"]
    assert not db.exec(
        select(PartCharacteristic).where(PartCharacteristic.part_id == uuid.UUID(pid))
    ).all()


def test_sources_left_unassigned_are_remembered_only_with_components(
    client, db, normal_user_token_headers, source
):
    folder, _root = source
    headers = normal_user_token_headers
    pid = create(client, headers, folder)["id"]
    config = {
        "components": [{"key": "BASE", "name": "Base", "sheets": ["DR(base)"]}],
        "unassigned": ["sheet:Resumen base", "sheet:DR(base)", "file:cover.pdf"],
    }
    response = client.put(f"{API}/{pid}/components", headers=headers, json=config)
    assert response.status_code == 200, response.text
    options = client.get(f"{API}/{pid}/components", headers=headers).json()
    # An assigned source cannot also be "left unassigned".
    assert options["unassigned"] == ["file:cover.pdf", "sheet:Resumen base"]
    response = client.put(
        f"{API}/{pid}/components",
        headers=headers,
        json={"components": [], "unassigned": ["file:cover.pdf"]},
    )
    assert response.status_code == 200, response.text
    stored = db.get(Part, uuid.UUID(pid))
    db.refresh(stored)
    assert stored.components == [] and stored.component_unassigned == []


def test_without_components_measurements_are_read_as_one_piece(
    client, normal_user_token_headers, source
):
    folder, root = source
    headers = normal_user_token_headers
    write(
        root,
        "base/intern.01_c1.csv",
        b"N16 diameter\n1;Diameter;;10;0.1;-0.1;9.95;0;;\n",
    )
    pid = create(client, headers, folder)["id"]
    # Saving an empty organization is the same as never defining components.
    response = client.put(
        f"{API}/{pid}/components", headers=headers, json={"components": []}
    )
    assert response.status_code == 200, response.text
    response = client.post(f"{API}/{pid}/read-data", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["imported"] >= 1
    evidence = client.get(f"/api/v1/evidence/parts/{pid}", headers=headers).json()
    entries = evidence["study"]["payload"]["catalog"]["entries"]
    assert {e["id"] for e in entries} == {"N16"}


def test_assigning_a_drawing_to_a_component_never_makes_it_principal(
    client, db, normal_user_token_headers, source
):
    from app.knowledge_models import PartFile, PartReference

    folder, root = source
    headers = normal_user_token_headers
    pid = create(client, headers, folder)["id"]
    write(root, "base.pdf", b"%PDF base")
    config = {
        "components": [
            {
                "key": "BASE",
                "name": "BASE",
                "files": [{"path": "base.pdf", "revision": ""}],
            }
        ]
    }
    response = client.put(f"{API}/{pid}/components", headers=headers, json=config)
    assert response.status_code == 200, response.text
    part_id = uuid.UUID(pid)
    files = db.exec(select(PartFile).where(PartFile.part_id == part_id)).all()
    assert [(f.name, f.kind, f.primary) for f in files] == [
        ("base.pdf", "drawing", False)
    ]
    reference = db.get(PartReference, (part_id, "drawing"))
    assert reference is None or reference.file_id is None
