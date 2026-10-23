# Próximos pasos

> Estado al **20/10/2026**, tras la sesión de revisión y limpieza de ese día. Este documento
> resume qué queda abierto y qué hace falta para continuar. El detalle de cada tema está en el
> documento enlazado; actualizar aquí el estado cuando cambie.

## 1. Correcciones de otras piezas: en espera de ejemplos

**Estado:** la recopilación de ejemplos está en curso. No se programa nada hasta tenerlos.

- **Ya funciona con otras piezas:** las mediciones (CSV CMM por bloques y tablas `DR` de
  informes PPAP XLS/XLSX), al crear la pieza y con **Actualizar datos**.
- **Solo funciona en el 3212:** las correcciones (diapositivas PPTX, previsiones `DR(100%)` de
  los XLS de retoques y sus correspondencias con cotas). En otras piezas se detectan los
  documentos, no se interpretan y la lectura termina «con incidencias».

**Para continuar hace falta:**

1. Documentos de corrección de otra pieza: PPTX y XLS de retoques, con las mediciones de antes
   y después de cada corrección.
2. Resultados esperados contrastados: qué acción corresponde a qué cota y muestreo, qué
   previsión se lee de cada celda y qué diapositivas son decisiones de no actuar. Idealmente,
   revisados con quien prepara esos documentos (preguntas A13 y A14).
3. Con esos ejemplos, elegir el método: ampliar los adaptadores, una LLM con capacidad visual o
   una combinación.

**21/10/2026:** los ejemplos han llegado (`Exemples`, 8 features, 21 piezas con datos). El plan
medido de qué se extrae con reglas, qué con LLM y qué no está en los datos está en
[ingesta automática](ingesta-automatica.md); falta el punto 2 (resultados esperados revisados).

**Primer paso al recibirlos:** inventariar los documentos y comparar su estructura con la del
3212 (títulos `Tool correction n.m`, campos `DIM. Nr.`, hoja `DR(100%)` con retoque en la
columna O y previsiones en P:S). Escribir los resultados esperados **antes** de tocar código.

Detalle: [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx)
y [preguntas abiertas](preguntas-abiertas.md).

## 2. Asistente: Ollama, Copilot y concurrencia (pendiente de decisión)

**Estado:** sin cambios de comportamiento. En desarrollo hay un proceso de backend, que atiende
un chat a la vez; en producción (`--workers 4`) pueden ejecutarse hasta cuatro chats a la vez
por contenedor. Ollama limita por modelo, no por servidor, y el indexador de embeddings funciona
aparte del chat.

**Decisiones que hay que recoger**, con INTEPLAST y su IT (el [acta del 24/09/2026](acta-reunion-2026-09-24.md)
les asigna verificar la ejecución local o con Copilot, en Olot y en la República Checa):

1. **Proveedor:** Ollama local, un modelo en la nube como motor de nuestro chat, o un agente
   de Copilot Studio.
2. **Máquina**, si se mantiene Ollama: GPU, RAM disponible y modelos de chat y embeddings.
3. **Tiempos de respuesta medidos** con esos modelos en esa máquina, con una consulta y con
   dos simultáneas. Es la primera medición útil antes de decidir.
4. **Usuarios simultáneos** esperados.
5. **Alcance del límite:** solo el chat, o también los embeddings.

**Qué implica cada opción**, en resumen:

| Opción | Trabajo |
|---|---|
| Ollama, un chat en todo el servidor | Acotado: bloqueo compartido entre procesos (PostgreSQL), aviso de «ocupado», liberación ante errores y cancelaciones, y prueba con dos procesos |
| Ollama, N chats a la vez | El mismo mecanismo con un límite configurable según la capacidad medida |
| Modelo en la nube como motor | Nuevo `ChatProvider` (hoy solo hay Ollama), autenticación, coste y cuotas; los embeddings seguirían en Ollama salvo que se cambien |
| Agente de Copilot Studio | Trabajo distinto: exponer nuestras lecturas como API con Entra ID. Concretar antes de estimar |

Relacionado: el acceso a los originales en Microsoft 365 (pregunta A10) también depende de IT.

Detalle: [asistente, concurrencia y despliegue](asistente.md#concurrencia-y-despliegue).

## 3. Otras tareas abiertas

| Tarea | Estado | Detalle |
|---|---|---|
| Adjuntos del feature que no siguen a la pieza | Tarea separada. Afecta a la portada CAD y al plano de la fila COTAS. Desvincular y volver a vincular la pieza pierde sus cotas en el feature y la configuración 3D de la portada | [portadas CAD](portadas-cad.md#origen-del-cad-de-la-portada) |
| Política de finales de línea | Por decidir. El equipo de desarrollo tiene `core.autocrlf=true`: `git stash`, `checkout` o `reset` reescriben los ficheros en CRLF y Biome falla, aunque el contenido sea correcto. Recomendación: `* text=auto eol=lf` en `.gitattributes`; alternativa local: `git config core.autocrlf false`. Ya están en CRLF o mixtos en la copia de trabajo: `conocimiento/0-bolt-eye/3212/5-retoques-molde.md`, `conocimiento/0-bolt-eye/3212/6-metodo-medida.md`, `conocimiento/0-bolt-eye/3212/historial-molde.md` y `conocimiento/formatos-parsing.md` | — |
| Página antigua `/features/{id}/fichero/{assetId}` | Sin enlaces desde la interfaz. Su texto para un adjunto sin archivo aún remite a la edición del feature: corregir el texto o redirigir a la ficha de pieza | [aplicación](app-web.md) |
| SharePoint: primera prueba real | Implementado el 22/10/2026 (`SHAREPOINT_ENABLED`). Falta: crear en Admin el usuario con el correo de Microsoft, activar, entrar pegando la dirección de Postman y comprobar listado, visores, Nueva pieza y Actualizar datos. El secret caducaba hacia el **24/11/2026**: confirmar con informática. Para el login automático, pedir que registren `http://localhost:8000/api/v1/login/microsoft/callback` | [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| Volcado OAuth en `TODO.md` | Contiene la salida de una prueba de Graph (tenant y un código ya canjeado). Retirarlo y valorar limpiar el historial de Git. Lo gestiona Eduard | — |

## Hecho el 20/10/2026

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
