"""Named piece files, with explicit primary references and retained source history."""

import uuid
from pathlib import PurePosixPath
from typing import cast

from fastapi import HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.evidence import register_document
from app.file_sources import local_path, stamp
from app.knowledge_models import PartDocument, PartFile, PartReference
from app.models import (
    AssetKind,
    FeatureAsset,
    FilePublic,
    Part,
    PartFileInput,
    PartFileKind,
    ReferenceChoice,
    ReferenceKind,
    StoredFile,
)
from app.part_setup import KINDS, reference_choices, references, validate_references


class PartFilePublic(BaseModel):
    kind: PartFileKind
    name: str
    primary: bool
    path: str | None = None
    file: FilePublic


def primary_files(session: Session, part_id: uuid.UUID) -> dict[str, StoredFile]:
    result = references(session, part_id)
    chosen = reference_choices(session, part_id)
    for asset, document in session.exec(
        select(FeatureAsset, StoredFile)
        .join(StoredFile, col(FeatureAsset.file_id) == StoredFile.id)
        .where(FeatureAsset.part_id == part_id)
        .order_by(col(FeatureAsset.position), col(FeatureAsset.id))
    ).all():
        if asset.kind not in chosen:
            result.setdefault(AssetKind(asset.kind).value, document)
    return result


def read_files(session: Session, part: Part) -> list[PartFilePublic]:
    if not part.files_managed:
        return [
            PartFilePublic(
                kind=cast(PartFileKind, kind),
                name=file.filename,
                primary=kind in KINDS,
                path=file.source_path,
                file=FilePublic.model_validate(file),
            )
            for kind, file in primary_files(session, part.id).items()
        ]
    return [
        PartFilePublic(
            kind=cast(PartFileKind, row.kind),
            name=row.name,
            primary=row.primary,
            path=file.source_path,
            file=FilePublic.model_validate(file),
        )
        for row, file in session.exec(
            select(PartFile, StoredFile)
            .join(StoredFile, col(PartFile.file_id) == StoredFile.id)
            .where(PartFile.part_id == part.id)
            .order_by(col(PartFile.position), col(PartFile.file_id))
        ).all()
    ]


def save_files(
    session: Session,
    part: Part,
    choices: list[PartFileInput],
    *,
    folder_path: str | None,
) -> None:
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    existing = {item.file.id for item in read_files(session, part)}
    changed_folder = folder_path != part.folder_path
    root = (
        local_path(folder_path, directory=True)
        if folder_path and (changed_folder or any(c.path for c in choices))
        else None
    )
    resolved: list[tuple[PartFileInput, StoredFile]] = []
    used_ids: set[uuid.UUID] = set()
    used_paths: set[str] = set()
    primary_kinds: set[str] = set()
    for choice in choices:
        choice.name = choice.name.strip()
        if not choice.name:
            raise HTTPException(422, "Escribe un nombre para cada fichero.")
        if choice.primary:
            if choice.kind not in KINDS or choice.kind in primary_kinds:
                raise HTTPException(422, "Elige un único archivo principal por tipo.")
            primary_kinds.add(choice.kind)
        if choice.file_id and choice.path:
            raise HTTPException(422, "Selecciona el fichero guardado o una nueva ruta.")
        if choice.path:
            if root is None or not local_path(choice.path).is_relative_to(root):
                raise HTTPException(
                    422, "Selecciona archivos dentro de la carpeta de la pieza."
                )
            if choice.kind in KINDS:
                validate_references(
                    folder_path or "",
                    [
                        ReferenceChoice(
                            kind=cast(ReferenceKind, choice.kind),
                            path=choice.path,
                            source_version=choice.source_version,
                        )
                    ],
                )
            elif (
                choice.source_version
                and stamp(local_path(choice.path)) != choice.source_version
            ):
                raise HTTPException(
                    409, "El archivo ha cambiado. Selecciónalo de nuevo."
                )
            # Register against the chosen folder, without committing the identity change.
            previous = part.folder_path
            part.folder_path = folder_path
            try:
                file = register_document(
                    session,
                    part,
                    PurePosixPath(choice.path)
                    .relative_to(folder_path or "")
                    .as_posix(),
                )
            finally:
                part.folder_path = previous
        elif choice.file_id and choice.file_id in existing:
            stored = session.get(StoredFile, choice.file_id)
            assert stored is not None
            file = stored
            if changed_folder and (
                not file.source_path
                or root is None
                or not local_path(file.source_path).is_relative_to(root)
            ):
                raise HTTPException(
                    422, "Los archivos deben pertenecer a la nueva carpeta de la pieza."
                )
            # Type changes must keep a compatible format, even for legacy uploaded files.
            extensions = {
                "part": {".step", ".stp", ".igs", ".iges"},
                "scan": {".stl", ".obj", ".ply", ".glb", ".gltf"},
                "drawing": {".pdf"},
                "mold": {
                    ".step",
                    ".stp",
                    ".igs",
                    ".iges",
                    ".stl",
                    ".obj",
                    ".ply",
                    ".glb",
                    ".gltf",
                },
            }
            if (
                choice.kind in extensions
                and PurePosixPath(file.filename).suffix.lower()
                not in extensions[choice.kind]
            ):
                raise HTTPException(
                    422, "El formato no corresponde al tipo de fichero."
                )
        else:
            raise HTTPException(422, "Selecciona un fichero de esta pieza.")
        if file.id in used_ids or (file.source_path and file.source_path in used_paths):
            raise HTTPException(422, "Este fichero ya está añadido a la pieza.")
        used_ids.add(file.id)
        if file.source_path:
            used_paths.add(file.source_path)
        resolved.append((choice, file))

    # Empty choices remain explicit; legacy links must not restore a removed file.
    for row in session.exec(select(PartFile).where(PartFile.part_id == part.id)).all():
        session.delete(row)
    for previous_document in session.exec(
        select(PartDocument).where(PartDocument.part_id == part.id)
    ).all():
        if previous_document.kind.startswith("reference_"):
            previous_document.kind = "source"
            session.add(previous_document)
    session.flush()
    principals: dict[str, StoredFile] = {}
    for position, (choice, file) in enumerate(resolved):
        primary = choice.kind in KINDS and (
            choice.primary
            or (choice.kind not in primary_kinds and choice.kind not in principals)
        )
        session.add(
            PartFile(
                part_id=part.id,
                file_id=file.id,
                kind=choice.kind,
                name=choice.name,
                position=position,
                primary=primary,
            )
        )
        doc = session.get(PartDocument, (part.id, file.id))
        if doc is None:
            doc = PartDocument(part_id=part.id, file_id=file.id)
        if primary:
            principals[choice.kind] = file
            doc.kind = f"reference_{choice.kind}"
        session.add(doc)
    for kind in (*KINDS, "moldflow"):
        selected = session.get(PartReference, (part.id, kind)) or PartReference(
            part_id=part.id, kind=kind
        )
        selected.file_id = principals[kind].id if kind in principals else None
        session.add(selected)
    part.files_managed = True
    if changed_folder:
        part.last_read = None
    part.folder_path = folder_path
    session.add(part)
