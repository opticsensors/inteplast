# `4- Metrologia` — 🔑 el núcleo de datos

**239 ficheros · 91,5 MB**
`144 pdf · 40 txt · 19 csv · 15 dxf · 12 igs · 9 xls`

Es la carpeta con más valor del proyecto. Contiene **toda la historia de medición del molde**:
9 muestreos entre enero de 2024 y abril de 2025.

> ⚠️ **Hidratación re-verificada el 2026-08-13: 195 de los 239 están EN LA NUBE.**
> El *"todos LOCAL"* de la primera inspección **ya no vale** — OneDrive ha liberado espacio.
> Lo que queda local es justo lo tabular: **los 9 `.xls`**, **los 16 CSV de cavidad**, el
> `3212_totes.csv` de `intern.01` y la carpeta `support intern.01/c13/` entera. Todos los
> `.igs`, todos los `.dxf` salvo uno, casi todos los `.txt` y 142 de los 144 PDF son
> placeholders.
>
> 🔑 **El estado es volátil**: leer un placeholder lo hidrata. La sesión del 2026-08-13 hidrató
> los 12 `PUNTS_NOUS.txt` con solo hashearlos (de 33 locales pasó a 44). **Comprobar siempre el
> atributo `0x400000` antes de abrir algo; no fiarse de ninguna tabla.**
>
> 👉 Práctico: **toda la ingesta tabular (XLS + CSV) se puede hacer hoy sin riesgo.** Lo
> geométrico hay que hidratarlo a propósito — son 1–3 MB por fichero, nada que ver con el STEP
> de 247 MB de `3- 3D Molde`.

Los esquemas exactos de cada formato están en [formatos-parsing.md](../formatos-parsing.md).
Aquí se explica **qué hay, cómo está organizado y cómo leerlo**.

---

## 1. Organización: dos niveles

```
4- Metrologia/
├── 3212-00_intern.01.xls  …  3212-00_intern.09.xls    ← (a) informes consolidados
├── support intern.01/                                  ← (b) salidas crudas de CMM
│   ├── 3212_totes.csv
│   ├── c13/  c14/  c15/  c16/
├── support intern.03/
├── support intern.05/
└── support.intern.08/
```

**`intern.NN` = muestreo**, una tirada de piezas medida en una fecha. La secuencia `01 → 09` es
la **historia de maduración del molde**.

⚠️ **El nombre de las carpetas `support` es inconsistente incluso dentro del mismo proyecto**:
`support intern.01`, `support intern.03`, `support intern.05`, **`support.intern.08`** (con
punto). Normalizar con regex, nunca con match exacto.

### Qué contiene cada muestreo

| Muestreo | Fecha | Lote | Resp. | Motivo del muestreo | Hoja del XLS | `support/` | Datos 3D |
|---|---|---|:--:|---|---|:--:|---|
| `intern.01` | 25/01/2024 | 315252 | DB | — | `DR(3D)` | ✅ | ✅ **completo** (todas las cotas) |
| `intern.02` | **08/02/2024** | **315252** | **MH** | **FOT** · *rougness push in* | *(solo `DR(100%)`)* | ❌ | ❌ |
| `intern.03` | 14/03/2024 | 315346 | DB | *cotes marcades en gris* | `DR(3D)` | ✅ | ⚠️ parcial (N242, N117, N118) |
| `intern.04` | **12/04/2024** ⚠️ | 315346 | KK | **FOT** | *(solo `DR(100%)`)* | ❌ | ❌ |
| `intern.05` | 01/05/2024 | 315426 | DB | *cotes marcades en gris* | `DR(3D)` | ✅ | ⚠️ parcial |
| `intern.06` | **15/05/2024** | **—** | **KK** | ***ICL + water + Push-in*** | *(solo `DR(100%)`)* | ❌ | ❌ |
| `intern.07` | **30/10/2024** ⚠️ | **315714** | **MH** | *Comparation of the technologies KnO x VdB* | `Comparation KnO x VdB` | ❌ | ❌ |
| `intern.08` | **17/01/2025** ⚠️ *(el fichero dice 2024, ver abajo)* | *Batch 08/01/2025* | NV | *Cotes CMM* | `DR` | ✅ | ✅ |
| `intern.09` | 02/04/2025 | *Batch 08/01/2025* | MH | *Sizes Nr.128/134/162 GN evolvation* | `DR` | ❌ | ✅ |

🆕 **Casi todo lo que antes figuraba como `—` sale de la hoja `HISTORY`, no de la cabecera**
(→ [§2](#la-hoja-history-es-un-log-acumulativo--rellena-todos-los-huecos)). Las ⚠️ marcan
**discrepancias entre `HISTORY` y la cabecera del informe**, verificadas el 2026-08-13:

| Muestreo | `HISTORY` | Cabecera `L8` | Comentario |
|---|---|---|---|
| `intern.04` | 12/04/2024 | 15/04/2024 | 3 días de diferencia |
| `intern.07` | 30/10/2024 | 31/10/2024 | 1 día |
| `intern.08` | 17/01/**2024** | 20/01/**2024** | **el año está mal en los dos sitios**: por secuencia (informe 7 = 30/10/2024, lote de 08/01/2025) tiene que ser **2025** |

📌 **El "lote" de `.08`/`.09` no es un error de captura.** El remark de `HISTORY` dice
literalmente `Batch 08/01/2025`: **ese lote se identifica por fecha**, no por número. El valor
de `L9` es fiel al original — lo que hay que hacer es **admitir el tipo fecha en el campo lote**,
no "corregirlo".

> 🔑 **Las 4 carpetas `support` coinciden exactamente con los muestreos que llevaron medición
> 3D real.** Si no hay carpeta `support`, no hubo CMM.

La cronología completa y su relación con los retoques de molde está en
[historial-molde.md](historial-molde.md).

---

## 2. (a) Los informes `.xls` — datos consolidados

`3212-00_intern.NN.xls` · Excel legacy **BIFF8** (OLE) · cp1252 · 0,37–0,72 MB

Plantilla corporativa de 1999 (`Title: PPAP`, `Subject: aCCORDING TO QS9000 /TS`,
`Author: Ferran Colell`, `Last Saved By: David Barneda`).

### Hojas

| Hoja | Contenido | Presente en |
|---|---|---|
| `INTRO` | Cabecera administrativa + selector de idioma | todos |
| `HISTORY` | Historial `INFORME 1..4` con fecha, responsable y nº de lote | todos |
| **`DR(3D)`** | 🔑 tabla de cotas 3D | `.01`, `.03`, `.05` |
| **`DR`** | Igual, pero **fusionada con las filas informativas** de `DR(100%)` | `.08`, `.09` |
| `DR(N165)` | Desglose punto a punto de N165 (espesores locales) | `.01`, `.03` |
| `DR(100%)` | Requisitos informativos del plano (notas, normas, acabados) → OK/NOK | `.01`–`.06` |
| `DR(SKETCH)`, `DR_SKETCH(2)`, `DR_SKETCH(3)` | Croquis anotados | varía |
| `Comparation KnO x VdB` | Comparativa entre dos plantas/laboratorios | solo `.07` |

> **Buscar la hoja por patrón `DR*`, no por nombre exacto.** Cambia entre ficheros.

### Los 9 ficheros, uno por uno

Verificado el 2026-08-13 abriendo los 9 libros con Excel COM:

| Fichero | Hojas | `L8` fecha | `L9` lote | `L10` resp. | Filas hoja `DR*` |
|---|---|---|---|---|--:|
| `3212-00_intern.01.xls` | INTRO · HISTORY · **DR(3D)** · DR(N165) · DR(100%) · DR(SKETCH) · DR_SKETCH(2) · DR_SKETCH(3) | 25/01/2024 | 315252 | ⚠️ `0` | **115** |
| `…intern.02.xls` | INTRO · HISTORY · DR(100%) · DR(SKETCH) | *(vacío)* | *(vacío)* | *(vacío)* | — |
| `…intern.03.xls` | *idem `.01`* | 14/03/2024 | 315346 | ⚠️ `0` | **46** |
| `…intern.04.xls` | INTRO · HISTORY · DR(100%) · DR(SKETCH) | 15/04/2024 | 315346 | Katarína Kopcová | — |
| `…intern.05.xls` | INTRO · HISTORY · **DR(3D)** · DR(100%) · DR(SKETCH) · DR_SKETCH(2) · DR_SKETCH(3) *(sin DR(N165))* | 01/05/2024 | 315426 | DB | **47** |
| `…intern.06.xls` | INTRO · HISTORY · DR(100%) · DR(SKETCH) | *(vacío)* | *(vacío)* | *(vacío)* | — |
| `…intern.07.xls` | INTRO · HISTORY · **Comparation KnO x VdB** · DR(SKETCH) | 31/10/2024 | 315714 | Michal Heidenreich | — |
| `…intern.08.xls` | INTRO · HISTORY · **DR** · DR(SKETCH) | ⚠️ 20/01/2024 | ⚠️ `08/01/2025` | NV | **281** |
| `…intern.09.xls` | INTRO · HISTORY · **DR** · DR(SKETCH) | 02/04/2025 | ⚠️ `08/01/2025` | Michal Heidenreich | **118** |

Las **115 → 46 → 47** filas de `DR(3D)` son la prueba visual de que los informes son parciales
del `.03` en adelante. `.08` tiene 281 porque su hoja `DR` fusiona las filas de `DR(100%)`.

### La cabecera — casi idéntica en los 9, con una excepción

| Celda | Campo | Ejemplo |
|---|---|---|
| `H3` | Nombre pieza | `Pump Housing PAD2 FL` |
| `C5` / `H5` / `L5` | ITP Ref. / Part nº / Part nº Level | `732120000` / `3130517012` / `3E1005491360` |
| `C6` | **PPAP Ref.** | `PPAP-3212-00_int.01` |
| `H6` / `L6` | Nº Plano / **Drawing nº Level** | `0140S00237` / `06/3E1005491360` |
| `L8` | **Report date** | `25/01/2024` |
| `L9` | **Parts batch nº** | `315252` |
| `L10` | Metrology responsible | `DB`, `NV`, `Katarína Kopcová`, `Michal Heidenreich` |

🆕 **La cabecera está replicada en TODAS las hojas del libro**, no solo en `DR*`. Comprobado
leyendo los mismos campos desde `DR(3D)`, `DR(100%)` y `DR(SKETCH)`: dan lo mismo.
→ **Para los metadatos no hace falta localizar la hoja buena**; sirve cualquiera.

⚠️ **Excepciones verificadas — la cabecera no siempre es fiable:**

| Fichero | Problema |
|---|---|
| `intern.06` | 🔴 **Fórmulas rotas**: `H3` y `H6` devuelven `#¡REF!`, y el nº de plano aparece corrido a `L6`. Es el único que rompe la regla "las celdas no se movieron". |
| `intern.02` | `C6` sigue diciendo `PPAP-3212-00_int.01` — copia-pega sin actualizar (el nombre del fichero sí dice `.02`) |
| `intern.01`, `intern.03` | `L10` devuelve `0`, no el responsable. Los de estos dos hay que sacarlos de `HISTORY` (`DB` en ambos) |
| `intern.08`, `intern.09` | `L9` contiene la fecha `08/01/2025` — **no es un error, así se identifica ese lote** (ver §1) |

### La hoja `HISTORY` es un log acumulativo — rellena todos los huecos

🆕 Hallazgo del 2026-08-13. `HISTORY` **no repite la cabecera: acumula una entrada por informe**,
y cada muestreo hereda el historial de los anteriores. Consecuencia directa:

> 🔑 **`intern.09.xls!HISTORY` contiene la cronología completa de los 9 muestreos.**
> Es la mejor fuente de fechas, lotes y responsables del proyecto — mucho mejor que las
> cabeceras, que están incompletas (`.02`, `.06`) o rotas (`.06`).

**Layout** (constante en los 9): fila 6 = cabecera `Date | Engin. Change Level | Document afectat
| Nº Docum/Nº Revisió | Responsable | Remarks`. Después, un rótulo `INFORME n` en la columna A y
**el dato en la fila siguiente**: `A` fecha · `E` responsable · `F` remarks (lote y motivo).

Las filas del rótulo **no son regulares** (7, 12, 17, 22, 25, 28, 31, 34, 37): hay que localizar
`INFORME \d+` por búsqueda en la columna A y leer la fila `+1`, no calcular un salto fijo.

⚠️ En `intern.09` el bloque del noveno informe está rotulado **`INFORME 8` otra vez** (fila 37) —
errata de plantilla. Y ese informe tiene **dos** líneas: `02/04/2025` y `04/04/2025 · Update to
5 pcs`.

Los remarks son la única fuente del **motivo** de cada muestreo: `FOT` (First Off Tool) en el
`.02` y el `.04`, `ICL+water+Push-in` en el `.06`, `Comparation of the technologies KnO x VdB`
en el `.07`, `Sizes Nr.128/134/162 GN evolvation` en el `.09`.

### La tabla `DR(3D)` — cabecera doble en 12–13, datos desde la fila 14

| Col | Campo | Ejemplo |
|:--:|---|---|
| A | **N-number** — ⚠️ solo en la primera fila del grupo, hay que arrastrarlo | `N178`, `N170`, `242` |
| B | `LTR` | `min`, `max`, `1`..`4`, `L1`..`L6`, `X`, `Z`, `A-B` |
| C | `type` | `c`, `g`, `h`, `j`, `d`, `GX`, `GN`, `LP(2) MAX.`, `Ø1`..`Ø4`, `B1`..`B4` |
| D–F | Nominal, Tol +, Tol − | `4`, `0,00`, `-0,10` |
| G | `Equipment` | `CMM`, `INFORMATIVE` |
| H–K | **Valor medido** por cavidad | `Cav.13`, `Cav.14`, `Cav.15`, `Cav.16` |
| L | **NOK** (`X` si fuera de tolerancia) | `X` |
| M | Comentarios | `H= -1.5`, `H= 5`, `PUNTS LOCALS`, `A`, `B` |

### 🔴 El XLS **no** es la fuente de verdad

Dos problemas verificados:

1. **Datos caducados.** El bloque N117/N118 de `intern.05.xls` es copia-pega **idéntica** de
   `intern.03.xls` (`30,996 / 30,999 / 31,008 / 30,979`), mientras el CSV de `intern.05` da
   `31,016`. Alguien duplicó el fichero y no actualizó ese bloque.
   🔴 **Y no es un caso aislado**: `intern.09.xls` (02/04/2025) tiene el bloque **N117 + N118
   copiado de `intern.01`** (25/01/2024) — los **32 valores** (4 bolts + 4 llenties × 4
   cavidades) idénticos 15 meses después — y sus `N275`/`N276` copiados de `intern.08`.
   **`intern.09.xls` es un collage de tres muestreos distintos.**
   → [historial-molde.md §8](historial-molde.md#8-hubo-una-tercera-corrección-de-molde--no)
2. **Informes parciales.** Solo `intern.01` cubre todas las cotas: 115 filas de `DR(3D)` frente a
   46 en `.03` y 47 en `.05`, donde la hoja contiene **solo N242 + N117 + N118**. Mirando
   únicamente los XLS parecería que N170 nunca se volvió a medir. **Sí se midió: está en los
   CSV** — que traen las 211 filas en todos los muestreos
   ([§3](#-los-csv-son-idénticos-en-estructura-entre-los-4-muestreos)).

→ **Usar los CSV para las medidas y el XLS solo para metadatos** (fecha, lote, responsable,
motivo, PPAP ref) y la marca `NOK` consolidada. Y para los metadatos, **`HISTORY` antes que la
cabecera**: está completa y no tiene fórmulas rotas.

### Cómo abrirlo

Lo más cómodo sigue siendo **Excel vía COM desde PowerShell**, siempre en solo lectura
(también valdría `pandas` + `xlrd`, pero el COM lee el `.Text` ya formateado y los colores de
celda):

```powershell
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
$wb = $xl.Workbooks.Open($ruta, 0, $true)        # 0, $true = read-only
foreach ($s in $wb.Worksheets) { $s.Name }        # listar hojas
$ws = $wb.Worksheets.Item("DR(3D)")
$ws.Cells.Item(17,8).Text                         # .Text respeta el formato mostrado
$wb.Close($false); $xl.Quit()
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
```

⚠️ **Cerrar siempre**: si no, quedan procesos `EXCEL.EXE` colgados.
⚠️ Los scripts `.ps1` deben ser **solo ASCII** — PowerShell 5.1 los lee como ANSI y un guion
largo o una `ç` provoca un error de sintaxis.

---

## 3. (b) `support intern.NN/` — salidas crudas de la CMM

Aquí están las **medidas reales**. Estructura del muestreo 01 (los otros varían ligeramente):

```
support intern.01/
├── 3212_totes.csv                    ← comparativa: una columna por cavidad
├── c13/
│   ├── 3212_c13.csv          18 KB   ← 🔑 INFORME DE MEDICIÓN DE LA CAVIDAD
│   ├── 3212_Cav13.txt       600 KB   ← pieza entera escaneada (17.656 pts)
│   ├── 3212_PUNTS.txt       436 KB   ← solo el perfil interior (12.828 pts)
│   ├── 3212_PUNTS_NOUS.txt    5 KB   ← 150 puntos OBJETIVO (6 contornos x 25)
│   ├── 3212_CONTORN.igs     3,3 MB   ← 🔁 duplicado de 3212_PUNTS.txt
│   ├── Perfil_3212_C_c13.dxf 1,5 MB  ← 🔁 duplicado de 3212_Cav13.txt
│   └── PA_1..6.pdf, PB_1..6.pdf      ← 12 gráficas de desviación de contorno
├── c14/  c15/  c16/                  ← idem
```
🔁 = **no ingerir, es el mismo dato que el `.txt`** → [§4](#-el-igs-y-el-dxf-son-duplicados-de-los-txt)

⚠️ **La estructura no es uniforme entre muestreos.** En `intern.03` y `.05` los CSV y los TXT
principales están en la **raíz** de la carpeta `support`, no dentro de `c13/`. En
`support.intern.08` las subcarpetas son `C13/` (mayúscula) y los ficheros llevan el nº de
cavidad **como prefijo** (`13_3212.csv`).

### Inventario real, muestreo por muestreo (2026-08-13)

| | `intern.01` | `intern.03` | `intern.05` | `intern.08` |
|---|---|---|---|---|
| **CSV cavidad** | `c13/3212_c13.csv`<br>`c14/3212c14.csv`<br>`c15/3212c15.csv`<br>`c16/3212c16.csv` | `3212c13..c16.csv`<br>*(raíz)* | `3212_c13..c16.csv`<br>*(raíz)* | `C13/13_3212.csv`<br>… `C16/16_3212.csv` |
| **`totes`** | `3212_totes.csv` | `3212 totes.csv`<br>*(con espacio)* | `3212_totes.csv` | ❌ no hay |
| **Perfil cavidad `.txt`** | `c13/3212_Cav13.txt` … `Cav16` | `3212_C13_.txt` ⚠️<br>`3212_C14..C16.txt`<br>*(raíz)* | `c13/3212_C13.txt`<br>`c14/3212_C14.txt`<br>`c15/3212_Cav_.txt` ⚠️<br>`c16/3212_Cav_.txt` ⚠️ | `C13/13_3212_Cav_.txt` … |
| **`PUNTS` / `PUNTS_NOUS`** | 4 + 4 | 4 + 4 | 4 + 4 | ❌ no hay |
| **`.igs`** | 4 | 4 | 4 | ❌ no hay |
| **`.dxf`** | `Perfil_3212_C_c13.dxf`<br>`Perfil_3212_C14.dxf`<br>`Perfil_3212_C16.dxf`<br>⚠️ **falta c15** | `Perfil_3212_C13..C16.dxf`<br>*(raíz)* | `c13/Perfil_3212_C13.dxf`<br>`c14/Perfil_3212_C14.dxf`<br>`c15/Perfil_3212_C.dxf` ⚠️<br>`c16/Perfil_3212_C.dxf` ⚠️ | `C13/13_Perfil_3212_C.dxf` … |
| **PDF PA/PB** | 48 | 48 | 48 | ❌ no hay |

⚠️ **Falta un fichero**: `support intern.01/c15/` no tiene el `Perfil_*.dxf` que sí tienen c13,
c14 y c16.

🔴 **Colisión de nombres en `intern.05`**: `c15/` y `c16/` llaman a sus ficheros **exactamente
igual** (`3212_Cav_.txt`, `Perfil_3212_C.dxf`). **La cavidad solo está en el nombre de la carpeta
padre.** Si aplanas la estructura al ingerir, se pisan. `intern.08` resolvió el problema poniendo
la cavidad **como prefijo** del nombre.

### El CSV de cavidad — el fichero más importante de todo el proyecto

`;` como delimitador, **cp1252**, export por bloques. Esquema columna a columna en
[formatos-parsing.md](../formatos-parsing.md#1-csv-de-medición-de-cavidad--el-formato-más-importante).

**Contiene ~55 bloques de N-number.** Los del 3212, en orden:

```
N178 planitud · [60 × POINT n → N165 espesor local] · GLOBAL · N165 MIN/MAX
N170 ø4-0.1 & N117 POS 0.15 AT 1/2/3&4
   ├─ N170 BOLT 1/2/3/4  MIN/MAX H=1.5mm   (IDs CMM 11,12,13,14)
   ├─ N170 BOLT 1/2/3/4  MIN/MAX H=5.0mm   (IDs CMM 15,16,17,18)
   └─ N117 POSITION BOLT 1/2/3/4           (IDs CMM 31,32,33,34)
N236 · N237 · N240 · N161 · N163 · N162 · N211 · N283 · N153 · N155 · N127 · N152
N176 · N177 · N219 · N180 · N243 · N275 · N276 · N116/260 & N258
N113 3+0.1 A1..A4  ·  N118 POS 0.15 A1..A4        ← las llenties
N265 · N266 · N232 · N233 · N244 · N277 · N142 · N145
*** POSICIONS X-Z B1/B2/B3 & B4 ***
*** POSICIONS X-Z DIAMETRES 161/162/163 & 233 ***
```

> 📌 **El CSV cubre más cotas que el XLS.** `N275`, `N276`, `N277`, `N244`, `N232`, `N142`,
> `N145`, `N116/260`, `N258`, `N180`, `N219` aparecen en el CSV y **no** en `DR(3D)`.
> Otra razón para ingerir el CSV.

### 🔑 Los CSV son idénticos en estructura entre los 4 muestreos

🆕 Verificado el 2026-08-13 sobre `intern.01/c13`, `intern.01/c14`, `intern.03/c13`,
`intern.05/c13` y `intern.08/C13`:

```
114 cabeceras de bloque · 211 filas de dato · en TODOS
diff de las cabeceras intern.01/c13 ↔ intern.08/C13  →  IDÉNTICAS
```

**El programa de la CMM nunca cambió en 15 meses.** Dos consecuencias fuertes:

1. **Los CSV son comparables fila a fila entre muestreos** sin hacer *matching* difuso: basta
   `cabecera_de_bloque + índice dentro del bloque` (ver
   [formatos-parsing.md](../formatos-parsing.md#receta-cruzar-dos-muestreos)).
2. **Se remidió *todo* en cada muestreo con CMM**, no solo lo que fallaba. La sensación de
   "informe parcial" es **exclusiva del XLS**: 211 mediciones × 4 cavidades × 4 muestreos =
   **3.376 mediciones reales** disponibles. Es el argumento definitivo para ingerir el CSV.

📌 **El bloque de N165 son 60 secciones** (`POINT 1` … `POINT 60`, dos filas cada una: min y
max). Coincide exactamente con el método de medida: *"take these 4 points every 6° (60
sections)"*. Es la materia prima del feature **espesor local**.

### `totes.csv` — la comparativa

Mismo formato pero con **una columna por cavidad** en vez de las columnas de resultado:

```
N178 PLAN. 0.10 MAX.;;;;;;c13;c14;c15;c16
11;Planitud;;0;0.1;0;0.061;0.073;0.079;0.069
      ↑ID    ↑carac.  ↑nom ↑tol+ ↑tol-  ↑ los 4 valores medidos
```

⚠️ **Pierde la desviación, el "fuera de tolerancia" y la barra-semáforo.** Es cómodo para
comparar cavidades de un vistazo, pero **el CSV por cavidad es estrictamente más rico**.
Para ingerir, usar el de cavidad.

### Cómo leer los CSV

```bash
iconv -f cp1252 -t utf-8 "…/support intern.01/c13/3212_c13.csv"

# Cada fila con su cabecera de bloque:
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | awk -F';' '
  /^\*\*\*\*\*\*/ { next }
  $1 !~ /^[0-9]+$/ { hdr=$0; sub(/[; \t]+$/,"",hdr); next }
  { printf "%-46s | %s\n", hdr, $0 }'

# Solo la lista de bloques:
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | grep -v "^[0-9]*;" | grep -v "^\*\*\*\*" | grep -v "^;"
```

---

## 4. Los ficheros de apoyo geométrico

### Los `.txt` son **tres familias distintas**, no una

Formato común: 3 columnas XYZ en **ancho fijo con signo** (`+0000.0392`), sin cabecera, mm, CRLF.
Medido el 2026-08-13 sobre `support intern.01/c13/`:

| Familia | Cuántos | Puntos | Bounding box | Qué es |
|---|:--:|--:|---|---|
| **Perfil de cavidad**<br>`3212_Cav13.txt`, `3212_C13_.txt`, `3212_Cav_.txt`, `13_3212_Cav_.txt` | 16 | **17.656** | X[−33,2; 33,2]<br>Y[0; 49,2]<br>Z[−33,2; 59,9] | **La pieza entera escaneada** |
| **`3212_PUNTS.txt`** | 12 | **12.828** | X[−17,8; 16,9]<br>**Y[12,0; 28,0]**<br>Z[−17,0; 16,6] | **Solo el perfil interior** — la zona que se controla contra tolerancia de contorno |
| **`3212_PUNTS_NOUS.txt`** | 12 | **150** | X[−16,6; 16,6]<br>**Y[12,0; 16,7]**<br>Z[−16,6; 16,6] | 🔑 **6 contornos × 25 puntos** = los puntos **objetivo** que se le pasan al proveedor del molde (respuesta al Dubte 5) |

🆕 **Los `PUNTS_NOUS` son 150 puntos repartidos en 6 alturas**, no una nube suelta: en
`intern.01/c13` están en Y ≈ 16,7 · 16,0 · 14,9 · 13,9 · 12,9 · 12,0, con 25 puntos cada una
(≈ uno cada 14,4°). En `intern.05/c13` las alturas cambian: 16,6 · 15,9 · 14,8 · 13,8 · 12,8 · 12,0.

🔴 **Los 12 `PUNTS_NOUS.txt` son TODOS DISTINTOS** — 12 hashes MD5 distintos, aunque pesen los
mismos 5.100 B (es el ancho fijo: 150 × 34 B). **Hay un objetivo por cavidad y por muestreo**,
no un fichero de referencia replicado. Son **dato ingerible, no un adjunto**.

### 🔴 El `.igs` y el `.dxf` son **duplicados** de los `.txt`

Verificado el 2026-08-13, y cambia la prioridad de ingesta:

| Fichero | Qué contiene realmente |
|---|---|
| `3212_CONTORN.igs` (3,3 MB) | **12.827 entidades IGES tipo 110 (LINE)** = la polilínea que une **los 12.828 puntos de `3212_PUNTS.txt`**. X e Y coinciden punto a punto; **la Z lleva un offset constante de −3,8807 mm** (otro origen en el export). |
| `Perfil_3212_C*.dxf` (1,5 MB) | **Una sola `POLYLINE` con 17.656 `VERTEX`** = exactamente **los 17.656 puntos del `.txt` de perfil de cavidad**. El primer vértice (`−0,01126 / 0,02092 / 27,738`) es literalmente la primera línea de `3212_Cav13.txt`. |

→ **No ingerir ninguno de los dos.** El `.txt` tiene el mismo dato, pesa 2,5× menos y se lee con
`awk` o `pandas`; el `.dxf` además necesitaría instalar `ezdxf`. Conservarlos solo como descarga
para el usuario que quiera abrirlos en un CAD.

**Cabecera del `.igs`** — de aquí sale la **fecha real de medición**:

```
GENERATING SYSTEM   : TRANSPAK
DATE OF CREATION    : 19/01/2024        ← ⚠️ el informe intern.01 declara 25/01/2024
NAME OF CONTOUR     : GEOPAK-WIN SCANNING
sección G: Mitutoyo GmbH · unidades MM · timestamp 240119.105452
```

🆕 **El escaneo es del 19/01/2024 y el informe del 25/01/2024**: la fecha del XLS es la de
emisión del informe, **no la de la medición**. Los PDFs PA/PB lo confirman (`19.01.2024 10:50`).

### Los 144 PDF `PA_1..6` / `PB_1..6` — 🔑 tolerancia de contorno, **fuente única**

12 gráficas × 4 cavidades × 3 muestreos (`.01`, `.03`, `.05`). `intern.08` **no tiene**.

🆕 **No son «dos recorridos partidos en 6 tramos»** (así lo decía esta ficha antes, y era falso).
Verificado el 2026-08-13 con PyMuPDF: son **2 perfiles × 6 contornos medidos**, y los 12 se
comparan **contra el mismo nominal**, `CONTORN (10)`:

| | Elementos medidos | Zona de la pieza |
|---|---|---|
| `PERFIL_A` — `PA_1..6` | contornos **21, 31, 22, 32, 23, 33** | alturas Y ≈ 19–30 mm |
| `PERFIL_B` — `PB_1..6` | contornos **25, 35, 26, 36, 27, 37** | alturas Y ≈ 12–23 mm |

#### 🔴 Por qué son irremplazables

1. **No están en el CSV**: ninguno de los 114 bloques es una tolerancia de contorno. El CSV mide
   cotas *puntuales* — diámetros, posiciones, planitudes, distancias — no perfiles completos.
2. **No se pueden recalcular desde los `.txt`**: la comparación necesita el **contorno nominal**,
   y ese no está en ningún fichero que tengamos. ⚠️ **Trampa**: el `3212_CONTORN.igs` **no es el
   nominal**, es el contorno *escaneado* (su cabecera dice `GEOPAK-WIN SCANNING`). El nominal
   vive dentro del programa de la CMM.

#### Qué se saca de cada PDF

Cabecera común: `Compar. tol. de contorno` · pieza `3212-00 PUMP HOUSING INNER PROFILE` ·
plano `YZ(X)` · `Offset -0.025` · `Nº de pares actual/nominal: 1` ·
`GEOPAK MMC modo repetición in MCOSMOS-3 v4.3`. De `intern.01/c13/PA_1.pdf`:

| Campo | Valor |
|---|---|
| Tolerancia (banda) | `0.0500` → `Tol. Inferior −0,025` / `Tol. Superior +0,025` |
| Max. Desviación inferior / superior | `−0,242` / `−0,038` |
| **Max. Infracción de tolerancia** | **`−0,217`** / `0,000` |
| Desviación media | `0,181` |
| Contorno actual vs nominal | `Contorno (21)` vs `CONTORN (10)` |
| **Hora** | `19.01.2024 10:50` |

→ 144 PDF × 6 valores = **864 mediciones de contorno** que no están en ningún CSV ni XLS.

⚠️ **La tabla del PDF son celdas sueltas**: los bloques de texto de PyMuPDF **no** agrupan las
filas, y `Contorno (21)` sale separado de sus números. Hay que **agrupar las palabras por
coordenada Y**. Receta en
[formatos-parsing.md §4ter](../formatos-parsing.md#4ter-pdf-pa_16--pb_16--tolerancia-de-contorno).

#### 🔑 La prueba de que el retoque enderezó el perfil interior

Extraídos los 144 PDF, la **infracción media de tolerancia** por cavidad:

| Muestreo | c13 | c14 | c15 | c16 | Peor caso |
|---|--:|--:|--:|--:|--:|
| `intern.01` | 0,160 | 0,160 | 0,161 | 0,162 | 0,238 |
| ⚙️ *corrección de molde nº1* | | | | | |
| `intern.03` | **0,029** | **0,034** | **0,027** | **0,026** | 0,052 |
| ⚙️ *corrección de molde nº2* | | | | | |
| `intern.05` | 0,027 | 0,031 | 0,024 | 0,026 | 0,060 |

**La corrección nº1 dividió la desviación del contorno por 5,5**, y lo hizo **en las cuatro
cavidades a la vez** — huella de un cambio en la geometría común del molde, no de un retoque
cavidad a cavidad. La nº2 apenas movió el contorno (0,029 → 0,027): no tocó esta zona.

⚠️ **Matiz honesto: los 12 elementos siguen fuera de tolerancia en los tres muestreos** (12/12 en
todos). La banda es ±0,025 mm y la infracción residual es de 0,01–0,06 mm. El perfil **mejoró
mucho pero nunca llegó a entrar en tolerancia**. Es una evidencia independiente de la del Bolt
Eye, y en un dato que el CSV no contiene.
→ [historial-molde.md](historial-molde.md)

---

## 5. Qué aporta a la base de datos

**Es la carpeta de máxima prioridad de ingesta.**

| Fuente | Nº | Destino | Prioridad |
|---|--:|---|:--:|
| **CSV por cavidad** | 16 | `MEDICION` (n_number, tipo, nominal, tol, valor, desviación, NOK, cavidad, altura_H, id_elemento_cmm) — **3.376 filas** | **1** |
| **`PUNTS_NOUS.txt`** | 12 | 🆕 **Dato, no adjunto**: 150 puntos objetivo × cavidad × muestreo = la evidencia cuantitativa de la acción correctiva | **2** |
| **PDF `PA`/`PB`** | 144 | 🆕 `MEDICION` de tipo contorno: 4 valores × 144 = **576 filas** que no están en ningún CSV | **3** |
| XLS: `HISTORY` | 9 | 🆕 `MUESTREO` (fecha, lote, responsable, **motivo**). **Con `intern.09` solo ya salen los 9** | **4** |
| XLS: cabecera + columna NOK | 9 | `MUESTREO` (ppap_ref, plano, revisión) + validación cruzada del semáforo | 5 |
| `.txt` de perfil y `PUNTS` | 28 | Ficheros adjuntos a `MEDICION` / materia prima de geometría | 6 |
| ~~`totes.csv`~~ | 3 | ❌ **No ingerir**: subconjunto pobre del CSV de cavidad (sin desviación, sin NOK, sin semáforo) | — |
| ~~`.igs`~~ | 12 | ❌ **No ingerir**: 🆕 = `PUNTS.txt` con offset en Z. Solo descarga | — |
| ~~`.dxf`~~ | 15 | ❌ **No ingerir**: 🆕 = `.txt` de perfil. Solo descarga | — |

### 📊 Para ver todo esto hay visores hechos

En vez de leer descripciones, ejecútalos: generan un índice navegable con una página por fichero.
Están en este mismo repo, en `data-explorer/`:

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
$s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\data-explorer"
& $py "$s\ver_csv.py"     # los 16 informes de la CMM + comparativas
& $py "$s\ver_txt.py"     # las 40 nubes de puntos en 3D
```

→ [docs/visores.md](../visores.md)

### 🆕 Dónde vive el N-number — y dónde **no**

El N-number es el *join key* de toda la base de datos, pero **solo existe en tres de los siete
formatos**. Verificado el 2026-08-13:

| Fichero | ¿Nombra las cotas? | Detalle |
|---|:--:|---|
| **CSV de cavidad** | ✅ | **35 N-numbers** en las cabeceras de bloque |
| **XLS** `DR(3D)`/`DR` | ✅ | columna A (⚠️ solo en la primera fila del grupo) |
| **PPTX** de retoques | ✅ | `DIM. Nr.170` en el subtítulo |
| `.txt` (nubes) | ❌ | **cero líneas con una letra** en los 3 ficheros (17.656 / 12.828 / 150 filas, todas numéricas puras) |
| PDF `PA`/`PB` | ❌ | numeración interna propia: `Contorno (21)`, `CONTORN (10)`, `PERFIL_A` |
| `.igs` | ❌ | ningún N-number |
| **Plano 2D** | ⚠️ | los tiene **dibujados sobre la geometría**, pero es una imagen JPEG: 0 caracteres de texto |

🔴 **Consecuencia**: la geometría (`.txt`) y la tolerancia de contorno (PDF) son **anónimas**. No
se puede saber a qué cota pertenece un punto de la nube leyendo el fichero.

**Cómo se puede reconstruir el vínculo**, de más a menos fiable:

1. **El método de medida** (`6- Métode de mesura`) describe cómo se mide cada N-number →
   [6-metodo-medida.md](6-metodo-medida.md). Es la fuente textual.
2. 🆕 **Anclaje geométrico**: cruzar el **nominal del CSV** con la nube. Las 211 filas traen
   nominal, 16 traen la altura (`H=`) y 16 dan coordenadas X-Z explícitas (bloques `POSICIONS`).
   Con eso se localiza el elemento: `N232 Ø4` → 210 puntos a radio 2,0 y `Y≈15,98`; `N170 bolt 1`
   → 20 puntos a `Y=1,5` en (31, 0). **Funciona para las cotas circulares**, pero deja fuera las
   que no están en la nube (N161/N162/N163) y las no circulares.
3. **El plano 2D**, que es el único sitio donde el N-number aparece *junto al punto al que se
   refiere* — pero es un escaneo. → [preguntas-abiertas A4](../preguntas-abiertas.md)
4. Los PDF `PA`/`PB` **no se pueden enlazar** con lo que tenemos.
   → [preguntas-abiertas A9](../preguntas-abiertas.md)

### 🆕 CSV y TXT son **dos exports paralelos**, no uno derivado del otro

Pregunta natural: *¿el CSV se saca del TXT?* **No.** Verificado el 2026-08-13 sobre
`intern.01/c13`:

**Los puntos del TXT sí son los del palpado que generó las cotas.** En `3212_Cav13.txt`, los
puntos del bolt B1 están en **exactamente tres alturas** — `Y=0` (92 puntos, el plano A),
`Y=1,5` (20) e `Y=5,0` (20) — que son justo las que pide el plan de medición. Ajustando un
círculo a esos 20 puntos:

| | Ajuste sobre la nube | CSV |
|---|--:|--:|
| N170 B1 · H=1,5 mm | 3,451 (mín. 3,420 / máx. 3,484) | **3,429** |
| N170 B1 · H=5,0 mm | 3,449 (mín. 3,434 / máx. 3,467) | **3,436** |

El valor del CSV cae dentro del mín/máx de la nube: **mismo palpado**, y la diferencia es la
esperable entre un ajuste rápido por mínimos cuadrados y el algoritmo real de la CMM
(`GX`/`GN`/`LP(2)`, compensación del radio del palpador).

🔴 **Pero el TXT no contiene todos los elementos.** Buscando puntos al radio de cada diámetro
del plano en `3212_Cav13.txt`:

| Cota | Ø | Puntos en la nube |
|---|--:|---|
| N232 | 4,00 | 210 (a `Y≈15,98`) |
| N233 | 7,50 | 178 (a `Y≈13,57`) |
| N127/N283 | 16,30 | 551 (a `Y≈18,6–19,8`) |
| **N161** | 45,40 | 🔴 **0** |
| **N162** | 49,89 | 🔴 **0** |
| **N163** | 52,79 | 🔴 **0** |
| N265 | 59,70 | 51 |
| N266 | 67,10 | 40 |

**N161, N162 y N163 están evaluados en el CSV y no tienen ni un punto en la nube.**
→ **El CSV no se puede regenerar desde el TXT.** Hay que ingerir los dos.

📌 **Cómo se generan.** La medición es **automática**: los PDF llevan la firma
`GEOPAK MMC modo repetición in MCOSMOS-3 v4.3` — el programa de pieza se ejecuta en modo
repetición y emite sus informes (los 12 PDF de una cavidad salen en 4 minutos seguidos).
**El guardado, en cambio, es manual**, y se nota: los nombres son inconsistentes entre cavidades
del *mismo* muestreo (`3212_c13.csv` junto a `3212c14.csv`), las carpetas también
(`support intern.01` / `support.intern.08`), y en `intern.05` dos cavidades conservan el
**nombre por defecto sin rellenar** (`3212_Cav_.txt`). Un pipeline automático no produce eso.

### 🆕 Cada CSV es UNA pieza, no un promedio

`3212c14.csv` son las medidas de **la única pieza que salió del hueco 14** en esa tanda.
Verificado el 2026-08-13 por cuatro vías independientes:

1. Las **12 gráficas PA/PB de una cavidad** están tomadas en una **sesión continua de 4 minutos**
   (`10:50` → `10:54` en `intern.01/c13`). No da tiempo a desmontar y realinear otra pieza.
2. El `3212_CONTORN.igs` de esa misma carpeta lleva el timestamp `240119.105452` = **10:54:52**,
   justo el cierre de esa sesión.
3. El `DR(3D)` del XLS tiene **una sola columna por cavidad** (`Cav.13`…`Cav.16`).
4. `HISTORY` de `intern.09` anota *"Update to 5 pcs"* → hasta ese momento **no** eran 5.

📌 **Los `MIN`/`MAX` no son dos piezas.** Son el valor mínimo y máximo **del mismo elemento en la
misma pieza** — el diámetro más estrecho y el más ancho del mismo agujero, que es como se detecta
si ha salido ovalado. Lo mismo con los 60 `POINT n`: 60 secciones de la misma pieza.

Una fila de CSV ≈ una fila de `MEDICION`. Ver [modelo-datos.md](../modelo-datos.md).
