"""Lee una sola vez los planos sin .icp y decide su tag. El visor solo consulta lo que deja aquí.

    python leer_planos.py                # los que falten, con 4 procesos
    python leer_planos.py --doc 2243     # uno concreto (rehace su lectura)
    python leer_planos.py --tabla        # escribe la tabla de conocimiento/planos-globos.md

Tres lectores, según lo que trae el plano:
- Globos de color: el lector oficial de la aplicación (`backend/app/ingestion/`), sin cambios.
- `[]210` y `No. 200`: OCR por teselas del plano muy ampliado, en horizontal y en vertical.
- Números en rectángulos, también girados: se detecta el rectángulo y se lee solo su interior.

Los dos últimos son prototipo, probados solo en el 2820, el 3174, el 3186 y el 3214. Todo son
lecturas automáticas: pueden fallar sin avisar y no sustituyen a un `.icp`.
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

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402

BACKEND = datos.REPO / "backend"
VERSION = 1

# Decisión del tag. Los falsos globos (cotas resaltadas, dibujo en azul) tienen aros, pero no números.
MIN_GLOBOS, MIN_GLOBOS_LEIDOS = 20, .4
MIN_MARCAS = 20  # marcas `[]` o `No.` para considerar numerado el plano
MIN_COBERTURA_TEXTO = .8  # parte de las cotas de los informes presente como número en la capa de texto
MIN_COTAS = 10
MIN_RECUADROS, MIN_COBERTURA_RECUADROS = 15, .5
POCO_TEXTO = 50  # con menos palabras en la página, se considera que no hay capa de texto

TESELA, SOLAPE = 1600, 240
PUNTOS_POR_PT_RECUADRO = 5.54  # unos 400 ppp: en el 3214, recuadros de unos 57 px


# ---------------------------------------------------------------- marcas `[]` y `No.`

MARCA_CUADRO = re.compile(r"\[\]\s*(\d(?:\s?\d){1,3})(?!\d)")
MARCA_NO = re.compile(r"(?i)N[o0]\s*[.,．]\s*(\d{3,4})(\s*[Φφ±\dR(].*)?")


def marcas_en_token(texto: str) -> list[tuple[str, str, int, int]]:
    """Marcas de un texto del OCR: (estilo, número, inicio, fin).

    `[]` se busca en todo el texto, porque el OCR la junta con la cota vecina. `No.` tiene que
    abrir el texto, seguida como mucho de la cota: «ADDED No.15.», «No.100 - No.108» o «VIEW No. 1»
    son notas y tablas, no marcas de una cota.
    """
    texto = texto.strip()
    salida = [("[]", re.sub(r"\s", "", m.group(1)), m.start(), m.end()) for m in MARCA_CUADRO.finditer(texto)]
    m = MARCA_NO.fullmatch(texto)
    if m and "no" not in (m.group(2) or "").lower():
        salida.append(("No.", m.group(1), m.start(), m.end(1)))
    return salida


def sin_repetir(marcas: list[dict]) -> list[dict]:
    """Quita lo que se ha leído dos veces por el solape de teselas o por leer en los dos sentidos.

    Un número cortado por el borde de una tesela («27» de «271») cae junto al completo: gana el largo.
    """
    salida: list[dict] = []
    for m in sorted(marcas, key=lambda x: (-len(x["t"]), -x["s"])):
        cerca = [o for o in salida if o["p"] == m["p"] and abs(o["x"] - m["x"]) < .012 and abs(o["y"] - m["y"]) < .012]
        if not any(o["t"].startswith(m["t"]) for o in cerca):
            salida.append(m)
    return salida


def recorta_cuadros(marcas: list[dict]) -> list[dict]:
    """El OCR pega la marca con lo que la sigue: `[]198` y `0.005` salen como «1980».

    Si casi todas las marcas `[]` del plano tienen tres cifras, la cuarta no forma parte del número.
    """
    cuadros = [m for m in marcas if m["via"] == "[]"]
    if not cuadros or sum(len(m["t"]) == 3 for m in cuadros) < .8 * len(cuadros):
        return marcas
    return sin_repetir([{**m, "t": m["t"][:3]} if m["via"] == "[]" else m for m in marcas])


def ocr_teselas(page, engine) -> list[dict]:
    """Texto del OCR con su posición en la página (0–1). Muy ampliado, en horizontal y en vertical."""
    zoom = min(6., max(3., 4700 / max(1., page.rect.width)))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    alto0, ancho0 = rgb.shape[:2]
    salida = []
    for vertical in (False, True):
        imagen = np.rot90(rgb, -1) if vertical else rgb
        alto, ancho = imagen.shape[:2]
        for y in range(0, max(1, alto - SOLAPE), TESELA - SOLAPE):
            for x in range(0, max(1, ancho - SOLAPE), TESELA - SOLAPE):
                tesela = np.ascontiguousarray(imagen[y:y + TESELA, x:x + TESELA])
                if (tesela < 200).mean() < .002:
                    continue
                resultado, _ = engine(tesela)
                for caja, texto, score in resultado or []:
                    q = np.array(caja, float) + (x, y)
                    if vertical:  # a coordenadas de la página sin girar
                        q = np.stack([q[:, 1], alto0 - 1 - q[:, 0]], axis=1)
                    q = q / (ancho0, alto0)
                    salida.append({"texto": texto, "s": round(float(score), 3), "q": q.round(5).tolist()})
    return salida


def marcas_de_tokens(tokens: list[dict], pagina: int) -> list[dict]:
    """Sitúa cada marca dentro de su texto: el OCR puede juntarla con la cota de al lado."""
    salida = []
    for token in tokens:
        q = np.array(token["q"])
        izquierda, derecha = (q[0] + q[3]) / 2, (q[1] + q[2]) / 2
        n = max(1, len(token["texto"].strip()))
        for estilo, numero, ini, fin in marcas_en_token(token["texto"]):
            a, b = izquierda + (derecha - izquierda) * ini / n, izquierda + (derecha - izquierda) * fin / n
            alto = np.abs(q[3] - q[0]).max()
            x0, x1, y0, y1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
            salida.append({"p": pagina, "t": numero, "s": token["s"], "via": estilo,
                           "x": round(float((x0 + x1) / 2), 5), "y": round(float((y0 + y1) / 2), 5),
                           "w": round(float(x1 - x0 + alto * .3), 5), "h": round(float(y1 - y0 + alto * .3), 5)})
    return sin_repetir(salida)


# ---------------------------------------------------------------- números en rectángulos

ETIQUETA_RECUADRO = re.compile(r"\d{1,3}(?:\.\d{1,2})?|[A-Z]\d{1,2}")
LIMPIA_RECUADRO = re.compile(r"[\s|\[\]()_:;'`,-]")
MIN_SCORE_RECUADRO, MIN_SCORE_OTRO_SENTIDO = .8, .97


def rectangulos(gris: np.ndarray) -> list[tuple]:
    """Cuadriláteros casi perfectos, de tamaño de recuadro, sin contar dos veces sus dos bordes."""
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    contornos, _ = cv2.findContours(binaria, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    salida = []
    for k in contornos:
        area = cv2.contourArea(k)
        if not 700 <= area <= 40000:
            continue
        (cx, cy), (a, b), angulo = cv2.minAreaRect(k)
        if min(a, b) < 25 or max(a, b) > 260 or max(a, b) / max(1, min(a, b)) > 3.2 or area / max(1, a * b) < .86:
            continue
        poligono = cv2.approxPolyDP(k, .03 * cv2.arcLength(k, True), True)
        if len(poligono) == 4 and cv2.isContourConvex(poligono):
            salida.append((area, cx, cy, a, b, angulo))
    unicos: list[tuple] = []
    for r in sorted(salida, reverse=True):
        if not any(np.hypot(r[1] - u[1], r[2] - u[2]) < .4 * min(u[3], u[4]) for u in unicos):
            unicos.append(r)
    return unicos


def esquinas_prolongadas(binaria: np.ndarray, r: tuple) -> int:
    """Cuántas esquinas siguen en línea más allá del rectángulo: una celda de tabla, no un recuadro."""
    _, cx, cy, a, b, angulo = r
    t = np.radians(angulo)
    ex, ey = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
    margen = max(8., .25 * min(a, b))
    prolongadas = 0
    for sa in (-1, 1):
        for sb in (-1, 1):
            esquina = np.array([cx, cy]) + sa * ex * a / 2 + sb * ey * b / 2
            for paso in (sa * ex, sb * ey):  # los dos lados que salen de la esquina
                tinta = 0
                for d in np.linspace(.3, 1, 8) * margen:
                    x, y = (esquina + paso * d).round().astype(int)
                    if 0 <= y < binaria.shape[0] and 0 <= x < binaria.shape[1]:
                        tinta += int(binaria[max(0, y - 2):y + 3, max(0, x - 2):x + 3].any())
                if tinta >= 7:
                    prolongadas += 1
                    break
    return prolongadas


def sentido_admitido(angulo_total: float) -> bool:
    """Un plano se lee de abajo o de la derecha: el texto nunca está boca abajo (6 frente a 9)."""
    phi = (angulo_total + 180) % 360 - 180
    return -95 <= phi < 85  # con margen: un escaneo nunca queda a 90° exactos


def recorte_recuadro(gris: np.ndarray, r: tuple, giro: int) -> np.ndarray | None:
    _, cx, cy, a, b, angulo = r
    matriz = cv2.getRotationMatrix2D((cx, cy), angulo + giro, 1)
    derecha = cv2.warpAffine(gris, matriz, (gris.shape[1], gris.shape[0]), flags=cv2.INTER_CUBIC, borderValue=255)
    w, h = (a, b) if giro % 180 == 0 else (b, a)
    mx, my = max(5, w * .12), max(5, h * .12)
    x0, x1, y0, y1 = int(cx - w / 2 + mx), int(cx + w / 2 - mx), int(cy - h / 2 + my), int(cy + h / 2 - my)
    interior = derecha[max(0, y0):y1, max(0, x0):x1]
    if not interior.size:
        return None
    interior = cv2.resize(interior, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(interior, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)


def lee_recuadro(gris: np.ndarray, r: tuple, engine) -> tuple[str, float] | None:
    """Mejor lectura en sentido admitido; otro sentido solo si no hay ninguna y es casi segura.

    Entre las válidas gana la más larga: leído de lado, un «33» se queda en «3» con mucha confianza.
    """
    lecturas = []
    for giro in (0, 90, 180, 270):
        imagen = recorte_recuadro(gris, r, giro)
        if imagen is None:
            continue
        crudo, _ = engine(cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR), use_det=False, use_cls=False)
        for texto, score, *_ in crudo or []:
            limpio = LIMPIA_RECUADRO.sub("", texto).upper().strip(".")
            if ETIQUETA_RECUADRO.fullmatch(limpio):
                lecturas.append((limpio, float(score), sentido_admitido(r[5] + giro)))
    for admitido, minimo in ((True, MIN_SCORE_RECUADRO), (False, MIN_SCORE_OTRO_SENTIDO)):
        validas = [x for x in lecturas if x[2] == admitido and x[1] >= minimo]
        if validas:
            mejor = max(validas, key=lambda x: (len(x[0]), x[1]))
            return mejor[0], mejor[1]
    return None


def recuadros_de_pagina(page, engine) -> list[dict]:
    zoom = min(PUNTOS_POR_PT_RECUADRO, 9000 / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
    gris = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    # Una línea de cota puede tocar dos esquinas de un recuadro; una celda de tabla sigue por más.
    rects = [r for r in rectangulos(gris) if esquinas_prolongadas(binaria, r) < 3]
    salida = []
    for r in rects:
        leido = lee_recuadro(gris, r, engine)
        if leido:
            _, cx, cy, a, b, _ = r
            salida.append({"p": page.number + 1, "t": leido[0], "s": round(leido[1], 3), "via": "recuadro",
                           "x": round(cx / pix.width, 5), "y": round(cy / pix.height, 5),
                           "w": round(max(a, b) / pix.width, 5), "h": round(max(a, b) / pix.height, 5), "alto": min(a, b)})
    if salida:  # los recuadros de numeración de un plano tienen casi la misma altura; el ancho depende del número
        mediana = float(np.median([x["alto"] for x in salida]))
        salida = [x for x in salida if .7 * mediana <= x["alto"] <= 1.4 * mediana]
    return [{k: v for k, v in x.items() if k != "alto"} for x in salida]


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
        sys.path.insert(0, str(BACKEND))
        from app.ingestion.balloon_reader import own_reader
        from rapidocr_onnxruntime import RapidOCR

        _motor, _lector = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1), own_reader()
        if _lector is None:
            raise RuntimeError("No se ha podido cargar el lector de globos del backend")
    return _motor, _lector


def firma(ruta: Path) -> dict:
    sys.path.insert(0, str(BACKEND))
    from app.ingestion.drawing_version import reader_id

    return {"sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(), "version": VERSION, "lector": reader_id()}


def lee_globos(ruta: Path, page, motor, lector) -> tuple[list[dict], int, str]:
    """Globos de color con el lector de la aplicación: lecturas ofrecidas, detectados y fuente."""
    from app.ingestion.balloon_reader import read_balloons_combined
    from app.ingestion.drawing import balloon_source, best_rotation, rotate

    trabajo, globos, fuente = balloon_source(ruta, page)
    if len(globos) < MIN_GLOBOS:
        return [], len(globos), fuente
    giros = best_rotation(trabajo, globos, lector)
    imagen, movidos = rotate(trabajo, globos, giros) if giros else (trabajo, globos)
    read_balloons_combined(imagen, movidos, motor, lector)
    salida = []
    for globo, leido in zip(globos, movidos, strict=True):
        if leido["candidates"]:
            x0, y0, x1, y1 = globo["box"]
            combinada = leido["candidates"][0]["readings"][0]
            salida.append({"p": page.number + 1, "t": combinada["text"], "s": combinada["score"], "via": "globo",
                           "x": round((x0 + x1) / 2, 5), "y": round((y0 + y1) / 2, 5),
                           "w": round(x1 - x0, 5), "h": round(y1 - y0, 5)})
    return salida, len(globos), fuente


def analiza(doc: int) -> dict:
    p = datos.plano(doc)
    ruta = Path(datos.original(p["ruta"]))
    local, motivo = datos.estado_onedrive(p["ruta"])
    if not local:
        return {"doc": doc, "error": motivo}
    t0 = time.time()
    motor, lector = herramientas()
    c = datos.con()
    cotas = cotas_informes(c, p["codigo"])
    globos, marcas, recuadros, paginas = [], [], [], []
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
                marcas_pag = marcas_de_tokens(ocr_teselas(page, motor), page.number + 1)
                marcas += marcas_pag
                pagina["marcas"] = len(marcas_pag)
                if len(marcas_pag) < MIN_MARCAS:
                    recuadros_pag = recuadros_de_pagina(page, motor)
                    recuadros += recuadros_pag
                    pagina["recuadros"] = len(recuadros_pag)
            paginas.append(pagina)
    marcas = recorta_cuadros(marcas)
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
