"""Catálogo de los PDF de planos (`conocimiento/planos.jsonl`) y revisiones que citan los informes.

Comprueba el catálogo (formato de cada registro: páginas, fechas, procedencia; coherencia entre copias
idénticas; rutas, SHA-256 y cobertura frente a la biblioteca) y escribe las tablas generadas de
`conocimiento/planos.md`: resumen por pieza, inventario de los PDF y revisión del plano que cita la
cabecera de cada informe (`perfil_ppap`), con la celda de donde sale y la fecha tal como está escrita.
**Solo lee la biblioteca** (`mode=ro`); el catálogo es la fuente y se edita a mano, con la evidencia de
cada registro.

    python conocimiento/herramientas/planos_catalogo.py              # comprueba y reescribe las tablas
    python conocimiento/herramientas/planos_catalogo.py --comprobar  # sin escribir; código 1 si algo no cuadra
    python conocimiento/herramientas/planos_catalogo.py --detalle 3233   # cabeceras hoja a hoja de una pieza
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import BD, CONOCIMIENTO  # noqa: E402
from perfil_ppap import ETIQUETAS, es_etiqueta  # noqa: E402

CATALOGO = CONOCIMIENTO / "planos.jsonl"
DOCUMENTO = CONOCIMIENTO / "planos.md"
# Mismo criterio que PLANOS_SQL del visor (prototypes/data-explorer/conocimiento/datos.py), con las copias idénticas.
FILTRO = ("ext='pdf' AND estado IN ('sin_texto','extraido','duplicado') AND (carpeta_norm='pieza_2d3d'"
          " OR lower(ruta) LIKE '%ballo%' OR lower(ruta) LIKE '%balon%' OR lower(ruta) LIKE '%drw%')")
CAMPOS = ("documento_id", "ruta", "sha256", "carpeta_pieza", "copia_de", "fecha_nombre", "papel", "globos", "planos",
          "verificacion", "procedencia", "evidencia", "nota", "revisado")
CAMPOS_PLANO = ("numero", "componente", "paginas", "revision", "tipo", "fecha_cambio", "cambio", "fecha_emision", "pieza")
# Lo que describe el dibujo: debe coincidir entre copias idénticas byte a byte.
CAMPOS_DIBUJO = ("papel", "globos", "planos", "procedencia")
PAPELES = {"plano", "plano con globos", "plano con marcas"}
# Comprobación del registro (`verificacion`) y, por campo cuando difiere, `procedencia` ({campo: fuente}).
FUENTE = r"visto|capa de texto|nombre del fichero|inferido|inferido de \d+|documentado"
VERIFICACION = re.compile(rf"^({FUENTE}|copia idéntica de \d+)$")
PROCEDENCIA = re.compile(rf"^({FUENTE})$")
FECHA = re.compile(r"^\d{4}-\d\d-\d\d$")
MES = re.compile(r"^\d{4}-\d\d$")


def conectar_lectura() -> sqlite3.Connection:
    return sqlite3.connect(BD.resolve().as_uri() + "?mode=ro", uri=True)


def leer_catalogo() -> list[dict]:
    return [json.loads(linea) for linea in CATALOGO.read_text(encoding="utf-8").splitlines() if linea.strip()]


def fecha_correcta(valor, mes_permitido: bool = False) -> bool:
    """None, AAAA-MM-DD de calendario o, si se permite, AAAA-MM (precisión mensual de las firmas de Aisin)."""
    if valor is None:
        return True
    if not isinstance(valor, str):
        return False
    try:
        if FECHA.match(valor):
            date.fromisoformat(valor)
            return True
        if mes_permitido and MES.match(valor):
            date.fromisoformat(valor + "-01")
            return True
    except ValueError:
        return False
    return False


def comprobar_registro(r: dict) -> list[str]:
    """Campos y formato de un registro, sin biblioteca."""
    i = r.get("documento_id")
    faltan = [c for c in CAMPOS if c not in r]
    if faltan:
        return [f"{i}: faltan {faltan}"]
    problemas = []
    if r["papel"] not in PAPELES:
        problemas.append(f"{i}: papel desconocido {r['papel']!r}")
    if not isinstance(r["globos"], bool):
        problemas.append(f"{i}: globos debe ser true/false")
    if not VERIFICACION.match(r["verificacion"] or ""):
        problemas.append(f"{i}: verificación desconocida {r['verificacion']!r}")
    if not isinstance(r["procedencia"], dict):
        problemas.append(f"{i}: procedencia debe ser un objeto {{campo: fuente}}")
    else:
        for campo, fuente in r["procedencia"].items():
            if campo not in CAMPOS_PLANO:
                problemas.append(f"{i}: procedencia de un campo desconocido {campo!r}")
            if not PROCEDENCIA.match(fuente or ""):
                problemas.append(f"{i}: fuente desconocida {fuente!r} para {campo}")
    if not r["evidencia"]:
        problemas.append(f"{i}: sin evidencia")
    if not fecha_correcta(r["fecha_nombre"]):
        problemas.append(f"{i}: fecha_nombre no válida {r['fecha_nombre']!r}")
    if not isinstance(r["planos"], list) or not r["planos"]:
        return problemas + [f"{i}: sin planos"]
    for p in r["planos"]:
        if [c for c in CAMPOS_PLANO if c not in p] or not p.get("numero"):
            problemas.append(f"{i}: plano incompleto {p}")
            continue
        pags = p["paginas"]
        if (not isinstance(pags, list) or not pags or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in pags)
                or pags != sorted(set(pags))):
            problemas.append(f"{i}: páginas no válidas en {p['numero']}: {pags!r}")
        if not fecha_correcta(p["fecha_cambio"]):
            problemas.append(f"{i}: fecha_cambio no válida en {p['numero']}: {p['fecha_cambio']!r}")
        if not fecha_correcta(p["fecha_emision"], mes_permitido=True):
            problemas.append(f"{i}: fecha_emision no válida en {p['numero']}: {p['fecha_emision']!r}")
    paginas = [n for p in r["planos"] if isinstance(p.get("paginas"), list) for n in p["paginas"]]
    if len(r["planos"]) > 1 and len(paginas) != len(set(paginas)):
        problemas.append(f"{i}: dos planos del mismo PDF comparten página")
    return problemas


def comprobar_copias(catalogo: list[dict]) -> list[str]:
    """Una copia idéntica byte a byte describe el mismo dibujo que su original."""
    por_id = {r.get("documento_id"): r for r in catalogo}
    problemas = []
    for r in catalogo:
        original = por_id.get(r.get("copia_de"))
        if r.get("copia_de") is None:
            continue
        if original is None:
            problemas.append(f"{r['documento_id']}: su original {r['copia_de']} no está en el catálogo")
            continue
        distintos = [c for c in CAMPOS_DIBUJO if r.get(c) != original.get(c)]
        if distintos:
            problemas.append(f"{r['documento_id']}: copia idéntica de {r['copia_de']} con {', '.join(distintos)} distintos")
    return problemas


def comprobar_catalogo(con: sqlite3.Connection, catalogo: list[dict]) -> list[str]:
    """Formato de cada registro, coherencia entre copias, y rutas, SHA-256 y cobertura frente a la biblioteca."""
    problemas = []
    docs = {r[0]: r for r in con.execute(f"SELECT id, ruta, sha256, codigo, duplicado_de FROM documento WHERE {FILTRO}")}
    vistos = set()
    for r in catalogo:
        i = r.get("documento_id")
        if i in vistos:
            problemas.append(f"{i}: repetido en el catálogo")
        vistos.add(i)
        problemas += comprobar_registro(r)
        if i not in docs:
            problemas.append(f"{i}: no es un PDF de plano de la biblioteca")
            continue
        _, ruta, sha, codigo, dup = docs[i]
        if r.get("ruta") != ruta:
            problemas.append(f"{i}: ruta distinta de la biblioteca")
        if r.get("sha256") != sha:
            problemas.append(f"{i}: SHA-256 distinto de la biblioteca")
        if r.get("carpeta_pieza") != codigo:
            problemas.append(f"{i}: carpeta_pieza {r.get('carpeta_pieza')} frente a {codigo}")
        if r.get("copia_de") != dup:
            problemas.append(f"{i}: copia_de {r.get('copia_de')} frente a duplicado_de {dup}")
    problemas += comprobar_copias(catalogo)
    problemas += [f"{i}: PDF de plano de la biblioteca que no está en el catálogo ({docs[i][1]})"
                  for i in sorted(set(docs) - vistos)]
    return problemas


def letra(col: int) -> str:
    s = ""
    while col:
        col, resto = divmod(col - 1, 26)
        s = chr(65 + resto) + s
    return s


def celda_de_campo(filas: dict[int, dict[int, str]], patron: str) -> str | None:
    """La celda del valor de un campo de la cabecera, con la regla de `perfil_ppap.valor_de_campo`."""
    for fila in sorted(filas):
        items = sorted(filas[fila].items())
        for n, (_, texto) in enumerate(items):
            if re.search(patron, texto.strip(), re.I):
                for col, valor in items[n + 1:]:
                    if not valor.strip():
                        continue
                    if es_etiqueta(valor):
                        if re.search(patron, valor.strip(), re.I):
                            continue
                        return None
                    return f"{letra(col)}{fila}"
                return None
    return None


def normalizar_fecha(literal: str | None) -> str | None:
    """Fecha AAAA-MM-DD de la cabecera cuando el literal es una sola fecha; si no, None.

    Admite ISO (con o sin hora), DD/MM/AAAA y DD.MM.AAAA. Rangos ('29.08.2024-4.9.2024'), texto ('TM April 2025'),
    'xx' y el cero de Excel ('1899-12-31') dan None (I-304). El literal se conserva aparte, sin recortar."""
    if not literal:
        return None
    t = literal.strip()
    m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d)(?:[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?)?", t)
    if m:
        a, mes, d = m.groups()
    else:
        m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t)
        if not m:
            return None
        d, mes, a = m.groups()
    try:
        fecha = date(int(a), int(mes), int(d))
    except ValueError:
        return None
    return fecha.isoformat() if fecha.year >= 1950 else None


def cabeceras(con: sqlite3.Connection, piezas: list[str]) -> list[dict]:
    """Una fila por hoja con plano o revisión en la cabecera: archivo (cada copia por separado), hoja, literal y celda."""
    marcas = ",".join("?" * len(piezas))
    hojas = {}
    for doc, hoja, codigo, ruta, fila_cab, meta in con.execute(
            f"SELECT p.documento_id, p.hoja, d.codigo, d.ruta, p.fila_cabecera, p.metadatos FROM perfil_ppap p "
            f"JOIN documento d ON d.id = p.documento_id WHERE d.codigo IN ({marcas})", piezas):
        m = json.loads(meta or "{}")
        if m.get("drawing_no") is None and m.get("drawing_level") is None:
            continue
        literal_fecha = m.get("report_date")
        literal_fecha = None if literal_fecha is None else str(literal_fecha)
        hojas[(doc, hoja)] = dict(pieza=codigo, ruta=ruta, hoja=hoja, plano=m.get("drawing_no"),
                                  revision=m.get("drawing_level"), fecha_literal=literal_fecha,
                                  fecha=normalizar_fecha(literal_fecha), fila_cabecera=fila_cab, celdas=defaultdict(dict))
    docs = sorted({d for d, _ in hojas})
    for n in range(0, len(docs), 500):
        lote = docs[n:n + 500]
        for doc, hoja, fila, col, valor in con.execute(
                f"SELECT c.documento_id, c.hoja, c.fila, c.col, c.valor FROM celda c JOIN perfil_ppap p "
                f"ON p.documento_id = c.documento_id AND p.hoja = c.hoja WHERE c.fila < p.fila_cabecera "
                f"AND c.documento_id IN ({','.join('?' * len(lote))})", lote):
            h = hojas.get((doc, hoja))
            if h is not None and valor is not None:
                h["celdas"][fila][col] = str(valor)
    salida = []
    for h in hojas.values():
        h["celda_plano"] = celda_de_campo(h["celdas"], ETIQUETAS["drawing_no"])
        h["celda_revision"] = celda_de_campo(h["celdas"], ETIQUETAS["drawing_level"])
        del h["celdas"]
        salida.append(h)
    return sorted(salida, key=lambda h: (h["pieza"], h["fecha"] or "", h["ruta"], h["hoja"]))


def literal(valor: str | None) -> str:
    if valor is None:
        return "—"
    return f"`{valor}`" if valor.strip() else "(vacío)"


def relativa(ruta: str, codigo: str) -> str:
    """Ruta desde la carpeta de la pieza ('3205/', '3212 Pump Housing/')."""
    partes = ruta.split("/")
    for n, parte in enumerate(partes):
        if parte == codigo or parte.startswith(codigo + " "):
            return "/".join(partes[n + 1:])
    return ruta


def tabla_resumen(catalogo: list[dict]) -> str:
    por_pieza = defaultdict(list)
    for r in catalogo:
        por_pieza[r["carpeta_pieza"]].append(r)
    filas = ["| Pieza | PDF | Copias idénticas | Con globos | Dibujos distintos¹ | Números de plano | Planos de otra pieza o sin asignar |",
             "|---|---:|---:|---:|---:|---|---:|"]
    for pieza in sorted(por_pieza):
        rs = por_pieza[pieza]
        dibujos = {(p["numero"], p["componente"], p["revision"], p["fecha_cambio"]) for r in rs for p in r["planos"]}
        numeros = sorted({p["numero"] for r in rs for p in r["planos"]})
        ajenos = sum(1 for r in rs if any(p["pieza"] != pieza for p in r["planos"]))
        filas.append(f"| {pieza} | {len(rs)} | {sum(1 for r in rs if r['copia_de'])} | {sum(1 for r in rs if r['globos'])} "
                     f"| {len(dibujos)} | {', '.join(f'`{n}`' for n in numeros)} | {ajenos or ''} |")
    filas.append("")
    filas.append("¹ Número, componente, revisión y fecha del último cambio distintos. Es un recuento informativo: "
                 "qué debe contar la columna «Planos» del visor está sin decidir.")
    return "\n".join(filas)


def tabla_inventario(catalogo: list[dict]) -> str:
    filas = ["| Pieza | Id | PDF | Plano · revisión | Tipo | Último cambio | Globos | Comprobado |",
             "|---|---:|---|---|---|---|---|---|"]
    for r in sorted(catalogo, key=lambda r: (r["carpeta_pieza"], min(p["fecha_cambio"] or "9" for p in r["planos"]), r["ruta"])):
        planos = "; ".join(
            f"`{p['numero']}` {p['revision'] or '?'}" + (f" ({p['componente']}, p. {','.join(map(str, p['paginas']))})"
                                                       if p["componente"] and len(r["planos"]) > 1 else
                                                       f" ({p['componente']})" if p["componente"] else "")
            + ("" if p["pieza"] == r["carpeta_pieza"] else f" — pieza: {p['pieza'] or 'pendiente'}")
            for p in r["planos"])
        tipos = "; ".join(sorted({p["tipo"] for p in r["planos"] if p["tipo"]})) or "—"
        cambios = "; ".join(sorted({p["fecha_cambio"] for p in r["planos"] if p["fecha_cambio"]})) or "—"
        globos = {"plano con marcas": "marcas"}.get(r["papel"], "sí" if r["globos"] else "no")
        copia = f" = {r['copia_de']}" if r["copia_de"] else ""
        comprobado = r["verificacion"] + "".join(f"; {NOMBRE_CAMPO.get(c, c)}: {f}" for c, f in sorted(r["procedencia"].items()))
        filas.append(f"| {r['carpeta_pieza']} | {r['documento_id']}{copia} | `{relativa(r['ruta'], r['carpeta_pieza'])}` "
                     f"| {planos} | {tipos} | {cambios} | {globos} | {comprobado} |")
    return "\n".join(filas)


NOMBRE_CAMPO = {"revision": "revisión", "fecha_cambio": "fecha del cambio", "fecha_emision": "emisión",
                "paginas": "páginas", "numero": "número"}


def tabla_cabeceras(hojas: list[dict]) -> str:
    grupos = defaultdict(list)
    for h in hojas:
        grupos[(h["pieza"], h["plano"], h["revision"])].append(h)
    filas = ["| Pieza | Plano (literal) | Revisión (literal) | Libros | Hojas | Fechas de cabecera | Primera hoja (archivo · hoja · celdas) |",
             "|---|---|---|---:|---:|---|---|"]
    clave = lambda h: (h["fecha"] or "9", h["ruta"], h["hoja"])  # noqa: E731
    for (pieza, plano, revision), hs in sorted(grupos.items(), key=lambda kv: (kv[0][0], min(map(clave, kv[1])))):
        fechas = sorted(h["fecha"] for h in hs if h["fecha"])
        rango = (fechas[0] if fechas[0] == fechas[-1] else f"{fechas[0]} … {fechas[-1]}") if fechas else "—"
        sin = len(hs) - len(fechas)
        if sin and fechas:
            rango += f" ({sin} sin fecha válida)"
        p = min(hs, key=clave)
        celdas = " / ".join(c for c in (p["celda_plano"], p["celda_revision"]) if c) or "?"
        filas.append(f"| {pieza} | {literal(plano)} | {literal(revision)} | {len({h['ruta'] for h in hs})} | {len(hs)} | {rango} "
                     f"| `{relativa(p['ruta'], pieza)}` · `{p['hoja']}` · {celdas} |")
    return "\n".join(filas)


BLOQUES = ("resumen", "inventario", "cabeceras")


def generar(con: sqlite3.Connection, catalogo: list[dict]) -> dict[str, str]:
    piezas = sorted({r["carpeta_pieza"] for r in catalogo})
    return {"resumen": tabla_resumen(catalogo), "inventario": tabla_inventario(catalogo),
            "cabeceras": tabla_cabeceras(cabeceras(con, piezas))}


def sustituir(texto: str, bloques: dict[str, str]) -> str:
    for nombre, contenido in bloques.items():
        patron = re.compile(rf"(<!-- planos-{nombre}:inicio -->\n)(?:.*?\n)?(<!-- planos-{nombre}:fin -->)", re.S)
        if not patron.search(texto):
            raise SystemExit(f"Falta el marcador planos-{nombre} en {DOCUMENTO.name}")
        texto = patron.sub(lambda m: m[1] + contenido + "\n" + m[2], texto)
    return texto


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--comprobar", action="store_true", help="no escribe; falla si algo no cuadra o la tabla está desfasada")
    parser.add_argument("--detalle", metavar="PIEZA", help="cabeceras hoja a hoja de una pieza")
    args = parser.parse_args()
    con = conectar_lectura()
    catalogo = leer_catalogo()
    if args.detalle:
        print("ruta | hoja | plano (celda) | revisión (celda) | fecha de cabecera (literal) | fecha normalizada")
        for h in cabeceras(con, [args.detalle]):
            print(f"{h['ruta']} | {h['hoja']} | {h['plano']!r} ({h['celda_plano']}) | {h['revision']!r} ({h['celda_revision']}) "
                  f"| {h['fecha_literal']!r} | {h['fecha'] or '—'}")
        return
    problemas = comprobar_catalogo(con, catalogo)
    print("\n".join(problemas) or f"planos.jsonl: {len(catalogo)} registros, sin problemas")
    actual = DOCUMENTO.read_text(encoding="utf-8")
    nuevo = sustituir(actual, generar(con, catalogo))
    if args.comprobar:
        if nuevo != actual:
            problemas.append("planos.md: tablas desfasadas")
            print("planos.md: tablas desfasadas; ejecutar sin --comprobar")
        sys.exit(1 if problemas else 0)
    if problemas:
        sys.exit(1)
    if nuevo != actual:
        DOCUMENTO.write_text(nuevo, encoding="utf-8")
        print("planos.md: tablas actualizadas")
    else:
        print("planos.md: sin cambios")


if __name__ == "__main__":
    main()
