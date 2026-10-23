# 0- Bolt Eye

> Carpeta `Exemples/0- Bolt Eye` (hasta el 2026-10-20 eran las cuatro carpetas de `Exemples`).
> 580 ficheros, 2,4 GB. Biblioteca completa el 2026-10-21; 220 ficheros estaban solo en la nube
> y se descargaron al leerlos.

| Pieza | Ficheros | Estado de los datos | Ficha |
|---|--:|---|---|
| **3212 Pump Housing** | 253 | Piloto de la app. Analizado a fondo (agosto–septiembre 2026) | [3212/README.md](3212/README.md) |
| 3197 Pot | 203 | Completo: CSV CMM, 11 informes PPAP, 3 PPTX + 4 XLS de corrección con previsiones | [3197.md](3197.md) |
| 3051 Pump Housing | 122 | Completo, otro formato de corrección (tabla en el PPTX, sin XLS de previsiones) | [3051.md](3051.md) |
| 2820 Pump Housing | 2 | Solo plano y STEP | [2820.md](2820.md) |

Contexto anterior (inventario del 2026-08-07): [otros-proyectos.md](otros-proyectos.md).

## El feature en cada pieza

| | 3212 Pump Housing | 3197 Pot | 3051 Pump Housing |
|---|---|---|---|
| Diámetro | `N170` Ø4 **−0,1** (GX y LP a H=1,5 y 5) | `N230` Ø4 **+0,1/0** (GX, «Hole 1…») | no localizado todavía |
| Posición | `N117` ⌖0,15 | `N220` ⌖0,25 con MMC | — |
| Primera medición | 3,43 mm (−0,57) | 3,77–3,79 mm (−0,22) | — |
| Acción | 1.33: *«Podem utilitzar els expulsors de 4 com en els altres motlles»* | 1.14: *«Incrementar zona marcada en vermell Ø0,28mm. Atenció en diàmetre. S'ha d'aprofitar per a corregir la posició»* | — |
| Previsión XLS | +0,5 → 3,929 / 3,977 | +0,28 → 4,050–4,064 | — |
| Después | GX 3,97–3,98 dentro, LP máx. fuera | 4,068–4,073 dentro (`intern.03`) | — |

🔑 **Lección del feature con dos casos**: en las dos piezas el agujero Ø4 del bolt eye salió
**pequeño en la primera prueba** y se corrigió agrandándolo en el molde. En el 3197 la previsión
falló por unos +0,01 mm; en el 3212 la evaluación LP siguió fuera. Fuentes:
`3197 Pot/4- Metrologia/Support_intern.02/…/3197 C*.csv` (línea 18-19),
`Support_intern.03/c*-3197.csv`, `5- Retoques de molde/3197-00_intern.02_MOLD_CORRECTION.xls!DR_8cav.` fila 48,
`20231031-Mold correction_1_P3197.pptx` diapositiva 14.

⚠️ **Los N-numbers solo valen dentro de su plano**: `N1120` es *Profilform 0,2 at Hole 1* en el
3197 y *ø19,6 ± 0,1* en el 3051 (`3051_Cloud_of_Points.xlsm!D19_6_N1120`). Nunca unir cotas de
piezas distintas por compartir número.

## Formatos en las cuatro piezas

| | 3212 | 3197 | 3051 | 2820 |
|---|---|---|---|---|
| Cavidades | c13–c16 (molde de 16) | C1–C8 | Cav_1–Cav_4 | — |
| CSV CMM por bloques | ✅ 16 | ✅ 113, **bilingües ES/DE**, con condiciones de proceso en la ruta (`135ºC/500bar`) | ❌ | — |
| CSV «totes» | ✅ | ✅ con variantes (`c5.1`, `c5bis`, `c1-24`) | ❌ | — |
| Nubes de puntos TXT | ✅ 40 | ✅ 46 | ✅ 64 + libro `3051_Cloud_of_Points.xlsm` | — |
| Informes PPAP XLS | `DR(3D)`, `DR`, `DR(100%)` | `DR_8cav.`, `DR`, `DR_PAR`, `DR cicle`, `DR-55º/65º/90º`, `DR roughness` | `DR(100%)`, `DR(4CAV_CMM)`, `DR` | — |
| Columna `class` en el DR | no | **sí** (desplaza Tol a F–G) | no | — |
| PPTX de corrección | plantilla `Tool correction n.m (DIM. Nr.x)` | **la misma plantilla** | **otra**: `Correction plan Nn`, tabla *Current / Correction / Wished* por cavidad | — |
| Previsión | XLS `DR(100%)`, `Retoc` en O, P:S | XLS `DR_8cav.`/`DR`, `Retoc` en T, U:AB, MAX/MIN en AD:AE | dentro del PPTX | — |
| Método de medida | DOCX (Bosch, firmado por X. Arcos) | DOCX `3 130 516 01B_01_measurement_description_pot.docx` | DOCX `0140Y0038S_01_measuring description.docx` | — |
| Moldflow | `.mfr` | `.mfr` | `.mfr` | — |
| STL de pieza real | ✅ | ❌ | ✅ | — |
