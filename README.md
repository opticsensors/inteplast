# INTEPLAST

Base colaborativa de conocimiento para el diseño de piezas inyectadas: features, warnings,
lessons learned y ficheros agrupados por pieza. Piloto actual: **3212 Pump Housing**.
La ingesta de mediciones y correcciones de molde todavía no está implementada.

## Documentación

- [CLAUDE.md](CLAUDE.md): contexto, rutas y reglas del proyecto.
- [Aplicación](docs/app-web.md): modelo, API, permisos y comportamiento.
- [Datos del 3212](docs/3212/README.md) y [visores](data-explorer/README.md).
- [Desarrollo](development.md), [backend](backend/README.md), [frontend](frontend/README.md).
- [Despliegue](deployment.md) y [correcciones de la revisión](docs/revision-2026-09-15.md).

## Arranque local (PowerShell)

Requisitos: Docker Desktop en ejecución y Node.js 22 con npm. Desde la raíz:

```powershell
npm.cmd ci
docker compose up -d --build db prestart backend mailcatcher
npm.cmd run dev
```

Frontend: http://localhost:5173. API: http://localhost:8000/docs.
`prestart` termina con código 0 después de aplicar migraciones y crear el administrador inicial.
Las credenciales locales de ejemplo están en `.env`; los usuarios los crea el administrador.

Para sincronizar automáticamente cambios del backend, usar en otra terminal:

```powershell
docker compose watch backend
```

Sin `watch`, los cambios del backend requieren `--build`. Para cargar el ejemplo opcional:

```powershell
docker compose exec backend python -m app.seed_features
```

## Comprobaciones

```powershell
npm.cmd run build --workspace frontend
npm.cmd run test:components
.\scripts\test.ps1
.\scripts\test.ps1 -E2E
```

En Git Bash/Linux: `bash scripts/test.sh` y `bash scripts/test.sh --e2e`.
Los scripts crean un proyecto Docker temporal, con BD `app_test`, sin puertos publicados ni
volúmenes compartidos con la aplicación. No ejecutar suites contra la BD de trabajo.

## Visores de datos

```powershell
& 'C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe' .\data-explorer\ver_todo.py
```

Los datos del cliente permanecen fuera del repositorio. Revisar los atributos de OneDrive antes
de leer ficheros: un placeholder puede disparar una descarga completa.

## Parar la aplicación

```powershell
docker compose down
```

Este comando conserva la BD y las subidas. No añadir `-v`: eliminaría los volúmenes persistentes.
No hace falta borrar imágenes ni limpiar el builder para un arranque normal.

