"""Caras CAD de cada feature: herramienta de exploración (24/11/2026).

Lee el GLB preparado por la app (`cover-v1`: triángulos + rangos de caras OCCT),
clasifica las caras (plano, cilindro con radio y eje, otras), las dibuja con la
misma convención de cámara que `StepCoverCanvas.tsx` (objeto centrado en su caja,
FOV 45°, Z arriba) y elige un encuadre donde se vean las caras marcadas.

Es una ayuda para que el LLM proponga caras; **no** es un lector de producción y
la app no la importa. Las selecciones que salgan de aquí son propuestas del LLM,
sin validar (ver README).
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True

GRIS = (0xB8, 0xBD, 0xC6)
ROJO = (0xE3, 0x26, 0x36)
FONDO = (0xF4, 0xF5, 0xF7)
LINEA = (0x30, 0x34, 0x3A)


@dataclass
class Cara:
    mesh: int
    face: int
    first: int
    last: int
    area: float = 0.0
    centro: np.ndarray = field(default_factory=lambda: np.zeros(3))
    normal: np.ndarray = field(default_factory=lambda: np.zeros(3))
    tipo: str = "?"  # plano | cilindro | otra
    radio: float | None = None
    eje: np.ndarray | None = None
    eje_punto: np.ndarray | None = None
    convexa: bool | None = None  # cilindro: True = pin/exterior, False = agujero
    bbox: tuple[np.ndarray, np.ndarray] | None = None

    @property
    def key(self) -> tuple[int, int]:
        return (self.mesh, self.face)


@dataclass
class Modelo:
    positions: list[np.ndarray]
    normals: list[np.ndarray | None]
    triangles: list[np.ndarray]
    edges: list[np.ndarray | None]
    caras: list[Cara]
    centro: np.ndarray
    diagonal: float
    geometry_key: str
    source_hash: str

    def cara(self, mesh: int, face: int) -> Cara:
        return self._index[(mesh, face)]

    def __post_init__(self) -> None:
        self._index = {c.key: c for c in self.caras}


def leer_glb(path: str | Path) -> Modelo:
    data = Path(path).read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20 : 20 + jlen])
    base = 28 + jlen

    def acc(i: int, vec: bool) -> np.ndarray:
        a = js["accessors"][i]
        v = js["bufferViews"][a["bufferView"]]
        arr = np.frombuffer(
            data,
            np.float32 if vec else np.uint32,
            count=a["count"] * (3 if vec else 1),
            offset=base + v["byteOffset"],
        )
        return arr.reshape(-1, 3).astype(np.float64) if vec else arr.astype(np.int64)

    positions, normals, triangles, edges, caras = [], [], [], [], []
    for mi, m in enumerate(js["meshes"]):
        surf = m["primitives"][0]
        pos = acc(surf["attributes"]["POSITION"], True)
        tri = acc(surf["indices"], False).reshape(-1, 3)
        lin = acc(m["primitives"][1]["indices"], False) if len(m["primitives"]) > 1 else None
        positions.append(pos)
        nrm = surf["attributes"].get("NORMAL")
        normals.append(acc(nrm, True) if nrm is not None else None)
        triangles.append(tri)
        edges.append(lin)
        for fi, f in enumerate(m["extras"]["faces"]):
            if f["last"] < f["first"]:
                continue
            caras.append(Cara(mi, fi, f["first"], f["last"]))
    allp = np.concatenate(positions)
    lo, hi = allp.min(0), allp.max(0)
    modelo = Modelo(
        positions,
        normals,
        triangles,
        edges,
        caras,
        (lo + hi) / 2,
        float(np.linalg.norm(hi - lo)) or 1.0,
        js["extras"]["geometryKey"],
        js["extras"]["sourceHash"],
    )
    for c in caras:
        _analizar(modelo, c)
    return modelo


def _analizar(m: Modelo, c: Cara) -> None:
    pos = m.positions[c.mesh]
    tri = m.triangles[c.mesh][c.first : c.last + 1]
    a, b, d = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    cr = np.cross(b - a, d - a)
    areas = np.linalg.norm(cr, axis=1) / 2
    c.area = float(areas.sum())
    w = areas / (c.area or 1)
    cen = (a + b + d) / 3
    c.centro = (cen * w[:, None]).sum(0)
    ok = areas > 1e-12
    n = np.zeros_like(cr)
    n[ok] = cr[ok] / (2 * areas[ok, None])
    mean = (n * w[:, None]).sum(0)
    c.normal = mean / (np.linalg.norm(mean) or 1)
    pts = pos[np.unique(tri)]
    c.bbox = (pts.min(0), pts.max(0))
    if not ok.any():
        c.tipo = "otra"
        return
    if (n[ok] @ c.normal).min() > 0.999:
        c.tipo = "plano"
        return
    # Cilindro: las normales son perpendiculares a un eje.
    cov = (n[ok, :, None] * n[ok, None, :] * w[ok, None, None]).sum(0)
    vals, vecs = np.linalg.eigh(cov)
    eje = vecs[:, 0]
    if np.abs(n[ok] @ eje).max() > 0.02 or len(pts) < 6:
        c.tipo = "otra"
        return
    # Círculo en el plano perpendicular al eje (ajuste algebraico).
    u = np.cross(eje, [1, 0, 0] if abs(eje[0]) < 0.9 else [0, 1, 0])
    u /= np.linalg.norm(u)
    v = np.cross(eje, u)
    x, y = pts @ u, pts @ v
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    sol, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    cx, cy = sol[0], sol[1]
    r = float(np.sqrt(max(sol[2] + cx * cx + cy * cy, 0)))
    resid = np.abs(np.hypot(x - cx, y - cy) - r)
    if r <= 0 or resid.max() > max(0.02 * r, 0.01):
        c.tipo = "otra"
        return
    c.tipo = "cilindro"
    c.radio = r
    c.eje = eje
    c.eje_punto = cx * u + cy * v + (pts @ eje).mean() * eje
    rel = cen - c.eje_punto
    rel -= np.outer(rel @ eje, eje)
    c.convexa = bool(((n * rel).sum(1) * w).sum() > 0)


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def _poly(m: Modelo, mi: int) -> pv.PolyData:
    tri = m.triangles[mi]
    faces = np.hstack([np.full((len(tri), 1), 3), tri]).ravel()
    poly = pv.PolyData(m.positions[mi] - m.centro, faces)
    if m.normals[mi] is not None:
        poly.point_data["Normals"] = m.normals[mi]
        poly.point_data.active_normals_name = "Normals"
    return poly


def camara_inicial(m: Modelo) -> dict:
    s = m.diagonal * 0.72
    return {"position": [s, -s, 0.8 * s], "target": [0.0, 0.0, 0.0], "up": [0.0, 0.0, 1.0]}


def _plotter(size: int) -> pv.Plotter:
    p = pv.Plotter(off_screen=True, window_size=(size, size), lighting=None)
    p.background_color = [c / 255 for c in FONDO]
    return p


def _poner_camara(p: pv.Plotter, cam: dict, m: Modelo) -> None:
    p.camera.position = tuple(cam["position"])
    p.camera.focal_point = tuple(cam["target"])
    p.camera.up = tuple(cam["up"])
    p.camera.view_angle = 45
    p.camera.clipping_range = (m.diagonal / 1000, m.diagonal * 20)


def colores_triangulos(m: Modelo, mi: int, colores: dict[tuple[int, int], tuple]) -> np.ndarray:
    rgb = np.tile(np.array(GRIS, np.uint8), (len(m.triangles[mi]), 1))
    for c in m.caras:
        if c.mesh == mi and c.key in colores:
            rgb[c.first : c.last + 1] = colores[c.key]
    return rgb


def render(
    m: Modelo,
    colores: dict[tuple[int, int], tuple],
    cam: dict,
    size: int = 526,
    etiquetas: dict[tuple[int, int], str] | None = None,
    aristas: bool = True,
) -> np.ndarray:
    """Imagen con el aspecto de la portada de la app (gris, rojo, aristas)."""
    p = _plotter(size)
    for mi in range(len(m.positions)):
        poly = _poly(m, mi)
        poly.cell_data["rgb"] = colores_triangulos(m, mi, colores)
        p.add_mesh(
            poly,
            scalars="rgb",
            rgb=True,
            smooth_shading=True,
            ambient=0.30,
            diffuse=0.70,
            specular=0.08,
            specular_power=30,
        )
        if aristas and m.edges[mi] is not None and len(m.edges[mi]):
            seg = m.edges[mi].reshape(-1, 2)
            lines = np.hstack([np.full((len(seg), 1), 2), seg]).ravel()
            p.add_mesh(
                pv.PolyData(m.positions[mi] - m.centro, lines=lines),
                color=[c / 255 for c in LINEA],
                line_width=1,
                lighting=False,
            )
    light = pv.Light(light_type="headlight", intensity=0.9)
    p.add_light(light)
    _poner_camara(p, cam, m)
    if etiquetas:
        pts = np.array([m.cara(*k).centro - m.centro for k in etiquetas])
        p.add_point_labels(
            pts,
            list(etiquetas.values()),
            font_size=11,
            point_size=4,
            shape_opacity=0.6,
            always_visible=True,
        )
    p.enable_anti_aliasing("ssaa")
    img = p.screenshot(return_img=True)
    p.close()
    return img


def _visor_ids(m: Modelo, size: int):
    """Colores enteros por cara, sin mezclar identificadores en los bordes."""
    p = pv.Plotter(off_screen=True, window_size=(size, size), lighting=None)
    p.render_window.SetMultiSamples(0)
    p.background_color = (0, 0, 0)
    for mi in range(len(m.positions)):
        ids = np.zeros(len(m.triangles[mi]), np.int64)
        for gi, c in enumerate(m.caras):
            if c.mesh == mi:
                ids[c.first : c.last + 1] = gi + 1
        rgb = np.stack([(ids >> 16) & 255, (ids >> 8) & 255, ids & 255], 1).astype(np.uint8)
        poly = _poly(m, mi)
        poly.cell_data["rgb"] = rgb
        p.add_mesh(poly, scalars="rgb", rgb=True, lighting=False)
    return p


def _mapa_ids(p, m, cam):
    _poner_camara(p, cam, m)
    p.render()
    rgb = p.screenshot(return_img=True).astype(np.int32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def ids_visibles(m: Modelo, cam: dict, size: int = 160) -> np.ndarray:
    """Índice de cara por píxel (+1; 0 = fondo)."""
    p = _visor_ids(m, size)
    try:
        p.show(auto_close=False, interactive=False)
        return _mapa_ids(p, m, cam)
    finally:
        p.close()


def _direcciones(n: int = 48) -> np.ndarray:
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5**0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


def _up(d: np.ndarray) -> list[float]:
    return [0.0, 0.0, 1.0] if abs(d[2]) < 0.95 else [0.0, 1.0, 0.0]


def encuadre(
    m: Modelo,
    sel: list[tuple[int, int]],
    zoom: float = 1.0,
    dirs: np.ndarray | None = None,
) -> tuple[dict, float]:
    """Cámara que enseña la mayor parte de las caras marcadas.

    Prueba direcciones, cuenta caras marcadas visibles y su área en pantalla,
    y encuadra la caja de las caras marcadas (como mínimo una fracción de la
    pieza, para que se entienda dónde están). Devuelve cámara y fracción de
    caras marcadas visibles.
    """
    gidx = {c.key: i + 1 for i, c in enumerate(m.caras)}
    selg = np.array([gidx[k] for k in sel])
    pts = np.array([m.cara(*k).centro for k in sel]) - m.centro
    lo = np.min([m.cara(*k).bbox[0] for k in sel], 0) - m.centro
    hi = np.max([m.cara(*k).bbox[1] for k in sel], 0) - m.centro
    target = (lo + hi) / 2
    extent = max(np.linalg.norm(hi - lo), 0.7 * m.diagonal / zoom)
    dist = extent * 0.5 / np.tan(np.radians(22.5)) * 1.15
    direcciones = _direcciones() if dirs is None else dirs
    p = _visor_ids(m, 192)
    # Evitar que un primer plano coloque la cámara dentro o pegada al sólido.
    limites = np.concatenate(m.positions)
    caja = np.array(list(product(*zip(limites.min(0), limites.max(0))))) - m.centro

    def buscar(objetivo, distancia):
        best = None
        for d in direcciones:
            frontal = ((caja - objetivo) @ d).max() + 0.12 * m.diagonal
            cam = {"position": list(objetivo + d * max(distancia, frontal)), "target": list(objetivo), "up": _up(d)}
            ids = _mapa_ids(p, m, cam)
            vis = np.isin(ids, selg)
            fraccion = len(np.unique(ids[vis])) / len(selg)
            area = vis.mean()
            score = fraccion + 3 * np.sqrt(area) + 0.025 * d[2]
            if best is None or score > best[0]:
                best = (score, cam, fraccion, area)
        return best

    try:
        p.show(auto_close=False, interactive=False)
        best = buscar(target, dist)
        if best[3] < 0.0015:
            # Un pin puede estar técnicamente visible y ocupar un solo píxel.
            # Probar el grupo más denso y un segundo grupo separado, sin cambiar las caras.
            radio = 0.12 * m.diagonal
            densidad = [np.count_nonzero(np.linalg.norm(pts - pt, axis=1) <= radio) for pt in pts]
            disponibles = np.ones(len(pts), dtype=bool)
            for _ in range(2):
                if not disponibles.any():
                    break
                centro = pts[np.argmax(np.where(disponibles, densidad, -1))]
                cerca = np.linalg.norm(pts - centro, axis=1) <= radio
                detalle = buscar(pts[cerca].mean(0), min(dist, 0.32 * m.diagonal))
                if detalle[3] > best[3] * 2 and detalle[2] > 0:
                    best = detalle
                disponibles &= ~cerca
        return best[1], best[2]
    finally:
        p.close()


def guardar_png(img: np.ndarray, path: str | Path) -> None:
    from PIL import Image

    Image.fromarray(img).save(path)


def resumen(m: Modelo, filtro=None, orden="area", n=60) -> list[str]:
    caras = [c for c in m.caras if filtro is None or filtro(c)]
    caras.sort(key=lambda c: -c.area if orden == "area" else (c.radio or 0))
    out = []
    for c in caras[:n]:
        cc = c.centro - m.centro
        extra = ""
        if c.tipo == "cilindro":
            extra = f" R={c.radio:.3f} eje=({c.eje[0]:+.2f},{c.eje[1]:+.2f},{c.eje[2]:+.2f}) {'pin' if c.convexa else 'agujero'} h={np.ptp((np.array(c.bbox)-m.centro)@c.eje):.2f}"
        elif c.tipo == "plano":
            extra = f" n=({c.normal[0]:+.2f},{c.normal[1]:+.2f},{c.normal[2]:+.2f})"
        out.append(
            f"{c.mesh}:{c.face} {c.tipo:8s} A={c.area:9.2f} c=({cc[0]:+7.2f},{cc[1]:+7.2f},{cc[2]:+7.2f}){extra}"
        )
    return out


def vista(m: Modelo, d, zoom: float = 1.0, target=None) -> dict:
    """Cámara mirando desde la dirección `d` (desde el objetivo hacia la cámara)."""
    d = np.asarray(d, float)
    d /= np.linalg.norm(d)
    t = np.zeros(3) if target is None else np.asarray(target, float)
    dist = m.diagonal * 0.5 / np.tan(np.radians(22.5)) * 1.1 / zoom
    return {"position": list(t + d * dist), "target": list(t), "up": _up(d)}


VISTAS4 = [(1, -1, 0.8), (-1, 1, 0.8), (0.001, -0.001, 1), (0.001, -0.001, -1)]


def eje_fino(m: Modelo) -> int:
    lo = np.min([c.bbox[0] for c in m.caras], 0)
    hi = np.max([c.bbox[1] for c in m.caras], 0)
    return int(np.argmin(hi - lo))


def vistas_auto(m: Modelo) -> list:
    """Dos isométricas y dos frontales según el eje más fino de la pieza."""
    k = eje_fino(m)
    if k == 2:
        return VISTAS4
    e = np.zeros(3)
    e[k] = 1
    o = np.array([1.0, -1.0, 0.0]) if k == 2 else np.array([0, 0, 1.0])
    o[k] = 0
    return [list(e * 0.8 + o * 0.6 + [0.3, 0.3, 0.3] * (1 - e)), list(-e * 0.8 + o * 0.6 - [0.3, 0.3, 0.3] * (1 - e)), list(e + 0.001), list(-e + 0.001)]


def mosaico(m: Modelo, colores, dirs=None, size=400, etiquetas=None, zoom=1.0, target=None):
    dirs = vistas_auto(m) if dirs is None else dirs
    imgs = [render(m, colores, vista(m, d, zoom, target), size, etiquetas) for d in dirs]
    while len(imgs) % 2:
        imgs.append(np.full_like(imgs[0], 255))
    filas = [np.concatenate(imgs[i : i + 2], 1) for i in range(0, len(imgs), 2)]
    return np.concatenate(filas, 0)


def cilindros(m: Modelo, dec: int = 2) -> list[str]:
    """Histograma de cilindros por radio: n caras, agujero/pin, área total."""
    from collections import defaultdict

    g = defaultdict(list)
    for c in m.caras:
        if c.tipo == "cilindro":
            g[(round(c.radio, dec), c.convexa)].append(c)
    out = []
    for (r, cv), cs in sorted(g.items()):
        out.append(
            f"R={r:<7} {'pin ' if cv else 'aguj'} n={len(cs):3d} A={sum(c.area for c in cs):8.1f} "
            + " ".join(f"{c.mesh}:{c.face}" for c in cs[:12])
        )
    return out


PALETA = [
    (230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48), (145, 30, 180),
    (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128),
    (220, 190, 255), (170, 110, 40), (255, 225, 25), (128, 0, 0), (0, 0, 128),
]


def zona(m: Modelo, punto, radio: float, dirs, size=450, max_caras=40, path=None, filtro=None):
    """Caras dentro de una esfera (coordenadas centradas), de colores y numeradas."""
    p = np.asarray(punto, float)
    cs = [
        c for c in m.caras
        if np.linalg.norm(c.centro - m.centro - p) < radio and (filtro is None or filtro(c))
    ]
    cs.sort(key=lambda c: -c.area)
    cs = cs[:max_caras]
    col = {c.key: PALETA[i % len(PALETA)] for i, c in enumerate(cs)}
    lab = {c.key: str(c.face) for c in cs}
    imgs = []
    for d in dirs:
        d = np.asarray(d, float)
        d /= np.linalg.norm(d)
        dist = radio * 1.3 / np.tan(np.radians(22.5))
        cam = {"position": list(p + d * dist), "target": list(p), "up": _up(d)}
        imgs.append(render(m, col, cam, size, lab))
    img = np.concatenate(imgs, 1)
    if path:
        guardar_png(img, path)
    return [c.face for c in cs]
