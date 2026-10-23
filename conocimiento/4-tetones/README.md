# 4- Tetones

> Carpeta `Exemples/4- Tetones`. 107 ficheros, 1,7 GB. Leído el 2026-10-21 (biblioteca:
> `consultar.py arbol "4- Tetones" --detalle`).

| Pieza | Contenido | Ficha |
|---|---|---|
| **3288** | Proyecto completo (105 ficheros): SOP oval RCP 3.1, bimaterial, BASE + TAPA | [3288.md](3288.md) |
| 3167 | Solo `Readme.txt`: *«Infomración referente a esta pieza está en el apartado 6-Pockets»* | → `6- Pockets/3167` |
| 3214 | Solo `Readme.txt`: *«… en el apartado 2-Nervios de Soldadura»* | → `2- Nervios de Soldadura/3214` |

## Qué es el feature aquí

En el 3288 los **tetones** son los pines que se **remachan (soldadura en caliente)** para unir
las dos piezas del conjunto. El método de medida lo dice en su item 8: *«Altura de remachado no
debe sobresalir del plano base. Comprobar que los tetones soldados no sobresalen pasando el
dedo»* (`3288/6- Método de medición/MM732880000.pdf`, página 3). Es un control **visual/táctil**,
sin cota numérica en el informe.

Las correcciones de molde documentadas en esta pieza **no tratan de los tetones**: casi todas
son rebabas (*flashes/burrs*) y tamaño general de la pieza. Ver [3288.md](3288.md#correcciones).
Para fichar el feature «tetón» con este ejemplo faltaría identificar qué cotas del plano
corresponden a los tetones (pregunta en [incongruencias.md](../incongruencias.md)).

## Diferencias con el piloto 3212 (resumen)

| Aspecto | 3212 (Bolt Eye) | 3288 (Tetones) |
|---|---|---|
| Esqueleto | 8 carpetas (`1-2D y 3D Pieza` … `8- STL peça real`) | 7 carpetas (`1- 2D y 3D pieza` … `7- Pieza real STL`) |
| Cliente / sector | Robert Bosch BueP, automoción | **B. Braun** (ref. cliente 508008), sanitario: Purell, MEVOPUR |
| Pieza | 1 pieza, molde de 16 (se controlan 4) | Conjunto bimaterial BASE + TAPA, molde cubo Foboha 16+16; informes con 20 cavidades |
| Metrología | CSV de CMM por cavidad + XLS PPAP | **Solo XLS PPAP** + PDF exportados (`DR_*.pdf`); KEYENCE, video CNC, galgas. **Sin CSV de CMM** |
| Método de medida | DOCX de Bosch | Ficha de ayuda PDF de INTEPLAST + `MM3288_rev0.xlsx` |
| Planos | PDF escaneado sin globos legibles | PDF con globos **y** ficheros `.icp`/`.prf` del software de globos de la CMM ZEISS |
| Correcciones | 2 planes (2024) | 3 *loops* (2026), misma plantilla PPTX con títulos en catalán |
| Moldflow | Estudio `.mfr` | `README.txt`: *«No Moldflow information available for this part.»* |
