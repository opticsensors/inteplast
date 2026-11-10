"""Mide los lectores de planos numerados sin globos (`[]`, `No.` y recuadros) de `lectores_planos.py`.

Mide lo que ofrece el visor de conocimiento, sin ajustar nada. Tres fases, todo en una carpeta:

    python probar_lectores_numerados.py leer      # lee los planos (lento: ~30 min con 4 procesos)
    python probar_lectores_numerados.py muestra   # elige la muestra con semilla y genera los recortes
    python probar_lectores_numerados.py informe   # cuenta con las decisiones de revision.json

Qué se mide, por plano y página (alcance: solo los 4 planos conocidos, sin validación independiente):
- **Lecturas ofrecidas** (muestra al azar con semilla): número correcto y ubicación correcta, por
  separado. «Ubicación correcta» = la caja está sobre una marca de numeración de una cota, no sobre
  el mismo número en una tabla o una nota, ni desplazada.
- **Omisiones confirmadas en la revisión**: marcas vistas en el plano que el lector no ofrece. No es
  una tasa de detección: no se ha inventariado todo el plano.
- **Contraste con los informes**: las cotas numéricas de `medida_dr` que no aparecen entre las
  lecturas son «cotas del informe no encontradas». Solo pasan a omisión si se ve su marca en el plano.
- **Controles negativos**: planos donde el visor pasa estos lectores y no están numerados (3205-B y
  3206), y dos escaneos con globos donde se fuerzan. Cada detección se revisa antes de contarla como
  falsa; si hubiera muchas, se revisa una muestra y el resto queda pendiente.

Las cotas con letra del 3214 (`A4`, `D5`…) quedan fuera: siguen pendientes.

Reproducible: `lecturas/<doc>.json` guarda la identidad del lector (huellas del código, versión de
RapidOCR) y la firma del PDF, y no se reutiliza si cambia cualquiera de las dos; `muestra.json`, la
semilla y la selección; `revision.json`, las decisiones de la revisión a ojo. Cada decisión lleva la
huella de lo que se revisó (el PDF y la lectura exacta, o el PDF y la cota; las omisiones, el PDF y todo
lo que ofrece el lector en ese plano). Si cambia, la decisión no vale: `muestra` la pasa a
`invalidadas` y el informe la cuenta como no revisada. Los recortes están en `recortes/` y las hojas
para revisar en `hojas/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cv2
import fitz
import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI), str(AQUI / "conocimiento")]
import datos  # noqa: E402
import leer_planos  # noqa: E402
import lectores_planos as lectores  # noqa: E402

CARPETA = AQUI / "out" / f"probar-numerados-{date.today().isoformat()}"
# Los cuatro planos numerados que leen estos lectores (los otros dos, 3237 y 3238, van por la capa de texto).
POSITIVOS = {1: "2820 []", 582: "3174 No.", 873: "3186 No.", 2243: "3214 recuadros"}
# Sin numeración. En los dos primeros el visor ya pasa estos lectores (escaneo sin texto ni globos);
# en los otros dos, escaneos con globos, el visor no los pasa y aquí se fuerzan.
NEGATIVOS = {1631: "3205-B, plano limpio", 2003: "3206, plano limpio"}
FORZADOS = {329: "3212 rev. 07, escaneo con globos", 2184: "3206 Drw_Marking, cotas resaltadas"}
# Sin informes (2820) o con pocas páginas (3214): se buscan a ojo las marcas sin caja. Lado mayor de la
# página en píxeles: el `[]` del 2820 es texto pequeño; los recuadros del 3214 se ven con menos.
BARRIDO = {1: 6800, 2243: 4200}
SEMILLA = 20261110
N_MUESTRA = 40  # lecturas al azar por plano; si hay pocas más, se revisan todas
N_NEGATIVOS = 60  # detecciones en controles negativos que se revisan todas; con más, una muestra de 40
MAX_CANDIDATOS = 6  # sitios del OCR que se miran por cada cota del informe no encontrada


def huella(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]


def version_de(paquete: str) -> str:
    try:
        return version(paquete)
    except PackageNotFoundError:
        return "no instalado"


def identidad() -> dict:
    """Qué código ha leído: si cambia, las lecturas guardadas ya no valen para esta medida."""
    return {"lectores_planos.py": huella(AQUI / "lectores_planos.py"),
            "leer_planos.py": huella(AQUI / "conocimiento" / "leer_planos.py"),
            "leer_planos": leer_planos.VERSION, "lector_globos": lectores.reader_id(),
            "rapidocr": version_de("rapidocr-onnxruntime"), "onnxruntime": version_de("onnxruntime"),
            "pymupdf": fitz.VersionBind}


# ---------------------------------------------------------------- fase 1: leer

def lee_forzado(doc: int) -> dict:
    """Los dos lectores en todas las páginas, sin el filtro del visor (globos o capa de texto)."""
    p = datos.plano(doc)
    ruta = Path(datos.original(p["ruta"]))
    local, motivo = datos.estado_onedrive(p["ruta"])
    if not local:
        return {"doc": doc, "error": motivo}
    motor, _ = leer_planos.herramientas()
    marcas, recuadros, ocr = [], [], []
    with fitz.open(ruta) as pdf:
        for page in pdf:
            tokens = lectores.ocr_teselas(page, motor)
            ocr.append({"pagina": page.number + 1, "tokens": tokens})
            marcas += lectores.marcas_de_tokens(tokens, page.number + 1)
            recuadros += lectores.recuadros_de_pagina(page, motor)
    return {"firma": leer_planos.firma(ruta), "doc": doc, "codigo": p["codigo"], "nombre": p["nombre"],
            "tag": "forzado", "lecturas": [], "detalle": {"marcas": lectores.recorta_cuadros(marcas),
                                                          "recuadros": recuadros, "ocr": ocr}}


def lee(tarea: tuple[int, str]) -> dict:
    doc, carpeta = tarea
    destino = Path(carpeta) / "lecturas" / f"{doc}.json"
    resultado = lee_forzado(doc) if doc in FORZADOS else leer_planos.lee_plano(doc, detalle=True)
    if resultado.get("error"):
        return resultado
    visor = datos.lectura(doc)
    resultado["ruta"] = datos.plano(doc)["ruta"]
    resultado["identidad"] = identidad()
    resultado["igual_que_visor"] = None if doc in FORZADOS else bool(visor) and visor["lecturas"] == resultado["lecturas"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return resultado


def al_dia(guardado: dict | None, actual: dict, firma_pdf: dict | None) -> bool:
    """Una lectura guardada vale si se hizo con este código y con este mismo PDF."""
    return bool(guardado) and firma_pdf is not None and guardado.get("identidad") == actual \
        and guardado.get("firma") == firma_pdf


def firma_actual(doc: int) -> tuple[dict | None, str]:
    """Firma del PDF tal como está ahora (None si no se puede leer sin forzar OneDrive)."""
    ruta = datos.plano(doc)["ruta"]
    local, motivo = datos.estado_onedrive(ruta)
    return (leer_planos.firma(Path(datos.original(ruta))), motivo) if local else (None, motivo)


def leer(carpeta: Path, docs: list[int], procesos: int) -> None:
    actual = identidad()
    pendientes = []
    for doc in docs:
        ruta = carpeta / "lecturas" / f"{doc}.json"
        guardado = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
        firma_pdf, motivo = firma_actual(doc)
        if firma_pdf is None:
            print(f"{doc}: {motivo}", flush=True)
        elif al_dia(guardado, actual, firma_pdf):
            print(f"{doc}: ya leído con este código y este PDF", flush=True)
        else:
            pendientes.append((doc, str(carpeta)))
    if not pendientes:
        return
    with multiprocessing.get_context("spawn").Pool(max(1, min(procesos, len(pendientes)))) as pool:
        for r in pool.imap_unordered(lee, pendientes):
            if r.get("error"):
                print(f"{r['doc']}: {r['error']}", flush=True)
                continue
            d = r["detalle"]
            print(f"{r['doc']} {r['codigo']} {r['tag']}: {len(r['lecturas'])} lecturas ofrecidas, {len(d['marcas'])} marcas,"
                  f" {len(d['recuadros'])} recuadros; igual que el visor: {r['igual_que_visor']}", flush=True)


# ---------------------------------------------------------------- fase 2: muestra

def elige(total: int, n: int, semilla: int, clave: str) -> list[int]:
    """Índices al azar, reproducibles con la semilla y la clave; si hay pocos más de n, todos."""
    if total <= n + 10:
        return list(range(total))
    return sorted(random.Random(f"{semilla}:{clave}").sample(range(total), n))


def no_encontradas(cotas: set[str], lecturas: list[dict]) -> list[str]:
    """Cotas numéricas de los informes que no aparecen entre las lecturas ofrecidas (contraste)."""
    leidas = {leer_planos.base_cota(x["t"]) for x in lecturas}
    return sorted(cotas - leidas, key=lambda c: (len(c), c))


def candidatos(ocr: list[dict], numero: str, limite: int = MAX_CANDIDATOS) -> list[dict]:
    """Sitios donde el OCR leyó ese número suelto (no dentro de otro): dónde mirar si está su marca."""
    # Ni dentro de otro número ni como decimales («0.123»); «No.123» sí vale.
    patron = re.compile(rf"(?<!\d)(?<!\d[.,]){re.escape(numero)}(?!\d)(?![.,]\d)")
    salida = []
    for pagina in ocr:
        for token in pagina["tokens"]:
            if patron.search(token["texto"]):
                q = np.array(token["q"])
                x0, y0 = q.min(axis=0)
                x1, y1 = q.max(axis=0)
                salida.append({"p": pagina["pagina"], "texto": token["texto"], "x": float((x0 + x1) / 2),
                               "y": float((y0 + y1) / 2), "w": float(x1 - x0), "h": float(y1 - y0)})
    unicos: list[dict] = []
    for c in salida:  # el solape de teselas y los dos sentidos repiten el mismo sitio
        if not any(u["p"] == c["p"] and abs(u["x"] - c["x"]) < .01 and abs(u["y"] - c["y"]) < .01 for u in unicos):
            unicos.append(c)
    return unicos[:limite]


def lecturas(carpeta: Path) -> dict[int, dict]:
    salida = {}
    for f in sorted((carpeta / "lecturas").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        salida[r["doc"]] = r
    return salida


def huella_de(*partes) -> str:
    return hashlib.sha256(json.dumps(partes, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def entrada(r: dict) -> dict:
    """De qué depende la revisión de un plano: el PDF, el código que lo leyó, lo que ofrece el lector y
    todo lo que encontraron los lectores de marcas y recuadros (en los controles, `lecturas` está vacío y
    lo revisado son esas detecciones)."""
    detalle = r.get("detalle", {})
    return {"pdf": r["firma"]["sha256"], "identidad": r["identidad"], "lecturas": huella_de(r["lecturas"]),
            "detecciones": huella_de(detalle.get("marcas", []), detalle.get("recuadros", []))}


def lecturas_cambiadas(plan: dict, leidas: dict[int, dict]) -> list[int]:
    """Planos cuyas lecturas o detecciones ya no son las de la muestra."""
    return [d for d, r in leidas.items() if entrada(r) != plan["entrada"].get(str(d))]


def plan_de_muestra(leidas: dict[int, dict], semilla: int, cotas_de) -> dict:
    """Qué se revisa: lecturas al azar, detecciones de los controles y cotas del informe no encontradas.

    Cada cosa revisable lleva la huella de lo que se mira (PDF y lectura exacta, o PDF y cota): una
    decisión solo vale para esa huella, no para otra lectura que caiga en el mismo identificador.
    """
    items, cotas_faltan = [], {}
    for doc, r in leidas.items():
        pdf = r["firma"]["sha256"]
        if doc in POSITIVOS:
            for i in elige(len(r["lecturas"]), N_MUESTRA, semilla, f"lecturas-{doc}"):
                x = r["lecturas"][i]
                items.append({"id": f"L{doc}-{i}", "tipo": "lectura", "doc": doc, "indice": i, **x,
                              "huella": huella_de(pdf, "lectura", x)})
            cotas = cotas_de(r["codigo"])
            faltan = no_encontradas(cotas, r["lecturas"]) if cotas else []
            cotas_faltan[str(doc)] = {"cotas": len(cotas), "no_encontradas": faltan,
                                      "huellas": {c: huella_de(pdf, "cota", doc, c) for c in faltan}}
            for cota in faltan:
                for k, c in enumerate(candidatos(r["detalle"]["ocr"], cota)):
                    items.append({"id": f"C{doc}-{cota}-{k}", "tipo": "candidato", "doc": doc, "cota": cota,
                                  "p": c["p"], "t": c["texto"], "x": c["x"], "y": c["y"], "w": c["w"], "h": c["h"]})
        else:
            detecciones = r["detalle"]["marcas"] + r["detalle"]["recuadros"]
            elegidas = elige(len(detecciones), 40, semilla, f"negativos-{doc}") if len(detecciones) > N_NEGATIVOS \
                else list(range(len(detecciones)))
            for i in elegidas:
                items.append({"id": f"N{doc}-{i}", "tipo": "negativo", "doc": doc, "indice": i, **detecciones[i],
                              "huella": huella_de(pdf, "negativo", detecciones[i])})
    return {"semilla": semilla, "n_muestra": N_MUESTRA, "items": items, "contraste": cotas_faltan,
            "entrada": {str(d): entrada(r) for d, r in leidas.items()},
            # Una omisión (marca sin lectura) depende del PDF y de todo lo que ofrece el lector en ese plano.
            "huella_omisiones": {str(d): huella_de(r["firma"]["sha256"], "omisiones", r["lecturas"])
                                 for d, r in leidas.items() if d in POSITIVOS},
            "detecciones_negativas": {str(d): len(r["detalle"]["marcas"]) + len(r["detalle"]["recuadros"])
                                      for d, r in leidas.items() if d not in POSITIVOS}}


VACIAS = {"lectura": {"numero": None, "ubicacion": None, "visto": None, "nota": ""},
          "negativo": {"resultado": None, "nota": ""},
          "contraste": {"resultado": None, "evidencia": None, "nota": ""}}


def esperadas(plan: dict) -> dict[str, tuple[str, str]]:
    """Clave de cada decisión -> (huella de lo revisado, tipo)."""
    salida = {i["id"]: (i["huella"], i["tipo"]) for i in plan["items"] if i["tipo"] in ("lectura", "negativo")}
    for doc, c in plan["contraste"].items():
        salida.update({f"C{doc}-{cota}": (c["huellas"][cota], "contraste") for cota in c["no_encontradas"]})
    return salida


def con_contenido(d: dict) -> bool:
    return any(v not in (None, "") for k, v in d.items() if k != "huella")


def concilia(plan: dict, previa: dict) -> dict:
    """La revisión que sigue valiendo para esta muestra. Una decisión cuya huella no coincide (cambió el
    PDF o la lectura) no se arrastra: queda en `invalidadas`, con el motivo, y su sitio vuelve a vacío."""
    previas, invalidadas = previa.get("decisiones", {}), list(previa.get("invalidadas", []))
    decisiones = {}
    for clave, (h, tipo) in esperadas(plan).items():
        d = previas.get(clave)
        if d is not None and d.get("huella") != h:
            if con_contenido(d):
                invalidadas.append({"clave": clave, **d, "motivo": "cambió el PDF o la lectura revisada"})
            d = None
        decisiones[clave] = d if d is not None else {**VACIAS[tipo], "huella": h}
    for clave, d in previas.items():
        if clave not in decisiones and con_contenido(d):
            invalidadas.append({"clave": clave, **d, "motivo": "ya no está en la muestra"})
    omisiones = []
    for o in previa.get("omisiones", []):
        if o.get("huella") == plan["huella_omisiones"].get(str(o["doc"])):
            omisiones.append(o)
        else:
            invalidadas.append({**o, "motivo": "omisión: cambió el PDF o lo que ofrece el lector en ese plano"})
    return {"semilla": plan["semilla"], "decisiones": decisiones, "omisiones": omisiones,
            "invalidadas": invalidadas, "notas": previa.get("notas", "")}


def zoom_de(page) -> float:
    """El mismo aumento que el OCR de las marcas (`lectores.ocr_teselas`)."""
    return min(6., max(3., 4700 / max(1., page.rect.width)))


def pagina_gris(pdf, numero: int, zoom: float | None = None) -> np.ndarray:
    """Página entera en gris, girada como la ve el OCR (las coordenadas 0–1 se refieren a esto)."""
    page = pdf[numero - 1]
    z = zoom or zoom_de(page)
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), colorspace=fitz.csGRAY, alpha=False)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()


def recorte(gris: np.ndarray, item: dict, color=(0, 0, 255)) -> np.ndarray:
    """La caja del item en rojo con contexto alrededor, para ver el número y lo que numera."""
    alto, ancho = gris.shape
    cx, cy, w, h = item["x"] * ancho, item["y"] * alto, max(4, item["w"] * ancho), max(4, item["h"] * alto)
    margen = max(1.5 * max(w, h), 160)
    x0, y0 = int(max(0, cx - w / 2 - margen)), int(max(0, cy - h / 2 - margen))
    x1, y1 = int(min(ancho, cx + w / 2 + margen)), int(min(alto, cy + h / 2 + margen))
    salida = cv2.cvtColor(gris[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    holgura = max(10, .6 * min(w, h))  # que la caja no tache el número que hay que leer
    cv2.rectangle(salida, (int(cx - w / 2 - x0 - holgura), int(cy - h / 2 - y0 - holgura)),
                  (int(cx + w / 2 - x0 + holgura), int(cy + h / 2 - y0 + holgura)), color, 2)
    cv2.circle(salida, (int(cx - x0), int(cy - y0)), 4, color, -1)  # centro: lo que señala el visor
    return salida


def hoja(recortes: list[tuple[str, np.ndarray]], columnas: int = 4, celda: tuple[int, int] = (420, 330)) -> np.ndarray:
    """Hoja de revisión: los recortes en rejilla, cada uno con su rótulo encima."""
    filas = (len(recortes) + columnas - 1) // columnas
    cw, ch = celda
    lienzo = np.full((filas * (ch + 28), columnas * cw, 3), 255, np.uint8)
    for k, (rotulo, img) in enumerate(recortes):
        f, c = divmod(k, columnas)
        escala = min(cw / img.shape[1], ch / img.shape[0], 2.)
        img = cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA if escala < 1 else cv2.INTER_CUBIC)
        y, x = f * (ch + 28) + 26, c * cw
        lienzo[y:y + img.shape[0], x:x + img.shape[1]] = img
        cv2.putText(lienzo, rotulo, (x + 4, y - 7), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.rectangle(lienzo, (x, y), (x + cw - 1, y + ch - 1), (200, 200, 200), 1)
    return lienzo


def rotulo(item: dict) -> str:
    texto = re.sub(r"[^\x20-\x7e]", "?", str(item["t"]))[:18]
    lee = f"cota {item['cota']}: '{texto}'" if item["tipo"] == "candidato" else f"lee {texto} ({item.get('via', '')})"
    return f"{item['id']} p{item['p']} {lee}"


def guarda_png(ruta: Path, img: np.ndarray) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ok, datos_png = cv2.imencode(".png", img)  # imwrite no admite rutas con caracteres no ASCII en Windows
    if not ok:
        raise RuntimeError(f"No se ha podido codificar {ruta}")
    ruta.write_bytes(datos_png.tobytes())


def barrido(gris: np.ndarray, cajas: list[dict], prefijo: str, carpeta: Path, lado: int = 1700) -> list[str]:
    """Teselas de la página con una caja verde en cada lectura ofrecida y una rejilla de 0,05 rotulada.

    Para buscar a ojo marcas sin caja (omisiones). Se saltan las teselas casi en blanco.
    """
    alto, ancho = gris.shape
    color = cv2.cvtColor(gris, cv2.COLOR_GRAY2BGR)
    for x in cajas:
        cx, cy, w, h = x["x"] * ancho, x["y"] * alto, x["w"] * ancho, x["h"] * alto
        cv2.rectangle(color, (int(cx - w / 2 - 4), int(cy - h / 2 - 4)), (int(cx + w / 2 + 4), int(cy + h / 2 + 4)), (0, 170, 0), 3)
    for k in range(1, 20):
        xg, yg = int(k * .05 * ancho), int(k * .05 * alto)
        cv2.line(color, (xg, 0), (xg, alto), (255, 160, 160), 1)
        cv2.line(color, (0, yg), (ancho, yg), (255, 160, 160), 1)
    nombres = []
    for y in range(0, alto, lado - 100):
        for x in range(0, ancho, lado - 100):
            tesela = gris[y:y + lado, x:x + lado]
            if (tesela < 160).mean() < .004:
                continue
            img = color[y:y + lado, x:x + lado].copy()
            for k in range(0, 21):  # rótulos de la rejilla visibles en esta tesela
                xg, yg = int(k * .05 * ancho) - x, int(k * .05 * alto) - y
                if 0 <= xg < img.shape[1]:
                    cv2.putText(img, f"x{k * .05:.2f}", (xg + 3, 22), cv2.FONT_HERSHEY_SIMPLEX, .7, (200, 0, 0), 2)
                if 0 <= yg < img.shape[0]:
                    cv2.putText(img, f"y{k * .05:.2f}", (3, yg - 4), cv2.FONT_HERSHEY_SIMPLEX, .7, (200, 0, 0), 2)
            nombre = f"{prefijo}-x{x / ancho:.2f}-y{y / alto:.2f}.png"
            guarda_png(carpeta / nombre, img)
            nombres.append(nombre)
    return nombres


def muestra(carpeta: Path, semilla: int) -> None:
    leidas = lecturas(carpeta)
    faltan = [d for d in (*POSITIVOS, *NEGATIVOS, *FORZADOS) if d not in leidas]
    if faltan:
        sys.exit(f"Faltan lecturas de {faltan}: ejecutar antes la fase «leer»")
    distintas = [d for d, r in leidas.items() if r["igual_que_visor"] is False]
    if distintas:
        print(f"AVISO: las lecturas de {distintas} no son las que enseña el visor", flush=True)
    c = datos.con()
    plan = plan_de_muestra(leidas, semilla, lambda codigo: leer_planos.cotas_informes(c, codigo))
    (carpeta / "muestra.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    por_doc = defaultdict(list)
    for item in plan["items"]:
        por_doc[item["doc"]].append(item)
    for doc, items in por_doc.items():
        with fitz.open(datos.original(leidas[doc]["ruta"])) as pdf:
            for p in sorted({i["p"] for i in items}):
                gris = pagina_gris(pdf, p)
                for item in (i for i in items if i["p"] == p):
                    item["_img"] = recorte(gris, item)
                    guarda_png(carpeta / "recortes" / f"{item['id']}.png", item["_img"])
        for tipo in ("lectura", "candidato", "negativo"):
            grupo = [i for i in items if i["tipo"] == tipo]
            for k in range(0, len(grupo), 20):
                guarda_png(carpeta / "hojas" / f"{tipo}-{doc}-{k // 20 + 1:02d}.png",
                           hoja([(rotulo(i), i["_img"]) for i in grupo[k:k + 20]]))
    for doc, lado in BARRIDO.items():
        r = leidas[doc]
        with fitz.open(datos.original(r["ruta"])) as pdf:
            for page in pdf:
                gris = pagina_gris(pdf, page.number + 1, zoom=lado / max(page.rect.width, page.rect.height))
                cajas = [x for x in r["lecturas"] if x["p"] == page.number + 1]
                nombres = barrido(gris, cajas, f"barrido-{doc}-p{page.number + 1}", carpeta / "barrido")
                print(f"barrido {doc} p{page.number + 1}: {len(nombres)} teselas", flush=True)
    revision = carpeta / "revision.json"
    previa = json.loads(revision.read_text(encoding="utf-8")) if revision.exists() else {}
    nueva = concilia(plan, previa)
    revision.write_text(json.dumps(nueva, ensure_ascii=False, indent=1), encoding="utf-8")
    cuenta = Counter(i["tipo"] for i in plan["items"])
    nuevas_invalidadas = len(nueva["invalidadas"]) - len(previa.get("invalidadas", []))
    print(f"Muestra con semilla {semilla}: {dict(cuenta)}; cotas del informe no encontradas: "
          f"{ {d: len(c['no_encontradas']) for d, c in plan['contraste'].items()} }. Decisiones en {revision}"
          + (f"; {nuevas_invalidadas} decisiones invalidadas (ver «invalidadas»)" if nuevas_invalidadas else ""), flush=True)


# ---------------------------------------------------------------- fase 3: informe

NUMERO, UBICACION = ("bien", "mal", "dudoso"), ("bien", "mal", "dudoso")
NEGATIVO = ("falso", "marca_real", "dudoso")
CONTRASTE = ("omision_confirmada", "no_encontrada")


def valida(plan: dict, revision: dict) -> list[str]:
    """Decisiones con valores fuera de las categorías: un error de la revisión, no se adivina."""
    errores = []
    for item in plan["items"]:
        d = revision["decisiones"].get(item["id"])
        if item["tipo"] == "lectura" and d:
            errores += [f"{item['id']}: {k}={d.get(k)!r}" for k, ok in (("numero", NUMERO), ("ubicacion", UBICACION))
                        if d.get(k) is not None and d.get(k) not in ok]
        elif item["tipo"] == "negativo" and d and d.get("resultado") is not None and d["resultado"] not in NEGATIVO:
            errores.append(f"{item['id']}: resultado={d['resultado']!r}")
    for clave, d in revision["decisiones"].items():
        if clave.startswith("C") and d.get("resultado") is not None and d["resultado"] not in CONTRASTE:
            errores.append(f"{clave}: resultado={d['resultado']!r}")
    return errores


def vigente(dec: dict, clave: str, huella: str, campo: str) -> dict | None:
    """La decisión de `clave` si es de esto mismo (misma huella) y está tomada (`campo` no vacío)."""
    d = dec.get(clave)
    return d if d and d.get("huella") == huella and d.get(campo) is not None else None


def resume(plan: dict, revision: dict, leidas: dict[int, dict]) -> dict:
    """Cuentas por plano y página a partir de las decisiones vigentes; lo demás cuenta como no revisado."""
    dec = revision["decisiones"]
    salida = {"semilla": plan["semilla"], "planos": {}, "controles": {}}
    for doc in POSITIVOS:
        r = leidas[doc]
        lecturas_doc = [i for i in plan["items"] if i["doc"] == doc and i["tipo"] == "lectura"]
        tomada = {i["id"]: vigente(dec, i["id"], i["huella"], "numero") for i in lecturas_doc}
        paginas = {}
        for p in sorted({x["p"] for x in r["lecturas"]} | {i["p"] for i in plan["items"] if i["doc"] == doc}):
            items = [i for i in lecturas_doc if i["p"] == p]
            numero = Counter((tomada[i["id"]] or {}).get("numero") or "sin revisar" for i in items)
            ubicacion = Counter((tomada[i["id"]] or {}).get("ubicacion") or "sin revisar" for i in items)
            ambas = sum(bool(tomada[i["id"]]) and tomada[i["id"]]["numero"] == "bien"
                        and tomada[i["id"]]["ubicacion"] == "bien" for i in items)
            paginas[p] = {"ofrecidas": sum(x["p"] == p for x in r["lecturas"]), "muestra": len(items),
                          "numero": dict(numero), "ubicacion": dict(ubicacion), "ambas_bien": ambas}
        contraste = plan["contraste"].get(str(doc), {"cotas": 0, "no_encontradas": [], "huellas": {}})
        decision_cota = {c: vigente(dec, f"C{doc}-{c}", contraste["huellas"][c], "resultado") for c in contraste["no_encontradas"]}
        resultado = {c: d["resultado"] if d else "sin revisar" for c, d in decision_cota.items()}
        huella_omisiones = plan["huella_omisiones"].get(str(doc))
        omisiones = [o for o in revision["omisiones"] if o["doc"] == doc and huella_omisiones and o.get("huella") == huella_omisiones]
        omisiones += [{"doc": doc, "cota": c, "origen": "informe", **{k: v for k, v in d.items() if k not in ("resultado", "huella")}}
                      for c, d in decision_cota.items() if d and d["resultado"] == "omision_confirmada"]
        fallos = [{"id": i["id"], "p": i["p"], "lee": i["t"], **{k: v for k, v in d.items() if k != "huella"}}
                  for i in lecturas_doc if (d := tomada[i["id"]])
                  and (d["numero"] in ("mal", "dudoso") or d["ubicacion"] in ("mal", "dudoso"))]
        salida["planos"][str(doc)] = {"plano": POSITIVOS[doc], "nombre": r["nombre"], "paginas": paginas,
                                      "cotas_informes": contraste["cotas"], "contraste": resultado,
                                      "omisiones_confirmadas": omisiones, "fallos": fallos}
    for doc in (*NEGATIVOS, *FORZADOS):
        items = [i for i in plan["items"] if i["doc"] == doc]
        tomada = {i["id"]: vigente(dec, i["id"], i["huella"], "resultado") for i in items}
        revisadas = [i for i in items if tomada[i["id"]]]
        total = plan["detecciones_negativas"][str(doc)]
        salida["controles"][str(doc)] = {
            "plano": {**NEGATIVOS, **FORZADOS}[doc], "forzado": doc in FORZADOS, "detecciones": total,
            "seleccionadas": len(items), "revisadas": len(revisadas),
            "resultado": dict(Counter(tomada[i["id"]]["resultado"] for i in revisadas)),
            "pendientes": total - len(revisadas),  # sin seleccionar y seleccionadas sin decisión
            "detalle": [{"id": i["id"], "p": i["p"], "lee": i["t"], "via": i["via"],
                         **{k: v for k, v in tomada[i["id"]].items() if k != "huella"}} for i in revisadas]}
    return salida


def pdf_cambiado(plan: dict, firmas: dict[int, dict | None]) -> list[int]:
    """Planos cuyo PDF ya no es el de la muestra (o no se puede comprobar ahora)."""
    return [d for d, f in firmas.items() if f is None or f["sha256"] != plan["entrada"][str(d)]["pdf"]]


def informe(carpeta: Path) -> None:
    plan = json.loads((carpeta / "muestra.json").read_text(encoding="utf-8"))
    revision = json.loads((carpeta / "revision.json").read_text(encoding="utf-8"))
    errores = valida(plan, revision)
    if errores:
        sys.exit("Decisiones con valores no previstos:\n  " + "\n  ".join(errores))
    leidas = lecturas(carpeta)
    cambiadas = lecturas_cambiadas(plan, leidas)
    if cambiadas:
        sys.exit(f"Las lecturas de {cambiadas} cambiaron después de elegir la muestra: repetir «muestra» y la revisión")
    pdfs = pdf_cambiado(plan, {d: firma_actual(d)[0] for d in leidas})
    if pdfs:
        sys.exit(f"El PDF de {pdfs} no es el de la muestra (o no se puede comprobar): repetir «leer», «muestra» y la revisión")
    resumen = resume(plan, revision, leidas)
    sin_vigencia = [k for k, (h, _) in esperadas(plan).items()
                    if revision["decisiones"].get(k) and revision["decisiones"][k].get("huella") != h]
    if sin_vigencia:
        print(f"AVISO: {len(sin_vigencia)} decisiones no son de estas lecturas y cuentan como sin revisar: "
              f"{sin_vigencia[:10]}… (ejecutar «muestra» para conciliarlas)", flush=True)
    # Evidencia de cada omisión con posición: las del barrido y las del contraste sin candidato del OCR.
    con_sitio = [(o["doc"], o["p"], o["x"], o["y"], o.get("numero") or o.get("cota"))
                 for r in resumen["planos"].values() for o in r["omisiones_confirmadas"] if "x" in o]
    for doc, p, x, y, numero in con_sitio:
        with fitz.open(datos.original(leidas[doc]["ruta"])) as pdf:
            img = recorte(pagina_gris(pdf, p), {"x": x, "y": y, "w": .01, "h": .006}, (0, 140, 255))
            guarda_png(carpeta / "recortes" / f"omision-{doc}-p{p}-{numero}.png", img)
    (carpeta / "informe.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    for doc, r in resumen["planos"].items():
        for p, x in r["paginas"].items():
            print(f"{r['plano']} p{p}: {x['ofrecidas']} ofrecidas; muestra {x['muestra']}: número {x['numero']},"
                  f" ubicación {x['ubicacion']}, las dos bien {x['ambas_bien']}")
        print(f"  contraste con {r['cotas_informes']} cotas de informes: {Counter(r['contraste'].values())};"
              f" omisiones confirmadas {len(r['omisiones_confirmadas'])}")
    for doc, r in resumen["controles"].items():
        print(f"control {r['plano']}: {r['detecciones']} detecciones, revisadas {r['revisadas']}: {r['resultado']};"
              f" pendientes {r['pendientes']}")


# ---------------------------------------------------------------- principal

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fase", choices=["leer", "muestra", "informe"])
    parser.add_argument("--carpeta", type=Path, default=CARPETA)
    parser.add_argument("--doc", type=int, action="append", help="Solo este plano (se puede repetir)")
    parser.add_argument("--procesos", type=int, default=4)
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()
    if args.fase == "leer":
        # Los más lentos primero, para repartir mejor los procesos.
        orden = [582, 873, 1, 1631, 2003, 2243, *FORZADOS]
        leer(args.carpeta, args.doc or orden, args.procesos)
    elif args.fase == "muestra":
        muestra(args.carpeta, args.semilla)
    else:
        informe(args.carpeta)


if __name__ == "__main__":
    main()
