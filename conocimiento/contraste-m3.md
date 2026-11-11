# Contraste en los originales de las hojas de M3 (P-2 y P-5, 11/11/2026)

**Qué se contrasta.** M3 de `revision.py` encuentra hojas cuyo `intern.NN` del nombre no coincide con el muestreo
que cita su cabecera (`ppap_ref`). En la biblioteca se midió qué parte de sus valores (cota, cavidad, valor) está
también en el muestreo citado ([destino de las comprobaciones](revision-comprobaciones.md#m3)):

- **P-2:** al menos el 90 %, en las piezas que no estaban contrastadas. 3218 y 3174 ya lo estaban y están en I-001.
- **P-5:** entre el 30 y el 90 %.

**Alcance.** Las conclusiones valen para las hojas contrastadas. Revisar una muestra no cierra las demás hojas de su
grupo. Una repetición confirmada son valores idénticos en dos informes: no dice si se volvió a medir ni por qué.

**Herramienta:** `conocimiento/herramientas/contraste_m3.py`. Primero `muestra`, que solo consulta la biblioteca;
después `contrastar`, que lee los originales sobre copias temporales, en solo lectura y con las macros desactivadas.

## Muestra (fijada antes de abrir los originales)

- **P-2:** las 14 hojas del grupo, todas.
- **P-5:** una hoja por pieza, 11 de las 35, elegida al azar con la semilla `20261111`.

Se reproducen los grupos del 11/11: de las 124 hojas de M3, 47 con al menos el 90 %, 35 entre el 30 y el 90 %, 35 por
debajo del 30 % y 7 sin medidas. Cada hoja se compara con la hoja del libro citado que más claves comparte en la
biblioteca, decidida también antes de abrir nada.

| Grupo | Pieza | Hoja del caso | Cabecera | Coincidencia (biblioteca) | Se compara con |
|---|---|---|---|---|---|
| P-2 | 3186 | `Customer/3186-00_intern.08.xls!DR_100%` | `3186-00_int.15` | 97,7 % | `Interns/3186-00_intern.15.xls!DR_100%` |
| P-2 | 3186 | `Interns/3186-00_intern.09.xls!DR_100%` | `3186-00_int.08` | 100 % | `Interns/3186-00_intern.08.xls!DR_100%` |
| P-2 | 3195 | `Interns/3195-00_intern.02.xls!DR_param` | `3195-00_int.01` | 100 % | `Interns/3195-00_intern.01.xls!DR_param` |
| P-2 | 3205 | `Customer/3205-00_intern.14_2.xls!DR` | `3205-00_int.11` | 98,9 % | `Interns/3205-00_intern.11.xls!DR` |
| P-2 | 3205 | `Interns/3205-00_intern.14.xls!DR` | `3205-00_int.11` | 99,4 % | `Interns/3205-00_intern.11.xls!DR` |
| P-2 | 3205 | `Interns/3205-00_intern.14.xls!DR (customer)` | `3205-00_int.11` | 100 % | `Interns/3205-00_intern.11.xls!DR (customer)` |
| P-2 | 3205 | `Interns/3205-00_intern.14_1.xls!DR` | `3205-00_int.11` | 98,9 % | `Interns/3205-00_intern.11.xls!DR` |
| P-2 | 3205 | `Interns/3205-00_intern.14_1.xls!DR (customer)` | `3205-00_int.11` | 98,6 % | `Interns/3205-00_intern.11.xls!DR (customer)` |
| P-2 | 3205 | `Interns/3205-00_intern.14_2.xls!DR` | `3205-00_int.11` | 98,9 % | `Interns/3205-00_intern.11.xls!DR` |
| P-2 | 3205 | `Interns/3205-00_intern.14_2.xls!DR (customer)` | `3205-00_int.11` | 98,6 % | `Interns/3205-00_intern.11.xls!DR (customer)` |
| P-2 | 3238 | `Customers/V00/3238-00_intern05_customer.xls!DR` | `3238-00_int.03` | 93,9 % | `Customers/V00/3238-00_intern.03-a.xls!DR_100%` |
| P-2 | 3238 | `Interns/V00/3238-00_intern.04.xls!DR_100%` | `3238-00_int.03` | 95,3 % | `Customers/V00/3238-00_intern.03-a.xls!DR_100%` |
| P-2 | 3238 | `5- Retoques molde/20240904_3rd loop of corrections/3238-00_intern04_corr.xls!DR_100%` | `3238-00_int.03` | 94,7 % | `Customers/V00/3238-00_intern.03-a.xls!DR_100%` |
| P-2 | 3168 | `Interns/3168-00_intern.14.xls!DR` | `3168-00_int.13` | 99,2 % | `Interns/3168-00_intern.13.xls!DR` |
| P-5 | 3051 | `3051-00_intern.09.xls!DR(4CAV_CMM) (2)` | `3051-00_int.01` | 35,6 % | `3051-00_intern.01.xls!DR(4CAV_CMM)` |
| P-5 | 3174 | `Version 00/Customer/3174-00_intern.26.xls!DR_100%` | `3174-00_int.08` | 32,2 % | `Version 00/Interns/3174-00_intern.08.xls!DR_100%` |
| P-5 | 3186 | `Interns/3186-00_intern.16.xls!DR` | `3186-00_int.13` | 79,4 % | `Interns/3186-00_intern.13.xls!DR_100%` |
| P-5 | 3205 | `Interns/3205-00_intern.06.xls!DR_100%` | `3205-00_int.02` | 76,5 % | `Customer/3205-00_intern.02.xls!DR_100%` |
| P-5 | 3206 | `Customer/3206-00_intern19.xls!DR` | `3206-00_int.18` | 69,2 % | `Customer/3206-00_intern.18_Customer.xls!DR` |
| P-5 | 3212 | `3212-00_intern.02.xls!DR(100%)` | `PPAP-3212-00_int.01` | 64,7 % | `3212-00_intern.01.xls!DR(100%)` |
| P-5 | 3214 | `Interns/3214-00_int.05.xls!DR_L_Mig_1` | `3214-00_int.04` | 50 % | `Interns/3214-00_int.04.xls!DR` |
| P-5 | 3218 | `Customer/Version 00/3218-00_intern.05_Set No.3.xls!DR_100% (customer)` | `3281-00_int.15` | 72 % | `Interns/3218-00_intern.15.xls!DR_100%` |
| P-5 | 3233 | `Interns/3233-00_intern.04.xls!100% (CUSTOMER)` | `3233-00_int.03` | 58,4 % | `Interns/3233-00_intern.03.xls!100% (CUSTOMER)` |
| P-5 | 3237 | `Interns/V00/3237-00_intern.10.xls!DR` | `3237-00_int.09` | 88,7 % | `Interns/V00/3237-00_intern.09.xls!DR` |
| P-5 | 3238 | `Interns/V00/3238-00_intern.08.xls!DR` | `3238-00_int.07` | 87,4 % | `Interns/V00/3238-00_intern.07.xls!DR` |

## Cómo se compara y cómo se clasifica

Fijado antes de abrir los originales y precisado tras la revisión del 11/11/2026 (ver *Correcciones*).

- **Clave:** cota, cavidad y número de muestra dentro de esa cota y cavidad, en orden de fila y columna. No se
  compara por posición, porque las filas pueden estar desplazadas entre libros (3174 `intern.09`). Las coordenadas
  salen de `medida_dr` y el valor se lee del original. Se cuenta aparte cuándo no coincide con el de la biblioteca.
- **Recuentos,** sobre las medidas de la hoja del caso:
  - **excluidas:** celdas con `RAND()` (I-003) y ceros, cuyo significado no está confirmado (I-002), en cualquiera
    de las dos hojas;
  - **sin pareja:** la clave no está en la hoja comparada;
  - **comparadas:** el resto.

  El total es la suma de las tres. «% de la hoja» es sobre las medidas no excluidas.
- **Repetición confirmada:** al menos el 90 % de las medidas comparables con el mismo valor, con 20 comparables como
  mínimo.
- **Confirmada en parte:** un bloque de al menos 5 filas seguidas completas, con 10 valores de tres decimales o más
  dentro del propio bloque. Una fila completa tiene todas sus medidas, salvo las excluidas, con pareja y el mismo
  valor. Vale cualquier bloque que cumpla, aunque no sea el más largo. Una coincidencia de valores redondos puede
  ser casualidad; un bloque así, difícilmente.
- **Sospecha descartada con evidencia:** al menos 20 medidas comparables, menos del 30 % iguales y ningún bloque de
  5 filas completas.
- **Pendiente por falta de evidencia:** el resto, con el motivo: pocas medidas comparables, coincidencias sueltas o
  con pocos decimales, original ilegible.

## Resultados (11/11/2026)

**Lectura de los originales.** En las 25 hojas, lo leído coincide con la biblioteca en todas las celdas comparadas.
Excel se abrió en cálculo manual para leer los valores guardados.

| | Confirmada (≥90 % de las comparables) | Confirmada en parte | Pendiente | Descartada |
|---|---|---|---|---|
| P-2 (14 hojas, todo el grupo) | 14 | 0 | 0 | 0 |
| P-5 (11 de 35 hojas) | 3 | 5 | 3 | 0 |

| Grupo | Pieza | Hoja del caso → hoja comparada | Medidas | Excluidas | Sin pareja | Comparadas | Iguales | Bloque que cumple | Bloque más largo, si es otro | Resultado |
|---|---|---|---|---|---|---|---|---|---|---|
| P-2 | 3186 | `Customer/3186-00_intern.08.xls!DR_100%` → `Interns/3186-00_intern.15.xls!DR_100%` | 172 | 0 | 0 | 172 | 168: 97,7 % de las comparables, 97,7 % de la hoja | 38 filas (19–57), 140 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3186 | `Interns/3186-00_intern.09.xls!DR_100%` → `Interns/3186-00_intern.08.xls!DR_100%` | 1.280 | 0 | 0 | 1.280 | 1.280: 100,0 % de las comparables, 100,0 % de la hoja | 321 filas (14–335), 557 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3195 | `Interns/3195-00_intern.02.xls!DR_param` → `Interns/3195-00_intern.01.xls!DR_param` | 432 | 0 | 0 | 432 | 432: 100,0 % de las comparables, 100,0 % de la hoja | 36 filas (14–49), 388 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Customer/3205-00_intern.14_2.xls!DR` → `Interns/3205-00_intern.11.xls!DR` | 1.448 | 1 | 0 | 1.447 | 1.431: 98,9 % de las comparables, 98,9 % de la hoja | 88 filas (139–235), 80 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14.xls!DR` → `Interns/3205-00_intern.11.xls!DR` | 1.448 | 1 | 0 | 1.447 | 1.439: 99,4 % de las comparables, 99,4 % de la hoja | 92 filas (16–121), 355 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14.xls!DR (customer)` → `Interns/3205-00_intern.11.xls!DR (customer)` | 1.112 | 1 | 0 | 1.111 | 1.111: 100,0 % de las comparables, 100,0 % de la hoja | 139 filas (15–194), 250 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14_1.xls!DR` → `Interns/3205-00_intern.11.xls!DR` | 1.448 | 1 | 0 | 1.447 | 1.431: 98,9 % de las comparables, 98,9 % de la hoja | 88 filas (139–235), 80 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14_1.xls!DR (customer)` → `Interns/3205-00_intern.11.xls!DR (customer)` | 1.104 | 1 | 0 | 1.103 | 1.087: 98,5 % de las comparables, 98,5 % de la hoja | 80 filas (104–193), 80 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14_2.xls!DR` → `Interns/3205-00_intern.11.xls!DR` | 1.448 | 1 | 0 | 1.447 | 1.431: 98,9 % de las comparables, 98,9 % de la hoja | 88 filas (139–235), 80 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3205 | `Interns/3205-00_intern.14_2.xls!DR (customer)` → `Interns/3205-00_intern.11.xls!DR (customer)` | 1.104 | 1 | 0 | 1.103 | 1.087: 98,5 % de las comparables, 98,5 % de la hoja | 80 filas (104–193), 80 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3238 | `V00/3238-00_intern05_customer.xls!DR` → `V00/3238-00_intern.03-a.xls!DR_100%` | 492 | 0 | 0 | 492 | 461: 93,7 % de las comparables, 93,7 % de la hoja | 55 filas (14–68), 112 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3238 | `V00/3238-00_intern.04.xls!DR_100%` → `V00/3238-00_intern.03-a.xls!DR_100%` | 636 | 0 | 8 | 628 | 606: 96,5 % de las comparables, 95,3 % de la hoja | 55 filas (14–68), 112 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3238 | `20240904_3rd loop of corrections/3238-00_intern04_corr.xls!DR_100%` → `V00/3238-00_intern.03-a.xls!DR_100%` | 636 | 0 | 8 | 628 | 602: 95,9 % de las comparables, 94,7 % de la hoja | 55 filas (14–68), 112 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-2 | 3168 | `Interns/3168-00_intern.14.xls!DR` → `Interns/3168-00_intern.13.xls!DR` | 1.024 | 0 | 0 | 1.024 | 1.016: 99,2 % de las comparables, 99,2 % de la hoja | 111 filas (31–141), 555 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-5 | 3051 | `3051-00_intern.09.xls!DR(4CAV_CMM) (2)` → `3051-00_intern.01.xls!DR(4CAV_CMM)` | 1.092 | 219 | 533 | 340 | 199: 58,5 % de las comparables, 22,8 % de la hoja | — | — | Pendiente: 199 de 340 iguales, sin bloque que cumpla: ningún bloque de 5 filas completas |
| P-5 | 3174 | `Customer/3174-00_intern.26.xls!DR_100%` → `Interns/3174-00_intern.08.xls!DR_100%` | 2.192 | 0 | 48 | 2.144 | 673: 31,4 % de las comparables, 30,7 % de la hoja | 48 filas (98–145), 344 con decimales | — | **Confirmada en parte** |
| P-5 | 3186 | `Interns/3186-00_intern.16.xls!DR` → `Interns/3186-00_intern.13.xls!DR_100%` | 1.276 | 0 | 0 | 1.276 | 1.013: 79,4 % de las comparables, 79,4 % de la hoja | 36 filas (146–181), 61 con decimales | 52 filas (89–140), 0 con decimales | **Confirmada en parte** |
| P-5 | 3205 | `Interns/3205-00_intern.06.xls!DR_100%` → `Customer/3205-00_intern.02.xls!DR_100%` | 952 | 0 | 168 | 784 | 728: 92,9 % de las comparables, 76,5 % de la hoja | 11 filas (42–52), 64 con decimales | 76 filas (63–179), 0 con decimales | **Confirmada** (≥90 % de las comparables) |
| P-5 | 3206 | `Customer/3206-00_intern19.xls!DR` → `Customer/3206-00_intern.18_Customer.xls!DR` | 712 | 4 | 0 | 708 | 467: 66,0 % de las comparables, 66,0 % de la hoja | 30 filas (133–162), 57 con decimales | — | **Confirmada en parte** |
| P-5 | 3212 | `3212-00_intern.02.xls!DR(100%)` → `3212-00_intern.01.xls!DR(100%)` | 1.550 | 0 | 743 | 807 | 498: 61,7 % de las comparables, 32,1 % de la hoja | — | 5 filas (74–78), 7 con decimales | Pendiente: 498 de 807 iguales, sin bloque que cumpla: 5 filas con 7 valores de tres decimales |
| P-5 | 3214 | `Interns/3214-00_int.05.xls!DR_L_Mig_1` → `Interns/3214-00_int.04.xls!DR` | 8 | 0 | 0 | 8 | 4: 50,0 % de las comparables, 50,0 % de la hoja | — | 1 filas (17–17), 0 con decimales | Pendiente: solo 8 medidas comparables |
| P-5 | 3218 | `Version 00/3218-00_intern.05_Set No.3.xls!DR_100% (customer)` → `Interns/3218-00_intern.15.xls!DR_100%` | 2.656 | 1 | 32 | 2.623 | 1.899: 72,4 % de las comparables, 71,5 % de la hoja | 41 filas (19–59), 199 con decimales | — | **Confirmada en parte** |
| P-5 | 3233 | `Interns/3233-00_intern.04.xls!100% (CUSTOMER)` → `Interns/3233-00_intern.03.xls!100% (CUSTOMER)` | 5.663 | 2.358 | 0 | 3.305 | 3.305: 100,0 % de las comparables, 100,0 % de la hoja | 115 filas (15–211), 1.300 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-5 | 3237 | `V00/3237-00_intern.10.xls!DR` → `V00/3237-00_intern.09.xls!DR` | 640 | 4 | 12 | 624 | 568: 91,0 % de las comparables, 89,3 % de la hoja | 50 filas (15–69), 100 con decimales | — | **Confirmada** (≥90 % de las comparables) |
| P-5 | 3238 | `V00/3238-00_intern.08.xls!DR` → `V00/3238-00_intern.07.xls!DR` | 644 | 0 | 12 | 632 | 562: 88,9 % de las comparables, 87,3 % de la hoja | 55 filas (14–68), 112 con decimales | — | **Confirmada en parte** |

Ejemplos de celdas (hoja del caso = hoja comparada):

- 3186 `3186-00_intern.08.xls!DR_100%`: `I14` = `I14` = 42,548 (cota 102, c1); distinta: `K15` 42,55 frente a `K15` 42,552 (cota 102, c3)
- 3186 `3186-00_intern.09.xls!DR_100%`: `I14` = `I14` = 22,268 (cota 101, c1)
- 3195 `3195-00_intern.02.xls!DR_param`: `I14` = `I14` = 62,197 (cota 680, c1)
- 3205 `3205-00_intern.14_2.xls!DR`: `I16` = `I16` = 27,926 (cota 1, c1); distinta: `I44` 0,076 frente a `I44` 0,161 (cota 5, c1)
- 3205 `3205-00_intern.14.xls!DR`: `I16` = `I16` = 27,926 (cota 1, c1); distinta: `I123` 0,064 frente a `I123` -0,05 (cota 70, c1)
- 3205 `3205-00_intern.14.xls!DR (customer)`: `I15` = `I15` = 28,015 (cota 1, c1)
- 3205 `3205-00_intern.14_1.xls!DR`: `I16` = `I16` = 27,926 (cota 1, c1); distinta: `I44` 0,076 frente a `I44` 0,161 (cota 5, c1)
- 3205 `3205-00_intern.14_1.xls!DR (customer)`: `I15` = `I15` = 28,015 (cota 1, c1); distinta: `I28` 0,076 frente a `I28` 0,161 (cota 5, c1)
- 3205 `3205-00_intern.14_2.xls!DR`: `I16` = `I16` = 27,926 (cota 1, c1); distinta: `I44` 0,076 frente a `I44` 0,161 (cota 5, c1)
- 3205 `3205-00_intern.14_2.xls!DR (customer)`: `I15` = `I15` = 28,015 (cota 1, c1); distinta: `I28` 0,076 frente a `I28` 0,161 (cota 5, c1)
- 3238 `3238-00_intern05_customer.xls!DR`: `I14` = `I14` = 9,31 (cota 1, c1); distinta: `I69` 89,123 frente a `I69` 89,077 (cota 94, c1)
- 3238 `3238-00_intern.04.xls!DR_100%`: `I14` = `I14` = 9,31 (cota 1, c1); distinta: `I69` 88,793 frente a `I69` 89,077 (cota 94, c1)
- 3238 `3238-00_intern04_corr.xls!DR_100%`: `I14` = `I14` = 9,31 (cota 1, c1); distinta: `I69` 88,793 frente a `I69` 89,077 (cota 94, c1)
- 3168 `3168-00_intern.14.xls!DR`: `H14` = `H14` = 5,974 (cota 10, c1); distinta: `H30` 0,462 frente a `H30` 0,44 (cota 230, c1)
- 3051 `3051-00_intern.09.xls!DR(4CAV_CMM) (2)`: `H14` = `H14` = 0,241 (cota 680, c1); distinta: `K14` 0,242 frente a `K14` 0,263 (cota 680, c4)
- 3174 `3174-00_intern.26.xls!DR_100%`: `I15` = `I15` = 22,302 (cota 101, c1); distinta: `I14` 61,37 frente a `I14` 60,585 (cota 100, c1)
- 3186 `3186-00_intern.16.xls!DR`: `I23` = `I23` = 55,932 (cota 105, c1); distinta: `I14` 22,52 frente a `I14` 22,268 (cota 101, c1)
- 3205 `3205-00_intern.06.xls!DR_100%`: `I37` = `I23` = 2,27 (cota 3, c1); distinta: `I15` 28,015 frente a `I15` 28,059 (cota 1, c1)
- 3206 `3206-00_intern19.xls!DR`: `I15` = `I15` = 53,364 (cota 1, c1); distinta: `I23` 53,455 frente a `I23` 53,491 (cota 1, c1)
- 3212 `3212-00_intern.02.xls!DR(100%)`: `H25` = `H25` = 3,297 (cota 113, c13); distinta: `L25` 3,297 frente a `H26` 3,304 (cota 113, c13)
- 3214 `3214-00_int.05.xls!DR_L_Mig_1`: `H17` = `H47` = 2,3 (cota 44, c9); distinta: `H15` 136,9834 frente a `H15` 137,08 (cota 1, c9)
- 3218 `3218-00_intern.05_Set No.3.xls!DR_100% (customer)`: `I14` = `I14` = 22,215 (cota 101, c1); distinta: `I16` 5,69 frente a `I16` 5,7 (cota 108, c1)
- 3233 `3233-00_intern.04.xls!100% (CUSTOMER)`: `I15` = `I15` = 12,02 (cota B2, c1)
- 3237 `3237-00_intern.10.xls!DR`: `J15` = `J15` = 0,234 (cota 1, c1); distinta: `J70` 90,039 frente a `J70` 89,775 (cota 78, c1)
- 3238 `3238-00_intern.08.xls!DR`: `I14` = `I14` = 9,31 (cota 1, c1); distinta: `I69` 89,107 frente a `I69` 89,064 (cota 94, c1)

### Qué se concluye y qué no

- **P-2: las 14 hojas, todo el grupo, repiten los valores del muestreo que cita su cabecera.** Coinciden entre el
  93,7 % y el 100 % de las medidas comparables, y en 12 de las 14 hojas todas las medidas tienen pareja. Afecta a:
  - 3168 `intern.14`;
  - 3186 `intern.08` y `.09`;
  - 3195 `intern.02`;
  - las seis hojas de las tres copias del 3205 `intern.14`;
  - 3238 `intern05_customer` e `intern.04`, con su copia en `5- Retoques molde`.
- **P-5: 8 de las 11 hojas de la muestra tienen valores repetidos.**
  - **3 con al menos el 90 % de las medidas comparables iguales:**
    - 3233 `intern.04` frente a `intern.03`: 3.305 de 3.305, sin contar 2.358 celdas excluidas;
    - 3237 `intern.10` frente a `intern.09`: 568 de 624;
    - 3205 `intern.06` frente a `intern.02`: 728 medidas iguales, el 92,9 % de las comparables y el 76,5 % de la
      hoja, porque 168 de sus 952 medidas no tienen pareja.
  - **5 con un bloque de filas completas iguales:**
    - 3174 `intern.26` frente a `intern.08`: 48 filas;
    - 3186 `intern.16` frente a `intern.13`: 36 filas, de la 146 a la 181. El bloque más largo, de 52 filas, son
      valores con dos decimales o menos y no cuenta;
    - 3206 `intern19` frente a `intern.18`: 30 filas;
    - 3218 `intern.05_Set No.3` frente a `intern.15`: 41 filas;
    - 3238 `intern.08` frente a `intern.07`: 55 filas.
  - Las otras 24 hojas de P-5 no se han contrastado: este resultado no las cierra.
- **Pendientes por falta de evidencia:**
  - **3212 `intern.02!DR(100%)` frente a `intern.01`:** 498 de 807 medidas comparables iguales, pero 743 de las
    1.550 medidas de la hoja no tienen pareja. El único bloque de 5 filas completas (74–78) tiene 7 valores con tres
    decimales, menos de los 10 exigidos.
  - **3051 `intern.09!DR(4CAV_CMM) (2)`:** 199 de 340 comparables iguales, pero ninguna fila completa igual. Es la
    hoja copiada de I-203; frente a `intern.01` no se puede separar la repetición de la casualidad con estos criterios.
  - **3214 `int.05!DR_L_Mig_1`:** solo 8 medidas comparables.
- **Ninguna sospecha descartada.**
- **Lo que no dice:** son valores idénticos en dos informes. No dice si se volvió a medir, ni qué informe es el
  original, ni por qué. El caso del 3218 es llamativo: un libro llamado `intern.05_Set No.3` cita en su cabecera el
  muestreo 15 y comparte con `intern.15` un bloque de 41 filas. Se registra tal cual, sin interpretarlo.

Las repeticiones confirmadas se añaden a [I-001](incongruencias.md) como evidencia de valores repetidos. Los
resultados completos (recuentos, bloques, ejemplos y lecturas) están en `conocimiento/datos/contraste-m3/resultados.json`,
fuera de Git.

### Correcciones durante el contraste

1. **Primera ejecución, 3233.** Excel recalculó al abrir las 2.354 celdas con `RAND()` y lo leído no era lo guardado.
   Se repitió en cálculo manual y con las celdas excluidas.
2. **Revisión del 11/11/2026.** El primer cálculo tenía dos fallos:
   - contaba los valores con decimales en toda la hoja, no dentro del bloque, y solo miraba el bloque más largo;
   - daba por iguales filas en las que solo se comparaba una parte.

   Con los dos corregidos (`evaluar()`, con pruebas en `test_revision.py`), el 3212 pasa de «confirmada en parte»
   a pendiente, y el 3186 se justifica con otro bloque. También se separan en la tabla las medidas excluidas, sin
   pareja y comparadas. P-2 no cambia.
