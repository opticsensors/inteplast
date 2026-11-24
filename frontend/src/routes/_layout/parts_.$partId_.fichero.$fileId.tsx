import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { ExternalLink } from "lucide-react"
import { lazy, Suspense } from "react"
import { CatalogService, EvidenceService } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { partLabel } from "@/components/Features/parts"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
import {
  AttachmentDetail,
  isFolderAttachment,
  SharePointFolders,
} from "@/components/Parts/AttachmentActions"
import { consultationScope } from "@/components/Parts/consultationEntries"
import { validatePartSearch } from "@/components/Parts/measurementSelection"
import { guessFileKind, savedFiles } from "@/components/Parts/pieceFileDrafts"
import { Button } from "@/components/ui/button"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"

const ModelViewer = lazy(() => import("@/components/Features/ModelViewer"))
const WebModelViewer = lazy(
  () => import("@/components/Features/WebModelViewer"),
)
const DrawingSearch = lazy(() => import("@/components/Features/DrawingSearch"))
const SourceTableViewer = lazy(
  () => import("@/components/Parts/SourceTableViewer"),
)
export const Route = createFileRoute(
  "/_layout/parts_/$partId_/fichero/$fileId",
)({
  component: PartFile,
  validateSearch: validatePartSearch,
  head: () => ({ meta: [{ title: "Fichero - INTEPLAST" }] }),
})
function PartFile() {
  const { partId, fileId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = useNavigate()
  const detail = useQuery({
    queryKey: ["parts", "detail", partId],
    queryFn: () => CatalogService.readPartDetail({ partId }),
  })
  const attachment = savedFiles(detail.data).find(
    (item) => item.file_id === fileId,
  )
  const result = useQuery({
    queryKey: ["part-evidence", partId, search.revision, search.snapshot, ""],
    enabled: detail.isSuccess && !isFolderAttachment(attachment?.kind),
    queryFn: () =>
      EvidenceService.readPartEvidence({
        partId,
        revision: search.revision,
        snapshotId: search.snapshot,
        cota: "",
      }),
  })
  const file =
    attachment?.file ?? result.data?.documents.find((f) => f.id === fileId)
  const kind = attachment?.kind ?? guessFileKind(file?.filename ?? "")
  const access = useFileAccess(isFolderAttachment(kind) ? undefined : file?.id)
  if (detail.isPending) return <p>Cargando documento…</p>
  if (detail.error) return <p role="alert">{fileErrorMessage(detail.error)}</p>
  if (file && isFolderAttachment(kind)) {
    return (
      <AttachmentDetail
        key={`${file.id}:${file.version}`}
        kind={kind}
        file={file}
        partId={partId}
        name={attachment?.name || file.filename}
        context={partLabel(detail.data.part)}
      />
    )
  }
  if (result.isPending) return <p>Cargando documento…</p>
  if (result.error) return <p role="alert">{fileErrorMessage(result.error)}</p>
  if (!file) return <p>Documento no encontrado en esta pieza.</p>
  const { viewer, action } = fileAction(file)
  const table = /\.(csv|xlsx?)$/i.test(file.filename)
  const displayName = attachment?.name || file.filename
  const scope = consultationScope(result.data?.features ?? [], search)
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        {result.data ? partLabel(result.data.part) : ""}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold tracking-tight">
            {displayName}
          </h1>
          {displayName !== file.filename && (
            <p className="break-words text-sm text-muted-foreground">
              {file.filename}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {kind === "drawing" ? (
            <SharePointFolders kind={kind} />
          ) : (
            viewer === "pdf" &&
            access.url && (
              <Button asChild size="sm" variant="outline">
                <a href={access.url} target="_blank" rel="noreferrer">
                  <ExternalLink className="mr-2" />
                  Abrir en pestaña
                </a>
              </Button>
            )
          )}
          {viewer !== "pdf" && (
            <Button asChild size="sm" variant="outline">
              <FileLink fileId={file.id} downloadFile>
                Descargar original
              </FileLink>
            </Button>
          )}
        </div>
      </div>
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Cargando visor…</p>
        }
      >
        {table ? (
          <SourceTableViewer
            key={`${file.id}:${file.version}`}
            fileId={file.id}
            version={file.version}
            query={search.sourceQ ?? search.sourceLocator ?? ""}
            locator={search.sourceLocator}
            cavity={search.sourceCavity}
            value={search.sourceValue}
            onQuery={(sourceQ) =>
              void navigate({
                to: "/parts/$partId/fichero/$fileId",
                params: { partId, fileId },
                search: { ...search, sourceQ },
                replace: true,
                resetScroll: false,
              })
            }
          />
        ) : action === "view" ? (
          viewer === "pdf" ? (
            <DrawingSearch
              key={`${file.id}:${file.version}`}
              file={file}
              title={displayName}
              initialQuery={search.drawingQ ?? search.cota}
              onQueryChange={(drawingQ) =>
                void navigate({
                  to: "/parts/$partId/fichero/$fileId",
                  params: { partId, fileId },
                  search: { ...search, drawingQ },
                  replace: true,
                  resetScroll: false,
                })
              }
              allowedCotas={
                scope === undefined
                  ? undefined
                  : (scope?.characteristics ?? []).map((cota) => cota.code)
              }
            />
          ) : viewer === "image" ? (
            <img
              src={access.url}
              alt={displayName}
              className="max-h-[75vh] object-contain"
            />
          ) : usesWebPreview(file) ? (
            <WebModelViewer file={file} showCadEdges={kind === "part"} />
          ) : (
            <ModelViewer file={file} showCadEdges={kind === "part"} />
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
