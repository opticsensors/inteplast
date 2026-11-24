"""Sube las propuestas de `propuestas.py` como portadas por pieza, por la API.

Uso:
    python subir.py <carpeta_salida> <vinculos.txt> <.env> [--url http://localhost:8000]

`vinculos.txt` es la salida de (psql -At, solo lectura):
    select p.code, f.name, f.id, p.id, a.id, s.id, s.version
    from featureasset a join feature f on f.id=a.feature_id join part p on p.id=a.part_id
    join storedfile s on s.id=a.file_id where a.kind='part';

Usa los mismos endpoints que la ficha (`POST /files/`, `PUT /features/{id}` con
`part_covers`), así que el servidor valida pieza, adjunto, versión y SHA-256.
No toca vínculos que ya tienen portada propia (imagen o caras): se listan como
omitidos. Las credenciales salen del `.env` y no se imprimen.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests


def leer_env(path: str) -> dict[str, str]:
    env = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main(out_dir: str, vinculos: str, env_path: str, url: str = "http://localhost:8000") -> None:
    api = url.rstrip("/") + "/api/v1"
    # Con SHAREPOINT_ENABLED=true la app solo admite el login de Microsoft: se usa el
    # token de la sesión del navegador (variable INTEPLAST_TOKEN), que además lleva
    # la cuenta de Microsoft con la que el servidor comprueba el STEP por Graph.
    token = os.environ.get("INTEPLAST_TOKEN")
    if not token:
        env = leer_env(env_path)
        r = requests.post(
            f"{api}/login/access-token",
            data={"username": env["FIRST_SUPERUSER"], "password": env["FIRST_SUPERUSER_PASSWORD"]},
            timeout=30,
        )
        if not r.ok:
            sys.exit(f"Login {r.status_code}: {r.text[:200]}. Define INTEPLAST_TOKEN.")
        token = r.json()["access_token"]
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"

    links = {}
    for line in Path(vinculos).read_text(encoding="utf-8").splitlines():
        code, feature, feature_id, part_id, asset_id, file_id, version = line.split("|")
        links[(feature, code, file_id)] = (feature_id, part_id, asset_id, version or None)

    data = json.loads((Path(out_dir) / "propuestas.json").read_text(encoding="utf-8"))
    por_feature: dict[str, list] = {}
    for p in data["propuestas"]:
        key = (p["feature"], p["pieza"], p["file_id"])
        if key not in links:
            print(f"SIN VÍNCULO {key}")
            continue
        feature_id, part_id, asset_id, version = links[key]
        detalle = s.get(f"{api}/features/{feature_id}", timeout=60).json()
        actual = next((c for c in detalle.get("part_covers", []) if c.get("part_id") == part_id), {})
        if actual.get("image") or actual.get("cover_3d"):
            print(f"OMITIDO (ya tiene portada) {p['feature']} {p['pieza']}")
            continue
        with open(Path(out_dir) / p["imagen"], "rb") as fh:
            up = s.post(f"{api}/files/", files={"file": (f"caras-llm-{p['pieza']}.png", fh, "image/png")}, timeout=60)
        up.raise_for_status()
        por_feature.setdefault(feature_id, []).append({
            "part_id": part_id,
            "image_id": up.json()["id"],
            "cover_3d": {
                "asset_id": asset_id, "part_id": part_id, "file_id": p["file_id"],
                "file_version": version, "source_sha256": p["source_sha256"],
                "geometry_key": p["geometry_key"], "recipe": "occt-import-js@0.0.23/cover-v1",
                "faces": p["faces"], "camera": p["camera"],
            },
            "_txt": f"{p['feature']} {p['pieza']}",
        })
    for feature_id, covers in por_feature.items():
        nombres = [c.pop("_txt") for c in covers]
        r = s.put(f"{api}/features/{feature_id}", json={"part_covers": covers}, timeout=300)
        print(("OK   " if r.ok else f"ERROR {r.status_code} {r.text[:300]} ") + ", ".join(nombres))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--url")]
    url = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--url=")), "http://localhost:8000")
    main(*args[:3], url=url)
