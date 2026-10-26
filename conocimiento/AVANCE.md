# Avance de la lectura de Exemples

Registro de trabajo para poder retomar entre sesiones. Actualizar al terminar cada paso.

## Seguimiento de las rectificaciones · 23–26/10/2026

Eduard autorizó corregir `docs/` y el código dentro de `conocimiento/`. Se mantuvo intacto
el código de la aplicación y se conservaron los originales de `Exemples`.

- Corregidos los tres errores del revisor: **10 `#REF!` del 3167**, identificadores reales de
  los CSV `#P#`, y **rev.06 en los nueve informes del 3212**. La lectura BIFF de los 18 XLS
  del 3167 distingue 170 fórmulas válidas y 10 rotas; no confunde `RAND()` con `#REF!`.
- Confirmadas **cuatro cavidades del 3212** en `INTRO!C40`; recuperados metadatos de
  `DR(SKETCH)` que faltaban en otras hojas. La app sigue con el piloto 3212.
- Sincronizados `docs/modelo-datos.md` y `docs/preguntas-abiertas.md`: rev.07 del 21/06/2022,
  fecha de creación PDF separada, velocidades de inserción distintas e IGES separado del TXT 3D.
- Añadida entrada guiada en `README.md`, separación entre conocimiento vigente e historial,
  y nota de las 38 rutas largas. Reducidas cautelas redundantes sin presentar propuestas como
  acciones ejecutadas. Corregida la cobertura declarada de la muestra de 7.291 valores.
- Lectores v2: firma PDF antes de abrir XLS; fórmulas OOXML identificadas por su tipo;
  conservación de resultados vacíos o ausentes como NULL. Los perfiles PPAP/DR tratan esos
  NULL como datos ausentes. Las reparaciones I-003/I-004 ya no dependen de cambios manuales.
- Verificador: semilla aplicada también a celdas, coordenadas de la muestra conservadas,
  contraste XML de fórmulas/textos y presencia de caché, y recuento de documentos sin muestra.
  **Nueve pruebas de regresión pasan**, incluido el XLS con un ZIP de dibujos incrustado,
  el tratamiento de NULL y la conservación de la tabla anterior cuando una reconstrucción falla.
- La primera reconstrucción completa de `celda_aleatoria` detectó un fallo de Excel en cadena
  después de un error de apertura. Se restauró el respaldo completo y se corrigió la herramienta:
  proceso aislado por XLS, reintento, macros desactivadas y sustitución atómica solo sin errores.
  La lectura BIFF independiente recuperó las 353.732 coordenadas aleatorias de los 68 XLS,
  sin faltantes ni adicionales; ese contraste no compara literalmente el texto de las fórmulas.
  **La reconstrucción final con procesos aislados terminó sin errores:** 649.977 celdas en
  191 libros, idénticas al respaldo en coordenadas, fórmulas y valores. Se examinaron 642 XLS
  candidatos y se abrieron sobre copias los 78 con tokens sospechosos; el PDF se descartó por firma.
- Reextraídos **322 XLSX/XLSM y el PDF nombrado `.xls`**. Contraste de todos los nodos de
  fórmula contra XML: **3.584.670 fórmulas**, **296.245 aleatorias**, **400.094 con valor XML
  vacío o ausente**, sin discrepancias de coordenadas o contadores. Ningún valor previo cambió.
  Una muestra adicional guarda **951 comprobaciones XML**, todas correctas, con coordenadas,
  semilla por documento, resultado esperado/obtenido y SHA-256 para repetirla.
- Regenerados los perfiles: **1.364 hojas PPAP**, **1.791 hojas DR** y **1.671.138 valores DR**,
  con los mismos recuentos anteriores. **64 hallazgos y 11 comprobaciones SQL** concordantes;
  `PRAGMA quick_check` y claves foráneas sin errores. El verificador ejecutado con semilla
  `20261026` añade **24/24 comprobaciones CSV** correctas en tres documentos, sin documentos
  seleccionados que queden sin muestra. Sus coordenadas y resultados constan en `auditoria`.
- Verificados los **465 archivos versionados fuera de `conocimiento/` y `docs/`**, sin cambios.
  El control SHA-256 repetido el **26/10** confirmó los **4.530 originales** intactos en contenido,
  tamaño y fecha de modificación, sin altas ni bajas.

Respaldo previo de la biblioteca, manifiestos y resultados en
`datos/revision-2026-10-23/seguimiento-implementador/` (fuera de Git).

## Revisión doble del 23/10/2026

Encargo inicial: revisar toda la base de conocimiento contra `Exemples`, con dos pasadas y
como máximo dos subagentes. En esa fase solo se modificó `conocimiento/`, sin tocar código.
Después Eduard autorizó corregir también `docs/` y el código dentro de `conocimiento/`;
el seguimiento de esas rectificaciones figura al inicio de este registro.
Los apartados anteriores del trabajo, conservados debajo, son un registro histórico: sus cifras
de cobertura y sus conclusiones deben leerse con las rectificaciones de esta revisión.

### Primera pasada: contraste documental y de datos

- Leídos los **32 Markdown** y los **56 hallazgos iniciales**. Revisión repartida entre Bolt Eye,
  familias 1–7 y documentación transversal; todas las familias incluidas.
- Inventario original completo: **4.530 archivos, 43 extensiones, 20.760.567.122 bytes**.
  Ruta, tamaño y SHA-256 coinciden con la biblioteca. Se usaron rutas largas de Windows para
  abrir 38 fotografías de rutas largas. La enumeración las encuentra; el fallo está en
  abrirlas con la ruta ordinaria en este Windows, no en que necesariamente desaparezcan al listar.
- Lectura directa del XML de **160 PPTX, 1.534 diapositivas**, incluidos planes, variantes,
  plantillas y documentos ajenos a la carpeta donde están archivados. El recuento bruto no
  equivale al número de correcciones propias ni ejecutadas.
- Comprobados los **979 archivos con extensión XLS/XLSX/XLSM**: 978 libros abiertos con calamine
  y un PDF mal nombrado. **7.291 valores numéricos muestreados coinciden** con los originales.
  Hubo muestras en **919 libros**; **60 archivos quedaron sin muestra**, incluido el PDF mal
  nombrado. De esos 60, 54 sí contienen números que los filtros no seleccionaron.
  El manifiesto guardó recuentos y fallos, pero no las coordenadas de los aciertos:
  esa muestra exacta no quedó reproducible. Son límites de cobertura, no discrepancias detectadas.
  La coincidencia de valores guardados no demuestra que sean mediciones reales (I-003).
- Revisión XML de los **322 XLSX/XLSM**, incluidas fórmulas compartidas: **296.245 fórmulas
  aleatorias directas**. Junto con los XLS previamente registrados, el total corregido es
  **649.977 celdas en 191 libros de 9 piezas**. Las fórmulas BIFF8 de todos los XLS no se
  reextrajeron en esta revisión; se contrastaron sus valores guardados y la trazabilidad de fuentes.
- En el 3212 se recalcularon los **3.376 registros de sus 16 CSV**, los resúmenes de los
  **144 perfiles PDF**, las previsiones XLS, los 12 pares PUNTS/PUNTS_NOUS y la relación
  geométrica de los **15 DXF y 12 IGES** con los TXT. En Bolt Eye también se leyeron los
  137 CSV, 158 TXT, 7 STEP y métodos DOCX. Se inspeccionaron visualmente los detalles
  de planos/métodos que sustentan las nuevas rectificaciones.

### Segunda pasada: revisión cruzada e integración

- Cada subagente releyó las fichas del otro y contrastó los puntos decisivos con originales.
  La documentación transversal recibió además una revisión independiente de integración.
- Se corrigieron las magnitudes distintas entre `rev1`/`rev1_` del plan 2 del 3212 y las
  atribuciones de cotas. El material visual del 3212 sí consta; el método del 3051 sí identifica
  sus Bolt Eyes. Las temperaturas de boquilla del 3197 y sus tolerancias divergentes quedaron explícitas.
- **IGES no equivale a TXT 3D:** tiene Z constante, sin transformaciones. DXF y TXT sí coinciden
  hasta el redondeo comprobado. Se retiró la recomendación de deduplicar IGES como otra copia 3D.
- El cajetín del plano 3212 fecha la **rev.07 el 21/06/2022**, no el día de impresión PDF de 2025.
  Queda abierta la discrepancia **0,1 frente a 0,2 mm/s** del ensayo de inserción (I-207).
- El supuesto plan del 3174 en la carpeta 3218 contiene referencias explícitas al 3218 y es
  distinto del plan real del 3174. Se recuperó su atribución y se limitó la laguna a loops 2–5.
- El método actualizado del 3288 sí identifica **cota 80 del conjunto, revisión 2**, como control
  del remachado y ausencia de GAP. Se distinguió de las cotas 80 de otros componentes/revisiones.
- Se separaron plantillas P3033 y documentos de otras piezas, versiones fechadas en 2026 dentro
  de carpetas de 2023 y propuestas frente a ejecución o aprobación. Se confirmaron los ocho
  valores alterados del PPAP Inf_04 del 3167, sin inferir una concesión formal del cliente.
- Comprobados directamente todos los TXT/CSV: **568 archivos `#P#` = 564 TXT + 4 CSV**.
  Se corrigieron los recuentos y las reglas que equiparaban extensión con formato, número de
  columnas con cavidades físicas, o coincidencia de valores con copia demostrada.

### Reparaciones de la biblioteca y comprobaciones finales

- **I-004, documento 4218:** el `.xls` que contiene un PDF se reextrajo como dos páginas;
  se retiraron 1.868 elementos y 2.613 celdas espurias de su anterior lectura como Excel.
- **I-003:** añadidas 1.255 fórmulas reales sin valor cacheado; eliminadas 84 marcas de fórmula
  que correspondían a texto literal. Se preservaron NULL y textos originales, y se corrigieron
  94 contadores de fórmulas de `estructura` conforme al XML. No se recalcularon libros ni ejecutaron macros.
- **62 hallazgos** con identificadores únicos y **9 comprobaciones SQL** concordantes.
  Evidencias locales con rutas válidas y SHA-256 completos; enlaces de documentación revisados.
- Verificación de integridad al cierre: **4.530 originales sin cambios de contenido, tamaño o
  fecha de modificación**, sin altas ni bajas; **491 archivos protegidos sin cambios**, incluido
  el código de `conocimiento/herramientas/` y los archivos versionados fuera de `conocimiento/`.
- Manifiestos, resultados del contraste y respaldo de los registros reparados en
  `datos/revision-2026-10-23/` (datos locales ignorados por Git). `git diff --check` y comprobación
  de claves foráneas sin errores. Las reparaciones fueron inicialmente manuales; el seguimiento
  posterior las incorpora a los lectores para hacerlas reproducibles (ver [README.md](README.md)).

**Límites:** ambas revisiones cubren la documentación completa, con contraste dirigido y controles
masivos de fuentes. No equivalen a interpretar íntegramente cada foto, vídeo, CAD/Moldflow, macro
o archivo dentro de comprimidos. Inventario completo y ausencia de errores de extracción no
demuestran cobertura semántica completa. Las dudas de revisión aplicable, autorización de
tolerancias, ejecución de acciones y entrega efectiva al cliente siguen abiertas cuando no
hay evidencia. En esta fase inicial no se contactó con la empresa ni se modificó documentación
fuera de `conocimiento/`.

## Encargo (Eduard, 2026-10-21)

- Leer **todos** los ficheros de `Exemples` (incluidos los que estén solo en la nube), sin
  modificar, mover ni crear nada allí. No escribir en `C:\edu`.
- Volcar en `conocimiento/` todo lo útil para entender los datos: significado, importancia,
  orden y estructura natural, diferencias entre features, qué falla y qué habría que cambiar en
  la app. No es para la app: es contexto para Claude.
- Ir **feature a feature**. Como mucho un agente auxiliar; el trabajo lo hace Claude.
- Si hay muchos ficheros casi iguales (gráficas, fotos), extraer datos de todos y mirar a ojo una
  muestra, comprobando que el resto no aporta nada distinto.
- Lo que no cuadre o haya que pedir a INTEPLAST: a `conocimiento/incongruencias.md`.
  `docs/preguntas-abiertas.md` queda en `docs/` y está pendiente de revisión (ver `TODO.md`).
- `docs/` queda para la aplicación. Respuestas breves y directas.

## Hecho

- [x] Ruta nueva del Bolt Eye en repo y `.env` (`Exemples/0- Bolt Eye`). App verificada: 284/284
      originales disponibles.
- [x] Estructura `conocimiento/`, `.venv` con `--system-site-packages` (+ openpyxl, python-pptx,
      ezdxf, olefile, extract-msg, odfpy, python-calamine), `.gitignore` de `datos/` y `.venv/`.
- [x] Herramientas: `inventariar.py`, `extraer.py`, `lectores.py`, `esquema.sql`, `consultar.py`,
      `perfil_ppap.py`, `perfil_correcciones.py`, `globos_icp.py`.
- [x] Inventario: 4.530 ficheros, 43 extensiones.
- [x] Movidos de `docs/`: `3212/` → `0-bolt-eye/3212/`, `formatos-parsing.md`, `visores.md`,
      `otros-proyectos.md` → `0-bolt-eye/`. 85 enlaces reescritos.
- [x] Analizados y documentados: 0 Bolt Eye (README + 3197, 3051, 2820), 1 Clips, 2 Nervios,
      3 Paredes delgadas, 4 Tetones (README + 3288), 5 Anclajes. Incongruencias I-0xx…I-5xx y
      hallazgos H-xxx en `incongruencias.md` / `hallazgos.jsonl`.
- [x] `.icp` de planos con globos descodificado (tabla `globo`, 19 planos).

- [x] Extracción completa: 4.530 ficheros, 0 errores (reintentos con Excel COM para XLS que xlrd no
      lee y texto aproximado para `.doc` bloqueados por Word). Incluye los 220 que estaban en la nube.
- [x] 6 Pockets y 7 Planitudes documentados. `comparativa.md` y `README.md` de `conocimiento/`.
- [x] CLAUDE.md reorganizado: trampas y recetas → `trampas.md`; documentación de datos → `conocimiento/`.
- [x] Revisión visual: plano con globos del 3288 (cliente **B. Braun**, globos azules = sellos del `.icp`).

- [x] Segunda pasada (2026-10-21): globos `.icp` validados (infra-CONVERT); `#P#` ↔ cotas PPAP (eISIR);
      `.dfd` = Q-DAS; historia de los 15 loops del 3218 (`1-clips/3218.md`). Comentarios del backend actualizados.

- [x] Verificación (2026-10-21, tercera pasada):
  - Reinventario sin cambios; todos los ficheros ya locales.
  - `verificar.py`: muestra al azar comparada con los originales por otro método (Excel COM, XML crudo,
    pdfplumber, bytes). Última tanda (semilla 99, 15 ficheros por extensión): 650/653 correctas; los 3
    fallos se explican (2 celdas `ALEATORIO.ENTRE` aún sin marcar, ya corregido, y un carácter checo que
    PyMuPDF y pdfplumber leen distinto en un plano CAD). Antes se corrigieron falsos fallos del propio
    verificador (errores CVErr de Excel, booleanos, texto de Word partido en runs, separador CSV).
  - 🔴 **Valores generados con `RAND()`** (I-003): `formulas_aleatorias.py` y tabla `celda_aleatoria`. Macro
    `Generate_Sheets` leída con olevba. Los SPC `#P#` del 3167/3168/3237 salen de esos libros.
  - **Dos versiones del Inf_04 del 3167** con valores cambiados (I-603).
  - Lectores: DXF con nº de vértices y caja (confirma la trampa 13 en los 15 DXF del 3212); libros sin
    ninguna celda pasan a `sin_texto` con el nº de imágenes (3 libros). `celda_aleatoria` incluye también
    `ALEATORIO.ENTRE` (nombre en castellano guardado sin resolver): 648.806 celdas en 191 libros.
  - `verificar.py --hallazgos`: rutas, SHA-256, ids y 7 cifras clave recalculadas por SQL (campo
    `comprobacion`). Corregidas 2 rutas de evidencia (H-602, I-601) y cifras desfasadas (H-501: 103
    `#P#` en el 3237, ninguno en el 3238; hojas de `perfil_ppap` y diapositivas en READMEs y `comparativa.md`).
  - Investigación web: detección de datos fabricados (cola plana sin valores fuera, Cpk demasiado altos,
    comparar R&R con capacidad; análisis de últimos dígitos), capas bruto/derivado/curado con trazabilidad,
    conjuntos de preguntas con respuesta conocida para comprobar una base de conocimiento. Aplicado:
    `comprobacion` en los hallazgos y la regla de mirar `celda_aleatoria` antes de usar un valor.

- [x] Plan de ingesta automática (2026-10-21), en [docs/ingesta-automatica.md](../docs/ingesta-automatica.md):
  - Prototipo `lector_dr.py` (tablas `lectura_dr`, `medida_dr`): 1.791 hojas y 1,67 M de valores; sobre
    las 1.335 hojas PPAP lee 1.236 frente a 738 del lector actual de la app. Concordancia con la NOK
    del libro: 96,2 %. Plantilla de cliente frente a `#P#`: 5.188 de 5.188 iguales.
  - `python-calamine` en el `.venv`: abre los 14 `.xls` que `xlrd` no abre. **Corregido un error de la
    biblioteca**: en esos libros, Excel por COM recalculaba `RAND` al abrir y se guardaba un valor
    distinto del del fichero (8.422 celdas, todas `RAND` o dependientes). Ahora los valores salen
    de calamine (84.038 de 84.038 iguales) y las fórmulas de COM.
  - Prueba manual de 14 correcciones: el texto da el tipo de acción en 12; la imagen hace falta para
    zona y sentido en 7.

## Pendiente (siguientes tandas)

- [ ] Ampliar el campo `comprobacion` a más hallazgos numéricos (H-001, H-305, I-203…; I-204 ya comprobado).
- [ ] Revisar con INTEPLAST el uso del «Cpk generator» y qué versión del Inf_04 del 3167 se entregó
      (I-003, I-603). Lo decide Eduard.

- [ ] Ajustar la transformación `.icp` → PDF en los otros 18 planos (validado solo BSG-296-02).
- [ ] Profundizar: rebabas en nervios tras postizos (shroud), loops del 3174, `#P#` ↔ cotas en otras piezas.
- [ ] Contenido de los comprimidos (zip, rar, cab): de momento solo se lista.
- [ ] Macros de los `.xlsm` (olevba): leída `Generate_Sheets` del «Cpk generator»; quedan las demás.
- [ ] Muestreo visual de fotos, PDF sin texto (247), 3 libros que solo tienen imágenes y vídeos; diapositivas cuyo texto está en imágenes (3056).
- [x] `docs/preguntas-abiertas.md` revisada el 26/10/2026: entrega ampliada, preguntas vigentes y resoluciones enlazadas a fichas canónicas. [Revisión documental](../docs/revision-2026-10-26.md).
