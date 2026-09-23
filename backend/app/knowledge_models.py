"""Piece-scoped evidence. Imported snapshots retain the original evaluation identity."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models import FeatureCategory, FilePublic, PartPublic, get_datetime_utc


class PartCharacteristic(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("part_id", "code", "revision"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    part_id: uuid.UUID = Field(foreign_key="part.id", ondelete="CASCADE", index=True)
    code: str = Field(max_length=64)
    revision: str = Field(default="06", max_length=64)
    title: str = Field(default="", max_length=255)


class FeatureCharacteristicLink(SQLModel, table=True):
    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", ondelete="CASCADE", primary_key=True
    )
    characteristic_id: uuid.UUID = Field(
        foreign_key="partcharacteristic.id", ondelete="CASCADE", primary_key=True
    )
    role: str = Field(default="primary", max_length=32)


class PendingCharacteristic(SQLModel, table=True):
    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", ondelete="CASCADE", primary_key=True
    )
    code: str = Field(primary_key=True, max_length=64)


class PartDocument(SQLModel, table=True):
    part_id: uuid.UUID = Field(
        foreign_key="part.id", ondelete="CASCADE", primary_key=True
    )
    file_id: uuid.UUID = Field(
        foreign_key="storedfile.id", ondelete="RESTRICT", primary_key=True
    )
    kind: str = Field(default="source", max_length=32)


class PartFile(SQLModel, table=True):
    part_id: uuid.UUID = Field(
        foreign_key="part.id", ondelete="CASCADE", primary_key=True
    )
    file_id: uuid.UUID = Field(
        foreign_key="storedfile.id", ondelete="RESTRICT", primary_key=True
    )
    kind: str = Field(max_length=16)
    name: str = Field(max_length=255)
    position: int = 0
    primary: bool = False


class PartReference(SQLModel, table=True):
    """Explicit file choices; null remembers a removal without deleting evidence."""

    part_id: uuid.UUID = Field(
        foreign_key="part.id", ondelete="CASCADE", primary_key=True
    )
    kind: str = Field(primary_key=True, max_length=16)
    file_id: uuid.UUID | None = Field(
        default=None, foreign_key="storedfile.id", ondelete="RESTRICT"
    )


class EvidenceJob(SQLModel, table=True):
    """Durable, restartable import/index queue; stable identity, versioned payload."""

    id: uuid.UUID = Field(primary_key=True)
    kind: str = Field(max_length=16)
    part_id: uuid.UUID | None = Field(
        default=None, foreign_key="part.id", ondelete="CASCADE"
    )
    file_id: uuid.UUID | None = Field(
        default=None, foreign_key="storedfile.id", ondelete="CASCADE"
    )
    cache_key: str = Field(max_length=64)
    state: str = Field(default="queued", max_length=16, index=True)
    message: str | None = None
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DrawingLocation(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("file_id", "sha256", "candidate_id"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID = Field(
        foreign_key="storedfile.id", ondelete="CASCADE", index=True
    )
    sha256: str = Field(max_length=64)
    candidate_id: str = Field(max_length=96)
    label: str = Field(max_length=64)
    page: int
    box: list[float] = Field(sa_column=Column(JSON, nullable=False))
    reviewed_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    reviewed_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CharacteristicPublic(BaseModel):
    id: uuid.UUID
    part_id: uuid.UUID
    code: str
    revision: str
    title: str
    role: str | None = None


class CharacteristicAssignment(BaseModel):
    code: str = PydanticField(pattern=r"^N\d{1,6}(?:\.\d{1,3})?$", max_length=64)
    revision: str = PydanticField(min_length=1, max_length=64)
    role: Literal["primary", "reference", "context"] = "primary"


class FeatureEvidencePublic(BaseModel):
    characteristics: list[CharacteristicPublic]
    pending: list[str]
    cases: list[str]


class JobPublic(BaseModel):
    state: str
    message: str | None = None
    updated_at: datetime | None = None
    payload: dict[str, Any] = {}


class EvidenceDocument(FilePublic):
    relative_path: str | None = None


class MetrologyFeatureInfo(BaseModel):
    id: uuid.UUID
    name: str
    category: FeatureCategory | None = None
    tags: list[str] = []


class MetrologyFeature(MetrologyFeatureInfo):
    characteristics: list[CharacteristicPublic] = []


class MetrologyFeatureChoice(MetrologyFeatureInfo):
    part_ids: list[uuid.UUID] = []


class MetrologyFilters(BaseModel):
    parts: list[PartPublic]
    features: list[MetrologyFeatureChoice]


class MetrologyPart(BaseModel):
    part: PartPublic
    features: list[MetrologyFeature]
    matched_feature_ids: list[uuid.UUID] = []


class MetrologyCatalog(BaseModel):
    data: list[MetrologyPart]
    count: int
    features: list[MetrologyFeature]


class PartEvidencePublic(BaseModel):
    part: PartPublic
    documents: list[EvidenceDocument]
    characteristics: list[CharacteristicPublic]
    features: list[MetrologyFeature] = []
    study: JobPublic
    import_available: bool
    measurement_revisions: list[str] = []
    drawing_file_id: uuid.UUID | None = None
    drawing_reference_set: bool = False
    refresh_job: JobPublic = PydanticField(
        default_factory=lambda: JobPublic(state="empty")
    )


class LocationReview(BaseModel):
    sha256: str = PydanticField(pattern=r"^[0-9a-f]{64}$")
    candidate_id: str = PydanticField(min_length=1, max_length=96)
    label: str = PydanticField(pattern=r"^N\d{1,6}(?:\.\d{1,3})?$", max_length=64)


class LocationPublic(BaseModel):
    id: uuid.UUID
    candidate_id: str
    label: str
    page: int
    box: list[float]
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime


class DrawingPublic(JobPublic):
    reviews: list[LocationPublic] = []
