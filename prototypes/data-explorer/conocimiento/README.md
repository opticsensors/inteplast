# Visor de `conocimiento/` (prototipo, 04/11/2026)

App local para ver qué hay en `conocimiento/` sin ir a los originales. Es un prototipo personal:
**no forma parte de la aplicación web** ni se integra en ella.

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
& $py "prototypes\data-explorer\conocimiento\app.py"      # abre http://127.0.0.1:8765
& $py "prototypes\data-explorer\conocimiento\revision.py" # solo la revisión, a out/conocimiento/revision.md
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
Tras leer, hay que reiniciar `app.py`. Para el lector de globos usa el código oficial de
`backend/app/ingestion/`, que necesita onnxruntime y scipy, ya instalados en ese Python.

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
| `conocimiento/datos/biblioteca.sqlite` (solo lectura) | Lista de planos, texto de cada página, globos del `.icp`, medidas DR, cadena de correcciones y revisión |
| `hallazgos.jsonl`, `casos-referencia.jsonl`, `datos/aceptacion/*.jsonl` | Fichas de pieza, grafo y revisión |
| Markdown de `conocimiento/`, `docs/` y la raíz | Grafo y contenido de cada nodo |
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
  Al pulsar un globo se ven las medidas de esa cota en los informes DR de la pieza.
  - Un solo tag por plano: **Con `.icp`**, **Globos sin `.icp`**, **Numerado sin globos** o **Sin
    globos ni numeración** (con tinte rojo). Qué lleva cada plano y por qué, en
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
  piezas en una tabla para compararlas; se ordena pulsando la columna. La subpestaña **Grafo** muestra piezas,
  features y familias: una pieza se une a sus features, a su familia y a otra pieza si comparten ficheros
  idénticos (mismo SHA-256). No cuentan los README de remisión, la caché del navegador ni los ficheros vacíos.
  Al pulsar una pieza se abre su ficha: identidad, evolución de una cota, cadena de correcciones, muestreos,
  hallazgos, casos y ficheros por carpeta.
  - Un solo tag por pieza: **Medidas y correcciones** (18), **Medidas sin correcciones** (2) o **Sin medidas**
    (1, con tinte rojo). Se calcula con los datos salvo 3056 y 3226, fijadas en `TAG_FIJO` (`datos.py`) con su motivo.
  - **Familias:** Bearing Plate, Pump Housing, Shroud e Isomask (`FAMILIAS` en `datos.py`). No son un campo de los
    datos sino agrupaciones nuestras, con su fuente. Isomask es una suposición, marcada como tal.
  - **Evolución de una cota:** un punto por cavidad y muestreo, unidos por líneas, como en la app principal. Se
    elige pestaña del Excel y elemento. El muestreo sale del `intern.NN` del nombre, igual que en
    `cadena_correcciones.py`. Punto lleno, medido en esa pestaña; hueco con línea discontinua, de otra pestaña del
    informe; rombo, mismos valores que un muestreo anterior. Al pasar el ratón se ve de dónde sale y qué otro valor
    había. Reglas en [`valores-por-punto.md`](../../../conocimiento/valores-por-punto.md#cómo-dibuja-un-punto-el-visor-decidido-el-06112026).
  - **Componente (3288):** base y tapa son dos piezas con numeración propia. Se elige una, y la lista de cotas, la cabecera,
    la línea y las correcciones son las suyas. El plano de cada pieza abre la suya, y el del conjunto `BSG-296-00` pide elegir.
  - **Valores excluidos:** en una lista con su motivo, también cuando no queda ningún punto que dibujar.
  - **Correcciones:** activa los tramos entre muestreos dibujados consecutivos, sin cruzar series. Al pulsar uno se
    abre debajo el panel: gráfica de los dos muestreos, cambio por cavidad y texto de las correcciones que parten de
    él o se validan en él, con todas sus variantes, cada una con su fichero y diapositiva. Solo texto: las imágenes del
    PPTX no están en la biblioteca.
- **Grafo:** Markdown, features, piezas, hallazgos, preguntas abiertas y casos, unidos por los
  enlaces entre ficheros y por las menciones explícitas. Pulsar un nodo muestra su contenido y
  resalta sus vecinos.
- **Esquema:** flujo de los originales a las tablas y diagrama de relaciones con el número de filas.
- **Revisión:** comprobaciones de los enlaces pieza ↔ documento ↔ muestreo (`revision.py`).
  Solo informan; no corrigen la biblioteca. La pestaña enseña los 25 primeros casos de cada una; `revision.json`
  los guarda todos.
