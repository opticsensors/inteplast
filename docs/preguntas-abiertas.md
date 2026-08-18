# Preguntas — abiertas y resueltas

> **Antes de preguntar algo a INTEPLAST, mirar aquí.** Varias de las preguntas originales se
> han resuelto leyendo los datos, sin necesidad de consultar.
>
> Última revisión: **2026-08-13**

---

## 🔴 ABIERTAS — hay que preguntar a INTEPLAST

> ⚠️ **Cómo se escriben estas preguntas.** El interlocutor de INTEPLAST no se acuerda de lo que
> hizo — estos datos son de 2024 y 2025 — y tiene poca paciencia para leer. Cada pregunta va en
> tres bloques cortos: **Recordatorio** (el ancla: fichero, fecha, diapositiva, su propia frase
> textual) → **Qué no nos cuadra** (con números) → **Pregunta** (una, directa, en negrita).
> Lo de *"por qué nos importa para la BD"* es para nosotros: **no se lo mandes**.

---

### A1 · Tres cotas quedaron NOK y el molde no se volvió a tocar

**Recordatorio.** El 18/03/2024 hicisteis la **corrección de molde nº2** del 3212
(`20240318-Mold correction_2_P3212_rev1.pptx`). Después seguisteis midiendo hasta
`intern.09`, en abril de 2025. Ya hemos comprobado en vuestros propios datos de CMM que
**el molde no se retocó más** después de esa corrección nº2.

**Qué no nos cuadra.** En `intern.08`, la última medición 3D completa, estas tres cotas están
fuera de tolerancia **en las cuatro cavidades**:

| Cota | Debe estar entre | c13 | c14 | c15 | c16 |
|---|---|--:|--:|--:|--:|
| **N161** Ø45,4 +0,12 | 45,400 – 45,520 | 45,393 | 45,367 | 45,380 | 45,384 |
| **N165** (max) 1,35 −0,05 | 1,300 – 1,350 | 1,399 | 1,394 | 1,411 | 1,399 |
| **N265** Ø59,7 −0,1 | 59,600 – 59,700 | 59,596 | 59,585 | 59,585 | 59,599 |

Y en N161 os pasasteis de largo: en la diapositiva **2.16** pedíais *"reduir Ø −0,305 mm"*
partiendo de 45,731, que estaba **por encima** del máximo. Acabó en 45,393, **por debajo** del
mínimo. Cruzó la tolerancia de lado a lado.

**Preguntas:**

1. **¿Bosch os firmó una concesión / desviación para estas tres cotas?** Si existe el documento,
   nos interesa.
2. **¿Se detectó en su momento que N161 se había pasado al otro lado?**
3. **¿Por qué se siguió midiendo hasta abril de 2025** si ya no se iba a tocar el molde?

<details><summary>Contexto interno (no enviar)</summary>

*Resuelto por datos → [R10](#r10--hubo-una-tercera-corrección-de-molde-era-a1). La respuesta a
la 1 es importante para la BD: "esta cota se quedó fuera y se aceptó" es una lesson learned de
pleno derecho y ahora no tenemos ni rastro de ella. La 2 es el caso de sobrecorrección más claro
de todo el proyecto. N161 además está ovalada (Ø mín. por debajo y LP(2) máx. por encima a la
vez), así que ninguna corrección de diámetro puro la iba a arreglar.*
</details>

---

### A3 · ¿Cuánto mide el pin del ensayo de inserción?

**Recordatorio.** En el método de medida del 3212 tenéis el ensayo de los N287/N288: se mete un
pin en el agujero del bolt eye a 0,1 mm/s y se registra la fuerza máxima, que debe caer entre
**15 N y 50 N**.

**Qué no nos cuadra.** Aparecen tres diámetros distintos para ese pin:

| Dónde | Diámetro |
|---|---|
| Método de medida | **Ø3,992** |
| Corrección 1, diapositiva **1.37** | *"el pin fa **3,93**"* |
| Corrección 2, diapositiva **2.18** | *"el pin fa **3,94**"* |

**Pregunta: ¿cuál es el pin que se usa realmente, y los otros dos números qué son?**
(¿un pin distinto, un desgaste, una medida de otra cosa?)

---

### A4 · Los planos 2D que tenemos son un escaneo

**Recordatorio.** El plano que nos disteis del 3212 es
`0140S00237` rev. 07, en PDF (`20250523_DRW 0140S00237_07.pdf`).

**Qué no nos cuadra.** Ese PDF **no tiene texto**: dentro hay **una sola imagen JPEG de
3276×2317 px** y **cero fuentes**. Todo lo que se saque de él es una reconstrucción por OCR, y al
ampliar se pixela.

**Y es el único sitio donde se ve dónde está cada cota.** Los N-numbers **no aparecen en ningún
otro fichero con su posición**: en las nubes de puntos (`3212_Cav13.txt`, `3212_PUNTS.txt`) **no
hay ni una letra** — son tres columnas de coordenadas — y las gráficas de contorno `PA_*/PB_*`
usan una numeración interna suya (`Contorno (21)`, `CONTORN (10)`). El único sitio donde un
N-number aparece **junto al punto de la pieza al que se refiere** es el plano.

**🆕 Qué hemos podido hacer nosotros (2026-08-18).** Montamos un visor con OCR
([`ver_plano.py`](../data-explorer/planos/ver_plano.py)) y el resultado acota mucho la petición:

- ✅ **Las notas se leen bien** (1.504 palabras, confianza media 74).
- ✅ **Confirmado que los N-numbers SÍ están en el plano**, en **globos verdes y sin la `N`**:
  el racimo del Bolt Eye pone `170`, `170.2` … `170.7` junto a la cota `Ø4 −0,1 (4x)`. Hemos
  localizado **178 globos**.
- ❌ **Pero el número de dentro no se puede leer.** Mide ~9 píxeles. Con Tesseract sale basura;
  con RapidOCR **parece** que sale bien y es peor: auditando 16 lecturas al azar contra la imagen,
  **solo 6 son correctas (37 %)**, y falla `155`→`156` **con 0,99 de confianza**. Los errores son
  de un dígito y no hay forma de detectarlos. Lo hemos quitado de nuestras herramientas.
- ❌ **Los marcos GD&T son ilegibles** (`⌖0,15 A-B` sale como `[1]`, `G97]`), y el símbolo `Ø` se
  lee como `9`/`@`/`$`.

O sea: **la petición no es un lujo, es la única salida.** Hoy el mapeo `N-number → zona de la
pieza` solo se puede hacer **a mano, ampliando globo a globo**, sobre 178 globos y para cada una
de las cuatro piezas. Con el plano en vectorial sería inmediato y exacto.

**Y si el CAD nativo no es posible, nos vale una alternativa más sencilla: el mismo plano
escaneado a más resolución.** El actual son 3276×2317 px (~198 DPI) y las cifras de los globos
miden 9 píxeles. A 600 DPI se leerían todas sin problema.

Y además **no es el plano de vuestros informes**: todos los informes, hasta `intern.09` de abril
de 2025, dicen `Drawing nº Level: 06`. El PDF que tenemos es la **rev. 07, del 23/05/2025** —
posterior a toda la metrología.

**Preguntas:**

1. **¿Nos podéis pasar el plano en un formato con texto** — PDF vectorial, **SVG**, DWG o el
   CATDrawing nativo? Nos vale cualquiera de los cuatro. Con el escaneo actual el mapeo
   `N-number → zona de la pieza` **hay que hacerlo a mano, globo a globo**: los números están
   impresos, pero a 9 píxeles ningún OCR los lee.
2. **¿Nos podéis pasar la rev. 06**, que es la que corresponde a las mediciones?

<details><summary>Contexto interno (no enviar)</summary>

*Verificado el 2026-08-13. Sin el plano vectorial, el mapeo `N-number → zona de la pieza` solo se
puede hacer (a) a mano sobre la imagen, (b) por OCR sobre los globos del plano, o (c) por anclaje
geométrico: cruzar el nominal del CSV con la nube de puntos, que funciona para las cotas
circulares pero deja fuera las que no están en la nube (N161/N162/N163) y las no circulares.
→ [3212/4-metrologia.md](3212/4-metrologia.md)*

*Actualización 2026-08-18: la vía (b) queda **descartada, y esta vez con la medida hecha**.
Tesseract da basura evidente. RapidOCR parecía funcionar (131 N-numbers "leídos") pero al auditar
16 lecturas al azar contra la imagen solo 6 eran correctas: **37 %**, con fallos de un dígito y
confianza de 0,99. Se ha quitado de `ver_plano.py`, que ahora solo LOCALIZA los globos y explica
por qué hay que pedir otro plano. Queda la vía (a), a mano.
→ [visores.md](visores.md) · [3212/1-pieza-2d-3d.md](3212/1-pieza-2d-3d.md)*
</details>

---

### A9 · Las gráficas de contorno `PA`/`PB` no dicen a qué cota del plano corresponden

**Recordatorio.** En cada carpeta de cavidad hay 12 PDF (`PA_1..6`, `PB_1..6`) titulados
*"Compar. tol. de contorno"* sobre el `3212-00 PUMP HOUSING INNER PROFILE`, con tolerancia
±0,025 mm.

**Qué no nos cuadra.** Esos PDF **no citan ningún N-number**. Identifican lo que miden con una
numeración interna vuestra: `PERFIL_A` con los contornos **21, 31, 22, 32, 23, 33** y `PERFIL_B`
con los **25, 35, 26, 36, 27, 37**, todos comparados contra el mismo nominal `CONTORN (10)`.
Como el N-number es lo que une plano, metrología y retoques de molde, estas 144 gráficas se nos
quedan colgando fuera del sistema.

**Preguntas:**

1. **¿A qué cota del plano (N-number) corresponde esta comparación de contorno?**
2. **¿Qué diferencia hay entre los seis recorridos de un mismo perfil** (21, 31, 22, 32, 23, 33)?
   ¿Son secciones a distinta altura, posiciones angulares, o repeticiones de la misma medición?
3. **¿De dónde sale el contorno nominal `CONTORN (10)`?** No está en ninguno de los ficheros que
   tenemos, así que no podemos recalcular la comparación por nuestra cuenta.

<details><summary>Contexto interno (no enviar)</summary>

*Estos PDF son **fuente única**: la comparación contra el perfil teórico no está en el CSV ni es
recalculable desde las nubes (⚠️ el `3212_CONTORN.igs` es el contorno **escaneado**, no el
nominal). Y son valiosos: prueban que la corrección nº1 dividió por 5,5 la desviación del
contorno en las 4 cavidades a la vez.
→ [3212/4-metrologia.md](3212/4-metrologia.md), [3212/historial-molde.md](3212/historial-molde.md)*
</details>

---

### A5 · Moldflow: no podemos abrir el `.mfr`

**Recordatorio.** En `7- Moldflow` del 3212 hay un fichero `.mfr` de 184 MB. En el *Dubte 6* nos
dijisteis que ahí están los puntos de inyección y las líneas de soldadura, y que se abren con
**Moldflow Communicator**.

**Qué no nos cuadra.** Es un formato binario propietario: sin licencia de Moldflow no podemos
leerlo, y meter 184 MB por estudio en la herramienta tampoco tiene sentido.

**Pregunta: ¿nos podéis exportar de cada estudio estas tres cosas?**

1. Una **imagen del patrón de llenado**
2. Una **imagen de las líneas de soldadura**
3. Los puntos de inyección: **número, posición, tipo y diámetro** — las cuatro variables que
   vosotros mismos dijisteis que definen la restricción

---

### A6 · ¿Qué features queremos fichar además del Bolt Eye?

**Recordatorio.** En la reunión de febrero acordamos empezar por el **Bolt Eye** del 3212
(N170 + N117), y en el *Dubte 4* nos dijisteis que las **llenties** (N118) van con la misma
filosofía pero **fichadas aparte**.

**Qué no nos cuadra.** Nada — es una decisión vuestra que aún no está tomada. Mirando vuestros
datos, estos son los candidatos que aparecen solos:

| Candidato | Por qué sale |
|---|---|
| **Llenties** | N242 (L1…L6, variantes A y B) + N118. Ya lo dijisteis vosotros. Aparece en las correcciones 1.35 y 2.9. |
| **Diámetros del perfil interior** | N161 / N162 / N163 — los que más se resistieron: hicieron falta las dos correcciones y N161 acabó fuera igual |
| **Espesores locales** | N165, con 60 secciones medidas cada 6° |
| **Tubuladuras** | N127 / N283 (Ø16,3−0,3) + cilindricidad N152 / N153, con el ensayo de estanqueidad |
| **Nervios** | Solo aparece en el 3197 (`3197_Punts_nervis_Frontal*.csv`) |

**Pregunta: ¿cuáles de estos cinco queréis que fichemos, y en qué orden?**

---

### A7 · Del `2820 Pump Housing` solo tenemos 2 ficheros

**Recordatorio.** En la carpeta `Exemples` nos disteis cuatro proyectos: 2820, 3051, 3197 y 3212.

**Qué no nos cuadra.** Del **2820** solo hay **dos ficheros**, los dos en `1-2D y 3D Pieza`:
el plano (`20160817_DRW_3130516933_…pdf`, de 2016) y el STEP de la pieza. No hay carpeta de
metrología, ni de retoques de molde, ni de Moldflow.

**Pregunta: ¿el 2820 tiene metrología y retoques y no nos los habéis pasado, o es una pieza
antigua sin histórico?**

---

### A8 · Los proyectos 3181 y 3157

**Recordatorio.** En la corrección de molde nº2 del 3212, diapositiva **2.1** (cota N128,
Ø21,5−0,2), escribisteis: *"De momento no tocar. **Marc ha de fer comparativa amb 3181 i
3157**"*.

**Qué no nos cuadra.** Esos dos proyectos no están entre los que nos disteis — en `Exemples`
solo hay 2820, 3051, 3197 y 3212.

**Pregunta: ¿nos podéis pasar el 3181 y el 3157?**

Es exactamente el caso de uso de la herramienta: vosotros ya comparáis una cota problemática
con lo que pasó en otras piezas, a mano. Con esos dos proyectos podríamos demostrarlo
funcionando.

---

## ✅ RESUELTAS con los datos (no hace falta preguntar)

### R10 · ¿Hubo una tercera corrección de molde? *(era A1)*

**Resuelto el 2026-08-12 cruzando los CSV de la CMM: no la hubo.**

Se compara el valor medido de cada fila entre dos muestreos. Antes de concluir, se **calibra el
método** sobre un tramo donde sabemos que sí hubo retoque (`intern.03 → .05`, con la corrección
nº2 en medio):

| Tramo | ¿Corrección en medio? | Filas | **Δ ≥ 0,10 mm** | Δ máx |
|---|---|--:|--:|--:|
| `intern.03 → .05` | ✅ la nº2 | 211 ×4 cav. | **129 en cada cavidad** | 0,335–0,349 mm |
| `intern.05 → .08` | ❓ | 211 ×4 cav. | **0 en las cuatro** | 0,055–0,081 mm |

Un retoque mueve **129 de 211 filas más de 0,10 mm en las cuatro cavidades a la vez**. Entre
`intern.05` (01/05/2024) e `intern.08` no se mueve **ninguna**, y el máximo de todo el fichero
(0,081 mm) queda por debajo de la menor acción documentada. **El molde no se tocó.**

`intern.09` no tiene CSV; de sus 6 cotas medidas de verdad, la única con histórico es `N162`:
49,858 (`.05`) → 49,855 (`.08`) → 49,840 (`.09`). **−0,015 mm en un año**: ruido.

> **No faltan ficheros de una corrección nº3.** Lo que queda por preguntar es *por qué se dio
> por bueno el molde con tres cotas NOK → [A1 reformulada](#a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué).*

**De regalo**, el tramo de control valida las acciones de la corrección nº2 una por una
(N161 −0,335 vs −0,305 pedidos; N162 +0,201 vs 0,22; N266 +0,124 vs 0,14; N265 +0,089 vs 0,11)
**y confirma [R9](#r9--las-diapositivas-sin-cota-identificada-era-a2)**: la slide 2.13, que
identificamos como `N240` leyendo una imagen, pedía bajar 0,08 mm — y N240 bajó 0,057 mm.

🔴 **Hallazgo colateral:** el bloque `N117`+`N118` de `intern.09.xls` (02/04/2025) es **copia
literal de `intern.01`** (25/01/2024) — los 32 valores idénticos, 15 meses después — y sus
`N275`/`N276` son copia de `intern.08`. Tercer caso de copia-pega detectado.

→ Todo el detalle en [3212/historial-molde.md §8](3212/historial-molde.md#8-hubo-una-tercera-corrección-de-molde--no).

### R9 · Las diapositivas sin cota identificada *(era A2)*

**Resuelto el 2026-08-11 leyendo las imágenes del PPTX.** No hacía falta preguntar: el
N-number **sí está en la diapositiva**, pero no en el texto, sino **dentro del recorte del
informe** que ilustra el bloque *Current situation*. La primera columna de ese recorte es la
columna `Nr` del `DR(3D)`.

| Slide | Retoc | N-numbers |
|---|:--:|---|
| **1.16** | +0,29 | `N155` · `N258` · `N267` · `N268` |
| **1.17** | +0,29 | `N154` · `N165` · `N166` · `N167` |
| **1.18** | +0,29 | `N236` · `N237` · `N240` · `N241` · `N252` · `N256` |
| **2.3** | +0,02 | `N154` · `N155` · `N258` · `N267` · `N268` |
| **2.4** | +0,02 | `N165` · `N166` · `N167` |
| **2.5** | +0,02 | `N236` · `N237` · `N240` · `N241` · `N252` · `N256` |
| **2.13** | −0,08 | `N240` |

🔑 **Las 6 primeras no son "diapositivas sin cota": son la diapositiva del PLANO A.** Las tres
comparten *la misma imagen de zona roja* (`image54.png` en la corr. 1 = `image12.png` en la
corr. 2, byte a byte 101.725 B), y en ella lo marcado en rojo es **la brida perimetral
completa**. No llevan `DIM. Nr.` porque el retoque no es de una cota: es un **desplazamiento de
la referencia** que arrastra a un grupo de cotas a la vez. Eso explica el `0,29 mm` que citan
las slides 1.27 (N236) y 1.28 (N243) como *"tocar el pla A"*.

**2.13 es distinta**: sí es una cota concreta, `N240` (18,5 +0,2 /5). El recorte del plano lleva
el globo `[]240` rodeado en rojo con una flecha.

**Evidencia** (ficheros y rutas dentro del ZIP):

| Qué | Dónde |
|---|---|
| Slides huérfanas corr. 1 | `ppt/slides/slide15.xml`, `slide16.xml`, `slide17.xml` = 1.16/1.17/1.18 *(desfase de 1 por la slide 5/37 que falta)* |
| Slides huérfanas corr. 2 | `ppt/slides/slide3/4/5/13.xml` = 2.3/2.4/2.5/2.13 *(sin desfase)* |
| Recortes con el N-number | corr. 1 → `image50,55,56,57` (1.16), `58,59,60,61` (1.17), `62,66,67,68,69,70` (1.18) · corr. 2 → `image13-16` (2.3), `17,18` (2.4), `22-26` (2.5), `48` (2.13) |
| Zona roja = plano A | corr. 1 `image54.png` · corr. 2 `image12.png` |

Validado que **todas** las imágenes de los `_rels` están realmente colocadas: el número de
`r:embed` distintos del `slideN.xml` coincide con el número de relaciones de imagen.

→ Detalle en [3212/5-retoques-molde.md](3212/5-retoques-molde.md) y la comprobación numérica
de que el retoque se aplicó en [3212/historial-molde.md](3212/historial-molde.md#6-la-segunda-prueba-el-plano-a).

### R1 · ¿Qué `intern.NN` corresponde a cada retoque de molde?

**Resuelto.** El enlace está en el **nombre del `.xls`** que acompaña a cada PPTX:
`3212-00_intern.01_mold_correction.xls`, `3212-00_intern.03_correction_2_.xls`. Las fechas
confirman (reunión 1–4 días alrededor del informe).

| Corrección | Origen | Validación |
|---|---|---|
| nº1 (24/01/2024) | `intern.01` (25/01/2024) | `intern.03` (14/03/2024) |
| nº2 (18/03/2024) | `intern.03` | `intern.05` (01/05/2024) |

Además la corrección 2 **audita explícitamente** la 1 en el texto de sus diapositivas, y 12 de
18 llevan un marcador `OK`. → [3212/historial-molde.md](3212/historial-molde.md)

### R2 · ¿A qué muestreo pertenece el STL?

**Resuelto.** `3212-315346-c13.stl` → lote **315346** = `Parts batch nº` de **`intern.03`
(14/03/2024) y `intern.04` (15/04/2024)**. Ambos comparten lote, así que el escaneado
corresponde a esa tirada — la **posterior a la corrección nº1**.

### R3 · ¿Cuál es la versión buena entre `rev0` / `rev1` / `rev1_`?

**Resuelto por comparación.** En el 3212:
- Corrección 1: `rev1` (es la única con PDF acompañante).
- Corrección 2: `rev1` y `rev1_` son **idénticos** (mismo tamaño, 7,65 MB) → da igual cuál.
- `2N/Old/` contiene la versión superada del `.xls`.

**Regla:** mayor `rev`, descartar `Old/` y `Copia de`.

### R4 · ¿Dónde está la acción que se hizo en el molde? *(Dubte 5)*

**Resuelto.** En los PPTX de `5- Retoques de molde`, una diapositiva por cota, con la magnitud
en mm y la zona marcada en rojo. Para las geometrías no circulares, INTEPLAST pasa al proveedor
una **nube de puntos** (`_PUNTS_NOUS.txt`, 150 puntos objetivo) en vez de una cota.

🆕 **Ampliado el 2026-08-13**: esos 150 puntos no son una nube suelta sino **6 contornos de 25
puntos** a alturas Y concretas (≈ uno cada 14,4°), y **los 12 ficheros del 3212 son todos
distintos** — hay un objetivo **por cavidad y por muestreo**, y las alturas cambian entre
muestreos. Es decir: **la corrección se especifica cavidad a cavidad**, no para el molde entero.
→ [3212/4-metrologia.md §4](3212/4-metrologia.md#los-txt-son-tres-familias-distintas-no-una)

### R5 · ¿Funcionó el retoque del Bolt Eye?

**Resuelto y cuantificado.** N170 Ø4−0,1, cavidad 13, bolt 1 @ H=1,5 mm:
`3,429` (NOK) → **corrección 1.33** → `3,974` (OK) → `3,981` → `3,978` un año después.
**+0,545 mm**, y N170 desaparece de la corrección nº2.

### R6 · ¿Cómo se calcula la posición ⌖? *(Dubte 2)*

**Verificado numéricamente** contra los datos reales:
`2 · √(ΔX² + ΔZ²) = 2 · √(0,006² + 0,011²) = 0,0251 ≈ 0,026` ✅

### R7 · ¿Qué significan `GX`, `GN`, `LP(2)`?

**Resuelto** con el método de medida: `GX` = Ø mínimo, `GN` = Ø máximo, `LP(2)` = distancia
directa entre dos puntos opuestos a la misma altura.
→ [3212/6-metodo-medida.md](3212/6-metodo-medida.md#2-vocabulario-de-evaluación)

### R8 · ¿Por qué se mide el agujero a dos alturas? *(Dubte 7)*

**Resuelto.** El cilindro interior es largo y lleva **grados de conicidad** para poder expulsar
la pieza. El cliente quiere Ø y posición arriba y abajo. Lo regula una **nota de ángulo de
desmoldeo** en el plano, no la tolerancia de posición.

---

## 📋 Preguntas originales a INTEPLAST y sus respuestas

Las 9 preguntas (*dubtes*) que se enviaron y las respuestas de **Xavier Arcos** (Metrology
Manager) están en **`inteplast_resposta_dubtes.md`**, en el vault de Obsidian
(`C:\edu\projects\Inteplast\`), con sus imágenes. Resumen:

| # | Tema | Respuesta clave |
|:--:|---|---|
| 1 | Ejes y error de B1 | B1 se usa para alinear → solo puede tener error en X. Los otros 3, en ambos sentidos. |
| 2 | Cálculo de la posición ⌖ | `2 · √(ΔX² + ΔZ²)`. Siempre positivo, 0 = perfecto. |
| 3 | Planitud del plano A | Es la referencia de alineación. Influencia **indirecta y de magnitud baja**, pero *"puede pasar de OK a NOK tocando ese plano"*. |
| 4 | Cotas N118 (llenties) | Misma filosofía, pero **ficharlo aparte** del bolt eye. |
| 5 | Dónde está la acción en el molde | Nube de puntos de la CMM al proveedor + los PPTX de corrección. |
| 6 | Puntos de inyección y líneas de soldadura | En los `.mfr` de `7- Moldflow`, con **Moldflow Communicator**. No hay correlación hecha con el error de posición. Restricciones: **posición, número, diámetro y tipo**. |
| 7 | Medida a dos alturas | **Conicidad de desmoldeo**. Lo fija una nota del plano o un acuerdo con el cliente. |
| 8 | Parámetros de máquina | **No van en la BD**: dependen de la geometría global, el material, el molde y la máquina. Demasiadas variables no ligadas al feature. |
| 9 | Calibre del diámetro | Es un **calibre pasa** de producción. *"No creo que sea importante."* |
