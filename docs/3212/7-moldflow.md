# `7- Moldflow` — estudio reológico

**1 fichero · 184,2 MB · LOCAL (hidratado, pero ilegible)**

```
7- Moldflow/
└── 3212 - Pump Housing.mfr        184,22 MB
```

> ⚠️ La carpeta `2- Moldflow` **no existe** en el 3212. Los estudios están siempre aquí, en la
> `7-`. Ver [2-moldflow.md](2-moldflow.md).

---

## 🔴 No es parseable. Verificado.

`.mfr` = **Moldflow Results**, binario propietario de Autodesk. Los primeros 200 bytes del
fichero, leídos el 2026-08-11:

```
HEX   62 7F 0A 0B 02 50 31 5C 5E 74 71 01 73 7F 06 0C 0B 5C 1D 7B 12 62 18 0D …
ASCII b....P1\^tq.s....\.{.b...e..aab.f...b.3=,1B1%F...q.^U].^pC..vD.21Ap.t…
```

**No hay magic number, ni cabecera legible, ni cadenas de texto.** Los datos están comprimidos
o cifrados desde el byte 0. No hay especificación pública del formato.

→ **Ninguna herramienta genérica puede leerlo.** No intentar.

## Cómo abrirlo

**Moldflow Communicator**, el visor gratuito de Autodesk. Es lo que indicó INTEPLAST
explícitamente en la respuesta al **Dubte 6**:

> *"Dintre de les carpetes dels projectes, n'hi una a cada projecte que posa Moldflow, on hi ha
> els estudis reològics de cada una de les peces. Per veure'ls us heu de baixar un programa que
> es diu Moldflow Communicator, es fàcil de fer anar i podreu veure com es comporta el flux
> quan injectem."*

Comparación entre proyectos:

| Proyecto | Fichero | Tamaño |
|---|---|--:|
| 3051 | `3051_pump housing RB_VDA 12 mm.mfr` | 168 MB |
| 3197 | `3197 - RB - Pot.mfr` | 150 MB |
| **3212** | `3212 - Pump Housing.mfr` | **184 MB** |

---

## Por qué importa: aquí se validan dos warnings del Bolt Eye

De `inteplast_notas_reunion_20_2_2026.md`, dos de los warnings del feature dependen de este
fichero:

1. **Ubicación de los puntos de inyección**
2. **No líneas de soldadura en la zona del agujero** — es una nota del plano 2D, y **la única
   forma de comprobar si se cumple es mirando el patrón de llenado aquí**.

Lo que INTEPLAST explicó (Dubte 6):

- *"Si inyectamos por A y B, la línea de soldadura quedará perpendicular y pasará por agujeros
  ⇒ no es aceptable. Si inyectamos por C y D, no pasará por ningún agujero."*
- **No hay correlación hecha** entre la posición de los puntos de inyección y el error de
  posición de los bolt eyes. *"Lo que sí podemos ver según los estudios de MF es qué solución
  es la mejor."*
- La posición de las líneas de soldadura es *"una combinación de espesores, cambios de sección
  y de cómo es la geometría general de la pieza"*.

### Las 4 variables que definen la restricción de inyección

Según INTEPLAST, un punto de inyección queda definido por:

| Variable | Nota |
|---|---|
| **Número** | Cuántos puntos |
| **Posición** | Dónde |
| **Tipo** | Tipo de inyección |
| **Diámetro** | Ø del punto |

*"De vegades ens vé imposat per client."*

---

## Qué aporta a la base de datos

El `.mfr` **no se puede indexar**. La única vía realista:

| Elemento | Cómo obtenerlo | Destino |
|---|---|---|
| Referencia al fichero | Directo | `PROYECTO.FICHEROS.moldflow` |
| **Imagen del patrón de llenado** | **Exportación manual** desde Moldflow Communicator | `WARNING.imagen` |
| **Imagen de las líneas de soldadura** | **Exportación manual** | `WARNING.imagen` — es la evidencia del warning |
| Puntos de inyección: nº, posición, tipo, Ø | **Entrada manual** | Campos estructurados de `PROYECTO` |

Esto es exactamente la **pregunta abierta A5** en
[preguntas-abiertas.md](../preguntas-abiertas.md): pedir a INTEPLAST que exporte esas dos
imágenes y esos 4 datos por proyecto. Es lo mínimo para materializar el warning de líneas de
soldadura sin depender del `.mfr`.

**Prioridad de ingesta: 8 (la última), y bloqueada** hasta que llegue la exportación manual.

> 💡 **No confundir con `3- 3D Molde`**: aquel es la geometría del molde (247 MB, en la nube);
> este es la simulación del llenado (184 MB, local pero cifrado). Ninguno de los dos se puede
> leer, por motivos distintos.
