import * as THREE from "three"
import { createFaceBoxPicker } from "@/components/Features/faceBoxPicker"

// Orthographic view of overlapping patches. Face 0's visible pixels all lie
// inside the box, but its geometry continues behind face 1 and beyond the box.
export function overlappingPatches() {
  const positions = [],
    indices = [],
    ranges = []
  function patch(x1, x2, y1, y2, z, reverse = false) {
    const v = positions.length / 3,
      first = indices.length / 3
    positions.push(x1, y1, z, x2, y1, z, x2, y2, z, x1, y2, z)
    const corners = reverse ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3]
    indices.push(...corners.map((i) => v + i))
    ranges.push({ first, last: first + 1, faceIndex: ranges.length })
  }
  patch(-0.8, 0.2, -0.1, 0.1, 0)
  patch(-1, -0.23, -0.4, 0.4, 0.2)
  patch(0.1, 0.18, 0.2, 0.28, 0)
  patch(0.1, 0.18, 0.2, 0.28, -0.2)
  patch(-0.4, -0.1, 0.16, 0.28, 0)
  patch(0.25, 0.4, -0.3, -0.2, 0, true)
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  )
  geometry.setIndex(indices)
  const mesh = new THREE.Mesh(geometry)
  const renderer = new THREE.WebGLRenderer()
  renderer.setPixelRatio(2)
  renderer.setSize(200, 150)
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10)
  camera.position.z = 5
  const picker = createFaceBoxPicker(renderer, [mesh], [ranges])
  try {
    return picker
      .select(camera, { left: 0.25, top: 0.25, right: 0.75, bottom: 0.75 })
      .sort()
  } finally {
    picker.dispose()
    geometry.dispose()
    mesh.material.dispose()
    renderer.dispose()
    renderer.forceContextLoss()
  }
}
