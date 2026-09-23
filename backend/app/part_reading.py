"""Report explicit data reads without re-importing while checking their progress."""

import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.evidence import job_id
from app.file_sources import SourceError
from app.knowledge_models import EvidenceJob
from app.measurement_models import MeasurementPreview
from app.models import Part, get_datetime_utc
from app.part_setup import PartRefreshResult, ReadFileReport, refresh


def read_report(session: Session, part: Part) -> PartRefreshResult | None:
    if not part.last_read:
        return None
    report = PartRefreshResult.model_validate(part.last_read)
    if report.corrections_key:
        job = session.get(EvidenceJob, job_id("study", part.id))
        if job and job.cache_key == report.corrections_key:
            report.corrections_state = job.state
            report.state = (
                "processing"
                if job.state in {"queued", "processing"}
                else "partial"
                if job.state == "error"
                else "ready"
            )
            for file in report.files:
                if file.group == "corrections":
                    file.status = "used" if job.state == "ready" else job.state
            if job.state == "ready":
                known = {file.path for file in report.files}
                report.files.extend(
                    ReadFileReport(
                        path=path,
                        group="measurements"
                        if path.lower().endswith((".csv", ".txt"))
                        else "corrections",
                        status="used",
                    )
                    for path in job.payload.get("source_files", [])
                    if path not in known
                )
            if job.state == "error" and job.message:
                report.notices.append(job.message)
    return report


def run_read(session: Session, part: Part, user_id: uuid.UUID) -> PartRefreshResult:
    try:
        if not part.folder_path:
            raise HTTPException(422, "Vincula primero la carpeta de esta pieza.")
        result = refresh(session, part, user_id)
    except (HTTPException, SourceError) as error:
        session.rollback()
        result = PartRefreshResult(
            state="error",
            measurements=MeasurementPreview(context_key="", files=[]),
            notices=[
                str(error.detail if isinstance(error, HTTPException) else error.message)
            ],
        )
    result.updated_at = get_datetime_utc().isoformat()
    part.last_read = result.model_dump(mode="json")
    session.add(part)
    session.commit()
    return read_report(session, part) or result
