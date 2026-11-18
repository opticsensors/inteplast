# Cotas de cada feature por pieza

> **Referencia de trabajo (ground truth) acordada con Eduard el 18/11/2026.** Recoge qué cotas
> forman cada feature en cada pieza de `Exemples`, con su evidencia. Sirve para la presentación
> a INTEPLAST y como patrón contra el que comparar cualquier propuesta automática.
>
> **Qué es y qué no es.** Es una asociación **documental**: cada fila sale de un original leído
> (método de medida, informe, plano o diapositiva). **INTEPLAST no la ha validado.** Qué cotas
> quiere enseñar INTEPLAST como representativas de cada feature sigue siendo decisión suya.
> No sustituye al algoritmo de la app ni se copia a mano en fichas (regla del 16/11/2026,
> [AGENTS.md](../AGENTS.md)).
>
> **Cómo se hizo.** Primera propuesta de Claude, revisión independiente de un segundo asistente y
> contraste final de Claude sobre los originales, el 18/11/2026. Las filas marcadas *(registro V-)*
> vienen de los vínculos `V-*` de [hallazgos.jsonl](hallazgos.jsonl) (Codex, 02/11/2026) y no se
> han vuelto a abrir. Rutas relativas a `Exemples/`.

**Confianza documental**

- **Alta:** un original nombra el feature junto a la cota, o el plano la dibuja sobre el elemento.
- **Media:** se deduce de una corrección o de la geometría sin que el texto nombre el feature.
- **Baja / candidata:** se enseña como propuesta pendiente de confirmar.

**Rol:** *principal* (define el elemento), *relacionada* (citada al corregirlo), *funcional*
(ensayo del conjunto), *referencia* (datum o control indirecto).

Los números de cota son locales a cada plano. Que dos piezas usen el mismo número no relaciona
sus cotas.

---

## 0. Bolt Eye

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3212 | N170 | Ø4 −0,1 (×4), a H = 1,5 y 5 | principal | Alta | Plano rev. 07 *(registro V-3212)*; [ficha](0-bolt-eye/3212/6-metodo-medida.md) |
| 3212 | N117 | Posición ⌖0,15 A/B | principal | Alta | Ídem |
| 3212 | N178 | Planitud 0,10 del plano A | referencia | Alta | Ídem |
| 3212 | N288 | Ensayo de inserción del pin 15–50 N | funcional | Alta | Plano rev. 07, globos 288/288.1. El método DOCX lo rotula **N287** ([A3](../docs/preguntas-abiertas.md), I-207) |
| 3197 | N230 / N220 | Ø4 +0,1 / posición ⌖0,25 MMC | principal | Alta | *(registro V-3197)* |
| 3051 | N880 / N890 | Ø3,8 +0,1 / posición ⌖0,2 MMC | principal | Alta | *(registro V-3051)* |
| 2820 | []252 | 5× ⌖Ø0,1Ⓜ A\|B\|C, flecha en el agujero de una oreja | principal | Candidata | `0- Bolt Eye/2820 Pump Housing/1-2D y 3D Pieza/20160817_DRW_…EN_DE.pdf`, vista superior derecha (sin capa de texto, leído en imagen) |
| 2820 | []207 | 3,8 +0,1 en la sección A–A | relacionada | Candidata | Ídem, sección A–A. Nota []166: *«applies to screw flanges no. 1»* |

⚠️ **3212, seed frente a `V-3212`:** `backend/app/seed_features.py:154` vincula N170, N117, N178 y
N288 en **rev. 06**. `V-3212` registra N170, N117 y N178 en **rev. 07**. N288 está en el plano
rev. 07; que falte en `V-3212` refleja el alcance de ese registro, no que no pertenezca al
feature. Recomendación de la revisión: mantener rev. 06 en el seed, porque los nueve informes
históricos citan la rev. 06 (pregunta 2 de A4 en [preguntas abiertas](../docs/preguntas-abiertas.md)), y usar la rev. 07 solo como plano
de referencia en la presentación. El seed marca N288 como `primary`; documentalmente es un ensayo
*funcional*. Ambas son decisiones de la app, pendientes.

2820 no tiene histórico de medición: solo plano y STEP ([ficha](0-bolt-eye/2820.md)).

## 1. Clips en piezas

En las *bearing plates* (3174, 3186, 3218) los «clips» son los pines que encajan la placa
(*clipped pins*). Casi todo se mide con la pieza clipada (H-301).

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3174 | N712 | *«Measure the position of the clip»* | principal | Alta | `…/3174/6- Método de medición/3174_00_MM_rev07.xls!DIMENSIONS` fila 50 |
| 3174 | N215 | *«Evaluate the profile of the clips from D reference»* | principal | Alta | Ídem, fila 16 |
| 3174 | N216 | *«Profile of the inner clips from D reference»* (CT) | principal | Alta | Ídem, fila 17 |
| 3174 | N511 | Ø4,6 ±0,05, mín./máx. en los tres pines | relacionada | Alta | Ídem, fila 33. La corrección 2.12 dice *«Move the clips num. 2 and num. 3»* sobre la 511: el plan desplaza el pin, la cota es el diámetro |
| 3186 | N216 | Perfil de los clips interiores | principal | Alta | `…/3186/6- Método de medición/3186_00_MM_rev01.xls!DIMENSIONS` fila 16 |
| 3186 | N1003 | Posición ×2 que controla ese perfil | referencia | Alta | Misma fila, celda J16: *«this profile will be checked by the position of dimension 1003 (x2)»* |
| 3186 | N215 | Perfil desde D, sin la palabra *clip* | relacionada | Media | Ídem, fila 15. En el 3174 la misma cota se llama *«profile of the clips»*; el plano archivado del 3186 es el del 3174 (I-301) |
| 3218 | N2603 / N2612 | Clip 1: Ø2 ±0,05 a 1 mm del fondo / posición del clip | principal | Alta | `…/3218/6- Método de medición/3218_00_MM_rev04.xls!DIMENSIONS` filas 40–41. La corrección 10.9 cita las dos juntas (Ø2 ±0,05; posición 0,1) |
| 3218 | N2702 / N2705 | Clip 2: Ø / posición | principal | Alta | Ídem, filas 42–43 |
| 3218 | N2902 / N2905 | Clip 3: Ø / posición | principal | Alta | Ídem, filas 46–47 |
| 3218 | 2601, 2904 | 2,6 +0,05/0: *«correct the clip on both side 0,07 mm»* | relacionada | Media | Correcciones 1.28 y 1.34 |
| 3218 | 500 | Ø2,45: *«correct… at each side of the clip 0,05 mm»* | relacionada | Media | Corrección 1.9 (plan con nombre heredado P3174, I-302) |
| 3218 | 1906–1912 | *«The clip is closing too much during the injection»* | relacionada | Media | Corrección 1.16 |
| 3218 | 1910, 2501 | Ø2,32 ±0,03 y Ø2,65 ±0,05; *«Position of the clip is OK»* | relacionada | Media | Correcciones 10.4 y 10.7 |
| 3195 | 3120 | 7,4 +0,1; *«correct 0,04 mm only in the clip surface»* | principal | Media | Correcciones 1.16/1.17 del plan 1. La versión comentada por el matricero (rev3) dice que ya no hacía falta corregir |
| 3309 | N15 | Distancia entre clips (arriba y abajo), pieza clipada en CMM; también con calibre | principal | Alta | `…/3309/6- Método de medición/3309_00_V1_MM.xls!DIMENSIONS` filas 8–9 |
| 3309 | N14, N16 | Cotas que afectan a la N15 al corregirlas | relacionada | Media | W-3309 (plan T3) |
| 3309 | F1, F2, F3 | Fuerza de extracción total (250 N mín.), extracción en posición temporal (18 N mín.), inserción (50 N máx.) | funcional | Alta | Ídem, filas 11–13 |
| 3226 | — | El informe no numera las cotas | — | — | 47 filas con nominal y columna `Nr` vacía ([A28](../docs/preguntas-abiertas.md#a28-3226-sin-numeracion)) |

## 2. Nervios de soldadura

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3205 | 17 | 7,2 ±0,05: longitud del director de energía (×5) | principal | Alta | Corrección 6.1: *«La longitud del director d'energia està correcte (cota 17)»*; `3205-00_intern.11.xls!DR` fila 140 |
| 3205 | 18 | 0,6 ±0,05: grosor del director | principal | Alta | Corrección 2.4 (*«Incrementar el gruix del director d'energia»*); `intern.11` fila 145 |
| 3205 | 19 | R24,1 ±0,075: posición radial del director | principal | Alta | Corrección 6.1 (*«Moure tot el director d'energia 0,1 mm cap a la part exterior»*); `intern.11` fila 155 |
| 3205 | 152 | 0,9 ±0,1: altura del nervio | principal | Alta | Corrección 2.4; *«Rib height 0,9 ±0,1»* en la comparación de lotes |
| 3205 | 62, 104, 154 | 0,6 ±0,05; 1° ±0,5; 60° ±1 | relacionada | Media | Citadas juntas en la corrección 2.4. La diapositiva escribe «191» para el valor R24,1, que en el informe es la 19 |
| 3205 | 21 | Rebaba ≤ 0,2 en los nervios | relacionada | Alta | `intern.11` fila 238; loops 9–10 *«Burrs on the ribs»* por cavidad y nervio |
| 3205 | 3 | 2,4 ±0,1; comentario *«Flashes on the ribs (+0.2 on tol.)»* | relacionada | Media | `3205-00_intern.26.xls!DR` fila 19 |
| 3206 | 64 | R25,6 ±0,075, *«EDGE OF THE RIB»* | principal | Alta | `3206-00_intern.02.xls!DR_(100%)` fila 127. La corrección 6.1 titula «DIM. Nr. 19» pero su texto remite a la cota 64 |
| 3206 | 20 | 0,6 ±0,05 (×7 posiciones) | principal | Alta | `intern.02` filas 89–102; corrección 1.2 *«ribs»* |
| 3206 | 21 | 6 ±0,05 (×7 posiciones) | principal | Alta | `intern.02` filas 103–116; corrección 1.3 *«ribs»* |
| 3206 | 83 | 0,9 ±0,1 (×7), evaluada en mínimo y máximo: altura de los nervios | principal | Alta | `intern.02` filas 187–188; plan del 21/03/2024, diapositiva 5 |
| 3206 | 6 | 2,3 ±0,1 | relacionada | Media | Corrección 1.5 (05/09/2023): *«Increase height of all the ribs»* |
| 3206 | 203 | Nota: *«Draft angle of blade groove, and welding ribs»* | relacionada | Alta | `intern.02` fila 212, informativa |
| 3214 | 10 | 13,8 ±0,2, *«centre weld rib»* | principal | Alta | `…/3214/4- Metrologia/Customer/3214-00_int.02_customer.xls!DR` fila 28 |
| 3214 | 12, 13 | 0,26 +0,06/−0,05 y 0,3 ±0,05, *«height weld rib»* | principal | Alta | Ídem, filas 30–31 |

⚠️ **3206, la 19 no es el radio del nervio:** en `intern.02` (filas 75–88) la 19 es un perfil 0,2
respecto de B/C en siete posiciones, izquierda y derecha (1-L … 7-R). En el 3205 la 19 sí es R24,1: cada pieza tiene su numeración.

## 3. Paredes muy delgadas

El espesor de pared se identifica en el plano: la cota tiene las flechas entre las dos caras.
Buscar nominales pequeños no sirve, porque mezcla radios y huelgos.

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3237 | 123 (PPAP 1-123, 1-123.1) | Espesor de pared 0,4 ±0,05 (2×), medido con calibre | principal | Alta | `…/3237/1- 2D y 3D pieza/20260914_3130589019 2D 05.pdf`, sección D–D; `…/3237/4- Metrologia/Customer/PPAP_3237_INF_02.xlsm!cav_1` filas 108–109 |
| 3237 | 116 | 0,3 ±0,05 (2×) en la misma sección | relacionada | Media | Plano, sección D–D |
| 3238 | 148 (1-148, 1-148.1) | Espesor de pared 0,4 ±0,05 (2×), por CT | principal | Alta | `…/3238/1- 2D y 3D pieza/20260914_313058901F 2D 05.pdf`, sección D–D; `PPAP_3238_INF_02.xlsm!cav_1` filas 121–122 |
| 3238 | 4010 | Nota: desmoldeo de todo el contorno de pared fina, excepto ranuras | relacionada | Alta | `PPAP_3238_INF_02.xlsm!cav_1` fila 179, informativa |
| 3233 | 520 | Espesor del fondo bajo las ondulaciones, 0,4 ±0,05, por CT | principal | Alta | `…/3233/6- Método de medición/Support MM/20230728_DRW_0196S0000K_D_01.pdf`, sección C–C, zona G7; `…/3233/4- Metrologia/Customer/3233-00_inf.06_OPL_81A.xls`: hoja `100% BOSCH PORTAL` fila 105 da «520»; hoja `100%` fila 106 da «G7» con los mismos valores |

**No son espesores:** 3237 1-1 y 3238 1-2 son **R0,25 ±0,1** (sección J–J). En el PPAP del 3238,
el «2» de la fila 179 es la columna `e_Type`, no el número de cota. 3233/480 es **R0,2 ±0,05**
(esquina de la sección C–C), y 490/530 también llevan `R`. 3237 1-88 (0,2) y 1-131 (0,27) y
3238 1-104 (0,2, comparador) y 1-116 (0,18, CT) no se han localizado en el plano.

**Correcciones de engrosamiento:** 3237 1.5 (diapositiva 6) y 3238 1.7 (diapositiva 8) colorean en
amarillo la zona a engrosar sobre el CAD sin escribir ningún número de cota. Qué cota corrigen sigue
abierto.

## 4. Tetones

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3288 | 80 | Remachado sin sobresalir del plano base y sin holgura pin–agujero (lupa DG0266) | principal | Alta | `…/3288/6- Método de medición/MM732880000_rev00.pdf` p. 6, conjunto **BSG-296-00 nivel 2**; `MM3288_rev0.xlsx!Dimensions` fila 16. No confundir con la 80 de `DR(base)` (I-106) |
| 3288 | 30 | 3,3 ±0,1: altura de los pines indicadores (pasa/no pasa D28212 o comparador) | principal | Alta | `MM3288_rev0.xlsx!Dimensions` filas 11 y 13 |
| 3288 | 43 | 2,7 ±0,1: altura del pin | principal | Alta | Ídem, fila 15 |
| 3214 | 6 | Ø1,14 ±0,02 de los pines | principal | Alta | Corrección 1.1, diapositiva 1 (`…/3214/5- Retoques molde/20231003-Mold correction_1_P3214.pptx`): *«increase in Ø0,03 the pins»*, con el croquis de los cuatro pines; `3214-00_int.02_customer.xls!DR` fila 20 |
| 3214 | 3, 4, 5, 7 | 30,9 / 2,55 / 13,9 / 5,75 ±0,05: posiciones de los pines en el mismo croquis | relacionada | Media | Croquis de la corrección 1.1; `int.02_customer` filas 17–19 y 24 |
| 3167 | 500 … 500.5 | Ø1,4 ±0,05, *«Gauss Pin at Tooth 2, 4, 6, 8, 10, 12»* | principal | Media | `…/3167/4- Metrologia/Customer/PPAP-3167-00_4/…/PPAP-3167-00_Inf_04*.xlsm!cav_1`, columna P |
| 3167 | 470, 490, 520, 540 | Ø1 / 0,8 ±0,05: *«Add the ribs to all the pins (x6 pin) (x3 ribs per pin)»* | relacionada | Media | Corrección 1.3, `…/3167/5- Retoques molde/1stloop of corrections/202307-Mold correction_1_P3167_v2.pptx` diapositiva 3 |

Pendiente para 3214 y 3167: INTEPLAST los incluyó en Tetones, pero no consta que llame «tetón» a
estos pines.

## 6. Pockets

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3167 | 1220 (… .8, .9 … .17, .T…) | Pockets 2 a 10; nominal 0, tolerancia +0,5 | principal | Alta | `PPAP-3167-00_Inf_04 - Desviacions aplicades.xlsm!cav_1`, columna P *«POCKET #2…#10»* |
| 3167 | 2120, 2260 (… .3) | Pockets 1, 11, 12 y 13 (2120 = 5,2 +0,1/0; 2260 = tolerancia +0,5) | principal | Alta | Ídem, *«POCKET #1, #11–#13»* |
| 3167 | 2730, 2740 | 39,31 +0,2/−0,1: 2730 en los puntos P1–P3 de los pockets 6–13; 2740 en P4–P6 de los pockets 1–6 y 8–13 | principal | Alta | `…/PPAP-3167-00_2/PPAP-3167-00_2.xlsm!cav_1`, columna P: pocket 6 = 2730–2730.2 (P1–P3) y 2740.15–.17 (P4–P6). Las etiquetas de los pockets 1–4 de la 2740 están más abajo (p. ej. fila 558, *«Pocket 1 P4»*). Corrección 2.3 (posible aceptación en pockets 1 y 13, H-602). En `Inf_04` la tolerancia inferior es −0,15 y la columna D solo dice P1…P6 |
| 3167 | 1240, 1320 | 0,8 ±0,05: *«Correct to all the pockets of all the cavities»* | principal | Alta | Correcciones 1.1, 1.2 y 3.2 (*«Touch only the pocket 13»*) |
| 3167 | 1290 | *«Thickness of the holder»*, todos los pockets | principal | Alta | Corrección 1.12 |
| 3167 | 1030, 1090 | 4,1 ±0,05; retoque en pockets 2–10 y 12–13, no en 1 y 11 | relacionada | Alta | Corrección 3.1, `…/3167/5- Retoques molde/3r loop of corrections/20240605_Mold correction_3_P3167_v1.pptx` |
| 3056 | 1200, 1230, 1231, 1210 | Pocket U′: 0,85 ±0,03 a MH2.4 / 5,2 / 5,1 (info) / posición 0,2 A/B/C | principal | Alta | `…/3056/4- Metrologia/Interns/V00/3056-00_intern5.xls!DR (1)` fila 125 y siguientes |
| 3056 | 1330, 1310, 1311, 1290 (+ .1 W, .2 V) | Pockets U″, W y V: mismas magnitudes | principal | Alta | Mismo bloque |
| 3202 | 76 | 0,75 0/−0,1 (×3), por vídeo | principal | Alta | Calibre *«GO-NO GO POCKETS»*: `…/3202/6- Método de medición/3202_00_MM_V05.pdf` p. 6; p. 12 *«N76 & N79 — JIG G/NG, control of mass production»*; `3202-00_intern.01.xls!DR_100%` fila 69 |
| 3202 | 79.1, 79.2, 79.3 | 3,2 +0,05/−0,15 en tres posiciones, H = −5, por CT | principal | Alta | Ídem; `intern.01` filas 73, 75, 77 |

⚠️ **3056, dos numeraciones con el mismo nivel de plano:** `intern5` e `intern7` declaran nivel 02
(`INTRO!C33`) y la misma cota *«F/17 0,85 Pocket U′ right at MH2.4»* es la **1200** en
`intern5!DR (1)` fila 125 y la **2140** en `intern7!DR (1)` fila 142. `intern10` (nivel 04,
06/03/2024) solo conserva el bloque en `DR (DIF)`, una hoja oculta con resultados `#REF!`.

## 7. Planitudes

| Pieza | Cota | Qué es | Rol | Confianza | Evidencia |
|---|---|---|---|---|---|
| 3168 | 230 | Planitud 0,6 CZ | principal | Alta | Corrección 1.4, `…/3168/5- Retoques molde/20230227-FOT VdB/20230227-Mold correction_1_P3168.pptx` diapositiva 4 (*«Flatness of 0,6 CZ and 0,4»*); H-703 |
| 3168 | 1330 | Planitud 0,4 | principal | Alta | Ídem |
| 3205 | 5 | Planitud 0,1 del plano A | principal | Alta | `3205_00_MM_V05.xls!DIMENSIONS` fila 12 (dos círculos R19 y R24, 25 + 25 puntos). `3205-00_intern.26.xls!DR` fila 20 anota *«10 POINTS ON RIBS»*: esa medición no siguió el método. También interesa en Nervios: A es la cara de los nervios |
| 3206 | 9 | Planitud 0,1 del plano A | principal | Alta | `3206_00_MM_V06.xls!DIMENSIONS` fila 16; `3206-00_intern.02.xls!DR_(100%)` fila 28 |

⚠️ **3206, la Nr.09 del plan del 21/03/2024** (`…/3206/5- Retoques molde/20240320_After new sliders
correction/20240321-Mold correction_new sliders_loop1.pptx`): la diapositiva 4 la usa para
*«compensar planitud»*, la 5 sube la altura de los nervios con la **83** y la 6 vuelve a citar la
**09** con esa misma acción de altura. Probablemente la 6 quería decir 83; pendiente de confirmar.

## 5. Anclajes

Sin piezas: el `Readme.txt` dice que la información *«ya fue entregada anteriormente»* sin decir
dónde (I-501).

---

## Qué cambió respecto a la primera propuesta (18/11/2026)

| Primera propuesta | Corregido | Motivo |
|---|---|---|
| Paredes: 3237 1-1/1-88/1-131, 3238 2/116/104, 3233 480/520 (baja) | 3237/123, 3238/148, 3233/520 (alta) | Las tres se ven como espesor en el plano; 1-1, 1-2 y 480 son radios; el «2» del 3238 era la columna `e_Type` |
| 3206: 19 = R25,6 | 64 = R25,6 | El informe rotula la 64 como *«EDGE OF THE RIB»*; la 19 es un perfil |
| 3214 sin tetones | 6 (Ø pines) + 3, 4, 5, 7 | Corrección 1.1 y croquis |
| 3167 pines: «los únicos rotulados» | Más 470/490/520/540 | Corrección 1.3 |
| 3167: 2730 = pocket 6 | 2730 (pockets 6–13) y 2740 (pockets 1–6 y 8–13) | Subpuntos de `PPAP-3167-00_2` |
| 3206: 20 y 21 ×5; 83 con tolerancia solo inferior | ×7 posiciones; 83 = 0,9 ±0,1 | `intern.02` filas 89–116 y 187–188 |
| 3202: 79 ×4 | 79.1–79.3 (tres posiciones) | `intern.01` |
| 3056: fuente `intern10` | `intern5!DR (1)` | En `intern10` el bloque solo queda en `DR (DIF)` con `#REF!` |
| 2820: ninguna | []252 y []207 candidatas | Plano 2016, leído en imagen |

## Preguntas para INTEPLAST

1. **3206.** El método define N9 como planitud de A. En el plan del 21/03/2024, las diapositivas 4
   y 6 citan N9 y la 5 asigna la altura de los nervios a N83. ¿Qué cota quería citar la 6? En la
   corrección 6.1, ¿confirmáis N64 como el R25,6 que el título atribuye a N19?
2. **3056.** ¿Qué informe y qué hoja tomamos como referencia de los pockets? `intern5` e `intern7`
   declaran nivel 02 con identificadores distintos (1200 frente a 2140). ¿Tenéis la correspondencia?
3. **Paredes.** ¿Qué cota corrigen las acciones de engrosamiento 3237 1.5 y 3238 1.7?
4. **Tetones.** ¿Los pines del 3214 (cota 6) y del 3167 (500) son lo que llamáis tetones?
5. **2820.** ¿Existe el resto del proyecto (A7)? Mientras tanto, ¿[]252 representa el Bolt Eye?
