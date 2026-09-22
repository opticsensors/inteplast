"""Preview, validate and append CMM imports; never assign their cotas to a feature."""

import copy
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.core.config import settings
from app.evidence import job_id, register_document
from app.file_sources import SourceError, local_path
from app.ingestion.common import result
from app.ingestion.measurement_csv import READER, content_hash, parse
from app.knowledge_models import EvidenceJob, JobPublic, PartCharacteristic
from app.measurement_models import (
    MeasurementCommitRequest,
    MeasurementCommitResult,
    MeasurementFilePreview,
    MeasurementFileSelection,
    MeasurementFileStatus,
    MeasurementImport,
    MeasurementImportSummary,
    MeasurementPreview,
    MeasurementPreviewRequest,
)
from app.models import Part, get_datetime_utc

MAX_BYTES = 10 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def context_key(part: Part) -> str:
    return digest(
        [str(part.id), part.code, part.folder_path, settings.ASSETS_SOURCE_ID, READER]
    )


def imported(session: Session, part_id: uuid.UUID) -> list[MeasurementImport]:
    return list(
        session.exec(
            select(MeasurementImport)
            .where(MeasurementImport.part_id == part_id)
            .order_by(col(MeasurementImport.imported_at), col(MeasurementImport.id))
        ).all()
    )


def natural(value: str) -> list[Any]:
    return [int(v) if v.isdigit() else v.casefold() for v in re.split(r"(\d+)", value)]


def root_path(part: Part) -> Path:
    if not part.folder_path:
        raise HTTPException(422, "Selecciona primero la carpeta de esta pieza.")
    return local_path(part.folder_path, directory=True)


def file_path(part: Part, relative: str) -> Path:
    root = root_path(part)
    path = local_path(f"{part.folder_path}/{relative}")
    if not path.is_relative_to(root) or path.suffix.casefold() != ".csv":
        raise HTTPException(
            422, "Selecciona un CSV dentro de la carpeta de esta pieza."
        )
    return path


def discover(part: Part) -> list[str]:
    root = root_path(part)
    paths = []
    visited = 0
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = [
            f
            for f in folders
            if not f.startswith(".") and not Path(directory, f).is_symlink()
        ]
        visited += len(folders) + len(files)
        if visited > 20000:
            raise HTTPException(
                422,
                "La carpeta es demasiado amplia. Vincula la carpeta concreta de la pieza.",
            )
        for filename in files:
            if filename.lower().endswith(".csv") and not filename.startswith("."):
                paths.append(Path(directory, filename).relative_to(root).as_posix())
                if len(paths) > 250:
                    raise HTTPException(
                        422,
                        "Hay más de 250 CSV. Acota la carpeta antes de importarlos.",
                    )
    return sorted(paths)


def inferred(path: str) -> dict[str, str]:
    patterns = {
        "revision": r"(?<![a-z0-9])rev(?:ision|isión)?[ ._-]*([a-z0-9]+)",
        "sample": r"(?<![a-z])(?:intern|int|muestreo|sample)[ ._-]*(\d+)",
        "cavity": r"(?<![a-z])(?:cavidad|cavity|cav|c)[ ._-]*(\d{1,3})(?!\d)",
    }
    result = {}
    for key, pattern in patterns.items():
        values = {m.upper() for m in re.findall(pattern, path, re.I)}
        result[key] = next(iter(values)) if len(values) == 1 else ""
    return result


def normalize(selection: MeasurementFileSelection) -> MeasurementFileSelection:
    item = selection.model_copy()
    for field in ("revision", "sample", "cavity"):
        value = getattr(item, field).strip()
        if value and not re.fullmatch(r"[\w.-]{1,64}", value):
            raise HTTPException(
                422,
                "Usa letras, números, punto o guion para revisión, muestreo y cavidad.",
            )
        if field == "sample":
            value = re.sub(r"^intern[.\s]*", "", value, flags=re.I)
            if value.isdigit():
                value = value.zfill(2)
        if field == "cavity":
            value = re.sub(r"^c", "", value, flags=re.I)
            if value.isdigit():
                value = f"c{int(value)}"
        setattr(item, field, value)
    return item


def fingerprint(part: Part, item: MeasurementFileSelection) -> str:
    return digest(
        [
            str(part.id),
            item.revision,
            item.sample,
            item.cavity,
            item.sha256,
            READER,
            part.code == "3212"
            and part.folder_path == "3212 Pump Housing"
            and item.revision == "06",
        ]
    )


def legacy_study(session: Session, part_id: uuid.UUID) -> dict[str, Any]:
    frozen = session.exec(
        select(MeasurementImport)
        .where(
            MeasurementImport.part_id == part_id,
            MeasurementImport.reader == "legacy-pilot-snapshot",
        )
        .order_by(
            col(MeasurementImport.imported_at).desc(), col(MeasurementImport.id).desc()
        )
    ).first()
    if frozen and frozen.baseline:
        return frozen.baseline
    job = session.get(EvidenceJob, job_id("study", part_id))
    return job.payload if job and job.payload else {}


def save_refreshed_study(
    session: Session,
    part: Part,
    payload: dict[str, Any],
    key: str,
    user_id: uuid.UUID,
) -> None:
    """Only an explicit piece refresh advances the baseline; retain older snapshots."""
    preserve_legacy(session, part, user_id)
    identity = digest([str(part.id), "manual-study-refresh", key])
    if session.exec(
        select(MeasurementImport).where(MeasurementImport.fingerprint == identity)
    ).first():
        return
    session.add(
        MeasurementImport(
            part_id=part.id,
            fingerprint=identity,
            revision=payload["measurement_revision"],
            sample="",
            cavity="",
            source_path=part.folder_path or "",
            source_id=settings.ASSETS_SOURCE_ID,
            sha256=digest(payload),
            reader="legacy-pilot-snapshot",
            rows=[],
            baseline=copy.deepcopy(payload),
            imported_by=user_id,
        )
    )
    session.flush()


def preserve_legacy(session: Session, part: Part, user_id: uuid.UUID) -> None:
    """Keep the already loaded pilot consultable before the first CSV import."""
    identity = digest([str(part.id), "legacy-pilot-snapshot"])
    if session.exec(
        select(MeasurementImport).where(MeasurementImport.fingerprint == identity)
    ).first():
        return
    payload = legacy_study(session, part.id)
    if not payload.get("measurement_revision") or not payload.get("catalog"):
        return
    session.add(
        MeasurementImport(
            part_id=part.id,
            fingerprint=identity,
            revision=payload["measurement_revision"],
            sample="",
            cavity="",
            source_path=part.folder_path or "",
            source_id=settings.ASSETS_SOURCE_ID,
            sha256=digest(payload),
            reader="legacy-pilot-snapshot",
            rows=[],
            baseline=copy.deepcopy(payload),
            imported_by=user_id,
        )
    )
    session.flush()


def prepare(
    session: Session, part: Part, request: MeasurementPreviewRequest
) -> tuple[MeasurementPreview, dict[str, list[dict[str, Any]]]]:
    selections = request.files or [
        MeasurementFileSelection.model_validate({"path": p, **inferred(p)})
        for p in discover(part)
    ]
    if len({item.path for item in selections}) != len(selections):
        raise HTTPException(422, "El mismo archivo está seleccionado más de una vez.")
    history = imported(session, part.id)
    known = {row.fingerprint for row in history}
    revisions = {row.revision for row in history}
    legacy = legacy_study(session, part.id)
    if legacy.get("measurement_revision"):
        revisions.add(legacy["measurement_revision"])
    contexts = {(row.revision, row.sample, row.cavity) for row in history}
    legacy_revision = legacy.get("measurement_revision")
    if isinstance(legacy_revision, str):
        contexts.update(
            (legacy_revision, s, c)
            for s in legacy.get("samples", [])
            for c in legacy.get("cavities", [])
        )
    previews = []
    parsed: dict[str, list[dict[str, Any]]] = {}
    total = 0
    for selection in selections:
        item = normalize(selection)
        try:
            path = file_path(part, item.path)
            size = path.stat().st_size
            total += size
            if size > MAX_BYTES or total > MAX_TOTAL:
                raise ValueError(
                    "Límite de lectura: 10 MB por CSV y 64 MB por selección."
                )
            data = path.read_bytes()
            sha = content_hash(data)
            if item.sha256 and item.sha256 != sha:
                raise HTTPException(
                    409, f"Ha cambiado {item.path}. Vuelve a revisar la importación."
                )
            item.sha256 = sha
            # Reuse confirmed context only for these exact previously reviewed bytes.
            previous = [
                row
                for row in history
                if row.sha256 == sha
                and row.source_id == settings.ASSETS_SOURCE_ID
                and row.source_path == f"{part.folder_path}/{item.path}"
            ]
            for field in ("revision", "sample", "cavity"):
                values = {getattr(row, field) for row in previous}
                if not getattr(item, field) and len(values) == 1:
                    setattr(item, field, next(iter(values)))
            pilot = (
                part.code == "3212"
                and part.folder_path == "3212 Pump Housing"
                and item.revision == "06"
            )
            rows, issues = parse(data, pilot=pilot)
            parsed[item.path] = rows
            status: MeasurementFileStatus = "new"
            if not all((item.revision, item.sample, item.cavity)):
                status = "needs_context"
            elif fingerprint(part, item) in known:
                status = "imported"
            elif (item.revision, item.sample, item.cavity) in contexts:
                status = "replacement"
            elif item.revision in revisions:
                status = "new_sample"
            elif revisions:
                status = "new_revision"
            previews.append(
                MeasurementFilePreview(
                    **item.model_dump(),
                    status=status,
                    rows=len(rows),
                    cotas=len({n for row in rows for n in row["numbers"]}),
                    issues=issues,
                    examples=[
                        {
                            key: row[key]
                            for key in (
                                "numbers",
                                "nominal",
                                "tol_inf",
                                "tol_sup",
                                "value",
                                "unit",
                            )
                        }
                        for row in rows[:3]
                    ],
                )
            )
        except (ValueError, UnicodeError, OSError, SourceError) as error:
            message = (
                error.message
                if isinstance(error, SourceError)
                else "No se puede leer este archivo."
                if isinstance(error, OSError)
                else str(error)
            )
            previews.append(
                MeasurementFilePreview(
                    **item.model_dump(), status="unsupported", issues=[message]
                )
            )
    return MeasurementPreview(
        context_key=context_key(part),
        files=previews,
        notices=[]
        if previews
        else ["No se han encontrado archivos CSV en la carpeta de esta pieza."],
    ), parsed


def commit(
    session: Session, part: Part, user_id: uuid.UUID, request: MeasurementCommitRequest
) -> MeasurementCommitResult:
    # Serialize imports, including retries and imports initiated from another feature.
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    session.refresh(part)
    if request.context_key != context_key(part):
        raise HTTPException(
            409, "La pieza o su carpeta han cambiado. Vuelve a revisar los datos."
        )
    if not request.files or any(not f.sha256 for f in request.files):
        raise HTTPException(422, "Revisa y selecciona los archivos antes de importar.")
    preview, parsed = prepare(session, part, request)
    seen: dict[tuple[str, str, str], str] = {}
    for item in preview.files:
        if item.status in {"unsupported", "needs_context"}:
            raise HTTPException(
                422, f"Revisa el formato, revisión, muestreo y cavidad de {item.path}."
            )
        key = (item.revision, item.sample, item.cavity)
        if key in seen and seen[key] != item.sha256:
            raise HTTPException(
                409,
                "Hay archivos distintos para la misma revisión, muestreo y cavidad. Selecciona un solo export completo por combinación.",
            )
        seen[key] = item.sha256 or ""
        if item.status == "replacement" and not item.replace_existing:
            raise HTTPException(
                409,
                f"Confirma la sustitución de {item.path}; se conservarán las mediciones anteriores.",
            )
    added, skipped = 0, 0
    for item in preview.files:
        identity = fingerprint(part, item)
        if session.exec(
            select(MeasurementImport).where(MeasurementImport.fingerprint == identity)
        ).first():
            skipped += 1
            continue
        preserve_legacy(session, part, user_id)
        document = register_document(session, part, item.path)
        rows = copy.deepcopy(parsed[item.path])
        for row in rows:
            row["source"] = {
                "file_id": str(document.id),
                "path": item.path,
                "locator": f"Línea {row['line']} · {row['title']}",
            }
            for code in row["numbers"]:
                characteristic = session.exec(
                    select(PartCharacteristic).where(
                        PartCharacteristic.part_id == part.id,
                        PartCharacteristic.revision == item.revision,
                        PartCharacteristic.code == code,
                    )
                ).first()
                if characteristic is None:
                    session.add(
                        PartCharacteristic(
                            part_id=part.id,
                            revision=item.revision,
                            code=code,
                            title=row["title"][:255],
                        )
                    )
                    session.flush()
        session.add(
            MeasurementImport(
                part_id=part.id,
                fingerprint=identity,
                revision=item.revision,
                sample=item.sample,
                cavity=item.cavity,
                source_path=f"{part.folder_path}/{item.path}",
                source_id=settings.ASSETS_SOURCE_ID,
                sha256=item.sha256 or "",
                reader=READER,
                rows=rows,
                imported_by=user_id,
                imported_at=get_datetime_utc(),
            )
        )
        session.flush()
        added += 1
    session.commit()
    return MeasurementCommitResult(
        imported=added,
        skipped=skipped,
        revisions=sorted({i.revision for i in preview.files}, key=natural),
    )


def history_summary(
    session: Session, part_id: uuid.UUID
) -> list[MeasurementImportSummary]:
    rows = imported(session, part_id)
    active = {(r.revision, r.sample, r.cavity): r.id for r in rows}
    return [
        MeasurementImportSummary(
            **row.model_dump(exclude={"rows", "baseline"}),
            rows=row.baseline.get("catalog", {}).get("row_count", 0)
            if row.baseline
            else len(row.rows),
            active=not bool(row.baseline)
            and active[row.revision, row.sample, row.cavity] == row.id,
            baseline=bool(row.baseline),
        )
        for row in reversed(rows)
    ]


def study(
    session: Session,
    part: Part,
    revision: str | None,
    snapshot_id: uuid.UUID | None = None,
) -> tuple[JobPublic, list[str]]:
    batches = imported(session, part.id)
    legacy = legacy_study(session, part.id)
    revisions = {b.revision for b in batches}
    if legacy.get("measurement_revision"):
        revisions.add(legacy["measurement_revision"])
    all_revisions = sorted(revisions, key=natural)
    if snapshot_id:
        snapshot = next((b for b in batches if b.id == snapshot_id), None)
        if not snapshot:
            raise HTTPException(404, "Importación no encontrada en esta pieza.")
        revision = snapshot.revision
        batches = [b for b in batches if b.imported_at <= snapshot.imported_at]
        baseline = next(
            (
                b.baseline
                for b in reversed(batches)
                if b.baseline and b.revision == revision
            ),
            None,
        )
        legacy = baseline or {}
    selected = revision or (all_revisions[-1] if all_revisions else None)
    base = (
        copy.deepcopy(legacy) if selected == legacy.get("measurement_revision") else {}
    )
    active = {
        (b.sample, b.cavity): b
        for b in batches
        if b.revision == selected and not b.baseline
    }
    if not active:
        job = session.get(EvidenceJob, job_id("study", part.id))
        if job and not revision and not batches and job.state != "ready":
            return JobPublic(state=job.state, message=job.message), all_revisions
        if base:
            return JobPublic(state="ready", payload=base), all_revisions
        return JobPublic(state="empty"), all_revisions
    base = base or {
        "cases": {},
        "corrections": {},
        "actions": {},
        "action_index": {},
        "profiles": [],
        "support": [],
        "samples": [],
        "cavities": [],
        "catalog": {"entries": []},
    }
    entries = {e["id"]: e for e in base["catalog"]["entries"]}
    for (sample, cavity), batch in active.items():
        for entry in entries.values():
            if entry.get("kind") == "diagnostic":
                continue
            for series in entry["series"]:
                series["records"].get(cavity, {}).pop(sample, None)
        for row in batch.rows:
            code = "/".join(row["numbers"])
            entry = entries.setdefault(
                code,
                {
                    "id": code,
                    "numbers": row["numbers"],
                    "kind": "dimension",
                    "title": row["title"],
                    "series": [],
                    "actions": [],
                    "reviewed_case": None,
                },
            )
            series = next(
                (s for s in entry["series"] if s["id"] == row["series_id"]), None
            )
            if series is None:
                series = {
                    "id": row["series_id"],
                    "records": {},
                    **{
                        k: row[k]
                        for k in (
                            "label",
                            "block",
                            "idx",
                            "unit",
                            "element",
                            "evaluation",
                        )
                    },
                }
                entry["series"].append(series)
            lower, upper, value = row["lower"], row["upper"], row["value"]
            status = result(value, lower, upper)
            series["records"].setdefault(cavity, {})[sample] = {
                "value": value,
                "lower": lower,
                "upper": upper,
                "status": status,
                "source": row["source"],
                "nominal": row["nominal"],
                "tol_inf": row["tol_inf"],
                "tol_sup": row["tol_sup"],
                "deviation": row["deviation"],
            }
    base["catalog"]["entries"] = list(entries.values())
    base["samples"] = sorted(set(base["samples"]) | {s for s, _ in active}, key=natural)
    base["cavities"] = sorted(
        set(base["cavities"]) | {c for _, c in active}, key=natural
    )
    base["measurement_revision"] = selected
    base["csv_count"] = len(
        {
            (sample, cavity)
            for entry in entries.values()
            for series in entry["series"]
            for cavity, records in series["records"].items()
            for sample in records
        }
    )
    base["catalog"]["row_count"] = sum(
        len(records)
        for e in entries.values()
        for s in e["series"]
        for records in s["records"].values()
    )
    return JobPublic(state="ready", payload=base), all_revisions
