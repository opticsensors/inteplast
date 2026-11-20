# Carga del catálogo de Exemples · 19/11/2026

La instalación local contiene 21 piezas, 8 features y 6136 cotas por pieza, revisión y componente. Se dieron de alta 19 piezas y se conservaron las fichas 3197 y 3212. Se vincularon 92 de las 98 cotas de referencia previstas, contando cada combinación de feature, pieza y código una vez. Los vínculos guardados por revisión suman 134.

Antes de la carga se restauró la copia de la BD en un PostgreSQL temporal. La copia está en `C:/Users/eduard.almar/.codex/backups/inteplast/20261119-140441/app-before-catalog.dump`. La restauración reprodujo las dos fichas de pieza, los dos features y la migración desplegada.

Se retiró el feature de prueba «Nervios», propiedad del administrador local, con sus tres notas y su vínculo con la 3212. El borrado se hizo como operación de mantenimiento de la BD. El resto de la carga se ejecutó dentro del backend con las funciones de la API y el acceso delegado de Eduard a SharePoint. Se verificó la lectura de las ocho carpetas antes de empezar.

## Procedencia

- La app descubrió los archivos y las referencias principales, propuso los features según la carpeta y leyó las mediciones. Las listas enviadas para las 19 altas se contrastaron con las funciones del formulario web. Los cuatro enlaces entre carpetas duplicadas reutilizan sus respectivas piezas.
- Los datos de identificación, los nombres de familias y clientes, las descripciones, los vínculos documentales y las notas proceden del plan autorizado. Las cifras de cotas por pieza se refieren a las que registra la app por revisión y componente. La tabla del plan identifica los campos que quedaron en blanco.
- Bolt Eye conserva sus diez notas originales y su portada en la pieza 3212. Se añadió la lección prevista sobre el diámetro. En la 3212 se mantuvo la lectura anterior y la revisión 06. La cota N288 quedó vinculada como contexto.
- La ficha 3197 conserva el identificador y las 125 cotas previas. Tras «Actualizar datos» tiene 139 cotas. Se mantuvo su configuración de archivos.

## Resultado por pieza

«Parcial» es el estado de la lectura de la app. Puede indicar que quedan hojas de medidas por interpretar o que se detectaron documentos de correcciones cuyo contenido aún requiere configurar un lector. La columna «Entradas pendientes» cuenta las entradas de medidas marcadas así en el informe, que pueden corresponder a archivos o a hojas.

| Pieza | Features | Archivos vinculados | Plano principal | Cotas | Medidas | Lectura | Entradas pendientes |
|---|---|---|---|---|---|---|---|
| 2820 | Bolt Eye | 2 | 20160817_DRW_3130516933_0140S00050-DRW-000-02-1-EN_DE.pdf | 0 | Sin medidas detectadas | Completa | 0 |
| 3051 | Bolt Eye | 4 | — | 197 | Detectadas | Parcial | 15 |
| 3197 | Bolt Eye | 3 | 20240222_0140S00363 D 02.pdf | 139 | Detectadas | Parcial | 11 |
| 3212 | Bolt Eye | 5 | 20250523_DRW 0140S00237_07.pdf | 37 | Detectadas | Lectura anterior | — |
| 3174 | Clips en Piezas | 4 | 20250219_6494730_004.pdf | 692 | Detectadas | Parcial | 55 |
| 3186 | Clips en Piezas | 5 | — | 213 | Detectadas | Parcial | 16 |
| 3218 | Clips en Piezas | 4 | — | 233 | Detectadas | Parcial | 150 |
| 3195 | Clips en Piezas | 4 | — | 1598 | Detectadas | Parcial | 87 |
| 3226 | Clips en Piezas | 3 | 20241028_DW-UMED-2-2_REV01.PDF | 0 | Informe pendiente | Parcial | 1 |
| 3309 | Clips en Piezas | 3 | — | 25 | Detectadas | Parcial | 0 |
| 3205 | Nervios de Soldadura, Planitudes | 12 | — | 87 | Detectadas | Parcial | 22 |
| 3206 | Nervios de Soldadura, Planitudes | 11 | — | 120 | Detectadas | Parcial | 70 |
| 3214 | Nervios de Soldadura, Tetones | 4 | R-2718, R-2971_C11692_rev.B.pdf | 86 | Detectadas | Parcial | 22 |
| 3233 | Paredes muy Delgadas | 4 | — | 155 | Detectadas | Parcial | 328 |
| 3237 | Paredes muy Delgadas | 4 | — | 371 | Detectadas | Parcial | 82 |
| 3238 | Paredes muy Delgadas | 4 | — | 386 | Detectadas | Parcial | 44 |
| 3288 | Tetones | 12 | — | 117 | Detectadas | Parcial | 8 |
| 3056 | Pockets | 3 | 20240417_DRW_0131S00135_D_04.pdf | 685 | Detectadas | Parcial | 55 |
| 3167 | Pockets, Tetones | 4 | — | 493 | Detectadas | Parcial | 160 |
| 3202 | Pockets | 11 | — | 384 | Detectadas | Parcial | 21 |
| 3168 | Planitudes | 3 | — | 118 | Detectadas | Parcial | 56 |

## Resultado por feature

| Feature | Piezas | Vínculos de cota por revisión | Notas |
|---|---|---|---|
| Bolt Eye | 2820, 3051, 3197, 3212 | 8 | 11 |
| Clips en Piezas | 3174, 3186, 3195, 3218, 3226, 3309 | 41 | 6 |
| Nervios de Soldadura | 3205, 3206, 3214 | 24 | 2 |
| Paredes muy Delgadas | 3233, 3237, 3238 | 7 | 1 |
| Tetones | 3167, 3214, 3288 | 15 | 1 |
| Anclajes | — | 0 | 0 |
| Pockets | 3056, 3167, 3202 | 34 | 2 |
| Planitudes | 3168, 3205, 3206 | 5 | 2 |

Anclajes queda sin piezas. Su carpeta contiene una remisión sin identificar el proyecto al que corresponde.

## Cotas vinculadas

| Feature | Pieza | Rol | Revisiones de la app | Cotas |
|---|---|---|---|---|
| Bolt Eye | 3212 | Principal | 06 | N170, N117 |
| Bolt Eye | 3212 | Referencia | 06 | N178 |
| Bolt Eye | 3212 | Contexto | 06 | N288 |
| Bolt Eye | 3197 | Principal | 3E1009447060 | N230, N220 |
| Bolt Eye | 3051 | Principal | 01 | N880, N890 |
| Clips en Piezas | 3174 | Principal | 001, 002, .004, sin-revision | N712, N215, N216 |
| Clips en Piezas | 3174 | Contexto | 001, 002, .004, sin-revision | N511 |
| Clips en Piezas | 3186 | Principal | 2.0 | N216 |
| Clips en Piezas | 3186 | Referencia | 2.0 | N1003 |
| Clips en Piezas | 3186 | Contexto | 2.0 | N215 |
| Clips en Piezas | 3218 | Principal | 002 | N2603, N2612, N2702, N2705, N2902, N2905 |
| Clips en Piezas | 3218 | Contexto | 002 | N2601, N2904, N500, N1906, N1907, N1908, N1909, N1910, N1911, N1912, N2501 |
| Clips en Piezas | 3195 | Principal | 0130S1B006, 09 | N3120 |
| Clips en Piezas | 3309 | Principal | sin-revision | N15 |
| Clips en Piezas | 3309 | Contexto | sin-revision | N14, N16 |
| Nervios de Soldadura | 3205 | Principal | - | N17, N18, N19, N152 |
| Nervios de Soldadura | 3205 | Contexto | - | N62, N104, N154, N3 |
| Nervios de Soldadura | 3206 | Principal | A, B | N64, N20, N21, N83 |
| Nervios de Soldadura | 3206 | Contexto | A, B | N6 |
| Nervios de Soldadura | 3214 | Principal | A, G | N10, N12, N13 |
| Paredes muy Delgadas | 3237 | Principal | 03, 04 | N123 |
| Paredes muy Delgadas | 3237 | Contexto | 03, 04 | N116 |
| Paredes muy Delgadas | 3238 | Principal | 03, 04 | N148 |
| Paredes muy Delgadas | 3233 | Principal | 01 | N520 |
| Tetones | 3214 | Principal | A, G | N6 |
| Tetones | 3214 | Contexto | A, G | N3, N4, N5, N7 |
| Tetones | 3167 | Principal | 02 | N500 |
| Tetones | 3167 | Contexto | 02 | N470, N490, N520, N540 |
| Pockets | 3167 | Principal | 02 | N1220, N2120, N2260, N2730, N2740, N1240, N1320, N1290 |
| Pockets | 3167 | Contexto | 02 | N1030, N1090 |
| Pockets | 3056 | Principal | 01, 02 | N1200, N1230, N1231, N1210, N1330, N1310, N1311, N1290 |
| Pockets | 3202 | Principal | -, 0 | N76, N79.1, N79.2, N79.3 |
| Planitudes | 3168 | Principal | 01 | N230, N1330 |
| Planitudes | 3205 | Principal | - | N5 |
| Planitudes | 3206 | Principal | A, B | N9 |

En la 3167, la corrección 1.3 cita N470, N490, N520 y N540 al proponer nervios en los pines. Se vincularon como contexto del retoque. El diámetro de 1,4 de los pines se mide con la N500.

## Cotas de referencia pendientes

| Feature | Pieza | Cotas | Motivo |
|---|---|---|---|
| Nervios de Soldadura | 3205 | N21 | La lectura no registró la cota. El informe describe la rebaba en los nervios. |
| Nervios de Soldadura | 3206 | N203 | La lectura no registró la cota. Figura como nota informativa sobre el desmoldeo. |
| Paredes muy Delgadas | 3238 | N4010 | La lectura no registró la cota. El PPAP la presenta como nota sobre el desmoldeo de la pared fina. |
| Tetones | 3288 | N80 | La lectura no registró la cota. El método indica una comprobación visual del remachado con lupa. |
| Tetones | 3288 | N30 | Se leyó N30 con nominal 4,35 en la revisión 1.0. El método de los tetones especifica 3,3 para la altura de los pines indicadores. |
| Tetones | 3288 | N43 | Se leyó N43 con nominal 56,75 en la revisión 1.0. El método de los tetones especifica 2,7 para la altura del pin. |

## Vínculos comprobados solo en algunas revisiones

| Pieza | Cotas | Revisiones omitidas | Evidencia |
|---|---|---|---|
| 3205 | N17 | B | La N17 de longitud del director tiene nominal 7,2. En la revisión B solo se leyeron coordenadas y una medida radial con nominal 0. |
| 3056 | N1200, N1230, N1231, N1210, N1330, N1310, N1311, N1290 | 03, 04 | Las hojas de medición de las revisiones 01 y 02 identifican estos pockets. En 03 y 04 la numeración antigua aparece en una hoja oculta de comparación con errores de fórmula. La N1210 de la hoja de medición de 04 tiene otro nominal. |

Las candidatas del 2820 y los identificadores funcionales F1–F3 del 3309 quedan fuera del recuento anterior según el plan. El catálogo conserva los resultados de cada lectura.

## Incidencias de lectura y selección de archivos

El formulario propuso el nombre de la carpeta para las 19 altas. Se aplicaron los nombres aprobados de la tabla. El detalle de cada pieza se conserva en su informe de lectura y en los JSON de esta carga.

| Pieza | Avisos y ejemplos |
|---|---|
| 2820 | No se han encontrado documentos de correcciones. |
| 3051 | Principal pendiente (Plano). 15 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3051-00_intern.01.xls · DR(100%). Pendiente: 35 filas descartadas (identificadores no admitidos, tolerancias invertidas); filas 28, 30, 44, 45, 46, 106, 107, 113…. |
| 3197 | 14 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3197-00_intern.01.xls · DR_8cav.. Pendiente: 42 filas descartadas (identificadores no admitidos, tolerancias invertidas); filas 30, 31, 32, 33, 43, 44, 45, 46…. |
| 3174 | 45 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3174-00_Intern.32_For PPAP.xls · DR_100% after correction. Pendiente: 5 filas descartadas (identificadores no admitidos); filas 42, 43, 44, 45, 46. |
| 3186 | Principal pendiente (Plano). 22 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3186-00 MSA.xlsx. Pendiente: no se ha reconocido una tabla dimensional; requiere revisión. |
| 3218 | Principal pendiente (Plano). 66 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3218-00_intern.33 – kopie.xls · DR_100%. Pendiente: 5 filas descartadas (identificadores no admitidos); filas 64, 68, 69, 70, 71. |
| 3195 | Principal pendiente (Molde, Plano). 33 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3195-00_Int_02.xlsm · cav_1. Pendiente: 35 filas descartadas (identificadores no admitidos); filas 209, 210, 226, 272, 275, 295, 297, 305…. |
| 3226 | 6 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3226-00_intern.01.xls · DR. Pendiente: la columna de valores no rotula la cavidad y las filas no tienen número de cota; hoja sin leer. |
| 3309 | Principal pendiente (Escaneo, Plano). 12 documentos de correcciones por interpretar. |
| 3205 | Principal pendiente (Plano). 60 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3205-00_intern.02.xls · DR_competencia. Pendiente: no se reconocen las columnas de cavidad; hoja sin leer. |
| 3206 | Principal pendiente (Molde, Plano). 36 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3206-00_intern.11.xls · DR_PARAM(1). Pendiente: 4 filas descartadas (identificadores no admitidos); filas 57, 60, 63, 66. |
| 3214 | 3 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3214-00_int.02_customer.xls · DR. Pendiente: 11 filas descartadas (identificadores no admitidos); filas 36, 49, 83, 84, 85, 86, 87, 88…. |
| 3233 | Principal pendiente (Molde, Plano). 8 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3233-00_inf.06_OPL_81A.xls · 100%. Pendiente: 136 filas descartadas (identificadores no admitidos); filas 15, 18, 19, 20, 22, 23, 24, 25…. |
| 3237 | Principal pendiente (Escaneo, Plano). 24 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3237-10_intern.01 including CPK.xls · DRxSPC. Pendiente: tabla con nominales; falta clasificar su función y formato; hoja sin leer. |
| 3238 | Principal pendiente (Escaneo, Plano). 27 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3238-00_intern.03-a.xls · N94. Pendiente: tabla con nominales; falta clasificar su función y formato; hoja sin leer. |
| 3288 | Principal pendiente (CAD, Escaneo, Molde, Plano). 38 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3288-00_intern.01.xls · DR(base). Pendiente: las columnas de cavidad solo llevan un número; hoja sin leer. |
| 3056 | Principal pendiente (Molde). 5 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3056-00_intern.1_100%.xls · DR (3D). Pendiente: 28 filas descartadas (identificadores no admitidos); filas 42, 43, 48, 49, 54, 55, 60, 61…. |
| 3167 | Principal pendiente (Molde, Plano). 27 documentos de correcciones por interpretar. Ejemplo de medición pendiente en supplyon.xlsm · cav_1. Pendiente: 56 filas descartadas (identificadores no admitidos); filas 59, 68, 89, 93, 97, 133, 134, 135…. |
| 3202 | Principal pendiente (CAD, Molde, Plano). 5 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3202-00_intern.03_COSTUMER.xls · DR_100%. Pendiente: 54 filas descartadas (identificadores no admitidos); filas 270, 271, 272, 273, 274, 275, 276, 277…. |
| 3168 | Principal pendiente (Molde, Plano). 29 documentos de correcciones por interpretar. Ejemplo de medición pendiente en 3168 - Dimensional comparation 6 inj vs 12 inj.xlsx · Comparation Dimensional report. Pendiente: tabla con nominales; falta clasificar su función y formato; hoja sin leer. |

El registro detallado local está en `C:/Users/eduard.almar/.codex/scratch/inteplast-carga-20261119/results/`. Cada `p<código>.json` conserva la propuesta, los archivos enviados cuando hubo alta y el informe de la lectura que se ejecutó. `verified.json` recoge el estado comprobado de las fichas y `assignments.json` los vínculos y pendientes por cota.

Fuentes del contenido cargado. [Plan del catálogo](plan-carga-catalogo-2026-11-18.md), [cotas por feature](../conocimiento/cotas-por-feature.md), [identidad de piezas](../conocimiento/identidad-piezas.md).

### Ajuste posterior de la portada 3288

La tabla anterior conserva el resultado de la carga automática. Después, Eduard autorizó
usar uno de los dos componentes para representar la 3288. Se vincularon los STEP de base y
tapa y se escogió la base como CAD principal y portada inicial de Tetones. La ficha sigue
representando una sola pieza. En la edición de Tetones se puede escoger la tapa y guardar
esa elección solo para el feature. La 3202 conserva su selección original.
