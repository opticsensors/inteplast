import { FilesService } from "@/client"
import { absoluteFileUrl, fetchPreparedPreview } from "@/hooks/useFileAccess"
import { COVER_RECIPE, sha256 } from "./cadCover"
import { type CoverMesh, loadCoverGeometry } from "./coverGeometry"

interface Primitive {
  mode: number
  attributes: { POSITION: number; NORMAL?: number }
  indices: number
}
interface CoverGlb {
  extras: { coverRecipe: string; sourceHash: string; geometryKey: string }
  meshes: { primitives: Primitive[]; extras: { faces: CoverMesh["faces"] } }[]
  accessors: {
    bufferView: number
    componentType: number
    type: string
    count: number
  }[]
  bufferViews: { byteOffset: number; byteLength: number }[]
}

/** Read our packed GLB directly into Three.js buffers. Both producers use cover-v1. */
export function decodeCoverGlb(buffer: ArrayBuffer) {
  const header = new DataView(buffer)
  const jsonLength = header.getUint32(12, true)
  const bin = 28 + jsonLength
  if (
    header.getUint32(0, true) !== 0x46546c67 ||
    header.getUint32(4, true) !== 2 ||
    header.getUint32(8, true) !== buffer.byteLength ||
    header.getUint32(16, true) !== 0x4e4f534a ||
    header.getUint32(bin - 4, true) !== 0x004e4942
  )
    throw new Error("Formato de vista 3D no válido.")
  const model: CoverGlb = JSON.parse(
    new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLength)),
  )
  // A native preview (e.g. an older server) has no selectable face topology.
  if (!model.extras?.coverRecipe) return null
  if (
    model.extras.coverRecipe !== COVER_RECIPE ||
    !model.meshes?.length ||
    ![model.extras.sourceHash, model.extras.geometryKey].every((hash) =>
      /^[a-f0-9]{64}$/.test(hash),
    )
  )
    throw new Error("La vista preparada no contiene la selección CAD.")
  function range(index: number, vectors: boolean) {
    const a = model.accessors[index],
      view = model.bufferViews[a.bufferView]
    const count = a.count * (vectors ? 3 : 1)
    if (
      a.componentType !== (vectors ? 5126 : 5125) ||
      a.type !== (vectors ? "VEC3" : "SCALAR") ||
      view.byteLength !== count * 4 ||
      view.byteOffset < 0 ||
      !Number.isSafeInteger(count)
    )
      throw new Error("Datos de geometría no válidos.")
    return [bin + view.byteOffset, count] as const
  }
  const vector = (i: number) => new Float32Array(buffer, ...range(i, true))
  const indices = (i: number) => new Uint32Array(buffer, ...range(i, false))
  const meshes = model.meshes.map((mesh) => {
    const [surface, lines] = mesh.primitives
    if (
      surface.mode !== 4 ||
      (lines && lines.mode !== 1) ||
      !Array.isArray(mesh.extras.faces)
    )
      throw new Error("La vista preparada no contiene caras CAD.")
    return {
      positions: vector(surface.attributes.POSITION),
      normals:
        surface.attributes.NORMAL == null
          ? undefined
          : vector(surface.attributes.NORMAL),
      indices: indices(surface.indices),
      edgeIndices: lines ? indices(lines.indices) : undefined,
      faces: mesh.extras.faces,
    }
  })
  return {
    meshes,
    geometryKey: model.extras.geometryKey,
    sourceHash: model.extras.sourceHash,
  }
}

function waitForWorker(signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    signal.throwIfAborted()
    const cancel = () => {
      clearTimeout(timer)
      reject(signal.reason)
    }
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", cancel)
      resolve()
    }, 1000)
    signal.addEventListener("abort", cancel, { once: true })
  })
}

async function prepareGlb(fileId: string, signal: AbortSignal) {
  const deadline = performance.now() + 60000
  do {
    signal.throwIfAborted()
    const status = await FilesService.preparePreview({ fileId })
    signal.throwIfAborted()
    if (status.state === "ready" && status.url)
      return fetchPreparedPreview(fileId, signal, status.url)
    if (status.state !== "queued" && status.state !== "processing") break
    await waitForWorker(signal)
  } while (performance.now() < deadline)
}

export async function readCoverGeometry(
  fileId: string,
  signal: AbortSignal,
  checkSource?: (hash: string) => void,
) {
  // A prepared file needs only one authorized revalidation. A 409 queues a new version.
  let glb = await fetchPreparedPreview(fileId, signal)
  if (!glb || glb.status === 409) glb = await prepareGlb(fileId, signal)
  if (glb) {
    if (!glb.ok)
      throw new Error(
        "El CAD no está disponible. Comprueba el acceso al original.",
      )
    const geometry = decodeCoverGlb(await glb.arrayBuffer())
    signal.throwIfAborted()
    if (geometry) {
      checkSource?.(geometry.sourceHash)
      return geometry
    }
  }

  // Keep the exact local importer for a failed conversion or an unavailable worker.
  const access = await FilesService.createFileAccessUrl({ fileId })
  const response = await fetch(absoluteFileUrl(access.url), { signal })
  if (!response.ok)
    throw new Error(
      "El CAD no está disponible. Revisa su vínculo en Piezas ejemplo.",
    )
  const bytes = await response.arrayBuffer()
  const sourceHash = await sha256(bytes)
  signal.throwIfAborted()
  checkSource?.(sourceHash)
  return { ...(await loadCoverGeometry(bytes, sourceHash, signal)), sourceHash }
}
