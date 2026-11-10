"""Lee una sola vez los planos sin .icp y decide su tag. El visor solo consulta lo que deja aquí.

    python leer_planos.py                # los que falten, con 4 procesos
    python leer_planos.py --doc 2243     # uno concreto (rehace su lectura)
    python leer_planos.py --tabla        # escribe la tabla de conocimiento/planos-globos.md

Tres lectores, según lo que trae el plano, todos de `lectores_planos.py` (el mismo código que
usan los scripts de medida del prototipo; desde el 09/11/2026, ya no el de la aplicación final):
- Globos de color: detección, orientación y lector combinado (RapidOCR + lector propio en ONNX).
- `[]210` y `No. 200`: OCR por teselas del plano muy ampliado, en horizontal y en vertical.
- Números en rectángulos, también girados: se detecta el rectángulo y se lee solo su interior.

Los dos últimos se probaron solo en el 2820, el 3174, el 3186 y el 3214. Todo son lecturas
automáticas: pueden fallar sin avisar y no sustituyen a un `.icp`. Aquí solo se decide qué
lector vale para cada plano (su tag) y se guarda el resultado.
Resultado en out/conocimiento/lecturas/, fuera de Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import re
import sys
import time
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402

sys.path.insert(0, str(datos.EXPLORER))
import lectores_planos as lectores  # noqa: E402

VERSION = 1

# Decisión del tag. Los falsos globos (cotas resaltadas, dibujo en azul) tienen aros, pero no números.
MIN_GLOBOS, MIN_GLOBOS_LEIDOS = 20, .4
MIN_MARCAS = 20  # marcas `[]` o `No.` para considerar numerado el plano
MIN_COBERTURA_TEXTO = .8  # parte de las cotas de los informes presente como número en la capa de texto
MIN_COTAS = 10
MIN_RECUADROS, MIN_COBERTURA_RECUADROS = 15, .5
POCO_TEXTO = 50  # con menos palabras en la página, se considera que no hay capa de texto


# ---------------------------------------------------------------- cotas de los informes

def base_cota(cota: str) -> str:
    return re.sub(r"^N", "", cota).split(".")[0].split("/")[0]


def cotas_informes(c, codigo: str) -> set[str]:
    filas = c.execute("SELECT DISTINCT m.cota FROM medida_dr m JOIN documento d ON d.id=m.documento_id WHERE d.codigo=?", (codigo,))
    return {b for (cota,) in filas if cota and re.fullmatch(r"\d{1,4}", b := base_cota(cota))}


def cobertura(numeros: set[str], cotas: set[str]) -> float:
    return len(numeros & cotas) / len(cotas) if len(cotas) >= MIN_COTAS else 0.


def decide_tag(detectados: int, leidos: int, marcas: int, recuadros: int, cob_recuadros: float, cob_texto: float) -> str:
    if detectados >= MIN_GLOBOS and leidos / detectados >= MIN_GLOBOS_LEIDOS:
        return "globos"
    if marcas >= MIN_MARCAS or cob_texto >= MIN_COBERTURA_TEXTO:
        return "numerado"
    if recuadros >= MIN_RECUADROS and cob_recuadros >= MIN_COBERTURA_RECUADROS:
        return "numerado"
    return "nada"


# ---------------------------------------------------------------- un plano

_motor = None
_lector = None


def herramientas():
    """Una instancia por proceso: cargar los modelos cuesta segundos."""
    global _motor, _lector
    if _motor is None:
        from rapidocr_onnxruntime import RapidOCR

        _motor, _lector = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1), lectores.own_reader()
        if _lector is None:
            raise RuntimeError(f"No se ha podido cargar el lector de globos: {lectores.MODELO}")
    return _motor, _lector


def firma(ruta: Path) -> dict:
    return {"sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(), "version": VERSION, "lector": lectores.reader_id()}


def lee_globos(ruta: Path, page, motor, lector) -> tuple[list[dict], int, str]:
    """Globos de color: lecturas ofrecidas, detectados y fuente. Con menos de MIN_GLOBOS no se leen."""
    globos, fuente = lectores.read_page_balloons(ruta, page, motor, lector, min_balloons=MIN_GLOBOS)
    if len(globos) < MIN_GLOBOS:
        return [], len(globos), fuente
    salida = []
    for globo in globos:
        if globo["candidates"]:
            x0, y0, x1, y1 = globo["box"]
            combinada = globo["candidates"][0]["readings"][0]
            salida.append({"p": page.number + 1, "t": combinada["text"], "s": combinada["score"], "via": "globo",
                           "x": round((x0 + x1) / 2, 5), "y": round((y0 + y1) / 2, 5),
                           "w": round(x1 - x0, 5), "h": round(y1 - y0, 5)})
    return salida, len(globos), fuente


def lee_plano(doc: int, detalle: bool = False) -> dict:
    """Lecturas y tag de un plano, sin guardar nada.

    Con `detalle` añade lo que encontraron los lectores de marcas y recuadros aunque el tag no lo use,
    y el texto del OCR por página (lo usa probar_lectores_numerados.py). Las lecturas son las mismas.
    """
    p = datos.plano(doc)
    ruta = Path(datos.original(p["ruta"]))
    local, motivo = datos.estado_onedrive(p["ruta"])
    if not local:
        return {"doc": doc, "error": motivo}
    t0 = time.time()
    motor, lector = herramientas()
    c = datos.con()
    cotas = cotas_informes(c, p["codigo"])
    globos, marcas, recuadros, paginas, ocr = [], [], [], [], []
    numeros_texto: set[str] = set()
    with fitz.open(ruta) as pdf:
        for page in pdf:
            palabras = page.get_text("words")
            numeros_texto |= {w[4] for w in palabras if re.fullmatch(r"[1-9]\d{0,3}", w[4])}
            leidos, detectados, fuente = lee_globos(ruta, page, motor, lector)
            globos += leidos
            pagina = {"pagina": page.number + 1, "detectados": detectados, "leidos": len(leidos),
                      "fuente": fuente, "palabras": len(palabras)}
            if detectados < MIN_GLOBOS and len(palabras) < POCO_TEXTO:
                tokens = lectores.ocr_teselas(page, motor)  # lo mismo que lectores.marcas_de_pagina
                marcas_pag = lectores.marcas_de_tokens(tokens, page.number + 1)
                if detalle:
                    ocr.append({"pagina": page.number + 1, "tokens": tokens})
                marcas += marcas_pag
                pagina["marcas"] = len(marcas_pag)
                if len(marcas_pag) < MIN_MARCAS:
                    recuadros_pag = lectores.recuadros_de_pagina(page, motor)
                    recuadros += recuadros_pag
                    pagina["recuadros"] = len(recuadros_pag)
            paginas.append(pagina)
    marcas = lectores.recorta_cuadros(marcas)
    detectados = sum(x["detectados"] for x in paginas)
    cob_texto = cobertura(numeros_texto, cotas)
    cob_recuadros = cobertura({base_cota(x["t"]) for x in recuadros}, cotas)
    tag = decide_tag(detectados, len(globos), len(marcas), len(recuadros), cob_recuadros, cob_texto)
    lecturas = []
    if tag == "globos":
        lecturas = globos
    elif tag == "numerado":
        lecturas = marcas if len(marcas) >= MIN_MARCAS else recuadros if cob_recuadros >= MIN_COBERTURA_RECUADROS else []
    resultado = {"firma": firma(ruta), "doc": doc, "codigo": p["codigo"], "nombre": p["nombre"], "tag": tag,
                 "detectados": detectados, "leidos": len(globos), "marcas": len(marcas), "recuadros": len(recuadros),
                 "cotas_informes": len(cotas), "cobertura_texto": round(cob_texto, 3),
                 "cobertura_recuadros": round(cob_recuadros, 3),
                 "cobertura_lecturas": round(cobertura({base_cota(x["t"]) for x in lecturas}, cotas), 3),
                 "paginas": paginas, "lecturas": lecturas, "segundos": round(time.time() - t0)}
    if detalle:
        resultado["detalle"] = {"marcas": marcas, "recuadros": recuadros, "ocr": ocr}
    return resultado


def analiza(doc: int) -> dict:
    resultado = lee_plano(doc)
    if not resultado.get("error"):
        datos.LECTURAS.mkdir(parents=True, exist_ok=True)
        (datos.LECTURAS / f"{doc}.json").write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return resultado


def resumen(r: dict) -> str:
    if r.get("error"):
        return f"{r['doc']}: {r['error']}"
    return (f"{r['doc']} {r['codigo']} {r['nombre'][:45]} -> {r['tag']} | globos {r['leidos']}/{r['detectados']} | marcas {r['marcas']}"
            f" | recuadros {r['recuadros']} | cobertura texto {r['cobertura_texto']}, recuadros {r['cobertura_recuadros']},"
            f" lecturas {r['cobertura_lecturas']} de {r['cotas_informes']} | {r['segundos']} s")


# ---------------------------------------------------------------- tabla

INICIO_TABLA, FIN_TABLA = "<!-- tabla-planos:inicio -->", "<!-- tabla-planos:fin -->"
DOCUMENTO = datos.CONOCIMIENTO / "planos-globos.md"


def detalle_tabla(p: dict) -> str:
    if p["tag"] == "icp":
        g = datos.globos(p["id"], 1)
        modo = {"calibrada": "globos dibujados, calibración", "aproximada": "sin globos dibujados, calco 1:1",
                "gemela": "sin globos dibujados, calibración de la gemela"}.get(g.get("metodo"), "sin situar")
        return f"{len(g['globos'])} sellos de `{g.get('icp', '')}`; {modo}"
    r = datos.lectura(p["id"])
    if not r:
        return "sin analizar"
    if p["tag"] == "globos":
        return f"{r['leidos']} leídos de {r['detectados']} detectados; {r['cobertura_lecturas']:.0%} de {r['cotas_informes']} cotas de informes"
    if p["tag"] == "numerado":
        if r["lecturas"]:
            via = r["lecturas"][0]["via"]
            cotas = f"{r['cobertura_lecturas']:.0%} de {r['cotas_informes']} cotas de informes" if r["cotas_informes"] else "sin informes con los que contrastar"
            return f"{len(r['lecturas'])} marcas `{via}`; {cotas}"
        return f"número en la capa de texto: {r['cobertura_texto']:.0%} de {r['cotas_informes']} cotas de informes"
    return f"{r['detectados']} aros de color sin números legibles" if r["detectados"] >= MIN_GLOBOS else "nada encontrado"


def tabla() -> str:
    filas = ["| Pieza | Plano | Tag | Pág. | Detalle |", "|---|---|---|---:|---|"]
    orden = {t: i for i, t in enumerate(datos.TAGS)}
    for p in sorted(datos.planos(), key=lambda x: (orden.get(x["tag"], 9), x["codigo"], x["nombre"])):
        nombre = p["nombre"].replace("|", "\\|")
        filas.append(f"| {p['codigo']} | `{nombre}` | {datos.TAGS.get(p['tag'], 'sin analizar')} | {p['paginas']} | {detalle_tabla(p)} |")
    return "\n".join(filas)


def escribe_tabla() -> None:
    texto = DOCUMENTO.read_text(encoding="utf-8")
    bloque = f"{INICIO_TABLA}\n{tabla()}\n{FIN_TABLA}"
    if INICIO_TABLA not in texto or FIN_TABLA not in texto:
        sys.exit(f"Faltan las marcas de la tabla en {DOCUMENTO}")
    inicio, fin = texto.index(INICIO_TABLA), texto.index(FIN_TABLA) + len(FIN_TABLA)
    DOCUMENTO.write_text(texto[:inicio] + bloque + texto[fin:], encoding="utf-8", newline="\n")
    print(f"Tabla escrita en {DOCUMENTO}")


# ---------------------------------------------------------------- principal

def pendientes() -> list[int]:
    salida = []
    for p in datos.planos():
        if p["icp"]:
            continue
        guardada = datos.lectura(p["id"])
        local = datos.estado_onedrive(p["ruta"])[0]
        if not local:
            print(f"{p['id']}: en la nube, no se lee")
        elif not guardada or guardada["firma"] != firma(Path(datos.original(p["ruta"]))):
            salida.append(p["id"])
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc", type=int, action="append", help="Rehacer este plano (se puede repetir)")
    parser.add_argument("--procesos", type=int, default=4)
    parser.add_argument("--tabla", action="store_true", help="Solo escribir la tabla de conocimiento/planos-globos.md")
    args = parser.parse_args()
    if args.tabla:
        return escribe_tabla()
    docs = args.doc or pendientes()
    print(f"{len(docs)} planos por leer", flush=True)
    if not docs:
        return None
    if len(docs) == 1:
        print(resumen(analiza(docs[0])), flush=True)
        return None
    with multiprocessing.get_context("spawn").Pool(min(args.procesos, len(docs))) as pool:
        for r in pool.imap_unordered(analiza, docs):
            print(resumen(r), flush=True)
    return None


if __name__ == "__main__":
    main()
