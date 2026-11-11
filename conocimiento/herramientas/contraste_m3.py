"""Contraste en los originales de las hojas de M3 (pendientes P-2 y P-5, 11/11/2026). Solo lectura.

M3 (`revision.py`): hojas cuyo `intern.NN` del nombre no coincide con el muestreo que cita su cabecera (`ppap_ref`).
En la biblioteca se midió qué parte de sus valores (cota, cavidad, valor) está también en el muestreo citado:

- P-2: al menos el 90 %, en las piezas no contrastadas aún (3218 y 3174 ya están en I-001).
- P-5: entre el 30 y el 90 %.

    python contraste_m3.py muestra      # fija la muestra ANTES de abrir originales: datos/contraste-m3/muestra.json
    python contraste_m3.py contrastar   # lee los originales de la muestra: datos/contraste-m3/resultados.json

La muestra: todas las hojas de P-2 y una hoja por pieza de P-5, elegida con la semilla SEMILLA. Cada hoja se compara
con la hoja del libro citado que más claves comparte en la biblioteca, decidido también antes de abrir nada.

La comparación es por clave (cota, cavidad, número de muestra dentro de esa cota y cavidad, en orden de fila y
columna), porque las filas pueden estar desplazadas entre libros (3174 `intern.09`). Las coordenadas de cada valor
salen de `medida_dr`; el valor se lee del original, y se cuenta aparte si no coincide con el de la biblioteca. Excel
se abre en cálculo manual para leer los valores guardados. Se excluyen las celdas con RAND() (I-003) y los ceros,
cuyo significado no está confirmado (I-002). Recuentos sobre las medidas de la hoja del caso: total = excluidas +
sin pareja + comparadas.

Criterios, fijados antes de abrir los originales y precisados tras la revisión del 11/11/2026 (`evaluar`):

- **Repetición confirmada**: al menos el 90 % de las medidas comparables con el mismo valor, con 20 comparables
  como mínimo. **Parcial**: un bloque de al menos 5 filas seguidas completas (todas sus medidas, salvo las
  excluidas, con pareja y el mismo valor) con 10 valores de tres decimales o más dentro del propio bloque.
  Son valores idénticos: no dice si se volvió a medir.
- **Sospecha descartada con evidencia**: al menos 20 medidas comparables, menos del 30 % iguales y ningún bloque de
  5 filas completas.
- **Pendiente por falta de evidencia**: el resto (pocas medidas comparables, coincidencias sueltas o con pocos
  decimales, original ilegible), con el motivo.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadena_correcciones import MUESTREO, serie_de  # noqa: E402
from comun import BD, DATOS, NUBE, original  # noqa: E402
from lectores import copia_temporal  # noqa: E402

SEMILLA = 20261111
YA_CONTRASTADAS = {"3218", "3174"}  # I-001, 11/11/2026
SALIDA = DATOS / "contraste-m3"
MIN_CLAVES, MIN_BLOQUE, MIN_INFORMATIVOS = 20, 5, 10


def muestreo_de(nombre: str):
    m = MUESTREO.search(nombre or "")
    return (serie_de(nombre), int(m.group(1))) if m else None


def letra(col: int) -> str:
    s = ""
    while col:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s


NO_MEDIDAS = {"aleatoria", "cero"}  # RAND() (I-003) y ceros de significado no confirmado (I-002): excluidos, contados aparte


def filas_de(c, doc: int, hoja: str | None = None) -> list[tuple]:
    q = "SELECT hoja, fila, col, cota, cavidad, valor, marca FROM medida_dr WHERE documento_id=? AND valor IS NOT NULL"
    filas = c.execute(q + (" AND hoja=?" if hoja is not None else ""), (doc, hoja) if hoja is not None else (doc,)).fetchall()
    return sorted(filas, key=lambda x: (x[0], x[1], x[2]))


def claves(filas: list[tuple]) -> dict:
    """(cota, cavidad, k) -> (fila, col, valor, marca): k es el número de muestra de esa cota y cavidad en la hoja."""
    vistos: Counter = Counter()
    salida = {}
    for _, fila, col, cota, cav, valor, marca in sorted(filas, key=lambda x: (x[1], x[2])):
        k = vistos[(cota, cav)]
        vistos[(cota, cav)] += 1
        salida[(cota, cav, k)] = (fila, col, valor, marca)
    return salida


def grupos(c) -> list[dict]:
    """Las hojas de M3 con su coincidencia en la biblioteca (multiconjunto de cota, cavidad y valor), como el 11/11/2026."""
    docs = {r[0]: r for r in c.execute("SELECT id, codigo, nombre, ruta FROM documento")}
    por_muestreo = defaultdict(list)
    for i, cod, nombre, ruta in c.execute("SELECT id, codigo, nombre, ruta FROM documento WHERE carpeta_norm='metrologia'"):
        m = muestreo_de(nombre)
        if m:
            por_muestreo[(cod, m[0], m[1])].append(i)
    salida = []
    for doc, hoja, meta in c.execute("SELECT documento_id, hoja, metadatos FROM perfil_ppap ORDER BY documento_id, hoja").fetchall():
        _, cod, nombre, ruta = docs[doc]
        ref = str((json.loads(meta or "{}") or {}).get("ppap_ref") or "")
        a, b = muestreo_de(nombre), muestreo_de(ref)
        if not (a and b) or a[1] == b[1]:
            continue
        # Igual que el cálculo del 11/11/2026 que definió los grupos: todos los valores, también RAND() y ceros.
        mia = Counter((x[3], x[4], round(x[5], 6)) for x in filas_de(c, doc, hoja))
        mejor = None
        for d in por_muestreo.get((cod, a[0], b[1]), []):
            otra = Counter((x[3], x[4], round(x[5], 6)) for x in filas_de(c, d))
            f = sum((mia & otra).values()) / sum(mia.values()) if mia else 0
            if mejor is None or f > mejor[1]:
                mejor = (d, f)
        salida.append({"pieza": cod, "documento": doc, "ruta": ruta, "hoja": hoja, "ppap_ref": ref,
                       "citado": mejor[0] if mejor else None, "coincidencia": round(mejor[1], 3) if mejor else None,
                       "medidas": sum(mia.values())})
    return salida


def hoja_destino(c, caso: dict) -> tuple[str | None, int]:
    """La hoja del libro citado que más claves comparte con la hoja del caso (en la biblioteca); empate: el mismo nombre."""
    a = claves(filas_de(c, caso["documento"], caso["hoja"]))
    mejor, n_mejor = None, -1
    for (h,) in c.execute("SELECT DISTINCT hoja FROM medida_dr WHERE documento_id=? ORDER BY hoja", (caso["citado"],)):
        b = claves(filas_de(c, caso["citado"], h))
        n = sum(1 for k in a.keys() & b.keys() if round(a[k][2], 6) == round(b[k][2], 6))
        if n > n_mejor or (n == n_mejor and h == caso["hoja"]):
            mejor, n_mejor = h, n
    return mejor, n_mejor


def muestra() -> dict:
    c = sqlite3.connect(f"file:{BD.resolve().as_posix()}?mode=ro", uri=True)
    todos = grupos(c)
    clase = Counter("≥90 %" if x["coincidencia"] is not None and x["coincidencia"] >= 0.9 else
                    "30-90 %" if x["coincidencia"] is not None and x["coincidencia"] >= 0.3 else
                    "<30 %" if x["medidas"] else "sin medidas" for x in todos)
    p2 = [x for x in todos if x["coincidencia"] is not None and x["coincidencia"] >= 0.9 and x["pieza"] not in YA_CONTRASTADAS]
    p5_todas = [x for x in todos if x["coincidencia"] is not None and 0.3 <= x["coincidencia"] < 0.9]
    azar = random.Random(SEMILLA)
    p5 = []
    for pieza in sorted({x["pieza"] for x in p5_todas}):
        candidatas = [x for x in p5_todas if x["pieza"] == pieza]
        p5.append(azar.choice(candidatas))
    elegidas = [{**x, "grupo": "P-2"} for x in p2] + [{**x, "grupo": "P-5"} for x in p5]
    rutas = {r[0]: r[1] for r in c.execute("SELECT id, ruta FROM documento")}
    for x in elegidas:
        x["ruta_citado"] = rutas[x["citado"]]
        x["hoja_citado"], x["claves_iguales_biblioteca"] = hoja_destino(c, x)
    r = {"semilla": SEMILLA, "m3": len(todos), "grupos": dict(clase), "p2_total": len(p2), "p5_total": len(p5_todas),
         "muestra": elegidas}
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "muestra.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def leer_hojas(ruta: str, hojas: set[str], excel) -> dict:
    """Value2 de las hojas pedidas, desde una copia temporal del original abierta en solo lectura."""
    path = original(ruta)
    if os.stat(path).st_file_attributes & NUBE:
        raise RuntimeError("en la nube: no se lee")
    carpeta, copia = copia_temporal(str(path))
    try:
        libro = excel.Workbooks.Open(copia, 0, True)
        try:
            salida = {}
            for h in hojas:
                rango = libro.Worksheets(h).UsedRange
                valores = rango.Value2
                if not isinstance(valores, tuple):
                    valores = ((valores,),)
                salida[h] = (rango.Row, rango.Column, valores)
            return salida
        finally:
            libro.Close(False)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def valor_en(hoja: tuple, fila: int, col: int):
    fila0, col0, valores = hoja
    try:
        v = valores[fila - fila0][col - col0]
    except IndexError:
        return None
    return v if isinstance(v, float) else None


def _con_decimales(v: float) -> bool:
    """Tres decimales o más: dos medidas así no suelen coincidir por casualidad."""
    return round(v, 2) != round(v, 6)


def evaluar(a: dict, b: dict, leer_a, leer_b) -> dict:
    """Compara la hoja del caso (`a`) con la citada (`b`), claves de `claves()`. `leer_*(fila, col)` da el valor del original.

    Recuentos sobre las medidas de `a`: total = excluidas (RAND() o cero, en cualquiera de las dos hojas) + sin pareja
    + comparadas (+ no leídas). Corregido el 11/11/2026 tras la revisión:

    - un bloque son filas seguidas **completas**: todas sus medidas, salvo las excluidas, con pareja y el mismo valor
      (antes, una medida sin pareja no rompía el bloque: 3212 `intern.02`, fila 142, 4 de 8 medidas);
    - los valores con tres decimales o más se cuentan **dentro de cada bloque** (antes, en toda la hoja: 3186
      `intern.16`, el bloque más largo, de 52 filas, no tiene ninguno);
    - vale cualquier bloque que cumpla, aunque no sea el más largo, que se da aparte."""
    lector = {"a": 0, "b": 0}
    cuenta = Counter()
    iguales, distintos = [], []
    por_fila: dict = defaultdict(list)  # fila de `a` -> [(igual o None si sin pareja, con decimales)]
    for k in sorted(a, key=lambda k: (a[k][0], a[k][1])):
        fila, col, valor, marca = a[k]
        cuenta["total"] += 1
        pareja = b.get(k)
        if marca in NO_MEDIDAS or (pareja and pareja[3] in NO_MEDIDAS):
            cuenta["excluidas"] += 1
            continue
        if pareja is None:
            cuenta["sin_pareja"] += 1
            por_fila[fila].append((None, False))
            continue
        va, vb = leer_a(fila, col), leer_b(pareja[0], pareja[1])
        lector["a"] += va is None or abs(va - valor) > 1e-9
        lector["b"] += vb is None or abs(vb - pareja[2]) > 1e-9
        if va is None or vb is None:
            cuenta["no_leidas"] += 1
            por_fila[fila].append((None, False))
            continue
        cuenta["comparadas"] += 1
        igual = abs(va - vb) < 1e-9
        por_fila[fila].append((igual, igual and _con_decimales(va)))
        (iguales if igual else distintos).append(
            (f"{letra(col)}{fila}", f"{letra(pareja[1])}{pareja[0]}", va, vb, k[0], k[1]))
    # Bloques: filas seguidas (orden de la hoja del caso) con todas sus medidas comparadas e iguales.
    bloques, actual = [], []
    for fila in sorted(por_fila):
        if all(e is True for e, _ in por_fila[fila]):
            actual.append(fila)
        else:
            if actual:
                bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)
    resumen = [{"filas": len(x), "desde": x[0], "hasta": x[-1], "con_decimales": sum(d for f in x for _, d in por_fila[f])}
               for x in bloques]
    validos = [x for x in resumen if x["filas"] >= MIN_BLOQUE and x["con_decimales"] >= MIN_INFORMATIVOS]
    valido = max(validos, key=lambda x: (x["filas"], x["con_decimales"]), default=None)
    mas_largo = max(resumen, key=lambda x: (x["filas"], x["con_decimales"]), default=None)
    n, iguales_n = cuenta["comparadas"], len(iguales)
    share = iguales_n / n if n else 0
    if n >= MIN_CLAVES and share >= 0.9:
        clase, motivo = "repetición confirmada", f"{iguales_n} de {n} medidas comparables iguales (≥90 %)"
    elif valido:
        clase = "repetición confirmada (parcial)"
        motivo = (f"bloque de {valido['filas']} filas completas iguales (filas {valido['desde']}-{valido['hasta']}, "
                  f"{valido['con_decimales']} valores con tres decimales o más)")
    elif n >= MIN_CLAVES and share < 0.3 and not any(x["filas"] >= MIN_BLOQUE for x in resumen):
        clase, motivo = "sospecha descartada con evidencia", f"solo {iguales_n} de {n} iguales, sin bloque de {MIN_BLOQUE} filas"
    else:
        clase = "pendiente"
        largos = [x for x in resumen if x["filas"] >= MIN_BLOQUE]
        motivo = (f"solo {n} medidas comparables" if n < MIN_CLAVES else
                  f"{iguales_n} de {n} iguales, sin bloque que cumpla: " +
                  (", ".join(f"{x['filas']} filas con {x['con_decimales']} valores de tres decimales" for x in largos[:3])
                   if largos else f"ningún bloque de {MIN_BLOQUE} filas completas"))
    return {"clase": clase, "motivo": motivo, **{k: cuenta[k] for k in ("total", "excluidas", "sin_pareja", "comparadas", "no_leidas")},
            "iguales": iguales_n, "bloque_valido": valido, "bloque_mas_largo": mas_largo, "lector_distinto": lector,
            "ejemplos_iguales": iguales[:3], "ejemplos_distintos": distintos[:3]}


def contrastar() -> list[dict]:
    import pythoncom
    import win32com.client

    elegidas = json.loads((SALIDA / "muestra.json").read_text(encoding="utf-8"))["muestra"]
    c = sqlite3.connect(f"file:{BD.resolve().as_posix()}?mode=ro", uri=True)
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible, excel.DisplayAlerts, excel.AutomationSecurity = False, False, 3  # sin macros
    # Cálculo manual antes de abrir nada: si no, Excel recalcula las RAND() al abrir y lo leído no es lo guardado
    # (primera ejecución del 11/11/2026, 3233: 2.354 celdas). El modo se fija con un libro en blanco abierto.
    excel.Workbooks.Add()
    excel.Calculation = -4135  # xlCalculationManual
    resultados = []
    try:
        for x in elegidas:
            r = {k: x[k] for k in ("grupo", "pieza", "ruta", "hoja", "ppap_ref", "ruta_citado", "hoja_citado", "coincidencia")}
            try:
                if x["ruta"] == x["ruta_citado"]:
                    hojas = leer_hojas(x["ruta"], {x["hoja"], x["hoja_citado"]}, excel)
                    ha, hb = hojas[x["hoja"]], hojas[x["hoja_citado"]]
                else:
                    ha = leer_hojas(x["ruta"], {x["hoja"]}, excel)[x["hoja"]]
                    hb = leer_hojas(x["ruta_citado"], {x["hoja_citado"]}, excel)[x["hoja_citado"]]
            except Exception as e:  # noqa: BLE001 - se registra y la hoja queda pendiente
                resultados.append({**r, "clase": "pendiente", "motivo": f"original no leído: {e}"})
                continue
            a = claves(filas_de(c, x["documento"], x["hoja"]))
            b = claves(filas_de(c, x["citado"], x["hoja_citado"]))
            e = evaluar(a, b, lambda f, col: valor_en(ha, f, col), lambda f, col: valor_en(hb, f, col))
            resultados.append({**r, **e})
            print(f"{x['grupo']} {x['pieza']} {x['ruta'].split('/')[-1]}!{x['hoja']}: {e['clase']} ({e['motivo']})", flush=True)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
    (SALIDA / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return resultados


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paso", choices=("muestra", "contrastar"))
    args = p.parse_args()
    if args.paso == "muestra":
        r = muestra()
        print(json.dumps({k: v for k, v in r.items() if k != "muestra"}, ensure_ascii=False))
        for x in r["muestra"]:
            print(f"{x['grupo']} | {x['pieza']} | {x['ruta']} | {x['hoja']} | {x['ppap_ref']} | {x['coincidencia']} | "
                  f"{x['ruta_citado']} | {x['hoja_citado']} | {x['claves_iguales_biblioteca']}")
    else:
        contrastar()


if __name__ == "__main__":
    main()
