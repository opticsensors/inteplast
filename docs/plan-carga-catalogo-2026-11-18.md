# Cargar las 21 piezas y los 8 features en la base de datos · plan

**Plan del 18 de noviembre de 2026. Carga completada el 19/11/2026.** Eduard la autorizó tras
comprobar las [portadas por pieza](plan-portadas-por-pieza-2026-11-18.md) en la instalación
local (commit `cd4ca0f`). La BD contiene las 21 piezas y los 8 features. Se vincularon 92 de
las 98 cotas de referencia. El detalle por pieza y revisión, los seis pendientes y la copia
previa constan en el [registro de ejecución](carga-catalogo-2026-11-19.md).

## Qué se quiere conseguir

La base de datos `app` de la instalación local tendrá las 21 piezas de `Exemples` y los 8 features
del catálogo, listos para enseñar a INTEPLAST. Hay dos orígenes de datos que **no se mezclan**:

| Qué | Cómo se rellena |
|---|---|
| **Ficheros de la pieza** (CAD, plano, escaneo, molde… y cuál es el principal) y **sus cotas y mediciones** | Solo con el algoritmo de la app: lo mismo que hace «Nueva pieza → seleccionar carpeta → Crear», y la lectura automática de datos. Prohibido elegirlos, corregirlos o completarlos con conocimiento del agente |
| Features (nombre y descripción), nombre, código, descripción, familia y cliente de la pieza, vínculos feature ↔ pieza ↔ cota, advertencias y lecciones | Carga manual **autorizada expresamente por Eduard** (18/11/2026), tomada de `conocimiento/` y `docs/`. Sin dato documentado, el campo queda en blanco |

Esta separación cumple [AGENTS.md](../AGENTS.md): la carga manual son elecciones que Eduard ha
indicado expresamente y quedarán identificadas como tales (paso 9). No demuestran que el algoritmo
funcione. Si el algoritmo propone algo incorrecto (un plano equivocado, una cota mal leída), **se
conserva** y se anota como fallo, sin corregirlo a mano.

## Decisiones de Eduard (18/11/2026)

1. **Ejecución por API, con su usuario.** El agente llama a los mismos endpoints que el botón, en el
   mismo orden, actuando como Eduard (la app lee `Exemples` por SharePoint con su token delegado,
   `SHAREPOINT_ENABLED=true`). Si la sesión de Microsoft ha caducado, Eduard entra una vez en la web.
2. **Borrar el feature «Nervios»** (descripción «Paredes finas que unen dos partes para reforzarlas»
   y notas «Los nervios no pueden ser de espesor menor a 2mm», «No hay nada que añadir», «Sin
   comentarios aun»). Fue inventado. Se borra entero; después se crea «Nervios de Soldadura».
   El feature «Bolt Eye» y sus notas se conservan.
3. **Nombres de los features = nombre de su carpeta sin el número**, para que la app los proponga
   sola al elegir la carpeta (`suggested_features` de `POST /parts/discover`): «Bolt Eye»,
   «Clips en Piezas», «Nervios de Soldadura», «Paredes muy Delgadas», «Tetones», «Anclajes»,
   «Pockets», «Planitudes».
4. **Familia:** rellenarla con la mejor aproximación posible a partir de `conocimiento/`; en blanco
   solo si no hay base. INTEPLAST la cambiará después.
5. **Cliente:** rellenarlo cuando esté apuntado en los informes o documentos, asegurándolo todo lo
   posible; en blanco si no está claro. Crear los clientes que falten.
6. **Advertencias y lecciones:** solo las que estén documentadas en `conocimiento/` o `docs/` y sean
   interesantes. Si no hay, ninguna.

## Referencia de cotas por feature

Las cotas que forman cada feature ya están investigadas, revisadas por un segundo asistente y
contrastadas en los originales: **[conocimiento/cotas-por-feature.md](../conocimiento/cotas-por-feature.md)**
(commit `a5937cd`). Es la referencia de trabajo acordada
(«ground truth»). Resumen de lo que se cargará como vínculo feature ↔ cota:

| Feature | Piezas y cotas (rol) |
|---|---|
| Bolt Eye | 3212: N170, N117 (primary), N178 (reference), N288 (context). 3197: N230, N220. 3051: N880, N890 |
| Clips en Piezas | 3174: N712, N215, N216 (primary), N511 (context). 3186: N216 (primary), N1003 (reference), N215 (context). 3218: N2603, N2612, N2702, N2705, N2902, N2905 (primary); N2601, N2904, N500, N1906–N1912, N1910, N2501 (context). 3195: N3120. 3309: N15 (primary), N14, N16 (context) |
| Nervios de Soldadura | 3205: N17, N18, N19, N152 (primary); N62, N104, N154, N21, N3 (context). 3206: N64, N20, N21, N83 (primary); N6, N203 (context). 3214: N10, N12, N13 |
| Paredes muy Delgadas | 3237: N123 (primary), N116 (context). 3238: N148 (primary), N4010 (context). 3233: N520 |
| Tetones | 3288: N80, N30, N43. 3214: N6 (primary); N3, N4, N5, N7 (context). 3167: N500 (primary); N470, N490, N520, N540 (context) |
| Pockets | 3167: N1220, N2120, N2260, N2730, N2740, N1240, N1320, N1290 (primary); N1030, N1090 (context). 3056: N1200, N1230, N1231, N1210, N1330, N1310, N1311, N1290. 3202: N76, N79.1, N79.2, N79.3 |
| Planitudes | 3168: N230, N1330. 3205: N5. 3206: N9 |
| Anclajes | Sin piezas |

Reglas de traducción a la app (comprobadas en el código el 18/11/2026):

- **Roles.** La API solo admite `primary`, `reference` y `context`
  (`CharacteristicAssignment`, `backend/app/knowledge_models.py:139`). Correspondencia: principal →
  `primary`; referencia → `reference`; relacionada y funcional → `context`.
- **Código.** Debe cumplir `N<número>[.<subpunto de 1–3 cifras>]`, con prefijo de componente opcional.
  La lectura automática guarda las cotas con `N` (`N117`, comprobado en la BD). No se pueden vincular
  `F1`–`F3` del 3309, los `[]252`/`[]207` del 2820 ni subpuntos como `.T`: se vincula la cota base o
  nada.
- **Revisión.** Es obligatoria. Usar la revisión con la que la lectura automática guardó **esa misma
  cota** en esa pieza (en el 3197 es `3E1009447060`, en el 3212 `06`). Si la lectura no creó la cota,
  usar la revisión que la lectura asignó al resto de cotas de la pieza y anotarlo. Si la pieza no
  tiene ninguna lectura (2820, 3226), no vincular cotas.
- **Endpoint.** `PUT /api/v1/evidence/features/{feature_id}/parts/{part_id}/characteristics`
  (`backend/app/api/routes/evidence.py`). Crea la cota si no existe y añade el vínculo pieza–feature.
  Antes de usarlo, comprobar que la cota existe tras la lectura. Si no existe, anotarla como
  «sin medición» en el registro del paso 9.
- **No vincular** las candidatas del 2820 ni nada marcado como «candidata» en la referencia.
- **3212:** se conserva la **rev. 06** del seed (los nueve informes históricos citan la 06; la 07 es
  solo el plano de referencia para la presentación). Su N288 está como `primary` en el seed: pasarlo
  a `context` (es un ensayo funcional).

## Datos manuales de cada pieza

Fuentes: [identidad-piezas.md](../conocimiento/identidad-piezas.md) (cabeceras de los informes),
cabecera `CUSTOMER:` de los métodos de medida (`6- Método de medición/*_MM*.xls`), las fichas de
cada feature en `conocimiento/` y el cajetín de los planos.

| Pieza | Carpeta (relativa a `Exemples`) | Nombre | Familia (aprox.) | Cliente | Por qué ese cliente |
|---|---|---|---|---|---|
| 2820 | `0- Bolt Eye/2820 Pump Housing` | Pump Housing | Pump Housing | Bosch | Cajetín BOSCH del plano de 2016 (sin informes) |
| 3051 | `0- Bolt Eye/3051 Pump Housing` | Pump Housing VDA 12 mm | Pump Housing | Bosch | Descripción de medida de Bosch; los informes dicen `XXX` |
| 3197 | `0- Bolt Eye/3197 Pot` *(ya existe)* | Pot PCE2.0 | Pot | Bosch | Informes, 15 de 15 |
| 3212 | `0- Bolt Eye/3212 Pump Housing` *(ya existe)* | Pump Housing PAD2 FL | Pump Housing | Bosch *(ya puesto)* | Informes, 12 de 12; método «For: Robert Bosch» |
| 3174 | `1- Clips en Piezas/Tipo A/3174` | Bearing Plate STD | Bearing Plate | Autoliv | Informes 81/81 y método |
| 3186 | `1- Clips en Piezas/Tipo A/3186` | Bearing Plate LC2 | Bearing Plate | Autoliv | Informes 36/37 y método |
| 3218 | `1- Clips en Piezas/Tipo A/3218` | Bearing Plate R230 P2 SAMS | Bearing Plate | Autoliv | Informes 77/79 y método |
| 3195 | `1- Clips en Piezas/Tipo B/3195` | Brush Holder | Brush Holder | Bosch | Método firmado «For: Robert Bosch»; nº de pieza Bosch |
| 3226 | `1- Clips en Piezas/Tipo B/3226` | Manifold | Manifold | — | Sin dato |
| 3309 | `1- Clips en Piezas/Tipo B/3309` | Support Stopper | Support Stopper | Toyoda Gosei | Informes 13/13; método `TOYODA` |
| 3205 | `2- Nervios de Soldadura/3205` | Shroud, Water Pump 150 W | Shroud | Aisin | Método `CUSTOMER: AISIN` (V01–V05) |
| 3206 | `2- Nervios de Soldadura/3206` | Shroud, Water Pump 240 W | Shroud | Aisin | Método `AISIN`. El único informe con «B. Braun» es la plantilla del 3247 (I-303) |
| 3214 | `2- Nervios de Soldadura/3214` | Bottom Pencil Part | Bottom Pencil Part | — | Conflicto: informes «Lina Medical» (19/19), método «CLUNAS/STRYKER». En blanco hasta aclararlo |
| 3233 | `3- Paredes muy Delgadas/3233` | Isomask A Long - BDU34 | Insulation Mask | Bosch | Descripción de medida de Bosch; nº de pieza Bosch |
| 3237 | `3- Paredes muy Delgadas/3237` | Insulation Mask El. Side | Insulation Mask | Bosch | Informes 46/47 |
| 3238 | `3- Paredes muy Delgadas/3238` | Insulation Mask | Insulation Mask | Bosch | Informes 26/27 |
| 3288 | `4- Tetones/3288` | SOP RCP3.1 | — | B. Braun | Informes 10/10 y método `BBraun` |
| 3056 | `6- Pockets/3056` | Insulating Mask E-Side | Insulation Mask | Bosch | Informes 16/17 |
| 3167 | `6- Pockets/3167` | IPB1.1 Carrying Plate | Carrying Plate | Bosch | Descripción de medida de Bosch y documentos en alemán; informes con `XXX` |
| 3202 | `6- Pockets/3202` | Insulator, Motor, Water Pump | Insulator | Aisin | Método `CUSTOMER: AISIN` (V02–V05) |
| 3168 | `7- Planitudes/3168` | End Lamination | End Lamination | Bosch | Análisis enviado a Bosch (`_BOSCH`), ficha del feature |

- **No registrar** las carpetas que solo tienen un `Readme.txt` que remite a otra:
  `4- Tetones/3167`, `4- Tetones/3214`, `7- Planitudes/3205` y `7- Planitudes/3206`. Esas piezas se
  vinculan a su segundo feature a mano (paso 6).
- **Familia** = tipo de pieza según el nombre de los informes. Alternativa más agrupada, si Eduard la
  prefiere: «Aislamiento de motor eléctrico» para 3056, 3168, 3202, 3233, 3237 y 3238. 3288 queda en
  blanco: «SOP RCP3.1» no es un tipo de pieza.
- **Cliente «Bosch»:** ya existe en la BD con esa grafía. Se reutiliza; no se crea «Robert Bosch».
  Clientes nuevos: Autoliv, Aisin, B. Braun, Toyoda Gosei.
- **Nombre y código:** se registra con lo que proponga el botón (como haría el usuario). Después se
  sustituye el nombre por el de la tabla (autorizado por Eduard). Si el código propuesto no es el de
  cuatro cifras, se corrige y se anota como fallo del algoritmo.
- **Descripción de la pieza:** una o dos frases tomadas de la ficha del feature en `conocimiento/`
  (qué es la pieza y en qué feature aparece). Sin cifras que no estén allí.

## Descripción de los features

Tomarla de la sección «Qué es…» de cada ficha:

- **Bolt Eye:** se conserva la actual. Fuente: [0-bolt-eye](../conocimiento/0-bolt-eye/README.md).
- **Clips en Piezas:** se miden con la pieza montada. Fuente: [1-clips](../conocimiento/1-clips/README.md).
- **Nervios de Soldadura:** directores de energía que se funden al soldar el shroud. Fuente: [2-nervios-soldadura](../conocimiento/2-nervios-soldadura/README.md).
- **Paredes muy Delgadas:** paredes de 0,4 mm en máscaras aislantes. Fuente: [3-paredes-delgadas](../conocimiento/3-paredes-delgadas/README.md).
- **Tetones:** pines remachados o soldados y pines de los dientes. Fuente: [4-tetones](../conocimiento/4-tetones/README.md).
- **Anclajes:** se deja en blanco, porque la carpeta no trae piezas (I-501).
- **Pockets:** alojamientos numerados con paredes y fondos controlados. Fuente: [6-pockets](../conocimiento/6-pockets/README.md).
- **Planitudes:** planitud funcional del montaje. Fuente: [7-planitudes](../conocimiento/7-planitudes/README.md).

## Advertencias y lecciones propuestas

Solo registros documentados. Cada nota cita su fuente (ID de [hallazgos.jsonl](../conocimiento/hallazgos.jsonl)
o ficha) en el cuerpo y no afirma más que el registro: una propuesta de corrección no prueba que se
ejecutara.

| Feature | Tipo | Contenido (resumen) | Fuente |
|---|---|---|---|
| Bolt Eye | — | Se conservan las 10 notas actuales del seed | `seed_features.py` |
| Bolt Eye | lección | El diámetro salió inicialmente por debajo del objetivo y se corrigió por retoque: 3212 N170 de 3,429 a 3,974 (`.01`→`.03`); 3197 N230 de 3,784 a 4,073 (`.02`→`.03`) | H-001 |
| Clips en Piezas | advertencia | Las piezas con clips se miden montadas (clipadas); la condición libre/clipada forma parte de la medición | H-301 |
| Clips en Piezas | advertencia | 3309: corregir #9–#12 afecta a #24/#26/#27 y #14/#16 a la funcional #15; medir #15 con útil antes de modificar | W-3309 |
| Clips en Piezas | advertencia | 3174: el primer plan aplaza correcciones hasta resolver la deformación; correcciones distintas por cavidad y pin | W-3174 |
| Clips en Piezas | advertencia | 3186: corrección de la 202 distinta por cavidad; la 200 se ajusta por el ensayo de empuje | W-3186 |
| Clips en Piezas | lección | 3218: sobrecorrección de la 2210 y correcciones posteriores equivocadas; seguir la evolución por cota y conservar versiones | H-305 |
| Clips en Piezas | lección | 3195: los planes cambian de estrategia en 2360 y 2660; conservar la secuencia antes de reutilizar una corrección | L-3195 |
| Nervios de Soldadura | lección | Revisar las rebabas por nervio y cavidad tras cada intervención; el rediseño propuesto (postizos en nervios) no acredita su ejecución | H-401 |
| Nervios de Soldadura | lección | 3206: el matricero atribuye defectos al molde (descentramiento de 0,1 mm del núcleo, agujero central 0,03 mm mayor, electroerosión) | H-404 |
| Paredes muy Delgadas | advertencia | Antes de corregir acero, contrastar CMM/CT y acondicionamiento: en 3238 el plan 2 propone cambiar el programa CMM y la cota 169 se deforma al humidificar | [3-paredes-delgadas](../conocimiento/3-paredes-delgadas/README.md) |
| Tetones | advertencia | 3288: el remachado (DIM. 80) se controla con lupa y sin holgura pin–agujero; no tiene valor numérico | I-106 y [4-tetones](../conocimiento/4-tetones/README.md) |
| Pockets | advertencia | 3202: cotas no funcionales con propuesta de desviación; aumentar la cota 8 puede impedir el montaje; volver a medir antes de corregir | W-3202 |
| Pockets | advertencia | 3167: el cliente podía aceptar la desviación en los pockets 1 y 13, pero no es una concesión formal | H-602 |
| Planitudes | lección | 3168: Bosch no pudo montar la pieza en el paquete del estátor por colisión en el frente del diente; tras cortarlo, montaba | H-702 |
| Planitudes | lección | 3168: para la planitud (230/1330) se propuso pulir todo el lado de inyección; no consta que se ejecutara | H-703 |
| Anclajes | — | Ninguna | — |

## Pasos

0. **Preparación.**
   - Revisar el arreglo de Eduard.
   - `docker compose up -d --build db prestart backend` si cambió el backend.
   - **Copia de la BD** con `pg_dump` a una carpeta fuera de Git.
   - Comprobar que la sesión de Microsoft de Eduard es válida (una lectura de carpeta por API). No sobrescribir `.env`.
1. **Sesión de API como Eduard.** Crear un token de acceso de su usuario
   (`eduard.almar@eurecat.org`) dentro del contenedor del backend con la función de seguridad de la
   app. Todas las llamadas a `http://localhost:8000/api/v1` se hacen con él, para que Graph actúe con
   su token delegado. Script en el scratchpad, no en el repo.
2. **Borrar «Nervios»** con `DELETE /features/{id}` (hace falta superusuario o el dueño; si no basta,
   `admin@example.com`). Comprobar que desaparecen sus notas y su vínculo con 3212.
3. **Features.** Crear «Nervios de Soldadura», «Clips en Piezas», «Paredes muy Delgadas», «Tetones»,
   «Anclajes», «Pockets» y «Planitudes» con su descripción. «Bolt Eye» ya existe.
4. **Familias y clientes.** `POST /families` y `POST /customers` con los nombres de la tabla. Son
   idempotentes: un nombre existente devuelve el existente.
5. **Piezas nuevas (19), una a una, como el botón.**
   - `POST /parts/discover` con la carpeta. Si devuelve `existing_part`, no registrar.
   - Construir `files` **exactamente** como `discoveredFiles()` + `fileRequest()`
     (`frontend/src/components/Parts/pieceFileDrafts.ts`): la referencia de cada tipo como principal y,
     en planos, también los demás candidatos.
   - `POST /parts/register` con `code` y `name` propuestos, esos `files`, `feature_ids` =
     `suggested_features`, y además familia, cliente y descripción de la tabla.
   - `POST /parts/{id}/read-data`: «organizar por componentes antes de leer» queda desmarcado, como
     está por defecto. Esperar a que termine (`GET /parts/{id}/read-data`) antes de la siguiente.
   - Guardar el resultado de cada pieza: archivos elegidos, avisos y cotas leídas.
6. **Piezas existentes.**
   - **3212:** solo los campos manuales y el cambio de rol de N288.
   - **3197:** Eduard eligió el 19/11/2026 conservar la ficha y sus 125 cotas de partida,
     mantener su configuración de archivos (`files_managed = false`) y ejecutar «Actualizar datos».
   - Vínculos extra feature ↔ pieza con `POST /features/{id}/parts/{part_id}`: 3167 → Tetones;
     3214 → Tetones; 3205 y 3206 → Planitudes.
7. **Nombres y cotas.**
   - Ajustar el nombre de cada pieza con `PUT /parts/{id}` según la tabla.
   - Vincular las cotas de la referencia con las reglas de arriba, solo las que la lectura creó, con
     la revisión que la lectura usó.
8. **Advertencias y lecciones** con `POST /features/{id}/notes`, según la tabla.
9. **Registro de lo cargado.**
   - Escribir en `docs/` qué campos salieron del algoritmo y cuáles se cargaron a mano desde
     `conocimiento/`, con fecha.
   - Listar los fallos del algoritmo encontrados: plano principal dudoso, cotas de la referencia que
     no se leyeron, códigos o nombres propuestos raros, piezas sin datos.
   - Actualizar `docs/proximos-pasos.md`.
   - No corregir esos fallos a mano.

## Comprobación final

- **El catálogo:** 21 piezas y 8 features.
- **Ficha de cada pieza:** archivos con su principal (los que eligió la app), cliente y familia según la
  tabla, y estado de mediciones.
- **Ficha de cada feature:** sus piezas, sus cotas con rol y sus notas.
- **Contraste con la referencia:** el número de cotas vinculadas por pieza coincide con
  `cotas-por-feature.md`, menos las que la lectura no encontró (anotadas).
- **Base de tests:** intacta. Este trabajo no ejecuta tests contra `app`.

## Riesgos

- **Tiempo:** la lectura por Graph de 21 carpetas puede tardar horas. Las piezas grandes, como el
  3167 con 700 ficheros, pueden agotar el límite de lectura: se anota, no se fuerza.
- **Sesión:** si la sesión de Microsoft caduca a mitad, parar y pedir a Eduard que entre de nuevo.
- **Cotas no encontradas:** si la lectura no crea una cota de la referencia, se queda sin vincular.
  Vincularla crearía una cota sin medición que parecería un dato del algoritmo.
- **3288:** tiene base y tapa. Organizar sus componentes es una elección de Eduard en la app.
