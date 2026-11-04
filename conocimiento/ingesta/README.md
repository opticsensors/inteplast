# Contratos de ingesta por pieza

Contraste técnico completado el 02/11/2026. Piloto: [3167](3167.md). Las 21 fichas tienen balance por documento y hoja, casos originales y reglas de exclusión. La revisión documental no sustituye una aprobación corporativa.

| Pieza | Documentos | Hojas | Salida Excel | Medición utilizable | Generado | Sin confirmar | CSV | PDF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [2820](2820.md) | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| [3051](3051.md) | 122 | 28 | 17724 | 14188 | 0 | 3536 | 0 | 0 |
| [3056](3056.md) | 160 | 44 | 27871 | 21430 | 0 | 6441 | 0 | 0 |
| [3167](3167.md) | 701 | 133 | 123265 | 120680 | 0 | 2585 | 0 | 0 |
| [3168](3168.md) | 322 | 73 | 30343 | 28538 | 0 | 1805 | 0 | 0 |
| [3174](3174.md) | 291 | 245 | 313665 | 192425 | 57164 | 57266 | 684 | 0 |
| [3186](3186.md) | 158 | 51 | 52380 | 41073 | 0 | 11307 | 0 | 0 |
| [3195](3195.md) | 193 | 62 | 119927 | 110635 | 0 | 9292 | 0 | 0 |
| [3197](3197.md) | 203 | 20 | 14670 | 12752 | 0 | 1918 | 7680 | 0 |
| [3202](3202.md) | 214 | 27 | 13584 | 12913 | 0 | 671 | 0 | 0 |
| [3205](3205.md) | 373 | 87 | 73365 | 57756 | 0 | 15459 | 0 | 0 |
| [3206](3206.md) | 241 | 105 | 34006 | 27998 | 984 | 4991 | 0 | 0 |
| [3212](3212.md) | 253 | 23 | 13227 | 10396 | 0 | 2831 | 5460 | 144 |
| [3214](3214.md) | 137 | 40 | 2756 | 2676 | 0 | 80 | 0 | 0 |
| [3218](3218.md) | 350 | 688 | 1007775 | 665837 | 262392 | 79490 | 0 | 0 |
| [3226](3226.md) | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| [3233](3233.md) | 128 | 235 | 71854 | 70729 | 1112 | 13 | 0 | 0 |
| [3237](3237.md) | 339 | 111 | 31548 | 24517 | 0 | 7031 | 0 | 0 |
| [3238](3238.md) | 180 | 69 | 22438 | 14297 | 0 | 8141 | 0 | 0 |
| [3288](3288.md) | 105 | 25 | 30751 | 19366 | 0 | 11385 | 0 | 0 |
| [3309](3309.md) | 43 | 26 | 11356 | 6632 | 0 | 4724 | 0 | 0 |

Inventario: 4.529 archivos asignados a las 21 piezas y [1 documento general sin código](balances/sin_pieza.jsonl): **4.530 en total**. Los recuentos son por archivo, antes de priorizar CSV/fusionar/deduplicar en la app.

[Lecciones y vínculos preparados para la app](lecciones-para-app.json): 10 notas y 6 grupos de vínculos revisados documentalmente, conservando evidencia y estado. La fuente editable sigue siendo `hallazgos.jsonl`.

Reproducción: `auditar_ingesta.py` → `cerrar_fichas.py` → `verificar_aceptacion.py`. Originales y biblioteca en lectura; solo se escriben la auditoría derivada y las fichas.
