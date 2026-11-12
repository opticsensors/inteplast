# Planos: qué es cada PDF y qué revisión citan los informes (12/11/2026)

Responde a tres preguntas: **qué es un PDF de plano** (qué dibujo, qué revisión, de qué pieza), **por qué una
pieza tiene varios** y **qué revisión citan sus informes**. Los globos, los `.icp` y los lectores están en
[planos-globos.md](planos-globos.md); la identidad de cada pieza, en [identidad-piezas.md](identidad-piezas.md).

- **Fuente:** [`planos.jsonl`](planos.jsonl), un registro por PDF físico, escrito a mano con la evidencia de cada
  dato (página, cajetín o tabla de revisiones). `verificacion` dice cómo se comprobó el registro: `visto`,
  `capa de texto`, `inferido` (misma carpeta y mismo `.icp` que otro ya visto), `documentado` (sale de otra ficha)
  o `copia idéntica de N`. Cuando un campo tiene otro origen, `procedencia` lo dice campo a campo: por ejemplo, la
  revisión del 6494730 sale del **nombre del fichero** y su fecha, de la capa de texto; la fecha del cambio de una
  copia con globos puede estar **inferida de** otro PDF de la misma serie, con su id.
- **Qué separa:** el PDF del dibujo que contiene (un PDF puede llevar varios planos, como en el 3288); la carpeta
  donde está el PDF (`carpeta_pieza`) de la pieza a la que pertenece el dibujo (`pieza`), que pueden no coincidir
  (3186, 3218); y la fecha del cambio (tabla de revisiones), la de emisión (firmas, *Released on* o sello de
  impresión; en Aisin, solo el mes de las firmas, `AAAA-MM`) y la del nombre del fichero.
- **Tablas generadas:** las de los bloques marcados salen de
  [`planos_catalogo.py`](herramientas/planos_catalogo.py), que lee la biblioteca **sin modificarla**. Antes de
  escribir comprueba el catálogo: campos, páginas, fechas de calendario, fuentes de `procedencia`, que las copias
  idénticas describan el mismo dibujo, rutas y SHA-256, y que no falte ningún PDF de plano. Pruebas en
  `test_planos_catalogo.py`. No editar las tablas a mano. `--detalle PIEZA` da las cabeceras hoja a hoja, con la
  fecha **tal como está escrita** y su normalización (`AAAA-MM-DD` solo si el literal es una fecha).
- **El visor no usa todavía el catálogo.** Su columna «Planos» (Piezas → Números) cuenta los PDF distintos, no
  los dibujos. Qué debe contar está sin decidir.
- Revisado el 12/11/2026 con un revisor externo. Las observaciones de abajo son datos con su alcance, **no reglas
  automáticas** para el visor.

## Resumen

**62 PDF de planos en 21 piezas**: 56 distintos y 6 copias idénticas byte a byte (`documento.duplicado_de`). Una
pieza tiene varios PDF por cinco motivos, que se combinan:

1. **Copias de trabajo de INTEPLAST del mismo dibujo:** el plano limpio y el plano con globos de infra-CONVERT
   (los pone INTEPLAST en el PC de la CMM, [planos-globos.md](planos-globos.md#cómo-están-hechos-los-pdf-con-globos)),
   versiones de baja resolución (`low resolution`, `lr`) y copias idénticas en otra carpeta.
2. **Revisiones sucesivas del cliente:** Aisin (`−`, `A`, `B`), Bosch (índices) y B. Braun (niveles).
3. **Planos de estudio de Aisin, anteriores al número definitivo** (DWG. TYPE `J`): `213137-01030-10` (3205),
   `213137-01028-10` (3206) y `885253-01125-10` (3202).
4. **Conjunto y componentes:** el 3288 tiene los planos del conjunto `BSG-296-00`, de la base `-01` y de la tapa
   `-02`; un mismo PDF trae los tres.
5. **Plano de otra pieza:** en las carpetas del 3186 y del 3218 está el plano `6494730` del 3174 ([I-301](incongruencias.md)).

La revisión que escribe la cabecera de un informe **no basta para saber qué revisión se aplicó**: hay cabeceras
que no cambian cuando cambia el plano y hojas que ya usan las cotas de una revisión posterior a la que citan
([I-009](incongruencias.md)). Hay que leerla hoja a hoja y contrastarla con los nominales y tolerancias.

## Cómo se lee la revisión en cada cliente

| Cliente | Dónde está la revisión | Cuidado con |
|---|---|---|
| **Aisin** (3202, 3205, 3206) | Letra del nº de pieza (`213137-10300-B`; `−` sin letra) y tabla REVISION RECORD (ECI No. y fecha `'AA.MM.DD`) | **DWG. TYPE** es el tipo de plano, no la revisión: `J` estudio (sello *FOR OFF TOOL PREPARATION*), `JT` prototipo preliminar, `G` producción. Una misma letra puede tener varias filas (la B del 3205: ECI de 10/2023 y de 10/2024). En las carpetas, `_231011`/`_241028` es la fecha del ECI y `vG` el tipo |
| **Bosch** | Casilla *Ind.* y tabla *Change/Aend.* (nº de cambio `3E…`, fecha `AAAAMMDD`); casilla *DP/TD* | Los informes escriben `índice/nº de cambio` (`01/0196E0000J04`). Las cifras en cápsula junto a una cota son la **clase de control** que indica el plano, no el número de la cota. Su significado lo da la leyenda de cada plano: en el 3233, 4 = SPC con Cpk ≥ 1,33 y 5 = muestreo (D_01), 1 = característica MOC (D_02); en el 3056, 4 = SPC con Cpk ≥ 1,67; en el 3167, 6 = Cpk ≥ 1,33. La capa de texto puede leer «≥» como «>»: copiar el signo del plano impreso |
| **B. Braun** (3288) | *NIVEL/REV.* del cajetín con su fecha | El conjunto y cada componente tienen su propio nivel |
| Otros | 6494730: revisión del nombre y *Released on*; Clunas `C11692`: *Rev.*; INTEPLAST `732260000`: *DRW REV*; Toyoda Gosei: sin revisión identificada | — |

## Resumen por pieza

<!-- planos-resumen:inicio -->
| Pieza | PDF | Copias idénticas | Con globos | Dibujos distintos¹ | Números de plano | Planos de otra pieza o sin asignar |
|---|---:|---:|---:|---:|---|---:|
| 2820 | 1 | 0 | 0 | 1 | `0140S00050` |  |
| 3051 | 1 | 0 | 0 | 1 | `0140S00275` |  |
| 3056 | 1 | 0 | 0 | 1 | `0131S00135` |  |
| 3167 | 2 | 0 | 1 | 2 | `0130S00338` |  |
| 3168 | 1 | 0 | 0 | 1 | `0130S00337` |  |
| 3174 | 1 | 0 | 0 | 1 | `6494730` |  |
| 3186 | 1 | 0 | 0 | 1 | `6494730` | 1 |
| 3195 | 2 | 0 | 1 | 2 | `0130S0002K`, `0130S1B006` |  |
| 3197 | 1 | 0 | 0 | 1 | `0140S00363` |  |
| 3202 | 10 | 3 | 7 | 4 | `885253-01125-10`, `885253-11250` |  |
| 3205 | 9 | 0 | 6 | 5 | `213137-01030-10`, `213137-10300` |  |
| 3206 | 9 | 0 | 5 | 5 | `213137-01028-10`, `213137-10280` |  |
| 3212 | 1 | 0 | 1 | 1 | `0140S00237` |  |
| 3214 | 1 | 0 | 0 | 1 | `C11692` |  |
| 3218 | 1 | 1 | 0 | 1 | `6494730` | 1 |
| 3226 | 1 | 0 | 0 | 1 | `732260000` |  |
| 3233 | 2 | 0 | 0 | 2 | `0196S0000K` |  |
| 3237 | 2 | 0 | 1 | 2 | `3130589019` |  |
| 3238 | 2 | 0 | 1 | 2 | `313058901F` |  |
| 3288 | 12 | 2 | 7 | 4 | `BSG-296-00`, `BSG-296-01`, `BSG-296-02` |  |
| 3309 | 1 | 0 | 0 | 1 | `77217-02200-000A` |  |

¹ Número, componente, revisión y fecha del último cambio distintos. Es un recuento informativo: qué debe contar la columna «Planos» del visor está sin decidir.
<!-- planos-resumen:fin -->

## Inventario de los PDF

Ordenado por pieza y fecha del cambio. «Id» es `documento.id` de la biblioteca; `= N`, copia idéntica de N.

<!-- planos-inventario:inicio -->
| Pieza | Id | PDF | Plano · revisión | Tipo | Último cambio | Globos | Comprobado |
|---|---:|---|---|---|---|---|---|
| 2820 | 1 | `1-2D y 3D Pieza/20160817_DRW_3130516933_0140S00050-DRW-000-02-1-EN_DE.pdf` | `0140S00050` 02 | DP/TD 000 | 2016-07-13 | no | visto |
| 3051 | 4 | `1-2D y 3D Pieza/20211205_0140S00275-DRW_pendent acceptació.pdf` | `0140S00275` 03 | DP/TD 000 | 2021-03-08 | no | capa de texto |
| 3056 | 3134 | `1- 2D y 3D pieza/20240417_DRW_0131S00135_D_04.pdf` | `0131S00135` 04 | DP/TD 000 | 2024-03-06 | no | capa de texto |
| 3167 | 3968 | `6- Método de medición/Drawing baloneed.pdf` | `0130S00338` 02 | DP/TD 000 | 2021-03-22 | sí | visto |
| 3167 | 3294 | `1- 2D y 3D pieza/20260727_0130S00338_DRAFT_V07.pdf` | `0130S00338` 07 | DP/TD 000 | 2026-07-15 | no | capa de texto |
| 3168 | 4208 | `1- 2D y 3D pieza/20260727_0130S00337_DRAFT_V02.pdf` | `0130S00337` 02 | DP/TD 000 | 2026-07-16 | no | capa de texto |
| 3174 | 582 | `1- 2D y 3D pieza/20250219_6494730_004.pdf` | `6494730` 004 | — | — | no | capa de texto; revisión: nombre del fichero |
| 3186 | 873 | `1- 2D y 3D pieza/20230123_6494730_002.pdf` | `6494730` 002 — pieza: 3174 | — | — | no | capa de texto; revisión: nombre del fichero |
| 3195 | 1537 | `6- Método de medición/Ballooned DRW/1 - 0130S1B006-DRW-000-07-1-EN DE_ballown.pdf` | `0130S1B006` 07 | DP/TD 000 | 2021-04-14 | sí | visto |
| 3195 | 1381 | `1- 2D y 3D pieza/20241121_3134341864_0130S0002K_D_01.pdf` | `0130S0002K` 01 | DP/TD 000 | 2024-09-16 | no | capa de texto |
| 3197 | 126 | `1-2D y 3D Pieza/20240222_0140S00363 D 02.pdf` | `0140S00363` 02 | DP/TD 000 | 2023-04-24 | no | capa de texto |
| 3202 | 4080 | `6- Método de medición/Ballooned DRW/885253-01125-10/3202_DRW_ballooned.pdf` | `885253-01125-10` − | J | 2023-01-13 | sí | visto |
| 3202 | 4079 | `6- Método de medición/Ballooned DRW/3202_balloned.pdf` | `885253-11250` − | JT | 2023-03-20 | sí | inferido |
| 3202 | 4086 | `6- Método de medición/Ballooned DRW/885253-11250/3202.pdf` | `885253-11250` − | JT | 2023-03-20 | no | visto |
| 3202 | 4088 | `6- Método de medición/Ballooned DRW/885253-11250/3202_balloned low resolution.pdf` | `885253-11250` − | JT | 2023-03-20 | sí | inferido |
| 3202 | 4089 = 4079 | `6- Método de medición/Ballooned DRW/885253-11250/3202_balloned.pdf` | `885253-11250` − | JT | 2023-03-20 | sí | copia idéntica de 4079 |
| 3202 | 4077 | `6- Método de medición/Ballooned DRW/20231129_885253-11250_insulator_motor_v1.pdf` | `885253-11250` − | G | 2023-09-29 | no | visto |
| 3202 | 4090 = 4077 | `6- Método de medición/Ballooned DRW/885253-11250-G/20231129_885253-11250_insulator_motor_v1.pdf` | `885253-11250` − | G | 2023-09-29 | no | copia idéntica de 4077 |
| 3202 | 4091 | `6- Método de medición/Ballooned DRW/885253-11250-G/20231129_885253-11250_insulator_motor_v1_ Ballooned.pdf` | `885253-11250` − | G | 2023-09-29 | sí | visto; emisión: inferido de 4077; tipo: inferido de 4077 |
| 3202 | 3993 | `1- 2D y 3D pieza/20241121_885253-11250-A_INSULAT balooned.pdf` | `885253-11250` A | G | 2024-10-28 | sí | visto |
| 3202 | 4078 = 3993 | `6- Método de medición/Ballooned DRW/20241121_885253-11250-A_insulator_motor_balooned.pdf` | `885253-11250` A | G | 2024-10-28 | sí | copia idéntica de 3993 |
| 3205 | 1931 | `6- Método de medición/DRW ballooned/213137-01030-10/3205_DRW ballooned.pdf` | `213137-01030-10` − | J | 2023-01-17 | sí | visto |
| 3205 | 1939 | `6- Método de medición/DRW ballooned/213137-10300-A/3205-A.pdf` | `213137-10300` A | JT | 2023-03-10 | no | visto; cambio: inferido de 1941; fecha del cambio: inferido de 1941 |
| 3205 | 1941 | `6- Método de medición/DRW ballooned/213137-10300-A/3205-A_balloned.pdf` | `213137-10300` A | JT | 2023-03-10 | sí | visto; emisión: inferido de 1939; tipo: inferido de 1939 |
| 3205 | 1942 | `6- Método de medición/DRW ballooned/213137-10300-A/3205-A_balloned_1.pdf` | `213137-10300` A | JT | 2023-03-10 | sí | visto; cambio: inferido de 1941; fecha del cambio: inferido de 1941 |
| 3205 | 1935 | `6- Método de medición/DRW ballooned/213137-10300/3205.pdf` | `213137-10300` − | JT | 2023-03-10 | no | visto |
| 3205 | 1937 | `6- Método de medición/DRW ballooned/213137-10300/3205_balloned.pdf` | `213137-10300` − | JT | 2023-03-10 | sí | inferido |
| 3205 | 1631 | `1- 2D y 3D pieza/20231129_213137-10300-B.pdf` | `213137-10300` B | G | 2023-10-11 | no | visto |
| 3205 | 1943 | `6- Método de medición/DRW ballooned/213137-10300-B_231011/20231129_213137-10300-B_shroud_vG_Ballooned.pdf` | `213137-10300` B | G | 2023-10-11 | sí | visto; cambio: inferido de 1631; fecha del cambio: inferido de 1631 |
| 3205 | 1949 | `6- Método de medición/DRW ballooned/213137-10300-B_241028/20241121_213137-10300-B_balloned.pdf` | `213137-10300` B | G | 2024-10-28 | sí | visto |
| 3206 | 2191 | `6- Método de medición/DRW ballooned/213137-01028-10/3206_DRW ballooned.pdf` | `213137-01028-10` − | J | 2023-01-17 | sí | visto; emisión: inferido de 2184 |
| 3206 | 2184 | `6- Método de medición/Drw_Marking_DR_intern02.pdf` | `213137-01028-10` − | J | 2023-01-17 | marcas | visto; cambio: inferido de 2191; fecha del cambio: inferido de 2191 |
| 3206 | 2199 | `6- Método de medición/DRW ballooned/213137-10280-A/3206-A.pdf` | `213137-10280` A | JT | 2023-03-10 | no | visto; cambio: inferido de 2003; fecha del cambio: inferido de 2003 |
| 3206 | 2201 | `6- Método de medición/DRW ballooned/213137-10280-A/3206-A_balloned lr.pdf` | `213137-10280` A | JT | 2023-03-10 | sí | visto; cambio: inferido de 2003; fecha del cambio: inferido de 2003; emisión: inferido de 2199 |
| 3206 | 2195 | `6- Método de medición/DRW ballooned/213137-10280/3206.pdf` | `213137-10280` − | JT | 2023-03-10 | no | visto |
| 3206 | 2197 | `6- Método de medición/DRW ballooned/213137-10280/3206_balloned.pdf` | `213137-10280` − | JT | 2023-03-10 | sí | inferido |
| 3206 | 2003 | `1- 2D y 3D pieza/3206.pdf` | `213137-10280` B | G | 2023-10-11 | no | visto |
| 3206 | 2202 | `6- Método de medición/DRW ballooned/213137-10280-B_231011/20231129_213137-10280-B_shroud_vG_Ballooned.pdf` | `213137-10280` B | G | 2023-10-11 | sí | visto; cambio: inferido de 2003; fecha del cambio: inferido de 2003 |
| 3206 | 2208 | `6- Método de medición/DRW ballooned/213137-10280-B_241028/20241121_213137-10280-B_balloned.pdf` | `213137-10280` B | G | 2024-10-28 | sí | visto |
| 3212 | 329 | `1-2D y 3D Pieza/20250523_DRW 0140S00237_07.pdf` | `0140S00237` 07 | — | 2022-06-21 | sí | documentado |
| 3214 | 2243 | `1- 2D y 3D pieza/R-2718, R-2971_C11692_rev.B.pdf` | `C11692` B | — | — | no | visto |
| 3218 | 1031 = 582 | `1- 2D y 3D pieza/20250219_6494730_004.pdf` | `6494730` 004 — pieza: 3174 | — | — | no | copia idéntica de 582; revisión: nombre del fichero |
| 3226 | 1574 | `1- 2D y 3D pieza/20241028_DW-UMED-2-2_REV01.PDF` | `732260000` 01 | — | — | no | capa de texto |
| 3233 | 2502 | `6- Método de medición/Support MM/20230728_DRW_0196S0000K_D_01.pdf` | `0196S0000K` 01 | DP/TD 003 | 2023-07-04 | no | capa de texto |
| 3233 | 2379 | `1- 2D y 3D pieza/20250316_DRW_0196S0000K_D_02.pdf` | `0196S0000K` 02 | DP/TD 000 | 2025-03-11 | no | capa de texto |
| 3237 | 2835 | `6- Método de medición/OLD/1 - 3130589019_D_03_balloned.pdf` | `3130589019` 03 | DP/TD 000 | 2024-01-10 | sí | visto |
| 3237 | 2507 | `1- 2D y 3D pieza/20260914_3130589019 2D 05.pdf` | `3130589019` 05 | DP/TD 000 | 2026-04-17 | no | capa de texto |
| 3238 | 3015 | `6- Método de medición/OLD/1 - 313058901F_D_03_balloned.pdf` | `313058901F` 03 | DP/TD 000 | 2024-01-10 | sí | visto |
| 3238 | 2846 | `1- 2D y 3D pieza/20260914_313058901F 2D 05.pdf` | `313058901F` 05 | DP/TD 000 | 2026-04-17 | no | capa de texto |
| 3288 | 3029 | `1- 2D y 3D pieza/Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` | `BSG-296-01` 1 (base, p. 1); `BSG-296-00` 1 (conjunto, p. 2); `BSG-296-02` 1 (tapa, p. 3) | — | 2025-02-19; 2025-05-21 | no | visto; emisión: capa de texto |
| 3288 | 3113 | `6- Método de medición/balloned/REV.01/BSG-296-00/2. 20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | `BSG-296-00` 1 (conjunto) | — | 2025-02-19 | sí | inferido |
| 3288 | 3114 | `6- Método de medición/balloned/REV.01/BSG-296-00/20250714_BSG-296-00 SOP RCP 3.1 balloned.pdf` | `BSG-296-00` 1 (conjunto) | — | 2025-02-19 | sí | inferido |
| 3288 | 3116 | `6- Método de medición/balloned/REV.01/BSG-296-00/20250714_BSG-296-00 SOP RCP 3.1.pdf` | `BSG-296-00` 1 (conjunto) | — | 2025-02-19 | no | visto; emisión: capa de texto |
| 3288 | 3120 = 3029 | `6- Método de medición/balloned/REV.01/BSG-296-01/Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` | `BSG-296-01` 1 (base, p. 1); `BSG-296-00` 1 (conjunto, p. 2); `BSG-296-02` 1 (tapa, p. 3) | — | 2025-02-19; 2025-05-21 | no | copia idéntica de 3029; emisión: capa de texto |
| 3288 | 3049 | `5- Retoques molde/20260429_1 loop of correction/BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | `BSG-296-01` 1 (base) | — | 2025-05-21 | sí | visto |
| 3288 | 3050 | `5- Retoques molde/20260429_1 loop of correction/BSG-296-2 SOP RCP 3.1 balloned.pdf` | `BSG-296-02` 1 (tapa) | — | 2025-05-21 | sí | visto |
| 3288 | 3118 = 3049 | `6- Método de medición/balloned/REV.01/BSG-296-01/BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf` | `BSG-296-01` 1 (base) | — | 2025-05-21 | sí | copia idéntica de 3049 |
| 3288 | 3122 | `6- Método de medición/balloned/REV.01/BSG-296-02/BSG-296-2 SOP RCP 3.1 balloned.pdf` | `BSG-296-02` 1 (tapa) | — | 2025-05-21 | sí | inferido |
| 3288 | 3124 | `6- Método de medición/balloned/REV.01/BSG-296-02/BSG-296-2 SOP RCP 3.1.pdf` | `BSG-296-02` 1 (tapa) | — | 2025-05-21 | no | visto |
| 3288 | 3126 | `6- Método de medición/balloned/REV.02/BSG-296-00 SOP RCP 3.1 .pdf` | `BSG-296-00` 2 (conjunto) | — | 2026-08-26 | no | visto; emisión: capa de texto |
| 3288 | 3127 | `6- Método de medición/balloned/REV.02/BSG-296-00 SOP RCP 3.1 balonned.pdf` | `BSG-296-00` 2 (conjunto) | — | 2026-08-26 | sí | inferido |
| 3309 | 1588 | `1- 2D y 3D pieza/dwg_ab_77217-02200-000A_2864368.pdf` | `77217-02200-000A` ? | — | — | no | visto |
<!-- planos-inventario:fin -->

## Historia de los planos por pieza

### 3205 y 3206 — Aisin, *shroud* 150 W y 240 W

Las carpetas de `6- Método de medición/DRW ballooned/` siguen la historia del plano:

| Fecha | Qué es | 3205 | 3206 | DWG. TYPE |
|---|---|---|---|---|
| 17/01/2023 | Plano de estudio, *NEW ADOPTION (PROTOTYPE)*, sin ECI | `213137-01030-10` | `213137-01028-10` | J |
| 10/03/2023 | Prototipo preliminar: `−` y `A` llevan la misma fila (las firmas del A son de abril de 2023) | ECI 211G23-015 | ECI 211G23-016 | JT |
| 11/10/2023 | `B`: producción, se añade el plan de entrada (*GATE PLAN NEWLY ADDED*) | ECI 211G23-066 | ECI 211G23-067 | G |
| 28/10/2024 | `B` sin cambiar de letra: cambio de nombre del proveedor y *G103 DISUSE* | ECI 211G24-081 | ECI 211G24-081 | G |

- El estudio y el definitivo son la misma pieza: en la reunión con Aisin del 04/04/2023
  (`3205/6- Método de medición/Inteplast 打ち合わせ宿題事項(西尾、設計合体).pptx`, diapositiva 2), preguntas sobre
  `213137-01028`/`-01030` se contestan con `213137-10280`/`-10300` (punto 4).
- `1- 2D y 3D pieza` trae la `B` de 10/2023 sin globos (3205 `20231129_213137-10300-B.pdf`, 3206 `3206.pdf`).
- `Drw_Marking_DR_intern02.pdf` del 3206 es el plano de estudio con marcas de color, sin números.
- **Cabeceras de los informes.** 3205: `213137-10300` `-` en 123 hojas de 44 libros (09/2023 → 09/2026); `B`
  solo en dos hojas de la copia `Customer` de `intern.17` (23/04/2024 y 06/02/2025); la otra copia de
  `intern.17` dice `-` (09/06/2025), y `intern.14_2` combina `213137-10300-B` con `-` (4 hojas). 3206: `-A`
  hasta 03/2024 y `-B` desde 04/2024.

### 3202 — Aisin, *insulator* 240 W

| Fecha | Plano | DWG. TYPE | Cambio |
|---|---|---|---|
| 13/01/2023 | `885253-01125-10` (estudio, `885253-01125-10/`) | J | ECI 213J22-020, *NEW ADOPTION (PROTOTYPE)* |
| 20/03/2023 | `885253-11250` `−` (`885253-11250/`) | JT | ECI 211G23-016, prototipo preliminar |
| 29/09/2023 | `885253-11250` `−` (`885253-11250-G/`) | G | ECI 211G23-067, *NEW ADOPTION (PRODUCTION), CORRECTION* |
| 28/10/2024 | `885253-11250-A` (`1- 2D y 3D pieza/`) | G | ECI 211G24-081, *DRAWING RENEWED, TOLERANCE CHANGE, ADDED NOTE* |

- La `G` de la carpeta `885253-11250-G` es el tipo de plano, no una revisión.
- **La A cambia tolerancias.** Comprobadas dos cotas: globo 1, Ø38,65 ±0,10 → +0,45/−0,10; globo 2, Ø56,1 ±0,15
  → +0,15/−0,35. El resto de cotas de la A no se ha comparado.
- **Informes:** la cabecera dice `-` en todos (29 hojas, 06/2023 → 05/2025; `0` en el PPAP de 01/2024).
  `intern.05` (13/09/2024, antes de la A) usa ±0,10 y ±0,15; `intern.07` (23/05/2025), hoja
  `3pcs countermeasurement`, filas 15 y 16, usa ya las de la A con la cabecera en `-` (R6). **La cabecera sigue
  desfasada, pero estas dos cotas ya incorporan las tolerancias de A.** No consta desde qué informe o lote se
  aplicó la A ([I-604](incongruencias.md)).

### 3195 — Bosch, *brush holder*

- `0130S1B006` índice 07 (14/04/2021, 3E1004281060), con globos, en `6- Método de medición/Ballooned DRW/`.
- `0130S0002K` índice 01 (16/09/2024, 3E1008667560), en `1- 2D y 3D pieza/` (el nombre lleva el nº de pieza
  3134341864). **Es la misma pieza con otro número, con al menos una tolerancia distinta:** la cota 2360 (5, 4x,
  sección J) es `+0,22/+0,13` (5,13–5,22) en el 07 y `+0,22/−0,13` (4,87–5,22) en el `0130S0002K`. Solo se ha
  comparado esa zona.
- **Informes:** todos los que tienen la 2360 usan `+0,13`, también `int_20` (28/04/2026). Sus cabeceras citan
  `0130S1B006` con `09/3E1008859560` (35 hojas de 21 libros), un índice sin PDF en Exemples; `Int_03`
  (10/04/2024) e `int_21` (01/10/2026) dicen `07`, y `REPORT HUMIDITY - 3195-00_int_04.xls`, `07/3E1008859560`
  ([I-313](incongruencias.md)).

### 3233 — Bosch

- `20230728_DRW_0196S0000K_D_01.pdf` (`6- Método de medición/Support MM/`): índice 01 de **DP/TD 003**
  (04/07/2023, `0196E0000J04`). Es el `01/0196E0000J04` que citan las cabeceras.
- `20250316_DRW_0196S0000K_D_02.pdf` (`1- 2D y 3D pieza/`): índice 02 de **DP/TD 000** (11/03/2025,
  3E1014105160). Su tabla lista además un índice 01 de DP/TD 000 (21/05/2024, 3E1012588060) cuyo PDF no está.
- **Clase de control indicada en el plano.** Hay 11 cápsulas junto a cotas. En el D_01, 10 llevan 5 (muestreo)
  y 1 lleva 4 (SPC): la 10,39 ±0,1 aparece dos veces, una con 5 y otra con 4. En el D_02, las 11 llevan 1 (MOC).
  Es la clasificación que indica el plano; no dice cómo se ejecutó el control en fábrica.
- **Nominales que cambian** (capa de texto, misma posición en las dos hojas; lista no exhaustiva): 0,67 → 0,71
  (2x), 1,508 → 1,51 (2x), 3,35 → 3,41, 1,39 → 1,37, 1,43 → 1,42 y 11,96 → 11,97; el D_02 añade 0,6 ±0,05 y
  cambia un ángulo (27 +5/−2 donde el D_01 tiene 30 y 2).
- **Informes.** La cabecera dice `01/0196E0000J04` en 72 hojas de 23 libros (07/2024 → 08/2026) y
  `02/3E1014105160` solo en la hoja `100% BOSCH PORTAL` de la copia `Customer` de `intern.16` (08/09/2026). Pero
  **desde `intern.02` (23/08/2024) hay hojas con los nominales nuevos** (3,41; 0,71; 11,97; 1,37; 1,42), y
  **desde `intern.09` (27/02/2025) ya no queda ninguno de los antiguos**; los `PPAP_3233_Inf_01/02` del cliente
  solo traen los nuevos. Esos nominales pueden venir del índice 01 de DP/TD 000 o del 02: sin el PDF del 01 no se
  distingue ([I-009](incongruencias.md)).

### 3237 y 3238 — Bosch

- Con globos, en `6- Método de medición/OLD/`: índice 03 (10/01/2024, 3E1011383160). Su tabla: 03, 02
  (26/10/2023) y 01.
- En `1- 2D y 3D pieza/`, `2D 05`: índice 05 (17/04/2026, 3E1018058160). Su tabla lista 05, 04 (03/12/2024,
  3E1011980460), 03 y 01: no lista el 02, y la fila 05 no tiene *Checked* ni *Releas.*
- **Informes:** `03` hasta 10/2024, `04` desde el 29/11/2024 y `05` desde 07/2026 (3238) u 08/2026 (3237).
  **No hay PDF del índice 04**, el que citan los informes de 11/2024 a 07–08/2026 ([I-801](incongruencias.md)).

### 3167 y 3168 — Bosch

- 3167 `0130S00338`: con globos, índice 02 (22/03/2021); en `1- 2D y 3D pieza/`, `DRAFT_V07`, índice 07
  (15/07/2026), con una fila 06 (10/06/2025). Las cabeceras dicen `0130S000338` (sic) y no traen revisión.
- 3168 `0130S00337`: `DRAFT_V02`, índice 02 (16/07/2026). Sus cabeceras citan `01` hasta 04/2026, anterior al 02.
- Los dos borradores llevan el mismo nº de cambio (3E1019023760) y su última fila no tiene *Checked* ni *Releas.*

### 3288 — B. Braun

| Plano | Nivel 0 | Nivel 1 | Nivel 2 |
|---|---|---|---|
| `BSG-296-00` conjunto | 11/12/2018 | 19/02/2025: tolerancias de faltado y rebabas | 26/08/2026: códigos y nota del símbolo RIC (ECM 204145) |
| `BSG-296-01` base | 11/12/2018 | 21/05/2025: tolerancias de faltado y rebabas | — |
| `BSG-296-02` tapa | 11/12/2018 | 21/05/2025: ídem | — |

- `1- 2D y 3D pieza/Cj20240714_BSG-296-01-N0 BASE SOP RCP 3.1.pdf` trae los tres planos en nivel 1: base (p1),
  conjunto (p2) y tapa (p3). El nombre dice 20240714; la capa de texto, 2025-07-14.
- `6- Método de medición/balloned/REV.01` tiene el conjunto en nivel 1 y `REV.02`, en nivel 2. El globo 80 del
  conjunto (la DIM. 80 del método) está dibujado en REV.01 y en el `.icp` de REV.02.
- **Informes:** `DR(base)` y `DR(tapa)` dicen `BSG-296-00` (I6) y nivel `1` (AB6) en `intern.01`–`.04`
  (30/04–23/09/2026), y la fila 14 (D14) identifica `BSG-296-01 rev1 21/05/2025` y `BSG-296-02 rev1 21/05/2025`.
  El nivel 1 coincide con base y tapa; el conjunto está en nivel 2 desde el 26/08/2026, así que en `intern.04`
  la cabecera no sigue al conjunto. Los informes del molde anterior 3247 (16/04 y 20/05/2025) dicen nivel `0`:
  posterior al nivel 1 del conjunto (19/02/2025) y anterior al de base y tapa (21/05/2025).

### 3174, 3186 y 3218 — plano `6494730`

- 3174: `6494730` rev 004 (*Released on* 2025-02-19); el 3218 tiene una copia idéntica. 3186: rev 002 (2023-01-20).
- El catálogo asigna el dibujo al 3174 (su nº de pieza es 649473000A). La pieza 3186 tiene STEP `6541691` y nº
  654169100A; la 3218, STEP `6546952` y nº 654695200B. Aun así, sus cabeceras citan `6494730` (o `64947300`).
  Si ese plano **también** les corresponde está **pendiente** ([I-301](incongruencias.md),
  [A19](../docs/preguntas-abiertas.md#a19-planos)).
- La revisión (004, 002) sale del nombre del fichero; la fecha, de *Released on* en la capa de texto.

### Piezas con un solo PDF

| Pieza | Plano | Cabeceras de los informes |
|---|---|---|
| 2820 | `0140S00050` índice 02 (13/07/2016) | Sin informes |
| 3051 | `0140S00275` índice 03 (08/03/2021); nombre «pendent acceptació» (I-205) | `01` (29 hojas, 11/2019 → 02/2023) |
| 3056 | `0131S00135` índice 04 (06/03/2024) | `01`, `02`; `03/3E1004555360` (10/04/2024) y `04` (05/2024 → 02/2025) |
| 3197 | `0140S00363` índice 02 (24/04/2023) | El nº de cambio del 02, `3E1009447060`, desde 04/2023 |
| 3212 | `0140S00237` rev 07 (21/06/2022), escaneo | `06/3E1005491360` ([trampas](trampas.md)) |
| 3214 | Clunas `C11692` Rev. B (A: CR-159; B: R-2971 añadida, CR-162) | `11206` `G` (10/2023 → 10/2025) y `C 11692` `A` (11/2025 → 06/2026) |
| 3226 | INTEPLAST `732260000`, DRW REV 01 (28/10/2024) | Sin cabecera de plano |
| 3309 | Toyoda Gosei `77217-02200-000A` | `GF991-53540`, sin revisión |

## Revisiones que citan las cabeceras

Una fila por pieza, plano y revisión **tal como están escritos**. Cada copia de un libro cuenta como libro
distinto. La celda es la de la primera hoja (`plano / revisión`). El detalle hoja a hoja, con ruta, celdas y
fecha: `planos_catalogo.py --detalle PIEZA`. Las fechas que no son fechas (`xx`, `1899-12-31`, texto; I-304) no
entran en el rango.

<!-- planos-cabeceras:inicio -->
| Pieza | Plano (literal) | Revisión (literal) | Libros | Hojas | Fechas de cabecera | Primera hoja (archivo · hoja · celdas) |
|---|---|---|---:|---:|---|---|
| 3051 | `0140S00275` | `01` | 15 | 29 | 2019-11-26 … 2023-02-02 | `4- Metrologia/3051-00_intern.01.xls` · `DR(100%)` · H6 / L6 |
| 3056 | `0 131 S00 135` | `01` | 10 | 30 | 2020-01-29 … 2022-08-26 | `4- Metrologia/Interns/V00/3056-00_intern.1_100%.xls` · `DR (2)` · G6 / L6 |
| 3056 | `0 131 S00 135` | `02` | 4 | 14 | 2021-02-04 … 2021-08-24 | `4- Metrologia/Interns/V00/3056-00_intern5.xls` · `DR (1)` · G6 / L6 |
| 3056 | `0 131 S00 135` | `03/3E1004555360` | 1 | 2 | 2024-04-10 | `4- Metrologia/Interns/V00/3056-00_intern9.xls` · `DR` · G6 / L6 |
| 3056 | `0 131 S00 135` | `04` | 2 | 5 | 2024-05-15 … 2025-02-06 | `4- Metrologia/Interns/V00/3056-00_intern10.xls` · `DR` · G6 / L6 |
| 3167 | `0130S000338` | — | 30 | 84 | 2023-04-04 … 2026-09-22 (8 sin fecha válida) | `4- Metrologia/Interns/3167-00 Int_01.xls` · `DR_CC(P1)` · I6 |
| 3168 | `0310 S00 337` | `01` | 33 | 61 | 2023-02-20 … 2026-04-21 | `4- Metrologia/Interns/3168-00_intern.01.xls` · `DR(1)` · I6 / P6 |
| 3174 | `6494730` | `001` | 36 | 65 | 2023-02-24 … 2025-03-18 | `4- Metrologia/Version 00/Customer/3174-00_intern.01_for customer - copia.xls` · `DR_CMM 600 BAR` · J6 / Q6 |
| 3174 | `6494730` | `002` | 57 | 66 | 2023-06-16 … 2025-09-29 (4 sin fecha válida) | `4- Metrologia/Version 00/Interns/3174-00_intern.03.xls` · `DR_CMM` · J6 / Q6 |
| 3174 | `#REF!` | `#REF!` | 3 | 3 | 2025-03-18 … 2025-05-15 | `4- Metrologia/Version 00/Interns/3174-00_intern.30.xls` · `DR CMM` · K6 / Q6 |
| 3174 | `6494730` | `.004` | 2 | 4 | 2025-05-15 | `4- Metrologia/Version 00/Customer/3174-00_intern.31_Ball measurement after correction.xls` · `DR CMM` · K6 / Q6 |
| 3174 | `6494730` | `004` | 2 | 6 | 2025-05-30 … 2025-06-26 | `4- Metrologia/Version 00/Customer/3174-00_Intern.32_For PPAP.xls` · `DR_100% after correction` · K6 / Q6 |
| 3186 | `64947300` | `2` | 34 | 51 | 2023-04-21 … 2025-07-04 (2 sin fecha válida) | `5- Retoques molde/20230421_1st loop of correction/3186-00_intern.01_corrections.xls` · `DR_100%` · I6 / M6 |
| 3186 | `3247-00_int.01` | `0` | 1 | 1 | 2025-04-16 | `5- Retoques molde/20250609_9th loop/DR_20.xls` · `DR(tapa)` · I6 / P6 |
| 3195 | `0130S1B006` | `09/3E1008859560` | 21 | 35 | 2023-10-16 … 2026-04-28 (3 sin fecha válida) | `4- Metrologia/Interns/3195-00_intern.01.xls` · `DR` · K6 / Q6 |
| 3195 | `0130S1B006` | `07` | 2 | 3 | 2024-04-10 … 2026-10-01 | `4- Metrologia/Interns/3195-00_Int_03.xls` · `DR` · I6 / P6 |
| 3195 | `0130S1B006` | `07/3E1008859560` | 1 | 1 | 2024-07-05 | `4- Metrologia/Customer/REPORT HUMIDITY - 3195-00_int_04.xls` · `DR` · AA6 / AG6 |
| 3195 | `Comprovar punxons` | `00` | 1 | 3 | 2025-03-05 | `6- Método de medición/gauge check tool pins/D31956_intern.01.xls` · `DR_2cav.` · G6 / J6 |
| 3197 | `0140S00363` | `'3E1009447060` | 3 | 5 | 2023-04-18 … 2023-11-06 | `4- Metrologia/3197-00_intern.01.xls` · `DR_8cav.` · J6 / Q6 |
| 3197 | `0140S00363` | `3E1009447060` | 12 | 16 | 2024-01-10 … 2024-10-25 | `4- Metrologia/3197-00_intern.03.xls` · `DR_8cav.` · J6 / Q6 |
| 3202 | `885253-11250` | `-` | 12 | 29 | 2023-06-05 … 2025-05-23 | `4- Metrologia/Customers/3202-00_intern.01_COSTUMER.xls` · `DR_100%` · I6 / M6 |
| 3202 | `885253-11250` | `0` | 1 | 1 | 2024-01-02 | `4- Metrologia/Customers/PPAP-3202-00_INF.01.xls` · `DR_100%` · I6 / M6 |
| 3205 | `213137-10300` | `-` | 44 | 123 | 2023-09-13 … 2026-09-21 | `4- Metrologia/Customer/3205-00_intern.01.xls` · `DR_100%` · I6 / Q6 |
| 3205 | `213137-10300-B` | `B` | 1 | 2 | 2024-04-23 … 2025-02-06 | `4- Metrologia/Customer/3205-00_intern.17.xls` · `DR_Concentricitat_nou_metode` · I6 / M6 |
| 3205 | `213137-10300-B` | `-` | 1 | 4 | 2024-05-07 … 2024-10-18 | `4- Metrologia/Customer/3205-00_intern.14_2.xls` · `DR` · I6 / Q6 |
| 3206 | `213137-10280-A` | `A` | 16 | 64 | 2023-09-04 … 2024-03-26 | `4- Metrologia/Interns/3206-00_intern.01.xls` · `DR_(100%)` · I6 / M6 |
| 3206 | (vacío) | `213137-10280-A` | 1 | 1 | 2023-12-13 | `4- Metrologia/Interns/3206-00_intern.07.xls` · `DR_fm` · O6 |
| 3206 | `213137-10280-B` | `B` | 22 | 52 | 2024-04-17 … 2026-02-19 | `4- Metrologia/Customer/3206-00_intern.12.xls` · `DR_(100%)` · I6 / M6 |
| 3206 | `BSG-296-00` | `0` | 1 | 1 | 2025-04-16 | `5- Retoques molde/20250709_correction after ribs inserts/DR_17.xls` · `DR(base)` · I6 / L6 |
| 3212 | `0140S00237` | `06/3E1005491360` | 9 | 20 | 2024-01-20 … 2025-04-02 | `4- Metrologia/3212-00_intern.08.xls` · `DR` · H6 / L6 |
| 3212 | `0140S00237` | — | 2 | 2 | — | `4- Metrologia/3212-00_intern.04.xls` · `DR(100%)` · H6 |
| 3212 | `#REF!` | — | 1 | 1 | — | `4- Metrologia/3212-00_intern.06.xls` · `DR(100%)` · H6 |
| 3214 | `11206` | `G` | 14 | 31 | 2023-10-02 … 2025-10-21 | `4- Metrologia/Interns/3214-00_int.01.xls` · `DR` · H6 / L6 |
| 3214 | `C 11692` | `A` | 5 | 9 | 2025-11-12 … 2026-06-03 | `4- Metrologia/Interns/3214-00_int.10_OQLow.xls` · `DR` · H6 / L6 |
| 3218 | `6494730` | `002` | 77 | 193 | 2024-01-18 … 2026-09-15 (2 sin fecha válida) | `4- Metrologia/Interns/3218-00_intern.01.xls` · `DR_100%` · J6 / Q6 |
| 3218 | `64947300` | `2` | 1 | 1 | 2024-09-17 | `4- Metrologia/Interns/3218-00_intern.08.xls` · `315596` · J6 / Q6 |
| 3218 | `64947300` | `002` | 3 | 3 | 2025-03-13 … 2025-04-23 | `4- Metrologia/Interns/3218-00_intern.12_Settings.xls` · `315915` · J6 / Q6 |
| 3218 | `BSG-296-00` | `0` | 2 | 2 | 2025-04-16 | `5- Retoques molde/20250518 6th correction/3217_DR_intern17.xls` · `DR(base)` · I6 / P6 |
| 3218 | `3247-00_int.01` | `0` | 2 | 2 | 2025-04-16 | `5- Retoques molde/20250518 6th correction/3217_DR_intern17.xls` · `DR(tapa)` · I6 / P6 |
| 3218 | `6494730` | `0` | 1 | 1 | 2026-01-16 | `4- Metrologia/Interns/3218-00_intern.30_Comparison between productions.xls` · `KnO - 3D CMM+CT-scan +ICLs` · J6 / BP6 |
| 3218 | `6494730` | `004/19.2.2025` | 2 | 4 | 2026-02-02 | `4- Metrologia/Interns/3218-00_intern.31.xls` · `DR_100%-500BAR_update FM` · J6 / Q6 |
| 3218 | `6494730` | `004` | 13 | 61 | 2026-03-02 … 2026-09-15 (8 sin fecha válida) | `4- Metrologia/Interns/3218-00_intern.32.xls` · `DR_100%` · J6 / Q6 |
| 3233 | `0196S0000K` | `01/0196E0000J04` | 23 | 72 | 2024-07-02 … 2026-08-11 (1 sin fecha válida) | `4- Metrologia/Customer/3233-00_intern.01.xls` · `100%` · I6 / AO6 |
| 3233 | `0196S0000K` | `02/3E1014105160` | 1 | 1 | 2026-09-08 | `4- Metrologia/Customer/3233-00_intern.16.xls` · `100% BOSCH PORTAL` · I6 / AO6 |
| 3237 | `3 130 589 019` | `03` | 15 | 22 | 2023-03-08 … 2024-10-17 (2 sin fecha válida) | `6- Método de medición/3237-00_jig RB vs ITP.xls` · `DR_JIGS.` · I6 / Q6 |
| 3237 | `3 130 589 019` | `04` | 9 | 23 | 2024-11-29 … 2025-04-10 (1 sin fecha válida) | `4- Metrologia/Interns/V00/3237-00_intern.09.xls` · `DR` · J6 / N6 |
| 3237 | `3130589019` | `04` | 19 | 37 | 2025-03-03 … 2026-07-31 | `4- Metrologia/Interns/V00/3237-00_intern.15.xls` · `DR` · I6 / M6 |
| 3237 | `3130589019` | `05` | 2 | 2 | 2026-08-20 … 2026-09-15 | `4- Metrologia/Interns/V20/3237-20_intern.10.xls` · `CP` · I6 / M6 |
| 3238 | `313058901F` | `03/3E1011383160` | 14 | 18 | 2023-03-08 … 2024-10-14 | `6- Método de medición/3238-00_JIG RB vs ITP.xls` · `DR_4cav.` · I6 / Q6 |
| 3238 | `3 130 589 01F` | `04` | 6 | 24 | 2024-11-29 … 2025-10-28 | `4- Metrologia/Interns/V00/3238-00_intern.07.xls` · `DR` · I6 / M6 |
| 3238 | `3 130 589 01F` | `04/3E1011980460` | 1 | 1 | 2025-11-10 | `4- Metrologia/Interns/V20/3238-20_intern.03.xls` · `DR` · I6 / M6 |
| 3238 | `3 130 589 01F` | `05` | 3 | 3 | 2026-07-23 … 2026-09-09 | `4- Metrologia/Interns/V20/3238-20_intern.04.xls` · `DR` · I6 / M6 |
| 3288 | `BSG-296-00` | `0` | 3 | 5 | 2025-04-16 … 2025-05-20 | `5- Retoques molde/20260429_1 loop of correction/3247-00_intern.01.xls` · `DR(base)` · I6 / P6 |
| 3288 | `3247-00_int.01` | `0` | 1 | 1 | 2025-04-16 | `5- Retoques molde/20260429_1 loop of correction/3247-00_intern.01.xls` · `DR(tapa)` · I6 / P6 |
| 3288 | `BSG-296-00` | `1` | 7 | 17 | 2026-04-30 … 2026-09-23 | `4- Metrologia/Interns/3288-00_intern.01.xls` · `DR(base)` · I6 / AB6 |
| 3309 | `GF991-53540` | — | 13 | 26 | — | `4- Metrologia/Customer/3309-00 Int_02.xls` · `DR` · N3 |
<!-- planos-cabeceras:fin -->

## Observaciones con alcance

### Numeración de los globos entre revisiones (3205, 3206 y 3202)

- **Lo que se conserva es el número, no necesariamente la cota ni su tolerancia.** Son tres cosas distintas: que
  el número siga existiendo, que señale la misma característica y que esta tenga la misma especificación.
- **Altas y bajas de números** (tabla `globo`, por `.icp`):
  - 3205, de `3205.icp` (`−`) a `3205-A.icp`: altas 46, 47, 107–115 y 145, aunque el 200–204 ya existía; de A a
    B (10/2023): baja el 145 y entran 146, 147 y 148; en la B de 10/2024 baja el 85. **No se añaden siempre al
    final**, y también desaparecen números.
  - 3206, de `3206-A.icp` a la B (10/2023): baja el 50 y entran 108, 109 y 110; en la B de 10/2024 baja el 107.
  - 3202: `3202.icp` y `885253-11250_G.icp` tienen los mismos 232 números.
- **Posición:** en el 3205, entre la A y la B de 10/2024, cinco de los globos que más se desplazaban tras ajustar
  escala y desplazamiento (70, 9, 32, 109 y 113) señalan la misma cota: se movió el dibujo. Del plano de estudio
  al definitivo (3206) no se conserva: en una muestra de 6, el 63 y el 64 señalan otra cota, el 75 y el 200 la
  misma, y 2 no se pudieron comprobar. Revisión visual del 12/11/2026, sin más muestra.
- **Para el visor:** unir por número es una **correspondencia candidata**, a validar, dentro de un mismo
  componente y una misma serie de planos. Una correspondencia validada sirve para localizar la cota; las
  tolerancias se toman de cada revisión. No extender a Bosch ni a otras piezas sin comprobarlo.

### La cabecera del informe frente a la revisión aplicada

- Que exista un plano posterior no prueba que debiera aplicarse de inmediato a todos los lotes: **revisión
  publicada y revisión aplicable son cosas distintas**. Un «retraso» de la cabecera no es por sí solo un
  incumplimiento.
- La cabecera puede seguir en una revisión cuando las cotas ya son de otra (3202, 3233), mezclar revisiones
  entre hojas y copias de un mismo informe (3205 `intern.17`, 3233 `intern.16`), citar un índice sin PDF (3195,
  `09`) o mezclar el número del conjunto con el nivel de los componentes (3288).
- Para saber qué se aplicó: leer la cabecera **hoja a hoja**, contrastar nominales y tolerancias con cada
  revisión y conservar las copias como alternativas.

## Pendiente

- Preguntas a INTEPLAST: [A26](../docs/preguntas-abiertas.md#a26-revisiones-plano) (3237/3238, 3195, 3202,
  3233 y 3288).
- 3202: comparar el resto de cotas de la A con el plano `−`. 3195: comparar el resto del plano. 3233: comparación
  completa de nominales y clases (aquí solo la capa de texto en la misma posición).
- Visor: decidir qué cuenta la columna «Planos» antes de usar el catálogo.
