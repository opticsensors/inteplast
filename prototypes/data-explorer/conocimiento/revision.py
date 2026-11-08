"""Revisión de enlaces pieza ↔ documento ↔ muestreo en lo que guarda `conocimiento/`.

Solo lee: la biblioteca (solo lectura), hallazgos.jsonl, casos-referencia.jsonl y las auditorías
de aceptación. No corrige nada. Cada comprobación dice qué mira y cuántos casos encuentra; un aviso
es algo que mirar, no un error demostrado. El JSON guarda todos los casos; el Markdown y la pestaña
Revisión solo enseñan los primeros.

    python revision.py            # escribe out/conocimiento/revision.json y revision.md
"""

from __future__ import annotations

import json
import posixpath
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402
from datos import CONOCIMIENTO, MUESTREO, OUT, serie_de  # noqa: E402

MAX_EJEMPLOS = 25  # solo para presentarlos
MARGEN_DIAS = 7  # el mismo margen que cadena_correcciones.py: la fecha del informe es la de emisión


def fecha(texto) -> date | None:
    """Fecha ISO válida; la fecha cero de Excel (1899-12-31, I-304) y anteriores a 2000 no cuentan."""
    try:
        f = date.fromisoformat(str(texto)[:10]) if texto else None
    except ValueError:
        return None
    return f if f and f.year >= 2000 else None


def muestreo_de(nombre: str):
    m = MUESTREO.search(nombre or "")
    return (serie_de(nombre), int(m.group(1))) if m else None


def comprobacion(id_, grupo, titulo, que, casos, total=None, nivel=None, nota=""):
    casos = list(casos)
    if nivel is None:
        nivel = "ok" if not casos else "aviso"
    return {"id": id_, "grupo": grupo, "titulo": titulo, "que": que, "n": len(casos), "total": total,
            "nivel": nivel, "casos": casos, "nota": nota}


def revisar() -> dict:
    c = datos.con()
    codigos = {r[0] for r in c.execute("SELECT DISTINCT codigo FROM documento WHERE codigo IS NOT NULL")}
    doc_codigo = {r[0]: (r[1], r[2], r[3]) for r in c.execute("SELECT id, codigo, nombre, ruta FROM documento")}
    total_docs = len(doc_codigo)
    res = []

    # ---------------------------------------------------------------- pieza
    sin = [{"id": i, "ruta": r} for i, (cod, _, r) in doc_codigo.items() if cod is None]
    res.append(comprobacion("P1", "pieza", "Documentos sin pieza",
                            "documento.codigo vacío: el fichero no está dentro de la carpeta de ninguna pieza.",
                            sin, total_docs, nivel="info" if len(sin) <= 1 else None,
                            nota="El único esperado es el Readme de 5- Anclajes, que no trae piezas."))

    varios = []
    for cod in sorted(codigos):
        feats = c.execute("SELECT feature, pieza, count(*) FROM documento WHERE codigo=? GROUP BY 1, 2", (cod,)).fetchall()
        if len(feats) > 1:
            varios.append({"pieza": cod, "features": "; ".join(f"{f} ({p}): {n} ficheros" for f, p, n in feats)})
    res.append(comprobacion("P2", "pieza", "Piezas presentes en varios features",
                            "Mismo código de pieza bajo más de un feature. Lo normal es que la copia solo traiga un Readme.",
                            varios, len(codigos), nivel="info"))

    patron = re.compile(r"(?<!\d)(" + "|".join(sorted(codigos)) + r")(?!\d)")
    cita = []
    for i, (cod, nombre, ruta) in doc_codigo.items():
        if not cod:
            continue
        otros = sorted(set(patron.findall(nombre)) - {cod})
        if otros and cod not in nombre:
            cita.append({"id": i, "pieza": cod, "cita": ",".join(otros), "ruta": ruta})
    res.append(comprobacion("P3", "pieza", "Nombre de fichero que cita otra pieza y no la propia",
                            "El nombre contiene el código de otra de las piezas y no el de la carpeta donde está. "
                            "Puede ser una pieza hermana, un número de otra cosa o un fichero mal archivado (p. ej. I-702).",
                            cita, total_docs))

    mal = c.execute("SELECT m.documento_id, m.pieza, d.codigo, d.ruta, count(*) FROM medida_cmm m JOIN documento d"
                    " ON d.id=m.documento_id WHERE d.codigo IS NOT m.pieza GROUP BY 1").fetchall()
    res.append(comprobacion("P4", "pieza", "medida_cmm: pieza distinta de la del documento",
                            "medida_cmm.pieza frente al código de la carpeta del CSV.",
                            [{"id": a, "pieza_medida": b, "pieza_doc": cc, "ruta": r, "filas": n} for a, b, cc, r, n in mal],
                            c.execute("SELECT count(DISTINCT documento_id) FROM medida_cmm").fetchone()[0]))

    for tabla, idc in (("perfil_ppap", "P5"), ("perfil_correccion", "P6")):
        filas = c.execute(f"SELECT t.documento_id, t.pieza, d.pieza, d.ruta FROM {tabla} t JOIN documento d ON d.id=t.documento_id"
                          " WHERE t.pieza IS NOT d.pieza").fetchall()
        total = c.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
        res.append(comprobacion(idc, "pieza", f"{tabla}: pieza distinta de la del documento",
                                f"{tabla}.pieza frente a la carpeta de pieza del documento.",
                                [{"id": a, "tabla": b, "documento": cc, "ruta": r} for a, b, cc, r in filas], total))

    refs = []
    ppap = c.execute("SELECT p.documento_id, p.hoja, p.metadatos, d.codigo, d.nombre, d.ruta FROM perfil_ppap p"
                     " JOIN documento d ON d.id=p.documento_id").fetchall()
    for doc, hoja, meta, cod, nombre, ruta in ppap:
        ref = (json.loads(meta or "{}") or {}).get("ppap_ref")
        m = re.match(r"\s*(\d{4})", str(ref or ""))
        if m and m.group(1) != cod:
            refs.append({"id": doc, "hoja": hoja, "pieza": cod, "ppap_ref": ref, "ruta": ruta})
    res.append(comprobacion("P7", "pieza", "Referencia PPAP del cajetín con otra pieza",
                            "El campo ppap_ref de la cabecera del informe empieza por un código distinto de la carpeta. "
                            "Suele delatar plantillas heredadas de otra pieza.", refs, len(ppap),
                            nota="Por pieza: " + ", ".join(f"{k}: {v}" for k, v in sorted(Counter(
                                f"{x['pieza']}→{str(x['ppap_ref'])[:4]}" for x in refs).items()))))

    cad = []
    filas = c.execute("SELECT pieza, cota, documento_id, origen_documento_id, validacion_documento_id FROM cadena_correccion").fetchall()
    for pieza, cota, d0, d1, d2 in filas:
        for papel, d in (("corrección", d0), ("origen", d1), ("validación", d2)):
            if d is not None and doc_codigo.get(d, (None,))[0] != pieza:
                cad.append({"pieza": pieza, "cota": cota, "papel": papel, "documento": d,
                            "pieza_doc": doc_codigo.get(d, (None,))[0], "ruta": doc_codigo.get(d, (None, None, None))[2]})
    res.append(comprobacion("P8", "pieza", "cadena_correccion: documentos de otra pieza",
                            "El PPTX de corrección y los informes de origen y validación deben ser de la misma pieza que la cadena.",
                            cad, len(filas)))

    icp = c.execute("SELECT d.id, d.codigo, d.ruta, count(g.sello), sum(g.x1 IS NULL), sum(g.etiqueta IS NULL)"
                    " FROM documento d LEFT JOIN globo g ON g.documento_id=d.id WHERE d.ext='icp' GROUP BY d.id").fetchall()
    rotos = [{"id": i, "pieza": cod, "ruta": r, "sellos": n, "sin_posicion": a or 0, "sin_numero": b or 0}
             for i, cod, r, n, a, b in icp if (a or 0) or (b or 0) or not n]
    res.append(comprobacion("P9", "pieza", ".icp con globos sin posición o sin número",
                            "Sellos desalineados (coordenadas nulas) o sin número visible en el .prf.", rotos, len(icp), nivel="info"))
    pdf_dirs = {posixpath.dirname(p["ruta"]) for p in datos.planos()}
    sueltos = [{"id": i, "ruta": r} for i, _, r, *_ in icp if posixpath.dirname(r) not in pdf_dirs]
    res.append(comprobacion("P10", "pieza", ".icp sin plano PDF en su carpeta",
                            "No hay un PDF de plano (de la lista de planos) junto al .icp.", sueltos, len(icp), nivel="info",
                            nota="Puede estar en la carpeta de una copia idéntica; el visor de planos también busca ahí."))

    sin_plano = sorted(codigos - {p["codigo"] for p in datos.planos()})
    res.append(comprobacion("P11", "pieza", "Piezas sin PDF de plano",
                            "Piezas sin ningún PDF en 1- 2D y 3D pieza ni carpetas de globos.",
                            [{"pieza": p} for p in sin_plano], len(codigos)))

    hz = []
    for h in datos.hallazgos():
        for p in datos.piezas_de(h.get("pieza")):
            if p not in codigos:
                hz.append({"hallazgo": h.get("id"), "pieza": p})
    res.append(comprobacion("P12", "pieza", "hallazgos.jsonl: piezas que no existen en la biblioteca",
                            "Cada código del campo pieza debe ser una de las piezas inventariadas.", hz, len(datos.hallazgos()),
                            nivel="info" if all(x["pieza"] == "3247" for x in hz) else None,
                            nota="3247 es el nombre de un libro guardado en la carpeta del 3288 (I-104), no una pieza de Exemples."))

    cr = []
    for x in datos.casos():
        f = c.execute("SELECT id, codigo, sha256 FROM documento WHERE ruta=?", (x.get("ruta"),)).fetchone()
        if not f:
            cr.append({"caso": x["id"], "problema": "ruta no inventariada", "ruta": x.get("ruta")})
        elif str(x.get("pieza")) != f["codigo"]:
            cr.append({"caso": x["id"], "problema": f"pieza {x.get('pieza')} ≠ carpeta {f['codigo']}", "ruta": x.get("ruta")})
        elif x.get("sha256") and x["sha256"] != f["sha256"]:
            cr.append({"caso": x["id"], "problema": "SHA-256 distinto del inventariado", "ruta": x.get("ruta")})
    res.append(comprobacion("P13", "pieza", "casos-referencia.jsonl: ruta, pieza y huella",
                            "Cada caso debe apuntar a un documento inventariado de su pieza y con la misma huella.",
                            cr, len(datos.casos())))

    au, n_au = [], 0
    for f in sorted((CONOCIMIENTO / "datos" / "aceptacion").glob("*-auditoria.jsonl")):
        esperado = f.name.split("-")[0]
        for linea in f.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            n_au += 1
            x = json.loads(linea)
            real = doc_codigo.get(x.get("id"), (None,))[0] or "sin_pieza"
            if str(x.get("codigo")) != esperado or real != esperado:
                au.append({"fichero": f.name, "id": x.get("id"), "codigo_fila": x.get("codigo"), "codigo_biblioteca": real,
                           "ruta": x.get("ruta")})
    res.append(comprobacion("P14", "pieza", "Auditorías de aceptación: pieza del fichero, de la fila y de la biblioteca",
                            "Cada fila de <pieza>-auditoria.jsonl debe ser de esa pieza también en la biblioteca actual.", au, n_au))

    # ---------------------------------------------------------------- muestreo
    informes = c.execute(
        "SELECT DISTINCT d.id, d.codigo, d.nombre, d.ruta, d.sha256 FROM lectura_dr l JOIN documento d ON d.id=l.documento_id"
        " WHERE d.carpeta_norm='metrologia' AND l.papel='informe'").fetchall()
    sin_m = [{"id": i, "pieza": cod, "ruta": r} for i, cod, n, r, _ in informes if not muestreo_de(n)]
    res.append(comprobacion("M1", "muestreo", "Informes de metrología sin muestreo en el nombre",
                            "Hojas DR con papel «informe» cuyo nombre no lleva intern.NN / int.NN: sus medidas no se pueden "
                            "situar en la historia del molde por el nombre.", sin_m, len(informes)))

    carpeta = []
    for i, cod, n, r, _ in informes:
        propio = muestreo_de(n)
        padre = muestreo_de(posixpath.basename(posixpath.dirname(r)))
        if propio and padre and propio[1] != padre[1]:
            carpeta.append({"id": i, "pieza": cod, "nombre": f"intern.{propio[1]:02d}", "carpeta": f"intern.{padre[1]:02d}", "ruta": r})
    res.append(comprobacion("M2", "muestreo", "Muestreo del nombre distinto del de la carpeta",
                            "El fichero dice un muestreo y su carpeta otro.", carpeta, len(informes)))

    ref_m, con_ref = [], 0
    for doc, hoja, meta, cod, nombre, ruta in ppap:
        ref = (json.loads(meta or "{}") or {}).get("ppap_ref")
        a, b = muestreo_de(nombre), muestreo_de(str(ref or ""))
        if a and b:
            con_ref += 1
            if a[1] != b[1]:
                ref_m.append({"id": doc, "hoja": hoja, "pieza": cod, "nombre": nombre, "ppap_ref": ref})
    res.append(comprobacion("M3", "muestreo", "Muestreo del nombre distinto del de la cabecera PPAP",
                            "intern.NN del nombre del fichero frente al de ppap_ref en la cabecera del informe. "
                            "Indica cabeceras heredadas de un informe anterior (I-001) o un nombre mal puesto.",
                            ref_m, con_ref))

    por = defaultdict(lambda: defaultdict(set))
    for i, cod, n, r, sha in informes:
        m = muestreo_de(n)
        if m:
            por[cod][m].add(sha)
    copias = [{"pieza": cod, "muestreo": f"serie {s} intern.{k:02d}", "versiones": len(shas)}
              for cod, ms in sorted(por.items()) for (s, k), shas in sorted(ms.items()) if len(shas) > 1]
    res.append(comprobacion("M4", "muestreo", "Muestreos con varias versiones distintas del informe",
                            "Mismo muestreo (pieza, serie, número) en ficheros con contenido distinto. Hay que elegir cuál "
                            "vale (I-603: versiones con valores cambiados).", copias, sum(len(v) for v in por.values()), nivel="info"))

    huecos = []
    for cod, ms in sorted(por.items()):
        for serie in sorted({s for s, _ in ms}):
            nums = sorted(k for s, k in ms if s == serie)
            faltan = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
            if faltan:
                huecos.append({"pieza": cod, "serie": serie, "hay": ",".join(map(str, nums)), "faltan": ",".join(map(str, faltan))})
    res.append(comprobacion("M5", "muestreo", "Huecos en la numeración de muestreos",
                            "Números de intern.NN que faltan entre el primero y el último de cada pieza y serie. "
                            "Puede ser un muestreo no entregado o no medido por DR.", huecos, len(por), nivel="info"))

    fechas = defaultdict(lambda: defaultdict(set))
    for doc, hoja, meta, cod, nombre, ruta in ppap:
        f = fecha((json.loads(meta or "{}") or {}).get("report_date"))
        m = muestreo_de(nombre)
        if f and m:
            fechas[cod][m].add(f)
    cero = []
    for doc, hoja, meta, cod, nombre, ruta in ppap:
        bruto = (json.loads(meta or "{}") or {}).get("report_date")
        if bruto and fecha(bruto) is None:
            cero.append({"id": doc, "hoja": hoja, "pieza": cod, "report_date": bruto, "nombre": nombre})
    res.append(comprobacion("M12", "muestreo", "Cabeceras con fecha de informe no válida",
                            "report_date con la fecha cero de Excel (1899-12-31), texto u otra cosa que no es fecha. "
                            "No cuentan en M6 ni M7.", cero, len(ppap), nivel="info",
                            nota="Ya documentado como I-304 en incongruencias.md."))
    disp, orden = [], []
    for cod, ms in sorted(fechas.items()):
        anterior = None
        for clave in sorted(ms):
            fs = sorted(ms[clave])
            if (fs[-1] - fs[0]).days > 31:
                disp.append({"pieza": cod, "muestreo": f"serie {clave[0]} intern.{clave[1]:02d}", "desde": str(fs[0]),
                             "hasta": str(fs[-1])})
            if anterior and anterior[0] == clave[0] and fs[-1] < anterior[2] - timedelta(days=MARGEN_DIAS):
                orden.append({"pieza": cod, "muestreo": f"intern.{clave[1]:02d} ({fs[-1]})",
                              "anterior": f"intern.{anterior[1]:02d} ({anterior[2]})"})
            anterior = (clave[0], clave[1], fs[0])
    res.append(comprobacion("M6", "muestreo", "Fechas de informe muy dispersas dentro de un muestreo",
                            "Copias del mismo muestreo con report_date separadas más de 31 días: no se sabe qué fecha tiene el muestreo.",
                            disp, sum(len(v) for v in fechas.values())))
    res.append(comprobacion("M7", "muestreo", "Muestreo con fecha anterior al muestreo previo",
                            f"intern.N+1 con todas sus fechas más de {MARGEN_DIAS} días antes que la primera de intern.N "
                            "(misma pieza y serie).", orden, sum(len(v) for v in fechas.values())))

    cad_m, cad_f, cad_o = [], [], []
    filas = c.execute("SELECT pieza, cota, documento_id, fecha_correccion, origen_muestreo, origen_documento_id, origen_fecha,"
                      " validacion_muestreo, validacion_documento_id, validacion_fecha FROM cadena_correccion").fetchall()
    for f in filas:
        for papel, num, doc in (("origen", f["origen_muestreo"], f["origen_documento_id"]),
                                ("validación", f["validacion_muestreo"], f["validacion_documento_id"])):
            if num is not None and doc is not None:
                m = muestreo_de(doc_codigo.get(doc, (None, ""))[1])
                if m and m[1] != num:
                    cad_m.append({"pieza": f["pieza"], "cota": f["cota"], "papel": papel, "muestreo": num,
                                  "nombre_documento": doc_codigo[doc][1]})
        if f["origen_muestreo"] is not None and f["validacion_muestreo"] is not None and f["validacion_muestreo"] <= f["origen_muestreo"]:
            cad_o.append({"pieza": f["pieza"], "cota": f["cota"], "origen": f["origen_muestreo"], "validacion": f["validacion_muestreo"]})
        fc, fo, fv = fecha(f["fecha_correccion"]), fecha(f["origen_fecha"]), fecha(f["validacion_fecha"])
        if fc and fo and fo > fc + timedelta(days=MARGEN_DIAS):
            cad_f.append({"pieza": f["pieza"], "cota": f["cota"], "problema": "origen posterior a la corrección",
                          "correccion": str(fc), "origen": str(fo)})
        if fc and fv and fv < fc:
            cad_f.append({"pieza": f["pieza"], "cota": f["cota"], "problema": "validación anterior a la corrección",
                          "correccion": str(fc), "validacion": str(fv)})
    res.append(comprobacion("M8", "muestreo", "cadena_correccion: muestreo distinto del nombre de su informe",
                            "origen_muestreo / validacion_muestreo frente al intern.NN del documento enlazado.", cad_m, len(filas)))
    res.append(comprobacion("M9", "muestreo", "cadena_correccion: validación no posterior al origen",
                            "El muestreo de validación debe ser mayor que el de origen.", cad_o, len(filas)))
    agrupado = Counter((x["pieza"], x["problema"]) for x in cad_f)
    res.append(comprobacion("M10", "muestreo", "cadena_correccion: fechas incoherentes con la corrección",
                            f"Origen más de {MARGEN_DIAS} días después de la fecha de la corrección, o validación antes de ella. "
                            "Por pieza (cada cota cuenta una vez):",
                            [{"pieza": p, "problema": pr, "cotas": n} for (p, pr), n in sorted(agrupado.items())], len(filas),
                            nota=f"{len(cad_f)} cotas en total. Ejemplos por cota en revision.json."))
    res[-1]["detalle"] = cad_f[:200]

    cmm = c.execute("SELECT DISTINCT m.documento_id, m.muestreo, d.nombre, d.ruta FROM medida_cmm m JOIN documento d ON d.id=m.documento_id").fetchall()
    cm = []
    for doc, num, nombre, ruta in cmm:
        m = muestreo_de(nombre) or muestreo_de(posixpath.dirname(ruta))
        if not m or int(num) != m[1]:
            cm.append({"id": doc, "muestreo": num, "nombre": nombre, "ruta": ruta})
    res.append(comprobacion("M11", "muestreo", "medida_cmm: muestreo distinto del nombre o la carpeta del CSV",
                            "medida_cmm.muestreo frente al intern.NN del nombre o, si no lo trae, de la ruta.", cm, len(cmm)))

    varias = defaultdict(list)
    for cod, cota, nominal, n, hojas in c.execute(
            "SELECT d.codigo, m.cota, m.nominal, count(*), group_concat(DISTINCT m.hoja) FROM medida_dr m"
            " JOIN documento d ON d.id=m.documento_id WHERE m.nominal IS NOT NULL AND m.marca IS NULL GROUP BY 1, 2, 3"):
        varias[(cod, cota)].append((nominal, n, hojas))
    ambiguas = [{"pieza": cod, "cota": cota, "nominales": " · ".join(f"{nom:g} ({n} medidas)" for nom, n, _ in sorted(v, key=lambda x: -x[1])[:4]),
                 "hojas": "; ".join(sorted({h for *_, hs in v for h in (hs or "").split(",")}))[:160]}
                for (cod, cota), v in sorted(varias.items(), key=lambda kv: (kv[0][0], datos.clave_cota(kv[0][1]))) if len(v) > 1]
    por_pieza = Counter(x["pieza"] for x in ambiguas)
    res.append(comprobacion("M13", "muestreo", "Misma cota con varias nominales dentro de una pieza",
                            "medida_dr: un mismo número de cota de la misma pieza aparece con nominales distintas. Puede ser "
                            "otra hoja o variante del plano, una revisión que cambió la cota o una fila mal asignada; "
                            "al seguir la cota entre muestreos hay que separar las nominales.", ambiguas, len(varias),
                            nota="Por pieza: " + ", ".join(f"{k}: {v}" for k, v in sorted(por_pieza.items()))))

    resumen = Counter(r["nivel"] for r in res)
    return {"comprobaciones": res, "resumen": dict(resumen), "biblioteca": str(datos.BD)}


def markdown(r: dict) -> str:
    lineas = ["# Revisión de enlaces pieza y muestreo", "",
              f"Generado por `prototypes/data-explorer/conocimiento/revision.py` sobre `{Path(r['biblioteca']).name}`. "
              "Solo lectura; un aviso es algo que mirar, no un error demostrado.", "",
              "| Id | Comprobación | Casos | De | Nivel |", "|---|---|---|---|---|"]
    for x in r["comprobaciones"]:
        lineas.append(f"| {x['id']} | {x['titulo']} | {x['n']} | {x['total'] if x['total'] is not None else ''} | {x['nivel']} |")
    for x in r["comprobaciones"]:
        lineas += ["", f"## {x['id']} · {x['titulo']}", "", x["que"] + (" " + x["nota"] if x["nota"] else ""), ""]
        if x["casos"]:
            claves = list(x["casos"][0])
            lineas += ["| " + " | ".join(claves) + " |", "|" + "---|" * len(claves)]
            for e in x["casos"][:MAX_EJEMPLOS]:
                lineas.append("| " + " | ".join(str(e.get(k, "")).replace("|", "\\|") for k in claves) + " |")
            if x["n"] > MAX_EJEMPLOS:
                lineas.append(f"\nSe muestran {MAX_EJEMPLOS} de {x['n']}; la lista completa está en revision.json.")
        else:
            lineas.append("Sin casos.")
    return "\n".join(lineas) + "\n"


def main() -> None:
    r = revisar()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "revision.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (OUT / "revision.md").write_text(markdown(r), encoding="utf-8")
    for x in r["comprobaciones"]:
        print(f"{x['id']:4} {x['nivel']:5} {x['n']:5} / {x['total'] if x['total'] is not None else '-':<6} {x['titulo']}")
    print(OUT / "revision.md")


if __name__ == "__main__":
    main()
