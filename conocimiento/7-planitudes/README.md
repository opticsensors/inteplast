# 7- Planitudes

> `Exemples/7- Planitudes`. 324 ficheros, 0,7 GB. Leído el 2026-10-21. Rutas relativas a esa carpeta.

| Pieza | Contenido | |
|---|---|---|
| **3168** | END LAMINATION, plano `0310 S00 337`, informes con 8–16 columnas de cavidad; 33 libros PPAP perfilados (02/2023 → 04/2026) | ficha abajo |
| 3205, 3206 | Solo `Readme.txt` → `2- Nervios de Soldadura` | [nervios](../2-nervios-soldadura/README.md) |

## 3168 — End lamination

Aislamiento de las láminas del estátor de un motor eléctrico (cliente Bosch). La planitud es una
exigencia funcional del montaje sobre el paquete de chapas.

### Correcciones

| Carpeta | Contenido |
|---|---|
| `20230227-FOT VdB/20230227-Mold correction_1_P3168.pptx` | Plan 1 (*First Off Tool*). 1.4: *«Flatness of 0,6 CZ and 0,4 … To polish all the injection side»*; 1.6: *«Do not corrected for these loop of corrections. Wait…»* |
| `20230417_1loop corrections/` | Plan 2 y comparación de informes (`3168-00_intern.02_comparation…`) |
| `20230823_Modification/` | **Análisis de un NOK en el montaje de Bosch** (`3168_End lamination NOK.pptx` y versión `_BOSCH`): *problematic situation → root cause (colisión en el frente del diente con el paquete del estátor) → analyse → actions*. También contiene propuestas de modificación fechadas en **2026**, un XLSX cuyo nombre cita 3167 (I-702) y `Parts report_23082023.pptx`, que identifica **ITP-3206** en su diapositiva 1 |
| `0231030_Photos/` | Fotos de rebabas por lote y fuerza de cierre (`Batch number 315147/Força tanca 2700KN/Rebaves/`) y `Comparacio pesos i dist rebaves.xlsx` (peso de pieza frente a rebaba) |
| `20270728_ModificacioLamelasGPF/` | Correo `RE_ Pressupost Motlle Nº 3168.msg` (presupuesto de modificación de láminas) |

- 🔑 **Dos versiones del mismo análisis**: la interna y la enviada a Bosch difieren en la redacción (la
  interna: *«For dimension point of view, we don't see major difference. To be check with CT Scan»*; la de
  Bosch abrevia esa frase y cambia *«Customer says»* por *«Bosch»* ante el mismo comentario sobre la esquina
  rugosa, ya presente en ambas). Al extraer lecciones, distinguir el documento interno del de cliente.
- De las 49 diapositivas, **13** pertenecen a los dos planes numerados del 3168; otras **3** son la plantilla
  `YYYYMMDD-Mold correction_1_PXXXX.pptx` (incluye ejemplos P3033), **7** pertenecen al informe rotulado
  ITP-3206 y **26** a análisis/propuestas del 3168. No atribuir las plantillas ni el informe 3206 al historial de 3168.
- Las propuestas `3168_End lamination_Tool modification proposal.pptx` (08/05/2026) y `_v2.pptx`
  (rev.16/06/2026), diapositivas 5–6, cambian el retroceso propuesto de todas las láminas de **0,035 a 0,30 mm**.
  Ambas proponen **96 postizos nuevos, 12 por cavidad** en inyección, y electroerosión en expulsión.
  Su fecha y revisión prevalecen sobre el nombre de la carpeta de 2023; son propuestas, sin ejecución probada aquí.
- Parámetro de proceso como variable del ensayo: la fuerza de cierre (2700 kN) aparece en la ruta de las fotos.

### Metrología y método

- 33 libros PPAP; algunos `.xlsm`; 73 `.txt` en formato `#P#` (ver [3- Paredes muy Delgadas](../3-paredes-delgadas/README.md)).
- **Extensión engañosa**: `4- Metrologia/Customer/3168-00_intern.13_6injecton points.xls` es en realidad
  un **PDF 1.7 de dos páginas** con ocho columnas CAV, no un libro editable (I-004). Identificar el formato
  por su firma antes de leerlo como Excel.
- 🔴 Los 40 SPC de `PPAP_3168-00_Inf.01/SPC/` (50 valores por cavidad): 39 coinciden valor a valor con las
  hojas `N<cota>_Cav_n` de `3168_spc *.xlsx`, que tienen la forma de salida del «Cpk generator» pero sin la
  hoja `INTRO`; no se puede ver si son medidas o generados (I-003). `3168-R&R.xlsx` tiene columnas auxiliares
  con `RAND()` junto al estudio R&R.
- Método: programa CMM (`CMMprogramm 3 131 171 80B.CAB`, `._PI`), útiles pasa/no pasa en CATIA
  (`6- Método de medición/3168 JIGs G-NG/G dim6.56-6.88.CATPart`).
- Moldflow: `README.txt` sin estudio. STL de pieza real (450 MB). Molde: 2 STEP.

## Incongruencias

[I-701 a I-703](../incongruencias.md).
