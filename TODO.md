# TODO

-  [ ] quiero que planeemos juntos que hacer con los datos de ver_tofo.py en data explorer.
me dijiste que txt, que son los datos raw de los puntos medidos de cmm, permite desde el propio software configurar como extraer de esas nuves de puntos cotas y ciertos otros valores, los cuales se guardan en los csv, por lo tanto no hace falta representar los txt ya que estos no nos aprotan nada relevante apra nuestra web app de inteplast verdad?
centrandonos en los csv, hay muchas filas, las que empiezan por point X o global X nos son de interes olos que empiezan por posicions? o solo las corerspondientes a tolerancias NXXX que son los numericos encercalsod marcados en verde en el plano 2d. De los de inetres que crees que es mas interesante ver si estan dentro de toleacias, su evolucion por cavidad o por tandas o todo? y cual es la forma mas inetersanete de representarlo?

por otro lado los perfiles a y b que son y los pondrias en la app o no son relevantes?

por otro lado crees que la app puede encontarr una forma de buscar en el pdf del plano 2d esas cotas sin tener que hacerlo manual? que necesitariamos? un pdf con svg/texto ? con el de ahora que es como una mimaghen no se podria mejorar? realmente crees que hace falta? 

luego lo mas interesante de todo creo que es no tanto ve rla evolucion de las cotas sino ver en base los resultados de mediciones que modificaicon se ha hecho y como ha afectado eso a la nueva medicion. esto donde esta documentado, en los excels? en los pptx? puedes llertelos para la pieza de estudio y decirme?

por otro lado, que son el fichero de punts nous? me dijiste que era algo del molde? esta realcionado/linkado con los cmabios hechos? nos interesa?

haz una lectura extensa de la doc y tu mismo leete ficheros de la carpeta de la pieza de estudio para entender como funciona/esta ordenado ese proceso de modificaciones iterativas...

no cambies nda del codigo, lee la doc del repo, lee tambien los ficheros de la carpeta de inteplast datos: C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples\3212 Pump Housing

-  [ ] 









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
