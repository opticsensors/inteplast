import { createRoot } from "react-dom/client"
import { PerspectiveCamera, Vector3 } from "three"
import { createModelControls } from "../../../src/components/Features/modelControls"
import PdfViewer from "../../../src/components/Features/PdfViewer"

if (location.hash === "#model") {
  const canvas = document.createElement("canvas")
  canvas.width = 800
  canvas.height = 600
  canvas.style.cssText = "width:800px;height:600px;display:block"
  document.getElementById("root").appendChild(canvas)
  const camera = new PerspectiveCamera(45, 800 / 600, 0.01, 1000)
  const { controls } = createModelControls(camera, canvas, 10)
  const front = camera.position.clone().normalize().multiplyScalar(5)
  const frame = () => {
    controls.update()
    camera.updateMatrixWorld()
    requestAnimationFrame(frame)
  }
  frame()
  window.viewer = {
    position: () => camera.position.toArray(),
    up: () => camera.up.toArray(),
    front: () => front.clone().project(camera).toArray(),
    distance: () => camera.position.distanceTo(controls.target),
    reset: () => controls.reset(),
    projectedOrigin: () => new Vector3().project(camera).toArray(),
  }
} else {
  const root = createRoot(document.getElementById("root"))
  window.viewer = {
    mount: () =>
      root.render(
        <PdfViewer file={{ id: "synthetic-pdf" }} title="Plano de prueba" />,
      ),
    unmount: () => root.render(null),
  }
  window.viewer.mount()
}
