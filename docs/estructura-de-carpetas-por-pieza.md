# Preparación de las carpetas de pieza para INTEPLAST

**Documento de trabajo · 24/11/2026.** Sirve para preparar los cambios en las carpetas de las 21 piezas de `Exemples` y revisar el resultado con INTEPLAST. Los archivos citados son los que se han localizado. La decisión sobre cuál está aprobado corresponde al responsable de la pieza. Este inventario no es una lista de planos principales para cargar en la aplicación. **Es una propuesta abierta:** se ajustará con Eduard y con INTEPLAST antes de pedir ningún cambio.

## Decisiones de Eduard

1. **Planos y Cotas consultarán un solo origen de planos:** `1- 2D y 3D pieza`. El visor abre el PDF vigente de la pieza o del componente y conserva todas sus páginas. Usará el `.icp` si pertenece exactamente a ese plano y está junto al PDF. Cuando falte, el PDF se podrá abrir igualmente y la búsqueda aprovechará su texto o el OCR.
2. **Las revisiones anteriores se consultarán en SharePoint.** La carpeta del plano abrirá la ubicación del vigente. La carpeta con reloj abrirá el histórico de esa pieza. Al elegir otra revisión de **mediciones**, cambia la serie de Excel consultada y el visor sigue con el PDF vigente. Si se necesita ver dónde estaba una cota en el plano anterior, el usuario irá a SharePoint. Queda descartado el salto automático desde una medida antigua a un número del plano actual. La búsqueda manual en el vigente sigue disponible.
3. **Los Excel serán la única fuente de mediciones para este plan.** INTEPLAST puede aportar los informes Excel de manera habitual. Los CSV de máquina no están disponibles en todas las piezas. La preparación, la lectura y la validación de Cotas se harán a partir de los Excel, sin exigir CSV, mezclarlos con Excel ni recurrir a ellos para rellenar huecos. Los soportes ya entregados pueden conservarse como originales. Esta decisión actualiza, para este trabajo, la petición de Excel más CSV de la [reunión del 20/11](reunion-inteplast-2026-11-20.md). Describe el objetivo para la aplicación y las carpetas, no un cambio de software ya desplegado.

4. **El CAD del molde y el estudio Moldflow se abren con su aplicación de origen.** En la web local, ambos adjuntos tienen **Descargar original** junto al acceso a su carpeta de SharePoint. Cuando solo se identifica la carpeta, se puede abrir desde la ficha de la pieza. La captura es opcional y se guarda desde el lápiz. En consulta solo se muestra si ya hay una imagen guardada. INTEPLAST puede conservar su organización interna de los ficheros de molde. [Seguimiento del despliegue](proximos-pasos.md)

## Estructura propuesta

La **3212 Pump Housing**, de Bolt Eye, es la referencia por algo concreto: se distingue el plano de pieza, el STEP de producto y el STEP de molde. Su escaneo 07 funciona sin `.icp` y sus Excel identifican cavidades 13–16. Conviene conservar esa claridad. Para los nombres de carpeta propongo el esquema de las entregas más recientes. En Bolt Eye el Moldflow útil puede estar en la carpeta **7** y el STL en la **8**. Al preparar cada pieza se identifica el contenido por su función. [Comparación de los dos esquemas](../conocimiento/comparativa.md#esqueleto-del-3212-frente-al-nuevo)

```text
<código de pieza>/
  1- 2D y 3D pieza/
    <plano>_rev<revisión>.pdf
    <plano>_rev<revisión>.icp                 si existe el proyecto correspondiente
    <CAD de producto vigente>.stp
    Revisiones anteriores/
      <número de plano>/<revisión y, si hace falta, cambio>/
        <PDF de esa edición y su ICP si existe>
  2- Moldflow/
    <estudio disponible>
  3- Molde/
    <ficheros del molde tal como los organiza INTEPLAST>
  4- Metrologia/
    Interns/                                 informes <código>-<serie>_intern.NN, con su nombre actual
    Customer/                                copias enviadas al cliente
    Soportes/                                Excel que no son el informe del muestreo
  5- Retoques molde/
  6- Método de medición/
  7- Pieza real STL/
```

**Variantes que admite la propuesta.** Para varios componentes con plano propio, abrir una subcarpeta directamente bajo `1- 2D y 3D pieza` por ámbito, por ejemplo `Base`, `Tapa` y `Conjunto`. Cada PDF queda junto a su propio ICP. El CAD va en el ámbito que represente. Un PDF multipágina que ya constituye el documento aprobado se conserva entero. Si cubre varios componentes, identificar qué página corresponde a cada uno y resolver qué se va a publicar antes de duplicar archivos. En el histórico, el número de plano distingue los componentes. En Metrología, los Bolt Eye que tienen los informes en la raíz pueden seguir así; moverlos a `Interns/` es solo por orden.

**Dónde abrir cada carpeta.** Proponemos `1- 2D y 3D pieza/Revisiones anteriores/` como destino común del botón de carpeta con reloj. La carpeta del plano abre la ubicación del PDF vigente, que puede ser la raíz de Diseño o la carpeta de su componente. Al seleccionar planos vigentes y sus ICP, la app deberá excluir `Revisiones anteriores/` y todo su contenido, también cuando falte el PDF vigente. Acordar el nombre con INTEPLAST y probar ambos enlaces con una cuenta que tenga acceso. [Consulta A26](preguntas-abiertas.md#a26-revisiones-plano)

## Método 1. Preparar el plano de consulta

1. Inventariar los PDF y los proyectos ICP de diseño, Método y Retoques **durante la preparación**. Incluir los lazos de corrección aunque el nombre no contenga «plano», `DRW` o `ballooned`. En la app, la consulta se limitará a la carpeta de vigentes.
2. Identificar número de plano, pieza o componente, revisión, cambio o fecha del cajetín, estado de aprobación y páginas. Un nombre reciente, el mayor número, los globos o estar ya en diseño no acreditan la vigencia. Ante un borrador, cambio de referencia o dos candidatos sin resolver, anotar la pregunta para el responsable y dejar la publicación pendiente. Si falta un vigente identificable, la pieza puede conservar sus mediciones y quedar sin plano de consulta. Un PDF de Método, de Retoques o del histórico nunca cubre ese hueco en la app.
3. Para la edición aprobada, buscar primero el PDF numerado con su proyecto ICP. Contrastar número de plano, componente, edición, hoja y colocación de las marcas. Si hay varias copias, comparar su contenido y orientación. Conservar juntos el PDF y el ICP que se hayan podido emparejar. Si el ICP corresponde a otra revisión o su ajuste es dudoso, preparar solo el PDF vigente.
4. Sin ICP, usar el PDF aprobado de mejor calidad disponible para esa edición. El visor enseña el documento entero. La búsqueda solo puede localizar números que el lector reconozca en la capa de texto o en la imagen. Un plano sin numeración puede mostrar nominales y tolerancias y aun así carecer del identificador usado en el Excel. Pedir la versión aprobada numerada si se necesita esa búsqueda. La numeración del Excel o la de un plano anterior no se superpone al vigente. [Estilos de numeración observados](../conocimiento/planos-globos.md)

## Método 2. Ordenar las revisiones en SharePoint, pieza por pieza

La tabla sirve para preparar los dos destinos. **Diseño** significa la actual carpeta `1- 2D y 3D pieza` o su variante en Bolt Eye. **Método** y **Retoques** son las carpetas 6 y 5. Los números tras «PDF» son identificadores del [inventario con rutas, páginas y cajetines](../conocimiento/planos.md#inventario-de-los-pdf). Permiten localizar el original aunque haya copias de nombre parecido. Las entradas de histórico distinguen lo encontrado de lo que solo se conoce por el Excel o la tabla de revisiones.

| Pieza | Plano localizado y acción para Diseño | Histórico de esa pieza y decisión pendiente |
|---|---|---|
| 2820 | PDF 1, `0140S00050` 02, en Diseño junto al STEP. Mantener el PDF si sigue vigente. Lleva números en corchetes y carece de ICP. | Solo se localizó el 02. La tabla de cambios menciona el 01. Archivar ese PDF si se aporta. |
| 3051 | PDF 4, `0140S00275` 03, lleva `pendent acceptació` en Diseño. Pedir el aprobado y, si existe, el aprobado numerado. | Guardar el pendiente de aceptación como borrador identificado. Los Excel citan 01 y falta su PDF. |
| 3056 | PDF 3134, `0131S00135` 04, en Diseño. PDF sin numeración de cotas de informe ni ICP. Solicitar la copia numerada de la misma edición si existe. | Los Excel citan 01, 02, 03 y 04. Localizar los anteriores para el histórico. |
| 3167 | PDF 3294, `0130S00338` 07, es `DRAFT_V07`. Pedir el liberado. El globado 02 carece de ICP y pertenece a otra edición. | Método contiene el 02 (PDF 3968). Retoques, quinto lazo, contiene otro `D_07_DRAFT` (3958), distinto del de Diseño. Conservar los borradores distinguidos por cambio. |
| 3168 | PDF 4208, `0130S00337` 02, es `DRAFT_V02`. Pedir el liberado. El disponible carece de numeración de cotas y de ICP. | El 01 consta en los Excel. Pedir el PDF 01 y clasificar el borrador 02 por separado. |
| 3174 | PDF 582, `6494730_004`, de varias páginas con marcas «No.». Conservar todas las hojas. La revisión 004 figura en el nombre. | Los Excel citan 001, 002 y 004. Hay un 002 bajo 3186. Confirmar su alcance antes de incorporar una referencia al histórico de 3174. |
| 3186 | PDF 873, `6494730_002`, en Diseño. El STEP es `6541691` y el dibujo está identificado con la 3174. Pedir el plano propio o confirmación de plano compartido y edición aplicable. | Conservar la procedencia del 002. Resolver primero la identidad para clasificarlo como vigente, revisión anterior o referencia de familia. |
| 3195 | PDF 1381, `0130S0002K` 01, en Diseño. En Método hay un globado de **otro número**, `0130S1B006` 07, sin ICP. Confirmar el número vigente y su CAD. | Guardar las dos series por número. PDF 1537 es el 07. Falta el 09 de `0130S1B006` que citan los informes. En la cota 2360 incluso cambia el signo de la tolerancia inferior. |
| 3197 | PDF 126, `0140S00363` 02, en Diseño. Carece de números de cota como los del Excel y de ICP. Solicitar numerado de esa edición si existe. | Solo se localizó el PDF 02. Los informes expresan el cambio como `3E1009447060`. Conservar ese identificador. |
| 3202 | PDF 3993, `885253-11250` A, en Diseño, con globos. Su copia en Método (4078) es idéntica. **La A no tiene ICP correspondiente** en la entrega. Preparar PDF solo, con lectura de los globos. | Método/`Ballooned DRW` contiene estudio J, prototipo JT y producción G anterior, además de versiones de baja resolución y sus ICP. Archivar por dibujo, tipo y cambio. La G del nombre es el tipo de plano. |
| 3205 | PDF 1631 en Diseño es la B de **11/10/2023**. Método/`DRW ballooned/213137-10300-B_241028` contiene el PDF 1949 y el ICP 1946 de la B de **28/10/2024**. Contrastar el cambio aprobado y preparar juntos el PDF y su ICP si se confirma esa edición. | Separar estudio `213137-01030-10`, prototipos y ambas B por cambio. La B de 2023 tiene su pareja en `…-B_231011`. El nombre «B» solo perdería una edición. |
| 3206 | `3206.pdf` (2003) en Diseño es la B de **11/10/2023**. Método/`DRW ballooned/213137-10280-B_241028` contiene PDF 2208 e ICP 2205 de la B de **28/10/2024**. Verificar ese par contra la edición aprobada. | Separar la B de 2023 (`…-B_231011`), los prototipos y el estudio `213137-01028-10`. En la carpeta del estudio aparecen dos ICP distintos. Mantener sus contextos. |
| 3212 | PDF 329, `0140S00237` 07, ya en Diseño. Escaneo con globos y sin ICP. Es la referencia para la ruta «PDF solo». | El Excel cita 06/`3E1005491360`. Solicitar el 06 para el histórico si lo conservan. Las mediciones mantienen su revisión 06. |
| 3214 | PDF 2243, Clunas `C11692` B, en Diseño. Tiene dos páginas y números en recuadro. Publicar ambas hojas si se confirma esa edición. | Los Excel citan `11206` G y `C 11692` A. Identificar si son series distintas y pedir las ediciones aplicables. |
| 3218 | PDF 1031 en Diseño es copia idéntica del 004 de la 3174. El STEP se identifica como `6546952`. Pedir confirmación de alcance o plano propio. | Los Excel citan 002 y 004. Mantener los documentos como referencias de familia hasta saber cuáles aplican. La coincidencia de bytes solo acredita la copia. |
| 3226 | PDF 1574 en Diseño, `DW-UMED-2-2_REV01`, cajetín `732260000`. Sin números de cota. El Excel menciona `DW-UMED-18`. Confirmar qué dibujo corresponde a qué documento. | No se localizó otra edición de plano en el catálogo. Pedir la referencia citada y el plano numerado, si existe. |
| 3233 | PDF 2379, `0196S0000K` 02, DP/TD 000, en Diseño. PDF sin numeración de cotas del Excel. | Método/`Support MM` contiene el 01 **DP/TD 003** (2502). La tabla del 02 cita además un 01 **DP/TD 000** ausente. Separar ambas series. |
| 3237 | PDF 2507, `3130589019 2D 05`, en Diseño. Es el plano de consulta acordado para este caso. Tiene números en la capa de texto y carece de ICP. | Método/`OLD` contiene el 03 con globos (2835). Llevar esa edición al histórico. Solicitar el 04, citado por los Excel y ausente en la entrega. |
| 3238 | PDF 2846, `313058901F 2D 05`, en Diseño. Números en capa de texto, sin ICP. Conservar el identificador terminado en **F**. | Método/`OLD` contiene su propio 03 con globos (3015). Falta su 04. La carpeta de histórico pertenece a la 3238. |
| 3288 | Diseño contiene un PDF de tres páginas (3029), con **base, conjunto y tapa en nivel 1**. Método/`balloned/REV.02` contiene el **conjunto** nivel 2 (3127/3128, PDF/ICP). En `REV.01/BSG-296-01` hay base (3118/3119) y en `REV.01/BSG-296-02`, tapa (3122/3123). Confirmar vigencia **por componente** y preparar cada pareja en su ámbito. | El histórico sigue cada número `BSG-296-00/01/02`. Conservar el multipágina y las variantes de Método y Retoques. El primer lazo trae otra copia de la tapa globada (3050) y el tercero un PDF vectorial de tapa (3097). Evitar que el nivel 2 del conjunto sustituya a los planos de base y tapa. |
| 3309 | PDF 1588, `77217-02200-000A`, en Diseño. Sin numeración de cotas ni revisión identificada. El STEP se llama `77217-12300…` y el Excel cita `GF991-53540`. Aclarar esas referencias. | Solo se localizó ese PDF. Pedir las referencias aplicables antes de crear una sucesión de revisiones. |

Para ejecutar esta tabla, guardar cada revisión sustituida en `1- 2D y 3D pieza/Revisiones anteriores/<nº de plano>/<revisión + cambio>/` junto con su propio ICP cuando exista. Los estudios, borradores y documentos de aplicabilidad dudosa conservan su estado explícito. Una mención en una tabla de cambios o en un Excel se registra como **PDF pendiente** hasta localizar el archivo. Si Método o Retoques necesitan conservar una copia para explicar un ensayo, preservar esa referencia y su origen. [Historia por pieza](../conocimiento/planos.md#historia-de-los-planos-por-pieza) · [Proyectos ICP y PDF correspondientes](../conocimiento/planos-globos.md) · [Detalle de la tapa de la 3288](../conocimiento/4-tetones/3288.md#tolerancias-y-rebabas-de-la-tapa)

## Método 3. Organizar la metrología solo con Excel

**Unidad de archivo propuesta (revisada el 24/11/2026): el propio Excel, con su nombre actual.** No hace falta una carpeta por muestreo ni por serie. El nombre ya los lleva: en `3237-20_intern.09.xls`, `20` es la serie y `09` el muestreo. Así se llaman los informes de las 20 piezas con Excel; solo `Customer/3205-00_intern.xls` lleva `intern` sin número (ver [Cómo están hoy los Excel](#cómo-están-hoy-los-excel-24112026)). Las carpetas `V00`/`V20` que ya existen se pueden dejar como están. La revisión del **informe** y la del **plano medido** se leen dentro del libro, que puede declarar una distinta por hoja. Tampoco hay carpetas por revisión.

**Qué pedir a INTEPLAST, porque el nombre no lo dice:**

1. **Apartar en `Soportes/` los Excel que no son el informe de un muestreo:** generadores de Cpk, comparativas, MSA, volcados de datos (`DADES`, `totes`, `NEW_SC`), informes PPAP para el portal y copias `_old`, `- copia` o `(2)`. Hoy conviven con los informes. De los 750 Excel de `4- Metrologia`, 464 tienen nombre de informe; el resto son de este tipo o de nombre libre.
2. **Indicar la copia de referencia cuando un muestreo tiene varias:** la de `Interns` y la de `Customer`, o variantes con sufijo (`_customer`, `_for PPAP`, `_Wrong correction`). Ejemplo: `3218-00_intern.20.xls`, `…_20250717.xls` y `…_Wrong correction.xls`.
3. **Mantener la forma `<código>-<serie>_intern.NN` en los informes nuevos.** No hace falta unificar los antiguos: la app ya acepta `intern.01`, `intern2`, `int.10`, `int_04` e `Int_09`.

**Pendiente en la app, no en las carpetas:** hoy la app saca el muestreo del nombre, pero no la serie. `3168-00_intern.01.xls` y `3168-10_intern.01.xls` quedan juntos como muestreo 01; si los valores difieren, se muestran como series aparte con el nombre del archivo. Hay que leer también la serie (`-00`, `-10`, `-20`) para separarlas.

| Nivel | Qué debe poder recuperarse del Excel | Cómo preparar los casos actuales |
|---|---|---|
| Muestreo | Código de pieza, serie o variante, identificador de muestreo, lote si consta, fecha de medición si se conoce y edición del informe. | Conservar `intern.NN`, identificación del lote y fecha de emisión por separado. Si dos documentos discrepan, mantener ambos con su procedencia. INTEPLAST debe identificar qué copia o bloques son de referencia. |
| Hoja o bloque | Componente o conjunto, número de plano, revisión medida y, cuando distinga dos ediciones, identificador de cambio. Método, condición o montaje cuando cambien. | Leer cabecera, rótulos de bloque y `HISTORY` cuando exista. Una cabecera ausente, heredada o contradictoria queda pendiente. Una referencia de conjunto puede convivir con otra de componente. |
| Cota | Número escrito, elemento o evaluación, nominal, tolerancias y unidad que figuran en esa revisión. | Conservar varias filas si representan mínimo, máximo, diámetro, posiciones o equipos distintos. Un número de fila no sustituye a un identificador de cota. |
| Lectura | Cavidad identificada, muestra o repetición si hay varias, valor, unidad y condición de ensayo. Origen trazable a archivo, hoja y celda. | Aceptar las cavidades que la cabecera rotula, incluso si empiezan en 9 o 13. Una columna por cavidad es válida. No hace falta partir los Excel ni crear carpetas por cavidad. Para un libro por cavidad, identificarla expresamente en el informe y conservar su muestreo. |
| Naturaleza del valor | Distinguir medido en ese muestreo, heredado, calculado, previsto, impuesto y ausente. | Pedir una marca explícita cuando haga falta. Conservar fórmulas y originales, sin recalcular los libros para preparar la entrega. Excluir de la serie de medición nueva las previsiones, las muestras generadas y los valores heredados identificados. Una coincidencia de cifras por sí sola no acredita que se copiaron. |

Se pueden conservar los formatos `.xls`, `.xlsx` o `.xlsm` originales. Un Excel de método, un generador de Cpk o una copia preparada para cliente pueden tener el mismo aspecto que un informe de medición. Documentar para cada muestreo qué Excel y qué hojas contienen mediciones, qué copia se remitió al cliente y qué queda como soporte. Si dos copias contienen medidas genuinas diferentes, identificar el ensayo o la muestra de cada una. Si cambia una tolerancia o un valor sin explicación, mantener la discrepancia abierta. Las cifras históricas proceden del Excel que se consulta. [Valores múltiples con celda de origen](../conocimiento/valores-por-punto.md) · [Contraste de hojas repetidas](../conocimiento/contraste-m3.md)

### Cómo están hoy los Excel (24/11/2026)

Consulta de solo lectura a la biblioteca de `conocimiento/` (tablas `documento` y `lectura_dr`, y celdas de la fila de cabecera). Se cuentan los `.xls/.xlsx/.xlsm/.xlsb` bajo `4- Metrologia`. **Informes** son los que se llaman `<código>-<serie>_intern.NN` o sus variantes `int.NN`, `int_NN`, `Int_NN` e `internNN`. Fuera de `4- Metrologia` hay más Excel, sobre todo en Retoques y Método; la app ya no los toma como medidas.

**Dónde están:**

| Carpeta actual | Piezas |
|---|---|
| Sueltos en la raíz de `4- Metrologia` | Bolt Eye: 3051, 3197, 3212 |
| `Interns/`, y `Customer/` o `Customers/` cuando hay copias de cliente | 3167, 3168, 3186, 3195, 3202, 3205, 3206, 3214, 3218, 3226, 3233, 3288, 3309 |
| `Interns/V00`, `V01`, `V10` o `V20`, por serie | 3056 (V00, V01), 3237 (V00, V10, V20), 3238 (V00, V20, también en `Customers/`) |
| `Version 00/Interns` y `Version 00/Customer` | 3174 |
| Sin Excel | 2820 |

**El muestreo va en el nombre en todas las piezas.** 464 de los 750 Excel tienen nombre de informe; 390 de ellos sin sufijo. Ninguna pieza tiene carpetas por muestreo ni por revisión. La serie es el número tras el código: `00` en todas, y además `01` (3056), `10` (3168, 3237) y `20` (3237, 3238).

**Formatos de cabecera.** Fila de cabecera y columnas, de izquierda a derecha:

- **A**, fila 13: `Nr · Dimension · LTR · type · Nominal · Tol + · Tol- · Equipment · Cav.1… · NOK · Comments`.
- **B**, igual que A con `class` entre `Nominal` y `Tol +`.
- **C**, informe interno en castellano, fila 13: `Nr · Dimensión · LTR · tipo · Nominal · Tol + · Tol- · Units · Equipo · CAV.1… · NOK · Comentarios`.
- **D**, fila 13 (3288) u 8 (3309): `Item · Dimension / Specificat · type · Nominal · [class] · Tol + · Tol- · Meas. Equip. · Cav.1… · NOK · Comments`.
- **E**, formato de cliente eISIR, fila 7, en hojas `cav_N` o libros `.xlsm`: `e_Type · Number · Kind · Type · Target · Tol + · Tol - · Units · Measuring Device · 1…5 · NOK · Comments`. En las hojas `cav_N` las columnas `1…5` son muestras de esa cavidad; en `3195-00_Int_NN.xlsm` son `Cav. 1…8`.

| Pieza | Nombre de los informes | Informes / Excel | Otros Excel en Metrología | Hojas con medidas (las más frecuentes) | Cabecera · cavidades |
|---|---|---:|---|---|---|
| 2820 | — | 0 / 0 | — | — | — |
| 3051 | `3051-00_intern.01.xls` | 11 / 14 | `Suport_Int_NN/3051_Cloud_of_Points.xlsm` | `DR(100%)`, `DR(4CAV_CMM)`, `DR` | A · Cav.1–4 |
| 3056 | `3056-00_intern2.xls`, `3056-00_intern.1_100%.xls`, `3056-01_intern.3.xls` | 17 / 17 | `…_MIN MAX COMPARISON.xls` | `DR (3D)`, `DR (DIF)`, `DR(100%)`, `DR (PARAM.)` | A · CAV.1–4 |
| 3167 | `3167-00 Int_09.xls` | 23 / 122 | 83 generadores de Cpk en `Customer/PPAP-3167-00_4/Estudis Estadístics/`, `PPAP-3167-00_Inf_NN.xlsm` | `DR_100%_old`, `DR_CC(P1)`/`(P2)`, `DR`, `cav_N` | C y A · CAV.1–4; E en `cav_N` |
| 3168 | `3168-00_intern.01.xls`, `3168-10_intern.01.xls` | 29 / 41 | `PPAP_3168-00_inf0N.xlsm`, comparativas, SPC, `3168-R&R.xlsx` | `DR`, `DR-Dry`, `DR-Conditioned`, `cav_N` | A · CAV.1–8; E en `cav_N` |
| 3174 | `3174-00_intern.NN.xls`, también con `_Ball`, `_for customer`, `- copia`, `– Was open` | 58 / 83 | `3174_SPC*.xlsm`, `PPAP-3174-00_INFNN.xls`, `DADES`, `Peça_clipada`, `3174-00_600/700/800.xls` | `DR_CMM`, `DR_100%`, `DR`, `DR_CMM 600 BAR` | B · CAV.1–8 |
| 3186 | `3186-00_intern.NN.xls` | 29 / 36 | MSA, Cpk, `Peça_clipada`, `3186-CMM.xlsx` | `DR_100%`, `DR_CMM`, `DR` | B · CAV.1–4 |
| 3195 | `3195-00_intern.01.xls`, `3195-00_int_04.xls`, `3195-00_Int_02.xlsm` | 28 / 69 | 25 `N####.xlsm` por cota, resúmenes `Humid`, `no H`, `totes`, `Results` | `DR`, `DR_100%`, `DR_Humid`, `DR_HR%-sh#` | B · CAV.1–8; E en `Int_NN.xlsm` |
| 3197 | `3197-00_intern.NN.xls` | 11 / 14 | `Support_intern.05/`, `Support_intern.08/` (`dades`, `MSA`, `totes_nozzle 90`) | `DR`, `DR_8cav.`, `DR-<n>º`, `DR_PAR` | B · CAV.1–8 |
| 3202 | `3202-00_intern.NN.xls`, `…_COSTUMER.xls` | 10 / 13 | `PPAP-3202-00_INF.01.xls`, plan de control, `circle_diagram` | `DR_100%`, `DR_Param`, `DR_N…+CROQUIS`, `3pcs countermeasurement` | B · CAV.1–4 |
| 3205 | `3205-00_intern.NN.xls`; `Customer/3205-00_intern.xls` sin número | 39 / 40 | — | `DR`, `DR (customer)`, `DR_100%`, `DR_CMM`, `NEW INSERTS CN` | B · CAV.1–8; postizos 1, 2, 3.1, 3.2… en `NEW INSERTS CN` |
| 3206 | `3206-00_intern.NN.xls`, `…_per GPF`, `…_versio FM` | 34 / 45 | `3206_Dades*.xls`, `totes`, `PLAN_7_PUNTS`, `Shroud_CMM_Cloud_Position` | `DR_(100%)`, `DR_PARAM(#)`, `DR`, `DR_CMM`, `DR_Concentricitat_nou_metode` | B · CAV.1–4 |
| 3212 | `3212-00_intern.NN.xls` | 9 / 9 | — | `DR(100%)`, `DR(3D)`, `DR(N…)`, `DR` | A · Cav.13–16 |
| 3214 | `3214-00_int.NN.xls`, también `_OQLow`, `_OQHigh`, `_EC`, `_customer` | 18 / 20 | `3214-00_MSA.xlsm`, `FOT review 20240605.xlsx` | `DR`, `DR_EC`, `DR_H_…`/`DR_L_…` (Inici, Mig, Final), `DR_OQ low`/`high`, `FAI` | A · CAV.9–12 |
| 3218 | `3218-00_intern.NN.xls`, con sufijos como `_Set No.3`, `_PPAP_customer`, `_Wrong correction`, `_old` | 56 / 99 | 15+ `3218_NEW_SC…`, `CLIPS`, `DATA`, CT-SCAN, `500bar`/`700bar`, `Jig variability study` | `DR_100%`, `DR_100%_for PPAP`, `KnO - 3D CMM+ ICLs…`, `DR(KnO)`, `DR(VdB)` | B · CAV.1–8 |
| 3226 | `3226-00_intern.01.xls` | 1 / 1 | — | `DR`, sin cabecera reconocida | Faltan número de cota y cavidad ([A28](preguntas-abiertas.md#a28-3226-sin-numeracion)) |
| 3233 | `3233-00_intern.NN.xls` | 21 / 32 | `PPAP_3233_Inf_NN*.xlsm`, `Overview`, `315595 - Test tracció/` | `100%`, `100% (CUSTOMER)`, `100% BOSCH PORTAL`, `3D CMM`, 160 hojas `cav_N` | B · CAV.1–32; E en `cav_N` |
| 3237 | `3237-00_intern.NN.xls`, `3237-20_…`, con sufijos de comparativa o `including CPK` | 39 / 59 | `Customer/EPC/` (10), `PPAP_3237_INF_NN.xlsm`, `Support Int_NN/` | `DR`, `DR (2)`, `cav_N`, `CP` | B · CAV.1–4; E en `cav_N` |
| 3238 | `3238-00_intern.NN.xls`, `3238-20_…` | 19 / 24 | `PPAP_3238(-20)_INF_NN.xlsm`, `DMC code measurements tool` | `cav_N`, `DR (2)`, `DR_100%`, `DR`, `DR_HUM` | B · CAV.1–4; E en `cav_N` |
| 3288 | `3288-00_intern.NN.xls` | 4 / 4 | — | `DR(base)`, `DR(tapa)`, `DR(tapa)param` | D · Cav.1–20 en tapa; 1–20 en base |
| 3309 | `3309-00 Int_NN.xls`, `P3309-00 Int_NN.xls` | 8 / 8 | — | `DR`, `DR (Cotes Groc i taronja)`, `DR-Customer` | D (fila 8) · CAV. 1–4 |

**Muestreos con varias copias** (mismo `intern.NN` en más de un archivo): son lo habitual. En 3167, 3174, 3186, 3195, 3202, 3205, 3206, 3214, 3218, 3233, 3237, 3238 y 3309 hay muestreos que están en `Interns` y en `Customer`, o repetidos con sufijo. En 3056, 3168, 3237 y 3238 el mismo número aparece además en dos o más series. Por eso hay que pedir la copia de referencia, no reorganizar carpetas.

### Revisión de los Excel de cada pieza

Los ejemplos son localizadores relativos a `4- Metrologia` salvo indicación expresa. Una hoja sirve para encontrar el caso, no como plantilla universal de esa pieza. Las cavidades indicadas corresponden al ejemplo. El número de cavidades físicas del molde requiere su propia fuente. [Cabeceras con rutas y celdas](../conocimiento/planos.md#revisiones-que-citan-las-cabeceras) · [Identidades y excepciones por hoja](../conocimiento/identidad-piezas.md)

| Pieza | Excel u hoja de partida | Cómo organizarlo y qué resolver |
|---|---|---|
| [2820](../conocimiento/ingesta/2820.md) | Entrega con plano y STEP, sin informe. | Dejar Metrología sin muestreos e indicar «sin Excel entregado». |
| [3051](../conocimiento/ingesta/3051.md) | En raíz, `3051-00_intern.01.xls`, hojas `DR(100%)` y `DR(4CAV_CMM)`, C1–C4. | Ordenar por `intern`, conservar hojas y revisión declarada 01. En `intern.06` hay mínimo, máximo y diámetro de una misma cota. Preservar cada evaluación y los bloques heredados. |
| [3056](../conocimiento/ingesta/3056.md) | `Interns/V00/3056-00_intern.1_100%.xls`, hojas `DR (3D)` y `DR (PARAM.)` con distintas cavidades. | Mantener V00 y el muestreo. Leer por hoja la secuencia 01–04. La numeración 1200/2140 varía entre muestreos aun con el mismo nivel declarado. Evitar reconstruir la identidad por nominal. |
| [3167](../conocimiento/ingesta/3167.md) | `Interns/3167-00 Int_01.xls`, `DR_CC(P1)` y `DR_CC(P2)`, C1–C4. Hay además Excel de cliente por cavidad en `Customer/PPAP-3167-00_…`. | Mantener los bloques P1/P2 y el identificador de cavidad. Distinguir medidas propias de muestras de cliente generadas. La revisión del plano está ausente en las cabeceras revisadas. |
| [3168](../conocimiento/ingesta/3168.md) | `Interns/3168-00_intern.01.xls!DR(1)` y `3168-10_intern.01.xls!DR`, ambos con C1–C8. | Separar series 00/10 y condiciones de ensayo aunque coincida `intern.01`. Conservar el 01 declarado en los informes. Verificar el formato real de los archivos con extensión Excel. |
| [3174](../conocimiento/ingesta/3174.md) | `Version 00/Interns/3174-00_intern.01.xls`, `DR_100%` y `DR_CMM 600 BAR`. En `intern.25` la misma cavidad se repite en varias columnas. | Preservar serie, presión, método y muestra. Distinguir las ediciones 001/002/004 y las hojas con `#REF!`. Revisar copias internas y de cliente por contenido. |
| [3186](../conocimiento/ingesta/3186.md) | `Interns/3186-00_intern.01.xls`, `DR_100%` y `DR_CMM`, C1–C4. | Conservar condiciones clipada/libre cuando se declaren. Mantener la revisión 2 declarada y la consulta de aplicabilidad del 6494730. Hay hojas de otra pieza en Retoques. |
| [3195](../conocimiento/ingesta/3195.md) | `Interns/3195-00_intern.01.xls!DR` y `3195-00_Int_01.xlsm!DR_100%`, C1–C8 en esos ejemplos. | Identificar autoría y papel de cada copia del muestreo. Separar mediciones de humedad y de útiles. Conservar por hoja `07`, `09/3E1008859560` y sus tolerancias declaradas. |
| [3197](../conocimiento/ingesta/3197.md) | En raíz, `3197-00_intern.02.xls`, `DR_8cav.` con C1–C8 y `DR_PAR` con C1 y C2. | Conservar condición de ensayo, presión y temperatura cuando estén identificadas. Los informes citan el cambio `3E1009447060`. Diferenciar previsiones de retoque de lecturas. |
| [3202](../conocimiento/ingesta/3202.md) | `Interns/3202-00_intern.01.xls!DR_100%`, C1–C4. En `intern.07`, hoja `3pcs countermeasurement`, filas 15–16. | La cabecera declara «-» aunque esas filas ya usan tolerancias de A. Conservar literal, tolerancias y muestreo. Pedir el primer lote o informe al que se aplicó A. |
| [3205](../conocimiento/ingesta/3205.md) | `Interns/3205-00_intern.01.xls!DR_100%`, C1–C8. En `Customer/3205-00_intern.17.xls` hay hojas que citan B. | Revisar por hoja la discrepancia con la copia interna del mismo muestreo. Distinguir previsiones que aparecen dentro del informe y mediciones nuevas. |
| [3206](../conocimiento/ingesta/3206.md) | `Interns/3206-00_intern.01.xls!DR_(100%)`, C1–C4. | Registrar plano A o B por hoja y mantener el contexto de cambio de postizos. En Retoques hay una hoja `DR(base)` con referencia ajena. Separarla de las medidas de la pieza. |
| [3212](../conocimiento/ingesta/3212.md) | En raíz, `3212-00_intern.01.xls!DR(3D)`, C13–C16. En `intern.08!DR` la cota 113 aparece en dos bloques. | Conservar los identificadores 13–16, revisión 06, bloque y repetición. Contrastar en el propio Excel qué se volvió a medir. La disponibilidad de CSV de esta pieza no cambia la regla. |
| [3214](../conocimiento/ingesta/3214.md) | `Interns/3214-00_int.01.xls!DR`, C9–C12. Los libros también distinguen pruebas como `OQLow`. | Mantener los números reales de cavidad y el ensayo. Conservar por separado las referencias `11206/G` y `C 11692/A`. |
| [3218](../conocimiento/ingesta/3218.md) | `Interns/3218-00_intern.01.xls!DR_CMM 580 BAR`. En `intern.06` hay hojas `DR_400b` a `DR_700b`. | Preservar presión, método, lote y cavidad aunque se repitan cota y muestreo. Conservar 002 y 004 por hoja. Las hojas identificadas con otro molde quedan como antecedente. |
| [3226](../conocimiento/ingesta/3226.md) | `Interns/3226-00_intern.01.xls!DR`, filas 14–60. `D14` contiene el nominal 21,4 e `I14` el valor 21,15. | Guardar el Excel del muestreo. Faltan el número de cota y la identificación de la cavidad. La copia en Retoques no los aporta. Dejar la interpretación pendiente. [A28](preguntas-abiertas.md#a28-3226-sin-numeracion) |
| [3233](../conocimiento/ingesta/3233.md) | `Interns/3233-00_intern.01.xls!100%`. En `intern.16`, hoja `100% BOSCH PORTAL`, celda P87, Interns y Customer discrepan. | Identificar la copia de referencia. Separar hojas con muestras generadas, mantener los rótulos de las 32 columnas y la revisión declarada. Pedir aclaración sobre nominales cambiados y cavidades físicas. |
| [3237](../conocimiento/ingesta/3237.md) | `Interns/V00/3237-00_intern.09.xls!DR`, J6/N6, revisión 04. También existe `Interns/V20/3237-20_intern.09.xls`. | Conservar serie, lote y humedad si se declara. Hay informes 03/04/05. En la serie 04 se consulta su gráfica mientras el plano de la app sigue siendo el 05. |
| [3238](../conocimiento/ingesta/3238.md) | `Interns/V00/3238-00_intern.07.xls!DR`, I6/M6, revisión 04. En V20 hay hojas 04 y 05 en distintos muestreos. | Separar serie, tecnología CMM/CT y condición de humedad. Los informes o archivos de comprobación de útiles tienen otra finalidad. La serie antigua conserva las tolerancias de su Excel. |
| [3288](../conocimiento/ingesta/3288.md) | `Interns/3288-00_intern.01.xls!DR(base)` y `DR(tapa)`. I6/AB6 citan el conjunto y el nivel, D14 identifica el plano del componente. | Conservar un solo libro y dos ámbitos con numeración propia. Las 20 columnas y el método que declara 16+16 requieren aclaración. Preguntar qué nivel aplica a `intern.04`. Mantener los Excel del molde 3247 como referencia histórica. |
| [3309](../conocimiento/ingesta/3309.md) | `Interns/3309-00 Int_01.xls!DR`, C1–C4. En los libros la referencia es `GF991-53540` sin revisión. | Ordenar por muestreo y mantener referencia y revisión tal como figuran. Solicitar plano numerado y correspondencia con el CAD y el PDF. |

## Método 4. Preparar los demás archivos de la pieza

| Tipo | Convención propuesta | Casos que cambian la preparación |
|---|---|---|
| CAD de producto | En Diseño, un STEP vigente por producto o componente identificado. Conservar número de pieza y revisión CAD cuando consten. | En la 3202 los STEP de útiles están en Método. En la 3288 hay dos STEP de producto (`BASE_RCP31` y `TAPA_RCP31`). En 3237 y 3238 el código de versión del STEP sigue su propia serie. |
| CAD de molde | Identificar la carpeta de la pieza que contiene los ficheros de molde. El botón de carpeta la abrirá en SharePoint con la organización que ya use INTEPLAST. | En la 3206 la carpeta contiene los dos lados y en la 3056 hay lados y electrodos. En ambos casos basta la ruta de la carpeta para consultarlos. [Inventario de moldes](preguntas-abiertas.md#a29-archivo-principal) |
| Moldflow | El botón de carpeta abrirá en SharePoint la ubicación real de los ficheros del estudio. Conservar su formato de entrega y registrar su ausencia cuando proceda. | En 3212 se encuentra en `7- Moldflow`. La 3206 trae un vídeo AVI. En la 3288 el README indica que no hay estudio. |
| Escaneos y fotos | Identificar pieza, componente y, si constan, lote, cavidad y fecha. Proponer una ubicación estable para las fotos si INTEPLAST confirma cómo se entregarán. | En 3288 hay `Base.stl` en el nombre de un escaneo y otro llamado `Nou`, de alcance pendiente. El escaneo guardado bajo 3309 empieza por `3218-00`. Las fotos de un retoque conservan su relación con ese lazo. |
| Piezas en varios features | Preparar una sola carpeta de datos por código. Mantener la relación con todos sus features. | 3167 y 3214 tienen remisiones en Tetones. 3205 y 3206, en Planitudes. Anclajes contiene una remisión sin identificar la pieza. Conservarla como pendiente. [Comparativa](../conocimiento/comparativa.md#pieza-por-pieza) |

## Cómo usar este documento para hacer los cambios

1. **Preparar una relación de operaciones por pieza.** Partir de su fila de planos y de su fila de Excel. Para cada archivo anotar ruta actual, destino propuesto, pieza/componente, documento, revisión/cambio, motivo, evidencia y estado. Usar «preparado», «pendiente de archivo», «pendiente de confirmación» y «comprobado» para distinguir lo ejecutable de las consultas abiertas. Conservar las rutas de origen y las referencias que se verían afectadas al mover un archivo.
2. **Resolver las decisiones que afectan al destino.** Concretar con INTEPLAST el nombre de la carpeta histórica, los documentos liberados en los casos dudosos y las copias de Excel de referencia. Un dato ausente puede seguir ausente. Evitar deducir una aprobación o completar una ficha para que la prueba pase.
3. **Preparar las carpetas y revisar la selección desde cero.** En una copia de trabajo, aplicar primero las operaciones documentadas. Revisar con el comportamiento previsto qué devolvería cada carpeta de Diseño, incluidas las páginas de cada PDF. Si el plan localiza una edición mejor en Método o Retoques, el cambio consiste en preparar allí la fuente y colocar el archivo acordado en Diseño. El visor no buscará excepciones fuera de esa carpeta.
4. **Comprobar cada pieza antes de darla por preparada.** Al abrir Diseño debe quedar inequívoco el PDF de cada ámbito. Su ICP, si existe, debe situar las marcas en el dibujo y la hoja correctos. Los antiguos se deben poder encontrar por número y cambio en el histórico de SharePoint. Si falta el viejo PDF, el Excel histórico sigue siendo consultable con la revisión que declara.
5. **Repetir la comprobación con los Excel como única entrada de medidas.** Elegir una cota con datos en cada pieza que los permita y remontar un punto de la gráfica a libro, hoja, celda, revisión, cavidad y muestra. Verificar también un caso sin informe (2820), otro sin identificadores suficientes (3226), uno con copias discrepantes (3233) y otro con numeración repetida por componente (3288). En 3237, cambiar de 05 a 04 debe cambiar la gráfica, mantener el PDF 05 y dejar el acceso al antiguo en SharePoint.

### Ejemplos de operaciones para el futuro plan

Rutas relativas a la raíz de cada pieza. Los destinos usan los nombres propuestos. Al preparar la copia de trabajo se pueden conservar los nombres originales de ambos archivos de una pareja PDF/ICP.

| Pieza y origen | Destino propuesto | Qué comprobar |
|---|---|---|
| 3205 · `6- Método de medición/DRW ballooned/213137-10300-B_241028/`, archivos `20241121_213137-10300-B_balloned.pdf` y `20241121_213137-10300-B.icp` | Ambos a `1- 2D y 3D pieza/` si se confirma ese cambio. La edición sustituida de 2023 y su ICP, a `1- 2D y 3D pieza/Revisiones anteriores/213137-10300/B_231011/`. | INTEPLAST identifica el cambio vigente. La B de 2024 debe usar su propio ICP y la B de 2023 debe conservarse completa. |
| 3237 · `6- Método de medición/OLD/1 - 3130589019_D_03_balloned.pdf` | `1- 2D y 3D pieza/Revisiones anteriores/3130589019/03/`. El PDF `20260914_3130589019 2D 05.pdf` ya está en Diseño. | El botón con reloj permite llegar al 03 en SharePoint. El visor abre el 05 y excluye el 03 de la búsqueda de vigentes. El 04 solo se incorpora cuando se reciba su PDF. |
| 3237 · `4- Metrologia/Interns/V00/3237-00_intern.09.xls` y `4- Metrologia/Interns/V20/3237-20_intern.09.xls` | Sin mover. | Persisten los dos muestreos con su serie, que sale del nombre (`-00`, `-20`). En el primero se recupera el nivel 04 de `DR!N6`. |
| 3167 · `4- Metrologia/Customer/PPAP-3167-00_4/Estudis Estadístics/` (83 generadores de Cpk) | `4- Metrologia/Soportes/`, conservando la subcarpeta. | No son informes de muestreo y no deben leerse como medidas. |
| 3226 · `4- Metrologia/Interns/3226-00_intern.01.xls` | Sin mover. | La asignación cota–cavidad sigue pendiente hasta recibir la identificación que falta. |

**Alcance de la revisión.** Se contrastaron las 21 piezas con las fichas de ingesta, el catálogo de planos y la biblioteca SQLite de conocimiento. El 24/11 se compararon por ruta los PDF, ICP, Excel (`.xls/.xlsx/.xlsm/.xlsb`), STEP y MFR de la biblioteca con el directorio local de `Exemples`: coincidieron las 2.634 rutas. Esta comparación verifica presencia. Las revisiones, las marcas y los casos de Excel se apoyan en los cajetines, hojas y celdas ya estudiados y citados. La liberación industrial de los candidatos y la futura estructura de SharePoint requieren confirmación de INTEPLAST.
