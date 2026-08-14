# `8- STL peça real` — escaneado 3D de una pieza real

**1 fichero · 235,7 MB · LOCAL (hidratado y legible)**

```
8- STL peça real/
└── 3212-315346-c13.stl        247.145.084 bytes
```

Es el **único fichero grande del proyecto que se puede leer de verdad**: el `.step` del molde
está en la nube y el `.mfr` está cifrado. Este es una malla de triángulos abierta y estándar.

---

## El nombre codifica tres cosas

```
3212 - 315346 - c13
  │       │      └── CAVIDAD 13
  │       └───────── LOTE 315346
  └───────────────── PROYECTO
```

> 🔑 **El lote `315346` es el `Parts batch nº` de `intern.03` (14/03/2024) y de `intern.04`
> (15/04/2024).** Es decir: **la pieza escaneada es posterior a la corrección de molde nº1**.
> Sirve para comparar la geometría real contra el nominal *después* del primer retoque.
>
> (En el 3051 la convención es distinta: `09-12-2024_C1-3051.stl` → `fecha_cavidad-proyecto`.)

---

## Contenido verificado

Cabecera leída el 2026-08-11:

```
bytes 0–79   : "COLOR=" FF FF FF FF 00 00 …      ← cabecera de 80 bytes
bytes 80–83  : 4.942.900                          ← nº de triángulos (uint32 LE)
```

| Dato | Valor |
|---|---|
| Formato | **STL binario** (no ASCII) |
| Cabecera | `COLOR=` + `FFFFFFFF` → convención de **Materialise Magics** (color por defecto) |
| Triángulos | **4.942.900** |
| Tamaño esperado (`84 + 50 × N`) | 247.145.084 bytes |
| Tamaño real | 247.145.084 bytes |
| **Coherencia** | ✅ **exacta** — el fichero no está truncado ni corrupto |

Malla muy densa (~5 M triángulos) → es un escaneado óptico completo, no una teselación de CAD.

---

## Cómo leerlo

**El formato es trivial y está documentado**, a diferencia del `.mfr`:

```
[80 bytes]  cabecera libre
[uint32]    nº de triángulos N
N × 50 bytes:
    [3 × float32]  normal      (nx, ny, nz)
    [3 × float32]  vértice 1   (x, y, z)
    [3 × float32]  vértice 2
    [3 × float32]  vértice 3
    [uint16]       attribute byte count
```

Leer la cabecera es **barato** (84 bytes) y el fichero está hidratado, así que es seguro:

```powershell
$fs = [System.IO.File]::OpenRead($ruta)
$buf = New-Object byte[] 84
[void]$fs.Read($buf, 0, 84)
$fs.Close()
[BitConverter]::ToUInt32($buf, 80)        # nº de triángulos
```

**Procesar la malla completa** (bounding box, secciones, comparación con el CAD) requiere
✅ **Sí se puede procesar aquí** (corregido el 2026-08-13). Hay Python 3.11 en
`C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe` — fuera del PATH, hay
que llamarlo por ruta absoluta — y ya trae **`open3d`, `pyvista`, `vedo`, `pymeshlab`, `libigl`,
`scikit-image` y `numpy`**, que cubren de sobra una malla de 4,9 M triángulos (`numpy-stl` o
`trimesh` no están, pero no hacen falta).

**Visualizar**: cualquier visor de mallas. 5 M de triángulos es pesado pero manejable en
escritorio; **inviable en un navegador sin decimar**.

---

## Por qué importa

Es la entrada natural para el enfoque de **geometría computacional / slicing** descrito en
`inteplast_datos_cad.md`:

- Convertir las reglas de diseño a operaciones sobre la malla (buscar zonas que no las cumplan).
- O convertir el STL a un stack de imágenes binarias por slices y aplicar visión por computador.

Y es la **verificación independiente de la metrología**: la CMM da ~55 cotas puntuales; el STL
da la superficie completa de la misma familia de piezas. Se pueden contrastar.

⚠️ **No es la misma pieza física que se midió en la CMM**, solo el mismo lote. No esperar que
los números coincidan exactamente con `intern.03`.

---

## Qué aporta a la base de datos

| Uso | Viabilidad |
|---|---|
| **Referencia + metadatos** (lote, cavidad, nº triángulos) | ✅ Trivial → `PIEZA_REAL` |
| Descarga desde el frontend | ❌ 236 MB |
| Previsualización 3D en el navegador | ⚠️ Solo con un derivado decimado (glTF) |
| Análisis geométrico automático | ✅ Alto valor y **viable ya**: hay Python 3.11 con `open3d`, `pyvista`, `pymeshlab` y `libigl` |
| **Derivado decimado** (glTF para el navegador) | ✅ `open3d` / `pymeshlab` lo hacen en unas líneas |

Encaja como `PIEZA_REAL (lote, cavidad, escaneado.stl)` colgando de `PROYECTO`, y alimenta la
sección *"piezas de referencia"* del frontend → ver [modelo-datos.md](../modelo-datos.md).

**Prioridad de ingesta: 8** para el análisis geométrico; **1** si solo se guardan los metadatos
(es un único registro).
