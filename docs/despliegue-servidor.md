# Despliegue en servidor interno

**Decisión recogida el 05/11/2026:** preparar INTEPLAST sobre **Linux con Docker**,
con **HTTPS interno**, acceso desde la red corporativa o VPN e inicio de sesión
automático con Microsoft. Los usuarios abrirán un enlace; SSH quedará para administrar
y actualizar el servidor.

**Fases fijadas por Eduard el 09/11/2026:**

1. Pruebas locales con cuentas de Eurecat. Login automático y lectura del OneDrive de Eduard comprobados.
2. Piloto actual en el servidor de Eurecat, con cuentas de Eurecat y el OneDrive de Eduard.
3. Traslado a los servidores de INTEPLAST. Esta fase depende de [A10](preguntas-abiertas.md#a10-acceso-originales).

**Asistente — decisión de Eduard (17/11/2026): Ollama descartado.** Antes del traslado,
hacer en el PC de Eduard una prueba de concepto con Codex (ChatGPT), con el modelo más rápido
disponible como motor de fondo, simulando un agente conectado a la API de la app sin crear
un agente para esta prueba. **La solución final será Copilot de empresa.** La prueba con Codex es
local y provisional; no se traslada como solución de producción. Prueba integrada el
18/11/2026 con puente de Windows y búsqueda por palabras sin Ollama; detalle en
[asistente](asistente.md#prueba-local-integrada-18112026).

## Estado del servidor de Eurecat y punto de reanudación (23/11/2026)

**Despliegue completado el 23/11/2026.** La web y la API responden por HTTPS. Eduard ha
entrado con Microsoft como administrador y se han trasladado las 21 piezas, los 8 features
y los archivos subidos. Eduard ha confirmado la lectura de PDF y CAD desde su carpeta
`Exemples` de OneDrive. Queda probar con un segundo usuario desde otro equipo.
[Casos de trabajo](proximos-pasos.md#casos-de-trabajo-del-23-de-noviembre).

**Actualización de Planos del 23/11.** Se desplegó el código `8dbadfb`. Desde el PC se verificaron
por HTTPS la salud de la API, el parámetro de página y el campo de giro de las miniaturas,
el módulo del visor que aplica ese giro y el enlace a la pieza en la página antigua del adjunto.

Las comprobaciones siguientes corresponden a la preparación previa a la instalación.

| Comprobación | Resultado del 23/11 |
|---|---|
| Acceso desde el PC de Eduard | El DNS resolvió a `172.20.48.115` y Eduard entró con su cuenta corporativa desde PowerShell mediante `ssh -l "$env:USERNAME" euredinteplast.local.eurecat.org`. SSH guardó la clave del servidor en `known_hosts` al aceptarla en la primera conexión. Su huella ED25519 quedó pendiente de contraste por otro canal. |
| Máquina | Ubuntu 24.04.5 LTS, 2 CPU disponibles, 15 GiB de RAM y 4 GiB de swap. En `/`, 33 GiB libres de 43 GiB. Git 2.43.0. |
| Docker | Docker 29.10.0 y Compose v5.8.0. La cuenta de Eduard accede al motor con `sudo docker ps`, que devolvió una tabla vacía. Sin `sudo`, el socket `root:docker` denegó el acceso. |
| HTTPS | La conexión al 443 desde el PC falló. En el servidor, `ss -ltn 'sport = :443'` confirmó que ningún servicio escuchaba en ese puerto. |

**Plan utilizado para la primera instalación**

1. Abrir Docker Desktop y ejecutar `docker ps` en PowerShell. La última vez, WSL falló al crear la máquina virtual de Docker con `CreateVm/HCS/0x80070569`. Si se repite tras reiniciar, pasar el error a IT para que revise el derecho «Iniciar sesión como servicio» de las máquinas virtuales en ese PC.
2. Con el motor disponible, medir los datos locales desde la raíz del repo. Si los contenedores existentes están parados, arrancarlos con `docker compose start db backend`. Anotar las dos cifras y comprobar que en el servidor cabe la restauración con margen para imágenes, copias y caché de CAD.

   ```powershell
   docker compose exec -T db sh -c 'du -sh $PGDATA'
   docker compose exec -T backend du -sh /app/uploads
   ```

3. Preparar el certificado y la configuración privada del [despliegue desde PowerShell](#desplegar-desde-el-pc), registrar el retorno HTTPS en Entra y validar el acceso al origen elegido.
4. Hacer la primera copia, [restaurar los datos en Eurecat](#rutas-traslado-de-datos-y-persistencia) y [probar el acceso con usuarios](#estado-y-comprobaciones-antes-de-abrir-el-acceso-al-equipo).

**Actualizaciones posteriores.** Desarrollar y probar los cambios en el PC, subir la versión
validada a GitHub y desplegar esa versión por SSH con Compose. Aplicar las migraciones sobre
la base de datos del servidor y conservar sus volúmenes para mantener las fichas que edite el equipo.

## Desplegar desde el PC

Desde la raíz del repo en PowerShell, el mismo comando instala o actualiza el software publicado en la rama `main` de GitHub. Por defecto conecta a `euredinteplast.local.eurecat.org` con el nombre de usuario de Windows y usa `~/inteplast` en el servidor. Para otra instalación, `-Server` debe coincidir con el `DOMAIN` del certificado y `-User` permite elegir la cuenta SSH. SSH y, si hace falta, `sudo docker` piden la contraseña en la terminal.

```powershell
.\scripts\deploy.ps1
```

**Primera instalación**

1. Publicar en `main` la versión que se quiere desplegar, incluido `compose.server.yml`. Para preparar únicamente la copia de Git mientras llega el certificado, ejecutar `.\scripts\deploy.ps1 -PrepareOnly`.
2. Preparar una carpeta privada fuera del repo en el PC, por ejemplo `$env:USERPROFILE\inteplast-produccion`. Copiar allí [la plantilla](../.env.production.example) como `.env.production`, completar las credenciales de PostgreSQL y Microsoft, el correo del primer administrador y el origen. Al trasladar el catálogo, conservar su `ASSETS_SOURCE_ID`. Planificar la rotación de `SECRET_KEY` y el nuevo inicio de sesión si la instalación anterior tenía una clave de ejemplo. Para un origen común, configurar la unidad y la raíz iniciales o seleccionar la carpeta desde **Admin → SharePoint**. La selección en Admin tiene prioridad.
3. Añadir a esa carpeta `fullchain.pem` (certificado del nombre HTTPS y certificados intermedios) y `privkey.pem` (clave PEM correspondiente, utilizable por el proxy sin contraseña). El PC debe confiar en la autoridad emisora. El registro **Web** de Entra debe admitir `https://euredinteplast.local.eurecat.org/api/v1/login/microsoft/callback`.
4. Lanzar la instalación desde el PC. Los tres ficheros viajan por SSH y se guardan en `~/.config/inteplast/` con acceso privado.

```powershell
.\scripts\deploy.ps1 -ConfigDirectory "$env:USERPROFILE\inteplast-produccion"
```

En las siguientes ejecuciones se reutiliza la configuración instalada. Para cambiarla, el administrador actualiza esos ficheros en el servidor por su canal de administración. El lanzador conserva una configuración existente incluso si se repite el comando inicial. Al renovar el certificado, recrear el proxy desde `~/inteplast` con `sudo docker compose -p inteplast --env-file ~/.config/inteplast/.env.production -f compose.yml -f compose.server.yml up -d --no-deps --force-recreate proxy` para que cargue el nuevo par.

**Actualizaciones.** El lanzador comprueba origen, rama y cambios locales, avanza únicamente por *fast-forward* y serializa los despliegues. Compose construye las imágenes antes de sustituir servicios. Si PostgreSQL ya tiene una revisión de Alembic y cambia la revisión objetivo, guarda un `pg_dump -Fc` en `~/.local/share/inteplast/backups/` antes de migrar. El proyecto Compose se llama `inteplast` para conservar los volúmenes entre versiones. El comando termina comprobando la web y la respuesta de salud de la API por HTTPS desde el PC.

Si una ejecución falla, corregir la causa que indica la terminal y repetir el comando. Para diagnosticar una migración o un servicio, desde `~/inteplast` se pueden consultar los registros con `sudo docker compose -p inteplast --env-file ~/.config/inteplast/.env.production -f compose.yml -f compose.server.yml logs --tail=80 prestart backend proxy`. Un fallo después de migrar puede requerir restaurar una copia compatible. La copia inicial de los datos del PC, la restauración, el respaldo de `app-uploads` y la conservación de copias fuera del servidor se gestionan con el [procedimiento de traslado](#rutas-traslado-de-datos-y-persistencia).

Se usa el [patrón de producción de Docker Compose](https://docs.docker.com/compose/how-tos/production/) y la espera de servicios de [`docker compose up --wait`](https://docs.docker.com/reference/cli/docker/compose/up/).

## Plataforma y acceso elegidos

- **Linux con Docker Engine y Docker Compose.** Los contenedores actuales ya son Linux.
  La web compilada y servida por Nginx, la API y PostgreSQL con pgvector pueden convivir
  en la misma máquina, con volúmenes persistentes.
- Si IT dispone de **Windows Server**, pedir una **máquina virtual Linux** sobre esa
  infraestructura. Docker Desktop no está soportado en Windows Server, según la
  [documentación de Docker](https://docs.docker.com/desktop/setup/install/windows-install/).
- **HTTPS con nombres internos y certificados reconocidos por los equipos corporativos.**
  IT puede proporcionar el DNS y los certificados; no hace falta comprar un dominio nuevo
  ni publicar la aplicación en Internet. El acceso puede limitarse a la red corporativa o VPN.
- **SSH para mantenimiento.** Una sesión SSH normal no cifra el tráfico HTTP del navegador.
  Los usuarios de la web no necesitan cuenta SSH ni configurar un túnel.

El navegador necesita alcanzar la web, la API y el inicio de sesión de Microsoft.
El backend necesita conexiones salientes HTTPS a Microsoft Entra, Microsoft Graph y los
destinos de descarga de SharePoint/OneDrive. El retorno del login llega a través del
navegador del usuario, por lo que la API puede seguir siendo interna.

## Nombre propuesto por IT de Eurecat (17/11/2026)

IT y Eduard acordaron **un solo nombre DNS** para la fase 2, con la API en el mismo dominio:

- Web: `https://euredinteplast.local.eurecat.org`
- API: el mismo nombre, bajo `/api`. **En minúsculas**: IT lo escribió `/API`, pero las rutas
  distinguen mayúsculas y la API ya vive en `/api/v1` (`API_V1_STR`).
- Puertos: solo 443 y SSH. Salida HTTPS hacia Microsoft, Docker Hub y GitHub (mensaje a IT
  del 16/11/2026).

Un solo nombre sirve y simplifica: web y API comparten origen, sin CORS entre dominios.
Configuración de la instalación interna con `compose.server.yml`:

| Qué | Cambio |
|---|---|
| Reglas de Traefik | El proxy sirve la API bajo `/api/` y la web bajo `/` en el mismo nombre. Solo publica el puerto 443. |
| `VITE_API_URL` | `https://euredinteplast.local.eurecat.org`, sin `/api`: el cliente ya añade `/api/v1`. Se fija al construir el frontend |
| `FRONTEND_HOST`, `BACKEND_CORS_ORIGINS` | `https://euredinteplast.local.eurecat.org` |
| `MICROSOFT_REDIRECT_URI` y Entra | `https://euredinteplast.local.eurecat.org/api/v1/login/microsoft/callback`, registrado como Web |
| Certificado | Traefik carga la cadena y clave privadas aportadas por la instalación. Falta acordar su entrega y renovación en Eurecat. |

## Por qué HTTPS y qué alternativas existen

Servir una web en `http://IP:puerto` es posible, como en el proyecto IoT con Grafana y
Node-RED. En INTEPLAST, el requisito adicional lo introduce el retorno automático del
login de Microsoft: debe estar registrado en Entra y utilizar HTTPS, salvo la excepción
de localhost para desarrollo. Véanse los
[requisitos de las URI de retorno de Microsoft](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url).

| Acceso | Aplicación a INTEPLAST |
|---|---|
| HTTP por IP y puerto, con el login manual de Postman | Técnicamente permite el flujo de copiar y pegar el enlace, con el retorno HTTPS de Postman (el que se usó hasta el 09/11/2026). Opción temporal de prueba; no es el acceso elegido para el equipo. |
| HTTP por IP y puerto, con retorno automático a esa IP | Microsoft no admite esa URI HTTP de retorno para el flujo actual. |
| HTTPS interno, desde red corporativa o VPN | **Opción elegida.** Enlace compartido y retorno automático, sin publicar el servicio en Internet. |
| Túnel SSH y acceso por localhost | Alternativa de desarrollo, registrando el retorno de localhost y encaminando web y API. Cada usuario tendría que mantener su túnel. |

IP y HTTPS también pueden combinarse, con un certificado válido para esa IP y una URI
registrada. Se prefieren nombres internos para facilitar el acceso y la gestión de certificados.

## Petición a IT

Petición inicial, anterior al acuerdo de usar un solo nombre para web y API:

> Queremos desplegar INTEPLAST en un servidor interno, accesible desde la red corporativa
> o VPN, con inicio de sesión mediante Microsoft y lectura de documentos de SharePoint.
>
> Necesitamos:
>
> - Una máquina Linux con Docker Engine y Docker Compose, o una VM Linux sobre vuestra infraestructura.
> - Nombres DNS internos para web y API, con certificados HTTPS reconocidos por los equipos y un responsable de su renovación. Ambos servicios pueden estar en la misma máquina.
> - Acceso SSH para desplegar y mantener la aplicación, y acceso web para los usuarios desde las redes previstas.
> - Conectividad saliente hacia Microsoft Entra, Microsoft Graph y los servicios de descarga de SharePoint/OneDrive.
> - Registrar como plataforma **Web** el retorno `https://<nombre-interno-api>/api/v1/login/microsoft/callback` en la aplicación de Microsoft Entra correspondiente.
> - Confirmar el tenant, el registro de aplicación, los permisos delegados y su consentimiento, la biblioteca compartida y los usuarios autorizados. Necesitamos el identificador de unidad (`SHAREPOINT_DRIVE_ID`) y la carpeta raíz.
> - Almacenamiento persistente y copias de seguridad de PostgreSQL y de los archivos de la aplicación, con un procedimiento de restauración.
> - Acordar la integración final de Copilot con la API de la app, sus permisos y usuarios simultáneos. Ollama queda descartado; dimensionar CPU, RAM y disco para CAD grandes, importaciones y uso de la aplicación.
>
> La aplicación ya incluye contenedores e integración con Microsoft. Quedan la configuración del servidor, el traslado de datos y las pruebas del login y de archivos reales.

La capacidad final se fijará con mediciones en la máquina elegida. Las conversiones CAD,
la caché de SharePoint, las vistas 3D y las consultas de la futura integración con Copilot
deben entrar en ese cálculo; no reservar recursos para modelos de Ollama. Consultar
[vistas 3D](vistas-3d.md) y [concurrencia del asistente](asistente.md#concurrencia-y-despliegue).

## Configuración de la aplicación

Preparar una configuración privada de producción siguiendo [deployment.md](../deployment.md).
No copiar sin revisar las direcciones de localhost, los montajes de Windows o los valores
de ejemplo. Las credenciales se entregarán por el canal privado acordado con IT.

| Variable o elemento | Ajuste necesario |
|---|---|
| `ENVIRONMENT` | `production`. |
| `DOMAIN` y reglas del proxy | El nombre interno acordado con IT. El lanzador configura las rutas del proxy a partir de ese nombre. |
| `FRONTEND_HOST`, `BACKEND_CORS_ORIGINS` | La dirección HTTPS de la web accesible desde los equipos de los usuarios. |
| `VITE_API_URL` | El overlay incorpora `https://${DOMAIN}` al construir el frontend. |
| `MICROSOFT_REDIRECT_URI` | `https://<nombre-interno-api>/api/v1/login/microsoft/callback`, exactamente igual que la URI registrada en Entra como Web. |
| `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_SCOPES` | Los del registro autorizado para la organización y la biblioteca de destino; comprobar vigencia del secret y permisos concedidos. |
| `SHAREPOINT_ENABLED` | `true` para leer por Graph; en la implementación actual también activa el login Microsoft y desactiva el login por contraseña. |
| `SHAREPOINT_DRIVE_ID` | La unidad compartida elegida. Vacío significa el OneDrive de cada usuario conectado, no una biblioteca común. |
| `SHAREPOINT_ROOT_PATH` | La carpeta raíz dentro de esa unidad, no una ruta del sistema operativo. |
| `ASSETS_SOURCE_ID`, `ASSETS_SOURCE_NAME` | Mantener el identificador del conjunto actual al migrar su BD y sus documentos; el nombre es la etiqueta visible. |
| `ASSISTANT_ENABLED` | Mantener `false` en el servidor hasta disponer de la integración con Copilot. Ollama está descartado y el proveedor Codex incorporado el 18/11 es solo para la prueba local; no trasladar la sesión ni el token del puente del PC al servidor. |

El usuario necesita tanto un alta activa en la app como permisos en Microsoft para los
originales. Al pasar al entorno de INTEPLAST, su IT debe preparar o autorizar el registro
de Microsoft y los accesos a SharePoint.

### Primer administrador de INTEPLAST

Eduard administra el piloto de Eurecat. Para la entrega, INTEPLAST debe designar a la persona
responsable y comunicar su correo corporativo. Antes del primer arranque, quien despliegue
la web pondrá ese correo en `FIRST_SUPERUSER` del `.env.production` del cliente.

- **Base nueva.** `prestart` crea la cuenta configurada como administradora activa. La persona
  entra con Microsoft. `FIRST_SUPERUSER_PASSWORD` se configura con un secreto aleatorio de la
  instalación. La contraseña corporativa solo se introduce ante Microsoft.
- **Copia de la base de Eurecat.** La restauración conserva los usuarios y sus roles. Si el
  correo designado ya existe, `prestart` conserva su estado y sus permisos. Si falta, lo
  crea como administrador en el siguiente arranque. Quien haga el traspaso comprobará en la
  base de destino que la cuenta esté activa y tenga el rol de administrador.
- **Comprobación de entrega.** La persona designada inicia sesión con su propia cuenta y abre
  **Admin → Add User**. Después de verificarlo, revisar con INTEPLAST si Eduard debe conservar
  acceso y ajustar su rol en la instalación del cliente según lo acordado.

<a id="ajustes-pendientes-en-los-archivos-de-despliegue"></a>

## Servicios del servidor

El lanzador combina `compose.yml` y `compose.server.yml`. Arranca PostgreSQL,
las migraciones de `prestart`, el backend, el frontend compilado y Traefik con certificado
interno. El backend recibe el identificador del origen para leer por Graph. El asistente
permanece desactivado hasta integrar Copilot. El acceso a los documentos del equipo
requiere validar la biblioteca compartida con sus usuarios.

La integración Graph y el retorno automático ya existen: estos puntos son principalmente
configuración de despliegue. Si se decide usar carpetas locales del servidor en lugar de
SharePoint, habrá además que adaptar el selector: el actual modo local depende de Windows
y del servidor de desarrollo Vite. El modo SharePoint ya dispone de selector dentro de la web.

## Rutas, traslado de datos y persistencia

Con SharePoint no hace falta instalar OneDrive ni sincronizar la carpeta personal de Eduard
en el servidor. Graph obtiene los documentos y la app guarda una caché en su almacenamiento.

Los vínculos guardan rutas relativas, por ejemplo `0- Bolt Eye/3212 Pump Housing/...`.
Si se conserva la estructura bajo la raíz y el mismo `ASSETS_SOURCE_ID`, trasladar la app
de Windows a Linux no exige cambiar cada vínculo. `SHAREPOINT_ROOT_PATH` solo cambia si
cambia la carpeta raíz dentro de la unidad. Renombrar o mover documentos dentro de ella
sí requiere adaptar sus referencias: la integración actual los identifica por ruta.

Para conservar la instalación existente hay que trasladar:

- **La base de datos**, con fichas, usuarios, vínculos e información importada.
- **El volumen de archivos `app-uploads`**, montado en `/app/uploads`, con las subidas y
  derivados. Los originales externos siguen en SharePoint y tienen su propia conservación.
- **La configuración privada y las claves necesarias.** `SECRET_KEY` también cifra la caché
  de tokens Microsoft: conservarla de forma segura al migrar o planificar su rotación y
  el nuevo inicio de sesión de los usuarios. No cambiarla como si solo fuera una ruta.

Copiar el repositorio no traslada estos datos. Hacer una copia previa y comprobar la
restauración; el seed de ejemplo no recupera una instalación existente. El procedimiento
de migraciones y volúmenes está en [deployment.md](../deployment.md#persistencia-y-actualización-desde-la-versión-anterior).

## Estado y comprobaciones antes de abrir el acceso al equipo

En local, Eduard comprobó el retorno automático de Microsoft el 09/11 y la lectura de
archivos reales de su OneDrive por Graph el 12/11. La prueba con la biblioteca compartida
y las cuentas del equipo corresponde al despliegue en Eurecat.
[Pruebas locales de SharePoint](ficheros-externos.md#sharepoint-microsoft-graph).

Comprobar en el servidor de destino:

- Acceso a web y API desde otro equipo de la red/VPN, con certificados reconocidos.
- Login Microsoft con retorno automático y rol correcto del administrador corporativo.
- Listado de la biblioteca común y apertura/descarga de PDF y CAD reales con varios usuarios,
  incluyendo una cuenta sin permiso sobre un original para comprobar el rechazo.
- Conservación de fichas, vínculos y subidas tras migrar y reiniciar los servicios.
- Generación de vistas 3D y, si se incluye, funcionamiento del asistente con concurrencia.
- Copias de seguridad y restauración verificadas, y responsables de renovaciones y mantenimiento.
