import { type ChildProcess, execFile } from "node:child_process"
import { realpath, stat } from "node:fs/promises"
import path from "node:path"
import type { Plugin } from "vite"

const loopback = (value: string | undefined) =>
  ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(value ?? "")

export function parsePickerOutput(output: string): string | null {
  const value = output.replace(/^\uFEFF/, "").trim()
  // Also accept the empty cancellation response from an already-running older helper.
  if (!value) return null
  const selected: unknown = JSON.parse(value)
  if (selected === null || typeof selected === "string") return selected
  throw new Error("El selector de Windows ha devuelto una selección no válida.")
}

export async function selectedRelativePath(root: string, selected: string) {
  const base = await realpath(root)
  const target = await realpath(selected)
  const relative = path.relative(base, target)
  if (
    !relative ||
    relative.startsWith(`..${path.sep}`) ||
    relative === ".." ||
    path.isAbsolute(relative)
  )
    throw new Error("Selecciona un archivo o carpeta dentro de Exemples.")
  return relative.split(path.sep).join("/")
}

/** The dialog runs on the local Windows workstation, never in the Docker backend. */
export function nativePickerPlugin(root: string, apiUrl: string): Plugin {
  let busy = false
  let activeChild: ChildProcess | undefined
  return {
    name: "inteplast-native-picker",
    configureServer(server) {
      server.httpServer?.once("close", () => activeChild?.kill())
      server.middlewares.use("/__native-picker", async (req, res) => {
        res.setHeader("Content-Type", "application/json; charset=utf-8")
        res.setHeader("Cache-Control", "no-store")
        const reply = (status: number, body: unknown) => {
          res.statusCode = status
          res.end(JSON.stringify(body))
        }
        const origin = req.headers.origin
        let localOrigin = false
        try {
          const url = new URL(origin ?? "")
          localOrigin =
            ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) &&
            url.host === req.headers.host &&
            url.protocol === "http:"
        } catch {
          /* Reject requests without a same-origin browser context. */
        }
        if (
          req.method !== "POST" ||
          !loopback(req.socket.remoteAddress) ||
          !localOrigin ||
          req.headers["content-type"] !== "application/json"
        ) {
          reply(403, {
            detail:
              "El selector solo está disponible desde la aplicación local.",
          })
          return
        }
        if (process.platform !== "win32" || !root) {
          reply(503, {
            detail:
              "El selector de Windows necesita la aplicación local y su carpeta de originales configurada.",
          })
          return
        }
        if (busy) {
          reply(409, { detail: "Ya hay un selector de Windows abierto." })
          return
        }
        busy = true
        try {
          const authorization = req.headers.authorization
          if (!authorization?.startsWith("Bearer ")) {
            reply(401, { detail: "Inicia sesión para seleccionar archivos." })
            return
          }
          const auth = await fetch(
            `${apiUrl.replace(/\/$/, "")}/api/v1/users/me`,
            {
              headers: { Authorization: authorization },
              signal: AbortSignal.timeout(10000),
            },
          )
          if (!auth.ok) {
            reply(401, {
              detail: "La sesión ha caducado. Vuelve a iniciar sesión.",
            })
            return
          }
          let body = ""
          for await (const chunk of req) {
            body += chunk
            if (body.length > 4096)
              throw new Error("Petición demasiado grande.")
          }
          const input = JSON.parse(body)
          if (!["folder", "file"].includes(input.kind))
            throw new Error("Selección no válida.")
          const script = path.resolve(
            server.config.root,
            "../scripts/native-picker.ps1",
          )
          const output = await new Promise<string>((resolve, reject) => {
            let startupError: Error | undefined
            let startupTimer: ReturnType<typeof setTimeout>
            const child = execFile(
              "powershell.exe",
              [
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script,
              ],
              {
                windowsHide: true,
                timeout: 5 * 60 * 1000,
                maxBuffer: 16384,
                env: {
                  ...process.env,
                  INTEPLAST_PICKER_ROOT: root,
                  INTEPLAST_PICKER_KIND: input.kind,
                },
              },
              (error, stdout) => {
                clearTimeout(startupTimer)
                activeChild = undefined
                if (error)
                  reject(
                    startupError ??
                      new Error(
                        "No se pudo completar la selección en Windows. Vuelve a intentarlo.",
                      ),
                  )
                else resolve(stdout)
              },
            )
            activeChild = child
            child.stdin?.end()
            let status = ""
            child.stderr?.on("data", (chunk) => {
              status += chunk.toString()
              if (status.includes("INTEPLAST_PICKER_READY"))
                clearTimeout(startupTimer)
            })
            startupTimer = setTimeout(() => {
              startupError = new Error(
                "Windows no ha podido mostrar el selector. Vuelve a intentarlo.",
              )
              child.kill()
            }, 20000)
            res.on("close", () => {
              if (!res.writableEnded) child.kill()
            })
            if (res.destroyed) child.kill()
          })
          const selected = parsePickerOutput(output)
          if (!selected) {
            reply(200, { path: null })
            return
          }
          const relative = await selectedRelativePath(root, selected)
          const info = await stat(selected)
          if (input.kind === "folder" ? !info.isDirectory() : !info.isFile())
            throw new Error("El elemento seleccionado no es válido.")
          reply(200, { path: relative })
        } catch (error) {
          reply(400, {
            detail:
              error instanceof Error
                ? error.message
                : "No se pudo abrir el selector.",
          })
        } finally {
          busy = false
        }
      })
    },
  }
}
