"""Content adapters. Viewers use the document UUID, not a filesystem location.

Two interchangeable sources serve the same dataset with the same relative paths:
the local folder (`ASSETS_ROOT`, the default) and SharePoint through Microsoft
Graph (`SHAREPOINT_ENABLED=true`, see `app.sharepoint`). Local sources are
metadata-only until content is explicitly requested. Keep Microsoft identities
out of feature/viewer APIs.
"""

import hashlib
import json
import mimetypes
import os
import stat
from pathlib import Path, PurePosixPath

from fastapi import HTTPException

from app import sharepoint
from app.core.config import settings
from app.models import FileStatus, SourceEntry, SourceListing, StoredFile
from app.source_types import SourceError, SourceItem

__all__ = ["SourceError", "SourceItem"]


def local_path(relative: str, *, directory: bool = False) -> Path:
    """Reject absolute paths, traversal, alternate streams and symlink escapes."""
    if not settings.ASSETS_ROOT:
        raise SourceError(
            "unavailable", "La carpeta de referencia no está configurada.", 503
        )
    if (
        relative and ("\\" in relative or ":" in relative or "\x00" in relative)
    ) or relative.startswith("/"):
        raise SourceError("unavailable", "Ruta de referencia no válida.", 400)
    parts = relative.split("/") if relative else []
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        raise SourceError("unavailable", "Ruta de referencia no válida.", 400)
    if not directory and not parts:
        raise SourceError("unavailable", "Selecciona un fichero.", 400)
    try:
        root = Path(settings.ASSETS_ROOT).resolve(strict=True)
        candidate = root.joinpath(*parts)
        # Windows OneDrive reparse points are not necessarily symbolic links.
        if any(
            root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts) + 1)
        ):
            raise SourceError("unavailable", "No se permiten enlaces simbólicos.", 400)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise SourceError(
                "unavailable", "Ruta fuera de la carpeta de referencia.", 400
            )
        info = resolved.stat()
        if getattr(info, "st_file_attributes", 0) & (0x400000 | 0x1000 | 0x40000):
            raise SourceError(
                "unavailable",
                "El archivo está solo en la nube. Hazlo disponible localmente.",
            )
        if directory and not stat.S_ISDIR(info.st_mode):
            raise SourceError("missing", "Carpeta no encontrada.", 404)
        if not directory and not stat.S_ISREG(info.st_mode):
            raise SourceError("missing", "Fichero no encontrado.", 404)
        return resolved
    except FileNotFoundError:
        raise SourceError(
            "missing",
            "Archivo o carpeta no encontrado. Puedes volver a vincularlo.",
            404,
        )
    except (OSError, RuntimeError):
        raise SourceError(
            "unavailable", "No se puede acceder a la carpeta de referencia.", 503
        )


def stamp(path: Path) -> str:
    info = path.stat()
    # Change detector, not a content hash or an archive of historical versions.
    return f"{info.st_mtime_ns}:{info.st_size}"


def reference_key(path: str, version: str) -> str:
    """Deduplicate a reference by dataset, relative path and observed version."""
    return hashlib.sha256(
        json.dumps([settings.ASSETS_SOURCE_ID, path, version]).encode()
    ).hexdigest()


def content_type(path: str) -> str:
    cad = {
        ".stp": "model/step",
        ".step": "model/step",
        ".igs": "model/iges",
        ".iges": "model/iges",
    }
    return (
        cad.get(PurePosixPath(path).suffix.lower())
        or mimetypes.guess_type(path)[0]
        or "application/octet-stream"
    )


def sharepoint_reference(document: StoredFile) -> bool:
    """A dataset reference read through Graph instead of the local folder."""
    return sharepoint.enabled() and document.source == "local"


def connected(document: StoredFile) -> None:
    if document.source_key != settings.ASSETS_SOURCE_ID:
        raise SourceError(
            "unavailable", "El origen de este documento no está conectado.", 503
        )


def resolve_document(document: StoredFile) -> Path:
    if document.source == "upload":
        path = settings.uploads_path / str(document.id)
        if not path.is_file():
            raise SourceError(
                "missing", "No se encuentra el contenido del fichero.", 404
            )
        return path
    if document.source == "local":
        connected(document)
        if sharepoint.enabled():
            # SharePoint always serves the latest version of the linked path.
            return sharepoint.download(sharepoint.item(document.source_path or ""))
        path = local_path(document.source_path or "")
        # A link registered through SharePoint has no local stamp to compare.
        if stamp(path) != document.source_version and not (
            document.source_version or ""
        ).startswith("sp:"):
            raise SourceError(
                "changed",
                "El original ha cambiado. Revisa la revisión y vuelve a vincularlo.",
            )
        return path
    raise SourceError(
        "unavailable", "El origen de este documento no está disponible.", 503
    )


def check_document(document: StoredFile) -> None:
    """Availability without downloading: SharePoint only reads the metadata."""
    if sharepoint_reference(document):
        connected(document)
        sharepoint.item(document.source_path or "")
    else:
        resolve_document(document)


def document_status(document: StoredFile) -> FileStatus:
    try:
        check_document(document)
        return FileStatus(
            state="available", message="Disponible", path=document.source_path
        )
    except SourceError as error:
        return FileStatus(
            state=error.state, message=error.message, path=document.source_path
        )
    except OSError:
        return FileStatus(
            state="unavailable",
            message="No se puede acceder al archivo.",
            path=document.source_path,
        )


def document_path(document: StoredFile) -> Path:
    try:
        return resolve_document(document)
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except OSError:
        raise HTTPException(status_code=503, detail="No se puede acceder al archivo.")


def document_check(document: StoredFile) -> None:
    try:
        check_document(document)
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except OSError:
        raise HTTPException(status_code=503, detail="No se puede acceder al archivo.")


def document_version(document: StoredFile) -> str:
    """The version of the bytes that would be served now, for derived caches."""
    if sharepoint_reference(document):
        try:
            connected(document)
            return sharepoint.item(document.source_path or "").version or ""
        except SourceError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message)
    return stamp(document_path(document))


def linked_version(document: StoredFile) -> str | None:
    """The version recorded when linking; through SharePoint, always the latest."""
    if sharepoint_reference(document):
        return document_version(document)
    return document.source_version


def source_item(relative: str, *, directory: bool = False) -> SourceItem:
    """A file or folder of the active source, validated and with its metadata."""
    if sharepoint.enabled():
        return sharepoint.item(relative, directory=directory)
    path = local_path(relative, directory=directory)
    if directory:
        return SourceItem(path=relative, directory=True, local=path)
    return SourceItem(
        path=relative, size=path.stat().st_size, version=stamp(path), local=path
    )


def with_metadata(item: SourceItem) -> SourceItem:
    """Size and version of a walked item, read only when a caller needs them."""
    if item.version is not None:
        return item
    path = item.local or local_path(item.path)
    return item.with_metadata(path.stat().st_size, stamp(path))


def item_file(item: SourceItem) -> Path:
    """A readable local file: the original, or SharePoint's cached version."""
    if sharepoint.enabled():
        return sharepoint.download(item if item.remote else sharepoint.item(item.path))
    return item.local or local_path(item.path)


def item_changed(item: SourceItem) -> bool:
    """A local original modified after its version was read. Cached copies are fixed."""
    if sharepoint.enabled():
        return False
    return stamp(item.local or local_path(item.path)) != item.version


def inside(relative: str, folder: str) -> bool:
    if sharepoint.enabled():
        return relative != folder and PurePosixPath(relative).is_relative_to(folder)
    return local_path(relative).is_relative_to(local_path(folder, directory=True))


def browse_source(
    relative: str, skip: int, limit: int, directories_only: bool = False
) -> SourceListing:
    if sharepoint.enabled():
        entries = [
            SourceEntry(
                name=item.name,
                path=item.path,
                directory=item.directory,
                size=None if item.directory else item.size,
            )
            for item in sharepoint.children(relative)
            if item.directory or not directories_only
        ]
        entries.sort(key=lambda entry: (not entry.directory, entry.name.casefold()))
        return SourceListing(
            configured=True,
            name=settings.ASSETS_SOURCE_NAME,
            path=relative,
            entries=entries[skip : skip + limit],
            count=len(entries),
        )
    if not settings.ASSETS_ROOT:
        return SourceListing(
            configured=False,
            name=settings.ASSETS_SOURCE_NAME,
            path="",
            entries=[],
            count=0,
        )
    directory = local_path(relative, directory=True)
    entries = []
    # No recursion or content reads. Each request visits one directory only.
    with os.scandir(directory) as items:
        for item in items:
            if item.name.startswith(".") or item.is_symlink():
                continue
            is_dir = item.is_dir(follow_symlinks=False)
            if directories_only and not is_dir:
                continue
            if not is_dir and not item.is_file(follow_symlinks=False):
                continue
            entries.append(
                SourceEntry(
                    name=item.name,
                    path="/".join(filter(None, [relative, item.name])),
                    directory=is_dir,
                    size=None if is_dir else item.stat().st_size,
                )
            )
    entries.sort(key=lambda entry: (not entry.directory, entry.name.casefold()))
    return SourceListing(
        configured=True,
        name=settings.ASSETS_SOURCE_NAME,
        path=relative,
        entries=entries[skip : skip + limit],
        count=len(entries),
    )
