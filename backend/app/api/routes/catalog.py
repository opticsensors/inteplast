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
from app.component_models import identity_expression, qualified
from app.evidence import job_id
from app.feature_links import feature_membership
from app.file_sources import SourceError, document_cache_key
from app.knowledge_models import (
    EvidenceJob,
    FeatureCharacteristicLink,
    PartCharacteristic,
    PartDocument,
)
from app.measurement_status import MeasurementStatus, measurement_status
from app.models import (
    AssetKind,
    Feature,
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
    cad_cache_key: str | None = None
    image: FilePublic | None = None
    # Catalogue label: detected / pending / none; no label until the piece is read.
    measurement_status: MeasurementStatus | None = None


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
    cad_cache_key: str | None = None
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_id: uuid.UUID


def part_references(session: SessionDep, part_id: uuid.UUID) -> dict[str, StoredFile]:
    return primary_files(session, part_id)


def part_card(session: SessionDep, part: Part, count: int) -> PartCardPublic:
    cad = part_references(session, part.id).get("part")
    cover = session.get(EvidenceJob, job_id("part-cover", part.id))
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
            "cad_cache_key": cad_key,
            "image": FilePublic.model_validate(image) if image else None,
            "measurement_status": measurement_status(session, part),
        },
    )


def _text_patterns(needle: str) -> tuple[str, str, str]:
    """LIKE pattern for text, LIKE pattern for cota numbers and the compact number."""
    escaped = needle.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    like = f"%{escaped}%"
    code_query = re.sub(r"\s+", "", needle.upper())
    code_like = (
        f"%{code_query}%" if re.fullmatch(r"N?\d+(?:\.\d+)?", code_query) else like
    )
    return like, code_like, code_query


def _scoped_features(feature_id: uuid.UUID | None) -> Any:
    scoped = select(Feature.id)
    return scoped.where(Feature.id == feature_id) if feature_id else scoped


def catalog_part_filters(
    needle: str, piece: list[Any], feature_id: uuid.UUID | None
) -> list[Any]:
    """Pieces shown by the catalogue: the list, the grid and the graph use this.

    Every piece filter at once; with a feature, only its pieces; with text, pieces whose
    code, name, cotas or linked features match it.
    """
    links = feature_membership()
    scoped_features = _scoped_features(feature_id)
    part_filters: list[Any] = list(piece)
    if feature_id:
        part_filters.append(
            col(Part.id).in_(
                select(links.c.part_id).where(links.c.feature_id.in_(scoped_features))
            )
        )
    if needle:
        like, code_like, _ = _text_patterns(needle)
        matching_features = scoped_features.where(
            or_(
                col(Feature.name).ilike(like, escape="\\"),
                col(Feature.description).ilike(like, escape="\\"),
            )
        )
        matching_cotas = select(PartCharacteristic.part_id).where(
            or_(
                identity_expression().ilike(code_like, escape="\\"),
                col(PartCharacteristic.title).ilike(like, escape="\\"),
            )
        )
        if feature_id:
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
    return part_filters


@router.get("/catalog", response_model=CatalogPublic)
def search_catalog(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str = "",
    kind: Literal["all", "part", "feature"] = "all",
    part_id: uuid.UUID | None = None,
    feature_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=40, ge=1, le=100),
) -> CatalogPublic:
    """Pieces, features and cotas that match the search and the filters.

    A piece matches when it meets every piece filter (piece, family, customer). A feature
    matches when it is linked to at least one piece that meets all of them at once.
    Old links with `category` or `tag` are accepted and ignored.
    """
    needle = q.strip()
    piece = crud.part_conditions(
        part_id=part_id, family_id=family_id, customer_id=customer_id
    )
    features, feature_count = (
        crud.search_features(
            session=session,
            q=needle or None,
            part_id=part_id,
            family_id=family_id,
            customer_id=customer_id,
            feature_id=feature_id,
            skip=skip,
            limit=limit,
        )
        if kind != "part"
        else ([], 0)
    )
    links = feature_membership()
    scoped_features = _scoped_features(feature_id)
    scoped = bool(feature_id)
    part_filters = catalog_part_filters(needle, piece, feature_id)
    like, code_like, code_query = _text_patterns(needle)
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
                identity_expression().ilike(code_like, escape="\\"),
                col(PartCharacteristic.title).ilike(like, escape="\\"),
            )
        ]
        if piece:
            cota_filters.append(
                col(PartCharacteristic.part_id).in_(select(Part.id).where(*piece))
            )
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
                code=qualified(c.code, c.component),
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
    cad_key = document_cache_key(cad)
    if body.cad_cache_key is not None and body.cad_cache_key != cad_key:
        raise HTTPException(409, "El CAD ha cambiado. Vuelve a preparar su portada.")
    try:
        validate_document(cad, body.file_version, body.source_sha256)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)
    if document_cache_key(cad) != cad_key:
        raise HTTPException(409, "El CAD ha cambiado mientras se preparaba su portada.")
    image = session.get(StoredFile, body.image_id)
    if not image or image.content_type != "image/png" or image.source != "upload":
        raise HTTPException(422, "La portada debe ser una imagen PNG.")
    cover = session.get(EvidenceJob, job_id("part-cover", part_id))
    if not cover:
        cover = EvidenceJob(
            id=job_id("part-cover", part_id),
            kind="part-cover",
            part_id=part_id,
            cache_key=cad_key,
        )
    cover.file_id = cad.id
    cover.cache_key = cad_key
    cover.state = "ready"
    cover.payload = {"image_id": str(image.id), "source_sha256": body.source_sha256}
    session.add(cover)
    if not session.get(PartDocument, (part_id, image.id)):
        session.add(PartDocument(part_id=part_id, file_id=image.id, kind="derived"))
    session.commit()
    return FilePublic.model_validate(image)


# The graph loads every result at once; past this many nodes it says so and stops.
GRAPH_LIMIT = 500
NodeKind = Literal["part", "feature", "family", "customer"]
GroupKind = Literal["family", "customer"]


class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    ref_id: uuid.UUID
    label: str
    # Pieces only: their optional name and the saved CAD capture, never a new capture.
    name: str | None = None
    image: FilePublic | None = None


class GraphLink(BaseModel):
    source: str
    target: str
    kind: Literal["feature", "family", "customer"]


class CatalogGraph(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
    total: int
    truncated: bool


@router.get("/catalog/graph", response_model=CatalogGraph)
def read_catalog_graph(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str = "",
    kind: Literal["all", "part", "feature"] = "all",
    part_id: uuid.UUID | None = None,
    feature_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    limit: int = Query(default=GRAPH_LIMIT, ge=1, le=GRAPH_LIMIT),
) -> CatalogGraph:
    """What the list shows with the same search and filters, as nodes and links.

    Every result at once, without pages. Families and customers of the shown pieces come
    as nodes too. Past `limit` nodes the answer is cut and says so with the real total,
    so that a part is never presented as the whole.
    """
    needle = q.strip()
    piece = crud.part_conditions(
        part_id=part_id, family_id=family_id, customer_id=customer_id
    )
    parts = (
        list(
            session.exec(
                select(Part)
                .where(*catalog_part_filters(needle, piece, feature_id))
                .order_by(Part.code, col(Part.id))
            ).all()
        )
        if kind != "feature"
        else []
    )
    features = (
        list(
            session.exec(
                select(Feature)
                .where(
                    *crud.feature_conditions(
                        q=needle or None,
                        part_id=part_id,
                        family_id=family_id,
                        customer_id=customer_id,
                        feature_id=feature_id,
                    )
                )
                .order_by(Feature.name, col(Feature.id))
            ).all()
        )
        if kind != "part"
        else []
    )
    candidates: list[tuple[NodeKind, Any]] = [
        *(("part", part) for part in parts),
        *(("feature", feature) for feature in features),
    ]
    seen: set[str] = set()
    groups: tuple[GroupKind, ...] = ("family", "customer")
    for relation in groups:
        for part in parts:
            value = getattr(part, relation)
            if value is not None and f"{relation}:{value.id}" not in seen:
                seen.add(f"{relation}:{value.id}")
                candidates.append((relation, value))
    shown = candidates[:limit]
    nodes: list[GraphNode] = []
    for group, item in shown:
        if group == "part":
            card = part_card(session, item, 0)
            nodes.append(
                GraphNode(
                    id=f"part:{item.id}",
                    kind="part",
                    ref_id=item.id,
                    label=item.code,
                    name=item.name,
                    image=card.image,
                )
            )
        else:
            nodes.append(
                GraphNode(
                    id=f"{group}:{item.id}",
                    kind=group,
                    ref_id=item.id,
                    label=item.name,
                )
            )
    present = {node.id for node in nodes}
    links: list[GraphLink] = []
    shown_parts = [item.id for group, item in shown if group == "part"]
    shown_features = [item.id for group, item in shown if group == "feature"]
    if shown_parts and shown_features:
        membership = feature_membership()
        for linked_part, linked_feature in session.exec(
            select(membership.c.part_id, membership.c.feature_id)
            .where(
                membership.c.part_id.in_(shown_parts),
                membership.c.feature_id.in_(shown_features),
            )
            .distinct()
        ).all():
            links.append(
                GraphLink(
                    source=f"part:{linked_part}",
                    target=f"feature:{linked_feature}",
                    kind="feature",
                )
            )
    for group, item in shown:
        if group != "part":
            continue
        for relation in groups:
            target = getattr(item, f"{relation}_id")
            if target and f"{relation}:{target}" in present:
                links.append(
                    GraphLink(
                        source=f"part:{item.id}",
                        target=f"{relation}:{target}",
                        kind=relation,
                    )
                )
    links.sort(key=lambda link: (link.source, link.target))
    return CatalogGraph(
        nodes=nodes,
        links=links,
        total=len(candidates),
        truncated=len(candidates) > len(shown),
    )


class DrawingCard(BaseModel):
    file: FilePublic
    name: str
    primary: bool
    part: PartPublic
    # From «Organizar por componentes», when the drawing is assigned there.
    component: str | None = None
    revision: str | None = None


class DrawingsPublic(BaseModel):
    data: list[DrawingCard]
    count: int


def component_of(part: Part, path: str | None) -> tuple[str | None, str | None]:
    """Component name and revision assigned to this drawing, if any."""
    for component in part.components or []:
        for assigned in component.get("files", []):
            if path and f"{part.folder_path}/{assigned.get('path')}" == path:
                return component.get("name") or None, assigned.get("revision") or None
    return None, None


@router.get("/catalog/drawings", response_model=DrawingsPublic)
def read_catalog_drawings(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str = "",
    part_id: uuid.UUID | None = None,
    feature_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=40, ge=1, le=100),
) -> DrawingsPublic:
    """Every drawing of the loaded pieces, not only the principal one.

    The drawings of a piece are the ones its page shows (`read_files`): its managed file
    list or, for pieces without one, its references and the files attached to features.
    Pieces follow the catalogue's piece criterion (piece, family, customer and feature);
    the text matches the file name or the piece's code or name.
    """
    piece = crud.part_conditions(
        part_id=part_id, family_id=family_id, customer_id=customer_id
    )
    parts = session.exec(
        select(Part)
        .where(*catalog_part_filters("", piece, feature_id))
        .order_by(col(Part.code), col(Part.id))
    ).all()
    needle = " ".join(q.split()).casefold()
    cards: list[DrawingCard] = []
    for part in parts:
        seen: set[uuid.UUID] = set()
        drawings = [
            item for item in read_files(session, part) if item.kind == "drawing"
        ]
        # The principal first, then the page's order.
        for item in sorted(drawings, key=lambda item: not item.primary):
            if item.file.id in seen:
                continue
            seen.add(item.file.id)
            texts = (item.file.filename, item.name, part.code, part.name or "")
            if needle and not any(needle in text.casefold() for text in texts):
                continue
            component, revision = component_of(part, item.path)
            cards.append(
                DrawingCard(
                    file=item.file,
                    name=item.name,
                    primary=item.primary,
                    part=PartPublic.model_validate(part),
                    component=component,
                    revision=revision,
                )
            )
    return DrawingsPublic(data=cards[skip : skip + limit], count=len(cards))
