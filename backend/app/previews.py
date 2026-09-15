"""Durable preview queue; one native conversion at a time across API workers.

Postgres owns the queue/worker lock. The uploads volume owns disposable GLBs.
No client-supplied path reaches the converter; sources use the document adapter.
"""

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

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.file_sources import document_path, stamp
from app.models import FilePreview, StoredFile
from app.preview_converter import EXTENSIONS, MAX_INPUT_BYTES, RECIPE

logger = logging.getLogger(__name__)
WORKER_LOCK = 3212091501


def preview_key(document: StoredFile) -> str:
    source = document_path(document)
    return hashlib.sha256(
        json.dumps(
            [
                str(document.id),
                str(document.version),
                document.source,
                document.source_key,
                document.source_path,
                stamp(source),
                RECIPE,
            ]
        ).encode()
    ).hexdigest()


def preview_directory(file_id: uuid.UUID) -> Path:
    return settings.uploads_path / "previews" / str(file_id)


def preview_path(preview: FilePreview) -> Path:
    return preview_directory(preview.file_id) / f"{preview.cache_key}.glb"


def request_preview(session: Session, document: StoredFile, retry: bool) -> FilePreview:
    if Path(document.filename).suffix.lower() not in EXTENSIONS:
        raise HTTPException(
            status_code=415, detail="Este formato no tiene vista ligera."
        )
    if document.size > MAX_INPUT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El original supera el límite de conversión (512 MB).",
        )
    key = preview_key(document)
    preview = session.get(FilePreview, document.id)
    if preview is None:
        preview = FilePreview(file_id=document.id, cache_key=key)
    elif (
        preview.cache_key != key
        or (preview.state == "error" and retry)
        or (preview.state == "ready" and not preview_path(preview).is_file())
    ):
        preview.cache_key = key
        preview.state = "queued"
        preview.message = None
        preview.size = preview.triangles = 0
        preview.source_sha256 = None
    session.add(preview)
    session.commit()
    session.refresh(preview)
    return preview


def run_converter(
    source: Path, extension: str, output: Path, stop: threading.Event
) -> dict[str, Any]:
    environment = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    # Native libraries can crash or hang: keep them outside the API process.
    with (
        tempfile.TemporaryFile(dir=output.parent) as errors,
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "app.preview_converter",
                str(source),
                extension,
                str(output),
                str(settings.PREVIEW_MEMORY_MB),
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        ) as process,
    ):
        deadline = time.monotonic() + settings.PREVIEW_TIMEOUT_SECONDS
        try:
            while process.poll() is None:
                if stop.wait(0.5):
                    raise InterruptedError("Worker stopping")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Preview conversion timed out")
            if process.returncode:
                errors.seek(0, os.SEEK_END)
                errors.seek(max(0, errors.tell() - 4096))
                detail = errors.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Converter exited with code {process.returncode}: {detail}"
                )
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    metadata: dict[str, Any] = json.loads(output.with_suffix(".json").read_text())
    return metadata


def process_next(stop: threading.Event) -> bool:
    """Called only while holding the advisory lock (or explicitly in tests)."""
    with Session(engine) as session:
        preview = session.exec(
            select(FilePreview)
            .where(col(FilePreview.state).in_(["queued", "processing"]))
            .order_by(col(FilePreview.created_at))
        ).first()
        if preview is None:
            return False
        file_id, key = preview.file_id, preview.cache_key
        preview.state = "processing"
        session.add(preview)
        session.commit()
        document = session.get(StoredFile, file_id)
        if document is None:
            return True
        output = preview_path(preview)
        temporary = output.with_name(f"{key}.pending.glb")
        try:
            if preview_key(document) != key:
                raise ValueError("Source version no longer matches job")
            output.parent.mkdir(parents=True, exist_ok=True)
            metadata = run_converter(
                document_path(document),
                Path(document.filename).suffix.lower(),
                temporary,
                stop,
            )
            # Re-read under the same document row lock used by relink/request.
            session.expire_all()
            current = session.exec(
                select(StoredFile).where(StoredFile.id == file_id).with_for_update()
            ).first()
            active = session.get(FilePreview, file_id)
            if current is None or active is None or active.cache_key != key:
                return True
            if preview_key(current) != key:
                raise ValueError("Original changed during conversion")
            temporary.replace(output)
            temporary.with_suffix(".json").replace(output.with_suffix(".json"))
            active.state = "ready"
            active.message = (
                "Vista parcial: algunas superficies del STEP no se han podido "
                "representar. Descarga el original para consultar el molde completo."
                if metadata.get("step_incomplete_faces")
                else None
            )
            active.size = metadata["size"]
            active.triangles = metadata["triangles"]
            active.source_sha256 = metadata["source_sha256"]
            session.add(active)
            session.commit()
            # Keep only this document's current derivative; never touch originals.
            for old in output.parent.iterdir():
                if old.name not in {output.name, output.with_suffix(".json").name}:
                    old.unlink(missing_ok=True)
            logger.info("Preview ready: %s (%s bytes)", file_id, active.size)
        except InterruptedError:
            # Durable 'processing' is picked up by the next worker after restart.
            session.rollback()
        except Exception:
            logger.exception("Preview conversion failed for %s", file_id)
            session.rollback()
            session.expire_all()
            active = session.get(FilePreview, file_id)
            if active is not None and active.cache_key == key:
                active.state = "error"
                active.message = "No se ha podido preparar la vista 3D. Puedes reintentar o descargar el original."
                session.add(active)
                session.commit()
        finally:
            temporary.unlink(missing_ok=True)
            temporary.with_suffix(".json").unlink(missing_ok=True)
    return True


def worker(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            # Session retains its connection until unlock. Other API processes
            # cannot start a second expensive conversion; crash releases the lock.
            with Session(engine) as lock_session:
                acquired = lock_session.execute(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK}
                ).scalar()
                if acquired:
                    try:
                        process_next(stop)
                    finally:
                        lock_session.execute(
                            text("SELECT pg_advisory_unlock(:key)"),
                            {"key": WORKER_LOCK},
                        )
        except Exception:
            logger.exception("Preview worker iteration failed")
        stop.wait(2)


def delete_preview(file_id: uuid.UUID) -> None:
    directory = preview_directory(file_id)
    if directory.is_dir():
        shutil.rmtree(directory)


@asynccontextmanager
async def preview_lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    stop = threading.Event()
    thread = None
    if settings.PREVIEW_WORKER_ENABLED:
        thread = threading.Thread(target=worker, args=(stop,), daemon=True)
        thread.start()
    try:
        yield
    finally:
        stop.set()
        if thread:
            thread.join(timeout=5)
