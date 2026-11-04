"""Publica balances conciliados y contratos técnicos para las 21 piezas.

Exige auditoría actual y sin discrepancias. No convierte un formato no soportado
en mediciones, ni una revisión documental en aprobación de INTEPLAST.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from auditar_ingesta import huella_lectores, escribir_jsonl, iguales, original
from comun import BD, CONOCIMIENTO
from identidad_piezas import recoger
from fichas_ingesta import informe
from verificar_aceptacion import cargar, validar_balance, casos, lecciones, comprobar_csv


def balance_documento(r):
    doc={k:r.get(k) for k in ('id','ruta','codigo','ext','tamano','sha256','duplicado_de','huella_lectores')}
    doc['fecha']='2026-11-02'
    doc['archivo_verificado']=r.get('inventario_vigente',False)
    doc['tratamiento']='conservar_documento_soporte'
    doc['hojas']=[]
    for h in r.get('hojas',[]):
        states=h['estados_backend']
        doc['hojas'].append(dict(hoja=h['hoja'],referencia=h['referencia_dr'],salida=h['leidas_backend'],
            coinciden=h['coinciden'],no_leidas=sum(h['ausentes'].values()),motivos_no_leidas=h['ausentes'],
            discrepantes=h['discrepantes'],adicionales=h['adicionales'],
            adicionales_medicion=h.get('adicionales_utilizables',h.get('adicionales_estados',{}).get('medicion',0)),
            medicion=states.get('medicion',0),generado=states.get('generado',0),sin_confirmar=states.get('sin_confirmar',0),
            copias=h['marcas'].get('copia',0),copias_medicion=h.get('copias_medicion',0),utilizables=h.get('utilizables',0),marcas=h['marcas'],localizadores_no_leidos={k:v for k,v in h['ejemplos'].items() if k in h['ausentes']}))
    if doc['hojas']:
        doc['tratamiento']='conservar_resultados_y_marcas'
    if r.get('tipo')=='tabla_excel' and not doc['hojas']:
        doc['tratamiento']='conservar_libro_sin_tabla_dimensional_reconocida'
        doc['motivo']='Plantilla, cálculo SPC/MSA, método o formato sin resultado dimensional reconocido; no inventar medidas.'
    if r.get('seleccion_automatica') is False:
        doc['tratamiento']='conservar_plan_o_comparativa_de_correccion'
        doc['motivo']='Fuera de la selección automática de mediciones por carpeta de retoques/corrección; los recuentos describen las tablas, no nuevas muestras.'
    if r.get('incidencia_controlada'):
        doc['tratamiento']='conservar_pdf_con_extension_xls'
        doc['motivo']=r['incidencia_controlada']
    if r.get('tipo')=='csv':
        doc['csv']={'salida':r.get('leidas_backend',0),'cotas':r.get('cotas_backend',0),'comprobacion':r.get('comprobacion_original')}
        if doc['csv']['salida']:
            from app.ingestion.measurement_tables import csv_rows
            data=original(r['ruta']).read_bytes()
            rows=csv_rows(data,pilot=r['codigo']=='3212')
            diferencias=comprobar_csv(data,rows)
            if diferencias or len(rows)!=doc['csv']['salida']:raise ValueError(f"{r['id']}: {diferencias}")
            doc['csv']['contraste']='Columna exacta de cavidad y variante; valor, nominal y tolerancias.'
        doc['tratamiento']='importar_csv_dimensional' if doc['csv']['salida'] else 'conservar_csv_no_dimensional'
        if r.get('motivo'):doc['motivo']=r['motivo']
    if r['ext']=='txt':
        with original(r['ruta']).open('rb') as f:head=f.read(2048)
        if b'#P#' in head:
            probado=(r['codigo']=='3167' and ('Estudis' in r['ruta'] or 'Estudios' in r['ruta'])) or (r['codigo']=='3237' and bool(re.fullmatch(r'3237_SPC_Cav_[1-4]\.txt',Path(r['ruta']).name,re.I)))
            doc['tratamiento']='conservar_spc_sin_importar_mediciones'
            doc['procedencia']='generado' if probado else 'sin_confirmar'
            doc['motivo']='I-003: salida del generador documentada; no es medición.' if probado else 'Formato #P# fuera del lector productivo actual; no certificar constantes por ausencia de fórmulas.'
    if r.get('duplicado_de'):
        doc['duplicado_exacto']=True
        doc['politica_duplicado']='Conservar procedencia; no contabilizar como una nueva adquisición.'
    if r.get('comprobacion_original') and r.get('tipo')=='tabla_excel':
        cells=r['comprobacion_original']['celdas']
        doc['contraste_original']={'lector':r['comprobacion_original']['lector'],'celdas':len(cells),'coinciden':sum(c['coincide'] for c in cells),
            'localizadores':[{'hoja':c['hoja'],'fila':c['fila'],'col':c['col']} for c in cells]}
    doc['referencia_cliente_ampliada']=r.get('referencia_cliente_ampliada',0)
    return doc


def resumen(docs):
    c=Counter({k:0 for k in ('hojas','referencia','salida','coinciden','no_leidas','adicionales','medicion','generado','sin_confirmar','copias','utilizables','csv','perfiles','celdas_originales')})
    c['documentos']=len(docs)
    tratamientos=Counter();motivos=Counter()
    for d in docs:
        tratamientos[d['tratamiento']]+=1
        c['hojas']+=len(d['hojas'])
        for h in d['hojas']:
            c.update({k:h[k] for k in ('referencia','salida','coinciden','no_leidas','adicionales','medicion','generado','sin_confirmar','copias','utilizables')})
            motivos.update(h['motivos_no_leidas'])
        c['csv']+=d.get('csv',{}).get('salida',0)
        c['perfiles']+=int('perfil_contorno' in d)
        c['celdas_originales']+=d.get('contraste_original',{}).get('celdas',0)
    return dict(c),dict(tratamientos),dict(motivos)


def seccion(texto, numero, contenido):
    return re.sub(rf'(?ms)^## {numero}\. .*?(?=^## \d+\.|\Z)',contenido.strip()+'\n\n',texto,count=1)


def ficha(codigo,docs,identidad,inventario):
    c,tratamientos,motivos=resumen(docs)
    path=CONOCIMIENTO/'ingesta'/f'{codigo}.md'
    text=path.read_text(encoding='utf-8')
    contexto=json.loads((CONOCIMIENTO/'ingesta'/'contextos.json').read_text(encoding='utf-8'))[codigo]
    text=re.sub(r'Cavidades reales:.*?(?=\nLa revisión)', 'Cavidades y declaración del molde: '+contexto['cavidades'],text,flags=re.S)
    text=seccion(text,5,'## 5. Condiciones de medida\n\n'+contexto['condiciones']+'\n\nFuentes y rutas específicas: '+', '.join('`'+p+'`' for p in contexto['rutas_sensibles']))
    if '### Rutas que requieren conservar el contexto' not in text:
        text=text.replace('## 3. ', '### Rutas que requieren conservar el contexto\n\n'+'\n'.join('- `'+p+'`' for p in contexto['rutas_sensibles'])+'\n\n## 3. ',1)
    referencias=[r for r in cargar(CONOCIMIENTO/'casos-referencia.jsonl') if r['pieza']==codigo]
    text=seccion(text,9,'## 9. Casos originales contrastados con el backend\n\n'+', '.join('**'+r['id']+'**' for r in referencias)+'\n\nFuente: [casos-referencia.jsonl](../casos-referencia.jsonl). Se comprueban hash, valor original, ámbito, estado, marcas y elegibilidad numérica; las copias incluyen coordenada de origen. Los casos de identidad y soporte no se hacen pasar por pruebas de medición.')
    text=re.sub(r'> Borrador.*\n> .*\n',
        '> Contrato técnico cerrado el 02/11/2026 por contraste de lectores y originales.\n'
        '> Aceptación del alcance descrito; los datos excluidos conservan su fuente y motivo. No equivale a homologación del cliente.\n',text)
    cliente=identidad[codigo]['clientes'].most_common(1)
    valor=cliente[0][0] if cliente else 'no consta en INTRO!C23'
    if 'Cliente declarado en INTRO' not in text:
        text=text.replace('Cavidades reales:',f'Cliente declarado en INTRO: **{valor}**; conservar las discrepancias I-005, no usarlo como aprobación comercial.\n\nCavidades reales:')
    cifras='\n'.join(f'| `{k}` | {inventario[codigo][k]} |' for k in ('libros_ppap','hojas_ppap','cotas_dr','diapositivas_perfiladas','filas_cadena','celdas_rand','libros_rand'))
    text=seccion(text,7,f'''## 7. Balance de aceptación por fichero y hoja

Manifiesto completo: [balances/{codigo}.jsonl](balances/{codigo}.jsonl). Incluye los **{c['documentos']} documentos**, cada hoja, sus cantidades, tratamiento, motivo y localizadores. Auditoría reproducible: `auditar_ingesta.py --pieza {codigo}` y `verificar_aceptacion.py --balances`.

| Resultado de las tablas Excel | Cantidad |
|---|---:|
| Hojas con referencia o salida | {c['hojas']} |
| Valores en referencia independiente | {c['referencia']} |
| Coinciden en celda, valor, cota, nominal y tolerancias | {c['coinciden']} |
| Referencia fuera de la salida del lector, con motivo | {c['no_leidas']} |
| Salidas adicionales conservadas como evidencia, no medición | {c['adicionales']} |
| Salida total del lector | {c['salida']} |
| Procedencia medición (incluye copias) | {c['medicion']} |
| Copias conservadas (subconjunto de los estados) | {c['copias']} |
| Mediciones utilizables, sin copias | {c['utilizables']} |
| Generado | {c['generado']} |
| Sin confirmar | {c['sin_confirmar']} |
| Celdas muestreadas directamente en originales | {c['celdas_originales']} |
| Resultados CSV contrastados contra su columna original | {c['csv']} |
| Perfiles PDF contrastados | {c['perfiles']} |

Las dos igualdades exigidas son **referencia = coincidencias + no leídos** y **salida = medición + generado + sin confirmar**. Ninguna discrepancia de valor/contexto se acepta. Los adicionales tienen marcas de exclusión (fórmulas, valores impuestos, copias o bloques secundarios), y no se incorporan como mediciones sin evidencia independiente.

Este balance mide la salida por documento **antes** de fusionar series, priorizar CSV y deduplicar en la app. Los libros de retoques se contabilizan para contrastar su contenido, pero se mantienen fuera de la selección automática de nuevas mediciones. No es un recuento de filas ya cargadas en la BD.''')
    text=text.replace('## 8. ',f'''Inventario complementario de la biblioteca, reproducible con las consultas de `fichas_ingesta.py` y `:pieza={codigo}`. Incluye las plantillas fuera del alcance productivo; no confundir con el balance del lector anterior.

| Métrica de biblioteca | Cantidad |
|---|---:|
{cifras}

## 8. ''',1)
    table='\n'.join(f'| `{k}` | {v} |' for k,v in sorted(tratamientos.items()))
    missing='; '.join(f'{k}: {v}' for k,v in sorted(motivos.items())) or 'ninguno'
    text=seccion(text,8,f'''## 8. Tratamiento cerrado de los casos problemáticos

| Tratamiento de archivo | Documentos |
|---|---:|
{table}

Fuera de la salida numérica de referencia: {missing}. El manifiesto identifica el fichero, la hoja y ejemplos de coordenadas para cada motivo; estas cantidades no se sustituyen por cero.

- Generado y sin confirmar se conservan visibles y se excluyen de estadísticas, gráficas y respuestas numéricas; la exclusión es por celda.
- Los códigos no soportados, tablas agregadas, comparativas, libros SPC/MSA y #P# quedan como documentos/evidencia con exclusión explícita. No se certifican como nuevas mediciones.
- Las copias estructurales del mismo libro conservan coordenada de origen; no cuentan dos veces. Las diferencias conservan su estado y nunca sustituyen al original. Condiciones y revisiones se conservan separadas. No inferir ejecución de un plan ni cavidades físicas a partir de columnas.
- Ante revisión, cavidad o procedencia desconocida se conserva el contexto desconocido y se impide fusionarlo con uno conocido. Reclasificar requiere evidencia; no borrar valores.
- Los límites de producción siguen siendo 16 MiB por libro y 128 MiB por selección; la auditoría por archivo no elimina esos límites.''')
    text=seccion(text,11,f'''## 11. Aceptación técnica

**Cerrada el 02/11/2026 por Codex para el alcance del manifiesto.** El piloto 3167 usa las mismas reglas y verificaciones que el resto. Se han comprobado los casos originales de la sección 9, conciliado todas las hojas y fijado el tratamiento de cada fichero.

Criterios para una ejecución futura: mismos originales y huella del lector; balances exactos; cero discrepancias de valores/contexto; los datos generados o sin confirmar no entran en cálculos; todo archivo sin salida lleva un motivo. Si cambian fuentes o lectores, repetir la auditoría, no actualizar los esperados a ciegas.

La revisión comercial de la pieza, el número físico de cavidades cuando no consta y el uso de constantes sospechosas no se inventan: el contrato conserva esos límites y sus exclusiones. Las lecciones asociadas están revisadas documentalmente; la aprobación corporativa de INTEPLAST es un estado diferente y no se atribuye al revisor técnico.''')
    text=text.replace('Revisión humana pendiente','Contraste técnico completado').replace('Los casos muestreados no certifican todas las hojas ni sustituyen la revisión del contrato.','Los casos muestreados se complementan con el balance exhaustivo por fichero y hoja; no acreditan hechos físicos que el original no documenta.')
    if codigo=='3167' and '[validacion-3167.json]' not in text:
        text=text.replace('## 10. ','''Contraste específico del piloto: [validacion-3167.json](validacion-3167.json), reproducible con `validar_piloto.py`. Comprueba todas las secuencias SPC de los 328 archivos contra los 82 generadores y compara celda a celda las dos versiones Inf_04. Las ocho diferencias de valor se conservan separadas; la copia no sustituye al original.

## 10. ''',1)
    path.write_text(text.rstrip()+'\n',encoding='utf-8')
    return c


def main():
    from validar_piloto import validar_piloto
    piloto=validar_piloto()
    if piloto['errores']:raise ValueError(piloto['errores'])
    for funcion in (casos,lecciones):
        result=funcion()
        if result['errores']:raise ValueError(result['errores'])
    por_pieza={};huella=huella_lectores();errores=[]
    for p in sorted((CONOCIMIENTO/'datos'/'aceptacion').glob('*-auditoria.jsonl')):
        raw=cargar(p)
        for r in raw:
            if r.get('huella_lectores')!=huella:errores.append(f"{r['id']}: auditoría de otra versión del lector")
            if r.get('errores'):errores.extend(f"{r['id']}: {e}" for e in r['errores'])
            if not r.get('inventario_vigente'):errores.append(f"{r['id']}: inventario desactualizado")
        por_pieza[raw[0]['codigo']]=[balance_documento(r) for r in raw]
    by_id={d['id']:d for docs in por_pieza.values() for d in docs}
    with sqlite3.connect(BD.resolve().as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        expected={r[0] for r in con.execute('SELECT id FROM documento')}
        if set(by_id)!=expected:errores.append('Inventario incompleto')
        # Profile reader renders only into a temporary directory, never into originals.
        from app.ingestion.profile_pdf import read_pdf
        with tempfile.TemporaryDirectory(prefix='inteplast-perfiles-') as td:
            for m in con.execute('SELECT * FROM medida_contorno'):
                d=by_id[m['documento_id']]
                actual=read_pdf(original(d['ruta']),Path(td),0.3,str(d['id']))
                fields=('tol_inf','tol_sup','desv_inf','desv_sup','infr_inf','infr_sup','media')
                mismatches=[k for k in fields if not iguales(actual.get(k),m[k])]
                if mismatches:errores.append(f"{d['id']}: perfil discordante {mismatches}")
                d['perfil_contorno']={'campos_contrastados':list(fields),'coinciden':not mismatches,'pagina':m['pagina'],'sha256':m['sha256']}
                d['tratamiento']='perfil_contorno_contrastado'
        identidad=recoger(con)
        inventario=informe(con)
    for docs in por_pieza.values():
        for d in docs:errores.extend(validar_balance(d))
    if errores:raise ValueError('\n'.join(errores[:60]))
    (CONOCIMIENTO/'ingesta'/'validacion-3167.json').write_text(json.dumps(piloto,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    totals={}
    for codigo,docs in por_pieza.items():
        escribir_jsonl(CONOCIMIENTO/'ingesta'/'balances'/f'{codigo}.jsonl',docs)
        if codigo!='sin_pieza':totals[codigo]=ficha(codigo,docs,identidad,inventario)
    cabecera=['# Contratos de ingesta por pieza','','Contraste técnico completado el 02/11/2026. Piloto: [3167](3167.md). Las 21 fichas tienen balance por documento y hoja, casos originales y reglas de exclusión. La revisión documental no sustituye una aprobación corporativa.','','| Pieza | Documentos | Hojas | Salida Excel | Medición utilizable | Generado | Sin confirmar | CSV | PDF |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for codigo,c in totals.items():cabecera.append(f"| [{codigo}]({codigo}.md) | {c['documentos']} | {c['hojas']} | {c['salida']} | {c['utilizables']} | {c['generado']} | {c['sin_confirmar']} | {c['csv']} | {c['perfiles']} |")
    cabecera+=['','Inventario: 4.529 archivos asignados a las 21 piezas y [1 documento general sin código](balances/sin_pieza.jsonl): **4.530 en total**. Los recuentos son por archivo, antes de priorizar CSV/fusionar/deduplicar en la app.','','[Lecciones y vínculos preparados para la app](lecciones-para-app.json): 10 notas y 6 grupos de vínculos revisados documentalmente, conservando evidencia y estado. La fuente editable sigue siendo `hallazgos.jsonl`.','','Reproducción: `auditar_ingesta.py` → `cerrar_fichas.py` → `verificar_aceptacion.py`. Originales y biblioteca en lectura; solo se escriben la auditoría derivada y las fichas.']
    (CONOCIMIENTO/'ingesta'/'README.md').write_text('\n'.join(cabecera)+'\n',encoding='utf-8')
    print(json.dumps({'piezas':len(totals),'documentos':len(by_id),'resumen':totals},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
