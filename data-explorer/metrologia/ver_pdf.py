"""
ver_pdf.py - Visualiza las graficas de tolerancia de contorno (PDF) del 3212.

Que son estos ficheros
----------------------
144 PDF repartidos en `PA_1..6.pdf` y `PB_1..6.pdf` dentro de cada carpeta de cavidad.
NO son una representacion de los .csv ni de los .txt: son un dato que no esta en ningun
otro sitio.

La CMM, ademas de medir cotas sueltas (eso es el .csv), recorre el PERFIL INTERIOR de la
pieza y lo compara **contra el contorno teorico**. El resultado de esa comparacion solo
existe aqui:

  * el .csv no tiene ningun bloque de tolerancia de contorno; mide diametros,
    posiciones y planitudes, no perfiles completos;
  * y no se puede recalcular desde los .txt, porque haria falta el contorno NOMINAL,
    que no esta en ningun fichero que tengamos (ojo: el `3212_CONTORN.igs` es el
    contorno ESCANEADO, no el nominal).

Los 12 PDF de una cavidad son **2 perfiles x 6 contornos medidos**:

    PERFIL_A  (PA_1..6)  contornos 21, 31, 22, 32, 23, 33   alturas Y ~ 19-30 mm
    PERFIL_B  (PB_1..6)  contornos 25, 35, 26, 36, 27, 37   alturas Y ~ 12-23 mm

Todos se comparan contra el mismo nominal, `CONTORN (10)`, con tolerancia +-0,025 mm.

De cada PDF se extraen 6 numeros (mas la hora) y se incrusta la pagina renderizada,
para poder juzgar la grafica original al lado del dato.

Que genera
----------
    out/pdf-3212.html            <- el arbol
    out/pdf/intern.01-c13-PA_1.html
    out/pdf/img/*.png            <- la pagina del PDF renderizada
    out/pdf/evo-c13.html         <- evolucion del contorno entre muestreos

Uso
---
    python data-explorer/metrologia/ver_pdf.py
    python data-explorer/metrologia/ver_pdf.py --muestreo 01 --cavidad c13
    python data-explorer/metrologia/ver_pdf.py --zoom 2.0        # render mas grande (y mas pesado)
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import webbrowser
from pathlib import Path

import fitz  # PyMuPDF
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

# --------------------------------------------------------------------------------------
# Rutas absolutas a los datos (no estan en este repo)
# --------------------------------------------------------------------------------------

RAIZ = Path(
    r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos"
    r"\11. inteplast\Exemples\3212 Pump Housing\4- Metrologia"
)
SALIDA = Path(__file__).resolve().parent.parent / "out"   # data-explorer/out, compartida

# Lote y contexto de cada muestreo. De la hoja HISTORY de los .xls.
# Las fechas se dejan fuera de la interfaz: los muestreos ya se ordenan por numero.
MUESTREOS = {
    "01": ("315252", "primer muestreo completo"),
    "03": ("315346", "despues de la correccion de molde n1"),
    "05": ("315426", "despues de la correccion de molde n2"),
    "08": ("08/01/2025", "verificacion posterior"),
}

VERDE, ROJO, GRIS, AZUL = "#2a9d5c", "#d1495b", "#9aa0a6", "#3d6fb4"

# --------------------------------------------------------------------------------------
# Descubrimiento
# --------------------------------------------------------------------------------------


def num_muestreo(ruta: Path) -> str:
    for parte in ruta.parts:
        m = re.search(r"intern[.\s]*(\d+)", parte, re.IGNORECASE)
        if m:
            return m.group(1).zfill(2)
    return "??"


def num_cavidad(ruta: Path) -> str | None:
    """Los PA/PB siempre viven dentro de la carpeta de su cavidad: c13/, C13/..."""
    for texto in (ruta.parent.name, ruta.stem):
        m = re.search(r"[cC](?:av)?[._\s]?(\d{2})", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
        m = re.search(r"^(\d{2})[_\s]", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
    return None


def descubrir(raiz: Path) -> list[dict]:
    ficheros = []
    for ruta in raiz.rglob("*.pdf"):
        m = re.match(r"^P([AB])_(\d+)$", ruta.stem)
        if not m:
            continue
        cavidad = num_cavidad(ruta)
        if cavidad is None:
            print(f"  [aviso] no se deduce la cavidad, se salta: {ruta}")
            continue
        ficheros.append(
            {
                "ruta": ruta,
                "muestreo": num_muestreo(ruta),
                "cavidad": cavidad,
                "perfil": m.group(1),
                "indice": int(m.group(2)),
                "rel": ruta.relative_to(raiz.parent).as_posix(),
            }
        )
    return sorted(ficheros, key=lambda f: (f["muestreo"], f["cavidad"], f["perfil"], f["indice"]))


# --------------------------------------------------------------------------------------
# Extraccion
# --------------------------------------------------------------------------------------


def filas_por_y(pagina, tolerancia: float = 3.0) -> list[str]:
    """Reconstruye las filas visuales de la tabla agrupando las palabras por su
    coordenada Y. Hace falta porque la tabla del PDF son celdas independientes: los
    bloques de texto de PyMuPDF no las agrupan por fila."""
    palabras = sorted(pagina.get_text("words"), key=lambda w: (w[1], w[0]))
    filas, actual, y_ref = [], [], None
    for x0, y0, _, _, palabra, *_ in palabras:
        if y_ref is None or abs(y0 - y_ref) <= tolerancia:
            actual.append((x0, palabra))
            y_ref = y0 if y_ref is None else y_ref
        else:
            filas.append(sorted(actual))
            actual, y_ref = [(x0, palabra)], y0
    if actual:
        filas.append(sorted(actual))
    return [" ".join(p for _, p in f) for f in filas]


def a_float(texto: str) -> float | None:
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def leer_pdf(ruta: Path, destino_img: Path, zoom: float, nombre_base: str) -> dict:
    """Saca los 6 numeros de la tabla y renderiza la pagina a PNG.

    `nombre_base` tiene que identificar muestreo + cavidad + elemento: los 144 PDF se
    llaman solo PA_1..PB_6 y, si el nombre del PNG no lleva el muestreo, los de un
    muestreo sobrescriben a los de otro y cada pagina acaba mostrando la grafica de
    otra tanda.
    """
    doc = fitz.open(ruta)
    pagina = doc[0]
    filas = filas_por_y(pagina)
    datos: dict = {"fichero": ruta.name}

    for fila in filas:
        # 'Contorno (21) -0.025 -0.242 -0.217'
        m = re.match(r"Contorno \((\d+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", fila)
        if m:
            datos.update(contorno=m.group(1), tol_inf=a_float(m.group(2)),
                         desv_inf=a_float(m.group(3)), infr_inf=a_float(m.group(4)))
        # 'CONTORN (10) 0.025 -0.038 0.000'
        m = re.match(r"CONTORN \((\d+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", fila)
        if m:
            datos.update(nominal=m.group(1), tol_sup=a_float(m.group(2)),
                         desv_sup=a_float(m.group(3)), infr_sup=a_float(m.group(4)))
        m = re.match(r"YZ\(X\)\s+(-?[\d.]+)", fila)
        if m:
            datos["media"] = a_float(m.group(1))
        m = re.match(r"Tolerancia:([\d.]+)", fila)
        if m:
            datos["banda"] = a_float(m.group(1))
        m = re.search(r"(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2})", fila)
        if m:
            datos["hora"] = m.group(2)
        if fila.startswith("PERFIL_"):
            datos["perfil_nombre"] = fila.strip()

    texto = pagina.get_text()
    m = re.search(r"LD=(-?[\d.]+)", texto)
    datos["ld"] = a_float(m.group(1)) if m else None

    nombre_png = re.sub(r"[^A-Za-z0-9._-]", "_", f"{nombre_base}.png")
    pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    pix.save(destino_img / nombre_png)
    datos["png"] = nombre_png
    doc.close()
    return datos


def hay_infraccion(d: dict) -> bool:
    return bool(d.get("infr_inf")) or bool(d.get("infr_sup"))


def peor_infraccion(d: dict) -> float:
    return max(abs(d.get("infr_inf") or 0.0), abs(d.get("infr_sup") or 0.0))


# --------------------------------------------------------------------------------------
# Graficos de comparativa
# --------------------------------------------------------------------------------------


def fig_evolucion(por_elemento: dict[str, dict[str, dict]]) -> go.Figure:
    """Peor infraccion de tolerancia de cada elemento a lo largo de los muestreos."""
    fig = go.Figure()
    for elemento in sorted(por_elemento):
        serie = por_elemento[elemento]
        muestreos = sorted(serie)
        fig.add_trace(
            go.Scatter(
                x=[f"intern.{m}" for m in muestreos],
                y=[peor_infraccion(serie[m]) for m in muestreos],
                mode="lines+markers", name=elemento,
                hovertemplate="%{y:.3f} mm fuera<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(
        height=620, margin=dict(l=70, r=40, t=20, b=50),
        yaxis_title="cuanto se sale de la tolerancia (mm)",
        xaxis_title="", plot_bgcolor="white",
        legend=dict(font=dict(size=11, family="monospace")),
    )
    fig.add_hline(y=0, line=dict(color=VERDE, width=2, dash="dot"),
                  annotation_text="dentro de tolerancia", annotation_position="right")
    return fig


def fig_desviaciones(por_elemento: dict[str, dict[str, dict]]) -> go.Figure:
    """Desviacion maxima inferior y superior contra la banda de tolerancia."""
    fig = go.Figure()
    elementos = sorted(por_elemento)
    muestreos = sorted({m for s in por_elemento.values() for m in s})

    for muestreo in muestreos:
        fig.add_trace(
            go.Scatter(
                x=[por_elemento[e].get(muestreo, {}).get("desv_inf") for e in elementos],
                y=elementos, mode="markers", name=f"intern.{muestreo}",
                marker=dict(size=9, symbol="triangle-left"),
                hovertemplate="desviacion inferior %{x:.3f} mm<extra>%{y}</extra>",
            )
        )
    banda = 0.025
    fig.add_vrect(x0=-banda, x1=banda, fillcolor="rgba(42,157,92,0.12)", line_width=0)
    fig.update_layout(
        height=max(420, 34 * len(elementos)), margin=dict(l=120, r=40, t=20, b=50),
        xaxis_title="desviacion maxima inferior (mm)   ·   la franja verde es la tolerancia",
        plot_bgcolor="white", legend=dict(orientation="h", y=1.02, x=0),
    )
    return fig


# --------------------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------------------

ESTILO = """
:root { --linea: #e3e6ea; --tinta: #1a1a1a; --suave: #667; --azul: #3d6fb4; --rojo: #d1495b;
        --verde: #2a9d5c; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 0 auto; max-width: 1180px;
       padding: 28px 24px 80px; color: var(--tinta); background: #fff; line-height: 1.55; }
h1 { font-size: 27px; margin: 0 0 6px; letter-spacing: -0.02em; }
h2 { font-size: 19px; margin: 40px 0 12px; }
h3 { font-size: 15px; margin: 26px 0 6px; }
p { margin: 10px 0; }
code { background: #f2f4f7; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
.sub { color: var(--suave); font-size: 14px; margin-bottom: 22px; }
.ruta { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: var(--suave); }
.intro { background: #f7f9fc; border: 1px solid var(--linea); border-radius: 10px;
         padding: 4px 22px 18px; margin: 22px 0 30px; }
.intro h3 { font-size: 15px; color: var(--azul); margin: 20px 0 4px; }
.intro p { font-size: 14.5px; margin: 4px 0; }
.leyenda { border-left: 3px solid var(--azul); background: #f7f9fc; padding: 12px 16px;
           margin: 18px 0; font-size: 14px; border-radius: 0 6px 6px 0; }

.arbol { border: 1px solid var(--linea); border-radius: 10px; overflow: hidden; }
.arbol details { border-bottom: 1px solid var(--linea); }
.arbol details:last-child { border-bottom: 0; }
.arbol summary { cursor: pointer; padding: 11px 16px; font-weight: 600; font-size: 15px;
                 background: #fafbfc; user-select: none; list-style: none; display: flex;
                 align-items: center; gap: 10px; }
.arbol summary::-webkit-details-marker { display: none; }
.arbol summary::before { content: ""; width: 0; height: 0; flex: none;
                         border-left: 5px solid var(--suave);
                         border-top: 4px solid transparent;
                         border-bottom: 4px solid transparent;
                         transition: transform .12s; }
.arbol details[open] > summary::before { transform: rotate(90deg); }
.arbol summary:hover { background: #f2f5f9; }
.arbol .meta { font-weight: 400; color: var(--suave); font-size: 13px; margin-left: auto;
               text-align: right; }
.arbol details details > summary { padding-left: 40px; font-size: 14px; background: #fff; }
.hojas { padding: 4px 0 8px; }
a.hoja { display: flex; align-items: center; gap: 10px; padding: 7px 16px 7px 64px;
         text-decoration: none; color: var(--tinta); font-size: 14px;
         border-left: 3px solid transparent; }
a.hoja:hover { background: #f2f5f9; border-left-color: var(--azul); }
a.hoja .fam { font-weight: 600; min-width: 92px; font-family: ui-monospace, monospace; }
a.hoja .nom { color: var(--suave); }
a.hoja .num { margin-left: auto; font-size: 12.5px; font-family: ui-monospace, monospace; }
.mal { color: var(--rojo); font-weight: 600; }
.bien { color: var(--verde); }

.volver { display: inline-block; margin-bottom: 18px; font-size: 14px; color: var(--azul);
          text-decoration: none; }
.volver:hover { text-decoration: underline; }
.tarjeta { border: 1px solid var(--linea); border-radius: 10px; padding: 14px 18px;
           margin: 16px 0; font-size: 14px; background: #fafbfc; }
img.hoja-pdf { width: 100%; border: 1px solid var(--linea); border-radius: 8px; margin: 8px 0; }
table.datos { border-collapse: collapse; font-size: 14px; margin: 16px 0; width: 100%; }
table.datos th, table.datos td { border: 1px solid var(--linea); padding: 7px 12px;
                                 text-align: right; }
table.datos th { background: #f2f4f7; text-align: left; font-weight: 600; }
table.datos td.et { text-align: left; }

/* barra de tolerancia en CSS: sin javascript */
.barra { position: relative; height: 54px; margin: 22px 0 34px; }
.barra .escala { position: absolute; top: 22px; left: 0; right: 0; height: 8px;
                 background: #eef0f3; border-radius: 4px; }
.barra .dentro { position: absolute; top: 22px; height: 8px; background: rgba(42,157,92,.35);
                 border-left: 2px solid var(--verde); border-right: 2px solid var(--verde); }
.barra .marca { position: absolute; top: 12px; width: 2px; height: 28px; background: var(--rojo); }
.barra .marca.ok { background: var(--verde); }
.barra .et { position: absolute; top: 0; font-size: 11px; color: var(--suave);
             transform: translateX(-50%); white-space: nowrap; }
.barra .pie { position: absolute; top: 34px; font-size: 11px; color: var(--suave);
              transform: translateX(-50%); }

details.info { border: 1px solid var(--linea); border-radius: 10px; margin: 18px 0 26px;
               background: #fafbfc; }
details.info > summary { cursor: pointer; padding: 10px 16px 10px 34px; font-size: 14px;
               font-weight: 600; color: var(--azul); user-select: none; }
details.info > summary::marker { color: var(--suave); font-size: 12px; }
details.info > summary:hover { background: #f2f5f9; border-radius: 10px; }
details.info .info-cuerpo { padding: 0 20px 14px; border-top: 1px solid var(--linea);
               background: #fff; border-radius: 0 0 10px 10px; }
details.info .info-cuerpo p { font-size: 14px; margin: 10px 0; }
"""

INTRO = """
<details class='info'><summary>M&aacute;s informaci&oacute;n</summary><div class='info-cuerpo'>
<p>La maquina, ademas de medir cotas sueltas, <b>recorre el perfil interior de la pieza y lo
compara contra el contorno teorico</b>. Estas graficas son esa comparacion, y <b>ese dato no esta
en ningun otro fichero</b>: los <code>.csv</code> no miden perfiles completos, y desde las nubes
de puntos no se puede recalcular porque el contorno nominal no lo tenemos.</p>
<p><b>12 graficas por cavidad</b>: <b>PERFIL_A</b> (<code>PA_1</code>&ndash;<code>PA_6</code>)
recorre la zona alta del interior y <b>PERFIL_B</b> (<code>PB_1</code>&ndash;<code>PB_6</code>) la
baja; los seis de cada uno son recorridos distintos de esa misma zona.</p>
<p><b>Como se lee:</b> la linea es <b>cuanto se aleja la pieza real del perfil teorico</b>. La
tolerancia es <b>&plusmn;0,025 mm</b>: dentro de la banda, bien. De cada grafica se sacan cuatro
numeros &mdash; la <b>desviacion maxima</b> (lo mas lejos que llego, por dentro y por fuera) y la
<b>infraccion de tolerancia</b> (cuanto se paso del limite; si es <code>0,000</code>, no se
paso).</p>
</div></details>
"""


def pagina(titulo: str, cuerpo: str, con_plotly: bool = False, nivel: str = "..") -> str:
    plotly = f"<script src='{nivel}/vendor/plotly.min.js'></script>" if con_plotly else ""
    return (
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(titulo)}</title><style>{ESTILO}</style>{plotly}</head>"
        f"<body>{cuerpo}</body></html>"
    )


def grafico(fig: go.Figure, div_id: str) -> str:
    alto = fig.layout.height or 600
    spec = fig.to_json().replace("</", r"<\/")
    return (
        f"<div id='{div_id}' style='height:{alto}px'></div>"
        f"<script type='application/json' id='spec-{div_id}'>{spec}</script>"
        f"<script>(function(){{var s=JSON.parse(document.getElementById('spec-{div_id}').textContent);"
        f"Plotly.newPlot('{div_id}',s.data,s.layout,{{displaylogo:false,responsive:true}});}})();</script>"
    )


def barra_tolerancia(d: dict) -> str:
    """Dibuja en CSS donde caen las desviaciones respecto a la banda de tolerancia."""
    tol = d.get("tol_sup") or 0.025
    escala = max(4 * tol, abs(d.get("desv_inf") or 0), abs(d.get("desv_sup") or 0)) * 1.15

    def pos(valor: float) -> float:
        return 50 + 50 * valor / escala

    partes = [
        "<div class='barra'><div class='escala'></div>",
        f"<div class='dentro' style='left:{pos(-tol):.1f}%;width:{pos(tol)-pos(-tol):.1f}%'></div>",
        f"<div class='et' style='left:{pos(-tol):.1f}%'>-{tol}</div>",
        f"<div class='et' style='left:{pos(tol):.1f}%'>+{tol}</div>",
    ]
    for clave, etiqueta in (("desv_inf", "max. inferior"), ("desv_sup", "max. superior")):
        valor = d.get(clave)
        if valor is None:
            continue
        dentro = abs(valor) <= tol
        partes.append(
            f"<div class='marca{' ok' if dentro else ''}' style='left:{pos(valor):.1f}%'></div>"
            f"<div class='pie' style='left:{pos(valor):.1f}%'>{valor:+.3f}</div>"
        )
    partes.append("</div>")
    return "".join(partes)


def tabla_datos(d: dict) -> str:
    def celda(valor, mal=False):
        if valor is None:
            return "<td>-</td>"
        clase = " class='mal'" if mal and valor else ""
        return f"<td><span{clase}>{valor:+.3f}</span></td>" if isinstance(valor, float) else f"<td>{valor}</td>"

    return (
        "<table class='datos'>"
        "<tr><th>Que se compara</th><td class='et'>"
        f"Contorno medido <b>({d.get('contorno', '?')})</b> contra el nominal "
        f"<b>CONTORN ({d.get('nominal', '?')})</b></td></tr>"
        f"<tr><th>Tolerancia</th><td class='et'>&plusmn;{d.get('tol_sup', '?')} mm "
        f"(banda total {d.get('banda', '?')})</td></tr>"
        "<tr><th>Desviacion maxima inferior</th>" + celda(d.get("desv_inf")) + "</tr>"
        "<tr><th>Desviacion maxima superior</th>" + celda(d.get("desv_sup")) + "</tr>"
        "<tr><th>Se paso del limite por abajo</th>" + celda(d.get("infr_inf"), True) + "</tr>"
        "<tr><th>Se paso del limite por arriba</th>" + celda(d.get("infr_sup"), True) + "</tr>"
        f"<tr><th>Desviacion media</th><td>{d.get('media', '-')}</td></tr>"
        f"<tr><th>Hora de la medicion</th><td>{d.get('hora', '-')}</td></tr>"
        "</table>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", type=Path, default=RAIZ, help="carpeta 4- Metrologia")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de salida")
    parser.add_argument("--zoom", type=float, default=1.5, help="resolucion del render (1.5 ~ 176 KB)")
    parser.add_argument("--muestreo", help="ver solo un muestreo, p.ej. 01")
    parser.add_argument("--cavidad", help="ver solo una cavidad, p.ej. c13")
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()

    ficheros = descubrir(args.raiz)
    if args.muestreo:
        ficheros = [f for f in ficheros if f["muestreo"] == args.muestreo.zfill(2)]
    if args.cavidad:
        ficheros = [f for f in ficheros if f["cavidad"] == args.cavidad.lower()]
    if not ficheros:
        sys.exit("Ningun PDF PA/PB coincide con el filtro")
    print(f"{len(ficheros)} PDF de contorno")

    destino = args.salida / "pdf"
    imagenes = destino / "img"
    imagenes.mkdir(parents=True, exist_ok=True)
    vendor = args.salida / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")

    arbol: dict[str, dict[str, list[str]]] = {}
    # cavidad -> elemento (PA_1...) -> muestreo -> datos
    por_cavidad: dict[str, dict[str, dict[str, dict]]] = {}

    for fichero in ficheros:
        elemento = f"P{fichero['perfil']}_{fichero['indice']}"
        clave = f"intern.{fichero['muestreo']}-{fichero['cavidad']}-{elemento}"
        datos = leer_pdf(fichero["ruta"], imagenes, args.zoom, clave)
        por_cavidad.setdefault(fichero["cavidad"], {}).setdefault(elemento, {})[
            fichero["muestreo"]
        ] = datos

        mal = hay_infraccion(datos)
        print(f"  intern.{fichero['muestreo']} {fichero['cavidad']} {elemento:5s} "
              f"contorno {datos.get('contorno', '??'):>3s}  "
              f"desv {datos.get('desv_inf', 0):+.3f}/{datos.get('desv_sup', 0):+.3f}  "
              f"{'FUERA ' + format(peor_infraccion(datos), '.3f') if mal else 'ok'}")

        nombre = f"{clave}.html"
        cuerpo = (
            "<a class='volver' href='../pdf-3212.html'>&larr; volver al indice</a>"
            f"<h1>{html.escape(fichero['ruta'].name)}</h1>"
            f"<div class='ruta'>{html.escape(fichero['rel'])}</div>"
            f"<div class='tarjeta'><b>{datos.get('perfil_nombre', 'PERFIL_?')}</b>, "
            f"recorrido {fichero['indice']} de 6 &nbsp;&middot;&nbsp; muestreo "
            f"<b>intern.{fichero['muestreo']}</b> (lote "
            f"{MUESTREOS.get(fichero['muestreo'], ('?',))[0]}) &nbsp;&middot;&nbsp; cavidad "
            f"<b>{fichero['cavidad']}</b><br>"
            + (f"<span class='mal'>Se sale {peor_infraccion(datos):.3f} mm de la tolerancia</span>"
               if mal else "<span class='bien'>Dentro de tolerancia</span>")
            + "</div>"
            + barra_tolerancia(datos)
            + tabla_datos(datos)
            + "<h2>La grafica original</h2>"
            "<div class='leyenda'>La pagina del PDF tal cual. La linea es la desviacion a lo "
            "largo del recorrido; las dos lineas rectas de arriba y abajo son la banda de "
            "tolerancia.</div>"
            f"<img class='hoja-pdf' src='img/{datos['png']}' alt='grafica de contorno'>"
        )
        (destino / nombre).write_text(pagina(fichero["ruta"].name, cuerpo), encoding="utf-8")

        arbol.setdefault(fichero["muestreo"], {}).setdefault(fichero["cavidad"], []).append(
            f"<a class='hoja' href='pdf/{nombre}'>"
            f"<span class='fam'>{elemento}</span>"
            f"<span class='nom'>contorno {datos.get('contorno', '??')} "
            f"&middot; {datos.get('perfil_nombre', '')}</span>"
            f"<span class='num'>"
            + (f"<span class='mal'>fuera {peor_infraccion(datos):.3f}</span>"
               if mal else "<span class='bien'>ok</span>")
            + "</span></a>"
        )

    # --- una pagina de evolucion por cavidad -------------------------------------------
    hojas_evo: list[str] = []
    for cavidad, elementos in sorted(por_cavidad.items()):
        con_varios = {e: s for e, s in elementos.items() if len(s) > 1}
        if not con_varios:
            continue
        nombre = f"evo-{cavidad}.html"
        cuerpo = (
            "<a class='volver' href='../pdf-3212.html'>&larr; volver al indice</a>"
            f"<h1>{cavidad} &middot; evolucion del contorno</h1>"
            f"<div class='sub'>{len(con_varios)} recorridos seguidos a lo largo de "
            f"{len({m for s in con_varios.values() for m in s})} muestreos</div>"
            "<div class='leyenda'>Cada linea es uno de los 12 recorridos del perfil. El eje "
            "vertical es <b>cuanto se sale de la tolerancia</b>: <b>cero es estar dentro</b>. "
            "Si las lineas bajan hacia cero de un muestreo al siguiente, el retoque del molde "
            "acerco el perfil al teorico.</div>"
            + grafico(fig_evolucion(con_varios), "g1")
            + "<h2>Desviacion maxima inferior, recorrido a recorrido</h2>"
            "<div class='leyenda'>Lo mas lejos que se aleja la pieza del perfil teorico por "
            "dentro, en mm. La franja verde es la tolerancia.</div>"
            + grafico(fig_desviaciones(con_varios), "g2")
        )
        (destino / nombre).write_text(pagina(f"{cavidad} - contorno", cuerpo, True), encoding="utf-8")
        hojas_evo.append(
            f"<a class='hoja' href='pdf/{nombre}' style='padding-left:40px'>"
            f"<span class='fam'>{cavidad}</span>"
            f"<span class='nom'>evolucion de los {len(con_varios)} recorridos</span>"
            f"<span class='num'>&nbsp;</span></a>"
        )

    # --- el arbol ----------------------------------------------------------------------
    ramas = []
    for muestreo in sorted(arbol):
        lote, nota = MUESTREOS.get(muestreo, ("", ""))
        cavidades = []
        for cavidad in sorted(arbol[muestreo]):
            enlaces = arbol[muestreo][cavidad]
            malas = sum(1 for e in enlaces if "fuera" in e)
            cavidades.append(
                f"<details><summary>{cavidad}"
                f"<span class='meta'>{len(enlaces)} graficas &middot; "
                + (f"<span class='mal'>{malas} fuera de tolerancia</span>" if malas
                   else "<span class='bien'>todas dentro</span>")
                + f"</span></summary><div class='hojas'>{''.join(enlaces)}</div></details>"
            )
        ramas.append(
            f"<details><summary>intern.{muestreo}"
            f"<span class='meta'>lote {lote}" + (f" &middot; <i>{nota}</i>" if nota else "")
            + f"</span></summary>{''.join(cavidades)}</details>"
        )
    if hojas_evo:
        ramas.append(
            "<details><summary>Comparar los muestreos entre si (evolucion)"
            f"<span class='meta'>{len(hojas_evo)} paginas &middot; una cavidad cada una</span>"
            f"</summary><div class='hojas'>{''.join(hojas_evo)}</div></details>"
        )

    indice = (
        "<a class='volver' href='index.html'>&larr; volver al inicio</a>"
        "<h1>3212 Pump Housing &middot; tolerancia de contorno</h1>"
        "<div class='sub'>El perfil interior de la pieza comparado contra el teorico. "
        "Abre una carpeta y elige una grafica.</div>"
        f"<div class='ruta'>{html.escape(str(args.raiz))}</div>"
        + INTRO
        + "<h2>Ficheros</h2>"
        f"<div class='arbol'>{''.join(ramas)}</div>"
    )
    fichero_indice = args.salida / "pdf-3212.html"
    fichero_indice.write_text(pagina("3212 - tolerancia de contorno", indice, nivel="."),
                              encoding="utf-8")

    paginas = len(list(destino.glob("*.html")))
    peso = sum(f.stat().st_size for f in imagenes.glob("*.png")) / 1e6
    print(f"\nIndice: {fichero_indice}")
    print(f"{paginas} paginas en {destino}  ·  {peso:.0f} MB de imagenes")
    if not args.no_abrir:
        webbrowser.open(fichero_indice.as_uri())


if __name__ == "__main__":
    main()
