"""Grafo de la pestaña Piezas: piezas, features y familias, y qué ficheros idénticos comparten las piezas.

Hasta el 10/11/2026 había además un grafo de todo el conocimiento (Markdown, hallazgos, preguntas y casos) en
su propia pestaña; se quitó del visor. Lo que mostraba sigue en `conocimiento/` (Markdown y JSONL).
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from itertools import combinations

import datos


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
               for f in c.execute(f"SELECT codigo, feature, count(*) n FROM documento WHERE codigo IS NOT NULL AND {datos.SIN_THUMBS}"
                                  " GROUP BY 1, 2")]
    por_contenido: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in c.execute("SELECT sha256, codigo, nombre, carpeta_norm FROM documento WHERE sha256 IS NOT NULL AND codigo IS NOT NULL"
                       f" AND tamano > 0 AND lower(coalesce(ext, '')) NOT IN ('', 'txt') AND {datos.SIN_THUMBS} ORDER BY nombre"):
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
