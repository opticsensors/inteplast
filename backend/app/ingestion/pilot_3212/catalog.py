"""3212 evaluation catalogue; separate CMM elements and measurement rows retain identity."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.ingestion import cmm
from app.ingestion.common import number, result, source
from app.ingestion.pilot_3212.measurements import csv_identity


def dimension_ids(block: str) -> list[str]:
    """Keep joint headers together; N116/260 + N258 is not one interchangeable measure."""
    found: list[str] = []
    for match in re.finditer(r"\bN(\d{3})((?:\s*/\s*\d{3})*)", block):
        found.extend("N" + n for n in re.findall(r"\d{3}", match.group(0)))
    return list(dict.fromkeys(found))


def catalog_group(block: str) -> tuple[str, list[str], str]:
    if block.startswith(("POINT ", "GLOBAL ")):
        return "N165", ["N165"], "dimension"
    ids = dimension_ids(block) if block.startswith("N") else []
    if ids:
        return "/".join(ids), ids, "dimension"
    return "COORD:" + block, [], "diagnostic"


def load_catalog(
    root: Path, actions: dict[str, Any], reviewed_cases: dict[str, Any]
) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    seen: set[tuple[str, str]] = set()
    row_count = 0
    for file in cmm.discover(root / "4- Metrologia"):
        sample, cavity = file["muestreo"], file["cavidad"]
        if (sample, cavity) in seen:
            raise ValueError(f"CSV duplicado: {sample}/{cavity}")
        seen.add((sample, cavity))
        table = cmm.correct_sign(cmm.read_csv(file["ruta"]))
        element, previous = "", None
        for row in table.to_dict("records"):
            block, idx = row["bloque"].strip(), int(row["idx"])
            group = (block, row["ocurrencia"])
            if group != previous:
                element, previous = "", group
            element = row["id_cmm"] or element
            key, ids, kind = catalog_group(block)
            entry = entries.setdefault(
                key,
                {
                    "id": key,
                    "numbers": ids,
                    "kind": kind,
                    "title": block,
                    "series": {},
                    "actions": [],
                },
            )
            identity = csv_identity(row, element) if block.startswith("N170") else None
            series_key = (
                "|".join(map(str, identity))
                if identity
                else f"{block}|{row['ocurrencia']}|{idx}"
            )
            label = f"{block} · [{idx}] {row['caracteristica']}"
            if identity:
                label = f"{identity[1]} · {'GX' if idx == 1 else 'LP máximo'}"
            unit = "°" if str(row["caracteristica"]).startswith("Phi") else "mm"
            series = entry["series"].setdefault(
                series_key,
                {
                    "id": series_key,
                    "label": label,
                    "unit": unit,
                    "records": {},
                    "block": block,
                    "idx": idx,
                },
            )
            if sample in series["records"].get(cavity, {}):
                raise ValueError(
                    f"Evaluación duplicada: {key}/{series_key}/{cavity}/{sample}"
                )
            nominal, low, high, measured = (
                number(row[k]) for k in ("nominal", "tol_inf", "tol_sup", "medido")
            )
            lower = nominal + low if nominal is not None and low is not None else None
            upper = nominal + high if nominal is not None and high is not None else None
            series["records"].setdefault(cavity, {})[sample] = {
                "value": measured,
                "lower": lower,
                "upper": upper,
                "status": result(measured, lower, upper),
                "reported_nok": bool(row["nok_original"]),
                "corrected": bool(row["signo_corregido"]),
                "original_value": number(row["medido_original"]),
                "source": source(
                    file["ruta"],
                    root,
                    f"{block} · aparición {row['ocurrencia']} · fila {idx} · CMM {element or '—'}",
                ),
            }
            row_count += 1
    for entry in entries.values():
        entry["actions"] = [
            a["id"]
            for a in actions.values()
            if set(entry["numbers"]) & set(a["features"])
        ]
        entry["reviewed_case"] = entry["id"] if entry["id"] in reviewed_cases else None
        series = list(entry["series"].values())
        if entry["id"] == "N165":
            series.sort(
                key=lambda s: (
                    0
                    if s["block"].startswith("GLOBAL")
                    else 1
                    if s["block"].startswith("N165")
                    else 2,
                    int(match[1])
                    if (match := re.match(r"POINT\s+(\d+)", s["block"]))
                    else 0,
                    s["idx"],
                )
            )
        entry["series"] = series
    return {
        "entries": sorted(
            entries.values(), key=lambda e: (e["kind"] != "dimension", e["id"])
        ),
        "row_count": row_count,
        "files": len(seen),
    }
