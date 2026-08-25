# INTEPLAST — contexto del proyecto

## Qué es este repo

**El repo de INTEPLAST: código + conocimiento del proyecto**
(`github.com/opticsensors/inteplast`). Aquí vive todo lo del proyecto salvo los datos crudos del
cliente y las notas de Obsidian (ver rutas abajo).

| Carpeta | Qué es |
|---|---|
| `backend/` `frontend/` | La **aplicación** (FastAPI + React, sobre el template `full-stack-fastapi-template`). → [docs/app-web.md](docs/app-web.md) |
| `scripts/` | Shell de **build y test** del template. ⚠️ Nada que ver con los visores |
| `data-explorer/` | 📊 Los **visores de los datos crudos** (Python): `metrologia/` (CMM) y `planos/` (el plano 2D). → [docs/visores.md](docs/visores.md) |
| `docs/` | 🔑 El **conocimiento del dominio**: análisis de los datos, modelo de la BD, preguntas abiertas |
| `compose*.yml` `deployment.md` `development.md` | Docker y despliegue |

> `docs/` y este `CLAUDE.md` vivían hasta el **2026-08-14** en un vault de Obsidian
> (`C:\edu\projects\Inteplast`). Se movieron aquí. En el vault se quedan las notas originales
> `inteplast_*.md` y sus imágenes (`_/`): los `docs/` las citan por nombre y se leen por ruta
> absoluta desde ahí.

## Objetivo del proyecto

Construir una **base de datos interactiva de conocimiento de diseño de piezas inyectadas**.
El usuario introduce el **ID de un feature** (p. ej. *Bolt Eye*) y el sistema devuelve:
**warnings** (qué vigilar al diseñarlo), **lessons learned** (qué se hizo en el molde cuando
salió mal), **cotas**, y **piezas/moldes de referencia** con sus CAD descargables.

Cliente final: **Robert Bosch** (división BueP). Informes en formato **PPAP / QS9000-TS**.

## Rutas

| Qué | Ruta |
|---|---|
| **Este repo** (código + docs) | `C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast` |
| 📊 **Visores** de los datos | `…\repos\inteplast\data-explorer` *(dentro de este repo)* |
| 🔴 **Datos** de INTEPLAST | `C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples` |
| 🔴 **Notas** de Obsidian | `C:\edu\projects\Inteplast` *(vault en `C:\edu`)* |

> 🔴 **Los datos crudos del cliente NO se copian al repo** — se leen in situ desde `Exemples`
> (rutas absolutas en la cabecera de cada script de `data-explorer/`). Son gigas, están en
> OneDrive Files On-Demand y no son nuestros.
>
> ⚠️ Un script nuevo **de exploración de datos** va a `data-explorer/`, **no** a `scripts/`
> (que es el de build y test del template). Y en `docs/` se anota qué hace y dónde está.

## Foco actual

**Solo se trabaja sobre `3212 Pump Housing`.** Es el proyecto piloto, el más completo, y el
único con histórico cerrado (metrología + retoques de molde + escaneado STL). Los otros tres
(`2820`, `3051`, `3197`) están documentados pero **no se tocan** salvo petición explícita.

---

## La aplicación — lo que ya está construido

Sobre la plantilla de FastAPI está implementada la **base de conocimiento de features**: fichas de
feature con **warnings**, **lessons learned**, **ficheros de ejemplo** (molde, CAD, escaneo, plano
2D, Moldflow) y buscador global. Es el bloque transversal de
[docs/modelo-datos.md](docs/modelo-datos.md).

🔑 **Los ficheros se agrupan por PIEZA, no por tipo.** La tabla `Part` (código `3212` + nombre) es
el embrión del `PROYECTO`, y la ficha del feature enseña **un desplegable por pieza con sus
ficheros dentro** (desde el 2026-08-25; antes era una matriz pieza × tipo).
Un feature puede además estar **declarado** en una pieza sin tener ningún fichero subido todavía
(`FeaturePartLink`, embrión de `INSTANCIA_EN_PROYECTO`).

🔴 **No está la ingesta** (`MUESTREO`, `MEDICION`, `CORRECCION_MOLDE`): eso se alimenta de los
CSV/XLS/PPTX y es la siguiente fase.

```powershell
docker compose up -d --build db prestart backend   # backend + BD (aplica migraciones)
cd frontend; npm run dev                           # http://localhost:5173
docker compose exec backend python -m app.seed_features   # carga de ejemplo: Bolt Eye del 3212
```

- 🔑 **Antes de tocar `backend/` o `frontend/`, leer [docs/app-web.md](docs/app-web.md)**: modelo,
  endpoints, permisos, decisiones y cabos sueltos.
- 🔴 **`--build` no es opcional tras tocar `backend/`.** El código va dentro de la imagen: sin él,
  `docker compose up -d` reutiliza el `backend:latest` viejo y arrancas con código antiguo **sin
  ningún error visible**. Se comprueba con `docker compose exec backend alembic current`.
- ⚠️ **Cambiar un endpoint o un modelo obliga a regenerar el cliente TypeScript**
  (`bash scripts/generate-client.sh`), o el frontend se queda desincronizado.
- La página `/items` es la demo de la plantilla: ya no está en el menú, pero el `Item` sigue en el
  código. La página real de gestión es `/features`, y la **ficha del feature es `/features/{id}`**
  — desde el 2026-08-19 es una página con URL propia, no una modal.

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
  `data-explorer/planos/ver_plano.py`, copiar de ahí.

  ⚠️ **Tesseract sirve para texto grande, NO para texto pequeño.** Para cifras de ~9 px (los
  globos del plano) devuelve basura. Está instalado también `rapidocr-onnxruntime` (2026-08-18),
  que **parece** mejor pero **acierta solo el 37 % en esas cifras y no lo avisa**: ninguno de los
  dos sirve ahí.

  🔑 **Regla que salió de eso: antes de dar por buena una extracción automática, auditar una
  muestra al azar contra la fuente y contar aciertos.** Ni el número de resultados ni la
  confianza del motor valen como validación.

  Sigue siendo válido: para leer `.xls` lo más cómodo es **Excel vía COM desde PowerShell**, y
  para CSV/TXT/PPTX la **Bash tool** (Git Bash tiene `unzip`, `iconv`, `awk`, `find`).

- 📊 **Para VER los datos crudos ya hay visores hechos**, en este repo, en `data-explorer/`
  (ver [docs/visores.md](docs/visores.md) y [data-explorer/README.md](data-explorer/README.md)):

  ```powershell
  $py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
  $s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\data-explorer"
  & $py "$s\ver_todo.py"    # genera los cuatro visores y abre out/index.html
  ```

  `metrologia/ver_csv.py` (16 informes de la CMM), `metrologia/ver_txt.py` (40 nubes de puntos),
  `metrologia/ver_pdf.py` (144 gráficas de contorno) y `planos/ver_plano.py` (el plano 2D con OCR
  y buscador) generan un índice navegable con una página por fichero. **Úsalos antes de escribir
  un parser nuevo**: el código de parseo ya resuelto está ahí.
- **Los CSV de la CMM son cp1252**, no UTF-8. Sin `iconv -f cp1252` salen `C�lculo de f�rmula`.
- 🔴 **OneDrive Files On-Demand**: hay ficheros que son *placeholders*. Leer un solo byte dispara
  la descarga completa y en los grandes **da timeout**. **El estado cambia solo**: el 2026-08-13
  había **195 de los 239 ficheros de `4- Metrologia` en la nube** (el 2026-08-11 estaban todos
  locales). Se salvan los 9 `.xls` y los 16 CSV de cavidad — o sea, **toda la ingesta tabular se
  puede hacer sin riesgo**; lo geométrico (`.igs`, `.dxf`, `.txt`, PDF) hay que hidratarlo, pero
  son 1–3 MB por fichero. El `.step` de 247 MB sigue en la nube; el `.mfr` y el `.stl`, locales.
  **No fiarse de ninguna tabla: comprobar el atributo antes de abrir nada:**
  ```powershell
  $a = [int](Get-Item -LiteralPath $ruta).Attributes
  if ($a -band 0x400000) { "EN LA NUBE - no leer" } else { "LOCAL - seguro" }
  ```
- 🔴 **Los tests del backend NUNCA contra la BD `app`.** El `conftest.py` de la plantilla la
  **vacía al terminar** (`Item`, `Feature`, `Part`, `StoredFile`, `User`), y de paso te tira la
  sesión del navegador: el superusuario se recrea con otro `id` y el token que tienes guardado
  deja de valer. Van contra `app_test`, y hay que copiarlos al contenedor porque la imagen no los
  lleva — receta completa en [docs/app-web.md](docs/app-web.md#-los-tests-siempre-contra-app_test):

  ```powershell
  docker compose exec -T backend rm -rf /app/backend/tests
  docker cp backend/tests inteplast-backend-1:/app/backend/tests
  docker compose exec -T -e POSTGRES_DB=app_test backend python -m pytest tests -q
  ```

  Si aun así se vacía la BD: `docker compose exec backend python -m app.seed_features` la repuebla.
- **Ficheros temporales** → siempre al scratchpad de la sesión, nunca al repo ni a `/tmp`.
- Los scripts de PowerShell largos: escribirlos a fichero con `Write` y ejecutarlos con `&`,
  no meterlos inline (el quoting se rompe).
- 🔴 **Los `.ps1` deben ser SOLO ASCII.** PowerShell 5.1 los lee como ANSI: un guion largo (`—`)
  o una `ç` en un literal provoca un error de sintaxis. Sin acentos en los scripts.

### Receta: leer un `.xls` PPAP

```powershell
$xl = New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false
$wb = $xl.Workbooks.Open($ruta, 0, $true)          # 0, $true = read-only
$ws = $wb.Worksheets.Item("DR(3D)")
$ws.Cells.Item($fila,$col).Text
$wb.Close($false); $xl.Quit()                       # SIEMPRE cerrar, deja procesos colgados
```

### Receta: leer un CSV de CMM

```bash
iconv -f cp1252 -t utf-8 "…/3212_c13.csv"
```

### Receta: sacar el texto de un PPTX de corrección

```bash
D=$(mktemp -d); unzip -o -q -j "…/correction.pptx" "ppt/slides/slide*.xml" -d "$D"
for f in $(ls "$D"/slide*.xml | sort -V); do sed 's/<[^>]*>/\n/g' "$f" | grep -v '^\s*$'; done
```
*(No extraer `ppt/media/` salvo que haga falta: tarda minutos.)*

---

## Trampas que ya nos han mordido

1. 🔴 **El `.xls` no siempre es la fuente de verdad — el CSV sí.** `intern.05.xls` tiene el
   bloque N117/N118 **copiado y pegado de `intern.03`** (valores idénticos), mientras el CSV de
   `intern.05` da valores distintos. **Ingerir los CSV, no los XLS.**
2. 🔴 **Solo `intern.01` es un informe completo.** Del `.03` en adelante solo se remide lo que
   fallaba. Si miras solo los XLS parecerá que N170 nunca se volvió a medir — sí se midió, está
   en los CSV.
3. **Error de signo sistemático en el export de la CMM**: bolts B2 y B4, `Posición Z` sale con
   el signo invertido (nominal +31, medido −30,990 ⇒ desviación −61,99). Está en **todos** los
   muestreos. No es una pieza mala.
4. **Errata de plantilla**: el bloque `N170 BOLT 1 MIN/MAX H=5.0 mm` aparece repetido dentro del
   bloque del **BOLT 2**. Fiarse del **ID de elemento CMM** (11–14 = H1,5; 15–18 = H5,0;
   31–34 = posición), no del literal del título.
5. **Nombres inconsistentes** en carpetas y ficheros (`support intern.01`, `Suport_Int_01`,
   `support.intern.08`; `3212_c13.csv`, `3212c14.csv`, `13_3212.csv`). Normalizar con regex,
   nunca con match exacto. ⚠️ Y en `intern.05`, `c15/` y `c16/` llaman a sus ficheros **igual**
   (`3212_Cav_.txt`, `Perfil_3212_C.dxf`): **la cavidad solo está en la carpeta padre.** Derivarla
   de la ruta, nunca del basename.
6. **Multilingüe**: catalán, castellano, inglés y alemán, a veces en el mismo fichero.
   Las acciones de retoque de molde están **en catalán**.
7. **Cavidades no empiezan en 1**: el 3212 usa **c13–c16** (molde de 16, se controlan 4).
8. 🔴 **El plano 2D no tiene texto: es un escaneo.** El PDF es una imagen JPEG de 3276×2317 px
   impresa con *"Microsoft: Print To PDF"*, con **0 fuentes**. `pdftotext` devuelve 1 byte.
   **Ya hay OCR hecho**: `data-explorer/planos/ver_plano.py` saca 1.504 palabras (confianza media
   74) y las deja en `out/plano/texto-3212.txt`. Las notas se leen bien; la `Ø` sale como
   `9`/`@`/`$` (`Ø40,3` → `940.3`) y los marcos GD&T son ilegibles.
   🔑 **Los N-numbers están en el plano**, en **globos verdes sin la `N`** (`170`, `170.2`… =
   N170 y sus puntos). Se **localizan** los 178, pero 🔴 **NO se pueden leer**: miden ~9 px.
   Tesseract da basura; **RapidOCR es peor porque acierta solo el 37 % y falla con 0,99 de
   confianza** (auditadas 16 lecturas al azar: 6 buenas; `155` por `156`, `103` por `109`).
   **No volver a intentarlo con este PDF**: la salida es pedir el plano bueno (A4).
9. 🔴 **El plano que tenemos no es el de los informes.** El PDF es la **rev. 07** (23/05/2025);
   todos los informes —hasta `intern.09` de abril de 2025— referencian la **rev. 06**.
10. **La carpeta `2- Moldflow` no existe en el 3212** (en 3051/3197 existe pero está vacía).
    Los estudios están siempre en `7- Moldflow`. No leerlo como dato faltante.
11. **Las hojas del XLS cambian de nombre**: `DR(3D)` en `.01/.03/.05`, `DR` en `.08/.09`,
    ninguna en `.02/.04/.06`. Buscar por patrón `DR*`, no por nombre exacto. Para **metadatos**
    da igual: la cabecera está replicada en todas las hojas del libro.
12. 🔑 **Los metadatos buenos están en la hoja `HISTORY`, no en la cabecera.** Es un log
    **acumulativo**: `intern.09.xls!HISTORY` trae **los 9 muestreos** con fecha, lote,
    responsable y *motivo*, incluidos los que tienen la cabecera vacía (`.02`, `.06`) o rota
    (`.06` da `#¡REF!`). Rótulos `INFORME n` en filas irregulares; hasta 2 filas por informe.
13. 🔴 **Los `.igs` y los `.dxf` son duplicados de los `.txt`**: el `.igs` = `_PUNTS.txt` (con un
    offset constante de −3,8807 en Z), el `.dxf` = `_Cav<NN>.txt` (mismos 17.656 puntos). **No
    ingerirlos** — mismo dato, 2,5× más peso, y el `.dxf` exigiría Python.
14. **La fecha del `.xls` es la de emisión del informe, no la de la medición.** El escaneo del
    muestreo 01 es del **19/01/2024** (cabecera del `.igs` y PDFs `PA`/`PB`); el informe declara
    el 25/01/2024.

---

## Documentación — dónde está cada cosa

Leer bajo demanda, no de entrada.

### El proyecto 3212 — un documento por carpeta

Empieza siempre por [docs/3212/README.md](docs/3212/README.md): ficha del proyecto, estado de
hidratación en OneDrive y por dónde empezar.

| Carpeta del proyecto | Documento | Qué encontrarás |
|---|---|---|
| `1-2D y 3D Pieza` | [1-pieza-2d-3d.md](docs/3212/1-pieza-2d-3d.md) | Plano 2D (🔴 es un **escaneo sin texto**) y sólido CATIA sin árbol de features |
| `2- Moldflow` | [2-moldflow.md](docs/3212/2-moldflow.md) | **No existe.** Documentado para no buscarla. |
| `3- 3D Molde` | [3-molde-3d.md](docs/3212/3-molde-3d.md) | STEP de 247 MB, 🔴 **en la nube**: leerlo dispara la descarga |
| `4- Metrologia` | [4-metrologia.md](docs/3212/4-metrologia.md) | 🔑 Los 9 muestreos, los XLS y los CSV de CMM |
| `5- Retoques de molde` | [5-retoques-molde.md](docs/3212/5-retoques-molde.md) | 🔑 Las 54 acciones correctivas, diapositiva a diapositiva |
| `6- Métode de mesura` | [6-metodo-medida.md](docs/3212/6-metodo-medida.md) | **Leer primero**: `GX`/`GN`/`LP(2)`, alineación, cómo se mide cada N-number |
| `7- Moldflow` | [7-moldflow.md](docs/3212/7-moldflow.md) | `.mfr` cifrado: solo Moldflow Communicator |
| `8- STL peça real` | [8-stl-pieza-real.md](docs/3212/8-stl-pieza-real.md) | Malla de 4,9 M triángulos, lote 315346 |
| *(transversal `4-`↔`5-`)* | [historial-molde.md](docs/3212/historial-molde.md) | Cronología muestreo ↔ corrección y la **prueba de que el retoque del Bolt Eye funcionó** |

### Documentos generales

| Documento | Léelo cuando… |
|---|---|
| [docs/app-web.md](docs/app-web.md) | vayas a tocar la **aplicación** (`backend/`, `frontend/`): modelo, endpoints, permisos, cómo levantarla y qué falta |
| [docs/visores.md](docs/visores.md) | quieras **ver los datos** en vez de leer sobre ellos: qué hace cada visor de `data-explorer/` y qué decisiones lleva dentro |
| [docs/formatos-parsing.md](docs/formatos-parsing.md) | vayas a **escribir un parser**: esquemas exactos de CSV/XLS/PPTX, columna a columna |
| [docs/modelo-datos.md](docs/modelo-datos.md) | trabajes en el **esquema de la BD** o en la ingesta |
| [docs/preguntas-abiertas.md](docs/preguntas-abiertas.md) | vayas a **preguntar algo a INTEPLAST** — mira antes si ya está resuelto |
| [docs/otros-proyectos.md](docs/otros-proyectos.md) | te preguntes qué pasa con 2820/3051/3197 y **por qué no se tocan** |

---

## Convenciones de trabajo

- Responder **en castellano**.
- Al resolver una pregunta abierta, **actualizar `docs/preguntas-abiertas.md`** moviéndola a
  resueltas **con la evidencia** (fichero, celda o línea concreta).
- No inventar cifras: toda afirmación numérica debe salir de un fichero leído en la sesión.
