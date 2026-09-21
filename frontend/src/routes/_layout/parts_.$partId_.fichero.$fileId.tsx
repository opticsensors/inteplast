import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Navigate } from "@tanstack/react-router"
import { lazy, Suspense } from "react"
import { EvidenceService } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
import { validatePartSearch } from "@/components/Parts/measurementSelection"
import { Button } from "@/components/ui/button"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"

const ModelViewer = lazy(() => import("@/components/Features/ModelViewer"))
const WebModelViewer = lazy(
  () => import("@/components/Features/WebModelViewer"),
)
export const Route = createFileRoute(
  "/_layout/parts_/$partId_/fichero/$fileId",
)({
  component: PartFile,
  validateSearch: validatePartSearch,
})
function PartFile() {
  const { partId, fileId } = Route.useParams()
  const search = Route.useSearch()
  const result = useQuery({
    queryKey: ["part-evidence", partId],
    queryFn: () => EvidenceService.readPartEvidence({ partId }),
  })
  const file = result.data?.documents.find((f) => f.id === fileId)
  const access = useFileAccess(file?.id)
  if (result.isPending) return <p>Cargando documento…</p>
  if (result.error) return <p role="alert">{fileErrorMessage(result.error)}</p>
  if (!file) return <p>Documento no encontrado en esta pieza.</p>
  const { viewer, action } = fileAction(file)
  if (viewer === "pdf")
    return (
      <Navigate
        to="/parts/$partId"
        params={{ partId }}
        search={{
          ...search,
          plano: true,
          drawingQ: search.drawingQ ?? search.cota,
          drawingFile: fileId,
        }}
        replace
      />
    )
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        {result.data?.part.code} · {result.data?.part.name}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="break-all text-lg font-semibold">{file.filename}</h1>
        <Button asChild size="sm" variant="outline">
          <FileLink fileId={file.id} downloadFile>
            Descargar original
          </FileLink>
        </Button>
      </div>
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Cargando visor…</p>
        }
      >
        {action === "view" ? (
          viewer === "image" ? (
            <img
              src={access.url}
              alt={file.filename}
              className="max-h-[75vh] object-contain"
            />
          ) : usesWebPreview(file) ? (
            <WebModelViewer file={file} />
          ) : (
            <ModelViewer file={file} />
          )
        ) : (
          <div className="rounded-lg border p-12 text-center text-sm text-muted-foreground">
            Descarga el original para abrirlo en su aplicación.
          </div>
        )}
      </Suspense>
    </div>
  )
}
