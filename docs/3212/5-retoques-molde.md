# `5- Retoques de molde` — 🔑 lessons learned

**8 ficheros · 60,9 MB · todos LOCAL (seguros)**

Aquí está **la respuesta al Dubte 5** (*"¿dónde encontramos qué acción se hizo en el molde?"*).
Son las decisiones de retoque tomadas en reunión, una diapositiva por cota.

> Este documento describe **el contenido de la carpeta**. El análisis de si las correcciones
> funcionaron está en [historial-molde.md](historial-molde.md).

---

## 1. Inventario completo

```
5- Retoques de molde/
├── 20240124-Mold correction_1_P3212_rev0.pptx      18,62 MB   ← versión vieja
├── 20240124-Mold correction_1_P3212_rev1.pptx      18,54 MB   ← 🔑 CORRECCIÓN 1 (la buena)
├── 20240124-Mold correction_1_P3212_rev1.pdf        6,45 MB   ← misma, en PDF
├── 3212-00_intern.01_mold_correction.xls            0,70 MB   ← ⚠️ clon de intern.01.xls
└── 2N/                                                        ← "2ª corrección"
    ├── 20240318-Mold correction_2_P3212_rev1.pptx   7,65 MB   ← 🔑 CORRECCIÓN 2
    ├── 20240318-Mold correction_2_P3212_rev1_.pptx  7,65 MB   ← duplicado exacto
    ├── 3212-00_intern.03_correction_2_.xls          0,67 MB
    └── Old/
        └── 3212-00_intern.03_correction_2.xls       0,66 MB   ← versión superada
```

**Solo hay 2 correcciones** (enero y marzo de 2024), pese a que los muestreos llegan hasta
abril de 2025 → pregunta abierta A1 en [preguntas-abiertas.md](../preguntas-abiertas.md).

### Qué fichero usar

| Quiero… | Uso |
|---|---|
| El contenido de la corrección 1 | `20240124-…_rev1.pptx` |
| El contenido de la corrección 2 | `2N/20240318-…_rev1.pptx` (el `rev1_` es idéntico) |
| Leerlo a ojo rápido | El `.pdf` de la corrección 1 |
| Datos de los `.xls` | **Nada** — ver abajo |

### ⚠️ Los `.xls` de esta carpeta no aportan contenido

Comprobado celda a celda el 2026-08-11:

- **`3212-00_intern.01_mold_correction.xls` es un clon exacto** de
  `4- Metrologia/3212-00_intern.01.xls`: mismo texto en `DR(3D)`, **mismos colores de relleno y
  de fuente, mismas 21 formas, 0 comentarios**. No hay ni una anotación.
- **`2N/3212-00_intern.03_correction_2_.xls`** sí tiene columnas extra (15–26), pero contienen
  una **re-ordenación de los mismos datos de N242** separados por el comentario A/B. No son
  anotaciones nuevas.

> 🔑 **Su único valor es el nombre del fichero**: dice de qué muestreo salió cada corrección.
> Es lo que permitió reconstruir la cadena muestreo ↔ corrección.
> **Todo el contenido real de la corrección está en los PPTX.**

---

## 2. Cómo leer un PPTX de corrección

Un `.pptx` es un **ZIP**: `ppt/slides/slide*.xml` (texto) + `ppt/media/` (imágenes).

```bash
D=$(mktemp -d)
unzip -o -q -j "…/20240124-Mold correction_1_P3212_rev1.pptx" "ppt/slides/slide*.xml" -d "$D"
for f in $(ls "$D"/slide*.xml | sort -V); do
  echo "--- $(basename "$f")"
  sed 's/<[^>]*>/\n/g' "$f" | grep -v '^[[:space:]]*$'
done
rm -rf "$D"
```

⚠️ **No extraer `ppt/media/` salvo que se necesite**: son 8–19 MB de imágenes y tarda minutos.

### Estructura de una diapositiva — muy regular

```
Título:    Tool correction nº1 – P3212            24/01/2024        33/37
Constante: Longitud 70mm                                  ← pie fijo, ignorar
Subtítulo: Tool correction 1.33 (DIM. Nr.170)   Ø4-0,1
Bloque 1:  Current situation:      [imagen: recorte del informe / CAD con la cota]
Bloque 2:  Tool correction plan:   [imagen: zona marcada en ROJO]
Texto:     <acción correctiva, en CATALÁN, con la magnitud en mm>
Marcador:  OK                                             ← estado (solo en algunas)
```

### ⚠️ Trampas al parsear

1. **El texto viene fragmentado en *runs* XML.** `sed 's/<[^>]*>/\n/g'` parte palabras:
   `Fer ~ creixre ~ el ~ plastic`. Hay que reunir los runs (trabajar con `<a:p>` como unidad)
   antes de aplicar regex.
2. **La numeración del pie miente**: la corrección 1 declara `n/37` pero **solo hay 36
   diapositivas** — falta la `5/37`.
3. **Ortografía irregular** en catalán: `creixre` / `creixe` / `créixer`, `rondundesa` /
   `rodunesa`, `Corretgir` / `Corregir`. No hacer match exacto sobre los verbos.
4. **Diapositivas sin cota en el texto**: aparecen literalmente como `DIM. Nr.XX` / `xx`
   (7 en total). ⚠️ **No son inparseables: el N-number está en la imagen** → ver §3bis.
5. **La numeración de fichero no coincide con la de diapositiva en la corrección 1.** Como
   falta la `5/37`, a partir de ahí hay un desfase de 1: `slide15.xml` = **1.16**. En la
   corrección 2 no hay desfase (`slide3.xml` = 2.3). **Leer el número del pie, no del nombre
   del fichero.**

Campos a extraer y sus regex → [formatos-parsing.md](../formatos-parsing.md#3-pptx-de-corrección-de-molde).

---

## 3bis. 🔑 Las 7 diapositivas "sin cota" son el retoque del PLANO A

*(Resuelto el 2026-08-11 — era la pregunta abierta A2, ahora R9.)*

Las diapositivas huérfanas **no dicen** su N-number en el texto, pero **sí lo enseñan en la
imagen**: el bloque *Current situation* es un recorte del `DR(3D)` cuya **primera columna es la
columna `Nr`**. Basta con extraer las imágenes de esa diapositiva y mirarlas.

| Slide | Fichero | `Retoc` | N-numbers |
|---|---|:--:|---|
| 1.16 | `slide15.xml` | +0,29 | `N155` `N258` `N267` `N268` |
| 1.17 | `slide16.xml` | +0,29 | `N154` `N165` `N166` `N167` |
| 1.18 | `slide17.xml` | +0,29 | `N236` `N237` `N240` `N241` `N252` `N256` |
| 2.3 | `slide3.xml` | +0,02 | `N154` `N155` `N258` `N267` `N268` |
| 2.4 | `slide4.xml` | +0,02 | `N165` `N166` `N167` |
| 2.5 | `slide5.xml` | +0,02 | `N236` `N237` `N240` `N241` `N252` `N256` |
| 2.13 | `slide13.xml` | −0,08 | **`N240`** |

### Por qué no llevan `DIM. Nr.`

Porque **el retoque no es de una cota, es de la referencia**. Las 6 diapositivas comparten la
misma imagen de zona roja — `image54.png` en la corrección 1 e `image12.png` en la 2, el mismo
fichero byte a byte (101.725 B) — y lo que está pintado de rojo es **la brida perimetral
entera: el plano A**.

Eso es exactamente el `0,29 mm` que citan de pasada las otras diapositivas:

- **1.27 (N236)**: *"màxim 0,29 mm… si ens quedem curts s'ha de tornar a tocar el Pla A"*
- **1.28 (N243)**: *"si toquem **0,29 mm** en el pla A, tocar aquí 0,27"*

> 🔑 **Modelo de datos:** estas diapositivas no son una `ACCION` sobre un N-number, sino una
> **acción sobre una referencia (datum) con N cotas afectadas**. El `DR(3D)` recortado que
> acompaña lleva una columna `Retoc` con el valor propuesto y **el resultado simulado por
> cavidad** — es decir, INTEPLAST ya calcula *a priori* el efecto del retoque. Esa columna es
> ingerible como `ACCION.efecto_previsto`.

**2.13 es un caso distinto**: sí tiene cota, `N240`. Solo faltaba el número tras `DIM. Nr.`.
El recorte del plano lleva el globo `[]240` rodeado en rojo con una flecha señalando la cara.

### Receta para recuperar el N-number de una diapositiva

```bash
P="…/20240124-Mold correction_1_P3212_rev1.pptx"; D=$(mktemp -d)
# 1) qué imágenes usa la diapositiva
unzip -o -q "$P" "ppt/slides/_rels/slide15.xml.rels" -d "$D"
grep -o 'media/image[0-9]*\.png' "$D/ppt/slides/_rels/slide15.xml.rels"
# 2) extraer solo esas (las <30 KB son los recortes del informe; las grandes, plano y 3D)
unzip -o -q -j "$P" "ppt/media/image5[0-7].png" -d "$D/img"
```
Luego **mirar las imágenes pequeñas**: el N-number está en la columna de la izquierda.
Validación: el nº de `r:embed` distintos en `slideN.xml` debe coincidir con el nº de
relaciones de imagen — si coincide, ninguna imagen del `rels` está huérfana.

---

## 3. Contenido de la corrección nº1 — 24/01/2024

**36 diapositivas presentes** (declara 37, falta la 5/37). Sale del muestreo `intern.01`.

| Slide | DIM Nr. | Cota | Acción |
|---|---|---|---|
| 1.1 | N214 | Ø16−0,2 | Fer créixer el plàstic **Ø0,23 mm** |
| 1.2 | N283 | 16,3−0,3 | Fer créixer el plàstic **Ø0,24 mm** |
| 1.3 | N138 | Ø21,3±0,2 | Fer créixer el plàstic **Ø0,27 mm** |
| 1.4 | N134 | 21,5−0,2 | Fer créixer el plàstic **Ø0,16 mm** |
| 1.6 | N137 / N142 / N211 | 11,5±0,2 / 17±0,15 / 60±0,20 | Incrementar plàstic **0,1 mm**; *cuidado, la dim. 136 (3 mm) està bé, només desplaçar-la* |
| 1.7 | N137 | 11,5±0,2 | Incrementar plàstic **0,12 mm** *(retoc marró)* |
| 1.8 | N150 | 1,8±0,15 | Incrementar plàstic **0,13 mm** |
| 1.9 | N171 | Ø16−0,2 | Fer créixer plàstic **Ø0,32 mm**; *hem deixat menys acer, aquí hem de tocar molt més* |
| 1.10 | N127 | 16,3−0,3 | Fer créixer plàstic **Ø0,26 mm** |
| 1.11 | N141 | Ø21,3±0,2 | **Ø0,27 mm** |
| 1.12 | N128 | Ø21,5−0,2 | **Ø0,21 mm** |
| 1.13 | N145 / N175 | 17±0,15 / 1,8±0,15 | Fer créixer plàstic **0,15 mm** |
| 1.14 | N159 | Ø12,4−0,2 | **Reduir el ferro Ø −0,2** fent créixer el plàstic |
| 1.15 | N158 / N168 | 27,9±0,1 / 21,6±0,2 | Incrementar **0,1 mm** — ⛔ *No tocar res ara* |
| **1.16** | N155 · N258 · N267 · N268 | 49,5±0,2 /4 · 8,6±0,1 · 4,6+0,1 · 5,35+0,1 | 🔑 **PLANO A**: incrementar plàstic **0,29 mm** |
| **1.17** | N154 · N165 · N166 · N167 | 5,85−0,1 · 1,35−0,05 /4 · 1,9±0,1 · 3,43±0,05 | 🔑 **PLANO A**: **0,29 mm** |
| **1.18** | N236 · N237 · N240 · N241 · N252 · N256 | 12+0,05 /5 · 13,4+0,05 /5 · 18,5+0,2 /5 · 20,7+0,25 · 14,6+0,1 · 15,7+0,1 | 🔑 **PLANO A**: **0,29 mm** |
| 1.19 | N154 | 5,85−0,1 | ⛔ *Aquí no fer res* |
| 1.20 | N167 | 3,43±0,05 | Incrementar **0,27 mm** |
| 1.21 | N166 | 1,9±0,1 | **0,38 mm** — ⛔ *no fer res encara* |
| 1.22 | N233 | Ø7,5±0,05 | Incrementar **0,09 mm**; *el salt està molt bé, mantenir-lo* |
| 1.23 | N265 | 59,7−0,1 | Incrementar **0,11 mm** |
| 1.24 | N266 | 67,1−0,1 | Incrementar **0,32 mm** |
| 1.25 | N267 | 4,6+0,1 | Incrementar **0,09 mm** |
| 1.26 | N268 | 5,35+0,1 | ⛔ *No fer res. Mesura sense tenir en compte marcatge.* |
| 1.27 | N236 | 12+0,05 | Mantenir; **màxim 0,29 mm**. *Si ens quedem curts s'ha de tornar a tocar el Pla A i afecta a moltes coses* |
| 1.28 | N243 | — | 🔗 *Si toquem **0,29 mm** en el pla A, tocar aquí **0,27*** |
| 1.29 | N165 | 1,35−0,05 | Corregir **segons núvol de punts**; màx **0,38 mm** després de tocar el pla A |
| 1.30 | N162 | 49,89−0,12 | Millorar rodonesa, retoc màx **Ø0,43 mm** |
| 1.31 | N161 | 45,4+0,12 | Retoc màx **Ø−0,40 mm** |
| 1.32 | N163 | 52,79+0,12 | Màx **Ø0,44 mm** |
| **1.33** | **N170** | **Ø4−0,1** | 🔑 ***Podem utilitzar els expulsors de 4 com en els altres motlles*** ← **BOLT EYE** |
| 1.34 | N113 | 3+0,1 | Retoc segons taula; *l'ull de la posición 3 es corretgeix menys* |
| 1.35 | N117 / N118 | — | *Els ulls han quedat molt bé, només mouria el B3.* Tocar la posició de les **llenties 2, 3, 4 de totes les cavitats** |
| 1.36 | N242 | 0,05 | Corregir segons núvol de punts |
| 1.37 | N288 | 15N–50N | *El pin fa **3,93**…* ⛔ *No tocar res* |

---

## 4. Contenido de la corrección nº2 — 18/03/2024

**18 diapositivas.** Sale del muestreo `intern.03`. **Es un subconjunto de la primera**: solo
las cotas que seguían mal.

| Slide | DIM Nr. | Cota | Acción | Estado |
|---|---|---|---|:--:|
| 2.1 | N128 | Ø21,5−0,2 | **Ø0,05 mm** — *De momento no tocar. Marc ha de fer comparativa amb **3181 i 3157*** | |
| 2.2 | N158 / N168 | 27,9±0,1 / 21,6±0,2 | Incrementar plàstic **0,06 mm** | OK |
| **2.3** | N154 · N155 · N258 · N267 · N268 | — | 🔑 **PLANO A**: incrementar plàstic **0,02 mm** | OK |
| **2.4** | N165 · N166 · N167 | — | 🔑 **PLANO A**: **0,02 mm** | OK |
| **2.5** | N236 · N237 · N240 · N241 · N252 · N256 | — | 🔑 **PLANO A**: **0,02 mm** | OK |
| 2.6 | N166 | 1,9±0,1 | Incrementar plàstic **0,38 mm** | OK |
| 2.7 | N265 | 59,7−0,1 | **0,11 mm** — *"a l'últim ho demanàvem i crec que no s'ha aplicat… troben el mateix resultat"* | OK |
| 2.8 | N266 | 67,1−0,1 | **Incrementar acer o reduir plàstic 0,14 mm** — *"Que ha passat? Ens em colat molt no?"* | OK |
| 2.9 | N267 | 4,6+0,1 | Tocar **l'ull 2 de totes les cavitats 0,03 mm**; l'ull 4 només a **cav. 13, 14 i 15** | |
| 2.10 | N268 | 5,35+0,1 | Incrementar **0,09 mm** | OK |
| 2.11 | N165 | 1,35−0,05 | Màx **0,22 mm** després de tocar el pla A | OK |
| 2.12 | N241 | 20,7+0,25 | **Erosionar 0,08 mm** en la direcció de la fletxa | OK |
| **2.13** | **N240** | 18,5+0,2 /5 | Pujar **0,08 mm** després de tocar el pla A | |
| 2.14 | N284 | Rz 6,3 / Rmax 10 | **Polir la superfície** | OK |
| 2.15 | N162 | 49,89−0,12 | Retoc màx **Ø0,22 mm** | OK |
| 2.16 | N161 | 45,4+0,12 | **Reduir Ø−0,305 mm** (en diàmetre total) | |
| 2.17 | N242 | 0,05 | Segons núvol de punts, *tenint en compte que mourem el pla A 0,02 mm* | |
| 2.18 | N288 | 15N–50N | *El pin fa **3,94**… Espera remesura* | |

> 📌 **12 de las 18 diapositivas terminan con un marcador `OK`** suelto. Es el campo de estado
> de la acción, y es directamente ingerible.

> 📌 **La corrección 2 audita a la 1 en su propio texto** (slides 2.7, 2.8, 2.18). No hace falta
> inferir si la corrección anterior funcionó: está escrito.

> 📌 **Slide 2.1 menciona los proyectos `3181` y `3157`**, que no están en `Exemples`. Confirma
> que la comparación entre piezas ya se practica manualmente → pregunta abierta A8.

---

## 5. Vocabulario de las acciones

Normalizarlo al ingerir — es el campo `sentido` del modelo de lesson learned.

| Expresión (catalán) | Qué se hace en el molde | Efecto en la pieza | Signo |
|---|---|---|:--:|
| *Fer créixer el plàstic* / *Incrementar plàstic* | Quitar acero | La cota crece | **+** |
| *Reduir el ferro* | Quitar acero (dicho al revés) | La cota crece | **+** |
| *Incrementar acer* / *Reduir plàstic* | Añadir acero | La cota disminuye | **−** |
| *Erosionar* | Electroerosión → quita acero | La cota crece | **+** |
| *Polir* | Acabado superficial | Sin cambio dimensional | ∅ |
| *Corregir segons núvol de punts* | Se le pasa el `.txt` de puntos al proveedor | — | ∅ |
| *No fer res* / *No tocar res* | Decisión explícita de no actuar | — | ∅ |

> Responde a la pregunta de las notas de reunión (*"¿son siempre quitar metal / añadir
> plástico?"*): **no**. Hay ambos sentidos, más erosión, pulido y correcciones por nube de
> puntos sin magnitud escalar.

---

## 6. Qué aporta a la base de datos

**Es la fuente única de las lessons learned.** Sin esta carpeta el proyecto no tiene contenido
que mostrar en el frontend.

| Fuente | Destino | Prioridad |
|---|---|:--:|
| Texto de las diapositivas | `CORRECCION_MOLDE` + `ACCION` (slide_nº, n_numbers, cota, acción, magnitud_mm, sentido, estado) | **4** |
| Imágenes de `ppt/media/` | `ACCION.imagen_zona_roja` — son **exactamente** las imágenes de "zona en rojo" que describe el frontend de `inteplast_PADIH_fase_B.md` | **5** |
| Nombre del `.xls` acompañante | `CORRECCION_MOLDE.muestreo_origen` | **4** |
| Frases de acoplamiento entre cotas | `DEPENDENCIA_COTA` (el plano A arrastra a las demás) | **4** |

Ver [modelo-datos.md](../modelo-datos.md) y [historial-molde.md](historial-molde.md).
