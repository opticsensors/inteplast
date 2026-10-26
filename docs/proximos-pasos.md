# Próximos pasos

> Estado documental al **26/10/2026**, contrastado con el código. Este es el índice de
> pendientes; el contrato y las limitaciones de cada tema viven en el documento enlazado.
> Las pruebas de una fecha anterior no se presentan como validaciones de esta revisión.

<a id="1-correcciones-de-otras-piezas-en-espera-de-ejemplos"></a>
## 1. Ingesta de otras piezas: validar casos y resultados

**Ejemplos recibidos e inventariados.** Seleccionar una segunda pieza y preparar resultados
esperados revisados antes de ampliar el lector de correcciones. Ya hay lectura genérica
de mediciones; las correcciones XLS/PPTX siguen limitadas al piloto.

También falta trasladar a producción las protecciones de la biblioteca de conocimiento:
fórmulas aleatorias y sin caché, archivos cuyo contenido no coincide con su extensión y
variantes de las hojas PPAP. La biblioteca y la aplicación tienen lectores independientes.

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
| Captura de pieza tras cambios en Graph | Corregir su invalidación cuando cambia el contenido sin cambiar UUID/version del vínculo | [Cambios remotos y miniatura](portadas-cad.md#cambios-remotos-y-miniatura-de-pieza) |
| SharePoint: primera prueba real | Validar login delegado, permisos, listado, visores, alta y actualización con un entorno autorizado | [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| Página antigua `/features/{id}/fichero/{assetId}` | Actualizar el mensaje del adjunto sin archivo o redirigir a la pieza; ya no recibe enlaces de la UI | [Aplicación](app-web.md) |
| Política de finales de línea | Acordar una política LF en el repositorio; la incidencia de CRLF se registró el 20/10 | [Desarrollo](../development.md) |
| Volcado OAuth señalado en `TODO.md` | Eduard revisará su retirada y el tratamiento del historial; tarea ajena a esta revisión documental | — |
| Prueba de conocimiento en sesión sin contexto | El usuario la hará más adelante: preguntas de desarrollo, respuestas con fuentes y registro de lagunas, sin recorrer originales | [Entrada a conocimiento](../conocimiento/README.md#entrada-para-una-sesión-sin-contexto) |

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
