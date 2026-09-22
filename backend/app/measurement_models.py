"""Immutable measurement imports, shared by every feature using a piece."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field as DBField
from sqlmodel import SQLModel

from app.models import get_datetime_utc


class MeasurementImport(SQLModel, table=True):
    id: uuid.UUID = DBField(default_factory=uuid.uuid4, primary_key=True)
    part_id: uuid.UUID = DBField(foreign_key="part.id", ondelete="RESTRICT", index=True)
    fingerprint: str = DBField(max_length=64, unique=True)
    revision: str = DBField(max_length=64, index=True)
    sample: str = DBField(max_length=64)
    cavity: str = DBField(max_length=64)
    source_path: str
    source_id: str
    sha256: str = DBField(max_length=64)
    reader: str = DBField(max_length=64)
    rows: list[dict[str, Any]] = DBField(sa_column=Column(JSON, nullable=False))
    baseline: dict[str, Any] | None = DBField(default=None, sa_column=Column(JSON))
    imported_by: uuid.UUID | None = DBField(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    imported_at: datetime = DBField(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class MeasurementFileSelection(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    revision: str = Field(default="", max_length=64)
    sample: str = Field(default="", max_length=64)
    cavity: str = Field(default="", max_length=64)
    replace_existing: bool = False


class MeasurementPreviewRequest(BaseModel):
    files: list[MeasurementFileSelection] = Field(default_factory=list, max_length=250)


MeasurementFileStatus = Literal[
    "new",
    "new_sample",
    "new_revision",
    "imported",
    "replacement",
    "needs_context",
    "unsupported",
]


class MeasurementFilePreview(MeasurementFileSelection):
    status: MeasurementFileStatus
    rows: int = 0
    cotas: int = 0
    issues: list[str] = []
    examples: list[dict[str, Any]] = []


class MeasurementPreview(BaseModel):
    context_key: str
    files: list[MeasurementFilePreview]
    notices: list[str] = []


class MeasurementCommitRequest(MeasurementPreviewRequest):
    context_key: str


class MeasurementImportSummary(BaseModel):
    id: uuid.UUID
    revision: str
    sample: str
    cavity: str
    source_path: str
    sha256: str
    imported_at: datetime
    rows: int
    active: bool
    baseline: bool = False


class MeasurementCommitResult(BaseModel):
    imported: int
    skipped: int
    revisions: list[str]
