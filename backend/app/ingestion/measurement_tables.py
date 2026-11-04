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

from app.ingestion.formula_flags import FormulaAudit, inspect_formulas
from app.ingestion.measurement_csv import parse
from app.ingestion.measurement_provenance import (
    mark_copied_cells,
    possible_generator_copies,
)

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


class Workbook(list):  # type: ignore[type-arg]
    """Value grid plus a separate audit keyed by physical cell, without recalculation."""

    def __init__(self, sheets: list[Any], audit: FormulaAudit) -> None:
        super().__init__(sheets)
        self.audit = audit


def workbook(path: Path) -> list[tuple[str, list[list[Any]]]]:
    sheets: Any
    sheet: Any
    audit = inspect_formulas(path)
    if path.suffix.lower() == ".xls":
        try:
            book = xlrd.open_workbook(path, on_demand=True)
        except (xlrd.XLRDError, AssertionError, IndexError):
            from python_calamine import CalamineWorkbook

            with CalamineWorkbook.from_path(str(path)) as alternative:
                sheets = []
                for name in alternative.sheet_names:
                    sheet = alternative.get_sheet_by_name(name)
                    # Calamine trims empty leading rows/columns by default.
                    rows = sheet.to_python(skip_empty_area=False)
                    sheets.append((name, rows))
                audit.warnings.append(
                    "Valores leídos con Calamine; fórmulas verificadas en BIFF."
                )
                return Workbook(sheets, audit)
        try:
            return Workbook(
                [
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
                ],
                audit,
            )
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
        return Workbook(result, audit)


def header_label(value: Any) -> str:
    text = (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    text = re.sub(r"\s+", "", text)
    return {
        "target": "nominal",
        "tol+": "tol +",
        "tol-": "tol-",
        "equipo": "equipment",
        "measuringdevice": "equipment",
        "tipo": "type",
    }.get(text, text)


def identity_flags(
    grid: list[list[Any]], part_code: str
) -> tuple[list[str], list[str]]:
    """Use explicit header signals. A conflicting PPAP alone does not erase own ITP."""
    fields = {}
    for row in grid[:12]:
        for col, value in enumerate(row):
            label = re.sub(r"[^a-z0-9]", "", token(str(value)).lower())
            key = (
                "itp"
                if label in {"itpref", "partrefitp"}
                else "ppap"
                if label in {"ppapref", "ppapno"}
                else "part"
                if label in {"partno", "partn", "partnumber"}
                else None
            )
            if key:
                fields[key] = next(
                    (
                        str(v).strip()
                        for v in row[col + 1 :]
                        if v is not None and str(v).strip()
                    ),
                    "",
                )
    flags, warnings = [], []
    if re.fullmatch(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}", fields.get("part", "")):
        flags.append("cabecera_desplazada")
    if part_code:
        # Excel numeric cells arrive as floats (xlrd) or decimal text (OOXML).
        # Removing the decimal separator would turn 732180000.0 into 7321800000.
        itp = fields.get("itp", "")
        integer = re.fullmatch(r"(\d+)\.0+", itp)
        if integer:
            itp = integer[1]
        itp = re.sub(r"[.\s]", "", itp)
        itp_code = itp[1:5] if re.fullmatch(r"7\d{8}", itp) else ""
        ppap = re.search(r"(\d{4})-\d{2}[_-]in[tf]", fields.get("ppap", ""), re.I)
        if itp_code and itp_code != part_code:
            flags.append("identidad_otra_pieza")
        elif ppap and ppap[1] != part_code:
            if itp_code == part_code:
                warnings.append(
                    f"PPAP identifica {ppap[1]}, pero ITP identifica la pieza {part_code}. Revisar cabecera."
                )
            else:
                flags.append("identidad_sin_confirmar")
    return flags, warnings


def report_rows(
    sheets: list[tuple[str, list[list[Any]]]],
    *,
    part_code: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    revisions = set()
    output = []
    structures = {}
    for sheet, grid in sheets:
        identity, identity_warnings = identity_flags(grid, part_code)
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
                        if not identity:
                            revisions.add(following)
        if not re.match(r"DR\b|DR[_(-]|CAV[._ ]*\d|100%", sheet, re.I):
            continue
        header = next(
            (
                r
                for r, row in enumerate(grid[:30])
                if any(header_label(v) == "nominal" for v in row)
                and (
                    any(cavity_label(str(v))[0] for v in row)
                    or re.match(r"CAV[._ ]*\d", sheet, re.I)
                )
            ),
            None,
        )
        if header is None:
            continue
        labels = [header_label(v) for v in grid[header]]
        # Later blocks can repeat Nominal/Tol headers for forecasts or customer
        # limits. They must not replace the context of the first measurement block.
        columns: dict[str, int] = {}
        for i, label in enumerate(labels):
            if label:
                columns.setdefault(label, i)
        cavities = [
            (i, cavity_label(str(v)))
            for i, v in enumerate(grid[header])
            if cavity_label(str(v))[0]
        ]
        if not cavities:
            sheet_cavity = re.match(r"CAV[._ ]*(\d+)", sheet, re.I)
            end = columns.get("nok", len(labels))
            if sheet_cavity:
                cavities = [
                    (i, (f"c{int(sheet_cavity[1])}", f"muestra{int(m[1])}"))
                    for i, value in enumerate(grid[header][:end])
                    if (
                        m := re.fullmatch(
                            r"(?:Nr\.?)?\s*(\d+)(?:\.0)?", str(value).strip(), re.I
                        )
                    )
                ]
        if not cavities:
            continue
        audit = getattr(sheets, "audit", FormulaAudit())
        code_column = columns.get("number", 0)

        def normalized_code(row: list[Any], code_column: int = code_column) -> str:
            value = str(row[code_column]).strip() if code_column < len(row) else ""
            return value.removesuffix(".0")

        structures[sheet] = (
            header,
            tuple(normalized_code(row) for row in grid[header + 1 :]),
        )
        possible_copies = possible_generator_copies(
            sheet, grid, header, [c for c, _ in cavities], audit
        )
        groups = {}
        group = ""
        secondary_columns = set()
        previous_column = None
        secondary = False
        first_cavity = cavities[0][1][0]
        for c, (cavity, variant) in cavities:
            if previous_column is not None and (
                c != previous_column + 1 or (cavity == first_cavity and not variant)
            ):
                secondary = True
                group = ""
            text = (
                str(grid[header - 1][c])
                if header > 0 and c < len(grid[header - 1])
                else ""
            )
            group = conditions(text) or group
            groups[c] = group
            if secondary and not group:
                secondary_columns.add(c)
            previous_column = c
        # Conditions already distinguish repeated cavities. Add a column discriminator
        # only for repetitions that would otherwise overwrite the same observation.
        counts_by_context: dict[tuple[str, str], int] = defaultdict(int)
        for col, (cavity, _) in cavities:
            counts_by_context[cavity, groups[col]] += 1
        cavities = [
            (
                col,
                (
                    cavity,
                    variant
                    or (
                        f"col{excel_column(col)}"
                        if counts_by_context[cavity, groups[col]] > 1
                        else ""
                    ),
                ),
            )
            for col, (cavity, variant) in cavities
        ]
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
            code_column = columns.get("number", 0)
            raw_code = str(row[code_column]).strip() if len(row) > code_column else ""
            if raw_code:
                match = re.fullmatch(r"N?(\d+(?:[.-]\d+)*)", raw_code, re.I)
                ncode = "N" + match[1].removesuffix(".0") if match else ""
            nominal = number(cell("nominal"))
            if not ncode or nominal is None:
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
            declared_unit = str(cell("units") or cell("unit") or "").strip()
            if declared_unit:
                unit = declared_unit
            for column, (cavity, variant) in cavities:
                value = number(row[column]) if column < len(row) else None
                info = audit.cells.get((sheet, r + 1, column + 1), {})
                if value is None and not info:
                    continue
                flags = list(info.get("flags", []))
                state = info.get("provenance_state", "medicion")
                if str(cell("equipment")).strip().upper() == "IMPOSED":
                    flags.append("valor_impuesto")
                    if state != "generado":
                        state = "sin_confirmar"
                copy_evidence = possible_copies.get((r + 1, column + 1))
                if copy_evidence and state != "generado":
                    flags.append("posible_copia_de_generador")
                    state = "sin_confirmar"
                flags.extend(identity)
                if column in secondary_columns:
                    flags.append("bloque_secundario_sin_contexto")
                    if state != "generado":
                        state = "sin_confirmar"
                if identity and state != "generado":
                    state = "sin_confirmar"
                if value is None and state == "medicion":
                    state = "sin_confirmar"
                    flags.append("valor_no_numerico")
                if value == 0:
                    flags.append("cero")
                    if nominal != 0 and state == "medicion":
                        state = "sin_confirmar"
                        flags.append("cero_sin_confirmar")
                warnings = list(audit.warnings) + identity_warnings
                if audit.random_sheets:
                    warnings.append(
                        "El libro contiene RAND. Se excluyen sus fórmulas y dependencias posibles; las copias como valores solo se señalan cuando coinciden estructura, intervalo y redondeo del generador."
                    )
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
                        "deviation": value - nominal if value is not None else None,
                        "provenance_state": state,
                        "flags": flags,
                        "warnings": warnings,
                        "formula": info.get("formula"),
                        **(
                            {"generator_evidence": copy_evidence}
                            if copy_evidence
                            else {}
                        ),
                        "original_value": info.get("cached_error")
                        or (row[column] if column < len(row) else None),
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
    mark_copied_cells(output, structures)
    return (next(iter(revisions)) if len(revisions) == 1 else ""), output


def excel_column(index: int) -> str:
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
