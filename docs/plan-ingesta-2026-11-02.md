# Ingesta de todas las piezas y conocimiento

> Revisión P1–P9: correcciones contrastadas con 53 casos contra el backend y auditoría de los 4.530 originales. Resultados y alcance en `conocimiento/ingesta/revision-P1-P9.json`.

Plan autorizado por Eduard el 02/11/2026. No implica importar datos en la aplicación,
validar lecciones en nombre de INTEPLAST ni borrar originales o respaldos. Git lo gestiona Eduard.

## Criterios comunes

- Originales de `Exemples` y `C:\edu` de solo lectura. Fixtures sintéticas en los tests.
- Lectores de producción independientes de `conocimiento/` y `prototypes/`.
- Tests del backend mediante `scripts/test.ps1` o `scripts/test.sh`, en stack aislado.
- Conservar evidencia, localizador y revisión. No confundir fecha de archivo con ejecución.
- Una coincidencia entre lectores no sustituye casos comprobados en originales.
- La aceptación técnica se documenta con contrastes reproducibles; la aprobación corporativa requiere una fuente de INTEPLAST y no se presume.

## Estado de las fases

| Fase | Entrega y aceptación | Estado |
|---|---|---|
| F0 | 53 casos de 21 piezas, coordenada/hash/valor y evidencia; fórmulas BIFF referidas a auditoría COM anterior | Contrastados de nuevo en originales; verificador reproducible sin errores |
| F1 | Firma/formato, fórmulas BIFF8/OOXML, Calamine, XLSM, estado por celda, gráficos/asistente y regresión | Implementado y probado; no se ha cargado la app |
| F2 | Clasificador y agregado de 21 piezas, fuentes complementarias y conflictos; I-108/I-310/H-310 | Implementado y contrastado |
| F3 | 21 contratos con balance por archivo/hoja, casos originales y exclusiones; piloto 3167 | Cierre técnico completado: 4.530 archivos conciliados, cero discrepancias aceptadas |
| F4 | Fuente única en hallazgos, revisión documental, mapa y exportación | 10 notas y 6 grupos de vínculos contrastados en 51 comprobaciones; exportación preparada. Aprobación corporativa y carga son estados separados |
| F5 | Correcciones N1/N2/N5, hidratación fechada y cifras actuales | Hecho; historial conservado |
| F6 | Índice y evaluación después de editar las fuentes | Reconstruido; evaluación registrada, detalle en [rag.md](../conocimiento/rag.md#evaluación-del-02112026) |
| F7 | Prefijos concretos, total/truncado, guía de herramientas | Implementado: 10 diapositivas y 54 ubicaciones |
| F8 | Tablas independientes CMM/contorno y consulta exacta | 3.376 evaluaciones y 144 perfiles contrastados |
| F9 | SQL de identidad/N170 y 3 preguntas negativas en conjunto separado | Hecho; preguntas reales de usuarios pendientes |

F0 se prepara junto a F1/F2. F3 usa F0/F2. F6 se ejecuta después de todas las
ediciones de fuentes y de F7, para evaluar el estado final. Las preguntas reales de
Eduard e INTEPLAST no se sustituyen por preguntas del implementador. La validación
técnica de las fichas queda registrada por Codex; no representa una homologación del cliente.

## Política de procedencia acordada con Eduard

Tres estados por valor: `medicion`, `generado`, `sin_confirmar`.
Solo `medicion` sin marca `copia` entra en estadísticas, gráficas y respuestas numéricas del asistente.
Se conservan los valores originales y se muestran motivos y recuentos de exclusión.
Se excluye la celda generada, no las medidas de origen de la misma fila.
Una hoja con RAND lleva un aviso sobre cálculos dependientes. Mientras no se resuelvan
dependencias, los resultados de fórmula potencialmente afectados quedan sin confirmar.
La detección directa no demuestra el origen de constantes ni de copias pegadas como valores.
Los futuros lectores SPC `#P#` deberán distinguir salidas del generador demostradas
de procedencia sin confirmar (3168 SPC y 3237-20).

## Decisiones y límites

- Ficha piloto: 3167, contraste técnico completado; [ficha y balance](../conocimiento/ingesta/3167.md).
- Nuevas dependencias: solo las necesarias para lectura estática; no ejecutar Excel ni macros.
- XLSM: habilitar únicamente junto con las protecciones y sus pruebas.
- CLAUDE.md: actualizar la información de hidratación dentro del alcance autorizado.
- Carga de notas/vínculos: pendiente de validación de INTEPLAST y decisión de Eduard.
- F8: lector independiente limitado a formatos documentados.
- Respaldo de 1,16 GB: conservar. Servidor persistente y afinado semántico: aplazados.

## Correcciones P1–P9 y verificación final

- P1: ITP numérico normalizado; PPAP 3281 con ITP propio del 3218 queda con aviso. En el balance completo del 3218, sin confirmar pasa de 457.462 a 79.490; no es una resta de medidas recuperadas, porque también se conservan IMPOSED y se revisan dependencias/copias.
- P2: 53 casos contrastan el original y la salida productiva: estado, marcas, elegibilidad, tolerancias e identidad. Incluyen CAV y 100% numérico, además de la exclusión explícita de B3 alfanumérico.
- P3: posible copia del generador solo con fila/fuente, muestra replicada e intervalo/redondeo compatibles. Conserva sin_confirmar, nunca generado.
- P4: copia estructural por coordenada/contexto/valor exacto. Las diferencias permanecen aparte; IMPOSED queda visible sin entrar en estadísticas. En 3174 se marcan 7.136 copias; en 3218, 56. Son observaciones conservadas, no nuevas mediciones.
- P5: referencias estáticas y propagación; independientes recuperan medicion. Dependencias dinámicas, externas, nombres y ciclos no resueltos siguen sin confirmar.
- P6/P7: resultado_vacio preciso y excepción UnsupportedWorkbook por archivo. Los errores inesperados siguen fallando.
- P8/P9: candidatos recuperados de las ocho fichas, citas concretas, cotas asociadas y nombres de feature uniformes. Contextos propios de las 21 piezas, con declaraciones contradictorias conservadas.
- 371 pruebas de backend (stack aislado), 61 de conocimiento y 7 de interfaz correctas; TypeScript y Ruff de los archivos revisados correctos. Mypy de los cuatro lectores revisados correcto; el lint global sigue encontrando errores ajenos a este cambio en balloon_reader, drawing y routes/evidence.
- 978 libros Excel auditados más un PDF con extensión XLS; 649.977 coordenadas RAND coinciden exactamente con la biblioteca. Cero celdas exclusivas de uno u otro lector.
- Las auditorías conservan su huella de ejecución. El ajuste final de anotaciones de tipos no cambia el AST ejecutable: se comprobó igualdad tras retirar exclusivamente anotaciones e imports de tipos, antes de actualizar la huella publicada.

Detalle reproducible: [resultado P1–P9](../conocimiento/ingesta/revision-P1-P9.json), [contratos](../conocimiento/ingesta/README.md) y `verificar_aceptacion.py`. No se importaron datos del cliente en la app. Las lecciones siguen sin aprobación de INTEPLAST.

## Verificación anterior a las correcciones P1–P9 (histórico)

- Backend: `scripts/test.ps1 -q`, **361 pruebas correctas**, stack aislado y retirado al terminar. Tras añadir la protección de bloques contiguos repetidos, **32 pruebas seleccionadas correctas** (330 no seleccionadas; 362 en total).
- Auditoría estática de originales: **976 libros**, **649.977 celdas RAND en 191 libros**, sin diferencias de coordenadas respecto a `celda_aleatoria` ni errores. El XLS que contiene un PDF se identifica aparte. Se comparan libros canónicos extraídos, sin multiplicar duplicados exactos; no certifica dependencias ni constantes pegadas desde un generador.
- Conocimiento: **60 pruebas correctas** (22 lectores, 26 RAG, 12 revisión). `verificar.py --hallazgos`: sin problemas.
- Aceptación: 4.530 documentos con tratamiento, 53 casos originales y 16 registros de conocimiento con 51 comprobaciones de fuente. `auditar_ingesta.py` contrasta el lector productivo con `medida_dr` y lectura independiente Calamine; completa las variantes de muestras cliente omitidas por el perfil histórico. `verificar_aceptacion.py` comprueba balances, huellas de lectores, archivos y columnas CSV exactas, incluida la variante de muestra.
- Piloto 3167: 701 documentos, 133 hojas con referencia/salida; 123.265 resultados Excel = 119.394 medición + 3.871 sin confirmar. Las 19.022 referencias sin salida tienen motivo y localizadores. Los 16.400 valores de los 328 SPC coinciden con 82 generadores. Se contrastaron las 11.808 celdas de muestras de las dos versiones Inf_04 (9.880 numéricas y 1.928 de texto), con 8 cambios de valor y 520 cambios de tolerancia. Se conservan las versiones separadas; detalle en [validación independiente](../conocimiento/ingesta/validacion-3167.json).
- El contraste detectó y corrigió dos problemas productivos: cabeceras Nominal/Tol repetidas a la derecha que sustituían las principales y bloques secundarios sin contexto tratados como mediciones. También corrigió I-311 en la biblioteca: el Nr de una comparativa desplazaba el código de cota del bloque principal; `medida_dr` y `cadena_correccion` regeneradas.
- Frontend: comprobación TypeScript y Biome; 6 pruebas de gráfica/procedencia y evolución. Los valores generados permanecen en evidencia y no producen puntos ni variaciones medidas.
- Aplicación local reconstruida con `docker compose up -d --build backend frontend`: backend sano y HTTP 200 en salud/API y frontend. No se han cargado mediciones, lecciones ni vínculos nuevos en la BD de la aplicación.
- CMM: comparación de las 3.376 evaluaciones con `ingestion/cmm.py`, sin diferencias numéricas (>1e-9). Convención distinta de exceso cero: biblioteca 0, backend ausente; ambas significan conforme tras corregir signo.
- PDF: 144 perfiles, mismos 7 campos numéricos que `profile_pdf.py`; renderizado de comprobación solo en temporales.
- N170 B1/H1,5/c13, muestras 01/03/05/08: GX 3,429 / 3,974 / 3,981 / 3,978; LP máximo 3,477 / 4,018 / 4,023 / 4,023. LP NOK: 32 / 30 / 28 / 26 de 32 por muestreo.
- `exacto medidas --pieza 3212 --cota N170`: 256 CSV + 832 DR, 24 documentos. El límite se avisa; usar `--max 1200` para ver todo.
- Identidad: 3288 ya no tiene un número heredado como principal; 3218 conserva sus 184 hojas con PPAP 3281 como propias con aviso. Cambios de valor principal adicionales: 3309 recupera GF991-53540/733090000; 3202 recupera 885253-11250 en una cabecera propia. Otros cambios son recuentos/exclusiones, no nuevos valores principales.
- La comparación independiente detectó y permitió corregir un fallo del lector CMM nuevo en los nominales negativos de posición Z; queda cubierto por prueba sintética.
- RAG: frescura completa verificada, sin textos pendientes de vector; `planos-globos.md` aparece en búsqueda. La evaluación y sus limitaciones se conservan en [rag.md](../conocimiento/rag.md#evaluación-del-02112026), sin modificar las preguntas históricas de control.

Los [21 contratos](../conocimiento/ingesta/README.md) están cerrados para el alcance que describen. Sus balances miden cada documento antes de fusionar series, priorizar CSV y deduplicar; no son filas ya importadas en la BD. Las plantillas no soportadas y #P#/SPC tienen exclusión explícita, sin certificarlas como mediciones. Una ampliación del lector exige repetir el contraste y justificar los cambios de esperado.

La exportación F4 conserva referencias naturales y revisión (incluida la desconocida); todavía no resuelve UUID ni importa la BD. Las 3 preguntas negativas fueron escritas por Codex, no por INTEPLAST. Evalúan recuperación de evidencia, no la calidad de una respuesta generada.
