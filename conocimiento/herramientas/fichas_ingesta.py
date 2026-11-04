"""Inventario reproducible y borradores de contratos de ingesta.

Lee biblioteca en modo ro. --crear solo crea fichas que no existen; nunca pisa
la revisión manual. Los recuentos de biblioteca NO certifican el backend.
"""
import argparse
import json
import sqlite3
from pathlib import Path

from comun import BD, CONOCIMIENTO
from identidad_piezas import CAMPOS, recoger

CONSULTAS = {
    "documentos": "SELECT count(*) FROM documento WHERE codigo=:pieza",
    "duplicados_exactos": "SELECT count(*) FROM documento WHERE codigo=:pieza AND estado='duplicado'",
    "hojas_ppap": "SELECT count(*) FROM perfil_ppap p JOIN documento d ON d.id=p.documento_id WHERE d.codigo=:pieza",
    "libros_ppap": "SELECT count(DISTINCT p.documento_id) FROM perfil_ppap p JOIN documento d ON d.id=p.documento_id WHERE d.codigo=:pieza",
    "valores_dr": "SELECT count(*) FROM medida_dr m JOIN documento d ON d.id=m.documento_id WHERE d.codigo=:pieza",
    "cotas_dr": "SELECT count(DISTINCT m.cota) FROM medida_dr m JOIN documento d ON d.id=m.documento_id WHERE d.codigo=:pieza",
    "celdas_rand": "SELECT count(*) FROM celda_aleatoria a JOIN documento d ON d.id=a.documento_id WHERE d.codigo=:pieza",
    "libros_rand": "SELECT count(DISTINCT a.documento_id) FROM celda_aleatoria a JOIN documento d ON d.id=a.documento_id WHERE d.codigo=:pieza",
    "diapositivas_perfiladas": "SELECT count(*) FROM perfil_correccion WHERE pieza=:pieza",
    "filas_cadena": "SELECT count(*) FROM cadena_correccion WHERE pieza=:pieza",
    "cmm": "SELECT count(*) FROM medida_cmm WHERE pieza=:pieza",
    "contorno": "SELECT count(*) FROM medida_contorno WHERE pieza=:pieza",
}
PARTICULAR = {
    "2820": "Solo plano y STEP; cero medidas no significa pieza no válida. No fabricar muestreos.",
    "3051": "XLS sin CSV CMM. N880 cambia de Ø3,8 a Ø4 en intern.11. I-203: hoja copiada entre informes; no generar nuevas muestras por repetición.",
    "3056": "Los planes contienen imágenes (I-602): OCR/lectura visual pendiente. No aceptar títulos extraídos como acciones completas.",
    "3167": "Piloto de ficha: PPAP cliente XLSM (B=cota, E=nominal, F/G=tolerancias, J:N=muestras), internos DR, SPC #P# y Cpk generator. I-603: conservar ambas versiones Inf_04 sin escoger por nombre. Los 328 SPC de Estudis Estadístics coinciden con salidas generadas; no son mediciones (I-003).",
    "3168": "Firma PDF en intern.13_6injecton points.xls. SPC sin fórmula de origen: sin_confirmar. No convertir constantes en mediciones por ausencia de RAND. I-007: tolerancias diferentes por copia.",
    "3174": "Plan 2 incluye diapositivas del 3186 (I-309); excluirlas de acciones propias. I-007: cota 504 ±0,15/±0,07 según copia. RAND en hojas copia. Método rev06 vincula N712.",
    "3186": "Plano archivado del 3174 (I-301), no propio. Cota 1604 repetida; corregir identidad de plantillas 3247. Conservar condición clipada/libre.",
    "3195": "I-308: una fila 2360 tiene nominal/contexto de 2500.1. I-307: carpeta N6 usa acciones 5.x. No deducir orden solo de la numeración.",
    "3197": "CSV bilingüe, condiciones de temperatura/presión/ciclo en la ruta; distinguir comparativas totes y puntos SYM-POINT. No colapsar C5bis/C5.1. Separar GX/LP y revisiones de tolerancia N230.",
    "3202": "I-001/I-006: bloques heredados y copias internas/cliente discordantes. Métodos V02–V05, GG/GN, altura y útil; no mezclar medidas por compartir cota.",
    "3205": "PPAP castellano; columnas de corrección no son medidas. Conservar loops 4 y 11 y las dos fechas del último. I-402: algunas diapositivas pertenecen al 3206.",
    "3206": "RAND en DR_(customer) (2), cabeceras heredadas 3247. Variantes de plan con magnitudes distintas: conservar versión, no elegir por fecha del fichero.",
    "3212": "CSV prioritarios: 16 × 211 = 3.376 evaluaciones; 144 PA/PB. ID CMM, no solo rótulo N170. Corregir signos B2/B4 conservando original. POINT/GLOBAL → N165; no confundir GX con LP máximo. XLS parciales I-001.",
    "3214": "PPAP sin CMM; no forzar reglas del piloto. Carpeta Tetones remite a Nervios: resolver referencia sin duplicar documentos.",
    "3218": "184 hojas/62 libros con PPAP 3281, pero identidad propia 3218. RAND muestras 2–5: conservar muestra origen. Plano del 3174 y plantillas 3247 no identifican esta pieza. N2705 también es posición del clip.",
    "3226": "Datos mínimos sin perfiles PPAP de la biblioteca. Cero medidas reconocidas no demuestra ausencia en todos los originales; revisar alcance antes de aceptar.",
    "3233": "32 columnas de cavidad no prueban 32 cavidades físicas. PPAP 100% (CUSTOMER), SPC #P#, MSA y métodos DOC. Plan genérico P3033: no importarlo como corrección propia.",
    "3237": "PPAP cliente XLSM, #P# y RAND. Cuatro SPC coinciden con generador (generado); 3237-20 sin generador original (sin_confirmar). Separar cotas de Cmk/Cpk.",
    "3238": "PPAP cliente XLSM con RAND. Condicionamiento por humedad y discrepancias CMM/CT. Resultados de útiles no son medidas de la pieza. No aceptar plantilla genérica P3033.",
    "3288": "Referencia cliente 508008 en método; 509131 es del 3247. I-101: cavidades físicas sin resolver, no inferirlas de 20 columnas. Cota 80 del conjunto nivel 2 no equivale a BASE rev1. Ceros con nominal no cero: sin_confirmar.",
    "3309": "DR contiene Part Ref. ITP 733090000 y Part Number/Drawing No. GF991-53540. Separar copias de Int_03/04 y cotas acopladas. N15 requiere útil y pieza clipada.",
}


def informe(con):
    return {codigo: {clave: con.execute(sql, {"pieza": codigo}).fetchone()[0]
                     for clave, sql in CONSULTAS.items()}
            for codigo, in con.execute("SELECT DISTINCT codigo FROM documento WHERE codigo IS NOT NULL ORDER BY codigo")}


def ficha(con, codigo, cifras, identidad, casos, hallazgos):
    propios = identidad[codigo]
    campos = {k: propios["campos"][k].most_common(1)[0][0] if propios["campos"][k] else "no consta"
              for k, _ in CAMPOS}
    rutas = [r[0] or "Raíz / referencias Readme" for r in con.execute("SELECT DISTINCT carpeta FROM documento WHERE codigo=? ORDER BY carpeta", (codigo,))]
    extensiones = con.execute("SELECT ext,count(*) FROM documento WHERE codigo=? GROUP BY ext ORDER BY ext", (codigo,)).fetchall()
    hojas = con.execute("SELECT DISTINCT p.hoja FROM perfil_ppap p JOIN documento d ON d.id=p.documento_id WHERE d.codigo=? ORDER BY p.hoja", (codigo,)).fetchall()
    referencias = [r for r in casos if r["pieza"] == codigo]
    notas = [r["id"] for r in hallazgos if r.get("tipo") in {"warning", "leccion", "vinculo_feature_cota"}
             and codigo in r.get("aplica_a", {}).get("piezas", [])]
    problemas = [r["id"] for r in hallazgos if r["id"].startswith("I-") and (r.get("pieza") == "*" or codigo in r.get("pieza", "").split(","))]
    lineas = [f"# Ficha de ingesta · {codigo}", "", "> Borrador del 02/11/2026. Revisión humana pendiente; no autoriza carga en la app.",
              "> Inventario reproducible ≠ número de medidas aceptadas. Revisar este contrato antes de generalizar el lector.", "",
              "## Respuesta rápida", "", PARTICULAR[codigo], "",
              "## 1. Identidad", "", "Valores propios del agregado revisado de [identidad-piezas.md](../identidad-piezas.md):", "",
              *[f"- {k}: `{v}`." for k, v in campos.items()],
              "", "Cavidades reales: confirmar en plano/método; el agregado de columnas no es una prueba del molde.",
              "La revisión de cada resultado se conserva por informe; no se hereda la revisión mayoritaria de esta ficha.", "",
              "## 2. Carpetas y variantes", "", *[f"- `{r}`" for r in rutas], "",
              "Resolver Readme que remiten a otras carpetas; no duplicar originales por referencias ni por copias exactas.", "",
              "## 3. Formatos de medida", "", "Inventario por extensión: " + ", ".join(f"{e}: {n}" for e, n in extensiones) + ".", "",
              "Hojas perfiladas: " + (", ".join(f"`{h}`" for h, in hojas) or "ninguna") + ".", "",
              "Reglas de lectura: [formatos-parsing.md](../formatos-parsing.md). Las columnas se detectan por etiqueta; no asumir las del 3212.", "",
              "## 4. Identidad de cada resultado", "",
              "Clave: pieza + revisión de plano + informe/copia + hoja + muestreo + cavidad + muestra + elemento + evaluación + unidad.",
              "Conservar fichero, SHA-256, celda/línea/página y valor original. Un contexto desconocido queda explícitamente pendiente; no fusionarlo por N-number.", "",
              "## 5. Condiciones de medida", "",
              "Conservar libre/clipada, humedad/acondicionamiento, equipo, temperatura, presión, altura y útil cuando consten. Ausencia ≠ condiciones iguales.",
              "Revisar método y condiciones antes de comparar series; particularidades en la respuesta rápida.", "",
              "## 6. Correcciones", "",
              "Consultar `rag.py exacto cadena --pieza " + codigo + "`. Conservar plan, revisión, acción, origen/validación y fuente de fecha.",
              "Una fecha del nombre, un OK o un plan no prueban ejecución. Cotas solo en imágenes requieren lectura visual; no asignarlas desde otra pieza.", "",
              "## 7. Resultados esperados y alcance de aceptación", "",
              "Contrato de inventario (SQL parametrizado en `herramientas/fichas_ingesta.py`, clave `:pieza`):", "",
              "| Métrica | Esperado en biblioteca |", "|---|---:|",
              *[f"| `{k}` | {v} |" for k, v in cifras.items()], "",
              "Estos totales incluyen copias, fórmulas y filas fuera del alcance del backend: **no son el número de mediciones válidas a importar**.",
              "La aceptación productiva exige un manifiesto por fichero/hoja que explique importados, excluidos y pendientes, sin pérdidas silenciosas.",
              "El número final de observaciones productivas queda pendiente de resolver las exclusiones y de la revisión humana; no se certifica con el mismo lector.", "",
              "## 8. Tratamiento de casos problemáticos", "",
              "- Conservar generado y sin_confirmar, con motivo y recuento; solo medicion entra en estadísticas. Excluir por celda, no por fila.",
              "- No ejecutar macros ni recalcular; caché ausente/error no es cero. Fórmulas potencialmente dependientes de RAND quedan sin_confirmar.",
              "- No usar cabeceras heredadas/desplazadas para identidad ni fusionar copias con valores/tolerancias distintos.",
              "- #P#, SYM-POINT, plantillas no reconocidas y acciones en imágenes: informar como pendientes, sin inventar resultados.",
              "- Revisar límites actuales de lectura del backend (16 MiB/libro, 128 MiB/selección). Superarlos produce un error explícito.", "",
              "Incongruencias documentadas: " + (", ".join(problemas) or "consultar las transversales") + " en [incongruencias.md](../incongruencias.md).", "",
              "## 9. Casos contrastados en originales", "",
              *[f"- **{r['id']}**: `{r['ruta']}` · {r.get('hoja', '')}!{r.get('celda', 'línea '+str(r.get('linea', '')))}. Esperado `{r['valor_original']}`; {r['tratamiento_esperado']}. {r['motivo']}" for r in referencias], "",
              "Evidencia, fórmula y hash completos en [casos-referencia.jsonl](../casos-referencia.jsonl). Una firma PDF solo valida el formato, no su interpretación.",
              "Los casos muestreados no certifican todas las hojas ni sustituyen la revisión del contrato.", "",
              "## 10. Warnings, lecciones y feature ↔ cotas", "",
              "Fuente editable única: [hallazgos.jsonl](../hallazgos.jsonl). IDs: " + (", ".join(notas) or "sin candidatos consolidados todavía") + ".",
              f"Consulta: `python conocimiento/herramientas/conocimiento_feature.py --pieza {codigo}`.", "",
              "## 11. Pendiente de preguntar y aceptación", "",
              "- Confirmar revisión vigente, cavidades físicas, copia autorizada, condiciones de medida y significado de ceros/contextos incompletos.",
              "- Aclarar uso de valores generados y la procedencia de constantes sospechosas; reclasificar solo con evidencia, sin borrar el original.",
              "- Eduard/revisor: validar la ficha y completar el manifiesto de aceptación por fichero. INTEPLAST: validar conocimiento funcional.",
              "- Aprobación de la ficha: pendiente. Carga de notas/vínculos: pendiente. Fecha/responsable de aceptación: no consta.", ""]
    return "\n".join(lineas)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--crear", action="store_true")
    args = p.parse_args()
    with sqlite3.connect(BD.resolve().as_uri() + "?mode=ro", uri=True) as con:
        datos = informe(con)
        if not args.crear:
            print(json.dumps({"consultas": CONSULTAS, "inventario": datos}, ensure_ascii=False, indent=2))
            return
        identidad = recoger(con)
        casos = [json.loads(s) for s in (CONOCIMIENTO / "casos-referencia.jsonl").read_text(encoding="utf-8").splitlines()]
        hallazgos = [json.loads(s) for s in (CONOCIMIENTO / "hallazgos.jsonl").read_text(encoding="utf-8").splitlines()]
        carpeta = CONOCIMIENTO / "ingesta"
        carpeta.mkdir(exist_ok=True)
        for codigo in ["3167", *[k for k in datos if k != "3167"]]:
            destino = carpeta / f"{codigo}.md"
            if not destino.exists():
                destino.write_text(ficha(con, codigo, datos[codigo], identidad, casos, hallazgos), encoding="utf-8")
        print(f"Inventario preparado para {len(datos)} piezas; revisión humana pendiente.")


if __name__ == "__main__":
    main()
