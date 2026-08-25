import type { FilePublic } from "@/client"

/**
 * Que se puede hacer con un fichero desde el navegador.
 *
 * 🔴 Lo que NO se puede, y no hay forma: lanzar el programa del PC. Esta
 * prohibido, y ademas los bytes estan en el servidor, no en el disco del
 * usuario. Descargar y abrirlo desde la barra de descargas es el techo.
 */
export type ViewerKind = "pdf" | "image" | "mesh" | "brep" | null

/** Por encima de esto no se ofrece visor: se ofrece la descarga y se explica. */
export const VIEWER_MAX_MB = 50

const extensionOf = (filename: string) => {
  const dot = filename.lastIndexOf(".")
  return dot === -1 ? "" : filename.slice(dot + 1).toLowerCase()
}

/** Mallas: triangulos ya teselados, los pinta three.js directamente. */
const MESH = new Set(["stl", "glb", "gltf", "obj", "ply"])

/**
 * B-rep: geometria con NURBS, hay que teselarla antes de pintarla. Lo hace
 * OpenCascade compilado a WASM, en el propio navegador.
 */
const BREP = new Set(["step", "stp", "igs", "iges", "brep"])

/**
 * El programa que hace falta para abrir lo que no tiene visor. Es lo que se
 * escribe en gris debajo de la fila, para no prometer nada que no se cumple.
 */
const REQUIRED_APP: Record<string, string> = {
  mfr: "Moldflow Communicator",
  mpi: "Moldflow Insight",
  sldprt: "SolidWorks",
  sldasm: "SolidWorks",
  catpart: "CATIA",
  catproduct: "CATIA",
  prt: "el CAD que lo genero",
  dxf: "un CAD 2D (AutoCAD, LibreCAD...)",
  dwg: "AutoCAD",
}

/** El visor que le toca a un fichero, o null si no hay ninguno posible. */
export function viewerFor(file: FilePublic | null | undefined): ViewerKind {
  if (!file) return null
  const extension = extensionOf(file.filename)
  if (extension === "pdf" || file.content_type === "application/pdf") {
    return "pdf"
  }
  if (file.content_type?.startsWith("image/")) return "image"
  if (MESH.has(extension)) return "mesh"
  if (BREP.has(extension)) return "brep"
  return null
}

/** Nombre del programa necesario, cuando lo sabemos. */
export const requiredApp = (file: FilePublic | null | undefined) =>
  file ? (REQUIRED_APP[extensionOf(file.filename)] ?? null) : null

export const isTooBig = (file: FilePublic) =>
  file.size > VIEWER_MAX_MB * 1024 * 1024

/**
 * Que ofrece la fila: `view` = se puede mirar aqui; `download` = solo bajar.
 * El motivo es el que se escribe en gris, y es la parte que hace honesta la
 * interfaz: el usuario sabe que va a pasar ANTES de clicar.
 */
export function fileAction(file: FilePublic | null | undefined): {
  action: "view" | "download"
  viewer: ViewerKind
  reason: string | null
} {
  if (!file) return { action: "download", viewer: null, reason: null }

  const viewer = viewerFor(file)
  if (!viewer) {
    const app = requiredApp(file)
    return {
      action: "download",
      viewer: null,
      reason: app ? `necesita ${app}` : "no se puede previsualizar",
    }
  }
  // El molde del 3212 son 247 MB de ensamblaje completo: teselarlo en el
  // navegador no termina. Mas vale decirlo que dejar la pestana colgada.
  if ((viewer === "mesh" || viewer === "brep") && isTooBig(file)) {
    return {
      action: "download",
      viewer: null,
      reason: `demasiado grande para el visor (mas de ${VIEWER_MAX_MB} MB)`,
    }
  }
  return { action: "view", viewer, reason: null }
}
