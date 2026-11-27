import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FileQuestion } from "lucide-react"
import { lazy, Suspense } from "react"

import { ApiError, FeaturesService } from "@/client"
import { FeatureNotFound } from "@/components/Features/FeatureNotFound"
import { assetName, partName } from "@/components/Features/parts"
import { featureQueryOptions } from "@/components/Features/queries"
import { SourceFilePicker } from "@/components/Features/SourceFilePicker"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
import {
  AttachmentHeader,
  EditAttachmentLink,
  isFolderAttachment,
} from "@/components/Parts/AttachmentActions"
import { AttachmentDetail } from "@/components/Parts/AttachmentGallery"
import { PartCadViewer } from "@/components/Parts/PartCadViewer"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  fileErrorMessage,
  useDocumentStatus,
  useFileAccess,
} from "@/hooks/useFileAccess"

/** El visor 3D arrastra three.js y OpenCascade: solo se descarga si hace falta. */
const ModelViewer = lazy(() => import("@/components/Features/ModelViewer"))
const WebModelViewer = lazy(
  () => import("@/components/Features/WebModelViewer"),
)
const PdfViewer = lazy(() => import("@/components/Features/DrawingSearch"))

export const Route = createFileRoute(
  "/_layout/features_/$featureId_/fichero/$assetId",
)({
  component: AssetDetail,
  validateSearch: (search: Record<string, unknown>): { cota?: string } => ({
    cota: typeof search.cota === "string" ? search.cota : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "Fichero - INTEPLAST",
      },
    ],
  }),
})

const isNotFound = (error: Error) =>
  error instanceof ApiError && error.status === 404

/** Caja gris con un icono y una explicacion. Los tres casos sin visor. */
function EmptyState({
  title,
  children,
}: {
  title: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border bg-muted/30 py-16 text-center">
      <FileQuestion className="size-8 text-muted-foreground" />
      <p className="font-medium">{title}</p>
      {children && (
        <div className="max-w-md text-sm text-muted-foreground">{children}</div>
      )}
    </div>
  )
}

function AssetDetail() {
  const { featureId, assetId } = Route.useParams()
  const { cota } = Route.useSearch()
  const queryClient = useQueryClient()

  const {
    data: feature,
    isPending,
    isError,
  } = useQuery({
    ...featureQueryOptions(featureId),
    retry: (failureCount, error) => !isNotFound(error) && failureCount < 3,
  })
  const asset = (feature?.assets ?? []).find((item) => item.id === assetId)
  const folderAttachment = isFolderAttachment(asset?.kind)
  const step =
    asset?.kind === "part" && /\.(stp|step)$/i.test(asset.file?.filename ?? "")
  const access = useFileAccess(
    folderAttachment || step ? undefined : asset?.file?.id,
  )
  const status = useDocumentStatus(
    folderAttachment || step ? null : asset?.file,
  )

  if (isPending) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-16 w-1/2" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    )
  }

  if (isError || !feature) return <FeatureNotFound />

  if (!asset) {
    return (
      <EmptyState title="Este fichero ya no esta en la ficha">
        <p>Puede que se haya borrado.</p>
      </EmptyState>
    )
  }

  const file = asset.file
  const name = assetName(asset)
  const sourcePicker = file?.source === "local" && (
    <SourceFilePicker
      document={file}
      editIcon
      initialPath={asset.part?.folder_path ?? ""}
      onLinked={async (linked) => {
        await FeaturesService.updateFeatureAsset({
          assetId: asset.id,
          requestBody: { file_id: linked.id, name: linked.filename },
        })
        await queryClient.invalidateQueries({ queryKey: ["features"] })
      }}
    />
  )
  if ((file || asset.part) && isFolderAttachment(asset.kind)) {
    const context = [
      feature.name,
      asset.part?.code,
      asset.part && partName(asset.part),
    ]
      .filter(Boolean)
      .join(" · ")
    return (
      <AttachmentDetail
        key={`${asset.part?.id ?? file?.id}:${asset.kind}`}
        kind={asset.kind}
        file={file}
        partId={asset.part?.id}
        context={context}
        sourcePicker={sourcePicker}
      />
    )
  }
  const { action, viewer, reason } = fileAction(file)
  const unavailable =
    file?.source === "local" &&
    (status.isError || (status.data && status.data.state !== "available"))

  return (
    <div className="flex flex-col gap-4">
      <AttachmentHeader
        kind={asset.kind}
        file={file}
        partId={asset.part?.id}
        context={[
          feature.name,
          asset.part?.code,
          asset.part && partName(asset.part),
        ]
          .filter(Boolean)
          .join(" · ")}
        title={name}
      >
        {asset.part ? (
          <EditAttachmentLink partId={asset.part.id} />
        ) : (
          sourcePicker
        )}
      </AttachmentHeader>

      {!file ? (
        <EmptyState title="Sin archivo vinculado">
          <p>Los archivos se gestionan en la ficha de la pieza.</p>
          {asset.part && (
            <Button variant="link" asChild>
              <Link to="/parts/$partId" params={{ partId: asset.part.id }}>
                Abrir pieza {asset.part.code}
              </Link>
            </Button>
          )}
        </EmptyState>
      ) : unavailable ? (
        <EmptyState
          title={
            status.data?.state === "changed"
              ? "El original ha cambiado"
              : "Archivo no disponible"
          }
        >
          <p>
            {status.isError
              ? fileErrorMessage(status.error)
              : status.data?.message}
          </p>
          <Button
            onClick={() => {
              void status.refetch()
              void access.refetch()
            }}
          >
            Comprobar de nuevo
          </Button>
        </EmptyState>
      ) : access.isError ? (
        <EmptyState title="No se ha podido abrir el archivo">
          <p>{fileErrorMessage(access.error)}</p>
          <Button onClick={() => void access.refetch()}>Reintentar</Button>
        </EmptyState>
      ) : action === "download" ? (
        <EmptyState title="Este formato no se puede ver en el navegador">
          <p>
            {reason ? `${reason[0].toUpperCase()}${reason.slice(1)}. ` : ""}
            Consulta el original en su aplicación de origen.
          </p>
        </EmptyState>
      ) : step ? (
        <PartCadViewer file={file} />
      ) : !access.url ? (
        <Skeleton className="h-[70vh] w-full rounded-lg" />
      ) : viewer === "pdf" ? (
        <Suspense
          fallback={<Skeleton className="h-[75vh] w-full rounded-lg" />}
        >
          <PdfViewer
            initialQuery={cota}
            key={`${file.id}:${file.version}`}
            file={file}
            title={name}
          />
        </Suspense>
      ) : viewer === "image" ? (
        <div className="flex justify-center rounded-lg border bg-muted/30 p-4">
          <img
            src={access.url}
            alt={name}
            className="max-h-[75vh] object-contain"
          />
        </div>
      ) : (
        <Suspense
          fallback={<Skeleton className="h-[70vh] w-full rounded-lg" />}
        >
          {usesWebPreview(file) ? (
            <WebModelViewer
              key={`${file.id}:${file.version}`}
              file={file}
              showCadEdges={asset.kind === "part"}
            />
          ) : (
            <ModelViewer
              key={`${file.id}:${file.version}`}
              file={file}
              showCadEdges={asset.kind === "part"}
            />
          )}
        </Suspense>
      )}
    </div>
  )
}
