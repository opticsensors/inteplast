"""Explicit 3212 samples, reviewed cases and source mappings."""

from __future__ import annotations

from typing import Any

SAMPLES = ("01", "03", "05", "08")


CAVITIES = ("c13", "c14", "c15", "c16")


CORRECTIONS = {
    "1": {
        "date": "24/01/2024",
        "before": "01",
        "after": "03",
        "xls": "5- Retoques de molde/3212-00_intern.01_mold_correction.xls",
        "pptx": "5- Retoques de molde/20240124-Mold correction_1_P3212_rev1.pptx",
    },
    "2": {
        "date": "18/03/2024",
        "before": "03",
        "after": "05",
        "xls": "5- Retoques de molde/2N/3212-00_intern.03_correction_2_.xls",
        "pptx": "5- Retoques de molde/2N/20240318-Mold correction_2_P3212_rev1.pptx",
    },
}


CASES: dict[str, dict[str, Any]] = {
    "N161": {
        "title": "Diámetro interior",
        "caption": "Dos extremos fuera de tolerancia",
        "correction": "2",
        "actions": ["2.16"],
        "description": "El plan propone reducir 0,305 mm en diámetro total y conservar la redondez. La previsión y las dos evaluaciones se comparan por separado.",
        "note": "GX y LP(2) máximo describen evaluaciones diferentes de la misma geometría. Una sola de ellas no basta para declarar conforme la característica.",
    },
    "N240": {
        "title": "Distancia al plano A",
        "caption": "Una previsión con dos pasos",
        "correction": "2",
        "actions": ["2.13", "2.5"],
        "description": "La previsión combina +0,020 mm del plano A y −0,080 mm del retoque local: un efecto neto de −0,060 mm sobre la cota.",
        "note": "La acción 2.13 no nombra N240 en su título. La correspondencia se revisó en la imagen del plano y en la tabla del Excel, filas 224–225.",
    },
    "N170": {
        "title": "Diámetro del Bolt Eye",
        "caption": "La mejora es parcial",
        "correction": "1",
        "actions": ["1.33"],
        "description": "La acción plantea usar expulsores de 4 y esperar a revisar la posición. El Excel calcula una previsión de +0,500 mm para las evaluaciones del diámetro.",
        "note": "El CSV y el método indican H=1,5 mm; el Excel anota H=−1,5. Se conserva esa discrepancia. B2 a H=5 se identifica por ID CMM 16, aunque la cabecera diga B1.",
    },
    "N165": {
        "title": "Espesor local",
        "caption": "Plano A y retoque local",
        "correction": "2",
        "actions": ["2.11", "2.4"],
        "description": "El Excel encadena +0,020 mm del plano A y −0,220 mm de retoque local. La previsión final del máximo ya supera el límite permitido.",
        "note": "La previsión usa GLOBAL, resumen de los puntos locales. El bloque N165 MIN/MAX del CSV es otra evaluación; se muestra aparte. Las 60 secciones pertenecen a la misma pieza.",
    },
}


# Associations reviewed against the original slide images.
REVIEWED_ACTION_LINKS = {
    "1.16": ["N155", "N258", "N267", "N268"],
    "1.17": ["N154", "N165", "N166", "N167"],
    "1.18": ["N236", "N237", "N240", "N241", "N252", "N256"],
    "2.3": ["N154", "N155", "N258", "N267", "N268"],
    "2.4": ["N165", "N166", "N167"],
    "2.5": ["N236", "N237", "N240", "N241", "N252", "N256"],
    "2.13": ["N240"],
}
