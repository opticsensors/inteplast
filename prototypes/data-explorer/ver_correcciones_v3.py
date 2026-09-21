"""Catalogo de cotas y comparacion visual de perfiles del 3212 Pump Housing.

    py -3.11 prototypes/data-explorer/ver_correcciones_v3.py
    py -3.11 prototypes/data-explorer/ver_correcciones_v3.py --no-abrir

Reutiliza los lectores y correspondencias revisados de ver_correcciones.py.
Lee los originales en modo consulta y genera out/correcciones-3212-v3/index.html.
No cambia los scripts ni las salidas anteriores. Requiere las dependencias de v1.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import posixpath
import re
import webbrowser
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import fitz
from plotly.offline import get_plotlyjs

from ver_correcciones import (
    ROOT, OUTPUT as V1_OUTPUT, CORRECTIONS, NS, build_data as build_base_data,
    csv_identity, number, result, source, ver_csv,
)


OUTPUT = Path(__file__).resolve().parent / "out" / "correcciones-3212-v3"

# Explicit links already reviewed in PPTX images; not inferred from a later measurement.
REVIEWED_ACTION_LINKS = {
    "1.16": ["N155", "N258", "N267", "N268"],
    "1.17": ["N154", "N165", "N166", "N167"],
    "1.18": ["N236", "N237", "N240", "N241", "N252", "N256"],
    "2.3": ["N154", "N155", "N258", "N267", "N268"],
    "2.4": ["N165", "N166", "N167"],
    "2.5": ["N236", "N237", "N240", "N241", "N252", "N256"],
    "2.13": ["N240"],
}


def dimension_ids(block: str) -> list[str]:
    """Keep joint headers together; N116/260 + N258 is not one interchangeable measure."""
    found = []
    for match in re.finditer(r"\bN(\d{3})((?:\s*/\s*\d{3})*)", block):
        found.extend("N" + n for n in re.findall(r"\d{3}", match.group(0)))
    return list(dict.fromkeys(found))


def catalog_group(block: str) -> tuple[str, list[str], str]:
    if block.startswith(("POINT ", "GLOBAL ")):
        return "N165", ["N165"], "dimension"
    ids = dimension_ids(block) if block.startswith("N") else []
    if ids:
        return "/".join(ids), ids, "dimension"
    return "COORD:" + block, [], "diagnostic"


def action_dimension_ids(title: str) -> list[str]:
    """Read every DIM. Nr. field, without mistaking nominal values for identifiers."""
    fields = re.findall(r"\bDIM\.?\s*Nr\.?\s*(N?\d{3}(?!\d)(?:\s*[/,;&]\s*N?\d{3}(?!\d))*)",
                        title, re.IGNORECASE)
    return list(dict.fromkeys("N" + n for field in fields for n in re.findall(r"\d{3}", field)))


def load_catalog(root: Path, actions: dict, reviewed_cases: dict) -> dict:
    entries, seen, row_count = {}, set(), 0
    for file in ver_csv.descubrir(root / "4- Metrologia"):
        sample, cavity = file["muestreo"], file["cavidad"]
        if (sample, cavity) in seen:
            raise ValueError(f"CSV duplicado: {sample}/{cavity}")
        seen.add((sample, cavity))
        table = ver_csv.corregir_signo(ver_csv.leer_csv_cavidad(file["ruta"]))
        element, previous = "", None
        for row in table.to_dict("records"):
            block, idx = row["bloque"].strip(), int(row["idx"])
            group = (block, row["ocurrencia"])
            if group != previous:
                element, previous = "", group
            element = row["id_cmm"] or element
            key, ids, kind = catalog_group(block)
            entry = entries.setdefault(key, {"id": key, "numbers": ids, "kind": kind,
                                             "title": block, "series": {}, "actions": []})
            identity = csv_identity(row, element) if block.startswith("N170") else None
            series_key = "|".join(map(str, identity)) if identity else f"{block}|{row['ocurrencia']}|{idx}"
            label = f"{block} · [{idx}] {row['caracteristica']}"
            if identity:
                label = f"{identity[1]} · {'GX' if idx == 1 else 'LP máximo'}"
            unit = "°" if str(row["caracteristica"]).startswith("Phi") else "mm"
            series = entry["series"].setdefault(series_key, {"id": series_key, "label": label,
                "unit": unit, "records": {}, "block": block, "idx": idx})
            if sample in series["records"].get(cavity, {}):
                raise ValueError(f"Evaluación duplicada: {key}/{series_key}/{cavity}/{sample}")
            nominal, low, high, measured = (number(row[k]) for k in ("nominal", "tol_inf", "tol_sup", "medido"))
            lower = nominal + low if nominal is not None and low is not None else None
            upper = nominal + high if nominal is not None and high is not None else None
            series["records"].setdefault(cavity, {})[sample] = {
                "value": measured, "lower": lower, "upper": upper, "status": result(measured, lower, upper),
                "reported_nok": bool(row["nok_original"]), "corrected": bool(row["signo_corregido"]),
                "original_value": number(row["medido_original"]),
                "source": source(file["ruta"], root, f"{block} · aparición {row['ocurrencia']} · fila {idx} · CMM {element or '—'}"),
            }
            row_count += 1
    for entry in entries.values():
        entry["actions"] = [a["id"] for a in actions.values() if set(entry["numbers"]) & set(a["features"])]
        entry["reviewed_case"] = entry["id"] if entry["id"] in reviewed_cases else None
        series = list(entry["series"].values())
        if entry["id"] == "N165":
            series.sort(key=lambda s: (0 if s["block"].startswith("GLOBAL") else 1 if s["block"].startswith("N165") else 2,
                                       int(re.search(r"POINT\s+(\d+)", s["block"])[1]) if s["block"].startswith("POINT") else 0, s["idx"]))
        entry["series"] = series
    return {"entries": sorted(entries.values(), key=lambda e: (e["kind"] != "dimension", e["id"])),
            "row_count": row_count, "files": len(seen)}


def extract_action_index(root: Path, assets: Path) -> dict:
    """Extract all plan slides; associate DIM.Nr. titles or previously reviewed image links."""
    actions = {}
    for plan_id, correction in CORRECTIONS.items():
        path = root / correction["pptx"]
        with zipfile.ZipFile(path) as archive:
            names = sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                           key=lambda n: int(re.search(r"(\d+)\.xml", n)[1]))
            for physical, name in enumerate(names, 1):
                xml = ET.fromstring(archive.read(name))
                paragraphs = ["".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
                              for p in xml.findall(".//a:p", NS)]
                titles = [p for p in paragraphs if re.search(r"Tool\s+correction\s+\d+\.\d+", p)]
                if len(titles) != 1:
                    raise ValueError(f"Título de acción ambiguo: {path.name}/{name}")
                title = titles[0]
                action_id = re.search(r"Tool\s+correction\s+(\d+\.\d+)", title)[1]
                features = action_dimension_ids(title)
                method = "DIM. Nr. del título"
                if action_id in REVIEWED_ACTION_LINKS:
                    features, method = REVIEWED_ACTION_LINKS[action_id], "Imágenes revisadas del PPTX"
                rels = ET.fromstring(archive.read(posixpath.join(posixpath.dirname(name), "_rels", posixpath.basename(name) + ".rels")))
                targets = {r.attrib["Id"]: r.attrib for r in rels}
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
                    filename = "slide-" + hashlib.sha256(blob).hexdigest()[:20] + Path(target).suffix.lower()
                    (assets / filename).write_bytes(blob)
                    images.append({"url": "assets/" + filename, "label": f"Acción {action_id}"})
                actions[action_id] = {"id": action_id, "plan": plan_id, "title": title,
                    "features": list(dict.fromkeys(features)), "link_method": method if features else "Sin asociación",
                    "paragraphs": [p for p in paragraphs if p], "images": images,
                    "source": source(path, root, f"Acción {action_id} · diapositiva {physical}")}
    return actions


def profile_crop(page) -> fitz.Rect:
    """Locate the plot's white vector frame, not a pixel crop of the full-page thumbnail."""
    frames = [d["rect"] for d in page.get_drawings()
              if d.get("fill") and min(d["fill"]) > .98
              and d["rect"].width > .6 * page.rect.width
              and .2 * page.rect.height < d["rect"].height < .6 * page.rect.height]
    if len(frames) != 1:
        raise ValueError(f"No se identifica de forma única el marco del perfil: {len(frames)} candidatos")
    r = frames[0]
    return fitz.Rect(r.x0 - 8, r.y0 - 8, r.x1 + 8, r.y1 + 8) & page.rect


def build_data(root: Path, assets: Path) -> dict:
    data = build_base_data(root, assets)
    print("Recortando las gráficas vectoriales de los perfiles...", flush=True)
    for profile in data["profiles"]:
        with fitz.open(root / profile["source"]["path"]) as doc:
            page = doc[0]
            clip = profile_crop(page)
            filename = f"grafica-{profile['sample']}-{profile['cavity']}-{profile['element']}.png"
            page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False).save(assets / filename)
            profile.update(crop_image="assets/" + filename, crop_rect=list(clip), crop_method="Marco vectorial del gráfico + 8 pt")
    print("Catalogando todas las evaluaciones CSV y acciones PPTX...", flush=True)
    data["action_index"] = extract_action_index(root, assets)
    data["catalog"] = load_catalog(root, data["action_index"], data["cases"])
    return data

PAGE = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="correcciones-version" content="3">
<title>3212 · Correcciones de molde · Inteplast</title>
<script src="assets/plotly.min.js"></script>
<style>
:root{--ink:#162f40;--muted:#6f7e88;--line:#dfe6e9;--bg:#f3f6f8;--paper:#fff;--accent:#087d85;--blue:#2773b6;--violet:#8b5aa9;--ok:#18765c;--ok-bg:#eaf4ee;--bad:#b2473e;--bad-bg:#fcf0ed;--warning:#916314;--radius:14px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 "Segoe UI",Arial,sans-serif;font-variant-numeric:tabular-nums}button,select{font:inherit;color:inherit}button{cursor:pointer}button,a,select{-webkit-tap-highlight-color:transparent;touch-action:manipulation}button{border:0}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #48a9b3;outline-offset:3px}[hidden]{display:none!important}h1,h2,h3,p{margin:0}h1{font-size:30px;font-weight:600;letter-spacing:-1px}h2{font-size:17px;font-weight:600}h3{font-size:14px;font-weight:600}.muted{color:var(--muted)}.small{font-size:12px}.eyebrow{font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--muted)}
.topbar{height:72px;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 32px;gap:20px}.brand{font-size:19px;font-weight:700;letter-spacing:2px}.brand span{color:#70c5cb}.project{display:flex;align-items:center;gap:14px}.project b{font-size:20px;font-weight:600}.project span{color:#afc0cb;font-size:13px}.top-actions{display:flex;align-items:center;gap:16px}.top-actions .version{font-size:11px;color:#afc0cb;letter-spacing:1px}.icon-btn{border:1px solid #ffffff35;background:transparent;color:white;padding:7px 10px;border-radius:6px;line-height:1}
.workspace{display:grid;grid-template-columns:205px minmax(0,1fr);max-width:1720px;margin:auto;min-height:calc(100vh - 72px)}.sidebar{padding:32px 18px;border-right:1px solid var(--line)}.sidebar-title{padding:0 12px;margin-bottom:18px}.case-nav{display:flex;flex-direction:column;gap:8px}.case-tab{text-align:left;padding:14px 13px;background:transparent;border:1px solid transparent;border-radius:10px;transition:background .15s}.case-tab:hover{background:#e9eff2}.case-tab[aria-current=true]{background:white;border-color:var(--line);box-shadow:0 3px 12px #17354807}.case-tab .code{display:flex;align-items:center;justify-content:space-between;font-size:18px;font-weight:650}.case-tab[aria-current=true] .code{color:var(--accent)}.case-tab .desc{display:block;font-size:12px;color:var(--muted);margin-top:3px}.case-tab .plan-tag{font-size:10px;font-weight:600;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:2px 4px}.sidebar-rule{border-top:1px solid var(--line);margin:24px 12px 18px}.sidebar-foot{margin:30px 12px;color:var(--muted);font-size:11px}.sidebar-foot b{font-weight:600;color:var(--ink)}
main{padding:26px 30px 36px;min-width:0}.page-heading{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:18px}.heading-left .eyebrow{margin-bottom:4px}.heading-right{display:flex;align-items:center;gap:14px}.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:6px;font-size:12px;font-weight:600;white-space:nowrap}.pill:before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor}.inside{color:var(--ok)}.outside{color:var(--bad)}.unknown{color:var(--muted)}.pill.inside{background:var(--ok-bg)}.pill.outside{background:var(--bad-bg)}.pill.unknown{background:#edf0f2}.button{background:white;border:1px solid var(--line);border-radius:7px;padding:8px 12px;font-size:12px;font-weight:600}.button:hover{border-color:#8ea9b5}.button[aria-pressed=true]{border-color:var(--accent);color:var(--accent);background:#edf7f7}
.filters{display:flex;gap:24px;flex-wrap:wrap;align-items:center;margin-bottom:20px}.filter{display:flex;gap:9px;align-items:center}.filter-label{font-size:11px;color:var(--muted)}.segmented{display:inline-flex;background:#e8edf0;padding:3px;border-radius:7px;gap:2px}.segmented button{background:transparent;border-radius:5px;padding:5px 11px;font-size:12px;min-width:42px}.segmented button[aria-pressed=true]{background:white;color:var(--accent);box-shadow:0 1px 4px #243b4812;font-weight:700}.status-line{margin-left:auto;display:flex;align-items:center;gap:9px;font-size:12px}.status-line .small{border-left:1px solid var(--line);padding-left:9px}
.hero{display:grid;grid-template-columns:minmax(260px,.86fr) minmax(0,1.85fr);gap:18px}.panel{border:1px solid var(--line);background:white;border-radius:var(--radius);min-width:0;overflow:hidden}.panel-head{padding:18px 20px 0;display:flex;align-items:start;justify-content:space-between;gap:10px}.panel-head h2{margin-top:3px}.action-panel{display:flex;flex-direction:column}.action-meta{display:flex;align-items:center;justify-content:space-between;width:100%;gap:12px}.action-meta .eyebrow{color:var(--accent)}.action-title{font-size:18px;padding:10px 20px 0;letter-spacing:-.3px;min-height:40px}.action-image{border:0;padding:12px 20px;background:#fff;display:block;position:relative;flex:1;min-height:200px;width:100%}.action-image img{width:100%;height:225px;object-fit:contain;display:block}.enlarge{position:absolute;right:15px;bottom:12px;color:var(--muted);background:#ffffffed;border:1px solid var(--line);border-radius:5px;padding:3px 6px;font-size:12px}.image-tabs{display:flex;justify-content:center;gap:6px;padding:3px 20px 13px;min-height:31px}.image-tabs button{height:6px;width:22px;border-radius:3px;background:#dce5e9;padding:0}.image-tabs button[aria-pressed=true]{background:var(--accent)}.action-bottom{padding:13px 20px 17px;border-top:1px solid #edf1f3}.action-switch{display:flex;gap:6px;margin-bottom:9px;flex-wrap:wrap}.action-switch button{font-size:11px;padding:4px 7px;border-radius:4px;border:1px solid var(--line);background:#fff}.action-switch button[aria-pressed=true]{color:var(--accent);border-color:#a2cccc;background:#f0f8f8}.delta-plan{display:flex;align-items:baseline;justify-content:space-between;gap:8px}.delta-plan b{font-size:22px;font-weight:600;letter-spacing:-.7px}.delta-plan .formula{font-size:12px;color:var(--muted);margin-top:1px}.delta-plan .unit{font-size:11px;font-weight:400;margin-left:3px;letter-spacing:0}.chart-panel{position:relative;display:flex;flex-direction:column}.chart-panel .history-chart{flex:1;min-height:280px}.chart-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:18px 20px 0}.chart-head .button{font-size:11px;padding:5px 8px}.chart{height:300px;min-width:0}.history-chart{height:300px;overflow:hidden}.legend{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:5px 22px 15px;font-size:11px;color:var(--muted)}.legend span{display:inline-flex;gap:6px;align-items:center}.legend i{width:7px;height:7px;display:inline-block;background:var(--blue);border-radius:50%}.legend i.square{border-radius:1px;background:var(--violet)}.legend i.diamond{border-radius:0;transform:rotate(45deg);background:white;border:1.6px solid var(--ink)}.legend i.band{width:14px;height:8px;border-radius:1px;background:#dceee3}.legend .limits{margin-left:auto}.clipped{position:absolute;top:62px;right:20px;font-size:10px;color:var(--warning);background:#fff7e4;border-radius:4px;padding:2px 5px}
.results{margin-top:18px}.result-head{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}.result-head h2{font-size:14px}.result-table{width:100%;border-collapse:collapse}.result-table th,.result-table td{padding:11px 20px;text-align:right;white-space:nowrap}.result-table th{font-size:10px;color:var(--muted);font-weight:500;letter-spacing:.3px}.result-table th:first-child,.result-table td:first-child{text-align:left}.result-table th b{display:block;font-size:12px;color:var(--ink);font-weight:600}.result-table td{font-size:22px;font-weight:550;letter-spacing:-.5px}.result-table td:first-child{font-size:12px;letter-spacing:0;font-weight:600}.result-table tbody tr+tr{border-top:1px solid #edf1f3}.result-table .forecast{background:#f5f8fa;color:var(--ink)}.result-table td.delta{font-size:16px;color:var(--muted);font-weight:400}.result-table .state-mark{font-size:10px;vertical-align:middle;margin-left:5px}.table-scroll{overflow:auto}.data-warning{padding:10px 20px;background:#fff7e4;font-size:12px;color:#815616}
.detail-panel{margin-top:18px}.detail-header{display:flex;align-items:center;justify-content:space-between;padding:0 20px;border-bottom:1px solid var(--line);gap:12px}.detail-tabs{display:flex;gap:20px;overflow:auto}.detail-tabs button{padding:15px 0 13px;border-bottom:2px solid transparent;white-space:nowrap;background:transparent;font-size:12px;color:var(--muted)}.detail-tabs button[aria-selected=true]{border-color:var(--accent);color:var(--ink);font-weight:600}.detail-body{padding:18px 20px}.cavity-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.cavity-card{padding:12px;text-align:left;border:1px solid var(--line);border-radius:8px;background:white;min-width:0}.cavity-card.active{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}.cavity-card header{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:11px}.cavity-card header b{font-weight:650}.cavity-row{display:flex;justify-content:space-between;align-items:center;font-size:11px;gap:6px;margin-top:7px}.cavity-row strong{font-size:17px;font-weight:550}.bullet-chart{height:24px;margin:4px 0 8px;width:100%;display:block}.matrix{width:100%;border-collapse:collapse}.matrix th{font-size:11px;color:var(--muted);font-weight:500;padding:5px 12px;text-align:left}.matrix td{border-top:1px solid #edf1f3;padding:5px 9px}.matrix td:first-child{font-size:12px;white-space:nowrap}.matrix-button{width:100%;display:flex;align-items:center;justify-content:space-around;gap:8px;padding:7px 10px;border:1px solid transparent;background:#f8fafb;border-radius:5px;font-size:12px}.matrix-button.active{border-color:var(--accent);background:#f0f8f8}.matrix-value{display:flex;gap:5px;align-items:center}.matrix-value:before{content:"";height:5px;width:5px;border-radius:50%;background:currentColor}.matrix-value:last-child:before{border-radius:0}.matrix-legend{display:flex;gap:14px;font-size:11px;color:var(--muted);margin-bottom:9px}.detail-context{font-size:11px;color:var(--muted);white-space:nowrap}.local-chart{height:270px}.local-caption{display:flex;align-items:center;justify-content:space-between;font-size:11px;color:var(--muted)}
.profile-top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0 22px}.profile-top .family{display:flex;align-items:center;gap:4px;margin-right:12px}.family label{font-size:11px;color:var(--muted);margin-right:5px}.family button{border:1px solid var(--line);background:#fff;padding:7px 11px;border-radius:6px;font-size:12px}.family button[aria-pressed=true]{border-color:var(--accent);background:var(--accent);color:white}.profile-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.profile-card .panel-head{align-items:center;padding-bottom:12px}.profile-number{font-size:30px;letter-spacing:-1px;font-weight:550;line-height:1.2}.profile-card .profile-photo{display:block;width:100%;background:white;border-top:1px solid var(--line);padding:10px;position:relative}.profile-photo img{width:100%;height:290px;object-fit:contain;display:block}.profile-card .profile-source{padding:10px 16px;font-size:11px;border-top:1px solid var(--line);display:flex;justify-content:space-between}.profile-missing{display:flex;align-items:center;gap:12px;color:var(--muted);font-size:12px;padding:13px 18px;background:#eaf0f3;border:1px dashed #ccd8df;border-radius:8px;margin-top:18px}.profile-evolution{margin-top:18px}.profile-evolution .chart{height:235px}.empty{padding:48px 20px;text-align:center;color:var(--muted);font-size:13px}
footer{padding:19px 2px 0;display:flex;justify-content:space-between;align-items:center;gap:15px;color:var(--muted);font-size:10px}footer button{background:none;padding:0;color:var(--muted);font-size:10px;text-decoration:underline;text-underline-offset:3px}.dialog{padding:0;border:1px solid var(--line);border-radius:12px;max-height:92vh;color:var(--ink);box-shadow:0 25px 100px #0d293244}.dialog::backdrop{background:#142f40a6;backdrop-filter:blur(3px)}.dialog-header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:16px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:white;z-index:2}.dialog-header h2{font-size:16px}.close{background:#eef3f5;border-radius:6px;width:30px;height:30px;font-size:21px;line-height:1}.image-dialog{width:min(1250px,95vw);background:white}.image-dialog img{display:block;max-width:100%;width:auto;height:auto;max-height:78vh;object-fit:contain;margin:12px auto}.image-caption{padding:0 22px 15px;color:var(--muted);font-size:11px}.evidence-dialog{width:min(880px,94vw)}.evidence-body{padding:22px}.evidence-body details{border-bottom:1px solid var(--line);padding:10px 0}.evidence-body summary{cursor:pointer;font-size:13px;font-weight:600}.evidence-body p{margin:10px 0;font-size:12px;color:var(--muted)}.evidence-body ul{list-style:none;padding:0}.evidence-body li{padding:9px 0;font-size:12px;overflow-wrap:anywhere}.evidence-body li+li{border-top:1px solid #edf1f3}.source-path{font-size:11px}.image-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:12px 0}.image-grid button{padding:5px;background:white;border:1px solid var(--line);border-radius:6px}.image-grid img{height:100px;width:100%;object-fit:contain}.evidence-body .note{border-left:2px solid var(--accent);padding-left:12px}.evidence-body table{width:100%;font-size:12px;border-collapse:collapse}.evidence-body td,.evidence-body th{padding:7px;border-bottom:1px solid var(--line);text-align:right}.evidence-body td:first-child,.evidence-body th:first-child{text-align:left}
body.presenting .sidebar{display:none}body.presenting .workspace{grid-template-columns:minmax(0,1fr);max-width:1460px}body.presenting .version{display:none}body.presenting main{padding-top:20px}.present-nav{display:none;align-items:center;gap:8px}body.presenting .present-nav{display:flex}.present-nav button{background:#ffffff16;border:1px solid #ffffff22;color:white;border-radius:5px;font-size:12px;padding:5px 10px}.present-nav button[aria-pressed=true]{background:white;color:var(--ink)}
@media(min-width:1500px){.action-image img{height:260px}.history-chart{height:335px}.action-title{font-size:20px}}
@media(max-width:1150px){.workspace{grid-template-columns:165px minmax(0,1fr)}.sidebar{padding:24px 10px}main{padding:22px 20px}.hero{grid-template-columns:minmax(230px,.9fr) minmax(0,1.65fr)}.result-table th,.result-table td{padding-left:13px;padding-right:13px}.result-table td{font-size:20px}.heading-right{gap:8px}.profile-photo img{height:220px}.cavity-cards{gap:8px}.cavity-card{padding:9px}.cavity-row{font-size:10px}.cavity-row strong{font-size:15px}.legend{gap:10px}.legend .limits{margin-left:0}.topbar{padding:0 22px}}
@media(max-width:900px){.workspace{display:block}.sidebar{padding:12px 20px;border-right:0;border-bottom:1px solid var(--line)}.sidebar-title,.sidebar-rule,.sidebar-foot{display:none}.case-nav{flex-direction:row;gap:5px;overflow:auto}.case-tab{padding:8px 12px;flex-shrink:0}.case-tab .code{font-size:15px;gap:10px}.case-tab .desc{font-size:10px}.case-tab .plan-tag{display:none}.hero{grid-template-columns:minmax(210px,.8fr) minmax(0,1.5fr)}.top-actions .version{display:none}.project span{display:none}.filters{gap:12px}.status-line{margin-left:0}.cavity-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.present-nav{flex-wrap:wrap}.present-nav button{font-size:10px;padding:4px 6px}body.presenting .project{display:none}}
@media(max-width:650px){.topbar{height:60px;padding:0 16px}.brand{font-size:15px}.project b{font-size:17px}.top-actions{gap:6px}.page-heading{align-items:start;gap:12px}h1{font-size:23px}.heading-right .pill{display:none}.sidebar{padding:10px 12px}main{padding:18px 12px}.hero{display:flex;flex-direction:column}.action-panel{display:grid;grid-template-columns:1fr 1fr}.action-panel .panel-head{grid-column:1/3}.action-title{grid-column:1/3;min-height:0;font-size:17px}.action-image{grid-column:1;grid-row:3/5;padding:10px;min-height:140px}.action-image img{height:150px}.image-tabs{grid-column:1;grid-row:5;padding:4px 10px 12px}.action-bottom{grid-column:2;grid-row:3/6;border-top:0;padding:20px 12px 12px 0;display:flex;flex-direction:column;justify-content:center}.delta-plan{align-items:start;flex-direction:column}.history-chart{height:285px}.filters{gap:9px}.filter{gap:6px}.filter-label{font-size:10px}.segmented button{padding:5px 8px;min-width:35px}.status-line{width:100%;justify-content:space-between}.result-table th,.result-table td{padding:10px}.result-table td{font-size:19px}.result-table td.delta{font-size:14px}.result-table td:first-child{font-size:11px}.result-head{padding:12px}.detail-header{padding:0 12px}.detail-body{padding:12px}.detail-tabs{gap:13px}.detail-context{font-size:10px}.matrix th{padding:5px}.matrix td{padding:4px}.matrix-button{padding:7px 4px;gap:5px;flex-direction:column;align-items:start;font-size:11px}.matrix td:first-child{font-size:11px}.profile-strip{grid-template-columns:1fr}.profile-photo img{height:340px}.family button{padding:6px 9px}.image-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.topbar .present-nav{display:none}body.presenting .sidebar{display:block}body.presenting .project{display:flex}footer{align-items:start}.chart-head{padding-left:13px;padding-right:13px}.legend{padding-left:13px;padding-right:13px}.local-caption{gap:10px}}
@media print{.topbar{background:white;color:var(--ink)}.sidebar,.filters,.top-actions,.heading-right,.detail-header,.button,footer,.image-tabs{display:none!important}.workspace{display:block}main{padding:10px}.hero{grid-template-columns:1fr 2fr}.panel{break-inside:avoid}.result-table td{font-size:18px}.profile-strip{grid-template-columns:repeat(3,1fr)}body{background:white}}
</style>
<style>
.profile-map{margin:0 0 18px;padding:15px 18px}.profile-map-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}.profile-map-head h2{font-size:14px}.profile-map-table{display:grid;grid-template-columns:60px repeat(4,minmax(0,1fr));gap:5px 9px;align-items:center}.profile-map-table .axis{text-align:center;font-size:11px;color:var(--muted)}.profile-map-table .row-label{font-size:12px;font-weight:600}.map-cell{padding:7px 10px;border:1px solid transparent;border-radius:6px;text-align:center;font-size:17px;font-weight:600;line-height:1.2;position:relative}.map-cell.selected{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}.map-cell.reference{border:1px dashed #7f9ba5}.map-cell span{font-size:10px;font-weight:400;margin-left:5px}.map-cell.unknown{background:#f0f3f5}.profile-compare-head{display:flex;justify-content:space-between;align-items:center;margin:20px 1px 12px;gap:12px}.profile-compare-head h2{font-size:16px}.profile-change{font-size:13px;padding:5px 9px;border:1px solid var(--line);background:white;border-radius:6px}.profile-change strong{font-size:17px;margin-left:7px}.profile-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.profile-pair .profile-card .panel-head{align-items:start;padding:15px 18px}.sample-picker{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);margin-bottom:10px}.sample-picker select,.catalog-controls select,.catalog-metric select{background:white;border:1px solid var(--line);border-radius:6px;padding:6px 10px;font-size:12px;color:var(--ink);max-width:100%}.profile-card .profile-photo{padding:0;border-top:1px solid var(--line);background:#fff;overflow:hidden}.profile-card .profile-photo img{width:100%;height:auto;aspect-ratio:1.32;object-fit:contain}.profile-card .profile-source{padding:9px 16px;gap:10px;flex-wrap:wrap}.profile-card .profile-source b{font-weight:550;color:var(--ink)}.profile-card .empty{min-height:280px;display:grid;place-content:center}.profile-top{margin-bottom:16px}.profile-evolution .chart{height:185px}.profile-evolution details summary{padding:14px 18px;font-weight:600;font-size:13px;cursor:pointer}.profile-evolution .chart{min-height:185px}.catalog-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.catalog-search{flex:1;min-width:190px;background:white;border:1px solid var(--line);border-radius:7px;padding:10px 13px;font:inherit}.catalog-filters{display:flex;gap:6px;flex-wrap:wrap}.catalog-filter{padding:8px 11px;border:1px solid var(--line);border-radius:7px;background:white;font-size:12px}.catalog-filter[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:white}.catalog-count{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px;font-size:12px;color:var(--muted)}.catalog-table{width:100%;border-collapse:collapse}.catalog-table th{font-size:11px;font-weight:500;color:var(--muted);padding:12px;text-align:center;border-bottom:1px solid var(--line)}.catalog-table th:first-child{text-align:left;padding-left:20px}.catalog-table td{padding:10px 12px;text-align:center;border-bottom:1px solid #edf1f3}.catalog-table td:first-child{text-align:left;padding-left:20px}.catalog-table tr:last-child td{border:0}.catalog-table tbody tr:hover{background:#f8fbfc}.catalog-open{display:block;width:100%;text-align:left;background:transparent;padding:0}.catalog-open b{font-size:16px;color:var(--accent)}.catalog-open span{font-size:11px;color:var(--muted);display:block;max-width:320px;white-space:normal}.catalog-state{display:inline-block;border-radius:5px;padding:5px 8px;font-size:12px;min-width:52px}.catalog-state.inside{background:#edf6f0}.catalog-state.outside{background:#fbefec}.catalog-state.unknown{background:#edf1f3}.catalog-docs{display:flex;gap:5px;align-items:center;justify-content:center;flex-wrap:wrap}.doc-badge{font-size:10px;border:1px solid var(--line);border-radius:4px;padding:3px 5px;background:white;color:var(--muted);white-space:nowrap}.doc-badge.linked{color:var(--accent);border-color:#b8d9d9}.catalog-dialog{width:min(1120px,96vw)}.catalog-dialog .dialog-header{align-items:start}.catalog-dialog .dialog-header h2{font-size:23px;line-height:1.2}.catalog-dialog-body{padding:20px}.catalog-metric{display:flex;align-items:center;gap:12px;margin-bottom:15px}.catalog-metric select{width:100%;min-width:0}.catalog-metric label{font-size:11px;color:var(--muted)}.catalog-dialog-toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px}.catalog-dialog-actions{display:flex;gap:8px;flex-wrap:wrap}.catalog-dialog #catalog-chart{height:330px}.catalog-measurements{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}.catalog-measurements th,.catalog-measurements td{padding:10px;border-bottom:1px solid var(--line);text-align:center}.catalog-measurements th{font-size:11px;font-weight:500;color:var(--muted)}.catalog-measurements td:first-child{text-align:left}.catalog-measurements strong{font-size:21px;font-weight:550}.catalog-measurements .range{font-size:10px;color:var(--muted);display:block}.catalog-note{font-size:11px;color:var(--muted);margin-top:13px}.catalog-actions-images img{height:160px}.catalog-link-type{font-size:10px;letter-spacing:.2px;color:var(--muted)}
@media(max-width:1150px){.profile-map-table{grid-template-columns:45px repeat(4,minmax(0,1fr))}.map-cell{font-size:15px;padding:7px 4px}.map-cell span{font-size:9px}.catalog-table td,.catalog-table th{padding:9px 7px}.catalog-open span{max-width:210px}.catalog-docs{flex-direction:column}.profile-pair{gap:12px}}
@media(max-width:650px){.profile-map{padding:12px 10px}.profile-map-table{grid-template-columns:34px repeat(4,minmax(0,1fr));gap:5px}.profile-map-table .axis{font-size:10px}.map-cell{font-size:13px;padding:9px 3px}.map-cell span{display:none}.profile-map-head{align-items:start}.profile-map-head .small{font-size:10px}.profile-pair{grid-template-columns:1fr}.profile-compare-head{align-items:start}.profile-change{font-size:11px;white-space:nowrap}.profile-change strong{font-size:14px}.profile-card .profile-photo img{height:auto}.catalog-table td,.catalog-table th{padding:8px 5px}.catalog-table td:first-child,.catalog-table th:first-child{padding-left:10px}.catalog-open b{font-size:14px}.catalog-open span{display:none}.catalog-state{font-size:11px;padding:4px;min-width:42px}.catalog-docs .doc-badge{font-size:9px}.catalog-filters{gap:4px}.catalog-filter{font-size:11px;padding:7px}.catalog-count{font-size:11px}.catalog-dialog-body{padding:12px}.catalog-metric{align-items:start;flex-direction:column;gap:4px}.catalog-dialog #catalog-chart{height:285px}.catalog-measurements th,.catalog-measurements td{padding:8px 5px}.catalog-measurements strong{font-size:17px}.catalog-dialog-toolbar{gap:9px}.profile-number{font-size:28px}}
</style>
</head>
<body>
<header class="topbar"><div class="brand">INTE<span>PLAST</span></div><div class="project"><b>3212</b><span>Pump Housing</span></div><nav class="present-nav" id="present-nav" aria-label="Casos en presentación"></nav><div class="top-actions"><span class="version">CORRECCIONES DE MOLDE</span><button class="icon-btn" id="presentation" aria-pressed="false" title="Modo presentación" aria-label="Activar modo presentación"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M7 3H3v4m10-4h4v4M3 13v4h4m10-4v4h-4"/></svg></button></div></header>
<div class="workspace">
<aside class="sidebar"><div class="sidebar-title eyebrow">Datos del 3212</div><nav class="case-nav" id="case-nav" aria-label="Catálogo, correcciones y perfiles"></nav><div class="sidebar-rule"></div><div class="sidebar-foot"><b>3212 Pump Housing</b><br>4 cavidades · 4 muestreos<br><br>CSV · XLS · PPTX · PDF</div></aside>
<main>
<div class="page-heading"><div class="heading-left"><div class="eyebrow" id="context"></div><h1 id="title"></h1></div><div class="heading-right"><span class="pill" id="headline-state"></span><button class="button" id="evidence-open">Fuentes ↗</button></div></div>
<div class="filters"><div class="filter"><span class="filter-label">Cavidad</span><div class="segmented" id="cavities" aria-label="Cavidad"></div></div><div class="filter" id="bolt-filter" hidden><span class="filter-label">Agujero</span><div class="segmented" id="bolts" aria-label="Agujero"></div></div><div class="filter" id="height-filter" hidden><span class="filter-label">H</span><div class="segmented" id="heights" aria-label="Altura"></div></div><div class="status-line" id="status-line" aria-live="polite"></div></div>
<div id="case-view">
<div class="hero">
<section class="panel action-panel"><div class="panel-head"><div class="action-meta"><span class="eyebrow" id="action-meta"></span><span class="small muted" id="action-date"></span></div></div><h2 class="action-title" id="action-title"></h2><button class="action-image" id="action-image" aria-label="Ampliar imagen del retoque"><img id="action-photo" alt="Zona del retoque en el documento original"><span class="enlarge">↗</span></button><div class="image-tabs" id="image-tabs" aria-label="Imágenes de la acción"></div><div class="action-bottom"><div class="action-switch" id="action-switch"></div><div class="delta-plan"><span class="eyebrow">Δ previsto</span><div><b id="plan-delta"></b><div class="formula" id="plan-steps"></div></div></div></div></section>
<section class="panel chart-panel"><div class="chart-head"><div><div class="eyebrow">01 → 03 → 05 → 08</div><h2>Evolución y previsión</h2></div><button class="button" id="zoom-band" aria-pressed="false">Ampliar tolerancia</button></div><div class="chart history-chart" id="history-chart" role="img" aria-label="Evolución de las medidas y previsión por muestreo"></div><div class="legend" id="history-legend"></div><span class="clipped" id="clipped" hidden></span></section>
</div>
<section class="panel results"><div class="result-head"><h2 id="result-title"></h2><span class="small muted">mm</span></div><div class="table-scroll" id="result-table"></div><div id="warnings" hidden></div></section>
<section class="panel detail-panel"><div class="detail-header"><div class="detail-tabs" id="detail-tabs" role="tablist" aria-label="Comparación detallada"></div><span class="detail-context" id="detail-context"></span></div><div class="detail-body" id="detail-body" role="tabpanel"><div id="cavities-view"></div><div id="matrix-view" hidden></div><div id="local-view" hidden><div class="local-caption" id="local-caption"></div><div id="local-chart" class="local-chart" role="img" aria-label="Espesor mínimo y máximo en las 60 secciones locales"></div></div></div></section>
</div>
<div id="profile-view" hidden><div class="profile-top" id="profile-picker"></div><section class="panel profile-map"><div class="profile-map-head"><h2 id="profile-map-title"></h2><span class="small muted">Exceso · mm &nbsp; | &nbsp; — Sin PDF</span></div><div class="profile-map-table" id="profile-map"></div></section><div class="profile-compare-head"><h2 id="profile-compare-title"></h2><div class="profile-change" id="profile-change"></div></div><div class="profile-pair" id="profile-pair"></div><section class="panel profile-evolution"><details id="profile-history"><summary>Evolución de las cuatro cavidades</summary><div class="chart" id="profile-chart" role="img" aria-label="Evolución del exceso de perfil por cavidad"></div></details></section></div>
<div id="catalog-view" hidden><div class="catalog-controls"><input id="catalog-search" class="catalog-search" type="search" placeholder="Buscar cota o evaluación…" aria-label="Buscar cota o evaluación"><div class="catalog-filters" id="catalog-filters"></div></div><div class="catalog-count"><span id="catalog-count"></span><span>Fuera / evaluaciones · <b id="catalog-cavity-label"></b></span></div><section class="panel table-scroll"><table class="catalog-table"><thead><tr><th>Cota / grupo</th><th>Fuentes</th><th>01</th><th>03</th><th>05</th><th>08</th></tr></thead><tbody id="catalog-list"></tbody></table><div class="empty" id="catalog-empty" hidden>Sin coincidencias</div></section></div>
<footer><span>3212 · <span id="footer-selection"></span></span><button id="scope-open">Alcance y trazabilidad</button></footer>
</main></div>
<dialog class="dialog image-dialog" id="image-dialog" aria-labelledby="image-title"><div class="dialog-header"><h2 id="image-title"></h2><button class="close" data-close="image-dialog" aria-label="Cerrar imagen">×</button></div><img id="zoom-image" alt="Imagen original ampliada"><div class="image-caption" id="image-caption"></div></dialog>
<dialog class="dialog evidence-dialog" id="evidence-dialog" aria-labelledby="evidence-title"><div class="dialog-header"><h2 id="evidence-title"></h2><button class="close" data-close="evidence-dialog" aria-label="Cerrar fuentes">×</button></div><div class="evidence-body" id="evidence-body"></div></dialog>
<dialog class="dialog catalog-dialog" id="catalog-dialog" aria-labelledby="catalog-detail-title"><div class="dialog-header"><div><div class="eyebrow">Mediciones CSV</div><h2 id="catalog-detail-title"></h2></div><button class="close" data-close="catalog-dialog" aria-label="Cerrar mediciones">×</button></div><div class="catalog-dialog-body"><div class="catalog-dialog-toolbar"><div class="segmented" id="catalog-cavities" aria-label="Cavidad de la medición"></div><div class="catalog-dialog-actions" id="catalog-detail-actions"></div></div><div class="catalog-metric"><label for="catalog-series">Evaluación</label><select id="catalog-series"></select></div><div id="catalog-chart" role="img" aria-label="Histórico de la evaluación seleccionada"></div><div class="table-scroll" id="catalog-measurements"></div><div class="catalog-note" id="catalog-note"></div></div></dialog>
<script id="dataset" type="application/json">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('dataset').textContent);
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>v==null?'—':Number(v).toLocaleString('es-ES',{minimumFractionDigits:3,maximumFractionDigits:3});
const signed=v=>v==null?'—':(v>0?'+':'')+fmt(v);
const val=r=>r?.value??null;
const subtract=(a,b)=>a==null||b==null?null:a-b;
const colors=['#2773b6','#8b5aa9'];
const names={profiles:'Perfiles A/B',catalog:'Todas las cotas',N161:'Diámetro interior',N240:'Distancia al plano A',N170:'Bolt Eye',N165:'Espesor local'};
const actionTitles={'2.16':'Reducir Ø 0,305 mm','2.13':'Retoque local · N240','2.5':'Plano A · N240','1.33':'Expulsores Ø4','2.11':'Retoque local · N165','2.4':'Plano A · N165'};
const states={inside:'Dentro',outside:'Fuera',unknown:'Sin evaluar'};
const symbols={inside:'●',outside:'▲',unknown:'—'};
const state={feature:'profiles',cavity:'c13',bolt:1,height:'1.5',action:'2.16',image:0,detail:'cavities',profile:'PA_1',profileA:'01',profileB:'03',catalogFilter:'all',catalogQuery:'',catalogEntry:null,catalogSeries:0,zoom:false};
const variant=()=>state.feature==='N170'?`B${state.bolt}-H${state.height}`:'main';
const comparison=(cavity=state.cavity,v=variant())=>data.cases[state.feature].comparisons[v][cavity];
function summary(records){
 const known=records.filter(r=>r&&['inside','outside'].includes(r.status));
 const outside=known.filter(r=>r.status==='outside').length;
 return {outside,total:records.length,missing:records.length-known.length,status:known.length!==records.length?'unknown':outside?'outside':'inside'};
}
function shortLabel(label){return label.replace('LP(2) máximo','LP máx.').replace('LP máximo','LP máx.').replace('GLOBAL mínimo','GLOBAL mín.').replace('GLOBAL máximo','GLOBAL máx.')}
function sourceLink(source,label){return source?`<a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(label||source.path)}</a>`:'—'}
function sourceRow(source,label){return `<li><b>${esc(label)}</b><br>${sourceLink(source)}<br><span class="muted source-path">${esc(source?.locator||'')}</span></li>`}
function loadImage(element,url,alt){
 if(alt)element.alt=alt;
 if(element.getAttribute('src')===url)return;
 // Do not keep showing the previous action while the next image is decoding.
 element.style.opacity='0';element.onload=()=>{element.style.opacity='1'};
 element.src=url;
 if(element.complete&&element.naturalWidth)element.style.opacity='1';
}
function statusValue(value,status){return `<span class="${status||'unknown'}">${fmt(value)}<span class="state-mark" aria-label="${states[status||'unknown']}">${symbols[status||'unknown']}</span></span>`}
const config={displayModeBar:false,responsive:true,scrollZoom:false};
function plot(id,traces,extra={}){
 const layout={font:{family:'Segoe UI, Arial, sans-serif',size:11,color:'#6f7e88'},paper_bgcolor:'#fff',plot_bgcolor:'#fff',margin:{l:59,r:27,t:46,b:39},showlegend:false,hovermode:'closest',xaxis:{fixedrange:true,zeroline:false,showgrid:false},yaxis:{fixedrange:true,zeroline:false,gridcolor:'#edf1f3',tickformat:'.3f',title:{text:'mm',font:{size:10}},automargin:true},...extra};
 return Plotly.react($(id),traces,layout,config);
}
function toleranceBand(lo,hi){return lo==null||hi==null?[]:[{type:'rect',xref:'paper',x0:0,x1:1,y0:lo,y1:hi,line:{width:0},fillcolor:'#e7f2eb',layer:'below'}]}
function segmented(id,values,selected,attribute){$(id).innerHTML=values.map(([key,label])=>`<button data-${attribute}="${esc(key)}" aria-pressed="${String(String(key)===String(selected))}">${esc(label)}</button>`).join('')}
function renderNavigation(){
 const buttons=Object.entries(names).map(([key,name])=>`<button class="case-tab" data-case="${key}" aria-current="${state.feature===key}"><span class="code">${key==='profiles'?'A / B':key==='catalog'?'Catálogo':key}${data.cases[key]?`<span class="plan-tag">Plan 0${data.cases[key].correction}</span>`:''}</span><span class="desc">${esc(name)}</span></button>`).join('');
 $('case-nav').innerHTML=buttons;
 $('present-nav').innerHTML=Object.keys(names).map(key=>`<button data-case="${key}" aria-pressed="${state.feature===key}">${key==='profiles'?'A / B':key==='catalog'?'Catálogo':key}</button>`).join('');
 segmented('cavities',data.cavities.map(c=>[c,c.toUpperCase()]),state.cavity,'cavity');
 segmented('bolts',[1,2,3,4].map(b=>[b,`B${b}`]),state.bolt,'bolt');
 segmented('heights',[['1.5','1,5 mm'],['5.0','5 mm']],state.height,'height');
 $('bolt-filter').hidden=$('height-filter').hidden=state.feature!=='N170';
}
function render(){
 renderNavigation();
 const profiles=state.feature==='profiles',catalog=state.feature==='catalog';
 $('case-view').hidden=profiles||catalog;$('profile-view').hidden=!profiles;$('catalog-view').hidden=!catalog;
 $('footer-selection').textContent=`${state.cavity.toUpperCase()} · ${profiles?state.profile:(catalog?'Catálogo':state.feature)+' · '+(state.feature==='N170'?variant():'4 muestreos')}`;
 if(profiles){renderProfiles();return}
 if(catalog){renderCatalog();return}
 const def=data.cases[state.feature],corr=data.corrections[def.correction],cmp=comparison(),s=summary(cmp.items.map(i=>i.after));
 $('context').textContent=`${state.feature} / Plan de corrección 0${def.correction}`;
 $('title').textContent=names[state.feature];
 $('headline-state').className='pill '+s.status;
 $('headline-state').textContent=s.missing?'Evaluación incompleta':s.outside===0?'Medidas dentro':s.outside===s.total?'Fuera de tolerancia':'Cumplimiento parcial';
 $('status-line').innerHTML=`<span class="${s.status}">${s.missing?`${s.missing} sin evaluar`:`${s.outside} / ${s.total} fuera`}</span><span class="small muted">intern.${corr.after} · ${state.cavity.toUpperCase()}</span>`;
 renderAction();renderHistory();renderResults();renderDetailTabs();renderDetail();
}
function renderAction(){
 const def=data.cases[state.feature],corr=data.corrections[def.correction],action=data.actions[state.action];
 const item=comparison().items[0],deltas=item.steps.map(s=>s.delta),net=deltas.every(d=>d!=null)?deltas.reduce((s,d)=>s+d,0):null;
 $('action-meta').textContent=`Acción ${state.action} · Propuesta`;$('action-date').textContent=corr.date;
 $('action-title').textContent=actionTitles[state.action];
 state.image=Math.min(state.image,Math.max(0,action.images.length-1));
 const img=action.images[state.image];
 loadImage($('action-photo'),img?.url||'',img?.label||'Sin imagen');
 $('action-image').disabled=!img;
 $('image-tabs').innerHTML=action.images.map((img,i)=>`<button data-photo="${i}" aria-pressed="${i===state.image}" aria-label="Imagen ${i+1} de ${action.images.length}"></button>`).join('');
 $('action-switch').innerHTML=def.actions.map(id=>`<button data-action="${id}" aria-pressed="${id===state.action}">${id}${id==='2.4'||id==='2.5'?' · Plano A':''}</button>`).join('');
 $('plan-delta').innerHTML=`${signed(net)}<span class="unit">mm</span>`;
 $('plan-steps').textContent=deltas.length>1?deltas.map(signed).join(' → ')+' · conjunto':`Previsión XLS · ${state.cavity.toUpperCase()}`;
}
function historyRange(items,lo,hi){
 const values=items.flatMap(i=>[...i.history.map(val),i.prediction]).filter(v=>v!=null);
 const hasLimits=lo!=null&&hi!=null&&hi>lo;
 if(state.zoom&&hasLimits)return [lo-(hi-lo)*.35,hi+(hi-lo)*.35];
 const all=[...values,...[lo,hi].filter(v=>v!=null)];
 if(!all.length)return null;
 const min=Math.min(...all),max=Math.max(...all),padding=Math.max((max-min)*.18,.008);
 return [min-padding,max+padding];
}
function renderHistory(){
 const def=data.cases[state.feature],corr=data.corrections[def.correction],items=comparison().items;
 const lo=items[0]?.lower,hi=items[0]?.upper,afterIndex=data.samples.indexOf(corr.after),traces=[];
 items.forEach((item,i)=>{
  const ys=item.history.map(val);
  traces.push({type:'scatter',name:shortLabel(item.label),x:[0,1,2,3],y:ys,mode:'lines+markers',connectgaps:false,line:{color:colors[i],width:2.5},marker:{color:colors[i],size:8,symbol:i?'square':'circle',line:{width:2,color:'#fff'}},customdata:data.samples,hovertemplate:`${esc(shortLabel(item.label))} · intern.%{customdata}<br><b>%{y:.3f} mm</b><extra></extra>`});
  traces.push({type:'scatter',name:'Previsión '+shortLabel(item.label),x:[afterIndex],y:[item.prediction],mode:'markers',marker:{color:colors[i],size:13,symbol:'diamond-open',line:{width:2}},hovertemplate:`Previsto · ${esc(shortLabel(item.label))}<br><b>%{y:.3f} mm</b><extra></extra>`});
 });
 const shape=toleranceBand(lo,hi),annotations=[];
 for(const [plan,x] of [['1',.5],['2',1.5]]){
  const active=plan===def.correction;
  shape.push({type:'line',xref:'x',yref:'paper',x0:x,x1:x,y0:0,y1:1,line:{color:active?'#90bfc4':'#dce4e8',dash:'dot',width:1}});
  annotations.push({x,y:1.08,xref:'x',yref:'paper',text:`Plan 0${plan}`,showarrow:false,font:{size:10,color:active?'#087d85':'#99a5ad'},bgcolor:active?'#ecf6f6':'#fff',borderpad:4});
 }
 // Populate the legend before Plotly measures the remaining flex height.
 $('history-legend').innerHTML=items.map((item,i)=>`<span><i class="${i?'square':''}"></i>${esc(shortLabel(item.label))}</span>`).join('')+`<span><i class="diamond"></i>Previsto</span><span class="limits"><i class="band"></i>${fmt(lo)}–${fmt(hi)} mm</span>`;
 const range=historyRange(items,lo,hi);
 plot('history-chart',traces,{xaxis:{tickvals:[0,1,2,3],ticktext:data.samples.map(s=>`intern.${s}`),range:[-.18,3.18],fixedrange:true,showgrid:false,zeroline:false},yaxis:{range,gridcolor:'#edf1f3',zeroline:false,tickformat:'.3f',fixedrange:true,automargin:true},shapes:shape,annotations});
 $('zoom-band').setAttribute('aria-pressed',String(state.zoom));$('zoom-band').textContent=state.zoom?'Ver rango completo':'Ampliar tolerancia';
 const clipped=range?items.flatMap(i=>i.history.map(val)).filter(v=>v!=null&&(v<range[0]||v>range[1])).length:0;
 $('clipped').hidden=!state.zoom||!clipped;$('clipped').textContent=`${clipped} medidas fuera de vista`;
}
function renderResults(){
 const def=data.cases[state.feature],corr=data.corrections[def.correction],cmp=comparison();
 $('result-title').textContent=`Resultado del plan 0${def.correction} · ${state.cavity.toUpperCase()}${state.feature==='N170'?' · '+variant().replace('-H',' · H=')+' mm':''}`;
 $('result-table').innerHTML=`<table class="result-table"><thead><tr><th>Evaluación</th><th>Antes<b>intern.${corr.before}</b></th><th class="forecast">Previsión<b>XLS</b></th><th>Después<b>intern.${corr.after}</b></th><th>Δ observado</th><th>Real − previsto</th></tr></thead><tbody>${cmp.items.map(item=>`<tr><td>${esc(shortLabel(item.label))}</td><td>${statusValue(val(item.before),item.before?.status)}</td><td class="forecast">${statusValue(item.prediction,item.prediction_status)}</td><td>${statusValue(val(item.after),item.after?.status)}</td><td class="delta">${signed(subtract(val(item.after),val(item.before)))}</td><td class="delta">${signed(subtract(val(item.after),item.prediction))}</td></tr>`).join('')}</tbody></table>`;
 $('warnings').hidden=!cmp.warnings.length;$('warnings').innerHTML=cmp.warnings.map(w=>`<div class="data-warning">${esc(w)}</div>`).join('');
}
function renderDetailTabs(){
 const tabs=[['cavities','Comparar cavidades']];
 if(state.feature==='N170')tabs.push(['matrix','8 secciones × 4 cavidades']);
 if(state.feature==='N165')tabs.push(['local','60 secciones locales']);
 if(!tabs.some(([id])=>id===state.detail))state.detail=tabs[0][0];
 $('detail-tabs').innerHTML=tabs.map(([id,name])=>`<button role="tab" id="tab-${id}" data-detail="${id}" aria-controls="detail-body" aria-selected="${id===state.detail}" tabindex="${id===state.detail?0:-1}">${name}</button>`).join('');
 $('detail-body').setAttribute('aria-labelledby','tab-'+state.detail);
 const corr=data.corrections[data.cases[state.feature].correction];
 $('detail-context').textContent=state.detail==='local'?`intern.${corr.before} → ${corr.after}`:`intern.${corr.after}`;
}
function bulletSvg(item,min,max){
 const x=v=>12+(v-min)/(max-min)*156,y=12,after=val(item.after),pred=item.prediction;
 const band=item.lower!=null&&item.upper!=null?`<rect x="${x(item.lower)}" y="7" width="${Math.max(0,x(item.upper)-x(item.lower))}" height="10" fill="#e1efe6"/>`:'';
 const diamond=pred==null?'':`<path d="M${x(pred)},6 l5,6 -5,6 -5,-6Z" fill="white" stroke="#78909c" stroke-width="1.2"/>`;
 const dot=after==null?'':`<circle cx="${x(after)}" cy="${y}" r="3.5" fill="${item.after.status==='inside'?'#18765c':item.after.status==='outside'?'#b2473e':'#6f7e88'}"/>`;
 return `<svg class="bullet-chart" viewBox="0 0 180 24" role="img" aria-label="Después ${fmt(after)}; previsto ${fmt(pred)}; límites ${fmt(item.lower)} a ${fmt(item.upper)}"><line x1="12" y1="12" x2="168" y2="12" stroke="#dfe6e9"/>${band}${diamond}${dot}</svg>`;
}
function renderCavities(){
 const all=data.cavities.map(c=>comparison(c));
 const ranges=all[0].items.map((_,i)=>{
  const vals=all.flatMap(c=>[val(c.items[i].after),c.items[i].prediction,c.items[i].lower,c.items[i].upper]).filter(v=>v!=null);
  const min=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):1,pad=Math.max((max-min)*.1,.005);
  return [min-pad,max+pad];
 });
 $('cavities-view').innerHTML=`<div class="cavity-cards">${data.cavities.map((c,index)=>{
  const cmp=all[index],s=summary(cmp.items.map(i=>i.after));
  return `<button class="cavity-card ${c===state.cavity?'active':''}" data-cavity="${c}" aria-pressed="${c===state.cavity}"><header><b>${c.toUpperCase()}</b><span class="${s.status}">${s.missing?'Sin evaluar':s.outside+' / '+s.total+' fuera'}</span></header>${cmp.items.map((item,i)=>`<div class="cavity-row"><span class="muted">${esc(shortLabel(item.label))}</span><strong class="${item.after?.status||'unknown'}">${fmt(val(item.after))}</strong></div>${bulletSvg(item,...ranges[i])}`).join('')}</button>`;
 }).join('')}</div><div class="small muted" style="margin-top:10px">● Medido &nbsp; ◇ Previsto &nbsp; <span style="color:#18765c">▰</span> Tolerancia</div>`;
}
function renderMatrix(){
 const variants=data.cases.N170.variants;
 $('matrix-view').innerHTML=`<div class="matrix-legend"><span>● GX</span><span>▪ LP máx.</span><span class="inside">Dentro</span><span class="outside">Fuera</span></div><div class="table-scroll"><table class="matrix"><thead><tr><th>Sección</th>${data.cavities.map(c=>`<th>${c.toUpperCase()}</th>`).join('')}</tr></thead><tbody>${variants.map(v=>`<tr><td>${v.replace('-H',' · H=')} mm</td>${data.cavities.map(c=>`<td><button class="matrix-button ${v===variant()&&c===state.cavity?'active':''}" data-matrix="${v}|${c}" aria-label="${v} ${c}" aria-pressed="${v===variant()&&c===state.cavity}">${comparison(c,v).items.map(item=>`<span class="matrix-value ${item.after?.status||'unknown'}" title="${esc(shortLabel(item.label))}: ${fmt(val(item.after))} · ${states[item.after?.status||'unknown']}">${fmt(val(item.after))}</span>`).join('')}</button></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function renderLocal(){
 const corr=data.corrections[data.cases.N165.correction],samples=[corr.before,corr.after],pairs=data.sections[state.cavity],traces=[];
 let outside=0,missing=0;
 for(const pair of pairs[corr.after]){const s=summary(pair);if(s.missing)missing++;else if(s.outside)outside++;}
 $('local-caption').innerHTML=`<span><span style="color:#ac8a58">━</span> intern.${corr.before} &nbsp; <span style="color:#087d85">━</span> intern.${corr.after}</span><span>${outside} / 60 secciones fuera${missing?' · '+missing+' sin evaluar':''}</span>`;
 samples.forEach((sample,j)=>[0,1].forEach((metric,i)=>traces.push({type:'scatter',name:`intern.${sample} · ${metric?'máximo':'mínimo'}`,x:Array.from({length:60},(_,p)=>p+1),y:pairs[sample].map(pair=>val(pair[metric])),mode:'lines',connectgaps:false,line:{color:j?'#087d85':'#ac8a58',width:j?1.8:1.2,dash:i?'solid':'dot'},fill:i?'tonexty':'none',fillcolor:j?'rgba(8,125,133,.09)':'rgba(172,138,88,.07)',hovertemplate:`intern.${sample} · ${metric?'máximo':'mínimo'}<br>Sección %{x}: <b>%{y:.3f} mm</b><extra></extra>`})));
 plot('local-chart',traces,{margin:{l:59,r:20,t:15,b:35},shapes:toleranceBand(1.3,1.35),xaxis:{title:{text:'Sección',font:{size:10}},dtick:10,range:[1,60],fixedrange:true,showgrid:false},hovermode:'x unified'});
}
function renderDetail(){
 // Keep chart nodes mounted: removing a chart during Plotly's deferred layout causes races.
 for(const view of ['cavities','matrix','local'])$(view+'-view').hidden=state.detail!==view;
 if(state.detail==='matrix')renderMatrix();else if(state.detail==='local')renderLocal();else renderCavities();
}
function profileRecord(cavity,sample){return data.profiles.find(p=>p.cavity===cavity&&p.sample===sample&&p.element===state.profile)}
function profileStatus(p){return p?.excess==null?'unknown':p.excess>1e-9?'outside':'inside'}
function profileCard(sample,side){
 const p=profileRecord(state.cavity,sample),status=profileStatus(p);
 const picker=`<div class="sample-picker"><span>${side==='A'?'Referencia':'Comparación'}</span><select data-profile-side="${side}" aria-label="Muestreo ${side==='A'?'de referencia':'de comparación'}">${data.samples.map(s=>`<option value="${s}" ${s===sample?'selected':''}>intern.${s}</option>`).join('')}</select></div>`;
 const image=p?.crop_image?`<button class="profile-photo" data-image="${esc(p.crop_image)}" data-caption="${esc(p.source.path)} · Gráfica original" aria-label="Ampliar gráfica ${state.profile} intern.${sample}"><img src="${esc(p.crop_image)}" alt="Gráfica ${state.profile} ${state.cavity} intern.${sample}, ejes originales"><span class="enlarge">↗</span></button>`:'<div class="empty">Sin informe disponible</div>';
 return `<article class="panel profile-card"><div class="panel-head"><div>${picker}<div class="profile-number ${status}">${fmt(p?.excess)}</div><span class="small muted">Exceso · mm</span></div><span class="pill ${status}">${states[status]}</span></div>${image}<div class="profile-source"><span class="muted">Desviación <b>${fmt(p?.desv_inf)} / ${fmt(p?.desv_sup)}</b> mm</span><span class="muted">Escala original</span></div></article>`;
}
function renderProfiles(){
 $('context').textContent='Contorno interior / Perfiles';$('title').textContent='Perfiles A / B';
 $('headline-state').className='pill unknown';$('headline-state').textContent='Banda ±0,025 mm';
 $('status-line').innerHTML=`<span class="muted">${state.profile.replace('_',' · ')} · ${state.cavity.toUpperCase()}</span>`;
 $('profile-picker').innerHTML=['PA','PB'].map(f=>`<div class="family"><label>${f}</label>${[1,2,3,4,5,6].map(n=>`<button data-profile="${f}_${n}" aria-pressed="${state.profile===f+'_'+n}">${n}</button>`).join('')}</div>`).join('');
 $('profile-map-title').textContent=`${state.profile.replace('_',' · ')} / Cavidades × muestreos`;
 const values=data.profiles.filter(p=>p.element===state.profile&&p.excess!=null).map(p=>p.excess),max=Math.max(.001,...values);
 $('profile-map').innerHTML=`<span></span>${data.samples.map(s=>`<span class="axis">intern.${s}</span>`).join('')}`+data.cavities.map(c=>`<span class="row-label">${c.toUpperCase()}</span>${data.samples.map(s=>{
  const p=profileRecord(c,s),status=profileStatus(p),selected=c===state.cavity&&s===state.profileB,reference=c===state.cavity&&s===state.profileA;
  const color=status==='outside'?`rgba(178,71,62,${.045+.16*p.excess/max})`:status==='inside'?'#edf6f0':'#f0f3f5';
  return `<button class="map-cell ${status}${selected?' selected':''}${reference?' reference':''}" style="background:${color}" data-profile-cell="${c}|${s}" aria-pressed="${selected}" aria-label="${c} intern.${s}: ${p?.excess==null?'sin PDF':fmt(p.excess)+' mm de exceso'}">${fmt(p?.excess)}<span>${status==='unknown'?'':status==='outside'?'▲':'●'}</span></button>`;
 }).join('')}`).join('');
 $('profile-compare-title').textContent=`${state.cavity.toUpperCase()} · ${state.profile.replace('_',' / ')}`;
 const delta=subtract(profileRecord(state.cavity,state.profileB)?.excess,profileRecord(state.cavity,state.profileA)?.excess);
 $('profile-change').innerHTML=`Δ exceso<strong class="${delta==null?'unknown':delta<0?'inside':delta>0?'outside':'unknown'}">${signed(delta)} <span class="small">mm</span></strong>`;
 $('profile-pair').innerHTML=profileCard(state.profileA,'A')+profileCard(state.profileB,'B');
 if($('profile-history').open)renderProfileHistory();
}
function renderProfileHistory(){
 const palette=['#087d85','#2773b6','#8b5aa9','#ac8a58'];
 plot('profile-chart',data.cavities.map((c,i)=>({type:'scatter',name:c.toUpperCase(),x:data.samples,y:data.samples.map(s=>profileRecord(c,s)?.excess??null),mode:'lines+markers',connectgaps:false,line:{color:palette[i],width:c===state.cavity?3:1.5},marker:{size:c===state.cavity?8:5},hovertemplate:`${c.toUpperCase()} · intern.%{x}<br><b>%{y:.3f} mm</b><extra></extra>`})),{showlegend:true,legend:{orientation:'h',x:0,y:1.25},margin:{l:58,r:25,t:35,b:32},xaxis:{type:'category',categoryorder:'array',categoryarray:data.samples,tickvals:data.samples,ticktext:data.samples.map(s=>'intern.'+s),fixedrange:true,showgrid:false},yaxis:{rangemode:'tozero',tickformat:'.3f',fixedrange:true,gridcolor:'#edf1f3',zeroline:false},hovermode:'x unified'});
}
const catalogEntries=()=>data.catalog.entries;
const activeCatalogEntry=()=>catalogEntries().find(e=>e.id===state.catalogEntry);
function filterEntries(filter=state.catalogFilter){
 return catalogEntries().filter(e=>filter==='diagnostic'?e.kind==='diagnostic':e.kind==='dimension'&&(filter!=='actions'||e.actions.length)&&(filter!=='forecast'||e.reviewed_case));
}
function renderCatalog(){
 $('context').textContent='Inventario / Mediciones y documentación';$('title').textContent='Cotas medidas';
 $('headline-state').className='pill unknown';$('headline-state').textContent=`${filterEntries('all').length} grupos de cotas`;
 $('status-line').innerHTML=`<span class="muted">${data.catalog.files} CSV · ${data.catalog.row_count.toLocaleString('es-ES')} registros</span>`;
 $('catalog-search').value=state.catalogQuery;
 $('catalog-filters').innerHTML=[['all','Todas'],['actions','Con acciones'],['forecast','Previsión contrastada'],['diagnostic','Coordenadas']].map(([id,label])=>`<button class="catalog-filter" data-catalog-filter="${id}" aria-pressed="${state.catalogFilter===id}">${label} · ${filterEntries(id).length}</button>`).join('');
 $('catalog-cavity-label').textContent=state.cavity.toUpperCase();renderCatalogList();
}
function renderCatalogList(){
 const q=state.catalogQuery.toLocaleLowerCase('es'),entries=filterEntries().filter(e=>[e.id,e.title,...e.series.map(s=>s.label)].join(' ').toLocaleLowerCase('es').includes(q));
 $('catalog-count').textContent=`${entries.length} ${state.catalogFilter==='diagnostic'?'grupos de coordenadas':'grupos de cotas'}`;
 $('catalog-empty').hidden=entries.length!==0;
 $('catalog-list').innerHTML=entries.map(entry=>`<tr><td><button class="catalog-open" data-catalog="${esc(entry.id)}"><b>${esc(entry.kind==='diagnostic'?'X / Z':entry.id)}</b><span>${esc(entry.kind==='diagnostic'?entry.title:entry.series.length+' evaluaciones'+(entry.numbers.length>1?' · cabecera compartida':''))}</span></button></td><td><div class="catalog-docs"><span class="doc-badge linked" title="Mediciones CSV">CSV</span>${entry.actions.length?`<button class="doc-badge linked" data-catalog-sources="${esc(entry.id)}" title="Acciones relacionadas">PPT · ${entry.actions.length}</button>`:'<span class="doc-badge" title="Sin asociación encontrada en estos planes">PPT —</span>'}${entry.reviewed_case?`<button class="doc-badge linked" data-open-case="${entry.reviewed_case}" title="Abrir comparación de previsión XLS y resultado">XLS ✓</button>`:'<span class="doc-badge" title="Previsión XLS sin revisar para esta cota">XLS · ?</span>'}</div></td>${data.samples.map(sample=>{
  const s=summary(entry.series.map(series=>series.records[state.cavity]?.[sample]));
  return `<td><button class="catalog-state ${s.status}" data-catalog="${esc(entry.id)}" title="${s.outside} fuera de ${s.total}; ${s.missing} sin evaluar">${s.missing?'—':s.outside+' / '+s.total}</button></td>`;
 }).join('')}</tr>`).join('');
}
function openCatalog(id){
 if(!catalogEntries().some(e=>e.id===id))return;
 state.catalogEntry=id;state.catalogSeries=0;$('catalog-dialog').showModal();renderCatalogDetail();
}
function renderCatalogDetail(){
 const entry=activeCatalogEntry();if(!entry)return;
 state.catalogSeries=Math.min(state.catalogSeries,entry.series.length-1);
 const series=entry.series[state.catalogSeries],records=data.samples.map(s=>series.records[state.cavity]?.[s]);
 $('catalog-detail-title').textContent=entry.kind==='diagnostic'?entry.title:entry.id;
 segmented('catalog-cavities',data.cavities.map(c=>[c,c.toUpperCase()]),state.cavity,'catalog-cavity');
 $('catalog-detail-actions').innerHTML=`<button class="button" data-catalog-sources="${esc(entry.id)}">Fuentes${entry.actions.length?' · '+entry.actions.length+' acciones':''} ↗</button>${entry.reviewed_case?`<button class="button" data-open-case="${entry.reviewed_case}">Ver corrección ↗</button>`:'<span class="doc-badge">Previsión sin revisar</span>'}`;
 $('catalog-series').innerHTML=entry.series.map((s,i)=>`<option value="${i}" ${i===state.catalogSeries?'selected':''}>${esc(s.label)}</option>`).join('');
 plot('catalog-chart',[
  {type:'scatter',name:'Límite inferior',x:data.samples,y:records.map(r=>r?.lower??null),mode:'lines',line:{color:'#a8cfb7',width:1},connectgaps:false,hoverinfo:'skip'},
  {type:'scatter',name:'Límite superior',x:data.samples,y:records.map(r=>r?.upper??null),mode:'lines',line:{color:'#a8cfb7',width:1},fill:'tonexty',fillcolor:'rgba(24,118,92,.08)',connectgaps:false,hoverinfo:'skip'},
  {type:'scatter',name:'Medido',x:data.samples,y:records.map(val),mode:'lines+markers',connectgaps:false,line:{color:'#2773b6',width:2.5},marker:{size:9,color:'#2773b6'},hovertemplate:`intern.%{x}<br><b>%{y:.3f} ${series.unit}</b><extra></extra>`}
 ],{margin:{l:63,r:25,t:25,b:40},xaxis:{type:'category',categoryorder:'array',categoryarray:data.samples,tickvals:data.samples,ticktext:data.samples.map(s=>'intern.'+s),fixedrange:true,showgrid:false},yaxis:{fixedrange:true,gridcolor:'#edf1f3',zeroline:false,tickformat:'.3f',title:{text:series.unit}},hovermode:'x unified'});
 $('catalog-measurements').innerHTML=`<table class="catalog-measurements"><thead><tr><th>${esc(shortLabel(series.unit))}</th>${data.samples.map(s=>`<th>intern.${s}</th>`).join('')}</tr></thead><tbody><tr><td>${state.cavity.toUpperCase()}</td>${records.map(r=>`<td><strong class="${r?.status||'unknown'}">${fmt(val(r))}</strong><span class="range">${fmt(r?.lower)}–${fmt(r?.upper)}</span></td>`).join('')}</tr></tbody></table>`;
 const notes=[];
 if(entry.numbers.length>1)notes.push('Cabecera compartida: se conserva la evaluación original sin repartirla automáticamente entre cotas.');
 if(records.some(r=>r?.corrected))notes.push('Signo B2/B4 corregido según la revisión del export; valor original conservado en Fuentes.');
 if(entry.id==='N170')notes.push('Identidad por ID CMM; se conserva la cabecera original mal rotulada en Fuentes.');
 $('catalog-note').textContent=notes.join(' ');
}
function catalogSources(scopeOnly=false){
 const entry=activeCatalogEntry();$('evidence-title').textContent=entry&&!scopeOnly?`${entry.id} · Fuentes`:'Catálogo · Alcance';
 let content=`<p>${data.catalog.files} CSV · ${data.catalog.row_count.toLocaleString('es-ES')} registros · ${Object.keys(data.action_index).length} acciones documentadas.</p>`;
 if(entry&&!scopeOnly){
  content+=entry.actions.map(id=>{const a=data.action_index[id];return `<details><summary>Plan 0${a.plan} · Acción ${id}</summary><p class="catalog-link-type">${esc(a.link_method)} · ${esc(a.features.join(', '))}</p>${a.paragraphs.map(p=>`<p>${esc(p)}</p>`).join('')}<div class="image-grid catalog-actions-images">${a.images.map(img=>`<button data-image="${esc(img.url)}" data-caption="${esc(a.source.path)} · ${esc(a.source.locator)}" aria-label="Ampliar imagen ${id}"><img src="${esc(img.url)}" alt="Acción ${id}" loading="lazy"></button>`).join('')}</div><p>${sourceLink(a.source)}</p></details>`}).join('');
  const series=entry.series[state.catalogSeries]||entry.series[0];
  content+=`<details open><summary>${esc(series.label)}</summary><ul>${data.samples.map(s=>{const r=series.records[state.cavity]?.[s];return sourceRow(r?.source,`intern.${s} · ${fmt(val(r))} ${series.unit}${r?.corrected?' · original '+fmt(r.original_value):''}`)}).join('')}</ul></details>`;
 }
 content+=`<details ${scopeOnly?'open':''}><summary>Alcance de la extracción</summary><p>El catálogo se obtiene de los CSV, incluyendo sus evaluaciones locales y coordenadas auxiliares. Las cabeceras compartidas permanecen agrupadas. Los recuentos son evaluaciones, no piezas.</p><p>Las acciones se asocian por DIM. Nr. del título o por correspondencias de imágenes ya revisadas. No se infiere ejecución. La previsión XLS está contrastada para los cuatro casos piloto; en las demás cotas queda sin revisar.</p><p>La pieza, los formatos y los planes siguen siendo los del 3212. La lista de cotas se descubre automáticamente; la ingesta completa de otra pieza todavía requiere adaptación.</p><p><a href="datos.json" download>Descargar datos y procedencia</a></p></details>`;
 $('evidence-body').innerHTML=content;$('evidence-dialog').showModal();
}
function evidence(scopeOnly=false){
 if(state.feature==='catalog'){catalogSources(true);return}
 $('evidence-title').textContent=scopeOnly?'Alcance y trazabilidad':`${state.feature==='profiles'?state.profile:state.feature} · Fuentes`;
 const scope=`<details ${scopeOnly?'open':''}><summary>Alcance</summary><p>Propuestas de corrección y resultados posteriores. El marcador original «OK» no confirma ejecución ni aceptación. La comparación temporal no acredita causalidad exclusiva.</p><p>Previsiones: resultados guardados en los XLS, sin recalcular. Los emparejamientos están revisados para el 3212. Límites según CSV/XLS; el plano disponible es rev.07 y los informes citan rev.06.</p><p>PUNTS_NOUS coincide con los últimos 150 puntos de PUNTS; no consta un objetivo de mecanizado. Los perfiles A/B no tienen una correspondencia N-number confirmada.</p><p><a href="datos.json" download>Descargar datos y procedencia</a></p></details>`;
 let content='';
 if(state.feature==='profiles'){
  content='<ul>'+data.profiles.filter(p=>p.cavity===state.cavity&&p.element===state.profile).map(p=>sourceRow(p.source,`intern.${p.sample} · ${p.element}`)).join('')+'</ul>';
 }else{
  const def=data.cases[state.feature],cmp=comparison(),corr=data.corrections[def.correction];
  content=`<p class="note">${esc(def.note)}</p><details ${scopeOnly?'':'open'}><summary>Acciones ${def.actions.join(' + ')}</summary>${def.actions.map(id=>{
   const a=data.actions[id];return `<h3 style="margin-top:16px">Acción ${id}</h3>${a.paragraphs.map(p=>`<p>${esc(p)}</p>`).join('')}<p>Marcador original: ${esc(a.marker)}</p><div class="image-grid">${a.images.map(img=>`<button data-image="${esc(img.url)}" data-caption="${esc(img.label)}" aria-label="Ampliar ${esc(img.label)}"><img src="${esc(img.url)}" alt="${esc(img.label)}" loading="lazy"></button>`).join('')}</div><p>${sourceLink(a.source)}<br>${esc(a.source.locator)}</p>`;
  }).join('')}</details><details><summary>Previsiones y mediciones</summary>${cmp.items.map(item=>`<h3 style="margin-top:16px">${esc(item.label)}</h3><p>${fmt(item.xls_before)} ${item.steps.map(step=>`→ ${signed(step.delta)} = ${fmt(step.value)} (${esc(step.cells)})`).join(' ')}</p><ul>${sourceRow(item.source,'Previsión XLS')}${item.history.map((record,i)=>sourceRow(record?.source,`intern.${data.samples[i]} · ${fmt(val(record))} mm`)).join('')}</ul>`).join('')}</details>`;
  if(state.feature==='N165')content+=`<details><summary>N165 MIN/MAX · evaluación alternativa</summary><table><thead><tr><th></th>${data.samples.map(s=>`<th>${s}</th>`).join('')}</tr></thead><tbody>${[0,1].map(i=>`<tr><td>${i?'Máximo':'Mínimo'}</td>${data.samples.map(s=>`<td>${fmt(val(data.scan[state.cavity][s][i]))}</td>`).join('')}</tr>`).join('')}</tbody></table></details>`;
  content+=`<details><summary>Nubes · ${state.cavity.toUpperCase()} · intern.${corr.after}</summary><ul>${data.support.filter(s=>s.cavity===state.cavity&&s.sample===corr.after).map(s=>sourceRow(s.source,s.kind)).join('')}</ul></details>`;
 }
 $('evidence-body').innerHTML=scopeOnly?scope+content:content+scope;
 $('evidence-dialog').showModal();
}
function openImage(url,caption){loadImage($('zoom-image'),url);$('image-title').textContent=state.feature==='profiles'?state.profile:`${state.feature==='catalog'?state.catalogEntry:state.feature} · Imagen original`;$('image-caption').textContent=caption||'';$('image-dialog').showModal()}
function chooseCase(feature){
 state.feature=feature;state.zoom=false;state.image=0;
 if(data.cases[feature]){state.action=data.cases[feature].actions[0];state.detail=feature==='N170'?'matrix':feature==='N165'?'local':'cavities'}
 render();
}
document.addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button)return;const d=button.dataset;
 if(d.case){chooseCase(d.case);return}
 if(d.profileCell){const [c,s]=d.profileCell.split('|');state.cavity=c;if(s===state.profileA)state.profileA=state.profileB;state.profileB=s;render();return}
 if(d.catalogFilter){state.catalogFilter=d.catalogFilter;renderCatalog();return}
 if(d.catalog){openCatalog(d.catalog);return}
 if(d.catalogSources){state.catalogEntry=d.catalogSources;if(!$('catalog-dialog').open)state.catalogSeries=0;catalogSources();return}
 if(d.catalogCavity){state.cavity=d.catalogCavity;renderCatalogDetail();return}
 if(d.openCase){$('catalog-dialog').close();chooseCase(d.openCase);return}
 if(d.cavity){state.cavity=d.cavity;render();return}
 if(d.bolt){state.bolt=Number(d.bolt);render();return}
 if(d.height){state.height=d.height;render();return}
 if(d.action){state.action=d.action;state.image=0;renderAction();return}
 if(d.photo!=null){state.image=Number(d.photo);renderAction();return}
 if(d.detail){state.detail=d.detail;renderDetailTabs();renderDetail();return}
 if(d.matrix){const [v,c]=d.matrix.split('|'),m=v.match(/^B([1-4])-H(1\.5|5\.0)$/);state.bolt=Number(m[1]);state.height=m[2];state.cavity=c;render();return}
 if(d.profile){state.profile=d.profile;render();return}
 if(d.image){openImage(d.image,d.caption);return}
 if(d.close){$(d.close).close();return}
});
$('action-image').addEventListener('click',()=>{const a=data.actions[state.action],img=a.images[state.image];if(img)openImage(img.url,a.source.path+' · '+a.source.locator)});
$('zoom-band').addEventListener('click',()=>{state.zoom=!state.zoom;renderHistory()});
$('evidence-open').addEventListener('click',()=>evidence());$('scope-open').addEventListener('click',()=>evidence(true));
$('presentation').addEventListener('click',()=>{const active=document.body.classList.toggle('presenting');$('presentation').setAttribute('aria-pressed',String(active));$('presentation').setAttribute('aria-label',active?'Salir del modo presentación':'Activar modo presentación');requestAnimationFrame(()=>{render();document.querySelectorAll('.js-plotly-plot').forEach(el=>{if(el.offsetWidth)Plotly.Plots.resize(el)})})});
for(const id of ['image-dialog','evidence-dialog','catalog-dialog'])$(id).addEventListener('click',e=>{if(e.target===$(id)){const r=$(id).getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$(id).close()}});
$('profile-history').addEventListener('toggle',()=>{if($('profile-history').open)renderProfileHistory()});
$('profile-pair').addEventListener('change',e=>{const side=e.target.dataset.profileSide;if(!side)return;const key='profile'+side,other='profile'+(side==='A'?'B':'A'),previous=state[key];state[key]=e.target.value;if(state[key]===state[other])state[other]=previous;renderProfiles()});
$('catalog-search').addEventListener('input',e=>{state.catalogQuery=e.target.value;renderCatalogList()});
$('catalog-series').addEventListener('change',e=>{state.catalogSeries=Number(e.target.value);renderCatalogDetail()});
$('catalog-dialog').addEventListener('close',()=>{if(state.feature==='catalog')render()});
$('detail-tabs').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const tabs=[...$('detail-tabs').querySelectorAll('[role=tab]')],current=tabs.findIndex(t=>t.getAttribute('aria-selected')==='true');let next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(current+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;e.preventDefault();state.detail=tabs[next].dataset.detail;renderDetailTabs();renderDetail();$('tab-'+state.detail).focus()});
render();
</script>
</body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", type=Path, default=ROOT, help="Carpeta 3212 Pump Housing")
    parser.add_argument("--salida", type=Path, default=OUTPUT, help="Carpeta exclusiva para la versión 3")
    parser.add_argument("--no-abrir", action="store_true", help="Generar sin abrir el navegador")
    args = parser.parse_args()
    root, destination = args.raiz.resolve(), args.salida.resolve()
    old_outputs = [V1_OUTPUT.resolve(), (OUTPUT.parent / "correcciones-3212-v2").resolve()]
    if destination == root or root in destination.parents:
        parser.error("La salida debe estar fuera de los datos originales")
    if destination == OUTPUT.parent.resolve() or any(destination == old or old in destination.parents for old in old_outputs):
        parser.error("Usar una carpeta propia de v3; las salidas anteriores se conservan")
    page = destination / "index.html"
    if page.exists() and '<meta name="correcciones-version" content="3">' not in page.read_text(encoding="utf-8"):
        parser.error("La carpeta contiene otra vista. Seleccionar una salida exclusiva de v3")
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    print("Leyendo CSV, previsiones XLS, acciones PPTX y perfiles...", flush=True)
    data = build_data(root, assets)
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
    (destination / "datos.json").write_text(encoded, encoding="utf-8")
    (assets / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    page.write_text(PAGE.replace("__DATA__", encoded.replace("<", "\\u003c").replace("&", "\\u0026")), encoding="utf-8")
    print(f"Vista v3: {page}")
    dimensions = sum(entry["kind"] == "dimension" for entry in data["catalog"]["entries"])
    print(f"{dimensions} grupos de cotas; {data['catalog']['row_count']} registros; "
          f"{len(data['action_index'])} acciones; {len(data['profiles'])} gráficas de perfil.")
    if not args.no_abrir:
        webbrowser.open(page.as_uri())


if __name__ == "__main__":
    main()
