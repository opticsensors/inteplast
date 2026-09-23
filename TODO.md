# TODO

titulo oficial: gestor de conocimiento de modificaciones de molde

- [ ] test de preguntas para el asistente
  1. Busca el feature Bolt Eye. ¿Qué advertencias y lecciones aprendidas tiene registradas?
  2. En la pieza 3212, revisión 06, ¿qué mediciones y tolerancias hay para N170? Indica el muestreo, la cavidad y la fuente.

- [ ] Trazabilidad en mediciones: en pieza en el apartado de cotas/mediciones nos interesa que q al pasar el raton por puntos del garfico salga la info de estos, eso ya pasa y funciona bien, sale la cavidad y el valor y si algunos estan solapados salen en esa ventana todos, lo que quiero ahora es que al mover el cusor del punto esta ventana desaparece, como es de esperar pero yo quiero que si clicko el punto (o conjunto de ellos si estan solapados) esta ventana se retenga que pueda mover el cursor en ella y clickar su valor que muestra y que al clickar me lleve a una nueva pagina parecida a la que me lleva cuando clicko plano 2d y que en esta ventana tmb haya un buscador que por defecto salga lo que se tiene que buscar para encontarr ese valor en el csv o excel o lo que sea. y debajo el buscador salga el ficher raw de donde se ha sacado.

- [ ] se puede hace lo mismo en correciones una vez hecho el punto de abjao: 
      - quiero cambiar la subtarjeta correciones por algo mas parecido a la grafica de mediciones, que salgan en el eje x los dos intern del bloque seleccionada arriba en mediciones y que en el primero salga el original y en el segundo punto de x algan perdiccion (si la hay) y medicion y que tmb haya misma leyenda con las cavidades debajo y que al pasar el raton tmb muestres su valor y su variacion y lo que es: prediccion o cambio medido, y importante que mantenga Cambio propuesto en el molde
La acción plantea usar expulsores de 4 y esperar a revisar la posición. El Excel calcula una previsión de +0,500 mm para las evaluaciones del diámetro. si lo hay, si no lo hay ponerlo brevemente, No hay una acción vinculada a N178.



- [x] Problema: en la tarjeta de pieza por ejemplo la de pot, por defecto antes de buscar ni una cota me sale debajo del buscador: el listado de la s cotas, esto lo vo feo e inecesario. yo quiero que me salga el grafico que sale cuando clicko por ejemplo la cota n170, per sin rellenar ni sin leyenda. ni sin Elemento B1, Altura 1,5 mm, Evaluación GX
ya que aun no hemos seleccinado cta, pero quiero que el grafico con sus dimebnsiones iguales aparezca sin rellenar ni sin numeros en el eje y (en l x si no? porque ya sabra cuantos intern hay, y si en una cota hay menos o mas se ajusta en el momento)


- [ ] solucionar que el molde tarda mucho en cargar, (pregunatr si realmente le sinetersa que se ueda ver en la web....)

- [ ] añadir la foto de la pieza de verdad en ficheros vinculados a una pieza. 


- [ ] quiero consistencia entre features (tarjeta buena y que no tiens que modificar) y pieza (tarjetas que tienes que cambiar, especialmente la parte de edicion, que flojea un poco)
Al darle a nueva fature se me abre una nueva ventana con una tarjeta de feature vacia, y con mini titulos encima los rectangulos vacios que me dicen que va alli. titulo, descripcion, tags, etc. (eso no pasa en la tarjeta de pieza...)

quiero que nueva pieza haga lo mismo. pero pieza requiere de un paso previo: sleccionar la carpeta donde se encuentran todos sus datos. 
Sin esa carpeta no se pueden cargar sus ficheros (por defect y de forma automatica con posibilidad de cambio) ni tampoco se pueden cargar las mediciones y correciones!
por eso en vez de una modal que es cutre creo que es mejor llevar al user, como havce nueva feature, a un pagina nueva que hay que definir.

harias una que primero me salga un boton con seleccionar carpeta de lapieza y me permita seleccionarla como pasaba en la modal, y que una vez hecho me seleccione un nobre por defecto (el de la carpeta, con poss de editarlo) y me sleccione los ficheros asociados a la pieza (cad, escaneo etc) y que luego o al mimso momento tmb me leea las mediciobnes/cotas/correcciones etc?

o harias como featres y que crear pieza me lleve a una tarjeta de pieza pero vacia y esperando a ser rellenada? y que alli de algina manera aparezca la opcion de seleccionar la carpeta/ cargar sus fichers/obetner as mediciones y correcciones etc? 

que opcion te gusta mas y es mejor en mi caso?









