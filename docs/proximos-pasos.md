# Próximos pasos

La implementación de protecciones y criterios de aceptación para todas las piezas se sigue en
[Plan de ingesta del 02/11/2026](plan-ingesta-2026-11-02.md), con verificaciones y contratos técnicos cerrados para las 21 piezas.

> Revisión completa contra el código el **26/10/2026**; las entradas posteriores llevan su
> fecha. El **04/11/2026** se contrastaron de nuevo los pendientes y se corrigieron los
> documentos desfasados ([revisión](revision-2026-11-04.md)). Este es el índice de
> pendientes; el contrato y las limitaciones de cada tema viven en el documento enlazado.
> Las pruebas de una fecha anterior no se presentan como validaciones de esta revisión.

## Login de Microsoft sin copiar y pegar: hecho (09/11/2026)

Era la tarea acordada el 30/10/2026. **Eduard confirma el 09/11/2026** que la dirección de
retorno Web `http://localhost:8000/api/v1/login/microsoft/callback` ya está registrada en Entra
y que ha entrado en la aplicación final con su cuenta de Eurecat, sin Postman ni copiar enlaces.
El `.env` local tiene `MICROSOFT_REDIRECT_URI` con esa dirección y `SHAREPOINT_ENABLED=true`
(comprobado el 09/11/2026). La prueba no se repitió en esa sesión: Docker estaba parado.
La URI de `localhost` sirve para la instalación de desarrollo; en el servidor habrá que
registrar su URL HTTPS.

Esto cierra el login, **no** la lectura de archivos reales por Graph, que sigue pendiente.
`SHAREPOINT_DRIVE_ID` está vacío: las pruebas apuntan al OneDrive de quien inicia sesión, no a
una biblioteca compartida de INTEPLAST.

## Próxima sesión de la app final: usuarios y prueba real de archivos

**Despliegue futuro acordado el 05/11/2026:** Linux con Docker y HTTPS interno, accesible
por red corporativa o VPN. La petición a IT, configuración y comprobaciones pendientes
están en [Despliegue en servidor interno](despliegue-servidor.md). El servidor aún no está validado.

**Fases fijadas por Eduard el 09/11/2026:** 1) pruebas con cuentas de Eurecat; 2) servidor de
Eurecat, cuentas de Eurecat y SharePoint de Eurecat; 3) traslado a los servidores de INTEPLAST.
Las fases 1 y 2 no dependen de A10; la 3 sí.

- Definir con Eduard quién será el primer administrador corporativo y asignarle ese rol
  una vez. Su cuenta actual sigue siendo normal; **no se le han concedido permisos de
  administrador**. El administrador también entrará con Microsoft y gestionará las altas
  desde «Admin», sin tener que crear cada usuario manualmente en la BD.
- Adaptar el formulario de alta: todavía exige contraseña aunque en modo Microsoft no se
  utiliza. Actualmente el switch de SharePoint también desactiva el login con contraseña;
  es una decisión de la app, no una obligación de SharePoint. La propuesta es usar Microsoft
  para usuarios y administradores, con los roles gestionados por la app. Dar de alta un
  usuario en ella no le concede acceso a archivos en Microsoft.
- Probar listado y apertura de un PDF/STEP real, y después visores, alta y actualización.
  El éxito del login no sustituye estas comprobaciones. La biblioteca compartida y los
  permisos de INTEPLAST siguen pendientes de concretar.

Detalle técnico: [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph).

## Prioridad a corto plazo (28/10/2026)

Eduard fija estos tres frentes como los siguientes:

| Tarea | Próximo paso | Referencia |
|---|---|---|
| SharePoint: primera prueba real | Login real el 30/10; **retorno automático, sin copiar y pegar, confirmado el 09/11**. Lo siguiente: administrador corporativo, permisos, listado, visores, alta y actualización ([próxima sesión](#próxima-sesión-de-la-app-final-usuarios-y-prueba-real-de-archivos)) | [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| Validar el conocimiento: fichas, biblioteca SQL y RAG | Prueba en una sesión sin contexto: preguntas de desarrollo, respuestas con fuentes y registro de lagunas, sin recorrer los originales. Ya hay una evaluación de recuperación con 55 preguntas (27/10/2026); faltan preguntas reales de INTEPLAST | [Entrada a conocimiento](../conocimiento/README.md#entrada-para-una-sesión-sin-contexto), [evaluación](../conocimiento/rag/README.md) |
| Localizar cotas en el plano 2D | **En la aplicación desde el 30/10:** el índice del plano usa el lector del prototipo (capa vectorial o imagen globo a globo, detector en dos pasadas, RapidOCR + lector propio en ONNX, un número por plano, umbral provisional 0,434 vectorial / 0,6072 imagen). Reproduce exactamente las lecturas del prototipo en 5 planos reales. Prototipo congelado: no se ajusta más sin evidencia nueva. Pendiente: que Eduard verifique la referencia del 3167 (`muestra_verificacion.py`) y medir con planos nuevos de INTEPLAST, apartados antes de ajustar nada. Abiertos: el 3202 «G» (negritas), las lecturas ofrecidas sin verificar, globos grises o negros, numeración del cliente en negro (2820, 3214, 3174), búsqueda por valor (3051, 3197) y lectura directa de `.icp`. **Desde el 05/11 los lectores nuevos (`[]`, `No.` y recuadros) y el `.icp` se prueban primero en el [visor de `conocimiento/`](#visor-de-conocimiento-banco-de-pruebas-antes-de-la-app-final)**; no están en la app | [Lector de globos](cotas-y-evidencia-web.md#lector-de-globos-30102026), [prototipo](../prototypes/data-explorer/README.md#correspondencia-globo-a-globo-y-ensayo-de-umbrales-29102026), [planos con globos](../conocimiento/planos-globos.md) |

## Visor de `conocimiento/`: banco de pruebas antes de la app final

**Aclarado por Eduard el 09/11/2026.** Antes de cargar las 21 piezas en la aplicación final,
Eduard usa el [visor de `conocimiento/`](../prototypes/data-explorer/conocimiento/README.md)
(`prototypes/data-explorer/conocimiento/app.py`, http://127.0.0.1:8765) como aplicación de
pruebas con todas las piezas. Ahí se prueban también los lectores de planos antes de llevarlos
a la app. Cuando Eduard habla de «la app de conocimiento» se refiere a este visor.

Pasar algo a la app final significa **reimplementarlo** en `backend/app/ingestion/` con sus
tests: la app no importa ni copia el prototipo (separación de producto, `CLAUDE.md`).
**Primero se termina el visor** (Eduard, 09/11/2026). Terminado, sirve para enseñar sus resultados a
INTEPLAST, con cada error respaldado por escrito; lo que ya está en las preguntas a INTEPLAST no se repite.

Estado el 09/11/2026: 26 lecturas de planos sin `.icp` y 21 capturas CAD ya generadas en
`out/conocimiento/`. Los lectores de planos del visor y de los scripts de medida son ya un solo
código, `prototypes/data-explorer/lectores_planos.py`, sin cambiar ninguna lectura
([detalle](../prototypes/data-explorer/README.md#un-solo-código-de-lectura-de-planos-09112026)).
Tests: 97 del visor (`tests/test_visor_conocimiento.py`) y 18 de los lectores
(`tests/test_lectores_planos.py`), dentro de los 174 del prototipo, todos correctos. Las mediciones
de `probar_lector_planos.py` anteriores al 09/11 son histórico, con puntuaciones redondeadas; las
nuevas, con puntuación completa, van a una carpeta nueva.
Pendientes: [visor, pendiente](../prototypes/data-explorer/conocimiento/README.md#pendiente-09112026).

<a id="1-correcciones-de-otras-piezas-en-espera-de-ejemplos"></a>
## 1. Ingesta de otras piezas: validar casos y resultados

**Ejemplos recibidos y contrastados.** Las 21 piezas tienen [balance por fichero y hoja](../conocimiento/ingesta/README.md), y el piloto de ficha 3167 está validado técnicamente. Usar estos contratos al ampliar el lector; las correcciones XLS/PPTX de la aplicación siguen limitadas al piloto 3212.

Las protecciones de fórmulas aleatorias/sin caché, firma de contenido, variantes PPAP y bloques secundarios ya están en producción local, con exclusión por celda y procedencia visible. La biblioteca y la aplicación mantienen lectores independientes. Las lecciones están contrastadas documentalmente y preparadas para revisión corporativa; no se han cargado en la app.

Detalle y criterios para avanzar: [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx),
[contrato actual](cotas-y-evidencia-web.md) y [propuesta de ingesta](ingesta-automatica.md).
La consulta al cliente debe centrarse en contrastar los casos y su elaboración (A13/A14),
no en pedir otra vez los ejemplos ya disponibles.

## 2. Asistente: Copilot de empresa, junto con el servidor (trabajo futuro)

**Preferencia de Eduard (09/11/2026):** si es posible, el asistente será el **Copilot de
empresa**, mediante un agente que permita usarlo con los datos de la app. Es trabajo futuro,
que se abordará junto con el servidor. Mientras tanto se mantiene el chat actual con Ollama.

Acordar con INTEPLAST y su IT proveedor, máquina, usuarios simultáneos y alcance del límite.
Medir latencia con una consulta y con dos simultáneas antes de dimensionar. La integración
actual y las alternativas pendientes se mantienen en
[asistente, concurrencia y despliegue](asistente.md#concurrencia-y-despliegue).
Los acuerdos de IT constan en el [acta del 24/09](acta-reunion-2026-09-24.md).

## 3. Otras tareas abiertas

| Tarea | Próximo paso | Referencia |
|---|---|---|
| Adjuntos del feature que no siguen a la pieza | Definir cómo actualizar el vínculo sin perder cotas ni configuración de portada | [Origen del CAD](portadas-cad.md#origen-del-cad-de-la-portada) |
| Captura de pieza tras cambios en Graph | **Corregida el 30/10:** la versión del origen invalida la captura en backend y navegador; probada con Graph simulado. Pendiente comprobar la conexión real | [Cambios remotos y miniatura](portadas-cad.md#cambios-remotos-y-miniatura-de-pieza) |
| Lector de comparativas CSV del backend (`measurement_tables.csv_rows`) | Encontrado el 09/11 al cargar el 3197 en la biblioteca: asigna los POINT de las comparativas del 3212 a N178 (título en la misma línea que el primer valor), deja sin tolerancias las comparativas con las cavidades desde la columna 7 (3197 `.03`/`.04`) y no reconoce `3197_totes_nozzle 55/65.csv`. No se ha corregido: es la app final, después del visor | [3197](../conocimiento/0-bolt-eye/3197.md#csv-de-la-cmm-en-la-biblioteca-09112026) |
| Página antigua `/features/{id}/fichero/{assetId}` | Actualizar el mensaje del adjunto sin archivo o redirigir a la pieza; ya no recibe enlaces de la UI | [Aplicación](app-web.md) |
| Política de finales de línea | Propuesta LF y procedimiento escritos el 04/11; los aplica Eduard con la copia limpia | [Desarrollo](../development.md#finales-de-línea-propuesta-del-04112026-sin-aplicar) |
| Volcado OAuth en el historial de Git | Retirado de `TODO.md` el 04/11 (el código era de un solo uso y ya caducado). Sigue en el historial desde `a6f3b44`; reescribirlo o no lo decide Eduard | — |

## Hecho el 20/10/2026

Registro histórico de aquella sesión; estas pruebas no se han repetido el 26/10.

- Buscador del plano: cada resultado indica su origen («Revisada», «Texto del PDF» u «OCR · sin
  verificar») y se avisa cuando hay propuestas OCR.
- Series de informes XLS de otras piezas: ya no reciben las etiquetas del piloto 3212
  (`describeSeries`), con test de regresión.
- Limpieza: tres componentes y tres exportaciones sin uso eliminados; test obsoleto del menú
  «Opciones de la pieza» trasladado a la ficha de pieza.
- Documentación: ficha de pieza como lugar de los archivos, portada CAD, concurrencia del
  asistente y estado de la generalización de correcciones.
- Comprobaciones: compilación, Biome y 141 tests de componentes (140 correctos, 1 omitido: el
  opcional del diálogo de Windows).
