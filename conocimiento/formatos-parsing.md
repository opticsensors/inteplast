# Formatos y parsing

> Esquemas del piloto 3212, columna a columna, de tres formatos que hay que ingerir:
> el CSV de la CMM, el XLS PPAP y el PPTX de corrección de molde.
> Dónde vive cada uno → [3212/README.md](0-bolt-eye/3212/README.md).
> No generalizar sus columnas a otras piezas: ver [comparativa.md](comparativa.md).

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
| 3 | Característica (DE) o `Variable` | `Durchmesser`, `Rundheit` en 3197; también hay variantes bilingües fuera de Bolt Eye |
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
   → Corregir solo los elementos conocidos B2/B4 (`32`/`34`, `Posición Z`) cuando
   `|medido| ≈ |nominal|` con signo opuesto. Recalcular desviación, exceso y NOK; conservar los
   valores originales. No aplicar la heurística a otras características sin validarlas.
2. **Errata de plantilla en las cabeceras.** `N170 BOLT 1 MIN/MAX H=5.0 mm` aparece repetido
   dentro del bloque del **BOLT 2** (copiar-pegar). Presente en los 4 muestreos del 3212.
   → Usar el **ID de elemento CMM**, no el texto de la cabecera.
3. **cp1252**: sin `iconv` salen `C�lculo de f�rmula`.

### Receta

```bash
iconv -f cp1252 -t utf-8 "…/3212_c13.csv"

# Extraer cada fila con su cabecera de bloque:
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | awk -F';' '
  /^\*\*\*\*/ || /^\/\/\/\// { next }
  NF>=8 && $2!="" { printf "%-46s | %s\n", hdr, $0; next }
  { line=$0; sub(/[; \t\r]+$/,"",line); if (line!="") hdr=line }'
```

⚠️ **No usar `$1 !~ /^[0-9]+$/` como test de cabecera**: muchas filas de dato tienen
**la columna 1 vacía** (`;Cálculo de fórmula;;1.350;…`). La receta usa **`NF>=8 && $2!=""`**
para detectarlas correctamente.

### 🆕 El export no cambia entre muestreos

Verificado el 2026-08-13 en `intern.01/c13`, `.01/c14`, `.03/c13`, `.05/c13` y `.08/C13`:
**114 cabeceras de bloque y 211 filas de dato en todos**, y el `diff` de las cabeceras entre
`intern.01/c13` e `intern.08/C13` (aproximadamente un año después) es **vacío**.

**Los exports conservan la estructura; eso no acredita que nunca cambiara el programa.** Por eso el emparejamiento por
`cabecera + índice` de la receta siguiente permite comparar los registros, verificando las
cabeceras repetidas. Los CSV conservan todas las filas frente a la selección XLS de `.03`/`.05`;
esa cobertura no prueba por sí sola una nueva adquisición de cada característica.

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
**~130 de 211 filas más de 0,10 mm**; en `.05 → .08` ninguna supera ese umbral y el máximo es
~0,08 mm. **Esto no prueba que ese segundo tramo carezca de retoques**: los hay documentados
de 0,02 y 0,03 mm. El umbral sirve para describir estos tramos, no para cerrar el historial.
→ [3212/historial-molde.md §8](0-bolt-eye/3212/historial-molde.md#8-hubo-una-tercera-corrección-de-molde--pendiente-de-confirmar)

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
| `DR(100%)` | Requisitos, medidas numéricas CMM y con otros equipos, ensayos y OK/NOK |
| `DR(SKETCH)`, `DR_SKETCH(2)`, `DR_SKETCH(3)` | Croquis anotados |

⚠️ **Las hojas varían entre ficheros.** En el 3212 solo `intern.01`, `.03`, `.05` tienen
`DR(3D)`; `.08` y `.09` la llaman `DR` (plantilla nueva); `.02`, `.04`, `.06` **no tienen
esa tabla** (sí `DR(100%)` y croquis); `.07` tiene una hoja `Comparation KnO x VdB`.
→ **Buscar la hoja por patrón (`DR*`), no por nombre exacto.**

### Cabecera del informe

El mapa de celdas, los valores identificativos y las excepciones de los nueve libros se
mantienen en [Metrología: cabecera del informe](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro).
Seleccionar la hoja por contenido, combinar con `HISTORY` y conservar hoja/celda de cada
dato. No imponer el esquema del 3212 a las otras plantillas PPAP.

### 🆕 La hoja `HISTORY` — log acumulativo de metadatos

`HISTORY` **no repite la cabecera: acumula una entrada por informe**, y cada muestreo hereda el
historial de los anteriores.

> 🔑 **`intern.09.xls!HISTORY` contiene entradas de los 9 informes del 3212.**
> Reúne fechas, responsables y remarks (lote o motivo, cuando se consignan). Complementa la
> cabecera de `DR(SKETCH)` y permite contrastar discrepancias entre hojas.

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
31/10/2024) y `.08` (17 vs 20/01/2024). **Guardar ambas fechas con su hoja de origen**.

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
[3212/6-metodo-medida.md](0-bolt-eye/3212/6-metodo-medida.md#2-vocabulario-de-evaluación).

### Discrepancias entre medidas XLS y CSV

1. **Datos caducados.** El bloque N117/N118 de `intern.05.xls` es copia-pega **idéntica** de
   `intern.03.xls` (`30,996 / 30,999 / 31,008 / 30,979`), mientras el CSV de `intern.05` da
   `31,016`. Para esa observación CMM se prioriza el CSV de la tanda, conservando la discrepancia.
2. **Informes parciales.** Solo `intern.01` cubre todas las cotas. Del `.03` en adelante el
   `DR(3D)` de `.03` y `.05` contiene una selección (N242 + N117 + N118), sin que la
   selección demuestre por sí sola qué fallaba. Mirando solo esas hojas parecería
   que N170 nunca se volvió a medir; sí se midió, está en los CSV.

→ **CSV primero para medidas CMM coincidentes.** Los XLS aportan también ensayos y medidas
de otros equipos. En los XLS de retoques, `DR(100%)` incluye O=`Retoc/Retocs`, P:S=previsiones
y H:K=medidas iniciales. Separar previsiones de observaciones y conservar celdas/etapas.
Ejemplo: corrección 2, N240 `P224=H224+$O$224`, `P225=P224+$O$225`.
`xlrd` lee el valor guardado de fórmulas BIFF8; no las recalcula. Para auditar fórmulas usar
Excel sobre una copia temporal en solo lectura. Los mapeos deben comprobar característica, equipo y evaluación;
no propagar un N-number ciegamente a filas de cálculos intermedios.
Ver [revisión 17/09/2026](0-bolt-eye/3212/revision-2026-09-17.md).

### Receta (PowerShell + Excel COM)

Consultar primero las celdas extraídas con `consultar.py celdas`. Para regenerar o auditar
fórmulas, usar las [herramientas de conocimiento](README.md#cómo-se-actualiza), que trabajan
sobre copias cuando necesitan Excel; el lector de valores guardados no recalcula el libro.

Si hace falta inspeccionar formato o colores mediante COM, abrir **una copia temporal**,
con `AutomationSecurity = 3`, `UpdateLinks = 0` y `ReadOnly = true`; cerrar el libro sin
guardar y terminar la instancia propia de Excel en `finally`. Abrir en solo lectura no
impide que Excel recalcule en memoria, por lo que sus resultados no deben sustituir al
valor almacenado en el original.

`.Text` da el texto mostrado; `.Interior.ColorIndex` y `.Font.ColorIndex` permiten detectar
marcado manual (`-4142` = sin relleno, `2` = blanco, `-4105`/`1` = fuente automática/negra).
Mantener los scripts `.ps1` en ASCII según la convención de [CLAUDE.md](../CLAUDE.md).

---

## 3. PPTX de corrección de molde

`5- Retoques de molde/AAAAMMDD-Mold correction_<N>_P<proyecto>_rev<N>.pptx`
Es un **ZIP**: `ppt/slides/slide*.xml` (texto) + `ppt/media/` (imágenes).

**Alcance actual:** el importador utiliza reglas de texto y correspondencias explícitas
revisadas para el piloto 3212, sin interpretación mediante una LLM. La lectura de otras
estructuras sigue pendiente de desarrollo y validación. La decisión entre ampliar
adaptadores, incorporar una LLM con capacidad visual o combinar ambos métodos se recoge
en la [hoja de ruta: generalizar la importación de correcciones PPTX](../docs/hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx).

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
| `marcador_original` | Presencia literal de `OK`; separado de ejecución confirmada y conformidad dimensional |
| `imagen_zona_roja` | Imagen verificada de la diapositiva; no inferir su función solo por orden o tamaño |
| `es_accion_sobre_datum` | Sin `DIM. Nr.` + varios recortes de informe + zona roja = la brida ⇒ es un retoque de **referencia** (plano A), no de cota |
| `efecto_previsto` | `DR(100%)` del Excel de retoques, O y P:S; el recorte PPTX permite contrastar: valor propuesto + **resultado simulado por cavidad** |

**Qué imágenes lleva una diapositiva** — `ppt/slides/_rels/slideN.xml.rels`:

```bash
grep -o 'media/image[0-9]*\.png' ppt/slides/_rels/slide15.xml.rels
```

El tamaño puede orientar la inspección, pero **no identifica la función de una imagen**:
hay que abrirla y comprobar qué representa. Las relaciones de imagen pueden incluir
recursos que no se muestran; comprobar que cada `r:embed` utilizado resuelve a su imagen,
sin exigir igualdad con todas las relaciones de imagen del `.rels`.

### ⚠️ Trampas del PPTX

1. **El texto viene fragmentado en runs XML.** `sed 's/<[^>]*>/\n/g'` parte palabras:
   `Fer ~ creixre ~ el ~ plastic`. Hay que **reunir los runs** antes de aplicar regex, o
   trabajar con `<a:p>` (párrafo) como unidad.
2. **Diapositivas sin cota identificada**: aparecen literalmente como `DIM. Nr.XX` / `xx`
   (7 en el 3212). **No son inparseables**: el N-number está en la **imagen** del bloque
   *Current situation*, que es un recorte del `DR(3D)` cuya primera columna es la columna `Nr`.
   Hay que leerlas (OCR o a ojo). En el 3212, 6 de las 7 son el retoque del **plano A** —
   una acción sobre una *referencia*, no sobre una cota. → [3212/5-retoques-molde.md §3bis](0-bolt-eye/3212/5-retoques-molde.md#3bis--las-7-diapositivas-sin-cota-son-el-retoque-del-plano-a)
3. **La numeración del pie miente**: la corrección 1 del 3212 declara `n/37` pero solo hay
   **36 diapositivas** (falta la 5/37). ⚠️ Como consecuencia **`slideN.xml` ≠ slide N**: a
   partir de la que falta hay un desfase de 1 (`slide15.xml` = diapositiva **1.16**). En la
   corrección 2 no hay desfase. **Tomar el número del pie (`(\d+)/(\d+)`), no del nombre del
   fichero.**
4. **Ortografía irregular** en catalán (`creixre`/`creixe`/`créixer`, `rondundesa`/`rodunesa`,
   `Corretgir`/`Corregir`). No hacer match exacto sobre los verbos.
5. **Versiones**: `_rev0` / `_rev1` / `_rev1_` no son duplicados necesariamente. En la corrección 2
   del 3212, `rev1_` cambia magnitudes de 2.15/2.16 y cuatro marcas `OK` respecto a `rev1` (I-204).
   Comparar contenido y conservar versiones; el sufijo mayor no prueba cuál se ejecutó.

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
| `_PUNTS_NOUS.txt` | **150** | X[−16,6; 16,6] **Y[12,0; 16,7]** Z[−16,6; 16,6] | **6 grupos × 25 puntos**, iguales a los últimos 150 de PUNTS; no consta un objetivo corregido |

**Revisión 17/09/2026:** `np.array_equal(nous, punts[-150:])` da True en los doce pares.
Seis grupos de 25 puntos, con Y ligeramente variable dentro de cada grupo. No se demuestra
que sean nominales ni una transformación de corrección. Los hashes diferentes solo prueban
que los archivos difieren. Conservar origen, muestreo, cavidad y relación de subconjunto;
el vínculo a una acción se debe confirmar. [Detalle](0-bolt-eye/3212/revision-2026-09-17.md).

---

## 4bis. Relación de los `.igs` y `.dxf` con los `.txt`

El contraste de coordenadas, la precisión comprobada y las fechas de adquisición se
mantienen en [Metrología: IGES/DXF/TXT](0-bolt-eye/3212/4-metrologia.md#rectificación-dxf-equivalente-con-redondeo-iges-con-z-aplanada).

**Regla de ingesta:** conservar el IGES como soporte distinto de la nube 3D. Deduplicar
puntos DXF/TXT solo después de verificar equivalencia y mantener el vínculo a ambos
originales. La fecha de la cabecera geométrica no sustituye a la fecha de emisión PPAP.

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

→ 144 PDF = **144 registros de contorno**, con 864 valores en las seis columnas de límites,
desviaciones e infracciones (más media y metadatos cuando estén disponibles). **No están en
ningún CSV ni XLS**, y
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
| 5 | **Cavidades no empiezan en 1** | Conservar los identificadores originales, sin renumerar ni inferir el tamaño del molde. [Evidencia del 3212](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro). |
| 6 | **Error de signo CMM** | B2 y B4, `Posición Z`, IDs `32`/`34`. Invertir si `\|medido\| ≈ \|nominal\|` con signo opuesto, conservando originales y recalculando desviación, exceso y NOK. |
| 7 | **Erratas en cabeceras de sección** | Fiarse del ID de elemento CMM. |
| 8 | **`2- Moldflow` vacía** | Los estudios están en `7- Moldflow`. |
| 9 | **Duplicados y comprimidos** | Deduplicar solo tras comparar contenido. El nombre, la revisión o la presencia de un comprimido no prueban redundancia; el contenido de los archivos comprimidos sigue pendiente de contraste completo. |
| 10 | **Multilingüismo** | Catalán, castellano, inglés y alemán, a veces en el mismo fichero. El frontend debe asumirlo. |
| 11 | **Planos 2D sin texto extraíble** | El plano 3212 es un escaneo confirmado. OCR solo como ayuda visual; números de globo manuales hasta recibir mejor fuente. No confundir el fallo de extracción de un PDF PA/PB con una medición OK. |
| 12 | **`.mfr` ilegible** | Binario propietario. Requiere Moldflow Communicator + exportación manual de imágenes. |
| 13 | **STEP de molde de 645 MB** | No servible al navegador. Derivado ligero o solo enlace de descarga. |
| 14 | **XLS con datos caducados** | `intern.05.xls` copia el bloque N117/N118 de `intern.03`; **`intern.09.xls` lo copia de `intern.01` (15 meses antes) y sus N275/N276 de `intern.08`**. El CSV manda. |
| 17 | **Detectar repetición entre informes** | Si un bloque coincide **valor a valor en las 4 cavidades**, marcar `sospecha_de_copia`. La igualdad prueba repetición de valores, no el mecanismo ni la intención; contrastar lote, fecha y export de la tanda. |
| 15 | **Informes XLS parciales** | Solo `intern.01` es completo. |
| 16 | **Hojas del XLS variables** | `DR(3D)` / `DR` / ninguna. Buscar por patrón `DR*` y validar las etiquetas. `INTRO`, `HISTORY` y las comparativas no comparten necesariamente la cabecera de DR. |
| 18 | **IGES y DXF tienen distinta relación con TXT** | Conservar la geometría y verificar equivalencia antes de deduplicar. → [§4bis](#4bis-relación-de-los-igs-y-dxf-con-los-txt) |
| 19 | 🆕 **Combinar `HISTORY` y `DR(SKETCH)`** | `intern.09.xls!HISTORY` acumula los 9 informes; `DR(SKETCH)` conserva su cabecera incluso en `.02/.06/.07`. En `HISTORY`, E26 está vacío y F29/F32 no indican lote; hay rótulos `INFORME n` en filas irregulares y hasta 2 filas de dato por informe. → [§2](#-la-hoja-history--log-acumulativo-de-metadatos) |
| 20 | 🆕 **Colisión de nombres al aplanar** | En `intern.05`, `c15/` y `c16/` llaman a sus ficheros **igual** (`3212_Cav_.txt`, `Perfil_3212_C.dxf`): la cavidad **solo está en el nombre de la carpeta padre**. Derivar la cavidad de la ruta completa, nunca del basename. |
| 21 | **Fecha del informe ≠ fecha de la medición** | El `.xls` fecha la **emisión** (25/01/2024); el `.igs` y los PDF `PA`/`PB` llevan 19/01/2024. Conservar fecha y fuente, sin trasladar automáticamente la fecha de un perfil a todas las filas CSV. |
| 22 | **`_PUNTS_NOUS.txt` no demuestra un objetivo** | En los doce pares coincide exactamente con los últimos 150 puntos de PUNTS. Conservar como soporte geométrico, sin asignar una acción automáticamente. |
| 23 | **Estructura CSV estable en los exports revisados** | 114 bloques y 211 filas en los 4 muestreos del 3212; las cabeceras coinciden. No demuestra que el programa nunca cambiara. Emparejar evaluación, aparición e ID CMM; la cabecera de B2 H=5 está mal rotulada. |

---

## 6. Comandos útiles

```bash
cd "C:/Users/eduard.almar/OneDrive - EURECAT/Escritorio/proyectos/11. inteplast/Exemples/0- Bolt Eye"

# Inventario por extensión
find . -type f | sed 's/.*\.//' | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn

# Tamaños lógicos por proyecto (¡no usar du: OneDrive miente!)
for d in */; do find "$d" -type f -printf "%s\n" \
  | awk -v d="$d" '{s+=$1;n++} END {printf "%-24s %7.1f MB (%d f)\n",d,s/1048576,n}'; done

# Solo las cabeceras de sección (N-numbers) de un CSV
iconv -f cp1252 -t utf-8 "…/3212_c13.csv" | grep -v "^[0-9]*;" | grep -v "^\*\*\*\*"
```
