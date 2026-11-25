# La aplicación web — base de conocimiento de features

> La prueba de concepto descrita en `inteplast_PADIH_fase_B.md`, implementada sobre la plantilla
> `full-stack-fastapi-template`: **backend** en `backend/`, **frontend** en `frontend/`.
>
> Este documento cubre **lo que se ha construido y por qué**. Las trampas de los datos crudos
> están en [formatos-parsing.md](../conocimiento/formatos-parsing.md); el modelo del dominio completo (proyectos,
> muestreos, mediciones, correcciones de molde) en [modelo-datos.md](modelo-datos.md).

> **Revisión documental: 26/10/2026.** Describe el código disponible; los ensayos históricos
> conservan su fecha y no se han repetido en esta revisión. Para localizar el contrato de
> cada subsistema y distinguir propuestas e historial, empezar por [docs/README.md](README.md).

---

## Qué hay implementado

«Usar carpeta de la pieza» conserva los planos reconocidos aunque falte evidencia para
elegir el principal. En carpetas de soporte o corrección también comprueba los PDF
identificados por `DRW` o `ballooned` mediante el identificador del dibujo o una copia
contrastada. Al guardar se respeta la selección explícita de la estrella, incluso vacía.

**22/09/2026:** **Catálogo** reúne piezas y features en `/features`, con cotas solo cuando
se escribe en el buscador. Nueva pieza y Nuevo feature están juntos. Cada pieza tiene ficha
con código (título), nombre opcional, familia, cliente y descripción, features vinculados y la consulta de metrología
reutilizada. Los vínculos se editan desde cualquiera de las dos fichas. La portada STEP
encuadrada aparece junto a la cabecera de la ficha y en la tarjeta del catálogo;
los archivos abren su visor desde la ficha.

La ficha de feature mantiene el mismo reparto en consulta y edición: portada y datos
arriba, advertencias/lecciones a la izquierda y piezas con sus cotas a la derecha.
La documentación se consulta en la ficha de pieza, sin repetirla en el feature.
Las notas permiten adjuntar imágenes a su cuerpo Markdown (`![nombre](file:id)`),
reutilizando los archivos y las URL de acceso temporales existentes; no se guardan URL
caducables en el texto. Plegar el punto mantiene las subidas y borradores pendientes.

El alta se hace en **Catálogo → Nueva pieza** (`/parts/nueva`), en una ficha común con
la edición y el diseño de Features. La carpeta seleccionada en Windows propone nombre,
código y cuatro referencias. Se pueden añadir más ficheros de esa carpeta, escoger su
tipo, darles un nombre visible y elegir el principal de cada tipo de referencia.
Crear guarda la ficha e incorpora automáticamente CSV CMM individuales/comparativos y
tablas PPAP XLS/XLSX. **Actualizar datos** repite la lectura de forma explícita y muestra
su progreso en Cotas; el resultado y las fuentes quedan en el registro técnico del servidor,
sin un panel de diagnóstico en la ficha (decisión del 16/11/2026). Features ofrece únicamente piezas registradas y reutiliza sus referencias al
asociarlas. La integración nativa local se describe en [ficheros-externos.md](ficheros-externos.md).
La interpretación de correcciones de otras piezas sigue pendiente.

Desde el **2026-10-22** el mismo conjunto se puede leer desde **SharePoint** con
`SHAREPOINT_ENABLED=true`: cada usuario entra con su cuenta de Microsoft y los archivos se leen
por Graph con sus permisos. El login real funciona con retorno automático desde el 09/11/2026;
falta la primera prueba real de archivos. Ver
[SharePoint](ficheros-externos.md#sharepoint-microsoft-graph).

El **bloque transversal** del modelo de datos: `FEATURE` + `WARNING` + `LESSON_LEARNED` +
ficheros de ejemplo. Es lo que consume el frontend descrito en la fase B y lo que responde a
*«dame todo del Bolt Eye»*.

Y desde el **2026-08-18**, la **pieza como entidad propia** (`Part`): los ficheros ya no cuelgan
del feature sueltos, cuelgan de la pieza a la que pertenecen. Es el embrión de `PROYECTO`.

Desde el **2026-09-15**, una ficha puede **vincular originales externos** sin subirlos. El PDF y
el STEP del 3212 están conectados y comprobados en la instalación local. Configuración, límites
de revisión y lectura desde SharePoint en [ficheros-externos.md](ficheros-externos.md).

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

<a id="modelo-de-datos-backendappmodelspy"></a>
## Modelo de datos implementado

```
StoredFile                    identidad común de un documento subido o referenciado
  id, filename, content_type, size, created_at
  source = upload | local (ruta del conjunto, leída de la carpeta o de SharePoint)
  source_key, source_path, source_version
  version (UUID del vínculo), revision (etiqueta), reference_key (deduplicación)

Part                          registro de pieza; no es una tabla independiente de moldes
  id, code ("3212", UNIQUE), name (opcional), description, folder_path
  family_id → PartFamily, customer_id → Customer, material_id → Material (opcionales, RESTRICT)
  cavity_count (entero positivo opcional introducido por el usuario)
  files_managed, last_read, created_at

PartFamily / Customer         listas compartidas (17/11/2026)
  id, name, key (UNIQUE: sin mayúsculas ni espacios sobrantes)

Feature                       la ficha del feature
  id, name, description, owner_id, image_id → StoredFile (solo sin piezas),
  cover_3d (JSON, sin uso desde el 19/11/2026)
  ├─ FeatureNote (n)          kind = warning | lesson
  │    title, body (markdown reducido), position
  ├─ FeatureAsset (n)         kind = mold | part | scan | drawing | moldflow
  │    name, position, part_id → Part, file_id → StoredFile
  └─ FeaturePartLink (n:n)    → Part   embrión de INSTANCIA_EN_PROYECTO
       image_id → StoredFile, cover_3d (JSON): portada de este feature en esa pieza
```

Los modelos están en [models.py](../backend/app/models.py),
[knowledge_models.py](../backend/app/knowledge_models.py) y
[measurement_models.py](../backend/app/measurement_models.py). La correspondencia entre
las tablas reales de archivos, cotas y snapshots y el dominio propuesto se mantiene en
[Modelo de datos, sección 5](modelo-datos.md#5-lo-que-el-frontend-ya-construido-espera).

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
declarada puede mostrar sus cotas y el enlace a su ficha aunque no tenga adjuntos.

Decisiones que conviene conocer antes de tocarlo:

| Decisión | Por qué |
|---|---|
| **Una sola tabla `FeatureNote`** con `kind` en vez de dos tablas | Warnings y lessons learned tienen exactamente los mismos campos y la misma UI. Una tabla, un juego de endpoints, un componente |
| **Sin tags ni categoría de feature** (17/11/2026, migración `o16d92fa1c07`) | No venían de INTEPLAST y con 8 features casi cada categoría tenía uno solo; «bomba» era falso para el 3197. Lo propio de cada feature va en descripción, advertencias, lecciones y cotas. Valores perdidos, anotados: Bolt Eye (`hole`, `bomba`, `automoción`) y Nervios (`rib`). Volver atrás recrea las columnas vacías; los valores solo vuelven desde la copia de la BD |
| **Caché del frontend tras reconstruir** (18/11/2026) | `index.html` se sirve con `Cache-Control: no-cache`; `/assets/` (nombres con huella) con caché larga y 404 si no existe, en vez de devolver `index.html` (`frontend/nginx.conf`). Una pestaña abierta antes de una reconstrucción que pide un trozo antiguo recarga una vez sola (`vite:preloadError` en `main.tsx`). Antes, abrir la portada en edición tras reconstruir mostraba «Oops! Something went wrong» |
| **Familia y cliente como tablas propias** (17/11/2026) | Desplegable compartido con «Añadir». El nombre es único sin distinguir mayúsculas ni espacios: «bosch» y «Bosch » no crean otra entrada; «Robert Bosch» sí. La migración agrupó así los textos de `Part.customer` (grafía más repetida; si empatan, la de la pieza más antigua). Renombrar, fusionar y borrar quedan para cuando se corrija el idioma |
| Los enums se guardan como **VARCHAR** (`sa_type=AutoString`), no como tipo `ENUM` de Postgres | Añadir una categoría nueva no obliga a una migración. En la API y en el cliente TypeScript siguen siendo uniones cerradas |
| `Feature.owner_id` es **`ON DELETE SET NULL`** | La ficha es conocimiento compartido: sobrevive al borrado del usuario que la creó. (El `Item` de la plantilla, en cambio, es `CASCADE`) |
| Las notas y los adjuntos son **`ON DELETE CASCADE`** | No tienen sentido sin su feature |
| `FeatureAsset.file_id` y `part_id` son **`SET NULL`** | Las FK conservan la fila del adjunto ante un borrado directo del registro referenciado. La API bloquea el borrado de piezas usadas; no ofrece dejarlas sin pieza como flujo de usuario |
| `Part.code` es **UNIQUE**; las piezas existentes se pueden vincular sin duplicarlas | Es la clave con la que se agrupa todo. El alta desde carpeta extrae un código editable del nombre |
| `FeaturePartLink` es una tabla de unión **sin campos propios** | Solo dice *«este feature está en esta pieza»*. Las cotas no cuelgan de aquí: se asocian con `FeatureCharacteristicLink` (feature ↔ cota de una pieza y revisión, con rol). El modelo normalizado `INSTANCIA_EN_PROYECTO` sigue pendiente |
| Borrar una pieza es **solo de superusuario** | Sin confirmación solo se borra una pieza sin uso (`409` si tiene vínculos, importaciones, cotas o documentos). Con la clave del alcance (`GET /parts/{id}/deletion`) se borra con sus datos en la app; los features, las demás piezas, los documentos compartidos y los originales se conservan (17/11/2026, `app/part_deletion.py`) |

### Ficheros subidos y originales externos

`FeatureAsset.file_id` apunta a un documento independiente de su origen. Las referencias
locales conservan metadatos del original; SharePoint añade acceso delegado y caché de lectura.
La detección de cambios y las versiones difieren entre ambos modos: consultar el
[contrato de archivos](ficheros-externos.md#modelo-y-api) y la
[integración Graph](ficheros-externos.md#sharepoint-microsoft-graph).

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

Resumen de rutas, no inventario exhaustivo; contratos de [mediciones](cotas-y-evidencia-web.md#api-de-cotas-y-mediciones),
[archivos](ficheros-externos.md) y [asistente](asistente.md) en sus referencias.
Todo bajo `/api/v1`. Documentación interactiva en `http://localhost:8000/docs`.

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/features/` | Buscar. Params: `q`, `part_id`, `feature_id`, `skip`, `limit` (`category` y `tag` de enlaces antiguos se ignoran) |
| `GET` | `/features/filters` | Features con sus vínculos y piezas **que algún feature usa**, para los desplegables |
| `GET` `POST` | `/families`, `/customers`, `/materials` | Listar y añadir familias, clientes y materiales con usuario autenticado. Añadir un nombre existente con otras mayúsculas o espacios devuelve el existente |
| `POST` | `/features/` | Crear |
| `GET` | `/features/{id}` | Ficha completa: + `notes` + `assets` + `part_covers` (una por pieza, en su orden definitivo) |
| `PUT` `DELETE` | `/features/{id}` | Editar / borrar. `PUT` guarda la cabecera y las portadas cambiadas (`part_covers`) en una sola transacción; una pieza retirada mientras tanto da 409 y rechaza `cover_3d` suelto con 422. Ver [portadas CAD](portadas-cad.md#una-portada-por-pieza-19112026) |
| `POST` | `/features/{id}/notes` | Añadir warning o lesson learned |
| `PUT` `DELETE` | `/features/notes/{id}` | Editar / borrar una nota |
| `POST` `DELETE` | `/features/{id}/parts/{part_id}` | Vincular una pieza / quitar su tarjeta y adjuntos del feature |
| `PUT` | `/features/{id}/parts/order` | Guardar el orden de tarjetas de ese feature |
| `PUT` | `/features/{id}/notes/order` | Ordenar advertencias o lecciones en una sola operación (`kind`, `note_ids`) |
| `PUT` | `/features/{id}/assets/order` | Ordenar los ficheros de una pieza (`part_id`, `asset_ids`) |
| `POST` | `/features/{id}/assets` | Adjuntar el fichero de una pieza |
| `PUT` `DELETE` | `/features/assets/{id}` | Editar / quitar un adjunto |
| `POST` | `/evidence/drawings/{id}/marks` | Etiqueta de lectura de la tarjeta de plano. Prepara un índice de búsqueda ausente o desactualizado en el trabajador de evidencia y devuelve `pending` mientras se procesa. La respuesta contiene solo el estado de las marcas. La verificación estricta del proyecto se consulta con `icp-check`. |
| `POST` | `/parts/from-folder` | Registrar o reutilizar una carpeta de pieza existente, sin duplicados |
| `GET` `POST` | `/parts/` | Listar (incluye `feature_count` por pieza) y dar de alta piezas |
| `PUT` | `/parts/{id}` | Editar la identidad, familia, cliente, material, número de cavidades, carpeta y archivos según `PartUpdate`. Omitir un campo opcional conserva su valor y `null` lo quita. Un código duplicado devuelve `409` y una referencia de catálogo inexistente devuelve `422` |
| `GET` | `/catalog` | Búsqueda paginada de piezas/features; cotas por pieza/revisión solo con texto. Filtros `part_id`, `feature_id`, `family_id`, `customer_id` y `kind=all/part/feature`. **Criterio único:** una pieza cumple si cumple todos los filtros de pieza a la vez; un feature, si está vinculado a al menos una pieza que los cumpla todos |
| `GET` | `/parts/{id}/cover` | CAD vinculado, clave de la versión actual y captura del mismo original. Si solo cambió el estilo, devuelve la imagen guardada con `cover_needs_refresh` mientras se prepara su sustituta. Comprueba acceso y versión antes de devolver la imagen. La lista y la cuadrícula usan `deferred_cover_part_id` para pedirla al entrar la tarjeta en pantalla. |
| `GET` | `/catalog/graph` | Lo mismo que `/catalog` con los mismos filtros (`catalog_part_filters` y `crud.feature_conditions`), sin páginas: nodos de pieza (código, nombre, captura CAD guardada; nunca lanza una nueva), feature, familia y cliente, y uniones pieza–feature (pertenencia completa, como la lista), pieza–familia y pieza–cliente. Tope `limit` (máx. y por defecto 500 nodos): si se supera devuelve `truncated` y el `total` real |
| `GET` | `/catalog/drawings` | «Planos» del catálogo: **todos** los planos de las piezas que cumplen los filtros (mismo criterio de pieza, familia, cliente y feature), no solo el principal. Cada pieza aporta los que muestra su ficha (`read_files`): su lista gestionada o, si no la tiene, sus referencias y los adjuntos de features (corregido el 18/11/2026; antes solo miraba `PartFile`). `q` busca en el nombre del archivo y en el código o nombre de la pieza. Cada tarjeta lleva componente y revisión si están asignados en «Organizar por componentes». Paginado (`skip`, `limit` ≤ 100) |
| `POST` | `/files/{id}/thumbnail?page=1` | Miniatura PNG de la página indicada (por defecto la primera, 480 px de ancho). Devuelve el giro adicional en grados horarios (`rotation`) y un enlace firmado para esa página y versión (`purpose: file-thumbnail`). La caché está en `uploads/thumbnails/{id}/`. El proceso hijo de PyMuPDF tiene un límite de 60 s y admite hasta dos conversiones simultáneas por proceso de la API y una por documento. Si está ocupado responde `busy`. Los fallos de conversión devuelven `422`, el tiempo agotado `504` y los formatos distintos de PDF `415`. |
| `POST` | `/files/{id}/icp-check` | «Globos verificados con .icp» (`app/icp_checks.py`, `app/ingestion/icp_verification.py`): cada `.icp` candidato del plano (`drawing_project_files`) se coloca a 1:1 y sus sellos deben caer sobre aros verdes o azules detectados por un detector independiente del índice: ≥10 coincidencias y la mitad de los aros y de los sellos, un único proyecto válido y ninguno ilegible; además, el lector de planos de la app (`drawing.balloon_source` + `icp.choose`, sin OCR) debe asociar esa página a ese proyecto con globos dibujados y los números verificados deben estar entre los que coloca. Sin lecturas, el lector solo asocia PDF de una página: **una hoja de un PDF de varias páginas no se verifica nunca** (dos planos pueden compartir posiciones con otros números). Proceso hijo con 180 s de límite, bloqueo por documento, caché por versión del PDF y de sus `.icp`, tomada de una sola lectura de la lista de proyectos; si el plano o sus `.icp` cambian durante el cálculo, el resultado se descarta y responde `busy`. `busy` también si no hay hueco. Sin `.icp` responde al momento sin dibujar |
| `GET` | `/files/{id}/thumbnail` | Sirve la miniatura con token o sesión; un enlace de una versión anterior ya no sirve (`409`/`401`) |
| `GET` | `/parts/{id}/detail` | Identidad, portada/CAD, referencias y features vinculados. La tarjeta (también en `/catalog`) trae `corrections_documented` (la lectura encontró documentos de correcciones: `corrections_state` distinto de `empty`) y `measurement_status`: `detected` / `pending` / `none` / `null` (`app/measurement_status.py`: filas de la importación vigente de cada revisión, muestra y cavidad —la última por `imported_at` y luego `id`, como en el historial; una importación vacía posterior retira los valores— que cumplen `usable_measurement`, con valor numérico, cota y fuente con archivo y celda; si no hay, el estado vivo de la lectura) |
| `POST` | `/parts/discover` | Propuesta de una carpeta. `suggested_features`: features del catálogo que se llaman exactamente como una carpeta superior sin su prefijo de orden, con coincidencia única; solo propuesta, nada se vincula hasta registrar con la selección del usuario |
| `PUT` | `/parts/{id}/cover` | Guardar una captura del CAD actual, validando versión y SHA-256 |
| `PUT` | `/parts/{id}/face-image` | Guardar un PNG de las caras de un feature o de la pieza completa. Verifica el STEP y la revisión de las selecciones antes de reutilizar la imagen. |
| `GET` | `/parts/{id}/deletion` | Alcance del borrado: qué se elimina, qué se conserva y la clave `key`. **Solo superusuario** |
| `DELETE` | `/parts/{id}` | Borrar una pieza. **Solo superusuario**. Sin `confirm`, solo si no tiene uso (`409`). Con `?confirm=<key>`, con sus datos; si el alcance ha cambiado → `409` |
| `POST` | `/files/` | Subir un fichero (multipart) → devuelve el `id` que se referencia |
| `GET` | `/files/source` | Listar una carpeta del origen configurado; `path`, `skip`, `limit` |
| `POST` | `/files/reference` | Registrar/reutilizar una referencia del origen configurado; ver contrato local/Graph |
| `PUT` | `/files/{id}/reference` | Volver a vincular con control de versión; conserva el UUID |
| `GET` | `/files/{id}/status` | Disponible, ausente, cambiado o inaccesible |
| `GET` | `/files/{id}/access-url` | Obtener enlace temporal autenticado; `download=true` fuerza descarga |
| `GET` | `/files/{id}` | Servirlo con bearer o enlace firmado válido |
| `DELETE` | `/files/{id}` | Borrar el registro; no borra el original externo |

**La búsqueda `q` es global**: mira en el nombre, la descripción, el **código y el
nombre de las piezas** (por adjunto y por declaración), el nombre de los adjuntos, y el título y
el cuerpo de warnings y lessons learned. Es lo que permite encontrar el Bolt Eye escribiendo
`3212`, `Pump Housing` o `N170`.

### Permisos

Hay dos roles (usuario y superusuario). El registro público está desactivado por defecto
(`ALLOW_PUBLIC_SIGNUP=false`); Admin crea las cuentas. Con SharePoint se entra con Microsoft:
la cuenta se asocia al usuario de Admin con el mismo correo. `/signup` indica que se contacte con
el administrador. Las rutas privadas para crear usuarios de prueba requieren
`ENABLE_TEST_ROUTES=true`, `ENVIRONMENT=local` y una BD cuyo nombre termine en `_test`.

- **Leer**: cualquier usuario autenticado ve **todas** las fichas. Es el sentido de la
  herramienta — a diferencia del `Item` de la plantilla, que solo enseña los propios.
- **Crear y editar**: cualquier usuario autenticado. La base es colaborativa.
- **Borrar un feature**: solo el autor o un superusuario.
- **Borrar notas, adjuntos y ficheros**: cualquier usuario autenticado, conforme al modelo
  colaborativo. También son acciones permanentes; quitar un adjunto no borra sus bytes.
- **Borrar piezas**: solo superusuario, comprobado en el backend. Con sus datos solo tras revisar el alcance en la ficha de pieza y escribir su código (ver [borrado de una pieza](#borrado-de-una-pieza-17112026)).
- **Gestión de usuarios**: superusuario, como en la plantilla.

### Borrado de una pieza (17/11/2026)

En la ficha de pieza, un administrador abre **⋯ → Eliminar**. El diálogo pide el alcance a
`GET /parts/{id}/deletion` y muestra qué se elimina y qué se conserva. «Eliminar pieza» se
activa al escribir el código de la pieza y envía `DELETE /parts/{id}?confirm=<key>`.
Los usuarios normales no ven la acción y el backend responde `403`. Código: `app/part_deletion.py`
y `Parts/DeletePart.tsx`.

- **Se elimina:** la pieza, sus cotas (`PartCharacteristic`) y las asignaciones de esas cotas
  a features, las importaciones de medición, sus listas de archivos y referencias, los trabajos
  de evidencia, sus adjuntos en features y su entrada en el orden de piezas de cada feature.
  Una portada 3D hecha con esta pieza se quita del feature.
- **Documentos:** un `StoredFile` usado solo por esta pieza se elimina con su vista previa,
  su índice de plano y sus ubicaciones revisadas. Si es una subida, también sus bytes. Si lo usa
  otra pieza, un feature, la imagen de un feature o una nota (`![…](file:id)` en una advertencia
  o lección), se conserva entero.
- **Nunca se tocan** los originales de INTEPLAST, en local ni en SharePoint: el `StoredFile`
  de un original es solo una referencia. Los features, sus notas y las demás piezas se conservan.
- **Confirmación ligada a los datos:** `key` es la huella del contenido completo de las filas
  que se borran (cotas, sus asignaciones, importaciones, adjuntos y ubicaciones revisadas), no
  solo de los recuentos; de los trabajos de evidencia, solo su identidad, porque su progreso
  cambia con el diálogo abierto. Si algo cambia entre la revisión y el borrado, se responde `409` y el diálogo
  vuelve a cargar el alcance. El borrado bloquea la pieza y espera a que termine una importación
  de evidencia que esté escribiendo en ella.
- **Sin `confirm`** se mantiene el comportamiento anterior: solo se borra una pieza sin uso.
  Es lo que usa la papelera del desplegable «Añadir pieza» de la ficha del feature.
- **Pruebas** en BD aislada (`tests/api/routes/test_parts.py`): alcance y borrado completo,
  rechazo a usuarios normales, clave antigua o falsa, clave que cambia al editar una ubicación,
  una cota o una importación sin cambiar los recuentos, conservación del original, del documento
  compartido, de la imagen de una nota, de la otra pieza y sus cotas, y ausencia de filas que apunten a la pieza o a sus
  documentos borrados. En el navegador, `piece-editor.test.cjs`.

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
`GET /evidence/metrology/filters` proporciona opciones ligeras con pertenencia;
`GET /evidence/parts/{id}` incluye features y sus cotas, además de los datos importados.
El catálogo ofrece todas las piezas registradas, incluidas las que no tienen features.
`Common/SearchSelect` se reutiliza también en Features. El filtro Feature solo atribuye a la
consulta sus cotas realmente vinculadas.
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
Ambos conservan el contexto en el historial del navegador. Las mediciones y correcciones se
leen en **Catálogo → Nueva pieza** y con **Actualizar datos** en la ficha de pieza; Admin solo
gestiona usuarios. Metrología permite cambiar de revisión si hay
varias, y consultar una versión anterior desde el historial de importaciones de la pieza.

| Ruta | Fichero | Qué es |
|---|---|---|
| `/` | `routes/_layout/index.tsx` | Redirige a `/features`, conservando los filtros de los enlaces antiguos |
| `/features/{id}` | `routes/_layout/features_.$featureId.tsx` | 🔑 **La ficha del feature**: cabecera con la imagen a la izquierda e identidad a la derecha (nombre, descripción, piezas), y debajo advertencias y lecciones a la izquierda y piezas con sus cotas a la derecha. **Se edita aquí mismo** (ver abajo) |
| `/features` | `routes/_layout/features.tsx` | **Catálogo e inicio**: buscador, filtros y tarjetas que abren la ficha en lectura, con *Nuevo feature* y *Editar* directamente accesibles. La búsqueda va en la URL (`/features?q=3212`) |
| `/features/{id}/fichero/{assetId}` | `routes/_layout/features_.$featureId_.fichero.$assetId.tsx` | Página antigua de un adjunto del feature. Se conserva para enlaces guardados; la interfaz ya no enlaza a ella |
| `/parts/{id}` | `routes/_layout/parts_.$partId.tsx` | 🔑 **La ficha de pieza**: identidad, carpeta, Cotas (mediciones, correcciones y plano), Features y Archivos. Se edita aquí mismo con `?editar=true` |
| `/parts/nueva` | `routes/_layout/parts_.nueva.tsx` | Alta de pieza desde su carpeta, con la misma composición que la ficha |
| `/parts/{id}/fichero/{fileId}` | `routes/_layout/parts_.$partId_.fichero.$fileId.tsx` | 🔑 **La página de un archivo de la pieza**: visor PDF con buscador de cotas, tabla CSV/XLS/XLSX, imagen o 3D; si no hay visor, descarga del original |
| `/features/nuevo` | `routes/_layout/features_.nuevo.tsx` | **Alta completa** con todas las secciones desde el principio. Añadir contenido crea el feature automáticamente; Guardar termina en su ficha de consulta |
| `/admin` | `routes/_layout/admin.tsx` | Usuarios, permisos y selección de la [carpeta de originales](ficheros-externos.md#cambiar-la-carpeta-desde-admin) de SharePoint |

Componentes en `components/Features/`:

| Fichero | Qué |
|---|---|
| `FeatureSearch.tsx` | Buscador + Pieza, Feature, Familia y Cliente bajo Filtros. Selectores con búsqueda interna poblados desde `/features/filters`, `/families` y `/customers`; `feature_id` filtra por identidad exacta; en la URL quedan `part`, `feature`, `family` y `customer` |
| `FeatureCard.tsx` | La tarjeta: imagen, nombre, descripción y el resumen *«2 piezas · 3197, 3212»* |
| `PartAssetList.tsx` | 🔑 **Las piezas del feature con sus cotas**: un desplegable por pieza con su fila COTAS y «Ver pieza». Los documentos se consultan en la ficha de pieza. **El mismo componente sirve la ficha y el formulario** (`editable`) |
| `Parts/FeaturePartEvidence.tsx` | Fila **COTAS** compacta: números, plano, añadir y papelera. Añadir permite seleccionar una cota importada con su revisión o escribir otra al final de la fila. |
| `Parts/PartDetailPage.tsx` | Ficha y alta de pieza (`/parts/{id}`, `/parts/nueva`): cabecera, carpeta, Cotas, Features y Archivos. **Actualizar datos** (`Parts/PartReadStatus.tsx`) relee la carpeta; no asigna cotas al feature. |
| `viewers.ts` | Extensión → visor, carga directa hasta 50 MiB y GLB automático para STL/STEP grandes |
| `ModelViewer.tsx` | El visor 3D (three.js + OpenCascade en WASM). Carga dinámica; también puede activarse al generar una portada CAD |
| `modelControls.ts` | Giro libre en pantalla, desplazamiento y zoom 3D, sin bloqueo en los polos ni inercia al soltar |
| `PdfViewer.tsx` | PDF.js en canvas: rueda sobre el cursor, arrastre del plano, encuadre y cambio de página |
| `parts.ts` | La unión *piezas declaradas + piezas con ficheros* y el reparto por pieza y tipo. Es la lógica de la lista |
| `PartActions.tsx` | Buscador de piezas registradas; seleccionar vincula una al feature |
| `PartIdentityEditor.tsx` | Código y nombre editables en la cabecera de la pieza, con autoguardado y recuperación de errores |
| `FeatureForm.tsx` | El formulario de alta y edición (datos básicos + warnings, lessons y **Piezas** con sus cotas). Lo montan `/features/nuevo` y la propia ficha en modo edición. 🔑 **Repite el reparto de la ficha** —foto a la izquierda, datos a la derecha, secciones debajo— con una casilla en el sitio de cada dato, para que entrar y salir de edición no mueva nada de sitio |
| `FeatureNotFound.tsx` | La pantalla de «feature no encontrado» de la ficha |
| `FeatureActions.tsx` | El botón *Editar* compartido por las tarjetas y la ficha; *Eliminar* vive en la ficha, con confirmación y solo para autor o superusuario |
| `NoteList.tsx` | Warnings y lessons **en modo edición**: título editable en su sitio, desplegable con el cuerpo dentro y autoguardado |
| `SourceFilePicker.tsx` | Selector de originales: elegir un archivo y vincularlo a esta tarjeta, sin opciones adicionales |
| `DocumentStatus.tsx` | Estado del original y aviso de archivo ausente/cambiado/inaccesible |
| `constants.ts` | Las etiquetas en castellano de los tipos de archivo y notas, y el icono de cada tipo |
| `queries.ts` | Claves de consulta: catálogo/fichas de features bajo `["features"]`; las piezas tienen `["parts"]` y otras consultas invalidan sus propias claves |

Y en `components/Common/`: `FileUpload.tsx` (drag and drop), `RichText.tsx` (editor y visor),
`CollapsibleSection.tsx` (los paneles desplegables).

### Piezas, cotas y archivos (actualizado el 22/09/2026)

Del 25/08 al 22/09/2026 la ficha del feature tenía un desplegable por pieza con una fila por
fichero, editable en línea. Desde el 22/09 **los archivos pertenecen a la pieza** y se
gestionan en su ficha. En la ficha del feature, cada pieza muestra sus **cotas** y el enlace
«Ver pieza»; el desplegable conserva el código y el nombre de la pieza.

**Añadir pieza** (editor del feature) busca exclusivamente en el catálogo registrado. Al
vincular una pieza por primera vez se copian sus archivos principales como adjuntos del
feature, sin copiar bytes ni sobrescribir los existentes. Esos adjuntos no se muestran en la
ficha del feature: los usan la portada CAD y el acceso al plano desde las cotas. No se
actualizan si después cambian los archivos de la pieza
([limitación](portadas-cad.md#origen-del-cad-de-la-portada)). **Nueva pieza** está en
Catálogo: selecciona una carpeta de Windows dentro del origen configurado, propone el
nombre completo y los archivos y prepara datos compatibles al crearla. El código se obtiene
del prefijo numérico de la carpeta o se asigna uno provisional estable `PIEZA-…`.
Se reutilizan registros existentes, sin crear carpetas ni duplicar piezas. Código y carpeta
son únicos; un código asociado a otra carpeta produce conflicto.

En la ficha de pieza, **Editar pieza** permite cambiar código, nombre, familia, cliente,
material, número de cavidades, descripción, carpeta y archivos. **Guardar cambios** los guarda
juntos y **Cancelar** los descarta.
Cambiar la carpeta propone sus archivos y conserva el título y el código ya editados. Uso
detallado en [archivos externos](ficheros-externos.md#uso-en-la-ficha-de-pieza). Código y
nombre también se editan en la cabecera de cada pieza dentro del editor del feature, con
autoguardado: son datos compartidos entre features. El selector nativo de Windows se abre
en la raíz configurada (`Exemples`); con SharePoint se usa un navegador de carpetas dentro de
la web. `folder_path` es la ruta relativa a la raíz, la misma en ambos orígenes.

La fila COTAS es compacta, con la altura de una fila de archivo. Añadir cota inserta un campo
al final que se guarda con Intro, al salir o con Guardar el feature; los errores conservan
el borrador. No solicita revisión ni relación. Reutiliza vínculos existentes sin cambiar
sus metadatos; para altas toma la revisión del estudio o una única revisión conocida de
la pieza/cota. Sin esa información queda «sin confirmar», sin asumir la revisión 06.

Si hay cotas importadas, Añadir cota ofrece primero un selector con búsqueda y revisión;
la alternativa manual conserva el comportamiento anterior. **Actualizar datos**, en la
sección Cotas de la ficha de pieza, procesa las tablas compatibles automáticamente sin
asignar sus cotas al feature.
Una pieza vinculada a varios features comparte las mismas importaciones.

La API de mediciones, su revisión explícita, los snapshots y los límites de cada vía se
mantienen en [Cotas y evidencia](cotas-y-evidencia-web.md#api-de-cotas-y-mediciones).
La tabla `MeasurementImport` conserva importaciones anteriores; consultar ese contrato
antes de cambiar la lectura automática o asumir que equivale al flujo CSV revisado.

Las piezas antiguas sin correspondencia en el origen siguen disponibles en el buscador.
La papelera elimina directamente del catálogo las piezas sin uso, sin confirmación;
las utilizadas muestran «Usada en X features» y tienen la papelera desactivada. Aunque el
contador de features sea cero, la API también rechaza piezas con importaciones, cotas o
documentos de evidencia. Se mantiene el permiso de superusuario. La API cuenta vínculos directos y adjuntos de cada feature una
sola vez. Borrar el registro conserva los originales: si su carpeta sigue en el origen,
continúa disponible para registrarla de nuevo. Las carpetas aún no registradas no muestran papelera.

Las tarjetas de pieza del feature se reordenan con el tirador y `@dnd-kit/react`, con
desplazamiento animado durante el arrastre. Space/flechas/Space permiten ordenar con teclado y
Escape cancela. `Feature.part_order` guarda el orden de piezas por feature, también usado en
consulta. El mismo arrastre se aplica a las advertencias y las lecciones, guardando
`position` en una sola operación por lista. Las listas no intercambian elementos al
arrastrar. La papelera de una tarjeta retira la pieza del feature, sus adjuntos copiados y
sus cotas asignadas en una transacción; conserva la pieza compartida, los otros features y
los originales. Al volver a la ficha se conserva el desplegado de cada pieza en la sesión del
navegador y se restaura el scroll de la ruta.

En la ficha de pieza, **Archivos** muestra el tipo, el tamaño y la descarga del original.
Pulsar el tipo abre la página del archivo (`/parts/{id}/fichero/{fileId}`). Allí se ve el
nombre del fichero y, si se ha elegido un nombre distinto en edición, se conserva como título.
La página muestra el visor del formato o la descarga. El plano tiene dos iconos de carpeta
de SharePoint para el vigente y el histórico, pendientes de conectar. En Molde y Moldflow
la cabecera ofrece la carpeta de SharePoint y la descarga. Cada fichero admite una captura
opcional que se guarda desde el lápiz y se comparte entre sus enlaces de pieza y feature.
En el modo local, un original ausente o modificado se rechaza y requiere revisar el vínculo
en **Editar pieza**. El tratamiento de cambios en Graph sigue el
[contrato del origen](ficheros-externos.md#sharepoint-microsoft-graph).

La página antigua `/features/{id}/fichero/{assetId}` sigue respondiendo para enlaces
guardados, con estado del original y **Volver a vincular**, pero la interfaz ya no enlaza a
ella. Si el adjunto carece de archivo, indica dónde gestionarlo y ofrece «Abrir pieza» cuando tiene una pieza asociada.

La selección del visor depende del MIME, extensión y tamaño. Los formatos admitidos,
límites de carga y componentes se mantienen en
[Ficheros externos, visores](ficheros-externos.md#visores-de-archivos). Los formatos sin
visor se descargan para abrirlos con su aplicación.

La aplicación no integra protocolos ni componentes de escritorio para abrir CAD local.
Su flujo es descargar → abrir desde la barra de descargas → Windows usa el programa asociado.
Una integración de escritorio sería un desarrollo adicional y requeriría instalación/configuración
en el equipo del usuario.

### El visor 3D

La aplicación muestra CAD y mallas y permite crear portadas seleccionando superficies y
encuadre. En Piezas y Features, el CAD de producto se muestra sombreado con aristas
visibles. El STEP aporta el perímetro de cada cara, incluidas las uniones tangentes.
La misma representación se usa al marcar caras y al generar las portadas automáticas.
Las mallas que solo contienen triángulos permiten aproximar las aristas por el cambio de
ángulo entre caras. Las capturas guardadas a mano se actualizan al volver a guardarlas.
Consultar [interacción y formatos](ficheros-externos.md#visores-de-archivos),
[portadas y selección de caras](portadas-cad.md) y
[conversión de archivos grandes a GLB](vistas-3d.md).

La carga es dinámica, pero también puede producirse al generar automáticamente una captura
de pieza en el catálogo. La comprobación histórica con originales del piloto está en
[Ficheros externos](ficheros-externos.md#verificación-con-el-3212).

### El visor de planos PDF

`PdfViewer.tsx` muestra el documento y los controles de página, zoom y encuadre. Su contrato
técnico está en [Visores de archivos](ficheros-externos.md#visores-de-archivos). La búsqueda
de cotas y sus marcas revisadas se describe en [Consulta del plano](interfaz.md#consulta-del-plano),
y el índice que la alimenta en [Cotas y evidencia](cotas-y-evidencia-web.md#indexación-y-revisiones).
El canvas no recupera detalle que no exista en la imagen de origen.

El visor usa el mismo giro por página que la miniatura y transforma también las coordenadas
de las cotas al encuadrarlas. El backend infiere el giro por la dirección del texto. Cuando
esa señal es insuficiente, compara mediante OCR el texto legible en la zona del cajetín
para los cuatro giros posibles. En caso de duda conserva la orientación del PDF.

### La ficha es una página, no una modal (2026-08-19)

Hasta el 2026-08-19 la ficha era una modal de 672 px. Ahora es la página `/features/{id}`, y la
modal se ha borrado. El motivo no es estético:

- **La ficha es el destino de la herramienta**, no una vista previa. Con URL propia se puede
  enviar por Teams, guardar en favoritos y enlazar desde estos `docs/`.
- La **cabecera repite la lectura de la tarjeta del buscador** —imagen a la izquierda, identidad
  a la derecha— para que el salto del resultado a la ficha no obligue a releer nada. Debajo, lo
  que hay que saber para diseñar: advertencias, lecciones y las piezas con sus cotas (desde el
  22/09/2026 los archivos se consultan en la ficha de pieza).
- **Cabe lo que viene.** La matriz pieza × tipo ya se salía en la modal; los muestreos y las
  correcciones de molde de la siguiente fase no habrían entrado de ninguna manera.
- **El formulario tampoco es una modal.** Era una modal con warnings, lessons, piezas y cinco
  tipos de fichero dentro de 672 px, que además abría modales encima de la modal. Ahora el alta
  es `/features/nuevo` y la edición ocurre **dentro de la propia ficha**. Desde el 2026-08-25
  las notas se editan **en línea** (`NoteDialog` y `AssetDialog` se han borrado; ver abajo) y
  desde el 22/09/2026 los archivos se editan en la ficha de pieza. Se mantienen
  confirmaciones de borrado, el diálogo de cambios pendientes y los diálogos para crear o
  ampliar una portada CAD.

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
las notas, las piezas vinculadas y sus cotas se guardan en línea. Los archivos no se editan
aquí: pertenecen a la pieza y se guardan con **Guardar cambios** en su ficha. **Los dos dejan
la misma ficha en lectura**.
Cambiar de modo reemplaza la entrada del historial: *atrás* vuelve al catálogo con sus filtros
y posición, sin recorrer modos de edición anteriores. El modo vive en la URL y no en un `useState` por
dos motivos: el *Editar* de la lista entra directo a él, y recargar (F5) no te echa de la
edición. Antes de salir, se completan los guardados pendientes de notas, piezas y cotas, y las
subidas; si fallan, se conserva la edición y se muestra el error. **Cancelar descarta la
cabecera**, no deshace las notas, piezas ni cotas guardadas en línea. `validateSearch` lo declara **opcional**, o el catálogo no podría enlazar la ficha sin
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
| Archivo de una pieza | Fila con el nombre + lápiz → modal con tipo, pieza y fichero | En la ficha de pieza, con **Editar pieza**: tipo, nombre visible y archivo en la propia fila. Se guarda con la cabecera, sin autoguardado |
| Añadir | Modal vacía que hay que rellenar y confirmar | Crea la fila en el momento, abierta y con el texto seleccionado para escribir encima |

Las notas mantienen el botón de borrar y edición en línea. Los archivos de la pieza agrupan
en su fila el tipo, el nombre, el cambio de archivo y la papelera, sin botones debajo.

🔑 **Autoguardado de notas, sin botón de guardar**: se envían solo los campos modificados localmente
tras **0,7 s**, mediante `PUT` parcial (`model_dump(exclude_unset=True)`). Las escrituras se
serializan: una respuesta antigua no dispara una escritura que deshaga cambios posteriores.
Una actualización del servidor sincroniza los campos limpios, sin convertir diferencias
ajenas en ediciones locales. Los campos pendientes de la cabecera sobreviven a los refrescos.
Plegar una sección de edición conserva montados sus borradores; guardar o navegar espera los
guardados pendientes. La cabecera se sigue guardando mediante su botón.

- El **título vacío no se guarda** (`min_length=1` en el backend): el campo se marca en rojo y se
  queda esperando. En la ficha de pieza, un archivo sin nombre visible se marca en rojo y
  bloquea **Guardar cambios**.
- Al **añadir un archivo a la pieza**, el nombre visible es el del fichero y el tipo se propone
  por la extensión: `.pdf` → plano, `.stl`/`.obj`/`.ply`/`.glb`/`.gltf` → escaneo, `.mfr`/`.mpi` →
  Moldflow. `.step`, `.stp`, `.igs` e `.iges` se proponen como molde si la ruta contiene «molde», «mold»
  o «mould», y como CAD en otro caso. El tipo se puede cambiar antes de guardar.

### Tres cosas del frontend que hay que saber

1. **El alta muestra cabecera, warnings, lessons y piezas desde el primer momento.** Abrir o
   cancelar el formulario vacío no crea registros. La primera nota o pieza crea automáticamente
   el feature con los datos actuales y nombre provisional «Nuevo feature» si falta título. Las
   altas simultáneas comparten esa misma creación. Las notas, las piezas y sus cotas se guardan
   al vuelo; Guardar espera las operaciones pendientes y termina en la ficha de consulta.

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
   libre. Un editor futuro deberá mantener el contrato Markdown o adaptar también la
   persistencia, renderización e imágenes; no asumir que será solo frontend.

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
endpoints. Reconstruir la imagen o usar el modo de desarrollo apropiado.

Para comprobar **el estado de las migraciones dentro de esa imagen**:

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic heads     # current debe coincidir con heads
```

Que `current` coincida con `heads` **no demuestra que la imagen contenga el código actual**:
ambos comandos podrían estar usando una imagen antigua. El frontend en desarrollo con Vite
sirve desde el disco; el frontend construido en Docker también requiere reconstrucción.

### Datos de ejemplo

Hay una carga opcional con el **Bolt Eye del 3212**: sus 8 warnings y 2 lessons learned, sacados
de [modelo-datos.md](modelo-datos.md) y [3212/historial-molde.md](../conocimiento/0-bolt-eye/3212/historial-molde.md).

```powershell
docker compose exec backend python -m app.seed_features
```

Es idempotente: si el feature ya existe no toca nada. La creación completa usa una transacción:
un fallo revierte el ejemplo entero y permite reintentar. Crea la pieza **3212 Pump Housing**, la
declara en el feature y le cuelga los cinco adjuntos, uno por tipo. Los adjuntos se crean **sin
fichero**: los originales se vinculan después desde la aplicación. El seed no depende de rutas
personales. También vincula N170, N117, N178 y N288 de la revisión del piloto; la carga
no realiza una importación de medidas. Los vínculos a originales dependen de cada instalación.

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

Comandos para ejecutar las comprobaciones; **no se han ejecutado en esta revisión documental**.
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
| **Vincular un feature con sus N-numbers y sus cotas** | Implementado con `PartCharacteristic` + `FeatureCharacteristicLink` (cota por pieza y revisión, con rol); ver [Cotas y evidencia](cotas-y-evidencia-web.md). Las tolerancias se leen de las mediciones importadas; el modelo normalizado `INSTANCIA_EN_PROYECTO` de [modelo-datos.md](modelo-datos.md) sigue pendiente |
| **Vistas ligeras de escaneo y molde** | Implementadas: cola persistente, GLB en caché, original intacto y descarga íntegra; ver [vistas-3d.md](vistas-3d.md) |
| **Conexión Microsoft 365** | Implementada el 22/10/2026 con la app de Eurecat (login delegado + Graph). Login real el 30/10 y retorno automático el 09/11/2026; pendiente la primera prueba real de archivos. INTEPLAST: confirmar ubicación y permisos con su IT (A10, prioridad 1). Se direcciona por ruta: un renombrado rompe el vínculo. Ver [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| **La ficha de una pieza** | Implementada el 22/09/2026: `/parts/{id}` con identidad, carpeta, Cotas, Features y Archivos (`Parts/PartDetailPage.tsx`) |
| **Adjuntos del feature copiados de la pieza** | No se actualizan si cambian los archivos de la pieza; afecta a la portada CAD y al plano de la fila COTAS. Ver [portadas CAD](portadas-cad.md#origen-del-cad-de-la-portada) |
| **Sustitución del asistente** | Integrado el 18/11: Codex como motor de fondo de la prueba local, mediante puente de Windows y lecturas del backend existente; sin cambios del frontend ni Ollama. Búsqueda por palabras, respuesta completa y una llamada simultánea al modelo. Copilot sigue pendiente como solución final. Ver [asistente](asistente.md#prueba-local-integrada-18112026) |
| **Correcciones de otras piezas** | Las mediciones ya son genéricas; las correcciones XLS/PPTX solo se interpretan en el 3212. Ejemplos recibidos; faltan resultados esperados revisados y generalizar el lector. Ver [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx) |

### Nombre real del fichero en las tarjetas (2026-09-17)

La decisión del 17/09 afectaba a los adjuntos `FeatureAsset`: al vincularlos, la API toma
el nombre de `StoredFile.filename`; la migración `f170a3c9de85` actualizó esas etiquetas.
La ficha de pieza posterior usa **`PartFile.name`, un nombre visible editable**, separado
del nombre original. Cambiarlo no renombra el fichero original. No aplicar la regla
histórica de los adjuntos a todas las filas de archivos de la UI actual.

El selector tiene una sola acción: vincular el archivo elegido a esta tarjeta. Cambiar el archivo
de una tarjeta no cambia el documento de otros features. Se han retirado el texto introductorio
y las opciones de reemplazar/actualizar el documento compartido. La API de actualización explícita
de referencias sigue disponible para integraciones, y mantiene sincronizados los nombres.
