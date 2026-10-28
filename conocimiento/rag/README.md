# RAG: investigación, glosario y evaluación

Carpeta de apoyo del RAG local ([rag.md](../rag.md)). **No se indexa** (`rag_fuentes.ficheros_markdown`):
no describe Exemples y las preguntas de evaluación se encontrarían a sí mismas.

| Fichero | Qué es |
|---|---|
| [investigacion-2026-10-27.md](investigacion-2026-10-27.md) | Bedrock, Dust, Lookio, pgvector/Qdrant, Docling/Azure DI, RAG agéntico, GraphRAG, SQL, Copilot, evaluación |
| `glosario.json` | 47 conceptos ES/CA/EN/DE/CS que amplían la consulta. **Propuesta pendiente de validar por Eduard**. `rag.py glosario --contar` muestra cuántos documentos contienen cada término |
| `preguntas.jsonl` | 55 preguntas con fuente esperada: 40 de `ajuste` (R-…) y 15 de `control` (C-…) |

```bash
PY=conocimiento/.venv/Scripts/python.exe
$PY conocimiento/herramientas/evaluar_rag.py --k 5            # --sin-glosario, --solo R-014,C-015, --codigo <otra version>, --registrar
$PY conocimiento/herramientas/rag.py buscar "venteo" --sin-glosario   # comparar sin ampliar
```

Una pregunta acierta si la primera fuente esperada (subcadena en id, ruta, localizador, sección o extracto)
sale entre las k primeras. Mide **recuperación**, no la respuesta redactada.

## Resultado del 27/10/2026 (k = 5)

Las tres configuraciones sobre el mismo índice (con `identidad-piezas.md`); registradas en
`datos/rag/evaluacion.jsonl`.

| Configuración | Ajuste (40) recall@5 · MRR | Control (15) recall@5 · MRR |
|---|---|---|
| Código anterior (`HEAD` del 27/10) | 0,775 · 0,61 | 0,80 · 0,68 |
| Actual sin glosario (`tablas` × 0,5, hoja vacía marcada) | 0,825 · 0,62 | 0,80 · 0,68 |
| Actual con glosario | **0,975 · 0,80** | **0,933 · 0,85** |

- **Ajuste**: con estas 40 preguntas se ajustó el glosario (se añadieron `zona_marcada`, `mas_grande`,
  `agujero`, «pines», «añadió plástico» y se quitaron `molde` y `cavidad`, que diluían la búsqueda). Su
  cifra es optimista por construcción.
- **Control**: 15 preguntas escritas después del ajuste y no usadas para él. Es la cifra a citar. Las
  multilingües de control pasan de 3/6 a 5/6.
- Por tipo (todas): curado 26/26, filtro 8/8 (R-014, el caso del 3167: fuera del top-5 con el código
  anterior, 4.º sin glosario, 1.º con él), metadato 1/1 (R-025, cliente del 3309: lo resuelve
  `identidad-piezas.md` con cualquier código), multilingüe 15/17.
- **Fallan 2 de 55:** R-035 («pines nuevos más grandes por falta de redondez»: la diapositiva del 3051
  existe, pero queda por debajo de otras con *pins*, *bigger* y *roundness*) y C-015 («no corregir en este
  loop y esperar» frente a *«Do not corrected for these loop of corrections. Wait…»*: paráfrasis sin
  términos del glosario).
- **28/10/2026, tras añadir las fichas 3174, 3186, 3309 y 3202** (mismo código y glosario, índice nuevo):
  ajuste 0,975 · 0,755; **control 0,867 · 0,79**. Falla además C-012 (*«medidas con valor cero en los informes
  del 3288»*): el hallazgo I-002 baja al 8.º puesto, pero el 1.º resultado es el fragmento de
  `incongruencias.md` que contiene su fila. El evaluador solo mira identificador, ruta, sección y extracto, no el
  fragmento entero. No se ha cambiado para no ajustar la medida contra el conjunto de control.
- Límite: las 55 preguntas las escribió Claude tras leer las fichas. Antes de dar la cifra por
  representativa, añadir preguntas reales de INTEPLAST o de Eduard sin mirar las fichas.

## Pendiente

- Revisar `glosario.json` (Eduard) y medir de nuevo con `evaluar_rag.py`.
- Probar un reranker local (bge-reranker-v2-m3 o Qwen3-Reranker-0.6B) con esta evaluación y su latencia.
- Añadir preguntas de la capa exacta (cifras con respuesta conocida, incluidas las que deben negarse:
  `RAND()`, dato ausente, N-number de otra pieza). Hoy la cubren las comprobaciones SQL de los hallazgos.
