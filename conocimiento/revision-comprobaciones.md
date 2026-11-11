# Destino de las comprobaciones de `revision.py` (11/11/2026)

La pestaña **Revisión** sale del [visor de `conocimiento/`](../prototypes/data-explorer/conocimiento/README.md). Era el control
de calidad de nuestra extracción, no un resultado para enseñar a INTEPLAST. Antes de retirarla se ha decidido dónde queda
cada una de sus 27 comprobaciones, más los casos de referencia y las notas de estructura y formato que enseñaba al final.
`revision.py` sigue funcionando desde la consola.

**Punto de partida:** `revision.py` ejecutado el 11/11/2026 sobre la biblioteca del 10/11/2026 (08:51). Da los mismos recuentos
que el `revision.json` del 09/11, salvo P9, que baja de 19 a 0 por la corrección de `globos_icp.py` del 09/11/2026.

**Después de L1** (11/11/2026, [detalle](#l1-lector-de-la-cabecera-ppap)): con `perfil_ppap`, la identidad y la cadena
regenerados, M12 baja de 29 a 27 y M6 sube de 28 a 30. Los demás recuentos no cambian. La columna «Casos» ya los recoge.

## Cómo se consulta ahora

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
& $py "prototypes\data-explorer\conocimiento\revision.py"
```

Imprime el recuento de cada comprobación y escribe `prototypes/data-explorer/out/conocimiento/revision.json`, con todos los
casos, y `revision.md`, con los 25 primeros de cada una. Para saber si un cambio de lector ha empeorado algo, se comparan
esos recuentos con la columna «Casos» de abajo. Si cambia el recuento de una comprobación, hay que revisar su destino.

## Destinos

- **Junto al dato:** el visor ya lo enseña donde se consulta: la gráfica, el panel de correcciones o la ficha de pieza.
- **Errores:** una incidencia `I-` de [incongruencias.md](incongruencias.md) y `hallazgos.jsonl`, visible en la pestaña Errores.
- **Interno:** regla de regresión o caso esperado. Solo sale en `revision.py`.
- **Pendiente:** falta evidencia o una decisión. Se sigue en la [lista de pendientes](#pendientes) de este fichero; los del
  visor, también en su [README](../prototypes/data-explorer/conocimiento/README.md#pendiente-09112026).

Una comprobación puede tener varios destinos.

## Tabla

| Id | Comprobación | Casos (11/11) | Incidencia | Destino | Motivo y evidencia |
|---|---|---|---|---|---|
| P1 | Documentos sin pieza | 1 de 4.530 | I-501 | Errores · Interno | `5- Anclajes/Readme.txt`: el feature no trae piezas. Esperado |
| P2 | Piezas en varios features | 4 de 21 | — | Interno | 3167 y 3214 en Tetones, 3205 y 3206 en Planitudes: en el segundo feature solo hay un `Readme.txt`. Esperado |
| P3 | Nombre de fichero que cita otra pieza | 12 de 4.530 | I-302, I-702 | Errores · Interno · Pendiente P-1 | [Detalle](#p3) |
| P4–P6 | Pieza de `medida_cmm`, `perfil_ppap` y `perfil_correccion` frente a su carpeta | 0 | — | Interno | Regresión |
| P7 | Cajetín PPAP que cita otra pieza | 193 de 1.364 | I-310, I-303, I-104, I-105, I-108 | Errores | [Detalle](#p7). Nada nuevo |
| P8 | Cadena con documentos de otra pieza | 0 de 2.062 | — | Interno | Regresión |
| P9 | `.icp` con globos sin posición o sin número | 0 de 19 | — | Interno | Eran 19 el 09/11; los resolvió la corrección de `globos_icp.py` |
| P10 | `.icp` sin plano PDF en su carpeta | 1 de 19 | — | Interno | 3288 `REV.01/…/Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.icp`: su plano está en la carpeta de una copia, y el visor lo busca ahí ([planos-globos.md](planos-globos.md)) |
| P11 | Pieza sin PDF de plano | 1 de 21 | I-301 | Errores | 3218: su único plano (`20250219_6494730_004.pdf`, documento 1031) es copia byte a byte del plano del 3174, y la biblioteca lo marca como duplicado (`duplicado_de` 582) |
| P12 | Pieza de `hallazgos.jsonl` que no está en la biblioteca | 1 de 95 | I-104 | Interno | 3247 es un libro guardado en la carpeta del 3288, no una pieza de Exemples |
| P13, P14 | Casos de referencia y auditorías de aceptación | 0 | — | Interno | Regresión |
| M1 | Informes sin muestreo en el nombre | 47 de 480 | — | Junto al dato | La ficha de pieza los lista («N ficheros con medidas DR sin intern.NN en el nombre», `app.js:674`) y el resumen de cota los cuenta aparte (`datos.py:578`). Casi todos son entregas al cliente (`PPAP-3174-00_INF04.xls`, `PPAP_3238_INF_01.xlsm`): los `INF.NN` no son muestreos (`cadena_correcciones.py`). Hay además estudios sueltos (`3218 CT-SCAN results.xlsx`, `3195` `Results.xlsx`) |
| M2 | Muestreo del nombre distinto del de la carpeta | 0 de 480 | — | Interno | Solo compara cuando el número está en el nombre y en la carpeta (`revision.py:198`), así que no garantiza la asignación. La gráfica toma el muestreo solo del nombre (`datos.py:395`) |
| M3 | Muestreo del nombre distinto del de la cabecera | 124 de 1.156 | I-001 (ampliada) | Errores · Junto al dato, en parte · Interno · Pendientes P-2, P-5 y V1 | [Detalle](#m3) |
| M4 | Muestreos con varias versiones del informe | 82 de 324 | I-006, I-007, I-603 | Junto al dato · Errores | La gráfica elige una copia y avisa «Otra copia (…) da …» si otra trae valores distintos (`evolucion.py:186`); la cadena conserva las copias como alternativas |
| M5 | Huecos en la numeración de muestreos | 14 de 19 | — | Interno | Un hueco no es un error: puede ser un muestreo no entregado o no medido por DR |
| M6 | Fechas muy dispersas dentro de un muestreo | 30 de 325 | I-203 (los 2 nuevos) | Junto al dato, en parte · Pendiente V2 | La tabla «Muestreos» de la ficha de pieza da todas las fechas de cada muestreo, y la cadena avisa «copias de intern.NN con fechas distintas». Desde V3, el detalle del punto da la fecha de su hoja, pero no avisa de las otras. Eran 28: con L1, el 3051 `intern.09` y `.10` ya tienen fecha (16/03/2021) y difieren de su hoja `DR(4CAV_CMM) (2)`, la copiada del 15/01/2021 (I-203) |
| M7 | Muestreo con fecha anterior al previo | 4 de 325 | — | Interno · Pendiente P-3 | [Detalle](#m7) |
| M8, M9 | Cadena: muestreo del informe enlazado; validación posterior al origen | 0 de 2.062 | — | Interno | Regresión |
| M10 | Cadena: fechas incoherentes con la corrección | 4 grupos, 128 filas de 2.062 | I-302, I-306, I-402 | Junto al dato · Errores · Pendiente P-6 | [Detalle](#m10). Nada nuevo para el visor; queda un contraste incompleto |
| M11 | `medida_cmm`: muestreo distinto del nombre o de la carpeta | 0 de 75 | — | Interno | Regresión |
| M12 | Fecha de informe no válida | 27 de 1.364 | I-304 (ampliada) | Errores · Junto al dato | [Detalle](#m12). Eran 29; los 2 del 3051 eran del lector (L1, corregido) |
| M13 | Misma cota con varias nominales en una pieza | 565 de 4.882 | I-008 y otras | Junto al dato, en parte · Errores · Pendiente P-4 | [Detalle](#m13) |
| — | Notas de estructura y formato | 19 | — | Interno | Registros `estructura` y `formato` de `hallazgos.jsonl` (`H-…`). Siguen ahí y en las fichas, y se consultan con `rag.py`. No son errores |
| — | Casos de referencia de los lectores | 53 | — | Interno | `casos-referencia.jsonl`. Los comprueban P13 y `verificar_aceptacion.py` |

## Detalle

### P3

| Casos | Fichero | Destino |
|---|---|---|
| 1 | 3218 `5- Retoques molde/20240119_1st loop of correction/20230314-Mold correction_1_P3174.pptx` | I-302 |
| 1 | 3168 `5- Retoques molde/20230823_Modification/20260612_3167_modification proposal.xlsx` | I-702 |
| 7 | `6- Método de medición/…/Jigs`: `3206.CATPart` en el 3205, y `3205-C` y `3205-D` (CATPart, STEP y PDF) en el 3206 | Interno: 3205 y 3206 son la misma familia y comparten útiles de medida ([Nervios de soldadura](2-nervios-soldadura/README.md)) |
| 1 | 3309 `7- Pieza real STL/3218-00 316919 C1.stl` | Pregunta ya abierta en la [ficha del 3309](1-clips/3309.md) |
| 1 | 3238 `6- Método de medición/3238-CMM 1c/3237_3130589019.CATPart` | Pendiente P-1 |
| 1 | 3205 `5- Retoques molde/6th loop of correction (possible-rib inserts)/Archiv/28012025/POSSIBLES POSTISSOS GASOS EXP 4 CAV 3206 24-1-25.step` | Pendiente P-1 |

### P7

Ocho casos citan el 3247 (2 + 1 + 5) y uno el 3186.

| Casos | Patrón | Destino |
|---|---|---|
| 184 | 3218 → 3281 | I-310 |
| 2 | 3218 → 3247: `20250518 6th correction/3217_DR_intern17.xls` y su `Copia de …` (`DR(base)`) | I-303 |
| 1 | 3206 → 3247: `20250709_correction after ribs inserts/DR_17.xls` (`DR(base)`) | I-303 |
| 5 | 3288 → 3247: en `5- Retoques molde/20260429_1 loop of correction/`, `3247-00_intern.01.xls` (`DR(base)`), `3247-00_intern.02.xls` (`DR(base)` y `DR(tapa)`) y `3288-00_intern.01-base_1_stadistics.xls` (`DR(base)` y `DR(tapa)`) | Libros del 3247 guardados en la carpeta del 3288: I-104, I-105 (el de estadística) e I-108 (identidad heredada del 3247). [identidad-piezas.md](identidad-piezas.md) marca sus hojas como «heredada» |
| 1 | 3218 → 3186: `3218-00_intern.08.xls!315596` (`ppap_ref` `3186-00_int.17`, ITP 731860000) | [identidad-piezas.md](identidad-piezas.md) la marca como «heredada». La hoja no tiene medidas en `medida_dr`, así que no llega a ninguna gráfica |

### M3

Hojas cuyo `intern.NN` del nombre no coincide con el de `ppap_ref` en la cabecera. La gráfica sitúa el punto por el nombre
del fichero, no por la cabecera. La pregunta es si la hoja también trae las medidas del muestreo que cita.

- **Biblioteca.** Se compararon los valores de cada hoja, por cota, cavidad y valor, con los del muestreo que cita la
  cabecera (misma pieza y serie): 47 hojas comparten al menos el 90 %, 35 entre el 30 y el 90 %, 35 menos del 30 %, y 7 no
  tienen medidas leídas. Las 47 se reparten así: 3218 18, 3174 15, 3205 7, 3238 3, 3186 2, 3168 1 y 3195 1.
- **Control.** La misma comparación contra el muestreo siguiente, que no puede ser el origen, también da al menos el 90 %
  en 23 de 112 hojas. El bloque se repite en varios muestreos seguidos (3218: `intern.01` = `.02` = `.03`). La coincidencia
  demuestra que hay repetición, pero no qué muestreo es el origen.
- **Originales** (Excel por COM, 11/11/2026):
  - `3218-00_intern.02.xls!DR_100%` repite `intern.01` en las 3.821 celdas numéricas de las filas 13–400. La fecha es
    otra: 20/02/2024 frente a 18/01/2024.
  - `3174-00_intern.09.xls!DR_100%` repite `intern.08` en 3.060 de 3.116 celdas, comparadas por el rótulo de la fila.
    Posición a posición solo coinciden 650 de 3.203, porque `intern.09` tiene filas desplazadas. La fecha es la misma,
    23/11/2023.
  - Los ficheros tienen SHA-256 distintos: son libros diferentes con el bloque copiado.
- **En el visor.** La gráfica avisa por cota con «Mismos valores que intern.NN. No sabemos si se volvió a medir.» cuando
  todos los valores presentes repiten un muestreo anterior de la serie (`evolucion.py:220`). Comprobado en la cota 101 del
  3218, `intern.02`. No avisa si solo se repiten algunas cavidades de la cota (pendiente V1).
- **Destino**, por grupo:

  | Grupo | Hojas | Por pieza | Destino |
  |---|---|---|---|
  | Al menos el 90 % | 47 | 3218 18, 3174 15, 3205 7, 3238 3, 3186 2, 3168 1, 3195 1 | Errores: I-001 ampliada con 3218 y 3174, contrastados en el original. Las demás piezas, pendiente P-2 |
  | Del 30 al 90 % | 35 | 3214 12, 3218 8, 3051 3, 3233 3, 3186 2, 3237 2, 3174 1, 3205 1, 3206 1, 3212 1, 3238 1 | Pendiente P-5: probable repetición parcial, sin contrastar. Las tres del 3051 son `DR(4CAV_CMM) (2)`, la hoja copiada de I-203. Las 12 del 3214 solo tienen 8 medidas cada una, así que su porcentaje dice poco |
  | Menos del 30 % | 35 | 3195 6, 3174 5, 3205 3, 3218 4, 3233 4, 3051 3, 3186 2, 3202 2, 3237 2, 3288 2, 3206 1, 3238 1 | Interno, sin conclusión. No aparece el bloque del muestreo citado (la coincidencia más alta es del 13,8 %), pero eso no descarta que se repitan algunas cotas: no se ha buscado. La gráfica sitúa el punto por el nombre, y solo avisa si una cota repite entera un muestreo anterior |
  | Sin medidas leídas | 7 | 3205 6, 3218 1 | Interno: no hay valores que comparar y la hoja no llega a la gráfica |

### M7

| Muestreo | Fechas | Destino |
|---|---|---|
| 3195 `int_15` frente a `int_13` | 16/04/2025 y 05/06/2025 | Documentado en la [ficha del 3195](1-clips/3195.md): ordenar por número |
| 3212 `intern.08` frente a `intern.05` | 20/01/2024 y 01/05/2024 | Documentado: el año del `.08` está mal ([historial del molde](0-bolt-eye/3212/historial-molde.md)) |
| 3167 `Int_12_Comp.xls` frente a `Int_11.xls` | 26/06/2025 y 30/07/2025 | Pendiente P-3, sin contrastar |
| 3186 `intern.17` frente a `intern.16` | 04/09/2024 y 17/09/2024 | Pendiente P-3, sin contrastar |

La gráfica ordena por número de muestreo. El detalle del punto enseña la fecha de la cabecera tal como está.

### M10

Son 4 grupos, uno por pieza, con 128 filas de `cadena_correccion` en total. Hay 4 PPTX de corrección y 6 informes de origen.
Se han contrastado en el original 5 de los 6 informes de origen, y en los 5 la fecha sale de `=INTRO!C55`. El sexto,
`3195-00_Int_02.xlsm`, queda sin contrastar: no se encontró la etiqueta en `A1:Z15` de sus hojas `DR` (pendiente P-6).
Las fechas de corrección salen del nombre del PPTX o de su diapositiva, y su explicación es la de las incidencias citadas.

| Pieza | Filas | Fecha de la corrección y de dónde sale | Origen, en el original | Explicación |
|---|---|---|---|---|
| 3186 | 55 | 21/04/2023, del nombre `20230421-Mold correction_1_P3186.pptx`, que está en la carpeta `20230621_2nd loop of correction` | `intern.02`: 20/06/2023 (`DR_100%!M8`) | Nombre de un plan anterior dentro de la carpeta de un loop posterior (I-302, última frase). La cadena ordena por la fecha de la carpeta, 21/06/2023, estimada |
| 3195 | 8 | 27/05/2020, del nombre `N2/OLD/20200527-…_rev1 (sliders).pptx` | `3195-00_intern.02.xls`: 16/10/2023 (`DR!Q8`). `3195-00_Int_02.xlsm`: sin contrastar (P-6) | Probable errata por 2024 (I-306). La carpeta no tiene fecha, así que el orden queda sin comprobar |
| 3205 | 11 | 21/03/2024, de la diapositiva del plan del 3206 que lleva `20240411-Mold correction_new sliders_loop1.pptx` | `intern.10`: 05/04/2024 en las dos copias (`DR_100%!Q8`) | El PPTX base es el plan del 3206 (I-402). La fecha del nombre, 11/04/2024, sí cuadra |
| 3218 | 54 | 14/03/2023, del nombre `20230314-Mold correction_1_P3174.pptx`, que está en `20240119_1st loop of correction` | `intern.01`: 18/01/2024 (`DR_100%!Q8`) | Nombre heredado del 3174 (I-302). La cadena ordena por la fecha de la carpeta, 19/01/2024, estimada |

**En el visor.** Las 128 filas llevan en `cadena_correccion.avisos` el aviso «fecha de la corrección no fiable: … anterior
en más de 7 días a su XLS de origen …». Lo enseñan el panel de correcciones de la gráfica (`evolucion.js:261`) y la tabla
de la cadena de la ficha de pieza (`app.js:689`).

### M12

| Pieza | Hojas | Valor | Destino |
|---|---|---|---|
| 3218 | 9 | `1899-12-31` (fecha cero de Excel) | I-304 |
| 3167 | 8 | `1899-12-31` en 7 hojas; «TM April 2025» en 1 | I-304, ampliada: `Int_03.xls!DR_100%!M8` = 00/01/1900; `Int_09.xls!DR-TM-COND._1.2%!M8` escrito a mano |
| 3174 | 4 | «29.08.2024-4.9.2024» | I-304, ampliada: rango de fechas en `intern.19.xls!DR!Q8` |
| 3186 | 2 | «xx» | I-304 |
| 3195 | 2 | `1899-12-31` | I-304 |
| 3237 | 2 | «13/02/2024 -10/04/2024» | I-304, ampliada: rango en `intern_ABO.xls!DR_4cav.!M8` |
| 3051 | 2 → 0 | «Report date:» | No era del dato. En `intern.09`, `DR(4CAV_CMM)!K8` y `O8` dicen «Report date:» y la fecha está en `P8`, 16/03/2021; el lector tomaba la segunda etiqueta como fecha. Corregido (L1): `intern.09` y `.10` dan ya 16/03/2021. En la biblioteca, las celdas de los dos libros son iguales; en el original solo se abrió `intern.09` |

**En el visor (V3, hecho el 11/11/2026).** `datos.fecha_informe` decide cómo se enseña la fecha en el detalle del punto
y en la tabla «Muestreos». Antes se recortaba a 10 caracteres («Report dat», «TM April 2», «29.08.2024» de un intervalo).

| En el informe | Se enseña |
|---|---|
| Fecha de Excel | La fecha: `2021-03-16` |
| Fecha cero | «sin fecha utilizable: fecha cero de Excel (1899-12-31), I-304» |
| Dos fechas | «intervalo «29.08.2024-4.9.2024»: no es una fecha única (I-304)», con el texto entero |
| Una fecha escrita como texto | «29.08.2024 (escrita como texto)» |
| Otro texto | «sin fecha utilizable: el informe dice «xx» (I-304)», con el texto original |
| Una etiqueta de la plantilla | «fecha no leída: el lector tomó la etiqueta «…» (fallo de lectura, no del informe)». Desde L1 no queda ningún caso |

La fecha es la de la hoja del punto, no la de la primera hoja del libro: 3167 `Int_09` tiene 26/06/2025, «TM April 2025»
y 08/07/2025 en hojas distintas (`datos.fechas_por_hoja`). Hay 6 hojas con medidas sin fecha propia, y para ellas no se
elige ninguna fecha. Si el libro tiene una sola fecha, se enseña diciendo de qué hoja sale (5 hojas: «2026-04-28, de la hoja
«DR (dry)» del mismo libro: esta no tiene fecha propia»). Si tiene varias, «sin fecha propia» (3218 `intern.33`, hoja
`3rd test 21-5-2026 deformation`: el libro tiene 3 fechas; antes se le asignaba 05/05/2026, señalado por el revisor).

### L1: lector de la cabecera PPAP

`perfil_ppap.py` guardaba como valor de un campo la primera celda no vacía que seguía a su etiqueta, aunque fuera otra
etiqueta. Corregido el 11/11/2026 (`valor_de_campo`): si la etiqueta se repite, se salta; si sigue otra etiqueta, el
campo queda vacío. Solo cuenta como etiqueta un texto acabado en «:» que coincide con un campo conocido. La relectura
de `identidad_piezas.py` usa la misma función. Hay una prueba de regresión en `test_lectores.py`, con las celdas del
3051 y del 3205, que falla con el lector anterior.

Después se regeneraron `perfil_ppap`, `identidad-piezas.md` y `cadena_correccion`, y se compararon antes y después
campo a campo y fila a fila:

- **`perfil_ppap`: cambian 118 campos de 1.364 hojas.**
  - **12 son de L1.** En el 3051 `intern.09` y `.10` (`DR(4CAV_CMM)`), fecha, lote y responsable pasan de la etiqueta al
    valor (16/03/2021, 313991). Además, 6 campos que guardaban otra etiqueta quedan vacíos: `ppap_ref` = «Nº Plano:» en
    los documentos 1729, 1730, 1897 y 2411; `part_no` y `drawing_no` en el 3206 `intern.07.xls!DR_fm`.
  - **Los otros 106 no son de L1.** La tabla guardada era anterior al cambio de `perfil_ppap.py` del 04/11/2026
    (commit `ce8cd6a`), que no se había vuelto a ejecutar. Con el código de entonces, esas hojas ya dan lo mismo que
    ahora. Son `itp_ref`, `part_no`, `drawing_no` y `ppap_ref` de 26 hojas de 13 libros del 3309 (`3309-00_INF.0N`),
    y `part_no` y `drawing_no` de `PPAP-3202-00_INF.01.xls`.
- **`identidad-piezas.md`.** La hoja `DR_fm` del 3206 pasa de «desplazada» (por la etiqueta) a «propia», y el 3206 suma
  117 hojas propias de 118. En sus columnas de cavidad, «9 (1)» pasa a «8 (1)»: la tabla enseña los 3 valores más
  frecuentes y ahora hay empate a 1.
- **`cadena_correccion`: ninguna fila cambia** (2.062). El 3051 no tiene correcciones, y las hojas del 3309 y del 3202
  no cambian de fecha.
- **`revision.py`:** M12 pasa de 29 a 27 y M6 de 28 a 30 (ver la tabla). Las demás comprobaciones no cambian.

### M13

- 565 cotas en 18 piezas: 3167 145, 3288 127, 3218 94, 3056 42, 3233 29, 3237 15, 3051 14, 3174 14, 3206 14, 3168 11,
  3214 11, 3205 10, 3186 9, 3195 9, 3212 8, 3238 8, 3197 4 y 3202 1.
- **En el visor.** La gráfica separa los elementos por nominal (`evolucion.py:268`), así que no mezcla dos nominales en una
  curva. No explica por qué cambia la nominal, ni detecta una fila asignada a otra cota.
- **Causas conocidas** en casos concretos: otra hoja, condición o elemento, y piezas distintas en un mismo libro (I-008);
  tolerancia distinta entre informes (I-206 en el 3197, I-007); código de cota equivocado (I-308 en el 3195).
- **Las 565 no se han clasificado** (pendiente P-4).

## Pendientes

| Id | Qué | De | Dónde se sigue |
|---|---|---|---|
| V1 | Decidir si la gráfica avisa cuando una cota repite solo parte de las cavidades de un muestreo anterior | M3 | Aquí y en el [README del visor](../prototypes/data-explorer/conocimiento/README.md#pendiente-09112026) |
| V2 | En el detalle del punto, avisar si su muestreo tiene copias con fechas distintas | M6 | Ídem |
| ~~V3~~ | **Hecho el 11/11/2026.** Fecha entera y clasificada: fecha, intervalo, sin fecha utilizable con el texto original, o fallo de lectura. La de la hoja del punto ([M12](#m12)) | M12 | — |
| ~~L1~~ | **Hecho el 11/11/2026.** El lector ya no toma una etiqueta como valor, con prueba de regresión, y se compararon las tablas derivadas ([L1](#l1-lector-de-la-cabecera-ppap)). M12 queda en 27 | M12 | — |
| P-1 | Dos nombres de P3 sin documentar: el `3237_3130589019.CATPart` del 3238 y el `…4 CAV 3206 24-1-25.step` del 3205. No afectan a medidas ni a gráficas | P3 | Aquí |
| P-2 | Contrastar en el original las hojas de M3 con al menos el 90 % de 3168, 3186, 3195, 3205 y 3238 antes de añadirlas a I-001 | M3 | Aquí e I-001 |
| P-3 | Contrastar las fechas de M7 del 3167 (`Int_12_Comp` frente a `Int_11`) y del 3186 (`intern.17` frente a `intern.16`) | M7 | Aquí |
| P-4 | Clasificar por causa las 565 cotas de M13 | M13 | Aquí |
| P-5 | Contrastar una muestra de las 35 hojas de M3 con entre el 30 y el 90 % de coincidencia (probable repetición parcial) y decidir si van a I-001 | M3 | Aquí |
| P-6 | Localizar la fecha de `3195-00_Int_02.xlsm`, el sexto informe de origen de M10 | M10 | Aquí |
