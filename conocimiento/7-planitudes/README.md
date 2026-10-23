# 7- Planitudes

> `Exemples/7- Planitudes`. 324 ficheros, 0,7 GB. Leído el 2026-10-21. Rutas relativas a esa carpeta.

| Pieza | Contenido | |
|---|---|---|
| **3168** | END LAMINATION, plano `0310 S00 337`, 8–16 cavidades; 33 informes PPAP (02/2023 → 04/2026) | ficha abajo |
| 3205, 3206 | Solo `Readme.txt` → `2- Nervios de Soldadura` | [nervios](../2-nervios-soldadura/README.md) |

## 3168 — End lamination

Aislamiento de las láminas del estátor de un motor eléctrico (cliente Bosch). La planitud es una
exigencia funcional del montaje sobre el paquete de chapas.

### Correcciones

| Carpeta | Contenido |
|---|---|
| `20230227-FOT VdB/20230227-Mold correction_1_P3168.pptx` | Plan 1 (*First Off Tool*). 1.4: *«Flatness of 0,6 CZ and 0,4 … To polish all the injection side»*; 1.6: *«Do not corrected for these loop of corrections. Wait…»* |
| `20230417_1loop corrections/` | Plan 2 y comparación de informes (`3168-00_intern.02_comparation…`) |
| `20230823_Modification/` | **Análisis de un NOK en el montaje de Bosch** (`3168_End lamination NOK.pptx` y versión `_BOSCH`): *problematic situation → root cause (colisión en el frente del diente con el paquete del estátor) → analyse → actions*, propuesta de modificación del molde (`…Tool modification pr…`, `modification proposal.xlsx`) y `Parts report_23082023.pptx` |
| `0231030_Photos/` | Fotos de rebabas por lote y fuerza de cierre (`Batch number 315147/Força tanca 2700KN/Rebaves/`) y `Comparacio pesos i dist rebaves.xlsx` (peso de pieza frente a rebaba) |
| `20270728_ModificacioLamelasGPF/` | Correo `RE_ Pressupost Motlle Nº 3168.msg` (presupuesto de modificación de láminas) |

- 🔑 **Dos versiones del mismo análisis**: la interna y la enviada a Bosch difieren en la redacción (la
  interna: *«For dimension point of view, we don't see major difference. To be check with CT Scan»*; la de
  Bosch añade *«Bosch: The corner is rough…»*). Al extraer lecciones, distinguir el documento interno del
  de cliente.
- Solo 16 de las 49 diapositivas siguen la plantilla `Tool correction n.m`; el resto son presentaciones de
  análisis (formato 8D informal) sin numeración de acción.
- Parámetro de proceso como variable del ensayo: la fuerza de cierre (2700 kN) aparece en la ruta de las fotos.

### Metrología y método

- 33 libros PPAP; algunos `.xlsm`; 73 `.txt` en formato `#P#` (ver [3- Paredes muy Delgadas](../3-paredes-delgadas/README.md)).
- 🔴 Los 40 SPC de `PPAP_3168-00_Inf.01/SPC/` (50 valores por cavidad): 39 coinciden valor a valor con las
  hojas `N<cota>_Cav_n` de `3168_spc *.xlsx`, que tienen la forma de salida del «Cpk generator» pero sin la
  hoja `INTRO`; no se puede ver si son medidas o generados (I-003). `3168-R&R.xlsx` tiene columnas auxiliares
  con `RAND()` junto al estudio R&R.
- Método: programa CMM (`CMMprogramm 3 131 171 80B.CAB`, `._PI`), útiles pasa/no pasa en CATIA
  (`6- Método de medición/3168 JIGs G-NG/G dim6.56-6.88.CATPart`).
- Moldflow: `README.txt` sin estudio. STL de pieza real (450 MB). Molde: 2 STEP.

## Incongruencias

[I-701 a I-703](../incongruencias.md).
