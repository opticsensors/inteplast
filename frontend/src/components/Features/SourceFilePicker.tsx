import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, File, Folder, Link2, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"

import { type FilePublic, FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { formatFileSize } from "@/utils"
import { usePendingTask } from "./usePendingTask"

/** A location picker. Closing it never cancels a write already in flight. */
export function SourceFilePicker({
  document,
  onLinked,
  disabled = false,
  compact = false,
  initialPath = "",
}: {
  document?: FilePublic
  onLinked: (file: FilePublic) => Promise<void>
  disabled?: boolean
  compact?: boolean
  initialPath?: string
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const label = document
    ? "Cambiar archivo vinculado"
    : "Vincular archivo existente"
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!busy) setOpen(value)
      }}
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant={compact ? "ghost" : "outline"}
            size={compact ? "icon" : "sm"}
            className={compact ? "size-7 shrink-0" : undefined}
            aria-label={label}
            disabled={disabled}
            onClick={() => setOpen(true)}
          >
            <Link2 className="size-3.5" />
            {!compact && label}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{label}</TooltipContent>
      </Tooltip>
      {open && (
        <DialogContent
          aria-describedby={undefined}
          className="sm:max-w-2xl"
          showCloseButton={!busy}
          onEscapeKeyDown={(event) => {
            if (busy) event.preventDefault()
          }}
          onPointerDownOutside={(event) => event.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>{label}</DialogTitle>
          </DialogHeader>
          <SourceBrowser
            initialPath={initialPath}
            onLinked={onLinked}
            setBusy={setBusy}
            close={() => setOpen(false)}
          />
        </DialogContent>
      )}
    </Dialog>
  )
}

export function SourceBrowser({
  onLinked,
  setBusy,
  close,
  initialPath = "",
  onFolderSelected,
}: {
  onLinked?: (file: FilePublic) => Promise<void>
  initialPath?: string
  onFolderSelected?: (path: string) => Promise<void>
  setBusy: (busy: boolean) => void
  close: () => void
}) {
  const queryClient = useQueryClient()
  const [path, setPath] = useState(initialPath)
  const folderMode = Boolean(onFolderSelected)
  const [skip, setSkip] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState("")
  const listing = useQuery({
    queryKey: ["file-source", path, skip, folderMode],
    queryFn: () =>
      FilesService.listSource({
        path,
        skip,
        limit: 50,
        directoriesOnly: folderMode,
      }),
    retry: false,
  })
  const linking = usePendingTask(async (_: undefined) => {
    if (!folderMode && !selected) return
    setError("")
    try {
      if (onFolderSelected) {
        await onFolderSelected(path)
        close()
        return
      }
      const file = await FilesService.referenceFile({
        requestBody: { path: selected! },
      })
      await onLinked?.(file)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["features"] }),
        queryClient.invalidateQueries({ queryKey: ["file-status"] }),
        queryClient.invalidateQueries({ queryKey: ["file-access"] }),
      ])
      close()
    } catch (failure) {
      setError(fileErrorMessage(failure))
      throw failure
    }
  })
  useEffect(() => {
    setBusy(linking.pending)
    return () => setBusy(false)
  }, [linking.pending, setBusy])
  const navigate = (next: string) => {
    setPath(next)
    setSkip(0)
    setSelected(null)
    setError("")
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={!path || linking.pending}
          onClick={() => navigate(path.split("/").slice(0, -1).join("/"))}
          aria-label="Carpeta superior"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <span className="min-w-0 break-words">
          {listing.data?.name ?? "Archivos de referencia"}
          {path && ` / ${path}`}
        </span>
      </div>
      {listing.isPending ? (
        <output>Leyendo carpeta…</output>
      ) : listing.isError ? (
        <div role="alert" className="space-y-2">
          <p>{fileErrorMessage(listing.error)}</p>
          <Button type="button" onClick={() => void listing.refetch()}>
            Reintentar
          </Button>
        </div>
      ) : !listing.data.configured ? (
        <p>
          La carpeta de referencia todavía no está conectada. Contacta con quien
          administra la aplicación.
        </p>
      ) : (
        <>
          <section
            className="max-h-[40vh] overflow-y-auto rounded-md border"
            aria-label={
              folderMode ? "Carpetas disponibles" : "Archivos disponibles"
            }
          >
            {listing.data.entries.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">
                La carpeta está vacía.
              </p>
            )}
            {listing.data.entries.map((entry) => (
              <button
                key={entry.path}
                type="button"
                disabled={linking.pending}
                aria-pressed={
                  entry.directory ? undefined : selected === entry.path
                }
                onClick={() =>
                  entry.directory
                    ? navigate(entry.path)
                    : setSelected(entry.path)
                }
                className={`flex w-full items-center gap-2 border-b px-3 py-2 text-left text-sm last:border-0 hover:bg-accent ${selected === entry.path ? "bg-accent ring-1 ring-inset ring-primary" : ""}`}
              >
                {entry.directory ? (
                  <Folder className="size-4 shrink-0" />
                ) : (
                  <File className="size-4 shrink-0" />
                )}
                <span className="min-w-0 flex-1 break-words">{entry.name}</span>
                {entry.size != null && (
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatFileSize(entry.size)}
                  </span>
                )}
              </button>
            ))}
          </section>
          {listing.data.count > 50 && (
            <div className="flex items-center justify-between text-sm">
              <Button
                type="button"
                variant="outline"
                disabled={!skip || linking.pending}
                onClick={() => setSkip(skip - 50)}
              >
                Anterior
              </Button>
              <span>
                {skip + 1}–{Math.min(skip + 50, listing.data.count)} de{" "}
                {listing.data.count}
              </span>
              <Button
                type="button"
                variant="outline"
                disabled={skip + 50 >= listing.data.count || linking.pending}
                onClick={() => setSkip(skip + 50)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={linking.pending}
          onClick={close}
        >
          Cancelar
        </Button>
        <Button
          type="button"
          disabled={
            (!folderMode && !selected) ||
            linking.pending ||
            !listing.data?.configured ||
            listing.isError ||
            listing.isPending
          }
          onClick={() => void linking.run(undefined)}
        >
          {linking.pending && <Loader2 className="size-4 animate-spin" />}
          {folderMode ? "Usar esta carpeta" : "Vincular"}
        </Button>
      </div>
    </div>
  )
}
