# Investigación: cómo recuperar el conocimiento de INTEPLAST (27/10/2026)

Pregunta de Eduard: ¿conviene una plataforma (AWS Bedrock Knowledge Bases, Dust, Lookio, Copilot)
o lo que ya tenemos? ¿Qué aportan pgvector/Qdrant, Docling/Azure Document Intelligence, el RAG
agéntico y GraphRAG? ¿Nuestro caso es una combinación de RAG y consultas SQL?

**Método.** Unas 60 búsquedas y lecturas, hechas por un agente de investigación y filtradas con el
contexto del proyecto. **Reddit no fue accesible** (bloqueado para el agente): la opinión de comunidad
sale de Hacker News, foros de Microsoft/AWS, dev.to y blogs; de YouTube apenas hubo material útil.
Cada afirmación lleva su fuente. Etiquetas: **[Oficial]** documentación o precios del fabricante,
**[Benchmark]** artículo o comparativa, **[Proveedor]** blog de parte interesada, **[Comunidad]** opinión.
Los precios son los publicados el 27/10/2026 y cambian; las conclusiones de aplicación son nuestras.

## Conclusión

Lo que hay (búsqueda híbrida, señal literal para identificadores, vía exacta de SQL de solo lectura y,
en la app, herramientas tipadas con cifras presentadas por el backend) coincide con la práctica
recomendada. **Ninguna plataforma gestionada entiende las reglas que ya resolvemos**: celdas `RAND()`
(I-003), N-numbers locales a cada plano, CSV antes que XLS (I-001), versiones y procedencia por celda.

La decisión pendiente con IT no es dónde vive el conocimiento, sino **qué modelo conversa con él**.
Propuesta: el backend de la app como **única capa de conocimiento** (datos + reglas + herramientas de
lectura), publicada también como servidor **MCP** (*Model Context Protocol*, el conector estándar que
entienden Copilot Studio, Claude Code y otros), y el modelo de delante intercambiable: Ollama local,
un modelo en la nube o Copilot.

```
Usuario ─► Chat de la app (Ollama) ─┐
Usuario ─► Copilot en Teams ────────┼─► MCP ─► Backend (BD + reglas) ─► cifra + fuente
Eduard ──► Claude Code ─────────────┘
```

## Resumen por opción

| Opción | ¿Encaja? | Por qué |
|---|---|---|
| AWS Bedrock Knowledge Bases | No | Copiar datos de Bosch de Microsoft 365 a otra nube; control total sobre SharePoint; Excel como texto; SQL solo sobre Redshift |
| Dust | No (salvo asistente corporativo general) | Genérico, sin nuestras reglas; otro subencargado de datos; como mucho, cliente del MCP |
| Lookio | No | Sin SharePoint, sin Excel ni PPTX, sin empresa ni alojamiento declarados |
| pgvector + texto completo de Postgres + RRF | Sí, seguir | Escala mínima (~10⁴ vectores); actualizar a ≥ 0.8.7 |
| Qdrant / LanceDB / sqlite-vec | No hace falta | Solo con millones de vectores o filtrado muy intensivo |
| Docling local | Parcial | PDF nativo y PPTX; no sustituye la biblioteca para XLSX |
| Azure Document Intelligence (`ocrHighResolution`) | Probar un día | Pensado para texto pequeño en planos; en el Azure del cliente |
| Visión por recortes («detectar → recortar → leer») | Sí, para globos y zonas rojas | Nunca la página entera; vocabulario cerrado de N-numbers |
| RAG agéntico en la app (2B en CPU) | No | Latencia y fiabilidad de las llamadas a herramientas |
| Servidor MCP del backend | Sí | Una capa de herramientas para app, Copilot y Claude Code |
| GraphRAG (Microsoft, LightRAG, Neo4j) | No | El grafo ya existe en el modelo relacional; extraerlo con LLM rompe la clave N-number |
| SQL generado libremente en la app | No | Solo en el agente de desarrollo, con solo lectura |
| Catálogo de consultas con nombre y parámetros | Sí | Acierta en lo que cubre y se niega en lo demás |
| Copilot como indexador | No | Limitaciones oficiales con celdas de Excel, imágenes y ficheros *Confidential* |
| Copilot como frontal vía MCP | Sí, si hay licencias | Identidad del usuario, sin copiar datos; exige endpoint HTTPS con Entra ID |
| Cabecera contextual + reranker local | Sí, medido | Barato; validar con la evaluación (`preguntas.jsonl`) |

## 1. AWS Bedrock Knowledge Bases

**No encaja.** Obligaría a llevar datos confidenciales del cliente final a AWS y a conceder permisos
amplios sobre SharePoint, y no aporta nada para hojas con fórmulas ni para cifras exactas.

- *Managed Knowledge Base* (17/06/2026): RAG totalmente gestionado (AWS elige embeddings, reranker y
  modelo), seis conectores (S3, SharePoint, Confluence, Google Drive, OneDrive, web), «Smart Parsing» y
  un recuperador agéntico. En la UE: Dublín, Fráncfort y Londres. [Oficial]
  <https://aws.amazon.com/blogs/aws/introducing-amazon-bedrock-managed-knowledge-base-for-faster-more-accurate-enterprise-ai-applications/>
- La versión clásica deja de admitir conectores nuevos de SharePoint el 30/09/2026; el conector estaba en
  *preview*, sin tablas ni imágenes. [Oficial] <https://docs.aws.amazon.com/bedrock/latest/userguide/sharepoint-data-source-connector.html>
- La gestionada pide autenticación Entra *App-Only* con certificado y `fullcontrol` por sitio, o
  `Sites.FullControl.All`. [Oficial] <https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-ds-sharepoint.html>
- Formatos: xls/xlsx, csv, pdf, docx, md, html, txt (≤ 50 MB); **no lista pptx**. Sin verificar si el
  parser gestionado lo admite. [Oficial] <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html>
- Datos estructurados (lenguaje natural → SQL) solo sobre Redshift o Glue; AWS advierte del riesgo de
  ejecutar SQL arbitrario. [Oficial] <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-structured.html>
- GraphRAG con Neptune Analytics: solo S3, ≤ 1.000 ficheros por origen, sin personalizar el grafo.
  [Oficial] <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-graphs.html>
- Experiencias: tablas incrustadas mal recuperadas (AWS recomienda preprocesar con Textract)
  [Comunidad] <https://repost.aws/questions/QUf3w9xg2kQWa6m6qg3sciZw/issue-with-knowledge-base-and-tabular-data>;
  útil para pruebas de concepto, poco control de troceado y ranking [Comunidad]
  <https://dev.to/bijkler/aws-bedrock-managed-knowledge-bases-should-we-use-them-3119>.
- Precio (página oficial): 5 $/GB-mes de datos originales, 1 $ por 1.000 consultas, modo agéntico 4 $ por
  1.000 + 1 $ por 1.000 consultas internas. La versión clásica paga el almacén vectorial (OpenSearch
  Serverless ≈ 350 $/mes de suelo según [Proveedor] <https://cloudburn.io/blog/amazon-bedrock-pricing>).
  <https://aws.amazon.com/bedrock/pricing/>

## 2. Dust y Lookio

- **Dust** (dust.tt): plataforma seria de agentes, residencia EU/US, SSO Entra, SOC 2 Tipo II. Pro 24 €/
  usuario/mes (anual); Business hasta 100 personas, 3 conectores y 5 servidores MCP. [Oficial]
  <https://dust.tt/home/pricing>. Conector SharePoint con `Files.Read.All` y `Sites.Read.All`; las hojas se
  consultan como tablas generando SQL, y Dust reconoce que la búsqueda semántica no sirve para
  preguntas cuantitativas. [Oficial] <https://docs.dust.tt/docs/microsoft-connection>,
  <https://docs.dust.tt/docs/table-queries>. **Para nosotros**: volvería a indexar con un parseo
  genérico y sin nuestras reglas; solo tendría sentido como otro frontal del MCP.
- **Lookio** (lookio.app, el único producto con ese nombre relacionado con RAG): RAG por API para PDF,
  CSV, Markdown/TXT y web; sin Excel, PPTX ni SharePoint; no publica empresa ni alojamiento.
  [Oficial] <https://lookio.app/pricing>, [Comunidad] <https://www.producthunt.com/p/lookio>. Descartado.

## 3. pgvector frente a Qdrant

**Seguir con pgvector** (la app) y con SQLite + NumPy (la herramienta de desarrollo: ~9.500 × 768 floats,
unos 29 MB, comparación exacta instantánea).

- pgvector 0.8.7 (01/10/2026) es la última; la CVE-2026-3172 se corrigió en 0.8.2. [Oficial]
  <https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md>
- Umbral para salir de Postgres: sin consenso, entre 1 M y 5–10 M de vectores o > 100 consultas/s.
  [Proveedor/Comunidad] <https://encore.dev/articles/pgvector-vs-qdrant>
- La crítica más citada («The Case Against pgvector», HN) admite que con miles de documentos basta el
  recorrido secuencial. [Comunidad] <https://alex-jacobs.com/posts/the-case-against-pgvector/>
- `ts_rank` de Postgres no es BM25; si la evaluación lo pide, probar pg_textsearch 1.0 (03/2026).
  [Proveedor] <https://tigerdata.com/blog/pg-textsearch-bm25-full-text-search-postgres>
- Recomendación práctica: un `tsvector` `spanish` para el texto y otro `simple` para identificadores
  (N170, I-003), que el stemming estropearía.

## 4. Lectura de documentos: Docling, Azure Document Intelligence y visión

- **XLSX/CSV**: ningún parser genérico distingue fórmulas `RAND()`, cachés ausentes o PDF con extensión
  XLS; la biblioteca es superior.
- **PDF nativo y PPTX**: Docling (MIT, local) bastaría; el texto de los PPTX ya se extrae.
- **Globos de ~9 px** (planos escaneados como el del 3212): detectar los círculos (OpenCV), recortar,
  ampliar y leer con un modelo de visión **restringido a los N-numbers posibles** de esa revisión; auditar
  una muestra. Un pipeline YOLO + VLM llega a ≈ 93,5 % F1 en 1.367 planos [Benchmark]
  <https://arxiv.org/pdf/2506.17374>; los modelos generales sin ajuste inventan datos GD&T [Benchmark]
  <https://arxiv.org/pdf/2411.03707>. Azure DI `ocrHighResolution` está pensado para texto pequeño en
  planos A1–A3 [Oficial] <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/add-on-capabilities?view=doc-intel-4.0.0>.
- **Zonas rojas de las diapositivas**: primero lo determinista (formas DrawingML con contorno rojo: color,
  geometría y caja con python-pptx); después, recorte + descripción corta del modelo de visión,
  guardada como «generada, sin verificar». Propuesta propia, no de una fuente.
- Benchmarks de OCR de documentos: ParseBench (04/2026) concluye que «ningún método es
  consistentemente fuerte en las cinco dimensiones» [Benchmark] <https://arxiv.org/abs/2604.08538>;
  olmOCR-Bench sitúa a olmOCR 2 en 82,4 y a Mistral OCR (03/2025) en 72,0 [Benchmark]
  <https://arxiv.org/pdf/2510.19817>.
- Precios: Mistral OCR 3, 2 $/1.000 páginas [Oficial] <https://mistral.ai/news/mistral-ocr-3>;
  LlamaParse 1,25 $/1.000 créditos [Oficial] <https://developers.llamaindex.ai/llamaparse/general/pricing/>.
  Azure DI: la página oficial no mostró las cifras (sin verificar).

## 5. RAG agéntico

- En la app, con `qwen3.5:2b` en CPU: **enrutado determinista**, una o dos llamadas a herramientas y
  cifras presentadas por el backend (lo que ya hace). Los modelos de 1–3B valen para una llamada, no para
  cadenas [Comunidad] <https://www.promptquorum.com/power-local-llm/best-local-models-tool-calling-2026>;
  sustituir el bucle agéntico por llamadas directas redujo la latencia p50 un 62 % en un sistema real
  [Benchmark] <https://arxiv.org/html/2607.08010v1>.
- El bucle buscar → reflexionar tiene sentido en un cliente potente (Claude Code, nube, Copilot), con
  presupuesto de pasos.
- Diseñar pocas herramientas, sin solapes, con respuestas compactas que devuelvan identificadores.
  [Oficial] <https://www.anthropic.com/engineering/writing-tools-for-agents>
- MCP se donó a la Agentic AI Foundation (Linux Foundation) el 09/12/2025; lo admiten Copilot, ChatGPT,
  VS Code y otros. [Oficial] <https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation>

## 6. GraphRAG

- El grafo del dominio es explícito: pieza → feature → cota (por plano y revisión) → medición (muestreo,
  cavidad) → corrección. Son tablas con claves; se recorren con SQL (CTE recursivas si hace falta) y se
  exponen como herramientas (`historial_cota(pieza, cota)`). Un LLM, como mucho, **propone** vínculos
  para revisión humana.
- GraphRAG-Bench (ICLR 2026): en muchas tareas rinde peor que el RAG normal y solo mejora con modelos
  grandes (de 3B a 14B). [Benchmark] <https://arxiv.org/abs/2506.05690>
- Coste de indexación de LightRAG: fuentes contradictorias (757 M frente a 62 M de tokens en un
  benchmark [Benchmark] <https://arxiv.org/pdf/2605.05643>; «igual que un RAG vectorial» en blogs).

## 7. RAG, SQL o híbrido

**Sí, nuestro caso es híbrido, y en tres capas**: documentos (PPTX, DOCX, correos) → búsqueda;
cifras → consultas controladas; conocimiento curado (fichas y hallazgos) → lectura directa.

- Texto → SQL: BIRD 82,95 % frente a 92,96 % humano; Spider 2.0 con esquemas de ~800 columnas, 21,3 %
  [Benchmark vía fuente secundaria] <https://dbschema.com/blog/tools/text-to-sql-tools-and-when-to-trust-them/>;
  los propios benchmarks tienen errores de anotación del 52,8 % (BIRD Mini-Dev) y 62,8 % (Spider 2.0-Snow)
  [Benchmark, v3 del 19/01/2026] <https://arxiv.org/abs/2601.08778>. *(Corregido el 28/10/2026: decía 66,1 % y
  «BIRD» sin precisar.)*
- Capa semántica (consultas con nombre): 98–100 % en lo cubierto frente a 84–90 % generando SQL con el
  esquema completo, y se niega ante lo no cubierto [Proveedor, dbt]
  <https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026>.
- El SQL libre queda para el agente de desarrollo, con solo lectura, límites y vistas sin celdas
  aleatorias. La vía `rag.py exacto sql` ya aplica un autorizador de solo lectura.

## 8. Microsoft Copilot Studio / Microsoft 365 Copilot

**Canal sí, motor de cifras no.**

- Conocimiento subido desde SharePoint: se copia a Dataverse, se sincroniza cada 4–6 h, ≤ 500 objetos;
  **los ficheros etiquetados *Confidential* o *Highly Confidential* no dan respuesta**. [Oficial]
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-unstructured-data>
- Excel: *«To search over Excel file content, use code interpreter instead of semantic search. Semantic
  search has limitations for cell indexing.»* (code interpreter en preview, 16 MB y 10 ficheros).
  [Oficial] <https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-code-interpreter-structured-data>
- Retrieval API: ≤ 25 resultados, tablas solo de doc/docx/pptx, sin imágenes; semántica solo en
  doc/docx/pptx/pdf/aspx/one. [Oficial]
  <https://learn.microsoft.com/en-us/microsoft-365-copilot/extensibility/api-reference/retrieval-api-overview>
- Integración correcta: nuestro backend como **servidor MCP** dentro de un agente de Copilot Studio o
  como conector federado (identidad del usuario, sin indexar; exige licencia M365 Copilot) [Oficial]
  <https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/federated-connectors-overview>.
  Requiere un endpoint HTTPS accesible (p. ej. tras Azure API Management) con OAuth de Entra ID.
- Residencia: los entornos europeos usan Azure OpenAI en el EU Data Boundary; los modelos de Anthropic
  quedan fuera de esa frontera y vienen desactivados en la UE. [Oficial]
  <https://learn.microsoft.com/en-us/power-platform/admin/geographical-availability-copilot>
- Precios: paquete Copilot Studio 200 $/mes por 25.000 créditos; M365 Copilot 30 $/usuario/mes (anual)
  [Oficial] <https://www.microsoft.com/en-us/microsoft-365-copilot/pricing/copilot-studio>. Sin licencia,
  10 usuarios × 20 preguntas/día saldrían del orden de 500 $/mes (estimación del agente, suponiendo
  ~12 créditos por respuesta con dos herramientas; sin verificar cómo se cuentan las llamadas MCP).

## 9. Evaluación

- Medir antes de cambiar embeddings, reranker o grafos. Tres capas: **exacta** (cifras con resultado
  conocido; incluir casos en que hay que negarse: `RAND()`, dato ausente, N-number de otra pieza),
  **recuperación** (pregunta → fuente esperada; recall@k y MRR) y **narrativa** (juez con aprobado/suspenso
  calibrado con etiquetas de Eduard).
- Tamaño: con 100 preguntas y 90 % de acierto, el intervalo de confianza al 95 % es ±5,9 puntos; con 200,
  ±4,2 (aproximación binomial; agrupar por pieza). [Oficial, método]
  <https://www.anthropic.com/research/statistical-approach-to-model-evals>
- Los jueces automáticos discrepan entre sí (RAGAS 0,0 frente a DeepEval 1,0 ante la misma respuesta
  inventada en un experimento) [Comunidad]
  <https://dev.to/nickjlamb/we-gave-the-same-fabricated-answer-to-ragas-and-deepeval-one-scored-it-00-the-other-scored-it-10-57om>:
  preferir comprobaciones deterministas.
- **Aplicado**: `preguntas.jsonl` + `herramientas/evaluar_rag.py` (capa de recuperación) y
  `verificar.py --hallazgos` (capa exacta, 66 hallazgos con comprobación de rutas y SHA-256; 14 con SQL).

## 10. Mejoras de recuperación

- *Contextual retrieval* (Anthropic, 09/2024): −35 % de fallos con embeddings contextuales, −49 % con BM25
  contextual y −67 % con reranker, sobre una base del 5,7 %; la mejora depende mucho del dominio.
  [Oficial] <https://www.anthropic.com/news/contextual-retrieval>. Aquí ya se envía título + sección al
  modelo y al FTS: la versión determinista está hecha en buena parte.
- Reranker local (bge-reranker-v2-m3 o Qwen3-Reranker-0.6B) sobre los 30 primeros: medir con la
  evaluación y la latencia en CPU; los benchmarks en español se contradicen.
- Embeddings: EmbeddingGemma-300m 61,15 en MTEB (Multilingual, v2), media por tarea a 768 dimensiones
  [Oficial, ficha del modelo] <https://huggingface.co/google/embeddinggemma-300m-qat-q8_0-unquantized>, frente a
  Qwen3-Embedding-0.6B 64,33 [Benchmark] <https://arxiv.org/pdf/2506.05176>. *(Corregido el 28/10/2026: el artículo
  de Qwen3 es anterior a EmbeddingGemma y no contiene su cifra.)* Cambiar solo si la evaluación muestra fallos semánticos
  (recalcular cuesta ~2,5 h en este equipo).

## Lo que se aplicó el 27/10/2026

Ver [README de esta carpeta](README.md): glosario multilingüe, peso de las tarjetas de hoja, evaluación
reproducible y sus resultados.

## Sin verificar o contradictorio

Precio del SQL estructurado de Bedrock y si su parser lee PPTX; precios oficiales de Azure DI; coste por
crédito de Copilot Studio y si una llamada MCP cuenta como acción; coste de indexación de LightRAG;
rerankers en español; empresa y alojamiento de Lookio; toda opinión de Reddit.
