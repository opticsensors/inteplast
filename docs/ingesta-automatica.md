# Ingesta automática de Exemples: qué puede leer la app sola y qué no

> **Plan del 21/10/2026. No se ha tocado el código de la app.** Las cifras se han medido sobre
> los 4.530 ficheros de `Exemples` con la biblioteca de [`conocimiento/`](../conocimiento/README.md)
> y con prototipos que viven allí (`conocimiento/herramientas/lector_dr.py`, tablas `lectura_dr` y
> `medida_dr`). La app no los importa: lo que se apruebe se reimplementa en `backend/app/ingestion/`
> con pruebas sobre fuentes sintéticas, como el resto de lectores.

## La respuesta corta

| Se puede extraer siempre, con reglas | Necesita LLM (con validación y revisión) | Ni algoritmo ni LLM: falta el dato |
|---|---|---|
| Pieza, feature, carpeta, nº de informe, fecha y loop desde la ruta | Qué hace cada acción de corrección (añadir o quitar plástico, erosionar, postizo, no actuar…), si la magnitud es total o por lado, dependencias | Qué versión de un plan se ejecutó (I-401) y qué versión de un informe se entregó (I-603) |
| Medidas de los informes PPAP internos (`DR*`) y de cliente (`cav_N`) | Método de medida en DOCX/PDF/DOC | Si `OK` en una diapositiva significa aprobado o ejecutado |
| CSV de CMM por bloques, export `#P#`, Q-DAS `.dfd` | Lecciones aprendidas y warnings: síntesis entre loops y piezas | Para qué se usaron los valores generados con `RAND()` (I-003) |
| Metadatos de la hoja `HISTORY` | Qué cotas son el feature en cada pieza (propuesta para confirmar) | Columna 29 de los `DR` del 3288 (I-107) |
| Título, cotas, nominal, magnitudes y fecha de las correcciones PPTX que siguen la plantilla (80 % de las diapositivas) | Correos `.msg` y presentaciones de análisis sin plantilla | |
| Posición de los globos en el plano (`.icp`/`.prf`), calibrando cada plano | Zona y sentido marcados en la imagen (flecha, superficie roja): LLM con visión **sin probar**, o una persona | |
| Marcas de calidad: valores `RAND`, copias, comparativas, atípicos, ceros, bloques heredados | | |

## 1. Lo que la app puede leer siempre (medido)

### 1.1 Identidad desde la ruta

| Dato | Cobertura | Nota |
|---|---|---|
| Pieza (código de 4 dígitos) | 4.529 de 4.530 ficheros | El que falta es el `Readme.txt` de `5- Anclajes` |
| Carpeta normalizada (metrología, retoques, molde…) | 4.530 de 4.530 | Dos esqueletos de carpetas, un vocabulario (`comun.carpeta_normalizada`) |
| Nº de informe (`intern.NN`, `Int_NN`, `INF_NN`) en el nombre | 590 de 626 libros con tablas | |
| Fecha `YYYYMMDD` en subcarpetas de retoques | 57 de 99 (1 imposible: `20270728…`) | Validar rango; la fecha de carpeta no es la de medición |
| Nº de loop en subcarpetas de retoques | 66 de 99 | Formatos «1st loop», «6th correction», «N2», «Loop 5» |

Una pieza puede estar en varios features: la carpeta con solo `Readme.txt` remite a la buena. La
identidad tiene que ser el código, no la carpeta.

### 1.2 Informes dimensionales PPAP

**Hoy la app** (`measurement_tables.report_rows`) lee 738 de las 1.335 hojas con cabecera PPAP
reconocible (55 %). Además, `xlrd` no abre 14 libros.

**El prototipo** con las reglas de abajo lee 1.236 de esas 1.335 (92,6 %) y, contando las hojas
que la app no considera (plantilla de cliente por cavidad, hojas sin nombre `DR`), **1.791 hojas y
≈1,67 M de valores**. Las 99 que no lee: 64 son plantillas casi vacías (está bien que no den nada)
y 35 tienen números que habría que revisar a mano (2,6 %; la app lee una de ellas). Son sobre todo
la plantilla del 3247 sin código en la columna A y comparativas sueltas.

Por qué falla hoy y regla que lo arregla:

| Causa (hojas afectadas) | Regla determinista |
|---|---|
| Se salta toda hoja con «100%» en el nombre (303) | 290 de 316 hojas «100%» son el informe completo, no previsiones. Decidir por etiquetas de corrección en la cabecera (`Retoc`, `Corr.`, `Correction`, `RETOC PROPOSAT`, `MESURA FINAL PREVISTA`, `Desviació`), no por el nombre |
| La hoja no empieza por `DR` (188: nombres de lote como `315614`) | Detectar la tabla por estructura: fila con «Nominal»/«Target» y columnas de cavidad en las 40 primeras filas |
| Cavidades rotuladas solo con número (`1`…`20`, 3288) o una hoja por cavidad (`cav_N` con muestras 1…5) | Admitir números consecutivos tras el nominal; plantilla de cliente: cavidad del nombre de hoja |
| Etiquetas distintas | Sinónimos: `Tol +`/`Tol. +`, `Equipment`/`Equipo`/`Meas. Equip.`/`Measuring Device`, `Nominal`/`Target`, `Nr`/`Number` |
| Código de cota fuera de la columna A, ids de cliente (`1-197.1`, `B-0580-935.1`), letras (`A`, `Z1`) o nombres (`Distance 1`, `POST 1`) | Columna por etiqueta o, sin ella, la de más códigos a la izquierda del nominal. Nombres cortos con nominal y valores se aceptan marcados |
| Tolerancias escritas al revés (2.197 filas, p. ej. `+(−0,658) / −0`) | Mismo intervalo: ordenar y marcar |
| Bloques auxiliares a la derecha con rótulo de cavidad (`CAV.312` = índices calculados) | Cavidad válida 1–64 y solo el primer bloque contiguo. Bloques siguientes solo si tienen encima un rótulo de condición («750 bars», «punxons recanvi…»); sin rótulo son previsiones o desviaciones |
| Libros que `xlrd` no abre (14) | `python-calamine` abre los 13 probados y da los valores guardados; coinciden con los de la biblioteca en 84.038 de 84.038 celdas numéricas |

**Validación independiente** (no es la misma lógica que extrae):

- **Columna NOK del propio libro.** En las hojas de informe, cuando el libro marca NOK, el cálculo
  con nominal + tolerancias + valores leídos también da fuera en el **96,2 %** (32.996 de 34.301
  filas). Las discrepancias son sobre todo del libro: 7.380 filas fuera en hojas que no usan la
  columna NOK y 2.448 claramente fuera sin marcar en hojas que sí la usan. Al revés, 552 filas
  marcadas sin motivo aparente.
- **Export `#P#` frente a la plantilla de cliente.** 5.188 de 5.188 líneas `#P#` que encuentran su
  fila (misma cota y mismos valores) tienen el mismo nominal y los mismos límites. 400 de ellas
  están en dos versiones del libro con tolerancias distintas: es el caso I-603.
- **Lectura del 3197 frente a los originales** (septiembre, lector actual): 30 valores CSV y 30 XLS,
  60 coincidencias ([app-web](app-web.md)). Comparar CSV y XLS de un mismo muestreo queda
  pendiente; en el 3212 el CSV manda (I-001).

**Marcas que el lector debe poner** (y por defecto no importar como medida):

| Marca | Hojas | Valores | Regla |
|---|--:|--:|---|
| `generada` (celdas `RAND`/`RANDBETWEEN`/`NORM.INV(RAND())`) | 74 | 117.172 | Leer la fórmula, no solo el valor guardado. xlsx: `<f>` del XML; xls: registros `FORMULA`/`SHRFMLA` con el token de `RAND` o el nombre `RANDBETWEEN`/`ALEATORIO`. Con una sola celda aleatoria, marcar la hoja entera: lo que depende de ella (`MIN`, `MAX`…) tampoco es medida |
| `comparativa` (`DIF`, `Differences`, `vs`, `Comparation`) | 29 | 121.634 | Por nombre de hoja; guardan diferencias entre sistemas o condiciones |
| `copia` (nombre acabado en ` (n)`) | 87 | 54.021 | Duplicados o generadores |
| `sospechosa` (más del 30 % de valores atípicos) | 19 | 6.447 | Desviaciones guardadas como valores, plantillas de otra pieza (I-303, I-105) |
| `atipico` (desviación > 10 × intervalo y > 1) | — | 0,45 % de los valores de informe | Errores de signo (3218 cota 2611: −9,94 con nominal 10), nominal de otra cota (3174 cota 507) |
| `cero` (0 con nominal ≠ 0) | — | 3.967 | Medida no hecha (I-002) |
| `heredado` | — | — | Comparar con el informe anterior de la misma pieza: bloques idénticos (I-001; 5.079 de 5.079 en el 3288) |

(Totales de `lectura_dr`; una hoja puede llevar varias marcas.)

### 1.3 Otros formatos estructurados

| Fuente | Resultado | Nota |
|---|---|---|
| CSV CMM por bloques | La app ya lee los 86 informes | Las 50 listas de puntos (`*Punts*`) se rechazan, como debe ser |
| Export `#P#` (`.txt`, 4 `.csv`) | 568 ficheros, 24.494 líneas | Campo 3 = tipo: `1` variable, `2` atributo (nominal y límites vacíos: 3.454 líneas). 4.770 líneas sin valores. Los SPC (50–125 valores) salen de generadores con `RAND` (I-003): no son medidas |
| Hoja `HISTORY` | 582 de 584 libros con rótulos `INFORME n` | De 3.611 informes reales, 3.009 con fecha en la columna A. Los demás: 199 la llevan solo en texto y 403 están vacíos. Otros 495 rótulos son huecos de plantilla al final |
| Globos `.icp` + `.prf` (infra-CONVERT) | 19 planos, 2.118 sellos (51 sin coordenadas) | Número y posición de cada globo. La transformación a la página está validada en un plano (99 % a < 10 pt); hay que calibrar cada plano (centro de la hoja, escala) |
| Q-DAS `.dfd` | 1 fichero | Campos K estándar |
| Método de medida en XLS (`MM_revNN.xls`, hoja `DIMENSIONS`) | 30 libros | Cota, equipo e instrucción en columnas |
| Plano 2D: número y revisión | Del nombre del fichero (`…0140S00237_07`, `…_D_02`, `rev.B`) | 20 planos únicos: 7 escaneados, 2 casi sin texto, 11 vectoriales |

### 1.4 Correcciones PPTX: la parte que sale por reglas

Medido sobre las 1.534 diapositivas de `perfil_correccion`, todas las piezas:

| Campo | Diapositivas | Regla |
|---|--:|---|
| Número `n.m` | 1.234 (80 %) | Títulos `Tool correction n.m`, `Correcció nr.`, `DIM#n`, `Correction n` |
| Cotas (`DIM. Nr. a, b and c`) | 945 (62 %) | Varias cotas por título, subpuntos `1320.2` |
| Bloques situación actual / plan | 1.033 (67 %) | `Current/Actual situation`, `Tool correction plan`/`Correction proposal`/`Pla de correcció` |
| Magnitud en mm | 771 (50 %) | Regex; **qué significa** (total, por lado, en radio) no sale por regex |
| Cavidades explícitas | 250 (16 %) | En el resto no se nombran: probablemente todas, sin confirmar |

Nervios (47 %) y Planitudes (33 %) bajan porque muchas diapositivas son análisis sin plantilla.
También salen por reglas la fecha y la paginación de la cabecera (`31/10/2023 · 10/42`), el
nominal con tolerancia del título y las tablas de la diapositiva (p. ej. movimientos X/Y por
cavidad en el 3218, 13.9). Las previsiones de los libros de corrección se leen por etiqueta de
columna (§1.2), no por posición fija: el 3212 tiene `Retoc` en O, el 3197 en T.

## 2. Lo que necesita un LLM

### 2.1 Prueba a mano: 14 diapositivas al azar

Extraje lo que haría un LLM en 14 diapositivas distintas de 7 piezas, en inglés y catalán:

| Campo | Sale del texto | Necesita la imagen |
|---|--:|--:|
| Tipo de acción («Increase plastic», «burn/erode», «new inserts», «venting», «Do not corrected… wait») | 12 | 2 (rebabas sin acción escrita; «segons detall») |
| Total o por lado («split for both sides», «each side… in total», «in radius») | 14; en 3 hay que interpretar | — |
| Cavidades | 2 explícitas; 12 no las nombran | — |
| Zona y sentido («red surface», «arrow direction») | 7 | **7** |

Conclusión: **el LLM aporta clasificación de texto libre multilingüe, no números**. Las magnitudes
y las cotas ya salen por reglas. La zona marcada en rojo y las flechas solo están en la imagen: se
guardan como evidencia (diapositiva y recorte) y se describen a mano, salvo que una prueba con
un modelo con visión demuestre lo contrario.

### 2.2 Cómo usarlo sin perder fiabilidad

1. **Lote, no chat.** Se ejecuta al importar, fuera del asistente. El `qwen3.5:2b` del asistente
   es pequeño para extracción estructurada (no probado). El modelo es decisión pendiente, y los
   datos son del cliente: Ollama local con un modelo mayor o el que se acuerde (acta del 24/09).
2. **Esquema cerrado.** Salida JSON con vocabulario fijo:
   - `accion`: `anadir_plastico`, `quitar_plastico`, `erosionar_pulir`, `postizo_nuevo`, `mover`, `venteo`, `parametros_proceso`, `no_actuar`, `verificar`, `otra`.
   - `reparto`: `total`, `por_lado`, `en_radio`, `por_cavidad`, `no_consta`.
   - `cavidades`: lista, `todas` o `no_consta`.
   - Además: `depende_de` y `estado`.
3. **Sin números propios.** La magnitud, las cotas y las cavidades se eligen entre las candidatas
   que ya extrajeron las reglas.
4. **Cita literal por campo.** Cada campo lleva el fragmento de texto que lo justifica.
5. **Validación determinista.** La cita existe en la diapositiva; la cota está en el título; la
   magnitud está entre las candidatas; las cavidades existen en la pieza. Si algo falla, la
   propuesta va a revisión, no a la base.
6. **Revisión humana en la web.** Todo queda `propuesto` hasta que alguien lo acepta, como hoy
   con los globos (`EvidenceJob`, `DrawingLocation`). Medir la tasa de aceptación por campo y por
   plantilla.
7. **Conjunto de referencia antes de elegir modelo.** Partir de los casos revisados del 3212
   (`pilot_3212`) y anotar 40–60 diapositivas de otras 4–5 piezas, con al menos una por plantilla
   de título. Escribir los resultados esperados **antes** de programar
   ([próximos pasos §1](proximos-pasos.md)).

### 2.3 Otras tareas de LLM (todas como propuesta para revisar)

- **Método de medida en DOCX/PDF/DOC:** cómo se mide cada cota, alineación, equipo.
- **Lecciones aprendidas y warnings:** resumir una cadena muestreo → corrección → muestreo y las
  repeticiones entre piezas (el Bolt Eye pequeño en la primera prueba del 3212 y del 3197; nervios
  postizos tras rebabas repetidas). Siempre con enlaces a las fuentes.
- **Feature ↔ cotas:** los datos no dicen qué cotas son «el tetón» o «el clip» (I-106). Proponer
  candidatas con búsqueda de palabras clave en correcciones y métodos («clip», «pocket», «rib»,
  «nervi», «bolt») y que alguien las confirme.
- **Correos, presentaciones de análisis (8D informal), fotos y vídeos:** resumen opcional; el
  valor está en enlazarlos como evidencia, no en estructurarlos.

## 3. Lo que no está en los datos

Ni reglas ni LLM pueden decidir:
- qué versión de un plan se ejecutó (I-401);
- qué versión de un informe se entregó (I-603);
- qué significa el marcador `OK`;
- si los valores `RAND` se usaron en alguna entrega (I-003).

La app debe mostrar las versiones y dejar elegir. Por defecto: la carpeta `Uploaded to IQS`
cuando exista; si no, la versión más reciente. Esto se pregunta a INTEPLAST; ver
[preguntas abiertas](preguntas-abiertas.md) (pendiente de revisar).

## 4. Orden propuesto

| Fase | Qué | Con qué se comprueba |
|---|---|---|
| 0 | Generalizar `report_rows` con las reglas de §1.2 y `calamine` para `.xls`. Marcas `generada`/`copia`/`comparativa`/`atipico`/`cero` | Las cifras de §1.2 y la concordancia NOK por hoja; por debajo del 90 %, revisión |
| 1 | Lectores de `#P#` (sin los SPC), `HISTORY` e identidad desde la ruta; detección de bloques heredados | `#P#` frente a PPAP de cliente (5.188 de 5.188); `HISTORY` frente a cabecera |
| 2 | Correcciones de todas las piezas: título, cotas, magnitudes, fecha, tablas; previsiones por etiqueta; enlace con las mediciones de la misma pieza por cota | Conjunto de referencia por plantilla |
| 3 | LLM en lote para el significado de las acciones, con validación y revisión (§2.2) | Tasa de aceptación por campo |
| 4 | Lecciones, warnings y feature ↔ cotas propuestos por LLM | Revisión de INTEPLAST |
| — | Zonas en imagen y escaneos | Solo si una prueba con visión lo justifica |

Las fases 0–2 no necesitan LLM y cubren las medidas y la estructura de las correcciones de las
21 piezas con datos.

## 5. Decisiones pendientes (Eduard)

- Modelo y lugar del LLM de extracción (local o Copilot) y si los datos del cliente pueden salir
  del servidor.
- Política por defecto para valores `generada` y versiones de informe (propuesta: no importarlos
  como medida y mostrarlos marcados).
- Si los atributos (`#P#` tipo 2, OK/NOK visuales) entran como cotas cualitativas.

## Cómo repetir las mediciones

```bash
PY=conocimiento/.venv/Scripts/python.exe
$PY conocimiento/herramientas/formulas_aleatorias.py   # celda_aleatoria
$PY conocimiento/herramientas/lector_dr.py             # lectura_dr (por hoja) y medida_dr (por valor)
$PY conocimiento/herramientas/consultar.py sql "SELECT papel, count(*), sum(valores) FROM lectura_dr GROUP BY papel"
```

La concordancia NOK está en `lectura_dr.nok`: `[no marcado y dentro, no marcado y fuera, marcado
y dentro, marcado y fuera]`.
