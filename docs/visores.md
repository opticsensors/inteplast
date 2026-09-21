# Visores de los datos crudos — dónde está el código

> 📁 **El código vive en este mismo repo**, en `prototypes/data-explorer/`. No en
> `scripts/`, que es el de build y test del template FastAPI.
>
> ```
> C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\prototypes\data-explorer
> ```
>
> Este documento es el resumen: qué hay allí, qué hace y qué decisiones lleva dentro.
> La documentación de uso completa está en el [`README.md` de esa carpeta](../prototypes/data-explorer/README.md).

Son prototipos independientes de la web. Los lectores de la aplicación se mantienen
en `backend/app/ingestion/`; Docker no incluye la carpeta `prototypes/`.
>
> 🔴 Los **datos** que lee sí están fuera del repo, en
> `…\Escritorio\proyectos\11. inteplast\Exemples`.

---

## Qué hay

| Fichero | Qué hace |
|---|---|
| **`ver_todo.py`** | **Punto de entrada.** Ejecuta los cuatro visores y genera `out/index.html`, donde se elige CSV, TXT, PDF o plano |
| `metrologia/ver_csv.py` | Los **16 CSV de cavidad** → árbol + 24 páginas |
| `metrologia/ver_txt.py` | Las **40 nubes de puntos** `.txt` → árbol + 44 páginas |
| `metrologia/ver_pdf.py` | Las **144 gráficas de contorno** en PDF → árbol + 148 páginas + 144 PNG |
| `planos/ver_plano.py` | Plano 2D con búsqueda de texto OCR y globos localizados |
| `README.md` | Uso, opciones y las trampas de los datos que los scripts ya resuelven |
| `out/` | Lo generado (~42 MB). **Ignorado en git**, se rehace en un par de minutos |

```
out/index.html            ← SE ABRE ESTO: elegir entre los cuatro
 ├── csv-3212.html        las cotas medidas y comparadas contra el plano
 ├── txt-3212.html        las nubes de puntos en bruto
 ├── pdf-3212.html        el perfil interior contra el contorno teórico
 └── plano-3212.html      el plano 2D y su texto OCR
```

## Cómo se ejecutan

🔴 **Python no está en el PATH** — el `python.exe` de la consola es el stub de la Microsoft Store
y falla. Hay que llamarlo por ruta absoluta:

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
$s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\prototypes\data-explorer"

& $py "$s\ver_todo.py"                 # genera los cuatro y abre la pantalla inicial
& $py "$s\ver_todo.py" --solo pdf      # regenera solo uno
& $py "$s\metrologia\ver_csv.py" --corregir-signo # invierte el error de signo de B2/B4
& $py "$s\metrologia\ver_txt.py" --familia nous --muestreo 01
& $py "$s\metrologia\ver_pdf.py" --zoom 2.0       # render de los PDF más grande
```

Python 3.11.8 con `pandas`, `numpy` y `plotly` ya instalados. → [CLAUDE.md](../CLAUDE.md)

⚠️ `ver_txt.py` **hidrata ficheros de OneDrive** (36 de los 40 `.txt` son placeholders, ~22 MB).
La primera pasada tarda un par de minutos.

---

## Qué muestran

**`ver_csv.py`** — árbol con una carpeta por muestreo (`intern.01`, `.03`, `.05`, `.08`) y sus 4
cavidades, más dos carpetas de comparativas al final:

1. **Un fichero medido**: una barra por característica, en el orden real del fichero. El eje X va
   en **fracción de la tolerancia consumida** (`0` = nominal, `±1` = límite) para poder comparar
   en el mismo gráfico cotas de ±0,5 mm y de ±0,02 mm. El hover da los mm reales.
2. **Comparar las cavidades entre sí** (una página por muestreo): separa un problema del molde
   entero de uno de una sola cavidad.
3. **Comparar los muestreos entre sí** (una página por cavidad): heatmap 211 cotas × 4 muestreos.
   Una fila que pasa de roja a verde es una medición que entró en tolerancia; el historial
   permite estudiar si el cambio corresponde a un retoque.

**`ver_txt.py`** — árbol de dos niveles (muestreo → cavidad → los 3 ficheros de esa cavidad).
Cada página trae la nube 3D girable y la vista en planta, con el nº de puntos, el bounding box y
los niveles de altura detectados. Al final, los subconjuntos PUNTS_NOUS de cada muestreo superpuestos.

**`ver_pdf.py`** — árbol de dos niveles (muestreo → cavidad → las 12 gráficas). Cada página lleva
los 6 números extraídos, una barra que sitúa la desviación respecto a la banda de tolerancia, y
**la página del PDF renderizada** para juzgar la gráfica original al lado del dato. Al final, la
evolución del contorno por cavidad a lo largo de los muestreos.

**`ver_plano.py`** — una sola página con el plano completo: se teclea una cota y **el plano la
marca**, con zoom y arrastre. El plano es un escaneo sin texto, así que lo que se busca es una
capa reconstruida con Tesseract (1.504 palabras, confianza media 74). Además localiza los
**178 globos de N-number** y vuelca el texto a `out/plano/texto-3212.txt`.
→ detalle abajo, en *Lo que confirmaron sobre los datos*.

---

## Decisiones que llevan dentro (y por qué)

- **Los `totes.csv` se excluyen**: no traen desviación ni semáforo. → [formatos-parsing.md](formatos-parsing.md)
- **La cavidad se deduce de la ruta completa**, no del nombre: en `intern.05` las carpetas `c15/`
  y `c16/` tienen ficheros con el mismo nombre.
- **Las cabeceras repetidas se numeran** (`N170 BOLT 1 … H=5.0 mm` sale dos veces): sin eso el
  cruce entre muestreos se multiplica y falla.
- **El error de signo de B2/B4 se marca por defecto**. `--corregir-signo` recalcula también
  desviación, exceso y NOK, conservando los valores originales del export.
- **Una extracción PDF incompleta queda sin evaluar**: la página explica qué campos faltan y
  los gráficos dejan un hueco. No se muestra un OK por ausencia de datos.
- **Las fechas no salen en la interfaz**: los muestreos ya se ordenan por número, y lo relevante
  de cada uno es qué pasó antes (el retoque de molde). Las fechas viven en
  [3212/historial-molde.md](3212/historial-molde.md).
- **Una página por resultado, no scroll infinito**: además de navegarse mejor, evita el límite de
  ~16 contextos WebGL del navegador, que dejaba gráficos en blanco.
- **El plano se busca por *variantes normalizadas*, no por texto crudo**: el OCR lee `Ø40,3`
  como `940.3` (la `Ø` sale como `9`/`@`/`$`), así que cada palabra genera varias formas
  posibles y se comparan conjuntos. Sin eso, buscar una cota no encuentra nada.
- **La búsqueda de varias palabras encadena por posición**: el OCR da una caja por palabra
  suelta, así que `PRESSURE TEST` se resuelve buscando palabras contiguas en la misma banda, no
  comparando contra una sola caja. Y el mínimo de 3 caracteres por lado en las coincidencias
  parciales es lo que evita que buscar `TEST` marque cada `T` que el OCR saca de las líneas.
- **Los globos de N-number se localizan pero NO se leen**: ver abajo.
- **El PNG de cada PDF lleva muestreo + cavidad + elemento en el nombre**: los 144 PDF se llaman
  todos `PA_1`…`PB_6`, así que un nombre derivado solo de la carpeta hace que los de un muestreo
  **sobrescriban** a los de otro y cada página acabe mostrando la gráfica de otra tanda. Pasó, y
  el síntoma es silencioso: los enlaces siguen funcionando. La comprobación que lo caza es
  **contar imágenes distintas**, no solo que existan.

---

## Lo que confirmaron sobre los datos

🆕 **Cada CSV es UNA pieza, no un promedio.** `3212c14.csv` son las medidas de la única pieza que
salió del hueco 14 en esa tanda. Evidencia:

1. Las **12 gráficas de contorno** de una cavidad están tomadas en una **sesión continua de 4
   minutos** (10:50 → 10:54): no da tiempo a desmontar y realinear piezas distintas.
2. El `.igs` de esa misma carpeta lleva el timestamp `240119.105452` — el cierre de esa sesión.
3. El `DR(3D)` del XLS tiene **una sola columna por cavidad**.
4. `HISTORY` de `intern.09` anota *"Update to 5 pcs"*, señal de que hasta entonces era una.

📌 Los **MIN/MAX** que aparecen por todo el CSV **no son dos piezas**: son el valor mínimo y
máximo del mismo elemento en la misma pieza (el diámetro más estrecho y el más ancho del mismo
agujero, que es como se detecta la ovalidad).

---

## 🔴 El plano 2D: los N-numbers NO se pueden leer. Hay que pedir otro plano

Actualizado el **2026-08-18** tras tres intentos. Esta sección corrige a las dos anteriores.

### La conclusión

El plano numera las características en **globos de color** (`170`, `170.2`… = N170 y sus puntos
de medida), sin el prefijo `N`. Los globos **se localizan** perfectamente por color —hay **178**—
pero **las cifras de dentro miden ~9 px y no se pueden leer**. Se probaron dos motores:

| Motor | Resultado |
|---|---|
| **Tesseract 5.5** | Basura evidente: `1733`, `39`, `85`. Con ×6 y ×10, canal R, Otsu, máscara de color, aislado de dígitos, HoughCircles y `--psm 6/7/8/11` con lista blanca |
| **RapidOCR** (PP-OCR) | **Peor**: parece que funciona y **se equivoca en silencio** |

### La auditoría que lo zanjó

Con RapidOCR se llegó a "leer" 131 N-numbers y parecía un éxito. **Auditando 16 lecturas al azar
contra la imagen: 6 correctas. 37 %.**

| leyó | pone | conf | | leyó | pone | conf |
|---|---|---|---|---|---|---|
| `155` | **156** | 0,99 | | `283` | **293** | 0,81 |
| `103` | **109** | 0,98 | | `234` | **294** | 0,80 |
| `153` | **158** | 0,94 | | `234.1` | **264.1** | 0,78 |
| `113` | **118** | 0,92 | | `133` | **180** | 0,73 |

🔴 **Los fallos son de un solo dígito y vienen con confianza 0,99: no hay umbral que los filtre
y pasan desapercibidos.** Un 37 % con errores indetectables **es peor que no tener nada**, porque
produce N-numbers inventados con pinta de correctos — y esto acaba en un informe PPAP para Bosch.

**Por eso se quitó.** `ver_plano.py` ya no intenta leerlos: si tecleas un N-number, la página te
dice que no se puede y enciende los 178 globos para que lo busques a ojo con el zoom.

### 🔑 Las tres lecciones, para no repetirlas

1. **Cobertura no es precisión.** Se midió "cuántos N-numbers encontramos" (26/34, 76 %) y se dio
   por bueno, **sin comprobar si lo leído era correcto**. La métrica que importaba era otra.
2. **La confianza del OCR no vale para validar.** `155` por `156` a 0,99 de confianza.
3. **Había una señal de alarma y se ignoró**: 131 N-numbers base distintos con solo 178 globos es
   imposible, porque muchos globos son sufijos (`.1`, `.2`, `.T`) del mismo número. **Cuando un
   recuento no cuadra con la física del problema, es que hay invención.**

> **Antes de dar por buena cualquier extracción automática, auditar una muestra al azar contra
> la fuente y contar aciertos.** No mirar solo cuántos resultados salen.

### Lo que sí funciona en `ver_plano.py`

- **El texto normal**: 1.504 palabras, confianza media 74. Las notas casi perfectas (`BOSCH`,
  `PRESSURE TEST WATER`, conf 96). Buscas y el plano lo marca, con zoom y arrastre.
- **Las cotas**, con la `Ø` leída como `9`/`@`/`$` (`Ø40,3` → `940.3`): se compensa comparando
  variantes normalizadas, así que teclear `40,3` la encuentra.
- **La localización de los 178 globos**, para saber *dónde* mirar aunque no *qué* pone.
- ❌ Los **marcos GD&T** son ilegibles (`⌖0,15 A-B` → `[1]`, `G97]`).
- ❌ El **OCR rotado** no aporta: a 270° salen 192 palabras de confianza alta y ninguna de 4+
  letras — son las líneas del dibujo leídas como `=` y `|`.

### La salida real: pedir el plano bueno

La página lo dice arriba del todo y trae **el texto listo para enviar**. Se pide, por orden:
PDF vectorial / SVG / DWG / CATDrawing nativo; si no, **el mismo plano a 600 DPI o más**; y la
**rev. 06**, que es la de los informes. → [preguntas-abiertas.md](preguntas-abiertas.md) (A4)

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

La documentación antigua del visor TXT llamaba «objetivos» a PUNTS_NOUS. Esa interpretación
está retirada: son los últimos 150 puntos de PUNTS. Los visores anteriores se conservan
sin cambios de código por petición del usuario. [Hallazgos y límites](3212/revision-2026-09-17.md).

## Correcciones v2 · presentación (18/09/2026)

`prototypes/data-explorer/ver_correcciones_v2.py` → `prototypes/data-explorer/out/correcciones-3212-v2/index.html`.
Lanzamiento: `py -3.11 .\prototypes\data-explorer\ver_correcciones_v2.py`.

Reutiliza los lectores de v1 y conserva ambos scripts anteriores. Prioriza imagen de la acción,
evolución completa con previsión diferenciada, resultados y comparación por cavidad. Añade
matriz N170, detalle local N165, perfiles en paralelo y modo presentación. Textos originales,
localizadores y límites de interpretación están en «Fuentes». [Uso](../prototypes/data-explorer/README.md).

## Correcciones v3 · perfiles y catálogo (18/09/2026)

`prototypes/data-explorer/ver_correcciones_v3.py` → `prototypes/data-explorer/out/correcciones-3212-v3/index.html`.
Lanzamiento: `py -3.11 .\prototypes\data-explorer\ver_correcciones_v3.py`.

Sustituye las miniaturas de páginas PDF en esta nueva vista por recortes del gráfico,
con ejes y escala originales: matriz de exceso por cavidad/muestreo y dos gráficas grandes
con referencia y comparación seleccionables. Conserva los PDF completos en Fuentes.
Los perfiles del 08 siguen ausentes; no se rellenan ni se interpretan como conformes.

Añade un catálogo descubierto de los 16 CSV: 34 grupos de cotas, dos de coordenadas y
3376 evaluaciones. Cada evaluación tiene histórico, tolerancias y procedencia. Mantiene
unidas las cabeceras compartidas, separa las coordenadas auxiliares y respeta la identidad
CMM de N170. Indexa las 54 acciones PPTX, incluyendo los títulos que citan varias cotas.
Las asociaciones visuales revisadas se distinguen de las extraídas del título.

Las cuatro fichas anteriores siguen como comparaciones XLS contrastadas; el resto de
previsiones queda sin revisar. El descubrimiento del catálogo es automático dentro de estos
formatos, pero los planes, rutas y correspondencias siguen adaptados al 3212. La v3 no implica
una ingesta genérica de cualquier pieza. [Detalle y uso](../prototypes/data-explorer/README.md).

## Nuevo buscador del plano (18/09/2026)

Por petición del usuario se crea `prototypes/data-explorer/buscar_en_plano.py` desde cero, conservando
`ver_todo.py` y `planos/ver_plano.py`. Lanzamiento:
`py -3.11 .\prototypes\data-explorer\buscar_en_plano.py --buscar N170`.
Salida: `prototypes/data-explorer/out/buscar-en-plano/index.html`.

Incluye texto nativo PDF, candidatos OCR de globos coloreados, búsqueda de números y
sufijos, búsqueda separada de texto/valores, zoom al resultado, recortes originales y
ubicaciones revisadas exportables como JSON. Las revisiones quedan ligadas al contenido
exacto del PDF, sin modificarlo. Admite `--pdf` y documentos de varias páginas.

La localización circular separa globos que el visor anterior agrupaba: los 263 candidatos
actuales no equivalen a los 178 componentes anteriores ni a cotas correctamente leídas.
La revisión visual encuentra las ubicaciones base de N170/N161/N240. Persisten omisiones
y confusiones de dígitos/sufijos; **no se ha validado una precisión global**. Todas las lecturas
OCR se presentan como propuestas hasta su revisión explícita. El resultado no resuelve
automáticamente las limitaciones del PDF ni la discrepancia de revisiones del plano.

La petición de un plano mejor sigue vigente. Este buscador ofrece una consulta asistida
y una vía de revisión persistente; no sustituye la validación metrológica. Los detalles y
opciones están en [Data Explorer](../prototypes/data-explorer/README.md).
