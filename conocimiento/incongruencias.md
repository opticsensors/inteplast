# Incongruencias y cosas que habría que pedir o aclarar

Lo que no cuadra en los datos de `Exemples`, con su evidencia. **No son preguntas redactadas para
INTEPLAST** (eso vive en `docs/preguntas-abiertas.md`, pendiente de revisión): es el material de
partida. Cada entrada tiene su registro en [hallazgos.jsonl](hallazgos.jsonl) con el mismo id.

Estados: `abierta` (sin explicar), `explicable` (hay una hipótesis razonable, sin confirmar),
`resuelta` (confirmada con evidencia).

## Transversales (afectan a varias piezas)

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-001 | **Bloques de medidas repetidos entre informes PPAP sucesivos.** Ya visto en el 3212 (N117/N118 de `intern.05` = `intern.03`; `intern.09` mezcla `.01` y `.08`). En el 3288, `DR(base)` es idéntica en `intern.02/.03/.04` y coincide al 94 % con `.01`. Parece una práctica: actualizar solo lo que se vuelve a medir y heredar el resto. Un lector no puede tratar cada informe como medición completa. | 3212: [historial-molde §8](0-bolt-eye/3212/historial-molde.md); 3288: `perfil_ppap` y comparación celda a celda | abierta |
| I-002 | **Valor `0` dentro de celdas de medida** con nominal distinto de 0 (3–4 por informe en `DR(tapa)` del 3288). Probablemente medida no realizada o pieza ausente; no es una medida real. | `perfil_ppap.ceros` | explicable |
| I-003 | 🔴 **Valores generados con `RAND()` en libros de medición.** 648.806 celdas en 191 libros de 9 piezas tienen fórmulas aleatorias (`RAND`, `RANDBETWEEN` —también con su nombre en castellano, `ALEATORIO.ENTRE`—, `NORM.INV(RAND(),…)`): su valor no es una medición. Tres casos: **(a)** el libro «Cpk generator» (detalle abajo), que produce los SPC `#P#` de 3167, 3168 y 3237; **(b)** informes PPAP con las muestras 2–5 calculadas a partir de la muestra 1; **(c)** columnas auxiliares en un R&R (3168) y 10 celdas rotas (`#REF!`) en `DR_100%` del 3167. No consta para qué se usaron ni qué se entregó al cliente. | tabla `celda_aleatoria` (`formulas_aleatorias.py`); detalle abajo | abierta |

### I-003 en detalle

Comprobado el 2026-10-21 con las fórmulas guardadas en los ficheros (openpyxl para xlsx/xlsm, Excel por
COM para xls) y la macro VBA extraída con `olevba`. Se describe qué hace cada libro, no por qué.

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
- **Los SPC `#P#` salen de ahí**: todas las secuencias del fichero (todas sus líneas, valor a valor)
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
dentro de J ± W (4.400 de 4.400) y su desviación respecto a J se reparte de forma plana entre 0 y W
(29/24/23/24 % por cuartos en el 3237): es la forma que deja el generador; una medida real se concentraría
cerca de J. En los 3174/3218 no hay una señal así de clara en las hojas principales.

**(c) Otros.** `3168-R&R.xlsx`: columnas auxiliares `ROUND(min + (max−min)·RAND())` junto a la tabla del
estudio R&R. 3167 `Int_03`…`Int_22`: 10 celdas `=ROUND(#REF!+$O$16*RAND(),$O$14)` en `DR_100%`, rotas (en `DR_100%` o `DR_100%_old` de 18 libros).

**Para la app**: estas celdas no se pueden ingerir como medición. Antes de leer un libro, consultar
`celda_aleatoria`; los `#P#` SPC y los Cmk/Cpk derivados no valen como evidencia de capacidad.

## 0- Bolt Eye

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-201 | **Arrastre de Excel en la identificación de material** del 3197: la cota 200 (visual) vale `PPS-GF40`, `PPS-GF41` … `PPS-GF47` en CAV.1–8. Debería ser el mismo material en todas. | `3197 Pot/5- Retoques de molde/3197-00_intern.02_MOLD_CORRECTION.xls!DR_8cav.` fila 34 | explicable |
| I-202 | **Plan de corrección «4» del 3197 sin PPTX**: existe `3197-00_intern.09_correction04.xls` (columna `Correction`), pero solo hay PPTX de los planes 1–3. | `3197 Pot/5- Retoques de molde/` | abierta |
| I-203 | **Hoja copiada durante dos años en el 3051**: `DR(4CAV_CMM) (2)`, fechada el 15/01/2021 (91 cotas, 82 NOK, 219 ceros), aparece igual en `intern.08`, `.09`, `.10` y `.11` (este último de 02/02/2023). | `perfil_ppap`; `3051 Pump Housing/4- Metrologia/3051-00_intern.08..11.xls` | abierta |
| I-204 | **Las dos variantes de la corrección 2 del 3212 no son equivalentes**: `rev1.pptx` lleva 11 marcadores `OK` y `rev1_.pptx` 15. El prototipo y la app usan `rev1`. | `perfil_correccion` | abierta |
| I-205 | **Plano del 3051 sin aprobar**: el único plano se llama `…0140S00275-DRW_pendent acceptació.pdf`. | `3051 Pump Housing/1-2D y 3D Pieza/` | abierta |

## 1- Clips en Piezas

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-301 | **Plano equivocado en 3186 y 3218**: el PDF del 3218 es copia byte a byte del plano del 3174 (`6494730` rev 004, SHA `31219eb5e961`); el del 3186 es `6494730` rev 002. Sus STEP son `6541691` y `6546952` y sus números de pieza 654169100A y 654695200B. Falta el plano propio de cada uno. | `Tipo A/3186/1- 2D y 3D pieza/20230123_6494730_002.pdf`; `Tipo A/3218/1- 2D y 3D pieza/20250219_6494730_004.pdf` | abierta |
| I-302 | **Plan de otra pieza en la carpeta del 3218**: `3218/5- Retoques molde/20240119_1st loop of correction/20230314-Mold correction_1_P3174.pptx` (39 diapositivas). También `3186/…/20230621_2nd loop…/20230421-Mold correction_1_P3186.pptx` (plan 1 en la carpeta del loop 2) y `2023915-Mold correction_3` en la del loop 4. | `perfil_correccion` | abierta |
| I-303 | **Plantilla PPAP del 3247 reutilizada sin cambiar la cabecera**: `3218/…/20250518 6th correction/3217_DR_intern17.xls` y `3186/…/20250609_9th loop/DR_20.xls` tienen hojas `DR(base)`/`DR(tapa)` con *ITP Ref.* 732470000 y *PPAP Ref.* `3247-00_int.01`. Además el nombre cita la pieza **3217**, que no está en Exemples. | `perfil_ppap.metadatos` | abierta |
| I-305 | **Historia incompleta del 3218**: faltan los planes de los loops 1–5 (la carpeta del loop 1 tiene el plan del 3174); el loop 6 numera todo `1.1` y el fichero del loop 14 está numerado `13.x`. | [3218.md](1-clips/3218.md) | abierta |
| I-304 | **Fechas de informe imposibles o no fechas**: `1899-12-31` (fecha cero de Excel) y `xx` en informes de 3186, 3195 y 3218; también texto `29.08.2024` en lugar de fecha. | `perfil_ppap.metadatos.report_date` | explicable |

## 2- Nervios de Soldadura

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-401 | **¿Qué versión del plan se ejecutó?** Tras los postizos de nervios hay versiones del mismo plan con magnitudes distintas: `20250723_Pla de correció_1 (after…)` +0,15/+0,3; `20250729_…` +0,05/+0,25 (3206) o +0,1/+0,25 (3205). Ninguna dice cuál es la vigente. | `3206/5- Retoques molde/20250709_correction after ribs inserts/`; `3205/…/7th loop…` | abierta |

## 5- Anclajes

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-501 | **Feature sin datos**: solo un `Readme.txt` que dice que la información *«ya fue entregada anteriormente»*, sin indicar dónde. | `5- Anclajes/Readme.txt` | abierta |

## 6- Pockets

| Id | Qué | Evidencia | Estado |
|---|---|---|---|
| I-601 | **Nombre de fichero, numeración y fecha no coinciden**: `20240214_Mold correction_1_P3167.pptx` contiene las correcciones `2.1`, `2.5`…`2.11` (plan 2, con `2.10` repetida); la versión PDF del plan 2 fecha las diapositivas el *14/02/2023* dentro de una carpeta y fichero de 2024. | `3167/5- Retoques molde/2n loop of corrections/` | abierta |
| I-602 | **Planes del 3056 sin texto**: el contenido está en imágenes; solo se lee el título de cada diapositiva. Para extraerlo haría falta OCR o lectura visual. | `3056/5- Retoques molde/20200207-Tool correction_1_P3056.pptx` | abierta |
| I-603 | **Dos versiones del PPAP Inf_04 con valores distintos.** `PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm` difiere de `PPAP-3167-00_Inf_04.xlsm` en las tolerancias (columna G en 118 filas por cavidad, F en 12: cotas 2010–2070, 2580, 2730.\*, 2740.\*; p. ej. 2580, nominal 0,66, pasa de −0,05 a −0,1 y 2730.T, 39,31, de −0,1 a −0,2) y en 8 de 11.808 celdas de medida. Los 8 valores cambiados quedaban por debajo del nuevo límite inferior y en esta versión aparecen justo por encima: 2580 `cav_1` 0,55 → 0,56/0,57 (3 valores); 2730.T `cav_2` 39,086–39,092 → 39,111–39,121 (5 valores, límite 39,11). La copia de `PPAP-3167-00_4/Uploaded to IQS/` tiene los valores y tolerancias originales. Las cotas 2730/2740 son las de la concesión de la corrección 2.3 (*«The customer can accepted the deviation for the pocket 1 and 13…»*, H-602), que explicaría las tolerancias; el cambio de valores no tiene explicación en los datos. | `3167/4- Metrologia/Customer/PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm` `cav_1!J483:N483`, `cav_2!J558:N558`, columna G | abierta |

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
| I-106 | **Qué cotas son «tetones»**. Ninguna corrección trata de los tetones: son rebabas y tamaño general. El único control explícito es visual (*«los tetones soldados no sobresalen»*, item 8 del método). Falta saber qué números de cota del plano corresponden al feature. | `MM732880000.pdf` p.3; las tres correcciones | abierta |
| I-107 | **Significado de la columna 29 (comentarios) de los `DR`**: lleva un número (15, 16, 17…) en cada fila. | `3288-00_intern.01.xls!DR(tapa)` | abierta |
