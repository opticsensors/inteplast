import uuid
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.feature_covers import (
    apply_cover_changes,
    drop_cad_covers,
    ensure_link,
    feature_detail,
    feature_public,
    features_public,
    ordered_part_ids,
)
from app.models import (
    Feature,
    FeatureAsset,
    FeatureAssetCreate,
    FeatureAssetOrder,
    FeatureAssetPublic,
    FeatureAssetUpdate,
    FeatureCreate,
    FeatureDetail,
    FeatureFilters,
    FeatureNote,
    FeatureNoteCreate,
    FeatureNoteOrder,
    FeatureNotePublic,
    FeatureNoteUpdate,
    FeaturePartLink,
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


def lock_feature(session: SessionDep, feature_id: uuid.UUID) -> Feature:
    """Serialize every change that a cover depends on: covers, links and attachments."""
    feature = session.exec(
        select(Feature).where(Feature.id == feature_id).with_for_update()
    ).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


Response = TypeVar("Response")


def commit_with(
    session: SessionDep,
    feature: Feature,
    respond: Callable[[Session, Feature], Response],
) -> Response:
    """Build the answer before committing.

    The answer reads the saved CAD captures, which may ask SharePoint. If that fails (an
    expired Microsoft session) nothing is saved, so an error never hides a saved change.
    """
    session.flush()
    session.refresh(feature)
    answer = respond(session, feature)
    session.commit()
    return answer


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


@router.get("/", response_model=FeaturesPublic)
def read_features(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str | None = None,
    part_id: uuid.UUID | None = None,
    feature_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Buscar features.

    `q` busca a la vez en nombre, descripcion, codigo y nombre de las piezas,
    nombres de los adjuntos, y texto de warnings y lessons learned.
    `part_id` y `feature_id` se combinan con la búsqueda.
    """
    features, count = crud.search_features(
        session=session,
        q=q,
        part_id=part_id,
        feature_id=feature_id,
        skip=skip,
        limit=limit,
    )
    return FeaturesPublic(data=features_public(session, features), count=count)


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
    return feature_detail(session, feature)


@router.post("/", response_model=FeaturePublic)
def create_feature(
    *, session: SessionDep, current_user: CurrentUser, feature_in: FeatureCreate
) -> Any:
    """
    Crear un feature.
    """
    if feature_in.image_id and not session.get(StoredFile, feature_in.image_id):
        raise HTTPException(status_code=404, detail="File not found")
    feature = crud.create_feature(
        session=session, feature_in=feature_in, owner_id=current_user.id
    )
    return feature_public(session, feature)


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

    `part_covers` guarda las portadas cambiadas de algunas piezas junto con la
    cabecera, en una sola transaccion: si una falla, no se guarda nada.
    """
    # Locked like unlinking a piece or removing an attachment, so that a cover never
    # lands on a removed link or keeps faces of a STEP that is no longer attached.
    feature = lock_feature(session, feature_id)
    if feature_in.image_id and not session.get(StoredFile, feature_in.image_id):
        raise HTTPException(status_code=404, detail="File not found")
    if feature_in.part_covers:
        apply_cover_changes(session, feature, feature_in.part_covers)
    feature.sqlmodel_update(
        feature_in.model_dump(exclude_unset=True, exclude={"part_covers"})
    )
    session.add(feature)
    return commit_with(session, feature, feature_public)


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
    return commit_with(session, feature, feature_detail)


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
    feature = lock_feature(session, feature_id)
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
        return commit_with(session, feature, feature_detail)
    return feature_detail(session, feature)


@router.delete("/{feature_id}/parts/{part_id}")
def unlink_feature_part(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    part_id: uuid.UUID,
) -> Message:
    """
    Quitar la tarjeta, sus adjuntos y su portada de este feature. La pieza
    compartida, los documentos originales y las portadas de las demas piezas se
    conservan.
    """
    feature = lock_feature(session, feature_id)
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
    # The link holds this piece's cover: deleting it removes only that one.
    part_link = session.get(FeaturePartLink, (feature_id, part_id))
    if part_link:
        session.delete(part_link)
    for asset in [asset for asset in feature.assets if asset.part_id == part_id]:
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
    lock_feature(session, feature_id)
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


def locked_asset(session: SessionDep, asset_id: uuid.UUID) -> FeatureAsset:
    """The attachment, read again once its feature is locked.

    A cover save holds the same lock: either it sees the attachment gone and refuses
    the faces, or this change sees the saved cover and drops its faces.
    """
    asset = session.get(FeatureAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    lock_feature(session, asset.feature_id)
    asset = session.exec(
        select(FeatureAsset)
        .where(FeatureAsset.id == asset_id)
        .execution_options(populate_existing=True)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


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
    asset = locked_asset(session, asset_id)
    if asset_in.part_id and not session.get(Part, asset_in.part_id):
        raise HTTPException(status_code=404, detail="Part not found")
    changes = asset_in.model_dump(exclude_unset=True)
    file_id = changes.get("file_id", asset.file_id)
    if file_id:
        document = session.get(StoredFile, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="File not found")
        changes["name"] = document.filename
    if any(
        key in changes and changes[key] != getattr(asset, key)
        for key in ("part_id", "file_id", "kind")
    ):
        # A cover selected on this STEP no longer matches what the attachment points at.
        drop_cad_covers(session, [asset])
    asset.sqlmodel_update(changes)
    if asset.part_id:
        ensure_link(session, asset.feature_id, asset.part_id)
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
    Una portada hecha sobre ese STEP se queda como imagen, sin las caras.
    """
    asset = locked_asset(session, asset_id)
    drop_cad_covers(session, [asset])
    session.delete(asset)
    session.commit()
    return Message(message="Asset deleted successfully")
