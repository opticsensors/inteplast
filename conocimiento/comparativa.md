# Comparativa entre features y piezas

> Lectura completa de `Exemples` del 2026-10-21: 4.530 ficheros, 8 features, 21 piezas con datos.
> Cifras de la biblioteca (`consultar.py`) y de las tablas `perfil_ppap` / `perfil_correccion`.

## Cifras por feature

| Feature | Piezas | Ficheros | CSV CMM | TXT `#P#` | Libros PPAP | Diap. corrección | % plantilla `Tool correction` | Planos `.icp` | STEP | STL | `.mfr` |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| [0 Bolt Eye](0-bolt-eye/README.md) | 4 | 580 | **132** | 0 | 42 | 219 | 76 % | 0 | 7 | 2 | 3 |
| [1 Clips](1-clips/README.md) | 6 | 1.049 | 1 | 0 | **237** | **890** | 90 % | 0 | 17 | 7 | 2 |
| [2 Nervios](2-nervios-soldadura/README.md) | 3 | 748 | 0 | 0 | 104 | 198 | 47 % | 11 | 39 | 5 | 1 |
| [3 Paredes delgadas](3-paredes-delgadas/README.md) | 3 | 647 | 1 | 135 | 93 | 49 | 100 % | 0 | 36 | 6 | 3 |
| [4 Tetones](4-tetones/README.md) | 1 | 107 | 0 | 0 | 11 | 17 | 100 % | 4 | 3 | 2 | 0 |
| [5 Anclajes](5-anclajes/README.md) | 0 | 1 | — | — | — | — | — | — | — | — | — |
| [6 Pockets](6-pockets/README.md) | 3 | 1.074 | 1 | 356 | 63 | 112 | 83 % | 4 | 255 | 5 | 1 |
| [7 Planitudes](7-planitudes/README.md) | 1 | 324 | 0 | 73 | 33 | 49 | 33 % | 0 | 8 | 1 | 0 |

«Diap. corrección» = filas de `perfil_correccion`: todos los PPTX de la pieza, con todas las versiones de cada plan (hay muchas repetidas). «% plantilla» =
diapositivas con número `n.m` reconocible.

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
| Esqueleto de carpetas | 8 carpetas del 3212 (`1-2D y 3D Pieza` … `8- STL peça real`) frente a 7 en las entregas de 2026-10 (`1- 2D y 3D pieza` … `7- Pieza real STL`); nivel extra `Tipo A/B` en Clips; carpetas de feature con solo un `Readme.txt` que remite a otra (3167, 3214, 3205, 3206) |
| Medición CMM | CSV por bloques (solo Bolt Eye: 3212, 3197 bilingüe); **export `#P#`** en `.txt` (Paredes, Pockets, Planitudes; 564 ficheros); PPAP del cliente `.xlsm` por cavidad (3167); KEYENCE/vídeo/galgas sin CMM (3288, 3214, 3309) |
| Cabecera PPAP | inglés (`Part Name`, `Drawing nº`) o **castellano** (`Nombre pieza`, `Nº Plano`, `CP`/`SPC`); campos corridos o `#REF!`; fechas `1899-12-31`, `xx`, texto |
| Columnas del DR | Nominal/Tol en D–F (3212, 3288) o con **`class`** en E y Tol en F–G (3197, shroud); cavidades `Cav.13`, `CAV.1`, `C1` o **solo número** (`1`…`20`); de 4 a 32 cavidades; NOK y comentarios donde acaben las cavidades |
| Hojas | `DR(3D)`, `DR`, `DR(100%)`, `DR_100%`, `DR_8cav.`, `DR_CMM`, `DR(tapa)`/`DR(base)`, `DR_PAR`, `DR cicle`, `DR-55º`… |
| Previsión de la corrección | libro aparte `DR(100%)` con `Retoc` en O (3212); en T con previsión U–AB (3197); **dentro del informe** (`Dim`/`Corr.`, shroud); **en la tabla del PPTX** (3051); ninguna (3288) |
| Título del plan | `Tool correction 1.33 (DIM. Nr.170)`; `Correcció nr. 1.1 (DIM. Nr. 54, 57 and 60)`; `Tool correction DIM#5: …` (3309); `1 / . Dim 210Ø21,5-0,2` (3051, cota pegada al nominal); solo imágenes (3056); presentaciones de análisis sin numerar (3168, 3226) |
| Planes por pieza | 1–2 (3212, 3214) hasta **15 loops** (3218), cada uno en `YYYYMMDD_Nth loop…` con varias versiones; numeración que se reinicia (shroud tras postizos) o no coincide con el nombre del fichero |
| Método de medida | DOCX del cliente (Bolt Eye); **XLS `MM_revNN.xls` con hoja `DIMENSIONS`** (Clips, 3309); fichas PDF de INTEPLAST (3288); ensayos del cliente (TES) |
| Plano | escaneo sin texto (3212); vectorial con texto pero **sin globos** (3197, 3051); **con globos + `.icp`/`.prf`** que dan su posición (3205, 3206, 3288, 3202; 19 planos) |
| Condición de medida | pieza montada (*clipped*, Clips) o libre; condiciones de proceso en la ruta (3197: `135ºC/500bar`, boquilla); fuerza de cierre (3168) |
| Moldflow | `.mfr` (10 piezas); `README.txt` *«No Moldflow information available»*; un vídeo `.avi` de llenado (3206) |

## Implicaciones para la app (comprobado en el código el 2026-10-21)

1. **Raíz y alta de piezas.** La raíz está en `Exemples/0- Bolt Eye`; para los demás features hay que subirla a
   `Exemples` y migrar rutas relativas. La carpeta del feature ya dice qué piezas lo tienen
   (`FeaturePartLink`), pero una pieza puede estar en varios features: la identidad tiene que ser el código, y
   las carpetas con solo `Readme.txt` deben resolverse a la carpeta real.
2. **`report_rows`** (`backend/app/ingestion/measurement_tables.py`) **descarta toda hoja con «100%» en el
   nombre**. En el 3212 era deliberado (previsiones), pero en Clips y en los shroud `DR_100%` es el informe
   principal. Tampoco reconoce cavidades rotuladas solo con número (`1…20`, `DR(base)` del 3288).
3. **Formato `#P#`** (564 ficheros) y **PPAP del cliente `.xlsm`**: la app no los lee. El `#P#` lo genera
   INTEPLAST para importarlo en eISIR (SupplyOn/Bosch) y su id `1-<cota>[.sub|.Cmk|.Cpk|.T]` enlaza con la
   cota del PPAP interno (87 % de coincidencia de nominal en el 3237). Si algún día se leen, **los SPC no**
   (punto 8).
4. **Bloques heredados**: comparar cada bloque con informes anteriores de la misma pieza y marcarlo
   (`sospecha_de_copia`) en lugar de tratarlo como medición nueva.
5. **Correcciones**: la plantilla común permite un lector para casi todas las piezas si admite las variantes de
   título y bloque, varias cotas por título, cotas con subpuntos (`1320.2`), versiones por loop (elegir la
   vigente) y localiza la previsión por cabecera (`Retoc`, `Corr.`, `Correction`), no por columna fija.
6. **Planos con globos**: los `.icp`/`.prf` de infra-CONVERT dan número y posición de cada globo,
   **validado** en el 3288 (99 % a menos de 10 pt; `globos_icp.py`). La transformación a la página hay que
   ajustarla por plano (centro de la hoja, Y hacia arriba).
7. **Lecciones que ya están en los datos**: Bolt Eye pequeño en primera prueba (3212, 3197), nervios postizos
   tras rebabas repetidas (shroud), concesión del cliente (3167), análisis de NOK de montaje (3168), causas de
   molde según el matricero (3206). Ver `hallazgos.jsonl` (tipo `leccion`).
8. 🔴 **Valores que no son medidas** (I-003): 648.806 celdas con `RAND()`/`RANDBETWEEN` en 191 libros de 9
   piezas (generadores de Cpk, muestras 2–5 calculadas en PPAP de cliente, auxiliares de R&R) y los SPC `#P#`
   que salen de ellos. Un lector de producción tiene que leer la fórmula, no solo el valor, y descartar o
   marcar esas celdas; la tabla `celda_aleatoria` dice cuáles son. Lo mismo con las versiones «aplicadas» de
   un informe (I-603): preferir la versión entregada (`Uploaded to IQS`).
