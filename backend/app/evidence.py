"""Cached evidence imports. Source documents remain read-only and authenticated."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.file_sources import content_type, document_path, local_path, stamp
from app.knowledge_models import EvidenceJob, PartCharacteristic, PartDocument
from app.models import Part, StoredFile, get_datetime_utc
from app.previews import preview_lifespan

logger = logging.getLogger(__name__)
LOCK = 3212091801
RECIPE = "piece-evidence-v1"


def job_id(kind: str, target: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"inteplast:{kind}:{target}")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def drawing_key(document: StoredFile) -> str:
    return digest(
        [RECIPE, str(document.id), str(document.version), document.source_version]
    )


def study_key(part: Part) -> str:
    root = local_path(part.folder_path or "", directory=True)
    manifest = [
        (p.relative_to(root).as_posix(), stamp(p))
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".csv", ".xls", ".pptx", ".pdf", ".txt"}
    ]
    return digest([RECIPE, part.folder_path, sorted(manifest)])


def queue(
    session: Session,
    kind: str,
    target: uuid.UUID,
    key: str,
    *,
    requested_by: uuid.UUID | None = None,
) -> EvidenceJob:
    # Serialize creation/update for this identity, including concurrent requests.
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": job_id(kind, target).int % (2**63 - 1)},
    )
    job = session.get(EvidenceJob, job_id(kind, target))
    if job is None:
        job = EvidenceJob(
            id=job_id(kind, target),
            kind=kind,
            cache_key=key,
            part_id=target if kind == "study" else None,
            file_id=target if kind == "drawing" else None,
        )
    elif job.cache_key == key and job.state != "error":
        return job
    job.cache_key, job.state, job.message = key, "queued", None
    if requested_by is not None:
        job.payload = {**job.payload, "_refresh_requested_by": str(requested_by)}
    job.updated_at = get_datetime_utc()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def register_document(session: Session, part: Part, relative: str) -> StoredFile:
    from app.api.routes.files import reference_metadata
    from app.models import LocalFileReference

    metadata = reference_metadata(
        LocalFileReference(path=f"{part.folder_path}/{relative}")
    )
    stored = session.exec(
        select(StoredFile).where(StoredFile.reference_key == metadata["reference_key"])
    ).first()
    if stored is None:
        stored = StoredFile(**metadata)
        session.add(stored)
        session.flush()
    if session.get(PartDocument, (part.id, stored.id)) is None:
        session.add(PartDocument(part_id=part.id, file_id=stored.id))
    return stored


def publish_study(
    session: Session, part: Part, data: dict[str, Any], directory: Path
) -> dict[str, Any]:
    originals: dict[str, str] = {}
    images: dict[str, str] = {}

    def original(relative: str) -> str:
        if relative not in originals:
            originals[relative] = str(register_document(session, part, relative).id)
        return originals[relative]

    def image(relative: str) -> str:
        if relative not in images:
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError("Invalid derivative path")
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            fid = uuid.uuid5(
                uuid.NAMESPACE_URL, f"inteplast:evidence-image:{content_hash}"
            )
            stored = session.get(StoredFile, fid)
            if stored is None:
                stored = StoredFile(
                    id=fid,
                    filename=path.name,
                    content_type=content_type(path.name),
                    size=path.stat().st_size,
                )
                session.add(stored)
                session.flush()
                settings.uploads_path.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, settings.uploads_path / str(fid))
            if session.get(PartDocument, (part.id, fid)) is None:
                session.add(PartDocument(part_id=part.id, file_id=fid, kind="derived"))
                session.flush()
            images[relative] = str(fid)
        return images[relative]

    def convert(value: Any) -> Any:
        if isinstance(value, list):
            return [convert(v) for v in value]
        if isinstance(value, dict):
            if "path" in value and "url" in value:
                return {
                    "path": value["path"],
                    "locator": value.get("locator", ""),
                    "file_id": original(value["path"]),
                }
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, str) and value.startswith("assets/"):
            return image(value)
        if isinstance(value, str) and value.startswith("file:"):
            return None
        return value

    result: dict[str, Any] = convert(data)
    for entry in result["catalog"]["entries"]:
        for code in entry["numbers"]:
            characteristic = session.exec(
                select(PartCharacteristic).where(
                    PartCharacteristic.part_id == part.id,
                    PartCharacteristic.code == code,
                    PartCharacteristic.revision == "06",
                )
            ).first()
            if characteristic is None:
                characteristic = PartCharacteristic(
                    part_id=part.id, code=code, revision="06"
                )
            characteristic.title = entry["title"][:255]
            session.add(characteristic)
    result["measurement_revision"] = "06"
    result["adapter"] = "3212 / CSV CMM + DR(100%) + planes 1 y 2"
    result["source_files"] = sorted(originals)
    return result


def process_next(stop: threading.Event) -> bool:
    with Session(engine) as session:
        job = session.exec(
            select(EvidenceJob)
            .where(col(EvidenceJob.state).in_(["queued", "processing"]))
            .order_by(col(EvidenceJob.updated_at))
        ).first()
        if job is None:
            return False
        identity, key = job.id, job.cache_key
        job.state, job.message = "processing", None
        session.add(job)
        session.commit()
        try:
            part = session.get(Part, job.part_id) if job.part_id else None
            document = session.get(StoredFile, job.file_id) if job.file_id else None
            source = (
                document_path(document)
                if document
                else local_path(part.folder_path or "", directory=True)
                if part
                else None
            )
            if source is None:
                raise ValueError("Missing source")
            with tempfile.TemporaryDirectory(prefix="inteplast-evidence-") as temporary:
                destination = Path(temporary)
                env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
                with tempfile.TemporaryFile() as log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "app.evidence_converter",
                            job.kind,
                            str(source),
                            temporary,
                        ],
                        stdout=log,
                        stderr=log,
                        env=env,
                    )
                    started = time.monotonic()
                    try:
                        while process.poll() is None:
                            if stop.wait(0.25):
                                raise InterruptedError()
                            if time.monotonic() - started > 1800:
                                raise TimeoutError("Evidence import timed out")
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                    if process.returncode:
                        log.seek(0)
                        logger.error(
                            "Evidence converter: %s",
                            log.read().decode(errors="replace")[-5000:],
                        )
                        raise ValueError("Evidence reader failed")
                data = json.loads(
                    (destination / "result.json").read_text(encoding="utf-8")
                )
                session.expire_all()
                active = session.exec(
                    select(EvidenceJob)
                    .where(EvidenceJob.id == identity)
                    .with_for_update()
                ).first()
                if active is None or active.cache_key != key:
                    return True
                if document:
                    session.refresh(document)
                    document_path(document)  # Reject changed external bytes.
                    if drawing_key(document) != key:
                        raise ValueError("Drawing changed")
                    data.pop("source", None)
                    for page in data["pages"]:
                        page.pop("image", None)
                elif part:
                    session.refresh(part)
                    if study_key(part) != key:
                        raise ValueError("Sources changed during import")
                    data = publish_study(session, part, data, destination)
                    if active.payload.get("_refresh_requested_by"):
                        from app.measurement_imports import save_refreshed_study

                        save_refreshed_study(
                            session,
                            part,
                            data,
                            key,
                            uuid.UUID(active.payload["_refresh_requested_by"]),
                        )
                active.payload, active.state = data, "ready"
                active.updated_at = get_datetime_utc()
                session.add(active)
                session.commit()
        except InterruptedError:
            session.rollback()
        except Exception:
            logger.exception("Evidence processing failed: %s", identity)
            session.rollback()
            active = session.get(EvidenceJob, identity)
            if active and active.cache_key == key:
                active.state = "error"
                active.message = "No se ha podido preparar la evidencia. Comprueba los originales y vuelve a intentarlo."
                session.add(active)
                session.commit()
    return True


def worker(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            with Session(engine) as session:
                if session.execute(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK}
                ).scalar():
                    try:
                        process_next(stop)
                    finally:
                        session.execute(
                            text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK}
                        )
        except Exception:
            logger.exception("Evidence worker iteration failed")
        stop.wait(2)


@asynccontextmanager
async def evidence_lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    stop = threading.Event()
    thread = None
    if settings.EVIDENCE_WORKER_ENABLED:
        thread = threading.Thread(target=worker, args=(stop,), daemon=True)
        thread.start()
    try:
        async with preview_lifespan(app):
            yield
    finally:
        stop.set()
        if thread:
            thread.join(timeout=5)
