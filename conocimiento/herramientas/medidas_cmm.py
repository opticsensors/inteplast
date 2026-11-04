"""Lectores independientes de CSV CMM y perfiles PA/PB documentados del 3212.

Solo lee originales. Publica tablas derivadas atomicas en la biblioteca.
No importa lectores de la app. Conserva valor original, coordenada y SHA-256.
Uso: python conocimiento/herramientas/medidas_cmm.py [--comprobar]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

from comun import BD, original

SCHEMA = """
CREATE TABLE IF NOT EXISTS medida_cmm (
 documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, fila INTEGER,
 bloque TEXT, ocurrencia INTEGER, indice INTEGER, cota TEXT, elemento_cmm TEXT,
 caracteristica TEXT, evaluacion TEXT, nominal REAL, tol_sup REAL, tol_inf REAL,
 valor REAL, desviacion REAL, fuera REAL, valor_original REAL, desviacion_original REAL,
 fuera_original REAL, corregido INTEGER, bolt TEXT, altura REAL, sha256 TEXT,
 PRIMARY KEY(documento_id,fila)
);
CREATE INDEX IF NOT EXISTS medida_cmm_pieza_cota ON medida_cmm(pieza,cota,muestreo,cavidad);
CREATE TABLE IF NOT EXISTS medida_contorno (
 documento_id INTEGER PRIMARY KEY, pieza TEXT, muestreo TEXT, cavidad TEXT,
 perfil TEXT, indice INTEGER, contorno TEXT, tol_inf REAL, tol_sup REAL,
 desv_inf REAL, desv_sup REAL, infr_inf REAL, infr_sup REAL, media REAL,
 fecha TEXT, exceso REAL, pagina INTEGER, sha256 TEXT
);
"""


def numero(texto: str) -> float | None:
    texto = texto.strip().replace(",", ".")
    if not texto:
        return None
    if not re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", texto):
        raise ValueError(f"Numero no reconocido: {texto!r}")
    value = float(texto)
    if not math.isfinite(value):
        raise ValueError("Numero no finito")
    return value


def contexto(ruta: str) -> tuple[str, str]:
    muestreo = re.search(r"intern[. _-]*(\d+)", ruta, re.I)
    cavidades = re.findall(r"(?:^|[/_ ]|3212)c(?:av)?[. _]*(\d+)(?=[/_. -]|$)", ruta, re.I)
    if not muestreo or len(set(cavidades)) != 1:
        raise ValueError(f"Contexto de muestreo/cavidad ambiguo: {ruta}")
    return muestreo[1].zfill(2), f"c{int(cavidades[0])}"


def leer_csv(datos: bytes) -> list[dict]:
    """Conserva las 211 evaluaciones, incluidas POINT/GLOBAL y diagnosticos X/Z."""
    texto = datos.decode("cp1252")
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
        cotas = re.findall(r"\bN(\d+(?:\.\d+)?)", bloque, re.I)
        cota = cotas[0] if len(set(cotas)) == 1 else None
        if bloque.startswith(("POINT ", "GLOBAL ")):
            cota = "165"
        evaluacion, bolt, altura = campos[1].strip(), None, None
        if cota == "170" and elemento.isdigit() and 11 <= int(elemento) <= 18:
            code = int(elemento)
            bolt = f"B{(code - 11) % 4 + 1}"
            altura = 1.5 if code <= 14 else 5.0
            evaluacion = "GX" if idx == 1 else "LP_max" if idx == 2 else f"evaluacion_{idx}"
        corregido = (elemento in {"32", "34"} and campos[1].strip().casefold().replace("ó", "o") == "posicion z"
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


def leer_perfil(path: Path) -> dict:
    # pdfplumber groups text independently from the backend's PyMuPDF reader.
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("Se esperaba un perfil de una pagina")
        texto = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2) or ""
    out = {}
    for etiqueta, campos in [("Contorno", ("tol_inf", "desv_inf", "infr_inf")),
                              ("CONTORN", ("tol_sup", "desv_sup", "infr_sup"))]:
        matches = re.findall(etiqueta + r"\s*\((\d+)\)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", texto)
        if len(matches) != 1:
            raise ValueError(f"Tabla {etiqueta} ambigua o ausente")
        out.update(zip(campos, (numero(v) for v in matches[0][1:])))
        if etiqueta == "Contorno":
            out["contorno"] = matches[0][0]
    m = re.search(r"YZ\(X\)\s+([-\d.]+)", texto)
    out["media"] = numero(m[1]) if m else None
    fecha = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})", texto)
    out["fecha"] = " ".join(fecha.groups()) if fecha else None
    out["exceso"] = max(abs(out["infr_inf"]), abs(out["infr_sup"]))
    out["pagina"] = 1
    return out


def construir(con: sqlite3.Connection, comprobar: bool = False) -> dict:
    cmm, perfiles = [], []
    for doc, ruta, nombre, sha in con.execute(
            "SELECT id,ruta,nombre,sha256 FROM documento WHERE codigo='3212' AND estado='extraido' AND ext IN ('csv','pdf') ORDER BY ruta"):
        perfil = re.fullmatch(r"P([AB])_(\d+)\.pdf", nombre, re.I)
        individual = nombre.lower().endswith(".csv") and "totes" not in nombre.lower()
        if not perfil and not individual:
            continue
        path = Path(original(ruta))
        datos = path.read_bytes()
        if hashlib.sha256(datos).hexdigest() != sha:
            raise ValueError(f"Original cambiado desde la biblioteca: {ruta}")
        muestreo, cavidad = contexto(ruta)
        common = dict(documento_id=doc, pieza="3212", muestreo=muestreo, cavidad=cavidad, sha256=sha)
        if perfil:
            perfiles.append({**common, "perfil": perfil[1].upper(), "indice": int(perfil[2]), **leer_perfil(path)})
        else:
            cmm.extend({**common, **row} for row in leer_csv(datos))
    if comprobar:
        return {"medida_cmm": len(cmm), "medida_contorno": len(perfiles)}
    con.executescript(SCHEMA)
    with con:
        for tabla, filas in [("medida_cmm", cmm), ("medida_contorno", perfiles)]:
            con.execute(f"DELETE FROM {tabla} WHERE pieza='3212'")
            for row in filas:
                names = list(row)
                con.execute(f"INSERT INTO {tabla} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", [row[k] for k in names])
    return {"medida_cmm": len(cmm), "medida_contorno": len(perfiles)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comprobar", action="store_true", help="leer originales sin publicar tablas")
    args = p.parse_args()
    with sqlite3.connect(BD.resolve().as_uri() + ("?mode=ro" if args.comprobar else "?mode=rw"), uri=True) as con:
        print(json.dumps(construir(con, args.comprobar), ensure_ascii=False))


if __name__ == "__main__":
    main()
