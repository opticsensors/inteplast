"""Grafo del conocimiento: Markdown, features, piezas, hallazgos (I-xxx), preguntas (A-xx) y casos.

Nodos y aristas salen solo del texto que ya existe: enlaces Markdown entre ficheros y menciones
explícitas de pieza (código de 4 cifras de las 21 piezas), hallazgo (I-001), pregunta (A10) o caso
(CR-001). Los campos `pieza` y `feature` de hallazgos.jsonl y casos-referencia.jsonl dan el resto.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import datos
from datos import CONOCIMIENTO, REPO

ENLACE = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
HALLAZGO = re.compile(r"(?<![\w-])(I-\d{3})(?!\d)")
CASO = re.compile(r"(?<![\w-])(CR-\d{3})(?!\d)")
# A1…A23 solo como pregunta: no tras «hoja», «formato», «DIN»… (A3/A4 suelen ser tamaños de papel).
PREGUNTA = re.compile(r"(?<![\w/-])A(\d{1,2})(?![\w-])")
PAPEL = re.compile(r"(?i)(hoja|formato|papel|din|página|pagina|tamaño|plano|iso)\s*$")
TITULO_PREGUNTA = re.compile(r"^###\s+A(\d{1,2})\s*·\s*(.+)$")


def tipo_md(rel: str) -> str:
    partes = rel.split("/")
    if partes[0] == "docs":
        return "docs"
    if partes[0] != "conocimiento":
        return "raiz"
    if len(partes) >= 3 and re.match(r"\d-", partes[1]):
        if partes[2] == "README.md" and len(partes) == 3:
            return "ficha-feature"
        return "ficha-pieza"
    if len(partes) >= 3 and partes[1] in ("ingesta", "rag"):
        return partes[1]
    return "conocimiento"


def ficheros_md() -> list[Path]:
    salida = [p for p in CONOCIMIENTO.rglob("*.md") if "datos" not in p.relative_to(CONOCIMIENTO).parts
              and ".venv" not in p.parts and "__pycache__" not in p.parts]
    salida += sorted((REPO / "docs").glob("*.md"))
    salida += [REPO / n for n in ("CLAUDE.md", "README.md", "TODO.md") if (REPO / n).is_file()]
    return sorted(salida)


def numero_feature(texto: str) -> str | None:
    m = re.match(r"\s*(\d)\s*-", texto or "")
    return m.group(1) if m else None


@lru_cache(maxsize=1)
def construir() -> dict:
    nodos: dict[str, dict] = {}
    aristas: Counter = Counter()

    def nodo(id_, tipo, etiqueta, **extra):
        if id_ not in nodos:
            nodos[id_] = {"id": id_, "tipo": tipo, "etiqueta": etiqueta, **extra}
        return nodos[id_]

    def arista(a, b, tipo, peso=1):
        if a != b and a in nodos and b in nodos:
            aristas[(a, b, tipo)] += peso

    # features (carpetas de conocimiento) y piezas (biblioteca)
    carpetas_feature = {p.name[0]: p for p in CONOCIMIENTO.iterdir() if p.is_dir() and re.match(r"\d-", p.name)}
    for num, carpeta in sorted(carpetas_feature.items()):
        nodo(f"feature:{num}", "feature", carpeta.name, ruta=f"conocimiento/{carpeta.name}/README.md")
    codigos = set()
    for p in datos.piezas():
        codigos.add(p["codigo"])
        nodo(f"pieza:{p['codigo']}", "pieza", p["codigo"], documentos=p["documentos"],
             etiquetas=[f.split("- ", 1)[-1] for f in p["features"]])
        for f in p["features"]:
            n = numero_feature(f)
            if n:
                arista(f"pieza:{p['codigo']}", f"feature:{n}", "feature")
    pieza_re = re.compile(r"(?<![\d.,])(" + "|".join(sorted(codigos)) + r")(?![\d.,]\d)")

    # hallazgos
    for h in datos.hallazgos():
        hid = h["id"]
        nodo(hid, "hallazgo", hid, estado=h.get("estado"), relevancia=h.get("relevancia"), subtipo=h.get("tipo"),
             resumen=(h.get("afirmacion") or "")[:240])
        for cod in datos.piezas_de(h.get("pieza")):
            arista(hid, f"pieza:{cod}", "pieza")
        n = numero_feature(h.get("feature"))
        if n:
            arista(hid, f"feature:{n}", "feature")

    # preguntas abiertas
    preguntas = REPO / "docs" / "preguntas-abiertas.md"
    secciones: dict[str, list[str]] = {}
    estado = "abierta"
    actual = None
    for linea in preguntas.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            estado = "resuelta" if "RESUELT" in linea.upper() else "abierta"
            actual = None
        m = TITULO_PREGUNTA.match(linea)
        if m:
            actual = f"A{int(m.group(1))}"
            nodo(actual, "pregunta", actual, titulo=m.group(2).strip(), estado=estado)
            secciones[actual] = []
        elif linea.startswith("### "):
            actual = None
        if actual:
            secciones[actual].append(linea)
    for pid, lineas in secciones.items():
        texto = "\n".join(lineas)
        nodos[pid]["texto"] = texto
        for hid in set(HALLAZGO.findall(texto)):
            nodo(hid, "hallazgo", hid)
            arista(pid, hid, "menciona")
        for cod, n in Counter(pieza_re.findall(texto)).items():
            arista(pid, f"pieza:{cod}", "menciona", n)

    # casos de referencia
    for x in datos.casos():
        nodo(x["id"], "caso", x["id"], resumen=f"{x.get('tratamiento_esperado')}: {x.get('motivo')}"[:240])
        arista(x["id"], f"pieza:{x.get('pieza')}", "pieza")

    # Markdown
    textos = {}
    for path in ficheros_md():
        rel = path.relative_to(REPO).as_posix()
        texto = path.read_text(encoding="utf-8", errors="replace")
        textos[rel] = (path, texto)
        titulo = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), path.stem)
        nodo(rel, tipo_md(rel), titulo, ruta=rel, palabras=len(texto.split()))
    for rel, (path, texto) in textos.items():
        etiquetas = set()
        for destino in ENLACE.findall(texto):
            if destino.startswith("http"):
                continue
            try:
                objetivo = (path.parent / destino).resolve().relative_to(REPO).as_posix()
            except ValueError:
                continue
            arista(rel, objetivo, "enlace")
        for hid, n in Counter(HALLAZGO.findall(texto)).items():
            nodo(hid, "hallazgo", hid)
            arista(rel, hid, "menciona", n)
        for cid, n in Counter(CASO.findall(texto)).items():
            arista(rel, cid, "menciona", n)
        for m in PREGUNTA.finditer(texto):
            pid = f"A{int(m.group(1))}"
            if pid in nodos and not PAPEL.search(texto[max(0, m.start() - 12):m.start()]):
                arista(rel, pid, "menciona")
        for cod, n in Counter(pieza_re.findall(texto)).items():
            arista(rel, f"pieza:{cod}", "menciona", n)
            etiquetas.add(cod)
        partes = rel.split("/")
        if partes[0] == "conocimiento" and len(partes) >= 3 and re.match(r"\d-", partes[1]):
            arista(rel, f"feature:{partes[1][0]}", "carpeta", 5)
            etiquetas.add(partes[1])
            if partes[2] != "README.md":
                cod = re.match(r"\d{4}", partes[2])
                if cod:
                    arista(rel, f"pieza:{cod.group(0)}", "ficha", 5)
        nodos[rel]["etiquetas"] = sorted(etiquetas)[:12]

    grado = defaultdict(int)
    for (a, b, _), _peso in aristas.items():
        grado[a] += 1
        grado[b] += 1
    for n in nodos.values():
        n["grado"] = grado[n["id"]]
    return {"nodos": list(nodos.values()),
            "aristas": [{"source": a, "target": b, "tipo": t, "peso": p} for (a, b, t), p in aristas.items()]}


@lru_cache(maxsize=1)
def piezas_y_features() -> dict:
    """Piezas, features y familias: a qué features pertenece cada pieza y qué ficheros comparten las piezas.

    Dos piezas se unen si tienen un fichero idéntico (mismo SHA-256). Quedan fuera los que coinciden
    sin decir nada de las piezas: README de remisión (txt), caché del navegador (GPUCache, sin
    extensión) y ficheros vacíos. El cliente y los hallazgos no unen: el cliente de los informes es
    poco fiable (I-005) y un hallazgo como I-003 junta piezas por un problema de los datos.
    """
    c = datos.con()
    nodos = [{"id": f"feature:{f[0]}", "tipo": "feature", "etiqueta": f[0]}
             for f in c.execute("SELECT DISTINCT feature FROM documento WHERE feature IS NOT NULL ORDER BY 1")]
    nodos += [{"id": f"pieza:{p['codigo']}", "tipo": "pieza", "etiqueta": p["codigo"]} for p in datos.piezas()]
    aristas = [{"source": f"pieza:{f['codigo']}", "target": f"feature:{f['feature']}", "tipo": "feature", "ficheros": f["n"]}
               for f in c.execute("SELECT codigo, feature, count(*) n FROM documento WHERE codigo IS NOT NULL GROUP BY 1, 2")]
    por_contenido: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in c.execute("SELECT sha256, codigo, nombre, carpeta_norm FROM documento WHERE sha256 IS NOT NULL AND codigo IS NOT NULL"
                       " AND tamano > 0 AND lower(coalesce(ext, '')) NOT IN ('', 'txt') ORDER BY nombre"):
        por_contenido[f["sha256"]].setdefault(f["codigo"], {"nombre": f["nombre"], "carpeta": f["carpeta_norm"]})
    comunes: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for piezas in por_contenido.values():
        for a, b in combinations(sorted(piezas), 2):
            comunes[a, b].append(piezas[a])
    aristas += [{"source": f"pieza:{a}", "target": f"pieza:{b}", "tipo": "identicos",
                 "ficheros": sorted(lista, key=lambda x: x["nombre"])} for (a, b), lista in sorted(comunes.items())]
    # Las familias son agrupaciones nuestras (datos.FAMILIAS), no un dato de los originales.
    nodos += [{"id": f"familia:{nombre}", "tipo": "familia", "etiqueta": nombre, "supuesta": bool(f.get("supuesta")), "fuente": f["fuente"]}
              for nombre, f in datos.FAMILIAS.items()]
    aristas += [{"source": f"pieza:{c}", "target": f"familia:{nombre}", "tipo": "familia"}
                for nombre, f in datos.FAMILIAS.items() for c in f["piezas"]]
    return {"nodos": nodos, "aristas": aristas}


def contenido(id_: str) -> dict:
    g = construir()
    n = next((x for x in g["nodos"] if x["id"] == id_), None)
    if not n:
        return {"error": "no existe"}
    vecinos = [a for a in g["aristas"] if id_ in (a["source"], a["target"])]
    salida = {"nodo": n, "vecinos": len(vecinos)}
    if n.get("ruta") and (REPO / n["ruta"]).is_file():
        salida["markdown"] = (REPO / n["ruta"]).read_text(encoding="utf-8", errors="replace")
        salida["ruta"] = n["ruta"]
    elif n["tipo"] == "hallazgo":
        h = next((x for x in datos.hallazgos() if x["id"] == id_), None)
        salida["datos"] = h or {"nota": "Citado en el texto pero sin entrada en hallazgos.jsonl"}
    elif n["tipo"] == "pregunta":
        salida["markdown"] = n.get("texto", "")
    elif n["tipo"] == "caso":
        salida["datos"] = next((x for x in datos.casos() if x["id"] == id_), None)
    elif n["tipo"] == "pieza":
        salida["datos"] = next((p for p in datos.piezas() if p["codigo"] == n["etiqueta"]), None)
    return salida
