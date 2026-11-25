# Próximos pasos

> 🗓️ **20/11/2026: reunión con INTEPLAST.** Puntos a comentar en
> [reunion-inteplast-2026-11-20.md](reunion-inteplast-2026-11-20.md).

La implementación de protecciones y criterios de aceptación para todas las piezas se sigue en
[Plan de ingesta del 02/11/2026](plan-ingesta-2026-11-02.md), con verificaciones y contratos técnicos cerrados para las 21 piezas.

> Revisión completa contra el código el **26/10/2026**; las entradas posteriores llevan su
> fecha. El **04/11/2026** se contrastaron de nuevo los pendientes y se corrigieron los
> documentos desfasados ([revisión](revision-2026-11-04.md)). Este es el índice de
> pendientes; el contrato y las limitaciones de cada tema viven en el documento enlazado.
> Las pruebas de una fecha anterior no se presentan como validaciones de esta revisión.

## 🔴 Prioridad urgente: cambios rápidos (23/11/2026)

1. **Desplegado en Eurecat.** Un enlace guardado a un adjunto sin archivo indica que los archivos se gestionan en la ficha de la pieza. Si el adjunto tiene pieza, «Abrir pieza» lleva a su ficha. La prueba local de navegador cubre ambos casos.
2. **Completado en Eurecat.** Con Microsoft activo, **Admin → Add User** solo pide el correo corporativo. El alta crea un usuario normal activo.

## 🔴 Reorganizar Metrología de las 21 piezas (prueba de concepto, 24/11/2026)

**Decisión de Eduard: es un cambio importante y se hará en breve.** La reorganización la hacemos nosotros, no INTEPLAST. Se aplica en una copia de `Exemples` a las 21 piezas, para ver cómo quedaría y cómo de bien funciona la app. Después se enseña el resultado a INTEPLAST. La app es la misma; deben mejorar sus resultados. El código del backend queda así como versión definitiva, preparada para la estructura que habrá de verdad.

**Regla:** en `4- Metrologia/Interns/`, solo informes de muestreo, un Excel por muestreo. Si existen, los CSV de máquina pueden ir junto al Excel de su muestreo, pero solo sirven de comprobación. Todo lo demás va en cualquier otra carpeta: copias de cliente, Cpk, comparativas, MSA, volcados y PPAP. Detalle en [Método 3](estructura-de-carpetas-por-pieza.md#método-3-organizar-la-metrología-solo-con-excel).

1. **Relación de operaciones por pieza**, de ruta actual a destino:
   - informes de la raíz (3051, 3197, 3212) y de `Version 00/Interns` (3174) a `Interns/`;
   - comparativas fuera de `Interns/`;
   - copias dudosas, en su sitio;
   - CSV de máquina junto al Excel de su muestreo.
2. **Aplicarla en la copia de trabajo,** sin tocar los originales.
3. **Cambiar el backend:**
   - leer medidas solo de `Interns/`;
   - leer la variante (`-00`, `-10`, `-20`) y separar sus historiales;
   - avisar de los Excel sin muestreo reconocible y de los muestreos con varios Excel;
   - usar el CSV solo para comprobar (decisión 3): las medidas salen siempre del Excel; si el CSV da otro valor para la misma cota, muestreo y cavidad, la app avisa sin cambiar nada. Antes, contar en 3167, 3197, 3212 y 3233 cuántas cotas del Excel se identifican en el CSV ([límite](estructura-de-carpetas-por-pieza.md#método-3-organizar-la-metrología-solo-con-excel)).
4. **Recargar las 21 piezas y comparar con la carga actual:** muestreos, series duplicadas, avisos y gráficas.
5. **Enseñarlo a INTEPLAST con las preguntas abiertas:**
   - qué significan las variantes;
   - qué copia vale en los 13 muestreos repetidos dentro de `Interns/`;
   - qué son `3206-00_intern.121` y `.122`;
   - si adoptan la estructura para los informes nuevos.

## Siguientes pasos acordados para Planos y Cotas (23/11/2026)

1. **Mostrar solo el plano vigente en la ficha y en Planos.** Tomar el PDF definitivo de `1- 2D y 3D pieza`. Usar su `.icp` únicamente si corresponde a ese plano y está en esa misma carpeta. Si falta, mostrar el PDF solo. Excluir los PDF y `.icp` de método de medición, retoques y `OLD` de la selección del vigente. Mostrar una tarjeta por pieza o por componente con plano propio y conservar todas las hojas del PDF. Si hay varios candidatos indistinguibles, dejar la elección al usuario. Aplicar también el criterio de vigencia al CAD de pieza y al molde en sus carpetas correspondientes.
2. **Conservar las revisiones de las mediciones en Cotas.** Mantener el selector «Revisión de mediciones» cuando haya varias. Cada muestreo conserva el informe de origen, la revisión declarada y sus nominales y tolerancias. Cambiar la revisión consultada cambia la gráfica y mantiene el plano vigente en el visor. Si ese plano aún carece de mediciones, las anteriores siguen disponibles con su revisión. Mantener separadas las series cuya equivalencia no esté acreditada y señalar una cota histórica en el plano vigente solo si se ha comprobado la correspondencia.

3. **Conectar los iconos con SharePoint.** La carpeta del plano abrirá el directorio que contiene el PDF vigente. La carpeta con reloj abrirá el histórico de planos. Acordar con INTEPLAST el nombre y la ubicación del histórico antes de conectar ese botón. Moldflow tendrá un único destino, la carpeta que contiene su archivo. Abrir cada destino en otra pestaña con los permisos del usuario.

**Molde y Moldflow (24/11/2026).** En local, ambos adjuntos tienen la descarga del original junto a la carpeta de SharePoint. El recuadro de consulta tiene el tamaño del visor CAD y muestra la captura o el icono de imagen del catálogo. El lápiz permite pegar, arrastrar o elegir una captura opcional y guardarla. Si hay únicamente una carpeta identificada, la ficha de pieza da acceso directo a ella. Quedan pendientes la comprobación de los enlaces con una sesión real de Microsoft y el despliegue posterior en el servidor. Los dos iconos del plano siguen pendientes de conectar.

**Caso para validar la selección y las mediciones.** En la 3237, Planos debe abrir el PDF 05 de `2D y 3D pieza`. El plano 03 con globos de `Método de medición/OLD` pertenece al histórico. Cotas debe conservar las mediciones que citan el 04. [Casos de revisiones de plano e informes](preguntas-abiertas.md#a26-revisiones-plano).

**Rendimiento pendiente.** Priorizar las miniaturas visibles, aprovechar la imagen guardada mientras conserve su vigencia y el usuario tenga acceso, y aplazar las comprobaciones de globos hasta mostrar la imagen. Medir de nuevo el tiempo hasta la primera miniatura con las 40 tarjetas actuales. En dos reaperturas locales, con las 40 imágenes ya generadas, la primera se sirvió a los 13 s y la última a los 17 s.

El 24/11 el cambio a aristas invalidó el estilo de las portadas automáticas. En una apertura local pasaron 52 s desde la respuesta del catálogo hasta el primer PNG automático servido. Corregido en local para que la lista y la cuadrícula muestren la captura anterior del mismo CAD verificado durante la regeneración. Con el STEP de la 3212 (10,5 MB), cinco generaciones por estilo en Chromium local dieron medianas de 8,97 s sin aristas y 9,88 s con aristas. Cargar y decodificar el PNG por HTTP local llevó 7 ms de mediana en siete lecturas. Estas últimas mediciones excluyen SharePoint y la subida de la captura.

## Casos de trabajo del 23 de noviembre

Acuerdos de la reunión del viernes 20 recogidos para el lunes 23. El piloto sigue utilizando la carpeta `Exemples` del OneDrive de Eduard.

| Caso | Qué falta hacer o decidir |
|---|---|
| Pieza sin feature | Probar un borde ámbar y el aviso «Sin feature asociado» en la tarjeta del catálogo. La pieza se debe poder guardar así. Comprobar que el aviso desaparece al vincular el primer feature. |
| Carpeta del molde | El botón abre los ficheros del molde en SharePoint. Probar en el servidor con otra cuenta que tenga acceso, incluida una pieza con despiece y sin ensamblaje vinculado. |
| Carpeta de fotos | Acordar dónde se guardan las fotos y cómo se identifica la carpeta de cada pieza. Añadir un adjunto de tipo carpeta y comprobar que permite abrir todas sus fotos. |
| Material y cavidades | Pedir a INTEPLAST la plantilla Excel de datos de pieza y un ejemplo rellenado. Identificar los campos, leer automáticamente el material y el número de cavidades y mostrarlos junto a Cliente y Familia. Acordar si interesan otros campos. |
| Varios features sobre un CAD | Mostrar juntas las caras ya marcadas por el usuario sobre el CAD de la pieza, con un color por feature y una leyenda con los nombres. Probar con dos features y decidir cómo representar una cara compartida. |
| Piloto en el servidor de Eurecat | Ángel concedió `Files.Read.All` el 25/11 y se verificó en el token de Eduard. Pablo ya abre modelos 3D en la web. En sus capturas, 7 de 10 tarjetas carecían de miniatura. Queda comprobar las portadas con Pablo tras el despliegue. Fortinet sigue pendiente para descargas nuevas. [Diagnóstico](despliegue-servidor.md#estado-del-servidor-de-eurecat-y-punto-de-reanudación-23112026). |
| Excel de cotas y plano correspondiente | Pedir a INTEPLAST un informe rellenado y el plano numerado de la misma revisión, con el CSV de máquina cuando exista. Acordar cómo identificar pieza, componente, plano, revisión y muestreo. Contrastar el mismo número de cota en Excel y plano, con nominal, tolerancias, unidad, cavidad y valor medido. Pedir que se distingan las mediciones nuevas de las copiadas. |

## Portadas y carga del catálogo (19/11/2026)

1. **Primero:** [portadas por pieza](plan-portadas-por-pieza-2026-11-18.md). Carrusel en la ficha
   del feature, pila con número en lista y cuadrícula, y una captura por pieza.
   **Desplegado en la instalación local el 19/11/2026.** Copia restaurada en una BD temporal,
   migración aplicada y aplicación reconstruida. Bolt Eye y Nervios conservaron su imagen y su
   selección CAD en la pieza 3212. **Tanda 5 cerrada.** Eduard confirmó en la web que
   las dos fichas se ven correctamente. La ubicación de la copia consta en el plan.
   **Después de la tanda 5:** limpieza de imágenes subidas que ya no usa nadie (por ejemplo, la
   portada de una pieza desvinculada, cuyo fichero se conserva). Decisión de Eduard, 19/11/2026.
2. **Carga completada.** Las 21 piezas y los 8 features ya están en la BD local. La 3197 pasó de
   125 a 139 cotas conservando su historial. Se retiró «Nervios» y se cargó «Nervios de Soldadura»
   con las piezas 3205, 3206 y 3214. Se verificaron las 19 altas contra la selección de archivos del formulario.
   [Registro de ejecución](carga-catalogo-2026-11-19.md).

## Pendiente ahora (18/11/2026)

Lo abierto tras cerrar el plan del catálogo (tandas A–E) y las dos tandas de etiquetas,
todo ya en `main` (`7b471c0`). El detalle de cada tanda está en
[Estado de las tandas](#estado-de-las-tandas).

| Pendiente | Qué falta | Dónde empezar |
|---|---|---|
| **Cotas pendientes tras la carga del 19/11** | Revisar N21 de 3205, N203 de 3206, N4010 de 3238 y N80 de 3288, que la lectura no registró. En la 3288, los nominales de N30 y N43 corresponden a otras medidas. El informe de la 3226 sigue pendiente de interpretación | [Cotas pendientes y ejemplos de lectura](carga-catalogo-2026-11-19.md#cotas-de-referencia-pendientes) |
| **Distinguir el CAD de producto del utillaje** | En la 3202 el descubrimiento encontró un CAD en la carpeta de diseño y otros seis archivos en las carpetas de útiles del método de medición. Quedó sin principal y, por tanto, sin captura. Contrastar la regla general con la 3288, que sí tiene dos CAD de producto (base y tapa) | [Criterios para los archivos principales](plan-principales-y-tablas-2026-11-18.md) |
| **Filtro del catálogo por medidas** | Aplazado. Si se retoma, usar el resultado de la extracción de valores válidos con el mismo criterio que las tarjetas, para lista, cuadrícula y grafo | `backend/app/measurement_status.py` (hoy por tarjeta) y `crud.part_conditions` |
| **Validar en la web con sesión de Microsoft** | Nada de lo anterior se ha comprobado con la sesión real: borrado de pieza, familias y clientes, cuadrícula, grafo, Planos y etiquetas. Solo hay pruebas aisladas y capturas del banco | Instalación local, `http://localhost:5173` |
| **Primer administrador de INTEPLAST** | Eduard administra el piloto de Eurecat. Queda pendiente que INTEPLAST designe a su responsable y que esa persona compruebe su acceso a Admin | [Procedimiento de entrega](despliegue-servidor.md#primer-administrador-de-inteplast) |
| **Secretos de la instalación** | La instalación local usa los valores de ejemplo `changethis` (`SECRET_KEY`, contraseñas). Cambiarlos antes de llevarla al servidor | `.env`, [despliegue](despliegue-servidor.md) |
| **Etiquetas no incorporadas** | «Propuesta de retoque detectada»: solo cuando se pueda mostrar la frase original (3 de 20 piezas en el ensayo). «Cotas con datos»: en espera, porque los originales no acreditan el enlace plano–revisión–medida (caso 3288: plano REV.02, informes de revisión 1) | Ensayo del revisor, `C:/Users/eduard.almar/.codex/workspaces/inteplast-ensayo-etiquetas-20261118/resultado.json` |

El [plan de archivos principales y tablas de medidas](plan-principales-y-tablas-2026-11-18.md) recoge los criterios de aceptación de las mejoras incorporadas a `main`.

Límite conocido, no pendiente: «Globos verificados con .icp» nunca marca una hoja de un PDF
de varias páginas (sin lecturas, el lector solo asocia PDF de una página).

## Plan del catálogo: pieza, cuadrícula, grafo y planos (17/11/2026)

**Revisado por el segundo asistente el 17/11/2026, con sus ajustes incorporados; sin código.**
Recoge lo acordado con Eduard en el chat del 17/11/2026. Cada tanda se comprueba antes de
pasar a la siguiente y se anota aquí al cerrarla.
El traslado al servidor va aparte:
[nombre propuesto por IT](despliegue-servidor.md#nombre-propuesto-por-it-de-eurecat-17112026).

### Estado de las tandas

| Tanda | Estado (17/11/2026) |
|---|---|
| **A** | ✅ Cerrada. Migración `o16d92fa1c07` (tablas `partfamily` y `customer`, `Part.family_id`/`customer_id`; sin `Feature.tags`/`category`). API `/families` y `/customers`; filtros `family_id` y `customer_id` con el criterio único (`crud.part_conditions` / `features_of_parts`). Backend completo en BD aislada: 450 pruebas correctas, con las nuevas de migración (variantes de mayúsculas y espacios, empate por la pieza más antigua, vuelta atrás), alta repetida, pieza sin familia, filtros combinados y búsqueda sin tags. Ruff y mypy sin errores; cliente TypeScript regenerado |
| **B** | ✅ Cerrada. Código como título, nombre opcional al lado, «Familia · Cliente» debajo; `CatalogNameSelect` con «Añadir «texto»»; tarjetas y selectores con el código primero; sin categoría ni tags en features, catálogo y metrología (sin «Más filtros»); `category` y `tag` de enlaces antiguos se ignoran. Componentes del frontend: 159 pruebas, 158 correctas y 1 omitida (la opcional del diálogo de Windows), con las nuevas de familia añadida y reutilizada, filtros por familia y cliente, código primero y móvil. Biome y `tsc` sin errores |
| **Despliegue A+B** | ✅ 17/11/2026: copia de la BD de trabajo en `C:/Users/eduard.almar/.codex/backups/inteplast/20261117-162532/app-before-families-customers.dump` (comprobado que contiene `{bomba,automoción}` y «Bosch»), migración aplicada y backend y frontend reconstruidos. Resultado: 3212 enlazada al cliente «Bosch»; 3197 sin cliente; ninguna familia (las añaden los usuarios) |
| **C** | ✅ Cerrada (17/11/2026). Grupo «Vista» junto al buscador; cuadrícula de una columna en móvil y más según el ancho; vista guardada en el navegador y Lista si no se puede guardar; cotas encontradas arriba. Pruebas de navegador: cambio de vista por tipo, recuerdo tras recargar, móvil sin desbordar y almacenamiento bloqueado |
| **D** | ✅ Cerrada (18/11/2026). `GET /catalog/graph` con el mismo criterio de filtros que la lista (`catalog_part_filters`, `crud.feature_conditions`), tope de 500 nodos con `total` y `truncated`. `force-graph@1.43.5` fijado y cargado solo al abrir el grafo. Pruebas: 3 de API (nodos y uniones con filtros, igual que la lista en 7 combinaciones, corte con total real) y de navegador (clic en un nodo real de pieza y de feature abre su ficha, casillas de familia y cliente, clic en familia filtra, fondo con el tema, aviso del tope). Revisado en capturas claro/oscuro: corregidos repintado en oscuro, código duplicado, zoom excesivo y desbordamiento lateral del lienzo |
| **E** | ✅ Cerrada (18/11/2026). `GET /catalog/drawings` (todos los planos, con componente y revisión asignados) y miniaturas `POST`/`GET /files/{id}/thumbnail` cacheadas por versión del original. Pruebas: listado y filtros; no regenera si el archivo no cambia y sí si cambia (borra la anterior y el enlace viejo deja de servir); `busy` con los huecos ocupados; solo PDF. Navegador: cuadrícula, marcador y reintento, icono si falla y clic al visor del plano |
| **Comprobación final C–E** | Backend completo en BD aislada: 456 pruebas correctas. Componentes del frontend: 167 pruebas, 166 correctas y 1 omitida. Ruff, mypy, Biome y `tsc` sin errores; cliente regenerado. Se ajustó `test_usage_counts…` de `test_parts.py`, que dependía de que la pieza saliera en la primera página de `/parts/` |
| **Entorno (18/11/2026)** | OneDrive había dejado `node_modules` «solo en la nube» y no podía recuperarlo («la red no está disponible»). Con permiso de Eduard se borró y se reinstaló con `npm ci`; la carpeta queda marcada para mantenerse en el equipo |
| **Revisión externa D–E (18/11/2026)** | Cuatro fallos reproducidos y corregidos con pruebas de regresión: (1) **seguridad**: la etiqueta emergente del grafo interpretaba el nombre como HTML; ahora se escapa (prueba con `<img onerror>` que no se ejecuta); (2) «Planos» solo miraba `PartFile` y dejaba fuera los planos de piezas por referencia o adjunto de feature; ahora usa la misma regla que la ficha (`read_files`); (3) dos peticiones de la misma miniatura podían borrarse el temporal (error 500) y PyMuPDF corría en hilos; ahora proceso hijo con 60 s de límite, bloqueo por documento liberado también tras fallo o timeout y temporal `*.part` fuera de la limpieza; (4) el grafo no permitía cargar más de 40 cotas; ahora «Mostrar más cotas», y lista y cuadrícula conservan su paginación sin cotas |
| **Etiquetas, tanda 1 (18/11/2026)** | «Medidas detectadas» / «Informe pendiente de interpretar» / «Sin medidas detectadas» en tarjeta y cuadrícula (`app/measurement_status.py`), y feature sugerido por carpeta en «Nueva pieza», editable antes de crear. **Aceptación con los originales** en pila aislada (Carpeta → Crear pieza quitando todas las sugerencias → Leer datos; 25 carpetas, 21 códigos, 16 min): 19 piezas con medidas, las mismas 19 que el ensayo del revisor; 2820 «Sin medidas detectadas»; 3226 «Informe pendiente de interpretar»; 3212 detectada con la lectura aún en proceso; solo 4 sugerencias (Bolt Eye: 2820, 3051, 3197 y 3212), ninguna vinculada tras quitarlas; «Nervios de Soldadura» no sugiere «Nervios». Revisión posterior: dos fallos corregidos con prueba de regresión — la etiqueta contaba importaciones sustituidas (ahora solo la vigente de cada revisión, muestra y cavidad, con el desempate del historial) y cambiar de carpeta podía quitar un feature añadido a mano. Repetida la aceptación con los originales tras corregirlos: mismo resultado (19, 2820 y 3226, 4 sugerencias). Backend 490 pruebas y componentes 175 (174 correctas, 1 omitida). Pendiente: filtro del catálogo por medidas (ver [Pendiente ahora](#pendiente-ahora-18112026)) |
| **Etiquetas, tanda 2 (18/11/2026)** | «Documentación de retoques» en tarjeta y cuadrícula (la lectura encontró documentos de correcciones; solo disponibilidad) y «Globos verificados con .icp» en Planos (`POST /files/{id}/icp-check`: ajuste 1:1 del `.icp` y aros verdes o azules de un detector independiente; ≥10 coincidencias y la mitad de aros y sellos; un único proyecto; en proceso hijo, caché por versión). Solo etiquetas positivas. **Aceptación con los originales** (25 carpetas, 21 códigos, 22 min): retoques en 20 piezas, las mismas 20 del ensayo (todas menos la 2820); 60 planos comprobados, 7 verificados, los mismos 7 archivos del ensayo (3202 ×2, 3205 ×2, 3206, 3288 ×2); 283 controles con `.icp` de otras piezas y ninguno aceptado; sin errores ni tiempo agotado (el más lento, 13,7 s). La tanda 1 sigue igual (19 piezas con medidas, 2820 y 3226, 4 sugerencias). Revisión posterior: tres fallos corregidos con prueba de regresión — (1) un PDF de varias páginas con los mismos huecos y otros números (globos 1–24 frente a un `.icp` 101–124) salía verificado: ahora también debe asociarlo el lector del plano, como en el ensayo, y un PDF de varias páginas nunca se verifica; (2) la clave de caché y el cálculo podían ver listas de `.icp` distintas: ahora salen de una sola lectura y el resultado se descarta si cambian durante el cálculo; (3) la pantalla recordaba la etiqueta por la versión del PDF y dejaba de esperar a los 80 s: ahora pregunta al abrir Planos y sigue mientras haya «busy». Repetida la aceptación (24 min): los mismos 7 planos, 20 retoques, 283 controles sin aceptados y la tanda 1 igual. Caché del verificador pasada a `icp-verification-v2` (un positivo guardado con la regla anterior se recalcula y se rechaza; regresión con el PDF de dos páginas). Backend 506 pruebas; componentes 177 (176 correctas, 1 omitida). Subida a `main` con el visto bueno del revisor |

### Decisiones de Eduard (17/11/2026)

| Tema | Decisión |
|---|---|
| Identidad de la pieza | El **código** (único) pasa a ser el título. El **nombre** queda opcional, a su lado. Debajo, **familia** y **cliente** |
| Familia | Campo nuevo. Desplegable con lista guardada para todos y «+ Añadir» al final, en modo edición. Idioma mezclado de momento; se corregirá más adelante |
| Cliente | La empresa que encarga la pieza a INTEPLAST. Pasa de texto libre al mismo desplegable con «+ Añadir» |
| Tags | **Se quitan** de los features y no se crean en la pieza. Contenían «bomba» y «automoción» (Bolt Eye); «bomba» era falso para el 3197 (Pot) |
| Categoría de feature | **Se quita.** No viene de INTEPLAST y con 8 features casi cada categoría tiene uno solo. Lo propio de cada feature va en la descripción, las advertencias, las lecciones y las cotas de cada pieza |
| Filtros | Quedan pieza, feature, familia y cliente. Desaparecen Categoría y Tag del catálogo y de metrología |
| Vistas | Botones Lista · Cuadrícula · Grafo en el catálogo |
| Grafo | Como el de la pestaña Piezas del visor: piezas como círculos con la captura del CAD, features con su nombre. Clic → ficha. Familia y cliente se pueden añadir, apagados al empezar. Fondo según el tema |
| «Fabricante» | Era el cliente |

### Tanda A: modelo de datos (backend)

1. **Tablas `PartFamily` y `Customer`** (id, nombre). Nombre único sin distinguir mayúsculas
   ni espacios sobrantes: «bosch» y «Bosch » no crean otra entrada. `Part.family_id` y
   `Part.customer_id`, opcionales.
2. **Migración del cliente:** los textos de `Part.customer` se agrupan con la misma
   normalización de las tablas (sin distinguir mayúsculas, sin espacios al principio ni al
   final y con los espacios internos reducidos a uno): «Bosch», «bosch» y «Bosch » dan un solo
   `Customer`. Se guarda la grafía más repetida y, si empatan, la de la pieza más antigua. Cada
   pieza queda enlazada a él. Fuera de esa normalización no se corrige ni se fusiona nada
   («Bosch» y «Robert Bosch» siguen siendo dos). Hoy solo hay «Bosch» (3212).
3. **Quitar `Feature.tags` y `Feature.category`.** Copia de la BD de trabajo antes de migrar.
   Valores que se pierden y quedan anotados: Bolt Eye (`hole`, `bomba`, `automoción`) y
   Nervios (`rib`). La vuelta atrás de la migración recrea las columnas vacías; los valores
   solo se recuperan desde la copia.
4. **API:**
   - `GET /families`, `POST /families`, `GET /customers` y `POST /customers`, con usuario
     autenticado. Añadir devuelve la existente si el nombre ya está (sin duplicar).
   - Renombrar y fusionar quedan fuera de este plan, para cuando se corrija el idioma. No se
     borra una familia o un cliente en uso.
   - Pieza: crear, editar, catálogo y ficha devuelven y aceptan `family` y `customer` como
     referencia. Se retira el texto libre de cliente.
   - Catálogo: filtros `family_id` y `customer_id`. **Criterio único para lista, cuadrícula y
     grafo, calculado en el servidor:** una pieza cumple si cumple todos los filtros de pieza
     activos (pieza, familia y cliente). Un feature cumple si está vinculado a **al menos una
     pieza que cumpla todos a la vez**. Ejemplo: con familia «Pump Housing» y cliente «Bosch»
     sale un feature vinculado a una pieza Pump Housing de Bosch, pero no uno vinculado a una
     pieza Pump Housing de otro cliente y a otra pieza de Bosch de otra familia.
   - Se retiran `category` y `tag` del catálogo, de `/features/` y de `/features/filters`.
5. **Quitar tags y categoría del resto del backend:**
   - búsqueda de texto (`crud.py`, que hoy busca también en los tags);
   - validación de tags con forma de N-number (`routes/features.py`);
   - texto del asistente (`assistant/corpus.py`);
   - seed (`seed_features.py`);
   - modelos públicos (`models.py`, `knowledge_models.py`);
   - el enum `FeatureCategory`.
6. **Sin sugerencia de familia desde la carpeta** (descartada en la revisión): el texto tras el
   código puede ser el nombre concreto de la pieza y no su familia. Basta el desplegable.
7. **Cierre:**
   - tests de la migración en la pila aislada, con datos previos de cliente (incluidas
     variantes de mayúsculas y espacios), tags y categoría;
   - tests de la API: alta repetida, mayúsculas, pieza sin familia y filtros combinados
     (familia y cliente en la misma pieza frente a piezas distintas);
   - test de la búsqueda sin tags;
   - cliente TypeScript regenerado, Ruff y mypy.
   - **A no se aplica sola a la BD de trabajo:** se despliega junto con B (ver «Orden y
     dependencias»).

### Tanda B: pieza y filtros (frontend)

1. **Editor de pieza** (`PartDetailPage.tsx`):
   - primera fila con **Código** en grande y estrecho, y **Nombre (opcional)** a su lado;
   - debajo, **Familia** y **Cliente** como desplegables con buscador;
   - al final de cada lista, «+ Añadir» con el texto escrito, siguiendo el patrón de
     «Añadir pieza» y «Añadir feature» (`PartActions.tsx`, `AddFeatureButton.tsx`);
   - en móvil, los campos uno debajo de otro.
2. **Ficha de pieza:** título = código; el nombre al lado en tono secundario; una línea
   «Familia · Cliente».
3. **Tarjeta del catálogo** (`PartCard.tsx`) con el mismo orden. Revisar las 23 apariciones de
   `name ?? code` y similares para mostrar siempre el código primero, en selectores, enlaces,
   cotas encontradas y metrología.
4. **Features:** se quitan categoría y tags del formulario, la ficha y la tarjeta
   (`FeatureForm.tsx`, `FeatureCard.tsx`, `TagInput.tsx`, `constants.ts`, ficha del feature).
5. **Filtros:**
   - Catálogo (`FeatureSearch.tsx`): Pieza, Feature, Familia y Cliente.
   - Metrología (`MetrologyFilters.tsx`, `measurementSelection.ts`, `consultationEntries.ts`,
     `Measurements.tsx`, `MetrologyPage.tsx`): se quitan Categoría y Tag.
   - Los parámetros `category` y `tag` de enlaces antiguos se ignoran sin error.
6. **Cierre:** compilación, lint, pruebas de navegador existentes adaptadas y nuevas:
   - añadir una familia desde el desplegable y elegirla en otra pieza;
   - filtrar por familia y por cliente;
   - ficha y tarjeta con código primero;
   - vista móvil.

   `docs/interfaz.md` y `docs/app-web.md` actualizados.

### Tanda C: cuadrícula

1. Botón **Lista / Cuadrícula** en el catálogo, para Todo, Piezas y Features, junto al buscador.
2. Cuadrícula responsive: una columna en móvil, más según el ancho. Cada celda lleva la portada
   grande, el código y el nombre; en piezas también la familia. Los features llevan su
   portada y nombre.
3. La vista elegida se guarda en el navegador. Si no se puede guardar, se abre en Lista sin error.
4. Las cotas encontradas por búsqueda siguen arriba, como ahora.
5. **Cierre:** pruebas de navegador del cambio de vista, que se recuerde y en móvil.

### Tanda D: grafo

1. Tercer botón, **Grafo**. Muestra lo mismo que la lista con la búsqueda y los filtros activos,
   con el mismo criterio de filtros de A.4.
2. **Tamaño:** el grafo carga **todos** los resultados de una vez, sin las páginas de 40 de la
   lista. Para no colgar el navegador hay un tope alto (500 nodos). Si se supera, el grafo lo dice
   («Mostrando 500 de 1.234: filtra para ver el resto») y nunca presenta una parte como si fuera
   todo. Con las 21 piezas de Exemples y sus features queda muy lejos del tope.
3. **API** `GET /catalog/graph`, con los mismos filtros que el catálogo y el total real:
   - nodos de pieza (id, código, nombre, imagen de portada si existe), de feature (id,
     nombre), de familia y de cliente;
   - uniones pieza–feature (`FeaturePartLink`), pieza–familia y pieza–cliente.
4. **Dibujo:**
   - Librería `force-graph`, la del visor. Va instalada con npm a versión fija y se carga solo
     al abrir el grafo, para no hacer más pesado el catálogo.
   - **Pieza:** círculo con la captura del CAD ya guardada. Si no la tiene, círculo con el
     código; el grafo no lanza capturas de CAD.
   - **Feature:** nodo con su nombre, como en el visor.
   - **Familia y cliente:** nodos de otro color, con interruptores apagados al empezar.
   - **Colores y fondo** tomados del tema claro u oscuro de la web; cambian al cambiar de tema.
5. **Interacción:**
   - arrastrar, zoom y nombre al pasar el ratón;
   - **clic en pieza → ficha de pieza; clic en feature → ficha de feature**;
   - clic en familia o cliente → catálogo filtrado por ese valor.
6. **Límites:** el grafo no es navegable con teclado; la lista y la cuadrícula siguen siendo
   la vista accesible. Hoy la BD de trabajo tiene 2 piezas, así que se verá casi vacío hasta
   cargar más.
7. **Cierre:**
   - test de la API: nodos y uniones con filtros, mismo resultado que la lista con los mismos
     filtros, y aviso con el total cuando se supera el tope;
   - pruebas de navegador: **pulsar un nodo real** de pieza y de feature y comprobar que se abre
     su ficha (sin prueba unitaria aparte, que repetiría la misma lógica), los interruptores
     añaden y quitan nodos, y el fondo cambia con el tema.

### Tanda E: planos en el catálogo

1. Nuevo tipo **«Planos»** junto a Todo · Piezas · Features, siempre en cuadrícula.
2. **Qué planos:** **todos** los archivos de tipo plano vinculados a piezas cargadas
   (`PartFile` de tipo `drawing`), no solo el principal: en piezas con BASE y TAPA, mostrar solo
   el principal ocultaría documentación necesaria. Con los filtros de pieza, familia y cliente,
   con el criterio de A.4.
3. **Miniatura:** PNG de la primera página, generado en el servidor con PyMuPDF (ya en la
   imagen del backend). Se guarda en el almacén de derivados con una clave de la versión del
   archivo. Se genera la primera vez que se pide, con un marcador mientras tanto y pocas a la
   vez. Funciona igual con carpeta local y SharePoint (caché existente).
4. **Celda:** miniatura, nombre del archivo y código de pieza. Además, **componente y revisión
   cuando estén asignados** en «Organizar por componentes», para distinguir los planos sin
   depender del nombre del archivo. Al pulsar, se abre el plano en su pieza, con la ruta actual
   del visor de planos.
5. **Cierre:** tests del endpoint y de la caché (no regenera si el archivo no cambia; regenera
   si cambia), y prueba de navegador de la cuadrícula y del clic.

### Orden y dependencias

A → B → C → D. E depende de A (filtros) y puede ir después de C. Cada tanda deja tests,
compilación, lint, Ruff y mypy correctos, cliente regenerado si cambia la API, y documentación
al día. Cambios sin commit (Git lo gestiona Eduard), con un parche de revisión por tanda.
Se parte del estado con los [cambios del 17/11/2026](#cambios-del-17112026-sin-commitear)
(migración `n95c81ebf063`, componentes por nombre): las migraciones de A van detrás.

**A y B se despliegan juntas.** Se desarrollan y prueban por separado en la pila aislada, pero
la BD de trabajo no se migra hasta tener B lista: con A sola, la web actual seguiría pidiendo el
cliente como texto, los tags y la categoría, que ya no existirían. Copia de la BD, migración y
reconstrucción de backend y frontend van en el mismo paso.

### Fuera de este plan

- Renombrar y fusionar familias o clientes; se hará al corregir el idioma.
- Uniones entre piezas por archivos idénticos (el visor las calcula con el SHA-256 de cada
  fichero; la web no lo guarda).
- Los tags de plano del visor quedaron fuera del plan inicial. El catálogo ya muestra el
  resultado del lector de cada PDF, descrito en [la interfaz](interfaz.md).
  La prueba con las carpetas originales en una instalación aislada dio «Globos detectados»
  en el 3212 (114 números leídos de 262 aros) y «Sin marcas detectadas» en el 3197.
  «Cotas con datos» sigue pendiente de acreditar la relación entre cota, plano y revisión.
- Rellenar familias o clientes de las piezas: lo hacen los usuarios, no el agente.

### Revisión (17/11/2026)

El segundo asistente da el plan por coherente y ejecutable, sin cambiar alcance ni añadir
pantallas. Respuestas a los puntos abiertos, ya incorporadas:

1. **Familia y cliente:** tablas propias. La migración agrupa variantes de mayúsculas y
   espacios (A.2).
2. **Tags y categoría:** se borran con copia previa y valores documentados. Volver atrás no
   los recupera automáticamente.
3. **Sugerencia de familia desde la carpeta:** fuera (A.6).
4. **Planos:** todos los vinculados, con componente y revisión cuando estén asignados (E.2, E.4).
5. **Clic del grafo:** basta una prueba de navegador sobre un nodo real (D.7).

Ajustes de ejecución añadidos: A y B se despliegan juntas; un solo criterio de filtros para
lista, cuadrícula y grafo (A.4); el grafo carga todos los resultados, con tope y aviso (D.2).

## Plan por tandas (16/11/2026)

Acordado por Eduard el 16/11/2026, tras contrastarlo con el revisor. **Criterio general:** lo
habitual es automático; las excepciones tienen un punto manual rápido. Las piezas de un solo
componente siguen como hoy, sin preguntas nuevas. No se busca el 100 % en planos futuros.
El estado de cada tanda se anota aquí al cerrarla.

| Tanda | Qué | Cierre |
|---|---|---|
| 1.1 | Cerrar los cambios del 13/11: pruebas del editor de piezas en el navegador y propuestas de carpeta de 3212, 3309 y 3288 (sin incorporar medidas de BASE/TAPA) | Resultados documentados y pendientes identificados. No hace falta regenerar el cliente |
| 1.2 | Comparativas CSV (`measurement_tables.csv_rows`): POINT del 3212 que heredan N178, comparativas del 3197 sin tolerancias y `3197_totes_nozzle 55/65.csv` sin reconocer | Tests que fallan antes y pasan después, contraste con las fuentes, formatos ya admitidos sin cambios injustificados y lector versionado |
| 2 | 3226: etiquetas y disposición de cabeceras y cavidades (la fila 13 ya está dentro de las 30 que examina el lector). **Protección con test:** las `DR(base)` del 3288 no se incorporan mezcladas con la tapa | El 3226 da medidas contrastadas; diferencias con v6 explicadas |
| 3 | `.icp` automático en `backend/app/ingestion/`: extraer sellos, asociarlos a PDF/página/revisión y colocarlos, sin scripts, SQLite ni JSON del prototipo. Planos con globos (calibración) y planos limpios (1:1 o correspondencia comprobada) | Coinciden números **y posiciones** en casos de 3202, 3205, 3206 y 3288. Lista de fallos concretos, que decide la prioridad de «Ajustar marcas» |
| 4 | Componentes, versión acotada: identidad de cota = pieza + componente + código + revisión; componente predeterminado en piezas simples; «Organizar por componentes» en la ficha de pieza, con propuestas por nombres explícitos (`DR(base)`, `DR(tapa)`); asignación de planos y hojas guardada. Sin reglas exclusivas del 3288. Antes de migrar el 3288, revisar qué hay cargado y su procedencia | Dos cotas con el mismo número en BASE y TAPA siguen separadas al importar, consultar, ver gráficas y abrir planos. Migración y cliente regenerado |
| 5.1 | Hojas omitidas: clasificar por contenido y función las 364 por nombre y las 97 por estructura | Exclusiones justificadas; pendientes relevantes visibles en la web |
| 5.2 | `No.`: mejora acotada en el prototipo (`N°`, tablas de vistas, notas generales) y traslado al backend con «OCR · sin verificar» | Medido en casos conocidos y controles negativos; no es validación independiente |
| 5.3 | Identificadores con letras: tabla por pieza y reglas explícitas antes de admitir nada | Ejemplos documentados; sin fusionar cotas de una misma zona |
| 5.4 | «Ajustar marcas» en el visor de planos de la web (giro, volteo, desplazamiento, escala) | Solo si los fallos de la tanda 3 lo justifican |

**Fuera de esta entrega:** lector de globos (congelado), `[]`, recuadros, localización por zonas,
lector general de correcciones, exports `#P#` (esperan la A27), selección automática del CAD de
molde y rendimiento.

Los cambios de cada tanda quedan sin commitear. Para revisarlos por separado hay un parche por
tanda en `out/plan-2026-11-16/` (fuera de Git).

### Cambios del 17/11/2026 (sin commitear)

Pedidos por Eduard el 17/11/2026. Ninguna ficha se ha tocado a mano.

- **Borrar pieza con sus datos:** hecho, ver [más abajo](#borrar-pieza-con-sus-datos).
- **`.icp` de copias idénticas:** si la carpeta del plano no tiene `.icp`, hereda el de una copia
  byte a byte dentro de la pieza. Sobre los originales: 4 PDF heredan; **27 de 30 planos
  situados** (antes 25). Se esperaban 3 de los 5 pendientes y son 2: el tercero hereda bien,
  pero son 3 páginas sin globos. [Medición](../conocimiento/planos-globos.md#copias-idénticas-17112026).
- **Plano principal propuesto:** prefiere un PDF con `.icp` en su carpeta; si no hay, el
  primero por ruta. Cambia la propuesta en 4 de 21 carpetas (3202, 3205, 3206, 3288). En el
  3288 propone el primero de 9 con `.icp` (`REV.01/BSG-296-00/…`), que es de conjunto, no de
  BASE: la regla no distingue componentes. [Detalle](ingesta-automatica.md).
- **Componentes por nombre:** el usuario nombra los componentes y la app propone archivos y
  hojas; sin componentes, la pieza se lee como una sola. Con «Varios componentes», al crear la
  pieza se abre «Componentes» y al cerrarlo se leen los datos.
  [Detalle](ingesta-automatica.md#propuesta-por-nombre-17112026).
- **Revisión externa (17/11/2026):** cinco fallos reproducibles, corregidos con pruebas de
  regresión: (1) el borrado eliminaba una imagen usada en una nota de un feature; (2) la clave
  de confirmación no cambiaba al editar una ubicación revisada, una cota o una importación;
  (3) dos `.icp` heredados con la misma carpeta y nombre (`REV1/copy/plan.icp`,
  `REV2/copy/plan.icp`) se pisaban y el lector recibía uno; (4) asignar un PDF a un componente
  lo hacía principal si la pieza no tenía plano; (5) lo que se veía «Sin asignar» sin tocar el
  selector (ambiguo o sin coincidencia) no se recordaba y podía recibir propuesta después.
  Pruebas: `test_parts.py` (imagen de nota; clave al editar ubicación, cota o importación),
  `test_drawing_twins.py` (`REV1/copy` y `REV2/copy`), `test_components.py` (sin principal) y
  `piece-editor.test.cjs` (lo ambiguo guardado no se propone al renombrar componentes).
- **Instalación local:** reconstruida y migración `n95c81ebf063` aplicada el 17/11/2026.
- **Pendiente de los cuatro:** verlos en la web con carpetas reales.

### Resultados de la tanda 1 (16/11/2026)

**1.1 Cambios del 13/11.**
- **Editor de piezas en el navegador:** `piece-editor.test.cjs` y `piece-file-proposals.test.cjs`,
  9 pruebas correctas en 70 s. El agotamiento de `warmUp` del 13/11 no se reproduce. Aquel día
  corría a la vez la lectura de las 21 carpetas con cuatro procesos; es una explicación
  posible, no comprobada.
- **Propuestas de carpeta**, con el código actual de `part_setup.discover` y de
  `pieceFileDrafts.discoveredFiles` sobre las carpetas reales (pieza nueva, sin base de datos):
  - 3212: un CAD, un plano, un molde y un escaneo, como antes.
  - 3309: propone el CAD `…SUPPORT_FUEL_TANK_FILLER_PIPE_NO2.stp`.
  - 3288: los 10 planos, con uno principal (el primero por orden alfabético, el de la BASE de
    `1- 2D y 3D pieza`). De los 2 CAD y los 2 escaneos solo propone uno: el de la TAPA no sale.
    Se resuelve con los componentes (tanda 4).
- **Pendiente:** verlo en la web con sesión iniciada. El login es de Microsoft y no se puede
  automatizar; lo comprobado es el código de las dos partes, no la pantalla.

**1.2 Comparativas CSV** (`automatic-tables-v7`).
- Los tres fallos se reprodujeron con los ficheros reales y con ejemplos mínimos. Los 4 tests
  nuevos fallan con el código anterior y pasan con el arreglo.
  - Título en la línea del primer valor (`POINT 1 -> …;Cálculo de fórmula;…`): las 61 filas con
    título de cada comparativa del 3212 heredaban N178. Ahora abren su bloque, como en el export
    individual, y dan las mismas series.
  - Nominal y tolerancias se localizan por contenido. Solo la comparativa `.03` del 3197 las
    perdía (840 filas); `.04` y `.07` se leían bien.
  - `3197_totes_nozzle 55/65.csv`: 80 filas cada una; antes, ninguna.
  - Una disposición no prevista deja el archivo como pendiente, con su línea; no se adivina.
- **Efecto en lo que guarda la app**, comparando fila a fila la lectura completa antes y después:
  - 3212: las 8.041 observaciones, idénticas. El fallo de los POINT no llegaba a guardarse:
    donde hay export individual de la cavidad, la comparativa se descarta.
  - 3197: 11.276 idénticas; entran 160 de los CSV de boquilla y salen las 160 celdas del Excel
    `intern.08` que sustituyen. 158 tienen el mismo valor; las otras 2 son
    [I-209](../conocimiento/incongruencias.md).
- **Comprobaciones:** 397 tests de backend con PostgreSQL `app_test` aislado, Ruff y mypy.
- **Resultados ya importados:** al cambiar la versión del lector, **Actualizar datos** guarda una
  importación nueva de **todos** los grupos (revisión, muestreo, cavidad) de la pieza, no solo de
  los que cambian, y conserva las anteriores en el historial (`automatic_measurements.refresh`
  compara lector y contenido). No se ha ejecutado en la BD de trabajo.

### Resultados de la tanda 2 (16/11/2026)

**Las dos hojas fallaban por causas distintas, y el 3226 no se puede leer como cotas.**
- **3226: bloqueado por los datos.** En `4- Metrologia/Interns/3226-00_intern.01.xls!DR`, leído
  con el lector de la app, la columna `Nr` está vacía en las 47 filas con nominal (14–60) y hay
  una sola columna de valores, sin rótulo de cavidad. Su plano tampoco lleva numeración. No hay
  identificador que leer y no se inventa uno por la posición de la fila. El criterio de cierre
  («el 3226 da medidas contrastadas») **no se cumple**: hace falta un informe o plano numerado
  ([A28](preguntas-abiertas.md#a28-3226-sin-numeracion), sin enviar).
- **3288 `DR(base)`:** las cavidades van rotuladas solo con números (`1`…`20`); `DR(tapa)` usa
  `Cav.1`…`Cav.20`. Por eso solo se lee la tapa.

**Hecho:**
- El lector explica por qué no lee una hoja con cabecera `Nominal`
  (`measurement_tables.unread_structure`) y la ficha de pieza la enseña como entrada propia,
  «archivo · hoja X», también cuando otra hoja del mismo archivo sí se leyó
  (`ReadFileReport.sheet`, cliente TypeScript regenerado). El estado queda «parcial».
- **Protección BASE/TAPA:** no se ha añadido la lectura de cavidades numeradas, que es lo que
  mantiene `DR(base)` fuera hasta que existan los componentes (tanda 4). Test:
  `test_base_sheet_is_not_mixed_with_the_cover_before_components_exist`.
- Test del 3226: `test_report_without_cota_numbers_or_cavity_label_stays_pending_with_its_reason`.

**Comprobado:**
- Las 21 carpetas, fila a fila contra la lectura anterior: 1.212.958 observaciones antes y
  después, ninguna nueva, quitada ni cambiada.
- 97 hojas pasan a verse como pendientes con su motivo (las 97 omitidas por estructura):
  70 sin columnas de cavidad reconocidas, 14 con cavidades solo numeradas (4 son las `DR(base)`
  del 3288) y 13 sin número de cota ni rótulo de cavidad.
- 400 tests de backend con PostgreSQL `app_test` aislado, Ruff, mypy, compilación y lint del frontend.

### Resultados de la tanda 3 (16/11/2026)

**El `.icp` ya está en la app.** Si junto al plano vinculado hay un `.icp`, el número de cada
globo sale de él y no del OCR. Lector propio en `backend/app/ingestion/icp.py`, sin scripts,
SQLite ni JSON del prototipo. Contrato en
[Globos del `.icp`](cotas-y-evidencia-web.md#globos-del-icp-16112026).

- **Lectura de los sellos:** los 19 `.icp` de Exemples dan los mismos 2.126 sellos que la
  biblioteca, con número y coordenadas idénticos.
- **Medición en los 30 planos con `.icp`:** 25 situados (18 con globos dibujados y 7 limpios a
  escala 1:1), 2.521 sellos, todos con el mismo número que el visor y ninguno a más de un radio
  de su sitio (máximo, 0,4 radios). Detalle en
  [planos con globos](../conocimiento/planos-globos.md#icp-automático-en-la-app-16112026).
- **Corrige al OCR:** en 12 globos el lector ofrecía otro número (10 en el 3202 «G»). Con el
  `.icp` se enseña el correcto.
- **Los 5 sin situar** no son fallos de colocación: 4 no tienen el `.icp` en su carpeta (está
  junto a una copia idéntica en otra) y 1 es un PDF de 2 páginas sin globos. En 3 de ellos basta
  con vincular la copia que está junto a su `.icp`.
- **Sin `.icp` no cambia nada:** el índice de un plano real del 3238 es idéntico byte a byte
  con el código anterior, y esos planos conservan su caché.
- **En la web:** el buscador del plano distingue «Globo del plano (.icp)» y «.icp · posición
  aproximada» (planos limpios) de «OCR · sin verificar». Las revisiones guardadas prevalecen.
- **Comprobaciones:** 419 tests de backend, 32 pruebas de la consulta de pieza y plano en el
  navegador, Ruff, mypy, compilación y lint del frontend. No hay cambio de contrato de la API.
- **Pendiente:** verlo en la web con sesión iniciada, y el índice por SharePoint con un `.icp`
  real (probado con Graph simulado).

**«Ajustar marcas» (5.4): no se hace en esta ejecución.** El editor previsto mueve, gira,
voltea y escala las marcas. De los 25 planos situados ninguno lo necesita, y a los 5 sin situar
les falta la asociación (qué `.icp` o qué página), no un ajuste. Lo que sí aportaría es poder
**elegir a mano el `.icp` y la página**, o que la app reconozca copias idénticas en otras
carpetas. Queda como propuesta, sin implementar.

### Tanda 4 (16/11/2026): componentes implementados

- Identidad de base de datos: pieza + componente + código original + revisión. La migración
  `m84b70daef52` conserva las cotas anteriores en el componente predeterminado; no reasigna
  medidas ni vínculos históricos. Los selectores y series usan `BASE:N16` / `TAPA:N16`.
- «Organizar por componentes» en la ficha guardada: nombres libres, propuestas de hojas
  explícitas, asignación persistente de hojas y archivos, revisión de cada plano. Las piezas
  simples mantienen su lectura automática. Una fuente sin asignación inequívoca queda pendiente.
- Los planos se seleccionan por componente y revisión; si hay varios se elige en la consulta.
  Los CAD/escaneos asignados se añaden a la lista de ficheros, aunque no fueran el principal.
- Claves y asignaciones de fuentes ya importadas no se eliminan silenciosamente: requieren
  migración de procedencia. El nombre visible y la asociación de planos sí se pueden cambiar.
- Ensayo de los cuatro informes reales del 3288, sin escribir en la BD de trabajo:
  20.189 observaciones de BASE y 12.659 de TAPA; las 12.659 de TAPA conservan valor,
  nominal, tolerancias y estado de procedencia. `DR(tapa)param` queda pendiente si no se asigna.
  Evidencia: `out/plan-2026-11-16/components-real-3288.json`.
- Comprobado: migración en PostgreSQL aislado, pruebas API de identidad, historial, gráficas
  y actualización idempotente; prueba de Excel compartido; selección de plano por componente
  y revisión; guardar y reabrir organización en navegador. Cliente TypeScript regenerado.
  Comprobación final conjunta al terminar la tanda 5: 430 tests de backend correctos.
  Sin migración ni importación en la BD de trabajo.

### Tanda 5 (16/11/2026): alcance ejecutado y límites

**5.1 Hojas omitidas.** Inventario completo de las **461** hojas del alcance (364 por nombre y
97 por estructura), cruzado con celdas, perfiles y `celda_aleatoria` de la biblioteca en solo
lectura. No son 461 formatos distintos. Resultado por archivo/hoja:

| Decisión | Hojas |
|---|---:|
| Plantilla sin valores en la columna nominal: excluir | 77 |
| Comparativa: conservar como documento, no como medición nueva | 21 |
| Informe con valores: candidato a importar tras adaptar y verificar su formato | 135 |
| Formato o identidad aún no resueltos | 216 |
| Fórmulas aleatorias: pendiente de procedencia | 7 |
| Bloques con contextos secundarios: pendiente de separación | 5 |

Las 39 `Template` están entre las vacías. Las 87 `FULL_SPC` tienen nominales: **no** se excluyen
solo por su nombre. Las siete hojas con fórmulas aleatorias son `DR_100%_Setting 3 (2)` del 3174
(9 celdas por hoja); ausencia de `RAND` no certifica el resto. El inventario, evidencias y
clasificación reproducible están en `out/plan-2026-11-16/omisiones.json`, generado por
`prototypes/data-explorer/auditar_omisiones.py`.

Las tablas pendientes y las filas rechazadas (motivo y primeras localizaciones) quedan en
`Part.last_read` y en la API de lectura, incluso si se incorporó otra parte del archivo.
**La ficha no las muestra:** Eduard retiró el informe de lectura de la GUI por verboso
(confirmado el 17/11/2026). Excluir una plantilla vacía no provoca por sí
solo un estado parcial. No se han habilitado en bloque los 135 formatos candidatos: su
adaptación y validación siguen pendientes. Este paso cierra el inventario y la visibilidad,
no la cobertura de todas las mediciones.

**5.2 No./N°.** Reimplementado en el backend, tras ajustar el prototipo; índice `drawing-v5`.
Los números siguen siendo «OCR · sin verificar». Sobre OCR guardado de 8 documentos, backend
y prototipo coinciden en número y posición; se eliminan las 14 ubicaciones incorrectas
revisadas del 3174/3186 y no se pierde ninguna lectura de esas muestras marcada como correcta.
Las propuestas pasan de 326 a 283 en 3174 y de 319 a 279 en 3186. Los controles negativos
de ese ensayo no ofrecen marcas No. No es una validación independiente.

Lectura completa nueva de los tres PDF de método del 3186: `E040215_06` da 172 marcas después
de excluir 7 referencias a notas; `E1133806…` da 36 y `E507287_008` da 37 (otras 7 referencias
a notas excluidas). Se aplicó la última guarda de cifras significativas a las lecturas recién
calculadas, sin repetir el OCR. En una muestra visual fija de 16 del primero, 14 eran números
de cota correctos y bien situados, y 2 eran notas que la guarda elimina. Evidencia:
`out/plan-2026-11-16/no-live.json`, `no-backend.json` y `no-live-sample.png`.

Límites: tres o cuatro cifras significativas (100–9999), mínimo 20 marcas por documento,
lectura horizontal y vertical, filtro local de vistas/notas. Puede omitir marcas junto a una
anotación y no cubre todos los giros. El OCR completo de estos PDF tardó aproximadamente
5,5 / 1,6 / 1,5 minutos. No se promete cobertura total ni se modifica el lector de globos.

**5.3 Letras.** Tabla por pieza con procedencia en [ingesta automática](ingesta-automatica.md#identificadores-con-letras-16112026).
Se corrige la simplificación «3056 = repeticiones»: aparecen también ejes, diámetros y lados.
No se convierten en cotas numéricas ni se admiten automáticamente zonas o elementos auxiliares.
El JSON del inventario conserva el literal y una celda de evidencia por identificador.

**5.4 Ajustar marcas.** Se mantiene la decisión medida de la tanda 3: no implementarlo ahora.
Los 5 fallos pendientes de `.icp` requieren resolver la asociación, no girar o desplazar marcas.

**Pendientes que requieren datos o una ampliación:** A28/3226; interpretar los formatos y
los identificadores aún no resueltos; asociar los cinco planos `.icp` pendientes; comprobación
con sesión corporativa y Graph real. Los puntos declarados fuera de la entrega siguen fuera.
Las migraciones y pruebas se ejecutan en la pila aislada, no en la BD de trabajo.

### Comprobación final y entrega (16/11/2026)

- **Backend:** 430 tests correctos (86 s) en PostgreSQL `app_test` aislado. Ruff correcto y
  mypy sin errores en 91 archivos. Incluye cambio de carpeta, fuentes sin componente,
  revisiones distintas dentro de un Excel y búsqueda de cotas cualificadas.
- **Frontend:** compilación y lint correctos; 40 pruebas de navegador de editor y consulta
  de pieza/plano; una prueba adicional de selección por componente y revisión. Se comprueba
  guardar y reabrir la organización y conservar la consulta del historial. Son pruebas con
  API simulada, complementadas con las pruebas de API anteriores; no una sesión corporativa.
- **Prototipo:** 200 tests y 17 subtests correctos. Se conserva el lector de globos.
- **Datos reales:** cuatro informes del 3288; inventario de las 461 hojas; reproducción del
  lector No. sobre ocho documentos y OCR nuevo de tres PDF. Las cifras y límites figuran arriba.
- Cambios sin commit ni push. Parches de revisión en `out/plan-2026-11-16/tanda-1.patch`
  hasta `tanda-5.patch`. La tanda 5 incluye los ajustes finales de componentes encontrados
  en la comprobación conjunta. La pila de prueba se detiene al terminar; la BD de trabajo,
  los originales y `.env` no se modifican.
- En ese cierre todavía faltaban la migración y la reconstrucción de la instalación de
  trabajo. Se ejecutaron después, por indicación de Eduard; véase la activación siguiente.

### Activación en la instalación de trabajo (16/11/2026)

- Backend y web reconstruidos; migración `m84b70daef52` aplicada. Copia previa de PostgreSQL
  en `C:/Users/eduard.almar/.codex/backups/inteplast/20261116-164010/app-before-components.dump`,
  con archivo verificado. `.env` y originales sin modificar.
- Solo se ha añadido el **3288**. Siguen las piezas anteriores 3197 y 3212; las seis tablas
  de datos previos conservan sus recuentos y hashes, excluyendo las nuevas filas del 3288.
  No se han poblado las 21 piezas. El nombre `SOP oval RCP 3.1` se eligió desde su documentación;
  la carpeta se llama `3288`, y el lector no deduce automáticamente ese nombre completo.
- 3288: **138 cotas BASE y 117 TAPA**, 98 grupos importados; 20.189 observaciones BASE y
  12.695 TAPA (incluidas 36 de `DR(tapa)param`). Actualizar de nuevo: 0 grupos nuevos,
  98 sin cambios. Los informes dan la revisión numérica como `1.0`; esa etiqueta se ha
  usado también en la asignación de sus planos, sin cambiar las revisiones originales.
- Planos asignados manualmente en REV.01: BASE `BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf`
  y TAPA `BSG-296-2 SOP RCP 3.1 balloned.pdf`. Índices comprobados mediante la API de la app
  con Graph real: listos, 141 y 120 marcas `.icp`, sin posición aproximada. La consulta
  mantiene `BASE:N16` y `TAPA:N16` separadas. Esta configuración no acredita selección
  automática general del plano o su revisión.
- Se ha cambiado el principal del 3288 al plano de BASE con globos. La propuesta anterior
  era el primer PDF por orden alfabético, un plano limpio. Se conservan los 10 PDF vinculados
  (5 de conjunto, 3 de BASE y 2 de TAPA). La estrella es única por tipo y pieza; las cotas
  usan los planos asignados a su componente. Mejorar la elección inicial sigue pendiente.
- La lectura conserva sus incidencias: fila 32 de `DR(tapa)` con tolerancias invertidas
  en cuatro informes y 38 documentos de correcciones pendientes de interpretación.
  Por decisión de Eduard, el detalle permanece en `Part.last_read` y en la API de lectura;
  se retira de la GUI, sin marcar artificialmente la lectura como completa.
- Se comprobó el acceso Microsoft y la consulta del 3212 antes de interrumpir el uso de
  su navegador. Desde entonces, las comprobaciones y el despliegue se hacen en segundo
  plano, por petición de Eduard. No se afirma una revisión visual completa de la app real.
- Interfaz de componentes compactada conforme a Features. Pruebas de editor en navegador
  sin ventana: **9/9**, incluidos guardar/reabrir componentes, móvil, lectura diferida,
  actualización y retirada del diagnóstico al terminar una lectura parcial. Compilación
  y lint correctos (permanece un aviso informativo anterior en la fixture del asistente).

### Rectificación: ninguna selección manual del agente (16/11/2026)

Eduard indica que el agente no debe rellenar ni corregir fichas por su cuenta para
compensar fallos del algoritmo. **Esta instrucción prevalece sobre la práctica de la
activación anterior.** Queda recogida en `AGENTS.md` y `CLAUDE.md`.

- **Revertido el cambio de estrella del agente.** El 3288 vuelve al principal que propuso
  el descubrimiento: `1- 2D y 3D pieza/Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf`.
  La elección alfabética sigue pendiente de corregir. No se ha seleccionado otro plano.
- **Intervenciones anteriores identificadas:** el nombre `SOP oval RCP 3.1`, el cliente
  `B. Braun`, la organización BASE/TAPA, sus hojas, CAD y planos REV.01 con revisión `1.0`
  fueron introducidos por el agente. Las 255 cotas del 3288 se importaron después de esa
  configuración. Son una prueba de importación con configuración manual, no del flujo
  automático completo desde carpeta. Estas asociaciones y las medidas no se han borrado
  en la rectificación de la estrella; ya forman parte de la procedencia de los datos.
- En adelante, dejar que el algoritmo produzca sus propuestas aunque sean incorrectas;
  registrar y corregir el problema general. Cuando los datos no permitan resolverlo,
  documentar las convenciones necesarias para INTEPLAST o permitir que el usuario elija.
  El agente no debe tomar esa decisión por el usuario ni preparar fichas para aparentar
  que la ingesta es generalizable.

**17/11/2026: 3288 retirado de la BD de trabajo**, por indicación de Eduard, que lo creará él
desde la web para probar el flujo real. Borrados la pieza, sus 98 importaciones, 255 cotas,
19 referencias a archivos y la portada generada; los originales no se tocan. La web no permite
borrar una pieza con cotas, así que se hizo por SQL en una transacción con comprobación de
recuentos: 3197 y 3212 quedan igual. Copia previa en
`C:/Users/eduard.almar/.codex/backups/inteplast/20261117-084058/app-before-deleting-3288.dump`.

**Siguiente trabajo de carpeta:** mejorar la propuesta de plano principal y documentar con
INTEPLAST las convenciones de entrega una vez contrastadas las reglas generales. Mantener
las excepciones de componentes como asignaciones manuales reutilizables; no presentarlas
como clasificación automática resuelta.

**Resuelto el diseño del 3288:** una ficha con componentes separados. El análisis anterior está en
([ingesta automática §1.5](ingesta-automatica.md#15-diferencias-con-el-piloto-3212-12112026)).
Las diferencias de todas las piezas respecto al 3212 están en
[comparativa](../conocimiento/comparativa.md#respecto-al-3212-la-referencia-de-la-app).

## Login de Microsoft sin copiar y pegar: hecho (09/11/2026)

Era la tarea acordada el 30/10/2026. **Eduard confirma el 09/11/2026** que la dirección de
retorno Web `http://localhost:8000/api/v1/login/microsoft/callback` ya está registrada en Entra
y que ha entrado en la aplicación final con su cuenta de Eurecat, sin Postman ni copiar enlaces.
El `.env` local tiene `MICROSOFT_REDIRECT_URI` con esa dirección y `SHAREPOINT_ENABLED=true`
(comprobado el 09/11/2026). La prueba no se repitió en esa sesión: Docker estaba parado.
La URI de `localhost` sirve para la instalación de desarrollo; en el servidor habrá que
registrar su URL HTTPS.

**Lectura de archivos reales por Graph: comprobada el 12/11/2026** sobre el OneDrive de Eduard.
El backend en marcha tenía `SHAREPOINT_ENABLED=true` en su entorno, y sus registros muestran
peticiones a `graph.microsoft.com` respondidas con `200 OK`: el listado de `4- Tetones/3288`
y los metadatos del plano, la pieza, el molde, el escaneo y el Moldflow del 3212, entre otros.
La caché de descargas (`/app/uploads/sharepoint`) guarda dos STEP descargados el 30/10/2026.
Sus tamaños coinciden byte a byte con los originales:
`3212…/20200204_3 130 516 987_AllCATPart.stp` (10.549.640 B) y
`3197 Pot/…/20230404_0140S00363_SPT_001.stp` (6.343.383 B). El recorrido de carpetas al crear
una pieza (`POST /parts/discover`) también pasa por Graph: el código usa `sharepoint.walk`
cuando el interruptor está activo.
`SHAREPOINT_DRIVE_ID` está vacío: las pruebas apuntan al OneDrive de quien inicia sesión, no a
una biblioteca compartida. Para la fase 2 hay que rellenarlo junto con `SHAREPOINT_ROOT_PATH`.
Las rutas guardadas en la BD son relativas a esa raíz, así que `Exemples` debe conservar la
misma estructura bajo la raíz nueva.

## Próxima sesión de la app final: usuarios y prueba real de archivos

El servidor de Eurecat ya sirve la web por HTTPS interno. Eduard ha comprobado el inicio
de sesión con Microsoft y la lectura de PDF y CAD. Queda repetir la prueba con un segundo usuario.
[Despliegue en servidor interno](despliegue-servidor.md).

**Fases fijadas por Eduard el 09/11/2026:** 1) pruebas con cuentas de Eurecat; 2) servidor de
Eurecat, cuentas de Eurecat y SharePoint de Eurecat; 3) traslado a los servidores de INTEPLAST.
Las fases 1 y 2 no dependen de A10; la 3 sí.

- En Eurecat, Eduard entra con Microsoft y administra las altas por correo desde **Admin**.
  Para la fase 3, pedir el correo de la persona designada por INTEPLAST y verificar con ella
  el [traspaso de administración](despliegue-servidor.md#primer-administrador-de-inteplast).
- Probar el listado y la apertura de los originales con el segundo usuario. La biblioteca
  compartida y los permisos de INTEPLAST siguen pendientes de concretar para la fase 3.

Detalle técnico: [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph).

## Prioridad a corto plazo (28/10/2026)

Eduard fija estos tres frentes como los siguientes:

| Tarea | Próximo paso | Referencia |
|---|---|---|
| SharePoint: primera prueba real | Login real el 30/10; **retorno automático, sin copiar y pegar, confirmado el 09/11**. Lo siguiente: administrador corporativo, permisos, listado, visores, alta y actualización ([próxima sesión](#próxima-sesión-de-la-app-final-usuarios-y-prueba-real-de-archivos)) | [SharePoint](ficheros-externos.md#sharepoint-microsoft-graph) |
| Validar el conocimiento: fichas, biblioteca SQL y RAG | Prueba en una sesión sin contexto: preguntas de desarrollo, respuestas con fuentes y registro de lagunas, sin recorrer los originales. Ya hay una evaluación de recuperación con 55 preguntas (27/10/2026); faltan preguntas reales de INTEPLAST | [Entrada a conocimiento](../conocimiento/README.md#entrada-para-una-sesión-sin-contexto), [evaluación](../conocimiento/rag/README.md) |
| Localizar cotas en el plano 2D | **En la aplicación desde el 30/10:** el índice del plano usa el lector del prototipo (capa vectorial o imagen globo a globo, detector en dos pasadas, RapidOCR + lector propio en ONNX, un número por plano, umbral provisional 0,434 vectorial / 0,6072 imagen). Reproduce exactamente las lecturas del prototipo en 5 planos reales. Prototipo congelado: no se ajusta más sin evidencia nueva. Pendiente: que Eduard verifique la referencia del 3167 (`muestra_verificacion.py`) y medir con planos nuevos de INTEPLAST, apartados antes de ajustar nada. Abiertos: el 3202 «G» (negritas), las lecturas ofrecidas sin verificar, globos grises o negros, numeración del cliente en negro (2820, 3214, 3174), y búsqueda por valor (3051, 3197). **El `.icp` está en la app desde el 16/11/2026** ([tanda 3](#resultados-de-la-tanda-3-16112026)). Los lectores nuevos (`[]`, `No.` y recuadros) se prueban primero en el [visor de `conocimiento/`](#visor-de-conocimiento-banco-de-pruebas-antes-de-la-app-final); no están en la app | [Lector de globos](cotas-y-evidencia-web.md#lector-de-globos-30102026), [prototipo](../prototypes/data-explorer/README.md#correspondencia-globo-a-globo-y-ensayo-de-umbrales-29102026), [planos con globos](../conocimiento/planos-globos.md) |

## Visor de `conocimiento/`: banco de pruebas antes de la app final

**Aclarado por Eduard el 09/11/2026.** Antes de cargar las 21 piezas en la aplicación final,
Eduard usa el [visor de `conocimiento/`](../prototypes/data-explorer/conocimiento/README.md)
(`prototypes/data-explorer/conocimiento/app.py`, http://127.0.0.1:8765) como aplicación de
pruebas con todas las piezas. Ahí se prueban también los lectores de planos antes de llevarlos
a la app. Cuando Eduard habla de «la app de conocimiento» se refiere a este visor.

Pasar algo a la app final significa **reimplementarlo** en `backend/app/ingestion/` con sus
tests: la app no importa ni copia el prototipo (separación de producto, `CLAUDE.md`).
**Primero se termina el visor** (Eduard, 09/11/2026). Terminado, sirve para enseñar sus resultados a
INTEPLAST, con cada error respaldado por escrito; lo que ya está en las preguntas a INTEPLAST no se repite.

Estado el 09/11/2026: 26 lecturas de planos sin `.icp` y 21 capturas CAD ya generadas en
`out/conocimiento/`. Los lectores de planos del visor y de los scripts de medida son ya un solo
código, `prototypes/data-explorer/lectores_planos.py`, sin cambiar ninguna lectura
([detalle](../prototypes/data-explorer/README.md#un-solo-código-de-lectura-de-planos-09112026)).
Tests: 97 del visor (`tests/test_visor_conocimiento.py`) y 18 de los lectores
(`tests/test_lectores_planos.py`), dentro de los 174 del prototipo, todos correctos. Las mediciones
de `probar_lector_planos.py` anteriores al 09/11 son histórico, con puntuaciones redondeadas; las
nuevas, con puntuación completa, van a una carpeta nueva.
Pendientes: [visor, pendiente](../prototypes/data-explorer/conocimiento/README.md#pendiente-09112026).

<a id="1-correcciones-de-otras-piezas-en-espera-de-ejemplos"></a>
## 1. Ingesta de otras piezas: validar casos y resultados

**Ejemplos recibidos y contrastados.** Las 21 piezas tienen [balance por fichero y hoja](../conocimiento/ingesta/README.md), y el piloto de ficha 3167 está validado técnicamente. Usar estos contratos al ampliar el lector; las correcciones XLS/PPTX de la aplicación siguen limitadas al piloto 3212.

Las protecciones de fórmulas aleatorias/sin caché, firma de contenido, variantes PPAP y bloques secundarios ya están en producción local, con exclusión por celda y procedencia visible. La biblioteca y la aplicación mantienen lectores independientes. Las lecciones están contrastadas documentalmente y preparadas para revisión corporativa; no se han cargado en la app.

Detalle y criterios para avanzar: [hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx),
[contrato actual](cotas-y-evidencia-web.md) y [propuesta de ingesta](ingesta-automatica.md).
La consulta al cliente debe centrarse en contrastar los casos y su elaboración (A13/A14),
no en pedir otra vez los ejemplos ya disponibles.

<a id="2-asistente-copilot-de-empresa-junto-con-el-servidor-trabajo-futuro"></a>
## 2. Asistente: prueba local con Codex antes del servidor; Copilot definitivo

**Decisión expresa de Eduard (17/11/2026): Ollama descartado. La solución final será
Copilot de empresa mediante un agente conectado a la API de la app.** Sustituye la
preferencia provisional del 09/11 y el plan de mantener Ollama mientras tanto.

Antes de llevar la app al servidor, hacer una **prueba de concepto en este PC con Codex
(ChatGPT), usando el modelo más rápido disponible como motor de fondo**. No crear
un agente para esta prueba: simular cómo consultaría y respondería un agente conectado a la API
de la aplicación. Codex sirve para salir del paso y evaluar respuestas, fuentes y latencia;
es provisional y local, no la solución de producción.

**Integrado el 18/11/2026, después de A–E.** Puente local de Windows con `codex exec`, modelo
`gpt-reserve` y esfuerzo `low`; mismo frontend y lecturas del backend. La búsqueda por palabras
sustituye la dependencia semántica de Ollama en esta prueba. Pasan 83 pruebas aisladas;
resta evaluar la calidad con preguntas representativas. Arranque y límites en el
[puente Codex](../integrations/codex-bridge/README.md). Después, acordar con IT
la integración final de Copilot, sus permisos, usuarios simultáneos y límites. No pedir
Ollama ni dimensionar el servidor para ejecutar sus modelos.

Alcance y estado en [decisión del asistente](asistente.md#decisión-de-eduard-17112026)
y [concurrencia y despliegue](asistente.md#concurrencia-y-despliegue).
Los acuerdos de IT constan en el [acta del 24/09](acta-reunion-2026-09-24.md).

## 3. Otras tareas abiertas

| Tarea | Próximo paso | Referencia |
|---|---|---|
| ~~Borrar pieza con sus datos, desde la web~~ | **Implementado el 17/11/2026** con pruebas en BD aislada y en el navegador. Falta probarlo en la instalación local con una pieza real | [Alcance y cierre](#borrar-pieza-con-sus-datos) |
| Adjuntos del feature que no siguen a la pieza | Definir cómo actualizar el vínculo sin perder cotas ni configuración de portada | [Origen del CAD](portadas-cad.md#origen-del-cad-de-la-portada) |
| Captura de pieza tras cambios en Graph | **Corregida el 30/10:** la versión del origen invalida la captura en backend y navegador; probada con Graph simulado. Pendiente comprobar la conexión real | [Cambios remotos y miniatura](portadas-cad.md#cambios-remotos-y-miniatura-de-pieza) |
| ~~Lector de comparativas CSV del backend (`measurement_tables.csv_rows`)~~ | **Corregido el 16/11/2026** ([tanda 1](#resultados-de-la-tanda-1-16112026)). Encontrado el 09/11 al cargar el 3197 en la biblioteca: asignaba los POINT de las comparativas del 3212 a N178 (título en la misma línea que el primer valor), dejaba sin tolerancias la comparativa del 3197 `.03` y no reconocía `3197_totes_nozzle 55/65.csv` | [3197](../conocimiento/0-bolt-eye/3197.md#csv-de-la-cmm-en-la-biblioteca-09112026) |
| Política de finales de línea | Propuesta LF y procedimiento escritos el 04/11; los aplica Eduard con la copia limpia | [Desarrollo](../development.md#finales-de-línea-propuesta-del-04112026-sin-aplicar) |
| Volcado OAuth en el historial de Git | Retirado de `TODO.md` el 04/11 (el código era de un solo uso y ya caducado). Sigue en el historial desde `a6f3b44`; reescribirlo o no lo decide Eduard | — |

<a id="borrar-pieza-con-sus-datos"></a>
### Borrar pieza con sus datos (implementado el 17/11/2026)

Añadir una acción de administrador para eliminar una pieza con sus cotas, mediciones e
historial importado, componentes y registros derivados propios, sin recurrir a SQL.
Actualmente el backend rechaza el borrado si conserva cotas, importaciones, documentos
de evidencia o vínculos con features, incluso para administradores.

- Antes de borrar, mostrar la pieza y el alcance de los datos afectados y pedir confirmación.
- Gestionar explícitamente sus vínculos con features, conservando los features y el
  conocimiento compartido. No eliminar silenciosamente datos de otras piezas.
- Conservar las carpetas y archivos originales de INTEPLAST, tanto locales como en SharePoint,
  y cualquier documento compartido. Eliminar solo los datos propios de la pieza en la app.
- **Cierre:** borrado completo desde la web con permisos comprobados en el backend;
  pruebas en una base aislada de cancelación, rechazo a usuarios no administradores,
  conservación de originales y de otras piezas/features, y ausencia de registros huérfanos.

**Hecho el 17/11/2026.** Ficha de pieza → **⋯ → Eliminar**, solo administradores. Detalle en
[app-web](app-web.md#borrado-de-una-pieza-17112026).

- **Alcance:** `GET /parts/{id}/deletion` dice qué se elimina (cotas, mediciones, documentos
  propios, ubicaciones revisadas, asignaciones y adjuntos en features, portadas 3D afectadas)
  y qué se conserva (originales, features, documentos que usa otra pieza). Hay que escribir
  el código de la pieza para activar el borrado.
- **Confirmación:** el borrado lleva la clave del alcance revisado; si los datos han cambiado,
  se rechaza con `409` y el diálogo vuelve a cargar el alcance.
- **Originales:** no se tocan. De la app se borran las referencias que solo usaba la pieza y,
  si eran subidas, sus bytes.
- **Comprobado:** backend completo en BD aislada, 447 pruebas correctas (con las de componentes,
  `.icp` y las 7 de regresión de la revisión externa del mismo día), incluidas las nuevas
  de alcance, rechazo a no administradores, clave falsa o antigua, conservación de original,
  documento compartido, otra pieza y features, y ausencia de huérfanos. En el navegador,
  `piece-editor.test.cjs`: la acción no aparece a un usuario normal y el administrador
  confirma escribiendo el código. Componentes del frontend: 157 pruebas, 156 correctas y
  1 omitida (la opcional del diálogo de Windows). `ruff`, `mypy`, Biome y `tsc` sin errores.
- **Pendiente:** probarlo en la instalación local con una pieza de prueba (no se ha borrado
  ninguna pieza real). La cancelación se comprueba en la interfaz (sin clave no se borra nada);
  no hay prueba específica de pulsar Cancelar.

## Hecho el 20/10/2026

Registro histórico de aquella sesión; estas pruebas no se han repetido el 26/10.

- Buscador del plano: cada resultado indica su origen («Revisada», «Texto del PDF» u «OCR · sin
  verificar») y se avisa cuando hay propuestas OCR.
- Series de informes XLS de otras piezas: ya no reciben las etiquetas del piloto 3212
  (`describeSeries`), con test de regresión.
- Limpieza: tres componentes y tres exportaciones sin uso eliminados; test obsoleto del menú
  «Opciones de la pieza» trasladado a la ficha de pieza.
- Documentación: ficha de pieza como lugar de los archivos, portada CAD, concurrencia del
  asistente y estado de la generalización de correcciones.
- Comprobaciones: compilación, Biome y 141 tests de componentes (140 correctos, 1 omitido: el
  opcional del diálogo de Windows).
