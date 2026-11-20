# Selección de superficies en los STEP del catálogo · 19/11/2026

El editor de portadas rechazaba tres archivos completos al encontrar una cara sin triángulos. Los tres contienen miles de caras que sí se pueden seleccionar. La miniatura se veía porque para dibujar la pieza completa basta la malla. El mensaje de error aparecía al comprobar los índices de las caras en la vista interactiva.

| Pieza | Archivo | Caras con triángulos | Caras sin triángulos |
|---|---|---:|---:|
| 3056 | `20190521_3130589008_02_0131S00135.002-Isoliermaske E-Seite.stp` | 3.664 | 1 |
| 3167 | `20220623_313026000C-02.stp` | 10.957 | 11 |
| 3288, tapa | `20240516_TAPA_RCP31.stp` | 2.737 | 1 |

Se abrieron los **27 STEP/STP de las 21 piezas** que utiliza u ofrece el catálogo como CAD de pieza. Se incluyeron la base y la tapa de la 3288 y los seis STEP candidatos de la 3202, entre ellos los útiles. El séptimo candidato de la 3202 es un IGES. Los moldes y escaneos tienen otro visor y quedan fuera del ensayo.

Los otros **24 STEP** pasaron la validación anterior. Corresponden a 2820, 3051, 3168, 3174, 3186, 3195, 3197, 3202, 3205, 3206, 3212, 3214, 3218, 3226, 3233, 3237, 3238, la base de 3288 y 3309. El lector emitió avisos de sintaxis en 3174, 3186 y 3218 y aun así obtuvo geometría y rangos de caras válidos.

## Reproducción y corrección

La prueba usó los originales y el mismo `occt-import-js@0.0.23` de la web, con la configuración de importación del editor. Se contrastaron todos los rangos de caras con los triángulos de su propia malla. Cuando una cara no produce triángulos, el lector conserva su índice y devuelve como último triángulo el inmediatamente anterior al primero. En la 3167 aparece, por ejemplo, el intervalo vacío de 94.406 a 94.405.

El editor ahora omite esos intervalos al seleccionar, mantiene los índices originales de las demás caras y sigue comprobando solapes y límites. La vista 3D de la pieza completa puede dibujar la malla independientemente de esa comprobación. Una cara que carece de triángulos sigue sin tener una superficie sobre la que hacer clic. Esta prueba verifica el comportamiento de la web y no certifica la precisión dimensional del modelo original.

También se abrió el editor WebGL en Chromium con los tres archivos afectados, la base de la 3288 y el STEP de la 3212. En cada caso se hizo clic sobre el modelo y se generó una captura con la cara seleccionada. En la 3056 se seleccionó la cara 1519, en la 3167 la 8722 y en la tapa de la 3288 la 2649. En los cinco casos se verificó que la anotación de la captura identificaba los bytes del STEP original por su SHA-256.
