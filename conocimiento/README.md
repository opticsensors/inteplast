# Conocimiento de los datos de Exemples

Todo lo que sabemos de los datos que entrega INTEPLAST (`Exemples`): qué contienen, cómo se
organizan, qué significan, qué diferencias hay entre features y piezas, y qué no cuadra.
**No es parte de la aplicación**: es el contexto para entender los datos y mejorar la app.
La documentación de la app sigue en `docs/`.

## Entrada para una sesión sin contexto

1. Leer [comparativa.md](comparativa.md) para situar la pieza y su familia. **La app sigue
   con el piloto 3212**; la biblioteca ya cubre las ocho familias.
2. Abrir el README de esa familia y la ficha de la pieza. Para el piloto:
   [3212/README.md](0-bolt-eye/3212/README.md). Seguir solo los enlaces del tema que se necesita.
3. Consultar [trampas.md](trampas.md) antes de interpretar datos y buscar los IDs relevantes
   en [incongruencias.md](incongruencias.md) / [hallazgos.jsonl](hallazgos.jsonl).
4. Resolver cifras y localizar evidencia con `consultar.py` (abajo). Abrir el original concreto
   si falta detalle visual o hay contradicción; no hace falta releer todo `Exemples`.
5. Para desarrollar la aplicación, seguir el [índice de docs](../docs/README.md) y las instrucciones de `CLAUDE.md`.

Las fichas temáticas recogen el conocimiento vigente. `AVANCE.md` y las revisiones fechadas
son historial de trabajo: no usar una cifra antigua de cobertura como si fuera el estado actual.

## Referencias por tema

Cada tema tiene una ubicación de referencia para su detalle y evidencia. Los resúmenes
conservan la conclusión útil y enlazan aquí; una cifra corregida se mantiene en la ficha
propietaria. `hallazgos.jsonl` sigue siendo el registro estructurado verificable, no una
segunda explicación en prosa.

| Tema | Referencia que se actualiza |
|---|---|
| Inventario y diferencias entre familias | [Comparativa](comparativa.md); detalles propios en cada ficha de familia/pieza |
| Identidad, cabeceras PPAP y cavidades del 3212 | [Metrología: cabecera y excepciones](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro) |
| Revisión del plano 3212, fechas y limitaciones del escaneo | [Definición de pieza](0-bolt-eye/3212/1-pieza-2d-3d.md) |
| Correspondencia IGES/DXF/TXT y fechas de adquisición | [Metrología: soportes geométricos](0-bolt-eye/3212/4-metrologia.md#rectificación-dxf-equivalente-con-redondeo-iges-con-z-aplanada) |
| Columnas CSV y reglas de parsing | [Formatos y parsing](formatos-parsing.md) |
| Variantes PPTX y contenido de acciones del 3212 | [Retoques: qué fichero usar](0-bolt-eye/3212/5-retoques-molde.md#qué-fichero-usar) |
| Cronología y comparación antes/después | [Historial del molde](0-bolt-eye/3212/historial-molde.md) (3212, a mano); otras piezas: tabla `cadena_correccion` (`rag.py exacto cadena`) |
| Cliente, plano, nº de cliente e ITP de cada pieza | [Identidad de las piezas](identidad-piezas.md) (generada); cliente poco fiable: [I-005](incongruencias.md) |
| Vocabulario metrológico y ensayos | [Método de medida](0-bolt-eye/3212/6-metodo-medida.md) |
| Fórmulas aleatorias, procedencia y recuentos I-003 | [Incongruencias I-003](incongruencias.md#i-003-en-detalle) |
| Cómo regenerar y comprobar la biblioteca | [Cómo se actualiza](#cómo-se-actualiza); resultados fechados en [AVANCE](AVANCE.md) |
| Funciones implementadas y propuestas de la aplicación | [Índice de docs](../docs/README.md); no deducirlas de la cobertura de esta biblioteca |

## Qué hay aquí

| Ruta | Qué es | En Git |
|---|---|---|
| [AVANCE.md](AVANCE.md) | Estado de la lectura de Exemples y qué queda pendiente | ✅ |
| [comparativa.md](comparativa.md) | Diferencias entre features y piezas: esqueleto, formatos, plantillas | ✅ |
| [identidad-piezas.md](identidad-piezas.md) | Nombre, plano, nº de cliente, ITP, cliente y columnas de cavidad por pieza, con recuentos y valores anómalos. **Generado** por `identidad_piezas.py` | ✅ |
| [rag/](rag/README.md) | Investigación de arquitectura (27/10/2026), glosario multilingüe y preguntas de evaluación del RAG. No se indexa | ✅ |
| [incongruencias.md](incongruencias.md) | Lo que no cuadra o habría que pedir a INTEPLAST, con evidencia | ✅ |
| [hallazgos.jsonl](hallazgos.jsonl) | Un registro por hallazgo o incongruencia: afirmación, fuentes (ruta, SHA-256, localizador), estado | ✅ |
| [formatos-parsing.md](formatos-parsing.md) | Formatos del 3212 columna a columna (CSV CMM, XLS PPAP, PPTX) | ✅ |
| [visores.md](visores.md) | Los visores de `prototypes/data-explorer/` y lo que confirmaron | ✅ |
| `0-bolt-eye/` … `7-planitudes/` | Una carpeta por feature: `README.md` del feature y fichas de pieza (`3212/` en detalle) | ✅ |
| `herramientas/` | Inventario, extracción, perfiles y consultas (Python) | ✅ |
| `datos/biblioteca.sqlite` | Inventario + contenido extraído de todos los ficheros | ❌ (datos del cliente) |
| `datos/rag/` | Índice RAG, caché de embeddings y registro de construcciones ([rag.md](rag.md)) | ❌ (datos del cliente) |
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
Derivadas: `perfil_ppap`, `perfil_correccion` (cotas citadas normalizadas y su literal en `cotas_texto`),
`globo`, `celda_aleatoria` (celdas con `RAND()`: no son medidas, I-003), `auditoria` (resultado de
`verificar.py`), `lectura_dr`/`medida_dr` (prototipo de lector PPAP generalizado: una fila por hoja y una
por valor, con marcas; ver [docs/ingesta-automatica.md](../docs/ingesta-automatica.md)) y
`cadena_correccion` (cota corregida → medidas del muestreo de origen y del siguiente con valores nuevos;
secuencia, no causa: `rag.py exacto cadena`).

🔴 Antes de dar por buena una cifra de un libro, comprobar `celda_aleatoria`, su fórmula y
procedencia. La ausencia en esa tabla **no certifica que sea una medición**: puede depender de
una fórmula aleatoria, ser una copia como valores o una previsión de retoque.

```sql
SELECT d.ruta, a.hoja, count(*) FROM celda_aleatoria a JOIN documento d ON d.id = a.documento_id
WHERE d.codigo = '3237' GROUP BY 1, 2;
```

### Búsqueda con citas (RAG)

Una sola interfaz para buscar por significado y por literal en las fichas, `hallazgos.jsonl`,
la biblioteca y `docs/`, con procedencia y acceso exacto de solo lectura. Usa `embeddinggemma`
en Ollama local; sin Ollama la búsqueda se declara solo léxica. Referencia: [rag.md](rag.md).

```bash
R=conocimiento/herramientas/rag.py
$PY $R estado                                          # índice, modelo, frescura y cobertura
$PY $R buscar "rebabas en nervios de soldadura" --json # híbrida; filtros --pieza --feature --coleccion --vigencia
$PY $R buscar "N170" --pieza 3212                      # los N-numbers son locales a cada plano
$PY $R ver <id> --contexto 2                           # fragmento completo y vecinos
$PY $R exacto medidas --pieza 3212 --cota N170         # valores con celda original, fórmula y marcas
$PY $R exacto cadena --pieza 3197 --cota N230          # corrección → muestreo de origen y de validación
$PY $R construir                                       # incremental; tras cambiar fichas o biblioteca
$PY conocimiento/herramientas/evaluar_rag.py           # preguntas con respuesta conocida (rag/preguntas.jsonl)
```

Las consultas en castellano se amplían con el glosario de `rag/glosario.json` (los originales están
sobre todo en inglés y catalán); el resultado muestra la ampliación y `--sin-glosario` la desactiva.

Los resultados indican relevancia, no certeza, y no son un inventario: las cifras se citan
desde `exacto` (o `consultar.py`) con sus filtros.

## Cómo se actualiza

```bash
$PY conocimiento/herramientas/inventariar.py        # metadatos; no abre ficheros
$PY conocimiento/herramientas/extraer.py            # solo lo nuevo, cambiado, con error o con lector nuevo
$PY conocimiento/herramientas/perfil_ppap.py
$PY conocimiento/herramientas/perfil_correcciones.py
$PY conocimiento/herramientas/globos_icp.py
$PY conocimiento/herramientas/identidad_piezas.py      # reescribe identidad-piezas.md
$PY conocimiento/herramientas/formulas_aleatorias.py   # abre con Excel los xls con token RAND
$PY conocimiento/herramientas/verificar.py --n 10       # muestra al azar contra los originales
$PY conocimiento/herramientas/lector_dr.py              # medidas PPAP con reglas deterministas
$PY conocimiento/herramientas/cadena_correcciones.py    # después de perfil_correcciones y lector_dr
$PY conocimiento/herramientas/rag.py construir          # índice RAG al final
```

- `extraer.py` **lee los originales y descarga los que estén solo en la nube**. Nunca escribe en
  Exemples; Word/Excel por COM trabajan sobre copias temporales.
- La base usa diario clásico (no WAL) porque está en OneDrive. Si se corrompe, borrar
  `datos/biblioteca.sqlite` y regenerar: los Markdown y `hallazgos.jsonl` no dependen de ella.
- **I-003 e I-004 ya se resuelven en los lectores (versión 2).** Los XLSX/XLSM conservan las
  fórmulas sin valor guardado como NULL y distinguen las fórmulas del texto literal `=`.
  Un `.xls` con firma `%PDF-` se lee como PDF; `documento.lector` refleja el formato real y
  `version_extraida` conserva la versión del selector por extensión. Después de extraer,
  ejecutar `formulas_aleatorias.py` para reconstruir sus marcas. No requieren parches manuales.
  Esta reconstrucción lee cada XLS en un proceso de Excel aislado, con macros desactivadas,
  y solo sustituye `celda_aleatoria` cuando termina sin errores; si falla, conserva la tabla anterior
  y devuelve un código de salida de error. El resultado queda registrado en `ejecucion`.
- Subir la versión de un lector en `lectores.py` hace que esos ficheros se vuelvan a extraer.
- `verificar.py --semilla 20261023 --n 10` conserva las coordenadas y resultados de cada
  comprobación en `auditoria`, y los parámetros y cobertura en `ejecucion`. La semilla controla
  tanto la selección de documentos como la de celdas; el resumen distingue documentos con y
  sin muestra. Para repetir exactamente una selección deben mantenerse la biblioteca y los filtros.
  Contrasta las fórmulas y la presencia de valor guardado con el XML original; los perfiles PPAP/DR
  conservan la distinción entre ausencia de medida y cero.
- Pruebas de regresión de los lectores, sin tocar los originales ni la biblioteca:
  `conocimiento/.venv/Scripts/python.exe -B -m unittest discover -s conocimiento/herramientas -p "test_*.py"`.

### Rutas largas en Windows

Hay **38 JPEG de WhatsApp del 3205 con rutas de 260 caracteres o más**. Python y PowerShell
pueden enumerarlos, pero en este equipo (`LongPathsEnabled = 0`) abrirlos por la ruta ordinaria
falla. Las herramientas usan `comun.original()` / `comun.larga()` para leer con el prefijo
`\\?\`. Todo lector nuevo debe mantener ese soporte; listar un fichero no demuestra que pueda
abrirse. Esto también se debe comprobar al implementar la ingesta de la aplicación.

## Reglas al documentar

- Cada afirmación numérica sale de un fichero leído; citar ruta y localizador (hoja!celda,
  diapositiva, página, línea). Las conclusiones importantes van también a `hallazgos.jsonl`.
- Mantener el detalle y la evidencia en una ficha temática de referencia. Los resúmenes de
  familia, las trampas y `docs/` deben enlazarla, sin copiar todo el análisis. Si cambia un hecho,
  buscar también sus copias y el ID del hallazgo antes de cerrar la revisión.
- Si la cifra clave de un hallazgo se puede recalcular con SQL, añadir `"comprobacion": {"sql": …,
  "esperado": [...]}`; `verificar.py --hallazgos` la recalcula junto con rutas, SHA-256 e ids. Pasarlo
  después de tocar la biblioteca o los Markdown.
- Antes de usar un valor de un libro, comprobar que no está en `celda_aleatoria` (I-003).
- Separar lo extraído de lo interpretado. Una propuesta de corrección no prueba ejecución.
- Marcar una inferencia como **probable** o una duda como **pendiente** una vez, junto a la
  conclusión. Evitar repetir cautelas que no cambian cómo se usa el dato.
- Los N-numbers son locales a cada plano: no unir cotas de piezas distintas por el número.

## Alcance de la revisión del 23/10/2026

Dos pasadas sobre todos los Markdown y los 56 hallazgos anteriores, con contraste de originales
y una segunda revisión cruzada. El inventario y los SHA-256 de los 4.530 originales coinciden
con la biblioteca. La cobertura de inventario no implica lectura semántica completa: hay CAD,
imágenes, vídeos y comprimidos pendientes de interpretación. Resultados y límites en
[AVANCE.md](AVANCE.md#revisión-doble-del-23102026).
