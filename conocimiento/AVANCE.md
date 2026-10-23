# Avance de la lectura de Exemples

Registro de trabajo para poder retomar entre sesiones. Actualizar al terminar cada paso.

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

- [ ] Ampliar el campo `comprobacion` a más hallazgos numéricos (H-001, H-305, I-203, I-204…).
- [ ] Revisar con INTEPLAST el uso del «Cpk generator» y qué versión del Inf_04 del 3167 se entregó
      (I-003, I-603). Lo decide Eduard.

- [ ] Ajustar la transformación `.icp` → PDF en los otros 18 planos (validado solo BSG-296-02).
- [ ] Profundizar: rebabas en nervios tras postizos (shroud), loops del 3174, `#P#` ↔ cotas en otras piezas.
- [ ] Contenido de los comprimidos (zip, rar, cab): de momento solo se lista.
- [ ] Macros de los `.xlsm` (olevba): leída `Generate_Sheets` del «Cpk generator»; quedan las demás.
- [ ] Muestreo visual de fotos, PDF sin texto (247), 3 libros que solo tienen imágenes y vídeos; diapositivas cuyo texto está en imágenes (3056).
- [ ] `docs/preguntas-abiertas.md`: revisar (obsoleta) con `incongruencias.md`; anotado en `TODO.md`.
