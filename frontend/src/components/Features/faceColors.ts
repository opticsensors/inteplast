import type { BufferGeometry } from "three"
import type { FaceLayer, FilePublic } from "@/client"
import { COVER_RECIPE } from "./cadCover"
import type { coverFaceRanges } from "./coverFaceRanges"
import type { CoverMesh } from "./coverGeometry"

export const SHARED_COLOR = "#333040"

export function compatibleLayers(
  layers: FaceLayer[],
  file: Pick<FilePublic, "id" | "version">,
  sourceHash: string,
  geometryKey: string,
  meshes: CoverMesh[],
) {
  return layers.filter(
    ({ selection: s }) =>
      s.file_id === file.id &&
      (s.file_version ?? null) === (file.version ?? null) &&
      s.source_sha256 === sourceHash &&
      s.geometry_key === geometryKey &&
      s.recipe === COVER_RECIPE &&
      s.faces.every(({ mesh, face }) => {
        const range = meshes[mesh]?.faces[face]
        return range && range.last >= range.first
      }),
  )
}

// Material zero is the grey CAD, one is shared, then one per feature.
export function coloredFaces(
  layers: FaceLayer[],
  hidden: ReadonlySet<string> = new Set(),
) {
  const faces = new Map<string, number>()
  let shared = false
  layers.forEach((layer, index) => {
    if (hidden.has(layer.feature_id)) return
    for (const face of layer.selection.faces) {
      const key = `${face.mesh}:${face.face}`
      if (faces.has(key)) {
        faces.set(key, 1)
        shared = true
      } else faces.set(key, index + 2)
    }
  })
  return { faces, shared }
}

export function paintFaceGroups(
  geometry: BufferGeometry,
  ranges: ReturnType<typeof coverFaceRanges>,
  color: (face: number) => number,
) {
  geometry.clearGroups()
  function append(start: number, count: number, material: number) {
    if (!count) return
    const last = geometry.groups[geometry.groups.length - 1]
    if (
      last &&
      last.materialIndex === material &&
      last.start + last.count === start
    )
      last.count += count
    else geometry.addGroup(start, count, material)
  }
  let next = 0
  for (const face of ranges) {
    append(next * 3, (face.first - next) * 3, 0)
    append(
      face.first * 3,
      (face.last - face.first + 1) * 3,
      color(face.faceIndex),
    )
    next = face.last + 1
  }
  append(next * 3, (geometry.index?.count ?? 0) - next * 3, 0)
}
