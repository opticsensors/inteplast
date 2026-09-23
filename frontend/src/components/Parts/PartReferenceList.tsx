import { Link } from "@tanstack/react-router"
import { Download, FolderOpen, Loader2, Trash2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { PartDetailPublic, ReferenceChoice } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { ASSET_ICONS, ASSET_KIND_LABELS } from "@/components/Features/constants"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickNativePath } from "@/lib/nativePicker"
import { formatFileSize } from "@/utils"

export const REFERENCE_KINDS = ["part", "scan", "mold", "drawing"] as const
export type ReferenceChanges = Partial<
  Record<ReferenceChoice["kind"], ReferenceChoice>
>

export function PartReferenceList({
  data,
  editing,
  changes,
  onChange,
  saving,
  onPickingChange,
}: {
  data: PartDetailPublic
  editing: boolean
  changes: ReferenceChanges
  onChange: (choice: ReferenceChoice) => void
  saving: boolean
  onPickingChange: (value: boolean) => void
}) {
  const picker = useRef<AbortController | null>(null)
  const [picking, setPicking] = useState<ReferenceChoice["kind"] | null>(null)
  const [error, setError] = useState("")
  useEffect(() => {
    if (!editing) setError("")
    return () => picker.current?.abort()
  }, [editing])

  const choose = async (kind: ReferenceChoice["kind"]) => {
    const controller = new AbortController()
    picker.current = controller
    setPicking(kind)
    onPickingChange(true)
    setError("")
    try {
      const path = await pickNativePath("file", controller.signal)
      if (!path || controller.signal.aborted) return
      if (
        !data.part.folder_path ||
        !path.startsWith(`${data.part.folder_path}/`)
      )
        throw new Error(
          "Selecciona un archivo dentro de la carpeta de esta pieza.",
        )
      onChange({ kind, path, source_version: null })
    } catch (error) {
      if (!controller.signal.aborted) setError(fileErrorMessage(error))
    } finally {
      picker.current = null
      setPicking(null)
      onPickingChange(false)
    }
  }
  const kinds = editing
    ? [
        ...new Set([
          ...REFERENCE_KINDS,
          ...data.references.map(({ kind }) => kind),
        ]),
      ]
    : data.references.map(({ kind }) => kind)
  return (
    <>
      <div className="divide-y border-t">
        {kinds.map((kind) => {
          const file = data.references.find(
            (reference) => reference.kind === kind,
          )?.file
          const change =
            !editing || kind === "moldflow" ? undefined : changes[kind]
          const present = change ? Boolean(change.path) : Boolean(file)
          const current = file && !change
          const Icon = ASSET_ICONS[kind]
          const label = ASSET_KIND_LABELS[kind]
          const content = (
            <>
              <span className="shrink-0 font-medium">{label}</span>
              {current ? (
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </span>
              ) : (
                <span className="truncate text-xs text-muted-foreground">
                  {present ? change?.path?.split("/").pop() : "Sin archivo"}
                </span>
              )}
            </>
          )
          return (
            <fieldset
              key={kind}
              className="flex min-w-0 items-center gap-2 py-1.5 text-sm"
              aria-label={`Archivo ${label}`}
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted/60">
                <Icon className="size-4 text-muted-foreground" />
              </span>
              {current ? (
                <Link
                  to="/parts/$partId/fichero/$fileId"
                  params={{ partId: data.part.id, fileId: file.id }}
                  title={file.filename}
                  aria-label={`${label}: ${file.filename}`}
                  className="flex min-w-0 flex-1 items-baseline gap-2 hover:underline"
                >
                  {content}
                </Link>
              ) : (
                <span
                  className="flex min-w-0 flex-1 items-baseline gap-2"
                  title={change?.path ?? undefined}
                >
                  {content}
                </span>
              )}
              {editing && kind !== "moldflow" ? (
                <>
                  <Button
                    type="button"
                    size="icon"
                    variant="outline"
                    className="size-7 shrink-0"
                    title={`${present ? "Cambiar" : "Seleccionar"} ${label}`}
                    aria-label={`${present ? "Cambiar" : "Seleccionar"} ${label}`}
                    disabled={saving || picking !== null}
                    onClick={() => void choose(kind)}
                  >
                    {picking === kind ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <FolderOpen className="size-3.5" />
                    )}
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-7 shrink-0 text-destructive"
                    title={`Quitar ${label}`}
                    aria-label={`Quitar ${label}`}
                    disabled={!present || saving || picking !== null}
                    onClick={() => {
                      setError("")
                      onChange({ kind, path: null })
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </>
              ) : file && !editing ? (
                <Button
                  asChild
                  size="icon"
                  variant="outline"
                  className="size-7 shrink-0"
                >
                  <FileLink
                    fileId={file.id}
                    downloadFile
                    title={`Descargar ${file.filename}`}
                  >
                    <Download className="size-3.5" />
                    <span className="sr-only">Descargar {file.filename}</span>
                  </FileLink>
                </Button>
              ) : null}
            </fieldset>
          )
        })}
      </div>
      {!editing && !data.references.length && (
        <p className="text-sm text-muted-foreground">
          Sin archivos vinculados.
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </>
  )
}
