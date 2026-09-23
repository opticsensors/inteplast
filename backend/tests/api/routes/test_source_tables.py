import io
import struct
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.core.config import settings

API = f"{settings.API_V1_STR}/files"


def upload(client, headers, name, data):
    response = client.post(API + "/", headers=headers, files={"file": (name, data)})
    assert response.status_code == 200, response.text
    return f"{API}/{response.json()['id']}/table"


def test_csv_preview_preserves_original_cells_and_requires_auth(
    client: TestClient, normal_user_token_headers
):
    data = "N170 diámetro;;;;;;;;\r\n16;GX;;4,000;0;-0,1;3,975;-0,025;\r\n\r\n".encode(
        "cp1252"
    )
    url = upload(client, normal_user_token_headers, "measurement.csv", data)
    assert client.get(url).status_code == 401
    response = client.get(url, headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    rows = response.json()["sheets"][0]["rows"]
    assert rows[0][0] == "N170 diámetro"
    assert rows[1][6] == "3,975"
    assert rows[2] == []
    assert response.json()["sheets"][0]["name"] == "CSV"


def test_binary_xls_is_read_even_when_uploaded_under_uuid(
    client: TestClient, normal_user_token_headers
):
    def record(code, data):
        return struct.pack("<HH", code, len(data)) + data

    # A real BIFF2 worksheet stream, with the observation in G1.
    data = (
        record(9, struct.pack("<HH", 2, 16))
        + record(3, struct.pack("<HH3sd", 0, 6, bytes(3), 3.975))
        + record(10, b"")
    )
    url = upload(client, normal_user_token_headers, "measurements.xls", data)
    response = client.get(url, headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    assert response.json()["sheets"][0]["rows"][0][6] == "3.975"


def xlsx_data(reference="H90"):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="DR_PAR" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="90"><c r="{reference}"><f>4-0.025</f><v>3.975</v></c><c r="I90" t="e"><v>#REF!</v></c><c r="J90" t="b"><v>1</v></c></row></sheetData></worksheet>',
        )
    return buffer.getvalue()


def test_xlsx_preview_preserves_coordinates_errors_and_saved_formula_results(
    client: TestClient, normal_user_token_headers
):
    url = upload(client, normal_user_token_headers, "report.xlsx", xlsx_data())
    response = client.get(url, headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    sheet = response.json()["sheets"][0]
    assert sheet["name"] == "DR_PAR"
    assert len(sheet["rows"]) == 90
    assert sheet["rows"][89][7:] == ["3.975", "#REF!", "TRUE"]


def test_preview_limits_sparse_workbooks_and_reports_corrupt_files(
    client: TestClient, normal_user_token_headers
):
    headers = normal_user_token_headers
    url = upload(client, headers, "too-large.xlsx", xlsx_data("H1048576"))
    assert client.get(url, headers=headers).status_code == 413
    url = upload(client, headers, "corrupt.xlsx", b"not a workbook")
    assert client.get(url, headers=headers).status_code == 422
    url = upload(client, headers, "unsupported.pdf", b"%PDF")
    assert client.get(url, headers=headers).status_code == 415


def test_preview_refuses_changed_local_original(
    client: TestClient, normal_user_token_headers, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    path = tmp_path / "measurement.csv"
    path.write_text("N170;3.975", encoding="utf-8")
    response = client.post(
        API + "/reference",
        headers=normal_user_token_headers,
        json={"path": "measurement.csv"},
    )
    assert response.status_code == 200, response.text
    path.write_text("N170;99.000;changed", encoding="utf-8")
    response = client.get(
        f"{API}/{response.json()['id']}/table", headers=normal_user_token_headers
    )
    assert response.status_code == 409
