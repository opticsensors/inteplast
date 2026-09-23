"""Shared catalogue and piece details; reuse feature membership and CAD sources."""

import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, or_
from sqlmodel import col, func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import get_part_or_404
from app.cad_covers import validate_document
from app.evidence import job_id
from app.feature_links import feature_membership
from app.file_sources import SourceError
from app.knowledge_models import (
    EvidenceJob,
    FeatureCharacteristicLink,
    PartCharacteristic,
    PartDocument,
)
from app.models import (
    AssetKind,
    Feature,
    FeatureCategory,
    FeaturePublic,
    FilePublic,
    Part,
    PartPublic,
    StoredFile,
)
from app.part_files import PartFilePublic, primary_files, read_files

router = APIRouter(tags=["catalog"])


class PartCardPublic(PartPublic):
    feature_count: int = 0
    characteristic_count: int = 0
    cad: FilePublic | None = None
    image: FilePublic | None = None


class PartReferencePublic(BaseModel):
    kind: AssetKind
    file: FilePublic


class PartDetailPublic(BaseModel):
    part: PartCardPublic
    features: list[FeaturePublic]
    references: list[PartReferencePublic]
    files: list[PartFilePublic] = []


class CotaSearchResult(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    revision: str
    part: PartPublic


class CatalogPublic(BaseModel):
    features: list[FeaturePublic]
    parts: list[PartCardPublic]
    cotas: list[CotaSearchResult]
    feature_count: int
    part_count: int
    cota_count: int


class PartCoverRequest(BaseModel):
    file_id: uuid.UUID
    file_version: uuid.UUID | None = None
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_id: uuid.UUID


def part_references(session: SessionDep, part_id: uuid.UUID) -> dict[str, StoredFile]:
    return primary_files(session, part_id)


def part_card(session: SessionDep, part: Part, count: int) -> PartCardPublic:
    cad = part_references(session, part.id).get("part")
    cover = session.get(EvidenceJob, job_id("part-cover", part.id))
    image = None
    if (
        cad
        and cover
        and cover.cache_key == str(cad.version)
        and cover.file_id == cad.id
    ):
        image = session.get(StoredFile, uuid.UUID(cover.payload["image_id"]))
    characteristic_count = session.exec(
        select(func.count())
        .select_from(PartCharacteristic)
        .where(PartCharacteristic.part_id == part.id)
    ).one()
    return PartCardPublic.model_validate(
        part,
        update={
            "feature_count": count,
            "characteristic_count": characteristic_count,
            "cad": FilePublic.model_validate(cad) if cad else None,
            "image": FilePublic.model_validate(image) if image else None,
        },
    )


@router.get("/catalog", response_model=CatalogPublic)
def search_catalog(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str = "",
    kind: Literal["all", "part", "feature"] = "all",
    part_id: uuid.UUID | None = None,
    feature_id: uuid.UUID | None = None,
    category: FeatureCategory | None = None,
    tag: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=40, ge=1, le=100),
) -> CatalogPublic:
    needle = q.strip()
    features, feature_count = (
        crud.search_features(
            session=session,
            q=needle or None,
            category=category,
            tag=tag,
            part_id=part_id,
            feature_id=feature_id,
            skip=skip,
            limit=limit,
        )
        if kind != "part"
        else ([], 0)
    )
    links = feature_membership()
    scoped_features = select(Feature.id)
    if feature_id:
        scoped_features = scoped_features.where(Feature.id == feature_id)
    if category:
        scoped_features = scoped_features.where(Feature.category == category)
    if tag:
        scoped_features = scoped_features.where(col(Feature.tags).any(tag))  # type: ignore[arg-type]
    scoped = bool(feature_id or category or tag)
    part_filters: list[Any] = []
    if part_id:
        part_filters.append(Part.id == part_id)
    if scoped:
        part_filters.append(
            col(Part.id).in_(
                select(links.c.part_id).where(links.c.feature_id.in_(scoped_features))
            )
        )
    escaped = needle.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    like = f"%{escaped}%"
    code_query = re.sub(r"\s+", "", needle.upper())
    code_like = (
        f"%{code_query}%" if re.fullmatch(r"N?\d+(?:\.\d+)?", code_query) else like
    )
    if needle:
        matching_features = scoped_features.where(
            or_(
                col(Feature.name).ilike(like, escape="\\"),
                col(Feature.description).ilike(like, escape="\\"),
            )
        )
        matching_cotas = select(PartCharacteristic.part_id).where(
            or_(
                col(PartCharacteristic.code).ilike(code_like, escape="\\"),
                col(PartCharacteristic.title).ilike(like, escape="\\"),
            )
        )
        if scoped:
            matching_cotas = matching_cotas.join(FeatureCharacteristicLink).where(
                col(FeatureCharacteristicLink.feature_id).in_(scoped_features)
            )
        part_filters.append(
            or_(
                col(Part.name).ilike(like, escape="\\"),
                col(Part.code).ilike(like, escape="\\"),
                col(Part.id).in_(matching_cotas),
                col(Part.id).in_(
                    select(links.c.part_id).where(
                        links.c.feature_id.in_(matching_features)
                    )
                ),
            )
        )
    parts = (
        session.exec(
            select(Part)
            .where(*part_filters)
            .order_by(Part.code, col(Part.id))
            .offset(skip)
            .limit(limit)
        ).all()
        if kind != "feature"
        else []
    )
    part_count = (
        session.exec(select(func.count()).select_from(Part).where(*part_filters)).one()
        if kind != "feature"
        else 0
    )
    counts = (
        dict(
            session.exec(
                select(links.c.part_id, func.count())
                .where(links.c.part_id.in_([p.id for p in parts]))
                .group_by(links.c.part_id)
            ).all()
        )
        if parts
        else {}
    )
    cotas, cota_count = [], 0
    if needle and kind != "feature":
        cota_filters: list[Any] = [
            or_(
                col(PartCharacteristic.code).ilike(code_like, escape="\\"),
                col(PartCharacteristic.title).ilike(like, escape="\\"),
            )
        ]
        if part_id:
            cota_filters.append(PartCharacteristic.part_id == part_id)
        if scoped:
            cota_filters.append(
                col(PartCharacteristic.id).in_(
                    select(FeatureCharacteristicLink.characteristic_id).where(
                        col(FeatureCharacteristicLink.feature_id).in_(scoped_features)
                    )
                )
            )
        cota_count = session.exec(
            select(func.count()).select_from(PartCharacteristic).where(*cota_filters)
        ).one()
        exact = code_query if code_query.startswith("N") else "N" + code_query
        cotas = [
            CotaSearchResult(
                id=c.id,
                code=c.code,
                title=c.title,
                revision=c.revision,
                part=PartPublic.model_validate(p),
            )
            for c, p in session.exec(
                select(PartCharacteristic, Part)
                .join(Part, col(PartCharacteristic.part_id) == Part.id)
                .where(*cota_filters)
                .order_by(
                    case((col(PartCharacteristic.code) == exact, 0), else_=1),
                    Part.code,
                    PartCharacteristic.code,
                    PartCharacteristic.revision,
                    col(PartCharacteristic.id),
                )
                .offset(skip)
                .limit(limit)
            ).all()
        ]
    return CatalogPublic(
        features=[FeaturePublic.model_validate(f) for f in features],
        parts=[part_card(session, p, counts.get(p.id, 0)) for p in parts],
        cotas=cotas,
        feature_count=feature_count,
        part_count=part_count,
        cota_count=cota_count,
    )


@router.get("/parts/{part_id}/detail", response_model=PartDetailPublic)
def read_part_detail(
    session: SessionDep, _current_user: CurrentUser, part_id: uuid.UUID
) -> PartDetailPublic:
    part = get_part_or_404(session, part_id)
    features, count = crud.search_features(
        session=session, part_id=part_id, limit=10000
    )
    return PartDetailPublic(
        part=part_card(session, part, count),
        files=read_files(session, part),
        features=[FeaturePublic.model_validate(f) for f in features],
        references=[
            PartReferencePublic(
                kind=AssetKind(kind), file=FilePublic.model_validate(file)
            )
            for kind, file in part_references(session, part.id).items()
        ],
    )


@router.put("/parts/{part_id}/cover", response_model=FilePublic)
def save_part_cover(
    session: SessionDep,
    _current_user: CurrentUser,
    part_id: uuid.UUID,
    body: PartCoverRequest,
) -> FilePublic:
    part = session.exec(
        select(Part).where(Part.id == part_id).with_for_update()
    ).first()
    if part is None:
        raise HTTPException(404, "Part not found")
    cad = part_references(session, part_id).get("part")
    if cad is None or cad.id != body.file_id:
        raise HTTPException(409, "El CAD de la pieza ha cambiado.")
    try:
        validate_document(cad, body.file_version, body.source_sha256)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)
    image = session.get(StoredFile, body.image_id)
    if not image or image.content_type != "image/png" or image.source != "upload":
        raise HTTPException(422, "La portada debe ser una imagen PNG.")
    cover = session.get(EvidenceJob, job_id("part-cover", part_id))
    if not cover:
        cover = EvidenceJob(
            id=job_id("part-cover", part_id),
            kind="part-cover",
            part_id=part_id,
            cache_key=str(cad.version),
        )
    cover.file_id = cad.id
    cover.cache_key = str(cad.version)
    cover.state = "ready"
    cover.payload = {"image_id": str(image.id), "source_sha256": body.source_sha256}
    session.add(cover)
    if not session.get(PartDocument, (part_id, image.id)):
        session.add(PartDocument(part_id=part_id, file_id=image.id, kind="derived"))
    session.commit()
    return FilePublic.model_validate(image)
