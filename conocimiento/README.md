# Conocimiento de los datos de Exemples

Todo lo que sabemos de los datos que entrega INTEPLAST (`Exemples`): qué contienen, cómo se
organizan, qué significan, qué diferencias hay entre features y piezas, y qué no cuadra.
**No es parte de la aplicación**: es el contexto para entender los datos y mejorar la app.
La documentación de la app sigue en `docs/`.

## Qué hay aquí

| Ruta | Qué es | En Git |
|---|---|---|
| [AVANCE.md](AVANCE.md) | Estado de la lectura de Exemples y qué queda pendiente | ✅ |
| [comparativa.md](comparativa.md) | Diferencias entre features y piezas: esqueleto, formatos, plantillas | ✅ |
| [incongruencias.md](incongruencias.md) | Lo que no cuadra o habría que pedir a INTEPLAST, con evidencia | ✅ |
| [hallazgos.jsonl](hallazgos.jsonl) | Un registro por hallazgo o incongruencia: afirmación, fuentes (ruta, SHA-256, localizador), estado | ✅ |
| [formatos-parsing.md](formatos-parsing.md) | Formatos del 3212 columna a columna (CSV CMM, XLS PPAP, PPTX) | ✅ |
| [visores.md](visores.md) | Los visores de `prototypes/data-explorer/` y lo que confirmaron | ✅ |
| `0-bolt-eye/` … `7-planitudes/` | Una carpeta por feature: `README.md` del feature y fichas de pieza (`3212/` en detalle) | ✅ |
| `herramientas/` | Inventario, extracción, perfiles y consultas (Python) | ✅ |
| `datos/biblioteca.sqlite` | Inventario + contenido extraído de todos los ficheros | ❌ (datos del cliente) |
| `.venv/` | Entorno de las herramientas (`--system-site-packages`) | ❌ |

## Cómo se consulta (lo primero antes de abrir originales)

```bash
PY=conocimiento/.venv/Scripts/python.exe
$PY conocimiento/herramientas/consultar.py estado                      # cobertura y errores
$PY conocimiento/herramientas/consultar.py arbol "2- Nervios de Soldadura" --pieza 3205 --detalle
$PY conocimiento/herramientas/consultar.py buscar '"tool correction" AND rib*' --feature "2- Nervios de Soldadura"
$PY conocimiento/herramientas/consultar.py ver <id|ruta> [--desde 0 --n 20]
$PY conocimiento/herramientas/consultar.py celdas <id> --hoja "DR(tapa)" --filas 12-20
$PY conocimiento/herramientas/consultar.py sql "SELECT … FROM perfil_ppap …"
```

Tablas: `documento` (un fichero, con feature/pieza/carpeta normalizada, estado y SHA-256),
`elemento` (texto con localizador: diapositiva, página, fila de hoja, línea), `celda` (hojas y CSV con
coordenada), `estructura` (huella por fichero), `elemento_fts` (búsqueda de texto completo).
Derivadas: `perfil_ppap`, `perfil_correccion`, `globo`, `celda_aleatoria` (celdas con `RAND()`: no son
medidas, I-003), `auditoria` (resultado de `verificar.py`) y `lectura_dr`/`medida_dr` (prototipo de
lector PPAP generalizado: una fila por hoja y una por valor, con marcas; ver
[docs/ingesta-automatica.md](../docs/ingesta-automatica.md)).

🔴 Antes de dar por buena una cifra de un libro, comprobar que la celda no está en `celda_aleatoria`:

```sql
SELECT d.ruta, a.hoja, count(*) FROM celda_aleatoria a JOIN documento d ON d.id = a.documento_id
WHERE d.codigo = '3237' GROUP BY 1, 2;
```

## Cómo se actualiza

```bash
$PY conocimiento/herramientas/inventariar.py        # metadatos; no abre ficheros
$PY conocimiento/herramientas/extraer.py            # solo lo nuevo, cambiado, con error o con lector nuevo
$PY conocimiento/herramientas/perfil_ppap.py
$PY conocimiento/herramientas/perfil_correcciones.py
$PY conocimiento/herramientas/globos_icp.py
$PY conocimiento/herramientas/formulas_aleatorias.py   # abre con Excel los xls con token RAND
$PY conocimiento/herramientas/verificar.py --n 10       # muestra al azar contra los originales
$PY conocimiento/herramientas/lector_dr.py              # medidas PPAP con reglas deterministas
```

- `extraer.py` **lee los originales y descarga los que estén solo en la nube**. Nunca escribe en
  Exemples; Word/Excel por COM trabajan sobre copias temporales.
- La base usa diario clásico (no WAL) porque está en OneDrive. Si se corrompe, borrar
  `datos/biblioteca.sqlite` y regenerar: los Markdown y `hallazgos.jsonl` no dependen de ella.
- Subir la versión de un lector en `lectores.py` hace que esos ficheros se vuelvan a extraer.

## Reglas al documentar

- Cada afirmación numérica sale de un fichero leído; citar ruta y localizador (hoja!celda,
  diapositiva, página, línea). Las conclusiones importantes van también a `hallazgos.jsonl`.
- Si la cifra clave de un hallazgo se puede recalcular con SQL, añadir `"comprobacion": {"sql": …,
  "esperado": [...]}`; `verificar.py --hallazgos` la recalcula junto con rutas, SHA-256 e ids. Pasarlo
  después de tocar la biblioteca o los Markdown.
- Antes de usar un valor de un libro, comprobar que no está en `celda_aleatoria` (I-003).
- Separar lo extraído de lo interpretado. Una propuesta de corrección no prueba ejecución.
- Los N-numbers son locales a cada plano: no unir cotas de piezas distintas por el número.
