"""Cadena correccion -> medicion: para cada cota citada en una diapositiva de correccion, las medidas del muestreo
de origen y del siguiente muestreo con valores nuevos (validacion), en la misma pieza y serie.

Tabla derivada `cadena_correccion` (se recalcula). Regla del piloto 3212 (historial-molde.md, §2), generalizada y
revisada el 28/10/2026 en dos rondas de revision externa:

- **Muestreo = serie + numero.** `3168-00_intern.01` y `3168-10_intern.01` son series distintas; la cadena no las
  cruza. Sin `-NN` en el nombre, serie `00`. Los `INF.NN` son entregas PPAP al cliente, no muestreos.
- **Origen**: el `intern.NN` del XLS de la carpeta del PPTX (`3212-00_intern.01_mold_correction.xls`). Si hay varios,
  el que lleva el numero del plan (`intern.09_correction04` es el plan 4) o el unico sin numero. Tambien vale el de una
  subcarpeta con el numero del plan (3309 `Mold Correction Loop 2/`). Si no hay, el ultimo muestreo con una copia
  fechada <= fecha de la correccion + 7 dias (`fuente_origen = 'fecha'`, aproximado: la fecha es de emision).
- **Fechas**: cada copia tiene la de su cabecera; sin ella, la de las demas copias del muestreo si coinciden (31 dias).
  Se usa la copia coherente con su papel (origen: no posterior a la correccion; validacion: no anterior) y se avisa si
  las copias de un muestreo tienen fechas distintas (3205/3206 `intern.17`: 04/2024 y 2025). Si la fecha del plan no
  cuadra con la de su XLS de origen (nombre heredado, I-302/I-306), se conserva en `fecha_correccion` y se avisa; si
  la carpeta tiene una fecha que si cuadra, se usa como **estimada** en `fecha_orden` (3186 loop 2: 21/04 del nombre,
  21/06 de la carpeta); si no, o si el plan no tiene fecha, el orden y la validez temporal de las copias quedan sin
  comprobar: ninguna copia se filtra ni se declara anterior o posterior (`admisible: null` en `alternativas`).
- **Orden**: sirve para detectar contradicciones, no para elegir otro origen. Si una correccion anterior de otro plan
  de la misma serie (origen por carpeta, no archivada en `Old/`, con fecha fiable) ya parte de un muestreo posterior al
  origen de esta, o igual o posterior a su validacion, el vinculo queda `indeterminada` (3167: el plan 3 de 06/2024
  saldria de Int_02 por fecha, y el plan 2 de 02/2024 ya parte de Int_03).
- **Validacion**: el siguiente muestreo de la serie, no anterior a la correccion, con alguna copia que no repita un
  muestreo anterior. La repeticion se mide con los valores utilizables (sin `RAND()`, ceros ni atipicos) alineando las
  filas de la cota por posicion y, si no, por contenido: misma cota, cavidades y muestras, y la misma etiqueta de
  elemento cuando la hay en los dos lados (LEFT/RIGHT). Una fila emparejada en otra posicion sin etiqueta cuenta si
  tiene al menos tres valores; cada fila se empareja una sola vez, con repeticiones (3186 cota 103: filas de
  intern.03 intercambiadas en el `intern.04` del cliente). Con menos valores, o si las etiquetas no casan, la
  comparacion es indeterminada. Un bloque de
  cavidades duplicado en columnas cuenta una vez (3212 `intern.02`). `validacion_estado`: `nueva`, `parcial` (repite
  parte de las filas), `herencia_indeterminada`, `indeterminada` (contradiccion de orden) o `sin_medidas_validas`
  (los informes posteriores solo traen valores excluidos, 3218 cota 2800).
- **Copias** del mismo muestreo (Interns, Customer…): se agrupan por valores, nominales y tolerancias; las distintas se
  guardan en `alternativas` y `depende_copia` = 1 si la conclusion (sube, baja o igual la proporcion de valores fuera;
  todo dentro o no) cambia segun la copia (I-006). Para decidir si un informe repite otro solo cuentan los valores: una
  tolerancia distinta no hace nueva una medida.
- **Valores**: `medida_dr` de hojas con papel `informe` en carpetas de metrologia. `*_evaluables` son los que tienen
  nominal y las dos tolerancias; `*_fuera` se cuenta sobre ellos. No incluye los CSV de la CMM (en el 3212 son la
  fuente preferente: trampas.md, 1).
- Cota sin medidas propias: se juntan sus subpuntos (`210` -> `210.1`…`210.5`). Cita ambigua de `perfil_correccion`
  (`DIM. Nr.45,1`): subpunto o lista segun lo que se mida en la pieza; si no se puede decidir, las dos lecturas, con
  aviso. Diapositiva con el mismo texto que otra pieza: aviso (I-309).

Muestra secuencia, no causa: que la cota cambie no prueba que la accion se ejecutara (I-401, I-204).

    python conocimiento/herramientas/cadena_correcciones.py [--pieza 3212]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import conectar  # noqa: E402

# Sin `INF`: es la numeracion de las entregas PPAP al cliente, no la de muestreos (3202 `PPAP-…_INF.01` es de 01/2024 y
# `intern.01` de 06/2023; en 7 piezas los numeros chocan).
# Dos cifras de muestreo; una tercera es la version del fichero: 3206 `intern.121` e `intern.122` son las versiones 1 y 2
# de intern.12 (la pieza numera hasta el 24 y en Exemples no hay muestreos de tres cifras).
MUESTREO = re.compile(r"(?i)(?:intern|int)[\s._-]*0*(\d{1,2})(\d)?(?!\d)")
SERIE = re.compile(r"(?<!\d)\d{4}[-_ ]?(\d{2})(?=[\s._-]*(?:intern|int)[\s._-]*\d)", re.I)
FECHA_TEXTO = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(20\d{2})(?!\d)")
FECHA_NOMBRE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
OTRA_PIEZA = re.compile(r"\bP(3\d{3})\b")
NUM_CORRECCION = re.compile(r"(?i)correcti?on[\s_-]*(?:plan|loop)?[\s_-]*0*(\d{1,2})(?!\d)")
ARCHIVADA = re.compile(r"(?i)(?:^|/)(?:old|obsolet\w*)(?:/|$)")
MARGEN_DIAS = 7       # la fecha del informe es de emision: 3212 intern.01 el 25/01 tras la correccion del 24/01
DISPERSION_DIAS = 31  # copias de un mismo muestreo con fechas mas separadas: no se sabe cual es la fecha del muestreo
MAX_CARPETA_DIAS = 180
EXCLUIDAS = {"aleatoria": "RAND() (I-003)", "cero": "cero (I-002)", "atipico": "atipico"}
ESTADO = {"nuevo": "nueva", "parcial": "parcial", "indeterminado": "herencia_indeterminada"}
PREFERENCIA = {"nuevo": 0, "parcial": 1, "indeterminado": 2}
FUERZA = {"igual": 3, "parcial": 2, "indeterminado": 1, "nuevo": 0}

COLUMNAS = [
    ("pieza", "TEXT"), ("documento_id", "INTEGER"), ("diapositiva", "INTEGER"), ("numero", "TEXT"), ("cota", "TEXT"),
    ("fecha_correccion", "TEXT"), ("fuente_fecha", "TEXT"), ("fecha_orden", "TEXT"), ("fuente_fecha_orden", "TEXT"),
    ("serie", "TEXT"),
    ("origen_muestreo", "INTEGER"), ("fuente_origen", "TEXT"), ("origen_documento_id", "INTEGER"), ("origen_fecha", "TEXT"),
    ("origen_n", "INTEGER"), ("origen_evaluables", "INTEGER"), ("origen_min", "REAL"), ("origen_max", "REAL"),
    ("origen_fuera", "INTEGER"),
    ("validacion_muestreo", "INTEGER"), ("validacion_documento_id", "INTEGER"), ("validacion_fecha", "TEXT"),
    ("validacion_n", "INTEGER"), ("validacion_evaluables", "INTEGER"), ("validacion_min", "REAL"),
    ("validacion_max", "REAL"), ("validacion_fuera", "INTEGER"), ("validacion_estado", "TEXT"),
    ("depende_copia", "INTEGER"), ("alternativas", "TEXT"),
    ("nominal", "REAL"), ("tol_sup", "REAL"), ("tol_inf", "REAL"), ("avisos", "TEXT"),
]
ESQUEMA = ("CREATE TABLE IF NOT EXISTS cadena_correccion (\n  "
           + ",\n  ".join(f"{nombre} {tipo}" for nombre, tipo in COLUMNAS)
           + ",\n  PRIMARY KEY (documento_id, diapositiva, cota)\n);\n")


def fecha_valida(texto) -> date | None:
    try:
        f = date.fromisoformat(str(texto)[:10])
    except ValueError:
        return None
    return f if 2015 <= f.year <= 2027 else None   # 1899-12-31 y textos (I-304) quedan fuera


def fecha_correccion(texto: str, ruta: str) -> tuple[date | None, str | None]:
    for m in FECHA_TEXTO.finditer(texto or ""):
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))), "diapositiva"
        except ValueError:
            continue
    partes = PurePosixPath(ruta).parts
    for fuente, parte in (("nombre", partes[-1]), *(("carpeta", p) for p in reversed(partes[:-1]))):
        m = FECHA_NOMBRE.search(parte)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), fuente
            except ValueError:
                continue
    return None, None


def fecha_de_carpeta(ruta: str) -> date | None:
    for parte in reversed(PurePosixPath(ruta).parts[:-1]):
        m = FECHA_NOMBRE.search(parte)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def fecha_de_nombre(ruta: str) -> date | None:
    m = FECHA_NOMBRE.search(PurePosixPath(ruta).name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def serie_de(nombre: str) -> str:
    m = SERIE.search(nombre)
    return m.group(1) if m else "00"


def etiqueta(muestreo: tuple[str, int]) -> str:
    serie, n = muestreo
    return f"intern.{n:02d}" if serie == "00" else f"intern.{n:02d} (serie {serie})"


def firma(celdas: list[tuple[int, str | None, float]]) -> tuple:
    """Valores de una fila agrupados por muestra: la k-esima aparicion de una cavidad es su muestra k. Una muestra
    identica a la anterior cuenta una vez (3212 `intern.02`: el bloque c13-c16 repetido en las columnas 12-15)."""
    muestras: list[list] = []
    vistas: Counter = Counter()
    for col, cavidad, valor in celdas:
        clave = cavidad or f"col{col}"
        k = vistas[clave]
        vistas[clave] += 1
        while len(muestras) <= k:
            muestras.append([])
        muestras[k].append((clave, round(valor, 6)))
    unicas = [m for i, m in enumerate(muestras) if i == 0 or m != muestras[i - 1]]
    return tuple(x for m in unicas for x in m)


def etiquetas_de_elemento(con, pieza: str) -> dict[tuple[int, str, int], str]:
    """(documento, hoja, fila) -> texto entre la columna del codigo y la del nominal, sin la del tipo (`LEFT`, `RIGHT`,
    numero de elemento). Es la identificacion del elemento cuando el informe la trae."""
    disposicion = {(doc, hoja): json.loads(columnas or "{}") for doc, hoja, columnas in con.execute(
        "SELECT l.documento_id, l.hoja, l.columnas FROM lectura_dr l JOIN documento d ON d.id = l.documento_id "
        "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' AND l.papel = 'informe'", (pieza,))}
    partes: dict = defaultdict(list)
    for doc, hoja, fila, col, valor in con.execute(
            "SELECT ce.documento_id, ce.hoja, ce.fila, ce.col, ce.valor FROM celda ce "
            "JOIN lectura_dr l ON l.documento_id = ce.documento_id AND l.hoja = ce.hoja "
            "JOIN documento d ON d.id = ce.documento_id WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' "
            "AND l.papel = 'informe' AND ce.col BETWEEN 2 AND 9 ORDER BY ce.col", (pieza,)):
        cols = disposicion.get((doc, hoja), {})
        codigo, nominal, tipo = cols.get("codigo") or 0, cols.get("nominal"), cols.get("tipo")
        if nominal and codigo < col < nominal and col != tipo and str(valor or "").strip():
            partes[(doc, hoja, fila)].append(str(valor).strip().casefold())
    return {k: " ".join(v) for k, v in partes.items()}


def cargar(con, pieza: str) -> tuple[dict, dict]:
    """cota -> (serie, n) -> [copias]; y (serie, n) -> {fechas: [(fecha, copia)], consenso}."""
    fechas_doc: dict = defaultdict(list)
    for doc, meta in con.execute("SELECT p.documento_id, p.metadatos FROM perfil_ppap p JOIN documento d ON d.id = p.documento_id "
                                 "WHERE d.codigo = ?", (pieza,)):
        f = fecha_valida(json.loads(meta or "{}").get("report_date"))
        if f:
            fechas_doc[doc].append(f)
    etiquetas = etiquetas_de_elemento(con, pieza)
    filas = con.execute(
        "SELECT d.id, d.nombre, d.ruta, m.cota, m.hoja, m.fila, m.col, m.cavidad, m.valor, m.nominal, m.tol_sup, "
        "m.tol_inf, m.marca FROM medida_dr m JOIN documento d ON d.id = m.documento_id "
        "JOIN lectura_dr l ON l.documento_id = m.documento_id AND l.hoja = m.hoja "
        "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' AND l.papel = 'informe' "
        "ORDER BY d.id, m.cota, m.hoja, m.fila, m.col", (pieza,)).fetchall()
    por_doc: dict = {}
    for doc, nombre, ruta, cota, hoja, fila, col, cavidad, valor, nominal, tsup, tinf, marca in filas:
        if not MUESTREO.search(nombre):
            continue
        c = por_doc.setdefault((doc, cota), {"documento": doc, "nombre": nombre,
                                             "copia": f"{PurePosixPath(ruta).parent.name}/{nombre}",
                                             "celdas": defaultdict(list), "filas": [], "excluidas": Counter(),
                                             "nominales": set()})
        # RAND (I-003), ceros (I-002) y atipicos de lector_dr no entran en las cifras ni en la comparacion; se avisan.
        if marca in EXCLUIDAS:
            c["excluidas"][marca] += 1
            continue
        c["celdas"][(hoja, fila)].append((col, cavidad, valor, (nominal, tsup, tinf)))
        c["filas"].append((valor, nominal, tsup, tinf))
        if nominal is not None:
            c["nominales"].add(nominal)
    copias: dict = defaultdict(lambda: defaultdict(list))
    muestreos: dict = defaultdict(lambda: {"fechas": set(), "consenso": None})
    for (doc, cota), c in por_doc.items():
        numero = MUESTREO.search(c["nombre"])
        clave = (serie_de(c["nombre"]), int(numero.group(1)))
        c["version"] = numero.group(2)
        c["fecha_propia"] = min(fechas_doc[doc]) if fechas_doc.get(doc) else None
        celdas = sorted(c.pop("celdas").items())
        c["elementos"] = [(cota, etiquetas.get((doc, hoja, fila)), firma([x[:3] for x in cs]), tuple(x[3] for x in cs))
                          for (hoja, fila), cs in celdas]
        c["nominales"] = sorted(c["nominales"])
        copias[cota][clave].append(c)
        for f in fechas_doc.get(doc, []):
            muestreos[clave]["fechas"].add((f, c["copia"]))
    for info in muestreos.values():
        dias = sorted(f for f, _ in info["fechas"])
        info["consenso"] = dias[0] if dias and (dias[-1] - dias[0]).days <= DISPERSION_DIAS else None
    for por_muestreo in copias.values():
        for clave, lista in por_muestreo.items():
            for c in lista:
                c["fecha"] = c["fecha_propia"] or muestreos[clave]["consenso"]
    return copias, muestreos


def comparar(b: dict, a: dict, tolerancias: bool = False) -> tuple[str, int, int, int]:
    """(veredicto, filas de b emparejadas en a, filas de b, emparejadas en otra posicion): igual, parcial, nuevo o
    indeterminado. Con `tolerancias`, tambien nominal y tolerancias de cada valor (para agrupar copias equivalentes)."""
    eb, ea = b["elementos"], a["elementos"]
    if not eb:
        return "nuevo", 0, 0, 0

    def clave(e):
        return (e[0], e[2], e[3]) if tolerancias else (e[0], e[2])

    def compatibles(x, y):
        return clave(x) == clave(y) and (x[1] is None or y[1] is None or x[1] == y[1])

    usadas, iguales, reordenadas, dudosas, conflicto = set(), 0, 0, 0, False
    pendientes = list(range(len(eb)))
    if len(eb) == len(ea) and all(x[0] == y[0] and len(x[2]) == len(y[2]) for x, y in zip(eb, ea)):
        pendientes = []
        for i, (x, y) in enumerate(zip(eb, ea)):   # misma estructura: elemento a elemento
            if compatibles(x, y):
                usadas.add(i)
                iguales += 1
            else:
                pendientes.append(i)
    for i in pendientes:   # filas desplazadas, reordenadas u hojas de mas
        x = eb[i]
        candidatas = [j for j, y in enumerate(ea) if j not in usadas and clave(y) == clave(x)]
        if not candidatas:
            continue
        misma = [j for j in candidatas if x[1] is not None and ea[j][1] == x[1]]
        sin_etiqueta = [j for j in candidatas if x[1] is None or ea[j][1] is None]
        if misma:
            j = misma[0]
        elif sin_etiqueta:
            # Sin etiqueta, una fila completa en otra posicion solo cuenta con tres valores o mas (cada uno con su
            # cavidad y muestra); cada fila de `a` se usa una vez, asi que una fila repetida tiene que estar repetida
            # en las dos copias. Con menos valores, la correspondencia es dudosa.
            if len(x[2]) < 3:
                dudosas += 1
                continue
            j = sin_etiqueta[0]
        else:
            conflicto = True                 # los mismos valores con otra etiqueta (LEFT frente a RIGHT)
            continue
        usadas.add(j)
        iguales += 1
        reordenadas += 1
    if conflicto or dudosas:
        return "indeterminado", iguales, len(eb), reordenadas
    return ("igual" if iguales == len(eb) else "nuevo" if iguales == 0 else "parcial"), iguales, len(eb), reordenadas


def herencia(c: dict, muestreo: tuple[str, int], por_muestreo: dict) -> tuple[str, tuple | None, int, int, int]:
    """La relacion mas fuerte de la copia con cualquier copia de un muestreo anterior de la misma serie."""
    mejor: tuple = ("nuevo", None, 0, len(c["elementos"]), 0)
    for clave, otras in sorted(por_muestreo.items(), key=lambda x: -x[0][1]):   # ante empate, el mas reciente
        if clave[0] != muestreo[0] or clave[1] >= muestreo[1]:
            continue
        for a in otras:
            if not a["elementos"]:
                continue
            veredicto, iguales, total, reordenadas = comparar(c, a)
            if FUERZA[veredicto] > FUERZA[mejor[0]] or (veredicto == mejor[0] == "parcial" and iguales > mejor[2]):
                mejor = (veredicto, clave, iguales, total, reordenadas)
    return mejor


def metricas(c: dict | None) -> dict | None:
    if not c:
        return None
    valores = [f[0] for f in c["filas"]]
    evaluables = [f for f in c["filas"] if None not in f[1:]]
    return {"n": len(valores), "evaluables": len(evaluables),
            "fuera": sum(1 for v, nom, sup, inf in evaluables if v > nom + sup + 1e-9 or v < nom + inf - 1e-9),
            "min": min(valores) if valores else None, "max": max(valores) if valores else None}


def conclusion(mo: dict | None, mv: dict | None) -> tuple | None:
    """Sube, baja o igual la proporcion de valores fuera, y si todo queda dentro."""
    if not mo or not mv or not mo["evaluables"] or not mv["evaluables"]:
        return None
    po, pv = mo["fuera"] / mo["evaluables"], mv["fuera"] / mv["evaluables"]
    return (pv > po + 1e-9) - (pv < po - 1e-9), mv["fuera"] == 0


def distintas(copias: list[dict]) -> list[list[dict]]:
    """Copias agrupadas por contenido equivalente: mismos valores, nominales y tolerancias, en los dos sentidos."""
    grupos: list[list[dict]] = []
    for c in copias:
        for g in grupos:
            if comparar(c, g[0], True)[0] == "igual" and comparar(g[0], c, True)[0] == "igual":
                g.append(c)
                break
        else:
            grupos.append([c])
    return grupos


def mas_completa(copias: list[dict], limite: date | None = None) -> dict:
    """La de mas valores; con `limite`, antes las fechadas no despues de el (o sin fecha)."""
    def coherente(c):
        return limite is None or c["fecha"] is None or (c["fecha"] - limite).days <= MARGEN_DIAS
    return max(copias, key=lambda c: (coherente(c), len(c["filas"]), -c["documento"]))


def numeros_de_plan(ruta: str, plan: str | None) -> set[int]:
    numeros = {int(plan)} if plan and plan.isdigit() else set()
    m = NUM_CORRECCION.search(PurePosixPath(ruta).name)
    if m:
        numeros.add(int(m.group(1)))
    return numeros


def origen_por_carpeta(con, ruta: str, pieza: str, plan: str | None) -> tuple[tuple[str, int] | None, bool]:
    """(muestreo, si lo fija el numero de plan del XLS). Sin numero, el XLS de la carpeta vale para cualquier plan."""
    carpeta = PurePosixPath(ruta).parent
    planes = numeros_de_plan(ruta, plan)
    candidatos, en_subcarpeta = {}, {}   # muestreo -> numero de correccion del nombre (o None)
    for otra, nombre in con.execute("SELECT ruta, nombre FROM documento WHERE codigo = ? AND ext IN ('xls','xlsx','xlsm')",
                                    (pieza,)):
        m = MUESTREO.search(nombre)
        if not m:
            continue
        c = NUM_CORRECCION.search(nombre)
        numero = int(c.group(1)) if c else None
        clave = (serie_de(nombre), int(m.group(1)))
        if PurePosixPath(otra).parent == carpeta:   # misma carpeta (2N/Old/ no cuenta para 2N/)...
            candidatos[clave] = numero
        elif PurePosixPath(otra).parent.parent == carpeta and numero in planes:
            # ...salvo una subcarpeta con el numero del plan: 3309 `Mold Correction Loop 2/…Int_02_mold correction loop 2.xls`
            en_subcarpeta[clave] = numero
    if len(en_subcarpeta) == 1 and not any(c in planes for c in candidatos.values()):
        return next(iter(en_subcarpeta)), True
    if len(candidatos) <= 1:
        k = next(iter(candidatos), None)
        return k, k is not None and candidatos[k] is not None
    del_plan = [k for k, c in candidatos.items() if plan and plan.isdigit() and c == int(plan)]
    sin_numero = [k for k, c in candidatos.items() if c is None]
    return (del_plan[0], True) if len(del_plan) == 1 else (sin_numero[0], False) if len(sin_numero) == 1 else (None, False)


def planes_de_la_pieza(con, pieza: str, filas, muestreos: dict) -> dict[int, dict]:
    """Por documento de correccion: fecha (la menor de sus diapositivas) y su fuente, fecha para ordenar, carpeta,
    numeros de plan y origen por carpeta."""
    planes: dict = {}
    for doc, _, _, _, texto, ruta, plan, _ in filas:
        fecha, fuente = fecha_correccion(texto, ruta)
        d = planes.setdefault(doc, {"ruta": ruta, "plan": plan, "fecha": fecha, "fuente": fuente, "diapositiva": None})
        if fecha and (d["fecha"] is None or fecha < d["fecha"]):
            d["fecha"], d["fuente"] = fecha, fuente
        if fuente == "diapositiva" and (d["diapositiva"] is None or fecha < d["diapositiva"]):
            d["diapositiva"] = fecha
    for d in planes.values():
        # Todas las fechas candidatas del plan, para que el aviso conserve las discrepancias y sus fuentes.
        d["candidatas"] = [(fuente, f) for fuente, f in (("diapositiva", d["diapositiva"]),
                                                         ("nombre", fecha_de_nombre(d["ruta"])),
                                                         ("carpeta", fecha_de_carpeta(d["ruta"]))) if f]
        d["origen"], d["por_numero"] = origen_por_carpeta(con, d["ruta"], pieza, d["plan"])
        d["numeros"] = numeros_de_plan(d["ruta"], d["plan"])
        d["archivada"] = bool(ARCHIVADA.search(d["ruta"]))
        fechas_xls = sorted(f for f, _ in muestreos.get(d["origen"], {}).get("fechas", ())) if d["origen"] else []

        def cuadra(f):
            return not fechas_xls or any((x - f).days <= MARGEN_DIAS for x in fechas_xls)

        d["fecha_orden"], d["fuente_orden"], d["fiable"], d["aviso_fecha"] = d["fecha"], d["fuente"], bool(d["fecha"]), None
        if not d["fecha"]:
            d["aviso_fecha"] = ("sin fecha de la correccion (ni en diapositivas, nombre o carpeta): orden y validez "
                                "temporal de las copias sin comprobar")
        elif not cuadra(d["fecha"]):
            # Nombre heredado (3186 loop 2, 3218 loop 1 «P3174», 3195 N2 «2020»): la fecha no sirve para ordenar.
            carpeta = fecha_de_carpeta(d["ruta"])
            base = (f"fecha de la correccion no fiable: {d['fecha'].isoformat()} ({d['fuente']}) es anterior en mas de "
                    f"{MARGEN_DIAS} dias a su XLS de origen {etiqueta(d['origen'])} ({fechas_xls[0].isoformat()})")
            if carpeta and carpeta != d["fecha"] and cuadra(carpeta) and \
                    (carpeta - fechas_xls[0]).days <= MAX_CARPETA_DIAS:
                d["fecha_orden"], d["fuente_orden"] = carpeta, "carpeta (estimada)"
                d["aviso_fecha"] = f"{base}; para ordenar se usa la de la carpeta, {carpeta.isoformat()}, estimada"
            else:
                d["fiable"] = False
                candidatas = ", ".join(f"{fuente} {f.isoformat()}" for fuente, f in d["candidatas"])
                d["aviso_fecha"] = (f"{base}; fechas candidatas: {candidatas}; orden y validez temporal de las copias "
                                    "sin comprobar")
    return planes


def limite_de_orden(doc: int, planes: dict, serie: str) -> dict | None:
    """La correccion anterior, de otro plan y misma serie, con el origen por carpeta mas alto."""
    d = planes[doc]
    if not d["fiable"] or not d["fecha_orden"]:
        return None
    carpeta = PurePosixPath(d["ruta"]).parent

    def mismo_plan(o):   # versiones del mismo plan en la misma carpeta (`v1`, `rev2`, `_results`)
        return PurePosixPath(o["ruta"]).parent == carpeta and (bool(o["numeros"] & d["numeros"])
                                                               or not (o["numeros"] or d["numeros"]))

    previos = [o for k, o in planes.items() if k != doc and o["origen"] and o["origen"][0] == serie and o["fiable"]
               and o["fecha_orden"] and not o["archivada"] and o["fecha_orden"] < d["fecha_orden"] and not mismo_plan(o)]
    return max(previos, key=lambda o: o["origen"][1], default=None)


def agregar_subpuntos(copias: dict, cota: str) -> tuple[dict, list[str]]:
    """Sin medidas de la cota pero si de sus subpuntos (3174: `DIM. Nr.210` se mide como 210.1 … 210.5): se juntan."""
    claves = sorted(k for k in copias if k.startswith(cota + "."))
    junta: dict = defaultdict(dict)
    for k in claves:
        for muestreo, lista in copias[k].items():
            for c in lista:
                j = junta[muestreo].setdefault(c["documento"], {
                    "documento": c["documento"], "nombre": c["nombre"], "copia": c["copia"], "fecha": c["fecha"],
                    "fecha_propia": c["fecha_propia"], "version": c["version"], "elementos": [], "filas": [],
                    "excluidas": Counter(),
                    "nominales": set()})
                j["elementos"] += c["elementos"]
                j["filas"] += c["filas"]
                j["excluidas"].update(c["excluidas"])
                j["nominales"].update(c["nominales"])
    resultado = {m: [dict(j, nominales=sorted(j["nominales"])) for j in docs.values()] for m, docs in junta.items()}
    return resultado, claves


def resolver_ambigua(cita: dict, medidas: set[str]) -> list[tuple[str, list[str]]]:
    """`DIM. Nr.45,1`: subpunto si se mide 45.1 y no toda la lista; lista si al reves; si no, las dos lecturas."""
    literal, lista, sub = cita["literal"], cita["lista"], cita["subpunto"]
    tiene_sub, tiene_lista = sub in medidas, all(c in medidas for c in lista)
    if tiene_sub and not tiene_lista:
        return [(sub, [f"cita «{literal}» leida como subpunto {sub}: se mide {sub} y no {' y '.join(lista)}"])]
    if tiene_lista and not tiene_sub:
        return [(c, [f"cita «{literal}» leida como lista {', '.join(lista)}: no se mide {sub}"]) for c in lista]
    aviso = f"cita ambigua «{literal}»: lista ({', '.join(lista)}) o subpunto {sub}; las medidas no lo deciden"
    return [(c, [aviso]) for c in [*lista, sub]]


def textos_de_otras_piezas(con) -> dict[str, set[tuple[str, str, int]]]:
    """Texto normalizado de diapositiva -> {(pieza, fichero, diapositiva)}, para avisar de copias entre piezas (I-309)."""
    textos = defaultdict(set)
    for pieza, ruta, diap, texto in con.execute("SELECT substr(pieza, 1, 4), ruta, diapositiva, texto FROM perfil_correccion"):
        t = re.sub(r"\s+", " ", texto or "").strip().casefold()
        if len(t) > 60:   # titulos y diapositivas casi vacias se repiten sin significar nada
            textos[t].add((pieza, PurePosixPath(ruta).name, diap))
    return textos


def preparar_tabla(con) -> bool:
    """Crea la tabla; si existe con otras columnas (version anterior), la borra. Devuelve si la ha recreado."""
    actuales = [c[1] for c in con.execute("PRAGMA table_info(cadena_correccion)")]
    recreada = bool(actuales) and actuales != [nombre for nombre, _ in COLUMNAS]
    if recreada:
        con.execute("DROP TABLE cadena_correccion")
    con.executescript(ESQUEMA)
    return recreada


def resumen_excluidas(copias: list[dict]) -> str:
    total = Counter()
    for c in copias:
        total.update(c["excluidas"])
    return ", ".join(f"{k} {EXCLUIDAS[marca]}" for marca, k in sorted(total.items())) or "sin valores"


def fechas_dispersas(muestreo: tuple, muestreos: dict) -> str | None:
    fechas = sorted(muestreos.get(muestreo, {}).get("fechas", ()))
    if fechas and (fechas[-1][0] - fechas[0][0]).days > DISPERSION_DIAS:
        extremos = [fechas[0], fechas[-1]]
        return (f"copias de {etiqueta(muestreo)} con fechas distintas ({len(fechas)} fechas de cabecera): de "
                + " a ".join(f"{f.isoformat()} ({copia})" for f, copia in extremos))
    return None


def fila_cadena(p, doc, diap, numero, cota, fecha, fuente_fecha, plan_doc, planes, copias, muestreos, avisos) -> tuple:
    por_muestreo = copias.get(cota, {})
    if not por_muestreo:
        por_muestreo, subpuntos = agregar_subpuntos(copias, cota)
        if por_muestreo:
            avisos.append(f"sin medidas de la cota {cota}; se juntan sus subpuntos {', '.join(subpuntos)}")
    if not por_muestreo:
        avisos.append("sin medidas de esta cota en informes XLS de metrologia de la pieza")
    if plan_doc["aviso_fecha"]:
        avisos.append(plan_doc["aviso_fecha"])
    estimada = plan_doc["fuente_orden"] == "carpeta (estimada)"
    fecha_orden, fuente_orden = (plan_doc["fecha_orden"], plan_doc["fuente_orden"]) if estimada else (fecha, fuente_fecha)

    def viables(muestreo):
        return [c for c in por_muestreo.get(muestreo, []) if c["filas"]]

    por_carpeta = plan_doc["origen"]
    origen, fuente = (por_carpeta, "xls_carpeta") if por_carpeta in por_muestreo else (None, None)
    if por_carpeta is not None and por_carpeta not in por_muestreo:
        avisos.append(f"el XLS de la carpeta indica {etiqueta(por_carpeta)}, sin medidas de esta cota")
    if origen is None and fecha_orden:
        candidatos = {}
        for k in por_muestreo:
            fechas = [c["fecha"] for c in viables(k) if c["fecha"] and (c["fecha"] - fecha_orden).days <= MARGEN_DIAS]
            if fechas:
                candidatos[k] = max(fechas)
        if candidatos:
            origen, fuente = max(candidatos, key=lambda k: (candidatos[k], k[1])), "fecha"

    estado = None
    limite = limite_de_orden(doc, planes, origen[0]) if origen else None
    if origen and limite and limite["origen"][1] > origen[1]:
        avisos.append(f"contradiccion de orden: {PurePosixPath(limite['ruta']).name} ({limite['fecha_orden'].isoformat()}) "
                      f"ya parte de {etiqueta(limite['origen'])} y esta correccion es posterior, pero su origen seria "
                      f"{etiqueta(origen)}: origen y validacion indeterminados")
        origen, fuente, estado = None, None, "indeterminada"

    copias_origen = viables(origen) if origen else []
    if origen and not copias_origen:
        avisos.append(f"origen {etiqueta(origen)} sin medidas validas ({resumen_excluidas(por_muestreo[origen])})")
    # Con fecha del plan fiable (o estimada de la carpeta) se comprueba el tiempo en origen y validacion. Si no es fiable o
    # no hay fecha (3205: diapositiva 21/03/2024, nombre 11/04/2024, informes del 05/04/2024), ninguna copia se filtra ni
    # se declara anterior o posterior: validez temporal sin comprobar.
    temporal = plan_doc["fiable"] and fecha_orden is not None
    sin_comprobar = ("sin fecha de la correccion: validez temporal sin comprobar" if fecha_orden is None else
                     "fecha de la correccion no fiable: validez temporal sin comprobar")
    # Las mismas copias para elegir el origen y para depende_copia: las no posteriores a la correccion (3174 cota 210:
    # la copia del cliente de intern.26 es del 18/03/2025 y la correccion del 14/02/2025). Si no hay ninguna, todas,
    # sin darlas por validas en el tiempo.
    admisibles = [c for c in copias_origen if c["fecha"] is None
                  or (c["fecha"] - fecha_orden).days <= MARGEN_DIAS] if temporal else []
    base_origen = admisibles or copias_origen
    descartadas = [c for c in copias_origen if c not in base_origen]
    if temporal and copias_origen and not admisibles:
        avisos.append(f"ninguna copia de origen es anterior a la correccion: se comparan todas ({len(copias_origen)}), "
                      "sin validez temporal")
    co = mas_completa(base_origen) if base_origen else None
    if temporal and co and co["fecha"] and (co["fecha"] - fecha_orden).days > MARGEN_DIAS:
        avisos.append(f"la copia de origen {co['copia']} es del {co['fecha'].isoformat()}, posterior a la correccion")

    validacion, elegida, vivas, saltados, sin_validas = None, None, [], [], False
    if origen:
        for muestreo in sorted(k for k in por_muestreo if k[0] == origen[0] and k[1] > origen[1]):
            lista = viables(muestreo)
            if not lista:
                saltados.append(f"{etiqueta(muestreo)} sin medidas validas ({resumen_excluidas(por_muestreo[muestreo])})")
                sin_validas = True
                continue
            # 3195: int_02 (16/10/2023) es anterior al plan 1 (31/10/2023), no puede validarlo.
            posteriores = [c for c in lista if not (c["fecha"] and c["fecha"] < fecha_orden)] if temporal else lista
            if not posteriores:
                saltados.append(f"{etiqueta(muestreo)} anterior a la correccion "
                                f"({min(c['fecha'] for c in lista).isoformat()})")
                continue
            relaciones = [(c, herencia(c, muestreo, por_muestreo)) for c in posteriores]
            vivas = [(c, h) for c, h in relaciones if h[0] != "igual"]
            if not vivas:
                # Heredado (I-001): 3212 N170 de .02 repite las filas de .01; N265 de .04 las de .01, no las de .03.
                reordenadas = [c["copia"] for c, h in relaciones if h[4]]
                saltados.append(f"{etiqueta(muestreo)} = {etiqueta(relaciones[0][1][1])}"
                                + (f" (filas reordenadas en {', '.join(reordenadas)})" if reordenadas else ""))
                continue
            elegida, (veredicto, previo, iguales, total, _) = min(
                vivas, key=lambda x: (PREFERENCIA[x[1][0]], -len(x[0]["filas"]), x[0]["documento"]))
            validacion, estado = muestreo, ESTADO[veredicto]
            if veredicto == "parcial":
                avisos.append(f"{etiqueta(muestreo)} repite {iguales} de {total} filas de {etiqueta(previo)} (I-001)")
            elif veredicto == "indeterminado":
                avisos.append(f"{etiqueta(muestreo)}: no se puede establecer la correspondencia de sus filas con las de "
                              "muestreos anteriores (orden, etiquetas o filas de pocos valores); no se sabe si repite valores")
            repetidas = [(c, h) for c, h in relaciones if h[0] == "igual"]
            if repetidas:
                avisos.append(f"{etiqueta(muestreo)}: la copia {', '.join(c['copia'] for c, _ in repetidas)} repite "
                              f"{etiqueta(repetidas[0][1][1])}"
                              + (" con las filas reordenadas" if any(h[4] for _, h in repetidas) else "")
                              + f" (I-006); se usa {elegida['copia']}")
            if len(posteriores) < len(lista):
                avisos.append(f"{etiqueta(muestreo)}: copias fechadas antes de la correccion, no se usan")
            if temporal and elegida["fecha"] is None:
                avisos.append(f"{etiqueta(muestreo)} sin fecha de informe valida: no se puede comprobar que sea "
                              "posterior a la correccion")
            break
        if validacion and limite and validacion[1] <= limite["origen"][1]:
            avisos.append(f"contradiccion de orden: {PurePosixPath(limite['ruta']).name} "
                          f"({limite['fecha_orden'].isoformat()}) ya parte de {etiqueta(limite['origen'])}; la validacion "
                          f"{etiqueta(validacion)} no es posterior: validacion indeterminada")
            validacion, elegida, vivas, estado = None, None, [], "indeterminada"
        if validacion is None and estado is None and sin_validas:
            estado = "sin_medidas_validas"
    if saltados:
        avisos.append("muestreos saltados (repiten valores de uno anterior, I-001, sin medidas validas o anteriores a la "
                      "correccion): " + "; ".join(saltados))
    for papel, muestreo in (("origen", origen), ("validacion", validacion)):
        dispersas = muestreo and fechas_dispersas(muestreo, muestreos)
        if dispersas:
            avisos.append(f"{papel}: {dispersas}")

    mo, mv = metricas(co), metricas(elegida)
    grupos_o = distintas(base_origen)
    grupos_v = distintas([c for c, _ in vivas]) if elegida else []
    alternativas, depende = [], 0
    if len(grupos_o) > 1 or len(grupos_v) > 1 or descartadas:
        motivo_todas = "ninguna copia de origen es anterior a la correccion; se compara sin validez temporal"
        for papel, grupos, usada in (("origen", grupos_o, co), ("validacion", grupos_v, elegida)):
            for g in grupos:
                # admisible: True (comprobada), False (comprobada y fuera de plazo) o None (sin comprobar).
                if not temporal:
                    admisible, motivo = None, sin_comprobar
                elif papel == "origen" and not admisibles:
                    admisible, motivo = False, motivo_todas
                else:
                    admisible, motivo = True, None
                alternativas.append({"papel": papel, "copias": [c["copia"] for c in g], "elegida": usada in g,
                                     "admisible": admisible, **({"motivo": motivo} if motivo else {}),
                                     **metricas(g[0])})
        for g in distintas(descartadas):   # evidencia que se conserva, pero no entra en la conclusion
            alternativas.append({"papel": "origen", "copias": [c["copia"] for c in g], "elegida": False,
                                 "admisible": False, "motivo": f"posterior a la correccion ({g[0]['fecha'].isoformat()})",
                                 **metricas(g[0])})
        conclusiones = {conclusion(metricas(a[0]), metricas(b[0])) for a in grupos_o for b in (grupos_v or [[None]])}
        depende = int(len(conclusiones - {None}) > 1)
        detalle = "; ".join(f"{a['papel']} {', '.join(a['copias'])}: {a['fuera']}/{a['evaluables']} fuera"
                            + ("" if a["admisible"] else f" ({a['motivo']})") for a in alternativas)
        avisos.append("copias del mismo muestreo con valores o tolerancias distintos (I-006)"
                      + (", la conclusion depende de la copia" if depende else "") + f": {detalle}")
    for papel, c, m, muestreo in (("origen", co, mo, origen), ("validacion", elegida, mv, validacion)):
        if not c:
            continue
        if c.get("version"):
            avisos.append(f"{papel}: {c['copia']} se lee como version {c['version']} de {etiqueta(muestreo)}")
        if c["excluidas"]:
            avisos.append(f"{papel}: excluidos " + ", ".join(f"{k} {EXCLUIDAS[marca]}"
                                                             for marca, k in sorted(c["excluidas"].items())))
        if m["n"] > m["evaluables"]:
            avisos.append(f"{papel}: {m['n'] - m['evaluables']} de {m['n']} valores sin nominal o tolerancia completa, "
                          "no se evaluan")
        if len(c["nominales"]) > 1:
            avisos.append(f"{papel}: la cota tiene filas con nominales distintos {c['nominales']}; min/max mezclan "
                          "elementos, *_fuera compara cada valor con el suyo")

    con_valores = [x for lista in por_muestreo.values() for x in lista if x["filas"]]
    ref_copia = co or elegida or (mas_completa(con_valores) if con_valores else None)
    ref = next((f[1:] for f in ref_copia["filas"]), None) if ref_copia else None
    return (p, doc, diap, numero, cota, fecha.isoformat() if fecha else None, fuente_fecha,
            fecha_orden.isoformat() if fecha_orden else None, fuente_orden, origen[0] if origen else None,
            origen[1] if origen else None, fuente, co and co["documento"], co and co["fecha"] and co["fecha"].isoformat(),
            mo and mo["n"], mo and mo["evaluables"], mo and mo["min"], mo and mo["max"], mo and mo["fuera"],
            validacion[1] if validacion else None, elegida and elegida["documento"],
            elegida and elegida["fecha"] and elegida["fecha"].isoformat(),
            mv and mv["n"], mv and mv["evaluables"], mv and mv["min"], mv and mv["max"], mv and mv["fuera"], estado,
            depende, json.dumps(alternativas, ensure_ascii=False) if alternativas else None,
            ref and ref[0], ref and ref[1], ref and ref[2], json.dumps(avisos, ensure_ascii=False))


def construir(con, pieza: str | None) -> int:
    if preparar_tabla(con) and pieza:
        pieza = None   # tabla de una version anterior: se rehace entera
    con.execute("DELETE FROM cadena_correccion" + (" WHERE pieza = ?" if pieza else ""), (pieza,) if pieza else ())
    ambiguas = ("coalesce(cotas_ambiguas, '[]')" if "cotas_ambiguas" in
                {c[1] for c in con.execute("PRAGMA table_info(perfil_correccion)")} else "'[]'")
    con_citas = f"(cotas NOT IN ('[]', '') OR {ambiguas} NOT IN ('[]', ''))"
    piezas = [pieza] if pieza else [r[0] for r in con.execute(
        f"SELECT DISTINCT substr(pieza, 1, 4) FROM perfil_correccion WHERE {con_citas}")]
    insertar = (f"INSERT OR REPLACE INTO cadena_correccion ({', '.join(n for n, _ in COLUMNAS)}) "
                f"VALUES ({', '.join('?' * len(COLUMNAS))})")
    total = 0
    textos = textos_de_otras_piezas(con)
    for p in piezas:
        copias, muestreos = cargar(con, p)
        filas = con.execute(
            f"SELECT documento_id, diapositiva, numero, cotas, texto, ruta, plan, {ambiguas} FROM perfil_correccion "
            f"WHERE substr(pieza, 1, 4) = ? AND {con_citas}", (p,)).fetchall()
        planes = planes_de_la_pieza(con, p, filas, muestreos)
        medidas = set(copias)
        for doc, diap, numero, cotas, texto, ruta, plan, citas_ambiguas in filas:
            fecha, fuente_fecha = fecha_correccion(texto, ruta)
            otras = sorted({c for c in OTRA_PIEZA.findall(texto or "") if c != p})
            copias_texto = sorted(f"{nombre} d{d} (pieza {pz})" for pz, nombre, d in
                                  textos.get(re.sub(r"\s+", " ", texto or "").strip().casefold(), ()) if pz != p)
            citadas = [(c, []) for c in json.loads(cotas or "[]") if c != "XX"]
            for cita in json.loads(citas_ambiguas or "[]"):
                if cita.get("tipo") == "lista_o_subpunto":
                    citadas += resolver_ambigua(cita, medidas)
            for cota, avisos_cita in citadas:
                avisos = [f"el texto nombra otra pieza: P{', P'.join(otras)}"] if otras else []
                if copias_texto:
                    avisos.append("diapositiva identica a otra pieza (I-309), puede no ser de esta: "
                                  + "; ".join(copias_texto[:3]))
                avisos += avisos_cita
                con.execute(insertar, fila_cadena(p, doc, diap, numero, cota, fecha, fuente_fecha, planes[doc], planes,
                                                  copias, muestreos, avisos))
                total += 1
    con.commit()
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pieza")
    args = ap.parse_args()
    con = conectar()
    n = construir(con, args.pieza)
    print(f"Filas de cadena_correccion: {n}")


if __name__ == "__main__":
    main()
