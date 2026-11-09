"""Lectores independientes de CSV CMM (3212 y 3197) y perfiles PA/PB documentados del 3212.

Solo lee originales. Publica tablas derivadas atomicas en la biblioteca.
No importa lectores de la app. Conserva valor original, coordenada y SHA-256.

- `medida_cmm`: export individual por bloques, una cavidad por fichero.
- `medida_cmm_comparativa`: comparativas «totes», una columna por cavidad. Copia de lo que ya
  hay en los individuales o, en el 3197 `intern.09`-`.11`, la unica fuente CSV del muestreo.
- `punto_cmm`: CSV de puntos `SYM-POINT` del 3197. Sin nominal ni tolerancia: coordenadas tal cual,
  en el orden del fichero.
- `medida_contorno`: perfiles PA/PB del 3212.

Las condiciones de la ruta o del nombre (temperatura/presion, ciclo, boquilla) van en `variante` y en
la etiqueta de cavidad (`c1@135ºC/500bar`), como hace `lector_dr.py` con sus bloques: nunca se funden
con la medida sin condicion. Las repeticiones de cavidad (`C4.1`, `c5bis`) conservan su etiqueta.
Un CSV sin cavidad en la ruta (`3197_Diametres.csv`) queda sin cavidad: no se deduce por el orden.
Uso: python conocimiento/herramientas/medidas_cmm.py [--comprobar]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path

from comun import BD, NUBE, original

PIEZAS = ("3212", "3197")

SCHEMA = """
CREATE TABLE IF NOT EXISTS medida_cmm (
 documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, fila INTEGER,
 bloque TEXT, ocurrencia INTEGER, indice INTEGER, cota TEXT, elemento_cmm TEXT,
 caracteristica TEXT, evaluacion TEXT, nominal REAL, tol_sup REAL, tol_inf REAL,
 valor REAL, desviacion REAL, fuera REAL, valor_original REAL, desviacion_original REAL,
 fuera_original REAL, corregido INTEGER, bolt TEXT, altura REAL, sha256 TEXT, variante TEXT,
 PRIMARY KEY(documento_id,fila)
);
CREATE INDEX IF NOT EXISTS medida_cmm_pieza_cota ON medida_cmm(pieza,cota,muestreo,cavidad);
CREATE TABLE IF NOT EXISTS medida_cmm_comparativa (
 documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, variante TEXT, fila INTEGER,
 columna INTEGER, rotulo TEXT, bloque TEXT, ocurrencia INTEGER, indice INTEGER, cota TEXT,
 elemento_cmm TEXT, caracteristica TEXT, nominal REAL, tol_sup REAL, tol_inf REAL, valor REAL,
 sha256 TEXT, PRIMARY KEY(documento_id,fila,columna)
);
CREATE INDEX IF NOT EXISTS medida_cmm_comparativa_pieza_cota ON medida_cmm_comparativa(pieza,cota,muestreo,cavidad);
CREATE TABLE IF NOT EXISTS punto_cmm (
 documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, variante TEXT, fila INTEGER,
 bloque TEXT, cota TEXT, elemento_cmm TEXT, tipo TEXT, marca TEXT,
 coord_1 REAL, coord_2 REAL, coord_3 REAL, sha256 TEXT, PRIMARY KEY(documento_id,fila)
);
CREATE TABLE IF NOT EXISTS medida_contorno (
 documento_id INTEGER PRIMARY KEY, pieza TEXT, muestreo TEXT, cavidad TEXT,
 perfil TEXT, indice INTEGER, contorno TEXT, tol_inf REAL, tol_sup REAL,
 desv_inf REAL, desv_sup REAL, infr_inf REAL, infr_sup REAL, media REAL,
 fecha TEXT, exceso REAL, pagina INTEGER, sha256 TEXT
);
"""

# Rotulo de cavidad en una cabecera o en una carpeta: c1, C4.1, c5bis, c13, c1-24 (ciclo en el 3197 intern.06).
CAVIDAD = re.compile(r"c(\d+)(\.\d+|bis)?(?:-(\d+))?", re.I)
NUMERO = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def numero(texto: str) -> float | None:
    texto = texto.strip().replace(",", ".")
    if not texto:
        return None
    if not NUMERO.fullmatch(texto):
        raise ValueError(f"Numero no reconocido: {texto!r}")
    value = float(texto)
    if not math.isfinite(value):
        raise ValueError("Numero no finito")
    return value


def es_numero(texto: str) -> bool:
    return bool(NUMERO.fullmatch(texto.strip().replace(",", ".")))


def texto_de(datos: bytes) -> str:
    """UTF-8 si lo es; si no, cp1252 (los exportes de la CMM)."""
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("cp1252")


def contexto(ruta: str) -> tuple[str, str]:
    """3212: muestreo y cavidad de la ruta."""
    muestreo = re.search(r"intern[. _-]*(\d+)", ruta, re.I)
    cavidades = re.findall(r"(?:^|[/_ ]|3212)c(?:av)?[. _]*(\d+)(?=[/_. -]|$)", ruta, re.I)
    if not muestreo or len(set(cavidades)) != 1:
        raise ValueError(f"Contexto de muestreo/cavidad ambiguo: {ruta}")
    return muestreo[1].zfill(2), f"c{int(cavidades[0])}"


def rotulo_cavidad(m: re.Match) -> tuple[str, str | None]:
    """`c5bis` -> ('c5bis', None); `c1-24` -> ('c1', '24')."""
    return f"c{int(m[1])}{(m[2] or '').lower()}", m[3]


def contexto_3197(ruta: str) -> tuple[str, str | None, list[str]]:
    """Muestreo, cavidad (o None) y condiciones literales de la ruta y el nombre."""
    partes = ruta.split("/")
    i = next((k for k, p in enumerate(partes) if re.search(r"intern[. _-]*\d+", p, re.I)), None)
    if i is None:
        raise ValueError(f"Sin intern.NN en la ruta: {ruta}")
    muestreo = re.search(r"intern[. _-]*(\d+)", partes[i], re.I)[1].zfill(2)
    carpetas = partes[i + 1:-1]
    cav_carpeta = [rotulo_cavidad(m) for p in carpetas if (m := CAVIDAD.fullmatch(p))]
    condiciones = [p for p in carpetas if not CAVIDAD.fullmatch(p)]
    nombre = re.sub(r"3197", " ", partes[-1].rsplit(".", 1)[0])
    cav_nombre = [rotulo_cavidad(m) for m in re.finditer(r"(?i)(?<![a-z\d])c(\d+)(\.\d+|bis)?(?:-(\d+))?(?![a-z\d])", nombre)]
    cavidades = {c for c, _ in cav_carpeta + cav_nombre}
    if len(cavidades) > 1:
        raise ValueError(f"Cavidad ambigua en la ruta: {ruta}")
    ciclos = [c for _, c in cav_carpeta + cav_nombre if c]
    boquilla = re.search(r"nozzle\s*(\d+)", nombre, re.I)
    return muestreo, next(iter(cavidades), None), condiciones + ciclos + ([f"nozzle {boquilla[1]}"] if boquilla else [])


def etiqueta(cavidad: str | None, condiciones: list[str]) -> tuple[str | None, str | None]:
    variante = "/".join(condiciones) or None
    if cavidad is None:
        return None, variante
    return cavidad + (f"@{variante}" if variante else ""), variante


def cota_de(bloque: str, pieza: str) -> str | None:
    if pieza == "3212" and bloque.startswith(("POINT ", "GLOBAL ")):
        return "165"
    cotas = re.findall(r"\bN(\d+(?:\.\d+)?)", bloque, re.I)
    return cotas[0] if len(set(cotas)) == 1 else None


def leer_csv(datos: bytes, pieza: str = "3212") -> list[dict]:
    """Export individual. En el 3212 conserva las 211 evaluaciones, incluidas POINT/GLOBAL y diagnosticos X/Z."""
    texto = texto_de(datos) if pieza != "3212" else datos.decode("cp1252")
    bloque, elemento, idx = "", "", 0
    ocurrencias = {}
    salida = []
    for linea, campos in enumerate(csv.reader(texto.splitlines(), delimiter=";"), 1):
        if not campos or not any(x.strip() for x in campos):
            continue
        cabecera = ";".join(campos).strip("; \t")
        if cabecera.startswith(("****", "////")):
            continue
        if any(re.fullmatch(r"c\d+", x.strip(), re.I) for x in campos[4:]):
            raise ValueError("Comparativa de cavidades: fuera del lector individual")
        if len(campos) < 8 or not campos[1].strip():
            bloque, elemento, idx = cabecera, "", 0
            ocurrencias[bloque] = ocurrencias.get(bloque, 0) + 1
            continue
        idx += 1
        elemento = campos[0].strip() or elemento
        nominal, sup, inf, valor, desv = map(numero, campos[3:8])
        fuera = numero(campos[8]) if len(campos) > 8 else None
        if nominal is None or valor is None:
            raise ValueError(f"Falta nominal/valor en linea {linea}")
        if sup is not None and inf is not None and inf > sup:
            raise ValueError(f"Tolerancias invertidas en linea {linea}")
        cota = cota_de(bloque, pieza)
        evaluacion, bolt, altura = campos[1].strip(), None, None
        # Reglas del piloto: Bolt Eye N170 y signo invertido de B2/B4 (trampas.md). Solo en el 3212.
        if pieza == "3212" and cota == "170" and elemento.isdigit() and 11 <= int(elemento) <= 18:
            code = int(elemento)
            bolt = f"B{(code - 11) % 4 + 1}"
            altura = 1.5 if code <= 14 else 5.0
            evaluacion = "GX" if idx == 1 else "LP_max" if idx == 2 else f"evaluacion_{idx}"
        corregido = (pieza == "3212" and elemento in {"32", "34"}
                     and campos[1].strip().casefold().replace("ó", "o") == "posicion z"
                     and abs(nominal) > 1 and nominal * valor < 0 and abs(abs(valor) - abs(nominal)) < 0.5)
        original_val, original_desv, original_fuera = valor, desv, fuera
        if corregido:
            valor = -valor
            desv = valor - nominal
            fuera = (min(desv - inf, 0) if desv < inf else max(desv - sup, 0) if desv > sup else 0) if inf is not None and sup is not None else None
        salida.append(dict(fila=linea, bloque=bloque, ocurrencia=ocurrencias.get(bloque, 1), indice=idx,
                           cota=cota, elemento_cmm=elemento, caracteristica=campos[1].strip(), evaluacion=evaluacion,
                           nominal=nominal, tol_sup=sup, tol_inf=inf, valor=valor, desviacion=desv, fuera=fuera,
                           valor_original=original_val, desviacion_original=original_desv, fuera_original=original_fuera,
                           corregido=int(corregido), bolt=bolt, altura=altura))
    if not salida:
        raise ValueError("No hay evaluaciones CMM")
    return salida


def es_comparativa(datos: bytes) -> bool:
    filas = csv.reader(texto_de(datos).splitlines(), delimiter=";")
    return any(sum(bool(CAVIDAD.fullmatch(x.strip())) for x in f[1:]) >= 2 for f in filas)


def leer_comparativa(datos: bytes, pieza: str) -> list[dict]:
    """Comparativa «totes»: una columna por cavidad, rotulada en la cabecera del primer bloque.

    Tres disposiciones en los originales, que se distinguen por la columna 2: con texto (caracteristica
    en aleman o vacia), la nominal va en la 3; si en todas las filas es un numero (3197 `nozzle`), en la 2.
    Las tolerancias solo se toman si hay dos numeros entre la nominal y la primera cavidad.
    El lector del backend (`measurement_tables.csv_rows`, 09/11/2026) no separa los titulos pegados al
    primer valor: asigna los POINT de las comparativas del 3212 a N178. Aqui si se separan."""
    filas = list(csv.reader(texto_de(datos).splitlines(), delimiter=";"))
    cabecera = next((f for f in filas if sum(bool(CAVIDAD.fullmatch(x.strip())) for x in f[1:]) >= 2), None)
    if cabecera is None:
        raise ValueError("Sin cabecera de cavidades")
    columnas = [(i, x.strip()) for i, x in enumerate(cabecera) if i > 0 and CAVIDAD.fullmatch(x.strip())]
    primera = columnas[0][0]
    valores = [f for f in filas if len(f) > primera and f[1].strip() and not ";".join(f).startswith(("****", "////"))]
    i_nom = 2 if valores and all(es_numero(f[2]) for f in valores) else 3
    bloque, elemento, idx = "", "", 0
    ocurrencias: dict = {}
    salida = []
    for linea, campos in enumerate(filas, 1):
        if not campos or not any(x.strip() for x in campos):
            continue
        texto = ";".join(campos).strip("; \t")
        if texto.startswith(("****", "////")):
            continue
        if not campos[1].strip():
            bloque = campos[0].strip()
            elemento, idx = "", 0
            ocurrencias[bloque] = ocurrencias.get(bloque, 0) + 1
            continue
        if len(campos) <= primera:
            raise ValueError(f"Fila sin columnas de cavidad en linea {linea}")
        cabeza = campos[0].strip()
        if re.search(r"\s", cabeza):
            # Titulo del bloque en la misma linea que su primer valor (3212: «POINT 1 -> 1.35-0.05 MIN/MAX;Cálculo...»).
            # En el export individual va en su propia linea; los elementos son numeros, nunca llevan espacios.
            bloque, elemento, idx = cabeza, "", 0
            ocurrencias[bloque] = ocurrencias.get(bloque, 0) + 1
            cabeza = ""
        idx += 1
        elemento = cabeza or elemento
        nominal = numero(campos[i_nom])
        sup = inf = None
        if i_nom + 2 < primera and es_numero(campos[i_nom + 1]) and es_numero(campos[i_nom + 2]):
            sup, inf = numero(campos[i_nom + 1]), numero(campos[i_nom + 2])
        if nominal is None:
            raise ValueError(f"Falta nominal en linea {linea}")
        for col, rotulo in columnas:
            valor = numero(campos[col]) if col < len(campos) else None
            if valor is None:
                continue
            salida.append(dict(fila=linea, columna=col, rotulo=rotulo, bloque=bloque, ocurrencia=ocurrencias.get(bloque, 1),
                               indice=idx, cota=cota_de(bloque, pieza), elemento_cmm=elemento,
                               caracteristica=campos[1].strip(), nominal=nominal, tol_sup=sup, tol_inf=inf, valor=valor))
    if not salida:
        raise ValueError("Comparativa sin valores")
    return salida


def leer_puntos(datos: bytes, pieza: str) -> list[dict]:
    """`id;SYM-POINT;marca;a;b;c`: tres coordenadas sin rotulo, en el orden del fichero."""
    bloque, salida = "", []
    for linea, campos in enumerate(csv.reader(texto_de(datos).splitlines(), delimiter=";"), 1):
        texto = ";".join(campos).strip("; \t")
        if not texto or texto.startswith(("****", "////")):
            continue
        if len(campos) >= 6 and campos[1].strip().upper() == "SYM-POINT":
            c1, c2, c3 = map(numero, campos[3:6])
            salida.append(dict(fila=linea, bloque=bloque, cota=cota_de(bloque, pieza), elemento_cmm=campos[0].strip(),
                               tipo=campos[1].strip(), marca=campos[2].strip(), coord_1=c1, coord_2=c2, coord_3=c3))
        elif len(campos) < 4 or not campos[1].strip():
            bloque = texto
        else:
            raise ValueError(f"Fila no reconocida en linea {linea}: {texto[:60]}")
    if not salida:
        raise ValueError("Sin puntos SYM-POINT")
    return salida


def leer_perfil(path: Path) -> dict:
    # pdfplumber groups text independently from the backend's PyMuPDF reader.
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("Se esperaba un perfil de una pagina")
        texto = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2) or ""
    out = {}
    for etiqueta_tabla, campos in [("Contorno", ("tol_inf", "desv_inf", "infr_inf")),
                                   ("CONTORN", ("tol_sup", "desv_sup", "infr_sup"))]:
        matches = re.findall(etiqueta_tabla + r"\s*\((\d+)\)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", texto)
        if len(matches) != 1:
            raise ValueError(f"Tabla {etiqueta_tabla} ambigua o ausente")
        out.update(zip(campos, (numero(v) for v in matches[0][1:])))
        if etiqueta_tabla == "Contorno":
            out["contorno"] = matches[0][0]
    m = re.search(r"YZ\(X\)\s+([-\d.]+)", texto)
    out["media"] = numero(m[1]) if m else None
    fecha = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})", texto)
    out["fecha"] = " ".join(fecha.groups()) if fecha else None
    out["exceso"] = max(abs(out["infr_inf"]), abs(out["infr_sup"]))
    out["pagina"] = 1
    return out


def leer_original(ruta: str, sha: str) -> tuple[Path, bytes]:
    path = Path(original(ruta))
    if os.stat(path).st_file_attributes & NUBE:
        raise ValueError(f"En la nube, no se lee: {ruta}")
    datos = path.read_bytes()
    if hashlib.sha256(datos).hexdigest() != sha:
        raise ValueError(f"Original cambiado desde la biblioteca: {ruta}")
    return path, datos


def construir(con: sqlite3.Connection, comprobar: bool = False) -> dict:
    tablas: dict[str, list] = {"medida_cmm": [], "medida_cmm_comparativa": [], "punto_cmm": [], "medida_contorno": []}
    errores = []
    for doc, pieza, ruta, nombre, sha in con.execute(
            "SELECT id,codigo,ruta,nombre,sha256 FROM documento WHERE codigo IN (%s) AND estado='extraido' AND ext IN ('csv','pdf')"
            " ORDER BY codigo,ruta" % ",".join("?" * len(PIEZAS)), PIEZAS).fetchall():
        perfil = pieza == "3212" and re.fullmatch(r"P([AB])_(\d+)\.pdf", nombre, re.I)
        if not perfil and not nombre.lower().endswith(".csv"):
            continue
        try:
            path, datos = leer_original(ruta, sha)
            if pieza == "3212":
                if perfil or "totes" not in nombre.lower():
                    muestreo, cavidad = contexto(ruta)
                else:  # comparativa: la cavidad sale de cada columna
                    muestreo, cavidad = re.search(r"intern[. _-]*(\d+)", ruta, re.I)[1].zfill(2), None
                condiciones = []
            else:
                muestreo, cavidad, condiciones = contexto_3197(ruta)
            common = dict(documento_id=doc, pieza=pieza, muestreo=muestreo, sha256=sha)
            if perfil:
                tablas["medida_contorno"].append({**common, "cavidad": cavidad, "perfil": perfil[1].upper(),
                                                  "indice": int(perfil[2]), **leer_perfil(path)})
            elif b"SYM-POINT" in datos:
                cav, variante = etiqueta(cavidad, condiciones)
                tablas["punto_cmm"].extend({**common, "cavidad": cav, "variante": variante, **r} for r in leer_puntos(datos, pieza))
            elif es_comparativa(datos):
                for r in leer_comparativa(datos, pieza):
                    m = CAVIDAD.fullmatch(r["rotulo"])
                    cav_col, ciclo = rotulo_cavidad(m)
                    if cavidad and cav_col != cavidad:
                        raise ValueError(f"La ruta dice {cavidad} y la columna {r['rotulo']}")
                    cav, variante = etiqueta(cav_col, condiciones + ([ciclo] if ciclo else []))
                    tablas["medida_cmm_comparativa"].append({**common, "cavidad": cav, "variante": variante, **r})
            else:
                cav, variante = etiqueta(cavidad, condiciones)
                tablas["medida_cmm"].extend({**common, "cavidad": cav, "variante": variante, **r} for r in leer_csv(datos, pieza))
        except (ValueError, OSError) as e:
            errores.append(f"{ruta}: {e}")
    if errores:
        raise SystemExit("No se publica nada:\n" + "\n".join(errores))
    resumen = {t: dict(Counter(r["pieza"] for r in filas)) for t, filas in tablas.items()}
    if comprobar:
        return resumen
    con.executescript(SCHEMA)
    if "variante" not in {r[1] for r in con.execute("PRAGMA table_info(medida_cmm)")}:
        con.execute("ALTER TABLE medida_cmm ADD COLUMN variante TEXT")
    with con:
        for tabla, filas in tablas.items():
            con.execute(f"DELETE FROM {tabla} WHERE pieza IN ({','.join('?' * len(PIEZAS))})", PIEZAS)
            for row in filas:
                names = list(row)
                con.execute(f"INSERT INTO {tabla} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", [row[k] for k in names])
    return resumen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comprobar", action="store_true", help="leer originales sin publicar tablas")
    args = p.parse_args()
    with sqlite3.connect(BD.resolve().as_uri() + ("?mode=ro" if args.comprobar else "?mode=rw"), uri=True) as con:
        print(json.dumps(construir(con, args.comprobar), ensure_ascii=False))


if __name__ == "__main__":
    main()
