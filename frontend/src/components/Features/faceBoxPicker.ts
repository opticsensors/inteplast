import * as THREE from "three"
import type { coverFaceRanges } from "./coverFaceRanges"

type Ranges = ReturnType<typeof coverFaceRanges>
export type ViewBox = {
  left: number
  right: number
  top: number
  bottom: number
}

function faceIdGeometry(
  source: THREE.BufferGeometry,
  ranges: Ranges,
  firstId: number,
) {
  const index = source.getIndex()!
  const position = source.getAttribute("position")
  const triangleIds = new Uint32Array(index.count / 3)
  ranges.forEach(({ first, last }, i) => {
    triangleIds.fill(firstId + i, first, last + 1)
  })
  const owners = new Int32Array(position.count).fill(-1)
  let shared = false
  for (let i = 0; i < index.count; i++) {
    const vertex = index.array[i]
    const id = triangleIds[Math.floor(i / 3)]
    if (owners[vertex] >= 0 && owners[vertex] !== id) {
      shared = true
      break
    }
    owners[vertex] = id
  }
  // OCCT usually gives each face its own vertices. In that case both GPU
  // passes reuse the displayed position and index buffers, including on large STEP files.
  let geometry = new THREE.BufferGeometry()
  geometry.setAttribute("position", position)
  geometry.setIndex(index)
  if (shared) geometry = geometry.toNonIndexed()
  const colors = new Uint8Array(3 * geometry.getAttribute("position").count)
  for (let i = 0; i < colors.length / 3; i++) {
    const id = shared ? triangleIds[Math.floor(i / 3)] : owners[i]
    colors[3 * i] = id & 255
    colors[3 * i + 1] = (id >> 8) & 255
    colors[3 * i + 2] = id >> 16
  }
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3, true))
  geometry.addGroup(0, index.count, 0)
  geometry.addGroup(0, index.count, 1)
  return geometry
}

/** Depth-tested face IDs tell us what is visible. Testing all vertices of those
 * faces also excludes faces that continue outside the box behind another face. */
export function createFaceBoxPicker(
  renderer: THREE.WebGLRenderer,
  meshes: THREE.Mesh[],
  ranges: Ranges[],
) {
  if (ranges.reduce((sum, group) => sum + group.length, 0) > 0xffffff) {
    throw new Error("Demasiadas caras para seleccionar por área.")
  }
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0)
  const material = new THREE.MeshBasicMaterial({
    vertexColors: true,
    toneMapped: false,
    blending: THREE.NoBlending,
  })
  // Closed solids can have depth ties right on a silhouette. Prefer their
  // front surface there, while keeping the reverse of an open sheet selectable.
  const back = material.clone()
  back.side = THREE.BackSide
  back.polygonOffset = true
  back.polygonOffsetFactor = 1
  back.polygonOffsetUnits = 1
  const target = new THREE.WebGLRenderTarget(1, 1)
  const faces = [{ mesh: -1, first: 0, last: -1, faceIndex: -1 }]
  const pickMeshes = meshes.map((mesh, meshIndex) => {
    const geometry = faceIdGeometry(
      mesh.geometry,
      ranges[meshIndex],
      faces.length,
    )
    for (const range of ranges[meshIndex]) {
      faces.push({ mesh: meshIndex, ...range })
    }
    const pickMesh = new THREE.Mesh(geometry, [material, back])
    pickMesh.matrixAutoUpdate = false
    mesh.updateWorldMatrix(true, false)
    pickMesh.matrix.copy(mesh.matrixWorld)
    scene.add(pickMesh)
    return pickMesh
  })
  const transforms = meshes.map(() => new THREE.Matrix4())
  const projection = new THREE.Matrix4()
  let previous: THREE.Matrix4 | undefined
  let pixels = new Uint8Array(0)

  function prepareView(camera: THREE.Camera) {
    const { width, height } = renderer.domElement
    camera.updateMatrixWorld()
    projection.multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse,
    )
    if (
      !previous?.equals(projection) ||
      target.width !== width ||
      target.height !== height
    ) {
      target.setSize(width, height)
      const original = renderer.getRenderTarget()
      try {
        renderer.setRenderTarget(target)
        renderer.render(scene, camera)
      } finally {
        renderer.setRenderTarget(original)
      }
      previous = projection.clone()
      pickMeshes.forEach((mesh, i) => {
        transforms[i].multiplyMatrices(projection, mesh.matrix)
      })
    }
  }
  function select(camera: THREE.Camera, box: ViewBox): string[] {
    // box is a fraction of the viewport, with its origin at the top left.
    const { width, height } = renderer.domElement
    const x = Math.floor(box.left * width)
    const y = Math.floor((1 - box.bottom) * height)
    const w = Math.ceil(box.right * width) - x
    const h = Math.ceil((1 - box.top) * height) - y
    if (w <= 0 || h <= 0) return []
    prepareView(camera)
    if (pixels.length < w * h * 4) pixels = new Uint8Array(w * h * 4)
    renderer.readRenderTargetPixels(target, x, y, w, h, pixels)
    const seen = new Uint8Array(faces.length)
    const visible: number[] = []
    for (let i = 0; i < w * h * 4; i += 4) {
      const id = pixels[i] | (pixels[i + 1] << 8) | (pixels[i + 2] << 16)
      if (id && !seen[id]) {
        seen[id] = 1
        visible.push(id)
      }
    }
    const result: string[] = []
    const left = 2 * box.left - 1,
      right = 2 * box.right - 1
    const top = 1 - 2 * box.top,
      bottom = 1 - 2 * box.bottom
    for (const id of visible) {
      const { mesh, first, last, faceIndex } = faces[id]
      const m = transforms[mesh].elements
      const geometry = meshes[mesh].geometry
      const p = geometry.getAttribute("position").array
      const index = geometry.getIndex()!.array
      let inside = true
      for (let corner = first * 3; corner < (last + 1) * 3; corner++) {
        const i = index[corner] * 3
        const vx = p[i],
          vy = p[i + 1],
          vz = p[i + 2]
        const cx = m[0] * vx + m[4] * vy + m[8] * vz + m[12]
        const cy = m[1] * vx + m[5] * vy + m[9] * vz + m[13]
        const cz = m[2] * vx + m[6] * vy + m[10] * vz + m[14]
        const cw = m[3] * vx + m[7] * vy + m[11] * vz + m[15]
        if (
          cw <= 0 ||
          cx < left * cw ||
          cx > right * cw ||
          cy < bottom * cw ||
          cy > top * cw ||
          Math.abs(cz) > cw
        ) {
          inside = false
          break
        }
      }
      if (inside) result.push(`${mesh}:${faceIndex}`)
    }
    return result
  }
  return {
    prepareView,
    select,
    dispose() {
      target.dispose()
      material.dispose()
      back.dispose()
      for (const mesh of pickMeshes) mesh.geometry.dispose()
    },
  }
}
