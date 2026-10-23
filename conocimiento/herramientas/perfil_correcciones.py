"""Perfil de los planes de correccion de molde (PPTX) de todas las piezas.

Por diapositiva: numero de correccion (plan.n), cotas del titulo (DIM. Nr.), bloques de la
plantilla presentes, marcador OK, magnitudes en mm y cavidades citadas. Mide cuanto se parecen
a la plantilla del piloto 3212. Tabla derivada `perfil_correccion` (se recalcula).

    python conocimiento/herramientas/perfil_correcciones.py [--feature "..."]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import conectar  # noqa: E402

TITULO = re.compile(
    r"(tool\s+correction|correcci[oóò]n?|correction|korrektur)\s*(?:n[ºr°o]?\.?\s*)?(\d+)\s*[.,]\s*(\d+)",
    re.I,
)
DIM = re.compile(r"DIM\.?\s*N[rº°o]?\.?\s*([^)\n]*)", re.I)
BLOQUES = {
    "current_situation": r"current situation",
    "actual_situation": r"actual situation",
    "tool_correction_plan": r"tool correction plan",
    "correction_proposal": r"correction proposal",
}
MM = re.compile(r"[-+]?\d+[.,]\d+\s*mm", re.I)
CAVIDADES = re.compile(r"cavit(?:y|ies|ats?|ies)\s*:?\s*([\d,\s and y]+)", re.I)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfil_correccion (
  documento_id INTEGER, diapositiva INTEGER, feature TEXT, pieza TEXT, ruta TEXT,
  rotulo TEXT, plan TEXT, numero TEXT, cotas TEXT, bloques TEXT, marcador_ok INTEGER,
  magnitudes TEXT, cavidades TEXT, imagenes INTEGER, texto TEXT,
  PRIMARY KEY (documento_id, diapositiva)
);
"""


def cotas(texto: str) -> list[str]:
    m = DIM.search(texto)
    if not m:
        return []
    return re.findall(r"\b\d{1,4}(?:\.\d+)?\b|\bxx\b", m.group(1), re.I)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature")
    args = parser.parse_args()
    con = conectar()
    con.executescript(ESQUEMA)
    filtro, valores = ("AND d.feature = ?", [args.feature]) if args.feature else ("", [])
    con.execute(f"DELETE FROM perfil_correccion WHERE feature = ?" if args.feature else
                "DELETE FROM perfil_correccion", valores)
    filas = con.execute(
        "SELECT d.id, d.feature, d.pieza, d.ruta, e.localizador, e.texto, e.datos FROM elemento e "
        "JOIN documento d ON d.id = e.documento_id WHERE d.ext = 'pptx' AND e.tipo = 'diapositiva' "
        f"AND d.estado = 'extraido' {filtro} ORDER BY d.id, e.orden",
        valores,
    ).fetchall()
    for doc_id, feature, pieza, ruta, loc, texto, datos in filas:
        texto = texto or ""
        titulo = TITULO.search(texto)
        imagenes = len(json.loads(datos).get("imagenes", [])) if datos else 0
        con.execute(
            "INSERT OR REPLACE INTO perfil_correccion VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, int(loc.split()[-1]), feature, pieza, ruta,
             titulo.group(1) if titulo else None,
             titulo.group(2) if titulo else None,
             f"{titulo.group(2)}.{titulo.group(3)}" if titulo else None,
             json.dumps(cotas(texto)),
             json.dumps([k for k, p in BLOQUES.items() if re.search(p, texto, re.I)]),
             int(bool(re.search(r"^\s*OK\s*$", texto, re.M))),
             json.dumps(MM.findall(texto)),
             json.dumps([c.strip() for c in CAVIDADES.findall(texto)]),
             imagenes, texto[:4000]),
        )
    con.commit()
    print(f"Diapositivas perfiladas: {len(filas)}")


if __name__ == "__main__":
    main()
