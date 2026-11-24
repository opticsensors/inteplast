"""Propuestas de caras por feature y pieza (LLM, 24/11/2026, sin validar).

Uso:
    python propuestas.py <carpeta_glb> <carpeta_salida>

`<carpeta_glb>` contiene una carpeta por `StoredFile.id` con el GLB `cover-v1`
que prepara la app (`/app/uploads/previews/<file_id>/<cache_key>.glb`).
Escribe en la salida, por cada propuesta, `<feature>_<pieza>.png` (captura con
el aspecto de la portada) y `propuestas.json` (caras, cámara, huellas). Además,
`pieza_<código>.png` con todos los features de la pieza en colores y leyenda.

Las reglas y su justificación están en `reglas.py` y en el README. Una pieza
sin regla fiable no lleva propuesta: se anota en `SIN_PROPUESTA`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import caras
import reglas

# file_id del CAD de la pieza (StoredFile) en la instalación local del 24/11/2026.
CAD = {
    "2820": "b1415f73-53b5-49ce-983f-e14829b83954",
    "3051": "430e7086-52b7-4c57-a10a-4610b166ffae",
    "3197": "7d1235aa-e6e0-4b61-b3d6-53ae916b4871",
    "3174": "c4d8179f-3826-4932-bf6c-18d6222d75e3",
    "3186": "e4dafe7c-9600-4127-8795-c32b76839879",
    "3195": "6c66e775-552f-47db-a711-6a6b4de0c399",
    "3218": "675d21bc-f3d2-4c01-af17-88631b039b47",
    "3226": "7c343f6c-7ece-469f-8c24-4f0bbe5306fd",
    "3205": "93c560f4-ba46-40d7-a383-552dd4643423",
    "3206": "cfc1244e-bb43-41eb-812d-38efc054ea4f",
    "3214": "aef61fa7-642f-4869-bf2c-6bae45302cc9",
    "3233": "afe769d1-a587-4f88-8965-eb1c5e2b3b54",
    "3237": "efe46e18-ebe4-47ff-9dea-52d597a8cee3",
    "3238": "da918409-ed53-418e-a90c-777331a91d9f",
    "3168": "93b9018d-e9ba-4c5f-b7ae-b924fde4915f",
    "3056": "3ce2ce87-51da-4d9d-8a20-25ed56d665ec",
    "3167": "a13dc3a7-1f0c-4ac5-8334-f87aa0de43b1",
}


def _pares(pares):
    out = []
    for a, b, _ in pares:
        out += [a, b]
    return out


def _nervio(m):
    return reglas.directores_energia(m)[0]


def _plano_a(m):
    _, base = reglas.directores_energia(m)
    return reglas.plano_apoyo(m, base, tol=0.02) if base is not None else []


def _plano_principal(m):
    planos = [c for c in m.caras if c.tipo == "plano"]
    mayor = max(planos, key=lambda c: c.area)
    d = mayor.centro @ mayor.normal
    return [
        c for c in planos
        if c.normal @ mayor.normal > 0.9999 and abs(c.centro @ mayor.normal - d) < 0.02
    ]


# (feature, pieza): (regla, confianza, por qué)
PROPUESTAS = {
    ("Bolt Eye", "2820"): (lambda m: reglas.agujeros(m, 1.9, 0.015), "media",
        "Agujeros Ø3,8 de las 5 orejas ([]207 3,8 +0,1; []252 5× posición). Candidata en cotas-por-feature."),
    ("Bolt Eye", "3051"): (lambda m: reglas.agujeros(m, 1.9, 0.015), "alta",
        "Agujeros Ø3,8 de las 4 orejas (N880 Ø3,8 +0,1; N890 posición)."),
    ("Bolt Eye", "3197"): (lambda m: reglas.agujeros(m, 2.0, 0.015, excluir_centro=10), "alta",
        "Agujeros Ø4 de las 4 orejas (N230 Ø4 +0,1; N220 posición); se excluye el agujero central."),
    ("Clips en Piezas", "3174"): (lambda m: reglas.pines(m, 2.3, 0.01), "media",
        "Tres pines Ø4,6 que se clipan (N511, corrección 2.12 «move the clips 2 and 3»)."),
    ("Clips en Piezas", "3186"): (lambda m: reglas.pines(m, 2.3, 0.01), "media",
        "Misma placa que el 3174: tres pines Ø4,6 (plano archivado del 3174, I-301)."),
    ("Clips en Piezas", "3218"): (lambda m: reglas.pines(m, 0.985, 0.02, area_min=5), "baja",
        "Pines Ø2 (clips 1–3: N2603/2702/2902 Ø2 ±0,05). Ø1,94 en uno de ellos; sin confirmar cuál es cada clip."),
    ("Clips en Piezas", "3195"): (lambda m: reglas.fuera_de_radio(
        m, 31.3, excluir=lambda w: w[:, 1].min() < -28 and abs(w[:, 0]).max() < 12), "baja",
        "Pestañas que sobresalen del disco del portaescobillas. La cota 3120 no dice qué clip."),
    ("Clips en Piezas", "3226"): (lambda m: reglas.extremos(m, 0, 0.08), "baja",
        "Pestañas de los dos extremos. El informe no numera cotas (A28): solo forma."),
    ("Nervios de Soldadura", "3205"): (_nervio, "alta",
        "5 directores de energía: altura 0,9 (152), flancos 60° (154), R24,1 (19)."),
    ("Nervios de Soldadura", "3206"): (_nervio, "alta",
        "7 nervios: 0,6 (20), 6 (21), altura 0,9 (83), borde R25,6 (64)."),
    ("Planitudes", "3205"): (_plano_a, "media",
        "Plano A = apoyos de los nervios (N5 planitud 0,1; el método mide en R19 y R24)."),
    ("Planitudes", "3206"): (_plano_a, "media",
        "Plano A = apoyos de los nervios (N9 planitud 0,1)."),
    ("Planitudes", "3168"): (_plano_principal, "baja",
        "Cara plana mayor y las coplanarias (230 planitud 0,6 CZ; 1330 0,4). No consta sobre qué cara."),
    ("Paredes muy Delgadas", "3233"): (lambda m: _pares(reglas.espesores(m, 0.4, 0.01)), "media",
        "Caras enfrentadas a 0,40 (520 espesor 0,4 ±0,05 bajo las ondulaciones)."),
    ("Paredes muy Delgadas", "3237"): (lambda m: _pares(reglas.espesores(m, 0.4, 0.01)), "media",
        "Caras enfrentadas a 0,40 (123 espesor 0,4 ±0,05, sección D–D)."),
    ("Paredes muy Delgadas", "3238"): (lambda m: _pares(reglas.espesores(m, 0.4, 0.01)), "media",
        "Caras enfrentadas a 0,40 (148 espesor 0,4 ±0,05, sección D–D)."),
    ("Tetones", "3214"): (lambda m: reglas.pines(m, 0.57, 0.01), "alta",
        "Cuatro pines Ø1,14 (cota 6, corrección 1.1 «increase in Ø0,03 the pins»)."),
    ("Tetones", "3167"): (lambda m: reglas.pines_con_desmoldeo(m, 0.7, 0.025), "media",
        "Cota 500: seis pines Ø1,4 ±0,05. Se admiten los flancos con salida y sus caras contiguas; "
        "la corrección 1.3 muestra tres nervios por pin."),
}

SIN_PROPUESTA = {
    ("Clips en Piezas", "3309"): "Los brazos con gancho van en diagonal; ni los extremos ni el radio los aíslan.",
    ("Nervios de Soldadura", "3214"): "El nervio central (altura 0,26–0,3) no tiene el perfil a 60° de 3205/3206.",
    ("Pockets", "3202"): "La pieza no tiene CAD vinculado.",
    ("Pockets", "3056"): "La regla de espesor (0,85) encuentra 4 caras de pared ocultas dentro "
        "de la pieza: la captura no enseña ningún pocket. Falta una regla del hueco.",
    ("Pockets", "3167"): "La regla de espesor (0,8) encuentra 76 caras de pared y solo el 3 % "
        "se ve en la mejor vista. Falta una regla del hueco.",
    ("Bolt Eye", "3212"): "Portada hecha por Eduard: no se toca.",
    ("Tetones", "3288"): "Portada hecha por Eduard: no se toca.",
}

COLORES = [(0xE3, 0x26, 0x36), (0x1F, 0x77, 0xB4), (0x2C, 0xA0, 0x2C), (0xFF, 0x7F, 0x0E), (0x94, 0x67, 0xBD)]


def _leyenda(img, items):
    from PIL import Image, ImageDraw, ImageFont

    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("segoeui.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    y = 10
    for nombre, col in items:
        d.rectangle([10, y + 3, 24, y + 17], fill=col, outline=caras.LINEA)
        d.text((32, y), nombre, fill=caras.LINEA, font=font)
        y += 22
    return np.asarray(im)


def main(glb_dir: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    resultado, por_pieza = [], {}
    def modelo(pieza):
        archivos = list((Path(glb_dir) / CAD[pieza]).glob("*.glb"))
        if len(archivos) != 1:
            raise ValueError(f"{pieza}: se esperaba un único GLB para el CAD, hay {len(archivos)}")
        return caras.leer_glb(archivos[0])

    for (feature, pieza), (regla, conf, porque) in PROPUESTAS.items():
        fid = CAD[pieza]
        m = modelo(pieza)
        sel = sorted({c.key for c in regla(m)})
        if not sel:
            print(f"{feature} {pieza}: la regla no encuentra caras")
            SIN_PROPUESTA[(feature, pieza)] = "La regla no encuentra caras."
            continue
        cam, vis = caras.encuadre(m, sel)
        img = caras.render(m, {k: caras.ROJO for k in sel}, cam)
        nombre = f"{feature.replace(' ', '_')}_{pieza}.png"
        caras.guardar_png(img, out / nombre)
        print(f"{feature} {pieza}: {len(sel)} caras, visibles {vis:.0%}")
        resultado.append({
            "feature": feature, "pieza": pieza, "file_id": fid,
            "source_sha256": m.source_hash, "geometry_key": m.geometry_key,
            "faces": [{"mesh": a, "face": b} for a, b in sel],
            "camera": {k: [float(x) for x in v] for k, v in cam.items()},
            "imagen": nombre, "confianza": conf, "porque": porque,
            "caras_visibles": round(vis, 2),
        })
        por_pieza.setdefault(pieza, []).append((feature, sel))
    # Vista previa del paso 2: una pieza con todos sus features en colores.
    for pieza, feats in por_pieza.items():
        if len(feats) < 2:
            continue
        m = modelo(pieza)
        col, todas = {}, []
        for i, (_, sel) in enumerate(feats):
            for k in sel:
                col[k] = COLORES[i % len(COLORES)]
            todas += sel
        cam, _ = caras.encuadre(m, sorted(set(todas)))
        img = caras.render(m, col, cam)
        img = _leyenda(img, [(f, COLORES[i % len(COLORES)]) for i, (f, _) in enumerate(feats)])
        caras.guardar_png(img, out / f"pieza_{pieza}.png")
    (out / "propuestas.json").write_text(json.dumps({
        "fecha": "2026-11-24", "autor": "Prototipo de reglas geométricas, pendiente de revisión de Eduard",
        "propuestas": resultado,
        "sin_propuesta": [{"feature": f, "pieza": p, "motivo": t} for (f, p), t in SIN_PROPUESTA.items()],
    }, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
