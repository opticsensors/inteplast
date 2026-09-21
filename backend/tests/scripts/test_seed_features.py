from importlib import import_module
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app.models import AssetKind, Feature, FeatureNote, NoteKind, Part
from app.seed_features import seed


def test_seed_rolls_back_late_failure_and_can_be_retried(db: Session) -> None:
    # Other API tests may create a feature with the sample's name. This is the
    # isolated test database; give the real seed its required empty starting state.
    db.exec(delete(Feature).where(Feature.name == "Bolt Eye"))
    db.commit()
    original_part = db.exec(select(Part).where(Part.code == "3212")).first()
    original_part_id = original_part.id if original_part else None

    # Fail at the last inserts, after the feature, notes and part have been flushed.
    with (
        patch("app.seed_features.BOLT_EYE_ASSETS", [(AssetKind.part, None)]),
        pytest.raises(IntegrityError),
    ):
        seed(db)

    assert db.exec(select(Feature).where(Feature.name == "Bolt Eye")).first() is None
    part = db.exec(select(Part).where(Part.code == "3212")).first()
    assert (part.id if part else None) == original_part_id

    seed(db)
    feature = db.exec(select(Feature).where(Feature.name == "Bolt Eye")).one()
    assert len(feature.notes) == 10
    assert len(feature.assets) == 5
    assert [part.code for part in feature.parts] == ["3212"]
    first_id = feature.id

    seed(db)
    feature = db.exec(select(Feature).where(Feature.name == "Bolt Eye")).one()
    assert feature.id == first_id
    assert len(feature.notes) == 10
    assert len(feature.assets) == 5


def test_n170_migration_preserves_edited_lessons(db: Session) -> None:
    migration = import_module("app.alembic.versions.g28b14daef96_correct_seed_n170")
    feature = Feature(name="Bolt Eye")
    db.add(feature)
    db.flush()
    title = "Retoque de molde 1.33 sobre N170 (correccion 1)"
    original = FeatureNote(
        feature_id=feature.id, kind=NoteKind.lesson, title=title, body=migration.OLD
    )
    edited = FeatureNote(
        feature_id=feature.id,
        kind=NoteKind.lesson,
        title=title,
        body="Reviewed by the team",
    )
    db.add(original)
    db.add(edited)
    db.commit()
    with patch.object(migration.op, "get_bind", return_value=db.connection()):
        migration.upgrade()
    db.commit()
    db.refresh(original)
    db.refresh(edited)
    assert original.body == migration.NEW
    assert edited.body == "Reviewed by the team"
