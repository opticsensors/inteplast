import { Eraser, RotateCcw } from "lucide-react"
import { type ReactNode, useEffect, useRef, useState } from "react"
import * as THREE from "three"

import { type FeatureCover3D, type FilePublic, FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import { absoluteFileUrl, fileErrorMessage } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { CoverLoading } from "./CoverLoading"
import {
  COVER_RECIPE,
  type CoverControls,
  MAX_COVER_STEP_SIZE,
  sha256,
} from "./cadCover"
import { loadCoverGeometry } from "./coverGeometry"
import { createModelControls } from "./modelControls"

type Face = { first: number; last: number }
type Surface = {
  meshIndex: number
  faceIndex: number
}

/** CAD face selection always uses the full STEP tessellation, never a decimated mesh. */
export default function StepCoverCanvas({
  file,
  initial,
  editable = false,
  className,
  fallback,
  onReady,
  onSelectionChange,
  onResetSelection,
  disabled = false,
  wholePart = false,
}: {
  file: FilePublic
  initial?: FeatureCover3D | null
  editable?: boolean
  className?: string
  fallback?: ReactNode
  onReady?: (controls: CoverControls | null) => void
  onSelectionChange?: (count: number) => void
  onResetSelection?: () => void
  disabled?: boolean
  wholePart?: boolean
}) {
  const host = useRef<HTMLDivElement>(null)
  const callbacks = useRef({ onReady, onSelectionChange })
  callbacks.current = { onReady, onSelectionChange }
  const reset = useRef<() => void>(() => {})
  const clearSelection = useRef<() => void>(() => {})
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
    setRestartable(false)
    setError("")
    setStatus("Cargando CAD…")

    const run = async () => {
      if (file.size > MAX_COVER_STEP_SIZE)
        throw new Error(
          "La selección de superficies admite STEP de hasta 50 MB. Vincula una exportación de la pieza más pequeña.",
        )
      const access = await FilesService.createFileAccessUrl({ fileId: file.id })
      if (stopped) return
      const response = await fetch(absoluteFileUrl(access.url), {
        signal: abort.signal,
      })
      if (!response.ok)
        throw new Error(
          "El CAD no está disponible. Revisa su vínculo en Piezas ejemplo.",
        )
      const buffer = await response.arrayBuffer()
      if (stopped) return
      const sourceHash = await sha256(buffer)
      if (stopped) return
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
      setStatus("Preparando superficies…")
      const { meshes: prepared, geometryKey } = await loadCoverGeometry(
        buffer,
        abort.signal,
      )
      if (stopped) return
      const object = new THREE.Group()
      const meshes: THREE.Mesh[] = []
      const materials = [
        new THREE.MeshPhongMaterial({
          color: 0xb8bdc6,
          side: THREE.DoubleSide,
        }),
        new THREE.MeshPhongMaterial({
          color: 0xe32636,
          side: THREE.DoubleSide,
        }),
        new THREE.MeshPhongMaterial({
          color: 0xf5ac54,
          side: THREE.DoubleSide,
        }),
      ]
      cleanup.push(() => {
        for (const mesh of meshes) mesh.geometry.dispose()
        for (const material of materials) material.dispose()
      })
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
        rendered.userData.cadFaces = mesh.faces
        meshes.push(rendered)
        object.add(rendered)
        // Allow closing between meshes, including during renderer preparation.
        await new Promise((resolve) => setTimeout(resolve, 0))
        if (stopped) {
          release()
          return
        }
      }
      const surfaces = new Map<string, Surface>()
      const ranges: Face[][] = []
      meshes.forEach((mesh, meshIndex) => {
        const faces = mesh.userData.cadFaces as Face[]
        ranges.push(faces)
        mesh.userData.meshIndex = meshIndex
        mesh.geometry.clearGroups()
        let next = 0
        faces.forEach((face, faceIndex) => {
          if (
            face.first < next ||
            face.last < face.first ||
            (face.last + 1) * 3 > (mesh.geometry.index?.count ?? 0)
          )
            throw new Error(
              "El STEP no conserva superficies seleccionables válidas.",
            )
          if (face.first > next)
            mesh.geometry.addGroup(next * 3, (face.first - next) * 3, 0)
          mesh.geometry.addGroup(
            face.first * 3,
            (face.last - face.first + 1) * 3,
            0,
          )
          surfaces.set(`${meshIndex}:${faceIndex}`, {
            meshIndex,
            faceIndex,
          })
          next = face.last + 1
        })
        const triangles = (mesh.geometry.index?.count ?? 0) / 3
        if (next < triangles)
          mesh.geometry.addGroup(next * 3, (triangles - next) * 3, 0)
      })
      if (stopped) {
        release()
        return
      }
      if (!surfaces.size)
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
      const paint = () => {
        // Merge adjacent faces of the same color: a gray part needs one draw
        // call per mesh, instead of thousands of calls for its CAD surfaces.
        meshes.forEach((mesh, meshIndex) => {
          const geometry = mesh.geometry
          geometry.clearGroups()
          const append = (first: number, count: number, color: number) => {
            if (!count) return
            const last = geometry.groups[geometry.groups.length - 1]
            if (
              last &&
              last.materialIndex === color &&
              last.start + last.count === first
            )
              last.count += count
            else geometry.addGroup(first, count, color)
          }
          let next = 0
          ranges[meshIndex].forEach((face, faceIndex) => {
            append(next * 3, (face.first - next) * 3, 0)
            const key = `${meshIndex}:${faceIndex}`
            append(
              face.first * 3,
              (face.last - face.first + 1) * 3,
              selected.has(key) ? 1 : key === hovered ? 2 : 0,
            )
            next = face.last + 1
          })
          append(next * 3, (geometry.index?.count ?? 0) - next * 3, 0)
        })
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
      scene.background = new THREE.Color(0xf4f5f7)
      scene.add(object, new THREE.HemisphereLight(0xffffff, 0x555566, 2.2))
      const light = new THREE.DirectionalLight(0xffffff, 1.6)
      scene.add(light)
      const camera = new THREE.PerspectiveCamera(45, 1, size / 1000, size * 20)
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
      const controller = createModelControls(camera, canvas, size)
      cleanup.push(controller.dispose)
      const controls = controller.controls
      const restore = () => {
        if (initial) {
          camera.position.fromArray(initial.camera.position)
          camera.up.fromArray(initial.camera.up)
          controls.target.fromArray(initial.camera.target)
          controls.update()
        } else {
          controls.reset()
          camera.position.multiplyScalar(0.72)
          controls.update()
        }
      }
      restore()
      reset.current = restore
      const resize = () => {
        const width = container.clientWidth,
          height = container.clientHeight
        if (!width || !height) return
        renderer.setSize(width, height)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        controls.handleResize()
      }
      const observer = new ResizeObserver(resize)
      observer.observe(container)
      cleanup.push(() => observer.disconnect())
      resize()
      const draw = () => {
        light.position.copy(camera.position)
        renderer.render(scene, camera)
      }
      renderer.setAnimationLoop(() => {
        controls.update()
        draw()
      })

      const ray = new THREE.Raycaster()
      const pick = (event: PointerEvent) => {
        const box = canvas.getBoundingClientRect()
        ray.setFromCamera(
          new THREE.Vector2(
            ((event.clientX - box.left) / box.width) * 2 - 1,
            (-(event.clientY - box.top) / box.height) * 2 + 1,
          ),
          camera,
        )
        const hit = ray.intersectObjects(meshes, false)[0]
        if (!hit || hit.faceIndex == null) return null
        const meshIndex = hit.object.userData.meshIndex as number
        const faceIndex = ranges[meshIndex].findIndex(
          (face) => hit.faceIndex! >= face.first && hit.faceIndex! <= face.last,
        )
        return faceIndex < 0 ? null : `${meshIndex}:${faceIndex}`
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
        hovered = pick(event)
        paint()
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
          if (!selected.size)
            throw new Error(
              "Selecciona al menos una superficie para la portada.",
            )
          hovered = null
          paint()
          controls.update()
          draw()
          const cameraView = {
            position: camera.position.toArray(),
            target: controls.target.toArray(),
            up: camera.up.toArray(),
          }
          const image = await new Promise<Blob>((resolve, reject) =>
            canvas.toBlob(
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
  }, [file.id, file.version, file.size, initial, editable, wholePart])

  return (
    <div
      className={cn(
        "relative aspect-square w-full overflow-hidden rounded-lg border",
        className,
      )}
    >
      <div ref={host} className="size-full" />
      {(status || error) && fallback && (
        <div className="absolute inset-0">{fallback}</div>
      )}
      {status && !error && <CoverLoading />}
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
