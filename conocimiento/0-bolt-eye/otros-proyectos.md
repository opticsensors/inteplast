# Los otros tres proyectos — documentados, sin tocar

> **Nota (2026-10-21):** documento del inventario de agosto de 2026, cuando solo se trabajaba el 3212.
> Las fichas actuales de cada pieza estan en [README.md](README.md), [3197.md](3197.md), [3051.md](3051.md)
> y [2820.md](2820.md); las rutas ahora cuelgan de `Exemples/0- Bolt Eye/`.

> **Alcance de la aplicación:** `3212 Pump Housing` sigue siendo el piloto
> (→ [3212/README.md](3212/README.md)). La biblioteca de conocimiento ya incluye los otros
> proyectos y familias; documentarlos no amplía automáticamente el piloto de la aplicación.
>
> Inspección: 2026-08-07. No re-verificados el 2026-08-11.

> **Rectificaciones contrastadas el 23/10/2026:** la biblioteca se ha ampliado, manteniendo
> el 3212 como piloto de la aplicación. En 3197, `intern.08.xls!DR-55º/65º/90º!I12` identifica
> **temperaturas de boquilla en ºC**, no diámetros. Las 118 CSV se reparten en 59 informes
> individuales, 9 comparativas y 50 exports de puntos. Un estudio MSA evalúa el sistema de
> medida; no equivale por sí solo a una incertidumbre completa. Véanse las fichas actuales.

---

## El conjunto completo

```
Exemples/0- Bolt Eye/           580 ficheros · 2,20 GB lógicos   (hasta 2026-10-20: Exemples/)
├── 2820 Pump Housing/            2 ficheros    5,8 MB
├── 3051 Pump Housing/          122 ficheros  591,7 MB
├── 3197 Pot/                   203 ficheros  817,4 MB
└── 3212 Pump Housing/          253 ficheros  834,0 MB   ← PILOTO DE LA APLICACIÓN
```

**Hay 3 Pump Housing** (2820, 3051, 3212) y **1 Pot** (3197). Los tres Pump Housing son de la
misma familia; su comparación está documentada en las fichas actuales.

## Por qué el 3212 es el piloto

| Motivo | Detalle |
|---|---|
| **Tiene el histórico más documentado** | Metrología (9 muestreos) + retoques de molde (2 correcciones documentadas) + escaneado STL. Permite estudiar *problema → acción → resultado*; faltan confirmar posibles retoques posteriores y la aceptación de cotas NOK. |
| **Es sobre el que se trabajó el feature *Bolt Eye*** | Todas las preguntas y respuestas de `inteplast_resposta_dubtes.md` se refieren a él. |
| **Es el que INTEPLAST usó para explicarnos el dominio** | El conocimiento que tenemos está anclado a esta pieza. |
| **Alcance** | Validar la aplicación con el 3212; las otras piezas aportan conocimiento para su futura generalización. |

---

## `2820 Pump Housing` — 2 ficheros, 5,8 MB

```
1-2D y 3D Pieza/
├── 20160817_DRW_3130516933_0140S00050-DRW-000-02-1-EN_DE.pdf
└── 3130516933-Pumphousing-with-chamfer.stp
```

**Es una carcasa vacía**: solo plano 2D y sólido. Sin metrología, sin retoques, sin Moldflow.

> **No se usa porque no tiene conocimiento que extraer.** Su valor es otro: es el caso de
> prueba de **"pieza sin histórico"** — sirve para validar el flujo de alta de un proyecto
> nuevo en el frontend, cuando llegue ese momento.

⚠️ Está pendiente confirmar con INTEPLAST si el resto del proyecto existe y no se compartió, o
si realmente no hay más (pregunta abierta A7 en [preguntas-abiertas.md](../../docs/preguntas-abiertas.md)).

---

## `3051 Pump Housing` — 122 ficheros, 591,7 MB

Proyecto **completo**, con la numeración de carpetas 1–8; en el 3212 falta físicamente la carpeta 2.

| Carpeta | Contenido destacado |
|---|---|
| `1-2D y 3D Pieza` | `20211205_0140S00275-DRW_pendent acceptació.pdf` ← *"pendiente aceptación"*, etiqueta del fichero, sin acreditar aprobación vigente · `20190718_3130516996-Pumphousing_VDA12mm.stp` |
| `2- Moldflow` | **existe pero VACÍA** |
| `3- 3D Molde` | `3051-cela_forma.stp` (78 MB) — contiene 460 entidades `PRODUCT`; el nombre por sí solo no demuestra que sea solo un postizo ni que represente todo el molde. |
| `4- Metrologia` | Muestreos hasta **`intern.11`**. Carpetas `Suport_Int_01`, `Support_Inf_04`… Cavidades `Cav_1`–`Cav_4`. Incluye `3051_Cloud_of_Points.xlsm` (libro **con macros** que post-procesa las nubes de puntos). |
| `5- Retoques de molde` | Nomenclatura alternativa: `3051_Correction_plan_N<N>_rev<N>.pptx`. Subcarpetas `2nCorrection_plan/`, `3rCorretion_plan/`, `4tCorretion_plan/`, `Old/` → **al menos 4 iteraciones de corrección** (el 3212 solo tiene 2). |
| `6- Métode de mesura` | `0140Y0038S_01_measuring description.docx` |
| `7- Moldflow` | `3051_pump housing RB_VDA 12 mm.mfr` (168 MB) |
| `8- STL peça real` | `09-12-2024_C1-3051.stl` (311 MB) — convención de nombre **distinta**: `fecha_cavidad-proyecto` |

> **Es el segundo candidato natural.** Tiene más iteraciones de corrección que el 3212 y es un
> Pump Housing, así que es directamente comparable. Cuando el esquema esté validado sobre el
> 3212, este es el siguiente.

---

## `3197 Pot` — 203 ficheros, 817,4 MB

Proyecto completo, **de otra familia de pieza** (*Pot*, no *Pump Housing*).

| Carpeta | Contenido destacado |
|---|---|
| `1-2D y 3D Pieza` | `20240222_0140S00363 D 02.pdf` · `20230404_0140S00363_SPT_001.stp` |
| `2- Moldflow` | **existe pero VACÍA** |
| `3- 3D Molde` | `M1176_P-3197 6_05_2025.step` (**645 MB**, el fichero más pesado del conjunto). `M1176` = nº de molde — es el único proyecto que lo lleva en el nombre. |
| `4- Metrologia` | Muestreos hasta `intern.11`. Cavidades **C1–C8**. Informes **bilingües ES/DE** (`Diámetro;Durchmesser`). Incluye `3197_MSA.xls` + `.pdf` (**Measurement System Analysis**, estudio R&R del sistema de medida; no equivale por sí solo a su incertidumbre completa). También `3197_Punts_nervis_Frontal*.csv` (puntos de los **nervios**). |
| `5- Retoques de molde` | `Burrs_3197_20240318.pdf` (informe de rebabas), `GPF_*.pdf` (documentos rotulados GPF) |
| `6- Métode de mesura` | `3 130 516 01B_01_measurement_description_pot.docx` |
| `7- Moldflow` | `3197 - RB - Pot.mfr` (150 MB) |
| `8- STL peça real` | **no existe** |

### Dos cosas que lo hacen especial

**1. El mismo feature con otras reglas.** El Pot tiene bolt eyes, pero con tolerancias
distintas:

```
N230   ø4 (GX) Hole 1                      → Ø4 +0,1/0   (¡INVERSA a la del 3212!)
N220   Position ø0,25 A/C/B ø4 Hole 1      → posición 0,25 con MMC (Ø0,328 efectivo)
N1120  Profilform 0,2 at Hole 1 to A/C/B   → tolerancia de perfil
```

| | 3212 Pump Housing | 3197 Pot |
|---|---|---|
| Diámetro | Ø4 **−0,1** | Ø4 **+0,1** |
| Posición | ⌖0,15 | ⌖0,25 **con MMC** |
| Referencias | A-B | A/C/B |

> Es el argumento empírico para separar **`FEATURE`** de **`INSTANCIA_EN_PROYECTO`** en el
> modelo de datos → [modelo-datos.md](../../docs/modelo-datos.md).

**2. Es el único con un DOE de proceso.** Tiene carpetas de condiciones:

```
Support_intern.02/135ºC|140ºC|145ºC / 500bar|600bar/
Support_intern.08/3197_totes_nozzle 55|65|90          ← temperatura de boquilla (ºC)
```

Relaciona **parámetros de proceso con desviación dimensional** — dato muy valioso. Pero
INTEPLAST dijo en el **Dubte 8** que **no quiere parámetros de máquina en la BD**, porque el
proyecto es de fase de diseño y *"son demasiadas variables que no están relacionadas con el
feature en sí"*.

> **Módulo futuro, no ahora.** El dato existe y está bien organizado; la decisión de dejarlo
> fuera es del cliente, no una limitación técnica.

---

## Ejes de variación del conjunto

Lo que multiplica los ficheros:

```
PROYECTO (4) × MUESTREO intern.NN (1..11) × CAVIDAD (c13..c16 / C1..C8 / Cav_1..4)
                                          × [solo 3197] CONDICIÓN DE PROCESO
```

## Inventario global por tipo de fichero (los 4 proyectos)

| Ext. | Nº | Dónde | ¿Legible? |
|---|--:|---|---|
| `.pdf` | 162 | Planos 2D, gráficas PA/PB, planes de corrección, MSA | ⚠️ PA/PB con texto; planos vectoriales y escaneados según pieza |
| `.txt` | 158 | Nubes de puntos XYZ | ✅ Trivial |
| `.csv` | 137 | 75 informes individuales CMM + 12 comparativas + 50 exports de puntos | ✅ `;` + cp1252, por bloques |
| `.xls` | 44 | Informes PPAP + correcciones + MSA | ✅ BIFF8 → Excel COM |
| `.dxf` | 15 | Perfiles medidos | Mismos vértices que TXT hasta redondeo de 0,00005 mm |
| `.pptx` | 14 | Planes de corrección de molde | ✅ Es un ZIP |
| `.igs` | 12 | Exportación de contornos | XY de PUNTS con Z constante; no son duplicados 3D |
| `.rar` | 7 | Comprimidos; redundancia no contrastada íntegramente | ⚠️ Necesita unrar |
| `.stp`/`.step` | 7 | Sólidos de pieza y de molde | ✅ pero pesado |
| `.zip` | 6 | Comprimidos; redundancia no contrastada íntegramente | ✅ |
| `.dwg` | 6 | Perfiles de sección | ❌ Propietario (convertir a DXF) |
| `.xlsm` | 3 | Post-proceso de nubes (con macros) | ✅ |
| `.mfr` | 3 | Moldflow | ❌ Binario propietario |
| `.docx` | 3 | Instrucciones de medición | ⚠️ Texto e imágenes: requieren lectura de ambos |
| `.stl` | 2 | Escaneado 3D de pieza real | ✅ |
| `.xlsx` | 1 | Resumen ad-hoc | ✅ |

🔁 **Los 15 `.dxf` y los 12 `.igs` del inventario global son exactamente los de
`3212/4- Metrologia`** — las cifras coinciden, no hay ninguno en los otros tres proyectos. Y
La conclusión de agosto de que ambos formatos eran duplicados 3D queda **rectificada el
23/10/2026**: los 15 DXF comparten vértices y orden con el TXT hasta redondeo de 0,00005 mm;
los 12 IGES conservan XY hasta 0,0001 mm, pero **aplanan Z a una constante**, sin matrices
de transformación. Conservar los IGES como soporte distinto, no como nubes 3D equivalentes.
→ [formatos-parsing.md §4bis](../formatos-parsing.md#4bis-relación-de-los-igs-y-dxf-con-los-txt)

## Nomenclatura común a los cuatro

| Elemento | Ejemplo | Significado |
|---|---|---|
| Nº proyecto INTEPLAST | `3212` | Referencia interna, 4 dígitos. Prefijo de casi todos los ficheros. |
| ITP Ref. | `732120000` | Referencia de artículo (`7` + nº proyecto + versión) |
| Part nº (cliente) | `3130517012` / `3 130 516 987` | Referencia Bosch. Aparece **con y sin espacios**. |
| Nº Plano | `0140S00237` | Número de plano del cliente |
| Part / Drawing Level | `3E1005491360`, `06/…` | Nivel de revisión de pieza y de plano |
| Nº de molde | `M1176` | Solo en el nombre del STEP del molde del 3197 |

> Cliente en los cuatro: **Robert Bosch**, división BueP. Informes en formato **PPAP /
> QS9000-TS**, plantilla corporativa de INTEPLAST de 1999.
