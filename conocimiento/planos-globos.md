# Planos con globos: inventario (29/10/2026)

> **Estado de cada plano (los 56, con un tag):** [tabla al final](#estado-de-cada-plano-05112026).
>
> **Lector de globos contra los `.icp` (09/11/2026):** 97,1 % de aciertos en desarrollo, sin errores,
> y 90,5 % en examen, con 14 errores. Medido con el extractor de `.icp` ya corregido.
> [Medición y fallos por plano](#lector-de-globos-contra-los-icp-09112026).
>
> **Lectores de planos numerados (`[]`, `No.`, recuadros) (10/11/2026):** en una muestra al azar de 165
> lecturas, los 165 números están bien leídos; 149 están bien situados y 16 están en una tabla o
> desplazados. La revisión confirma 24 omisiones, casi todas marcas giradas. Los 70 recuadros
> encontrados en planos sin numeración son todos falsos. Solo son los 4 planos conocidos, sin
> validación independiente. [Medición y fallos](#lectores-de-planos-numerados-10112026).

Qué planos de `Exemples` llevan globos (la numeración de cotas dibujada sobre el plano), de qué
color y estilo son, y cuáles traen el `.icp` de infra-CONVERT con el número y la posición de cada
globo. Base: los 56 PDF de plano únicos de la biblioteca (`1- 2D y 3D pieza`, carpetas de globos y
nombres con «drw»; los duplicados exactos cuentan una vez). Qué dibujo y qué revisión es cada PDF, y
qué revisión citan los informes: [planos.md](planos.md).

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

Validada a mano en BSG-296-02 (3288) el 21/10 (cifras de esta sección con el extractor anterior al
09/11/2026, ver [la corrección](#referencia-el-extractor-de-icp-corregido-el-09112026)). El 29/10 se ajustó de forma automática en 19 de
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
número y posición, contados el 29/10 con el extractor anterior. Con el corregido hay más: por ejemplo,
232 en `3202.icp` ([09/11/2026](#referencia-el-extractor-de-icp-corregido-el-09112026)).

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

## Lector de globos contra los `.icp` (09/11/2026)

**Qué se mide.** El lector de globos de color del prototipo,
[`lectores_planos.py`](../prototypes/data-explorer/lectores_planos.py), es el mismo que usa el visor:
RapidOCR y el lector propio en ONNX, un número por plano y umbral de 0,434 en la capa vectorial y de
0,6072 en la imagen. Se ha medido en los 20 planos con globos dibujados y `.icp`, sin cambiar el lector.
- **Referencia:** cada sello del `.icp`, con su número y su posición según la calibración. El
  extractor se corrigió el 09/11/2026 (abajo) y las calibraciones se reajustaron con los sellos
  corregidos.
- **Puntuaciones:** completas.
- **Grupos:** desarrollo (3205 y 3206) y examen (3202 y 3288), por separado.
- **Resultados:** `prototypes/data-explorer/out/probar-planos-2026-11-09-icp2-desarrollo/` y
  `-examen/`, fuera de Git, con `probar_lector_planos.py --grupo … --lectores buscador`.

Qué cuenta en cada columna:
- **Acierto:** lectura ofrecida con el número del sello.
- **Omisión:**
  - *no detectado:* sello sin globo detectado a menos de un radio;
  - *sin lectura:* globo detectado sin lectura ofrecida.
- **Error:**
  - *erróneo:* lectura ofrecida con otro número;
  - *en falso:* lectura ofrecida en una página declarada sin globos.
- **Sin referencia:** lectura ofrecida en un globo sin sello cerca. El `.icp` no permite decir si
  es acierto o error.

| Grupo | Planos | Sellos | Aciertos | No detectados | Sin lectura | Erróneos | En falso | Sin referencia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| desarrollo | 11 | 925 | 898 (97,1 %) | 5 | 22 | 0 | 0 | 0 |
| examen | 9 | 1247 | 1128 (90,5 %) | 12 | 95 | 12 | 2 | 1 |

**Primera medición, con la referencia sin corregir: provisional.** Daba un 95,0 % en desarrollo y un
89,3 % en examen. Parte de sus fallos eran de la referencia, no del lector:
- los 7 «erróneos» de desarrollo;
- 21 de los 37 no detectados;
- casi todas sus 126 lecturas sin referencia.

Las lecturas del lector son las mismas; solo ha cambiado la referencia. Su detalle está en el
commit `d67b52b`.

| | Desarrollo | Examen |
|---|---|---|
| Sellos | 873 → 925 | 1193 → 1247 |
| Aciertos | 829 (95,0 %) → 898 (97,1 %) | 1065 (89,3 %) → 1128 (90,5 %) |
| No detectados | 15 → 5 | 22 → 12 |
| Sin lectura | 22 → 22 | 94 → 95 |
| Erróneos | 7 → 0 | 12 → 12 |
| En falso | 0 → 0 | 2 → 2 |
| Sin referencia | 62 → 0 | 64 → 1 |

| Grupo | Página | Pieza | PDF | Fuente | Sellos | Aciertos | No det. | Sin lect. | Erróneos | En falso | Sin ref. |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| desarrollo | 1931-p1 | 3205 | `3205_DRW ballooned.pdf` | capa vectorial | 75 | 72 | 3 | 0 | 0 | 0 | 0 |
| desarrollo | 1937-p1 | 3205 | `3205_balloned.pdf` | capa vectorial | 96 | 96 | 0 | 0 | 0 | 0 | 0 |
| desarrollo | 1941-p1 | 3205 | `3205-A_balloned.pdf` | capa vectorial | 108 | 108 | 0 | 0 | 0 | 0 | 0 |
| desarrollo | 1942-p1 | 3205 | `3205-A_balloned_1.pdf` | capa vectorial | 108 | 107 | 0 | 1 | 0 | 0 | 0 |
| desarrollo | 1943-p1 | 3205 | `20231129_213137-10300-B_shroud_vG_Ballooned.pdf` | capa vectorial | 110 | 108 | 1 | 1 | 0 | 0 | 0 |
| desarrollo | 1949-p1 | 3205 | `20241121_213137-10300-B_balloned.pdf` | capa vectorial | 109 | 107 | 0 | 2 | 0 | 0 | 0 |
| desarrollo | 2184-p1 | 3206 | `Drw_Marking_DR_intern02.pdf` (sin globos) | imagen | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| desarrollo | 2191-p1 | 3206 | `3206_DRW ballooned.pdf` | mixta | 43 | 43 | 0 | 0 | 0 | 0 | 0 |
| desarrollo | 2197-p1 | 3206 | `3206_balloned.pdf` | capa vectorial | 69 | 68 | 1 | 0 | 0 | 0 | 0 |
| desarrollo | 2201-p1 | 3206 | `3206-A_balloned lr.pdf` | imagen | 68 | 51 | 0 | 17 | 0 | 0 | 0 |
| desarrollo | 2202-p1 | 3206 | `20231129_213137-10280-B_shroud_vG_Ballooned.pdf` | capa vectorial | 70 | 69 | 0 | 1 | 0 | 0 | 0 |
| desarrollo | 2208-p1 | 3206 | `20241121_213137-10280-B_balloned.pdf` | capa vectorial | 69 | 69 | 0 | 0 | 0 | 0 | 0 |
| examen | 4079-p1 | 3202 | `3202_balloned.pdf` | capa vectorial | 232 | 231 | 0 | 1 | 0 | 0 | 0 |
| examen | 4080-p1 | 3202 | `3202_DRW_ballooned.pdf` | capa vectorial | 202 | 198 | 3 | 1 | 0 | 0 | 0 |
| examen | 4088-p1 | 3202 | `3202_balloned low resolution.pdf` | imagen | 232 | 167 | 3 | 61 | 1 | 0 | 0 |
| examen | 4091-p1 | 3202 | `20231129_885253-11250_insulator_motor_v1_ Ballooned.pdf` («G») | capa vectorial | 232 | 192 | 3 | 27 | 10 | 0 | 0 |
| examen | 3049-p1 | 3288 | `BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | mixta | 141 | 138 | 0 | 3 | 0 | 0 | 0 |
| examen | 3113-p1 | 3288 | `2. 20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | mixta | 29 | 28 | 1 | 0 | 0 | 0 | 1 |
| examen | 3114-p1 | 3288 | `20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | mixta | 29 | 28 | 0 | 1 | 0 | 0 | 0 |
| examen | 3122-p1 | 3288 | `BSG-296-2 SOP RCP 3.1 balloned.pdf` | capa vectorial | 120 | 117 | 1 | 1 | 1 | 0 | 0 |
| examen | 3127-p1 | 3288 | `BSG-296-00 SOP RCP 3.1 balonned.pdf` | capa vectorial | 30 | 29 | 1 | 0 | 0 | 0 | 0 |
| examen | 1588-p1 | 3309 | `dwg_ab_77217-02200-000A_2864368.pdf` (sin globos) | imagen | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

Las demás páginas declaradas sin globos no tienen ninguna detección. Posición: x, y en fracción de
la página sin girar.

### Fallos, por plano y página

Se han mirado a ojo, contra el plano, todos los errores, todos los no detectados y la lectura sin
referencia. Están en las hojas `hoja-errores-*.png` y `hoja-tipo-b.png` y en las carpetas de recortes
de `out/probar-planos-2026-11-09-informe/` y `-icp2-informe/`.
- **Azul:** posición de cada sello, con la calibración.
- **Rojo:** el globo o el sello en cuestión.

**Errores del lector: 14, todos en examen.** En las 14 el número es legible y la referencia es
correcta. Diez son del 3202 «G», con números en negrita muy gruesa. Las dos de la página sin globos
(3309) son números del cliente en un círculo azul: un «2» con línea de referencia y un «1» dentro de
una tabla, en la columna «番号 No.». Están bien leídos, pero no son globos de cota.

| Página | Pieza | Sello | Leído | Puntuación | Fuente | Posición |
|---|---|---|---|---:|---|---|
| 4088-p1 | 3202 | 406 | 408 | 0,647 | imagen | 0,31; 0,24 |
| 4091-p1 | 3202 | 335 | 336 | 0,494 | capa vectorial | 0,24; 0,26 |
| 4091-p1 | 3202 | 405 | 406 | 0,481 | capa vectorial | 0,76; 0,30 |
| 4091-p1 | 3202 | 406 | 408 | 0,470 | capa vectorial | 0,76; 0,31 |
| 4091-p1 | 3202 | 350 | 360 | 0,469 | capa vectorial | 0,14; 0,38 |
| 4091-p1 | 3202 | 175 | 176 | 0,704 | capa vectorial | 0,39; 0,41 |
| 4091-p1 | 3202 | 179 | 170 | 0,595 | capa vectorial | 0,39; 0,50 |
| 4091-p1 | 3202 | 161 | 101 | 0,477 | capa vectorial | 0,15; 0,62 |
| 4091-p1 | 3202 | 345 | 346 | 0,519 | capa vectorial | 0,60; 0,67 |
| 4091-p1 | 3202 | 195 | 106 | 0,472 | capa vectorial | 0,35; 0,80 |
| 4091-p1 | 3202 | 289 | 280 | 0,435 | capa vectorial | 0,69; 0,82 |
| 3122-p1 | 3288 | 73 | 731 | 0,443 | capa vectorial | 0,67; 0,21 |
| 1588-p1 | 3309 | no es globo | 2 | 0,986 | imagen | 0,79; 0,26 |
| 1588-p1 | 3309 | no es globo | 1 | 0,623 | imagen | 0,62; 0,63 |

**No detectados: 17, todos del detector.** El globo está dibujado donde cae el sello, con el número
legible, y el detector no lo encuentra.
- 1931-p1: 45, 102, 121
- 1943-p1: 94
- 2197-p1: 50
- 4080-p1: 201, 242, 260
- 4088-p1: 101, 173, 178
- 4091-p1: 17, 101, 163. El 163, en negrita, es nuevo: su sello no estaba en la referencia antigua.
- 3113-p1: 25
- 3122-p1: 2
- 3127-p1: 72

**Sin lectura: 117.** El lector se abstiene. Entre paréntesis, cuántos tenían el número correcto
por debajo del umbral.
- 1942-p1 (1 de 1): 7
- 1943-p1 (0 de 1): 92
- 1949-p1 (0 de 2): 8, 203
- 2201-p1 (13 de 17; ráster de 150 ppp, girado): 1, 2, 3, 9, 12, 20, 21, 23, 30, 40, 43, 60, 71, 76,
  84, 90, 106
- 2202-p1 (0 de 1): 83
- 4079-p1 (1 de 1): 270
- 4080-p1 (1 de 1): 175
- 4088-p1 (45 de 61; ráster de 150 ppp, girado): 2, 6, 7, 9, 12, 14, 21, 26, 27, 32, 33, 34, 35, 36,
  38, 39, 40, 42, 44, 45, 50, 53, 70, 73, 76, 81, 92, 95, 117, 125, 126, 136, 166, 167, 169, 185,
  186, 190, 191, 193, 197, 199, 203, 214, 221, 225, 226, 232, 234, 236, 250, 276, 287, 290, 292, 293,
  294, 300, 302, 335, 350
- 4091-p1 (13 de 27; «G», negritas): 34, 44, 90, 115, 116, 135, 139, 152, 165, 169, 176, 185, 235,
  236, 250, 251, 260, 261, 275, 276, 280, 285, 292, 294, 295, 325, 330
- 3049-p1 (2 de 3): 55, 95, 132
- 3114-p1 (1 de 1): 25
- 3122-p1 (1 de 1): 20

**Sin referencia: 1.** El 80 del 3113-p1 es un globo dibujado y bien leído. El `.icp` de REV.01
(`20250714_BSG-296-00 SOP RCP 3.1.icp`) no tiene ese sello. El otro PDF del mismo `.icp`, el 3114,
no lo dibuja.

**En resumen:**
- **Desarrollo:** 0 errores del lector.
- **Examen:** 14 errores; 10 son del 3202 «G».
- **Omisiones:** 17 del detector y 117 sin lectura. Casi todas las sin lectura están en los dos
  rásteres de 150 ppp (61 en el 4088 y 17 en el 2201) y en el «G» (27).

**Planos con referencia visual, no `.icp`.** Se miden aparte, sin cambios; la referencia es una
lectura visual de Claude.
- **3212** (desarrollo): 111 aciertos de 253 globos (43,9 %), 3 erróneos (156→155, 166→165,
  236.T→235.T), 5 no detectados y 134 sin lectura.
- **3167** (examen): 126 de 212 (59,4 %), 0 erróneos, 14 no detectados y 72 sin lectura. Su
  referencia sigue sin verificar.

### Referencia: el extractor de `.icp`, corregido el 09/11/2026

**Formato.** Cada sello del `.icp` guarda dos cadenas, cada una con su longitud delante (entero de 4
bytes): el texto visible del globo y su nombre, `INFRA_CONVERT_STAMP_<n>`. Después vienen los dos
puntos en doble precisión, el estilo, un índice y el GUID. En los 2.126 sellos de los 19 `.icp`, el
texto visible coincide con el número del nombre y todas las coordenadas tienen sentido.

**Qué fallaba en el extractor anterior.** El fallo era nuestro, no de los ficheros de INTEPLAST.
- **Coordenadas desplazadas.** Leía el número con `INFRA_CONVERT_STAMP_(\d+)`, que se comía la
  primera cifra de la coordenada siguiente cuando ese byte era un dígito ASCII: 1287 por 128.
  - Las coordenadas quedaban desplazadas un byte. Hubo 20 sellos en puntos sin globo y 51 con valores
    fuera de rango, que se guardaban sin posición.
  - Además, 8 sellos se perdían, pisados por un número mal leído: 192 en vez de 19 sustituía al sello 192.
- **Número equivocado.** Tomaba el número de la fila del `.prf` con id = índice − 1, regla deducida
  el 21/10 en BSG-296-02. Cuando el `.prf` se salta filas falla:
  - 7 sellos recibían otro número (el globo 70 del 3205 salía como 45);
  - 49 se quedaban sin número y fuera de la referencia y del visor.

**Corrección** ([`globos_icp.py`](herramientas/globos_icp.py), versión 2):
- el nombre se lee con su longitud;
- el número es el texto visible del propio `.icp`;
- el `.prf` se guarda aparte, en `etiqueta_prf`, solo para contrastar;
- un sello repetido o con un formato inesperado es un error, no se descarta en silencio;
- primero se leen y validan todos los ficheros, y después la tabla `globo` se sustituye en una sola
  transacción. Si falla un fichero o la escritura, queda la tabla anterior. Antes se borraba al
  empezar y un `.icp` defectuoso la dejaba vacía.

Tests con registros sintéticos en `herramientas/test_globos_icp.py`: el byte que parece una cifra, el
`.prf` con saltos, los sellos sin fila, y un `.icp` defectuoso, uno que falta o un fallo al escribir, que
dejan intacta la tabla anterior. Hoy hay 2.126 sellos; el `.prf` coincide en 2.070, discrepa
en 7 y no tiene fila para 49.

**Contraste con el plano.** En las páginas medidas, los sellos cuyo número decide ahora solo el `.icp`
se han contrastado por posición con la lectura del lector: 7 en los que el `.prf` discrepa y 52 casos
sin fila (contando cada página).
- En 59 de 60, el lector ofrece en su globo el número del `.icp`.
- El que falta es el 106 del 2201: sin lectura, con 108 bajo el umbral. El mismo sello es acierto en
  el 2202.

**Calibraciones.** Cada calibración guarda ahora la huella de los sellos con que se ajustó
(`sellos_sha256`) y solo se reutiliza si los sellos no cambian. Las 20 se reajustaron:
- el mismo `.icp` en todas, con ajustes más limpios (por ejemplo, 127 de 173 emparejamientos pasan
  a 140 de 140 en el 3049);
- los sellos se desplazan como mucho 0,00007 del lado de la página, menos de un píxel.

**Qué cambia en el visor.**
- **En las 30 páginas con `.icp`:** 3.094 sellos quedan igual, 40 cambian de sitio (los que estaban
  mal), 163 aparecen por primera vez y ninguno desaparece.
- **Planos sin `.icp`:** no cambian.
- **Total:** el visor pasa de 5.322 a 5.485 globos en las 68 páginas.

| Página | Método | Sellos | Movidos | Nuevos |
|---|---|---|---|---|
| 1931-p1 | calibrada | 71 → 75 | 63 | 37, 61, 84, 203 |
| 1935-p1 · 1937-p1 | 1:1 · calibrada | 91 → 96 | 19, 45, 128 | 14, 36, 37, 70, 101 |
| 1939-p1 · 1941-p1 · 1942-p1 | 1:1 · calibrada | 102 → 108 | 45, 128 | 14, 33, 36, 37, 70, 145 |
| 1943-p1 | calibrada | 104 → 110 | 45, 115, 128 | 14, 33, 36, 37, 70, 148 |
| 1949-p1 | calibrada | 103 → 109 | 93, 94 | 33, 47, 53, 54, 70, 91 |
| 2191-p1 | calibrada | 42 → 43 | 68, 83 | 203 |
| 2195-p1 · 2197-p1 | 1:1 · calibrada | 65 → 69 | — | 7, 102, 104, 106 |
| 2199-p1 · 2201-p1 | 1:1 · calibrada | 62 → 68 | 17 | 7, 62, 67, 104, 106, 107 |
| 2202-p1 | calibrada | 64 → 70 | 17, 45 | 7, 62, 67, 104, 106, 110 |
| 2208-p1 | calibrada | 67 → 69 | — | 14, 110 |
| 3029-p1 · 3049-p1 | 1:1 · calibrada | 129 → 141 | — | 20, 30, 51, 61, 86, 108, 123, 124, 133, 135, 136, 141 |
| 3113-p1 · 3114-p1 · 3116-p1 | calibrada · calibrada · 1:1 | 26 → 29 | — | 26, 60, 71 |
| 3122-p1 · 3124-p1 | calibrada · 1:1 | 112 → 120 | 67 | 14, 17, 19, 28, 42, 45, 58, 120 |
| 3126-p1 · 3127-p1 | 1:1 · calibrada | 29 → 30 | — | 80 |
| 4077-p1 · 4079-p1 · 4086-p1 · 4088-p1 · 4091-p1 | gemela · calibrada · 1:1 · calibrada · calibrada | 226 → 232 | 193, 204 | 1, 16, 110, 119, 163, 227 |
| 4080-p1 | calibrada | 193 → 202 | 71, 185, 210, 406 | 22, 38, 40, 83, 176, 285, 289, 405, 407 |

«Movidos»: sellos con el mismo número a más del 0,5 % del lado de su posición anterior. En el tipo A,
el número del `.prf` (45, 115, 17) pasa al globo que de verdad lo lleva. Copias del estado anterior:
`prototypes/data-explorer/out/referencia-icp-2026-11-09/antes/` (tabla `globo`, calibraciones y lo
que enseñaba el visor), fuera de Git.

## Lectores de planos numerados (10/11/2026)

**Qué se mide.** Los tres lectores de planos sin globos de
[`lectores_planos.py`](../prototypes/data-explorer/lectores_planos.py), tal como los usa el visor:
- `[]210` en el 2820;
- `No. 200` en el 3174 y el 3186;
- números en recuadro en el 3214.

Sin ajustar nada. Las lecturas son exactamente las que enseña el visor (comprobado plano a plano).

**Alcance.** Son los 4 planos donde se probaron estos lectores, y los filtros de recuadros se ajustaron
en el 3214. No hay validación independiente: eso exige planos nuevos, apartados antes de mirarlos. El
3237 y el 3238 tampoco son numerados por OCR: su número está en la capa de texto.

**Cómo.**
- **Lecturas ofrecidas:** una muestra al azar de 40 por plano (semilla 20261110) y las 45 del 3214. En
  cada una se mira por separado si el número es el del plano y si la caja está sobre la marca de
  numeración de una cota (y no sobre el mismo número en una tabla o una nota, ni desplazada).
- **Omisiones:** solo cuentan las marcas vistas en el plano que el lector no ofrece.
  - **2820 y 3214:** barrido a ojo de todas las páginas, con una caja en cada lectura.
  - **3174 y 3186:** se buscan en el plano las cotas de los informes que el lector no encuentra.

  No se ha inventariado todo el plano en el 3174 ni en el 3186: no hay tasa de detección.
- **Informes:** sirven de contraste, no de referencia. Una cota del informe que no aparece y cuya
  marca no se ve en el plano queda como «cota del informe no encontrada».
- **Controles negativos:** planos donde no debería salir nada. Cada detección se revisa antes de
  contarla como falsa.
  - el 3205-B y el `3206.pdf`, dos escaneos limpios donde el visor sí pasa estos lectores;
  - dos escaneos donde el visor no los pasa y aquí se fuerzan: el 3212 rev. 07, con globos, y el
    `Drw_Marking`, con cotas resaltadas.

**Lecturas ofrecidas (muestra):**

| Plano | Pág. | Ofrecidas | Muestra | Número correcto | Ubicación correcta |
|---|---:|---:|---:|---:|---:|
| 2820 `[]` | 1 | 166 | 40 | 40 | 38 |
| 3174 `No.` | 1 · 2 · 3 · 4 | 76 · 59 · 91 · 100 | 10 · 11 · 11 · 8 | 10 · 11 · 11 · 8 | 10 · 11 · 8 · 3 |
| 3186 `No.` | 1 · 2 · 3 · 4 | 75 · 59 · 85 · 100 | 4 · 12 · 15 · 9 | 4 · 12 · 15 · 9 | 4 · 10 · 12 · 8 |
| 3214 recuadros | 1 · 2 | 43 · 2 | 43 · 2 | 43 · 2 | 43 · 2 |
| **Total** | | | **165** | **165** | **149** |

La página 5 del 3174 y del 3186 no ofrece ninguna lectura (es la tabla de cotas por vista).

**Fallos de ubicación (16, todos con el número bien leído):**
- **Tablas de vistas: 14 en total, 8 en el 3174 y 6 en el 3186.** El lector toma por marca el rango
  «No.1600 – No.1611» de la tabla que dice qué cotas salen en cada vista.
  - 3174: 1611, 1900 y 1304 en la p3; 2705, 2407, 2700, 2100 y 2802 en la p4.
  - 3186: 1000 y 1100 en la p2; 1611, 1700 y 1912 en la p3; 2213 en la p4.

  Fuera de la muestra se vio además otro caso: el texto de nota «TO BE MEASURED AT No.1504» (3186, p3).
- **Cajas desplazadas en el 2820: 2 (las notas 254 y 111).** La caja cae sobre el texto de la nota y
  deja la marca fuera. Esas notas, y también la 255 y la 114, se leen dos veces: una caja sobre la
  marca y otra corrida.

**Omisiones confirmadas en la revisión (24).** Hay recorte de cada una en `recortes/`:
- **2820 (barrido de la p1): 10.**
  - **Giradas unos 45°:** 133, 155, 250 y 256.
  - **Otras formas:** 171, vertical; 178, pegada a su cota.
  - **Notas numeradas:** 118 y 115.
  - **Una sola cifra:** 1 y 3. El lector exige dos cifras o más, así que no las lee nunca.
- **3174: 1,** la 401 (p1). Está girada unos 30° sobre el ángulo «90°» en recuadro.
- **3186: 13,** todas marcas giradas:
  - 401 en la p1 (la misma que en el 3174);
  - en la p3: 1208, 1500–1504, 1507–1510, 1604 y 1909.

  El lector sí lee algunas giradas unos 30° (No.1701, No.1702), pero no las de la sección P-P.
- **3214 (barrido de las 2 páginas): ninguna.**

**Contraste con los informes:**
- **3174:** 122 de 129 cotas encontradas.
  - **401:** es una omisión confirmada.
  - **1–5 y 14:** no hay marca `No.` con ese número, porque el plano numera las cotas con 3 o 4
    cifras. Las notas generales del plano llevan esos números; puede que los informes se refieran a
    ellas, pero no está confirmado.
- **3186:** 156 de 168.
  - **11:** son omisiones confirmadas.
  - **Cota 1:** como en el 3174, no tiene marca `No.`.
- **3214:** 42 de 42.
- **El contraste se engaña.** En el 3186, la 1500 y la 1504 cuentan como encontradas, pero solo se
  leen en la tabla de vistas y en el texto de una nota; sus marcas giradas no se leen.

**Controles negativos: 70 detecciones, las 70 falsas.**
- **Marcas `[]` y `No.`:** ninguna detección en las 4 páginas.
- **Recuadros:** 21 en el 3205-B y 19 en el 3206 (planos donde el visor sí los pasa), y 18 y 12 en los
  dos forzados. Todo son recuadros que no numeran nada:
  - cotas básicas (12.02, 1.65…);
  - celdas de marcos de tolerancia (0.15, 0.1);
  - radios en recuadro (R4, R22);
  - letras de referencia leídas como cifras (B como 8, E como 3).

  El lector de recuadros lee cualquier número enmarcado. Lo que deja el 3205-B y el 3206 como «Sin
  globos ni numeración» es la regla del tag: hacen falta 15 recuadros que cubran la mitad de las cotas
  de los informes.

**Pendiente:**
- **Las 11 cotas con letra del 3214** (`A4`, `D5`, `F3`…). En el barrido no aparecen como recuadro.
  Las letras A–F y las cifras 1–8 del marco son la cuadrícula de zonas del plano; podrían ser
  referencias de zona, pero no está comprobado.
- **Validación independiente:** necesita planos numerados nuevos.

**Reproducir.** Con [`probar_lectores_numerados.py`](../prototypes/data-explorer/probar_lectores_numerados.py),
en tres fases: `leer`, `muestra` e `informe`. Todo queda en
`prototypes/data-explorer/out/probar-numerados-2026-11-10/`, fuera de Git:
- las lecturas, con la identidad del lector (huellas del código y versión de RapidOCR);
- `muestra.json`, con la semilla y la selección;
- `revision.json`, con las decisiones a ojo, cada una ligada al PDF y a la lectura exacta que se
  revisó (si cambian, deja de contar y hay que revisarla de nuevo);
- `informe.json`;
- los recortes, las hojas de revisión y el barrido.

## Estado de cada plano (05/11/2026)

Cada plano lleva un solo tag, según cómo se puede buscar una cota en él. Lo decide
[`leer_planos.py`](../prototypes/data-explorer/conocimiento/leer_planos.py), sin revisión manual:

| Tag | PDF | Búsqueda por número |
|---|---:|---|
| **Con `.icp`** | 30 | Número y posición salen del `.icp`, tenga o no los globos dibujados |
| **Globos sin `.icp`** | 7 | Lector de globos del prototipo ([`lectores_planos.py`](../prototypes/data-explorer/lectores_planos.py), el mismo que usan las medidas; hasta el 09/11/2026, la copia de la aplicación, con las mismas lecturas). Lectura automática |
| **Numerado sin globos** | 6 | `[]210`, `No. 200` y recuadros con OCR (lectura automática); sobrerrayados, por la capa de texto |
| **Sin globos ni numeración** | 13 | No se puede; como mucho, el texto del plano. Tinte rojo en el visor |

**Qué significa `.icp` en un plano limpio.** Cada sello guarda la cabeza del globo y la punta que
señala la cota (`x1, y1` y `x2, y2`). Por eso el visor reconstruye el globo sobre el plano sin
dibujar: el número en el círculo y una línea hasta la cota. En 9 de los 10 planos limpios el `.icp`
cae a un 0,1–0,3 % de la hoja de su sitio en la versión globada, con escala 1:1 y origen en el
centro. La excepción es `20231129_885253-11250_insulator_motor_v1.pdf`, con la hoja a la mitad: el
1:1 deja en la hoja 91 de sus 232 sellos (cifra recalculada el 10/11/2026 con el extractor corregido).
Usa la calibración de su versión globada, porque el `.icp` es el mismo y coinciden las formas de la
hoja. Un `.icp` no garantiza todos los globos: el 80 del 3113 está dibujado y no está en el `.icp` de
REV.01. El ejemplo que había aquí, el 3205 con 93 sellos situados de 96 globos, era un fallo del
extractor anterior; hoy sus 96 sellos tienen número y posición.

**Cómo se decide el tag sin `.icp`:**
- **Globos:** al menos 20 aros y al menos el 40 % leídos. Así salen `Drw_Marking` (125 aros, 0
  leídos: son cotas resaltadas) y el 3309 (70 aros, 2 leídos: dibujo en azul).
- **Numerado:** al menos 20 marcas `[]` o `No.`; o el 80 % de las cotas de los informes como número
  en la capa de texto; o al menos 15 recuadros que cubran la mitad de esas cotas.

**Qué fiabilidad tienen las lecturas (revisado a ojo con muestras al azar):**

| Lector | Planos | Resultado |
|---|---|---|
| Globos | 7 PDF: 1.332 leídos de 1.946 | Muestra de 96: ningún error claro, 2 dudosos a esa resolución (3238 `9891`, 3202 `286`). En otra muestra del 3195, 1 de 22 mal: lee `1210.T` donde pone 1630, con 0,985 de confianza |
| `[]` | 2820 | Muestra de 40 (10/11/2026): 40 números bien, 38 bien situados (2 cajas desplazadas). 10 omisiones confirmadas en el barrido. Sin informes con los que contrastar |
| `No.` | 3174 y 3186 | Muestras de 40 (10/11/2026): 80 números bien; 32 y 34 sobre su cota, el resto en tablas de vistas. 1 y 13 omisiones confirmadas, marcas giradas. Contraste: 122 de 129 y 156 de 168 cotas de informes |
| Recuadros | 3214, escaneo | 45 de 45 bien (10/11/2026), sin omisiones en el barrido, 42 de 42 cotas numéricas de informes. **Sus filtros se ajustaron en este mismo plano: no es una medida independiente**. En planos sin numeración lee cualquier número enmarcado (70 detecciones, todas falsas) |

Detalle en [Lectores de planos numerados](#lectores-de-planos-numerados-10112026). Las muestras
anteriores (36 y 24) no guardaron su selección; las del 10/11 son reproducibles.

Límites: 614 globos quedan sin leer (234 del 3195, 148 del 3212, 113 del 3167), y buscarlos no da
resultado. Las 11 cotas con letra del 3214 (`A4`, `D5`, `F3`…) no aparecen en el OCR ni, en el
barrido del 10/11/2026, como recuadro: siguen pendientes. Buscar en el 3237 o el 3238 también encuentra otras cifras de su
texto (`30` y `30°`). Los lectores de `[]`, `No.` y recuadros son prototipo: solo se han probado en
estos 4 planos y no están en la aplicación.

`20231129_213137-10300-B.pdf` y `3206.pdf` (2003) son la rev. B de 10/2023 (ECI 211G23-066 y -067),
el mismo dibujo que las versiones globadas de `…-B_231011/` ([planos.md](planos.md#3205-y-3206--aisin-shroud-150-w-y-240-w)),
pero el detector no encuentra globos y su carpeta no tiene `.icp`: van como «Sin globos ni numeración».

Generada con `leer_planos.py --tabla`; no editar a mano.

<!-- tabla-planos:inicio -->
| Pieza | Plano | Tag | Pág. | Detalle |
|---|---|---|---:|---|
| 3202 | `20231129_885253-11250_insulator_motor_v1.pdf` | Con .icp | 1 | 232 sellos de `885253-11250_G.icp`; sin globos dibujados, calibración de la gemela |
| 3202 | `20231129_885253-11250_insulator_motor_v1_ Ballooned.pdf` | Con .icp | 1 | 232 sellos de `885253-11250_G.icp`; globos dibujados, calibración |
| 3202 | `3202.pdf` | Con .icp | 1 | 232 sellos de `3202.icp`; sin globos dibujados, calco 1:1 |
| 3202 | `3202_DRW_ballooned.pdf` | Con .icp | 1 | 202 sellos de `insulator_240W_ballooned.icp`; globos dibujados, calibración |
| 3202 | `3202_balloned low resolution.pdf` | Con .icp | 1 | 232 sellos de `3202.icp`; globos dibujados, calibración |
| 3202 | `3202_balloned.pdf` | Con .icp | 1 | 232 sellos de `3202.icp`; globos dibujados, calibración |
| 3205 | `20231129_213137-10300-B_shroud_vG_Ballooned.pdf` | Con .icp | 1 | 110 sellos de `213137-10300-  -B.icp`; globos dibujados, calibración |
| 3205 | `20241121_213137-10300-B_balloned.pdf` | Con .icp | 1 | 109 sellos de `20241121_213137-10300-B.icp`; globos dibujados, calibración |
| 3205 | `3205-A.pdf` | Con .icp | 1 | 108 sellos de `3205-A.icp`; sin globos dibujados, calco 1:1 |
| 3205 | `3205-A_balloned.pdf` | Con .icp | 1 | 108 sellos de `3205-A.icp`; globos dibujados, calibración |
| 3205 | `3205-A_balloned_1.pdf` | Con .icp | 1 | 108 sellos de `3205-A.icp`; globos dibujados, calibración |
| 3205 | `3205.pdf` | Con .icp | 1 | 96 sellos de `3205.icp`; sin globos dibujados, calco 1:1 |
| 3205 | `3205_DRW ballooned.pdf` | Con .icp | 1 | 75 sellos de `Shroud_150W_ballooned.icp`; globos dibujados, calibración |
| 3205 | `3205_balloned.pdf` | Con .icp | 1 | 96 sellos de `3205.icp`; globos dibujados, calibración |
| 3206 | `20231129_213137-10280-B_shroud_vG_Ballooned.pdf` | Con .icp | 1 | 70 sellos de `213137-10280-  -B.icp`; globos dibujados, calibración |
| 3206 | `20241121_213137-10280-B_balloned.pdf` | Con .icp | 1 | 69 sellos de `20241121_213137-10280-B.icp`; globos dibujados, calibración |
| 3206 | `3206-A.pdf` | Con .icp | 1 | 68 sellos de `3206-A.icp`; sin globos dibujados, calco 1:1 |
| 3206 | `3206-A_balloned lr.pdf` | Con .icp | 1 | 68 sellos de `3206-A.icp`; globos dibujados, calibración |
| 3206 | `3206.pdf` | Con .icp | 1 | 69 sellos de `3206.icp`; sin globos dibujados, calco 1:1 |
| 3206 | `3206_DRW ballooned.pdf` | Con .icp | 1 | 43 sellos de `Shroud_240W_ballooned.icp`; globos dibujados, calibración |
| 3206 | `3206_balloned.pdf` | Con .icp | 1 | 69 sellos de `3206.icp`; globos dibujados, calibración |
| 3288 | `2. 20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 29 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 29 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `20250714_BSG-296-00 SOP RCP 3.1.pdf` | Con .icp | 1 | 29 sellos de `20250714_BSG-296-00 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `BSG-296-00 SOP RCP 3.1 .pdf` | Con .icp | 2 | 30 sellos de `BSG-296-00 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `BSG-296-00 SOP RCP 3.1 balonned.pdf` | Con .icp | 1 | 30 sellos de `BSG-296-00 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | Con .icp | 1 | 141 sellos de `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-2 SOP RCP 3.1 balloned.pdf` | Con .icp | 1 | 120 sellos de `BSG-296-2 SOP RCP 3.1.icp`; globos dibujados, calibración |
| 3288 | `BSG-296-2 SOP RCP 3.1.pdf` | Con .icp | 1 | 120 sellos de `BSG-296-2 SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
| 3288 | `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` | Con .icp | 3 | 141 sellos de `Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.icp`; sin globos dibujados, calco 1:1 |
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
