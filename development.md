# Desarrollo de INTEPLAST

## Entorno habitual

Desde la raíz, con Docker Desktop arrancado:

```powershell
npm.cmd ci
docker compose up -d --build db prestart backend mailcatcher
npm.cmd run dev
```

El frontend usa Vite local. El backend y PostgreSQL corren en Docker. Para sincronización y
recarga automática del backend, ejecutar `docker compose watch backend`; `up` por sí solo
no sincroniza el código. El WORKDIR del backend es `/app/backend`.

`compose.override.yml` añade puertos y configuración local. Usar los nombres de servicio:
arrancar todo el Compose también incluye servicios que no hacen falta para trabajar.
Los puertos de desarrollo se publican solo en `127.0.0.1`, para no exponer las credenciales
de ejemplo a otros equipos. Producción usa el proxy HTTPS del Compose principal.

| Servicio | URL local |
|---|---|
| Frontend Vite | http://localhost:5173 |
| API / Swagger | http://localhost:8000/docs |
| Mailcatcher (si se arranca) | http://localhost:1080 |
| Adminer (opcional: `docker compose up -d adminer`) | http://localhost:8080 |
| Traefik (opcional: `docker compose up -d proxy`) | http://localhost:8090 |

Mailcatcher captura el correo local. No se inicia automáticamente al arrancar solo `backend`;
incluirlo como servicio si se van a probar recuperación de contraseña o altas desde Admin.

## Backend local sin contenedor

PostgreSQL sigue siendo necesario. `uv` gestiona un workspace con `.venv` en la **raíz**:

```powershell
docker compose up -d db mailcatcher
uv sync --package app
cd backend
..\.venv\Scripts\Activate.ps1
python -m app.backend_pre_start
alembic upgrade head
python -m app.initial_data
fastapi dev app/main.py
```

Detener antes el servicio backend si ocupa el puerto 8000. Para correo desde el proceso local,
configurar `SMTP_HOST=localhost`, `SMTP_PORT=1025` y `SMTP_TLS=false` en ese entorno.
En Bash el intérprete es `../.venv/bin/python` desde `backend/`.
Los tres pasos previos al servidor esperan a PostgreSQL, aplican las migraciones y crean el
administrador inicial; son necesarios en una BD nueva porque aquí no se ejecuta `prestart` de Docker.

## Configuración y datos

`.env` contiene valores de desarrollo y está versionado. No guardar credenciales reales en él.
Para despliegue, usar variables del entorno o un fichero excluido, por ejemplo `.env.production`;
ver [deployment.md](deployment.md). Las variables del shell prevalecen en la interpolación de Compose.

En Docker, `UPLOADS_DIR=/app/uploads` coincide con el volumen `app-uploads`. En un proceso local,
el valor por defecto `uploads` es relativo al directorio de trabajo, normalmente `backend/uploads`.
Las subidas y la BD sobreviven a `docker compose down`. `down -v` las elimina.

El registro público está desactivado por defecto. El administrador crea usuarios desde `/admin`.
Las rutas privadas de aprovisionamiento solo se habilitan explícitamente en el entorno de tests.

## Tests aislados

```powershell
.\scripts\test.ps1 -q
.\scripts\test.ps1 -E2E
npm.cmd run test:components
```

Equivalente en Bash:

```bash
bash scripts/test.sh -q
bash scripts/test.sh --e2e
```

Cada ejecución usa `compose.test.yml` como fichero **independiente**, con un nombre de proyecto
nuevo. La BD y las subidas son temporales; no se leen las credenciales de `.env`, no se publican
puertos y no se montan los volúmenes de trabajo. Los argumentos se pasan a pytest/Playwright.
El script elimina su propio stack al terminar. La suite de componentes simula la API.

`pytest` rechaza una BD cuyo nombre no termine en `_test`, incluso si se invoca directamente.
No basta con esa convención para aislar una instalación: usar los lanzadores anteriores.
Playwright también rechaza la ejecución fuera del stack explícito de tests.

## Comprobaciones de código

```powershell
npm.cmd run build --workspace frontend
npm.cmd run lint
```

`lint` comprueba sin modificar. Para formatear intencionadamente: `npm.cmd run format --workspace frontend`.
Las herramientas de Python están en las dependencias de desarrollo:

```powershell
cd backend
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
```

No hay `.pre-commit-config.yaml` ni workflows de GitHub Actions configurados en este repositorio.
Los comandos de comprobación se ejecutan explícitamente; instalar `prek` no crea esa configuración.

## Regenerar la API TypeScript

Tras cambiar modelos o endpoints:

```bash
bash scripts/generate-client.sh
```

Requiere `uv`, Node.js y las dependencias instaladas con `npm ci`. Exporta OpenAPI sin abrir la BD,
genera `frontend/src/client` e incluye las rutas exclusivas de tests para su aprovisionamiento.
`frontend/openapi.json` es un intermedio ignorado. Versionar los cambios del cliente generado.
