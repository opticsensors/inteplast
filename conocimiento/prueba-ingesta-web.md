# Prueba repetible de extracción de la web

**Resultado vigente: lector v6, segunda revisión sin IA.** Las 21 carpetas terminan:
19 aportan datos (18 con pendientes) y 2 no producen observaciones. Véanse
[el informe visual actual](../out/conocimiento/prueba-web/2026-11-13-sin-ia/lectura-carpetas.html)
y la sección «Segunda revisión sin IA» al final. El balance v5 se conserva como histórico.

El 13/11/2026 Eduard autorizó tres ajustes pequeños en la web antes de probar todas las
piezas: corregir la selección de referencias, separar métodos de medición y ajustar
límites, y proponer todos los planos detectados. Correcciones, selección entre copias,
lector `.icp` y modelo de componentes quedan fuera de este trabajo.

## Cambios

- `reference_kind`: `SUPPORT` en el nombre del producto ya no descarta su CAD. Las
  carpetas de soporte siguen excluidas. Se reconocen `ballooned`, `balloned` y
  `balonned`, también dentro del método de medición. Se mantienen las exclusiones
  de metrología y retoques; no se afirma que cualquier PDF sea un plano.
- La propuesta de Archivos incorpora todos los candidatos de plano y conserva uno
  principal. Una elección vacía explícita sigue vacía. Los demás tipos conservan
  su selección anterior. No se interpreta qué plano corresponde a cada medida.
  Se aplica al elegir una carpeta nueva o cambiarla en el editor; no modifica los
  archivos de piezas ya guardadas ni despliega los cambios en el servidor.
- `collect`: los archivos de las carpetas de métodos de medición no se leen como
  mediciones ni consumen el límite. Se conservan como documentos del origen.
- Límites configurables `AUTO_MEASUREMENT_MAX_FILE_MB=32` y
  `AUTO_MEASUREMENT_MAX_TOTAL_MB=256` (MiB). Se aplican antes de abrir el archivo.
  La versión de lectura pasa a `automatic-tables-v5` para que una actualización
  explícita no reutilice como idéntico un resultado de la versión anterior.
  Los límites 16/128 que figuran en fichas históricas del 02/11 quedan sustituidos
  por estos valores en el código actual.
- Diagnóstico opcional de archivos, hojas y filas omitidas. No modifica qué medidas
  acepta el lector ni la política de valores generados o copias.

## Ejecutar

Script: [`probar_ingesta_web.py`](../prototypes/data-explorer/probar_ingesta_web.py).
Requiere las dependencias del backend. Desde un entorno que las tenga:

```text
python prototypes/data-explorer/probar_ingesta_web.py --root "RUTA/Exemples" --out "out/conocimiento/prueba-web/NUEVA-EJECUCION" --jobs 2
```

`--piece 3214` limita la prueba a una pieza; se puede repetir el argumento.
`--timeout 1800` fija el máximo de segundos por pieza. `--jobs 2` ejecuta dos piezas
a la vez (por defecto una; máximo cuatro). Cada pieza corre en un proceso
independiente. Usar una carpeta de salida nueva para conservar ejecuciones
anteriores; repetir la misma reemplaza sus resultados.

En Windows, se puede usar la imagen del backend con los originales montados en
solo lectura. Ejemplo desde la raíz del repositorio, en PowerShell:

```powershell
$testRepo = (Get-Location).Path
$testSource = 'C:\RUTA\Exemples'
$testOutput = Join-Path $testRepo 'out\conocimiento\prueba-web\NUEVA-EJECUCION'
New-Item -ItemType Directory -Force -Path $testOutput | Out-Null
docker run --rm --network none `
  --env PYTHONDONTWRITEBYTECODE=1 `
  --mount "type=bind,source=$testRepo,target=/repo,readonly" `
  --mount "type=bind,source=$testSource,target=/source,readonly" `
  --mount "type=bind,source=$testOutput,target=/output" `
  --workdir /tmp backend:latest `
  python /repo/prototypes/data-explorer/probar_ingesta_web.py `
  --root /source --out /output --jobs 2
```

El código se importa del repositorio montado, no de la copia que contenga la imagen.
La imagen aporta las dependencias. Antes de montar OneDrive en Docker, comprobar en
Windows que los originales están disponibles localmente; Docker no expone sus atributos
de recuperación. No se debe provocar su descarga inadvertidamente. El 13/11 se
comprobaron los 4.530 archivos: ninguno estaba solo en la nube.

## Qué se ejecuta y qué se guarda

- Se descubren carpetas con código de cuatro cifras hasta el nivel de `Tipo A/B`.
  Las remisiones que solo contienen README quedan aparte. Dos carpetas con contenido
  para un mismo código producen un error, no una selección silenciosa.
- Se ejecutan `part_setup.folder_files`, `reference_candidates` y
  `automatic_measurements.collect` del backend. No se duplica el lector.
- Se fuerza origen local, se impide el acceso a red y no se llama a ninguna función
  de escritura en la base de datos. No se importan correcciones ni se ejecuta OCR.
- `ejecucion.json`: fuentes de código con SHA-256, carpetas, fecha y parámetros.
- `piezas/CODIGO.json`: inventario de rutas/tamaños/fechas, candidatos de referencias,
  `.icp` encontrados, observaciones, estados de procedencia y diagnóstico por archivo,
  hoja y fila. Incluye límites efectivos, versión del lector y versiones de paquetes.
- `resumen.json` y `resumen.md`: resultados acumulados, guardados después de cada pieza.
  Un error en una pieza no impide probar las siguientes.

## Cómo interpretar el resultado

`read` significa que la ejecución terminó con observaciones; **no certifica que estén
todas ni que sean correctas**. `read_with_gaps` señala archivos pendientes, hojas con
cabecera nominal omitidas o filas rechazadas. Algunas hojas pueden ser plantillas
vacías o comparativas: requieren revisar su significado. `no_observations` y `error`
se muestran por separado.

Las observaciones incluyen registros generados/sin confirmar; el recuento utilizable
aplica la función productiva `usable_measurement`. No equivale al número de cotas:
una cota puede tener varias cavidades, muestreos y elementos.

Limitaciones explícitas:

- `.icp`: se inventarían, pero la web aún no los interpreta. La lectura de planos no
  forma parte de esta prueba de tablas.
- Tapa/base: se detecta su presencia en nombres de hoja y se advierte de la falta de
  identidad de componente. No se da por correcto el agrupamiento de sus cotas.
- El 3212 tenía una exclusión demasiado amplia en v5: `collect(pilot=True)`
  descartaba sus informes Excel de metrología. El adaptador específico lee casos
  de corrección y no sustituye esos informes. **Corregido en v6:** se leen los Excel
  de metrología por la ruta general. Las correcciones siguen fuera del ensayo.
  El balance de la primera ejecución, que se conserva debajo, corresponde a v5.
- No se prueban sesión/permisos de SharePoint, persistencia en PostgreSQL ni exactitud
  contra una referencia humana. Las pruebas automatizadas cubren los cambios de código.

## Resultados de la primera ejecución

Informe completo: [resumen de las 21 piezas](../out/conocimiento/prueba-web/2026-11-13-final/resumen.md).
JSON y detalles: `out/conocimiento/prueba-web/2026-11-13-final/`.

**21 carpetas probadas: 18 extraen observaciones, 2 no producen observaciones y
1 aborta por un CSV.** De las 18 que extraen, 17 tienen avisos de omisión; la otra
es 3309. No se interpreta ninguna como cobertura completa certificada.

| Pieza | Estado | Observaciones retenidas |
|---|---|---:|
| 2820 | Sin tabla de mediciones en la carpeta | 0 |
| 3051 | Extrae, con pendientes | 12.388 |
| 3197 | Extrae, con pendientes | 11.436 |
| 3212 | Extrae CSV; informes Excel descartados por la excepción del piloto | 3.120 |
| 3174 | Extrae, con pendientes | 196.200 |
| 3186 | Extrae, con pendientes | 29.255 |
| 3218 | Extrae, con pendientes | 542.909 |
| 3195 | Extrae, con pendientes | 59.039 |
| 3226 | DR sin cabecera/cavidades reconocidas | 0 |
| 3309 | Extrae, sin avisos de omisión | 4.447 |
| 3205 | Extrae, con pendientes | 44.625 |
| 3206 | Extrae, con pendientes | 19.869 |
| 3214 | Extrae, con pendientes | 2.164 |
| 3233 | Extrae, con pendientes | 62.902 |
| 3237 | Extrae, con pendientes | 27.741 |
| 3238 | Extrae, con pendientes | 18.638 |
| 3288 | Extrae tapa; omite las cuatro hojas DR(base) | 12.695 |
| 3056 | Extrae, con pendientes | 24.933 |
| 3167 | Aborta al leer Cav_1.csv | — |
| 3202 | Extrae, con pendientes | 7.779 |
| 3168 | Extrae, con pendientes | 22.127 |

Total de las carpetas que terminan: **1.102.267 registros retenidos**, de los que
**781.573** cumplen `usable_measurement`. Son observaciones, no cotas únicas ni un
inventario completo de las mediciones disponibles.

Mejora comprobada: las cinco piezas que excedían los límites anteriores —3174,
3205, 3206, 3218 y 3309— terminan ahora. El antes se calcula con los tamaños y
rutas inventariados, no con una segunda ejecución completa del lector antiguo.
3309 recupera el CAD `SUPPORT…`; 3288 ofrece diez planos candidatos y dos CAD
candidatos (solo uno se propone como CAD principal).

Fallos concretos pendientes:

- **3167:** `4- Metrologia/Customer/PPAP-3167-00_2/PPAP 3167-00_int02.1/Cav_1.csv`
  produce «Número no reconocido en la línea 1: mm». La colección aborta aunque
  hubiera leído archivos anteriores: el cero del JSON de error no demuestra que
  la carpeta carezca de mediciones. No se ha cambiado ese lector en esta tarea.
- **3288:** las cuatro hojas `DR(base)` se omiten por cabecera/cavidades no
  reconocidas. Además sigue faltando identidad de componente para separar las
  cotas de base y tapa. Se leen `DR(tapa)` y sus hojas de parámetros.
- **19 `.icp` sin interpretar:** 3202 (4), 3205 (5), 3206 (6) y 3288 (4).
- Hay **350 hojas omitidas con cabecera nominal** para revisar; pueden incluir
  plantillas o comparativas. No equivalen a 350 pérdidas de mediciones. También
  quedan identificadores con letras y filas con tolerancias invertidas.
- Rendimiento: 3218 tardó 887 s y 3195 951 s en estos lotes concurrentes. Son
  tiempos observados, no un ensayo controlado de rendimiento.

Se consolidan resultados completos por pieza de cuatro lotes (`paralelo`,
`restantes`, `complemento`, `ultimo`). Los tres primeros se detuvieron cuando sus
piezas necesarias ya estaban guardadas para evitar seguir repitiendo lecturas.
Los cuatro usaron las mismas huellas de los 110 archivos de código registrados;
las piezas repetidas coinciden en estado y recuentos. `ejecucion.json` identifica
el lote elegido para cada pieza. No se suman duplicados.

Los ensayos preliminares permanecen en `2026-11-13/`; no forman parte del balance
final. La repetición habitual solo necesita ejecutar el script una vez sobre las
21 carpetas. No se han modificado originales ni la base de datos de producción.

## Validación del código (13/11/2026)

- 83 pruebas de backend correctas, con PostgreSQL `app_test` en un stack aislado:
  lectores, procedencia de fórmulas, selección de referencias, editor y flujo de piezas.
- Mypy correcto en los cuatro módulos productivos modificados; Ruff correcto.
- Dos pruebas específicas del frontend correctas: todos los planos conservando un
  principal y respeto de una eliminación explícita.
- TypeScript y compilación Vite correctos, con los avisos existentes de tamaño y OCCT.
- La suite de navegador `piece-editor.test.cjs` no llegó a ejecutar sus aserciones:
  `warmUp` agotó 180 segundos cargando `/piece-test`, en dos intentos. No se presenta
  como una validación de interfaz superada. El fallo no procede de una aserción sobre
  los cambios.

## Informe visual para enseñar

Archivo independiente: [lectura-carpetas.html](../out/conocimiento/prueba-web/2026-11-13-final/lectura-carpetas.html).
Se abre con doble clic, funciona sin conexión y se puede compartir como un único
archivo. Incluye las 21 piezas seleccionables, filtros por estado, ejemplos de
archivos/hojas/filas, comparación de los cinco bloqueos de tamaño y una vista de
impresión que incluye todas las piezas aunque haya un filtro activo.

Para regenerar esta presentación sin volver a leer los originales:

```text
python prototypes/data-explorer/crear_informe_ingesta_html.py --input out/conocimiento/prueba-web/2026-11-13-final/resumen.json --output out/conocimiento/prueba-web/2026-11-13-final/lectura-carpetas.html
```

Solo usa la biblioteca estándar. La plantilla es
`prototypes/data-explorer/informe_ingesta_web.html`; los recuentos y diagnósticos
se insertan desde el JSON. Los textos explicativos de casos concretos corresponden
a esta ejecución del 13/11: deben revisarse si se prepara una presentación de una
ejecución posterior. No es una pantalla de la web ni del visor.

## Segunda revisión sin IA · lector v6

Cambios posteriores al primer balance:

- Se elimina la exclusión general de Excel para el piloto 3212; no se modifica el
  adaptador de correcciones ni las correspondencias específicas de sus CSV.
- Se reconoce el marcador de exportación SPC `#P#` antes de interpretar columnas
  CMM. Se conserva el archivo como pendiente explícito y continúa la lectura de
  otros formatos. No se importan las cifras SPC sin aclarar campos y procedencia.
- Los errores numéricos de un CSV CMM compatible siguen abortando la colección;
  no se ha añadido una regla de ignorar cualquier error.
- El estado de la web queda parcial mientras haya archivos de mediciones
  pendientes, incluso si finaliza el trabajo separado de correcciones.

Nueva ejecución: `out/conocimiento/prueba-web/2026-11-13-sin-ia/`.
Las pruebas de código han pasado: 65 de lectores/procedencia/piloto y 23 de API,
con PostgreSQL `app_test` aislado; Mypy correcto en los cuatro módulos modificados.
Ruff correcto. El stack de pruebas se ha retirado; no se ha desplegado la web.

**21 carpetas terminadas: 19 aportan observaciones, 2 no producen observaciones,
0 errores que interrumpan la carpeta.** De las 19, 18 conservan pendientes; 3309
termina sin avisos de omisión. No se certifica cobertura completa.

### Qué significa que 18 sean parciales

El script marca `read_with_gaps` con cualquier archivo pendiente, hoja omitida
con cabecera nominal o fila rechazada. No calcula una proporción de cotas leídas
ni pondera la importancia de la omisión. Las 18 tienen hojas señaladas; 17,
archivos sin tabla reconocida; 16, identificadores rechazados; 5, tolerancias
invertidas. Estos grupos se solapan y no se suman.

En las 18 hay 460 hojas señaladas: 364 por nombre no admitido y 96 por cabecera
o cavidades no reconocidas. Entre los nombres repetidos están `FULL_SPC` (87),
`Template` (39), `SKETCH` (11) y `3D CMM` (10). Son ocurrencias en archivos, no
formatos únicos ni mediciones perdidas. Hay que revisar contenido y función antes
de decidir si deben importarse o excluirse justificadamente.

El contraste de gravedad es visible en los casos concretos:

- **3212:** su único archivo/hoja pendiente es `3212-00_intern.07.xls`,
  `Comparation KnO x VdB`, por nombre de hoja no admitido. No se ha validado que
  carezca de observaciones nuevas, pero no equivale a fallar los ocho informes leídos.
- **3288:** se omiten cuatro `DR(base)`; además falta identidad de componente.
  Es una carencia concreta de lectura y agrupamiento que debemos resolver nosotros.
- **3214/3233:** los identificadores de zona no encajan en el lector numérico;
  no hace falta volver a preguntar si son zonas. Una zona puede contener varias
  cotas, por lo que admitir letras sin resolver la identidad tampoco basta.

La etiqueta común es un aviso conservador, no evidencia de 18 problemas
independientes ni de 18 carpetas inutilizables. Tampoco permite afirmar que todas
las omisiones sean menores. La distinción cavidad/muestreo ya existe en el lector;
las contradicciones de fuentes se preguntan con ejemplos concretos en el paquete
para INTEPLAST.

| Pieza | Antes (v5) | Ahora (v6) | Sigue pendiente |
|---|---|---|---|
| 3212 | 3.120 registros; Excel descartado | 8.041 registros; CSV y 8 informes Excel leídos | Un informe Excel sin tabla reconocida; revisar otras omisiones |
| 3167 | Aborta en `Cav_1.csv` | 105.770 registros de archivos compatibles | 4 exports SPC `#P#` sin interpretar, además de otros formatos y hojas omitidos |
| 2820 | Sin observaciones | Sin observaciones | No hay informe tabular de mediciones |
| 3226 | Sin observaciones | Sin observaciones | Estructura de informe no reconocida |

Total: **1.212.958 registros retenidos**, de los cuales **890.024** cumplen
`usable_measurement`. Son observaciones, no cotas únicas. La recuperación de
registros no prueba por sí sola su cobertura o exactitud frente al original.

Los resultados de lectura de las otras 19 piezas coinciden con v5, excluyendo
versión del lector y tiempo de ejecución. El JSON v5 consolidado redondeó los
nanosegundos de los inventarios al pasar por JavaScript: se contrastan a esa
precisión, con rutas y tamaños idénticos (diferencia máxima: 200 ns).
Se comprobaron las huellas de los 110
archivos de código registrados: no cambiaron durante la ejecución. Esta vez se
ejecutaron las 21 carpetas en un solo lote, con cuatro procesos y sin red.

Evidencia: [resumen](../out/conocimiento/prueba-web/2026-11-13-sin-ia/resumen.md),
[comparación](../out/conocimiento/prueba-web/2026-11-13-sin-ia/comparacion.json),
[validación](../out/conocimiento/prueba-web/2026-11-13-sin-ia/validacion.json) e
[informe visual actual](../out/conocimiento/prueba-web/2026-11-13-sin-ia/lectura-carpetas.html).

Para regenerar el HTML con el antes/después real, sin releer los originales:

```text
python prototypes/data-explorer/crear_informe_ingesta_html.py --input out/conocimiento/prueba-web/2026-11-13-sin-ia/resumen.json --previous out/conocimiento/prueba-web/2026-11-13-final/resumen.json --output out/conocimiento/prueba-web/2026-11-13-sin-ia/lectura-carpetas.html
```

La lista concreta para INTEPLAST está en
[Preguntas abiertas: extracción sin IA](../docs/preguntas-abiertas.md#extraccion-sin-ia).
Incluye la A27 sobre un export `#P#`, reutiliza las preguntas ya abiertas y separa
las aclaraciones del cliente de los cambios que corresponden a nuestro lector.
No se ha enviado ningún mensaje a INTEPLAST.
