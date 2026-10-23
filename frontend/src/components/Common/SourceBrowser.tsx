import { useQuery } from "@tanstack/react-query"
import { ChevronRight, File, Folder, Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { FilesService, type SourceEntry } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { useLoginMethods } from "@/hooks/useLoginMethods"
import { registerSourceBrowser, type SourcePick } from "@/lib/sourcePicker"
import { formatFileSize } from "@/utils"

const PAGE = 200

async function listAll(path: string, directoriesOnly: boolean) {
  const entries: SourceEntry[] = []
  for (;;) {
    const page = await FilesService.listSource({
      path,
      skip: entries.length,
      limit: PAGE,
      directoriesOnly,
    })
    entries.push(...page.entries)
    if (!page.entries.length || entries.length >= page.count) return entries
  }
}

/**
 * The folder and file picker of the SharePoint source, replacing the Windows
 * dialog that only reaches the local folder. Paths are relative to the root.
 */
export function SourceBrowser() {
  const [pick, setPick] = useState<SourcePick | null>(null)
  const [path, setPath] = useState("")
  const resolver = useRef<((path: string | null) => void) | null>(null)
  const { data: methods } = useLoginMethods()

  const finish = (value: string | null) => {
    resolver.current?.(value)
    resolver.current = null
    setPick(null)
  }

  useEffect(() => {
    registerSourceBrowser(
      (request) =>
        new Promise((resolve) => {
          resolver.current?.(null)
          resolver.current = resolve
          setPath(request.start ?? "")
          setPick(request)
        }),
    )
    return () => registerSourceBrowser(null)
  }, [])

  useEffect(() => {
    const signal = pick?.signal
    if (!signal) return
    const cancel = () => {
      resolver.current?.(null)
      resolver.current = null
      setPick(null)
    }
    signal.addEventListener("abort", cancel, { once: true })
    return () => signal.removeEventListener("abort", cancel)
  }, [pick])

  const folders = pick?.kind === "folder"
  const listing = useQuery({
    queryKey: ["source-browser", path, folders],
    queryFn: () => listAll(path, folders),
    enabled: pick !== null,
    retry: false,
  })
  const segments = path ? path.split("/") : []
  const root = methods?.source_name ?? "Origen"

  return (
    <Dialog open={pick !== null} onOpenChange={(open) => !open && finish(null)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {folders ? "Elegir carpeta" : "Elegir archivo"}
          </DialogTitle>
          <DialogDescription>{root} · SharePoint</DialogDescription>
        </DialogHeader>
        <nav
          aria-label="Carpeta actual"
          className="flex min-w-0 flex-wrap items-center gap-1 text-sm"
        >
          {[root, ...segments].map((name, index) => (
            <span key={`${index}-${name}`} className="flex items-center gap-1">
              {index > 0 && (
                <ChevronRight className="size-3.5 text-muted-foreground" />
              )}
              <button
                type="button"
                className="rounded px-1 hover:bg-muted disabled:font-medium disabled:hover:bg-transparent"
                disabled={index === segments.length}
                onClick={() => setPath(segments.slice(0, index).join("/"))}
              >
                {name}
              </button>
            </span>
          ))}
        </nav>
        <div className="max-h-80 min-h-32 overflow-y-auto rounded-md border">
          {listing.isPending ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : listing.isError ? (
            <p role="alert" className="p-3 text-sm text-destructive">
              {fileErrorMessage(listing.error)}
            </p>
          ) : listing.data.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">
              {folders ? "No hay subcarpetas." : "Carpeta vacía."}
            </p>
          ) : (
            <ul className="divide-y">
              {listing.data.map((entry) => (
                <li key={entry.path}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-muted"
                    onClick={() =>
                      entry.directory ? setPath(entry.path) : finish(entry.path)
                    }
                  >
                    {entry.directory ? (
                      <Folder className="size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <File className="size-4 shrink-0 text-muted-foreground" />
                    )}
                    <span className="min-w-0 flex-1 truncate">
                      {entry.name}
                    </span>
                    {!entry.directory && entry.size != null && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatFileSize(entry.size)}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">
              Cancelar
            </Button>
          </DialogClose>
          {folders && (
            <Button type="button" disabled={!path} onClick={() => finish(path)}>
              Elegir esta carpeta
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
