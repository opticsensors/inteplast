# Por qué un punto tiene varios valores

> Censo del 06/11/2026 sobre las 19 piezas con medidas leídas ([I-008](incongruencias.md)). Se repite con
> `conocimiento/herramientas/valores_por_punto.py`, que solo lee la biblioteca y no abre originales.

**Cota + muestreo + cavidad no identifica una medida.** Esa combinación da más de un valor en
**90.247 de 255.832 puntos (35,3 %)**, y la mayoría de esos valores no son duplicados: son medidas
distintas (otro elemento, otra condición, otra pieza). Por eso no hay una regla única para quedarse con
uno. Una gráfica de un valor por cavidad y muestreo necesita elegir antes qué se está mirando.

Alcance: `medida_dr`, hojas con papel `informe` de la carpeta de metrología, con `intern.NN` en el nombre
y sin `RAND()`, ceros ni atípicos. Son los mismos filtros que `cadena_correcciones.py`. Quedan fuera dos
piezas: 2820 no tiene informes, y la hoja `DR` del `intern.01` de 3226 tiene 44 valores en la columna I, pero
no rotula ninguna columna de cavidad y `lector_dr.py` no la reconoce (id 1577, filas 12–13).

## Las seis causas

Un punto puede tener varias causas, así que las columnas no suman el total. 67.383 puntos tienen una sola
causa y 685 quedan sin clasificar.

| Causa | Puntos | Solo esa causa | Qué es | Ejemplo |
|---|---:|---:|---|---|
| **Elementos distintos** | 53.836 | 37.544 | La misma cota agrupa cosas distintas: mínimo y máximo, varios postes, otro equipo. **No son duplicados** | 3051 `intern.06`, cota 40, c1, `DR(100%)`, filas 20–22: 12,38 (`min`), 12,42 (`max`), 12,445 (`Ø` con CMM) |
| **Hojas distintas** | 40.101 | 22.279 | Cada hoja de un libro puede ser otra condición, otra tecnología o **otra pieza** | 3218 `intern.06`, cota 2207, c8, fila 50: 2,629 / 2,622 / 2,625 / 2,624 en `DR_400b` a `DR_700b` |
| **Filas seguidas sin rótulo** | 7.654 | 3.834 | Filas consecutivas de una cota sin nada que las distinga. **Probable:** varios elementos en orden fijo | 3237 `intern.09`, cota 131, c4, `DR`, filas 124–125: 0,264 y 0,253 |
| **Bloques separados** | 7.285 | 1.442 | La misma cota y elemento en dos zonas de una hoja, con otras cotas entre medias. [Ver abajo](#bloques-separados-en-una-misma-hoja) | 3212 `intern.08`, cota 113, c13, `DR`, filas 25 y 52: 3,297 y 3,074 |
| **Copias que discrepan** | 4.602 | 1.287 | Dos ficheros del mismo muestreo con la misma hoja y elemento y otro valor. Amplía [I-006](incongruencias.md) | 3233 `intern.16`, cota 420, c8, `100% BOSCH PORTAL!P87`: 0,74 en `Customer` y 0,81 en `Interns` |
| **Varias piezas por cavidad** | 3.609 | 917 | La cavidad aparece en varias columnas de la misma fila. `cadena_correcciones.py` las trata como muestras | 3174 `intern.25`, cota 801, c5, `DR_100%` fila 216: 25,13 / 25,152 / 25,111 (columnas M, U y AC) |

### Lo que dicen los nombres de hoja

Los nombres no siguen un estándar, y ninguno marca siempre el informe «principal»
([tabla por pieza](#hojas-de-cada-pieza)). Lo que significan es interpretación a partir del nombre:

- **Condición de proceso:** presión (`DR_400b`, `DR_CMM 600 BARS`, `3 postpreasures`), máquina o ensayo
  (`Husky-210º(6)`, `3rd test`, `1st trial`), humedad (`DR_Humid`, `DR-Conditioned`, `DR-1100 humidif`).
- **Tecnología o alineado:** `DR_CMM` frente a `DR_100%`, `DR_CMM 600 DRW ALIGMENT`, `KnO - 3D CMM+ ICLs`.
  Pueden discrepar mucho: 3174 `intern.05`, cota 1117, c3, da 0,273 en `DR_100%` y 0,011 en `DR_CMM`.
- **Versión o destino:** `DR_100%_for PPAP`, `DR_100% (customer)`, `DR_100%_old`, `DR_100% not updated`.
- **Otra pieza:** en el **3288** `DR(base)` y `DR(tapa)` son dos piezas con **numeración de cotas propia**.
  8.139 de sus 8.356 puntos con varios valores juntan las dos hojas: la cota 77 de `intern.03`, c10, da
  0,19 en `DR(base)` y 2,1–2,13 (Ø) en `DR(tapa)`. **En el 3288 la clave tiene que incluir la hoja.**

Las pestañas de un libro son del **mismo muestreo**, no de otros, y ninguna es el export de la máquina. Son
tablas de Excel; el equipo de cada valor está en su columna `Equipment`, no en el nombre de la pestaña:

| Libro | Pestaña | Filas | Equipos (valores) | Qué dice `HISTORY` |
|---|---|---:|---|---|
| `3218/…/Interns/3218-00_intern.06.xls` | `DR_100%` | 252 | CT-SCAN 1.400, DEPTH GAUGE 280, CMM 128, CALIPER 88, IMPOSED 88 | Informe 6, lote 315567: *«parametres i cotes en gris»*, *«500BARS is the one that has less deformation»* |
| | `DR_400b` a `DR_700b` | 69 cada una | CMM 520, DEPTH GAUGE 32 | |
| `3174/…/Customer/3174-00_intern.05.xls` | `DR_100%` | 278 | CT-SCAN 1.032, CMM 480, DEPTH GAUGE 304, CALIPER 152, IMPOSED 120 | Informe 5, lote 315089: *«cotes nou programa cmm peça clipada»*, *«program cota 102/303/309»* |
| | `DR_CMM` | 61 | CMM 440, IMPOSED 40, `CMM +` 8 | |

**Probable:** `DR_100%` es el informe completo y las demás, mediciones parciales o pruebas de ese muestreo. En el
3174 `intern.05` (copia de `Interns`), `DR_CMM` y `DR_100%` solo coinciden en 16 de 336 puntos comparables; por
qué difieren está **pendiente**, aunque la cabecera de `DR_CMM` lleva el rótulo `Inteplast JIG`.

Las pestañas no solo cambian de nombre: también cambia qué se mide en cada informe. En el 3174 (`Interns`):

| Muestreos | Pestañas de informe |
|---|---|
| `.01`, `.02` | `DR_100%` y varias `DR_CMM 600/700/800 …`; en `.01`, también `DR_CT-SCAN 600 bar` |
| `.03`–`.05`, `.08`, `.09`, `.25` | `DR_100%` y `DR_CMM` |
| `.06`, `.10`, `.12`–`.17`, `.20`, `.22`, `.24` | `DR`, de 48 a 488 valores frente a más de 2.000 de `DR_100%` (`.15` y `.16` tienen una segunda pestaña pequeña) |
| `.18`, `.19`, `.23` | `DR` y una pestaña con el número de lote (`315594`, `315614`, `315691`) |
| `.11`, `.26`–`.29` | `DR_CMM` (en `.26`, también `ICL_203481`) |
| `.30`–`.33` | `DR CMM`; hasta `.32`, también `DR_CMM` |

## Bloques separados en una misma hoja

En el **3212 `intern.08.xls`, hoja `DR`**, las cotas 113, 117 y 118 aparecen dos veces, y el CSV de la CMM
indica cuál es la de ese muestreo. Valores de c13 (columna H):

| Cota | Primer bloque, igual que `intern.01` | Último bloque | CSV de `support.intern.08` |
|---|---|---|---|
| 113 | filas 25–28: 3,297 · 3,304 · 3,276 · 3,3 | filas 52–55: 3,074 · 3,051 · 3,036 · 3,057 | 3,074 · 3,051 · 3,036 · 3,057 |
| 117 | filas 36–39: 0,026 · 0,036 · 0,087 · 0,061 | filas 56–59: 0,05 · 0,039 · 0,072 · 0,027 | 0,05 · 0,039 · 0,072 · 0,027 |
| 118 | filas 40–43: 0,015 · 0,13 · 0,235 · 0,148 | filas 60–63: 0,027 · 0,011 · 0,035 · 0,136 | 0,027 · 0,011 · 0,035 · 0,136 |

En esos 12 elementos (24 filas) el primer bloque repite un muestreo anterior y solo el último coincide con el CSV. Es un
caso de [I-001](incongruencias.md) dentro de una sola hoja: `medida_dr` guarda los dos bloques como informe.

**Esto no se puede generalizar a «quedarse con la última fila».** Comparando filas completas de 3 valores
o más con los muestreos anteriores, en todas las piezas:

| Pieza | Bloques separados | Solo el primero repite un muestreo anterior | Solo el último | Los dos | Ninguno |
|---|---:|---:|---:|---:|---:|
| 3056 | 223 | 0 | 0 | 0 | 223 |
| 3167 | 175 | 0 | 0 | 75 | 100 |
| 3168 | 2 | 0 | 0 | 0 | 2 |
| 3174 | 25 | 3 | 0 | 13 | 9 |
| 3186 | 4 | 1 | 1 | 1 | 1 |
| 3195 | 23 | 1 | 0 | 0 | 22 |
| 3197 | 13 | 0 | 0 | 2 | 11 |
| 3205 | 13 | 0 | 0 | 0 | 13 |
| 3206 | 7 | 0 | 0 | 0 | 7 |
| 3212 | 12 | **12** | 0 | 0 | 0 |
| 3214 | 15 | 0 | 1 | 0 | 14 |
| 3218 | 1.123 | 9 | 11 | 470 | 633 |
| 3237 | 145 | 0 | 0 | 2 | 143 |
| 3238 | 10 | 0 | 0 | 0 | 10 |
| 3288 | 167 | 0 | 0 | 120 | 47 |
| **Total** | **1.957** | **26** | **13** | **683** | **1.235** |

Solo el 3212 tiene un patrón claro. En el 3218 `intern.27`, hoja `KnO - 3D CMM+ ICLs`, pasa en los dos
sentidos según la cota. En el 3056 `intern7`, `DR (Summary)`, hay dos zonas parecidas (cota 1740.11, c2,
filas 26 y 241: 2,681 y 2,671) y ninguna repite nada. Qué significan esas zonas está **pendiente**.

## Contraste con los CSV

Hoy solo se puede contrastar el 3212: `medida_cmm` tiene 3.376 filas y son todas suyas. Exportes de la máquina por
muestreo solo hay dos: 3212 (19 CSV) y 3197 (118, sin cargar en esa tabla). Los CSV de 3167, 3174, 3233, 3237 y 3238 (de 1
a 5) son exportes `#P#`, del método de medida o una prueba suelta, y no sirven para contrastar muestreos. Las otras 14 piezas
no tienen ninguno ([A24](../docs/preguntas-abiertas.md#a24-csv-cmm)). Por eso «CSV antes que XLS» ([trampa 1](trampas.md))
resuelve el piloto, pero no el resto de piezas.

Los muestreos sin CSV no se pueden desempatar así: en el 3212 solo tienen CSV `.01`, `.03`, `.05` y `.08`.
En la cota 113 (c13, primer elemento) el CSV da 3,297, 3,056, 3,042 y 3,074, mientras los XLS de `.04`,
`.06` y `.09` repiten 3,297 y el de `.05` repite 3,056.

## Cuánto cubre una pestaña y cuánto se repite

Una línea de una sola pestaña no cubre toda la historia de la cota. Sobre 4.174 cotas con 2 muestreos o más
(33.054 pares cota-muestreo):

- La mejor pestaña de cada cota cubre el **75 %** de sus muestreos; la mejor pestaña y elemento, el **70 %**.
- Solo el **38 %** de las cotas tiene una pestaña y elemento presentes en todos sus muestreos.
- El **56 %** de los pares tiene exactamente los mismos valores que un muestreo anterior. Es una comparación simple
  y no prueba que no se volviera a medir, sobre todo en cotas con pocos valores. `cadena_correcciones.py` usa un criterio
  más estricto.

| Pieza | Cotas con 2+ muestreos | Pares cota-muestreo | Cubre la mejor pestaña | Cubre la mejor pestaña y elemento | Cotas completas con pestaña y elemento | Pares que repiten un muestreo anterior |
|---|---:|---:|---:|---:|---:|---:|
| 3051 | 202 | 1.177 | 95 % | 93 % | 67 % | 42 % |
| 3056 | 699 | 1.960 | 77 % | 73 % | 37 % | 32 % |
| 3167 | 467 | 6.296 | 79 % | 79 % | 10 % | 56 % |
| 3168 | 85 | 417 | 76 % | 69 % | 6 % | 42 % |
| 3174 | 175 | 2.269 | 83 % | 80 % | 0 % | 57 % |
| 3186 | 214 | 3.647 | 74 % | 68 % | 0 % | 75 % |
| 3195 | 786 | 2.085 | 80 % | 76 % | 75 % | 27 % |
| 3197 | 128 | 786 | 54 % | 51 % | 0 % | 44 % |
| 3202 | 224 | 737 | 85 % | 83 % | 72 % | 39 % |
| 3205 | 73 | 978 | 56 % | 48 % | 0 % | 47 % |
| 3206 | 65 | 821 | 54 % | 36 % | 0 % | 41 % |
| 3212 | 119 | 675 | 93 % | 89 % | 55 % | 60 % |
| 3214 | 54 | 504 | 81 % | 69 % | 0 % | 71 % |
| 3218 | 247 | 6.941 | 65 % | 58 % | 5 % | 63 % |
| 3233 | 212 | 1.457 | 86 % | 85 % | 66 % | 73 % |
| 3237 | 132 | 824 | 56 % | 49 % | 8 % | 53 % |
| 3238 | 127 | 820 | 60 % | 60 % | 10 % | 73 % |
| 3288 | 140 | 560 | 100 % | 100 % | 100 % | 64 % |
| 3309 | 25 | 100 | 100 % | 82 % | 64 % | 34 % |
| **Total** | **4.174** | **33.054** | **75 %** | **70 %** | **38 %** | **56 %** |

## Informes sin `intern.NN`

`intern.NN` es el número de muestreo en el nombre del fichero (`3212-00_intern.08.xls`, a veces `Int_08`). Hay 47
ficheros con medidas en metrología que no lo llevan. No entran en estas cifras ni en la cadena de correcciones.

- **37 son informes PPAP o `INF`,** con su propia numeración, que no es la de los muestreos (la cadena lo
  explica en `cadena_correcciones.py`). Están en carpetas como `Customer`, `SupplyOn` o `Uploaded to IQS`.
  **Qué versiones se enviaron al cliente no consta** ([A18](../docs/preguntas-abiertas.md#a18-cpk-generator)).
- **Los otros 10** son de otros tipos, como estudios y resúmenes: `3218-00_Jig variability study.xlsx`,
  `3218 CT-SCAN results.xlsx`, `3233_Overview.xlsx`, `Results.xlsx` del 3195, `3205-00_intern.xls`…

Un PPAP no es el Excel `intern`, aunque gran parte de sus valores coincide con él. Por ejemplo,
`3238/4- Metrologia/Customers/V00/PPAP_3238_INF_01.xlsm`:

| Pestaña | Qué tiene |
|---|---|
| `DR 100%` | 154 filas, un valor por cavidad (4). Numeración del cliente: `1-2` es la cota 2 |
| `cav_1` a `cav_4` | Una por cavidad, con 5 muestras en las columnas J–N, más columnas auxiliares Y–AB |
| `Data`, `Template` | Listas y plantilla |

- **Muestra 1:** la columna J coincide con `DR 100%` en 608 de 616 filas, y el 73 % de esos valores está en algún
  informe `intern`, sobre todo `3238-00_intern.02.xls`.
- **Muestras 2–5:** solo el 20 % está en un `intern`, y una parte puede ser casualidad, porque se compara el valor a
  3 decimales y muchos tienen 2. Son valores fijos, y 2.175 de los 2.176 que tienen factor caen dentro de J ± factor.
- **`RAND()`:** las 2.176 celdas están en las columnas auxiliares Y–AB (`=ROUND(-$X8+2*$X8*RAND()+$J8,$W8)`), no
  en J–N. De los 47 ficheros, 11 tienen `RAND()`, en distintos sitios según el libro ([I-003](incongruencias.md#i-003-en-detalle)).

**Esto no prueba que un valor esté falseado.** Es compatible con muestras 2–5 calculadas, pero no demuestra su
origen ni para qué se usaron. Para saberlo habría que preguntar ([A18](../docs/preguntas-abiertas.md#a18-cpk-generator)).
Mientras tanto no se tratan como medidas.

| Pieza | Ficheros | Valores | Con `RAND()` | Ejemplo |
|---|---:|---:|---:|---|
| 3167 | 12 | 69.644 | 0 | `PPAP-3167-00_Inf_04.xlsm` |
| 3168 | 2 | 10.429 | 0 | `PPAP_3168-00_inf00.xlsm` |
| 3174 | 8 | 18.762 | 1 | `PPAP-3174-00_INF05.xls` |
| 3195 | 3 | 699 | 0 | `Results.xlsx` |
| 3202 | 1 | 1.032 | 0 | `PPAP-3202-00_INF.01.xls` |
| 3205 | 1 | 2.256 | 0 | `3205-00_intern.xls` |
| 3218 | 2 | 9.481 | 0 | `3218 CT-SCAN results.xlsx` |
| 3233 | 8 | 71.052 | 3 | `PPAP_3233_Inf_01.xlsm` |
| 3237 | 6 | 30.764 | 3 | `PPAP_3237_INF_01.xlsm` |
| 3238 | 4 | 25.508 | 4 | `PPAP_3238_INF_01.xlsm` |

Las nueve piezas restantes con medidas (3051, 3056, 3186, 3197, 3206, 3212, 3214, 3288, 3309) no tienen ninguno.

## Cómo dibuja un punto el visor (decidido el 06/11/2026)

Eduard pidió que la línea se dibuje siempre, un punto por cavidad y muestreo, como en la app. Por eso son
**convenciones de dibujo, no una afirmación de cuál es el valor correcto**: ninguna regla general se sostiene (arriba).
Cada punto dice de dónde sale y qué otro valor había. Código en
[`evolucion.py`](../prototypes/data-explorer/conocimiento/evolucion.py).

Primero se elige qué se mira, **pestaña** y **elemento**. Por defecto, la pestaña y el elemento que cubren más muestreos.

| Caso | Qué se dibuja | Por qué |
|---|---|---|
| El informe no tiene la pestaña elegida | **Punto hueco y línea discontinua**, con el mismo elemento de otra pestaña del informe. Sin ninguna, no hay punto | Sin rellenar se perderían cerca de 30 de cada 100 puntos. El hueco avisa de que puede ser otra condición o tecnología. Recomendación aceptada por Eduard |
| Dos piezas en un libro (3288, base y tapa) | Se elige el componente, y línea, nominales, tolerancias, recuentos y correcciones son todos de ese. Nunca se rellena uno con otro. El plano de cada pieza abre la suya; el del conjunto `BSG-296-00` pide elegir | Los números son locales a cada pieza. Sale de los nombres: pestañas `DR(base)`/`BASE`, PPTX `..._BASE`/`..._TAPA` y planos `BSG-296-01`/`-02` ([ficha](4-tetones/3288.md)) |
| Filas seguidas sin rótulo | Cada fila es un elemento (`fila 1`, `fila 2`) | Probablemente son elementos distintos. El orden puede cambiar entre informes (3186, cota 103) |
| Misma fila en dos bloques de la pestaña | El último, con aviso del otro valor | Convención. Solo en el 3212 está comprobado que el último es el bueno |
| Varias piezas de la misma cavidad | La media, rotulada como media | Una media no es una medida. Columnas idénticas no se promedian: son un bloque duplicado |
| Copias con los mismos valores | Una, sin aviso | No cambian nada |
| Copias que discrepan | La de `Interns` (si no hay, la de nombre más corto), con aviso del otro valor | Nada dice cuál vale (I-006, [A17](../docs/preguntas-abiertas.md#a17-versiones-informes)) |
| Muestreo con los mismos valores que uno anterior | **Se dibuja**, en rombo, con aviso | No se da por erróneo: el dato está así en el informe y no sabemos si se volvió a medir (decisión de Eduard) |
| Hay CSV de ese muestreo y la fila es de CMM | El valor del CSV, con aviso si el Excel dice otra cosa. Se cruza por posición entre las filas de CMM con la misma nominal | «CSV antes que XLS» ([trampa 1](trampas.md)). Hoy solo está cargado el del 3212 |
| `RAND()`, ceros y atípicos | Fuera de la línea, en una lista con el motivo, también si no queda ningún punto que dibujar (10 de las 13 cotas así que se han mirado son del 3168) | I-002, I-003 |

**Correcciones de un tramo:** se conserva cada variante con su fichero y diapositiva, y ninguna se oculta. Solo comparten
variante las copias de una misma acción con número, en ficheros distintos y con el mismo texto no vacío: dos acciones
distintas pueden tener el mismo texto. De 1.326 acciones, en 210 hay textos distintos, y en 73 varias diapositivas de un
mismo fichero. Una versión solo se marca como preferente si está documentada: hoy, las del 3212
([qué fichero usar](0-bolt-eye/3212/5-retoques-molde.md#qué-fichero-usar)). En el resto se avisa de que no consta cuál vale.

La cadena de correcciones sigue saltando los muestreos que repiten otro al buscar la validación ([rag.md](rag.md)), así
que un tramo de la gráfica puede mostrar una corrección que se valida más tarde. Cambiar entre dos muestreos es una
secuencia, no una prueba de que la corrección funcionó.

**Qué sale con la selección por defecto de cada cota** (`python evolucion.py --resumen`), sobre 33.512 pares
cota-muestreo: 30.126 tienen punto (90 %): 23.567 de la pestaña elegida (70 %), 6.554 huecos (20 %) y 5 solo del CSV.
Otros 3.386 no tienen punto (10 %). De los que tienen punto, 20.382 repiten un muestreo anterior, 1.044 tienen otro valor
y 262 son media.

**Auditoría del 06/11/2026** (semilla 20261106, contra los ficheros originales, todos en local): en 60 puntos al azar,
59 de 59 valores coinciden con la celda del Excel que cita el punto (el otro es una media) y 60 de 60 están en la cota
correcta. En 15 puntos tomados del CSV, los 15 coinciden con la línea citada. Esto comprueba **de dónde sale** cada punto,
no que sea la medida correcta para esa gráfica: para eso no hay referencia automática fuera del 3212.

## Qué usa la app principal

La regla es la misma: **los CSV prevalecen sobre los resúmenes XLS** de las mismas cotas y contexto
([cotas y evidencia](../docs/cotas-y-evidencia-web.md)). En la práctica depende de la pieza: el piloto 3212 se apoya en sus
CSV, y al importar otras se leerá casi siempre Excel, porque solo el 3197 tiene más CSV de máquina por muestreo. Su
lector de CSV (`backend/app/ingestion/measurement_csv.py`) ya obtuvo 60 de 60 en un contraste puntual del 3197, y es el
punto de partida si se cargan esos CSV en la biblioteca. Si INTEPLAST guarda los demás, cambiaría mucho:
[A24](../docs/preguntas-abiertas.md#a24-csv-cmm).

## Límites

- El **elemento** se deduce de etiqueta, tipo, nominal, equipo y comentario de cada fila. Es una heurística:
  un comentario distinto entre copias (`post1 pasted from 13`) separa dos filas que quizá son la misma, y por
  eso «Copias que discrepan» puede quedarse corta.
- «Solo el primero repite» compara con muestreos anteriores por valores. No demuestra cómo se guardó el dato.

La cadena de correcciones también separa las dos piezas del 3288 desde el 07/11/2026: copias, fechas, herencias y orden entre
planes se construyen aparte para cada una. Regenerada toda la tabla, las 2.030 filas de las otras 16 piezas son idénticas, y en
el 3288 cambian los 25 pasos que mezclaban ([detalle](4-tetones/3288.md)).
- El censo se revisó con muestras al azar por causa desde la biblioteca, sin contrastar las causas con los originales
  salvo lo que ya constaba en I-001 e I-006. Sí se auditó de dónde sale cada punto dibujado ([arriba](#cómo-dibuja-un-punto-el-visor-decidido-el-06112026)).
- El significado de hojas y bloques es interpretación; para confirmarlo habría que preguntar a INTEPLAST.

## Censo por pieza

| Pieza | Puntos | Con varios valores | Elementos distintos | Hojas distintas | Copias que discrepan | Filas seguidas sin rótulo | Bloques separados | Varias piezas por cavidad |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3051 | 4.708 | 1.340 | 924 | 324 | 0 | 12 | 0 | 464 |
| 3056 | 8.288 | 2.820 | 2.139 | 540 | 15 | 401 | 639 | 274 |
| 3167 | 26.691 | 7.937 | 3.097 | 4.984 | 0 | 28 | 294 | 56 |
| 3168 | 4.035 | 1.452 | 1.252 | 267 | 0 | 90 | 8 | 2 |
| 3174 | 18.245 | 7.977 | 4.859 | 4.317 | 565 | 607 | 112 | 702 |
| 3186 | 14.591 | 4.777 | 3.445 | 407 | 359 | 486 | 14 | 79 |
| 3195 | 16.751 | 2.815 | 964 | 1.398 | 313 | 603 | 148 | 328 |
| 3197 | 6.568 | 1.051 | 691 | 376 | 0 | 0 | 92 | 207 |
| 3202 | 2.871 | 1.405 | 1.288 | 226 | 124 | 87 | 0 | 207 |
| 3205 | 7.727 | 3.447 | 3.056 | 388 | 123 | 183 | 96 | 221 |
| 3206 | 3.170 | 1.701 | 1.449 | 604 | 193 | 88 | 16 | 80 |
| 3212 | 2.755 | 868 | 856 | 36 | 0 | 28 | 12 | 44 |
| 3214 | 2.016 | 503 | 367 | 129 | 16 | 0 | 42 | 29 |
| 3218 | 73.413 | 32.277 | 19.366 | 14.473 | 2.247 | 4.160 | 2.874 | 903 |
| 3233 | 45.747 | 8.713 | 6.397 | 2.974 | 571 | 384 | 0 | 1 |
| 3237 | 3.319 | 1.508 | 987 | 372 | 27 | 172 | 272 | 0 |
| 3238 | 3.294 | 954 | 846 | 88 | 0 | 56 | 36 | 0 |
| 3288 | 11.243 | 8.356 | 1.511 | 8.139 | 0 | 269 | 2.630 | 12 |
| 3309 | 400 | 346 | 342 | 59 | 49 | 0 | 0 | 0 |
| **Total** | **255.832** | **90.247** | **53.836** | **40.101** | **4.602** | **7.654** | **7.285** | **3.609** |

## Hojas de cada pieza

| Pieza | Informes | Hojas por informe (mediana · máximo) | Nombres más frecuentes (informes) |
|---|---:|---:|---|
| 3051 | 11 | 1 · 3 | `DR(4CAV_CMM)` (7) · `DR(100%)` (5) · `DR` (4) · `DR(1)` (1) |
| 3056 | 17 | 2 · 5 | `DR (DIF)` (9) · `DR (3D)` (5) · `DR(100%)` (4) · `DR(Sketch)` (4) · `DR(1)` (3) · `DR` (2) |
| 3167 | 22 | 2 · 8 | `DR_100%_old` (13) · `DR` (7) · `DR_100%` (5) · `DR(1)` (3) · `DR_CC(P4)` (2) · `DR_CC(P3)` (2) |
| 3168 | 27 | 1 · 6 | `DR` (21) · `DR-Conditioned (Customer)` (2) · `DR-Conditioned` (2) · `DR-Dry (Customer)` (2) · `DR-Dry` (2) · `Sketch` (2) |
| 3174 | 54 | 2 · 7 | `DR_CMM` (26) · `DR` (23) · `DR_100%` (17) · `DR CMM` (5) · `DR_CMM 600 DRW ALIGMENT` (4) · `DR_CMM 700 DRW ALIGMENT` (4) |
| 3186 | 27 | 1 · 2 | `DR_100%` (21) · `DR_CMM` (5) · `DR` (5) · `315895` (2) · `315596` (1) · `DR_CMM +ball 550b` (1) |
| 3195 | 26 | 2 · 10 | `DR` (8) · `Template` (6) · `cav_1` (5) · `cav_7` (5) · `cav_3` (5) · `cav_4` (5) |
| 3197 | 11 | 1 · 3 | `DR` (6) · `DR_8cav.` (4) · `DR_PAR` (1) · `DR cicle` (1) · `DR-90º` (1) · `DR-55º` (1) |
| 3202 | 9 | 1 · 6 | `DR_100%` (5) · `DR_Param` (2) · `DR_N1_N4 & N278 MUNT.+CROQUIS` (2) · `DR_Param_Nous` (2) · `3 postpreasures` (2) · `DR_100% (COSTUMER)` (1) |
| 3205 | 35 | 2 · 4 | `DR_SKETCH` (26) · `DR` (24) · `DR_100%` (8) · `DR_100%_customer` (3) · `DR_parcial` (1) · `DR_Concentricitat_nou_metode` (1) |
| 3206 | 31 | 2 · 7 | `DR_(100%)` (13) · `DR_(SKETCH)` (9) · `DR` (9) · `DR_Concentricitat_nou_metode` (8) · `DR_CMM` (8) · `DR_PARAM(1)` (5) |
| 3212 | 8 | 1 · 3 | `DR(100%)` (6) · `DR(3D)` (3) · `DR(N165)` (2) · `DR` (2) |
| 3214 | 18 | 1,5 · 12 | `DR` (16) · `DR_EC` (2) · `param` (2) · `Sketch2` (1) · `DR_H_Inici_2` (1) · `DR_L_Mig_2` (1) |
| 3218 | 56 | 2,5 · 12 | `DR_100%` (31) · `DR_100%_for PPAP` (20) · `KnO - 3D CMM+ ICLs_ini` (12) · `DR(KnO)` (8) · `DR(VdB)` (4) · `KnO - 3D CMM+ ICLs - after 168h` (4) |
| 3233 | 20 | 2 · 6 | `100%` (11) · `3D CMM` (8) · `100% BOSCH PORTAL` (8) · `23426_real` (4) · `315595` (2) · `316895` (2) |
| 3237 | 34 | 1 · 3 | `DR` (23) · `CP` (5) · `DR (Customer)` (4) · `DRxSPC` (2) · `DR spc` (2) · `DR_100%` (2) |
| 3238 | 15 | 1 · 3 | `DR` (8) · `DR_100%` (5) · `DR_100%_Remesurat 19-06` (1) · `DR_HUM` (1) · `DR-no humid` (1) · `DR-humid` (1) |
| 3288 | 4 | 2,5 · 3 | `DR(base)` (4) · `DR(tapa)` (4) · `DR(tapa)param` (2) |
| 3309 | 8 | 2 · 2 | `DR` (8) · `DR (Cotes Groc i taronja)` (5) |

## Cómo repetirlo

```bash
PY=conocimiento/.venv/Scripts/python.exe
$PY conocimiento/herramientas/valores_por_punto.py                # censo y bloques separados
$PY conocimiento/herramientas/valores_por_punto.py --hojas        # nombres de hoja
$PY conocimiento/herramientas/valores_por_punto.py --cobertura    # cuánto cubre una pestaña y cuánto se repite
$PY conocimiento/herramientas/valores_por_punto.py --sin-intern   # ficheros sin intern.NN, uno a uno
$PY conocimiento/herramientas/valores_por_punto.py --ejemplos 8   # casos al azar para auditarlos
$PY conocimiento/herramientas/consultar.py celdas <id> --hoja DR --filas 25-63   # 338 = 3212 intern.08
```

Si cambian `lector_dr.py` o la biblioteca, hay que repetirlo y actualizar estas cifras.
