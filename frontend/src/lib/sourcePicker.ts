import { LoginService } from "@/client"
import { pickNativePath } from "./nativePicker"

export type SourcePick = {
  kind: "folder" | "file"
  start?: string
  signal?: AbortSignal
}

let browser: ((pick: SourcePick) => Promise<string | null>) | null = null
let sharepoint: Promise<boolean> | null = null

/** Registered by `Common/SourceBrowser`, mounted once in the application layout. */
export function registerSourceBrowser(open: typeof browser) {
  browser = open
}

const usesSharePoint = () => {
  sharepoint ??= Promise.resolve()
    .then(() => LoginService.loginMethods())
    .then((methods) => methods.sharepoint)
    .catch(() => {
      // Ask again next time; meanwhile keep the local behaviour.
      sharepoint = null
      return false
    })
  return sharepoint
}

/**
 * A folder or file of the configured source, as a path from its root.
 * Locally the Windows dialog; with SharePoint, a browser inside the
 * application, opened at `start` when given. Cancelling returns null.
 */
export async function pickSourcePath(
  kind: SourcePick["kind"],
  signal?: AbortSignal,
  start?: string,
): Promise<string | null> {
  if (!(await usesSharePoint())) return pickNativePath(kind, signal)
  if (!browser) throw new Error("El selector de SharePoint no está disponible.")
  return browser({ kind, start, signal })
}
