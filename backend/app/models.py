import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    FiniteFloat,
    StringConstraints,
    model_validator,
)
from sqlalchemy import ARRAY, JSON, Column, DateTime, String
from sqlmodel import AutoString, Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr = Field(default=None, max_length=255)
    password: str = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str = Field(default=None, min_length=1, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ---------------------------------------------------------------------------
# Ficheros subidos (imagenes de features, CAD, planos PDF)
# ---------------------------------------------------------------------------


# Stable document identity. Legacy table name retained to preserve all existing FKs.
# Location is resolved by app.file_sources, never by a viewer or feature.
class StoredFile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=255)
    size: int = 0
    source: str = Field(default="upload", max_length=32)
    source_key: str | None = Field(default=None, max_length=100)
    source_path: str | None = Field(default=None, max_length=2048)
    source_version: str | None = Field(default=None, max_length=100)
    version: uuid.UUID | None = None
    revision: str | None = Field(default=None, max_length=100)
    reference_key: str | None = Field(default=None, max_length=64, unique=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FilePublic(SQLModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    created_at: datetime | None = None
    source: str = "upload"
    version: uuid.UUID | None = None
    revision: str | None = None


class LocalFileReference(SQLModel):
    path: str = Field(min_length=1, max_length=2048)
    revision: str | None = Field(default=None, max_length=100)


class RelinkFileReference(LocalFileReference):
    expected_version: uuid.UUID


class SourceEntry(SQLModel):
    name: str
    path: str
    directory: bool
    size: int | None = None


class SourceListing(SQLModel):
    configured: bool
    name: str
    path: str
    entries: list[SourceEntry]
    count: int


class FileStatus(SQLModel):
    state: Literal["available", "missing", "changed", "unavailable"]
    message: str
    path: str | None = None


class FileAccessPublic(SQLModel):
    url: str
    expires_at: datetime


class FilePreview(SQLModel, table=True):
    """One replaceable, disposable web representation per original document."""

    file_id: uuid.UUID = Field(
        primary_key=True, foreign_key="storedfile.id", ondelete="CASCADE"
    )
    cache_key: str = Field(max_length=64)
    state: str = Field(default="queued", max_length=16, index=True)
    message: str | None = Field(default=None, max_length=255)
    size: int = 0
    triangles: int = 0
    source_sha256: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FilePreviewPublic(SQLModel):
    state: Literal["queued", "processing", "ready", "error"]
    message: str | None = None
    url: str | None = None


# ---------------------------------------------------------------------------
# Base de conocimiento de features
# ---------------------------------------------------------------------------


# Tipos geometricos comunes con los que se clasifica un feature
class FeatureCategory(str, Enum):
    hole = "hole"
    rib = "rib"
    thickness = "thickness"
    boss = "boss"
    fillet = "fillet"
    draft = "draft"
    other = "other"


# Un mismo tipo de nota sirve para advertencias y lecciones aprendidas
class NoteKind(str, Enum):
    warning = "warning"
    lesson = "lesson"


# Los tipos de fichero que una pieza puede aportar en "piezas ejemplo"
class AssetKind(str, Enum):
    mold = "mold"
    part = "part"
    scan = "scan"
    drawing = "drawing"
    moldflow = "moldflow"


# ---------------------------------------------------------------------------
# Pieza = proyecto = molde. Embrion del PROYECTO de docs/modelo-datos.md: el
# numero de 4 digitos (3212) que prefija todos los ficheros del proyecto.
# ---------------------------------------------------------------------------


class PartBase(SQLModel):
    code: str = Field(min_length=1, max_length=64, unique=True, index=True)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    customer: str | None = Field(default=None, max_length=255)
    # Relative to the configured source; never an absolute workstation path.
    folder_path: str | None = Field(
        default=None, max_length=2048, unique=True, index=True
    )


class PartCreate(PartBase):
    pass


class PartFromFolder(SQLModel):
    folder_path: str = Field(min_length=1, max_length=2048)


ReferenceKind = Literal["part", "scan", "mold", "drawing"]


class ReferenceChoice(BaseModel):
    kind: ReferenceKind
    path: str | None = Field(default=None, max_length=2048)
    source_version: str | None = None


PartFileKind = Literal["part", "scan", "mold", "drawing", "moldflow", "document"]


class PartFileInput(BaseModel):
    file_id: uuid.UUID | None = None
    path: str | None = Field(default=None, max_length=2048)
    source_version: str | None = None
    kind: PartFileKind
    name: str = Field(min_length=1, max_length=255)
    primary: bool = False


class PartUpdate(SQLModel):
    code: str = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    customer: str | None = Field(default=None, max_length=255)
    folder_path: str | None = Field(default=None, max_length=2048)
    references: list[ReferenceChoice] | None = Field(default=None, max_length=4)
    files: list[PartFileInput] | None = Field(default=None, max_length=200)


class FeaturePartOrder(SQLModel):
    part_ids: list[uuid.UUID]


class FeatureNoteOrder(SQLModel):
    kind: NoteKind
    note_ids: list[uuid.UUID]


class FeatureAssetOrder(SQLModel):
    part_id: uuid.UUID | None = None
    asset_ids: list[uuid.UUID]


class FeaturePartLink(SQLModel, table=True):
    """Feature presente en una pieza, tenga o no ficheros adjuntos.

    Embrion de INSTANCIA_EN_PROYECTO (docs/modelo-datos.md): aqui colgaran los
    N-numbers y las tolerancias con que cada pieza materializa el feature.
    """

    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", primary_key=True, ondelete="CASCADE"
    )
    part_id: uuid.UUID = Field(
        foreign_key="part.id", primary_key=True, ondelete="CASCADE"
    )


class Part(PartBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    files_managed: bool = False
    last_read: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    features: list["Feature"] = Relationship(
        back_populates="parts", link_model=FeaturePartLink
    )


class PartPublic(PartBase):
    id: uuid.UUID
    created_at: datetime | None = None


class PartCatalogPublic(PartPublic):
    feature_count: int


class PartsPublic(SQLModel):
    data: list[PartCatalogPublic]
    count: int


# Shared properties
class FeatureBase(SQLModel):
    name: str = Field(min_length=1, max_length=255, index=True)
    description: str | None = Field(default=None, max_length=2000)
    category: FeatureCategory | None = Field(
        default=None, index=True, sa_type=AutoString
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_type=ARRAY(String),  # type: ignore
    )


# Properties to receive on feature creation
class FeatureCreate(FeatureBase):
    image_id: uuid.UUID | None = None


class CadFaceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mesh: int = Field(ge=0, le=1000000)
    face: int = Field(ge=0, le=1000000)


class CadCamera(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    target: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    up: tuple[FiniteFloat, FiniteFloat, FiniteFloat]

    @model_validator(mode="after")
    def valid_view(self) -> "CadCamera":
        direction = [a - b for a, b in zip(self.position, self.target, strict=True)]
        cross = [
            direction[1] * self.up[2] - direction[2] * self.up[1],
            direction[2] * self.up[0] - direction[0] * self.up[2],
            direction[0] * self.up[1] - direction[1] * self.up[0],
        ]
        if any(abs(v) > 1e12 for v in (*self.position, *self.target, *self.up)):
            raise ValueError("Camera coordinates out of range")
        if sum(v * v for v in cross) < 1e-12:
            raise ValueError("Camera direction and up must define a view")
        return self


Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class FeatureCover3D(BaseModel):
    """An annotation tied to exact source bytes and a deterministic tessellation."""

    model_config = ConfigDict(extra="forbid")
    asset_id: uuid.UUID
    part_id: uuid.UUID
    file_id: uuid.UUID
    file_version: uuid.UUID | None = None
    source_sha256: Sha256
    geometry_key: Sha256
    recipe: Literal["occt-import-js@0.0.23/cover-v1"]
    faces: list[CadFaceSelection] = Field(min_length=1, max_length=5000)
    camera: CadCamera

    @model_validator(mode="after")
    def unique_faces(self) -> "FeatureCover3D":
        if len({(face.mesh, face.face) for face in self.faces}) != len(self.faces):
            raise ValueError("Duplicate CAD faces")
        return self


# Properties to receive on feature update
class FeatureUpdate(SQLModel):
    # Omitted fields stay unchanged; explicit null is only valid for nullable columns.
    name: str = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: FeatureCategory | None = None
    tags: list[str] = Field(default=None)
    image_id: uuid.UUID | None = None
    cover_3d: FeatureCover3D | None = None


# Database model, database table inferred from class name
class Feature(FeatureBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    # Quien lo creo. La ficha sobrevive al borrado del usuario: es conocimiento
    # compartido, no contenido personal.
    owner_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    image_id: uuid.UUID | None = Field(
        default=None, foreign_key="storedfile.id", ondelete="SET NULL"
    )
    image: StoredFile | None = Relationship()
    cover_3d: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    part_order: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    notes: list["FeatureNote"] = Relationship(
        back_populates="feature",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "FeatureNote.position"},
    )
    assets: list["FeatureAsset"] = Relationship(
        back_populates="feature",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "FeatureAsset.position"},
    )
    # Piezas en las que el feature esta declarado, tengan ficheros o no. Las
    # que si los tienen salen igualmente por `assets`; la vista une las dos.
    parts: list["Part"] = Relationship(
        back_populates="features",
        link_model=FeaturePartLink,
        sa_relationship_kwargs={"order_by": "Part.code"},
    )


# Advertencia o leccion aprendida asociada a un feature
class FeatureNoteBase(SQLModel):
    kind: NoteKind = Field(sa_type=AutoString)
    title: str = Field(min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=20000)
    position: int = 0


class FeatureNoteCreate(FeatureNoteBase):
    pass


class FeatureNoteUpdate(SQLModel):
    kind: NoteKind = Field(default=None)
    title: str = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=20000)
    position: int = Field(default=None)


class FeatureNote(FeatureNoteBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", nullable=False, ondelete="CASCADE"
    )
    feature: Feature | None = Relationship(back_populates="notes")


class FeatureNotePublic(FeatureNoteBase):
    id: uuid.UUID
    feature_id: uuid.UUID
    created_at: datetime | None = None


# Fichero de ejemplo (molde, CAD, escaneo, plano 2D, Moldflow) de una pieza
class FeatureAssetBase(SQLModel):
    kind: AssetKind = Field(sa_type=AutoString)
    name: str = Field(min_length=1, max_length=255)
    position: int = 0


class FeatureAssetCreate(FeatureAssetBase):
    part_id: uuid.UUID | None = None
    file_id: uuid.UUID | None = None


class FeatureAssetUpdate(SQLModel):
    kind: AssetKind = Field(default=None)
    name: str = Field(default=None, min_length=1, max_length=255)
    position: int = Field(default=None)
    part_id: uuid.UUID | None = None
    file_id: uuid.UUID | None = None


class FeatureAsset(FeatureAssetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", nullable=False, ondelete="CASCADE"
    )
    # Borrar la pieza no borra el adjunto: cae al grupo "sin pieza"
    part_id: uuid.UUID | None = Field(
        default=None, foreign_key="part.id", index=True, ondelete="SET NULL"
    )
    file_id: uuid.UUID | None = Field(
        default=None, foreign_key="storedfile.id", ondelete="SET NULL"
    )
    feature: Feature | None = Relationship(back_populates="assets")
    part: Part | None = Relationship()
    file: StoredFile | None = Relationship()


class FeatureAssetPublic(FeatureAssetBase):
    id: uuid.UUID
    feature_id: uuid.UUID
    created_at: datetime | None = None
    part: PartPublic | None = None
    file: FilePublic | None = None


# Lo que se pinta en una tarjeta de resultado
class FeaturePublic(FeatureBase):
    id: uuid.UUID
    created_at: datetime | None = None
    owner_id: uuid.UUID | None = None
    image: FilePublic | None = None
    cover_3d: FeatureCover3D | None = None
    part_order: list[uuid.UUID] = Field(default_factory=list)
    assets: list[FeatureAssetPublic] = []
    parts: list[PartPublic] = []


# Lo que se pinta en la modal de detalle
class FeatureDetail(FeaturePublic):
    notes: list[FeatureNotePublic] = []


class FeaturesPublic(SQLModel):
    data: list[FeaturePublic]
    count: int


# Valores disponibles para los filtros del dashboard
class FeatureFilterOption(SQLModel):
    id: uuid.UUID
    name: str
    category: FeatureCategory | None = None
    tags: list[str] = Field(default_factory=list)
    part_ids: list[uuid.UUID] = Field(default_factory=list)


class FeatureFilters(SQLModel):
    categories: list[FeatureCategory]
    tags: list[str]
    parts: list[PartPublic]
    features: list[FeatureFilterOption]


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: uuid.UUID


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
