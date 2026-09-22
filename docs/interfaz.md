# Patrones de interfaz

Estas reglas se aplican a las nuevas pantallas y a los cambios de las existentes.
La referencia visual es el catálogo y el editor de Features. Antes de crear una composición
nueva, comprobar qué componente o patrón de la aplicación ya resuelve esa tarea.

## Búsqueda y filtros

- Usar `Common/SearchField`: campo a todo el ancho, lupa a la izquierda y limpieza
  a la derecha. Features, Metrología, cotas y el visor del plano comparten este componente.
- Colocar la búsqueda arriba, seguida de filtros horizontales que se apilan en móvil.
  No introducir listas laterales para escoger cotas.
- En el catálogo, reunir Pieza, Feature, Categoría y Tag bajo «Filtros», junto al buscador.
  Los cuatro desplegables usan `Common/SearchSelect` con etiqueta visible y búsqueda interna.
  Plegar los filtros conserva la selección; el botón cuenta los cuatro criterios activos.
  Mostrar etiquetas eliminables y «Limpiar filtros» solo cuando haya filtros aplicados.
  Limpiar filtros conserva el texto buscado y el tipo de resultado; limpiar la búsqueda
  solo borra el texto.
- El selector Feature filtra por identidad exacta, se combina con el texto buscado y
  se conserva en la URL. Pieza y Feature ofrecen las relaciones realmente vinculadas.
  El catálogo ofrece todas las piezas registradas, también las que aún no tienen features.
- Usar los controles `Select` de la aplicación. `Common/FilterSelect` añade una etiqueta
  visible para filtros de detalle como Elemento, Altura y Evaluación.
- Separar variables independientes. No concatenar B, H y GX/LP en un único desplegable.
  Ofrecer solo combinaciones que existan y ocultar controles sin alternativas.
- La identidad de N170 procede del ID de la serie calculado con el elemento CMM;
  no se deduce de cabeceras repetidas o incorrectas del CSV.
- La búsqueda numérica acepta prefijos: `N1` y `N11` deben ofrecer `N113`. Priorizar
  la coincidencia exacta. Al seleccionar una cota, su número queda en el buscador.

## Títulos de la ficha de feature

- Los títulos principales Warnings, Lessons Learned y Piezas ejemplo usan `text-lg`
  (18 px), frente a los 14 px de sus subtarjetas, tanto en consulta como en edición.

## COTAS dentro de una pieza del feature

- La tarjeta usa la misma fila compacta, borde y espaciado que Molde, CAD, Escaneo,
  Plano y Moldflow: icono de regla y etiqueta **COTAS** a la izquierda, números a su lado.
  No tiene cabecera separada, «Ver pieza», revisión ni relación visibles.
- Los recuadros de cotas y «Añadir cota» se colocan de izquierda a derecha; solo pasan
  a otra línea cuando no caben. La altura normal coincide con las filas de ficheros,
  tanto en consulta como en edición.
- Pulsar «Añadir cota» crea un campo vacío al final y lo enfoca, sin formulario aparte
  ni diálogo. Intro, salir del campo o Guardar el feature guardan el número. Una pausa
  mientras se escribe no debe guardar un prefijo incompleto como una cota nueva.
- Si hay mediciones importadas, ese recuadro usa `Common/SearchSelect` compacto para
  elegir una cota existente. Las opciones incluyen la revisión para distinguir números
  iguales; «Escribir otra cota» conserva el campo manual. No asignar todas las cotas
  importadas al feature. Los recuadros guardados mantienen su presentación compacta.
- La fila COTAS no incluye importación. Las mediciones se preparan al registrar la pieza
  con Nueva pieza y mediante «Actualizar datos». Aquí se eligen las cotas del feature.
- Nueva pieza y Actualizar datos mantienen dimensiones constantes durante todos sus
  estados, con contenido desplazable y carga/error en un hueco fijo del pie. Crear (o
  Actualizar) va inmediatamente a la izquierda de Cancelar. Cancelar descarta el formulario.
- No mostrar instrucciones de relleno, «Elegir otra carpeta», «Archivos guardados»,
  resultados de importación ni formularios de revisión por archivo. La lectura es automática
  y las sustituciones conservan historial. Abrir Actualizar datos no modifica la pieza:
  el procesamiento empieza con Actualizar en el pie.
- Reutilizar `Input`, el botón con Plus, la papelera, `useAutosave` y `SaveStatus` del
  editor de ficheros. Los borradores fallidos se conservan y participan en Guardar.
- Las cotas guardadas abren sus mediciones; el icono de plano contiguo abre esa cota
  directamente en el dibujo. En edición se pueden retirar con la papelera.
- Ocultar metadatos no los borra: conservar revisión y relación de los vínculos existentes.

## Catálogo compartido y ficha de pieza (22/09/2026)

- El menú **Catálogo** abre `/features`: tarjetas de piezas y features con la misma
  composición y tamaño de portada. Etiqueta y borde de color distinguen los tipos.
- La vista inicial solo muestra piezas y features. Las cotas aparecen al buscar,
  identificadas por pieza y revisión; abren esa consulta dentro de la ficha de pieza.
- Cabecera en tres filas: título y acciones; Todo/Piezas/Features con subrayado activo;
  buscador y Filtros. Nuevo feature usa borde y precede a Nueva pieza, en verde sólido.
  Los controles principales tienen 44 px de altura y reutilizan el estilo de Features.
- `/parts` redirige al catálogo filtrado por piezas. `/parts/{id}` conserva los enlaces
  de cotas y plano y ahora muestra portada, identidad, Features, Cotas y Archivos.
- La portada de pieza es una captura de todo el CAD STEP sin superficies marcadas.
  Al pulsarla abre el visor interactivo reutilizado de Features, sin edición de caras.
- Editar permite cambiar nombre/código y añadir o desvincular features existentes.
  La relación es la misma en ambas direcciones. Guardar/Cancelar afectan a la cabecera;
  los vínculos se guardan en línea, como en el editor de Features.
- Cotas integra la consulta anterior de Metrología. La pieza la fija la ficha; Feature
  y Más filtros siguen disponibles. No elegir una cota automáticamente.
- Los selectores usan `Common/SearchSelect`, compartido con los filtros de Features:
  misma altura y borde, búsqueda interna, teclado, limpieza y opciones con desplazamiento.
- En la consulta de cotas, Categoría y Tag están en Más filtros. Son atributos de features: deben coincidir en
  el mismo feature y limitar a sus cotas vinculadas. No atribuir a esos filtros todas
  las cotas de una pieza. Las opciones se ajustan a las combinaciones disponibles.
- Sin filtros de feature/categoría/tag, están disponibles todas las cotas de la pieza,
  incluidas las que no tienen feature. Las cotas disponibles son botones compactos.
- «Mostrar más cotas» es un botón con aspecto de enlace gris subrayado, sin negrita.
  Excluir los diagnósticos «Coordenadas» de las opciones y sugerencias de cotas.
- Cambiar pieza limpia cota, revisión, evaluación, cavidades, tramo y plano. El contexto
  anterior se recupera con Atrás. Cambiar filtros limpia la cota y mantiene la pieza.
- Un feature presente sin cotas vinculadas muestra ese estado. No atribuirle todas las
  cotas de la pieza. Las vinculadas sin mediciones siguen siendo seleccionables.
- Conservar pieza, feature, cota y revisión en los enlaces desde Features y al navegar
  por mediciones, correcciones y plano. El plano conserva el ámbito y sus subcotas.
  Una revisión vinculada diferente de la importada no puede mostrar sus mediciones.

## Página de cotas

La sección Cotas de la ficha de pieza contiene la consulta de metrología, sin pestañas
Documentos/Mediciones/Correcciones ni listados de archivos de mediciones.

Orden estable dentro de Cotas: buscador con Plano a su derecha, selector de feature,
Correcciones debajo a la izquierda, filtros de evaluación y gráfica. `Common/SearchToolbar` alinea el buscador y `Parts/DrawingToggle`
en una fila, también en móvil; el botón tiene la misma altura que el campo.
No repetir debajo del buscador el número o el título de la cota seleccionada, ni añadir
el subtítulo «Cotas y mediciones · revisión…» bajo el nombre de pieza.
Al abrir Correcciones se mantiene esta misma estructura y selección, con **todos los
muestreos** en la gráfica. Nunca recortar el historial al antes/después de un solo plan.
Los tramos se seleccionan **dentro de la gráfica**, pulsando la región entre dos muestreos.
La región seleccionada se rellena en gris; la tarjeta se actualiza sin mover la gráfica.
No añadir una fila de botones debajo para cambiar de tramo. Las regiones admiten ratón,
toque y teclado; consultar un punto no cambia el tramo. El detalle muestra la
propuesta del molde, el efecto previsto y el cambio medido para la cavidad seleccionada;
no muestra fotografías/capturas ni «Documentos y valores de origen».

Ofrecer todas las acciones ya vinculadas a la cota y a cada plan, también las que no tienen
una previsión cuantitativa validada. Distinguir «sin acción vinculada» de «sin actuación
documentada». Una diferencia entre mediciones nunca basta para inventar una intervención.
Mantener separadas la base del XLS para la previsión y las mediciones CSV para el cambio real.

El alta de piezas parte de **Catálogo → Nueva pieza**. Se selecciona una carpeta con
el diálogo de Windows y se proponen su nombre, CAD, escaneo, molde y plano. Las propuestas
son editables antes de registrar la pieza. Crear procesa automáticamente los CSV/XLS/XLSX
compatibles sin formularios de revisión por archivo.
**Actualizar datos** inicia otra lectura únicamente al pulsarlo. Se conservan el historial
y las revisiones. No hay vigilancia automática. La cabecera mantiene el título, con los
botones a la derecha.
«Añadir pieza» en Features busca exclusivamente en el catálogo registrado. Al vincular
una pieza incorpora sus archivos de referencia como punto de partida, respetando los
ficheros que el feature ya tenga. Las cotas se asignan explícitamente. Etiquetas: CAD y Escaneo.

El plano es una referencia para localizar y comprobar la cota. El botón sigue disponible
para cotas sin mediciones cuando existe un plano vinculado. No sustituir un plano ausente
por un informe PDF cualquiera.

## Consulta del plano

Plano abre una **página de archivo propia**, igual que los planos de Features:
`/parts/{id}/fichero/{fileId}`. Esto se aplica tanto al archivo de la pieza como al botón
Plano de Cotas. La página muestra el nombre del PDF y reutiliza `DrawingSearch` y `PdfViewer`.
No incrustar el plano en la sección Cotas de la ficha. Atrás recupera la ficha y sus filtros.
Los enlaces antiguos con `plano=true` redirigen al archivo concreto.

El buscador ocupa todo el ancho disponible. Las coincidencias aparecen debajo como botones en una
franja que se adapta al ancho disponible, con un contador de resultados. Seleccionar
una enfoca su ubicación. Conservar las subcotas entre los resultados, sin casilla para
activarlas. Si el mismo número aparece en varias ubicaciones, distinguirlas con `1/2`, `2/2`.

No añadir columna lateral, descarga del original, filtro «Sin lectura», metadatos de revisión
ni formulario «Número de esta ubicación / Guardar revisión» en esta consulta. Las revisiones
ya guardadas siguen siendo utilizadas al buscar.

## Gráficas y detalle

- Mostrar información solo sobre un punto, al pasar el cursor, tocarlo o enfocarlo con
  el teclado. Las zonas vacías y los segmentos de línea no activan información.
- Colocar el recuadro junto al punto y ajustarlo a los bordes. Contiene solo el muestreo,
  cavidad y valor con unidad. Si varios puntos se solapan, mostrar esas cavidades juntas;
  no añadir otras alejadas aunque pertenezcan al mismo muestreo.
- La leyenda permite activar cavidades. No incluir el texto «Banda de tolerancia» ni
  instrucciones como «Pasa el cursor…». No añadir estado, límites o enlaces al recuadro.
- No duplicar los valores en tablas permanentes bajo la gráfica.
- Conservar los huecos si faltan mediciones. Una ausencia no es cero.
- Distinguir una previsión de una medición real. Una propuesta del PPTX no demuestra
  ejecución, mejora ni cierre de una corrección.
- No mostrar por defecto catálogos de descargas, nubes PUNTS, perfiles A/B, listados
  de acciones ni detalles del importador. Las fuentes son contextuales a la consulta.

## Navegación y estado

- No añadir botones o enlaces de retorno como «← Piezas» o «Volver a…».
  Atrás y Adelante corresponden al navegador. Los títulos pueden mostrar contexto.
- Conservar pieza, búsqueda, feature, categoría, tag, cota, revisión, elemento, altura, evaluación, cavidades visibles, tramo, acción
  y cavidad del detalle en la URL. Cambiar de evaluación conserva el tramo seleccionado.
- La página del plano usa `drawingQ` sin sobrescribir la consulta de cotas.
  Los enlaces desde una cota conservan además `drawingFile`, el PDF concreto vinculado
  en Features; no cambiarlo por otro documento según su nombre.
  Atrás vuelve a la entrada anterior; la búsqueda del PDF reemplaza únicamente el estado
  de su propia página. Recargar conserva el documento y la búsqueda.
- Escribir o ajustar evaluaciones reemplaza la entrada actual. Cambiar pieza o filtros de
  feature/categoría/tag, seleccionar otra cota o abrir
  correcciones/plano añade una entrada: Atrás restaura la consulta anterior completa.
- Mantener los enlaces antiguos de cotas/correcciones interpretando sus parámetros,
  sin recuperar las pestañas eliminadas.

## Comprobación

Revisar escritorio y móvil, teclado, ausencia de desplazamiento horizontal, consulta
de valores, combinaciones de filtros e historial del navegador. Los cambios compartidos
deben comprobarse también en Features para evitar divergencias entre pantallas.
