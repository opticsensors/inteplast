"""Build a portable visual report from an existing production-reader dry run.

Standard library only. Does not reopen originals or run the reader.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "out/conocimiento/prueba-web/2026-11-13-final"


def category(result: dict) -> str:
    status = result["status"]
    if status == "error":
        return "error"
    if status == "read":
        return "clean"
    if status == "read_with_gaps":
        return "partial"
    attempted = any(d["status"] != "skipped" for d in result.get("diagnostics", []))
    return "unread" if attempted else "absent"


def inventory_fingerprint(result: dict) -> list[tuple]:
    # The v5 consolidated JSON passed through JavaScript Number, which cannot
    # preserve nanosecond integers at epoch scale. Compare at that precision.
    return sorted(
        (f["path"], f["size"], float(f["mtime_ns"]))
        for f in result.get("manifest", [])
    )


def piece(result: dict, limits: dict | None) -> dict:
    evidence = []
    for file in result.get("diagnostics", []):
        sheets = []
        for sheet in file.get("sheets", []):
            rejected = sheet.get("rejected_rows", [])
            if sheet["status"] == "skipped" and sheet.get("nominal_header_rows"):
                sheets.append({
                    "name": sheet["sheet"], "reason": sheet.get("reason"),
                    "headers": sheet["nominal_header_rows"], "rejected": 0,
                })
            elif rejected:
                examples = []
                seen = set()
                for row in rejected:
                    identity = (str(row.get("code", "")), row["reason"])
                    if identity not in seen and len(examples) < 3:
                        examples.append(row)
                        seen.add(identity)
                sheets.append({
                    "name": sheet["sheet"], "reason": "rejected_rows",
                    "rejected": len(rejected), "examples": examples,
                })
        file_issue = result.get("file_issues", {}).get(file["path"])
        if file["status"] in {"error", "unsupported", "empty"} or sheets or file_issue:
            evidence.append({
                "path": file["path"], "status": file["status"],
                "reason": file.get("reason"), "issue": file_issue,
                "sheets": sheets,
            })
    # An error is the primary evidence, ahead of omissions earlier in the scan.
    evidence.sort(key=lambda f: f["status"] != "error")
    folder = result["folder"].split("/")
    feature = folder[0].split("- ", 1)[-1]
    if len(folder) > 2:
        feature += " · " + folder[-2]
    return {
        "code": result["code"], "feature": feature,
        "category": category(result), "status": result["status"],
        "observations": result.get("observations", 0),
        "usable": result.get("usable_observations"),
        "drawings": len(result.get("references", {}).get("drawing", [])),
        "cad": len(result.get("references", {}).get("part", [])),
        "icp": len(result.get("icp", [])),
        "files": result.get("files_found", 0),
        "fileIssues": len(result.get("file_issues", {})),
        "reviewSheets": result.get("sheets_to_review", 0),
        "rejected": result.get("rejected_rows", {}),
        "limitations": result.get("limitations", []),
        "error": result.get("error", {}).get("message"),
        "spc": sum(
            d["status"] == "unsupported" and "#P#" in d.get("reason", "")
            for d in result.get("diagnostics", [])
        ),
        "pilotExcelRead": sum(
            bool(result.get("pilot")) and d["status"] == "read"
            and Path(d["path"]).suffix.lower() in {".xls", ".xlsx", ".xlsm"}
            for d in result.get("diagnostics", [])
        ),
        "pilotExcelEmpty": sum(
            bool(result.get("pilot")) and d["status"] == "empty"
            and not d.get("reason")
            for d in result.get("diagnostics", [])
        ),
        "elapsed": result.get("elapsed_seconds"),
        "evidence": evidence, "limits": limits,
        "fixedSize": bool(limits and limits["old_size_blocked"] and result["status"].startswith("read")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT / "resumen.json")
    parser.add_argument("--output", type=Path, default=DEFAULT / "lectura-carpetas.html")
    parser.add_argument("--previous", type=Path, help="Earlier dry run to compare reader fixes")
    args = parser.parse_args()
    run = json.loads(args.input.read_text(encoding="utf-8"))
    limits = {r["code"]: r for r in run.get("size_comparison", [])}
    previous = {}
    if args.previous:
        earlier = json.loads(args.previous.read_text(encoding="utf-8"))
        previous = {r["code"]: r for r in earlier["results"]}
        earlier_limits = {r["code"]: r for r in earlier.get("size_comparison", [])}
        # Reuse only when paths, sizes and recorded timestamps agree (see above).
        for r in run["results"]:
            old = previous.get(r["code"], {})
            if r["code"] not in limits and inventory_fingerprint(r) == inventory_fingerprint(old):
                if r["code"] in earlier_limits:
                    limits[r["code"]] = earlier_limits[r["code"]]
    pieces = [piece(r, limits.get(r["code"])) for r in run["results"]]
    pieces.sort(key=lambda p: p["code"])
    for p in pieces:
        old = previous.get(p["code"])
        if old:
            p["previous"] = {
                "category": category(old), "observations": old.get("observations", 0),
                "usable": old.get("usable_observations"),
            }
    if len({p["code"] for p in pieces}) != len(pieces):
        raise ValueError("Duplicate piece codes in source report")
    payload = {
        "date": run["started_at"][:10], "pieces": pieces,
        "counts": dict(Counter(p["category"] for p in pieces)),
        "source": args.input.name, "reader": next(
            (r["reader"] for r in run["results"] if r.get("reader")), "unknown"
        ),
    }
    template = Path(__file__).with_name("informe_ingesta_web.html").read_text(encoding="utf-8")
    if template.count("__REPORT_DATA__") != 1:
        raise ValueError("Expected one data placeholder")
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Embedded source names must never close the JSON script element.
    encoded = encoded.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(template.replace("__REPORT_DATA__", encoded), encoding="utf-8")
    print(f"Created {args.output} ({len(pieces)} pieces, {args.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
