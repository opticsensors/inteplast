import { useQuery } from "@tanstack/react-query"
import { LoaderCircle } from "lucide-react"
import { useState } from "react"

import { type FilePublic, FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import ModelViewer from "./ModelViewer"

/** The original stays downloadable; only the lightweight GLB reaches WebGL. */
export default function WebModelViewer({ file }: { file: FilePublic }) {
  const [retrying, setRetrying] = useState(false)
  const preview = useQuery({
    queryKey: ["file-preview", file.id, file.version],
    queryFn: () => FilesService.preparePreview({ fileId: file.id }),
    refetchInterval: (query) =>
      ["queued", "processing"].includes(query.state.data?.state ?? "")
        ? 2000
        : false,
    refetchOnWindowFocus: false,
    gcTime: 0,
    retry: 1,
  })

  if (preview.data?.state === "ready" && preview.data.url) {
    return (
      <div className="flex flex-col gap-2">
        {preview.data.message && (
          <output className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            {preview.data.message}
          </output>
        )}
        <ModelViewer file={file} previewUrl={preview.data.url} />
      </div>
    )
  }

  const failed = preview.isError || preview.data?.state === "error"
  return (
    <output className="flex h-[70vh] flex-col items-center justify-center gap-3 rounded-lg border bg-muted/30 p-6 text-center">
      {failed ? (
        <>
          <p className="max-w-md text-sm">
            {preview.isError
              ? fileErrorMessage(preview.error)
              : preview.data?.message}
          </p>
          <Button
            variant="outline"
            disabled={retrying}
            onClick={async () => {
              setRetrying(true)
              try {
                await FilesService.preparePreview({
                  fileId: file.id,
                  retry: true,
                })
              } catch {
                // The refreshed query below displays API/source errors.
              } finally {
                await preview.refetch()
                setRetrying(false)
              }
            }}
          >
            Reintentar
          </Button>
        </>
      ) : (
        <>
          <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
          <p>Preparando la vista 3D…</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            La primera vez puede tardar unos minutos. Puedes salir y volver más
            tarde.
          </p>
        </>
      )}
    </output>
  )
}
