import * as THREE from "three"
import { type FilePublic, FilesService } from "@/client"
import { MAX_COVER_STEP_SIZE, sha256 } from "@/components/Features/cadCover"
import { loadCoverGeometry } from "@/components/Features/coverGeometry"
import { createModelControls } from "@/components/Features/modelControls"
import { absoluteFileUrl } from "@/hooks/useFileAccess"

/** Reuse the STEP worker and the feature camera; render the complete, unmarked part. */
export async function capturePartCad(file: FilePublic, signal: AbortSignal) {
  if (file.size > MAX_COVER_STEP_SIZE)
    throw new Error("El STEP supera los 50 MB.")
  const access = await FilesService.createFileAccessUrl({ fileId: file.id })
  const response = await fetch(absoluteFileUrl(access.url), { signal })
  if (!response.ok) throw new Error("El CAD no está disponible.")
  const bytes = await response.arrayBuffer()
  const sourceHash = await sha256(bytes)
  const { meshes } = await loadCoverGeometry(bytes, signal)
  signal.throwIfAborted()
  const object = new THREE.Group()
  const material = new THREE.MeshPhongMaterial({
    color: 0xb8bdc6,
    side: THREE.DoubleSide,
  })
  const geometries: THREE.BufferGeometry[] = []
  let renderer: THREE.WebGLRenderer | undefined
  let controller: ReturnType<typeof createModelControls> | undefined
  try {
    for (const mesh of meshes) {
      const geometry = new THREE.BufferGeometry()
      geometries.push(geometry)
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(mesh.positions, 3),
      )
      geometry.setIndex(new THREE.BufferAttribute(mesh.indices, 1))
      if (mesh.normals)
        geometry.setAttribute(
          "normal",
          new THREE.BufferAttribute(mesh.normals, 3),
        )
      else geometry.computeVertexNormals()
      object.add(new THREE.Mesh(geometry, material))
    }
    const bounds = new THREE.Box3().setFromObject(object)
    if (bounds.isEmpty()) throw new Error("El STEP no contiene geometría.")
    const size = bounds.getSize(new THREE.Vector3()).length() || 1
    object.position.sub(bounds.getCenter(new THREE.Vector3()))
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf4f5f7)
    const light = new THREE.DirectionalLight(0xffffff, 1.6)
    scene.add(object, new THREE.HemisphereLight(0xffffff, 0x555566, 2.2), light)
    const camera = new THREE.PerspectiveCamera(45, 1, size / 1000, size * 20)
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(512, 512)
    controller = createModelControls(camera, renderer.domElement, size)
    camera.position.multiplyScalar(0.72)
    controller.controls.update()
    light.position.copy(camera.position)
    renderer.render(scene, camera)
    const image = await new Promise<Blob>((resolve, reject) =>
      renderer!.domElement.toBlob(
        (blob) =>
          blob
            ? resolve(blob)
            : reject(new Error("No se ha podido crear la portada.")),
        "image/png",
      ),
    )
    signal.throwIfAborted()
    return { image, sourceHash }
  } finally {
    controller?.dispose()
    for (const geometry of geometries) geometry.dispose()
    material.dispose()
    renderer?.dispose()
    renderer?.forceContextLoss()
  }
}
