"""Evolución de una cota: un valor por cavidad y muestreo, para la gráfica de líneas de la ficha de pieza.

Una cota, un muestreo y una cavidad pueden tener varios valores (I-008). Se elige primero qué se mira, pestaña y
elemento, y lo que aún queda se resuelve con estas reglas, acordadas el 06/11/2026 y documentadas en
`conocimiento/valores-por-punto.md`. Ninguna decide en silencio: el punto lleva su procedencia y sus avisos.

- Falta la pestaña elegida: se usa otra del mismo muestreo con el mismo elemento, y el punto se dibuja hueco.
- Filas sin rótulo: cada una es un elemento propio (`fila 1`, `fila 2`).
- La misma fila en dos bloques de la hoja: el último, salvo que el CSV de la CMM diga otra cosa.
- Varias piezas de una cavidad: la media, rotulada como media.
- Copias que discrepan: la de `Interns`; si no hay, la de nombre más corto.
- Muestreo con los mismos valores que otro anterior: se dibuja y se marca. No se da por erróneo.
- CSV de la CMM de ese muestreo: manda sobre el Excel en las filas de CMM. Cargados el 3212 y el 3197 (09/11/2026), sin condición
  de proceso; la comparativa «totes» solo donde no hay export individual (`csv_de`). Solo con correspondencia segura: mismo número
  de elementos en la hoja que filas en el CSV y calificadores compatibles (`fila_csv`); si no, el Excel y un aviso.

    python evolucion.py --resumen   # qué dibuja, pieza a pieza, con la selección por defecto
"""

from __future__ import annotations

import json
import re
import sys
import threading
from collections import Counter, defaultdict
from functools import lru_cache

import datos
from valores_por_punto import cargar

TOLERANCIA_CSV = .0015  # el Excel puede redondear a menos decimales que el CSV
HOJA_CSV = "CSV de la CMM"
# Versión de una corrección con texto distinto entre copias, solo donde está documentada. Fuente: 3212/5-retoques-molde.md#qué-fichero-usar
VERSION_DOCUMENTADA = {"3212": ("/5- Retoques de molde/20240124-Mold correction_1_P3212_rev1.pptx", "/5- Retoques de molde/2N/20240318-Mold correction_2_P3212_rev1.pptx")}
SIN_TEXTO = re.compile(r"^(Tool correction|Correcci[oó]n?\b|Longitud|Current situation|\d+\s*/\s*\d+$|\d+$|OK$)", re.I)
ESTADOS = {"nueva": "valores nuevos", "parcial": "repite parte de los valores", "indeterminada": "orden contradictorio",
           "herencia_indeterminada": "no se sabe si repite valores", "sin_medidas_validas": "sin medidas válidas"}


def coma(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def etiqueta_muestreo(serie: str, n: int) -> str:
    return f"intern.{n:02d}" + ("" if serie == "00" else f" ({serie})")


def clave_natural(texto: str) -> list:
    return [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.findall(r"\d+|\D+", texto or "")]


def celda(fila: int, col: int) -> str:
    letras = ""
    while col:
        col, resto = divmod(col - 1, 26)
        letras = chr(65 + resto) + letras
    return f"{letras}{fila}"


def limites(tolerancia: tuple) -> list | None:
    nominal, sup, inf = tolerancia
    if nominal is None or sup is None or inf is None:
        return None
    return [round(nominal + inf, 6), round(nominal + sup, 6)]


def calificadores(texto: str | None) -> dict:
    """Lo que distingue dos medidas de la misma cota y nominal: extremo, ajuste y altura o posición.

    Excel (rótulo y comentario: `MAX`, `GG`, `H=-8.5 mm`) y título del bloque del CSV (`(Max-Value ...)`, `(GG)`, `X=-4,5`,
    `in height 4mm`). Las alturas se comparan en valor absoluto: el Excel escribe `H=-4.5` donde el CSV dice `X=-4,5`."""
    t = re.sub(r"min-zone", "", (texto or "").casefold()).replace(",", ".")
    salida: dict = {}
    extremos = set(re.findall(r"(?<![a-z])(min|max)(?:imum|-value)?(?![a-z])", t))  # también «BOLT 1MIN/MAX» (3212)
    if len(extremos) == 1:
        salida["extremo"] = extremos.pop()
    ajustes = set(re.findall(r"\b(gg|gn|gx|gc|lp|ls)\b", t))
    if len(ajustes) == 1:
        salida["ajuste"] = ajustes.pop()
    posiciones = re.findall(r"\b[hx]\s*=\s*(-?\d+(?:\.\d+)?)", t) + re.findall(r"height\s*(\d+(?:\.\d+)?)\s*mm", t)
    if posiciones:
        salida["posicion"] = frozenset(abs(float(x)) for x in posiciones)
    return salida


def compatibles(a: dict, b: dict) -> bool:
    """Ninguna característica que digan los dos lados se contradice."""
    return all(a[k] == b[k] for k in a.keys() & b.keys())


def calificadores_excel(x: dict) -> dict:
    etiqueta, tipo, _, _, comentario = x["identidad"]  # el `MAX` o `GG` del Excel va en el tipo
    return calificadores(f"{etiqueta or ''} {tipo or ''} {comentario or ''}")


def elementos_de_hoja(filas: list[dict]) -> dict:
    """Elementos de CMM distintos (identidad y orden) por libro, hoja, cavidad y nominal, en el orden de su primera fila.

    Toda la hoja, no cada bloque: una cota medida a dos alturas en dos zonas son dos elementos (3197 `intern.05`, cotas 550
    y 560), y el CSV solo se cruza por posición si trae tantas filas como elementos hay."""
    primera: dict = defaultdict(dict)
    for x in filas:
        if x["elemento"][3].startswith("cmm"):
            e = (x["identidad"], x["orden"])
            d = primera[(x["doc"], x["hoja"], x["cavidad"], x["identidad"][2])]
            d[e] = min(d.get(e, x["fila"]), x["fila"])
    return {k: sorted(d, key=d.get) for k, d in primera.items()}


def fila_csv(ref: list | None, lista: list, e: tuple, cal: dict) -> dict | None:
    """La fila del CSV que es este elemento: misma posición, mismo número de elementos y calificadores compatibles."""
    if not ref or len(lista) != len(ref) or e not in lista:
        return None
    r = ref[lista.index(e)]
    return r if compatibles(cal, calificadores(r.get("bloque"))) else None


def preparar(filas: list[dict]) -> list[dict]:
    """Da a cada valor su `clave` de elemento. La posición entre filas iguales del mismo bloque la distingue."""
    iguales: dict = defaultdict(set)
    for x in filas:
        etiqueta, tipo, (nominal, _, _), equipo, comentario = x["elemento"]
        x["identidad"] = (etiqueta, tipo, None if nominal is None else round(nominal, 6), equipo, comentario)
        iguales[(x["doc"], x["hoja"], x["bloque"], x["identidad"])].add(x["fila"])
    posicion = {clave: {f: i for i, f in enumerate(sorted(lista), 1)} for clave, lista in iguales.items()}
    for x in filas:
        grupo = posicion[(x["doc"], x["hoja"], x["bloque"], x["identidad"])]
        x["orden"], x["varias"] = grupo[x["fila"]], len(grupo) > 1
        x["clave"] = json.dumps([*x["identidad"], x["orden"]], ensure_ascii=False)
        x["cavidad"] = re.sub(r"\.m\d+$", "", x["cav"] or "?")  # las muestras de una cavidad son la misma línea
    return filas


def nombre_elemento(x: dict, con_fila: bool, con_nominal: bool) -> str:
    etiqueta, tipo, nominal, equipo, comentario = x["identidad"]
    partes = [p for p in (etiqueta, tipo) if p]
    if con_nominal and nominal is not None:
        partes.append(coma(nominal))
    if equipo:
        partes.append(equipo.upper())
    comentario = re.sub(r"\b(false|true)\b", "", comentario).strip()  # casillas de verificación del Excel
    if comentario:
        partes.append(comentario[:40])
    if con_fila:
        partes.append(f"fila {x['orden']}")
    return " · ".join(partes) or "sin rótulo"


def prioridad_copia(nombre: str, ruta: str) -> tuple:
    return ("/interns/" not in ruta.casefold(), len(nombre), nombre, ruta)


def origen_de(x: dict) -> dict:
    partes = x["ruta"].split("/")
    return {"fichero": x["nombre"], "carpeta": partes[-2] if len(partes) > 1 else "", "hoja": x["hoja"],
            "celda": celda(x["fila"], x["col"])}


def punto(lineas: list[dict], ref: list | None, pestana: str, elementos: dict) -> dict:
    """Un punto a partir de las filas candidatas de una pestaña: copia, bloque, muestra y CSV, por este orden."""
    copias: dict = defaultdict(list)
    for x in lineas:
        copias[(x["doc"], x["nombre"], x["ruta"])].append(x)
    orden = sorted(copias, key=lambda k: prioridad_copia(k[1], k[2]))
    elegida = copias[orden[0]]
    ultimo = max(x["bloque"] for x in elegida)
    del_bloque = [x for x in elegida if x["bloque"] == ultimo]
    valores = [x["valor"] for x in del_bloque]
    valor = sum(valores) / len(valores)
    base = del_bloque[0]
    hueco = base["hoja"] != pestana
    p = {"v": round(valor, 6), **origen_de(base), "hueco": hueco, "fecha": base.get("fecha"), "media": None,
         "repite": None, "csv": None, "lim": limites(base["elemento"][2]), "info": []}
    avisos = []
    if len(set(valores)) > 1:  # columnas idénticas son un bloque duplicado, no varias piezas
        p["media"] = len(valores)
        avisos.append(f"Media de {len(valores)} piezas de esta cavidad: " + " · ".join(coma(v) for v in valores))
    for fila, v in sorted({(x["fila"], x["valor"]) for x in elegida if x["bloque"] != ultimo}):
        if v not in valores:
            avisos.append(f"También {coma(v)} en la fila {fila} de esta pestaña; se usa el último bloque.")
    ya_vistos = {x["valor"] for x in elegida}
    for k in orden[1:]:
        distintos = sorted({x["valor"] for x in copias[k]} - ya_vistos)
        if distintos:
            avisos.append(f"Otra copia ({k[2].split('/')[-2]}/{k[1]}) da {' · '.join(coma(v) for v in distintos)}.")
    if ref and base["elemento"][3].startswith("cmm"):
        cal = calificadores_excel(base)
        lista = elementos.get((base["doc"], base["hoja"], base["cavidad"], base["identidad"][2]), [])
        r = fila_csv(ref, lista, (base["identidad"], base["orden"]), cal)
        if r:
            p["csv"] = {"fichero": r["nombre"], "carpeta": r["carpeta"], "linea": r["fila"], "columna": r.get("columna")}
            if abs(r["valor"] - valor) > TOLERANCIA_CSV:
                avisos.insert(0, f"CSV de la CMM: {coma(r['valor'])}; el Excel dice {coma(valor)}. Se usa el CSV.")
                p["v"], p["hueco"] = r["valor"], False
        else:  # sin correspondencia segura, el CSV solo confirma un valor igual de la misma medida
            r = next((r for r in ref if abs(r["valor"] - valor) <= TOLERANCIA_CSV
                      and compatibles(cal, calificadores(r.get("bloque")))), None)
            if r:
                p["csv"] = {"fichero": r["nombre"], "carpeta": r["carpeta"], "linea": r["fila"], "columna": r.get("columna")}
            else:
                avisos.append("Este muestreo tiene CSV de la CMM, pero esta fila no se ha podido cruzar con él.")
    if p["hueco"]:
        avisos.insert(0, f"El informe no tiene la pestaña «{pestana}»: valor de «{base['hoja']}».")
    p["avisos"] = avisos
    return p


def solo_csv(ref: list | None, posicion: int | None) -> dict | None:
    if not ref or posicion is None:
        return None
    r = ref[posicion]
    celda = f"línea {r['fila']}" + (f", columna {r['columna']}" if r.get("columna") else "")
    return {"v": r["valor"], "fichero": r["nombre"], "carpeta": r["carpeta"], "hoja": HOJA_CSV, "celda": celda,
            "hueco": False, "fecha": None, "media": None, "repite": None, "lim": r["lim"],
            "csv": {"fichero": r["nombre"], "carpeta": r["carpeta"], "linea": r["fila"], "columna": r.get("columna")},
            "avisos": ["El Excel de este muestreo no trae esta fila: valor del CSV de la CMM."], "info": []}


def _lista(items: list[str], n: int = 3) -> str:
    return ", ".join(items[:n]) + (f" y {len(items) - n} más" if len(items) > n else "")


def marcar_coincidencias(puntos: dict, muestreos: list, etiquetas: list, minimo: int = 2) -> None:
    """V1 (11/11/2026), solo información: cavidades de un muestreo con el mismo valor que en uno anterior de su serie,
    cuando no son todas (eso ya es `repite`). Se cita el muestreo anterior con más coincidencias, desde `minimo`
    cavidades: una sola coincide a menudo por azar. No se interpreta como copia ni como error.
    Igual que `marcar_repetidos`, no cuenta los valores del CSV, que es la medida de su muestreo."""
    for i, (serie, _) in enumerate(muestreos):
        presentes = {c: lista[i] for c, lista in puntos.items() if lista[i] and not lista[i]["csv"]}
        if len(presentes) <= minimo or any(p["repite"] for p in presentes.values()):
            continue
        mejor: list = []
        mejor_j = None
        for j in range(i):
            if muestreos[j][0] != serie:
                continue
            iguales = [c for c, p in presentes.items()
                       if puntos[c][j] and not puntos[c][j]["csv"] and round(puntos[c][j]["v"], 6) == round(p["v"], 6)]
            if len(iguales) >= len(mejor):  # empate: el más reciente
                mejor, mejor_j = iguales, j
        if mejor_j is None or len(mejor) < minimo or len(mejor) == len(presentes):
            continue
        texto = (f"Mismo valor que en {etiquetas[mejor_j]} en {len(mejor)} de {len(presentes)} cavidades de este muestreo "
                 f"({_lista(mejor, 6)}).")
        for c in mejor:
            presentes[c]["info"].append(texto)


def anotar_fechas(salida: dict, fechas: dict, codigo: str, componente: str | None) -> None:
    """V2 (11/11/2026), solo información: otras fechas de cabecera del muestreo del punto, separando las de otras hojas
    del mismo archivo y las de otros archivos (copias). `fechas` sale de `datos.fechas_de_muestreos`."""
    for cav, lista in salida["puntos"].items():
        for m, p in zip(salida["muestreos"], lista):
            if not p or p["hoja"] == HOJA_CSV:
                continue
            propia = p["fecha"] if p["fecha"] and datos._FECHA_ISO.fullmatch(p["fecha"]) else None
            hojas: dict = defaultdict(list)
            archivos: dict = defaultdict(list)
            for x in fechas.get((m["serie"], m["n"]), []):
                if x["fecha"] == propia or (componente and datos.componente_de_nombre(codigo, x["hoja"]) not in (None, componente)):
                    continue
                if (x["carpeta"], x["fichero"]) == (p["carpeta"], p["fichero"]):
                    if x["hoja"] != p["hoja"]:
                        hojas[x["fecha"]].append(f"«{x['hoja']}»")
                else:
                    nombre = f"{x['carpeta']}/{x['fichero']}"
                    if nombre not in archivos[x["fecha"]]:
                        archivos[x["fecha"]].append(nombre)
            if hojas:
                p["info"].append("Otras hojas de este archivo tienen otra fecha: "
                                 + "; ".join(f"{f} ({_lista(h)})" for f, h in sorted(hojas.items())) + ".")
            if archivos:
                p["info"].append("Otros archivos de este muestreo tienen otra fecha: "
                                 + "; ".join(f"{f} ({_lista(a, 2)})" for f, a in sorted(archivos.items())) + ".")


def marcar_repetidos(puntos: dict, muestreos: list, etiquetas: list) -> None:
    """Muestreo con exactamente los mismos valores que uno anterior de su serie; se cita el primero que los tuvo.
    Un muestreo con CSV sí sirve de comparación, pero no se marca: el CSV es la medida de ese muestreo."""
    huellas: list = []
    for i, (serie, _) in enumerate(muestreos):
        presentes = {c: lista[i] for c, lista in puntos.items() if lista[i]}
        huella = tuple(sorted((c, round(p["v"], 6)) for c, p in presentes.items()))
        anterior = next((j for j in range(i) if huellas[j] == huella and muestreos[j][0] == serie), None) if huella else None
        huellas.append(huella)
        if anterior is not None and not any(p["csv"] for p in presentes.values()):
            for p in presentes.values():
                p["repite"] = etiquetas[anterior]
                p["avisos"].append(f"Mismos valores que {etiquetas[anterior]}. No sabemos si se volvió a medir.")


def excluidos_de(filas: list[dict], elemento: str | None = None) -> list[dict]:
    """Valores que no se dibujan, con su motivo. Sin elemento, los de toda la cota."""
    return [{"muestreo": etiqueta_muestreo(x["serie"], x["n"]), "cavidad": x["cavidad"], "valor": x["valor"],
             "motivo": datos.EXCLUIDAS[x["marca"]], **origen_de(x)}
            for x in sorted(filas, key=lambda y: (y["serie"], y["n"], y["fila"], y["col"]))
            if x["marca"] in datos.EXCLUIDAS and (elemento is None or x["clave"] == elemento)]


def construir(filas: list[dict], csv: dict | None = None, pestana: str | None = None, elemento: str | None = None) -> dict:
    """Lo que dibuja la gráfica para una cota. Sin acceso a la base: `filas` sale de `cargar` y `csv` de `csv_de`.

    Si un libro mezcla dos piezas (3288), `filas` trae solo las de una: así nunca se rellenan entre sí."""
    csv = csv or {}
    preparar(filas)
    validas = [x for x in filas if x["marca"] not in datos.EXCLUIDAS]
    muestreos_cota = sorted({(x["serie"], x["n"]) for x in validas})
    por_hoja: dict = defaultdict(set)
    for x in validas:
        por_hoja[x["hoja"]].add((x["serie"], x["n"]))
    hojas = sorted(por_hoja, key=lambda h: (-len(por_hoja[h]), clave_natural(h)))
    if pestana not in por_hoja:
        pestana = hojas[0] if hojas else None
    cobertura: dict = defaultdict(set)
    primera_fila: dict = {}
    ejemplo: dict = {}
    for x in validas:
        if x["hoja"] == pestana:
            cobertura[x["clave"]].add((x["serie"], x["n"]))
            primera_fila[x["clave"]] = min(primera_fila.get(x["clave"], x["fila"]), x["fila"])
            ejemplo.setdefault(x["clave"], x)
    elementos = sorted(cobertura, key=lambda k: primera_fila[k])
    if elemento not in cobertura:
        elemento = max(elementos, key=lambda k: (len(cobertura[k]), -primera_fila[k])) if elementos else None
    con_nominal = len({x["identidad"][2] for x in ejemplo.values()}) > 1
    salida = {
        "hojas": [{"hoja": h, "muestreos": len(por_hoja[h])} for h in hojas], "hoja": pestana, "elemento": elemento,
        "elementos": [{"id": k, "etiqueta": nombre_elemento(ejemplo[k], ejemplo[k]["varias"], con_nominal), "muestreos": len(cobertura[k])} for k in elementos],
        "muestreos": [], "cavidades": [], "puntos": {}, "banda": None, "tolerancia_cambia": False, "sin_elemento": [],
        "excluidos": [], "tramos": [], "resumen": {},
    }
    if not elemento:  # sin nada que dibujar, los valores excluidos y sus motivos siguen a la vista
        salida["excluidos"] = excluidos_de(filas)
        return salida

    candidatas = [x for x in validas if x["clave"] == elemento]
    por_muestreo: dict = defaultdict(list)
    for x in candidatas:
        por_muestreo[(x["serie"], x["n"])].append(x)
    orden_hojas = {h: i for i, h in enumerate(hojas)}

    # El CSV se cruza por posición entre los elementos de CMM de la hoja con la misma nominal, si cuadra su número y
    # los calificadores (extremo, ajuste, altura) no se contradicen.
    elementos_cmm = elementos_de_hoja(validas)
    nominal = ejemplo[elemento]["identidad"][2]
    es_cmm = ejemplo[elemento]["elemento"][3].startswith("cmm")
    cal_elemento = calificadores_excel(ejemplo[elemento])
    posiciones: dict = {}
    for x in candidatas if es_cmm else ():
        lista = elementos_cmm.get((x["doc"], x["hoja"], x["cavidad"], x["identidad"][2]), [])
        e = (x["identidad"], x["orden"])
        if e in lista:
            posiciones.setdefault((x["cavidad"], len(lista)), lista.index(e))

    def relleno(ref: list | None, cav: str) -> dict | None:
        """Muestreo sin fila en el Excel: la fila del CSV en la misma posición, si es inequívoca y compatible."""
        i = posiciones.get((cav, len(ref))) if ref else None
        if i is None or not compatibles(cal_elemento, calificadores(ref[i].get("bloque"))):
            return None
        return solo_csv(ref, i)

    solo_en_csv = {k for k, lista in csv.items() if es_cmm and k[3] == nominal and relleno(lista, k[2])}

    muestreos = sorted(set(por_muestreo) | {k[:2] for k in solo_en_csv})
    cavidades = sorted({x["cavidad"] for x in candidatas} | {k[2] for k in solo_en_csv}, key=clave_natural)
    puntos: dict = {c: [] for c in cavidades}
    for m in muestreos:
        lineas = por_muestreo.get(m, [])
        hojas_aqui = sorted({x["hoja"] for x in lineas}, key=orden_hojas.get)
        for cav in cavidades:
            ref = csv.get((*m, cav, nominal)) if es_cmm else None
            de_cav = [x for x in lineas if x["cavidad"] == cav]
            hoja = pestana if any(x["hoja"] == pestana for x in de_cav) else next((h for h in hojas_aqui if any(x["hoja"] == h for x in de_cav)), None)
            if hoja is None:
                puntos[cav].append(relleno(ref, cav))
            else:
                puntos[cav].append(punto([x for x in de_cav if x["hoja"] == hoja], ref, pestana, elementos_cmm))

    etiquetas = [etiqueta_muestreo(*m) for m in muestreos]
    marcar_repetidos(puntos, muestreos, etiquetas)
    marcar_coincidencias(puntos, muestreos, etiquetas)
    todos = [p for lista in puntos.values() for p in lista if p]
    rangos = {tuple(p["lim"]) for p in todos if p["lim"]}
    if len(rangos) == 1:
        inf, sup = next(iter(rangos))
        salida["banda"] = {"inf": inf, "sup": sup}
    salida["tolerancia_cambia"] = len(rangos) > 1
    salida["muestreos"] = [{"id": f"{s}/{n:02d}", "serie": s, "n": n, "etiqueta": e} for (s, n), e in zip(muestreos, etiquetas)]
    salida["cavidades"], salida["puntos"] = cavidades, puntos
    salida["sin_elemento"] = [etiqueta_muestreo(*m) for m in muestreos_cota if m not in set(muestreos)]
    salida["excluidos"] = excluidos_de(filas, elemento)
    salida["tramos"] = [{"id": f"{a['id']}-{b['id']}", "de": i, "a": i + 1, "correcciones": []}
                        for i, (a, b) in enumerate(zip(salida["muestreos"], salida["muestreos"][1:])) if a["serie"] == b["serie"]]
    salida["resumen"] = {"puntos": len(todos), "huecos": sum(p["hueco"] for p in todos), "repetidos": sum(bool(p["repite"]) for p in todos),
                         "medias": sum(bool(p["media"]) for p in todos), "csv": sum(bool(p["csv"]) for p in todos),
                         "otro_valor": sum(any(a.startswith(("También", "Otra copia", "CSV de")) for a in p["avisos"]) for p in todos)}
    return salida


def columnas(c, tabla: str) -> set:
    return {r[1] for r in c.execute(f"PRAGMA table_info({tabla})")}


def csv_de(c, codigo: str, cota: str) -> dict:
    """Evaluaciones de la CMM de una cota, por muestreo, cavidad y nominal, en el orden del fichero.

    Solo exportes sin condición (`variante` vacía): una medida a 135 ºC/500 bar, a ciclo 24 o con la boquilla a 55 ºC no es
    la de la pestaña de esa cavidad. La comparativa «totes» solo entra donde el muestreo y la cavidad no tienen export
    individual (3197 `intern.09`-`.11`); donde hay los dos, coinciden en valor y cota (09/11/2026)."""
    salida: dict = defaultdict(list)
    sin_condicion = " AND m.variante IS NULL" if "variante" in columnas(c, "medida_cmm") else ""
    for f in c.execute("SELECT d.nombre, d.ruta, m.muestreo, m.cavidad, m.fila, m.bloque, m.nominal, m.tol_sup, m.tol_inf, m.valor"
                       " FROM medida_cmm m JOIN documento d ON d.id = m.documento_id WHERE m.pieza = ? AND m.cota = ? AND m.valor IS NOT NULL"
                       + sin_condicion + " ORDER BY m.muestreo, m.cavidad, m.fila", (codigo, cota)):
        nominal = None if f["nominal"] is None else round(f["nominal"], 6)
        salida[("00", int(f["muestreo"]), (f["cavidad"] or "").casefold(), nominal)].append({
            "nombre": f["nombre"], "carpeta": f["ruta"].split("/")[-2], "fila": f["fila"], "bloque": f["bloque"], "valor": f["valor"],
            "lim": limites((f["nominal"], f["tol_sup"], f["tol_inf"]))})
    if not columnas(c, "medida_cmm_comparativa"):
        return dict(salida)
    individuales = {(m, (cav or "").casefold()) for m, cav in c.execute(
        "SELECT DISTINCT muestreo, cavidad FROM medida_cmm WHERE pieza = ?" + sin_condicion.replace("m.", ""), (codigo,))}
    for f in c.execute("SELECT d.nombre, d.ruta, m.muestreo, m.cavidad, m.fila, m.rotulo, m.bloque, m.nominal, m.tol_sup, m.tol_inf, m.valor"
                       " FROM medida_cmm_comparativa m JOIN documento d ON d.id = m.documento_id WHERE m.pieza = ? AND m.cota = ?"
                       " AND m.valor IS NOT NULL AND m.variante IS NULL ORDER BY m.muestreo, m.cavidad, m.fila", (codigo, cota)):
        if (f["muestreo"], (f["cavidad"] or "").casefold()) in individuales:
            continue
        nominal = None if f["nominal"] is None else round(f["nominal"], 6)
        salida[("00", int(f["muestreo"]), (f["cavidad"] or "").casefold(), nominal)].append({
            "nombre": f["nombre"], "carpeta": f["ruta"].split("/")[-2], "fila": f["fila"], "columna": f["rotulo"], "bloque": f["bloque"], "valor": f["valor"],
            "lim": limites((f["nominal"], f["tol_sup"], f["tol_inf"]))})
    return dict(salida)


def parrafos(texto: str) -> list[str]:
    """El texto de la propuesta, sin el título, la plantilla ni la numeración de la diapositiva. Mismo criterio que la app."""
    lineas = [re.sub(r"\s+", " ", x.replace("", "→")).strip() for x in (texto or "").splitlines()]
    return [x for x in lineas if x and not SIN_TEXTO.match(x)]


def agrupar_correcciones(pasos: list[dict]) -> list[dict]:
    """Una acción por número de corrección, con todas sus variantes y sin perder ningún fichero ni diapositiva.

    Solo comparten variante las copias de una acción con número, en ficheros distintos y con el mismo texto no vacío.
    Sin número no se sabe si dos diapositivas son la misma acción, y en un mismo fichero dos diapositivas no son copias:
    aunque el texto coincida, no se juntan. Ninguna variante se oculta; `preferente` solo sale de lo documentado."""
    acciones: dict = {}
    for i, f in enumerate(pasos):
        clave = (f["numero"], f["serie"], f["origen"], f["validacion"], f["componente"]) if f["numero"] else ("sin número", i)
        a = acciones.setdefault(clave, {k: f[k] for k in ("numero", "fecha", "serie", "origen", "validacion", "componente")} | {"variantes": []})
        copia = {"pptx": f["pptx"], "carpeta": f["carpeta"], "diapositiva": f["diapositiva"], "documento": f["documento"]}
        v = next((v for v in a["variantes"] if f["texto"] and v["texto"] == f["texto"]
                  and all(x["documento"] != f["documento"] for x in v["copias"])), None)
        if v is None:
            a["variantes"].append({"texto": f["texto"], "fecha": f["fecha"], "estado": f["estado"], "avisos": list(f["avisos"]),
                                   "preferente": f["preferente"], "copias": [copia]})
        else:
            v["copias"].append(copia)
            v["preferente"] = v["preferente"] or f["preferente"]
            v["avisos"] += [x for x in f["avisos"] if x not in v["avisos"]]
    for a in acciones.values():
        a["variantes"].sort(key=lambda v: not v["preferente"])  # estable: el resto sigue en el orden de los documentos
        a["textos_distintos"] = len({tuple(v["texto"]) for v in a["variantes"]}) > 1
    return list(acciones.values())


def correcciones(c, codigo: str, cota: str) -> list[dict]:
    """Las correcciones de `cadena_correccion` para una cota, con el texto de cada diapositiva."""
    pasos = []
    documentadas = VERSION_DOCUMENTADA.get(codigo, ())
    for f in c.execute("SELECT ca.*, d.nombre AS pptx, d.ruta AS ruta_pptx FROM cadena_correccion ca JOIN documento d ON d.id = ca.documento_id"
                       " WHERE ca.pieza = ? AND ca.cota = ? ORDER BY ca.fecha_orden, ca.numero, d.ruta, ca.diapositiva", (codigo, cota)):
        texto = c.execute("SELECT texto FROM elemento WHERE documento_id = ? AND tipo = 'diapositiva' AND localizador = ?",
                          (f["documento_id"], f"diapositiva {f['diapositiva']}")).fetchone()
        pasos.append({"numero": f["numero"], "fecha": f["fecha_correccion"], "serie": f["serie"] or "00", "origen": f["origen_muestreo"],
                      "validacion": f["validacion_muestreo"], "estado": ESTADOS.get(f["validacion_estado"], f["validacion_estado"]),
                      "pptx": f["pptx"], "carpeta": f["ruta_pptx"].split("/")[-2], "documento": f["documento_id"], "diapositiva": f["diapositiva"],
                      "avisos": json.loads(f["avisos"] or "[]"), "texto": parrafos(texto["texto"] if texto else ""),
                      "preferente": f["ruta_pptx"].endswith(tuple(documentadas)) if documentadas else False,
                      "componente": datos.componente_de_nombre(codigo, f["pptx"])})
    return agrupar_correcciones(pasos)


def asociar_correcciones(salida: dict, lista: list[dict]) -> None:
    """Un tramo muestra las correcciones que parten de él o que se validan en él. Secuencia, no causa."""
    salida["correcciones"] = lista
    for t in salida["tramos"]:
        a, b = salida["muestreos"][t["de"]], salida["muestreos"][t["a"]]
        t["correcciones"] = [i for i, x in enumerate(lista) if x["serie"] == a["serie"] and (
            (x["origen"] is not None and a["n"] <= x["origen"] < b["n"]) or (x["validacion"] is not None and a["n"] < x["validacion"] <= b["n"]))]
    enlazadas = {i for t in salida["tramos"] for i in t["correcciones"]}
    salida["correcciones_sin_tramo"] = len(lista) - len(enlazadas)


@lru_cache(maxsize=64)
def _datos_cota(codigo: str, cota: str) -> tuple:
    c = datos.con()
    fechas = datos.fechas_por_hoja(c, codigo)  # la de su hoja, sin recortar (V3, 11/11/2026)
    filas = cargar(c, codigo, cota, excluidas=True)
    for x in filas:
        x["fecha"] = fechas.get((x["doc"], x["hoja"]), fechas.get(x["doc"]))
    return tuple(filas), csv_de(c, codigo, cota), tuple(correcciones(c, codigo, cota))


def resumen_csv(codigo: str, cota: str) -> dict | None:
    """Evaluaciones de la CMM de la cota que entran en la gráfica (las de `csv_de`), y en cuántos ficheros.

    None si de la pieza no hay ningún CSV leído: «no leídos» no es lo mismo que «sin medidas de esta cota».
    """
    c = datos.con()
    if not columnas(c, "medida_cmm") or not c.execute("SELECT 1 FROM medida_cmm WHERE pieza = ? LIMIT 1", (codigo,)).fetchone():
        return None
    puntos = [p for lista in _datos_cota(codigo, cota)[1].values() for p in lista]
    return {"medidas": len(puntos), "ficheros": len({p["nombre"] for p in puntos})}


def cotas_csv(c, codigo: str) -> set:
    """Cotas con evaluaciones de la CMM que entran en la gráfica: el mismo criterio que `csv_de`, por cota."""
    if not columnas(c, "medida_cmm"):
        return set()
    sin_condicion = " AND variante IS NULL" if "variante" in columnas(c, "medida_cmm") else ""
    cotas = {f[0] for f in c.execute("SELECT DISTINCT cota FROM medida_cmm WHERE pieza = ? AND valor IS NOT NULL" + sin_condicion, (codigo,))}
    if columnas(c, "medida_cmm_comparativa"):
        individuales = {(m, (cav or "").casefold()) for m, cav in c.execute(
            "SELECT DISTINCT muestreo, cavidad FROM medida_cmm WHERE pieza = ?" + sin_condicion, (codigo,))}
        cotas |= {cota for cota, m, cav in c.execute(
            "SELECT DISTINCT cota, muestreo, cavidad FROM medida_cmm_comparativa WHERE pieza = ? AND valor IS NOT NULL AND variante IS NULL",
            (codigo,)) if (m, (cav or "").casefold()) not in individuales}
    cotas.discard(None)
    return cotas


@lru_cache(maxsize=64)
def cotas_con_datos(codigo: str, componente: str | None = None) -> dict:
    """Cotas de la pieza con algo en su ficha del plano: medidas de los informes, del CSV de la CMM o corrección.

    Las mismas fuentes que las tres líneas de la ficha; con `componente` (3288), solo las de esa pieza del libro.
    """
    c = datos.con()
    medidas = datos.medidas(codigo)
    excel = {f["cota"] for f in medidas if componente is None or datos.componente_de_nombre(codigo, f["hoja"]) == componente}
    csv = cotas_csv(c, codigo)
    corregidas = {f["cota"] for f in c.execute(
        "SELECT ca.cota, d.nombre FROM cadena_correccion ca JOIN documento d ON d.id = ca.documento_id WHERE ca.pieza = ?", (codigo,))
        if componente is None or datos.componente_de_nombre(codigo, f["nombre"]) in (None, componente)}
    todas = (excel | csv | corregidas) - {None}
    return {"cotas": sorted(todas, key=datos.clave_cota), "pieza_con_datos": bool(medidas or csv or corregidas)}


_datos_planos: dict | None = None
_bloqueo_planos = threading.Lock()


def datos_de_planos() -> dict[int, dict]:
    """Tag de datos de cada plano: de sus números situados (todas las páginas), cuántos tienen datos en su ficha.

    «con» si alguno los tiene; si no, «sin», también con 0 números situados (mismo criterio que la casilla del
    plano). Se calcula una vez (unos segundos: hay que situar los globos de los 56 planos); `app.py` lo
    lanza al arrancar, en segundo plano.
    """
    global _datos_planos
    with _bloqueo_planos:
        if _datos_planos is None:
            salida = {}
            for p in datos.planos():
                componente = p["componente"] if p["componente"] in datos.COMPONENTES.get(p["codigo"], {}) else None
                marcadas = set(cotas_con_datos(p["codigo"], componente)["cotas"]) if p["codigo"] else set()
                etiquetas = [b["etiqueta"] for pag in range(1, p["paginas"] + 1) for b in datos.globos(p["id"], pag)["globos"]]
                con = sum(e in marcadas for e in etiquetas)
                salida[p["id"]] = {"datos": "con" if con else "sin", "numeros_con_datos": con, "numeros": len(etiquetas)}
            _datos_planos = salida
        return _datos_planos


def serie(codigo: str, cota: str, pestana: str | None = None, elemento: str | None = None, componente: str | None = None) -> dict:
    """Con varios componentes (3288), todo lo que se devuelve es de uno: línea, tolerancias, excluidos y correcciones."""
    filas, csv, lista = _datos_cota(codigo, cota)
    filas, lista = list(filas), list(lista)
    nombres = datos.COMPONENTES.get(codigo, {})
    por_componente: Counter = Counter()
    if nombres:
        for x in filas:
            por_componente[datos.componente_de_nombre(codigo, x["hoja"])] += 1
        if componente not in nombres:
            desde_pestana = datos.componente_de_nombre(codigo, pestana)
            componente = desde_pestana or next((k for k in nombres if por_componente[k]), next(iter(nombres)))
        filas = [x for x in filas if datos.componente_de_nombre(codigo, x["hoja"]) == componente]
        lista = [x for x in lista if x["componente"] in (None, componente)]
    else:
        componente = None
    salida = construir([dict(x) for x in filas], csv, pestana, elemento)
    anotar_fechas(salida, datos.fechas_de_muestreos(codigo), codigo, componente)
    asociar_correcciones(salida, lista)
    salida["componente"] = componente
    salida["componentes"] = [{"id": k, "etiqueta": v, "valores": por_componente[k]} for k, v in nombres.items()]
    return salida


def resumen() -> None:
    """Con la selección por defecto de cada cota, cuántos muestreos cubre la línea y de qué tipo son sus puntos."""
    print("| Pieza | Cotas | Muestreos de esas cotas | Con punto | De la pestaña elegida | Hueco | Solo CSV | Sin punto | Repetidos | Media | Otro valor |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    total: Counter = Counter()
    c = datos.con()

    def linea(nombre: str, t: Counter) -> None:
        print(f"| {nombre} | {t['cotas']} | {t['muestreos']} | {t['con']} | {t['llenos']} | {t['huecos']} | {t['csv']} | {t['muestreos'] - t['con']} "
              f"| {t['repetidos']} | {t['medias']} | {t['otro']} |")
    for p in datos.piezas():
        codigo = p["codigo"]
        por_cota: dict = defaultdict(list)
        for x in cargar(c, codigo, excluidas=True):
            # En un libro con dos piezas, el mismo número es otra cota en cada una.
            por_cota[(x["cota"], datos.componente_de_nombre(codigo, x["hoja"]))].append(x)
        t: Counter = Counter()
        for (cota, _), filas in por_cota.items():
            muestreos = {(x["serie"], x["n"]) for x in filas if x["marca"] not in datos.EXCLUIDAS}
            if not muestreos:
                continue
            s = construir(filas, csv_de(c, codigo, cota))
            t.update(cotas=1, muestreos=len(muestreos), con=len(s["muestreos"]))
            for i in range(len(s["muestreos"])):
                presentes = [lista[i] for lista in s["puntos"].values() if lista[i]]
                solo = bool(presentes) and all(q["hoja"] == HOJA_CSV for q in presentes)
                hueco = bool(presentes) and not solo and all(q["hueco"] for q in presentes)
                t.update(csv=solo, huecos=hueco, llenos=bool(presentes) and not solo and not hueco, repetidos=any(q["repite"] for q in presentes),
                         medias=any(q["media"] for q in presentes), otro=any(any(a.startswith(("También", "Otra copia", "CSV de")) for a in q["avisos"]) for q in presentes))
        if t["cotas"]:
            linea(codigo, t)
            total.update(t)
    linea("**Total**", total)


def csv_frente_excel(codigo: str) -> dict:
    """Puntos donde el CSV de la CMM y el Excel del mismo muestreo discrepan (selección por defecto de cada cota).

    Para cada uno mira si el valor del Excel es, ±0,0005, el del CSV de un muestreo anterior de la misma cota y cavidad.
    El control es lo mismo frente a un muestreo posterior, que no se puede haber heredado: mide la coincidencia casual."""
    c = datos.con()
    por_cota: dict = defaultdict(list)
    for x in cargar(c, codigo, excluidas=True):
        por_cota[x["cota"]].append(x)
    casos = []
    for cota, filas in por_cota.items():
        csv = csv_de(c, codigo, cota)
        valores: dict = defaultdict(set)
        for (_, n, cav, _), lista in csv.items():
            valores[(cav, n)].update(r["valor"] for r in lista)
        s = construir(filas, csv)
        for cav, pts in s["puntos"].items():
            for m, p in zip(s["muestreos"], pts):
                aviso = next((a for a in (p or {}).get("avisos", ()) if a.startswith("CSV de la CMM:")), None)
                if not aviso:
                    continue
                excel = float(re.search(r"el Excel dice (-?\d+(?:,\d+)?)", aviso)[1].replace(",", "."))
                iguales = sorted(n for (cv, n), vs in valores.items() if cv == cav and any(abs(excel - v) <= .0005 for v in vs))
                casos.append({"cota": cota, "cavidad": cav, "muestreo": m["n"], "csv": p["v"], "excel": excel,
                              "celda": f"{p['fichero']}!{p['hoja']}!{p['celda']}",
                              "anterior": [n for n in iguales if n < m["n"]], "posterior": [n for n in iguales if n > m["n"]]})
    return {"discrepan": len(casos), "igual_a_csv_anterior": sum(bool(x["anterior"]) for x in casos),
            "control_igual_a_csv_posterior": sum(bool(x["posterior"]) for x in casos),
            "por_muestreo": sorted(Counter((x["muestreo"], x["anterior"][-1] if x["anterior"] else 0) for x in casos).items()),
            "casos": casos}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--resumen" in sys.argv:
        resumen()
    elif "--csv-frente-excel" in sys.argv:
        r = csv_frente_excel(sys.argv[sys.argv.index("--csv-frente-excel") + 1])
        print(json.dumps({k: v for k, v in r.items() if k != "casos"}, ensure_ascii=False))
        for x in r["casos"][:10]:
            print(json.dumps(x, ensure_ascii=False))
