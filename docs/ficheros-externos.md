# Archivos originales externos y visores

Implementado y comprobado el **2026-09-15**. La aplicación puede vincular archivos que ya
existen en una carpeta accesible al backend. Se guardan sus metadatos y su referencia; los
originales se leen cuando se abre el visor o se descarga. Las subidas siguen disponibles.

## Uso en la ficha

1. Abrir **Bolt Eye → Editar → Piezas ejemplo → 3212**.
2. En la fila del plano o del CAD, pulsar el **icono de cadena**, junto a la descarga.
3. Entrar en `1-2D y 3D Pieza`, seleccionar el fichero y, si se conoce, indicar su revisión.
4. Pulsar **Vincular**. La asociación se guarda automáticamente; **Guardar** guarda también
   los cambios de la cabecera y vuelve al listado.
5. Abrir el fichero desde la ficha. Tiene una **página propia** con enlace para volver al
   feature. El selector de archivos es un diálogo; el visor permanece en la página.

El PDF se muestra como una imagen interactiva: **rueda para ampliar donde está el cursor y
arrastre izquierdo para mover el plano**. Tiene acercar/alejar, **Encuadrar** y cambio de página
si hay varias. **Abrir en pestaña** y **Descargar** permiten acceder al PDF original.
El 3D permite girar con arrastre izquierdo, acercar/alejar con la rueda y **Encuadrar**;
el arrastre derecho o central desplaza la pieza. El giro es libre y se detiene al soltar.
Los archivos sin visor también tienen una página de
detalles y descarga. Los desplegables por pieza y la posición de scroll se recuperan al volver.

La ficha muestra el nombre legible y el tamaño, sin repetir nombres internos, rutas ni etiquetas
de revisión. Tampoco muestra el pie «Archivo vinculado» cuando todo está disponible. Conserva
los avisos de «sin archivo vinculado», no encontrado, original cambiado y origen inaccesible.
Desde el icono de cadena se elige un archivo y se pulsa **Vincular**. Ese archivo sustituye
al vínculo de la tarjeta actual; las demás fichas conservan sus documentos. El selector ya no
pide elegir entre reemplazar y actualizar un documento compartido, ni muestra texto introductorio.
La tarjeta y el visor muestran el nombre real completo, incluida la extensión.

Seleccionar de nuevo el mismo archivo, con la misma fecha/tamaño, reutiliza su registro.
El selector no pide una etiqueta de revisión. La API conserva la etiqueta existente al omitirla;
una etiqueta distinta devuelve conflicto. La actualización explícita del documento compartido
sigue disponible en `PUT /files/{id}/reference` para integraciones, fuera de este selector.

La cabecera puede usar una [portada creada desde el STEP](portadas-cad.md), con superficies
marcadas en rojo. El marcado se guarda en la aplicación y mantiene intacto el original.

## Configuración local con Docker

En el equipo de desarrollo de Eduard ya está configurado `.env`, excluido de Git, para
la carpeta `Exemples` indicada en [CLAUDE.md](../CLAUDE.md), con una subcarpeta por pieza. Esto utiliza la
copia local sincronizada por OneDrive. **No inicia sesión en Microsoft ni usa Microsoft Graph.**

Esta conexión local es temporal. Cada pieza guarda su `folder_path` relativo al origen;
el selector de ficheros comienza ahí. Código, nombre y carpeta se comparten entre features,
pero cada ficha vincula solo los ficheros que necesita. La futura conexión con SharePoint/OneDrive
deberá sustituir el acceso al origen manteniendo esta interacción.

El 2026-09-17 se amplió el montaje desde `Exemples/3212 Pump Housing` a `Exemples`.
Los cuatro documentos existentes se actualizaron añadiendo `3212 Pump Housing/` a sus rutas
y recalculando sus claves de deduplicación; conservaron UUID, versión y vínculos. La pieza 3212
quedó asociada a esa subcarpeta. Se verificó la disponibilidad de los cuatro originales y se
guardó una copia previa de la BD y `.env` fuera del repositorio. En otra instalación que cambie
su carpeta raíz, también hay que adaptar las rutas relativas existentes.

En otro equipo, crear `.env` a partir de [.env.example](../.env.example), sin sobrescribir una
configuración existente. Descomentar el bloque de originales externos y ajustar:

| Variable | Qué representa |
|---|---|
| `ASSETS_HOST_PATH` | Carpeta común de las piezas, fuera del repo. En Windows usar `/`, por ejemplo `C:/datos/Exemples` |
| `ASSETS_SOURCE_ID` | Nombre estable del conjunto de datos, independiente de la ruta del PC |
| `ASSETS_SOURCE_NAME` | Nombre que muestra el selector |
| `COMPOSE_FILE`, `COMPOSE_PATH_SEPARATOR` | Activan `compose.yml`, `compose.override.yml` y `compose.assets.yml`; conservar los valores del ejemplo |

Desde la raíz:

```powershell
docker compose up -d --build db prestart backend mailcatcher
npm.cmd run dev
```

El mismo comando funciona en PowerShell y Bash. `docker compose watch backend`, `exec` y
`up` leen automáticamente `.env`, también en una terminal nueva; no se necesitan variables
exportadas ni un lanzador especial. Si el bloque de originales queda comentado, la aplicación
arranca con subidas y el selector indica que no hay origen configurado.

### Migración desde `.env.local`

La configuración se unifica en `.env` desde el **2026-09-16**. En una instalación existente:

1. Conservar una copia privada de `.env` y `.env.local` antes de actualizar el repositorio.
2. Incorporar a `.env` las variables de `.env.local`, conservando sus valores y evitando
   claves duplicadas. **No cambiar `ASSETS_SOURCE_ID`**: lo usan los documentos ya vinculados.
3. Archivar `.env.local` fuera del repositorio; deja de ser un fichero activo de configuración.
4. Detener el `watch` anterior con Ctrl+C y arrancar `docker compose watch backend`.

`.env` ya no se versiona y `.env.example` contiene únicamente valores de ejemplo. No copiar la
plantilla sobre una instalación existente. Los antiguos `scripts/compose.*` quedan como alias
compatibles que leen ese mismo `.env`. La configuración del equipo de Eduard ya está migrada.

### Montaje y backend nativo

`compose.assets.yml` monta únicamente la carpeta elegida en `/external-assets`, con
`read_only: true` y `create_host_path: false`. La aplicación no escribe, renombra ni borra los
originales. No combinar este Compose con `compose.test.yml`: las pruebas usan archivos sintéticos
en almacenamiento temporal. En un backend Python nativo, configurar directamente `ASSETS_ROOT`
con la ruta local y los mismos `ASSETS_SOURCE_ID`/`ASSETS_SOURCE_NAME`; el montaje de Compose no
se aplica a procesos Python externos a Docker. Para imponer solo lectura allí, usar permisos del SO.

### OneDrive y cambios de ubicación

- Los archivos que se van a abrir deben estar **disponibles localmente**. Comprobar los
  atributos de OneDrive antes de leerlos; no descargar recursivamente el proyecto.
- Listar o vincular consulta metadatos, sin leer el contenido. En Windows nativo se rechazan
  los atributos de archivo solo en la nube. **Docker Linux no expone necesariamente esos
  atributos**: no garantiza detectar un placeholder antes de que Windows intente descargarlo.
- Si cambia solo la ubicación de la carpeta raíz, ajustar `ASSETS_HOST_PATH` y recrear el
  backend, conservando `ASSETS_SOURCE_ID` y la estructura interna.
- Si se renombra o mueve un archivo dentro de la carpeta, esta integración local requiere
  **Volver a vincular**. No identifica automáticamente el nuevo nombre.
- Si se conecta otro conjunto de datos, darle otro `ASSETS_SOURCE_ID`. Las referencias antiguas
  se mostrarán inaccesibles en vez de resolver silenciosamente una ruta de otro conjunto.

## Modelo y API

```text
FeatureAsset.file_id → StoredFile.id → adaptador del origen → contenido
                                      upload: /app/uploads/{id}
                                      local: ASSETS_ROOT + ruta relativa
```

`StoredFile` conserva su nombre y sus UUID anteriores, pero ahora representa un documento con
origen `upload` o `local`. El visor y la ficha siguen usando `file_id`; no reciben rutas absolutas
del PC. [file_sources.py](../backend/app/file_sources.py) concentra la resolución de contenido.

Campos nuevos: `source`, `source_key`, `source_path`, `source_version`, `version`, `revision`
y `reference_key`. `reference_key` deduplica conjunto/ruta/estado mediante SHA-256 **de esos
metadatos**. `version` es un UUID que cambia al volver a vincular e invalida enlaces firmados
anteriores; `expected_version` evita sobrescribir una vinculación concurrente.

**La revisión local no es un archivo histórico.** `source_version` compara fecha de modificación
en nanosegundos y tamaño. Detecta cambios normales y bloquea la lectura hasta revisarlos, pero no
detecta una modificación que conserve ambos metadatos. No calcula un hash del contenido al
vincular ni conserva los bytes de revisiones anteriores. La etiqueta `revision` la introduce
el usuario; no se infiere una revisión de ingeniería a partir de cualquier fecha del nombre.

Rutas autenticadas, bajo `/api/v1`:

| Método y ruta | Función |
|---|---|
| `GET /files/source?path=…&skip=0&limit=50` | Listar una carpeta, sin recursión; máximo 200 elementos por página |
| `POST /files/reference` | Registrar/reutilizar `{path, revision?}` sin subir bytes |
| `PUT /files/{id}/reference` | Volver a vincular con `{path, revision?, expected_version}` |
| `GET /files/{id}/status` | Estado y ruta relativa; nunca la raíz del equipo |
| `GET /files/{id}/access-url` | Enlace temporal para el visor o para descargar con `download=true` |
| `GET /files/{id}` | Contenido autorizado; admite peticiones de rangos de bytes del PDF |
| `DELETE /files/{id}` | Borrar el registro; solo borra bytes si el origen es una subida |

Se rechazan rutas absolutas, `..`, enlaces simbólicos y archivos especiales. Todos los usuarios
activos de esta base colaborativa pueden leer el origen configurado y vincular archivos; no se
han añadido permisos por documento. Un UUID solo no autoriza una descarga.

La migración `a62f58d4e930` asigna `source=upload` a registros anteriores y mantiene sus enlaces.
Su downgrade se rechaza mientras existan referencias externas. Hacer copia de BD antes de
actualizar y conservar `.env` por separado. El backup de la app **no incluye** los originales
externos; su conservación corresponde al almacenamiento que los contiene.

## Integración futura con INTEPLAST

La **prioridad 1 de la reunión** es confirmar con informática dónde están los originales y cómo
autorizar su lectura: [pregunta A10](preguntas-abiertas.md#a10-acceso-originales).

Propuesta para Microsoft 365: añadir un adaptador Graph con identidad de organización, unidad
y archivo; mantener el UUID interno de documento y el contrato de los visores. Microsoft ofrece
[direcciones por ID](https://learn.microsoft.com/en-us/graph/onedrive-addressing-driveitems),
que permiten seguir el archivo cuando cambia de nombre. Habrá que implementar autenticación,
listado, lectura/rangos, estados y política de revisiones. La migración de nuestras referencias
locales a esos IDs exige una asociación explícita; cambiar una variable no conecta dos empresas.

Los permisos se acordarán con IT, acotados al contenido necesario. Evaluar los
[permisos Selected](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
según su biblioteca y usuarios; no presuponer acceso a todos los archivos del tenant.
**Graph todavía no está implementado.** Esta separación permite incorporarlo sin reescribir
el renderizado PDF/3D; el selector y la gestión del origen sí necesitarán esa integración.

## Verificación con el 3212

En la instalación local se han vinculado a las filas existentes del Bolt Eye:

| Archivo original, dentro de `1-2D y 3D Pieza` | Tamaño exacto | Etiqueta |
|---|---:|---|
| `20250523_DRW 0140S00237_07.pdf` | 1.487.728 bytes | `07` |
| `20200204_3 130 516 987_AllCATPart.stp` | 10.549.640 bytes | `2020-02-04 (nombre de origen)` |

Comprobado en Chromium **145.0.7632.6**, con la aplicación y su API reales:

- Seleccionar y vincular ambos originales desde el editor, sin subir sus contenidos.
- Ver el PDF completo, ampliar alrededor del cursor y arrastrarlo en ambos ejes. La rueda
  no desplaza la página web. Es el escaneo original: los detalles
  pequeños conservan su limitación de resolución. Sigue pendiente pedir un plano mejor.
- Cargar el STEP (**83.132 triángulos**), girar, hacer zoom y encuadrar.
- Descargar ambos mediante la interfaz: SHA-256 idéntico al original de cada archivo.
- Volver al feature y abrir de nuevo ambos visores, sin errores JavaScript de la aplicación.
- Recrear el backend y comprobar que persisten los mismos UUID, la disponibilidad y las
  lecturas por rangos. Backend/BD saludables y Alembic en `a62f58d4e930`; sin diferencias
  pendientes entre modelo y esquema en la comprobación aislada.
- Comparar tamaño, fecha de modificación y SHA-256 de los dos originales antes/después:
  permanecen intactos. El montaje de origen figura como solo lectura en Compose.
- Comprobar la instalación tras la vinculación: una ficha, dos documentos externos y cero
  archivos en el directorio de subidas. Se retiró únicamente el stack temporal de pruebas.

Se guardó un backup de BD antes de migrar. El backup, las capturas del visor y los resultados
de la comprobación están fuera del repo, en
`C:\Users\eduard.almar\.codex\scratch\inteplast-file-sources`. No contienen nuevas copias de
los originales dentro de la aplicación. El seed continúa sin dependencias de archivos personales.

**No confundir revisiones:** el PDF disponible es rev. 07; los informes de medidas citan rev. 06.
La fecha del nombre del STEP no se presenta como una revisión CAD confirmada. Ver
[definición de la pieza](3212/1-pieza-2d-3d.md).

Pruebas automáticas: **114 backend** en BD temporal (91 % de cobertura, fase de referencias),
**21 componentes** tras los ajustes de los visores, con
API simulada y red externa bloqueada, TypeScript/build, Ruff y mypy. Se prueban rechazo de
rutas, originales modificados, renombrado/revinculación con archivos sintéticos, tokens antiguos,
conflictos y conservación de borradores. No se renombra ningún original para hacer esas pruebas.
Biome pasa tras actualizar su esquema y los patrones de exclusión a la versión instalada;
`git diff --check` pasa. El build mantiene los avisos ya conocidos de tamaño de paquetes y
módulos Node opcionales de OCCT. La suite E2E general de la revisión anterior no se ha repetido;
en esta fase se ha comprobado el recorrido específico de documentos reales descrito arriba.

### Ajustes de interacción posteriores del mismo día

Se comprueba de nuevo el recorrido real en Chromium tras limpiar los textos y sustituir el
iframe por PDF.js: PDF completo, punto bajo el cursor fijo al ampliar, arrastre en ambos ejes,
encuadre y STEP con ocho arrastres verticales/diagonales seguidos, parada al soltar y reapertura.
Las tres nuevas regresiones usan un PDF vectorial sintético de dos páginas y el control 3D real;
comprueban además cambio de página, desmontaje/reapertura y dirección de giro sin bloqueo en polos.
Capturas y resultado en `viewer-interaction-verification.json` dentro de la carpeta de scratch
anterior. En esta fase no hay cambios de API ni BD. `npm audit --omit=dev` devuelve cero avisos;
el aviso moderado anterior del generador de SDK sigue fuera de las dependencias de producción.

PDF.js requiere Node 22.13+ de la rama 22 o Node 24+ para el build. El worker se empaqueta
localmente y Nginx declara el MIME JavaScript de `.mjs`. El contenido se renderiza en el
navegador, sin crear una copia de imagen en el backend. Los metadatos de origen se conservan
para vincular y descargar aunque la interfaz ya no los muestre de forma permanente.

También se comprueba el build servido desde un Nginx temporal: configuración válida, worker
con HTTP 200 y `application/javascript`, mismo recorrido de PDF/STEP y reapertura sin errores
JavaScript. Resultado en `viewer-production-verification.json`. Se retira ese contenedor al
terminar; la instalación habitual sigue usando Vite y su backend local.

### Vistas ligeras del escaneo y del molde (2026-09-15)

Los dos originales grandes están vinculados al Bolt Eye. La aplicación genera automáticamente
su GLB en el servidor y lo reutiliza al volver; la descarga entrega el original. Nueva tabla
`FilePreview`, migración `b73c69e5fa41` y endpoints `POST/GET /files/{id}/preview`.
Configuración, límites y pruebas en [vistas-3d.md](vistas-3d.md).

Quedan para las siguientes fases: Graph, mediciones/N-numbers y marcado de zonas.
El límite de carga directa de 50 MiB sigue vigente para otros formatos 3D grandes.

### Alta de piezas desde carpetas existentes (2026-09-17)

El buscador de «Añadir pieza» lista las subcarpetas directas del origen común y carga todas
las páginas antes de filtrar. Elegir una registra o reutiliza su pieza, sin leer el contenido
de los documentos ni crear carpetas. Nombre y código se rellenan automáticamente y siguen
siendo editables. La carpeta se comparte entre features, pero sus adjuntos se eligen por feature.
La asociación local es temporal; no implementa todavía Microsoft Graph. Se mantiene la pregunta
[A12](preguntas-abiertas.md) sobre si esa raíz común coincide con la organización real en la nube.
