"""Validated CMM block exports; project mappings are opt-in, never inferred by N-number."""

import csv
import hashlib
import math
import re
from typing import Any

READER = "cmm-blocks-v1"


def dimension_numbers(block: str) -> list[str]:
    numbers: list[str] = []
    for match in re.finditer(
        r"\bN\s*(\d{1,6}(?:\.\d{1,3})?)((?:\s*/\s*N?\s*\d{1,6}(?:\.\d{1,3})?)*)",
        block,
        re.I,
    ):
        numbers.extend("N" + n for n in re.findall(r"\d+(?:\.\d+)?", match[0]))
    return list(dict.fromkeys(numbers))


def numeric(value: str, line: int) -> float | None:
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?", value):
        raise ValueError(f"Número no reconocido en la línea {line}: {value[:40]}")
    result = float(value.replace(",", "."))
    if not math.isfinite(result):
        raise ValueError(f"Número no finito en la línea {line}")
    return result


def parse(
    data: bytes, *, pilot: bool = False
) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    rows: list[dict[str, Any]] = []
    block, element, idx, occurrence = "", "", 0, 0
    seen: dict[str, int] = {}
    ignored = 0
    for line, cells in enumerate(csv.reader(text.splitlines(), delimiter=";"), 1):
        if not cells or not any(c.strip() for c in cells):
            continue
        heading = ";".join(cells).strip("; \t")
        if any(re.fullmatch(r"c\d+", c.strip(), re.I) for c in cells[3:]):
            raise ValueError(
                "Es una comparativa de cavidades. Selecciona el export individual de cada cavidad."
            )
        if heading.startswith(("****", "////")):
            continue
        if len(cells) < 8 or not cells[1].strip():
            block, element, idx = heading, "", 0
            seen[block] = seen.get(block, 0) + 1
            occurrence = seen[block]
            continue
        idx += 1
        if len(cells) > 9 and re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", cells[9].strip()):
            raise ValueError(
                "Las columnas de resultado no corresponden al export CMM individual."
            )
        element = cells[0].strip() or element
        metric = cells[1].strip()
        nominal, high, low, value, deviation = [numeric(v, line) for v in cells[3:8]]
        if nominal is None or value is None:
            raise ValueError(f"Falta nominal o valor medido en la línea {line}")
        if low is not None and high is not None and low > high:
            raise ValueError(f"Tolerancias invertidas en la línea {line}")
        if any(
            not math.isfinite(nominal + limit)
            for limit in (low, high)
            if limit is not None
        ):
            raise ValueError(f"Límite de tolerancia no finito en la línea {line}")
        numbers = dimension_numbers(block)
        if pilot and block.startswith(("POINT ", "GLOBAL ")):
            numbers = ["N165"]
        if not numbers:
            ignored += 1
            continue
        series_id = f"{block}|{occurrence}|{idx}"
        if not pilot:
            series_id += f"|CMM:{element}"
        label = f"{block} · [{idx}] {metric}"
        if pilot and block.startswith("N170"):
            from app.ingestion.pilot_3212.measurements import csv_identity

            identity = csv_identity({"bloque": block, "idx": idx}, element)
            if identity is None:
                raise ValueError(f"Evaluación CMM no identificada en la línea {line}")
            series_id = "|".join(map(str, identity))
            label = f"{identity[1]} · {'GX' if idx == 1 else 'LP máximo'}"
        rows.append(
            {
                "numbers": numbers,
                "title": block,
                "series_id": series_id,
                "label": label,
                "block": block,
                "idx": idx,
                "element": None if pilot else f"CMM {element}" if element else block,
                "evaluation": None if pilot else f"{metric} · {idx}",
                "unit": "°" if metric.startswith("Phi") else "mm",
                "nominal": nominal,
                "tol_inf": low,
                "tol_sup": high,
                "value": value,
                "deviation": deviation,
                "lower": nominal + low if low is not None else None,
                "upper": nominal + high if high is not None else None,
                "line": line,
            }
        )
    if not rows:
        raise ValueError(
            "No se reconoce un CSV CMM por bloques con cotas N, nominal y medición."
        )
    return rows, (
        [f"{ignored} filas sin una cota identificada; no se incorporarán."]
        if ignored
        else []
    )


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
