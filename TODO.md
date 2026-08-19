# TODO

- [ ]

- [ ] la tabla siguiente que hay en la gui: 
Pieza	Molde	CAD	Escaneo	Plano	Moldflow
3212
Pump Housing
vamos a planear antes de cambiar nada del codigo.

La tabla de piezas ejemplo de, por ejemplo, el feature bolt eye o de cualquier otro feature, no me acaba de gustar cómo está diseñado. Es un poco fuera de lugar, ¿no? En comparación con todo lo demás, en mi opinión. No solo esto, sino que los iconos que aparecen en cada celda no pegan mucho, además no los puedo clicar, no acabo de ver el sentido de esto. La idea es que el usuario los pueda clicar y se abra el programa pertinente que permite abrirlos. Esto no sé si puedes hacerlo. Y también quiero que cambies el diseño, y para cambiar el diseño, en vez de una tabla, quiero que pongas esos desplegables, igual que están en piezas de ejemplo, y los subdesplegables dentro del desplegable piezas de ejemplo.

Los subdesplegables tienen que ser, en este caso, el nombre de la pieza, como es el caso de 3212 Pump Housing. Y al clicar este subdesplegable, dentro tienen que aparecer en una lista o bullet point o alguna forma que tú creas que quede bien, los nombres de, bueno, los ficheros, nombres, lo que sea, correspondientes al molde, CAD, escaneo, plano y mold flow. ¿Cómo lo ves?




## Seleccionar features sobre el CAD / plano (decidir enfoque)

Preguntas abiertas
- [ ] ¿Con que fichero se marca la zona de un feature: plano 2D, STL, o STP de la pieza?
- [ ] ¿Marcar sobre imagen 2D (captura/recorte) o sobre el 3D interactivo?
- [ ] ¿Hace falta seleccion "tipo SolidWorks" (cara/arista/punto) o basta con pintar una region?
- [ ] ¿Se quiere autodeteccion de features (todas las caras cilindricas O4 -> Bolt Eye)?
- [ ] ¿Pedir a INTEPLAST/Bosch el CAD con PMI (STEP AP242) o damos por hecho que no lo hay?

Hechos que cierran opciones (ya comprobados)
- [ ] STL = solo triangulos, SIN topologia: no existe "la cara del agujero". Solo pintar/inferir region
- [ ] STL del 3212 = 4,9 M triangulos ~= 245 MB (50 B/triangulo) -> hay que decimar a 200-500 k + glTF/Draco (3-8 MB)
- [ ] .sldprt / CATPart: ningun visor web los lee. Convertir a STEP, o API de SolidWorks en Windows
- [ ] El solido CATIA del 3212 no tiene arbol de features -> no se pueden "leer" los features del CAD
- [ ] STEP/IGES (B-rep) SI tiene caras/aristas/vertices con tipo (cilindro O4) -> es la unica via "tipo SolidWorks"
- [ ] STEP del molde = 247 MB: convertir siempre en el servidor, nunca servirlo crudo. Usar el STP de la pieza
- [ ] El plano 2D es un escaneo sin texto -> en 2D la via estandar es ballooning con OCR, no extraccion de texto

Soluciones por nivel de esfuerzo                                                                                - [ ] Nivel 0 (1-2 dias, recomendado empezargulos/poligonos + etiqueta N-number
      sobre captura del 3D o recorte del plano. Guardar coords normalizadas (0-1) + label, pintar con SVG sobre       Libs: Annotorious / react-image-annotapias.
      Fuente de imagenes ya existente: diapositivas de correccion de molde (zona en rojo), graficas de contorno,plano.
- [ ] Nivel 1 (1-2 semanas): visor 3D del STL decimado con three.js + @react-three/fiber + three-mesh-bvh (pickirapido).
      Clic -> raycast -> region growing por angulo entre normales (equivalente a la seleccion por tangencia de  SolidWorks).
      Guardar la pose de camara para generar la miniatura de la ficha automaticamente.                          - [ ] Nivel 2 (semanas, valor real): B-rep. js (OpenCascade en WASM) o OCCT en servidor
      -> malla separada por cara con id + tipo de superficie. Habilita seleccion persistente y autodeteccion de features.
      Alternativas de pago: HOOPS Communicator (seleccion por cara, estandar del sector),
      CAD Exchanger Web Toolkit, Autodesk APo selecciona por cuerpo, no por cara).
- [ ] Via 2D estandar del sector: ballooning (InspectionXpert/Ideagen, High QA, Net-Inspect, Discus).
      Caja sobre la cota + numero = N-number02. Con OCR y caja manual de respaldo.
      Encaja con el TODO ya existente de localizar y marcar una cota en el PDF del plano.
- [ ] Via 3D estandar del sector: MBD/PMI (Spso / PC-DMIS / Teamcenter.
      Requiere CAD anotado del cliente; hoy solo tenemos PDF escaneado rev. 07 -> descartado por ahora.

Decisiones de diseño que hay que tomar SI o SI antes de implementar
- [ ] NO guardar indices de triangulo ni de rtar o re-decimar el CAD.
      Guardar ancla geometrica: punto 3D + normal + radio de crecimiento, en coords de pieza con la alineacion de `6- Metode de mesura`.
- [ ] Modelar la seleccion como entidad propia de BD (p.ej. `zona_feature`: tipo 2D/3D, fichero origen, ancla,
N-numbers).
      Asi el mismo Bolt Eye puede tener caja en el plano + region en el STL + cara en el STEP, todas apuntando a N170.



# DONE

- [ ] make a data explorer python script that reads the 2d planos odf and extracts the text/ can locate where a certain text (cota name) in the pdf and mark it

- [ ] borra: Full Stack FastAPI Template - 2026 del pie de pagina de la web, no quiero que este ni ver el texto ni la linia que lo separa de lo de arriba. Tambien tienes que borrar el texto que aparece en la parte de arriba de la pestaña al abrirse y en la pestaña de ADMIN que sale Admin - FastAPI template cuando tendria que decir Admin - inteplast, como el dashborad o las features

- [ ] Bug: Solapamiento del header con el contenido al hacer scroll

Al hacer scroll hacia abajo en la página, la línea horizontal superior y el icono ubicado en la parte superior derecha se mantienen visibles y terminan solapándose con el contenido de la página, concretamente con los textos del contenido principal.

- [ ] eliminar cajas de features y admin que aparecen debajo la caja de resultados del dashboard, no quiero que este eso alli, ya se puede ir a features y admin des de la izquierda, es redundante.

- [ ] lo que me interesaria ver de cada feature es el numero de piezas en las que aparece, por ejemplo, el bolt eye aparece en la pieza 3212, pero debajo se indica todos los ficheros de pieza/molde/planos. Todos estos tienen en comun una cosa: el id de la pieza, esto es: 3212. en un futuro es posible que haya mas piezas, y como usuario me interesa ver rapido y visualmente que piezas son estas. esto por ahora no mpasas, se indican todos estos ficheros y leerlo es confuso, ya que se indican por su nombre el cual no es el mas intuitivo. Como se te ocurre mejorrar esto? habia pensado que agruparas de alguna forma para cada pieza cuantos de estos ficheros se tinene: pieza cad, pieza escaneada, molde, plano 2d,... y que de forma facil el usuario pueda verlo! 

antes de cambiar nada del codigo vamos a planear como hacer esto. 
Dime que opciones sencillas y limpias en la gui se te ocurren para hacer este cambio, hazme preguntas si tienes dudas!


- [ ] En el dashboard, mientras, en el dashboard se muestran varias features y yo lo que quiero es que cuando yo clico una de esas features, que se abra una ventana, la foto de la feature que aparece en esta ventana aparezca un poco más grande, porque de momento aparece muy pequeña en comparación el resto de la ventana. Entonces quiero que lo adaptes como tú creas al tamaño un poco más grande.

- [ ] Revisa si tiene más sentido que, al hacer clic en un feature de los resultados, se abra una página propia en lugar del modal actual. La idea es que el feature tenga más protagonismo y la experiencia se sienta más natural dentro de la web.

Valora cuál de las dos opciones ofrece una mejor UX y, si consideras que la página independiente es mejor, adapta la implementación actual para conseguirlo sin complicar innecesariamente el resto de la aplicación.

- [ ] Reorganiza el layout de la página del feature para que la información tenga una jerarquía más clara. Mantén la imagen a la izquierda y coloca a la derecha el título, la descripción, la categoría, los tags y el nombre de la pieza, intentando que esta información quede compacta y bien agrupada.

La organización debería ser similar a la de la tarjeta que aparece en los resultados al buscar ese feature, ya que ahí la distribución funciona bien: imagen a la izquierda y la información a la derecha. Usa una estructura parecida, reajustando libremente tamaños de imagen, textos y espacios para adaptarla a la página completa. Debajo de esta sección principal deberían quedar los Lessons Learned, Warnings y Example Pieces como contenido secundario.