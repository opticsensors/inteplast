"""CMM block CSV parsing, source identities and the documented B2/B4 sign correction."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


ENCODING = "cp1252"  # los CSV de la CMM NO son utf-8


def sample_number(ruta: Path) -> str:
    """'support intern.01' / 'support.intern.08' -> '01' / '08'."""
    for parte in ruta.parts:
        m = re.search(r"intern[.\s]*(\d+)", parte, re.IGNORECASE)
        if m:
            return m.group(1).zfill(2)
    return "??"


def cavity_number(ruta: Path) -> str | None:
    """Saca la cavidad del nombre del fichero o, si no esta, de la carpeta padre.

    Hay tres grafias en el 3212: '3212_c13.csv', '3212c14.csv' y '13_3212.csv'.
    Y en intern.05 las carpetas c15/ y c16/ tienen ficheros con el MISMO nombre,
    asi que la carpeta padre es la unica pista.
    """
    for texto in (ruta.stem, ruta.parent.name):
        m = re.search(r"^(\d{2})[_\s]", texto)  # 13_3212
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
        m = re.search(r"[cC][._\s]?(\d{2})", texto)  # 3212_c13 / 3212c14 / C13
        if m and 13 <= int(m.group(1)) <= 16:
            return f"c{m.group(1)}"
    return None


def discover(raiz: Path) -> list[dict[str, Any]]:
    """Los 16 CSV de cavidad, ordenados por muestreo y cavidad.

    Los 3 'totes.csv' quedan fuera a proposito: tienen una columna por cavidad pero
    PIERDEN la desviacion, el fuera-de-tolerancia y el semaforo. El CSV de cavidad es
    estrictamente mas rico.
    """
    ficheros = []
    for ruta in raiz.rglob("*.csv"):
        if "totes" in ruta.stem.lower():
            continue
        cavidad = cavity_number(ruta)
        if cavidad is None:
            logger.info(f"  [aviso] no se deduce la cavidad, se salta: {ruta.name}")
            continue
        ficheros.append(
            {
                "ruta": ruta,
                "muestreo": sample_number(ruta),
                "cavidad": cavidad,
                "rel": ruta.relative_to(raiz.parent).as_posix(),
            }
        )
    return sorted(ficheros, key=lambda f: (f["muestreo"], f["cavidad"]))


def parse_float(texto: str) -> float | None:
    texto = texto.strip()
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def read_csv(ruta: Path) -> pd.DataFrame:
    """Aplana el export por bloques a una tabla de una fila por medicion.

    Regla de deteccion (la que funciona): una linea es DATO si tiene >=8 campos y el
    campo 2 (caracteristica) no esta vacio. Ojo: muchas filas de dato traen el ID de
    elemento CMM VACIO ( ';Calculo de formula;;1.350;...' ), asi que mirar el campo 1
    para decidir da falsos positivos.
    """
    filas: list[dict[str, Any]] = []
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
                    "nominal": parse_float(campos[3]),
                    "tol_sup": parse_float(campos[4]),
                    "tol_inf": parse_float(campos[5]),
                    "medido": parse_float(campos[6]),
                    "desviacion": parse_float(campos[7]),
                    "fuera_tol": parse_float(campos[8]),
                    "barra": campos[9].strip(),
                }
            )

    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla

    # NOK: la columna 9 trae valor, o la barra ASCII se sale por un lado.
    tabla["nok"] = tabla["fuera_tol"].notna() | tabla["barra"].str.contains(
        r"<<|>>", regex=True
    )

    # Error de signo conocido del export (bolts B2 y B4, 'Posicion Z'): el nominal es
    # +31 y la maquina escribe -30,990, con lo que la desviacion sale -61,99. Esta en
    # los cuatro muestreos: NO es una pieza mala.
    tabla["signo_sospechoso"] = [
        bool(
            id_cmm in {"32", "34"}
            and caracteristica.casefold().replace("ó", "o") == "posicion z"
            and nom is not None
            and med is not None
            and abs(nom) > 1
            and nom * med < 0
            and abs(abs(med) - abs(nom)) < 0.5
        )
        for id_cmm, caracteristica, nom, med in zip(
            tabla["id_cmm"],
            tabla["caracteristica"],
            tabla["nominal"],
            tabla["medido"],
            strict=True,
        )
    ]
    for campo in ("medido", "desviacion", "fuera_tol", "barra", "nok"):
        tabla[f"{campo}_original"] = tabla[campo]
    tabla["signo_corregido"] = False

    tabla["etiqueta"] = [
        f"{b}  [{i}] {c}" + (f"  #{d}" if d else "")
        for b, i, c, d in zip(
            tabla["bloque"],
            tabla["idx"],
            tabla["caracteristica"],
            tabla["id_cmm"],
            strict=True,
        )
    ]
    tabla["clave"] = (
        tabla["bloque"]
        + "#"
        + tabla["ocurrencia"].astype(str)
        + "||"
        + tabla["idx"].astype(str)
    )
    if tabla["clave"].duplicated().any():
        raise ValueError(
            f"claves duplicadas en {ruta.name}: no se podra cruzar con otros muestreos"
        )
    return tabla


def correct_sign(tabla: pd.DataFrame) -> pd.DataFrame:
    """Corrige B2/B4 y sus estados derivados, conservando los valores del export.

    Aplicarla otra vez no vuelve a invertir los valores ya corregidos.
    """
    tabla = tabla.copy()
    if tabla.empty:
        return tabla
    afectadas = tabla["signo_sospechoso"] & ~tabla["signo_corregido"]
    if tabla.loc[afectadas, ["tol_inf", "tol_sup"]].isna().any().any():
        raise ValueError(
            "No se puede corregir el signo sin ambos limites de tolerancia"
        )
    tabla.loc[afectadas, "medido"] = -tabla.loc[afectadas, "medido"]
    tabla.loc[afectadas, "desviacion"] = (
        tabla.loc[afectadas, "medido"] - tabla.loc[afectadas, "nominal"]
    ).round(12)
    for indice, fila in tabla.loc[afectadas].iterrows():
        if fila["desviacion"] < fila["tol_inf"]:
            exceso, barra = fila["desviacion"] - fila["tol_inf"], "<<---+-----"
        elif fila["desviacion"] > fila["tol_sup"]:
            exceso, barra = fila["desviacion"] - fila["tol_sup"], "-----+--->>"
        else:
            exceso, barra = None, "OK (recalculado)"
        tabla.loc[indice, "fuera_tol"] = exceso
        tabla.loc[indice, "nok"] = exceso is not None
        tabla.loc[indice, "barra"] = barra
    tabla.loc[afectadas, "signo_corregido"] = True
    return tabla
