# Preparación de las carpetas de pieza para INTEPLAST

**Documento de trabajo · actualizado el 27/11/2026.** El plan abarca las carpetas de los features y de las 21 piezas de `Exemples`. El inventario recoge los archivos localizados. El responsable de la pieza confirma la aprobación de los documentos dudosos.

1. **Primero, la estructura de carpetas.** Acordar con Eduard las reglas de ubicación y documentar los movimientos por pieza. La prueba posterior se hará en una carpeta hermana de `Exemples`. El nombre propuesto es `Exemples reestructurados`. En esta fase los Excel se conservan tal como se recibieron. Su ubicación distingue informes de muestreo, copias de cliente y soportes.
2. **Después, el contenido de los Excel.** Revisar por separado qué convenciones necesitan las hojas, cabeceras e identificadores para poder leer las mediciones de forma consistente. El inventario y los casos del método 3 servirán de punto de partida. [Próximos pasos de Metrología](proximos-pasos.md#-reorganizar-metrología-de-las-21-piezas-prueba-de-concepto-24112026)

<a id="estado-de-las-siete-carpetas-al-26112026"></a>

## Estado de las siete carpetas al 27/11/2026

**Definidas con Eduard:** `1- 2D y 3D pieza/`, `2- Moldflow/`, `3- Molde/` y `4- Metrologia/`. Sus reglas de estructura quedan acordadas para preparar la futura copia de `Exemples`.

| Carpeta | Estado |
|---|---|
| `5- Retoques molde/` | Propuesta acordada con Eduard. Un PowerPoint vigente por plan y una referencia al retoque en el intern que lo comprueba. Pendiente de contrastar con Metrología de INTEPLAST. |
| `6- Método de medición/` | Fuera del alcance actual de la web por decisión de Eduard. Queda abierta la [pregunta para INTEPLAST](preguntas-abiertas.md#consulta-metodo-medicion). |
| `7- Pieza real STL/` | Última carpeta por concretar. De las 21 piezas, 18 traen un STL en esta carpeta, la 3288 trae dos y la carpeta está ausente en la 2820 y la 3197. En la 3309, el único STL lleva el código 3218 en el nombre. [Dudas de identificación en A29](preguntas-abiertas.md#a29-archivo-principal) |

### Retoques del molde

**Qué proponemos a INTEPLAST.** Cuando un muestreo compruebe un retoque, Metrología anotará qué retoque verifica en el Excel de ese intern, en la columna **`Remarks` (F)** de `HISTORY`, bajo el encabezado del informe actual. Si el muestreo comprueba la ronda, basta una línea como **«Verifica plan 10»**. Si comprueba una acción concreta, **«Verifica acción 10.1»**. El número de plan debe permitir localizar su PowerPoint en `Retoques molde`. Si hay duda sobre el plan o la versión que se comprobó, se puede escribir el nombre exacto del PowerPoint. El Excel ya identifica el intern.

**Disponibilidad de la plantilla.** En 353 de los 355 muestreos se encontró al menos una copia con `HISTORY` y la cabecera `Remarks` en F6. En los otros dos, los interns 14 y 16 de la pieza 3195, los Excel disponibles carecen de esa hoja. Conviene confirmar con Metrología qué plantilla usará para esos casos en adelante. [Recuento y ejemplo de anotación](../conocimiento/retoques-por-muestreo.md#disponibilidad-de-history-y-remarks)

El PowerPoint conserva la descripción del retoque con el detalle disponible, por ejemplo un pulido o un ajuste de una cavidad. Una referencia al plan acredita qué ronda se comprobó. Para atribuir la ejecución de una acción concreta se necesita una anotación que la identifique.

**Cómo guardar los ficheros.** En `5- Retoques molde/`, cada plan tendrá una carpeta con **un PowerPoint vigente** que identifique el plan en el nombre. Las versiones anteriores del mismo PowerPoint se conservan con su nombre en una subcarpeta de histórico, por ejemplo `Old/` u `Obsoleto/`, para que un intern antiguo siga remitiendo a la versión que comprobó. Un PowerPoint de resultados tiene otra función y puede acompañar al plan. El Excel auxiliar que a veces se guarda junto al PowerPoint queda descartado como registro del vínculo. Puede conservarse como soporte de cálculos o de las medidas que dieron origen al plan.

**Pregunta prioritaria.** Cuando Metrología rellena el intern, ¿sabe qué plan o acción está comprobando? Si dispone del dato, el registro se hace una sola vez en `HISTORY`. **Anotar también el intern en el PowerPoint es opcional.** Si ese dato solo lo conoce quien gestiona el plan, se propondrá que esa persona anote en el PowerPoint qué intern comprobó la ronda o la acción. La elección del registro queda pendiente de la respuesta de INTEPLAST. [Pregunta para la reunión](preguntas-abiertas.md#a20-planes-correccion) · [Evidencia por pieza e intern](../conocimiento/retoques-por-muestreo.md)

## Decisiones de Eduard

1. **El adjunto «Plano» abre el único PDF que está directamente en `1- 2D y 3D pieza/`.** Se conservan todas sus páginas. Si su ICP está junto al PDF en ese mismo nivel, lo acompaña. El PDF también se abre por sí solo.
2. **Los planos de las subcarpetas son históricos por su ubicación.** La ficha ofrecerá un enlace a su carpeta en SharePoint para quien quiera consultarlos. La presentación de ese enlace queda por decidir. Cambiar la revisión de mediciones cambia la serie de Excel y mantiene el mismo PDF de primer nivel en el visor.
3. **Los Excel son la única fuente de mediciones para este plan.** INTEPLAST puede aportar estos informes habitualmente. Desde el acuerdo del 24/11/2026, el CSV de máquina es opcional y sirve para comprobar el Excel. Puede acompañar al informe o conservarse en el soporte de su muestreo. Una discrepancia en la misma cota, muestreo y cavidad se documenta con ambos orígenes. El valor de referencia sigue siendo el del Excel. Para la copia se admiten las dos ubicaciones de informes acordadas el 26/11/2026 en el [método 3](#método-3-organizar-la-metrología-solo-con-excel). Esto actualiza la petición de Excel más CSV de la [reunión del 20/11](reunion-inteplast-2026-11-20.md).

4. **Moldflow.** El icono de la ficha de pieza abre la página de Moldflow. Desde esa página el usuario abre la carpeta del estudio en SharePoint y allí puede consultar o descargar sus archivos. Para ofrecer el enlace basta con la ruta de la carpeta, incluso si está vacía. La página de Moldflow permite añadir una captura opcional de la simulación.
5. **Molde.** En los adjuntos de la ficha, el icono de Molde abre su página. Desde allí el usuario accede a la carpeta del molde en SharePoint y elige qué archivo consultar o descargar. La página admite una captura opcional, por ejemplo una imagen de las cavidades. El acceso requiere únicamente la ruta de la carpeta, sin seleccionar un STEP principal ni visualizar el molde en 3D en la web.

## Estructura propuesta

### De la raíz a la pieza

Cada carpeta de primer nivel identifica **un feature** y contiene directamente las carpetas de sus piezas. Si dos tipos distinguen dos features, cada tipo se incorpora al nombre de su feature. Así se trasladarán los grupos actuales de Clips a la copia. [Inventario de Clips](../conocimiento/1-clips/README.md)

| Carpeta en `Exemples` | Feature en `Exemples reestructurados` | Carpetas de pieza directamente debajo |
|---|---|---|
| `1- Clips en Piezas/Tipo A/` | `Clips en pieza A/` | `3174/`, `3186/`, `3218/` |
| `1- Clips en Piezas/Tipo B/` | `Clips en pieza B/` | `3195/`, `3226/`, `3309/` |

**Piezas compartidas.** Se conserva la convención que ya usa INTEPLAST. Una carpeta contiene los datos y, bajo cada otro feature, una carpeta con el mismo código contiene un `Readme.txt` que indica dónde encontrarlos. En los originales, los README de Planitudes para **3205 y 3206** remiten a Nervios de Soldadura. Los de Tetones remiten a Pockets para **3167** y a Nervios de Soldadura para **3214**. Al preparar la copia, comprobar que desde cada remisión se llega a la carpeta del mismo código. La nota de Anclajes sigue pendiente de identificación. [Inventario por feature](../conocimiento/comparativa.md#pieza-por-pieza)

### Dentro de la pieza

**La función de la carpeta determina cómo debe interpretarla el lector.** El prefijo numérico es opcional y el orden es libre. La numeración del esquema solo facilita la lectura. En el original de Bolt Eye, Moldflow puede llevar el **7** y el STL el **8**. La futura validación deberá comprobar que cambiar u omitir el prefijo da el mismo resultado. La **3212 Pump Housing** sirve de referencia para distinguir el plano vigente, el STEP de producto y el CAD de molde. [Comparación de los dos esquemas](../conocimiento/comparativa.md#esqueleto-del-3212-frente-al-nuevo)

```text
<código de pieza>/
  1- 2D y 3D pieza/
    <plano>_rev<revisión>.pdf
    <plano>_rev<revisión>.icp                 si existe el proyecto correspondiente
    <CAD de producto vigente>.stp
    <carpeta de histórico de nombre libre>/
      <planos antiguos con la organización interna de la entrega>
  2- Moldflow/
    <contenido de la carpeta tal como se entrega>
  3- Molde/
    <ficheros del molde tal como los organiza INTEPLAST>
  4- Metrologia/
    <informes Excel>                         en esta raíz cuando la pieza prescinde de Interns/
    Interns/                                 opcional; si existe, todos los informes internos van aquí
    support intern.NN/                       si existe, conserva los soportes y los CSV de ese muestreo
    Customer/, Soportes/, …                  copias de cliente y otros documentos auxiliares, cuando existan
  5- Retoques molde/
    <carpeta del plan>/
      <PowerPoint vigente del plan>.pptx
      Old/                                   versiones anteriores del mismo plan, si las hay
  6- Método de medición/
  7- Pieza real STL/
```

**Reglas fijas y variantes admitidas**

| Zona | Regla | Flexibilidad |
|---|---|---|
| Diseño (`2D y 3D pieza`) | Un único PDF en el primer nivel para el adjunto de plano, con su ICP opcional a su lado. La pieza simple tiene un STEP de producto (`.stp` o `.step`). | El PDF puede contener varias hojas, incluso de distintos componentes. La pieza compuesta puede tener varios CAD de producto, uno por componente identificado. |
| Histórico de planos y CAD de producto | Los planos guardados bajo una subcarpeta de Diseño quedan para consulta en SharePoint. La subcarpeta admite cualquier nombre y organización interna. | Los STEP anteriores pueden compartir carpeta con los planos antiguos o tener su propio histórico. |
| Metrología | Una sola ubicación de referencia por pieza. Si existe `Metrologia/Interns/`, reúne los informes internos de todas las variantes y muestreos. Si falta, los informes se guardan directamente en la raíz de Metrología. | Se conservan las carpetas de cliente y de soporte. Sus Excel quedan fuera de los informes internos. Los CSV opcionales pueden seguir en el soporte de su muestreo. [Regla y ejemplos](#método-3-organizar-la-metrología-solo-con-excel) |
| Retoques | Un PowerPoint vigente por plan. Las versiones anteriores quedan en el histórico de ese plan. | El nombre de la subcarpeta de histórico es libre. Los documentos de resultados y soporte pueden acompañar al plan. |
| Molde, Moldflow, Método y STL | Conservar los archivos en la carpeta de su función. Los documentos auxiliares de un método conservan su contexto. | Se admite la organización interna de cada entrega, incluidos lados del molde y electrodos. |

**Carpetas opcionales vacías o ausentes.** La copia conserva los directorios que existen en el original, incluidos los vacíos. Para las categorías en las que se buscan archivos, se comprobará que una carpeta vacía y una ausente permiten cargar el resto de la pieza. En Moldflow el destino es la propia carpeta y el enlace es independiente de su contenido. [Ejemplos de carpetas vacías comprobadas en disco](../conocimiento/comparativa.md#esqueleto-del-3212-frente-al-nuevo)

## Método 1. Preparar el plano de consulta

1. Inventariar los PDF y los proyectos ICP de diseño, Método y Retoques **durante la preparación**. Incluir los lazos de corrección aunque el nombre no contenga «plano», `DRW` o `ballooned`. En la app, la consulta se limitará a la carpeta de vigentes.
2. Identificar número de plano, pieza o componente, revisión, cambio o fecha del cajetín, estado de aprobación y páginas. Un nombre reciente, el mayor número, los globos o estar ya en diseño no acreditan la vigencia. Ante un borrador, cambio de referencia o dos candidatos sin resolver, anotar la pregunta para el responsable y dejar la publicación pendiente. Si falta un vigente identificable, la pieza puede conservar sus mediciones y quedar sin plano de consulta. Un PDF de Método, de Retoques o del histórico nunca cubre ese hueco en la app.
3. Para la edición aprobada, buscar primero el PDF numerado con su proyecto ICP. Contrastar número de plano, componente, edición, hoja y colocación de las marcas. Si hay varias copias, comparar su contenido y orientación. Conservar juntos el PDF y el ICP que se hayan podido emparejar. Si el ICP corresponde a otra revisión o su ajuste es dudoso, preparar solo el PDF vigente.
4. Sin ICP, usar el PDF aprobado de mejor calidad disponible para esa edición. El visor enseña el documento entero. La búsqueda solo puede localizar números que el lector reconozca en la capa de texto o en la imagen. Un plano sin numeración puede mostrar nominales y tolerancias y aun así carecer del identificador usado en el Excel. Pedir la versión aprobada numerada si se necesita esa búsqueda. La numeración del Excel o la de un plano anterior no se superpone al vigente. [Estilos de numeración observados](../conocimiento/planos-globos.md)

## Método 2. Ordenar las revisiones en SharePoint, pieza por pieza

**Qué abre la ficha en la carpeta preparada (26/11/2026).** Para el adjunto de plano se toma exclusivamente el PDF del primer nivel. Si falta, el adjunto queda sin plano. Los planos de cualquier subcarpeta quedan fuera de la lectura, la indexación y la asignación de etiquetas de vigencia. Para ofrecer el histórico basta con enlazar la carpeta de SharePoint. Por ejemplo, en la copia de la 3237 el adjunto abre el PDF 05 de la raíz y el usuario puede consultar el 03 entrando en la carpeta enlazada.

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
| 3288 | Diseño contiene un PDF de tres páginas (3029), con **base, conjunto y tapa en nivel 1**. Método/`balloned/REV.02` contiene el **conjunto** nivel 2 (3127/3128, PDF/ICP). En `REV.01/BSG-296-01` hay base (3118/3119) y en `REV.01/BSG-296-02`, tapa (3122/3123). Confirmar con el responsable qué PDF debe ocupar la raíz de la copia. Mantener sus páginas juntas. | El histórico sigue cada número `BSG-296-00/01/02`. Conservar el multipágina y las variantes de Método y Retoques. El primer lazo trae otra copia de la tapa globada (3050) y el tercero un PDF vectorial de tapa (3097). Evitar que el nivel 2 del conjunto sustituya a los planos de base y tapa. |
| 3309 | PDF 1588, `77217-02200-000A`, en Diseño. Sin numeración de cotas ni revisión identificada. El STEP se llama `77217-12300…` y el Excel cita `GF991-53540`. Aclarar esas referencias. | Solo se localizó ese PDF. Pedir las referencias aplicables antes de crear una sucesión de revisiones. |

Para ejecutar esta tabla, guardar cada revisión sustituida en el histórico de Diseño de esa pieza junto con su propio ICP cuando exista. Los estudios, borradores y documentos de aplicabilidad dudosa conservan su estado explícito. Una mención en una tabla de cambios o en un Excel se registra como **PDF pendiente** hasta localizar el archivo. Si Método o Retoques necesitan conservar una copia para explicar un ensayo, preservar esa referencia y su origen. [Historia por pieza](../conocimiento/planos.md#historia-de-los-planos-por-pieza) · [Proyectos ICP y PDF correspondientes](../conocimiento/planos-globos.md) · [Detalle de la tapa de la 3288](../conocimiento/4-tetones/3288.md#tolerancias-y-rebabas-de-la-tapa)

## Método 3. Organizar la metrología solo con Excel

**Estructura acordada con Eduard el 26/11/2026.** Cada pieza tiene una sola ubicación para sus informes internos, con un Excel de referencia por variante y muestreo.

| Organización de la pieza en la copia | Dónde están los Excel de referencia |
|---|---|
| Con `4- Metrologia/Interns/` | Todos en `Interns/`, directamente o en subcarpetas de variante o de muestreo. La raíz de Metrología queda fuera de esta selección. |
| Sin `Interns/` | Todos directamente en el primer nivel de `4- Metrologia/`. Es el caso de 3051, 3197 y 3212. |

**Copias de cliente y soportes.** Se conservan en sus carpetas, por ejemplo `Customer/`, `Customers/` o `Soportes/`. Sus Excel quedan fuera de los informes de referencia en ambos esquemas, aunque falte el interno. En la 3205, `Interns/3205-00_intern.01.xls` y `Customer/3205-00_intern.01.xls` tienen el mismo nombre y distinta finalidad. También se guardan aparte los generadores de Cpk, las comparativas auxiliares, los MSA, los volcados y los PPAP de cliente. Cuando haya varias copias internas de referencia dudosa, se mantienen en su sitio hasta que INTEPLAST las identifique.

**CSV de máquina.** Son opcionales y solo sirven de comprobación. Pueden acompañar al Excel o conservarse en una carpeta de soporte. El nombre o la ruta deben permitir asociarlos al muestreo, a la cavidad y, cuando haya varias, a la variante. En la **3212** se conserva la carpeta tal como se recibió, con los nueve Excel en la raíz y los CSV en `support intern.01/`, `support intern.03/`, `support intern.05/` y `support.intern.08/`. Tampoco hacen falta carpetas por muestreo dentro de `Interns/` cuando el nombre del informe ya lo identifica.

**La reorganización la hacemos nosotros.** Primero se aplica a las 21 piezas en una copia de `Exemples`, como prueba de concepto. Luego se enseña a INTEPLAST cómo queda y cómo mejoran los resultados de la app. No se les pide que muevan nada ([próximos pasos](proximos-pasos.md#-reorganizar-metrología-de-las-21-piezas-prueba-de-concepto-24112026)).

#### Muestreo, variante y revisión

- **Muestreo** es la tanda de medición: `intern.01`, `intern.02`… Es la historia de maduración del molde: se mide, se retoca y se vuelve a medir.
- **Variante** son las dos cifras tras el código de pieza: 3237-**00**, 3237-**20**. Cada variante numera sus muestreos desde 01, así que `3168-00_intern.01` y `3168-10_intern.01` son dos mediciones distintas. INTEPLAST no ha explicado qué significan. Los PDF de la 3168-10 citan «Ultramid B3EG7» y los de la 3237-20 «Akromid», lo que apunta a otro material o versión del artículo. En `conocimiento/` se llamaba «serie».
- **Revisión** es la edición del plano medido (03, 04, 05…). Cambia dentro de una misma variante: en la 3237-00 hay informes con 03, 04 y 05. La app la lee de la casilla `Drawing level` de las 12 primeras filas de cada hoja. Si falta, toma la de otra copia del mismo muestreo y, si tampoco hay, la deja como «sin-revision».

Variantes distintas de `00`, contadas por muestreo en la biblioteca:

| Pieza | Muestreos por variante |
|---|---|
| 3056 | -00: 11 · -01: 5 |
| 3168 | -00: 15 · -10: 8 |
| 3237 | -00: 22 · -20: 11 · -10: 1 |
| 3238 | -00: 11 · -20: 6 |

Las demás piezas, Bolt Eye incluido, solo tienen `-00`. **No se elige una variante:** cada una se guarda como historial propio y se muestra con su etiqueta, por ejemplo «3237-00» y «3237-20».

#### Qué necesita la app y qué le da igual

| | Detalle |
|---|---|
| **Hace falta** | Un Excel de referencia por variante y muestreo en la ubicación acordada para esa pieza. |
| | El número de muestreo en el nombre o en la ruta: `intern`, `int`, `muestreo` o `sample` seguido de un número. |
| | La variante tras el código (`3237-20`) cuando la pieza tenga más de una. Sin ella se entiende `00`. |
| | Una hoja de medidas cuyo nombre empiece por `DR` o `CAV_N`, o contenga `100%`. Otra hoja solo se lee si su cabecera lleva la referencia ITP o PPAP de la pieza; `Hoja1` sin ella no se lee. |
| | Formato `.xls`, `.xlsx` o `.xlsm`. |
| **Opcional** | El CSV de máquina junto al Excel o en el soporte del muestreo. Si se identifica la lectura correspondiente, permite comprobar el valor del Excel. |
| **Recomendable** | `Drawing level` relleno en cada hoja, para no quedar «sin-revision». |
| | Las etiquetas de cabecera habituales: `Nominal`, `Tol +`, `Tol-`, `CAV.1`… |
| **Da igual** | Cómo se escriba el muestreo: `intern.01`, `intern2`, `int_04`, `Int_09`, `P3309-00 Int_03`. Tampoco importan las mayúsculas, el separador (espacio, punto, guion o guion bajo) ni lo que vaya tras el número (`_customer`, `including CPK`, `- Flatness`). |
| | Las subcarpetas dentro de `Interns/` (`V00`, `V20`, `Version 00`). |
| | El nombre de las carpetas que guardan documentos auxiliares fuera de la ubicación de referencia. |
| | El orden de las columnas, la fila de la cabecera (formatos A–E), el número de cavidades y si van en columnas (`CAV.1…`) o una hoja por cavidad (`cav_N`). |
| | El nombre exacto de la hoja, dentro de la pauta `DR…`, `CAV_N` o `100%`. |

**Un error de escritura no se adivina.** Si un Excel de la ubicación de referencia lleva `intren.03` y su ruta tampoco identifica el muestreo, se señala el archivo para que se revise su nombre.

**Qué preguntar a INTEPLAST**, porque no se puede deducir:

1. **Qué significan las variantes** `-00`, `-01`, `-10` y `-20`, y si comparten molde. Si lo comparten, una corrección de una variante podría aplicar a la otra.
2. **Cuál es la copia de referencia** en los muestreos repetidos dentro de `Interns/` ([lista](#cómo-están-hoy-los-excel-24112026)). Mientras no respondan, las copias dudosas se quedan en `Interns/` y la app las muestra separadas, con un aviso.
3. **Qué son `Customer/3206-00_intern.121.xls` y `.122`.** Son los únicos dos muestreos que no tienen copia en `Interns`.
4. **Si adoptan la estructura** para los informes nuevos, tras ver la prueba.

**Pendiente en la app:**

1. Leer los informes internos de una sola ubicación por pieza según la regla anterior. Comprobar los dos esquemas con 3205 (Interns y Customer) y 3212 (Excel en raíz y CSV en soportes).
2. Leer la variante del nombre y separar sus historiales. Hoy `3168-00_intern.01.xls` y `3168-10_intern.01.xls` quedan juntos como muestreo 01; si sus valores difieren, salen como series aparte con el nombre del archivo.
3. Avisar de los Excel sin muestreo reconocible en la ubicación de referencia y de los muestreos con más de un Excel interno para una misma variante.
4. **Usar el CSV solo como comprobación (decisión 3).** El código actual todavía da prioridad al CSV de la CMM cuando cubre la misma cota, muestreo y cavidad. Hay que cambiarlo así:
   - las medidas salen siempre del Excel;
   - el CSV no rellena cotas que falten en el Excel;
   - si el CSV da otro valor para la misma cota, muestreo y cavidad, se muestra un aviso con los dos valores y su origen (archivo, hoja y celda, o línea del CSV).

   **Límite que hay que tener en cuenta:** el CSV nombra los elementos con el identificador de la máquina, no con el número de cota del plano. Esa correspondencia solo está resuelta para el piloto de la 3212. En las demás piezas solo se compara cuando la cota se identifique sin ambigüedad. Si no, no se avisa y se anota como comprobación no disponible. Antes de implementarlo, contar en las 4 piezas con CSV (3167, 3197, 3212 y 3233) cuántas cotas del Excel tienen su elemento identificable en el CSV.

| Nivel | Qué debe poder recuperarse del Excel | Cómo preparar los casos actuales |
|---|---|---|
| Muestreo | Código de pieza, variante, identificador de muestreo, lote si consta, fecha de medición si se conoce y edición del informe. | Conservar `intern.NN`, identificación del lote y fecha de emisión por separado. Si dos documentos discrepan, mantener ambos con su procedencia. INTEPLAST debe identificar qué copia o bloques son de referencia. |
| Hoja o bloque | Componente o conjunto, número de plano, revisión medida y, cuando distinga dos ediciones, identificador de cambio. Método, condición o montaje cuando cambien. | Leer cabecera, rótulos de bloque y `HISTORY` cuando exista. Una cabecera ausente, heredada o contradictoria queda pendiente. Una referencia de conjunto puede convivir con otra de componente. |
| Cota | Número escrito, elemento o evaluación, nominal, tolerancias y unidad que figuran en esa revisión. | Conservar varias filas si representan mínimo, máximo, diámetro, posiciones o equipos distintos. Un número de fila no sustituye a un identificador de cota. |
| Lectura | Cavidad identificada, muestra o repetición si hay varias, valor, unidad y condición de ensayo. Origen trazable a archivo, hoja y celda. | Aceptar las cavidades que la cabecera rotula, incluso si empiezan en 9 o 13. Una columna por cavidad es válida. No hace falta partir los Excel ni crear carpetas por cavidad. Para un libro por cavidad, identificarla expresamente en el informe y conservar su muestreo. |
| Naturaleza del valor | Distinguir medido en ese muestreo, heredado, calculado, previsto, impuesto y ausente. | Pedir una marca explícita cuando haga falta. Conservar fórmulas y originales, sin recalcular los libros para preparar la entrega. Excluir de la serie de medición nueva las previsiones, las muestras generadas y los valores heredados identificados. Una coincidencia de cifras por sí sola no acredita que se copiaron. |

Se pueden conservar los formatos `.xls`, `.xlsx` o `.xlsm` originales. Un Excel de método, un generador de Cpk o una copia preparada para cliente pueden tener el mismo aspecto que un informe de medición. Documentar para cada muestreo qué Excel y qué hojas contienen mediciones, qué copia se remitió al cliente y qué queda como soporte. Si dos copias contienen medidas genuinas diferentes, identificar el ensayo o la muestra de cada una. Si cambia una tolerancia o un valor sin explicación, mantener la discrepancia abierta. Las cifras históricas proceden del Excel que se consulta. [Valores múltiples con celda de origen](../conocimiento/valores-por-punto.md) · [Contraste de hojas repetidas](../conocimiento/contraste-m3.md)

### Cómo están hoy los Excel (24/11/2026)

Consulta de solo lectura a la biblioteca de `conocimiento/` (tablas `documento` y `lectura_dr`, y celdas de la fila de cabecera). Se cuentan los `.xls/.xlsx/.xlsm/.xlsb` bajo `4- Metrologia`. **Informes** son los que se llaman `<código>-<variante>_intern.NN` o sus variantes `int.NN`, `int_NN`, `Int_NN` e `internNN`. Fuera de `4- Metrologia` hay más Excel, sobre todo en Retoques y Método; la app ya no los toma como medidas.

**Dónde están:**

| Carpeta actual | Piezas |
|---|---|
| Sueltos en la raíz de `4- Metrologia` | Bolt Eye: 3051, 3197, 3212 |
| `Interns/`, y `Customer/` o `Customers/` cuando hay copias de cliente | 3167, 3168, 3186, 3195, 3202, 3205, 3206, 3214, 3218, 3226, 3233, 3288, 3309 |
| `Interns/V00`, `V01`, `V10` o `V20`, por variante | 3056 (V00, V01), 3237 (V00, V10, V20), 3238 (V00, V20, también en `Customers/`) |
| `Version 00/Interns` y `Version 00/Customer` | 3174 |
| Sin Excel | 2820 |

**El muestreo va en el nombre en todas las piezas.** 464 de los 750 Excel tienen nombre de informe; 390 de ellos sin sufijo. Ninguna pieza tiene carpetas por muestreo ni por revisión. La variante es el número tras el código: `00` en todas, y además `01` (3056), `10` (3168, 3237) y `20` (3237, 3238).

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

**Muestreos con varias copias** (mismo `intern.NN` en más de un archivo): son lo habitual. En 3167, 3174, 3186, 3195, 3202, 3205, 3206, 3214, 3218, 3233, 3237, 3238 y 3309 hay muestreos que están en `Interns` y en `Customer`, o repetidos con sufijo. En 3056, 3168, 3237 y 3238 el mismo número aparece además en dos o más variantes, que no son copias sino mediciones distintas.

El inventario recoge 357 muestreos con nombre de informe, contados por variante y número. Dos aparecen únicamente en `Customer/`: `3206-00_intern.121.xls` y `.122`. Se conservan allí, pendientes de aclaración con INTEPLAST. **Dentro de `Interns` hay 13 muestreos con más de un Excel, en 8 piezas.**

- **Comparativas, que salen de `Interns/` por su función:**
  - `3056-00_intern7_MIN MAX COMPARISON`;
  - `3195-00_int_08_comparison humid sec`;
  - `3233-00_intern.01_comparison`;
  - `3237-00_intern.10_Comparativa_Sec_vs_Humit` y `…_comparativa old vs new`.
- **Copias cuya referencia debe decir INTEPLAST:**
  - `3195-00_Int_01.xlsm` frente a `intern.01.xls`, y lo mismo con el 02;
  - `3202-00_intern.04` y `_2`;
  - `3205-00_intern.14`, `_1` y `_2`;
  - `3206-00_intern.02_per GPF`;
  - `3206-00_intern.07_versio FM`;
  - `3218-00_intern.22` en `.xls` y `.xlsx`, más `_old`;
  - `3218-00_intern.27_VdB`;
  - `3233-00_intern_04` en `315595 - Test tracció/`.

**Otras inconsistencias de los Excel.** La app ya resuelve sin pedir nada:

- los cinco formatos de cabecera;
- las cavidades en columnas o en una hoja por cavidad;
- varias hojas de medida por libro según condición (`DR-Dry` y `DR-Conditioned`), equipo (`DR_100%` y `DR_CMM`) o componente (`DR(base)` y `DR(tapa)`).

Necesitan a INTEPLAST:

- la 3226, sin número de cota ni cavidad ([A28](preguntas-abiertas.md#a28-3226-sin-numeracion));
- los PPAP de cliente con muestras generadas por `RAND()`, que se conservan como documentación de cliente.

### Revisión de los Excel de cada pieza

Los ejemplos son localizadores relativos a `4- Metrologia` salvo indicación expresa. Una hoja sirve para encontrar el caso, no como plantilla universal de esa pieza. Las cavidades indicadas corresponden al ejemplo. El número de cavidades físicas del molde requiere su propia fuente. [Cabeceras con rutas y celdas](../conocimiento/planos.md#revisiones-que-citan-las-cabeceras) · [Identidades y excepciones por hoja](../conocimiento/identidad-piezas.md)

| Pieza | Excel u hoja de partida | Cómo organizarlo y qué resolver |
|---|---|---|
| [2820](../conocimiento/ingesta/2820.md) | Entrega con plano y STEP, sin informe. | Dejar Metrología sin muestreos e indicar «sin Excel entregado». |
| [3051](../conocimiento/ingesta/3051.md) | En raíz, `3051-00_intern.01.xls`, hojas `DR(100%)` y `DR(4CAV_CMM)`, C1–C4. | Ordenar por `intern`, conservar hojas y revisión declarada 01. En `intern.06` hay mínimo, máximo y diámetro de una misma cota. Preservar cada evaluación y los bloques heredados. |
| [3056](../conocimiento/ingesta/3056.md) | `Interns/V00/3056-00_intern.1_100%.xls`, hojas `DR (3D)` y `DR (PARAM.)` con distintas cavidades. | Mantener V00 y el muestreo. Leer por hoja la secuencia 01–04. La numeración 1200/2140 varía entre muestreos aun con el mismo nivel declarado. Evitar reconstruir la identidad por nominal. |
| [3167](../conocimiento/ingesta/3167.md) | `Interns/3167-00 Int_01.xls`, `DR_CC(P1)` y `DR_CC(P2)`, C1–C4. Hay además Excel de cliente por cavidad en `Customer/PPAP-3167-00_…`. | Mantener los bloques P1/P2 y el identificador de cavidad. Distinguir medidas propias de muestras de cliente generadas. La revisión del plano está ausente en las cabeceras revisadas. |
| [3168](../conocimiento/ingesta/3168.md) | `Interns/3168-00_intern.01.xls!DR(1)` y `3168-10_intern.01.xls!DR`, ambos con C1–C8. | Separar variantes 00/10 y condiciones de ensayo aunque coincida `intern.01`. Conservar el 01 declarado en los informes. Verificar el formato real de los archivos con extensión Excel. |
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
| [3237](../conocimiento/ingesta/3237.md) | `Interns/V00/3237-00_intern.09.xls!DR`, J6/N6, revisión 04. También existe `Interns/V20/3237-20_intern.09.xls`. | Conservar variante, lote y humedad si se declara. Hay informes 03/04/05. En la revisión 04 se consulta su gráfica mientras el plano de la app sigue siendo el 05. |
| [3238](../conocimiento/ingesta/3238.md) | `Interns/V00/3238-00_intern.07.xls!DR`, I6/M6, revisión 04. En V20 hay hojas 04 y 05 en distintos muestreos. | Separar variante, tecnología CMM/CT y condición de humedad. Los informes o archivos de comprobación de útiles tienen otra finalidad. La serie antigua conserva las tolerancias de su Excel. |
| [3288](../conocimiento/ingesta/3288.md) | `Interns/3288-00_intern.01.xls!DR(base)` y `DR(tapa)`. I6/AB6 citan el conjunto y el nivel, D14 identifica el plano del componente. | Conservar un solo libro y dos ámbitos con numeración propia. Las 20 columnas y el método que declara 16+16 requieren aclaración. Preguntar qué nivel aplica a `intern.04`. Mantener los Excel del molde 3247 como referencia histórica. |
| [3309](../conocimiento/ingesta/3309.md) | `Interns/3309-00 Int_01.xls!DR`, C1–C4. En los libros la referencia es `GF991-53540` sin revisión. | Ordenar por muestreo y mantener referencia y revisión tal como figuran. Solicitar plano numerado y correspondencia con el CAD y el PDF. |

## Método 4. Preparar los demás archivos de la pieza

| Tipo | Convención propuesta | Casos que cambian la preparación |
|---|---|---|
| CAD de producto | En Diseño, un STEP vigente por producto o componente identificado. Conservar número de pieza y revisión CAD cuando consten. | En la 3202 los STEP de útiles están en Método. En la 3288 hay dos STEP de producto (`BASE_RCP31` y `TAPA_RCP31`). En 3237 y 3238 el código de versión del STEP sigue su propia serie. |
| CAD de molde | Cuando se disponga del STEP del molde completo, se recomienda dejarlo como único STEP en el primer nivel. Los lados, electrodos y demás archivos pueden organizarse en subcarpetas con tantos STEP como corresponda. | El enlace a SharePoint funciona igualmente con varios STEP en la raíz o con un despiece sin conjunto. La 3206 contiene los dos lados y la 3056 incluye lados y electrodos. [Inventario de moldes](preguntas-abiertas.md#a29-archivo-principal) |
| Moldflow | Conservar la carpeta tal como se entrega. La página de Moldflow enlaza con su ruta en SharePoint sin inspeccionar los archivos. | En 3212 se encuentra en `7- Moldflow`. La 3206 trae un vídeo AVI. En la 3288 el README indica que no hay estudio. |
| Escaneos y fotos | Identificar pieza, componente y, si constan, lote, cavidad y fecha. Proponer una ubicación estable para las fotos si INTEPLAST confirma cómo se entregarán. | En 3288 hay `Base.stl` en el nombre de un escaneo y otro llamado `Nou`, de alcance pendiente. El escaneo guardado bajo 3309 empieza por `3218-00`. Las fotos de un retoque conservan su relación con ese lazo. |
| Piezas en varios features | Preparar una sola carpeta de datos por código. Mantener la relación con todos sus features. | 3167 y 3214 tienen remisiones en Tetones. 3205 y 3206, en Planitudes. Anclajes contiene una remisión sin identificar la pieza. Conservarla como pendiente. [Comparativa](../conocimiento/comparativa.md#pieza-por-pieza) |

## Cómo usar este documento para hacer los cambios

1. **Preparar una relación de operaciones por pieza.** Partir de su fila de planos y de su fila de Excel. Para cada archivo anotar ruta actual, destino propuesto, pieza/componente, documento, revisión/cambio, motivo, evidencia y estado. Usar «preparado», «pendiente de archivo», «pendiente de confirmación» y «comprobado» para distinguir lo ejecutable de las consultas abiertas. Conservar las rutas de origen y las referencias que se verían afectadas al mover un archivo.
2. **Resolver las decisiones que afectan al destino.** Concretar con INTEPLAST qué planos o CAD están liberados cuando su vigencia sea dudosa y cuáles son las copias de Excel de referencia. Un dato ausente puede seguir ausente. Evitar deducir una aprobación o completar una ficha para que la prueba pase.
3. **Preparar las carpetas y revisar la selección desde cero.** En una copia de trabajo, aplicar primero las operaciones documentadas. Revisar con el comportamiento previsto qué devolvería cada carpeta de Diseño, incluidas las páginas de cada PDF. Si el plan localiza una edición mejor en Método o Retoques, el cambio consiste en preparar allí la fuente y colocar el archivo acordado en Diseño. El visor no buscará excepciones fuera de esa carpeta.
4. **Comprobar cada pieza antes de darla por preparada.** El adjunto debe abrir el único PDF de la raíz con todas sus hojas. Su ICP, si existe, debe situar las marcas en el dibujo y la hoja correctos. El enlace al histórico debe abrir la carpeta de esa pieza en SharePoint.
5. **En la segunda fase, comprobar la lectura de los Excel.** Elegir una cota con datos en cada pieza que los permita y remontar un punto de la gráfica a libro, hoja, celda, revisión, cavidad y muestra. Verificar también un caso sin informe (2820), otro sin identificadores suficientes (3226), uno con copias discrepantes (3233) y otro con numeración repetida por componente (3288). En 3237, cambiar de 05 a 04 debe cambiar la gráfica, mantener el PDF 05 y dejar el acceso al antiguo en SharePoint.

### Ejemplos de operaciones para el futuro plan

Rutas relativas a la raíz de cada pieza. En los ejemplos, `Revisiones anteriores/` representa la carpeta de histórico que se utilice en esa pieza. Al preparar la copia de trabajo se pueden conservar los nombres originales de ambos archivos de una pareja PDF/ICP.

| Pieza y origen | Destino propuesto | Qué comprobar |
|---|---|---|
| 3205 · `6- Método de medición/DRW ballooned/213137-10300-B_241028/`, archivos `20241121_213137-10300-B_balloned.pdf` y `20241121_213137-10300-B.icp` | Ambos a `1- 2D y 3D pieza/` si se confirma ese cambio. La edición sustituida de 2023 y su ICP, a `1- 2D y 3D pieza/Revisiones anteriores/213137-10300/B_231011/`. | INTEPLAST identifica el cambio vigente. La B de 2024 debe usar su propio ICP y la B de 2023 debe conservarse completa. |
| 3237 · `6- Método de medición/OLD/1 - 3130589019_D_03_balloned.pdf` | `1- 2D y 3D pieza/Revisiones anteriores/3130589019/03/`. El PDF `20260914_3130589019 2D 05.pdf` ya está en Diseño. | El adjunto abre el 05. El enlace al histórico abre la carpeta de SharePoint que contiene el 03. El 04 solo se incorpora cuando se reciba su PDF. |
| 3237 · `4- Metrologia/Interns/V00/3237-00_intern.09.xls` y `4- Metrologia/Interns/V20/3237-20_intern.09.xls` | Sin mover. | Persisten los dos muestreos, cada uno con su variante, que sale del nombre (`-00`, `-20`). En el primero se recupera el nivel 04 de `DR!N6`. |
| 3237 · `4- Metrologia/Interns/V00/3237-00_intern.10_Comparativa_Sec_vs_Humit.xls` | `4- Metrologia/Soportes/`. | En `Interns/` queda solo `3237-00_intern.10.xls`. |
| 3212 · `4- Metrologia/3212-00_intern.NN.xls` (raíz) y carpetas de soporte | Conservar las rutas originales. | Los nueve Excel de la raíz son los informes internos. Las cuatro carpetas de soporte conservan los 16 CSV de cavidad para comprobación y los tres resúmenes `totes` como documentación auxiliar. |
| 3167 · `4- Metrologia/Customer/PPAP-3167-00_4/Estudis Estadístics/` (83 generadores de Cpk) | Sin mover. | Al estar fuera de `Interns/`, ya no se leen como medidas. |
| 3218 · `4- Metrologia/Interns/3218-00_intern.22.xls`, `.xlsx` y `_old.xls` | Sin mover hasta que INTEPLAST indique la referencia. | La app debe mostrarlos separados y avisar de que hay tres Excel para el mismo muestreo. |
| 3226 · `4- Metrologia/Interns/3226-00_intern.01.xls` | Sin mover. | La asignación cota–cavidad sigue pendiente hasta recibir la identificación que falta. |

**Alcance de la revisión.** Se contrastaron las 21 piezas con las fichas de ingesta, el catálogo de planos y la biblioteca SQLite de conocimiento. El 24/11 se compararon por ruta los PDF, ICP, Excel (`.xls/.xlsx/.xlsm/.xlsb`), STEP y MFR de la biblioteca con el directorio local de `Exemples`: coincidieron las 2.634 rutas. Esta comparación verifica presencia. Las revisiones, las marcas y los casos de Excel se apoyan en los cajetines, hojas y celdas ya estudiados y citados. La liberación industrial de los candidatos y la futura estructura de SharePoint requieren confirmación de INTEPLAST.
