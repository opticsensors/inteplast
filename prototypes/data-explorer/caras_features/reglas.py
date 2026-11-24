"""Reglas geométricas que proponen las caras de cada feature (24/11/2026).

Cada regla traduce a geometría lo que dicen las cotas de
`conocimiento/cotas-por-feature.md` (diámetro del agujero, altura del nervio,
espesor de pared...). Son **propuestas del LLM sin validar**: la regla se
corrige aquí y se vuelve a ejecutar, no se retocan caras a mano en la app.
"""

from __future__ import annotations

import numpy as np

from caras import Cara, Modelo


def _verts(m: Modelo, c: Cara) -> np.ndarray:
    pos = m.positions[c.mesh]
    return pos[np.unique(m.triangles[c.mesh][c.first : c.last + 1])]


# --------------------------------------------------------------------------
# Agujeros y pines
# --------------------------------------------------------------------------


def agujeros(m: Modelo, radio: float, tol: float = 0.03, excluir_centro: float = 3.0) -> list[Cara]:
    """Cilindros cóncavos de ese radio, sin el agujero central de la pieza."""
    out = []
    for c in m.caras:
        if c.tipo != "cilindro" or c.convexa or abs(c.radio - radio) > tol:
            continue
        rel = m.centro - c.eje_punto
        rel -= (rel @ c.eje) * c.eje
        if np.linalg.norm(rel) < excluir_centro:
            continue
        out.append(c)
    return out


def _continuacion(m, semilla, origen, eje, radio, zmin, zmax):
    """Sigue aristas compartidas dentro del volumen del pin, incluidas sus tapas."""
    por_arista = {}
    centro = origen + eje * ((zmin + zmax) / 2)
    alcance = np.hypot(radio, (zmax - zmin) / 2)
    for c in m.caras:
        if c.key != semilla.key:
            if c.mesh != semilla.mesh or np.linalg.norm(c.centro - centro) > alcance:
                continue
            w = _verts(m, c) - origen
            z = w @ eje
            if z.min() < zmin or z.max() > zmax:
                continue
            if np.linalg.norm(w - np.outer(z, eje), axis=1).max() > radio:
                continue
        # Los dos lados de la costura OCCT pueden usar índices de vértice distintos.
        tri = m.triangles[c.mesh][c.first : c.last + 1]
        edges = np.sort(np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
        edges, counts = np.unique(edges, axis=0, return_counts=True)
        for a, b in np.round(m.positions[c.mesh][edges[counts == 1]], 5):
            edge = tuple(sorted((tuple(a), tuple(b))))
            por_arista.setdefault(edge, set()).add(c.key)
    vecinos = {}
    for keys in por_arista.values():
        for k in keys:
            vecinos.setdefault(k, set()).update(keys)
    vistas, pendientes = {semilla.key}, [semilla.key]
    while pendientes:
        nuevas = vecinos.get(pendientes.pop(), set()) - vistas
        vistas.update(nuevas)
        pendientes.extend(nuevas)
    return [m.cara(*k) for k in sorted(vistas)]


def tapas(m: Modelo, cil: list[Cara]) -> list[Cara]:
    """Solo superficies unidas al extremo del pin, incluso si hay un chaflán."""
    out = {}
    for p in cil:
        z = (_verts(m, p) - p.eje_punto) @ p.eje
        for borde, signo in [(z.min(), -1), (z.max(), 1)]:
            extremo = p.eje_punto + borde * p.eje
            caras = _continuacion(m, p, extremo, signo * p.eje, p.radio + 0.02, -0.01, 0.75 * p.radio)
            for c in caras:
                if c.tipo == "plano" and c.normal @ (signo * p.eje) > 0.99:
                    out[c.key] = c
    return list(out.values())


def _arco(xy):
    if len(xy) < 5:
        return None
    media = xy.mean(0)
    puntos = xy - media
    ajuste = np.c_[2 * puntos, np.ones(len(xy))]
    x, y, _ = np.linalg.lstsq(ajuste, (puntos * puntos).sum(1), rcond=None)[0]
    centro = media + [x, y]
    delta = xy - centro
    radios = np.linalg.norm(delta, axis=1)
    angulos = np.sort(np.arctan2(delta[:, 1], delta[:, 0]))
    if np.ptp(radios) > 0.003 or np.diff(np.r_[angulos, angulos[0] + 2 * np.pi]).max() > 1.6 * np.pi:
        return None
    return centro, radios.mean()


def pines_con_desmoldeo(m: Modelo, radio: float, tol: float) -> list[Cara]:
    """Pin con salida sobre la cara principal y diámetro en tolerancia en ambos extremos."""
    eje = max((c for c in m.caras if c.tipo == "plano"), key=lambda c: c.area).normal
    u = np.cross(eje, [1, 0, 0] if abs(eje[0]) < 0.9 else [0, 1, 0])
    u /= np.linalg.norm(u)
    v = np.cross(eje, u)
    seleccion = {}
    for c in m.caras:
        if c.tipo == "plano" or c.key in seleccion:
            continue
        w = _verts(m, c)
        z = w @ eje
        if np.ptp(z) < radio:
            continue
        xy = np.c_[w @ u, w @ v]
        if np.ptp(xy, axis=0).max() > 2 * (radio + tol):
            continue
        a = _arco(xy[z <= z.min() + 0.001])
        b = _arco(xy[z >= z.max() - 0.001])
        if a is None or b is None or max(abs(a[1] - radio), abs(b[1] - radio)) > tol:
            continue
        if np.linalg.norm(a[0] - b[0]) > 0.01:
            continue
        centro = (a[0] + b[0]) / 2
        origen = centro[0] * u + centro[1] * v
        tri = m.positions[c.mesh][m.triangles[c.mesh][c.first : c.last + 1]]
        normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        rel = tri.mean(1) - origen
        if (normales * (rel - np.outer(rel @ eje, eje))).sum() <= 0:
            continue  # Orificio, con las normales hacia el eje.
        caras = _continuacion(m, c, origen, eje, 1.25 * radio, z.min() - radio, z.max() + radio)
        seleccion.update((cara.key, cara) for cara in caras)
    return list(seleccion.values())


def pines(m: Modelo, radio: float, tol: float = 0.03, area_min: float = 0.0) -> list[Cara]:
    cil = [
        c for c in m.caras
        if c.tipo == "cilindro" and c.convexa and abs(c.radio - radio) <= tol and c.area >= area_min
    ]
    return cil + tapas(m, cil)


# --------------------------------------------------------------------------
# Zonas (clips sin cota que dé una geometría medible)
# --------------------------------------------------------------------------


def extremos(m: Modelo, eje: int, frac: float, lados=(-1, 1)) -> list[Cara]:
    """Caras enteras dentro de la fracción `frac` de cada extremo del eje."""
    d = np.eye(3)[eje] if np.isscalar(eje) else np.asarray(eje, float) / np.linalg.norm(eje)
    proy = np.concatenate(m.positions) @ d
    lo, hi = proy.min(), proy.max()
    span = hi - lo
    out = []
    for c in m.caras:
        w = _verts(m, c) @ d
        if (-1 in lados and w.max() <= lo + frac * span) or (1 in lados and w.min() >= hi - frac * span):
            out.append(c)
    return out


def fuera_de_radio(m: Modelo, r: float, eje: int = 2, excluir=None) -> list[Cara]:
    """Caras enteras más allá del radio `r` del eje de la pieza (pestañas del borde)."""
    k = [i for i in range(3) if i != eje]
    out = []
    for c in m.caras:
        w = _verts(m, c) - m.centro
        if (np.hypot(w[:, k[0]], w[:, k[1]]) > r).all() and (excluir is None or not excluir(w)):
            out.append(c)
    return out


# --------------------------------------------------------------------------
# Nervios de soldadura (director de energía)
# --------------------------------------------------------------------------


def directores_energia(m: Modelo, angulo: float = 60.0, holgura: float = 0.12):
    """Nervio con flancos inclinados `angulo` respecto del plano base.

    Busca parejas de flancos planos simétricos (normal con componente vertical
    cos(90-angulo)), y toma todas las caras que caen dentro de la caja del
    nervio: paredes, flancos, cresta, extremos y acuerdos con la base.
    Devuelve (caras del nervio, altura de la base) .
    """
    nz = np.cos(np.radians(angulo))
    eje = np.array([0, 0, 1.0])
    # Eje de "arriba": el de la pieza más fina (los nervios salen de la cara grande).
    flancos = [c for c in m.caras if c.tipo == "plano" and abs(abs(c.normal @ eje) - nz) < 0.03]
    if not flancos:
        return [], None
    signo = np.sign(np.median([c.normal @ eje for c in flancos]))
    usados, grupos = set(), []
    for a in flancos:
        if a.key in usados:
            continue
        for b in flancos:
            if b.key in usados or b is a or abs(a.area - b.area) > 0.05 * a.area:
                continue
            ha, hb = a.normal - (a.normal @ eje) * eje, b.normal - (b.normal @ eje) * eje
            if ha @ hb / (np.linalg.norm(ha) * np.linalg.norm(hb)) > -0.98:
                continue
            if np.linalg.norm(a.centro - b.centro) > 2.0:
                continue
            usados |= {a.key, b.key}
            grupos.append((a, b))
            break
    sel: list[Cara] = []
    bases: list[float] = []
    for a, b in grupos:
        v = np.vstack([_verts(m, a), _verts(m, b)])
        xy = v[:, :2]
        mu = xy.mean(0)
        _, _, vt = np.linalg.svd(xy - mu, full_matrices=False)
        loc = (xy - mu) @ vt.T
        lo, hi = loc.min(0) - holgura, loc.max(0) + holgura
        lo[1] -= 0.25
        hi[1] += 0.25
        z0 = v[:, 2].min() if signo > 0 else v[:, 2].max()
        zlo, zhi = (z0 - 0.5, v[:, 2].max() + 0.05) if signo > 0 else (v[:, 2].min() - 0.05, z0 + 0.5)
        zbase = []
        for c in m.caras:
            w = _verts(m, c)
            q = (w[:, :2] - mu) @ vt.T
            if (q >= lo).all() and (q <= hi).all() and (w[:, 2] >= zlo).all() and (w[:, 2] <= zhi).all():
                sel.append(c)
                zbase.append(w[:, 2].min() if signo > 0 else w[:, 2].max())
        # La base es donde arranca el nervio (los acuerdos con el plano de apoyo).
        bases.append(min(zbase) if signo > 0 else max(zbase))
    return sel, (float(np.median(bases)) if bases else None)


def plano_apoyo(m: Modelo, z: float, tol: float = 0.15, area_min: float = 1.0) -> list[Cara]:
    """Caras planas horizontales a la altura `z` (en coordenadas del CAD)."""
    out = []
    for c in m.caras:
        if c.tipo != "plano" or abs(abs(c.normal[2]) - 1) > 2e-3 or c.area < area_min:
            continue
        w = _verts(m, c)
        if np.ptp(w[:, 2]) < 1e-3 and abs(w[0, 2] - z) <= tol:
            out.append(c)
    return out


# --------------------------------------------------------------------------
# Espesores (paredes delgadas, pockets)
# --------------------------------------------------------------------------


def espesores(m: Modelo, e: float, tol: float = 0.04, area_min: float = 0.3):
    """Parejas de caras opuestas separadas `e`: planos paralelos o cilindros coaxiales."""
    planos = [c for c in m.caras if c.tipo == "plano" and c.area >= area_min]
    cils = [c for c in m.caras if c.tipo == "cilindro" and c.area >= area_min]
    pares = []
    for i, a in enumerate(planos):
        for b in planos[i + 1 :]:
            if a.normal @ b.normal > -0.999:
                continue
            d = abs((b.centro - a.centro) @ a.normal)
            if abs(d - e) > tol:
                continue
            # Que se solapen al proyectar una sobre otra.
            u = np.cross(a.normal, [1, 0, 0] if abs(a.normal[0]) < 0.9 else [0, 1, 0])
            u /= np.linalg.norm(u)
            v = np.cross(a.normal, u)
            pa, pb = _verts(m, a), _verts(m, b)
            A = np.c_[pa @ u, pa @ v]
            B = np.c_[pb @ u, pb @ v]
            if (np.minimum(A.max(0), B.max(0)) - np.maximum(A.min(0), B.min(0)) > 0.2).all():
                # y que el material esté entre ellas (normales hacia fuera).
                if (b.centro - a.centro) @ a.normal < 0:
                    pares.append((a, b, d))
    for i, a in enumerate(cils):
        for b in cils[i + 1 :]:
            if abs(abs(a.eje @ b.eje) - 1) > 1e-3 or a.convexa == b.convexa:
                continue
            rel = b.eje_punto - a.eje_punto
            rel -= (rel @ a.eje) * a.eje
            if np.linalg.norm(rel) > 0.02:
                continue
            d = abs(a.radio - b.radio)
            if abs(d - e) > tol:
                continue
            ext, inn = (a, b) if a.radio > b.radio else (b, a)
            if ext.convexa and not inn.convexa:
                pares.append((a, b, d))
    return pares
