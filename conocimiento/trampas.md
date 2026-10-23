# Trampas de los datos y recetas de lectura

> Movido desde `CLAUDE.md` el 2026-10-21. Las trampas se descubrieron en el 3212 (`0-bolt-eye/3212/`);
> varias se repiten en los demás features: ver [comparativa.md](comparativa.md) e
> [incongruencias.md](incongruencias.md). Las rutas `docs/…` antiguas ahora están en `conocimiento/`.

### Receta: leer un `.xls` PPAP

```powershell
$xl = New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false
$wb = $xl.Workbooks.Open($ruta, 0, $true)          # 0, $true = read-only
$ws = $wb.Worksheets.Item("DR(3D)")
$ws.Cells.Item($fila,$col).Text
$wb.Close($false); $xl.Quit()                       # SIEMPRE cerrar, deja procesos colgados
```

### Receta: leer un CSV de CMM

```bash
iconv -f cp1252 -t utf-8 "…/3212_c13.csv"
```

### Receta: sacar el texto de un PPTX de corrección

```bash
D=$(mktemp -d); unzip -o -q -j "…/correction.pptx" "ppt/slides/slide*.xml" -d "$D"
for f in $(ls "$D"/slide*.xml | sort -V); do sed 's/<[^>]*>/\n/g' "$f" | grep -v '^\s*$'; done
```
*(No extraer `ppt/media/` salvo que haga falta: tarda minutos.)*

---

## Trampas que ya nos han mordido

1. 🔴 **Priorizar el CSV para medidas CMM coincidentes.** `intern.05.xls` tiene el
   bloque N117/N118 **copiado y pegado de `intern.03`** (valores idénticos), mientras el CSV de
   `intern.05` da valores distintos. Los XLS conservan valor para contexto, otros ensayos y
   previsiones de retoque en `DR(100%)`; registrar las discrepancias por bloque.
2. 🔴 **Solo `intern.01` tiene el XLS completo.** Los XLS posteriores presentan selecciones
   de cotas; eso no significa que la CMM solo remidiera lo que fallaba. Los CSV de cavidad de
   `.01`, `.03`, `.05` y `.08` conservan las 211 filas. N170 sí se volvió a medir.
3. **Error de signo sistemático en el export de la CMM**: bolts B2 y B4, `Posición Z` sale con
   el signo invertido (nominal +31, medido −30,990 ⇒ desviación −61,99). Está en **todos** los
   muestreos. No es una pieza mala.
4. **Errata de plantilla**: el bloque `N170 BOLT 1 MIN/MAX H=5.0 mm` aparece repetido dentro del
   bloque del **BOLT 2**. Fiarse del **ID de elemento CMM** (11–14 = H1,5; 15–18 = H5,0;
   31–34 = posición), no del literal del título.
5. **Nombres inconsistentes** en carpetas y ficheros (`support intern.01`, `Suport_Int_01`,
   `support.intern.08`; `3212_c13.csv`, `3212c14.csv`, `13_3212.csv`). Normalizar con regex,
   nunca con match exacto. ⚠️ Y en `intern.05`, `c15/` y `c16/` llaman a sus ficheros **igual**
   (`3212_Cav_.txt`, `Perfil_3212_C.dxf`): **la cavidad solo está en la carpeta padre.** Derivarla
   de la ruta, nunca del basename.
6. **Multilingüe**: catalán, castellano, inglés y alemán, a veces en el mismo fichero.
   Las acciones de retoque de molde están **en catalán**.
7. **Cavidades no empiezan en 1**: el 3212 usa **c13–c16** (molde de 16, se controlan 4).
8. 🔴 **El plano 2D no tiene texto: es un escaneo.** El PDF es una imagen JPEG de 3276×2317 px
   impresa con *"Microsoft: Print To PDF"*, con **0 fuentes**. `pdftotext` devuelve 1 byte.
   **Ya hay OCR hecho**: `prototypes/data-explorer/planos/ver_plano.py` saca 1.504 palabras (confianza media
   74) y las deja en `out/plano/texto-3212.txt`. Las notas se leen bien; la `Ø` sale como
   `9`/`@`/`$` (`Ø40,3` → `940.3`) y los marcos GD&T son ilegibles.
   🔑 **Los N-numbers están en el plano**, en **globos verdes sin la `N`** (`170`, `170.2`… =
   N170 y sus puntos). Se **localizan** los 178, pero 🔴 **NO se pueden leer**: miden ~9 px.
   Tesseract da basura; **RapidOCR es peor porque acierta solo el 37 % y falla con 0,99 de
   confianza** (auditadas 16 lecturas al azar: 6 buenas; `155` por `156`, `103` por `109`).
   **No volver a intentarlo con este PDF**: la salida es pedir el plano bueno (A4).
9. 🔴 **El plano que tenemos no es el de los informes.** El PDF es la **rev. 07** (23/05/2025);
   todos los informes —hasta `intern.09` de abril de 2025— referencian la **rev. 06**.
10. **La carpeta `2- Moldflow` no existe en el 3212** (en 3051/3197 existe pero está vacía).
    Los estudios están siempre en `7- Moldflow`. No leerlo como dato faltante.
11. **Las hojas del XLS cambian de nombre**: `DR(3D)` en `.01/.03/.05`, `DR` en `.08/.09`,
    ninguna en `.02/.04/.06`. Buscar por patrón `DR*`, no por nombre exacto. Para **metadatos**
    da igual: la cabecera está replicada en todas las hojas del libro.
12. 🔑 **Los metadatos buenos están en la hoja `HISTORY`, no en la cabecera.** Es un log
    **acumulativo**: `intern.09.xls!HISTORY` trae **los 9 muestreos** con fecha, lote,
    responsable y *motivo*, incluidos los que tienen la cabecera vacía (`.02`, `.06`) o rota
    (`.06` da `#¡REF!`). Rótulos `INFORME n` en filas irregulares; hasta 2 filas por informe.
13. 🔴 **Los `.igs` y los `.dxf` son duplicados de los `.txt`**: el `.igs` = `_PUNTS.txt` (con un
    offset constante de −3,8807 en Z), el `.dxf` = `_Cav<NN>.txt` (comprobado el 2026-10-21 en los 15 DXF del 3212: nº de vértices =
    nº de puntos del TXT de su cavidad, de 17.656 a 18.267; `estructura.vertices`). **No ingerirlos** —
    mismo dato, 2,5× más peso.
14. **La fecha del `.xls` es la de emisión del informe, no la de la medición.** El escaneo del
    muestreo 01 es del **19/01/2024** (cabecera del `.igs` y PDFs `PA`/`PB`); el informe declara
    el 25/01/2024.
15. 🔴 **No todo número de un libro es una medida.** Hay celdas con `RAND()`, `RANDBETWEEN` y
    `NORM.INV(RAND(),…)` (648.806 en 191 libros, ninguno del Bolt Eye) y ficheros `#P#` SPC escritos desde ellas.
    El valor guardado en el fichero es el último que calculó Excel; al abrirlo cambia. Antes de usar una
    celda, mirar su fórmula o la tabla `celda_aleatoria`. Ver [incongruencias I-003](incongruencias.md#i-003-en-detalle).
16. **Varias versiones del mismo informe con valores distintos** (`… - Desviacions aplicades.xlsm`,
    `…_old.xlsx`, `Uploaded to IQS/…`). No elegir por nombre ni por fecha de fichero sin comparar: en el
    3167 la versión «aplicada» cambia tolerancias y valores (I-603).
