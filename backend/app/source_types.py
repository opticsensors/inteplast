"""Types shared by the local folder and the SharePoint adapters."""

from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any


class SourceError(Exception):
    def __init__(self, state: str, message: str, status_code: int = 409):
        self.state = state
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class SourceItem:
    """A file or folder of the dataset, addressed by its path from the source root.

    Size and version are filled lazily for local walks, as before; SharePoint
    listings already include them. `local` is the walked file, `remote` the Graph item.
    """

    path: str
    directory: bool = False
    size: int | None = None
    version: str | None = None
    local: Path | None = None
    remote: Any = None

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.path).suffix.lower()

    def relative_to(self, folder: str) -> str:
        return PurePosixPath(self.path).relative_to(folder).as_posix()

    def with_metadata(self, size: int, version: str) -> "SourceItem":
        return replace(self, size=size, version=version)
