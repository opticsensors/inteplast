"""Numeric observations in individual/wide CMM exports and PPAP report sheets."""

import csv
import io
import math
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import xlrd

from app.ingestion.measurement_csv import parse

CAVITY = re.compile(r"c(?:av(?:ity)?\.?)?[\s_]*(\d+)(.*)", re.I)


def number(value: Any) -> float | None:
    try:
        result = float(str(value).strip().replace(",", "."))
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def token(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w.-]+", "", text).strip(".-")


def conditions(text: str) -> str:
    values = []
    for match in re.finditer(
        r"(nozzle\s*)?(\d+(?:[.,]\d+)?)\s*[º°]?\s*(C\b|bar\b)", text, re.I
    ):
        values.append(
            ("nozzle" if match[1] else "")
            + match[2].replace(",", ".")
            + match[3].lower()
        )
    if not values:
        nozzle = re.search(r"nozzle[ _]*(\d+)", text, re.I)
        if nozzle:
            values.append(f"nozzle{nozzle[1]}c")
    return ".".join(values)


def cavity_label(text: str) -> tuple[str, str]:
    match = CAVITY.fullmatch(text.strip())
    return (f"c{int(match[1])}", token(match[2])) if match else ("", "")


def csv_rows(data: bytes, *, pilot: bool = False) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    cells = list(csv.reader(text.splitlines(), delimiter=";"))
    headers = next(
        (
            [
                (i, cavity_label(v))
                for i, v in enumerate(row)
                if i >= 5 and cavity_label(v)[0]
            ]
            for row in cells
            if any(cavity_label(v)[0] for v in row[5:])
        ),
        [],
    )
    if not headers:
        rows, _ = parse(data, pilot=pilot)
        return rows
    output: list[dict[str, Any]] = []
    start = headers[0][0]
    for column, (cavity, variant) in headers:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
        for row in cells:
            if any(cavity_label(v)[0] for v in row[5:]):
                writer.writerow([row[0]])
            elif len(row) > column and len(row) > 3 and row[1].strip():
                value = number(row[column])
                nominal = number(row[3])
                if value is None or nominal is None:
                    writer.writerow([])
                else:
                    writer.writerow(
                        row[:4]
                        + (row[4:6] if start == 6 else ["", ""])
                        + [row[column], value - nominal]
                    )
            else:
                writer.writerow(row[:1])
        rows, _ = parse(buffer.getvalue().encode(), pilot=pilot)
        output.extend(
            {**row, "_cavity": cavity, "_variant": variant, "_wide": True}
            for row in rows
        )
    return output


def workbook(path: Path) -> list[tuple[str, list[list[Any]]]]:
    if path.suffix.lower() == ".xls":
        book = xlrd.open_workbook(path, on_demand=True)
        try:
            return [
                (
                    sheet.name,
                    [
                        [
                            None
                            if sheet.cell_type(r, c)
                            in {xlrd.XL_CELL_ERROR, xlrd.XL_CELL_BOOLEAN}
                            else sheet.cell_value(r, c)
                            for c in range(sheet.ncols)
                        ]
                        for r in range(sheet.nrows)
                    ],
                )
                for sheet in book.sheets()
            ]
        finally:
            book.release_resources()
    # Read cached numeric values, never evaluate formulas or follow external links.
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError("El libro excede el tamaño admitido.")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = [
                "".join(item.itertext())
                for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        rels = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        sheets = ET.fromstring(archive.read("xl/workbook.xml")).findall(
            "s:sheets/s:sheet", ns
        )
        result = []
        for sheet in sheets:
            target = rels[
                sheet.attrib[
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                ]
            ]
            target = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath("xl/" + target)
            )
            grid: list[list[Any]] = []
            for row in ET.fromstring(archive.read(target)).findall(
                "s:sheetData/s:row", ns
            ):
                row_index = int(row.attrib["r"]) - 1
                if row_index > 100000:
                    raise ValueError("Demasiadas filas en el libro.")
                while len(grid) <= row_index:
                    grid.append([])
                for cell in row:
                    letters = re.match(r"[A-Z]+", cell.attrib["r"])
                    if not letters:
                        continue
                    column = 0
                    for letter in letters[0]:
                        column = column * 26 + ord(letter) - 64
                    if column > 1000:
                        continue
                    while len(grid[row_index]) < column:
                        grid[row_index].append("")
                    kind = cell.attrib.get("t")
                    value: Any = cell.findtext("s:v", default="", namespaces=ns)
                    if kind == "s":
                        value = shared[int(value)]
                    elif kind == "inlineStr":
                        inline = cell.find("s:is", ns)
                        value = "".join(inline.itertext()) if inline is not None else ""
                    elif kind in {"e", "b"}:
                        value = None
                    grid[row_index][column - 1] = value
            result.append((sheet.attrib["name"], grid))
        return result


def report_rows(
    sheets: list[tuple[str, list[list[Any]]]],
) -> tuple[str, list[dict[str, Any]]]:
    revisions = set()
    output = []
    for sheet, grid in sheets:
        for row in grid[:12]:
            for c, value in enumerate(row):
                if "drawing" in str(value).lower() and "level" in str(value).lower():
                    following = next(
                        (
                            str(v).strip().lstrip("'")
                            for v in row[c + 1 :]
                            if v is not None and str(v).strip()
                        ),
                        "",
                    )
                    if (
                        following
                        and len(following) <= 64
                        and not following.startswith("#")
                    ):
                        level = re.fullmatch(r"(\d{2})/\w+", following)
                        if level:
                            following = level[1]
                        revisions.add(following)
        if not re.match(r"DR\b|DR[_(-]", sheet, re.I) or "100%" in sheet:
            continue
        header = next(
            (
                r
                for r, row in enumerate(grid[:30])
                if any(str(v).strip().lower() == "nominal" for v in row)
                and any(cavity_label(str(v))[0] for v in row)
            ),
            None,
        )
        if header is None:
            continue
        labels = [str(v).strip().lower() for v in grid[header]]
        columns = {label: i for i, label in enumerate(labels)}
        cavities = [
            (i, cavity_label(str(v)))
            for i, v in enumerate(grid[header])
            if cavity_label(str(v))[0]
        ]
        groups = {}
        group = ""
        for c, _ in cavities:
            text = str(grid[header - 1][c]) if c < len(grid[header - 1]) else ""
            group = conditions(text) or group
            groups[c] = group
        counts: dict[str, int] = defaultdict(int)
        ncode, shot = "", ""
        for r in range(header + 1, len(grid)):
            row = grid[r]

            def cell(
                label: str, columns: dict[str, int] = columns, row: list[Any] = row
            ) -> Any:
                c = columns.get(label)
                return row[c] if c is not None and c < len(row) else None

            marker = re.search(r"SHOT\s*(\d+)", " ".join(map(str, row)), re.I)
            if marker:
                shot = "shot" + marker[1]
            raw_code = str(row[0]).strip() if row else ""
            if raw_code:
                match = re.fullmatch(r"N?(\d+(?:\.\d+)?)", raw_code, re.I)
                ncode = "N" + match[1].removesuffix(".0") if match else ""
            nominal = number(cell("nominal"))
            if (
                not ncode
                or nominal is None
                or str(cell("equipment")).strip().upper() == "IMPOSED"
            ):
                continue
            high, low = number(cell("tol +")), number(cell("tol-"))
            if low is not None and high is not None and low > high:
                continue
            evaluation = str(cell("type") or "")
            counts[ncode] += 1
            idx = counts[ncode]
            title = f"{ncode} {nominal:g} {evaluation}".strip()
            unit = (
                "µm"
                if re.match(r"R(?:a|z|max|t)\b", evaluation, re.I)
                else "°"
                if "°" in evaluation
                else "mm"
            )
            for column, (cavity, variant) in cavities:
                value = number(row[column]) if column < len(row) else None
                if value is None:
                    continue
                output.append(
                    {
                        "numbers": [ncode],
                        "title": title,
                        "series_id": f"PPAP:{sheet}:{ncode}:{idx}",
                        "label": title,
                        "block": title,
                        "idx": idx,
                        "element": str(cell("equipment") or ""),
                        "evaluation": evaluation,
                        "unit": unit,
                        "nominal": nominal,
                        "tol_inf": low,
                        "tol_sup": high,
                        "value": value,
                        "deviation": value - nominal,
                        "lower": nominal + low if low is not None else None,
                        "upper": nominal + high if high is not None else None,
                        "_cavity": cavity,
                        "_condition": groups[column],
                        "_variant": ".".join(filter(None, [variant, shot])),
                        "_sheet": sheet,
                        "_cell": f"{excel_column(column)}{r + 1}",
                        "_report": True,
                    }
                )
    return (next(iter(revisions)) if len(revisions) == 1 else ""), output


def excel_column(index: int) -> str:
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
