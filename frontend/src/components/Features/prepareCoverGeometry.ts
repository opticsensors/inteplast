import type { OcctResult } from "occt-import-js"
import { sha256 } from "./cadCover"
import { cadBoundaryIndices } from "./coverFaceRanges"
import type { CoverMesh } from "./coverGeometry"

/** Keep the server GLB and saved browser selections on the same tessellation recipe. */
export async function prepareCoverGeometry(result: OcctResult) {
  if (!result.success || !result.meshes.length)
    throw new Error("OpenCascade no ha podido leer la geometría del fichero.")

  const meshes: CoverMesh[] = result.meshes.map((mesh) => ({
    positions: Float32Array.from(mesh.attributes.position.array),
    normals: mesh.attributes.normal
      ? Float32Array.from(mesh.attributes.normal.array)
      : undefined,
    indices: Uint32Array.from(mesh.index.array),
    edgeIndices: cadBoundaryIndices(
      mesh.index.array,
      mesh.attributes.position.array.length / 3,
      mesh.brep_faces ?? [],
    ),
    faces: mesh.brep_faces ?? [],
  }))
  // Preserve the existing cover-v1 fingerprint exactly, including float32
  // rounding and property order. Moving the work must not invalidate covers.
  const geometryKey = await sha256(
    new TextEncoder().encode(
      JSON.stringify(
        meshes.map((mesh) => ({
          positions: Array.from(mesh.positions),
          indices: Array.from(mesh.indices),
          faces: mesh.faces,
        })),
      ),
    ).buffer,
  )
  return { meshes, geometryKey }
}
