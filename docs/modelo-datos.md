# Modelo de datos

> Cómo se conecta todo y cómo se traduce a la base de datos.
> Contexto de arquitectura (FastAPI + React + PostgreSQL) → `inteplast_PADIH_fase_B.md`.
> Discusión Neo4j vs PostgreSQL → `inteplast_database.md`.

> **Propuesta de dominio, revisada contra el código el 26/10/2026.** Implementación web: [cotas por pieza/revisión, índice de planos y snapshots
> de mediciones/correcciones](cotas-y-evidencia-web.md). El diagrama siguiente describe el
> dominio completo, no implica que todas sus tablas estén ya implementadas.
> El 3212 sigue siendo el piloto de la aplicación; la biblioteca de conocimiento abarca más piezas.

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

El Pot comparte la familia Bolt Eye, pero sus cotas, referencias y tolerancias pertenecen
a su propia pieza y revisión. El análisis y las diferencias entre especificaciones se
mantienen en la [ficha del 3197](../conocimiento/0-bolt-eye/3197.md), incluido el conflicto
entre tolerancias de informes (I-206). No copiar una tolerancia del 3212 ni fijar una única
para todos los documentos del 3197.

Esto obliga a separar **feature** (concepto transversal) de **cota de una pieza y revisión**.
La implementación usa `PartCharacteristic` y `FeatureCharacteristicLink`; la entidad
`INSTANCIA_EN_PROYECTO` del esquema siguiente es una propuesta más amplia.

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
  │    │                     ↑ fecha_medicion con fuente y alcance; perfil ≠ toda la tanda
  │    │                     ↑ lote es TEXTO: en .08/.09 vale "08/01/2025", una fecha
  │    │                     ↑ motivo y responsable: HISTORY y cabeceras contrastadas
  │    ├─ MEDICION         n_number, tipo, sub_ref(Ø1..Ø4 / B1..B4 / L1..L6),
  │    │                   nominal, tol+, tol−, equipo, altura_H, cavidad,
  │    │                   valor, desviacion, fuera_tol, nok, comentario,
  │    │                   id_elemento_cmm          ← join interno del CSV
  │    ├─ MEDICION_CONTORNO  recorrido(PA/PB), tramo(1..6), cavidad, tolerancia,
  │    │                     desv_max_inf, desv_max_sup, infraccion_inf, infraccion_sup
  │    │                       ↑ de los 144 PDF; no está en ningún CSV ni XLS
  │    ├─ SOPORTE_GEOMETRICO cavidad, archivo, subconjunto_de
  │    │                       ↑ PUNTS_NOUS = últimos 150 de PUNTS; objetivo no demostrado
  │    └─ FICHEROS CRUDOS: csv_cmm, nube_puntos.txt, contorno.igs
  │       (relaciones entre formatos: ver la ficha de metrología del 3212)
  │
  ├─ CORRECCION_MOLDE (nº) fecha, revision,
  │    │                   muestreo_origen ──┐    ← del nombre del .xls que la acompaña
  │    │                   muestreo_validacion ┘  ← siguiente muestreo con datos 3D
  │    └─ ACCION           slide_nº, n_number(s), cota_nominal, situacion_actual,
  │                        accion_texto, magnitud_mm, sentido(+plastico/-hierro/∅),
  │                        marcador_original, ejecucion_confirmada, imagen_zona
  │         └─ PREVISION   evaluacion, cavidad, etapas, valor_previsto, archivo/hoja/celdas
  │                        ↑ XLS DR(100%); separada de la medición posterior
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
2. **`CORRECCION_MOLDE.muestreo_origen` / `.muestreo_validacion`** permite comparar
   el antes y el después de un plan. Confirmar ejecución y causalidad requiere evidencia adicional.
   Reconstruido para el 3212 en [3212/historial-molde.md](../conocimiento/0-bolt-eye/3212/historial-molde.md).
3. **`DEPENDENCIA_COTA`** captura el acoplamiento entre cotas (el plano A arrastra todo lo
   demás). Es conocimiento tácito que no está en ninguna tabla, solo en el texto de las
   diapositivas.

---

## 4. Prioridad de ingesta

**Prioridad propuesta para ampliar la ingesta**, no una lista de lectores ya implementados.
El contrato actual está en [Cotas y evidencia](cotas-y-evidencia-web.md).
El XLS no debe prevalecer automáticamente sobre el export CMM; ver
[formatos-parsing.md](../conocimiento/formatos-parsing.md#discrepancias-entre-medidas-xls-y-csv).

| Prioridad | Fuente | Por qué | Esfuerzo |
|:--:|---|---|---|
| **1** | **CSV de CMM por cavidad** (`3212_c13.csv`) | Fuente prioritaria para las evaluaciones CMM exportadas en los cuatro muestreos. Conservar valores y semáforo originales, junto con las correcciones verificadas. No cubre todos los requisitos ni ensayos del plano. | Bajo |
| **2** | XLS de retoques, `DR(100%)` | Previsiones por cavidad, hipótesis y efectos encadenados, con celdas de origen | Medio |
| 3 | PDF `PA`/`PB` | Mediciones de contorno que no están en CSV ni XLS; conservar estado desconocido si falla la extracción | Medio |
| 4 | XLS: `HISTORY` y cabeceras contrastadas | Cronología e identificación: combinar hojas según la [cabecera contrastada del 3212](../conocimiento/0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro) | Bajo |
| 5 | Texto e imágenes de los PPTX de corrección | Lessons learned, acciones y zonas de retoque, con su evidencia | Medio |
| 6 | Método de medida (DOCX) | Decodifica el vocabulario y aporta la consecuencia funcional. **Entrada manual**, es un documento por proyecto. | Bajo |
| 7 | `.txt` de perfil, `PUNTS` y `PUNTS_NOUS` | Soporte geométrico; NOUS es subconjunto, no objetivo demostrado | Medio |
| 8 | Plano 2D, Moldflow, STEP/STL | Referencias y visualización; análisis automático pendiente | Alto |
| — | `.igs` del 3212 | Conservar como soporte distinto; no deduplicar como nube 3D. Evidencia en la ficha de metrología enlazada debajo | — |
| — | `.dxf` y CSV `*_totes.csv` del 3212 | Evitar duplicar puntos solo tras verificar equivalencia y conservar procedencia. `totes` compara CSV individuales; no aplicar la relación del 3212 a otras piezas sin contrastar | — |

La marca NOK del XLS sirve para contrastar la medición; no sustituye al CSV cuando el informe
contiene bloques copiados de otra tanda. Completar los metadatos cruzando las hojas del libro.
Contraste geométrico: [3212, IGES y DXF](../conocimiento/0-bolt-eye/3212/4-metrologia.md#rectificación-dxf-equivalente-con-redondeo-iges-con-z-aplanada).

---

## 5. Lo que el frontend ya construido espera

**Tablas reales consultadas en el código el 26/10/2026.** El diagrama de la sección 3 no
es el esquema SQL desplegado. Estas son las correspondencias actuales:

| Concepto o sección | Persistencia implementada | Fuente del código |
|---|---|---|
| Pieza e identidad | `Part`: código, nombre, descripción, cliente y carpeta | [models.py](../backend/app/models.py) |
| Feature y piezas asociadas | `Feature`, `FeaturePartLink`; los adjuntos heredados también pueden aportar una pieza | [models.py](../backend/app/models.py) |
| Advertencias y lecciones | `FeatureNote`, con `kind=warning/lesson`; contenido editado o aceptado por una persona | [models.py](../backend/app/models.py) |
| Cotas del feature | `PartCharacteristic` por pieza/código/revisión y `FeatureCharacteristicLink` con rol | [knowledge_models.py](../backend/app/knowledge_models.py) |
| Archivos y referencias de pieza | `PartFile`, `PartReference` y `PartDocument`, asociados a `StoredFile` | [knowledge_models.py](../backend/app/knowledge_models.py) |
| Mediciones importadas | `MeasurementImport`: filas, contexto, huella y estado previo en JSON | [measurement_models.py](../backend/app/measurement_models.py) |
| Estudio piloto, correcciones e índices | `EvidenceJob`: estados y resultados estructurados en JSON | [knowledge_models.py](../backend/app/knowledge_models.py) |
| Imagen y zona CAD | `Feature.image_id` / `cover_3d`; captura de pieza y archivos derivados | [Portadas CAD](portadas-cad.md) |

No existen todavía las tablas normalizadas `MUESTREO`, `MEDICION`, `CORRECCION_MOLDE`
y `DEPENDENCIA_COTA` del esquema propuesto. Las notas de la GUI tampoco son una extracción
automática del texto de los PPTX. La importación y la consulta de snapshots se describen
una sola vez en [Cotas y evidencia](cotas-y-evidencia-web.md); la navegación, en
[Interfaz](interfaz.md).

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

## Revisión de interpretación del 17/09/2026

La primera experiencia se centra en antes → acción propuesta → previsión XLS → después.
Prototipo independiente: `prototypes/data-explorer/ver_correcciones.py` (N161, N240, N170, N165 y perfiles).
Desde el 18/09/2026 la web lo incorpora para el 3212 ([Cotas y evidencia](cotas-y-evidencia-web.md));
el prototipo se conserva como referencia. [Evidencia y decisiones](../conocimiento/0-bolt-eye/3212/revision-2026-09-17.md).

No agregar N170 como conforme si solo entra GX; conservar LP máximo, agujero y altura.
No contar las 120 filas POINT de N165 como 120 características independientes.
Registrar propuesta, marcador, ejecución y resultado como conceptos separados. Una medición
posterior no prueba causalidad exclusiva; pueden coexistir retoques y cambios de proceso.
