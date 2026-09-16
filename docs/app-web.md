# La aplicación web — base de conocimiento de features

> La prueba de concepto descrita en `inteplast_PADIH_fase_B.md`, implementada sobre la plantilla
> `full-stack-fastapi-template`: **backend** en `backend/`, **frontend** en `frontend/`.
>
> Este documento cubre **lo que se ha construido y por qué**. Las trampas de los datos crudos
> están en [formatos-parsing.md](formatos-parsing.md); el modelo del dominio completo (proyectos,
> muestreos, mediciones, correcciones de molde) en [modelo-datos.md](modelo-datos.md).

---

## Qué hay implementado

El **bloque transversal** del modelo de datos: `FEATURE` + `WARNING` + `LESSON_LEARNED` +
ficheros de ejemplo. Es lo que consume el frontend descrito en la fase B y lo que responde a
*«dame todo del Bolt Eye»*.

Y desde el **2026-08-18**, la **pieza como entidad propia** (`Part`): los ficheros ya no cuelgan
del feature sueltos, cuelgan de la pieza a la que pertenecen. Es el embrión de `PROYECTO`.

Desde el **2026-09-15**, una ficha puede **vincular originales externos** sin subirlos. El PDF y
el STEP del 3212 están conectados y comprobados en la instalación local. Configuración, límites
de revisión y futura conexión Graph en [ficheros-externos.md](ficheros-externos.md).

🔴 **Lo que NO está**: la parte de ingesta (`MUESTREO`, `MEDICION`, `CORRECCION_MOLDE`,
`DEPENDENCIA_COTA`). Esas tablas se alimentan de los CSV/XLS/PPTX y son la siguiente fase.

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
| `Part.code` es **UNIQUE** y el alta va por desplegable, no por texto libre | Es la clave con la que se agrupa todo. Escrito a mano acababa en dos piezas por cada pieza real |
| `FeaturePartLink` es una tabla de unión **sin campos propios** | Hoy solo dice *«este feature está en esta pieza»*. Cuando llegue la ingesta, aquí cuelgan los N-numbers y las tolerancias y pasa a ser `INSTANCIA_EN_PROYECTO` |
| Borrar una pieza es **solo de superusuario** | Es compartida por todos los features; no tiene autor al que atribuirla |

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
| `GET` | `/features/filters` | Categorías, tags y piezas **que algún feature usa**, para los desplegables |
| `POST` | `/features/` | Crear |
| `GET` | `/features/{id}` | Ficha completa: + `notes` + `assets` |
| `PUT` `DELETE` | `/features/{id}` | Editar / borrar |
| `POST` | `/features/{id}/notes` | Añadir warning o lesson learned |
| `PUT` `DELETE` | `/features/notes/{id}` | Editar / borrar una nota |
| `POST` `DELETE` | `/features/{id}/parts/{part_id}` | Declarar / quitar una pieza sin ficheros |
| `POST` | `/features/{id}/assets` | Adjuntar el fichero de una pieza |
| `PUT` `DELETE` | `/features/assets/{id}` | Editar / quitar un adjunto |
| `GET` `POST` | `/parts/` | Listar y dar de alta piezas |
| `PUT` | `/parts/{id}` | Editar código o nombre. El código es único: choque → `409` |
| `DELETE` | `/parts/{id}` | Borrar una pieza. **Solo superusuario** |
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
- **Borrar piezas**: solo superusuario.
- **Gestión de usuarios**: superusuario, como en la plantilla.

---

## Frontend (`frontend/src/`)

| Ruta | Fichero | Qué es |
|---|---|---|
| `/` | `routes/_layout/index.tsx` | **Dashboard**: buscador global + filtros y tarjetas de resultado. La búsqueda va en la URL (`/?q=3212`) |
| `/features/{id}` | `routes/_layout/features_.$featureId.tsx` | 🔑 **La ficha del feature**: cabecera con la imagen a la izquierda e identidad a la derecha (nombre, descripción, categoría, tags, piezas), y debajo a todo el ancho warnings, lessons y los ficheros por pieza. **Se edita aquí mismo** (ver abajo) |
| `/features` | `routes/_layout/features.tsx` | **Gestión** (la página «Ítems» de la fase B): mismas tarjetas, con *Añadir feature* y, en cada una, *Editar* y *Borrar* |
| `/features/{id}/fichero/{assetId}` | `routes/_layout/features_.$featureId_.fichero.$assetId.tsx` | 🔑 **La página de un fichero**: el visor (PDF, imagen o 3D), el botón de descargar y, cuando no hay visor posible, qué programa hace falta |
| `/features/nuevo` | `routes/_layout/features_.nuevo.tsx` | **Alta**. Al guardar los datos básicos salta a la ficha en modo edición, que es donde se le cuelgan notas y ficheros |
| `/admin` | `routes/_layout/admin.tsx` | Usuarios y permisos; punto de alta de cuentas con el registro público cerrado |

Componentes en `components/Features/`:

| Fichero | Qué |
|---|---|
| `FeatureSearch.tsx` | Buscador + tres desplegables (molde, categoría, tag) poblados desde `/features/filters`, y los ayudantes que traducen ese estado a los *search params* de la URL |
| `FeatureCard.tsx` | La tarjeta: imagen, nombre, descripción, tags y el resumen *«2 piezas · 3197, 3212»* |
| `PartAssetList.tsx` | 🔑 **Los ficheros agrupados por pieza**: un desplegable por pieza y dentro una fila por fichero. **El mismo componente sirve la ficha y el formulario** (`editable`) |
| `viewers.ts` | Extensión → visor, carga directa hasta 50 MiB y GLB automático para STL/STEP grandes |
| `ModelViewer.tsx` | El visor 3D (three.js + OpenCascade en WASM). Se carga con `import()` dinámico: no pesa nada hasta que alguien abre un 3D |
| `modelControls.ts` | Giro libre en pantalla, desplazamiento y zoom 3D, sin bloqueo en los polos ni inercia al soltar |
| `PdfViewer.tsx` | PDF.js en canvas: rueda sobre el cursor, arrastre del plano, encuadre y cambio de página |
| `parts.ts` | La unión *piezas declaradas + piezas con ficheros* y el reparto por pieza y tipo. Es la lógica de la lista |
| `PartSelect.tsx` | Desplegable de piezas con alta al vuelo (código + nombre) |
| `FeatureForm.tsx` | El formulario de alta y edición (datos básicos + warnings, lessons, **Piezas** y **Ficheros por pieza**). Lo montan `/features/nuevo` y la propia ficha en modo edición. 🔑 **Repite el reparto de la ficha** —foto a la izquierda, datos a la derecha, secciones debajo— con una casilla en el sitio de cada dato, para que entrar y salir de edición no mueva nada de sitio |
| `FeatureNotFound.tsx` | La pantalla de «feature no encontrado» de la ficha |
| `FeatureActions.tsx` | Los botones *Editar* y *Borrar* de la tarjeta de gestión |
| `NoteList.tsx` | Warnings y lessons **en modo edición**: título editable en su sitio, desplegable con el cuerpo dentro y autoguardado |
| `AssetEditRow.tsx` | Fila **en edición**: tipo/pieza, nombre, subida y vínculo a un archivo existente |
| `SourceFilePicker.tsx` | Diálogo de selección de originales; vincular o volver a vincular con revisión opcional |
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
o ha cambiado, **Volver a vincular** permite corregir la ubicación/revisión. El selector es un
diálogo; los visores siguen en su página. Al volver se conserva el desplegado por pieza en la
sesión del navegador y se restaura el scroll de la ruta.

Lo decide `viewers.ts` a partir del tipo MIME, la extensión y el tamaño: los PDF con tipo
`application/pdf` y las imágenes JPEG, PNG, GIF, WebP, AVIF y BMP se pintan en la página.
La imagen de cabecera admite esos mismos formatos al seleccionar, arrastrar o pegar (Ctrl+V);
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
la ficha puede activar o ampliar el 3D. La selección queda ligada a la revisión del documento.

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

🔑 **Cada página tiene su tarjeta** (2026-08-24). En el **dashboard** la tarjeta se clica y
lleva a la ficha: se viene a consultar. En **gestión** la tarjeta **no se clica** — lleva sus dos
botones, *Editar* y *Borrar*, y no hay otro sitio al que ir. Antes clicarla llevaba a la ficha en
modo `gestion`: la misma ficha de solo lectura del dashboard, con esos mismos dos botones arriba
a la derecha. Un paso de más para nada, y el menú `⋯` de la tarjeta eran otros dos clics para
elegir entre dos cosas. **Ese modo `gestion` se ha borrado**, botones y *search param* incluidos.

🔑 **La ficha tiene dos caras, y las dos son la misma página** — solo cambia un *search param*:

| Desde | URL | Qué enseña |
|---|---|---|
| Dashboard | `/features/{id}` | Solo lectura. Se consulta, no se toca |
| *Editar* de la lista | `?editar=true` | **El mismo contenido, en el mismo sitio, editable** |

*Editar* no cambia el reparto de la página: el nombre sigue siendo el nombre —ahora en una
casilla—, la foto sigue a la izquierda —ahora se puede soltar otra encima—, y las secciones
siguen debajo, con sus botones de añadir y borrar. Arriba a la derecha están *Cancelar* y
*Guardar*, y ahí es donde tienen que estar: lo único que se guarda a mano es la cabecera, porque
las notas y los ficheros se guardan en línea. **Los dos devuelven a
`/features`**, que es de donde se venía: dejar la ficha en solo lectura sería un callejón sin
salida, porque ahí ya no hay botón de editar. El modo vive en la URL y no en un `useState` por
dos motivos: el *Editar* de la lista entra directo a él, y recargar (F5) no te echa de la
edición. Antes de salir, se completan los guardados pendientes de notas/adjuntos y las subidas;
si fallan, se conserva la edición y se muestra el error. **Cancelar descarta la cabecera**, no
deshace las notas ni los adjuntos guardados en línea. `validateSearch` lo declara **opcional**, o el dashboard no podría enlazar la ficha sin
pasarlo (TanStack exige en los enlaces todo search param que el validador declare obligatorio).

**No hay botón *Volver*** en ninguna de las dos: para eso están el botón del navegador y el menú
lateral. El único que queda es el de «Feature no encontrado», donde no hay nada más donde pulsar.

🔑 **La búsqueda vive en la URL** (`validateSearch` en las dos rutas). Sin eso, volver de la ficha
con el botón *atrás* devolvía el buscador vacío — que es el precio que se paga por cambiar una
modal por una página, y por eso se pagó de entrada. El input sigue siendo estado local y se
refleja en la URL con `replace: true` tras el *debounce*, para no dejar una entrada de historial
por tecla.

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

1. **Al crear un feature, `/features/nuevo` salta a su ficha en modo edición.** Los warnings,
   lessons y adjuntos necesitan que el feature exista para colgarse de él, así que el alta solo
   pide los datos básicos y al guardar te deja en la ficha ya editable, con esas secciones. Los
   datos básicos se guardan con el botón; las notas y los adjuntos **se guardan solos según se
   escriben**.

2. 🔴 **Radix `Select` dentro de un `<form>` dispara `onValueChange("")` él solo** mientras su
   lista no se haya abierto. En el formulario del feature eso **borraba la categoría**: el
   desplegable enseñaba *Sin categoría* aunque el feature fuera `hole`, y al guardar el `PUT`
   salía con `category: ""` → **422 «Something went wrong!»**. Venía de la modal original, no del
   cambio a páginas. El corte está en `FeatureForm.tsx` y en `PartSelect.tsx`:

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
.\scripts\compose.ps1 up -d --build db prestart backend   # aplica las migraciones al arrancar
cd frontend; npm run dev                           # http://localhost:5173
```

El lanzador carga también `.env.local` si existe y mantiene el montaje de originales. En Bash,
usar `bash scripts/compose.sh`. Configuración en [ficheros-externos.md](ficheros-externos.md).

🔴 **Sin `.\scripts\compose.ps1 watch backend`, hay que usar `--build` después de tocar `backend/`.** El Dockerfile copia el código
dentro de la imagen; si ya existe un `backend:latest`, `docker compose up -d` a secas **lo
reutiliza tal cual** y arrancas con el código viejo — sin errores, simplemente faltan los
endpoints. Cómo se detecta:

```powershell
.\scripts\compose.ps1 exec backend alembic current
.\scripts\compose.ps1 exec backend alembic heads     # current debe coincidir con heads
```

El frontend no tiene este problema: Vite sirve desde el disco.

### Datos de ejemplo

Hay una carga opcional con el **Bolt Eye del 3212**: sus 8 warnings y 2 lessons learned, sacados
de [modelo-datos.md](modelo-datos.md) y [3212/historial-molde.md](3212/historial-molde.md).

```powershell
.\scripts\compose.ps1 exec backend python -m app.seed_features
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
| **Sin paginación en la UI** | La API ya la tiene (`skip`/`limit`); gestión pide 100 y el dashboard 50 al buscar o 5 recientes. Con más fichas hay que añadir controles |
| **Ordenar warnings y adjuntos arrastrando** | El campo `position` ya está en la BD y se respeta al leer, pero la UI todavía no deja reordenar |
| **Imagen con la zona marcada en rojo** | Implementada la [portada CAD](portadas-cad.md): caras del STEP, captura, cámara y 3D interactivo. El marcado libre sobre imágenes/planos sigue pendiente |
| **Vincular un feature con sus N-numbers y sus cotas** | La tabla ya existe (`FeaturePartLink`), pero está vacía de contenido: solo dice *feature ↔ pieza*. Añadirle los N-numbers y las tolerancias la convierte en el `INSTANCIA_EN_PROYECTO` de [modelo-datos.md](modelo-datos.md) |
| **Vistas ligeras de escaneo y molde** | Implementadas: cola persistente, GLB en caché, original intacto y descarga íntegra; ver [vistas-3d.md](vistas-3d.md) |
| **Conexión Microsoft 365** | Adaptador local implementado. Confirmar ubicación/permisos con IT (A10, prioridad 1) y desarrollar Graph con IDs estables; los visores usan el UUID interno del documento |
| **La ficha de una pieza** | Hoy `Part` solo tiene código y nombre; el desplegable permite crear y seleccionar, no editar piezas existentes. La API sí permite editarlas. No hay página propia de pieza |
