import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app import measurement_imports
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import get_part_or_404
from app.evidence import drawing_key, job_id, queue, study_key
from app.file_sources import SourceError, document_path
from app.knowledge_models import (
    CharacteristicAssignment,
    CharacteristicPublic,
    DrawingLocation,
    DrawingPublic,
    EvidenceDocument,
    EvidenceJob,
    FeatureCharacteristicLink,
    FeatureEvidencePublic,
    JobPublic,
    LocationPublic,
    LocationReview,
    MetrologyCatalog,
    MetrologyFilters,
    PartCharacteristic,
    PartDocument,
    PartEvidencePublic,
    PendingCharacteristic,
)
from app.metrology import catalog, filters, part_features
from app.models import (
    Feature,
    FeatureAsset,
    FeaturePartLink,
    Message,
    Part,
    PartPublic,
    StoredFile,
    get_datetime_utc,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/metrology/filters", response_model=MetrologyFilters)
def read_metrology_filters(
    session: SessionDep, _current_user: CurrentUser
) -> MetrologyFilters:
    return filters(session)


@router.get("/metrology", response_model=MetrologyCatalog)
def read_metrology(
    session: SessionDep,
    _current_user: CurrentUser,
    q: str = "",
    feature_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
) -> MetrologyCatalog:
    return catalog(session, q, feature_id, skip, limit)


def public_job(job: EvidenceJob | None) -> JobPublic:
    if not job:
        return JobPublic(state="empty")
    return JobPublic(
        state=job.state,
        message=job.message,
        updated_at=job.updated_at,
        payload=job.payload if job.state == "ready" else {},
    )


def characteristic_public(
    item: PartCharacteristic, role: str | None = None
) -> CharacteristicPublic:
    return CharacteristicPublic.model_validate(item, from_attributes=True).model_copy(
        update={"role": role}
    )


@router.get("/parts/{part_id}", response_model=PartEvidencePublic)
def read_part_evidence(
    session: SessionDep,
    _current_user: CurrentUser,
    part_id: uuid.UUID,
    revision: str | None = None,
    snapshot_id: uuid.UUID | None = None,
) -> Any:
    part = get_part_or_404(session, part_id)
    from app.part_setup import references

    drawing = references(session, part_id).get("drawing")
    study, revisions = measurement_imports.study(session, part, revision, snapshot_id)
    ids = (
        select(FeatureAsset.file_id)
        .where(FeatureAsset.part_id == part_id)
        .union(
            select(PartDocument.file_id).where(
                PartDocument.part_id == part_id, PartDocument.kind != "derived"
            )
        )
    )
    documents = session.exec(
        select(StoredFile)
        .where(col(StoredFile.id).in_(ids))
        .order_by(StoredFile.filename)
    ).all()
    return PartEvidencePublic(
        part=PartPublic.model_validate(part),
        features=part_features(session, [part_id])[part_id],
        documents=[
            EvidenceDocument.model_validate(d, update={"relative_path": d.source_path})
            for d in documents
        ],
        characteristics=[
            characteristic_public(c)
            for c in session.exec(
                select(PartCharacteristic)
                .where(PartCharacteristic.part_id == part_id)
                .order_by(PartCharacteristic.code)
            ).all()
        ],
        study=study,
        measurement_revisions=revisions,
        drawing_file_id=drawing.id if drawing else None,
        refresh_job=public_job(session.get(EvidenceJob, job_id("study", part_id))),
        import_available=part.code == "3212"
        and part.folder_path == "3212 Pump Housing",
    )


@router.post("/parts/{part_id}/import", response_model=JobPublic)
def import_part_evidence(
    session: SessionDep, _current_user: CurrentUser, part_id: uuid.UUID
) -> Any:
    part = get_part_or_404(session, part_id)
    if part.code != "3212" or part.folder_path != "3212 Pump Housing":
        raise HTTPException(
            status_code=422,
            detail="Esta pieza todavía no tiene un adaptador de mediciones configurado.",
        )
    try:
        key = study_key(part)
    except SourceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    return public_job(queue(session, "study", part_id, key))


@router.get(
    "/features/{feature_id}/parts/{part_id}", response_model=FeatureEvidencePublic
)
def read_feature_evidence(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    part_id: uuid.UUID,
) -> Any:
    if session.get(Feature, feature_id) is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    get_part_or_404(session, part_id)
    rows = session.exec(
        select(PartCharacteristic, FeatureCharacteristicLink.role)
        .join(FeatureCharacteristicLink)
        .where(
            FeatureCharacteristicLink.feature_id == feature_id,
            PartCharacteristic.part_id == part_id,
        )
        .order_by(PartCharacteristic.code)
    ).all()
    job = session.get(EvidenceJob, job_id("study", part_id))
    codes = {c.code for c, _ in rows}
    return FeatureEvidencePublic(
        characteristics=[characteristic_public(c, role) for c, role in rows],
        pending=[
            p.code
            for p in session.exec(
                select(PendingCharacteristic).where(
                    PendingCharacteristic.feature_id == feature_id
                )
            )
        ],
        cases=[
            c
            for c in (
                job.payload.get("cases", {}) if job and job.state == "ready" else {}
            )
            if c in codes
        ],
    )


@router.put(
    "/features/{feature_id}/parts/{part_id}/characteristics",
    response_model=CharacteristicPublic,
)
def assign_characteristic(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    part_id: uuid.UUID,
    body: CharacteristicAssignment,
) -> Any:
    get_part_or_404(session, part_id)
    # Two features may concurrently select the same previously unseen cota.
    session.exec(select(Part).where(Part.id == part_id).with_for_update()).one()
    if session.get(Feature, feature_id) is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    # Lock the feature to serialize an assignment with unlink/edit operations.
    session.exec(
        select(Feature).where(Feature.id == feature_id).with_for_update()
    ).one()
    characteristic = session.exec(
        select(PartCharacteristic).where(
            PartCharacteristic.part_id == part_id,
            PartCharacteristic.code == body.code,
            PartCharacteristic.revision == body.revision,
        )
    ).first()
    if characteristic is None:
        characteristic = PartCharacteristic(
            part_id=part_id, code=body.code, revision=body.revision
        )
        session.add(characteristic)
        session.flush()
    link = session.get(FeatureCharacteristicLink, (feature_id, characteristic.id))
    if link is None:
        link = FeatureCharacteristicLink(
            feature_id=feature_id, characteristic_id=characteristic.id
        )
    link.role = body.role
    session.add(link)
    if session.get(FeaturePartLink, (feature_id, part_id)) is None:
        session.add(FeaturePartLink(feature_id=feature_id, part_id=part_id))
    pending = session.get(PendingCharacteristic, (feature_id, body.code))
    if pending:
        session.delete(pending)
    session.commit()
    return characteristic_public(characteristic, body.role)


@router.delete(
    "/features/{feature_id}/characteristics/{characteristic_id}", response_model=Message
)
def unassign_characteristic(
    session: SessionDep,
    _current_user: CurrentUser,
    feature_id: uuid.UUID,
    characteristic_id: uuid.UUID,
) -> Any:
    link = session.get(FeatureCharacteristicLink, (feature_id, characteristic_id))
    if not link:
        raise HTTPException(status_code=404, detail="Association not found")
    session.delete(link)
    session.commit()
    return Message(message="Cota desvinculada")


def drawing_document(session: SessionDep, file_id: uuid.UUID) -> StoredFile:
    document = session.get(StoredFile, file_id)
    if not document:
        raise HTTPException(status_code=404, detail="File not found")
    if not document.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Selecciona un plano PDF")
    document_path(document)
    return document


@router.get("/drawings/{file_id}", response_model=DrawingPublic)
def read_drawing_index(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> Any:
    document = drawing_document(session, file_id)
    job = session.get(EvidenceJob, job_id("drawing", file_id))
    if job and job.cache_key != drawing_key(document):
        return DrawingPublic(
            state="empty", message="Nueva versión: prepara la búsqueda de este plano."
        )
    public = public_job(job)
    sha = public.payload.get("signature", {}).get("sha256")
    reviews = (
        session.exec(
            select(DrawingLocation).where(
                DrawingLocation.file_id == file_id, DrawingLocation.sha256 == sha
            )
        ).all()
        if sha
        else []
    )
    return DrawingPublic(
        **public.model_dump(),
        reviews=[
            LocationPublic.model_validate(r, from_attributes=True) for r in reviews
        ],
    )


@router.post("/drawings/{file_id}/index", response_model=JobPublic)
def index_drawing(
    session: SessionDep, _current_user: CurrentUser, file_id: uuid.UUID
) -> Any:
    document = drawing_document(session, file_id)
    return public_job(queue(session, "drawing", file_id, drawing_key(document)))


@router.put("/drawings/{file_id}/review", response_model=LocationPublic)
def review_drawing_location(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    body: LocationReview,
) -> Any:
    document = drawing_document(session, file_id)
    job = session.exec(
        select(EvidenceJob)
        .where(EvidenceJob.id == job_id("drawing", file_id))
        .with_for_update()
    ).first()
    if (
        not job
        or job.state != "ready"
        or job.cache_key != drawing_key(document)
        or job.payload.get("signature", {}).get("sha256") != body.sha256
    ):
        raise HTTPException(
            status_code=409,
            detail="El plano ha cambiado. Recarga su índice antes de revisar.",
        )
    candidate = next(
        (
            c
            for c in job.payload.get("balloons", []) + job.payload.get("words", [])
            if c["id"] == body.candidate_id
        ),
        None,
    )
    if not candidate:
        raise HTTPException(
            status_code=422, detail="Ubicación no encontrada en este plano"
        )
    review = session.exec(
        select(DrawingLocation).where(
            DrawingLocation.file_id == file_id,
            DrawingLocation.sha256 == body.sha256,
            DrawingLocation.candidate_id == body.candidate_id,
        )
    ).first()
    if review is None:
        review = DrawingLocation(
            file_id=file_id,
            sha256=body.sha256,
            candidate_id=body.candidate_id,
            label=body.label,
            page=candidate["page"],
            box=candidate["box"],
        )
    review.label, review.reviewed_by, review.reviewed_at = (
        body.label,
        current_user.id,
        get_datetime_utc(),
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return LocationPublic.model_validate(review, from_attributes=True)
