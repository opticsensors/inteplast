"""Read original spreadsheet cells for an authenticated, read-only web preview."""

import csv
import io
import posixpath
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import xlrd
from fastapi import HTTPException
from pydantic import BaseModel

MAX_CELLS = 500_000
MAX_ROWS = 20_000
MAX_COLUMNS = 512


class SourceSheet(BaseModel):
    name: str
    rows: list[list[str]]


class SourceTable(BaseModel):
    sheets: list[SourceSheet]


def check_size(rows: int, columns: int, cells: int) -> None:
    if rows > MAX_ROWS or columns > MAX_COLUMNS or cells > MAX_CELLS:
        raise HTTPException(
            413,
            "La tabla es demasiado grande para la vista previa. Descarga el original.",
        )


def display(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def read_xls(path: Path) -> list[SourceSheet]:
    book = xlrd.open_workbook(path, on_demand=True)
    sheets = []
    total = 0
    try:
        for sheet in book.sheets():
            total += sheet.nrows * sheet.ncols
            check_size(sheet.nrows, sheet.ncols, total)
            rows = []
            for r in range(sheet.nrows):
                cells = []
                for cell in sheet.row(r):
                    if cell.ctype == xlrd.XL_CELL_ERROR:
                        value = xlrd.error_text_from_code.get(cell.value, "#ERROR!")
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = "TRUE" if cell.value else "FALSE"
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_datetime(
                            cell.value, book.datemode
                        ).isoformat(sep=" ")
                    else:
                        value = display(cell.value)
                    cells.append(value)
                rows.append(cells)
            sheets.append(SourceSheet(name=sheet.name, rows=rows))
    finally:
        book.release_resources()
    return sheets


def read_xlsx(path: Path) -> list[SourceSheet]:
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 64 * 1024 * 1024:
            raise HTTPException(
                413, "El libro es demasiado grande para la vista previa."
            )
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = [
                "".join(t.text or "" for t in item.findall(".//s:t", ns))
                for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        rels = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            if item.attrib.get("TargetMode") != "External"
        }
        sheets = []
        total = 0
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall(
            "s:sheets/s:sheet", ns
        ):
            rel = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            if rel not in rels:
                continue
            target = rels[rel]
            target = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath("xl/" + target)
            )
            grid: list[list[str]] = []
            for cell in ET.fromstring(archive.read(target)).findall(
                "s:sheetData/s:row/s:c", ns
            ):
                address = re.fullmatch(r"([A-Z]+)([1-9]\d*)", cell.attrib.get("r", ""))
                if not address:
                    continue
                value = cell.findtext("s:v", default="", namespaces=ns)
                kind = cell.attrib.get("t")
                if kind == "s":
                    value = shared[int(value)]
                elif kind == "inlineStr":
                    value = "".join(t.text or "" for t in cell.findall("s:is//s:t", ns))
                elif kind == "b":
                    value = "TRUE" if value == "1" else "FALSE"
                # Formatting-only cells do not extend the preview to Excel's last row.
                if not value:
                    continue
                r = int(address[2])
                c = 0
                for letter in address[1]:
                    c = c * 26 + ord(letter) - 64
                check_size(r, c, total)
                while len(grid) < r:
                    grid.append([])
                added = max(0, c - len(grid[r - 1]))
                total += added
                check_size(r, c, total)
                grid[r - 1].extend([""] * added)
                grid[r - 1][c - 1] = value
            sheets.append(SourceSheet(name=sheet.attrib["name"], rows=grid))
        return sheets


def read_table(path: Path, filename: str) -> SourceTable:
    extension = Path(filename).suffix.lower()
    if extension not in {".csv", ".xls", ".xlsx"}:
        raise HTTPException(415, "La vista de tabla admite CSV, XLS y XLSX.")
    if path.stat().st_size > 16 * 1024 * 1024:
        raise HTTPException(413, "El archivo es demasiado grande para la vista previa.")
    try:
        if extension == ".xls":
            sheets = read_xls(path)
        elif extension == ".xlsx":
            sheets = read_xlsx(path)
        else:
            data = path.read_bytes()
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = data.decode("cp1252")
            try:
                delimiter = (
                    csv.Sniffer().sniff(text[:8192], delimiters=";,\t").delimiter
                )
            except csv.Error:
                delimiter = ";" if ";" in text else ","
            rows: list[list[str]] = []
            total = 0
            for row in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter):
                total += len(row)
                check_size(len(rows) + 1, len(row), total)
                rows.append(row)
            sheets = [SourceSheet(name="CSV", rows=rows)]
    except (
        ValueError,
        KeyError,
        IndexError,
        BadZipFile,
        ET.ParseError,
        csv.Error,
        xlrd.XLRDError,
    ) as error:
        raise HTTPException(422, "No se ha podido leer la tabla original.") from error
    return SourceTable(sheets=sheets)
