# Caras CAD de cada feature (propuesta del LLM, 24/11/2026)

Prueba pedida por Eduard el 24/11/2026: que el LLM marque en rojo las caras de cada feature en
el CAD de cada pieza, como hizo él a mano con el Bolt Eye del 3212, para **ver cómo queda** y
preparar el paso siguiente (una pieza con todos sus features en colores y leyenda).

> 🔴 **Son propuestas del LLM sin validar.** No acreditan una selección automática fiable ni
> sustituyen la decisión de Eduard o de INTEPLAST (regla del 16/11/2026, [AGENTS.md](../../../AGENTS.md)).
> Si una portada está mal, se corrige la **regla** en `reglas.py` y se vuelve a generar; no se
> retocan caras a mano en la app para disimularlo.

## Qué hay

| Fichero | Qué hace |
|---|---|
| `caras.py` | Lee el GLB `cover-v1` que prepara la app (triángulos + rangos de caras OCCT), clasifica cada cara (plano, cilindro con radio/eje/pin o agujero, otra), dibuja con el aspecto y la cámara de `StepCoverCanvas.tsx` (objeto centrado, FOV 45°, Z arriba) y elige un encuadre donde se vean las caras marcadas |
| `reglas.py` | Reglas geométricas por tipo de feature: agujeros y pines por diámetro, director de energía (flancos a 60°), plano de apoyo, espesores entre caras enfrentadas, zonas extremas |
| `propuestas.py` | Qué regla se aplica a cada feature×pieza, con confianza y motivo (de [cotas-por-feature.md](../../../conocimiento/cotas-por-feature.md)). Escribe capturas PNG, `propuestas.json` y la vista previa multicolor por pieza |
| `subir.py` | Guarda las propuestas como portadas por pieza con la API de la app (`POST /files/`, `PUT /features/{id}` con `part_covers`). No toca vínculos que ya tienen portada propia |

La app no importa nada de aquí. Se ejecuta con el Python del equipo (ruta absoluta, ver
`CLAUDE.md`). Copiar los `.py` a una carpeta temporal antes de ejecutarlos: el 24/11/2026 Python
se quedó bloqueado varias veces leyendo módulos desde la carpeta de OneDrive.

```powershell
# 1. GLB preparados por la app (solo lectura)
docker compose cp backend:/app/uploads/previews/<file_id> <tmp>\glb\
# 2. Propuestas, capturas y vista previa por pieza
& $py propuestas.py <tmp>\glb <tmp>\out
# 3. Subida a la instalación local
& $py subir.py <tmp>\out <tmp>\vinculos.txt .env
```

## Reglas y resultado del 24/11/2026

Ver `propuestas.json` de la ejecución para las caras y la cámara exactas. Confianza = cuánto se
apoya la regla en una cota concreta, no un acierto medido.

| Feature | Piezas | Regla | Confianza |
|---|---|---|---|
| Bolt Eye | 2820, 3051, 3197 | Agujeros Ø3,8 / Ø3,8 / Ø4 de las orejas (sin el central) | media / alta / alta |
| Clips | 3174, 3186 | Tres pines Ø4,6 (N511) | media |
| Clips | 3218 | Pines Ø2 (N2603/2702/2902) | baja |
| Clips | 3195, 3226 | Pestañas fuera del disco / en los extremos: solo forma | baja |
| Nervios de soldadura | 3205, 3206 | Director de energía: parejas de flancos a 60° y todo lo que cae en su caja (5 y 7 nervios, altura 0,9) | alta |
| Planitudes | 3205, 3206 | Plano A = apoyos de esos nervios | media |
| Planitudes | 3168 | Cara plana mayor y coplanarias | baja |
| Paredes muy delgadas | 3233, 3237, 3238 | Caras planas enfrentadas a 0,40 ± 0,01 con solape | media |
| Tetones | 3214 | Cuatro pines Ø1,14 (cota 6) y sus tapas | alta |
| Tetones | 3167 | Pines Ø2: la cota 500 dice Ø1,4 y no hay cilindros de ese diámetro | baja |

**Sin propuesta:** 3309 (clips en diagonal, ninguna regla los aísla), 3214 en Nervios (el nervio
central no tiene el perfil a 60°), Pockets 3056 y 3167 (la regla de espesor 0,85 / 0,8 encuentra
paredes ocultas dentro de la pieza; la captura no enseña ningún pocket, falta una regla del hueco)
y 3202 (sin CAD). **No tocados:** 3212 Bolt Eye y 3288 Tetones,
portadas de Eduard.

## Límites

- Las caras son índices del GLB (`mesh:face`). Valen para esos bytes y esa receta
  (`occt-import-js@0.0.23/cover-v1`): si cambia el STEP, la app pide limpiar la selección.
- La captura PNG la dibuja PyVista, no el navegador. El tono y el grosor de las aristas son
  parecidos a los de la app, no idénticos. Al ampliar, la app dibuja el 3D con sus propias
  caras y cámara.
- El encuadre busca la dirección que enseña más caras marcadas y su área. Con caras repartidas
  por toda la pieza enseña la pieza entera.
