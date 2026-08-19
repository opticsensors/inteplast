import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    Part,
    PartCreate,
    PartPublic,
    PartsPublic,
    PartUpdate,
)

router = APIRouter(prefix="/parts", tags=["parts"])


def get_part_or_404(session: SessionDep, part_id: uuid.UUID) -> Part:
    part = session.get(Part, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part


@router.get("/", response_model=PartsPublic)
def read_parts(
    session: SessionDep, _current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Todas las piezas (= proyectos), ordenadas por codigo. Es lo que puebla el
    desplegable al adjuntar un fichero.
    """
    parts = crud.get_parts(session=session, skip=skip, limit=limit)
    return PartsPublic(
        data=[PartPublic.model_validate(part) for part in parts], count=len(parts)
    )


@router.post("/", response_model=PartPublic)
def create_part(
    *, session: SessionDep, _current_user: CurrentUser, part_in: PartCreate
) -> Any:
    """
    Dar de alta una pieza. El codigo es unico: es la clave con la que se agrupan
    los ficheros de todos los features.
    """
    if crud.get_part_by_code(session=session, code=part_in.code):
        raise HTTPException(
            status_code=409, detail="Ya existe una pieza con ese codigo"
        )
    part = crud.create_part(session=session, part_in=part_in)
    return PartPublic.model_validate(part)


@router.put("/{part_id}", response_model=PartPublic)
def update_part(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    part_id: uuid.UUID,
    part_in: PartUpdate,
) -> Any:
    """
    Editar el codigo o el nombre de una pieza.
    """
    part = get_part_or_404(session, part_id)
    if part_in.code and part_in.code != part.code:
        clash = crud.get_part_by_code(session=session, code=part_in.code)
        if clash:
            raise HTTPException(
                status_code=409, detail="Ya existe una pieza con ese codigo"
            )
    part.sqlmodel_update(part_in.model_dump(exclude_unset=True))
    session.add(part)
    session.commit()
    session.refresh(part)
    return PartPublic.model_validate(part)


@router.delete("/{part_id}")
def delete_part(
    session: SessionDep, current_user: CurrentUser, part_id: uuid.UUID
) -> Message:
    """
    Borrar una pieza. Solo superusuario: la comparten todos los features.

    Los adjuntos no se borran, se quedan sin pieza (`part_id` a NULL) y la vista
    los agrupa aparte.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    part = get_part_or_404(session, part_id)
    session.delete(part)
    session.commit()
    return Message(message="Part deleted successfully")
