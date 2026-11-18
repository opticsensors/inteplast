# Prueba local del asistente con Codex

Implementación preparada y probada el **18/11/2026** en una copia aislada; integrada después
de terminar A–E por indicación de Eduard. Se configura mediante el `.env` privado y el
Compose habitual, sin necesitar el Compose adicional. No hay modificaciones del frontend,
de las migraciones, del esquema público del chat ni de los importadores.

La solución definitiva sigue siendo **Copilot**. Este puente permite probar Codex como motor
de fondo en el PC de Eduard, reutilizando el chat de la app y sus consultas de solo lectura.

## Funcionamiento

1. El chat llama al mismo `POST /api/v1/assistant/chat`, con la misma autenticación.
2. `service.py` conserva las búsquedas, las comprobaciones de datos, las fuentes y los límites
   existentes. El nuevo `CodexProvider` envía mensajes y definiciones de lecturas al puente.
3. El puente se ejecuta en Windows y llama a `codex exec` mediante entrada/salida JSON.
   Usa la autenticación ya guardada de Codex, sin copiarla al contenedor ni a la app.
4. Codex devuelve una respuesta o una solicitud de lectura estructurada. El puente **no
   ejecuta esas lecturas**: el backend valida los parámetros y las realiza con el usuario
   autenticado, como antes. Solo admite `search_catalog`, `search_knowledge`, `read_part`
   y `read_feature`. No se añaden endpoints de datos ni un agente autónomo.
5. El backend entrega los mismos eventos `status`, `delta`, `sources`, `done` o `error` al
   frontend. Las respuestas factuales que ya se calculaban sin modelo siguen ese camino.

Esto simula la interacción del futuro agente con los datos de la app. Las lecturas siguen
siendo funciones internas del backend; **no valida todavía una API de herramientas HTTP para
Copilot**. La comunicación backend–puente sí se ha probado por HTTP desde Docker a Windows.

## Diferencias acotadas de la prueba

- **Sin Ollama:** con `ASSISTANT_PROVIDER=codex` se desactiva la búsqueda semántica y su
  indexador, aunque se herede `ASSISTANT_SEMANTIC_ENABLED=true`. Se conserva la búsqueda
  por palabras. La calidad de recuperación por significado queda fuera de esta prueba.
- Cada llamada al modelo es efímera y recibe el historial acotado del backend. No comparte
  conversación ni daemon con las sesiones de desarrollo de Codex. Puede haber varias
  llamadas por pregunta si hay que consultar más datos.
- El puente espera el JSON completo y confirmado antes de devolver el texto o las lecturas.
  **El texto llega completo, no token a token.** La ventana, las fuentes y los controles del
  frontend no cambian; los estados de búsqueda del backend se siguen enviando.
- Una solicitud al modelo a la vez para todo el puente. Otra recibe «ocupado». Una
  desconexión o un tiempo agotado termina el proceso de esa solicitud, incluidos sus hijos.
- Codex se inicia con configuración de usuario ignorada, directorio temporal vacío, sandbox
  de solo lectura, instrucciones específicas y capacidades de shell, apps, plugins, hooks,
  navegador, ordenador, imágenes y multiagente desactivadas. Las lecturas se representan
  como datos JSON; no se le da acceso al repositorio ni a la base de datos.
- El servicio usa un token privado, rechaza peticiones del navegador con `Origin`, limita el
  tamaño de entrada/salida y no devuelve diagnósticos de la CLI, prompts ni credenciales a la GUI.

## Preparación y arranque local

Requisitos: Node.js y Codex CLI con sesión iniciada en Windows. Comprobado con Codex CLI
`0.169.0`. La prueba usa el modo no interactivo documentado por OpenAI:
[Codex no interactivo](https://learn.chatgpt.com/docs/non-interactive-mode).

Desde una terminal PowerShell:

```powershell
.\integrations\codex-bridge\start.ps1
# O sin ventana, con registros en la carpeta privada:
.\integrations\codex-bridge\start.ps1 -Background
```

El lanzador crea una clave privada en `%LOCALAPPDATA%/INTEPLAST/codex-bridge/bridge.token`
si no existe, y arranca el puente en `127.0.0.1:11435`. No modifica el `.env` de la aplicación.
En primer plano se detiene con Ctrl+C. En segundo plano guarda `bridge.pid`, `bridge.log`
y `bridge-error.log` en la misma carpeta privada. No instala un servicio ni una tarea de
inicio automático: tras reiniciar Windows hay que arrancar de nuevo el puente.
`-Model`, `-Effort`, `-Port` y `-StateDirectory` permiten cambiar
la configuración de esta prueba sin modificar la de las sesiones de desarrollo de Codex.

Configuración de la instalación local en `.env`, conservando sus otros valores:

```dotenv
ASSISTANT_ENABLED=true
ASSISTANT_PROVIDER=codex
ASSISTANT_MODEL=gpt-reserve
ASSISTANT_CODEX_BRIDGE_URL=http://host.docker.internal:11435
ASSISTANT_CODEX_BRIDGE_TOKEN=<contenido del archivo privado bridge.token>
ASSISTANT_SEMANTIC_ENABLED=false
```

`compose.yml` transmite estos valores al backend. Reconstruir únicamente ese servicio:

```powershell
docker compose up -d --no-deps --build backend
```

El token se exige al habilitar Codex; con el asistente desactivado no es necesario y no
se inicia Ollama. La configuración de sesión/modelo de las otras sesiones de Codex no cambia.

Como alternativa para otras pruebas, `compose.codex.yml` puede añadirse al final de los
archivos Compose habituales y recibe estas variables:

| Variable | Valor |
|---|---|
| `CODEX_BRIDGE_TOKEN` | Contenido del archivo privado; no escribirlo en Git ni en el chat. |
| `CODEX_BRIDGE_MODEL` | Mismo modelo que el puente; por defecto `gpt-reserve`. |
| `CODEX_BRIDGE_URL` | `http://host.docker.internal:11435` desde Docker Desktop. |

No necesita frontend nuevo, cambios en la BD ni migraciones. El Compose adicional es
opcional y no se ha añadido a la instalación de Eduard.

## Verificación del 18/11/2026

- **8 pruebas del puente**: autenticación, rechazo de accesos desde navegador, contrato de
  lecturas, respuestas inválidas, concurrencia, cancelación y formato NDJSON.
- **16 pruebas del adaptador Python**: contrato HTTP, token, respuestas incompletas,
  llamadas no permitidas, errores, configuración desactivada sin credenciales y ausencia
  de dependencia de embeddings de Ollama.
- **59 pruebas del asistente** con PostgreSQL temporal `codex_poc_test`, incluida una nueva
  prueba del recorrido por la ruta autenticada del chat, con notas y fuentes.
- Ruff y mypy correctos en los módulos de backend modificados.
- **Codex real, datos sintéticos:** lectura directa con `gpt-6.2-sol` en 6,43 s,
  `gpt-6.1-terra` en 5,44 s y `gpt-reserve` en 5,14 s. Se eligió `gpt-reserve` con esfuerzo
  `low` para esta prueba por el menor tiempo observado. Una muestra por modelo no demuestra
  que sea siempre el más rápido; todos estaban disponibles en la CLI de este PC.
- **Dos lecturas simuladas y respuesta:** `search_catalog` → `read_feature` → respuesta,
  con Codex real, en 15,88 s. El identificador utilizado salió del resultado simulado.
- **Recorrido completo con datos de una BD de prueba:** login de prueba → ruta real del chat
  → lectura de una nota sintética → puente HTTP desde Docker → Codex real → respuesta con
  una fuente, en **7,03 s**. Se recibió el mismo contrato de eventos del frontend.
- **Cancelación de Codex real:** interrupción a los 500 ms, proceso finalizado y directorio
  temporal vacío en 1,83 s en total. Sintaxis del lanzador PowerShell comprobada.
- **Instalación local tras integrar A–E:** backend reconstruido y saludable; consulta HTTP
  al chat desplegado sobre advertencias de una ficha existente, con Codex real, respuesta y
  una fuente en **17,07 s**. Solo lecturas, sin crear ni modificar fichas. Se usó un token
  técnico de dos minutos para una cuenta existente; no es una nueva validación del login
  Microsoft. Puente activo en segundo plano; pila de tests retirada.

Las 83 pruebas se repitieron sobre el árbol actual al integrar A–E, con PostgreSQL temporal;
Ruff y mypy también correctos. Los tiempos se identifican arriba como pruebas sintéticas
o consulta real; no validan la ingesta automática de piezas,
la calidad sobre los originales de INTEPLAST ni la integración final con Copilot.

Comandos de pruebas unitarias desde la raíz de la copia:

```powershell
node --test integrations/codex-bridge/bridge.test.mjs
```

Para Python, con el entorno del backend y su directorio en `PYTHONPATH`:

```text
pytest tests/assistant_provider --confcutdir=tests/assistant_provider -q
```

Las pruebas de rutas se ejecutan exclusivamente en la pila aislada del repositorio;
nunca contra la BD de trabajo. Las copias privadas de la integración están en
`~/.codex/workspaces/inteplast-codex-integration-20261118`, fuera de Git.
