import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { lazy, Suspense } from "react"
import { CatalogService, EvidenceService } from "@/client"
import { partLabel } from "@/components/Features/parts"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
import {
  AttachmentHeader,
  EditAttachmentLink,
  isFolderAttachment,
} from "@/components/Parts/AttachmentActions"
import { AttachmentDetail } from "@/components/Parts/AttachmentGallery"
import { consultationScope } from "@/components/Parts/consultationEntries"
import { validatePartSearch } from "@/components/Parts/measurementSelection"
import { PartCadViewer } from "@/components/Parts/PartCadViewer"
import { guessFileKind, savedFiles } from "@/components/Parts/pieceFileDrafts"
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
    enabled:
      detail.isSuccess &&
      !isFolderAttachment(attachment?.kind) &&
      attachment?.kind !== "part",
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
  const access = useFileAccess(
    file && !isFolderAttachment(kind) && fileAction(file).viewer === "image"
      ? file.id
      : undefined,
  )
  if (detail.isPending) return <p>Cargando documento…</p>
  if (detail.error) return <p role="alert">{fileErrorMessage(detail.error)}</p>
  if (file && isFolderAttachment(kind)) {
    return (
      <AttachmentDetail
        key={`${file.id}:${file.version}`}
        kind={kind}
        file={file}
        partId={partId}
        context={partLabel(detail.data.part)}
      />
    )
  }
  if (attachment?.kind !== "part" && result.isPending)
    return <p>Cargando documento…</p>
  if (attachment?.kind !== "part" && result.error)
    return <p role="alert">{fileErrorMessage(result.error)}</p>
  if (!file) return <p>Documento no encontrado en esta pieza.</p>
  const { viewer, action } = fileAction(file)
  const table = /\.(csv|xlsx?)$/i.test(file.filename)
  const displayName = attachment?.name || file.filename
  const scope = consultationScope(result.data?.features ?? [], search)
  return (
    <div className="space-y-5">
      <AttachmentHeader
        kind={kind}
        file={file}
        partId={partId}
        context={partLabel(detail.data.part)}
        title={displayName}
        subtitle={displayName !== file.filename ? file.filename : undefined}
      >
        <EditAttachmentLink partId={partId} />
      </AttachmentHeader>
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
          ) : kind === "part" && /\.(step|stp)$/i.test(file.filename) ? (
            <PartCadViewer file={file} part={detail.data.part} />
          ) : usesWebPreview(file) ? (
            <WebModelViewer file={file} showCadEdges={kind === "part"} />
          ) : (
            <ModelViewer file={file} showCadEdges={kind === "part"} />
          )
        ) : (
          <div className="rounded-lg border p-12 text-center text-sm text-muted-foreground">
            Este formato se consulta en su aplicación de origen.
          </div>
        )}
      </Suspense>
    </div>
  )
}
