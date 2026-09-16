"""Validate a cover against its feature's linked CAD and current original bytes."""

import hashlib
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session

from app.file_sources import document_path
from app.models import AssetKind, Feature, FeatureAsset, FeatureCover3D, StoredFile


def validate_cover(session: Session, feature: Feature, cover: FeatureCover3D) -> None:
    asset = session.get(FeatureAsset, cover.asset_id)
    if (
        not asset
        or asset.feature_id != feature.id
        or asset.kind != AssetKind.part
        or asset.part_id != cover.part_id
        or asset.file_id != cover.file_id
    ):
        raise HTTPException(
            409, "Vincula primero el STEP como pieza CAD de este feature."
        )
    document = session.get(StoredFile, cover.file_id)
    if not document or Path(document.filename).suffix.lower() not in {".step", ".stp"}:
        raise HTTPException(422, "La portada necesita un archivo STEP de la pieza.")
    if document.size > 50 * 1024 * 1024:
        raise HTTPException(
            422, "La selección de superficies admite STEP de hasta 50 MB."
        )
    if document.version != cover.file_version:
        raise HTTPException(
            409, "El CAD ha cambiado. Revisa la portada antes de guardarla."
        )
    original = document_path(document)
    digest = hashlib.sha256()
    try:
        with original.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise HTTPException(503, "No se puede comprobar el CAD de la portada.")
    # Recheck source availability/version after reading as well.
    document_path(document)
    if digest.hexdigest() != cover.source_sha256:
        raise HTTPException(
            409, "El CAD ha cambiado. Revisa la portada antes de guardarla."
        )
