# 6- Pockets

> `Exemples/6- Pockets`. 1.074 ficheros, 5,7 GB. Leído el 2026-10-21. Rutas relativas a esa carpeta.
> También es el origen de `4- Tetones/3167` (allí solo hay un `Readme.txt` que remite aquí).

## Piezas

| Pieza | Qué es (cabecera PPAP) | Plano | Columnas de cavidad en informes | Correcciones |
|---|---|---|---|---|
| **3056** | INSULATING MASK E-SIDE | `0 131 S00 135` | 4–6 | 1 plan (02/2020) + anexos de medida de pockets (02/2020 y 03/2020) |
| **3167** | IPB1.1 CARRYING PLATE | `0130S000338` | 4–8 (otras hojas 10–36) | 3 loops con varias versiones (07/2023 → 06/2024) |
| **3202** | INSULATOR, MOTOR, WATER PUMP | `885253-11250` (rev. G) | 4–9 | 1 plan con comentarios del matricero (06/2023) |

## Qué es el «pocket»

Alojamientos o cajeados de la pieza, numerados (*pocket 1 … 13*), con paredes y fondos de espesor
controlado. Ejemplos:

- 3056: `20200207-Tool correction_1_P3056_info extra pockets.pptx` compara, pocket a pocket, una rejilla de
  espesores medidos en pieza (filas a–f × columnas 1–4, ~0,83–1,03 mm) con los teóricos del diseño del
  molde, y la de marzo repite la tabla *«after correction»* con pares antes–después.
- 3167: las correcciones citan pockets concretos (*«POCKET 2 to 10»*, *«Only touch the pockets from 2-10»*,
  *«Touch only the pocket 13»*) y el PPAP del cliente etiqueta cotas como `Pocket 6` (cota 2730, 39,31 +0,2/−0,1).
- 🔑 **Posibilidad de aceptación**, no concesión formal acreditada: *«The customer can accepted the deviation
  for the pocket 1 and 13 but need to correct the…»* (3167, `20240214_Mold correction_2_P3167.pptx`,
  diapositiva 4, acción 2.3). El plan recoge esa posibilidad; no basta para dar por aprobadas cotas NOK.

## Formatos

- **PPAP del cliente en `.xlsm`** (`4- Metrologia/Customer/PPAP-3167-00_2/PPAP-3167-00_2.xlsm`): una hoja por
  cavidad (`cav_1`…), columnas `B` = id de característica con subpuntos (`2730`, `2730.1`…), `E` nominal,
  `F`/`G` tolerancias (con error de coma flotante: `0.199999999999996`), `H` unidad, `I` equipo (`3D CMM`),
  `J` valor, `P` comentario (`Pocket 6`). Formato distinto al PPAP interno de INTEPLAST.
- **Export `#P#`** (ver [3- Paredes muy Delgadas](../3-paredes-delgadas/README.md)): 356 `.txt` y 4 `.csv` en el
  3167, con tabulador (`PPAP 3167-00_int02.1/Cav_3.txt`) o punto y coma
  (`Estudis Estadístics/3167-00_SPC_N1220.10_Cav_1.txt`).
  Los cuatro CSV `PPAP 3167-00_int02.1/Cav_1..4.csv` usan ids como `500`, `500.1` y `520`, sin prefijo `1-`.
  No interpretar automáticamente el tercer campo como número de medidas: en esos CSV puede ser `3`
  aunque sigan solo dos valores. Las columnas repetidas de cavidad tampoco fijan el número físico del molde.
- 🔴 **Los 328 SPC de `PPAP-3167-00_4/Estudis Estadístics/` no son mediciones**: cada uno coincide valor a valor
  con la salida de uno de los 82 `3167_Cpk generator_SPC_N*.xlsm` de la misma carpeta, que generan 50 piezas
  por cavidad con `NORM.INV(RAND(),…)` a partir de un valor real (I-003).
- 🔴 **Versiones del Inf_04**: `PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm` amplía tolerancias y
  cambia 8 valores que quedaban fuera del nuevo límite; la de `Uploaded to IQS/` conserva los originales (I-603).
  Conservar ambas con su procedencia; el nombre `Uploaded to IQS/` identifica la copia archivada como subida,
  pero no demuestra que las desviaciones de la otra copia fueran aprobadas por el cliente.
- 3202 tiene planos con globos (`6- Método de medición/Ballooned DRW/…`, `.icp`/`.prf`, 202–232 globos) y
  un `.mfr` de 380 MB; 3056 y 3167 solo un `README.txt` en Moldflow.
- Moldes muy pesados: `3- Molde` del 3056 suma 1,7 GB (129 ficheros, incluye electrodos `Electrode/*.stp`).
- Planes de corrección: 3167 y 3202 con la plantilla `Tool correction n.m (DIM. Nr. …)`, varias cotas por
  diapositiva y la cota con subpuntos (`1320.2`, `1320.4`…). **3056 lleva el contenido en imágenes**: el texto
  de cada diapositiva es solo el título (*«Tool correction nº1 – P3056 … 1/3»*).

## Incongruencias

[I-601 a I-603](../incongruencias.md) y la transversal I-003 (valores generados con `RAND()`).
