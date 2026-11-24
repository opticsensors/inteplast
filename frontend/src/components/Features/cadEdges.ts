import {
  BufferAttribute,
  BufferGeometry,
  EdgesGeometry,
  LineBasicMaterial,
  LineSegments,
  type Mesh,
} from "three"

function faceBoundaries(geometry: BufferGeometry, segments?: Uint32Array) {
  if (!segments) return new EdgesGeometry(geometry, 30)
  const outline = new BufferGeometry()
  outline.setAttribute("position", geometry.getAttribute("position"))
  outline.setIndex(new BufferAttribute(segments, 1))
  return outline
}

export function offsetCadSurface(mesh: Mesh) {
  const materials = Array.isArray(mesh.material)
    ? mesh.material
    : [mesh.material]
  for (const material of materials) {
    material.polygonOffset = true
    material.polygonOffsetFactor = 1
    material.polygonOffsetUnits = 1
  }
}

export const cadLineColor = 0x30343a

export function addCadEdges(mesh: Mesh, segments?: Uint32Array) {
  offsetCadSurface(mesh)
  const lines = new LineSegments(
    faceBoundaries(mesh.geometry, segments),
    new LineBasicMaterial({
      color: cadLineColor,
      depthWrite: false,
      toneMapped: false,
    }),
  )
  lines.renderOrder = 1
  mesh.add(lines)
  return lines
}
