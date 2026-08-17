import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import FilePublic, Message, StoredFile

router = APIRouter(prefix="/files", tags=["files"])

CHUNK_SIZE = 1024 * 1024


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
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored


@router.get("/{file_id}")
def read_file(session: SessionDep, file_id: uuid.UUID) -> FileResponse:
    """
    Servir un fichero por id.

    Sin autenticacion a proposito: el `<img src>` y los enlaces de descarga del
    frontend no pueden mandar la cabecera Authorization. El id es un UUID v4,
    que hace de secreto. Si algun dia hay ficheros confidenciales habra que
    pasar a URLs firmadas.
    """
    stored = session.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    path = storage_path(file_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File content not found")
    return FileResponse(
        path,
        media_type=stored.content_type,
        filename=stored.filename,
        content_disposition_type="inline",
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
