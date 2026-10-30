# Cotas, planos y correcciones en la web

Integración del 18/09/2026; separación de lectores y simplificación de la interfaz del
21/09/2026. Los prototipos se conservan en `prototypes/data-explorer/` y no forman parte de la web.
**Implementación revisada el 26/10/2026, sin ejecutar pruebas ni reimportar datos.**
Esta es la ficha técnica de cotas, mediciones y evidencia; la ampliación a otras
plantillas se propone en [ingesta automática](ingesta-automatica.md).

## Navegación

La consulta parte del catálogo y de las fichas de pieza/feature. Las reglas de
pantalla, filtros, gráficas y navegación se mantienen en [interfaz.md](interfaz.md),
en particular [COTAS en el feature](interfaz.md#cotas-dentro-de-una-pieza-del-feature),
[página de cotas](interfaz.md#página-de-cotas) y
[consulta del plano](interfaz.md#consulta-del-plano).
Importar mediciones no crea vínculos automáticos entre cotas y features; esos
vínculos se eligen explícitamente y conservan su revisión.

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
| `MeasurementImport` (`measurement_models.py`) | Lote interpretado de CSV/tablas y snapshot base del piloto, con pieza, revisión, muestreo, cavidad, huella y autor; los cambios añaden versiones. |

El adaptador de correcciones es **específico del piloto 3212**, identificado por
código `3212` y carpeta `3212 Pump Housing` (`pilot.py`). Sus lectores propios están en
`backend/app/ingestion/pilot_3212/`: 16 CSV, catálogo completo de evaluaciones,
cuatro casos contrastados, acciones PPTX, previsiones XLS, perfiles A/B y referencias a TXT.
El modelo, la navegación, las asociaciones y el buscador PDF son reutilizables. El lector
CSV por bloques de `backend/app/ingestion/measurement_csv.py`, junto al lector automático
descrito abajo, permite incorporar mediciones de otras piezas con formatos compatibles.
No ejecuta el adaptador del 3212 sobre
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

La selección de origen se amplió a SharePoint el 22/10/2026. Su configuración y
validación con el entorno de INTEPLAST se siguen en
[ficheros externos](ficheros-externos.md#sharepoint-microsoft-graph).

1. Nueva pieza abre una ficha vacía en `/parts/nueva` y permite seleccionar una carpeta
   con el diálogo de Windows o el navegador SharePoint, según el origen configurado.
   La detección usa rutas,
   extensiones y metadatos para proponer CAD, escaneo, molde y plano, sin leer su contenido.
   Las cuatro propuestas se pueden cambiar antes de guardar.
2. El usuario puede cambiar título, descripción, código, cliente y propuestas, añadir
   features y más archivos de la carpeta con nombre y tipo propios. Crear registra una
   nueva pieza, guarda su lista en `PartFile` y los principales en `PartReference` y
   `PartDocument`, y prepara las mediciones. Si la carpeta ya existe, se ofrece abrir
   su ficha. Cancelar descarta todo el borrador.
3. `automatic_measurements.py` incorpora CSV individuales/comparativos y tablas DR de
   informes PPAP XLS/XLSX, sin revisión manual por archivo. Busca la revisión en la ruta
   y en cabeceras `Drawing…Level`; la ruta tiene prioridad. Si falta, reutiliza la única
   revisión encontrada para ese muestreo o, si este no tiene ninguna, para el conjunto.
   Es una regla de agrupación, no una confirmación documental de cada archivo.
   Conserva las condiciones de temperatura, presión, boquilla y repetición que reconoce.
   Sin contexto suficiente usa `sin-revision`, `sin-cavidad` o un identificador de archivo
   para el muestreo. Los CSV prevalecen sobre resúmenes XLS de
   las mismas cotas y contexto. Dos exports individuales discrepantes conservan series
   separadas con procedencia. Las tolerancias ausentes en un CSV comparativo se recuperan
   del XLS del mismo contexto solo si cota, nominal y límites son inequívocos.
   Una pieza sin mediciones también se registra y aparece en el catálogo.
4. Actualizar datos repite la lectura por acción explícita. Los grupos sin cambios se
   omiten; los cambios generan versiones consultables, incluso si se recuperan bytes de
   una versión anterior. La ficha permanece abierta y muestra los archivos utilizados,
   progreso, fecha e incidencias. Consultar el resumen no vuelve a importar datos.
5. Las correcciones del 3212 se preparan con su adaptador cuando están los originales.
   Los documentos de retoques de otras piezas se detectan internamente; su interpretación
   sigue pendiente y se indica en el resultado de lectura. No se inventan correspondencias
   ni previsiones. DR(100%) y carpetas de retoques se excluyen de mediciones. Estado y
   requisitos para otras piezas en la
   [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx).
6. Añadir pieza en Features ofrece solo registros existentes e incorpora sus referencias
   al vincularla por primera vez, respetando las filas existentes. Añadir cota permite
   escoger explícitamente qué cotas pertenecen al feature y de qué revisión.

El lector automático limita cada tabla a 16 MB y el conjunto a 128 MB; los originales
se leen mediante el [adaptador de origen](ficheros-externos.md). Cada observación
conserva archivo y línea CSV o celda XLS/XLSX. El
piloto 3212 conserva sus identidades CMM y su adaptador de XLS/correcciones. Los CSV de
puntos espaciales no son tablas de cotas y se omiten. El contraste registrado en
septiembre de la 3197 obtuvo 60 coincidencias en 60 valores muestreados (30 CSV y
30 XLS). Ejemplos: `Support_intern.02/
135ºC/500bar/3197 C1.csv`, línea 2, y cabeceras/celdas de `3197-00_intern.02.xls!DR_PAR`.

`measurement_tables.py` lee resultados guardados, sin recalcular fórmulas. Usa
`xlrd` para XLS y XML para XLSX; no incorpora el lector alternativo, la detección de
fórmulas aleatorias ni el reconocimiento del PDF con extensión XLS de
`conocimiento/`. Solo lee tablas con el nombre de hoja y las cabeceras reconocidos;
la exclusión de `100%` es una regla del lector, no una prueba de que toda hoja así
nombrada sea una previsión. Estas limitaciones y su ampliación están en
[ingesta automática](ingesta-automatica.md).

El refresco explícito del estudio piloto avanza la base actual y conserva snapshots
anteriores. Las comparaciones nuevas esperan la revisión de mediciones pendientes.
Una publicación ordinaria del adaptador no sustituye por sí sola la base congelada.

### Contrato de importación CSV con revisión explícita

La API de `measurement_imports.py` sigue disponible, separada del flujo automático
de Crear/Actualizar datos. Sus límites y decisiones no deben atribuirse a ese flujo:
la ruta automática conserva exports discrepantes como series separadas; esta API
exige elegir un export completo por combinación de revisión/muestreo/cavidad.

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
No se importa ninguna pieza real durante el despliegue. Hay tests con datos sintéticos
y el contraste puntual de la 3197 registrado arriba. Queda pendiente la validación
representativa de otras plantillas y de su interpretación; 60 coincidencias no
validan el conjunto completo de esa pieza ni de `Exemples`.

### API de cotas y mediciones

Rutas autenticadas bajo `/api/v1`; la especificación OpenAPI es la referencia del
contrato completo. Código: `api/routes/evidence.py`, `measurement_imports.py`,
`part_setup.py` y `files.py`.

| Ruta | Función |
|---|---|
| `GET /evidence/metrology`, `GET /evidence/metrology/filters` | Catálogo y filtros ligeros. |
| `GET /evidence/parts/{part_id}` | Estudio, cotas, documentos y revisiones; admite `revision` y `snapshot_id`. |
| `POST /parts/register`, `POST /parts/{part_id}/refresh` | Alta y actualización automática descritas arriba. |
| `POST /evidence/parts/{part_id}/import` | Encola exclusivamente el estudio del adaptador piloto. |
| `POST /evidence/parts/{part_id}/measurements/preview` y `/import` | Revisión e incorporación explícita de CSV. |
| `GET /evidence/parts/{part_id}/measurements/history` | Versiones de mediciones y snapshots conservados. |
| `GET /evidence/features/{feature_id}/parts/{part_id}` | Cotas vinculadas y números pendientes del feature. |
| `PUT /evidence/features/{feature_id}/parts/{part_id}/characteristics` | Asigna explícitamente una cota/revisión. |
| `DELETE /evidence/features/{feature_id}/characteristics/{characteristic_id}` | Retira el vínculo. |
| `GET /evidence/drawings/{file_id}`, `POST …/index`, `PUT …/review` | Consulta, preparación y revisión del índice del plano. |
| `GET /files/{file_id}/table` | Tabla original de solo lectura. |

## Lectura de resultados

La interacción de las gráficas y la selección de tramos se mantienen en
[interfaz: gráficas y detalle](interfaz.md#gráficas-y-detalle). Aquí se conserva su
significado técnico:

- Correcciones compara los tramos intern.01/.03/.05/.08 del piloto. Las acciones
  vinculadas de ambos planes se consultan también fuera de los cuatro casos
  cuantitativos. Un tramo sin documentación conserva las mediciones sin inventar
  una acción. La pantalla indica que la ejecución no está confirmada.
- Los puntos de la gráfica de mediciones enlazan a su origen; el detalle de
  correcciones aún no ofrece ese enlace por punto.
- El visor de CSV/XLS/XLSX muestra hojas, filas y columnas originales en solo lectura, con
  buscador precargado, salto y resaltado de la línea/celda guardada. Resuelve también los
  bloques CMM repetidos del piloto por aparición y fila; no atribuye una coincidencia solo
  por compartir cota. Los Excel muestran resultados guardados, sin recalcular fórmulas.
  El historial del navegador conserva la consulta. Los originales ausentes o modificados
  muestran un error, sin sustituirse por otra versión. La vista admite 16 MB, 20.000 filas,
  512 columnas y 500.000 celdas en total; pagina la cuadrícula de 80 en 80 filas.
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

### Lector de globos (30/10/2026)

El índice usa el lector del prototipo de búsqueda en planos, portado a `backend/app/ingestion/`
(`drawing.py`, `balloon_reader.py` y `drawing_version.py`). Reproduce exactamente sus lecturas,
comprobado en 5 planos reales. Cómo funciona:
- **Dónde se buscan los globos:** en la capa vectorial cuando el PDF los trae como vectores sobre
  el escaneo (infra-CONVERT); si no, en la imagen original. Se decide globo a globo, también en
  páginas mixtas.
- **Detector:** dos pasadas, con el tamaño típico de los globos de ese plano, y orientación
  automática de la página.
- **Lectura:** RapidOCR y el lector propio, una CRNN pequeña en ONNX entrenada solo con números
  sintéticos, votan; después se asigna un número a cada globo, sin repetir números en el plano.
- **Umbral provisional por fuente:** 0,434 en la capa vectorial y 0,6072 en la imagen. Por
  debajo, el globo queda sin lectura y no aparece en la búsqueda. Cada lectura guarda su
  procedencia (`Combinado`, `RapidOCR`, `Lector propio`) y cada globo su `fuente`.
- **Lector no disponible:** si falta el modelo o sus metadatos, o no se pueden cargar/validar,
  se localizan los globos sin ofrecer números automáticamente y se muestra un aviso.
  La búsqueda en el texto del plano sigue funcionando. No se recurre a RapidOCR solo, cuyos
  resultados no están validados con los umbrales del combinado.
- **Caché:** la identidad del lector (versión, huellas del ONNX y del JSON, y umbrales) forma parte de la
  clave del índice. Al cambiar el lector, la consulta devuelve `empty` con «El plano o su lector
  han cambiado: prepara de nuevo la búsqueda». La versión del índice pasa a 4 con esta corrección.
- **Revisiones:** los identificadores de candidato derivan de la caja detectada, así que mejorar
  el detector los cambia. Se respetan primero las revisiones cuyo identificador sigue existiendo.
  Una revisión antigua solo se reasocia si hay un único globo compatible en su página y ninguna
  otra revisión antigua compite por él (el centro revisado debe caer dentro de su caja).
  Si ese globo ya se ha revisado con su identificador actual, esa revisión prevalece y su
  predecesora deja de mostrarse. Las revisiones ambiguas o sin correspondencia siguen apareciendo
  como «Revisada» en su posición guardada, sin depender de las detecciones del índice.
  La consulta no modifica ni borra las filas guardadas.

Comprobación de estas correcciones (30/10/2026): **336 tests del backend en Docker aislado**,
**30 pruebas de la consulta de pieza/plano** (incluidas las revisiones sin correspondencia en
escritorio y móvil), compilación del frontend, Ruff y lint sin errores. Cliente TypeScript
regenerado sin cambios de contrato. Imagen de desarrollo `backend:latest` reconstruida.

Medición en el prototipo, con los umbrales actuales:
- Grupo B (3202, 3288 y 3167): **84,8 % de cobertura y 1,2 % de errores** entre las lecturas
  evaluables ofrecidas.
- 3212, escaneo de baja resolución: ofrece 114 de 253 globos (111 correctos).

**Limitaciones:**
- Hay lecturas ofrecidas sin verificar: 64 en ese banco, sin referencia.
- El 3202 «G», con negritas muy gruesas, falla más.
- Solo se detectan globos verdes o azules.
- No se ha demostrado que generalice a planos nuevos: los planos actuales sirvieron para diseñarlo.
- Un número por plano y un tamaño de globo dominante por página son supuestos.

Detalle en `prototypes/data-explorer/README.md` y `conocimiento/planos-globos.md`.

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
- Las mediciones y correcciones se importan al registrar una pieza y mediante **Actualizar
  datos** en su ficha. Admin queda reservado a la gestión de usuarios; se ha retirado el
  bloque de importación de la pieza piloto. Nunca se publican resultados si las fuentes
  cambiaron mientras se procesaban.
- El lector prepara los ficheros de metrología y retoques en una carpeta temporal del
  contenedor: evita miles de accesos pequeños al montaje de Windows. Se elimina al terminar;
  no incluye los directorios de CAD/escaneados grandes.
- Originales enlazados mediante los adaptadores local o SharePoint de solo lectura,
  descritos en [ficheros externos](ficheros-externos.md). Imágenes derivadas en el volumen
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
La actualización de datos se inicia desde la ficha de la pieza. No se modifican los originales.

## Validación de la nueva consulta (21/09/2026)

**Registro histórico.** Las tres secciones de validación siguientes conservan las
comprobaciones documentadas en septiembre. No se han repetido en la revisión del
26/10/2026 y no describen necesariamente la interfaz o el lector actuales. En
particular, el flujo automático posterior admite CSV comparativos y sustituye la
antigua revisión de importación desde la pantalla.

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
