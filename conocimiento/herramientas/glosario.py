"""Glosario multilingue del dominio (ES/CA/EN/DE/CS) para ampliar las consultas del RAG.

Los originales de Exemples estan sobre todo en ingles y catalan; las preguntas suelen ser en castellano.
`venteo` no aparece en ningun original y `venting`, en 12 documentos (27/10/2026): sin ampliar la consulta,
ni la busqueda literal ni la semantica encuentran esas diapositivas. El glosario vive en
conocimiento/rag/glosario.json, es una propuesta revisable y no cambia el indice: solo la consulta.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

IDIOMAS = ("es", "ca", "en", "de", "cs")
MAX_TERMINOS = 24   # tope de terminos anadidos por consulta, para no diluir la busqueda


def plano(texto: str) -> str:
    """Minusculas sin diacriticos, como el FTS5 de la biblioteca y del indice (unicode61 remove_diacritics 2)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.casefold()) if not unicodedata.combining(c))


def cargar(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("conceptos", [])


def terminos(concepto: dict) -> list[str]:
    return list(dict.fromkeys(t for idioma in IDIOMAS for t in concepto.get(idioma, [])))


def aparece(termino: str, texto_plano: str) -> bool:
    t = plano(termino)
    if t.endswith("*"):
        return re.search(r"(?<!\w)" + re.escape(t[:-1]) + r"\w*", texto_plano) is not None
    return re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", texto_plano) is not None


def expandir(consulta: str, conceptos: list[dict]) -> list[dict]:
    """Conceptos disparados por la consulta, con los terminos que hay que anadir (los que no estan ya)."""
    q = plano(consulta)
    salida, total = [], 0
    for c in conceptos:
        solo_destino = {plano(t) for t in c.get("solo_destino", [])}
        todos = terminos(c)
        disparadores = [t for t in todos if plano(t) not in solo_destino and aparece(t, q)]
        if not disparadores:
            continue
        nuevos = [t for t in todos if not aparece(t, q)][:max(0, MAX_TERMINOS - total)]
        total += len(nuevos)
        salida.append({"concepto": c["id"], "disparado_por": disparadores, "terminos": nuevos})
    return salida


def termino_fts(termino: str) -> str:
    """Frase FTS5 entre comillas; un '*' final la convierte en prefijo (`"creix"*`)."""
    t = termino.replace('"', "").strip()
    return f'"{t[:-1]}"*' if t.endswith("*") else f'"{t}"'


def anadidos(expansion: list[dict]) -> list[str]:
    return list(dict.fromkeys(t for e in expansion for t in e["terminos"]))
