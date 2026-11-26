import { Eraser, RotateCcw } from "lucide-react"
import { type ReactNode, useEffect, useRef, useState } from "react"
import * as THREE from "three"

import type { FaceLayer, FeatureCover3D, FilePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { useConfigureCadViewer } from "@/hooks/useCadPreferences"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { CoverLoading } from "./CoverLoading"
import {
  CAD_COVER_BACKGROUND,
  COVER_RECIPE,
  type CoverControls,
  MAX_COVER_STEP_SIZE,
} from "./cadCover"
import { addCadEdges } from "./cadEdges"
import { coverFaceRanges } from "./coverFaceRanges"
import {
  coloredFaces,
  compatibleLayers,
  paintFaceGroups,
  SHARED_COLOR,
} from "./faceColors"
import {
  captureCamera,
  createModelCamera,
  createModelControls,
  frameCover,
} from "./modelControls"
import { modelPivot } from "./modelPivot"
import { readCoverGeometry } from "./preparedCover"

const EMPTY_LAYERS: FaceLayer[] = []

type Surface = {
  meshIndex: number
  faceIndex: number
}

/** CAD face selection always uses the full STEP tessellation, never a decimated mesh. */
export default function StepCoverCanvas({
  file,
  initial,
  color = "#e32636",
  layers = EMPTY_LAYERS,
  editable = false,
  className,
  fallback,
  onReady,
  onSelectionChange,
  onResetSelection,
  disabled = false,
  wholePart = false,
  allowWholeComponent = false,
}: {
  file: FilePublic
  initial?: FeatureCover3D | null
  color?: string
  layers?: FaceLayer[]
  editable?: boolean
  className?: string
  fallback?: ReactNode
  onReady?: (controls: CoverControls | null) => void
  onSelectionChange?: (count: number) => void
  onResetSelection?: () => void
  disabled?: boolean
  wholePart?: boolean
  allowWholeComponent?: boolean
}) {
  const host = useRef<HTMLDivElement>(null)
  const configureViewer = useConfigureCadViewer()
  const callbacks = useRef({ onReady, onSelectionChange })
  callbacks.current = { onReady, onSelectionChange }
  const reset = useRef<() => void>(() => {})
  const clearSelection = useRef<() => void>(() => {})
  const [legend, setLegend] = useState<FaceLayer[]>([])
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [shared, setShared] = useState(false)
  const toggleLayers = useRef<(ids: Set<string>) => void>(() => {})
  const [selectedCount, setSelectedCount] = useState(0)
  const [restartable, setRestartable] = useState(false)
  const [status, setStatus] = useState("Cargando CAD…")
  const [error, setError] = useState("")

  useEffect(() => {
    const container = host.current
    if (!container) return
    let stopped = false
    const abort = new AbortController()
    const cleanup: (() => void)[] = []
    const release = () => {
      for (const dispose of cleanup.splice(0).reverse()) dispose()
    }
    callbacks.current.onReady?.(null)
    setSelectedCount(0)
    setLegend([])
    setHidden(new Set())
    setShared(false)
    setRestartable(false)
    setError("")
    setStatus("Cargando CAD…")

    const run = async () => {
      if (file.size > MAX_COVER_STEP_SIZE)
        throw new Error(
          "La selección de superficies admite STEP de hasta 50 MB. Vincula una exportación de la pieza más pequeña.",
        )
      const checkSource = (sourceHash: string) => {
        if (
          initial &&
          (initial.recipe !== COVER_RECIPE ||
            initial.source_sha256 !== sourceHash ||
            initial.file_id !== file.id ||
            (initial.file_version ?? null) !== (file.version ?? null))
        ) {
          setRestartable(true)
          throw new Error(
            "El CAD ha cambiado. Limpia la selección para trabajar con esta revisión.",
          )
        }
      }
      const {
        meshes: prepared,
        geometryKey,
        sourceHash,
      } = await readCoverGeometry(file.id, abort.signal, checkSource)
      if (stopped) return
      setStatus("Preparando superficies…")
      const object = new THREE.Group()
      const meshes: THREE.Mesh[] = []
      const valid = compatibleLayers(
        layers,
        { id: file.id, version: file.version },
        sourceHash,
        geometryKey,
        prepared,
      )
      const palette = wholePart
        ? ["#b8bdc6", SHARED_COLOR, ...valid.map((layer) => layer.color)]
        : ["#b8bdc6", color, "#f5ac54"]
      const materials = palette.map(
        (tint) =>
          new THREE.MeshPhongMaterial({ color: tint, side: THREE.DoubleSide }),
      )
      let painted = coloredFaces(valid)
      setLegend(valid)
      setShared(painted.shared)
      cleanup.push(() => {
        for (const mesh of meshes) mesh.geometry.dispose()
        for (const material of materials) material.dispose()
      })
      let lastYield = performance.now()
      for (const mesh of prepared) {
        const geometry = new THREE.BufferGeometry()
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
        const rendered = new THREE.Mesh(geometry, materials)
        const edges = addCadEdges(rendered, mesh.edgeIndices)
        cleanup.push(() => {
          edges.geometry.dispose()
          edges.material.dispose()
        })
        meshes.push(rendered)
        object.add(rendered)
        if (performance.now() - lastYield >= 10) {
          await new Promise((resolve) => setTimeout(resolve, 0))
          if (stopped) return
          lastYield = performance.now()
        }
      }
      const surfaces = new Map<string, Surface>()
      const ranges = meshes.map((mesh, meshIndex) => {
        mesh.userData.meshIndex = meshIndex
        if (wholePart && !valid.length) return []
        const faces = coverFaceRanges(
          prepared[meshIndex].faces,
          (mesh.geometry.index?.count ?? 0) / 3,
        )
        for (const { faceIndex } of faces) {
          surfaces.set(`${meshIndex}:${faceIndex}`, {
            meshIndex,
            faceIndex,
          })
        }
        return faces
      })
      if (stopped) {
        release()
        return
      }
      if (!wholePart && !surfaces.size)
        throw new Error(
          "Este STEP no contiene superficies que se puedan seleccionar.",
        )
      if (stopped) {
        release()
        return
      }
      const selected = new Set(
        (initial?.faces ?? []).map((face) => `${face.mesh}:${face.face}`),
      )
      if (
        initial &&
        (initial.geometry_key !== geometryKey ||
          [...selected].some((key) => !surfaces.has(key)))
      ) {
        setRestartable(true)
        throw new Error(
          "La geometría ha cambiado. Limpia la selección para volver a marcar las superficies.",
        )
      }
      let hovered: string | null = null
      let needsDraw = true
      const paint = () => {
        needsDraw = true
        // Merge adjacent faces of the same color: a gray part needs one draw
        // call per mesh, instead of thousands of calls for its CAD surfaces.
        meshes.forEach((mesh, meshIndex) => {
          paintFaceGroups(mesh.geometry, ranges[meshIndex], (face) => {
            const key = `${meshIndex}:${face}`
            return wholePart
              ? (painted.faces.get(key) ?? 0)
              : selected.has(key)
                ? 1
                : key === hovered
                  ? 2
                  : 0
          })
        })
      }
      toggleLayers.current = (ids) => {
        painted = coloredFaces(valid, ids)
        setShared(painted.shared)
        paint()
      }
      const changed = () => {
        paint()
        setSelectedCount(selected.size)
        callbacks.current.onSelectionChange?.(selected.size)
      }
      changed()

      const bounds = new THREE.Box3().setFromObject(object)
      const size = bounds.getSize(new THREE.Vector3()).length() || 1
      object.position.sub(bounds.getCenter(new THREE.Vector3()))
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(CAD_COVER_BACKGROUND)
      scene.add(object, new THREE.HemisphereLight(0xffffff, 0x555566, 2.2))
      const light = new THREE.DirectionalLight(0xffffff, 1.6)
      scene.add(light)
      const camera = createModelCamera(size)
      const target = frameCover(
        camera,
        initial?.camera,
        wholePart && valid.length === 1 ? valid[0].selection.camera : undefined,
      )
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      cleanup.push(() => {
        renderer.setAnimationLoop(null)
        renderer.dispose()
        renderer.forceContextLoss()
        renderer.domElement.remove()
      })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      const canvas = renderer.domElement
      canvas.setAttribute(
        "aria-label",
        editable
          ? "Seleccionar superficies del CAD"
          : wholePart
            ? "Modelo 3D de la pieza"
            : "Portada 3D del feature",
      )
      canvas.setAttribute("role", "img")
      container.appendChild(canvas)
      const controller = createModelControls(
        camera,
        canvas,
        modelPivot(object),
        target,
        object,
      )
      cleanup.push(controller.dispose)
      configureViewer(controller)
      cleanup.push(() => configureViewer(null))
      const controls = controller.controls
      reset.current = controller.reset
      const resize = () => {
        const width = container.clientWidth,
          height = container.clientHeight
        if (!width || !height) return
        renderer.setSize(width, height)
        controller.resize(width / height)
        needsDraw = true
      }
      const observer = new ResizeObserver(resize)
      observer.observe(container)
      cleanup.push(() => observer.disconnect())
      resize()
      const draw = () => {
        light.position.copy(controller.viewCamera.position)
        renderer.render(scene, controller.viewCamera)
        needsDraw = false
      }
      const invalidate = () => {
        needsDraw = true
      }
      controls.addEventListener("change", invalidate)
      cleanup.push(() => controls.removeEventListener("change", invalidate))
      renderer.setAnimationLoop(() => {
        if (needsDraw) draw()
      })

      const ray = new THREE.Raycaster()
      const pick = (event: PointerEvent) => {
        const box = canvas.getBoundingClientRect()
        ray.setFromCamera(
          new THREE.Vector2(
            ((event.clientX - box.left) / box.width) * 2 - 1,
            (-(event.clientY - box.top) / box.height) * 2 + 1,
          ),
          controller.viewCamera,
        )
        const hit = ray.intersectObjects(meshes, false)[0]
        if (!hit || hit.faceIndex == null) return null
        const meshIndex = hit.object.userData.meshIndex as number
        const range = ranges[meshIndex].find(
          (face) => hit.faceIndex! >= face.first && hit.faceIndex! <= face.last,
        )
        return range ? `${meshIndex}:${range.faceIndex}` : null
      }
      let down: { id: number; x: number; y: number; moved: boolean } | null =
        null
      const pointerDown = (event: PointerEvent) => {
        // A second touch cancels selection; pinch/drag are navigation only.
        if (down) {
          down = null
          return
        }
        if (event.button === 0)
          down = {
            id: event.pointerId,
            x: event.clientX,
            y: event.clientY,
            moved: false,
          }
      }
      const pointerMove = (event: PointerEvent) => {
        if (down) {
          if (Math.hypot(event.clientX - down.x, event.clientY - down.y) > 4)
            down.moved = true
          return
        }
        const next = pick(event)
        if (next !== hovered) {
          hovered = next
          paint()
        }
      }
      const pointerUp = (event: PointerEvent) => {
        if (
          down?.id === event.pointerId &&
          !down.moved &&
          Math.hypot(event.clientX - down.x, event.clientY - down.y) <= 4
        ) {
          const key = pick(event)
          if (key) {
            if (selected.has(key)) selected.delete(key)
            else if (selected.size < 5000) selected.add(key)
            changed()
          }
        }
        down = null
      }
      const cancel = () => {
        down = null
        hovered = null
        paint()
      }
      const leave = () => {
        hovered = null
        paint()
      }
      if (editable) {
        canvas.addEventListener("pointerdown", pointerDown)
        canvas.addEventListener("pointermove", pointerMove)
        canvas.addEventListener("pointerup", pointerUp)
        canvas.addEventListener("pointercancel", cancel)
        canvas.addEventListener("lostpointercapture", cancel)
        canvas.addEventListener("pointerleave", leave)
        cleanup.push(() => {
          canvas.removeEventListener("pointerdown", pointerDown)
          canvas.removeEventListener("pointermove", pointerMove)
          canvas.removeEventListener("pointerup", pointerUp)
          canvas.removeEventListener("pointercancel", cancel)
          canvas.removeEventListener("lostpointercapture", cancel)
          canvas.removeEventListener("pointerleave", leave)
        })
      }
      clearSelection.current = () => {
        selected.clear()
        hovered = null
        changed()
      }
      callbacks.current.onReady?.({
        clear: clearSelection.current,
        capture: async () => {
          if (!selected.size && !allowWholeComponent)
            throw new Error(
              "Selecciona al menos una superficie para la portada.",
            )
          hovered = null
          paint()
          draw()
          const cameraView = captureCamera(camera, controller.target)
          const crop = document.createElement("canvas")
          const side = Math.min(canvas.width, canvas.height)
          crop.width = crop.height = side
          const ctx = crop.getContext("2d")
          if (!ctx) throw new Error("No se ha podido crear la imagen.")
          ctx.drawImage(
            canvas,
            (canvas.width - side) / 2,
            (canvas.height - side) / 2,
            side,
            side,
            0,
            0,
            side,
            side,
          )
          const image = await new Promise<Blob>((resolve, reject) =>
            crop.toBlob(
              (blob) =>
                blob
                  ? resolve(blob)
                  : reject(new Error("No se ha podido crear la imagen.")),
              "image/png",
            ),
          )
          return {
            image,
            annotation: {
              recipe: COVER_RECIPE,
              source_sha256: sourceHash,
              geometry_key: geometryKey,
              faces: [...selected].map((key) => {
                const surface = surfaces.get(key)!
                return { mesh: surface.meshIndex, face: surface.faceIndex }
              }),
              camera: cameraView,
            },
          }
        },
      })
      setStatus("")
    }
    void run().catch((failure) => {
      release()
      if (!stopped) {
        setError(fileErrorMessage(failure))
        setStatus("")
        callbacks.current.onReady?.(null)
      }
    })
    return () => {
      stopped = true
      abort.abort()
      callbacks.current.onReady?.(null)
      release()
    }
  }, [
    configureViewer,
    file.id,
    file.version,
    file.size,
    initial,
    editable,
    wholePart,
    layers,
    color,
    allowWholeComponent,
  ])

  return (
    <div
      className={cn(
        "relative size-full min-h-0 overflow-hidden rounded-lg border [container-type:size]",
        className,
      )}
    >
      <div ref={host} className="size-full" />
      {editable && !status && !error && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-1/2 size-[min(100cqw,100cqh)] -translate-x-1/2 -translate-y-1/2 border border-dashed border-foreground/25"
        />
      )}
      {(status || error) && fallback && (
        <div className="absolute inset-0">{fallback}</div>
      )}
      {status && !error && <CoverLoading />}
      {!status && !error && legend.length > 0 && (
        <fieldset
          aria-label="Features visibles"
          className="absolute left-2 top-2 max-w-[70%] space-y-1 rounded-md border bg-background/95 px-2 py-1 text-xs shadow-sm"
        >
          {legend.map((layer) => (
            <label
              key={layer.feature_id}
              className="flex cursor-pointer items-center gap-1.5"
            >
              <input
                type="checkbox"
                checked={!hidden.has(layer.feature_id)}
                onChange={() => {
                  const next = new Set(hidden)
                  if (next.has(layer.feature_id)) next.delete(layer.feature_id)
                  else next.add(layer.feature_id)
                  setHidden(next)
                  toggleLayers.current(next)
                }}
              />
              <span
                aria-hidden
                className="size-2.5 rounded-sm"
                style={{ backgroundColor: layer.color }}
              />
              {layer.name}
            </label>
          ))}
          {shared && (
            <span className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="size-2.5 rounded-sm"
                style={{ backgroundColor: SHARED_COLOR }}
              />
              Varios features
            </span>
          )}
        </fieldset>
      )}
      {error && (
        <p
          role="alert"
          className={cn(
            "absolute flex items-center justify-center p-4 text-center text-sm",
            fallback
              ? "inset-x-2 bottom-2 rounded bg-background/95"
              : "inset-0 bg-muted",
          )}
        >
          {error}
        </p>
      )}
      {((!status && !error) || (editable && restartable)) && (
        <div className="absolute right-2 top-2 flex gap-1">
          {editable && (
            <Button
              type="button"
              variant="secondary"
              size="icon"
              className="size-7"
              title="Limpiar selección"
              aria-label="Limpiar selección"
              disabled={disabled || (!restartable && !selectedCount)}
              onClick={() =>
                restartable ? onResetSelection?.() : clearSelection.current()
              }
            >
              <Eraser className="size-3.5" />
            </Button>
          )}
          <Button
            type="button"
            variant="secondary"
            size="icon"
            className="size-7"
            title="Encuadrar"
            aria-label="Encuadrar"
            disabled={disabled || Boolean(status) || Boolean(error)}
            onClick={() => reset.current()}
          >
            <RotateCcw className="size-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}
