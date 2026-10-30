# Planos con globos: inventario (29/10/2026)

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
  - **3174 (Autoliv):** «No. 214» sobre la cota; vectorial sin capa de texto.

  El resto de originales está sin revisar. El detector de color no ve ninguno de estos estilos.
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
