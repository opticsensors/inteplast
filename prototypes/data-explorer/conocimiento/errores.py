"""Pestaña Errores: las incidencias (`I-`) de `conocimiento/hallazgos.jsonl`, por pieza.

- **Generales:** las de la sección «Transversales» de `incongruencias.md`. Una sola ficha, enlazada desde cada pieza a
  la que afectan; no se decide por número de piezas.
- **Otras referencias:** las que no citan ninguna pieza del catálogo (I-501, Anclajes; la plantilla 3247).
- **Estado:** «Duda» (pregunta abierta), «Pendiente de aclarar» (incongruencia abierta), «Explicación posible · sin
  confirmar» (`explicable`: hipótesis razonable sin confirmar), «Resuelta», «Corregida». Abierta no significa comprobada:
  ninguna se presenta como error demostrado. Las de explicación posible siguen pendientes (revisión del 09/11/2026).
- **Título:** la frase en negrita con la que abre su fila en `incongruencias.md`. El texto es el original, sin separar
  hechos y causas.

El resto de `hallazgos.jsonl` no son errores (`NO_SON_ERRORES`) y no se muestran en el visor: siguen en
`hallazgos.jsonl` y en las fichas `.md`. Las notas de estructura y formato y los casos de referencia salían en la pestaña
Revisión, quitada el 11/11/2026 (`conocimiento/revision-comprobaciones.md`).
"""

from __future__ import annotations

import re
from functools import lru_cache

import datos

ESTADOS = {"abierta": "Pendiente de aclarar", "explicable": "Explicación posible · sin confirmar", "resuelta": "Resuelta",
           "corregida": "Corregida"}
PENDIENTES = {"abierta": 0, "explicable": 1}  # sin confirmar; el número es el orden en la lista
# No son errores y no se muestran en el visor: siguen en conocimiento/hallazgos.jsonl y en las fichas Markdown.
# Los cinco primeros estaban en la pestaña Grafo (quitada el 10/11/2026); estructura y formato, en Revisión (11/11/2026).
NO_SON_ERRORES = {"leccion", "warning", "vinculo_feature_cota", "dato", "proceso", "estructura", "formato"}
RELEVANCIA = {"alta": 0, "media": 1, "baja": 2}


@lru_cache(maxsize=1)
def _incongruencias() -> str:
    return (datos.CONOCIMIENTO / "incongruencias.md").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def titulos() -> dict[str, str]:
    """La frase en negrita con la que abre cada fila de `incongruencias.md` (puede llevar un emoji delante)."""
    return {i: t.strip().rstrip(".:").strip()
            for i, t in re.findall(r"^\| (I-\d+) \| [^|*]*\*\*(.+?)\*\*", _incongruencias(), re.M)}


@lru_cache(maxsize=1)
def transversales() -> frozenset[str]:
    seccion = _incongruencias().split("## Transversales", 1)[1].split("\n## ", 1)[0]
    return frozenset(re.findall(r"^\| (I-\d+) \|", seccion, re.M))


@lru_cache(maxsize=1)
def catalogo() -> frozenset[str]:
    """Las piezas con ficha: los códigos de la biblioteca (mismo criterio que `datos.piezas`)."""
    return frozenset(r[0] for r in datos.con().execute("SELECT DISTINCT codigo FROM documento WHERE codigo IS NOT NULL"))


def estado(x: dict) -> str:
    if x.get("tipo") == "pregunta" and x.get("estado") == "abierta":
        return "Duda"
    return ESTADOS.get(x.get("estado"), x.get("estado") or "?")


def _evidencia(x: dict) -> list[dict]:
    salida = []
    for e in x.get("evidencia") or []:
        if isinstance(e, dict) and e.get("ruta"):
            carpeta, _, fichero = e["ruta"].rpartition("/")
            salida.append({"fichero": fichero, "carpeta": carpeta, "localizador": e.get("localizador")})
    return salida


def _graficas(x: dict) -> list[dict]:
    return [{"pieza": c["pieza"], "cota": re.sub(r"(?i)^N", "", str(c["cota"]))}
            for c in x.get("cotas") or [] if isinstance(c, dict) and c.get("pieza") in catalogo() and c.get("cota")]


@lru_cache(maxsize=1)
def incidencias() -> tuple[dict, ...]:
    salida = []
    for x in datos.hallazgos():
        if not x["id"].startswith("I-"):
            continue
        piezas = sorted(datos.piezas_de(x.get("pieza")))
        salida.append({
            "id": x["id"], "titulo": titulos().get(x["id"]) or x.get("titulo") or x["id"], "estado": estado(x),
            "pendiente": x.get("estado") in PENDIENTES, "orden": PENDIENTES.get(x.get("estado"), 2), "relevancia": x.get("relevancia"), "texto": x.get("afirmacion") or "",
            "piezas": piezas, "general": x["id"] in transversales(), "en_catalogo": [p for p in piezas if p in catalogo()],
            "evidencia": _evidencia(x), "graficas": _graficas(x),
        })
    # Pendientes de aclarar, después las de explicación posible y al final las cerradas; dentro, por relevancia y número.
    salida.sort(key=lambda i: (i["orden"], RELEVANCIA.get(i["relevancia"], 3), [int(n) for n in re.findall(r"\d+", i["id"])]))
    return tuple(salida)


def _otra(i: dict) -> bool:
    return i["general"] or not i["en_catalogo"]


def propias(codigo: str) -> list[dict]:
    return [i for i in incidencias() if not i["general"] and codigo in i["piezas"]]


def generales_de(codigo: str) -> list[dict]:
    return [i for i in incidencias() if i["general"] and codigo in i["piezas"]]


def resumen_pieza(codigo: str) -> dict:
    p, g = propias(codigo), generales_de(codigo)
    return {"propias_pendientes": sum(i["pendiente"] for i in p), "propias": len(p),
            "generales_pendientes": sum(i["pendiente"] for i in g), "generales": len(g)}


def lista() -> dict:
    """Una fila por pieza del catálogo y otra para las generales y otras referencias."""
    otras = [i for i in incidencias() if _otra(i)]
    return {"piezas": [{"codigo": p["codigo"], "carpetas": p["carpetas"], "features": p["features"], **resumen_pieza(p["codigo"])}
                       for p in datos.piezas()],
            "otras": {"pendientes": sum(i["pendiente"] for i in otras), "total": len(otras)}}


def de_pieza(codigo: str) -> dict:
    return {"codigo": codigo, **resumen_pieza(codigo), "incidencias": propias(codigo)}


def generales(pieza: str | None = None) -> dict:
    """Con pieza, solo las generales que le afectan; sin ella, las generales y las que no citan una pieza del catálogo."""
    return {"pieza": pieza, "incidencias": generales_de(pieza) if pieza else [i for i in incidencias() if _otra(i)]}


