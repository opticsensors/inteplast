"""
ver_txt.py - Visualiza las nubes de puntos crudas de la CMM del 3212.

Que son estos ficheros
----------------------
Son la MISMA medicion que los `.csv`, pero sin evaluar: las coordenadas XYZ en bruto
que palpo o escaneo la maquina. Tres columnas en ancho fijo con signo, sin cabecera,
en milimetros:

    -0000.0113 +0000.0209 +0027.7380
    +0000.0392 +0000.0203 +0027.7390
         X          Y          Z

En el 3212 hay TRES familias distintas, y confundirlas es facil porque las tres son
"un .txt con puntos":

  1. PERFIL DE CAVIDAD   `3212_Cav13.txt`, `3212_C13_.txt`, `13_3212_Cav_.txt`...
     ~17.656 puntos. Es LA PIEZA ENTERA escaneada.

  2. `3212_PUNTS.txt`    ~12.828 puntos, solo entre Y=12 y Y=28.
     Es SOLO EL PERFIL INTERIOR, la zona que se controla contra tolerancia de contorno
     (la de las graficas PA/PB en PDF).

  3. `3212_PUNTS_NOUS.txt`  150 puntos exactos = 6 contornos de 25 puntos a 6 alturas.
     No son medidas: son los puntos OBJETIVO que INTEPLAST le pasa al proveedor del
     molde para que retoque. Hay uno DISTINTO por cavidad y por muestreo.

Los `.igs` y los `.dxf` de las mismas carpetas NO aportan nada: son estos mismos puntos
otra vez (el .igs = PUNTS.txt con un offset en Z, el .dxf = el perfil de cavidad).

Que genera
----------
Un INDICE con arbol de carpetas (`out/txt-3212.html`) y una PAGINA POR FICHERO en
`out/txt/`. Cada pagina se abre desde el arbol; no hay scroll infinito.

Uso
---
    python scripts/ver_txt.py                     # genera todo y abre el arbol
    python scripts/ver_txt.py --max-puntos 12000  # mas detalle, paginas mas pesadas
    python scripts/ver_txt.py --familia nous      # solo los puntos objetivo
    python scripts/ver_txt.py --muestreo 01 --cavidad c13
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

# --------------------------------------------------------------------------------------
# Rutas absolutas a los datos (no estan en este repo)
# --------------------------------------------------------------------------------------

RAIZ = Path(
    r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos"
    r"\11. inteplast\Exemples\3212 Pump Housing\4- Metrologia"
)
SALIDA = Path(__file__).resolve().parent / "out"

EN_LA_NUBE = 0x400000        # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS (OneDrive Files On-Demand)

FAMILIAS = {
    "perfil": ("Perfil de cavidad", "la pieza entera escaneada"),
    "punts": ("PUNTS", "solo el perfil interior, la zona con tolerancia de contorno"),
    "nous": ("PUNTS_NOUS", "los puntos OBJETIVO que se le pasan al fabricante del molde"),
}
ORDEN_FAMILIA = {"perfil": 0, "punts": 1, "nous": 2}

# Lote y contexto de cada muestreo con medicion 3D, de la hoja HISTORY de los .xls.
# -> docs/3212/4-metrologia.md
# Las fechas se dejan fuera de la interfaz a proposito: lo que ordena los muestreos es su
# numero, y lo que importa de cada uno es que paso antes (el retoque de molde).
MUESTREOS = {
    "01": ("315252", "primer muestreo completo"),
    "03": ("315346", "despues de la correccion de molde n1"),
    "05": ("315426", "despues de la correccion de molde n2"),
    "08": ("08/01/2025", "verificacion posterior (este lote se identifica por fecha)"),
}

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
    """La cavidad esta en el nombre del fichero o, si no, en la carpeta padre.

    En intern.05 las carpetas c15/ y c16/ tienen ficheros con el MISMO nombre
    ('3212_Cav_.txt'), asi que la carpeta padre es la unica pista que queda.
    """
    for texto in (ruta.stem, ruta.parent.name):
        m = re.search(r"^(\d{2})[_\s]", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
        m = re.search(r"[cC](?:av)?[._\s]?(\d{2})", texto)
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
    return None


def familia(ruta: Path) -> str:
    nombre = ruta.stem.upper()
    if "PUNTS_NOUS" in nombre:
        return "nous"
    if "PUNTS" in nombre:
        return "punts"
    return "perfil"


def descubrir(raiz: Path) -> list[dict]:
    ficheros = []
    for ruta in raiz.rglob("*.txt"):
        cavidad = num_cavidad(ruta)
        if cavidad is None:
            print(f"  [aviso] no se deduce la cavidad, se salta: {ruta.name}")
            continue
        ficheros.append(
            {
                "ruta": ruta,
                "muestreo": num_muestreo(ruta),
                "cavidad": cavidad,
                "familia": familia(ruta),
                "rel": ruta.relative_to(raiz.parent).as_posix(),
                "en_la_nube": bool(ruta.stat().st_file_attributes & EN_LA_NUBE),
            }
        )
    return sorted(
        ficheros,
        key=lambda f: (f["muestreo"], f["cavidad"], ORDEN_FAMILIA[f["familia"]]),
    )


# --------------------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------------------


def leer_nube(ruta: Path) -> np.ndarray:
    """Devuelve un array (n, 3) de float. El ancho fijo se parsea igual con separador
    de espacios: '+0000.0392' es un float valido tal cual."""
    tabla = pd.read_csv(ruta, sep=r"\s+", header=None, names=["x", "y", "z"], engine="c")
    return tabla[["x", "y", "z"]].to_numpy(dtype=float)


def submuestrear(puntos: np.ndarray, maximo: int) -> np.ndarray:
    """Toma puntos equiespaciados en el ORDEN DE MEDICION (no al azar): asi se conserva
    el recorrido del palpador y la nube sigue pareciendose a si misma."""
    if len(puntos) <= maximo:
        return puntos
    return puntos[np.linspace(0, len(puntos) - 1, maximo).astype(int)]


def niveles_y(puntos: np.ndarray, separacion: float = 0.3) -> list[tuple[float, int]]:
    """Agrupa los puntos por altura Y. Sirve para ver que los PUNTS_NOUS son 6 contornos
    y no una nube suelta. Devuelve [(altura_media, n_puntos), ...]."""
    orden = np.sort(puntos[:, 1])
    grupos, actual = [], [orden[0]]
    for valor in orden[1:]:
        if valor - actual[-1] > separacion:
            grupos.append(actual)
            actual = []
        actual.append(valor)
    grupos.append(actual)
    return [(float(np.mean(g)), len(g)) for g in grupos]


# --------------------------------------------------------------------------------------
# Graficos
# --------------------------------------------------------------------------------------


def fig_nube(puntos: np.ndarray, con_lineas: bool = False) -> go.Figure:
    """Nube 3D interactiva (rotar con el raton), coloreada por altura Y."""
    x, y, z = puntos[:, 0].round(3), puntos[:, 1].round(3), puntos[:, 2].round(3)
    fig = go.Figure(
        go.Scatter3d(
            x=x, y=z, z=y,                      # la Y del fichero es la ALTURA -> eje vertical
            mode="lines+markers" if con_lineas else "markers",
            marker=dict(size=2.2 if con_lineas else 1.3, color=y,
                        colorscale="Viridis", colorbar=dict(title="altura Y<br>(mm)")),
            line=dict(color="rgba(120,120,120,0.45)", width=1),
            hovertemplate="X %{x:.3f}<br>Z %{y:.3f}<br>Y %{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=680, margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(xaxis_title="X (mm)", yaxis_title="Z (mm)",
                   zaxis_title="Y = altura (mm)", aspectmode="data"),
    )
    return fig


def fig_planta(puntos: np.ndarray) -> go.Figure:
    """Vista en planta (X-Z), que es donde se ve el contorno circular de la pieza."""
    x, z, y = puntos[:, 0].round(3), puntos[:, 2].round(3), puntos[:, 1].round(3)
    fig = go.Figure(
        go.Scattergl(
            x=x, y=z, mode="markers",
            marker=dict(size=2.5, color=y, colorscale="Viridis", showscale=True,
                        colorbar=dict(title="altura Y")),
            hovertemplate="X %{x:.3f}<br>Z %{y:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=620, margin=dict(l=60, r=20, t=10, b=50),
        xaxis=dict(title="X (mm)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Z (mm)"), plot_bgcolor="white",
    )
    return fig


def fig_objetivos_superpuestos(grupo: list[tuple[str, np.ndarray]]) -> go.Figure:
    """Los PUNTS_NOUS de la misma cavidad en los distintos muestreos, en planta."""
    fig = go.Figure()
    for muestreo, puntos in grupo:
        fig.add_trace(
            go.Scatter(
                x=puntos[:, 0].round(3), y=puntos[:, 2].round(3),
                mode="markers", name=f"intern.{muestreo}", marker=dict(size=6),
                hovertemplate="X %{x:.3f}<br>Z %{y:.3f}<extra>intern." + muestreo + "</extra>",
            )
        )
    fig.update_layout(
        height=660, margin=dict(l=60, r=20, t=10, b=50),
        xaxis=dict(title="X (mm)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Z (mm)"), plot_bgcolor="white",
    )
    return fig


# --------------------------------------------------------------------------------------
# HTML: un indice con arbol + una pagina por fichero
# --------------------------------------------------------------------------------------

ESTILO = """
:root { --linea: #e3e6ea; --tinta: #1a1a1a; --suave: #667; --azul: #3d6fb4; }
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
.aviso { background: #fff7f7; border-left: 3px solid #d1495b; padding: 10px 16px;
         margin: 16px 0; font-size: 14px; border-radius: 0 6px 6px 0; }

/* arbol */
.arbol { border: 1px solid var(--linea); border-radius: 10px; overflow: hidden; }
.arbol details { border-bottom: 1px solid var(--linea); }
.arbol details:last-child { border-bottom: 0; }
.arbol summary { cursor: pointer; padding: 11px 16px; font-weight: 600; font-size: 15px;
                 background: #fafbfc; user-select: none; list-style: none; display: flex;
                 align-items: center; gap: 10px; }
.arbol summary::-webkit-details-marker { display: none; }
.arbol summary::before { content: "\\25B8"; color: var(--suave); font-size: 12px;
                         transition: transform .12s; }
.arbol details[open] > summary::before { transform: rotate(90deg); }
.arbol summary:hover { background: #f2f5f9; }
.arbol .meta { font-weight: 400; color: var(--suave); font-size: 13px; margin-left: auto;
               text-align: right; }
.arbol details details > summary { padding-left: 40px; font-size: 14px; font-weight: 600;
                                   background: #fff; }
.hojas { padding: 4px 0 8px; }
a.hoja { display: flex; align-items: center; gap: 10px; padding: 7px 16px 7px 64px;
         text-decoration: none; color: var(--tinta); font-size: 14px;
         border-left: 3px solid transparent; }
a.hoja:hover { background: #f2f5f9; border-left-color: var(--azul); }
a.hoja .fam { font-weight: 600; min-width: 96px; }
a.hoja .nom { font-family: ui-monospace, Consolas, monospace; color: var(--suave); }
a.hoja .num { margin-left: auto; color: var(--suave); font-size: 12.5px;
              font-family: ui-monospace, Consolas, monospace; }

/* paginas de resultado */
.volver { display: inline-block; margin-bottom: 18px; font-size: 14px; color: var(--azul);
          text-decoration: none; }
.volver:hover { text-decoration: underline; }
.tarjeta { border: 1px solid var(--linea); border-radius: 10px; padding: 14px 18px;
           margin: 16px 0; font-size: 14px; background: #fafbfc;
           font-family: ui-monospace, Consolas, monospace; }
.leyenda { border-left: 3px solid var(--azul); background: #f7f9fc; padding: 12px 16px;
           margin: 18px 0; font-size: 14px; border-radius: 0 6px 6px 0; }
"""

INTRO = """
<div class='intro'>
<h3>Que estas viendo</h3>
<p>Los <b>puntos que toco la maquina</b>, sin interpretar. Cuando la CMM mide una pieza va
recorriendola y anotando coordenadas; de ahi salen luego los diametros y las planitudes del
informe. Estos ficheros son ese paso anterior: <b>solo X, Y, Z en milimetros</b>.</p>

<h3>Que es un &laquo;muestreo&raquo; y una &laquo;cavidad&raquo;</h3>
<p>Un <b>muestreo</b> es una tanda de piezas sacada del molde y llevada a medir
(<code>intern.01</code>, <code>intern.03</code>&hellip;). Entre uno y otro <b>se retoco el
molde</b>. Una <b>cavidad</b> es cada uno de los huecos del molde: de los 16 que tiene se
controlan cuatro, <b>c13 a c16</b>. Asi que cada carpeta del arbol es <i>una tanda</i> y dentro
esta <i>cada pieza medida</i> &mdash; <b>una sola pieza por cavidad</b>, no un promedio de
varias.</p>

<h3>Las tres familias de fichero</h3>
<p><b>Perfil de cavidad</b> (~17.600 puntos): la pieza entera. Es lo que veras como una nube
con forma reconocible.<br>
<b>PUNTS</b> (~12.800 puntos): solo la <b>parte interior</b> de la pieza, entre las alturas 12 y
28 mm. Es la zona critica, la que se compara contra el contorno teorico en las graficas PA/PB.<br>
<b>PUNTS_NOUS</b> (150 puntos): <b>no son medidas</b>. Son las coordenadas <b>a donde deberia
llegar la pieza</b> despues de retocar el molde, y es lo que INTEPLAST le manda al fabricante
del molde. Son 6 anillos de 25 puntos, a 6 alturas distintas. Hay uno <b>distinto por cavidad y
por muestreo</b>, o sea que <b>cada hueco del molde se retoca por separado</b>.</p>

<h3>Como se mira</h3>
<p>Cada pagina trae la <b>nube en 3D</b> (arrastra con el raton para girarla, rueda para acercar)
y una <b>vista en planta</b> desde arriba, que es donde se aprecia el contorno redondo de la
pieza. El color es siempre la <b>altura</b>.</p>
</div>
"""


def pagina(titulo: str, cuerpo: str, con_plotly: bool = False) -> str:
    plotly = "<script src='../vendor/plotly.min.js'></script>" if con_plotly else ""
    return (
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(titulo)}</title><style>{ESTILO}</style>{plotly}</head>"
        f"<body>{cuerpo}</body></html>"
    )


def grafico(fig: go.Figure, div_id: str) -> str:
    """Un div + el JSON de la figura. Se pinta al cargar: en cada pagina hay 1 o 2."""
    alto = fig.layout.height or 600
    # El '</' escapado evita que un texto de la figura cierre el <script> antes de tiempo.
    spec = fig.to_json().replace("</", r"<\/")
    return (
        f"<div id='{div_id}' style='height:{alto}px'></div>"
        f"<script type='application/json' id='spec-{div_id}'>{spec}</script>"
        f"<script>(function(){{var s=JSON.parse(document.getElementById('spec-{div_id}').textContent);"
        f"Plotly.newPlot('{div_id}',s.data,s.layout,{{displaylogo:false,responsive:true}});}})();</script>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", type=Path, default=RAIZ, help="carpeta 4- Metrologia")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de salida")
    parser.add_argument("--max-puntos", type=int, default=6000,
                        help="puntos por grafico (submuestreo); mas = mas detalle y mas peso")
    parser.add_argument("--familia", choices=sorted(FAMILIAS), help="ver solo una familia")
    parser.add_argument("--muestreo", help="ver solo un muestreo, p.ej. 01")
    parser.add_argument("--cavidad", help="ver solo una cavidad, p.ej. c13")
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()

    ficheros = descubrir(args.raiz)
    if args.familia:
        ficheros = [f for f in ficheros if f["familia"] == args.familia]
    if args.muestreo:
        ficheros = [f for f in ficheros if f["muestreo"] == args.muestreo.zfill(2)]
    if args.cavidad:
        ficheros = [f for f in ficheros if f["cavidad"] == args.cavidad.lower()]
    if not ficheros:
        sys.exit("Ningun .txt coincide con el filtro")

    en_la_nube = [f for f in ficheros if f["en_la_nube"]]
    print(f"{len(ficheros)} ficheros .txt")
    if en_la_nube:
        print(f"  {len(en_la_nube)} estan EN LA NUBE (OneDrive): se descargaran al leerlos.\n")

    destino = args.salida / "txt"
    destino.mkdir(parents=True, exist_ok=True)
    vendor = args.salida / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")

    # muestreo -> cavidad -> [<a>]
    arbol: dict[str, dict[str, list[str]]] = {}
    objetivos: dict[str, list[tuple[str, np.ndarray]]] = {}

    for fichero in ficheros:
        puntos = leer_nube(fichero["ruta"])
        alturas = niveles_y(puntos)
        reducido = submuestrear(puntos, args.max_puntos)
        etiqueta, descripcion = FAMILIAS[fichero["familia"]]

        print(f"  intern.{fichero['muestreo']} {fichero['cavidad']} "
              f"{fichero['familia']:7s} {len(puntos):6d} pts  <- {fichero['ruta'].name}")

        if fichero["familia"] == "nous":
            objetivos.setdefault(fichero["cavidad"], []).append((fichero["muestreo"], puntos))

        resumen_alturas = (
            f"{len(alturas)} niveles de altura: "
            + ", ".join(f"Y={a:.1f} ({n} pts)" for a, n in alturas)
            if len(alturas) <= 8
            else f"{len(alturas)} alturas distintas &rarr; es un escaneo continuo, no por niveles"
        )
        nombre = f"intern.{fichero['muestreo']}-{fichero['cavidad']}-{fichero['familia']}.html"
        cuerpo = (
            "<a class='volver' href='../txt-3212.html'>&larr; volver al indice</a>"
            f"<h1>{html.escape(fichero['ruta'].name)}</h1>"
            f"<div class='ruta'>{html.escape(fichero['rel'])}</div>"
            f"<div class='tarjeta'><b>{etiqueta}</b> &mdash; {descripcion}<br><br>"
            f"muestreo <b>intern.{fichero['muestreo']}</b> "
            f"(lote {MUESTREOS.get(fichero['muestreo'], ('?',))[0]}) &nbsp;&middot;&nbsp; "
            f"cavidad <b>{fichero['cavidad']}</b><br>"
            f"<b>{len(puntos):,}</b> puntos".replace(",", ".")
            + (f" (se dibujan {len(reducido):,} para que la pagina no pese)".replace(",", ".")
               if len(reducido) < len(puntos) else "")
            + f"<br>X [{puntos[:,0].min():8.3f} , {puntos[:,0].max():8.3f}] &nbsp; "
            f"Y [{puntos[:,1].min():8.3f} , {puntos[:,1].max():8.3f}] &nbsp; "
            f"Z [{puntos[:,2].min():8.3f} , {puntos[:,2].max():8.3f}] (mm)<br>"
            f"{resumen_alturas}</div>"
            "<div class='leyenda'>Arrastra con el raton para <b>girar</b> la nube y usa la rueda "
            "para acercarte. El color es la <b>altura</b> (la Y del fichero). Debajo, la misma "
            "nube <b>vista desde arriba</b>.</div>"
            + grafico(fig_nube(reducido, con_lineas=fichero["familia"] == "nous"), "g1")
            + "<h2>Vista en planta (desde arriba)</h2>"
            + grafico(fig_planta(reducido), "g2")
        )
        (destino / nombre).write_text(pagina(fichero["ruta"].name, cuerpo, True), encoding="utf-8")

        arbol.setdefault(fichero["muestreo"], {}).setdefault(fichero["cavidad"], []).append(
            f"<a class='hoja' href='txt/{nombre}'>"
            f"<span class='fam'>{etiqueta}</span>"
            f"<span class='nom'>{html.escape(fichero['ruta'].name)}</span>"
            f"<span class='num'>{len(puntos):,} pts</span></a>".replace(",", ".")
        )

    # --- comparativa de puntos objetivo -------------------------------------------------
    hojas_obj: list[str] = []
    for cavidad, grupo in sorted(objetivos.items()):
        if len(grupo) < 2:
            continue
        nombre = f"obj-{cavidad}.html"
        cuerpo = (
            "<a class='volver' href='../txt-3212.html'>&larr; volver al indice</a>"
            f"<h1>{cavidad} &middot; los puntos objetivo de cada muestreo</h1>"
            f"<div class='sub'>{', '.join('intern.' + m for m, _ in sorted(grupo))}</div>"
            "<div class='leyenda'>Cada color es el objetivo que se le paso al fabricante del "
            "molde en un muestreo distinto, visto desde arriba. <b>Si los puntos no coinciden "
            "entre muestreos es que se volvio a retocar esa cavidad.</b> Los 12 ficheros "
            "<code>PUNTS_NOUS</code> del 3212 son todos distintos entre si: el retoque se "
            "especifica <b>hueco por hueco</b>, no para el molde entero.</div>"
            + grafico(fig_objetivos_superpuestos(sorted(grupo)), "g")
        )
        (destino / nombre).write_text(pagina(f"{cavidad} - objetivos", cuerpo, True), encoding="utf-8")
        hojas_obj.append(
            f"<a class='hoja' href='txt/{nombre}' style='padding-left:40px'>"
            f"<span class='fam'>{cavidad}</span>"
            f"<span class='nom'>objetivos de {cavidad} en {len(grupo)} muestreos, superpuestos</span>"
            f"<span class='num'>{len(grupo)} series</span></a>"
        )

    # --- el arbol ----------------------------------------------------------------------
    ramas = []
    for muestreo in sorted(arbol):
        lote, nota = MUESTREOS.get(muestreo, ("", ""))
        cavidades = []
        for cavidad in sorted(arbol[muestreo]):
            enlaces = arbol[muestreo][cavidad]
            cavidades.append(
                f"<details><summary>{cavidad}"
                f"<span class='meta'>{len(enlaces)} fichero(s)</span></summary>"
                f"<div class='hojas'>{''.join(enlaces)}</div></details>"
            )
        ramas.append(
            f"<details><summary>intern.{muestreo}"
            f"<span class='meta'>lote {lote}"
            + (f" &middot; <i>{nota}</i>" if nota else "")
            + f"</span></summary>{''.join(cavidades)}</details>"
        )
    if hojas_obj:
        ramas.append(
            "<details><summary>Comparar los objetivos entre muestreos"
            f"<span class='meta'>{len(hojas_obj)} paginas &middot; una cavidad cada una</span>"
            f"</summary><div class='hojas'>{''.join(hojas_obj)}</div></details>"
        )

    indice = (
        "<a class='volver' href='index.html'>&larr; volver al inicio</a>"
        "<h1>3212 Pump Housing &middot; nubes de puntos de la CMM</h1>"
        "<div class='sub'>Las coordenadas en bruto que midio la maquina. "
        "Abre una carpeta y elige un fichero.</div>"
        f"<div class='ruta'>{html.escape(str(args.raiz))}</div>"
        + INTRO
        + "<div class='aviso'>Los <code>.igs</code> y <code>.dxf</code> que hay en estas mismas "
        "carpetas <b>son estos mismos puntos otra vez</b>, en otro formato: el <code>.igs</code> "
        "es el <code>PUNTS.txt</code> con un desplazamiento en Z, y el <code>.dxf</code> es el "
        "perfil de cavidad. No hace falta abrirlos.</div>"
        "<h2>Ficheros</h2>"
        f"<div class='arbol'>{''.join(ramas)}</div>"
    )
    fichero_indice = args.salida / "txt-3212.html"
    fichero_indice.write_text(pagina("3212 - nubes de puntos", indice), encoding="utf-8")

    paginas = len(list(destino.glob("*.html")))
    print(f"\nIndice: {fichero_indice}")
    print(f"{paginas} paginas en {destino}")
    if not args.no_abrir:
        webbrowser.open(fichero_indice.as_uri())


if __name__ == "__main__":
    main()
