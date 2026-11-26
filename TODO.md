# TODO

NEW todo humanly made:

- queiro que tu como modelo llm hagas lo siguiente (puedes create herramientas python on prototipos para ayudarte a hace rla tarea): ir pieza a pieza y dibujar (colorear las zonas que tu crees que correposnden al feature) entonces actualizarias tu cada caption/portada/minuatura de los features de modo que cada uno de ellos muetre en rojo las caras que correpsonden a ese, igual que pasa con el bolot eye que hice yo manualomente. Podrias tu intenatr hacer eso? auqnue te equivoques haz una primera solucion. es sobretodo para ver como queda, y tambien apra hacer el siguiente apso ligado a eso: que cada pieza aparezca (con una opcion o no de desactivarlo, aun no lo tnago claro) con colores distintos y una letyenda que me diga una cierta pieza todfos los features coloreados en ella. de modo quie las fichas del feature olo muetran rojo, poruq eel feature es uno para cada una de susp piezas donde aparece, pero las fichas de pieza para una misma pieza peude haber varios features y puede ser ineteresante hacer que aparezcan en colores en los mkiniarutar y tamb al cliclakrals y amplicar en la modal. como lo ves? crees que puedes irt pieza a pieza yu en funcion de lo que sabes de los features por texto poder identificarlos y amrcar sus caras en los cads visualizados en la web? 

- el cuadrado del cad de pieza en modo editar queda no alineado con el utlimo recatngulo de la derecha, el de descripcion... -> hacerlo ams grande para que queden alineados
- añadir rectangulo material y nuemro cavidades
- quitar los tags de pieza, y poner solo warnings, como ese no tiene mediciones, ese no tienen correciones, ese no teiene feature asociado, y qeue l warning sea como el color warning y con el icono, texto similar al de los tags coloridos, loq ue no se si encuiadrarlo rollo tag o no, 
 




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

- [x] revisar `docs/preguntas-abiertas.md`: está bastante obsoleta. Contrastarla con lo que salga de
  `conocimiento/` (en especial `conocimiento/incongruencias.md`) tras leer todos los features de Exemples.
  *(04/11/2026: añadidas y cerradas A17–A23, con una tabla que asigna cada una de las 31
  incongruencias abiertas a una pregunta o explica por qué no se pregunta. Listas para enviar
  después de A10; A18 solo si Eduard decide enviarla.)*

- [x] prueba de acceso a Exemples por Graph con Postman (Angel)
  *(Hecha antes de la reorganización de Exemples del 21/10: listó las cuatro piezas del Bolt Eye.
  El volcado de la sesión, con el código de autorización, se ha retirado de este fichero el
  04/11/2026; sigue en el historial de Git desde `a6f3b44`. El login de la app sustituye esa
  prueba: [SharePoint](docs/ficheros-externos.md#sharepoint-microsoft-graph).)*
