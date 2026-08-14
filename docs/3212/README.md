# 3212 Pump Housing — proyecto piloto

> **Este es el único proyecto sobre el que se trabaja.** Los otros tres (2820, 3051, 3197)
> quedan documentados pero sin tocar → [otros-proyectos.md](../otros-proyectos.md).
>
> **Ruta:** `…\Exemples\3212 Pump Housing`
> **Volumen:** 253 ficheros · 834 MB lógicos
> **Inspección:** 2026-08-07, ampliada y verificada el 2026-08-11

---

## Ficha del proyecto

| Campo | Valor | De dónde sale |
|---|---|---|
| Nº proyecto INTEPLAST | **3212** | Prefijo de casi todos los ficheros |
| Nombre de pieza | `Pump Housing PAD2 FL` | `DR(3D)!H3` |
| ITP Ref. | `732120000` | `DR(3D)!C5` |
| Part nº (Bosch) | `3130517012` | `DR(3D)!H5` |
| Part nº Level | `3E1005491360` | `DR(3D)!L5` |
| Nº Plano | `0140S00237` | `DR(3D)!H8` |
| Drawing nº Level | **`06/3E1005491360`** en *todos* los informes | `DR(3D)!L6` |
| Cliente | Robert Bosch, división BueP | Metadatos de los ficheros |
| Nº de molde | *(no aparece en ningún fichero)* | — |
| Cavidades controladas | **c13, c14, c15, c16** | Cabecera `DR(3D)!H13:K13` |
| Nº total de cavidades del molde | 16 (se controlan 4) | Se deduce de la numeración |
| Material | *(no consta en los datos)* | — |

### ⚠️ Dos incoherencias de identificación (sin resolver)

1. **El plano que tenemos no es el de los informes.** Todos los informes —incluido `intern.09`
   de abril de 2025— dicen `Drawing nº Level: 06/…`, pero el PDF en disco es la **revisión 07**,
   emitida el **23/05/2025**, es decir *posterior a toda la metrología*.
   → **Las cotas del plano que tenemos pueden no coincidir con las medidas.**
2. **El part nº del STEP no coincide con el de los informes.** El sólido se llama
   `3 130 516 987_AllCATPart.stp` y su entidad `PRODUCT` es `3 130 516 987`, pero los informes
   dicen Part nº `3130517012`. Puede ser una revisión anterior o una pieza hermana.

---

## Las carpetas — un `.md` por cada una

| Carpeta | Ficheros | Peso | Qué es | Doc |
|---|--:|--:|---|---|
| `1-2D y 3D Pieza` | 2 | 11,5 MB | Plano 2D + sólido de la pieza | [1-pieza-2d-3d.md](1-pieza-2d-3d.md) |
| `2- Moldflow` | — | — | **No existe en el 3212** | [2-moldflow.md](2-moldflow.md) |
| `3- 3D Molde` | 1 | 246,7 MB | Ensamblaje del molde (STEP) | [3-molde-3d.md](3-molde-3d.md) |
| `4- Metrologia` | **239** | 91,5 MB | 🔑 **El núcleo de datos** | [4-metrologia.md](4-metrologia.md) |
| `5- Retoques de molde` | 8 | 60,9 MB | 🔑 **Lessons learned** | [5-retoques-molde.md](5-retoques-molde.md) |
| `6- Métode de mesura` | 1 | 3,4 MB | Cómo se mide cada cota | [6-metodo-medida.md](6-metodo-medida.md) |
| `7- Moldflow` | 1 | 184,2 MB | Estudio reológico | [7-moldflow.md](7-moldflow.md) |
| `8- STL peça real` | 1 | 235,7 MB | Escaneado 3D de una pieza | [8-stl-pieza-real.md](8-stl-pieza-real.md) |

**Análisis transversal** (cruza `4-` y `5-`): [historial-molde.md](historial-molde.md) — la
cronología muestreo ↔ corrección y la prueba de que el retoque del Bolt Eye funcionó.

> ⚠️ **El esqueleto de 8 carpetas es una convención de INTEPLAST, no una garantía.** En el 3212
> la carpeta `2- Moldflow` sencillamente **no existe** (en 3051 y 3197 existe pero está vacía).
> Los estudios de Moldflow están siempre en `7-`.

---

## Estado de hidratación en OneDrive

> 🔴 **Es volátil: cambió entre el 2026-08-11 y el 2026-08-13.** OneDrive libera espacio por su
> cuenta, así que **esta tabla es una foto, no una garantía**. Comprobar el atributo siempre.

Re-comprobado el **2026-08-13** con `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS` (`0x400000`):

| Carpeta | Ficheros | 🔴 En la nube | 🟢 Local |
|---|--:|--:|--:|
| `1-2D y 3D Pieza` | 2 | 0 | 2 |
| `3- 3D Molde` | 1 | **1** (el STEP de 246,7 MB) | 0 |
| **`4- Metrologia`** | 239 | **195** | 44 |
| `5- Retoques de molde` | 8 | **1** | 7 |
| `6- Métode de mesura` | 1 | 0 | 1 |
| `7- Moldflow` | 1 | 0 | 1 (el `.mfr` de 184 MB) |
| `8- STL peça real` | 1 | 0 | 1 (el `.stl` de 236 MB) |

En `4- Metrologia` lo que queda local es **justo lo tabular** —los 9 `.xls`, los 16 CSV de
cavidad, el `totes.csv` de `intern.01`— más `support intern.01/c13/` entera. Todos los `.igs`,
casi todos los `.dxf` y `.txt` y 142 de los 144 PDF son placeholders.
→ [4-metrologia.md](4-metrologia.md)

⚠️ **Leer un placeholder lo hidrata**: la sesión del 2026-08-13 pasó `4- Metrologia` de 33 a 44
locales solo con hashear los 12 `PUNTS_NOUS.txt` (5 KB cada uno). Para ficheros pequeños es
inofensivo; para el STEP de 247 MB es un timeout.

```powershell
# Comprobar antes de abrir cualquier fichero grande:
$a = [int](Get-Item -LiteralPath $ruta).Attributes
if ($a -band 0x400000) { "EN LA NUBE - no leer" } else { "LOCAL - seguro" }

# Recuento por carpeta:
Get-ChildItem -LiteralPath $r -Recurse -File |
  Group-Object { ($_.FullName.Substring($r.Length+1) -split '\\')[0] } |
  ForEach-Object { "{0,-22} total={1,4} nube={2,4}" -f $_.Name, $_.Count,
    ($_.Group | Where-Object { [int]$_.Attributes -band 0x400000 }).Count }
```

---

## Por dónde empezar si vienes de cero

1. [6-metodo-medida.md](6-metodo-medida.md) — **primero**, porque sin el vocabulario
   (`GX`, `GN`, `LP(2)`) y el sistema de referencia no se entiende ningún dato.
2. [4-metrologia.md](4-metrologia.md) — dónde están las medidas y cómo leerlas.
3. [historial-molde.md](historial-molde.md) — la historia completa del molde y la prueba de
   valor del proyecto.
4. [5-retoques-molde.md](5-retoques-molde.md) — el detalle de las 55 acciones correctivas.

## Nomenclatura de ficheros del 3212

| Patrón | Significado |
|---|---|
| `3212-00_intern.NN.xls` | Informe dimensional del **muestreo NN**. El `-00` es fijo. |
| `PPAP-3212-00_int.NN` | La referencia PPAP que va dentro del informe (nótese `int` vs `intern`) |
| `support intern.NN/` | Salidas crudas de CMM de ese muestreo (nombre **inconsistente**) |
| `3212_c13.csv`, `3212c14.csv`, `13_3212.csv` | Informe CMM de **una cavidad**. Tres grafías distintas. |
| `3212_totes.csv` | *"totes"* = todas (catalán): comparativa con una columna por cavidad |
| `AAAAMMDD-Mold correction_N_P3212_revN.pptx` | Plan de corrección de molde nº N |
| `3212-315346-c13.stl` | `proyecto-LOTE-cavidad` |
