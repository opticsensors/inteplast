"""Part galleries are shared by every entry point, including attachments on features."""

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, CompoundSelect, delete, union
from sqlmodel import Session, col, select

from app import sharepoint
from app.api.deps import CurrentUser, SessionDep
from app.feature_covers import COVER_IMAGE_TYPES
from app.file_sources import SourceError, document_check
from app.knowledge_models import AttachmentPhoto, PartDocument, PartFile, PartReference
from app.models import FeatureAsset, FilePublic, Part, StoredFile

GalleryKind = Literal["mold", "moldflow", "scan"]
router = APIRouter()


class GalleryChange(BaseModel):
    previous_ids: list[uuid.UUID]
    image_ids: list[uuid.UUID] = Field(max_length=8)


def gallery_scope(
    session: Session,
    kind: GalleryKind,
    part_id: uuid.UUID | None,
    file_id: uuid.UUID | None,
    *,
    lock: bool = False,
) -> ColumnElement[bool]:
    if part_id:
        query = select(Part).where(Part.id == part_id)
        part = session.exec(query.with_for_update() if lock else query).first()
        if not part:
            raise HTTPException(404, "Pieza no encontrada.")
        # Check original access on the server, including requests from a folder-only link.
        sources: CompoundSelect[tuple[uuid.UUID | None]] = union(
            *(
                select(model.file_id).where(
                    model.part_id == part_id, model.kind == kind
                )
                for model in (PartFile, PartDocument, PartReference, FeatureAsset)
            )
        )
        originals = session.exec(
            select(StoredFile).where(col(StoredFile.id).in_(sources))
        ).all()
        for original in originals:
            document_check(original)
        if not originals and sharepoint.enabled() and part.folder_path:
            try:
                sharepoint.item(part.folder_path, directory=True)
            except SourceError as error:
                raise HTTPException(error.status_code, error.message) from error
        return col(AttachmentPhoto.part_id) == part_id
    if not file_id:
        raise HTTPException(422, "Selecciona una pieza o un adjunto.")
    file_query = select(StoredFile).where(StoredFile.id == file_id)
    attachment = session.exec(
        file_query.with_for_update() if lock else file_query
    ).first()
    if not attachment:
        raise HTTPException(404, "Adjunto no encontrado.")
    document_check(attachment)
    return col(AttachmentPhoto.file_id) == file_id


def gallery_images(
    session: Session, scope: ColumnElement[bool], kind: GalleryKind
) -> list[StoredFile]:
    return list(
        session.exec(
            select(StoredFile)
            .join(AttachmentPhoto, col(AttachmentPhoto.image_id) == col(StoredFile.id))
            .where(scope, AttachmentPhoto.kind == kind)
            .order_by(col(AttachmentPhoto.position))
        ).all()
    )


@router.get("/attachment-gallery")
def read_attachment_gallery(
    session: SessionDep,
    _current_user: CurrentUser,
    kind: GalleryKind,
    part_id: uuid.UUID | None = None,
    file_id: uuid.UUID | None = None,
) -> list[FilePublic]:
    scope = gallery_scope(session, kind, part_id, file_id)
    return [FilePublic.model_validate(f) for f in gallery_images(session, scope, kind)]


@router.put("/attachment-gallery")
def update_attachment_gallery(
    session: SessionDep,
    _current_user: CurrentUser,
    kind: GalleryKind,
    body: GalleryChange,
    part_id: uuid.UUID | None = None,
    file_id: uuid.UUID | None = None,
) -> list[FilePublic]:
    scope = gallery_scope(session, kind, part_id, file_id, lock=True)
    current = [f.id for f in gallery_images(session, scope, kind)]
    if current not in (body.previous_ids, body.image_ids):
        raise HTTPException(
            409, "La galería ha cambiado. Cancela la edición y vuelve a abrirla."
        )
    images = []
    if len(set(body.image_ids)) != len(body.image_ids):
        raise HTTPException(422, "Hay imágenes repetidas.")
    for image_id in body.image_ids:
        image = session.get(StoredFile, image_id)
        if (
            not image
            or image.source != "upload"
            or image.id == file_id
            or image.content_type.partition(";")[0].strip().lower()
            not in COVER_IMAGE_TYPES
        ):
            raise HTTPException(422, "Selecciona una imagen subida para la galería.")
        images.append(FilePublic.model_validate(image))
    if current != body.image_ids:
        session.execute(
            delete(AttachmentPhoto).where(scope, col(AttachmentPhoto.kind) == kind)
        )
        for position, image_id in enumerate(body.image_ids):
            session.add(
                AttachmentPhoto(
                    part_id=part_id,
                    file_id=None if part_id else file_id,
                    kind=kind,
                    position=position,
                    image_id=image_id,
                )
            )
        session.commit()
    return images
