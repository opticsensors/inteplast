"""Classify the measured v6 omissions against the read-only knowledge library.

This is an audit, not an application reader. It never changes the library or originals.
Usage: python auditar_omisiones.py --output out/plan-2026-11-16/omisiones.json
"""

import argparse
import collections
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def audit():
    con = sqlite3.connect(f"file:{(ROOT / 'conocimiento/datos/biblioteca.sqlite').as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    baseline = json.loads((ROOT / 'out/conocimiento/prueba-web/2026-11-13-sin-ia/resumen.json').read_text(encoding='utf8'))
    result = []
    for piece in baseline['results']:
        for file in piece.get('diagnostics', []):
            for sheet in file.get('sheets', []):
                if not sheet.get('reason') or not sheet.get('nominal_header_rows'):
                    continue
                path = piece['folder'] + '/' + file['path']
                doc = con.execute('select id,duplicado_de from documento where ruta=?', (path,)).fetchone()
                if not doc:
                    raise ValueError(f'No library provenance: {path}')
                canonical = doc['duplicado_de'] or doc['id']
                cells = [dict(r) for r in con.execute('select fila,col,valor,numero,formula from celda where documento_id=? and hoja=?', (canonical, sheet['sheet']))]
                header = next((c for c in cells if c['fila'] <= 30 and str(c['valor']).strip().lower() in {'nominal', 'target'}), None)
                body = [c for c in cells if header and c['fila'] > header['fila']]
                nominal_rows = {c['fila'] for c in body if c['col'] == header['col'] and c['numero'] is not None}
                filled_nominals = [c for c in body if header and c['col'] == header['col'] and c['valor'] is not None and str(c['valor']).strip()]
                random = con.execute('select count(*) from celda_aleatoria where documento_id=? and hoja=?', (canonical, sheet['sheet'])).fetchone()[0]
                profile = con.execute('select papel,plantilla,filas_cota,valores from lectura_dr where documento_id=? and hoja=?', (canonical, sheet['sheet'])).fetchone()
                role = profile['papel'] if profile else None
                if not header:
                    decision = 'pendiente_discrepancia_biblioteca'
                elif not filled_nominals:
                    decision = 'excluir_plantilla_sin_nominales'
                elif random:
                    decision = 'pendiente_procedencia_aleatoria'
                elif role == 'comparativa':
                    decision = 'excluir_comparativa_como_medicion_nueva'
                elif role == 'bloques_secundarios':
                    decision = 'pendiente_contextos_secundarios'
                elif role == 'informe' and profile['valores']:
                    decision = 'candidata_importacion_con_adaptacion'
                else:
                    decision = 'pendiente_formato_o_identidad'
                result.append({
                    'piece': piece['code'], 'path': path, 'document_id': doc['id'],
                    'canonical_document_id': canonical, 'sheet': sheet['sheet'],
                    'v6_reason': sheet['reason'], 'header_row': header['fila'] if header else None,
                    'nominal_rows': len(nominal_rows), 'random_cells': random,
                    'filled_nominals': len(filled_nominals),
                    'library_profile': dict(profile) if profile else None,
                    'decision': decision,
                    'evidence_cells': [c for c in cells if header and c['fila'] in {header['fila'], min(nominal_rows, default=-1)}][:35],
                })
    letters = []
    for code in ['3056', '3167', '3195', '3214', '3233']:
        records = [dict(r) for r in con.execute("""
            select m.cota, count(*) observations, min(d.ruta) example_path,
                   min(m.hoja) example_sheet
            from medida_dr m join documento d on d.id=m.documento_id
            where d.codigo=? and m.cota glob '*[A-Za-z]*'
            group by m.cota order by count(*) desc
        """, (code,))]
        for record in records:
            record.pop('example_sheet')
            example = con.execute("""select d.ruta,m.hoja,m.fila,m.col,m.nominal,m.equipo
                from medida_dr m join documento d on d.id=m.documento_id
                where d.codigo=? and m.cota=? order by d.ruta,m.hoja,m.fila,m.col limit 1""", (code, record['cota'])).fetchone()
            record['evidence'] = dict(example)
            value = record['cota']
            record['class'] = (
                'zona' if code in {'3214', '3233'} and re.fullmatch(r'[A-Z]\d+', value)
                else 'evaluacion_o_repeticion_por_confirmar' if re.fullmatch(r'\d+(?:\.\d+)?\.?[A-Z]+\d*', value)
                else 'elemento_auxiliar' if value.startswith('~')
                else 'identificador_por_clasificar'
            )
        letters.append({'piece': code, 'identifiers': records})
    con.close()
    return {'baseline': 'v6 2026-11-13', 'unit': 'file + sheet (duplicates retained as paths)',
            'counts': dict(collections.Counter(r['decision'] for r in result)),
            'by_v6_reason': dict(collections.Counter(r['v6_reason'] for r in result)),
            'sheets': result, 'letter_identifiers': letters,
            'limits': 'Library profiles are evidence for triage, not independent measurement validation. No new format is imported by this audit. Missing RAND is not proof of measurement provenance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'counts': data['counts'], 'by_v6_reason': data['by_v6_reason']}, ensure_ascii=False))
