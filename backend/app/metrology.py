"""Piece-scoped navigation; feature membership never implies cota membership."""

import uuid

from sqlalchemy import func, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from app.feature_links import feature_membership
from app.knowledge_models import (
    CharacteristicPublic,
    FeatureCharacteristicLink,
    MetrologyCatalog,
    MetrologyFeature,
    MetrologyFeatureChoice,
    MetrologyFilters,
    MetrologyPart,
    PartCharacteristic,
)
from app.models import Feature, Part, PartPublic


def part_features(
    session: Session, part_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[MetrologyFeature]]:
    result: dict[uuid.UUID, list[MetrologyFeature]] = {id: [] for id in part_ids}
    if not part_ids:
        return result
    links = feature_membership()
    by_pair: dict[tuple[uuid.UUID, uuid.UUID], MetrologyFeature] = {}
    for part_id, feature in session.exec(
        select(links.c.part_id, Feature)
        .join(Feature, col(Feature.id) == links.c.feature_id)
        .where(links.c.part_id.in_(part_ids))
        .order_by(col(Feature.name), col(Feature.id))
    ).all():
        item = MetrologyFeature.model_validate(feature, from_attributes=True)
        result[part_id].append(item)
        by_pair[part_id, feature.id] = item
    for cota, feature_id, role in session.exec(
        select(
            PartCharacteristic,
            FeatureCharacteristicLink.feature_id,
            FeatureCharacteristicLink.role,
        )
        .join(FeatureCharacteristicLink)
        .where(col(PartCharacteristic.part_id).in_(part_ids))
        .order_by(PartCharacteristic.code, PartCharacteristic.revision)
    ).all():
        by_pair[cota.part_id, feature_id].characteristics.append(
            CharacteristicPublic.model_validate(cota, from_attributes=True).model_copy(
                update={"role": role}
            )
        )
    return result


def filters(session: Session) -> MetrologyFilters:
    """Lightweight selector data; no studies or inferred cota assignments."""
    links = feature_membership()
    by_feature: dict[uuid.UUID, list[uuid.UUID]] = {}
    for part_id, feature_id in session.exec(
        select(links.c.part_id, links.c.feature_id).order_by(links.c.part_id)
    ).all():
        by_feature.setdefault(feature_id, []).append(part_id)
    return MetrologyFilters(
        parts=[
            PartPublic.model_validate(part)
            for part in session.exec(
                select(Part)
                .where(col(Part.id).in_(select(links.c.part_id)))
                .order_by(Part.code)
            ).all()
        ],
        features=[
            MetrologyFeatureChoice.model_validate(
                feature, from_attributes=True
            ).model_copy(update={"part_ids": by_feature.get(feature.id, [])})
            for feature in session.exec(select(Feature).order_by(Feature.name)).all()
        ],
    )


def catalog(
    session: Session,
    q: str,
    feature_id: uuid.UUID | None,
    skip: int,
    limit: int,
) -> MetrologyCatalog:
    links = feature_membership()
    needle = q.strip()
    # Search names/codes only. An N-number never becomes a global result.
    escaped = needle.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    like = f"%{escaped}%"
    feature_filter = (
        col(Feature.id) == feature_id
        if feature_id
        else col(Feature.name).ilike(like, escape="\\")
    )
    matches = (
        session.exec(select(Feature).where(feature_filter).order_by(Feature.name)).all()
        if needle or feature_id
        else []
    )
    matched_ids = {feature.id for feature in matches}
    conditions: list[ColumnElement[bool]] = []
    if feature_id:
        conditions.append(
            col(Part.id).in_(
                select(links.c.part_id).where(links.c.feature_id == feature_id)
            )
        )
    elif needle:
        conditions.append(
            or_(
                col(Part.code).ilike(like, escape="\\"),
                col(Part.name).ilike(like, escape="\\"),
                col(Part.id).in_(
                    select(links.c.part_id).where(links.c.feature_id.in_(matched_ids))
                ),
            )
        )
    count = session.exec(
        select(func.count()).select_from(Part).where(*conditions)
    ).one()
    parts = session.exec(
        select(Part).where(*conditions).order_by(Part.code).offset(skip).limit(limit)
    ).all()
    features = part_features(session, [part.id for part in parts])
    return MetrologyCatalog(
        count=count,
        features=[MetrologyFeature(id=f.id, name=f.name) for f in matches],
        data=[
            MetrologyPart(
                part=PartPublic.model_validate(part),
                features=[
                    feature
                    for feature in features[part.id]
                    if not feature_id or feature.id == feature_id
                ],
                matched_feature_ids=[
                    feature.id
                    for feature in features[part.id]
                    if feature.id in matched_ids
                    and (
                        feature_id
                        or needle.casefold()
                        not in f"{part.code} {part.name or ''}".casefold()
                    )
                ],
            )
            for part in parts
        ],
    )
