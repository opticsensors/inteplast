"""Evidence used for automatic file proposals. All paths come from the source adapter."""

import hashlib
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from app.file_sources import item_file, source_item

DRAWING_NAME = re.compile(
    r"(?<![a-z0-9])(?:drw|bal{1,2}o{1,2}n{1,2}ed)(?![a-z0-9])", re.I
)
AUXILIARY = re.compile(
    r"(?:^|[^a-z0-9])(?:electrodes?|electrodos?|insert[os]*|bridge|puente|"
    r"(?:(?:movable|fixed|injection|ejection)[ _-]*side)|transport[ _-]*bar|"
    r"part(?:[ _-]+(?:and|with)[ _-]+(?:sprue|shrinkage))?|"
    r"tool[ _-]*mark|core|semimolde|aufbau[ _-]*(?:top|bottom)|inj|exp)(?:$|[^a-z0-9])",
    re.I,
)
MOLD_ASSEMBLY = re.compile(
    r"(?:^|[^a-z0-9])(?:mold|mould|molde|assembly|conjunto)(?:$|[^a-z0-9])", re.I
)


@lru_cache(maxsize=256)
def file_digest(local: Path, _version: str) -> bytes:
    result = hashlib.sha256()
    with local.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.digest()


def digest_for(path: str, version: str) -> bytes:
    item = source_item(path)
    if item.version != version:
        raise OSError("El archivo cambió durante la selección.")
    return file_digest(item_file(item), version)


@lru_cache(maxsize=128)
def page_evidence(local: Path, _version: str, *filename: str) -> str | bool | None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.ingestion.drawing_reference",
            str(local),
            *filename,
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode or not result.stdout.strip():
        return None
    evidence = json.loads(result.stdout.splitlines()[-1])
    return evidence if isinstance(evidence, (str, bool)) else None


def drawing_ids(filename: str) -> set[str]:
    # Unambiguous stand-alone numeric product/drawing identifiers; ignore YYYYMMDD dates.
    return {
        t
        for t in re.findall(r"(?<![a-z0-9])\d{7,12}(?![a-z0-9])", filename, re.I)
        if not re.fullmatch(r"(?:19|20)\d{6}", t)
    }


def conflicting_product_numbers(cad: str, drawing: str) -> bool:
    cad_ids, drawing_numbers = drawing_ids(cad), drawing_ids(drawing)
    if cad_ids and drawing_numbers and cad_ids.isdisjoint(drawing_numbers):
        return True
    # Two different catalogue numbers from the same explicitly numbered series.
    pattern = r"(?<!\d)(\d{5})-(\d{5})(?!\d)"
    cad_series, drawing_series = (
        set(re.findall(pattern, cad)),
        set(re.findall(pattern, drawing)),
    )
    return bool(
        {p for p, _ in cad_series} & {p for p, _ in drawing_series}
    ) and cad_series.isdisjoint(drawing_series)
