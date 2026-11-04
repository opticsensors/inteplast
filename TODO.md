# TODO

titulo oficial: gestor de conocimiento de modificaciones de molde
*(04/11/2026: todavía no se usa; `PROJECT_NAME` y el `<title>` de la web siguen sin él. Pendiente decidir dónde va.)*

- [x] asistente: ollama run qwen3.5:2b --think=false
  *(04/11/2026: es el modelo por defecto y se envía `think: False`, `backend/app/assistant/providers.py`.)*
- [ ] test de preguntas para el asistente
  1. Busca el feature Bolt Eye. ¿Qué advertencias y lecciones aprendidas tiene registradas?
  2. En la pieza 3212, revisión 06, ¿qué mediciones y tolerancias hay para N170? Indica el muestreo, la cavidad y la fuente.
  3. que correcion tiene la n170 del bold eye de la pieza pump housing?
      La pieza Pump Housing (3212) no tiene el feature "Nervios" ni ninguna característica de refuerzo. El error indica que no existe un registro para esa descripción específica en la base de datos del sistema.

  *(04/11/2026: la pregunta 3 y variantes con erratas son tests de regresión automáticos
  (`backend/tests/api/routes/test_assistant.py`, `ORIGINAL_QUESTION`), con datos sintéticos y sin
  llamar al modelo. **Sigue pendiente** probar las respuestas completas con Ollama y los datos
  reales, con criterios de aceptación explícitos.)*

- [ ] solucionar que el molde tarda mucho en cargar, (pregunatr si realmente le sinetersa que se ueda ver en la web....)
  *(04/11/2026: sin tiempos medidos. En el acta del 24/09 XA quedó en consultarlo; alternativas: solo la cavidad o una imagen.)*

- [ ] añadir la foto de la pieza de verdad en ficheros vinculados a una pieza.
  *(04/11/2026: los tipos de archivo de pieza no incluyen foto; hoy se puede subir como «document».)*

- [ ] revisar `docs/preguntas-abiertas.md`: está bastante obsoleta. Contrastarla con lo que salga de
  `conocimiento/` (en especial `conocimiento/incongruencias.md`) tras leer todos los features de Exemples.
  *(04/11/2026: añadidas A17–A23 y una tabla que asigna cada una de las 31 incongruencias
  abiertas a una pregunta o explica por qué no se pregunta. **Pendiente: que Eduard valide la
  redacción** antes de enviarla; A18 solo si decide enviarla.)*

- [x] prueba de acceso a Exemples por Graph con Postman (Angel)
  *(Hecha antes de la reorganización de Exemples del 21/10: listó las cuatro piezas del Bolt Eye.
  El volcado de la sesión, con el código de autorización, se ha retirado de este fichero el
  04/11/2026; sigue en el historial de Git desde `a6f3b44`. El login de la app sustituye esa
  prueba: [SharePoint](docs/ficheros-externos.md#sharepoint-microsoft-graph).)*
