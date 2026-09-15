# Despliegue de INTEPLAST

El despliegue utiliza `compose.yml` y el proxy HTTPS de `compose.traefik.yml`.
Este repositorio **no incluye workflows de GitHub Actions ni entornos de CI/CD configurados**.
Los pasos siguientes se ejecutan en el servidor preparado por el responsable del despliegue.

## Preparación

- Docker Engine y Docker Compose instalados.
- DNS para `api`, `dashboard` y, si se utilizan, `traefik` y `adminer` bajo el dominio elegido.
- Acceso al servidor y almacenamiento para la BD y las subidas; política de copias de ambos.
- Ficheros del cliente fuera del repositorio. La referencia a un archivo externo grande sigue
  pendiente de implementación; hoy la aplicación admite subidas de hasta 50 MB.

## Configuración

Crear `.env.production` fuera del control de versiones, partiendo de los **nombres** de `.env`.
Usar contraseñas distintas de los valores locales de ejemplo y una clave de firma aleatoria.
La aplicación rechaza `changethis` cuando `ENVIRONMENT` es `production` o `staging`.

Configurar al menos:

| Variable | Valor / finalidad |
|---|---|
| `ENVIRONMENT` | `production` |
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

Compose lee `.env` en los servicios y sobreescribe las variables declaradas en `environment`.
Por ello las opciones de despliegue, incluidas las de registro y tests, están declaradas en
`compose.yml`; `--env-file .env.production` proporciona sus valores de interpolación.

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

## Persistencia y actualización desde la versión anterior

La BD usa `app-db-data`; los ficheros usan `app-uploads`, montado en `/app/uploads`.
El Dockerfile fija esa ruta absoluta para `UPLOADS_DIR`.

**Antes de recrear un backend antiguo**, comprobar si existen ficheros en
`/app/backend/uploads`. La versión anterior escribía ahí por error, fuera del volumen.
Si contiene datos, copiar primero esa carpeta a una ubicación de rescate **fuera del repo**,
conservar los nombres UUID y colocar esos bytes en `/app/uploads` del volumen persistente.
Verificar descargas y copias antes de retirar el contenedor antiguo. Si ya se eliminó el
contenedor y no hay copia, la BD conserva metadatos pero no puede reconstruir los bytes.

`docker compose down` conserva los volúmenes. **`down -v` los elimina** y no forma parte de
la actualización ni de las pruebas. Para tests, utilizar exclusivamente los lanzadores de
[development.md](development.md), que crean otro proyecto con datos temporales.
