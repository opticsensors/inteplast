import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import ARRAY, DateTime, String
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
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


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
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


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


# Database model for an uploaded file. The bytes live on disk under
# settings.UPLOADS_DIR, named after the row id; the row keeps the metadata.
class StoredFile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=255)
    size: int = 0
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


class PartCreate(PartBase):
    pass


class PartUpdate(SQLModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)


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


class PartsPublic(SQLModel):
    data: list[PartPublic]
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


# Properties to receive on feature update
class FeatureUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: FeatureCategory | None = None
    tags: list[str] | None = None
    image_id: uuid.UUID | None = None


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
    kind: NoteKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=20000)
    position: int | None = None


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
    kind: AssetKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    position: int | None = None
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
    assets: list[FeatureAssetPublic] = []
    parts: list[PartPublic] = []


# Lo que se pinta en la modal de detalle
class FeatureDetail(FeaturePublic):
    notes: list[FeatureNotePublic] = []


class FeaturesPublic(SQLModel):
    data: list[FeaturePublic]
    count: int


# Valores disponibles para los filtros del dashboard
class FeatureFilters(SQLModel):
    categories: list[FeatureCategory]
    tags: list[str]
    parts: list[PartPublic]


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
