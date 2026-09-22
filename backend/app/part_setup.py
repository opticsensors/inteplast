"""Explicit piece registration, proposed reference files and manual data refresh."""

import os
import re
import uuid
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app import automatic_measurements, measurement_imports
from app.evidence import queue, register_document, study_key
from app.file_sources import SourceError, local_path, stamp
from app.knowledge_models import PartDocument
from app.measurement_models import (
    MeasurementPreview,
)
from app.models import Part, PartPublic, StoredFile

ReferenceKind = Literal["part", "scan", "mold", "drawing"]
KINDS: tuple[ReferenceKind, ...] = ("part", "scan", "mold", "drawing")
LABELS = {"part": "CAD", "scan": "Escaneo", "mold": "Molde", "drawing": "Plano"}


class ReferenceChoice(BaseModel):
    kind: ReferenceKind
    path: str | None = Field(default=None, max_length=2048)
    source_version: str | None = None


class ReferenceCandidate(BaseModel):
    path: str
    source_version: str
    size: int


class ReferenceProposal(ReferenceChoice):
    candidates: list[ReferenceCandidate] = []


class FolderDiscovery(BaseModel):
    folder_path: str
    name: str
    references: list[ReferenceProposal]
    notices: list[str] = []


class PartSetupRequest(BaseModel):
    folder_path: str = Field(min_length=1, max_length=2048)
    name: str = Field(min_length=1, max_length=255)
    references: list[ReferenceChoice] = Field(max_length=4)


class PartSetupResult(BaseModel):
    part: PartPublic


class PartRefreshResult(BaseModel):
    imported: int = 0
    skipped: int = 0
    measurements: MeasurementPreview
    corrections_state: str = "empty"
    notices: list[str] = []


def folder_files(folder_path: str) -> list[Path]:
    root = local_path(folder_path, directory=True)
    paths: list[Path] = []
    visited = 0
    for directory, folders, filenames in os.walk(root, followlinks=False):
        folders[:] = [
            name
            for name in folders
            if not name.startswith(".") and not Path(directory, name).is_symlink()
        ]
        visited += len(folders) + len(filenames)
        if visited > 20000:
            raise HTTPException(422, "Selecciona la carpeta concreta de la pieza.")
        paths.extend(
            Path(directory, name)
            for name in filenames
            if not name.startswith((".", "~$"))
            and not Path(directory, name).is_symlink()
        )
    return paths


def reference_kind(relative: str) -> ReferenceKind | None:
    text = relative.casefold()
    suffix = PurePosixPath(text).suffix
    # Metrology geometry, presentations and reports are not reference CAD/drawings.
    if re.search(r"metrolog|retoqu|correction|mesura|measurement|support|suport", text):
        return None
    if suffix in {".stl", ".ply", ".obj", ".glb", ".gltf"}:
        return "mold" if re.search(r"molde|mould|mold(?!flow)", text) else "scan"
    if suffix in {".stp", ".step", ".igs", ".iges"}:
        if re.search(r"molde|mould|mold(?!flow)|cela.forma", text):
            return "mold"
        if re.search(r"pieza|peça|part|cad|housing|pot", text):
            return "part"
    if suffix == ".pdf" and re.search(r"drw|drawing|plano|2d", text):
        return "drawing"
    return None


def references(session: Session, part_id: uuid.UUID) -> dict[str, StoredFile]:
    return {
        doc.kind.removeprefix("reference_"): file
        for doc, file in session.exec(
            select(PartDocument, StoredFile)
            .join(StoredFile, col(PartDocument.file_id) == StoredFile.id)
            .where(PartDocument.part_id == part_id)
        ).all()
        if doc.kind.startswith("reference_")
    }


def discover(session: Session, folder_path: str) -> FolderDiscovery:
    if not folder_path:
        raise HTTPException(
            422, "Selecciona la carpeta de una pieza dentro del origen."
        )
    root = local_path(folder_path, directory=True)
    candidates: dict[str, list[ReferenceCandidate]] = defaultdict(list)
    notices = []
    for path in folder_files(folder_path):
        kind = reference_kind(path.relative_to(root).as_posix())
        if not kind:
            continue
        relative = f"{folder_path}/{path.relative_to(root).as_posix()}"
        try:
            checked = local_path(relative)
            candidates[kind].append(
                ReferenceCandidate(
                    path=relative,
                    source_version=stamp(checked),
                    size=checked.stat().st_size,
                )
            )
        except SourceError:
            notices.append(f"No se puede vincular todavía: {relative}.")
    part = session.exec(select(Part).where(Part.folder_path == folder_path)).first()
    current = references(session, part.id) if part else {}
    proposals = []
    for kind in KINDS:
        choices = sorted(candidates[kind], key=lambda item: item.path.casefold())
        existing = current.get(kind)
        # A deterministic first approximation, explicitly reviewed before saving.
        selected = choices[0] if choices else None
        proposals.append(
            ReferenceProposal(
                kind=kind,
                path=existing.source_path
                if existing
                else selected.path
                if selected
                else None,
                source_version=existing.source_version
                if existing
                else selected.source_version
                if selected
                else None,
                candidates=choices,
            )
        )
        if len(choices) > 1 and not existing:
            notices.append(
                f"Hay varios archivos para {LABELS[kind]}. Revisa la propuesta."
            )
    return FolderDiscovery(
        folder_path=folder_path,
        name=(part.name if part else None) or root.name,
        references=proposals,
        notices=notices,
    )


def validate_references(folder_path: str, choices: list[ReferenceChoice]) -> None:
    root = local_path(folder_path, directory=True)
    if len({choice.kind for choice in choices}) != len(choices):
        raise HTTPException(422, "Cada tipo de archivo debe aparecer una sola vez.")
    paths = [choice.path for choice in choices if choice.path]
    if len(set(paths)) != len(paths):
        raise HTTPException(422, "Selecciona un archivo distinto para cada tipo.")
    for choice in choices:
        if not choice.path:
            continue
        path = local_path(choice.path)
        if not path.is_relative_to(root):
            raise HTTPException(
                422, "Los archivos deben estar dentro de la carpeta de la pieza."
            )
        allowed = {
            "drawing": {".pdf"},
            "part": {".stp", ".step", ".igs", ".iges"},
            "mold": {
                ".stp",
                ".step",
                ".igs",
                ".iges",
                ".stl",
                ".glb",
                ".obj",
                ".ply",
                ".gltf",
            },
            "scan": {".stl", ".ply", ".obj", ".glb", ".gltf"},
        }
        if path.suffix.lower() not in allowed[choice.kind]:
            raise HTTPException(
                422, f"El formato no corresponde a {LABELS[choice.kind]}."
            )
        if choice.source_version and stamp(path) != choice.source_version:
            raise HTTPException(409, "Un archivo ha cambiado. Selecciónalo de nuevo.")


def save_references(
    session: Session, part: Part, choices: list[ReferenceChoice]
) -> None:
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    session.refresh(part)
    validate_references(part.folder_path or "", choices)
    for choice in choices:
        for doc in session.exec(
            select(PartDocument).where(
                PartDocument.part_id == part.id,
                PartDocument.kind == f"reference_{choice.kind}",
            )
        ).all():
            doc.kind = "source"  # Keep historical evidence attached to the piece.
            session.add(doc)
        session.flush()
        if choice.path:
            relative = (
                PurePosixPath(choice.path)
                .relative_to(part.folder_path or "")
                .as_posix()
            )
            file = register_document(session, part, relative)
            session.flush()
            document = session.get(PartDocument, (part.id, file.id))
            assert document is not None
            document.kind = f"reference_{choice.kind}"
            session.add(document)


def refresh(session: Session, part: Part, user_id: uuid.UUID) -> PartRefreshResult:
    paths = folder_files(part.folder_path or "")
    added, skipped = automatic_measurements.refresh(session, part, user_id, paths)
    preview = MeasurementPreview(
        context_key=measurement_imports.context_key(part), files=[]
    )
    notices: list[str] = []
    corrections_state = "empty"
    correction_files = [
        p
        for p in paths
        if p.suffix.lower() in {".pptx", ".xls", ".xlsx", ".pdf"}
        and re.search(r"retoqu|correction", p.as_posix(), re.I)
    ]
    if part.code == "3212" and part.folder_path == "3212 Pump Housing":
        from app.ingestion.pilot_3212.config import CORRECTIONS

        root = local_path(part.folder_path, directory=True)
        required = [
            root / c[key] for c in CORRECTIONS.values() for key in ("xls", "pptx")
        ]
        if all(path.is_file() for path in required):
            key = study_key(part)
            corrections_state = queue(
                session, "study", part.id, key, requested_by=user_id
            ).state
        elif correction_files:
            corrections_state = "needs_review"
            notices.append("Faltan documentos del estudio de correcciones del 3212.")
    elif correction_files:
        corrections_state = "needs_review"
        notices.append(
            f"Detectados {len(correction_files)} documentos de correcciones. Esta pieza aún necesita configurar su interpretación."
        )
    if not correction_files:
        notices.append("No se han encontrado documentos de correcciones.")
    return PartRefreshResult(
        imported=added,
        skipped=skipped,
        measurements=preview,
        corrections_state=corrections_state,
        notices=notices,
    )
