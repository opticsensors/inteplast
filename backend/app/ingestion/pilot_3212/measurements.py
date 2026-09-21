"""3212 CMM identities and saved XLS correction predictions with source-cell checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import xlrd

from app.ingestion import cmm
from app.ingestion.common import number, result, source
from app.ingestion.pilot_3212.config import CASES, CAVITIES, CORRECTIONS, SAMPLES

RecordKey = tuple[str, str, str, str, int]
Records = dict[RecordKey, dict[str, Any]]


def csv_identity(row: dict[str, Any], inherited_id: str) -> tuple[str, str, int] | None:
    block, idx = row["bloque"].strip(), int(row["idx"])
    if block.startswith("N170"):
        element = int(inherited_id) if inherited_id.isdigit() else -1
        if 11 <= element <= 14:
            bolt, height = element - 10, "1.5"
        elif 15 <= element <= 18:
            bolt, height = element - 14, "5.0"
        else:
            raise ValueError(f"N170 sin ID CMM reconocido: {block}, {inherited_id}")
        return ("N170", f"B{bolt}-H{height}", idx)
    if block.startswith("N161 "):
        return ("N161", "main", idx)
    if block.startswith("N240 "):
        return ("N240", "main", idx)
    if block.startswith("GLOBAL "):
        return ("N165", "main", idx)
    if block.startswith("N165 MIN"):
        return ("N165", "scan", idx)
    match = re.match(r"POINT\s+(\d+)\s", block)
    if match:
        return ("N165", f"P{int(match[1]):02d}", idx)
    return None


def load_csv(root: Path) -> tuple[Records, list[dict[str, Any]]]:
    records: Records = {}
    files = cmm.discover(root / "4- Metrologia")
    seen_files = set()
    for file in files:
        sample, cavity = file["muestreo"], file["cavidad"]
        if (sample, cavity) in seen_files:
            raise ValueError(
                f"CSV duplicado para {sample}/{cavity}; seleccionar la fuente explícitamente"
            )
        seen_files.add((sample, cavity))
        table = cmm.read_csv(file["ruta"])
        element, previous_group = "", None
        for row in table.to_dict("records"):
            group = (row["bloque"], row["ocurrencia"])
            if group != previous_group:
                element, previous_group = "", group
            element = row["id_cmm"] or element
            identity = csv_identity(row, element)
            if identity is None:
                continue
            nominal, lo, hi = (
                number(row[k]) for k in ("nominal", "tol_inf", "tol_sup")
            )
            lower = nominal + lo if nominal is not None and lo is not None else None
            upper = nominal + hi if nominal is not None and hi is not None else None
            key = (sample, cavity, *identity)
            if key in records:
                raise ValueError(f"Medición duplicada: {key}")
            measured = number(row["medido"])
            records[key] = {
                "value": measured,
                "lower": lower,
                "upper": upper,
                "status": result(measured, lower, upper),
                "reported_nok": bool(row["nok"]),
                "source": source(
                    file["ruta"],
                    root,
                    f"{row['bloque'].strip()} · aparición {row['ocurrencia']} · fila {row['idx']} · CMM {element or 'sin ID'}",
                ),
            }
    return records, files


def cell_value(sheet: Any, row: int, col: int) -> float | None:
    if row > sheet.nrows or col > sheet.ncols:
        return None
    cell = sheet.cell(row - 1, col - 1)
    return number(cell.value) if cell.ctype == xlrd.XL_CELL_NUMBER else None


def validate_excel_mapping(sheet: Any, row: int, feature: str) -> None:
    """Check fixed pilot mappings against feature, equipment and nominal."""
    inherited = ""
    for r in range(row):
        value = sheet.cell_value(r, 0)
        if value != "":
            inherited = str(value).replace("N", "").split(".")[0]
    if inherited != feature[1:]:
        raise ValueError(
            f"Mapeo XLS obsoleto: fila {row}, esperaba {feature}, encontró {inherited}"
        )
    if str(sheet.cell_value(row - 1, 6)).strip() != "CMM":
        raise ValueError(f"La fila XLS {row} ya no es una medida CMM")
    expected = {"N161": 45.4, "N240": 18.5, "N170": 4.0, "N165": 1.35}[feature]
    actual = cell_value(sheet, row, 4)
    if actual is None or abs(actual - expected) > 1e-9:
        raise ValueError(f"Nominal XLS inesperado en {feature}, fila {row}: {actual}")


def mappings(feature: str, variant: str) -> list[tuple[Any, ...]]:
    # label, original row, final prediction row, [(retoc row, intermediate prediction row)]
    if feature == "N161":
        return [
            ("GX", 101, 101, [(101, 101)]),
            ("LP(2) máximo", 102, 102, [(102, 102)]),
        ]
    if feature == "N240":
        return [("Distancia", 224, 225, [(224, 224), (225, 225)])]
    if feature == "N165":
        return [
            ("GLOBAL mínimo", 111, 116, [(111, 111), (116, 116)]),
            ("GLOBAL máximo", 112, 117, [(112, 112), (117, 117)]),
        ]
    match = re.fullmatch(r"B([1-4])-H(1\.5|5\.0)", variant)
    if not match:
        raise ValueError(f"Variante N170 no reconocida: {variant}")
    start = 146 + (int(match[1]) - 1) * 4 + (2 if match[2] == "5.0" else 0)
    return [
        ("GX", start, start, [(146, start)]),
        ("LP máximo", start + 1, start + 1, [(146, start + 1)]),
    ]


def compare(
    records: Records,
    books: dict[str, Any],
    root: Path,
    feature: str,
    variant: str,
    cavity: str,
) -> dict[str, Any]:
    case = CASES[feature]
    correction = CORRECTIONS[case["correction"]]
    sheet = books[case["correction"]].sheet_by_name("DR(100%)")
    cavity_index = CAVITIES.index(cavity)
    original_col, prediction_col = 8 + cavity_index, 16 + cavity_index
    items, warnings = [], []
    for idx, (label, original_row, predicted_row, steps) in enumerate(
        mappings(feature, variant), 1
    ):
        validate_excel_mapping(sheet, original_row, feature)
        before = records.get((correction["before"], cavity, feature, variant, idx))
        after = records.get((correction["after"], cavity, feature, variant, idx))
        xls_before = cell_value(sheet, original_row, original_col)
        predicted = cell_value(sheet, predicted_row, prediction_col)
        lower = cell_value(sheet, original_row, 4)
        low_delta, high_delta = (
            cell_value(sheet, original_row, 6),
            cell_value(sheet, original_row, 5),
        )
        upper = (
            lower + high_delta if lower is not None and high_delta is not None else None
        )
        lower = (
            lower + low_delta if lower is not None and low_delta is not None else None
        )
        for stage, record in (("inicial", before), ("posterior", after)):
            if not record or record["value"] is None:
                warnings.append(f"{label}: falta la medición {stage} de esta cavidad.")
            elif record["lower"] != lower or record["upper"] != upper:
                warnings.append(
                    f"{label}: límites diferentes entre CSV {stage} y Excel; revisar comparabilidad."
                )
        if (
            before
            and xls_before is not None
            and before["value"] is not None
            and abs(before["value"] - xls_before) > 0.0005
        ):
            warnings.append(
                f"{label}: el valor inicial del Excel ({xls_before}) difiere del CSV ({before['value']}). La previsión se conserva tal como está guardada."
            )
        stages: list[dict[str, Any]] = [
            {
                "delta": cell_value(sheet, r, 15),
                "value": cell_value(sheet, pr, prediction_col),
                "cells": f"O{r} → {xlrd.formula.colname(prediction_col - 1)}{pr}",
            }
            for r, pr in steps
        ]
        if (
            all(s["delta"] is not None for s in stages)
            and xls_before is not None
            and predicted is not None
        ):
            if abs(xls_before + sum(s["delta"] for s in stages) - predicted) > 1e-7:
                warnings.append(
                    f"{label}: el resultado XLS no coincide con la suma de los pasos revisados; comprobar fórmula."
                )
        items.append(
            {
                "label": label,
                "before": before,
                "after": after,
                "prediction": predicted,
                "prediction_status": result(predicted, lower, upper),
                "lower": lower,
                "upper": upper,
                "xls_before": xls_before,
                "steps": stages,
                "source": source(
                    root / correction["xls"],
                    root,
                    f"DR(100%)!{xlrd.formula.colname(original_col - 1)}{original_row}; "
                    f"{xlrd.formula.colname(prediction_col - 1)}{predicted_row}; "
                    + "; ".join(s["cells"] for s in stages),
                ),
                "history": [
                    records.get((sample, cavity, feature, variant, idx))
                    for sample in SAMPLES
                ],
            }
        )
    return {"items": items, "warnings": warnings}
