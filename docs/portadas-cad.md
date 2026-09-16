# Portadas de features desde el CAD

## Uso

En **Editar**, la imagen de cabecera admite:

- Clic para seleccionar una imagen del ordenador.
- Arrastrar y soltar una imagen.
- Pegar una imagen con **Ctrl+V**, fuera de los campos de texto.
- **Desde CAD** para utilizar un STEP ya subido o vinculado como **Pieza CAD**.

El editor CAD permite elegir la pieza, marcar varias superficies con clics, quitar una marca
con otro clic y limpiar la selección. Arrastrar gira; la rueda amplía; el botón de encuadre
recupera la vista inicial. **Usar como portada** genera una imagen y la coloca en el borrador
de cabecera. **Guardar** en la ficha persiste conjuntamente imagen y selección; **Cancelar**
descarta ese borrador. Las notas y adjuntos mantienen su autoguardado habitual.

Si falta el STEP, se indica que hay que subirlo o vincularlo antes, con acceso a **Piezas
ejemplo**. Solo se ofrecen archivos STEP/STP de tipo `part` asociados a una pieza. El editor
admite hasta 50 MiB; el molde y el escaneo simplificados conservan sus visores independientes.

Las tarjetas muestran la imagen generada. La ficha ofrece **Activar 3D** y **Ampliar portada
3D**, con las mismas marcas y encuadre. **Editar portada 3D** permite retomar la selección.
Elegir, pegar, soltar o quitar una imagen sustituye la portada CAD al guardar la cabecera.

## Persistencia y revisiones

`Feature.cover_3d` es una anotación JSON nullable añadida por la migración
`c84d70f6ab52_add_feature_cad_cover.py`. Las fichas existentes mantienen su imagen.

Guarda el adjunto, la pieza, el documento y su versión, SHA-256 de los bytes del STEP, receta
del importador, huella de la geometría, superficies seleccionadas y cámara. `Feature.image_id`
sigue apuntando a una imagen para las miniaturas. El STEP original no se modifica.

`PUT /features/{id}` acepta `cover_3d` junto a `image_id`. Comprueba que el CAD pertenece al
feature y a la pieza, que está disponible y que su versión y SHA-256 coinciden. Un cambio del
original produce un error antes de guardar la cabecera. El esquema valida selección no vacía,
sin duplicados y cámara finita y válida. Una edición de otros campos conserva la portada.

El navegador verifica además la huella de la geometría antes de aplicar índices de caras.
Los índices solo valen para esos bytes y esa receta: **no son identificadores estables entre
revisiones del CAD**. Si cambia el documento, la ficha conserva la imagen, pero exige revisar
la selección; **Nueva selección** permite empezar sobre la revisión actual. No se ha añadido
una correspondencia automática de caras ni un historial de originales.

El origen sigue resolviéndose mediante el UUID interno y enlaces autenticados, igual que los
visores existentes. La integración futura con Graph puede conservar este contrato.

## Implementación

- `CadCoverEditor.tsx`: selección del CAD, captura y borrador de portada.
- `StepCoverCanvas.tsx`: caras de `occt-import-js`, selección por clic, cámara y captura PNG.
  Mantiene la teselación completa del STEP; no usa el GLB simplificado para identificar caras.
  Agrupa superficies consecutivas del mismo color para reducir las llamadas de dibujo.
- `FeatureCover.tsx`: miniatura, activación del 3D y ampliación; carga diferida del visor.
- `cadCover.ts`: elegibilidad, identidad del documento y versión de la receta.
- `cad_covers.py`: validación del vínculo y de los bytes al guardar.

`occt-import-js` queda fijado a `0.0.23`. Al cambiar el importador o la teselación, hay que
actualizar la receta y revisar la compatibilidad de las selecciones guardadas.

## Archivos de «Piezas ejemplo»

En edición, el icono de cadena está junto a la descarga. Abre el selector de originales;
si ya hay un documento local, ofrece **Usar otro archivo en esta ficha** o **Actualizar
ubicación o revisión del documento**. Esta última acción conserva el UUID y afecta a todas
las fichas que utilizan el documento, como explica el diálogo. No aparecen dos botones de
vínculo debajo de cada fila. El icono tiene nombre accesible y ayuda al pasar el ratón.

## Comprobaciones

- Backend: persistencia, cambios de imagen, ediciones parciales, CAD de otro feature,
  original modificado y rechazo de selecciones/cámaras inválidas.
- Interfaz: falta de STEP, guardado conjunto de portada y cabecera, conservación del borrador
  al refrescar, pegado sin interceptar campos de texto, selección de archivo y arrastre.
- Ejecutar las pruebas con `scripts/test.ps1` y `npm run test:components`; la BD de trabajo
  nunca se usa para las pruebas. Ver también [la guía de la aplicación](app-web.md).

Verificado el 15/09/2026: 131 pruebas del backend y 28 de interfaz, build de producción,
Biome, Ruff y mypy correctos. En una instalación aislada se ha comprobado el STEP real del
3212: marcar/desmarcar, arrastrar sin seleccionar, guardar, girar, ampliar y reabrir con la
misma selección y cámara. La descarga conserva el SHA-256 del original. Cambiar la versión
del vínculo bloquea las marcas antiguas y permite iniciar una selección nueva sin perder
la imagen guardada. La revisión visual de la instalación de trabajo no modificó la ficha.
