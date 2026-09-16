export type CoverMesh = {
  positions: Float32Array
  normals?: Float32Array
  indices: Uint32Array
  faces: { first: number; last: number; color?: number[] | null }[]
}

export type CoverGeometry = { meshes: CoverMesh[]; geometryKey: string }
export type CoverWorkerResult = CoverGeometry | { error: string }

/** One cancellable worker per opening; no STEP parsing on the UI thread. */
export function loadCoverGeometry(buffer: ArrayBuffer, signal: AbortSignal) {
  return new Promise<CoverGeometry>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Carga cancelada", "AbortError"))
      return
    }
    const worker = new Worker(new URL("./cover.worker.ts", import.meta.url), {
      type: "module",
    })
    const dispose = () => {
      signal.removeEventListener("abort", cancel)
      worker.terminate()
    }
    const cancel = () => {
      dispose()
      reject(new DOMException("Carga cancelada", "AbortError"))
    }
    signal.addEventListener("abort", cancel, { once: true })
    worker.onmessage = ({ data }: MessageEvent<CoverWorkerResult>) => {
      dispose()
      if ("error" in data) reject(new Error(data.error))
      else resolve(data)
    }
    worker.onerror = (event) => {
      event.preventDefault()
      dispose()
      reject(new Error("No se ha podido preparar la pieza CAD."))
    }
    worker.onmessageerror = () => {
      dispose()
      reject(new Error("No se ha podido recibir la geometría del CAD."))
    }
    try {
      worker.postMessage(buffer, [buffer])
    } catch (error) {
      dispose()
      reject(error)
    }
  })
}
