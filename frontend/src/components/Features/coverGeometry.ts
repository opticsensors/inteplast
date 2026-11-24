export type CoverMesh = {
  positions: Float32Array
  normals?: Float32Array
  indices: Uint32Array
  edgeIndices?: Uint32Array
  faces: { first: number; last: number; color?: number[] | null }[]
}

export type CoverGeometry = { meshes: CoverMesh[]; geometryKey: string }
export type CoverWorkerResult = CoverGeometry | { error: string }

function parseStep(buffer: ArrayBuffer, signal: AbortSignal) {
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
      reject(new Error("No se ha podido preparar el CAD."))
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

// CPU geometry only. Each viewer owns and disposes its GPU resources and camera.
const byteLimit = 64 * 1024 * 1024
const recent = new Map<string, { geometry: CoverGeometry; bytes: number }>()
let retainedBytes = 0

function remember(hash: string, geometry: CoverGeometry) {
  const bytes = geometry.meshes.reduce(
    (sum, m) =>
      sum +
      m.positions.byteLength +
      m.indices.byteLength +
      (m.normals?.byteLength ?? 0) +
      (m.edgeIndices?.byteLength ?? 0) +
      m.faces.length * 128 +
      256,
    0,
  )
  if (bytes > byteLimit) return
  for (const [key, entry] of recent) {
    if (retainedBytes + bytes <= byteLimit && recent.size < 4) break
    recent.delete(key)
    retainedBytes -= entry.bytes
  }
  recent.set(hash, { geometry, bytes })
  retainedBytes += bytes
}

type Job = {
  controller: AbortController
  result: Promise<CoverGeometry>
  consumers: number
}
const pending = new Map<string, Job>()

/** Call only with the SHA-256 of the bytes just read through the file access API. */
export async function loadCoverGeometry(
  buffer: ArrayBuffer,
  hash: string,
  signal: AbortSignal,
) {
  signal.throwIfAborted()
  const hit = recent.get(hash)
  if (hit) {
    recent.delete(hash)
    recent.set(hash, hit)
    return hit.geometry
  }
  let job = pending.get(hash)
  if (!job) {
    const controller = new AbortController()
    const result = parseStep(buffer, controller.signal)
      .then((geometry) => {
        controller.signal.throwIfAborted()
        remember(hash, geometry)
        return geometry
      })
      .finally(() => {
        if (pending.get(hash)?.controller === controller) pending.delete(hash)
      })
    job = { controller, result, consumers: 0 }
    pending.set(hash, job)
  }
  const active = job
  active.consumers++
  return new Promise<CoverGeometry>((resolve, reject) => {
    const cancel = () => {
      if (--active.consumers === 0 && pending.get(hash) === active) {
        pending.delete(hash)
        active.controller.abort()
      }
      reject(signal.reason)
    }
    signal.addEventListener("abort", cancel, { once: true })
    active.result
      .then(resolve, reject)
      .finally(() => signal.removeEventListener("abort", cancel))
  })
}
