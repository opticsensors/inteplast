import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

from app import sharepoint
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.core.security import ALGORITHM
from app.file_sources import (
    SourceError,
    browse_source,
    content_type,
    document_check,
    document_path,
    document_status,
    reference_key,
    source_item,
    stamp,
)
from app.icp_checks import delete_checks
from app.icp_checks import prepare as prepare_icp_check
from app.models import (
    FeatureAsset,
    FileAccessPublic,
    FilePreview,
    FilePreviewPublic,
    FilePublic,
    FileStatus,
    LocalFileReference,
    Message,
    Part,
    RelinkFileReference,
    SourceListing,
    StoredFile,
    User,
)
from app.previews import delete_preview, preview_key, preview_path, queue_preview
from app.source_tables import SourceTable, read_table
from app.thumbnails import (
    delete_thumbnails,
    thumbnail_key,
    thumbnail_path,
    thumbnail_rotation,
)
from app.thumbnails import prepare as prepare_thumbnail_file

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


@router.get("/attachment-folder")
def read_attachment_folder(
    session: SessionDep,
    _current_user: CurrentUser,
    kind: Literal["mold", "moldflow"],
    part_id: uuid.UUID | None = None,
    file_id: uuid.UUID | None = None,
) -> str | None:
    if not sharepoint.enabled():
        return None
    part = session.get(Part, part_id) if part_id else None
    document = session.get(StoredFile, file_id) if file_id else None
    path = None
    if (
        document
        and document.source == "local"
        and document.source_key == settings.ASSETS_SOURCE_ID
    ):
        path = document.source_path
    try:
        return sharepoint.attachment_folder_url(
            kind, part.folder_path if part else None, path
        )
    except SourceError as error:
        raise HTTPException(error.status_code, error.message) from error


class ScreenshotChange(BaseModel):
    image_id: uuid.UUID | None
    previous_id: uuid.UUID | None


@router.get("/{file_id}/screenshot")
def read_attachment_screenshot(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> FilePublic | None:
    document = session.get(StoredFile, file_id)
    if not document:
        raise HTTPException(404, "Archivo no encontrado.")
    document_check(document)
    image = (
        session.get(StoredFile, document.screenshot_id)
        if document.screenshot_id
        else None
    )
    return FilePublic.model_validate(image) if image else None


@router.put("/{file_id}/screenshot")
def update_attachment_screenshot(
    session: SessionDep,
    _current_user: CurrentUser,
    file_id: uuid.UUID,
    body: ScreenshotChange,
) -> FilePublic | None:
    from app.feature_covers import COVER_IMAGE_TYPES

    document = session.exec(
        select(StoredFile).where(StoredFile.id == file_id).with_for_update()
    ).first()
    if not document:
        raise HTTPException(404, "Archivo no encontrado.")
    document_check(document)
    if document.screenshot_id not in (body.previous_id, body.image_id):
        raise HTTPException(409, "La captura ha cambiado. Vuelve a abrir el editor.")
    image = session.get(StoredFile, body.image_id) if body.image_id else None
    if body.image_id and (
        not image
        or image.id == file_id
        or image.source != "upload"
        or image.content_type.lower().split(";")[0].strip() not in COVER_IMAGE_TYPES
    ):
        raise HTTPException(422, "Selecciona una imagen subida para la captura.")
    document.screenshot_id = body.image_id
    session.add(document)
    session.commit()
    return FilePublic.model_validate(image) if image else None


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
        item = source_item(body.path)
        version = item.version or ""
        filename = item.local.name if item.local else item.name
        return {
            "filename": filename,
            "content_type": content_type(filename),
            "size": item.size or 0,
            "source": "local",
            "source_key": settings.ASSETS_SOURCE_ID,
            "source_path": body.path,
            "source_version": version,
            "version": uuid.uuid4(),
            "revision": body.revision or None,
            "reference_key": reference_key(body.path, version),
        }
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except OSError:
        raise HTTPException(status_code=503, detail="No se puede acceder al archivo.")


def existing_reference(
    session: SessionDep, metadata: dict[str, Any]
) -> StoredFile | None:
    document = session.exec(
        select(StoredFile).where(StoredFile.reference_key == metadata["reference_key"])
    ).first()
    if document is None and settings.SHAREPOINT_ENABLED:
        # SharePoint always shows the latest version: one document per path.
        document = session.exec(
            select(StoredFile)
            .where(
                StoredFile.source == "local",
                StoredFile.source_key == metadata["source_key"],
                StoredFile.source_path == metadata["source_path"],
            )
            .order_by(col(StoredFile.created_at).desc())
        ).first()
    return document


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

    existing = existing_reference(session, metadata)
    if existing:
        return reuse(existing)
    document = StoredFile(**metadata)
    session.add(document)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = existing_reference(session, metadata)
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
    from app.knowledge_models import PartDocument

    if session.exec(
        select(PartDocument).where(PartDocument.file_id == file_id)
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Este original conserva evidencia importada. Registra la nueva versión como otro documento y actualiza los datos de la pieza.",
        )
    assets = session.exec(
        select(FeatureAsset).where(FeatureAsset.file_id == file_id)
    ).all()
    document.sqlmodel_update(reference_metadata(body))
    document.screenshot_id = None
    session.add(document)
    if any(asset.kind == "part" for asset in assets):
        from app.previews import queue_product_step

        queue_product_step(session, document.id, _current_user.id)
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


@router.get("/{file_id}/table", response_model=SourceTable)
def read_source_table(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> SourceTable:
    document = session.get(StoredFile, file_id)
    if not document:
        raise HTTPException(404, "Archivo no encontrado.")
    path = document_path(document)
    try:
        version = stamp(path)
        table = read_table(path, document.filename)
        if stamp(path) != version:
            raise HTTPException(
                409,
                "El original ha cambiado durante la lectura. Actualiza los datos de la pieza.",
            )
        return table
    except OSError as error:
        raise HTTPException(503, "No se puede acceder al archivo original.") from error


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
    document_check(document)
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
) -> uuid.UUID:
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
    return user_id


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
    preview = queue_preview(session, document, retry, current_user.id)
    session.commit()
    session.refresh(preview)
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
        user_id = get_current_user(session, credentials.credentials).id
    elif token:
        user_id = authorize_file_token(session, file_id, token, purpose="file-preview")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    document = session.get(StoredFile, file_id)
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    with sharepoint.acting_as(user_id):
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


class ThumbnailPublic(BaseModel):
    state: Literal["ready", "busy"]
    url: str | None = None
    rotation: int = 0


class IcpCheckPublic(BaseModel):
    state: Literal["ready", "busy"]
    # True only when one .icp of the drawing passes the strict check on some page.
    verified: bool | None = None


@router.post("/{file_id}/icp-check", response_model=IcpCheckPublic)
def check_drawing_icp(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> IcpCheckPublic:
    """«Globos verificados con .icp»: strict check of a drawing, once per version.

    "busy" means that the drawing or others are being checked: ask again later.
    """
    document = session.get(StoredFile, file_id)
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    state, result = prepare_icp_check(document)
    if state == "busy" or result is None:
        return IcpCheckPublic(state="busy")
    return IcpCheckPublic(state="ready", verified=bool(result["verified"]))


@router.post("/{file_id}/thumbnail", response_model=ThumbnailPublic)
def prepare_thumbnail(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    page: int = Query(1, ge=1, le=2147483647),
) -> ThumbnailPublic:
    """Upright PDF page and its clockwise display correction, cached per version.

    "busy" means that other thumbnails are being drawn: show a placeholder and ask again.
    """
    document = session.get(StoredFile, file_id)
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    state, key = prepare_thumbnail_file(document, page)
    if state == "busy":
        return ThumbnailPublic(state="busy")
    try:
        rotation = thumbnail_rotation(thumbnail_path(file_id, key))
    except FileNotFoundError:
        # A newer version was generated between prepare and opening the PNG.
        return ThumbnailPublic(state="busy")
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = jwt.encode(
        {
            "sub": str(file_id),
            "uid": str(current_user.id),
            "purpose": "file-thumbnail",
            "cache_key": key,
            "version": str(document.version) if document.version else None,
            "exp": expires_at,
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return ThumbnailPublic(
        state="ready",
        url=f"{settings.API_V1_STR}/files/{file_id}/thumbnail?token={token}&page={page}",
        rotation=rotation,
    )


@router.get("/{file_id}/thumbnail")
def read_thumbnail(
    session: SessionDep,
    file_id: uuid.UUID,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer)
    ],
    token: str | None = None,
    page: int = Query(1, ge=1, le=2147483647),
) -> FileResponse:
    if credentials:
        user_id = get_current_user(session, credentials.credentials).id
    elif token:
        user_id = authorize_file_token(
            session, file_id, token, purpose="file-thumbnail"
        )
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    document = session.get(StoredFile, file_id)
    if document is None:
        raise HTTPException(status_code=404, detail="File not found")
    with sharepoint.acting_as(user_id):
        key = thumbnail_key(document, page)
    if token and not credentials:
        authorize_file_token(
            session, file_id, token, purpose="file-thumbnail", cache_key=key
        )
    path = thumbnail_path(file_id, key)
    if not path.is_file():
        raise HTTPException(
            status_code=409, detail="La miniatura ha cambiado. Vuelve a pedirla."
        )
    return FileResponse(
        path,
        media_type="image/png",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
            "Referrer-Policy": "no-referrer",
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
        user_id = get_current_user(session, credentials.credentials).id
    elif token:
        user_id = authorize_file_token(session, file_id, token)
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    stored = session.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    with sharepoint.acting_as(user_id):
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
    from app.knowledge_models import PartDocument

    if session.exec(
        select(PartDocument).where(PartDocument.file_id == file_id)
    ).first():
        raise HTTPException(
            status_code=409, detail="Documento utilizado como evidencia de una pieza"
        )
    session.delete(stored)
    session.commit()
    if stored.source == "upload":
        storage_path(file_id).unlink(missing_ok=True)
    delete_preview(file_id)
    delete_thumbnails(file_id)
    delete_checks(file_id)
    return Message(message="File deleted successfully")
