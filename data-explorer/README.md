# `data-explorer/` — visores de los datos crudos

Scripts para **ver** los datos en vez de leer descripciones. Generan un **índice con árbol de
carpetas** y **una página por resultado**.

Están repartidos en dos carpetas según de dónde salga el dato:

```
data-explorer/
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
│   └── obj-c13.html               ← los objetivos de retoque superpuestos
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
$s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\data-explorer"

& $py "$s\ver_csv.py"                    # genera el HTML y lo abre en el navegador
& $py "$s\ver_txt.py"
```

> 📁 **Dónde vive esto.** Estos visores son **utilidades de exploración de los datos crudos**, no
> parte de la aplicación: no comparten nada con `backend/` ni con `frontend/`, y por eso están en
> `data-explorer/` y no en `scripts/` (que es el de build y test del template FastAPI).
> El puntero a esta carpeta está en [`../docs/visores.md`](../docs/visores.md) y en
> [`../CLAUDE.md`](../CLAUDE.md).
>
> 🔴 Los **datos** que lee siguen fuera del repo, en
> `…\Escritorio\proyectos\11. inteplast\Exemples` (ruta absoluta en la cabecera de cada script).

Python 3.11.8 con `pandas`, `numpy` y `plotly` 6.6 ya instalados — no hace falta `pip install`.

⚠️ **`ver_plano.py` usa Tesseract**, que 🔴 **no está en el PATH**: el script lo busca solo en
`C:\Program Files\Tesseract-OCR\`. Sirve para el texto del plano (notas y cotas).

🔴 **No sirve para los números de dentro de los globos, y RapidOCR tampoco** (acierta el 37 % y
falla con 0,99 de confianza). Esa parte **se quitó a propósito**: ver
[`docs/visores.md`](../docs/visores.md). No volver a intentarlo con este PDF.

### Opciones

```powershell
& $py "$s\ver_csv.py" --no-abrir           # no abrir el navegador
& $py "$s\ver_csv.py" --corregir-signo     # invierte el error de signo de B2/B4
& $py "$s\ver_txt.py" --familia nous       # solo los puntos objetivo
& $py "$s\ver_txt.py" --muestreo 01 --cavidad c13
& $py "$s\ver_txt.py" --max-puntos 12000   # más detalle (y más peso)
& $py "$s\ver_csv.py" --raiz "D:\otra\ruta\4- Metrologia"
```

Los dos apuntan por defecto a la ruta absoluta de los datos del 3212, que **no está en este
repo**:

```
C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\proyectos\11. inteplast\Exemples\3212 Pump Housing\4- Metrologia
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
   muestreos. Una fila que pasa de roja a verde es **un retoque de molde que funcionó**. Debajo,
   las 15 cotas que más se movieron en mm reales.

### `ver_txt.py` — las nubes de puntos

Árbol de dos niveles: muestreo → cavidad → los 3 ficheros de esa cavidad (perfil, `PUNTS`,
`PUNTS_NOUS`). Cada página trae la **nube 3D** (arrastra para rotar, color = altura Y) y la
**vista en planta X-Z**, con las estadísticas reales (nº de puntos, bounding box, niveles de
altura detectados). Al final, una carpeta con los **puntos objetivo de cada muestreo
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
  mala**. Se marca en el hover; `--corregir-signo` lo invierte.
- **Nombres inconsistentes**: `3212_c13.csv`, `3212c14.csv`, `13_3212.csv`. Y en `intern.05` las
  carpetas `c15/` y `c16/` tienen ficheros con el **mismo nombre**, así que la cavidad se deduce
  de la carpeta padre.
- **Los 4 muestreos con CMM traen los mismos 114 bloques y 211 filas**: el programa de la máquina
  nunca cambió, por eso las vistas 2 y 3 pueden alinear fila a fila.

- **Cada CSV es UNA pieza**, no un promedio: `3212c14.csv` son las medidas de la única pieza que
  salió del hueco 14 en esa tanda. Los `MIN`/`MAX` que se repiten por todo el fichero son el
  valor mínimo y máximo **del mismo elemento en la misma pieza** (así se detecta la ovalidad).

Todo el detalle está en el vault de notas, `C:\edu\projects\Inteplast`:
`docs/formatos-parsing.md`, `docs/3212/4-metrologia.md` y `docs/visores.md`.

---

## Detalle técnico: por qué una página por resultado

La primera versión encadenaba los 84 gráficos en un solo HTML de 15 MB. Además de ser imposible
de navegar, **no funcionaba**: cada figura de Plotly consume un **contexto WebGL** y Chrome solo
permite ~16 simultáneos, así que los primeros gráficos se quedaban en blanco.

Partirlo en una página por resultado lo resuelve de raíz —1 o 2 gráficos por página— y de paso
hace que el índice cargue al instante. `plotly.min.js` se escribe **una sola vez** en
`out/vendor/` y las 68 páginas lo referencian con una ruta relativa, en vez de llevar 4,9 MB de
librería embebidos cada una.

⚠️ Eso implica que **las páginas necesitan estar junto a su carpeta `vendor/`**: si mueves un
HTML suelto a otro sitio, se queda sin librería y no pinta nada. Mueve `out/` entera.
