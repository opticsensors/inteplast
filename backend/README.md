# Backend de INTEPLAST

FastAPI + SQLModel + PostgreSQL. Leer [docs/app-web.md](../docs/app-web.md) antes de modificar
modelos o endpoints; allí se describen la base de conocimiento y los permisos.

## Arranque

Desde la raíz:

```powershell
docker compose up -d --build db prestart backend mailcatcher
```

API: http://localhost:8000/docs. `prestart` aplica Alembic y crea el administrador inicial.
El código de la imagen vive en `/app/backend/app`; el directorio de trabajo es `/app/backend`.
`docker compose watch backend` sincroniza cambios locales. Sin `watch`, reconstruir con `--build`.

También se puede ejecutar Python localmente: `uv sync --package app` desde la raíz instala el
workspace en `.venv`. Desde `backend/`, activar `../.venv/bin/activate` (Bash) o
`..\.venv\Scripts\Activate.ps1` (PowerShell). Antes de `fastapi dev app/main.py`, con PostgreSQL
arrancado, aplicar las migraciones y crear el administrador siguiendo la receta de
[development.md](../development.md); el proceso local no ejecuta el `prestart` de Docker.

## Pruebas

Desde la raíz:

```powershell
.\scripts\test.ps1 -q
```

O en Bash:

```bash
bash scripts/test.sh -q
bash scripts/test.sh -x
```

El lanzador utiliza un proyecto Docker independiente con `compose.test.yml`, BD `app_test` y
almacenamiento temporal. No modifica el stack de trabajo. `conftest.py` rechaza nombres de BD
que no terminen en `_test` antes de ejecutar los tests y sustituye las subidas por una carpeta
temporal. La limpieza de tablas solo ocurre dentro de la BD de test.

Los argumentos llegan a pytest mediante `backend/scripts/test.sh`; la cobertura se muestra en
consola y su HTML se genera en el directorio indicado por `COVERAGE_HTML_DIR` (en el stack de
tests, `/test-artifacts/htmlcov`). Ese informe es temporal y desaparece al limpiar el stack.
Los tests no están incluidos en la imagen de producción: el stack de pruebas monta `backend/`
en solo lectura. No copiar ni ejecutar los tests dentro del contenedor de trabajo.

## Migraciones

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic heads
```

La revisión actual debe coincidir con `heads`; no depender de un identificador pegado en una guía.
Para crear una revisión, hacerlo desde el **código local**, para que el fichero no quede atrapado
en un contenedor. Desde `backend/` con `uv` y PostgreSQL local disponible:

```powershell
uv run alembic revision --autogenerate -m "descripcion del cambio"
```

Revisar el contenido generado, versionarlo y reconstruir el backend. El prestart ejecuta
`alembic upgrade head`. No borrar migraciones que ya se hayan aplicado.

## Ficheros y acceso

`UPLOADS_DIR=/app/uploads` en Docker; volumen persistente `app-uploads`. No guardar bytes en
`/app/backend/uploads` dentro del contenedor. En local, el valor por defecto es `uploads`.
Antes de actualizar una instalación antigua, comprobar si hay bytes en la ruta antigua y
rescatarlos; ver [deployment.md](../deployment.md).

El registro público está cerrado por defecto (`ALLOW_PUBLIC_SIGNUP=false`). Admin crea usuarios.
Los ficheros requieren autenticación o una URL firmada temporal obtenida con autenticación;
conocer un UUID no permite descargarlos. El token de fichero no sirve como token de sesión.

## Cliente y plantillas

Regenerar el cliente tras cambiar la API: `bash scripts/generate-client.sh` desde la raíz.
Las plantillas de correo están en `app/email-templates/src` (MJML) y `build` (HTML utilizado en
runtime). Al cambiar una plantilla MJML, exportar y versionar también su HTML.

No hay CI ni configuración de depuración de VS Code incluida: ejecutar las comprobaciones
indicadas en [development.md](../development.md).
