"""Evidence-based exclusions; never alter the saved numeric observations."""

import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.ingestion.formula_dependencies import resolve_cell

REF = r"\$?[A-Z]{1,3}\$?\d+"
GENERATOR = re.compile(
    r"ROUND\((?P<source>"
    + REF
    + r")-(?P<factor>"
    + REF
    + r")\+2\*(?P=factor)\*RAND\(\),(?P<digits>"
    + REF
    + r")\)",
    re.I,
)


def usable_measurement(record: dict[str, Any]) -> bool:
    return record.get(
        "provenance_state", "medicion"
    ) == "medicion" and "copia" not in record.get(
        "flags", record.get("exclusion_reasons", [])
    )


def possible_generator_copies(
    sheet: str, grid: list[list[Any]], header: int, columns: list[int], audit: Any
) -> dict[tuple[int, int], dict[str, Any]]:
    """Match the generator's sample labels, same-row inputs, range and precision."""

    def sample(v: Any) -> int | None:
        m = re.fullmatch(r"(?:Nr\.?)?\s*(\d+)(?:\.0)?", str(v).strip(), re.I)
        return int(m[1]) if m else None

    samples = {
        sample(grid[header][c]): c
        for c in columns
        if sample(grid[header][c]) is not None
    }
    found = {}
    for (s, row, col), info in audit.cells.items():
        if (
            s != sheet
            or "aleatoria" not in info["flags"]
            or col - 1 >= len(grid[header])
        ):
            continue
        match = GENERATOR.fullmatch(
            re.sub(r"\s+", "", info.get("formula", "")).lstrip("=")
        )
        if not match:
            continue
        label = sample(grid[header][col - 1])
        candidate = samples.get(label)
        if (
            candidate is None
            or candidate == col - 1
            or (sheet, row, candidate + 1) in audit.cells
        ):
            continue
        refs = [
            resolve_cell(match[k], row, col, info.get("formula_origin"))
            for k in ("source", "factor", "digits")
        ]
        if any(f != row or c < 1 for f, c in refs):
            continue
        source_col = refs[0][1] - 1
        if source_col not in samples.values() or source_col == candidate:
            continue
        try:
            source, factor, digits = [Decimal(str(grid[f - 1][c - 1])) for f, c in refs]
            value = Decimal(str(grid[row - 1][candidate]))
            if not all(v.is_finite() for v in (source, factor, digits, value)):
                continue
            if factor < 0 or digits != int(digits) or not 0 <= digits <= 12:
                continue
            quantum = Decimal(1).scaleb(-int(digits))

            def rounded(v: Decimal, quantum: Decimal = quantum) -> Decimal:
                return v.quantize(quantum, rounding=ROUND_HALF_UP)

            if rounded(value) != value or not rounded(
                source - factor
            ) <= value <= rounded(source + factor):
                continue
        except (ValueError, ArithmeticError, IndexError):
            continue
        found[row, candidate + 1] = {
            "source_cell": refs[0],
            "generator_cell": (row, col),
            "factor_cell": refs[1],
            "precision_cell": refs[2],
            "sample": label,
        }
    return found


def mark_copied_cells(rows: list[dict[str, Any]], structures: dict[str, Any]) -> None:
    by_sheet: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        by_sheet[r["_sheet"]][r["_cell"]] = r
    for name, copied in by_sheet.items():
        m = re.fullmatch(r"(.+?)(?:\s*\((?:[2-9]|\d{2,})\)|\s*-\s*copia)", name, re.I)
        if not m:
            continue
        candidates = [n for n in by_sheet if n.casefold() == m[1].strip().casefold()]
        if len(candidates) != 1:
            for r in copied.values():
                r["warnings"].append(
                    "No se identifica una hoja de origen única para esta posible copia; se conservan los valores."
                )
            continue
        source = candidates[0]
        base = by_sheet[source]
        if structures.get(source) != structures.get(name) or not set(copied) <= set(
            base
        ):
            for r in copied.values():
                r["warnings"].append(
                    "Hoja con nombre de copia pero estructura o cobertura distinta; no se deduplica."
                )
            continue
        for cell, r in copied.items():
            origin = base[cell]
            if r["provenance_state"] == "generado":
                continue
            context = (
                "numbers",
                "nominal",
                "tol_inf",
                "tol_sup",
                "_cavity",
                "_variant",
                "unit",
                "evaluation",
                "element",
                "_condition",
            )
            equal_context = all(r[k] == origin[k] for k in context)
            if (
                origin["provenance_state"] != "generado"
                and equal_context
                and r["value"] == origin["value"]
            ):
                r["flags"].append("copia")
                r["duplicate_of"] = {"sheet": source, "cell": cell}
            else:
                r["flags"].append("difiere_de_hoja_origen")
                r["comparison_origin"] = {"sheet": source, "cell": cell}
