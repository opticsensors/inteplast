import { MOUSE, type PerspectiveCamera } from "three"
import { TrackballControls } from "three/examples/jsm/controls/TrackballControls.js"

/** Grab the model in screen space, with no fixed-up pole or residual inertia. */
export function createModelControls(
  camera: PerspectiveCamera,
  element: HTMLElement,
  size: number,
) {
  // Set the CAD's vertical axis before the controller saves the initial camera.
  camera.up.set(0, 0, 1)
  camera.position.set(size, -size, size * 0.8)
  const controls = new TrackballControls(camera, element)
  controls.staticMoving = true
  controls.rotateSpeed = 1.5
  controls.zoomSpeed = 0.8
  controls.panSpeed = 0.5
  controls.minDistance = size * 0.08
  controls.maxDistance = size * 8
  controls.mouseButtons = {
    LEFT: MOUSE.ROTATE,
    MIDDLE: MOUSE.PAN,
    RIGHT: MOUSE.PAN,
  }
  // Typing in another control must not leave the viewer in a keyboard mode.
  controls.keys = ["", "", ""]
  element.style.cursor = "grab"
  const start = () => {
    element.style.cursor = "grabbing"
  }
  const end = () => {
    element.style.cursor = "grab"
  }
  controls.addEventListener("start", start)
  controls.addEventListener("end", end)
  // Update screen coordinates on scroll as well as resize, before a new drag.
  const measure = () => controls.handleResize()
  element.addEventListener("pointerdown", measure, { capture: true })
  controls.update()
  return {
    controls,
    dispose: () => {
      element.removeEventListener("pointerdown", measure, { capture: true })
      controls.removeEventListener("start", start)
      controls.removeEventListener("end", end)
      controls.dispose()
    },
  }
}
