import {
  type Camera,
  type Mesh,
  type Object3D,
  Quaternion,
  Raycaster,
  Vector2,
  Vector3,
} from "three"

/** Incremental TrackballControls rotation in camera space, without inertia. */
function dragOrientation(view: Camera, dx: number, dy: number, scale: number) {
  const axis = new Vector3(-dy, -dx, 0).normalize()
  return view.quaternion
    .clone()
    .multiply(
      new Quaternion().setFromAxisAngle(axis, Math.hypot(dx, dy) * scale),
    )
}

export function bindModelRotation(
  canvas: HTMLCanvasElement,
  model: Object3D | undefined,
  view: () => Camera,
  orient: (orientation: Quaternion) => void,
  pivot: Vector3,
  defaultPivot: Vector3,
) {
  let classic = false
  let pickCenter = true
  let drag:
    | {
        id: number
        started: number
        startX: number
        startY: number
        x: number
        y: number
        moved: boolean
        rotate: boolean
        pick: boolean
      }
    | undefined
  const surfaces: Mesh[] = []
  model?.traverseVisible((child) => {
    if ((child as Mesh).isMesh) surfaces.push(child as Mesh)
  })
  function resetPivot() {
    pivot.copy(defaultPivot)
  }
  function pick(event: PointerEvent) {
    const box = canvas.getBoundingClientRect()
    const cursor = new Vector2(
      (2 * (event.clientX - box.left)) / box.width - 1,
      1 - (2 * (event.clientY - box.top)) / box.height,
    )
    if (Math.abs(cursor.x) > 1 || Math.abs(cursor.y) > 1) return
    const ray = new Raycaster()
    ray.setFromCamera(cursor, view())
    const hit = ray.intersectObjects(surfaces, false)[0]
    if (hit) pivot.copy(hit.point)
  }

  function down(event: PointerEvent) {
    if (event.pointerType === "touch" && !event.isPrimary) {
      drag = undefined
      return
    }
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
    const touch = event.pointerType === "touch"
    const rotate = !classic && (touch || event.button === 1)
    const canPick = pickCenter && !touch && event.button === 1
    if (!rotate && !canPick) return
    drag = {
      id: event.pointerId,
      started: event.timeStamp,
      startX: event.clientX,
      startY: event.clientY,
      x: event.clientX,
      y: event.clientY,
      moved: false,
      rotate,
      pick: canPick,
    }
    if (rotate && !touch) {
      event.preventDefault()
      event.stopPropagation()
      canvas.setPointerCapture(event.pointerId)
    }
  }
  function move(event: PointerEvent) {
    if (!drag || event.pointerId !== drag.id) return
    if (
      Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 4
    )
      drag.moved = true
    if (drag.pick && !drag.moved) {
      // Keep Arcball and classic pan stationary until the middle click becomes a drag.
      event.stopPropagation()
      return
    }
    const dx = event.clientX - drag.x
    const dy = event.clientY - drag.y
    if (drag.rotate && (dx || dy))
      orient(
        dragOrientation(
          view(),
          dx,
          dy,
          Math.PI /
            Math.max(1, Math.min(canvas.clientWidth, canvas.clientHeight)),
        ),
      )
    drag.x = event.clientX
    drag.y = event.clientY
  }
  function up(event: PointerEvent) {
    if (!drag || drag.id !== event.pointerId) return
    if (
      drag.pick &&
      !drag.moved &&
      event.timeStamp - drag.started <= 500 &&
      Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) <= 4
    )
      pick(event)
    drag = undefined
  }
  function cancel() {
    drag = undefined
  }
  canvas.addEventListener("pointerdown", down)
  window.addEventListener("pointermove", move, true)
  window.addEventListener("pointerup", up)
  window.addEventListener("pointercancel", cancel)
  window.addEventListener("blur", cancel)
  return {
    setOptions(nextClassic: boolean, nextPick: boolean) {
      if (classic !== nextClassic || pickCenter !== nextPick) cancel()
      classic = nextClassic
      pickCenter = nextPick
      if (!pickCenter) resetPivot()
    },
    resetPivot,
    dispose() {
      canvas.removeEventListener("pointerdown", down)
      window.removeEventListener("pointermove", move, true)
      window.removeEventListener("pointerup", up)
      window.removeEventListener("pointercancel", cancel)
      window.removeEventListener("blur", cancel)
    },
  }
}
