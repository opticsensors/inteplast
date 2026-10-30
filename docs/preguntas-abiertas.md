# Preguntas — abiertas y resueltas

> **Antes de preguntar algo a INTEPLAST, mirar aquí.** Varias de las preguntas originales se
> han resuelto leyendo los datos, sin necesidad de consultar.
>
> Última revisión documental: **2026-10-26**. Los análisis y localizadores viven en
> las fichas enlazadas; aquí se mantiene la pregunta o la resolución.

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
