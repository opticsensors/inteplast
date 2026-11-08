"""Acceso de solo lectura a lo que hay en `conocimiento/` (biblioteca SQLite, JSONL y Markdown).

Única excepción: los PDF de plano originales se abren para dibujar sus imágenes y, ya abiertos,
para situar las palabras de su capa de texto. Antes de abrir uno se comprueba que OneDrive lo
tiene en local. Todo lo demás (qué planos hay, su texto, sus globos, medidas y correcciones) sale
de la biblioteca.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import sqlite3
import sys
import threading
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXPLORER = AQUI.parent
REPO = EXPLORER.parent.parent
CONOCIMIENTO = REPO / "conocimiento"
BD = CONOCIMIENTO / "datos" / "biblioteca.sqlite"
OUT = EXPLORER / "out" / "conocimiento"
CACHE = OUT / "cache"
# Calibración .icp → página que dejó probar_lector_planos.py (prototipo de lectura de globos).
CALIBRACION = EXPLORER / "out" / "probar-planos-calibracion.json"
# Lecturas y tag de los planos sin .icp que deja leer_planos.py.
LECTURAS = OUT / "lecturas"
# Capturas de cada pieza que deja miniaturas_cad.py.
MINIATURAS = OUT / "cad"
TAGS ={"icp": "Con .icp", "globos": "Globos sin .icp", "numerado": "Numerado sin globos",
        "nada": "Sin globos ni numeración"}

sys.path.insert(0, str(CONOCIMIENTO / "herramientas"))
from cadena_correcciones import MUESTREO, serie_de  # noqa: E402
from comun import COMPONENTES, EXEMPLES, componente_de_nombre, original  # noqa: E402, F401

RECALL = 0x400000 | 0x40000 | 0x1000  # atributos de OneDrive: el fichero no está en local
EXCLUIDAS = {"aleatoria": "generada con RAND() (I-003)", "cero": "cero (I-002)", "atipico": "atípico"}
# Planos guardados de lado: giro horario (grados) que deja el texto derecho. Comprobado a ojo el 05/11/2026.
GIROS = {"3202_balloned low resolution.pdf": 90, "3206-A_balloned lr.pdf": 90, "Drw_Marking_DR_intern02.pdf": 270}
MIN_DENTRO_HOJA = .95  # parte de los sellos que debe caer en la hoja para dar por bueno el calco 1:1
# Tag de la pieza: qué datos tiene. La cuenta automática falla en dos, por cómo están hechos sus ficheros.
TAGS_PIEZA = {"correcciones": "Medidas y correcciones", "medidas": "Medidas sin correcciones", "nada": "Sin medidas"}
TAG_FIJO = {
    "3056": ("correcciones", "Tiene plan de corrección (20200207-Tool correction_1_P3056.pptx), casi solo en imágenes: no se enlaza a ninguna cota (I-602)."),
    "3226": ("medidas", "Su intern.01 tiene valores en la hoja DR, pero sin columnas de cavidad rotuladas: el lector no la reconoce y la tabla sale a cero."),
}
# Familias de pieza. No están en los datos como campo: son agrupaciones nuestras, con su fuente.
FAMILIAS = {
    "Bearing Plate": {"piezas": ["3174", "3186", "3218"], "fuente": "Nombre en las cabeceras DR; mismo plano y numeración (1-clips/3186.md, I-301)."},
    "Pump Housing": {"piezas": ["2820", "3051", "3212"], "fuente": "Nombre de carpeta y de STEP; misma familia en 0-bolt-eye/otros-proyectos.md."},
    "Shroud": {"piezas": ["3205", "3206"], "fuente": "SHROUD, WATER PUMP en las cabeceras DR; misma familia en 2-nervios-soldadura/README.md."},
    "Isomask": {"piezas": ["3233", "3237", "3238"], "supuesta": True,
                "fuente": "Suposición: forma parecida en las capturas y el nombre Isomask/Insulation Mask. Ningún documento las agrupa; sin confirmar por INTEPLAST."},
}
FAMILIA_DE = {c: nombre for nombre, f in FAMILIAS.items() for c in f["piezas"]}
# Qué plano es cada componente, según 4-tetones/3288.md: BSG-296-00 es el conjunto y no se asume ninguno.
PLANOS_COMPONENTE = {"3288": [(r"BSG-296-0?1\b|\bBASE\b", "base"), (r"BSG-296-0?2\b|\bTAPA\b", "tapa"), (r"BSG-296-00\b", "conjunto")]}


def componente_de_plano(codigo: str, nombre: str) -> str | None:
    return next((comp for patron, comp in PLANOS_COMPONENTE.get(codigo, []) if re.search(patron, nombre, re.I)), None)


def con() -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{BD.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def sin_acentos(texto: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn").lower()


# ---------------------------------------------------------------- planos

PLANOS_SQL = (
    "SELECT id, feature, pieza, codigo, ruta, nombre, estado FROM documento WHERE ext='pdf'"
    " AND duplicado_de IS NULL AND estado IN ('sin_texto','extraido') AND (carpeta_norm='pieza_2d3d'"
    " OR lower(ruta) LIKE '%ballo%' OR lower(ruta) LIKE '%balon%' OR lower(ruta) LIKE '%drw%')"
    " ORDER BY codigo, ruta"
)


@lru_cache(maxsize=1)
def calibraciones() -> dict:
    try:
        return json.loads(CALIBRACION.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def icps_de_carpeta(c, ruta: str) -> list[sqlite3.Row]:
    """.icp de la carpeta del PDF y de las carpetas de sus copias idénticas (mismo SHA-256)."""
    carpetas = {posixpath.dirname(ruta)}
    for (otra,) in c.execute("SELECT o.ruta FROM documento d JOIN documento o ON o.sha256=d.sha256 AND o.id<>d.id"
                             " WHERE d.ruta=? AND d.sha256 IS NOT NULL", (ruta,)):
        carpetas.add(posixpath.dirname(otra))
    salida = []
    for carpeta in sorted(carpetas):
        filas = c.execute(
            "SELECT d.id, d.ruta, d.nombre, count(g.sello) AS globos, sum(g.x1 IS NOT NULL AND g.etiqueta IS NOT NULL) AS situados"
            " FROM documento d LEFT JOIN globo g ON g.documento_id=d.id WHERE d.ext='icp' AND d.ruta LIKE ? GROUP BY d.id",
            (carpeta + "/%",)).fetchall()
        salida += [f for f in filas if posixpath.dirname(f["ruta"]) == carpeta]
    return salida


def paginas(c, doc: int) -> list[dict]:
    salida = []
    for f in c.execute("SELECT localizador, texto, datos FROM elemento WHERE documento_id=? AND tipo='pagina' ORDER BY orden", (doc,)):
        datos = json.loads(f["datos"] or "{}")
        m = re.search(r"(\d+)", f["localizador"] or "")
        salida.append({"pagina": int(m.group(1)) if m else len(salida) + 1, "texto": f["texto"] or "",
                       "ancho_pt": datos.get("ancho_pt"), "alto_pt": datos.get("alto_pt"),
                       "imagenes": datos.get("imagenes")})
    return salida


@lru_cache(maxsize=None)
def lectura(doc: int) -> dict | None:
    """Lo que dejó leer_planos.py para este plano, o None si aún no se ha leído."""
    try:
        return json.loads((LECTURAS / f"{doc}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=1)
def planos() -> list[dict]:
    c = con()
    cal = calibraciones()
    salida = []
    for f in c.execute(PLANOS_SQL).fetchall():
        pags = paginas(c, f["id"])
        icps = icps_de_carpeta(c, f["ruta"])
        calibradas = sorted(int(k.split("-p")[1]) for k in cal if k.split("-p")[0] == str(f["id"]))
        leido = None if icps else lectura(f["id"])
        salida.append({
            "id": f["id"], "feature": f["feature"], "pieza": f["pieza"], "codigo": f["codigo"],
            "ruta": f["ruta"], "nombre": f["nombre"], "estado": f["estado"],
            "paginas": max(1, len(pags)), "con_texto": sum(bool(p["texto"].strip()) for p in pags),
            "icp": [i["nombre"] for i in icps], "globos_icp": sum(i["situados"] or 0 for i in icps),
            "calibradas": calibradas, "giro": GIROS.get(f["nombre"], 0),
            "componente": componente_de_plano(f["codigo"], f["nombre"]),
            # Un solo estado por plano. Sin .icp ni lectura todavía no se sabe: no se inventa ninguno.
            "tag": "icp" if icps else leido["tag"] if leido else None,
            "detectados": leido["detectados"] if leido else 0, "leidos": leido["leidos"] if leido else 0,
        })
    return salida


def plano(doc: int) -> dict | None:
    return next((p for p in planos() if p["id"] == doc), None)


def estado_onedrive(ruta: str) -> tuple[bool, str]:
    path = original(ruta)
    try:
        atributos = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
    except OSError as e:
        return False, f"no se puede leer: {e}"
    if atributos & RECALL:
        return False, "en la nube (OneDrive): no se abre para no forzar la descarga"
    return True, "local"


_bloqueo_render = threading.Lock()


def endereza(page, giro: int) -> None:
    """Gira la página solo en memoria: el original no se toca."""
    if giro:
        page.set_rotation((page.rotation + giro) % 360)


def girar_punto(x: float, y: float, giro: int) -> tuple[float, float]:
    """Coordenadas 0–1 de la página original en la página enderezada."""
    return {90: (1 - y, x), 270: (y, 1 - x)}.get(giro, (x, y))


def imagen(doc: int, pagina: int, tipo: str) -> Path | None:
    """JPEG de una página: 'mini' (420 px de ancho) o 'grande' (hasta 4000 px de lado). En caché."""
    p = plano(doc)
    if not p:
        return None
    giro = GIROS.get(p["nombre"], 0)
    destino = CACHE / f"{doc}-p{pagina}-{tipo}{f'-g{giro}' if giro else ''}.jpg"
    if destino.is_file():
        return destino
    local, _ = estado_onedrive(p["ruta"])
    if not local:
        return None
    import fitz  # PyMuPDF

    with _bloqueo_render:
        if destino.is_file():
            return destino
        CACHE.mkdir(parents=True, exist_ok=True)
        with fitz.open(original(p["ruta"])) as pdf:
            if not 1 <= pagina <= pdf.page_count:
                return None
            page = pdf[pagina - 1]
            endereza(page, giro)
            lado = max(page.rect.width, page.rect.height)
            zoom = 420 / page.rect.width if tipo == "mini" else min(4000 / lado, 6.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            destino.write_bytes(pix.tobytes("jpg", jpg_quality=82))
    return destino


def palabras(doc: int, pagina: int) -> list[dict]:
    """Palabras de la capa de texto con su caja normalizada (0–1). Del PDF original, en caché."""
    p = plano(doc)
    giro = GIROS.get(p["nombre"], 0) if p else 0
    destino = CACHE / f"{doc}-p{pagina}-palabras{f'-g{giro}' if giro else ''}.json"
    if destino.is_file():
        return json.loads(destino.read_text(encoding="utf-8"))
    if not p or not estado_onedrive(p["ruta"])[0]:
        return []
    import fitz

    with fitz.open(original(p["ruta"])) as pdf:
        page = pdf[pagina - 1]
        endereza(page, giro)
        w, h = page.rect.width, page.rect.height
        giro = page.rotation_matrix
        salida = []
        for x0, y0, x1, y1, texto, *_ in page.get_text("words"):
            r = fitz.Rect(x0, y0, x1, y1) * giro if page.rotation else fitz.Rect(x0, y0, x1, y1)
            r.normalize()
            salida.append({"t": texto, "x": r.x0 / w, "y": r.y0 / h, "w": r.width / w, "h": r.height / h})
    CACHE.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    return salida


def filas_globo(c, icp_id: int) -> list[sqlite3.Row]:
    """Sellos del .icp con número y las dos posiciones: cabeza (redonda) y punta (señala la cota)."""
    return c.execute("SELECT etiqueta, x1, y1, x2, y2 FROM globo WHERE documento_id=? AND x1 IS NOT NULL"
                     " AND x2 IS NOT NULL AND etiqueta IS NOT NULL", (icp_id,)).fetchall()


def globos_calibrados(c, icp_id: int, cal: dict, giro: int = 0) -> list[dict]:
    m, cual, signo = cal["matriz"], cal["punto"], cal["signo"]

    def aplica(x: float, y: float) -> tuple[float, float]:
        y = signo * y
        return girar_punto(m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2], giro)

    salida = []
    for f in filas_globo(c, icp_id):
        cabeza, punta = ((f["x1"], f["y1"]), (f["x2"], f["y2"])) if cual == 0 else ((f["x2"], f["y2"]), (f["x1"], f["y1"]))
        x, y = aplica(*cabeza)
        px, py = aplica(*punta)
        salida.append({"etiqueta": f["etiqueta"], "x": x, "y": y, "px": px, "py": py})
    return salida


def calibracion_gemela(doc: int, nombre_icp: str, pag: dict) -> dict | None:
    """Calibración de otro plano con el mismo .icp y la misma forma de hoja: el mismo dibujo globado.

    Sirve cuando el 1:1 falla porque la hoja está impresa a otra escala. Las calibraciones están
    normalizadas a la página, así que no dependen del tamaño.
    """
    c = con()
    forma = pag["ancho_pt"] / pag["alto_pt"]
    for clave, cal in calibraciones().items():
        otro, _, numero = clave.partition("-p")
        if cal["icp"] != nombre_icp or int(otro) == doc:
            continue
        pag_otro = next((x for x in paginas(c, int(otro)) if str(x["pagina"]) == numero), None)
        if pag_otro and pag_otro["ancho_pt"] and abs(pag_otro["ancho_pt"] / pag_otro["alto_pt"] - forma) < .01:
            return cal
    return None


def globos_leidos(doc: int, pagina: int) -> dict:
    """Lecturas automáticas de un plano sin .icp (globos dibujados o numeración propia)."""
    r = lectura(doc)
    if not r or r["tag"] not in ("globos", "numerado"):
        return {"globos": [], "metodo": None}
    salida = [{"etiqueta": x["t"], "x": x["x"], "y": x["y"], "w": x["w"], "h": x["h"]} for x in r["lecturas"] if x["p"] == pagina]
    if r["tag"] == "globos":
        pag = next((x for x in r["paginas"] if x["pagina"] == pagina), {"detectados": 0, "leidos": 0})
        detalle = f"lectura automática: {pag['leidos']} leídos de {pag['detectados']} globos detectados. Puede fallar sin avisar"
    elif salida:
        detalle = "lectura automática de la numeración del plano. Puede fallar sin avisar"
    else:
        detalle = "la numeración está en el texto del PDF: se encuentra con el buscador"
    return {"globos": salida, "metodo": "lectura" if salida else None, "detalle": detalle}


def globos(doc: int, pagina: int) -> dict:
    """Globos situados sobre la página (coordenadas 0–1): del .icp o, sin él, de las lecturas guardadas.

    Con calibración del prototipo (RANSAC sobre los globos detectados) la posición es fiable. Sin
    ella se supone el plano a escala 1:1 con el origen en el centro de la hoja (lo que cumplen las
    calibraciones existentes) y la posición es aproximada. Si eso deja puntos fuera de la hoja, el
    plano está a otra escala y se usa la calibración de su gemela. `x, y` es la cabeza del globo y
    `px, py` su punta.
    """
    p = plano(doc)
    if not p:
        return {"globos": [], "metodo": None}
    c = con()
    icps = icps_de_carpeta(c, p["ruta"])
    if not icps:
        return globos_leidos(doc, pagina)
    guardada = calibraciones().get(f"{doc}-p{pagina}")
    if guardada:
        icp = next((i for i in icps if i["nombre"] == guardada["icp"]), None)
        if icp:
            return {"globos": globos_calibrados(c, icp["id"], guardada, GIROS.get(p["nombre"], 0)), "metodo": "calibrada", "icp": icp["nombre"],
                    "detalle": f"calibración del prototipo: {guardada['inliers']} de {guardada['tentativos']} emparejamientos"}
    if pagina != 1:
        return {"globos": [], "metodo": None, "detalle": "sin calibración para esta página"}
    pag = next((x for x in paginas(c, doc) if x["pagina"] == pagina), None)
    if not pag or not pag["ancho_pt"]:
        return {"globos": [], "metodo": None}
    raiz = Path(p["nombre"]).stem.lower()
    icp = next((i for i in icps if Path(i["nombre"]).stem.lower() == raiz), None) or max(icps, key=lambda i: i["situados"] or 0)
    ancho_mm, alto_mm = pag["ancho_pt"] * 25.4 / 72, pag["alto_pt"] * 25.4 / 72
    todos = [{"etiqueta": f["etiqueta"], "x": .5 + f["x1"] / ancho_mm, "y": .5 - f["y1"] / alto_mm,
              "px": .5 + f["x2"] / ancho_mm, "py": .5 - f["y2"] / alto_mm} for f in filas_globo(c, icp["id"])]
    dentro = [g for g in todos if -.05 < g["x"] < 1.05 and -.05 < g["y"] < 1.05]
    if len(dentro) < MIN_DENTRO_HOJA * len(todos):
        gemela = calibracion_gemela(doc, icp["nombre"], pag)
        if gemela:
            return {"globos": globos_calibrados(c, icp["id"], gemela), "metodo": "gemela", "icp": icp["nombre"],
                    "detalle": "sin globos dibujados: número y línea salen del .icp, con la calibración de su versión globada"}
        return {"globos": [], "metodo": None, "icp": icp["nombre"], "detalle": "el .icp no cuadra con la escala de esta hoja"}
    return {"globos": dentro, "metodo": "aproximada", "icp": icp["nombre"],
            "detalle": "sin globos dibujados: número y línea salen del .icp, con escala 1:1 y origen en el centro de la hoja"}


def normaliza_cota(q: str) -> str:
    q = q.strip()
    m = re.fullmatch(r"(?i)(?:n|no\.?|\[\]|□)\s*(\d+(?:\.\d+)?)", q)
    return m.group(1) if m else q


def es_la_cota(palabra: str, cota: str) -> bool:
    """La palabra es esa cota o una subcota, con o sin marca: 30, 30.1, N30, No.30, []30. No 130, 230 ni una fecha."""
    m = re.fullmatch(r"(?i)(?:n|no\.?|\[\]|□)?\s*(\d+(?:\.\d+)*)\.?", palabra.strip().strip(",;:()"))
    return bool(m) and (m.group(1) == cota or m.group(1).startswith(cota + "."))


def buscar_en_plano(doc: int, q: str) -> dict:
    q = q.strip()
    if not q:
        return {"resultados": []}
    p = plano(doc)
    cota = normaliza_cota(q)
    con_marca = cota != q  # N30 pregunta por una cota; 30 sigue siendo una búsqueda de texto
    clave = sin_acentos(cota if con_marca else q)
    resultados = []
    for pagina in range(1, p["paginas"] + 1):
        g = globos(doc, pagina)
        for b in g["globos"]:
            if b["etiqueta"] and (b["etiqueta"] == cota or b["etiqueta"].split(".")[0] == cota):
                tipo = "lectura automática" if g["metodo"] == "lectura" else f"globo ({g['metodo']})"
                ancho, alto = max(b.get("w", 0), .012), max(b.get("h", 0), .012)
                resultados.append({"pagina": pagina, "tipo": tipo, "texto": b["etiqueta"],
                                   "x": b["x"] - ancho / 2, "y": b["y"] - alto / 2, "w": ancho, "h": alto})
    c = con()
    paginas_con = {x["pagina"] for x in paginas(c, doc) if clave in sin_acentos(x["texto"])}
    for pagina in sorted(paginas_con):
        for w in palabras(doc, pagina):
            if es_la_cota(w["t"], cota) if con_marca else clave in sin_acentos(w["t"]):
                resultados.append({"pagina": pagina, "tipo": "texto del PDF", "texto": w["t"], **{k: w[k] for k in "xywh"}})
    componente = p["componente"] if p["componente"] in COMPONENTES.get(p["codigo"], {}) else None
    return {"resultados": resultados[:400], "cota": info_cota(p["codigo"], cota, componente=componente) if p["codigo"] else None,
            "paginas_con_texto": sorted(paginas_con)}


# ---------------------------------------------------------------- medidas y piezas

_medidas: dict[str, list[dict]] = {}
_bloqueo_medidas = threading.Lock()


def medidas(codigo: str) -> list[dict]:
    """Medidas de informes (medida_dr) de la pieza con su muestreo deducido del nombre del fichero."""
    with _bloqueo_medidas:
        if codigo in _medidas:
            return _medidas[codigo]
        c = con()
        fechas = {}
        for f in c.execute("SELECT p.documento_id, p.metadatos FROM perfil_ppap p JOIN documento d ON d.id=p.documento_id"
                           " WHERE d.codigo=?", (codigo,)):
            fecha = (json.loads(f["metadatos"] or "{}") or {}).get("report_date")
            if fecha:
                fechas.setdefault(f["documento_id"], str(fecha)[:10])
        docs = {f["id"]: f for f in c.execute("SELECT id, nombre, ruta FROM documento WHERE codigo=? AND carpeta_norm='metrologia'", (codigo,))}
        papeles = {(f["documento_id"], f["hoja"]): f["papel"] for f in c.execute(
            "SELECT documento_id, hoja, papel FROM lectura_dr WHERE documento_id IN (%s)" % ",".join(map(str, docs) or ["0"]))}
        filas = []
        if docs:
            for f in c.execute("SELECT documento_id, hoja, fila, col, cota, cavidad, valor, nominal, tol_sup, tol_inf, marca"
                               " FROM medida_dr WHERE documento_id IN (%s)" % ",".join(map(str, docs))):
                d = docs[f["documento_id"]]
                m = MUESTREO.search(d["nombre"])
                filas.append({**dict(f), "nombre": d["nombre"], "ruta": d["ruta"],
                              "papel": papeles.get((f["documento_id"], f["hoja"])),
                              "serie": serie_de(d["nombre"]) if m else None,
                              "muestreo": int(m.group(1)) if m else None, "fecha": fechas.get(f["documento_id"])})
        _medidas[codigo] = filas
        return filas


def clave_cota(cota: str):
    partes = re.findall(r"\d+|\D+", cota or "")
    return [(0, int(x)) if x.isdigit() else (1, x) for x in partes]


def tolerancia(f: dict) -> tuple:
    """Nominal y tolerancias redondeadas: 0.0499999999 y 0.05 son la misma tolerancia."""
    return tuple(None if v is None else round(v, 6) for v in (f["nominal"], f["tol_sup"], f["tol_inf"]))


def info_cota(codigo: str, cota: str, solo_con_muestreo: bool = False, componente: str | None = None) -> dict:
    """Recuentos de una cota. Con `componente`, solo los de esa pieza del libro: en el 3288 el número es otra cota en cada una."""
    filas = [f for f in medidas(codigo) if f["cota"] == cota and (f["muestreo"] is not None or not solo_con_muestreo)
             and (componente is None or componente_de_nombre(codigo, f["hoja"]) == componente)]
    nominales = Counter(tolerancia(f) for f in filas if f["nominal"] is not None)
    c = con()
    cadenas = sum(componente_de_nombre(codigo, f[0]) in (None, componente) or componente is None for f in c.execute(
        "SELECT d.nombre FROM cadena_correccion ca JOIN documento d ON d.id = ca.documento_id WHERE ca.pieza=? AND ca.cota=?", (codigo, cota)))
    return {"pieza": codigo, "cota": cota, "medidas": len(filas),
            "excluidas": sum(f["marca"] in EXCLUIDAS for f in filas),
            "nominal": [list(k) + [n] for k, n in nominales.most_common(3)], "correcciones": cadenas,
            "documentos": len({f["documento_id"] for f in filas})}


@lru_cache(maxsize=1)
def hallazgos() -> list[dict]:
    salida = []
    for linea in (CONOCIMIENTO / "hallazgos.jsonl").read_text(encoding="utf-8").splitlines():
        if linea.strip():
            salida.append(json.loads(linea))
    return salida


@lru_cache(maxsize=1)
def casos() -> list[dict]:
    texto = (CONOCIMIENTO / "casos-referencia.jsonl").read_text(encoding="utf-8")
    return [json.loads(x) for x in texto.splitlines() if x.strip()]


def piezas_de(valor) -> set[str]:
    return set(re.findall(r"\b\d{4}\b", str(valor or "")))


def cad_de(codigo: str) -> list[sqlite3.Row]:
    """STEP de la propia pieza (`1- 2D y 3D pieza`), sin los del molde ni los del método de medida."""
    return con().execute("SELECT nombre, ruta FROM documento WHERE codigo=? AND lower(ext) IN ('stp','step')"
                         " AND carpeta_norm='pieza_2d3d' AND duplicado_de IS NULL ORDER BY nombre", (codigo,)).fetchall()


@lru_cache(maxsize=1)
def piezas() -> list[dict]:
    """Una fila por pieza con sus cifras, para poder compararlas. Mismas definiciones que `pieza()`."""
    c = con()
    salida = {}
    for f in c.execute("SELECT codigo, feature, pieza, count(*) n, sum(tamano) b FROM documento WHERE codigo IS NOT NULL"
                       " GROUP BY codigo, feature, pieza"):
        p = salida.setdefault(f["codigo"], {"codigo": f["codigo"], "features": [], "carpetas": [], "documentos": 0, "bytes": 0,
                                            "planos": 0, "correcciones": 0, "hallazgos": 0, "casos": 0})
        p["features"].append(f["feature"])
        p["carpetas"].append(f["pieza"])
        p["documentos"] += f["n"]
        p["bytes"] += f["b"] or 0
    for h in hallazgos():
        for cod in piezas_de(h.get("pieza")):
            if cod in salida:
                salida[cod]["hallazgos"] += 1
    for f in c.execute("SELECT pieza, count(*) FROM cadena_correccion GROUP BY pieza"):
        if f[0] in salida:
            salida[f[0]]["correcciones"] = f[1]
    for p in planos():
        if p["codigo"] in salida:
            salida[p["codigo"]]["planos"] += 1
    for x in casos():
        if str(x.get("pieza")) in salida:
            salida[str(x.get("pieza"))]["casos"] += 1
    muestreos, cotas = defaultdict(set), defaultdict(set)
    for f in c.execute("SELECT d.codigo, d.nombre, m.cota FROM medida_dr m JOIN documento d ON d.id=m.documento_id"
                       " WHERE d.carpeta_norm='metrologia' AND d.codigo IS NOT NULL GROUP BY d.id, m.cota"):
        m = MUESTREO.search(f["nombre"])
        if m:
            muestreos[f["codigo"]].add((serie_de(f["nombre"]), int(m.group(1))))
            cotas[f["codigo"]].add(f["cota"])
    for codigo, p in salida.items():
        p["muestreos"], p["cotas"] = len(muestreos[codigo]), len(cotas[codigo])
        p["cad"] = [f["nombre"] for f in cad_de(codigo)]
        p["tag"], p["tag_motivo"] = TAG_FIJO.get(codigo) or (tag_de_pieza(p), None)
        p["familia"] = FAMILIA_DE.get(codigo)
    return sorted(salida.values(), key=lambda p: p["codigo"])


def tag_de_pieza(p: dict) -> str:
    return "nada" if not p["cotas"] else "correcciones" if p["correcciones"] else "medidas"


def identidad(codigo: str) -> list[str]:
    """Filas de identidad-piezas.md que citan la pieza (tal cual, Markdown)."""
    texto = (CONOCIMIENTO / "identidad-piezas.md").read_text(encoding="utf-8")
    cabecera, filas = None, []
    for linea in texto.splitlines():
        if linea.startswith("|") and cabecera is None and "---" not in linea:
            cabecera = linea
        if linea.startswith("|") and re.search(rf"\b{codigo}\b", linea):
            filas.append(linea)
    return ([cabecera, "|" + "---|" * (cabecera.count("|") - 1)] + filas) if cabecera and filas else []


def pieza(codigo: str) -> dict:
    c = con()
    carpetas = [dict(f) for f in c.execute(
        "SELECT carpeta_norm, count(*) n, sum(estado='extraido') extraidos, sum(estado='solo_metadatos') metadatos,"
        " sum(estado='sin_texto') sin_texto, sum(estado='duplicado') duplicados FROM documento WHERE codigo=? GROUP BY 1 ORDER BY 2 DESC",
        (codigo,))]
    extensiones = [dict(f) for f in c.execute("SELECT ext, count(*) n FROM documento WHERE codigo=? GROUP BY 1 ORDER BY 2 DESC", (codigo,))]
    filas = medidas(codigo)
    muestreos = defaultdict(lambda: {"documentos": set(), "medidas": 0, "excluidas": 0, "fechas": set(), "papeles": Counter()})
    cotas = defaultdict(lambda: {"medidas": 0, "muestreos": set()})
    por_componente: dict = defaultdict(lambda: defaultdict(lambda: {"medidas": 0, "muestreos": set()}))
    sin_muestreo = set()
    for f in filas:
        if f["muestreo"] is None:
            sin_muestreo.add(f["nombre"])
            continue
        clave = f"{f['serie']}/{f['muestreo']:02d}"
        m = muestreos[clave]
        m["documentos"].add(f["nombre"])
        m["medidas"] += 1
        m["excluidas"] += f["marca"] in EXCLUIDAS
        m["papeles"][f["papel"] or "?"] += 1
        if f["fecha"]:
            m["fechas"].add(f["fecha"])
        cotas[f["cota"]]["medidas"] += 1
        cotas[f["cota"]]["muestreos"].add(clave)
        componente = componente_de_nombre(codigo, f["hoja"])
        if componente:
            por_componente[f["cota"]][componente]["medidas"] += 1
            por_componente[f["cota"]][componente]["muestreos"].add(clave)
    cadenas = [{**dict(f), "componente": componente_de_nombre(codigo, f["pptx"])} for f in c.execute(
        "SELECT cota, numero, fecha_correccion, serie, origen_muestreo, origen_fuera, origen_n, validacion_muestreo,"
        " validacion_fuera, validacion_n, validacion_estado, nominal, tol_sup, tol_inf, avisos, documento_id, diapositiva,"
        " (SELECT nombre FROM documento d WHERE d.id = documento_id) AS pptx"
        " FROM cadena_correccion WHERE pieza=? ORDER BY fecha_orden, cota", (codigo,))]
    return {
        "codigo": codigo, "resumen": next((p for p in piezas() if p["codigo"] == codigo), None),
        "componentes": COMPONENTES.get(codigo, {}),
        "identidad": identidad(codigo), "carpetas": carpetas, "extensiones": extensiones,
        "muestreos": [{"clave": k, "documentos": sorted(v["documentos"]), "medidas": v["medidas"], "excluidas": v["excluidas"],
                       "fechas": sorted(v["fechas"]), "papeles": dict(v["papeles"])} for k, v in sorted(muestreos.items())],
        "sin_muestreo": sorted(sin_muestreo),
        "cotas": [{"cota": k, "medidas": v["medidas"], "muestreos": len(v["muestreos"]),
                   "por_componente": {n: {"medidas": x["medidas"], "muestreos": len(x["muestreos"])} for n, x in por_componente[k].items()}}
                  for k, v in sorted(cotas.items(), key=lambda kv: clave_cota(kv[0]))],
        "cadenas": cadenas,
        "hallazgos": [h for h in hallazgos() if codigo in piezas_de(h.get("pieza"))],
        "casos": [x for x in casos() if str(x.get("pieza")) == codigo],
    }


def resumen_cota(codigo: str, cota: str, componente: str | None = None) -> dict:
    info = info_cota(codigo, cota, solo_con_muestreo=True, componente=componente)
    info["sin_muestreo"] = info_cota(codigo, cota, componente=componente)["medidas"] - info["medidas"]
    return info
