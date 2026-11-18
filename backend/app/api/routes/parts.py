import hashlib
import re
import uuid
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from app import crud, part_deletion
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.catalog_names import check_names
from app.core.config import settings
from app.file_sources import SourceError, source_item
from app.models import (
    FeatureAsset,
    FeaturePartLink,
    Part,
    PartCatalogPublic,
    PartCreate,
    PartFromFolder,
    PartPublic,
    PartsPublic,
    PartUpdate,
)
from app.part_deletion import PartDeletionResult, PartDeletionScope

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
        source_item(path, directory=True)
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
    check_names(session, part_in.family_id, part_in.customer_id)
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
    Editar el codigo, el nombre, la familia o el cliente de una pieza.
    """
    part = get_part_or_404(session, part_id)
    if part_in.code and part_in.code != part.code:
        clash = crud.get_part_by_code(session=session, code=part_in.code)
        if clash:
            raise HTTPException(
                status_code=409, detail="Ya existe una pieza con ese codigo"
            )
    changes = part_in.model_dump(exclude_unset=True, exclude={"references", "files"})
    check_names(session, changes.get("family_id"), changes.get("customer_id"))
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


@router.get("/{part_id}/deletion", response_model=PartDeletionScope)
def read_part_deletion(
    session: SessionDep, current_user: CurrentUser, part_id: uuid.UUID
) -> Any:
    """
    Alcance del borrado de una pieza: lo que se elimina y lo que se conserva.
    Solo superusuario. La clave devuelta confirma el borrado de estos datos.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return part_deletion.scope(session, get_part_or_404(session, part_id))


@router.delete("/{part_id}", response_model=PartDeletionResult)
def delete_part(
    session: SessionDep,
    current_user: CurrentUser,
    part_id: uuid.UUID,
    confirm: str | None = None,
) -> Any:
    """
    Borrar una pieza. Solo superusuario. Nunca borra originales ni carpetas.

    Sin `confirm` solo se borra una pieza sin uso. Con la clave que devuelve
    `GET /parts/{part_id}/deletion` se borran también sus cotas, mediciones,
    documentos propios y vínculos con features; los features se conservan.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    # FOR UPDATE also blocks new FK references until the deletion commits.
    part = part_deletion.lock_part(session, part_id)
    if confirm is None:
        count = feature_counts(session, [part_id]).get(part_id, 0)
        if count:
            raise HTTPException(
                status_code=409,
                detail=f"Pieza usada en {count} feature{'s' if count != 1 else ''}. "
                "Desvinculala antes de eliminarla del catalogo.",
            )
        current = part_deletion.scope(session, part)
        if (
            current.characteristics
            or current.measurement_imports
            or has_evidence(session, part_id)
        ):
            raise HTTPException(
                status_code=409,
                detail="La pieza conserva cotas o documentos de evidencia",
            )
        confirm = current.key
    deleted, removed = part_deletion.delete(session, part, confirm)
    session.commit()
    from app.api.routes.files import storage_path
    from app.icp_checks import delete_checks
    from app.previews import delete_preview
    from app.thumbnails import delete_thumbnails

    for document in removed:
        if document.source == "upload":
            storage_path(document.id).unlink(missing_ok=True)
        delete_preview(document.id)
        delete_thumbnails(document.id)
        delete_checks(document.id)
    return PartDeletionResult(message="Part deleted successfully", scope=deleted)


def has_evidence(session: SessionDep, part_id: uuid.UUID) -> bool:
    from app.knowledge_models import PartDocument

    return (
        session.exec(
            select(PartDocument).where(PartDocument.part_id == part_id)
        ).first()
        is not None
    )
