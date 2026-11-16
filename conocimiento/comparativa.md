# Comparativa entre features y piezas

> Inventario de `Exemples`: 4.530 ficheros, 8 features, 21 piezas con datos.
> Contrastado el 2026-10-23 por ruta, tamaño y SHA-256. Esto no equivale a interpretar íntegramente
> cada imagen, CAD o comprimido. Cifras de la biblioteca y de `perfil_ppap` / `perfil_correccion`.

## Cifras por feature

| Feature | Piezas | Ficheros | CSV (todos) | TXT `#P#` | Libros PPAP | Diap. inventariadas | % título numerado | Planos `.icp` | STEP | STL | `.mfr` |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| [0 Bolt Eye](0-bolt-eye/README.md) | 4 | 580 | **137** | 0 | 42 | 219 | 76 % | 0 | 7 | 2 | 3 |
| [1 Clips](1-clips/README.md) | 6 | 1.049 | 1 | 0 | **237** | **890** | 90 % | 0 | 17 | 7 | 2 |
| [2 Nervios](2-nervios-soldadura/README.md) | 3 | 748 | 0 | 0 | 104 | 198 | 47 % | 11 | 39 | 5 | 1 |
| [3 Paredes delgadas](3-paredes-delgadas/README.md) | 3 | 647 | 3 | 135 | 93 | 49 | 100 % | 0 | 36 | 6 | 3 |
| [4 Tetones](4-tetones/README.md) | 1 | 107 | 0 | 0 | 11 | 17 | 100 % | 4 | 3 | 2 | 0 |
| [5 Anclajes](5-anclajes/README.md) | 0 | 1 | — | — | — | — | — | — | — | — | — |
| [6 Pockets](6-pockets/README.md) | 3 | 1.074 | 5 | 356 | 63 | 112 | 83 % | 4 | 255 | 5 | 1 |
| [7 Planitudes](7-planitudes/README.md) | 1 | 324 | 0 | 73 | 33 | 49 | 33 % | 0 | 8 | 1 | 0 |

«Diap. inventariadas» = filas de `perfil_correccion`: todos los PPTX de cada carpeta, incluidas
versiones repetidas, plantillas y documentos de otras piezas. **No es un recuento de acciones
propias ni ejecutadas.** «% título numerado» = diapositivas con número `n.m` reconocido.
CSV cuenta extensiones, no un único formato: en Bolt Eye hay 50 CSV de puntos, 75 informes
individuales CMM y 12 comparativas; Pockets contiene 1 CMM y 4 `#P#`. Los `#P#` suman
**568 ficheros: 564 TXT + 4 CSV**. Comprobado leyendo todos los TXT/CSV originales.

## Lo que se repite en todas (y ya conocíamos del 3212)

- **Informe PPAP de INTEPLAST** (plantilla de 1999, `INTERNAL DIMENSIONAL REPORT`, hojas `INTRO`/`HISTORY`/`DR*`)
  en todas las piezas con metrología. Responsables más frecuentes: Xavier Arcos, DB, Michal Heidenreich,
  Václav Vladyka (escritos con y sin mayúsculas).
- **Plan de corrección PPTX** con la estructura del 3212 (título con nº de plan y fecha, `Longitud 70mm`,
  *situación actual* → *plan* con zona en rojo) en casi todas las piezas.
- **Informes que heredan bloques de informes anteriores** (I-001): 3212, 3288, 3051.
- **Varios valores para una misma cota, muestreo y cavidad** en las 19 piezas con medidas leídas (I-008):
  [causas y censo por pieza](valores-por-punto.md).
- Nombres inconsistentes, copias (`Copia de …`, `- copia`, `_rev1_`), versiones múltiples y ficheros de otras piezas.
- Multilingüe: castellano, catalán, inglés, alemán y checo.

## Lo que cambia entre piezas (lo que un lector genérico tiene que admitir)

| Aspecto | Variantes encontradas |
|---|---|
| Esqueleto de carpetas | Numeración 1–8 del 3212, con 7 carpetas presentes (falta la 2) frente a 7 en las entregas de 2026-10 (`1- 2D y 3D pieza` … `7- Pieza real STL`); **el mismo número no es el mismo contenido** ([tabla](#esqueleto-del-3212-frente-al-nuevo)); nivel extra `Tipo A/B` en Clips; carpetas vacías que la biblioteca no ve; carpetas de feature con solo un `Readme.txt` que remite a otra (3167, 3214, 3205, 3206) |
| Medición CMM | CSV por bloques (3212, 3197 y soportes de otras familias, p. ej. 3174/3167); variantes comparativas en 3237/3238; **export `#P#`** (564 TXT y 4 CSV); PPAP del cliente `.xlsm` por cavidad (3167); KEYENCE/vídeo/galgas en 3288, 3214, 3309 |
| Cabecera PPAP | inglés (`Part Name`, `Drawing nº`) o **castellano** (`Nombre pieza`, `Nº Plano`, `CP`/`SPC`); campos corridos o `#REF!`; fechas `1899-12-31`, `xx`, texto |
| Columnas del DR | Nominal/Tol en D–F (3212, 3288) o con **`class`** en E y Tol en F–G (3197, shroud); cavidades `Cav.13`, `CAV.1`, `C1` o **solo número** (`1`…`20`); de 4 a 32 columnas de cavidad; NOK y comentarios donde acaben las cavidades. Conservar los identificadores: [cabecera del 3212](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro) |
| Hojas | `DR(3D)`, `DR`, `DR(100%)`, `DR_100%`, `DR_8cav.`, `DR_CMM`, `DR(tapa)`/`DR(base)`, `DR_PAR`, `DR cicle`, `DR-55º`… |
| Previsión de la corrección | libro aparte `DR(100%)` con `Retoc` en O (3212); en T con previsión U–AB (3197); **dentro del informe** (`Dim`/`Corr.`, shroud); **en la tabla del PPTX** (3051); ninguna (3288) |
| Título del plan | `Tool correction 1.33 (DIM. Nr.170)`; `Correcció nr. 1.1 (DIM. Nr. 54, 57 and 60)`; `Tool correction DIM#5: …` (3309); `1 / . Dim 210Ø21,5-0,2` (3051: flecha U+F0E0 entre cota y nominal, perdida en algunas extracciones); solo imágenes (3056); presentaciones de análisis sin numerar (3168, 3226) |
| Planes por pieza | 1–2 (3212, 3214) hasta **numeración 15** (3218, con huecos), en carpetas `YYYYMMDD_Nth loop…` con varias versiones; numeración que se reinicia (shroud tras postizos) o no coincide con el nombre del fichero |
| Método de medida | DOCX del cliente (Bolt Eye); **XLS `MM_revNN.xls` con hoja `DIMENSIONS`** (Clips, 3309); fichas PDF de INTEPLAST (3288); ensayos del cliente (TES) |
| Plano | escaneo sin texto (3212); vectorial con texto pero **sin globos** (3197, 3051); **con globos + `.icp`/`.prf`** que dan su posición (3205, 3206, 3288, 3202; 19 planos). Los globos los pone INTEPLAST: azules de infra-CONVERT en 25 PDF, verdes solo en el 3212 → [planos con globos](planos-globos.md) |
| Condición de medida | pieza montada (*clipped*, Clips) o libre; condiciones de proceso en la ruta (3197: `135ºC/500bar`, boquilla); fuerza de cierre (3168) |
| Moldflow | `.mfr` (10 piezas); `README.txt` *«No Moldflow information available»*; un vídeo `.avi` de llenado (3206) |

## Respecto al 3212 (la referencia de la app)

> Contrastado el 12/11/2026: inventario de la biblioteca, listado del disco para las carpetas
> vacías, fichas y contratos de `ingesta/`. Dos análisis independientes; sus discrepancias se
> resolvieron mirando el original. No se ha reinterpretado ningún CAD ni ninguna imagen.

El **3197** es la única pieza parecida en formatos. Las 17 piezas fuera de Bolt Eye siguen
otro esqueleto, y la información está en otros formatos.

### Esqueleto del 3212 frente al nuevo

| 3212 (y 2820, 3051, 3197) | Esqueleto nuevo (los otros 7 features) |
|---|---|
| `1-2D y 3D Pieza`: plano escaneado rev. 07 + STP | `1- 2D y 3D pieza`; puede llevar varios componentes (3288: BASE y TAPA) |
| no existe la 2 (vacía en 3051 y 3197) | **`2- Moldflow`**: `.mfr`, un TXT que dice que no hay, un `.avi` (3206) o vacía |
| `3- 3D Molde`: 1 STEP | `3- Molde`: ensamblajes, piezas, planos PDF, electrodos (127 STEP en el 3056) |
| `4- Metrologia`: `support intern.NN/` con **una carpeta por cavidad `c13`–`c16`** | `Interns/` + `Customer(s)/`, a veces con versión (`V00/V10/V20`) o `PPAP-xxxx_N`; **ninguna carpeta por cavidad** |
| `5- Retoques de molde`: `2N` | `YYYYMMDD_Nth loop…` por iteración; `N1`–`N6` en el 3195; sin subcarpetas en 3056, 3202 y 3214 |
| `6- Métode de mesura`: 1 DOCX | `6- Método de medición`: XLS `MM_revNN`, CATIA, útiles, programas CMM, `.icp`/`.prf` |
| **`7- Moldflow`** | **`7- Pieza real STL`** |
| `8- STL peça real` | — |

⚠️ **La biblioteca solo registra ficheros.** Carpetas vacías comprobadas en disco:
- `2- Moldflow` en 3051, 3197, 3186 y 3218.
- `3- Molde` y `6- Método de medición` en 3226.

### Lo que el 3212 tiene y el resto casi nunca

1. **La cavidad en la ruta.** Fuera de Bolt Eye va en las columnas del libro (`CAV.1`, `C1`, solo
   número; de 4 a 32). En el 3233, 32 columnas no prueban 32 cavidades físicas.
2. **CSV de la CMM.** Solo el 3212 (19) y el 3197 (118). Fuera de Bolt Eye la fuente es el libro PPAP.
3. **TXT de nubes de puntos.** En 3233, 3237, 3167 y 3168 los TXT son exportaciones `#P#`.
   En el 3238 son resultados de útiles, no medidas de la pieza.
4. **La previsión en un libro `DR(100%)` aparte.** Las demás variantes están en la fila
   «Previsión de la corrección» de la tabla de arriba.
5. **El plano escaneado.** El resto son vectoriales. Cuatro piezas traen además el `.icp`
   con la posición de los globos.

### Pieza por pieza

Detalle y balance de lectura en el contrato de cada pieza (`ingesta/<código>.md`).

| Pieza | Qué cambia frente al 3212 |
|---|---|
| [2820](ingesta/2820.md) · Bolt Eye | Solo plano + STP |
| [3051](ingesta/3051.md) · Bolt Eye | Metrología `Suport_Int_NN`/`Support_Inf_NN` con nubes de puntos e IGS, **sin CSV de la CMM**; 4 planes; previsión en la tabla del PPTX |
| [3197](ingesta/3197.md) · Bolt Eye | El más parecido. Sin STL real; `Support_intern.02`–`.11` con subcarpetas por **condición de proceso** (ºC, bar, boquilla: no son revisiones) y por cavidad `C1`–`C8`; CSV bilingües; DR con `class`; retoques `N2`, `N3`; otras tolerancias |
| [3174](ingesta/3174.md) · Clips A | Loops hasta el 11 (algunos solo XLS); el plan 2 lleva 30 diapositivas del 3186 (I-309); su plano es el de la familia |
| [3186](ingesta/3186.md) · Clips A | Medida clipada y sin clipar; loops 7–9 solo XLS; plano archivado del 3174 (I-301) |
| [3218](ingesta/3218.md) · Clips A | Hasta el loop 15, con huecos (el 14 copia el 13); plano del 3174 (I-301) |
| [3195](ingesta/3195.md) · Clips B | Retoques `N1`–`N6`; método con útiles, vídeos y programa CMM |
| [3226](ingesta/3226.md) · Clips B | 2 ficheros de metrología; el PPTX de la raíz de retoques es la plantilla `…_PXXXX.pptx`; lo demás es interferencia con la 3227 |
| [3309](ingesta/3309.md) · Clips B | Títulos `Tool correction DIM#5`; el STL se llama `3218-…` (identidad pendiente) |
| [3205](ingesta/3205.md) · Nervios | Loops hasta el 11 (postizos, correderas); corrección dentro del informe; `.icp` |
| [3206](ingesta/3206.md) · Nervios | Moldflow en vídeo; propuestas distintas tras cambiar postizos; `.icp` |
| [3214](ingesta/3214.md) · Nervios | 95 PDF de molde; 1–2 planes; su carpeta en Tetones solo remite aquí |
| [3233](ingesta/3233.md) · Paredes | 32 columnas de cavidad; `#P#` SupplyOn; el único PPTX es la plantilla P3033 |
| [3237](ingesta/3237.md) · Paredes | SupplyOn/SPC, XLSM de cliente, acondicionamiento por humedad, comparativas de medición |
| [3238](ingesta/3238.md) · Paredes | TXT de útiles; discrepancias CMM/CT y humedad antes de retocar |
| [3288](ingesta/3288.md) · Tetones | **BASE + TAPA**: 2 STEP, 2 STL, `DR(base)`/`DR(tapa)` con numeraciones propias; 20 columnas frente a 16+16 cavidades declaradas; 4 XLS sin `Customer`; `.icp` |
| [3056](ingesta/3056.md) · Pockets | 127 STEP de molde con `Electrode/`; acciones casi solo en imágenes |
| [3167](ingesta/3167.md) · Pockets | PPAP de cliente `PPAP-3167-00_1…5`; `#P#`; carpetas hasta el loop 6, 3 con plan |
| [3202](ingesta/3202.md) · Pockets | Método de 146 ficheros con `Ballooned DRW` + `.icp`; la `G` de la carpeta es tipo de plano, no revisión |
| [3168](ingesta/3168.md) · Planitudes | 111 fotos en retoques; `#P#`; un `.xls` que es un PDF |

Sin pieza propia: `4- Tetones/3167` y `/3214` y `7- Planitudes/3205` y `/3206` son solo
remisiones. `5- Anclajes` no tiene pieza (I-501).

## Implicaciones para la app

Lo que el 3212 obliga a cambiar en la app está en
[ingesta automática §1.5](../docs/ingesta-automatica.md#15-diferencias-con-el-piloto-3212-12112026).

La variación de datos exige conservar pieza, revisión, cavidad y procedencia; comparar
versiones por contenido; y separar medidas, previsiones y valores derivados. Para fórmulas
aleatorias y sus exportaciones, consultar [I-003](incongruencias.md#i-003-en-detalle).

El estado del código no se mantiene en esta comparativa. Consultar:

- [Cotas y evidencia](../docs/cotas-y-evidencia-web.md#datos-y-alcance): formatos realmente
  admitidos y límites del piloto.
- [Ingesta automática](../docs/ingesta-automatica.md): diferencias observadas, prototipos
  de la biblioteca y propuesta para generalizar la aplicación.
- [Ficheros externos](../docs/ficheros-externos.md): configuración de raíz y selección de carpetas.
- [Próximos pasos](../docs/proximos-pasos.md): estado de las tareas pendientes.
