"""
ver_csv.py - Visualiza los CSV crudos de la maquina de medicion (CMM) del 3212.

Que son estos ficheros
----------------------
Cada `.csv` es el INFORME DE MEDICION de UNA cavidad en UN muestreo, tal y como lo
escupe la CMM (Mitutoyo / GEOPAK-WIN). No es una tabla rectangular: es un export por
bloques. Un bloque = una cota del plano (un N-number), y dentro van 1..n filas medidas:

    ****************************************************   <- separador de bloque
    N170 BOLT 1MIN/MAX H=1.5mm                             <- CABECERA: que cota es
    11;Diametro;;4.000;0.000;-0.100;3.429;-0.571;-0.471;<<---+-----
    |  |         | |     |      |      |      |      |   |
    |  |         | |     |      |      |      |      |   +-- barra ASCII (semaforo)
    |  |         | |     |      |      |      |      +-- fuera de tolerancia (vacio = OK)
    |  |         | |     |      |      |      +-- desviacion (medido - nominal)
    |  |         | |     |      |      +-- MEDIDO
    |  |         | |     |      +-- tolerancia inferior
    |  |         | |     +-- tolerancia superior
    |  |         | +-- NOMINAL (lo que pide el plano)
    |  |         +-- caracteristica en aleman (solo en el 3197)
    |  +-- que se midio: Diametro, Posicion, Planitud, Cilindricidad...
    +-- ID de elemento CMM (el numero de programa de la maquina)

Que genera
----------
Un INDICE con arbol de carpetas (`out/csv-3212.html`) y una PAGINA POR RESULTADO en
`out/csv/`. Cada pagina se abre desde el arbol; no hay scroll infinito.

    out/csv-3212.html            <- el arbol: se abre esto
    out/csv/intern.01-c13.html   <- una pagina por fichero medido
    out/csv/cav-intern.01.html   <- las 4 cavidades de un muestreo comparadas
    out/csv/evo-c13.html         <- la evolucion de una cavidad entre muestreos
    out/vendor/plotly.min.js     <- la libreria, compartida por todas las paginas

Uso
---
    python scripts/ver_csv.py                  # genera todo y abre el arbol
    python scripts/ver_csv.py --no-abrir
    python scripts/ver_csv.py --corregir-signo # invierte el error de signo de B2/B4
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import webbrowser
from pathlib import Path

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

ENCODING = "cp1252"          # los CSV de la CMM NO son utf-8
LIMITE_FRAC = 3.0            # el grafico corta en +-3 x tolerancia; el hover da el valor real

# Lote y contexto de cada muestreo con medicion 3D. Salen de la hoja HISTORY de los .xls
# (es un log acumulativo; intern.09 los tiene los nueve). -> docs/3212/4-metrologia.md
# Las fechas se dejan fuera de la interfaz a proposito: lo que ordena los muestreos es su
# numero, y lo que importa de cada uno es que paso antes (el retoque de molde).
MUESTREOS = {
    "01": ("315252", "primer muestreo completo"),
    "03": ("315346", "despues de la correccion de molde n1"),
    "05": ("315426", "despues de la correccion de molde n2"),
    "08": ("08/01/2025", "verificacion posterior (este lote se identifica por fecha)"),
}

# --------------------------------------------------------------------------------------
# Descubrimiento de ficheros
# --------------------------------------------------------------------------------------


def num_muestreo(ruta: Path) -> str:
    """'support intern.01' / 'support.intern.08' -> '01' / '08'."""
    for parte in ruta.parts:
        m = re.search(r"intern[.\s]*(\d+)", parte, re.IGNORECASE)
        if m:
            return m.group(1).zfill(2)
    return "??"


def num_cavidad(ruta: Path) -> str | None:
    """Saca la cavidad del nombre del fichero o, si no esta, de la carpeta padre.

    Hay tres grafias en el 3212: '3212_c13.csv', '3212c14.csv' y '13_3212.csv'.
    Y en intern.05 las carpetas c15/ y c16/ tienen ficheros con el MISMO nombre,
    asi que la carpeta padre es la unica pista.
    """
    for texto in (ruta.stem, ruta.parent.name):
        m = re.search(r"^(\d{2})[_\s]", texto)          # 13_3212
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
        m = re.search(r"[cC][._\s]?(\d{2})", texto)     # 3212_c13 / 3212c14 / C13
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
    return None


def descubrir(raiz: Path) -> list[dict]:
    """Los 16 CSV de cavidad, ordenados por muestreo y cavidad.

    Los 3 'totes.csv' quedan fuera a proposito: tienen una columna por cavidad pero
    PIERDEN la desviacion, el fuera-de-tolerancia y el semaforo. El CSV de cavidad es
    estrictamente mas rico.
    """
    ficheros = []
    for ruta in raiz.rglob("*.csv"):
        if "totes" in ruta.stem.lower():
            continue
        cavidad = num_cavidad(ruta)
        if cavidad is None:
            print(f"  [aviso] no se deduce la cavidad, se salta: {ruta.name}")
            continue
        ficheros.append(
            {
                "ruta": ruta,
                "muestreo": num_muestreo(ruta),
                "cavidad": cavidad,
                "rel": ruta.relative_to(raiz.parent).as_posix(),
            }
        )
    return sorted(ficheros, key=lambda f: (f["muestreo"], f["cavidad"]))


# --------------------------------------------------------------------------------------
# Parser del CSV
# --------------------------------------------------------------------------------------


def a_float(texto: str) -> float | None:
    texto = texto.strip()
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def leer_csv_cavidad(ruta: Path) -> pd.DataFrame:
    """Aplana el export por bloques a una tabla de una fila por medicion.

    Regla de deteccion (la que funciona): una linea es DATO si tiene >=8 campos y el
    campo 2 (caracteristica) no esta vacio. Ojo: muchas filas de dato traen el ID de
    elemento CMM VACIO ( ';Calculo de formula;;1.350;...' ), asi que mirar el campo 1
    para decidir da falsos positivos.
    """
    filas: list[dict] = []
    bloque = "(sin bloque)"
    ocurrencia = 0
    vistos: dict[str, int] = {}
    idx = 0

    with ruta.open(encoding=ENCODING, errors="replace") as fichero:
        for linea in fichero:
            linea = linea.rstrip("\r\n")
            if not linea.replace(";", "").strip():
                continue
            if linea.startswith("****") or linea.startswith("////"):
                continue

            campos = linea.split(";")
            es_dato = len(campos) >= 8 and campos[1].strip() != ""

            if not es_dato:
                bloque = linea.rstrip("; \t")
                # Hay cabeceras REPETIDAS: 'N170 BOLT 1 MIN/MAX H=5.0 mm' sale tambien
                # dentro del bloque del BOLT 2 (errata de la plantilla). Se numera cada
                # aparicion para que la clave de cruce entre muestreos sea unica.
                vistos[bloque] = vistos.get(bloque, 0) + 1
                ocurrencia = vistos[bloque]
                idx = 0
                continue

            idx += 1
            campos += [""] * (10 - len(campos))
            filas.append(
                {
                    "bloque": bloque,
                    "ocurrencia": ocurrencia,
                    "idx": idx,
                    "id_cmm": campos[0].strip(),
                    "caracteristica": campos[1].strip(),
                    "nominal": a_float(campos[3]),
                    "tol_sup": a_float(campos[4]),
                    "tol_inf": a_float(campos[5]),
                    "medido": a_float(campos[6]),
                    "desviacion": a_float(campos[7]),
                    "fuera_tol": a_float(campos[8]),
                    "barra": campos[9].strip(),
                }
            )

    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla

    # NOK: la columna 9 trae valor, o la barra ASCII se sale por un lado.
    tabla["nok"] = tabla["fuera_tol"].notna() | tabla["barra"].str.contains(r"<<|>>", regex=True)

    # Error de signo conocido del export (bolts B2 y B4, 'Posicion Z'): el nominal es
    # +31 y la maquina escribe -30,990, con lo que la desviacion sale -61,99. Esta en
    # los cuatro muestreos: NO es una pieza mala.
    tabla["signo_sospechoso"] = [
        bool(
            nom is not None
            and med is not None
            and abs(nom) > 1
            and nom * med < 0
            and abs(abs(med) - abs(nom)) < 0.5
        )
        for nom, med in zip(tabla["nominal"], tabla["medido"])
    ]

    tabla["etiqueta"] = [
        f"{b}  [{i}] {c}" + (f"  #{d}" if d else "")
        for b, i, c, d in zip(tabla["bloque"], tabla["idx"], tabla["caracteristica"], tabla["id_cmm"])
    ]
    tabla["clave"] = (tabla["bloque"] + "#" + tabla["ocurrencia"].astype(str)
                      + "||" + tabla["idx"].astype(str))
    if tabla["clave"].duplicated().any():
        raise ValueError(f"claves duplicadas en {ruta.name}: no se podra cruzar con otros muestreos")
    return tabla


def alinear(referencia: pd.DataFrame, otra: pd.DataFrame) -> pd.DataFrame:
    """Reordena 'otra' segun las claves de 'referencia', con NaN donde no haya dato.

    Devuelve SIEMPRE len(referencia) filas: es lo que permite superponer cavidades y
    muestreos sabiendo que la fila i es la misma medicion en todos.
    """
    return otra.set_index("clave").reindex(referencia["clave"]).reset_index()


def corregir_signo(tabla: pd.DataFrame) -> pd.DataFrame:
    """Invierte el medido de las filas con el error de signo y recalcula la desviacion."""
    tabla = tabla.copy()
    afectadas = tabla["signo_sospechoso"]
    tabla.loc[afectadas, "medido"] = -tabla.loc[afectadas, "medido"]
    tabla.loc[afectadas, "desviacion"] = tabla.loc[afectadas, "medido"] - tabla.loc[afectadas, "nominal"]
    return tabla


def fraccion_tolerancia(fila: pd.Series) -> float | None:
    """Desviacion expresada en FRACCION DE LA TOLERANCIA consumida.

    0 = clavado en el nominal · +-1 = justo en el limite · fuera de [-1, 1] = NOK.
    Sirve para poner en el mismo grafico una cota de +-0,5 y una de +-0,02.
    """
    desv, sup, inf = fila["desviacion"], fila["tol_sup"], fila["tol_inf"]
    if desv is None or pd.isna(desv):
        return None
    banda = sup if desv >= 0 else (abs(inf) if inf is not None and not pd.isna(inf) else None)
    if not banda:                     # tolerancia 0 por ese lado: cualquier desvio se sale
        return LIMITE_FRAC * (1 if desv >= 0 else -1) if desv else 0.0
    return desv / banda


# --------------------------------------------------------------------------------------
# Graficos
# --------------------------------------------------------------------------------------

VERDE, ROJO, GRIS = "#2a9d5c", "#d1495b", "#9aa0a6"
PALETA_CAV = {"c13": "#3d6fb4", "c14": "#2a9d5c", "c15": "#e08b1e", "c16": "#8e5ea2"}


def hover_medicion(tabla: pd.DataFrame) -> list[str]:
    textos = []
    for _, f in tabla.iterrows():
        if pd.isna(f["medido"]):
            textos.append("sin dato")
            continue
        tol = f"+{f['tol_sup']:.3f} / {f['tol_inf']:.3f}" if pd.notna(f["tol_sup"]) else "-"
        textos.append(
            f"<b>{html.escape(str(f['bloque']))}</b><br>"
            f"{f['caracteristica']} (ID CMM {f['id_cmm'] or '-'})<br>"
            f"nominal <b>{f['nominal']}</b>  tol {tol}<br>"
            f"medido <b>{f['medido']}</b><br>"
            f"desviacion <b>{f['desviacion']:+.3f} mm</b><br>"
            f"{'FUERA DE TOLERANCIA' if f['nok'] else 'dentro de tolerancia'}"
            + ("<br><i>signo invertido en el export</i>" if f["signo_sospechoso"] else "")
        )
    return textos


def fig_fichero(tabla: pd.DataFrame) -> go.Figure:
    """Una barra por caracteristica, con la banda de tolerancia sombreada."""
    fraccion = tabla.apply(fraccion_tolerancia, axis=1).clip(-LIMITE_FRAC, LIMITE_FRAC)
    colores = [ROJO if nok else VERDE for nok in tabla["nok"]]
    eje_y = list(range(len(tabla)))

    fig = go.Figure()
    fig.add_shape(                                   # la banda "dentro de tolerancia"
        type="rect", x0=-1, x1=1, y0=-0.5, y1=len(tabla) - 0.5,
        fillcolor="rgba(42,157,92,0.10)", line_width=0, layer="below",
    )
    for x in (-1, 1):
        fig.add_shape(type="line", x0=x, x1=x, y0=-0.5, y1=len(tabla) - 0.5,
                      line=dict(color=VERDE, width=1, dash="dot"), layer="below")

    fig.add_trace(
        go.Bar(
            x=fraccion, y=eje_y, orientation="h",
            marker=dict(color=colores, line=dict(width=0)),
            hovertext=hover_medicion(tabla), hoverinfo="text", showlegend=False,
        )
    )
    fig.update_layout(
        height=max(600, 15 * len(tabla)),
        margin=dict(l=430, r=40, t=20, b=50),
        xaxis=dict(
            title="desviacion / tolerancia   (0 = nominal del plano, +-1 = el limite)",
            range=[-LIMITE_FRAC - 0.2, LIMITE_FRAC + 0.2], zeroline=True, zerolinewidth=2,
        ),
        yaxis=dict(
            tickmode="array", tickvals=eje_y, ticktext=tabla["etiqueta"],
            tickfont=dict(size=9, family="monospace"), autorange="reversed", showgrid=False,
        ),
        bargap=0.25, plot_bgcolor="white",
    )
    return fig


def fig_cavidades(tablas: dict[str, pd.DataFrame]) -> go.Figure:
    """Las 4 cavidades superpuestas sobre la misma caracteristica."""
    referencia = tablas[min(tablas)]
    eje_y = list(range(len(referencia)))

    fig = go.Figure()
    fig.add_shape(type="rect", x0=-1, x1=1, y0=-0.5, y1=len(referencia) - 0.5,
                  fillcolor="rgba(42,157,92,0.10)", line_width=0, layer="below")

    for cavidad, tabla in sorted(tablas.items()):
        alineada = alinear(referencia, tabla)
        fraccion = alineada.apply(fraccion_tolerancia, axis=1).clip(-LIMITE_FRAC, LIMITE_FRAC)
        fig.add_trace(
            go.Scatter(
                x=fraccion, y=eje_y, mode="markers", name=cavidad,
                marker=dict(size=7, color=PALETA_CAV.get(cavidad, GRIS),
                            symbol="diamond", line=dict(width=0)),
                hovertext=hover_medicion(alineada), hoverinfo="text",
            )
        )

    fig.update_layout(
        height=max(600, 15 * len(referencia)),
        margin=dict(l=430, r=40, t=20, b=50),
        xaxis=dict(title="desviacion / tolerancia", range=[-LIMITE_FRAC - 0.2, LIMITE_FRAC + 0.2],
                   zeroline=True, zerolinewidth=2),
        yaxis=dict(tickmode="array", tickvals=eje_y, ticktext=referencia["etiqueta"],
                   tickfont=dict(size=9, family="monospace"), autorange="reversed", showgrid=False),
        plot_bgcolor="white", legend=dict(orientation="h", y=1.01, x=0),
    )
    return fig


def fig_evolucion(por_muestreo: dict[str, pd.DataFrame]) -> go.Figure:
    """Heatmap caracteristica x muestreo. Rojo = se sale, verde = dentro."""
    muestreos = sorted(por_muestreo)
    referencia = por_muestreo[muestreos[0]]

    columnas = []
    for muestreo in muestreos:
        alineada = alinear(referencia, por_muestreo[muestreo])
        columnas.append(alineada.apply(fraccion_tolerancia, axis=1).clip(-LIMITE_FRAC, LIMITE_FRAC))

    matriz = pd.concat(columnas, axis=1)
    hover = [
        [
            f"{referencia['etiqueta'].iloc[i]}<br>intern.{m}<br>"
            + (f"desv/tol = {matriz.iloc[i, j]:+.2f}" if pd.notna(matriz.iloc[i, j]) else "sin dato")
            for j, m in enumerate(muestreos)
        ]
        for i in range(len(matriz))
    ]

    fig = go.Figure(
        go.Heatmap(
            z=matriz.values, x=[f"intern.{m}" for m in muestreos], y=list(range(len(matriz))),
            colorscale=[[0.0, ROJO], [0.33, "#f7f7f7"], [0.5, VERDE],
                        [0.67, "#f7f7f7"], [1.0, ROJO]],
            zmid=0, zmin=-LIMITE_FRAC, zmax=LIMITE_FRAC,
            hovertext=hover, hoverinfo="text", colorbar=dict(title="desv/tol"),
        )
    )
    fig.update_layout(
        height=max(600, 14 * len(matriz)),
        margin=dict(l=430, r=40, t=20, b=50),
        yaxis=dict(tickmode="array", tickvals=list(range(len(matriz))),
                   ticktext=referencia["etiqueta"], tickfont=dict(size=9, family="monospace"),
                   autorange="reversed"),
        plot_bgcolor="white",
    )
    return fig


def fig_mas_movidas(por_muestreo: dict[str, pd.DataFrame], top: int = 15) -> go.Figure:
    """Las cotas que mas se movieron entre el primer y el ultimo muestreo, en mm."""
    muestreos = sorted(por_muestreo)
    referencia = por_muestreo[muestreos[0]]

    series = {m: alinear(referencia, por_muestreo[m])["medido"].values for m in muestreos}
    valores = pd.DataFrame(series)
    recorrido = valores.max(axis=1) - valores.min(axis=1)
    indices = recorrido.sort_values(ascending=False).head(top).index

    fig = go.Figure()
    for i in indices:
        fig.add_trace(
            go.Scatter(
                x=[f"intern.{m}" for m in muestreos], y=[series[m][i] for m in muestreos],
                mode="lines+markers", name=referencia["etiqueta"].iloc[i][:60],
                hovertemplate="%{y:.3f} mm<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(
        height=620, margin=dict(l=70, r=40, t=20, b=50),
        yaxis_title="valor medido (mm)", plot_bgcolor="white",
        legend=dict(font=dict(size=9, family="monospace")),
    )
    return fig


# --------------------------------------------------------------------------------------
# HTML: un indice con arbol + una pagina por resultado
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
.aviso { background: #fff7f7; border-left: 3px solid var(--rojo, #d1495b); padding: 10px 16px;
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
.hojas { padding: 4px 0 8px; }
a.hoja { display: flex; align-items: center; gap: 10px; padding: 7px 16px 7px 40px;
         text-decoration: none; color: var(--tinta); font-size: 14px; border-left: 3px solid transparent; }
a.hoja:hover { background: #f2f5f9; border-left-color: var(--azul); }
a.hoja .nom { font-family: ui-monospace, Consolas, monospace; }
a.hoja .cav { font-weight: 600; min-width: 40px; }
a.hoja .num { margin-left: auto; color: var(--suave); font-size: 12.5px;
              font-family: ui-monospace, Consolas, monospace; }
a.hoja .mal { color: #d1495b; }

/* paginas de resultado */
.volver { display: inline-block; margin-bottom: 18px; font-size: 14px; color: var(--azul);
          text-decoration: none; }
.volver:hover { text-decoration: underline; }
.tarjeta { border: 1px solid var(--linea); border-radius: 10px; padding: 14px 18px;
           margin: 16px 0; font-size: 14px; background: #fafbfc; }
.tarjeta b { font-variant-numeric: tabular-nums; }
.leyenda { border-left: 3px solid var(--azul); background: #f7f9fc; padding: 12px 16px;
           margin: 18px 0; font-size: 14px; border-radius: 0 6px 6px 0; }
table { border-collapse: collapse; font-size: 11px; font-family: ui-monospace, Consolas, monospace;
        width: 100%; }
th, td { border: 1px solid #e6e6e6; padding: 2px 6px; text-align: right; }
th { background: #f0f2f5; position: sticky; top: 0; }
td.txt { text-align: left; }
tr.nok { background: #ffeceb; }
details.crudo { margin: 20px 0; }
details.crudo summary { cursor: pointer; font-size: 13.5px; color: var(--azul); }
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


def tabla_html(tabla: pd.DataFrame) -> str:
    cabecera = ("<tr><th>bloque</th><th>#</th><th>ID</th><th>caracteristica</th><th>nominal</th>"
                "<th>tol+</th><th>tol-</th><th>medido</th><th>desv</th><th>fuera</th>"
                "<th>semaforo</th></tr>")
    filas = []
    for _, f in tabla.iterrows():
        clase = ' class="nok"' if f["nok"] else ""
        filas.append(
            f"<tr{clase}>"
            f"<td class='txt'>{html.escape(str(f['bloque']))}</td><td>{f['idx']}</td>"
            f"<td>{html.escape(str(f['id_cmm']))}</td>"
            f"<td class='txt'>{html.escape(str(f['caracteristica']))}</td>"
            f"<td>{f['nominal']}</td><td>{f['tol_sup']}</td><td>{f['tol_inf']}</td>"
            f"<td><b>{f['medido']}</b></td><td>{f['desviacion']}</td>"
            f"<td>{'' if pd.isna(f['fuera_tol']) else f['fuera_tol']}</td>"
            f"<td class='txt'>{html.escape(str(f['barra']))}</td></tr>"
        )
    return f"<table>{cabecera}{''.join(filas)}</table>"


LEYENDA_BANDA = (
    "<div class='leyenda'><b>Como se lee.</b> Cada barra es una medicion. El eje horizontal "
    "<b>no esta en milimetros</b>: esta en <b>fraccion de la tolerancia que se ha comido</b>. "
    "El <b>0</b> es clavar el valor que pide el plano; <b>&plusmn;1</b> es justo el limite "
    "permitido (la franja verde). Todo lo que se salga de la franja esta <b>fuera de "
    "tolerancia</b> y sale en rojo. Se normaliza asi porque en la misma pieza conviven cotas "
    "de &plusmn;0,5 mm y de &plusmn;0,02 mm, y en milimetros no se podrian comparar. "
    "<b>Pon el raton encima de cualquier barra</b> y veras el nominal, el medido y la "
    "desviacion reales en mm. Las barras cortadas en &plusmn;3 estan aun mas lejos.</div>"
)

INTRO = """
<div class='intro'>
<h3>Que es un &laquo;muestreo&raquo;</h3>
<p>Cada cierto tiempo se saca una tanda de piezas del molde y se lleva al laboratorio a medir.
Eso es un muestreo: <code>intern.01</code>, <code>intern.03</code>&hellip; El 3212 tiene nueve,
pero <b>solo cuatro se midieron con la maquina 3D</b>, y son los que ves aqui: el
<b>01, 03, 05 y 08</b>. Entre uno y otro <b>se retoco el molde</b>, asi que la secuencia es la
historia de como fue mejorando la pieza.</p>

<h3>Que es una &laquo;cavidad&raquo;</h3>
<p>El molde tiene 16 huecos y saca 16 piezas por inyectada. De esos 16 se controlan cuatro:
<b>c13, c14, c15 y c16</b>. Por eso hay un fichero por cavidad y muestreo:
<code>intern.05 / c14</code> son las medidas de la pieza que salio del hueco 14 en esa tanda.</p>

<h3>Que hay dentro de cada fichero</h3>
<p><b>211 mediciones.</b> La maquina recorre la pieza siguiendo un programa y va anotando:
un diametro aqui, una planitud alla, la posicion de aquel agujero&hellip; De cada una guarda
<b>lo que pedia el plano</b> (el valor nominal y cuanto se puede desviar) y <b>lo que se midio
de verdad</b>. Si la diferencia se pasa de lo permitido, esa medicion es un <b>NOK</b>.</p>

<h3>Por que se pueden comparar entre si</h3>
<p>Porque <b>el programa de la maquina no se toco en 15 meses</b>. En los cuatro muestreos midio
exactamente las mismas 211 cosas y en el mismo orden. Eso significa que <b>la medicion numero 57
del primer muestreo y la numero 57 del ultimo son el mismo punto de la misma zona de la
pieza</b>: basta restarlas para saber si el retoque del molde funciono. Es lo que hacen las dos
ultimas carpetas del arbol.</p>
</div>
"""

AVISO_RAREZAS = (
    "<div class='aviso'><b>Dos rarezas del fichero que no son piezas malas.</b><br>"
    "1. Los bolts <b>B2 y B4</b> exportan <code>Posicion Z</code> con el <b>signo invertido</b> "
    "(el plano pide +31 y la maquina escribe -30,990, con lo que la desviacion sale -61,99). "
    "Pasa en los cuatro muestreos: es la convencion de signo del export. Se avisa en el hover; "
    "con <code>--corregir-signo</code> se invierte.<br>"
    "2. La cabecera <code>N170 BOLT 1 MIN/MAX H=5.0 mm</code> aparece <b>repetida dentro del "
    "bloque del BOLT 2</b> (un copiar-pegar de la plantilla). Para saber que es cada fila hay "
    "que mirar el <b>ID de elemento CMM</b> (11-14 = altura 1,5 mm &middot; 15-18 = altura "
    "5,0 mm &middot; 31-34 = posicion), no el titulo.</div>"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", type=Path, default=RAIZ, help="carpeta 4- Metrologia")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de salida")
    parser.add_argument("--corregir-signo", action="store_true",
                        help="invierte el medido de las filas con el error de signo de B2/B4")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador al terminar")
    args = parser.parse_args()

    ficheros = descubrir(args.raiz)
    if not ficheros:
        sys.exit(f"No se ha encontrado ningun CSV de cavidad en {args.raiz}")
    print(f"{len(ficheros)} CSV de cavidad encontrados\n")

    destino = args.salida / "csv"
    destino.mkdir(parents=True, exist_ok=True)
    vendor = args.salida / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")

    tablas: dict[tuple[str, str], pd.DataFrame] = {}
    hojas: dict[str, list[str]] = {}          # muestreo -> <a> del arbol

    # --- una pagina por fichero medido -------------------------------------------------
    for fichero in ficheros:
        tabla = leer_csv_cavidad(fichero["ruta"])
        if args.corregir_signo:
            tabla = corregir_signo(tabla)
        tablas[(fichero["muestreo"], fichero["cavidad"])] = tabla

        nok = int(tabla["nok"].sum())
        print(f"  intern.{fichero['muestreo']} {fichero['cavidad']}  "
              f"{len(tabla):3d} mediciones, {nok:3d} NOK  <- {fichero['ruta'].name}")

        nombre = f"intern.{fichero['muestreo']}-{fichero['cavidad']}.html"
        cuerpo = (
            "<a class='volver' href='../csv-3212.html'>&larr; volver al indice</a>"
            f"<h1>{html.escape(fichero['ruta'].name)}</h1>"
            f"<div class='ruta'>{html.escape(fichero['rel'])}</div>"
            f"<div class='tarjeta'>Muestreo <b>intern.{fichero['muestreo']}</b> "
            f"(lote {MUESTREOS.get(fichero['muestreo'], ('?',))[0]}) &nbsp;&middot;&nbsp; "
            f"cavidad <b>{fichero['cavidad']}</b> &nbsp;&middot;&nbsp; <b>una pieza</b><br>"
            f"<b>{len(tabla)}</b> mediciones &nbsp;&middot;&nbsp; "
            f"<b style='color:{ROJO}'>{nok} fuera de tolerancia</b> &nbsp;&middot;&nbsp; "
            f"{int(tabla['signo_sospechoso'].sum())} con el error de signo de B2/B4</div>"
            + LEYENDA_BANDA
            + grafico(fig_fichero(tabla), "g")
            + f"<details class='crudo'><summary>ver las {len(tabla)} filas en crudo (mm)</summary>"
            f"{tabla_html(tabla)}</details>"
        )
        (destino / nombre).write_text(pagina(fichero["ruta"].name, cuerpo, con_plotly=True),
                                      encoding="utf-8")

        hojas.setdefault(fichero["muestreo"], []).append(
            f"<a class='hoja' href='csv/{nombre}'>"
            f"<span class='cav'>{fichero['cavidad']}</span>"
            f"<span class='nom'>{html.escape(fichero['ruta'].name)}</span>"
            f"<span class='num'>{len(tabla)} mediciones &middot; "
            f"<span class='mal'>{nok} NOK</span></span></a>"
        )

    # --- una pagina por comparativa ----------------------------------------------------
    hojas_cav: list[str] = []
    for muestreo in sorted({f["muestreo"] for f in ficheros}):
        del_muestreo = {c: t for (m, c), t in tablas.items() if m == muestreo}
        if len(del_muestreo) < 2:
            continue
        nombre = f"cav-intern.{muestreo}.html"
        cuerpo = (
            "<a class='volver' href='../csv-3212.html'>&larr; volver al indice</a>"
            f"<h1>intern.{muestreo} &middot; las {len(del_muestreo)} cavidades comparadas</h1>"
            f"<div class='sub'>lote {MUESTREOS.get(muestreo, ('',))[0]} &middot; "
            f"{', '.join(sorted(del_muestreo))} &middot; una pieza por cavidad</div>"
            "<div class='leyenda'>Las cuatro cavidades del molde, <b>medida a medida</b>. "
            "Sirve para distinguir <b>un problema del molde entero</b> (los cuatro rombos "
            "desplazados a la vez hacia el mismo lado) de <b>un problema de una sola cavidad</b> "
            "(un rombo suelto lejos de los otros tres). Lo primero se corrige cambiando "
            "parametros de inyeccion; lo segundo, retocando ese hueco del molde.</div>"
            + LEYENDA_BANDA
            + grafico(fig_cavidades(del_muestreo), "g")
        )
        (destino / nombre).write_text(pagina(f"intern.{muestreo} - cavidades", cuerpo, True),
                                      encoding="utf-8")
        hojas_cav.append(
            f"<a class='hoja' href='csv/{nombre}'>"
            f"<span class='cav'>{muestreo}</span>"
            f"<span class='nom'>intern.{muestreo} &middot; {len(del_muestreo)} cavidades "
            f"superpuestas</span>"
            f"<span class='num'>lote {MUESTREOS.get(muestreo, ('',))[0]}</span></a>"
        )

    hojas_evo: list[str] = []
    for cavidad in sorted({f["cavidad"] for f in ficheros}):
        de_la_cavidad = {m: t for (m, c), t in tablas.items() if c == cavidad}
        if len(de_la_cavidad) < 2:
            continue
        nombre = f"evo-{cavidad}.html"
        cuerpo = (
            "<a class='volver' href='../csv-3212.html'>&larr; volver al indice</a>"
            f"<h1>{cavidad} &middot; evolucion entre muestreos</h1>"
            f"<div class='sub'>{' &rarr; '.join('intern.' + m for m in sorted(de_la_cavidad))}</div>"
            "<div class='leyenda'>Cada <b>fila</b> es una medicion y cada <b>columna</b> un "
            "muestreo, en orden cronologico. <b>Verde = dentro de tolerancia, rojo = fuera.</b> "
            "Leer de izquierda a derecha es ver madurar el molde: <b>una fila que pasa de roja a "
            "verde es un retoque que funciono</b>. Debajo, las 15 cotas que mas se movieron, esta "
            "vez en milimetros reales.</div>"
            + grafico(fig_evolucion(de_la_cavidad), "g1")
            + "<h2>Las 15 cotas que mas se movieron (mm)</h2>"
            + grafico(fig_mas_movidas(de_la_cavidad), "g2")
        )
        (destino / nombre).write_text(pagina(f"{cavidad} - evolucion", cuerpo, True), encoding="utf-8")
        hojas_evo.append(
            f"<a class='hoja' href='csv/{nombre}'>"
            f"<span class='cav'>{cavidad}</span>"
            f"<span class='nom'>evolucion de {cavidad} a lo largo de "
            f"{len(de_la_cavidad)} muestreos</span>"
            f"<span class='num'>heatmap + mm</span></a>"
        )

    # --- el arbol ----------------------------------------------------------------------
    ramas = []
    for muestreo in sorted(hojas):
        lote, nota = MUESTREOS.get(muestreo, ("", ""))
        ramas.append(
            f"<details open><summary>intern.{muestreo}"
            f"<span class='meta'>lote {lote}"
            + (f" &middot; <i>{nota}</i>" if nota else "")
            + f"</span></summary><div class='hojas'>{''.join(hojas[muestreo])}</div></details>"
        )
    if hojas_cav:
        ramas.append(
            "<details><summary>Comparar las cavidades entre si"
            f"<span class='meta'>{len(hojas_cav)} paginas &middot; un muestreo cada una</span>"
            f"</summary><div class='hojas'>{''.join(hojas_cav)}</div></details>"
        )
    if hojas_evo:
        ramas.append(
            "<details><summary>Comparar los muestreos entre si (evolucion)"
            f"<span class='meta'>{len(hojas_evo)} paginas &middot; una cavidad cada una</span>"
            f"</summary><div class='hojas'>{''.join(hojas_evo)}</div></details>"
        )

    indice = (
        "<a class='volver' href='index.html'>&larr; volver al inicio</a>"
        "<h1>3212 Pump Housing &middot; mediciones de la CMM</h1>"
        "<div class='sub'>Los informes de la maquina de medir, tal cual salen de ella. "
        "Elige un fichero en el arbol.</div>"
        f"<div class='ruta'>{html.escape(str(args.raiz))}</div>"
        + INTRO
        + AVISO_RAREZAS
        + ("<div class='aviso'><b>Modo --corregir-signo activo:</b> el medido de las filas "
           "afectadas se ha invertido.</div>" if args.corregir_signo else "")
        + "<h2>Ficheros</h2>"
        f"<div class='arbol'>{''.join(ramas)}</div>"
    )
    fichero_indice = args.salida / "csv-3212.html"
    fichero_indice.write_text(pagina("3212 - mediciones de la CMM", indice), encoding="utf-8")

    paginas = len(list(destino.glob("*.html")))
    print(f"\nIndice: {fichero_indice}")
    print(f"{paginas} paginas en {destino}")
    if not args.no_abrir:
        webbrowser.open(fichero_indice.as_uri())


if __name__ == "__main__":
    main()
