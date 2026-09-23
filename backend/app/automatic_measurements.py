"""Refresh measurements directly from supported source tables, preserving history."""

import copy
import hashlib
import json
import logging
import re
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app import measurement_imports
from app.core.config import settings
from app.evidence import register_document
from app.file_sources import local_path, stamp
from app.ingestion.measurement_tables import (
    cavity_label,
    conditions,
    csv_rows,
    report_rows,
    workbook,
)
from app.knowledge_models import PartCharacteristic
from app.measurement_models import MeasurementImport
from app.models import Part

READER = "automatic-tables-v1"
logger = logging.getLogger(__name__)
Context = tuple[str, str, str]


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def path_context(path: str, part_code: str = "") -> dict[str, str]:
    context = measurement_imports.inferred(path)
    if context["cavity"]:
        context["cavity"] = f"c{int(context['cavity'])}"
    if context["sample"]:
        context["sample"] = context["sample"].zfill(2)
    context["condition"] = conditions(path)
    context["variant"] = ""
    for segment in Path(path).with_suffix("").parts:
        # A repetition suffix belongs to the cavity, not the drawing revision.
        match = re.search(
            r"(?:^|[_ -])c(?:av[._ ]*)?(\d+)(\.\d+|bis|[-_]\d+)(?=$|[_ .-])",
            segment,
            re.I,
        )
        if match:
            if match[2].lstrip("-_") == part_code:
                continue
            context["cavity"], context["variant"] = cavity_label(
                "c" + match[1] + match[2]
            )
    return context


def collect(
    root: Path, paths: list[Path], *, pilot: bool = False
) -> dict[Context, list[dict[str, Any]]]:
    sources = []
    revisions: dict[str, set[str]] = defaultdict(set)
    total = 0
    part_code = re.match(r"\d+", root.name)
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() not in {".csv", ".xls", ".xlsx"} or re.search(
            r"retoqu|correction", relative, re.I
        ):
            continue
        size = path.stat().st_size
        version = stamp(path)
        total += size
        if size > 16 * 1024 * 1024 or total > 128 * 1024 * 1024:
            raise HTTPException(
                422, "Los archivos de mediciones superan el tamaño admitido."
            )
        context = path_context(relative, part_code[0] if part_code else "")
        try:
            if path.suffix.lower() == ".csv":
                rows = csv_rows(path.read_bytes(), pilot=pilot)
                revision = context["revision"]
            else:
                revision, rows = report_rows(workbook(path))
                revision = context["revision"] or revision
                if pilot:
                    # The pilot adapter already supplies XLS evaluations and forecasts.
                    rows = []
        except ValueError as error:
            if path.suffix.lower() == ".csv" and "No se reconoce un CSV CMM" in str(
                error
            ):
                # Point clouds have coordinates, not measured drawing characteristics.
                logger.info("No dimensional table in %s", relative)
                continue
            raise HTTPException(422, f"No se ha podido leer {path.name}.") from error
        if stamp(path) != version:
            raise HTTPException(
                409, f"{path.name} ha cambiado durante la lectura. Vuelve a actualizar."
            )
        if revision:
            revisions[context["sample"]].add(revision)
        sources.append((relative, context, revision, rows, version))
    all_revisions = set().union(*revisions.values()) if revisions else set()
    groups: dict[Context, list[dict[str, Any]]] = defaultdict(list)
    for relative, context, revision, rows, version in sources:
        known = revisions.get(context["sample"], all_revisions)
        revision = revision or (
            next(iter(known)) if len(known) == 1 else "sin-revision"
        )
        base_sample = context["sample"] or "archivo-" + digest(relative)[:8]
        for original in rows:
            row = copy.deepcopy(original)
            cavity = row.get("_cavity") or context["cavity"] or "sin-cavidad"
            condition = row.get("_condition") or context["condition"]
            variant = row.get("_variant") or context["variant"]
            sample = ".".join(filter(None, [base_sample, condition, variant]))
            if len(sample) > 64:
                sample = sample[:50] + "." + digest(sample)[:12]
            row["source"] = {
                "path": relative,
                "version": version,
                "locator": f"{row['_sheet']}!{row['_cell']}"
                if row.get("_report")
                else f"Línea {row['line']} · {row['title']}",
            }
            groups[revision, sample, cavity].append(row)
    for key, rows in groups.items():
        limits: dict[tuple[tuple[str, ...], float], list[dict[str, Any]]] = defaultdict(
            list
        )
        for row in rows:
            if (
                row.get("_report")
                and row["tol_inf"] is not None
                and row["tol_sup"] is not None
            ):
                limits[tuple(row["numbers"]), row["nominal"]].append(row)
        for row in rows:
            if row.get("_wide") and row["tol_inf"] is None and row["tol_sup"] is None:
                candidates = limits[tuple(row["numbers"]), row["nominal"]]
                if len({(r["tol_inf"], r["tol_sup"]) for r in candidates}) == 1:
                    for field in ("tol_inf", "tol_sup", "lower", "upper"):
                        row[field] = candidates[0][field]
                    row["tolerance_source"] = candidates[0]["source"].copy()
        # Individual CMM exports take precedence over summaries of the same cotas.
        rows.sort(
            key=lambda row: (
                2 if row.get("_report") else 1 if row.get("_wide") else 0,
                row["source"]["path"],
            )
        )
        retained: list[dict[str, Any]] = []
        csv_numbers = {
            n for row in rows if not row.get("_report") for n in row["numbers"]
        }
        individual_numbers = {
            n
            for row in rows
            if not row.get("_report") and not row.get("_wide")
            for n in row["numbers"]
        }
        seen: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row.get("_report") and set(row["numbers"]) <= csv_numbers:
                continue
            if row.get("_wide") and set(row["numbers"]) <= individual_numbers:
                continue
            previous = seen.get(row["series_id"])
            if previous:
                if all(
                    previous[k] == row[k]
                    for k in ("value", "nominal", "tol_inf", "tol_sup")
                ):
                    continue
                # Retain conflicting/repeated exports as separate series, with provenance.
                row["series_id"] += "|source:" + digest(row["source"]["path"])[:12]
                row["label"] += " · " + Path(row["source"]["path"]).stem
            seen[row["series_id"]] = row
            retained.append({k: v for k, v in row.items() if not k.startswith("_")})
        groups[key] = retained
    return groups


def refresh(
    session: Session,
    part: Part,
    user_id: uuid.UUID,
    paths: list[Path],
    *,
    used_files: dict[str, str] | None = None,
) -> tuple[int, int]:
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    root = local_path(part.folder_path or "", directory=True)
    groups = collect(
        root,
        paths,
        pilot=part.code == "3212" and part.folder_path == "3212 Pump Housing",
    )
    history = measurement_imports.imported(session, part.id)
    active = {(b.revision, b.sample, b.cavity): b for b in history if not b.baseline}
    # Empty snapshots retire observations removed from the current source files.
    for key, batch in active.items():
        if batch.reader == READER:
            groups.setdefault(key, [])
    documents = {}
    known = {
        (c.revision, c.code)
        for c in session.exec(
            select(PartCharacteristic).where(PartCharacteristic.part_id == part.id)
        ).all()
    }
    added, skipped = 0, 0
    for key, rows in groups.items():
        revision, sample, cavity = key
        checksum = digest(rows)
        previous = active.get(key)
        unchanged = bool(
            previous and previous.reader == READER and previous.sha256 == checksum
        )
        if used_files is not None:
            for row in rows:
                for source in [
                    row["source"],
                    *([row["tolerance_source"]] if "tolerance_source" in row else []),
                ]:
                    path = source["path"]
                    if used_files.get(path) != "imported":
                        used_files[path] = "unchanged" if unchanged else "imported"
        if unchanged:
            skipped += 1
            continue
        measurement_imports.preserve_legacy(session, part, user_id)
        for row in rows:
            for source in [
                row["source"],
                *([row["tolerance_source"]] if "tolerance_source" in row else []),
            ]:
                relative = source["path"]
                if relative not in documents:
                    if stamp(root / relative) != source["version"]:
                        raise HTTPException(
                            409,
                            f"{Path(relative).name} ha cambiado. Vuelve a actualizar.",
                        )
                    documents[relative] = register_document(session, part, relative)
                source["file_id"] = str(documents[relative].id)
            for code in row["numbers"]:
                if (revision, code) not in known:
                    session.add(
                        PartCharacteristic(
                            part_id=part.id,
                            revision=revision,
                            code=code,
                            title=row["title"][:255],
                        )
                    )
                    known.add((revision, code))
        session.add(
            MeasurementImport(
                part_id=part.id,
                fingerprint=digest(
                    [
                        str(part.id),
                        key,
                        checksum,
                        str(previous.id) if previous else None,
                        READER,
                    ]
                ),
                revision=revision,
                sample=sample,
                cavity=cavity,
                source_path=part.folder_path or "",
                source_id=settings.ASSETS_SOURCE_ID,
                sha256=checksum,
                reader=READER,
                rows=rows,
                imported_by=user_id,
            )
        )
        added += 1
    session.commit()
    return added, skipped
