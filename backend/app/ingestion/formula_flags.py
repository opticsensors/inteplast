"""Static BIFF8/OOXML formula provenance; never recalculate or execute macros.

BIFF layouts: MS-XLS Formula, ShrFmla, Array, PtgExp and Rgce. Token sizes
come from xlrd's BIFF tables, not a byte-pattern search in cached numbers.
Unknown syntax is reported as unconfirmed, never certified as a measurement.
"""

import io
import posixpath
import re
import struct
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from xlrd.biffh import unpack_unicode_update_pos  # type: ignore[import-untyped]
from xlrd.compdoc import CompDoc  # type: ignore[import-untyped]
from xlrd.formula import szdict  # type: ignore[import-untyped]

from app.ingestion.formula_dependencies import (
    biff_references,
    uncertain_dependencies,
    xml_references,
)

RANDOM = re.compile(
    r"(?<![\w.])(?:_xlfn\.)?(?:RAND(?:BETWEEN|ARRAY)?|ALEATORIO(?:\.ENTRE)?)\s*\(", re.I
)
RANDOM_NAME = re.compile(
    r"(?:_xlfn\.)?(?:RAND(?:BETWEEN|ARRAY)?|ALEATORIO(?:\.ENTRE)?)", re.I
)
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NAME_TOKEN = re.compile(r"(?<![\w.])(?:[^\W\d]|\\)[\w.\\]*")
Key = tuple[str, int, int]  # one-based physical coordinates


class UnsupportedWorkbook(ValueError):
    """Recognized file/format limitation, safe to report as a per-file issue."""


def coordinates(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"\$?([A-Z]+)\$?(\d+)", ref)
    if not match:
        raise ValueError("Coordenada OOXML no válida.")
    col = 0
    for ch in match[1]:
        col = col * 26 + ord(ch) - 64
    return col, int(match[2])


@dataclass
class FormulaAudit:
    cells: dict[Key, dict[str, Any]] = field(default_factory=dict)
    random_sheets: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    sheet_names: set[str] = field(default_factory=set)

    def finish(self) -> "FormulaAudit":
        self.random_sheets = {
            h for (h, _, _), v in self.cells.items() if "aleatoria" in v["flags"]
        }
        uncertain = (
            uncertain_dependencies(self.cells, self.sheet_names)
            if self.random_sheets
            else set()
        )
        for key, info in self.cells.items():
            flags = info["flags"]
            if "aleatoria" in flags:
                info["provenance_state"] = "generado"
            else:
                if (
                    key in uncertain
                    and "dependencia_aleatoria_no_resuelta" not in flags
                ):
                    flags.append("dependencia_aleatoria_no_resuelta")
                info["provenance_state"] = "sin_confirmar" if flags else "medicion"
        return self


def signature(path: Path) -> str:
    with path.open("rb") as stream:
        head = stream.read(1024)
    if head.lstrip().startswith(b"%PDF-"):
        raise UnsupportedWorkbook(
            "Contenido PDF con extensión de libro: requiere lectura como PDF, no como tabla Excel."
        )
    expected = "biff" if path.suffix.lower() == ".xls" else "ooxml"
    actual = (
        "biff"
        if head.startswith(bytes.fromhex("d0cf11e0a1b11ae1"))
        else "ooxml"
        if head.startswith(b"PK\x03\x04")
        else "desconocido"
    )
    if expected != actual:
        raise UnsupportedWorkbook(
            f"La firma {actual} no corresponde a la extensión {path.suffix}."
        )
    return actual


def records(data: bytes, start: int = 0) -> Iterator[tuple[int, bytes]]:
    pos = start
    while pos + 4 <= len(data):
        code, size = struct.unpack_from("<HH", data, pos)
        if pos + 4 + size > len(data):
            raise ValueError("Registro BIFF truncado.")
        yield code, data[pos + 4 : pos + 4 + size]
        pos += size + 4
        if code == 0x000A:
            return


def token_flags(
    tokens: bytes, names: dict[int, str], external: dict[tuple[int, int], str]
) -> list[str]:
    pos, random, complete, calls_external, named_reference = (
        0,
        False,
        True,
        False,
        False,
    )
    function_names = []
    try:
        while pos < len(tokens):
            op = tokens[pos]
            if op & 0x80:
                raise ValueError("Token inválido")
            kind = (op & 0x1F) + (32 if op & 0x60 else 0)
            size = szdict[80][kind]
            if kind == 0x17:
                _, end = unpack_unicode_update_pos(tokens, pos + 1, lenlen=1)
                size = end - pos
            elif kind == 0x19:
                attr, count = struct.unpack_from("<BH", tokens, pos + 1)
                size = count * 2 + 6 if attr == 4 else 4
            elif kind == 0x21:
                random |= struct.unpack_from("<H", tokens, pos + 1)[0] == 63
            elif kind == 0x22:
                func = struct.unpack_from("<H", tokens, pos + 2)[0] & 0x7FFF
                random |= func == 63
                calls_external |= func == 255
            elif kind == 0x23:
                named_reference = True
                function_names.append(
                    names.get(struct.unpack_from("<I", tokens, pos + 1)[0], "")
                )
            elif kind == 0x39:
                named_reference = True
                ixti, idx = struct.unpack_from("<HI", tokens, pos + 1)
                function_names.append(external.get((ixti, idx), ""))
            if size <= 0 or pos + size > len(tokens):
                raise ValueError("Token no interpretado")
            pos += size
    except (ValueError, IndexError, struct.error, UnicodeError):
        complete = False
    random |= calls_external and any(RANDOM_NAME.fullmatch(n) for n in function_names)
    return (
        (["aleatoria"] if random else [])
        + ([] if complete else ["formula_no_interpretada"])
        + (
            ["nombre_o_funcion_no_resuelto"]
            if (named_reference or calls_external) and not random
            else []
        )
    )


def biff_stream(data: bytes) -> FormulaAudit:
    """Inspect an unencrypted BIFF8 Workbook stream (also used by synthetic tests)."""
    audit = FormulaAudit()
    if len(data) < 8 or struct.unpack_from("<H", data)[0] != 0x0809:
        raise UnsupportedWorkbook("Falta cabecera BIFF8 verificable.")
    names: dict[int, str]
    supbooks: list[list[str]]
    links: list[tuple[int, int, int]]
    sheets, names, supbooks, links = [], {}, [], []
    all_sheets, internal_books = [], []
    for code, payload in records(data):
        if code == 0x0809 and struct.unpack_from("<H", payload)[0] != 0x0600:
            raise UnsupportedWorkbook("Solo se admite análisis de fórmulas BIFF8.")
        if code == 0x002F:
            raise UnsupportedWorkbook(
                "Libro cifrado: no se pueden verificar sus fórmulas."
            )
        if code == 0x0085:
            name, _ = unpack_unicode_update_pos(payload, 6, lenlen=1)
            all_sheets.append(name)
            if payload[5] == 0:
                sheets.append((name, struct.unpack_from("<I", payload)[0]))
        elif code == 0x0018:
            name, _ = unpack_unicode_update_pos(payload, 14, known_len=payload[3])
            names[len(names) + 1] = name
        elif code == 0x01AE:
            supbooks.append([])
            internal_books.append(payload[2:4] == b"\x01\x04")
        elif code == 0x0023 and supbooks:
            name, _ = unpack_unicode_update_pos(payload, 6, lenlen=1)
            supbooks[-1].append(name)
        elif code == 0x0017:
            count = struct.unpack_from("<H", payload)[0]
            if len(payload) < 2 + 6 * count:
                raise UnsupportedWorkbook(
                    "EXTERNSHEET continuado no admitido; fórmulas sin verificar."
                )
            links.extend(
                struct.unpack_from("<HHH", payload, 2 + 6 * i) for i in range(count)
            )
    external = {
        (ixti, idx): name
        for ixti, (book, _, _) in enumerate(links)
        if book < len(supbooks)
        for idx, name in enumerate(supbooks[book], 1)
    }
    audit.sheet_names = set(all_sheets)
    internal_links = {
        i: all_sheets[first]
        for i, (book, first, last) in enumerate(links)
        if book < len(internal_books)
        and internal_books[book]
        and first == last
        and first < len(all_sheets)
    }
    for sheet, offset in sheets:
        formulas, shared = [], {}
        previous = None
        for code, payload in records(data, offset):
            if code == 0x0006:
                row, col = struct.unpack_from("<HH", payload)
                size = struct.unpack_from("<H", payload, 20)[0]
                if len(payload) < 22 + size:
                    raise ValueError("Fórmula BIFF truncada.")
                tokens = payload[22 : 22 + size]
                flags = []
                cached_error = None
                if payload[12:14] == b"\xff\xff":
                    if payload[6] == 2:
                        flags.append("formula_error")
                        from xlrd.biffh import error_text_from_code

                        cached_error = error_text_from_code.get(
                            payload[8], "error BIFF"
                        )
                    elif payload[6] == 3:
                        flags.append("resultado_vacio")
                previous = (row, col)
                formulas.append((row, col, tokens, flags, cached_error))
            elif code in (0x04BC, 0x0221) and previous is not None:
                size_offset = 8 if code == 0x04BC else 12
                size = struct.unpack_from("<H", payload, size_offset)[0]
                tokens = payload[size_offset + 2 : size_offset + 2 + size]
                if len(tokens) != size:
                    raise ValueError("Fórmula compartida truncada.")
                shared[previous] = (
                    struct.unpack_from("<HHBB", payload),
                    token_flags(tokens, names, external),
                    tokens,
                )
        for row, col, tokens, flags, cached_error in formulas:
            reference_tokens = tokens
            if len(tokens) == 5 and tokens[0] == 1:
                anchor = struct.unpack_from("<HH", tokens, 1)
                group = shared.get(anchor)
                if (
                    group
                    and group[0][0] <= row <= group[0][1]
                    and group[0][2] <= col <= group[0][3]
                ):
                    flags += group[1]
                    reference_tokens = group[2]
                else:
                    flags.append("formula_compartida_no_resuelta")
            else:
                flags += token_flags(tokens, names, external)
            refs, complete = biff_references(
                reference_tokens, sheet, row, col, internal_links
            )
            audit.cells[sheet, row + 1, col + 1] = {
                "flags": list(flags),
                "format": "BIFF8",
                "cached_error": cached_error,
                "references": refs,
                "references_complete": complete
                and not any(
                    f in flags
                    for f in (
                        "formula_compartida_no_resuelta",
                        "nombre_o_funcion_no_resuelto",
                        "formula_no_interpretada",
                    )
                ),
            }
    return audit.finish()


def ooxml(path: Path) -> FormulaAudit:
    audit = FormulaAudit()
    with ZipFile(path) as archive:
        if sum(f.file_size for f in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError("El libro excede el tamaño admitido.")
        rels = {
            e.attrib["Id"]: e.attrib["Target"]
            for e in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        book_xml = ET.fromstring(archive.read("xl/workbook.xml"))
        defined_names = {
            n.attrib["name"].casefold()
            for n in book_xml.findall("s:definedNames/s:definedName", NS)
        }
        for sheet in book_xml.findall("s:sheets/s:sheet", NS):
            audit.sheet_names.add(sheet.attrib["name"])
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
            cells = ET.fromstring(archive.read(target)).findall(
                "s:sheetData/s:row/s:c", NS
            )
            masters = {
                f.attrib["si"]: (f.text, c.attrib["r"])
                for c in cells
                if (f := c.find("s:f", NS)) is not None
                and f.attrib.get("t") == "shared"
                and f.text
            }
            arrays = []
            for cell in cells:
                f = cell.find("s:f", NS)
                if f is not None and f.attrib.get("t") == "array":
                    bounds = f.attrib.get("ref", cell.attrib["r"]).split(":")
                    arrays.append(
                        ((*coordinates(bounds[0]), *coordinates(bounds[-1])), f)
                    )
            for cell in cells:
                col, row = coordinates(cell.attrib["r"])
                formula = cell.find("s:f", NS)
                if formula is None:
                    formula = next(
                        (
                            f
                            for (c1, r1, c2, r2), f in arrays
                            if c1 <= col <= c2 and r1 <= row <= r2
                        ),
                        None,
                    )
                if formula is None:
                    continue
                master = masters.get(formula.attrib.get("si", ""), ("", ""))
                text = formula.text or master[0] or ""
                anchor = None
                if formula.attrib.get("t") == "shared" and master[1]:
                    ac, ar = coordinates(master[1])
                    anchor = (ar, ac)
                flags = []
                if not text:
                    flags.append("formula_compartida_no_resuelta")
                # Excel string constants containing '=RAND()' are not executable calls.
                executable = re.sub(r'"(?:[^"]|"")*"', '""', text)
                if RANDOM.search(executable):
                    flags.append("aleatoria")
                if defined_names and any(
                    name.casefold() in defined_names
                    for name in NAME_TOKEN.findall(executable)
                ):
                    flags.append("nombre_o_funcion_no_resuelto")
                if not cell.findtext("s:v", default="", namespaces=NS):
                    flags.append("formula_sin_valor")
                if cell.attrib.get("t") == "e":
                    flags.append("formula_error")
                refs, complete = xml_references(
                    text, sheet.attrib["name"], row, col, anchor
                )
                audit.cells[sheet.attrib["name"], row, col] = {
                    "flags": flags,
                    "formula": text,
                    "format": "OOXML",
                    "formula_origin": anchor,
                    "references": refs,
                    "references_complete": complete
                    and bool(text)
                    and "nombre_o_funcion_no_resuelto" not in flags,
                    "cached_error": cell.findtext("s:v", namespaces=NS)
                    if cell.attrib.get("t") == "e"
                    else None,
                }
    return audit.finish()


def inspect_formulas(path: Path) -> FormulaAudit:
    if signature(path) == "ooxml":
        return ooxml(path)
    compound = CompDoc(path.read_bytes(), logfile=io.StringIO())
    stream = compound.get_named_stream("Workbook") or compound.get_named_stream("Book")
    if stream is None:
        raise UnsupportedWorkbook("El contenedor OLE no contiene un libro Excel.")
    return biff_stream(stream)
