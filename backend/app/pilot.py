"""The 3212 pilot keeps dedicated readers. Identify it by code and folder name.

The folder name, not its full path, so moving the source root (for example from
`Exemples/0- Bolt Eye` to `Exemples`) does not disable the pilot.
"""

from pathlib import PurePosixPath

from app.models import Part

PILOT_CODE = "3212"
PILOT_FOLDER = "3212 Pump Housing"


def is_pilot(part: Part) -> bool:
    return (
        part.code == PILOT_CODE
        and PurePosixPath(part.folder_path or "").name == PILOT_FOLDER
    )
