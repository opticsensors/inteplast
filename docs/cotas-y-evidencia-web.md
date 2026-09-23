# Cotas, planos y correcciones en la web

Integración del 18/09/2026; separación de lectores y simplificación de la interfaz del
21/09/2026. Los prototipos se conservan en `prototypes/data-explorer/` y no forman parte de la web.

## Navegación

- **Catálogo** (`/features`) reúne tarjetas de piezas y features. Solo al buscar aparecen
  también cotas con pieza y revisión. Todo/Piezas/Features limita los tipos de tarjeta;
  Nueva pieza y Nuevo feature están juntos. `/parts` redirige al catálogo de piezas.
- La **ficha de feature** conserva el conocimiento transversal. En cada bloque de pieza
  aparece una fila **COTAS** con icono, números y acceso al plano, del mismo estilo y altura
  que los ficheros. El icono abre la búsqueda de esa cota; el número abre sus mediciones.
  En edición, Añadir cota inserta al final un selector de cotas importadas con revisión,
  o un campo manual si no hay mediciones. La papelera retira el vínculo. Los recuadros
  guardados conservan revisión y relación internamente, sin texto adicional en la fila.
  Las mediciones se preparan desde Nueva pieza/Actualizar datos; no crean asociaciones al feature.
- La **ficha de pieza** (`/parts/{id}`) muestra el CAD completo con ampliación interactiva,
  sus features y la sección Cotas, que reutiliza la consulta anterior de Metrología.
  La pieza queda fijada por la ficha. Feature tiene búsqueda interna; Categoría y Tag se
  despliegan desde Más filtros. Editar permite vincular features en la misma relación
  compartida que «Añadir pieza» del editor de features.
- La pieza abre la consulta sin seleccionar una cota arbitraria. El filtro Feature
  permite consultar todas sus cotas (también las no vinculadas) o solo las asignadas al
  feature de entrada. Las cotas sin mediciones siguen disponibles; pertenecer a la pieza
  no atribuye sus cotas a un feature que no las tenga vinculadas.
- La consulta usa el buscador superior compartido con
  Features, filtros independientes de Elemento/Altura/Evaluación y gráfica con cavidades
  activables. Plano, a la derecha del buscador, abre una página propia del archivo con
  el visor de Features. El enlace del PDF en la pieza usa la misma página. Atrás conserva
  la consulta anterior. Correcciones queda debajo a la izquierda.
  No hay pestañas ni listas de
  documentos, perfiles o nubes de puntos. Las reglas están en [interfaz.md](interfaz.md).
- La URL conserva pieza, búsqueda, feature, categoría, tag, cota, revisión, filtros, cavidades y modo de consulta. Atrás y Adelante
  restauran el contexto al visitar otra cota, una corrección o el plano. No hay enlaces de retorno.
- El **visor PDF existente** conserva zoom, arrastre y paginación. Su búsqueda ofrece propuestas
  OCR, texto nativo y ubicaciones revisadas; seleccionarlas encuadra y resalta la zona.
  Usa el buscador compartido; acepta prefijos y subcotas. Las coincidencias y su contador
  aparecen sobre el plano, sin columna lateral ni formulario de revisión.

`GET /evidence/metrology/filters` devuelve el catálogo ligero de piezas y features con
categoría, tags y pertenencia a piezas, sin snapshots de mediciones. La pertenencia feature/pieza une declaración explícita, ficheros y
vínculos de cotas; los números solo se obtienen de `FeatureCharacteristicLink`.
`GET /evidence/parts/{id}` incluye esos mismos features con sus cotas. El frontend cruza
las asociaciones y los filtros con el snapshot de esa pieza y su revisión; categoría y
tag deben coincidir en el mismo feature. Nunca muestra mediciones
de otra revisión para resolver un vínculo. Los cambios no alteran las asociaciones
ni importan datos de otras piezas.

Los N-numbers ya no son tags globales. La migración convierte los cuatro tags documentados
del Bolt Eye del 3212 en asociaciones a cotas rev. 06. Los demás números se conservan como
pendientes de asignación, sin inventar su pieza (en la instalación de estudio, `N0`). Las nuevas
altas/ediciones rechazan tags con forma de N-number. El buscador global sigue encontrando
features por las cotas vinculadas.

## Datos y alcance

`knowledge_models.py` añade:

| Entidad | Identidad / función |
|---|---|
| `PartCharacteristic` | Pieza + código N + revisión, únicos en conjunto. Existe sin marca en PDF. |
| `FeatureCharacteristicLink` | Asociación N:M con rol. La misma cota puede estar en varios features. |
| `PendingCharacteristic` | Identificadores heredados que aún no tienen contexto confirmado. |
| `PartDocument` | Original o imagen derivada compartido por la pieza. Protege su uso como evidencia. |
| `EvidenceJob` | Cola persistente y resultado de importación/indexación por versión. |
| `DrawingLocation` | Revisión humana de una ubicación, ligada a SHA-256, usuario y fecha. |
| `MeasurementImport` (`measurement_models.py`) | Export CSV interpretado e inmutable, con pieza, revisión, muestreo, cavidad, hash y autor; las sustituciones añaden versiones. |

El primer importador es **específico del 3212**. Sus lectores propios están en
`backend/app/ingestion/pilot_3212/`: 16 CSV, catálogo completo de evaluaciones,
cuatro casos contrastados, acciones PPTX, previsiones XLS, perfiles A/B y referencias a TXT.
El modelo, la navegación, las asociaciones y el buscador PDF son reutilizables. El lector
CSV por bloques de `backend/app/ingestion/measurement_csv.py` permite incorporar otra
pieza del mismo formato, con contexto revisado. No ejecuta el adaptador del 3212 sobre
otros proyectos ni deduce reglas de B/H/GX/LP por el número de cota.

El resultado importado se conserva como **snapshot JSON estructurado** en `EvidenceJob`,
con evaluaciones identificadas por bloque/ID CMM/fila y referencias a `StoredFile`.
El adaptador piloto sustituye el `payload` del mismo trabajo al reimportar
(`queue` y `process_next` en `backend/app/evidence.py`). El nuevo flujo CSV conserva
versiones en `MeasurementImport`; antes de la primera importación guarda también el
estudio piloto previo y lo usa como base estable. Las sucesivas reimportaciones del
adaptador piloto no sustituyen esa base ni las mediciones incorporadas por el nuevo flujo.
El historial general de entregas PPTX/XLS sigue pendiente. No se ha
implementado todavía el modelo completo normalizado de `MUESTREO`/`MEDICION`/eventos de
ejecución de retoques. El índice de acciones guarda cada acción una sola vez por identificador;
los casos y las cotas se refieren a ella. No se crean lessons learned automáticamente.

## Alta y actualización de piezas (22/09/2026)

1. Nueva pieza abre una ficha vacía en `/parts/nueva` y permite seleccionar una carpeta
   con el diálogo de Windows. La detección usa rutas,
   extensiones y metadatos para proponer CAD, escaneo, molde y plano, sin leer su contenido.
   Las cuatro propuestas se pueden cambiar antes de guardar.
2. El usuario puede cambiar título, descripción, código, cliente y propuestas, añadir
   features y más archivos de la carpeta con nombre y tipo propios. Crear registra una
   nueva pieza, guarda su lista en `PartFile` y los principales en `PartReference` y
   `PartDocument`, y prepara las mediciones. Si la carpeta ya existe, se ofrece abrir
   su ficha. Cancelar descarta todo el borrador.
3. `automatic_measurements.py` incorpora CSV individuales/comparativos y tablas DR de
   informes PPAP XLS/XLSX, sin revisión manual por archivo. Obtiene la revisión de las
   cabeceras y conserva temperatura, presión, boquilla y repetición en el muestreo.
   Si un contexto realmente falta, queda identificado como sin-revision/sin-cavidad;
   nunca se inventa una revisión o cavidad. Los CSV prevalecen sobre resúmenes XLS de
   las mismas cotas y contexto. Dos exports individuales discrepantes conservan series
   separadas con procedencia. Las tolerancias ausentes en un CSV comparativo se recuperan
   del XLS del mismo contexto solo si cota, nominal y límites son inequívocos.
   Una pieza sin mediciones también se registra y aparece en el catálogo.
4. Actualizar datos repite la lectura por acción explícita. Las mediciones existentes se
   omiten; los cambios generan versiones consultables, incluso si se recuperan bytes de
   una versión anterior. La ficha permanece abierta y muestra los archivos utilizados,
   progreso, fecha e incidencias. Consultar el resumen no vuelve a importar datos.
5. Las correcciones del 3212 se preparan con su adaptador cuando están los originales.
   Los documentos de retoques de otras piezas se detectan internamente; su interpretación
   sigue pendiente y se indica en el resultado de lectura. No se inventan correspondencias
   ni previsiones. DR(100%) y carpetas de retoques se excluyen de mediciones.
6. Añadir pieza en Features ofrece solo registros existentes e incorpora sus referencias
   al vincularla por primera vez, respetando las filas existentes. Añadir cota permite
   escoger explícitamente qué cotas pertenecen al feature y de qué revisión.

El lector automático limita cada tabla a 16 MB y el conjunto a 128 MB; los originales
se leen in situ. Cada observación conserva archivo y línea CSV o celda XLS/XLSX. El
piloto 3212 conserva sus identidades CMM y su adaptador de XLS/correcciones. Los CSV de
puntos espaciales no son tablas de cotas y se omiten. Contraste de la 3197: 60 valores
muestreados (30 CSV y 30 XLS) coinciden con sus fuentes. Ejemplos: `Support_intern.02/
135ºC/500bar/3197 C1.csv`, línea 2, y cabeceras/celdas de `3197-00_intern.02.xls!DR_PAR`.

El refresco explícito del estudio piloto avanza la base actual y conserva snapshots
anteriores. Las comparaciones nuevas esperan la revisión de mediciones pendientes.
Una publicación ordinaria del adaptador no sustituye por sí sola la base congelada.

Se reconoce el export CMM con bloques de cotas N y columnas separadas por `;`, nominal,
tolerancias y medición; decimales con punto o coma, UTF-8 o Windows-1252. Este formato
usa mm, salvo evaluaciones Phi en grados. Otros formatos se señalan como no compatibles;
las filas sin cota identificable no se atribuyen a otra cota. Para el 3212 rev. 06 se
mantienen las identidades CMM/N170 y GLOBAL/POINT ya revisadas. Las evaluaciones de otras
piezas conservan bloque, aparición, fila e ID CMM, sin fusionarlas por compartir número.

Cada export representa una revisión/muestreo/cavidad completos. Dos exports distintos
para esa misma combinación requieren elegir uno; no se combinan silenciosamente. Una
reimportación con el mismo contenido/contexto se omite, incluso con otro nombre de archivo.
Los nuevos muestreos se añaden, las revisiones se consultan por separado y sustituir valores
exige confirmación. El historial conserva los datos interpretados previos, accesibles
desde Consultar, y no vuelve a activar un archivo antiguo por importarlo de nuevo.

La revisión y el hash se verifican de nuevo al incorporar; si cambia el archivo o la
pieza/carpeta, hay que revisar de nuevo. Las importaciones de una pieza se serializan y
se guardan en una transacción. Límites: 250 CSV detectados, 10 MB por archivo y 64 MB por
selección. Solo se leen los CSV, sin recorrer el contenido de CAD o escaneos ni copiarlos.
No se importa ninguna pieza real durante el despliegue. La generalización se ha probado
con datos sintéticos; falta contrastar una segunda pieza real con metrología (A13).

## Lectura de resultados

- Correcciones conserva intern.01/.03/.05/.08 y permite seleccionar cada tramo pulsando
  su región dentro de la gráfica, que queda resaltada en gris. No hay botones de tramo
  debajo. Las acciones
  ya vinculadas de ambos planes se consultan incluso si la cota no pertenece a uno de los
  cuatro casos cuantitativos. Los tramos sin documentación conservan las mediciones.
- El detalle hace visible el cambio propuesto en el molde y compara, por cavidad, efecto
  previsto y cambio medido. No muestra imágenes ni «Documentos y valores de origen».
  Los controles mantienen su selección al volver del plano con el navegador;
  buscar en el dibujo no sustituye la búsqueda previa de cotas.
- Cavidad y valor aparecen al pasar el cursor, tocar o enfocar un punto; el recuadro queda
  junto a él. No se activa sobre zonas vacías ni incluye fuentes, límites o estados.
  No se repiten en tablas. La leyenda activa cavidades; el tramo seleccionado se resalta.
  La previsión se muestra en el detalle, separada de los muestreos reales de la gráfica.
- La previsión sigue siendo el valor **guardado** en `DR(100%)`, con celdas y deltas. No es
  una simulación ni se recalculan fórmulas de Excel en el navegador.
- El efecto previsto usa el valor inicial del XLS; el cambio medido usa las dos mediciones
  CSV de la evaluación seleccionada. No confundir esas bases si difieren. Las previsiones
  se muestran solo para las correspondencias revisadas de N161/N240/N170/N165 GLOBAL.
- Los estados corresponden a cada evaluación. GX y LP siguen separados, sin un resumen
  automático de cierre de toda la cota ni conclusiones de aceptación de la pieza.
- El catálogo conserva GLOBAL, medidas locales y diagnósticos con su identidad original;
  no agrega evaluaciones distintas ni une observaciones ausentes. N165 permite consultar
  GLOBAL, Escaneo y P01/P02… como elementos distintos. La comparación documentada de GLOBAL
  no se aplica a un punto local ni a una evaluación sin correspondencia.
- Los perfiles y referencias a TXT/PUNTS_NOUS siguen en los datos importados, pero no se
  muestran en la consulta de cotas. Los originales permanecen conservados.
- Una cota vinculada sin evaluaciones importadas muestra ese estado, sin sustituirla por otra.

## Indexación y revisiones

La primera búsqueda se prepara desde el visor. El servidor ejecuta `app.ingestion.drawing.build_index`
en un subproceso; OCR y extracción de números ocurren una vez por versión. Las propuestas
no se dan por verificadas. La revisión humana guarda número y ubicación del candidato
real del índice: el cliente no puede inventar coordenadas mediante ese endpoint.

Un cambio de `StoredFile.version` invalida el índice. Las revisiones anteriores se conservan
ligadas al hash, pero no se aplican a otros bytes. Los originales externos cambiados se
rechazan mediante el adaptador de archivos. **Plano rev. 07 y mediciones rev. 06 no tienen
equivalencia validada**: localizar un número no demuestra esa equivalencia.

El endpoint de revisión permite etiquetar las ubicaciones detectadas, incluidas las que no
tienen lectura. La pantalla de consulta ya no ofrece ese formulario; sigue usando las
etiquetas revisadas que existan para la versión actual.
No hay todavía herramienta para dibujar una ubicación nueva que el detector no haya encontrado.

## Ejecución y mantenimiento

- Los lectores de producción viven en `backend/app/ingestion/`: plano/OCR, CSV, perfiles
  PDF y adaptador 3212 para XLS/PPTX. Se han trasladado las reglas revisadas a módulos
  propios, sin interfaces HTML, lanzadores ni rutas personales de los prototipos.
- El conversor importa únicamente módulos del backend. Docker excluye `prototypes/`
  del contexto y no copia scripts de exploración. Plotly deja de ser una dependencia
  del backend; los visores experimentales mantienen sus dependencias locales.

- Nuevos endpoints autenticados bajo `/api/v1/evidence`: pieza, importación, asociaciones de
  feature/cota, índice PDF y revisión de ubicación. SDK TypeScript regenerado.
- Un trabajador con bloqueo asesor PostgreSQL serializa los trabajos costosos. Cola durable,
  recuperación tras reinicio, límite de 30 minutos por subproceso y errores reintentables.
  `EVIDENCE_WORKER_ENABLED=false` lo desactiva (incluido en la configuración de tests).
- `Reimportar archivos`, en **Admin → Datos de piezas**, conserva el adaptador piloto y calcula la firma de fuentes; si no
  cambiaron reutiliza la importación. La consulta de cotas no ofrece esa operación.
  Nunca publica resultados si las fuentes cambiaron mientras se procesaban.
- El lector prepara los ficheros de metrología y retoques en una carpeta temporal del
  contenedor: evita miles de accesos pequeños al montaje de Windows. Se elimina al terminar;
  no incluye los directorios de CAD/escaneados grandes.
- Originales enlazados con el adaptador local de solo lectura. Imágenes derivadas en el volumen
  de uploads, accesibles mediante los enlaces autenticados habituales. No se exponen `file://`
  ni rutas físicas del ordenador al navegador.
- Los originales incorporados como evidencia no se pueden borrar o volver a vincular sobre el
  mismo UUID. Si cambia el original, una nueva importación registra otro documento. Las
  referencias externas no archivan sus bytes: si el cliente reemplaza un original, la versión
  vieja puede dejar de estar accesible. El nuevo historial CSV sí conserva sus valores
  interpretados, aunque el original externo se sustituya; no archiva los bytes originales.
- La migración `f17a03c9de85` sucede a `f170a3c9de85` (nombres de adjuntos); su downgrade
  devuelve los identificadores a los tags para no perderlos.
- `g28b14daef96` corrige la lección de ejemplo que afirmaba que N170 estaba resuelta.
  Solo reemplaza el texto original exacto del seed; conserva cualquier edición del usuario.
  Un rollback de esquema no reintroduce esa conclusión incorrecta.

Despliegue local: `docker compose up -d --build db prestart backend`, frontend Vite habitual.
El botón de importación en Admin solo aparece para la carpeta piloto configurada. No se modifican
originales ni los otros proyectos del cliente.

## Validación de la nueva consulta (21/09/2026)

- Flujo CSV: pruebas en base aislada de contexto incompleto, hashes cambiados,
  duplicados, sustituciones, versiones anteriores, revisiones independientes, piezas
  compartidas sin asociaciones automáticas y conservación del estudio piloto previo.
  Pruebas de interfaz de importación/selección, escritorio/móvil y revisión histórica
  conservada al filtrar y navegar. TypeScript/Vite, Ruff, Mypy y Biome verificados.
- Contraste de solo lectura del nuevo lector con el catálogo 3212: 16 CSV individuales,
  3.120 filas asociadas a cotas, sin diferencias de valor ni límites. Las tres comparativas
  `totes` se rechazan por su estructura de columnas. Esta comprobación no importa datos
  en la aplicación ni valida el formato de una segunda pieza real.

- Fila COTAS: comprobación de altura frente a ficheros en lectura y edición, inserción
  al final, ajuste a varias líneas en móvil, enlaces al plano, duplicados, metadatos,
  cancelación, errores y Guardar del feature. 63 pruebas de edición/piezas verificadas;
  se ajustó la prueba de arrastre para comparar coordenadas del documento sin que el
  scroll altere el resultado. Compilación y revisión visual correctas.
- Simplificación de cabecera y correcciones: las 21 pruebas pasan con Plano alineado,
  sin saltos de anchura al activarlo; cierre y navegador restauran los filtros y el tramo.
  Se comprueban enlaces directos, regiones de gráfica con ratón/teclado/toque, valores
  solo sobre puntos y ausencia de imágenes/fuentes en el detalle. Revisión visual en
  escritorio y móvil; TypeScript/Vite compila.
- Evolución completa: 21 pruebas de selección de tramos, previsiones y cambios medidos,
  acciones de ambos planes, valores ausentes, teclado/móvil, historial y gestión de importación.
  Comprobación con el catálogo real: N170 C13/B1/H1,5/GX muestra +0,500 mm previstos frente
  a +0,545 mm medidos; .03→.05 y .05→.08 conservan los valores sin inventar acciones.
  N161, N165 y N240 muestran las acciones vinculadas de los planes 1 y 2.
- Segunda iteración: 17 pruebas de búsqueda, consulta y visores. Incluyen los prefijos
  N1/N11/N113, selección sin título duplicado, activación solo sobre puntos, recuadro junto
  al punto, cavidades solapadas/separadas y coincidencias del plano en escritorio/móvil.
  El buscador PDF real se comprueba con un visor sustituido para observar las coordenadas
  seleccionadas; las pruebas del visor PDF usan documentos sintéticos.
- 85 pruebas de componentes en serie, incluidas seis pruebas de navegador para la consulta
  de cotas en la primera iteración: filtros, valores interactivos, correcciones, plano,
  historial y móvil. Estas últimas usan datos sintéticos para aislar la navegación.
- Revisión visual en escritorio y móvil, teclado y toque; compilación TypeScript/Vite y
  Biome en los componentes modificados. Features sigue usando el mismo campo de búsqueda.
- Comprobación de los filtros sobre el catálogo real de referencia del 3212: 36 entradas,
  211 series accesibles sin colisiones y 21 evaluaciones con correspondencia de corrección.
  No se modifica ni reimporta el estudio para cambiar su presentación.

## Validación de la separación de lectores (21/09/2026)

- 178 pruebas del backend en la pila aislada, incluidas fuentes sintéticas CSV/PDF/PPTX,
  previsiones XLS, identidad de candidatos y un conversor ejecutado con solo código del
  backend. Las 22 pruebas de los prototipos pasan desde su nueva ubicación.
- Importación real con los módulos propios: 16 CSV, 144 perfiles y 54 acciones. Comparación
  del snapshot completo con `datos.json` del prototipo v3: 23.567 valores numéricos, sin
  diferencias en los datos (se ignoran las URL `file:` locales). Los originales se leen
  sin modificarlos y los resultados de esta comprobación se generan fuera del repositorio.
- Esta equivalencia comprueba la migración de los lectores, no valida la exactitud del OCR
  ni amplía el alcance del adaptador a otras piezas.

## Validación de la integración inicial (18/09/2026)

- 156 pruebas del backend en la base de datos aislada; 79 pruebas de componentes ejecutadas
  en serie para evitar la competencia entre los navegadores de las pruebas 3D.
- Compilación TypeScript/Vite, Ruff y Mypy; migración de ida y vuelta en la base de pruebas.
- Importación real del 3212: 16 CSV, 144 perfiles, 54 acciones, cuatro casos. Coincidencia de
  21.613 valores numéricos con la salida del prototipo v3 (casos, catálogo y medidas locales).
- Revisión en navegador de escritorio y móvil: navegación desde Bolt Eye, búsqueda y encuadre
  en el plano, N288 sin evaluaciones, correcciones y gráficas de perfiles. OCR: 263 ubicaciones
  detectadas; este conteo no es una validación humana de sus lecturas.
