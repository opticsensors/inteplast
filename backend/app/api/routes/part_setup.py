import uuid

from fastapi import APIRouter, HTTPException

from app import part_setup
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import create_part_from_folder, get_part_or_404
from app.file_sources import SourceError
from app.models import PartFromFolder, PartPublic
from app.part_setup import (
    FolderDiscovery,
    PartRefreshResult,
    PartSetupRequest,
    PartSetupResult,
)

router = APIRouter(prefix="/parts", tags=["parts"])


@router.post("/discover", response_model=FolderDiscovery)
def discover_part_folder(
    session: SessionDep,
    _current_user: CurrentUser,
    body: PartFromFolder,
) -> FolderDiscovery:
    try:
        return part_setup.discover(session, body.folder_path)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)


@router.post("/setup", response_model=PartSetupResult)
def setup_part(
    session: SessionDep,
    current_user: CurrentUser,
    body: PartSetupRequest,
) -> PartSetupResult:
    try:
        part_setup.validate_references(body.folder_path, body.references)
        public = create_part_from_folder(
            session=session,
            _current_user=current_user,
            part_in=PartFromFolder(folder_path=body.folder_path),
        )
        part = get_part_or_404(session, public.id)
        part_setup.save_references(session, part, body.references)
        part.name = body.name.strip()
        if not part.name:
            raise HTTPException(422, "Escribe el nombre de la pieza.")
        session.add(part)
        session.commit()
        session.refresh(part)
        return PartSetupResult(part=PartPublic.model_validate(part))
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)


@router.post("/{part_id}/refresh", response_model=PartRefreshResult)
def refresh_part_data(
    session: SessionDep,
    current_user: CurrentUser,
    part_id: uuid.UUID,
) -> PartRefreshResult:
    try:
        return part_setup.refresh(
            session, get_part_or_404(session, part_id), current_user.id
        )
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)
