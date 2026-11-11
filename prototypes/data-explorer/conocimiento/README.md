# Visor de `conocimiento/` (prototipo, 04/11/2026)

App local para ver qué hay en `conocimiento/` sin ir a los originales. Es un prototipo personal:
**no forma parte de la aplicación web**, y la aplicación no importa ni copia su código.

**Para qué sirve (Eduard, 09/11/2026):** es la aplicación de pruebas con las 21 piezas antes de
cargarlas en la aplicación final. Aquí se prueban también los lectores de planos antes de
llevarlos a la app. Lo que se dé por bueno se reimplementa en `backend/app/ingestion/`, con sus tests.
Cuando Eduard habla de «la app de conocimiento» se refiere a este visor.

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
& $py "prototypes\data-explorer\conocimiento\app.py"      # abre http://127.0.0.1:8765
& $py "prototypes\data-explorer\conocimiento\revision.py" # comprobaciones internas, a out/conocimiento/revision.md (sin pestaña desde el 11/11/2026)
& $py "prototypes\data-explorer\conocimiento\leer_planos.py"         # lee una vez los planos sin .icp (hecho el 05/11/2026)
& $py "prototypes\data-explorer\conocimiento\leer_planos.py" --tabla # tabla de conocimiento/planos-globos.md
```

Usa FastAPI, uvicorn y PyMuPDF, ya instalados en ese Python. En el navegador carga force-graph,
marked y mermaid desde jsDelivr (hace falta internet). La gráfica de cota es un SVG propio
(`static/evolucion.js`), sin librerías.

`python evolucion.py --resumen` resume qué dibuja la gráfica en todas las piezas.

`leer_planos.py` guarda en `out/conocimiento/lecturas/`, fuera de Git, el tag y las lecturas de los 26
planos sin `.icp` (unos 30 minutos con 4 procesos; solo rehace los que hayan cambiado). El visor
solo consulta esos ficheros. Sin ellos arranca igual, pero esos planos no tienen tag ni lecturas.
Tras leer, hay que reiniciar `app.py`. Los lectores (globos de color, `[]`, `No.` y recuadros) y el
uso de los `.icp` (calibración, calco 1:1 y gemela) salen de
[`lectores_planos.py`](../lectores_planos.py), el mismo código que usan los scripts de medida del
prototipo (desde el 09/11/2026; antes, el lector de globos era la copia de `backend/app/ingestion/`,
con las mismas lecturas). Necesita onnxruntime, scipy y rapidocr-onnxruntime, ya instalados en ese
Python, y el modelo `out/lector-globos/general/lector_globos.onnx`, fuera de Git.

`miniaturas_cad.py` guarda en `out/conocimiento/cad/`, fuera de Git, una captura de cada pieza a partir
de su STEP de `1- 2D y 3D pieza`. Se hace una vez y el visor solo sirve esos JPEG, sin leer ningún
STEP. Usa el lector oficial (`backend/app/preview_converter.py`), que necesita cadquery-ocp y trimesh.
No están en ese Python, así que se ejecuta desde un entorno aparte, fuera de OneDrive:

```powershell
& $py -m venv --system-site-packages "$env:TEMP\venv-cad"
& "$env:TEMP\venv-cad\Scripts\python.exe" -m pip install cadquery-ocp==7.9.3.1.1 trimesh==5.1.0
& "$env:TEMP\venv-cad\Scripts\python.exe" "prototypes\data-explorer\conocimiento\miniaturas_cad.py"
```

Solo hace las que faltan; `--pieza 3212` rehace una.

## Qué lee

| Fuente | Para qué |
|---|---|
| `conocimiento/datos/biblioteca.sqlite` (solo lectura) | Lista de planos, texto de cada página, globos del `.icp`, medidas DR y cadena de correcciones |
| `hallazgos.jsonl` | Errores |
| `out/probar-planos-calibracion.json` | Calibración `.icp` → página que dejó `probar_lector_planos.py` |
| `out/conocimiento/lecturas/*.json` | Tag y lecturas automáticas de los planos sin `.icp` |
| `out/conocimiento/cad/*.jpg` | Captura del CAD de cada pieza |
| **Excepción:** los PDF de plano originales | Solo para dibujar las páginas y situar las palabras de su capa de texto. Antes de abrir uno se comprueba que OneDrive lo tiene en local |

Las imágenes y palabras se guardan en `out/conocimiento/cache/`, fuera de Git. La primera vez que
se abre la cuadrícula se dibujan las 56 miniaturas (unos segundos cada una).

## Pestañas

- **Planos:** cuadrícula con los 56 PDF de plano únicos de la biblioteca (mismo criterio que
  `probar_lector_planos.py`). Se filtran por pieza, nombre, feature o tag. Al pulsar una miniatura se
  abre el visor: zoom con la rueda, arrastre y ◀ ▶ para pasar al siguiente plano de la lista. Dentro
  del plano, una búsqueda resalta los globos y las palabras que coinciden: con marca (`N30`, `No. 200`,
  `[]210`) busca esa cota y sus subcotas, y sin ella (`30`, texto) busca también dentro de otras palabras, como `130`.
  - **Ficha de la cota (columna derecha, 10/11/2026).** Al buscar una cota o pulsar un globo sale su ficha, sin
    gráfica, con tres datos:
    - **Excel:** medidas en los informes y en cuántos.
    - **CSV de la CMM:** los mismos puntos que dibuja la gráfica de la pieza.
    - **Correcciones.**

    Distingue «sin medidas de esta cota» de «la pieza no tiene medidas leídas». Si no hay CSV leídos de la
    pieza (solo los hay del 3197 y del 3212), dice «no leídos». «Ver evolución completa →» abre la ficha de la
    pieza con esa cota ya dibujada.
  - **«Marcar cotas con datos» (10/11/2026).** Debajo del buscador. Pinta de verde suave los números de la página
    cuya ficha tiene medidas (Excel o CSV) o alguna corrección, y dice cuántos son («72 de 76 cotas con datos»).
    - Igual en todos los planos, también con «0 de 166» (2820, pieza sin nada leído) o «0 de 0» (sin números situados).
    - Sale desactivada al abrir el visor, para que se vea primero todo lo que se detecta. Si se activa, se
      mantiene al pasar de un plano a otro.
    - Es el número de la pieza: el plano puede ser de otra revisión que los informes.
    - Mismas fuentes que la ficha (`evolucion.cotas_con_datos`); en el 3288, las de la pieza del libro que es
      el plano.
  - **Tag de datos (10/11/2026).** Junto al tag de tipo, de contorno, en la cuadrícula y en la barra del plano.
    - **«Cotas con datos»** (verde) si alguno de los números situados en el plano, en cualquier página, tiene
      datos.
    - **«Cotas sin datos»** (gris) si no, también con 0 números situados. Hoy son 40 y 16. Entre las 16 están el
      3237 y el 3238: su numeración está en la capa de texto y no hay números situados, aunque sus piezas sí
      tienen medidas.
    - La cuadrícula filtra por él («Con y sin datos»).
    - Se calcula una vez al arrancar el visor, en segundo plano (unos 8 s, `evolucion.datos_de_planos`).
  - **Aviso de lectura.** Si los números del plano salen de leerlo (globos sin `.icp` o numeración), abajo del
    todo de la columna sale «Lectura automática: puede fallar sin avisar». Con `.icp` no sale.
  - **Panel limpio.** El panel no enseña la ruta, la tabla de páginas ni el detalle de la lectura. El aviso de
    OneDrive solo sale si el PDF está en la nube.
  - **Volver a la cuadrícula.** No hay botón: la pestaña «Planos» (o la flecha atrás) devuelve a la
    cuadrícula con sus filtros. Igual con «Piezas».
  - Un solo tag por plano, junto a su nombre en la barra de arriba: **Con `.icp`**, **Globos sin `.icp`**,
    **Numerado sin globos** o **Sin globos ni numeración** (con tinte rojo). Qué lleva cada plano y por qué, en
    [`planos-globos.md`](../../../conocimiento/planos-globos.md#estado-de-cada-plano-05112026).
  - Círculo azul continuo: globo dibujado, con calibración del prototipo.
  - Círculo naranja discontinuo, con número y línea: plano limpio. El globo no está dibujado, así que
    se reconstruye desde el `.icp`.
  - Círculo verde: lectura automática. Puede fallar sin avisar; un globo sin círculo no se ha leído.
  - Los números de globo son locales a cada plano. En una pieza con varias hojas (3288) el mismo
    número puede ser otra cota.
  - Los tres planos guardados de lado (`GIROS` en `datos.py`) se enderezan solo en memoria, con sus
    globos.
- **Piezas:** cuadrícula con la captura del CAD de cada pieza, filtrable por pieza, feature, tag, familia o
  fichero CAD. Cada tarjeta dice cuántos muestreos tiene. La subpestaña **Números** pone las cifras de todas las
  piezas en una tabla para compararlas; se ordena pulsando la columna. Pulsar una fila despliega debajo sus ficheros
  por carpeta, con total. Junto a «Ficheros», una columna por tipo; cada fichero cae en una sola, así que suman
  «Ficheros». Los PDF se reparten entre «pdf» (con texto) y «pdf escaneado» (sin capa de texto). Al final, si los hay,
  «vacíos» (0 bytes o solo saltos de línea) y «otros sin texto extraíble» (Excel, ODS o Word hechos de imágenes o
  gráficos); esos salen de su tipo. Una copia idéntica cuenta como su original. No cuentan los Thumbs.db (miniaturas
  de Windows). El número de la pieza abre su ficha. La subpestaña **Grafo** muestra piezas,
  features y familias: una pieza se une a sus features, a su familia y a otra pieza si comparten ficheros
  idénticos (mismo SHA-256). No cuentan los README de remisión, la caché del navegador ni los ficheros vacíos.
  Al pulsar una pieza se abre su ficha: evolución de una cota, cadena de correcciones (todos los pasos de la pieza;
  pulsar una cota la dibuja) y muestreos. El 09/11/2026 salieron de la ficha, porque no aportaban al mirarla:
  - identidad, que está en `conocimiento/identidad-piezas.md`;
  - el recuento de errores, que está en la pestaña Errores y en Números;
  - lo que se sabe de la pieza (lecciones, avisos, vínculos feature-cota, datos y proceso), que no son errores y
    siguen en las fichas `.md` (no se ven en el visor: ver «Errores»);
  - los ficheros por carpeta, que ahora están en Números.
  - Un solo tag por pieza: **Medidas y correcciones** (18), **Medidas sin correcciones** (2) o **Sin medidas**
    (1, con tinte rojo). Se calcula con los datos salvo 3056 y 3226, fijadas en `TAG_FIJO` (`datos.py`) con su motivo.
  - **Familias:** Bearing Plate, Pump Housing, Shroud e Isomask (`FAMILIAS` en `datos.py`). No son un campo de los
    datos sino agrupaciones nuestras, con su fuente. Isomask es una suposición, marcada como tal.
  - **Evolución de una cota:** un punto por cavidad y muestreo, unidos por líneas, como en la app principal. Se
    elige pestaña del Excel y elemento. El muestreo sale del `intern.NN` del nombre, igual que en
    `cadena_correcciones.py`. Punto lleno, medido en esa pestaña; hueco con línea discontinua, de otra pestaña del
    informe; rombo, mismos valores que un muestreo anterior. Al pasar el ratón se ve de dónde sale y qué otro valor
    había. Reglas en [`valores-por-punto.md`](../../../conocimiento/valores-por-punto.md#cómo-dibuja-un-punto-el-visor-decidido-el-06112026).
  - **CSV de la CMM:** manda sobre el Excel en las filas de CMM, con aviso si el Excel dice otra cosa. Cargados el 3212 y,
    desde el 09/11/2026, el 3197: solo exportes sin condición de proceso, y la comparativa «totes» solo donde no hay export
    individual. Solo se cruza si la correspondencia es segura: tantos elementos de CMM en la hoja (misma cota y nominal) como
    filas en el CSV, y sin calificadores contradictorios (mínimo/máximo, GG/GN/GX, altura). Si no, se queda el Excel con aviso. `python evolucion.py --csv-frente-excel 3197` cuenta dónde discrepan y si el Excel trae el CSV de un
    muestreo anterior ([I-208](../../../conocimiento/incongruencias.md)).
  - **Componente (3288):** base y tapa son dos piezas con numeración propia. Se elige una, y la lista de cotas, la cabecera,
    la línea y las correcciones son las suyas. El plano de cada pieza abre la suya, y el del conjunto `BSG-296-00` pide elegir.
  - **Valores excluidos:** en una lista con su motivo, también cuando no queda ningún punto que dibujar.
  - **Correcciones:** activa los tramos entre muestreos dibujados consecutivos, sin cruzar series. Al pulsar uno se
    abre debajo el panel: gráfica de los dos muestreos, cambio por cavidad y texto de las correcciones que parten de
    él o se validan en él, con todas sus variantes, cada una con su fichero y diapositiva. Solo texto: las imágenes del
    PPTX no están en la biblioteca.
- **Grafo y Esquema: quitadas el 10/11/2026.** No aportaban al mirar el visor. El grafo de la pestaña
  Piezas sigue igual. Del visor salieron también sus APIs (`/api/grafo`, `/api/nodo`, `/api/esquema`), su
  código y las librerías mermaid y marked. De `conocimiento/` no se ha tocado nada.
- **Errores** (09/11/2026, `errores.py`): las incidencias `I-` de `hallazgos.jsonl`, una fila por pieza con su captura y el
  contador de propias pendientes y generales («3 propias pendientes de 4 · 1 general»). Cada pieza abre sus incidencias:
  título de `incongruencias.md`, estado, texto original y «Ver evidencia» (fichero y celda o línea, y la gráfica si la
  incidencia cita una cota). Por defecto, solo las pendientes; las resueltas y corregidas, con una casilla.
  - **Estado:** «Duda» (pregunta), «Pendiente de aclarar» (incongruencia abierta), «Explicación posible · sin
    confirmar» (`explicable`: hipótesis razonable sin confirmar), «Resuelta», «Corregida». Abierta no quiere decir
    comprobada: ninguna se presenta como error demostrado. Las de explicación posible cuentan como pendientes y van
    después de las «Pendiente de aclarar» (revisión del 09/11/2026: antes salían como «Explicada», ocultas).
  - **Generales:** las de la sección «Transversales» de `incongruencias.md`, con una sola ficha. Cada pieza las cuenta aparte
    y enlaza a la lista filtrada de las que le afectan. La fila «Generales y otras referencias» suma las que no citan
    ninguna pieza del catálogo (I-501, la plantilla 3247).
  - **El resto de `hallazgos.jsonl` no son errores** (`errores.NO_SON_ERRORES`) y no se muestran en el visor: lecciones,
    advertencias, vínculos feature-cota, datos y proceso desde el 10/11/2026, al quitar la pestaña Grafo; estructura y
    formato desde el 11/11/2026, al quitar Revisión. Siguen intactos en `conocimiento/hallazgos.jsonl` y en las fichas
    Markdown. Cómo presentar las lecciones y los warnings útiles, ligados a piezas, features o cotas, se decidirá aparte.
    Los avisos de las gráficas siguen junto a sus puntos.
- **Revisión: quitada el 11/11/2026.** Era el control de calidad de nuestra extracción, no un resultado para INTEPLAST.
  Antes de quitarla se decidió el destino de cada comprobación (junto al dato, Errores, interno o pendiente), con
  evidencia y recuentos de referencia, en [revision-comprobaciones.md](../../../conocimiento/revision-comprobaciones.md).
  Con ella salieron sus rutas (`/api/revision`, `/api/revision/referencias`) y su código. `revision.py` sigue
  funcionando desde la consola, con sus tests.

## Pendiente (09/11/2026)

**Objetivo (Eduard, 09/11/2026):** terminar el visor antes de pasar nada a la app final. Terminado, servirá para enseñar
sus resultados a INTEPLAST con cada error respaldado por escrito (fichero, celda o línea). Lo que ya está en las preguntas a
INTEPLAST no se repite aquí; correcciones solo en texto y familias se dejan de momento.

Recogido de las fichas enlazadas el 09/11/2026; las cifras son las de esas fichas, no se han recalculado.

| Tema | Qué falta | Fuente |
|---|---|---|
| ~~Extractor de `.icp` (`globos_icp.py`)~~ | **Corregido el 09/11/2026.** Ponía el número del `.prf` y no el dibujado (45 en el globo 70 del 3205), situaba 20 sellos donde no hay globo por un byte de desfase y dejaba fuera los sellos sin fila en el `.prf`. En las 30 páginas con `.icp` del visor: 40 sellos cambian de sitio y 163 aparecen; los planos sin `.icp` no cambian | [planos-globos.md](../../../conocimiento/planos-globos.md#referencia-el-extractor-de-icp-corregido-el-09112026) |
| ~~Un solo código de lectura de planos~~ | **Hecho el 09/11/2026**: el visor y los scripts de medida usan `lectores_planos.py`, sin depender del backend; las 26 lecturas y lo que enseña el visor en los 56 planos no cambian | [README del prototipo](../README.md#un-solo-código-de-lectura-de-planos-09112026) |
| Lectores `[]`, `No.` y recuadros | **Medidos el 10/11/2026** en los 4 planos conocidos (2820, 3174, 3186 y 3214), con muestra al azar reproducible. Los 165 números de la muestra están bien leídos y 149 bien situados; los otros 16 están en tablas de vistas o desplazados. Hay 24 omisiones confirmadas, casi todas marcas giradas, y los recuadros dan falsos positivos en planos sin numeración. **Falta:** validarlos en planos nuevos, apartados antes de mirarlos, y las 11 cotas con letra del 3214 | [planos-globos.md](../../../conocimiento/planos-globos.md#lectores-de-planos-numerados-10112026) |
| Globos sin leer *(aparcado)* | 614 globos de color sin lectura (234 del 3195, 148 del 3212, 113 del 3167). Las 11 cotas con letra del 3214 no salen en el OCR. 13 planos sin globos ni numeración | ídem |
| `.icp` | 30 de los 56 planos dan número y posición sin leer nada. En la app final, la lectura directa de `.icp` sigue abierta | [próximos pasos](../../../docs/proximos-pasos.md#prioridad-a-corto-plazo-28102026) |
| ~~CSV del 3197~~ | **Hecho el 09/11/2026**: 118 CSV en la biblioteca y en la gráfica | [3197](../../../conocimiento/0-bolt-eye/3197.md#csv-de-la-cmm-en-la-biblioteca-09112026) |
| Varios valores por punto | Las reglas de dibujo son convenciones. El significado de hojas y bloques es interpretación hasta que respondan A17 y A24 | [valores-por-punto.md](../../../conocimiento/valores-por-punto.md#límites) |
| Correcciones *(aparcado)* | Solo texto: las imágenes del PPTX no están en la biblioteca | [Pestañas](#pestañas) |
| Familias *(aparcado)* | Isomask es una suposición | [Pestañas](#pestañas) |
| ~~Avisos junto al punto~~ (11/11/2026) | Salieron al decidir el destino de las comprobaciones de Revisión. **Hechos el 11/11/2026**, como información (gris, con una barra a la izquierda) y no como aviso. ~~V2~~: el detalle del punto dice si su muestreo tiene otra fecha en **otras hojas del mismo archivo** o en **otros archivos** (copias), por separado, con la hoja o el archivo (`evolucion.anotar_fechas`). ~~V1~~: «Mismo valor que en intern.NN en k de n cavidades de este muestreo (…)», desde 2 cavidades y cuando no son todas, que ya es el rombo. No se interpreta como copia ni como error (`evolucion.marcar_coincidencias`). ~~V3~~ **hecho el 11/11/2026:** la fecha del informe se enseña entera y es la de la hoja del punto. Se distingue fecha, intervalo («29.08.2024-4.9.2024: no es una fecha única»), sin fecha utilizable con el texto original («xx», fecha cero) y fallo de lectura (`datos.fecha_informe`) | [revision-comprobaciones.md](../../../conocimiento/revision-comprobaciones.md#pendientes) |
