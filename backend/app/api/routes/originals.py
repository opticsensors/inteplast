"""Check and select the SharePoint folder backing the existing catalogue."""

import base64
import uuid
from datetime import timedelta
from typing import Annotated, Any
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

from app import sharepoint as sp
from app.api.deps import SessionDep, get_current_active_superuser
from app.core.config import settings
from app.core.security import ALGORITHM
from app.microsoft_models import MicrosoftAccount, SharePointFolder
from app.models import Part, User, get_datetime_utc
from app.source_types import SourceError

router = APIRouter(prefix="/admin/originals", tags=["originals"])
Admin = Annotated[User, Depends(get_current_active_superuser)]
FIELDS = "id,name,folder,webUrl,parentReference,sharepointIds,remoteItem"


class FolderLink(BaseModel):
    url: str = Field(min_length=1, max_length=8192)


class FolderInfo(BaseModel):
    name: str
    web_url: str | None
    per_user: bool = False


class FolderCheck(BaseModel):
    folder: FolderInfo
    total: int
    checked: int
    found: int
    unavailable: list[str]
    ticket: str


class FolderChoice(BaseModel):
    ticket: str = Field(min_length=1, max_length=8192)


def sharing_url(raw: str) -> str:
    """Accept both Copy link and the address bar of SharePoint's folder views."""
    try:
        url = urlsplit(raw.strip())
        host = url.hostname or ""
        valid = (
            url.scheme == "https"
            and host.endswith(".sharepoint.com")
            and url.username is None
            and url.password is None
            and url.port in (None, 443)
        )
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(
            422,
            "Introduce un enlace HTTPS de una carpeta de SharePoint o OneDrive de empresa.",
        )
    query = parse_qs(url.query)
    for key in ("id", "RootFolder"):
        path = next(iter(query.get(key, [])), "")
        if path.startswith("/") and not path.startswith("//"):
            return urlunsplit(("https", host, quote(path, safe="/"), "", ""))
    return urlunsplit(("https", host, url.path, url.query, ""))


def folder_details(data: dict[str, Any], account: MicrosoftAccount) -> SharePointFolder:
    item = data.get("remoteItem") or data
    if "folder" not in item:
        raise HTTPException(
            422,
            "El enlace apunta a un archivo. Selecciona la carpeta de los originales.",
        )
    if (
        str(item.get("sharepointIds", {}).get("tenantId", "")).lower()
        != account.tenant_id.lower()
    ):
        raise HTTPException(
            422,
            "La carpeta debe pertenecer a la organización Microsoft autorizada para esta aplicación.",
        )
    drive = item.get("parentReference", {}).get("driveId")
    if not drive or not item.get("id") or not item.get("webUrl"):
        raise HTTPException(422, "Microsoft no ha devuelto una carpeta identificable.")
    return SharePointFolder(
        source_id=settings.ASSETS_SOURCE_ID,
        drive_id=drive,
        item_id=item["id"],
        name=item["name"],
        web_url=item["webUrl"],
    )


def microsoft_account(session: SessionDep, admin: User) -> MicrosoftAccount:
    if not sp.enabled():
        raise HTTPException(
            409, "La conexión a SharePoint está desactivada en este servidor."
        )
    account = session.get(MicrosoftAccount, admin.id)
    if account is None:
        raise HTTPException(
            409, "Inicia sesión con Microsoft para comprobar una carpeta."
        )
    return account


def graph(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return sp.request(url, params)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message) from error


def check_folder_read(folder: SharePointFolder) -> None:
    graph(
        sp.folder_item_url(folder.drive_id, folder.item_id) + "/children",
        {"$top": 1, "$select": "id"},
    )


def catalog_part_folders(session: SessionDep) -> list[str]:
    paths = session.exec(
        select(Part.folder_path)
        .where(col(Part.folder_path).is_not(None))
        .order_by(Part.folder_path)
    )
    return [path for path in paths if path]


def sample_part_folders(paths: list[str]) -> list[str]:
    """Prefer one registered piece per top-level feature folder."""
    by_feature: dict[str, str] = {}
    for path in paths:
        by_feature.setdefault(path.partition("/")[0].casefold(), path)
        if len(by_feature) == 3:
            return list(by_feature.values())
    first = list(by_feature.values())
    return (first + [path for path in paths if path not in first])[:3]


def unavailable_part_folders(folder: SharePointFolder, paths: list[str]) -> list[str]:
    missing = []
    for path in paths:
        url = sp.folder_item_url(folder.drive_id, folder.item_id, path)
        try:
            item = sp.request(url, {"$select": "folder"})
        except SourceError as error:
            if error.status_code not in (403, 404, 409):
                raise
            item = {}
        if item.get("folder") is None:
            missing.append(path)
    return missing


def info(folder: SharePointFolder) -> FolderInfo:
    return FolderInfo(name=folder.name, web_url=folder.web_url)


@router.get("")
def read_originals(session: SessionDep, admin: Admin) -> FolderInfo:
    active = sp.configured_folder(session)
    if active:
        return info(active)
    current = FolderInfo(
        name=settings.SHAREPOINT_ROOT_PATH or settings.ASSETS_SOURCE_NAME,
        web_url=None,
        per_user=not bool(settings.SHAREPOINT_DRIVE_ID),
    )
    if sp.enabled() and session.get(MicrosoftAccount, admin.id) is not None:
        try:
            metadata = sp.item("", directory=True).remote
            current.web_url = metadata.get("webUrl")
        except SourceError:
            pass  # Keep the setting editable even when the old folder is unreachable.
    return current


@router.post("/check")
def check_originals(data: FolderLink, session: SessionDep, admin: Admin) -> FolderCheck:
    account = microsoft_account(session, admin)
    active = sp.configured_folder(session)
    url = sharing_url(data.url)
    encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    folder = folder_details(
        graph(f"{sp.GRAPH}/shares/u!{encoded}/driveItem", {"$select": FIELDS}), account
    )
    check_folder_read(folder)
    paths = catalog_part_folders(session)
    sample = sample_part_folders(paths)
    try:
        unavailable = unavailable_part_folders(folder, sample)
    except SourceError as error:
        raise HTTPException(error.status_code, error.message) from error
    ticket = jwt.encode(
        {
            "purpose": "originals-folder",
            "sub": str(admin.id),
            "source": folder.source_id,
            "drive": folder.drive_id,
            "item": folder.item_id,
            "previous": str(active.revision) if active else None,
            "exp": get_datetime_utc() + timedelta(minutes=30),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return FolderCheck(
        folder=info(folder),
        total=len(paths),
        checked=len(sample),
        found=len(sample) - len(unavailable),
        unavailable=unavailable,
        ticket=ticket,
    )


@router.put("")
def save_originals(data: FolderChoice, session: SessionDep, admin: Admin) -> FolderInfo:
    account = microsoft_account(session, admin)
    try:
        claims = jwt.decode(
            data.ticket,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "purpose", "source", "drive", "item"]},
        )
        if (claims["purpose"], claims["sub"], claims["source"]) != (
            "originals-folder",
            str(admin.id),
            settings.ASSETS_SOURCE_ID,
        ) or "previous" not in claims:
            raise jwt.InvalidTokenError()
    except jwt.InvalidTokenError:
        raise HTTPException(422, "Vuelve a comprobar la carpeta antes de guardarla.")
    folder = folder_details(
        graph(sp.folder_item_url(claims["drive"], claims["item"]), {"$select": FIELDS}),
        account,
    )
    check_folder_read(folder)
    current = session.exec(
        select(SharePointFolder)
        .where(SharePointFolder.source_id == settings.ASSETS_SOURCE_ID)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if current and (current.drive_id, current.item_id) == (
        folder.drive_id,
        folder.item_id,
    ):
        return info(current)
    conflict = "Otro administrador ha cambiado la carpeta. Vuelve a comprobarla."
    if (str(current.revision) if current else None) != claims["previous"]:
        raise HTTPException(409, conflict)
    if current:
        current.drive_id, current.item_id = folder.drive_id, folder.item_id
        current.name, current.web_url = folder.name, folder.web_url
        current.revision = uuid.uuid4()
    session.add(current or folder)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, conflict)
    return info(folder)
