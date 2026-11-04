"""Balance por original/hoja: compara lectores de producción con evidencia independiente.

No importa datos en la app ni escribe originales/biblioteca. La biblioteca aporta
coordenadas, valores y contexto calculados por otro lector. El backend es solamente
el sistema bajo prueba; sus recuentos nunca se usan como resultado esperado.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

from comun import BD, CONOCIMIENTO, EXEMPLES

ROOT = CONOCIMIENTO.parent
sys.path.insert(0, str(ROOT / "backend"))


def huella_lectores():
    paths=[ROOT/'backend/app/ingestion'/n for n in ('measurement_tables.py','formula_flags.py','formula_dependencies.py','measurement_provenance.py','measurement_csv.py')]
    paths+=[CONOCIMIENTO/'herramientas'/'lector_dr.py']
    return hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()


def original(ruta):
    p = (EXEMPLES / ruta).resolve()
    return Path("\\\\?\\" + str(p)) if os.name == "nt" else p


def coordenada(cell):
    m = re.fullmatch(r"([A-Z]+)([0-9]+)", cell)
    col = 0
    for x in m[1]:
        col = col * 26 + ord(x) - 64
    return int(m[2]), col


def iguales(a, b):
    if a is None or b is None:
        return a is b
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8)
    except (ValueError, TypeError):
        return str(a) == str(b)


def escribir_jsonl(path, filas):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporal = path.with_suffix(path.suffix + ".nuevo")
    temporal.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in filas), encoding="utf-8")
    temporal.replace(path)


def referencia_cliente(hoja, grid, aleatorias):
    """Independent reader adapter: physical coordinates survive header aliases.

    Names CAV.1 (2) and Nr.1 are customer sample templates omitted by the
    historical library profile. R2/OK/NOK/shot suffixes identify distinct samples.
    This does not call or reuse the production header/number parsers.
    """
    from lector_dr import leer_hoja
    nombre = re.match(r'^CAV[._ ]*(\d+)(?:\s*\(\d+\))?$', hoja, re.I)
    celdas = {}
    cambio = bool(nombre)
    for f, row in enumerate(grid,1):
        for c, value in enumerate(row,1):
            if value is None or value == '':continue
            value=str(value)
            if f<=40:
                repeticion=re.fullmatch(r'CAV\.?\s*(\d+)_(\d+)\s+(\d+)',value,re.I)
                if repeticion:
                    value='CAV.'+'.'.join(repeticion.groups())
                    cambio=True
                m=re.fullmatch(r'Nr\.?\s*(\d+)(?:\.0)?',value,re.I)
                if m and nombre:value=m[1]
                m=re.fullmatch(r'CAV\.?\s*(\d+)\s*(?:R(\d+)|_(\d+)|\s+(OK|NOK))',value,re.I)
                if m:
                    value=f'CAV.{m[1]}.{m[2] or m[3] or (1 if m[4].upper()=="OK" else 2)}'
                    cambio=True
            celdas[f,c]=value
    if not cambio:return None
    # A gap after an increasing cavity is a comparison column, not a new series.
    # Annotate only the next, distinct cavity; repeated Cav.1 blocks stay excluded.
    for f in range(1,min(len(grid),40)+1):
        cavs=[(c,int(m[1])) for (rr,c),v in celdas.items() if rr==f and (m:=re.fullmatch(r'CAV\.?\s*(\d+)(?:\.\d+)*',v,re.I))]
        prev=None
        for c,cv in sorted(cavs):
            if prev and c>prev[0]+1 and cv>prev[1] and not celdas.get((f-1,c)):
                celdas[f-1,c]='Cavidades distintas, separadas por columnas auxiliares'
            prev=(c,cv)
    return leer_hoja(f'cav_{nombre[1]}' if nombre else hoja,celdas,aleatorias)


def auditar_libro(con, doc, medidas=None):
    from app.ingestion.measurement_tables import workbook, report_rows
    from app.ingestion.formula_flags import UnsupportedWorkbook
    from app.ingestion.measurement_provenance import usable_measurement

    salida = {"hojas": [], "errores": []}
    oracle = defaultdict(dict)
    for m in (medidas if medidas is not None else con.execute("SELECT * FROM medida_dr WHERE documento_id=?", (doc["id"],))):
        oracle[m["hoja"]][(m["fila"], m["col"])] = dict(m)
    try:
        book = workbook(original(doc["ruta"]))
        revision, rows = report_rows(book, part_code=doc["codigo"])
    except Exception as e:
        if isinstance(e,UnsupportedWorkbook):salida['incidencia_controlada']=str(e)
        else:salida["errores"].append(f"{type(e).__name__}: {e}")
        rows, book, revision = [], [], ""
    salida["revision_backend"] = revision
    if hasattr(book,'audit'):
        expected={(h,f,c) for h,f,c in con.execute('SELECT hoja,fila,col FROM celda_aleatoria WHERE documento_id=?',(doc['id'],))}
        actual={k for k,v in book.audit.cells.items() if 'aleatoria' in v['flags']}
        salida['contraste_rand']={'referencia':len(expected),'backend':len(actual),'solo_referencia':len(expected-actual),'solo_backend':len(actual-expected)}
        if expected!=actual:salida['errores'].append('Coordenadas RAND distintas de la biblioteca')
    backend = defaultdict(dict)
    for r in rows:
        key = coordenada(r["_cell"])
        if key in backend[r["_sheet"]]:
            salida["errores"].append(f"Coordenada repetida: {r['_sheet']}!{r['_cell']}")
        backend[r["_sheet"]][key] = r
    muestras_original = []
    ampliadas=0
    if backend:
        from python_calamine import CalamineWorkbook
        with CalamineWorkbook.from_path(str(original(doc['ruta']))) as independiente:
            for hoja, valores in backend.items():
                grid = independiente.get_sheet_by_name(hoja).to_python(skip_empty_area=False)
                aleatorias={(f,c) for f,c in con.execute('SELECT fila,col FROM celda_aleatoria WHERE documento_id=? AND hoja=?',(doc['id'],hoja))}
                extra=referencia_cliente(hoja,grid,aleatorias)
                if extra:
                    for fila in extra['medidas']:
                        f,c,cota,nom,ts,ti,equipo,cav,valor,marca=fila
                        if (f,c) not in oracle[hoja]:
                            oracle[hoja][f,c]=dict(documento_id=doc['id'],hoja=hoja,fila=f,col=c,cota=cota,nominal=nom,tol_sup=ts,tol_inf=ti,equipo=equipo,cavidad=cav,valor=valor,marca=marca)
                            ampliadas+=1
                keys = sorted(valores)
                for f,c in sorted({keys[0], keys[len(keys)//2], keys[-1]}):
                    valor = grid[f-1][c-1] if f<=len(grid) and c<=len(grid[f-1]) else None
                    esperado = valores[f,c]['value']
                    # Errors/missing caches are checked through formula provenance, not coerced to zero.
                    ok = esperado is None or iguales(valor,esperado)
                    muestras_original.append({'hoja':hoja,'fila':f,'col':c,'valor_original':valor,'valor_backend':esperado,'coincide':ok})
                    if not ok: salida['errores'].append(f'Valor original discordante: {hoja}!{f},{c}')
    salida['comprobacion_original']={'lector':'python-calamine (independiente de xlrd/XML de producción)','celdas':muestras_original}
    salida['referencia_cliente_ampliada']=ampliadas
    for hoja in sorted(set(oracle) | set(backend)):
        esperadas, obtenidas = oracle[hoja], backend[hoja]
        faltan = Counter()
        diferencias = Counter()
        muestras = defaultdict(list)
        estados = Counter(r["provenance_state"] for r in obtenidas.values())
        marcas = Counter(f for r in obtenidas.values() for f in r["flags"])
        coinciden = 0
        coinciden_estados = Counter()
        for key, m in esperadas.items():
            r = obtenidas.get(key)
            if r is None:
                motivo = "cota_no_numerica" if not re.fullmatch(r"\d+(?:[.-]\d+)*",m["cota"]) else "equipo_imposed" if m["equipo"].upper()=="IMPOSED" else "plantilla_o_bloque_no_reconocido"
                faltan[motivo] += 1
                if len(muestras[motivo]) < 3:
                    muestras[motivo].append({"fila":key[0],"col":key[1],"cota":m["cota"]})
                continue
            errores = []
            for campo, esperado in [("value",m["valor"]),("nominal",m["nominal"]),("tol_sup",m["tol_sup"]),("tol_inf",m["tol_inf"])]:
                if not iguales(r.get(campo), esperado):
                    errores.append(campo)
            if r["numbers"] != ["N"+m["cota"]]:
                errores.append("cota")
            if "aleatoria" in (m["marca"] or "") and r["provenance_state"] != "generado":
                errores.append("rand_no_marcada")
            if errores:
                for error in errores:
                    diferencias[error] += 1
                    if len(muestras[error]) < 3:
                        muestras[error].append({"fila":key[0],"col":key[1],"esperado":m,"obtenido":{k:r.get(k) for k in ["value","nominal","tol_inf","tol_sup","numbers","provenance_state"]}})
            else:
                coinciden += 1
                coinciden_estados[r['provenance_state']] += 1
        adicionales = set(obtenidas) - set(esperadas)
        salida["hojas"].append({"hoja":hoja,"referencia_dr":len(esperadas),"leidas_backend":len(obtenidas),"coinciden":coinciden,"coinciden_estados":dict(coinciden_estados),"ausentes":dict(faltan),"discrepantes":len(esperadas)-coinciden-sum(faltan.values()),"diferencias":dict(diferencias),"adicionales":len(adicionales),"adicionales_estados":dict(Counter(obtenidas[k]['provenance_state'] for k in adicionales)),"adicionales_utilizables":sum(usable_measurement(obtenidas[k]) for k in adicionales),"copias_medicion":sum(r["provenance_state"]=="medicion" and "copia" in r["flags"] for r in obtenidas.values()),"utilizables":sum(usable_measurement(r) for r in obtenidas.values()),"estados_backend":dict(estados),"marcas":dict(marcas),"ejemplos":dict(muestras),"adicionales_ejemplos":[{"fila":f,"col":c,"cota":obtenidas[f,c]['numbers']} for f,c in sorted(adicionales)[:3]]})
    salida["hojas_sin_resultados"] = [h for h,_ in book if h not in oracle and h not in backend]
    return salida


def ejecutar(pieza=None, directorio=None):
    inicio = time.monotonic()
    destino=Path(directorio) if directorio else CONOCIMIENTO/'datos'/'aceptacion'
    huella=huella_lectores()
    with sqlite3.connect(BD.resolve().as_uri()+"?mode=ro",uri=True) as con:
        con.row_factory=sqlite3.Row
        docs=[dict(d) for d in con.execute("SELECT * FROM documento ORDER BY codigo,id") if not pieza or d['codigo']==pieza]
        resultados=defaultdict(list)
        pieza_actual=None
        medidas_por_doc=defaultdict(list)
        for idx,d in enumerate(docs,1):
            d['codigo']=d['codigo'] or 'sin_pieza'
            if d['codigo']!=pieza_actual:
                if pieza_actual:
                    escribir_jsonl(destino/f'{pieza_actual}-auditoria.jsonl',resultados[pieza_actual])
                pieza_actual=d['codigo']
                medidas_por_doc=defaultdict(list)
                for m in con.execute('SELECT m.* FROM medida_dr m JOIN documento d ON d.id=m.documento_id WHERE d.codigo=?',(pieza_actual,)):
                    medidas_por_doc[m['documento_id']].append(dict(m))
            r={k:d[k] for k in ['id','ruta','codigo','sha256','ext','tamano','estado','duplicado_de']}
            r['huella_lectores']=huella
            r['tipo']='documento_soporte'
            stat=original(d['ruta']).stat()
            r['inventario_vigente']=stat.st_size==d['tamano'] and stat.st_mtime_ns==d['mtime_ns']
            if not r['inventario_vigente']:r['errores']=['Tamaño o fecha distinta del inventario']
            if d['ext'] in ('xls','xlsx','xlsm'):
                r['tipo']='tabla_excel'
                r.update(auditar_libro(con,d,medidas_por_doc[d['id']]))
                r['seleccion_automatica']=not bool(re.search('retoqu|correction',d['ruta'],re.I))
            elif d['ext']=='csv':
                from app.ingestion.measurement_tables import csv_rows
                r['tipo']='csv'
                try:
                    data=original(d['ruta']).read_bytes()
                    rows=csv_rows(data,pilot=d['codigo']=='3212')
                    r['leidas_backend']=len(rows)
                    r['cotas_backend']=len({n for x in rows for n in x['numbers']})
                    try:texto=data.decode('utf-8-sig')
                    except UnicodeDecodeError:texto=data.decode('cp1252')
                    raw=list(csv.reader(texto.splitlines(),delimiter=';'))
                    headers=next((rr for rr in raw if any(re.fullmatch(r'C(?:AV\.?)?\s*\d+.*',v.strip(),re.I) for v in rr[5:])),[])
                    diferencias=0
                    for row in rows:
                        source=raw[row['line']-1]
                        if row.get('_wide'):
                            cav=int(row['_cavity'][1:])
                            cols=[i for i,v in enumerate(headers) if (m:=re.fullmatch(r'C(?:AV\.?)?\s*(\d+)(.*)',v.strip(),re.I)) and int(m[1])==cav]
                            candidatos=[source[i] for i in cols if i<len(source)]
                            ok=any(iguales(x,row['value']) for x in candidatos)
                        else:ok=len(source)>6 and iguales(source[6],row['value'])
                        if not ok:diferencias+=1
                    r['comprobacion_original']={'filas':len(rows),'diferencias_valor':diferencias,'lector':'csv estándar, columna física del original'}
                    if diferencias:r.setdefault('errores',[]).append(f'{diferencias} valores CSV discordantes')
                except Exception as e:
                    r['leidas_backend']=0
                    r['motivo']=str(e)
            if r['tipo']!='documento_soporte':
                with original(d['ruta']).open('rb') as fichero:
                    r['sha256_actual']=hashlib.file_digest(fichero,'sha256').hexdigest()
                if d['sha256'] and r['sha256_actual']!=d['sha256']:
                    r.setdefault('errores',[]).append('Original distinto de la biblioteca')
            resultados[d['codigo']].append(r)
            if idx%50==0:
                print(f'{idx}/{len(docs)} documentos ({time.monotonic()-inicio:.0f} s)',flush=True)
        for codigo,filas in resultados.items():
            escribir_jsonl(destino/f'{codigo}-auditoria.jsonl',filas)
        if huella_lectores()!=huella:
            raise RuntimeError('Los lectores cambiaron durante la auditoría; repetir antes de aceptar')
        print(json.dumps({'piezas':len(resultados),'documentos':len(docs),'segundos':round(time.monotonic()-inicio,2)},ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pieza')
    p.add_argument('--directorio',help='Directorio de auditoría derivada; no modifica originales ni biblioteca')
    a=p.parse_args()
    ejecutar(a.pieza,a.directorio)
