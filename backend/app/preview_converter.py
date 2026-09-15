"""Isolated native converter. Only the worker invokes this module, never a URL.

GLB is a visual approximation, not geometry for dimensional inspection. Original
coordinates are retained (STEP imported in mm; STL has no declared unit).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

RECIPE = "glb-v8-occt7.9-weld-300k-stl-1m-step-limit"
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 25 * 1024 * 1024
EXTENSIONS = {".stl", ".step", ".stp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def step_mesh(path: Path) -> Any:
    import numpy as np
    import trimesh
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    reader = STEPControl_Reader()
    # Initialize the STEP controller before setting its parameters. Prefer the
    # 3D edge curves and rebuild inconsistent surface curves during transfer;
    # manufacturing assemblies can otherwise import with unmeshable faces.
    if not (
        Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
        and Interface_Static.SetIVal_s("read.surfacecurve.mode", 3)
        and Interface_Static.SetIVal_s("read.stdsameparameter.mode", 1)
    ):
        raise ValueError("Could not configure STEP import")
    if reader.ReadFile(str(path)) != IFSelect_RetDone or not reader.TransferRoots():
        raise ValueError("STEP import failed")
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError("Empty STEP")
    mesher = BRepMesh_IncrementalMesh(shape, 0.1, False, 0.35, False)
    if not mesher.IsDone():
        raise ValueError("STEP tessellation failed")
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    vertices, faces = [], []
    offset = 0
    retried, repaired = 0, 0
    face_index = 0
    incomplete_faces: list[int] = []

    def triangulation(face: Any) -> tuple[Any, Any]:
        location = TopLoc_Location()
        return BRep_Tool.Triangulation_s(face, location), location

    def present(poly: Any) -> bool:
        return poly is not None and poly.NbTriangles() > 0

    while explorer.More():
        face_index += 1
        face = TopoDS.Face_s(explorer.Current())
        poly, location = triangulation(face)
        if not present(poly):
            retried += 1
            BRepMesh_IncrementalMesh(face, 0.01, False, 0.2, False)
            poly, location = triangulation(face)
        pieces = [(face, poly, location)]
        if not present(poly):
            # Fix the face together with its edges/vertices in memory. Face-only
            # healing misses inconsistent edge geometry in real STEP assemblies.
            # Retain every resulting face if healing splits the surface.
            # Imported instances can share topology/curves. Healing an isolated
            # geometry copy avoids changing siblings or reusing their mesh state.
            pieces = []
            for fix_seams in (True, False):
                try:
                    isolated = BRepBuilderAPI_Copy(face, True, False).Shape()
                    fixer = ShapeFix_Shape(isolated)
                    fixer.SetPrecision(1e-6)
                    fixer.SetMaxTolerance(0.01)
                    # Some imported offset surfaces have inconsistent parameter
                    # bounds: the seam repair itself can throw. Retry a fresh
                    # copy without it, retaining other edge/wire repairs.
                    if not fix_seams:
                        fixer.FixFaceTool().FixMissingSeamMode = 0
                    fixer.Perform()
                    fixed = fixer.Shape()
                    BRepMesh_IncrementalMesh(fixed, 0.01, False, 0.2, False)
                    parts = TopExp_Explorer(fixed, TopAbs_FACE)
                    candidate = []
                    while parts.More():
                        part = TopoDS.Face_s(parts.Current())
                        candidate.append((part, *triangulation(part)))
                        parts.Next()
                    pieces = candidate
                    if pieces and all(present(piece[1]) for piece in pieces):
                        break
                except Exception:
                    continue
            repaired += 1
        if not pieces or any(not present(part[1]) for part in pieces):
            incomplete_faces.append(face_index)
        for part, poly, location in pieces:
            if not present(poly):
                continue
            transform = location.Transformation()
            points = np.empty((poly.NbNodes(), 3), dtype=np.float64)
            for i in range(poly.NbNodes()):
                point = poly.Node(i + 1).Transformed(transform)
                points[i] = (point.X(), point.Y(), point.Z())
            indices = np.array(
                [poly.Triangle(i + 1).Get() for i in range(poly.NbTriangles())],
                dtype=np.int64,
            )
            if part.Orientation() == TopAbs_REVERSED:
                indices = indices[:, [0, 2, 1]]
            vertices.append(points)
            faces.append(indices + offset - 1)
            offset += len(points)
        explorer.Next()
    if not faces:
        raise ValueError("No STEP faces")
    # Permit an explicitly labelled partial view only for a small number of
    # problematic faces. This is a count limit, not an area/accuracy guarantee.
    if len(incomplete_faces) > face_index * 0.01:
        raise ValueError("More than 1% of STEP faces could not be tessellated")
    return trimesh.Trimesh(
        vertices=np.concatenate(vertices),
        faces=np.concatenate(faces),
        process=False,
        metadata={
            "step_faces": face_index,
            "step_retried_faces": retried,
            "step_repaired_faces": repaired,
            "step_incomplete_faces": incomplete_faces,
        },
    )


def convert(source: Path, extension: str, output: Path) -> dict[str, Any]:
    import numpy as np
    import trimesh

    if extension not in EXTENSIONS or source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Unsupported preview input")
    before = source.stat()
    digest = sha256(source)
    mesh = (
        trimesh.load_mesh(source, file_type="stl", process=True)
        if extension == ".stl"
        else step_mesh(source)
    )
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError("Invalid or empty geometry")
    if extension != ".stl":
        # OCCT returns a separate vertex array for every CAD face. Weld shared
        # positions before decimation, or the reducer treats each surface as
        # disconnected and can collapse whole planar faces, opening large holes.
        mesh.merge_vertices(digits_vertex=8)
    bounds = mesh.bounds.copy()
    step_metadata = {
        key: value for key, value in mesh.metadata.items() if key.startswith("step_")
    }
    original_triangles = len(mesh.faces)
    target = 300_000 if extension == ".stl" else 500_000
    if original_triangles > target:
        mesh = mesh.simplify_quadric_decimation(face_count=target, aggression=7)
    # Assemblies can reach a topology-preserving floor above the target. Allow
    # up to 1M STEP triangles while retaining the independent 25 MiB byte cap.
    maximum = 330_000 if extension == ".stl" else 1_000_000
    if not len(mesh.faces) or len(mesh.faces) > maximum:
        raise ValueError(
            f"Could not reach web geometry budget: {len(mesh.faces)} triangles"
        )
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Invalid simplified geometry")
    # Catch gross losses, not a metrology guarantee. Small surface details can change.
    if not np.allclose(mesh.bounds, bounds, atol=max(np.ptp(bounds, axis=0)) * 0.01):
        raise ValueError("Simplification changed the overall bounds")
    # Trimesh's no-SciPy normal fallback scans every face for each vertex, which
    # takes minutes even after decimation. Accumulate area-weighted normals in
    # linear time instead; no heavyweight sparse-matrix dependency is needed.
    points = mesh.vertices[mesh.faces]
    face_vectors = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    normals = np.zeros_like(mesh.vertices)
    for corner in range(3):
        np.add.at(normals, mesh.faces[:, corner], face_vectors)
    lengths = np.linalg.norm(normals, axis=1)
    np.divide(normals, lengths[:, None], out=normals, where=lengths[:, None] > 0)
    mesh.vertex_normals = normals  # type: ignore[method-assign]
    mesh.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[176, 183, 195, 255],
            metallicFactor=0.1,
            roughnessFactor=0.65,
            doubleSided=True,
        )
    )
    data = trimesh.exchange.gltf.export_glb(mesh.scene(), include_normals=True)
    if len(data) > MAX_OUTPUT_BYTES:
        raise ValueError("Preview exceeds web size budget")
    after = source.stat()
    if (before.st_mtime_ns, before.st_size) != (
        after.st_mtime_ns,
        after.st_size,
    ) or sha256(source) != digest:
        raise ValueError("Original changed during conversion")
    output.write_bytes(data)
    return {
        **step_metadata,
        "source_sha256": digest,
        "size": len(data),
        "triangles": len(mesh.faces),
        "source_triangles": original_triangles,
        "bounds": bounds.tolist(),
        "preview_bounds": mesh.bounds.tolist(),
        "recipe": RECIPE,
    }


def main() -> None:
    # Set before importing native libraries. Linux production worker is bounded;
    # direct Windows development relies on the parent timeout for cancellation.
    source, extension, output, memory_mb = sys.argv[1:]
    if sys.platform == "linux":
        import ctypes
        import os
        import resource
        import signal

        # Also stop a native job if its API worker is killed without cleanup.
        ctypes.CDLL(None).prctl(1, signal.SIGKILL)
        if os.getppid() == 1:
            raise InterruptedError("Parent worker exited")

        limit = int(memory_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    metadata = convert(Path(source), extension, Path(output))
    Path(output).with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")


if __name__ == "__main__":
    main()
