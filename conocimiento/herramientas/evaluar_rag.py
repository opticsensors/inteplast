"""Evaluacion de la recuperacion del RAG con preguntas de respuesta conocida (conocimiento/rag/preguntas.jsonl).

Para cada pregunta se busca con sus filtros y se mira en que posicion aparece la primera fuente esperada
(subcadena, sin distinguir mayusculas, en id, ruta, localizador, seccion o extracto). Mide recuperacion,
no la calidad de una respuesta redactada. Las preguntas se escribieron leyendo las fichas: un acierto alto
no prueba cobertura de preguntas reales de INTEPLAST (ver conocimiento/rag/README.md). Las del conjunto
`control` (C-…) se escribieron despues de ajustar el glosario y no se han usado para ajustarlo.

    PY=conocimiento/.venv/Scripts/python.exe
    $PY conocimiento/herramientas/evaluar_rag.py [--k 5] [--sin-glosario] [--solo R-014,R-020] [--json]
    $PY conocimiento/herramientas/evaluar_rag.py --codigo <carpeta con otra version de rag.py>   # comparar versiones
    $PY conocimiento/herramientas/evaluar_rag.py --registrar   # anade el resumen a datos/rag/evaluacion.jsonl
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CONOCIMIENTO = AQUI.parent
PREGUNTAS = CONOCIMIENTO / "rag" / "preguntas.jsonl"
REGISTRO = CONOCIMIENTO / "datos" / "rag" / "evaluacion.jsonl"
CAMPOS = ("id", "ruta", "localizador", "seccion", "titulo", "extracto")


def cargar_rag(codigo: Path | None):
    """rag.py de esta carpeta o de otra (p. ej. la version de HEAD), siempre sobre el mismo indice y biblioteca."""
    carpeta = codigo or AQUI
    sys.path.insert(0, str(carpeta))
    for nombre in ("rag", "rag_fuentes", "glosario", "comun"):
        sys.modules.pop(nombre, None)
    rag = importlib.import_module("rag")
    raiz = CONOCIMIENTO.parent
    rutas = rag.Rutas(raiz=raiz, biblioteca=CONOCIMIENTO / "datos" / "biblioteca.sqlite", rag=CONOCIMIENTO / "datos" / "rag")
    return rag, rutas


def posicion(resultados: list[dict], esperado: list[str]) -> int | None:
    claves = [e.casefold() for e in esperado]
    for i, r in enumerate(resultados, 1):
        texto = " ".join(str(r.get(c) or "") for c in CAMPOS).casefold()
        if any(c in texto for c in claves):
            return i
    return None


def evaluar(k: int, glosario: bool, codigo: Path | None, solo: set[str] | None) -> dict:
    rag, rutas = cargar_rag(codigo)
    preguntas = [json.loads(l) for l in PREGUNTAS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if solo:
        preguntas = [p for p in preguntas if p["id"] in solo]
    embedder = rag.Ollama()
    admite_glosario = "glosario" in rag.buscar.__code__.co_varnames   # versiones anteriores al 27/10/2026 no lo tienen
    glosario = glosario and admite_glosario
    filas = []
    for p in preguntas:
        filtros = rag.Filtros(**{k2: v for k2, v in (p.get("filtros") or {}).items()})
        opciones = {"glosario": glosario} if admite_glosario else {}
        r = rag.buscar(rutas, p["pregunta"], "hibrido", filtros, n=k, embedder=embedder, **opciones)
        pos = posicion(r["resultados"], p["esperado"])
        filas.append({"id": p["id"], "conjunto": p.get("conjunto", "ajuste"), "tipo": p["tipo"], "pregunta": p["pregunta"], "posicion": pos,
                      "modo": r.get("modo_efectivo"), "expansion": [e["concepto"] for e in r.get("expansion", [])],
                      "colecciones": [x["coleccion"] for x in r["resultados"]]})
    resumen = resumir(filas, k)
    return {"k": k, "glosario": glosario, "codigo": str(codigo or AQUI), "preguntas": len(filas), "resumen": resumen, "filas": filas}


def resumir(filas: list[dict], k: int) -> dict:
    def metricas(grupo: list[dict]) -> dict:
        n = len(grupo) or 1
        salida = {f"recall@{c}": round(sum(1 for f in grupo if f["posicion"] and f["posicion"] <= c) / n, 3)
                  for c in (1, 3, 5, k) if c <= k}
        salida["mrr"] = round(sum(1 / f["posicion"] for f in grupo if f["posicion"]) / n, 3)
        salida["n"] = len(grupo)
        return salida
    grupos = defaultdict(list)
    for f in filas:
        grupos[f["tipo"]].append(f)
        grupos[f"conjunto:{f['conjunto']}"].append(f)
    return {"total": metricas(filas), **{t: metricas(g) for t, g in sorted(grupos.items())}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--sin-glosario", action="store_true")
    ap.add_argument("--codigo", type=Path, help="carpeta con otra version de rag.py (y sus modulos) para comparar")
    ap.add_argument("--solo", help="ids separados por comas")
    ap.add_argument("--registrar", action="store_true", help=f"anadir el resultado a {REGISTRO}")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.k < 1:
        ap.error("--k debe ser >= 1")
    r = evaluar(args.k, not args.sin_glosario, args.codigo, set(args.solo.split(",")) if args.solo else None)
    if args.registrar:
        from datetime import datetime, timezone
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), **r}, ensure_ascii=False) + "\n")
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    for f in r["filas"]:
        marca = "OK" if f["posicion"] else "NO"
        print(f"{marca} {f['id']} pos={f['posicion']} [{f['tipo']}] {f['pregunta']}"
              + (f"  · glosario: {','.join(f['expansion'])}" if f["expansion"] else ""))
    print(f"\n{r['preguntas']} preguntas · k={r['k']} · glosario={'si' if r['glosario'] else 'no'} · codigo {r['codigo']}")
    for grupo, m in r["resumen"].items():
        print(f"  {grupo:12} " + " · ".join(f"{k}={v}" for k, v in m.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
