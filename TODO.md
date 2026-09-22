# TODO

## Asistente de IA para consultar y transferir conocimiento

**Propuesta en discusión — 22/09/2026.** Explorar un asistente con LLM local como entrada
principal a la etapa 1 de la [hoja de ruta](docs/hoja-de-ruta.md). Aprovechar el backend
actual como fuente de datos y conservar las fichas, tablas, gráficas, planos y visores CAD
como recursos que el asistente pueda mostrar o abrir. La decisión de reducir la navegación
de la GUI dependerá de la prueba con usuarios. Este bloque es planificación, no funcionalidad
implementada ni una decisión cerrada de modelo o infraestructura.

### 1. Prueba inicial y experiencia de uso

- [ ] Preparar un piloto de consulta sobre el 3212 con preguntas reales de INTEPLAST:
      qué vigilar al diseñar un Bolt Eye, qué problemas hubo, qué se propuso, qué se midió
      después y qué sigue sin confirmarse.
- [ ] Ofrecer respuestas con fuentes y enlaces al caso, archivo, hoja/celda, diapositiva
      o medición correspondiente. Poder abrir desde el chat las vistas actuales.
- [ ] Mostrar tablas y gráficas cuando ayuden a comparar, reutilizando los componentes
      existentes y los datos del backend.
- [ ] Comparar con trabajadores la consulta por chat y la GUI: exactitud, tiempo para
      encontrar la respuesta y facilidad de comprobarla.

### 2. Funciones del backend accesibles al asistente

- [ ] Definir un conjunto pequeño de herramientas con argumentos validados. Nombres
      orientativos: `buscar_features`, `consultar_experiencias`, `obtener_mediciones`,
      `comparar_muestreos` y `abrir_documento`.
- [ ] Reutilizar los servicios y endpoints existentes; añadir consultas específicas cuando
      falten. Entregar resultados acotados en JSON o texto, con identidad y procedencia.
      Conservar pieza, revisión, muestreo, cavidad, evaluación, elemento, altura y unidades
      cuando sean aplicables. No enviar el estudio completo para cada pregunta.
- [ ] Resolver filtros, tolerancias, diferencias, recuentos y comparaciones numéricas con
      código del backend. El modelo selecciona la consulta y explica su resultado; los
      argumentos también deben comprobarse para evitar consultas al contexto equivocado.
- [ ] Para preguntas exhaustivas (p. ej. «todas las evaluaciones fuera de tolerancia»),
      recorrer el conjunto completo solicitado; indicar cobertura, ausencias y paginación.
      Los primeros resultados de una búsqueda documental no garantizan exhaustividad.
- [ ] Aplicar la autenticación y los permisos del usuario en cada herramienta y recuperación.
      Empezar con consultas de solo lectura y mantener el acceso a fuentes a través del backend.
- [ ] Gestionar resultados vacíos, contexto ambiguo y fallos de herramientas: pedir la pieza
      o revisión que falte y explicar qué no se ha podido comprobar.

### 3. Búsqueda documental y embeddings

**Qué son:** un modelo de embeddings transforma un texto en una lista de números que
representa aspectos de su significado. Comparar esas listas permite recuperar textos
relacionados aunque no compartan las mismas palabras. Ejemplo a validar: «agujero de anclaje»
y «Bolt Eye». Esa similitud no demuestra que dos diseños sean equivalentes ni que una
afirmación sea correcta. Generar embeddings no entrena el LLM ni sustituye los originales.

- [ ] Medir primero la búsqueda por identificadores y texto, con vocabulario y alias del
      dominio. Añadir embeddings si mejoran la recuperación de preguntas reales.
- [ ] Preparar fragmentos coherentes de warnings, lecciones, métodos y correcciones:
      preservar el contexto necesario para interpretar cada acción. Markdown/texto para
      contenido narrativo y JSON para resultados estructurados, generados desde las fuentes.
      Evitar mantener una segunda base de conocimiento manualmente en Markdown.
- [ ] Conservar por fragmento su identificador, fuente/localizador, versión o hash y
      contexto de pieza/revisión. Diferenciar una lección validada de una propuesta o
      interpretación pendiente. Mantener acceso al documento y a las imágenes relevantes.
- [ ] Elegir y probar un modelo local de embeddings con castellano, catalán e inglés y
      terminología técnica. Usar el mismo modelo y versión para documentos y preguntas.
- [ ] Evaluar `pgvector` en el PostgreSQL existente para guardar y consultar los vectores.
      La instalación de la extensión y la migración quedan pendientes; no se ha añadido.
      Para el piloto, priorizar sencillez y medir antes de elegir un índice aproximado.
- [ ] Al consultar: convertir la pregunta en un embedding, aplicar los filtros y permisos,
      recuperar fragmentos similares y combinarlos con búsqueda textual/exacta. Entregar
      al LLM los fragmentos seleccionados junto con sus fuentes para construir la respuesta.
- [ ] Actualizar el índice al crear, editar o retirar contenido; impedir que una versión
      obsoleta se presente como vigente. Conservar versiones históricas consultables con
      su contexto. Si cambia el modelo de embeddings, regenerar los vectores afectados.
- [ ] Comparar búsqueda textual frente a búsqueda híbrida con las mismas preguntas;
      comprobar especialmente IDs como N170 y diferencias de revisión o tolerancia.

### 4. Modelo local y arquitectura

- [ ] Concretar GPU/memoria, usuarios simultáneos y latencia aceptable. Valorar un servidor
      dentro de INTEPLAST compartido por los usuarios.
- [ ] Probar modelos existentes capaces de usar herramientas; elegir por resultados sobre
      nuestras preguntas. Ollama o llama.cpp son opciones a evaluar para ejecutarlos.
- [ ] Mantener configurables el modelo y su servidor para poder compararlos sin rehacer
      las consultas del backend. Empezar sin entrenamiento específico del LLM.
- [ ] Si se requiere operación local, mantener también embeddings, recuperación y
      procesamiento de documentos dentro de la infraestructura acordada.
- [ ] Tomar «Copilot estándar» solo como referencia de experiencia/capacidad deseada.
      Copilot es un producto con distintos modelos y modos; no identifica un único modelo
      descargable ni acredita que un modelo local ofrezca la misma fiabilidad.

### 5. Fiabilidad y evaluación

- [ ] Preparar unas 20–40 preguntas iniciales con respuestas y evidencias revisadas por
      un experto. Incluir sinónimos, comparaciones, datos ausentes, contradicciones,
      revisiones antiguas, preguntas ambiguas y preguntas que no se puedan resolver.
- [ ] Usar N170 como caso de control: separar GX y LP máximo por agujero/altura/cavidad;
      una mejora de GX no demuestra conformidad completa ni aceptación del cliente.
- [ ] Separar en la respuesta hechos documentados, cálculos, inferencias y recomendaciones.
      Conservar la diferencia entre propuesta de retoque, previsión, ejecución confirmada
      y resultado medido. Pedir contexto antes de trasladar una solución a otra geometría.
- [ ] Medir por separado recuperación de evidencia, elección de herramienta y argumentos,
      exactitud numérica, cobertura de la respuesta, apoyo real de las citas y reconocimiento
      de información insuficiente. Añadir tiempo de respuesta y utilidad para el trabajador.
- [ ] Repetir preguntas con formulaciones distintas y reservar casos para evaluar cambios.
      Acordar criterios de aceptación con INTEPLAST y ampliar la muestra antes de generalizar.
      Una demo o un porcentaje sobre pocas preguntas no certifica fiabilidad en producción.
- [ ] Registrar errores y corregir su origen (datos, búsqueda, herramientas o modelo).
      Las citas, el RAG y el uso de funciones ayudan a comprobar respuestas, pero no
      garantizan que la interpretación final sea correcta.
- [ ] Mantener las recomendaciones nuevas como propuestas revisables. El cálculo de un
      retoque para una geometría nueva y la predicción de contracciones requieren reglas
      o modelos adicionales de las etapas 2 y 3.

### 6. Captura y edición de conocimiento después del piloto de consulta

- [ ] Explorar que un trabajador relate un caso y el asistente prepare una ficha,
      preguntando por contexto, actuación, resultado y evidencia que falten.
- [ ] Permitir proponer cambios a warnings y lecciones mediante funciones del backend,
      mostrando el cambio para revisión y guardado por el usuario. Conservar autoría y fuentes.
- [ ] Evaluar la edición por conversación y por formularios antes de decidir qué pantallas
      simplificar. Medir estas operaciones separadamente de la consulta.

### Referencias técnicas de la propuesta

- [Ollama: uso de herramientas](https://docs.ollama.com/capabilities/tool-calling).
- [Ollama: embeddings](https://docs.ollama.com/capabilities/embeddings).
- [pgvector: búsqueda vectorial e híbrida en PostgreSQL](https://github.com/pgvector/pgvector).
- [Microsoft Copilot Chat: selección de modelos](https://learn.microsoft.com/es-es/copilot/overview).
