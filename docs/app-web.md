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

🔴 **Lo que NO está**: la parte de ingesta (`MUESTREO`, `MEDICION`, `CORRECCION_MOLDE`,
`DEPENDENCIA_COTA`). Esas tablas se alimentan de los CSV/XLS/PPTX y son la siguiente fase.

---

## Modelo de datos (`backend/app/models.py`)

```
StoredFile                    metadatos de un fichero subido; los bytes van al disco
  id, filename, content_type, size, created_at

Part                          la pieza = el proyecto = el molde  → embrión de PROYECTO
  id, code ("3212", UNIQUE), name ("Pump Housing")

Feature                       la ficha del feature
  id, name, description, category, tags[], owner_id, image_id → StoredFile
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
| **Tiene un fichero** (`FeatureAsset.part_id`) | El caso normal: subes el molde del 3212 y el 3212 aparece |
| **Está declarada** (`FeaturePartLink`) | *«el Bolt Eye también está en el 3197»* aunque no haya todavía ni un CAD subido |

La vista hace la **unión de los dos** (`frontend/src/components/Features/parts.ts`). Una pieza
declarada sin ficheros sale con la fila entera vacía, que es justo lo que hace visible **lo que
falta por subir**.

Decisiones que conviene conocer antes de tocarlo:

| Decisión | Por qué |
|---|---|
| **Una sola tabla `FeatureNote`** con `kind` en vez de dos tablas | Warnings y lessons learned tienen exactamente los mismos campos y la misma UI. Una tabla, un juego de endpoints, un componente |
| `tags` como **`ARRAY(String)` de Postgres**, no tabla aparte | Se filtra con `tags @> ...` y se busca con `array_to_string`. Sin joins ni tabla de unión para algo que es texto libre |
| Los enums se guardan como **VARCHAR** (`sa_type=AutoString`), no como tipo `ENUM` de Postgres | Añadir una categoría nueva no obliga a una migración. En la API y en el cliente TypeScript siguen siendo uniones cerradas |
| `Feature.owner_id` es **`ON DELETE SET NULL`** | La ficha es conocimiento compartido: sobrevive al borrado del usuario que la creó. (El `Item` de la plantilla, en cambio, es `CASCADE`) |
| Las notas y los adjuntos son **`ON DELETE CASCADE`** | No tienen sentido sin su feature |
| `FeatureAsset.file_id` y `part_id` son **`SET NULL`** | Borrar un fichero no borra la fila que lo describía; borrar una pieza no borra sus adjuntos, que caen a un grupo *«sin pieza»* al final de la matriz |
| `Part.code` es **UNIQUE** y el alta va por desplegable, no por texto libre | Es la clave con la que se agrupa todo. Escrito a mano acababa en dos piezas por cada pieza real |
| `FeaturePartLink` es una tabla de unión **sin campos propios** | Hoy solo dice *«este feature está en esta pieza»*. Cuando llegue la ingesta, aquí cuelgan los N-numbers y las tolerancias y pasa a ser `INSTANCIA_EN_PROYECTO` |
| Borrar una pieza es **solo de superusuario** | Es compartida por todos los features; no tiene autor al que atribuirla |

### Ficheros subidos

Los bytes se guardan en disco, en `settings.UPLOADS_DIR` (por defecto `uploads`, **relativo al
working dir**: `/app/uploads` en Docker, `backend/uploads` en local). El fichero se llama como el
`id` de la fila; el nombre original y el mime-type viven en la base de datos.

En Docker hay un volumen `app-uploads` montado en `/app/uploads` (`compose.yml`), así que los
ficheros sobreviven a un `docker compose down`.

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

🔴 **`GET /files/{id}` no pide autenticación, a propósito.** Un `<img src>` o un enlace de
descarga no pueden mandar la cabecera `Authorization`. El secreto es el UUID v4. Si algún día hay
que servir ficheros confidenciales, hay que pasar a URLs firmadas — está anotado en el propio
endpoint.

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
| `GET` | `/files/{id}` | Servirlo. **Sin autenticación** (ver arriba) |
| `DELETE` | `/files/{id}` | Borrarlo |

**La búsqueda `q` es global**: mira en el nombre, la descripción, los tags, el **código y el
nombre de las piezas** (por adjunto y por declaración), el nombre de los adjuntos, y el título y
el cuerpo de warnings y lessons learned. Es lo que permite encontrar el Bolt Eye escribiendo
`3212`, `Pump Housing` o `N170`.

### Permisos

La plantilla solo tiene dos roles (usuario y superusuario) y no se han añadido más:

- **Leer**: cualquier usuario autenticado ve **todas** las fichas. Es el sentido de la
  herramienta — a diferencia del `Item` de la plantilla, que solo enseña los propios.
- **Crear y editar**: cualquier usuario autenticado. La base es colaborativa.
- **Borrar un feature**: solo el autor o un superusuario. Es lo único irreversible.
- **Gestión de usuarios**: superusuario, como en la plantilla.

---

## Frontend (`frontend/src/`)

| Ruta | Fichero | Qué es |
|---|---|---|
| `/` | `routes/_layout/index.tsx` | **Dashboard**: buscador global + filtros, tarjetas de resultado, modal de detalle, accesos rápidos y recientes |
| `/features` | `routes/_layout/features.tsx` | **Gestión** (la página «Ítems» de la fase B): mismas tarjetas con editar y borrar |
| `/admin` | `routes/_layout/admin.tsx` | Usuarios y permisos. **Sin tocar**, es el de la plantilla |

Componentes en `components/Features/`:

| Fichero | Qué |
|---|---|
| `FeatureSearch.tsx` | Buscador + tres desplegables (molde, categoría, tag) poblados desde `/features/filters` |
| `FeatureCard.tsx` | La tarjeta: imagen, nombre, descripción, tags y el resumen *«2 piezas · 3197, 3212»* |
| `PartAssetMatrix.tsx` | 🔑 **La matriz pieza × tipo de fichero** de la ficha: una fila por pieza, una columna por tipo |
| `parts.ts` | La unión *piezas declaradas + piezas con ficheros* y el reparto en filas. Es la lógica de la matriz |
| `PartSelect.tsx` | Desplegable de piezas con alta al vuelo (código + nombre) |
| `FeatureDetailDialog.tsx` | La modal de solo lectura, con las secciones desplegables |
| `FeatureFormDialog.tsx` | Alta y edición: warnings, lessons, **Piezas** y **Ficheros por pieza** |
| `NoteDialog.tsx` `AssetDialog.tsx` | Las modales de segundo nivel |
| `constants.ts` | Las etiquetas en castellano de categorías y tipos, y el icono de cada tipo |
| `queries.ts` | Las query keys. Todo cuelga de `["features"]`: invalidar esa raíz refresca todo |

Y en `components/Common/`: `FileUpload.tsx` (drag and drop), `RichText.tsx` (editor y visor),
`CollapsibleSection.tsx` (los paneles desplegables).

### Las tres casillas de la matriz

En `PartAssetMatrix.tsx`, cada casilla tiene tres estados y **los tres se leen distinto a
propósito**:

| Se ve | Significa |
|---|---|
| ⬇ botón de descarga | Hay fichero subido. El nombre real (`Molde 3212 (STEP, 247 MB)`) está en el `title` |
| icono del tipo al 40 % | El adjunto está declarado pero **nadie ha subido el fichero**. Es el caso del seed |
| `–` en gris | Esa pieza no tiene nada de ese tipo |

El segundo estado es el que convierte la matriz en un **checklist de lo que falta**.

### Dos cosas del frontend que hay que saber

1. **Al crear un feature, la modal no se cierra.** Los warnings, lessons y adjuntos necesitan que
   el feature exista para colgarse de él, así que al guardar por primera vez la modal pasa a modo
   edición y aparecen esas secciones. Los datos básicos se guardan con el botón; las notas y los
   adjuntos se guardan solos desde sus propias modales.

2. **El editor de texto enriquecido es markdown reducido**, no TipTap: `**negrita**`,
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

🔴 **El `--build` no es opcional después de tocar `backend/`.** El Dockerfile copia el código
dentro de la imagen; si ya existe un `backend:latest`, `docker compose up -d` a secas **lo
reutiliza tal cual** y arrancas con el código viejo — sin errores, simplemente faltan los
endpoints. Cómo se detecta:

```powershell
docker compose exec backend alembic current   # tiene que decir b7f1c0d2a3e4 (head)
```

El frontend no tiene este problema: Vite sirve desde el disco.

### Datos de ejemplo

Hay una carga opcional con el **Bolt Eye del 3212**: sus 8 warnings y 2 lessons learned, sacados
de [modelo-datos.md](modelo-datos.md) y [3212/historial-molde.md](3212/historial-molde.md).

```powershell
docker compose exec backend python -m app.seed_features
```

Es idempotente: si el feature ya existe no toca nada. Crea la pieza **3212 Pump Housing**, la
declara en el feature y le cuelga los cinco adjuntos, uno por tipo. Los adjuntos se crean **sin
fichero** — los CAD del cliente no se copian al repo, se suben desde la aplicación.

🔴 **Nunca lances los tests contra `app`.** Ver [Comprobaciones](#comprobaciones): el
`conftest.py` de la plantilla **vacía la base de datos al terminar** y hay que usar `app_test`.

### Regenerar el cliente TypeScript

Cualquier cambio en los endpoints o en los modelos del backend obliga a regenerar el cliente, o el
frontend se queda desincronizado:

```bash
bash scripts/generate-client.sh     # necesita uv
```

Sin `uv` a mano, los tres pasos son: volcar `app.main.app.openapi()` a `frontend/openapi.json`,
`npm run generate-client` dentro de `frontend/`, y `npm run lint`.

### Comprobaciones

```powershell
cd frontend; npx tsc -p tsconfig.build.json --noEmit;  npm run lint
docker compose exec backend bash -c "ruff check app; ruff format --check app; mypy app"
```

#### 🔴 Los tests, SIEMPRE contra `app_test`

El `conftest.py` de la plantilla **vacía la base de datos al terminar**: borra `Item`, `Feature`,
`Part`, `StoredFile` y `User`. Lanzado contra `app` te borra los datos **y te tira la sesión del
navegador**, porque el superusuario se recrea con un `id` distinto al que lleva tu token.

Además los tests **no van dentro de la imagen** (`backend/Dockerfile` solo copia `app/`), así que
hay que meterlos antes. La receta completa:

```powershell
# 1. La base de datos de test, una sola vez
docker compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE app_test"
docker compose exec -T -e POSTGRES_DB=app_test backend alembic upgrade head

# 2. Cada vez: copiar los tests y lanzarlos contra app_test
docker compose exec -T backend rm -rf /app/backend/tests
docker cp backend/tests inteplast-backend-1:/app/backend/tests
docker compose exec -T -e POSTGRES_DB=app_test backend python -m pytest tests -q
```

`POSTGRES_DB` es lo único que hace falta: `settings.SQLALCHEMY_DATABASE_URI` se construye a partir
de esa variable, así que el `-e` desvía toda la sesión de test. Tras una migración nueva, repetir
el `alembic upgrade head` sobre `app_test`.

Los tests del backend están en `backend/tests/api/routes/test_features.py`, con las utilidades en
`backend/tests/utils/feature.py`.

---

## Cabos sueltos

| Qué | Estado |
|---|---|
| **La página `/items` de la plantilla sigue existiendo** | Se ha quitado del menú pero el `Item` de demo sigue en el backend, el frontend y los tests. No molesta; se puede borrar entero cuando se decida |
| **Sin paginación en la UI** | La API ya la tiene (`skip`/`limit`); el frontend pide 100 de golpe. Con cientos de fichas hay que añadir los controles |
| **Ordenar warnings y adjuntos arrastrando** | El campo `position` ya está en la BD y se respeta al leer, pero la UI todavía no deja reordenar |
| **Imagen con la zona marcada en rojo** | Se sube ya hecha desde el CAD. La herramienta de anotación dentro de la app que menciona la fase B no está |
| **Vincular un feature con sus N-numbers y sus cotas** | La tabla ya existe (`FeaturePartLink`), pero está vacía de contenido: solo dice *feature ↔ pieza*. Añadirle los N-numbers y las tolerancias la convierte en el `INSTANCIA_EN_PROYECTO` de [modelo-datos.md](modelo-datos.md) |
| **Más de un fichero del mismo tipo en la misma pieza** | La casilla los apila en vertical. Con tres o cuatro se queda alta; si pasa de verdad, toca un desplegable |
| **La ficha de una pieza** | Hoy `Part` solo tiene código y nombre, y se edita desde el desplegable. No hay página propia donde ver *«todos los features del 3212»* |
