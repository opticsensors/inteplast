# TODO

## 1. Pedir autorización a EURECAT

**Estado:** Graph PowerShell instalado; aprobación de informática pendiente.

**Carpeta:** [3212 Pump Housing en OneDrive](https://eurecatcloud-my.sharepoint.com/my?id=%2Fpersonal%2Feduard%5Falmar%5Feurecat%5Forg%2FDocuments%2FEscritorio%2Fproyectos%2F11%2E%20inteplast%2FExemples%2F3212%20Pump%20Housing&FolderCTID=0x012000DB740F941715AC47B18AAA9C3E7C3844).

- [ ] Enviar esta justificación desde la pantalla «Aprobación necesaria»:

> Solicito autorizar Microsoft Graph Command Line Tools para eduard.almar@eurecat.org.
> Queremos probar la lectura de PDF y modelos 3D de «3212 Pump Housing» en OneDrive para
> vincularlos a la aplicación INTEPLAST sin subirlos de nuevo.
> Pedimos Files.Read: lectura de archivos del usuario, sin escritura ni borrado;
> este permiso no queda limitado a esa carpeta.
> Si preferís una aplicación de pruebas con acceso acotado al proyecto, indicadnos cómo habilitarla.

## 2. Comprobar el acceso tras la aprobación

- [ ] Si autorizan la herramienta PowerShell, ejecutar:

  ```powershell
  Import-Module Microsoft.Graph.Authentication
  Connect-MgGraph -Scopes "Files.Read" -ContextScope Process
  Get-MgContext
  ```

- [ ] Obtener `driveId` e `itemId` y abrir un PDF mediante Graph sin usar la carpeta local.

**Estos comandos son solo para la prueba; no se ejecutarán para arrancar la web.**

## 3. Acordar e integrar la conexión de la web

**Opción preferida:** acceso automático del servidor, de solo lectura y limitado al proyecto,
si todos los usuarios autorizados de la web deben consultar los mismos archivos.
Acordarlo con informática. Si cada usuario necesita permisos distintos, usar acceso con su cuenta.
La aprobación de PowerShell no autoriza automáticamente la aplicación.

- [ ] Concretar con informática el registro y los permisos de la aplicación antes de programar.
- [ ] Añadir Graph conservando los documentos vinculados, los visores y las vistas 3D ligeras.
      Mantener los originales en OneDrive, sin subidas manuales duplicadas.
- [ ] Definir cómo aceptar nuevas revisiones y actualizar sus vistas sin perder el historial.
- [ ] Verificar apertura, descarga, vuelta a la ficha, renombrado, movimiento y pérdida de acceso.
      Permitir volver a vincular si cambia la identidad del archivo.

## 4. Reunión con INTEPLAST

- [ ] **Primero:** confirmar ubicación de originales, contacto de informática, permisos y revisiones.
      Preparar su autorización y el cambio de origen de EURECAT a INTEPLAST.
- [ ] Pedir una exportación compatible del molde para completar su vista web.

Preguntas [A10 y A11](docs/preguntas-abiertas.md).

## Mientras esperamos: continuar en local

- [ ] Incorporar las mediciones del Bolt Eye: N170/N117/N178, muestreos y correcciones.
      Distinguir los informes del plano rev. 06 del PDF disponible rev. 07.
- [ ] Añadir marcado de zonas sobre el plano o una imagen, ligado al documento y su revisión.
