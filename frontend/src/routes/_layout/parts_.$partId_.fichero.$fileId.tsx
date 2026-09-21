import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { lazy, Suspense } from "react"
import { EvidenceService } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
import { DrawingToggle } from "@/components/Parts/DrawingToggle"
import { Button } from "@/components/ui/button"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"

const DrawingSearch = lazy(() => import("@/components/Features/DrawingSearch"))
const ModelViewer = lazy(() => import("@/components/Features/ModelViewer"))
const WebModelViewer = lazy(
  () => import("@/components/Features/WebModelViewer"),
)
export const Route = createFileRoute(
  "/_layout/parts_/$partId_/fichero/$fileId",
)({
  component: PartFile,
  validateSearch: (s: Record<string, unknown>): { cota?: string } => ({
    cota: typeof s.cota === "string" ? s.cota : undefined,
  }),
})
function PartFile() {
  const { partId, fileId } = Route.useParams()
  const { cota } = Route.useSearch()
  const navigate = useNavigate()
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
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold tracking-tight">
          <span className="mr-3 font-mono">{result.data?.part.code}</span>
          {result.data?.part.name}
        </h1>
        <Suspense
          fallback={
            <p className="text-sm text-muted-foreground">Cargando plano…</p>
          }
        >
          <DrawingSearch
            file={file}
            title={file.filename}
            initialQuery={cota}
            searchAction={
              <DrawingToggle
                active
                onClick={() =>
                  void navigate({
                    to: "/parts/$partId",
                    params: { partId },
                    search: { cota },
                    replace: true,
                    resetScroll: false,
                  })
                }
              />
            }
          />
        </Suspense>
      </div>
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
