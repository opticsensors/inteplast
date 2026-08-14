# `1-2D y 3D Pieza` — definición de la pieza

**2 ficheros · 11,5 MB · ambos LOCAL (seguros de abrir)**

Es la carpeta de la **definición nominal**: qué debe ser la pieza. Todo lo demás en el proyecto
(metrología, retoques) mide desviaciones respecto a esto.

```
1-2D y 3D Pieza/
├── 20250523_DRW 0140S00237_07.pdf              1,42 MB   ← plano 2D del cliente
└── 20200204_3 130 516 987_AllCATPart.stp      10,06 MB   ← sólido 3D de la pieza
```

El prefijo `AAAAMMDD` del nombre es la **fecha de emisión de la revisión**, no la de copia.

---

## 1. El plano 2D — `20250523_DRW 0140S00237_07.pdf`

Es **el documento fuente de todos los N-numbers, las tolerancias GD&T y los warnings**.
De aquí salen `N170 Ø4−0,1`, `N117 ⌖0,15 A/B`, `N178 planitud 0,10`, la nota del ángulo de
desmoldeo y la nota de *"no líneas de soldadura en la zona del agujero"*.

### 🔴 Es un ESCANEO. No tiene texto.

Verificado el 2026-08-11:

```
%PDF-1.7
4 0 obj << /Filter /DCTDecode  /Subtype /Image  /Type /XObject
            /Width 3276  /Height 2317  /ColorSpace /DeviceRGB  /BitsPerComponent 8 >>
...
/Producer (Microsoft: Print To PDF)   /Author (Lucie Vargova)
/CreationDate (D:20250523081437+02'00')   /Title (DRW)
```

| Hecho | Consecuencia |
|---|---|
| **1 sola página**, y su contenido es **una imagen JPEG** (`/DCTDecode`) de 3276 × 2317 px | No hay geometría vectorial que explotar |
| **`/Font` = 0 fuentes** en todo el documento | **No hay capa de texto en absoluto** |
| `pdftotext -layout` devuelve **1 byte** (un salto de línea) | Confirmado empíricamente |
| Producido con *"Microsoft: Print To PDF"* | Alguien imprimió una imagen, no exportó un CAD |

**Resolución efectiva**: 3276 px de ancho. Si el original es A3 → ~198 DPI; si es A2 → ~140 DPI.
Es **poco para OCR fiable de cotas pequeñas** con símbolos GD&T (⌖, Ø, ⊥, marcos de control).

### Cómo leerlo

- **A ojo**: abrirlo en cualquier visor. Es lo que se ha hecho hasta ahora.
- **Extraer la imagen** para OCR o para recortar zonas del feature:
  ```bash
  pdfimages -j "20250523_DRW 0140S00237_07.pdf" plano   # si pdfimages está disponible
  # alternativa: pdftoppm -r 300 -png <pdf> plano
  ```
  *(En este equipo `pdftotext` sí está; `pdfinfo` y `qpdf` no.)*
- **Automáticamente: no se puede.** Ver la pregunta abierta A4 en
  [preguntas-abiertas.md](../preguntas-abiertas.md) — hay que pedir el CATDrawing/DWG nativo o
  un PDF exportado desde el CAD.

### ⚠️ Este plano no es el de los informes

Es la **revisión 07**, emitida el **23/05/2025**. Todos los informes dimensionales —incluido
`intern.09` de abril de 2025— referencian `Drawing nº Level: 06/3E1005491360`.
**El plano que tenemos es posterior a toda la metrología.** No dar por hecho que una cota del
plano coincide con el nominal que aparece en los informes.

---

## 2. El sólido 3D — `20200204_3 130 516 987_AllCATPart.stp`

STEP **AP214**, texto plano ISO-10303-21, 10 MB.

```
FILE_DESCRIPTION(('CATIA V5 STEP Exchange'),'2;1');
FILE_NAME('C:\Users\heb2bue\Desktop\3 130 516 987_AllCATPart.stp',
          '2019-10-18T08:07:34+00:00', ('none'),('none'),
          'CATIA Version 5 Release 19 SP 9 (IN-10)','CATIA V5 STEP AP214','none');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
/* file written by CATIA V5R19 */
#5 = PRODUCT('3 130 516 987_AllCATPart','','',(#2));
```

| Dato | Valor |
|---|---|
| Origen | **CATIA V5R19 SP9**, exportado el **2019-10-18** por el usuario `heb2bue` (Bosch) |
| Esquema | `AUTOMOTIVE_DESIGN` (AP214) |
| `PRODUCT` | `3 130 516 987_AllCATPart` ⚠️ *no coincide con el Part nº `3130517012` de los informes* |
| `ADVANCED_FACE` | 2.670 caras |
| `CYLINDRICAL_SURFACE` | 431 superficies cilíndricas |
| `CARTESIAN_POINT` | 80.467 puntos |
| `CLOSED_SHELL` | 7 |

### 🔴 Es geometría B-Rep pura, sin árbol de features

No hay `Extrusión`, `Taladro`, `Redondeo`, ni parámetros ni cotas: solo caras, aristas y
vértices. **No se puede preguntar al fichero "dónde están los bolt eyes"** — habría que
detectarlos geométricamente (buscar las 431 `CYLINDRICAL_SURFACE`, filtrar radio ≈ 2 mm y
posición en R31 a 90°).

Esta es exactamente la limitación que motiva las propuestas de `inteplast_datos_cad.md`
(macro de SolidWorks para recuperar el árbol, o geometría computacional sobre el STL).

### Cómo leerlo

- **Es texto**: `grep`, `head` y contar entidades funciona directamente y es barato.
  ```bash
  head -c 2000 "…/20200204_3 130 516 987_AllCATPart.stp"
  grep -c CYLINDRICAL_SURFACE "…/…stp"
  ```
- **Visualizar**: cualquier CAD o visor STEP. 10 MB se abre sin problema.
- **Programáticamente**: `pythonocc` / OCCT. ⚠️ Hay Python 3.11 (fuera del PATH, ver
  [CLAUDE.md](../../CLAUDE.md)) pero **OCCT no está instalado**: habría que añadirlo.

---

## Qué aporta esta carpeta a la base de datos

| Dato | Destino en el modelo |
|---|---|
| N-numbers, nominales y tolerancias | `MEDICION.nominal` / `tol+` / `tol−` — **hoy vienen del XLS/CSV, no del plano** |
| Notas del plano (desmoldeo, líneas de soldadura) | `WARNING` del feature |
| Nº de plano y nivel de revisión | `PROYECTO.nº_plano`, `.nivel_plano` |
| El PDF completo | `PROYECTO.FICHEROS.plano_2d` → descargable desde el frontend |
| El STEP | `PROYECTO.FICHEROS.pieza` → descargable; sección *"piezas de referencia"* |

**Prioridad de ingesta: baja.** El plano no es parseable y el STEP no tiene features. Ambos se
guardan como **fichero adjunto descargable**, no como datos estructurados.
