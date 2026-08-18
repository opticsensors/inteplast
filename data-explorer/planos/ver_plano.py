"""
ver_plano.py - El plano 2D del cliente. OJO: funciona a medias, y no por el codigo.

El PDF del plano NO tiene texto: es UNA IMAGEN escaneada (JPEG 3276x2317, ~198 DPI) y
encima borrosa. Todo lo que se saca de aqui es una reconstruccion por OCR.

  SE LEE     el texto normal: 1.504 palabras, confianza media 74. Las notas salen bien
             (`BOSCH`, `PRESSURE TEST WATER`, conf 96). En las cotas el simbolo de
             diametro sale como otro caracter (`%40,3` -> `940.3`), por eso la busqueda
             compara VARIANTES normalizadas y teclear `40,3` encuentra el `940.3`.
  NO SE LEE  los numeros de dentro de los GLOBOS, que son los N-numbers. Miden ~9 px.
             Tesseract da basura (`1733`, `39`, `85`). RapidOCR es PEOR: parece que
             funciona y acierta el 37% (auditadas 16 lecturas al azar: 6 buenas; lee
             `155` donde pone `156` CON 0,99 DE CONFIANZA). Se quito: dar N-numbers
             inventados con pinta de buenos es peor que no dar nada.
             *** NO VOLVER A INTENTARLO CON ESTE PDF. ***
  NO SE LEE  los marcos GD&T: `%0,15 A-B` sale como `[1]`, `G97]`.

Lo que hay que hacer: que INTEPLAST nos de otro PDF del plano que NO sea una imagen.
-> docs/preguntas-abiertas.md (A4)

Uso
---
    python data-explorer/planos/ver_plano.py                # genera la pagina y la abre
    python data-explorer/planos/ver_plano.py --buscar "40,3"
    python data-explorer/planos/ver_plano.py --reocr        # ignora la cache del OCR

Genera
------
    out/plano-3212.html            <- la pagina
    out/plano/img/3212-plano.jpg   la imagen del plano
    out/plano/ocr-3212.json        cache del OCR (palabras + cajas + confianza)
    out/plano/globos-3212.json     cache de los globos localizados
    out/plano/texto-3212.txt       el texto extraido, en orden de lectura
    out/plano/img/marcado-*.png    solo con --buscar: el plano con las marcas
"""

from __future__ import annotations

import argparse
import difflib
import html
import io
import json
import os
import re
import shutil
import sys
import webbrowser
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image

# --------------------------------------------------------------------------------------
# Rutas absolutas a los datos (no estan en este repo)
# --------------------------------------------------------------------------------------

RAIZ = Path(
    r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos"
    r"\11. inteplast\Exemples"
)
CARPETA_PLANO = "1-2D y 3D Pieza"
PROYECTO = "3212 Pump Housing"      # el unico que se trabaja -> CLAUDE.md
SALIDA = Path(__file__).resolve().parent.parent / "out"   # data-explorer/out, compartida

# Tesseract esta instalado pero NO en el PATH (por eso pytesseract da TesseractNotFoundError
# si no se le dice donde esta). Se busca en las dos ubicaciones conocidas de este equipo.
TESSERACT = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]

# --psm 11 = "sparse text": texto suelto sin asumir parrafos. Es el modo correcto para un
# plano, donde las cotas estan desperdigadas entre lineas de dibujo.
CONFIG_OCR = "--psm 11"
ESCALA = 2.0        # ampliar antes del OCR: a 1x salen 1311 palabras, a 2x salen 1504
CONF_MIN = 30       # por debajo de 30 es casi todo ruido de las lineas del dibujo

# El OCR lee el simbolo de diametro como uno de estos. Ver la cabecera.
AMBIGUOS = "9@$0oOQ©¢%&"


# --------------------------------------------------------------------------------------
# Entorno: donde esta Tesseract y que ficheros son seguros de abrir
# --------------------------------------------------------------------------------------


def buscar_tesseract() -> str:
    """Devuelve la ruta del ejecutable o aborta con un mensaje util."""
    for candidato in [shutil.which("tesseract"), *TESSERACT]:
        if candidato and Path(candidato).exists():
            return candidato
    sys.exit(
        "No se encuentra tesseract.exe. Se ha buscado en el PATH y en:\n  "
        + "\n  ".join(TESSERACT)
        + "\nInstalalo o corrige la constante TESSERACT en la cabecera de este script."
    )


def en_la_nube(ruta: Path) -> bool:
    """OneDrive Files On-Demand: leer un placeholder dispara la descarga completa.

    FILE_ATTRIBUTE_RECALL_ON_OPEN_ACCESS = 0x400000. -> CLAUDE.md
    """
    try:
        return bool(os.stat(ruta).st_file_attributes & 0x400000)
    except (AttributeError, OSError):
        return False


# --------------------------------------------------------------------------------------
# Descubrimiento
# --------------------------------------------------------------------------------------


def descubrir_planos(raiz: Path) -> list[dict]:
    """Los planos 2D de los cuatro proyectos, con su estado de hidratacion.

    Solo el del 3212 esta LOCAL; los otros tres son placeholders de OneDrive y este
    script NO los toca (se listan para que se vea que existen).
    """
    planos = []
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        directorio = carpeta / CARPETA_PLANO
        if not directorio.is_dir():
            continue
        for pdf in sorted(directorio.glob("*.pdf")):
            planos.append(
                {
                    "ruta": pdf,
                    "proyecto": carpeta.name,
                    "codigo": carpeta.name.split()[0],
                    "nube": en_la_nube(pdf),
                    "bytes": pdf.stat().st_size,
                }
            )
    return planos


# --------------------------------------------------------------------------------------
# Imagen, OCR y globos
# --------------------------------------------------------------------------------------


def extraer_imagen(pdf: Path) -> tuple[bytes, str, int, int]:
    """La imagen embebida del PDF, tal cual, sin re-renderizar ni recomprimir.

    El plano es un escaneo: la pagina NO tiene texto ni vectores, solo un JPEG. Sacarlo
    con extract_image conserva el bitmap original; rasterizar la pagina lo reinterpolaria
    sin anadir ni un pixel de informacion.
    """
    doc = fitz.open(pdf)
    pagina_1 = doc[0]
    texto = pagina_1.get_text().strip()
    if texto:
        print(f"  [ojo] esta pagina SI tiene capa de texto ({len(texto)} caracteres): "
              f"el OCR quiza sobra")
    imagenes = pagina_1.get_images(full=True)
    if not imagenes:
        sys.exit(f"El PDF no lleva ninguna imagen embebida: {pdf}")
    if len(imagenes) > 1:
        print(f"  [aviso] {len(imagenes)} imagenes embebidas, se usa la mayor")
    mejor = max(imagenes, key=lambda i: i[2] * i[3])
    datos = doc.extract_image(mejor[0])
    doc.close()
    return datos["image"], datos["ext"], datos["width"], datos["height"]


def ocr_palabras(jpeg: bytes, escala: float, conf_min: int) -> list[dict]:
    """Cada palabra con su caja en % de la imagen (no en px: asi el zoom no las descoloca).

    Se amplia antes de pasar el OCR porque los caracteres del plano miden ~11 px de alto
    en el original y Tesseract acierta mas alrededor de los 20-30 px.
    """
    gris = np.array(Image.open(io.BytesIO(jpeg)).convert("L"))
    alto, ancho = gris.shape
    grande = (gris if escala == 1 else
              cv2.resize(gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC))
    print(f"  OCR sobre {grande.shape[1]}x{grande.shape[0]} px (escala {escala}x)...")

    crudo = pytesseract.image_to_data(
        grande, config=CONFIG_OCR, output_type=pytesseract.Output.DICT
    )
    palabras = []
    for i, texto in enumerate(crudo["text"]):
        texto = texto.strip()
        conf = int(crudo["conf"][i])
        if not texto or conf < conf_min:
            continue
        palabras.append(
            {
                "t": texto,
                "x": round(crudo["left"][i] / escala / ancho * 100, 3),
                "y": round(crudo["top"][i] / escala / alto * 100, 3),
                "w": round(crudo["width"][i] / escala / ancho * 100, 3),
                "h": round(crudo["height"][i] / escala / alto * 100, 3),
                "c": conf,
            }
        )
    return palabras


def detectar_globos(jpeg: bytes) -> list[dict]:
    """Localiza los globos de N-number por COLOR. NO los lee: ver la cabecera del script.

    El plano numera las caracteristicas en globos con una flecha a la zona de la pieza y
    SIN el prefijo 'N'. Hay dos familias, verde (la mayoria) y azul (`161.x`). Los globos
    de una misma cota se tocan, asi que un racimo suele salir como UN componente conexo.
    """
    color = cv2.cvtColor(np.array(Image.open(io.BytesIO(jpeg)).convert("RGB")), cv2.COLOR_RGB2BGR)
    alto, ancho = color.shape[:2]
    azul_c, verde_c, rojo_c = cv2.split(color.astype(np.int16))

    # El umbral de 14 es critico: con 25 el anillo se parte en trozos sueltos y se pierden
    # los globos de trazo fino (salian 33 en vez de 173). Comprobado a ojo.
    familias = {
        "verde": ((verde_c - rojo_c) > 14) & ((verde_c - azul_c) > 14),
        "azul": ((azul_c - rojo_c) > 40) & ((azul_c - verde_c) > 25),
    }
    nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    globos = []
    for familia, mascara in familias.items():
        unidos = cv2.morphologyEx(mascara.astype(np.uint8) * 255, cv2.MORPH_CLOSE, nucleo)
        total, _, stats, _ = cv2.connectedComponentsWithStats(unidos, 8)
        for i in range(1, total):
            x, y, w, h, area = stats[i]
            # el maximo es generoso a proposito: muchos globos arrastran su flecha, y esa
            # flecha es justo lo que dice a que zona de la pieza se refiere la cota
            if area < 150 or w < 15 or h < 15 or w > 900 or h > 900:
                continue
            globos.append(
                {
                    "x": round(x / ancho * 100, 3), "y": round(y / alto * 100, 3),
                    "w": round(w / ancho * 100, 3), "h": round(h / alto * 100, 3),
                    "f": familia,
                }
            )
    verdes = sum(1 for gl in globos if gl["f"] == "verde")
    print(f"  {len(globos)} globos de N-number LOCALIZADOS ({verdes} verdes, "
          f"{len(globos) - verdes} azules) - localizados, no leidos")
    return globos


def con_cache(cache: Path, firma: dict, calcular, etiqueta: str, rehacer: bool):
    """Guarda el resultado en JSON y lo reutiliza mientras la firma no cambie."""
    if cache.exists() and not rehacer:
        try:
            guardado = json.loads(cache.read_text(encoding="utf-8"))
            if guardado.get("firma") == firma:
                print(f"  {etiqueta} en cache: {len(guardado['datos'])} ({cache.name})")
                return guardado["datos"]
        except (json.JSONDecodeError, KeyError):
            print(f"  cache de {etiqueta} ilegible, se rehace")
    datos = calcular()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"firma": firma, "datos": datos}, ensure_ascii=False),
                     encoding="utf-8")
    return datos


# --------------------------------------------------------------------------------------
# Normalizacion y busqueda de TEXTO
#
# No se compara texto crudo: se comparan CONJUNTOS DE VARIANTES. La misma funcion se
# aplica a lo que hay en el plano y a lo que se teclea, asi que da igual que el OCR haya
# leido `940.3` donde pone `%40,3`.
# --------------------------------------------------------------------------------------


def canon(texto: str) -> str:
    """Minusculas, sin espacios, decimales con punto y el diametro siempre como 'd'."""
    t = texto.lower().strip()
    t = t.replace(",", ".").replace(" ", "")
    return t.replace("\u00f8", "d").replace("\u2300", "d").replace("\u00d8", "d")


def variantes(texto: str) -> set[str]:
    """Las formas en que ESTA palabra podria haberse escrito o leido.

    `940.3` -> {'940.3', 'd40.3', '40.3'}   (por si la '9' es en realidad un diametro)
    `%40,3` -> {'d40.3', '40.3'}
    Asi `40,3` casa con las tres.
    """
    base = canon(texto)
    formas = {base}
    if not base:
        return formas
    # un caracter ambiguo al principio, seguido de digito: puede ser el simbolo de diametro
    if len(base) > 1 and base[0] in AMBIGUOS and base[1].isdigit():
        formas.add("d" + base[1:])
        formas.add(base[1:])
    if base[0] == "d" and len(base) > 1:
        formas.add(base[1:])
    sin_unidad = re.sub(r"(mm|deg|°)$", "", base)     # `0.2mm` -> `0.2`
    if sin_unidad != base and sin_unidad:
        formas.add(sin_unidad)
    return {f for f in formas if f}


def casa(texto: str, termino: str) -> str | None:
    """'exacto', 'parcial' o None. El minimo de 3 caracteres en AMBOS lados es
    importante: sin el, buscar 'TEST' marcaria cada 'T' y cada 'E' sueltas que el OCR
    saca de las lineas del dibujo."""
    formas, objetivos = variantes(texto), variantes(termino)
    if formas & objetivos:
        return "exacto"
    if any(len(f) >= 3 and len(o) >= 3 and (o in f or f in o)
           for f in formas for o in objetivos):
        return "parcial"
    return None


def buscar_secuencia(palabras: list[dict], terminos: list[str]) -> list[dict]:
    """Varias palabras seguidas: 'PRESSURE TEST'.

    El OCR devuelve una caja POR PALABRA, asi que una consulta de varias no puede
    compararse contra una sola: hay que encadenarlas por posicion. Se acepta la cadena si
    cada termino aparece a la derecha del anterior, en su misma banda horizontal y sin un
    hueco grande. El resultado es una caja que abarca toda la frase.
    """
    resultados = []
    for i, primera in enumerate(palabras):
        if casa(primera["t"], terminos[0]) is None:
            continue
        cadena, ultima = [primera], primera
        for termino in terminos[1:]:
            siguiente = None
            for candidata in palabras:
                hueco = candidata["x"] - (ultima["x"] + ultima["w"])
                if not (-0.3 <= hueco <= 1.6):
                    continue
                if abs(candidata["y"] - ultima["y"]) > ultima["h"] * 0.7:
                    continue
                if casa(candidata["t"], termino) is None:
                    continue
                if siguiente is None or candidata["x"] < siguiente["x"]:
                    siguiente = candidata
            if siguiente is None:
                break
            cadena.append(siguiente)
            ultima = siguiente
        if len(cadena) < len(terminos):
            continue
        x = min(p["x"] for p in cadena)
        y = min(p["y"] for p in cadena)
        resultados.append(
            {
                "i": i,
                "modo": "exacto" if all(casa(p["t"], t) == "exacto"
                                        for p, t in zip(cadena, terminos)) else "parcial",
                "punt": 3.0,
                "t": " ".join(p["t"] for p in cadena),
                "caja": {
                    "x": x, "y": y,
                    "w": max(p["x"] + p["w"] for p in cadena) - x,
                    "h": max(p["y"] + p["h"] for p in cadena) - y,
                },
            }
        )
    return resultados


def buscar(palabras: list[dict], consulta: str, difuso: bool = True) -> list[dict]:
    """Resultados en tres niveles, etiquetados para no vender aproximado como exacto.

    exacto     alguna variante de la palabra es identica a alguna de la consulta
    parcial    una esta contenida en la otra (minimo 3 caracteres por lado)
    aproximado difflib por encima de 0.78 (solo si no hubo nada mejor)
    """
    consulta = consulta.strip()
    if not consulta:
        return []
    terminos = consulta.split()
    if len(terminos) > 1:
        return buscar_secuencia(palabras, terminos)

    objetivos = variantes(consulta)
    exactos, parciales, aproximados = [], [], []
    for i, palabra in enumerate(palabras):
        modo = casa(palabra["t"], consulta)
        if modo == "exacto":
            exactos.append({"i": i, "modo": modo, "punt": 3.0})
            continue
        if modo == "parcial":
            parciales.append({"i": i, "modo": modo, "punt": 2.0})
            continue
        if difuso:
            razon = max(
                (difflib.SequenceMatcher(None, f, o).ratio()
                 for f in variantes(palabra["t"]) for o in objetivos),
                default=0.0,
            )
            if razon >= 0.78:
                aproximados.append({"i": i, "modo": "aproximado", "punt": razon})

    resultados = exactos or parciales or aproximados
    return sorted(resultados, key=lambda r: (-r["punt"], palabras[r["i"]]["y"]))


# --------------------------------------------------------------------------------------
# Salidas de fichero
# --------------------------------------------------------------------------------------


def volcar_texto(palabras: list[dict], destino: Path) -> None:
    """El texto en orden de lectura: por bandas horizontales y de izquierda a derecha."""
    ordenadas = sorted(palabras, key=lambda p: (round(p["y"] * 2), p["x"]))
    cabecera = [
        "# Texto extraido por OCR del plano 2D. NO es la fuente de verdad: el plano es un",
        "# escaneo y esto es una reconstruccion. El simbolo de diametro se lee como 9/@/$.",
        "# Los N-numbers NO estan aqui: van dentro de globos que ningun OCR sabe leer.",
        "# columnas: confianza(0-100)  x%  y%  texto",
        "",
    ]
    lineas = [f'{p["c"]:3d}  {p["x"]:6.2f} {p["y"]:6.2f}   {p["t"]}' for p in ordenadas]
    destino.write_text("\n".join(cabecera + lineas), encoding="utf-8")
    print(f"  texto extraido -> {destino.name} ({len(lineas)} palabras)")


def marcar_png(jpeg: bytes, palabras: list[dict], resultados: list[dict],
               destino: Path) -> None:
    """El plano con las cajas pintadas, para pegar en un informe."""
    img = cv2.cvtColor(np.array(Image.open(io.BytesIO(jpeg)).convert("RGB")), cv2.COLOR_RGB2BGR)
    alto, ancho = img.shape[:2]
    for orden, resultado in enumerate(resultados):
        p = resultado.get("caja") or palabras[resultado["i"]]
        x, y = int(p["x"] / 100 * ancho), int(p["y"] / 100 * alto)
        w, h = int(p["w"] / 100 * ancho), int(p["h"] / 100 * alto)
        margen = 6
        color = (60, 60, 220) if orden == 0 else (40, 150, 240)   # BGR: rojo el mejor
        cv2.rectangle(img, (x - margen, y - margen), (x + w + margen, y + h + margen),
                      color, 4 if orden == 0 else 2)
        cv2.putText(img, str(orden + 1), (x - margen, y - margen - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), img)
    print(f"  marcado -> {destino}")


# --------------------------------------------------------------------------------------
# La pagina
# --------------------------------------------------------------------------------------

ESTILO = """
:root { --linea: #e3e6ea; --tinta: #1a1a1a; --suave: #667; --azul: #3d6fb4; --rojo: #d1495b;
        --naranja: #e08a2e; --verde: #2a9d5c; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 0 auto; max-width: 1400px;
       padding: 28px 24px 60px; color: var(--tinta); background: #fff; line-height: 1.55; }
h1 { font-size: 27px; margin: 0 0 6px; letter-spacing: -0.02em; }
h2 { font-size: 20px; margin: 38px 0 12px; }
h3 { font-size: 15px; margin: 22px 0 6px; }
p { margin: 10px 0; }
code { background: #f2f4f7; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
.sub { color: var(--suave); font-size: 14px; margin-bottom: 18px; }
.ruta { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: var(--suave); }
.volver { display: inline-block; margin-bottom: 14px; font-size: 14px; color: var(--azul);
          text-decoration: none; }
.volver:hover { text-decoration: underline; }

/* ---------- el aviso principal ---------- */
.parada { border: 2px solid var(--rojo); border-radius: 12px; padding: 6px 24px 14px;
          margin: 18px 0 24px; background: #fdf5f6; color: #8d2233; }
.parada p { font-size: 15.5px; }
.parada b { color: var(--rojo); }

details.info { border: 1px solid var(--linea); border-radius: 10px; margin: 22px 0;
               background: #fafbfc; }
details.info > summary { cursor: pointer; padding: 10px 16px 10px 34px; font-size: 14px;
               font-weight: 600; color: var(--azul); user-select: none; }
details.info > summary::marker { color: var(--suave); font-size: 12px; }
details.info > summary:hover { background: #f2f5f9; border-radius: 10px; }
details.info .info-cuerpo { padding: 0 20px 14px; border-top: 1px solid var(--linea);
               background: #fff; border-radius: 0 0 10px 10px; }
details.info .info-cuerpo p { font-size: 14px; margin: 10px 0; }

table.datos { border-collapse: collapse; font-size: 14px; margin: 14px 0; width: 100%; }
table.datos th, table.datos td { border: 1px solid var(--linea); padding: 7px 12px;
                                 text-align: left; background: #fff; }
table.datos th { background: #f2f4f7; font-weight: 600; }
table.datos td.num { text-align: right; font-family: ui-monospace, Consolas, monospace; }
table.datos td.mal { color: var(--rojo); font-weight: 700; }
.nube { color: var(--suave); }

/* ---------- buscador de texto ---------- */
.barra { position: sticky; top: 0; z-index: 20; background: #fff; padding: 12px 0;
         border-bottom: 1px solid var(--linea); display: flex; gap: 10px; align-items: center;
         flex-wrap: wrap; }
.barra input[type=search] { flex: 1 1 260px; font-size: 15px; padding: 9px 13px;
         border: 1px solid var(--linea); border-radius: 8px; font-family: inherit; }
.barra input[type=search]:focus { outline: none; border-color: var(--azul);
         box-shadow: 0 0 0 3px rgba(61,111,180,.13); }
.barra button { font-size: 14px; padding: 8px 13px; border: 1px solid var(--linea);
         background: #fff; border-radius: 8px; cursor: pointer; font-family: inherit; }
.barra button:hover { border-color: var(--azul); color: var(--azul); }
.barra .cuenta { font-size: 13.5px; color: var(--suave); font-family: ui-monospace, monospace;
         min-width: 120px; }
.barra .cuenta b { color: var(--tinta); }
.barra label { font-size: 13px; color: var(--suave); display: flex; align-items: center;
         gap: 6px; white-space: nowrap; }
.pistas { font-size: 13px; color: var(--suave); margin: 8px 0 0; }
.pistas button { font-size: 12.5px; padding: 3px 9px; margin-right: 5px; border-radius: 20px;
         border: 1px solid var(--linea); background: #fafbfc; cursor: pointer;
         font-family: ui-monospace, Consolas, monospace; }
.pistas button:hover { border-color: var(--azul); color: var(--azul); }
.alerta { border-left: 3px solid var(--rojo); background: #fdf5f6; padding: 12px 16px;
          margin: 14px 0; font-size: 14px; border-radius: 0 6px 6px 0; }

/* ---------- visor ---------- */
.marco { display: grid; grid-template-columns: 1fr 290px; gap: 16px; margin-top: 16px; }
@media (max-width: 1000px) { .marco { grid-template-columns: 1fr; } }
#lienzo { position: relative; overflow: hidden; height: 74vh; min-height: 440px;
          border: 1px solid var(--linea); border-radius: 10px; background: #f2f4f7;
          cursor: grab; touch-action: none; }
#lienzo.arrastrando { cursor: grabbing; }
#mundo { position: absolute; top: 0; left: 0; width: 100%; transform-origin: 0 0; }
#mundo img { display: block; width: 100%; user-select: none; -webkit-user-drag: none; }
.caja { position: absolute; border: 2px solid var(--naranja);
        background: rgba(224,138,46,.16); border-radius: 2px; pointer-events: none; }
.caja.activa { border-color: var(--rojo); background: rgba(209,73,91,.22);
        box-shadow: 0 0 0 3px rgba(209,73,91,.25); }
.caja.todas { border-width: 1px; border-color: rgba(61,111,180,.5); background: none; }
.caja.globo { border-color: var(--verde); background: rgba(42,157,92,.13); }
.caja.globo.azul { border-color: var(--azul); background: rgba(61,111,180,.13); }
.etiqueta { position: absolute; transform: translateY(-115%); background: var(--rojo);
        color: #fff; font: 600 11px/1.4 ui-monospace, Consolas, monospace; padding: 1px 5px;
        border-radius: 3px; white-space: nowrap; pointer-events: none; }
.mandos { position: absolute; right: 10px; bottom: 10px; z-index: 5; display: flex; gap: 6px; }
.mandos button { width: 34px; height: 34px; font-size: 16px; border: 1px solid var(--linea);
        background: rgba(255,255,255,.94); border-radius: 8px; cursor: pointer; }
.mandos button:hover { border-color: var(--azul); color: var(--azul); }
.mandos button.ancho { width: auto; padding: 0 10px; font-size: 13px; }

.panel { border: 1px solid var(--linea); border-radius: 10px; overflow: hidden;
         display: flex; flex-direction: column; height: 74vh; min-height: 440px; }
.panel h3 { margin: 0; padding: 11px 14px; font-size: 14px; background: #fafbfc;
            border-bottom: 1px solid var(--linea); }
.panel h3 span { font-weight: 400; color: var(--suave); }
.lista { overflow-y: auto; flex: 1; }
.lista div { padding: 6px 14px; font-size: 13px; cursor: pointer; border-bottom: 1px solid #f2f4f7;
             display: flex; gap: 8px; align-items: baseline; }
.lista div:hover { background: #f2f5f9; }
.lista div.sel { background: #fdf5f6; box-shadow: inset 3px 0 0 var(--rojo); }
.lista .txt { font-family: ui-monospace, Consolas, monospace; }
.lista .cf { margin-left: auto; font-size: 11px; color: var(--suave); }
.lista .mod { font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em;
              color: var(--naranja); }
.lista .mod.exacto { color: var(--verde); }
.lista .mod.aproximado { color: var(--suave); }
.vacio { padding: 20px 14px; font-size: 13.5px; color: var(--suave); }
"""

GUION = r"""
const AMBIGUOS = "9@$0oOQ\u00a9\u00a2%&";

function canon(s) {
  return s.toLowerCase().trim().replace(/,/g, ".").replace(/ /g, "")
          .replace(/[\u00f8\u2300\u00d8]/g, "d");
}
function variantes(s) {
  const base = canon(s), f = new Set([base]);
  if (!base) return f;
  if (base.length > 1 && AMBIGUOS.includes(base[0]) && /\d/.test(base[1])) {
    f.add("d" + base.slice(1)); f.add(base.slice(1));
  }
  if (base[0] === "d" && base.length > 1) f.add(base.slice(1));
  const sinUnidad = base.replace(/(mm|deg|\u00b0)$/, "");
  if (sinUnidad && sinUnidad !== base) f.add(sinUnidad);
  f.delete("");
  return f;
}
function ratio(a, b) {                       // Dice sobre bigramas: barato y suficiente
  if (a === b) return 1;
  if (a.length < 2 || b.length < 2) return 0;
  const par = s => { const m = new Map();
    for (let i = 0; i < s.length - 1; i++) { const g = s.slice(i, i + 2);
      m.set(g, (m.get(g) || 0) + 1); } return m; };
  const A = par(a), B = par(b); let comun = 0;
  for (const [g, n] of A) comun += Math.min(n, B.get(g) || 0);
  return (2 * comun) / (a.length - 1 + b.length - 1);
}

// 'exacto' | 'parcial' | null. El minimo de 3 caracteres por lado evita que buscar TEST
// marque cada 'T' y cada 'E' que el OCR saca de las lineas del dibujo.
function casa(texto, termino) {
  const formas = [...variantes(texto)], objetivos = [...variantes(termino)];
  if (formas.some(f => objetivos.includes(f))) return "exacto";
  if (formas.some(f => f.length >= 3 &&
        objetivos.some(o => o.length >= 3 && (f.includes(o) || o.includes(f))))) return "parcial";
  return null;
}

// Varias palabras: el OCR da una caja POR palabra, asi que hay que encadenarlas por
// posicion (misma banda, a la derecha y sin hueco grande) y devolver la caja de la frase.
function buscarSecuencia(terminos) {
  const res = [];
  PALABRAS.forEach((primera, i) => {
    if (!casa(primera.t, terminos[0])) return;
    const cadena = [primera]; let ultima = primera;
    for (let k = 1; k < terminos.length; k++) {
      let sig = null;
      for (const c of PALABRAS) {
        const hueco = c.x - (ultima.x + ultima.w);
        if (hueco < -0.3 || hueco > 1.6) continue;
        if (Math.abs(c.y - ultima.y) > ultima.h * 0.7) continue;
        if (!casa(c.t, terminos[k])) continue;
        if (!sig || c.x < sig.x) sig = c;
      }
      if (!sig) break;
      cadena.push(sig); ultima = sig;
    }
    if (cadena.length < terminos.length) return;
    const x = Math.min(...cadena.map(p => p.x)), y = Math.min(...cadena.map(p => p.y));
    res.push({i, modo: cadena.every((p, k) => casa(p.t, terminos[k]) === "exacto")
                          ? "exacto" : "parcial", punt: 3,
              t: cadena.map(p => p.t).join(" "),
              caja: {x, y, w: Math.max(...cadena.map(p => p.x + p.w)) - x,
                           h: Math.max(...cadena.map(p => p.y + p.h)) - y}});
  });
  return res;
}

// Un N-number NO se puede buscar aqui: no esta en el texto, esta dentro de un globo que
// ningun OCR lee. En vez de devolver un resultado inventado, se avisa.
function pareceNNumber(texto) {
  return /^n?\s*\d{3}(\s*[.\-]\s*[0-9tT])?$/i.test(texto.trim());
}

function buscar(consulta) {
  consulta = consulta.trim();
  if (!consulta) return [];
  const terminos = consulta.split(/\s+/);
  if (terminos.length > 1) return buscarSecuencia(terminos);

  const objetivos = [...variantes(consulta)];
  const exactos = [], parciales = [], aprox = [];
  PALABRAS.forEach((p, i) => {
    const modo = casa(p.t, consulta);
    if (modo === "exacto") { exactos.push({i, modo, punt: 3}); return; }
    if (modo === "parcial") { parciales.push({i, modo, punt: 2}); return; }
    let mejor = 0;
    for (const f of variantes(p.t)) for (const o of objetivos) mejor = Math.max(mejor, ratio(f, o));
    if (mejor >= 0.78) aprox.push({i, modo: "aproximado", punt: mejor});
  });
  const res = exactos.length ? exactos : (parciales.length ? parciales : aprox);
  return res.sort((a, b) => b.punt - a.punt || PALABRAS[a.i].y - PALABRAS[b.i].y);
}

// ---------- pintar ----------
const lienzo = document.getElementById("lienzo");
const mundo  = document.getElementById("mundo");
const capa   = document.getElementById("capa");
const lista  = document.getElementById("lista");
const cuenta = document.getElementById("cuenta");
const entrada = document.getElementById("q");
const alerta = document.getElementById("alerta-n");
let resultados = [], activo = -1;

function cajaDe(r) { return r.caja || PALABRAS[r.i]; }
function textoDe(r) { return r.t || PALABRAS[r.i].t; }

function pintar() {
  capa.innerHTML = "";
  if (document.getElementById("globos").checked)
    GLOBOS.forEach(g => capa.appendChild(caja(g, "caja globo" + (g.f === "azul" ? " azul" : ""))));
  if (document.getElementById("todas").checked)
    PALABRAS.forEach(p => capa.appendChild(caja(p, "caja todas")));
  resultados.forEach((r, n) => {
    const p = cajaDe(r);
    capa.appendChild(caja(p, "caja" + (n === activo ? " activa" : "")));
    if (n === activo) {
      const e = document.createElement("div");
      e.className = "etiqueta"; e.textContent = textoDe(r);
      e.style.left = p.x + "%"; e.style.top = p.y + "%";
      capa.appendChild(e);
    }
  });
}
function caja(p, clase) {
  const d = document.createElement("div");
  d.className = clase;
  d.style.left = p.x + "%"; d.style.top = p.y + "%";
  d.style.width = p.w + "%"; d.style.height = p.h + "%";
  return d;
}

function pintarLista() {
  lista.innerHTML = "";
  if (!resultados.length) {
    lista.innerHTML = "<div class='vacio'>Sin resultados. Prueba con menos caracteres: el OCR "
      + "parte las cotas y confunde el simbolo de diametro.</div>";
    return;
  }
  resultados.forEach((r, n) => {
    const d = document.createElement("div");
    d.className = n === activo ? "sel" : "";
    d.innerHTML = "<span class='txt'>" + escapar(textoDe(r)) + "</span>"
      + "<span class='mod " + r.modo + "'>" + r.modo + "</span>"
      + "<span class='cf'>" + PALABRAS[r.i].c + "%</span>";
    d.onclick = () => { activo = n; irA(); };
    lista.appendChild(d);
  });
}
function escapar(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

function actualizar() {
  // si teclea un N-number hay que pararle los pies: eso NO se puede buscar aqui
  if (pareceNNumber(entrada.value)) {
    alerta.hidden = false;
    document.getElementById("globos").checked = true;
    resultados = []; activo = -1;
    cuenta.innerHTML = "no buscable";
    pintarLista(); pintar();
    return;
  }
  alerta.hidden = true;
  resultados = buscar(entrada.value);
  activo = resultados.length ? 0 : -1;
  cuenta.innerHTML = resultados.length
    ? "<b>" + (activo + 1) + "</b> / " + resultados.length
    : (entrada.value.trim() ? "0 resultados" : PALABRAS.length + " palabras");
  pintarLista();
  if (activo >= 0) irA(); else pintar();
}
function saltar(paso) {
  if (!resultados.length) return;
  activo = (activo + paso + resultados.length) % resultados.length;
  cuenta.innerHTML = "<b>" + (activo + 1) + "</b> / " + resultados.length;
  pintarLista(); irA();
}

// ---------- zoom y arrastre ----------
let z = 1, tx = 0, ty = 0;
function aplicar() { mundo.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + z + ")"; }
function ajustar() {
  z = Math.min(lienzo.clientWidth / mundo.offsetWidth, lienzo.clientHeight / mundo.offsetHeight);
  tx = (lienzo.clientWidth - mundo.offsetWidth * z) / 2;
  ty = (lienzo.clientHeight - mundo.offsetHeight * z) / 2;
  aplicar();
}
function zoom(factor, mx, my) {
  const nz = Math.min(30, Math.max(0.2, z * factor));
  if (mx === undefined) { mx = lienzo.clientWidth / 2; my = lienzo.clientHeight / 2; }
  tx = mx - (mx - tx) * (nz / z);
  ty = my - (my - ty) * (nz / z);
  z = nz; aplicar();
}
function irA() {
  pintar(); pintarLista();
  if (activo < 0) return;
  const p = cajaDe(resultados[activo]);
  const W = mundo.offsetWidth, H = mundo.offsetHeight;
  z = Math.max(z, 4);
  tx = lienzo.clientWidth / 2 - (p.x + p.w / 2) / 100 * W * z;
  ty = lienzo.clientHeight / 2 - (p.y + p.h / 2) / 100 * H * z;
  aplicar();
}

lienzo.addEventListener("wheel", e => {
  e.preventDefault();
  const r = lienzo.getBoundingClientRect();
  zoom(e.deltaY < 0 ? 1.18 : 1 / 1.18, e.clientX - r.left, e.clientY - r.top);
}, {passive: false});

let arrastrando = false, px = 0, py = 0;
lienzo.addEventListener("pointerdown", e => {
  arrastrando = true; px = e.clientX; py = e.clientY;
  lienzo.classList.add("arrastrando"); lienzo.setPointerCapture(e.pointerId);
});
lienzo.addEventListener("pointermove", e => {
  if (!arrastrando) return;
  tx += e.clientX - px; ty += e.clientY - py; px = e.clientX; py = e.clientY; aplicar();
});
lienzo.addEventListener("pointerup", e => {
  arrastrando = false; lienzo.classList.remove("arrastrando");
  lienzo.releasePointerCapture(e.pointerId);
});

entrada.addEventListener("input", actualizar);
entrada.addEventListener("keydown", e => { if (e.key === "Enter") saltar(e.shiftKey ? -1 : 1); });
document.getElementById("todas").addEventListener("change", pintar);
document.getElementById("globos").addEventListener("change", pintar);
document.getElementById("sig").onclick = () => saltar(1);
document.getElementById("ant").onclick = () => saltar(-1);
document.getElementById("mas").onclick = () => zoom(1.4);
document.getElementById("menos").onclick = () => zoom(1 / 1.4);
document.getElementById("ajustar").onclick = ajustar;
document.querySelectorAll(".pistas button").forEach(b => {
  b.onclick = () => { entrada.value = b.dataset.q || b.textContent; actualizar(); entrada.focus(); };
});
addEventListener("resize", ajustar);
window.addEventListener("load", () => { ajustar(); actualizar(); });
"""

def cuerpo_pagina(plano: dict, palabras: list[dict], globos: list[dict],
                  otros: list[dict], ancho: int, alto: int, imagen_rel: str) -> str:
    filas_otros = "".join(
        f"<tr><td>{html.escape(o['proyecto'])}</td>"
        f"<td class='ruta'>{html.escape(o['ruta'].name)}</td>"
        f"<td class='{'nube' if o['nube'] else ''}'>"
        f"{'en la nube' if o['nube'] else 'local'}</td></tr>"
        for o in otros
    )
    return f"""
<a class='volver' href='index.html'>&larr; volver al inicio</a>
<h1>El plano 2D del {html.escape(plano['codigo'])}</h1>
<div class='sub ruta'>{html.escape(plano['ruta'].name)}</div>

<div class='parada'>
<p><b>Esto no funciona como deberia.</b> El PDF del plano <b>no tiene texto: es una imagen</b>,
y ademas <b>se ve borrosa</b> ({ancho}&times;{alto}&nbsp;px). Lo que se busca aqui es una
reconstruccion por OCR, con sus fallos: <b>los numeros de dentro de los globos no se pueden leer
de ninguna manera</b>.</p>
<p><b>INTEPLAST deberia darnos otro PDF del plano que no sea una imagen</b>, para poder buscar en
el de verdad.</p>
</div>

<div class='barra'>
  <input type='search' id='q' placeholder='una cota (40,3) o una nota (BOSCH)&hellip;'
         autocomplete='off' spellcheck='false'>
  <button id='ant' title='anterior (Shift+Enter)'>&uarr;</button>
  <button id='sig' title='siguiente (Enter)'>&darr;</button>
  <span class='cuenta' id='cuenta'></span>
  <label><input type='checkbox' id='globos'> globos ({len(globos)})</label>
  <label><input type='checkbox' id='todas'> las {len(palabras)} palabras</label>
</div>
<div class='pistas'>Prueba: <button>BOSCH</button><button>40,3</button>
<button>PRESSURE TEST</button><button>0,2mm</button></div>
<div class='alerta' id='alerta-n' hidden><b>Un N-number no se puede buscar.</b> No esta en el
texto: esta dentro de un globo, y esas cifras son ilegibles. Se han encendido los {len(globos)}
globos: haz zoom y buscalo a ojo.</div>

<div class='marco'>
  <div id='lienzo'>
    <div id='mundo'><img src='{imagen_rel}' alt='plano 2D del {html.escape(plano["codigo"])}'>
      <div id='capa'></div></div>
    <div class='mandos'>
      <button id='menos' title='alejar'>&minus;</button>
      <button id='mas' title='acercar'>+</button>
      <button id='ajustar' class='ancho'>ajustar</button>
    </div>
  </div>
  <div class='panel'>
    <h3>Resultados <span>&mdash; clic para ir</span></h3>
    <div class='lista' id='lista'></div>
  </div>
</div>

<details class='info'><summary>M&aacute;s informaci&oacute;n</summary>
<div class='info-cuerpo'>
<p><b>Si se lee</b> el texto normal: {len(palabras)} palabras. Las notas salen bien
(<code>BOSCH</code>, <code>PRESSURE TEST WATER</code>). En las cotas el simbolo
<code>&#216;</code> se lee como <code>9</code> o <code>$</code>, asi que <code>40,3</code>
encuentra el <code>940.3</code> del OCR.</p>
<p><b>No se lee:</b> los <b>numeros de los globos</b> (los N-numbers) &mdash; miden ~9 px;
probado con Tesseract y RapidOCR, este ultimo acierta solo el 37&nbsp;% y falla sin avisar, asi
que se quito. Tampoco los <b>marcos GD&amp;T</b> (<code>&#8918;0,15 A-B</code> sale como
<code>[1]</code>).</p>
<p>Los globos <b>si</b> se localizan ({len(globos)}): sirven para saber donde mirar y leerlos a
ojo con el zoom. Detalle completo en <code>docs/visores.md</code> y en la pregunta A4 de
<code>docs/preguntas-abiertas.md</code>.</p>
<p><b>Los planos de los otros proyectos</b> estan en la nube de OneDrive y no se tocan:</p>
<table class='datos'><tr><th>proyecto</th><th>fichero</th><th>estado</th></tr>{filas_otros}</table>
</div></details>
"""


def escribir_pagina(destino: Path, plano: dict, palabras: list[dict], globos: list[dict],
                    otros: list[dict], ancho: int, alto: int, imagen_rel: str) -> None:
    datos = (
        "const PALABRAS = " + json.dumps(palabras, ensure_ascii=False) + ";\n"
        "const GLOBOS = " + json.dumps(globos, ensure_ascii=False) + ";\n"
    )
    cuerpo = cuerpo_pagina(plano, palabras, globos, otros, ancho, alto, imagen_rel)
    destino.write_text(
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(plano['codigo'])} - el plano 2D</title>"
        f"<style>{ESTILO}</style></head><body>{cuerpo}"
        f"<script>{datos}{GUION}</script></body></html>",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--buscar", help="marca este texto y escribe un PNG con las cajas")
    parser.add_argument("--n", help="(ya no busca el N-number: explica por que no se puede)")
    parser.add_argument("--escala", type=float, default=ESCALA,
                        help=f"ampliacion antes del OCR (por defecto {ESCALA})")
    parser.add_argument("--conf", type=int, default=CONF_MIN,
                        help=f"confianza minima 0-100 (por defecto {CONF_MIN})")
    parser.add_argument("--reocr", action="store_true", help="ignora la cache y rehace el OCR")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de salida")
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()

    pytesseract.pytesseract.tesseract_cmd = buscar_tesseract()
    print(f"tesseract: {pytesseract.pytesseract.tesseract_cmd}")

    if not RAIZ.is_dir():
        sys.exit(f"No se llega a los datos: {RAIZ}")
    planos = descubrir_planos(RAIZ)
    nuestros = [p for p in planos if p["proyecto"] == PROYECTO]
    if not nuestros:
        sys.exit(f"No hay ningun PDF en {RAIZ / PROYECTO / CARPETA_PLANO}")
    plano = nuestros[0]
    otros = [p for p in planos if p is not plano]

    print(f"\nplano: {plano['ruta'].name}  ({plano['bytes']/1e6:.2f} MB)")
    if plano["nube"]:
        sys.exit(
            "Ese fichero es un placeholder de OneDrive: abrirlo disparara la descarga.\n"
            "Hidratalo a mano (abrelo una vez desde el explorador) y vuelve a ejecutar."
        )

    destino = args.salida / "plano"
    (destino / "img").mkdir(parents=True, exist_ok=True)

    jpeg, ext, ancho, alto = extraer_imagen(plano["ruta"])
    print(f"  imagen embebida: {ancho}x{alto} {ext}, {len(jpeg)/1e6:.2f} MB")

    firma = {"bytes": plano["ruta"].stat().st_size, "escala": args.escala, "conf": args.conf}
    palabras = con_cache(destino / "ocr-3212.json", firma,
                         lambda: ocr_palabras(jpeg, args.escala, args.conf),
                         "OCR", args.reocr)
    globos = con_cache(destino / "globos-3212.json", {"bytes": len(jpeg), "v": 3},
                       lambda: detectar_globos(jpeg), "globos", args.reocr)
    volcar_texto(palabras, destino / "texto-3212.txt")

    imagen = destino / "img" / f"{plano['codigo']}-plano.jpg"
    imagen.write_bytes(jpeg)

    if args.n:
        print(
            f"\n[!] --n ya NO busca el N-number, porque no se puede: '{args.n}' no esta en el\n"
            f"    texto del plano, esta dentro de un globo de ~9 px. Se probo con Tesseract\n"
            f"    (basura) y con RapidOCR (37% de acierto, y falla con 0,99 de confianza).\n"
            f"    Abre la pagina, enciende los globos y busca a ojo con el zoom.\n"
            f"    Lo que hay que hacer de verdad: pedir el plano bueno. -> A4"
        )

    if args.buscar:
        resultados = buscar(palabras, args.buscar)
        print(f"\n'{args.buscar}': {len(resultados)} resultados")
        for orden, r in enumerate(resultados[:10], 1):
            caja = r.get("caja") or palabras[r["i"]]
            texto = r.get("t") or palabras[r["i"]]["t"]
            print(f"  {orden:2d}. {texto!r:22s} {r['modo']:11s} conf {palabras[r['i']]['c']:3d}  "
                  f"x={caja['x']:6.2f}% y={caja['y']:6.2f}%")
        if resultados:
            limpio = re.sub(r"[^\w.-]+", "_", args.buscar)
            marcar_png(jpeg, palabras, resultados[:10],
                       destino / "img" / f"marcado-{limpio}.png")

    fichero = args.salida / "plano-3212.html"
    escribir_pagina(fichero, plano, palabras, globos, otros, ancho, alto,
                    f"plano/img/{imagen.name}")
    print(f"\nPagina: {fichero}")
    if not args.no_abrir:
        webbrowser.open(fichero.as_uri())


if __name__ == "__main__":
    main()
