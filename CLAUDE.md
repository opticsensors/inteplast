# INTEPLAST — contexto del proyecto

## Qué es este repo

**El repo de INTEPLAST: código + conocimiento del proyecto**
(`github.com/opticsensors/inteplast`). Aquí vive todo lo del proyecto salvo los datos crudos del
cliente y las notas de Obsidian (ver rutas abajo).

| Carpeta | Qué es |
|---|---|
| `backend/` `frontend/` | La **aplicación** (FastAPI + React, sobre el template `full-stack-fastapi-template`). → [docs/app-web.md](docs/app-web.md) |
| `scripts/` | Lanzadores de **Compose, build y tests**. ⚠️ Nada que ver con los visores de datos |
| `prototypes/data-explorer/` | 📊 Los **visores de los datos crudos** (Python): `metrologia/` (CMM) y `planos/` (el plano 2D). → [conocimiento/visores.md](conocimiento/visores.md) |
| `conocimiento/` | 🔑 **Todo lo que sabemos de los datos de Exemples**: fichas por feature y pieza, comparativa, incongruencias, hallazgos y la biblioteca SQLite consultable (fuera de Git). No es parte de la app. → [conocimiento/README.md](conocimiento/README.md) |
| `docs/` | Documentación de la **aplicación**: modelo, API, interfaz, despliegue, hoja de ruta, preguntas abiertas |
| `compose*.yml` `deployment.md` `development.md` | Docker y despliegue |

> `docs/` y este `CLAUDE.md` vivían hasta el **2026-08-14** en un vault de Obsidian
> (`C:\edu\projects\Inteplast`). Se movieron aquí. En el vault se quedan las notas originales
> `inteplast_*.md` y sus imágenes (`_/`): los documentos las citan por nombre y se leen por ruta
> absoluta desde ahí. **No escribir nunca en `C:\edu`.** El 2026-10-21 el análisis de los datos
> pasó de `docs/` a `conocimiento/`.

## Objetivo del proyecto

El proyecto tiene **tres etapas**, aclaradas por Eduard el 22/09/2026:

1. **Transferencia de conocimiento mediante una GUI (actual):** facilitar que los trabajadores
   compartan y consulten la experiencia de diseño de piezas inyectadas.
2. **Reutilización de features en SolidWorks (futura):** extraer o crear features, insertarlos
   o arrastrarlos sobre otra pieza y modificarlos, con adaptación automática a la geometría
   cuando sea viable y con reglas de diseño por definir y validar.
3. **Predicción de contracciones (futura):** utilizar los resultados históricos de las piezas
   inyectadas para desarrollar predicciones; datos, método y validación por concretar.

Alcance y antecedentes en [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md).

La primera etapa se materializa en una **base de datos interactiva de conocimiento**.
El usuario introduce el **ID de un feature** (p. ej. *Bolt Eye*) y el sistema devuelve:
**warnings** (qué vigilar al diseñarlo), **lessons learned** (qué se hizo en el molde cuando
salió mal), **cotas**, y **piezas/moldes de referencia** con sus CAD descargables.

Cliente final: **Robert Bosch** (división BueP). Informes en formato **PPAP / QS9000-TS**.

## Rutas

| Qué | Ruta |
|---|---|
| **Este repo** (código + docs) | `C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast` |
| 📊 **Visores** de los datos | `…\repos\inteplast\prototypes\data-explorer` *(dentro de este repo)* |
| 🔴 **Datos** de INTEPLAST | `C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples` |
| 🔴 **Bolt Eye** (2820, 3051, 3197, **3212**) | `…\Exemples\0- Bolt Eye` *(la raíz de `.env` es `Exemples` desde el 2026-10-22)* |
| 🔴 **Notas** de Obsidian | `C:\edu\projects\Inteplast` *(vault en `C:\edu`)* |

> 🆕 **Desde el 2026-10-21 `Exemples` se organiza por feature**: `0- Bolt Eye` (las cuatro piezas
> de siempre, movidas sin cambios), `1- Clips en Piezas` … `7- Planitudes`, cada una con sus piezas.
> Las entregas nuevas usan otro esqueleto de 7 carpetas (`1- 2D y 3D pieza` … `7- Pieza real STL`)
> y una pieza puede aparecer en varios features: la carpeta duplicada solo trae un `Readme.txt`
> que remite a la otra. Leídos todos el 2026-10-21: ver [conocimiento/comparativa.md](conocimiento/comparativa.md).
>
> 🔴 **Los datos crudos del cliente NO se copian al repo** — se leen in situ desde `Exemples`
> (rutas absolutas en la cabecera de cada script de `prototypes/data-explorer/`). Son gigas, están en
> OneDrive Files On-Demand y no son nuestros.
>
> ⚠️ Un script nuevo **de exploración de datos** va a `prototypes/data-explorer/` (visores) o a
> `conocimiento/herramientas/` (biblioteca), **no** a `scripts/` (build y test del template). Se
> documenta en `conocimiento/`.

> **Separación de producto:** `prototypes/` es solo exploración. La aplicación no debe
> importar, ejecutar ni copiar sus scripts. Los lectores de la web se implementan y
> mantienen en `backend/app/ingestion/`, tomando los prototipos como referencia cuando
> sea útil. La imagen Docker excluye `prototypes/` por completo.

## Foco actual

**La app sigue con el piloto `3212 Pump Housing`** (Bolt Eye): adaptador de correcciones,
previsiones y casos revisados solo para él. El cierre y la posible existencia de retoques
posteriores siguen pendientes de confirmar.

**Los datos de los 8 features de Exemples ya están leídos** (2026-10-21) y documentados en
`conocimiento/`, con la biblioteca consultable. Antes de generalizar la app a otras piezas, partir
de [conocimiento/comparativa.md](conocimiento/comparativa.md).

---

## La aplicación — lo que ya está construido

Sobre la plantilla de FastAPI está implementada la **base de conocimiento de features**: fichas de
feature con **warnings**, **lessons learned**, **piezas ejemplo** con sus cotas, y buscador global.
Es el bloque transversal de [docs/modelo-datos.md](docs/modelo-datos.md).

🔑 **Los ficheros pertenecen a la PIEZA, no al feature** (desde el 2026-09-22). La tabla `Part`
(código `3212` + nombre) es el embrión del `PROYECTO`. Los archivos (molde, CAD, escaneo, plano 2D,
Moldflow…) se consultan y editan en la **ficha de pieza** `/parts/{id}`, sección Archivos
(`Parts/PartFiles.tsx`). La ficha del feature enseña **un desplegable por pieza con sus cotas**
(fila COTAS) y el enlace «Ver pieza», sin listar documentos (`Features/PartAssetList.tsx`).
Al vincular una pieza se copian sus archivos principales como adjuntos del feature, sin mostrarlos:
los usan la portada CAD y el acceso al plano desde las cotas, y no siguen los cambios posteriores
de la pieza ([limitación](docs/portadas-cad.md#origen-del-cad-de-la-portada)).
Un feature puede además estar **declarado** en una pieza sin tener ningún fichero subido todavía
(`FeaturePartLink`, embrión de `INSTANCIA_EN_PROYECTO`).

Desde el **2026-09-18** existe ingesta piloto del 3212 (snapshots de CSV/XLS/PPTX), cotas por
pieza/revisión, ficha de pieza y buscador PDF con revisiones compartidas. El modelo completo
normalizado de mediciones y ejecución de correcciones sigue pendiente. Ver
[docs/cotas-y-evidencia-web.md](docs/cotas-y-evidencia-web.md).

```powershell
docker compose up -d --build db prestart backend   # backend + BD (aplica migraciones)
cd frontend; npm run dev                           # http://localhost:5173
docker compose exec backend python -m app.seed_features   # carga de ejemplo: Bolt Eye del 3212
```

- 🔑 **Antes de tocar `backend/` o `frontend/`, leer [docs/app-web.md](docs/app-web.md)**: modelo,
  endpoints, permisos, decisiones y cabos sueltos.
- **Antes de diseñar o modificar una pantalla, leer [docs/interfaz.md](docs/interfaz.md)**.
  Features es la referencia visual. Reutilizar buscador, controles y composición;
  no inventar un diseño distinto por página ni añadir botones de retorno.
- 🔴 **Tras tocar `backend/`, reconstruir con `--build` o mantener `docker compose watch backend`
  activo.** `up -d` por sí solo reutiliza la imagen y no sincroniza el código local. Alembic
  `current` comprueba la revisión de la BD, **no** que el código de los endpoints esté actualizado.
- ⚠️ **Cambiar un endpoint o un modelo obliga a regenerar el cliente TypeScript**
  (`bash scripts/generate-client.sh`), o el frontend se queda desincronizado.
- La página `/items` es la demo de la plantilla: ya no está en el menú, pero el `Item` sigue en el
  código. El inicio y catálogo único es `/features` (`/` redirige conservando la búsqueda),
  con tarjetas de consulta y acceso directo a editar. La **ficha del feature es `/features/{id}`**
  — desde el 2026-08-19 es una página con URL propia, no una modal.
- **Subidas persistentes:** el Dockerfile fija `UPLOADS_DIR=/app/uploads`, que coincide con el
  volumen. Antes de recrear un contenedor anterior a la corrección, comprobar y rescatar los
  posibles bytes de `/app/backend/uploads` (ver [deployment.md](deployment.md)).
- **Acceso:** altas desde Admin por defecto; el UUID de un fichero ya no es un permiso de
  lectura. El frontend obtiene enlaces firmados temporales con autenticación.
- **Revisión del 2026-09-15:** cambios y pruebas en [docs/revision-2026-09-15.md](docs/revision-2026-09-15.md).
- **Archivos externos (2026-09-15):** el PDF y el STEP del 3212 están vinculados y comprobados
  en la instalación local. `StoredFile.id` identifica tanto subidas como referencias; el
  adaptador local lee originales sin copiarlos, con montaje Docker de solo lectura.
  `.env` contiene toda la configuración personal y queda fuera de Git; `.env.example` es la
  plantilla versionada. `docker compose` carga el origen directamente, sin lanzadores ni
  variables manuales en la terminal. No sobrescribir el `.env` de una instalación. Graph, revisiones
  históricas de originales e ingesta para otras piezas siguen pendientes. Escaneo y molde grandes usan GLB automáticos en
  caché; ver [docs/vistas-3d.md](docs/vistas-3d.md) y [docs/ficheros-externos.md](docs/ficheros-externos.md).
  **La pregunta A10 sobre acceso a originales es prioridad 1 de la reunión con INTEPLAST.**
- **SharePoint (2026-10-22):** `SHAREPOINT_ENABLED=true` en `.env` lee el mismo `Exemples` por
  Microsoft Graph en vez de la carpeta local, con las mismas rutas y la misma BD; cada usuario
  entra con su cuenta de Microsoft (MSAL, login delegado). `false` deja todo como en local.
  Implementado y probado con Graph simulado; **falta la primera prueba real**. Detalle y
  activación en [docs/ficheros-externos.md](docs/ficheros-externos.md#sharepoint-microsoft-graph).
- **Portadas CAD:** pulsar la cabecera abre la ampliación de imagen/3D; en edición abre una
  modal para pegar/arrastrar/elegir imágenes o crear una portada desde el STEP vinculado de
  la pieza, con caras rojas y encuadre guardados. `Feature.cover_3d`
  se liga a los bytes y la receta de importación; no reutilizar índices de caras entre
  revisiones. Detalles en [docs/portadas-cad.md](docs/portadas-cad.md).

---

## Modelo mental del dominio (leer esto antes de nada)

1. **PROYECTO = una pieza inyectada + su molde.** Se identifica con un número de 4 dígitos
   (`3212`) que prefija casi todos los ficheros.
2. **N-number** (`N170`, `N117`, `N178`…) = número de característica del plano 2D del cliente.
   **Es la clave que une el plano, la metrología, la CMM y los retoques de molde.** Es el
   *join key* natural de la base de datos.
3. **`intern.NN` = muestreo** (tirada de control). `intern.01`, `intern.02`… La secuencia es la
   **historia de maduración del molde**: se mide, se retoca el molde, se vuelve a medir.
4. **Corrección de molde** = reunión donde se decide qué retocar. Sale un PPTX con una
   diapositiva por cota: *situación actual → acción en mm sobre zona marcada en rojo*.
   **Esto es la "lesson learned" que pide INTEPLAST, ya existe, no hay que inventarla.**
5. **Un FEATURE agrupa varios N-numbers.** El *Bolt Eye* del 3212 = `N170` (Ø4−0,1) +
   `N117` (posición ⌖0,15) + `N178` (planitud del plano A, warning indirecto).
6. El mismo feature en otra pieza lleva **otras tolerancias** (3197: Ø4 **+0,1**, posición
   ⌖0,25 con MMC). Por eso hay que separar *feature* de *instancia del feature en una pieza*.

---

## Reglas duras del entorno (esto te ahorrará tiempo)

- ✅ **SÍ hay Python** (corregido el 2026-08-13 — antes esta nota decía lo contrario y era falso):

  ```
  C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe   → 3.11.8
  ```

  🔴 **No está en el PATH**: el `python.exe` que responde en la consola es el **stub de la
  Microsoft Store** y falla. **Invocarlo siempre por ruta absoluta.**

  Trae ya instalado (no hace falta pip): `pandas`, `numpy`, `polars`, `scipy`, `matplotlib`,
  **`plotly` 6.6**, `open3d`, `pyvista`, `vedo`, `pymeshlab`, `libigl`, `opencv`, `scikit-image`,
  **`pdfplumber`**, **`PyMuPDF`**, `pytesseract`, `python-docx`, `lxml`, `torch`, `fastapi`.

  → **el STL de 4,9 M triángulos y las nubes de puntos SÍ se pueden procesar aquí.**
  No hay `ezdxf` ni `pythonocc`/OCCT, pero `pip`/`uv` están disponibles.

  ✅ **Y SÍ hay Tesseract** (comprobado el 2026-08-18), v5.5.0, con `eng` y `osd`:

  ```
  C:\Program Files\Tesseract-OCR\tesseract.exe
  ```

  🔴 **Tampoco está en el PATH**: `pytesseract` da `TesseractNotFoundError` hasta que se le dice
  dónde está. Se arregla con `pytesseract.pytesseract.tesseract_cmd = <ruta>` — ya resuelto en
  `prototypes/data-explorer/planos/ver_plano.py`, copiar de ahí.

  ⚠️ **Tesseract sirve para texto grande, NO para texto pequeño.** Para cifras de ~9 px (los
  globos del plano) devuelve basura. Está instalado también `rapidocr-onnxruntime` (2026-08-18),
  que **parece** mejor pero **acierta solo el 37 % en esas cifras y no lo avisa**: ninguno de los
  dos sirve ahí.

  🔑 **Regla que salió de eso: antes de dar por buena una extracción automática, auditar una
  muestra al azar contra la fuente y contar aciertos.** Ni el número de resultados ni la
  confianza del motor valen como validación.

  Sigue siendo válido: para leer `.xls` lo más cómodo es **Excel vía COM desde PowerShell**, y
  para CSV/TXT/PPTX la **Bash tool** (Git Bash tiene `unzip`, `iconv`, `awk`, `find`).

- 📊 **Para VER los datos crudos ya hay visores hechos**, en este repo, en `prototypes/data-explorer/`
  (ver [conocimiento/visores.md](conocimiento/visores.md) y [prototypes/data-explorer/README.md](prototypes/data-explorer/README.md)):

  ```powershell
  $py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
  $s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\prototypes\data-explorer"
  & $py "$s\ver_todo.py"    # genera los cuatro visores y abre out/index.html
  ```

  `metrologia/ver_csv.py` (16 informes de la CMM), `metrologia/ver_txt.py` (40 nubes de puntos),
  `metrologia/ver_pdf.py` (144 gráficas de contorno) y `planos/ver_plano.py` (el plano 2D con OCR
  y buscador) generan un índice navegable con una página por fichero. **Consúltalos como
  referencia al estudiar los formatos**. Los lectores de producción pertenecen al backend;
  no se importan ni se ejecutan los scripts de exploración desde la web.
- **Los CSV de la CMM son cp1252**, no UTF-8. Sin `iconv -f cp1252` salen `C�lculo de f�rmula`.
- 🔴 **OneDrive Files On-Demand**: hay ficheros que son *placeholders*. Leer un solo byte dispara
  la descarga completa y en los grandes **da timeout**. **El estado cambia solo**: el 2026-08-13
  había **195 de los 239 ficheros de `4- Metrologia` en la nube** (el 2026-08-11 estaban todos
  locales). Se salvan los 9 `.xls` y los 16 CSV de cavidad — o sea, **toda la ingesta tabular se
  puede hacer sin riesgo**; lo geométrico (`.igs`, `.dxf`, `.txt`, PDF) hay que hidratarlo, pero
  son 1–3 MB por fichero. El `.step` del molde se hidrató expresamente el 15/09/2026 para
  generar su vista web; el estado de cualquier archivo puede volver a cambiar.
  **No fiarse de ninguna tabla: comprobar el atributo antes de abrir nada:**
  ```powershell
  $a = [int](Get-Item -LiteralPath $ruta).Attributes
  if ($a -band 0x400000) { "EN LA NUBE - no leer" } else { "LOCAL - seguro" }
  ```
- 🔴 **Los tests del backend NUNCA contra la BD `app`.** Desde la revisión del 2026-09-15,
  `conftest.py` rechaza nombres que no terminen en `_test` antes de ejecutar pruebas y usa una
  carpeta temporal para las subidas. La limpieza sigue borrando las tablas de la BD de test.
  Los lanzadores crean un proyecto Docker exclusivo con `compose.test.yml`, sin compartir BD,
  puertos ni volúmenes con la aplicación:

  ```powershell
  .\scripts\test.ps1 -q
  .\scripts\test.ps1 -E2E
  ```

  En Bash: `bash scripts/test.sh -q` y `bash scripts/test.sh --e2e`.
  No copiar tests al contenedor de trabajo ni usar `down -v` como limpieza.
  El seed solo crea un ejemplo; **no recupera datos borrados**.
- **Ficheros temporales** → siempre al scratchpad de la sesión, nunca al repo ni a `/tmp`.
- Los scripts de PowerShell largos: escribirlos a fichero con `Write` y ejecutarlos con `&`,
  no meterlos inline (el quoting se rompe).
- 🔴 **Convención del repo: mantener los `.ps1` en ASCII.** Evita problemas de codificación en
  PowerShell 5.1, que puede interpretar un fichero UTF-8 sin BOM como ANSI. No asumir que cada
  carácter no ASCII provoca por sí solo un error de sintaxis.

## Trampas de los datos (resumen)

Detalle y recetas de lectura (XLS por COM, CSV cp1252, texto de PPTX) en
[conocimiento/trampas.md](conocimiento/trampas.md). Lo esencial:

- **CSV de CMM antes que XLS** para medidas coincidentes: los informes PPAP heredan bloques de
  informes anteriores (3212, 3288, 3051: ver I-001 en `conocimiento/incongruencias.md`).
- **ID de elemento CMM**, no el título del bloque; signo invertido en B2/B4; cp1252.
- **Nombres inconsistentes** de carpetas y ficheros; la cavidad sale de la ruta, no del nombre.
- **Plano 3212 = escaneo sin texto, rev. 07** frente a rev. 06 de los informes. Los N-numbers del
  globo no se pueden leer por OCR; los `.icp` de otras piezas sí dan su posición.
- **Hojas `DR*` variables, metadatos en `HISTORY`**, fecha del XLS = emisión, no medición.
- **N-numbers locales a cada plano**: nunca unir cotas de piezas distintas por el número.
- 🔴 **Valores generados con `RAND()`** en 191 libros (generadores de Cpk, muestras 2–5 de PPAP de
  cliente) y en los `#P#` SPC: no son medidas. Mirar la fórmula o la tabla `celda_aleatoria`
  (I-003). Hay versiones de un mismo informe con valores cambiados (I-603).

---

## Documentación — dónde está cada cosa

Leer bajo demanda, no de entrada.

### Los datos de Exemples → `conocimiento/`

🔑 **Antes de abrir un original, consultar la biblioteca** (`conocimiento/datos/biblioteca.sqlite`,
fuera de Git): inventario y contenido extraído de los 4.530 ficheros, con búsqueda de texto y SQL.
Uso en [conocimiento/README.md](conocimiento/README.md); estado en [conocimiento/AVANCE.md](conocimiento/AVANCE.md).

| Documento | Léelo cuando… |
|---|---|
| [conocimiento/comparativa.md](conocimiento/comparativa.md) | quieras saber **en qué se parecen y se diferencian** los 8 features y sus piezas (esqueleto, formatos, plantillas) |
| [conocimiento/incongruencias.md](conocimiento/incongruencias.md) | busques **lo que no cuadra** o haya que pedir a INTEPLAST, con evidencia |
| `conocimiento/<n>-<feature>/README.md` | trabajes con un feature concreto (`0-bolt-eye` … `7-planitudes`) |
| [conocimiento/0-bolt-eye/3212/README.md](conocimiento/0-bolt-eye/3212/README.md) | trabajes con el **piloto 3212**: una ficha por carpeta; [6-metodo-medida.md](conocimiento/0-bolt-eye/3212/6-metodo-medida.md) primero (`GX`/`GN`/`LP(2)`), [historial-molde.md](conocimiento/0-bolt-eye/3212/historial-molde.md) para muestreo ↔ corrección, [revisión del 17/09/2026](conocimiento/0-bolt-eye/3212/revision-2026-09-17.md) para previsiones `DR(100%)`, `PUNTS_NOUS` y N170 |
| [conocimiento/formatos-parsing.md](conocimiento/formatos-parsing.md) | vayas a **escribir un parser**: CSV CMM, XLS PPAP y PPTX del 3212, columna a columna |
| [conocimiento/trampas.md](conocimiento/trampas.md) | necesites las **recetas de lectura** o el detalle de las trampas del 3212 |
| [conocimiento/visores.md](conocimiento/visores.md) | quieras **ver los datos**: los visores de `prototypes/data-explorer/` |

### La aplicación → `docs/`

| Documento | Léelo cuando… |
|---|---|
| [docs/proximos-pasos.md](docs/proximos-pasos.md) | vayas a **retomar el trabajo**: qué quedó abierto y qué hace falta para continuar |
| [docs/app-web.md](docs/app-web.md) | vayas a tocar la **aplicación** (`backend/`, `frontend/`): modelo, endpoints, permisos, cómo levantarla y qué falta |
| [docs/ficheros-externos.md](docs/ficheros-externos.md) | vayas a vincular originales, configurar la carpeta local o preparar Graph |
| [docs/modelo-datos.md](docs/modelo-datos.md) | trabajes en el **esquema de la BD** o en la ingesta |
| [docs/ingesta-automatica.md](docs/ingesta-automatica.md) | vayas a **generalizar la ingesta** a otras piezas: qué se lee con reglas (medido), qué necesita LLM y qué no está en los datos |
| [docs/preguntas-abiertas.md](docs/preguntas-abiertas.md) | vayas a **preguntar algo a INTEPLAST** (⚠️ pendiente de revisar: bastante obsoleta) |

---

## Convenciones de trabajo

- Responder **en castellano**.
- Al resolver una pregunta abierta, **actualizar `docs/preguntas-abiertas.md`** moviéndola a
  resueltas **con la evidencia** (fichero, celda o línea concreta).
- No inventar cifras: toda afirmación numérica debe salir de un fichero leído en la sesión.
