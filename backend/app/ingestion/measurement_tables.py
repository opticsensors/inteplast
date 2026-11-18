"""Numeric observations in individual/wide CMM exports and PPAP report sheets."""

import csv
import io
import math
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import xlrd

from app.ingestion.formula_flags import FormulaAudit, inspect_formulas
from app.ingestion.measurement_csv import UnsupportedMeasurementCsv, parse
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


WIDE_FIRST_CAVITY = 4  # element, evaluation and nominal always come first


def wide_limits(row: list[str], start: int, line: int) -> tuple[str, str, str] | None:
    """Nominal and tolerance cells of a comparison row, located from its content.

    The columns before the first cavity vary between exports: a second language for
    the evaluation, tolerances and a blank separator are all optional. A fixed
    position would read one of them as another. None when there is no nominal.
    """
    lead = [value.strip() for value in row[2:start]]
    at = next((i for i, value in enumerate(lead) if number(value) is not None), None)
    if at is None:
        return None
    limits = lead[at + 1 :]
    while limits and not limits[-1]:
        limits.pop()
    if len(limits) > 2 or any(v and number(v) is None for v in limits):
        raise UnsupportedMeasurementCsv(
            "comparativa de cavidades con columnas no reconocidas antes de la "
            f"primera cavidad (línea {line})"
        )
    limits += [""] * (2 - len(limits))
    return lead[at], limits[0], limits[1]


def csv_rows(data: bytes, *, pilot: bool = False) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    cells = list(csv.reader(text.splitlines(), delimiter=";"))

    def is_header(row: list[str]) -> bool:
        return any(cavity_label(v)[0] for v in row[WIDE_FIRST_CAVITY:])

    headers = next(
        (
            [
                (i, cavity_label(v))
                for i, v in enumerate(row)
                if i >= WIDE_FIRST_CAVITY and cavity_label(v)[0]
            ]
            for row in cells
            if is_header(row)
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
        # One output line per input line keeps the original line numbers.
        for line, row in enumerate(cells, 1):
            if is_header(row):
                writer.writerow([row[0]])
            elif len(row) > column and row[1].strip():
                limits = wide_limits(row, start, line)
                value = number(row[column])
                nominal = number(limits[0]) if limits else None
                if limits is None or value is None or nominal is None:
                    writer.writerow([])
                else:
                    writer.writerow(
                        [row[0], row[1], "", *limits, row[column], value - nominal]
                    )
            else:
                writer.writerow(row[:1])
        rows, _ = parse(buffer.getvalue().encode(), pilot=pilot, inline_titles=True)
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


def unread_structure(grid: list[list[Any]]) -> str | None:
    """Why a report sheet with a Nominal header has no readable measurement columns.

    It only describes the sheet: nothing is read from it. A cavity label or a cota
    number that the report does not contain is never made up.
    """
    for r, row in enumerate(grid[:30]):
        column = next(
            (c for c, value in enumerate(row) if header_label(value) == "nominal"), None
        )
        if column is None:
            continue
        numbered = [
            value
            for value in row[column + 1 :]
            if re.fullmatch(r"\d{1,3}(?:\.0)?", str(value).strip())
        ]
        if len(numbered) >= 2:
            return "cavities_numbered_only"
        codes = [
            str(line[0]).strip() if line else ""
            for line in grid[r + 1 :]
            if column < len(line) and number(line[column]) is not None
        ]
        if codes and not any(codes):
            return "no_cavity_label_and_no_characteristic_code"
        return "no_cavity_label"
    return None


def omitted_sheet_review(grid: list[list[Any]]) -> str | None:
    """Content evidence for an unsupported sheet, never a name-only exclusion."""
    header = next(
        (
            (r, c)
            for r, row in enumerate(grid[:30])
            for c, v in enumerate(row)
            if header_label(v) == "nominal"
        ),
        None,
    )
    if header is None:
        return None
    r, c = header
    if not any(
        c < len(row) and row[c] is not None and str(row[c]).strip()
        for row in grid[r + 1 :]
    ):
        return "empty_dimensional_template"
    return "unclassified_dimensional_table"


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


SUPPORTED_REPORT = re.compile(r"DR\b|DR[_(-]|CAV[._ ]*\d|100%", re.I)
MEASURING_DEVICE = re.compile(
    r"\b(?:CMM|CT[ -]?SCAN|CALIPER|MICROMETER|MICR[ÓO]METRO|IMPOSED)\b", re.I
)
DERIVED = re.compile(
    r"diffe?renc|difer[eè]nc|delta|forecast|previsi|prediction|simula|"
    r"theoret|te[oó]ric|compar|resumen|summary|\b(?:max|min|average|mean|target|OK)\b",
    re.I,
)
TRIAL_CONTEXT = re.compile(
    r"\b(?:batch|lote?|lot)\s*[:#-]?\s*\d+\b|humidif|\d+\s*(?:bar\b|[º°]\s*C\b)", re.I
)


@dataclass(frozen=True)
class ReportBlock:
    header: int
    end: int
    code_column: int
    context: str
    context_cell: str


def report_blocks(
    sheets: list[tuple[str, list[list[Any]]]],
    part_code: str,
) -> Iterator[tuple[str, list[list[Any]], ReportBlock | None]]:
    """Recover explicit PPAP blocks. Unknown conventions stay in the diagnostics."""
    for name, grid in sheets:
        if SUPPORTED_REPORT.match(name) or DERIVED.search(name.replace("_", " ")):
            yield name, grid, None
            continue
        # Require an explicit reference to this piece in the report header.
        identity = False
        conflict = False
        for row in grid[:12]:
            for col, value in enumerate(row):
                key = re.sub(r"[^a-z]", "", header_label(value))
                if key not in {"itpref", "refitp", "partrefitp", "ppapref", "refppap"}:
                    continue
                field = next(
                    (
                        str(v).strip()
                        for v in row[col + 1 :]
                        if v is not None and str(v).strip()
                    ),
                    "",
                )
                if "itp" in key:
                    match = re.fullmatch(
                        r"7(\d{4})\d{4}",
                        field.removesuffix(".0").replace(".", "").replace(" ", ""),
                    )
                else:
                    match = re.match(r"(\d{4})-\d{2}[_-]", field)
                if match:
                    identity |= match[1] == part_code
                    conflict |= match[1] != part_code
        found = False
        if identity and not conflict:
            for i in range(1, len(grid)):
                labels = [header_label(v) for v in grid[i]]
                if "nominal" not in labels or "equipment" not in labels:
                    continue
                upper = grid[i - 1]
                codes = {
                    j
                    for line in (grid[i], upper)
                    for j, v in enumerate(line)
                    if header_label(v).strip(".:")
                    in {"nr", "no", "number", "numero", "nº"}
                }
                cavities = [j for j, v in enumerate(grid[i]) if cavity_label(str(v))[0]]
                if (
                    len(codes) != 1
                    or not cavities
                    or cavities != list(range(cavities[0], cavities[-1] + 1))
                ):
                    continue
                if len({cavity_label(str(grid[i][j]))[0] for j in cavities}) != len(
                    cavities
                ):
                    continue
                contexts = [
                    (j, str(upper[j]).strip())
                    for j in cavities
                    if j < len(upper) and upper[j] is not None and str(upper[j]).strip()
                ]
                if len(contexts) != 1 or contexts[0][0] != cavities[0]:
                    continue
                col, context = contexts[0]
                if not TRIAL_CONTEXT.search(context) or DERIVED.search(
                    " ".join(str(v) for v in upper)
                ):
                    continue
                end = i + 1
                code_col = next(iter(codes))
                while end < len(grid):
                    line = grid[end]
                    if not any(v is not None and str(v).strip() for v in line):
                        break
                    code = str(line[code_col]).strip() if code_col < len(line) else ""
                    if code and not re.fullmatch(r"N?\d+(?:[.-]\d+)*", code, re.I):
                        break
                    if any(
                        header_label(v)
                        in {"nominal", "min", "max", "average", "summary"}
                        for v in line
                    ):
                        break
                    if not code and any(isinstance(v, str) and v.strip() for v in line):
                        break
                    end += 1
                if end > i + 1:
                    found = True
                    yield (
                        name,
                        grid,
                        ReportBlock(
                            i, end, code_col, context, f"{excel_column(col)}{i}"
                        ),
                    )
        if not found:
            yield name, grid, None


def cavity_series(
    rows: list[dict[str, Any]],
) -> Iterator[tuple[tuple[Any, ...], list[dict[str, Any]]]]:
    # report_rows emits the cells of each physical row together.
    for _, cells in groupby(
        rows,
        key=lambda r: (r["_sheet"], r["_cell"].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    ):
        group = list(cells)
        if len({r["value"] for r in group if r["value"] is not None}) < 4:
            continue
        fingerprint = tuple(
            (
                tuple(r["numbers"]),
                r["nominal"],
                r["element"],
                r["unit"],
                r["evaluation"],
                r["_cavity"],
                r["value"],
            )
            for r in group
        )
        yield fingerprint, group


def flag_repeated_results(rows: list[dict[str, Any]]) -> None:
    """An entire matching multi-cavity series in another sheet is uncertain evidence.

    Preserve the measurements from the established reader and keep both locators.
    Distinct lot names do not prove that repeated values came from independent tests.
    """
    if not any("measurement_context" in row for row in rows):
        return
    seen: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for fingerprint, group in sorted(
        cavity_series(rows), key=lambda pair: "measurement_context" in pair[1][0]
    ):
        prior = seen.setdefault(fingerprint, group)
        if (
            prior[0]["_sheet"] == group[0]["_sheet"]
            or "measurement_context" not in group[0]
        ):
            continue
        for row, other in zip(group, prior, strict=True):
            if row["provenance_state"] == "medicion":
                row["provenance_state"] = "sin_confirmar"
                row["flags"].append("serie_repetida_en_otra_hoja")
                row["comparison_origin"] = {
                    "sheet": other["_sheet"],
                    "cell": other["_cell"],
                }


def flag_repeated_reports(reports: dict[str, list[dict[str, Any]]]) -> None:
    """Compare only newly eligible series against the other books of the same piece.

    An identical multi-cavity vector under different report/lot labels does not
    establish an independent measurement. Keep both paths available for review.
    """
    targets: dict[tuple[Any, ...], list[tuple[str, list[dict[str, Any]]]]] = (
        defaultdict(list)
    )
    for path, rows in reports.items():
        recovered = [r for r in rows if "measurement_context" in r]
        for signature, group in cavity_series(recovered):
            if any(r["provenance_state"] == "medicion" for r in group):
                targets[signature].append((path, group))
    if not targets:
        return
    for path, rows in reports.items():
        for signature, other in cavity_series(rows):
            for target_path, group in targets.get(signature, []):
                if path == target_path:
                    continue
                for row, origin in zip(group, other, strict=True):
                    if row["provenance_state"] == "medicion":
                        row["provenance_state"] = "sin_confirmar"
                        row["flags"].append("serie_repetida_en_otro_informe")
                        row["comparison_origin"] = {
                            "path": path,
                            "sheet": origin["_sheet"],
                            "cell": origin["_cell"],
                        }


def report_rows(
    sheets: list[tuple[str, list[list[Any]]]],
    *,
    part_code: str = "",
    diagnostics: list[dict[str, Any]] | None = None,
    component_sheets: set[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    revisions = set()
    output: list[dict[str, Any]] = []
    structures = {}
    for sheet, grid, block in report_blocks(sheets, part_code):
        diagnostic: dict[str, Any] = {
            "sheet": sheet,
            "status": "skipped",
            "reason": "sheet_name_not_supported",
        }
        if diagnostics is not None:
            diagnostic["nominal_header_rows"] = [
                i + 1
                for i, row in enumerate(grid[:30])
                if any(header_label(v) == "nominal" for v in row)
            ]
            diagnostics.append(diagnostic)
        identity, identity_warnings = identity_flags(grid, part_code)
        sheet_revisions: set[str] = set()
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
                            sheet_revisions.add(following)
        if block is None and omitted_sheet_review(grid) == "empty_dimensional_template":
            diagnostic.update(
                status="excluded",
                reason="empty_dimensional_template",
                review="empty_dimensional_template",
            )
            continue
        if block is None and not SUPPORTED_REPORT.match(sheet):
            diagnostic["review"] = omitted_sheet_review(grid)
            continue
        header = (
            block.header
            if block
            else next(
                (
                    r
                    for r, row in enumerate(grid[:30])
                    if any(header_label(v) == "nominal" for v in row)
                    and (
                        any(cavity_label(str(v))[0] for v in row)
                        or re.match(r"CAV[._ ]*\d", sheet, re.I)
                        or (component_sheets is not None and sheet in component_sheets)
                    )
                ),
                None,
            )
        )
        if header is None:
            diagnostic["reason"] = "no_recognized_header_or_cavities"
            diagnostic["detail"] = unread_structure(grid)
            continue
        labels = [header_label(v) for v in grid[header]]
        # Later blocks can repeat Nominal/Tol headers for forecasts or customer
        # limits. They must not replace the context of the first measurement block.
        columns: dict[str, int] = {}
        for i, label in enumerate(labels):
            if label:
                columns.setdefault(label, i)
        if block:
            columns["number"] = block.code_column
        cavities = [
            (i, cavity_label(str(v)))
            for i, v in enumerate(grid[header])
            if cavity_label(str(v))[0]
        ]
        if not cavities and component_sheets and sheet in component_sheets:
            # Number-only cavity headers are accepted only after explicit organization.
            start = max(
                columns.get("nominal", 0),
                columns.get("tol-", 0),
                columns.get("tol +", 0),
            )
            cavities = [
                (i, (f"c{int(float(str(v)))}", ""))
                for i, v in enumerate(grid[header])
                if i > start and re.fullmatch(r"[1-9]\d{0,2}(?:\.0)?", str(v).strip())
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
            diagnostic["reason"] = "no_recognized_cavities"
            diagnostic["detail"] = unread_structure(grid)
            continue
        diagnostic.update(
            status="read", reason=None, header_row=header + 1, rejected_rows=[]
        )
        output_start = len(output)
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
            group = block.context if block else conditions(text) or group
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
        for r in range(header + 1, block.end if block else len(grid)):
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
            if block and not raw_code:
                continue
            if raw_code:
                match = re.fullmatch(r"N?(\d+(?:[.-]\d+)*)", raw_code, re.I)
                ncode = "N" + match[1].removesuffix(".0") if match else ""
            nominal = number(cell("nominal"))
            if not ncode or nominal is None:
                if diagnostics is not None and nominal is not None and raw_code:
                    diagnostic["rejected_rows"].append(
                        {
                            "row": r + 1,
                            "code": raw_code,
                            "reason": "unsupported_characteristic_code",
                        }
                    )
                continue
            high, low = number(cell("tol +")), number(cell("tol-"))
            if low is not None and high is not None and low > high:
                if diagnostics is not None:
                    diagnostic["rejected_rows"].append(
                        {
                            "row": r + 1,
                            "code": raw_code,
                            "reason": "reversed_tolerances",
                        }
                    )
                continue
            evaluation = str(cell("type") or "")
            if block:
                reason = None
                if DERIVED.search(" ".join(str(v) for v in row[: cavities[0][0]])):
                    reason = "derived_result"
                elif not MEASURING_DEVICE.match(str(cell("equipment") or "").strip()):
                    reason = "unverified_measuring_device"
                if reason:
                    diagnostic["rejected_rows"].append({"row": r + 1, "reason": reason})
                    continue
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
                if block and info and state == "medicion":
                    state = "sin_confirmar"
                    flags.append("formula_en_bloque_recuperado")
                equipment = str(cell("equipment")).strip().upper()
                if equipment == "IMPOSED" or (
                    block and re.match(r"IMPOSED\b", equipment)
                ):
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
                        "_revision": next(iter(sheet_revisions))
                        if len(sheet_revisions) == 1
                        else "",
                        "_cell": f"{excel_column(column)}{r + 1}",
                        "_report": True,
                        **(
                            {
                                "measurement_context": {
                                    "text": block.context,
                                    "cell": block.context_cell,
                                }
                            }
                            if block
                            else {}
                        ),
                    }
                )
        diagnostic["observations"] = len(output) - output_start
    mark_copied_cells(output, structures)
    flag_repeated_results(output)
    return (next(iter(revisions)) if len(revisions) == 1 else ""), output


def excel_column(index: int) -> str:
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
