# Despliegue en servidor interno

**Decisión recogida el 05/11/2026:** preparar INTEPLAST sobre **Linux con Docker**,
con **HTTPS interno**, acceso desde la red corporativa o VPN e inicio de sesión
automático con Microsoft. Los usuarios abrirán un enlace; SSH quedará para administrar
y actualizar el servidor.

Esta guía recoge la opción elegida, la petición a IT y el trabajo pendiente. **No implica
que el servidor esté provisionado ni que se haya desplegado o validado la aplicación allí.**
Los comandos generales están en [deployment.md](../deployment.md); la integración de
archivos, en [SharePoint y originales externos](ficheros-externos.md#sharepoint-microsoft-graph).

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

## Por qué HTTPS y qué alternativas existen

Servir una web en `http://IP:puerto` es posible, como en el proyecto IoT con Grafana y
Node-RED. En INTEPLAST, el requisito adicional lo introduce el retorno automático del
login de Microsoft: debe estar registrado en Entra y utilizar HTTPS, salvo la excepción
de localhost para desarrollo. Véanse los
[requisitos de las URI de retorno de Microsoft](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url).

| Acceso | Aplicación a INTEPLAST |
|---|---|
| HTTP por IP y puerto, con el login manual actual | Técnicamente permite mantener el flujo de copiar y pegar el enlace: el retorno registrado sigue siendo el HTTPS de Postman. Opción temporal de prueba; no es el acceso elegido para el equipo. |
| HTTP por IP y puerto, con retorno automático a esa IP | Microsoft no admite esa URI HTTP de retorno para el flujo actual. |
| HTTPS interno, desde red corporativa o VPN | **Opción elegida.** Enlace compartido y retorno automático, sin publicar el servicio en Internet. |
| Túnel SSH y acceso por localhost | Alternativa de desarrollo, registrando el retorno de localhost y encaminando web y API. Cada usuario tendría que mantener su túnel. |

IP y HTTPS también pueden combinarse, con un certificado válido para esa IP y una URI
registrada. Se prefieren nombres internos para facilitar el acceso y la gestión de certificados.

## Petición a IT

Texto base para solicitar la infraestructura; sustituir los nombres cuando IT los confirme:

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
> - Acordar dónde ejecutar Ollama y sus modelos si se incluye el asistente, y dimensionar CPU, RAM, disco y, si procede, GPU según CAD grandes y usuarios simultáneos.
>
> La aplicación ya incluye contenedores e integración con Microsoft. Quedan la configuración del servidor, el traslado de datos y las pruebas del login y de archivos reales.

La capacidad final se fijará con mediciones en la máquina elegida. Las conversiones CAD,
la caché de SharePoint, las vistas 3D y el asistente deben entrar en ese cálculo; consultar
[vistas 3D](vistas-3d.md) y [concurrencia del asistente](asistente.md#concurrencia-y-despliegue).

## Configuración de la aplicación

Preparar una configuración privada de producción siguiendo [deployment.md](../deployment.md).
No copiar sin revisar las direcciones de localhost, los montajes de Windows o los valores
de ejemplo. Las credenciales se entregarán por el canal privado acordado con IT.

| Variable o elemento | Ajuste necesario |
|---|---|
| `ENVIRONMENT` | `production`. |
| `DOMAIN` y reglas del proxy | Los nombres acordados con IT. El Compose actual utiliza `dashboard.<dominio>` y `api.<dominio>`; si se eligen otros, adaptar las reglas. |
| `FRONTEND_HOST`, `BACKEND_CORS_ORIGINS` | La dirección HTTPS de la web accesible desde los equipos de los usuarios. |
| `VITE_API_URL` | La dirección HTTPS de la API; se incorpora al construir el frontend. En el Compose actual se calcula como `https://api.${DOMAIN}`: cambiar solo una variable del entorno del contenedor ya construido no actualiza la web. |
| `MICROSOFT_REDIRECT_URI` | `https://<nombre-interno-api>/api/v1/login/microsoft/callback`, exactamente igual que la URI registrada en Entra como Web. |
| `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_SCOPES` | Los del registro autorizado para la organización y la biblioteca de destino; comprobar vigencia del secret y permisos concedidos. |
| `SHAREPOINT_ENABLED` | `true` para leer por Graph; en la implementación actual también activa el login Microsoft y desactiva el login por contraseña. |
| `SHAREPOINT_DRIVE_ID` | La unidad compartida elegida. Vacío significa el OneDrive de cada usuario conectado, no una biblioteca común. |
| `SHAREPOINT_ROOT_PATH` | La carpeta raíz dentro de esa unidad, no una ruta del sistema operativo. |
| `ASSETS_SOURCE_ID`, `ASSETS_SOURCE_NAME` | Mantener el identificador del conjunto actual al migrar su BD y sus documentos; el nombre es la etiqueta visible. |
| `ASSISTANT_OLLAMA_URL` | Dirección alcanzable desde el backend al servidor de Ollama, si se incluye el asistente. |

El usuario necesita tanto un alta activa en INTEPLAST como permisos en Microsoft para
los originales. Hay que designar al primer administrador corporativo de la app; el rol de
administrador de INTEPLAST no concede acceso a SharePoint. Si se cambia de Eurecat al entorno
de INTEPLAST, su IT debe preparar o autorizar el registro y los accesos correspondientes.

## Ajustes pendientes en los archivos de despliegue

El despliegue elegido necesita concretar estos ajustes; **no están implementados por el
hecho de documentarlos**:

1. **Certificados y proxy interno.** `compose.traefik.yml` usa Let's Encrypt con el reto
   TLS-ALPN-01, que requiere que la autoridad pueda alcanzar el servicio por el puerto 443.
   Esa receta no funciona sin cambios en un servidor accesible solo por red privada.
   Configurar los certificados de IT en el proxy, o integrar su proxy corporativo, adaptando
   también las reglas y el resolver `le` de `compose.yml`. IT puede valorar DNS-01 para un
   dominio que controle si prefiere esa alternativa; no requiere publicar la web.
   [Tipos de validación de Let's Encrypt](https://letsencrypt.org/docs/challenge-types/).
2. **Identificador del origen sin montaje local.** Actualmente `ASSETS_SOURCE_ID` y
   `ASSETS_SOURCE_NAME` llegan al backend mediante `compose.assets.yml`, que además exige
   `ASSETS_HOST_PATH` y monta una carpeta. Para usar solo SharePoint, pasarlos al backend
   mediante la configuración de producción sin exigir ese montaje. Ponerlos únicamente
   en `.env.production` no basta si Compose no los transmite al servicio.
3. **Servicios de producción.** Usar el frontend compilado y el backend de producción.
   Excluir `compose.override.yml`, destinado al desarrollo, y definir los servicios y
   puertos que utilizará el proxy elegido. No es necesario publicar PostgreSQL a los usuarios.
4. **Asistente.** Si se traslada también, instalar Ollama y sus modelos o conectarlo a un
   servicio existente. La dirección `host.docker.internal` del PC con Docker Desktop no
   debe darse por configurada en Docker Engine sobre Linux. Probar conectividad y carga
   concurrente; el proveedor y el dimensionamiento siguen pendientes de acordar.

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

Al recoger esta decisión, la configuración local tiene SharePoint activado y el identificador
de unidad vacío. Está documentado el login real correcto del 30/10/2026, usando el retorno
manual de Postman. **La lectura de archivos reales por Graph sigue pendiente de validar.**
El seguimiento está en [próximos pasos](proximos-pasos.md#próxima-sesión-quitar-el-copiar-y-pegar-del-login-de-microsoft).

Comprobar en el servidor de destino:

- Acceso a web y API desde otro equipo de la red/VPN, con certificados reconocidos.
- Login Microsoft con retorno automático y rol correcto del administrador corporativo.
- Listado de la biblioteca común y apertura/descarga de PDF y CAD reales con varios usuarios,
  incluyendo una cuenta sin permiso sobre un original para comprobar el rechazo.
- Conservación de fichas, vínculos y subidas tras migrar y reiniciar los servicios.
- Generación de vistas 3D y, si se incluye, funcionamiento del asistente con concurrencia.
- Copias de seguridad y restauración verificadas, y responsables de renovaciones y mantenimiento.
