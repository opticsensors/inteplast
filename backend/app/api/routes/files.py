import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.core.security import ALGORITHM
from app.file_sources import (
    SourceError,
    browse_source,
    content_type,
    document_path,
    document_status,
    local_path,
    stamp,
)
from app.models import (
    FeatureAsset,
    FileAccessPublic,
    FilePreview,
    FilePreviewPublic,
    FilePublic,
    FileStatus,
    LocalFileReference,
    Message,
    RelinkFileReference,
    SourceListing,
    StoredFile,
    User,
)
from app.previews import delete_preview, preview_key, preview_path, request_preview

router = APIRouter(prefix="/files", tags=["files"])

CHUNK_SIZE = 1024 * 1024
optional_bearer = HTTPBearer(auto_error=False)
INLINE_TYPES = {
    "application/pdf",
    "application/octet-stream",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
    "image/bmp",
    "model/gltf-binary",
    "model/gltf+json",
    "model/stl",
    "model/obj",
    "model/step",
    "model/iges",
}


def storage_path(file_id: uuid.UUID) -> Path:
    return settings.uploads_path / str(file_id)


@router.get("/source", response_model=SourceListing)
def list_source(
    _current_user: CurrentUser,
    path: str = "",
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    directories_only: bool = False,
) -> SourceListing:
    """Browse one directory in the configured source, without reading file bytes."""
    try:
        return browse_source(path, skip, limit, directories_only)
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except OSError:
        raise HTTPException(
            status_code=503, detail="No se puede leer la carpeta de referencia."
        )


def reference_metadata(body: LocalFileReference) -> dict[str, Any]:
    try:
        path = local_path(body.path)
        version = stamp(path)
        return {
            "filename": path.name,
            "content_type": content_type(path.name),
            "size": path.stat().st_size,
            "source": "local",
            "source_key": settings.ASSETS_SOURCE_ID,
            "source_path": body.path,
            "source_version": version,
            "version": uuid.uuid4(),
            "revision": body.revision or None,
            "reference_key": hashlib.sha256(
                json.dumps([settings.ASSETS_SOURCE_ID, body.path, version]).encode()
            ).hexdigest(),
        }
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except OSError:
        raise HTTPException(status_code=503, detail="No se puede acceder al archivo.")


@router.post("/reference", response_model=FilePublic)
def reference_file(
    session: SessionDep, _current_user: CurrentUser, body: LocalFileReference
) -> Any:
    """Register a local original once. Never copy or modify its bytes."""
    metadata = reference_metadata(body)

    def reuse(document: StoredFile) -> StoredFile:
        if body.revision and body.revision != document.revision:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El archivo ya está vinculado con otra revisión. "
                    "Deja la revisión vacía para usar la existente, o abre "
                    "el documento y usa Volver a vincular para actualizarla."
                ),
            )
        return document

    existing = session.exec(
        select(StoredFile).where(StoredFile.reference_key == metadata["reference_key"])
    ).first()
    if existing:
        return reuse(existing)
    document = StoredFile(**metadata)
    session.add(document)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(StoredFile).where(
                StoredFile.reference_key == metadata["reference_key"]
            )
        ).first()
        if existing:
            return reuse(existing)
        raise
    session.refresh(document)
    return document


@router.put("/{file_id}/reference", response_model=FilePublic)
def relink_file(
    session: SessionDep,
    _current_user: CurrentUser,
    file_id: uuid.UUID,
    body: RelinkFileReference,
) -> Any:
    """Explicitly replace a location/revision while preserving the document UUID."""
    document = session.exec(
        select(StoredFile).where(StoredFile.id == file_id).with_for_update()
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="File not found")
    if document.source != "local":
        raise HTTPException(
            status_code=400, detail="Este documento no es una referencia local."
        )
    if document.version != body.expected_version:
        raise HTTPException(
            status_code=409,
            detail="Otra persona ha actualizado el vínculo. Recarga la ficha.",
        )
    assets = session.exec(
        select(FeatureAsset).where(FeatureAsset.file_id == file_id)
    ).all()
    document.sqlmodel_update(reference_metadata(body))
    session.add(document)
    for asset in assets:
        asset.name = document.filename
        session.add(asset)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="El archivo ya está registrado. Vincúlalo como otro documento.",
        )
    session.refresh(document)
    return document


@router.get("/{file_id}/status", response_model=FileStatus)
def file_status(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> FileStatus:
    document = session.get(StoredFile, file_id)
    if not document:
        raise HTTPException(status_code=404, detail="File not found")
    return document_status(document)


@router.post("/", response_model=FilePublic)
async def upload_file(
    *, session: SessionDep, _current_user: CurrentUser, file: UploadFile
) -> Any:
    """
    Subir un fichero (imagen de feature, CAD, plano PDF...).

    Los bytes van al disco (`settings.UPLOADS_DIR`) y la fila solo guarda los
    metadatos. El id devuelto es el que se referencia desde el feature o desde
    una de sus piezas ejemplo.
    """
    stored = StoredFile(
        filename=file.filename or "sin-nombre",
        content_type=file.content_type or "application/octet-stream",
    )
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    path = storage_path(stored.id)
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = 0

    try:
        with path.open("wb") as target:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB",
                    )
                target.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    stored.size = size
    try:
        session.add(stored)
        session.commit()
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    session.refresh(stored)
    return stored


@router.get("/{file_id}/access-url", response_model=FileAccessPublic)
def create_file_access_url(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    download: bool = False,
) -> FileAccessPublic:
    """Issue a short-lived link for an image, viewer or browser download."""
    document = session.get(StoredFile, file_id)
    if not document:
        raise HTTPException(status_code=404, detail="File not found")
    document_path(document)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = jwt.encode(
        {
            "sub": str(file_id),
            "uid": str(current_user.id),
            "purpose": "file-access",
            "version": str(document.version) if document.version else None,
            "exp": expires_at,
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    url = f"{settings.API_V1_STR}/files/{file_id}?token={token}"
    if download:
        url += "&download=true"
    return FileAccessPublic(url=url, expires_at=expires_at)


def authorize_file_token(
    session: SessionDep,
    file_id: uuid.UUID,
    token: str,
    *,
    purpose: str = "file-access",
    cache_key: str | None = None,
) -> None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "uid", "purpose"]},
        )
        if payload["purpose"] != purpose or payload["sub"] != str(file_id):
            raise InvalidTokenError("Invalid file token")
        if cache_key is not None and payload.get("cache_key") != cache_key:
            raise InvalidTokenError("Invalid preview version")
        user_id = uuid.UUID(payload["uid"])
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired file link")
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired file link")
    document = session.get(StoredFile, file_id)
    if document and payload.get("version") != (
        str(document.version) if document.version else None
    ):
        raise HTTPException(
            status_code=401,
            detail="El vínculo del documento ha cambiado. Vuelve a abrirlo.",
        )


@router.post("/{file_id}/preview", response_model=FilePreviewPublic)
def prepare_preview(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    retry: bool = False,
) -> FilePreviewPublic:
    """Idempotently queue a web GLB, or return a signed link to its cached result."""
    document = session.exec(
        select(StoredFile).where(StoredFile.id == file_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    preview = request_preview(session, document, retry)
    result = FilePreviewPublic(state=preview.state, message=preview.message)
    if preview.state == "ready":
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        token = jwt.encode(
            {
                "sub": str(file_id),
                "uid": str(current_user.id),
                "purpose": "file-preview",
                "cache_key": preview.cache_key,
                "version": str(document.version) if document.version else None,
                "exp": expires_at,
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        result.url = f"{settings.API_V1_STR}/files/{file_id}/preview?token={token}"
    return result


@router.get("/{file_id}/preview")
def read_preview(
    session: SessionDep,
    file_id: uuid.UUID,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer)
    ],
    token: str | None = None,
) -> FileResponse:
    # Authenticate before exposing document state, just like original downloads.
    if credentials:
        get_current_user(session, credentials.credentials)
    elif token:
        authorize_file_token(session, file_id, token, purpose="file-preview")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    document = session.get(StoredFile, file_id)
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    key = preview_key(document)
    if token and not credentials:
        authorize_file_token(
            session, file_id, token, purpose="file-preview", cache_key=key
        )
    preview = session.get(FilePreview, file_id)
    if (
        preview is None
        or preview.state != "ready"
        or preview.cache_key != key
        or not preview_path(preview).is_file()
    ):
        raise HTTPException(
            status_code=409, detail="Vuelve a abrir la vista para prepararla."
        )
    return FileResponse(
        preview_path(preview),
        media_type="model/gltf-binary",
        filename="vista-3d.glb",
        content_disposition_type="inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/{file_id}")
def read_file(
    session: SessionDep,
    file_id: uuid.UUID,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer)
    ],
    token: str | None = None,
    download: bool = False,
) -> FileResponse:
    """
    Servir un fichero por id.

    Require an active user's bearer token or a purpose-bound, expiring file link.
    """
    if credentials:
        get_current_user(session, credentials.credentials)
    elif token:
        authorize_file_token(session, file_id, token)
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    stored = session.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    path = document_path(stored)
    media_type = stored.content_type.split(";", 1)[0].strip().lower()
    inline = media_type in INLINE_TYPES and not download
    return FileResponse(
        path,
        media_type=media_type if inline else "application/octet-stream",
        filename=stored.filename,
        content_disposition_type="inline" if inline else "attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.delete("/{file_id}")
def delete_file(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> Message:
    """
    Borrar un fichero. Las referencias desde features y piezas ejemplo quedan a
    NULL (ON DELETE SET NULL), no se borra la ficha.
    """
    stored = session.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    session.delete(stored)
    session.commit()
    if stored.source == "upload":
        storage_path(file_id).unlink(missing_ok=True)
    delete_preview(file_id)
    return Message(message="File deleted successfully")
