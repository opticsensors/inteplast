import type { ViewBox } from "./faceBoxPicker"

/** Own only editing gestures. Arcball receives ordinary left drags in Classic. */
export function bindFaceSelection(
  canvas: HTMLCanvasElement,
  isClassic: () => boolean,
  click: (event: PointerEvent) => void,
  hover: (event: PointerEvent | null) => void,
  select: (box: ViewBox) => void,
) {
  const frame = document.createElement("div")
  frame.setAttribute("aria-hidden", "true")
  frame.className =
    "pointer-events-none absolute border border-blue-600 bg-blue-500/15"
  frame.hidden = true
  canvas.after(frame)
  let drag:
    | { id: number; x: number; y: number; box: boolean; moved: boolean }
    | undefined
  function cancel() {
    const id = drag?.box ? drag.id : undefined
    drag = undefined
    frame.hidden = true
    if (id !== undefined && canvas.hasPointerCapture(id))
      canvas.releasePointerCapture(id)
  }
  function down(event: PointerEvent) {
    if (drag || !event.isPrimary || event.button !== 0) {
      cancel()
      return
    }
    const box =
      event.pointerType === "mouse" && (!isClassic() || event.shiftKey)
    drag = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      box,
      moved: false,
    }
    if (box) {
      event.stopPropagation()
      canvas.setPointerCapture(event.pointerId)
    }
  }
  function rectangle(x1: number, y1: number, event: PointerEvent): ViewBox {
    const bounds = canvas.getBoundingClientRect()
    const fraction = (n: number) => Math.max(0, Math.min(1, n))
    return {
      left: fraction(
        (Math.min(x1, event.clientX) - bounds.left) / bounds.width,
      ),
      right: fraction(
        (Math.max(x1, event.clientX) - bounds.left) / bounds.width,
      ),
      top: fraction((Math.min(y1, event.clientY) - bounds.top) / bounds.height),
      bottom: fraction(
        (Math.max(y1, event.clientY) - bounds.top) / bounds.height,
      ),
    }
  }
  function move(event: PointerEvent) {
    if (!drag) {
      if (!event.buttons) hover(event)
      return
    }
    if (event.pointerId !== drag.id) return
    if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 4)
      drag.moved = true
    if (!drag.box || !drag.moved) return
    const box = rectangle(drag.x, drag.y, event)
    if (frame.hidden) hover(null)
    frame.hidden = false
    frame.style.left = `${box.left * 100}%`
    frame.style.top = `${box.top * 100}%`
    frame.style.width = `${(box.right - box.left) * 100}%`
    frame.style.height = `${(box.bottom - box.top) * 100}%`
  }
  function up(event: PointerEvent) {
    if (!drag || drag.id !== event.pointerId) return
    const { x, y, box, moved } = drag
    cancel()
    if (event.button !== 0) return
    if (!moved && Math.hypot(event.clientX - x, event.clientY - y) <= 4)
      click(event)
    else if (box) select(rectangle(x, y, event))
  }
  function cancelOnEscape(event: KeyboardEvent) {
    if (drag?.box && event.key === "Escape") {
      event.stopPropagation()
      event.preventDefault()
      cancel()
    }
  }
  const events = new AbortController()
  const options = { signal: events.signal }
  canvas.addEventListener("pointerdown", down, options)
  canvas.addEventListener("pointermove", move, options)
  canvas.addEventListener("pointerup", up, options)
  canvas.addEventListener("pointercancel", cancel, options)
  canvas.addEventListener("lostpointercapture", cancel, options)
  canvas.addEventListener(
    "pointerleave",
    () => {
      if (drag && !drag.box) cancel()
      hover(null)
    },
    options,
  )
  canvas.addEventListener("wheel", cancel, { ...options, passive: true })
  window.addEventListener("keydown", cancelOnEscape, {
    ...options,
    capture: true,
  })
  window.addEventListener("blur", cancel, options)
  return () => {
    events.abort()
    cancel()
    frame.remove()
  }
}
