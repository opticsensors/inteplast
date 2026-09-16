# Despliegue de INTEPLAST

El despliegue utiliza `compose.yml` y el proxy HTTPS de `compose.traefik.yml`.
Este repositorio **no incluye workflows de GitHub Actions ni entornos de CI/CD configurados**.
Los pasos siguientes se ejecutan en el servidor preparado por el responsable del despliegue.

## Preparación

- Docker Engine y Docker Compose instalados.
- DNS para `api`, `dashboard` y, si se utilizan, `traefik` y `adminer` bajo el dominio elegido.
- Acceso al servidor y almacenamiento para la BD y las subidas; política de copias de ambos.
- Ficheros del cliente fuera del repositorio. Se admiten subidas de hasta 50 MB y referencias
  a originales accesibles al backend. La integración Microsoft Graph sigue pendiente.

## Configuración

Crear `.env.production` fuera del control de versiones, partiendo de `.env.example`.
Usar contraseñas distintas de los valores locales de ejemplo y una clave de firma aleatoria.
La aplicación rechaza `changethis` cuando `ENVIRONMENT` es `production` o `staging`.

Configurar al menos:

| Variable | Valor / finalidad |
|---|---|
| `ENVIRONMENT` | `production` |
| `PROJECT_NAME` | Nombre de la aplicación |
| `DOMAIN` | Dominio del servidor |
| `FRONTEND_HOST` | `https://dashboard.<dominio>`; se usa en enlaces de correo |
| `BACKEND_CORS_ORIGINS` | Origen HTTPS del frontend |
| `STACK_NAME` | Nombre único del despliegue |
| `SECRET_KEY` | Clave aleatoria de firma |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Credenciales y BD de la aplicación |
| `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD` | Administrador inicial |
| `DOCKER_IMAGE_BACKEND`, `DOCKER_IMAGE_FRONTEND` | Nombres de imágenes |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM_EMAIL` | Proveedor de correo |
| `SMTP_PORT`, `SMTP_TLS`, `SMTP_SSL` | Puerto y cifrado del proveedor; por defecto 587/true/false |
| `ALLOW_PUBLIC_SIGNUP` | Mantener `false` para altas administradas |
| `ENABLE_TEST_ROUTES` | Mantener `false`; nunca habilitar en este entorno |

`--env-file .env.production` proporciona los valores de interpolación. Los servicios reciben
las variables declaradas en `environment` de `compose.yml`; no necesitan ni leen un `.env`
de desarrollo. El fichero de producción no debe activar `compose.override.yml`.

## Proxy HTTPS

Crear una vez la red compartida:

```bash
docker network create traefik-public
```

Preparar las variables `DOMAIN`, `EMAIL`, `USERNAME` y `HASHED_PASSWORD` del proxy en su entorno
privado. `HASHED_PASSWORD` es la contraseña de Basic Auth en formato compatible con htpasswd;
no guardar su valor en Git. Arrancar:

```bash
docker compose -f compose.traefik.yml up -d
```

El proxy configura certificados Let's Encrypt y protege su dashboard con Basic Auth.

## Aplicación

Desde la raíz del código desplegado:

```bash
docker compose --env-file .env.production -f compose.yml build
docker compose --env-file .env.production -f compose.yml up -d
docker compose --env-file .env.production -f compose.yml exec backend alembic current
docker compose --env-file .env.production -f compose.yml exec backend alembic heads
```

Especificar `-f compose.yml` excluye el override local. Los Dockerfiles del frontend usan
`npm ci` y el `package-lock.json` versionado. El administrador crea usuarios desde `/admin`.
Los ficheros se sirven con autenticación o enlaces firmados temporales; el UUID solo no da acceso.

Para un origen local accesible desde el servidor, añadir `-f compose.assets.yml` a **cada**
comando de la aplicación y configurar `ASSETS_HOST_PATH`, `ASSETS_SOURCE_ID` y
`ASSETS_SOURCE_NAME` en `.env.production`. El montaje es de solo lectura. Usar los comandos
explícitos de arriba para seleccionar el fichero de producción y excluir el override de desarrollo.
Ver [archivos externos](docs/ficheros-externos.md). El acceso a los originales de INTEPLAST debe
acordarse antes del despliegue; una ruta del ordenador de desarrollo no es una conexión Graph.

## Persistencia y actualización desde la versión anterior

La BD usa `app-db-data`; los ficheros usan `app-uploads`, montado en `/app/uploads`.
El Dockerfile fija esa ruta absoluta para `UPLOADS_DIR`.
Las referencias externas se conservan en la BD, pero sus bytes permanecen en el almacenamiento
de origen y necesitan su propia política de copias. Conservar también la configuración del
origen. La migración `a62f58d4e930` mantiene los UUID de subidas anteriores y añade sus metadatos
de origen; hacer backup antes de migrar. Su downgrade se bloquea si existen referencias externas.

La migración `b73c69e5fa41` añade la cola `FilePreview`. Los GLB derivados se guardan en
`app-uploads/previews` y se pueden regenerar: no sustituyen la copia de los originales.
El backend incorpora OCP/VTK y bibliotecas gráficas nativas, aunque no utiliza una pantalla.
Reserva recursos para una conversión a la vez (límite predeterminado de 8 GiB de memoria
virtual y 15 minutos) y comparte el volumen si se ejecutan varias instancias. Configuración
y límites en [vistas 3D ligeras](docs/vistas-3d.md).

**Antes de recrear un backend antiguo**, comprobar si existen ficheros en
`/app/backend/uploads`. La versión anterior escribía ahí por error, fuera del volumen.
Si contiene datos, copiar primero esa carpeta a una ubicación de rescate **fuera del repo**,
conservar los nombres UUID y colocar esos bytes en `/app/uploads` del volumen persistente.
Verificar descargas y copias antes de retirar el contenedor antiguo. Si ya se eliminó el
contenedor y no hay copia, la BD conserva metadatos pero no puede reconstruir los bytes.

`docker compose down` conserva los volúmenes. **`down -v` los elimina** y no forma parte de
la actualización ni de las pruebas. Para tests, utilizar exclusivamente los lanzadores de
[development.md](development.md), que crean otro proyecto con datos temporales.
