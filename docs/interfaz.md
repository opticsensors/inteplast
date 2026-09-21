# Patrones de interfaz

Estas reglas se aplican a las nuevas pantallas y a los cambios de las existentes.
La referencia visual es el catálogo de Features. Antes de crear una composición
nueva, comprobar qué componente o patrón de la aplicación ya resuelve esa tarea.

## Búsqueda y filtros

- Usar `Common/SearchField`: campo a todo el ancho, lupa a la izquierda y limpieza
  a la derecha. Features, Metrología, cotas y el visor del plano comparten este componente.
- Colocar la búsqueda arriba, seguida de filtros horizontales que se apilan en móvil.
  No introducir listas laterales para escoger cotas.
- En Features, dejar Pieza y Feature visibles y agrupar Categoría y Tag bajo «Más filtros», con
  contador de filtros activos. Los cuatro desplegables usan `Common/SearchSelect` con
  búsqueda interna, igual que Metrología. Plegar los filtros conserva la selección.
- El selector Feature filtra por identidad exacta, se combina con el texto buscado y
  se conserva en la URL. Pieza y Feature ofrecen las relaciones realmente vinculadas.
  Ambos tabs muestran solo piezas usadas por algún feature; el catálogo completo de
  piezas se ofrece al añadirlas en edición. No precargar piezas sin vínculos en consulta.
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
- Reutilizar `Input`, el botón con Plus, la papelera, `useAutosave` y `SaveStatus` del
  editor de ficheros. Los borradores fallidos se conservan y participan en Guardar.
- Las cotas guardadas abren sus mediciones; el icono de plano contiguo abre esa cota
  directamente en el dibujo. En edición se pueden retirar con la papelera.
- Ocultar metadatos no los borra: conservar revisión y relación de los vínculos existentes.

## Metrología: una sola consulta

- El menú se llama **Metrología** y conserva `/parts` para mantener enlaces existentes.
  Features sigue siendo la entrada al conocimiento de diseño.
- La cabecera siempre es Metrología. Un buscador de cotas con Plano a su derecha y,
  debajo, Pieza, Feature y Más filtros. No interponer un catálogo de tarjetas de piezas.
- Pieza selecciona una sola pieza y busca por código/nombre dentro del desplegable.
  Hasta seleccionarla, el buscador de cotas y Plano permanecen desactivados.
- Feature es opcional y permite empezar por un feature antes de seleccionar pieza.
  En ese caso, Pieza ofrece solo las que lo contienen. Con pieza seleccionada, Feature
  ofrece sus features. No elegir una pieza ni una cota automáticamente.
- Los selectores usan `Common/SearchSelect`, compartido con los filtros de Features:
  misma altura y borde, búsqueda interna, teclado, limpieza y opciones con desplazamiento.
- Categoría y Tag están en Más filtros. Son atributos de features: deben coincidir en
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

Metrología es la entrada a las cotas de una pieza. Su ficha abre directamente la consulta,
sin pestañas Documentos/Mediciones/Correcciones ni listados de originales.

Orden estable: Metrología, buscador con Plano a su derecha, selectores de pieza/feature,
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

La importación pertenece a **Admin → Datos de piezas**. No añadir «Actualizar datos» ni
acciones de importación a la consulta. Se inicia únicamente mediante una acción explícita.

El plano es una referencia para localizar y comprobar la cota. El botón sigue disponible
para cotas sin mediciones cuando existe un plano vinculado. No sustituir un plano ausente
por un informe PDF cualquiera.

## Consulta del plano

Plano alterna la vista bajo la **misma cabecera, búsqueda y selectores de pieza/feature**, con el
botón a la derecha seleccionado mientras se consulta el dibujo. Pulsarlo de nuevo recupera
las cotas/correcciones y sus filtros. No abrir otra pestaña del navegador ni sustituir el
título de Metrología por el nombre del PDF. Los enlaces directos anteriores siguen funcionando.

El buscador ocupa el ancho disponible junto al botón Plano. Las coincidencias aparecen debajo como botones en una
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
- La vista del plano usa `plano=true` y `drawingQ` sin sobrescribir la consulta de cotas.
  Los enlaces desde una cota conservan además `drawingFile`, el PDF concreto vinculado
  en Features; no cambiarlo por otro documento según su nombre.
  Cerrar con Plano vuelve a la entrada anterior si se abrió desde la consulta; un enlace
  directo o recargado desactiva el modo conservando los filtros guardados en la URL.
- Escribir o ajustar evaluaciones reemplaza la entrada actual. Cambiar pieza o filtros de
  feature/categoría/tag, seleccionar otra cota o abrir
  correcciones/plano añade una entrada: Atrás restaura la consulta anterior completa.
- Mantener los enlaces antiguos de cotas/correcciones interpretando sus parámetros,
  sin recuperar las pestañas eliminadas.

## Comprobación

Revisar escritorio y móvil, teclado, ausencia de desplazamiento horizontal, consulta
de valores, combinaciones de filtros e historial del navegador. Los cambios compartidos
deben comprobarse también en Features para evitar divergencias entre pantallas.
