/**
 * `occt-import-js` no trae tipos: es OpenCascade (el kernel CAD de toda la
 * vida) compilado a WebAssembly. Aqui solo se declara lo que usamos, que es lo
 * que sale de sus propios ejemplos (`examples/three_viewer.html`).
 */
declare module "occt-import-js" {
  interface OcctArray {
    array: ArrayLike<number>
  }

  export interface OcctMesh {
    name?: string
    color?: [number, number, number]
    attributes: {
      position: OcctArray
      normal?: OcctArray
    }
    index: OcctArray
  }

  export interface OcctResult {
    success: boolean
    meshes: OcctMesh[]
  }

  export interface OcctModule {
    ReadStepFile(buffer: Uint8Array, params: unknown): OcctResult
    ReadIgesFile(buffer: Uint8Array, params: unknown): OcctResult
    ReadBrepFile(buffer: Uint8Array, params: unknown): OcctResult
  }

  export default function occtimportjs(options?: {
    locateFile?: (path: string) => string
  }): Promise<OcctModule>
}
