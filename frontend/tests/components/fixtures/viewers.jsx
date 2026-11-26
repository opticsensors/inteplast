import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRoot } from "react-dom/client"
import {
  BoxGeometry,
  BufferGeometry,
  Float32BufferAttribute,
  Mesh,
  Vector3,
} from "three"
import {
  captureCamera,
  createModelCamera,
  createModelControls,
  frameCover,
} from "../../../src/components/Features/modelControls"
import { modelPivot } from "../../../src/components/Features/modelPivot"
import PdfViewer from "../../../src/components/Features/PdfViewer"

if (location.hash === "#model") {
  const canvas = document.createElement("canvas")
  canvas.width = 800
  canvas.height = 600
  canvas.style.cssText = "width:800px;height:600px;display:block"
  const host = document.createElement("div")
  document.getElementById("root").appendChild(host)
  host.appendChild(canvas)
  let camera, controller, front, center
  const solid = new Mesh(new BoxGeometry(4, 4, 4))
  function open(size = 10, pivot = [0, 0, 0], saved) {
    controller?.dispose()
    camera = createModelCamera(size)
    center = new Vector3(...pivot)
    const target = frameCover(camera, saved)
    controller = createModelControls(camera, canvas, center, target, solid)
    controller.resize(800 / 600)
    front = camera.position.clone().sub(target).normalize().multiplyScalar(5)
  }
  open()
  window.viewer = {
    open,
    configure: (preferences) => controller.setPreferences(preferences),
    position: () => camera.position.toArray(),
    orientation: () => camera.quaternion.toArray(),
    front: () => front.clone().project(camera).toArray(),
    zoom: () => camera.zoom,
    target: () => controller.target.toArray(),
    projectedPivot: () => center.clone().project(camera).toArray(),
    height: () => captureCamera(camera, controller.target).ortho_height,
    parallel: () => {
      const lens = controller.viewCamera
      const near = new Vector3(1, 0, -5).applyMatrix4(lens.matrixWorld)
      const far = new Vector3(1, 0, -15).applyMatrix4(lens.matrixWorld)
      return [near.project(lens).x, far.project(lens).x]
    },
    meshCenter: (closed) => {
      const geometry = new BufferGeometry()
      geometry.setAttribute(
        "position",
        new Float32BufferAttribute([0, 0, 0, 3, 0, 0, 0, 6, 0, 0, 0, 9], 3),
      )
      const triangles = [0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3]
      geometry.setIndex(closed ? triangles : triangles.slice(3))
      const mesh = new Mesh(geometry.toNonIndexed())
      mesh.position.set(2, -1, 3)
      return modelPivot(mesh).toArray()
    },
    pointAtCursor: () => {
      const point = new Vector3(
        0.5,
        0,
        center.clone().project(camera).z,
      ).unproject(camera)
      return () => point.clone().project(camera).x
    },
    restoredView: () => {
      const restored = createModelCamera(10)
      restored.right = camera.right
      restored.left = camera.left
      frameCover(restored, captureCamera(camera, controller.target))
      restored.updateMatrixWorld()
      return front.clone().project(restored).toArray()
    },
    reset: () => controller.reset(),
  }
} else {
  const root = createRoot(document.getElementById("root"))
  const client = new QueryClient()
  window.viewer = {
    mount: (focus) =>
      root.render(
        <QueryClientProvider client={client}>
          <PdfViewer
            file={{ id: "synthetic-pdf" }}
            title="Plano de prueba"
            focus={focus}
          />
        </QueryClientProvider>,
      ),
    unmount: () => root.render(null),
  }
  window.viewer.mount()
}
