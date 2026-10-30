# `prototypes/data-explorer/` — visores de los datos crudos

Herramientas experimentales para explorar los datos. No forman parte de la web ni
de su imagen Docker. La aplicación tiene lectores propios en `backend/app/ingestion/`.

Scripts para **ver** los datos en vez de leer descripciones. Generan un **índice con árbol de
carpetas** y **una página por resultado**.

Están repartidos en dos carpetas según de dónde salga el dato:

```
prototypes/data-explorer/
├── ver_todo.py       punto de entrada: ejecuta los cuatro
├── metrologia/       lo que dejó la máquina de medición (4- Metrologia)
├── planos/           el plano 2D del cliente (1-2D y 3D Pieza)
└── out/              lo generado; es UNA sola carpeta compartida, ignorada en git
```

| Script | Qué lee | Qué genera |
|---|---|---|
| **[`ver_todo.py`](ver_todo.py)** | — | **`out/index.html`**: la pantalla donde se elige, y ejecuta los otros cuatro |
| [`metrologia/ver_csv.py`](metrologia/ver_csv.py) | Los **16 CSV de cavidad** (los informes de la CMM) | `out/csv-3212.html` + 24 páginas |
| [`metrologia/ver_txt.py`](metrologia/ver_txt.py) | Las **40 nubes de puntos** `.txt` | `out/txt-3212.html` + 44 páginas |
| [`metrologia/ver_pdf.py`](metrologia/ver_pdf.py) | Las **144 gráficas de contorno** en PDF | `out/pdf-3212.html` + 148 páginas + 144 PNG |
| [`planos/ver_plano.py`](planos/ver_plano.py) | El **plano 2D** (escaneo sin texto) → OCR | `out/plano-3212.html` + el texto extraído |

**Se abre `out/index.html`**, se elige el tipo de dato, se navega por el árbol y al hacer clic en
un fichero se va a su página.

```
out/
├── index.html                     ← SE ABRE ESTO (5 KB)
├── csv-3212.html                  ← árbol de las cotas medidas (12 KB)
├── txt-3212.html                  ← árbol de las nubes de puntos (16 KB)
├── pdf-3212.html                  ← árbol de la tolerancia de contorno (38 KB)
├── csv/
│   ├── intern.01-c13.html         ← una página por fichero medido
│   ├── cav-intern.01.html         ← las 4 cavidades de un muestreo comparadas
│   └── evo-c13.html               ← la evolución de una cavidad entre muestreos
├── txt/
│   ├── intern.01-c13-perfil.html  ← una página por nube de puntos
│   └── obj-c13.html               ← los subconjuntos PUNTS_NOUS superpuestos
├── pdf/
│   ├── intern.01-c13-PA_1.html    ← una página por gráfica de contorno
│   ├── evo-c13.html               ← la evolución del contorno entre muestreos
│   └── img/*.png                  ← la página del PDF renderizada
├── plano/
│   ├── ocr-3212.json              ← caché del OCR: cada palabra con su caja
│   ├── globos-3212.json           ← caché de los globos LOCALIZADOS (no leídos)
│   ├── texto-3212.txt             ← el texto extraído, en orden de lectura
│   └── img/*.jpg|png              ← el plano, y los marcados de --buscar/--n
└── vendor/plotly.min.js           ← la librería, compartida por todas las páginas
```

Cada página pesa entre 6 y 509 KB, así que abre al instante. `out/` no se versiona: son ficheros
generados, se rehacen en un par de minutos.

---

## Cómo se ejecutan

🔴 **Python no está en el PATH.** El `python.exe` que responde en la consola es el stub de la
Microsoft Store y falla. Hay que llamarlo **por ruta absoluta**:

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
$s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\prototypes\data-explorer"

& $py "$s\metrologia\ver_csv.py"                    # genera el HTML y lo abre en el navegador
& $py "$s\metrologia\ver_txt.py"
```

> 📁 **Dónde vive esto.** Estos visores son **utilidades de exploración de los datos crudos**, no
> parte de la aplicación: no comparten nada con `backend/` ni con `frontend/`, y por eso están en
> `prototypes/data-explorer/` y no en `scripts/` (que es el de build y test del template FastAPI).
> El puntero a esta carpeta está en [`../../conocimiento/visores.md`](../../conocimiento/visores.md) y en
> [`../../CLAUDE.md`](../../CLAUDE.md).
>
> 🔴 Los **datos** que lee siguen fuera del repo, en
> `…\Escritorio\proyectos\11. inteplast\Exemples\0- Bolt Eye` (ruta absoluta en la cabecera de
> cada script). Desde el 2026-10-21 `Exemples` se organiza por feature; el 3212 está en `0- Bolt Eye`.

En la máquina de desarrollo se usó Python 3.11.8. Dependencias de los visores:
`pandas`, `numpy`, `plotly`, `PyMuPDF`; el plano añade `opencv-python`, `Pillow` y
`pytesseract`, además del ejecutable Tesseract. En otro equipo hay que instalarlas.

⚠️ **`ver_plano.py` usa Tesseract**, que 🔴 **no está en el PATH**: el script lo busca solo en
`C:\Program Files\Tesseract-OCR\`. Sirve para el texto del plano (notas y cotas).

🔴 **No sirve para los números de dentro de los globos, y RapidOCR tampoco** (acierta el 37 % y
falla con 0,99 de confianza). Esa parte **se quitó a propósito** de `ver_plano.py`: ver
[`conocimiento/visores.md`](../../conocimiento/visores.md). Para los globos, ver la
[comparativa de lectores del 29/10/2026](#comparativa-de-lectores-de-globos-29102026): un lector
propio entrenado con números sintéticos acierta 227 de 253.

### Opciones

```powershell
& $py "$s\metrologia\ver_csv.py" --no-abrir           # no abrir el navegador
& $py "$s\metrologia\ver_csv.py" --corregir-signo     # invierte el error de signo de B2/B4
& $py "$s\metrologia\ver_txt.py" --familia nous       # solo el subconjunto PUNTS_NOUS
& $py "$s\metrologia\ver_txt.py" --muestreo 01 --cavidad c13
& $py "$s\metrologia\ver_txt.py" --max-puntos 12000   # más detalle (y más peso)
& $py "$s\metrologia\ver_csv.py" --raiz "D:\otra\ruta\4- Metrologia"
```

Los dos apuntan por defecto a la ruta absoluta de los datos del 3212, que **no está en este
repo**:

```
C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples\0- Bolt Eye\3212 Pump Housing\4- Metrologia
```

⚠️ **`ver_txt.py` hidrata ficheros de OneDrive.** 36 de los 40 `.txt` son placeholders; leerlos
los descarga (~22 MB en total). La primera pasada tarda un par de minutos, las siguientes no.

---

## Qué vas a ver

### `ver_csv.py` — los informes de la CMM

El árbol tiene una carpeta por muestreo (`intern.01`, `.03`, `.05`, `.08`) con sus 4 cavidades, y
al final **dos carpetas de comparativas**. Tres tipos de página:

1. **Un fichero medido.** Una barra por característica, en el orden exacto del fichero. El eje X
   no está en mm sino en **fracción de la tolerancia consumida**: `0` = nominal del plano,
   `±1` = el límite, fuera de la franja verde = **fuera de tolerancia**. Se normaliza para poder
   comparar en el mismo eje una cota de ±0,5 mm con otra de ±0,02 mm. El **hover da los mm
   reales** y debajo está la tabla completa en crudo.
2. **Comparar las cavidades entre sí** (una página por muestreo). Distingue un problema del molde
   entero — los 4 rombos desplazados juntos — de uno de una sola cavidad, un rombo suelto.
3. **Comparar los muestreos entre sí** (una página por cavidad): heatmap de las 211 cotas × 4
   muestreos. Una fila que pasa de roja a verde es **una medición que entró en tolerancia**;
   atribuir el cambio a un retoque requiere contrastarlo con su historial. Debajo,
   las 15 cotas que más se movieron en mm reales.

### `ver_txt.py` — las nubes de puntos

Árbol de dos niveles: muestreo → cavidad → los 3 ficheros de esa cavidad (perfil, `PUNTS`,
`PUNTS_NOUS`). Cada página trae la **nube 3D** (arrastra para rotar, color = altura Y) y la
**vista en planta X-Z**, con las estadísticas reales (nº de puntos, bounding box, niveles de
altura detectados). Al final, una carpeta con los **subconjuntos PUNTS_NOUS de cada muestreo
superpuestos** por cavidad.

### `ver_pdf.py` — la tolerancia de contorno

Árbol de dos niveles: muestreo → cavidad → las 12 gráficas. Cada página lleva los **6 números
extraídos**, una **barra** que sitúa la desviación respecto a la banda de tolerancia, y **la
página del PDF renderizada** para juzgar la gráfica original al lado del dato. Al final, la
evolución del contorno por cavidad a lo largo de los muestreos.

Estos PDF **no son una representación de los CSV ni de los TXT**: la comparación del perfil
interior contra el contorno teórico no está en ningún otro fichero, y no se puede recalcular
desde las nubes de puntos porque el contorno nominal no lo tenemos (⚠️ el `3212_CONTORN.igs` es
el contorno **escaneado**, no el nominal).

Los 12 de cada cavidad son **2 perfiles × 6 contornos**: `PERFIL_A` (`PA_1..6`, contornos 21, 31,
22, 32, 23, 33) recorre la zona alta del interior y `PERFIL_B` (`PB_1..6`, contornos 25, 35, 26,
36, 27, 37) la baja. Todos contra el mismo nominal, `CONTORN (10)`, con tolerancia ±0,025 mm.

---

## Lo que hay que saber de los datos (y que los scripts ya manejan)

- **Los CSV son cp1252**, no UTF-8, y son un **export por bloques**, no una tabla: una cabecera
  de N-number y debajo sus filas medidas.
- **Detección de fila de dato**: `≥8 campos` **y** campo 2 no vacío. Mirar el campo 1 (ID de
  elemento CMM) **no vale**: muchas filas de dato lo traen vacío.
- **Cabeceras repetidas**: `N170 BOLT 1 MIN/MAX H=5.0 mm` aparece también dentro del bloque del
  **BOLT 2** (errata de plantilla). Los scripts numeran cada aparición para poder cruzar
  muestreos; sin eso el cruce se multiplica.
- **Error de signo del export**: bolts **B2 y B4**, `Posición Z` sale con el signo invertido
  (nominal +31, medido −30,990 ⇒ desviación −61,99). Está en los 4 muestreos, **no es una pieza
  mala**. Se marca en el hover; `--corregir-signo` lo invierte en esos elementos y recalcula
  desviación, exceso y NOK. Conserva las columnas originales y aplicarlo dos veces no reinvierte.
- **Nombres inconsistentes**: `3212_c13.csv`, `3212c14.csv`, `13_3212.csv`. Y en `intern.05` las
  carpetas `c15/` y `c16/` tienen ficheros con el **mismo nombre**, así que la cavidad se deduce
  de la carpeta padre.
- **Los 4 muestreos con CMM traen los mismos 114 bloques y 211 filas**: el programa de la máquina
  nunca cambió, por eso las vistas 2 y 3 pueden alinear fila a fila.

- **Cada CSV es UNA pieza**, no un promedio: `3212c14.csv` son las medidas de la única pieza que
  salió del hueco 14 en esa tanda. Los `MIN`/`MAX` que se repiten por todo el fichero son el
  valor mínimo y máximo **del mismo elemento en la misma pieza** (así se detecta la ovalidad).

Todo el detalle está en este repo: [formatos-parsing.md](../../conocimiento/formatos-parsing.md),
[4-metrologia.md](../../conocimiento/0-bolt-eye/3212/4-metrologia.md) y [visores.md](../../conocimiento/visores.md).
Las notas originales citadas por esos documentos permanecen en el vault externo.

**Los PDF con campos ausentes o ilegibles quedan como estado desconocido**, con el motivo
visible y un hueco en la evolución. Una extracción incompleta nunca equivale a cero ni a OK.

### Regresiones sin datos del cliente

```powershell
& $py -B -m unittest discover -s "$s\tests" -v
```

Estos tests usan CSV sintéticos en memoria, páginas PDF simuladas y celdas XLS simuladas
para los emparejamientos y previsiones del prototipo. No recorren `Exemples`,
no abren archivos del cliente y no necesitan Docker ni una base de datos.

---

## Detalle técnico: por qué una página por resultado

La primera versión encadenaba los 84 gráficos en un solo HTML de 15 MB. Además de ser imposible
de navegar, **no funcionaba**: los gráficos que usan WebGL consumen contextos limitados por el
navegador; en aquella prueba los primeros gráficos se quedaban en blanco al acumularlos.

Partirlo en una página por resultado lo resuelve de raíz —1 o 2 gráficos por página— y de paso
hace que el índice cargue al instante. `plotly.min.js` se escribe **una sola vez** en
`out/vendor/` y las páginas de gráficos lo referencian con una ruta relativa, en vez de llevar 4,9 MB de
librería embebidos cada una.

⚠️ Eso implica que **las páginas necesitan estar junto a su carpeta `vendor/`**: si mueves un
HTML suelto a otro sitio, se queda sin librería y no pinta nada. Mueve `out/` entera.

## Prototipo independiente de correcciones (17/09/2026)

`ver_correcciones.py` genera `out/correcciones-3212/index.html`, sin modificar `ver_todo.py`
ni sus salidas. Lee CSV, previsiones de los XLS de retoques y texto/imágenes de PPTX.
Incluye N161, N240, N170 y N165, selección de cavidad, agujero/altura en N170, evolución,
secciones de N165 y perfiles A/B complementarios. Conserva enlaces y localizadores de origen.

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
& $py -m pip install xlrd
& $py prototypes/data-explorer/ver_correcciones.py
# Opcional: --no-abrir, --raiz <carpeta de la pieza>, --salida <carpeta de salida>
```

Dependencias: pandas, numpy, plotly, PyMuPDF y **xlrd**. Se leen valores guardados de XLS;
no se ejecutan macros ni se recalculan hipótesis. Las correspondencias son explícitas para
el 3212 y se validan; no es una ingesta genérica. Faltantes se muestran sin evaluar.
Para mover la vista, conservar juntos `index.html`, `datos.json` y `assets/`. Los enlaces
a originales siguen apuntando a la carpeta externa de esta máquina.

La documentación antigua del visor TXT llamaba «objetivos» a PUNTS_NOUS. Esa interpretación
está retirada: son los últimos 150 puntos de PUNTS. Los visores anteriores se conservan
sin cambios de código por petición del usuario. [Hallazgos y límites](../../conocimiento/0-bolt-eye/3212/revision-2026-09-17.md).

## Correcciones v2 · vista para presentación (18/09/2026)

```powershell
py -3.11 .\prototypes\data-explorer\ver_correcciones_v2.py
```

Genera y abre `out/correcciones-3212-v2/index.html`. Mantiene las opciones `--raiz`,
`--salida` y `--no-abrir`. Reutiliza los lectores de `ver_correcciones.py`; no modifica
ese script, `ver_todo.py` ni sus salidas.

- Imagen del retoque, evolución **01 → 03 → 05 → 08** y previsión sobre el muestreo posterior.
- Tabla antes / previsto / después y comparación visual de las cuatro cavidades.
- N170: matriz de ocho secciones por cuatro cavidades, con GX y LP separados.
- N165: detalle de las 60 secciones. Perfiles A/B: informes 01, 03 y 05 en paralelo.
- Modo presentación, ampliación de imágenes, zoom de tolerancia y fuentes bajo demanda.

La previsión conserva su símbolo propio; los huecos siguen sin evaluar. El resultado del
plan se refiere al muestreo posterior indicado, aunque el gráfico incluya todo el seguimiento.
Para trasladar la vista, copiar la carpeta de salida completa; los enlaces a originales
requieren acceso a su ubicación externa. No se requieren nuevas dependencias respecto a v1.

## Correcciones v3 · perfiles y catálogo (18/09/2026)

```powershell
py -3.11 .\prototypes\data-explorer\ver_correcciones_v3.py
```

Genera `out/correcciones-3212-v3/index.html`, con las mismas dependencias y opciones de v1.
Conserva los scripts y salidas anteriores.

- **Perfiles A/B:** matriz cavidad × muestreo con exceso, dos gráficas grandes y selección
  independiente de referencia y comparación. Los 144 recortes conservan ejes, cotas y escala
  del informe original; se detecta el marco vectorial del gráfico y se renderiza a mayor
  resolución. No se superponen ni se fuerza una escala común. El PDF completo queda en Fuentes.
- **Muestreos 01, 03, 05 y 08:** hay CSV en los cuatro; perfiles PDF solo en los tres primeros.
  El 08 permanece sin informe, sin convertirlo en cero ni OK.
- **Catálogo CSV:** 34 grupos de cotas y dos grupos de coordenadas, 3376 evaluaciones de
  16 CSV. Búsqueda, recuentos fuera de tolerancia y evolución por evaluación/cavidad. Las
  cabeceras compartidas, como N116/N260/N258, no se reparten entre cotas artificialmente.
- **Documentos:** se indexan las 54 acciones de ambos PPTX. Las asociaciones se obtienen
  de todos los campos `DIM. Nr.` del título o de correspondencias de imágenes ya revisadas;
  el método y la diapositiva quedan en Fuentes. Una asociación no confirma ejecución.
- **Correcciones contrastadas:** se conservan las fichas de N161, N240, N170 y N165, con sus
  previsiones XLS. Para las demás cotas, la previsión queda **sin revisar**, no «inexistente».

El catálogo descubre los bloques presentes en los CSV, pero la ingesta completa sigue
adaptada al **3212**: rutas, planes, correspondencias XLS y reglas de identidad metrológica.
`--raiz` permite trasladar sus datos; por sí solo no hace compatible cualquier otra pieza.
Las unidades angulares se mantienen en grados y los valores originales de las correcciones
de signo permanecen consultables. Los recuentos del catálogo son evaluaciones, no piezas.

## Buscador independiente del plano (18/09/2026)

```powershell
py -3.11 .\prototypes\data-explorer\buscar_en_plano.py --buscar N170
# Otro documento:
py -3.11 .\prototypes\data-explorer\buscar_en_plano.py --pdf "C:\Planos\pieza.pdf" --buscar N240
```

`buscar_en_plano.py` es una implementación nueva, independiente de `ver_todo.py` y de
`planos/ver_plano.py`. Genera `out/buscar-en-plano/index.html` e `indice.json`. El PDF del
3212 es el valor por defecto; `--pdf` acepta otro documento, incluidas varias páginas.

- Busca `N170` / `170`, permite incluir subcotas (`170.2`, `161.T`) y ofrece un modo
  separado **Texto / valor**. No confunde la coincidencia exacta N170 con N1700.
- Seleccionar un resultado centra y amplía el plano, con recorte de contexto. Se puede
  desplazar, ampliar, mostrar los globos y marcar una zona manualmente.
- **Texto PDF** procede de las palabras almacenadas en el documento. **OCR · revisar**
  es una lectura propuesta, nunca una ubicación confirmada automáticamente. **Revisada**
  aparece únicamente al confirmar una ubicación o importar revisiones del mismo PDF.
- Las revisiones se guardan en `localStorage` del navegador, vinculadas al SHA-256 del PDF.
  Exportar/importar JSON permite conservarlas o compartirlas; otra revisión del PDF se
  rechaza. No se escriben etiquetas sobre el original ni dentro del PDF.

La búsqueda utiliza PyMuPDF para texto y páginas; OpenCV para los globos verdes y azules;
el **lector combinado** para el número de cada globo; y Tesseract para el texto general del
escaneo. Los números OCR sueltos de las notas no se convierten en identificadores N: quedan en
Texto / valor. No hay coordenadas de N170/N161/N240 precargadas.

**Desde el 29/10/2026** (índice versión 3; versión 5 desde la tercera revisión). Lo que se mide en la
[ronda con examen](#ronda-con-examen-apartado-29102026) es lo que usa el buscador:
- **Vía vectorial**, si el PDF trae los globos como vectores.
- **Detector en dos pasadas.**
- **Orientación automática.**
- **Lector combinado**: RapidOCR más el lector propio `general`, con un número por plano.
- **Umbral de confianza por fuente del globo** (provisional): 0,434 en la capa vectorial y 0,6072 en la imagen. Ver [el ensayo](#correspondencia-globo-a-globo-y-ensayo-de-umbrales-29102026). Por debajo, el globo se marca pero queda «Sin lectura».

La lectura de cada globo indica su procedencia: combinada, RapidOCR y lector propio.

Comprobado con el índice regenerado:

| Plano | Ofrecidas bien | Ofrecidas mal | Sin lectura |
|---|---|---|---|
| 3212 (de 248 globos con referencia) | 162 | 8 | 78 |
| Índice del 28/10, mismo plano | 115 | 66 | 72 |
| 3205 `3205_balloned.pdf`, contra su `.icp` (de 89) | 88 | 1 | 0 |

En el 3212 se ofreció además una lectura en una detección que no es un globo. El índice del
28/10, sobre el que se hizo la lectura de referencia, queda congelado en
`out/buscar-en-plano/indice-2026-10-28.json` para `comparar_ocr_globos.py`.

El ensayo inicial con este PDF detecta **263 candidatos circulares**, no 263 cotas verificadas.
No es directamente comparable con los 178 componentes/racimos del visor antiguo. Hay
omisiones y lecturas incorrectas de dígitos y sufijos. La inspección comprueba ubicaciones
base de N170, N161 y N240; **no valida el resto ni acredita una tasa de acierto global**.
El escaneo continúa siendo la rev.07; localizar una cota no valida su equivalencia con rev.06.
La auditoría antigua de 6/16 corresponde al método anterior y no mide este nuevo método.

Dependencias: PyMuPDF, numpy, opencv-python, Pillow; OCR opcional con `pytesseract`, el
ejecutable Tesseract y `rapidocr-onnxruntime` (instalado en este equipo). El lector propio
necesita `torch`, que también está instalado, y el modelo `out/lector-globos/general/modelo.pt`.
El modelo se genera una vez con `entrenar_lector_globos.py --perfil general --muestras 100000`;
sin él, el buscador lee solo con RapidOCR y lo avisa. Sin esos motores siguen disponibles las
funciones que no los requieren. Opciones: `--sin-ocr`, `--reindexar`,
`--no-abrir` y `--salida`. La caché depende del contenido del PDF y de la versión del índice.
Los originales permanecen fuera del repositorio y los resultados están excluidos de Git.

### Búsqueda bajo demanda (28/10/2026)

- **Busca al pulsar Enter o la lupa**, no mientras se escribe. Antes saltaba por `1`, `17`…
- **La lectura principal va antes que las alternativas.** Un globo guarda hasta tres lecturas OCR.
  Si la buscada no es la principal, sale detrás como «Otra lectura · revisar» e indica cuál es
  la principal. Ejemplo: al buscar 133 aparece el globo 113.2, leído `133` y `132`.
- **Sin propuestas por vecindad (retiradas el 29/10/2026).** El 28/10 se proponían globos dudosos
  cercanos a N±1…N±3. Era una heurística para tapar un OCR que acertaba menos de la mitad, y el
  primer resultado era una propuesta errónea en 65 de 180 búsquedas. Ahora solo aparecen globos
  cuya lectura coincide. El camino es leer mejor: ver la comparativa siguiente.

**Referencia de medición.** Los 263 círculos detectados, leídos visualmente por Claude sobre
recortes ampliados el 28/10/2026. Eduard verificó una muestra al azar de 40: **40 correctas**
(`out/buscar-en-plano/verificacion-40.png`; la lectura completa está en
`chuleta-2026-10-28.json`, fuera de Git). Son 253 globos reales
y 10 detecciones que no corresponden a un único globo. El OCR del buscador da 115 lecturas
correctas, 66 incorrectas y 72 vacías.

**Por qué no cambiaba el OCR (28/10, superado por la comparativa del 29/10).** Las cifras miden unos 5 px de alto en la imagen del PDF. Se probaron
recortes sin aro ni líneas, ampliaciones ×3/×5/×8, canal rojo y banda central. Obtuvieron entre
104 y 132 lecturas correctas, a costa de más errores. Tampoco la unión de todas esas lecturas contiene
el número correcto en más de 158 de los 253 globos, y persiste la confusión 6→5 (`156`→`155`,
`186`→`185`…). Un clasificador rápido de dígitos con la tipografía del propio plano acertó 151
de 192 dígitos, pero solo segmentó bien 63 globos.
La lista de cotas de los XLS del 3212 no sirve como filtro: contiene 120 números base (113–295)
y omite globos reales del plano como 100–112, 183, 293 o 296. Por eso el índice no cambia y no
hace falta `--reindexar`.

**Supuestos que limitan el método:**

- Se buscan **globos circulares verdes o azules**. Otros planos pueden no tenerlos: en
  `Exemples` hay planos vectoriales con texto y sin globos (3197, 3051), y 19 planos con globos
  cuya posición y número están en `.icp`/`.prf` ([comparativa](../../conocimiento/comparativa.md),
  [ingesta](../../docs/ingesta-automatica.md)). La falta de círculo no implica que falte el
  número. Si está escrito, hay que leer la página entera. Si no lo está (3051, 3197), solo
  puede buscarse por el valor de la cota. Si existe el `.icp`, se usa en lugar del OCR.
  [Propuesta para la app](../../docs/ingesta-automatica.md#24-localizar-cotas-en-el-plano-2d-28102026).
- **Revisar los globos a mano está descartado**: los usuarios no lo harán.
- **Hay que trabajar con escaneos tal como están.** Se pidió el plano vectorial (A4) e INTEPLAST
  indicó que probablemente no lo tiene y que, en muchos casos, no dispone de una versión vectorial
  o SVG (comunicado por Eduard el 28/10/2026). Tampoco hay opción de pedir un escaneo mejor
  (Eduard, 29/10/2026). De los 20 planos únicos del estudio, 7 son escaneos.

## Comparativa de lectores de globos (29/10/2026)

¿Qué lee mejor los números de 5 px de los globos, sin LLM y en local? Mismos 263 círculos,
misma referencia; solo cuentan los 253 globos reales.

```powershell
# Lector propio: basta el Python del equipo (torch ya está instalado)
& $py "$s\entrenar_lector_globos.py"        # una vez; ~22 min en el portátil, sin datos del cliente
& $py "$s\comparar_ocr_globos.py" --lectores propio --desplazados --unicos
# Resto de motores: entorno aparte, fuera del repo y de OneDrive
$v = "$env:LOCALAPPDATA\inteplast\venv-ocr\Scripts\python.exe"
& $v "$s\comparar_ocr_globos.py" --listar
```

El entorno aparte se creó con `python -m venv --system-site-packages`, más `rapidocr`,
`onnxtr[cpu]`, `transformers`, `sentencepiece` y `easyocr --no-deps` con sus dependencias
menores. Los reconocedores PP-OCR en ONNX se descargan del catálogo de RapidOCR 3.10
(`modelscope.cn/models/RapidAI/RapidOCR/…/onnx/`) a `%LOCALAPPDATA%\inteplast\ocr-models`.
Nada de eso entra en el repositorio. Los resultados, con el detalle por globo, quedan en
`out/comparar-ocr/resultados.json` y `out/comparar-ocr-propio/resultados.json`.

**Aceptables ≤1 %** = cuántas lecturas, ordenadas por confianza, se pueden aceptar sin pasar
de un 1 % de errores. Los tiempos son orientativos: se midieron con otros procesos en marcha.

| Lector (vista de luminancia salvo indicación) | Aciertos | Errores | Vacíos | Aceptables ≤1 % | Tiempo |
|---|---|---|---|---|---|
| Buscador del 28/10 (PP-OCRv4, tres vistas) | 115 | 66 | 72 | — | — |
| PP-OCRv4 móvil, canal rojo | 120 | 52 | 81 | 7 | 8 s |
| PP-OCRv4 móvil | 126 | 52 | 75 | 16 | 8 s |
| PP-OCRv4 móvil + léxico | 133 | 120 | 0 | 41 | 97 s |
| PP-OCRv5 inglés, solo dígitos | 163 | 72 | 18 | 24 | 7 s |
| PP-OCRv6 small, solo dígitos | 167 | 70 | 16 | 70 | 4 s |
| PP-OCRv6 medium, solo dígitos | 178 | 63 | 12 | 81 | 247 s |
| docTR MASTER | 129 | 63 | 61 | 26 | 100 s |
| docTR PARSeq | 125 | 49 | 79 | 9 | 11 s |
| TrOCR base printed | 111 | 67 | 75 | 4 | 292 s |
| Tesseract, solo dígitos, `--psm 7` | 70 | 102 | 81 | 22 | 125 s |
| EasyOCR | 3 | 169 | 81 | 0 | 5 s |
| **Propio** (CRNN entrenada con sintéticos) | 205 | 48 | 0 | 156 | 2 s |
| Propio + 5 recortes desplazados | 218 | 35 | 0 | 148 | 7 s |
| **Propio + desplazados + un número por plano** | **227** | **26** | 0 | 148 | 7 s |
| Propio + léxico + desplazados + un número por plano | 229 | 24 | 0 | 153 | 153 s |

Resto de lo medido (en `resultados.json`): PP-OCRv5 latín 154, PP-OCRv5 chino 115, PP-OCRv4
inglés 141, PP-OCRv6 tiny 111, docTR CRNN 120/107, ViTSTR 83, SAR 110 y TrOCR small 101.
Los modelos PP-OCR *server* (v4 y v5) tardan 28 y 9 s por globo en este portátil: no se midieron.
EasyOCR devuelve uno o dos dígitos sueltos también con su detector: no es fallo de integración.

**Qué funciona, por orden de efecto:**

1. **Un lector propio pequeño, entrenado solo con números dibujados**
   ([`entrenar_lector_globos.py`](entrenar_lector_globos.py)). Es una CRNN de 0,24 M parámetros
   con CTC. Se entrena con 80.000 números 1–999, con sufijos `.1`–`.9`/`.T`, dibujados en
   15 tipografías de Windows (Arial, ISO, simplex, romans…). Las cifras miden 4–7 px y llevan
   aro, líneas cruzadas, globos vecinos, desenfoque y JPEG 4:2:0. Se recortan igual que los
   reales. **No ve ninguna lectura de la referencia**, que solo se usa para medir al final. Los
   lectores genéricos están entrenados con texto de otro tamaño y otra forma; este, con el caso
   concreto.
2. **Luminancia en vez de canal rojo.** El JPEG del plano guarda el color a media resolución
   (4:2:0), así que la luminancia es el canal nítido: 120 → 126 en PP-OCRv4 y 207 → 218 en el propio.
3. **Cinco recortes desplazados 1 px**, promediando sus lecturas: 205 → 218. Con cifras de 5 px,
   un píxel de recorte cambia el resultado de todos los lectores.
4. **Un número por plano**: asignación de máxima probabilidad conjunta (algoritmo húngaro), 218 → 227.
   Se basa en un hecho del plano: cada identificador aparece una vez, y en el 3212 no hay
   repetidos entre los 253. No usa posiciones ni numeración vecina.
5. **Léxico** (solo identificadores con forma válida, sin saber cuáles hay en el plano):
   +7 en PP-OCRv4, pero en el propio solo +2 y multiplica el tiempo por 20.

**Qué no compensa:** la comparación con plantillas (dibujar cada candidato en Arial y
correlacionarlo con el globo, `--sintesis`). Sola da 203; como desempate de los cinco primeros
candidatos, 230 frente a 229, y empeora la confianza (104 aceptables frente a 153). Tampoco los
modelos grandes: TrOCR o PP-OCRv6 medium tardan minutos y aciertan menos que el propio.

**Límites de la medición:**

- **Un solo plano**, y la referencia es una lectura visual (40/40 en la muestra verificada).
  Algunos «errores» pueden serlo de la referencia: 196/195, 36/35 o 134.1/154.1 son ambiguos a 5 px.
- De los 24 errores de la mejor configuración, **17 están en racimos de globos solapados**,
  5 tienen líneas sobre el texto y 2 son globos aislados con el 5/6 ambiguo. En los racimos, el
  círculo detectado no centra el texto que le corresponde.
- **≈150 de 253 lecturas** (59 %) se pueden aceptar con ≤1 % de error. El resto lleva una lectura
  probable que no es segura; cómo presentarla sin pedir revisión manual está por decidir.
- La detección sigue suponiendo **globos verdes o azules**.

**Este primer modelo no generaliza.** En los demás planos acierta el 33 %: ver la sección
siguiente.

## Prueba en todos los planos con globos (29/10/2026)

```powershell
& $v "$s\entrenar_lector_globos.py" --perfil amplio   # una vez; ~24 min en el portátil
& $v "$s\probar_lector_planos.py"                     # ~20 min; también con $py, sin PP-OCRv6
```

[`probar_lector_planos.py`](probar_lector_planos.py) recorre los PDF de planos de la biblioteca de
`conocimiento/`, detecta los globos de color, elige la orientación de la página y lee cada globo
con cinco lectores. Ninguno se reentrena con estos planos.

**Referencia automática, sin lectura manual.** 19 planos «ballooned» del 3202, 3205, 3206 y 3288 (1.992
globos) traen su `.icp` de infra-CONVERT con el número y la posición de cada sello. La
transformación a píxeles se ajusta en cada plano con RANSAC, y cada globo recibe el número del
sello más cercano. El 3212 se mide con la lectura visual del 28/10. Sin referencia quedan el 3167,
el 3195, el 3202 (plano A), el 3237, el 3238 y otro del 3288. En tres de ellos revisé a ojo una
muestra de 32 globos. El 3309 y el «Drw_Marking» del 3206 no tienen globos: el detector confunde
texto azul y resaltados con círculos.

| Lector | 19 planos con `.icp` | Rango por plano | Aceptables ≤1 % | 3212 (de 253) | Muestra visual (de 79) |
|---|---|---|---|---|---|
| OCR actual (RapidOCR, como el buscador) | 88,9 % | 76–98 % | 66 % | 115 | 60 |
| PP-OCRv6 small, solo dígitos | 81,3 % | 48–96 % | 42 % | 158 | — |
| Propio, primer modelo (perfil `3212`) | 33,3 % | 7–60 % | 7 % | 216 | — |
| Propio, perfil `amplio` | 79,6 % | 30–100 % | 56 % | 218 | 57 |
| **Combinado** (actual + amplio) | **95,5 %** | 81–100 % (mediana 99 %) | 72 % | 204 | 65 |

Los lectores propios leen aquí con el recorte centrado en la tinta (abajo), cinco desplazamientos
y un número por plano. Por eso el primer modelo da 216 en el 3212, frente a los 227 de la
comparativa con recorte fijo. «Combinado» promedia las puntuaciones del lector actual y del
amplio y después asigna un número por plano. La muestra visual son 79 globos válidos del 3167, el
3195 y el 3237 (de 96; el resto son detecciones que no corresponden a un único globo).

**Qué hizo falta para generalizar (sin datos del cliente):**

- **Recorte centrado en la tinta del número** (`fit_text`). En el 3212 el número ocupa un tercio
  del globo; en los de infra-CONVERT, casi todo, y el recorte fijo lo cortaba. Ahora se buscan
  los trazos oscuros del interior que no tocan el aro, y el recorte se escala a su altura.
- **Perfil sintético `amplio`**, con la misma red pequeña: cifras de 4 a 28 px, número de hasta
  el 80 % del globo, aros gruesos, globos rellenos y con pico, y rásteres nítidos sin JPEG.
- **Orientación y polaridad automáticas**: la página se gira hacia donde el lector está más
  seguro (dos planos venían girados), y un globo relleno con el número en blanco se invierte.

**Qué se ve:**

1. **Cada lector falla en cosas distintas.** El actual (RapidOCR) va bien con rásteres limpios y
   números grandes (88,9 %), pero no con el escaneo del 3212 (115 de 253). El propio es al revés.
   Juntos llegan al 95,5 % en los 19 planos.
2. **En el 3212 la combinación (204) queda por debajo del amplio solo (218)**: el lector actual se
   equivoca con mucha confianza y gana votaciones. Hay que ponderar cada lector según cuánto
   coincide con el otro en el mismo plano.
3. **Fallos que quedan en el amplio:** cifras muy gruesas (3202 «G»: 66 de 223), texto negro del
   dibujo encima del número (3237) y números de cuatro cifras, que pierden un cero al final
   (1660 → 166), porque el entrenamiento solo llega a 999.
4. **El detector necesita filtro**: en las muestras del 3195 y el 3167 (racimos densos y texto
   azul), 6 y 10 de 32 detecciones no son un único globo.

## Ronda con examen apartado (29/10/2026)

Cambios simples que no dependen de un plano concreto, diseñados mirando solo el **desarrollo**
(3205, 3206 y 3212, más el «Drw_Marking» del 3206 sin globos). El **examen** (3202, 3288, 3309 y
las muestras visuales del 3167, el 3195 y el 3237) no se miró hasta tener el código cerrado.

```powershell
& $v "$s\entrenar_lector_globos.py" --perfil general --muestras 100000   # ~24 min
& $v "$s\probar_lector_planos.py" --grupo desarrollo --salida "$s\out\probar-planos-desarrollo"
& $v "$s\probar_lector_planos.py" --grupo examen --salida "$s\out\probar-planos-examen"
& $v "$s\probar_lector_planos.py" --resumen "$s\out\probar-planos-desarrollo\resultados.json" "$s\out\probar-planos-examen\resultados.json"
```

1. **Vía vectorial.** En 20 de los 27 PDF con globos, los globos son vectores sobre un escaneo
   ([detalle](../../conocimiento/planos-globos.md#cómo-están-hechos-los-pdf-con-globos)). Se dibuja
   la página sin sus imágenes y quedan solo los globos y sus números. Se decide por cómo está hecho
   el PDF: tiene imágenes y al menos 200 trazados de color.
2. **Detector en dos pasadas.** Primero mide el tamaño típico de los globos de cada plano (radio
   del 0,3 al 3 % del lado), y después los busca de ese tamaño (0,6–1,6 veces la mediana),
   separados al menos un radio. Antes el tamaño era fijo y no veía los globos grandes del 3206.
3. **Perfil sintético `general`:** el amplio más negritas, trazo engrosado, números de hasta
   cuatro cifras, número negro en aro de color y texto negro del plano encima.
4. **Umbral de confianza único.** Fijado en desarrollo para no pasar del 2 % de lecturas
   ofrecidas erróneas, y aplicado tal cual al examen. Las detecciones que no son globo cuentan
   como error si dan lectura, pero solo donde está comprobado: lectura visual del 3212 y planos
   sin globos revisados a ojo. En los `.icp` hay sellos sin número ni posición, y una detección
   sin sello puede ser un globo real.

| Lector | Desarrollo (1.104 globos) | **Examen (1.169)** | Examen con umbral: bien / mal de las ofrecidas |
|---|---|---|---|
| OCR actual (RapidOCR) | 79,5 % | 88,5 % | 68,3 % / 3,0 % |
| Propio `amplio` | 91,1 % | 70,6 % | 56,3 % / 4,6 % |
| **Propio `general`** | 93,6 % | **90,3 %** | 77,8 % / **0,8 %** |
| **Combinado** (actual + `general`) | 94,2 % | **96,3 %** | **93,9 %** / 2,2 % |

Los lectores propios leen con cinco recortes desplazados y un número por plano. Las muestras
visuales del examen se leyeron a ojo. De 32 detecciones por plano, son globos válidos 31 en el
3195, 31 en el 3237 y solo 10 en el 3167:

| Lector | 3195 | 3237 | 3167 |
|---|---|---|---|
| OCR actual | 25 | 23 | 4 |
| `general` | 27 | 25 | 3 |
| Combinado | 28 | 28 | 4 |

**Qué se ve:**

- **El perfil `general` generaliza**: pasa del 93,6 % en desarrollo al 90,3 % en examen. El
  `amplio` se hundió (91,1 → 70,6 %) en el examen, que tenía negritas y cuatro cifras que no
  había visto.
- **La combinación sigue siendo lo mejor**, la misma para todos los planos. El `general` solo
  ofrece menos lecturas, pero se equivoca menos: 0,8 % de las ofrecidas frente a 2,2 %.
- **La vía vectorial resuelve el 3206 `213137-01028-10`**, que antes no se detectaba: 38 de 38
  con `general`. En los planos vectoriales, `general` acierta entre el 92 y el 100 % en
  desarrollo y entre el 72 y el 100 % en examen; el 72 % es el 3202 «G».
- **Puntos débiles:**
  - 3202 «G», con negritas muy gruesas: 159 de 222 con `general` y 198 combinado.
  - 3212: 206 de 248 con `general`, frente a 227 de 253 con el primer modelo y recorte fijo.
  - **3167**, ráster de baja resolución con texto azul: 22 de 32 detecciones no son globos, y
    los números de cuatro cifras pierden la última. La primera pasada encuentra sobre todo
    círculos pequeños (mediana de 12 px entre todos los candidatos, cuando los globos miden unos
    19), porque los huecos de las cifras («0», «6») también parecen aros. Así salen 158
    detecciones, frente a 293 con el detector anterior. Arreglado después: ver abajo.

### Arreglo del tamaño típico y cierre (29/10/2026)

Para medir el tamaño típico de los globos ya no cuentan los círculos que caen dentro de otro,
como los huecos de un «0» o un «6». Hay un test que reproduce el caso: sin el arreglo, el
detector se queda con círculos de 15 px en vez de con los globos de 22.

El arreglo nace de haber visto el 3167, que era plano de examen. Por eso se comprobó así:
- **Desarrollo:** los planos detectan exactamente lo mismo que antes.
- **Planos con `.icp`:** resultados prácticamente iguales. El combinado se queda en el 94,2 %
  en desarrollo y el 96,3 % en examen, y las lecturas ofrecidas erróneas en examen bajan de 25 a 23.
- **Umbral:** se mantiene en 0,412.
- **3167**, en una nueva muestra de 32 leída a ojo (ya no es examen limpio):
  - pasa de 158 a 239 detecciones, con radio típico de 21 px frente a 15;
  - son globos válidos 30 de 32, frente a 10;
  - aciertan 23 el combinado, 21 el OCR actual y 20 `general`.

El buscador (`buscar_en_plano.py`) usa todo esto: vía vectorial, detector en dos pasadas,
orientación automática y lector combinado con umbral. **No cubre**:
- globos grises o negros;
- la numeración del cliente en recuadros o etiquetas;
- la búsqueda por valor en planos sin número;
- la lectura directa de los `.icp`.

Una revisión posterior corrigió este resumen y la forma de medir: ver la sección siguiente.

## Evaluación revisada (29/10/2026)

Tras una revisión del trabajo, se corrigen afirmaciones, fallos de código y la forma de medir.

**Correcciones a lo dicho antes:**
- «Los demás planos no cambian» era falso para el 3309, sin globos. Sus detecciones falsas pasaron
  de 52 a 70, aunque las lecturas falsas ofrecidas bajaron de 4 a 2.
- El 96,3 % era solo sobre los globos detectados y emparejados. Sobre todos los sellos del `.icp`
  del examen se ofrecían bien 1.098 de 1.193, un 92,0 %.
- El paso de 10/32 a 30/32 en el 3167 comparaba muestras distintas. Mide la limpieza de las
  detecciones, no cuántos globos reales se recuperan.
- **El «examen» no es limpio.** El perfil `general` se diseñó después de ver fallos del 3202 «G»,
  del 3167 y del 3195. Los planos actuales son un banco de desarrollo y regresión. Para afirmar
  que generaliza hacen falta planos nuevos, no usados para decidir nada. Abajo, «grupo A» y
  «grupo B» corresponden a lo que antes se llamó desarrollo y examen.

**Fallos de código corregidos, cada uno con su test:**
1. **Globos vectoriales que podían perderse.** `page_raster` usaba la imagen de fondo sin mirar
   si había trazados encima. Ahora solo la usa si es lo único que hay en la página y la ocupa
   entera, sin girar ni voltear. *(La regla del 80 % que se añadió aquí comparaba cantidades y
   podía perder globos; la sustituyó la correspondencia globo a globo: ver la sección siguiente.)*
2. **Sin torch, el buscador sigue solo con RapidOCR** en vez de fallar.
3. **La caché del índice depende también del modelo** (su huella SHA-256) **y del umbral.**
4. **Un único umbral.** `buscar_en_plano.COMBINED_THRESHOLD` es el valor exacto que elige el
   evaluador, y este avisa si dejan de coincidir.
5. **Tests de la segunda pasada del detector**, con tamaños mezclados alrededor del típico, y de
   la limitación conocida: con dos familias de globos muy distintas, se queda con una.

**Cómo se mide ahora** (`probar_lector_planos.py`):
- Sobre **todos** los globos de referencia: cuántos se detectan y emparejan, aciertos y
  **cobertura**, es decir, globos con su número bien ofrecido.
- Las detecciones sin referencia son **pendientes**, ni buenas ni falsas. Solo son falsas las
  comprobadas: lectura visual o plano sin globos revisado a ojo.
- La **calibración `.icp` → página se calcula una vez y se guarda**
  (`out/probar-planos-calibracion.json`). Ya no depende de los lectores que se evalúan.
- Entran **todas las páginas con referencia**, aunque no tengan detecciones. Las que tienen
  `.icp` y ninguna detección resultaron ser las versiones sin globos guardadas junto a las
  globadas (`3205.pdf`, `3205-A.pdf`, `3206.pdf`, `3202.pdf`…). *(Corregido después: ahora se
  declaran por página, con su evidencia, y cualquier otra página con referencia y sin detecciones
  cuenta como cobertura perdida. Ver la sección siguiente.)*
- Cada ejecución guarda su configuración (`configuracion.json`): modelos, umbral y versión.

**Referencia fija del 3167**, `out/referencia-3167/chuleta-3167-2026-10-29.json`. Se juntaron los
candidatos de tres detectores: el actual, el antiguo del 28/10 y uno permisivo (323 en total).
Después leí a ojo cada uno y repasé el plano por cuadrantes sin encontrar globos sin candidato.
Resultado: **212 globos legibles**, 50 candidatos que no son globo y 61 dudosos en racimos
ilegibles a esta resolución, que quedan fuera. La lectura es mía y no está verificada. Comparación
de detectores sobre esa referencia:

| Detector | Globos legibles encontrados (de 212) | Candidatos que no son globo |
|---|---|---|
| Actual (dos pasadas) | 198 | 1 |
| Separación entre centros de 0,5 radios | 202 | 4, y 32 dudosos más |
| Antiguo (28/10) | 204 | 11 |
| Permisivo | 204 | 43 |

Los 14 globos que pierde el actual están casi todos en parejas solapadas. Reducir la separación
recupera 4, pero añade detecciones falsas y dudosas, y en los planos de desarrollo no cambia nada.
Se mantiene el detector actual.

**Resultados con el umbral 0,434**, elegido en el grupo A con como máximo un 2 % de lecturas
ofrecidas erróneas:

| Lector | Grupo | Referencias | Emparejadas | Aciertos | Cobertura | Mal ofrecidas |
|---|---|---|---|---|---|---|
| Combinado | A (3205, 3206, 3212) | 1.126 | 98,0 % | 94,2 % | 88,6 % | 2,0 % |
| Combinado | B (3202, 3288, 3167) | 1.405 | 97,3 % | 94,1 % | **89,0 %** | 3,0 % |
| `general` solo | B | 1.405 | 97,3 % | 87,7 % | 73,7 % | 1,1 % |
| OCR actual | B | 1.405 | 97,3 % | 86,5 % | 65,6 % | 3,9 % |

`general` solo usa su propio umbral (0,7226) y OCR actual el suyo (0,9326); ambos se eligen igual,
en el grupo A con como máximo un 2 % de lecturas ofrecidas erróneas. Así se calcula cada columna:
- **Aciertos:** sobre los globos emparejados, sin umbral.
- **Cobertura:** bien ofrecidas sobre las referencias.
- **Mal ofrecidas:** errores y falsos sobre lo ofrecido.

Por tipo de plano, con el combinado:

| Tipo | Planos | Cobertura | Mal ofrecidas |
|---|---|---|---|
| Vectoriales | 3205, 3206, 3288 y 3202 salvo el «G» | 90–100 % | 0–3 % |
| 3202 «G», negritas muy gruesas | — | 82 % | 5,1 % |
| Ráster | 3206-A lr | 89 % | 5,2 % |
| Ráster | 3202 lr | 85 % | 3,5 % |
| Ráster | 3212 | 64 % | 4,7 % |
| Ráster | **3167** | 72 % | **10,6 %** |

**Lo que queda abierto:**
- **El umbral no es una probabilidad calibrada.** En rásteres pobres el combinado se equivoca
  bastante más que la media. Una opción simple sería un umbral por tipo de fuente (capa vectorial
  o imagen) elegido igual, en el grupo A. Hay que decidirlo.
- Un número por plano y un tamaño de globo dominante por página son supuestos. Se cumplen en los
  datos actuales (ninguno de los 19 `.icp` repite números), pero no están garantizados.
- Generalización: hacen falta planos nuevos.

## Correspondencia globo a globo y ensayo de umbrales (29/10/2026)

Segunda revisión. Se corrigen dos fallos y se ensaya un umbral por fuente **sin cambiar el
buscador**, que sigue en 0,434.

**1. Fuente decidida globo a globo** (`buscar_en_plano.balloon_source`). La regla del 80 %
comparaba cantidades: con 8 globos vectoriales y 2 dentro del escaneo, se quedaba con los 8. Ahora:
- **Detección:** se detecta en la capa vectorial, a su resolución de siempre (hasta 600 ppp), y en
  la página completa, a la de su escaneo. Las coordenadas pasan a una escala común.
- **Emparejado uno a uno** (`pair_balloons`): solo valen los pares con los centros a menos de medio
  radio del mayor. Entre los válidos, del más cercano al más lejano. *(Corregido después de la
  segunda revisión: la primera versión cortaba la búsqueda en el primer par no válido. Como el
  límite depende de los radios de cada par, un par pequeño rechazado podía impedir uno grande
  válido y duplicar un globo. En los 20 planos con capa vectorial no cambiaba ningún emparejamiento.)*
- **Fuente:** los emparejados y los que solo están en la capa se leen en la capa. Los que solo
  están en la imagen se leen en la imagen. Cada globo lleva su `fuente`.
- **Imagen de trabajo:** la página completa, con la capa hasta 1,6 radios alrededor de cada globo
  vectorial, sin pisar los que solo están en la imagen.
- **Tests:** 8 vectoriales y 2 en el escaneo dan 10, sin duplicados. Un globo que solo se ve en la
  capa (sobre una franja de color del escaneo) se conserva. Pocos círculos de un solo trazado,
  también.
- **Índice del buscador:** pasa a la versión 4.

Una primera versión dibujaba la capa a la resolución del escaneo y solo tomaba la capa hasta 1,1
radios. Perdía lecturas en el 4091, el 3049 y el 1937. Se corrigió volviendo a los recortes de
antes para los globos vectoriales. Conviene que conste que la regresión se vio en planos del
grupo B.

**2. Páginas sin globos declaradas por página, con su evidencia** (`NO_BALLOON_PAGES`,
[detalle](../../conocimiento/planos-globos.md#cómo-están-hechos-los-pdf-con-globos)). Son 15 páginas, revisadas a ojo.
- **No dependen del detector ni del color.** Prueban que los globos del `.icp` de su carpeta no
  están ahí, no que no haya ninguna numeración.
- **No aportan referencias,** pero cualquier lectura que se ofrezca en ellas cuenta como falsa.
- **Cualquier otra página con referencia y sin detecciones** suma todas sus referencias al
  denominador.

**3. Lecturas pendientes ofrecidas.** Son las que superan el umbral en detecciones sin referencia.
Se muestran aparte y no entran en el porcentaje de errores, que solo cuenta lo evaluable.

**4. Trazabilidad.**
- **Calibración:** ligada a la página y a las huellas SHA-256 del PDF y del `.icp`. Las 20
  calibraciones las tienen ya.
- **Resumen** (`--resumen … --resumen-salida`): guarda los umbrales elegidos, los ficheros de
  entrada con su huella y las páginas declaradas.
- **Comparación** (`--comparar ANTES DESPUES`): por plano y agregada, y marca las regresiones.

**5. Ensayo de umbrales** para el combinado, en el grupo B. Son los planos 3202, 3288 y 3167, que,
como se dijo, no son un examen limpio.

| Política | Cobertura | Mal ofrecidas | Pendientes ofrecidas |
|---|---|---|---|
| Un umbral, 0,434 (el del buscador) | 89,1 % | 38 (2,9 %) | 69 |
| Por fuente: capa 0,434, imagen 0,6072 | 84,8 % | 14 (1,2 %) | 64 |

En el grupo A: 88,9 % y 2,0 % con un umbral; 83,5 % y 1,1 % por fuente. El 0,6072 es el umbral
que se elige en A solo con globos de imagen. El vectorial no se baja automáticamente: saldría
0,0321, demasiado permisivo, y el 3202 «G», que es vectorial, pasaría de 10 a 22 errores.

Por plano, con el umbral por fuente solo cambian los de imagen:

| Plano | Bien (un umbral → por fuente) | Mal | Pendientes ofrecidas |
|---|---|---|---|
| 3212 | 162 → 111 | 8 → 3 | 1 → 0 |
| 3167 | 152 → 126 | 18 → 0 | 4 → 0 |
| 3202 lr | 193 → 160 | 7 → 1 | 8 → 7 |
| 3206-A lr | 55 → 45 | 3 → 0 | 6 → 6 |
| 3202 «G» (vectorial) | 185 → 185 | 10 → 10 | 7 → 7 |

**Lo que muestra el ensayo:** el umbral por fuente mejora la fiabilidad porque se abstiene más, no
porque lea mejor. El caso difícil vectorial, el 3202 «G», no cambia. El 0,6072 sale de solo dos
planos de imagen con referencia en A, así que no se fija como definitivo. Con un solo umbral, el
evaluador sigue eligiendo 0,434 en A. *(Corregido: una versión anterior de esta sección decía
0,391. Ese valor salió de una medición intermedia que dejaba fuera los falsos de las páginas sin
globos. Con ellos contados, 0,391 daría en A 1.003 bien y 24 mal, más del 2 % permitido.)*

**Antes y después, con las mismas referencias y los mismos umbrales**
(`out/resumen-antes.json` y `out/resumen-despues.json`):

| Grupo | Cobertura | Mal | Pendientes ofrecidas |
|---|---|---|---|
| A | 88,6 % → 88,9 % | 20 → 20 | 63 → 63 |
| B | 89,0 % → 89,1 % | 38 → 38 | 68 → 69 |

Ganancias:
- 3206 `213137-01028-10`: +2. Dos globos que solo se ven en la imagen.
- 3206 `3206_balloned.pdf`: +1.
- 3288 `BSG-296-01`: +1.
- 3288 `BSG-296-00`: +1.

**No hay regresiones.** El efecto en los planos actuales es pequeño: la correspondencia arregla un
fallo que aquí casi no se daba, pero que con otros planos podía perder globos.

**Verificación pendiente de la referencia del 3167** (`muestra_verificacion.py`, para Eduard):
- `out/referencia-3167/verificar-aleatoria.png`: 40 al azar entre las 262 entradas juzgadas. Es la
  única muestra que estima la fiabilidad de la referencia.
- `out/referencia-3167/verificar-racimos.png`: 20 globos en racimos. Sirve para buscar fallos, no
  para estimar.
- Los errores del lector frente a la referencia están en
  `out/probar-planos-v5-examen/errores-3968-p1.png`.

La anotación se hace en `verificar.json`.

**Sigue abierto:**
- Decidir el umbral por fuente.
- Verificar la referencia del 3167.
- Probar con planos nuevos que no se hayan usado para ajustar nada. Sin ellos no se puede afirmar
  que el método generalice.


### Tercera revisión: emparejamiento, anotaciones y umbral por fuente aplicado (29/10/2026)

- **Emparejamiento** (`pair_balloons`). Se filtran los pares válidos antes de ordenarlos, así que un
  par pequeño rechazado ya no corta la búsqueda. Lo cubre un test con radios distintos, que falla
  con el código anterior. En los 20 planos con capa vectorial, ninguna página cambia: ni en
  detecciones, ni en fuente, ni en lecturas.
- **Anotaciones protegidas** (`muestra_verificacion.py`):
  - Estados: vacío (pendiente), `ok`, `corregido` (con `lectura_correcta`) y `dudoso`.
  - Regenerar conserva lo anotado. Si se perdieran filas ya anotadas, no escribe salvo con
    `--forzar`.
  - `--estado` muestra el recuento y los errores de formato.
- **Umbral por fuente aplicado provisionalmente en el buscador**:
  `COMBINED_THRESHOLDS = {"capa vectorial": 0,434, "imagen": 0,6072}`.
  - Cada globo usa el de su fuente, también en páginas mixtas. Lo cubre un test.
  - Los dos valores entran en la firma de la caché; el índice pasa a la versión 5.
  - El evaluador usa esos valores exactos y avisa si en el grupo A se eligen otros. Ahora coinciden.
  - Comprobado de punta a punta:
    - 3212: ofrece 114 lecturas, que son las 111 bien y 3 mal que predice la evaluación.
    - 3113, página mixta: 28 globos de la capa y 1 de la imagen.

Antes y después, con las mismas referencias y los mismos umbrales (v4 → v6):

| Política | Grupo | Cobertura | Mal ofrecidas | Pendientes ofrecidas |
|---|---|---|---|---|
| Un umbral, 0,434 | A | 88,6 % → 88,9 % | 20 → 20 (2,0 %) | 63 → 63 |
| Un umbral, 0,434 | B | 89,0 % → 89,1 % | 38 → 38 (3,0 % → 2,9 %) | 68 → 69 |
| **Por fuente (la del buscador)** | A | 83,2 % → 83,5 % | 10 → 10 (1,1 %) | 62 → 62 |
| **Por fuente (la del buscador)** | B | 84,8 % → 84,8 % | 14 → 14 (1,2 %) | 63 → 64 |

No hay regresiones en las lecturas evaluables. Los 53 tests del prototipo pasan.

**Limitaciones pendientes:**
- **64 lecturas pendientes ofrecidas en B,** sin referencia. No se sabe si son globos reales sin
  sello o detecciones falsas.
- **3202 «G»** (vectorial, negritas): sigue con 10 lecturas erróneas de 195 ofrecidas. El umbral
  por fuente no lo toca.
- **El umbral de imagen sale de solo dos planos con referencia** en A. Mejora la fiabilidad porque
  se abstiene más: en el 3212 se ofrecen 114 lecturas en vez de 171.
- **Referencia del 3167** sin verificar: a la espera de la muestra aleatoria y la de racimos.
- **Generalización** sin demostrar: hacen falta planos nuevos, apartados antes de ajustar nada más.
- **Supuestos no garantizados:** un número por plano y un tamaño de globo dominante por página.

### Estado: prototipo revisado y congelado (30/10/2026)

**Prototipo revisado, con umbrales provisionales; pendiente de validar la referencia del 3167 y la
generalización.** Último ajuste: `muestra_verificacion.py` comprueba primero que no se perderían
anotaciones y solo después escribe las hojas y `verificar.json`. Si se niega, no cambia ninguno de
los tres ficheros, y lo cubre un test. Pasan los 54 tests del prototipo.

Para no sobreajustar, el detector y los lectores no se tocan más sobre estos mismos planos sin
evidencia nueva: la verificación del 3167 o planos nuevos apartados. El 1,2 % de errores se
refiere a las lecturas evaluables. Siguen abiertas las 64 lecturas ofrecidas sin verificar y el
3202 «G». La integración en la aplicación se puede preparar manteniendo esas limitaciones a la vista.
