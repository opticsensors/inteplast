# Planos con globos: inventario (29/10/2026)

> **Estado de cada plano (los 56, con un tag):** [tabla al final](#estado-de-cada-plano-05112026).

Qué planos de `Exemples` llevan globos (la numeración de cotas dibujada sobre el plano), de qué
color y estilo son, y cuáles traen el `.icp` de infra-CONVERT con el número y la posición de cada
globo. Base: los 56 PDF de plano únicos de la biblioteca (`1- 2D y 3D pieza`, carpetas de globos y
nombres con «drw»; los duplicados exactos cuentan una vez).

**Cómo se midió.** Primera página de cada PDF a 150 ppp: recuento de píxeles verdes, azules y
rojos, y el detector de `prototypes/data-explorer/buscar_en_plano.py`, que busca círculos verdes
o azules de un radio entre el 0,4 y el 1,1 % del lado corto de la página. Los recuentos de globos y
la calibración del `.icp` salen de `probar_lector_planos.py`, sobre el ráster original
(`out/probar-planos/resultados.json`, fuera de Git). Lo marcado como **visto** se comprobó en
recortes ampliados. Lo demás sale solo de los recuentos.

## Resumen

| Tipo | PDF | Piezas |
|---|---|---|
| Globos azules de infra-CONVERT | 25 | 3167, 3195, 3202, 3205, 3206, 3237, 3238, 3288 |
| Globos verdes | 1 | 3212 (244 verdes y 8 azules) |
| Globos que el detector no ve | 1 | 3206, `213137-01028-10/3206_DRW ballooned.pdf` |
| Sin globos de color | 29 | Originales del cliente, versiones sin globos y falsas detecciones (abajo) |

- **Los globos de color los pone INTEPLAST, no el cliente.** Los planos de `1- 2D y 3D pieza`
  llegan sin globos de color, salvo el 3212 y el 3202 rev. A. INTEPLAST los globa en el PC de la
  CMM ZEISS con infra-CONVERT y los guarda en `6- Método de medición`, junto al `.icp`/`.prf`
  ([formato](4-tetones/3288.md#planos-con-globos)).
- **Pero varios originales traen su propia numeración de características, en negro.** Visto
  ampliado el 29/10/2026:
  - **2820 (Bosch):** «□153» junto a la cota; dibujo vectorial sin capa de texto.
  - **3214 (Clunas):** número en un recuadro bajo la cota, como «22» o «47»; escaneo.
  - **3174 (Autoliv):** «No. 214» sobre la cota; vectorial sin capa de texto. **3186:** igual.
  - **3237 y 3238 (`2D 05`):** número sobrerrayado junto a la cota, en la capa de texto (05/11/2026).

  El detector de color no ve ninguno de estos estilos. Quién lleva cada uno, en la
  [tabla final](#estado-de-cada-plano-05112026).
- **Lo habitual es un globo azul con su `.icp`.** 20 de los 27 PDF con globos lo traen en su
  carpeta o en la de una copia idéntica. Sin `.icp`: 3212, 3167, 3195, 3202 rev. A, 3237, 3238 y
  la copia del BSG-296-02 en `5- Retoques molde` del 3288, que no es idéntica.
- **El color del número varía.** Es negro dentro de un aro azul en el 3205, el 3206 y el 3202 «G»
  (visto); azul en el 3167, el 3195 y el 3237 (visto); y verde en el 3212. El resto no se ha revisado.
- **Estilos que complican la lectura** (vistos):
  - negritas muy gruesas (3202 «G»);
  - números de cuatro cifras (3167, 3195);
  - racimos de globos solapados (3167, 3195, 3212);
  - texto negro del plano bajo el número (3237);
  - página girada 90° (los «low resolution» del 3202 y el 3206);
  - globos grises de SOLIDWORKS Inspection junto a los azules (3206 `213137-01028-10`).

## Cómo están hechos los PDF con globos

Comprobado con PyMuPDF el 29/10/2026 (imágenes, trazados y palabras de la página 1):

- **20 de los 27: el dibujo es una imagen escaneada y los globos son vectores encima.** Son los de
  infra-CONVERT del 3202, 3205, 3206 y 3288, salvo las versiones «low resolution». El aro azul
  está hecho de cientos de segmentos cortos y el interior blanco de bandas horizontales. Los
  números son formas negras rellenas, no texto: hay 0 palabras y no se pueden buscar con Ctrl+F.
  Se ven nítidos a cualquier zoom.
- **7 de los 27: todo es imagen, globos incluidos.** Son el 3212, el 3167, el 3195, el 3237, el
  3238 y los dos «low resolution» (3202 y 3206-A).
- En el 3206 `213137-01028-10`, los globos grises de SOLIDWORKS Inspection no tienen trazados:
  forman parte de la imagen. Los azules sí son vectores.

**Consecuencia:** en los 20 primeros, la página dibujada sin sus imágenes deja solo los globos y
sus números, sin el plano detrás. Es la vía vectorial de
[`probar_lector_planos.py`](../prototypes/data-explorer/probar_lector_planos.py).

**Versiones sin globos junto a las globadas.** En varias carpetas con `.icp` está también el
plano sin globos. El `.icp` corresponde a la versión globada, no a estas. Revisadas a ojo, página
por página, el 29/10/2026:

| Página | Qué es |
|---|---|
| 3205 `213137-10300/3205.pdf` p1 | El mismo plano escaneado, sin globos ni capa vectorial (1 imagen, 0 trazados) |
| 3205 `213137-10300-A/3205-A.pdf` p1 | Plano rev. A escaneado, sin globos ni capa vectorial |
| 3206 `213137-10280/3206.pdf` p1 | Plano escaneado, sin globos ni capa vectorial |
| 3206 `213137-10280-A/3206-A.pdf` p1 | Plano rev. A escaneado, sin globos ni capa vectorial |
| 3202 `20231129_885253-11250_insulator_motor_v1.pdf` p1 | Plano escaneado (15 imágenes), sin globos ni capa vectorial |
| 3202 `885253-11250/3202.pdf` p1 | Plano escaneado, sin globos ni capa vectorial |
| 3288 `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` p1–p3 | B. Braun, vectorial (sin imágenes): hojas BSG-296-01, -00 y -02, sin globos |
| 3288 `REV.01/…/20250714_BSG-296-00 SOP RCP 3.1.pdf` p1 | B. Braun, vectorial, sin globos |
| 3288 `REV.01/…/BSG-296-2 SOP RCP 3.1.pdf` p1 | B. Braun, vectorial, sin globos |
| 3288 `REV.02/BSG-296-00 SOP RCP 3.1 .pdf` p1 y p2 | B. Braun, vectorial (versión 4), sin globos; la p2 es la página de firmas |

Esto prueba que los globos del `.icp` de su carpeta no están en esas páginas, no que no haya
ninguna numeración: en los B. Braun hay marcas «cc» de cota crítica, sin número. En la evaluación
del prototipo se declaran por página (`NO_BALLOON_PAGES` en `probar_lector_planos.py`), y cualquier
lectura que se ofrezca en ellas cuenta como falsa.

**Referencia visual del 3167** (29/10/2026, lectura de Claude sin verificar):
`prototypes/data-explorer/out/referencia-3167/chuleta-3167-2026-10-29.json`, fuera de Git. Tiene
212 globos legibles, 50 candidatos que no son globo y 61 dudosos en racimos ilegibles a la
resolución del ráster, unos 77 ppp en A1. Pendiente de verificar por Eduard con dos muestras
separadas (`muestra_verificacion.py`, semilla 20261029):
- una aleatoria de 40 entre las 262 entradas juzgadas;
- otra de 20 globos en racimos.

Solo la aleatoria estima la fiabilidad de la referencia.

## Calibración `.icp` → PDF

Validada a mano en BSG-296-02 (3288) el 21/10. El 29/10 se ajustó de forma automática en 19 de
los 20 PDF con `.icp`. El ajuste es un RANSAC con giro, escala, desplazamiento y simetría
vertical, que toma como emparejamientos tentativos las lecturas OCR de los globos. En esos 19, el
detector encuentra **1.992 de los 2.024 sellos** que tienen número y posición (98,4 %). De sus
2.116 detecciones, 124 (5,9 %) no corresponden a ningún sello.

Falta el 3206 `213137-01028-10`. Sus globos son azul puro (RGB medio 14, 14, 255), pero miden
unos 33 px de radio en la imagen reducida que usaba el detector, que solo admitía hasta 28 px.
Con el detector de dos pasadas y la vía vectorial (29/10/2026) se detectan 41 globos, y 38 casan
con los 43 sellos de `Shroud_240W_ballooned.icp`.

## Por PDF

Globos = círculos que encuentra el detector en el ráster original. Sellos = sellos del `.icp` con
número y posición.

| Pieza | PDF | Globos | `.icp` (sellos) | Notas |
|---|---|---|---|---|
| 3167 | `6- Método de medición/Drawing baloneed.pdf` | 293 | — | Cuatro cifras; racimos |
| 3195 | `Ballooned DRW/1 - 0130S1B006-DRW-000-07-1-EN DE_ballown.pdf` | 820 | — | Cuatro cifras; racimos densos |
| 3202 | `1- 2D y 3D pieza/20241121_885253-11250-A_INSULAT balooned.pdf` | 230 | — | Rev. A |
| 3202 | `Ballooned DRW/3202_balloned.pdf` | 232 | `3202.icp` (226), en la carpeta de su copia | |
| 3202 | `885253-01125-10/3202_DRW_ballooned.pdf` | 199 | `insulator_240W_ballooned.icp` (193) | |
| 3202 | `885253-11250/3202_balloned low resolution.pdf` | 229 | `3202.icp` (226) | Girada; 150 ppp |
| 3202 | `885253-11250-G/…_ Ballooned.pdf` | 231 | `885253-11250_G.icp` (226) | Negritas muy gruesas |
| 3205 | `213137-01030-10/3205_DRW ballooned.pdf` | 73 | `Shroud_150W_ballooned.icp` (71) | |
| 3205 | `213137-10300/3205_balloned.pdf` | 96 | `3205.icp` (91) | |
| 3205 | `213137-10300-A/3205-A_balloned.pdf` y `_1.pdf` | 108 y 108 | `3205-A.icp` (102) | |
| 3205 | `213137-10300-B_231011/…_Ballooned.pdf` | 109 | `213137-10300-  -B.icp` (104) | |
| 3205 | `213137-10300-B_241028/…_balloned.pdf` | 109 | `20241121_213137-10300-B.icp` (103) | |
| 3206 | `213137-01028-10/3206_DRW ballooned.pdf` | 0 | `20230202_…_DRW.icp` (287 sellos) y `Shroud_240W_ballooned.icp` (43) | Globos mayores que el rango del detector; también grises de SOLIDWORKS Inspection |
| 3206 | `213137-10280/3206_balloned.pdf` | 68 | `3206.icp` (65) | |
| 3206 | `213137-10280-A/3206-A_balloned lr.pdf` | 68 | `3206-A.icp` (62) | Girada; 150 ppp |
| 3206 | `213137-10280-B_231011/…_Ballooned.pdf` | 69 | `213137-10280-  -B.icp` (64) | |
| 3206 | `213137-10280-B_241028/…_balloned.pdf` | 69 | `20241121_213137-10280-B.icp` (67) | |
| 3212 | `1-2D y 3D Pieza/20250523_DRW 0140S00237_07.pdf` | 263 | — | Escaneo; cifras de unos 5 px; verdes. [Ficha](0-bolt-eye/3212/1-pieza-2d-3d.md) |
| 3237 | `6- Método de medición/OLD/1 - 3130589019_D_03_balloned.pdf` | 111 | — | Texto negro del plano bajo los números |
| 3238 | `6- Método de medición/OLD/1 - 313058901F_D_03_balloned.pdf` | 123 | — | |
| 3288 | `5- Retoques molde/…/BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | 140 | `Cj20240714_…_RCP 3.1.icp` (129), en la carpeta de su copia | |
| 3288 | `5- Retoques molde/…/BSG-296-2 SOP RCP 3.1 balloned.pdf` | 120 | — | Versión distinta de la de `REV.01` |
| 3288 | `REV.01/BSG-296-00/2. 20250714_…_balloned.pdf` | 29 | `20250714_BSG-296-00 SOP RCP 3.1.icp` (26) | |
| 3288 | `REV.01/BSG-296-00/20250714_…_balloned.pdf` | 29 | ídem (26) | |
| 3288 | `REV.01/BSG-296-02/BSG-296-2 SOP RCP 3.1 balloned.pdf` | 120 | `BSG-296-2 SOP RCP 3.1.icp` (112) | |
| 3288 | `REV.02/BSG-296-00 SOP RCP 3.1 balonned.pdf` | 30 | `BSG-296-00 SOP RCP 3.1.icp` (29) | |

## Sin globos de color (29 PDF)

- **Originales del cliente**: 2820, 3051, 3056, 3167 (`DRAFT_V07`), 3168, 3195, 3197, 3205, 3206,
  3214, 3233 (dos), 3237, 3238 y 3288 (`Cj20240714_…`, tres páginas). Que no tengan globos de
  color no quiere decir que no tengan números: el 2820 y el 3214 traen su numeración en negro
  (arriba).
- **Versiones sin globos junto a las globadas**:
  - 3202: `3202.pdf` e `insulator_motor_v1.pdf`;
  - 3205: `3205.pdf` y `3205-A.pdf`;
  - 3206: `3206.pdf` y `3206-A.pdf`;
  - 3288: los BSG-296-00/02 sin globos.
- **Falsas detecciones del detector**:
  - 3206 `Drw_Marking_DR_intern02.pdf`: cotas resaltadas en azul;
  - 3309: texto azul y símbolos ②;
  - 3226: logo azul de INTEPLAST;
  - 3174 y 3186: una detección verde en cada uno, sin revisar. El 3174 numera sus cotas con
    «No. NNN» (arriba).

## Qué implica

- **Si el plano trae `.icp`, no hace falta leer nada.** Número y posición salen del fichero, con
  la calibración anterior ([caso A](../docs/ingesta-automatica.md#24-localizar-cotas-en-el-plano-2d-28102026)).
- **Los `.icp` también sirven para probar lectores y detector** sin lectura manual: es la
  referencia de la [comparativa del prototipo](../prototypes/data-explorer/README.md#prueba-en-todos-los-planos-con-globos-29102026).
- **El detector solo ve aros verdes o azules.** Desde el 29/10/2026 ya no tiene un tamaño fijo:
  primero mide el tamaño típico de los globos de cada plano. Sigue sin ver los globos grises o
  negros, ni la numeración del cliente en recuadros o etiquetas.

## Estado de cada plano (05/11/2026)

Cada plano lleva un solo tag, según cómo se puede buscar una cota en él. Lo decide
[`leer_planos.py`](../prototypes/data-explorer/conocimiento/leer_planos.py), sin revisión manual:

| Tag | PDF | Búsqueda por número |
|---|---:|---|
| **Con `.icp`** | 30 | Número y posición salen del `.icp`, tenga o no los globos dibujados |
| **Globos sin `.icp`** | 7 | Lector de globos de la aplicación (`backend/app/ingestion/`). Lectura automática |
| **Numerado sin globos** | 6 | `[]210`, `No. 200` y recuadros con OCR (lectura automática); sobrerrayados, por la capa de texto |
| **Sin globos ni numeración** | 13 | No se puede; como mucho, el texto del plano. Tinte rojo en el visor |

**Qué significa `.icp` en un plano limpio.** Cada sello guarda la cabeza del globo y la punta que
señala la cota (`x1, y1` y `x2, y2`). Por eso el visor reconstruye el globo sobre el plano sin
dibujar: el número en el círculo y una línea hasta la cota. En 9 de los 10 planos limpios el `.icp`
cae a un 0,1–0,3 % de la hoja de su sitio en la versión globada, con escala 1:1 y origen en el
centro. La excepción es `20231129_885253-11250_insulator_motor_v1.pdf`, con la hoja a la mitad: el
1:1 dejaba 88 de 228 puntos en la hoja. Usa la calibración de su versión globada, porque el `.icp`
es el mismo y coinciden las formas de la hoja. Un `.icp` no garantiza todos los globos (en el 3205,
93 sellos con número y posición de 96 globos dibujados).

**Cómo se decide el tag sin `.icp`:**
- **Globos:** al menos 20 aros y al menos el 40 % leídos. Así salen `Drw_Marking` (125 aros, 0
  leídos: son cotas resaltadas) y el 3309 (70 aros, 2 leídos: dibujo en azul).
- **Numerado:** al menos 20 marcas `[]` o `No.`; o el 80 % de las cotas de los informes como número
  en la capa de texto; o al menos 15 recuadros que cubran la mitad de esas cotas.

**Qué fiabilidad tienen las lecturas (revisado a ojo con muestras al azar):**

| Lector | Planos | Resultado |
|---|---|---|
| Globos | 7 PDF: 1.332 leídos de 1.946 | Muestra de 96: ningún error claro, 2 dudosos a esa resolución (3238 `9891`, 3202 `286`). En otra muestra del 3195, 1 de 22 mal: lee `1210.T` donde pone 1630, con 0,985 de confianza |
| `[]` | 2820 | Muestra de 36 tras corregir la cuarta cifra pegada: 36 números bien, 1 con la marca desplazada. Sin informes con los que contrastar |
| `No.` | 3174 y 3186 | 94,6 % de 129 y 92,9 % de 168 cotas numéricas de informes. Muestras de 24: 21 y 24 sobre su cota; las otras 3 son el número correcto en una tabla o nota |
| Recuadros | 3214, escaneo | 45 de 45 bien y todas las cotas numéricas de los informes (42 de 42, más 45.1 y 45.2). **Sus filtros se ajustaron en este mismo plano: no es una medida independiente** |

Límites: 614 globos quedan sin leer (234 del 3195, 148 del 3212, 113 del 3167), y buscarlos no da
resultado. Las 11 cotas con letra del 3214 (`A4`, `D5`, `F3`…) no aparecen en el OCR; no se ha
comprobado si están en el plano. Buscar en el 3237 o el 3238 también encuentra otras cifras de su
texto (`30` y `30°`). Los lectores de `[]`, `No.` y recuadros son prototipo: solo se han probado en
estos 4 planos y no están en la aplicación.

`20231129_213137-10300-B.pdf` y `3206.pdf` (2003) parecen el mismo dibujo que versiones globadas de
otra carpeta, pero el detector no encuentra globos y su carpeta no tiene `.icp`: van como «Sin globos
ni numeración».

Generada con `leer_planos.py --tabla`; no editar a mano.

<!-- tabla-planos:inicio -->
| Pieza | Plano | Tag | Pág. | Detalle |
|---|---|---|---:|---|
| 3202 | `20231129_885253-11250_insulator_motor_v1.pdf` | Con .icp | 1 | 226 sellos de `885253-11250_G.icp`; sin globos dibujados, calibración de la gemela |
| 3202 | `20231129_885253-11250_insulator_motor_v1_ Ballooned.pdf` | Con .icp | 1 | 226 sellos de `885253-11250_G.icp`; globos dibujados, calibración |
| 3202 | `3202.pdf` | Con .icp | 1 | 226 sellos de `3202.icp`; sin globos dibujados, calco 1:1 |
| 3202 | `3202_DRW_ballooned.pdf` | Con .icp | 1 | 193 sellos de `insulator_240W_ballooned.icp`; globos dibujados, calibración |
| 3202 | `3202_balloned low resolution.pdf` | Con .icp | 1 | 226 sellos de `3202.icp`; globos dibujados, calibración |
| 3202 | `3202_balloned.pdf` | Con .icp | 1 | 226 sellos de `3202.icp`; globos dibujados, calibración |
| 3205 | `20231129_213137-10300-B_shroud_vG_Ballooned.pdf` | Con .icp | 1 | 104 sellos de `213137-10300-  -B.icp`; globos dibujados, calibración |
| 3205 | `20241121_213137-10300-B_balloned.pdf` | Con .icp | 1 | 103 sellos de `20241121_213137-10300-B.icp`; globos dibujados, calibración |
| 3205 | `3205-A.pdf` | Con .icp | 1 | 102 sellos de `3205-A.icp`; sin globos dibujados, calco 1:1 |
| 3205 | `3205-A_balloned.pdf` | Con .icp | 1 | 102 sellos de `3205-A.icp`; globos dibujados, calibración |
| 3205 | `3205-A_balloned_1.pdf` | Con .icp | 1 | 102 sellos de `3205-A.icp`; globos dibujados, calibración |
| 3205 | `3205.pdf` | Con .icp | 1 | 91 sellos de `3205.icp`; sin globos dibujados, calco 1:1 |
| 3205 | `3205_DRW ballooned.pdf` | Con .icp | 1 | 71 sellos de `Shroud_150W_ballooned.icp`; globos dibujados, calibración |
| 3205 | `3205_balloned.pdf` | Con .icp | 1 | 91 sellos de `3205.icp`; globos dibujados, calibración |
| 3206 | `20231129_213137-10280-B_shroud_vG_Ballooned.pdf` | Con .icp | 1 | 64 sellos de `213137-10280-  -B.icp`; globos dibujados, calibración |
| 3206 | `20241121_213137-10280-B_balloned.pdf` | Con .icp | 1 | 67 sellos de `20241121_213137-10280-B.icp`; globos dibujados, calibración |
| 3206 | `3206-A.pdf` | Con .icp | 1 | 62 sellos de `3206-A.icp`; sin globos dibujados, calco 1:1 |
| 3206 | `3206-A_balloned lr.pdf` | Con .icp | 1 | 62 sellos de `3206-A.icp`; globos dibujados, calibración |
| 3206 | `3206.pdf` | Con .icp | 1 | 65 sellos de `3206.icp`; sin globos dibujados, calco 1:1 |
| 3206 | `3206_DRW ballooned.pdf` | Con .icp | 1 | 42 sellos de `Shroud_240W_ballooned.icp`; globos dibujados, calibración |
| 3206 | `3206_balloned.pdf` | Con .icp | 1 | 65 sellos de `3206.icp`; globos dibujados, calibración |
| 3288 | `2. 20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 26 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 26 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `20250714_BSG-296-00 SOP RCP 3.1.pdf` | Con .icp | 1 | 26 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `BSG-296-00 SOP RCP 3.1 .pdf` | Con .icp | 2 | 29 sellos de `BSG-296-00 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `BSG-296-00 SOP RCP 3.1 balonned.pdf` | Con .icp | 1 | 29 sellos de `BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | Con .icp | 1 | 129 sellos de `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-2 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 112 sellos de `BSG-296-2 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-2 SOP RCP 3.1.pdf` | Con .icp | 1 | 112 sellos de `BSG-296-2 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` | Con .icp | 3 | 129 sellos de `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3167 | `Drawing baloneed.pdf` | Globos sin .icp | 1 | 126 leídos de 239 detectados; 68% de 150 cotas de informes |
| 3195 | `1 - 0130S1B006-DRW-000-07-1-EN DE_ballown.pdf` | Globos sin .icp | 1 | 629 leídos de 863 detectados; 83% de 616 cotas de informes |
| 3202 | `20241121_885253-11250-A_INSULAT balooned.pdf` | Globos sin .icp | 1 | 212 leídos de 229 detectados; 90% de 190 cotas de informes |
| 3212 | `20250523_DRW 0140S00237_07.pdf` | Globos sin .icp | 1 | 114 leídos de 262 detectados; 59% de 120 cotas de informes |
| 3237 | `1 - 3130589019_D_03_balloned.pdf` | Globos sin .icp | 1 | 65 leídos de 111 detectados; 58% de 102 cotas de informes |
| 3238 | `1 - 313058901F_D_03_balloned.pdf` | Globos sin .icp | 1 | 68 leídos de 123 detectados; 54% de 114 cotas de informes |
| 3288 | `BSG-296-2 SOP RCP 3.1 balloned.pdf` | Globos sin .icp | 1 | 118 leídos de 119 detectados; 83% de 140 cotas de informes |
| 2820 | `20160817_DRW_3130516933_0140S00050-DRW-000-02-1-EN_DE.pdf` | Numerado sin globos | 1 | 166 marcas `[]`; sin informes con los que contrastar |
| 3174 | `20250219_6494730_004.pdf` | Numerado sin globos | 5 | 326 marcas `No.`; 95% de 129 cotas de informes |
| 3186 | `20230123_6494730_002.pdf` | Numerado sin globos | 5 | 319 marcas `No.`; 93% de 168 cotas de informes |
| 3214 | `R-2718, R-2971_C11692_rev.B.pdf` | Numerado sin globos | 2 | 45 marcas `recuadro`; 100% de 42 cotas de informes |
| 3237 | `20260914_3130589019 2D 05.pdf` | Numerado sin globos | 1 | número en la capa de texto: 99% de 102 cotas de informes |
| 3238 | `20260914_313058901F 2D 05.pdf` | Numerado sin globos | 1 | número en la capa de texto: 98% de 114 cotas de informes |
| 3051 | `20211205_0140S00275-DRW_pendent acceptació.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3056 | `20240417_DRW_0131S00135_D_04.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3167 | `20260727_0130S00338_DRAFT_V07.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3168 | `20260727_0130S00337_DRAFT_V02.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3195 | `20241121_3134341864_0130S0002K_D_01.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3197 | `20240222_0140S00363 D 02.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3205 | `20231129_213137-10300-B.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3206 | `3206.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3206 | `Drw_Marking_DR_intern02.pdf` | Sin globos ni numeración | 1 | 125 aros de color sin números legibles |
| 3226 | `20241028_DW-UMED-2-2_REV01.PDF` | Sin globos ni numeración | 1 | nada encontrado |
| 3233 | `20230728_DRW_0196S0000K_D_01.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3233 | `20250316_DRW_0196S0000K_D_02.pdf` | Sin globos ni numeración | 1 | nada encontrado |
| 3309 | `dwg_ab_77217-02200-000A_2864368.pdf` | Sin globos ni numeración | 1 | 70 aros de color sin números legibles |
<!-- tabla-planos:fin -->
