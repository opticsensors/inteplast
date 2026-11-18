"""First-page thumbnails of drawings, cached by the version of the original.

The PNG lives in the derived store next to the 3D previews. It is generated the first
time it is asked for, a few at a time: past that the caller gets "busy" and asks again,
showing a placeholder meanwhile. Local folders and SharePoint behave the same, since the
bytes come from the document adapter and its cache.

PyMuPDF runs in a child process with a time limit (`app.thumbnail_converter`). One
generation per document at a time, across API workers, through a file lock that the
system releases when the file is closed, also after a failure or a timeout.
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

from fastapi import HTTPException

from app.core.config import settings
from app.file_sources import document_path, document_version
from app.models import StoredFile

RECIPE = "pdf-first-page-png-v1/480"
WIDTH = 480
TIMEOUT_SECONDS = 60
# A couple of child processes at once per API worker.
SLOTS = threading.BoundedSemaphore(2)


def thumbnail_key(document: StoredFile) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                str(document.id),
                str(document.version),
                document.source,
                document.source_key,
                document.source_path,
                document_version(document),
                RECIPE,
            ]
        ).encode()
    ).hexdigest()


def thumbnail_directory(file_id: uuid.UUID) -> Path:
    return settings.uploads_path / "thumbnails" / str(file_id)


def thumbnail_path(file_id: uuid.UUID, key: str) -> Path:
    return thumbnail_directory(file_id) / f"{key}.png"


def convert(source: Path, partial: Path) -> None:
    """Run the converter; any failure or timeout becomes a clear HTTP error."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.thumbnail_converter",
                str(source),
                str(partial),
                str(WIDTH),
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "OMP_NUM_THREADS": "1"},
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            504, "La miniatura ha tardado demasiado. Vuelve a intentarlo."
        ) from error
    if result.returncode != 0 or not partial.is_file():
        detail = (result.stderr or "").strip().splitlines()[-1:] or ["error"]
        raise HTTPException(422, f"No se puede generar la miniatura: {detail[0]}")


@contextmanager
def document_lock(file_id: uuid.UUID) -> Iterator[bool]:
    """True while this process holds the document's generation; False if another does."""
    directory = thumbnail_directory(file_id)
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


def prepare(document: StoredFile) -> tuple[str, str]:
    """("ready", key) once the PNG exists for this version, or ("busy", key)."""
    if Path(document.filename).suffix.lower() != ".pdf":
        raise HTTPException(415, "Solo los planos PDF tienen miniatura.")
    key = thumbnail_key(document)
    target = thumbnail_path(document.id, key)
    if target.is_file():
        return "ready", key
    if not SLOTS.acquire(blocking=False):
        return "busy", key
    try:
        with document_lock(document.id) as owner:
            if not owner:
                return "busy", key
            if target.is_file():  # Drawn by another request meanwhile.
                return "ready", key
            source = document_path(document)
            # Not "*.png": the cleanup below never touches a drawing in progress.
            partial = target.with_name(f"{key}.{os.getpid()}.part")
            try:
                convert(source, partial)
                os.replace(partial, target)
            finally:
                partial.unlink(missing_ok=True)
            # Older versions of this document are no longer served.
            for old in thumbnail_directory(document.id).glob("*.png"):
                if old != target:
                    old.unlink(missing_ok=True)
        return "ready", key
    finally:
        SLOTS.release()


def delete_thumbnails(file_id: uuid.UUID) -> None:
    directory = thumbnail_directory(file_id)
    if directory.is_dir():
        for path in directory.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
        directory.rmdir()
