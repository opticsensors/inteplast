# Retoques de molde por pieza y muestreo

**Revisión documental del 27/11/2026.** Un `intern` identifica un informe de medición. Puede recoger piezas de otra tirada, volver a medir el mismo lote o comprobar solo algunas cotas. Para saber qué se hizo en el molde buscamos una frase del taller o de Metrología, un lote común o una referencia de plan que permita situar la actuación.

**Cómo leer el índice.** El número de la columna «Muestreo» es el informe **en el que consta el retoque o su resultado**. Solo se indica el intervalo de ejecución cuando las fuentes permiten acotarlo. Si un informe dice «después del plan 5», acredita la ronda. El detalle de una acción concreta requiere que el documento la identifique como realizada. Una previsión, una instrucción, un «OK» aislado o una variación dimensional dejan la ejecución por confirmar.

## Cobertura de los informes

Se revisaron las 21 piezas de `Exemples`. Los Excel de Metrología identificados por nombre dan 355 combinaciones de pieza, serie e `intern`. Se contaron una sola vez las copias y los soportes del mismo número. Se contrastaron con hojas `HISTORY`, cabeceras de lote, comentarios junto a las cotas, tablas de retoques y los 154 PowerPoint de las carpetas de retoques. La relación de fuentes se limita a la entrega disponible. En un historial acumulativo se leyó el encabezado «INFORME n» inmediatamente anterior a la anotación.

La tabla cubre **todos los números encontrados**. Un intervalo como «01–11» incluye ambos extremos. La tercera columna señala los números para los que hay una referencia a una actuación previa o al estado del molde. La última reúne los demás. Cuando la asociación depende del nombre de un fichero o de su carpeta, la limitación figura en el detalle. Los enlaces de pieza llevan a su ficha de ingesta. Los enlaces de las filas de detalle abren los originales en la disposición local de `Exemples`.

| Pieza | Serie | Muestreos con nota de retoque o de estado del molde | Otros muestreos revisados sin actuación atribuida |
|---|---|---|---|
| [2820](ingesta/2820.md) | — | — | Sin informes de muestreo |
| [3051](ingesta/3051.md) | 00 | 09–10 | 01–08, 11 |
| [3056](ingesta/3056.md) | 00 | 02 | 01, 03–11 |
| [3056](ingesta/3056.md) | 01 | 05 | 01–04 |
| [3167](ingesta/3167.md) | 00 | 09 | 01–08, 10–22 |
| [3168](ingesta/3168.md) | 00 | 01 | 02–15 |
| [3168](ingesta/3168.md) | 10 | — | 01–08 |
| [3174](ingesta/3174.md) | 00 | 13, 28–29, 32 | 01–12, 14–27, 30–31, 33–34 |
| [3186](ingesta/3186.md) | 00 | 07, 11 | 01–06, 08–10, 12–22 |
| [3195](ingesta/3195.md) | 00 | 11, 16–18 | 01–10, 12–15, 19–21 |
| [3197](ingesta/3197.md) | 00 | — | 01–11 |
| [3202](ingesta/3202.md) | 00 | 03 | 01–02, 04–07 |
| [3205](ingesta/3205.md) | 00 | 19, 23 | 01–18, 20–22, 24–29 |
| [3206](ingesta/3206.md) | 00 | 02–04, 17 | 01, 05–16, 18–24 |
| [3212](ingesta/3212.md) | 00 | — | 01–09 |
| [3214](ingesta/3214.md) | 00 | 07–08, 14 | 01–06, 09–13 |
| [3218](ingesta/3218.md) | 00 | 21, 32–36 | 01–20, 22–31 |
| [3226](ingesta/3226.md) | 00 | — | 01 |
| [3233](ingesta/3233.md) | 00 | — | 01–16 |
| [3237](ingesta/3237.md) | 00 | — | 01–22 |
| [3237](ingesta/3237.md) | 10 | — | 01 |
| [3237](ingesta/3237.md) | 20 | 08 | 01–07, 09–11 |
| [3238](ingesta/3238.md) | 00 | — | 01–11 |
| [3238](ingesta/3238.md) | 20 | — | 01–06 |
| [3288](ingesta/3288.md) | 00 | — | 01–04 |
| [3309](ingesta/3309.md) | 00 | 02–03 | 01, 04 |

### Disponibilidad de HISTORY y Remarks

El 27/11/2026 se comprobaron las pestañas y cabeceras de los ficheros de Metrología con número de intern en el nombre. De 467 archivos con extensión Excel, 466 eran libros y uno era un PDF con extensión `.xls`. **456 libros tienen la hoja `HISTORY` y, en todos ellos, la cabecera `Remarks` está en F6.** Los otros diez libros carecen de esa hoja. El recuento incluye copias de cliente y soportes.

Por pieza, serie e intern, **353 de 355 muestreos** tienen al menos una copia con esa columna. Las dos excepciones son los interns **14 y 16 de la 3195**, serie 00. En la plantilla habitual, la observación se escribe más abajo en la columna F, en el bloque del informe correspondiente. Por ejemplo, `HISTORY!F49` del intern.33 de la 3218 ya indica que se midió después del plan 12. [Excel del ejemplo](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.33.xls>) · [Acuerdo para proponer a INTEPLAST](../docs/estructura-de-carpetas-por-pieza.md#retoques-del-molde)

## Actuaciones y comprobaciones documentadas

### 3051 · Pasadores centrales, numeración por aclarar

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · fichero 09 | La hoja identifica piezas con pasadores centrales nuevos, lote 313991. | [3051-00_intern.09.xls](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3051%20Pump%20Housing/4-%20Metrologia/3051-00_intern.09.xls>) · HISTORY!F13 y DR(4CAV_CMM)!H12 |
| 00 · fichero 10 | Se identifica un pasador nuevo específicamente en la cavidad 3. El informe distingue el lote 313999 para esa cavidad del 313991 para las demás. | [3051-00_intern.10.xls](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3051%20Pump%20Housing/4-%20Metrologia/3051-00_intern.10.xls>) · HISTORY!F18 y DR(4CAV_CMM)!H12 |

Los cambios de pasadores y los lotes están documentados. Su asignación a un número único queda abierta. Los ficheros se llaman 09 y 10, la referencia PPAP de ambas hojas dice `int.01` y el histórico coloca las dos anotaciones bajo «INFORME 2» e «INFORME 3». [3051-00_intern.09.xls](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3051%20Pump%20Housing/4-%20Metrologia/3051-00_intern.09.xls>) · DR(4CAV_CMM)!C6 e HISTORY!A12 · [3051-00_intern.10.xls](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3051%20Pump%20Housing/4-%20Metrologia/3051-00_intern.10.xls>) · DR(4CAV_CMM)!C6 e HISTORY!A17

### 3056 · Nervios, rebabas y ajuste del molde

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 02 | La corrección 3 figura como nervios mecanizados en la fila de N280. Otra nota dice que N1230 se redujo 0,1 mm, pero está escrita en la fila de N1250. Se conserva la discrepancia sin adjudicar ese valor a una intervención en N1250. | [3056-00_intern2.xls](<../../../proyectos/11.%20inteplast/Exemples/6-%20Pockets/3056/4-%20Metrologia/Interns/V00/3056-00_intern2.xls>) · DR(100%) (RETOQQUES)!N132 y N304 |
| 01 · 05 | El informe da las rebabas por eliminadas en N60 y sus subpuntos y registra un ajuste del molde en N1560 y sus subpuntos. También indica que se midió con un útil nuevo. El texto deja abierta la contribución de cada cambio al resultado dimensional. | [3056-01_intern.5.xls](<../../../proyectos/11.%20inteplast/Exemples/6-%20Pockets/3056/4-%20Metrologia/Interns/V01/3056-01_intern.5.xls>) · DR(100%)!O54:O59 y O395:O412 |

La diapositiva 2 del resumen de *pockets* da en verde las medidas posteriores a la corrección, con pares antes/después de la versión 00. La diapositiva carece de número de informe. [20200331-Tool correction_1_P3056_info extra pockets.pptx](<../../../proyectos/11.%20inteplast/Exemples/6-%20Pockets/3056/5-%20Retoques%20molde/20200331-Tool%20correction_1_P3056_info%20extra%20pockets.pptx>) · diapositiva 2

### 3167 · Última ronda sin identificar

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 09 | La copia de cliente rotula el lote de una hoja «Last loop of correction». Permite situar esa medición tras una ronda. Quedan abiertos el número de plan, la acción y las cavidades. | [3167-00 Int_09.xls](<../../../proyectos/11.%20inteplast/Exemples/6-%20Pockets/3167/4-%20Metrologia/Customer/3167-00%20Int_09.xls>) · DR-TM-COND._1.2%!M9 |

### 3168 · Intervención durante la primera prueba

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 01, como referencia de la prueba | Durante el ensayo el molde tenía dificultades para cerrar. El plan relata que lubricaron las columnas, pudieron seguir y también tuvieron que pulirlas. El informe de correcciones del 01 acompaña a la presentación en la carpeta de la primera prueba. La narración sitúa el trabajo en esa prueba, sin precisar si ocurrió antes o después de medir una cota. | [20230227-Mold correction_1_P3168.pptx](<../../../proyectos/11.%20inteplast/Exemples/7-%20Planitudes/3168/5-%20Retoques%20molde/20230227-FOT%20VdB/20230227-Mold%20correction_1_P3168.pptx>) · diapositiva 11, acción 1.11 |

En la serie 10, el informe 03 compara piezas medidas antes y después de modificar el **útil de sujeción de la CMM**. Es un cambio del método de medida. [3168-10_intern.03.xls](<../../../proyectos/11.%20inteplast/Exemples/7-%20Planitudes/3168/4-%20Metrologia/Interns/3168-10_intern.03.xls>) · DR-CC, fila 12

### 3174 · Informes posteriores al retoque

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 13 | El histórico del informe siguiente coloca bajo «INFORME 13» el lote 315561 y las cotas medidas tras varios retoques. No detalla el trabajo realizado. | [3174-00_intern.14.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Interns/3174-00_intern.14.xls>) · HISTORY!A47 y F48 |
| 00 · 28 y 29 | Ambos se identifican como posteriores a la corrección, con el mismo lote 315928 y el mismo ajuste de proceso. El 28 recoge dos inyecciones y el 29, cinco. Las dos entradas pueden referirse a la misma actuación. | [3174-00_intern.28.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Interns/3174-00_intern.28.xls>) · HISTORY!F68:F69 · [3174-00_intern.29.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Interns/3174-00_intern.29.xls>) · HISTORY!F71:F72 |
| 00 · 32, copia de cliente | La copia para PPAP dice «After tool correction», cinco inyecciones y lote 316036. El interno del mismo número describe la medición de N806. Se mantiene la referencia a la copia que menciona el retoque. | [3174-00_Intern.32_For PPAP_26.6.2025.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Customer/3174-00_Intern.32_For%20PPAP_26.6.2025.xls>) · HISTORY!A73 y F74:F75 · [3174-00_intern.32.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Interns/3174-00_intern.32.xls>) · HISTORY!A76 y F77 |

Un motivo real por el que una medida puede cambiar se ve en el 34. En el estudio de N102, el informe compara las piezas a las 2 y a las 168 horas de producción y anota que al cabo de una semana son aproximadamente **0,03 mm menores**. [3174-00_intern.34.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3174/4-%20Metrologia/Version%2000/Interns/3174-00_intern.34.xls>) · DR CMM!A24 e HISTORY!F83

### 3186 · Lotes ensayados tras la corrección

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 07 | El informe identifica el lote 315283 como posterior a la corrección. Queda sin identificar la acción concreta. | [3186-00_intern.07.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3186/4-%20Metrologia/Interns/3186-00_intern.07.xls>) · HISTORY!F38 |
| 00 · 11 | El ensayo de fuerza del lote 315396 se declara posterior a la corrección. No consta qué se mecanizó ni si fue otra intervención distinta de la anterior. | [3186-00_intern.11.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3186/4-%20Metrologia/Interns/3186-00_intern.11.xls>) · HISTORY!F58 |

### 3195 · Del retoque de una cavidad al de todas

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 11 | El informe vincula las cotas 750 y 751 al retoque solicitado por el cliente. No especifica cuánto se modificó. | [3195-00_int_11.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3195/4-%20Metrologia/Interns/3195-00_int_11.xls>) · HISTORY!F45:F46 |
| 00 · 16 | Se había modificado **solo la cavidad 1**, según la revisión 0 del plan 5. El Excel de origen del plan es el 15. El alcance que recoge la revisión 0 comprende ajustes de la zona de la escobilla. | [3195-00_int_16.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3195/4-%20Metrologia/Interns/3195-00_int_16.xls>) · Hoja1!A2 · [Planes de la pieza](1-clips/3195.md#los-planes) |
| 00 · 17 | Se habían modificado **todas las cavidades**, según la revisión 1 del plan 5. El paso del 16 al 17 queda documentado. La revisión 1 del plan incluye las rebabas de N3050 y el ajuste de N2660. La nota confirma el alcance por cavidad y deja sin desglosar la magnitud aplicada en cada superficie. | [3195-00_int_17.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3195/4-%20Metrologia/Interns/3195-00_int_17.xls>) · Calibres!A2 e HISTORY!F64 |
| 00 · 18 | Metrología identifica las piezas fabricadas en ROLD como posteriores al plan 6. La hoja de calibres conserva la nota del plan 5 del informe anterior. La fecha anotada en el histórico (04/12/2025) y la del nombre del PowerPoint del plan 6 (05/12/2025) aconsejan dejar abierta la fecha exacta. | [3195-00_int_18.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3195/4-%20Metrologia/Interns/3195-00_int_18.xls>) · HISTORY!F69 y Calibres!A2 |

### 3202 · Primeros retoques del matricero

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 03 | Las cotas marcadas en gris se midieron en el lote que el histórico identifica como posterior a los primeros retoques del matricero, del 22/09/2023. El registro no individualiza las operaciones. | [3202-00_intern.03.xls](<../../../proyectos/11.%20inteplast/Exemples/6-%20Pockets/3202/4-%20Metrologia/Interns/3202-00_intern.03.xls>) · HISTORY!A17 y F18 |

### 3205 · Postizos de los nervios y corrección de rebabas

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 19, por la carpeta | La entrega del 19 está en la carpeta titulada «segunda [ronda] después de los nuevos postizos para los nervios». Sitúa los postizos como antecedente de la ronda. No precisa en qué intervalo se montaron. | [3205-00_intern.19.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/5-%20Retoques%20molde/8th%20loop%20of%20correction%20%282nd%20after%20new%20inserts%20for%20ribs%29/3205-00_intern.19.xls>) · carpeta «8th loop of correction (2nd after new inserts for ribs)» |
| 00 · 23 | El informe identifica el lote 316647. El histórico del 24 atribuye al **23** las comprobaciones de altura de pasadores e ICL relacionadas con la corrección de rebabas. El Excel de resultados posterior a la corrección también identifica ese lote en su hoja DR. La fecha de la entrada del histórico difiere en el año de la de emisión del 23. | [3205-00_intern.23.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/4-%20Metrologia/Interns/3205-00_intern.23.xls>) · DR!C6, Q8 y Q9 · [3205-00_intern.24.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/4-%20Metrologia/Interns/3205-00_intern.24.xls>) · HISTORY!A42:F43 · [DR_3205-00_resultats rebava prova 20260312 after correction.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/5-%20Retoques%20molde/10th%20loop%20of%20correction/DR_3205-00_resultats%20rebava%20prova%2020260312%20after%20correction.xls>) · DR!Q9 |

El 24 dice «NO s'ha mesurat nomes report per client» en la entrada del propio informe. Para los postizos de venteo, el archivo del 27 contiene medidas de los postizos del molde y de los nuevos, pero su histórico rotula la entrada «INFORME 22». La comparación no fecha el montaje de esos postizos. [3205-00_intern.24.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/4-%20Metrologia/Interns/3205-00_intern.24.xls>) · HISTORY!F45 · [3205-00_intern.27.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3205/4-%20Metrologia/Interns/3205-00_intern.27.xls>) · HISTORY!A42 y F43:F44

### 3206 · Dos muestreos después de la misma corrección

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 02 | La cabecera de lote dice «21/9/23 after first correction». Es una medición posterior a la primera corrección. | [3206-00_intern.02.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3206/4-%20Metrologia/Interns/3206-00_intern.02.xls>) · DR_(100%)!M9 |
| 00 · 03 | La cabecera dice «19/10/23 After 2nd correction». La segunda corrección ya se había hecho cuando se obtuvieron estas piezas. | [3206-00_intern.03.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3206/4-%20Metrologia/Interns/3206-00_intern.03.xls>) · DR_CC!M9 |
| 00 · 04 | También dice «After 2nd correction» y fecha su lote el **18/10/23**, un día antes que el lote del 03. Por tanto, el salto del informe 03 al 04 no identifica una tercera intervención. | [3206-00_intern.04.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3206/4-%20Metrologia/Interns/3206-00_intern.04.xls>) · DR_CC!M9 |
| 00 · 17, por la carpeta | El Excel del 17 se guarda en la ronda posterior a los postizos de los nervios. El lote es 316163. Hay distintas magnitudes propuestas después de montar los postizos. Falta identificar cuál se ejecutó. | [3206-00_intern17_corr.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3206/5-%20Retoques%20molde/20250709_correction%20after%20ribs%20inserts/3206-00_intern17_corr.xls>) · carpeta «correction after ribs inserts» e INTRO!C54 · [Versiones del plan](2-nervios-soldadura/README.md) |

### 3214 · Punzones modificados y sustitución de un postizo

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 07 | El soporte del cliente para el lote 316233 identifica **punzones modificados a Ø2,34 ±0,02 mm**. Es la medida indicada para el punzón. | [3214-00_int.07_EC.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3214/4-%20Metrologia/Customer/Suport_int_07/3214-00_int.07_EC.xls>) · HISTORY!F23 y DR!H12 |
| 00 · 08 | El soporte del ensayo indica postizos de Ø2,34 ±0,02 mm y especifica que se sustituyó el correspondiente a la **cavidad 11**. | [3214-00_int.08_EC.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3214/4-%20Metrologia/Customer/Suport_int_08/3214-00_int.08_EC.xls>) · DR_EC!H12 |
| 00 · 14 | Se ensayaron punzones de recambio, grupos 1–4 y 5–8, lote 316789. No se identifica qué punzón de producción sustituyó cada uno ni cuándo entró en servicio. | [3214-00_int.14.xls](<../../../proyectos/11.%20inteplast/Exemples/2-%20Nervios%20de%20Soldadura/3214/4-%20Metrologia/Interns/3214-00_int.14.xls>) · DR!H12 y L12 e HISTORY!F42 |

### 3218 · Correcciones con seguimiento del resultado

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 21, como base de la ronda 8 | El plan repasa el resultado de la ronda anterior. Da por corregidas N201, N202, N409, N217, N218, N1604, N1910, N2612 y N2903. Para N501 indica corrección insuficiente, y para N2210, exceso en una comprobación y posición insuficientemente corregida en otra. También explicita actuaciones pendientes en N2403, N2700, N2705 y N2904. El Excel del 21 acompaña ese repaso. | [20250905-Mold correction_8_P3218.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20250905%208th%20correction/20250905-Mold%20correction_8_P3218.pptx>) · diapositivas 1–15 · [3218-00_intern.21_corrections.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20250905%208th%20correction/3218-00_intern.21_corrections.xls>) · Excel de la carpeta de la ronda 8 |
| 00 · 32 | El informe registra medición parcial tras corrección y piezas medidas a las 48 h. Una hoja identifica **pasadores modificados**, quinta inyección, lote 316633. Se usaron dos versiones del programa de medida. El histórico no numera la corrección. | [3218-00_intern.32.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.32.xls>) · HISTORY!F45 y «Modified pins - 5th shot»!I12 e I19 |
| 00 · 33 | Medición parcial tras el **plan 12**. En el plan siguiente se describen correcciones insatisfactorias de diámetro y se aportan comparaciones del molde antes/después en varias diapositivas. Las instrucciones para fabricar otros postizos o reducir de nuevo el diámetro abren la ronda siguiente. | [3218-00_intern.33.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.33.xls>) · HISTORY!F49 · [2026-06-30 Mold correction_13_P3218_rev1_measurement Kowa.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20260512%2013th%20correction/2026-06-30%20Mold%20correction_13_P3218_rev1_measurement%20Kowa.pptx>) · diapositivas 1–4, 9–10 |
| 00 · 34 | Medición parcial tras el **plan 13**. En la revisión posterior se dice que la cavidad 6 ya está bien y cambió de posición, y que la corrección de la cavidad 4 fue incorrecta para la acción rotulada 13.9. | [3218-00_intern.34.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.34.xls>) · HISTORY!F53 · [20260715-Mold correction_14_P3218.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20260715%2014th%20correction/20260715-Mold%20correction_14_P3218.pptx>) · diapositivas 2 y 9 |
| 00 · 35 | Medición parcial tras el **plan 14**. El informe confirma la ronda sin enumerar las operaciones ejecutadas. El fichero de la ronda 14 reutiliza números de acción 13.x. | [3218-00_intern.35.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.35.xls>) · HISTORY!F57 · [20260715-Mold correction_14_P3218.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20260715%2014th%20correction/20260715-Mold%20correction_14_P3218.pptx>) · diapositivas 1–2 |
| 00 · 36 | El histórico identifica medición parcial tras el **plan 15**. El plan pedía reducir el diámetro y mejorar la redondez. El informe confirma la ronda, pero deja sin verificar la magnitud realmente aplicada en cada cavidad. | [3218-00_intern.36.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.36.xls>) · HISTORY!F61 · [20260826-Mold correction_15_P3218.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20260828%2015th%20correction/20260826-Mold%20correction_15_P3218.pptx>) · diapositiva 1 |

**Dos vínculos de origen que suelen confundirse con la ejecución.** En el **27**, para N202/1, la celda `T24` dice `10.1`. La misma fila reúne las medidas, la indicación de que se debe corregir y la propuesta por cavidad. El **31** identifica el lote 316527 que aparece en la tabla de la primera diapositiva del plan 11. En ambos casos sabemos qué se midió para preparar el plan. [3218-00_intern.27_Customer comment_corrections.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20251112%2010th%20correction/3218-00_intern.27_Customer%20comment_corrections.xls>) · KnO - 3D CMM+ ICLs!A24:AJ24 · [20260210-Mold correction_11_P3218.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/5-%20Retoques%20molde/20260204%2011th%20correction/20260210-Mold%20correction_11_P3218.pptx>) · diapositiva 1 · [3218-00_intern.31.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20A/3218/4-%20Metrologia/Interns/3218-00_intern.31.xls>) · HISTORY!A40 y F41

### 3237 · Serie 20, poros de soldadura

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 20 · 07 → 08 | En el 07 las piezas quedaban en el lado de inyección por «porus soldadura». En el 08 el histórico dice que **se retocó el molde para eliminar esos poros**. Se midieron piezas sin humidificar del lote 136904. La fuente da el motivo y la intervención. Quedan sin especificar la operación de taller y el efecto cuantitativo sobre una cota. | [3237-20_intern.08.xls](<../../../proyectos/11.%20inteplast/Exemples/3-%20Paredes%20muy%20Delgadas/3237/4-%20Metrologia/Interns/V20/3237-20_intern.08.xls>) · HISTORY!A22, F24, A25 y F26 |

En la serie 10, una hoja de la copia de cliente del 01 lleva las columnas «Retocat» y «Original». La cabecera por sí sola no permite identificar qué parte del molde se cambió. [3237-10_intern.01 including CPK.xls](<../../../proyectos/11.%20inteplast/Exemples/3-%20Paredes%20muy%20Delgadas/3237/4-%20Metrologia/Customer/3237-10_intern.01%20including%20CPK.xls>) · N147-3!O2:P2

### 3309 · Resultados T2 y T3

| Muestreo | Qué consta | Evidencia |
|---|---|---|
| 00 · 01 → 02 (T2) | El lote se identifica como posterior al primer retoque. El PowerPoint de resultados da N6 como OK. Sus ocho valores de las cuatro cavidades coinciden con el Excel, en las filas «DOWN» y «UP». También registra mejora de marcas de expulsores, rebabas del clip aceptables y textura todavía insuficiente. La cantidad de acero realmente retirada para cada cota queda sin especificar. | [20260528-Mold correction_1_results_P3309.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3309/5-%20Retoques%20molde/20260528-Mold%20correction_1_results_P3309.pptx>) · diapositivas 1 y 11 · [3309-00 Int_02.xls](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3309/4-%20Metrologia/Interns/3309-00%20Int_02.xls>) · DR!N5 e I17:L18 |
| 00 · 02 → 03 (T3) | El informe T3 **confirma que se añadieron 0,25 mm** en la ronda anterior para N14 y N16. Ambas pasan a tolerancia según ese informe, y N5 queda fuera en algunas mediciones. Las dos copias de cliente del 03 discrepan. Para comparar valores concretos debe conservarse la copia consultada. | [20260821-P3309-T3_mold correction.pptx](<../../../proyectos/11.%20inteplast/Exemples/1-%20Clips%20en%20Piezas/Tipo%20B/3309/5-%20Retoques%20molde/20260821-P3309-T3_mold%20correction.pptx>) · diapositiva 1 · [Comparación de las copias de T3](1-clips/3309.md#qué-pasó-después-cadena-corrección--medición) |

## Piezas con planes o mediciones sin ejecución fechable por acción

| Pieza | Qué permiten leer los documentos |
|---|---|
| 2820 | La entrega contiene el plano y el CAD de la pieza. Falta una serie de Metrología y documentación de retoques para reconstruir intervalos. [Ficha de la 2820](0-bolt-eye/2820.md) |
| 3197 | Los Excel de Retoques relacionan los planes 1, 2, 3 y 4 con los muestreos de **origen** 02, 03, 05 y 09. Se conservan los PowerPoint de los planes 1–3. Esas referencias explican qué se pidió a partir de cada informe. La magnitud ejecutada y el informe posterior a cada operación quedan abiertos. [Planes de la 3197](0-bolt-eye/3197.md) |
| 3212 | El plan 1 parte del **01** y se comparan sus resultados con el **03**. El plan 2 parte del **03** y el **05** aporta nuevas medidas de CMM. **03 y 04 comparten el lote 315346**. La acción 2.7 sobre N265 incluso plantea dos explicaciones para obtener el mismo resultado que antes, que no se hubiera aplicado el retoque o que se hubiera medido mal. La ficha técnica recoge las propuestas, previsiones y medidas por cota y cavidad. [3212-00_intern.04.xls](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3212%20Pump%20Housing/4-%20Metrologia/3212-00_intern.04.xls>) · HISTORY!F18 y F23 · [20240318-Mold correction_2_P3212_rev1.pptx](<../../../proyectos/11.%20inteplast/Exemples/0-%20Bolt%20Eye/3212%20Pump%20Housing/5-%20Retoques%20de%20molde/2N/20240318-Mold%20correction_2_P3212_rev1.pptx>) · acción 2.7 · [Historial detallado](0-bolt-eye/3212/historial-molde.md) |
| 3226 | El 01 y su copia en Retoques permiten estudiar las dimensiones y las holguras de montaje con la 3227. Falta una actuación ejecutada vinculada al 01. [Ficha de la 3226](ingesta/3226.md) |
| 3233 | En Retoques hay una plantilla de PowerPoint. En Metrología constan cambios de programa de medida y de condiciones de proceso. Esos cambios no acreditan una modificación física del molde. [Ficha de la 3233](ingesta/3233.md) |
| 3238 | En la serie 20, el 03 identifica un lote con postizos rotos. El informe documenta el estado del molde. Queda sin situar su reparación o sustitución en un muestreo. [3238-20_intern.03.xls](<../../../proyectos/11.%20inteplast/Exemples/3-%20Paredes%20muy%20Delgadas/3238/4-%20Metrologia/Interns/V20/3238-20_intern.03.xls>) · DR!G9 e HISTORY!F8 · [Ficha de la 3238](ingesta/3238.md) |
| 3288 | Los planes describen actuaciones previstas en base y tapa. Entre los informes 02 y 04 se repite el bloque de valores de la base. En la tapa también se repiten muchas filas. El parte de servicio de BBS del 15–19/06/2026 explica que en la prueba de la tapa la inyección rápida producía más rebabas y que conectaron un segundo termorregulador. Identifica un cambio de proceso y un resultado observados. No fecha un mecanizado de la tapa. [Report Inteplast.pdf](<../../../proyectos/11.%20inteplast/Exemples/4-%20Tetones/3288/5-%20Retoques%20molde/20260622_3rd%20loop%20of%20correction/Report%20Inteplast.pdf>) · página 3, miércoles y jueves [Planes y comparación por componente](4-tetones/3288.md) |

## Referencia para evaluar el vínculo con un plan numerado

Etiquetas tomadas de la revisión documental anterior a la prueba del script. La unidad es pieza, serie, informe y plan. «Posterior» significa que el informe documenta o permite comprobar el resultado de esa ronda con el alcance descrito arriba. En la 3218, el informe 21 se identifica cruzando el Excel de la ronda 8 con el repaso de la 7. «Origen» identifica el informe usado para preparar ese mismo plan. «Sin medición» exige abstenerse de presentarlo como una comprobación nueva. Los casos con un retoque sin número de plan y los muestreos sin evidencia suficiente siguen abiertos. La revisión y las cavidades solo se evalúan cuando tienen etiqueta expresa.

| Pieza | Serie | Intern | Relación | Plan | Revisión | Cavidades |
|---|---|---|---|---|---|---|
| 3195 | 00 | 16 | posterior | 5 | 0 | 1 |
| 3195 | 00 | 17 | posterior | 5 | 1 | todas |
| 3195 | 00 | 18 | posterior | 6 | — | — |
| 3202 | 00 | 03 | posterior | 1 | — | — |
| 3206 | 00 | 02 | posterior | 1 | — | — |
| 3206 | 00 | 03 | posterior | 2 | — | — |
| 3206 | 00 | 04 | posterior | 2 | — | — |
| 3218 | 00 | 21 | posterior | 7 | — | — |
| 3218 | 00 | 33 | posterior | 12 | — | — |
| 3218 | 00 | 34 | posterior | 13 | — | — |
| 3218 | 00 | 35 | posterior | 14 | — | — |
| 3218 | 00 | 36 | posterior | 15 | — | — |
| 3309 | 00 | 02 | posterior | 1 | — | — |
| 3309 | 00 | 03 | posterior | 2 | — | — |
| 3197 | 00 | 02 | origen | 1 | — | — |
| 3197 | 00 | 03 | origen | 2 | — | — |
| 3197 | 00 | 05 | origen | 3 | — | — |
| 3197 | 00 | 09 | origen | 4 | — | — |
| 3212 | 00 | 01 | origen | 1 | — | — |
| 3212 | 00 | 03 | origen | 2 | — | — |
| 3218 | 00 | 27 | origen | 10 | — | — |
| 3218 | 00 | 31 | origen | 11 | — | — |
| 3309 | 00 | 01 | origen | 1 | — | — |
| 3205 | 00 | 24 | sin medición | — | — | — |

### Resultado de la prueba interna del 27/11/2026

El script recorrió los 355 muestreos de la entrega. Primero calculó sus propuestas a partir de la biblioteca de PowerPoint y Excel. Después leyó la tabla anterior para puntuarlas. Las reglas se desarrollaron conociendo estos ejemplos. La prueba mide qué información se puede recuperar en esta entrega y queda pendiente medir el rendimiento en piezas nuevas.

| Regla | Vínculos recuperados de los 14 documentados | Plan equivocado | Sin propuesta de los 14 | Otras propuestas pendientes de confirmar |
|---|---:|---:|---:|---:|
| Coincidencia de cotas y fechas | 1 | 0 | 13 | 14 |
| Notas del Excel, repaso del PowerPoint y coincidencia de cotas | 13 | 0 | 1 | 14 |

En los diez controles, ninguna regla atribuyó al informe la comprobación del plan que había servido para preparar, ni atribuyó una medición nueva al 24 de la 3205. De los trece aciertos, doce tienen una nota de Excel y uno se recupera del PowerPoint. En la 3195 se recuperan también la revisión y las cavidades de los informes 16 y 17. Una de las doce notas coincide además con la propuesta por cotas.

- **Qué lee el script.** En el Excel busca una ronda identificada en el bloque del informe actual de `HISTORY`, en la cabecera de las hojas o en los datos de lote de `INTRO`. Descarta las notas de cabecera repetidas literalmente, tras normalizar acentos y espacios, en un intern anterior de la misma pieza y serie. En los PowerPoint reconoce cuándo una diapositiva distingue el resultado de una ronda numerada de la propuesta siguiente y la carpeta contiene un solo intern identificable.
- **Qué significa una propuesta por cotas.** En una misma copia de Excel tienen que aparecer medidas nuevas para al menos dos cotas y la mitad de las cotas identificadas en un PowerPoint. Se exige un intern de origen identificado por un Excel en la carpeta del plan y una fecha del informe posterior o igual a la del plan. Las propuestas por cotas quedan pendientes de confirmación. Las 14 que carecen de etiqueta documental no permiten calcular cuántas acertaríamos en una pieza nueva.
- **Qué quedó fuera.** Para la 3309, intern.03, el PowerPoint T3 dice que en la ronda anterior se añadieron 0,25 mm en N14 y N16. Para identificar el plan 2 hay que comparar esa frase con el PowerPoint anterior y contrastarla con las copias del Excel. El script deja ese caso abierto. Las actuaciones sin número de ronda siguen en el inventario cualitativo de arriba.

La prueba se puede repetir desde la raíz del repositorio con `python conocimiento/herramientas/vincular_retoques.py --evaluar`. Con `--pieza 3195` se ve la procedencia de cada propuesta para esa pieza. El cálculo usa la biblioteca en modo de solo lectura. [Script de la prueba](herramientas/vincular_retoques.py)

## Cómo incorporar nueva evidencia

Para añadir una fila, registrar pieza, serie, muestreo, actuación que la fuente da por hecha, cota o cavidad si constan y localizador del original. Si la fuente solo confirma una ronda, conservar ese nivel de detalle. Para atribuir además un **cambio dimensional**, comparar la misma cota, cavidad, elemento y método antes y después, y comprobar que las cifras sean mediciones nuevas. Si el expediente solo aporta una propuesta o dos valores distintos, el vínculo de ejecución queda abierto. La [cadena de comparación de medidas](herramientas/cadena_correcciones.py) permite localizar esos casos para su revisión.
