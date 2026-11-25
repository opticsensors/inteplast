# Colores por feature y todos los features sobre el CAD de la pieza · plan

**25 de noviembre de 2026 · Decisiones de Eduard en el chat del 25/11/2026 · Sin implementar.**

Es el siguiente trabajo de la app ([próximos pasos](proximos-pasos.md#siguiente-colores-por-feature-en-el-cad-de-la-pieza-25112026)).
Parte de la tarea «Varios features sobre un CAD» y del estado actual de las portadas
([portadas CAD](portadas-cad.md)).

## El problema

Una pieza puede tener varios features, y cada feature marca sus caras sobre el CAD de esa pieza
(`FeaturePartLink.cover_3d`). Hoy la portada de la pieza es el CAD entero sin caras marcadas
([interfaz](interfaz.md)), y la del feature pinta sus caras en rojo. No hay ningún sitio donde se
vean juntos todos los features de una pieza.

## Decisiones de Eduard (25/11/2026)

1. **Un color fijo por feature, no por orden.** El mismo feature tiene el mismo color en todas
   las piezas (por ejemplo, Tetones siempre verde), para reconocerlo sin mirar la leyenda. Se
   descarta asignar los colores por posición dentro de cada pieza (rojo el primero, azul el
   segundo…), porque el mismo color significaría cosas distintas en piezas distintas.
2. **Asignación automática.** El color se asigna al crear el feature, a partir de una paleta fija
   de colores que se distingan bien sobre el gris de la pieza, y se guarda con el feature para que
   no cambie si se crean o borran otros. Los 8 features actuales reciben uno distinto cada uno.
   Si algún día hay más features que colores, la paleta se repite: con 2 o 3 features por pieza
   casi nunca coincidirán dos iguales en la misma pieza.
3. **La ficha del feature también usa su color**, en vez del rojo actual, para que el feature se
   vea igual en todas partes. Sustituye la decisión P2 del
   [plan de portadas por pieza](plan-portadas-por-pieza-2026-11-18.md) (caras rojas).
   Las portadas guardadas son PNG con el rojo ya pintado: se regeneran automáticamente con el
   color nuevo a partir de las caras y el encuadre guardados (`cover_3d`), sin volver a marcar
   nada a mano. Las portadas que son una imagen pegada, sin caras, no cambian.
4. **Ficha de pieza: todos sus features sobre el CAD**, cada uno con su color y una leyenda con
   los nombres. Se reutilizan las caras ya marcadas en cada feature; desde la pieza no se marcan
   caras. **Las marcas se ven siempre por defecto**, sin interruptor general. En la modal (visor
   3D de la pieza), la leyenda tiene una casilla por feature, con su color y su nombre, todas
   marcadas al abrir. Desmarcar una oculta las caras de ese feature. Mismo estilo que la leyenda
   del grafo (casillas superpuestas arriba a la izquierda, [interfaz](interfaz.md)). En la
   miniatura del catálogo y en la ficha del feature no hay casillas: un feature sin captura propia muestra la pieza gris; la miniatura de pieza es una imagen
   fija con todas las marcas, y en la ficha del feature solo hay un feature.
5. **Caras marcadas en dos features.** No se prohíben: si los dos features afectan a la misma
   cara, es información útil. Esa cara se pinta con un color reservado para «compartida», que no
   es de ningún feature, y la leyenda añade «Varios features». Si solo queda un feature visible en esa cara, adopta su color.
6. **Miniatura del catálogo con colores.** La captura de la pieza en el catálogo muestra las caras
   de todos sus features con sus colores. Se regenera sola cuando cambian las caras de cualquiera
   de sus features, igual que hoy se regenera cuando cambia el CAD.
7. **Caras de otra versión del CAD.** Las caras solo valen para los mismos bytes y la misma receta
   con que se marcaron ([persistencia](portadas-cad.md#persistencia-y-revisiones)). Si un feature
   se marcó sobre otra versión del CAD de la pieza, sus caras no se pintan y la ficha lo indica.
   No se remapean caras entre versiones. Esto incluye que el STEP cambie en SharePoint con la
   misma ruta:
   - **Ficha del feature:** conserva la captura guardada y pide revisar la selección, como hoy.
   - **Ficha de pieza y miniatura del catálogo:** se pintan solo los features cuyas caras
     correspondan al CAD actual; los demás se indican como pendientes de volver a marcar.
   - La selección antigua no se borra: deja de aplicarse mientras no coincidan los bytes.
8. **Aviso «Caras por revisar».** Cuando un feature tenía caras marcadas en una pieza y el CAD ha
   cambiado después, aparece un aviso del mismo tipo que los existentes: triángulo ámbar y texto
   corto, como «Sin mediciones detectadas» o «Sin features asociados» ([interfaz](interfaz.md)).
   - **Tarjeta de pieza:** «Caras por revisar: Tetones», con los nombres de los features afectados.
   - **Tarjeta de feature:** «Caras por revisar en 1 pieza».
   - **Fichas de pieza y de feature:** el mismo aviso debajo de la portada.
   - **Solo si había caras marcadas.** Un feature que nunca se marcó en esa pieza no genera
     aviso, para no llenar de avisos las piezas que simplemente están sin marcar.
   - **Sin descargar el CAD.** Al guardar las caras se guarda también la versión del archivo en
     el origen. El catálogo la compara con la versión actual, que ya consulta para las
     miniaturas. Hoy `cover_3d` guarda la huella de los bytes (`source_sha256`), que solo se
     conoce descargando el archivo, y no la versión del origen.

## Datos de partida (BD local, 25/11/2026)

Ninguna pieza tiene más de dos features. Cuatro tienen dos:

| Pieza | Features | Caras marcadas | En los dos features | Mismo CAD en los dos |
|---|---|---|---|---|
| 3205 | Nervios de Soldadura, Planitudes | 40 | 0 | Sí |
| 3206 | Nervios de Soldadura, Planitudes | 56 | 0 | Sí |
| 3167 | Pockets, Tetones | Solo en Tetones | — | — |
| 3214 | Nervios de Soldadura, Tetones | Solo en Tetones | — | — |

Hoy no hay caras compartidas. La regla del punto 5 cubre los casos futuros.

## Pruebas

- **3205 y 3206:** los dos features con su color, sin caras compartidas, y la leyenda con los dos nombres.
- **3167 y 3214:** solo se pinta Tetones. La leyenda ofrece únicamente los features con caras compatibles.
- **Cara compartida:** prueba con datos de test, porque hoy no existe en la BD.
- **Ficha del feature:** las portadas CAD existentes se regeneran con el color del feature, y las
  imágenes pegadas no cambian.
- **Catálogo:** la miniatura de la pieza se actualiza al cambiar las caras de uno de sus features.
- **Versión distinta del CAD:** las caras no se pintan y la ficha lo indica.
- **Leyenda de la modal:** al desmarcar un feature se ocultan sus caras y al volver a marcarlo
  reaparecen. Al abrir de nuevo la modal, todas vuelven a estar marcadas.
- **Aviso «Caras por revisar»:** cambiar el CAD de una pieza con caras marcadas muestra el aviso
  en su tarjeta, en la del feature y en las dos fichas. Un feature sin caras marcadas no lo genera.
  Volver a marcar las caras sobre el CAD actual lo quita.

## Por concretar al implementar

- Los colores concretos de la paleta y el reservado para caras compartidas: enseñarlos a Eduard
  antes de fijarlos.
- La posición y el aspecto de la leyenda, siguiendo [interfaz](interfaz.md) (Features es la
  referencia visual).
- Si el color se puede cambiar a mano (por ejemplo, en Admin). No se ha pedido.
- Cómo se regeneran de una vez las portadas existentes de los features y las miniaturas de las
  piezas sin bloquear el catálogo ([rendimiento pendiente](proximos-pasos.md)).
- Validar las 21 selecciones antiguas por su SHA-256 contra una versión del CAD comprobada. Si falta evidencia, verificar al preparar el CAD. Un fallo temporal de acceso conserva el estado de comprobación pendiente.
- Primera revisión visual con la 3205 y la 3167.

## Fase posterior

Permitir volver a marcar sobre un nuevo CAD principal conservando el vínculo y las cotas.

## Relacionado: fallos del 25/11/2026 en portadas y sesión

El commit `7fe7ca0` está desplegado. La sesión de Graph se comparte entre procesos y el catálogo ofrece reintentos cuando falla una portada. Pablo confirmó que ya ve bien las miniaturas en producción. La 3202 sigue sin CAD principal.
