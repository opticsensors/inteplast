# 2- Nervios de Soldadura

> `Exemples/2- Nervios de Soldadura`. 748 ficheros, 3,7 GB. Leído el 2026-10-21. Rutas relativas a esa carpeta.
> Perfiles: `perfil_ppap` (288 hojas), `perfil_correccion` (198 diapositivas). También son el origen de
> `7- Planitudes/3205` y `/3206` y de `4- Tetones/3214` (allí solo hay un `Readme.txt` que remite aquí).

## Piezas

| Pieza | Qué es | Plano / nº pieza | Cavidades / columnas documentadas | Correcciones |
|---|---|---|---|---|
| **3205** | SHROUD, WATER PUMP | `213137-10300` (y variante `-B`) | 8 (algunas hojas 2–38 columnas) | 10 loops (09/2023 → 04/2026) |
| **3206** | SHROUD, WATER PUMP | `213137-10280-A` y `-B` | 4 | unas 9 entregas (09/2023 → 07/2025) |
| **3214** | Bottom pencil part | plano `11206` / `C 11692`; refs. `R-2971`, `R-2718` | 4–8 | 2 planes (10/2023, 11/2023) |

3205 y 3206 son **la misma familia de pieza en dos moldes** (8 y 4 cavidades) y comparten útiles de medida
(`6- Método de medición/…/3205-C`, `3205-D`: CATPart, STEP y PDF idénticos en las dos carpetas).

## Qué es el «nervio de soldadura»

Son los **directores de energía** de la soldadura del *shroud*: nervios finos que se funden al soldar.
La corrección 6.1 lo dice así: *«Moure tot el director d'energia 0,1 mm cap a la part exterior … La
longitud del director d'energia està correcte (cota 17)»*
(`3205/5- Retoques molde/6th loop of correction (possible-rib inserts)/Archiv/20240425_Mold cor…pptx`).
Los informes PPAP lo citan como *«Draft angle of blade groove, and welding ribs»* (cota 203 del 3206, INFORMATIVE).

## Historia de las correcciones (3205, la más larga)

| Loop | Carpeta | Tema |
|---|---|---|
| 1 | `1st loop of correction/20230915-Mold correction_1_P3205.pptx` | Primer plan (plantilla `Tool correction`) |
| 2–3 | `2on loop … burrs and diameter 20231012`, `3rd loop of correction burrs` | Rebabas y diámetros; incluye fotos de WhatsApp |
| 5 | `5th loop of correction GPF` | Correderas nuevas (`new sliders update GPF`). ⚠️ El PPTX base es el plan **del 3206** (cabecera P3206, mismo texto que el de `3206/20240320_After new sliders correction/`); las versiones `_v1`/`_v2` no nombran pieza ([I-402](../incongruencias.md)) |
| 6 | `6th loop of correction (possible-rib inserts)` | Mover el director de energía; propuesta de **rediseño del nervio** (`Insert explanation`: *CURRENT / PROPOSED SHROUD RIB DESIGN*) |
| 7–8 | `7th / 8th loop … (after new inserts on the ribs)` | Tras poner **postizos en los nervios**: altura de nervios y ranuras, diámetros +0,1…+0,3, rebabas en nervios por cavidad |
| 9–10 | `9th`, `10th loop of correction` | *«Correcció 10.1 Burrs on the ribs / CAVITY 2: NERVI 1, 7, 9»*… |

🔑 **Lección del feature**: las rebabas en los nervios de soldadura se corrigieron loop tras loop
hasta **cambiar el diseño a nervios postizos** (loops 6–7), y aun así siguieron rebabas en los
loops 8–10. En el 3206, el matricero local (`20231128_local moldmaker evaluation/Presentation Schroud 4cavs.pptx`)
atribuye defectos a causas del molde, no del proceso: *«0,1mm runout difference in the ejection core»*,
*«central hole is around 0,03mm bigger than injection side pin»*, y un acabado peor porque
*«sparkerosion was not correctly done … mistake in spare erosion program»*.

## Formatos y diferencias con el 3212

- **Informe PPAP en castellano** (`Nombre pieza:`, `Nº Plano:`, `CP: CONTROL PLAN DIMENSION`,
  `SPC: STATISTICAL DIMENSION`) con columna `class`, CAV.1–8 en I–P y **columnas de corrección dentro
  del propio informe de metrología** (`Dim`, `Corr.`, CAV.1… desde la columna 20). En el 3212 la
  previsión estaba en un libro aparte.
- Hojas `DR_100%` y `DR_100% (costumer)` (informe interno y para el cliente).
- Planes de corrección en **dos plantillas** que conviven en la misma pieza: `Tool correction n.m`
  y `Correcció nr. n.m` / `Pla de correccions nº10 – P3205` con `Situació actual:` / `Pla de correcció:`
  (esta segunda ya aparece en marzo–abril de 2024, no solo en 2025–2026),
  más presentaciones libres (`Rebaves.pptx`, `8 cavity tool_23.10.2023.pptx`, `Insert explanation`).
- **La numeración se reinicia**: tras los postizos, el loop 7 vuelve a `Correcció nr. 1.1`; los loops 9 y 10 se
  numeran `9.x` y `10.x`.
- **Versiones del mismo plan con magnitudes distintas**: en `3206/…/20250709_correction after ribs inserts/`,
  diapositiva 2, `20250723_Pla de correció_1 (after…)` propone +0,15/+0,3; `20250729_…` sin sufijo,
  +0,05/+0,25; y `20250729_…_customer`, **+0,1/+0,15/+0,25** según la zona. No consta cuál se ejecutó.
  El archivo de 29/07 dentro del loop 7 del **3205** conserva las cotas 6, 7, 8, 12, 19, 83 y 84 del 3206;
  las versiones propias del 25/08 citan otras cotas. No decidir la pieza solo por la carpeta.
- 3205 y 3206 tienen **planos con globos** (`6- Método de medición/DRW ballooned/…`, `.icp`/`.prf`/`.tif`),
  como el 3288.
- Moldflow: `.mfr` de 779 MB en 3205; en 3206 solo un **vídeo de llenado** `RP-3083_Movie_RevA.avi` (10 s),
  el formato que recomendó EA en la reunión del 24/09/2026; en 3214 un `README.txt`.
- Correos `.msg` y fotos de WhatsApp en las carpetas de retoques (con rutas de más de 260 caracteres).
- 3214: informes sin CMM; dos planes de corrección en la plantilla `Tool correction`.
- 🔴 3206 `4- Metrologia/Customer/3206-00_intern.121.xls` y `.122.xls`: la hoja `DR_(customer) (2)` es una copia
  de `DR_(customer)` con cada valor recalculado por `RANDBETWEEN(valor·0,9998; valor·1,0002)` (I-003).

## Pendiente de profundizar

- ~~Errores de lectura en 8 ficheros de retoques~~: resueltos (0 errores en la biblioteca).
- Cuantificar, cavidad a cavidad, si las rebabas en nervios bajan tras los postizos (fotos y `Rebaves.pptx`).
