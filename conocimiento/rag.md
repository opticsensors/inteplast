# RAG local de conocimiento

Recuperación con citas sobre lo que sabemos de `Exemples`, para agentes de desarrollo. Combina
búsqueda **semántica** (embeddings), **literal** (FTS5 e identificadores) y **acceso exacto** de solo
lectura a la biblioteca. La generación la hace el agente que consulta: no hay chat ni segundo modelo.

No forma parte de la aplicación ni depende de ella (ni de su PostgreSQL ni de sus importadores).
No escribe en `biblioteca.sqlite` ni abre los originales de `Exemples`. Nada sale del equipo:
el modelo corre en Ollama local.

## Uso

```bash
PY=conocimiento/.venv/Scripts/python.exe
R=conocimiento/herramientas/rag.py
$PY $R estado [--verificar] [--json]               # índice, modelo, frescura, cobertura, últimas construcciones
$PY $R buscar "consulta" [--json] [--modo hibrido|lexico|semantico] [--n 10] [--por-fuente 3]
     [--coleccion conocimiento] [--pieza 3212] [--feature 0] [--vigencia vigente]
     [--tipo-fuente cad] [--documento 123] [--estado-hallazgo abierta] [--fts]
$PY $R ver <id> [--contexto 2] [--json]             # fragmento completo, otras apariciones y vecinos
$PY $R exacto medidas --pieza 3212 --cota N170 [--hoja H] [--cavidad c13] [--max 200] [--json]
$PY $R exacto celdas <id|ruta> [--hoja H] [--filas 10-40] [--max 500] [--json]
$PY $R exacto hallazgo I-003 [--comprobar] [--json]
$PY $R exacto cadena --pieza 3212 [--cota N170] [--json]  # correccion -> medidas de origen y validacion
$PY $R exacto sql "SELECT …" [--max 200] [--json]
$PY $R glosario [--contar] [--json]                 # conceptos del glosario y documentos que contienen cada termino
$PY conocimiento/herramientas/evaluar_rag.py [--k 5] [--sin-glosario] [--registrar]   # preguntas con respuesta conocida
$PY $R consultar arbol "0- Bolt Eye" --pieza 3212   # pasa a consultar.py, cuya CLI no cambia
$PY $R construir [--solo-lexico] [--forzar] [--lote 16]
```

Antes de construir o de usar el modo semántico, Ollama debe estar en marcha con `embeddinggemma`
(`ollama serve`, o la aplicación de Ollama). Sin Ollama, `buscar` responde en modo léxico y lo avisa.

Flujo recomendado para un agente: `buscar --json` → citar `ruta` + `localizador` del resultado →
`ver <id>` si hace falta contexto → `exacto …` para cualquier cifra, con los filtros que muestra
`alcance`. El top-k **no es un inventario**: `completo` es siempre `false`.

## Arquitectura

| Pieza | Qué hace |
|---|---|
| `herramientas/rag_fuentes.py` | Segmenta las fuentes en fragmentos con procedencia; clasificación de vigencia; menciones |
| `herramientas/rag.py` | Construcción, índice, búsqueda, fusión, `ver`, `exacto` y CLI |
| `herramientas/test_rag.py` | Pruebas con fixtures temporales y embeddings simulados |
| `datos/rag/indice.sqlite` | Índice publicado (fuera de Git) |
| `datos/rag/cache_embeddings.sqlite` | Vectores por espacio vectorial y SHA-256 de la entrada; sobrevive a un fallo |
| `datos/rag/registro.jsonl` | Una línea por construcción: parámetros, resultado, error, duración |

Sin dependencias nuevas: `sqlite3`, `urllib` y `numpy` (del Python del sistema, visible desde
`conocimiento/.venv` por `--system-site-packages`). El volumen (≈9.300 vectores de 768 dimensiones,
unos 29 MB en float32) no justifica una base vectorial: el coseno se calcula con NumPy sobre los
vectores normalizados que pasan los filtros.

### Índice

- `texto`: contenido único, entrada exacta enviada al modelo, `sha` (SHA-256 de esa entrada) y vector.
  Textos idénticos comparten un vector.
- `aparicion`: cada ocurrencia con su procedencia completa: `clave` estable, colección, tipo de fuente,
  ruta (`repo` o `Exemples`), título, sección, localizador, documento, feature, pieza, códigos de pieza,
  carpeta, revisión y su origen, vigencia y clasificación, naturaleza, estado del hallazgo o del documento,
  SHA-256 del original (de la biblioteca, no recalculado), duplicado de, vecinos (`grupo`, `orden`),
  texto retirado, motivo de no tener vector, avisos y datos (evidencia, comandos exactos).
- `mencion`: identificadores normalizados (`N170`, `I-003`, `intern.06`, `DR(SKETCH)`, códigos de
  pieza conocidos). Son **menciones**: no asignan pieza, revisión ni cavidad al fragmento.
- `fts`: FTS5 (`unicode61 remove_diacritics 2`) sobre contenido y contexto (título, sección, ruta).
- `meta`: esquema, receta, modelo, fusión, huellas de las fuentes, cobertura y errores.

### Colecciones y tratamiento

| Colección | Fuente | Naturaleza | Vigencia | Vector |
|---|---|---|---|---|
| `conocimiento` | Fichas `.md` de `conocimiento/` | `interpretacion` | `vigente` o `revision_fechada` | sí |
| `historial` | `AVANCE.md`, `0-bolt-eye/otros-proyectos.md` | `interpretacion` | `historial` | sí |
| `hallazgos` | `hallazgos.jsonl`, un registro (partido si es largo) | `hallazgo` + `estado_hallazgo` | `vigente` | sí |
| `docs` | `docs/*.md`, documentación de la aplicación | `aplicacion` + `estado_doc` | `vigente` o `historial` | sí |
| `biblioteca` | `elemento`: páginas, diapositivas, párrafos y tablas de Word, correos, resúmenes `.prf`, listados de comprimidos | `extraido` | `no_aplica` | si tiene ≥ 20 letras y ≥ 30 % de letras; si no, solo literal |
| `tablas` | Tarjeta por libro/CSV (hojas, tamaños, disponibilidad de fórmulas) y por hoja con `lectura_dr` o `perfil_ppap` (cabecera, plantilla, papel, recuentos) | `derivado` | `no_aplica` | sí |
| `cad` | STEP/STP, STL, DXF, IGS, CATIA y nubes TXT: tarjeta con metadatos y geometría que ya extrajo la biblioteca; los listados `PRODUCT` (> 400 caracteres) y cabeceras (> 300) que la tarjeta recorta van completos en `cad:<id>#productos<n>` / `#cabecera<n>` | `derivado` (tarjeta), `extraido` (textos) | `no_aplica` | sí |
| `inventario` | Documentos sin otra representación (imágenes, vídeos, escaneos, binarios, texto solo en filas) y los pendientes de extraer o con error | `inventario` | `no_aplica` | no |

Las **filas de hoja, líneas de texto y cadenas de binarios** (≈ 878.000 elementos) no se copian
ni reciben vector: la búsqueda literal las consulta en el `elemento_fts` de la biblioteca actual y
las devuelve como `indexado: false`. Los números y fórmulas se obtienen con `exacto`. Un
`--tipo-fuente` que las nombra (`elemento:fila`, `elemento:lineas`, `elemento:cadenas` o `elemento`)
mantiene esa búsqueda; cualquier otro tipo la excluye.

**Estado de los documentos.** Solo aportan contenido los documentos con extracción vigente
(`extraido`, `solo_metadatos`, `sin_texto`). Uno `eliminado` desaparece del índice, de la búsqueda
literal y de `exacto`. Uno `pendiente` o en `error` conserva en la biblioteca elementos de una
extracción anterior que ya no corresponde al fichero: queda solo como tarjeta de `inventario` con
su motivo, igual que sus duplicados. `estado` cuenta por tipo los elementos que quedan fuera por esto.

**Segmentación.** Markdown por encabezados (ignorando `#` dentro de bloques de código), en bloques
de párrafo, tabla o código de hasta 1.400 caracteres; una tabla partida repite su cabecera en cada
parte. El localizador es `ruta#ancla (lineas a-b)`. Los tachados `~~…~~` se conservan como
`[RETIRADO: …]` y marcan `retirado: true`. Las tablas de Word partidas también repiten su primera fila.

**Duplicados.** Los 39 documentos `duplicado` no tienen elementos propios: heredan los fragmentos de
su original vigente con su propia ruta, pieza y documento (`clave …@d<id>`, `duplicado_de`). Los
filtros se aplican a las apariciones **antes** de agrupar, así un duplicado se encuentra filtrando por
su pieza. En las filas literales la biblioteca busca en el original, pero el resultado lleva la
procedencia de la aparición (original o duplicado) que cumple **todos** los filtros, y las demás en
`otras_apariciones`.

**Revisión.** Solo se rellena cuando la fuente la declara de forma estructurada: el `drawing_level`
de la cabecera PPAP (`perfil_ppap`), con `revision_origen`. No se deduce de nombres ni de fechas.
Un error de Excel en esa celda (`#REF!`, `#N/A`…) deja la revisión vacía con el aviso
«revision desconocida». La cavidad no se asigna como metadato.

### Vigencia (clasificación explícita)

La vigencia es independiente del estado del hallazgo (`abierta`, `explicable`, `resuelta`… son su
ciclo de vida, no su antigüedad). Se clasifica por fichero en `rag_fuentes.VIGENCIA`:

| Fichero | Vigencia | Motivo |
|---|---|---|
| `conocimiento/AVANCE.md` | `historial` | Registro de trabajo; sus cifras no son el estado actual |
| `conocimiento/0-bolt-eye/otros-proyectos.md` | `historial` | Inventario de agosto; su nota remite a las fichas actuales |
| `conocimiento/0-bolt-eye/3212/revision-2026-09-17.md` | `revision_fechada` | Citada como evidencia por fichas vigentes; puede estar superada |
| `docs/revision-*.md`, `docs/acta-reunion-2026-09-24.md` | `historial` | Sección «Historial» de `docs/README.md` |
| Resto de `conocimiento/` | `vigente` (por defecto) | `README.md`: las fichas temáticas recogen el conocimiento vigente |
| Resto de `docs/` | `vigente` + `estado_doc` | Estado que da la tabla de `docs/README.md` |

Un fichero nuevo con nombre fechado (`revision-AAAA-MM-DD`, `acta-…`) se marca `revision_fechada`
por regla; la clasificación (`explicita`, `regla`, `por defecto`) acompaña cada resultado.
El historial no se oculta: se etiqueta y pesa la mitad en la fusión, para no esconder contradicciones.

### Embeddings

| Parámetro | Valor |
|---|---|
| Proveedor | Ollama local (`http://127.0.0.1:11434`, sin proxy); `RAG_OLLAMA_URL` y `RAG_MODELO` lo cambian |
| Modelo | `embeddinggemma:latest` (`embeddinggemma:300m-bf16`, 307,58 M parámetros, BF16) |
| Digest | `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1` |
| Dimensiones / contexto | 768 / 2.048 tokens |
| Entrada de documento | `title: <título o none> \| text: <contenido>` (como `backend/app/assistant/embeddings.py`) |
| Entrada de consulta | `task: search result \| query: <consulta>` |
| Truncado | `truncate: false`: un exceso de contexto es un error, nunca texto omitido en silencio |
| Espacio vectorial | `ollama:embeddinggemma:latest@85462619ee721b46:768:rag-v1` |

El espacio vectorial (modelo + digest + dimensiones + receta) es la clave de la caché y del índice:
nunca se mezclan vectores de modelos distintos. En cada búsqueda se compara con el modelo activo; si
no coincide, la parte semántica se desactiva con aviso. La versión de Ollama se registra, pero no
forma parte de la clave. La huella de cada vector es el SHA-256 de la entrada completa (título,
texto y prefijo). Si una entrada excede el contexto, queda solo literal y se cuenta en `estado`.

Cambiar de modelo: `RAG_MODELO=<modelo> … construir` recalcula todos los vectores en otro espacio.
`RECETA` forma parte del espacio vectorial: subirla invalida **todos** los vectores (2,5 h en este
equipo), así que solo se sube si cambia lo que recibe el modelo para todos los textos (prefijos,
formato del título). Cualquier otro cambio de segmentación o metadatos lo detecta la huella de
fragmentos: el índice se reescribe y solo se calculan los textos nuevos. Cambiar las reglas de
menciones: subir `MENCIONES` (reescribe el índice sin recalcular vectores).

### Búsqueda y fusión

1. **Filtros** sobre `aparicion` (colección, pieza por código, feature, vigencia, tipo de fuente,
   documento, estado del hallazgo). Un hallazgo transversal (`feature: *`) entra en cualquier feature.
2. **Listas**: semántica (coseno, hasta 60), literal FTS5 (términos sin palabras vacías, en OR),
   menciones exactas (rango compartido por empate: una mención es binaria), identidad propia
   (`I-003` → su registro) y filas literales de la biblioteca (FTS en AND y, si hace falta, en OR).
3. **RRF** (`k = 60`): `Σ peso / (60 + rango)`. Pesos: semántica 1, literal 1, mención 2,
   identidad propia 3, fila literal 0,6 y fila con el identificador exacto 2. Factores: `historial`
   0,5, `revision_fechada` 0,8, `inventario` 0,5 y `tablas` 0,5 (27/10/2026: sus tarjetas repiten la misma
   cabecera en `cav_1…cav_n` y en cada copia del libro, y con `--pieza 3167` ocupaban 7 de 8 resultados).
   Desempate estable por clave.
4. **Agrupación**: un resultado por texto (con `otras_apariciones`), como máximo `--por-fuente`
   (3) por fichero o documento y uno por hallazgo.

La similitud expresa relevancia, no certeza factual.

### Glosario multilingüe (27/10/2026)

Los originales están sobre todo en inglés y catalán; las preguntas, en castellano. `venteo` no aparece en
ningún original y `venting`, en 12 documentos: sin ampliar la consulta, ni la búsqueda literal ni la
semántica (`embeddinggemma`) encontraban esas diapositivas. `conocimiento/rag/glosario.json` (propuesta
pendiente de validar) agrupa por concepto los términos en ES/CA/EN/DE/CS; `herramientas/glosario.py`:

- Un término **dispara** su concepto si aparece como palabra o frase en la consulta (sin mayúsculas ni
  acentos; `créixer*` es prefijo). Los de `solo_destino` (`draft`, `flash`, `burn the`) se añaden pero no
  disparan: son ambiguos. Como máximo 24 términos añadidos por consulta.
- La expresión FTS en OR (índice y filas de la biblioteca) recibe los términos añadidos; la AND literal no.
- La parte semántica calcula en **una** llamada el vector de la consulta y el de la consulta ampliada y
  usa la mayor similitud de los dos.
- El JSON trae `expansion` (concepto, disparadores, términos) y el texto imprime `Glosario: …`.
  `--sin-glosario` lo desactiva. El índice no cambia: solo la consulta.

### Resultado JSON

`modo_pedido` / `modo_efectivo` (`hibrido`, `lexico`, `semantico` o `null`), `filtros`, `indice`
(fecha, modelo, frescura), `avisos`, `listas` (tamaño de cada señal), `resultados`, `completo: false`
y `nota`. Cada resultado trae `id`, `coleccion`, `tipo_fuente`, `indexado`, `naturaleza`, `vigencia`,
`clasificacion`, `ruta`, `localizador`, `titulo`/`seccion`, `documento_id`, `feature`, `codigos`,
`revision`, `estado_hallazgo`/`estado_doc`, `retirado`, `duplicado_de`, `sha256_original` (original),
`sha_fragmento` (contenido indexado), `avisos`, `extracto`, `puntuacion` (rrf, rango por señal,
similitud), `otras_apariciones` y `siguiente` (comandos `ver` y `exacto`). Los hallazgos traen su
`evidencia`. Las filas literales (`indexado: false`) traen la procedencia de la aparición que cumple
los filtros (`bib:e<elemento>` o `bib:e<elemento>@d<duplicado>`, con `duplicado_de`) y
`otras_apariciones`.

`ver <id>` devuelve el fragmento completo, sus otras apariciones, la frescura del índice y el
contexto: vecinos del mismo fichero en el índice o, para texto de la biblioteca, elementos vecinos de
la biblioteca actual. Antes de combinarlos comprueba que los elementos del fragmento siguen iguales
(id, documento y texto completos guardados al construir, no el fragmento: así no hay falsas
discrepancias por partes, cabeceras de tabla repetidas o duplicados) y que el documento conserva su
SHA-256 y un estado vigente. Si no, no adjunta contexto y lo explica en `aviso_contexto`.

| Aviso | Significado |
|---|---|
| `indice_desactualizado` / `indice_posiblemente_desactualizado` | Cambiaron fichas, hallazgos o biblioteca (o solo su fecha) desde la construcción |
| `embeddings_no_disponibles` | Sin Ollama, sin el modelo o con otro modelo: resultado **solo léxico** |
| `indice_incompleto` | Hay textos sin vector (índice `--solo-lexico` o entradas que exceden el contexto) |
| `sin_busqueda` | Modo semántico pedido y no disponible |
| `filtros_sin_fuentes` | Ninguna fuente indexada cumple los filtros (distinto de no encontrar nada); indica si las filas literales se buscaron aparte |
| `sin_resultados` | Hay fuentes, pero ninguna coincide |
| `cota_local` | La consulta trae un N-number sin `--pieza` |
| `geometria_parcial` | La consulta toca CAD/visual: solo hay metadatos y geometría parcial |
| `datos_no_extraidos` | La pieza filtrada tiene documentos sin contenido interpretado |

Errores (`{"error": código, "mensaje": …}` con `--json`, código de salida 2): `indice_ausente`,
`embeddings_no_disponibles`, `construccion_en_curso`, `fuentes_cambiadas`, `solo_lectura`,
`documento_ambiguo` (con `detalle.candidatos`), `documento_no_vigente`, `error`. Los límites
(`--n`, `--por-fuente`, `--max`, `--lote` ≥ 1; `--contexto` ≥ 0) se validan antes de llegar al SQL,
donde `LIMIT -1` significaría «sin límite».

## Acceso exacto

Todas las consultas abren la biblioteca con `mode=ro` y `PRAGMA query_only=ON`. El documento se
indica por id, ruta completa o final de ruta a partir de un separador (`Customer/3168-00_intern.15.xls`;
`%` y `_` son literales). Si varios ficheros comparten nombre no se elige ninguno: error
`documento_ambiguo` con los candidatos (en la biblioteca real, `3168-00_intern.15.xls` está en
`Interns` y en `Customer`, y su `C1!H28` vale 37,248 y 37,299). Un documento no vigente, o un duplicado cuyo
original no lo es, da `documento_no_vigente`; `exacto medidas --pieza` excluye sus filas y las
cuenta en `alcance.excluidas_no_vigentes`.

- `exacto medidas` lee `medida_dr` y lo marca como **derivado**: es la salida del prototipo
  heurístico `lector_dr.py`, que omite celdas vacías y no numéricas, normaliza códigos (`N170` → `170`,
  la consulta se normaliza igual), ordena tolerancias invertidas y descarta bloques secundarios.
  Cada fila trae la celda original (valor guardado, fórmula, si el formato conserva fórmulas), la
  marca (`aleatoria`, `cero`, `atipico`) y una clasificación: `generada_rand` si la celda tiene RAND,
  si no `indeterminada` con su motivo (papel de la hoja, cero, atípico). Ni `con_correccion` ni la
  ausencia en `celda_aleatoria` certifican medición, previsión o copia. Exige `--pieza` o `--documento`.
  No incluye los CSV de la CMM: para ellos, `exacto celdas`. `alcance` da filtros, total, documentos,
  hojas y si se truncó; sin filas, avisa de que eso no prueba que la cota no exista.
- `exacto celdas` distingue `sin_valor_guardado` (fórmula sin caché), `cero` y celda no listada
  (vacía o no extraída); marca las RAND y si el texto de las fórmulas está disponible (no en XLS BIFF).
  Un duplicado se lee desde su original, con aviso.
- `exacto hallazgo` devuelve el registro y, con `--comprobar`, ejecuta su `comprobacion.sql`.
- `exacto cadena` lee `cadena_correccion` (`herramientas/cadena_correcciones.py`): por cada cota citada
  en una diapositiva, el muestreo de origen (XLS de la carpeta del plan o de una subcarpeta con su número;
  si no hay, por fecha ±7 días) y el siguiente con valores nuevos, con recuento, valores evaluables (con
  nominal y dos tolerancias), mínimo, máximo, valores fuera y su proporción. Un muestreo es serie + número
  (`3168-00` y `3168-10` no se mezclan; `intern.122` es la versión 2 de `intern.12`); los `INF.NN` (entregas PPAP)
  no cuentan. Para saber si un informe repite otro compara las filas de la cota con sus valores utilizables (sin
  `RAND()`, ceros ni atípicos) por posición y, si no, por contenido: misma cavidad y muestra, la misma etiqueta de
  elemento cuando la hay en los dos lados (LEFT/RIGHT) y, sin etiqueta, filas de tres valores o más (un bloque
  duplicado en columnas cuenta una vez). Salta el que repite el bloque entero, aunque esté reordenado (I-001),
  marca `parcial` el que repite una parte, `herencia_indeterminada` si la correspondencia es dudosa y
  `sin_medidas_validas` si los informes posteriores solo traen valores excluidos. Cada copia lleva su fecha: el
  origen usa una copia no posterior a la corrección, la validación una no anterior, y se avisa si las copias de un
  muestreo tienen fechas distintas. Si la fecha del plan no cuadra con su XLS de origen, se avisa y, si la carpeta
  tiene una fecha que sí cuadra, se usa como estimada en `fecha_orden`, sin tocar `fecha_correccion`; si no, o si el
  plan no tiene fecha, el orden y la validez temporal de las copias quedan sin comprobar (`admisible: null`). Una corrección anterior de otro plan que ya parte de un
  muestreo posterior deja el vínculo `indeterminada` (3167, 3309 T3), sin elegir otro origen. Las copias del
  mismo muestreo con valores, nominales o tolerancias distintos se guardan en `alternativas`, y `depende_copia` = 1
  si la conclusión cambia según la copia (I-006, I-007). Una cota sin medidas propias usa sus subpuntos (`210` → `210.1`…`210.5`); una
  cita ambigua (`DIM. Nr.45,1`) se lee como subpunto o lista según lo que se mida, o se dejan las dos lecturas
  con aviso. Excluye `RAND()`, ceros y atípicos. Avisa de diapositivas copiadas de otra pieza (I-309). Muestra
  **secuencia, no causa**, y no incluye los CSV de la CMM. Una validación `parcial` mezcla valores nuevos y
  repetidos en sus cifras. Validada contra el 3212 (`historial-molde.md` §2 y §4) y el 3197
  (`0-bolt-eye/README.md`, N230 3,770–3,787 → 4,068–4,073).
- `exacto sql` (y la `comprobacion.sql` de los hallazgos) ejecuta con un autorizador de SQLite que
  solo admite lectura: `SELECT`/`WITH`, funciones y `PRAGMA` sin asignación o de esquema
  (`table_info`, `index_list`…). `ATTACH` (que crearía un fichero vacío aunque la conexión sea de solo
  lectura), escrituras y `PRAGMA x=valor` fallan con `solo_lectura`.

## Construcción y actualización

`construir` es explícito (no hay vigilancia) e idempotente:

1. Toma un cerrojo (`construir.lock`, con pid y equipo); uno huérfano de este equipo se recupera.
2. Calcula las **huellas** de las fuentes: SHA-256 de cada Markdown y de `hallazgos.jsonl`, tamaño y
   fecha de `biblioteca.sqlite`, y su **firma** (filas de `documento` con SHA-256, estado, lector y
   versión extraída; recuento de cada tabla salvo `celda`; última ejecución).
3. Recolecta los fragmentos. Si la huella de fragmentos, el modelo y las fuentes coinciden con el
   índice publicado, termina con `sin_cambios` sin tocarlo.
4. Calcula solo los vectores que faltan en la caché (lotes de 16, confirmados lote a lote).
5. Escribe un temporal con nombre único, pasa `PRAGMA integrity_check` y lo cierra.
6. Vuelve a calcular las huellas; si alguna fuente cambió durante la construcción, descarta el temporal
   (`fuentes_cambiadas`).
7. Sustituye el índice con `os.replace` (hasta 6 reintentos con espera creciente).
8. Registra el resultado en `registro.jsonl`, también si falla; el índice anterior queda intacto.

Como el índice se regenera entero a partir de la caché, un fichero modificado o eliminado no deja
fragmentos obsoletos. **Frescura**: cada búsqueda compara la fecha y el tamaño de las fuentes y, si
cambian, su SHA-256 o la firma; `estado --verificar` recolecta y compara todos los fragmentos.
OneDrive sincroniza `datos/rag/`, pero el cerrojo solo coordina este equipo: no construir a la vez en
dos equipos.

## Límites

- La vigencia se distingue por fichero (y tachado), no por afirmación: una ficha vigente puede
  contener un párrafo superado que no esté tachado.
- `revision` solo existe donde la cabecera PPAP la declara; la cavidad no se asigna; las menciones
  no son atributos.
- Algunas páginas PDF tienen caracteres mal decodificados (`n�`): corregirlo exige reextraer.
- Las filas de hoja solo se buscan por literal; el contexto semántico de las hojas está en las
  tarjetas de `tablas`. Solo tienen tarjeta propia las hojas con `lectura_dr` o `perfil_ppap`.
- CAD: recuentos de entidades, triángulos, vértices y cajas (de vértices en STEP), según el formato;
  sin consulta geométrica ni cálculos nuevos. Imágenes, vídeos y escaneos: solo inventario.
- Inventariar los 4.530 originales no equivale a cobertura semántica.
- `rag.py consultar sql` pasa a `consultar.py`, que no se ha modificado: abre la biblioteca con
  `mode=ro` pero sin el autorizador de `exacto sql`. Para SQL libre, usar `exacto sql`.
- El aviso `geometria_parcial` se dispara por palabras («plano», «caja», «3d»…): también con «plano A»
  como referencia de alineación. Es un aviso de más, no cambia los resultados.
- La interfaz admite otro recuperador (visual o geométrico) como una lista más en la fusión y una
  colección más, sin cambiar la salida.
- El glosario amplía por concepto, no traduce frases: una paráfrasis sin términos del glosario
  («no corregir en este loop y esperar» frente a *«Do not corrected… Wait»*) sigue dependiendo de la
  semántica. `conocimiento/rag/` no se indexa (investigación, glosario y preguntas de evaluación).

## Evaluación (27/10/2026)

`herramientas/evaluar_rag.py` busca las preguntas de `conocimiento/rag/preguntas.jsonl` con sus filtros y
mide en qué posición sale la primera fuente esperada (recall@k, MRR, por tipo y por conjunto). Las 40 del
conjunto `ajuste` sirvieron para ajustar el glosario; las 15 de `control` se escribieron después y no.
Con k = 5 y el índice del 27/10: código anterior 0,775 (ajuste) y 0,80 (control); código actual 0,975 y
0,933. El 28/10, con cuatro fichas nuevas en el índice, control 0,867: el fragmento correcto sale 1.º en
C-012, pero el evaluador no lo reconoce. Detalle, límites y fallos restantes en [rag/README.md](rag/README.md). `--registrar` añade el
resultado a `datos/rag/evaluacion.jsonl`.

## Pruebas

```bash
conocimiento/.venv/Scripts/python.exe -B -m unittest discover -s conocimiento/herramientas -p "test_*.py"
```

`test_rag.py` (23 pruebas) crea en un directorio temporal fichas, hallazgos, `docs/` y una biblioteca
con `esquema.sql`, y usa embeddings simulados (bolsa de palabras con hash estable). Comprueba:
segmentación y localizadores, cabeceras de tabla repetidas, `#` en código, tachados, vigencia y estado
de `docs/`; procedencia de la biblioteca, duplicados, tarjetas CAD/hoja/libro, revisión e inventario;
idempotencia (`sin_cambios`, `--forzar` sin vectores nuevos); cambios y bajas sin resultados obsoletos;
fallo a mitad con índice intacto, registro del error y reanudación desde la caché; fuentes cambiadas
durante la construcción; cerrojo activo y huérfano; identificadores exactos, filtros, transversales y
fila literal del CSV; fusión sin duplicados; modo sin embeddings y modelo distinto; desactualización;
`ver`; solo lectura; ausencia, cero, RAND y fórmulas no disponibles; medidas derivadas y su
clasificación. Al terminar cada prueba se comprueba que la biblioteca de la fixture no cambió
(las pruebas que simulan una actualización la modifican ellas mismas y renuevan la huella).

Regresiones de la revisión del 26/10/2026, una por fallo: nombre de fichero repetido (error con
candidatos, ruta inequívoca, `%`/`_` literales); documentos pendientes y eliminados y duplicados de
un original pendiente (fuera del índice, de las filas y de `exacto`); procedencia de filas literales
de un duplicado (pieza, documento y filtros cruzados); `ver` con elementos reutilizados o documento
cambiado, sin falsas discrepancias en partes, tablas con cabecera repetida y duplicados; listado
`PRODUCT` completo y encontrable; `--tipo-fuente elemento:fila`; `drawing_level = #REF!`; límites
negativos, `ATTACH`, `PRAGMA` de asignación, FTS5 y CTE recursivas bajo el autorizador.

Revisión del 27–28/10/2026 (26 pruebas en `test_rag.py`, 16 en `test_lectores.py`): el glosario encuentra
`venting` al buscar `venteo` y `--sin-glosario` no; un término de solo destino no dispara; una sola
llamada de embeddings para las dos consultas; `conocimiento/rag/` fuera del índice; hoja sin valores
marcada como plantilla; `exacto cadena` sin tabla derivada. En `test_lectores.py`: 21 formas reales de
citar cotas (`DIM.3320`, `DIM#6`, `Dim Nº630`, `dimension 3970`, `4100,1`, `3900.1.2.3…`, `rozměru 210`,
`dim.: 202`, listas escritas a mano) y la cadena con bloque heredado, XLS de la carpeta, subcarpeta `Old/`
ignorada y celdas `RAND()` excluidas; y el caso del 3309 (subcarpeta del plan 2, sin retroceso para el T3,
subpuntos, aviso de copia de otra pieza y de dos versiones del mismo muestreo, `INF.01` fuera). Tras la revisión
externa del 28/10/2026: series distintas, filas desplazadas, valores contenidos en el bloque anterior pero distintos
celda a celda (3218 cota 2402), copia que repite el muestreo anterior, valores sin tolerancia, contradicción de orden con
fechas desconocidas (3167), citas ambiguas resueltas con las medidas (3214 `45,1`) y nominales sin cota (`Dim 7,5+0,1`).

## Resultados medidos (2026-10-26)

Equipo: i7-1365U sin GPU, Ollama 0.40.9, `embeddinggemma:latest` (digest `85462619ee72…`, 768 dim,
BF16). Cifras de `registro.jsonl` y de `rag.py estado --verificar`.

| Medida | Valor |
|---|---|
| Primera construcción con embeddings | 8.943,6 s (~2 h 29 min): 8.628 vectores nuevos + 672 de la caché, ~1 texto/s |
| Correcciones de la revisión (textos CAD completos, `#REF!`) | 437 s con 244 vectores nuevos (9.297 reutilizados); después, varias cabeceras CAD: 18,6 s con 25 nuevos (9.528 reutilizados) |
| Reconstrucción con cambios, sin vectores nuevos | 28,5 s |
| Reconstrucción sin cambios (`sin_cambios`) | 3,5–6,8 s |
| Construcción `--solo-lexico` | 14 s |
| `indice.sqlite` / `cache_embeddings.sqlite` | 98,1 MB / 44,6 MB |
| Apariciones / textos únicos / con vector | 15.339 / 14.044 / 9.553 |
| Consulta híbrida desde la CLI (incluye arranque de Python) | 4,3–4,5 s |
| Pruebas (`test_lectores.py` + `test_rag.py`) | 32 OK (9 + 23); 37 OK (11 + 26) el 27/10/2026 |

Cobertura por colección (apariciones; *solo léxico* = sin vector, con motivo):

| Colección | Apariciones | Con vector | Solo léxico |
|---|---:|---:|---|
| conocimiento | 332 | 332 | 0 |
| historial | 31 | 31 | 0 |
| docs | 300 | 300 | 0 |
| hallazgos | 66 | 66 | 0 |
| cad | 1.045 | 989 | 56 (poco texto con letras): 734 tarjetas + 224 partes de 30 listados `PRODUCT` + 87 cabeceras completas de 87 ficheros |
| tablas | 2.932 | 2.932 | 0 |
| biblioteca | 9.217 | 5.976 | 3.241 (poco texto con letras) |
| inventario | 1.416 | 0 | 1.416: 598 con texto solo en `lineas` y 48 solo en `cadenas`; 412 imágenes; 245 PDF escaneados; 71 `Thumbs.db`; 20 duplicados sin contenido propio; 8 vídeos; 14 otros sin texto (caché de GPU, libros solo con imágenes, fichero vacío, bloqueo de Office) |

Los 4.530 documentos de la biblioteca quedan representados en alguna colección (cad 734, tablas 1.123,
biblioteca 1.257, inventario 1.416). Las 876.472 filas, 1.766 bloques de líneas y 202 cadenas no tienen
vector: se buscan por `elemento_fts`. De 5.356 páginas, 1.045 están vacías. Las 398 cabeceras están
cubiertas: 389 en tarjetas CAD (13 ficheros IGS/STEP tienen varias) y 9 en fragmentos. Hoy no hay
documentos `pendiente`, `error` ni `eliminado`.

Consultas reales (resumen del primer resultado):

| Consulta | Primer resultado |
|---|---|
| `buscar "rebabas en nervios de soldadura"` | `2-nervios-soldadura/README.md` (pendiente), luego H-401 y la historia de correcciones del 3205 |
| `buscar "como se corrige la planitud del plano A tras el muestreo"` | `3212/historial-molde.md` §2 (enlace corrección ↔ `intern.NN`), luego alineación del plano A |
| `buscar N170 --pieza 3212` | `3212/historial-molde.md` §4 (N170, mejora parcial); aviso `datos_no_extraidos` (2 documentos) |
| `buscar I-003` | `hallazgo:I-003` (señal `propio`), luego `incongruencias.md#i-003-en-detalle` |
| `buscar "pieza 3212 en STEP con caja de vertices" --coleccion cad` | `cad:330` (`3212.step` del molde), aviso `geometria_parcial` |
| `buscar "como se configura el acceso a SharePoint" --coleccion docs --json` | `docs/ficheros-externos.md`, `estado_doc` «Implementado; prueba real de SharePoint pendiente» |

Casos reales de la revisión, comprobados tras las correcciones:

| Caso | Resultado |
|---|---|
| `exacto celdas 3168-00_intern.15.xls` | `documento_ambiguo` con los candidatos 4312 (Customer) y 4336 (Interns) |
| `buscar "moldflow information available" --pieza 3226 --tipo-fuente elemento` (o `--documento 1575`) | `bib:e395907@d1575`, pieza 3226, `duplicado_de` el README del 3195 |
| `ver` sobre los 9.217 fragmentos de texto de la biblioteca | 0 discrepancias de identidad (incluye partes y 64 de duplicados) |
| `buscar "Postis sortida gasos" --modo lexico` | `cad:1818#productos36` (parte 36/36 del listado de `EXP 3205 22-4-25.step`) |
| `buscar N170 --pieza 3212 --tipo-fuente elemento:fila` | Filas de los CSV de la CMM del 3212 (`3212_totes.csv`, `3212_c13.csv`…) |
| `drawing_level = #REF!` (documentos 695, 769, 770) | Ninguna aparición con revisión `#REF!`; aviso «revision desconocida» |
| `exacto sql "ATTACH '…/zz_intruso.db' AS x"` / `--max -1` | `solo_lectura` sin crear el fichero / rechazado por la CLI |
| `exacto hallazgo I-001 --comprobar` (con el autorizador) | `coincide` (5079/5079) |

`biblioteca.sqlite` quedó intacta tras construir y consultar: mismo tamaño (1.243.066.368 B), fecha y
SHA-256 (`11775936c427…`) que antes de empezar.
