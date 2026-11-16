"""Read-only, repeatable check of the production folder and measurement readers.

No database, SharePoint, correction import or PDF/OCR execution. Each piece runs in
a separate process so a failure or a large workbook does not stop the other pieces.
See conocimiento/prueba-ingesta-web.md for invocation and interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]


def save(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def configure(root: Path, out: Path) -> None:
    # Do not load the deployment .env, start workers or connect to any database.
    os.chdir(out)
    os.environ.update(
        PROJECT_NAME="Offline extraction check",
        POSTGRES_SERVER="127.0.0.1",
        POSTGRES_PORT="1",
        POSTGRES_USER="offline",
        POSTGRES_PASSWORD="unused-offline-password",
        POSTGRES_DB="offline_unused",
        FIRST_SUPERUSER="offline@example.com",
        FIRST_SUPERUSER_PASSWORD="unused-offline-password",
        ASSETS_ROOT=str(root),
        SHAREPOINT_ENABLED="false",
        EVIDENCE_WORKER_ENABLED="false",
        PREVIEW_WORKER_ENABLED="false",
        PYTHONDONTWRITEBYTECODE="1",
    )
    sys.path.insert(0, str(REPO / "backend"))

    def deny_network(event: str, _args: Any) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("Network/database access is forbidden in this dry run")

    sys.addaudithook(deny_network)


def folders(root: Path) -> tuple[list[str], list[str]]:
    found, remissions = [], []
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        for child in sorted(directory.iterdir()):
            if child.is_symlink() or not child.is_dir() or child.name.startswith("."):
                continue
            if re.match(r"^\d{4}(?:$|[ _-])", child.name):
                # Remission folders contain only a README. Do not walk every original
                # here: the production folder walker will do that once per piece.
                content = [p for p in child.iterdir() if not p.is_symlink()]
                relative = child.relative_to(root).as_posix()
                if any(p.name.casefold() not in {"readme.txt", "thumbs.db", "desktop.ini"} for p in content):
                    found.append(relative)
                else:
                    remissions.append(relative)
            elif depth < 2:
                pending.append((child, depth + 1))
    return sorted(found), sorted(remissions)


def check_piece(root: Path, folder: str, out: Path) -> dict[str, Any]:
    configure(root, out)
    from app.automatic_measurements import READER, collect, measurement_skip_reason
    from app.core.config import settings
    from app.file_sources import source_item
    from app.ingestion.measurement_provenance import usable_measurement
    from app.models import Part
    from app.part_setup import folder_files, proposed_code, reference_candidates
    from app.pilot import is_pilot

    started = time.monotonic()
    diagnostics: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "folder": folder, "code": proposed_code(folder), "status": "error",
        "diagnostics": diagnostics, "limitations": [], "observations": 0,
        "reader": READER,
        "limits_mib": {"file": settings.AUTO_MEASUREMENT_MAX_FILE_MB, "total": settings.AUTO_MEASUREMENT_MAX_TOTAL_MB},
    }
    result["packages"] = {}
    for package in ("xlrd", "python-calamine", "pandas", "fastapi", "pydantic", "sqlmodel"):
        try:
            result["packages"][package] = version(package)
        except PackageNotFoundError:
            result["packages"][package] = "metadata_unavailable"
    try:
        items = folder_files(folder)
        result["files_found"] = len(items)
        result["manifest"] = [
            {"path": i.relative_to(folder), "size": i.local.stat().st_size,
             "mtime_ns": i.local.stat().st_mtime_ns}
            for i in items if i.local
        ]
        candidates, notices = reference_candidates(folder)
        result["references"] = {
            kind: [c.model_dump() for c in choices] for kind, choices in candidates.items()
        }
        result["reference_notices"] = notices
        result["icp"] = [i.relative_to(folder) for i in items if i.suffix == ".icp"]
        if result["icp"]:
            result["limitations"].append("icp_not_read_by_web")
        # Validate local availability before any content read (OneDrive placeholders).
        checked = [
            source_item(i.path) if measurement_skip_reason(i.relative_to(folder)) is None else i
            for i in items
        ]
        part = Part(code=result["code"], name=Path(folder).name, folder_path=folder)
        result["pilot"] = is_pilot(part)
        # pilot=True only changes reviewed CSV identities. Metrology Excel is
        # read normally; the separate correction-study adapter is not executed.
        issues: dict[str, str] = {}
        groups = collect(folder, checked, pilot=result["pilot"], file_issues=issues, diagnostics=diagnostics)
        result["file_issues"] = issues
        result["groups"] = len(groups)
        result["observations"] = sum(len(rows) for rows in groups.values())
        result["usable_observations"] = sum(usable_measurement(row) for rows in groups.values() for row in rows)
        result["characteristic_codes"] = len({n for rows in groups.values() for row in rows for n in row["numbers"]})
        result["provenance"] = dict(Counter(row.get("provenance_state", "unknown") for rows in groups.values() for row in rows))
        result["status"] = "read" if result["observations"] else "no_observations"
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(getattr(error, "detail", error))}
    result["file_statuses"] = dict(Counter(d["status"] for d in diagnostics))
    result["skipped_files"] = dict(Counter(d.get("reason") for d in diagnostics if d["status"] == "skipped"))
    sheets = [s for d in diagnostics for s in d.get("sheets", [])]
    result["sheets_to_review"] = sum(s["status"] == "skipped" and bool(s.get("nominal_header_rows")) for s in sheets)
    result["rejected_rows"] = dict(Counter(r["reason"] for s in sheets for r in s.get("rejected_rows", [])))
    components = {s["sheet"].strip().lower() for s in sheets}
    if any(re.search(r"\bbase\b", s) for s in components) and any(re.search(r"\btapa\b", s) for s in components):
        result["limitations"].append("component_identity_missing_base_tapa")
    if result["status"] == "read" and (result["sheets_to_review"] or result["rejected_rows"] or result.get("file_issues")):
        result["status"] = "read_with_gaps"
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return result


def report(out: Path, manifest: dict[str, Any], results: list[dict[str, Any]]) -> None:
    save(out / "resumen.json", {**manifest, "results": results})
    lines = [
        "# Prueba de lectura de la web", "",
        f"Ejecución: {manifest['started_at']}", "",
        "Lectura local con código productivo; sin base de datos, correcciones ni OCR.",
        "`read` solo significa que terminó la lectura; no acredita cobertura completa ni exactitud.",
        "Observaciones son registros retenidos, incluidos generados/sin confirmar; no son cotas únicas.",
        "Hojas a revisar: omitidas con cabecera nominal; pueden incluir plantillas vacías o comparativas.", "",
        "| Pieza | Estado | Planos candidatos | Observaciones | Utilizables | Hojas a revisar | Límites conocidos |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(f"| {r['code']} | {r['status']} | {len(r.get('references', {}).get('drawing', []))} | {r.get('observations', 0)} | {r.get('usable_observations', 0)} | {r.get('sheets_to_review', 0)} | {', '.join(r.get('limitations', []))} |")
        if r.get("error"):
            lines.append(f"\nError {r['code']}: {r['error']['message']}\n")
    lines += ["", "Detalle por archivo, hoja y fila: `piezas/*.json`. Código y parámetros: `ejecucion.json`."]
    (out / "resumen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=REPO / "out/conocimiento/prueba-web")
    parser.add_argument("--piece", action="append", help="Restrict to this piece code; repeatable")
    parser.add_argument("--timeout", type=int, default=1800, help="Seconds per piece")
    parser.add_argument("--jobs", type=int, default=1, choices=range(1, 5), help="Concurrent piece subprocesses (1-4)")
    parser.add_argument("--folder", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out == root or out.is_relative_to(root):
        parser.error("Output must be outside the source dataset")
    out.mkdir(parents=True, exist_ok=True)
    (out / "piezas").mkdir(exist_ok=True)
    if args.folder:
        result = check_piece(root, args.folder, out)
        save(out / "piezas" / f"{result['code']}.json", result)
        print(f"{result['code']}: {result['status']} · {result['observations']} observaciones · {result['elapsed_seconds']} s", flush=True)
        return int(result["status"] == "error")
    selected, remissions = folders(root)
    if args.piece:
        selected = [p for p in selected if re.match(r"\d{4}", Path(p).name)[0] in args.piece]
    codes = [re.match(r"\d{4}", Path(p).name)[0] for p in selected]
    if len(codes) != len(set(codes)):
        parser.error("Multiple non-empty folders for one code; select an unambiguous source root")
    if not selected:
        parser.error("No piece folders found")
    hashes = {
        p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((REPO / "backend/app").rglob("*.py"))
    }
    for p in [Path(__file__).resolve(), REPO / "frontend/src/components/Parts/pieceFileDrafts.ts"]:
        hashes[p.relative_to(REPO).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {
        "started_at": datetime.now(timezone.utc).isoformat(), "root": str(root),
        "folders": selected, "remissions_skipped": remissions, "code_sha256": hashes,
        "python": sys.version, "timeout_per_piece": args.timeout, "jobs": args.jobs,
        "limit_overrides": {k: os.environ.get(k) for k in ["AUTO_MEASUREMENT_MAX_FILE_MB", "AUTO_MEASUREMENT_MAX_TOTAL_MB"]},
        "scope": "production collect + reference_candidates, local, no database, no corrections, no OCR",
    }
    save(out / "ejecucion.json", manifest)
    def run_piece(folder: str, code: str) -> dict[str, Any]:
        target = out / "piezas" / f"{code}.json"
        # Avoid accepting a previous result if the subprocess fails before saving.
        if target.exists():
            target.unlink()
        print(f"[start] {folder}", flush=True)
        try:
            completed = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--root", str(root), "--out", str(out), "--folder", folder], timeout=args.timeout, check=False)
            if not target.exists():
                raise RuntimeError(f"Worker exited {completed.returncode} without a result")
            result = json.loads(target.read_text(encoding="utf-8"))
        except Exception as error:
            result = {"code": code, "folder": folder, "status": "error", "error": {"type": type(error).__name__, "message": str(error)}}
            save(target, result)
        return result

    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_piece, folder, code) for folder, code in zip(selected, codes)]
        for future in as_completed(futures):
            results.append(future.result())
            results.sort(key=lambda r: r["folder"])
            report(out, manifest, results)
            print(f"[completed {len(results)}/{len(selected)}]", flush=True)
    return int(any(r["status"] == "error" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
