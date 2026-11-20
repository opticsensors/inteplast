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
from sqlalchemy import JSON, Column, DateTime
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
    # Whose SharePoint permissions the conversion uses to read the original.
    requested_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
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


def catalog_key(name: str) -> str:
    """Identity of a family or customer name: no case, no extra spaces.

    «Bosch», «bosch» and «Bosch » are the same entry; «Robert Bosch» is another one.
    """
    return " ".join(name.split()).casefold()


class CatalogNameCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)


class CatalogNamePublic(SQLModel):
    id: uuid.UUID
    name: str


class CatalogNamesPublic(SQLModel):
    data: list[CatalogNamePublic]


class PartFamily(SQLModel, table=True):
    """Kind of piece (Pump Housing, Pot…), shared list that users extend."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=255)
    key: str = Field(max_length=255, unique=True, index=True)


class Customer(SQLModel, table=True):
    """Company that orders the piece from INTEPLAST, shared list that users extend."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=255)
    key: str = Field(max_length=255, unique=True, index=True)


class PartBase(SQLModel):
    code: str = Field(min_length=1, max_length=64, unique=True, index=True)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    family_id: uuid.UUID | None = Field(
        default=None, foreign_key="partfamily.id", index=True, ondelete="RESTRICT"
    )
    customer_id: uuid.UUID | None = Field(
        default=None, foreign_key="customer.id", index=True, ondelete="RESTRICT"
    )
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
    # Omitted keeps the value; null leaves the piece without family or customer.
    family_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
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
    Tambien guarda la portada de este feature en esta pieza: la captura y, si se
    hizo sobre el CAD, sus caras y su encuadre (docs/plan-portadas-por-pieza-2026-11-18.md).
    """

    feature_id: uuid.UUID = Field(
        foreign_key="feature.id", primary_key=True, ondelete="CASCADE"
    )
    part_id: uuid.UUID = Field(
        foreign_key="part.id", primary_key=True, ondelete="CASCADE"
    )
    image_id: uuid.UUID | None = Field(
        default=None, foreign_key="storedfile.id", ondelete="SET NULL"
    )
    cover_3d: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )


class Part(PartBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    files_managed: bool = False
    components: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    # "file:<path>" / "sheet:<name>" left without component on purpose: no proposals.
    component_unassigned: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    last_read: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    features: list["Feature"] = Relationship(
        back_populates="parts", link_model=FeaturePartLink
    )
    family: PartFamily | None = Relationship()
    customer: Customer | None = Relationship()


class PartPublic(PartBase):
    id: uuid.UUID
    created_at: datetime | None = None
    family: CatalogNamePublic | None = None
    customer: CatalogNamePublic | None = None


class PartCatalogPublic(PartPublic):
    feature_count: int


class PartsPublic(SQLModel):
    data: list[PartCatalogPublic]
    count: int


# Shared properties
class FeatureBase(SQLModel):
    name: str = Field(min_length=1, max_length=255, index=True)
    description: str | None = Field(default=None, max_length=2000)


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
    faces: list[CadFaceSelection] = Field(max_length=5000)
    camera: CadCamera

    @model_validator(mode="after")
    def unique_faces(self) -> "FeatureCover3D":
        if len({(face.mesh, face.face) for face in self.faces}) != len(self.faces):
            raise ValueError("Duplicate CAD faces")
        return self


class FeaturePartCoverChange(BaseModel):
    """The new cover of the feature in one piece.

    An image, optionally made on the piece's CAD; no image removes the own cover and the
    piece shows its CAD capture again.
    """

    model_config = ConfigDict(extra="forbid")
    part_id: uuid.UUID
    image_id: uuid.UUID | None = None
    cover_3d: FeatureCover3D | None = None


# Properties to receive on feature update
class FeatureUpdate(SQLModel):
    # Omitted fields stay unchanged; explicit null is only valid for nullable columns.
    name: str = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    # Image of the feature itself: only shown while it has no pieces.
    image_id: uuid.UUID | None = None
    # Covers changed on some pieces, saved with the header in one transaction.
    part_covers: list[FeaturePartCoverChange] | None = Field(
        default=None, max_length=500
    )

    @model_validator(mode="before")
    @classmethod
    def no_feature_cad_cover(cls, data: Any) -> Any:
        # A page opened before covers per piece would lose its faces silently.
        if isinstance(data, dict) and "cover_3d" in data:
            raise ValueError(
                "La portada CAD se guarda por pieza, en part_covers. Recarga la ficha."
            )
        return data


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
    # No longer written: the CAD cover lives on each FeaturePartLink since the
    # migration p27ea3fbd174. Kept one batch so that its downgrade can restore it.
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


class FeaturePartCoverPublic(BaseModel):
    """What the cover shows for one piece of the feature.

    `image` and `cover_3d` are the capture made for this feature; `auto_image` is the
    saved catalogue capture of the piece's CAD, shown when there is no own capture.
    """

    part_id: uuid.UUID
    image: FilePublic | None = None
    cover_3d: FeatureCover3D | None = None
    auto_image: FilePublic | None = None


# Lo que se pinta en una tarjeta de resultado
class FeaturePublic(FeatureBase):
    id: uuid.UUID
    created_at: datetime | None = None
    owner_id: uuid.UUID | None = None
    # Image of the feature itself, without piece: only shown while it has none.
    image: FilePublic | None = None
    part_order: list[uuid.UUID] = Field(default_factory=list)
    assets: list[FeatureAssetPublic] = []
    parts: list[PartPublic] = []
    # Card: the cover of the first piece (own capture, else the CAD one), or the
    # feature image when it has no pieces; and how many pieces it has.
    cover_image: FilePublic | None = None
    part_count: int = 0


# Lo que se pinta en la modal de detalle
class FeatureDetail(FeaturePublic):
    notes: list[FeatureNotePublic] = []
    # One per piece, in the order of the piece list.
    part_covers: list[FeaturePartCoverPublic] = []


class FeaturesPublic(SQLModel):
    data: list[FeaturePublic]
    count: int


# Valores disponibles para los filtros del dashboard
class FeatureFilterOption(SQLModel):
    id: uuid.UUID
    name: str
    part_ids: list[uuid.UUID] = Field(default_factory=list)


class FeatureFilters(SQLModel):
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
