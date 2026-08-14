# `2- Moldflow` — no existe en el 3212

**0 ficheros. La carpeta no está presente en `3212 Pump Housing`.**

Verificado el 2026-08-11: `Test-Path` sobre `…\3212 Pump Housing\2- Moldflow` devuelve `False`.

---

## Por qué existe este documento

Porque **es una trampa recurrente**. El esqueleto de carpetas de INTEPLAST numera de `1-` a
`8-`, y al ver que falta la `2-` la reacción natural es pensar *"falta el estudio de Moldflow"*.

**No falta.** El estudio reológico del 3212 está en **[`7- Moldflow`](7-moldflow.md)**, pesa
184 MB y está ahí desde el principio.

## Situación en los cuatro proyectos

| Proyecto | `2- Moldflow` | `7- Moldflow` |
|---|---|---|
| 2820 | no existe | no existe (proyecto incompleto) |
| 3051 | **existe pero VACÍA** | ✅ `3051_pump housing RB_VDA 12 mm.mfr` (168 MB) |
| 3197 | **existe pero VACÍA** | ✅ `3197 - RB - Pot.mfr` (150 MB) |
| **3212** | **no existe** | ✅ `3212 - Pump Housing.mfr` (184 MB) |

Es decir: la carpeta `2-` es un **resto de una convención antigua** que en unos proyectos quedó
creada y vacía y en otros ni se creó. En ninguno de los cuatro contiene nada.

## Regla para el parser

> Al recorrer el esqueleto de carpetas de un proyecto:
> - **no asumir que las 8 existen**,
> - **no interpretar la ausencia de `2-` como dato faltante**,
> - buscar siempre los estudios reológicos en `7- Moldflow`.

## Qué aporta a la base de datos

Nada. No se ingiere.
