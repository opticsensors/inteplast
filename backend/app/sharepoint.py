"""Read the dataset from OneDrive/SharePoint through Microsoft Graph.

The paths are the same as in the local folder, relative to `SHAREPOINT_ROOT_PATH`
instead of `ASSETS_ROOT`, so one database works with either source. Requests use
the delegated token of the acting user, so Microsoft applies that user's
permissions. Contents are downloaded once per version into a disk cache, and the
latest version is always served: a change in SharePoint never requires relinking.
"""

import hashlib
import logging
import re
import shutil
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Any, Literal, NamedTuple
from urllib.parse import quote

import httpx
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.microsoft_auth import access_token, forget
from app.microsoft_models import SharePointFolder
from app.source_types import SourceError, SourceItem

logger = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
# RFC 3986 pchar: spaces, "#" and "%" in names must be percent-encoded.
PATH_SAFE = "!$&'()*+,;=:@"
ATTEMPTS = 4
PAGE_SIZE = 200
acting_user: ContextVar[uuid.UUID | None] = ContextVar("sharepoint_user", default=None)


class FolderRoot(NamedTuple):
    drive_id: str
    item_id: str


active_folder: ContextVar[FolderRoot | None] = ContextVar(
    "sharepoint_folder", default=None
)
_local = threading.local()


def enabled() -> bool:
    return settings.SHAREPOINT_ENABLED


def configured_folder(session: Session) -> SharePointFolder | None:
    return (
        session.get(SharePointFolder, settings.ASSETS_SOURCE_ID) if enabled() else None
    )


def catalog_root(session: Session) -> FolderRoot | None:
    """Keep a request or background operation on one root, even across commits."""
    row = configured_folder(session)
    return FolderRoot(row.drive_id, row.item_id) if row else None


@contextmanager
def acting_as(user_id: uuid.UUID | None) -> Iterator[None]:
    """Read SharePoint as this user, e.g. inside a background job they requested."""
    with Session(engine) as session:
        origin = active_folder.set(catalog_root(session))
    token = acting_user.set(user_id)
    try:
        yield
    finally:
        active_folder.reset(origin)
        acting_user.reset(token)


def client() -> httpx.Client:
    if getattr(_local, "client", None) is None:
        _local.client = httpx.Client(
            timeout=httpx.Timeout(30, read=300), follow_redirects=False
        )
    return _local.client  # type: ignore[no-any-return]


def token() -> str:
    user_id = acting_user.get()
    if user_id is None:
        raise SourceError(
            "unavailable", "Inicia sesión con Microsoft para leer SharePoint.", 401
        )
    return access_token(user_id)


def retry_delay(response: httpx.Response | None, attempt: int) -> float:
    # Graph's throttling guidance: honour Retry-After, otherwise back off.
    if response is not None:
        try:
            return min(float(response.headers.get("Retry-After", "")), 60.0)
        except ValueError:
            pass
    return float(2**attempt)


def request(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = None
    for attempt in range(ATTEMPTS):
        try:
            response = client().get(
                url, params=params, headers={"Authorization": f"Bearer {token()}"}
            )
        except httpx.HTTPError:
            response = None
            if attempt == ATTEMPTS - 1:
                raise SourceError(
                    "unavailable", "No se puede conectar con SharePoint.", 503
                )
        else:
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
            if attempt == ATTEMPTS - 1:
                break
        time.sleep(retry_delay(response, attempt))
    assert response is not None
    if response.status_code == 401:
        user_id = acting_user.get()
        if user_id is not None:
            forget(user_id)
        raise SourceError(
            "unavailable",
            "Tu sesión de Microsoft ha caducado. Vuelve a iniciar sesión.",
            401,
        )
    if response.status_code == 404:
        raise SourceError(
            "missing", "Archivo o carpeta no encontrado en SharePoint.", 404
        )
    if response.status_code == 400 and url.startswith(f"{GRAPH}/shares/"):
        raise SourceError(
            "unavailable", "Microsoft no reconoce el enlace de carpeta.", 422
        )
    if response.status_code == 403:
        # Not 403 for the browser: that status ends the application session.
        raise SourceError(
            "unavailable",
            "Tu cuenta de Microsoft no tiene permiso para leer este elemento.",
            409,
        )
    if response.status_code >= 400:
        logger.warning("Graph %s: %s", response.status_code, response.text[:500])
        raise SourceError(
            "unavailable", "SharePoint no responde. Vuelve a intentarlo.", 503
        )
    data: dict[str, Any] = response.json()
    return data


def validate(relative: str) -> list[str]:
    """The same path rules as the local adapter (no traversal, no hidden parts)."""
    if (
        relative and ("\\" in relative or ":" in relative or "\x00" in relative)
    ) or relative.startswith("/"):
        raise SourceError("unavailable", "Ruta de referencia no válida.", 400)
    parts = relative.split("/") if relative else []
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        raise SourceError("unavailable", "Ruta de referencia no válida.", 400)
    return parts


def drive_url() -> str:
    if settings.SHAREPOINT_DRIVE_ID:
        return f"{GRAPH}/drives/{quote(settings.SHAREPOINT_DRIVE_ID, safe='')}"
    return f"{GRAPH}/me/drive"


def item_url(relative: str) -> str:
    """Path-based addressing from the drive root, each segment percent-encoded."""
    folder = active_folder.get()
    if folder is not None:
        return folder_item_url(folder.drive_id, folder.item_id, relative)
    parts = [p for p in settings.SHAREPOINT_ROOT_PATH.split("/") if p]
    parts += validate(relative)
    if not parts:
        return f"{drive_url()}/root"
    return f"{drive_url()}/root:/{'/'.join(quote(p, safe=PATH_SAFE) for p in parts)}:"


def folder_item_url(drive_id: str, item_id: str, relative: str = "") -> str:
    base = f"{GRAPH}/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}"
    path = "/".join(quote(p, safe=PATH_SAFE) for p in validate(relative))
    return f"{base}:/{path}:" if path else base


def version(data: dict[str, Any]) -> str:
    # cTag changes with the content only; "sp:" tells it apart from a local stamp.
    tag = data.get("cTag") or data.get("eTag") or data.get("lastModifiedDateTime")
    if active_folder.get() is not None:
        tag = (data.get("parentReference", {}).get("driveId"), data.get("id"), tag)
    digest = hashlib.sha256(str(tag).encode()).hexdigest()[:24]
    return f"sp:{digest}:{int(data.get('size') or 0)}"


def as_item(relative: str, data: dict[str, Any]) -> SourceItem:
    directory = "folder" in data
    if not directory and "file" not in data:
        raise SourceError("missing", "Este elemento no es un archivo.", 404)
    return SourceItem(
        path=relative,
        directory=directory,
        size=0 if directory else int(data.get("size") or 0),
        version="" if directory else version(data),
        remote=data,
    )


def item(relative: str, *, directory: bool = False) -> SourceItem:
    found = as_item(relative, request(item_url(relative)))
    if directory and not found.directory:
        raise SourceError("missing", "Carpeta no encontrada.", 404)
    if not directory and found.directory:
        if not relative:
            raise SourceError("unavailable", "Selecciona un fichero.", 400)
        raise SourceError("missing", "Fichero no encontrado.", 404)
    return found


def children(relative: str) -> list[SourceItem]:
    """One folder, all pages, hidden entries skipped as in the local listing."""
    url = f"{item_url(relative)}/children"
    params: dict[str, Any] | None = {"$top": PAGE_SIZE}
    entries: list[SourceItem] = []
    while url:
        page = request(url, params)
        for data in page.get("value", []):
            name = str(data.get("name", ""))
            if name.startswith(".") or not ("folder" in data or "file" in data):
                continue
            entries.append(as_item("/".join(filter(None, [relative, name])), data))
        url, params = page.get("@odata.nextLink", ""), None
    return entries


def attachment_folder_url(
    kind: Literal["mold", "moldflow"], part_folder: str | None, file_path: str | None
) -> str | None:
    """Use Graph's own folder URL, with the permissions of the current user."""
    pattern = (
        r"(?:\d+[\s_-]*)?(?:3d[\s_-]*)?(?:molde|mold|mould)"
        if kind == "mold"
        else r"(?:\d+[\s_-]*)?moldflow"
    )

    def matches(name: str) -> bool:
        return re.fullmatch(pattern, name.strip(), re.IGNORECASE) is not None

    found: SourceItem | None = None
    if file_path:
        parent = PurePosixPath(file_path).parent
        if kind == "mold" and part_folder and parent.is_relative_to(part_folder):
            segments = parent.relative_to(part_folder).parts
            if segments and matches(segments[0]):
                parent = PurePosixPath(part_folder, segments[0])
        found = item("" if str(parent) == "." else str(parent), directory=True)
    elif part_folder:
        candidates = [
            f for f in children(part_folder) if f.directory and matches(f.name)
        ]
        if len(candidates) > 1:
            # Older deliveries can have an empty 2- Moldflow beside 7- Moldflow.
            candidates = [
                f
                for f in candidates
                if f.remote.get("folder", {}).get("childCount") != 0
            ]
        if len(candidates) == 1:
            found = candidates[0]
    url = (found.remote or {}).get("webUrl") if found else None
    return url if isinstance(url, str) and url.startswith("https://") else None


def walk(folder: str, *, too_wide: str, limit: int = 20000) -> list[SourceItem]:
    """Files under a folder, breadth first, with the local walkers' size limit."""
    item(folder, directory=True)
    pending, files, visited = [folder], [], 0
    while pending:
        entries = children(pending.pop(0))
        visited += len(entries)
        if visited > limit:
            raise SourceError("unavailable", too_wide, 422)
        for entry in entries:
            if entry.directory:
                pending.append(entry.path)
            else:
                files.append(entry)
    return files


# Only folder names and a change cursor. Never cache a permission or a download URL.
_icp_inventories: dict[tuple[uuid.UUID | None, str, str], tuple[str, list[str]]] = {}
_icp_lock = threading.Lock()


def icp_folders(folder: str) -> list[str] | None:
    """Discover project folders, checking for changes on each subsequent lookup."""
    root_id = item(folder, directory=True).remote["id"]
    url = f"{item_url(folder)}/delta"
    key = (acting_user.get(), url, root_id)
    with _icp_lock:
        cached = _icp_inventories.get(key)
    if cached:
        cursor, folders = cached
        try:
            page = request(cursor)
        except SourceError as error:
            if error.status_code not in {404, 503}:
                raise
            # Expired cursors and resets need a new full snapshot.
        else:
            if (
                page.get("value") == []
                and page.get("@odata.deltaLink")
                and not page.get("@odata.nextLink")
            ):
                with _icp_lock:
                    if _icp_inventories.get(key) is cached:
                        _icp_inventories[key] = (page["@odata.deltaLink"], folders)
                return folders
    try:
        result = _icp_inventory(url, folder, root_id)
    except SourceError as error:
        if error.status_code in {404, 503}:
            return None  # Drives without folder delta can still list their children.
        raise
    if result is None:
        return None
    with _icp_lock:
        if len(_icp_inventories) >= 256 and key not in _icp_inventories:
            _icp_inventories.pop(next(iter(_icp_inventories)))
        _icp_inventories[key] = result
    return result[1]


def _icp_inventory(url: str, folder: str, root_id: str) -> tuple[str, list[str]] | None:
    """Delta supplies a hierarchy by ID. File versions still come from live listings."""
    params: dict[str, Any] | None = {
        "$select": "id,name,parentReference,folder,file,deleted",
        "$top": 500,
    }
    nodes: dict[str, dict[str, Any]] = {}
    while url:
        page = request(url, params)
        for node in page.get("value", []):
            if "deleted" in node:
                nodes.pop(node["id"], None)
            else:
                nodes[node["id"]] = node
        if len(nodes) > 20001:  # same ceiling as walk(), plus the piece folder
            raise SourceError(
                "unavailable", "Selecciona la carpeta concreta de la pieza.", 422
            )
        url, params = page.get("@odata.nextLink", ""), None
        if not url and not page.get("@odata.deltaLink"):
            return None

    parents = {
        node.get("parentReference", {}).get("id")
        for node in nodes.values()
        if "file" in node
        and PurePosixPath(node["name"]).suffix.lower() == ".icp"
        and not node["name"].startswith(".")
    }
    folders = set()
    for parent in parents:
        names: list[str] = []
        seen: set[str] = set()
        while parent != root_id:
            node = nodes.get(parent)
            if not node or "folder" not in node or parent in seen:
                return None
            if node["name"].startswith("."):
                break
            seen.add(parent)
            names.append(node["name"])
            parent = node.get("parentReference", {}).get("id")
        else:
            folders.add("/".join([folder, *reversed(names)]))
    return page["@odata.deltaLink"], sorted(folders)


def cache_directory(data: dict[str, Any]) -> Path:
    parent = data.get("parentReference") or {}
    identity = f"{parent.get('driveId', '')}:{data.get('id', '')}"
    return (
        settings.uploads_path
        / "sharepoint"
        / hashlib.sha256(identity.encode()).hexdigest()[:32]
    )


def download(found: SourceItem) -> Path:
    """The local copy of this version, downloaded once and reused afterwards."""
    data = found.remote or {}
    directory = cache_directory(data)
    target = directory / (
        hashlib.sha256((found.version or "").encode()).hexdigest()[:24] + found.suffix
    )
    if target.is_file():
        return target
    directory.mkdir(parents=True, exist_ok=True)
    partial = directory / f".{uuid.uuid4().hex}.part"
    url = data.get("@microsoft.graph.downloadUrl")
    try:
        for attempt in range(2):
            if not url or attempt:
                # Pre-authenticated URLs expire within minutes: ask for a fresh one.
                url = request(item_url(found.path)).get("@microsoft.graph.downloadUrl")
            if not url:
                raise SourceError(
                    "unavailable", "SharePoint no ofrece la descarga.", 503
                )
            try:
                # No Authorization header: the URL itself is pre-authenticated.
                with client().stream("GET", url) as response:
                    if response.status_code in {401, 403, 404, 410} and not attempt:
                        continue
                    response.raise_for_status()
                    with partial.open("wb") as output:
                        for chunk in response.iter_bytes(1024 * 1024):
                            output.write(chunk)
            except httpx.HTTPError:
                if attempt:
                    raise SourceError(
                        "unavailable", "No se ha podido descargar de SharePoint.", 503
                    )
                continue
            if partial.stat().st_size != found.size:
                raise SourceError(
                    "changed",
                    "El archivo ha cambiado durante la descarga. Vuelve a intentarlo.",
                )
            partial.replace(target)
            break
        else:
            raise SourceError(
                "unavailable", "No se ha podido descargar de SharePoint.", 503
            )
    finally:
        partial.unlink(missing_ok=True)
    # Keep only the current version of this item; other workers' .part files stay.
    for old in directory.iterdir():
        if old != target and not old.name.startswith("."):
            old.unlink(missing_ok=True)
    return target


def stage(
    folder: str, subfolders: tuple[str, ...], suffixes: set[str], output: Path
) -> Path:
    """Copy the files a reader needs into a temporary folder with the same layout."""
    root = output / PurePosixPath(folder).name
    for found in walk(folder, too_wide="Selecciona la carpeta concreta de la pieza."):
        relative = found.relative_to(folder)
        if found.suffix not in suffixes or relative.split("/", 1)[0] not in subfolders:
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(download(found), target)
    root.mkdir(parents=True, exist_ok=True)
    return root
