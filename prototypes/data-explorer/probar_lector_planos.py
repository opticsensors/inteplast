"""Mide los lectores de globos en todos los planos de Exemples que tienen globos de color.

    py -3.11 prototypes/data-explorer/probar_lector_planos.py
    py -3.11 prototypes/data-explorer/probar_lector_planos.py --solo 1937 4091

Recorre los PDF de planos de la biblioteca (conocimiento/datos/biblioteca.sqlite), detecta los
globos verdes o azules (en la capa vectorial si el PDF los trae como vectores), elige la
orientación de la página y los lee con RapidOCR (como el buscador del 28/10), PP-OCRv6 small (si
está descargado), los lectores propios de entrenar_lector_globos.py (perfiles 3212, amplio y
general, con torch) y el lector combinado (RapidOCR + general en ONNX, un número por plano).
Ningún lector se reentrena con estos planos.

Detección, orientación, lector combinado y calibración `.icp` salen de lectores_planos.py: lo que
se mide aquí es lo mismo que enseña el visor de conocimiento/.

Referencias, sin lectura manual por parte de los usuarios:
- `.icp` de infra-CONVERT de la misma carpeta, o de la de un duplicado exacto (tabla `globo`):
  número y posición de cada sello en unidades del dibujo. La transformación a la página se ajusta
  una vez por plano con RANSAC (giro, escala, desplazamiento y simetría vertical), usando como
  emparejamientos tentativos las lecturas de todos los lectores de esa primera ejecución; se
  acepta si explica al menos el 30 % de los globos y se guarda en out/probar-planos-calibracion.json.
  Las ejecuciones siguientes la reutilizan (--recalibrar la rehace). Ningún número del `.icp`
  entra en los lectores.
- Lecturas visuales de referencia (`out/*/chuleta-*.json`, fuera de Git) del mismo PDF.
- PDF sin globos revisados a ojo: todo lo detectado en ellos es falso.

Se mide sobre todos los globos de referencia, no solo los detectados: cuántos se detectan y
emparejan, cuántos se leen bien y la cobertura (globos con su número bien ofrecido). Las
detecciones sin referencia se cuentan como pendientes de validar. Las páginas con referencia se
evalúan aunque no tengan ninguna detección. Cada ejecución guarda su configuración (modelos,
umbral, versión) en configuracion.json. Planos sin referencia: se leen y se guarda una muestra de
32 globos para revisarla a ojo.

Desde el 09/11/2026 las puntuaciones se guardan completas y los umbrales se aplican sobre ellas, como
en el visor; configuracion.json lleva la identidad del lector combinado. Los resultados anteriores
(out/probar-planos*/, hasta el 29/10/2026) son histórico: guardan las puntuaciones redondeadas a 4
decimales, y una lectura justo por debajo del umbral podía contarse como ofrecida. No se añaden
resultados nuevos a una carpeta hecha con puntuaciones redondeadas o con otro lector combinado.
Cada página calibrada guarda la huella de los sellos del .icp que usó (`sellos_sha256`), y la
calibración solo se reutiliza si esos sellos no han cambiado (corrección de globos_icp.py, 09/11/2026).
Cada página con referencia guarda además, en `fallos_combinado`, los fallos del lector combinado tal
como lo ve el visor (umbral por fuente): sellos sin globo detectado, globos sin lectura ofrecida,
números erróneos, lecturas en globos falsos y lecturas ofrecidas en detecciones sin referencia; la
hoja errores-<página>.png muestra los dos tipos con globo detectado.

Lee los originales sin copiarlos; resultados y hojas en out/probar-planos/ (fuera de Git).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sqlite3
import sys
import time
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_ocr_globos as bench
import lectores_planos as lectores

REPO = Path(__file__).resolve().parents[2]
LIBRARY = REPO / "conocimiento" / "datos" / "biblioteca.sqlite"
EXEMPLES = Path(r"C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples")
OUTPUT = Path(__file__).resolve().parent / "out" / "probar-planos"
# Páginas sin globos, con su evidencia: todo lo que se detecte en ellas es falso y no aportan
# referencias. Se declaran aquí, por página, independientemente de lo que detecte el algoritmo.
# Revisadas a ojo el 29/10/2026 (Claude). «Sin capa vectorial»: 0 trazados en la página, según PyMuPDF.
# Prueban que los globos del .icp de su carpeta no están en esa página; no que no haya ninguna
# numeración de otro tipo (en el 3288 hay marcas «cc» de cota crítica, sin número).
NO_BALLOON_PAGES = {
    "2184-p1": "3206 Drw_Marking_DR_intern02.pdf: cotas resaltadas en azul, sin globos",
    "1588-p1": "3309 plano del cliente: texto azul y símbolos ②, sin globos",
    "1935-p1": "3205 213137-10300/3205.pdf: el mismo plano escaneado sin globos ni capa vectorial; "
               "el .icp de la carpeta es el de 3205_balloned.pdf",
    "1939-p1": "3205 213137-10300-A/3205-A.pdf: plano rev. A escaneado sin globos ni capa vectorial; "
               "el .icp es el de 3205-A_balloned.pdf",
    "2195-p1": "3206 213137-10280/3206.pdf: plano escaneado sin globos ni capa vectorial; "
               "el .icp es el de 3206_balloned.pdf",
    "2199-p1": "3206 213137-10280-A/3206-A.pdf: plano rev. A escaneado sin globos ni capa vectorial; "
               "el .icp es el de 3206-A_balloned lr.pdf",
    "4077-p1": "3202 20231129_885253-11250_insulator_motor_v1.pdf: plano escaneado (15 imágenes) sin globos "
               "ni capa vectorial; el .icp es el de la versión «_ Ballooned» y de 3202_balloned.pdf",
    "4086-p1": "3202 885253-11250/3202.pdf: plano escaneado sin globos ni capa vectorial; "
               "el .icp es el de 3202_balloned low resolution.pdf",
    "3029-p1": "3288 Cj20240714_BSG-296-01-N0 (B. Braun, vectorial, sin imágenes) hoja BSG-296-01: sin globos",
    "3029-p2": "3288 Cj20240714_BSG-296-01-N0 hoja BSG-296-00: sin globos; marcas «cc» sin número",
    "3029-p3": "3288 Cj20240714_BSG-296-01-N0 hoja BSG-296-02: sin globos",
    "3116-p1": "3288 REV.01 20250714_BSG-296-00 SOP RCP 3.1.pdf (vectorial): sin globos; marcas «cc» sin número",
    "3124-p1": "3288 REV.01 BSG-296-2 SOP RCP 3.1.pdf (vectorial): sin globos",
    "3126-p1": "3288 REV.02 BSG-296-00 SOP RCP 3.1 .pdf (vectorial, v4): sin globos; marcas «cc» sin número",
    "3126-p2": "3288 REV.02 BSG-296-00 SOP RCP 3.1 .pdf: página de firmas",
}
# Desarrollo: piezas que se miran para diseñar y ajustar. Examen: apartadas, solo se miden al final.
GROUPS = {"todos": set(), "desarrollo": {"3205", "3206", "3212"},
          "examen": {"3202", "3288", "3167", "3195", "3237", "3238", "3309"}}


def drawing_pdfs(con) -> list[tuple[int, str, str]]:
    """PDF de plano únicos: carpeta 2D de la pieza o carpetas de globos/método de medición."""
    return con.execute(
        "SELECT id, pieza, ruta FROM documento WHERE ext='pdf' AND duplicado_de IS NULL"
        " AND estado IN ('sin_texto','extraido') AND (carpeta_norm='pieza_2d3d'"
        " OR lower(ruta) LIKE '%ballo%' OR lower(ruta) LIKE '%balon%' OR lower(ruta) LIKE '%drw%')"
        " ORDER BY pieza, ruta").fetchall()


def stamps_near(con, ruta: str) -> dict[str, list[dict]]:
    """Sellos de cada .icp de la misma carpeta, con etiqueta y coordenadas."""
    folder = posixpath.dirname(ruta)
    found = {}
    for doc_id, icp in con.execute("SELECT id, ruta FROM documento WHERE ext='icp' AND ruta LIKE ?", (folder + "/%",)):
        if posixpath.dirname(icp) != folder:
            continue
        rows = con.execute("SELECT etiqueta, x1, y1, x2, y2 FROM globo WHERE documento_id=? AND x1 IS NOT NULL"
                           " AND etiqueta IS NOT NULL", (doc_id,)).fetchall()
        stamps = [{"label": lectores.normalize_number(e), "points": ((x1, y1), (x2, y2))} for e, x1, y1, x2, y2 in rows]
        found[posixpath.basename(icp)] = [s for s in stamps if s["label"]]
    return found


def icp_digests(con, ruta: str) -> dict[str, str]:
    """SHA-256 de cada .icp de la misma carpeta, por nombre."""
    folder = posixpath.dirname(ruta)
    return {posixpath.basename(icp): hashlib.sha256((EXEMPLES / icp).read_bytes()).hexdigest()
            for (icp,) in con.execute("SELECT ruta FROM documento WHERE ext='icp' AND ruta LIKE ?", (folder + "/%",))
            if posixpath.dirname(icp) == folder}


# Referencia de cada detección: el número, NOT_A_BALLOON si está comprobado que no es un globo, o
# None si no se sabe (p. ej., un globo real cuyo sello del .icp no tiene número ni posición).
NOT_A_BALLOON = "—"
# Calibración .icp → página, compartida por todas las ejecuciones y por el visor (ver `lectores.calibrate`).
CALIBRATION = lectores.CALIBRACION


def visual_reference(digest: str) -> dict | None:
    """Lectura visual de referencia del PDF con esa huella, si existe (chuletas en out/, fuera de Git)."""
    for path in sorted(OUTPUT.parent.glob("*/chuleta-*.json")):
        reference = json.loads(path.read_text(encoding="utf-8"))
        if reference.get("pdf_sha256") == digest:
            return reference
    return None


def visual_truth(reference: dict, size: tuple[int, int], balloons) -> tuple[list, int]:
    """Número de cada detección según la lectura visual, uno a uno, y cuántos globos reales se emparejan.

    Las entradas de la referencia sin número son detecciones comprobadas que no son un globo.
    """
    height, width = size
    centres = [((g["box"][0] + g["box"][2]) / 2 * width, (g["box"][1] + g["box"][3]) / 2 * height,
                g["lectura_visual"] or NOT_A_BALLOON) for g in reference["globos"]]
    pairs = sorted((np.hypot(cx - b["circle"][0], cy - b["circle"][1]), i, j)
                   for i, b in enumerate(balloons) for j, (cx, cy, _) in enumerate(centres)
                   if np.hypot(cx - b["circle"][0], cy - b["circle"][1]) < max(b["circle"][2] / 2, 3))
    truth, used = [None] * len(balloons), set()
    for _, i, j in pairs:
        if truth[i] is None and j not in used:
            truth[i] = centres[j][2]
            used.add(j)
    return truth, sum(1 for t in truth if t not in (None, NOT_A_BALLOON))


def read_all(rgb, balloons, readers, combined=None) -> dict[str, list[list[tuple[str, float]]]]:
    """Lecturas de cada lector, por globo. «combinado» es el del visor y el buscador (lectores_planos.py),
    con el lector propio en ONNX que se pasa en `combined`; necesita también «buscador»."""
    out = {}
    for name, read in readers.items():
        if name == "buscador":  # el buscador actual tal cual: RapidOCR sobre tres vistas
            out[name] = lectores.rapid_predictions(rgb, balloons, read)
            continue
        own = name.startswith("propio")
        runs = [read([lectores.text_crop(rgb, b["circle"], "luma", shift=s, fit_text=True) for b in balloons])
                for s in (lectores.SHIFTS if own else lectores.SHIFTS[:1])]
        out[name] = lectores.merge(runs[:1])
        if own:
            out[name + " + desplazados"] = lectores.merge(runs)
            out[name + " + desplazados + únicos"] = lectores.unique_assignment(out[name + " + desplazados"])
    if "buscador" in out and combined is not None:
        # Los dos lectores votan con su puntuación; después, un número por plano.
        out["combinado"] = lectores.combine(out["buscador"], lectores.own_predictions(rgb, balloons, combined))
    return out


def score(predictions, truth, sources: list[str] | None = None) -> dict:
    """Aciertos, errores y vacíos en globos con referencia; detecciones falsas y pendientes aparte.

    Una lectura ofrecida en algo comprobado que no es un globo es un error para quien busca: cuenta
    como tal en la curva de confianza («aceptables») y en `detalle`, que guarda (puntuación,
    resultado, fuente del globo) para fijar después umbrales comunes, también por fuente. Las
    detecciones sin referencia no se dan por buenas ni por falsas: son pendientes de validar.
    La puntuación se guarda completa: redondeada, una lectura de 0,60718 pasaría el umbral de 0,6072,
    y el visor no la ofrece.
    """
    counts = {"acierto": 0, "error": 0, "sin_lectura": 0, "falsas_con_lectura": 0, "pendientes": 0,
              "pendientes_con_lectura": 0}
    sources = sources or ["imagen"] * len(truth)
    scored = []
    for candidates, label, source in zip(predictions, truth, sources):
        read = lectores.label_of(candidates[0][0]) if candidates else None
        value = float(candidates[0][1]) if candidates else 0.
        if label is None:
            counts["pendientes"] += 1
            if read:
                counts["pendientes_con_lectura"] += 1
                scored.append({"lectura": read, "resultado": "pendiente", "puntuacion": value, "fuente": source})
            continue
        if label == NOT_A_BALLOON:
            if read:
                counts["falsas_con_lectura"] += 1
                scored.append({"lectura": read, "resultado": "falsa", "puntuacion": value, "fuente": source})
            continue
        outcome = "sin_lectura" if not read else "acierto" if read == label else "error"
        counts[outcome] += 1
        scored.append({"lectura": read, "resultado": outcome, "puntuacion": value, "fuente": source})
    safe = bench.best_at_precision(bench.precision_curve([s for s in scored if s["resultado"] != "pendiente"]),
                                   .01) or {}
    counts["aceptables_1pct"] = safe.get("aciertos", 0)
    counts["detalle"] = [(s["puntuacion"], s["resultado"], s["fuente"]) for s in scored]
    return counts


def offered(detail, threshold) -> tuple[int, int, int]:
    """Lecturas ofrecidas con ese umbral: (correctas, erróneas o en falsos globos, pendientes de validar).

    `threshold` es un número o un umbral por fuente del globo ({"capa vectorial": t, "imagen": t}).
    """
    def limit(item):
        return threshold[item[2] if len(item) > 2 else "imagen"] if isinstance(threshold, dict) else threshold
    shown = [item[1] for item in detail if item[0] >= limit(item)]
    return shown.count("acierto"), shown.count("error") + shown.count("falsa"), shown.count("pendiente")


def choose_threshold(detail, max_wrong: float) -> float:
    """El umbral más bajo (más lecturas ofrecidas) con, como mucho, `max_wrong` de lecturas erróneas."""
    for value in sorted({item[0] for item in detail if item[0] > 0}):
        ok, wrong, _ = offered(detail, value)
        if wrong <= max_wrong * (ok + wrong):
            return value
    return float("inf")


def page_detail(entry: dict, reader: str) -> list[tuple]:
    """Detalle de un lector en una página, con la fuente de cada globo. Los resultados anteriores al
    29/10/2026 no la guardaban: se toma la vía de la página, que entonces era una sola."""
    via = "capa vectorial" if entry.get("via") == "capa vectorial" else "imagen"
    return [tuple(d) if len(d) > 2 else (*d, via) for d in entry.get("lectores", {}).get(reader, {}).get("detalle", [])]


def threshold_summary(development: Path, exam: Path, max_wrong: float = .02, image_threshold: float | None = None,
                      output: Path | None = None) -> dict:
    """Umbral fijado con el primer grupo y aplicado sin cambios al segundo; resultado en `output`.

    Por grupo y lector: globos de referencia, cuántos se detectan y emparejan, aciertos sobre los
    emparejados y, con el umbral, lecturas ofrecidas bien, mal y pendientes de validar, y la
    **cobertura** (globos de referencia con su número bien ofrecido). El denominador son todas las
    referencias de las páginas evaluadas, tengan o no detecciones; solo quedan fuera las páginas
    declaradas sin globos (`NO_BALLOON_PAGES`). Para el combinado se usa el umbral exacto del
    buscador (lectores_planos.py), y se ensaya además un umbral por fuente del globo: el del buscador
    para la capa vectorial y, para la imagen, el mayor entre ese y el elegido en el primer grupo solo con globos
    de imagen (o `image_threshold`). El ensayo no cambia el buscador.
    """
    groups = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in
              (("desarrollo", development), ("examen", exam)) if path.is_file()}
    readers = sorted({r for entries in groups.values() for e in entries.values() for r in e.get("lectores", {})
                      if "detalle" in e["lectores"][r]})
    counted = lambda entries: {k: e for k, e in entries.items() if k not in NO_BALLOON_PAGES}
    result = {"fecha": time.strftime("%Y-%m-%d %H:%M"), "max_errores": max_wrong,
              "umbrales_buscador": dict(lectores.COMBINED_THRESHOLDS),
              "ficheros": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                           for path in (development, exam) if path.is_file()},
              "paginas_sin_globos": sorted(NO_BALLOON_PAGES), "lectores": {}, "por_plano": {}}
    print(f"Umbral: como mucho un {max_wrong:.0%} de lecturas ofrecidas erróneas en desarrollo")

    def row(reader, entries, threshold):
        # Las páginas declaradas sin globos no aportan referencias, pero sus lecturas falsas sí cuentan.
        references = sum(e.get("referencias", 0) for e in counted(entries).values())
        stats = [e["lectores"][reader] for e in entries.values() if "detalle" in e.get("lectores", {}).get(reader, {})]
        matched = sum(r["acierto"] + r["error"] + r["sin_lectura"] for r in stats)
        ok, wrong, pending = offered([d for e in entries.values() for d in page_detail(e, reader)], threshold)
        return {"referencias": references, "emparejados": matched, "aciertos": sum(r["acierto"] for r in stats),
                "bien": ok, "mal": wrong, "pendientes_ofrecidas": pending,
                "pendientes": sum(r.get("pendientes", 0) for r in stats)}

    def show(label, name, r, threshold):
        t = (f"{threshold:.4f}" if not isinstance(threshold, dict)
             else " / ".join(f"{k[:4]} {v:.4f}" for k, v in threshold.items()))
        print(f"{label:38} {name:10} referencias {r['referencias']:5} · emparejados {r['emparejados']:5} "
              f"({r['emparejados'] / max(1, r['referencias']):.1%}) · aciertos "
              f"{r['aciertos'] / max(1, r['emparejados']):6.1%} · umbral {t}: bien {r['bien']} "
              f"(cobertura {r['bien'] / max(1, r['referencias']):.1%}), mal {r['mal']} "
              f"({r['mal'] / max(1, r['bien'] + r['mal']):.1%} de las evaluables ofrecidas), "
              f"pendientes ofrecidas {r['pendientes_ofrecidas']} (de {r['pendientes']} pendientes)")

    policies = {}
    for reader in readers:
        development_detail = [d for e in groups.get("desarrollo", {}).values() for d in page_detail(e, reader)]
        threshold = choose_threshold(development_detail, max_wrong)
        if reader == "combinado":
            # Las dos políticas usan los valores exactos del buscador; se avisa si los que se
            # eligen ahora en desarrollo son otros. «un umbral» es el de la capa vectorial para todo.
            single, by_source = lectores.COMBINED_THRESHOLDS["capa vectorial"], dict(lectores.COMBINED_THRESHOLDS)
            image = choose_threshold([d for d in development_detail if d[2] == "imagen"], max_wrong)
            for name, chosen, used in (("un umbral", threshold, single), ("imagen", max(single, image), by_source["imagen"])):
                # Solo para este aviso se redondea a 4 decimales, como se fijaron los umbrales del buscador:
                # con puntuaciones completas se elige, p. ej., 0,60721 donde se fijó 0,6072. La decisión
                # de ofrecer una lectura usa siempre la puntuación completa.
                if round(chosen, 4) != round(used, 4):
                    print(f"AVISO: en desarrollo se elige {chosen} ({name}), pero el buscador usa {used}")
            if image_threshold is not None:
                by_source["imagen"] = image_threshold
            threshold = single
            policies = {"un umbral": single, "por fuente": by_source}
        for name, entries in groups.items():
            for label, t in ([(reader, threshold)] if reader != "combinado"
                             else [(f"combinado · {k}", v) for k, v in policies.items()]):
                r = row(reader, entries, t)
                result["lectores"].setdefault(label, {})[name] = dict(r, umbral=t)
                show(label, name, r, t)
    for name, entries in groups.items():
        for key, e in entries.items():
            if not e.get("referencias") and "detalle" not in e.get("lectores", {}).get("combinado", {}):
                continue
            declared = key in NO_BALLOON_PAGES  # sin globos: no aporta referencias, aunque un resultado antiguo las traiga
            plan = {"pieza": e.get("pieza"), "grupo": name, "fuente": e.get("via"),
                    "referencias": 0 if declared else e.get("referencias", 0), "emparejados": e.get("emparejados", 0),
                    "referencia": NO_BALLOON_PAGES[key] if declared else e.get("icp") or e.get("referencia")}
            for label, t in policies.items():
                ok, wrong, pending = offered(page_detail(e, "combinado"), t)
                plan[label] = {"bien": ok, "mal": wrong, "pendientes_ofrecidas": pending}
            result["por_plano"][key] = plan
    for name, entries in groups.items():
        empty = [k for k, e in counted(entries).items() if e.get("referencias") and
                 "detalle" not in e.get("lectores", {}).get("combinado", {})]
        if empty:
            print(f"{name}: páginas con referencia y sin resultados, que cuentan como no encontradas: {', '.join(empty)}")
    if output:
        output.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Resumen: {output}")
    return result


def compare(before: Path, after: Path):
    """Antes y después por plano y agregado, a partir de dos resúmenes con los mismos umbrales."""
    old, new = (json.loads(path.read_text(encoding="utf-8")) for path in (before, after))
    empty = {"bien": 0, "mal": 0, "pendientes_ofrecidas": 0}
    for policy in ("un umbral", "por fuente"):
        print(f"\n{policy}: plano · fuente · referencias · bien antes→después · mal · pendientes ofrecidas")
        totals = {}
        for key in sorted(set(old["por_plano"]) | set(new["por_plano"]), key=lambda k: int(k.split("-")[0])):
            a = old["por_plano"].get(key, {}).get(policy, empty)
            b = new["por_plano"].get(key, {}).get(policy, empty)
            plan = new["por_plano"].get(key) or old["por_plano"][key]
            group = totals.setdefault(plan["grupo"], [0] * 7)
            for i, v in enumerate((plan["referencias"], a["bien"], b["bien"], a["mal"], b["mal"],
                                   a["pendientes_ofrecidas"], b["pendientes_ofrecidas"])):
                group[i] += v
            flag = "  ← regresión" if b["bien"] < a["bien"] or b["mal"] > a["mal"] else ""
            print(f"  {key:9} {plan['pieza'][:4]:4} {str(plan['fuente'])[:26]:26} {plan['referencias']:4} · "
                  f"{a['bien']:4}→{b['bien']:4} · {a['mal']:3}→{b['mal']:3} · "
                  f"{a['pendientes_ofrecidas']:3}→{b['pendientes_ofrecidas']:3}{flag}")
        for name, (refs, a_ok, b_ok, a_bad, b_bad, a_p, b_p) in totals.items():
            print(f"  {name}: cobertura {a_ok / max(1, refs):.1%}→{b_ok / max(1, refs):.1%} · "
                  f"mal {a_bad}→{b_bad} ({a_bad / max(1, a_ok + a_bad):.1%}→{b_bad / max(1, b_ok + b_bad):.1%}) · "
                  f"pendientes ofrecidas {a_p}→{b_p}")


def failures(balloons, combined, truth, size: tuple[int, int], not_found=()) -> dict:
    """Fallos del lector combinado en una página, con lo que ofrece el visor (umbral de la fuente de cada globo).

    - `no_detectados`: sellos del .icp sin globo detectado (`not_found`: número y posición en píxeles).
    - `sin_lectura`: globo con referencia sin lectura ofrecida; `propuesta` es lo que quedó bajo el umbral.
    - `erroneos`: lectura ofrecida con otro número.
    - `en_falso`: lectura ofrecida en algo comprobado que no es un globo.
    - `sin_referencia`: lectura ofrecida en una detección sin referencia (ni acierto ni error: no se sabe).
    Posiciones normalizadas a la página sin girar (0–1); la puntuación, completa.
    """
    height, width = size
    where = lambda x, y: {"x": round(float(x) / width, 4), "y": round(float(y) / height, 4)}
    out = {"no_detectados": [dict(numero=label, **where(x, y)) for label, x, y in not_found],
           "sin_lectura": [], "erroneos": [], "en_falso": [], "sin_referencia": []}
    for balloon, candidates, label in zip(balloons, combined, truth):
        source = balloon.get("fuente", "imagen")
        read = lectores.label_of(candidates[0][0]) if candidates else None
        value = float(candidates[0][1]) if candidates else 0.
        shown = read if read and value >= lectores.COMBINED_THRESHOLDS[source] else None
        item = {"puntuacion": value, "fuente": source, **where(*balloon["circle"][:2])}
        if label is None:
            if shown:
                out["sin_referencia"].append(dict(leido=shown, **item))
        elif label == NOT_A_BALLOON:
            if shown:
                out["en_falso"].append(dict(leido=shown, **item))
        elif shown is None:
            out["sin_lectura"].append(dict(numero=label, propuesta=read, **item))
        elif shown != label:
            out["erroneos"].append(dict(numero=label, leido=shown, **item))
    return out


def mixing_problem(folder: Path, config: dict) -> str | None:
    """Por qué no se pueden añadir resultados a `folder` con esta configuración, o None si se puede.

    Una carpeta con resultados de otro lector combinado, o con puntuaciones redondeadas (todas las
    anteriores al 09/11/2026), no se mezcla con resultados nuevos.
    """
    if not (folder / "resultados.json").is_file():
        return None
    try:
        saved = json.loads((folder / "configuracion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if saved.get("puntuaciones") != config["puntuaciones"]:
        return "tiene resultados con puntuaciones redondeadas a 4 decimales (histórico, anterior al 09/11/2026)"
    if saved.get("lector_combinado") != config["lector_combinado"]:
        return f"tiene resultados de otro lector combinado ({saved.get('lector_combinado')})"
    return None


def error_sheet(rgb, balloons, predictions, truth, path: Path, limit: int = 48):
    tiles = []
    for b, candidates, label in zip(balloons, predictions, truth):
        read = lectores.label_of(candidates[0][0]) if candidates else None
        if label in (None, NOT_A_BALLOON) or read == label:
            continue
        x, y, r = b["circle"]
        k = int(r * 1.4)
        crop = rgb[max(0, int(y) - k):int(y) + k, max(0, int(x) - k):int(x) + k][:, :, ::-1]
        if not crop.size:
            continue
        tile = cv2.copyMakeBorder(cv2.resize(crop, (140, 140), interpolation=cv2.INTER_AREA), 0, 22, 0, 0,
                                  cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(tile, f"{label[1:]}>{(read or '-')[1:]}", (3, 157), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 200), 1)
        tiles.append(tile)
        if len(tiles) == limit:
            break
    if tiles:
        while len(tiles) % 8:
            tiles.append(np.full_like(tiles[0], 255))
        cv2.imwrite(str(path), np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))


def sample_sheet(rgb, balloons, predictions, path: Path, count: int = 32,
                 shown=("buscador", "propio-general + desplazados + únicos", "combinado")):
    """Planos sin .icp: muestra repartida de globos con lo que lee cada lector, para revisarla a ojo."""
    tiles = []
    for i in np.linspace(0, len(balloons) - 1, min(count, len(balloons))).astype(int):
        x, y, r = balloons[i]["circle"]
        k = int(r * 1.4)
        crop = rgb[max(0, int(y) - k):int(y) + k, max(0, int(x) - k):int(x) + k][:, :, ::-1]
        if not crop.size:
            continue
        lines = [f"{n[:6]}: {(lectores.label_of(p[i][0][0]) or '-')[1:] if p[i] else '-'}"
                 for n, p in predictions.items() if n in shown]
        tile = cv2.copyMakeBorder(cv2.resize(crop, (150, 150), interpolation=cv2.INTER_AREA), 0, 18 * len(lines), 0, 0,
                                  cv2.BORDER_CONSTANT, value=(255, 255, 255))
        for j, line in enumerate(lines):
            cv2.putText(tile, f"{i} {line}" if j == 0 else line, (3, 164 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, .45,
                        (0, 0, 200), 1)
        tiles.append(tile)
    if tiles:
        while len(tiles) % 8:
            tiles.append(np.full_like(tiles[0], 255))
        cv2.imwrite(str(path), np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", nargs="*", type=int, help="Ids de documento de la biblioteca")
    parser.add_argument("--minimo", type=int, default=1,
                        help="Detecciones para considerar una página sin referencia (con referencia, siempre)")
    parser.add_argument("--recalibrar", action="store_true", help="Volver a ajustar la calibración .icp → página")
    parser.add_argument("--lectores", nargs="*",
                        help="buscador, ppocr-v6-small-digitos, propio, propio-amplio, propio-general")
    parser.add_argument("--grupo", choices=sorted(GROUPS), default="todos",
                        help="desarrollo: piezas con las que se diseña; examen: apartadas hasta el final")
    parser.add_argument("--sin-vectores", action="store_true", help="Leer siempre la imagen, como antes")
    parser.add_argument("--salida", type=Path, default=OUTPUT)
    parser.add_argument("--resumen", nargs=2, type=Path, metavar=("DESARROLLO", "EXAMEN"),
                        help="Resumir dos resultados.json con el umbral fijado en el primero, y salir")
    parser.add_argument("--resumen-salida", type=Path, help="Dónde guardar el resumen (JSON); por defecto, "
                                                           "resumen.json junto al primer resultados.json")
    parser.add_argument("--umbral-imagen", type=float, help="Umbral fijo para los globos de imagen en el ensayo "
                                                            "por fuente (por defecto, el elegido en desarrollo)")
    parser.add_argument("--comparar", nargs=2, type=Path, metavar=("ANTES", "DESPUES"),
                        help="Comparar dos resúmenes por plano y agregado, y salir")
    args = parser.parse_args()
    if args.comparar:
        compare(*args.comparar)
        return
    if args.resumen:
        threshold_summary(*args.resumen, image_threshold=args.umbral_imagen,
                          output=args.resumen_salida or args.resumen[0].parent / "resumen.json")
        return
    args.salida.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(LIBRARY)
    from rapidocr_onnxruntime import RapidOCR
    from entrenar_lector_globos import OwnRecognizer, model_path
    own = {name: OwnRecognizer(model_path(profile)) for name, profile in
           (("propio", "3212"), ("propio-amplio", "amplio"), ("propio-general", "general"))
           if model_path(profile).is_file()}
    readers = {"buscador": RapidOCR(intra_op_num_threads=4, inter_op_num_threads=1)}
    v6 = bench.MODELS / "PP-OCRv6_rec_small.onnx"
    if v6.is_file():
        readers["ppocr-v6-small-digitos"] = bench.ppocr_reader(v6, "digitos", [])
    readers |= {name: bench.ctc_reader(recognizer, "digitos", []) for name, recognizer in own.items()}
    if args.lectores:
        readers = {name: read for name, read in readers.items() if name in args.lectores}
    # Lector propio del visor (ONNX): orienta la página y entra en el combinado.
    recognizer = lectores.own_reader()
    if recognizer is None:
        parser.error(f"Falta el lector propio en ONNX: {lectores.MODELO}")
    results_file = args.salida / "resultados.json"
    results = json.loads(results_file.read_text(encoding="utf-8")) if results_file.is_file() else {}
    calibration = lectores.lee_calibraciones(CALIBRATION)
    # Qué se ha medido y con qué: modelos, umbral, identidad del lector, precisión y opciones.
    config = {
        "fecha": time.strftime("%Y-%m-%d %H:%M"), "lectores": sorted(readers), "grupo": args.grupo,
        "modelos": {name: hashlib.sha256(model_path(profile).read_bytes()).hexdigest()[:16] for name, profile in
                    (("propio", "3212"), ("propio-amplio", "amplio"), ("propio-general", "general")) if name in own},
        "lector_combinado": lectores.reader_id(), "umbrales_combinado": dict(lectores.COMBINED_THRESHOLDS),
        "version_lectores": lectores.VERSION, "puntuaciones": "completas", "minimo": args.minimo,
        "sin_vectores": args.sin_vectores, "calibracion": str(CALIBRATION)}
    problem = mixing_problem(args.salida, config)
    if problem:
        parser.error(f"{args.salida} {problem}. Usa otra carpeta con --salida.")
    (args.salida / "configuracion.json").write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    for doc_id, piece, ruta in drawing_pdfs(con):
        if args.solo and doc_id not in args.solo or GROUPS[args.grupo] and piece[:4] not in GROUPS[args.grupo]:
            continue
        # El .icp puede estar junto a un duplicado exacto del PDF, en otra carpeta.
        candidates = {}
        for path in [ruta] + [r for (r,) in con.execute("SELECT ruta FROM documento WHERE duplicado_de=?", (doc_id,))]:
            candidates |= stamps_near(con, path)
        candidates = {name: stamps for name, stamps in candidates.items() if stamps}
        digests = {}
        for path in [ruta] + [r for (r,) in con.execute("SELECT ruta FROM documento WHERE duplicado_de=?", (doc_id,))]:
            digests |= icp_digests(con, path)
        pdf_digest = hashlib.sha256((EXEMPLES / ruta).read_bytes()).hexdigest()
        visual = visual_reference(pdf_digest)
        with fitz.open(EXEMPLES / ruta) as doc:
            for page in doc:
                start = time.perf_counter()
                if args.sin_vectores:
                    rgb = lectores.page_raster(page)
                    balloons, via = [dict(b, fuente="imagen") for b in lectores.detect_balloons(rgb)], "imagen"
                else:
                    rgb, balloons, via = lectores.balloon_source(EXEMPLES / ruta, page)
                key = f"{doc_id}-p{page.number + 1}"
                referenced = bool(candidates) or bool(visual) or key in NO_BALLOON_PAGES
                if len(balloons) < args.minimo and not referenced:
                    continue
                entry = {"pieza": piece, "ruta": ruta, "pagina": page.number + 1, "px": list(rgb.shape[:2]),
                         "via": via, "globos": len(balloons)}
                if key in NO_BALLOON_PAGES:
                    entry.update(referencia=f"sin globos: {NO_BALLOON_PAGES[key]}", referencias=0)
                elif visual:
                    entry["referencias"] = sum(1 for g in visual["globos"] if g["lectura_visual"])
                elif candidates:  # el .icp más grande, mientras no se calibre cuál es
                    entry["referencias"] = max(len(s) for s in candidates.values())
                if not balloons:
                    # Con referencia, cuenta como página con todos sus globos sin encontrar.
                    entry.update(referencia=entry.get("referencia", "sin detecciones"), emparejados=0, lectores={})
                    results[key] = entry
                    print(f"{key} {piece}: sin detecciones · referencias {entry.get('referencias', 0)}", flush=True)
                    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
                    continue
                turns = lectores.best_rotation(rgb, balloons, recognizer)
                image, moved = lectores.rotate(rgb, balloons, turns) if turns else (rgb, balloons)
                predictions = read_all(image, moved, readers, recognizer)  # mismo orden que `balloons`
                entry.update(giro_antihorario=90 * turns,
                             radio_mediano_px=round(float(np.median([b["circle"][2] for b in balloons])), 1))
                readings = [[lectores.label_of(c[0][0]) if c else None for c in p] for p in predictions.values()]
                # Las referencias se emparejan sobre la página sin girar.
                truth, not_found = None, []
                if key in NO_BALLOON_PAGES:
                    truth = [NOT_A_BALLOON] * len(balloons)
                    entry["emparejados"] = 0
                elif visual:
                    truth, matched = visual_truth(visual, rgb.shape[:2], balloons)
                    entry.update(referencia=f"lectura visual del {visual.get('fecha', '?')}", emparejados=matched)
                elif candidates:
                    stamp_digests = {name: lectores.stamps_digest(s) for name, s in candidates.items()}
                    calibrated = lectores.calibrate(key, balloons, readings, candidates, rgb.shape[:2], calibration,
                                                    args.recalibrar, pdf_digest, digests, stamp_digests)
                    if calibrated:
                        icp, fit = calibrated
                        stamps = candidates[icp]
                        match = lectores.match_stamps(balloons, stamps, fit)
                        truth = [None if j is None else stamps[j]["label"] for j in match]
                        matched = sum(j is not None for j in match)
                        mapped, used = lectores.stamps_on_page(stamps, fit), set(match)
                        not_found = [(s["label"], *mapped[j]) for j, s in enumerate(stamps) if j not in used]
                        entry.update(icp=icp, referencias=len(stamps), ajuste=f"{fit[0]}/{fit[1]}",
                                     emparejados=matched, sellos_sha256=stamp_digests[icp])
                        lectores.guarda_calibraciones(calibration, CALIBRATION)
                    else:
                        entry.update(referencia="calibración .icp fallida", emparejados=0)
                if truth is not None:
                    sources = [b.get("fuente", "imagen") for b in balloons]
                    entry["lectores"] = {name: score(p, truth, sources) for name, p in predictions.items()}
                    if "combinado" in predictions:
                        entry["fallos_combinado"] = failures(balloons, predictions["combinado"], truth, rgb.shape[:2],
                                                             not_found)
                        # Hoja de errores con lo que ofrece el visor: número erróneo o sin lectura («-»).
                        shown = [c if c and c[0][1] >= lectores.COMBINED_THRESHOLDS[s] else []
                                 for c, s in zip(predictions["combinado"], sources)]
                        error_sheet(rgb, balloons, shown, truth, args.salida / f"errores-{key}.png")
                else:
                    entry["lectores"] = {name: {"leidos": sum(bool(c) for c in p)} for name, p in predictions.items()}
                    sample_sheet(image, moved, predictions, args.salida / f"muestra-{key}.png")
                entry["segundos"] = round(time.perf_counter() - start, 1)
                results[key] = entry
                summary = "\n    ".join(f"{n}: " + " ".join(f"{k} {v}" for k, v in s.items() if k != "detalle")
                                       for n, s in entry["lectores"].items())
                source = (f"icp {entry['icp']} ajuste {entry['ajuste']}" if "icp" in entry
                          else entry.get("referencia", "sin referencia"))
                print(f"{key} {piece} {via} {entry['globos']} globos r≈{entry['radio_mediano_px']}px "
                      f"giro {entry['giro_antihorario']}° · {source} · referencias {entry.get('referencias', '-')} "
                      f"· emparejados {entry.get('emparejados', '-')}\n    {summary}", flush=True)
                results_file.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
