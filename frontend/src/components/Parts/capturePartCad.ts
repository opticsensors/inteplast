import * as THREE from "three"
import type { FaceLayer, FilePublic } from "@/client"
import { MAX_COVER_STEP_SIZE } from "@/components/Features/cadCover"
import { addCadEdges } from "@/components/Features/cadEdges"
import { coverFaceRanges } from "@/components/Features/coverFaceRanges"
import {
  coloredFaces,
  compatibleLayers,
  paintFaceGroups,
  SHARED_COLOR,
} from "@/components/Features/faceColors"
import {
  createModelControls,
  framePiece,
} from "@/components/Features/modelControls"
import { readCoverGeometry } from "@/components/Features/preparedCover"

/** Reuse the STEP worker and the feature camera; render the complete, unmarked part. */
export async function capturePartCad(
  file: FilePublic,
  signal: AbortSignal,
  layers: FaceLayer[] = [],
  featureId?: string,
) {
  if (file.size > MAX_COVER_STEP_SIZE)
    throw new Error("El STEP supera los 50 MB.")
  const { meshes, sourceHash, geometryKey } = await readCoverGeometry(
    file.id,
    signal,
  )
  const valid = compatibleLayers(layers, file, sourceHash, geometryKey, meshes)
  const specific = featureId
    ? valid.find((layer) => layer.feature_id === featureId)
    : undefined
  // If the old selection fails verification, produce the current piece instead.
  const visible = specific ? [specific] : valid
  const { faces } = coloredFaces(visible)
  signal.throwIfAborted()
  const object = new THREE.Group()
  const materials = [
    "#b8bdc6",
    SHARED_COLOR,
    ...visible.map((layer) => layer.color),
  ].map(
    (color) =>
      new THREE.MeshPhongMaterial({
        color,
        side: THREE.DoubleSide,
      }),
  )
  const geometries: THREE.BufferGeometry[] = []
  const lineMaterials: THREE.LineBasicMaterial[] = []
  let renderer: THREE.WebGLRenderer | undefined
  let controller: ReturnType<typeof createModelControls> | undefined
  try {
    for (const [meshIndex, mesh] of meshes.entries()) {
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
      if (faces.size)
        paintFaceGroups(
          geometry,
          coverFaceRanges(mesh.faces, mesh.indices.length / 3),
          (face) => faces.get(`${meshIndex}:${face}`) ?? 0,
        )
      const surface = new THREE.Mesh(
        geometry,
        faces.size ? materials : materials[0],
      )
      const edges = addCadEdges(surface, mesh.edgeIndices)
      geometries.push(edges.geometry)
      lineMaterials.push(edges.material)
      object.add(surface)
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
    if (specific) {
      const view = specific.selection.camera
      camera.position.fromArray(view.position)
      camera.up.fromArray(view.up)
      controller.controls.target.fromArray(view.target)
    } else
      framePiece(
        camera,
        valid.length === 1 ? valid[0].selection.camera : undefined,
      )
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
    return { image, sourceHash, geometryKey, featureId: specific?.feature_id }
  } finally {
    controller?.dispose()
    for (const geometry of geometries) geometry.dispose()
    for (const lineMaterial of lineMaterials) lineMaterial.dispose()
    for (const material of materials) material.dispose()
    renderer?.dispose()
    renderer?.forceContextLoss()
  }
}
