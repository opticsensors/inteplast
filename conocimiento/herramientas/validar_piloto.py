"""Contraste independiente de SPC y copias Inf_04 del piloto 3167; solo lectura."""
import json
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from python_calamine import CalamineWorkbook

from auditar_ingesta import original, iguales
from comun import BD
from verificar_aceptacion import digest


def validar_piloto():
    with sqlite3.connect(BD.resolve().as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        docs=[dict(r) for r in con.execute("SELECT id,ruta,sha256,ext FROM documento WHERE codigo='3167'")]
    por_nombre={Path(d['ruta']).name:d for d in docs if 'Estudis' in d['ruta']}
    archivos=[d for d in por_nombre.values() if d['ext']=='txt' and '_SPC_N' in d['ruta']]
    cache={};resultados=[];errores=[]
    for doc in archivos:
        p=original(doc['ruta'])
        if digest(p)!=doc['sha256']:errores.append(f"{doc['id']}: original cambiado")
        m=re.search(r'_SPC_(N.+)_Cav_(\d+)\.txt$',p.name)
        esperado='3167_Cpk generator_SPC_'+m[1]+'.xlsm'
        candidatos=[d for n,d in por_nombre.items() if n.replace('_','.')==esperado.replace('_','.')]
        if len(candidatos)!=1:raise ValueError(f'Generador ambiguo o ausente: {esperado}')
        libro=candidatos[0]
        if libro['id'] not in cache:
            path=original(libro['ruta'])
            if digest(path)!=libro['sha256']:errores.append(f"{libro['id']}: generador cambiado")
            with CalamineWorkbook.from_path(str(path)) as b:
                hojas={s:b.get_sheet_by_name(s).to_python(skip_empty_area=False) for s in b.sheet_names if s.startswith('N') and '_Cav_' in s}
            with ZipFile(path) as z:
                aleatorias=sum(bool(re.search(r'\b(?:RAND|RANDBETWEEN)\s*\(',f.text or '',re.I))
                    for name in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name)
                    for f in ET.fromstring(z.read(name)).iter() if f.tag.endswith('}f'))
            cache[libro['id']]=(hojas,aleatorias)
        hojas,aleatorias=cache[libro['id']]
        candidatas=[(s,g) for s,g in hojas.items() if s.endswith('_Cav_'+m[2])]
        secuencias=[line.split(';')[7:] for line in p.read_text(encoding='cp1252').splitlines() if line.startswith('#P#;')]
        valores=[float(v.replace(',','.')) for sec in secuencias for v in sec if v.strip()]
        aciertos=[s for s,g in candidatas if len(g)>=len(valores) and all(len(g[i])>51 and iguales(v,g[i][51]) for i,v in enumerate(valores))]
        ok=len(aciertos)==1 and bool(valores) and aleatorias>0
        if not ok:errores.append(f"{doc['id']}: SPC sin correspondencia completa")
        resultados.append(dict(documento_id=doc['id'],ruta=doc['ruta'],sha256=doc['sha256'],generador_id=libro['id'],
            generador=libro['ruta'],sha256_generador=libro['sha256'],hoja=aciertos[0] if aciertos else None,
            rango=f'AZ1:AZ{len(valores)}',valores=len(valores),coinciden=ok,formulas_rand=aleatorias))
    nombres=['PPAP-3167-00_Inf_04.xlsm','PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm']
    copias=[next(d for d in docs if Path(d['ruta']).name==n and '/Customer/'+n in d['ruta']) for n in nombres]
    for doc in copias:
        if digest(original(doc['ruta']))!=doc['sha256']:errores.append(f"{doc['id']}: copia Inf_04 cambiada")
    cambios=[];comparadas=0;no_numericas=0;tolerancias=[]
    with CalamineWorkbook.from_path(str(original(copias[0]['ruta']))) as a, CalamineWorkbook.from_path(str(original(copias[1]['ruta']))) as b:
        for s in a.sheet_names:
            if not re.fullmatch('cav_[1-4]',s,re.I):continue
            ga=a.get_sheet_by_name(s).to_python(skip_empty_area=False);gb=b.get_sheet_by_name(s).to_python(skip_empty_area=False)
            if len(ga)!=len(gb):errores.append(f'{s}: dimensiones distintas')
            for f,(ra,rb) in enumerate(zip(ga,gb),1):
                if f<8:continue
                for c in range(9,14):
                    va=ra[c] if c<len(ra) else None;vb=rb[c] if c<len(rb) else None
                    if not isinstance(va,(int,float)) or not isinstance(vb,(int,float)):
                        if va not in ('',None) or vb not in ('',None):
                            no_numericas+=1
                            if va!=vb:errores.append(f'{s}!{chr(65+c)}{f}: cambio de texto no previsto')
                        continue
                    comparadas+=1
                    if not iguales(va,vb):cambios.append(dict(hoja=s,celda=chr(65+c)+str(f),original=va,copia=vb))
                for c in (5,6):
                    va=ra[c] if c<len(ra) else None;vb=rb[c] if c<len(rb) else None
                    if isinstance(va,(int,float)) and isinstance(vb,(int,float)) and not iguales(va,vb):
                        tolerancias.append(dict(hoja=s,celda=chr(65+c)+str(f),original=va,copia=vb))
    if len(resultados)!=328 or len(cache)!=82:errores.append('Inventario SPC distinto de 328 archivos / 82 generadores')
    if len(cambios)!=8:errores.append('Las diferencias Inf_04 no coinciden con I-603: ocho valores')
    if comparadas+no_numericas!=11808:errores.append('Balance Inf_04 distinto de las 11.808 celdas de I-603')
    return dict(pieza='3167',fecha='2026-11-02',responsable='Codex',tipo='contraste_tecnico_independiente',
        spc=dict(archivos=len(resultados),generadores=len(cache),valores=sum(r['valores'] for r in resultados),comprobaciones=resultados),
        inf04=dict(fuentes=copias,celdas_comparadas=comparadas+no_numericas,numericas=comparadas,no_numericas=no_numericas,cambios_valor=cambios,cambios_tolerancia=tolerancias),errores=errores)


if __name__=='__main__':
    resultado=validar_piloto()
    print(json.dumps(resultado,ensure_ascii=False,indent=2))
    raise SystemExit(bool(resultado['errores']))
