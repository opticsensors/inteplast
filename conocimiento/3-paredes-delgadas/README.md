# 3- Paredes muy Delgadas

> `Exemples/3- Paredes muy Delgadas`. 647 ficheros, 1,7 GB. Leído el 2026-10-21. Rutas relativas a esa carpeta.
> Perfiles: `perfil_ppap` (205 hojas), `perfil_correccion` (49 diapositivas).

## Piezas

| Pieza | Qué es (cabecera PPAP) | Plano | Columnas de cavidad en informes | Correcciones |
|---|---|---|---|---|
| **3233** | Isomask A Long - BDU34 | `0196S0000K` | 32 (algunas hojas 10) | Solo plantilla genérica (3 diapositivas), sin plan propio PPTX |
| **3237** | INSULATION MASK EL. SIDE | `3 130 589 019` / `3130589019` | 4 y 8 | 5 PPTX propios, 15 diapositivas; más plantilla de 3 |
| **3238** | Insulation Mask | `3 130 589 01F` / `313058901F` | 4 y 8 | 7 PPTX propios, 25 diapositivas; más plantilla de 3 |

Máscaras aislantes de motor eléctrico (cliente Bosch por la numeración `3 130 …`). El plano aparece con y
sin espacios según el informe: normalizar antes de comparar.
Los tres `YYYYMMDD-Mold correction_1_PXXXX.pptx` incluyen ejemplos **P3033 de 26/07/2019**
(diapositivas 2–3); no son correcciones de 3233/3237/3238. El número de columnas de informe tampoco
demuestra por sí solo el número físico de cavidades del molde.

## Qué es el feature aquí

Paredes del orden de **0,25 mm** (característica `1-1` de los export SupplyOn: nominal 0,25, valores
0,225–0,272) y espesores de laminación (`Measuring_comparison_313117181A_INTEPLAST_END_LAMINATION…xlsx`,
*Thickness* 0,3 ±0,05 por CMM, en el 3233). Las correcciones van en la línea de **dar más espesor**:
*«Tool correction 1.5 Increase the thickness of the part»* (3237) y 1.7 (3238).

También hay decisiones de **no corregir acero** por discrepancias CMM/CT o por acondicionamiento:
`3238/5- Retoques molde/20240410_2nd loop of corrections/20240426-Mold correction_2_P3238.pptx`,
diapositivas 1 y 4, propone cambiar el programa CMM y señala que la cota 169 se deforma al humidificar.
Son condiciones de medida y decisiones del plan, no prueba de ejecución. La diapositiva 2 reduce la
propuesta del 22/04 de 0,14 a **0,07 mm por nervio**; conservar la versión y fecha junto a la acción.

## Formatos nuevos respecto al 3212

- 🔑 **Export de mediciones para el cliente** (`4- Metrologia/Customer/Support Int_0x/…/SupplyOn/`):
  ficheros `.txt` con líneas `#P#;<id>;<n>;<nominal>;<límite sup.>;<límite inf.>;<unidad>;<v1>;<v2>;…`.
  Las unidades pueden ser `mm` o `°`; hay ficheros SPC con `Cmk`/`Cpk` (`3237_SPC_Cav_1.txt`). Son 103 en el
  3237 y 32 en el 3233; el 3238 no tiene (sus 10 `.txt` son resultados de CMM de útiles, `6- Método de
  medición/Jigs results/3238 C1 ITP.txt` frente a `… RB.txt`). **La app no lee este formato.**
  - **Qué son (2026-10-21)**: ficheros que prepara INTEPLAST para importarlos en **eISIR** de SupplyOn
    (informe electrónico de muestras iniciales que pide Bosch). eISIR importa «protocolos de máquina» por
    cavidad, con un prefijo, y genera el informe cmk (manual eISIR 8.30, pp. 37–41). El marcador `#P#` no es
    Q-DAS y no está documentado públicamente.
  - 🔴 **Los cuatro `3237_SPC_Cav_n.txt` contienen valores generados**: coinciden valor a valor con
    `PPAP_3237_INF_02_SPC.xlsm`, cuya macro `Generate_Sheets` exporta 50 valores por cavidad calculados
    con `NORM.INV(RAND(),…)` a partir de un valor real. Para los 88 de
    `Support_V20_Inf_03/3237-20 SPC/`, el título de sus PDF apunta a `Cpk generator_IQS.xlsm`, ausente
    de Exemples; su procedencia queda por confirmar. Los PPAP de cliente `.xlsm` del 3233, 3237 y
    3238 también calculan muestras con `RAND()`. Detalle en
    [I-003](../incongruencias.md#i-003-en-detalle).
  - **Relación con las cotas**: el id es `1-<cota>[.subpunto | .Cmk | .Cpk | .T]`. En el 3237, 187 de 215 ids
    son una cota del PPAP interno con el mismo nominal; 7 difieren porque el PPAP pone texto (`Burrs`) y 21 no
    tienen cota en el PPAP (H-503).
- Informes PPAP con 32 columnas de cavidad (3233).
- MSA y comparativas de medición INTEPLAST ↔ cliente (`Measuring_comparison_…_EXTENDED.xlsx`, hoja `MSA`).
- Las correcciones existen en dos versiones: la de INTEPLAST (PPTX) y la enviada al matricero
  (`…_P3237_planitec.pdf`, `…_P3238_Planitec.pdf`). Planitec es el fabricante del molde.
- Plantilla de corrección del 3212 (`Tool correction n.m`), sin `DIM. Nr.` en algunos títulos
  (*«Tool correction 1.5 Increase the thickness of the part»*: la cota está en la imagen).
- Métodos de medida antiguos en `.doc` (Word 97-2003) en el 3233.
- Moldflow `.mfr` en las tres piezas; STL de pieza real en las tres.

## Pendiente de profundizar

- ~~Errores de lectura~~: resueltos (los `.doc` bloqueados se leen con texto aproximado; 0 errores).
- ~~Relacionar los id `1-xxx` de SupplyOn con los números de cota de los PPAP~~ hecho en el 3237 (H-503);
  falta con los planes de corrección.
