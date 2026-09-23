import hashlib
import re
import uuid
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.file_sources import SourceError, local_path
from app.models import (
    FeatureAsset,
    FeaturePartLink,
    Message,
    Part,
    PartCatalogPublic,
    PartCreate,
    PartFromFolder,
    PartPublic,
    PartsPublic,
    PartUpdate,
)

router = APIRouter(prefix="/parts", tags=["parts"])


def folder_part(session: SessionDep, path: str) -> Part | None:
    return session.exec(select(Part).where(Part.folder_path == path)).first()


def commit_part(session: SessionDep) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe una pieza con ese codigo o carpeta"
        )


def folder_name(path: str) -> str:
    """Validate through the source adapter, keeping local paths out of the UI."""
    try:
        local_path(path, directory=True)
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    return (PurePosixPath(path).name if path else settings.ASSETS_SOURCE_NAME)[:255]


def get_part_or_404(session: SessionDep, part_id: uuid.UUID) -> Part:
    part = session.get(Part, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part


def feature_counts(
    session: SessionDep, part_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Count distinct features across explicit links and attached files."""
    if not part_ids:
        return {}
    usage = (
        select(FeaturePartLink.part_id, FeaturePartLink.feature_id)
        .where(col(FeaturePartLink.part_id).in_(part_ids))
        .union(
            select(FeatureAsset.part_id, FeatureAsset.feature_id).where(
                col(FeatureAsset.part_id).in_(part_ids)
            )
        )
        .subquery()
    )
    return dict(
        session.exec(
            select(usage.c.part_id, func.count()).group_by(usage.c.part_id)
        ).all()
    )


@router.get("/", response_model=PartsPublic)
def read_parts(
    session: SessionDep, _current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Todas las piezas (= proyectos), ordenadas por codigo. Es lo que puebla el
    selector de piezas, con el numero de features que utiliza cada una.
    """
    parts = crud.get_parts(session=session, skip=skip, limit=limit)
    count = session.exec(select(func.count()).select_from(Part)).one()
    counts = feature_counts(session, [part.id for part in parts])
    return PartsPublic(
        data=[
            PartCatalogPublic.model_validate(
                part, update={"feature_count": counts.get(part.id, 0)}
            )
            for part in parts
        ],
        count=count,
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
    if part_in.folder_path is not None:
        name = folder_name(part_in.folder_path)
        if not part_in.name or part_in.name == "Nueva pieza":
            part_in.name = name
    part = Part.model_validate(part_in)
    session.add(part)
    commit_part(session)
    session.refresh(part)
    return PartPublic.model_validate(part)


@router.post("/from-folder", response_model=PartPublic)
def create_part_from_folder(
    *, session: SessionDep, _current_user: CurrentUser, part_in: PartFromFolder
) -> Any:
    """Register or reuse an existing part folder; never create source directories."""
    path = part_in.folder_path
    name = folder_name(path)
    existing = folder_part(session, path)
    if existing:
        return existing
    prefix = re.match(r"^(\d{1,64})(?:[\s_-]|$)", name)
    code = (
        prefix[1]
        if prefix
        else f"PIEZA-{hashlib.sha256(path.encode()).hexdigest()[:12]}"
    )
    part = session.exec(select(Part).where(Part.code == code).with_for_update()).first()
    if part and part.folder_path == path:
        return part
    if part and part.folder_path is not None:
        raise HTTPException(
            status_code=409,
            detail="Ese codigo pertenece a una pieza con otra carpeta. Revisa la pieza existente.",
        )
    if part:
        part.folder_path = path
        if not part.name or part.name == "Nueva pieza":
            part.name = name
    else:
        part = Part(code=code, name=name, folder_path=path)
    session.add(part)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # A simultaneous selection of this folder returns the same identity.
        existing = folder_part(session, path)
        if existing:
            return existing
        raise HTTPException(
            status_code=409, detail="Ya existe una pieza con ese codigo o carpeta"
        )
    session.refresh(part)
    return part


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
    changes = part_in.model_dump(exclude_unset=True, exclude={"references", "files"})
    if (
        part.files_managed
        and "folder_path" in changes
        and changes["folder_path"] != part.folder_path
        and part_in.files is None
    ):
        raise HTTPException(
            422, "Cambia la carpeta junto con sus ficheros desde la ficha de la pieza."
        )
    if part_in.files is not None and part_in.references is not None:
        raise HTTPException(422, "Guarda los ficheros en una sola operación.")
    if part_in.files is not None:
        from app.part_files import save_files

        try:
            save_files(
                session,
                part,
                part_in.files,
                folder_path=changes.get("folder_path", part.folder_path),
            )
        except SourceError as error:
            raise HTTPException(error.status_code, error.message)
    if part_in.references:
        from app.part_setup import save_references

        if "folder_path" in changes and part_in.folder_path != part.folder_path:
            raise HTTPException(422, "Cambia la carpeta antes de editar sus archivos.")
        try:
            save_references(session, part, part_in.references, remember_choices=True)
        except SourceError as error:
            raise HTTPException(error.status_code, error.message)
    if "folder_path" in changes and part_in.folder_path is not None:
        name = folder_name(part_in.folder_path)
        previous_name = (
            PurePosixPath(part.folder_path).name
            if part.folder_path
            else settings.ASSETS_SOURCE_NAME
        )
        if "name" not in changes and (
            not part.name or part.name in {"Nueva pieza", previous_name}
        ):
            changes["name"] = name
    part.sqlmodel_update(changes)
    session.add(part)
    commit_part(session)
    session.refresh(part)
    return PartPublic.model_validate(part)


@router.delete("/{part_id}")
def delete_part(
    session: SessionDep, current_user: CurrentUser, part_id: uuid.UUID
) -> Message:
    """
    Borrar una pieza sin uso. Solo superusuario. Nunca borra documentos ni carpetas.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    # FOR UPDATE also blocks new FK references until the deletion commits.
    part = session.exec(
        select(Part).where(Part.id == part_id).with_for_update()
    ).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    count = feature_counts(session, [part_id]).get(part_id, 0)
    if count:
        raise HTTPException(
            status_code=409,
            detail=f"Pieza usada en {count} feature{'s' if count != 1 else ''}. "
            "Desvinculala antes de eliminarla del catalogo.",
        )
    from app.knowledge_models import PartCharacteristic, PartDocument
    from app.measurement_models import MeasurementImport

    if (
        session.exec(
            select(MeasurementImport).where(MeasurementImport.part_id == part_id)
        ).first()
        or session.exec(
            select(PartCharacteristic).where(PartCharacteristic.part_id == part_id)
        ).first()
        or session.exec(
            select(PartDocument).where(PartDocument.part_id == part_id)
        ).first()
    ):
        raise HTTPException(
            status_code=409, detail="La pieza conserva cotas o documentos de evidencia"
        )
    session.delete(part)
    session.commit()
    return Message(message="Part deleted successfully")
