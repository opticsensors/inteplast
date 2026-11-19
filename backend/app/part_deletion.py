"""Delete a piece with the data the application keeps for it.

Only rows of the application are removed. The originals of INTEPLAST (local folder or
SharePoint) are never touched: a `StoredFile` that references them is only a pointer.
Uploaded bytes are removed only when no other piece or feature uses them, and features
always survive: they lose the card, attachments and cota links of this piece.

The scope shown to the administrator carries a key. Deleting with a stale key is
rejected, so the confirmation always matches what is actually removed.
"""

import hashlib
import json
import re
import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_
from sqlmodel import Session, col, select

from app.knowledge_models import (
    DrawingLocation,
    EvidenceJob,
    FeatureCharacteristicLink,
    PartCharacteristic,
    PartDocument,
    PartFile,
    PartReference,
)
from app.measurement_models import MeasurementImport
from app.models import (
    Feature,
    FeatureAsset,
    FeatureNote,
    FeaturePartLink,
    Part,
    StoredFile,
)


class DeletionFeature(BaseModel):
    id: uuid.UUID
    name: str


class PartDeletionScope(BaseModel):
    """What deleting the piece removes and what it keeps."""

    part_id: uuid.UUID
    code: str
    name: str | None = None
    folder_path: str | None = None
    features: list[DeletionFeature] = []
    characteristics: int = 0
    feature_characteristic_links: int = 0
    measurement_imports: int = 0
    feature_assets: int = 0
    covers_reset: int = 0
    files_removed: int = 0
    uploads_removed: int = 0
    files_kept: int = 0
    reviewed_locations: int = 0
    jobs: int = 0
    key: str


class PartDeletionResult(BaseModel):
    message: str
    scope: PartDeletionScope


def _count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(
        session.exec(select(func.count()).select_from(statement.subquery())).one()
    )


def _feature_ids(session: Session, part_id: uuid.UUID) -> set[uuid.UUID]:
    linked = session.exec(
        select(FeaturePartLink.feature_id).where(FeaturePartLink.part_id == part_id)
    ).all()
    attached = session.exec(
        select(FeatureAsset.feature_id).where(FeatureAsset.part_id == part_id)
    ).all()
    return set(linked) | set(attached)


def _own_file_ids(session: Session, part_id: uuid.UUID) -> set[uuid.UUID]:
    """Every document the piece points at, from its file lists and feature copies."""
    statements = [
        select(PartDocument.file_id).where(PartDocument.part_id == part_id),
        select(PartFile.file_id).where(PartFile.part_id == part_id),
        select(PartReference.file_id).where(PartReference.part_id == part_id),
        select(FeatureAsset.file_id).where(FeatureAsset.part_id == part_id),
        # Covers of features on this piece: they go with their links.
        select(FeaturePartLink.image_id).where(FeaturePartLink.part_id == part_id),
    ]
    return {
        file_id
        for statement in statements
        for file_id in session.exec(statement).all()
        if file_id is not None
    }


def _shared_file_ids(
    session: Session, part_id: uuid.UUID, file_ids: set[uuid.UUID]
) -> set[uuid.UUID]:
    """Documents that another piece or a feature uses on its own: they are kept."""
    if not file_ids:
        return set()
    ids = list(file_ids)
    statements = [
        select(PartDocument.file_id).where(
            col(PartDocument.file_id).in_(ids), col(PartDocument.part_id) != part_id
        ),
        select(PartFile.file_id).where(
            col(PartFile.file_id).in_(ids), col(PartFile.part_id) != part_id
        ),
        select(PartReference.file_id).where(
            col(PartReference.file_id).in_(ids), col(PartReference.part_id) != part_id
        ),
        select(FeatureAsset.file_id).where(
            col(FeatureAsset.file_id).in_(ids),
            or_(
                col(FeatureAsset.part_id).is_(None),
                col(FeatureAsset.part_id) != part_id,
            ),
        ),
        select(Feature.image_id).where(col(Feature.image_id).in_(ids)),
        select(FeaturePartLink.image_id).where(
            col(FeaturePartLink.image_id).in_(ids),
            col(FeaturePartLink.part_id) != part_id,
        ),
    ]
    shared = {
        file_id
        for statement in statements
        for file_id in session.exec(statement).all()
        if file_id is not None
    }
    return shared | (file_ids & _note_file_ids(session))


# Images inside warnings and lessons: `![name](file:<id>)`.
NOTE_FILE = re.compile(r"file:([0-9a-fA-F-]{36})")


def _note_file_ids(session: Session) -> set[uuid.UUID]:
    """Documents shown inside a feature note: deleting them would break the note."""
    found: set[uuid.UUID] = set()
    for body in session.exec(
        select(FeatureNote.body).where(col(FeatureNote.body).contains("file:"))
    ).all():
        for match in NOTE_FILE.findall(body or ""):
            try:
                found.add(uuid.UUID(match))
            except ValueError:
                continue
    return found


def _rows(session: Session, statement: Any) -> list[dict[str, Any]]:
    """Full content of the rows, in a stable order, for the confirmation key."""
    rows = [row.model_dump(mode="json") for row in session.exec(statement).all()]
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def _removed_assets(session: Session, part_id: uuid.UUID) -> list[FeatureAsset]:
    return list(
        session.exec(select(FeatureAsset).where(FeatureAsset.part_id == part_id)).all()
    )


def _covers_removed(session: Session, part_id: uuid.UUID) -> int:
    """Feature covers made on this piece. They live on its links and go with them;
    the covers of the feature on other pieces are not touched."""
    return _count(
        session,
        select(FeaturePartLink.feature_id).where(
            FeaturePartLink.part_id == part_id,
            col(FeaturePartLink.image_id).is_not(None),
        ),
    )


def scope(session: Session, part: Part) -> PartDeletionScope:
    part_id = part.id
    feature_ids = _feature_ids(session, part_id)
    features = (
        list(
            session.exec(
                select(Feature)
                .where(col(Feature.id).in_(list(feature_ids)))
                .order_by(col(Feature.name))
            ).all()
        )
        if feature_ids
        else []
    )
    assets = _removed_assets(session, part_id)
    own = _own_file_ids(session, part_id)
    shared = _shared_file_ids(session, part_id, own)
    removed = sorted(own - shared)
    removed_files = (
        list(
            session.exec(
                select(StoredFile).where(col(StoredFile.id).in_(removed))
            ).all()
        )
        if removed
        else []
    )
    characteristic_ids = select(PartCharacteristic.id).where(
        PartCharacteristic.part_id == part_id
    )
    jobs = select(EvidenceJob.id).where(
        or_(
            col(EvidenceJob.part_id) == part_id,
            col(EvidenceJob.file_id).in_(removed),
        )
    )
    result = PartDeletionScope(
        part_id=part_id,
        code=part.code,
        name=part.name,
        folder_path=part.folder_path,
        features=[DeletionFeature(id=f.id, name=f.name) for f in features],
        characteristics=_count(session, characteristic_ids),
        feature_characteristic_links=_count(
            session,
            select(FeatureCharacteristicLink.feature_id).where(
                col(FeatureCharacteristicLink.characteristic_id).in_(characteristic_ids)
            ),
        ),
        measurement_imports=_count(
            session,
            select(MeasurementImport.id).where(MeasurementImport.part_id == part_id),
        ),
        feature_assets=len(assets),
        covers_reset=_covers_removed(session, part_id),
        files_removed=len(removed_files),
        uploads_removed=sum(1 for f in removed_files if f.source == "upload"),
        files_kept=len(own & shared),
        reviewed_locations=_count(
            session,
            select(DrawingLocation.id).where(col(DrawingLocation.file_id).in_(removed)),
        )
        if removed
        else 0,
        jobs=_count(session, jobs),
        key="",
    )
    # The key binds the confirmation to these exact rows, not only to their counts.
    # Rows that are deleted enter with their whole content, so that editing one of them
    # (a dimension, an import, a reviewed location) also asks for a new review.
    identity = {
        "scope": result.model_dump(mode="json", exclude={"key"}),
        "assets": _rows(
            session, select(FeatureAsset).where(FeatureAsset.part_id == part_id)
        ),
        "feature_links": _rows(
            session, select(FeaturePartLink).where(FeaturePartLink.part_id == part_id)
        ),
        "removed": [str(file_id) for file_id in removed],
        "kept": sorted(str(file_id) for file_id in own & shared),
        "characteristics": _rows(
            session,
            select(PartCharacteristic).where(PartCharacteristic.part_id == part_id),
        ),
        "links": _rows(
            session,
            select(FeatureCharacteristicLink).where(
                col(FeatureCharacteristicLink.characteristic_id).in_(characteristic_ids)
            ),
        ),
        "imports": _rows(
            session,
            select(MeasurementImport).where(MeasurementImport.part_id == part_id),
        ),
        "locations": _rows(
            session,
            select(DrawingLocation).where(col(DrawingLocation.file_id).in_(removed)),
        )
        if removed
        else [],
        # Jobs only by identity: their progress changes while the dialog is open.
        "jobs": sorted(str(job_id) for job_id in session.exec(jobs).all()),
    }
    result.key = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()
    return result


def lock_part(session: Session, part_id: uuid.UUID) -> Part:
    part = session.exec(
        select(Part).where(Part.id == part_id).with_for_update()
    ).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    # Wait for an evidence import that is publishing into this piece, so that the
    # scope includes whatever it writes. Rows deleted below make later runs a no-op.
    session.exec(
        select(EvidenceJob.id).where(EvidenceJob.part_id == part_id).with_for_update()
    ).all()
    return part


def delete(
    session: Session, part: Part, key: str
) -> tuple[PartDeletionScope, list[StoredFile]]:
    """Delete the piece inside the caller's transaction; the caller commits.

    Returns the scope and the removed documents, so that uploaded bytes and previews
    can be cleaned once the transaction is committed.
    """
    # Lock the features of the piece first, like a cover save does, so that no cover
    # lands on its links between the confirmed scope and the deletion.
    feature_ids = _feature_ids(session, part.id)
    session.exec(
        select(Feature.id)
        .where(
            or_(
                col(Feature.id).in_(list(feature_ids)),
                cast(Feature.part_order, String).contains(str(part.id)),
            )
        )
        .order_by(col(Feature.id))
        .with_for_update()
    ).all()
    current = scope(session, part)
    if current.key != key:
        raise HTTPException(
            status_code=409,
            detail="Los datos de la pieza han cambiado. Revisa de nuevo el alcance antes de eliminarla.",
        )
    part_id = part.id
    assets = _removed_assets(session, part_id)
    feature_ids = _feature_ids(session, part_id)
    order_mentions = session.exec(
        select(Feature).where(cast(Feature.part_order, String).contains(str(part_id)))
    ).all()
    features = {feature.id: feature for feature in order_mentions}
    if feature_ids:
        features.update(
            (feature.id, feature)
            for feature in session.exec(
                select(Feature).where(col(Feature.id).in_(list(feature_ids)))
            ).all()
        )
    for feature in features.values():
        feature.part_order = [
            item for item in feature.part_order if item != str(part_id)
        ]
        session.add(feature)

    own = _own_file_ids(session, part_id)
    removed_ids = own - _shared_file_ids(session, part_id, own)
    removed = (
        list(
            session.exec(
                select(StoredFile).where(col(StoredFile.id).in_(list(removed_ids)))
            ).all()
        )
        if removed_ids
        else []
    )

    for asset in assets:
        session.delete(asset)
    characteristic_ids = select(PartCharacteristic.id).where(
        PartCharacteristic.part_id == part_id
    )
    for link in session.exec(
        select(FeatureCharacteristicLink).where(
            col(FeatureCharacteristicLink.characteristic_id).in_(characteristic_ids)
        )
    ).all():
        session.delete(link)
    rows: list[object] = [
        *session.exec(
            select(MeasurementImport).where(MeasurementImport.part_id == part_id)
        ).all(),
        *session.exec(
            select(PartCharacteristic).where(PartCharacteristic.part_id == part_id)
        ).all(),
        *session.exec(
            select(PartDocument).where(PartDocument.part_id == part_id)
        ).all(),
        *session.exec(select(PartFile).where(PartFile.part_id == part_id)).all(),
        *session.exec(
            select(PartReference).where(PartReference.part_id == part_id)
        ).all(),
        *session.exec(
            select(FeaturePartLink).where(FeaturePartLink.part_id == part_id)
        ).all(),
    ]
    for row in rows:
        session.delete(row)
    for job in session.exec(
        select(EvidenceJob).where(
            or_(
                col(EvidenceJob.part_id) == part_id,
                col(EvidenceJob.file_id).in_(list(removed_ids)),
            )
        )
    ).all():
        session.delete(job)
    if removed_ids:
        for location in session.exec(
            select(DrawingLocation).where(
                col(DrawingLocation.file_id).in_(list(removed_ids))
            )
        ).all():
            session.delete(location)
    session.flush()
    for document in removed:
        session.delete(document)
    session.delete(part)
    session.flush()
    return current, removed
