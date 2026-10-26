# 1- Clips en Piezas

> `Exemples/1- Clips en Piezas`. 1.049 ficheros, 4,9 GB. Leído el 2026-10-21. Único feature con un
> nivel intermedio: `Tipo A/` y `Tipo B/`, y dentro las piezas. Rutas relativas a esa carpeta.
> Perfiles: tablas `perfil_ppap` (542 hojas) y `perfil_correccion` (890 diapositivas).

## Piezas

| Grupo | Pieza | Qué es | Nº pieza cliente | Plano en la carpeta | Correcciones |
|---|---|---|---|---|---|
| Tipo A | **3174** | Bearing Plate STD | 649473000A | `6494730` rev 004 | 11 loops (03/2023 → 05/2026) |
| Tipo A | **3186** | Bearing Plate | 654169100A | `6494730` rev 002 ⚠️ | 6 loops con PPTX hasta 02/2024; entregas XLS posteriores hasta loop 9 (06/2025) |
| Tipo A | **3218** | Bearing Plate R230 P2 SAMS | 654695200B | `6494730` rev 004 ⚠️ (copia exacta del de 3174) | Numeración hasta **loop 15** (01/2024 → 08/2026), con lagunas: [3218.md](3218.md) |
| Tipo B | **3195** | Brush holder (Bosch) | 3134341864 | `0130S0002K` D 01 | N1–N6 (10/2023 → 12/2025) |
| Tipo B | **3226** | Manifold (`DW-UMED-2-2`) | — | `DW-UMED-2-2` REV01 | Solo análisis de holguras con la pieza 3227 |
| Tipo B | **3309** | Support stopper (`77217-12300`, *fuel tank filler pipe*) | — | `77217-02200-000A` (escaneo) | 3 entregas (04/2026 → 08/2026) |

«Tipo A» agrupa placas de rodamiento (*bearing plates*) que se montan con clips; «Tipo B», piezas
con clips de otro tipo (portaescobillas, soporte). Qué criterio usa INTEPLAST para A/B no consta.

## Qué es el clip y cómo se controla

- 3174 y 3218: el método (`6- Método de medición/3174_00_MM_revNN.xls` y `3218_00_MM_revNN.xls`,
  hoja `DIMENSIONS`) tiene filas *«MEASURE THE POSITION OF THE CLIP»* (`N712` en 3174; `N2612`,
  `N2905` en 3218). En el 3174 el equipo pasa de `CT - SCAN` (rev03–05) a `CMM` (rev06–07).
- 3186: el ensayo del cliente (`E507287_TES.docx`, `TES_E04021504.docx`, inglés/alemán) exige montar
  la placa *«clip by clip»* y numera los clips según el plano 617 2994.
- 3309: *«CHECK THE DISTANCE BETWEEN CLIPS (UP & DOWN). PART MUST BE CLIPPED AND MEASURED ON CMM»* (`N15`).
- Informes con columna *«CMM PROGRAM PART CLIPPED»* y notas *«clipped - measured 4.7.2025»*: la
  pieza se mide montada, no libre. Es una condición de medida que la app no recoge.

Correcciones que tocan directamente el clip (selección, `perfil_correccion`):
3174 2.12 (*«Move the clips num. 2 and num. 3»*, 0,1 mm), 3195 1.17 (*«correct 0,04mm only in the clip
surface»*) y 3218 10.4/10.7 (diámetro; el texto dice que la posición está OK), 10.9 (posición del clip
por cavidad, solo en Z) y 15.1 (redondez 0,1 frente a 0,02–0,03 de los otros clips).
Las acciones 1.9, 1.28 y 1.34 están en `3218/…/20240119_1st loop of correction/20230314-Mold
correction_1_P3174.pptx`: pese al nombre heredado **P3174**, la diapositiva 1 identifica explícitamente
*«these tool 3218»* y lo compara con 3186/3174 (I-302). Sí aporta evidencia del 3218: 1.9 propone
0,05 mm por lado del clip; 1.28/1.34, 0,07 mm por lado (0,14 mm total).
En 3195, la versión `Toolmaker_comments_rev3` renumera 1.17 como 1.16 y añade *«It is not need to correct
acording Anita 26/01/2024»*; la propuesta de 0,04 mm no acredita un retoque ejecutado.

## Diferencias con el 3212

| | 3212 | Clips |
|---|---|---|
| Método de medida | DOCX | **XLS estructurado** (`MM_revNN.xls`, hoja `DIMENSIONS`: N-number, equipo, instrucción), varias revisiones; ensayos del cliente en DOCX |
| Metrología | CSV CMM + XLS | **Casi solo XLS PPAP** (1 CSV en toda la carpeta); hojas `DR_CMM`, `DR (2)`…; subcarpetas `Interns/`, `Version 00/Customer/` |
| Cavidades | Cuatro: c13–c16 (`INTRO!C40` en los nueve informes) | 4, 8, 12, 16, 24… según hoja; varias hojas con columnas de cavidad repetidas |
| Correcciones | 2 planes | Hasta 15 loops, cada uno en carpeta `YYYYMMDD_Nth loop…`, con varias versiones (`draft`, `rev1`, `Updated`, `V1/V2`, `Toolmaker_comments`) |
| Plantilla | `Tool correction n.m (DIM. Nr.x)` | La misma en 3174, 3186, 3195 y 3218; **3309 usa `Tool correction DIM#5: …`** con autor y fecha; 3226 no es un plan sino holguras de montaje |
| Marcador `OK` | 11–15 | 100 en 3195 (versiones con comentarios del matricero) |
| Idiomas | catalán | inglés mayoritario, catalán, alemán, **checo** (`3174 korekční plán.pptx`, `3186 drnost.msg`) |
| Otros | — | correos `.msg`, vídeos `.MOV`/`.mp4`, fotos de lotes defectuosos, programas CMM (`.cab`, `._PI`), proyectos de globos |

🔴 **Valores generados con `RAND()`** (I-003): `3174_SPC*.xlsm` y los 25 `3195/…/Interns/N*.xlsm` son libros
«Cpk generator»; en 8 informes del 3174 (`intern.29`…`.32`, `INF09`) y 27 del 3218 (`intern.23`…`.36` y los
de los loops 10–15) hay hojas con muestras calculadas con `RANDBETWEEN` a partir de las medidas (en
`3218-00_intern.23.xls` en las propias hojas `CAV_n`). Consultar `celda_aleatoria` antes de usar un valor.

Moldflow: `.mfr` solo en 3174 y 3309 (con `debug.log` y una caché de GPU del visor); 3195 y 3226 tienen
un `README.txt`.

## Incongruencias

Detalle en [incongruencias.md](../incongruencias.md): planos de 3186/3218 que son el del 3174 (I-301),
plan del 3218 con nombre heredado P3174 (I-302), cabeceras PPAP de otros proyectos (I-303), fechas
imposibles (I-304).
