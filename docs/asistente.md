# Asistente local de consulta

El chat opcional usa Ollama en el PC del servidor y el modelo `qwen3.5:2b` con
`think: false`. Muestra texto progresivamente, admite detener/reintentar y conserva
la conversación al navegar dentro de la app. Se abre abajo a la derecha y se
minimiza a su cabecera. Cerrar no borra el historial; «Nueva conversación», salir de
la sesión o recargar sí. El historial solo vive en memoria del navegador.

## Arranque

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
las simultáneas reciben un aviso para reintentar, sin acumular cola.
Las respuestas largas se conservan completas en pantalla; solo se abrevia su copia
enviada como historial, manteniendo la pregunta anterior y sus identificadores.

## Límites del módulo

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Integración de pantalla | `frontend/src/assistant/AssistantEntry.tsx` | Activación independiente de la página abierta |
| Chat | `AssistantWidget.tsx`, `useAssistant.ts` | Ventana, historial temporal, estados, cancelación |
| Transporte | `frontend/src/assistant/api.ts` | Sesión actual y lectura incremental NDJSON |
| API | `backend/app/assistant/router.py`, `schemas.py` | Autenticación, límites, contrato de eventos |
| Orquestación | `service.py` | Historial acotado, instrucciones y llamadas a herramientas |
| Redacción | `drafting.py` | Entrega textos recuperados al modelo sin nombres de herramientas ni detalles de implementación |
| Consulta inicial | `retrieval.py` | Lectura del código de pieza explícito en la pregunta |
| Modelo | `providers.py`, `config.py` | Contrato `ChatProvider` y adaptador Ollama |
| Conocimiento | `tools.py` | Lecturas permitidas y enlaces de procedencia |
| Estadísticas | `summaries.py` | Resúmenes de todas las mediciones filtradas, separados por serie, unidad y tolerancia |
| Respuesta numérica | `answers.py` | Presentación directa de hechos calculados para consultas exactas, sin reinterpretación del modelo |
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
pregunta («pieza 3212») se consulta primero. Un nombre de feature inequívoco también
se resuelve antes de llamar al modelo. El modelo decide las demás herramientas.
Las mediciones incluyen un resumen del conjunto completo (cavidades, muestreos,
recuentos, tolerancias y documentos) y estadísticas por serie/unidad/tolerancia.
Por defecto no se envían filas individuales, para evitar que el modelo confunda
ejemplos parciales con el conjunto. `include_rows=true` o un filtro de cavidad y
muestreo devuelve hasta ocho filas con localizadores; `offset` permite continuar.
`summary_offset` pagina estadísticas.
`include_statistics=true` añade mínimos/máximos/medias por serie cuando se solicitan.
Se transmiten con una cabecera de columnas compartida para reducir el contexto
repetido. Las consultas exactas resueltas con una lectura completa pasan
directamente a redacción, sin cargar otra ronda de planificación de herramientas.
Las consultas puramente numéricas en español sobre una pieza explícita se presentan
directamente desde el backend cuando la lectura está completa. Así el modelo no
confunde cavidades con recuentos, ni convierte límites asimétricos en tolerancias ±.
Las explicaciones, comparaciones, búsqueda de conocimiento y otras preguntas siguen
usando Qwen. Los casos sin identificación suficiente conservan las herramientas.
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
probabilidad de que una respuesta sea correcta. Se comprobó con paráfrasis del
conocimiento piloto y debe revisarse al cambiar de modelo.
Cambiar modelo o dimensiones invalida los vectores anteriores. Desactivar semántica
mantiene las consultas estructuradas y la búsqueda por texto. Desactivar todo el
asistente también detiene su indexador. No hay hooks en los editores/importadores.

Las fichas se buscan según la pregunta y el historial de conversación. La página
abierta, su pieza/feature y sus filtros no se envían ni condicionan la consulta.
Una revisión pedida explícitamente prevalece; si se omite, la lectura utiliza la
última disponible. No se mezclan revisiones ni se atribuyen todas las cotas de una
pieza a cada feature.

No se leen los Markdown del repositorio, README, código, notas de desarrollo,
archivos originales ni rutas arbitrarias. Las notas de usuarios de la BD sí forman
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

`scripts/test.ps1 -k assistant` usa una BD aislada. Incluye autenticación,
desactivación, validación, transacciones de solo lectura, revisiones, pertenencia de
cotas, consultas reales de datos sintéticos y el contrato de Ollama sin thinking.
También cubre agregados completos frente a páginas parciales, diez notas, búsqueda
vectorial real con embeddings sintéticos, filtros, caché incremental, edición/borrado
y caída del proveedor semántico. No necesita Ollama para las pruebas automáticas.

`node --test frontend/tests/components/assistant.test.cjs` verifica streaming UTF-8,
fuentes, minimizar/reabrir, navegación sin enviar contexto de pantalla, detener,
reiniciar y errores.
La conexión real a Ollama se comprueba por separado con consultas de solo lectura;
los tests automáticos no dependen del modelo ni de los datos de trabajo.
