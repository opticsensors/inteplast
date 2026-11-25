"""Versioned renderings of CAD face selections. The original captures stay on the links."""

import uuid

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from app.evidence import digest, job_id
from app.knowledge_models import EvidenceJob, PartFile
from app.models import Feature, FeatureCover3D, FeaturePartLink, FilePublic, StoredFile


class FaceLayer(BaseModel):
    feature_id: uuid.UUID
    name: str
    color: str
    selection: FeatureCover3D


class FaceColors(BaseModel):
    key: str
    layers: list[FaceLayer]
    review: dict[str, str]
    images: dict[str, FilePublic]


def marked_part(session: Session, part_id: uuid.UUID) -> bool:
    return (
        session.exec(
            select(FeaturePartLink.feature_id)
            .where(
                FeaturePartLink.part_id == part_id,
                func.json_array_length(col(FeaturePartLink.cover_3d)["faces"]) > 0,
            )
            .limit(1)
        ).first()
        is not None
    )


def face_colors(
    session: Session,
    part_id: uuid.UUID,
    cad: StoredFile,
    source_key: str,
    gray: EvidenceJob | None,
) -> FaceColors | None:
    rows = session.exec(
        select(FeaturePartLink, Feature)
        .join(Feature, col(Feature.id) == col(FeaturePartLink.feature_id))
        .where(FeaturePartLink.part_id == part_id)
        .order_by(col(Feature.id))
    ).all()
    marked = [
        (link, feature) for link, feature in rows if (link.cover_3d or {}).get("faces")
    ]
    if not marked:
        return None
    key = digest(
        [
            "face-colors-v2",
            source_key,
            [
                [
                    str(feature.id),
                    feature.color,
                    {
                        k: v
                        for k, v in (link.cover_3d or {}).items()
                        if k not in {"source_key", "primary_at_selection"}
                    },
                ]
                for link, feature in marked
            ],
        ]
    )
    job = session.get(EvidenceJob, job_id("face-colors", part_id))
    current = (
        job.payload
        if job and job.file_id == cad.id and job.payload.get("source_key") == source_key
        else {}
    )
    sha = current.get("source_sha256")
    if (
        not sha
        and gray
        and gray.file_id == cad.id
        and source_key in (gray.cache_key, gray.payload.get("source_key"))
    ):
        sha = gray.payload.get("source_sha256")
    layers = []
    review = {}
    for link, feature in marked:
        data = link.cover_3d
        assert data is not None
        if data.get("file_id") != str(cad.id):
            # An intentionally selected component has its own coordinates.
            if data.get("primary_at_selection") is False or (
                data.get("primary_at_selection") is None
                and session.get(PartFile, (part_id, uuid.UUID(data["file_id"])))
                is not None
            ):
                continue
            review[str(feature.id)] = feature.name
            continue
        if (
            data.get("recipe") != "occt-import-js@0.0.23/cover-v1"
            or data.get("file_version") != (str(cad.version) if cad.version else None)
            or (sha and data.get("source_sha256") != sha)
            or (
                current.get("geometry_key")
                and data.get("geometry_key") != current["geometry_key"]
            )
            or (not sha and data.get("source_key") and data["source_key"] != source_key)
        ):
            review[str(feature.id)] = feature.name
            continue
        layers.append(
            FaceLayer(
                feature_id=feature.id,
                name=feature.name,
                color=feature.color,
                selection=FeatureCover3D.from_stored(data),
            )
        )
    images = {}
    if job and job.cache_key == key:
        for variant, image_id in current.get("images", {}).items():
            image = session.get(StoredFile, uuid.UUID(image_id))
            if image:
                images[variant] = FilePublic.model_validate(image)
    return FaceColors(key=key, layers=layers, review=review, images=images)
