# `6- Métode de mesura` — cómo se mide cada cota

**1 fichero · 3,45 MB · LOCAL (seguro)**

```
6- Métode de mesura/
└── Measurement_Method_Pump_Housing _012_V01.docx     3,45 MB
```

Documento **del cliente (Robert Bosch)** que define cómo se alinea la pieza y cómo se mide cada
característica. Firmado por **Xavier Arcos, Metrology Manager Inteplast Group** — la "XA" que
responde en `inteplast_resposta_dubtes.md`.

> 🔑 **Es la piedra Rosetta del proyecto.** Sin él, las columnas `GX` / `GN` / `LP(2)` del XLS y
> los bloques del CSV son ilegibles. Leer este documento **antes** que los datos.

---

## Cómo abrirlo

Un `.docx` es un **ZIP**: `word/document.xml` (texto) + `word/media/` (imágenes).

```bash
D=$(mktemp -d)
unzip -o -q -j "…/Measurement_Method_Pump_Housing _012_V01.docx" "word/document.xml" -d "$D"
sed 's/<[^>]*>//g' "$D/document.xml" | tr -s ' \n' ' '
rm -rf "$D"
```

Composición verificada el 2026-08-11:

| | |
|---|---|
| Entradas del ZIP | 87 |
| **Imágenes** | **55** (43 PNG + 8 JPEG) |
| Texto extraíble | **8.348 caracteres** |

> ⚠️ **El 90 % del valor está en las imágenes**, no en el texto: cada cota lleva una captura del
> CAD con la zona y la dirección de medición marcadas. El texto sin las imágenes se entiende
> solo a medias.
>
> **Documento de consulta y transcripción manual, no de ingesta automática.** Es 1 fichero por
> proyecto: no compensa automatizarlo.

---

## 1. Alineación de la pieza — el sistema de referencia

Responde a los **Dubtes 1 y 3**: por qué B1 se usa para alinear y por qué la planitud del plano
A contamina todo lo demás.

| Paso | Palpador | Operación |
|---|---|---|
| **Space-Orientation: A** | N11 | Construir el **plano A** escaneando **dos planos cada 0,1 mm** sobre Ø57 mm y Ø55,5 mm. Orientar el espacio con este plano. |
| **Zero Point: NP/ZP** | N11 | Medir un círculo de **6 puntos** (uno en cada plano), a **H = 16 mm desde A**, punto de inicio 0° en X+. De ese contorno se construye un círculo = **el punto cero**. |
| **Plane-Orientation: NP → B** | N11 | Medir un círculo de **16 puntos** a **H = 2 mm desde A**. Construir una línea desde el punto cero hasta B. |

**Fijación:** mordazas con muelles blandos (*clamps with soft coils*), sobre un útil CMM
específico para la comparación ITP–Bosch.

> 🔑 **Por eso el plano A es crítico.** Es el primero de la cadena: si no es recto, arrastra
> error a la posición de todos los agujeros. Es exactamente lo que INTEPLAST contestó en el
> Dubte 3, y lo que aparece en 5 diapositivas de retoque
> (ver [historial-molde.md](historial-molde.md#8-acoplamientos-entre-cotas)).

### Palpadores

| Ref. | Ø | Longitud | Tipo |
|---|---|---|---|
| N1 | 0,5 mm | 142,0 mm | TP200 (punto a punto) |
| N4 | 2,0 mm | 152,0 mm | TP200 |
| **N10** | **1,5 mm** | **203,65 mm** | SR25 (continuo) — **el del bolt eye** |
| N11 | 1,0 mm | 173,65 mm | SR25 (continuo) — **el de la alineación** |

Palpadores 1–6 = TP200 (punto a punto) · 7–12 = SR25 (continuo/scanning).

---

## 2. Vocabulario de evaluación

Decodifica la columna `type` de la hoja `DR(3D)`:

| Código | Significado |
|---|---|
| **`GX`** | Se evalúa el **diámetro MÍNIMO** del conjunto de puntos |
| **`GN`** | Se evalúa el **diámetro MÁXIMO** del conjunto de puntos |
| **`LP(2)`** | *Local Point (2)* — **distancia directa entre dos puntos opuestos**, a la misma altura. `LP(2) MAX.` / `LP(2) MIN.` según se reporte el mayor o el menor. |
| `MIN.` / `MAX.` | Mínimo / máximo de la nube evaluada |
| `min` / `max` | Idem, en cotas con doble límite |
| `c`, `g`, `h`, `j`, `d`, `b` | Símbolos GD&T: contorno, cilindricidad, oscilación, posición, distancia, perpendicularidad |
| `Ø1`..`Ø4` | Sub-referencia: los **4 bolt eyes** |
| `B1`..`B4` | Los 4 bolts en los bloques de posición |
| `L1`..`L6` | Las 6 **llenties** (N242) |
| `P1`..`Pn` | Puntos locales de espesor (hoja `DR(N165)`) |
| `GG` | Cálculo gaussiano (mínimos cuadrados) — el ajuste por defecto |

**`GX` + `LP(2) MAX.`** = se pide el Ø mínimo *y* la máxima distancia entre puntos opuestos.
Es la forma de detectar a la vez **agujero pequeño** y **ovalización**.

---

## 3. Cómo se mide cada N-number

### 🔑 Feature *Bolt Eye*

| N-number | Cota | Estrategia de medición |
|---|---|---|
| **N117** | Posición **⌖0,15 A/B** | Palpador **N10**. Para cada uno de los 4 cilindros (a 90°): construir un cilindro con **2 círculos, a H = 1,5 y 5 mm, 20 puntos cada uno**, cálculo GG. **La intersección de cada cilindro con el plano A es la posición del agujero.** En serie se usa un **calibre pasa**: pin central Ø3,95 + 4 pins de Ø3,9 **en R31 a 90°**. |
| **N170** | **Ø4 −0,1** (×4) | Palpador **N10**. Círculo de **20 puntos**, cálculo **`GX` (mínimo)** y **`LP` de dos puntos (máximo)**, **a H = 1,5 mm y H = 5,0 mm** en cada posición. *"Report the resulting **8 diameters** properly identified"* → 4 bolts × 2 alturas. En serie: **calibres de pin** (juego de centésimas), criterio pasa / no pasa. |
| **N178** | Planitud **0,10** | Palpador **N11**. Desde la referencia A, evaluar el error de planitud con el **plano de zona mínima**. |

> 📌 **`R31` explica el `31.000` de los bloques `*** POSICIONS X-Z B1/B2/B3 & B4 ***`** del CSV:
> los bolts están a 31 mm del centro, a 90° entre sí. De ahí que los nominales sean
> (31, 0), (0, −31), (−31, 0), (0, 31).

> 📌 **Las dos alturas (H = 1,5 y H = 5,0) responden al Dubte 7**: el cilindro interior es largo
> y lleva **grados de conicidad** para poder expulsar la pieza del molde. El cliente quiere Ø y
> posición arriba y abajo. Lo regula una **nota de ángulo de desmoldeo** del plano, no la
> tolerancia de posición ⌖0,15.

### Otras cotas dimensionales

| N-number | Cota | Estrategia |
|---|---|---|
| N155 | 49,5 ± 0,2 | N04. 20 puntos en 360° (uno cada 18°) sobre Ø13,2. Mínimo y distancia a A en dirección **Y**. |
| N161 | Ø45,4 **+0,12** | N10. Círculo de **60 puntos** a H = 2,3 mm. `GX` (Ø mínimo) + `LP(2)` máximo. |
| N162 | Ø49,89 **−0,12** | N01. Círculo de 60 puntos a H = 2,3 mm. ⚠️ Procedimiento especial: fijar un punto en el suelo a Z = 0, luego palpar cada punto de Ø49,89 a **Z = 0,35**. `GN` (Ø máximo) + `LP(2)` mínimo. |
| N163 | Ø52,79 **+0,12** | N10. Círculo de 60 puntos a **H = 1 mm**. `GX` + `LP(2)` máximo. |
| N165 | 1,35 **−0,05** | N10. Escanear **dos planos cada 0,1 mm** sobre Ø48,5 y Ø46,5. Mín. y máx. Para evaluarlo **localmente**: 4 puntos cada 6° (**60 secciones**) y mín/máx en cada zona. → de ahí el comentario `PUNTS LOCALS` del XLS, la hoja `DR(N165)` y los 60 bloques `POINT n` del CSV. |
| N211 | 60 ± 0,2 | N04. 20 puntos en 360° sobre Ø13,2, con diámetro de referencia previo en Z = 55. Mínimo y distancia a A en dirección **Z**. |
| N236 | 12 **+0,05** | N10. **36 puntos** en 360° (uno cada 10°) en un Ø34 desde el centro. Distancia de todos a A. Mín. y máx. |
| N273 | 13,4 **+0,05** | N10. 36 puntos en 360° (uno cada 10°) en un **Ø7** desde el centro. Mín. y máx. ⚠️ *En el XLS y en el CSV esta cota aparece como `N237`.* |
| N240 | 18,5 **+0,2** | N10. **Un solo punto** centrado en X = 0, Z = 0 en dirección Y+. Distancia a A. |
| N283 | Ø16,3 **−0,3** | N04. **3 círculos** desde arriba, 20 puntos cada uno, a H = −10, −7 y −4 mm. Evaluar la nube como cilindro en `GN` (Ø máximo) + `LP(2)` mínimo. |
| N153 | Cilindricidad 0,15 | N04. Error de cilindricidad **de los 3 círculos de N283**. |
| N127 | Ø16,3 **−0,3** | Idéntico a N283, en la otra tubuladura. |
| N152 | Cilindricidad 0,15 | Error de cilindricidad de los 3 círculos de N127. |

### Acabado superficial (no CMM)

| N-number | Requisito | Parámetros |
|---|---|---|
| N284 | Rz 6,3 µm y Rmax 10 µm | Medir en la dirección indicada |
| N184 | Rz máx. 12 µm | Ambas tubuladuras, geometría interior. `Lt 17,5 / Lc 2,5 / n=5 / λ 0,8` |
| N104 | Rmax 50 µm + **rebabas 0,04 máx.** | Exterior de las tubuladuras. `Lt 17,5 / Lc 2,5 / n=5 / λ 0,8`. Las rebabas de partición se comprueban **visualmente**. |
| N181 | Rz máx. 10 | `Lt 5,6 / Lc 0,8 / n=5 / λ 0,8` |
| N221 | Rz máx. 10 | `Lt 5,6 / Lc 0,8 / n=5 / λ 0,8` |

### Ensayos funcionales

| Pos. | Ensayo | Procedimiento |
|---|---|---|
| **220 / 280** | **Estanqueidad** | Útil con conectores que taponan ambas tubuladuras. Inyectar aire a **5 bar**, sumergir el banco en agua y comprobar que no salen burbujas durante **30 s**. Bosch suministra las juntas tóricas. |
| **N287 / N288** | **Fuerza de inserción del pin** | Pin de **Ø3,992** con una marca, guiado por un casquillo abierto. Presionar a **0,1 mm/s** hasta que la marca quede al nivel del chaflán. Reportar la **fuerza máxima**. Rango: **15N–50N**. |

> 🔑 **N288 es la consecuencia funcional del bolt eye.** Con el agujero a Ø3,43 (`intern.01`) un
> pin de Ø3,992 no entra → ver [historial-molde.md](historial-molde.md).
>
> ⚠️ **Discrepancia sin resolver**: la especificación dice **Ø3,992**, pero las diapositivas de
> corrección dicen *"el pin fa **3,93**"* (corr. 1) y *"el pin fa **3,94**"* (corr. 2).

---

## 4. Condiciones generales impuestas por el cliente

Van al final del documento y son warnings de proceso de medición:

- El método **es solo para correlación**. Hay que hacer un programa de CMM propio para tener
  repetibilidad. Si se usa otra estrategia, **hay que escribirla en rojo** en la descripción
  para que el cliente lo vea.
- Las cotas de forma y posición se evalúan **en la orientación correspondiente**; las no
  marcadas, en la orientación básica.
- Al palpar no debe haber deformación de la pieza.
- **Las piezas de plástico deben reposar 24 h antes de medirse.** Tras medir, guardarlas en
  bolsa **hermética** y **marcarlas con un número o letra**.
- En el envío, protegerlas de golpes y presión externa.

---

## 5. Qué aporta a la base de datos

**Prioridad de ingesta: alta en valor, baja en esfuerzo — pero manual.** Es 1 fichero.

| Aportación | Destino |
|---|---|
| Decodifica `GX` / `GN` / `LP(2)` | Sin esto `DR(3D)` es ilegible. Va a la documentación, no a la BD. |
| Estrategia de medición por N-number | `MEDICION.metodo` o campo descriptivo de la ficha del feature |
| Sistema de referencia A / NP / B | Justifica el **warning de planitud N178** y el acoplamiento entre cotas |
| `R31` | Explica los nominales de los bloques de posición del CSV |
| Calibre pasa, pin de inserción, ensayo de estanqueidad | **`WARNING` con consecuencia funcional** — convierte una cota fuera de tolerancia en un problema real y explicable, que es justo lo que debe mostrar la ficha del feature |
| N170 y N117 salen de la misma medición | Justifica agruparlos en el feature *Bolt Eye* |
