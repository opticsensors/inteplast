"""Move stored references when the configured source root moves up one level.

On 2026-10-22 the root changed from `Exemples/0- Bolt Eye` to `Exemples`, so every
relative path stored for this dataset gains the `0- Bolt Eye/` prefix. UUIDs,
versions and links are kept; only paths and their deduplication keys change.
Change `ASSETS_HOST_PATH` and recreate the backend first: the new paths are checked
against the mounted root before anything is written.

    docker compose exec backend python -m app.rebase_source "0- Bolt Eye"
    docker compose exec backend python -m app.rebase_source "0- Bolt Eye" --apply
"""

import argparse
import logging
from pathlib import Path, PurePosixPath

from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.file_sources import reference_key
from app.measurement_models import MeasurementImport
from app.models import Part, StoredFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RebaseError(Exception):
    pass


def valid_prefix(prefix: str) -> str:
    parts = PurePosixPath(prefix).parts
    if (
        not prefix
        or "\\" in prefix
        or prefix.startswith("/")
        or prefix.endswith("/")
        or any(part in {".", ".."} for part in parts)
    ):
        raise RebaseError(f"Prefijo no válido: {prefix!r}")
    return prefix


def rebase(session: Session, prefix: str, *, check_root: bool = True) -> dict[str, int]:
    """Prefix every relative path of the configured dataset. Commit is up to the caller."""
    prefix = valid_prefix(prefix)
    source_id = settings.ASSETS_SOURCE_ID
    files = session.exec(
        select(StoredFile).where(
            StoredFile.source == "local", StoredFile.source_key == source_id
        )
    ).all()
    parts = session.exec(select(Part).where(col(Part.folder_path).is_not(None))).all()
    imports = session.exec(
        select(MeasurementImport).where(MeasurementImport.source_id == source_id)
    ).all()
    paths = [f.source_path or "" for f in files] + [p.folder_path or "" for p in parts]
    if any(path == prefix or path.startswith(f"{prefix}/") for path in paths):
        raise RebaseError("Ya hay rutas con ese prefijo: no se aplica dos veces.")
    if check_root:
        if not settings.ASSETS_ROOT:
            raise RebaseError("No hay carpeta de referencia configurada.")
        root = Path(settings.ASSETS_ROOT)
        # stat() only: OneDrive placeholders are not downloaded.
        missing = [
            p.folder_path
            for p in parts
            if p.folder_path and not root.joinpath(prefix, p.folder_path).is_dir()
        ] + [
            f.source_path
            for f in files
            if f.source_path and not root.joinpath(prefix, f.source_path).exists()
        ]
        if missing:
            raise RebaseError(
                f"{len(missing)} rutas no existen bajo la raíz nueva, p. ej. {missing[0]!r}. "
                "Comprueba ASSETS_HOST_PATH antes de aplicar."
            )
    unexpected_keys = 0
    for file in files:
        if not file.source_path:
            continue
        if file.reference_key != reference_key(
            file.source_path, file.source_version or ""
        ):
            unexpected_keys += 1
        file.source_path = f"{prefix}/{file.source_path}"
        file.reference_key = reference_key(file.source_path, file.source_version or "")
        session.add(file)
    for part in parts:
        part.folder_path = f"{prefix}/{part.folder_path}"
        session.add(part)
    for batch in imports:
        if batch.source_path:
            batch.source_path = f"{prefix}/{batch.source_path}"
            session.add(batch)
    return {
        "files": len(files),
        "parts": len(parts),
        "imports": len(imports),
        "unexpected_keys": unexpected_keys,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("prefix", help="Carpeta que pasa a formar parte de las rutas")
    parser.add_argument(
        "--apply", action="store_true", help="Guardar; sin él solo se comprueba"
    )
    args = parser.parse_args()
    with Session(engine) as session:
        counts = rebase(session, args.prefix)
        logger.info("Rutas a recolocar en %s: %s", settings.ASSETS_SOURCE_ID, counts)
        if args.apply:
            session.commit()
            logger.info("Aplicado.")
        else:
            session.rollback()
            logger.info("Comprobación sin cambios. Repite con --apply para guardar.")


if __name__ == "__main__":
    main()
