"""Explicit piece registration, proposed reference files and manual data refresh."""

import hashlib
import os
import re
import subprocess
import unicodedata
import uuid
from collections import defaultdict
from pathlib import Path, PurePosixPath

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app import automatic_measurements, measurement_imports, sharepoint
from app.evidence import queue, register_document, study_key
from app.file_sources import (
    SourceError,
    SourceItem,
    inside,
    item_file,
    local_path,
    source_item,
)
from app.knowledge_models import PartDocument, PartReference
from app.measurement_models import (
    MeasurementPreview,
)
from app.models import (
    Feature,
    Part,
    PartPublic,
    ReferenceChoice,
    ReferenceKind,
    StoredFile,
)
from app.pilot import is_pilot
from app.reference_selection import (
    AUXILIARY,
    DRAWING_NAME,
    MOLD_ASSEMBLY,
    conflicting_product_numbers,
    digest_for,
    page_evidence,
)

KINDS: tuple[ReferenceKind, ...] = ("part", "scan", "mold", "drawing")
LABELS = {"part": "CAD", "scan": "Escaneo", "mold": "Molde", "drawing": "Plano"}


class ReferenceCandidate(BaseModel):
    path: str
    source_version: str
    size: int


class ReferenceProposal(ReferenceChoice):
    candidates: list[ReferenceCandidate] = []


class FeatureSuggestion(BaseModel):
    id: uuid.UUID
    name: str


class FolderDiscovery(BaseModel):
    folder_path: str
    name: str
    references: list[ReferenceProposal]
    notices: list[str] = []
    code: str = ""
    existing_part: PartPublic | None = None
    # Features named like a folder above the piece: a proposal the user can remove.
    suggested_features: list[FeatureSuggestion] = []


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
    state: str = "ready"
    files: list["ReadFileReport"] = []
    updated_at: str | None = None
    corrections_key: str | None = None


class ReadFileReport(BaseModel):
    path: str
    group: str
    status: str
    # Set when the entry describes one sheet of the file, not the whole file.
    sheet: str | None = None


def folder_files(folder_path: str) -> list[SourceItem]:
    """Files of a piece folder, as paths from the source root."""
    if sharepoint.enabled():
        too_wide = "Selecciona la carpeta concreta de la pieza."
        try:
            return [
                item
                for item in sharepoint.walk(folder_path, too_wide=too_wide)
                if not item.name.startswith("~$")
            ]
        except SourceError as error:
            if error.message == too_wide:
                raise HTTPException(422, too_wide)
            raise
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
    return [
        SourceItem(
            path="/".join(filter(None, [folder_path, p.relative_to(root).as_posix()])),
            local=p,
        )
        for p in paths
    ]


def reference_kind(relative: str) -> ReferenceKind | None:
    text = relative.casefold()
    path = PurePosixPath(text)
    suffix = path.suffix
    # Metrology geometry, presentations and reports are not reference CAD/drawings.
    # SUPPORT can also be the product name: only exclude support directories.
    if re.search(r"metrolog|retoqu|correction", text) or re.search(
        r"support|suport", path.parent.as_posix()
    ):
        return None
    ballooned = bool(re.search(r"bal{1,2}o{1,2}n{1,2}ed", text))
    if suffix == ".pdf" and ballooned:
        return "drawing"
    if re.search(r"mesura|measurement", text):
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


def reference_choices(session: Session, part_id: uuid.UUID) -> dict[str, PartReference]:
    return {
        choice.kind: choice
        for choice in session.exec(
            select(PartReference).where(PartReference.part_id == part_id)
        ).all()
    }


def references(session: Session, part_id: uuid.UUID) -> dict[str, StoredFile]:
    result = {
        doc.kind.removeprefix("reference_"): file
        for doc, file in session.exec(
            select(PartDocument, StoredFile)
            .join(StoredFile, col(PartDocument.file_id) == StoredFile.id)
            .where(PartDocument.part_id == part_id)
        ).all()
        if doc.kind.startswith("reference_")
    }
    for kind, choice in reference_choices(session, part_id).items():
        result.pop(kind, None)
        if choice.file_id and (file := session.get(StoredFile, choice.file_id)):
            result[kind] = file
    return result


def reference_candidates(
    folder_path: str,
) -> tuple[dict[str, list[ReferenceCandidate]], list[str], set[str]]:
    """Read-only discovery, also used by the offline ingestion check.

    Also returns the folders that hold an infra-CONVERT project (`.icp`).
    """
    candidates: dict[str, list[ReferenceCandidate]] = defaultdict(list)
    notices: list[str] = []
    files = folder_files(folder_path)
    icp_folders = {
        PurePosixPath(item.path).parent.as_posix()
        for item in files
        if item.suffix == ".icp"
    }
    extra_pdfs: list[ReferenceCandidate] = []
    for item in files:
        kind = reference_kind(item.relative_to(folder_path))
        inspect_pdf = (
            not kind
            and item.suffix == ".pdf"
            and DRAWING_NAME.search(PurePosixPath(item.name).stem)
        )
        if not kind and not inspect_pdf:
            continue
        relative = f"{folder_path}/{item.relative_to(folder_path)}"
        try:
            # Local walks are validated per candidate, as when linking them.
            checked = item if item.version is not None else source_item(relative)
            target = candidates[kind] if kind else extra_pdfs
            target.append(
                ReferenceCandidate(
                    path=relative,
                    source_version=checked.version or "",
                    size=checked.size or 0,
                )
            )
        except SourceError:
            notices.append(f"No se puede vincular todavía: {relative}.")
    # Only inspect newly discovered PDFs. A byte-identical document already classified
    # as a drawing or a drawing identifier on its technical page corroborates the name.
    recognized = list(candidates.get("drawing", []))
    for pdf in extra_pdfs:
        try:
            same_size = [other for other in recognized if other.size == pdf.size]
            name = PurePosixPath(pdf.path).name
            peers = [
                c
                for c in recognized
                if PurePosixPath(c.path).name.casefold() == name.casefold()
                and c.size <= 32 * 1024 * 1024
            ]
            local = (
                item_file(source_item(pdf.path))
                if pdf.size <= 32 * 1024 * 1024
                else None
            )
            if local and (
                any(
                    digest_for(pdf.path, pdf.source_version)
                    == digest_for(other.path, other.source_version)
                    for other in same_size
                )
                or page_evidence(local, pdf.source_version, PurePosixPath(name).stem)
                is True
                or (
                    peers
                    and (visible := page_evidence(local, pdf.source_version))
                    and any(
                        visible
                        == page_evidence(
                            item_file(source_item(c.path)), c.source_version
                        )
                        for c in peers
                    )
                )
            ):
                candidates["drawing"].append(pdf)
                continue
        except (OSError, SourceError, subprocess.TimeoutExpired):
            pass
        notices.append(f"Revisa si este PDF es un plano: {pdf.path}.")
    for choices in candidates.values():
        choices.sort(key=lambda item: item.path.casefold())
    return candidates, notices, icp_folders


def proposed_reference(
    kind: str,
    choices: list[ReferenceCandidate],
    icp_folders: set[str],
    *,
    folder_path: str,
    part_choices: list[ReferenceCandidate],
) -> ReferenceCandidate | None:
    """Only a coherent single scope can receive a star. Order is for display."""
    if (
        kind == "part"
        and len(choices) == 1
        and re.search(
            r"(?:^|[^a-z0-9])(?:electrodes?|electrodos?|tool[ _-]*mark|core|utillaje)(?:$|[^a-z0-9])",
            PurePosixPath(choices[0].path).relative_to(folder_path).as_posix(),
            re.I,
        )
    ):
        return None
    if kind == "mold":
        eligible = [
            c
            for c in choices
            if not AUXILIARY.search(
                PurePosixPath(c.path).relative_to(folder_path).as_posix()
            )
        ]
        if len(choices) > 1:
            eligible = [
                c for c in eligible if MOLD_ASSEMBLY.search(PurePosixPath(c.path).stem)
            ]
        choices = eligible
    if kind == "scan":
        code = re.match(r"^(\d{4})(?:\D|$)", PurePosixPath(folder_path).name)
        if code:
            choices = [
                c
                for c in choices
                if not (
                    (
                        marked := re.match(
                            r"^(\d{4})-\d{2}\b", PurePosixPath(c.path).stem
                        )
                    )
                    and marked[1] != code[1]
                )
            ]
    if kind == "drawing" and choices:
        if len(choices) > 1:
            beside = [
                c
                for c in choices
                if PurePosixPath(c.path).parent.as_posix() in icp_folders
            ]
            if (
                len(beside) != 1
                or len({c.size for c in choices}) != 1
                or choices[0].size > 32 * 1024 * 1024
            ):
                return None
            try:
                if len({digest_for(c.path, c.source_version) for c in choices}) != 1:
                    return None
            except (OSError, SourceError):
                return None
            choices = beside
        name = PurePosixPath(choices[0].path).stem
        if re.search(r"draft|pendent accept|pending approval|borrador", name, re.I):
            return None
        if len(part_choices) == 1:
            if conflicting_product_numbers(
                PurePosixPath(part_choices[0].path).stem, name
            ):
                return None
    return choices[0] if len(choices) == 1 else None


def discover(session: Session, folder_path: str) -> FolderDiscovery:
    from app.part_files import primary_files

    if not folder_path:
        raise HTTPException(
            422, "Selecciona la carpeta de una pieza dentro del origen."
        )
    root = source_item(folder_path, directory=True)
    candidates, notices, icp_folders = reference_candidates(folder_path)
    part = session.exec(select(Part).where(Part.folder_path == folder_path)).first()
    current = primary_files(session, part.id) if part else {}
    chosen = reference_choices(session, part.id) if part else {}
    proposals = []
    for kind in KINDS:
        choices = sorted(candidates[kind], key=lambda item: item.path.casefold())
        existing = current.get(kind)
        selected = (
            proposed_reference(
                kind,
                choices,
                icp_folders,
                folder_path=folder_path,
                part_choices=candidates["part"],
            )
            if kind not in chosen and not existing
            else None
        )
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
        if choices and not selected and not existing and kind not in chosen:
            notices.append(
                f"{LABELS[kind]} sin principal verificable. Puedes elegirlo en la ficha."
            )
    return FolderDiscovery(
        folder_path=folder_path,
        name=(part.name if part else None)
        or (root.local.name if root.local else root.name),
        references=proposals,
        notices=notices,
        code=part.code if part else proposed_code(folder_path),
        existing_part=PartPublic.model_validate(part) if part else None,
        suggested_features=suggested_features(session, folder_path),
    )


# Organisational order in front of a folder name: «0- Bolt Eye», «1. Clips en Piezas».
ORDER_PREFIX = re.compile(r"^\d+\s*[-–.]\s*")


def feature_key(name: str) -> str:
    """Same name ignoring case, accents and separators; nothing else is equated."""
    folded = "".join(
        char
        for char in unicodedata.normalize("NFKD", name.casefold())
        if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def suggested_features(session: Session, folder_path: str) -> list[FeatureSuggestion]:
    """Catalogue features named exactly like a folder above the piece, once each.

    Every folder between the source root and the piece counts, without its order
    prefix («0- Bolt Eye/3212», «1- Clips en Piezas/Tipo A/3174»). A name shared by two
    features of the catalogue suggests neither. No piece is linked until it is created
    with the user's own selection.
    """
    folders = PurePosixPath(folder_path).parts[:-1]
    if not folders:
        return []
    by_key: dict[str, list[Feature]] = defaultdict(list)
    for feature in session.exec(select(Feature)).all():
        by_key[feature_key(feature.name)].append(feature)
    found: list[Feature] = []
    for folder in folders:
        matches = by_key.get(feature_key(ORDER_PREFIX.sub("", folder)), [])
        if len(matches) == 1 and matches[0] not in found:
            found.append(matches[0])
    return [FeatureSuggestion(id=feature.id, name=feature.name) for feature in found]


def proposed_code(folder_path: str) -> str:
    prefix = re.match(r"^(\d{1,64})(?:[\s_-]|$)", PurePosixPath(folder_path).name)
    return (
        prefix[1]
        if prefix
        else f"PIEZA-{hashlib.sha256(folder_path.encode()).hexdigest()[:12]}"
    )


def validate_references(folder_path: str, choices: list[ReferenceChoice]) -> None:
    root = (
        source_item(folder_path, directory=True)
        if any(c.path for c in choices)
        else None
    )
    if len({choice.kind for choice in choices}) != len(choices):
        raise HTTPException(422, "Cada tipo de archivo debe aparecer una sola vez.")
    paths = [choice.path for choice in choices if choice.path]
    if len(set(paths)) != len(paths):
        raise HTTPException(422, "Selecciona un archivo distinto para cada tipo.")
    for choice in choices:
        if not choice.path:
            continue
        item = source_item(choice.path)
        if root is None or not inside(choice.path, folder_path):
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
        suffix = (item.local or PurePosixPath(item.path)).suffix.lower()
        if suffix not in allowed[choice.kind]:
            raise HTTPException(
                422, f"El formato no corresponde a {LABELS[choice.kind]}."
            )
        # SharePoint always uses the latest version: a newer one is not an error.
        if (
            choice.source_version
            and not sharepoint.enabled()
            and item.version != choice.source_version
        ):
            raise HTTPException(409, "Un archivo ha cambiado. Selecciónalo de nuevo.")


def save_references(
    session: Session,
    part: Part,
    choices: list[ReferenceChoice],
    *,
    remember_choices: bool = False,
) -> None:
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    session.refresh(part)
    if part.files_managed:
        # Keep older clients consistent with the named file list. A legacy choice
        # replaces its primary file and retains any additional files of that type.
        from app.models import PartFileInput
        from app.part_files import read_files, save_files

        changed_kinds = {choice.kind for choice in choices}
        retained = [
            PartFileInput(
                file_id=item.file.id,
                kind=item.kind,
                name=item.name,
                primary=item.primary,
            )
            for item in read_files(session, part)
            if not (item.primary and item.kind in changed_kinds)
        ]
        retained.extend(
            PartFileInput(
                path=choice.path,
                source_version=choice.source_version,
                kind=choice.kind,
                name=PurePosixPath(choice.path).name,
                primary=True,
            )
            for choice in choices
            if choice.path
        )
        save_files(session, part, retained, folder_path=part.folder_path, promote=False)
        return
    if not part.folder_path and any(choice.path for choice in choices):
        raise HTTPException(422, "Vincula primero la carpeta de esta pieza.")
    validate_references(part.folder_path or "", choices)
    changed = {choice.kind for choice in choices}
    current = references(session, part.id)
    paths = {file.source_path for kind, file in current.items() if kind not in changed}
    if any(choice.path and choice.path in paths for choice in choices):
        raise HTTPException(422, "Selecciona un archivo distinto para cada tipo.")
    for choice in choices:
        selected = session.get(PartReference, (part.id, choice.kind))
        if selected is None and remember_choices:
            selected = PartReference(part_id=part.id, kind=choice.kind)
        if selected is not None:
            selected.file_id = None
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
            if selected is not None:
                selected.file_id = file.id
        if selected is not None:
            session.add(selected)


def refresh(session: Session, part: Part, user_id: uuid.UUID) -> PartRefreshResult:
    from app.previews import queue_part_previews

    paths = folder_files(part.folder_path or "")
    used_files: dict[str, str] = {}
    added, skipped = automatic_measurements.refresh(
        session, part, user_id, paths, used_files=used_files
    )
    read_files = []
    for key, status in sorted(used_files.items()):
        path, sheet = automatic_measurements.split_sheet_key(key)
        read_files.append(
            ReadFileReport(path=path, group="measurements", status=status, sheet=sheet)
        )
    preview = MeasurementPreview(
        context_key=measurement_imports.context_key(part), files=[]
    )
    notices: list[str] = []
    corrections_state = "empty"
    corrections_key = None
    correction_files = [
        item
        for item in paths
        if item.suffix in {".pptx", ".xls", ".xlsx", ".pdf"}
        and re.search(r"retoqu|correction", item.path, re.I)
    ]
    if is_pilot(part):
        from app.ingestion.pilot_3212.config import CORRECTIONS

        folder = part.folder_path or ""
        present = {item.relative_to(folder) for item in paths}
        required = [c[key] for c in CORRECTIONS.values() for key in ("xls", "pptx")]
        if all(path in present for path in required):
            key = study_key(part)
            corrections_key = key
            corrections_state = queue(
                session, "study", part.id, key, requested_by=user_id
            ).state
            read_files.extend(
                ReadFileReport(
                    path=path,
                    group="corrections",
                    status="used"
                    if corrections_state == "ready"
                    else corrections_state,
                )
                for path in required
            )
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
    queue_part_previews(session, part, user_id)
    return PartRefreshResult(
        imported=added,
        skipped=skipped,
        measurements=preview,
        corrections_state=corrections_state,
        notices=notices,
        files=read_files,
        state="processing"
        if corrections_state in {"queued", "processing"}
        else "partial"
        if corrections_state in {"needs_review", "error"}
        or any(status.startswith("Pendiente:") for status in used_files.values())
        else "ready",
        corrections_key=corrections_key,
    )
