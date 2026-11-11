"""Ficha de identidad de las piezas: nombre, plano, numero de cliente, referencia ITP, cliente y columnas de cavidad.

Agrega las cabeceras de `perfil_ppap` (hojas DR) y el *Customer Name* de `INTRO!C23` (celdas) por codigo de pieza.
Para cada campo da el valor mayoritario con su recuento y aparte los minoritarios, que en los casos revisados
son plantillas heredadas (I-303) o errores de celda (#REF!). No interpreta: las columnas de cavidad de un
informe no son el numero de cavidades del molde (trampas.md, 7) y el cliente de INTRO es poco fiable (I-005).

    python conocimiento/herramientas/identidad_piezas.py            # escribe conocimiento/identidad-piezas.md
    python conocimiento/herramientas/identidad_piezas.py --salida -  # a la consola
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import BD, CONOCIMIENTO  # noqa: E402
from perfil_ppap import ETIQUETAS, valor_de_campo

SALIDA = CONOCIMIENTO / "identidad-piezas.md"
CAMPOS = (("part_name", "Nombre (cabecera DR)"), ("drawing_no", "Plano"), ("part_no", "Nº pieza cliente"),
          ("itp_ref", "ITP Ref."))
INVALIDOS = {"", "0", "-", "xx", "xxx", "#ref!", "#n/a", "drawing nº level:"}
CLIENTES = {"robert bosch": "Robert Bosch", "bosch": "Robert Bosch", "rb": "Robert Bosch", "b-braun": "B. Braun",
            "autoliv": "Autoliv", "toyoda gosei": "Toyoda Gosei", "lina medical": "Lina Medical", "aisin": "Aisin"}


def valido(v, campo: str = "") -> bool:
    texto = str(v or "").strip()
    if not texto or texto.casefold() in INVALIDOS or texto.startswith("#") or texto.endswith(":"):
        return False
    if campo in {"part_no", "itp_ref", "drawing_no"} and re.fullmatch(
            r"(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2})(?:T.*)?", texto):
        return False
    return True


def referencias(meta: dict) -> list[str]:
    """Codigos explicitos, sin confundir numeros de plano/cliente con proyectos."""
    refs = []
    itp = re.sub(r"[.\s]", "", str(meta.get("itp_ref", "")))
    if re.fullmatch(r"7\d{8}", itp):
        refs.append(itp[1:5])
    ppap = re.search(r"(?<!\d)(\d{4})[-_]\d{2}[_-]in[tf]", str(meta.get("ppap_ref", "")), re.I)
    if ppap:
        refs.append(ppap[1])
    return refs


def clasificar(codigo: str, meta: dict, firmas: dict[str, set[str]]) -> tuple[str, list[str]]:
    """Clasificacion conservadora: contradicciones se conservan junto a la procedencia."""
    avisos = []
    for campo in ("part_no", "itp_ref", "drawing_no"):
        value = str(meta.get(campo, "")).strip()
        if value and not valido(value, campo) and value.casefold() not in INVALIDOS and not value.startswith("#"):
            return "desplazada", [f"{campo} incompatible: {value}"]
    refs = referencias(meta)
    propias = refs.count(codigo)
    ajenas = [v for v in refs if v != codigo]
    coinciden = sum(str(meta.get(k, "")).strip() in firmas.get(k, set())
                   for k in ("part_name", "part_no", "drawing_no"))
    if len(ajenas) >= 2 and len(set(ajenas)) == 1 and not propias:
        return "heredada", [f"ITP y PPAP identifican {ajenas[0]}"]
    if ajenas:
        avisos.append("referencia de otro codigo: " + ", ".join(ajenas))
        if propias and coinciden >= 2:
            return "propia", avisos
        return "conflicto", avisos
    if propias or coinciden >= 2:
        return "propia", avisos
    return "conflicto", ["identidad insuficiente; requiere comprobacion del original"]


def resumen(c: Counter) -> tuple[str, str]:
    """Valor mayoritario (con recuento) y minoritarios."""
    if not c:
        return "no consta", ""
    (top, n), *resto = c.most_common()
    return f"`{top}` ({n})", "; ".join(f"`{v}` ({k})" for v, k in resto)


def recoger(con: sqlite3.Connection) -> dict:
    piezas: dict = defaultdict(lambda: {"features": set(), "docs": 0, "hojas": 0, "campos": defaultdict(Counter),
                                         "invalidos": Counter(), "cav": Counter(), "clientes": Counter(),
                                         "clientes_raw": Counter(), "xxx": 0, "revision": [], "propias": 0})
    for codigo, feature, n in con.execute("SELECT codigo, feature, count(*) FROM documento WHERE codigo IS NOT NULL "
                                          "AND estado != 'duplicado' GROUP BY 1, 2"):
        piezas[codigo]["features"].add(feature)
        piezas[codigo]["docs"] += n
    hojas = []
    for codigo, meta, cav, ruta, hoja, doc in con.execute(
        "SELECT d.codigo, p.metadatos, p.cavidades, d.ruta, p.hoja, d.id FROM perfil_ppap p "
        "JOIN documento d ON d.id=p.documento_id WHERE d.codigo IS NOT NULL ORDER BY d.ruta,p.hoja"):
        m = json.loads(meta or "{}")
        filas = defaultdict(list)
        for fila, col, valor in con.execute(
                "SELECT fila,col,valor FROM celda WHERE documento_id=? AND hoja=? AND fila<12 AND valor IS NOT NULL ORDER BY fila,col",
                (doc, hoja)):
            filas[fila].append((col, str(valor)))
        # Re-read only missing header fields with the documented label variants.
        for items in filas.values():
            for idx, (_, value) in enumerate(items):
                for campo, patron in ETIQUETAS.items():
                    if campo not in m and re.search(patron, value.strip(), re.I):
                        m[campo] = valor_de_campo(patron, [v for _, v in items[idx + 1:]]).strip()
        hojas.append((codigo, m, cav, ruta, hoja))
    candidatas = defaultdict(lambda: defaultdict(Counter))
    for codigo, meta, _, _, _ in hojas:
        refs = referencias(meta)
        if refs and codigo not in refs:
            continue
        if any(not valido(meta[k], k) for k in ("part_name", "drawing_no") if meta.get(k)):
            continue
        for campo in ("part_name", "part_no", "drawing_no"):
            if valido(meta.get(campo), campo):
                candidatas[codigo][campo][str(meta[campo]).strip()] += 1
    firmas = {codigo: {campo: {v for v, n in valores.items() if n > sum(valores.values()) / 2}
                       for campo, valores in campos.items()} for codigo, campos in candidatas.items()}
    for codigo, m, cav, ruta, hoja in hojas:
        p = piezas[codigo]
        p["hojas"] += 1
        estado, avisos = clasificar(codigo, m, firmas.get(codigo, {}))
        if estado != "propia" or avisos:
            p["revision"].append({"ruta": ruta, "hoja": hoja, "estado": estado,
                                  "avisos": avisos, "metadatos": m})
        if estado != "propia":
            continue
        p["propias"] += 1
        for campo, _ in CAMPOS:
            if campo in m:
                (p["campos"][campo] if valido(m[campo], campo) else p["invalidos"])[str(m[campo]).strip()] += 1
        p["cav"][len(json.loads(cav or "[]"))] += 1
    for codigo, valor in con.execute(
            "SELECT d.codigo, v.valor FROM celda c JOIN celda v ON v.documento_id = c.documento_id AND v.hoja = c.hoja "
            "AND v.fila = c.fila AND v.col = c.col + 1 JOIN documento d ON d.id = c.documento_id "
            "WHERE c.valor = 'Customer Name' AND d.codigo IS NOT NULL"):
        p = piezas[codigo]
        bruto = str(valor or "").strip()
        p["clientes_raw"][bruto] += 1
        if bruto.casefold() in ("xxx", ""):
            p["xxx"] += 1
        else:
            p["clientes"][CLIENTES.get(bruto.casefold(), bruto)] += 1
    return piezas


def markdown(piezas: dict) -> str:
    lineas = [
        "# Identidad de las piezas",
        "",
        "> **Generado** por `herramientas/identidad_piezas.py` desde la biblioteca; no editar a mano, regenerar.",
        "> Valores principales solo de hojas clasificadas como propias por referencias y campos coherentes.",
        "> Es una clasificacion heuristica revisable: los conflictos y exclusiones conservan su procedencia debajo.",
        "> Recuentos: hojas DR de `perfil_ppap` (cabeceras) y libros con `INTRO!C23` (*Customer Name*). Entre",
        "> paréntesis, cuántas hojas o libros dan ese valor. Los minoritarios suelen ser plantillas heredadas",
        "> ([I-303](incongruencias.md)) o errores de celda; el cliente de INTRO es poco fiable ([I-005](incongruencias.md)):",
        "> `XXX` es el valor de la plantilla sin rellenar. Las **columnas de cavidad** de un informe no son las",
        "> cavidades del molde ([trampas](trampas.md), 7): para eso, la ficha de la pieza. «⚠ minoría»: el cliente",
        "> solo consta en menos de la mitad de los libros; no basta para atribuirlo (3206: un libro con la",
        "> plantilla del 3247, I-303).",
        "",
        "| Pieza | Feature | Nombre | Plano | Nº pieza cliente | ITP Ref. | Cliente (INTRO!C23) | Columnas de cavidad | Hojas DR · docs |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    rarezas = []
    for codigo in sorted(piezas):
        p = piezas[codigo]
        celdas = []
        for campo, nombre in CAMPOS:
            top, resto = resumen(p["campos"][campo])
            celdas.append(top)
            if resto:
                rarezas.append(f"- **{codigo}** · {nombre}: {resto}")
        _, otros = resumen(p["clientes"])
        libros = sum(p["clientes_raw"].values())
        if p["clientes"]:
            top, n = p["clientes"].most_common(1)[0]
            # p. ej. 3206: el unico valor distinto de XXX es B-Braun, de una plantilla del 3247 (I-303)
            cliente = f"`{top}` ({n} de {libros})" + (" ⚠ minoría" if 2 * n < libros else "")
        else:
            cliente = f"no consta ({libros} libros)" if libros else "—"
        if p["xxx"]:
            cliente += f" · `XXX` en {p['xxx']}"
        if otros:
            rarezas.append(f"- **{codigo}** · Cliente: {otros}")
        variantes = sorted(v for v in p["clientes_raw"] if v and v.casefold() != "xxx")
        if len(variantes) > 1:
            rarezas.append(f"- **{codigo}** · Cliente escrito como: " + ", ".join(f"`{v}`" for v in variantes))
        cav = ", ".join(f"{n} ({k})" for n, k in p["cav"].most_common(3)) or "—"
        features = ", ".join(sorted(f for f in p["features"] if f))
        celdas_fila = [f"**{codigo}**", features, *celdas, cliente, cav, f"{p['hojas']} · {p['docs']}"]
        lineas.append("| " + " | ".join(celdas_fila) + " |")
        if p["invalidos"]:
            rarezas.append(f"- **{codigo}** · Valores no válidos en cabeceras: "
                           + "; ".join(f"`{v or '(vacío)'}` ({k})" for v, k in p["invalidos"].most_common()))
    lineas += ["", "## Valores minoritarios y no válidos", "",
               "Revisar antes de usar un campo para identificar la pieza. Un valor de otra pieza en una hoja",
               "(p. ej. `BSG-296-00` o `732470000`, del 3247/3288) indica una plantilla reutilizada sin actualizar.", "",
               *rarezas, ""]
    lineas += ["## Fuentes complementarias revisadas", "",
               "- **3288 · Nº pieza cliente: 508008**, `4- Tetones/3288/6- Método de medición/MM732880000.pdf`, p. 1.",
               "  Las cabeceras propias DR contienen 0; esta referencia procede del método, no del agregado DR.", "",
               "## Conflictos y hojas excluidas", "",
               "Las hojas propias con aviso participan en el agregado. Heredadas, desplazadas y conflictos sin resolver no.", ""]
    for codigo in sorted(piezas):
        p = piezas[codigo]
        lineas.append(f"### {codigo}: {p['propias']} propias de {p['hojas']} hojas")
        lineas.append("")
        for r in p["revision"]:
            campos = "; ".join(f"{k}={v}" for k, v in r["metadatos"].items() if k in {"itp_ref", "ppap_ref", "part_no"})
            lineas.append(f"- `{r['ruta']}!{r['hoja']}`: **{r['estado']}**. {'; '.join(r['avisos'])}. {campos}")
        lineas.append("")
    return "\n".join(linea.rstrip() for linea in lineas).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(SALIDA), help="fichero de salida o '-' para la consola")
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
    texto = markdown(recoger(con))
    if args.salida == "-":
        sys.stdout.reconfigure(encoding="utf-8")
        print(texto)
    else:
        Path(args.salida).write_text(texto, encoding="utf-8")
        print(f"Escrito {args.salida}")


if __name__ == "__main__":
    main()
