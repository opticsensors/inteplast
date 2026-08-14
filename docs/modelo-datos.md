# Modelo de datos

> Cómo se conecta todo y cómo se traduce a la base de datos.
> Contexto de arquitectura (FastAPI + React + PostgreSQL) → `inteplast_PADIH_fase_B.md`.
> Discusión Neo4j vs PostgreSQL → `inteplast_database.md`.

---

## 1. El N-number es la clave del conocimiento

```
        PLANO 2D (PDF)                 ← define N170 = Ø4 −0,1 y su tolerancia
             │
             ├──► MÉTODO DE MEDIDA (DOCX)   → cómo se mide: 20 pts, GX, H=1,5 y 5 mm
             │
             ├──► INFORME PPAP .xls DR(3D)  → nominal, tol, valor×cavidad, NOK
             │
             ├──► CSV de CMM  "N170 BOLT 1 MIN/MAX H=1.5mm" → medida cruda + desviación
             │
             ├──► PPTX retoque "Tool correction 1.33 (DIM. Nr.170)" → ACCIÓN CORRECTIVA
             │
             └──► FEATURE "Bolt Eye" → warnings + lessons learned
```

**Un feature agrupa varios N-numbers.** Para el Bolt Eye del 3212:

| N-number | Qué mide | Rol en la ficha |
|---|---|---|
| `N170` | Ø4 −0,1, a **H = 1,5 y 5,0 mm** | Cota principal + **warning de conicidad/desmoldeo** |
| `N117` | Posición ⌖0,15 de cada bolt (B1…B4) | Cota metrológica de posición |
| `N178` | Planitud 0,10 del plano A | **Warning indirecto**: A es la referencia de alineación |
| `N288` | Fuerza de inserción del pin (15N–50N) | **Consecuencia funcional** del Ø |
| `N161/162/163/233` | Diámetros y posiciones X-Z de otros círculos | Contexto, mismo bloque de medición |

---

## 2. El mismo feature en otra pieza — 3197 Pot

El Pot tiene la misma geometría con **otro esquema de tolerancia**:

```
N230   ø4 (GX) Hole 1                      → Ø4 +0,1/0   (¡tolerancia INVERSA a la del 3212!)
N220   Position ø0,25 A/C/B ø4 Hole 1      → posición 0,25 con MMC (Ø0,328 efectivo)
N220   … less MMC value                    → valor corregido por MMC
N1120  Profilform 0,2 at Hole 1 to A/C/B   → tolerancia de perfil
```

| | 3212 Pump Housing | 3197 Pot |
|---|---|---|
| Diámetro | Ø4 **−0,1** | Ø4 **+0,1** |
| Posición | ⌖0,15 | ⌖0,25 **con MMC** |
| Referencias | A-B | A/C/B |

> 🔑 **Misma geometría, reglas distintas.** Esto obliga a separar **`FEATURE`** (abstracto) de
> **`INSTANCIA_EN_PROYECTO`** (feature materializado en una pieza concreta, con sus N-numbers y
> sus tolerancias). Sin esa separación no se puede responder *"¿qué pasó con este feature en
> piezas anteriores?"*.

---

## 3. Esquema propuesto

```
PROYECTO (=molde)          3212, 3051, 3197, 2820
  ├─ nº, nombre_pieza, itp_ref, part_nº_cliente, nº_plano,
  │  nivel_pieza, nivel_plano, cliente, nº_molde
  ├─ FICHEROS: plano_2d.pdf, pieza.stp, molde.step, moldflow.mfr, metodo_medida.docx
  │
  ├─ CAVIDAD (n)           c13..c16 · C1..C8 · Cav_1..4
  │
  ├─ MUESTREO (intern.NN)  fecha_informe, fecha_medicion, lote(TEXTO), responsable,
  │    │                   motivo, ppap_ref, es_completo(bool)
  │    │                     ↑ fecha_medicion ≠ fecha_informe (del .igs/PDF, no del .xls)
  │    │                     ↑ lote es TEXTO: en .08/.09 vale "08/01/2025", una fecha
  │    │                     ↑ motivo y responsable salen de la hoja HISTORY (log acumulativo)
  │    ├─ MEDICION         n_number, tipo, sub_ref(Ø1..Ø4 / B1..B4 / L1..L6),
  │    │                   nominal, tol+, tol−, equipo, altura_H, cavidad,
  │    │                   valor, desviacion, fuera_tol, nok, comentario,
  │    │                   id_elemento_cmm          ← join interno del CSV
  │    ├─ MEDICION_CONTORNO  recorrido(PA/PB), tramo(1..6), cavidad, tolerancia,
  │    │                     desv_max_inf, desv_max_sup, infraccion_inf, infraccion_sup
  │    │                       ↑ de los 144 PDF; no está en ningún CSV ni XLS
  │    ├─ PUNTOS_OBJETIVO   cavidad, altura_Y, [25 puntos XYZ]   ← _PUNTS_NOUS.txt
  │    │                       ↑ 6 alturas × 25 pts; uno DISTINTO por cavidad y muestreo
  │    └─ FICHEROS CRUDOS: csv_cmm, nube_puntos.txt
  │       (derivados, solo descarga: contorno.igs = nube_puntos.txt con offset Z;
  │        perfil.dxf = nube de cavidad; totes.csv = subconjunto del csv_cmm)
  │
  ├─ CORRECCION_MOLDE (nº) fecha, revision,
  │    │                   muestreo_origen ──┐    ← del nombre del .xls que la acompaña
  │    │                   muestreo_validacion ┘  ← siguiente muestreo con datos 3D
  │    └─ ACCION           slide_nº, n_number(s), cota_nominal, situacion_actual,
  │                        accion_texto, magnitud_mm, sentido(+plastico/-hierro/∅),
  │                        estado(OK/pendiente/no_actuar), imagen_zona_roja
  │
  └─ PIEZA_REAL            lote, cavidad, escaneado.stl

FEATURE (transversal)      "Bolt Eye", "Nervio", "Llentia", "Espesor local"…
  ├─ descripcion, imagen_representativa, tags, categoria
  ├─ WARNING (n)           texto enriquecido  ← plano 2D + Moldflow + respuestas de INTEPLAST
  ├─ LESSON_LEARNED (n)    texto enriquecido  ← de los PPTX de corrección
  └─ INSTANCIA_EN_PROYECTO (n:n)   feature ↔ proyecto ↔ [n_numbers que lo materializan]

DEPENDENCIA_COTA (n:n)     n_number_origen → n_number_afectado, tipo, texto
                           ← "si toquem 0,29 mm en el pla A, tocar aquí 0,27"
```

### Las tres piezas que hay que modelar bien

1. **`INSTANCIA_EN_PROYECTO`** conecta un feature abstracto con todas sus mediciones y
   correcciones históricas a través de los N-numbers. Es lo que responde a *"estoy diseñando un
   bolt eye nuevo, ¿qué pasó en piezas anteriores?"*.
2. **`CORRECCION_MOLDE.muestreo_origen` / `.muestreo_validacion`** es lo que permite demostrar
   *"esta corrección mejoró esta cota"* — el par antes/después.
   Reconstruido para el 3212 en [3212/historial-molde.md](3212/historial-molde.md).
3. **`DEPENDENCIA_COTA`** captura el acoplamiento entre cotas (el plano A arrastra todo lo
   demás). Es conocimiento tácito que no está en ninguna tabla, solo en el texto de las
   diapositivas.

---

## 4. Prioridad de ingesta

⚠️ **Revisada respecto a la versión inicial**: el XLS ya no va primero. Ver
[formatos-parsing.md](formatos-parsing.md#el-xls-no-es-la-fuente-de-verdad-).

| Prioridad | Fuente | Por qué | Esfuerzo |
|:--:|---|---|---|
| **1** | **CSV de CMM por cavidad** (`3212_c13.csv`) | **Es la fuente de verdad**: cubre todas las cotas en todos los muestreos, incluidos los que el XLS omite. Incluye desviación y semáforo ya calculados. | Bajo |
| 2 | CSV `*_totes.csv` | Comparativa por cavidad ya montada | Bajo |
| 3 | `.xls` PPAP — **solo cabecera + NOK** | Aporta los metadatos que el CSV no tiene: fecha, lote, PPAP ref, responsable, y la marca NOK consolidada | Bajo |
| 4 | Texto de los PPTX de corrección | Lessons learned directas, formato regular | Medio |
| 5 | Imágenes `ppt/media/` de los PPTX | Las imágenes de "zona en rojo" que pide el frontend | Medio |
| 6 | Método de medida (DOCX) | Decodifica el vocabulario y aporta la consecuencia funcional. **Entrada manual**, es un documento por proyecto. | Bajo |
| 7 | Nubes de puntos `.txt` | Soporte a las correcciones *"segons núvol de punts"* | Medio |
| 8 | Plano 2D, Moldflow, STEP/STL | Alto valor pero requieren herramientas específicas / trabajo manual | Alto |

---

## 5. Lo que el frontend ya construido espera

Según `inteplast_PADIH_fase_B.md`, el frontend ya tiene: búsqueda global de features,
tarjetas con imagen + nombre + descripción + tags, y una modal con secciones desplegables de
**warnings**, **lessons learned** y **piezas ejemplo** (CAD, piezas de referencia, planos PDF).

El mapeo es directo:

| Sección del frontend | De dónde sale |
|---|---|
| Imagen representativa del feature | Imagen CAD con la zona en rojo — o `ppt/media/` de los PPTX |
| **Warnings** | Plano 2D + Moldflow + respuestas de `inteplast_resposta_dubtes.md` |
| **Lessons learned** | Texto de las diapositivas de corrección de molde |
| **Piezas ejemplo → moldes CAD** | `3- 3D Molde/*.step` (derivado ligero) |
| **Piezas ejemplo → piezas ref.** | `1-2D y 3D Pieza/*.stp` + `8- STL peça real/*.stl` |
| **Piezas ejemplo → planos 2D** | `1-2D y 3D Pieza/*.pdf` |
| Cotas | `MEDICION` filtrada por los N-numbers del feature |

### Warnings del Bolt Eye ya identificados

De `inteplast_notas_reunion_20_2_2026.md` + `inteplast_resposta_dubtes.md` + los datos:

1. **Ubicación del punto de inyección** (Moldflow, 4 variables: nº, posición, tipo, Ø)
2. **No líneas de soldadura en la zona del agujero** (nota del plano 2D, se valida en Moldflow)
3. **Tolerancias dimensionales** (N170)
4. **Tolerancias de ubicación en el espacio** (N117)
5. **Depende de la planitud de la cara de referencia** (N178) — *"puede pasar de OK a NOK
   tocando ese plano"*
6. **Conicidad / ángulo de desmoldeo** — por eso se mide a dos alturas (Dubte 7)
7. **Diámetro del bolt eye** — hay un calibre pasa que lo garantiza en serie (Dubte 9)
8. **Cambios de sección, contracciones disimilares, piezas no simétricas** — el problema de
   fondo según la reunión inicial
