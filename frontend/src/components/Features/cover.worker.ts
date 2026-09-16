import occtimportjs from "occt-import-js"
import wasmUrl from "occt-import-js/dist/occt-import-js.wasm?url"

import { sha256 } from "./cadCover"
import type { CoverMesh, CoverWorkerResult } from "./coverGeometry"

self.onmessage = async ({ data }: MessageEvent<ArrayBuffer>) => {
  try {
    const occt = await occtimportjs({ locateFile: () => wasmUrl })
    const result = occt.ReadStepFile(new Uint8Array(data), null)
    if (!result.success || !result.meshes.length)
      throw new Error("OpenCascade no ha podido leer la geometría del fichero.")

    const meshes: CoverMesh[] = result.meshes.map((mesh) => ({
      positions: Float32Array.from(mesh.attributes.position.array),
      normals: mesh.attributes.normal
        ? Float32Array.from(mesh.attributes.normal.array)
        : undefined,
      indices: Uint32Array.from(mesh.index.array),
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
    const transfer = meshes.flatMap((mesh) => [
      mesh.positions.buffer,
      mesh.indices.buffer,
      ...(mesh.normals ? [mesh.normals.buffer] : []),
    ])
    self.postMessage({ meshes, geometryKey } satisfies CoverWorkerResult, {
      transfer,
    })
  } catch (error) {
    self.postMessage({
      error:
        error instanceof Error
          ? error.message
          : "No se ha podido preparar el CAD.",
    } satisfies CoverWorkerResult)
  }
}
