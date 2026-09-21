"""3212 correction slides, original illustrations and reviewed characteristic associations."""

from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from app.ingestion.common import source
from app.ingestion.pilot_3212.config import CASES, CORRECTIONS, REVIEWED_ACTION_LINKS

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def extract_actions(root: Path, assets: Path) -> dict[str, Any]:
    actions = {}
    wanted = {a for case in CASES.values() for a in case["actions"]}
    for correction in CORRECTIONS.values():
        path = root / correction["pptx"]
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                (
                    n
                    for n in archive.namelist()
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
                ),
                key=lambda n: int(Path(n).stem.removeprefix("slide")),
            )
            for slide_index, name in enumerate(slide_names, 1):
                xml = ET.fromstring(archive.read(name))
                paragraphs = [
                    "".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
                    for p in xml.findall(".//a:p", NS)
                ]
                match = re.search(
                    r"Tool\s+correction\s+(\d+\.\d+)", "\n".join(paragraphs)
                )
                if not match or match[1] not in wanted:
                    continue
                action_id = match[1]
                relationships = ET.fromstring(
                    archive.read(
                        posixpath.join(
                            posixpath.dirname(name),
                            "_rels",
                            posixpath.basename(name) + ".rels",
                        )
                    )
                )
                targets = {r.attrib["Id"]: r.attrib for r in relationships}
                images = []
                for pic in xml.findall(".//p:pic", NS):
                    blip = pic.find(".//a:blip", NS)
                    if blip is None:
                        continue
                    rel = targets.get(blip.get("{" + NS["r"] + "}embed", ""), {})
                    if not rel or rel.get("TargetMode") == "External":
                        continue
                    target = posixpath.normpath(
                        posixpath.join(posixpath.dirname(name), rel["Target"])
                    )
                    if not target.startswith("ppt/media/"):
                        continue
                    blob = archive.read(target)
                    image_name = (
                        "slide-"
                        + hashlib.sha256(blob).hexdigest()[:20]
                        + Path(target).suffix.lower()
                    )
                    (assets / image_name).write_bytes(blob)
                    images.append(
                        {
                            "url": "assets/" + image_name,
                            "label": f"Imagen original · acción {action_id}",
                        }
                    )
                # The first picture is the corporate logo in these reviewed slides.
                illustrations = images[1:] if len(images) > 1 else images
                cleaned = [
                    p
                    for p in paragraphs
                    if p
                    and not p.startswith(
                        (
                            "Tool correction",
                            "Longitud",
                            "Current situation",
                            "Tool correction plan",
                        )
                    )
                    and not re.fullmatch(r"\d+/\d+", p)
                    and p != "OK"
                    and "nº" not in p
                ]
                actions[action_id] = {
                    "id": action_id,
                    "paragraphs": cleaned,
                    "images": illustrations,
                    "marker": "OK" if "OK" in paragraphs else "Sin marcador OK",
                    "source": source(
                        path,
                        root,
                        f"Acción {action_id} · diapositiva física {slide_index} · {posixpath.basename(name)}",
                    ),
                }
    missing = wanted - actions.keys()
    if missing:
        raise ValueError(f"No se localizaron las acciones revisadas: {sorted(missing)}")
    return actions


def action_dimension_ids(title: str) -> list[str]:
    """Read every DIM. Nr. field, without mistaking nominal values for identifiers."""
    fields = re.findall(
        r"\bDIM\.?\s*Nr\.?\s*(N?\d{3}(?!\d)(?:\s*[/,;&]\s*N?\d{3}(?!\d))*)",
        title,
        re.IGNORECASE,
    )
    return list(
        dict.fromkeys("N" + n for field in fields for n in re.findall(r"\d{3}", field))
    )


def extract_action_index(root: Path, assets: Path) -> dict[str, Any]:
    """Extract all plan slides; associate DIM.Nr. titles or previously reviewed image links."""
    actions = {}
    for plan_id, correction in CORRECTIONS.items():
        path = root / correction["pptx"]
        with zipfile.ZipFile(path) as archive:
            names = sorted(
                (
                    n
                    for n in archive.namelist()
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
                ),
                key=lambda n: int(Path(n).stem.removeprefix("slide")),
            )
            for physical, name in enumerate(names, 1):
                xml = ET.fromstring(archive.read(name))
                paragraphs = [
                    "".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
                    for p in xml.findall(".//a:p", NS)
                ]
                titles = [
                    p
                    for p in paragraphs
                    if re.search(r"Tool\s+correction\s+\d+\.\d+", p)
                ]
                if len(titles) != 1:
                    raise ValueError(f"Título de acción ambiguo: {path.name}/{name}")
                title = titles[0]
                match = re.search(r"Tool\s+correction\s+(\d+\.\d+)", title)
                assert match is not None
                action_id = match[1]
                features = action_dimension_ids(title)
                method = "DIM. Nr. del título"
                if action_id in REVIEWED_ACTION_LINKS:
                    features, method = (
                        REVIEWED_ACTION_LINKS[action_id],
                        "Imágenes revisadas del PPTX",
                    )
                rels = ET.fromstring(
                    archive.read(
                        posixpath.join(
                            posixpath.dirname(name),
                            "_rels",
                            posixpath.basename(name) + ".rels",
                        )
                    )
                )
                targets = {r.attrib["Id"]: r.attrib for r in rels}
                images = []
                for pic in xml.findall(".//p:pic", NS):
                    blip = pic.find(".//a:blip", NS)
                    if blip is None:
                        continue
                    rel = targets.get(blip.get("{" + NS["r"] + "}embed", ""), {})
                    if not rel or rel.get("TargetMode") == "External":
                        continue
                    target = posixpath.normpath(
                        posixpath.join(posixpath.dirname(name), rel["Target"])
                    )
                    if not target.startswith("ppt/media/"):
                        continue
                    blob = archive.read(target)
                    filename = (
                        "slide-"
                        + hashlib.sha256(blob).hexdigest()[:20]
                        + Path(target).suffix.lower()
                    )
                    (assets / filename).write_bytes(blob)
                    images.append(
                        {"url": "assets/" + filename, "label": f"Acción {action_id}"}
                    )
                actions[action_id] = {
                    "id": action_id,
                    "plan": plan_id,
                    "title": title,
                    "features": list(dict.fromkeys(features)),
                    "link_method": method if features else "Sin asociación",
                    "paragraphs": [p for p in paragraphs if p],
                    "images": images,
                    "source": source(
                        path, root, f"Acción {action_id} · diapositiva {physical}"
                    ),
                }
    return actions
