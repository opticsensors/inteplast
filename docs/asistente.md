# Asistente de consulta

## Decisión de Eduard (17/11/2026)

**Ollama queda descartado. La solución final será Copilot de empresa mediante un agente
conectado a la API de la aplicación.** Esta decisión sustituye la preferencia provisional
del 09/11 y las alternativas de despliegue con Ollama.

Antes de trasladar la app al servidor, se hará una **prueba de concepto en el PC de Eduard
con Codex (ChatGPT)**, sustituyendo temporalmente a Ollama como motor de fondo del asistente:

- Usar **el modelo más rápido disponible** para probar la respuesta y la experiencia de uso.
  El 18/11 se eligió `gpt-reserve` con esfuerzo `low` por el menor tiempo observado en
  tres pruebas individuales. No demuestra que sea siempre el más rápido.
- **No crear un agente para esta prueba.** Usar Codex de fondo con instrucciones
  para simular cómo respondería un agente conectado a la API de la app, apoyándose en sus
  consultas y resultados. La prueba debe permitir evaluar respuestas y fuentes con datos reales.
- Codex es una solución **provisional, local y anterior al despliegue**. No se plantea llevar
  esta prueba al servidor como sustituto de Copilot.
- Después, integrar **Copilot como solución final**, concretando con IT la conexión a la API,
  autenticación, permisos y uso por varios usuarios.

**Estado: prueba local integrada el 18/11/2026, después de A–E.** Codex sustituye el generador
y su configuración desactiva los embeddings y el indexador de Ollama. Se conserva la búsqueda
por palabras. No dimensionar ni pedir una instalación de Ollama para el servidor.

## Prueba local integrada (18/11/2026)

El backend incluye el [glosario de la aplicación](../backend/app/assistant/knowledge/glosario.md)
en el contexto que envía al modelo, tanto para decidir qué consultar como para redactar la
respuesta con los resultados. El glosario aporta las definiciones generales. Las fichas y las
mediciones aportan los hechos y las fuentes de cada caso. Para actualizar el vocabulario,
editar ese archivo y reconstruir el backend.

Un proveedor que use el mismo flujo de chat recibirá el glosario automáticamente. Si Copilot
se conecta desde fuera como agente de Microsoft y gestiona su propio contexto, su integración
deberá obtener ese mismo recurso a través de la API e incluirlo en el contexto del agente.
La ruta del archivo y su contenido se pueden conservar en ambos casos.

Para comprobar el glosario con cualquier proveedor, hacer estas tres preguntas en la misma
conversación usando un feature y una pieza vinculados en el catálogo de prueba.

| Pregunta de prueba | Qué comprobar |
|---|---|
| ¿Qué es un feature en esta app? | Explica el concepto y su relación con las piezas. Si da un ejemplo genérico, lo identifica como tal. |
| ¿En qué piezas está registrado el feature X? | Los vínculos coinciden con los del catálogo y la respuesta incluye la ficha como fuente. |
| ¿Cómo se aplica esa definición a la pieza Y? | Usa la definición del primer turno y el vínculo real de Y. Cualquier cota o advertencia concreta debe aparecer en los datos recuperados. |

El frontend y su protocolo permanecen intactos. El nuevo proveedor Python llama a un puente
HTTP en Windows, que ejecuta `codex exec` con la sesión de Codex del PC. Cada llamada es
efímera, en un directorio vacío, sin herramientas de shell, navegador, archivos o multiagente.
Codex devuelve texto o solicitudes JSON de las cuatro lecturas admitidas; el backend valida
y ejecuta esas lecturas con el usuario autenticado. No se crea un agente autónomo ni una
nueva API de datos para Copilot.

La instalación selecciona `ASSISTANT_PROVIDER=codex` y `ASSISTANT_MODEL=gpt-reserve` en su
`.env` privado. El token del puente queda fuera de Git y del frontend. `compose.yml` transmite
la configuración sin un overlay adicional. El puente está separado de las sesiones de
desarrollo; cambiarlo no modifica su modelo ni configuración.

Límites de la prueba: una llamada al modelo a la vez, respuesta completa al terminar en lugar
de token a token, y recuperación por palabras sin embeddings. Detener la consulta cancela su
proceso. Tras reiniciar Windows se arranca el puente con
`powershell -File .\integrations\codex-bridge\start.ps1 -Background`; no se instala un servicio
automático. Preparación, variables, modelo y pruebas en
[integrations/codex-bridge/README.md](../integrations/codex-bridge/README.md).

Al integrar se repitieron **83 pruebas aisladas** (8 Node, 16 del proveedor y 59 del asistente),
con Ruff y mypy correctos. El recorrido completo de la prueba previa, con BD sintética,
puente HTTP y Codex real, tardó 7,03 s. Eso no valida la ingesta automática ni la calidad
general sobre documentos del cliente; sigue pendiente la evaluación con preguntas reales
y la integración final de Copilot.

**Comprobación en la instalación:** backend reconstruido, puente activo en segundo plano y
consulta real de advertencias con fuente completada en 17,07 s, sin escribir datos. Se usó
una credencial técnica temporal de una cuenta existente, sin repetir el login Microsoft.
El frontend y la BD mantienen sus contenedores. La prueba solo acredita ese recorrido;
no sustituye una evaluación de calidad del asistente.

## Implementación de referencia con Ollama

**Estado contrastado con el código el 26/10/2026.** Esta ficha describe el chat
implementado. Esta revisión documental no ha ejecutado tests ni consultas al modelo.
La importación que alimenta sus lecturas se describe en
[cotas y evidencia](cotas-y-evidencia-web.md); su ampliación, en
[ingesta automática](ingesta-automatica.md).

El proveedor anterior, conservado como referencia técnica, usa Ollama en la URL configurada por el servidor; el modelo por
defecto es `qwen3.5:2b`, con `think: false`. Muestra texto progresivamente,
admite detener/reintentar y conserva
la conversación al navegar dentro de la app. Se abre abajo a la derecha y se
minimiza a su cabecera. Cerrar no borra el historial; «Nueva conversación», salir de
la sesión o recargar sí. El historial solo vive en memoria del navegador.

## Arranque de la implementación con Ollama (referencia técnica)

Los pasos siguientes describen el código existente. No son el plan de la prueba con Codex
ni las instrucciones para el futuro servidor.

1. Instalar y abrir Ollama en Windows. Descargar el modelo una vez:
   `ollama pull qwen3.5:2b` y `ollama pull embeddinggemma`.
2. Añadir a la `.env` privada de la raíz, conservando su configuración existente:

   ```dotenv
   ASSISTANT_ENABLED=true
   ASSISTANT_OLLAMA_URL=http://host.docker.internal:11434
   ASSISTANT_MODEL=qwen3.5:2b
   ```

3. Reconstruir: `docker compose up -d --build db prestart backend`.
4. Arrancar el frontend con `npm run dev --workspace frontend` e iniciar sesión.

Docker Desktop usa `host.docker.internal` para llegar a Ollama en Windows. Para un
backend ejecutado directamente en el mismo PC, usar `http://127.0.0.1:11434`.
El navegador habla exclusivamente con el backend; no necesita acceso a Ollama.
Otros usuarios de esta app usarían el Ollama del servidor, no el de su propio PC.

La plantilla `.env.example` lo deja desactivado. `ASSISTANT_ENABLED=false`, seguido
de recrear el backend y recargar la página, oculta el módulo y bloquea su endpoint.
La migración `i40d36fcab18` crea la caché `assistant_embedding` y habilita pgvector.
Compose usa PostgreSQL 18 con pgvector, conservando el volumen existente. En una
instalación con PostgreSQL externo hay que instalar la extensión antes de migrar.

Configuración adicional: `ASSISTANT_MAX_TOKENS=1024`,
`ASSISTANT_CONTEXT_TOKENS=8192`, `ASSISTANT_TIMEOUT_SECONDS=120`.
Se mantiene el modelo cargado 15 minutos después de usarlo. La primera consulta
puede tardar más; desactivar thinking no hace instantánea la inferencia en CPU.
No hay límite de palabras: se pide responder de forma directa y con la extensión
necesaria. Si alcanza el límite técnico de tokens, la interfaz lo indica. Se atiende una petición por proceso;
las simultáneas reciben un aviso para reintentar, sin acumular cola. En producción hay varios
procesos: ver [Concurrencia y despliegue](#concurrencia-y-despliegue). Estos límites describen
la implementación existente; habrá que medir la prueba con Codex y la integración con Copilot.
Las respuestas largas se conservan completas en pantalla. El navegador conserva
hasta 30 turnos y envía como máximo cuatro intercambios completos anteriores,
abreviando las respuestas largas, más la pregunta actual. La API admite hasta nueve
mensajes, 3.000 caracteres por mensaje y 12.000 en conjunto; el servicio selecciona
además un historial reciente de hasta 4.000 caracteres para el modelo. La memoria de
la conversación es limitada aunque los turnos anteriores sigan visibles.

## Concurrencia y despliegue

**Plan decidido el 17/11/2026: prueba local con Codex y solución final con Copilot.** La tabla
siguiente describe la implementación con Ollama revisada el 26/10/2026, aún presente en el
código. Sus límites son antecedentes técnicos, no una validación de los nuevos proveedores.

### Cómo funciona hoy

| Elemento | Comportamiento | Código |
|---|---|---|
| Chat | Cada proceso del backend atiende **una consulta a la vez**. Si llega otra, espera 0,1 s y recibe «El asistente está atendiendo otra consulta…», sin cola. | `assistant/router.py` (`_slot`) |
| Procesos | Desarrollo: `fastapi run --reload`, **un proceso** (`compose.override.yml`). Producción: `--workers 4` (`backend/Dockerfile`), es decir, **hasta cuatro consultas de chat a la vez por contenedor**. | |
| Límite de tiempo | Tras adquirir el turno, `ASSISTANT_TIMEOUT_SECONDS` (120 s por defecto) limita la ejecución de la consulta, incluidas las esperas al proveedor. La espera inicial de hasta 0,1 s del semáforo es independiente. | `assistant/router.py`, `assistant/providers.py` |
| Indexador | Cada `ASSISTANT_INDEX_INTERVAL_SECONDS` (60 s) comprueba qué textos han cambiado y solo calcula los embeddings pendientes, en lotes de cuatro, con un segundo de pausa mientras quede trabajo. Un bloqueo de PostgreSQL impide que dos procesos indexen a la vez. Funciona aparte del chat y **puede coincidir con él**, también en desarrollo. | `assistant/index.py` |
| Búsqueda semántica | `search_knowledge` calcula durante el chat el embedding de la pregunta. | `assistant/semantic.py` |
| Proveedor | Chat y embeddings usan adaptadores separados hacia la URL de Ollama. La app no establece un límite compartido entre ambos; la capacidad y configuración del servidor deben comprobarse en el despliegue elegido. | `assistant/providers.py`, `assistant/embeddings.py` |

**Riesgo, no medido:** en producción, varias consultas pueden competir por el mismo modelo.
Las que esperan consumen su límite de tiempo y pueden terminar con «La consulta ha tardado
demasiado». El indexador y los embeddings de las búsquedas compiten además por la misma
máquina. No hay tiempos medidos que permitan cuantificarlo.

### Trabajo pendiente del plan elegido

1. **Prueba local con Codex: implementada el 18/11.** Puente de Windows, `gpt-reserve` con
   esfuerzo `low`, sin agente autónomo y con lecturas del backend existente.
2. **Búsqueda sin Ollama: resuelta para la prueba.** Usa búsqueda por palabras; la recuperación
   semántica con otro proveedor queda fuera de esta prueba.
3. **Evaluación local:** probar preguntas representativas, exactitud, fuentes, latencia y errores.
   Registrar qué se ha simulado; el resultado no valida por sí solo la integración con Copilot.
4. **Copilot definitivo:** acordar con IT la integración del agente con la API, autenticación,
   permisos y presentación al usuario. No trasladar Codex ni Ollama como solución de producción.
5. **Uso compartido:** definir usuarios simultáneos, cuotas, límites y esperas, y medirlos con
   Copilot. Las mediciones de Ollama o de la prueba local no acreditan su capacidad en producción.

**Demo en el visor (12/11/2026).** La pestaña Asistente del visor de `conocimiento/`
([README](../prototypes/data-explorer/conocimiento/asistente/README.md)) usa Claude Code con Haiku 5.5 y la suscripción
personal de Eduard. Es una demo distinta de la prueba con Codex acordada el 17/11 y no es la
integración final con Copilot. Puede servir de referencia para las lecturas con citas y la
continuidad entre preguntas. Los tiempos medidos allí son de Claude Code, no de Codex ni de esta app.

## Límites del módulo

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Integración de pantalla | `frontend/src/assistant/AssistantEntry.tsx` | Activación independiente de la página abierta |
| Chat | `AssistantWidget.tsx`, `useAssistant.ts` | Ventana, historial temporal, estados, cancelación |
| Transporte | `frontend/src/assistant/api.ts` | Sesión actual y lectura incremental NDJSON |
| API | `backend/app/assistant/router.py`, `schemas.py` | Autenticación, límites, contrato de eventos |
| Orquestación | `service.py` | Historial acotado, instrucciones y llamadas a herramientas |
| Redacción | `drafting.py` | Entrega textos recuperados al modelo sin nombres de herramientas ni detalles de implementación |
| Consulta inicial | `retrieval.py`, `tools.py` | Resolución de nombres/códigos, erratas leves, intención y ámbito de la pregunta actual |
| Modelo | `providers.py`, `config.py` | Contrato `ChatProvider` y adaptador Ollama |
| Conocimiento | `tools.py` | Lecturas permitidas y enlaces de procedencia |
| Estadísticas | `summaries.py` | Resúmenes de todas las mediciones filtradas, separados por serie, unidad y tolerancia |
| Respuestas factuales | `answers.py` | Presentación directa de mediciones calculadas y planes citados, sin reinterpretación del modelo |
| Evidencia de correcciones | `corrections.py` | Separación de cabecera, propuesta original, límites de cotas y estado de ejecución |
| Búsqueda híbrida | `corpus.py`, `semantic.py` | Textos actuales, filtros, BM25 y similitud coseno, combinación RRF |
| Embeddings | `embeddings.py`, `index.py`, `index_models.py` | Adaptador local independiente, actualización incremental y caché PostgreSQL |

Solo hay dos puntos de montaje fuera del módulo: `AssistantEntry` en el layout
autenticado y el router en `backend/app/api/main.py`. El widget se carga de forma
diferida y tiene una barrera de errores independiente. Reutiliza botones, campos y
texto enriquecido seguro de la app; no modifica los importadores o las pantallas.

Un proveedor futuro se incorpora tras `ChatProvider` o adaptando el servicio, sin
rehacer el widget ni las lecturas. Copilot Studio requerirá además su publicación,
autenticación, facturación y transporte propios; no está configurado todavía.

## Qué puede consultar

- `search_catalog`: el mismo buscador léxico de catálogo que utiliza la API.
- `search_knowledge`: búsqueda por palabras y significado en descripciones de
  features, notas de usuarios y texto de planes de retoque importados. Filtra por
  pieza, feature, revisión y cota. Devuelve hasta seis pasajes con su procedencia;
  es una selección por relevancia, no un inventario completo.
- `read_feature`: descripción, notas de usuarios, piezas y cotas vinculadas
  explícitamente a ese feature.
- `read_part`: cotas/features de una pieza, mediciones importadas con valores,
  tolerancias, estados y origen; texto de planes de corrección ya importado de PPTX.

Las lecturas usan los servicios/modelos existentes directamente dentro del backend;
no se hace un viaje HTTP del backend a sí mismo. Un código de pieza explícito en la
pregunta («pieza 3212») se consulta primero. Los nombres de piezas y features también
se resuelven antes de llamar al modelo, tolerando una errata leve en nombres largos
(«bold eye», «Pump Housng») y variantes de «corrección». Los códigos numéricos no se
aproximan. Un código explícito prevalece sobre nombres compartidos; si quedan varias
fichas posibles, se pide aclaración. Las comparaciones conservan la búsqueda con herramientas.

La pieza, feature, cota y revisión identificados en la pregunta actual se conservan
durante las consultas; una herramienta no puede sustituirlos por otra ficha del historial.
Las correcciones se leen de `read_part(section=corrections)`, comprobando los vínculos
explícitos del feature con la pieza y sus cotas. Una consulta sin cota pero con feature
se limita a las cotas vinculadas. Los resultados del catálogo priorizan coincidencias
de nombre/cota antes que descripciones y relaciones indirectas, antes de paginar.

El modelo recibe las descripciones, formatos y restricciones de los parámetros.
Las herramientas admiten nombres inequívocos de pieza como recuperación, y diferencian
errores de identificación de ausencia de datos. Hay hasta cinco llamadas de lectura y
cinco rondas sucesivas, más la redacción final, dentro del límite global de tiempo y contexto.
Los preámbulos de planificación no se publican. Si falla una lectura o falta consultar
las correcciones, se permite reintentar; una respuesta del modelo que cierre esa búsqueda
fallida como «no existe» se sustituye por una explicación de lo que no se pudo verificar.
Las lecturas completas de correcciones pasan directamente a redacción, sin arrastrar
respuestas anteriores ni resultados de descubrimiento que puedan cambiar el tema.
Estas comprobaciones verifican el ámbito y la recuperación, no cada afirmación semántica
del texto generado. Un plan sigue sin demostrar ejecución ni ausencia de ejecución.

### Fidelidad de los datos técnicos

La preparación y presentación factual se hacen en el servicio común, antes del
adaptador `ChatProvider`. No dependen del nombre, tamaño o fabricante del modelo,
no cambian sus pesos y no contienen excepciones para piezas, features, cotas o
acciones concretas. Un futuro proveedor que implemente ese contrato recibe los
mismos campos de evidencia y utiliza las mismas comprobaciones.

Las correcciones distinguen `action_id`, cabecera documental, cita de propuesta y
procedencia. La propuesta se separa solo cuando aparece una cabecera de sección
reconocida; en otros formatos se conserva el texto original sin inventar esa separación.
Los números del título no se convierten en especificaciones de herramientas.
`recorded_limits` recoge únicamente nominal y límites numéricos ya estructurados en
las mediciones de la revisión consultada. Mantiene separadas cotas, unidades y regímenes
de tolerancia, con sus series, cavidades, muestreos y documentos. Una ausencia de datos
no se rellena interpretando el título. `summary_offset` pagina estos grupos de ocho
en ocho y `coverage.recorded_limits` indica si falta información.

Las consultas directas de correcciones en español con una lectura completa se
presentan desde esos campos, tanto tras la consulta inicial como después de una
búsqueda con herramientas. Esta presentación utiliza la lectura completa antes del
recorte para el contexto del modelo, por lo que un estudio con muchas series no
pierde sus hechos por el tamaño de esa ventana. Incluyen la cita en su idioma original, la fuente y el
límite de lo que demuestra un plan. No se pide al modelo que reescriba la propuesta,
los números ni su significado. Se conserva el texto como una cita, sin ejecutar su
Markdown como instrucciones. Los planes recortados o leídos parcialmente no activan
esta vía. Los límites son contexto opcional para esta intención: si no están completos,
se omiten sin impedir la presentación fiel de los planes completos. Solo se consultan
límites de cotas vinculadas a las acciones recuperadas, no de toda la pieza sin relación.

Las explicaciones, comparaciones, traducciones, otros idiomas y preguntas sobre
ejecución mantienen el recorrido con el modelo, que recibe la evidencia separada.
Esto mejora la entrada de todos los modelos, pero no garantiza la exactitud de cada
interpretación libre. Las pruebas cubren piezas y acciones distintas, espesores,
ángulos y fuerzas, datos ausentes, paginación, fuentes y proveedores simulados que
no pueden intervenir en la redacción factual. No sustituyen una evaluación de las
respuestas abiertas del modelo elegido.

### Mediciones y paginación

Las mediciones incluyen un resumen del conjunto completo (cavidades, muestreos,
recuentos, tolerancias y documentos) y estadísticas por serie/unidad/tolerancia.
Por defecto no se envían filas individuales, para evitar que el modelo confunda
ejemplos parciales con el conjunto. `include_rows=true` o un filtro de cavidad y
muestreo devuelve hasta ocho filas con localizadores; `offset` permite continuar.
`summary_offset` pagina el índice de series y las estadísticas de veinte en veinte.
`include_statistics=true` añade mínimos/máximos/medias por serie cuando se solicitan.
Se transmiten con una cabecera de columnas compartida para reducir el contexto
repetido. Las consultas exactas resueltas con una lectura completa pasan
directamente a redacción, sin cargar otra ronda de planificación de herramientas.
Las consultas puramente numéricas en español sobre una pieza explícita se presentan
directamente desde el backend cuando la lectura está completa. Así el modelo no
confunde cavidades con recuentos, ni convierte límites asimétricos en tolerancias ±.
Las explicaciones, comparaciones, búsqueda de conocimiento y otras preguntas siguen
usando el modelo configurado. Los casos sin identificación suficiente conservan las herramientas.
Las notas se leen de veinte en veinte. `coverage` conserva el total, lo realmente
entregado y el siguiente desplazamiento, incluso cuando el presupuesto de contexto
recorta una lista. Los cuerpos de notas muy largos señalan su recorte.

### Índice semántico local

`EmbeddingGemma` genera vectores de 768 dimensiones mediante `/api/embed` de Ollama;
no sustituye al modelo de conversación ni activa thinking. Se indexan pasajes de
hasta 1200 caracteres con solapamiento, conservando las relaciones y fuentes.
El índice realiza búsqueda coseno exacta con pgvector, adecuada para el corpus
actual; no necesita un servidor vectorial adicional ni un índice aproximado HNSW.
La parte léxica aplica BM25 al texto vigente y ambas clasificaciones se combinan
con RRF. Las mediciones numéricas no se convierten en embeddings.

El trabajador se monta en el lifespan del router y revisa cambios cada 60 segundos,
en lotes pequeños. Solo recalcula textos/relaciones que han cambiado. Las consultas
revalidan la huella del texto actual: un embedding antiguo nunca recupera una nota
borrada o una versión anterior. Mientras se indexa o si falla Ollama, la búsqueda
léxica sigue disponible y las herramientas indican el estado de cobertura.
La caché no es fuente de verdad y puede reconstruirse con
`docker compose exec backend python -m app.assistant.index`.

Configuración: `ASSISTANT_SEMANTIC_ENABLED=true`,
`ASSISTANT_EMBEDDING_MODEL=embeddinggemma`, `ASSISTANT_EMBEDDING_DIMENSIONS=768`,
`ASSISTANT_SEMANTIC_MIN_SIMILARITY=0.24`,
`ASSISTANT_EMBEDDING_TIMEOUT_SECONDS=30`, `ASSISTANT_INDEX_INTERVAL_SECONDS=60`.
El umbral coseno es configurable y depende del modelo/corpus; no expresa una
probabilidad de que una respuesta sea correcta. Los tests incluyen paráfrasis con
embeddings sintéticos; la calidad del modelo real debe evaluarse sobre el corpus y
revisarse al cambiar de modelo.
Cambiar modelo o dimensiones invalida los vectores anteriores. Desactivar semántica
mantiene las consultas estructuradas y la búsqueda por texto. Desactivar todo el
asistente también detiene su indexador. No hay hooks en los editores/importadores.

Las fichas se buscan según la pregunta y el historial de conversación. La página
abierta, su pieza/feature y sus filtros no se envían ni condicionan la consulta.
Una revisión pedida explícitamente prevalece; si se omite, la lectura utiliza la
última disponible según la ordenación de revisiones del servicio; esto no certifica
que sea la versión entregada o aprobada. No se mezclan revisiones ni se atribuyen todas las cotas de una
pieza a cada feature.

El único Markdown del repositorio que el backend incorpora al contexto es el glosario
empaquetado con la aplicación. Las notas de usuarios de la BD también forman
parte del conocimiento, aunque su cuerpo use Markdown. Solo hay acceso al contenido
que los importadores ya han extraído: no se interpreta geometría STEP, imágenes de
PPTX, PDFs completos ni nubes TXT. Un plan de retoque no demuestra su ejecución.

## Acceso y protocolo

Ambos endpoints requieren la sesión habitual de la app:

- `GET /api/v1/assistant/status`: activación y modelo configurado, sin cargarlo.
- `POST /api/v1/assistant/chat`: `messages` (roles user/assistant).
  Devuelve `application/x-ndjson`: eventos `status`, `delta`, `sources`, `done` o
  `error`. Un stream sin `done` no se considera una respuesta completa.

El cliente generado describe la API. El adaptador de chat usa `fetch` porque el
cliente Axios generado no entrega el stream progresivamente en el navegador.
Las respuestas canceladas o fallidas no se reenvían como historial válido.

El backend valida parámetros y solo permite cuatro herramientas de lectura. Cada
consulta abre una transacción PostgreSQL `READ ONLY` con timeout y vuelve a
comprobar que el usuario esté activo. El conocimiento es compartido entre usuarios
autenticados, igual que las APIs actuales; no se exponen cuentas, contraseñas o SQL.
Si se añaden permisos por pieza/feature, deben aplicarse también en esta frontera
de lectura y al corpus semántico. No se otorga al modelo una conexión libre a la base de datos.
El trabajador de indexación escribe únicamente su caché derivada en otra transacción;
las herramientas del chat continúan siendo de solo lectura.

Los enlaces de fuentes se construyen en el backend. El navegador solo permite
rutas internas de piezas/features, abiertas en otra pestaña; no ejecuta HTML ni
enlaces que escriba el modelo. Las fuentes identifican lo consultado, no validan
automáticamente cada afirmación de un modelo pequeño.

## Verificación

Los archivos `backend/tests/api/routes/test_assistant*.py` y
`frontend/tests/components/assistant.test.cjs` contienen los casos siguientes.
Se han inspeccionado como evidencia de cobertura prevista; no se han ejecutado en
esta revisión del 26/10/2026.

`scripts/test.ps1 -k assistant` usa una BD aislada. Incluye autenticación,
desactivación, validación, transacciones de solo lectura, revisiones, pertenencia de
cotas, consultas reales de datos sintéticos y el contrato de Ollama sin thinking.
También cubre agregados completos frente a páginas parciales, diez notas, búsqueda
vectorial real con embeddings sintéticos, filtros, caché incremental, edición/borrado
y caída del proveedor semántico. No necesita Ollama para las pruebas automáticas.

`node --test frontend/tests/components/assistant.test.cjs` verifica streaming UTF-8,
fuentes, minimizar/reabrir, navegación sin enviar contexto de pantalla, detener,
reiniciar y errores.
Los tests automáticos existentes no dependen del modelo ni de los datos de trabajo. El 18/11
se añadieron las comprobaciones del proveedor y puente Codex. Hay que evaluar por separado
la calidad de las respuestas locales y las de Copilot en la integración final. La prueba futura de
`conocimiento/` en una sesión nueva de desarrollo es otra tarea, recogida en
[Próximos pasos](proximos-pasos.md). El rechazo de llamadas simultáneas y la cancelación del
puente local están probados; siguen pendientes las mediciones de capacidad de Copilot.
