# Auditoría de las tablas derivadas (11/11/2026)

**Pregunta:** ¿están las tablas y los informes derivados al día respecto al código que los genera? La duda surgió
porque `perfil_ppap` llevaba sin regenerarse desde el cambio de su código del 04/11/2026 (ver
[revision-comprobaciones.md](revision-comprobaciones.md#l1-lector-de-la-cabecera-ppap)). Ni las fechas de los
ficheros ni los tests lo demuestran.

**Respuesta:** las tablas derivadas regeneradas con el código actual coinciden, fila a fila y campo a campo, con las
guardadas, **sobre las entradas disponibles**. Eso no acredita toda la extracción original: quedan fuera la
reextracción de las tablas base de unos 3.800 ficheros, las capturas CAD y la regeneración del OCR de los planos (ver la
tabla). Hubo dos desfases que no cambiaban ningún dato, y los dos se aplicaron el mismo día ([Aplicado](#aplicado-11112026)):

- **656 `.xls` extraídos con `xls@1`**, cuando el lector actual es `xls@2`. Al reextraerlos sale el mismo contenido.
- **La auditoría de aceptación del 02/11** se hizo con una versión anterior de los lectores. Al repetirla salen los
  mismos resultados.

**Impacto en el visor: ninguno.**

## Método

- **Copias aisladas en el scratchpad.** Cada una con el código de `conocimiento/herramientas`, los ficheros de
  `conocimiento/` y una copia de la biblioteca, con la misma estructura de carpetas. Las herramientas calculan sus rutas
  a partir de su carpeta, así que la base y los informes generados (`identidad-piezas.md`, `ingesta/`) quedan dentro de
  la copia. Los originales de Exemples solo se leen: antes se comprobó que los 4.530 estaban en local.
- **Biblioteca real intacta.** El mismo SHA-256 antes y después (`6c502196…`). `datos/aceptacion/` e `ingesta/`, sin
  cambios.
- **Comparación** contra una copia congelada de la biblioteca: el multiconjunto de filas completas y, por clave, los
  campos que cambian. No solo recuentos. La herramienta queda en el repo, con prueba en `test_revision.py`:
  `conocimiento/herramientas/comparar_derivadas.py tablas ACTUAL NUEVA` y `… aceptacion CARPETA_ACTUAL CARPETA_NUEVA`.
  El modo `aceptacion` se corrigió después de señalarlo el revisor. Antes no veía un fichero que solo estuviera en la
  carpeta nueva, y ocultaba los `id` repetidos. Ahora recorre la unión de los ficheros de las dos carpetas, registra
  los exclusivos de cada una aunque estén vacíos, y cuenta los `id` repetidos en toda la carpeta, también entre
  ficheros. Cualquiera de esas diferencias da código de salida 1. Repetida la comparación con la versión corregida:
  aceptación y balances actuales frente a los de la copia, 0 diferencias.
- **Tres fases:**
  - **A:** regenerar todas las derivadas sobre las tablas base actuales.
  - **B:** reextraer los `.xls` desfasados y volver a regenerar.
  - **C:** repetir la auditoría de aceptación y su cierre.

## Resultado

| Tabla o informe | Generador (en orden) | Depende de | Resultado | Diferencias | Causa | Impacto en el visor |
|---|---|---|---|---|---|---|
| `documento` | `inventariar.py` | disco de Exemples | Al día | 0: los 4.530 con el mismo tamaño y fecha en disco; ningún fichero sin inventariar | — | Ninguno |
| `celda`, `elemento`, `estructura` (`.xls`) | `extraer.py` | originales | Desfasada, sin efecto. **Aplicado** | 656 `.xls` con `xls@1` (extraídos el 21/10); el lector es `xls@2` desde `dc425dc` (26/10). Reextraídos en la copia (fase B): `celda` (11.420.290 filas) y `estructura` idénticas; `elemento` idéntica salvo su `id` autonumérico. Después, lo mismo en la biblioteca real | Subida de versión del lector sin reextraer | Ninguno. Cambian los `elemento.id`: se reconstruyó el índice RAG, que los guarda |
| `celda`, `elemento`, `estructura` (resto) | `extraer.py` | originales | **No verificable** en esta auditoría | Al día según la regla de `extraer.py` (`tamaño:mtime:lector@versión`), pero no se reextrajeron: son unos 3.800 ficheros, muchos con Word o Excel por COM | — | — |
| `elemento_fts` | disparadores de `elemento` | `elemento` | Al día | 887.347 filas, igual que `elemento`; `integrity-check` correcto | — | Ninguno |
| `celda_aleatoria` | `formulas_aleatorias.py` | `celda`, originales `.xls` (Excel) | Al día | 0 de 649.977 | — | Ninguno |
| `perfil_ppap` | `perfil_ppap.py` | `celda` | Al día | 0 de 1.364 | Se regeneró el mismo 11/11, tras L1 | Ninguno |
| `perfil_correccion` | `perfil_correcciones.py` | `elemento` | Al día | 0 de 1.534 | — | Ninguno |
| `globo` | `globos_icp.py` | originales `.icp`/`.prf` | Al día | 0 de 2.126 | — | Ninguno |
| `identidad-piezas.md` | `identidad_piezas.py` | `perfil_ppap`, `celda` | Al día | Idéntico | — | — |
| `lectura_dr`, `medida_dr` | `lector_dr.py` | `celda`, `celda_aleatoria` | Al día | 0 de 1.791 y 0 de 1.671.138 | — | Ninguno |
| `cadena_correccion` | `cadena_correcciones.py` | `perfil_correccion`, `medida_dr`, `lectura_dr`, `perfil_ppap` | Al día | 0 de 2.062 | — | Ninguno |
| `medida_cmm`, `medida_cmm_comparativa`, `punto_cmm`, `medida_contorno` | `medidas_cmm.py` | originales CSV, TXT y PDF (3197, 3212) | Al día | 0 de 8.296, 5.452, 400 y 144 | — | Ninguno |
| Censo de `valores_por_punto.py` | `valores_por_punto.py` (solo imprime) | `medida_dr` | Al día | Salida idéntica | — | — |
| `datos/aceptacion/*-auditoria.jsonl` | `auditar_ingesta.py` | biblioteca, originales, `backend/app/ingestion` | Desfasada, sin efecto. **Aplicado** | Repetida (fase C): mismos resultados en los 4.530 documentos. Cambia la huella de los lectores, y desaparece una nota escrita a mano (`ajuste_no_funcional`) en 1.535 documentos de 3167, 3174, 3195 y 3218; se conserva [aquí](#la-nota-manual-que-desaparece) | Los lectores cambiaron después (`ce8cd6a`, 04/11; `bf38394`, 10/11) y la auditoría no se repitió | Ninguno |
| `ingesta/balances/*.jsonl`, fichas, `validacion-3167.json`, `ingesta/README.md` | `cerrar_fichas.py` | auditoría de aceptación | Desfasada, sin efecto. **Aplicado** | Regenerados con la auditoría nueva: fichas, README y validación idénticos; los balances solo cambian en `huella_lectores`. `verificar_aceptacion.py --balances` daba **4.530 avisos «cambió el lector»**; ahora, 0 | La misma | Ninguno. Esos 4.530 avisos falsos habrían tapado cualquier aviso real |
| Lecturas de los planos sin `.icp` (`out/conocimiento/lecturas`) | `leer_planos.py` | PDF de plano, modelo ONNX | Al día según su firma | `pendientes()` vacío: las 26 con SHA-256, versión y lector actuales. No se regeneraron (OCR, unos 30 min) | — | — |
| Índice RAG (`datos/rag`) | `rag.py construir` | fichas, hallazgos, biblioteca | Al día | `estado --verificar`: frescura completa correcta (11/11) | — | — |
| `auditoria`, `ejecucion` | `verificar.py`, todas las herramientas | — | No aplica | Son registros de ejecuciones, no datos derivados | — | — |
| Capturas CAD (`out/conocimiento/cad`) | `miniaturas_cad.py` | STEP originales | **No verificable** | Necesita un entorno aparte (cadquery-ocp), que no se montó | — | — |

## Aplicado (11/11/2026)

Con el visto bueno del revisor, en el orden que propuso (reextracción → aceptación y balances → RAG → verificación):

1. **Reextracción.** `extraer.py --ext xls`, el mismo alcance que en la copia: 656 documentos, 226 s. Los 657 `.xls`
   quedan en `xls@2`. Comparada con la copia previa, la biblioteca real tiene `documento`, `celda`, `elemento` (sin `id`)
   y `estructura` idénticos, y solo cambian `version_extraida` y `extraido_el` en los 656 documentos.
2. **Aceptación y balances.** `auditar_ingesta.py` → `cerrar_fichas.py`. La auditoría es igual a la de la fase C en
   los 4.530 documentos, e `ingesta/` es igual byte a byte a la de la copia. En Git solo cambian los 22
   `ingesta/balances/*.jsonl`, una línea por documento: su `huella_lectores`.
3. **RAG.** `rag.py construir`: 9 vectores nuevos y 10.248 reutilizados. `estado --verificar`: frescura completa correcta.
4. **Verificación final:**
   - `comparar_derivadas.py tablas`, entre la copia previa y la biblioteca real: 0 diferencias en las 15 tablas.
   - `verificar_aceptacion.py` completo: 0 errores en casos, lecciones, balances y piloto.
   - `revision.py`, con los mismos recuentos que antes (M12 27, M6 30).
   - Tests: 101 del visor y 83 de herramientas.
   - `verificar.py --hallazgos`: sin problemas.

## Evidencia

| Qué | Huella completa |
|---|---|
| Biblioteca antes de la auditoría y durante las fases A, B y C (sin cambios) | `6c502196591afefd80bed2c982ca4bd030bb784094bf3bf695b3002625b09e98` |
| Biblioteca después de aplicar (por la reextracción: versión, fecha e `id` de `elemento`) | `128768578ee4782f138ba17844f35ce8397fa811df850daed669831f80399a70` |
| Huella de los lectores en la auditoría del 02/11 | `947e798f70a32a04c3bec78355936ca073e772a0892367214de363bab4446f5a` |
| Huella de los lectores actual (`auditar_ingesta.huella_lectores`) | `7120672202943114134761f4be61e245d61ea966918cef8d001b411d8b8eb3b1` |

Recuentos comparados en las fases A, B y en la verificación final, todos con 0 filas distintas: `celda` 11.420.290;
`elemento` 887.347; `estructura` 20.524; `celda_aleatoria` 649.977; `perfil_ppap` 1.364; `perfil_correccion` 1.534;
`globo` 2.126; `lectura_dr` 1.791; `medida_dr` 1.671.138; `cadena_correccion` 2.062; `medida_cmm` 8.296;
`medida_cmm_comparativa` 5.452; `medida_contorno` 144; `punto_cmm` 400. Para repetirlo: copiar la biblioteca y el árbol
de herramientas a una carpeta aislada, regenerar en el orden de la tabla y ejecutar `comparar_derivadas.py`.

### La nota manual que desaparece

La auditoría del 02/11 llevaba en 1.535 documentos de 3167, 3174, 3195 y 3218 esta nota, que no genera ningún script.
Describe una comprobación histórica sobre un cambio de tipos en los lectores:

> `ajuste_no_funcional`: «AST de los cinco lectores idéntico al eliminar únicamente anotaciones e imports de tipos. Se
> conserva la huella de ejecución; no cambian resultados.» `huella_ejecucion`:
> `25497a3cf680521322580eb2a2b8aaf137d494f86cc990c63ccd8a83e2916124`.

Se conserva aquí una vez. Los ficheros generados se reconstruyen sin ella.
