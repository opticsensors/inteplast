"""Assemble the supported 3212 evidence snapshot from application readers."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Any

import fitz
import numpy as np
import xlrd

from app.ingestion import cmm, profile_pdf
from app.ingestion.common import source
from app.ingestion.pilot_3212.actions import extract_action_index, extract_actions
from app.ingestion.pilot_3212.catalog import load_catalog
from app.ingestion.pilot_3212.config import CASES, CAVITIES, CORRECTIONS, SAMPLES
from app.ingestion.pilot_3212.measurements import compare, load_csv


def build_data(root: Path, assets: Path) -> dict[str, Any]:
    """Import the supported pilot using explicit input/output directories."""
    assets.mkdir(parents=True, exist_ok=True)
    records, files = load_csv(root)
    # Release already opened workbooks even if a later file or mapping fails.
    with ExitStack() as resources:
        books = {}
        for key, correction in CORRECTIONS.items():
            book = xlrd.open_workbook(root / correction["xls"])
            resources.callback(book.release_resources)
            books[key] = book
        cases = {}
        for feature, definition in CASES.items():
            variants = (
                [
                    f"B{bolt}-H{height}"
                    for bolt in range(1, 5)
                    for height in ("1.5", "5.0")
                ]
                if feature == "N170"
                else ["main"]
            )
            cases[feature] = {
                **definition,
                "variants": variants,
                "comparisons": {
                    variant: {
                        cavity: compare(records, books, root, feature, variant, cavity)
                        for cavity in CAVITIES
                    }
                    for variant in variants
                },
            }
    profiles = load_profiles(root, assets)
    for profile in profiles:
        with fitz.open(root / profile["source"]["path"]) as document:
            page = document[0]
            clip = profile_pdf.profile_crop(page)
            filename = f"grafica-{profile['sample']}-{profile['cavity']}-{profile['element']}.png"
            page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False).save(
                assets / filename
            )
            profile.update(
                crop_image="assets/" + filename,
                crop_rect=list(clip),
                crop_method="Marco vectorial del gráfico + 8 pt",
            )
    action_index = extract_action_index(root, assets)
    return {
        "cases": cases,
        "corrections": CORRECTIONS,
        "actions": extract_actions(root, assets),
        "sections": {
            cavity: {
                sample: [
                    [
                        records.get((sample, cavity, "N165", f"P{point:02d}", idx))
                        for idx in (1, 2)
                    ]
                    for point in range(1, 61)
                ]
                for sample in SAMPLES
            }
            for cavity in CAVITIES
        },
        "scan": {
            cavity: {
                sample: [
                    records.get((sample, cavity, "N165", "scan", idx)) for idx in (1, 2)
                ]
                for sample in SAMPLES
            }
            for cavity in CAVITIES
        },
        "profiles": profiles,
        "support": load_support(root),
        "samples": list(SAMPLES),
        "cavities": list(CAVITIES),
        "csv_count": len(files),
        "review_date": "17/09/2026",
        "action_index": action_index,
        "catalog": load_catalog(root, action_index, cases),
    }


def load_profiles(root: Path, assets: Path) -> list[Any]:
    profiles = []
    for item in profile_pdf.discover(root / "4- Metrologia"):
        sample, cavity = item["muestreo"], item["cavidad"]
        name = f"perfil-{sample}-{cavity}-{item['ruta'].stem}"
        record = profile_pdf.read_pdf(item["ruta"], assets, 1.25, name)
        record.update(
            sample=sample,
            cavity=cavity,
            element=item["ruta"].stem,
            image="assets/" + record["png"],
            source=source(item["ruta"], root, "Página 1"),
            excess=profile_pdf.worst_excess(record),
            errors=profile_pdf.measurement_errors(record),
        )
        profiles.append(record)
    return profiles


def load_support(root: Path) -> list[Any]:
    support = []
    for path in sorted((root / "4- Metrologia").rglob("*.txt")):
        record: dict[str, Any] = {
            "source": source(path, root),
            "sample": cmm.sample_number(path),
            "cavity": cmm.cavity_number(path),
        }
        if "PUNTS_NOUS" in path.name:
            parent = path.with_name("3212_PUNTS.txt")
            points = np.loadtxt(path)
            whole = np.loadtxt(parent)
            record.update(
                kind="PUNTS_NOUS",
                points=len(points),
                subset_verified=bool(np.array_equal(points, whole[-len(points) :])),
            )
        else:
            record["kind"] = "PUNTS" if "PUNTS" in path.name else "Nube de cavidad"
        support.append(record)
    return support
