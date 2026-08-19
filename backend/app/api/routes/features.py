import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Feature,
    FeatureAsset,
    FeatureAssetCreate,
    FeatureAssetPublic,
    FeatureAssetUpdate,
    FeatureCategory,
    FeatureCreate,
    FeatureDetail,
    FeatureFilters,
    FeatureNote,
    FeatureNoteCreate,
    FeatureNotePublic,
    FeatureNoteUpdate,
    FeaturePublic,
    FeaturesPublic,
    FeatureUpdate,
    Message,
    Part,
)

router = APIRouter(prefix="/features", tags=["features"])


def get_feature_or_404(session: SessionDep, feature_id: uuid.UUID) -> Feature:
    feature = session.get(Feature, feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


@router.get("/", response_model=FeaturesPublic)
def read_features(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str | None = None,
    category: FeatureCategory | None = None,
    tag: str | None = None,
    part_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Buscar features.

    `q` busca a la vez en nombre, descripcion, tags, codigo y nombre de las
    piezas, nombres de los adjuntos, y texto de warnings y lessons learned.
    `category`, `tag` y `part_id` son los filtros adicionales del dashboard.
    """
    features, count = crud.search_features(
        session=session,
        q=q,
        category=category,
        tag=tag,
        part_id=part_id,
        skip=skip,
        limit=limit,
    )
    return FeaturesPublic(
        data=[FeaturePublic.model_validate(feature) for feature in features],
        count=count,
    )


# Antes de /{feature_id}, si no "filters" se leeria como un id.
@router.get("/filters", response_model=FeatureFilters)
def read_feature_filters(session: SessionDep, _current_user: CurrentUser) -> Any:
    """
    Valores disponibles para los desplegables de filtrado del dashboard.
    """
    return crud.get_feature_filters(session=session)


@router.get("/{feature_id}", response_model=FeatureDetail)
def read_feature(
    session: SessionDep, _current_user: CurrentUser, feature_id: uuid.UUID
) -> Any:
    """
    Ficha completa de un feature: warnings, lessons learned y piezas ejemplo.
    """
    feature = get_feature_or_404(session, feature_id)
    return FeatureDetail.model_validate(feature)


@router.post("/", response_model=FeaturePublic)
def create_feature(
    *, session: SessionDep, current_user: CurrentUser, feature_in: FeatureCreate
) -> Any:
    """
    Crear un feature.
    """
    feature = crud.create_feature(
        session=session, feature_in=feature_in, owner_id=current_user.id
    )
    return FeaturePublic.model_validate(feature)


@router.put("/{feature_id}", response_model=FeaturePublic)
def update_feature(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    feature_in: FeatureUpdate,
) -> Any:
    """
    Editar un feature. Cualquier usuario autenticado puede hacerlo: la base de
    conocimiento es colaborativa.
    """
    feature = get_feature_or_404(session, feature_id)
    feature.sqlmodel_update(feature_in.model_dump(exclude_unset=True))
    session.add(feature)
    session.commit()
    session.refresh(feature)
    return FeaturePublic.model_validate(feature)


@router.delete("/{feature_id}")
def delete_feature(
    session: SessionDep, current_user: CurrentUser, feature_id: uuid.UUID
) -> Message:
    """
    Borrar un feature con sus warnings, lessons learned y piezas ejemplo.
    Solo el autor o un superusuario: es la unica accion irreversible.
    """
    feature = get_feature_or_404(session, feature_id)
    if not current_user.is_superuser and feature.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(feature)
    session.commit()
    return Message(message="Feature deleted successfully")


# ---------------------------------------------------------------------------
# Warnings y lessons learned
# ---------------------------------------------------------------------------


@router.post("/{feature_id}/notes", response_model=FeatureNotePublic)
def create_feature_note(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    note_in: FeatureNoteCreate,
) -> Any:
    """
    Anadir una advertencia (`kind=warning`) o leccion aprendida (`kind=lesson`).
    """
    get_feature_or_404(session, feature_id)
    return crud.create_feature_note(
        session=session, note_in=note_in, feature_id=feature_id
    )


@router.put("/notes/{note_id}", response_model=FeatureNotePublic)
def update_feature_note(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    note_id: uuid.UUID,
    note_in: FeatureNoteUpdate,
) -> Any:
    """
    Editar una advertencia o leccion aprendida.
    """
    note = session.get(FeatureNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.sqlmodel_update(note_in.model_dump(exclude_unset=True))
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.delete("/notes/{note_id}")
def delete_feature_note(
    session: SessionDep, _current_user: CurrentUser, note_id: uuid.UUID
) -> Message:
    """
    Borrar una advertencia o leccion aprendida.
    """
    note = session.get(FeatureNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    session.delete(note)
    session.commit()
    return Message(message="Note deleted successfully")


# ---------------------------------------------------------------------------
# Piezas en las que aparece el feature
# ---------------------------------------------------------------------------


@router.post("/{feature_id}/parts/{part_id}", response_model=FeatureDetail)
def link_feature_part(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    part_id: uuid.UUID,
) -> Any:
    """
    Declarar que el feature existe en esa pieza, tenga ficheros o no.

    Adjuntar un fichero a una pieza ya la hace aparecer en la ficha; esto es
    para las piezas de las que todavia no hay nada subido.
    """
    feature = get_feature_or_404(session, feature_id)
    part = session.get(Part, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    if part not in feature.parts:
        feature.parts.append(part)
        session.add(feature)
        session.commit()
        session.refresh(feature)
    return FeatureDetail.model_validate(feature)


@router.delete("/{feature_id}/parts/{part_id}")
def unlink_feature_part(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    part_id: uuid.UUID,
) -> Message:
    """
    Quitar la declaracion. Los adjuntos de esa pieza no se tocan: si los hay, la
    pieza sigue saliendo en la ficha porque tiene ficheros.
    """
    feature = get_feature_or_404(session, feature_id)
    part = session.get(Part, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    if part in feature.parts:
        feature.parts.remove(part)
        session.add(feature)
        session.commit()
    return Message(message="Part unlinked successfully")


# ---------------------------------------------------------------------------
# Piezas ejemplo (los ficheros: molde, CAD, escaneo, plano 2D, Moldflow)
# ---------------------------------------------------------------------------


@router.post("/{feature_id}/assets", response_model=FeatureAssetPublic)
def create_feature_asset(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    asset_in: FeatureAssetCreate,
) -> Any:
    """
    Adjuntar el fichero de una pieza. El fichero se sube antes por `/files/` y
    aqui se referencia con `file_id`.
    """
    get_feature_or_404(session, feature_id)
    if asset_in.part_id and not session.get(Part, asset_in.part_id):
        raise HTTPException(status_code=404, detail="Part not found")
    asset = crud.create_feature_asset(
        session=session, asset_in=asset_in, feature_id=feature_id
    )
    return FeatureAssetPublic.model_validate(asset)


@router.put("/assets/{asset_id}", response_model=FeatureAssetPublic)
def update_feature_asset(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    asset_id: uuid.UUID,
    asset_in: FeatureAssetUpdate,
) -> Any:
    """
    Editar un fichero adjunto.
    """
    asset = session.get(FeatureAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset_in.part_id and not session.get(Part, asset_in.part_id):
        raise HTTPException(status_code=404, detail="Part not found")
    asset.sqlmodel_update(asset_in.model_dump(exclude_unset=True))
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return FeatureAssetPublic.model_validate(asset)


@router.delete("/assets/{asset_id}")
def delete_feature_asset(
    session: SessionDep, _current_user: CurrentUser, asset_id: uuid.UUID
) -> Message:
    """
    Quitar un fichero adjunto del feature. El fichero subido no se borra.
    """
    asset = session.get(FeatureAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    session.delete(asset)
    session.commit()
    return Message(message="Asset deleted successfully")
