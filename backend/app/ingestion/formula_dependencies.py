"""Static cell references only; no formula execution or external workbook reads.

BIFF8 relative references follow MS-XLS SHRFMLA/RgceLocRel. Dynamic references,
external books, names and unsupported syntax remain unresolved.
"""

import re
import struct
from bisect import bisect_left, bisect_right
from collections import defaultdict, deque
from typing import Any

from xlrd.biffh import unpack_unicode_update_pos  # type: ignore[import-untyped]
from xlrd.formula import szdict  # type: ignore[import-untyped]

Range = tuple[str, int, int, int, int]


def biff_references(
    tokens: bytes, sheet: str, row: int, col: int, links: dict[int, str]
) -> tuple[list[Range], bool]:
    refs = []
    complete = True
    pos = 0

    def loc(r: int, c: int, relative: bool) -> tuple[int, int]:
        rr, cc = r, c & 255
        if relative:
            if c & 0x8000:
                rr = (row + (r if r < 32768 else r - 65536)) % 65536
            if c & 0x4000:
                cc = (col + (cc if cc < 128 else cc - 256)) % 256
        return rr + 1, cc + 1

    try:
        while pos < len(tokens):
            op = tokens[pos]
            if op & 0x80:
                raise ValueError("Invalid token")
            kind = (op & 31) + (32 if op & 96 else 0)
            size = szdict[80][kind]
            if kind == 0x17:
                _, end = unpack_unicode_update_pos(tokens, pos + 1, lenlen=1)
                size = end - pos
            elif kind == 0x19:
                attr, count = struct.unpack_from("<BH", tokens, pos + 1)
                size = count * 2 + 6 if attr == 4 else 4
            elif kind in (0x24, 0x2C, 0x3A, 0x25, 0x2D, 0x3B):
                offset = pos + 1
                target: str | None = sheet
                if kind in (0x3A, 0x3B):
                    target = links.get(struct.unpack_from("<H", tokens, offset)[0])
                    offset += 2
                if kind in (0x24, 0x2C, 0x3A):
                    r, c = struct.unpack_from("<HH", tokens, offset)
                    r1, c1 = r2, c2 = loc(r, c, kind == 0x2C)
                else:
                    a, b, c, d = struct.unpack_from("<HHHH", tokens, offset)
                    r1, c1 = loc(a, c, kind == 0x2D)
                    r2, c2 = loc(b, d, kind == 0x2D)
                if target:
                    refs.append(
                        (target, min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))
                    )
                else:
                    complete = False
            elif kind in (0x23, 0x39, 0x2A, 0x2B, 0x3C, 0x3D):
                complete = False
            elif kind in (0x21, 0x22):
                func = (
                    struct.unpack_from("<H", tokens, pos + (1 if kind == 0x21 else 2))[
                        0
                    ]
                    & 0x7FFF
                )
                if func in (78, 148, 255):  # OFFSET, INDIRECT, add-in call
                    complete = False
            if size <= 0 or pos + size > len(tokens):
                raise ValueError("Unsupported token")
            pos += size
    except (ValueError, IndexError, struct.error, UnicodeError):
        complete = False
    return refs, complete


CELL = r"\$?[A-Z]{1,3}\$?[1-9]\d*"
REF = re.compile(
    r"(?<![\w.])(?:(?:'((?:[^']|'')+)'|([A-Za-z_\u0080-\uffff][\w.]*))!)?("
    + CELL
    + r")(?::("
    + CELL
    + r"))?(?![\w.(])",
    re.I,
)


def resolve_cell(
    ref: str, row: int, col: int, anchor: tuple[int, int] | None = None
) -> tuple[int, int]:
    match: Any = re.fullmatch(r"(\$?)([A-Z]+)(\$?)(\d+)", ref, re.I)
    c = 0
    for char in match[2].upper():
        c = c * 26 + ord(char) - 64
    r = int(match[4])
    if anchor:
        if not match[1]:
            c += col - anchor[1]
        if not match[3]:
            r += row - anchor[0]
    return r, c


def xml_references(
    text: str, sheet: str, row: int, col: int, anchor: tuple[int, int] | None = None
) -> tuple[list[Range], bool]:
    code = re.sub(r'"(?:[^"]|"")*"', '""', text)
    refs = []
    complete = not bool(re.search(r"\[|#REF!|\b(?:INDIRECT|OFFSET)\s*\(", code, re.I))
    for m in REF.finditer(code):
        target = (m[1] or m[2] or sheet).replace("''", "'")
        r1, c1 = resolve_cell(m[3], row, col, anchor)
        r2, c2 = resolve_cell(m[4] or m[3], row, col, anchor)
        if min(r1, c1, r2, c2) < 1:
            complete = False
        else:
            refs.append((target, min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2)))
    # Sheet spans, whole-column references and unparsed qualifiers stay unresolved.
    rest = REF.sub("", code)
    if "!" in rest or re.search(r"\b[A-Z]+:[A-Z]+\b|\b\d+:\d+\b", rest, re.I):
        complete = False
    return refs, complete


def uncertain_dependencies(
    cells: dict[tuple[str, int, int], dict[str, Any]], sheet_names: set[str]
) -> set[tuple[str, int, int]]:
    """Return formulas reaching RAND/unknown references/cycles, by reverse graph."""
    names = {s.casefold(): s for s in sheet_names}
    by_row: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for s, r, c in cells:
        by_row[s][r].append(c)
    row_numbers = {s: sorted(rows) for s, rows in by_row.items()}
    reverse = defaultdict(set)
    remaining = {}
    bad = set()
    for key, info in cells.items():
        deps = set()
        if "aleatoria" in info["flags"] or not info.get("references_complete", False):
            bad.add(key)
        for target, r1, c1, r2, c2 in info.get("references", []):
            target = names.get(target.casefold())
            if target is None:
                bad.add(key)
                continue
            if r1 == r2 and c1 == c2:
                if (target, r1, c1) in cells:
                    deps.add((target, r1, c1))
            else:
                indices = row_numbers.get(target, [])
                for r in indices[bisect_left(indices, r1) : bisect_right(indices, r2)]:
                    deps.update(
                        (target, r, c) for c in by_row[target][r] if c1 <= c <= c2
                    )
        remaining[key] = len(deps)
        for d in deps:
            reverse[d].add(key)
    # Topological removal leaves cycles and formulas depending on them.
    ready = deque(k for k, n in remaining.items() if not n)
    while ready:
        k = ready.popleft()
        for dependent in reverse[k]:
            remaining[dependent] -= 1
            if not remaining[dependent]:
                ready.append(dependent)
    bad.update(k for k, n in remaining.items() if n)
    pending = deque(bad)
    while pending:
        for dependent in reverse[pending.popleft()]:
            if dependent not in bad:
                bad.add(dependent)
                pending.append(dependent)
    return bad
