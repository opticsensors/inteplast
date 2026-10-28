# Incongruencias y cosas que habría que pedir o aclarar

Lo que no cuadra en los datos de `Exemples`, con su evidencia. **No son preguntas redactadas para
INTEPLAST** (eso vive en `docs/preguntas-abiertas.md`): es el material de
partida. Cada entrada tiene su registro en [hallazgos.jsonl](hallazgos.jsonl) con el mismo id.

Estados: `abierta` (sin explicar), `explicable` (hay una hipótesis razonable, sin confirmar),
`resuelta` (confirmada con evidencia).

## Transversales (afectan a varias piezas)

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-001 | **Bloques de medidas repetidos entre informes PPAP sucesivos.** Ya visto en el 3212 (N117/N118 de `intern.05` = `intern.03`; `intern.09` mezcla `.01` y `.08`). En el 3288, `DR(base)` es idéntica en `intern.02/.03/.04` y coincide al 94 % con `.01`. Parece una práctica: actualizar solo lo que se vuelve a medir y heredar el resto. Un lector no puede tratar cada informe como medición completa. **3202**: `intern.02` repite `intern.01` en 176 de 189 cotas de `DR_100%`. **3309**: `Int_02` repite `Int_01` celda a celda en las cotas 3, 5, 8, 19, 26 y 27, así que en esas cotas no hay valores nuevos hasta `Int_03`, posterior también al plan 2; los datos no dicen si se volvió a medir ([3309](1-clips/3309.md)). **3186**: la 1604 no cambia, celda a celda, de `intern.03` a `intern.20` (14 informes). | 3212: [historial-molde §8](0-bolt-eye/3212/historial-molde.md); 3288: `perfil_ppap` y comparación celda a celda; 3202 y 3309: `medida_dr`, comprobado en el original (cotas 101 y 5) | abierta |
| I-002 | **Valor `0` dentro de celdas de medida** con nominal distinto de 0 (3–4 por informe en `DR(tapa)` del 3288). Puede representar medida no realizada, pieza ausente u otro caso; el significado no está confirmado. Conservar el cero original y marcarlo para revisión. | `perfil_ppap.ceros` | explicable |
| I-004 | **PDF con extensión `.xls` interpretado como celdas** en el 3168. El lector XLS v2 detecta la firma y lo extrae como dos páginas PDF. | Firma `%PDF-1.7`; detalle debajo | resuelta |
| I-003 | 🔴 **Valores generados con `RAND()` en libros de medición.** 649.977 celdas en 191 libros de 9 piezas tienen fórmulas aleatorias (`RAND`, `RANDBETWEEN` —también con su nombre en castellano, `ALEATORIO.ENTRE`—, `NORM.INV(RAND(),…)`): su valor no es una medición. Tres casos: **(a)** el libro «Cpk generator» (detalle abajo), con generación documentada de SPC `#P#` en 3167/3237 y coincidencias sin fórmula de origen en 3168; **(b)** informes PPAP con las muestras 2–5 calculadas a partir de la muestra 1; **(c)** columnas auxiliares en un R&R (3168) y 180 fórmulas del 3167: 170 funcionan y solo 10 contienen `#REF!`, todas en `Int_06.xls!DR_100%`. No consta para qué se usaron ni qué se entregó al cliente. | tabla `celda_aleatoria` (`formulas_aleatorias.py`); detalle abajo | abierta |
| I-005 | **El campo *Customer Name* de los libros no identifica al cliente de forma fiable.** De 592 libros con `INTRO!C23`, **229 conservan `XXX`** de la plantilla (12 piezas; es el único valor en 3051, 3205, 3226 y 3233), 4 dicen `B-Braun` por la plantilla heredada del 3247 (I-303) y el mismo cliente aparece como `Robert Bosch`, `ROBERT BOSCH`, `BOSCH` o `RB`. Para atribuir cliente: normalizar variantes, ignorar `XXX` y contrastar con la cabecera `DR` y la carpeta. Comprobado en tres originales (`DR_17.xls`, `3217_DR_intern17.xls`, `3309-00 Int_02.xls`). | `INTRO!C23`; p. ej. `3205/4- Metrologia/Customer/3205-00_intern.01.xls` (`XXX`), `3237/…/3237-00_intern.03-a.xls` (`RB`) | abierta |
| I-006 | **Copias del mismo muestreo con valores distintos**, sin nada que diga cuál vale (todas con la fecha de la copia a OneDrive). 3309 `Int_03`: `Customer/3309-00 Int_03.xls` da 0,749–0,781 en la fila 38 (cota 14) y `Customer/P3309-00 Int_03.xls` 0,84–0,90; las 12 celdas distintas de `DR` son de las cotas 14 y 16, y solo la segunda copia cuadra con el T3 (*«#14 and #16 are now in tolerance»*). 3202 `intern.03`: la copia interna repite en la cota 33 los valores de `intern.01` (0,34–0,38) y la del cliente trae otros (0,427–0,44); en la 312 (2 ±0,09) la interna da 2,091–2,205 (12 de 12 fuera) y la del cliente 2,073–2,089 (0 de 12), que repite el `PPAP-3202-00_INF.01` de 01/2024. No consta si es una medición nueva. Como I-603. La cadena conserva las copias distintas como alternativas y marca cuándo la conclusión depende de la copia. | `DR!I38:L38` de las dos copias del 3309; `DR_100%` filas 28 y 423–425 / 412–414 del 3202; comprobado en los originales | abierta |
| I-007 | **Copias del mismo muestreo con los mismos valores y tolerancias distintas**: 25 grupos en 4 piezas (3195: 12, 3174: 5, 3218: 5, 3168: 3). En el 3174 y el 3168 la copia para el cliente lleva una tolerancia más amplia: 3174 `intern.26`, cota 504, ±0,15 frente a ±0,07 (0/24 y 6/24 fuera); 3168 `intern.12`, cota 1540, −0,1 frente a −0,05/−0,07 (0/96 y 71/96 fuera). En el 3218 `intern.34` la diferencia va en los dos sentidos y en el 3195 no cambia el recuento. Una tolerancia distinta no demuestra por sí sola una modificación indebida (puede ser una desviación acordada o otra versión del plano, como I-603). La cadena agrupa las copias también por tolerancias. | Celdas de tolerancia de las cuatro copias, comprobadas en los originales por COM | abierta |

### I-003 en detalle

Comprobado el 2026-10-21 con las fórmulas guardadas en los ficheros (openpyxl para xlsx/xlsm, Excel por
COM para xls) y la macro VBA extraída con `olevba`. Se describe qué hace cada libro, no por qué.

**Actualización 23/10/2026:** el contraste XML de los 322 XLSX/XLSM incorpora **1.255 fórmulas
reales sin valor cacheado** de `INTRO` en 114 generadores y retira **84 textos** que empiezan por
`=` pero son cadenas (`sharedStrings`, sin elemento XML `f`). Ajuste neto +1.171: **649.977**
fórmulas directas en 191 libros. Se repararon `celda` y `celda_aleatoria`, preservando valores
vacíos como NULL y los textos originales como texto. Ejemplos: `3174_SPC.xlsm!INTRO!M5:T5`
y `3167_Cpk generator_SPC_N1220.10.xlsm!INTRO!I5:T5` (omitidas), `INTRO!E21` de este último
(texto, no fórmula). El lector XLSX v2 conserva estas distinciones al regenerar; después se
reconstruye `celda_aleatoria` con `formulas_aleatorias.py`, sin reparación manual.

La igualdad de secuencias demuestra correspondencia entre archivos, pero no siempre su proceso
de generación: en 3168 faltan las fórmulas de origen de los SPC. El título PDF del 3237-20 es un
indicio del libro usado, no prueba de sus fórmulas ni de la procedencia de cada valor.

**(a) «Cpk generator»** (`…Cpk generator_SPC_N*.xlsm` del 3167, `3174_SPC*.xlsm`, `3195/…/Interns/N*.xlsm`,
`3233-Cpk traccio.xlsm`, `PPAP_3237_INF_02_SPC.xlsm`: 114 libros con la misma hoja `INTRO`).

- Entrada en `INTRO!E2:T5`, por cavidad: *Min Real* y *Max Real*, o un único *Value Real* y un *Delta Real*.
  En `3167_Cpk generator_SPC_N1220.10.xlsm`: valores 0,114 / 0,103 / 0,115 / 0,194 y delta 0,02; *Made by*
  Xavier Arcos, *Equipment* 3D CMM, *Amount of parts/cav* 50, ruta `C:\Users\ZEISS-CMM\Desktop\3167 SPC`.
- Media y dispersión (`E7`, `E9`): media = (min+max)/2 o *Value Real* más un ruido `RAND()`; desviación =
  rango/4,5. El delta de las cavidades 2–4 es el de la 1 multiplicado por `0,8+0,4·RAND()`.
- `Z2:AO51` = `MROUND(NORM.INV(RAND(), media, desviación), precisión)`: **50 valores por cavidad**
  (columnas Z–AC = cavidades 1–4; AD–AO quedan en `ERROR` si no hay más cavidades). Las filas 11–17
  calculan media, rango, Cm/Cp y Cmk/Cpk de esos 50 valores (Cmk 8,9 en N1220.10, cavidad 1).
- La macro `Generate_Sheets` copia cada cavidad a una hoja `N<cota>_Cav_<n>` (valores fijos en la columna 52)
  y escribe `INTRO!B36\INTRO!B35_Cav_<n>.txt` con líneas `#P#;…`.
- **Correspondencia de SPC `#P#` con hojas de salida**: todas las secuencias del fichero (todas sus líneas, valor a valor)
  aparecen en una hoja de salida `N…_Cav_n` en 328 de 328 SPC del 3167 (82 generadores de
  `PPAP-3167-00_4/Estudis Estadístics/`), 39 de 40 del 3168 (`3168_spc *.xlsx`: mismas hojas de salida
  pero sin `INTRO`, así que no se ve cómo se calcularon) y los 4 `3237_SPC_Cav_n.txt` del 3237
  (`PPAP_3237_INF_02_SPC.xlsm`). Los 88 SPC del 3237-20 (`Support_V20_Inf_03/3237-20 SPC/`) no están en
  ningún libro de Exemples; sus 22 PDF se imprimieron desde `Cpk generator_IQS.xlsm` (metadato *title*),
  que no se ha entregado.

**(b) Informes con muestras calculadas** (5 muestras por cavidad, columnas J–N):

| Pieza | Libros | Fórmula | Dónde |
|---|---|---|---|
| 3233 | `PPAP_3233_Inf_01.xlsm` | `ROUNDUP(J ± RAND()/1000·5; 3)` | K–N de `cav_1`…`cav_32` (muestra 1 ± 0,005) |
| 3233 | 12 xls (`intern.01`…`.08`, `inf.06`, …) | `RAND()*(máx−mín)+mín` con los límites escritos en la fórmula (p. ej. `RAND()*(0.7-0.5)+0.5`) | hoja `100% (CUSTOMER)`, 2.354 celdas por libro |
| 3237, 3238 | `PPAP_3237_INF_01/02`, `PPAP_3238_INF_01/02` (`.xlsm`) | `ROUND(J − W + 2·W·RAND(); X)` | columnas auxiliares Y–AB; W = *Factor*, X = *Round* |
| 3237, 3238 | `PPAP_3237-20_INF_03`, `PPAP_3238-20_INF_01/02` | ídem, 5 columnas | Y–AC |
| 3218 | 27 xls (20 de `4- Metrologia`, `intern.23`…`.36`; 7 de los loops 10–15) | `RANDBETWEEN(I·(1 ± 0,0005))` (o ± 0,2 %) | J–M; en `Customer/Version 00/3218-00_intern.23.xls` en las propias `CAV_n`, en los demás en copias `CAV_n (2)` |
| 3174 | 8 xls (`intern.29`…`.32`, `INF09`) | `RANDBETWEEN` entre las muestras I y J | K–M de copias `CAV.n (2)` |
| 3206 | 2 xls (`intern.121`, `.122`) | `RANDBETWEEN(valor·0,9998; valor·1,0002)` | copia `DR_(customer) (2)` de la hoja `DR_(customer)` |

En `PPAP_3237_INF_02` y `PPAP_3238_INF_02` las muestras 2–5 que se ven (K–N, valores fijos) caen **todas**
dentro de J ± W (4.400 de 4.400) y su desviación respecto a J se reparte de forma aproximadamente
plana entre 0 y W (29/24/23/24 % por cuartos en el 3237). Es compatible con el generador, pero
esa distribución por sí sola no demuestra el origen de valores fijos ni permite excluir mediciones.
En los 3174/3218 tampoco hay una señal concluyente en las hojas principales.

**(c) Otros.** `3168-R&R.xlsx`: columnas auxiliares `ROUND(min + (max−min)·RAND())` junto a la tabla del
estudio R&R. En 18 XLS del 3167 hay **180 fórmulas aleatorias**: 170 son
`=ROUND($O$19+$O$22*RAND(),$O$20)` y conservan resultados numéricos en `O23:O32` de
`DR_100%` o `DR_100%_old` (17 libros). Solo las 10 de
`4- Metrologia/Interns/3167-00 Int_06.xls!DR_100%!O17:O26` están rotas:
`=ROUND(#REF!+$O$16*RAND(),$O$14)`. Comprobado en los 18 originales leyendo los registros
BIFF `FORMULA`/`SHRFMLA` y sus valores guardados; `Int_06` contiene referencias inválidas
y error `#REF!`, mientras los otros 17 conservan valores numéricos generados.

**Para la app**: estas celdas no se pueden ingerir como medición. Antes de leer un libro, consultar
`celda_aleatoria` y las dependencias/copia de valores. Los SPC y Cmk/Cpk vinculados a valores
generados no acreditan capacidad medida. Donde falte esa trazabilidad, dejar la procedencia sin confirmar.

### I-004 · PDF archivado con extensión XLS

`7- Planitudes/3168/4- Metrologia/Customer/3168-00_intern.13_6injecton points.xls` comienza por
`%PDF-1.7` y contiene **dos páginas PDF**, con ocho columnas CAV.1–CAV.8. La extracción anterior
lo había importado como texto binario en Excel: hoja ficticia `copia`, 1.868 elementos y 2.613
celdas. El 23/10/2026 se sustituyó esa extracción de `documento.id=4218` por las dos páginas
reales y se eliminaron las falsas celdas. Tras autorizarse el cambio de código, el lector XLS v2
detecta `%PDF-` antes de invocar Excel y aplica el lector PDF automáticamente. **Resuelta también
al regenerar**, conservando el original intacto.

## 0- Bolt Eye

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-201 | **Posible arrastre de Excel en la identificación de material** del 3197: la cota 200 (visual) vale `PPS-GF40`, `PPS-GF41` … `PPS-GF47` en CAV.1–8. Debería ser el mismo material en todas. | `3197 Pot/5- Retoques de molde/3197-00_intern.02_MOLD_CORRECTION.xls!DR_8cav.` fila 34 | explicable |
| I-202 | **Plan de corrección «4» del 3197 sin PPTX**: existe `3197-00_intern.09_correction04.xls` (columna `Correction`), pero solo hay PPTX de los planes 1–3. | `3197 Pot/5- Retoques de molde/` | abierta |
| I-203 | **Hoja copiada durante dos años en el 3051**: `DR(4CAV_CMM) (2)`, fechada el 15/01/2021 (91 cotas, 82 NOK, 219 ceros), aparece igual en `intern.08`, `.09`, `.10` y `.11` (este último de 02/02/2023). | `perfil_ppap`; `3051 Pump Housing/4- Metrologia/3051-00_intern.08..11.xls` | abierta |
| I-204 | **Las dos variantes de la corrección 2 del 3212 no son equivalentes**: `rev1.pptx` lleva 11 marcadores `OK` y `rev1_.pptx` 15 (añade 2.13/2.15/2.16/2.17). Además 2.15 cambia Ø0,22 a Ø0,21 y 2.16, −0,305 a −0,300 mm. No se puede elegir una por el nombre ni interpretar `OK` como ejecución confirmada. | XML de ambas versiones, diapositivas 13, 15, 16, 17 | abierta |
| I-205 | **Plano del 3051 etiquetado como pendiente de aceptación**: el único plano se llama `…0140S00275-DRW_pendent acceptació.pdf`. El nombre no demuestra su estado vigente de aprobación. | `3051 Pump Housing/1-2D y 3D Pieza/` | abierta |
| I-206 | **Tolerancia variable de N230 en el 3197**: +0,13 en `intern.09/.10` y `correction04`, frente a +0,10 en `.11` y el plano. No consta autorización. | `DR!F27:F30` de `.10`, `DR!F33:F36` de `.11` | abierta |
| I-207 | **Velocidad y numeración de inserción distintas en 3212**: el DOCX N287 indica 0,1 mm/s; el plano rev07, globo 289, 0,2 mm/s; globos 288/288.1 indican 15–50 N en recorrido de 1 mm. El cajetín fecha rev07 el 21/06/2022; 23/05/2025 es impresión PDF. Confirmar especificación/revisión aplicable. | DOCX N287 y PDF rev07, página 1 | abierta |

## 1- Clips en Piezas

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-301 | **Plano equivocado en 3186 y 3218**: el PDF del 3218 es copia byte a byte del plano del 3174 (`6494730` rev 004, SHA `31219eb5e961`); el del 3186 es `6494730` rev 002. Sus STEP son `6541691` y `6546952` y sus números de pieza 654169100A y 654695200B. Falta el plano propio de cada uno. | `Tipo A/3186/1- 2D y 3D pieza/20230123_6494730_002.pdf`; `Tipo A/3218/1- 2D y 3D pieza/20250219_6494730_004.pdf` | abierta |
| I-302 | **Nombre heredado de otra pieza**: el PPTX llamado `20230314-Mold correction_1_P3174.pptx` dentro del loop 1 del 3218 tiene 39 diapositivas y la primera identifica explícitamente la herramienta **3218**, comparada con 3186/3174. El plan del 3174 tiene 22 diapositivas y no es el mismo: no excluir el de 3218 por su nombre. Persisten nombres/numeraciones de plan 1 y 3 en carpetas de loops 2 y 4 del 3186. | XML de ambos PPTX; [3218.md](1-clips/3218.md) | explicable |
| I-303 | **Plantilla PPAP del 3247 reutilizada sin cambiar la cabecera**: `3218/…/20250518 6th correction/3217_DR_intern17.xls` (y su `Copia de …`), `3186/…/20250609_9th loop/DR_20.xls` y, añadido el 27/10/2026, `2- Nervios de Soldadura/3206/…/20250709_correction after ribs inserts/DR_17.xls` tienen hojas `DR(base)`/`DR(tapa)` con *ITP Ref.* 732470000 y *PPAP Ref.* `3247-00_int.01`; su *Customer Name* es `B-Braun` (I-005). Además el nombre cita la pieza **3217**, que no está en Exemples. | `perfil_ppap.metadatos`; `INTRO!C23` | abierta |
| I-305 | **Historia incompleta del 3218**: no se han localizado los planes de los loops **2–5**; el loop 1 sí tiene contenido referido al 3218, pese al nombre P3174. El loop 6 numera todo `1.1` y el del loop 14 conserva `13.x`, aunque añade resultados y acciones. | [3218.md](1-clips/3218.md) | abierta |
| I-306 | **Plan 2 del 3195 con fecha de 2020 en el nombre**: `N2/OLD/20200527-Mold correction_2_P3195_Toolmaker_comments_rev1 (sliders).pptx` (acciones 2.10–2.11, otra redacción que la rev2 del 10/06/2024). Probable errata por 20240527: la misma carpeta tiene un XLS del plan 2 fechado 20240502. | `3195/5- Retoques molde/N2/OLD/` | explicable |
| I-307 | **El plan de la carpeta N6 del 3195 se numera 5.x**: `N6/20251205-Mold correction_6_P3195.pptx` repite 5.1 y 5.2 de la rev1 del plan 5 y su 5.3 propone **aumentar** 0,015 mm por lado la cota 2660, que el plan 5 (5.5) proponía **reducir** 0,025 mm por lado. Identificar el plan por carpeta y fecha. | `3195/5- Retoques molde/N5/`, `N6/` | explicable |
| I-308 | **Código de cota equivocado en un informe del 3195**: `Interns/3195-00_int_05.xls!DR_HR%` fila 46 dice 2360 entre las filas 2500.3/2500/2500.2, con el nominal 8 de la 2500 (la 2360 es 5 +0,22 +0,13). Probable errata por 2500.1; solo en ese libro. Agrupar por código mezcla las dos cotas. | `DR_HR%!A44:I53`, comprobado en el original | explicable |
| I-309 | **El plan del loop 2 del 3174 lleva el plan 1 del 3186 dentro**: `20230512-Mold correction_2_P3174.pptx` (34 diapositivas) solo tiene propias la 1, 2, 3 y 5 (acciones 2.1–2.4); las otras 30 (numeradas 1.3–1.32) tienen el mismo texto que `3186/…/20230421-Mold correction_1_P3186.pptx`, en las mismas posiciones de la 7 a la 34, y citan cotas que solo se miden en 3186/3218 (1300, 1411, 1502…1910). No son acciones del 3174. Como la familia comparte numeración (I-301), las cotas 300–511 existen en ambas y no sirven para atribuirlas. La cadena lo avisa en cada fila. | `perfil_correccion` (texto idéntico) y XML de los dos PPTX | abierta |
| I-304 | **Fechas de informe imposibles o no fechas**: `1899-12-31` (fecha cero de Excel) y `xx` en informes de 3186, 3195 y 3218; también texto `29.08.2024` en lugar de fecha. | `perfil_ppap.metadatos.report_date` | explicable |

## 2- Nervios de Soldadura

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-401 | **¿Qué versión del plan se ejecutó?** En el 3206, diapositiva 2: `20250723_Pla de correció_1 (after…)` +0,15/+0,3; `20250729_…` sin sufijo +0,05/+0,25; `_customer` +0,1/+0,15/+0,25 según zona. La copia de 29/07 archivada en 3205 conserva cotas del 3206: no asignar pieza ni vigencia solo por carpeta. | `3206/5- Retoques molde/20250709_correction after ribs inserts/`; `3205/…/7th loop…` | abierta |
| I-402 | **El PPTX base del loop 5 del 3205 es el plan del 3206.** `3205/5- Retoques molde/5th loop of correction GPF/20240411-Mold correction_new sliders_loop1.pptx` lleva la cabecera *«Pla de correccions nº1 – P3206»* (21/03/2024) y el mismo texto en sus 6 diapositivas que `3206/…/20240321-Mold correction_new sliders_loop1.pptx` y `3206/…/20240422-Mold correction_rebaves.pptx`, con las mismas imágenes por diapositiva y SHA-256 distintos (comprobado en los originales). Las versiones `_v1`/`_v2` de esa carpeta no nombran pieza (*Correcció nr. 2.1, DIM. Nr.1, Ø 28 ± 0,05*). Mismo patrón que I-401. | `3205/…/5th loop of correction GPF/`; `3206/…/20240320_After new sliders correction/`, `…/20240422_corr burrs/` | abierta |

## 5- Anclajes

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-501 | **Feature sin datos**: solo un `Readme.txt` que dice que la información *«ya fue entregada anteriormente»*, sin indicar dónde. | `5- Anclajes/Readme.txt` | abierta |

## 6- Pockets

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-601 | **Nombre de fichero, numeración y fecha no coinciden**: `20240214_Mold correction_1_P3167.pptx` contiene las correcciones `2.1`, `2.5`…`2.11` (plan 2, con `2.10` repetida); la versión PDF del plan 2 fecha las diapositivas el *14/02/2023* dentro de una carpeta y fichero de 2024. | `3167/5- Retoques molde/2n loop of corrections/` | abierta |
| I-602 | **Planes del 3056 sin texto**: el contenido está en imágenes; solo se lee el título de cada diapositiva. Para extraerlo haría falta OCR o lectura visual. | `3056/5- Retoques molde/20200207-Tool correction_1_P3056.pptx` | abierta |
| I-603 | **Dos versiones del PPAP Inf_04 con valores distintos.** `PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm` difiere de `PPAP-3167-00_Inf_04.xlsm` en las tolerancias (columna G en 118 filas por cavidad, F en 12: cotas 2010–2070, 2580, 2730.\*, 2740.\*; p. ej. 2580, nominal 0,66, pasa de −0,05 a −0,1 y 2730.T, 39,31, de −0,1 a −0,2) y en 8 de 11.808 celdas de medida. Los 8 valores cambiados quedaban por debajo del nuevo límite inferior y en esta versión aparecen en el límite o por encima: 2580 `cav_1` 0,55 → 0,56/0,57 (3 valores); 2730.T `cav_2` 39,086–39,092 → 39,111–39,121 (5 valores, límite 39,11). La copia de `PPAP-3167-00_4/Uploaded to IQS/` tiene los valores y tolerancias originales. Las cotas 2730/2740 son las de la posible aceptación recogida en la corrección 2.3 (*«The customer can accepted the deviation for the pocket 1 and 13…»*, H-602), sin aprobación formal acreditada de esas tolerancias; el cambio de valores no tiene explicación en los datos. | `3167/4- Metrologia/Customer/PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm` `cav_1!J483:N483`, `cav_2!J558:N558`, columna G | abierta |

## 7- Planitudes

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-701 | **Carpeta fechada en el futuro**: `3168/5- Retoques molde/20270728_ModificacioLamelasGPF/`. ¿2023? ¿2026? | ruta | abierta |
| I-702 | **Fichero de otra pieza y fecha posterior a su carpeta**: `20230823_Modification/20260612_3167_modification proposal.xlsx` (pieza 3167, fechado en 2026 dentro de una carpeta de 2023). | ruta | abierta |
| I-703 | **Fecha truncada**: carpeta `0231030_Photos` (probablemente 20231030). | ruta | explicable |

## 4- Tetones · 3288

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-101 | **¿16 o 20 cavidades?** El método dice *«Nº cavidades molde: 16+16 (de 1 a 16)»* y Foboha *«16 fach»*, pero los informes tienen 20 columnas de cavidad con valores en todas, y las diapositivas citan las cavidades 17–20. | `MM732880000.pdf` p.1; `visual inspection 21.09.2026.pdf`; `3288-00_intern.0x.xls` columnas 8–27; corrección 1.2 BASE | abierta |
| I-102 | **Fechas de los ensayos mal escritas**: la misma diapositiva habla de *«trail at 16/04/2026 … 16/05/2026»* y de *«Dimensional report 8+8: trial on 16/04/2025 … 16/05/2025»*. Los informes del 3247 son de abril-mayo de 2025, así que «2026» parece una errata. | Corrección 1.1 BASE y 1.2 TAPA | explicable |
| I-103 | **Fecha de `DR(tapa)` distinta en `intern.03`**: 22/05/2026, frente al 23/06/2026 del resto de hojas del libro (lote BBS20260623 / BBS260623). | `3288-00_intern.03.xls` cabeceras | abierta |
| I-104 | **Cabecera desplazada en `3247-00_intern.01.xls!DR(tapa)`**: *Part Name* = `BSG-296-00`, *Part nº* = `11/12/2018`, *PPAP Ref.* = `DB`. Los campos están corridos una posición, como `intern.06` del 3212. | `perfil_ppap.metadatos` | abierta |
| I-105 | **Fichero de estadística con nombre del 3288 y contenido del 3247**: `3288-00_intern.01-base_1_stadistics.xls` declara *ITP Ref.* 732470000 y *PPAP Ref.* `3247-00_int.01`. | cabecera del libro | abierta |
| I-106 | **Correspondencia de los tetones entre revisiones**. El método `MM732880000_rev00.pdf`, p.6, sí identifica **DIM. Nº 80** del conjunto BSG-296-00 nivel 2 (26/08/2026): remachado sin sobresalir y sin GAP entre pin y agujero, lupa DG0266. La versión anterior lo describe como item 8 sin número de cota. Falta reconciliarlo con todos los planos de componentes; no equiparar ese 80 con BASE rev1, nominal 14,45. | Ambos métodos y `DR(base)` | abierta |
| I-107 | **Significado de la columna 29 (comentarios) de los `DR`**: lleva un número (15, 16, 17…) en cada fila. | `3288-00_intern.01.xls!DR(tapa)` | abierta |
