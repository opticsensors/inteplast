# Portadas por pieza: carrusel en la ficha y pila en el catálogo · plan

**18 de noviembre de 2026 · Pendiente de ejecutar. Sin código todavía.**

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
   - **Pulsar `3 / 24` despliega la lista de piezas con buscador** para saltar a una. Es una
     propuesta del asistente que Eduard ha visto en el prototipo sin objetarla. Se quita si él lo pide.
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
  - En la lista del número, las piezas sin captura propia llevan una marca discreta, sin texto
    explicativo ([sin textos de ayuda](interfaz.md)).
- **«Añadir pieza» con selección múltiple** en su desplegable con buscador. Comprobar si
  `Common/SearchSelect` lo admite; si no, añadir el modo múltiple sin cambiar los filtros del
  catálogo. Además, al crear la pieza desde su carpeta la app ya propone el feature.
- Al terminar, actualizar [interfaz](interfaz.md) y [portadas CAD](portadas-cad.md).

## Tandas

Cada tanda se comprueba antes de pasar a la siguiente y se anota en
[próximos pasos](proximos-pasos.md) al cerrarla.

| Tanda | Contenido |
|---|---|
| **1. Modelo y API** | Migración (vínculos que faltan, columnas nuevas, traslado de `cover_3d`), endpoint por pieza, `FeaturePublic`, desvincular y borrar pieza, cliente regenerado |
| **2. Ficha** | Carrusel, modal con 3D por pieza, teclado, táctil, lista del número |
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
  - Carrusel: flechas, teclado, `n / N`, lista con buscador y flechas visibles en táctil.
  - Modal con 3D de la pieza visible y cancelación al cambiar de pieza.
  - Pila en lista y cuadrícula.
  - Edición en serie: conserva los borradores y Cancelar los descarta todos.
- **Navegador:** escritorio y móvil, claro y oscuro, sin desplazamiento horizontal. Comprobar
  también en la ficha de pieza que no cambia su portada.

## Preguntas para Eduard

- **P1.** Las portadas que hoy son una imagen pegada, sin pieza: ¿se quedan como imagen del
  feature (solo visible si no tiene piezas, propuesta por defecto) o se asignan a una pieza que
  elija él?
- **P2.** El resaltado: la app pinta hoy las caras en rojo sobre la pieza en gris. En el
  prototipo, «R3 Foco» atenúa además el resto de la pieza. No se ha decidido; mientras tanto se
  mantiene el de hoy.
