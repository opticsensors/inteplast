from sqlmodel import Session

from app import crud
from app.models import (
    AssetKind,
    Feature,
    FeatureAsset,
    FeatureAssetCreate,
    FeatureCategory,
    FeatureCreate,
    FeatureNote,
    FeatureNoteCreate,
    NoteKind,
)
from tests.utils.utils import random_lower_string


def create_random_feature(
    db: Session,
    *,
    name: str | None = None,
    category: FeatureCategory | None = FeatureCategory.hole,
    tags: list[str] | None = None,
) -> Feature:
    feature_in = FeatureCreate(
        name=name or random_lower_string(),
        description=random_lower_string(),
        category=category,
        tags=tags if tags is not None else [random_lower_string()],
    )
    return crud.create_feature(session=db, feature_in=feature_in)


def create_random_note(
    db: Session, feature: Feature, *, kind: NoteKind = NoteKind.warning
) -> FeatureNote:
    note_in = FeatureNoteCreate(
        kind=kind, title=random_lower_string(), body=random_lower_string()
    )
    return crud.create_feature_note(session=db, note_in=note_in, feature_id=feature.id)


def create_random_asset(
    db: Session,
    feature: Feature,
    *,
    kind: AssetKind = AssetKind.mold,
    part_ref: str | None = None,
) -> FeatureAsset:
    asset_in = FeatureAssetCreate(
        kind=kind,
        name=random_lower_string(),
        part_ref=part_ref or random_lower_string(),
    )
    return crud.create_feature_asset(
        session=db, asset_in=asset_in, feature_id=feature.id
    )
