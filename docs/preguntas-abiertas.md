# Preguntas — abiertas y resueltas

> **Antes de preguntar algo a INTEPLAST, mirar aquí.** Varias de las preguntas originales se
> han resuelto leyendo los datos, sin necesidad de consultar.
>
> Última revisión documental: **2026-10-26**. El **2026-11-04** se añadieron las preguntas de la
> entrega ampliada (A17–A23), cerradas el mismo día, el **2026-11-06** la [A24](#a24-csv-cmm) y el **2026-11-08** la
> [A25](#a25-3288-tapa). Los análisis y localizadores
> viven en las fichas enlazadas; aquí se mantiene la pregunta o la resolución.

---

## 🔴 ABIERTAS — hay que preguntar a INTEPLAST

**Prioridad 1 para la próxima reunión: [A10 — acceso a los originales](#a10-acceso-originales).**
Eduard cree que están en OneDrive/SharePoint/Teams de empresa; todavía no está confirmado ni
tenemos acceso. Conseguir un contacto de informática y una biblioteca/carpeta de prueba.
El desarrollo continúa mientras tanto con el origen local de ejemplos en solo lectura.
La organización de las carpetas de piezas queda pendiente en A12.

> **Cómo se escriben estas preguntas.** Facilitar respuestas sin exigir que el interlocutor
> recuerde documentos de años anteriores. Cada pregunta va en
> tres bloques cortos: **Recordatorio** (el ancla: fichero, fecha, diapositiva, su propia frase
> textual) → **Qué no nos cuadra** (con números) → **Pregunta** (una, directa, en negrita).
> Lo de *"por qué nos importa para la BD"* es para nosotros: **no se lo mandes**.

---

<a id="a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué"></a>
### A1 · ¿Hubo más retoques y cómo se aceptaron las cotas NOK?

**Recordatorio.** El **plan de corrección de molde nº2** del 3212 está fechado el 18/03/2024
(`20240318-Mold correction_2_P3212_rev1.pptx`). Después seguisteis midiendo hasta
`intern.09`, en abril de 2025. Solo tenemos los documentos de dos correcciones. Los CSV
posteriores no muestran otro cambio grande comparable, pero **no permiten descartar retoques
pequeños**.

**Qué no nos cuadra.** En `intern.08`, la última medición 3D completa, estas tres cotas están
fuera de tolerancia **en las cuatro cavidades**:

| Cota | Debe estar entre | c13 | c14 | c15 | c16 |
|---|---|--:|--:|--:|--:|
| **N161** Ø45,4 +0,12 | 45,400 – 45,520 | 45,393 | 45,367 | 45,380 | 45,384 |
| **N165** (max) 1,35 −0,05 | 1,300 – 1,350 | 1,399 | 1,394 | 1,411 | 1,399 |
| **N265** Ø59,7 −0,1 | 59,600 – 59,700 | 59,596 | 59,585 | 59,585 | 59,599 |

Para N161, la diapositiva **2.16** propone *"reduir Ø −0,305 mm"* desde 45,731,
**por encima** del máximo. La medición posterior de c13 es 45,393, **por debajo** del
mínimo. Necesitamos confirmar qué se ejecutó y qué explica ese cambio.

Fuente de referencia de esta selección: [historial y resultados finales](../conocimiento/0-bolt-eye/3212/historial-molde.md#cómo-acabaron-las-cotas-problemáticas).

**Preguntas:**

1. **¿Hubo retoques después de la corrección nº2?** Si los hubo, nos interesan las fechas y los
   documentos que faltan.
2. **¿Bosch os firmó una concesión / desviación para estas tres cotas?** Si existe el documento,
   nos interesa.
3. **¿Se detectó que la medición posterior de N161 quedó por debajo del mínimo?**
4. **¿Qué motivó los informes posteriores hasta abril de 2025?**

<details><summary>Contexto interno (no enviar)</summary>

*Reabierta el 2026-09-15. El umbral de 0,10 mm usado en R10 no detecta los retoques de 0,02 y
0,03 mm que sí aparecen en las slides 2.3–2.5 y 2.9. El historial posterior y la eventual
concesión siguen sin confirmar. N161 muestra a la vez Ø mínimo por debajo y LP(2) máximo por
encima del límite: hay que conservar ambas evaluaciones y no resumirlo como un solo diámetro.*
</details>

---

### A3 · ¿Cuánto mide el pin del ensayo de inserción?

**Recordatorio.** El método de medida del 3212, `Pos. N287`, prescribe insertar el pin
a **0,1 mm/s**. El plano rev.07 indica **15–50 N** en un recorrido de **1 mm** (globos
288/288.1) y **0,2 mm/s** (globo 289). Los planes de corrección citan N288 y 15–50 N.

**Qué no nos cuadra.** Aparecen tres diámetros distintos para ese pin:

| Dónde | Diámetro |
|---|---|
| Método de medida | **Ø3,992** |
| Corrección 1, diapositiva **1.37** | *"el pin fa **3,93**"* |
| Corrección 2, diapositiva **2.18** | *"el pin fa **3,94**"* |

**Pregunta: ¿qué diámetro de pin, velocidad y revisión de la especificación se aplicaron
en estos ensayos?** Necesitamos reconciliar los tres diámetros y las dos velocidades.
El análisis se mantiene en [ensayos funcionales](../conocimiento/0-bolt-eye/3212/6-metodo-medida.md#ensayos-funcionales).

### Contraste de N266 y del método de medida — 17/09/2026

El contraste CSV/XLS frente al título PPTX de N266 está hecho; falta confirmar la
especificación del plano rev.06. Ver [resultado y fuentes](../conocimiento/0-bolt-eye/3212/historial-molde.md#cómo-acabaron-las-cotas-problemáticas).
El recuento de imágenes del DOCX ya está resuelto en la [ficha del método](../conocimiento/0-bolt-eye/3212/6-metodo-medida.md);
no volver a plantearlo como una pregunta al cliente.

<a id="a11--uso-exacto-de-punts_nous-y-trazabilidad-de-ejecución"></a>
### A16 · Uso exacto de PUNTS_NOUS y trazabilidad de ejecución

**Recordatorio:** en los doce pares, `PUNTS_NOUS` coincide exactamente con los últimos
150 puntos de `PUNTS`. Xavier explicó que se envía al proveedor una nube hecha con la CMM.
**Pregunta:** ¿para qué se separan esos 150 puntos y qué archivo corresponde a cada acción?
¿Dónde se confirma qué retoques se ejecutaron y en qué fecha? Un `OK` en el PPTX no permite
asumir esa confirmación. N170 mejora en GX, pero mantiene LP máximos fuera (30/32 en `.03`).
Su aceptación o eventual concesión también debe aclararse, junto a A1.

---

### A4 · Los planos 2D que tenemos son un escaneo

**Recordatorio.** El plano que nos disteis del 3212 es
`0140S00237` rev. 07, en PDF (`20250523_DRW 0140S00237_07.pdf`).

**Qué no nos cuadra.** El PDF disponible es un escaneo: los ensayos de OCR no dieron
lecturas fiables de los números de globo. Además, el plano y los informes identifican
revisiones distintas. El análisis, las fechas correctas y los resultados de OCR se mantienen
en la [ficha del plano](../conocimiento/0-bolt-eye/3212/1-pieza-2d-3d.md).

**Preguntas:**

1. **¿Nos podéis pasar un PDF con texto, SVG, DWG o CATDrawing del plano, incluidos sus globos?**
   Si solo existe escaneo, pedir una digitalización de mayor resolución, no una ampliación
   de la imagen actual. Habrá que validar las lecturas igualmente.
   *Respuesta parcial (28/10/2026, comunicada por Eduard): ya se pidió; probablemente no lo
   tienen y, en muchos casos, no disponen de versión vectorial o SVG. Se trabaja con escaneos.
   Sigue abierta la digitalización a mayor resolución.*
2. **¿Nos podéis pasar la rev.06 citada en los informes y aclarar sus cambios frente a la rev.07?**

<details><summary>Contexto interno (no enviar)</summary>

La app ya dispone de [búsqueda y revisión de posiciones de cotas](cotas-y-evidencia-web.md#indexación-y-revisiones).
Esa función admite propuestas y revisiones manuales; no convierte el OCR del escaneo en
una transcripción fiable. La fecha del nombre del PDF tampoco identifica la fecha de su revisión:
[contraste canónico](../conocimiento/0-bolt-eye/3212/1-pieza-2d-3d.md#-este-plano-no-es-el-de-los-informes).
</details>

---

### A9 · Las gráficas de contorno `PA`/`PB` no dicen a qué cota del plano corresponden

**Recordatorio.** En cada carpeta de cavidad hay 12 PDF (`PA_1..6`, `PB_1..6`) titulados
*"Compar. tol. de contorno"* sobre el `3212-00 PUMP HOUSING INNER PROFILE`, con tolerancia
±0,025 mm.

**Qué no nos cuadra.** Esos PDF **no citan ningún N-number**. Identifican lo que miden con una
numeración interna vuestra: `PERFIL_A` con los contornos **21, 31, 22, 32, 23, 33** y `PERFIL_B`
con los **25, 35, 26, 36, 27, 37**, todos comparados contra el mismo nominal `CONTORN (10)`.
Como el N-number es lo que une plano, metrología y retoques de molde, estas 144 gráficas se nos
quedan colgando fuera del sistema.

**Preguntas:**

1. **¿A qué cota del plano (N-number) corresponde esta comparación de contorno?**
2. **¿Qué diferencia hay entre los seis recorridos de un mismo perfil** (21, 31, 22, 32, 23, 33)?
   ¿Son secciones a distinta altura, posiciones angulares, o repeticiones de la misma medición?
3. **¿De dónde sale el contorno nominal `CONTORN (10)`?** No está en ninguno de los ficheros que
   tenemos, así que no podemos recalcular la comparación por nuestra cuenta.

<details><summary>Contexto interno (no enviar)</summary>

Los resultados de los contornos, su relación con los soportes geométricos y los límites
de la comparación antes/después están en [metrología](../conocimiento/0-bolt-eye/3212/4-metrologia.md)
y en el [historial del molde](../conocimiento/0-bolt-eye/3212/historial-molde.md).
La pregunta pendiente es su correspondencia con el plano, no volver a extraer esos resultados.

</details>

---

### A5 · Moldflow: no podemos abrir el `.mfr`

**Recordatorio.** En `7- Moldflow` del 3212 hay un fichero `.mfr` de 184 MB. En el *Dubte 6* nos
dijisteis que ahí están los puntos de inyección y las líneas de soldadura, y que se abren con
**Moldflow Communicator**.

**Qué no nos cuadra.** Nuestro parser no lee ese formato propietario. La documentación del
proyecto identifica **Moldflow Communicator como visor gratuito**, así que no atribuimos el
bloqueo a una licencia: faltan resultados exportados que nuestra aplicación pueda mostrar.

**Pregunta: ¿nos podéis exportar de cada estudio estas tres cosas?**

1. Una **imagen del patrón de llenado**
2. Una **imagen de las líneas de soldadura**
3. Los puntos de inyección: **número, posición, tipo y diámetro** — las cuatro variables que
   vosotros mismos dijisteis que definen la restricción

---

### A6 · ¿Qué features queremos fichar además del Bolt Eye?

**Recordatorio.** En la reunión de febrero acordamos empezar por el **Bolt Eye** del 3212
(N170 + N117), y en el *Dubte 4* nos dijisteis que las **llenties** (N118) van con la misma
filosofía pero **fichadas aparte**.

**Estado actualizado.** La entrega ampliada ya incluye otras familias; su alcance se mantiene
en la [comparativa](../conocimiento/comparativa.md). El acuerdo de febrero no basta para
priorizar su incorporación a la aplicación. El [acta del 24/09](acta-reunion-2026-09-24.md)
pide concretar piezas y features para las siguientes pruebas.

**Pregunta: ¿qué piezas y features de los ejemplos disponibles queréis incorporar primero
y quién validará el resultado?**

Las llenties del 3212 siguen siendo un caso separado del Bolt Eye. Sus cotas y acciones se
consultan en el [método de medida](../conocimiento/0-bolt-eye/3212/6-metodo-medida.md)
y en los [planes de corrección](../conocimiento/0-bolt-eye/3212/5-retoques-molde.md).

---

### A7 · Del `2820 Pump Housing` solo tenemos 2 ficheros

**Recordatorio.** El 2820 pertenece a la familia Bolt Eye de la entrega original;
la entrega ampliada de `Exemples` contiene otras familias.

**Qué no nos cuadra.** Del **2820** solo hay **dos ficheros**, los dos en `1-2D y 3D Pieza`:
el plano (`20160817_DRW_3130516933_…pdf`, de 2016) y el STEP de la pieza. No hay carpeta de
metrología, ni de retoques de molde, ni de Moldflow.

**Pregunta: ¿el 2820 tiene metrología y retoques y no nos los habéis pasado, o es una pieza
antigua sin histórico?**

---

### A8 · Los proyectos 3181 y 3157

**Recordatorio.** En la corrección de molde nº2 del 3212, diapositiva **2.1** (cota N128,
Ø21,5−0,2), escribisteis: *"De momento no tocar. **Marc ha de fer comparativa amb 3181 i
3157**"*.

**Qué no nos cuadra.** Esos dos proyectos no figuran entre las piezas con datos
del [inventario ampliado](../conocimiento/comparativa.md).

**Pregunta: ¿nos podéis pasar el 3181 y el 3157?**

Es exactamente el caso de uso de la herramienta: vosotros ya comparáis una cota problemática
con lo que pasó en otras piezas, a mano. Con esos dos proyectos podríamos demostrarlo
funcionando.

---

<a id="a10-acceso-originales"></a>
### A10 · ¿Desde donde va a leer los ficheros el servidor? *(para informatica, no para calidad)*

> ⚠️ Esta pregunta **no es de metrologia**: va dirigida a quien lleve los sistemas, no al
> interlocutor habitual. Si hace falta, se le pide que la reenvie.

**Recordatorio.** La base de conocimiento que estamos construyendo acabara corriendo en un
servidor vuestro. Los ficheros pesados de cada proyecto —en el `3212 Pump Housing`, el molde en
STEP de **247 MB**, el escaneo STL de **236 MB** y el estudio Moldflow de **184 MB**— **seguirán en su ubicación como originales**. La aplicación guarda referencias;
puede descargar una copia de lectura en caché y generar vistas ligeras. Hay que acordar
el acceso y la gestión de revisiones, aunque no se editen los originales.

**Preguntas:**

1. **¿Dónde están los originales: OneDrive, una biblioteca de SharePoint o un equipo de Teams?**
   Necesitamos el enlace a la ubicación del 3212 y saber quién la administra.
2. **¿Quién de informática puede preparar un acceso de solo lectura para la aplicación y
   las pruebas desde Eurecat mediante Microsoft Graph?** Empezar con una carpeta/biblioteca
   acotada; concretar quién registra la aplicación y autoriza los permisos.
3. **¿Todos los usuarios de esta aplicación podrán leer esos mismos archivos, o hay
   restricciones por persona/proyecto?** Esto determina cómo aplicar sus permisos.
4. **¿Cómo guardáis las revisiones y reorganizáis los archivos?** Distinguir renombrado dentro
   de la misma biblioteca, traslados entre bibliotecas y copias nuevas; confirmar si debemos
   mostrar siempre la última revisión o conservar una revisión concreta para cada muestreo.
   La elección de versiones CAD visibles en la GUI se concreta en [A15](#a15-versiones-cad-gui).

*Contexto interno (no enviar):* ya está implementada la referencia local con un UUID de
documento independiente de su ubicación. Los visores PDF/3D están comprobados con los dos
originales del 3212. Desde el 22/10/2026 hay un modo SharePoint (login delegado + Graph)
construido con la app de prueba de Eurecat; para INTEPLAST hará falta su registro de
aplicación y la ubicación de su biblioteca. La integración con EURECAT, si se prueba,
no concede acceso al entorno de INTEPLAST. Ver [ficheros-externos.md](ficheros-externos.md).

---

### A11 · ¿Podéis facilitar una exportación del molde 3212 compatible con el visor?

**Para el responsable del CAD del molde.** Al preparar la vista web de `3- 3D Molde/3212.step`,
OpenCascade necesita reparar numerosas caras en memoria y algunas siguen sin poder mallarse.
La aplicación muestra una **Vista parcial** y conserva la descarga íntegra del fichero recibido.

**Pedir:** una exportación STEP validada desde el CAD de origen y la revisión/fecha del molde
que representa. Conviene comprobarla con el conversor antes de sustituir el vínculo y guardar
la nueva entrega como una revisión distinta. Se está comprobando compatibilidad de exportación;
la vista web por sí sola no permite concluir que falten superficies en el CAD original.

→ [Vista ligera y límites](vistas-3d.md), [fichero del molde](../conocimiento/0-bolt-eye/3212/3-molde-3d.md).

---

### A12 · Ubicación de las carpetas de piezas

**Recordatorio:** cada pieza tiene una carpeta ya preparada por INTEPLAST, con sus CAD,
planos 2D, moldes y demás ficheros; por ejemplo, `3212 Pump Housing`.

**Qué no nos cuadra:** todavía no sabemos si esa organización se mantiene bajo una única
carpeta principal en Microsoft 365 o si las piezas están repartidas entre proyectos,
bibliotecas o ubicaciones. Esto determina dónde debe buscar el selector de piezas.

**Pregunta: ¿Todas las carpetas de piezas cuelgan de una misma carpeta principal o están
repartidas entre distintos proyectos o ubicaciones?**

**Contexto interno actualizado:** el adaptador local y el de SharePoint están implementados;
la configuración de la raíz y los permisos reales de INTEPLAST siguen pendientes de A10.
El selector parte del origen configurado, no descubre automáticamente todas las bibliotecas
ni resuelve las carpetas que solo remiten a otra pieza.
[Contrato y configuración](ficheros-externos.md).

---

### A13 · Incorporación de una segunda pieza con mediciones

**Prioridad de reunión:** tratar después del acceso a los originales y sus revisiones (A10).

**Pregunta:** ¿Podemos revisar una segunda pieza completa, con varios muestreos y sus
revisiones identificadas, para comprobar qué estructura y formatos se repiten? ¿Quién
de metrología podría contrastar con nosotros la primera importación?

**Confirmar:** formato de exportación CMM y unidades, identificación de revisión/muestreo/
cavidad, significado de archivos repetidos y si cada export contiene todas las mediciones
de esa combinación o hay entregas parciales. Pedir un ejemplo de cambio de revisión.

**Contexto interno (26/10/2026):** ya se recibieron los ejemplos ampliados. Hay lectura
genérica de mediciones y un contraste puntual documentado del 3197; eso no valida la
interpretación completa de otra pieza ni sus correcciones. La tarea pendiente es revisar
casos y resultados esperados con metrología. Estado y siguiente paso en la
[hoja de ruta](hoja-de-ruta.md#pendiente-generalizar-la-importación-de-correcciones-pptx).

---

### A14 · ¿Cómo se elaboran los XLS de metrología y de retoques?

**Para metrología y el responsable de los planes de corrección.**

**Recordatorio.** Del 3212 tenemos los CSV exportados por la CMM, los informes
`3212-00_intern.NN.xls` y los XLS de retoques. Los informes usan una plantilla PPAP y
añaden historial, requisitos y resultados de otros equipos o ensayos. Los XLS de retoques
incluyen propuestas y previsiones calculadas con fórmulas.

**Qué no nos cuadra.** No sabemos cómo pasan las medidas al Excel: importación automática,
macros o copia manual. Algunos bloques conservan valores de muestreos anteriores. Por
ejemplo, N117/N118 de `intern.05.xls` coincide con `.03`, mientras el CSV de `.05` contiene
valores distintos. Esto no demuestra por sí solo cómo se elaboró el informe.

**Pregunta: ¿Nos podéis enseñar cómo preparáis un `intern.NN.xls`, desde que termina la
medición hasta que emitís el informe, indicando qué se importa automáticamente, qué se
introduce a mano y qué se conserva del informe anterior?**

**Para el XLS de retoques:** ¿quién introduce los valores de retoque y las fórmulas de
previsión, y cómo indicáis después qué se ha ejecutado realmente?

**Pedir:** recorrer un ejemplo real con quien lo prepara y, si se utiliza, identificar la
plantilla, macro o herramienta de importación. Aclarar cómo distinguen medidas nuevas,
valores heredados y previsiones.

**Contexto interno (2026-09-22, no enviar):** el proceso mixto es una hipótesis, no una
confirmación del cliente. La respuesta determinará qué podemos automatizar y qué necesita
revisión humana. Una fórmula calcula una previsión; no acredita ejecución ni resultado.
Ver [metrología del 3212](../conocimiento/0-bolt-eye/3212/4-metrologia.md) y
[fórmulas y previsiones verificadas](../conocimiento/0-bolt-eye/3212/revision-2026-09-17.md).

---

<a id="a15-versiones-cad-gui"></a>
### A15 · Versiones CAD de pieza y molde: ¿cuáles tenemos y cuáles queréis en la GUI?

**Recordatorio.** En los ejemplos compartidos, como el 3212, tenemos el CAD de la pieza
y el CAD del molde, además del histórico de mediciones y retoques.

**Qué no nos cuadra.** No tenemos confirmado si los CAD entregados representan el diseño
inicial, una versión intermedia o la versión final tras los retoques. Tampoco está decidido
qué versiones deben poder consultarse desde la GUI.

**Preguntas:**

1. **¿Qué revisión representan los CAD de pieza y molde que nos habéis pasado: son los
   finales o corresponden a otra etapa?** Pedir la revisión/fecha de cada uno y, si se conoce,
   su relación con los muestreos y retoques. Confirmarlo por separado para pieza y molde.
2. **¿Queréis consultar en la GUI todas las versiones disponibles de pieza y molde, o solo
   la última vigente/aprobada?** Si queréis el histórico, ¿cuál debe aparecer por defecto?

**Aclarar:** qué significa «última» para vosotros: archivo más reciente o última revisión
aprobada. Si interesan las anteriores, confirmar cuáles se conservan y dónde están.

**Contexto interno (2026-09-22, no enviar):** esta decisión afecta al selector de versiones,
la vista y descarga del CAD y su relación con la metrología y las correcciones. Complementa
la gestión técnica de originales de A10. No asumir que un CAD recibido es final ni que las
revisiones de pieza y molde coinciden. La política de la GUI queda pendiente de su respuesta.

---

## Preguntas de la entrega ampliada (añadidas el 04/11/2026)

> **Revisadas y cerradas el 04/11/2026** (dos pasadas con el revisor y relectura final contra
> las fuentes; Eduard pidió darlas por terminadas). Listas para enviar después de A10.
> Salen de las 31 incongruencias
> abiertas de [incongruencias.md](../conocimiento/incongruencias.md); cada pregunta cita en su
> contexto interno los identificadores, y la [tabla de correspondencia](#correspondencia-con-las-incongruencias-abiertas)
> indica dónde queda cada una. Las cifras proceden de esa ficha, comprobadas allí en los originales.
> Prioridad propuesta, después de A10: A17, A20 y A22; luego A19 y A23; A21 al final.
> A18 solo se envía si Eduard lo decide.

<a id="a17-versiones-informes"></a>
### A17 · Copias del mismo informe con valores o tolerancias distintos: ¿cuál es la válida?

**Recordatorio.** En varias piezas hay dos o más copias del mismo muestreo (interna, de cliente,
«Desviacions aplicades») sin nada que indique cuál vale, y en una cota la tolerancia cambia
entre informes sucesivos.

**Qué no nos cuadra.**

| Pieza · informe | Diferencia entre copias |
|---|---|
| 3309 `Int_03` | Cota 14: 0,749–0,781 en `3309-00 Int_03.xls` y 0,84–0,90 en `P3309-00 Int_03.xls`. Solo la segunda cuadra con *«#14 and #16 are now in tolerance»* |
| 3202 `intern.03` | Cota 312 (2 ±0,09): la copia interna da 12 de 12 fuera y la de cliente 0 de 12, con los valores de `PPAP-3202-00_INF.01` de 01/2024 |
| 3174 `intern.26` | Cota 504: mismos valores, ±0,15 en la copia de cliente frente a ±0,07 (0/24 y 6/24 fuera) |
| 3168 `intern.12` | Cota 1540: mismos valores, −0,1 frente a −0,05/−0,07 (0/96 y 71/96 fuera) |
| 3167 `Inf_04` | La versión «Desviacions aplicades» amplía tolerancias (p. ej. 2580: −0,05 → −0,1) y cambia 8 valores medidos; la copia de `Uploaded to IQS` conserva los originales |
| 3197 N230 (informes sucesivos) | +0,13 en `intern.09/.10` y `correction04`, +0,10 en `intern.11` y en el plano |

**Preguntas:**

1. **Cuando hay varias copias de un mismo muestreo, ¿cuál es la que se entregó al cliente y
   cuál debemos tomar como medida?**
2. **¿Las tolerancias más amplias corresponden a desviaciones aprobadas por el cliente?** Si
   existe el documento de aprobación (por ejemplo, para 2730/2740 del 3167), nos interesa.

<details><summary>Contexto interno (no enviar)</summary>

I-006, I-007, I-603 e I-206; también I-203 (hoja `DR(4CAV_CMM) (2)` del 3051 repetida de
01/2021 a 02/2023). Una tolerancia distinta no demuestra por sí sola una modificación indebida.
La cadena de corrección ya conserva las copias como alternativas; la respuesta decide cuál se
muestra por defecto, no si se borra alguna.
</details>

<a id="a18-cpk-generator"></a>
### A18 · ¿Para qué se usa el libro «Cpk generator»? *(solo si Eduard decide enviarla)*

**Recordatorio.** En los ejemplos hay 114 libros con la hoja `INTRO` del «Cpk generator»
(3167, 3174, 3195, 3233, 3237) y varios informes PPAP con muestras calculadas por fórmulas
aleatorias, a partir de otra muestra o entre límites escritos en la fórmula
(3233, 3237, 3238, 3218, 3174, 3206).

**Qué no nos cuadra.** Esos valores salen de fórmulas aleatorias, no de la CMM, y no sabemos
para qué se usaron. Nuestra aplicación no los cuenta como medidas.

**Pregunta: ¿para qué usáis el «Cpk generator» y las muestras calculadas, y qué ficheros se
envían al cliente?** Nos basta con saber cómo distinguir lo medido de lo calculado.

<details><summary>Contexto interno (no enviar)</summary>

I-003. Pregunta delicada: afecta a informes PPAP; queda por confirmar qué versiones se
entregaron y para qué se utilizaron. La redacción evita juicios.
Seguimiento pendiente en [AVANCE.md](../conocimiento/AVANCE.md) («lo decide Eduard»). La app
ya excluye esos valores sin necesidad de respuesta.
</details>

<a id="a19-planos"></a>
### A19 · Planos que faltan o no corresponden a la pieza

**Recordatorio.** Cada pieza trae su plano en `1- 2D y 3D pieza`.

**Qué no nos cuadra.**

- **3186:** el plano es `6494730` rev 002 (`20230123_6494730_002.pdf`) y el STEP de la pieza,
  `20220929_6541691.stp`.
- **3218:** el plano es una copia exacta del plano del 3174 (`6494730` rev 004,
  `20250219_6494730_004.pdf`) y el STEP de la pieza, `20230503_6546952.stp`.
- El único plano del **3051** se llama `…0140S00275-DRW_pendent acceptació.pdf`.
- En el **3288**, el método `MM732880000_rev00.pdf` (p. 6) identifica la **DIM. Nº 80** del
  **conjunto** BSG-296-00, nivel 2; la versión anterior lo describe como item 8 sin número de
  cota. No tenemos el plano de ese conjunto.

**Preguntas:**

1. **¿Nos podéis pasar los planos propios del 3186 (STEP 6541691) y del 3218 (STEP 6546952)?**
2. **¿El plano del 3051 es el vigente o hay una versión aceptada posterior?**
3. **¿Nos podéis pasar el plano del conjunto BSG-296-00 del 3288, donde está la DIM. 80, y
   decirnos cómo se corresponden sus cotas con las de los planos de componente y los informes?**

<details><summary>Contexto interno (no enviar)</summary>

I-301, I-205 e I-106. Complementa A4 (plano del 3212). No equiparar la DIM. 80 con la cota de
BASE rev1 de nominal 14,45.
</details>

<a id="a20-planes-correccion"></a>
### A20 · Planes de corrección: cuáles faltan y cuál se ejecutó

**Recordatorio.** Los planes de corrección (PPTX) son la «lesson learned» de cada pieza; los
leemos por carpeta y fecha.

**Qué no nos cuadra.**

| Pieza | Situación |
|---|---|
| 3197 | Hay `3197-00_intern.09_correction04.xls`, pero solo PPTX de los planes 1–3 |
| 3218 | No encontramos los planes de los loops 2–5 |
| 3206 | Tres versiones de la diapositiva 2 tras los postizos: +0,15/+0,3 (23/07), +0,05/+0,25 (29/07) y otra `_customer` con valores por zona |
| 3205 | El PPTX base del loop 5 lleva la cabecera *«Pla de correccions nº1 – P3206»* y el mismo texto que planes del 3206 |
| 3174 | El plan del loop 2 (34 diapositivas) contiene 30 diapositivas con el mismo texto que el plan 1 del 3186 |
| 3167 | `2n loop of corrections/20240214_Mold correction_1_P3167.pptx` se llama plan 1, pero sus correcciones se numeran 2.1 y 2.5–2.11 (con 2.10 repetida); la versión PDF del plan 2 fecha sus diapositivas el 14/02/2023, dentro de una carpeta y un fichero de 2024 |
| 3168 | En `20230823_Modification/` hay un `20260612_3167_modification proposal.xlsx`: el nombre cita el 3167, pero su contenido (comparación de radios *ITP vs COMPETITOR*) no identifica ninguna pieza |

**Preguntas:**

1. **¿Existen el PPTX del plan 4 del 3197 y los planes de los loops 2–5 del 3218?**
2. **En el 3206, ¿qué versión del plan se ejecutó?**
3. **¿Las diapositivas del 3206 dentro del 3205, y las del 3186 dentro del 3174, se
   aplicaron también a esas piezas o están ahí como referencia?**
4. **En el 3167, ¿el fichero `20240214_Mold correction_1_P3167.pptx` es el plan 1 o el plan 2,
   y en qué fecha se hizo ese plan?**
5. **El `20260612_3167_modification proposal.xlsx` guardado en la carpeta del 3168, ¿corresponde
   al 3167 o al 3168?**

<details><summary>Contexto interno (no enviar)</summary>

I-202, I-305, I-401, I-402, I-309, I-601 e I-702. La cadena de corrección ya avisa de estos
casos; la respuesta decide a qué pieza se atribuyen las acciones. Relacionada con A1/A16: un
`OK` no confirma ejecución. I-702: atribución pendiente; comprobado el 04/11/2026 que el
contenido extraído (`Hoja1`, filas 2–41) no cita ninguna pieza, así que no se atribuye al
3167 por su nombre ni se mezcla con el historial del 3168.
</details>

<a id="a21-plantillas"></a>
### A21 · Cabeceras heredadas de otra pieza en los informes

**Recordatorio.** Varios informes reutilizan la plantilla PPAP de otra pieza.

**Qué no nos cuadra.** Informes del 3218, 3186 y 3206 (y `3288-00_intern.01-base_1_stadistics.xls`)
llevan la cabecera del 3247 (*ITP* 732470000, *PPAP* `3247-00_int.01`); en los del 3218, 3186
y 3206 el cliente figura además como `B-Braun`.
En el 3218, 184 hojas de 62 libros indican *PPAP Ref.* **3281** con el ITP y el número de pieza
del 3218. En el 3288, el número de cliente 509131 sale de hojas heredadas del 3247, mientras el
método indica 508008.

**Preguntas:**

1. **¿El 3281 es otra pieza o una errata en los informes del 3218?**
2. **¿Cuál es el número de cliente correcto del 3288?**

<details><summary>Contexto interno (no enviar)</summary>

I-303, I-105, I-108, I-310 e I-104. La app ya marca estas cabeceras y no atribuye identidad
por ellas; las respuestas solo afinan los avisos. Prioridad baja.
</details>

<a id="a22-3288"></a>
### A22 · 3288: número de cavidades y columnas de los informes

**Recordatorio.** El método del 3288 dice *«Nº cavidades molde: 16+16 (de 1 a 16)»* y Foboha
*«16 fach»*.

**Qué no nos cuadra.** Los informes tienen **20 columnas de cavidad** con valores en todas y las
diapositivas citan las cavidades 17–20. Además, la columna 29 (comentarios) de los `DR` lleva un
número (15, 16, 17…) en cada fila, y en `intern.03` la hoja `DR(tapa)` está fechada el
22/05/2026 y el resto del libro el 23/06/2026.

**Preguntas:**

1. **¿El molde del 3288 tiene 16 o 20 cavidades por componente?**
2. **¿Qué significa el número de la columna 29?**
3. **¿Qué fecha es la correcta en `intern.03`?**

<details><summary>Contexto interno (no enviar)</summary>

I-101, I-107 e I-103. La cavidad afecta a cómo se agrupan las medidas; es la más importante.
</details>

<a id="a23-anclajes"></a>
### A23 · El feature Anclajes no trae datos

**Recordatorio.** La carpeta `5- Anclajes` solo contiene un `Readme.txt`.

**Qué no nos cuadra.** El texto dice que la información *«ya fue entregada anteriormente»*,
pero no indica en qué pieza ni carpeta.

**Pregunta: ¿en qué pieza o carpeta de la entrega están los datos de Anclajes?**

<details><summary>Contexto interno (no enviar)</summary>

I-501. Puede estar repartido en carpetas de otros features; no se ha encontrado por nombre.
</details>

<a id="a24-csv-cmm"></a>
### A24 · ¿Guardáis los CSV de la CMM del resto de piezas?

*Añadida el 06/11/2026. Es la que más dudas de lectura resolvería: se propone enviarla junto con A17.*

**Recordatorio.** Del 3212 y del 3197 tenemos los ficheros que exporta la CMM en cada muestreo, en carpetas como
`4- Metrologia/support.intern.08/C13/13_3212.csv` y `4- Metrologia/Support_intern.03/`.

**Qué no nos cuadra.** Del resto de piezas solo tenemos los informes Excel, y sin el CSV no podemos saber qué valor es
de ese muestreo cuando el informe trae más de uno o repite uno anterior. Dos ejemplos del 3212, donde sí podemos comprobarlo:

| Informe | Cota 113, cavidad 13 | CSV de ese muestreo |
|---|---|---|
| `3212-00_intern.05.xls`, `DR(100%)!H25` | 3,056, igual que en `intern.03` | 3,042 |
| `3212-00_intern.08.xls`, `DR!H25` y `DR!H52` | 3,297 y 3,074, los dos en la misma hoja | 3,074 |

**Preguntas:**

1. **¿Guardáis los CSV de la CMM de las demás piezas y nos los podéis pasar?**
2. **Si en alguna pieza no se exportan, ¿de dónde salen los valores de CMM de sus informes?**

<details><summary>Contexto interno (no enviar)</summary>

I-001, I-008; [valores por punto](../conocimiento/valores-por-punto.md#contraste-con-los-csv). Exportes de máquina por
muestreo: 3212 (19) y 3197 (118). Sin ninguno: 3051, 3056, 3168, 3186, 3195, 3202, 3205, 3206, 3214, 3218, 3226, 3288 y 3309.
Con CSV sueltos que no sirven para contrastar muestreos: 3167, 3174, 3233, 3237 y 3238. Del 2820 no hay ninguna metrología:
eso ya lo pregunta [A7](#a7--del-2820-pump-housing-solo-tenemos-2-ficheros). Los CSV solo cubrirían lo medido con CMM, no
el escáner CT, las galgas ni el Keyence. Se solapa con [A14](#a14--cómo-se-elaboran-los-xls-de-metrología-y-de-retoques),
que pregunta cómo pasan las medidas al Excel; esta pide los ficheros.
</details>

<a id="a25-3288-tapa"></a>
### A25 · 3288, tapa: tolerancias de cuatro cotas y medición de rebabas

*Añadida el 08/11/2026, después de contrastar plano, diapositivas, informes y PDF. Solo recoge lo que los documentos no resuelven.*

**Recordatorio.** Planes de corrección de la tapa del 3288: `20260430_Mold correction_1_P3288_TAPA`, `20260525_Mold
correction_2_P3288_TAPA` y `20260525_Mold correction_3_P3288_TAPA`, este último junto a `DR-3288_intern03_flashes.pdf`
en la carpeta `20260622_3rd loop of correction`.

**Qué no nos cuadra.**

- Los títulos de las correcciones 1.2, 1.3, 1.4, 2.2 y 2.3 dicen *«89,95 ± 0,03 and 42,95 ± 0,03»*, *«4,1 ± 0,01»* y
  *«Ø 3,15 ± 0,01»*. El plano BSG-296-02 rev 1, los informes y la tabla de la propia diapositiva dicen ±0,3 y ±0,1.
- En la medición de rebabas con lupa, 45 de las 144 celdas dicen `> 0,05`.
- La corrección 3.2 (cota 115) junta los puntos 2, 3.1, 3.2 y 3.3, pero en el plano el globo 115 señala un solo agujero.
- En `intern.04`, las cotas 115 a 120 valen 0 en todas las cavidades. La inspección visual de Foboha de la inyección del
  18/09/2026 marca rebabas *Critical* en algunos agujeros.
- Hay dos `3288-00_intern.03.xls`, uno en Metrología y otro en la carpeta del tercer loop, con rebabas distintas. La tabla
  de rebabas de la corrección 2.2 coincide con `3288-00_intern02.xlsx`, no con `3288-00_intern.02.xls`.

**Preguntas:**

1. **¿±0,03 y ±0,01 son una errata de ±0,3 y ±0,1, o hay una revisión del plano de la tapa con esas tolerancias?**
2. **¿Qué significa `> 0,05` en las rebabas: menos de 0,05, o más de 0,05 sin anotar cuánto?**
3. **¿La cota 115 incluye los agujeros 3.1, 3.2 y 3.3, o esos van por la nota general de ±0,20?**
4. **En `intern.04`, ¿el 0 de las cotas 115 a 120 es «sin rebaba» o que no se midieron?**
5. **Cuando un informe tiene dos versiones (`intern.02` e `intern.03` de la tapa), ¿cuál es la de referencia?**

<details><summary>Contexto interno (no enviar)</summary>

I-109 a I-113; detalle y efecto en los recuentos en [3288](../conocimiento/4-tetones/3288.md#tolerancias-y-rebabas-de-la-tapa).
La cadena sigue con la tolerancia del informe y con el origen del plan 3 inferido (`intern.02` por fecha) hasta la respuesta.
La 1 cambia poco: todas las demás fuentes dicen ±0,3 y ±0,1. Las 3 y 4 son las que más mueven los recuentos del plan 3.
La 5 se solapa con [A17](#a17-versiones-informes): si se envía A17, basta con añadir allí estos dos casos.
</details>

### Correspondencia con las incongruencias abiertas

Las 31 entradas `abierta` de [incongruencias.md](../conocimiento/incongruencias.md) a
04/11/2026. Las `explicable`, `resuelta` y `corregida` no se preguntan.

| Incongruencia | Dónde queda |
|---|---|
| I-001 bloques repetidos entre informes | [A14](#a14--cómo-se-elaboran-los-xls-de-metrología-y-de-retoques) (cómo se elaboran los XLS) |
| I-003 valores generados con RAND | [A18](#a18-cpk-generator), solo si Eduard lo decide |
| I-005 *Customer Name* poco fiable | No se pregunta: se resuelve con reglas en [identidad-piezas.md](../conocimiento/identidad-piezas.md) |
| I-006, I-007, I-603, I-206, I-203 copias, versiones y tolerancias | [A17](#a17-versiones-informes) |
| I-101, I-103, I-107 (3288) | [A22](#a22-3288) |
| I-104, I-105, I-108, I-303, I-310 cabeceras heredadas | [A21](#a21-plantillas) |
| I-106, I-205, I-301 planos | [A19](#a19-planos) |
| I-202, I-305, I-309, I-401, I-402, I-601 planes de corrección | [A20](#a20-planes-correccion); I-601 en la pregunta 4 |
| I-702 fichero rotulado 3167 en la carpeta del 3168 | [A20](#a20-planes-correccion), pregunta 5; atribución pendiente hasta la respuesta |
| I-204 variantes de la corrección 2 del 3212 | [A16](#a11--uso-exacto-de-punts_nous-y-trazabilidad-de-ejecución) y [A1](#a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué) |
| I-207 velocidad de inserción del 3212 | [A3](#a3--cuánto-mide-el-pin-del-ensayo-de-inserción) |
| I-501 Anclajes sin datos | [A23](#a23-anclajes) |
| I-008 varios valores por cota, muestreo y cavidad (añadida el 06/11/2026) | [A24](#a24-csv-cmm) |
| I-109 a I-113 tolerancias y rebabas de la tapa del 3288 (añadidas el 08/11/2026) | [A25](#a25-3288-tapa) |
| I-602 planes del 3056 solo en imagen | No se pregunta: es un límite de nuestra lectura (OCR o lectura visual); pedir texto solo si se prioriza el 3056 |
| I-701 carpeta del 3168 fechada en 2027 | No se pregunta: la fecha de carpeta no se usa como fecha de ejecución; no cambia la lectura |

---

## Historial de conclusiones revisadas

<a id="r10--hubo-una-tercera-corrección-de-molde-era-a1"></a>
### R10 · Conclusión retirada: tercera corrección de molde

**Reabierta como A1 el 2026-09-15.** Esta entrada se conserva para que los enlaces y el historial
de la revisión no oculten que la conclusión anterior cambió; **no es una pregunta resuelta**.

La comparación posterior no descarta retoques pequeños. El método, su calibración y los
bloques heredados de informes se conservan en
[historial del molde, sección 8](../conocimiento/0-bolt-eye/3212/historial-molde.md#8-hubo-una-tercera-corrección-de-molde--no).

**Pendiente:** confirmar las intervenciones posteriores y la aceptación de cotas NOK con
[A1](#a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué). No tratar diferencias
medidas o marcadores `OK` como confirmación documental de ejecución.

---

## ✅ RESUELTAS con los datos (no hace falta preguntar)

### R9 · Las diapositivas sin cota identificada *(era A2)*

**Resuelto leyendo las imágenes de los PPTX.** Las acciones sobre el plano A agrupan
varias cotas; 2.13 identifica N240. La tabla completa, recortes y rutas dentro del ZIP
se mantienen en [retoques del molde](../conocimiento/0-bolt-eye/3212/5-retoques-molde.md).
El contraste medido está en [historial, plano A](../conocimiento/0-bolt-eye/3212/historial-molde.md#6-la-segunda-prueba-el-plano-a).

### R1 · ¿Qué `intern.NN` corresponde a cada retoque de molde?

**Resuelto.** Los XLS que acompañan a los planes identifican los muestreos de origen.
La cronología y el par antes/después de cada plan se mantienen en
[historial del molde](../conocimiento/0-bolt-eye/3212/historial-molde.md#1-cronología).

### R2 · ¿A qué muestreo pertenece el STL?

**Resuelto a nivel de lote:** el STL pertenece a una tirada compartida por dos informes;
no permite elegir uno de ellos como fecha exacta del escaneado. Ver
[ficha del STL y sus fuentes](../conocimiento/0-bolt-eye/3212/8-stl-pieza-real.md#el-nombre-codifica-tres-cosas).

<a id="r3--cuál-es-la-versión-buena-entre-rev0--rev1--rev1_"></a>
### R3 · Diferencias entre variantes rev0 / rev1 / rev1_

**Diferencias auditadas el 23/10/2026.** Las variantes de corrección 2 cambian magnitudes
y marcadores. La selección del piloto es explícita; no demuestra cuál se ejecutó ni qué
variante aprobó el cliente. Mantener la comparación y la regla de selección en
[Qué fichero usar](../conocimiento/0-bolt-eye/3212/5-retoques-molde.md#qué-fichero-usar).

### R4 · ¿Dónde se documenta la corrección? (Dubte 5)

En **PPTX + XLS de retoques**. El PPTX explica la propuesta y muestra la zona; `DR(100%)`
del XLS aporta retoques, previsiones por cavidad y fórmulas encadenadas. La ejecución debe
confirmarse por separado. La respuesta de Xavier habla de nubes hechas con CMM, sin
identificar un archivo como geometría objetivo. `PUNTS_NOUS` es un subconjunto de PUNTS;
su uso exacto y vínculo a acciones se recogen en [A16](#a16--uso-exacto-de-punts_nous-y-trazabilidad-de-ejecución).

### R5 · ¿Funcionó el retoque del Bolt Eye?

**Mejora parcial, no resolución completa.** Hay que conservar GX y LP máximo por agujero
y altura; la conformidad de GX no permite dar por aceptado el conjunto. Valores y fuentes:
[historial del Bolt Eye](../conocimiento/0-bolt-eye/3212/historial-molde.md#4-bolt-eye-n170-mejora-parcial-no-resolución-completa).

### R6 · ¿Cómo se calcula la posición ⌖? *(Dubte 2)*

**Verificado numéricamente.** La fórmula y el ejemplo de contraste están en
[Formatos y parsing](../conocimiento/formatos-parsing.md#verificación-del-cálculo-de-posición-confirma-la-respuesta-del-dubte-2).

### R7 · ¿Qué significan `GX`, `GN`, `LP(2)`?

**Resuelto.** Definiciones y diferencias de evaluación en el
[vocabulario del método de medida](../conocimiento/0-bolt-eye/3212/6-metodo-medida.md#2-vocabulario-de-evaluación).

### R8 · ¿Por qué se mide el agujero a dos alturas? *(Dubte 7)*

**Resuelto.** El cilindro interior es largo y lleva **grados de conicidad** para poder expulsar
la pieza. El cliente quiere Ø y posición arriba y abajo. Lo regula una **nota de ángulo de
desmoldeo** en el plano, no la tolerancia de posición.

---

## 📋 Preguntas originales a INTEPLAST y sus respuestas

Las 9 preguntas (*dubtes*) que se enviaron y las respuestas de **Xavier Arcos** (Metrology
Manager) están en **`inteplast_resposta_dubtes.md`**, en el vault de Obsidian
(`C:\edu\projects\Inteplast\`), con sus imágenes. Resumen:

| # | Tema | Respuesta clave |
|:--:|---|---|
| 1 | Ejes y error de B1 | B1 se usa para alinear → solo puede tener error en X. Los otros 3, en ambos sentidos. |
| 2 | Cálculo de la posición ⌖ | `2 · √(ΔX² + ΔZ²)`. Siempre positivo, 0 = perfecto. |
| 3 | Planitud del plano A | Es la referencia de alineación. Influencia **indirecta y de magnitud baja**, pero *"puede pasar de OK a NOK tocando ese plano"*. |
| 4 | Cotas N118 (llenties) | Misma filosofía, pero **ficharlo aparte** del bolt eye. |
| 5 | Dónde está la acción en el molde | Nube de puntos de la CMM al proveedor + los PPTX de corrección. |
| 6 | Puntos de inyección y líneas de soldadura | En los `.mfr` de `7- Moldflow`, con **Moldflow Communicator**. No hay correlación hecha con el error de posición. Restricciones: **posición, número, diámetro y tipo**. |
| 7 | Medida a dos alturas | **Conicidad de desmoldeo**. Lo fija una nota del plano o un acuerdo con el cliente. |
| 8 | Parámetros de máquina | **No van en la BD**: dependen de la geometría global, el material, el molde y la máquina. Demasiadas variables no ligadas al feature. |
| 9 | Calibre del diámetro | Es un **calibre pasa** de producción. *"No creo que sea importante."* |
