import uuid
from typing import Any

from sqlalchemy import ColumnElement, func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, or_, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Feature,
    FeatureAsset,
    FeatureAssetCreate,
    FeatureCategory,
    FeatureCreate,
    FeatureFilters,
    FeatureNote,
    FeatureNoteCreate,
    Item,
    ItemCreate,
    User,
    UserCreate,
    UserUpdate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ---------------------------------------------------------------------------
# Base de conocimiento de features
# ---------------------------------------------------------------------------


def create_feature(
    *, session: Session, feature_in: FeatureCreate, owner_id: uuid.UUID | None = None
) -> Feature:
    db_feature = Feature.model_validate(feature_in, update={"owner_id": owner_id})
    session.add(db_feature)
    session.commit()
    session.refresh(db_feature)
    return db_feature


def _search_conditions(
    *,
    q: str | None,
    category: FeatureCategory | None,
    tag: str | None,
    mold: str | None,
) -> list[ColumnElement[bool]]:
    """Filtros del buscador del dashboard, combinados con AND."""
    conditions: list[ColumnElement[bool]] = []

    if q:
        like = f"%{q}%"
        # Busqueda global: nombre, descripcion, tags, y tambien el contenido
        # relacionado (moldes, codigos de pieza, warnings y lessons learned).
        conditions.append(
            or_(
                col(Feature.name).ilike(like),
                col(Feature.description).ilike(like),
                func.array_to_string(col(Feature.tags), " ").ilike(like),
                col(Feature.id).in_(
                    select(FeatureAsset.feature_id).where(
                        or_(
                            col(FeatureAsset.name).ilike(like),
                            col(FeatureAsset.part_ref).ilike(like),
                        )
                    )
                ),
                col(Feature.id).in_(
                    select(FeatureNote.feature_id).where(
                        or_(
                            col(FeatureNote.title).ilike(like),
                            col(FeatureNote.body).ilike(like),
                        )
                    )
                ),
            )
        )

    if category:
        conditions.append(col(Feature.category) == category)

    if tag:
        conditions.append(col(Feature.tags).any(tag))  # type: ignore[arg-type]

    if mold:
        conditions.append(
            col(Feature.id).in_(
                select(FeatureAsset.feature_id).where(
                    col(FeatureAsset.part_ref) == mold
                )
            )
        )

    return conditions


def search_features(
    *,
    session: Session,
    q: str | None = None,
    category: FeatureCategory | None = None,
    tag: str | None = None,
    mold: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Feature], int]:
    conditions = _search_conditions(q=q, category=category, tag=tag, mold=mold)

    count_statement = select(func.count()).select_from(Feature)
    statement = (
        select(Feature)
        .options(selectinload(Feature.assets), selectinload(Feature.image))  # type: ignore[arg-type]
        .order_by(col(Feature.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count = session.exec(count_statement).one()
    features = list(session.exec(statement).all())
    return features, count


def get_feature_filters(*, session: Session) -> FeatureFilters:
    """Valores realmente presentes en la BD, para poblar los desplegables."""
    categories = sorted(
        {c for c in session.exec(select(Feature.category)).all() if c is not None}
    )
    tags = sorted(
        {tag for tags in session.exec(select(Feature.tags)).all() for tag in tags}
    )
    molds = sorted(
        {
            ref
            for ref in session.exec(
                select(FeatureAsset.part_ref).where(
                    col(FeatureAsset.part_ref).isnot(None)
                )
            ).all()
            if ref
        }
    )
    return FeatureFilters(categories=categories, tags=tags, molds=molds)


def create_feature_note(
    *, session: Session, note_in: FeatureNoteCreate, feature_id: uuid.UUID
) -> FeatureNote:
    db_note = FeatureNote.model_validate(note_in, update={"feature_id": feature_id})
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note


def create_feature_asset(
    *, session: Session, asset_in: FeatureAssetCreate, feature_id: uuid.UUID
) -> FeatureAsset:
    db_asset = FeatureAsset.model_validate(asset_in, update={"feature_id": feature_id})
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset
