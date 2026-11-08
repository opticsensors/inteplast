"""Censo de solo lectura: por qué un punto de una gráfica (cota + muestreo + cavidad) tiene varios valores en `medida_dr`.

Usa las mismas hojas y exclusiones que `cadena_correcciones.py`: papel `informe`, carpeta de metrología, `intern.NN` en
el nombre y sin `RAND()`, ceros ni atípicos. No escribe en la biblioteca. Conclusiones en `conocimiento/valores-por-punto.md`.

    python conocimiento/herramientas/valores_por_punto.py             # tablas Markdown del censo
    python conocimiento/herramientas/valores_por_punto.py --hojas     # nombres de hoja de cada pieza
    python conocimiento/herramientas/valores_por_punto.py --cobertura # cuánto cubre una hoja; muestreos que repiten otro
    python conocimiento/herramientas/valores_por_punto.py --sin-intern # informes sin intern.NN frente a los intern
    python conocimiento/herramientas/valores_por_punto.py --ejemplos 8 --semilla 20261106
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadena_correcciones import EXCLUIDAS, MUESTREO, firma, serie_de  # noqa: E402
from comun import BD  # noqa: E402

NO_COMENTARIO = re.compile(r"-?[\d.,]+(e-?\d+)?|x|nok|ok|#ref!", re.I)
CAUSAS = ("elementos", "hojas", "copias", "filas", "bloques", "muestras")
TITULOS = {"elementos": "Elementos distintos", "hojas": "Hojas distintas", "copias": "Copias que discrepan",
           "filas": "Filas seguidas sin rótulo", "bloques": "Bloques separados", "muestras": "Varias piezas por cavidad"}
SOLO_PRIMERA, SOLO_ULTIMA, LAS_DOS, NINGUNA = "solo_primera", "solo_ultima", "las_dos", "ninguna"


def cargar(con, pieza: str, cota_buscada: str | None = None, excluidas: bool = False) -> list[dict]:
    """Valores de la pieza, cada uno con la identidad de su fila: `elemento` y el `bloque` de filas seguidas de la cota.

    Con `cota_buscada` solo lee esa cota, sin cargar las celdas de toda la pieza. Con `excluidas` conserva los valores
    `RAND()`, ceros y atípicos, con su `marca`, para poder listarlos."""
    disposicion = {(d, h): json.loads(c or "{}") for d, h, c in con.execute(
        "SELECT l.documento_id, l.hoja, l.columnas FROM lectura_dr l JOIN documento d ON d.id = l.documento_id "
        "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' AND l.papel = 'informe'", (pieza,))}
    celdas: dict = defaultdict(dict)
    if cota_buscada is None:
        for d, h, f, c, v in con.execute(
                "SELECT ce.documento_id, ce.hoja, ce.fila, ce.col, ce.valor FROM celda ce "
                "JOIN lectura_dr l ON l.documento_id = ce.documento_id AND l.hoja = ce.hoja "
                "JOIN documento d ON d.id = ce.documento_id WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' "
                "AND l.papel = 'informe' AND ce.valor IS NOT NULL", (pieza,)):
            celdas[(d, h, f)][c] = str(v).strip()

    def celdas_de(d: int, h: str, f: int) -> dict:
        if cota_buscada is not None and (d, h, f) not in celdas:
            celdas[(d, h, f)] = {c: str(v).strip() for c, v in con.execute(
                "SELECT col, valor FROM celda WHERE documento_id = ? AND hoja = ? AND fila = ? AND valor IS NOT NULL", (d, h, f))}
        return celdas.get((d, h, f), {})
    salida = []
    for d, nombre, ruta, h, f, c, cota, nom, sup, inf, equipo, cav, valor, marca in con.execute(
            "SELECT d.id, d.nombre, d.ruta, m.hoja, m.fila, m.col, m.cota, m.nominal, m.tol_sup, m.tol_inf, m.equipo, "
            "m.cavidad, m.valor, m.marca FROM medida_dr m JOIN documento d ON d.id = m.documento_id "
            "JOIN lectura_dr l ON l.documento_id = m.documento_id AND l.hoja = m.hoja "
            "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' AND l.papel = 'informe' AND (? IS NULL OR m.cota = ?)",
            (pieza, cota_buscada, cota_buscada)):
        muestreo = MUESTREO.search(nombre)
        if not muestreo or valor is None or (marca in EXCLUIDAS and not excluidas):
            continue
        cols = disposicion.get((d, h), {})
        fila = celdas_de(d, h, f)
        c_cod, c_nom, c_tipo = cols.get("codigo") or 0, cols.get("nominal") or 0, cols.get("tipo")
        etiqueta = " ".join(fila[k].casefold() for k in sorted(fila) if c_cod < k < c_nom and k != c_tipo and fila[k])
        tipo = fila.get(c_tipo, "").casefold() if c_tipo else ""
        equipo = (equipo or "").strip().casefold()
        # Comentario: texto a la derecha del nominal que no sea un valor, una marca NOK ni el equipo (`H= 5`, `pocket 2`).
        comentario = " ".join(fila[k].casefold() for k in sorted(fila)
                              if k > c_nom and not NO_COMENTARIO.fullmatch(fila[k]) and fila[k].casefold() != equipo)
        salida.append({"doc": d, "nombre": nombre, "ruta": ruta, "hoja": h, "fila": f, "col": c, "cota": cota,
                       "cav": cav, "valor": round(valor, 6), "serie": serie_de(nombre), "n": int(muestreo.group(1)),
                       "elemento": (etiqueta, tipo, (nom, sup, inf), equipo, comentario[:60]), "marca": marca})
    cota_de: dict = defaultdict(dict)
    if cota_buscada is None:
        for x in salida:
            cota_de[(x["doc"], x["hoja"])][x["fila"]] = x["cota"]
    else:  # los bloques dependen de las otras cotas de la hoja
        hojas = {(x["doc"], x["hoja"]) for x in salida}
        for d, h, f, c in con.execute(
                "SELECT DISTINCT m.documento_id, m.hoja, m.fila, m.cota FROM medida_dr m JOIN documento d ON d.id = m.documento_id "
                "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia'", (pieza,)):
            if (d, h) in hojas:
                cota_de[(d, h)][f] = c
    bloque_de: dict = {}
    for clave, filas in cota_de.items():
        bloque, anterior = 0, None
        for f in sorted(filas):
            if filas[f] != anterior:
                bloque, anterior = bloque + 1, filas[f]
            bloque_de[(*clave, f)] = bloque
    for x in salida:
        x["bloque"] = bloque_de[(x["doc"], x["hoja"], x["fila"])]
    return salida


def conjuntos(pares) -> set[frozenset]:
    agrupados: dict = defaultdict(set)
    for clave, valor in pares:
        agrupados[clave].add(valor)
    return {frozenset(v) for v in agrupados.values()}


def causas_del_punto(filas: list[dict]) -> set[str]:
    """Causas presentes en un punto con varios valores; un mismo punto puede tener varias."""
    causas: set[str] = set()
    if len(conjuntos((x["hoja"], x["valor"]) for x in filas)) > 1:
        causas.add("hojas")
    por_hoja_elemento: dict = defaultdict(list)
    por_hoja_doc: dict = defaultdict(list)
    for x in filas:
        por_hoja_elemento[(x["hoja"], x["elemento"])].append(x)
        por_hoja_doc[(x["doc"], x["hoja"])].append(x)
    if any(len(conjuntos((x["doc"], x["valor"]) for x in l)) > 1 for l in por_hoja_elemento.values()):
        causas.add("copias")
    for hoja in por_hoja_doc.values():
        if len(conjuntos((x["elemento"], x["valor"]) for x in hoja)) > 1:
            causas.add("elementos")
        if any(len(s) > 1 for s in conjuntos((x["fila"], x["valor"]) for x in hoja)):
            causas.add("muestras")
        por_elemento: dict = defaultdict(list)
        for x in hoja:
            por_elemento[x["elemento"]].append(x)
        for lista in por_elemento.values():
            por_bloque: dict = defaultdict(list)
            for x in lista:
                por_bloque[x["bloque"]].append(x)
            if any(len({x["valor"] for x in b}) > 1 and len({x["fila"] for x in b}) > 1 for b in por_bloque.values()):
                causas.add("filas")
            if len(conjuntos((x["bloque"], x["valor"]) for x in lista)) > 1:
                causas.add("bloques")
    return causas


def bloques_repetidos(filas: list[dict], referencia: dict | None) -> tuple[Counter, Counter, list]:
    """Misma cota y elemento en dos zonas de una hoja, con otras cotas entre medias y valores distintos (3212 `intern.08`,
    `DR`, filas 25 y 52). ¿Cuál repite un muestreo anterior? Se compara la fila completa, con 3 valores o más."""
    celdas_fila: dict = defaultdict(list)
    meta: dict = {}
    for x in filas:
        k = (x["doc"], x["hoja"], x["fila"])
        celdas_fila[k].append((x["col"], x["cav"], x["valor"]))
        meta[k] = x
    firmas = {k: firma(sorted(v)) for k, v in celdas_fila.items()}
    vistas: dict = defaultdict(set)
    for k, f in firmas.items():
        if len(f) >= 3:
            vistas[(meta[k]["cota"], meta[k]["serie"], f)].add(meta[k]["n"])
    grupos: dict = defaultdict(list)
    for k, x in meta.items():
        grupos[(k[0], k[1], x["cota"], x["elemento"])].append(k[2])

    def repite(k) -> bool:
        x = meta[k]
        return any(n < x["n"] for n in vistas.get((x["cota"], x["serie"], firmas[k]), ()))

    herencia, csv, ejemplos = Counter(), Counter(), []
    for (d, h, cota, _), lista in grupos.items():
        lista = sorted(lista)
        primera, ultima = (d, h, lista[0]), (d, h, lista[-1])
        if meta[primera]["bloque"] == meta[ultima]["bloque"] or firmas[primera] == firmas[ultima]:
            continue
        rp, ru = repite(primera), repite(ultima)
        clase = SOLO_PRIMERA if rp and not ru else SOLO_ULTIMA if ru and not rp else LAS_DOS if rp else NINGUNA
        herencia[clase] += 1
        ejemplos.append((clase, meta[primera], lista[0], lista[-1], firmas[primera][:4], firmas[ultima][:4]))
        if referencia:
            n = meta[primera]["n"]

            def casa(k) -> bool:
                return all(round(v, 3) in referencia.get((n, (cav or "").split("@")[0].casefold(), cota), ())
                           for cav, v in firmas[k])
            if any((n, (cav or "").split("@")[0].casefold(), cota) in referencia for cav, _ in firmas[primera]):
                a, b = casa(primera), casa(ultima)
                csv[SOLO_ULTIMA if b and not a else SOLO_PRIMERA if a and not b else LAS_DOS if a else NINGUNA] += 1
    return herencia, csv, ejemplos


def hojas_por_pieza(con, piezas: list[str]) -> None:
    print("| Pieza | Informes | Hojas por informe (mediana · máximo) | Nombres de hoja más frecuentes (informes) |")
    print("|---|---:|---:|---|")
    for pieza in piezas:
        por_doc: dict = defaultdict(set)
        for d, nombre, hoja in con.execute(
                "SELECT d.id, d.nombre, l.hoja FROM lectura_dr l JOIN documento d ON d.id = l.documento_id "
                "WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia' AND l.papel = 'informe'", (pieza,)):
            if MUESTREO.search(nombre):
                por_doc[d].add(hoja)
        if not por_doc:
            continue
        nombres = Counter(h for hojas in por_doc.values() for h in hojas)
        tam = [len(h) for h in por_doc.values()]
        lista = " · ".join(f"`{h}` ({n})" for h, n in nombres.most_common(6))
        print(f"| {pieza} | {len(por_doc)} | {statistics.median(tam):g} · {max(tam)} | {lista} |")


def cobertura(con, piezas: list[str]) -> None:
    """¿Cuánto de la historia de una cota cubre una sola hoja? ¿Cuántos muestreos repiten los valores de uno anterior?"""
    print("| Pieza | Cotas con 2+ muestreos | Pares cota-muestreo | Cubre la mejor hoja | Cubre la mejor hoja y elemento "
          "| Cotas completas con hoja y elemento | Pares que repiten un muestreo anterior |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    total: Counter = Counter()

    def linea(nombre: str, t: Counter) -> None:
        print(f"| {nombre} | {t['cotas']} | {t['pares']} | {100 * t['hoja'] / t['pares']:.0f} % | {100 * t['elemento'] / t['pares']:.0f} % "
              f"| {100 * t['completas'] / t['cotas']:.0f} % | {100 * t['repite'] / t['pares']:.0f} % |")
    for pieza in piezas:
        por_cota: dict = defaultdict(list)
        for x in cargar(con, pieza):
            por_cota[(x["cota"], x["serie"])].append(x)
        t: Counter = Counter()
        for lista in por_cota.values():
            muestreos = sorted({x["n"] for x in lista})
            if len(muestreos) < 2:
                continue
            hojas, elementos, valores = defaultdict(set), defaultdict(set), defaultdict(set)
            for x in lista:
                hojas[x["hoja"]].add(x["n"])
                elementos[(x["hoja"], x["elemento"])].add(x["n"])
                valores[x["n"]].add((x["cav"], x["valor"]))
            mejor = max(len(v) for v in elementos.values())
            t.update(cotas=1, pares=len(muestreos), hoja=max(len(v) for v in hojas.values()), elemento=mejor,
                     completas=mejor == len(muestreos))
            t["repite"] += sum(any(valores[n] == valores[m] for m in muestreos[:i]) for i, n in enumerate(muestreos))
        if t["cotas"]:
            linea(pieza, t)
            total.update(t)
    linea("**Total**", total)


def sin_intern(con, piezas: list[str]) -> None:
    """Ficheros con medidas de metrología sin `intern.NN`, y cuántos de sus valores están en algún informe intern de la
    misma pieza (misma cota, sin el prefijo `1-` del cliente, misma cavidad y mismo valor a 3 decimales)."""
    print("| Pieza | Fichero | Carpeta | Valores | Celdas `RAND()` | Una por cavidad en intern | Muestra 1 en intern | Muestras 2–5 en intern |")
    print("|---|---|---|---:|---:|---:|---:|---:|")
    resumen: Counter = Counter()

    def clave(cota: str, cav: str | None) -> tuple:
        return re.sub(r"^1-", "", (cota or "").upper()), (cav or "").split("@")[0].split(".")[0]
    for pieza in piezas:
        internos: dict = defaultdict(set)
        ficheros: dict = {}
        for d, nombre, ruta, cota, cav, valor, marca in con.execute(
                "SELECT d.id, d.nombre, d.ruta, m.cota, m.cavidad, m.valor, m.marca FROM medida_dr m "
                "JOIN documento d ON d.id = m.documento_id WHERE d.codigo = ? AND d.carpeta_norm = 'metrologia'", (pieza,)):
            if MUESTREO.search(nombre):
                if marca != "aleatoria" and valor is not None:
                    internos[clave(cota, cav)].add(round(valor, 3))
            else:
                ficheros[d] = (nombre, ruta)
        for d, (nombre, ruta) in sorted(ficheros.items(), key=lambda x: x[1]):
            cuenta: dict = defaultdict(lambda: [0, 0])
            n = 0
            for cota, cav, valor, marca in con.execute("SELECT cota, cavidad, valor, marca FROM medida_dr WHERE documento_id = ?", (d,)):
                n += 1
                if marca == "aleatoria" or valor is None:
                    continue
                muestra = re.search(r"\.m(\d+)$", cav or "")
                grupo = "una" if not muestra else "primera" if muestra.group(1) == "1" else "resto"
                cuenta[grupo][0] += 1
                cuenta[grupo][1] += round(valor, 3) in internos.get(clave(cota, cav), ())
            aleatorias = con.execute("SELECT count(*) FROM celda_aleatoria WHERE documento_id = ?", (d,)).fetchone()[0]
            texto = [f"{100 * cuenta[g][1] / cuenta[g][0]:.0f} %" if cuenta[g][0] else "—" for g in ("una", "primera", "resto")]
            print(f"| {pieza} | `{nombre}` | {ruta.split('/')[-2]} | {n} | {aleatorias} | " + " | ".join(texto) + " |")
            resumen.update(ficheros=1, valores=n, con_rand=aleatorias > 0)
    print("\nResumen:", dict(resumen))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hojas", action="store_true", help="solo la tabla de nombres de hoja")
    ap.add_argument("--cobertura", action="store_true", help="cuánto cubre una hoja y cuántos muestreos repiten otro")
    ap.add_argument("--sin-intern", action="store_true", help="ficheros con medidas sin intern.NN frente a los intern")
    ap.add_argument("--ejemplos", type=int, default=0, help="casos al azar por causa, para auditarlos")
    ap.add_argument("--semilla", type=int, default=20261106)
    args = ap.parse_args()
    azar = random.Random(args.semilla)
    con = sqlite3.connect(f"file:{BD.as_posix()}?mode=ro", uri=True, timeout=30)
    piezas = [f[0] for f in con.execute("SELECT DISTINCT codigo FROM documento WHERE codigo IS NOT NULL ORDER BY 1")]
    if args.hojas or args.cobertura or args.sin_intern:
        if args.hojas:
            hojas_por_pieza(con, piezas)
        if args.cobertura:
            cobertura(con, piezas)
        if args.sin_intern:
            sin_intern(con, piezas)
        return
    referencia: dict = defaultdict(set)
    for n, cav, cota, valor in con.execute(
            "SELECT muestreo, cavidad, cota, valor FROM medida_cmm WHERE pieza = '3212' AND valor IS NOT NULL"):
        referencia[(int(n), (cav or "").casefold(), cota)].add(round(valor, 3))

    total, solas, herencia_total, csv_total = Counter(), Counter(), Counter(), Counter()
    muestras: dict = defaultdict(list)
    bloques_ej: list = []
    herencias: dict = {}
    base_tapa = 0
    print("| Pieza | Puntos | Con varios valores | " + " | ".join(TITULOS[c] for c in CAUSAS) + " |")
    print("|---|" + "---:|" * (len(CAUSAS) + 2))
    for pieza in piezas:
        filas = cargar(con, pieza)
        if not filas:
            continue
        puntos: dict = defaultdict(list)
        for x in filas:
            puntos[(x["cota"], x["serie"], x["n"], x["cav"])].append(x)
        t = Counter(puntos=len(puntos))
        for clave, lista in puntos.items():
            if len({x["valor"] for x in lista}) < 2:
                continue
            t["varios"] += 1
            causas = causas_del_punto(lista)
            if pieza == "3288" and {"DR(base)", "DR(tapa)"} <= {x["hoja"] for x in lista}:
                base_tapa += 1
            for c in causas:
                t[c] += 1
                muestras[c].append((pieza, clave, lista))
            if len(causas) == 1:
                solas[next(iter(causas))] += 1
            elif not causas:
                solas["sin_causa"] += 1
        print(f"| {pieza} | {t['puntos']} | {t['varios']} | " + " | ".join(str(t[c]) for c in CAUSAS) + " |")
        total.update(t)
        herencia, csv, ejemplos = bloques_repetidos(filas, referencia if pieza == "3212" else None)
        herencias[pieza] = herencia
        herencia_total.update(herencia)
        csv_total.update(csv)
        bloques_ej += [(pieza, *e) for e in ejemplos]
    print(f"| **Total** | {total['puntos']} | {total['varios']} | " + " | ".join(str(total[c]) for c in CAUSAS) + " |")
    print("\nPuntos con una sola causa:", {c: solas[c] for c in (*CAUSAS, "sin_causa")})
    print("3288, puntos con varios valores que juntan DR(base) y DR(tapa):", base_tapa)

    print("\n| Pieza | Bloques separados | Solo el primero repite un muestreo anterior | Solo el último | Los dos | Ninguno |")
    print("|---|---:|---:|---:|---:|---:|")
    for pieza, h in {**herencias, "**Total**": herencia_total}.items():
        if sum(h.values()):
            print(f"| {pieza} | {sum(h.values())} | {h[SOLO_PRIMERA]} | {h[SOLO_ULTIMA]} | {h[LAS_DOS]} | {h[NINGUNA]} |")
    print("\nEsos bloques del 3212 contra el CSV de la CMM (qué fila coincide):", dict(csv_total))
    for clase in (SOLO_PRIMERA, SOLO_ULTIMA):
        donde = Counter((e[0], e[2]["nombre"], e[2]["hoja"]) for e in bloques_ej if e[1] == clase)
        print(f"{clase}:", [(*k, n) for k, n in donde.most_common()])
    print("Filas de medida_cmm por pieza:", [tuple(f) for f in con.execute("SELECT pieza, count(*) FROM medida_cmm GROUP BY 1")])

    if args.ejemplos:
        for causa in CAUSAS:
            print(f"\n## Ejemplos: {causa} ({len(muestras[causa])})")
            for pieza, clave, lista in azar.sample(muestras[causa], min(args.ejemplos, len(muestras[causa]))):
                print(f"{pieza} cota {clave[0]} serie {clave[1]} intern.{clave[2]:02d} {clave[3]}")
                for x in sorted(lista, key=lambda y: (y["ruta"], y["hoja"], y["fila"], y["col"]))[:6]:
                    print(f"    {x['ruta'].split('/')[-2][:16]}/{x['nombre'][:42]} | {x['hoja'][:22]} f{x['fila']} c{x['col']} = {x['valor']} | "
                          f"{x['elemento'][0]!r} {x['elemento'][1]!r} {x['elemento'][3]!r} {x['elemento'][4]!r}")


if __name__ == "__main__":
    main()
