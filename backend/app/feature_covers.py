"""Covers of a feature, one per piece (docs/plan-portadas-por-pieza-2026-11-18.md).

Each piece of a feature shows its own capture, saved on its `FeaturePartLink`. Without
one it shows the saved catalogue capture of the piece's CAD (`part-cover`), never a new
one. The server decides the order of the pieces (`ordered_part_ids`): the card uses the
first one and the carousel follows `FeatureDetail.part_covers`. A feature without pieces
keeps its own image.
"""

import re
import uuid
from collections.abc import Iterable

from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session, select

from app.cad_covers import validate_cover
from app.evidence import job_id
from app.file_sources import document_cache_key
from app.knowledge_models import EvidenceJob
from app.models import (
    Feature,
    FeatureAsset,
    FeatureCover3D,
    FeatureDetail,
    FeaturePartCoverChange,
    FeaturePartCoverPublic,
    FeaturePartLink,
    FeaturePublic,
    FilePublic,
    Part,
    StoredFile,
)
from app.part_files import primary_files

# Saved CAD capture of each piece, shared by every feature built in one request.
AutoCovers = dict[uuid.UUID, StoredFile | None]

# Formats the cover shows as an image (frontend `RASTER_IMAGE_TYPES`).
COVER_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
    "image/bmp",
}


def part_cad_cover(
    session: Session, part_id: uuid.UUID
) -> tuple[StoredFile | None, str | None, StoredFile | None]:
    """The piece's CAD, the key of its current bytes and its saved capture, if current."""
    cad = primary_files(session, part_id).get("part")
    cover = session.get(EvidenceJob, job_id("part-cover", part_id))
    cad_key = None
    if cad:
        try:
            cad_key = document_cache_key(cad)
        except HTTPException as error:
            # Keep the catalogue usable when a CAD is missing/changed/inaccessible, but do not
            # present an old thumbnail as current. An expired login must still reach the browser.
            if error.status_code not in {404, 409, 503}:
                raise
    image = None
    if (
        cad
        and cover
        and cad_key is not None
        and cover.cache_key == cad_key
        and cover.file_id == cad.id
    ):
        image = session.get(StoredFile, uuid.UUID(cover.payload["image_id"]))
    return cad, cad_key, image


def _auto_cover(
    session: Session, part_id: uuid.UUID, cache: AutoCovers
) -> StoredFile | None:
    if part_id not in cache:
        cache[part_id] = part_cad_cover(session, part_id)[2]
    return cache[part_id]


def code_order(part: Part) -> tuple[tuple[int, int | str], ...]:
    """Natural order of codes: P2 before P10, 3051 before 3212."""
    return tuple(
        (0, int(chunk)) if chunk.isdigit() else (1, chunk.casefold())
        for chunk in re.split(r"(\d+)", part.code)
        if chunk
    )


def ordered_part_ids(feature: Feature) -> list[str]:
    """The definitive order of the pieces: `part_order`, then by code (natural)."""
    parts = {part.id: part for part in feature.parts}
    for asset in feature.assets:
        if asset.part:
            parts[asset.part.id] = asset.part
    existing = {str(part_id) for part_id in parts}
    order = [part_id for part_id in feature.part_order if part_id in existing]
    order.extend(
        str(part.id)
        for part in sorted(parts.values(), key=lambda part: (code_order(part), part.id))
        if str(part.id) not in order
    )
    return order


def _links(session: Session, feature_id: uuid.UUID) -> dict[uuid.UUID, FeaturePartLink]:
    return {
        link.part_id: link
        for link in session.exec(
            select(FeaturePartLink).where(FeaturePartLink.feature_id == feature_id)
        ).all()
    }


def _cover_3d(link: FeaturePartLink | None) -> FeatureCover3D | None:
    if not link or not link.cover_3d:
        return None
    try:
        return FeatureCover3D.model_validate(link.cover_3d)
    except ValidationError:
        return None


def _file(session: Session, file_id: uuid.UUID | None) -> FilePublic | None:
    document = session.get(StoredFile, file_id) if file_id else None
    return FilePublic.model_validate(document) if document else None


def _part_cover(
    session: Session,
    part_id: uuid.UUID,
    link: FeaturePartLink | None,
    cache: AutoCovers,
) -> FeaturePartCoverPublic:
    own = _file(session, link.image_id) if link else None
    # Always sent: the editor shows it again when the own cover is removed.
    auto = _auto_cover(session, part_id, cache)
    return FeaturePartCoverPublic(
        part_id=part_id,
        image=own,
        cover_3d=_cover_3d(link) if own else None,
        auto_image=FilePublic.model_validate(auto) if auto else None,
    )


def _card(
    session: Session,
    feature: Feature,
    order: list[str],
    links: dict[uuid.UUID, FeaturePartLink],
    cache: AutoCovers,
) -> dict[str, object]:
    if not order:
        image = FilePublic.model_validate(feature.image) if feature.image else None
        return {"cover_image": image, "part_count": 0}
    first = uuid.UUID(order[0])
    link = links.get(first)
    own = _file(session, link.image_id) if link else None
    if own is None:
        auto = _auto_cover(session, first, cache)
        own = FilePublic.model_validate(auto) if auto else None
    return {"cover_image": own, "part_count": len(order)}


def feature_public(
    session: Session, feature: Feature, cache: AutoCovers | None = None
) -> FeaturePublic:
    cache = {} if cache is None else cache
    order = ordered_part_ids(feature)
    links = _links(session, feature.id)
    return FeaturePublic.model_validate(
        feature, update=_card(session, feature, order, links, cache)
    )


def features_public(
    session: Session, features: Iterable[Feature]
) -> list[FeaturePublic]:
    cache: AutoCovers = {}
    return [feature_public(session, feature, cache) for feature in features]


def feature_detail(session: Session, feature: Feature) -> FeatureDetail:
    cache: AutoCovers = {}
    order = ordered_part_ids(feature)
    links = _links(session, feature.id)
    covers = [
        _part_cover(session, uuid.UUID(part_id), links.get(uuid.UUID(part_id)), cache)
        for part_id in order
    ]
    return FeatureDetail.model_validate(
        feature,
        update={
            **_card(session, feature, order, links, cache),
            "part_covers": covers,
        },
    )


def apply_cover_changes(
    session: Session, feature: Feature, changes: list[FeaturePartCoverChange]
) -> None:
    """Check every change first and only then write them: all or nothing.

    A piece that is no longer in the feature (removed meanwhile by someone else) is a
    conflict: nothing is saved and the page keeps its drafts to retry.
    """
    if len({change.part_id for change in changes}) != len(changes):
        raise HTTPException(422, "Hay dos portadas para la misma pieza.")
    links = _links(session, feature.id)
    checked: list[tuple[FeaturePartLink, FeaturePartCoverChange]] = []
    for change in changes:
        link = links.get(change.part_id)
        if link is None:
            part = session.get(Part, change.part_id)
            name = f"La pieza {part.code}" if part else "Una de las piezas"
            raise HTTPException(
                409,
                f"{name} ya no está en este feature. "
                "Actualiza la ficha y vuelve a guardar.",
            )
        if change.image_id is None:
            if change.cover_3d is not None:
                raise HTTPException(
                    422, "Guarda la imagen de portada junto con la selección 3D."
                )
        else:
            image = session.get(StoredFile, change.image_id)
            if not image:
                raise HTTPException(status_code=404, detail="File not found")
            media = (image.content_type or "").split(";", 1)[0].strip().lower()
            if media not in COVER_IMAGE_TYPES:
                raise HTTPException(422, "La portada debe ser una imagen.")
        if change.cover_3d is not None:
            if change.cover_3d.part_id != change.part_id:
                raise HTTPException(409, "La selección 3D es de otra pieza.")
            validate_cover(session, feature, change.cover_3d)
        checked.append((link, change))
    for link, change in checked:
        link.image_id = change.image_id
        link.cover_3d = (
            change.cover_3d.model_dump(mode="json") if change.cover_3d else None
        )
        session.add(link)


def ensure_link(session: Session, feature_id: uuid.UUID, part_id: uuid.UUID) -> None:
    """A piece that gets an attachment of the feature is also a piece of the feature."""
    if session.get(FeaturePartLink, (feature_id, part_id)) is None:
        session.add(FeaturePartLink(feature_id=feature_id, part_id=part_id))


def drop_cad_covers(session: Session, assets: Iterable[FeatureAsset]) -> int:
    """Forget the CAD selection of covers made on these attachments; keep the image.

    The capture stays as a plain image: it still shows the piece, but its faces can no
    longer be checked against a linked STEP.
    """
    by_feature: dict[uuid.UUID, set[str]] = {}
    for asset in assets:
        by_feature.setdefault(asset.feature_id, set()).add(str(asset.id))
    dropped = 0
    for feature_id, asset_ids in by_feature.items():
        # Filtered here, not in SQL: an emptied JSON column may hold JSON null.
        for link in session.exec(
            select(FeaturePartLink).where(FeaturePartLink.feature_id == feature_id)
        ).all():
            if (link.cover_3d or {}).get("asset_id") in asset_ids:
                link.cover_3d = None
                session.add(link)
                dropped += 1
    return dropped
