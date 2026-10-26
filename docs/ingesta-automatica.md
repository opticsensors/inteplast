# Ingesta automática de Exemples: qué puede leer la app sola y qué no

> **Plan del 21/10/2026, revisado contra el código el 26/10/2026.** Las cifras de cobertura
> se conservan como registro del estudio de los 4.530 ficheros de `Exemples`; no se han
> recalculado en esta revisión. Proceden de [`conocimiento/`](../conocimiento/README.md)
> y sus prototipos (`lector_dr.py`, tablas `lectura_dr` y `medida_dr`). La app no importa
> estos módulos ni su SQLite. Las correcciones posteriores de la biblioteca no cambian
> automáticamente el lector productivo ni actualizan las cifras históricas de este plan.

## La respuesta corta

**Implementado:** alta/actualización de piezas, CSV CMM individuales y comparativos,
un subconjunto de informes XLS/XLSX y el adaptador de correcciones del piloto 3212.
Los contratos, versiones y límites están centralizados en
[cotas y evidencia](cotas-y-evidencia-web.md#alta-y-actualización-de-piezas-22092026).
`measurement_tables.py` exige hojas `DR…` sin `100%`, cabeceras y códigos reconocidos;
lee cachés numéricas, usa `xlrd` para XLS y no detecta fórmulas aleatorias. Tampoco
reconoce como PDF un archivo con extensión XLS. Los lectores alternativos y las
marcas de calidad descritos abajo son trabajo pendiente de la app.

**Ampliación propuesta:** evaluar las reglas experimentales sobre fuentes de
referencia antes de trasladarlas a `backend/app/ingestion/`. El chat actual consulta
datos ya importados; no realiza esta extracción. Su alcance está en
[asistente](asistente.md#qué-puede-consultar).

| Candidatos extraíbles con reglas, según formato | Interpretación a revisar; un LLM sería opcional | Requiere confirmación externa |
|---|---|---|
| Código de pieza, clasificación de carpeta, nº de informe, fecha y loop presentes en la ruta | Qué hace cada acción de corrección, si la magnitud es total o por lado y sus dependencias | Qué versión de un plan se ejecutó (I-401) y qué versión de un informe se entregó (I-603) |
| Medidas de los informes PPAP internos (`DR*`) y de cliente (`cav_N`) | Método de medida en DOCX/PDF/DOC | Si `OK` en una diapositiva significa aprobado o ejecutado |
| CSV CMM y campos de export `#P#` o Q-DAS `.dfd` | Lecciones aprendidas y warnings: síntesis entre loops y piezas | Para qué se usaron los valores generados con `RAND()` (I-003) |
| Metadatos de la hoja `HISTORY` | Qué cotas son el feature en cada pieza (propuesta para confirmar) | Columna 29 de los `DR` del 3288 (I-107) |
| Títulos, cotas, nominales, magnitudes y fechas presentes en PPTX; cada campo tiene cobertura distinta | Correos `.msg` y presentaciones de análisis sin plantilla | |
| Posición de los globos en el plano (`.icp`/`.prf`), calibrando cada plano | Zona y sentido marcados en la imagen (flecha, superficie roja): LLM con visión **sin probar**, o una persona | |
| Indicios de revisión: fórmulas `RAND`, nombres de copia/comparativa, atípicos, ceros y bloques iguales | Confirmar qué representa cada indicio antes de excluir o clasificar valores | |

Los identificadores I-… remiten al registro de
[incongruencias y evidencia](../conocimiento/incongruencias.md), donde se mantienen
las comprobaciones y sus límites; no son funcionalidades de la aplicación.

## 1. Resultados del estudio y reglas propuestas (21/10/2026)

### 1.1 Identidad desde la ruta

| Dato | Cobertura | Nota |
|---|---|---|
| Pieza (código de 4 dígitos) | 4.529 de 4.530 ficheros | El que falta es el `Readme.txt` de `5- Anclajes` |
| Carpeta normalizada (metrología, retoques, molde…) | 4.530 de 4.530 | Dos esqueletos de carpetas, un vocabulario (`comun.carpeta_normalizada`) |
| Nº de informe (`intern.NN`, `Int_NN`, `INF_NN`) en el nombre | 590 de 626 libros con tablas | |
| Fecha `YYYYMMDD` en subcarpetas de retoques | 57 de 99 (una posterior al estudio: `20270728…`) | Revisar su significado; una fecha futura no es una fecha imposible y la carpeta no acredita la fecha de medición |
| Nº de loop en subcarpetas de retoques | 66 de 99 | Formatos «1st loop», «6th correction», «N2», «Loop 5» |

Una pieza puede aparecer en varias familias. La carpeta con solo `Readme.txt` remite
a otra ubicación. El código debe contrastarse con el documento: los nombres pueden
ser heredados y la carpeta no define por sí sola los vínculos feature ↔ cotas.

### 1.2 Informes dimensionales PPAP

**Medición registrada el 21/10 sobre el lector productivo**
(`measurement_tables.report_rows`): 738 de 1.335 hojas con cabecera PPAP reconocible
(55 %) y 14 archivos XLS que `xlrd` no abrió. Es un resultado histórico, no un
recuento revalidado tras las correcciones de la biblioteca.

**El prototipo** registró lectura de 1.236 de esas 1.335 (92,6 %) y, contando las hojas
que la app no considera (plantilla de cliente por cavidad, hojas sin nombre `DR`), **1.791 hojas y
≈1,67 M de valores**. Entre las 99 restantes se clasificaron 64 como plantillas casi vacías
y 35 con números pendientes de revisión (2,6 %; la app leía una de ellas). Son sobre todo
la plantilla del 3247 sin código en la columna A y comparativas sueltas.

Limitaciones observadas y reglas candidatas del prototipo; su aceptación en
producción requiere contraste por plantilla:

| Causa (hojas afectadas) | Regla candidata |
|---|---|
| Se salta toda hoja con «100%» en el nombre (303) | El estudio clasificó 290 de 316 hojas «100%» como informes completos. Evaluar las etiquetas de corrección en la cabecera (`Retoc`, `Corr.`, `Correction`, `RETOC PROPOSAT`, `MESURA FINAL PREVISTA`, `Desviació`) en vez de excluir por nombre |
| La hoja no empieza por `DR` (188: nombres de lote como `315614`) | Detectar la tabla por estructura: fila con «Nominal»/«Target» y columnas de cavidad en las 40 primeras filas |
| Cavidades rotuladas solo con número (`1`…`20`, 3288) o una hoja por cavidad (`cav_N` con muestras 1…5) | Admitir números consecutivos tras el nominal; plantilla de cliente: cavidad del nombre de hoja |
| Etiquetas distintas | Sinónimos: `Tol +`/`Tol. +`, `Equipment`/`Equipo`/`Meas. Equip.`/`Measuring Device`, `Nominal`/`Target`, `Nr`/`Number` |
| Código de cota fuera de la columna A, ids de cliente (`1-197.1`, `B-0580-935.1`), letras (`A`, `Z1`) o nombres (`Distance 1`, `POST 1`) | Columna por etiqueta o, sin ella, la de más códigos a la izquierda del nominal. Nombres cortos con nominal y valores se aceptan marcados |
| Tolerancias escritas al revés (2.197 filas, p. ej. `+(−0,658) / −0`) | Conservar los extremos originales y proponer su ordenación, marcada para revisión; no ocultar la anomalía |
| Bloques auxiliares a la derecha con rótulo de cavidad (`CAV.312` = índices calculados en el caso estudiado) | Propuesta: cavidades 1–64 y primer bloque contiguo; siguientes bloques solo con condición identificada («750 bars», «punxons recanvi…»). Sin rótulo, dejar el papel pendiente en vez de asumir que son mediciones |
| Archivos XLS que `xlrd` no abre (14) | El estudio abrió 13 con `python-calamine`, con 84.038/84.038 coincidencias numéricas frente a la biblioteca. El restante, `3168-00_intern.13_6injecton points.xls`, es un PDF (I-004): hay que reconocer el formato real, no tratar todos los casos como libros Excel |

**Contrastes registrados en el estudio**, con referencias distintas de la lógica
de extracción. Miden concordancia; no certifican por sí solos el significado de
las medidas ni la exactitud de todos los informes:

- **Columna NOK del propio libro.** En las hojas de informe, cuando el libro marca NOK, el cálculo
  con nominal + tolerancias + valores leídos también da fuera en el **96,2 %** (32.996 de 34.301
  filas). Se registraron además 7.380 filas calculadas fuera en hojas sin uso de NOK,
  2.448 fuera sin marcar en hojas que sí la usan y 552 marcadas sin causa identificada.
  Estas diferencias requieren revisar límites, unidades y significado de la marca;
  la concordancia no permite atribuir automáticamente el error al libro.
- **Export `#P#` frente a la plantilla de cliente.** 5.188 de 5.188 líneas `#P#` que encuentran su
  fila (misma cota y mismos valores) tienen el mismo nominal y los mismos límites. 400 de ellas
  están en dos versiones del libro con tolerancias distintas: es el caso I-603.
- **Lectura del 3197 frente a los originales** (septiembre, lector productivo): 30 valores CSV y 30 XLS,
  60 coincidencias ([cotas y evidencia](cotas-y-evidencia-web.md#alta-y-actualización-de-piezas-22092026)). Comparar CSV y XLS de un mismo muestreo queda
  pendiente. La prioridad del CSV en la app es una regla de importación por contexto;
  no convierte todas las discordancias CSV/XLS en errores del Excel (I-001).

**Marcas propuestas para revisión.** Los recuentos siguientes son los de
`lectura_dr` en el estudio del 21/10, no el inventario actual de fórmulas de la
biblioteca. Una hoja puede tener varias marcas. Salvo evidencia directa de la
celda y sus dependencias, una marca de hoja no clasifica todos sus valores.

| Marca | Hojas | Valores | Regla |
|---|--:|--:|---|
| `generada` (presencia de `RAND`/`RANDBETWEEN`) | 74 | 117.172 | Examinar fórmulas reales y dependencias. La presencia de una fórmula aleatoria obliga a revisar la hoja; no demuestra que sus 117.172 valores sean todos generados. Una fórmula sin caché conserva ausencia de valor |
| `comparativa` (`DIF`, `Differences`, `vs`, `Comparation`) | 29 | 121.634 | El nombre orienta; confirmar si las celdas son diferencias, medidas o previsiones |
| `copia` (nombre acabado en ` (n)`) | 87 | 54.021 | El sufijo no demuestra duplicación ni generación; comparar contenido |
| `sospechosa` (más del 30 % de valores atípicos) | 19 | 6.447 | Priorizar revisión de unidades, desviaciones o plantillas heredadas (I-303, I-105) |
| `atipico` (desviación > 10 × intervalo y > 1) | — | 0,45 % de los valores de informe | Detecta candidatos a error de signo/nominal; requiere comprobar el caso y su unidad |
| `cero` (0 con nominal ≠ 0) | — | 3.967 | Su significado no está resuelto (I-002); conservarlo sin afirmar que la medición no se hizo |
| `bloque_igual` | — | — | Igualdad respecto al informe anterior (I-001; 5.079/5.079 en el 3288) no prueba por sí sola copia ni nueva adquisición |

La política de importación de estos casos está pendiente; no existe en el lector
productivo una exclusión general basada en estas marcas.

### 1.3 Otros formatos estructurados

| Fuente | Resultado | Nota |
|---|---|---|
| CSV CMM por bloques | El estudio registró lectura de 86 informes con el lector de la app | Las 50 listas de puntos (`*Punts*`) no son tablas dimensionales; este recuento no garantiza otros formatos CSV |
| Export `#P#` (`.txt`, 4 `.csv`) | 568 ficheros, 24.494 líneas | 3.454 líneas sin nominal/límites y 4.770 sin valores. La semántica del tercer campo no está confirmada. La procedencia de las series SPC debe comprobarse por familia: existen enlaces documentados con generadores y casos sin origen demostrado; ver I-003 |
| Hoja `HISTORY` | 582 de 584 libros con rótulos `INFORME n` | 3.611 entradas candidatas: 3.009 con fecha en columna A, 199 solo en texto y 403 vacías; otros 495 rótulos se clasificaron como huecos finales de plantilla. Un rótulo no acredita la existencia ni entrega de un informe |
| Globos `.icp` + `.prf` (infra-CONVERT) | 19 planos, 2.118 sellos (51 sin coordenadas) | Número y posición de cada globo. La transformación a la página está validada en un plano (99 % a < 10 pt); hay que calibrar cada plano (centro de la hoja, escala) |
| Q-DAS `.dfd` | 1 fichero | Campos K estándar |
| Método de medida en XLS (`MM_revNN.xls`, hoja `DIMENSIONS`) | 30 libros | Cota, equipo e instrucción en columnas |
| Plano 2D: número y revisión | Candidatos en el nombre (`…0140S00237_07`, `…_D_02`, `rev.B`), a contrastar con el cajetín | 20 planos únicos en el estudio: 7 escaneados, 2 casi sin texto, 11 vectoriales. La fecha de archivo no equivale a la de revisión |

### 1.4 Correcciones PPTX: la parte que sale por reglas

Registro del estudio sobre 1.534 diapositivas de `perfil_correccion`. Incluye
versiones, plantillas y documentos heredados; no equivale a 1.534 acciones propias
de las piezas ni ejecutadas:

| Campo | Diapositivas | Regla |
|---|--:|---|
| Número `n.m` | 1.234 (80 %) | Títulos `Tool correction n.m`, `Correcció nr.`, `DIM#n`, `Correction n` |
| Cotas (`DIM. Nr. a, b and c`) | 945 (62 %) | Varias cotas por título, subpuntos `1320.2` |
| Bloques situación actual / plan | 1.033 (67 %) | `Current/Actual situation`, `Tool correction plan`/`Correction proposal`/`Pla de correcció` |
| Magnitud en mm | 771 (50 %) | Regex; **qué significa** (total, por lado, en radio) no sale por regex |
| Cavidades explícitas | 250 (16 %) | En el resto, `no_consta`; no asumir todas |

Nervios (47 %) y Planitudes (33 %) bajan porque muchas diapositivas son análisis sin plantilla.
También salen por reglas la fecha y la paginación de la cabecera (`31/10/2023 · 10/42`), el
nominal con tolerancia del título y las tablas de la diapositiva (p. ej. movimientos X/Y por
cavidad en el 3218, 13.9). Para generalizar las previsiones se propone localizar
columnas por etiqueta (§1.2): el 3212 tiene `Retoc` en O y el 3197 en T. El adaptador
productivo del piloto todavía usa correspondencias de filas y columnas concretas
en `pilot_3212/measurements.py`.

## 2. Interpretación propuesta con ayuda opcional de un LLM

### 2.1 Prueba a mano: 14 diapositivas al azar

El estudio del 21/10 registró una lectura manual de 14 diapositivas de siete
piezas, en inglés y catalán. No se ejecutó un LLM ni se midió su precisión:

| Campo | Sale del texto | Necesita la imagen |
|---|--:|--:|
| Tipo de acción («Increase plastic», «burn/erode», «new inserts», «venting», «Do not corrected… wait») | 12 | 2 (rebabas sin acción escrita; «segons detall») |
| Total o por lado («split for both sides», «each side… in total», «in radius») | 14; en 3 hay que interpretar | — |
| Cavidades | 2 explícitas; 12 no las nombran | — |
| Zona y sentido («red surface», «arrow direction») | 7 | **7** |

La muestra sugiere evaluar ayuda para clasificar texto libre multilingüe. Cotas y
magnitudes explícitas pueden obtenerse con reglas en las plantillas reconocidas;
esto no garantiza su interpretación. Para zonas y flechas, la propuesta es
conservar la diapositiva/recorte como evidencia y revisarla manualmente; la
alternativa con visión sigue sin validar.

### 2.2 Cómo usarlo sin perder fiabilidad

Este flujo todavía no está implementado:

1. **Lote, no chat.** Se propone ejecutarlo al importar, fuera del asistente. La
   idoneidad de `qwen3.5:2b` u otro modelo para extracción estructurada no se ha
   probado. Modelo, proveedor y lugar de ejecución siguen pendientes de decisión.
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
6. **Revisión humana en la web, pendiente de construir.** Todo quedaría `propuesto`
   hasta su aceptación, midiendo la tasa por campo y plantilla. El endpoint de
   revisión de globos existente no implementa este flujo de correcciones y la
   pantalla actual tampoco ofrece aquel formulario.
7. **Conjunto de referencia antes de elegir modelo.** Partir de los casos revisados del 3212
   (`pilot_3212`) y anotar 40–60 diapositivas de otras 4–5 piezas, con al menos una por plantilla
   de título. Escribir los resultados esperados **antes** de programar
   ([próximos pasos §1](proximos-pasos.md)).

### 2.3 Otras tareas de LLM (todas como propuesta para revisar)

- **Método de medida en DOCX/PDF/DOC:** cómo se mide cada cota, alineación, equipo.
- **Lecciones aprendidas y warnings:** resumir una cadena muestreo → corrección → muestreo y las
  semejanzas entre piezas (Bolt Eye pequeño en los primeros muestreos comparados del
  3212 y 3197; en 3197 el caso parte de intern.02, no demuestra el resultado de la
  primera prueba). Siempre con enlaces a las fuentes y sin atribuir causalidad
  solo por el orden temporal.
- **Feature ↔ cotas:** recuperar primero vínculos explícitos de métodos y planes;
  por ejemplo, el método del 3288 identifica DIM80 para el clip (I-106). Donde falte
  el vínculo, proponer candidatas mediante términos como «clip», «pocket», «rib»,
  «nervi» o «bolt» para confirmación humana.
- **Correos, presentaciones de análisis (8D informal), fotos y vídeos:** resumen opcional; el
  valor está en enlazarlos como evidencia, no en estructurarlos.

## 3. Lo que no está en los datos

Ni reglas ni LLM pueden decidir:

- qué versión de un plan se ejecutó (I-401);
- qué versión de un informe se entregó (I-603);
- qué significa el marcador `OK`;
- si los valores `RAND` se usaron en alguna entrega (I-003).

Se propone mostrar las versiones y pedir una selección explícita cuando su
vigencia sea relevante. `Uploaded to IQS` o una fecha reciente no acreditan por sí
solos entrega, aprobación ni ejecución. La app ya conserva versiones de mediciones
y selecciona una revisión por ordenación cuando no se pide otra; eso es una regla
de consulta, no una confirmación de vigencia. La política documental y de entregas
se consulta a INTEPLAST en [preguntas abiertas](preguntas-abiertas.md).

## 4. Orden propuesto

| Fase | Qué | Con qué se comprueba |
|---|---|---|
| 0 | Evaluar las reglas de §1.2, lector alternativo XLS, reconocimiento del formato real y marcas de revisión | Conjunto de referencia por plantilla, celdas/localizadores, fórmulas frente a cachés y discrepancias NOK revisadas; las cifras históricas sirven de comparación, no de criterio único |
| 1 | Lectores `#P#`, `HISTORY` e identidad desde ruta; identificación de series generadas y bloques iguales | Casos `#P#` frente a PPAP de cliente y `HISTORY` frente a cabecera; confirmar semántica y procedencia antes de clasificar |
| 2 | Correcciones de todas las piezas: título, cotas, magnitudes, fecha, tablas; previsiones por etiqueta; enlace con las mediciones de la misma pieza por cota | Conjunto de referencia por plantilla |
| 3 | LLM en lote para el significado de las acciones, con validación y revisión (§2.2) | Tasa de aceptación por campo |
| 4 | Lecciones, warnings y feature ↔ cotas propuestos por LLM | Revisión de INTEPLAST |
| — | Zonas en imagen y escaneos | Solo si una prueba con visión lo justifica |

Las fases 0–2 plantean reglas sin LLM para ampliar cobertura. Las 21 piezas con datos
son un ámbito de evaluación, no una cobertura garantizada: quedan formatos sin
identificadores, documentos visuales y ambigüedades que requieren revisión. El
estado y la prioridad de este trabajo se mantienen en la
[hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx).

## 5. Decisiones pendientes (Eduard)

- Modelo y lugar del LLM de extracción (local o Copilot) y si los datos del cliente pueden salir
  del servidor.
- Política para valores cuya generación esté demostrada, indicios aún sin confirmar
  y versiones de informe. La propuesta es conservar su procedencia y evitar
  presentar un valor generado como medición.
- Si las observaciones cualitativas entran como cotas. Antes hay que confirmar el
  significado del tercer campo de `#P#` y de las marcas OK/NOK visuales.

## Cómo repetir las mediciones

Estos comandos pertenecen a la biblioteca experimental: los dos primeros
regeneran tablas derivadas de `conocimiento`, no importan datos en la app. No se han
ejecutado en esta revisión documental. La preparación del entorno y la evidencia
vigente se mantienen en [conocimiento/README](../conocimiento/README.md).

```bash
PY=conocimiento/.venv/Scripts/python.exe
$PY conocimiento/herramientas/formulas_aleatorias.py   # celda_aleatoria
$PY conocimiento/herramientas/lector_dr.py             # lectura_dr (por hoja) y medida_dr (por valor)
$PY conocimiento/herramientas/consultar.py sql "SELECT papel, count(*), sum(valores) FROM lectura_dr GROUP BY papel"
```

La concordancia NOK está en `lectura_dr.nok`: `[no marcado y dentro, no marcado y fuera, marcado
y dentro, marcado y fuera]`.
