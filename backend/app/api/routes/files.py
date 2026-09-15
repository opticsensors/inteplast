import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.core.security import ALGORITHM
from app.models import FileAccessPublic, FilePublic, Message, StoredFile, User

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
    if not session.get(StoredFile, file_id) or not storage_path(file_id).is_file():
        raise HTTPException(status_code=404, detail="File not found")
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = jwt.encode(
        {
            "sub": str(file_id),
            "uid": str(current_user.id),
            "purpose": "file-access",
            "exp": expires_at,
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    url = f"{settings.API_V1_STR}/files/{file_id}?token={token}"
    if download:
        url += "&download=true"
    return FileAccessPublic(url=url, expires_at=expires_at)


def authorize_file_token(session: SessionDep, file_id: uuid.UUID, token: str) -> None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "uid", "purpose"]},
        )
        if payload["purpose"] != "file-access" or payload["sub"] != str(file_id):
            raise InvalidTokenError("Invalid file token")
        user_id = uuid.UUID(payload["uid"])
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired file link")
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired file link")


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
    path = storage_path(file_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File content not found")
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
    storage_path(file_id).unlink(missing_ok=True)
    return Message(message="File deleted successfully")
