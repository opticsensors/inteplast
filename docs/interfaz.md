# Patrones de interfaz

Estas reglas se aplican a las nuevas pantallas y a los cambios de las existentes.
La referencia visual es el catálogo y el editor de Features. Antes de crear una composición
nueva, comprobar qué componente o patrón de la aplicación ya resuelve esa tarea.

**Revisión documental: 26/10/2026.** Los patrones descritos se han contrastado con el código;
las comprobaciones de interfaz que deben ejecutarse se indican al final. Esta revisión no
incluye una nueva ejecución de pruebas ni una sesión de navegador.

Esta ficha concentra composición, interacción y navegación. El contrato de archivos está en
[ficheros externos](ficheros-externos.md), la selección de superficies en
[portadas CAD](portadas-cad.md) y la conversión de modelos grandes en [vistas 3D](vistas-3d.md).

## Búsqueda y filtros

- Usar `Common/SearchField`: campo a todo el ancho, lupa a la izquierda y limpieza
  a la derecha. Features, Metrología, cotas y el visor del plano comparten este componente.
- Colocar la búsqueda arriba, seguida de filtros horizontales que se apilan en móvil.
  No introducir listas laterales para escoger cotas.
- En el catálogo, reunir Pieza, Feature, Familia y Cliente bajo «Filtros», junto al buscador
  (Categoría y Tag se retiraron el 17/11/2026; sus parámetros en enlaces antiguos se ignoran).
  Los cuatro desplegables usan `Common/SearchSelect` con etiqueta visible y búsqueda interna.
  Una pieza cumple si cumple a la vez pieza, familia y cliente; un feature, si tiene al menos
  una pieza que los cumpla todos. El servidor aplica ese criterio.
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

## Ficha de feature: consulta y edición

- Consulta y edición comparten cabecera con portada a la izquierda y datos a la derecha.
  La ruta Catálogo / Features / nombre queda arriba, junto a Editar feature y el menú
  de acciones, o Cancelar / Guardar cambios. Eliminar permanece en el menú y pide confirmación.
- En escritorio, Advertencias y Lecciones aprendidas ocupan la columna izquierda;
  Piezas ejemplo, la derecha. En móvil se apilan. Los tres paneles muestran contadores
  y títulos `text-lg`, con el mismo fondo y estilo sobrio en ambas clases de notas.
- Los puntos empiezan cerrados, con chevrón a la izquierda y separadores en consulta.
  Al abrirlos aparecen texto e imágenes. En edición se conservan los controles de
  reordenar, título, eliminar y añadir, con el editor de texto e imágenes debajo.
  Plegar una nota conserva su borrador y cualquier subida pendiente.
- Nombre y descripción tienen etiquetas visibles. Los features ya no tienen categoría ni
  tags (17/11/2026). Cambiar imagen reutiliza el editor existente de portada, incluida la
  selección de superficies CAD.
- **Portada por pieza (19/11/2026):** la cabecera muestra una captura por pieza en carrusel,
  sin nada debajo. Con una pieza solo lleva su código; con varias, también `n / N` (texto, sin
  lista) y flechas `size-8 rounded-md border bg-background/95 shadow-sm` que aparecen al pasar
  el ratón o enfocar y siempre en táctil. En edición es el mismo carrusel con el lápiz, que
  edita la pieza visible. Detalle en [portadas CAD](portadas-cad.md#una-portada-por-pieza-19112026).
- **Añadir pieza** permite marcar varias piezas en su desplegable con buscador y añadirlas
  juntas con «Añadir N piezas»; marcar no cierra el menú.
- La ficha de feature muestra las piezas donde aparece y las cotas de cada una dentro
  de una misma subtarjeta con borde, tanto en consulta como en edición. «Ver pieza»
  abre su ficha, donde se consulta la documentación. No repetir documentos ni controles
  para añadir archivos en la ficha del feature.

## COTAS dentro de una pieza del feature

- Las cotas aparecen bajo «Cotas» dentro de la subtarjeta de su pieza.
  Se mantiene el icono de regla y los botones compactos, sin revisión ni relación visibles.
- Los recuadros de cotas y «Añadir cota» se colocan de izquierda a derecha; solo pasan
  a otra línea cuando no caben, tanto en consulta como en edición.
- Pulsar «Añadir cota» crea un campo vacío al final y lo enfoca, sin formulario aparte
  ni diálogo. Intro, salir del campo o Guardar el feature guardan el número. Una pausa
  mientras se escribe no debe guardar un prefijo incompleto como una cota nueva.
- Si hay mediciones importadas, ese recuadro usa `Common/SearchSelect` compacto para
  elegir una cota existente. Las opciones incluyen la revisión para distinguir números
  iguales; «Escribir otra cota» conserva el campo manual. No asignar todas las cotas
  importadas al feature. Los recuadros guardados mantienen su presentación compacta.
- La fila COTAS no incluye importación. Las mediciones se preparan al registrar la pieza
  con Nueva pieza y mediante «Actualizar datos». Aquí se eligen las cotas del feature.
- Nueva pieza abre `/parts/nueva`, con la misma estructura que Editar pieza y los campos
  etiquetados como en Features. Cancelar descarta el borrador sin registrar la pieza.
  Al elegir la carpeta, si una carpeta superior se llama exactamente como un feature del
  catálogo (sin su prefijo de orden: «0- Bolt Eye» → «Bolt Eye»), ese feature aparece ya
  en Features como propuesta, con su papelera para quitarlo. Se guarda exactamente la
  selección al crear; elegir otra carpeta cambia solo las propuestas, no lo elegido a mano
  (un feature añadido a mano sigue aunque una carpeta lo sugiera y otra no).
- Actualizar datos es un icono en la esquina superior derecha del título Cotas; su ayuda
  al pasar el ratón explica la lectura. No tiene panel vacío. El progreso aparece solo
  durante la lectura. El resultado, las incidencias y los archivos usados se conservan
  en el registro del servidor (`Part.last_read`, API `GET /parts/{id}/read-data`), sin
  panel ni resumen en la ficha. Decisión de Eduard del 16/11/2026. Un error de la
  petición permite reintentar; ocultar el diagnóstico no convierte una lectura parcial en completa.
- Reutilizar `Input`, el botón con Plus, la papelera, `useAutosave` y `SaveStatus` del
  editor de cotas. Los borradores fallidos se conservan y participan en Guardar.
- Las cotas guardadas abren sus mediciones; el icono de plano contiguo abre esa cota
  directamente en el dibujo. En edición se pueden retirar con la papelera.
- Ocultar metadatos no los borra: conservar revisión y relación de los vínculos existentes.

## Catálogo compartido y ficha de pieza (22/09/2026)

- El menú **Catálogo** abre `/features`: tarjetas de piezas y features con la misma
  composición y tamaño de portada. Etiqueta y borde de color distinguen los tipos.
- Las tarjetas de lista y cuadrícula se pueden abrir en cuanto llega el catálogo.
  Al acercarse a la pantalla, cada portada CAD se comprueba por separado. Una pieza
  y los features que usan su misma captura comparten la consulta.
- **Medidas (18/11/2026):** tarjeta y celda de pieza llevan una etiqueta con lo que la app
  ha leído: «Medidas detectadas» (algún valor válido con cota y fuente, aunque la lectura
  siga en curso), «Informe pendiente de interpretar» (lectura terminada con un informe de
  medidas que no se pudo leer) o «Sin medidas detectadas» (lectura terminada sin informes).
  Sin etiqueta mientras la pieza no se ha leído o la lectura sigue sin valores.
  «Documentación de retoques» se añade cuando la lectura encontró documentos de
  correcciones; solo indica disponibilidad (no que se haya entendido o ejecutado un retoque).
- La vista inicial solo muestra piezas y features. Las cotas aparecen al buscar,
  identificadas por pieza y revisión; abren esa consulta dentro de la ficha de pieza.
- **Vistas (17/11/2026):** junto al buscador, antes de Filtros, el grupo «Vista» con Lista y
  Cuadrícula (`Catalog/CatalogView.tsx`), para Todo, Piezas y Features. La cuadrícula
  (`Catalog/CatalogTiles.tsx`) tiene una columna en móvil y más según el ancho; cada celda
  lleva la portada grande y debajo el código y el nombre, y en piezas la familia y el cliente;
  en features, el nombre. La portada de un feature es la de su primera pieza; con dos piezas
  o más, en lista y cuadrícula, lleva dos capas detrás y el número de piezas (19/11/2026), sin
  navegación: se navega en la ficha. El borde superior de color distingue el tipo. La vista elegida se
  guarda en este navegador (`inteplast.catalog-view`); si no se puede leer o guardar, se abre
  en Lista sin error. Las cotas encontradas siguen arriba en ambas vistas.
- **Grafo (17–18/11/2026):** tercer botón de «Vista» (`Catalog/CatalogGraph.tsx`, cargado
  solo al abrirlo). Al entrar desde Piezas o Features, abre «Todo» y muestra los dos tipos
  con sus conexiones. Conserva la búsqueda y los filtros de pieza, feature, familia y cliente.
  Las pestañas Piezas y Features permiten volver a su lista. Consulta el catálogo
  (`GET /catalog/graph`), todo de una vez, hasta 500 nodos; si hay más dice «Mostrando N de
  M: filtra para ver el resto». Librería `force-graph@1.43.5`, la del visor, fijada en
  `package.json`. Piezas: círculo con la captura CAD guardada o, sin ella, con el código
  dentro. Features: píldora con su nombre en el color principal. Familias (ámbar) y
  clientes (rosa) se añaden con dos casillas, apagadas al empezar, en una leyenda superpuesta arriba a la izquierda del grafo (una por línea, con su color). Sin texto de ayuda encima del grafo. Fondo, texto y uniones
  salen del tema y se repintan al cambiarlo. Arrastrar, zoom (máximo ×4), nombre al pasar el
  ratón (el nombre se escapa: la etiqueta emergente de `force-graph` es HTML); clic en
  pieza o feature abre su ficha y en familia o cliente filtra el catálogo. Las cotas
  encontradas siguen encima del grafo con «Mostrar más cotas (N de M)»; lista y cuadrícula
  conservan su «Mostrar más» de piezas y features.
  No se recorre con teclado: Lista y Cuadrícula son las vistas accesibles. El lienzo va
  fuera del flujo (`absolute inset-0`) para no ensanchar la página.
- **Planos (18/11/2026):** cuarto tipo junto a Todo, Piezas y Features
  (`Catalog/CatalogDrawings.tsx`), siempre en cuadrícula y sin selector de vista. Muestra
  **todos** los planos de las piezas (no solo el principal) con los filtros de pieza,
  feature, familia y cliente. Cada celda: miniatura de la primera página, nombre del archivo,
  código de la pieza y, si están asignados en «Organizar por componentes», componente y
  revisión. Mientras el servidor dibuja la miniatura aparece un marcador y se reintenta; si
  no se puede cargar, el icono de plano. «Globos verificados con .icp» aparece cuando un
  `.icp` del plano pasa la comprobación estricta (ajuste 1:1 y aros detectados de forma
  independiente, con asociación del mismo proyecto por el lector en un PDF de una página).
  Para los demás planos se consulta el índice de búsqueda. La tarjeta muestra «Marcas del
  archivo .icp» si el lector ha situado sellos del proyecto, «Globos detectados» si encuentra
  una serie de aros con números legibles o «Numeración detectada» si reconoce marcas No./N°.
  Si solo encuentra aros dudosos muestra «Marcas sin identificar». «Sin marcas detectadas»
  requiere una lectura completa. Al abrir Planos se comprueban las versiones y se prepara
  cualquier índice pendiente. Mientras tanto aparece «Leyendo plano…». Si falla la lectura,
  aparece «Lectura no disponible». Al pulsar se abre el plano en su pieza
  (`/parts/{id}/fichero/{fileId}`, el visor de planos actual).
  La miniatura y el visor muestran cada hoja en la orientación de lectura detectada.
  Las hojas diseñadas en vertical pueden seguir en vertical. Al buscar una cota, la marca
  gira con la hoja.
- Cabecera en tres filas: título y acciones; Todo/Piezas/Features con subrayado activo;
  buscador y Filtros. Nuevo feature usa borde y precede a Nueva pieza, en verde sólido.
  Los controles principales tienen 44 px de altura y reutilizan el estilo de Features.
- `/parts` redirige al catálogo filtrado por piezas. `/parts/{id}` conserva los enlaces
  de cotas y plano y ahora muestra portada, identidad, Features, Cotas y Archivos.
- La ficha de pieza comparte cabecera, navegación y secciones con la del feature.
  Como en el feature, junto a Editar pieza hay un menú **⋯** con Eliminar, solo para
  administradores. El diálogo muestra qué se elimina y qué se conserva, y pide escribir
  el código de la pieza antes de activar «Eliminar pieza».
  Cotas y gráficas van a la izquierda; Features y, debajo, Archivos a la derecha.
  En móvil se apilan. Los features no repiten fotos: cada subtarjeta muestra el nombre
  enlazado y sus cotas de esta pieza. Pulsar una cota la consulta en la columna izquierda.
- Los listados de features y piezas usan subtarjetas compactas y enlaces «Ver feature» /
  «Ver pieza» en el color principal. En Archivos se pulsa el tipo para abrir el fichero y
  ver su nombre. El tamaño queda centrado verticalmente junto al icono de descarga.
- La portada de pieza es una captura de todo el CAD STEP sin superficies marcadas.
  Al pulsarla abre el visor interactivo reutilizado de Features, sin edición de caras.
- **Identidad de la pieza (17/11/2026):** el código es el título; el nombre, opcional, va a
  su lado en tono secundario, sin repetir el código («3212 Pump Housing»). Debajo, una línea
  «Familia · Cliente» con lo que tenga. La tarjeta del catálogo sigue el mismo orden, y los
  selectores, enlaces, cotas encontradas y metrología muestran el código primero.
- En edición, la primera fila tiene **Código** (grande y estrecho) y **Nombre (opcional)**;
  debajo, **Familia** y **Cliente** con `CatalogNameSelect` (`SearchSelect` con buscador).
  La última fila del desplegable es siempre «+ Añadir familia» / «+ Añadir cliente», con el
  mismo botón que «Añadir feature» o «Añadir fichero». Al pulsarla aparece un campo vacío,
  como en «Añadir cota», relleno con lo ya buscado; Intro o salir del campo lo crea y lo
  elige, Esc lo cancela. Un nombre que ya existe (otras mayúsculas o espacios) elige el
  existente sin duplicarlo. Los filtros del catálogo no ofrecen esa fila. En
  móvil los campos van uno debajo de otro. Solo el código es obligatorio.
- Editar permite cambiar la identidad y añadir o desvincular features existentes.
  La relación es la misma en ambas direcciones. «Añadir feature» utiliza un botón con
  + y desplegable con buscador, como «Añadir pieza», excluyendo los ya vinculados.
  Guardar/Cancelar afectan a la cabecera y a los archivos de referencia; los vínculos
  con features se guardan en línea, como en el editor de Features.
- En edición, Archivos muestra CAD, Escaneo, Molde y Plano 2D, incluso si están vacíos.
  La carpeta selecciona otro archivo y la papelera quita el vínculo, sin borrar el original
  ni su historial. No aparece Descargar hasta volver a consulta. Los cambios se guardan
  junto a la cabecera; cambiar solo archivos no importa mediciones. Si se cambia la carpeta,
  la interfaz inicia una lectura después de guardar. Un error conserva el borrador.
- Las subtarjetas de piezas dentro de Features conservan la papelera de desvincular,
  pero no ofrecen el menú de tres puntos para cambiar la carpeta de origen.
- Cotas integra la consulta anterior de Metrología. La pieza la fija la ficha; no mostrar
  Feature ni Más filtros. Mantener buscador local y controles de revisión, evaluación,
  cavidades y correcciones. No elegir una cota automáticamente.
- Los selectores de vínculos usan `Common/SearchSelect`, compartido con los filtros del
  catálogo: misma altura y borde, búsqueda interna, teclado, limpieza y opciones con
  desplazamiento. Los filtros de revisión y evaluación usan los controles `Select` de detalle.
- Feature se filtra en el catálogo. La ficha ofrece todas las cotas de la pieza, incluidas
  las que no tienen feature; ignora ese filtro y los antiguos `category` y `tag` de enlaces
  previos, y los limpia al seleccionar cotas o abrir el plano desde la consulta. Metrología
  ofrece Pieza y Feature; «Más filtros» desapareció con Categoría y Tag.
  Las cotas disponibles son botones compactos.
- «Mostrar más cotas» es un botón con aspecto de enlace gris subrayado, sin negrita.
  Excluir los diagnósticos «Coordenadas» de las opciones y sugerencias de cotas.
- Cambiar pieza limpia cota, revisión, evaluación, cavidades, tramo y plano. El contexto
  anterior se recupera con Atrás.
- Un feature presente sin cotas vinculadas muestra ese estado. No atribuirle todas las
  cotas de la pieza. Las vinculadas sin mediciones siguen siendo seleccionables.
- Conservar pieza, cota y revisión al navegar por mediciones, correcciones y plano.
  Los enlaces antiguos directos al plano de un feature conservan su ámbito y sus subcotas.
  Una revisión vinculada diferente de la importada no puede mostrar sus mediciones.

## Página de cotas

La sección Cotas de la ficha de pieza contiene la consulta de metrología, sin pestañas
Documentos/Mediciones/Correcciones ni listados de archivos de mediciones.

Orden estable dentro de Cotas: buscador con Plano a su derecha, revisión si hay varias,
Correcciones debajo a la izquierda, filtros de evaluación y gráfica. `Common/SearchToolbar` alinea el buscador y `Parts/DrawingToggle`
en una fila, también en móvil; el botón tiene la misma altura que el campo.
No repetir debajo del buscador el número o el título de la cota seleccionada, ni añadir
el subtítulo «Cotas y mediciones · revisión…» bajo el nombre de pieza.
Al abrir Correcciones se mantiene esta misma estructura y selección, con **todos los
muestreos disponibles de la cota** en la gráfica. Nunca recortar el historial al antes/después
de un solo plan.
Los tramos se seleccionan **dentro de la gráfica**, pulsando la región entre dos muestreos.
La región seleccionada se rellena en gris; la tarjeta se actualiza sin mover la gráfica.
No añadir una fila de botones debajo para cambiar de tramo. Las regiones admiten ratón,
toque y teclado; consultar un punto no cambia el tramo. El detalle incluye una segunda
gráfica del tramo con las cavidades visibles y la propuesta del molde. Distingue mediciones
con línea continua y punto lleno de predicciones con línea discontinua y punto vacío;
no muestra fotografías/capturas ni «Documentos y valores de origen».

Ofrecer todas las acciones ya vinculadas a la cota y a cada plan, también las que no tienen
una previsión cuantitativa validada. Distinguir «sin acción vinculada» de «sin actuación
documentada». Una diferencia entre mediciones nunca basta para inventar una intervención.
Mantener separadas la base del XLS para la previsión y las mediciones CSV para el cambio real.

El alta de piezas parte de **Catálogo → Nueva pieza**. La cabecera exige título, código y
cliente, admite descripción opcional y reserva una portada cuadrada. La carpeta ocupa una
fila compacta con etiqueta y nombre en la misma línea. El selector es nativo de Windows en
modo local y está dentro de la web con SharePoint. Las propuestas siguen siendo borradores
hasta **Crear pieza**; la interfaz inicia después la lectura de los CSV/XLS/XLSX compatibles.
El registro y la lectura son operaciones separadas: un fallo al leer conserva la pieza creada
y permite reintentar. La ficha muestra el aviso del fallo y conserva el informe de la última
lectura correcta, del que salen las etiquetas del catálogo y los nombres de hoja de
componentes (24/11/2026). Contrato de selección, archivos y guardado en
[Uso en la ficha de pieza](ficheros-externos.md#uso-en-la-ficha-de-pieza).

«Añadir fichero» usa el botón con Plus, borde y tamaño de «Añadir feature». En edición el
nombre editable aparece bajo el tipo. En consulta la fila muestra el tipo, el tamaño y la descarga.
Al abrir un plano aparecen dos iconos de carpeta, para el plano y para el histórico.
Molde y Moldflow tienen la carpeta de SharePoint y la descarga del original juntas en la
cabecera. El lápiz abre el editor de captura con pegar, arrastrar o elegir imagen,
Cancelar y Guardar captura. El recuadro ocupa todo el ancho y el 70 % de la altura de la
ventana, como el visor CAD. En consulta se ve la captura o el icono de imagen del catálogo.
Al editar, el recuadro vacío muestra el icono de subida y admite arrastrar, Ctrl+V y clic
para elegir una imagen del ordenador. El lápiz requiere acceso al original con sesión activa.
Una carpeta identificada sin fichero vinculado se abre desde Archivos de la pieza.
En consulta, código y cliente aparecen juntos bajo la descripción, alineados a la izquierda.
La tarjeta del catálogo muestra la descripción opcional bajo el nombre, hasta dos líneas
como en Features. En la fila siguiente, «código · cliente» acompaña a la etiqueta azul
Pieza, con el cliente truncado y el texto completo al pasar el ratón. Si no hay cliente,
se muestra únicamente el código.
Guardar aplica cabecera y archivos juntos; Cancelar los descarta. Los vínculos con features
de una pieza existente se guardan al modificarlos y no se deshacen con Cancelar.
Cotas muestra datos extraídos, sin alta manual en la ficha de pieza.
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

El buscador ocupa todo el ancho disponible. **Sin textos en pantalla (Eduard, 18/11/2026):**
el recuadro en el plano basta para ver si se ha encontrado y dónde. Con una sola coincidencia
se enmarca directamente, sin botones. Con varias aparecen debajo botones compactos solo con el
número para pasar de una a otra; si el mismo número aparece en varias ubicaciones, `1/2`,
`2/2`. Conservar las subcotas entre los resultados, sin casilla para activarlas. No mostrar
contador, origen de la lectura («Revisada», «Texto del PDF», «.icp», «OCR · sin verificar»)
ni avisos explicativos: el contador y el origen solo se anuncian a los lectores de pantalla
(`sr-only` y nombre accesible de cada botón). «Revisada» sigue prevaleciendo al elegir la
ubicación.

No añadir columna lateral, descarga del original, filtro «Sin lectura», autor o fecha de la
revisión ni formulario «Número de esta ubicación / Guardar revisión» en esta consulta. Las
revisiones ya guardadas siguen siendo utilizadas al buscar.
Si una revisión no tiene una correspondencia inequívoca con el detector actual, conservarla
como resultado «Revisada» en su posición guardada. No trasladarla a otra ubicación por cercanía
ni ocultarla por no aparecer en el índice nuevo.

## Gráficas y detalle

- La gráfica de cotas ajusta las etiquetas del eje X al ancho disponible. Conserva
  los puntos y el identificador completo de cada muestreo al consultarlo. Los avisos
  técnicos de la importación se conservan fuera de la gráfica.
- Mostrar información solo sobre un punto, al pasar el cursor, tocarlo o enfocarlo con
  el teclado. Las zonas vacías y los segmentos de línea no activan información.
- Colocar el recuadro junto al punto y ajustarlo a los bordes. En la evolución contiene
  muestreo, cavidad y valor con unidad. Si varios puntos se solapan, mostrar esas cavidades juntas;
  no añadir otras alejadas aunque pertenezcan al mismo muestreo.
- Pulsar el punto fija el recuadro. En la gráfica principal, si existe procedencia,
  el valor enlaza al CSV/XLS/XLSX original y a su localizador. Se cierra con la X, Escape
  o pulsando fuera. En el detalle de correcciones también se muestran «Original»,
  «Cambio medido» o «Predicción» y la variación cuando está disponible.
- La leyenda permite activar cavidades. No incluir el texto «Banda de tolerancia» ni
  instrucciones como «Pasa el cursor…». No añadir estado ni límites al recuadro.
- No duplicar los valores en tablas permanentes bajo la gráfica.
- Conservar los huecos si faltan mediciones. Una ausencia no es cero.
- Distinguir una previsión de una medición real. Una propuesta del PPTX no demuestra
  ejecución, mejora ni cierre de una corrección.
- No mostrar por defecto catálogos de descargas, nubes PUNTS, perfiles A/B, listados
  de acciones ni detalles del importador. Las fuentes son contextuales a la consulta.

## Navegación y estado

- No añadir botones o enlaces de retorno como «← Piezas» o «Volver a…».
  Atrás y Adelante corresponden al navegador. Los títulos pueden mostrar contexto.
- Conservar pieza, búsqueda, feature, categoría, tag, cota, revisión, elemento, altura,
  evaluación, cavidades visibles, tramo y acción en la URL. Cambiar de evaluación conserva
  el tramo seleccionado. `cavity` se sigue admitiendo en enlaces antiguos; el detalle actual
  utiliza la selección compartida de cavidades visibles.
- La página del plano usa `drawingQ` sin sobrescribir la consulta de cotas.
  La ruta contiene el `fileId` del PDF concreto vinculado; no cambiarlo por otro documento
  según su nombre. Los enlaces antiguos con `drawingFile` conservan esa elección al redirigir.
  Atrás vuelve a la entrada anterior; la búsqueda del PDF reemplaza únicamente el estado
  de su propia página. Recargar conserva el documento y la búsqueda.
- En el catálogo, escribir, cambiar tipo o ajustar filtros reemplaza la entrada actual;
  abrir una ficha añade una entrada. En Cotas, escribir, ajustar evaluaciones/cavidades,
  tramo o acción reemplaza la entrada; seleccionar otra cota o abrir correcciones, plano
  u origen añade una entrada. Atrás recupera la consulta anterior.
- El origen tabular conserva `sourceLocator`, `sourceQ`, `sourceCavity` y `sourceValue`.
  Su búsqueda no sobrescribe `q` ni `drawingQ`.
- Mantener los enlaces antiguos de cotas/correcciones interpretando sus parámetros,
  sin recuperar las pestañas eliminadas.

## Comprobación

**Componentes (16/11/2026).** Una ficha guardada con carpeta ofrece «Componentes» junto al
nombre de carpeta, también cuando todavía no tiene componentes configurados. Es una opción
manual; su presencia no indica detección automática. Las piezas simples no necesitan usarla.
Al crear una pieza, «Varios componentes» la guarda sin leerla y abre «Componentes».
Al cerrar el diálogo, guardado o cancelado, se leen sus datos: **sin componentes, como una
pieza normal** (17/11/2026). El diálogo reutiliza campos, selector y buscador de archivos de
la aplicación, con Cancelar / Guardar cambios y una sola frase de ayuda. Cada componente es
un campo de nombre compacto («Añadir componente» lo crea vacío y enfocado). Debajo, una fila
por **hoja de Excel** (con el número de libros que la contienen) y otra por **archivo**, cada
una con su desplegable; cada plano lleva su revisión. Lo que coincide con el nombre de un
componente aparece ya elegido y marcado «· Propuesta»; el usuario lo corrige y guarda todo
en una operación.
Una cota conserva el número original, pero su selección incluye el componente.
El enlace busca ese número dentro del PDF de su componente/revisión; si hay varias opciones,
la consulta muestra un selector. Una asociación incompleta no recupera el plano de otro
componente. Cambiar de carpeta conserva identidades e historial y vacía las asignaciones,
que hay que confirmar para la nueva carpeta.

El registro técnico de lectura identifica hoja y primeras filas rechazadas y distingue
plantillas vacías de pendientes relevantes. No se muestra en la ficha de pieza.

La estrella de Archivos sigue indicando un único principal por tipo y pieza. No certifica
el documento ni representa un principal por componente. Los enlaces de las cotas usan la
asignación guardada de componente y revisión. Al elegir carpeta, la ficha conserva los
planos reconocidos. Si hay varias alternativas, la estrella queda vacía al guardar y
reabrir. Un único `.icp` vecino puede desempatar copias del plano idénticas en contenido.
En edición, la estrella permite elegir o retirar el principal.

La lectura del 26/10/2026 ha contrastado `CatalogPage`, `FeatureSearch`, `FeatureForm`,
`NoteList`, `FeaturePartEvidence`, `PartDetailPage`, `PartFiles`, `MetrologyPage`,
`Measurements`, `MeasurementPlot`, `Corrections`, `DrawingSearch` y las rutas de archivos.
Hay pruebas de regresión en `frontend/tests/components/catalog.test.cjs`,
`piece-editor.test.cjs`, `parts-ui.test.cjs` y `part-evidence-ui.test.cjs`; su existencia
y sus aserciones se revisaron, pero no se ejecutaron en esta pasada documental.

Revisar escritorio y móvil, teclado, ausencia de desplazamiento horizontal, consulta
de valores, combinaciones de filtros e historial del navegador. Los cambios compartidos
deben comprobarse también en Features para evitar divergencias entre pantallas.
