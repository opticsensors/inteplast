# Portadas por pieza: carrusel en la ficha y pila en el catálogo · plan

**18 de noviembre de 2026 · Cerrado con Eduard el 19/11/2026 · En ejecución desde el 19/11/2026.**

> 🔴 **Orden decidido por Eduard (18/11/2026): este plan va PRIMERO.** El
> [plan de carga del catálogo](plan-carga-catalogo-2026-11-18.md) (21 piezas y 8 features) se
> ejecuta **después**, cuando este esté cerrado y comprobado. Motivo: la carga vincula varias
> piezas a cada feature (Bolt Eye 4, Clips en Piezas 5…) y la portada tiene que estar ya
> preparada para varias piezas. Si no, habría que migrar las portadas sobre la BD ya cargada.

Acordado con Eduard en el chat del 18/11/2026, con prototipos interactivos revisados por él.
Prototipo final (variante **A** de la ficha y **T2** de la tarjeta):
[prototipo-portadas-por-pieza.html](prototipo-portadas-por-pieza.html), que se abre en el navegador
y es una copia del artefacto privado `https://claude.ai/artifact/53kDZabavEG9ttsKp3sKho`.
Las piezas, los códigos y las formas del prototipo son de ejemplo.

## El problema

Un feature aparece en varias piezas, y en cada una está en un sitio distinto. Hoy la portada
es **una sola por feature** (`Feature.image_id` y `Feature.cover_3d`, que apunta a una pieza): con
24 piezas solo se ve el feature en una. Ninguna solución que ponga miniaturas, pestañas o
mosaicos debajo de la portada escala a 20–30 piezas, y Eduard no quiere nada debajo de la captura.

## Decisiones de Eduard (18/11/2026)

1. **Ficha del feature: carrusel (variante A).** Una sola captura, más grande que hoy
   (prototipo: 300 px; hoy `sm:size-48`, 192 px) y **sin nada debajo**.
   - Arriba a la izquierda, **solo el código** de la pieza, pequeño. Sin nombre ni número de
     ocurrencias.
   - Arriba a la derecha, la posición: **`3 / 24`**.
   - **Flechas a los lados**, con el estilo de los controles de la app (botón de 32 px,
     `rounded-md border bg-background/95 shadow-sm`, chevrones de lucide). Aparecen al pasar el
     ratón o al enfocar, como el icono de ampliar de `CoverButton`, y se ven siempre en pantallas
     táctiles.
   - Abajo a la derecha, el icono de ampliar actual (`Maximize2`).
   - Teclado ← / → con el carrusel enfocado y deslizamiento con el dedo en el móvil.
   - **Pulsar la captura abre la modal** (`CoverDialog`) con el mismo carrusel: CAD interactivo
     con sus caras rojas si esa pieza tiene portada CAD; si no, la imagen. «Encuadrar» como hoy.
   - **`3 / 24` es solo texto**, no se pulsa. La lista de piezas con buscador que proponía el
     prototipo queda **descartada** (Eduard, 19/11/2026): solo flechas, teclado y deslizamiento.
2. **Lista y cuadrícula: pila + número (T2).** La captura de la portada con dos capas detrás,
   que indican que hay más, y el número de piezas. Sin flechas ni navegación en la tarjeta: al
   pulsar se abre la ficha, y allí se navega.
3. **Las piezas sin el feature marcado se muestran igual**, con la captura automática de su CAD
   (la del catálogo, sin rojo): «mejor que mostrar algo que nada». Si una pieza no tiene captura,
   aparece el icono de imagen, como hoy.
4. **Pieza de portada** (la de arriba de la pila y la primera del carrusel): **una cualquiera de
   las vinculadas**; «ya lo corregiremos más adelante si no nos gusta». Regla provisional: **la
   primera en el orden de piezas de la ficha** (`part_order` y luego el código, como
   `featureParts()`). Sin selector ni estrella por ahora.
5. **Según el número de piezas (Eduard, 19/11/2026):**

   | Piezas | Ficha | Lista y cuadrícula |
   |---|---|---|
   | **0** | Imagen del feature o icono, como hoy | Como hoy |
   | **1** | Su captura con **solo el código** arriba a la izquierda. Sin flechas, sin `1 / 1`, sin teclado ni deslizamiento; en edición, sin `‹ 1 / 1 ›` | Su captura, **sin pila ni número** |
   | **2 o más** | Carrusel completo | Pila con número |

   En la lista sigue el resumen de debajo («1 pieza · 3212»), que ya existe y no es parte de la pila.
6. **Resaltado:** en CAD, caras rojas sobre la pieza en gris, como hoy. *(El 25/11/2026 Eduard
   decide sustituir el rojo por el color fijo de cada feature: ver el
   [plan de colores por feature](plan-colores-por-feature-2026-11-25.md).)* Sobre las fotos la app no
   dibuja marcas; una herramienta de círculo o elipse queda **descartada de momento**.

## Modelo de datos

La captura pasa a ser del **par feature–pieza**:

- **`FeaturePartLink`** gana `image_id` (FK a `StoredFile`, `SET NULL`) y `cover_3d` (JSON con el
  mismo esquema `FeatureCover3D`). Es el embrión de `INSTANCIA_EN_PROYECTO`
  ([modelo de datos](modelo-datos.md)), el sitio natural de lo que es «este feature en esta pieza».
- **Vínculos que faltan.** Hoy una pieza puede pertenecer al feature solo por un adjunto
  (`FeatureAsset.part_id`) sin fila en `FeaturePartLink` (lo dice el propio modelo, y
  `featureParts()` une los dos caminos). La migración crea las filas que falten. Desde entonces,
  todo alta de adjunto con pieza garantiza el vínculo. Comprobar antes con una consulta de
  **solo lectura** cuántos pares hay en cada caso.
- **Migración de las portadas actuales:**
  - `Feature.cover_3d` con `part_id` pasa al vínculo de esa pieza, junto con su imagen
    (`Feature.image_id`).
  - Una **imagen pegada sin pieza** (`image_id` sin `cover_3d`) **no se asigna a ninguna pieza**
    (no se decide por el usuario, [AGENTS.md](../AGENTS.md)). Se conserva en `Feature.image_id` y
    solo se usa cuando el feature no tiene piezas (por ejemplo «Anclajes»). Ver la pregunta P1.
  - `Feature.cover_3d` deja de usarse, pero la columna se mantiene en esta tanda para que el
    `downgrade` pueda restaurarla. Se retira en una tanda posterior.
- **Desvincular una pieza** borra su vínculo y con él su captura, sin tocar las demás. Desaparece
  el caso especial de `unlink_feature_part` que hoy vacía `Feature.cover_3d`
  (`api/routes/features.py`). Hay que adaptar igual `part_deletion._covers_to_reset` y la
  limpieza al quitar adjuntos.
- **Captura automática de la pieza:** sigue siendo la de siempre (`EvidenceJob` `part-cover`,
  `PUT /parts/{id}/cover`). No se duplica: es solo lo que se muestra cuando el par no tiene
  captura propia.

## API

- `PUT /features/{id}/parts/{part_id}/cover` con `image_id` y `cover_3d` opcional, y `DELETE`
  para quitarla. Valida como hoy `cad_covers.validate_cover`: el CAD debe ser un adjunto de **esa
  pieza** en ese feature, con su versión y su SHA-256.
- `FeaturePublic` añade por pieza su captura propia (imagen y `cover_3d`) y la captura automática
  guardada de la pieza, y para la tarjeta, la **imagen de portada** y el **número de piezas**,
  calculados en el servidor con la regla de la decisión 4.
- `FeatureUpdate.cover_3d` deja de aceptarse para piezas: la portada CAD se guarda por pieza.
- Regenerar el cliente TypeScript (`bash scripts/generate-client.sh`).

## Interfaz

- **Carrusel** (componente nuevo) en la cabecera de la ficha, en lugar de `FeatureCover`.
  Reutiliza `CoverButton`, `FeatureThumbnail`/`PartThumbnail`, `CoverDialog` y `StepCoverCanvas`.
  - La modal carga el 3D **solo de la pieza visible**. Al cambiar de pieza, cancela el worker
    como hoy al cerrar.
  - El carrusel **no genera capturas de pieza**: muestra las guardadas. Así una ficha con 24
    piezas no abre 24 STEP.
- **Pila** en `FeatureCard` (lista) y `FeatureTile` (cuadrícula): dos capas detrás y el número.
  En la lista se mantiene `PartSummary` («N piezas · códigos»).
- **Edición en serie.** En «Editar», la portada es el mismo carrusel con el lápiz de
  `CoverButton`, que abre el editor de **la pieza visible**:
  - La pieza ya viene elegida y desaparece el selector de pieza de `CadCoverEditor`.
  - Se mantienen las pestañas Imagen y CAD, y el editor tiene la misma navegación `‹ 3 / 24 ›`.
  - «Aplicar» guarda un borrador por pieza y se puede pasar a la siguiente sin cerrar.
  - **Guardar** en la ficha persiste todos los borradores, igual que hoy imagen y selección.
  - Sin lista de piezas (decisión 1) no hay marca de «sin captura propia»: se ve recorriendo el
    carrusel.
- **«Añadir pieza» con selección múltiple** en su desplegable con buscador. Comprobar si
  `Common/SearchSelect` lo admite; si no, añadir el modo múltiple sin cambiar los filtros del
  catálogo. Además, al crear la pieza desde su carpeta la app ya propone el feature.
- Al terminar, actualizar [interfaz](interfaz.md) y [portadas CAD](portadas-cad.md).

## Tandas

Cada tanda se comprueba antes de pasar a la siguiente y se anota en
[próximos pasos](proximos-pasos.md) al cerrarla.

**Estado del 19/11/2026.** Eduard aprobó la tanda 5. La BD de trabajo está en
`p27ea3fbd174` y la instalación local sirve el backend y el frontend reconstruidos.
Antes de migrar se restauró la copia de `pg_dump` en un PostgreSQL temporal. La copia
está en `C:/Users/eduard.almar/.codex/backups/inteplast/20261119-135348/app-before-part-covers.dump`.
Tras la migración se verificaron los dos PNG y se compararon los identificadores de
imagen y las selecciones CAD completas con la copia. Bolt Eye y Nervios conservan cada
uno su portada en la pieza 3212. La API y la web responden en localhost.
Eduard confirmó en la web que las dos fichas se ven correctamente. Con esa
comprobación queda cerrada la tanda 5.

**Correcciones tras la revisión (19/11/2026), aprobadas por Eduard:**

1. Un único `PUT /features/{id}` guarda cabecera y portadas cambiadas en una transacción; se
   retiran los endpoints por pieza (no se llegaron a desplegar).
2. El borrador de una pieza se descarta cuando el servidor confirma su desvinculación; si falla,
   se conserva. Si otro usuario la retiró, el guardado avisa del conflicto (409), no guarda nada
   y el reintento guarda el resto.
3. La vuelta atrás de la migración no resucita una selección 3D cuya portada se quitó o cuya
   pieza se desvinculó.
4. Una pieza sin captura muestra el icono, nunca la imagen propia del feature.
5. La selección múltiple de «Añadir pieza» cuenta y envía todo lo marcado, aunque la búsqueda lo
   oculte.
6. Deslizar en la modal solo sobre imagen; sobre el 3D el gesto gira la pieza.
7. La ficha recibe la captura automática de cada pieza también con portada propia.
8. Un único orden, decidido por el servidor (natural: P2 antes que P10); el carrusel lo sigue.
9. `cover_3d` suelto en `PUT /features/{id}` se rechaza con 422.

**Segunda revisión (19/11/2026):**

1. La respuesta de guardar, vincular y reordenar se prepara **antes** del `commit`: si la
   consulta a SharePoint falla (sesión caducada), no se guarda nada.
2. Guardar portadas, vincular, desvincular, quitar o cambiar un adjunto y borrar una pieza
   toman el mismo bloqueo del feature: una portada nunca conserva caras de un STEP retirado.
3. Antes de guardar, la ficha relee el feature. Si falta alguna pieza con borrador, avisa
   nombrándola, descarta solo ese borrador y no guarda nada; un 409 anterior por otro motivo
   ya no oculta el aviso.
4. La vuelta atrás de la migración borra la selección 3D antigua siempre que no pueda volver
   con la portada vigente de su pieza; una foto pegada después se conserva, sin caras.

**Comprobaciones posteriores (19/11/2026)**

- Añadir un adjunto toma el mismo bloqueo que desvincular su pieza. Si se desvincula al final,
  se eliminan el vínculo y sus adjuntos. Si el adjunto se añade después, se crea de nuevo el
  vínculo y se puede guardar una portada.
- El borrador conserva el código que tenía la pieza al pulsar «Aplicar». Si otro usuario
  la retira, el aviso puede identificarla aunque la ficha ya haya actualizado la lista.
  Si se retira entre la lectura y el guardado, la ficha comprueba los vínculos al recibir
  el 409 y basta un reintento para guardar los demás cambios.

Desvincular quita la portada de esa pieza y **conserva el fichero subido**. La limpieza de
imágenes sin referencias queda como tarea aparte, después de la tanda 5.

Desviaciones del plan, decididas al implementar:

- En la modal de consulta, el código y `n / N` van juntos arriba a la izquierda: arriba a la
  derecha está **Encuadrar** del visor 3D.
- Desvincular una pieza quita su portada (imagen incluida) con el vínculo y conserva el fichero
  subido; antes se conservaba la imagen del feature. Borrar una pieza sí borra las imágenes
  subidas solo para sus portadas.
- Quitar el adjunto STEP de una portada deja la imagen y borra solo la selección de caras.
- La edición no responde a ← / →: cambia de pieza con los botones `‹ ›` de su cabecera, para
  no interferir con el visor 3D ni con la subida.
- **Añadir pieza** múltiple: casillas en el mismo desplegable y botón «Añadir N piezas».

| Tanda | Contenido |
|---|---|
| **1. Modelo y API** | Migración (vínculos que faltan, columnas nuevas, traslado de `cover_3d`), endpoint por pieza, `FeaturePublic`, desvincular y borrar pieza, cliente regenerado |
| **2. Ficha** | Carrusel, modal con 3D por pieza, teclado, táctil, caso de una sola pieza |
| **3. Catálogo** | Pila con número en lista y cuadrícula |
| **4. Edición** | Editor por pieza en serie y «Añadir pieza» múltiple |
| **5. Despliegue** | Copia de la BD de trabajo con `pg_dump` fuera de Git (como en A+B), migración, reconstrucción y comprobación en la web con la sesión de Microsoft |

## Pruebas

- **Backend** (BD aislada, `.\scripts\test.ps1`; nunca contra `app`):
  - Migración: portada CAD que pasa a su pieza, imagen pegada conservada, vínculos creados a
    partir de adjuntos y `downgrade`.
  - Validación del endpoint: CAD de otra pieza, bytes cambiados, selección vacía.
  - Desvincular una pieza no toca las capturas de las demás; borrar una pieza.
  - Portada y número de piezas de la tarjeta.
- **Componentes** (`npm run test:components`):
  - Carrusel: flechas, teclado, `n / N` y flechas visibles en táctil.
  - Una sola pieza: código sin flechas ni `1 / 1`; sin pila en el catálogo.
  - Modal con 3D de la pieza visible y cancelación al cambiar de pieza.
  - Pila en lista y cuadrícula.
  - Edición en serie: conserva los borradores y Cancelar los descarta todos.
- **Navegador:** escritorio y móvil, claro y oscuro, sin desplazamiento horizontal. Comprobar
  también en la ficha de pieza que no cambia su portada.

## Preguntas resueltas (Eduard, 19/11/2026)

- **P1.** Las imágenes pegadas sin pieza se quedan como imagen del feature y solo se ven si no
  tiene piezas. Aceptado que, en un feature con piezas, esa imagen deje de verse y salga la
  captura automática del CAD.
- **P2.** Resaltado como hoy (caras rojas sobre gris), sin atenuar el resto. Sin marcas sobre fotos.
