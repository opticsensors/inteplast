# La aplicación web — base de conocimiento de features

> La prueba de concepto descrita en `inteplast_PADIH_fase_B.md`, implementada sobre la plantilla
> `full-stack-fastapi-template`: **backend** en `backend/`, **frontend** en `frontend/`.
>
> Este documento cubre **lo que se ha construido y por qué**. Las trampas de los datos crudos
> están en [formatos-parsing.md](formatos-parsing.md); el modelo del dominio completo (proyectos,
> muestreos, mediciones, correcciones de molde) en [modelo-datos.md](modelo-datos.md).

---

## Qué hay implementado

**22/09/2026:** **Catálogo** reúne piezas y features en `/features`, con cotas solo cuando
se escribe en el buscador. Nueva pieza y Nuevo feature están juntos. Cada pieza tiene ficha
con portada STEP completa ampliable en 3D, features vinculados y la consulta de metrología
reutilizada. Los vínculos se editan desde cualquiera de las dos fichas.

La ficha de feature mantiene el mismo reparto en consulta y edición: portada y datos
arriba, advertencias/lecciones a la izquierda y piezas con sus cotas a la derecha.
La documentación se consulta en la ficha de pieza, sin repetirla en el feature.
Las notas permiten adjuntar imágenes a su cuerpo Markdown (`![nombre](file:id)`),
reutilizando los archivos y las URL de acceso temporales existentes; no se guardan URL
caducables en el texto. Plegar el punto mantiene las subidas y borradores pendientes.

El alta se hace desde **Catálogo → Nueva pieza**. Propone nombre y
cuatro referencias desde una carpeta seleccionada en Windows e incorpora automáticamente
CSV CMM individuales/comparativos y tablas PPAP XLS/XLSX. **Actualizar datos** repite la lectura de forma
explícita. Features ofrece únicamente piezas registradas y reutiliza sus referencias al
asociarlas. La integración nativa local se describe en [ficheros-externos.md](ficheros-externos.md).
La interpretación de correcciones de otras piezas y la conexión Graph siguen pendientes.

El **bloque transversal** del modelo de datos: `FEATURE` + `WARNING` + `LESSON_LEARNED` +
ficheros de ejemplo. Es lo que consume el frontend descrito en la fase B y lo que responde a
*«dame todo del Bolt Eye»*.

Y desde el **2026-08-18**, la **pieza como entidad propia** (`Part`): los ficheros ya no cuelgan
del feature sueltos, cuelgan de la pieza a la que pertenecen. Es el embrión de `PROYECTO`.

Desde el **2026-09-15**, una ficha puede **vincular originales externos** sin subirlos. El PDF y
el STEP del 3212 están conectados y comprobados en la instalación local. Configuración, límites
de revisión y futura conexión Graph en [ficheros-externos.md](ficheros-externos.md).

Desde el **2026-09-18** hay catálogo de piezas, cotas por pieza/revisión, búsqueda de cotas
en el visor PDF con revisiones compartidas y una importación piloto de mediciones/correcciones
del 3212. Los lectores propios de `backend/app/ingestion/` guardan snapshots estructurados;
la web no depende de los visores de `prototypes/data-explorer/`. El modelo
completo normalizado de `MUESTREO`, `MEDICION`, `CORRECCION_MOLDE` y `DEPENDENCIA_COTA`
sigue pendiente. Alcance y funcionamiento en [Cotas y evidencia web](cotas-y-evidencia-web.md).

Desde el **2026-09-22**, Metrología incorpora tablas de otras piezas sin revisión archivo a
archivo. `MeasurementImport` conserva datos interpretados, hash,
contexto y versiones anteriores. El lector reutilizable está en
`backend/app/ingestion/measurement_csv.py` y `measurement_tables.py`; las reglas específicas
del piloto no se aplican a otra pieza por tener el mismo número de cota. La lectura de la
3197 se ha contrastado con 30 valores CSV y 30 XLS (60 coincidencias). La interpretación
de sus retoques sigue pendiente; los puntos de coordenadas no se importan como cotas.

---

## Modelo de datos (`backend/app/models.py`)

```
StoredFile                    identidad común de un documento subido o referenciado
  id, filename, content_type, size, created_at
  source = upload | local, source_key, source_path, source_version
  version (UUID del vínculo), revision (etiqueta), reference_key (deduplicación)

Part                          la pieza = el proyecto = el molde  → embrión de PROYECTO
  id, code ("3212", UNIQUE), name ("Pump Housing")

Feature                       la ficha del feature
  id, name, description, category, tags[], owner_id, image_id → StoredFile, cover_3d (JSON)
  ├─ FeatureNote (n)          kind = warning | lesson
  │    title, body (markdown reducido), position
  ├─ FeatureAsset (n)         kind = mold | part | scan | drawing | moldflow
  │    name, position, part_id → Part, file_id → StoredFile
  └─ FeaturePartLink (n:n)    → Part   embrión de INSTANCIA_EN_PROYECTO
```

### Las piezas: por qué el feature se agrupa por pieza y no por tipo de fichero

Hasta el 2026-08-18 el adjunto llevaba un `part_ref` de **texto libre** (`"3212 Pump Housing"`) y
la ficha los agrupaba **por tipo**. Con eso, `"3212 Pump Housing"` y `"3212 lote 315346"` eran dos
piezas distintas para la máquina, el desplegable de filtrado salía duplicado, y la ficha repetía
el `3212` una vez por fichero sin decir en ningún sitio *en cuántas piezas aparece el feature*.

Ahora hay dos caminos —a propósito— para que una pieza salga en la ficha de un feature:

| Camino | Para qué |
|---|---|
| **Tiene un fichero** (`FeatureAsset.part_id`) | El caso normal: vinculas el molde del 3212 y el 3212 aparece |
| **Está declarada** (`FeaturePartLink`) | *«el Bolt Eye también está en el 3197»* aunque no haya todavía ni un CAD vinculado |

La vista hace la **unión de los dos** (`frontend/src/components/Features/parts.ts`). Una pieza
declarada sin ficheros sale con la fila entera vacía, que es justo lo que hace visible **lo que
falta por vincular**.

Decisiones que conviene conocer antes de tocarlo:

| Decisión | Por qué |
|---|---|
| **Una sola tabla `FeatureNote`** con `kind` en vez de dos tablas | Warnings y lessons learned tienen exactamente los mismos campos y la misma UI. Una tabla, un juego de endpoints, un componente |
| `tags` como **`ARRAY(String)` de Postgres**, no tabla aparte | Se filtra con `tags @> ...` y se busca con `array_to_string`. Sin joins ni tabla de unión para algo que es texto libre |
| Los enums se guardan como **VARCHAR** (`sa_type=AutoString`), no como tipo `ENUM` de Postgres | Añadir una categoría nueva no obliga a una migración. En la API y en el cliente TypeScript siguen siendo uniones cerradas |
| `Feature.owner_id` es **`ON DELETE SET NULL`** | La ficha es conocimiento compartido: sobrevive al borrado del usuario que la creó. (El `Item` de la plantilla, en cambio, es `CASCADE`) |
| Las notas y los adjuntos son **`ON DELETE CASCADE`** | No tienen sentido sin su feature |
| `FeatureAsset.file_id` y `part_id` son **`SET NULL`** | Borrar un fichero no borra la fila que lo describía; borrar una pieza no borra sus adjuntos, que caen a un desplegable *«Sin pieza»* al final de la lista |
| `Part.code` es **UNIQUE**; las piezas existentes se pueden vincular sin duplicarlas | Es la clave con la que se agrupa todo. El alta desde carpeta extrae un código editable del nombre |
| `FeaturePartLink` es una tabla de unión **sin campos propios** | Hoy solo dice *«este feature está en esta pieza»*. Cuando llegue la ingesta, aquí cuelgan los N-numbers y las tolerancias y pasa a ser `INSTANCIA_EN_PROYECTO` |
| Borrar una pieza es **solo de superusuario y si no tiene uso** | Se rechaza con `409` si quedan vínculos directos o adjuntos en algún feature; no se borran carpetas ni documentos |

### Ficheros subidos y originales externos

`FeatureAsset.file_id` sigue apuntando a un documento independiente de su origen. Para
`source=local`, el backend resuelve una ruta relativa dentro de `ASSETS_ROOT`, montado en
solo lectura; vincular solo guarda metadatos. Si cambia su fecha/tamaño, exige revisar y volver
a vincular. El UUID se conserva, y cambia `version` para invalidar enlaces anteriores.
No hay historial de bytes ni detección automática de renombrados locales. Ver
[contrato de archivos](ficheros-externos.md#modelo-y-api).

Para `source=upload`, los bytes se guardan en disco, en `settings.UPLOADS_DIR`. El Dockerfile fija **`/app/uploads`**
como ruta absoluta; el WORKDIR es `/app/backend`. En local el valor por defecto `uploads` es
relativo al directorio de trabajo, normalmente `backend/uploads`. El fichero se llama como el
`id` de la fila; el nombre original y el mime-type viven en la base de datos.

En Docker hay un volumen `app-uploads` montado en `/app/uploads` (`compose.yml`), así que los
ficheros sobreviven a un `docker compose down`.

La tabla `FilePreview` guarda la cola y el estado del GLB derivado de cada documento. Los
bytes de las vistas ligeras viven bajo `/app/uploads/previews`; usan el mismo volumen,
pero se pueden regenerar. Ver [vistas-3d.md](vistas-3d.md).

Corregido el 2026-09-15: antes se escribía en `/app/backend/uploads`, fuera del volumen.
Antes de recrear una instalación antigua, comprobar esa ruta y rescatar cualquier fichero;
ver [deployment.md](../deployment.md). Los metadatos de la BD no permiten recuperar bytes perdidos.

### Sesión: qué pasa cuando el token deja de valer

Corregido el **2026-08-18**, después de quedarnos encerrados fuera de la aplicación.

Si el token es **válido y está en fecha** pero su usuario ya no existe —lo que pasa en cuanto se
resetea la base de datos, porque `initial_data.py` recrea el superusuario con un `id` nuevo—
`deps.get_current_user` devolvía **404**. Y `main.tsx` solo reaccionaba a `401`/`403`, así que la
aplicación se quedaba en un limbo: sesión iniciada, usuario desconocido, sin menú de Admin, sin
resultados, y **sin botón de cerrar sesión** (el sidebar no lo pinta sin usuario). Encima
`/login` rebotaba a `/` porque `isLoggedIn()` solo miraba que la cadena existiese. Solo se salía
borrando `localStorage` a mano.

Ahora, tres cierres independientes:

| Dónde | Qué hace |
|---|---|
| `backend/app/api/deps.py` | Token de un usuario inexistente → **401**, no 404. Es un fallo de autenticación, no un recurso que falte |
| `frontend/src/main.tsx` | Cualquier error de la consulta `currentUser` tira el token y va al login, sea cual sea el código. Y los `401`/`403` **no se reintentan**: antes eran 7 s de pantalla vacía, ahora 0,4 s |
| `frontend/src/hooks/useAuth.ts` | `isLoggedIn()` comprueba también el `exp` del JWT, así que un token caducado o corrupto ya no te rebota a `/` |

Comprobado con los cuatro tipos de token malo (usuario borrado, firma rota, caducado y basura):
los cuatro acaban en la pantalla de login en menos de medio segundo.

**`GET /files/{id}` requiere autenticación o una URL firmada temporal.** El frontend pide
`GET /files/{id}/access-url` con su token de sesión y recibe una URL que puede usar en imágenes,
visores y descargas. Caduca a los 15 minutos y está ligada al fichero y a un usuario activo;
no sirve como token de sesión ni para otro fichero. El UUID por sí solo devuelve 401.
HTML/SVG y tipos activos no permitidos se fuerzan como adjuntos, con `nosniff` y sin caché pública.

---

## API (`backend/app/api/routes/`)

Todo bajo `/api/v1`. Documentación interactiva en `http://localhost:8000/docs`.

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/features/` | Buscar. Params: `q`, `category`, `tag`, `part_id`, `skip`, `limit` |
| `GET` | `/features/filters` | Features con sus vínculos, categorías, tags y piezas **que algún feature usa**, para los desplegables |
| `POST` | `/features/` | Crear |
| `GET` | `/features/{id}` | Ficha completa: + `notes` + `assets` |
| `PUT` `DELETE` | `/features/{id}` | Editar / borrar |
| `POST` | `/features/{id}/notes` | Añadir warning o lesson learned |
| `PUT` `DELETE` | `/features/notes/{id}` | Editar / borrar una nota |
| `POST` `DELETE` | `/features/{id}/parts/{part_id}` | Vincular una pieza / quitar su tarjeta y adjuntos del feature |
| `PUT` | `/features/{id}/parts/order` | Guardar el orden de tarjetas de ese feature |
| `PUT` | `/features/{id}/notes/order` | Ordenar advertencias o lecciones en una sola operación (`kind`, `note_ids`) |
| `PUT` | `/features/{id}/assets/order` | Ordenar los ficheros de una pieza (`part_id`, `asset_ids`) |
| `POST` | `/features/{id}/assets` | Adjuntar el fichero de una pieza |
| `PUT` `DELETE` | `/features/assets/{id}` | Editar / quitar un adjunto |
| `POST` | `/parts/from-folder` | Registrar o reutilizar una carpeta de pieza existente, sin duplicados |
| `GET` `POST` | `/parts/` | Listar (incluye `feature_count` por pieza) y dar de alta piezas |
| `PUT` | `/parts/{id}` | Editar código o nombre. El código es único: choque → `409` |
| `GET` | `/catalog` | Búsqueda paginada de piezas/features; cotas por pieza/revisión solo con texto. Filtros compartidos y `kind=all/part/feature` |
| `GET` | `/parts/{id}/detail` | Identidad, portada/CAD, referencias y features vinculados |
| `PUT` | `/parts/{id}/cover` | Guardar una captura del CAD actual, validando versión y SHA-256 |
| `DELETE` | `/parts/{id}` | Borrar una pieza sin uso. **Solo superusuario**; usada → `409` |
| `POST` | `/files/` | Subir un fichero (multipart) → devuelve el `id` que se referencia |
| `GET` | `/files/source` | Listar una carpeta del origen configurado; `path`, `skip`, `limit` |
| `POST` | `/files/reference` | Registrar/reutilizar un original local sin copiarlo |
| `PUT` | `/files/{id}/reference` | Volver a vincular con control de versión; conserva el UUID |
| `GET` | `/files/{id}/status` | Disponible, ausente, cambiado o inaccesible |
| `GET` | `/files/{id}/access-url` | Obtener enlace temporal autenticado; `download=true` fuerza descarga |
| `GET` | `/files/{id}` | Servirlo con bearer o enlace firmado válido |
| `DELETE` | `/files/{id}` | Borrar el registro; no borra el original externo |

**La búsqueda `q` es global**: mira en el nombre, la descripción, los tags, el **código y el
nombre de las piezas** (por adjunto y por declaración), el nombre de los adjuntos, y el título y
el cuerpo de warnings y lessons learned. Es lo que permite encontrar el Bolt Eye escribiendo
`3212`, `Pump Housing` o `N170`.

### Permisos

Hay dos roles (usuario y superusuario). El registro público está desactivado por defecto
(`ALLOW_PUBLIC_SIGNUP=false`); Admin crea las cuentas. `/signup` indica que se contacte con
el administrador. Las rutas privadas para crear usuarios de prueba requieren
`ENABLE_TEST_ROUTES=true`, `ENVIRONMENT=local` y una BD cuyo nombre termine en `_test`.

- **Leer**: cualquier usuario autenticado ve **todas** las fichas. Es el sentido de la
  herramienta — a diferencia del `Item` de la plantilla, que solo enseña los propios.
- **Crear y editar**: cualquier usuario autenticado. La base es colaborativa.
- **Borrar un feature**: solo el autor o un superusuario.
- **Borrar notas, adjuntos y ficheros**: cualquier usuario autenticado, conforme al modelo
  colaborativo. También son acciones permanentes; quitar un adjunto no borra sus bytes.
- **Borrar piezas**: solo superusuario y después de desvincularlas de todos los features.
- **Gestión de usuarios**: superusuario, como en la plantilla.

---

## Frontend (`frontend/src/`)

Las reglas compartidas de búsqueda, filtros, gráficas y navegación están en
[Patrones de interfaz](interfaz.md). Se aplican también a nuevas pantallas.

**Catálogo** (`/features`) reúne tarjetas de piezas y features. Las cotas aparecen solo
al buscar y conservan pieza/revisión en el enlace. `/parts` redirige al mismo catálogo
filtrado por piezas. `/parts/{id}` muestra portada CAD, features, cotas y referencias.
La ficha comparte el diseño del feature: cabecera con portada y acciones, Cotas a la
izquierda, Features y Archivos a la derecha. Cada feature aparece sin foto, con su nombre
enlazado y las cotas de esta pieza; estas abren la medición en la misma página.
La sección Cotas reutiliza `MetrologyPage` con la pieza fijada por la ficha, sin selectores
de pieza, Feature ni Más filtros. Conserva buscador y controles de las mediciones.
`GET /evidence/metrology/filters` proporciona opciones ligeras con pertenencia, categoría
y tags; `GET /evidence/parts/{id}` incluye features y sus cotas, además de los datos importados.
El catálogo ofrece todas las piezas registradas, incluidas las que no tienen features.
`Common/SearchSelect` se reutiliza también en Features. Categoría y tag deben coincidir
en un mismo feature y solo atribuyen a la consulta sus cotas realmente vinculadas.
La ficha no selecciona N170 ni otra cota automáticamente. Siempre ofrece todas las cotas
de la pieza, también las no asignadas a features o sin mediciones. Los filtros del catálogo
en enlaces antiguos no limitan esta consulta; al interactuar se eliminan del enlace.
Se conservan pieza, cota y revisión, también al abrir el plano.

La sección Cotas abre la consulta sin pestañas ni listados de archivos de mediciones.
Mediciones y correcciones comparten filtros y gráfica; los números se consultan sobre
la gráfica. Correcciones conserva todos los muestreos; pulsar una región entre ellos la
selecciona en gris y actualiza la propuesta, previsión y cambio medido, sin imágenes ni
desplegable de documentos. Plano queda junto al buscador con su misma altura y abre
`/parts/{id}/fichero/{fileId}`, una página propia con el visor de Features. El enlace del
PDF en Archivos abre la misma página; no redirige a la sección Cotas. Los enlaces antiguos
con `plano=true` se resuelven al archivo. Correcciones queda debajo a la izquierda.
Ambos conservan el contexto en el historial del navegador. La importación CSV está en
**Catálogo → Nueva pieza / ficha de pieza → Actualizar datos**. Admin conserva la importación
piloto de mediciones/correcciones del 3212. Metrología permite cambiar de revisión si hay
varias, y consultar una versión anterior desde el historial de importaciones de la pieza.

| Ruta | Fichero | Qué es |
|---|---|---|
| `/` | `routes/_layout/index.tsx` | Redirige a `/features`, conservando los filtros de los enlaces antiguos |
| `/features/{id}` | `routes/_layout/features_.$featureId.tsx` | 🔑 **La ficha del feature**: cabecera con la imagen a la izquierda e identidad a la derecha (nombre, descripción, categoría, tags, piezas), y debajo a todo el ancho warnings, lessons y los ficheros por pieza. **Se edita aquí mismo** (ver abajo) |
| `/features` | `routes/_layout/features.tsx` | **Catálogo e inicio**: buscador, filtros y tarjetas que abren la ficha en lectura, con *Nuevo feature* y *Editar* directamente accesibles. La búsqueda va en la URL (`/features?q=3212`) |
| `/features/{id}/fichero/{assetId}` | `routes/_layout/features_.$featureId_.fichero.$assetId.tsx` | 🔑 **La página de un fichero**: el visor (PDF, imagen o 3D), el botón de descargar y, cuando no hay visor posible, qué programa hace falta |
| `/features/nuevo` | `routes/_layout/features_.nuevo.tsx` | **Alta completa** con todas las secciones desde el principio. Añadir contenido crea el feature automáticamente; Guardar termina en su ficha de consulta |
| `/admin` | `routes/_layout/admin.tsx` | Usuarios y permisos; punto de alta de cuentas con el registro público cerrado |

Componentes en `components/Features/`:

| Fichero | Qué |
|---|---|
| `FeatureSearch.tsx` | Buscador + Pieza y Feature; Categoría y Tag bajo Más filtros. Selectores con búsqueda interna poblados desde `/features/filters`; `feature_id` filtra por identidad exacta y se conserva como `feature` en la URL |
| `FeatureCard.tsx` | La tarjeta: imagen, nombre, descripción, tags y el resumen *«2 piezas · 3197, 3212»* |
| `PartAssetList.tsx` | 🔑 **Los ficheros agrupados por pieza**: un desplegable por pieza y dentro una fila por fichero. **El mismo componente sirve la ficha y el formulario** (`editable`) |
| `Parts/FeaturePartEvidence.tsx` | Fila **COTAS** compacta: números, plano, añadir y papelera. Añadir permite seleccionar una cota importada con su revisión o escribir otra al final de la fila. |
| `Parts/PartSetupDialog.tsx` | Alta y actualización automática, tamaño fijo, carga en el pie y acciones Crear/Cancelar. No asigna cotas al feature. |
| `viewers.ts` | Extensión → visor, carga directa hasta 50 MiB y GLB automático para STL/STEP grandes |
| `ModelViewer.tsx` | El visor 3D (three.js + OpenCascade en WASM). Se carga con `import()` dinámico: no pesa nada hasta que alguien abre un 3D |
| `modelControls.ts` | Giro libre en pantalla, desplazamiento y zoom 3D, sin bloqueo en los polos ni inercia al soltar |
| `PdfViewer.tsx` | PDF.js en canvas: rueda sobre el cursor, arrastre del plano, encuadre y cambio de página |
| `parts.ts` | La unión *piezas declaradas + piezas con ficheros* y el reparto por pieza y tipo. Es la lógica de la lista |
| `PartActions.tsx` | Buscador de piezas registradas; seleccionar vincula una al feature |
| `PartIdentityEditor.tsx` | Código y nombre editables en la cabecera de la pieza, con autoguardado y recuperación de errores |
| `PartFolderPicker.tsx` | Carpeta compartida de la pieza; reutiliza el explorador de originales |
| `FeatureForm.tsx` | El formulario de alta y edición (datos básicos + warnings, lessons, **Piezas** y **Ficheros por pieza**). Lo montan `/features/nuevo` y la propia ficha en modo edición. 🔑 **Repite el reparto de la ficha** —foto a la izquierda, datos a la derecha, secciones debajo— con una casilla en el sitio de cada dato, para que entrar y salir de edición no mueva nada de sitio |
| `FeatureNotFound.tsx` | La pantalla de «feature no encontrado» de la ficha |
| `FeatureActions.tsx` | El botón *Editar* compartido por las tarjetas y la ficha; *Eliminar* vive en la ficha, con confirmación y solo para autor o superusuario |
| `NoteList.tsx` | Warnings y lessons **en modo edición**: título editable en su sitio, desplegable con el cuerpo dentro y autoguardado |
| `AssetEditRow.tsx` | Fila **en edición**: tipo/pieza, nombre, subida y vínculo a un archivo existente |
| `SourceFilePicker.tsx` | Selector de originales: elegir un archivo y vincularlo a esta tarjeta, sin opciones adicionales |
| `DocumentStatus.tsx` | Estado del original y aviso de archivo ausente/cambiado/inaccesible |
| `constants.ts` | Las etiquetas en castellano de categorías y tipos, y el icono de cada tipo |
| `queries.ts` | Las query keys. Todo cuelga de `["features"]`: invalidar esa raíz refresca todo |

Y en `components/Common/`: `FileUpload.tsx` (drag and drop), `RichText.tsx` (editor y visor),
`CollapsibleSection.tsx` (los paneles desplegables).

### Los ficheros, agrupados por pieza (2026-08-25)

Hasta el 2026-08-25 esto era una **tabla** de pieza × tipo de fichero. Se cambió por tres motivos:
era lo único con forma de tabla en toda la ficha, en una casilla no cabe el nombre del fichero
—que es justo lo que se quiere leer— y con tres piezas se iba en horizontal. Ahora es lo mismo que
Warnings y Lessons: un **desplegable por pieza** (`3212 · Pump Housing`) y dentro **una fila por
fichero**.

**El checklist de lo que falta no se pierde**: lo dan el contador de cada pieza
(*«5 ficheros · 2 vinculados»*) y las filas que dicen *«sin archivo vinculado»*.

**Añadir pieza** busca exclusivamente en el catálogo registrado. **Nueva pieza** está en
Catálogo: selecciona una carpeta de Windows dentro del origen configurado, propone el
nombre completo y los archivos y prepara datos compatibles al crearla. El código se obtiene
del prefijo numérico de la carpeta o se asigna uno provisional estable `PIEZA-…`.
Se reutilizan registros existentes, sin crear carpetas ni duplicar piezas. Código y carpeta
son únicos; un código asociado a otra carpeta produce conflicto.

Código, nombre y carpeta se comparten entre features; cada feature elige sus propios ficheros.
El selector nativo de ficheros empieza en Exemples. **Cambiar carpeta** está en el menú
de tres puntos y conserva los nombres personalizados. `folder_path` pertenece al adaptador
local temporal; Graph sustituirá esa referencia por la identidad estable del origen.

La fila COTAS usa el mismo patrón compacto de los ficheros. Añadir cota inserta un campo
al final que se guarda con Intro, al salir o con Guardar el feature; los errores conservan
el borrador. No solicita revisión ni relación. Reutiliza vínculos existentes sin cambiar
sus metadatos; para altas toma la revisión del estudio o una única revisión conocida de
la pieza/cota. Sin esa información queda «sin confirmar», sin asumir la revisión 06.

Si hay cotas importadas, Añadir cota ofrece primero un selector con búsqueda y revisión;
la alternativa manual conserva el comportamiento anterior. Actualizar datos en Metrología
procesa las tablas compatibles automáticamente sin asignar sus cotas al feature.
Una pieza vinculada a varios features comparte las mismas importaciones.

API autenticada de mediciones (prefijo `/api/v1`):

| Método y ruta | Función |
|---|---|
| `POST /evidence/parts/{id}/measurements/preview` | Descubrir CSV o revisar una selección; devuelve contexto, hash, ejemplos y estado sin escribir datos. |
| `POST /evidence/parts/{id}/measurements/import` | Verificar otra vez contexto y hashes, incorporar cotas y conservar versiones. Requiere pieza vinculada a un feature y confirmación de las sustituciones. |
| `GET /evidence/parts/{id}/measurements/history` | Historial de importaciones, con revisiones y versión vigente por muestreo/cavidad. |
| `GET /evidence/parts/{id}?revision=…&snapshot_id=…` | Consulta de la revisión elegida o del estado guardado hasta una importación concreta; devuelve `measurement_revisions`. |

La migración `h39c25ebfa07` añade `MeasurementImport` (`measurement_models.py`). No
importa originales durante la migración. La primera importación CSV conserva también
una copia del estudio piloto previo, si existe, para que siga siendo consultable.

Las piezas antiguas sin correspondencia en el origen siguen disponibles en el buscador.
La papelera elimina directamente del catálogo las piezas sin uso, sin confirmación;
las utilizadas muestran «Usada en X features» y tienen la papelera desactivada. Se mantiene
el permiso de superusuario. La API cuenta vínculos directos y adjuntos de cada feature una
sola vez. Borrar el registro conserva los originales: si su carpeta sigue en el origen,
continúa disponible para registrarla de nuevo. Las carpetas aún no registradas no muestran papelera.

Las tarjetas se reordenan con el tirador y `@dnd-kit/react`, con desplazamiento animado durante
el arrastre. Space/flechas/Space permiten ordenar con teclado y Escape cancela. `Feature.part_order`
guarda el orden de piezas por feature, también usado en consulta. El mismo arrastre se aplica a
los ficheros dentro de cada pieza, las advertencias y las lecciones, guardando `position` en una
sola operación por lista. El orden de ficheros se conserva entre tipos distintos. Las listas no
intercambian elementos al arrastrar. La papelera retira la tarjeta y sus filas
de adjuntos en una transacción; conserva la pieza compartida, los otros features y los originales.
El desplegable de tipo de fichero contiene únicamente tipos.

🔑 **Cada fila promete lo que va a pasar antes de que la cliques**, que es lo que la tabla no hacía
(los iconos no se podían clicar y nadie sabía por qué):

| Se ve | Significa | Al clicar |
|---|---|---|
| Nombre legible del adjunto y tamaño | Hay fichero y **se puede ver aquí** | La página del fichero, con el visor |
| Igual, pero en gris debajo *«necesita Moldflow Communicator»* o *«demasiado grande para el visor»* | Hay fichero pero **la aplicación no ofrece un visor para él** | Página de detalles, estado y descarga |
| *«sin archivo vinculado»* en cursiva | El adjunto está declarado pero no tiene archivo. Es el caso inicial del seed | Vincular desde Editar |

La fila no repite el nombre original del archivo ni «Archivo vinculado». La cabecera del visor
también omite tipo, nombre interno, ruta y revisión técnica. Esos metadatos siguen en la BD.
Solo se muestran avisos de disponibilidad cuando requieren una acción. Si falta el original
o ha cambiado, **Volver a vincular** permite corregir la ubicación, conservando la revisión guardada. El selector es un
diálogo; los visores siguen en su página. Al volver se conserva el desplegado por pieza en la
sesión del navegador y se restaura el scroll de la ruta.

Lo decide `viewers.ts` a partir del tipo MIME, la extensión y el tamaño: los PDF con tipo
`application/pdf` y las imágenes JPEG, PNG, GIF, WebP, AVIF y BMP se pintan en la página.
La modal de edición de portada admite esos mismos formatos al seleccionar, arrastrar o pegar (Ctrl+V);
SVG y otros tipos no admitidos se ofrecen como archivos descargables. STL, GLB, OBJ, PLY,
STEP e IGES van directamente al visor 3D hasta **50 MiB**. Los STL y STEP/STP mayores usan
un [GLB generado en el servidor](vistas-3d.md); otros formatos grandes solo se descargan.
Los formatos sin visor —`.mfr` de Moldflow,
`.sldprt`, `.CATPart`— solo se descargan.

La aplicación no integra protocolos ni componentes de escritorio para abrir CAD local.
Su flujo es descargar → abrir desde la barra de descargas → Windows usa el programa asociado.
Una integración de escritorio sería un desarrollo adicional y requeriría instalación/configuración
en el equipo del usuario.

### El visor 3D

La cabecera también permite crear una [portada desde el STEP de la pieza](portadas-cad.md),
seleccionando superficies en rojo y guardando el encuadre. Las tarjetas usan una imagen;
la ficha muestra una miniatura clicable que abre una modal ajustada al cuadrado. El 3D se
activa automáticamente sobre la captura y su preparación se cancela al cerrar. El editor
mantiene iguales dimensiones en Imagen y CAD. La selección queda ligada a la revisión del documento.

Interacción ajustada el **2026-09-15** a petición del usuario: arrastre izquierdo para girar
libremente en el sentido de la pantalla, rueda para zoom, derecho/central para desplazar y
**Encuadrar** para recuperar la vista inicial. Se usa `TrackballControls` con el eje Z configurado
antes de inicializar el control y sin inercia al soltar. Se elimina el contador de triángulos
y el texto de instrucciones. La versión anterior cambiaba `camera.up` después de construir
`OrbitControls`; ese control había calculado su eje con otro valor y limitaba el paso por los polos.

`ModelViewer.tsx`, con **three.js** para lo que ya son triángulos (STL, GLB, OBJ, PLY) y
**`occt-import-js`** —OpenCascade compilado a WebAssembly, lo que usa Online 3D Viewer— para lo que
es B-rep con NURBS y hay que teselar (STEP, IGES, BREP).

El navegador tesela los CAD pequeños. El STEP de la pieza del 3212 son 10 MB y
tarda unos segundos. Y los dos paquetes van en `import()` dinámico: en el build salen como chunks
aparte (`three.module`, `occt-import-js`, `ModelViewer`), así que **quien no abre un 3D no se
descarga three.js**.

**Comprobado con el STEP real del 3212 el 2026-09-15:** 83.132 triángulos, giro, zoom,
encuadre, descarga idéntica al original y salida/vuelta desde la ficha. El PDF real también
se visualiza y amplía; su resolución original limita los detalles pequeños. Ver la
[verificación](ficheros-externos.md#verificación-con-el-3212). El escaneo y el molde grandes
usan `WebModelViewer.tsx`, que consulta la cola y entrega a `ModelViewer` únicamente su GLB.
El enlace de descarga continúa apuntando al original. Implementación y límites en
[vistas-3d.md](vistas-3d.md).

### El visor de planos PDF

`PdfViewer.tsx` sustituye el iframe nativo por un canvas de PDF.js. La rueda amplía alrededor del
cursor y el arrastre izquierdo mueve el plano en cualquier dirección sin desplazar la página
web. Los controles visibles son acercar, alejar y encuadrar; los de página aparecen solo si el
PDF tiene varias. Admite flechas y +/-/0 desde el teclado. El renderizador y su worker se sirven
desde la propia aplicación y se cargan solo al abrir un PDF; no se envía el plano a otro servicio.

El original sigue disponible mediante **Descargar** y **Abrir en pestaña**. El canvas se vuelve
a renderizar al ampliar, manteniendo la imagen anterior mientras tanto, con un límite de
16 megapíxeles para controlar memoria. El PDF escaneado del 3212 conserva su resolución de origen.
No se han añadido OCR, anotaciones ni selección de texto al canvas.

### La ficha es una página, no una modal (2026-08-19)

Hasta el 2026-08-19 la ficha era una modal de 672 px. Ahora es la página `/features/{id}`, y la
modal se ha borrado. El motivo no es estético:

- **La ficha es el destino de la herramienta**, no una vista previa. Con URL propia se puede
  enviar por Teams, guardar en favoritos y enlazar desde estos `docs/`.
- La **cabecera repite la lectura de la tarjeta del buscador** —imagen a la izquierda, identidad
  a la derecha— para que el salto del resultado a la ficha no obligue a releer nada. Debajo, a
  todo el ancho, lo que hay que saber para diseñar: warnings, lessons y los ficheros por pieza.
- **Cabe lo que viene.** La matriz pieza × tipo ya se salía en la modal; los muestreos y las
  correcciones de molde de la siguiente fase no habrían entrado de ninguna manera.
- **El formulario tampoco es una modal.** Era una modal con warnings, lessons, piezas y cinco
  tipos de fichero dentro de 672 px, que además abría modales encima de la modal. Ahora el alta
  es `/features/nuevo` y la edición ocurre **dentro de la propia ficha**. Desde el 2026-08-25
  las notas y los adjuntos se editan **en línea**: `NoteDialog` y `AssetDialog` se han borrado
(ver abajo). Se mantienen confirmaciones de borrado, el diálogo de cambios pendientes,
el selector de originales y los diálogos para crear o ampliar una portada CAD.

🔑 **Un único catálogo de piezas y features** (ampliado el 2026-09-22). El menú lateral tiene
una sola entrada **Catálogo**, activa también dentro de las fichas y los visores; **Admin**
sigue separado para los superusuarios. La cabecera muestra el título, *Nueva pieza* y
*Nuevo feature*, sin saludo ni párrafos de instrucciones. Las tarjetas reutilizan el diseño
de Features. La búsqueda conserva los filtros y ofrece *Mostrar más* para paginar.

La tarjeta se pulsa para consultar y su botón *Editar* abre directamente la edición. No hay
interruptor global ni menú intermedio. La ficha en lectura también ofrece *Editar*, y
*Eliminar* aparece como acción secundaria con confirmación para el autor o un superusuario.
Los permisos no cambian: cualquier usuario autenticado puede crear y editar.

🔑 **La ficha tiene dos caras, y las dos son la misma página** — solo cambia un *search param*:

| Desde | URL | Qué enseña |
|---|---|---|
| Tarjeta del catálogo | `/features/{id}` | Lectura, con acceso a *Editar* |
| *Editar* de la tarjeta o de la ficha | `?editar=true` | **El mismo contenido, en el mismo sitio, editable** |

*Editar* no cambia el reparto de la página: el nombre sigue siendo el nombre —ahora en una
casilla—, la foto sigue a la izquierda —ahora abre el editor de portada—, y las secciones
siguen debajo, con sus botones de añadir y borrar. Arriba a la derecha están *Cancelar* y
*Guardar*, y ahí es donde tienen que estar: lo único que se guarda a mano es la cabecera, porque
las notas y los ficheros se guardan en línea. **Los dos dejan la misma ficha en lectura**.
Cambiar de modo reemplaza la entrada del historial: *atrás* vuelve al catálogo con sus filtros
y posición, sin recorrer modos de edición anteriores. El modo vive en la URL y no en un `useState` por
dos motivos: el *Editar* de la lista entra directo a él, y recargar (F5) no te echa de la
edición. Antes de salir, se completan los guardados pendientes de notas/adjuntos y las subidas;
si fallan, se conserva la edición y se muestra el error. **Cancelar descarta la cabecera**, no
deshace las notas ni los adjuntos guardados en línea. `validateSearch` lo declara **opcional**, o el catálogo no podría enlazar la ficha sin
pasarlo (TanStack exige en los enlaces todo search param que el validador declare obligatorio).

**No hay botón *Volver*** en ninguna de las dos: para eso están el botón del navegador y el menú
lateral. El único que queda es el de «Feature no encontrado», donde no hay nada más donde pulsar.

🔑 **La búsqueda vive en la URL**. El catálogo lee directamente los parámetros validados y
los actualiza con `replace: true`, sin una entrada de historial por tecla. Solo la consulta a
la API usa *debounce*. Así *atrás* restaura los filtros y no quedan escrituras de URL pendientes
al abrir una ficha. Los favoritos antiguos de `/` redirigen con los mismos parámetros.

🔴 **Ojo con los *search params* del router**: TanStack pasa cada valor por `JSON.parse` y, al
escribir, entrecomilla lo que parezca JSON para conservar el tipo. Buscar `3212` daba
`/?q=%223212%22` — justo el caso más común aquí, un código de pieza. En `main.tsx` se le pasa
`stringifySearch: stringifySearchWith(JSON.stringify)` (sin parser) para que el texto viaje tal
cual, y `validateFeatureSearch` convierte a texto lo que vuelva como número.

### Editar es escribir encima (2026-08-25)

Hasta el 2026-08-25, editar una nota o un fichero era: pulsar un lápiz → se abría una modal →
rellenar → *Guardar*. Cuatro pasos para cambiar una palabra, y el título de la nota se leía en la
lista pero se escribía en otro sitio. Ahora **se escribe donde se lee**:

| | Antes | Ahora |
|---|---|---|
| Warning / lesson | Fila con el título + lápiz → modal con título y cuerpo | **Título editable en la fila** y desplegable con el cuerpo dentro, editable ahí mismo |
| Fichero de una pieza | Fila con el nombre + lápiz → modal con tipo, pieza y fichero | Tipo/pieza en desplegable, nombre en línea y acciones de subir, descargar y vincular en la fila |
| Añadir | Modal vacía que hay que rellenar y confirmar | Crea la fila en el momento, abierta y con el texto seleccionado para escribir encima |

Las notas mantienen el botón de borrar y edición en línea. Los archivos agrupan sus acciones
en la propia fila: subida, descarga, vínculo y borrado, sin botones de vínculo debajo.

🔑 **Autoguardado, sin botón de guardar**: se envían solo los campos modificados localmente
tras **0,7 s**, mediante `PUT` parcial (`model_dump(exclude_unset=True)`). Las escrituras se
serializan: una respuesta antigua no dispara una escritura que deshaga cambios posteriores.
Una actualización del servidor sincroniza los campos limpios, sin convertir diferencias
ajenas en ediciones locales. Los campos pendientes de la cabecera sobreviven a los refrescos.
Plegar una sección de edición conserva montados sus borradores; guardar o navegar espera los
guardados pendientes. La cabecera se sigue guardando mediante su botón.

- El **título vacío no se guarda** (`min_length=1` en el backend): el campo se marca en rojo y se
  queda esperando. Lo mismo con el nombre de un fichero.
- Al **subir un fichero en una fila recién creada** (la que aún se llama *«Nuevo fichero»*), el
  nombre pasa a ser el del fichero y el tipo se deduce de la extensión —`.pdf` → plano, `.stl` →
  escaneo, `.mfr` → Moldflow—. `.step` y `.stp` **no se deducen**: pueden ser el molde o la pieza,
  y adivinar mal es peor que no adivinar.

### Tres cosas del frontend que hay que saber

1. **El alta muestra cabecera, warnings, lessons y piezas desde el primer momento.** Abrir o
   cancelar el formulario vacío no crea registros. La primera nota o pieza crea automáticamente
   el feature con los datos actuales y nombre provisional «Nuevo feature» si falta título. Las
   altas simultáneas comparten esa misma creación. Las notas, piezas y adjuntos se guardan al
   vuelo; Guardar espera las operaciones pendientes y termina en la ficha de consulta.

2. 🔴 **Radix `Select` dentro de un `<form>` dispara `onValueChange("")` él solo** mientras su
   lista no se haya abierto. En el formulario del feature eso **borraba la categoría**: el
   desplegable enseñaba *Sin categoría* aunque el feature fuera `hole`, y al guardar el `PUT`
   salía con `category: ""` → **422 «Something went wrong!»**. Venía de la modal original, no del
   cambio a páginas. El corte está en `FeatureForm.tsx`:

   ```tsx
   onValueChange={(next) => next && field.onChange(next)}
   ```

   Un cambio de verdad nunca trae cadena vacía: el «Sin categoría» del desplegable vale `"none"`.
   ⚠️ Si se añade otro `Select` **controlado con `value=`** dentro de un formulario, hace falta
   el mismo corte.

3. **El editor de texto enriquecido es markdown reducido**, no TipTap: `**negrita**`,
   `*cursiva*`, `` `código` `` y listas con guion, con una barra de botones que los inserta. Es
   deliberado — cero dependencias nuevas y cero HTML que sanear. El campo del backend es texto
   libre, así que sustituirlo por un editor completo el día que haga falta es un cambio
   **solo de frontend**.

---

## Cómo se levanta

```powershell
docker compose up -d --build db prestart backend   # aplica las migraciones al arrancar
cd frontend; npm run dev                           # http://localhost:5173
```

Docker Compose carga el `.env` privado de la raíz, incluidos los originales, sin un lanzador.
En una instalación nueva, copiar `.env.example` a `.env` sin sobrescribir una configuración
existente. Configuración en [ficheros-externos.md](ficheros-externos.md).

🔴 **Sin `docker compose watch backend`, hay que usar `--build` después de tocar `backend/`.** El Dockerfile copia el código
dentro de la imagen; si ya existe un `backend:latest`, `docker compose up -d` a secas **lo
reutiliza tal cual** y arrancas con el código viejo — sin errores, simplemente faltan los
endpoints. Cómo se detecta:

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic heads     # current debe coincidir con heads
```

El frontend no tiene este problema: Vite sirve desde el disco.

### Datos de ejemplo

Hay una carga opcional con el **Bolt Eye del 3212**: sus 8 warnings y 2 lessons learned, sacados
de [modelo-datos.md](modelo-datos.md) y [3212/historial-molde.md](3212/historial-molde.md).

```powershell
docker compose exec backend python -m app.seed_features
```

Es idempotente: si el feature ya existe no toca nada. La creación completa usa una transacción:
un fallo revierte el ejemplo entero y permite reintentar. Crea la pieza **3212 Pump Housing**, la
declara en el feature y le cuelga los cinco adjuntos, uno por tipo. Los adjuntos se crean **sin
fichero**: los originales se vinculan después desde la aplicación. El seed no depende de rutas
personales. En desarrollo están vinculados el PDF, CAD, escaneo y molde del 3212.

### Regenerar el cliente TypeScript

Tras cambiar endpoints o modelos:

```bash
bash scripts/generate-client.sh
```

Requiere `uv` y npm. Exporta OpenAPI sin conectar a la BD, incluye las rutas exclusivas de tests
para su SDK y genera `frontend/src/client`. El JSON intermedio queda ignorado por Git.
Si `uv` no está disponible en el PATH, usar la alternativa Docker de
[development.md](../development.md#regenerar-la-api-typescript).

### Comprobaciones

Desde la raíz:

```powershell
npm.cmd run build --workspace frontend
npm.cmd run lint
npm.cmd run test:components
.\scripts\test.ps1 -q
.\scripts\test.ps1 -E2E
```

En Bash: `bash scripts/test.sh -q` y `bash scripts/test.sh --e2e`.
Los argumentos llegan a pytest o Playwright. `lint` comprueba sin modificar ficheros.

#### Los tests, siempre en una BD y un stack aislados

`compose.test.yml` es independiente de los otros Compose. Los lanzadores crean un nombre de
proyecto nuevo, PostgreSQL con BD `app_test` y subidas temporales, sin puertos publicados ni
volúmenes compartidos con el stack de trabajo. No cargan las credenciales de `.env`.

`conftest.py` rechaza nombres de BD que no terminen en `_test` antes de ejecutar pruebas y cambia
el directorio de subidas por otro temporal. Su limpieza borra únicamente las tablas de esa BD.
No copiar ni ejecutar tests dentro del backend de trabajo y no usar `docker compose down -v`.

Las pruebas de componentes simulan la API; las E2E utilizan el backend temporal. Los tests del
backend cubren features, piezas, validación, acceso a ficheros, usuarios y rollback del seed.
La cobertura HTML se genera dentro del stack de tests y desaparece al limpiarlo.
---

## Cabos sueltos

| Qué | Estado |
|---|---|
| **La página `/items` de la plantilla sigue existiendo** | Se ha quitado del menú pero el `Item` de demo sigue en el backend, el frontend y los tests. No molesta; se puede borrar entero cuando se decida |
| **Imagen con la zona marcada en rojo** | Implementada la [portada CAD](portadas-cad.md): caras del STEP, captura, cámara y 3D interactivo. El marcado libre sobre imágenes/planos sigue pendiente |
| **Vincular un feature con sus N-numbers y sus cotas** | La tabla ya existe (`FeaturePartLink`), pero está vacía de contenido: solo dice *feature ↔ pieza*. Añadirle los N-numbers y las tolerancias la convierte en el `INSTANCIA_EN_PROYECTO` de [modelo-datos.md](modelo-datos.md) |
| **Vistas ligeras de escaneo y molde** | Implementadas: cola persistente, GLB en caché, original intacto y descarga íntegra; ver [vistas-3d.md](vistas-3d.md) |
| **Conexión Microsoft 365** | Adaptador local implementado. Confirmar ubicación/permisos con IT (A10, prioridad 1) y desarrollar Graph con IDs estables; los visores usan el UUID interno del documento |
| **La ficha de una pieza** | Hoy `Part` solo tiene código y nombre; se crean, vinculan y editan desde el feature. No hay página propia de pieza |

### Nombre real del fichero en las tarjetas (2026-09-17)

Una tarjeta con fichero vinculado muestra siempre `StoredFile.filename`, incluida la extensión,
tanto al editar como al consultar o abrir el visor. Su nombre deja de ser una etiqueta editable.
Las filas sin archivo conservan el nombre provisional hasta vincular o subir uno. La API impone
el nombre real al crear o actualizar el adjunto; la migración `f170a3c9de85` corrige las etiquetas
antiguas de los documentos ya vinculados, sin modificar sus originales ni sus identidades.

El selector tiene una sola acción: vincular el archivo elegido a esta tarjeta. Cambiar el archivo
de una tarjeta no cambia el documento de otros features. Se han retirado el texto introductorio
y las opciones de reemplazar/actualizar el documento compartido. La API de actualización explícita
de referencias sigue disponible para integraciones, y mantiene sincronizados los nombres.
