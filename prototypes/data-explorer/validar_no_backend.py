"""Replay frozen OCR tokens through the prototype and backend No. readers.

Reuses known development and validation documents; this is NOT a new holdout or
a fresh OCR run. Reports position/number parity and the previously reviewed errors.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'backend'))
import lectores_planos as prototype
from app.ingestion.numbered_marks import proposals, MIN_MARKS


def center(mark):
    box = mark['box']
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def same(mark, other):
    x, y = center(mark)
    return mark['page'] == other['p'] and mark['candidates'][0]['label'] == 'N'+other['t'] and abs(x-other['x']) < .012 and abs(y-other['y']) < .012


def measure():
    development = HERE / 'out/probar-numerados-2026-11-10'
    report = json.loads((development / 'informe.json').read_text(encoding='utf8'))
    output = []
    files = list((development / 'lecturas').glob('*.json')) + list((HERE / 'out/validar-numerados-2026-11-13/lecturas').glob('*.json'))
    for file in files:
        data = json.loads(file.read_text(encoding='utf8'))
        pages = data.get('detalle', {}).get('ocr', [])
        if not pages:
            continue
        marks, reference = [], []
        for page in pages:
            tokens = page['tokens']
            number = page['pagina']
            reference += [m for m in prototype.marcas_de_tokens(tokens, number) if m['via'] == 'No.']
            marks += proposals([{'text': t['texto'], 'polygon': t['q'], 'score': t['s']} for t in tokens], number)
        old = [m for m in data.get('detalle', {}).get('marcas', []) if m['via'] == 'No.']
        bad = []
        reviewed_removed = []
        if file.parent.parent == development:
            for failure in report['planos'].get(file.stem, {}).get('fallos', []):
                if failure['ubicacion'] == 'mal':
                    mark = data['lecturas'][int(failure['id'].split('-')[1])]
                    if mark['via'] == 'No.':
                        bad.append({'id': failure['id'], 'still_offered': any(same(m, mark) for m in marks)})
            decisions = json.loads((development / 'revision.json').read_text(encoding='utf8'))['decisiones']
            for key, decision in decisions.items():
                if key.startswith('L' + file.stem + '-') and decision.get('numero') == 'bien' and decision.get('ubicacion') == 'bien':
                    mark = data['lecturas'][int(key.split('-')[1])]
                    if mark['via'] == 'No.' and not any(same(m, mark) for m in marks):
                        reviewed_removed.append({'id': key, 'label': mark['t'], 'note': decision.get('nota', '')})
        output.append({'document': data.get('doc', file.stem), 'path': data.get('ruta'), 'old_no': len(old), 'prototype_no': len(reference), 'backend_no': len(marks), 'offered': len(marks) if len(marks) >= MIN_MARKS else 0,
                       'parity_missing': sum(not any(same(m, r) for m in marks) for r in reference),
                       'parity_extra': sum(not any(same(m, r) for r in reference) for m in marks),
                       'known_wrong_locations': bad, 'previously_reviewed_readings_removed': reviewed_removed})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = measure()
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'documents': len(results), 'parity_missing': sum(r['parity_missing'] for r in results), 'parity_extra': sum(r['parity_extra'] for r in results), 'known_wrong_locations': [f for r in results for f in r['known_wrong_locations']], 'no_documents': [r for r in results if r['old_no'] or r['backend_no']]}, ensure_ascii=True))
