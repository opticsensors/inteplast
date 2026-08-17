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

🔴 **Lo que NO está**: la parte de ingesta (`PROYECTO`, `MUESTREO`, `MEDICION`,
`CORRECCION_MOLDE`, `DEPENDENCIA_COTA`). Esas tablas se alimentan de los CSV/XLS/PPTX y son la
siguiente fase. El esquema de ahora no las estorba: `FeatureAsset.part_ref` es el texto libre que
más adelante pasará a ser una FK a `PROYECTO`.

---

## Modelo de datos (`backend/app/models.py`)

```
StoredFile                    metadatos de un fichero subido; los bytes van al disco
  id, filename, content_type, size, created_at

Feature                       la ficha del feature
  id, name, description, category, tags[], owner_id, image_id → StoredFile
  ├─ FeatureNote (n)          kind = warning | lesson
  │    title, body (markdown reducido), position
  └─ FeatureAsset (n)         kind = mold | part | drawing
       name, part_ref, position, file_id → StoredFile
```

Decisiones que conviene conocer antes de tocarlo:

| Decisión | Por qué |
|---|---|
| **Una sola tabla `FeatureNote`** con `kind` en vez de dos tablas | Warnings y lessons learned tienen exactamente los mismos campos y la misma UI. Una tabla, un juego de endpoints, un componente |
| `tags` como **`ARRAY(String)` de Postgres**, no tabla aparte | Se filtra con `tags @> ...` y se busca con `array_to_string`. Sin joins ni tabla de unión para algo que es texto libre |
| Los enums se guardan como **VARCHAR** (`sa_type=AutoString`), no como tipo `ENUM` de Postgres | Añadir una categoría nueva no obliga a una migración. En la API y en el cliente TypeScript siguen siendo uniones cerradas |
| `Feature.owner_id` es **`ON DELETE SET NULL`** | La ficha es conocimiento compartido: sobrevive al borrado del usuario que la creó. (El `Item` de la plantilla, en cambio, es `CASCADE`) |
| Las notas y los adjuntos son **`ON DELETE CASCADE`** | No tienen sentido sin su feature |
| `FeatureAsset.file_id` es **`SET NULL`** | Borrar un fichero no borra la fila que lo describía |

### Ficheros subidos

Los bytes se guardan en disco, en `settings.UPLOADS_DIR` (por defecto `uploads`, **relativo al
working dir**: `/app/uploads` en Docker, `backend/uploads` en local). El fichero se llama como el
`id` de la fila; el nombre original y el mime-type viven en la base de datos.

En Docker hay un volumen `app-uploads` montado en `/app/uploads` (`compose.yml`), así que los
ficheros sobreviven a un `docker compose down`.

🔴 **`GET /files/{id}` no pide autenticación, a propósito.** Un `<img src>` o un enlace de
descarga no pueden mandar la cabecera `Authorization`. El secreto es el UUID v4. Si algún día hay
que servir ficheros confidenciales, hay que pasar a URLs firmadas — está anotado en el propio
endpoint.

---

## API (`backend/app/api/routes/`)

Todo bajo `/api/v1`. Documentación interactiva en `http://localhost:8000/docs`.

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/features/` | Buscar. Params: `q`, `category`, `tag`, `mold`, `skip`, `limit` |
| `GET` | `/features/filters` | Categorías, tags y moldes **que existen en la BD**, para los desplegables |
| `POST` | `/features/` | Crear |
| `GET` | `/features/{id}` | Ficha completa: + `notes` + `assets` |
| `PUT` `DELETE` | `/features/{id}` | Editar / borrar |
| `POST` | `/features/{id}/notes` | Añadir warning o lesson learned |
| `PUT` `DELETE` | `/features/notes/{id}` | Editar / borrar una nota |
| `POST` | `/features/{id}/assets` | Adjuntar una pieza ejemplo |
| `PUT` `DELETE` | `/features/assets/{id}` | Editar / quitar un adjunto |
| `POST` | `/files/` | Subir un fichero (multipart) → devuelve el `id` que se referencia |
| `GET` | `/files/{id}` | Servirlo. **Sin autenticación** (ver arriba) |
| `DELETE` | `/files/{id}` | Borrarlo |

**La búsqueda `q` es global**: mira en el nombre, la descripción, los tags, el nombre y el código
de pieza de los adjuntos, y el título y el cuerpo de warnings y lessons learned. Es lo que permite
encontrar el Bolt Eye escribiendo `3212` o `N170`.

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
| `FeatureCard.tsx` | La tarjeta: imagen, nombre, descripción, tags y badges de los adjuntos |
| `FeatureDetailDialog.tsx` | La modal de solo lectura, con las secciones desplegables |
| `FeatureFormDialog.tsx` | Alta y edición, con las secciones de warnings, lessons y piezas ejemplo |
| `NoteDialog.tsx` `AssetDialog.tsx` | Las modales de segundo nivel |
| `constants.ts` | Las etiquetas en castellano de categorías y tipos |
| `queries.ts` | Las query keys. Todo cuelga de `["features"]`: invalidar esa raíz refresca todo |

Y en `components/Common/`: `FileUpload.tsx` (drag and drop), `RichText.tsx` (editor y visor),
`CollapsibleSection.tsx` (los paneles desplegables).

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

Es idempotente: si el feature ya existe no toca nada. Los adjuntos se crean **sin fichero** — los
CAD del cliente no se copian al repo, se suben desde la aplicación.

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
cd backend;  ruff check app tests;  ruff format app tests;  mypy app
cd frontend; npx tsc -p tsconfig.build.json --noEmit;  npm run lint
docker compose exec backend bash scripts/tests-start.sh   # pytest, necesita la BD
```

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
| **Vincular un feature con sus N-numbers y sus cotas** | Requiere las tablas de ingesta. Es el siguiente paso natural: `INSTANCIA_EN_PROYECTO` de [modelo-datos.md](modelo-datos.md) |
