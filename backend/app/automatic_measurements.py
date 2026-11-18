"""Refresh measurements directly from supported source tables, preserving history."""

import copy
import hashlib
import json
import logging
import re
import unicodedata
import uuid
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app import measurement_imports
from app.component_models import assigned_component, qualified, split_code
from app.core.config import settings
from app.evidence import register_document
from app.file_sources import (
    SourceItem,
    item_changed,
    item_file,
    source_item,
    with_metadata,
)
from app.ingestion.formula_flags import UnsupportedWorkbook
from app.ingestion.measurement_csv import UnsupportedMeasurementCsv
from app.ingestion.measurement_provenance import usable_measurement
from app.ingestion.measurement_tables import (
    cavity_label,
    conditions,
    csv_rows,
    flag_repeated_reports,
    report_rows,
    workbook,
)
from app.knowledge_models import PartCharacteristic
from app.measurement_models import MeasurementImport
from app.models import Part
from app.pilot import is_pilot

READER = "automatic-tables-v9"
logger = logging.getLogger(__name__)
Context = tuple[str, str, str]
# Report sheets with a Nominal header whose measurement columns cannot be identified.
UNREAD_SHEET = {
    "cavities_numbered_only": "las columnas de cavidad solo llevan un número",
    "no_cavity_label_and_no_characteristic_code": (
        "la columna de valores no rotula la cavidad y las filas no tienen número de cota"
    ),
    "no_cavity_label": "no se reconocen las columnas de cavidad",
}
SHEET_SEPARATOR = "\x1f"


def sheet_key(relative: str, sheet: str) -> str:
    """Key of a sheet-level entry in the per-file status mapping."""
    return f"{relative}{SHEET_SEPARATOR}{sheet}"


def split_sheet_key(key: str) -> tuple[str, str | None]:
    relative, separator, sheet = key.partition(SHEET_SEPARATOR)
    return relative, sheet if separator else None


def measurement_skip_reason(relative: str) -> str | None:
    """Classify files before reading them or counting them towards size limits."""
    path = PurePosixPath(relative)
    if path.suffix.lower() not in {".csv", ".xls", ".xlsx", ".xlsm"}:
        return "unsupported_extension"
    if re.search(r"retoqu|correction", relative, re.I):
        return "correction_folder"
    directories = unicodedata.normalize("NFKD", path.parent.as_posix())
    directories = directories.encode("ascii", "ignore").decode().lower()
    if re.search(r"(?:metod[eo]|method)[^/]*(?:medic|mesur|measur)", directories):
        return "measurement_method"
    return None


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
    folder: str,
    items: list[SourceItem],
    *,
    pilot: bool = False,
    file_issues: dict[str, str] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    components: list[dict[str, Any]] | None = None,
) -> dict[Context, list[dict[str, Any]]]:
    sources = []
    revisions: dict[str, set[str]] = defaultdict(set)
    total = 0
    part_code = re.match(r"\d+", PurePosixPath(folder).name)
    for item in sorted(items, key=lambda item: PurePosixPath(item.path)):
        relative = item.relative_to(folder)
        reason = measurement_skip_reason(relative)
        if reason:
            if diagnostics is not None:
                diagnostics.append(
                    {"path": relative, "status": "skipped", "reason": reason}
                )
            continue
        diagnostic: dict[str, Any] = {"path": relative, "status": "reading"}
        if diagnostics is not None:
            diagnostics.append(diagnostic)
        item = with_metadata(item)
        size = item.size or 0
        version = item.version or ""
        total += size
        diagnostic.update(size=size, version=version)
        if (
            size > settings.AUTO_MEASUREMENT_MAX_FILE_MB * 1024 * 1024
            or total > settings.AUTO_MEASUREMENT_MAX_TOTAL_MB * 1024 * 1024
        ):
            diagnostic.update(status="error", reason="size_limit")
            raise HTTPException(
                422, "Los archivos de mediciones superan el tamaño admitido."
            )
        context = path_context(relative, part_code[0] if part_code else "")
        path = item_file(item)
        unread: dict[str, str] = {}
        only_empty_templates = False
        try:
            if item.suffix == ".csv":
                rows = csv_rows(path.read_bytes(), pilot=pilot)
                revision = context["revision"]
            else:
                sheets = workbook(path)
                sheet_diagnostics: list[dict[str, Any]] = []
                revision, rows = report_rows(
                    sheets,
                    part_code=part_code[0] if part_code else "",
                    diagnostics=sheet_diagnostics,
                    component_sheets={
                        s
                        for s, _ in sheets
                        if assigned_component(components or [], relative, s)
                    },
                )
                diagnostic["sheets"] = sheet_diagnostics
                only_empty_templates = (
                    bool(sheet_diagnostics)
                    and any(
                        s.get("review") == "empty_dimensional_template"
                        for s in sheet_diagnostics
                    )
                    and all(
                        s.get("review") == "empty_dimensional_template"
                        or (
                            not s.get("nominal_header_rows")
                            and s.get("reason") == "sheet_name_not_supported"
                        )
                        for s in sheet_diagnostics
                    )
                )
                unread = {
                    sheet["sheet"]: UNREAD_SHEET[sheet["detail"]]
                    for sheet in sheet_diagnostics
                    if sheet.get("detail")
                }
                for sheet_info in sheet_diagnostics:
                    review = sheet_info.get("review")
                    if review == "unclassified_dimensional_table":
                        unread[sheet_info["sheet"]] = (
                            "tabla con nominales; falta clasificar su función y formato"
                        )
                    rejected = sheet_info.get("rejected_rows", [])
                    if rejected and file_issues is not None:
                        locations = ", ".join(str(row["row"]) for row in rejected[:8])
                        reasons = {row["reason"] for row in rejected}
                        labels = []
                        if "unsupported_characteristic_code" in reasons:
                            labels.append("identificadores no admitidos")
                        if "reversed_tolerances" in reasons:
                            labels.append("tolerancias invertidas")
                        if "unverified_measuring_device" in reasons:
                            labels.append("equipo de medida sin verificar")
                        if "derived_result" in reasons:
                            labels.append("resultados derivados")
                        file_issues[sheet_key(relative, sheet_info["sheet"])] = (
                            f"Pendiente: {len(rejected)} filas descartadas ({', '.join(labels)}); filas {locations}"
                            + ("…" if len(rejected) > 8 else "")
                        )
                    if (
                        review == "empty_dimensional_template"
                        and file_issues is not None
                    ):
                        file_issues[sheet_key(relative, sheet_info["sheet"])] = (
                            "Excluida: plantilla dimensional sin nominales en las filas de datos"
                        )
                revision = context["revision"] or revision
                # The pilot's dedicated adapter reads correction workbooks, not
                # these metrology reports. Keep their ordinary table readings.
        except (UnsupportedWorkbook, UnsupportedMeasurementCsv) as error:
            if item_changed(item):
                raise HTTPException(
                    409,
                    f"{item.name} ha cambiado durante la lectura. Vuelve a actualizar.",
                ) from error
            diagnostic.update(status="unsupported", reason=str(error))
            if file_issues is not None:
                file_issues[relative] = (
                    f"Pendiente: {error}; conservado como documento, sin medidas tabulares"
                )
                continue
            raise HTTPException(
                422, f"No se ha podido leer {item.name}: {error}"
            ) from error
        except ValueError as error:
            if item.suffix == ".csv" and "No se reconoce un CSV CMM" in str(error):
                # Point clouds have coordinates, not measured drawing characteristics.
                logger.info("No dimensional table in %s", relative)
                diagnostic.update(status="skipped", reason="not_dimensional_csv")
                continue
            diagnostic.update(status="error", reason=str(error))
            raise HTTPException(
                422, f"No se ha podido leer {item.name}: {error}"
            ) from error
        if item_changed(item):
            raise HTTPException(
                409, f"{item.name} ha cambiado durante la lectura. Vuelve a actualizar."
            )
        if components:
            assigned = []
            for row in rows:
                component = assigned_component(
                    components, relative, row.get("_sheet", "")
                )
                if not component:
                    if file_issues is not None:
                        issue_key = (
                            sheet_key(relative, row["_sheet"])
                            if row.get("_sheet")
                            else relative
                        )
                        file_issues[issue_key] = (
                            "Pendiente: asigna esta fuente a un componente; medidas sin incorporar"
                        )
                    continue
                row["component"] = component
                row["original_numbers"] = row["numbers"].copy()
                row["numbers"] = [qualified(n, component) for n in row["numbers"]]
                row["series_id"] = component + ":" + row["series_id"]
                row["label"] = component + " · " + row["label"]
                assigned.append(row)
            rows = assigned
        if file_issues is not None:
            if not rows and not unread and not only_empty_templates:
                file_issues.setdefault(
                    relative,
                    "Pendiente: no se ha reconocido una tabla dimensional; requiere revisión",
                )
            # A sheet that holds a table but was not read stays visible on its own,
            # also when other sheets of the same file were read.
            for sheet, reason in unread.items():
                file_issues[sheet_key(relative, sheet)] = (
                    f"Pendiente: {reason}; hoja sin leer"
                )
        if revision:
            revisions[context["sample"]].add(revision)
        sources.append((relative, context, revision, rows, version))
        diagnostic.update(status="read" if rows else "empty", observations=len(rows))
    flag_repeated_reports(
        {
            relative: rows
            for relative, _, _, rows, _ in sources
            if rows and rows[0].get("_report")
        }
    )
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
            row.setdefault("provenance_state", "medicion")
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
            row_revision = (
                (row.get("_revision") or revision)
                if components or "measurement_context" in row
                else revision
            )
            groups[row_revision, sample, cavity].append(row)
    for key, rows in groups.items():
        limits: dict[tuple[tuple[str, ...], float], list[dict[str, Any]]] = defaultdict(
            list
        )
        for row in rows:
            if (
                row.get("_report")
                and usable_measurement(row)
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
            if (
                row.get("_report")
                and usable_measurement(row)
                and set(row["numbers"]) <= csv_numbers
            ):
                continue
            if row.get("_wide") and set(row["numbers"]) <= individual_numbers:
                continue
            previous = seen.get(row["series_id"])
            if previous:
                if all(
                    previous.get(k) == row.get(k)
                    for k in (
                        "value",
                        "nominal",
                        "tol_inf",
                        "tol_sup",
                        "provenance_state",
                        "flags",
                    )
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
    paths: list[SourceItem],
    *,
    used_files: dict[str, str] | None = None,
) -> tuple[int, int]:
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    folder = part.folder_path or ""
    source_item(folder, directory=True)
    groups = collect(
        folder,
        paths,
        pilot=is_pilot(part),
        file_issues=used_files,
        components=part.components,
    )
    history = measurement_imports.imported(session, part.id)
    active = {(b.revision, b.sample, b.cavity): b for b in history if not b.baseline}
    # Empty snapshots retire observations removed from the current source files.
    for key, batch in active.items():
        if batch.reader.startswith("automatic-tables-"):
            groups.setdefault(key, [])
    documents = {}
    known = {
        (c.revision, qualified(c.code, c.component))
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
                    current = source_item("/".join(filter(None, [folder, relative])))
                    if current.version != source["version"]:
                        raise HTTPException(
                            409,
                            f"{Path(relative).name} ha cambiado. Vuelve a actualizar.",
                        )
                    documents[relative] = register_document(session, part, relative)
                source["file_id"] = str(documents[relative].id)
            for code in row["numbers"]:
                if (revision, code) not in known:
                    component, number = split_code(code)
                    session.add(
                        PartCharacteristic(
                            part_id=part.id,
                            revision=revision,
                            code=number,
                            component=component,
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
