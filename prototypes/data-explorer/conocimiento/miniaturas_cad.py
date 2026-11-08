"""Captura de cada pieza a partir de su STEP de `1- 2D y 3D pieza`, para la cuadrícula de Piezas.

Se hace una vez y el visor solo sirve los JPEG de `out/conocimiento/cad/`: no necesita leer STEP.
El STEP se lee con el lector oficial (`backend/app/preview_converter.py`). Necesita sus mismas
librerías y un Python con pyvista:

    python -m venv --system-site-packages <fuera de OneDrive>
    <venv>/Scripts/python -m pip install cadquery-ocp==7.9.3.1.1 trimesh==5.1.0
    <venv>/Scripts/python miniaturas_cad.py                 # solo las que faltan
    <venv>/Scripts/python miniaturas_cad.py --pieza 3212    # rehace una
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import datos

sys.path.insert(0, str(datos.REPO / "backend"))

ANCHO, ALTO = 420, 298
MAX_SEGUNDOS = 900
PROCESOS = 3


def captura(codigo: str, destino: Path) -> None:
    """Dibuja la pieza en isométrica. Si tiene varios STEP (3288: base y tapa), uno al lado del otro."""
    import pyvista as pv
    from app.preview_converter import step_mesh
    from PIL import Image

    plotter = pv.Plotter(off_screen=True, window_size=(ANCHO * 2, ALTO * 2))
    plotter.set_background("white")
    desplazamiento, eje = 0.0, None
    for fila in datos.cad_de(codigo):
        local, motivo = datos.estado_onedrive(fila["ruta"])
        if not local:
            raise RuntimeError(f"{fila['nombre']}: {motivo}")
        malla = step_mesh(Path(datos.original(fila["ruta"])))
        if eje is None:  # la medida intermedia: por el grosor se taparían y por el largo saldrían diminutas
            eje = sorted(range(3), key=lambda i: malla.extents[i])[1]
        movimiento = [0.0, 0.0, 0.0]
        movimiento[eje] = desplazamiento - malla.bounds[0][eje]
        desplazamiento += malla.extents[eje] * 1.15
        malla.apply_translation(movimiento)
        plotter.add_mesh(pv.PolyData.from_regular_faces(malla.vertices, malla.faces), color="#aeb6c4")
    plotter.view_isometric()
    plotter.enable_parallel_projection()
    plotter.reset_camera()
    imagen = Image.fromarray(plotter.screenshot(return_img=True))
    plotter.close()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    imagen.resize((ANCHO, ALTO), Image.LANCZOS).save(temporal, "JPEG", quality=80)
    temporal.replace(destino)


def en_su_proceso(codigo: str) -> tuple[str, str]:
    """Cada pieza en un proceso aparte: el lector nativo puede romperse o colgarse con un STEP raro."""
    inicio = time.time()
    try:
        r = subprocess.run([sys.executable, __file__, "--una", codigo], capture_output=True, text=True, timeout=MAX_SEGUNDOS)
    except subprocess.TimeoutExpired:
        return codigo, f"sin terminar tras {MAX_SEGUNDOS} s"
    if r.returncode:
        return codigo, f"error: {(r.stderr or 'sin detalle').strip().splitlines()[-1]}"
    return codigo, f"ok en {time.time() - inicio:.0f} s"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pieza", help="rehace solo esta pieza")
    parser.add_argument("--una", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.una:
        return captura(args.una, datos.MINIATURAS / f"{args.una}.jpg")
    codigos = [args.pieza] if args.pieza else [
        p["codigo"] for p in datos.piezas() if p["cad"] and not (datos.MINIATURAS / f"{p['codigo']}.jpg").is_file()]
    with ThreadPoolExecutor(PROCESOS) as hilos:
        for codigo, resultado in hilos.map(en_su_proceso, codigos):
            print(codigo, resultado, flush=True)


if __name__ == "__main__":
    main()
