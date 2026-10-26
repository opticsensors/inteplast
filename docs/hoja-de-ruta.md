# Hoja de ruta del proyecto INTEPLAST

Alcance aclarado por Eduard el **22/09/2026**. El proyecto tiene tres etapas:
transferir conocimiento entre trabajadores, reutilizarlo al diseñar en SolidWorks y
predecir contracciones a partir de los resultados disponibles.

La **etapa 1 está en desarrollo**, con el 3212 Pump Housing como piloto. Las etapas 2 y 3
son objetivos futuros; su implementación, calendario y criterios de aceptación están por
concretar. Esta numeración describe la visión del proyecto y no establece equivalencias
con las tareas o fases contractuales citadas en notas anteriores.

## 1. Transferencia y consulta del conocimiento mediante una GUI

**Objetivo:** conseguir que el conocimiento de la empresa se transfiera de forma eficiente
entre trabajadores y se pueda consultar fácilmente, conservando el contexto de cada caso.

La interfaz gráfica permite buscar un feature y consultar sus advertencias de diseño,
lecciones aprendidas, piezas y moldes de referencia, documentos, cotas, mediciones y
correcciones. La información histórica ayuda a entender qué ocurrió y qué decisiones se
tomaron, para aprovechar esa experiencia en nuevos diseños.

**Ejemplo de uso:** un trabajador que va a diseñar un Bolt Eye consulta qué debe vigilar,
qué problemas aparecieron en piezas anteriores y qué actuaciones se documentaron.

**Estado:** es el trabajo actual. El alcance implementado y sus límites se mantienen en
[Aplicación web](app-web.md) y [Cotas y evidencia](cotas-y-evidencia-web.md). La validación
del conocimiento con INTEPLAST forma parte de esta etapa.

### Pendiente: generalizar la importación de correcciones PPTX

**Estado (26/10/2026): ejemplos recibidos; falta validar los resultados esperados.**
La entrega ampliada ya está inventariada en la biblioteca de conocimiento. No hace falta
volver a esperar otra entrega para estudiar formatos; hace falta seleccionar casos de
otras piezas y acordar qué debe producir su importación. El análisis y la propuesta están
en [ingesta automática](ingesta-automatica.md); no describen un lector general ya desplegado.

Qué funciona ya con otras piezas y qué no:

| Parte | Otras piezas | Código |
|---|---|---|
| Mediciones: CSV CMM por bloques y tablas `DR` de informes PPAP XLS/XLSX | ✅ Lectura genérica al crear la pieza y con **Actualizar datos** | `automatic_measurements.py`, `ingestion/measurement_csv.py`, `ingestion/measurement_tables.py` |
| Correcciones: diapositivas PPTX, previsiones `DR(100%)` de los XLS de retoques y sus correspondencias con cotas | ❌ Solo 3212. En otras piezas se detectan los documentos, que no se interpretan, y la lectura termina «con incidencias» | `ingestion/pilot_3212/` (planes, casos y asociaciones revisadas en `config.py`), `part_setup.refresh` |

El adaptador piloto se selecciona con `app/pilot.py`: código `3212` y carpeta llamada
`3212 Pump Housing`, cualquiera que sea su ruta desde la raíz. La revisión `06` está fijada en
`evidence.publish_study`. En el frontend, las reglas de N161, N240, N165 y N170 de
`describeSeries` (`Parts/measurementSelection.ts`) solo se aplican a series del piloto; las
series de informes XLS de otras piezas conservan sus columnas originales.

El importador de correcciones usa reglas de texto y correspondencias revisadas para el 3212.
No usa una LLM para interpretar las diapositivas ni está validado con otras estructuras.

**Antes de programar hace falta:**

1. **Seleccionar casos de la entrega disponible:** PPTX y XLS de retoques de otra pieza,
   junto con las mediciones de antes y después; identificar variantes y revisiones.
2. **Resultados esperados contrastados:** qué acción corresponde a qué cota y muestreo, qué
   previsión debe leerse de cada celda y qué diapositivas son decisiones de no actuar.
   Idealmente, revisados con quien prepara esos documentos (preguntas A13 y A14 en
   [preguntas abiertas](preguntas-abiertas.md)).
3. **Con esos ejemplos, elegir el método:** ampliar los adaptadores, interpretar con una LLM
   con capacidad visual, o combinar ambos. La elección todavía no está tomada.

La solución deberá conservar la procedencia de cada dato, señalar las asociaciones ambiguas
y validar las extracciones contra esos resultados esperados antes de dar por resuelta la
generalización.

También falta llevar al importador productivo las protecciones verificadas en las
herramientas de conocimiento: comprobar fórmulas y procedencia antes de tratar números
como medidas, reconocer archivos por su firma y admitir las variantes PPAP detectadas.
La lectura genérica actual de CSV/XLS/XLSX no equivale a cobertura completa de `Exemples`.
El contrato implementado se mantiene en [Cotas y evidencia](cotas-y-evidencia-web.md).

## 2. Features reutilizables y adaptables dentro de SolidWorks

**Objetivo:** que el diseñador pueda reutilizar features en SolidWorks y modificarlos
para una nueva pieza, evitando tener que modelarlos de nuevo desde cero.

La experiencia prevista incluye:

- Extraer un feature de un diseño existente o crear uno para incorporarlo al conjunto
  de features reutilizables.
- Seleccionarlo e insertarlo o arrastrarlo sobre otra pieza desde SolidWorks.
- Modificar sus parámetros y referencias para ajustarlo a la geometría de destino.
- Incorporar reglas que permitan adaptar automáticamente el feature al resto de la
  geometría cuando sea viable, aplicando el conocimiento de diseño de la primera etapa.

**Ejemplo de uso:** insertar un Bolt Eye ya definido, ajustar sus dimensiones, posición y
referencias a la nueva pieza y comprobar los requisitos aplicables. El resultado buscado
es una geometría reutilizable y editable que cumpla esos requisitos en su nuevo contexto.

**Estado:** etapa futura. Falta definir qué features se reutilizarán primero, cómo se
extraerán o crearán, qué podrá editar el usuario y qué adaptación será automática. También
deben concretarse las reglas y la comprobación del resultado; la adaptación automática
es un objetivo, no una capacidad ya validada.

El STEP de pieza del 3212 analizado contiene geometría sin el árbol de operaciones ni sus
parámetros originales. Para preparar features editables habrá que concretar qué modelos
nativos están disponibles y qué información debe reconstruirse. Ver
[análisis del CAD de pieza](../conocimiento/0-bolt-eye/3212/1-pieza-2d-3d.md).

## 3. Predicción de contracciones a partir de resultados

**Objetivo:** predecir las contracciones de las piezas de inyección basándose en los
resultados históricos, para anticipar su comportamiento dimensional al diseñar.

La base de conocimiento y los resultados recopilados en la primera etapa servirán como
punto de partida. Habrá que relacionar la geometría de referencia y sus revisiones con
las mediciones de las piezas obtenidas y el contexto disponible de cada caso.

**Estado:** etapa futura. Falta concretar qué magnitud se quiere predecir, qué datos son
necesarios y suficientes, qué método se utilizará y cómo se validará con resultados
reales. El alcance del material o materiales también queda por definir.

Las previsiones de los XLS de retoques que ya se consultan en el piloto se conservarán
con su significado original: son previsiones documentadas de efectos de correcciones.
El modelo predictivo de contracciones de esta etapa todavía está por desarrollar.

La decisión anterior de dejar los parámetros de máquina fuera de la base de consulta de
diseño se recoge en [Otros proyectos](../conocimiento/0-bolt-eye/otros-proyectos.md). Al definir la etapa predictiva
habrá que revisar qué variables necesita, sin dar por ampliada la recogida de datos actual.

## Relación entre las etapas

La primera etapa organiza y hace accesible la experiencia de INTEPLAST. La segunda aplica
ese conocimiento a la creación y adaptación de geometría reutilizable en SolidWorks. La
tercera utiliza los resultados acumulados para desarrollar y validar predicciones.

Las reglas de adaptación geométrica de la etapa 2 y la predicción de contracciones de la
etapa 3 son capacidades distintas; su posible integración se concretará posteriormente.

## Antecedentes documentales

La revisión del 22/09/2026 encontró la etapa 1 descrita en el repositorio. Las notas
originales del vault `C:\edu\projects\Inteplast` contienen antecedentes parciales:

- `inteplast_notas_reunion_20_2_2026.md`: consulta de warnings, lecciones y piezas ejemplo.
- `inteplast_datos_cad.md`: propuestas de macros SolidWorks para extraer geometría y
  comprobar reglas.
- `inteplast_database.md` e `inteplast_PADIH_fase_B.md`: propuestas de conexión CAD y
  futuras funciones de IA.

Esas notas no recogían explícitamente las tres etapas con el alcance indicado aquí.
Este documento incorpora la aclaración de Eduard, manteniendo las notas como antecedentes.
