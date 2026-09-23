# Preguntas — abiertas y resueltas

> **Antes de preguntar algo a INTEPLAST, mirar aquí.** Varias de las preguntas originales se
> han resuelto leyendo los datos, sin necesidad de consultar.
>
> Última revisión: **2026-09-22**

---

## 🔴 ABIERTAS — hay que preguntar a INTEPLAST

**Prioridad 1 para la próxima reunión: [A10 — acceso a los originales](#a10-acceso-originales).**
Eduard cree que están en OneDrive/SharePoint/Teams de empresa; todavía no está confirmado ni
tenemos acceso. Conseguir un contacto de informática y una biblioteca/carpeta de prueba.
El desarrollo continúa mientras tanto con el origen local de ejemplos en solo lectura.
La organización de las carpetas de piezas queda pendiente en A12.

> ⚠️ **Cómo se escriben estas preguntas.** El interlocutor de INTEPLAST no se acuerda de lo que
> hizo — estos datos son de 2024 y 2025 — y tiene poca paciencia para leer. Cada pregunta va en
> tres bloques cortos: **Recordatorio** (el ancla: fichero, fecha, diapositiva, su propia frase
> textual) → **Qué no nos cuadra** (con números) → **Pregunta** (una, directa, en negrita).
> Lo de *"por qué nos importa para la BD"* es para nosotros: **no se lo mandes**.

---

<a id="a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué"></a>
### A1 · ¿Hubo más retoques y cómo se aceptaron las cotas NOK?

**Recordatorio.** El 18/03/2024 hicisteis la **corrección de molde nº2** del 3212
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

Y en N161 os pasasteis de largo: en la diapositiva **2.16** pedíais *"reduir Ø −0,305 mm"*
partiendo de 45,731, que estaba **por encima** del máximo. Acabó en 45,393, **por debajo** del
mínimo. Cruzó la tolerancia de lado a lado.

**Preguntas:**

1. **¿Hubo retoques después de la corrección nº2?** Si los hubo, nos interesan las fechas y los
   documentos que faltan.
2. **¿Bosch os firmó una concesión / desviación para estas tres cotas?** Si existe el documento,
   nos interesa.
3. **¿Se detectó en su momento que N161 se había pasado al otro lado?**
4. **¿Qué motivó los informes posteriores hasta abril de 2025?**

<details><summary>Contexto interno (no enviar)</summary>

*Reabierta el 2026-09-15. El umbral de 0,10 mm usado en R10 no detecta los retoques de 0,02 y
0,03 mm que sí aparecen en las slides 2.3–2.5 y 2.9. El historial posterior y la eventual
concesión siguen sin confirmar. N161 muestra a la vez Ø mínimo por debajo y LP(2) máximo por
encima del límite: hay que conservar ambas evaluaciones y no resumirlo como un solo diámetro.*
</details>

---

### A3 · ¿Cuánto mide el pin del ensayo de inserción?

**Recordatorio.** En el método de medida del 3212 tenéis el ensayo de los N287/N288: se mete un
pin en el agujero del bolt eye a 0,1 mm/s y se registra la fuerza máxima, que debe caer entre
**15 N y 50 N**.

**Qué no nos cuadra.** Aparecen tres diámetros distintos para ese pin:

| Dónde | Diámetro |
|---|---|
| Método de medida | **Ø3,992** |
| Corrección 1, diapositiva **1.37** | *"el pin fa **3,93**"* |
| Corrección 2, diapositiva **2.18** | *"el pin fa **3,94**"* |

**Pregunta: ¿cuál es el pin que se usa realmente, y los otros dos números qué son?**
(¿un pin distinto, un desgaste, una medida de otra cosa?)

### Contraste de N266 y del método de medida — 17/09/2026

CSV y tablas XLS usan **67,1 +0,1**; el título PPTX de 1.24/2.8 dice **67,1 −0,1**.
El contraste ya está hecho. Falta confirmar cuál es la especificación en el plano rev.06,
no volver a deducir el signo por la frase sobre añadir acero. Según CSV/XLS, `.08` cumple.
El DOCX tiene **55 imágenes: 43 PNG + 8 JPEG + 4 JPG**; el desglose anterior omitía `.JPG`.

### A11 · Uso exacto de PUNTS_NOUS y trazabilidad de ejecución

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

**Qué no nos cuadra.** Ese PDF **no tiene texto**: dentro hay **una sola imagen JPEG de
3276×2317 px** y **cero fuentes**. Todo lo que se saque de él es una reconstrucción por OCR, y al
ampliar se pixela.

**Y es el único sitio donde se ve dónde está cada cota.** Los N-numbers **no aparecen en ningún
otro fichero con su posición**: en las nubes de puntos (`3212_Cav13.txt`, `3212_PUNTS.txt`) **no
hay ni una letra** — son tres columnas de coordenadas — y las gráficas de contorno `PA_*/PB_*`
usan una numeración interna suya (`Contorno (21)`, `CONTORN (10)`). El único sitio donde un
N-number aparece **junto al punto de la pieza al que se refiere** es el plano.

**🆕 Qué hemos podido hacer nosotros (2026-08-18).** Montamos un visor con OCR
([`ver_plano.py`](../prototypes/data-explorer/planos/ver_plano.py)) y el resultado acota mucho la petición:

- ✅ **Las notas se leen bien** (1.504 palabras, confianza media 74).
- ✅ **Confirmado que los N-numbers SÍ están en el plano**, en **globos verdes y sin la `N`**:
  el racimo del Bolt Eye pone `170`, `170.2` … `170.7` junto a la cota `Ø4 −0,1 (4x)`. Hemos
  localizado **178 globos**.
- ❌ **Pero el número de dentro no se puede leer.** Mide ~9 píxeles. Con Tesseract sale basura;
  con RapidOCR **parece** que sale bien y es peor: auditando 16 lecturas al azar contra la imagen,
  **solo 6 son correctas (37 %)**, y falla `155`→`156` **con 0,99 de confianza**. Los errores son
  de un dígito y no hay forma de detectarlos. Lo hemos quitado de nuestras herramientas.
- ❌ **Los marcos GD&T son ilegibles** (`⌖0,15 A-B` sale como `[1]`, `G97]`), y el símbolo `Ø` se
  lee como `9`/`@`/`$`.

O sea: **la petición no es un lujo, es la única salida.** Hoy el mapeo `N-number → zona de la
pieza` solo se puede hacer **a mano, ampliando globo a globo**, sobre 178 globos y para cada una
de las cuatro piezas. Con texto seleccionable, incluidos los globos, sería mucho más fiable; habría que validar el mapeo.

**Y si el CAD nativo no es posible, nos vale una alternativa más sencilla: el mismo plano
escaneado a más resolución.** El actual son 3276×2317 px (~198 DPI) y las cifras de los globos
miden 9 píxeles. Una digitalización real a 600 DPI podría ayudar, pero su precisión debe auditarse; reescalar la imagen actual no recupera detalles.

Y además **no es el plano de vuestros informes**: todos los informes, hasta `intern.09` de abril
de 2025, dicen `Drawing nº Level: 06`. El PDF que tenemos es la **rev. 07, del 23/05/2025** —
posterior a toda la metrología.

**Preguntas:**

1. **¿Nos podéis pasar el plano en un formato con texto** — PDF vectorial, **SVG**, DWG o el
   CATDrawing nativo? Nos vale cualquiera de los cuatro. Con el escaneo actual el mapeo
   `N-number → zona de la pieza` **hay que hacerlo a mano, globo a globo**: los números están
   impresos, pero a 9 píxeles ningún OCR los lee.
2. **¿Nos podéis pasar la rev. 06**, que es la que corresponde a las mediciones?

<details><summary>Contexto interno (no enviar)</summary>

*Verificado el 2026-08-13. Sin el plano vectorial, el mapeo `N-number → zona de la pieza` solo se
puede hacer (a) a mano sobre la imagen, (b) por OCR sobre los globos del plano, o (c) por anclaje
geométrico: cruzar el nominal del CSV con la nube de puntos, que funciona para las cotas
circulares pero deja fuera las que no están en la nube (N161/N162/N163) y las no circulares.
→ [3212/4-metrologia.md](3212/4-metrologia.md)*

*Actualización 2026-08-18: la vía (b) queda **descartada, y esta vez con la medida hecha**.
Tesseract da basura evidente. RapidOCR parecía funcionar (131 N-numbers "leídos") pero al auditar
16 lecturas al azar contra la imagen solo 6 eran correctas: **37 %**, con fallos de un dígito y
confianza de 0,99. Se ha quitado de `ver_plano.py`, que ahora solo LOCALIZA los globos y explica
por qué hay que pedir otro plano. Queda la vía (a), a mano.
→ [visores.md](visores.md) · [3212/1-pieza-2d-3d.md](3212/1-pieza-2d-3d.md)*
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

*Estos PDF son **fuente única**: la comparación contra el perfil teórico no está en el CSV ni es
recalculable desde las nubes (⚠️ el `3212_CONTORN.igs` es el contorno **escaneado**, no el
nominal). Y son valiosos: prueban que la corrección nº1 dividió por 5,5 la desviación del
contorno en las 4 cavidades a la vez.
→ [3212/4-metrologia.md](3212/4-metrologia.md), [3212/historial-molde.md](3212/historial-molde.md)*
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

**Qué no nos cuadra.** Nada — es una decisión vuestra que aún no está tomada. Mirando vuestros
datos, estos son los candidatos que aparecen solos:

| Candidato | Por qué sale |
|---|---|
| **Llenties** | N242 (L1…L6, variantes A y B) + N118. Ya lo dijisteis vosotros. Aparece en las correcciones 1.35 y 2.9. |
| **Diámetros del perfil interior** | N161 / N162 / N163 — los que más se resistieron: hicieron falta las dos correcciones y N161 acabó fuera igual |
| **Espesores locales** | N165, con 60 secciones medidas cada 6° |
| **Tubuladuras** | N127 / N283 (Ø16,3−0,3) + cilindricidad N152 / N153, con el ensayo de estanqueidad |
| **Nervios** | Solo aparece en el 3197 (`3197_Punts_nervis_Frontal*.csv`) |

**Pregunta: ¿cuáles de estos cinco queréis que fichemos, y en qué orden?**

---

### A7 · Del `2820 Pump Housing` solo tenemos 2 ficheros

**Recordatorio.** En la carpeta `Exemples` nos disteis cuatro proyectos: 2820, 3051, 3197 y 3212.

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

**Qué no nos cuadra.** Esos dos proyectos no están entre los que nos disteis — en `Exemples`
solo hay 2820, 3051, 3197 y 3212.

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
STEP de **247 MB**, el escaneo STL de **236 MB** y el estudio Moldflow de **184 MB**— **no se van
a copiar dentro de la aplicacion**: la idea es que sigan donde ya estan y que la aplicacion los
lea de ahi. Asi no hay dos copias de vuestro archivo CAD ni nada que sincronizar.

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
originales del 3212. Conectar Graph requerirá implementar su acceso e identificar los archivos
de INTEPLAST; no basta con sustituir la ruta local. La integración con EURECAT, si se prueba,
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

→ [Vista ligera y límites](vistas-3d.md), [fichero del molde](3212/3-molde-3d.md).

---

### A12 · Ubicación de las carpetas de piezas

**Recordatorio:** cada pieza tiene una carpeta ya preparada por INTEPLAST, con sus CAD,
planos 2D, moldes y demás ficheros; por ejemplo, `3212 Pump Housing`.

**Qué no nos cuadra:** todavía no sabemos si esa organización se mantiene bajo una única
carpeta principal en Microsoft 365 o si las piezas están repartidas entre proyectos,
bibliotecas o ubicaciones. Esto determina dónde debe buscar el selector de piezas.

**Pregunta: ¿Todas las carpetas de piezas cuelgan de una misma carpeta principal o están
repartidas entre distintos proyectos o ubicaciones?**

**Contexto interno (2026-09-17):** hasta confirmarlo, la aplicación asume una carpeta principal
común y presenta sus subcarpetas directas. Seleccionar una registra o reutiliza la pieza sin
crear ni modificar carpetas originales. El adaptador local es temporal; acceso y permisos
de SharePoint/OneDrive siguen pendientes en A10.

---

### A13 · Incorporación de una segunda pieza con mediciones

**Prioridad de reunión:** tratar después del acceso a los originales y sus revisiones (A10).

**Pregunta:** ¿Podemos revisar una segunda pieza completa, con varios muestreos y sus
revisiones identificadas, para comprobar qué estructura y formatos se repiten? ¿Quién
de metrología podría contrastar con nosotros la primera importación?

**Confirmar:** formato de exportación CMM y unidades, identificación de revisión/muestreo/
cavidad, significado de archivos repetidos y si cada export contiene todas las mediciones
de esa combinación o hay entregas parciales. Pedir un ejemplo de cambio de revisión.

**Contexto interno (2026-09-21):** Features registra/reutiliza la pieza desde su carpeta;
el flujo CSV permite revisar e incorporar mediciones y después asociar cotas al feature.
Las importaciones comparten datos entre features y conservan versiones. El lector actual
cubre el formato CMM por bloques, con pruebas sintéticas de otra pieza. Aún no se ha
validado una segunda pieza real ni la generalización de correcciones XLS/PPTX.

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
Ver [metrología del 3212](3212/4-metrologia.md) y
[fórmulas y previsiones verificadas](3212/revision-2026-09-17.md).

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

Se compara el valor medido de cada fila entre dos muestreos. Antes de concluir, se **calibra el
método** sobre un tramo donde sabemos que sí hubo retoque (`intern.03 → .05`, con la corrección
nº2 en medio):

| Tramo | ¿Corrección en medio? | Filas | **Δ ≥ 0,10 mm** | Δ máx |
|---|---|--:|--:|--:|
| `intern.03 → .05` | ✅ la nº2 | 211 ×4 cav. | **129 en cada cavidad** | 0,335–0,349 mm |
| `intern.05 → .08` | ❓ | 211 ×4 cav. | **0 en las cuatro** | 0,055–0,081 mm |

El retoque conocido nº2 coincide con **129 de 211 filas movidas más de 0,10 mm en cada cavidad**.
Entre `intern.05` e `intern.08` no hay cambios por encima de ese umbral y el máximo es 0,081 mm.
Esto **no descarta retoques menores**: las slides 2.3–2.5 documentan 0,02 mm y la 2.9, 0,03 mm.
La afirmación previa de que 0,081 mm era menor que cualquier acción documentada era incorrecta.

`intern.09` no tiene CSV y combina medidas con bloques copiados. La comparación utilizable
en este análisis fue `N162`:
49,858 (`.05`) → 49,855 (`.08`) → 49,840 (`.09`). El cambio de **−0,015 mm entre `.08` y `.09`**
en esa cota tampoco permite excluir una intervención.

> **Pendiente:** confirmar con INTEPLAST si hubo más correcciones y cómo se aceptaron las cotas
> NOK → [A1](#a1--se-cerró-el-molde-con-3-cotas-fuera-de-tolerancia--por-qué).

**De regalo**, el tramo de control valida las acciones de la corrección nº2 una por una
(N161 −0,335 vs −0,305 pedidos; N162 +0,201 vs 0,22; N266 +0,124 vs 0,14; N265 +0,089 vs 0,11)
**y confirma [R9](#r9--las-diapositivas-sin-cota-identificada-era-a2)**: la slide 2.13, que
identificamos como `N240` leyendo una imagen, pedía bajar 0,08 mm — y N240 bajó 0,057 mm.

🔴 **Hallazgo colateral:** el bloque `N117`+`N118` de `intern.09.xls` (02/04/2025) es **copia
literal de `intern.01`** (25/01/2024) — los 32 valores idénticos, 15 meses después — y sus
`N275`/`N276` son copia de `intern.08`. Tercer caso de copia-pega detectado.

→ Todo el detalle en [3212/historial-molde.md §8](3212/historial-molde.md#8-hubo-una-tercera-corrección-de-molde--no).

---

## ✅ RESUELTAS con los datos (no hace falta preguntar)

### R9 · Las diapositivas sin cota identificada *(era A2)*

**Resuelto el 2026-08-11 leyendo las imágenes del PPTX.** No hacía falta preguntar: el
N-number **sí está en la diapositiva**, pero no en el texto, sino **dentro del recorte del
informe** que ilustra el bloque *Current situation*. La primera columna de ese recorte es la
columna `Nr` del `DR(3D)`.

| Slide | Retoc | N-numbers |
|---|:--:|---|
| **1.16** | +0,29 | `N155` · `N258` · `N267` · `N268` |
| **1.17** | +0,29 | `N154` · `N165` · `N166` · `N167` |
| **1.18** | +0,29 | `N236` · `N237` · `N240` · `N241` · `N252` · `N256` |
| **2.3** | +0,02 | `N154` · `N155` · `N258` · `N267` · `N268` |
| **2.4** | +0,02 | `N165` · `N166` · `N167` |
| **2.5** | +0,02 | `N236` · `N237` · `N240` · `N241` · `N252` · `N256` |
| **2.13** | −0,08 | `N240` |

🔑 **Las 6 primeras no son "diapositivas sin cota": son la diapositiva del PLANO A.** Las tres
comparten *la misma imagen de zona roja* (`image54.png` en la corr. 1 = `image12.png` en la
corr. 2, byte a byte 101.725 B), y en ella lo marcado en rojo es **la brida perimetral
completa**. No llevan `DIM. Nr.` porque el retoque no es de una cota: es un **desplazamiento de
la referencia** que arrastra a un grupo de cotas a la vez. Eso explica el `0,29 mm` que citan
las slides 1.27 (N236) y 1.28 (N243) como *"tocar el pla A"*.

**2.13 es distinta**: sí es una cota concreta, `N240` (18,5 +0,2 /5). El recorte del plano lleva
el globo `[]240` rodeado en rojo con una flecha.

**Evidencia** (ficheros y rutas dentro del ZIP):

| Qué | Dónde |
|---|---|
| Slides huérfanas corr. 1 | `ppt/slides/slide15.xml`, `slide16.xml`, `slide17.xml` = 1.16/1.17/1.18 *(desfase de 1 por la slide 5/37 que falta)* |
| Slides huérfanas corr. 2 | `ppt/slides/slide3/4/5/13.xml` = 2.3/2.4/2.5/2.13 *(sin desfase)* |
| Recortes con el N-number | corr. 1 → `image50,55,56,57` (1.16), `58,59,60,61` (1.17), `62,66,67,68,69,70` (1.18) · corr. 2 → `image13-16` (2.3), `17,18` (2.4), `22-26` (2.5), `48` (2.13) |
| Zona roja = plano A | corr. 1 `image54.png` · corr. 2 `image12.png` |

Validado que **todas** las imágenes de los `_rels` están realmente colocadas: el número de
`r:embed` distintos del `slideN.xml` coincide con el número de relaciones de imagen.

→ Detalle en [3212/5-retoques-molde.md](3212/5-retoques-molde.md) y la comprobación numérica
de que el retoque se aplicó en [3212/historial-molde.md](3212/historial-molde.md#6-la-segunda-prueba-el-plano-a).

### R1 · ¿Qué `intern.NN` corresponde a cada retoque de molde?

**Resuelto.** El enlace está en el **nombre del `.xls`** que acompaña a cada PPTX:
`3212-00_intern.01_mold_correction.xls`, `3212-00_intern.03_correction_2_.xls`. Las fechas
confirman (reunión 1–4 días alrededor del informe).

| Corrección | Origen | Validación |
|---|---|---|
| nº1 (24/01/2024) | `intern.01` (25/01/2024) | `intern.03` (14/03/2024) |
| nº2 (18/03/2024) | `intern.03` | `intern.05` (01/05/2024) |

Además la corrección 2 **audita explícitamente** la 1 en el texto de sus diapositivas, y 12 de
18 llevan un marcador `OK`. → [3212/historial-molde.md](3212/historial-molde.md)

### R2 · ¿A qué muestreo pertenece el STL?

**Resuelto.** `3212-315346-c13.stl` → lote **315346** = `Parts batch nº` de **`intern.03`
(14/03/2024) y `intern.04` (15/04/2024)**. Ambos comparten lote, así que el escaneado
corresponde a esa tirada — la **posterior a la corrección nº1**.

### R3 · ¿Cuál es la versión buena entre rev0 / rev1 / rev1_?

El prototipo usa corrección 1 `rev1` y corrección 2 `rev1` sin guion bajo final.
**Rectificado 17/09/2026:** los dos PPTX de corrección 2 no son idénticos byte a byte:
8.024.315 y 8.024.918 B. No asumir equivalencia por tamaño redondeado o nombre.
`Old/` conserva una versión anterior del XLS. Falta auditar diferencias entre variantes
si se quiere automatizar su selección; guardar siempre qué archivo se utilizó.

### R4 · ¿Dónde se documenta la corrección? (Dubte 5)

En **PPTX + XLS de retoques**. El PPTX explica la propuesta y muestra la zona; `DR(100%)`
del XLS aporta retoques, previsiones por cavidad y fórmulas encadenadas. La ejecución debe
confirmarse por separado. La respuesta de Xavier habla de nubes hechas con CMM, sin
identificar un archivo como geometría objetivo. `PUNTS_NOUS` es un subconjunto de PUNTS;
su uso exacto y vínculo a acciones se recogen en A11.

### R5 · ¿Funcionó el retoque del Bolt Eye?

**Mejora parcial, no resolución completa.** GX de N170, c13 B1 H=1,5:
3,429 → 3,974 → 3,981 → 3,978. LP máximo del mismo elemento:
3,477 → 4,018 → 4,023 → 4,023, frente a máximo admisible 4,000.
En `.03`, 0/32 GX están fuera, pero sí 30/32 LP máximos. No concluir que quedó aceptado
porque desaparezca del segundo PPTX. [Fuentes](3212/revision-2026-09-17.md).

### R6 · ¿Cómo se calcula la posición ⌖? *(Dubte 2)*

**Verificado numéricamente** contra los datos reales:
`2 · √(ΔX² + ΔZ²) = 2 · √(0,006² + 0,011²) = 0,0251 ≈ 0,026` ✅

### R7 · ¿Qué significan `GX`, `GN`, `LP(2)`?

**Resuelto** con el método de medida: `GX` = Ø mínimo, `GN` = Ø máximo, `LP(2)` = distancia
directa entre dos puntos opuestos a la misma altura.
→ [3212/6-metodo-medida.md](3212/6-metodo-medida.md#2-vocabulario-de-evaluación)

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
