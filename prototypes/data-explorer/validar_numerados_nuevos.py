"""Valida los lectores de planos numerados (`[]`, `No.` y recuadros) en planos que nunca han visto.

Los lectores se ajustaron en los 4 únicos planos numerados del visor (2820, 3174, 3186 y 3214). Aquí se
pasan, sin tocar nada, por los PDF de Exemples que tienen pinta de plano y que el visor no incluye.
La regla de selección se fija antes de mirar ninguno:

- PDF no duplicado y fuera del conjunto del visor (`datos.PLANOS_SQL`);
- alguna página de tamaño de plano (lado mayor >= 1.150 pt, A3 o más);
- sin capa de texto útil (< 200 caracteres en total): son escaneos, como los planos que leen estos lectores;
- 10 páginas o menos. Fuera quedan 12 cuadernos de planos de molde del matricero (electrodos y herramienta,
  de 11 a 122 páginas, unas 700 en total): a unos 40 s por página no caben, y no son planos de pieza.
  Añadido el 13/11/2026 tras ver el número de páginas, sin haber visto ninguna lectura;
- fuera de `3- Molde`: solo planos de pieza y del método (Eduard, 13/11/2026). Las lecturas de molde que ya
  se habían hecho se quedan en la carpeta, pero no cuentan.

Se usa el mismo código que el visor (`leer_planos.lee_plano`, con su decisión de tag), así que lo que sale es
lo que el visor ofrecería si el plano estuviera dentro. Dos fases, todo en una carpeta fuera de Git:

    python validar_numerados_nuevos.py leer      # lento: unos 115 PDF, 4 procesos
    python validar_numerados_nuevos.py muestra   # hojas de revisión de lo que detectan los lectores

13/11/2026. Resultado y revisión en conocimiento/planos-globos.md.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import random
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import fitz

AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI), str(AQUI / "conocimiento")]
import datos  # noqa: E402
import leer_planos  # noqa: E402
import probar_lectores_numerados as medida  # noqa: E402  (recortes y hojas de revisión)

CARPETA = AQUI / "out" / "validar-numerados-2026-11-13"
SEMILLA = 20261113
N_MUESTRA = 40
LADO_PLANO, MAX_TEXTO, MAX_PAGINAS = 1150, 200, 10


def seleccion() -> dict[int, dict]:
    """PDF fuera del visor que cumplen la regla del docstring, con lo que `datos.plano` necesita."""
    c = sqlite3.connect(f"file:{datos.BD}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    en_visor = {r["id"] for r in c.execute(datos.PLANOS_SQL)}
    global MOLDE
    MOLDE = {r[0] for r in c.execute("SELECT id FROM documento WHERE carpeta_norm='molde'")}
    salida = {}
    for f in c.execute("SELECT id, feature, pieza, codigo, ruta, nombre, estado FROM documento"
                       " WHERE ext='pdf' AND duplicado_de IS NULL ORDER BY codigo, ruta"):
        if f["id"] in en_visor or f["id"] in MOLDE:
            continue
        pags = [json.loads(d or "{}") for (d,) in c.execute(
            "SELECT datos FROM elemento WHERE documento_id=? AND tipo='pagina'", (f["id"],))]
        texto = c.execute("SELECT sum(length(coalesce(texto,''))) FROM elemento WHERE documento_id=? AND tipo='pagina'",
                          (f["id"],)).fetchone()[0] or 0
        if texto < MAX_TEXTO and len(pags) <= MAX_PAGINAS and any(max(p.get("ancho_pt") or 0, p.get("alto_pt") or 0) >= LADO_PLANO for p in pags):
            salida[f["id"]] = {**dict(f), "componente": None}
    return salida


NUEVOS = seleccion()
_plano_visor = datos.plano
# El visor solo conoce sus 56 planos: para estos, `datos.plano` responde desde la biblioteca.
datos.plano = lambda doc: _plano_visor(doc) or NUEVOS.get(doc)


def lee(tarea: tuple[int, str]) -> dict:
    doc, carpeta = tarea
    try:
        r = leer_planos.lee_plano(doc, detalle=True)
    except Exception as e:  # un PDF dañado no para la medida; queda anotado
        r = {"doc": doc, "error": f"{type(e).__name__}: {e}"}
    r["ruta"] = NUEVOS[doc]["ruta"]
    if "detalle" in r:
        r["detalle"].pop("ocr", None)  # el texto del OCR ocupa mucho y aquí no se usa
    destino = Path(carpeta) / "lecturas" / f"{doc}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


def leer(carpeta: Path, procesos: int) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "seleccion.json").write_text(json.dumps(
        {"regla": __doc__.split("Se usa")[0].strip(), "docs": NUEVOS}, ensure_ascii=False, indent=1), encoding="utf-8")
    pendientes = [(d, str(carpeta)) for d in NUEVOS if not (carpeta / "lecturas" / f"{d}.json").exists()]
    print(f"{len(NUEVOS)} PDF seleccionados; {len(pendientes)} por leer", flush=True)
    with multiprocessing.get_context("spawn").Pool(procesos) as pool:
        for r in pool.imap_unordered(lee, pendientes):
            if r.get("error"):
                print(f"{r['doc']}: {r['error']}", flush=True)
                continue
            d = r["detalle"]
            print(f"{r['doc']} {r['codigo']} {r['tag']}: {len(d['marcas'])} marcas, {len(d['recuadros'])} recuadros,"
                  f" {r['detectados']} aros | {r['ruta'].split('/', 2)[-1]}", flush=True)


def muestra(carpeta: Path) -> None:
    """Por plano con detecciones: hasta N_MUESTRA al azar (semilla fija) en una hoja de revisión."""
    resumen = []
    for f in sorted((carpeta / "lecturas").glob("*.json"), key=lambda p: int(p.stem)):
        if int(f.stem) not in NUEVOS:  # lecturas de molde de antes de quitarlos
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("error"):
            resumen.append({"doc": r["doc"], "error": r["error"], "ruta": r["ruta"]})
            continue
        detecciones = r["detalle"]["marcas"] + r["detalle"]["recuadros"]
        fila = {"doc": r["doc"], "codigo": r["codigo"], "ruta": r["ruta"], "tag": r["tag"],
                "marcas": Counter(x["via"] for x in r["detalle"]["marcas"]), "recuadros": len(r["detalle"]["recuadros"]),
                "ofrecidas": len(r["lecturas"]), "cobertura_recuadros": r["cobertura_recuadros"]}
        resumen.append(fila)
        if not detecciones:
            continue
        rnd = random.Random(f"{SEMILLA}-{r['doc']}")
        elegidas = sorted(rnd.sample(range(len(detecciones)), min(N_MUESTRA, len(detecciones))))
        fila["muestra"] = elegidas
        ruta = Path(datos.original(r["ruta"]))
        recortes = []
        with fitz.open(ruta) as pdf:
            grises = {}
            for k in elegidas:
                x = detecciones[k]
                if x["p"] not in grises:
                    grises[x["p"]] = medida.pagina_gris(pdf, x["p"])
                recortes.append((f"{k} p{x['p']} lee {x['t']} ({x['via']})", medida.recorte(grises[x["p"]], x)))
        for n in range(0, len(recortes), 20):
            medida.guarda_png(carpeta / "hojas" / f"{r['doc']}-{n // 20}.png", medida.hoja(recortes[n:n + 20]))
    (carpeta / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in resumen:
        if "error" in x:
            print(f"{x['doc']}: ERROR {x['error']}")
        elif x["marcas"] or x["recuadros"]:
            print(f"{x['doc']} {x['codigo']} tag={x['tag']} marcas={dict(x['marcas'])} recuadros={x['recuadros']}"
                  f" ofrecidas={x['ofrecidas']} | {x['ruta'].split('/', 2)[-1]}")
    print(f"{sum(1 for x in resumen if 'error' not in x and not x['marcas'] and not x['recuadros'])} PDF sin ninguna detección;"
          f" tags: {dict(Counter(x.get('tag') for x in resumen))}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fase", choices=["leer", "muestra"])
    parser.add_argument("--carpeta", type=Path, default=CARPETA)
    parser.add_argument("--procesos", type=int, default=4)
    args = parser.parse_args()
    leer(args.carpeta, args.procesos) if args.fase == "leer" else muestra(args.carpeta)


if __name__ == "__main__":
    main()
