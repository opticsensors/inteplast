"""Verifica contratos de ingesta, casos originales y revisión documental de lecciones.

Solo lectura. No implica aprobación corporativa, carga de la app ni ejecución de macros.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from auditar_ingesta import coordenada, iguales, original, huella_lectores
from comun import BD, CONOCIMIENTO


def cargar(path):
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def comprobar_csv(data, rows):
    """Contrasta cada resultado con una columna inequívoca, incluida la repetición."""
    try:texto=data.decode('utf-8-sig')
    except UnicodeDecodeError:texto=data.decode('cp1252')
    raw=list(csv.reader(texto.splitlines(),delimiter=';'))
    patron=re.compile(r'C(?:AV(?:ITY)?\.?)?[\s_]*(\d+)(.*)',re.I)
    headers=next((r for r in raw if any(patron.fullmatch(v.strip()) for v in r[5:])),[])
    columns={}
    for i,v in enumerate(headers):
        if i<5:continue
        m=patron.fullmatch(v.strip())
        if m:
            suffix=unicodedata.normalize('NFKD',m[2]).encode('ascii','ignore').decode()
            variant=re.sub(r'[^\w.-]+','',suffix).strip('.-')
            columns.setdefault(('c'+str(int(m[1])),variant),[]).append(i)
    errores=[]
    for r in rows:
        src=raw[r['line']-1]
        if r.get('_wide'):
            candidates=columns.get((r['_cavity'],r['_variant']),[])
            if len(candidates)!=1:
                errores.append(f"L{r['line']}: columna ambigua {candidates}");continue
            column=candidates[0]
            inicio=min(c for values in columns.values() for c in values)
            limites=(4,5) if inicio==6 else (None,None)
        else:column=6;limites=(4,5)
        for campo,col in [('value',column),('nominal',3),('tol_sup',limites[0]),('tol_inf',limites[1])]:
            value=src[col].strip() if col is not None and col<len(src) else ''
            expected=float(value.replace(',','.')) if value else None
            if not iguales(expected,r.get(campo)):errores.append(f"L{r['line']} C{col}: {campo} discordante")
    return errores


def contenido(path, prueba):
    tipo=prueba['tipo']
    if tipo=='visual':return ''
    if tipo in ('diapositiva','documento_word'):
        member=f"ppt/slides/slide{prueba['numero']}.xml" if tipo=='diapositiva' else 'word/document.xml'
        with ZipFile(path) as z:
            return ' '.join(e.text for e in ET.fromstring(z.read(member)).iter() if e.tag.endswith('}t') and e.text)
    if tipo=='pagina':
        import fitz
        with fitz.open(str(path)) as d:return d[prueba['numero']-1].get_text()
    if tipo=='linea':return path.read_text(encoding='cp1252').splitlines()[prueba['numero']-1]
    if tipo=='fila_excel':
        from python_calamine import CalamineWorkbook
        with CalamineWorkbook.from_path(str(path)) as b:
            row=b.get_sheet_by_name(prueba['hoja']).to_python(skip_empty_area=False)[prueba['numero']-1]
            return ' '.join(map(str,row))
    raise ValueError(f'Tipo de comprobación desconocido: {tipo}')


def lecciones():
    errores=[];n=0;pruebas=0
    for r in cargar(CONOCIMIENTO/'hallazgos.jsonl'):
        if r.get('tipo') not in ('leccion','warning','vinculo_feature_cota'):continue
        n+=1
        if r.get('validacion')!='revisado_documentalmente':
            errores.append(f"{r['id']}: falta contraste documental")
        if not r.get('revision_documental',{}).get('comprobaciones'):
            errores.append(f"{r['id']}: sin comprobaciones")
        for prueba in r.get('revision_documental',{}).get('comprobaciones',[]):
            pruebas+=1
            ev=r['evidencia'][prueba['evidencia']]
            p=original(ev['ruta'])
            if digest(p)!=ev['sha256']:errores.append(f"{r['id']}: original cambiado")
            texto=re.sub(r'\s+',' ',contenido(p,prueba)).casefold()
            for frag in prueba.get('contiene',[]):
                if re.sub(r'\s+',' ',frag).casefold() not in texto:errores.append(f"{r['id']}: no encontrado {frag!r} en {prueba}")
            if prueba['tipo']=='visual' and not prueba.get('observacion'):
                errores.append(f"{r['id']}: inspección visual sin resultado")
    return {'registros':n,'comprobaciones':pruebas,'errores':errores}


def comprobar_salida_caso(caso, info):
    """El esperado se fija desde el original, nunca desde el estado observado."""
    esperado=caso['esperado_backend'];errores=[]
    if info is None:return [f"{caso['id']}: falta la salida esperada del backend"]
    from app.ingestion.measurement_provenance import usable_measurement
    if 'utilizable' in esperado and usable_measurement(info)!=esperado['utilizable']:
        errores.append(f"{caso['id']}: elegibilidad numérica incorrecta")
    for field in ('duplicate_of','comparison_origin'):
        if field in esperado and info.get(field)!=esperado[field]:errores.append(f"{caso['id']}: referencia {field} incorrecta")
    if 'estado' in esperado and info.get('provenance_state','medicion')!=esperado['estado']:
        errores.append(f"{caso['id']}: estado esperado {esperado['estado']}; backend {info.get('provenance_state','medicion')}")
    for flag in esperado.get('marcas',[]):
        if flag not in info.get('flags',[]):errores.append(f"{caso['id']}: falta marca {flag}")
    for flag in esperado.get('marcas_prohibidas',[]):
        if flag in info.get('flags',[]):errores.append(f"{caso['id']}: marca indebida {flag}")
    for aviso in esperado.get('avisos',[]):
        if not any(aviso in w for w in info.get('warnings',[])):errores.append(f"{caso['id']}: falta aviso {aviso}")
    return errores


def contrastar_backend(caso, cache):
    from app.ingestion.measurement_tables import workbook, report_rows, csv_rows, identity_flags
    esperado=caso.get('esperado_backend')
    if not esperado:return [f"{caso['id']}: falta criterio explícito para el backend"]
    ambito=esperado['ambito'];p=original(caso['ruta']);errores=[]
    key=(caso['ruta'],caso['pieza'])
    if ambito=='documento':
        if p.suffix.lower() in {'.xls','.xlsx','.xlsm','.csv'}:return [f"{caso['id']}: documento tabular sin contraste"]
        return []  # selección productiva: el original de soporte no es una tabla
    if key not in cache:
        try:
            if p.suffix.lower()=='.csv':cache[key]=(None,csv_rows(p.read_bytes(),pilot=caso['pieza']=='3212'),None)
            else:
                book=workbook(p);_,rows=report_rows(book,part_code=caso['pieza']);cache[key]=(book,rows,None)
        except ValueError as e:cache[key]=(None,[],e)
    book,rows,error=cache[key]
    if ambito=='incidencia':
        return [] if error and esperado['mensaje'] in str(error) else [f"{caso['id']}: incidencia esperada no producida"]
    if error:return [f"{caso['id']}: error del backend: {error}"]
    if ambito=='identidad':
        flags,warnings=identity_flags(dict(book)[caso['hoja']],caso['pieza'])
        errores+=comprobar_salida_caso(caso,{'flags':flags,'warnings':warnings})
        if esperado.get('sin_efecto_numerico') and any(r['_sheet']==caso['hoja'] and r['_cell']==caso['celda'] for r in rows):
            errores.append(f"{caso['id']}: cabecera importada como medición")
        return errores
    if ambito=='formula':
        fila,col=coordenada(caso['celda'])
        return comprobar_salida_caso(caso,book.audit.cells.get((caso['hoja'],fila,col)))
    if ambito=='ausencia':
        found=[r for r in rows if r['_sheet']==caso['hoja'] and r['_cell']==caso['celda']]
        return [f"{caso['id']}: celda excluida aparece como resultado"] if found else []
    if ambito=='tolerancia':
        fila,_=coordenada(caso['celda'])
        found=[r for r in rows if r['_sheet']==caso['hoja'] and coordenada(r['_cell'])[0]==fila]
        if not found:return [f"{caso['id']}: fila de tolerancia ausente"]
        if any(not iguales(r[esperado['campo']],caso['valor_original']) for r in found):errores.append(f"{caso['id']}: tolerancia sustituida")
        return errores
    if ambito!='medicion':return [f"{caso['id']}: ámbito no reconocido {ambito}"]
    found=[r for r in rows if (r.get('line')==caso['linea'] if 'linea' in caso else r['_sheet']==caso['hoja'] and r['_cell']==caso['celda'])]
    if len(found)!=1:return [f"{caso['id']}: esperada una observación, encontradas {len(found)}"]
    errores+=comprobar_salida_caso(caso,found[0])
    if not iguales(found[0]['value'],caso['valor_original']):errores.append(f"{caso['id']}: valor del backend distinto del original")
    return errores


def casos():
    errores=[];n=0;cache={};contrastados=0
    for r in cargar(CONOCIMIENTO/'casos-referencia.jsonl'):
        n+=1;p=original(r['ruta']);esperado=r['valor_original']
        if digest(p)!=r['sha256']:errores.append(f"{r['id']}: hash distinto")
        if isinstance(esperado,str) and esperado.startswith('%PDF'):
            with p.open('rb') as f:valor=f.read(8).decode('ascii')
        elif 'linea' in r:
            cells=next(x for i,x in enumerate(csv.reader(p.read_text(encoding='cp1252').splitlines(),delimiter=';'),1) if i==r['linea'])
            valor=cells[r['columna']-1]
        else:
            f,c=coordenada(r['celda'])
            if isinstance(esperado,str) and esperado.startswith('#') and p.suffix.lower()=='.xls':
                import xlrd
                with xlrd.open_workbook(p,on_demand=True) as b:
                    cell=b.sheet_by_name(r['hoja']).cell(f-1,c-1)
                    valor=xlrd.biffh.error_text_from_code.get(cell.value) if cell.ctype==xlrd.XL_CELL_ERROR else cell.value
            else:
                from python_calamine import CalamineWorkbook
                with CalamineWorkbook.from_path(str(p)) as b:
                    grid=b.get_sheet_by_name(r['hoja']).to_python(skip_empty_area=False)
                    valor=grid[f-1][c-1] if f<=len(grid) and c<=len(grid[f-1]) else None
        if esperado is None and valor in ('',None):valor=None
        if not iguales(valor,esperado):errores.append(f"{r['id']}: esperado {esperado!r}; original {valor!r}")
        fallos=contrastar_backend(r,cache);errores.extend(fallos)
        contrastados+=not fallos
    return {'casos':n,'contrastes_backend_correctos':contrastados,'errores':errores}


def validar_balance(r):
    errores=[]
    for h in r.get('hojas',[]):
        if h['referencia']!=h['coinciden']+h['no_leidas']+h['discrepantes']:
            errores.append(f"{r['id']} {h['hoja']}: balance de referencia no cierra")
        if h['salida']!=h['medicion']+h['generado']+h['sin_confirmar']:
            errores.append(f"{r['id']} {h['hoja']}: balance de procedencia no cierra")
        if h['salida']!=h['coinciden']+h['discrepantes']+h['adicionales']:
            errores.append(f"{r['id']} {h['hoja']}: salida no conciliada")
        if 'utilizables' in h and h['utilizables']!=h['medicion']-h['copias_medicion']:
            errores.append(f"{r['id']} {h['hoja']}: copias contadas como mediciones")
        if h['discrepantes'] or h.get('adicionales_medicion',0):
            errores.append(f"{r['id']} {h['hoja']}: discrepancias sin resolver")
    return errores


def balances():
    errores=[];ids=[]
    huella=huella_lectores()
    with sqlite3.connect(BD.resolve().as_uri()+'?mode=ro',uri=True) as con:
        inventario={r[0]:r[1:] for r in con.execute('SELECT id,ruta,tamano,mtime_ns FROM documento')}
    for p in (CONOCIMIENTO/'ingesta'/'balances').glob('*.jsonl'):
        for r in cargar(p):
            ids.append(r['id']);errores.extend(validar_balance(r))
            if r.get('huella_lectores')!=huella:errores.append(f"{r['id']}: cambió el lector")
            if r['id'] in inventario:
                ruta,tamano,mtime=inventario[r['id']];path=original(ruta);stat=path.stat()
                if ruta!=r['ruta'] or stat.st_size!=tamano or stat.st_mtime_ns!=mtime:errores.append(f"{r['id']}: cambió el original")
                if r['ext'] in ('xls','xlsx','xlsm','csv') and digest(path)!=r['sha256']:errores.append(f"{r['id']}: hash distinto")
                if r.get('csv',{}).get('salida'):
                    from app.ingestion.measurement_tables import csv_rows
                    data=path.read_bytes();rows=csv_rows(data,pilot=r['codigo']=='3212')
                    if len(rows)!=r['csv']['salida']:errores.append(f"{r['id']}: cambió el balance CSV")
                    errores.extend(f"{r['id']}: {e}" for e in comprobar_csv(data,rows))
    esperados=set(inventario)
    if set(ids)!=esperados or len(set(ids))!=len(ids):errores.append('Inventario incompleto o duplicado')
    return {'documentos':len(ids),'errores':errores}


def piloto():
    from validar_piloto import validar_piloto
    r=validar_piloto()
    return {'spc':r['spc']['archivos'],'valores_spc':r['spc']['valores'],
            'celdas_inf04':r['inf04']['celdas_comparadas'],'cambios_valor':len(r['inf04']['cambios_valor']),'errores':r['errores']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--casos',action='store_true');p.add_argument('--lecciones',action='store_true');p.add_argument('--balances',action='store_true');p.add_argument('--piloto',action='store_true')
    a=p.parse_args();todo=not(a.casos or a.lecciones or a.balances or a.piloto)
    resultado={}
    for nombre,funcion in [('casos',casos),('lecciones',lecciones),('balances',balances),('piloto',piloto)]:
        if todo or getattr(a,nombre):resultado[nombre]=funcion()
    print(json.dumps(resultado,ensure_ascii=False,indent=2))
    raise SystemExit(int(any(v['errores'] for v in resultado.values())))
