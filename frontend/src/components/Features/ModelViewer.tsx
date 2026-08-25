import { RotateCcw, TriangleAlert } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type * as THREE_NS from "three"

import type { FilePublic } from "@/client"
import { fileUrl } from "@/utils"

type Three = typeof THREE_NS

type Status =
  | { phase: "loading"; step: string }
  | { phase: "ready"; triangles: number }
  | { phase: "error"; message: string }

const extensionOf = (filename: string) =>
  filename.slice(filename.lastIndexOf(".") + 1).toLowerCase()

/** Cuenta triangulos de todo lo que cuelgue del objeto, solo para informar. */
function countTriangles(object: THREE_NS.Object3D): number {
  let total = 0
  object.traverse((child) => {
    const geometry = (child as THREE_NS.Mesh).geometry
    if (!geometry?.attributes?.position) return
    total += geometry.index
      ? geometry.index.count / 3
      : geometry.attributes.position.count / 3
  })
  return Math.round(total)
}

/**
 * Malla ya teselada (STL, PLY, OBJ, glTF): el fichero trae los triangulos
 * hechos y three.js solo tiene que pintarlos.
 */
async function loadMesh(
  three: Three,
  extension: string,
  buffer: ArrayBuffer,
): Promise<THREE_NS.Object3D> {
  const material = new three.MeshPhongMaterial({
    color: 0xb0b7c3,
    specular: 0x111111,
    shininess: 30,
    side: three.DoubleSide,
  })

  if (extension === "stl") {
    const { STLLoader } = await import(
      "three/examples/jsm/loaders/STLLoader.js"
    )
    const geometry = new STLLoader().parse(buffer)
    if (!geometry.attributes.normal) geometry.computeVertexNormals()
    return new three.Mesh(geometry, material)
  }

  if (extension === "ply") {
    const { PLYLoader } = await import(
      "three/examples/jsm/loaders/PLYLoader.js"
    )
    const geometry = new PLYLoader().parse(buffer)
    if (!geometry.attributes.normal) geometry.computeVertexNormals()
    return new three.Mesh(geometry, material)
  }

  if (extension === "obj") {
    const { OBJLoader } = await import(
      "three/examples/jsm/loaders/OBJLoader.js"
    )
    return new OBJLoader().parse(new TextDecoder().decode(buffer))
  }

  const { GLTFLoader } = await import(
    "three/examples/jsm/loaders/GLTFLoader.js"
  )
  const gltf = await new GLTFLoader().parseAsync(buffer, "")
  return gltf.scene
}

/**
 * B-rep (STEP, IGES, BREP): geometria con superficies NURBS, hay que teselarla
 * antes de poder pintarla. Lo hace OpenCascade compilado a WebAssembly, **en el
 * navegador del que mira**: el servidor no participa.
 */
async function loadBrep(
  three: Three,
  extension: string,
  buffer: ArrayBuffer,
): Promise<THREE_NS.Object3D> {
  const [{ default: occtimportjs }, { default: wasmUrl }] = await Promise.all([
    import("occt-import-js"),
    import("occt-import-js/dist/occt-import-js.wasm?url"),
  ])

  const occt = await occtimportjs({ locateFile: () => wasmUrl })
  const bytes = new Uint8Array(buffer)
  const result =
    extension === "igs" || extension === "iges"
      ? occt.ReadIgesFile(bytes, null)
      : extension === "brep"
        ? occt.ReadBrepFile(bytes, null)
        : occt.ReadStepFile(bytes, null)

  if (!result.success || result.meshes.length === 0) {
    throw new Error("OpenCascade no ha podido leer la geometria del fichero")
  }

  const group = new three.Group()
  for (const mesh of result.meshes) {
    const geometry = new three.BufferGeometry()
    geometry.setAttribute(
      "position",
      new three.Float32BufferAttribute(
        Array.from(mesh.attributes.position.array),
        3,
      ),
    )
    if (mesh.attributes.normal) {
      geometry.setAttribute(
        "normal",
        new three.Float32BufferAttribute(
          Array.from(mesh.attributes.normal.array),
          3,
        ),
      )
    }
    geometry.setIndex(Array.from(mesh.index.array))
    if (!mesh.attributes.normal) geometry.computeVertexNormals()

    const material = new three.MeshPhongMaterial({
      color: mesh.color
        ? new three.Color(mesh.color[0], mesh.color[1], mesh.color[2])
        : 0xb0b7c3,
      specular: 0x111111,
      shininess: 30,
      side: three.DoubleSide,
    })
    group.add(new three.Mesh(geometry, material))
  }
  return group
}

/**
 * Visor 3D. Se carga con `import()` dinamico desde la pagina del fichero, asi
 * que three.js y el WASM de OpenCascade **solo se descargan cuando alguien
 * abre un 3D**, nunca al entrar en la aplicacion.
 *
 * El limite de tamano lo decide `viewers.ts` antes de llegar aqui: el molde de
 * 247 MB del 3212 no pasa por este componente.
 */
export default function ModelViewer({ file }: { file: FilePublic }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const resetRef = useRef<() => void>(() => undefined)
  const [status, setStatus] = useState<Status>({
    phase: "loading",
    step: "Cargando el visor...",
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false
    let dispose: () => void = () => {}

    const run = async () => {
      try {
        const three = await import("three")
        if (disposed) return

        setStatus({ phase: "loading", step: "Descargando el fichero..." })
        const response = await fetch(fileUrl(file.id))
        if (!response.ok) {
          throw new Error(`no se ha podido descargar (HTTP ${response.status})`)
        }
        const buffer = await response.arrayBuffer()
        if (disposed) return

        setStatus({ phase: "loading", step: "Preparando la geometria..." })
        const extension = extensionOf(file.filename)
        const object = ["step", "stp", "igs", "iges", "brep"].includes(
          extension,
        )
          ? await loadBrep(three, extension, buffer)
          : await loadMesh(three, extension, buffer)
        if (disposed) return

        const { OrbitControls } = await import(
          "three/examples/jsm/controls/OrbitControls.js"
        )
        if (disposed) return

        // Centrar la pieza en el origen: los CAD vienen con las coordenadas
        // del sitio donde estaban en el molde, no alrededor del cero.
        const box = new three.Box3().setFromObject(object)
        const center = box.getCenter(new three.Vector3())
        const size = box.getSize(new three.Vector3()).length() || 1
        object.position.sub(center)

        const scene = new three.Scene()
        scene.add(object)
        scene.add(new three.HemisphereLight(0xffffff, 0x444455, 2.2))
        const keyLight = new three.DirectionalLight(0xffffff, 1.6)
        scene.add(keyLight)

        const camera = new three.PerspectiveCamera(
          45,
          1,
          size / 1000,
          size * 20,
        )
        const renderer = new three.WebGLRenderer({
          antialias: true,
          alpha: true,
        })
        renderer.setPixelRatio(window.devicePixelRatio)
        container.appendChild(renderer.domElement)

        const controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true

        const reset = () => {
          camera.position.set(size, -size, size * 0.8)
          camera.up.set(0, 0, 1)
          controls.target.set(0, 0, 0)
          controls.update()
        }
        reset()
        resetRef.current = reset

        const resize = () => {
          const { clientWidth, clientHeight } = container
          if (!clientWidth || !clientHeight) return
          renderer.setSize(clientWidth, clientHeight)
          camera.aspect = clientWidth / clientHeight
          camera.updateProjectionMatrix()
        }
        resize()
        const observer = new ResizeObserver(resize)
        observer.observe(container)

        renderer.setAnimationLoop(() => {
          controls.update()
          keyLight.position.copy(camera.position)
          renderer.render(scene, camera)
        })

        setStatus({ phase: "ready", triangles: countTriangles(object) })

        dispose = () => {
          renderer.setAnimationLoop(null)
          observer.disconnect()
          controls.dispose()
          object.traverse((child) => {
            const mesh = child as THREE_NS.Mesh
            mesh.geometry?.dispose()
            const material = mesh.material
            if (Array.isArray(material)) {
              for (const item of material) item.dispose()
            } else {
              material?.dispose()
            }
          })
          renderer.dispose()
          renderer.domElement.remove()
        }
      } catch (error) {
        if (disposed) return
        setStatus({
          phase: "error",
          message: error instanceof Error ? error.message : "error desconocido",
        })
      }
    }

    run()

    return () => {
      disposed = true
      dispose()
    }
  }, [file.id, file.filename])

  return (
    <div className="relative h-[70vh] w-full overflow-hidden rounded-lg border bg-muted/30">
      <div ref={containerRef} className="size-full" />

      {status.phase === "loading" && (
        <p className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          {status.step}
        </p>
      )}

      {status.phase === "error" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
          <TriangleAlert className="size-8 text-amber-500" />
          <p className="font-medium">No se ha podido abrir el 3D</p>
          <p className="max-w-md text-sm text-muted-foreground">
            {status.message}. El fichero se puede descargar igualmente con el
            boton de arriba.
          </p>
        </div>
      )}

      {status.phase === "ready" && (
        <>
          <p className="absolute bottom-2 left-3 text-xs text-muted-foreground">
            {status.triangles.toLocaleString("es-ES")} triangulos · arrastra
            para girar, rueda para acercar
          </p>
          <button
            type="button"
            onClick={() => resetRef.current()}
            className="absolute right-2 top-2 flex items-center gap-1 rounded-md border bg-background/80 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <RotateCcw className="size-3.5" />
            Encuadrar
          </button>
        </>
      )}
    </div>
  )
}
