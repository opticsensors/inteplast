"""Optional organization for assemblies; source files are never modified."""

import logging
import re
import uuid
from pathlib import PurePosixPath
from typing import cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import get_part_or_404
from app.automatic_measurements import measurement_skip_reason
from app.component_models import ComponentDefinition, ComponentOrganization
from app.evidence import register_document
from app.file_sources import (
    SourceError,
    SourceItem,
    inside,
    item_file,
    source_item,
    with_metadata,
)
from app.knowledge_models import PartCharacteristic
from app.measurement_models import MeasurementImport
from app.models import Part, PartFileInput, PartFileKind
from app.part_files import read_files, save_files
from app.part_setup import discover, folder_files

router = APIRouter(prefix="/parts", tags=["parts"])
logger = logging.getLogger(__name__)

# Sheet names per workbook version: the dialog reopens often, the files rarely change.
_SHEETS: dict[tuple[str, str], list[str]] = {}


def examined_sheets(item: SourceItem) -> list[str]:
    """Sheet names of a workbook, read from its index without importing measurements.

    An unreadable workbook has no sheets to offer; the import reports it on its own.
    """
    try:
        item = with_metadata(item)
        key = (item.path, item.version or "")
        if key not in _SHEETS:
            from python_calamine import CalamineWorkbook

            with CalamineWorkbook.from_path(str(item_file(item))) as book:
                names = list(book.sheet_names)
            if len(_SHEETS) > 2048:
                _SHEETS.clear()
            _SHEETS[key] = names
        return list(_SHEETS[key])
    except Exception:  # noqa: BLE001 - any reader failure means "no sheets offered"
        logger.info("Sheet names not available: %s", item.path, exc_info=True)
        return []


class ComponentSource(BaseModel):
    path: str
    kind: str


class WorkbookSheets(BaseModel):
    path: str
    sheets: list[str] = []


class ComponentOptions(ComponentOrganization):
    sources: list[ComponentSource] = []
    sheet_names: list[str] = []
    # Sheets of each measurement workbook, examined without importing anything.
    workbooks: list[WorkbookSheets] = []
    suggestions: list[ComponentDefinition] = []
    unassigned_characteristics: int = 0


@router.get("/{part_id}/components", response_model=ComponentOptions)
def read_component_options(
    session: SessionDep, _current_user: CurrentUser, part_id: uuid.UUID
) -> ComponentOptions:
    part = get_part_or_404(session, part_id)
    sources: dict[str, str] = {}
    sheet_names = set()
    workbooks: list[WorkbookSheets] = []
    if part.folder_path:
        proposal = discover(session, part.folder_path)
        for reference in proposal.references:
            for candidate in reference.candidates:
                relative = (
                    PurePosixPath(candidate.path)
                    .relative_to(part.folder_path)
                    .as_posix()
                )
                sources[relative] = reference.kind
        for item in folder_files(part.folder_path):
            if item.suffix in {".csv", ".xls", ".xlsx", ".xlsm"}:
                relative = item.relative_to(part.folder_path)
                sources.setdefault(relative, "measurements")
                if item.suffix != ".csv" and measurement_skip_reason(relative) is None:
                    names = examined_sheets(item)
                    workbooks.append(WorkbookSheets(path=relative, sheets=names))
                    sheet_names.update(names)
    for entry in (part.last_read or {}).get("files", []):
        if entry.get("sheet"):
            sheet_names.add(entry["sheet"])
    for component in part.components:
        sheet_names.update(component.get("sheets", []))
    # Reuse provenance already imported, without opening large workbooks in this UI.
    for batch in session.exec(
        select(MeasurementImport)
        .where(MeasurementImport.part_id == part.id)
        .order_by(col(MeasurementImport.imported_at).desc())
        .limit(24)
    ).all():
        for row in batch.rows:
            source = row.get("source", {})
            if "!" in source.get("locator", ""):
                sheet_names.add(source["locator"].split("!")[0])
    proposed: dict[str, ComponentDefinition] = {}
    for sheet in sorted(sheet_names):
        match = re.match(r"DR\(([^)]+)\)", sheet, re.I)
        if match and re.fullmatch(r"[a-z][a-z0-9_-]{0,23}", match[1], re.I):
            key = match[1].upper()
            proposed.setdefault(
                key, ComponentDefinition(key=key, name=key)
            ).sheets.append(sheet)
    return ComponentOptions(
        components=[ComponentDefinition.model_validate(c) for c in part.components],
        unassigned=list(part.component_unassigned or []),
        sources=[ComponentSource(path=p, kind=k) for p, k in sorted(sources.items())],
        sheet_names=sorted(sheet_names),
        workbooks=workbooks,
        suggestions=list(proposed.values()),
        unassigned_characteristics=len(
            session.exec(
                select(PartCharacteristic).where(
                    PartCharacteristic.part_id == part.id,
                    PartCharacteristic.component == "",
                )
            ).all()
        ),
    )


@router.put("/{part_id}/components", response_model=ComponentOrganization)
def save_component_organization(
    session: SessionDep,
    _current_user: CurrentUser,
    part_id: uuid.UUID,
    body: ComponentOrganization,
) -> ComponentOrganization:
    part = get_part_or_404(session, part_id)
    session.exec(select(Part).where(Part.id == part.id).with_for_update()).one()
    if not part.folder_path:
        raise HTTPException(422, "Selecciona primero la carpeta de la pieza.")
    used = {
        c.component
        for c in session.exec(
            select(PartCharacteristic).where(PartCharacteristic.part_id == part.id)
        ).all()
        if c.component
    }
    if not used <= {c.key for c in body.components}:
        raise HTTPException(
            409,
            "Conserva las claves de los componentes que ya tienen cotas. Puedes cambiar su nombre.",
        )
    # Existing history and feature links retain their identity. Source reassignment after
    # importing needs a migration, not an implicit rewrite of those identities.
    new = {c.key: c.model_dump() for c in body.components}
    for old in part.components:
        if old["key"] in used:
            before = set(old.get("sheets", []))
            after = set(new[old["key"]]["sheets"])
            old_files = {
                f["path"]
                for f in old.get("files", [])
                if not f["path"]
                .lower()
                .endswith((".pdf", ".step", ".stp", ".stl", ".obj", ".ply"))
            }
            new_files = {f["path"] for f in new[old["key"]]["files"]}
            if not before <= after or not old_files <= new_files:
                raise HTTPException(
                    409,
                    "Esta hoja ya tiene medidas importadas. Su reasignación requiere revisar la procedencia.",
                )
    choices = [
        PartFileInput(file_id=f.file.id, kind=f.kind, name=f.name, primary=f.primary)
        for f in read_files(session, part)
    ]
    known_paths = {f.path for f in read_files(session, part)}
    for component in body.components:
        for assignment in component.files:
            path = PurePosixPath(assignment.path)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in assignment.path
                or ":" in assignment.path
            ):
                raise HTTPException(
                    422, "Usa rutas relativas dentro de la carpeta de la pieza."
                )
            full = f"{part.folder_path}/{path.as_posix()}"
            if not inside(full, part.folder_path):
                raise HTTPException(422, "El archivo debe pertenecer a la pieza.")
            try:
                source_item(full)
            except SourceError as error:
                raise HTTPException(error.status_code, error.message) from error
            suffix = path.suffix.lower()
            kind = (
                "drawing"
                if suffix == ".pdf"
                else "part"
                if suffix in {".step", ".stp"}
                else "scan"
                if suffix in {".stl", ".obj", ".ply"}
                else None
            )
            if kind and full not in known_paths:
                choices.append(
                    PartFileInput(
                        path=full, kind=cast(PartFileKind, kind), name=path.name
                    )
                )
                known_paths.add(full)
            elif not kind:
                register_document(session, part, path.as_posix())
    # Assigning a drawing to a component does not make it the piece's principal.
    save_files(session, part, choices, folder_path=part.folder_path, promote=False)
    part.components = [c.model_dump() for c in body.components]
    assigned = {f"file:{f.path}" for c in body.components for f in c.files} | {
        f"sheet:{s}" for c in body.components for s in c.sheets
    }
    # Without components there is nothing to propose and nothing to remember.
    part.component_unassigned = (
        sorted(set(body.unassigned) - assigned) if body.components else []
    )
    part.last_read = None
    session.add(part)
    session.commit()
    return body
