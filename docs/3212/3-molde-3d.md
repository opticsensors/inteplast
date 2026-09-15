# `3- 3D Molde` — geometría del molde

**1 fichero · 258.699.834 bytes (246,7 MiB) · hidratado expresamente el 15/09/2026**

```
3- 3D Molde/
└── 3212.step        246,72 MiB  ← ensamblaje del molde
```

---

## Disponibilidad local

El 2026-08-11 y al inicio de la tarea del 15/09 era un placeholder de OneDrive
(`FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`). El 15/09 se solicitó expresamente conservar **solo
este fichero** en el dispositivo, se esperó a su descarga y se comprobó el atributo `0x80420`
antes de leerlo. No se descargaron recursivamente otras carpetas.

> **Si vuelve a quedar solo en la nube**, leerlo puede disparar la descarga completa.
> Comprobar antes los atributos de disponibilidad. Actualmente está descargado y se puede leer.

```powershell
# Comprobación obligatoria antes de abrirlo:
$a = [int](Get-Item -LiteralPath "…\3- 3D Molde\3212.step").Attributes
if ($a -band 0x400000) { "EN LA NUBE - no leer" } else { "LOCAL - seguro" }
```

Si de verdad hace falta: hidratarlo desde el Explorador (clic derecho → *Conservar siempre en
este dispositivo*), esperar a que baje, y entonces leerlo.

Las descripciones funcionales de componentes que siguen proceden de la inferencia inicial
por nombre/tamaño y ficheros equivalentes. La vista web permite ahora inspeccionar la geometría;
no identifica automáticamente la función de cada componente ni la revisión del molde.

---

## Qué es

Es el **ensamblaje completo del molde**, no solo la cavidad: placas, columnas, expulsores,
circuitos de refrigeración, postizos. De ahí los 247 MB.

Comparación entre proyectos:

| Proyecto | Fichero | Tamaño | Alcance |
|---|---|--:|---|
| 3051 | `3051-cela_forma.stp` | 78 MB | *"cela forma"* = celda de forma → **solo el postizo/cavidad** |
| 3197 | `M1176_P-3197 6_05_2025.step` | 645 MB | Ensamblaje completo (`M1176` = nº de molde) |
| **3212** | `3212.step` | **247 MB** | Ensamblaje completo |

⚠️ **El nombre del 3212 no lleva el número de molde.** En el 3197 sí (`M1176`). En todo el
proyecto 3212 no aparece el número de molde en ningún fichero.

**Cabecera y entidades verificadas el 15/09/2026:** STEP con esquema `automotive_design`
(AP214), 5.265 entidades `PRODUCT`, 62.387 `ADVANCED_FACE`, 5.267 `CLOSED_SHELL` y 1.439
`MANIFOLD_SOLID_BREP`. Son recuentos de entidades del fichero, no un inventario auditado de
componentes físicos ni de piezas únicas.

---

## Por qué importa

Las acciones correctivas de [`5- Retoques de molde`](5-retoques-molde.md) se aplican **sobre
esta geometría**: *"fer créixer el plàstic Ø0,23 mm en la zona marcada en vermell"* significa
quitar acero de una zona concreta de este ensamblaje.

En particular, la corrección que arregló el Bolt Eye —*"podem utilitzar els **expulsors** de 4
com en els altres motlles"*— es un cambio de componente del molde: los **expulsores** son
piezas de este STEP.

⚠️ **No conocemos la revisión del STEP en disco.** No sabemos si refleja el
molde antes o después de los retoques de 2024. No hay fecha ni revisión en el nombre.

---

## Qué aporta a la base de datos

| Uso | Viabilidad |
|---|---|
| Descarga desde el frontend | Vinculado al Bolt Eye por referencia local; descarga íntegra del STEP |
| Previsualización 3D en el navegador | GLB generado en el servidor, con caché; el STEP contiene superficies que requieren reparación y la vista puede ser parcial |
| **Enlace / referencia al fichero** | Implementado; original de solo lectura |
| **Derivado ligero** (mallado → GLB) | OCP instalado en Docker; objetivo 500.000 triángulos, máximo 1.000.000 y 25 MiB. [Detalles](../vistas-3d.md) |
| Extraer geometría de la cavidad | ❌ Fuera de alcance |

La visualización está incorporada; la extracción semántica de cavidades y componentes sigue
fuera de esta fase. El aviso **Vista parcial** señala las superficies que el conversor no pudo
representar; no se deben deducir ausencias de componentes a partir de esa vista.

Encaja en el modelo como `PROYECTO.FICHEROS.molde` y alimenta la sección *"moldes CAD"* de
*piezas ejemplo* del frontend → ver [modelo-datos.md](../modelo-datos.md).
