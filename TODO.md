# TODO

- [ ]

## Ficha del feature: la tabla «Piezas ejemplo» -> desplegables + visores

> Planeado con el usuario el **2026-08-24**. **Nada de esto estaba implementado** cuando se
> escribio este bloque: la ficha seguia con la tabla. Leer entero antes de tocar codigo, y leer
> tambien el bloque siguiente (**donde viven los ficheros**): las dos cosas se cruzan.

**El encargo, en sus palabras:**

> «La tabla de piezas ejemplo, de por ejemplo el feature Bolt Eye, no me acaba de gustar como
> esta disenado. Es un poco fuera de lugar en comparacion con todo lo demas. Los iconos que
> aparecen en cada celda no pegan mucho, ademas no los puedo clicar, no acabo de ver el sentido
> de esto. La idea es que el usuario los pueda clicar y se abra el programa pertinente. En vez de
> una tabla, quiero esos desplegables, igual que estan en Piezas ejemplo, y los subdesplegables
> dentro. Los subdesplegables tienen que ser el nombre de la pieza, como 3212 Pump Housing, y al
> clicarlo, dentro, en una lista o bullet points, los ficheros de molde, CAD, escaneo, plano y
> Moldflow.»
>
> Y sobre los derivados ligeros: «reduce el tamano o lo que sea necesario para el display, pero
> **nunca modifiques el original**».

**Donde esta hoy el codigo**

- `frontend/src/components/Features/PartAssetMatrix.tsx` — la tabla de 6 columnas. Es lo que se
  sustituye (propuesta de nombre: `PartAssetList.tsx`).
- `frontend/src/components/Features/parts.ts` — `partRows()` **ya agrupa por pieza y por tipo**,
  incluido el grupo «sin pieza» de los adjuntos huerfanos. Se reaprovecha entero, no se toca.
- `frontend/src/components/Common/CollapsibleSection.tsx` — el desplegable de Warnings y Lessons.
  Se anida sin problema: `FeatureForm.tsx` ya lo anida en «Ficheros por pieza».
- `frontend/src/components/Features/FeatureForm.tsx` — 🔑 el modo **edicion** agrupa **por tipo**
  (un sub-desplegable por tipo, con las piezas mezcladas dentro). Si la ficha pasa a agrupar por
  pieza, los dos quedan invertidos. Decision pendiente, abajo.

**Decisiones ya cerradas con el usuario**

- [ ] 1. **Fuera la tabla.** «Piezas ejemplo» sigue siendo un `CollapsibleSection`, y dentro un
      **sub-desplegable por pieza** (`3212 · Pump Housing`), y dentro una **fila por fichero**,
      ordenadas por `ASSET_KINDS` (molde, CAD, escaneo, plano, Moldflow).
- [ ] 2. **Dentro de cada pieza, solo lo declarado.** Nada de cinco filas fijas con guiones: si un
      tipo no tiene adjunto, no sale. El checklist de lo que falta lo dan el contador de la
      cabecera del sub-desplegable (`5 ficheros · 2 subidos`) y las filas «sin fichero subido».
- [ ] 3. **La fila dice por adelantado que va a pasar** (*Ver* / *Ver en 3D* / *Descargar*) y, en
      gris debajo, el motivo cuando no hay visor: «necesita Moldflow Communicator», «demasiado
      grande para el visor». **Sin modal de aviso**: cansa a la tercera vez.
- [ ] 4. 🔴 **Nunca se modifica el original.** Los derivados ligeros (ver mas abajo) son ficheros
      **nuevos, en otra carpeta**; el original se ofrece siempre integro para descargar. El
      derivado es un extra, jamas un reemplazo.
- [ ] 5. Abierto por defecto si solo hay una pieza; cerrados si hay varias.

**Hechos comprobados el 2026-08-24 (no volver a investigarlos)**

- [ ] 🔴 **Por eso los iconos no se pueden clicar: no hay ningun fichero detras.** El seed crea
      los cinco adjuntos del Bolt Eye **sin fichero** (`backend/app/seed_features.py:148`, el
      comentario lo dice: los CAD del cliente no se copian al repo). La celda **con** fichero si
      es un boton de descarga (`PartAssetMatrix.tsx:44`); la que no lo tiene pinta el icono del
      tipo al 40 % y no hace nada. Diga lo que diga el diseno, eso hay que escribirlo con
      palabras en la interfaz.
- [ ] `MAX_UPLOAD_SIZE_MB = 50` en `backend/app/core/config.py:75`.
- [ ] `GET /files/{id}` ya sirve con `content_disposition_type="inline"`
      (`backend/app/api/routes/files.py:82`) -> el PDF se abre en pestana o se embebe **sin tocar
      el backend**.
- [ ] Tamanos reales del 3212 (de los `docs/3212/`): plano PDF **1,42 MB** · STEP de la pieza
      **10,06 MB** · escaneo STL **235,7 MB** (4,9 M triangulos) · STEP del molde **246,7 MB** ·
      Moldflow `.mfr` **184,2 MB** (binario cifrado, sin cabecera legible).

**Visores: que se puede y que no**

| Fichero | Visor en el navegador | Como |
|---|---|---|
| Plano PDF (1,4 MB) | ✅ trivial | `<iframe>` con el visor nativo + «abrir en pestana». Cero dependencias, el backend ya lo sirve inline |
| Imagen | ✅ trivial | Lo mismo |
| **STEP de la pieza (10 MB)** | ✅ **si, y es el que se quiere mirar** | STEP es B-rep (NURBS): hay que teselarlo. `occt-import-js` = OpenCascade en WASM (lo que usa Online 3D Viewer) lo hace **en el navegador**. Unos segundos con 10 MB |
| STL del escaneo (236 MB) | ⚠️ solo con derivado | `three.js` + `STLLoader` pinta 4,9 M de triangulos sin problema; lo inviable es **bajar 236 MB para un vistazo**. Ver derivados |
| STEP del molde (247 MB) | ❌ | Ensamblaje completo (placas, correderas, refrigeracion). Teselar eso en WASM no termina |
| `.mfr` (184 MB), `.sldprt`, `.CATPart` | ❌ imposible | Binarios propietarios. El `.mfr` esta cifrado desde el byte 0 (`docs/3212/7-moldflow.md`). Solo Moldflow Communicator |

🔴 **Lo que el navegador NO puede hacer, y no hay forma:** lanzar un programa del PC. Esta
prohibido, y ademas los bytes estan en el servidor, no en el disco del usuario. La secuencia real
es descargar -> abrir desde la barra de descargas -> Windows lo abre con su programa asociado. Un
clic de mas, y es el techo de una app web. Un `inteplast://` propio con un agente instalado en
cada PC lo resolveria, pero es otro proyecto y pasa por IT.

**Derivados ligeros (para el visor, nunca para sustituir)**

- [ ] El escaneo: decimar a 200-500 k triangulos y exportar glTF/GLB con Draco -> pocos MB, cabe
      de sobra en los 50 del backend. `open3d` / `pymeshlab` lo hacen en unas lineas y **ya estan
      instalados** en el Python 3.11 de la maquina. Ya estaba apuntado en
      `docs/3212/8-stl-pieza-real.md:112`.
- [ ] 🔴 El script va a `data-explorer/`, **lee el STL y escribe un GLB aparte**. No mueve, no
      renombra y no sobrescribe el original.
- [ ] Para el molde en STEP haria falta OCCT (no instalado). Se deja para mas adelante; el molde
      se queda en descarga.

**Como queda una pieza (mockup acordado)**

```
▾  3212  Pump Housing                                    5 ficheros · 5 subidos

   Plano      Plano 2D rev. 07      3212_rev07.pdf · 1,4 MB          [Ver] [⬇]
   CAD        Pieza 3212            ...AllCATPart.stp · 10,1 MB   [Ver en 3D] [⬇]
   Escaneo    Escaneo lote 315346   3212-315346-c13.glb · 6 MB    [Ver en 3D] [⬇]
   Molde      Molde completo        3212.step · 247 MB                    [⬇]
              demasiado grande para el visor
   Moldflow   Estudio reologico     3212.mfr · 184 MB                     [⬇]
              necesita Moldflow Communicator
```

**Pendiente de decidir antes de implementar**

- [ ] ¿Fase 1 (lista por pieza + visor de PDF/imagen, sin dependencias) y fase 2 (visor 3D)
      **juntas o separadas**? Recomendacion: juntas, porque separarlas obliga a rehacer la fila
      dos veces.
- [ ] ¿Limite del visor 3D en **50 MB**? Por encima, descarga y explicacion en la fila.
- [ ] ¿Se alinea el **formulario de edicion** (hoy por tipo) con la ficha (por pieza)? Ojo: el
      boton «Anadir fichero» vive hoy dentro de cada tipo, habria que replantearlo.
- [ ] `three.js` y `occt-import-js` con **`import()` dinamico**, para que el WASM (varios MB) solo
      se descargue cuando alguien abre un 3D, no al entrar en la app.
- [ ] Para ver esto funcionando hace falta **subir ficheros de verdad**: el plano PDF (1,42 MB) y
      el STEP de la pieza (10,06 MB), los dos LOCAL y seguros segun
      `docs/3212/1-pieza-2d-3d.md`. ¿Los mete el seed o se suben a mano desde la app?
- [ ] Al terminar: actualizar `docs/app-web.md` (tabla de componentes, seccion «Las tres casillas
      de la matriz», los cabos sueltos) y la linea 63 de `CLAUDE.md`, que habla de la «matriz
      pieza x tipo de fichero».

---

## Donde viven los ficheros: ¿los sube la app o solo los referencia?

> Discutido con el usuario el **2026-08-24**, sin implementar nada. Es la decision de
> arquitectura que **hay que tomar antes** de rehacer la ficha y antes de que haya datos reales
> cargados: separar «el adjunto» de «donde estan sus bytes» es barato ahora y carisimo despues.

**La pregunta de fondo: ¿la app es el archivo o es el indice?** Hoy es archivo: `StoredFile`
copia los bytes a `settings.UPLOADS_DIR` y `FeatureAsset` apunta a esa copia. Para los ficheros
gordos eso es duplicar el archivo CAD entero de INTEPLAST y mantenerlo sincronizado para siempre.

**Los numeros que lo fuerzan**

- [ ] `MAX_UPLOAD_SIZE_MB = 50` (`backend/app/core/config.py:75`) -> **hoy no se pueden subir** ni
      el escaneo (235,7 MB), ni el molde (246,7 MB), ni el Moldflow (184,2 MB). Si caben el plano
      (1,42 MB) y el STEP de la pieza (10,06 MB).
- [ ] **Solo el 3212 suma ~678 MB** entre esos cuatro. Con los cuatro proyectos ya son varios GB,
      y el archivo real de INTEPLAST son todos sus moldes, no cuatro.
- [ ] Encaja con la regla que ya esta en `CLAUDE.md`: los datos crudos del cliente **no se copian,
      se leen in situ**. Esto es lo mismo, pero para la app.

**🔴 El limite duro que descarta la solucion ingenua**

El navegador **no puede leer una ruta**. Ni `C:\...` ni `\\servidor\share\...`: una pagina
servida por `http://` tiene prohibido navegar o hacer `fetch` a `file://`, y no hay permiso que
lo abra. Asi que «guardar un path» solo puede significar una de dos:

1. La app **ensena la ruta como texto** y el usuario la pega en el Explorador. Cero
   infraestructura; cero previsualizacion, cero descarga, cero visor.
2. **El servidor** es quien ve esa ruta y sirve los bytes. Ahi funciona todo. Esta es la buena.

**Las cuatro opciones, en orden de coste**

| # | Opcion | Que da | Que cuesta |
|---|---|---|---|
| 1 | Guardar la ruta y ensenarla | Un boton de «copiar ruta» | Una tarde. Sin visor ni descarga |
| 2 | 🔑 **Carpeta montada en el backend en `:ro`** + ruta **relativa** a un `ASSETS_ROOT` configurable | Descarga por streaming, visor, derivados. Sin subida, sin copia, **sin el limite de 50 MB** | Poco codigo. Exige que el servidor vea los ficheros |
| 3 | Enlaces de comparticion de SharePoint/OneDrive | El visor web de Microsoft (PDF perfecto; 3D solo algunos formatos, STEP no) | Casi nada de codigo. Cada usuario necesita permiso, y mover una carpeta rompe todos los enlaces en silencio |
| 4 | **Microsoft Graph** (driveId + itemId, URLs de descarga temporales, miniaturas) | La version industrial de la 3, la unica que escala si el archivo vive en SharePoint | Registro de aplicacion en el tenant, OAuth, permisos `Files.Read.All`, y una conversacion con el IT de INTEPLAST o de Bosch |

**Recomendacion: hibrido.** No es todo o nada, porque los ficheros son de dos naturalezas:

| Que | Como | Por que |
|---|---|---|
| Imagen del feature, plano PDF, **derivados de visualizacion** (GLB) | **Subida**, como ahora | Son pequenos y el derivado **no existe en OneDrive: lo generamos nosotros** |
| Molde, escaneo, Moldflow, STEP de la pieza | **Referencia** | Copiarlos es duplicar el archivo de la empresa |

**🔑 Donde va a correr la app (respuesta del usuario, 2026-08-24)**

> «La app va a correr en un servidor de INTEPLAST, pero en desarrollo creo que puede que tenga
> que correr en un servidor de Eurecat.»

Consecuencias, que son las que mandan en el diseno:

- [ ] **En produccion (INTEPLAST) la referencia es el escenario ideal**: el servidor monta su
      unidad de red y sirve los ficheros donde ya estan.
- [ ] **En desarrollo (Eurecat) el servidor NO va a ver esa unidad.** Por eso la ruta guardada
      tiene que ser **relativa a un `ASSETS_ROOT` configurable por entorno**, nunca absoluta: en
      desarrollo se apunta a una copia de muestra (o a `Exemples` en local), en produccion a la
      unidad de INTEPLAST, y la BD no cambia.
- [ ] Un adjunto sin bytes accesibles **no es un error**: la ficha tiene que saber decir «este
      fichero esta referenciado pero este servidor no lo ve».

**Cambio de modelo propuesto (hacerlo antes de que haya datos)**

- [ ] `FeatureAsset` deja de tener solo `file_id`. Pasa a poder apuntar a **una de tres**: fichero
      subido (`StoredFile`), **ruta relativa** a `ASSETS_ROOT`, o manana un id de Graph. Con eso,
      pasar de la opcion 2 a la 4 no obliga a rehacer nada.
- [ ] Los metadatos que hoy da `StoredFile` (nombre, tamano, fecha) hay que poder tenerlos
      tambien del referenciado, cacheados: si no, cada pintado de la ficha va al disco.

**🔴 Trampas conocidas que aqui muerden**

- [ ] **OneDrive Files On-Demand**: un referenciado puede ser un *placeholder*. Leer un byte
      dispara la descarga completa y en los grandes **da timeout** (`CLAUDE.md`). El backend tiene
      que comprobar el atributo `0x400000` antes de abrir y la interfaz decir «en la nube, la
      primera descarga puede tardar».
- [ ] **Nombres inconsistentes** en carpetas y ficheros: normalizar con regex, nunca con match
      exacto. Y en `intern.05`, `c15/` y `c16/` llaman igual a sus ficheros -> **la cavidad se
      deriva de la ruta, nunca del basename**.
- [ ] Si un dia alguien reorganiza las carpetas de INTEPLAST, **todas las referencias se rompen a
      la vez**. Guardar tambien nombre y tamano permite al menos detectarlo y avisar.

**Pendiente de decidir / preguntar**

- [ ] ¿En que unidad y con que raiz van a vivir los ficheros en el servidor de INTEPLAST? (**esto
      es una pregunta para INTEPLAST**: si se les pregunta, moverla a
      `docs/preguntas-abiertas.md` con la evidencia).
- [ ] ¿El servidor de desarrollo de Eurecat tendra algun acceso, o se trabaja con una muestra
      local?
- [ ] ¿Se sube el limite de 50 MB para casos sueltos, o todo lo que pase de ahi va por referencia
      por definicion?
- [ ] ¿Los derivados ligeros se generan a mano con un script de `data-explorer/` y se suben, o se
      automatizan en el backend? (automatizarlo exige meter `open3d`/`pymeshlab` en la imagen
      Docker: pesa mucho, y para STEP haria falta OCCT, que no esta).

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