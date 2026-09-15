# Vistas ligeras del escaneo y del molde

Implementado el **2026-09-15**. Los STL y STEP/STP de más de 50 MiB se abren mediante
un GLB generado automáticamente en el servidor. El visor y sus controles son los mismos
que los del CAD de la pieza. **Descargar** sigue entregando el original íntegro.
Por petición del usuario se elimina el pie informativo permanente «Vista simplificada…».
El aviso específico de **Vista parcial** sigue apareciendo cuando faltan superficies.

## Funcionamiento

1. Se vincula el original desde la carpeta de referencia o se utiliza un documento ya registrado.
2. Al abrir el 3D, `POST /files/{id}/preview` registra o consulta un trabajo. La pantalla muestra
   «Preparando la vista 3D…». Se puede salir: el trabajo continúa en el servidor.
3. El conversor lee el original mediante `file_sources`, genera un GLB y lo publica cuando
   termina. Las siguientes visitas reutilizan ese resultado.
4. Si cambia el original local, se pide **Volver a vincular**, igual que para PDF/CAD. Tras
   confirmar la nueva revisión, la siguiente apertura genera su vista. Nunca se presenta
   deliberadamente una vista anterior como si correspondiera a la revisión nueva.

No se suben ni se copian los originales a la aplicación. Los GLB y su manifiesto JSON se
guardan en `UPLOADS_DIR/previews/{documento}/{clave}.glb`, dentro del volumen persistente de
subidas. Son caché desechable, no originales ni un archivo histórico. Si se borra el GLB,
la aplicación lo vuelve a generar; al eliminar el documento se elimina su caché.

## Geometría y límites

- STL: `trimesh` y `fast-simplification`, objetivo de **300.000 triángulos**.
- STEP/STP: OpenCascade 7.9 mediante `cadquery-ocp`, importando todas las raíces y aplicando las
  transformaciones de cada cara. Teselación con desviación absoluta de **0,1 mm** y ángulo
  **0,35 rad**; simplificación posterior con objetivo de **500.000 triángulos**. Se admiten
  hasta **1.000.000** si el reductor necesita conservar más geometría, manteniendo el límite
  independiente de **25 MiB** por GLB.
- El lector STEP se inicializa antes de configurar las unidades. Se da preferencia a las
  curvas 3D (`read.surfacecurve.mode=3`) para reconstruir las curvas sobre las superficies,
  y se activa `read.stdsameparameter.mode=1` para alinear las representaciones de las aristas.
  Véase la [configuración del importador de OpenCascade](https://github.com/Open-Cascade-SAS/OCCT/blob/master/dox/user_guides/step/step.md#readsurfacecurvemode).
- Si una cara STEP no se puede mallar, se reintenta individualmente a **0,01 mm / 0,2 rad**.
  Si hace falta, `ShapeFix_Shape` repara la cara con sus aristas/vértices en memoria con tolerancia máxima
  de **0,01 mm**. Si falla, se prueba otra copia sin la reparación de costuras, que puede
  lanzar una excepción con los límites paramétricos de superficies offset importadas.
  Se incluyen las caras que se puedan mallar tras una división; los recuentos de reintentos
  y reparaciones y los índices de las caras incompletas quedan en el manifiesto.
- Si quedan caras incompletas, la aplicación muestra **«Vista parcial» encima del visor**,
  también al volver a abrirlo. Si afectan a más del **1 % del número de caras**, la conversión
  falla. Este límite cuenta caras, no superficie ni importancia funcional: una vista parcial
  no garantiza que todos los componentes estén completos. No debe usarse para comprobar cotas.
- El STEP se importa en mm. El STL no declara unidades y conserva sus coordenadas.
- Antes de reducir un STEP se unen vértices coincidentes de caras adyacentes (8 decimales
  en coordenadas mm). Mantener cada cara desconectada permitía colapsar superficies planas
  completas durante la reducción y abría huecos; la comprobación de límites globales no lo
  detectaba. Una prueba con una superficie cerrada de 1.310.720 triángulos verifica que
  sigue cerrada después de reducirla y conserva el volumen dentro del 1 %.
- El GLB conserva la geometría global y usa un material neutro. Esta primera versión no
  conserva colores/nombres de componentes ni permite ocultarlos por separado.
  El visor aplica iluminación plana a los derivados CAD para mantener legibles las placas
  y esquinas tras unir sus vértices. El escaneo conserva la iluminación suave.
- Las normales para la iluminación se calculan con acumulación vectorizada de NumPy.
  Se evita el cálculo alternativo de trimesh sin SciPy, que recorría todas las caras por
  cada vértice y retrasaba mucho la exportación aun después de simplificar la malla.
- Se rechazan geometrías vacías/no finitas, STEP que excedan el límite de caras incompletas, resultados que excedan
  el presupuesto y cambios de más del 1 % en los límites globales. Esto **no certifica precisión
  dimensional**: el control de cotas y los análisis deben utilizar el original.
- Entrada máxima **512 MiB**, GLB máximo **25 MiB**. La carga directa de otros formatos 3D
  mantiene el límite de 50 MiB. La subida manual también mantiene su límite de 50 MiB.

Implementación en `backend/app/preview_converter.py`. APIs de referencia:
[simplificación de trimesh](https://trimesh.org/trimesh.html#trimesh.Trimesh.simplify_quadric_decimation),
[exportación GLB](https://trimesh.org/trimesh.exchange.gltf.html#trimesh.exchange.gltf.export_glb)
y [bindings de OpenCascade](https://github.com/CadQuery/OCP).

## Cola, recursos y seguridad

`FilePreview` almacena un trabajo por documento: `queued`, `processing`, `ready` o `error`.
La migración **b73c69e5fa41**, posterior a **a62f58d4e930**, añade esa tabla sin modificar
los documentos existentes. No hace falta un servicio adicional: el ciclo de vida de FastAPI
arranca un trabajador ligero y PostgreSQL permite una sola conversión nativa simultánea
entre los procesos de la API mediante un bloqueo asesor.

La conversión corre en un **subproceso**, con límite de tiempo y, en Linux, de memoria virtual.
El resto de la API sigue atendiendo solicitudes. Al cerrar se mata el subproceso; los trabajos
`processing` se recuperan al reiniciar. En Linux también se termina si muere su proceso padre.
Los errores no se reintentan en bucle: el usuario dispone de **Reintentar** y de la descarga.

| Variable del backend | Valor predeterminado |
|---|---|
| `PREVIEW_WORKER_ENABLED` | `true`; `false` en el stack aislado de pruebas |
| `PREVIEW_TIMEOUT_SECONDS` | `900` (15 minutos) |
| `PREVIEW_MEMORY_MB` | `8192` (memoria virtual, Linux) |

El caché se identifica por UUID/revisión del documento, origen, tamaño/fecha del archivo y
versión de la receta. Se calcula SHA-256 antes y después de convertir y se guarda en el
manifiesto. En cada acceso se vuelve a comprobar la disponibilidad/revisión mediante el
adaptador. **No se recalcula el hash completo en cada visita**: la limitación del detector
local por tamaño/fecha sigue siendo la descrita en [ficheros-externos.md](ficheros-externos.md).
Al cambiar el algoritmo o sus parámetros hay que incrementar `RECIPE` para invalidar la caché.

Preparar una vista requiere una sesión autenticada. Su URL dura 15 minutos, está ligada al
usuario activo, documento, versión y clave de caché, y tiene un propósito distinto al de la
descarga del original. No sirve como autorización para leer otros documentos. La respuesta
GLB admite peticiones por rango y no es pública.

La cola está preparada para la instalación actual con PostgreSQL y un volumen compartido
por los procesos del backend. Para varias máquinas hace falta compartir ese almacenamiento
o sustituirlo por almacenamiento de objetos; no basta con replicar los contenedores.

## Instalación y comprobaciones

Reconstruir mediante `scripts/compose.ps1 up -d --build db prestart backend` para conservar
`.env.local`, montar los originales en solo lectura y aplicar la migración. El Dockerfile
instala las bibliotecas nativas necesarias. Python admitido: **3.10–3.13**; las dependencias
están fijadas en `uv.lock`. No requiere instalar CAD en el navegador ni credenciales Graph.

En desarrollo, `scripts/compose.ps1 watch backend` conserva el origen de `.env.local`. Las
pruebas y sus cachés se excluyen de la sincronización: modificarlas no debe reiniciar una
conversión larga. Los cambios del código de la aplicación sí reinician el backend y recuperan
el trabajo en curso desde el principio. Los patrones de exclusión son relativos a `backend/`,
según la [configuración de Compose Watch](https://docs.docker.com/compose/how-tos/file-watch/#ignore).

Las pruebas de `backend/tests/api/routes/test_previews.py` usan modelos sintéticos y la BD
aislada: conversión real STL/STEP, posición y orientación de componentes, caché, recuperación,
URLs protegidas, descarga original, cambio durante la conversión, reintento y límites.
También se comprueba la exclusión mutua entre trabajadores y se exporta una malla sintética
de 327.680 triángulos prohibiendo explícitamente el cálculo lento de normales.
Las pruebas simulan además una cara imposible de mallar: una pieza pequeña se rechaza;
un conjunto con menos del 1 % de caras afectadas conserva la vista y su advertencia visible.
Para los dos originales reales se conservan hashes y capturas fuera del repositorio, en
el scratch de la sesión `inteplast-derivatives`.

## Resultado con los originales del 3212

Comprobado en la aplicación local el **15/09/2026**:

| Archivo | Original | Vista web | Resultado |
|---|---:|---:|---|
| Escaneo STL | 247,1 MB | **7,2 MB** | 299.999 triángulos; sin aviso de caras incompletas |
| Molde STEP | 258,7 MB | **16,2 MB** | 695.928 triángulos; **vista parcial** |

Los tamaños de esta tabla son MB decimales. En el molde se recorrieron 68.605 caras:
8.545 requirieron reintento y **68 quedaron incompletas** después de las reparaciones.
No debe interpretarse ese cociente como porcentaje de superficie conservada. El aviso
se mantiene visible al abrir el modelo. Se ha añadido [A11 para el responsable del CAD](preguntas-abiertas.md)
para solicitar una exportación compatible y confirmar su revisión.

Se verificaron giro, zoom, encuadre, salida y reapertura en Chromium, sin descargar los
originales pesados para mostrar el modelo. Las descargas explícitas coinciden por SHA-256
con los originales. Sus tamaños, fechas y hashes tampoco cambiaron durante el trabajo.
Tras recrear el contenedor del backend, ambas vistas siguieron listas y conservaron sus
bytes, fecha y manifiesto: **no se repitió la conversión**. PDF y CAD pequeño también se
comprobaron de nuevo con los controles existentes.
