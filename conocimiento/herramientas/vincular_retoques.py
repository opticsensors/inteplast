"""Experimento de solo lectura: relacionar un intern con una ronda de retoques.

Sin argumentos, lista las propuestas. --pieza muestra también las abstenciones.
--evaluar compara al final con la tabla de referencia de retoques-por-muestreo.md.
"""
import argparse
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass
from itertools import groupby
from pathlib import PurePosixPath

from cadena_correcciones import ARCHIVADA, MUESTREO, numeros_de_plan, serie_de
from comun import BD, CONOCIMIENTO


@dataclass(frozen=True)
class Vinculo:
    plan: int
    metodo: str
    evidencia: str
    revision: str = ""
    cavidades: str = ""


def normalizar(texto):
    return " ".join(unicodedata.normalize("NFKD", texto.casefold())
                    .encode("ascii", "ignore").decode().split())


ORDEN = r"(\d{1,2}(?:st|nd|rd|th)|first|second|third|fourth)"
ACCION = r"(?:corrections?|retouch(?:es)?)\b"
NUMERO = r"(?:n(?:r|o|um)?[.°º]?\s*|#)(\d{1,2})\b"
DESPUES = re.compile(
    r"(?<![a-z])(?:after|despres de[ls]?|despues de[ls]?)\s+(?:(?:plan? de|pa de|mould|mold)\s+)?"
    r"(?:retocs?|retoques?|correccions?|correcciones|corrections?)\s*" + NUMERO
)
ORDINAL = re.compile(r"(?:(?<![a-z])after\s+|^lot\s+)" + ORDEN + r"\s+" + ACCION)
LOTE_FECHADO = re.compile(r"^" + ORDEN + r"\s+" + ACCION + r"\s+\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")
ARCHIVO_PLAN = re.compile(r"\bmold\s+correction[_ -]+(\d{1,2})(?=[_. -]|$)")
MODIFICADO = re.compile(r"\b(?:modificat(?:s|des)?|modificad[oa]s?|modified)\b")
NO_EJECUTADO = re.compile(r"\b(?:not|no|sense|without|pending|pendent|planned|previst|before|abans|will|to be)\b")
CODIGO_EN_PLAN = re.compile(r"(?<![a-z0-9])p(\d{4})(?!\d)", re.I)


def leer_mencion(texto):
    """Devuelve todos los planes reconocidos. Dos números distintos requieren revisión."""
    normal = normalizar(texto)
    if NO_EJECUTADO.search(normal):
        return set(), "", ""
    planes = {int(n) for n in DESPUES.findall(normal)}
    for ordinal in ORDINAL.findall(normal) + LOTE_FECHADO.findall(normal):
        letras = {"first": 1, "second": 2, "third": 3, "fourth": 4}
        planes.add(letras[ordinal] if ordinal in letras else int(re.match(r"\d+", ordinal)[0]))
    if MODIFICADO.search(normal):
        planes.update(map(int, ARCHIVO_PLAN.findall(normal)))
    rev = re.search(r"\brev[. _-]*(\d+)\b|_rev(\d+)\b", normal)
    cav = re.search(r"\b(?:nomes|solo|only)\s+(?:(?:la|the)\s+)?cavit(?:at|y|dad)\s+(\d+)\b", normal)
    todas = re.search(r"\b(?:totes les cavitats|todas las cavidades|all cavities)\b", normal)
    return planes, (rev[1] or rev[2]) if rev else "", cav[1] if cav else "todas" if todas else ""


def informes(db):
    grupos = defaultdict(list)
    for r in db.execute("""SELECT id, duplicado_de, codigo, nombre FROM documento
                WHERE carpeta_norm='metrologia' AND ext IN ('xls','xlsx','xlsm','xlsb')
                ORDER BY ruta"""):
        m = MUESTREO.search(r["nombre"])
        if m:
            clave = (r["codigo"], serie_de(r["nombre"]), int(m[1]))
            grupos[clave].append(r)
    return grupos


def columna(n):
    letras = ""
    while n:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def notas_de_informe(db, documento, intern):
    id_celdas = documento["duplicado_de"] or documento["id"]
    bloque = None
    for hoja, fila, col, texto in db.execute("""SELECT hoja, fila, col, valor FROM celda
            WHERE documento_id=? AND numero IS NULL AND valor IS NOT NULL AND
            ((upper(trim(hoja))='HISTORY' AND col IN (1,6)) OR fila<=12
            OR (upper(trim(hoja))='INTRO' AND fila IN (53,54))) ORDER BY hoja,fila,col""", (id_celdas,)):
        history = hoja.strip().upper() == "HISTORY"
        if history:
            if col == 1:
                encabezado = re.match(r"^(?:informe|report)\b(.*)", normalizar(texto))
                if encabezado:
                    numero = re.fullmatch(r"\s*(?:n[o.]?\s*)?(\d+)", encabezado[1])
                    bloque = int(numero[1]) if numero else None
            if col != 6 or bloque != intern:
                continue
        planes, revision, cavidades = leer_mencion(texto)
        if planes:
            localizador = f"{documento['nombre']} · {hoja}!{columna(col)}{fila}"
            for plan in sorted(planes):
                yield normalizar(texto), history, Vinculo(plan, "nota", localizador, revision, cavidades)


def vinculos_por_nota(db, grupos):
    resultado = {}
    conflictos = set()
    anteriores = defaultdict(set)
    for clave, documentos in sorted(grupos.items()):
        pieza, serie, intern = clave
        vistos = anteriores[pieza, serie]
        actuales = set()
        menciones = []
        for doc in documentos:
            codigo_explicito = re.search(r"(?<!\d)(\d{4})[-_ ]\d{2}(?=[ _.-]*(?:int))", doc["nombre"], re.I)
            if codigo_explicito and codigo_explicito[1] != pieza:
                continue
            for texto, history, vinculo in notas_de_informe(db, doc, intern):
                if history or texto not in vistos:
                    menciones.append(vinculo)
                if not history:
                    actuales.add(texto)
        vistos.update(actuales)
        if len({v.plan for v in menciones}) > 1:
            conflictos.add(clave)
        elif menciones:
            revisiones = {v.revision for v in menciones if v.revision}
            cavidades = {v.cavidades for v in menciones if v.cavidades}
            # Una discrepancia de alcance deja abierto ese campo, aun si coincide la ronda.
            fuentes = list(dict.fromkeys(v.evidencia for v in menciones))
            resultado[clave] = Vinculo(menciones[0].plan, "nota", " / ".join(fuentes),
                                       revisiones.pop() if len(revisiones) == 1 else "",
                                       cavidades.pop() if len(cavidades) == 1 else "")
    return resultado, conflictos


def plan_utilizable(nombre, ruta, pieza):
    codigos = set(CODIGO_EN_PLAN.findall(nombre))
    return (not ARCHIVADA.search(ruta) and (not codigos or codigos == {pieza})
            and not re.search(r"(?<![a-z])draft(?![a-z])", nombre, re.I))


def vinculos_por_repaso(db, grupos):
    """Una diapositiva compara una ronda identificada con la propuesta de la ronda actual."""
    adjuntos = defaultdict(dict)
    for pieza, ruta, nombre in db.execute("""SELECT codigo,ruta,nombre FROM documento WHERE
            carpeta_norm='retoques' AND ext IN ('xls','xlsx','xlsm','xlsb') ORDER BY ruta"""):
        m = MUESTREO.search(nombre)
        if m:
            clave = (pieza, serie_de(nombre), int(m[1]))
            adjuntos[PurePosixPath(ruta).parent][clave] = ruta

    anteriores = re.compile(r"\bloop\s+(\d+)\s*:\s*before (?:the )?(?:last|previous) correction\b")
    propuestas = re.compile(r"\bloop\s+(\d+)\s*:\s*proposal for correction\b")
    resultado_previo = re.compile(r"\b(?:corrected (?:not enough|too much)|was (?:not )?corrected)\b")
    repaso = defaultdict(dict)
    for r in db.execute("""SELECT d.codigo,d.nombre,d.ruta,p.diapositiva,p.plan,p.texto
            FROM perfil_correccion p JOIN documento d ON d.id=p.documento_id
            WHERE d.carpeta_norm='retoques' AND lower(p.texto) LIKE '%loop%'
            ORDER BY d.ruta,p.diapositiva"""):
        carpeta = PurePosixPath(r["ruta"]).parent
        if len(adjuntos[carpeta]) != 1 or not plan_utilizable(r["nombre"], r["ruta"], r["codigo"]):
            continue
        clave, excel = next(iter(adjuntos[carpeta].items()))
        if clave not in grupos:
            continue
        texto = normalizar(r["texto"])
        previo = {int(n) for n in anteriores.findall(texto)}
        actual = {int(n) for n in propuestas.findall(texto)}
        if (len(previo) != 1 or len(actual) != 1 or previo == actual or not resultado_previo.search(texto)
                or actual != numeros_de_plan(r["nombre"], r["plan"])):
            continue
        plan = previo.pop()
        evidencia = f"{r['ruta']} · diap. {r['diapositiva']} · Excel adjunto {PurePosixPath(excel).name}"
        repaso[clave].setdefault(plan, Vinculo(plan, "repaso en PowerPoint", evidencia))
    return repaso


def vinculos_por_medidas(db, grupos):
    """Cada candidatura se calcula en un solo PowerPoint, sin acumular revisiones."""
    filas = db.execute("""SELECT c.*, p.plan, d.nombre, d.ruta
        FROM cadena_correccion c JOIN documento d ON d.id=c.documento_id
        JOIN perfil_correccion p USING (documento_id, diapositiva)
        WHERE d.carpeta_norm='retoques' AND d.ext='pptx'
        ORDER BY c.documento_id,c.diapositiva,c.cota""")
    candidatos = defaultdict(dict)
    for _, acciones in groupby(filas, key=lambda r: r["documento_id"]):
        acciones = list(acciones)
        doc = acciones[0]
        if (not plan_utilizable(doc["nombre"], doc["ruta"], doc["pieza"])
                or re.search(r"\bresults?\b", doc["nombre"].replace("_", " "), re.I)):
            continue
        planes = set().union(*(numeros_de_plan(doc["nombre"], r["plan"]) for r in acciones))
        planes.update(int(n) for n in re.findall(r"(?<![a-z])loop[\s_-]*(\d+)", doc["nombre"], re.I))
        if len(planes) != 1:
            continue
        plan = planes.pop()
        total = len({r["cota"] for r in acciones})
        cotas = defaultdict(set)
        for r in acciones:
            if (r["validacion_estado"] != "nueva" or r["fuente_origen"] != "xls_carpeta"
                    or r["depende_copia"] or r["origen_muestreo"] >= r["validacion_muestreo"]
                    or not r["fecha_orden"] or not r["validacion_fecha"] or r["validacion_fecha"] < r["fecha_orden"]
                    or re.search(r"sin comprobar|sin validez temporal|otra pieza|de que componente", r["avisos"] or "")):
                continue
            # Las cotas deben coincidir en la misma copia de Excel.
            clave = (r["pieza"], r["serie"], r["validacion_muestreo"])
            if clave in grupos:
                cotas[clave, r["validacion_documento_id"]].add(r["cota"])
        for (clave, id_excel), medidas in cotas.items():
            cantidad = len(medidas)
            if cantidad < 2 or cantidad * 2 < total:
                continue
            evidencia = (f"{doc['nombre']} · Excel #{id_excel} · {cantidad}/{total} cotas "
                         f"identificadas en el PowerPoint ({', '.join(sorted(medidas))})")
            calidad = (cantidad / total, cantidad)
            if plan not in candidatos[clave] or calidad > candidatos[clave][plan][0]:
                candidatos[clave][plan] = calidad, Vinculo(plan, "medidas", evidencia)
    return {k: next(iter(planes.values()))[1] for k, planes in candidatos.items() if len(planes) == 1}


def leer_referencia():
    lineas = (CONOCIMIENTO / "retoques-por-muestreo.md").read_text(encoding="utf-8").splitlines()
    inicio = lineas.index("| Pieza | Serie | Intern | Relación | Plan | Revisión | Cavidades |") + 2
    etiquetas = []
    for linea in lineas[inicio:]:
        if not linea.startswith("|"):
            break
        pieza, serie, intern, tipo, plan, rev, cav = (s.strip() for s in linea.strip("|").split("|"))
        if tipo not in {"posterior", "origen", "sin medición"} or (plan == "—") != (tipo == "sin medición"):
            raise ValueError(f"Etiqueta no válida: {linea}")
        etiquetas.append(((pieza, serie, int(intern)), tipo, None if plan == "—" else int(plan), rev, cav))
    if not etiquetas or len(set(etiquetas)) != len(etiquetas):
        raise ValueError("Tabla de referencia vacía o con etiquetas duplicadas")
    return etiquetas


def identificador(clave):
    return f"{clave[0]}-{clave[1]} intern.{clave[2]:02d}"


def evaluar(nombre, propuestas, referencia):
    correctos = equivocados = ausentes = controles = errores_control = 0
    alcance = Counter()
    contrastados = set()
    print(f"\n{nombre}")
    for clave, relacion, esperado, rev, cav in referencia:
        v = propuestas.get(clave)
        if relacion == "posterior":
            if not v:
                ausentes += 1
                print(f"  Sin propuesta · {identificador(clave)} · plan esperado {esperado}")
            else:
                contrastados.add(clave)
                if v.plan != esperado:
                    equivocados += 1
                    print(f"  Plan erróneo · {identificador(clave)} · propone {v.plan}, esperado {esperado}")
                else:
                    correctos += 1
            for campo, etiqueta in (("revision", rev), ("cavidades", cav)):
                if etiqueta != "—":
                    valor = getattr(v, campo) if v and v.plan == esperado else ""
                    alcance["correcto" if valor == etiqueta else "erróneo" if valor else "sin resolver"] += 1
        else:
            controles += 1
            if v and (relacion == "sin medición" or v.plan == esperado):
                contrastados.add(clave)
                errores_control += 1
                print(f"  Falso vínculo · {identificador(clave)} · plan {v.plan} · {relacion}")
    print(f"  Vínculos documentados: {correctos} aciertos, {equivocados} planes erróneos, {ausentes} sin propuesta.")
    print(f"  Controles: {errores_control} vínculos indebidos entre {controles} controles.")
    print(f"  Revisión/cavidades: {dict(alcance)}.")
    print(f"  Otras propuestas sin etiqueta para ese plan: {len(propuestas.keys() - contrastados)}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluar", action="store_true")
    parser.add_argument("--pieza", help="limita la salida y la evaluación al código indicado")
    args = parser.parse_args()
    with closing(sqlite3.connect(BD.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        grupos = informes(db)
        if args.pieza:
            grupos = {k: v for k, v in grupos.items() if k[0] == args.pieza}
        medidas = vinculos_por_medidas(db, grupos)
        notas, conflictos = vinculos_por_nota(db, grupos)
        repasos = vinculos_por_repaso(db, grupos)
    documentales = dict(notas)
    for clave, planes in repasos.items():
        if len(planes) > 1 or (clave in notas and notas[clave].plan not in planes):
            conflictos.add(clave)
        else:
            documentales.setdefault(clave, next(iter(planes.values())))
    # La evidencia escrita prevalece sobre una coincidencia de cotas.
    combinadas = {k: v for k, v in (medidas | documentales).items() if k not in conflictos}
    print(f"{len(grupos)} muestreos · {len(notas)} con nota de plan · {len(medidas)} candidatos por medidas · "
          f"{len(repasos)} con repaso en PowerPoint · {len(combinadas)} propuestas combinadas · "
          f"{len(conflictos)} con documentos incompatibles")
    if not args.evaluar or args.pieza:
        for clave in sorted(grupos if args.pieza else combinadas):
            v = combinadas.get(clave)
            if v:
                alcance = (f" rev{v.revision}" if v.revision else "") + (f" · cav. {v.cavidades}" if v.cavidades else "")
                print(f"{identificador(clave)} · plan {v.plan}{alcance} · {v.metodo} · {v.evidencia}")
            else:
                print(f"{identificador(clave)} · sin propuesta")
    if args.evaluar:
        referencia = [r for r in leer_referencia() if not args.pieza or r[0][0] == args.pieza]
        if any(r[0] not in grupos for r in referencia):
            raise ValueError("Un informe etiquetado falta en el inventario")
        evaluar("Solo coincidencia de medidas", medidas, referencia)
        evaluar("Notas de Excel, repaso en PowerPoint y coincidencia de medidas", combinadas, referencia)


if __name__ == "__main__":
    main()
