# 3212 — historial del molde (análisis transversal `4-` ↔ `5-`)

> Reconstrucción de la cadena **muestreo → corrección de molde → muestreo de verificación**.
> Es la evidencia de que **la lesson learned funcionó**, que es lo que da valor a toda la base
> de datos.
>
> El contenido de las carpetas está en [4-metrologia.md](4-metrologia.md) y
> [5-retoques-molde.md](5-retoques-molde.md). Aquí está el **análisis que las cruza**.
>
> **Verificado el 2026-08-11** sobre los 9 `.xls`, los 2 `.pptx` y los CSV de CMM de los
> muestreos 01, 03, 05 y 08.

---

## 1. Cronología

> 🆕 **Actualizada el 2026-08-13 con la hoja `HISTORY`.** Los huecos que había en esta tabla no
> eran datos perdidos: estaban en `HISTORY`, que es un **log acumulativo**. `intern.09.xls!HISTORY`
> tiene por sí solo la cronología entera.
> → [4-metrologia.md §2](4-metrologia.md#la-hoja-history-es-un-log-acumulativo--rellena-todos-los-huecos)

| Evento | Fecha | Lote | Responsable | Motivo (remark) | Datos 3D |
|---|---|---|---|---|---|
| 🔬 **Escaneo CMM del muestreo 01** | **19/01/2024** | — | — | *(fecha real de medición, del `.igs`)* | — |
| ⚙️ **Corrección nº1** — 36 diapositivas | 24/01/2024 | — | — | — | — |
| **`intern.01`** | 25/01/2024 | 315252 | DB | — | ✅ **completo** |
| `intern.02` | **08/02/2024** | **315252** | **MH** | **FOT** · *rougness push in* | ❌ |
| **`intern.03`** | 14/03/2024 | **315346** | **DB** | *cotes marcades en gris* | ⚠️ parcial |
| ⚙️ **Corrección nº2** — 18 diapositivas | 18/03/2024 | — | — | — | — |
| `intern.04` | **12/04/2024** ⚠️ | **315346** | KK | **FOT** | ❌ |
| **`intern.05`** | 01/05/2024 | 315426 | DB | *cotes marcades en gris* | ⚠️ parcial |
| `intern.06` | **15/05/2024** | — | **KK** | ***ICL + water + Push-in*** | ❌ |
| `intern.07` | **30/10/2024** ⚠️ | **315714** | **MH** | *Comparation of the technologies KnO x VdB* | ❌ |
| **`intern.08`** | **17/01/2025** ⚠️ | *Batch 08/01/2025* | NV | *Cotes CMM* | ✅ |
| `intern.09` | 02/04/2025 | *Batch 08/01/2025* | **MH** | *Sizes Nr.128/134/162 GN evolvation* | ✅ |
| `intern.09` *(2ª línea)* | **04/04/2025** | — | MH | *Update to 5 pcs* | — |

⚠️ **Tres discrepancias `HISTORY` ↔ cabecera del informe**: `.04` (12 vs 15/04/2024), `.07`
(30 vs 31/10/2024) y `.08` (17 vs 20/01/2024). En el `.08` **el año está mal en ambos sitios**:
por secuencia — informe 7 el 30/10/2024, lote del 08/01/2025 — tiene que ser **2025**.

📌 **El "lote ⚠️" de `.08`/`.09` no era un error de captura.** El remark dice literalmente
`Batch 08/01/2025`: ese lote **se identifica por fecha**. Hay que admitir el tipo, no corregirlo.

📌 **La fecha del XLS es la de emisión del informe, no la de la medición.** El `.igs` y los PDFs
PA/PB del muestreo 01 están fechados el **19/01/2024**, seis días antes del informe — y **un día
antes de la reunión de corrección nº1**. La corrección se decidió con los datos ya medidos.

Las 4 carpetas `support` (CMM) existen solo para **01, 03, 05, 08** — coinciden exactamente con
los muestreos que llevaron medición 3D real.

### 🆕 Segunda prueba independiente: el contorno del perfil interior

Extraídos los 144 PDF `PA`/`PB` (2026-08-13), la **infracción media de tolerancia** del perfil
interior por cavidad:

| Muestreo | c13 | c14 | c15 | c16 |
|---|--:|--:|--:|--:|
| `intern.01` | 0,160 | 0,160 | 0,161 | 0,162 |
| ⚙️ **corrección nº1** | | | | |
| `intern.03` | **0,029** | **0,034** | **0,027** | **0,026** |
| ⚙️ **corrección nº2** | | | | |
| `intern.05` | 0,027 | 0,031 | 0,024 | 0,026 |

🔑 **La corrección nº1 dividió la desviación del contorno por 5,5, y en las cuatro cavidades a la
vez** — la huella de un cambio en la geometría común del molde, no de un retoque cavidad a
cavidad. La nº2 no tocó esta zona (0,029 → 0,027).

Es una evidencia **independiente** de la del Bolt Eye y sobre un dato que **el CSV no contiene**.

⚠️ **Matiz**: los 12 elementos siguen fuera de tolerancia en los tres muestreos (12/12). La banda
es ±0,025 mm y queda una infracción residual de 0,01–0,06 mm. El perfil mejoró mucho pero **nunca
llegó a entrar en tolerancia** — un candidato claro de pregunta para INTEPLAST.
→ [4-metrologia.md](4-metrologia.md#los-144-pdf-pa_16--pb_16--tolerancia-de-contorno-fuente-única)

📌 **El STL `3212-315346-c13.stl` es del lote 315346** = `intern.03` / `intern.04`, es decir
**posterior a la corrección nº1**. → [8-stl-pieza-real.md](8-stl-pieza-real.md)

---

## 2. Cómo se enlaza una corrección con su muestreo

El enlace **está en el nombre del `.xls`** que acompaña a cada PPTX:

```
5- Retoques de molde/3212-00_intern.01_mold_correction.xls      → corrección 1 ← intern.01
5- Retoques de molde/2N/3212-00_intern.03_correction_2_.xls     → corrección 2 ← intern.03
```

Y las fechas lo confirman: la reunión de corrección cae **1–4 días** alrededor del informe.

> **Regla general:**
> El `intern.NN` del nombre del XLS que acompaña al PPTX es el muestreo **origen**.
> El siguiente muestreo con datos 3D reales es el que **valida** la corrección.

| Corrección | Origen | Validación |
|---|---|---|
| nº1 (24/01/2024) | `intern.01` (25/01/2024) | `intern.03` (14/03/2024) |
| nº2 (18/03/2024) | `intern.03` | `intern.05` (01/05/2024) |

⚠️ El contenido de esos `.xls` es irrelevante — son clones del informe original. **Solo importa
el nombre.** Ver [5-retoques-molde.md](5-retoques-molde.md#1-inventario-completo).

---

## 3. La verificación ya está escrita en los PPTX

La corrección nº2 **audita a la nº1 en su propio texto**:

| Slide | Cota | Texto |
|---|---|---|
| 2.7 | N265 | *"A l'últim ho demanàvem i **crec que no s'ha aplicat** o ho hem mesurat malament perquè **troben el mateix resultat**"* |
| 2.8 | N266 | *"**Que ha passat? Ens em colat molt no?** Incrementar acer o reduir plàstic 0,14 mm"* |
| 2.18 | N288 | *"El pin fa 3,94 d'entra cares? **Espera remesura**"* |

Y **12 de las 18 diapositivas terminan con un marcador `OK`** = el estado de la acción.

También hay **comparación entre proyectos ya hecha a mano**: slide 2.1 → *"Marc ha de fer
comparativa amb **3181 i 3157**"*, dos proyectos que no están en `Exemples`. Confirma que el
caso de uso *"¿qué pasó en piezas anteriores?"* ya se practica manualmente.

---

## 4. 🔑 La prueba: el Bolt Eye (N170)

Cavidad 13, cota **N170 Ø4 −0,1**, valores del CSV de CMM (bolt 1, altura H = 1,5 mm):

| Muestreo | Medido | Desviación | Semáforo |
|---|---|---|---|
| `intern.01` (25/01/24) | **3,429** | −0,571 | 🔴 `<<---+-----` |
| ⚙️ *Corrección **1.33**: "Podem utilitzar els expulsors de 4 com en els altres motlles"* | | | |
| `intern.03` (14/03/24) | **3,974** | −0,026 | 🟢 `-----***---` |
| `intern.05` (01/05/24) | **3,981** | −0,019 | 🟢 |
| `intern.08` (~2025) | **3,978** | −0,022 | 🟢 estable un año después |

**+0,545 mm de un solo retoque, y se mantiene.** Y **N170 desaparece de la corrección nº2** →
confirma que quedó resuelto.

Los 4 bolts a la vez (H = 1,5 mm, cav. 13):

| Muestreo | Ø1 | Ø2 | Ø3 | Ø4 |
|---|---|---|---|---|
| `intern.01` | 3,429 | 3,425 | 3,431 | 3,428 |
| `intern.03` | 3,974 | 3,976 | 3,984 | 3,981 |
| `intern.05` | 3,981 | 3,971 | 3,984 | 3,982 |
| `intern.08` | 3,978 | 3,967 | 3,981 | 3,979 |

### Por qué importaba (consecuencia funcional)

El método de medida define el ensayo **N287/N288**: se inserta un **pin de Ø3,992** a 0,1 mm/s
y se registra la fuerza máxima (rango 15N–50N). Con el agujero a **Ø3,43 el pin no entra**.
No era una cota fuera de tolerancia: era la pieza inservible.
→ [6-metodo-medida.md](6-metodo-medida.md#ensayos-funcionales)

### Posición N117 (⌖0,15) — el bolt 3 nunca acaba de ir bien

| Muestreo | B1 | B2 | B3 | B4 |
|---|---|---|---|---|
| `intern.01` | 0,026 | 0,036 | **0,087** | 0,061 |
| `intern.03` | 0,018 | 0,014 | **0,086** | 0,020 |
| `intern.05` | 0,036 | 0,031 | **0,086** | 0,021 |
| `intern.08` | 0,050 | 0,039 | **0,072** | 0,027 |

Todos dentro de tolerancia, pero **B3 es sistemáticamente el peor**. Y el operario ya lo sabía:
slide **1.34** dice *"**L'ull de la posición 3 es corretgeix menys**"*. Es un ejemplo perfecto
de conocimiento tácito que la base de datos debe capturar.

---

## 5. Qué arregló la corrección nº1

Cotas que estaban en la corrección 1 y **desaparecen** en la 2 (⇒ quedaron OK):

```
N113  N127  N134  N137  N138  N141  N142  N145  N150  N154  N159
N163  N167  N170 ★  N171  N175  N211  N214  N233  N236  N243  N283  N117/N118
```

Cotas que **persisten** (la corrección 1 no bastó):

```
N128  N158/N168  N161  N162  N165  N166  N242  N265  N266  N267  N268  N288
```

Cotas **nuevas** en la corrección 2: `N241`, `N284`.

> ⚠️ **Ojo con la inferencia.** "Desaparecer de la corrección 2" es un indicio fuerte, no una
> prueba. Para N170 sí está verificado numéricamente contra los CSV; para el resto habría que
> repetir el mismo cruce cota a cota. **No dar por bueno el resto sin comprobarlo.**

---

## 6. La segunda prueba: el plano A

*(Añadido el 2026-08-11 al resolver la pregunta A2 → [R9](../preguntas-abiertas.md).)*

Las diapositivas 1.16–1.18 (y sus gemelas 2.3–2.5) son **el retoque del plano A**: la zona roja
es la brida perimetral entera y no llevan `DIM. Nr.` porque la acción es sobre la **referencia**,
no sobre una cota. → [5-retoques-molde.md §3bis](5-retoques-molde.md#3bis--las-7-diapositivas-sin-cota-son-el-retoque-del-plano-a)

Eso permite una segunda verificación independiente de la del Bolt Eye, **sin salir de los
PPTX**: los recortes del informe que ilustran esas diapositivas llevan los valores medidos, y
los de la corrección 1 son de `intern.01` mientras los de la corrección 2 son de `intern.03`.

**Cavidad 13, valor `MIN` donde la cota se mide a min/max:**

| Cota | Nominal | `intern.01` | `intern.03` | Δ |
|---|---|---:|---:|---:|
| N154 | 5,85 −0,10 | 5,44 | 5,74 | **+0,30** |
| N155 | 49,5 ±0,20 /4 | 49,187 | 49,444 | **+0,257** |
| N240 | 18,5 +0,20 /5 | 18,440 | 18,695 | **+0,255** |
| N258 | 8,6 ±0,10 | 8,351 | 8,595 | **+0,244** |
| N252 | 14,6 +0,10 | 14,339 | 14,580 | **+0,241** |
| N268 | 5,35 +0,10 | 5,00 | 5,24 | **+0,24** |
| N241 | 20,7 +0,25 | 20,48 | 20,71 | **+0,23** |
| N267 | 4,6 +0,10 | 4,47 | 4,63 | +0,16 |
| N237 | 13,4 +0,05 /5 | 13,403 | 13,398 | −0,005 |
| N236 | 12 +0,05 /5 | 12,027 | 11,982 | −0,045 |
| **N256** | **15,7 +0,10** | **15,331** | **15,10** | **−0,231** |

🔑 **El retoque de 0,29 mm del plano A se aplicó.** Siete cotas del grupo se mueven
**+0,23…+0,30 mm**, muy cerca del valor pedido, y pasan de rojo (NOK) a negro (OK) en el
recorte de la corrección 2.

### El efecto secundario: N256

**N256 se mueve la misma magnitud pero en sentido contrario** (−0,231) y **empeora**: ya estaba
por debajo del mínimo (15,331 < 15,70) y acaba en 15,10. Es la firma de un desplazamiento de
referencia: lo que se mide *desde* el plano A crece, lo que se mide *hacia* él decrece.

Y **la corrección 2 no lo arregla**: le aplica el mismo `Retocs` genérico de +0,02 mm del
grupo, que no basta ni de lejos. N256 sale de la corrección 2 **todavía NOK** y no hay
corrección 3 en los datos → refuerza la pregunta abierta **A1**.

> ⚠️ Ojo con N165, N166 y N167: también aparecen en el grupo del plano A, pero además tienen
> diapositiva propia (1.29, 1.21, 1.20) con su propia acción. Su Δ **no es atribuible solo al
> plano A** y no se ha incluido arriba.

> 📌 **La columna `Retoc` de esos recortes es una predicción**: INTEPLAST escribe el retoque
> propuesto y **el resultado simulado cavidad a cavidad** antes de tocar el molde. Comparar esa
> predicción con lo que salió después es material de primera para el frontend — y es
> directamente ingerible.

---

## 7. Acoplamientos entre cotas

El **plano A es la referencia de alineación**, así que tocarlo mueve todo lo demás. Aparece
explícito en 5 diapositivas:

- **1.27 (N236)**: *"si ens quedem curts s'ha de tornar a tocar el Pla A i afecta a moltes coses"*
- **1.28 (N243)**: *"si toquem 0,29 mm en el pla A, tocar aquí 0,27"*
- **1.29 (N165)**: *"com a màxim tocar 0,38 mm després de tocar el pla A"*
- **2.11 (N165)**: *"com a màxim tocar 0,22 mm després de tocar el pla A"*
- **2.17 (N242)**: *"tenint en compte que mourem el pla A 0,02 mm"*

Y sobre todo: **las diapositivas 1.16–1.18 y 2.3–2.5 son la dependencia escrita en negro sobre
blanco** (§6). Dan la lista explícita de las cotas que INTEPLAST considera arrastradas por el
plano A:

```
N154  N155  N165  N166  N167  N236  N237  N240  N241  N252  N256  N258  N267  N268
```

más `N243` por la 1.28 y `N242` por la 2.17. **Son 16 cotas colgando de una sola referencia.**

⚠️ Y **el signo no es uniforme**: de las que se pueden medir limpiamente, 8 crecen ≈ +0,25 mm,
`N236`/`N237` no se mueven y **`N256` decrece −0,23 mm** (§6). La dependencia hay que modelarla
**con signo por cota**, no como "tocar A sube todo".

Esto conecta directamente con el **warning de planitud N178** (Dubte 3): *"si no és recte pot
tenir influència en el resultat final de les posicions… pot passar de estar OK a NOK tocant
aquest pla"*.

→ **La BD necesita modelar dependencias entre N-numbers**, no solo cotas independientes.
Es la entidad `DEPENDENCIA_COTA` de [modelo-datos.md](../modelo-datos.md).

---

## 8. ¿Hubo una tercera corrección de molde? — **no**

*(Resuelto el 2026-08-12 cruzando los CSV de CMM — era la pregunta abierta A1.)*

### El método y su calibración

Se normalizan los CSV de CMM de dos muestreos (bloque + índice de fila dentro del bloque como
clave) y se resta el valor medido. Antes de concluir nada hay que **comprobar que el método
detecta un retoque conocido**, así que se corrió primero como control el tramo
`intern.03 → intern.05`, que tiene **la corrección nº2 en medio** (18/03/2024).

| Tramo | ¿Corrección en medio? | Filas | Δ ≥ 0,02 mm | Δ ≥ 0,05 mm | **Δ ≥ 0,10 mm** | Δ máx |
|---|---|--:|--:|--:|--:|--:|
| **`intern.03 → .05`** c13 | ✅ **sí, la nº2** | 211 | 142 | 131 | **129** | 0,335 |
| `intern.03 → .05` c14 | ✅ | 211 | 150 | 132 | **129** | 0,349 |
| `intern.03 → .05` c15 | ✅ | 211 | 149 | 132 | **129** | 0,343 |
| `intern.03 → .05` c16 | ✅ | 211 | 150 | 135 | **129** | 0,335 |
| **`intern.05 → .08`** c13 | ❓ | 211 | 12 | 1 | **0** | 0,070 |
| `intern.05 → .08` c14 | ❓ | 211 | 24 | 4 | **0** | 0,081 |
| `intern.05 → .08` c15 | ❓ | 211 | 29 | 3 | **0** | 0,078 |
| `intern.05 → .08` c16 | ❓ | 211 | 19 | 3 | **0** | 0,055 |

🔑 **La diferencia no admite discusión.** Un retoque de molde deja **129 de 211 filas movidas más
de 0,10 mm, en las cuatro cavidades a la vez**. Entre `intern.05` e `intern.08` hay **cero**, y
el máximo de todo el fichero (0,081 mm) está por debajo del mínimo de cualquier acción de las
correcciones documentadas.

> **Conclusión: el molde no se tocó entre el 01/05/2024 y `intern.08`.** No faltan ficheros de
> una corrección nº3: no hubo corrección nº3.

### De regalo: el control valida las acciones de la corrección nº2 una por una

El tramo de control no es solo una calibración, es **la verificación de la corrección nº2** que
[§5](#5-qué-arregló-la-corrección-nº1) dejaba pendiente. Cavidad 13:

| Cota | Pedido en la diapositiva | Medido `.03`→`.05` | ¿Cuadra? |
|---|---|--:|:--:|
| N161 | 2.16 · *reduir Ø −0,305 mm* | **−0,335** | ✅ |
| N162 | 2.15 · *retoc màx Ø 0,22 mm* | **+0,201** | ✅ |
| N165 (60 puntos) | 2.11 · *màx 0,22 mm* | **−0,16 … −0,20** | ✅ |
| N266 | 2.8 · *0,14 mm* | **+0,124** | ✅ |
| N265 | 2.7 · *0,11 mm* | **+0,089** | ✅ |
| **N240** | **2.13 · *pujar 0,08 mm*** | **−0,057** | ✅ |

La última fila es una **validación cruzada de [R9](../preguntas-abiertas.md)**: la diapositiva
2.13 no decía su cota y la identificamos como `N240` leyendo la imagen. Predijo que N240 tenía
que bajar 0,08 mm — y N240 bajó 0,057 mm. Ninguna otra cota del fichero se movió en ese sentido
y esa magnitud. La identificación era correcta.

### `intern.09` — tampoco, pero la evidencia es más débil

`intern.09` **no tiene carpeta `support`**, así que no hay CSV: solo su hoja `DR`. Y esa hoja
solo trae **6 cotas medidas de verdad** (`N128`, `N134`, `N162`, `N275`, `N276`, `N284`).

De las que se pueden comparar con `intern.08`, la única con histórico es `N162`:

| | `intern.05` | `intern.08` | `intern.09` |
|---|--:|--:|--:|
| N162 Ø49,89 GN (c13) | 49,858 | 49,855 | 49,840 |

**−0,015 mm en un año.** Ruido. Sin indicio de retoque.

### 🔴 Hallazgo colateral: `intern.09` también tiene datos caducados

Verificado valor a valor contra los CSV: **el bloque N117 + N118 de `intern.09.xls` (02/04/2025)
es copia literal de `intern.01` (25/01/2024)**. Los 32 valores — 4 bolts × 4 llenties ×
4 cavidades — coinciden exactamente, 15 meses después:

```
N117 intern.01 CSV   c13: 0.026 0.036 0.087 0.061      N118 intern.01 CSV   c13: 0.015 0.130 0.235 0.148
                     c14: 0.030 0.005 0.111 0.083                           c14: 0.076 0.054 0.201 0.254
                     c15: 0.041 0.007 0.115 0.066                           c15: 0.078 0.122 0.176 0.152
                     c16: 0.039 0.023 0.093 0.022                           c16: 0.005 0.061 0.187 0.159
                     ↑ idénticos a intern.09.xls        ↑ idénticos a intern.09.xls
```

Y `N275` (0,184) y `N276` (0,042) de `intern.09` son **copia de `intern.08`** — ahí sí
verificados como auténticos contra el CSV de `.08`.

> ⚠️ **`intern.09.xls` es un collage**: bloques de `intern.01`, bloques de `intern.08` y unas
> pocas medidas nuevas. Es el **tercer** caso de copia-pega detectado (los otros: `intern.05.xls`
> y este mismo fichero por partida doble). **Ningún XLS es fuente de verdad.**

### Cómo acabaron las cotas problemáticas

Estado en `intern.08`, la última medición 3D completa, en **las 4 cavidades**:

| Cota | Nominal | c13 | c14 | c15 | c16 | Veredicto |
|---|---|--:|--:|--:|--:|---|
| **N161** | Ø45,4 **+0,12** | 45,393 | 45,367 | 45,380 | 45,384 | 🔴 **NOK — pasada de rosca** |
| **N165** (max) | 1,35 **−0,05** | 1,399 | 1,394 | 1,411 | 1,399 | 🔴 **NOK** en las 4 |
| **N265** | Ø59,7 **−0,1** | 59,596 | 59,585 | 59,585 | 59,599 | 🔴 **NOK** (por 4–15 µm) |
| N162 | Ø49,89 −0,12 | 49,855 | 49,856 | 49,834 | 49,863 | 🟢 ok |
| N163 | Ø52,79 +0,12 | 52,807 | 52,807 | 52,824 | 52,806 | 🟢 ok |
| N266 | Ø67,1 +0,1 | 67,126 | 67,120 | 67,121 | 67,130 | 🟢 ok |
| N170 (bolt 1, H1,5) | Ø4 −0,1 | 3,978 | 3,975 | 3,976 | 3,974 | 🟢 ok |

📌 **`N161` es un caso de libro de sobrecorrección.** Estaba en 45,731 (por encima del máximo
45,520); la corrección 2.16 pidió reducir 0,305 mm; el resultado fue 45,396 — **por debajo del
mínimo 45,400**. Se cruzó al otro lado de la tolerancia. Es exactamente el tipo de lesson
learned que justifica el proyecto: *"cuidado, en el 3212 este retoque se pasó"*.

Y hay un segundo matiz: N161 se evalúa con **dos filas**, `GX` (Ø mínimo) y `LP(2) MAX.`
(distancia máxima entre puntos opuestos). En `intern.08` c13 salen **45,393** (`<<` por debajo)
y **45,525** (`>>` por encima) a la vez. No es solo que el agujero sea pequeño: **está ovalado**,
y ninguna corrección de diámetro puro lo va a arreglar. Las dos acciones que recibió (1.31 y
2.16) eran reducciones de Ø.

`N265` es el caso opuesto: falla **por 4 µm** (59,596 frente a un mínimo de 59,600). Al ingerir
conviene guardar la distancia al límite, no solo el booleano NOK — no es lo mismo pasarse 4 µm
que 49.

> 🔴 **Y aquí está la pregunta que sí hay que hacerle a INTEPLAST**: tres cotas quedaron NOK en
> las cuatro cavidades, el molde no se volvió a tocar y se siguió produciendo un año más.
> ¿Se aceptaron por concesión del cliente? → A1 reformulada en
> [preguntas-abiertas.md](../preguntas-abiertas.md).
