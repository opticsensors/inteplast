import { useQueryClient } from "@tanstack/react-query"
import { FolderOpen, Loader2, Plus, RefreshCw, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import {
  type FolderDiscovery,
  type PartPublic,
  PartsService,
  type ReferenceProposal,
} from "@/client"
import { ASSET_KIND_LABELS } from "@/components/Features/constants"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickNativePath } from "@/lib/nativePicker"

export function PartSetupDialog({
  part,
  onCreated,
  triggerClassName,
}: {
  part?: PartPublic
  onCreated?: (partId: string) => void
  triggerClassName?: string
}) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [folder, setFolder] = useState<FolderDiscovery>()
  const [name, setName] = useState("")
  const [references, setReferences] = useState<ReferenceProposal[]>([])
  const picker = useRef<AbortController | null>(null)
  useEffect(() => () => picker.current?.abort(), [])

  const invalidate = () =>
    Promise.all(
      [
        "parts",
        "part-evidence",
        "metrology-filters",
        "features",
        "measurement-history",
        "feature-evidence",
      ].map((key) => client.invalidateQueries({ queryKey: [key] })),
    )

  const run = async (task: () => Promise<void>) => {
    setBusy(true)
    setError("")
    try {
      await task()
    } catch (error) {
      setError(fileErrorMessage(error))
    } finally {
      setBusy(false)
    }
  }
  const discover = async (path: string) => {
    const data = await PartsService.discoverPartFolder({
      requestBody: { folder_path: path },
    })
    setFolder(data)
    setName(data.name)
    setReferences(data.references)
  }
  const start = () => {
    setOpen(true)
    setFolder(undefined)
    setName("")
    setReferences([])
    setError("")
    if (part)
      void run(async () => {
        if (!part.folder_path)
          throw new Error("Vincula primero la carpeta de esta pieza.")
        await discover(part.folder_path)
      })
  }
  const selectPath = async (kind: "folder" | "file") => {
    const controller = new AbortController()
    picker.current = controller
    try {
      return await pickNativePath(kind, controller.signal)
    } catch (error) {
      if (controller.signal.aborted) return null
      throw error
    } finally {
      picker.current = null
    }
  }
  const chooseFolder = () =>
    void run(async () => {
      const path = await selectPath("folder")
      if (path) await discover(path)
    })
  const chooseFile = (kind: ReferenceProposal["kind"]) =>
    void run(async () => {
      const path = await selectPath("file")
      if (!path) return
      if (!folder || !path.startsWith(`${folder.folder_path}/`))
        throw new Error(
          "Selecciona un archivo dentro de la carpeta de esta pieza.",
        )
      setReferences((items) =>
        items.map((item) =>
          item.kind === kind ? { ...item, path, source_version: null } : item,
        ),
      )
    })
  const save = () =>
    void run(async () => {
      if (!folder) return
      const data = await PartsService.setupPart({
        requestBody: {
          folder_path: folder.folder_path,
          name: name.trim(),
          references: references.map(({ kind, path, source_version }) => ({
            kind,
            path,
            source_version,
          })),
        },
      })
      try {
        await PartsService.refreshPartData({ partId: data.part.id })
      } finally {
        await invalidate()
      }
      setOpen(false)
      if (!part) onCreated?.(data.part.id)
    })
  const close = (value: boolean) => {
    if (!busy) setOpen(value)
  }

  return (
    <>
      <Button
        type="button"
        variant={part ? "outline" : "default"}
        className={triggerClassName}
        onClick={start}
      >
        {part ? <RefreshCw className="size-4" /> : <Plus className="size-4" />}
        {part ? "Actualizar datos" : "Nueva pieza"}
      </Button>
      <Dialog open={open} onOpenChange={close}>
        <DialogContent
          className="h-[36rem] max-h-[90dvh] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden sm:max-w-3xl"
          aria-describedby={undefined}
          showCloseButton={!busy}
          onPointerDownOutside={(event) => event.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>
              {part ? "Actualizar datos" : "Nueva pieza"}
            </DialogTitle>
          </DialogHeader>
          <fieldset
            disabled={busy}
            className="min-h-0 min-w-0 space-y-4 overflow-y-auto"
          >
            {!folder && !part && (
              <Button type="button" variant="outline" onClick={chooseFolder}>
                <FolderOpen className="size-4" />
                Seleccionar carpeta
              </Button>
            )}
            {folder && (
              <>
                <label
                  htmlFor={part ? "update-part-name" : "new-part-name"}
                  className="block space-y-1 text-sm"
                >
                  Nombre de la pieza
                  <Input
                    id={part ? "update-part-name" : "new-part-name"}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </label>
                <div className="space-y-2">
                  {references.map((reference) => (
                    <div
                      key={reference.kind}
                      className="flex flex-wrap items-center gap-2 rounded-md border p-2 text-sm"
                    >
                      <span className="w-16 shrink-0 font-medium">
                        {ASSET_KIND_LABELS[reference.kind]}
                      </span>
                      <p className="min-w-0 flex-1 break-all">
                        {reference.path?.split("/").pop() ?? "Sin archivo"}
                      </p>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        aria-label={`Seleccionar ${ASSET_KIND_LABELS[reference.kind]}`}
                        onClick={() => chooseFile(reference.kind)}
                      >
                        <FolderOpen className="size-3.5" />
                        {reference.path ? "Cambiar" : "Seleccionar"}
                      </Button>
                      {reference.path && (
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="size-8"
                          aria-label={`Quitar ${ASSET_KIND_LABELS[reference.kind]}`}
                          onClick={() =>
                            setReferences((items) =>
                              items.map((item) =>
                                item.kind === reference.kind
                                  ? {
                                      ...item,
                                      path: null,
                                      source_version: null,
                                    }
                                  : item,
                              ),
                            )
                          }
                        >
                          <X className="size-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </fieldset>
          <div className="space-y-3 border-t pt-3">
            <div className="h-10 overflow-y-auto text-sm" aria-live="polite">
              {busy && (
                <output className="flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin" />
                  Cargando…
                </output>
              )}
              {error && (
                <p role="alert" className="text-destructive">
                  {error}
                </p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                onClick={save}
                disabled={busy || !folder || !name.trim()}
              >
                {part ? "Actualizar" : "Crear"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={busy}
                onClick={() => close(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
