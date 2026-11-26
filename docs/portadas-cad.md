# Portadas de features y piezas desde el CAD

**Estado contrastado con el código el 26/10/2026.** Esta ficha es la referencia de miniaturas,
selección de caras y persistencia de portadas. Los visores de archivos se describen en
[ficheros externos](ficheros-externos.md#visores-de-archivos), y los GLB de modelos grandes
en [vistas 3D](vistas-3d.md). Las verificaciones fechadas al final son antecedentes;
no se han repetido en esta revisión documental.

## Una portada por pieza (19/11/2026)

Desde la migración `p27ea3fbd174_feature_part_covers.py` la portada del feature es **una por
pieza**: la captura y, si se hizo sobre el CAD, sus caras y su encuadre se guardan en
`FeaturePartLink.image_id` y `FeaturePartLink.cover_3d`. Decisiones y alcance en el
[plan de portadas por pieza](plan-portadas-por-pieza-2026-11-18.md).

- **Qué se ve de cada pieza:** su captura propia; si no tiene, la captura automática de su CAD
  en gris. Si tampoco hay CAD, se muestra el icono de imagen. Para selecciones compatibles
  se prepara progresivamente la captura en el color del feature con su cámara guardada.
- **Ficha:** carrusel de 300 px (192 px en el móvil), sin nada debajo. Con una pieza, solo su
  código arriba a la izquierda. Con varias, además `n / N` arriba a la derecha, flechas a los
  lados (al pasar el ratón o enfocar; siempre en táctil), ← / → y deslizamiento con el dedo.
  `n / N` es texto, no abre ninguna lista. La modal tiene el mismo carrusel; el código y la
  posición van juntos arriba a la izquierda porque la derecha es de **Encuadrar**. La modal
  carga la geometría de la pieza visible. Cambiar de pieza o cerrar cancela esa carga en el
  navegador. Si el servidor ya estaba preparando la vista, termina el trabajo para la próxima visita.
- **Lista y cuadrícula:** la captura corresponde a la primera pieza de la ficha (`part_order`
  y luego el código). Si le falta imagen, la tarjeta muestra el icono aunque otras piezas tengan
  captura. Con dos piezas o más, la portada y las dos capas de detrás son cuadradas, con fondo
  blanco y borde gris oscuro en ambos temas. El contador indica cuántas piezas hay.
- **Imagen del feature sin pieza** (`Feature.image_id`): solo se muestra mientras el feature no
  tiene piezas. La migración no la asigna a ninguna pieza.
- **API:** `PUT /features/{id}` guarda la cabecera y las portadas cambiadas
  (`part_covers`: pieza, `image_id` o nada para volver a la captura del CAD, y `cover_3d`
  opcional) en **una sola transacción**: si una portada falla, no se guarda nada. La respuesta
  se prepara antes del `commit`, así que un fallo de SharePoint tampoco deja nada a medias.
  Al aplicar una portada, el borrador conserva el código de la pieza. Antes de guardar, la
  ficha relee el feature. Si otro usuario ha retirado la pieza, el aviso muestra ese código
  incluso si la lista de piezas ya se ha actualizado. Se descarta su borrador y el reintento
  guarda el resto. Si la retirada coincide con el envío, el servidor responde **409** y
  la ficha vuelve a comprobar qué piezas siguen vinculadas antes de mostrar el aviso.
  Guardar portadas, vincular o desvincular piezas y añadir, quitar o cambiar adjuntos
  comparten el bloqueo del feature. `cover_3d` suelto en el feature (pestaña de la versión anterior) se
  rechaza con **422**. `FeaturePublic` añade `cover_image` y `part_count`; `FeatureDetail`,
  `part_covers` (una por pieza, con su captura automática aunque haya portada propia).
- **Orden:** lo decide el servidor (`part_order` y luego el código en orden natural: P2 antes
  que P10). La tarjeta usa la primera y el carrusel sigue `part_covers`.
- **Desvincular** quita la portada de esa pieza (su vínculo) y conserva el fichero subido. Al
  volver a vincularla empieza sin portada propia. El borrador sin guardar de esa pieza se
  descarta cuando el servidor confirma la desvinculación.
- **Deslizar** cambia de pieza en la ficha y, sobre una imagen, en la modal; sobre el 3D el
  gesto gira la pieza.
- **`Feature.cover_3d`** ya no se lee ni se escribe. Se mantiene una tanda para que el
  `downgrade` sepa en qué pieza estaba la portada.

## Piezas (22/09/2026)

El catálogo y `/parts/{id}` comparten la captura del STEP completo con todas sus selecciones
compatibles. La versión en gris sirve de respaldo a los features sin captura propia.
Se reutilizan la geometría preparada, los controles, `FeatureThumbnail`,
`CoverButton`, `CoverDialog` y `StepCoverCanvas`. Las capturas nuevas se calculan una a una
y se guardan para que volver al catálogo no vuelva a cargar todos los STEP.
El indicador de preparación incluye el tiempo de espera en la cola. Una pieza sin CAD
principal queda con el icono de imagen y no entra en la cola.

El editor muestra la captura automática de la pieza en la pestaña Imagen cuando falta una
portada propia. Si la pieza tiene varios STEP vinculados al feature, el selector de CAD permite
aplicar un componente entero o marcar sus caras. La elección guardada pertenece a ese feature.
La comprobación de las caras vacías en los STEP de 3056, 3167 y 3288 se recoge en el
[informe del catálogo](comprobacion-step-catalogo-2026-11-19.md).
El navegador genera el PNG a partir de la geometría y admite portadas de STEP/STP de hasta
**50 MiB**. Puede cargar el motor 3D al entrar en el catálogo si faltan capturas. No hay editor manual de
imagen ni selección de caras para la pieza: su portada abre la consulta 3D incluso al editar.

`PUT /parts/{id}/cover` comprueba el CAD actual, su versión y SHA-256. La imagen derivada
se asocia a la pieza; cambiar el CAD invalida la portada anterior. El CAD se obtiene de
las referencias de la pieza o, para registros antiguos, de sus adjuntos en Features.
Pulsar la portada abre el 3D interactivo completo, con giro, zoom y encuadre.

## Uso

En el feature, pulsar la portada en **Editar** (también si está vacía) abre **Editar portada**
de **la pieza visible** en el carrusel. Con varias piezas, la cabecera de la modal lleva
`‹ código n / N ›`: **Aplicar** guarda un borrador de esa pieza y deja la modal abierta para
pasar a la siguiente. **Guardar** en la ficha envía todos los borradores; **Cancelar** en la
ficha los descarta todos. La pestaña **Imagen** admite:

- Clic para seleccionar una imagen del ordenador.
- Arrastrar y soltar una imagen.
- Pegar una imagen con **Ctrl+V**, fuera de los campos de texto.
- **CAD**, en la misma ventana, usa el STEP de la pieza visible
  ([origen del CAD](#origen-del-cad-de-la-portada)). No se abre otra modal encima. Ya no hay
  selector de pieza; solo aparece un selector de archivo si esa pieza tiene varios STEP.

El editor CAD permite marcar varias superficies con clics, quitar una marca
con otro clic y limpiar la selección con el icono de borrador junto a **Encuadrar**.
Las miniaturas automáticas nuevas usan siempre proyección ortográfica. Se reutilizan
las miniaturas anteriores en perspectiva mientras correspondan al mismo CAD y, en las
coloreadas, a la misma selección y colores. Cambiar las preferencias del visor solo
actualiza la cuenta. El editor usa la proyección elegida en Ajustes de usuario. Los
encuadres nuevos guardan la altura visible. Al abrir uno antiguo se recupera su escala
en el plano de enfoque.
Arrastrar con la rueda pulsada gira alrededor del centro de la pieza, incluso en una
vista de detalle. Rodar hacia la pantalla acerca la zona bajo el cursor y rodar hacia
el usuario la aleja. Ctrl más arrastre con la rueda pulsada desplaza la vista. **Encuadrar**
recupera la vista inicial. **Aplicar** genera una imagen y la coloca en el borrador
de cabecera. Las imágenes elegidas, pegadas o arrastradas también requieren **Aplicar**.
**Cancelar**, la X o Esc en la modal descartan solo los cambios de esa apertura;
durante una subida se espera a que termine antes de aplicar o cerrar. **Guardar** en la ficha
persiste conjuntamente imagen y selección; **Cancelar** en la ficha descarta su borrador de
cabecera. Las notas, las piezas vinculadas y sus cotas mantienen su guardado en línea; los
archivos se editan en la ficha de pieza, con su propio **Guardar cambios**.

Si no hay ninguno, el editor indica «Vincula el CAD desde la ficha de la pieza» (o «Añade
una pieza que tenga un CAD vinculado» si el feature aún no se ha creado). Solo se ofrecen
archivos STEP/STP de tipo CAD asociados a una pieza. El editor
admite hasta 50 MiB; el molde y el escaneo simplificados conservan sus visores independientes.

Las tarjetas y la ficha muestran una imagen estática. En la ficha, toda la portada abre la
ampliación; el icono de 32 px aparece dentro, abajo a la derecha, al pasar el ratón o enfocar
con teclado, y permanece visible en pantallas táctiles. Las imágenes se amplían en la misma
modal; las portadas CAD activan automáticamente el 3D con sus marcas y encuadre, sin
selector imagen/3D. Solo hay una X de cierre arriba, además de Esc. La captura se conserva
mientras carga el CAD o si falla. Durante la carga aparece «Cargando modelo CAD…» con un
indicador animado pequeño, sin recuadro, en la parte inferior de la imagen.
Al apuntar a la portada CAD o enfocarla con el teclado, la ficha adelanta la carga del
código del visor. Al vincular un STEP de producto, el servidor prepara en segundo plano
un GLB con las aristas y los rangos de triángulos de cada cara. Las fichas antiguas
solicitan la preparación al entrar en la ficha. La cola, la validación de la versión y
el enlace de acceso son los de las [vistas 3D](vistas-3d.md).

La portada automática, la consulta y el editor comparten la geometría preparada.
La selección de cada feature sigue en su vínculo con la pieza. El visor comprueba
el archivo, su versión, el SHA-256 del STEP y la huella de la geometría antes de aplicar
las caras y la cámara guardadas. El GLB se reutiliza al recargar y entre usuarios con acceso.
Si SharePoint o una revinculación cambia el identificador de versión, el servidor comprueba
el SHA-256 del STEP autorizado. Cuando coinciden el contenido y la receta del conversor,
reutiliza el GLB guardado. Un cambio en los bytes del CAD genera una vista nueva.
Si falla la conversión, sigue disponible el lector STEP en el navegador para los archivos
admitidos por la portada.
Una ficha sin portada no abre una ampliación vacía.

La ampliación de piezas y features y el editor de portada comparten un diálogo de
92 % de ancho (hasta 1400 px en escritorio) y 90 % de alto. El visor ocupa el espacio
disponible entre la cabecera y las acciones. En el editor CAD, un marco delimita la
zona cuadrada que se captura al aplicar.
Los botones quedan a 12 px de la imagen, sin reservar una fila vacía para avisos.
El editor mantiene exactamente el mismo tamaño de modal y visor al alternar **Imagen/CAD**,
incluso mientras carga o si falta el STEP. No muestra los párrafos de instrucciones de la
versión anterior.

El editor abre **CAD** cuando ya existe una portada CAD, para retomar la selección.
Cambiar entre sus pestañas conserva las superficies seleccionadas durante esa apertura.
Elegir, pegar, soltar o quitar una imagen sustituye la portada CAD al aplicar y guardar la
cabecera. El pegado se limita a la modal y respeta los campos de texto.

## Persistencia y revisiones

La anotación (`cover_3d`, esquema `FeatureCover3D`) vive desde el 19/11/2026 en
`FeaturePartLink.cover_3d`, junto a su imagen en `FeaturePartLink.image_id`
([una portada por pieza](#una-portada-por-pieza-19112026)). Antes estaba en `Feature.cover_3d`
(migración `c84d70f6ab52_add_feature_cad_cover.py`).

Guarda el adjunto, la pieza, el documento y su versión, SHA-256 de los bytes del STEP, receta
del importador, huella de la geometría, superficies seleccionadas y cámara. El STEP original
no se modifica.

`PUT /features/{id}` (con `part_covers`) comprueba que la pieza es del feature, que la
selección es de esa pieza, que el CAD es un adjunto de esa pieza en ese feature, que está
disponible y que su versión y SHA-256 coinciden. Si algo falla no guarda nada. El esquema valida
selección no vacía, sin duplicados y cámara finita y válida. Editar otros campos del feature no
toca las portadas. Quitar el adjunto STEP (o cambiar su pieza, archivo o tipo) borra la selección
de caras de esa portada y conserva su imagen.

El navegador verifica además la huella de la geometría antes de aplicar índices de caras.
Los índices solo valen para esos bytes y esa receta: **no son identificadores estables entre
revisiones del CAD**. Si cambia el documento, la ficha conserva la imagen, pero exige revisar
la selección; el mismo icono **Limpiar selección** permite empezar sobre la revisión actual
cuando la anterior ya no es compatible. No hay una segunda acción «Nueva selección».
Al limpiar una selección válida se conserva el encuadre y no se vuelve a importar el STEP.
No se ha añadido
una correspondencia automática de caras ni un historial de originales.

El origen se resuelve mediante el UUID interno y enlaces autenticados. La integración
[SharePoint](ficheros-externos.md#sharepoint-microsoft-graph), incorporada el 22/10/2026,
mantiene este contrato y lee los bytes de la ruta vinculada; sigue pendiente su prueba real.

## Implementación

- `FeatureCoverEditor.tsx`: modal única y borrador independiente de imagen/CAD.
- `CadCoverEditor.tsx`: selección del CAD y captura dentro de esa modal.
- `CoverButton.tsx`: miniatura clicable compartida por consulta y edición.
- `CoverDialog.tsx`: ancho ajustado al cuadrado y filas de tamaño común a ambos editores.
- `prepareCoverGeometry.ts` prepara las mismas mallas y la misma huella en el conversor
  del servidor (`cover-glb.mjs`) y en el lector STEP del navegador (`cover.worker.ts`).
- `preparedCover.ts` lee los triángulos, las aristas y los rangos de caras del GLB.
  También resuelve la lectura del STEP si falla la preparación.
- `StepCoverCanvas.tsx`: caras de `occt-import-js`, selección por clic, cámara y captura PNG.
  Mantiene la teselación completa del STEP y comprueba las caras antes de aplicar la selección.
  Agrupa superficies consecutivas del mismo color para reducir las llamadas de dibujo.
- `FeatureCover.tsx`: carrusel por pieza (`CarouselFrame`, compartido con la edición) y
  ampliación de imagen/3D; carga diferida del visor al abrir.
- `coverSlides.ts`: qué muestra cada pieza y los borradores de edición sobre lo guardado.
- `FeatureCard.tsx` (`FeatureCoverStack`): pila con número en lista y cuadrícula.
- `feature_covers.py`: orden de las piezas, portada de cada pieza y de la tarjeta, guardado
  de todas o ninguna (`apply_cover_changes`) y limpieza al quitar adjuntos.
- `partUnlinked.ts`: aviso de desvinculación confirmada, para descartar el borrador.
- `cadCover.ts`: elegibilidad, identidad del documento y versión de la receta.
- `cad_covers.py`: validación del vínculo y de los bytes al guardar.

`occt-import-js` queda fijado a `0.0.23`. Al cambiar el importador o la teselación, hay que
actualizar la receta y revisar la compatibilidad de las selecciones guardadas.

## Origen del CAD de la portada

Desde el 22/09/2026 la ficha del feature no muestra ni edita archivos: se gestionan en la
ficha de pieza ([uso](ficheros-externos.md#uso-en-la-ficha-de-pieza)). El selector CAD de la
portada ofrece los **adjuntos de tipo CAD del feature** (`coverAssets` en `cadCover.ts`).
Esos adjuntos se crean al vincular una pieza al feature por primera vez, con **Añadir pieza**
o al crear la pieza con el feature seleccionado: se copian los archivos principales de la
pieza (CAD, escaneo, molde y plano), sin copiar bytes. El adjunto de plano es también el que
abre el plano desde la fila COTAS.

**Limitación conocida:** esos adjuntos no siguen a la pieza. Si después se cambia el CAD
principal en la ficha de pieza, el feature conserva el documento anterior y su portada sigue
ligada a él. La interfaz no tiene hoy una acción para actualizarlo; la solución funcional
queda como tarea separada. Desvincular la pieza y volver a vincularla copia los archivos
actuales, pero tiene dos efectos que no se recuperan al volver a vincular:

- Se retiran las cotas de esa pieza asignadas al feature.
- Se quita la portada del feature en esa pieza (imagen y selección), que vive en su vínculo
  (`unlink_feature_part` en `api/routes/features.py`). El fichero subido se conserva y las
  portadas de las demás piezas no cambian. Desde el 19/11/2026; antes se conservaba la imagen
  y se perdía solo la selección.

La portada de la pieza se selecciona a partir de su CAD principal actual. Su caché incluye
también el origen activo y la versión del contenido, como se explica debajo.

## Cambios remotos y miniatura de pieza

**Corregido el 30/10/2026:** `part_card` en
[`catalog.py`](../backend/app/api/routes/catalog.py) devuelve `cad_cache_key`, una identidad
que incluye el origen activo y la versión real del CAD. En SharePoint se consulta el
`cTag` (o su alternativa); en local, el sello actual del archivo. Listar piezas no descarga
el STEP ni calcula su SHA-256. Una revisión remota o un cambio de modo invalida la portada
aunque `cad.id` y `StoredFile.version` no cambien.

[`PartCover.tsx`](../frontend/src/components/Parts/PartCover.tsx) usa esa identidad en su
caché y vuelve a generar la captura cuando falta una portada válida. Si el CAD no está
disponible, no se muestra la portada anterior ni se intenta regenerarla; la pieza sigue
visible. La caducidad de la sesión Microsoft se comunica al navegador para iniciar sesión.
Las portadas guardadas con la clave antigua se regeneran una vez al consultarlas.

Al guardar se valida SHA-256 y se comprueba la identidad antes y después de leer los bytes.
Si el archivo cambia durante la captura/validación, se rechaza el guardado. No hay vigilancia
en segundo plano: el cambio se detecta al volver a consultar el catálogo o la ficha.
En features, `StepCoverCanvas` sigue comprobando los bytes antes de aplicar caras guardadas;
esta corrección afecta a la portada automática de la pieza, no remapea superficies.

Validación del 30/10: 344 tests del backend en Docker aislado y 14 pruebas de interfaz del
catálogo/portadas pasan. Incluyen cambios remotos con UUID estable, cambio a local, versiones
distintas durante el guardado y errores de acceso; Graph está simulado. Cliente TypeScript
regenerado con `cad_cache_key` en la tarjeta y en la petición de guardado (opcional para
clientes anteriores, que siguen sujetos a la comprobación SHA-256).

## Comprobaciones

Cobertura leída el 26/10/2026: componentes enumerados en Implementación, `PartCover.tsx`,
`capturePartCad.ts`, `api/routes/catalog.py`, `api/routes/features.py` y los esquemas de portada.
Las pruebas existentes están en [`test_cad_covers.py`](../backend/tests/api/routes/test_cad_covers.py),
[`cover-ui.test.cjs`](../frontend/tests/components/cover-ui.test.cjs) y
[`catalog.test.cjs`](../frontend/tests/components/catalog.test.cjs). Cubren, entre otros:

- Backend: persistencia, cambios de imagen, ediciones parciales, CAD de otro feature,
  original modificado y rechazo de selecciones/cámaras inválidas.
- Interfaz: falta de STEP, guardado conjunto de portada y cabecera, conservación del borrador
  al refrescar, pegado sin interceptar campos de texto, selección de archivo y arrastre,
  ampliación de imágenes y CAD, retorno del foco, cancelación durante el cálculo,
  compatibilidad de la huella geométrica y dimensiones idénticas entre pestañas,
  cancelación del borrador de la modal y retirada de portada sin guardar anticipadamente.
- Ejecutar las pruebas con `scripts/test.ps1` y `npm run test:components`; la BD de trabajo
  nunca se usa para las pruebas. Ver también [la guía de la aplicación](app-web.md).

**Registro histórico del 15/09/2026:** 131 pruebas del backend y 28 de interfaz, build de producción,
Biome, Ruff y mypy correctos. En una instalación aislada se ha comprobado el STEP real del
3212: marcar/desmarcar, arrastrar sin seleccionar, guardar, girar, ampliar y reabrir con la
misma selección y cámara. La descarga conserva el SHA-256 del original. Cambiar la versión
del vínculo bloquea las marcas antiguas y permite iniciar una selección nueva sin perder
la imagen guardada. La revisión visual de la instalación de trabajo no modificó la ficha.

**Registro histórico de la reorganización del 16/09/2026:** 41 pruebas de componentes, build y Biome correctos.
Comprobación en navegador con los estilos reales y datos/API simulados: icono de 32 px en
la esquina inferior derecha, hover/foco/táctil, ampliación, editor único y captura conservada
ante un error del visor CAD real. Revisadas las capturas de escritorio y móvil sin modificar
datos de la instalación.
