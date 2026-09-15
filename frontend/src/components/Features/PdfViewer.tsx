import { ChevronLeft, ChevronRight, Minus, Plus, RotateCcw } from "lucide-react"
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
  type RenderTask,
} from "pdfjs-dist"
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url"
import { useEffect, useRef, useState } from "react"

import { type FilePublic, FilesService } from "@/client"
import { absoluteFileUrl, fileErrorMessage } from "@/hooks/useFileAccess"

GlobalWorkerOptions.workerSrc = workerUrl

type View = { x: number; y: number; scale: number }
const toolbarButton =
  "flex size-8 items-center justify-center rounded-md hover:bg-accent disabled:opacity-40"

/** Render the PDF locally, then handle the sheet like an image on a desk. */
export default function PdfViewer({
  file,
  title,
}: {
  file: FilePublic
  title: string
}) {
  const surfaceRef = useRef<HTMLDivElement>(null)
  const sheetRef = useRef<HTMLCanvasElement>(null)
  const actions = useRef({ fit: () => {}, zoom: (_factor: number) => {} })
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    let loading: ReturnType<typeof getDocument> | undefined
    const load = async () => {
      try {
        const access = await FilesService.createFileAccessUrl({
          fileId: file.id,
        })
        if (!active) return
        loading = getDocument({
          url: absoluteFileUrl(access.url),
          useWasm: false,
        })
        const document = await loading.promise
        if (active) setPdf(document)
      } catch (failure) {
        if (active) setError(fileErrorMessage(failure))
      }
    }
    void load()
    return () => {
      active = false
      void loading?.destroy().catch(() => {})
    }
  }, [file.id])

  useEffect(() => {
    const surface = surfaceRef.current
    const canvas = sheetRef.current
    if (!pdf || !surface || !canvas) return
    let active = true
    let cleanup = () => {}
    let rendering: RenderTask | undefined
    let timer: ReturnType<typeof setTimeout> | undefined
    setReady(false)
    setError("")

    const openPage = async () => {
      try {
        const page = await pdf.getPage(pageNumber)
        if (!active) return
        const base = page.getViewport({ scale: 1 })
        let view: View = { x: 0, y: 0, scale: 1 }
        let viewportWidth = surface.clientWidth
        let viewportHeight = surface.clientHeight
        let fitted = true
        let renderSequence = 0
        let pointer: { id: number; x: number; y: number } | null = null
        canvas.style.width = `${base.width}px`
        canvas.style.height = `${base.height}px`

        const fitScale = () =>
          Math.min(
            (surface.clientWidth - 32) / base.width,
            (surface.clientHeight - 32) / base.height,
          )
        // Keep the current image during rendering. Cap the backing canvas, not the zoom.
        const render = async () => {
          const sequence = ++renderSequence
          rendering?.cancel()
          const scale = Math.min(
            view.scale * Math.min(window.devicePixelRatio || 1, 2),
            Math.sqrt(16_000_000 / (base.width * base.height)),
            8192 / Math.max(base.width, base.height),
          )
          const viewport = page.getViewport({ scale })
          const buffer = document.createElement("canvas")
          buffer.width = Math.ceil(viewport.width)
          buffer.height = Math.ceil(viewport.height)
          try {
            rendering = page.render({ canvas: buffer, viewport })
            await rendering.promise
            if (!active || sequence !== renderSequence) return
            canvas.width = buffer.width
            canvas.height = buffer.height
            canvas.getContext("2d")?.drawImage(buffer, 0, 0)
            setReady(true)
          } catch (failure) {
            if (
              active &&
              sequence === renderSequence &&
              !(
                failure instanceof Error &&
                failure.name === "RenderingCancelledException"
              )
            ) {
              setError(fileErrorMessage(failure))
            }
          }
        }
        const apply = (next: View, redraw = false) => {
          view = next
          canvas.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`
          if (redraw) {
            clearTimeout(timer)
            timer = setTimeout(() => void render(), 120)
          }
        }
        const fit = () => {
          fitted = true
          const scale = fitScale()
          apply(
            {
              x: (surface.clientWidth - base.width * scale) / 2,
              y: (surface.clientHeight - base.height * scale) / 2,
              scale,
            },
            true,
          )
        }
        const zoomAt = (factor: number, x: number, y: number) => {
          fitted = false
          const scale = Math.max(
            fitScale() * 0.25,
            Math.min(Math.max(8, fitScale() * 16), view.scale * factor),
          )
          const ratio = scale / view.scale
          apply(
            { x: x - (x - view.x) * ratio, y: y - (y - view.y) * ratio, scale },
            true,
          )
        }
        const wheel = (event: WheelEvent) => {
          event.preventDefault()
          const box = surface.getBoundingClientRect()
          const delta =
            event.deltaY *
            (event.deltaMode === 1
              ? 16
              : event.deltaMode === 2
                ? surface.clientHeight
                : 1)
          zoomAt(
            Math.exp(-Math.max(-200, Math.min(200, delta)) * 0.002),
            event.clientX - box.left,
            event.clientY - box.top,
          )
        }
        const down = (event: PointerEvent) => {
          if (event.button !== 0 || pointer) return
          event.preventDefault()
          surface.focus({ preventScroll: true })
          surface.setPointerCapture(event.pointerId)
          pointer = { id: event.pointerId, x: event.clientX, y: event.clientY }
          surface.style.cursor = "grabbing"
        }
        const move = (event: PointerEvent) => {
          if (!pointer || pointer.id !== event.pointerId) return
          fitted = false
          apply({
            ...view,
            x: view.x + event.clientX - pointer.x,
            y: view.y + event.clientY - pointer.y,
          })
          pointer = { id: event.pointerId, x: event.clientX, y: event.clientY }
        }
        const up = (event: PointerEvent) => {
          if (!pointer || pointer.id !== event.pointerId) return
          pointer = null
          surface.style.cursor = "grab"
          if (surface.hasPointerCapture(event.pointerId))
            surface.releasePointerCapture(event.pointerId)
        }
        const key = (event: KeyboardEvent) => {
          if (
            [
              "+",
              "=",
              "-",
              "0",
              "ArrowLeft",
              "ArrowRight",
              "ArrowUp",
              "ArrowDown",
            ].includes(event.key)
          )
            event.preventDefault()
          if (event.key === "0") fit()
          else if (["+", "=", "-"].includes(event.key))
            zoomAt(
              event.key === "-" ? 0.8 : 1.25,
              surface.clientWidth / 2,
              surface.clientHeight / 2,
            )
          else if (event.key.startsWith("Arrow")) {
            fitted = false
            apply({
              ...view,
              x:
                view.x +
                (event.key === "ArrowLeft"
                  ? -50
                  : event.key === "ArrowRight"
                    ? 50
                    : 0),
              y:
                view.y +
                (event.key === "ArrowUp"
                  ? -50
                  : event.key === "ArrowDown"
                    ? 50
                    : 0),
            })
          }
        }
        const resize = new ResizeObserver(() => {
          if (
            surface.clientWidth === viewportWidth &&
            surface.clientHeight === viewportHeight
          )
            return
          if (fitted) fit()
          else
            apply({
              ...view,
              x: view.x + (surface.clientWidth - viewportWidth) / 2,
              y: view.y + (surface.clientHeight - viewportHeight) / 2,
            })
          viewportWidth = surface.clientWidth
          viewportHeight = surface.clientHeight
        })
        resize.observe(surface)
        surface.addEventListener("wheel", wheel, { passive: false })
        surface.addEventListener("pointerdown", down)
        surface.addEventListener("pointermove", move)
        surface.addEventListener("pointerup", up)
        surface.addEventListener("pointercancel", up)
        surface.addEventListener("lostpointercapture", up)
        surface.addEventListener("keydown", key)
        actions.current = {
          fit,
          zoom: (factor) =>
            zoomAt(factor, surface.clientWidth / 2, surface.clientHeight / 2),
        }
        fit()
        cleanup = () => {
          resize.disconnect()
          surface.removeEventListener("wheel", wheel)
          surface.removeEventListener("pointerdown", down)
          surface.removeEventListener("pointermove", move)
          surface.removeEventListener("pointerup", up)
          surface.removeEventListener("pointercancel", up)
          surface.removeEventListener("lostpointercapture", up)
          surface.removeEventListener("keydown", key)
          if (pointer && surface.hasPointerCapture(pointer.id))
            surface.releasePointerCapture(pointer.id)
          surface.style.cursor = "grab"
        }
      } catch (failure) {
        if (active) setError(fileErrorMessage(failure))
      }
    }
    void openPage()
    return () => {
      active = false
      clearTimeout(timer)
      rendering?.cancel()
      cleanup()
      actions.current = { fit: () => {}, zoom: () => {} }
    }
  }, [pdf, pageNumber])

  return (
    <div className="relative h-[75vh] w-full overflow-hidden rounded-lg border bg-muted/30">
      <div
        ref={surfaceRef}
        role="application"
        aria-label={title}
        // biome-ignore lint/a11y/noNoninteractiveTabindex: This viewport implements arrow-key panning and keyboard zoom.
        tabIndex={0}
        className="size-full touch-none overflow-hidden outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
        style={{ cursor: "grab" }}
      >
        <canvas
          ref={sheetRef}
          role="img"
          aria-label={title}
          className="pointer-events-none absolute left-0 top-0 origin-top-left bg-white shadow-md"
          style={{ visibility: ready && !error ? "visible" : "hidden" }}
        />
      </div>
      {!ready && !error && (
        <output className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          Cargando plano…
        </output>
      )}
      {error && (
        <p
          role="alert"
          className="absolute inset-0 flex items-center justify-center p-6 text-center"
        >
          No se ha podido abrir el plano. {error}
        </p>
      )}
      {ready && !error && (
        <div className="absolute right-2 top-2 flex items-center gap-1 rounded-md border bg-background/90 p-1 shadow-sm">
          {pdf && pdf.numPages > 1 && (
            <>
              <button
                type="button"
                className={toolbarButton}
                aria-label="Página anterior"
                disabled={pageNumber === 1}
                onClick={() => setPageNumber(pageNumber - 1)}
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="px-1 text-xs">
                {pageNumber} / {pdf.numPages}
              </span>
              <button
                type="button"
                className={toolbarButton}
                aria-label="Página siguiente"
                disabled={pageNumber === pdf.numPages}
                onClick={() => setPageNumber(pageNumber + 1)}
              >
                <ChevronRight className="size-4" />
              </button>
            </>
          )}
          <button
            type="button"
            className={toolbarButton}
            aria-label="Alejar"
            title="Alejar"
            onClick={() => actions.current.zoom(0.8)}
          >
            <Minus className="size-4" />
          </button>
          <button
            type="button"
            className={toolbarButton}
            aria-label="Acercar"
            title="Acercar"
            onClick={() => actions.current.zoom(1.25)}
          >
            <Plus className="size-4" />
          </button>
          <button
            type="button"
            className="flex h-8 items-center gap-1 rounded-md px-2 text-xs hover:bg-accent"
            onClick={() => actions.current.fit()}
          >
            <RotateCcw className="size-3.5" />
            Encuadrar
          </button>
        </div>
      )}
    </div>
  )
}
