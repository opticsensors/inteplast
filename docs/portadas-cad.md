# Portadas de features desde el CAD

## Uso

En **Editar**, pulsar la portada (también si está vacía) abre **Editar portada**.
La pestaña **Imagen** admite:

- Clic para seleccionar una imagen del ordenador.
- Arrastrar y soltar una imagen.
- Pegar una imagen con **Ctrl+V**, fuera de los campos de texto.
- **CAD**, en la misma ventana, permite utilizar un STEP ya subido o vinculado como
  **Pieza CAD**. No se abre otra modal encima.

El editor CAD permite elegir la pieza, marcar varias superficies con clics, quitar una marca
con otro clic y limpiar la selección con el icono de borrador junto a **Encuadrar**.
Arrastrar gira; la rueda amplía; el botón de encuadre
recupera la vista inicial. **Aplicar** genera una imagen y la coloca en el borrador
de cabecera. Las imágenes elegidas, pegadas o arrastradas también requieren **Aplicar**.
**Cancelar**, la X o Esc en la modal descartan solo los cambios de esa apertura;
durante una subida se espera a que termine antes de aplicar o cerrar. **Guardar** en la ficha
persiste conjuntamente imagen y selección; **Cancelar** en la ficha descarta su borrador de
cabecera. Las notas y adjuntos mantienen su autoguardado habitual.

Si falta el STEP, se indica que hay que subirlo o vincularlo antes, con acceso a **Piezas
ejemplo**. Solo se ofrecen archivos STEP/STP de tipo `part` asociados a una pieza. El editor
admite hasta 50 MiB; el molde y el escaneo simplificados conservan sus visores independientes.

Las tarjetas y la ficha muestran una imagen estática. En la ficha, toda la portada abre la
ampliación; el icono de 32 px aparece dentro, abajo a la derecha, al pasar el ratón o enfocar
con teclado, y permanece visible en pantallas táctiles. Las imágenes se amplían en la misma
modal; las portadas CAD activan automáticamente el 3D con sus marcas y encuadre, sin
selector imagen/3D. Solo hay una X de cierre arriba, además de Esc. La captura se conserva
mientras carga el CAD o si falla. Durante la carga aparece «Cargando modelo CAD…» con un
indicador animado pequeño, sin recuadro, en la parte inferior de la imagen.
La conversión STEP y la huella de geometría se calculan
en un Web Worker: cerrar cancela la descarga y termina ese worker, incluso si está calculando.
Una ficha sin portada no abre una ampliación vacía.

Todas las modales de portada ajustan su ancho al cuadrado, con 16 px de margen interior.
El editor usa el mismo ancho y cuadrado que la ampliación; solo añade altura para los controles.
Si no cabe en altura, el diálogo completo se desplaza sin reducir el cuadrado.
Los botones quedan a 12 px de la imagen, sin reservar una fila vacía para avisos.
El editor mantiene exactamente el mismo tamaño de modal y visor al alternar **Imagen/CAD**,
incluso mientras carga o si falta el STEP. No muestra los párrafos de instrucciones de la
versión anterior.

El editor abre **CAD** cuando ya existe una portada CAD, para retomar la selección.
Cambiar entre sus pestañas conserva las superficies seleccionadas durante esa apertura.
Elegir, pegar, soltar o quitar una imagen sustituye la portada CAD al aplicar y guardar la
cabecera. El pegado se limita a la modal y respeta los campos de texto.

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
la selección; el mismo icono **Limpiar selección** permite empezar sobre la revisión actual
cuando la anterior ya no es compatible. No hay una segunda acción «Nueva selección».
Al limpiar una selección válida se conserva el encuadre y no se vuelve a importar el STEP.
No se ha añadido
una correspondencia automática de caras ni un historial de originales.

El origen sigue resolviéndose mediante el UUID interno y enlaces autenticados, igual que los
visores existentes. La integración futura con Graph puede conservar este contrato.

## Implementación

- `FeatureCoverEditor.tsx`: modal única y borrador independiente de imagen/CAD.
- `CadCoverEditor.tsx`: selección del CAD y captura dentro de esa modal.
- `CoverButton.tsx`: miniatura clicable compartida por consulta y edición.
- `CoverDialog.tsx`: ancho ajustado al cuadrado y filas de tamaño común a ambos editores.
- `cover.worker.ts` / `coverGeometry.ts`: conversión STEP y huella compatibles con cover-v1,
  transferencia de arrays y cancelación al cerrar.
- `StepCoverCanvas.tsx`: caras de `occt-import-js`, selección por clic, cámara y captura PNG.
  Mantiene la teselación completa del STEP; no usa el GLB simplificado para identificar caras.
  Agrupa superficies consecutivas del mismo color para reducir las llamadas de dibujo.
- `FeatureCover.tsx`: ampliación de imagen/3D; carga diferida del visor al abrir.
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
  al refrescar, pegado sin interceptar campos de texto, selección de archivo y arrastre,
  ampliación de imágenes y CAD, retorno del foco, cancelación durante el cálculo,
  compatibilidad de la huella geométrica y dimensiones idénticas entre pestañas,
  cancelación del borrador de la modal y retirada de portada sin guardar anticipadamente.
- Ejecutar las pruebas con `scripts/test.ps1` y `npm run test:components`; la BD de trabajo
  nunca se usa para las pruebas. Ver también [la guía de la aplicación](app-web.md).

Verificado el 15/09/2026: 131 pruebas del backend y 28 de interfaz, build de producción,
Biome, Ruff y mypy correctos. En una instalación aislada se ha comprobado el STEP real del
3212: marcar/desmarcar, arrastrar sin seleccionar, guardar, girar, ampliar y reabrir con la
misma selección y cámara. La descarga conserva el SHA-256 del original. Cambiar la versión
del vínculo bloquea las marcas antiguas y permite iniciar una selección nueva sin perder
la imagen guardada. La revisión visual de la instalación de trabajo no modificó la ficha.

Reorganización del 16/09/2026: 41 pruebas de componentes, build y Biome correctos.
Comprobación en navegador con los estilos reales y datos/API simulados: icono de 32 px en
la esquina inferior derecha, hover/foco/táctil, ampliación, editor único y captura conservada
ante un error del visor CAD real. Revisadas las capturas de escritorio y móvil sin modificar
datos de la instalación.
