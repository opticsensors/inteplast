"""«Globos verificados con .icp»: the strict check of a drawing, cached by version.

The result depends on the bytes of the PDF and of its candidate projects (the `.icp` of
its folder or of byte-identical copies, `evidence.drawing_project_files`). It is computed
the first time it is asked for, in a child process with a time limit, one per document
across API workers and a few at a time; meanwhile the caller gets "busy". A drawing
without candidate projects is answered at once, without rendering anything.
"""

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.evidence import drawing_project_snapshot, drawing_project_versions
from app.file_sources import document_path, document_version
from app.ingestion.icp_verification import RECIPE
from app.models import StoredFile

TIMEOUT_SECONDS = 180
SLOTS = threading.BoundedSemaphore(2)


def check_key(document: StoredFile, projects: list[list[str]]) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                str(document.id),
                str(document.version),
                document.source_path,
                document_version(document),
                projects,
                RECIPE,
            ]
        ).encode()
    ).hexdigest()


def check_directory(file_id: uuid.UUID) -> Path:
    return settings.uploads_path / "icp-checks" / str(file_id)


@contextmanager
def document_lock(file_id: uuid.UUID) -> Iterator[bool]:
    directory = check_directory(file_id)
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / ".lock", "a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run(pdf: Path, projects: list[list[str]], output: Path) -> None:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.icp_verifier",
                str(pdf),
                str(output),
                json.dumps(projects),
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            504, "La verificación del plano ha tardado demasiado."
        ) from error
    if result.returncode != 0 or not output.is_file():
        detail = (result.stderr or "").strip().splitlines()[-1:] or ["error"]
        raise HTTPException(422, f"No se puede verificar el plano: {detail[0]}")


def prepare(document: StoredFile) -> tuple[str, dict[str, Any] | None]:
    """("ready", result) or ("busy", None). Only PDFs with candidate projects are drawn."""
    if Path(document.filename).suffix.lower() != ".pdf":
        raise HTTPException(415, "Solo los planos PDF se verifican con .icp.")
    # One listing for the projects read and for the key they are stored under.
    projects, versions = drawing_project_snapshot(document)
    if not projects:
        return "ready", {"verified": False, "pages": [], "unreadable": []}
    key = check_key(document, versions)
    target = check_directory(document.id) / f"{key}.json"
    if target.is_file():
        return "ready", json.loads(target.read_text(encoding="utf-8"))
    if not SLOTS.acquire(blocking=False):
        return "busy", None
    try:
        with document_lock(document.id) as owner:
            if not owner:
                return "busy", None
            if not target.is_file():
                partial = target.with_name(f"{key}.{os.getpid()}.part")
                try:
                    run(document_path(document), projects, partial)
                    # The drawing or its projects changed while they were read: the
                    # result belongs to no version that can be asked for. Ask again.
                    if check_key(document, drawing_project_versions(document)) != key:
                        return "busy", None
                    os.replace(partial, target)
                finally:
                    partial.unlink(missing_ok=True)
                for old in check_directory(document.id).glob("*.json"):
                    if old != target:
                        old.unlink(missing_ok=True)
        return "ready", json.loads(target.read_text(encoding="utf-8"))
    finally:
        SLOTS.release()


def delete_checks(file_id: uuid.UUID) -> None:
    directory = check_directory(file_id)
    if directory.is_dir():
        for path in directory.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
        directory.rmdir()
