# 4- Tetones

> Carpeta `Exemples/4- Tetones`. 107 ficheros, 1,7 GB. Leído el 2026-10-21 (biblioteca:
> `consultar.py arbol "4- Tetones" --detalle`).

| Pieza | Contenido | Ficha |
|---|---|---|
| **3288** | Proyecto completo (105 ficheros): SOP oval RCP 3.1, bimaterial, BASE + TAPA | [3288.md](3288.md) |
| 3167 | Solo `Readme.txt`: *«Infomración referente a esta pieza está en el apartado 6-Pockets»* | → `6- Pockets/3167` |
| 3214 | Solo `Readme.txt`: *«… en el apartado 2-Nervios de Soldadura»* | → `2- Nervios de Soldadura/3214` |

## Qué es el feature aquí

En el 3288 se controlan **tetones soldados/remachados**; la fuente no concreta el procedimiento térmico.
El método de medida lo dice en su item 8: *«Altura de remachado no
debe sobresalir del plano base. Comprobar que los tetones soldados no sobresalen pasando el
dedo»* (`3288/6- Método de medición/MM732880000.pdf`, página 3). Es un control **visual/táctil**,
sin valor numérico en ese item.

**Sí hay identificación de cota**: `MM732880000_rev00.pdf` (25/09/2026), página 6, vincula el
remachado a **DIM. Nº 80**, exige además que no haya GAP entre agujero y pin y prescribe lupa DG0266.
El método refiere el conjunto **BSG-296-00, nivel 2 de 26/08/2026**; no confundir ese 80 con el 80
de `DR(base)` (BSG-296-01 rev1, nominal 14,45). Falta reconciliar todas las cotas de los tetones
entre componentes y revisiones; I-106 queda acotada por esta evidencia.

Los planes de corrección tratan sobre todo rebabas (*flashes/burrs*) y tamaño general, sin nombrar
explícitamente el remachado. Ver [3288.md](3288.md#correcciones).

## Diferencias con el piloto 3212 (resumen)

| Aspecto | 3212 (Bolt Eye) | 3288 (Tetones) |
|---|---|---|
| Esqueleto | 7 carpetas presentes, numeradas 1 y 3–8 | 7 carpetas (`1- 2D y 3D pieza` … `7- Pieza real STL`) |
| Cliente / sector | Robert Bosch BueP, automoción | **B. Braun**, sector sanitario inferido por el cliente y materiales ([3288.md](3288.md)) |
| Pieza | 1 pieza, molde de cuatro cavidades c13–c16 (`INTRO!C40`) | Conjunto bimaterial BASE + TAPA, molde cubo Foboha 16+16; informes con 20 cavidades |
| Metrología | CSV de CMM por cavidad + XLS PPAP | **Solo XLS PPAP** + PDF exportados (`DR_*.pdf`); KEYENCE, video CNC, galgas. **Sin CSV de CMM** |
| Método de medida | DOCX de Bosch | Ficha de ayuda PDF de INTEPLAST + `MM3288_rev0.xlsx` |
| Planos | PDF escaneado sin globos legibles | PDF con globos **y** ficheros `.icp`/`.prf` de infra-CONVERT |
| Correcciones | 2 planes (2024) | 3 *loops* (2026), misma plantilla PPTX con títulos en catalán |
| Moldflow | Estudio `.mfr` | `README.txt`: *«No Moldflow information available for this part.»* |
