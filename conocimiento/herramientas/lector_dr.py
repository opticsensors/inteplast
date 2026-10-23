"""Prototipo de lector determinista de informes dimensionales (hojas DR y PPAP de cliente).

Sirve para medir qué puede extraer la app sin intervención y con qué fiabilidad (ver
`docs/ingesta-automatica.md`). Lee de la biblioteca (tabla `celda`), no de los originales, y no lo
importa la app: los lectores de producción viven en `backend/app/ingestion/`.

Reglas (todas deterministas):
  - Hoja candidata: en sus 40 primeras filas hay una fila con «Nominal»/«Target» y columnas de
    cavidad (`Cav.1`, `CAV_2`, `C13`, `Cav 3.1`) o de muestra (1…5 en las hojas `cav_N` de cliente)
    o, en su defecto, números 1…N consecutivos (3288 `DR(base)`).
  - Columnas por etiqueta (inglés y castellano), nunca por posición, salvo el código de cota: la
    columna con «Nr»/«Number» o, si no hay, la de más códigos a la izquierda del nominal.
  - Cavidades 1–64 y solo el primer bloque contiguo; los siguientes, si llevan rótulo de condición.
  - Tolerancias al revés se ordenan; nombres cortos de cota («Distance 1») se aceptan con «~».
  - Papel de la hoja (lista de marcas; `informe` si no hay ninguna): `con_correccion` (etiquetas
    cortas «Retoc», «Corr.», «Correction»…), `copia` (« (n)»), `comparativa` (DIF, vs, compar…),
    `bloques_secundarios`, `generada` (celdas RAND), `sospechosa` (> 30 % atípicos). El nombre
    «100%» no decide nada (casi siempre es el informe completo).
  - Marcas por valor: `aleatoria` (celda en `celda_aleatoria`), `cero` (0 con nominal distinto de 0),
    `atipico` (desviación > 10 veces el intervalo de tolerancia).
  - Comprobación independiente: la columna NOK que calcula el propio libro frente a la que sale de
    nominal + tolerancias + valores leídos.

Guarda `lectura_dr` (una fila por hoja) y `medida_dr` (una fila por valor). Se recalculan.

    python conocimiento/herramientas/lector_dr.py
"""

from __future__ import annotations

import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import cerrar_registro, conectar, registrar  # noqa: E402

ESQUEMA = """
DROP TABLE IF EXISTS lectura_dr;
DROP TABLE IF EXISTS medida_dr;
CREATE TABLE lectura_dr (
  documento_id INTEGER, hoja TEXT, plantilla TEXT, papel TEXT, fila_cabecera INTEGER, columnas TEXT,
  cavidades TEXT, filas_cota INTEGER, valores INTEGER, cualitativos INTEGER, rechazadas TEXT,
  aleatorias INTEGER, ceros INTEGER, atipicos INTEGER, nok TEXT,
  ejemplos TEXT, columnas_descartadas TEXT,
  PRIMARY KEY (documento_id, hoja)
);
CREATE TABLE medida_dr (
  documento_id INTEGER, hoja TEXT, fila INTEGER, col INTEGER, cota TEXT, nominal REAL, tol_sup REAL,
  tol_inf REAL, equipo TEXT, cavidad TEXT, valor REAL, marca TEXT
);
"""
ETIQUETAS = {
    "nominal": r"(nominal|target|nom\.?|valor nominal)",
    "tol_sup": r"(tol\.?\s*\+|\+\s*tol\.?|upper tol\.?|tol\.?\s*sup\.?)",
    "tol_inf": r"(tol\.?\s*[-–]|[-–]\s*tol\.?|lower tol\.?|tol\.?\s*inf\.?)",
    "equipo": r"(equipment|equipo|meas\.?\s*equip\.?|measuring device|medio)",
    "tipo": r"(type|tipo)",
    "unidad": r"(units?|unidad)",
    "nok": r"(nok|fuera lim\.?)",
    "codigo": r"(nr\.?|number|n[ºo°]|item)",
}
PREVISION = re.compile(r"retoc|^corr\.?$|correction|previs|desviaci|wished", re.I)
CAVIDAD = re.compile(r"^(?:cav(?:ity|idad)?\.?\s*|c\s*)(\d+)((?:\.\d+)*)$", re.I)
# Cota: N-number (con subpuntos, .T, .Cmk), id de cliente («1-197.1», «B-0580-935.1») o letra (A, Z1).
# Un texto con espacios («SHOT 1», «BASE SOP…») es un rotulo de seccion, no una cota.
CODIGO = re.compile(r"^N?\s*(\d+(?:\.\d+)*(?:\.[A-Za-z]+)?)$|^([A-Za-z0-9][\w./-]{0,19})$", re.I)
COMPARATIVA = re.compile(r"dif|differen|vs|compar", re.I)
MAX_CAVIDAD = 64


def numero(texto: str | None) -> float | None:
    if texto is None:
        return None
    try:
        valor = float(str(texto).strip().replace(",", "."))
    except ValueError:
        return None
    return valor if math.isfinite(valor) else None


def etiqueta(texto: str) -> str | None:
    t = re.sub(r"\s+", " ", str(texto).strip().lower())
    for nombre, patron in ETIQUETAS.items():
        if re.fullmatch(patron, t):
            return nombre
    return None


def codigo_normal(texto: str) -> str | None:
    t = str(texto).strip()
    if re.fullmatch(r"\d+\.0", t):
        t = t[:-2]
    m = CODIGO.fullmatch(t)
    if not m or (m.group(2) and not re.search(r"\d", t) and len(t) > 2):
        return None
    return (m.group(1) or m.group(2)).upper()


def leer_hoja(hoja: str, celdas: dict[tuple[int, int], str], aleatorias: set[tuple[int, int]]) -> dict | None:
    filas = collections.defaultdict(dict)
    for (f, c), v in celdas.items():
        filas[f][c] = v
    cabecera = None
    for f in sorted(x for x in filas if x <= 40):
        etiquetas = {c: etiqueta(v) for c, v in filas[f].items()}
        if "nominal" not in etiquetas.values():
            continue
        cavs = {c: m for c, v in filas[f].items()
                if (m := CAVIDAD.fullmatch(str(v).strip())) and 1 <= int(m.group(1)) <= MAX_CAVIDAD}
        numeros = {c: int(float(v)) for c, v in filas[f].items()
                   if re.fullmatch(r"\d+(\.0)?", str(v).strip()) and 1 <= float(v) <= 64}
        if cavs or len(numeros) >= 2:
            cabecera = (f, etiquetas, cavs, numeros)
            break
    if cabecera is None:
        return None
    f0, etiquetas, cavs, numeros = cabecera
    descartadas = collections.Counter()
    col = {}
    for fila in (f0 - 1, f0):  # «Nr» y «NOK» a veces estan en la fila de encima
        for c, v in filas.get(fila, {}).items():
            e = etiqueta(v)
            if e and e not in col:
                col[e] = c
    cliente = bool(re.fullmatch(r"cav_\d+", hoja, re.I)) and not cavs
    if cliente:  # PPAP de cliente: una hoja por cavidad, columnas 1..5 = muestras
        cav_hoja = "c" + re.search(r"\d+", hoja).group(0)
        columnas_valor = {c: f"{cav_hoja}.m{n}" for c, n in numeros.items()}
        plantilla = "cliente_por_cavidad"
    elif cavs:
        # Bloques de columnas de cavidad consecutivas. El primero es la medida. Los siguientes solo
        # cuentan si llevan encima un rotulo de condicion («750 bars», «punxons recanvi…»); sin
        # rotulo, o con rotulo de correccion/comparacion, son previsiones, desviaciones u otra cosa.
        bloques, actual = [], []
        for c in sorted(cavs):
            if actual and c != actual[-1] + 1:
                bloques.append(actual)
                actual = []
            actual.append(c)
        bloques.append(actual)
        columnas_valor = {}
        for i, bloque in enumerate(bloques):
            rotulo = str(filas.get(f0 - 1, {}).get(bloque[0], "")).strip()
            if i and (not rotulo or PREVISION.search(rotulo) or COMPARATIVA.search(rotulo) or re.search(r"deviat|desvia", rotulo, re.I)):
                descartadas["bloque secundario sin rotulo de condicion"] += len(bloque)
                continue
            for c in bloque:
                m = cavs[c]
                columnas_valor[c] = "c" + str(int(m.group(1))) + m.group(2) + (f"@{rotulo[:30]}" if rotulo and len(bloques) > 1 else "")
        plantilla = "interna"
    else:
        columnas_valor = {c: f"c{n}" for c, n in numeros.items() if c > col.get("nominal", 0)}
        plantilla = "interna_cav_numericas"
    c_cod = col.get("codigo")
    if c_cod is None:  # sin rotulo: la columna a la izquierda del nominal con mas codigos de cota
        candidatas = collections.Counter(
            c for f in filas if f > f0 for c, v in filas[f].items()
            if c < col.get("nominal", 99) and codigo_normal(v) and re.search(r"\d", str(v)))
        c_cod = min(candidatas, key=lambda c: (-candidatas[c], c)) if candidatas else 1
    cab_texto = " ".join(str(v) for fila in (f0 - 1, f0) for v in filas.get(fila, {}).values())
    etiquetas_cortas = [str(v).strip() for fila in (f0 - 1, f0) for v in filas.get(fila, {}).values() if len(str(v).strip()) <= 40]
    marcas_hoja = []
    if any(PREVISION.search(v) for v in etiquetas_cortas):
        marcas_hoja.append("con_correccion")
    if re.search(r" \(\d+\)$", hoja):
        marcas_hoja.append("copia")
    if COMPARATIVA.search(hoja):
        marcas_hoja.append("comparativa")
    if descartadas:
        marcas_hoja.append("bloques_secundarios")
    papel = ",".join(marcas_hoja) or "informe"
    res = {"plantilla": plantilla, "papel": papel, "fila_cabecera": f0, "columnas": col,
           "cavidades": sorted(set(columnas_valor.values())), "medidas": [], "filas_cota": 0,
           "cualitativos": 0, "rechazadas": collections.Counter(), "nok": [0, 0, 0, 0], "cabecera": cab_texto[:200],
           "ejemplos": {}, "columnas_descartadas": dict(descartadas)}

    def rechazar(motivo: str, f: int, fila: dict) -> None:
        res["rechazadas"][motivo] += 1
        if motivo not in res["ejemplos"]:
            res["ejemplos"][motivo] = [f] + [str(fila.get(c, ""))[:30] for c in sorted(fila)[:10]]
    cota = None
    for f in sorted(x for x in filas if x > f0):
        fila = filas[f]
        bruto = fila.get(c_cod, "")
        valores = {c: fila.get(c) for c in columnas_valor if str(fila.get(c, "")).strip()}
        if str(bruto).strip():
            cota = codigo_normal(bruto)
            if cota is None:
                texto = re.sub(r"\s+", " ", str(bruto)).strip()
                # Un nombre corto con nominal y valores es la cota («Distance 1», «POST 1»); sin
                # valores es un rotulo de seccion y corta la herencia del codigo.
                if valores and numero(fila.get(col.get("nominal"))) is not None and len(texto) <= 30:
                    cota = "~" + texto
                else:
                    if valores:
                        rechazar("codigo no reconocido", f, fila)
                    continue
        nominal = numero(fila.get(col.get("nominal")))
        if not valores:
            continue
        if cota is None:
            rechazar("sin codigo", f, fila)
            continue
        if nominal is None:
            res["cualitativos"] += len(valores)
            continue
        sup, inf = numero(fila.get(col.get("tol_sup"))), numero(fila.get(col.get("tol_inf")))
        if sup is not None and inf is not None and inf > sup:  # mismo intervalo, escrito al reves
            sup, inf = inf, sup
            res["rechazadas"]["tolerancias en orden inverso (corregidas)"] += 1
        res["filas_cota"] += 1
        fuera = False
        ancho = (sup - inf) if sup is not None and inf is not None and sup > inf else None
        for c, v in valores.items():
            x = numero(v)
            if x is None:
                res["cualitativos"] += 1
                continue
            marca = []
            if (f, c) in aleatorias:
                marca.append("aleatoria")
            if x == 0 and nominal != 0:
                marca.append("cero")
            elif ancho and abs(x - nominal) > 10 * ancho and abs(x - nominal) > 1:
                marca.append("atipico")
            if sup is not None and inf is not None and not marca and not (nominal + inf - 1e-9 <= x <= nominal + sup + 1e-9):
                fuera = True
            res["medidas"].append((f, c, cota, nominal, sup, inf, str(fila.get(col.get("equipo"), ""))[:40],
                                   columnas_valor[c], x, ",".join(marca) or None))
        if "nok" in col and sup is not None and inf is not None:
            marcado = str(fila.get(col["nok"], "")).strip().lower() in ("x", "nok", "1")
            res["nok"][2 * marcado + fuera] += 1  # [no y dentro, no y fuera, marcado y dentro, marcado y fuera]
    return res


def main() -> None:
    con = conectar()
    con.executescript(ESQUEMA)
    ejecucion = registrar(con, "lector_dr", {})
    candidatas = con.execute(
        "SELECT DISTINCT c.documento_id, c.hoja FROM celda c JOIN documento d ON d.id = c.documento_id "
        "WHERE d.ext IN ('xls','xlsx','xlsm') AND d.estado = 'extraido' AND c.fila <= 40 "
        "AND lower(trim(c.valor)) IN ('nominal','target','nom.','valor nominal')"
    ).fetchall()
    por_doc = collections.defaultdict(list)
    for d, h in candidatas:
        por_doc[d].append(h)
    total = collections.Counter()
    for d, hojas in por_doc.items():
        for h in hojas:
            celdas = {(f, c): v for f, c, v in con.execute(
                "SELECT fila, col, valor FROM celda WHERE documento_id=? AND hoja=?", (d, h))}
            aleatorias = {(f, c) for f, c in con.execute(
                "SELECT fila, col FROM celda_aleatoria WHERE documento_id=? AND hoja=?", (d, h))}
            r = leer_hoja(h, celdas, aleatorias)
            if r is None:
                total["hojas_sin_cabecera"] += 1
                continue
            marcas = collections.Counter(m[9] for m in r["medidas"] if m[9])
            if r["medidas"] and marcas.get("atipico", 0) > 0.3 * len(r["medidas"]) and "comparativa" not in r["papel"]:
                r["papel"] = ("" if r["papel"] == "informe" else r["papel"] + ",") + "sospechosa"
            if any("aleatoria" in k for k in marcas):
                r["papel"] = ("" if r["papel"] == "informe" else r["papel"] + ",") + "generada"
            con.execute("INSERT INTO lectura_dr VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                d, h, r["plantilla"], r["papel"], r["fila_cabecera"], json.dumps(r["columnas"]),
                json.dumps(r["cavidades"]), r["filas_cota"], len(r["medidas"]), r["cualitativos"],
                json.dumps(dict(r["rechazadas"]), ensure_ascii=False),
                sum(n for k, n in marcas.items() if "aleatoria" in k), marcas.get("cero", 0),
                marcas.get("atipico", 0), json.dumps(r["nok"]), json.dumps(r["ejemplos"], ensure_ascii=False),
                json.dumps(r["columnas_descartadas"], ensure_ascii=False)))
            con.executemany("INSERT INTO medida_dr VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            [(d, h, *m) for m in r["medidas"]])
            total["hojas"] += 1
            total["valores"] += len(r["medidas"])
        con.commit()
    cerrar_registro(con, ejecucion, dict(total))
    print(dict(total))


if __name__ == "__main__":
    main()
