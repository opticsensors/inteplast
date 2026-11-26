import {
  type Object3D,
  OrthographicCamera,
  PerspectiveCamera,
  Quaternion,
  Vector3,
} from "three"
import { ArcballControls } from "three/examples/jsm/controls/ArcballControls.js"
import type { CadCamera } from "@/client"
import type { ViewerPreferences } from "@/hooks/useCadPreferences"
import { bindModelRotation } from "./modelRotation"

export function createModelCamera(size: number) {
  const half = size * 0.53
  const camera = new OrthographicCamera(
    -half,
    half,
    half,
    -half,
    size / 1000,
    size * 20,
  )
  camera.up.set(0, 0, 1)
  camera.position.set(1, -1, 0.8).setLength(size * 2)
  camera.lookAt(0, 0, 0)
  return camera
}

/** Read older perspective captures at the scale they had on their focal plane. */
export function frameCover(
  camera: OrthographicCamera,
  saved?: CadCamera,
  facing?: CadCamera,
) {
  const target = new Vector3()
  const view = saved ?? facing
  if (view) {
    const distance = camera.position.length()
    const direction = new Vector3()
      .fromArray(view.position)
      .sub(new Vector3().fromArray(view.target))
    if (saved) {
      target.fromArray(saved.target)
      const height =
        saved.ortho_height ?? 2 * Math.tan(Math.PI / 8) * direction.length()
      camera.zoom = (camera.top - camera.bottom) / height
    }
    camera.position.copy(direction.setLength(distance)).add(target)
    camera.up.fromArray(view.up)
  }
  camera.lookAt(target)
  camera.updateProjectionMatrix()
  return target
}

export function captureCamera(
  camera: OrthographicCamera,
  target: Vector3,
): CadCamera {
  return {
    position: camera.position.toArray(),
    up: camera.up.toArray(),
    target: target.toArray(),
    ortho_height:
      Math.min(camera.top - camera.bottom, camera.right - camera.left) /
      camera.zoom,
  }
}

export function createModelControls(
  camera: OrthographicCamera,
  canvas: HTMLCanvasElement,
  defaultPivot: Vector3,
  initialTarget = new Vector3(),
  model?: Object3D,
) {
  let classic = false
  let usePerspective = false
  const perspective = new PerspectiveCamera(45, 1, camera.near, camera.far)
  const routePointer = (event: PointerEvent) => {
    if (event.pointerType === "touch") return
    if (event.button === 0 && !classic) event.stopPropagation()
    if (event.button === 1) event.preventDefault()
  }
  canvas.addEventListener("pointerdown", routePointer)

  // Arcball handles the gestures on a second camera. Its own focus moves on
  // pan and cursor zoom. Apply those translations to the framing, while every
  // change of orientation carries the view rigidly around the active pivot.
  const navigation = camera.clone()
  navigation.position.sub(initialTarget)
  navigation.up.set(0, 1, 0) // Arcball expects camera-local up when rotating.
  const focusDistance = navigation.position.length()
  const controls = new ArcballControls(navigation, canvas.parentElement!)
  controls.enableRotate = false
  navigation.up.copy(camera.up)
  controls.enableAnimations = false
  controls.enableFocus = false
  controls.cursorZoom = true
  controls.scaleFactor = 1.2
  controls.minZoom = Math.min(0.1, camera.zoom)
  controls.maxZoom = Math.max(64, camera.zoom)
  controls.unsetMouseAction(0)
  controls.unsetMouseAction(0, "CTRL")
  controls.unsetMouseAction("WHEEL", "SHIFT")
  controls.setMouseAction("ROTATE", 1)
  controls.setMouseAction("PAN", 1, "CTRL")
  controls.setMouseAction("ZOOM", 1, "SHIFT")
  controls.update()
  controls.saveState()

  const focus = new Vector3()
  const previousFocus = new Vector3()
  const previousRotation = navigation.quaternion.clone()
  const basis = new Quaternion()
  const orientation = new Quaternion()
  const translation = new Vector3()
  const pivot = defaultPivot.clone()
  const rotation = new Quaternion()
  const target = initialTarget.clone()
  function syncPerspective() {
    if (!usePerspective) return
    const height = (camera.top - camera.bottom) / camera.zoom
    perspective.aspect = camera.right / camera.top
    perspective.zoom = Math.min(1, perspective.aspect)
    const distance = (height * perspective.zoom) / (2 * Math.tan(Math.PI / 8))
    perspective.position
      .set(0, 0, distance)
      .applyQuaternion(camera.quaternion)
      .add(target)
    perspective.quaternion.copy(camera.quaternion)
    perspective.up.copy(camera.up)
    perspective.near = Math.min(camera.near, distance / 100)
    perspective.far = distance + camera.far
    perspective.updateProjectionMatrix()
    perspective.updateMatrixWorld()
  }
  function syncView() {
    // Orthographic zoom changes magnification and leaves focal distance constant.
    navigation
      .getWorldDirection(focus)
      .multiplyScalar(focusDistance)
      .add(navigation.position)
    orientation.multiplyQuaternions(basis, navigation.quaternion)
    rotation.copy(previousRotation).invert().premultiply(orientation)
    target.sub(pivot).applyQuaternion(rotation).add(pivot)
    target.add(
      translation.subVectors(focus, previousFocus).applyQuaternion(basis),
    )
    previousFocus.copy(focus)
    previousRotation.copy(orientation)
    camera.position
      .copy(navigation.position)
      .sub(focus)
      .applyQuaternion(basis)
      .add(target)
    camera.quaternion.copy(orientation)
    camera.up.set(0, 1, 0).applyQuaternion(camera.quaternion)
    camera.zoom = navigation.zoom
    camera.updateProjectionMatrix()
    camera.updateMatrixWorld()
    syncPerspective()
    gestures.updateMarker()
  }
  const viewCamera = () => (usePerspective ? perspective : camera)
  const gestures = bindModelRotation(
    canvas,
    model,
    viewCamera,
    (next) => {
      // Keep Arcball's pan and wheel working in the axes of the displayed view.
      basis.copy(navigation.quaternion).invert().premultiply(next).normalize()
      controls.dispatchEvent({ type: "change" })
    },
    pivot,
    defaultPivot,
  )
  controls.addEventListener("change", syncView)
  syncView()
  const half = camera.top
  return {
    controls,
    target,
    get classic() {
      return classic
    },
    get viewCamera() {
      return viewCamera()
    },
    setPreferences(preferences: ViewerPreferences) {
      classic = preferences.cad_controls === "classic"
      usePerspective = preferences.cad_projection === "perspective"
      gestures.setOptions(classic, preferences.pick_rotation_center ?? true)
      controls.enableRotate = classic
      controls.scaleFactor = preferences.invert_zoom ? 1 / 1.2 : 1.2
      controls.cursorZoom = !classic
      if (classic) controls.setMouseAction("ROTATE", 0)
      else controls.unsetMouseAction(0)
      controls.setMouseAction(classic ? "PAN" : "ROTATE", 1)
      controls.dispatchEvent({ type: "change" })
    },
    resize(aspect: number) {
      for (const lens of [camera, navigation]) {
        lens.top = half / Math.min(1, aspect)
        lens.bottom = -lens.top
        lens.right = lens.top * aspect
        lens.left = -lens.right
        lens.updateProjectionMatrix()
      }
      controls.update()
      syncPerspective()
      gestures.updateMarker()
    },
    reset() {
      gestures.resetPivot()
      basis.identity()
      controls.reset()
      target.copy(initialTarget)
      controls.dispatchEvent({ type: "change" })
    },
    dispose() {
      canvas.removeEventListener("pointerdown", routePointer)
      gestures.dispose()
      controls.removeEventListener("change", syncView)
      controls.dispose()
    },
  }
}
