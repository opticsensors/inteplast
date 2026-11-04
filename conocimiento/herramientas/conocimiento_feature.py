"""Consulta y exportación revisable de la fuente única hallazgos.jsonl.

No conecta con la app. La exportación usa referencias naturales; el importador
futuro deberá resolver feature_id/characteristic_id y respetar revisión/ámbito.
"""
import argparse
import json
from pathlib import Path

FUENTE = Path(__file__).resolve().parent.parent / "hallazgos.jsonl"
TIPOS = {"leccion", "warning", "vinculo_feature_cota"}
ESTADOS = {"borrador", "revisado_documentalmente", "validado_por_INTEPLAST"}


def validar(registro):
    if registro.get("tipo") not in TIPOS:
        return []
    errores = []
    for campo in ("titulo", "aplica_a", "cotas", "validacion", "fuente_validacion"):
        if campo not in registro:
            errores.append(f"falta {campo}")
    if registro.get("validacion") not in ESTADOS:
        errores.append("validacion desconocida")
    if registro.get("validacion") == "validado_por_INTEPLAST" and not registro.get("fuente_validacion"):
        errores.append("validación INTEPLAST sin fuente")
    ambito = registro.get("aplica_a", {})
    if ambito.get("ambito") not in {"feature", "pieza"} or not ambito.get("feature"):
        errores.append("aplica_a requiere ámbito y feature")
    if ambito.get("ambito") == "pieza" and not ambito.get("piezas"):
        errores.append("ámbito pieza sin piezas")
    if not registro.get("evidencia"):
        errores.append("sin evidencia documental")
    for cota in registro.get("cotas", []):
        if not all(k in cota for k in ("pieza", "cota", "revision", "estado")):
            errores.append("cota sin pieza/código/revisión/estado")
        estados_cota = {"confirmada_documentalmente", "propuesta"}
        if registro.get("tipo") in {"leccion", "warning"}:
            estados_cota.add("contexto_documental")
        if cota.get("estado") not in estados_cota:
            errores.append("estado de vínculo desconocido")
    return [f"{registro.get('id')}: {error}" for error in errores]


def seleccionar(registros, feature=None, pieza=None, tipo=None):
    return [r for r in registros if r.get("tipo") in TIPOS
            and (not feature or r["aplica_a"]["feature"].casefold() == feature.casefold())
            and (not pieza or pieza in r["aplica_a"].get("piezas", []))
            and (not tipo or r["tipo"] == tipo)]


def exportar(registros, borradores=False, revisados=False):
    notas, vinculos = [], []
    for r in registros:
        errores = validar(r)
        if errores:
            raise ValueError("; ".join(errores))
        admitidos = {"validado_por_INTEPLAST"}
        if revisados:
            admitidos.add("revisado_documentalmente")
        if not borradores and r["validacion"] not in admitidos:
            continue
        contexto = dict(id_origen=r["id"], aplica_a=r["aplica_a"], validacion=r["validacion"],
                        fuente_validacion=r["fuente_validacion"], evidencia=r["evidencia"], cotas=r["cotas"])
        if r["tipo"] in {"leccion", "warning"}:
            notas.append({**contexto, "note": dict(kind="lesson" if r["tipo"] == "leccion" else "warning",
                                                   title=r["titulo"], body=r["afirmacion"])})
        if r["tipo"] == "vinculo_feature_cota":
            for cota in r["cotas"]:
                vinculos.append({**contexto, "characteristic_ref": cota,
                                 "link": {"role": cota.get("role", "primary")}})
    return dict(formato="inteplast-revision-1", carga_automatica=False,
                resolver_ids_y_revision=True, incluye_borradores=borradores, incluye_revision_documental=revisados,
                FeatureNote=notas, FeatureCharacteristicLink=vinculos)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feature")
    p.add_argument("--pieza")
    p.add_argument("--tipo", choices=sorted(TIPOS))
    p.add_argument("--exportar", action="store_true")
    p.add_argument("--borradores", action="store_true", help="exportación solo para revisar, no para cargar")
    p.add_argument("--revisados", action="store_true", help="incluye contraste documental sin atribuir aprobación de INTEPLAST")
    args = p.parse_args()
    registros = [json.loads(s) for s in FUENTE.read_text(encoding="utf-8").splitlines() if s.strip()]
    seleccion = seleccionar(registros, args.feature, args.pieza, args.tipo)
    errores = [e for r in seleccion for e in validar(r)]
    if errores:
        p.error("; ".join(errores))
    salida = exportar(seleccion, args.borradores, args.revisados) if args.exportar else seleccion
    print(json.dumps(salida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
