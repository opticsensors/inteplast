import uuid

from fastapi import APIRouter, HTTPException

from app import measurement_imports
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import get_part_or_404
from app.file_sources import SourceError
from app.measurement_models import (
    MeasurementCommitRequest,
    MeasurementCommitResult,
    MeasurementImportSummary,
    MeasurementPreview,
    MeasurementPreviewRequest,
)
from app.models import Part

router = APIRouter(prefix="/evidence/parts/{part_id}/measurements", tags=["evidence"])


def linked_part(session: SessionDep, part_id: uuid.UUID) -> Part:
    part = get_part_or_404(session, part_id)
    return part


@router.post("/preview", response_model=MeasurementPreview)
def preview_measurements(
    session: SessionDep,
    _current_user: CurrentUser,
    part_id: uuid.UUID,
    body: MeasurementPreviewRequest,
) -> MeasurementPreview:
    part = linked_part(session, part_id)
    try:
        return measurement_imports.prepare(session, part, body)[0]
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)


@router.post("/import", response_model=MeasurementCommitResult)
def import_measurements(
    session: SessionDep,
    current_user: CurrentUser,
    part_id: uuid.UUID,
    body: MeasurementCommitRequest,
) -> MeasurementCommitResult:
    part = linked_part(session, part_id)
    try:
        return measurement_imports.commit(session, part, current_user.id, body)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)


@router.get("/history", response_model=list[MeasurementImportSummary])
def measurement_history(
    session: SessionDep, _current_user: CurrentUser, part_id: uuid.UUID
) -> list[MeasurementImportSummary]:
    get_part_or_404(session, part_id)
    return measurement_imports.history_summary(session, part_id)
