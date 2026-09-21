"""Run application document readers outside the API process."""

import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    kind, source, destination = sys.argv[1:]
    output = Path(destination)
    if kind == "drawing":
        from app.ingestion.drawing import build_index

        data = build_index(Path(source), output, use_ocr=True)
    elif kind == "study":
        from app.ingestion.pilot_3212.study import build_data

        (output / "assets").mkdir(parents=True, exist_ok=True)
        # PDF readers perform many small seeks. On the Windows read-only bind
        # mount that is much slower than a single sequential copy. Stage only
        # the formats used by this adapter, never the large CAD/scan directories.
        root = Path(source).resolve()
        staged = output / "input"
        for folder in ("4- Metrologia", "5- Retoques de molde"):
            for path in (root / folder).rglob("*"):
                if path.is_file() and path.suffix.lower() in {
                    ".csv",
                    ".xls",
                    ".pptx",
                    ".pdf",
                    ".txt",
                }:
                    if path.is_symlink() or not path.resolve().is_relative_to(root):
                        raise ValueError("Source outside the part folder")
                    staged_file = staged / path.relative_to(root)
                    staged_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, staged_file)
        data = build_data(staged, output / "assets")
    else:
        raise ValueError(f"Unsupported evidence job: {kind}")
    (output / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
