"""Prototipo independiente: antes, accion propuesta, prevision XLS y medida posterior.

Lee los originales del 3212 sin modificarlos. Genera out/correcciones-3212/index.html;
no ejecuta ni modifica ver_todo.py ni las salidas de los visores anteriores.

    python prototypes/data-explorer/ver_correcciones.py
    python prototypes/data-explorer/ver_correcciones.py --no-abrir
    python prototypes/data-explorer/ver_correcciones.py --raiz "D:/datos/3212 Pump Housing"

Dependencias: pandas, numpy, plotly, PyMuPDF, xlrd (pip install xlrd).
Las correspondencias de acciones/celdas son revisadas para esta pieza, no inferidas.
xlrd lee resultados de formulas guardados; no recalcula ni ejecuta macros.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import posixpath
import re
import sys
import webbrowser
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from plotly.offline import get_plotlyjs

try:
    import xlrd
except ImportError:
    raise SystemExit(f'Falta xlrd. Instalar con: "{sys.executable}" -m pip install xlrd')

from metrologia import ver_csv, ver_pdf


ROOT = ver_csv.RAIZ.parent
OUTPUT = Path(__file__).resolve().parent / "out" / "correcciones-3212"
SAMPLES = ("01", "03", "05", "08")
CAVITIES = ("c13", "c14", "c15", "c16")
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
CORRECTIONS = {
    "1": {
        "date": "24/01/2024", "before": "01", "after": "03",
        "xls": "5- Retoques de molde/3212-00_intern.01_mold_correction.xls",
        "pptx": "5- Retoques de molde/20240124-Mold correction_1_P3212_rev1.pptx",
    },
    "2": {
        "date": "18/03/2024", "before": "03", "after": "05",
        "xls": "5- Retoques de molde/2N/3212-00_intern.03_correction_2_.xls",
        "pptx": "5- Retoques de molde/2N/20240318-Mold correction_2_P3212_rev1.pptx",
    },
}
CASES = {
    "N161": {
        "title": "Diámetro interior", "caption": "Dos extremos fuera de tolerancia",
        "correction": "2", "actions": ["2.16"],
        "description": "El plan propone reducir 0,305 mm en diámetro total y conservar la redondez. La previsión y las dos evaluaciones se comparan por separado.",
        "note": "GX y LP(2) máximo describen evaluaciones diferentes de la misma geometría. Una sola de ellas no basta para declarar conforme la característica.",
    },
    "N240": {
        "title": "Distancia al plano A", "caption": "Una previsión con dos pasos",
        "correction": "2", "actions": ["2.13", "2.5"],
        "description": "La previsión combina +0,020 mm del plano A y −0,080 mm del retoque local: un efecto neto de −0,060 mm sobre la cota.",
        "note": "La acción 2.13 no nombra N240 en su título. La correspondencia se revisó en la imagen del plano y en la tabla del Excel, filas 224–225.",
    },
    "N170": {
        "title": "Diámetro del Bolt Eye", "caption": "La mejora es parcial",
        "correction": "1", "actions": ["1.33"],
        "description": "La acción plantea usar expulsores de 4 y esperar a revisar la posición. El Excel calcula una previsión de +0,500 mm para las evaluaciones del diámetro.",
        "note": "El CSV y el método indican H=1,5 mm; el Excel anota H=−1,5. Se conserva esa discrepancia. B2 a H=5 se identifica por ID CMM 16, aunque la cabecera diga B1.",
    },
    "N165": {
        "title": "Espesor local", "caption": "Plano A y retoque local",
        "correction": "2", "actions": ["2.11", "2.4"],
        "description": "El Excel encadena +0,020 mm del plano A y −0,220 mm de retoque local. La previsión final del máximo ya supera el límite permitido.",
        "note": "La previsión usa GLOBAL, resumen de los puntos locales. El bloque N165 MIN/MAX del CSV es otra evaluación; se muestra aparte. Las 60 secciones pertenecen a la misma pieza.",
    },
}


def number(value):
    """Missing, invalid and Excel error values are never interpreted as zero."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if math.isfinite(value) else None
    return None


def source(path: Path, root: Path, locator: str = "") -> dict:
    return {"path": path.relative_to(root).as_posix(), "url": path.resolve().as_uri(), "locator": locator}


def result(value, lower, upper) -> str:
    if any(number(x) is None for x in (value, lower, upper)) or lower > upper:
        return "unknown"
    return "inside" if lower - 1e-9 <= value <= upper + 1e-9 else "outside"


def csv_identity(row, inherited_id: str) -> tuple | None:
    block, idx = row["bloque"].strip(), int(row["idx"])
    if block.startswith("N170"):
        element = int(inherited_id) if inherited_id.isdigit() else -1
        if 11 <= element <= 14:
            bolt, height = element - 10, "1.5"
        elif 15 <= element <= 18:
            bolt, height = element - 14, "5.0"
        else:
            raise ValueError(f"N170 sin ID CMM reconocido: {block}, {inherited_id}")
        return ("N170", f"B{bolt}-H{height}", idx)
    if block.startswith("N161 "):
        return ("N161", "main", idx)
    if block.startswith("N240 "):
        return ("N240", "main", idx)
    if block.startswith("GLOBAL "):
        return ("N165", "main", idx)
    if block.startswith("N165 MIN"):
        return ("N165", "scan", idx)
    match = re.match(r"POINT\s+(\d+)\s", block)
    if match:
        return ("N165", f"P{int(match[1]):02d}", idx)
    return None


def load_csv(root: Path) -> tuple[dict, list]:
    records, files = {}, ver_csv.descubrir(root / "4- Metrologia")
    seen_files = set()
    for file in files:
        sample, cavity = file["muestreo"], file["cavidad"]
        if (sample, cavity) in seen_files:
            raise ValueError(f"CSV duplicado para {sample}/{cavity}; seleccionar la fuente explícitamente")
        seen_files.add((sample, cavity))
        table = ver_csv.leer_csv_cavidad(file["ruta"])
        element, previous_group = "", None
        for row in table.to_dict("records"):
            group = (row["bloque"], row["ocurrencia"])
            if group != previous_group:
                element, previous_group = "", group
            element = row["id_cmm"] or element
            identity = csv_identity(row, element)
            if identity is None:
                continue
            nominal, lo, hi = (number(row[k]) for k in ("nominal", "tol_inf", "tol_sup"))
            lower = nominal + lo if nominal is not None and lo is not None else None
            upper = nominal + hi if nominal is not None and hi is not None else None
            key = (sample, cavity, *identity)
            if key in records:
                raise ValueError(f"Medición duplicada: {key}")
            measured = number(row["medido"])
            records[key] = {
                "value": measured, "lower": lower, "upper": upper,
                "status": result(measured, lower, upper), "reported_nok": bool(row["nok"]),
                "source": source(file["ruta"], root, f'{row["bloque"].strip()} · aparición {row["ocurrencia"]} · fila {row["idx"]} · CMM {element or "sin ID"}'),
            }
    return records, files


def cell_value(sheet, row: int, col: int):
    if row > sheet.nrows or col > sheet.ncols:
        return None
    cell = sheet.cell(row - 1, col - 1)
    return number(cell.value) if cell.ctype == xlrd.XL_CELL_NUMBER else None


def validate_excel_mapping(sheet, row: int, feature: str):
    """Check fixed pilot mappings against feature, equipment and nominal."""
    inherited = ""
    for r in range(row):
        value = sheet.cell_value(r, 0)
        if value != "":
            inherited = str(value).replace("N", "").split(".")[0]
    if inherited != feature[1:]:
        raise ValueError(f"Mapeo XLS obsoleto: fila {row}, esperaba {feature}, encontró {inherited}")
    if str(sheet.cell_value(row - 1, 6)).strip() != "CMM":
        raise ValueError(f"La fila XLS {row} ya no es una medida CMM")
    expected = {"N161": 45.4, "N240": 18.5, "N170": 4.0, "N165": 1.35}[feature]
    actual = cell_value(sheet, row, 4)
    if actual is None or abs(actual - expected) > 1e-9:
        raise ValueError(f"Nominal XLS inesperado en {feature}, fila {row}: {actual}")


def mappings(feature: str, variant: str) -> list[tuple]:
    # label, original row, final prediction row, [(retoc row, intermediate prediction row)]
    if feature == "N161":
        return [("GX", 101, 101, [(101, 101)]), ("LP(2) máximo", 102, 102, [(102, 102)])]
    if feature == "N240":
        return [("Distancia", 224, 225, [(224, 224), (225, 225)])]
    if feature == "N165":
        return [("GLOBAL mínimo", 111, 116, [(111, 111), (116, 116)]),
                ("GLOBAL máximo", 112, 117, [(112, 112), (117, 117)])]
    match = re.fullmatch(r"B([1-4])-H(1\.5|5\.0)", variant)
    if not match:
        raise ValueError(f"Variante N170 no reconocida: {variant}")
    start = 146 + (int(match[1]) - 1) * 4 + (2 if match[2] == "5.0" else 0)
    return [("GX", start, start, [(146, start)]), ("LP máximo", start + 1, start + 1, [(146, start + 1)])]


def compare(records: dict, books: dict, root: Path, feature: str, variant: str, cavity: str) -> dict:
    case = CASES[feature]
    correction = CORRECTIONS[case["correction"]]
    sheet = books[case["correction"]].sheet_by_name("DR(100%)")
    cavity_index = CAVITIES.index(cavity)
    original_col, prediction_col = 8 + cavity_index, 16 + cavity_index
    items, warnings = [], []
    for idx, (label, original_row, predicted_row, steps) in enumerate(mappings(feature, variant), 1):
        validate_excel_mapping(sheet, original_row, feature)
        before = records.get((correction["before"], cavity, feature, variant, idx))
        after = records.get((correction["after"], cavity, feature, variant, idx))
        xls_before = cell_value(sheet, original_row, original_col)
        predicted = cell_value(sheet, predicted_row, prediction_col)
        lower = cell_value(sheet, original_row, 4)
        low_delta, high_delta = cell_value(sheet, original_row, 6), cell_value(sheet, original_row, 5)
        upper = lower + high_delta if lower is not None and high_delta is not None else None
        lower = lower + low_delta if lower is not None and low_delta is not None else None
        for stage, record in (("inicial", before), ("posterior", after)):
            if not record or record["value"] is None:
                warnings.append(f"{label}: falta la medición {stage} de esta cavidad.")
            elif record["lower"] != lower or record["upper"] != upper:
                warnings.append(f"{label}: límites diferentes entre CSV {stage} y Excel; revisar comparabilidad.")
        if before and xls_before is not None and before["value"] is not None and abs(before["value"] - xls_before) > 0.0005:
            warnings.append(f"{label}: el valor inicial del Excel ({xls_before}) difiere del CSV ({before['value']}). La previsión se conserva tal como está guardada.")
        stages = [{"delta": cell_value(sheet, r, 15), "value": cell_value(sheet, pr, prediction_col),
                   "cells": f"O{r} → {xlrd.formula.colname(prediction_col - 1)}{pr}"} for r, pr in steps]
        if all(s["delta"] is not None for s in stages) and xls_before is not None and predicted is not None:
            if abs(xls_before + sum(s["delta"] for s in stages) - predicted) > 1e-7:
                warnings.append(f"{label}: el resultado XLS no coincide con la suma de los pasos revisados; comprobar fórmula.")
        items.append({
            "label": label, "before": before, "after": after, "prediction": predicted,
            "prediction_status": result(predicted, lower, upper), "lower": lower, "upper": upper,
            "xls_before": xls_before, "steps": stages,
            "source": source(root / correction["xls"], root,
                             f"DR(100%)!{xlrd.formula.colname(original_col-1)}{original_row}; "
                             f"{xlrd.formula.colname(prediction_col-1)}{predicted_row}; " + "; ".join(s["cells"] for s in stages)),
            "history": [records.get((sample, cavity, feature, variant, idx)) for sample in SAMPLES],
        })
    return {"items": items, "warnings": warnings}


def extract_actions(root: Path, assets: Path) -> dict:
    actions = {}
    wanted = {a for case in CASES.values() for a in case["actions"]}
    for correction_id, correction in CORRECTIONS.items():
        path = root / correction["pptx"]
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                 key=lambda n: int(re.search(r"(\d+)\.xml", n)[1]))
            for slide_index, name in enumerate(slide_names, 1):
                xml = ET.fromstring(archive.read(name))
                paragraphs = ["".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
                              for p in xml.findall(".//a:p", NS)]
                match = re.search(r"Tool\s+correction\s+(\d+\.\d+)", "\n".join(paragraphs))
                if not match or match[1] not in wanted:
                    continue
                action_id = match[1]
                relationships = ET.fromstring(archive.read(posixpath.join(posixpath.dirname(name), "_rels", posixpath.basename(name) + ".rels")))
                targets = {r.attrib["Id"]: r.attrib for r in relationships}
                images = []
                for pic in xml.findall(".//p:pic", NS):
                    blip = pic.find(".//a:blip", NS)
                    if blip is None:
                        continue
                    rel = targets.get(blip.get("{" + NS["r"] + "}embed"), {})
                    if not rel or rel.get("TargetMode") == "External":
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), rel["Target"]))
                    if not target.startswith("ppt/media/"):
                        continue
                    blob = archive.read(target)
                    image_name = "slide-" + hashlib.sha256(blob).hexdigest()[:20] + Path(target).suffix.lower()
                    (assets / image_name).write_bytes(blob)
                    images.append({"url": "assets/" + image_name, "label": f"Imagen original · acción {action_id}"})
                # The first picture is the corporate logo in these reviewed slides.
                illustrations = images[1:] if len(images) > 1 else images
                cleaned = [p for p in paragraphs if p and not p.startswith(("Tool correction", "Longitud", "Current situation", "Tool correction plan"))
                           and not re.fullmatch(r"\d+/\d+", p) and p != "OK" and "nº" not in p]
                actions[action_id] = {
                    "id": action_id, "paragraphs": cleaned, "images": illustrations,
                    "marker": "OK" if "OK" in paragraphs else "Sin marcador OK",
                    "source": source(path, root, f"Acción {action_id} · diapositiva física {slide_index} · {posixpath.basename(name)}"),
                }
    missing = wanted - actions.keys()
    if missing:
        raise ValueError(f"No se localizaron las acciones revisadas: {sorted(missing)}")
    return actions


def load_profiles(root: Path, assets: Path) -> list:
    profiles = []
    for item in ver_pdf.descubrir(root / "4- Metrologia"):
        sample, cavity = item["muestreo"], item["cavidad"]
        name = f"perfil-{sample}-{cavity}-{item['ruta'].stem}"
        record = ver_pdf.leer_pdf(item["ruta"], assets, 1.25, name)
        record.update(sample=sample, cavity=cavity, element=item["ruta"].stem,
                      image="assets/" + record["png"], source=source(item["ruta"], root, "Página 1"),
                      excess=ver_pdf.peor_infraccion(record), errors=ver_pdf.errores_medicion(record))
        profiles.append(record)
    return profiles


def load_support(root: Path) -> list:
    support = []
    for path in sorted((root / "4- Metrologia").rglob("*.txt")):
        record = {"source": source(path, root), "sample": ver_csv.num_muestreo(path), "cavity": ver_csv.num_cavidad(path)}
        if "PUNTS_NOUS" in path.name:
            parent = path.with_name("3212_PUNTS.txt")
            points = np.loadtxt(path)
            whole = np.loadtxt(parent)
            record.update(kind="PUNTS_NOUS", points=len(points), subset_verified=bool(np.array_equal(points, whole[-len(points):])))
        else:
            record["kind"] = "PUNTS" if "PUNTS" in path.name else "Nube de cavidad"
        support.append(record)
    return support


def build_data(root: Path, assets: Path) -> dict:
    records, files = load_csv(root)
    books = {key: xlrd.open_workbook(root / c["xls"]) for key, c in CORRECTIONS.items()}
    cases = {}
    for feature, definition in CASES.items():
        variants = [f"B{bolt}-H{height}" for bolt in range(1, 5) for height in ("1.5", "5.0")] if feature == "N170" else ["main"]
        cases[feature] = {
            **definition, "variants": variants,
            "comparisons": {variant: {cavity: compare(records, books, root, feature, variant, cavity)
                                       for cavity in CAVITIES} for variant in variants},
        }
    sections = {cavity: {sample: [[records.get((sample, cavity, "N165", f"P{p:02d}", idx))
                                  for idx in (1, 2)] for p in range(1, 61)] for sample in SAMPLES} for cavity in CAVITIES}
    scan = {cavity: {sample: [records.get((sample, cavity, "N165", "scan", idx)) for idx in (1, 2)]
                    for sample in SAMPLES} for cavity in CAVITIES}
    actions = extract_actions(root, assets)
    profiles = load_profiles(root, assets)
    support = load_support(root)
    for book in books.values():
        book.release_resources()
    return {"cases": cases, "corrections": CORRECTIONS, "actions": actions, "sections": sections,
            "scan": scan, "profiles": profiles, "support": support, "samples": list(SAMPLES),
            "cavities": list(CAVITIES), "csv_count": len(files), "review_date": "17/09/2026"}


PAGE = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>3212 · Correcciones y resultados</title>
<script src="assets/plotly.min.js"></script>
<style>
:root{--ink:#1c3033;--muted:#5c6e70;--line:#dce4e1;--paper:#fff;--bg:#f4f6f2;--green:#117966;--purple:#7759a6;--orange:#b16a29;--red:#ad3a32}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Segoe UI",Arial,sans-serif}button,select{font:inherit;color:inherit}button,a,select{touch-action:manipulation}a{color:var(--green);text-underline-offset:3px}button{cursor:pointer}header{padding:26px 5vw 20px;max-width:1540px;margin:auto}.eyebrow{font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--green)}.topline{display:flex;justify-content:space-between;gap:20px;align-items:center}.small{font-size:12px;color:var(--muted)}h1{font-size:clamp(30px,4vw,44px);font-weight:600;letter-spacing:-.04em;line-height:1.15;margin:20px 0 10px}header p{color:var(--muted);margin:0;max-width:780px}.timeline{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:23px;font-size:12px;color:var(--muted)}.timeline b{color:var(--ink)}.timeline span{padding:5px 10px;border:1px solid var(--line);border-radius:5px;background:white}.timeline .event{border:0;background:none;color:var(--green)}main{max-width:1540px;margin:auto;padding:0 5vw 55px}.navigation{display:flex;gap:8px;overflow:auto;border-bottom:1px solid var(--line);padding:12px 0 0;margin-bottom:22px}.navigation button{border:0;background:transparent;padding:12px 15px 13px;white-space:nowrap;border-bottom:3px solid transparent}.navigation button[aria-pressed=true]{border-color:var(--green);color:var(--green);font-weight:700}.navigation button span{font-size:12px;margin-left:7px;color:var(--muted)}.toolbar{display:flex;align-items:end;justify-content:space-between;gap:20px;margin:15px 0 20px}.toolbar h2{font-size:25px;letter-spacing:-.02em;margin:3px 0 0;font-weight:600}.controls{display:flex;flex-wrap:wrap;gap:12px}label{display:flex;flex-direction:column;font-size:12px;gap:4px;color:var(--muted)}select{background:white;border:1px solid #bacbc5;border-radius:6px;padding:8px 30px 8px 10px;min-width:105px;font-size:14px;max-width:100%}.split{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(270px,1fr);gap:22px}.panel{background:white;border:1px solid var(--line);border-radius:10px;padding:22px;min-width:0}.panel h3{font-size:17px;font-weight:600;margin:0 0 8px}.panel p{margin:6px 0 15px}.chart{height:320px;min-width:0}.chart.short{height:280px}.chart.tall{height:360px}.caption{font-size:12px;color:var(--muted)}.insight{border-left:3px solid var(--green);padding:12px 16px;background:#edf5f0;margin-top:14px}.insight strong{font-weight:600}.insight.issue{border-color:var(--orange);background:#faf3e9}.issue-text{font-size:13px;background:#fff6de;padding:10px 14px;border-radius:5px;margin:10px 0}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th{font-size:11px;color:var(--muted);font-weight:600}th:first-child,td:first-child{text-align:left}td span.state{display:block;font-size:11px}.inside{color:var(--green)}.outside{color:var(--red)}.unknown{color:var(--muted)}.action-photo{padding:0;border:1px solid var(--line);background:#f9faf8;border-radius:7px;display:block;width:100%;margin:15px 0 7px;overflow:hidden}.action-photo img{display:block;max-height:245px;width:100%;object-fit:contain}.action-text{font-size:14px}.action-text p{margin-bottom:8px}.source{font-size:12px;color:var(--muted);overflow-wrap:anywhere;white-space:normal}.source a{display:inline}.below{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}.stack{margin-top:22px}details{margin-top:15px}summary{cursor:pointer;font-size:13px;font-weight:600;padding:7px 0}details p{font-size:13px}.image-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.image-grid button{padding:3px;border:1px solid var(--line);background:white}.image-grid img{width:100%;height:140px;object-fit:contain}.quote{border-left:2px solid #b5c8c1;padding-left:12px}.sources-list{list-style:none;padding:0}.sources-list li{padding:8px 0;border-bottom:1px solid var(--line)}footer{border-top:1px solid var(--line);margin-top:26px;padding-top:17px;color:var(--muted);font-size:12px}footer p{max-width:1050px}.profile-image{width:100%;max-height:760px;object-fit:contain;cursor:zoom-in}dialog{max-width:95vw;width:1200px;max-height:94vh;border:1px solid var(--line);border-radius:10px;padding:18px}dialog::backdrop{background:#152a32b5}dialog img{width:100%;max-height:80vh;object-fit:contain}dialog .close{float:right;padding:6px 13px;background:#fff;border:1px solid var(--line);border-radius:5px}.empty{padding:40px 20px;text-align:center;color:var(--muted)}[hidden]{display:none!important}:focus-visible{outline:3px solid #c6ab62;outline-offset:3px}.profile-stats{display:flex;gap:25px;margin:14px 0}.profile-stats b{font-size:22px;font-weight:600}.profile-stats span{font-size:12px;display:block;color:var(--muted)}@media(max-width:1000px){.split{grid-template-columns:minmax(0,1fr)}.action-photo img{max-height:300px}.below{grid-template-columns:1fr}}@media(max-width:650px){header,main{padding-left:18px;padding-right:18px}.topline{align-items:start}.toolbar{align-items:start;flex-direction:column}.panel{padding:16px}.navigation button{padding-left:9px;padding-right:9px}.navigation button span{display:none}.timeline{font-size:11px}.chart{height:300px}.small.version{max-width:145px;text-align:right}.profile-stats{gap:16px}.image-grid{grid-template-columns:1fr}}
</style></head><body>
<header><div class="topline"><div class="eyebrow">Inteplast / Data Explorer</div><div class="small version">Prototipo de consulta · 3212 Pump Housing</div></div>
<h1>Del retoque al resultado</h1><p>Qué se midió, qué se propuso y qué ocurrió en la siguiente medición. Las previsiones se conservan tal como aparecen en el Excel.</p>
<div class="timeline"><span><b>01</b> · Medición inicial</span><span class="event">→ Corrección 1 · 24 ene 2024 →</span><span><b>03</b> · Nueva medición</span><span class="event">→ Corrección 2 · 18 mar 2024 →</span><span><b>05</b> · Nueva medición</span><span>→ <b>08</b> · Seguimiento</span></div></header>
<main><nav class="navigation" aria-label="Casos de corrección" id="navigation"></nav>
<div class="toolbar"><div><div class="eyebrow" id="case-meta"></div><h2 id="case-title"></h2></div><div class="controls"><label id="variant-wrap" hidden>Elemento<select id="variant"></select></label><label>Cavidad<select id="cavity"></select></label></div></div>
<div id="case-view"><div class="split"><section class="panel"><h3>Antes, previsto y después</h3><p class="caption" id="limits"></p><div id="main-chart" class="chart" aria-label="Comparación de medidas y previsión"></div><div class="table-scroll" id="comparison-table"></div><div id="conclusion" aria-live="polite"></div><div id="warnings"></div></section>
<aside class="panel"><div class="eyebrow" id="action-label"></div><h3 style="margin-top:8px">La propuesta de retoque</h3><p id="description" class="action-text"></p><div id="action-main"></div><details><summary>Texto, imágenes y acciones relacionadas</summary><div id="action-evidence"></div></details><p class="caption">Una propuesta o un marcador «OK» no acreditan por sí solos la ejecución. El resultado posterior puede incluir otros efectos.</p></aside></div>
<div class="below"><section class="panel"><h3>Evolución de la cavidad</h3><p class="caption">Medidas observadas en los cuatro muestreos. Franja verde: intervalo admisible.</p><div id="history-chart" class="chart short"></div></section><section class="panel"><h3>Las cuatro cavidades después</h3><p class="caption">Misma evaluación y mismo muestreo. Un punto representa un resultado, no una distribución de piezas.</p><div id="cavities-chart" class="chart short"></div></section></div>
<section id="local-panel" class="panel stack" hidden><h3>N165 · 60 secciones locales</h3><p class="caption">Mínimo y máximo de cada sección antes y después de la corrección 2. La numeración de sección no presupone un ángulo de orientación.</p><div id="local-chart" class="chart tall"></div><details><summary>Otra evaluación: bloque N165 MIN/MAX</summary><div id="scan-table" class="table-scroll"></div><p class="caption">Este bloque no es GLOBAL. Su resultado no se usa para comparar la previsión del Excel.</p></details></section>
<section class="panel stack"><h3>Procedencia y alcance</h3><p id="case-note" class="caption"></p><details><summary>Archivos, celdas y filas utilizados</summary><ul class="sources-list" id="sources"></ul></details><details><summary>Nubes de apoyo del muestreo posterior</summary><div id="support"></div><p class="caption">PUNTS_NOUS es un subconjunto de PUNTS. No consta su vínculo a una acción ni que sea geometría objetivo.</p></details></section></div>
<div id="profile-view" hidden><div class="split"><section class="panel"><h3>Contorno interior · evidencia complementaria</h3><p class="caption">Perfiles A y B, seis contornos por familia. No son los datums A/B. No está confirmado el N-number asociado ni la acción responsable de los cambios.</p><div class="controls"><label>Muestreo<select id="profile-sample"><option value="01">intern.01</option><option value="03">intern.03</option><option value="05">intern.05</option><option value="08">intern.08 · sin PDF</option></select></label><label>Perfil y contorno<select id="profile-element"></select></label></div><div id="profile-details"></div><div id="profile-chart" class="chart"></div><p class="caption">Media del peor exceso absoluto de cada uno de los doce PDF de esta cavidad, en mm. La ausencia de informes se muestra como un hueco.</p><div id="profile-source"></div></section><section class="panel" id="profile-original"></section></div></div>
<footer><p>Fuentes originales del 3212, leídas en modo consulta. Las correspondencias entre acciones, celdas y evaluaciones se han revisado para esta pieza. Las previsiones no son mediciones ni simulaciones recalculadas. El plano disponible es rev.07, mientras los informes citan rev.06; el mapeo completo del plano queda pendiente.</p><a href="datos.json" download>Descargar datos y procedencia de esta vista</a> · <span id="inventory"></span></footer></main>
<dialog id="image-dialog"><button class="close" id="close-dialog">Cerrar</button><p id="image-caption" class="caption"></p><img id="dialog-image" alt="Imagen original ampliada"></dialog>
<script id="dataset" type="application/json">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('dataset').textContent);
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>v==null?'—':Number(v).toLocaleString('es-ES',{minimumFractionDigits:3,maximumFractionDigits:3});
const signed=v=>v==null?'—':(v>0?'+':'')+fmt(v), val=r=>r?.value??null;
const stateName={inside:'Dentro',outside:'Fuera',unknown:'Sin evaluar'}, colors=['#117966','#7759a6'];
let selected='N161', variant='main';
const cfg={displayModeBar:false,responsive:true};
const layout=(extra={})=>({font:{family:'Segoe UI, Arial, sans-serif',size:12,color:'#395052'},paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:63,r:18,t:25,b:64},legend:{orientation:'h',y:-0.22,x:0},yaxis:{title:{text:'mm'},gridcolor:'#e5ebe7',zeroline:false},xaxis:{gridcolor:'#edf0ed',zeroline:false},...extra});
function band(lo,hi){return lo==null||hi==null?[]:[{type:'rect',xref:'paper',x0:0,x1:1,y0:lo,y1:hi,line:{width:0},fillcolor:'#dbeedf',opacity:.75,layer:'below'}]}
function plot(id,traces,lo,hi,extra={}){return Plotly.react($(id),traces,layout({shapes:band(lo,hi),...extra}),cfg)}
function sourceHtml(s){return s?`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.path)}</a><br><span>${esc(s.locator)}</span>`:'Fuente no disponible'}
function imageButton(img,cls='action-photo'){return `<button class="${cls}" data-image="${esc(img.url)}" data-caption="${esc(img.label)}" aria-label="Ampliar ${esc(img.label)}"><img src="${esc(img.url)}" alt="${esc(img.label)}" loading="lazy"></button>`}
function cell(v,state){return `${fmt(v)}<span class="state ${state??'unknown'}">${stateName[state??'unknown']}</span>`}
function current(cavity=$('cavity').value){return data.cases[selected].comparisons[variant][cavity]}
function render(){
 document.querySelectorAll('#navigation button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.case===selected)));
 const isProfile=selected==='profiles';$('case-view').hidden=isProfile;$('profile-view').hidden=!isProfile;$('variant-wrap').hidden=selected!=='N170';
 if(isProfile){$('case-meta').textContent='Perfiles A/B';$('case-title').textContent='La forma del contorno interior';renderProfile();return}
 const def=data.cases[selected],corr=data.corrections[def.correction],cmp=current(),items=cmp.items,lo=items[0]?.lower,hi=items[0]?.upper;
 $('case-meta').textContent=`${selected} · Corrección ${def.correction} · ${corr.date}`;$('case-title').textContent=def.title;
 $('limits').textContent=`Límites de referencia: ${fmt(lo)} a ${fmt(hi)} mm. La previsión del Excel se dibuja con un rombo abierto.`;
 $('description').textContent=def.description;$('action-label').textContent=`Acciones ${def.actions.join(' + ')}`;$('case-note').textContent=def.note;
 plot('main-chart',items.map((item,i)=>({name:item.label,x:[`Antes · ${corr.before}`,'Previsión XLS',`Después · ${corr.after}`],y:[val(item.before),item.prediction,val(item.after)],mode:'lines+markers',connectgaps:false,line:{color:colors[i],width:2},marker:{size:10,symbol:['circle','diamond-open','circle'],color:colors[i]},hovertemplate:'%{x}<br>%{y:.3f} mm<extra>'+esc(item.label)+'</extra>'})),lo,hi);
 $('comparison-table').innerHTML=`<table><thead><tr><th>Evaluación</th><th>Antes</th><th>Previsto</th><th>Después</th><th>Δ observado</th><th>Real − previsto</th></tr></thead><tbody>${items.map(item=>`<tr><td>${esc(item.label)}</td><td>${cell(val(item.before),item.before?.status)}</td><td>${cell(item.prediction,item.prediction_status)}</td><td>${cell(val(item.after),item.after?.status)}</td><td>${signed(val(item.after)!=null&&val(item.before)!=null?val(item.after)-val(item.before):null)}</td><td>${signed(val(item.after)!=null&&item.prediction!=null?val(item.after)-item.prediction:null)}</td></tr>`).join('')}</tbody></table>`;
 const known=items.filter(i=>i.after?.status&&i.after.status!=='unknown'),outside=known.filter(i=>i.after.status==='outside');
 const predictionOutside=items.filter(i=>i.prediction_status==='outside').length;
 $('conclusion').innerHTML=`<div class="insight ${outside.length?'issue':''}"><strong>${known.length!==items.length?'Faltan resultados para evaluar el conjunto.':outside.length?`${outside.length} de ${items.length} evaluaciones posteriores siguen fuera.`:'Las evaluaciones posteriores mostradas están dentro.'}</strong><br><span class="caption">${predictionOutside?`${predictionOutside} evaluaciones ya quedaban fuera en la previsión. `:''}Este resultado corresponde a ${esc($('cavity').value)}${variant!=='main'?' · '+esc(variant):''}; no acredita la aceptación de toda la pieza.</span></div>`;
 $('warnings').innerHTML=cmp.warnings.map(w=>`<div class="issue-text">${esc(w)}</div>`).join('');
 const action=data.actions[def.actions[0]],img=action.images[0];
 $('action-main').innerHTML=(img?imageButton(img):'')+`<div class="source">${sourceHtml(action.source)}</div><details><summary>Pasos de la previsión guardada</summary>${items.map(item=>`<p><b>${esc(item.label)}</b>: ${fmt(item.xls_before)} ${item.steps.map(s=>`→ ${signed(s.delta)} = ${fmt(s.value)} mm <span class="caption">(${esc(s.cells)})</span>`).join(' ')}</p>`).join('')}</details>`;
 $('action-evidence').innerHTML=def.actions.map(id=>{const a=data.actions[id];return `<h4>Acción ${esc(id)}</h4><div class="quote">${a.paragraphs.map(p=>`<p>${esc(p)}</p>`).join('')}</div><p class="caption">Marcador original: ${esc(a.marker)}. Ejecución no confirmada por este marcador.</p><div class="image-grid">${a.images.map(i=>imageButton(i,'')).join('')}</div><p class="source">${sourceHtml(a.source)}</p>`}).join('');
 plot('history-chart',items.map((item,i)=>({name:item.label,x:data.samples.map(s=>'intern.'+s),y:item.history.map(val),mode:'lines+markers',connectgaps:false,line:{color:colors[i],width:2},marker:{size:7},hovertemplate:'%{x}<br>%{y:.3f} mm<extra>'+esc(item.label)+'</extra>'})),lo,hi);
 plot('cavities-chart',items.map((item,i)=>({name:item.label,x:data.cavities,y:data.cavities.map(c=>val(current(c).items[i].after)),mode:'markers',marker:{size:10,color:colors[i],symbol:i?'diamond':'circle'},hovertemplate:'%{x}<br>%{y:.3f} mm<extra>'+esc(item.label)+'</extra>'})),lo,hi);
 $('sources').innerHTML=items.map(item=>`<li><b>${esc(item.label)} · Excel</b><div class="source">${sourceHtml(item.source)}</div></li><li><b>Medición inicial</b><div class="source">${sourceHtml(item.before?.source)}</div></li><li><b>Medición posterior</b><div class="source">${sourceHtml(item.after?.source)}</div></li>`).join('');
 const supports=data.support.filter(s=>s.cavity===$('cavity').value&&s.sample===corr.after);
 $('support').innerHTML=supports.length?`<ul class="sources-list">${supports.map(s=>`<li><b>${esc(s.kind)}</b>${s.kind==='PUNTS_NOUS'?` · ${s.points} puntos · ${s.subset_verified?'coincide con el final de PUNTS':'no se ha verificado la igualdad'}`:''}<div class="source">${sourceHtml(s.source)}</div></li>`).join('')}</ul>`:'<p>Sin archivos de soporte para esta selección.</p>';
 $('local-panel').hidden=selected!=='N165';if(selected==='N165')renderLocal();
}
function renderLocal(){
 const cav=$('cavity').value,traces=[];
 for(const [s,color] of [['03','#b16a29'],['05','#117966']])for(let i=0;i<2;i++)traces.push({name:`${s} · ${i?'máximo':'mínimo'}`,x:Array.from({length:60},(_,j)=>j+1),y:data.sections[cav][s].map(pair=>val(pair[i])),mode:'lines',line:{color,width:2,dash:i?'solid':'dot'},connectgaps:false});
 plot('local-chart',traces,1.30,1.35,{xaxis:{title:{text:'Sección'},dtick:10,gridcolor:'#edf0ed'}});
 $('scan-table').innerHTML=`<table><thead><tr><th>Evaluación</th>${data.samples.map(s=>`<th>intern.${s}</th>`).join('')}</tr></thead><tbody>${[0,1].map(i=>`<tr><td>${i?'Máximo':'Mínimo'}</td>${data.samples.map(s=>`<td>${cell(val(data.scan[cav][s][i]),data.scan[cav][s][i]?.status)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function renderProfile(){
 const cav=$('cavity').value,sample=$('profile-sample').value,el=$('profile-element').value;
 const p=data.profiles.find(p=>p.cavity===cav&&p.sample===sample&&p.element===el);
 const values=data.samples.map(s=>{const group=data.profiles.filter(p=>p.cavity===cav&&p.sample===s);return group.length===12&&group.every(p=>p.excess!=null)?group.reduce((sum,p)=>sum+p.excess,0)/12:null});
 plot('profile-chart',[{name:'Media del peor exceso',x:data.samples.map(s=>'intern.'+s),y:values,mode:'lines+markers',connectgaps:false,line:{color:'#117966',width:2},marker:{size:8}}],null,null,{showlegend:false,yaxis:{title:{text:'Exceso (mm)'},rangemode:'tozero',gridcolor:'#e5ebe7'}});
 if(!p){$('profile-details').innerHTML='<p class="empty">No hay PDF de perfil para este muestreo y cavidad. Estado sin evaluar.</p>';$('profile-original').innerHTML='<p class="empty">Sin informe original disponible.</p>';$('profile-source').innerHTML='';return}
 $('profile-details').innerHTML=`<div class="profile-stats"><div><b>${fmt(p.excess)}</b><span>Peor exceso · mm</span></div><div><b>${p.excess==null?'Sin evaluar':p.excess>0?'Fuera':'Dentro'}</b><span>Estado del perfil</span></div></div><p class="caption">${esc(p.perfil_nombre)} · contorno ${esc(p.contorno)} frente a CONTORN ${esc(p.nominal)}. Banda: ${fmt(p.tol_inf)} a ${fmt(p.tol_sup)} mm.</p>${p.errors.length?`<p class="issue-text">${esc(p.errors.join('; '))}</p>`:''}`;
 $('profile-source').innerHTML=`<div class="source">${sourceHtml(p.source)}</div>`;
 $('profile-original').innerHTML=`<h3>${esc(p.element)} · intern.${esc(sample)} · ${esc(cav)}</h3><button class="action-photo" data-image="${esc(p.image)}" data-caption="${esc(p.source.path)}" aria-label="Ampliar informe de perfil"><img class="profile-image" src="${esc(p.image)}" alt="Informe original de comparación de perfil"></button>`;
}
const names={N161:'Diámetro interior',N240:'Distancia',N170:'Bolt Eye',N165:'Espesor local',profiles:'Contorno interior'};
$('navigation').innerHTML=Object.entries(names).map(([id,name])=>`<button type="button" data-case="${id}" aria-pressed="false">${id==='profiles'?'Perfiles A/B':id}<span>${name}</span></button>`).join('');
$('cavity').innerHTML=data.cavities.map(c=>`<option value="${c}">${c.toUpperCase()}</option>`).join('');
$('profile-element').innerHTML=['PA','PB'].flatMap(p=>Array.from({length:6},(_,i)=>`${p}_${i+1}`)).map(p=>`<option>${p}</option>`).join('');
$('variant').innerHTML=data.cases.N170.variants.map(v=>`<option value="${v}">${v.replace('-H',' · H=')} mm</option>`).join('');
$('navigation').addEventListener('click',e=>{const b=e.target.closest('[data-case]');if(!b)return;selected=b.dataset.case;variant=selected==='N170'?$('variant').value:'main';render()});
for(const id of ['cavity','variant','profile-sample','profile-element'])$(id).addEventListener('change',()=>{if(id==='variant')variant=$('variant').value;render()});
document.addEventListener('click',e=>{const b=e.target.closest('[data-image]');if(!b)return;$('dialog-image').src=b.dataset.image;$('image-caption').textContent=b.dataset.caption;$('image-dialog').showModal()});
$('close-dialog').addEventListener('click',()=>$('image-dialog').close());
$('image-dialog').addEventListener('click',e=>{if(e.target===$('image-dialog'))$('image-dialog').close()});
$('inventory').textContent=`${data.csv_count} CSV · ${data.profiles.length} PDF de perfil · 2 planes de corrección`;
render();
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", type=Path, default=ROOT, help="Carpeta 3212 Pump Housing")
    parser.add_argument("--salida", type=Path, default=OUTPUT, help="Carpeta exclusiva de este prototipo")
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()
    root, destination = args.raiz.resolve(), args.salida.resolve()
    # Protect source originals and the existing ver_todo index, even with a custom output.
    if destination == root or root in destination.parents:
        parser.error("La salida debe estar fuera de los datos originales")
    if destination == OUTPUT.parent.resolve():
        parser.error("Usar una subcarpeta propia; no sobrescribir out/index.html de ver_todo")
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    print("Leyendo CSV, previsiones XLS y acciones PPTX...", flush=True)
    data = build_data(root, assets)
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
    (destination / "datos.json").write_text(encoded, encoding="utf-8")
    (assets / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    page = destination / "index.html"
    page.write_text(PAGE.replace("__DATA__", encoded.replace("<", "\\u003c").replace("&", "\\u0026")), encoding="utf-8")
    print(f"Prototipo: {page}")
    print(f"{data['csv_count']} CSV; {len(data['profiles'])} perfiles; {len(data['actions'])} acciones; 4 casos.")
    if not args.no_abrir:
        webbrowser.open(page.as_uri())


if __name__ == "__main__":
    main()
