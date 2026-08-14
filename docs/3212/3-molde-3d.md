# `3- 3D Molde` — geometría del molde

**1 fichero · 246,7 MB · 🔴 EN LA NUBE (no hidratado)**

```
3- 3D Molde/
└── 3212.step        246,72 MB   ← ensamblaje COMPLETO del molde
```

---

## 🔴 Antes de tocarlo: está en la nube

Comprobado el 2026-08-11: el fichero tiene el atributo `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`
(`0x400000`). Es un **placeholder de OneDrive Files On-Demand**.

> **Leer un solo byte dispara la descarga de los 247 MB completos.** No hay forma de leer solo
> la cabecera. Cualquier `head`, `grep` o `Get-Content` sobre él bloqueará la sesión varios
> minutos o dará timeout.

```powershell
# Comprobación obligatoria antes de abrirlo:
$a = [int](Get-Item -LiteralPath "…\3- 3D Molde\3212.step").Attributes
if ($a -band 0x400000) { "EN LA NUBE - no leer" } else { "LOCAL - seguro" }
```

Si de verdad hace falta: hidratarlo desde el Explorador (clic derecho → *Conservar siempre en
este dispositivo*), esperar a que baje, y entonces leerlo.

**Por eso su contenido no está verificado**, a diferencia del resto de carpetas de este
proyecto. Lo que sigue se infiere del nombre, del tamaño y de los ficheros equivalentes en
3051 y 3197.

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

Formato esperado: STEP AP203/AP214, texto plano ISO-10303-21 — igual que el sólido de la pieza,
pero con miles de `PRODUCT` (uno por componente del ensamblaje).

---

## Por qué importa (aunque no se pueda abrir)

Las acciones correctivas de [`5- Retoques de molde`](5-retoques-molde.md) se aplican **sobre
esta geometría**: *"fer créixer el plàstic Ø0,23 mm en la zona marcada en vermell"* significa
quitar acero de una zona concreta de este ensamblaje.

En particular, la corrección que arregló el Bolt Eye —*"podem utilitzar els **expulsors** de 4
com en els altres motlles"*— es un cambio de componente del molde: los **expulsores** son
piezas de este STEP.

⚠️ **El STEP en disco es el estado actual del molde, no el original.** No sabemos si refleja el
molde antes o después de los retoques de 2024. No hay fecha ni revisión en el nombre.

---

## Qué aporta a la base de datos

| Uso | Viabilidad |
|---|---|
| Descarga directa desde el frontend | ❌ 247 MB es inaceptable para un navegador |
| Previsualización 3D en el navegador | ❌ No sin un derivado ligero |
| **Enlace / referencia al fichero** | ✅ Es lo realista para el prototipo |
| **Derivado ligero** (mallado decimado → glTF) | ⚠️ Posible pero requiere hidratar los 247 MB y procesarlos con OCCT. Hay Python 3.11 con `open3d`/`pymeshlab`, pero **OCCT no está instalado** y hace falta para leer un STEP |
| Extraer geometría de la cavidad | ❌ Fuera de alcance |

**Prioridad de ingesta: la más baja de las 8 carpetas.** Guardar la referencia y punto.

Encaja en el modelo como `PROYECTO.FICHEROS.molde` y alimenta la sección *"moldes CAD"* de
*piezas ejemplo* del frontend → ver [modelo-datos.md](../modelo-datos.md).
