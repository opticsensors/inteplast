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
    mold: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Buscar features.

    `q` busca a la vez en nombre, descripcion, tags, nombres y codigos de las
    piezas ejemplo, y texto de warnings y lessons learned. `category`, `tag` y
    `mold` son los filtros adicionales del dashboard.
    """
    features, count = crud.search_features(
        session=session,
        q=q,
        category=category,
        tag=tag,
        mold=mold,
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
# Piezas ejemplo (moldes CAD, piezas de referencia, planos 2D)
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
    Adjuntar una pieza ejemplo. El fichero se sube antes por `/files/` y aqui
    se referencia con `file_id`.
    """
    get_feature_or_404(session, feature_id)
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
    Editar una pieza ejemplo.
    """
    asset = session.get(FeatureAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
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
    Quitar una pieza ejemplo del feature. El fichero subido no se borra.
    """
    asset = session.get(FeatureAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    session.delete(asset)
    session.commit()
    return Message(message="Asset deleted successfully")
