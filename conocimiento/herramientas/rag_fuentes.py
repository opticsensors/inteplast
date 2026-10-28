"""Fragmentos con procedencia para el RAG de conocimiento/ (solo lee sus fuentes).

Colecciones: fichas de conocimiento/ (vigentes, revisiones fechadas e historial), hallazgos.jsonl,
docs/ (documentacion de la aplicacion, aparte) y la biblioteca SQLite: texto extraido, contexto de
hojas, metadatos CAD e inventario de lo no interpretado. Referencia: conocimiento/rag.md.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath

LIMITE = 1400        # caracteres por fragmento (~500 tokens; embeddinggemma admite 2048)
LIMITE_TITULO = 160
RECETA = "rag-v1"    # subirla al cambiar segmentacion o prefijos: invalida todos los vectores
MENCIONES = "menciones-v2"   # subirla al cambiar `menciones`: reescribe el indice sin recalcular vectores

# Vigencia explicita. Lo no listado de conocimiento/ es ficha tematica vigente (README: «las fichas
# tematicas recogen el conocimiento vigente»); en docs/ lo no listado toma el estado de docs/README.md.
VIGENCIA = {
    "conocimiento/AVANCE.md": ("historial", "registro de trabajo; sus cifras no son el estado actual (conocimiento/README.md)"),
    "conocimiento/0-bolt-eye/otros-proyectos.md": ("historial", "inventario de agosto de 2026; su nota remite a las fichas actuales de cada pieza"),
    "conocimiento/0-bolt-eye/3212/revision-2026-09-17.md": ("revision_fechada", "revision del 17/09/2026 citada como evidencia por las fichas vigentes; contrastar con la ficha tematica, puede estar superada"),
    "docs/revision-2026-09-15.md": ("historial", "informe historico (docs/README.md, Historial)"),
    "docs/revision-2026-10-26.md": ("historial", "registro de la revision documental (docs/README.md, Historial)"),
    "docs/acta-reunion-2026-09-24.md": ("historial", "registro de acuerdos, no implementacion (docs/README.md, Historial)"),
}
FECHADO = re.compile(r"(revision|acta[\w-]*)-\d{4}-\d{2}-\d{2}")

TIPOS_TEXTO = ("pagina", "diapositiva", "parrafo", "tabla", "cabecera", "cuerpo", "resumen", "entradas", "destino")
TIPOS_DELEGADOS = ("fila", "lineas", "cadenas")   # solo busqueda literal sobre elemento_fts
# Estados con extraccion vigente. 'pendiente' y 'error' conservan elementos de una extraccion anterior que ya no
# corresponde al fichero; 'eliminado' ya no esta en Exemples (inventariar.py). Ninguno aporta contenido.
VIGENTES = ("extraido", "solo_metadatos", "sin_texto")
NO_VIGENTES = {
    "pendiente": "pendiente de extraer: el original cambio y no se usa el contenido de la extraccion anterior",
    "error": "error de lectura: no se usa el contenido de extracciones anteriores",
    "eliminado": "eliminado de Exemples",
}
ERROR_EXCEL = re.compile(r"#(REF!|N/A|VALUE!|DIV/0!|NAME\?|NUM!|NULL!)")
CAD ={"stp", "step", "stl", "dxf", "igs", "iges", "catpart", "catdrawing", "catproduct"}
HOJAS = {"xls", "xlsx", "xlsm", "ods", "csv"}
CATIA = {"catpart", "catdrawing", "catproduct"}

ALCANCE_CAD = {
    "step": "Caja de los CARTESIAN_POINT referenciados por VERTEX_POINT (o de todos los puntos si no hay "
            "vertices) y recuento de entidades del fichero; no es la caja del solido ni una medicion.",
    "stl": "Triangulos y caja de la malla; no identifica cotas ni es una medicion de la pieza.",
    "dxf": "Entidades, vertices y caja de las entidades (los perfiles CMM son POLYLINE 3D); no identifica cotas.",
    "igs": "Solo recuento de entidades por tipo IGES; sin caja ni geometria interpretada.",
    "catia": "Sin geometria extraida: solo version de CATIA y cadenas legibles del binario.",
    "nube": "Minimos y maximos por columna de la nube de puntos; no identifica cotas.",
}
ANCHO_CAD = {"productos": 400, "cabecera": 300}   # recorte de cada texto en la tarjeta CAD


@dataclass
class Fragmento:
    clave: str
    coleccion: str
    tipo_fuente: str
    contenido: str
    titulo: str | None = None
    ruta: str | None = None
    raiz: str = "repo"                 # repo | exemples
    seccion: str | None = None
    localizador: str | None = None
    documento_id: int | None = None
    feature: str | None = None
    pieza: str | None = None
    codigos: tuple[str, ...] = ()
    carpeta: str | None = None
    revision: str | None = None
    revision_origen: str | None = None
    vigencia: str = "no_aplica"
    clasificacion: str | None = None
    naturaleza: str = "extraido"
    estado_hallazgo: str | None = None
    estado_doc: str | None = None
    sha256_original: str | None = None
    duplicado_de: str | None = None
    grupo: str = ""
    orden: int = 0
    retirado: bool = False
    embeber: bool = True
    motivo_lexico: str | None = None
    avisos: tuple[str, ...] = ()
    identidad: str | None = None       # id propio (H-xxx/I-xxx) para coincidencia exacta
    datos: dict = field(default_factory=dict)

    def entrada(self) -> str:
        """Texto exacto que recibe el modelo; su SHA-256 es la clave del vector."""
        titulo = re.sub(r"\s+", " ", self.titulo or "none")[:LIMITE_TITULO]
        return f"title: {titulo} | text: {self.contenido}"


def sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def huella_elementos(filas) -> str:
    """Identidad de los elementos de la biblioteca de un fragmento: (id, documento_id, texto) en orden."""
    return sha("\x1f".join(f"{i}\x1e{doc}\x1e{texto or ''}" for i, doc, texto in filas))


def util(texto: str) -> bool:
    """Texto con letras suficientes para un embedding; el resto queda solo en busqueda literal."""
    t = texto.strip()
    letras = sum(c.isalpha() for c in t)
    return letras >= 20 and letras >= 0.3 * len(t)


def trocear(texto: str, limite: int = LIMITE) -> list[str]:
    """Parte por lineas y, si hace falta, por frases; nunca devuelve trozos mayores que el limite."""
    trozos, actual = [], ""
    for linea in texto.split("\n"):
        piezas = [linea]
        if len(linea) > limite:
            piezas = [p for p in re.split(r"(?<=[.;:!?])\s+", linea) if p]
            piezas = [p[i:i + limite] for p in piezas for i in range(0, len(p), limite)]
        for p in piezas:
            if actual and len(actual) + 1 + len(p) > limite:
                trozos.append(actual)
                actual = ""
            actual = f"{actual}\n{p}" if actual else p
    if actual.strip():
        trozos.append(actual)
    return [t.strip() for t in trozos if t.strip()]


# --- Markdown ---------------------------------------------------------------------------------

def slug(titulo: str) -> str:
    t = re.sub(r"[^\w\- ]", "", titulo.strip().lower())
    return t.replace(" ", "-")


def retirar(texto: str) -> tuple[str, bool]:
    """Los tachados conservan su condicion de texto retirado."""
    nuevo = re.sub(r"~~(.+?)~~", r"[RETIRADO: \1]", texto)
    return nuevo, nuevo != texto


def secciones(texto: str):
    """(ruta de encabezados, ancla, [(n_linea, linea)]) sin confundir # dentro de bloques de codigo."""
    pila: list[tuple[int, str]] = []
    vistos: dict[str, int] = {}
    ancla, actual, en_codigo = "", [], False
    for n, linea in enumerate(texto.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", linea):
            en_codigo = not en_codigo
        m = None if en_codigo else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", linea)
        if m:
            yield [t for _, t in pila], ancla, actual
            nivel, titulo = len(m.group(1)), m.group(2).strip()
            pila = [(lv, t) for lv, t in pila if lv < nivel] + [(nivel, titulo)]
            base = slug(titulo)
            ancla = base if base not in vistos else f"{base}-{vistos[base]}"
            vistos[base] = vistos.get(base, 0) + 1
            actual = []
        else:
            actual.append((n, linea))
    yield [t for _, t in pila], ancla, actual


def bloques(lineas: list[tuple[int, str]]):
    """Parrafos, tablas y bloques de codigo, cada uno con su rango de lineas."""
    actual, tipo, en_codigo = [], None, False
    for n, linea in lineas:
        valla = bool(re.match(r"^\s*(```|~~~)", linea))
        if en_codigo or valla:
            if not en_codigo and actual:
                yield tipo, actual
                actual = []
            actual.append((n, linea))
            tipo = "codigo"
            en_codigo = en_codigo != valla
            if not en_codigo:
                yield tipo, actual
                actual, tipo = [], None
            continue
        if not linea.strip():
            if actual:
                yield tipo, actual
            actual, tipo = [], None
            continue
        t = "tabla" if linea.lstrip().startswith("|") else "texto"
        if actual and t != tipo:
            yield tipo, actual
            actual = []
        tipo = t
        actual.append((n, linea))
    if actual:
        yield tipo, actual


def piezas_bloque(tipo: str, lineas: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    """Divide un bloque largo; las tablas repiten su cabecera en cada parte."""
    texto = "\n".join(l for _, l in lineas)
    if len(texto) <= LIMITE:
        return [(lineas[0][0], lineas[-1][0], texto)]
    if tipo == "tabla" and len(lineas) > 2 and re.match(r"^\s*\|[\s:|-]+\|\s*$", lineas[1][1]):
        cabecera = lineas[0][1] + "\n" + lineas[1][1]
        partes, actual = [], []
        for n, l in lineas[2:]:
            if actual and len(cabecera) + sum(len(x) + 1 for _, x in actual) + len(l) + 1 > LIMITE:
                partes.append(actual)
                actual = []
            actual.append((n, l))
        partes.append(actual)
        salida = []
        for p in partes:
            if not p:
                continue
            texto_parte = "\n".join(x for _, x in p)
            # Una fila mayor que el limite se parte, y cada trozo conserva la cabecera.
            for t in (trocear(texto_parte, LIMITE - len(cabecera) - 1) if len(texto_parte) + len(cabecera) > LIMITE else [texto_parte]):
                salida.append((p[0][0], p[-1][0], cabecera + "\n" + t))
        return salida
    return [(lineas[0][0], lineas[-1][0], t) for t in trocear(texto)]


def markdown(ruta: str, texto: str, coleccion: str, base: dict) -> list[Fragmento]:
    titulo_doc = next((m.group(1).strip() for m in re.finditer(r"^#\s+(.+)$", texto, re.M)), PurePosixPath(ruta).stem)
    fragmentos = []
    for camino, ancla, lineas in secciones(texto):
        piezas = [p for tipo, b in bloques(lineas) for p in piezas_bloque(tipo, b)]
        grupos, actual = [], []
        for p in piezas:
            if actual and sum(len(x[2]) + 2 for x in actual) + len(p[2]) > LIMITE:
                grupos.append(actual)
                actual = []
            actual.append(p)
        if actual:
            grupos.append(actual)
        for i, g in enumerate(grupos):
            contenido, retirado = retirar("\n\n".join(x[2] for x in g))
            if not contenido.strip():
                continue
            seccion = " > ".join(camino[1:] if camino and camino[0] == titulo_doc else camino) or None
            a, b = g[0][0], g[-1][1]
            fragmentos.append(Fragmento(
                clave=f"md:{ruta}#{ancla}:{i}" if ancla else f"md:{ruta}:{i}",
                coleccion=coleccion, tipo_fuente="markdown", contenido=contenido,
                titulo=titulo_doc + (f" — {seccion}" if seccion else ""), ruta=ruta, seccion=seccion,
                localizador=f"{ruta}{'#' + ancla if ancla else ''} (lineas {a}-{b})",
                retirado=retirado, grupo=f"md:{ruta}", orden=a, **base,
            ))
    return fragmentos


def features_biblioteca(con: sqlite3.Connection | None) -> dict[str, str]:
    if con is None:
        return {}
    return {m.group(1): f for (f,) in con.execute("SELECT DISTINCT feature FROM documento WHERE feature IS NOT NULL")
            if (m := re.match(r"(\d+)-", f))}


def estados_docs(readme: str) -> tuple[dict[str, str], set[str]]:
    """Estado de cada documento de docs/ segun su indice, y los marcados como historial."""
    estados, historial, en_historial = {}, set(), False
    for linea in readme.splitlines():
        if linea.startswith("## "):
            en_historial = "historial" in linea.lower()
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")] if linea.startswith("|") else []
        if len(celdas) >= 3:
            for enlace in re.findall(r"\]\(([\w./-]+\.md)", celdas[1]):
                estados[f"docs/{enlace}"] = celdas[2]
        if en_historial:
            historial.update(f"docs/{e}" for e in re.findall(r"\]\(([\w./-]+\.md)", linea))
    return estados, historial


def ficheros_markdown(raiz: Path) -> list[tuple[Path, str]]:
    """Markdown de conocimiento/ y docs/; nunca datos/, .venv/, codigo ni la referencia del propio RAG.

    conocimiento/rag/ (investigacion, glosario y preguntas de evaluacion) tampoco: no describe Exemples y,
    si se indexara, las preguntas de evaluacion se encontrarian a si mismas."""
    salida = []
    for carpeta in ("conocimiento", "docs"):
        for path in sorted((raiz / carpeta).rglob("*.md")):
            partes = path.relative_to(raiz).parts
            if path.relative_to(raiz).as_posix() == "conocimiento/rag.md" or partes[:2] == ("conocimiento", "rag"):
                continue
            if not any(p in (".venv", "datos", "herramientas", "__pycache__", "node_modules") for p in partes):
                salida.append((path, carpeta))
    return salida


def fuentes_markdown(raiz: Path, features: dict[str, str]) -> list[Fragmento]:
    fragmentos = []
    readme_docs = raiz / "docs" / "README.md"
    estados, historial_docs = estados_docs(readme_docs.read_text(encoding="utf-8")) if readme_docs.exists() else ({}, set())
    for path, coleccion in ficheros_markdown(raiz):
        rel = path.relative_to(raiz).as_posix()
        if rel in VIGENCIA:
            vigencia, motivo = VIGENCIA[rel]
            clasificacion = f"explicita: {motivo}"
        elif coleccion == "docs" and rel in historial_docs:
            vigencia, clasificacion = "historial", "docs/README.md: seccion Historial"
        elif FECHADO.search(path.name):
            vigencia, clasificacion = "revision_fechada", "regla: nombre fechado sin clasificacion explicita"
        else:
            vigencia = "vigente"
            clasificacion = ("por defecto: ficha tematica (conocimiento/README.md)" if coleccion == "conocimiento"
                             else "por defecto: documento de docs/")
        partes = PurePosixPath(rel).parts
        feature = codigo = None
        if coleccion == "conocimiento" and len(partes) > 2 and (m := re.match(r"(\d+)-", partes[1])):
            feature = features.get(m.group(1))
            for p in partes[2:]:
                if re.fullmatch(r"\d{4}", PurePosixPath(p).stem):
                    codigo = PurePosixPath(p).stem
                    break
        base = {"vigencia": vigencia, "clasificacion": clasificacion, "feature": feature,
                "codigos": (codigo,) if codigo else (),
                "naturaleza": "interpretacion" if coleccion == "conocimiento" else "aplicacion",
                "estado_doc": estados.get(rel) if coleccion == "docs" else None}
        if coleccion == "conocimiento" and vigencia == "historial":
            fragmentos += [replace(f, coleccion="historial") for f in markdown(rel, path.read_text(encoding="utf-8"), coleccion, base)]
        else:
            fragmentos += markdown(rel, path.read_text(encoding="utf-8"), coleccion, base)
    return fragmentos


def fuentes_hallazgos(path: Path) -> tuple[list[Fragmento], list[str]]:
    fragmentos, errores = [], []
    if not path.exists():
        return fragmentos, [f"no existe {path.name}"]
    for n, linea in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            r = json.loads(linea)
        except json.JSONDecodeError as error:
            errores.append(f"{path.name}:{n}: {error}")
            continue
        piezas = tuple(p.strip() for p in str(r.get("pieza") or "").split(",") if p.strip())
        evidencia = r.get("evidencia") or []
        lineas = [f"{r['id']} · {r.get('tipo')} · estado {r.get('estado')} · relevancia {r.get('relevancia')}",
                  f"Feature: {r.get('feature')} · pieza: {r.get('pieza') or '—'} · fecha {r.get('fecha')}"
                  + (f" · revisado {r['fecha_revision']}" if r.get("fecha_revision") else ""),
                  str(r.get("afirmacion", ""))]
        lineas += [f"Evidencia: {e.get('ruta')} · {e.get('localizador')}" for e in evidencia]
        if r.get("comprobacion"):
            lineas.append(f"Comprobacion SQL registrada: rag.py exacto hallazgo {r['id']} --comprobar")
        contenido = "\n".join(lineas)
        for i, trozo in enumerate(trocear(contenido) if len(contenido) > LIMITE else [contenido]):
            fragmentos.append(Fragmento(
                clave=f"hallazgo:{r['id']}" + (f"#{i}" if i else ""), coleccion="hallazgos", tipo_fuente="hallazgo",
                contenido=trozo, titulo=f"{r['id']} {r.get('tipo')}", ruta="conocimiento/hallazgos.jsonl",
                localizador=f"conocimiento/hallazgos.jsonl:{n} ({r['id']})", vigencia="vigente",
                clasificacion="registro estructurado vigente; el ciclo de vida va en estado_hallazgo",
                naturaleza="hallazgo", estado_hallazgo=r.get("estado"),
                feature=r.get("feature") or None, codigos=piezas,   # '*' = transversal: entra en cualquier filtro de feature
                grupo=f"hallazgo:{r['id']}", orden=n * 10 + i, identidad=r["id"],
                datos={"evidencia": evidencia, "comprobacion": r.get("comprobacion"), "feature_original": r.get("feature")},
            ))
    return fragmentos, errores


# --- Biblioteca -------------------------------------------------------------------------------

def _doc_base(d: dict) -> dict:
    return {"ruta": d["ruta"], "raiz": "exemples", "documento_id": d["id"], "feature": d["feature"],
            "pieza": d["pieza"], "codigos": (d["codigo"],) if d["codigo"] else (), "carpeta": d["carpeta_norm"],
            "sha256_original": d["sha256"], "grupo": f"doc:{d['id']}"}


def _estructura(con, doc_id: int) -> dict:
    salida = {}
    for clave, valor in con.execute("SELECT clave, valor FROM estructura WHERE documento_id=?", (doc_id,)):
        try:
            salida[clave] = json.loads(valor)
        except (TypeError, json.JSONDecodeError):
            salida[clave] = valor
    return salida


def _corto(valor, ancho: int = 300) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _texto_biblioteca(con, docs: dict[int, dict], consumidos: set[int]) -> list[Fragmento]:
    """Paginas, diapositivas, parrafos y tablas de Word, cabeceras de correo... con su localizador."""
    fragmentos: list[Fragmento] = []
    marcadores = ",".join("?" * len(TIPOS_TEXTO))
    filas = con.execute(f"SELECT id, documento_id, tipo, localizador, orden, texto FROM elemento "
                        f"WHERE tipo IN ({marcadores}) ORDER BY documento_id, orden", TIPOS_TEXTO)
    buffer: list[tuple] = []
    cabeceras: dict[tuple[int, str], str] = {}   # primera fila de cada tabla de Word

    def emitir(grupo: list[tuple]) -> None:
        if not grupo:
            return
        d = docs[grupo[0][1]]
        tipo = grupo[0][2]
        cab = ""
        if tipo == "tabla":
            cab = cabeceras.get((grupo[0][1], _num_tabla(grupo[0][3])), "")
            texto = "\n".join(r[5] or "" for r in grupo)
            if cab and not grupo[0][3].endswith(" fila 1"):
                texto = cab + "\n" + texto
            locs = [r[3] for r in grupo]
            loc = locs[0] if len(locs) == 1 else f"{locs[0]} … {locs[-1].split(' ', 2)[-1]}"
        else:
            texto = "\n".join(r[5] or "" for r in grupo)
            loc = grupo[0][3] if len(grupo) == 1 else f"{grupo[0][3]} … {grupo[-1][3]}"
        clave = f"bib:e{grupo[0][0]}" + (f"-e{grupo[-1][0]}" if len(grupo) > 1 else "")
        # `ver` compara esta identidad antes de leer vecinos de la biblioteca actual (ids reutilizados).
        origen = {"elementos": [r[0] for r in grupo], "documento_elementos": d["id"], "sha256_documento": d["sha256"],
                  "huella_elementos": huella_elementos((r[0], r[1], r[5]) for r in grupo)}
        partes = trocear(texto) if len(texto) > LIMITE else [texto.strip()]
        if tipo == "tabla" and len(partes) > 1 and cab:
            partes = [partes[0]] + [cab + "\n" + p for p in partes[1:]]
        for i, parte in enumerate(partes):
            if not parte.strip():
                continue
            embeber = util(parte)
            fragmentos.append(Fragmento(
                clave=clave + (f"#p{i + 1}" if len(partes) > 1 else ""), coleccion="biblioteca",
                tipo_fuente=f"elemento:{tipo}", contenido=parte,
                localizador=loc + (f" (parte {i + 1}/{len(partes)})" if len(partes) > 1 else ""),
                naturaleza="extraido", orden=grupo[0][4] * 100 + i, embeber=embeber,
                motivo_lexico=None if embeber else "poco texto con letras (cifras o simbolos)",
                datos=dict(origen), **_doc_base(d)))

    for fila in filas:
        doc_id, tipo = fila[1], fila[2]
        if doc_id not in docs or (doc_id in consumidos and tipo in ("cabecera", "resumen", "productos")):
            continue
        if tipo == "tabla" and fila[3].endswith(" fila 1"):
            cabeceras[(doc_id, _num_tabla(fila[3]))] = fila[5] or ""
        if buffer and (buffer[-1][1] != doc_id or buffer[-1][2] != tipo or tipo not in ("parrafo", "tabla")
                       or (tipo == "tabla" and _num_tabla(buffer[-1][3]) != _num_tabla(fila[3]))
                       or sum(len(r[5] or "") + 1 for r in buffer) + len(fila[5] or "") > LIMITE):
            emitir(buffer)
            buffer = []
        buffer.append(fila)
    emitir(buffer)
    return fragmentos


def _num_tabla(localizador: str) -> str:
    m = re.match(r"tabla (\d+)", localizador)
    return m.group(1) if m else localizador


def _formulas(est: dict, ext: str) -> str:
    valor = est.get("formulas")
    if ext == "csv":
        return "no aplica (CSV)"
    if isinstance(valor, int):
        return f"conservadas ({valor} con texto de formula, openpyxl)"
    if valor == "via Excel COM":
        return "conservadas (Excel por COM)"
    if valor:
        return f"no disponibles: {valor}; solo las RAND de celda_aleatoria"
    return "desconocido"


def _tablas(con, docs: dict[int, dict]) -> list[Fragmento]:
    """Una tarjeta por libro/CSV y otra por hoja con lectura DR o perfil PPAP. Sin valores de celdas."""
    fragmentos = []
    perfiles = {(r[0], r[1]): r for r in con.execute(
        "SELECT documento_id, hoja, fila_cabecera, metadatos, cavidades, filas_cota, items, equipos, nok, ceros, vacias FROM perfil_ppap")}
    lecturas = {(r[0], r[1]): r for r in con.execute(
        "SELECT documento_id, hoja, plantilla, papel, fila_cabecera, cavidades, filas_cota, valores, cualitativos, "
        "rechazadas, aleatorias, ceros, atipicos FROM lectura_dr")}
    por_doc: dict[int, list[str]] = {}
    for doc_id, hoja in sorted(set(perfiles) | set(lecturas)):
        por_doc.setdefault(doc_id, []).append(hoja)
    for d in docs.values():
        if d["ext"] not in HOJAS or d["estado"] != "extraido" or d["lector"] == "pdf":
            continue
        est = _estructura(con, d["id"])
        base = _doc_base(d)
        niveles, ilegibles = {}, {}
        for hoja in por_doc.get(d["id"], []):
            p = perfiles.get((d["id"], hoja))
            meta = json.loads(p[3]) if p and p[3] else {}
            if meta.get("drawing_level"):
                nivel = str(meta["drawing_level"])
                # Una referencia rota de Excel (#REF!) no es un nivel de plano: la revision queda desconocida.
                (ilegibles if ERROR_EXCEL.search(nivel) else niveles)[hoja] = nivel
        revision = next(iter(niveles.values())) if len(set(niveles.values())) == 1 and not ilegibles else None
        rev_origen = "nivel de plano (drawing_level) en la cabecera PPAP, perfil_ppap" if revision else None
        aviso_nivel = (f"drawing_level con error de Excel ({'; '.join(f'{h}={v}' for h, v in ilegibles.items())}): "
                       "revision desconocida",) if ilegibles else ()
        if d["ext"] == "csv":
            detalle = "; ".join(f"{k}={_corto(v, 400)}" for k, v in est.items() if k not in ("propiedades",))
            contenido = f"CSV «{d['nombre']}». {detalle}"
        else:
            hojas = est.get("hojas") or []
            lista = "; ".join(f"{h.get('nombre')} ({h.get('filas')}x{h.get('columnas')}, {h.get('celdas')} celdas)" for h in hojas)
            contenido = (f"Libro «{d['nombre']}» (.{d['ext']}, leido como {d['lector']}). Formulas: {_formulas(est, d['ext'])}. "
                         f"{len(hojas)} hojas: {lista}")
            if niveles:
                contenido += "\nNivel de plano declarado por hoja (perfil PPAP): " + "; ".join(f"{h}={v}" for h, v in niveles.items())
            if ilegibles:
                contenido += "\nNivel de plano ilegible (error de Excel) en: " + "; ".join(f"{h}={v}" for h, v in ilegibles.items())
        for i, parte in enumerate(trocear(contenido)):
            fragmentos.append(Fragmento(
                clave=f"libro:{d['id']}" + (f"#p{i + 1}" if i else ""), coleccion="tablas", tipo_fuente="libro",
                contenido=parte, localizador=f"{d['nombre']} (estructura)", naturaleza="derivado",
                revision=revision, revision_origen=rev_origen, orden=-1000 + i,
                avisos=("Tarjeta de contexto: los valores se consultan con rag.py exacto celdas/medidas",) + aviso_nivel,
                datos={"exacto": f"rag.py exacto celdas {d['id']}"}, **base))
        for hoja in por_doc.get(d["id"], []):
            p, l = perfiles.get((d["id"], hoja)), lecturas.get((d["id"], hoja))
            fila_cab = (l[4] if l else None) or (p[2] if p else None)
            cabecera = ""
            if fila_cab:
                celdas = con.execute("SELECT col, valor FROM celda WHERE documento_id=? AND hoja=? AND fila=? ORDER BY col",
                                     (d["id"], hoja, fila_cab)).fetchall()
                cabecera = " | ".join(str(v) for _, v in celdas if v not in (None, ""))[:500]
            lineas = [f"Hoja «{hoja}» del libro «{d['nombre']}».",
                      f"Cabecera (fila {fila_cab}): {cabecera}" if fila_cab else "Sin fila de cabecera detectada."]
            if l:
                lineas.append(
                    f"Lectura heuristica lector_dr: plantilla {l[2]}; papel {l[3]}; cavidades {', '.join(json.loads(l[5] or '[]'))}; "
                    f"{l[6]} filas de cota; {l[7]} valores numericos leidos; {l[8]} no numericos o sin nominal omitidos; "
                    f"aleatorias {l[10]}; ceros {l[11]}; atipicos {l[12]}; ajustes y rechazos {l[9]}.")
                if not l[7]:
                    # p. ej. las dos copias de PPAP-3167-00_Inf_03.xlsm en PPAP-3167-00_2/: cotas con nominal, sin valores
                    lineas.append("Sin valores de medida: plantilla sin rellenar o solo cabecera"
                                  + (f" (con {l[8]} valores no numericos)." if l[8] else "."))
            if p:
                meta = json.loads(p[3]) if p[3] else {}
                lineas.append(
                    f"Perfil PPAP: {p[5]} filas de cota; cavidades {', '.join(json.loads(p[4] or '[]'))}; equipos {_corto(p[7], 200)}; "
                    f"NOK {p[8]}; ceros {p[9]}; vacias {p[10]}; metadatos {_corto(meta, 400)}.")
            nivel = niveles.get(hoja)
            fragmentos.append(Fragmento(
                clave=f"hoja:{d['id']}:{hoja}", coleccion="tablas", tipo_fuente="hoja", contenido="\n".join(lineas)[:LIMITE],
                localizador=f"{hoja}!{fila_cab}" if fila_cab else hoja, seccion=hoja, naturaleza="derivado",
                revision=nivel, revision_origen="drawing_level de la cabecera PPAP (perfil_ppap)" if nivel else None,
                orden=-500, avisos=("Recuentos del prototipo heuristico (lector_dr/perfil_ppap), no inventario de celdas",
                                    "Los valores se consultan con rag.py exacto medidas/celdas")
                + ((f"drawing_level con error de Excel ({ilegibles[hoja]}): revision desconocida",) if hoja in ilegibles else ()),
                datos={"hoja": hoja, "exacto": f"rag.py exacto medidas --documento {d['id']} --hoja \"{hoja}\""}, **base))
    return fragmentos


def _cad(con, docs: dict[int, dict]) -> tuple[list[Fragmento], set[int]]:
    fragmentos, consumidos = [], set()
    textos, cuantos = {}, {}   # un documento puede tener varios elementos del mismo tipo (13 IGS/STEP con varias cabeceras)
    for doc_id, tipo, texto in con.execute(
            "SELECT e.documento_id, e.tipo, e.texto FROM elemento e JOIN documento d ON d.id=e.documento_id "
            "WHERE e.tipo IN ('cabecera','productos','resumen') AND d.ext IN ('stp','step','stl','igs','iges','txt') "
            "ORDER BY e.documento_id, e.orden"):
        previo = textos.setdefault(doc_id, {}).get(tipo)
        textos[doc_id][tipo] = (texto or "") if previo is None else f"{previo}\n{texto or ''}"
        conteo = cuantos.setdefault(doc_id, {})
        conteo[tipo] = conteo.get(tipo, 0) + 1
    for d in docs.values():
        if d["estado"] == "duplicado" or not (d["ext"] in CAD or d["ext"] == "txt"):
            continue
        est = _estructura(con, d["id"])
        if d["ext"] == "txt" and est.get("tipo") != "nube_de_puntos":
            continue
        t = textos.get(d["id"], {})
        formato = ("step" if d["ext"] in ("stp", "step") else "igs" if d["ext"] in ("igs", "iges")
                   else "catia" if d["ext"] in CATIA else "nube" if d["ext"] == "txt" else d["ext"])
        lineas = [f"Fichero CAD/3D «{d['nombre']}» (.{d['ext']}), carpeta {d['carpeta_norm']}, {d['tamano'] / 1e6:.1f} MB, estado {d['estado']}."]
        if t.get("productos"):
            lineas.append("Productos: " + _corto(t["productos"].replace("\n", " / "), ANCHO_CAD["productos"]))
        if t.get("cabecera"):
            lineas.append("Cabecera: " + _corto(t["cabecera"].replace("\n", " / "), ANCHO_CAD["cabecera"]))
        if formato == "step":
            lineas.append(f"Esquema {est.get('esquema')}; unidades {est.get('unidades')}; sistema de origen {_corto(est.get('sistema_origen'), 120)}.")
            lineas.append(f"Entidades: {est.get('entidades_total')} ({_corto(est.get('entidades'), 250)}). Caja: {_corto(est.get('caja'), 250)}.")
        elif formato == "stl":
            lineas.append(f"Formato {est.get('formato')}; {est.get('triangulos')} triangulos; caja {_corto(est.get('caja'))}; dimensiones {est.get('dimensiones')}.")
        elif formato == "dxf":
            lineas.append(f"DXF {est.get('version')}; unidades {est.get('unidades')}; entidades {_corto(est.get('entidades'), 200)}; "
                          f"vertices {est.get('vertices')}; caja {est.get('caja')}; capas {_corto(est.get('capas'), 200)}.")
        elif formato == "igs":
            lineas.append(f"Entidades: {est.get('entidades')} por tipo IGES {_corto(est.get('entidades_por_tipo'), 250)}.")
        elif formato == "catia":
            lineas.append(f"Version CATIA {_corto(est.get('version_catia'), 80)}; firma {_corto(est.get('firma_texto'), 80)}.")
        else:
            lineas.append(f"Nube de puntos: {est.get('puntos')} puntos; columnas {est.get('columnas')}; minimos {est.get('minimos')}; maximos {est.get('maximos')}.")
            if t.get("resumen"):
                lineas.append(_corto(t["resumen"], 300))
        lineas.append("Alcance: " + ALCANCE_CAD[formato])
        consumidos.add(d["id"])
        # La tarjeta resume; lo que recorta (listados PRODUCT, cabeceras largas) va completo en fragmentos propios.
        partes = {tipo: trocear(t[tipo]) for tipo, ancho in ANCHO_CAD.items()
                  if len(t.get(tipo, "").replace("\n", " / ")) > ancho}
        fragmentos.append(Fragmento(
            clave=f"cad:{d['id']}", coleccion="cad", tipo_fuente=f"cad:{formato}", contenido="\n".join(lineas)[:LIMITE],
            localizador=f"{d['nombre']} (estructura)", naturaleza="derivado", orden=-2000,
            avisos=("Metadatos y geometria parcial calculados por lectores.py; no es una medicion de la pieza",
                    "Consultas geometricas completas o calculos nuevos requieren abrir el original")
            + tuple(f"{tipo.capitalize()} recortado en la tarjeta: completo en cad:{d['id']}#{tipo}1…{len(p)}"
                    for tipo, p in partes.items()),
            datos={"formato": formato, "metodo": ALCANCE_CAD[formato], "elementos_incluidos": cuantos.get(d["id"], {})},
            **_doc_base(d)))
        for n, (tipo, trozos) in enumerate(partes.items()):
            for i, trozo in enumerate(trozos, 1):
                embeber = util(trozo)
                fragmentos.append(Fragmento(
                    clave=f"cad:{d['id']}#{tipo}{i}", coleccion="cad", tipo_fuente=f"cad:{tipo}", contenido=trozo,
                    titulo=f"{tipo.capitalize()} de {d['nombre']}", localizador=f"{d['nombre']} ({tipo}, parte {i}/{len(trozos)})",
                    naturaleza="extraido", orden=-1999 + n * 1000 + i, embeber=embeber,
                    motivo_lexico=None if embeber else "poco texto con letras (cifras o simbolos)",
                    avisos=(f"Texto {tipo} del fichero tal como lo extrajo lectores.py",),
                    datos={"formato": formato, "elemento": tipo, "parte": i, "partes": len(trozos)}, **_doc_base(d)))
    return fragmentos, consumidos


def _inventario(con, docs: dict[int, dict], representados: set[int]) -> list[Fragmento]:
    delegados = {doc_id: tipos for doc_id, tipos in con.execute(
        "SELECT documento_id, group_concat(DISTINCT tipo) FROM elemento WHERE tipo IN ('fila','lineas','cadenas') GROUP BY documento_id")}
    fragmentos = []
    for d in docs.values():
        if d["id"] in representados or d["estado"] == "eliminado":
            continue
        est = _estructura(con, d["id"])
        visual = {k: est[k] for k in ("formato", "ancho", "alto", "duracion_s", "fps", "paginas") if k in est}
        original = docs.get(d["duplicado_de"]) if d["duplicado_de"] else None
        if d["estado"] in NO_VIGENTES:
            motivo = NO_VIGENTES[d["estado"]] + (f" ({d['mensaje']})" if d["mensaje"] else "")
        elif d["estado"] == "duplicado" and (original is None or original["estado"] not in VIGENTES):
            motivo = ("duplicado cuyo original " + (f"Exemples/{original['ruta']} esta en estado {original['estado']}"
                                                    if original else "ya no esta en la biblioteca")
                      + ": no se usa la extraccion anterior")
        elif d["id"] in delegados:
            motivo = f"contenido solo en busqueda literal de la biblioteca ({delegados[d['id']]})"
        elif d["estado"] == "duplicado":
            motivo = f"duplicado sin contenido propio de Exemples/{original['ruta']}"
        else:
            motivo = f"sin texto interpretado (estado {d['estado']}{': ' + d['mensaje'] if d['mensaje'] else ''})"
        contenido = (f"Documento «{d['nombre']}» (.{d['ext']}, {d['tamano'] / 1e6:.2f} MB, estado {d['estado']}, "
                     f"lector {d['lector'] or '—'}{', en la nube al inventariar' if d['en_nube'] else ''}). {motivo}. "
                     + (f"Metadatos: {_corto(visual, 200)}. " if visual else "")
                     + f"Ruta: Exemples/{d['ruta']}")
        fragmentos.append(Fragmento(
            clave=f"doc:{d['id']}", coleccion="inventario", tipo_fuente=f"inventario:{d['ext'] or 'sin_ext'}",
            contenido=contenido, localizador=d["nombre"], naturaleza="inventario", embeber=False,
            motivo_lexico="solo inventario: " + motivo, orden=-3000,
            avisos=("Sin contenido interpretado: abrir el original para consultarlo",), **_doc_base(d)))
    return fragmentos


def fuentes_biblioteca(con: sqlite3.Connection) -> list[Fragmento]:
    columnas = ("id", "ruta", "feature", "pieza", "codigo", "carpeta_norm", "nombre", "ext", "tamano", "en_nube",
                "sha256", "estado", "lector", "mensaje", "duplicado_de")
    docs = {r[0]: dict(zip(columnas, r)) for r in con.execute(f"SELECT {', '.join(columnas)} FROM documento ORDER BY id")}
    vigentes = {i: d for i, d in docs.items() if d["estado"] in VIGENTES}
    cad, consumidos = _cad(con, vigentes)
    fragmentos = cad + _tablas(con, vigentes) + _texto_biblioteca(con, vigentes, consumidos)
    # Los duplicados no tienen elementos propios: heredan el contenido del original vigente con su procedencia.
    por_doc: dict[int, list[Fragmento]] = {}
    for f in fragmentos:
        por_doc.setdefault(f.documento_id, []).append(f)
    for d in docs.values():
        original = vigentes.get(d["duplicado_de"]) if d["duplicado_de"] else None
        if d["estado"] != "duplicado" or not original:
            continue
        for f in por_doc.get(original["id"], []):
            fragmentos.append(replace(
                f, clave=f"{f.clave}@d{d['id']}", duplicado_de=original["ruta"],
                avisos=f.avisos + (f"Contenido leido del original identico Exemples/{original['ruta']}",), **_doc_base(d)))
    representados = {f.documento_id for f in fragmentos}
    return fragmentos + _inventario(con, docs, representados)


# --- Identificadores ----------------------------------------------------------------------------

def menciones(texto: str, codigos: set[str], consulta: bool = False) -> set[tuple[str, str]]:
    """Identificadores normalizados. Una mencion no asigna pieza, revision ni cavidad al fragmento."""
    salida = set()
    flags = re.I if consulta else 0
    for m in re.finditer(r"(?<![\w.])N\s?(\d{1,4}(?:\.\d{1,3})*)(?![\w])", texto, flags):
        salida.add(("cota", f"N{m.group(1)}"))
    for m in re.finditer(r"\b([HI])-(\d{3})\b", texto, re.I if consulta else 0):
        salida.add(("hallazgo", f"{m.group(1).upper()}-{m.group(2)}"))
    for m in re.finditer(r"(?<![A-Za-z])intern\.?\s?(\d{1,2})(?!\d)", texto, re.I):   # tambien «3212-00_intern.06.xls»
        salida.add(("muestreo", f"intern.{int(m.group(1)):02d}"))
    for m in re.finditer(r"\bDR\s?\(([^()\n]{1,40})\)", texto, re.I if consulta else 0):
        salida.add(("hoja", f"DR({m.group(1).strip().upper()})"))
    for m in re.finditer(r"(?<!\d)(\d{4})(?!\d)", texto):
        if m.group(1) in codigos:
            salida.add(("pieza", m.group(1)))
    return salida
