# Formatos y parsing

> Esquemas exactos, columna a columna, de los tres formatos que hay que ingerir:
> el CSV de la CMM, el XLS PPAP y el PPTX de corrección de molde.
> Dónde vive cada uno → [3212/README.md](3212/README.md).

---

## 1. CSV de medición de cavidad — **el formato más importante**

`support intern.NN/c13/3212_c13.csv` · Delimitador `;` · **Codificación cp1252**

Es un **export plano por secciones**, no una tabla rectangular:

```
****************************************************************      ← separador de bloque
N178 PLAN. 0.10 MAX.                                                  ← CABECERA: N-number + descripción
11;Planitud;;0.000;0.100;0.000;0.061;0.061; ;-----**----              ← FILA DE DATO
```

### Columnas de una fila de dato

| # | Campo | Ejemplo |
|:--:|---|---|
| 1 | **ID de elemento CMM** | `11`, `31`, `201`, `1050` |
| 2 | **Característica (ES)** | `Diámetro`, `Posición`, `Planitud`, `Cilindricidad`, `Redondez`, `Oscilación radial`, `Perpendicularidad`, `Posición X/Y/Z`, `Distancia`, `Cálculo de fórmula` |
| 3 | Característica (DE) o `Variable` | `Durchmesser`, `Rundheit` — **solo en 3197** (bilingüe ES/DE) |
| 4 | **Nominal** | `4.000` |
| 5 | **Tol +** | `0.000` |
| 6 | **Tol −** | `-0.100` |
| 7 | **Medido** | `3.429` |
| 8 | **Desviación** (medido − nominal) | `-0.571` |
| 9 | **Fuera de tolerancia** (vacío si OK) | `-0.471` |
| 10 | Barra ASCII de posición en tolerancia | `<<---+-----` fuera bajo · `-----+--->>` fuera alto · `--****-----` dentro |

**La columna 10 es un semáforo directamente reutilizable: `<<` o `>>` ⇒ NOK.**
Equivalente: columna 9 no vacía ⇒ NOK.

### Bloques especiales (cabecera con `*** … ***`)

```
*** POSICIONS X-Z B1/B2/B3 & B4 ***
31;Posición X;;31.000;0.100;-0.100;31.006;0.006; ;-----*-----
31;Posición Z;;0.000;0.100;-0.100;0.011;0.011; ;-----**----
```

```
*** POSICIONS X-Z DIAMETRES 161/162/163 & 233 ***
201;Posición X;… 202;… 203;… 19;…
```

### 🔑 El ID de elemento CMM es el join key interno

En el 3212 los IDs son **estables entre muestreos** y son lo que enlaza las filas del mismo
bolt entre bloques distintos:

| ID | Qué es |
|---|---|
| `11`, `12`, `13`, `14` | Ø del bolt 1/2/3/4 a **H = 1,5 mm** |
| `15`, `16`, `17`, `18` | Ø del bolt 1/2/3/4 a **H = 5,0 mm** |
| `31`, `32`, `33`, `34` | Posición del bolt 1/2/3/4 (y sus `Posición X` / `Posición Z`) |
| `201`, `202`, `203`, `19` | Posiciones X-Z de los diámetros N161/162/163/233 |

**Fiarse del ID, no del literal de la cabecera** (ver trampa 2 abajo).

### Verificación del cálculo de posición (confirma la respuesta del Dubte 2)

```
31;Posición X;;31.000;…;31.006;0.006     → ΔX = +0,006
31;Posición Z;;0.000;…;0.011;0.011       → ΔZ = +0,011
N117 POSITION BOLT 1
31;Posición;;0.000;0.150;0.000;0.026     → posición = 0,026

2 · √(0,006² + 0,011²) = 2 · 0,01253 = 0,0251 ≈ 0,026  ✅
```

### ⚠️ Trampas del CSV

1. **Error de signo sistemático.** `32;Posición Z;;31.000;…;-30.990;-61.990` → nominal +31,
   medido −30,990 ⇒ desviación −61,99. Afecta a **B2 y B4** y aparece en **todos** los
   muestreos. Es la convención de signo del export, no una pieza mala.
   → Regla de corrección: si `|medido| ≈ |nominal|` pero con signo opuesto, invertir.
2. **Errata de plantilla en las cabeceras.** `N170 BOLT 1 MIN/MAX H=5.0 mm` aparece repetido
   dentro del bloque del **BOLT 2** (copiar-pegar). Presente en los 4 muestreos del 3212.
   → Usar el **ID de elemento CMM**, no el texto de la cabecera.
3. **cp1252**: sin `iconv` salen `C�lculo de f�rmula`.

### Receta

```bash
iconv -f cp1252 -t utf-8 "…/3212_c13.csv"

# Extraer cada fila con su cabecera de bloque:
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | awk -F';' '
  /^\*\*\*\*\*\*/ { next }
  $1 !~ /^[0-9]+$/ { hdr=$0; sub(/[; \t]+$/,"",hdr); next }
  { printf "%-46s | %s\n", hdr, $0 }'
```

⚠️ **Ese `$1 !~ /^[0-9]+$/` como test de cabecera es incorrecto**: muchas filas de dato tienen
**la columna 1 vacía** (`;Cálculo de fórmula;;1.350;…`) y se colarían como cabecera. El test
bueno es **`NF>=8 && $2!=""`** para dato, y cualquier otra línea no vacía (ni `****` ni `////`)
es cabecera.

### 🆕 El export no cambia entre muestreos

Verificado el 2026-08-13 en `intern.01/c13`, `.01/c14`, `.03/c13`, `.05/c13` y `.08/C13`:
**114 cabeceras de bloque y 211 filas de dato en todos**, y el `diff` de las cabeceras entre
`intern.01/c13` e `intern.08/C13` (15 meses después) es **vacío**.

**El programa de la CMM nunca se tocó.** Por eso el emparejamiento por
`cabecera + índice` de la receta siguiente es fiable, y por eso se remidió *todo* en cada
muestreo con CMM: la "parcialidad" de `.03`/`.05` es un artefacto del XLS, no de la medición.

### Receta: cruzar dos muestreos

La clave de emparejamiento es **`cabecera_de_bloque + índice de fila dentro del bloque`**. Los
IDs de elemento CMM no valen solos porque muchas filas los traen vacíos.

```bash
norm() {  # -> bloque|idx|id|caracteristica|nominal|medido|ok/NOK
  iconv -f cp1252 -t utf-8 "$1" | tr -d '\r' | awk -F';' '
    /^\*\*\*\*/ { next }
    /^\/\/\/\// { next }
    NF>=8 && $2 != "" {
      n[hdr]++
      printf "%s|%02d|%s|%s|%s|%s|%s\n", hdr, n[hdr], $1, $2, $4, $7, ($9 ~ /[0-9]/ ? "NOK" : "ok")
      next
    }
    { line=$0; gsub(/[;[:space:]]+$/,"",line); if (line != "") hdr=line }'
}
norm "$A" > /tmp/a; norm "$B" > /tmp/b
awk -F'|' 'NR==FNR{k=$1"|"$2; v[k]=$6; next} {k=$1"|"$2; if(k in v) printf "%-46s %+8.3f\n", $1, $6-v[k]}' /tmp/a /tmp/b
```

📌 **Calibrar siempre antes de concluir.** Un tramo con retoque de molde conocido mueve
**~130 de 211 filas más de 0,10 mm**; un tramo sin retoque no mueve ninguna y su máximo se
queda en ~0,08 mm. Ese es el umbral de discriminación medido en el 3212.
→ [3212/historial-molde.md §8](3212/historial-molde.md#8-hubo-una-tercera-corrección-de-molde--no)

---

## 2. XLS PPAP — informe dimensional interno

`4- Metrologia/<proyecto>-00_intern.NN.xls` · **BIFF8** (OLE) · cp1252

### Hojas

| Hoja | Contenido |
|---|---|
| `INTRO` | Cabecera administrativa + selector de idioma |
| `HISTORY` | Historial (`INFORME 1..4`) con fecha, responsable y nº de lote |
| **`DR(3D)`** | 🔑 **La tabla principal de cotas 3D** |
| `DR(N165)` | Desglose punto a punto de N165 (espesores locales P1…Pn) |
| `DR(100%)` | Requisitos informativos del plano (notas, normas, acabados) → OK/NOK |
| `DR(SKETCH)`, `DR_SKETCH(2)`, `DR_SKETCH(3)` | Croquis anotados |

⚠️ **Las hojas varían entre ficheros.** En el 3212 solo `intern.01`, `.03`, `.05` tienen
`DR(3D)`; `.08` y `.09` la llaman `DR` (plantilla nueva); `.02`, `.04`, `.06` **no tienen
ninguna** (solo `DR(100%)`); `.07` tiene una hoja `Comparation KnO x VdB`.
→ **Buscar la hoja por patrón (`DR*`), no por nombre exacto.**

### Cabecera del informe

| Celda | Campo | Ejemplo |
|---|---|---|
| `H3` | Nombre pieza | `Pump Housing PAD2 FL` |
| `C5` | ITP Ref. | `732120000` |
| `H5` | Part nº | `3130517012` |
| `L5` | Part nº Level | `3E1005491360` |
| `C6` | **PPAP Ref.** | `PPAP-3212-00_int.01` |
| `H6` | Nº Plano | `0140S00237` |
| `L6` | Drawing nº Level | `06/3E1005491360` |
| `L8` | **Report date** | `25/01/2024` |
| `L9` | **Parts batch nº** | `315252` |
| `L10` | Metrology responsible | `DB`, `Katarína Kopcová` |

✅ **La posición de estas celdas es idéntica en 8 de los 9 ficheros del 3212**, incluidos `.08` y
`.09` — el cambio de plantilla movió el *nombre de la hoja* (`DR(3D)` → `DR`), no la cabecera.

🆕 **La cabecera está replicada en TODAS las hojas del libro**, no solo en `DR*`. Verificado
leyendo los mismos campos desde `DR(3D)`, `DR(100%)` y `DR(SKETCH)`.
→ **Para los metadatos, abrir cualquier hoja; no hace falta localizar la buena.**

⚠️ **Lo que falla es el contenido, no la posición** — cuatro casos verificados en el 3212:

| Fichero | Fallo |
|---|---|
| `intern.06` | 🔴 **La única excepción a la regla de la posición**: `H3` y `H6` devuelven `#¡REF!` (fórmulas rotas) y el nº de plano aparece corrido a `L6` |
| `intern.02` | `C6` dice `PPAP-3212-00_int.01` — copia-pega sin actualizar |
| `intern.01`, `.03` | `L10` (responsable) devuelve `0`; el dato real está en `HISTORY` |
| `intern.08`, `.09` | `L9` contiene la fecha `08/01/2025`. **No es un error de captura**: el remark de `HISTORY` dice literalmente `Batch 08/01/2025` — ese lote se identifica por fecha. **Admitir el tipo, no "corregirlo".** `intern.08` sí tiene mal el **año** del `Report date` (2024 → debería ser 2025) |

**Validar el tipo del dato, no la posición de la celda.**

### 🆕 La hoja `HISTORY` — log acumulativo, la mejor fuente de metadatos

`HISTORY` **no repite la cabecera: acumula una entrada por informe**, y cada muestreo hereda el
historial de los anteriores.

> 🔑 **`intern.09.xls!HISTORY` contiene la cronología completa de los 9 muestreos del 3212.**
> Un solo fichero da fechas, lotes, responsables y **el motivo de cada muestreo** — datos que las
> cabeceras no tienen (`.02` y `.06` las tienen vacías, `.06` además rota).

**Layout** (constante): fila 6 = cabecera
`Date | Engin. Change Level | Document afectat | Nº Docum/Nº Revisió | Responsable | Remarks`.
Luego, un rótulo `INFORME n` en la columna A y **el dato en la fila siguiente**:

| Col | Campo |
|:--:|---|
| `A` | Fecha del informe |
| `E` | Responsable (iniciales: `DB`, `MH`, `KK`, `NV`) |
| `F` | Remarks — **lote y motivo** (`FOT Batch 315252`, `ICL+water+Push-in`, `cotes marcades en gris`) |

⚠️ **Las filas de rótulo no son regulares** (7, 12, 17, 22, 25, 28, 31, 34, 37): buscar
`INFORME \d+` en la columna A y leer la fila `+1`. **No calcular un salto fijo.**

⚠️ En `intern.09` el noveno bloque está rotulado **`INFORME 8` otra vez** (errata), y ese informe
tiene **dos** filas de dato (`02/04/2025` y `04/04/2025 · Update to 5 pcs`). El parser debe
admitir **n filas por informe**, no exactamente una.

⚠️ **`HISTORY` y la cabecera se contradicen** en `.04` (12 vs 15/04/2024), `.07` (30 vs
31/10/2024) y `.08` (17 vs 20/01/2024). Sin criterio para decidir cuál manda: **guardar las dos**
o quedarse con `HISTORY`, que es la que está completa.

### Tabla `DR(3D)` — filas 12–13 cabecera doble, datos desde la fila 14

| Col | Campo | Ejemplo |
|:--:|---|---|
| A | **N-number** (`Nr`) — solo en la primera fila del grupo | `N178`, `N170`, `N117`, `242` |
| B | `LTR` — tipo de dimensión / índice | `min`, `max`, `1`..`4`, `L1`..`L6`, `X`, `Z`, `A-B` |
| C | `type` — tipo de evaluación | `c`, `g`, `h`, `j`, `d`, `GX`, `GN`, `LP(2) MAX.`, `MIN.`, `MAX.`, `Ø1`..`Ø4`, `B1`..`B4` |
| D | **Nominal** | `4` |
| E | **Tol +** | `0,00` |
| F | **Tol −** | `-0,10` |
| G | `Equipment` | `CMM`, `INFORMATIVE` |
| H–K | **Valor medido por cavidad** | `Cav.13`, `Cav.14`, `Cav.15`, `Cav.16` |
| L | **NOK** — `X` si fuera de tolerancia | `X` |
| M | Comentarios | `H= -1.5`, `H= 5`, `PUNTS LOCALS`, `A`, `B` |

⚠️ **La columna A solo lleva el N-number en la primera fila del grupo**; las siguientes van
vacías y heredan. Hay que arrastrar el valor hacia abajo al parsear.

El significado de `GX` / `GN` / `LP(2)` está en
[3212/6-metodo-medida.md](3212/6-metodo-medida.md#2-vocabulario-de-evaluación).

### El XLS no es la fuente de verdad ⚠️

1. **Datos caducados.** El bloque N117/N118 de `intern.05.xls` es copia-pega **idéntica** de
   `intern.03.xls` (`30,996 / 30,999 / 31,008 / 30,979`), mientras el CSV de `intern.05` da
   `31,016`. **El CSV es el correcto.**
2. **Informes parciales.** Solo `intern.01` cubre todas las cotas. Del `.03` en adelante el
   `DR(3D)` solo contiene lo que fallaba (N242 + N117 + N118). Mirando solo los XLS parecería
   que N170 nunca se volvió a medir; sí se midió, está en los CSV.

→ **Prioridad de ingesta: CSV primero, XLS como fuente de metadatos** (fecha, lote, PPAP ref,
responsable) y de la marca `NOK` consolidada.

### Receta (PowerShell + Excel COM)

```powershell
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
$wb = $xl.Workbooks.Open($ruta, 0, $true)                 # read-only
foreach ($s in $wb.Worksheets) { $s.Name }                # listar hojas
$ws = $wb.Worksheets.Item("DR(3D)")
$ws.UsedRange.Rows.Count ; $ws.UsedRange.Columns.Count
$ws.Cells.Item($r,$c).Text                                # .Text respeta el formato mostrado
$wb.Close($false); $xl.Quit()
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
```

`.Interior.ColorIndex` y `.Font.ColorIndex` sirven para detectar marcado manual
(`-4142` = sin relleno, `2` = blanco, `-4105`/`1` = fuente automática/negra).

---

## 3. PPTX de corrección de molde

`5- Retoques de molde/AAAAMMDD-Mold correction_<N>_P<proyecto>_rev<N>.pptx`
Es un **ZIP**: `ppt/slides/slide*.xml` (texto) + `ppt/media/` (imágenes).

### Estructura de una diapositiva — muy regular, parseable

```
Título:    Tool correction nº1 – P3212            24/01/2024        33/37
Constante: Longitud 70mm                                    ← pie fijo, ignorar
Subtítulo: Tool correction 1.33 (DIM. Nr.170)   Ø4-0,1
Bloque 1:  Current situation:      [imagen: informe/CAD con la cota]
Bloque 2:  Tool correction plan:   [imagen: zona marcada en ROJO]
Texto:     <acción correctiva, en CATALÁN, con magnitud en mm>
Marcador:  OK                                               ← estado (solo en algunas)
```

### Campos a extraer

| Campo | Regex / fuente |
|---|---|
| `correccion_nº` | `Tool correction nº(\d+)` del título |
| `proyecto` | `P(\d{4})` del título |
| `fecha` | `(\d{2}/\d{2}/\d{4})` del título |
| `slide_nº` | `Tool correction (\d+)\.(\d+)` |
| `n_numbers` | `DIM\.\s*Nr\.?\s*(\d+)` — **puede haber varios en una diapositiva**. Si sale `XX`/`xx`, **está en la imagen** (trampa 2) |
| `cota_nominal` | El literal tras el subtítulo (`Ø4-0,1`, `27,9±0,1`) |
| `magnitud_mm` | `([\d,\.]+)\s*mm` en el texto de acción |
| `sentido` | `créixer/incrementar el plàstic` = +plástico · `reduir el ferro` = −hierro · `erosionar` · `polir` |
| `estado` | Presencia del marcador `OK` |
| `imagen_zona_roja` | La 2ª imagen de `ppt/media/` referenciada por la diapositiva |
| `es_accion_sobre_datum` | Sin `DIM. Nr.` + varios recortes de informe + zona roja = la brida ⇒ es un retoque de **referencia** (plano A), no de cota |
| `efecto_previsto` | La columna `Retoc`/`Retocs` del recorte del informe: valor propuesto + **resultado simulado por cavidad** |

**Qué imágenes lleva una diapositiva** — `ppt/slides/_rels/slideN.xml.rels`:

```bash
grep -o 'media/image[0-9]*\.png' ppt/slides/_rels/slide15.xml.rels
```

Por tamaño se distinguen sin abrirlas: **< 30 KB** = recorte del informe (la tabla con el
N-number) · **> 80 KB** = recorte del plano 2D o render 3D. Validación de integridad: el
número de `r:embed="rId…"` distintos en `slideN.xml` debe coincidir con el de relaciones de
imagen del `.rels`.

### ⚠️ Trampas del PPTX

1. **El texto viene fragmentado en runs XML.** `sed 's/<[^>]*>/\n/g'` parte palabras:
   `Fer ~ creixre ~ el ~ plastic`. Hay que **reunir los runs** antes de aplicar regex, o
   trabajar con `<a:p>` (párrafo) como unidad.
2. **Diapositivas sin cota identificada**: aparecen literalmente como `DIM. Nr.XX` / `xx`
   (7 en el 3212). **No son inparseables**: el N-number está en la **imagen** del bloque
   *Current situation*, que es un recorte del `DR(3D)` cuya primera columna es la columna `Nr`.
   Hay que leerlas (OCR o a ojo). En el 3212, 6 de las 7 son el retoque del **plano A** —
   una acción sobre una *referencia*, no sobre una cota. → [3212/5-retoques-molde.md §3bis](3212/5-retoques-molde.md#3bis--las-7-diapositivas-sin-cota-son-el-retoque-del-plano-a)
3. **La numeración del pie miente**: la corrección 1 del 3212 declara `n/37` pero solo hay
   **36 diapositivas** (falta la 5/37). ⚠️ Como consecuencia **`slideN.xml` ≠ slide N**: a
   partir de la que falta hay un desfase de 1 (`slide15.xml` = diapositiva **1.16**). En la
   corrección 2 no hay desfase. **Tomar el número del pie (`(\d+)/(\d+)`), no del nombre del
   fichero.**
4. **Ortografía irregular** en catalán (`creixre`/`creixe`/`créixer`, `rondundesa`/`rodunesa`,
   `Corretgir`/`Corregir`). No hacer match exacto sobre los verbos.
5. **Duplicados**: `_rev0` / `_rev1` / `_rev1_`. Quedarse con el `rev` mayor.

### Receta

```bash
D=$(mktemp -d)
unzip -o -q -j "…/20240124-Mold correction_1_P3212_rev1.pptx" "ppt/slides/slide*.xml" -d "$D"
for f in $(ls "$D"/slide*.xml | sort -V); do
  echo "--- $(basename "$f")"
  sed 's/<[^>]*>/\n/g' "$f" | grep -v '^[[:space:]]*$'
done
rm -rf "$D"
```
⚠️ **No extraer `ppt/media/`** salvo que se necesite: son 8–19 MB y tarda minutos.

---

## 4. Nubes de puntos `.txt` — **tres familias distintas**

3 columnas XYZ en **ancho fijo con signo** (`+0000.0392`), sin cabecera, en mm, CRLF.
Trivial de parsear (`awk '{print $1,$2,$3}'`). Cifras medidas en `intern.01/c13`:

| Fichero | Puntos | Bounding box | Qué es |
|---|--:|---|---|
| `_Cav<NN>.txt` / `_C<NN>.txt` / `_Cav_.txt` | **17.656** | X[−33,2; 33,2] Y[0; 49,2] Z[−33,2; 59,9] | La **pieza entera** escaneada |
| `_PUNTS.txt` | **12.828** | X[−17,8; 16,9] **Y[12,0; 28,0]** Z[−17,0; 16,6] | Solo el **perfil interior** (la zona con tolerancia de contorno) |
| `_PUNTS_NOUS.txt` | **150** | X[−16,6; 16,6] **Y[12,0; 16,7]** Z[−16,6; 16,6] | **6 contornos × 25 puntos** = los puntos **objetivo tras corrección** que INTEPLAST le pasa al proveedor del molde (respuesta al Dubte 5) |

🆕 **`_PUNTS_NOUS` tiene estructura, no es una nube suelta**: 150 puntos en **6 alturas Y**
(en `intern.01/c13`: 16,7 · 16,0 · 14,9 · 13,9 · 12,9 · 12,0), 25 puntos por altura ≈ uno cada
14,4°. Las alturas **cambian entre muestreos** (`intern.05/c13`: 16,6 · 15,9 · 14,8 · 13,8 ·
12,8 · 12,0) → no asumirlas fijas; deducirlas agrupando por Y.

🔴 **Los 12 `_PUNTS_NOUS.txt` del 3212 son todos distintos** (12 MD5 distintos pese a pesar los
mismos 5.100 B — es el ancho fijo: 150 × 34 B). **Uno por cavidad y por muestreo.** No es un
fichero de referencia replicado: **es dato ingerible**.

---

## 4bis. 🔴 Los `.igs` y los `.dxf` son **duplicados** de los `.txt`

Verificado en el 3212 el 2026-08-13. Antes de escribir un parser IGES o instalar `ezdxf`:

| Fichero | Contenido real | Equivale a |
|---|---|---|
| `*_CONTORN.igs` (3,3 MB) | **12.827 entidades IGES tipo 110 (LINE)** — una polilínea | **`_PUNTS.txt`** (12.828 puntos). X e Y coinciden punto a punto; la **Z lleva un offset constante de −3,8807 mm** |
| `Perfil_*.dxf` (1,5 MB) | **Una `POLYLINE` con 17.656 `VERTEX`** | **`_Cav<NN>.txt`** (17.656 puntos). El primer vértice es literalmente la primera línea del `.txt` |

→ **No ingerirlos.** Mismo dato, 2,5× más peso, y el `.dxf` obligaría a instalar `ezdxf`.
Conservarlos solo como fichero descargable.

**La cabecera del `.igs` sí es útil** — trae la **fecha real de medición**:

```
GENERATING SYSTEM   : TRANSPAK
DATE OF CREATION    : 19/01/2024        ← el informe intern.01 declara 25/01/2024
NAME OF CONTOUR     : GEOPAK-WIN SCANNING
sección G: Mitutoyo GmbH · unidades MM · timestamp 240119.105452
```

⚠️ **La fecha del XLS es la de emisión del informe, no la de la medición.** Para fechar una
medición, usar el `.igs` o los PDF `PA`/`PB` (`19.01.2024 10:50`), no `L8`.

---

## 4ter. PDF `PA_1..6` / `PB_1..6` — tolerancia de contorno

**Sí tienen texto extraíble** (a diferencia del plano 2D, que es un escaneo). 12 PDF por cavidad
= **2 perfiles × 6 contornos medidos**, todos contra el mismo nominal `CONTORN (10)`:

| | Elementos | Zona |
|---|---|---|
| `PERFIL_A` — `PA_1..6` | contornos **21, 31, 22, 32, 23, 33** | Y ≈ 19–30 mm |
| `PERFIL_B` — `PB_1..6` | contornos **25, 35, 26, 36, 27, 37** | Y ≈ 12–23 mm |

**6 valores por PDF**, en la tabla al pie:

| Campo del PDF | Ejemplo (`intern.01/c13/PA_1.pdf`) |
|---|---|
| `Tolerancia` (banda) / `Tol. Inferior` / `Tol. Superior` | `0.0500` / `−0.025` / `+0.025` |
| `Max. Desviación inferior` / `superior` | `−0.242` / `−0.038` |
| **`Max. Infracción de tol. Inf.` / `sup.`** | **`−0.217`** / `0.000` |
| `Desviación media` | `0.181` |
| `Contorno (N)` vs `CONTORN (10)` | qué se compara contra qué |
| Hora | `19.01.2024 10:50` — **la hora real de medición** |

### ⚠️ La tabla son celdas sueltas: hay que agrupar por coordenada Y

Ni `get_text()` ni `get_text("blocks")` de PyMuPDF juntan `Contorno (21)` con sus tres números:
cada celda es un bloque independiente. **La agrupación por `(bloque, línea)` falla.** Lo que
funciona es reconstruir las filas visuales por la coordenada Y:

```python
import fitz, re

def filas_por_y(pagina, tolerancia=3.0):
    palabras = sorted(pagina.get_text("words"), key=lambda w: (w[1], w[0]))
    filas, actual, y_ref = [], [], None
    for x0, y0, _, _, palabra, *_ in palabras:
        if y_ref is None or abs(y0 - y_ref) <= tolerancia:
            actual.append((x0, palabra)); y_ref = y0 if y_ref is None else y_ref
        else:
            filas.append(sorted(actual)); actual, y_ref = [(x0, palabra)], y0
    filas.append(sorted(actual))
    return [" ".join(p for _, p in f) for f in filas]

# -> 'Contorno (21) -0.025 -0.242 -0.217'
#    'CONTORN (10) 0.025 -0.038 0.000'
#    'YZ(X) 0.181'
```

`pdftotext -layout` también sirve, pero devuelve **cp1252** (`Desviaci�n`) y obliga a un binario
externo. Con PyMuPDF no hace falta ninguna de las dos cosas.

### La curva es vectorial

`PA_1.pdf` tiene **4.509 objetos de dibujo** y su path más largo son **871 segmentos de línea**
dentro del área del gráfico: el perfil de desviación **se puede reconstruir punto a punto**, no
solo los 6 números resumen. Requiere identificar el path por color y mapear coordenadas PDF → mm
con los ticks de los ejes. **No implementado**: primero hay que ver si aporta algo sobre el
resumen.

→ 144 PDF × 6 valores = **864 mediciones de contorno** que **no están en ningún CSV ni XLS**, y
que **no se pueden recalcular** desde las nubes de puntos porque el contorno nominal no lo
tenemos (el `.igs` es el *escaneado*, no el nominal).

---

## 5. Tabla de gotchas consolidada

| # | Problema | Mitigación |
|:--:|---|---|
| 1 | **OneDrive Files On-Demand** | 2,20 GB lógicos vs ~221 MB reales. Leer un placeholder dispara descarga → timeout. Hidratar antes, o procesar solo ficheros pequeños. 🆕 **El estado es volátil**: el 2026-08-13, 195 de los 239 ficheros de `4- Metrologia` estaban en la nube, cuando en agosto estaban todos locales. Y **leer un placeholder lo hidrata** (hashear los 12 `PUNTS_NOUS` pasó el recuento de 33 a 44). **Comprobar el atributo `0x400000` siempre, no fiarse de ninguna tabla.** |
| 2 | **cp1252** en los CSV | `iconv -f cp1252` / `encoding="cp1252"` |
| 3 | **Nombres de carpeta inconsistentes** | `support intern.01` / `Suport_Int_01` / `Support_Inf_04` / `support.intern.08`. Regex, no match exacto. |
| 4 | **Nombres de fichero inconsistentes** | `3212_c13.csv`, `3212c14.csv`, `3212 C1.csv`, `13_3212.csv`. Cavidad con `[cC]\.?\s?_?(\d{1,2})`. |
| 5 | **Cavidades no empiezan en 1** | 3212 → **c13–c16** (molde de 16, se controlan 4). 3197 → C1–C8. 3051 → Cav_1–Cav_4. |
| 6 | **Error de signo CMM** | B2 y B4, `Posición Z`. Invertir si `\|medido\| ≈ \|nominal\|` con signo opuesto. |
| 7 | **Erratas en cabeceras de sección** | Fiarse del ID de elemento CMM. |
| 8 | **`2- Moldflow` vacía** | Los estudios están en `7- Moldflow`. |
| 9 | **Duplicados y comprimidos** | `.rar`/`.zip` redundantes, `Copia de Copia de …`, `_rev0/_rev1/_rev1_`. Deduplicar antes de ingerir. |
| 10 | **Multilingüismo** | Catalán, castellano, inglés y alemán, a veces en el mismo fichero. El frontend debe asumirlo. |
| 11 | **Planos 2D sin texto extraíble** | `pdftotext` vacío. Hidratar y reintentar; si no, OCR o entrada manual. |
| 12 | **`.mfr` ilegible** | Binario propietario. Requiere Moldflow Communicator + exportación manual de imágenes. |
| 13 | **STEP de molde de 645 MB** | No servible al navegador. Derivado ligero o solo enlace de descarga. |
| 14 | **XLS con datos caducados** | `intern.05.xls` copia el bloque N117/N118 de `intern.03`; **`intern.09.xls` lo copia de `intern.01` (15 meses antes) y sus N275/N276 de `intern.08`**. El CSV manda. |
| 17 | **Detectar copia-pega entre informes** | Si un bloque coincide **valor a valor en las 4 cavidades** con un muestreo anterior, es copia. Regla de ingesta: hashear el bloque por muestreo y marcar `sospecha_de_copia` cuando el hash se repita. |
| 15 | **Informes XLS parciales** | Solo `intern.01` es completo. |
| 16 | **Hojas del XLS variables** | `DR(3D)` / `DR` / ninguna. Buscar por patrón `DR*`. 🆕 Para **metadatos** da igual: la cabecera está replicada en todas las hojas. |
| 18 | 🆕 **`.igs` y `.dxf` son duplicados de los `.txt`** | El `.igs` = `_PUNTS.txt` (con offset Z −3,8807); el `.dxf` = `_Cav<NN>.txt`. No ingerirlos: mismo dato y 2,5× más peso. → [§4bis](#4bis--los-igs-y-los-dxf-son-duplicados-de-los-txt) |
| 19 | 🆕 **Los metadatos buenos están en `HISTORY`, no en la cabecera** | Es un log **acumulativo**: `intern.09.xls!HISTORY` trae los 9 muestreos con fecha, lote, responsable y **motivo**. Rótulos `INFORME n` en filas irregulares y hasta 2 filas de dato por informe. → [§2](#-la-hoja-history--log-acumulativo-la-mejor-fuente-de-metadatos) |
| 20 | 🆕 **Colisión de nombres al aplanar** | En `intern.05`, `c15/` y `c16/` llaman a sus ficheros **igual** (`3212_Cav_.txt`, `Perfil_3212_C.dxf`): la cavidad **solo está en el nombre de la carpeta padre**. Derivar la cavidad de la ruta completa, nunca del basename. |
| 21 | 🆕 **Fecha del informe ≠ fecha de la medición** | El `.xls` fecha la **emisión** (25/01/2024); el `.igs` y los PDF `PA`/`PB` fechan el **escaneo** (19/01/2024). Para `MEDICION`, usar la del `.igs`/PDF. |
| 22 | 🆕 **`_PUNTS_NOUS.txt` es dato, no adjunto** | Los 12 del 3212 son **todos distintos** (uno por cavidad y muestreo) pese a pesar los mismos 5.100 B. Contienen 6 contornos × 25 puntos objetivo. |
| 23 | 🆕 **El CSV de la CMM no cambia nunca** | 114 bloques y 211 filas **idénticos** en los 4 muestreos del 3212 (`diff` de cabeceras `.01` ↔ `.08` = vacío). Los muestreos son comparables fila a fila; la "parcialidad" es solo del XLS. |

---

## 6. Comandos útiles

```bash
cd "C:/Users/eduard.almar/OneDrive - EURECAT/Escritorio/proyectos/11. inteplast/Exemples"

# Inventario por extensión
find . -type f | sed 's/.*\.//' | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn

# Tamaños lógicos por proyecto (¡no usar du: OneDrive miente!)
for d in */; do find "$d" -type f -printf "%s\n" \
  | awk -v d="$d" '{s+=$1;n++} END {printf "%-24s %7.1f MB (%d f)\n",d,s/1048576,n}'; done

# Solo las cabeceras de sección (N-numbers) de un CSV
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | grep -v "^[0-9]*;" | grep -v "^\*\*\*\*"
```
