# INTEPLAST

Base colaborativa de conocimiento para el diseño de piezas inyectadas: features, warnings,
lessons learned y ficheros agrupados por pieza. Piloto actual: **3212 Pump Housing**.
Existe una importación piloto de mediciones y correcciones del 3212; el modelo completo
normalizado y la conexión con Microsoft Graph siguen pendientes.

## Documentación

- [CLAUDE.md](CLAUDE.md): contexto, rutas y reglas del proyecto.
- [Aplicación](docs/app-web.md): modelo, API, permisos y comportamiento.
- [Archivos externos y visores](docs/ficheros-externos.md): vincular originales sin copiarlos,
  configuración local y futura integración con OneDrive.
- [Vistas 3D ligeras](docs/vistas-3d.md): GLB automáticos del escaneo y el molde, con caché.
- [Portadas CAD](docs/portadas-cad.md): superficies en rojo, captura y portada 3D interactiva.
- [Datos del 3212](docs/3212/README.md) y [visores](prototypes/data-explorer/README.md).
- [Desarrollo](development.md), [backend](backend/README.md), [frontend](frontend/README.md).
- [Despliegue](deployment.md) y [correcciones de la revisión](docs/revision-2026-09-15.md).

## Arranque local (PowerShell)

Requisitos: Docker Desktop en ejecución y Node.js 22.13 o posterior de la rama 22 (o Node 24+),
con npm. Desde la raíz:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
npm.cmd ci
docker compose up -d --build db prestart backend mailcatcher
npm.cmd run dev
```

Frontend: http://localhost:5173. API: http://localhost:8000/docs.
`prestart` termina con código 0 después de aplicar migraciones y crear el administrador inicial.
`.env` contiene la configuración privada de esta instalación y no se guarda en Git; la plantilla
es `.env.example`. Docker Compose lo carga automáticamente, también desde una terminal nueva.
Los usuarios los crea el administrador. La carpeta externa se configura siguiendo
la [guía de archivos](docs/ficheros-externos.md); PDF, CAD, escaneo y molde del Bolt Eye están vinculados
en la instalación local de desarrollo. Un seed nuevo sigue creando filas sin archivo.

Si vienes de la configuración anterior con `.env.local`, incorpora sus variables a `.env`
conservando sus valores (en especial `ASSETS_SOURCE_ID`). Ver la [migración](docs/ficheros-externos.md#migración-desde-envlocal).

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

Los visores experimentales viven en `prototypes/data-explorer/`. No forman parte
de la aplicación web ni de Docker; los lectores de la web están en `backend/app/ingestion/`.

```powershell
& 'C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe' .\prototypes\data-explorer\ver_todo.py
```

Los datos del cliente permanecen fuera del repositorio. Revisar los atributos de OneDrive antes
de leer ficheros: un placeholder puede disparar una descarga completa.

## Parar la aplicación

```powershell
docker compose down
```

Este comando conserva la BD y las subidas. No añadir `-v`: eliminaría los volúmenes persistentes.
No hace falta borrar imágenes ni limpiar el builder para un arranque normal.
