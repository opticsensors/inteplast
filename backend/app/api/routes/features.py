import re
import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.cad_covers import validate_cover
from app.models import (
    Feature,
    FeatureAsset,
    FeatureAssetCreate,
    FeatureAssetOrder,
    FeatureAssetPublic,
    FeatureAssetUpdate,
    FeatureCategory,
    FeatureCreate,
    FeatureDetail,
    FeatureFilters,
    FeatureNote,
    FeatureNoteCreate,
    FeatureNoteOrder,
    FeatureNotePublic,
    FeatureNoteUpdate,
    FeaturePartOrder,
    FeaturePublic,
    FeaturesPublic,
    FeatureUpdate,
    Message,
    Part,
    StoredFile,
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
    feature_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Buscar features.

    `q` busca a la vez en nombre, descripcion, tags, codigo y nombre de las
    piezas, nombres de los adjuntos, y texto de warnings y lessons learned.
    `category`, `tag`, `part_id` y `feature_id` se combinan con la búsqueda.
    """
    features, count = crud.search_features(
        session=session,
        q=q,
        category=category,
        tag=tag,
        part_id=part_id,
        feature_id=feature_id,
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
    if feature_in.tags and any(
        re.fullmatch(r"N\s*\d+(?:\.\d+)?", tag.strip(), re.I) for tag in feature_in.tags
    ):
        raise HTTPException(
            status_code=422,
            detail="Vincula los números de cota dentro de su pieza; los tags son globales.",
        )
    if feature_in.image_id and not session.get(StoredFile, feature_in.image_id):
        raise HTTPException(status_code=404, detail="File not found")
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
    if feature_in.tags and any(
        re.fullmatch(r"N\s*\d+(?:\.\d+)?", tag.strip(), re.I) for tag in feature_in.tags
    ):
        raise HTTPException(
            status_code=422,
            detail="Vincula los números de cota dentro de su pieza; los tags son globales.",
        )
    if feature_in.image_id and not session.get(StoredFile, feature_in.image_id):
        raise HTTPException(status_code=404, detail="File not found")
    changes = feature_in.model_dump(exclude_unset=True)
    if feature_in.cover_3d is not None:
        image = (
            session.get(StoredFile, feature_in.image_id)
            if feature_in.image_id
            else None
        )
        if not image or image.content_type not in {
            "image/png",
            "image/webp",
            "image/jpeg",
        }:
            raise HTTPException(
                422, "Guarda la imagen de portada junto con la selección 3D."
            )
        validate_cover(session, feature, feature_in.cover_3d)
        changes["cover_3d"] = feature_in.cover_3d.model_dump(mode="json")
    elif "image_id" in changes:
        # An uploaded/pasted image replaces the CAD cover as one atomic header edit.
        changes["cover_3d"] = None
    feature.sqlmodel_update(changes)
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


def save_positions(
    session: SessionDep,
    rows: Sequence[FeatureNote | FeatureAsset],
    ids: list[uuid.UUID],
) -> Message:
    by_id = {row.id: row for row in rows}
    if len(set(ids)) != len(ids) or set(ids) != set(by_id):
        raise HTTPException(
            status_code=409,
            detail="La lista ha cambiado. Actualiza la ficha y reintenta.",
        )
    for position, row_id in enumerate(ids):
        row = by_id[row_id]
        row.position = position
        session.add(row)
    session.commit()
    return Message(message="Order saved successfully")


@router.put("/{feature_id}/notes/order", response_model=Message)
def reorder_feature_notes(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    body: FeatureNoteOrder,
) -> Message:
    get_feature_or_404(session, feature_id)
    notes = session.exec(
        select(FeatureNote)
        .where(FeatureNote.feature_id == feature_id, FeatureNote.kind == body.kind)
        .order_by(col(FeatureNote.id))
        .with_for_update()
    ).all()
    return save_positions(session, notes, body.note_ids)


@router.put("/{feature_id}/assets/order", response_model=Message)
def reorder_feature_assets(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    body: FeatureAssetOrder,
) -> Message:
    get_feature_or_404(session, feature_id)
    assets = session.exec(
        select(FeatureAsset)
        .where(
            FeatureAsset.feature_id == feature_id,
            FeatureAsset.part_id == body.part_id,
        )
        .order_by(col(FeatureAsset.id))
        .with_for_update()
    ).all()
    return save_positions(session, assets, body.asset_ids)


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


def ordered_part_ids(feature: Feature) -> list[str]:
    parts = {part.id: part for part in feature.parts}
    for asset in feature.assets:
        if asset.part:
            parts[asset.part.id] = asset.part
    existing = {str(part_id) for part_id in parts}
    order = [part_id for part_id in feature.part_order if part_id in existing]
    order.extend(
        str(part.id)
        for part in sorted(parts.values(), key=lambda part: part.code)
        if str(part.id) not in order
    )
    return order


@router.put("/{feature_id}/parts/order", response_model=FeatureDetail)
def reorder_feature_parts(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    body: FeaturePartOrder,
) -> Any:
    feature = session.exec(
        select(Feature).where(Feature.id == feature_id).with_for_update()
    ).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    order = [str(part_id) for part_id in body.part_ids]
    if len(set(order)) != len(order) or set(order) != set(ordered_part_ids(feature)):
        raise HTTPException(
            status_code=409,
            detail="Las piezas han cambiado. Actualiza la ficha y reintenta.",
        )
    feature.part_order = order
    session.add(feature)
    session.commit()
    session.refresh(feature)
    return FeatureDetail.model_validate(feature)


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
        from app.part_setup import references

        order = ordered_part_ids(feature)
        feature.parts.append(part)
        existing_kinds = {
            asset.kind for asset in feature.assets if asset.part_id == part_id
        }
        for kind, document in references(session, part_id).items():
            if kind not in existing_kinds:
                session.add(
                    FeatureAsset(
                        feature_id=feature_id,
                        part_id=part_id,
                        file_id=document.id,
                        kind=kind,
                        name=document.filename,
                    )
                )
        if str(part_id) not in order:
            order.append(str(part_id))
        feature.part_order = order
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
    Quitar la tarjeta y sus adjuntos de este feature. La pieza compartida y
    los documentos originales se conservan.
    """
    session.exec(
        select(Feature).where(Feature.id == feature_id).with_for_update()
    ).first()
    feature = get_feature_or_404(session, feature_id)
    part = session.get(Part, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic

    for link in session.exec(
        select(FeatureCharacteristicLink)
        .join(PartCharacteristic)
        .where(
            FeatureCharacteristicLink.feature_id == feature_id,
            PartCharacteristic.part_id == part_id,
        )
    ):
        session.delete(link)
    if part in feature.parts:
        feature.parts.remove(part)
    removed = [asset for asset in feature.assets if asset.part_id == part_id]
    if feature.cover_3d and any(
        str(asset.id) == feature.cover_3d.get("asset_id") for asset in removed
    ):
        feature.cover_3d = None
    for asset in removed:
        session.delete(asset)
    feature.part_order = [item for item in feature.part_order if item != str(part_id)]
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
    if asset_in.file_id:
        document = session.get(StoredFile, asset_in.file_id)
        if not document:
            raise HTTPException(status_code=404, detail="File not found")
        asset_in.name = document.filename
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
    changes = asset_in.model_dump(exclude_unset=True)
    file_id = changes.get("file_id", asset.file_id)
    if file_id:
        document = session.get(StoredFile, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="File not found")
        changes["name"] = document.filename
    asset.sqlmodel_update(changes)
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
