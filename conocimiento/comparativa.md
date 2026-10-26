# Comparativa entre features y piezas

> Inventario de `Exemples`: 4.530 ficheros, 8 features, 21 piezas con datos.
> Contrastado el 2026-10-23 por ruta, tamaño y SHA-256. Esto no equivale a interpretar íntegramente
> cada imagen, CAD o comprimido. Cifras de la biblioteca y de `perfil_ppap` / `perfil_correccion`.

## Cifras por feature

| Feature | Piezas | Ficheros | CSV (todos) | TXT `#P#` | Libros PPAP | Diap. inventariadas | % título numerado | Planos `.icp` | STEP | STL | `.mfr` |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| [0 Bolt Eye](0-bolt-eye/README.md) | 4 | 580 | **137** | 0 | 42 | 219 | 76 % | 0 | 7 | 2 | 3 |
| [1 Clips](1-clips/README.md) | 6 | 1.049 | 1 | 0 | **237** | **890** | 90 % | 0 | 17 | 7 | 2 |
| [2 Nervios](2-nervios-soldadura/README.md) | 3 | 748 | 0 | 0 | 104 | 198 | 47 % | 11 | 39 | 5 | 1 |
| [3 Paredes delgadas](3-paredes-delgadas/README.md) | 3 | 647 | 3 | 135 | 93 | 49 | 100 % | 0 | 36 | 6 | 3 |
| [4 Tetones](4-tetones/README.md) | 1 | 107 | 0 | 0 | 11 | 17 | 100 % | 4 | 3 | 2 | 0 |
| [5 Anclajes](5-anclajes/README.md) | 0 | 1 | — | — | — | — | — | — | — | — | — |
| [6 Pockets](6-pockets/README.md) | 3 | 1.074 | 5 | 356 | 63 | 112 | 83 % | 4 | 255 | 5 | 1 |
| [7 Planitudes](7-planitudes/README.md) | 1 | 324 | 0 | 73 | 33 | 49 | 33 % | 0 | 8 | 1 | 0 |

«Diap. inventariadas» = filas de `perfil_correccion`: todos los PPTX de cada carpeta, incluidas
versiones repetidas, plantillas y documentos de otras piezas. **No es un recuento de acciones
propias ni ejecutadas.** «% título numerado» = diapositivas con número `n.m` reconocido.
CSV cuenta extensiones, no un único formato: en Bolt Eye hay 50 CSV de puntos, 75 informes
individuales CMM y 12 comparativas; Pockets contiene 1 CMM y 4 `#P#`. Los `#P#` suman
**568 ficheros: 564 TXT + 4 CSV**. Comprobado leyendo todos los TXT/CSV originales.

## Lo que se repite en todas (y ya conocíamos del 3212)

- **Informe PPAP de INTEPLAST** (plantilla de 1999, `INTERNAL DIMENSIONAL REPORT`, hojas `INTRO`/`HISTORY`/`DR*`)
  en todas las piezas con metrología. Responsables más frecuentes: Xavier Arcos, DB, Michal Heidenreich,
  Václav Vladyka (escritos con y sin mayúsculas).
- **Plan de corrección PPTX** con la estructura del 3212 (título con nº de plan y fecha, `Longitud 70mm`,
  *situación actual* → *plan* con zona en rojo) en casi todas las piezas.
- **Informes que heredan bloques de informes anteriores** (I-001): 3212, 3288, 3051.
- Nombres inconsistentes, copias (`Copia de …`, `- copia`, `_rev1_`), versiones múltiples y ficheros de otras piezas.
- Multilingüe: castellano, catalán, inglés, alemán y checo.

## Lo que cambia entre piezas (lo que un lector genérico tiene que admitir)

| Aspecto | Variantes encontradas |
|---|---|
| Esqueleto de carpetas | Numeración 1–8 del 3212, con 7 carpetas presentes (falta la 2) frente a 7 en las entregas de 2026-10 (`1- 2D y 3D pieza` … `7- Pieza real STL`); nivel extra `Tipo A/B` en Clips; carpetas de feature con solo un `Readme.txt` que remite a otra (3167, 3214, 3205, 3206) |
| Medición CMM | CSV por bloques (3212, 3197 y soportes de otras familias, p. ej. 3174/3167); variantes comparativas en 3237/3238; **export `#P#`** (564 TXT y 4 CSV); PPAP del cliente `.xlsm` por cavidad (3167); KEYENCE/vídeo/galgas en 3288, 3214, 3309 |
| Cabecera PPAP | inglés (`Part Name`, `Drawing nº`) o **castellano** (`Nombre pieza`, `Nº Plano`, `CP`/`SPC`); campos corridos o `#REF!`; fechas `1899-12-31`, `xx`, texto |
| Columnas del DR | Nominal/Tol en D–F (3212, 3288) o con **`class`** en E y Tol en F–G (3197, shroud); cavidades `Cav.13`, `CAV.1`, `C1` o **solo número** (`1`…`20`); de 4 a 32 columnas de cavidad; NOK y comentarios donde acaben las cavidades. Conservar los identificadores: [cabecera del 3212](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro) |
| Hojas | `DR(3D)`, `DR`, `DR(100%)`, `DR_100%`, `DR_8cav.`, `DR_CMM`, `DR(tapa)`/`DR(base)`, `DR_PAR`, `DR cicle`, `DR-55º`… |
| Previsión de la corrección | libro aparte `DR(100%)` con `Retoc` en O (3212); en T con previsión U–AB (3197); **dentro del informe** (`Dim`/`Corr.`, shroud); **en la tabla del PPTX** (3051); ninguna (3288) |
| Título del plan | `Tool correction 1.33 (DIM. Nr.170)`; `Correcció nr. 1.1 (DIM. Nr. 54, 57 and 60)`; `Tool correction DIM#5: …` (3309); `1 / . Dim 210Ø21,5-0,2` (3051: flecha U+F0E0 entre cota y nominal, perdida en algunas extracciones); solo imágenes (3056); presentaciones de análisis sin numerar (3168, 3226) |
| Planes por pieza | 1–2 (3212, 3214) hasta **numeración 15** (3218, con huecos), en carpetas `YYYYMMDD_Nth loop…` con varias versiones; numeración que se reinicia (shroud tras postizos) o no coincide con el nombre del fichero |
| Método de medida | DOCX del cliente (Bolt Eye); **XLS `MM_revNN.xls` con hoja `DIMENSIONS`** (Clips, 3309); fichas PDF de INTEPLAST (3288); ensayos del cliente (TES) |
| Plano | escaneo sin texto (3212); vectorial con texto pero **sin globos** (3197, 3051); **con globos + `.icp`/`.prf`** que dan su posición (3205, 3206, 3288, 3202; 19 planos) |
| Condición de medida | pieza montada (*clipped*, Clips) o libre; condiciones de proceso en la ruta (3197: `135ºC/500bar`, boquilla); fuerza de cierre (3168) |
| Moldflow | `.mfr` (10 piezas); `README.txt` *«No Moldflow information available»*; un vídeo `.avi` de llenado (3206) |

## Implicaciones para la app

La variación de datos exige conservar pieza, revisión, cavidad y procedencia; comparar
versiones por contenido; y separar medidas, previsiones y valores derivados. Para fórmulas
aleatorias y sus exportaciones, consultar [I-003](incongruencias.md#i-003-en-detalle).

El estado del código no se mantiene en esta comparativa. Consultar:

- [Cotas y evidencia](../docs/cotas-y-evidencia-web.md#datos-y-alcance): formatos realmente
  admitidos y límites del piloto.
- [Ingesta automática](../docs/ingesta-automatica.md): diferencias observadas, prototipos
  de la biblioteca y propuesta para generalizar la aplicación.
- [Ficheros externos](../docs/ficheros-externos.md): configuración de raíz y selección de carpetas.
- [Próximos pasos](../docs/proximos-pasos.md): estado de las tareas pendientes.
