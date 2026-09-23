import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app import part_setup
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.parts import commit_part, create_part_from_folder, get_part_or_404
from app.file_sources import SourceError
from app.models import (
    Feature,
    FeatureAsset,
    FeaturePartLink,
    Part,
    PartFileInput,
    PartFromFolder,
    PartPublic,
)
from app.part_setup import (
    FolderDiscovery,
    PartRefreshResult,
    PartSetupRequest,
    PartSetupResult,
)

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("/{part_id}/read-data", response_model=PartRefreshResult | None)
def read_part_data_report(
    session: SessionDep, _current_user: CurrentUser, part_id: uuid.UUID
) -> PartRefreshResult | None:
    from app.part_reading import read_report

    return read_report(session, get_part_or_404(session, part_id))


@router.post("/{part_id}/read-data", response_model=PartRefreshResult)
def read_part_data(
    session: SessionDep, current_user: CurrentUser, part_id: uuid.UUID
) -> PartRefreshResult:
    from app.part_reading import run_read

    return run_read(session, get_part_or_404(session, part_id), current_user.id)


class PartRegistration(BaseModel):
    folder_path: str = Field(min_length=1, max_length=2048)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=64)
    customer: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    files: list[PartFileInput] = Field(default_factory=list, max_length=200)
    feature_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


@router.post("/register", response_model=PartPublic)
def register_part(
    session: SessionDep, _current_user: CurrentUser, body: PartRegistration
) -> PartPublic:
    from app.file_sources import local_path
    from app.part_files import save_files

    try:
        local_path(body.folder_path, directory=True)
        existing = session.exec(
            select(Part).where(Part.folder_path == body.folder_path)
        ).first()
        if existing:
            raise HTTPException(
                409,
                {
                    "message": "Esta carpeta ya pertenece a una pieza.",
                    "part_id": str(existing.id),
                },
            )
        if not all(value.strip() for value in (body.name, body.code, body.customer)):
            raise HTTPException(422, "Completa el título, el código y el cliente.")
        if session.exec(select(Part).where(Part.code == body.code.strip())).first():
            raise HTTPException(409, "Ya existe una pieza con ese código.")
        features = []
        for feature_id in sorted(set(body.feature_ids)):
            feature = session.exec(
                select(Feature).where(Feature.id == feature_id).with_for_update()
            ).first()
            if feature is None:
                raise HTTPException(404, "Uno de los features ya no existe.")
            features.append(feature)
        part = Part(
            name=body.name.strip(),
            code=body.code.strip(),
            customer=body.customer.strip(),
            description=body.description,
            folder_path=body.folder_path,
        )
        session.add(part)
        session.flush()
        save_files(session, part, body.files, folder_path=body.folder_path)
        session.flush()
        for feature in features:
            session.add(FeaturePartLink(feature_id=feature.id, part_id=part.id))
            feature.part_order = [*feature.part_order, str(part.id)]
            session.add(feature)
            for kind, file in part_setup.references(session, part.id).items():
                session.add(
                    FeatureAsset(
                        feature_id=feature.id,
                        part_id=part.id,
                        file_id=file.id,
                        kind=kind,
                        name=file.filename,
                    )
                )
        commit_part(session)
        session.refresh(part)
        return PartPublic.model_validate(part)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message)
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Ya existe una pieza con ese código o carpeta.")


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
