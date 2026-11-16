# Asistente del visor (demo, 12/11/2026)

Pestaña **Asistente** del visor de `conocimiento/`: un chat mínimo con **Claude Haiku 5.5** que responde solo con lo que
hay en `conocimiento/` (fichas, hallazgos, biblioteca extraída de Exemples) y `docs/`, y enseña sus pasos y sus fuentes.

**Para qué (Eduard, 12/11/2026):** una demo que lleva y maneja Eduard en su portátil, con un usuario a la vez, para
enseñar lo rápido y lo listo que puede ser un asistente con solo ese contexto. **No es el asistente de la aplicación
final** (ver [docs/asistente.md](../../../../docs/asistente.md)).

## Cómo funciona

- **Claude Code por debajo, con la suscripción de quien lo ejecuta.** No hay clave de API ni coste por pregunta: gasta
  de la cuota de la suscripción. Por eso es **solo para uso personal en este equipo**: ni servidor compartido ni
  acceso de otras personas desde sus equipos. Para eso haría falta la API de pago (o el asistente de empresa).
- **Un proceso vivo por conversación** (`claude -p` con entrada y salida `stream-json`). Se arranca al abrir la pestaña,
  sin gastar nada, y cada pregunta se le escribe por la entrada: recuerda lo anterior y no paga el arranque.
  «Nueva conversación» lo cierra y empieza otro; «Parar» corta la respuesta y la siguiente pregunta reanuda la misma
  conversación (`--resume`).
- **Las funciones de `rag.py` como herramientas propias** (`herramientas_mcp.py`, servidor MCP por stdio, sin
  dependencias): `buscar`, `ver`, `medidas`, `cadena`, `hallazgo`, `celdas` y `sql`, todas de solo lectura. Además
  tiene Read, Grep y Glob sobre `conocimiento/` y `docs/`.
- **Las mismas reglas que un agente con `rag.py`**: buscar, citar ruta y localizador, y sacar las cifras de las
  herramientas exactas. Están en [instrucciones.md](instrucciones.md), que se añade al prompt de sistema.

### Encierro (comprobado el 12/11/2026, Claude Code 2.1.322)

| Intento | Resultado |
|---|---|
| Read de `docs/app-web.md` / de `conocimiento/…` | ✅ permitido |
| Read de `backend/app/main.py`, Grep en `backend/` | ❌ «is outside … conocimiento, … docs» (`--restricted`) |
| Bash (`ls ..`, `cat ../CLAUDE.md`, comandos encadenados) | ❌ sin Bash, PowerShell ni edición (`--tools Read,Grep,Glob`) |
| CLAUDE.md del repo y memoria del usuario | no se cargan (`memory_paths: None`; variables de entorno en `sesion.Config`) |
| Ajustes, hooks y MCP del usuario | no se cargan (`--restricted`, `--strict-mcp-config`) |

Lo que pediría permiso se deniega solo (`--permission-prompts none`). `--safe-mode` no se usa porque también desactiva
el servidor MCP propio; `--bare` tampoco, porque exige clave de API.

### Por qué un servidor MCP y no `rag.py` por consola

Medido el 12/11/2026 en este equipo:

| Cómo | Tiempo por búsqueda |
|---|---|
| `rag.py buscar` por la consola Bash del asistente | 30–150 s (unos 30 s antes de arrancar el comando, y el modelo de Ollama en frío) |
| `rag.py buscar` desde PowerShell | 4 s |
| `rag.buscar()` dentro de un proceso que ya lo tiene cargado (el MCP) | **0,5–0,8 s**; `cadena`, 0,04 s |

### Tiempos de la demo (12/11/2026, Haiku 5.5)

- Proceso preparado al abrir la pestaña: primera pregunta con 2 pasos → primer texto a los 5 s, completa en 8,9 s.
- Pregunta con 5 pasos (Bolt Eye del 3212): 17 s. Pregunta de seguimiento en la misma conversación: 2–10 s.
- Sin preparar, la primera pregunta paga unos 5 s más de arranque.

Son tiempos de Claude Code con Haiku en este portátil: **no son los de la aplicación final**, que tendría otro modelo
y otra forma de llamarlo.

## Requisitos

- Claude Code instalado (`claude` en el PATH o en `~/.local/bin`) y con la sesión iniciada.
- `conocimiento/.venv` y el índice del RAG (`rag.py construir`), como para usar `rag.py`.
- Ollama en marcha con `embeddinggemma` para la parte semántica; sin él, `buscar` va en modo léxico y lo avisa.
- Internet: Claude Code llama al modelo de Anthropic. **Lo que lee el asistente sale del equipo** hacia Anthropic, igual
  que al usar Claude Code en el repo.

## Reutilizar o quitar

El módulo es autocontenido; el visor solo tiene tres enganches:

| Dónde | Qué |
|---|---|
| `app.py` | `import asistente` + `asistente.instalar(app)` |
| `static/index.html` | `<script src="/asistente/asistente.js"></script>` (antes de `app.js`) |
| `static/app.js` | `window.vistasExtra?.[tab]` en `render()`: genérico, puede quedarse |

- **Quitarlo:** borrar esta carpeta y las líneas de `app.py` e `index.html`.
- **En otra app FastAPI:** `asistente.instalar(app)` y el `<script>`. La pestaña se añade sola al menú
  (`header nav`) o se monta en cualquier elemento con `montarAsistente(elemento)`.
- **Sin web:** `from asistente.sesion import SesionClaude, Config`. `preguntar(texto)` devuelve eventos simples
  (`paso`, `resultado_paso`, `texto`, `fin`, `error`). `Config` cambia modelo, carpetas, herramientas o instrucciones.

| Fichero | Qué hace |
|---|---|
| `sesion.py` | Proceso de Claude Code, permisos y traducción de eventos (sin FastAPI) |
| `herramientas_mcp.py` | Servidor MCP con las funciones de `rag.py` |
| `rutas.py` | `/api/asistente/{estado,preparar,preguntar,parar,nueva}` (respuesta en NDJSON) e `instalar()` |
| `instrucciones.md` | Prompt de sistema añadido |
| `static/asistente.js`, `static/asistente.css` | Interfaz: chat, pasos con tiempos, respuesta en Markdown escapado |

## Límites

- Una conversación para todo el servidor y una pregunta a la vez (409 si hay otra en curso).
- «Solo con estas fuentes» lo garantiza el encierro en cuanto a lo que **lee**. Que no añada nada de su conocimiento
  general se pide en las instrucciones y se comprueba con las citas: antes de enseñarla, ensayar las preguntas y
  auditar sus respuestas contra la fuente.
- Si el visor se cierra de golpe (sin Ctrl+C), el proceso de Claude termina solo al perder su entrada.
