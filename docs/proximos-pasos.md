# Próximos pasos

La implementación de protecciones y criterios de aceptación para todas las piezas se sigue en
[Plan de ingesta del 02/11/2026](plan-ingesta-2026-11-02.md), con verificaciones y contratos técnicos cerrados para las 21 piezas.

> Revisión completa contra el código el **26/10/2026**; las entradas posteriores llevan su
> fecha. El **04/11/2026** se contrastaron de nuevo los pendientes y se corrigieron los
> documentos desfasados ([revisión](revision-2026-11-04.md)). Este es el índice de
> pendientes; el contrato y las limitaciones de cada tema viven en el documento enlazado.
> Las pruebas de una fecha anterior no se presentan como validaciones de esta revisión.

## Próxima sesión: quitar el copiar y pegar del login de Microsoft

**Esta es la siguiente tarea acordada con Eduard (30/10/2026).** Se deja pendiente para
retomarla con tiempo; en esta sesión solo se documenta, sin cambiar configuración ni permisos.

**Punto de partida:** `SHAREPOINT_ENABLED=true` en la instalación local. Eduard ya ha
iniciado sesión correctamente con Microsoft después de dar de alta su correo en la app.
Su usuario está activo y **no es administrador**. Todavía se usa la dirección de retorno
de Postman, que obliga a copiar y pegar. Esto valida el login, **no** la lectura real de
archivos mediante Graph, que sigue pendiente. `SHAREPOINT_DRIVE_ID` está vacío: la primera
prueba apunta al OneDrive de Eduard, no a una biblioteca compartida de INTEPLAST.

### 1. Eduard o informática: registrar la dirección de retorno

En **Microsoft Entra → Registros de aplicaciones → la aplicación que ya estamos usando
→ Autenticación**, añadir esta URI a la plataforma **Web** (crear esa plataforma si falta):

```text
http://localhost:8000/api/v1/login/microsoft/callback
```

Eduard puede hacerlo si tiene permisos sobre ese registro; si no, pedirlo a informática
de Eurecat. No hace falta crear otra aplicación ni cambiar las credenciales para este paso.
Texto para retomar la petición: «Añadir la URI anterior como redirección Web en el registro
actual de la aplicación INTEPLAST para devolver el inicio de sesión al backend local».
La URI de Postman puede conservarse durante la prueba.
[Requisitos de Microsoft](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url).

### 2. Agente: cambiar la configuración y comprobar el retorno automático

**Después de confirmar que la URI está registrada**, cambiar solo esta variable del `.env`
existente, conservando el resto de sus valores:

```dotenv
MICROSOFT_REDIRECT_URI=http://localhost:8000/api/v1/login/microsoft/callback
```

Recrear el backend desde la raíz del repo (`docker compose up -d backend`) y recargar
`http://localhost:5173`. El código del retorno automático ya existe; este paso no requiere
implementar otro login. Comprobar que `/api/v1/login/methods` devuelve
`microsoft_paste=false` e iniciar un **nuevo** flujo con «Entrar con Microsoft».
**Criterio de cierre:** Microsoft devuelve al usuario a la app con sesión iniciada, sin
Postman ni copiar enlaces. En el despliegue final se registrará la URL HTTPS del servidor;
la URI de `localhost` es para esta instalación de desarrollo.

### Después: administración de usuarios y prueba real de archivos

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
| SharePoint: primera prueba real | **Login real confirmado el 30/10. Lo siguiente es quitar el copiar y pegar**, siguiendo los pasos al principio de este documento. Después: administrador corporativo, permisos, listado, visores, alta y actualización | [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| Validar el conocimiento: fichas, biblioteca SQL y RAG | Prueba en una sesión sin contexto: preguntas de desarrollo, respuestas con fuentes y registro de lagunas, sin recorrer los originales. Ya hay una evaluación de recuperación con 55 preguntas (27/10/2026); faltan preguntas reales de INTEPLAST | [Entrada a conocimiento](../conocimiento/README.md#entrada-para-una-sesión-sin-contexto), [evaluación](../conocimiento/rag/README.md) |
| Localizar cotas en el plano 2D | **En la aplicación desde el 30/10:** el índice del plano usa el lector del prototipo (capa vectorial o imagen globo a globo, detector en dos pasadas, RapidOCR + lector propio en ONNX, un número por plano, umbral provisional 0,434 vectorial / 0,6072 imagen). Reproduce exactamente las lecturas del prototipo en 5 planos reales. Prototipo congelado: no se ajusta más sin evidencia nueva. Pendiente: que Eduard verifique la referencia del 3167 (`muestra_verificacion.py`) y medir con planos nuevos de INTEPLAST, apartados antes de ajustar nada. Abiertos: el 3202 «G» (negritas), las lecturas ofrecidas sin verificar, globos grises o negros, numeración del cliente en negro (2820, 3214, 3174), búsqueda por valor (3051, 3197) y lectura directa de `.icp` | [Lector de globos](cotas-y-evidencia-web.md#lector-de-globos-30102026), [prototipo](../prototypes/data-explorer/README.md#correspondencia-globo-a-globo-y-ensayo-de-umbrales-29102026), [planos con globos](../conocimiento/planos-globos.md) |

<a id="1-correcciones-de-otras-piezas-en-espera-de-ejemplos"></a>
## 1. Ingesta de otras piezas: validar casos y resultados

**Ejemplos recibidos y contrastados.** Las 21 piezas tienen [balance por fichero y hoja](../conocimiento/ingesta/README.md), y el piloto de ficha 3167 está validado técnicamente. Usar estos contratos al ampliar el lector; las correcciones XLS/PPTX de la aplicación siguen limitadas al piloto 3212.

Las protecciones de fórmulas aleatorias/sin caché, firma de contenido, variantes PPAP y bloques secundarios ya están en producción local, con exclusión por celda y procedencia visible. La biblioteca y la aplicación mantienen lectores independientes. Las lecciones están contrastadas documentalmente y preparadas para revisión corporativa; no se han cargado en la app.

Detalle y criterios para avanzar: [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx),
[contrato actual](cotas-y-evidencia-web.md) y [propuesta de ingesta](ingesta-automatica.md).
La consulta al cliente debe centrarse en contrastar los casos y su elaboración (A13/A14),
no en pedir otra vez los ejemplos ya disponibles.

## 2. Asistente: Ollama, Copilot y concurrencia (pendiente de decisión)

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
