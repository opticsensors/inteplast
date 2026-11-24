import occtimportjs from "occt-import-js"
import wasmUrl from "occt-import-js/dist/occt-import-js.wasm?url"

import type { CoverWorkerResult } from "./coverGeometry"
import { prepareCoverGeometry } from "./prepareCoverGeometry"

self.onmessage = async ({ data }: MessageEvent<ArrayBuffer>) => {
  try {
    const occt = await occtimportjs({ locateFile: () => wasmUrl })
    const result = occt.ReadStepFile(new Uint8Array(data), null)
    const { meshes, geometryKey } = await prepareCoverGeometry(result)
    const transfer = meshes.flatMap((mesh) => [
      mesh.positions.buffer,
      mesh.indices.buffer,
      ...(mesh.edgeIndices ? [mesh.edgeIndices.buffer] : []),
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
