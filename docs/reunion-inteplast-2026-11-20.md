# Reunión con INTEPLAST · 20/11/2026

Puntos para comentar hoy. Detalle y evidencias en [preguntas abiertas](preguntas-abiertas.md).

## 0. Referencia: la carpeta del 3212

- Es la pieza que mejor funciona: **un archivo de cada tipo**.
- Un plano, un STEP de pieza, un STEP de molde, un escaneo, y CSV de la CMM.
- Lo que sigue es, sobre todo, pedir que las demás piezas se parezcan a esta.
- Le falta el `.icp` y el plano es un escaneo sin texto ([A4](preguntas-abiertas.md)).

## 1. Moldes con muchos STEP

- **Qué pasa:** hay moldes troceados en decenas de archivos y no sabemos cuál es el molde.
  - 3056, 3167 y 3202: lados, puente y pieza, más 121, 58 y 34 electrodos.
  - 3233: 17 STEP. 3195: 4. 3206: solo los dos lados. 3168: dos STEP (`ECO` y `ESY`).
- **Lo ideal:** **un solo STEP del molde completo** por pieza, en la carpeta `1- 2D y 3D pieza`.
- Aunque pese mucho y no se vea en la app, sirve para la **trazabilidad**.
- Ejemplo bueno: el 3205 trae `RP-3083_Mold_Rev0`.

## 2. Planos

- **Qué pasa:**
  - Hay piezas con **muchos planos**: 3202 (11), 3205 (9), 3206 (9), 3288 (12).
  - Hay **planos de varias páginas**: 3174 y 3186 (5), 3288 base (3), 3214 (2).
  - Planos repartidos por otras carpetas: método de medición, retoques…
  - No sabemos cuál es el bueno y la app no puede elegirlo.
- **Lo ideal:**
  - **Un solo plano, el definitivo**, en `1- 2D y 3D pieza`.
  - Poner en el **nombre del PDF** el número de plano y la revisión que figuran en su cajetín. Ejemplo de nombre: `0140S00237_rev07.pdf`.
  - Si tiene `.icp`, **el `.icp` en esa misma carpeta**.
  - Los antiguos y los borradores, fuera o marcados en el nombre.
- **Planos sin cotas numeradas, pero con el Excel numerado:**
  - En 6 piezas ningún plano lleva números: 3051, 3056, 3168, 3197, 3233 y 3309.
  - Sus Excel sí numeran las cotas (de 25 a 483 cotas por pieza).
  - No podemos señalar en el plano a qué corresponde cada número.
  - Ejemplo: en la 3056, la misma cota es la 1200 en `intern5` y la 2140 en `intern7`, con el mismo nivel de plano.
  - **Pregunta:** ¿tienen un plano con globos (y `.icp`) de estas piezas? ¿De dónde sale la numeración del Excel?
  - 3186 y 3218 están igual: su único plano numerado es el de la 3174.
  - 3226 no tiene números ni en el plano ni en el Excel ([A28](preguntas-abiertas.md#a28-3226-sin-numeracion)).
- Casos raros para confirmar:
  - 3186 y 3218 tienen el plano de la 3174.
  - 3051, 3167 y 3168 solo tienen un borrador (`pendent acceptació`, `DRAFT`).
  - 3309: el plano y el STEP llevan números distintos.

## 3. Pieza con dos componentes (3288: base y tapa)

- **Qué pasa:** necesita un tratamiento especial en todo.
  - Hay dos STEP, pero el plano de la tapa solo está en la carpeta de retoques.
  - El molde (`Aufbau_Top`) y el escaneo (`Base`) puede que cubran solo uno de los dos.
  - Hay un segundo escaneo, `Nou`, que no sabemos qué es.
- **Preguntar:** ¿es habitual tener piezas con varios componentes o es un caso aislado?
- **Lo ideal:** **cada archivo con el nombre del componente**: plano, STEP, molde, escaneo y hojas Excel.
- Sin eso no se sabe a qué componente corresponde cada cota.

## 4. Cotas y trazabilidad

- **Lo ideal:** el mismo número de cota en plano, Excel, CMM y planes de corrección.
- En la **cabecera del informe Excel de cada muestreo**, indicar la pieza, el componente si hay varios, el **número de plano** y la **revisión usada en ese muestreo**. En el 3212 los informes citan el plano `0140S00237`, revisión `06`, y el PDF entregado es la `07`.
- Hay informes que citan una revisión de plano que no tenemos: 3237, 3238, 3195 y 3233 ([A26](preguntas-abiertas.md#a26-revisiones-plano)).
- El 3226 no numera las cotas ([A28](preguntas-abiertas.md#a28-3226-sin-numeracion)).
- Solo el 3212 y el 3197 traen los CSV de la CMM; el resto, solo Excel.
  - El Excel a veces repite valores de un muestreo anterior, y el CSV no.
  - ¿Guardan los CSV del resto? Si no, ¿cómo se indica en el Excel qué se volvió a medir? ([A24](preguntas-abiertas.md#a24-csv-cmm))

### Cómo entregar los CSV de la máquina

- **Formato recomendado, tal como se entrega en el Bolt Eye 3212**  
  `3212 Pump Housing/4- Metrologia/support intern.03/3212c13.csv`  
  La carpeta indica el muestreo 03 y el archivo, la pieza 3212 y la cavidad 13. La revisión `06` figura en «Drawing nº Level» del Excel `3212-00_intern.03.xls`. Basta con entregar los CSV originales de la máquina junto con el informe del muestreo.
- **Variante con la revisión en una carpeta**  
  `3212 Pump Housing/4- Metrologia/rev.06/intern.03/3212_C13.csv`  
  Sirve si se entregan solo los CSV o si en un mismo muestreo se usan dos revisiones. Cada archivo queda bajo la revisión que le corresponde.
- En ambos formatos, **un CSV por cavidad y condición de ensayo**, con pieza y cavidad en el nombre.

| Ejemplo de la entrega | Dónde está el dato | Qué pedimos |
|---|---|---|
| `3212c13.csv`, `3212_c13.csv`, `3197 C1.csv`, `c1-3197.csv` | Pieza y cavidad en el nombre. | **Los cuatro son válidos.** Para nuevos archivos proponemos `3212_C13.csv`. |
| `135ºC/500bar/3197 C1.csv` | Temperatura y presión en dos carpetas. A 600 bar el archivo se llama igual. | Incluir las condiciones en el nombre, por ejemplo `3197_C1-135ºC-500bar.csv`, para distinguir los ensayos al copiar el CSV. |
| `C8/3197.csv` | La cavidad solo aparece en la carpeta `C8`. | Llamar al archivo `3197_C8.csv`. |
| `intern.03/totes-3197.csv` | Cada columna del CSV corresponde a una cavidad. | Entregar los CSV individuales. La tabla conjunta puede acompañarlos como resumen. |
| `intern.05/3197_Diametres.csv` | Hay ocho lecturas por bloque y ninguna lleva la cavidad. | ¿A qué cavidad corresponde cada lectura? En futuras entregas, identificarla en cada archivo. |

- **Número de cota dentro del CSV.** En el 3212, `POINT 1` a `POINT 60` son puntos de medida del espesor N165 y `GLOBAL` es su resumen. Pedimos que cada medida lleve el número del plano junto al nombre del punto, por ejemplo `N165 POINT 1`, `N165 POINT 2` y `N165 GLOBAL`. Así se conserva qué se midió y dónde. [Método del 3212](../conocimiento/0-bolt-eye/3212/4-metrologia.md) · [CSV del 3197](../conocimiento/0-bolt-eye/3197.md)

## 5. Otros

- **Anclajes está vacío:** solo trae un `Readme.txt` que remite a otra pieza sin decir cuál.
  ¿Dónde están sus datos? ([A23](preguntas-abiertas.md#a23-anclajes))
- **La 2820 está prácticamente vacía:** solo plano y STEP, sin metrología ni retoques.
  ¿No tiene histórico o no nos lo pasaron? ([A7](preguntas-abiertas.md))
- **Escaneo del 3309 con nombre de otra pieza:** se llama `3218-00 316919 C1.stl`.
  Es el único de su carpeta, pero el nombre dice 3218. Confirmar que es del 3309.

## Resumen en una frase

**Una carpeta `1- 2D y 3D pieza` por pieza con lo definitivo: un plano (con su `.icp`), un STEP de
pieza y un STEP de molde, todo con el nombre del componente cuando haya varios. Como el 3212.**
