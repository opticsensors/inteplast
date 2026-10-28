"""Perfil de los planes de correccion de molde (PPTX) de todas las piezas.

Por diapositiva: numero de correccion (plan.n), cotas citadas (`DIM. Nr.`, `DIM.`, `DIM#`, `Dim Nº`),
bloques de la plantilla presentes, marcador OK, magnitudes en mm y cavidades citadas. Mide cuanto
se parecen a la plantilla del piloto 3212. Tabla derivada `perfil_correccion` (se recalcula).

`cotas` guarda los codigos normalizados (sin ceros a la izquierda: `DIM. Nr.02` -> `2`, `XX` en
mayusculas) y `cotas_texto` los fragmentos literales de donde salen. `cotas_ambiguas` guarda las citas que no
se pueden leer solo con el texto: un nominal sin numero de cota (`Dim 7,5+0,1`) o `DIM. Nr.45,1`, que puede
ser la lista 45, 1 o el subpunto 45.1; `cadena_correcciones.py` las resuelve con las medidas de la pieza. No se expanden los rangos
(`1906 to 1912` da los dos extremos) ni se leen cotas citadas sin `DIM` (`Flatness Nº680`, `cota 17`).

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
# Lista de codigos tras DIM: `DIM. Nr. 54, 57 and 60`, `DIM. Nr.06-7-8-83`, `DIM.3320`, `DIM#6:`,
# `Dim Nº630 Ø66+0,1-0,03` (la lista acaba donde empieza el nominal), `DIM. Nr.2207 i 2210`, y las
# variantes escritas a mano: `208+209`, `2801, 2800, )`, `700,702,704`, `191 104, 152  i 154`,
# `230 and Nr. 1330`. Tras un simple espacio, un codigo no puede ir seguido de coma decimal:
# en `DIM. Nr.137 11,5±0,2` (si se pierde la flecha) el 11 es el nominal, no otra cota.
# Subpunto con coma (3195: `DIM.Nr.4100,1`): una o dos cifras tras una cota de tres o mas, sin mas cifras;
# `700,702` y `8,12` siguen siendo listas. `3900.1.2.3.4.5.6.7` (3195, 2.8) abrevia 3900.1 … 3900.7.
CODIGO = r"(?:XX|\d{3,},\d{1,2}(?![\d,])|\d+(?:\.\d+)*)(?!\d)"
NR = r"(?:n\s*[rº°o]?\s*\.?\s*)?"
SEPARADOR = r"\s*(?:,|;|/|&|\+|-|\band\b|\by\b|\bi\b|\bund\b|\bto\b)\s*"
LISTA = CODIGO + r"(?:" + SEPARADOR + NR + CODIGO + r"|\s+" + NR + CODIGO + r"(?!,\d))*"
DIM = re.compile(r"\bdim\b\s*[.#]?\s*:?\s*" + NR + "(" + LISTA + ")", re.I)   # 3174 loop 9: `move dim.: 202`
# Planes 4-6 del 3195: `Tool correction 5.3 dimension 3970`; una sola cota, sin coma decimal (`dimension 0,3` no).
# Checo en los loops 8-9 del 3174: `Korekce rozměru 210`, `posuňte rozměr 202`.
DIMENSION = re.compile(r"\b(?:dimension|rozm[eě]r[uůy]?)\s+(\d{2,}(?:\.\d+)?)(?![\d,]|\.\d)", re.I)
# Revision del 28/10/2026. `Dim 7,5+0,1` (3051, plan N4): tras DIM viene el nominal con su tolerancia, no un codigo.
NOMINAL_TRAS_DIM = re.compile(r"\d{1,3},\d{1,3}\s*(?:[+±]|[-−–]\s*\d)")
# `DIM. Nr.45,1` (3214): una cita sola de dos numeros cortos separados por coma; lista o subpunto segun la pieza.
LISTA_O_SUBPUNTO = re.compile(r"(\d{1,2}),(\d{1,2})")
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
  magnitudes TEXT, cavidades TEXT, imagenes INTEGER, texto TEXT, cotas_texto TEXT, cotas_ambiguas TEXT,
  PRIMARY KEY (documento_id, diapositiva)
);
"""
COLUMNAS = ("documento_id, diapositiva, feature, pieza, ruta, rotulo, plan, numero, cotas, bloques, "
            "marcador_ok, magnitudes, cavidades, imagenes, texto, cotas_texto, cotas_ambiguas")


def normalizar_cota(codigo: str) -> str:
    if codigo.upper() == "XX":
        return "XX"
    entero, _, resto = codigo.replace(",", ".").partition(".")
    return (entero.lstrip("0") or "0") + (f".{resto}" if resto else "")


def expandir_subpuntos(codigo: str) -> list[str]:
    """`3900.1.2.3` -> 3900.1, 3900.2, 3900.3 si los subpuntos son consecutivos; si no, el codigo tal cual."""
    partes = codigo.split(".")
    subpuntos = partes[1:]
    if len(subpuntos) >= 2 and all(p.isdigit() and len(p) <= 2 for p in subpuntos) \
            and all(int(b) == int(a) + 1 for a, b in zip(subpuntos, subpuntos[1:])):
        return [f"{partes[0]}.{p}" for p in subpuntos]
    return [codigo]


def analizar_citas(texto: str) -> tuple[list[str], list[str], list[dict]]:
    """Codigos normalizados (sin repetir, en orden), fragmentos literales de cada cita DIM y citas ambiguas."""
    texto = texto or ""
    codigos: list[str] = []
    fragmentos: list[str] = []
    ambiguas: list[dict] = []
    for m in sorted([*DIM.finditer(texto), *DIMENSION.finditer(texto)], key=lambda x: x.start()):
        if m.re is DIM and NOMINAL_TRAS_DIM.match(texto, m.start(1)):
            ambiguas.append({"literal": m.group(0).strip(), "tipo": "nominal_sin_cota"})
            continue
        corta = LISTA_O_SUBPUNTO.fullmatch(m.group(1)) if m.re is DIM else None
        if corta:
            ambiguas.append({"literal": m.group(0).strip(), "tipo": "lista_o_subpunto",
                             "lista": [normalizar_cota(corta.group(1)), normalizar_cota(corta.group(2))],
                             "subpunto": normalizar_cota(m.group(1))})
            continue
        fragmentos.append(m.group(0))
        for codigo in re.findall(CODIGO, m.group(1), re.I):
            for normal in expandir_subpuntos(normalizar_cota(codigo)):
                if normal not in codigos:
                    codigos.append(normal)
    return codigos, fragmentos, ambiguas


def citas_dim(texto: str) -> tuple[list[str], list[str]]:
    """Codigos normalizados (sin repetir, en orden) y fragmentos literales de cada cita DIM."""
    return analizar_citas(texto)[:2]


def cotas(texto: str) -> list[str]:
    return citas_dim(texto)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature")
    args = parser.parse_args()
    con = conectar()
    con.executescript(ESQUEMA)
    existentes = {c[1] for c in con.execute("PRAGMA table_info(perfil_correccion)")}
    for columna in ("cotas_texto", "cotas_ambiguas"):
        if columna not in existentes:
            con.execute(f"ALTER TABLE perfil_correccion ADD COLUMN {columna} TEXT")
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
        codigos, fragmentos, ambiguas = analizar_citas(texto)
        imagenes = len(json.loads(datos).get("imagenes", [])) if datos else 0
        con.execute(
            f"INSERT OR REPLACE INTO perfil_correccion ({COLUMNAS}) VALUES ({','.join('?' * 17)})",
            (doc_id, int(loc.split()[-1]), feature, pieza, ruta,
             titulo.group(1) if titulo else None,
             titulo.group(2) if titulo else None,
             f"{titulo.group(2)}.{titulo.group(3)}" if titulo else None,
             json.dumps(codigos),
             json.dumps([k for k, p in BLOQUES.items() if re.search(p, texto, re.I)]),
             int(bool(re.search(r"^\s*OK\s*$", texto, re.M))),
             json.dumps(MM.findall(texto)),
             json.dumps([c.strip() for c in CAVIDADES.findall(texto)]),
             imagenes, texto[:4000], json.dumps(fragmentos, ensure_ascii=False), json.dumps(ambiguas, ensure_ascii=False)),
        )
    con.commit()
    print(f"Diapositivas perfiladas: {len(filas)}")


if __name__ == "__main__":
    main()
