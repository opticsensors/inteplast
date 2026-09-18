import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Download, ExternalLink, FileQuestion } from "lucide-react"
import { lazy, Suspense } from "react"

import { ApiError, FeaturesService } from "@/client"
import { FeatureNotFound } from "@/components/Features/FeatureNotFound"
import { assetName } from "@/components/Features/parts"
import { featureQueryOptions } from "@/components/Features/queries"
import { SourceFilePicker } from "@/components/Features/SourceFilePicker"
import { fileAction, usesWebPreview } from "@/components/Features/viewers"
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
const PdfViewer = lazy(() => import("@/components/Features/PdfViewer"))

export const Route = createFileRoute(
  "/_layout/features_/$featureId_/fichero/$assetId",
)({
  component: AssetDetail,
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

/**
 * La pagina de un fichero. Un solo destino para las tres cosas que se pueden
 * querer hacer con un adjunto:
 *
 * - **Verlo**: el plano PDF y las imagenes se pintan aqui; el 3D (STL, GLB,
 *   STEP, IGES) se abre en el visor; STL/STEP grandes usan un GLB del servidor.
 * - **Bajarlo**: siempre, sea cual sea el formato.
 * - **Saber que necesita**: cuando no hay visor posible —Moldflow, SolidWorks,
 *   CATIA— la pagina lo dice con palabras.
 *
 * La aplicacion no integra el Explorador de Windows ni lanzadores de programas
 * locales; el usuario abre la descarga con la aplicacion que tenga asociada.
 */
function AssetDetail() {
  const { featureId, assetId } = Route.useParams()
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
  const access = useFileAccess(asset?.file?.id)
  const status = useDocumentStatus(asset?.file)

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
        <p>
          Puede que se haya borrado.{" "}
          <Link
            to="/features/$featureId"
            params={{ featureId }}
            className="underline"
          >
            Volver a {feature.name}
          </Link>
        </p>
      </EmptyState>
    )
  }

  const file = asset.file
  const name = assetName(asset)
  const { action, viewer, reason } = fileAction(file)
  const unavailable =
    file?.source === "local" &&
    (status.isError || (status.data && status.data.state !== "available"))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {/* Migas: de donde viene y de que pieza es. No es un boton Volver,
              es saber donde estas. */}
          <p className="text-sm text-muted-foreground">
            <Link
              to="/features/$featureId"
              params={{ featureId }}
              className="hover:underline"
            >
              {feature.name}
            </Link>
            {asset.part && (
              <>
                {" · "}
                <span className="font-mono">{asset.part.code}</span>
                {asset.part.name && ` ${asset.part.name}`}
              </>
            )}
          </p>
          <h1 className="break-words text-2xl font-bold tracking-tight">
            {name}
          </h1>
        </div>

        {file && (
          <div className="flex shrink-0 items-center gap-2">
            {file.source === "local" && (
              <SourceFilePicker
                document={file}
                initialPath={asset.part?.folder_path ?? ""}
                onLinked={async (linked) => {
                  await FeaturesService.updateFeatureAsset({
                    assetId: asset.id,
                    requestBody: { file_id: linked.id, name: linked.filename },
                  })
                  await queryClient.invalidateQueries({
                    queryKey: ["features"],
                  })
                }}
              />
            )}
            {viewer === "pdf" && access.url && !unavailable && (
              <Button variant="outline" size="sm" asChild>
                <a
                  href={access.url}
                  target="_blank"
                  rel="noreferrer"
                  title="Abrir el PDF en una pestana nueva"
                >
                  <ExternalLink className="mr-2" />
                  Abrir en pestana
                </a>
              </Button>
            )}
            {access.downloadUrl && !unavailable && (
              <Button size="sm" asChild>
                <a href={access.downloadUrl} download={file.filename}>
                  <Download className="mr-2" />
                  Descargar
                </a>
              </Button>
            )}
          </div>
        )}
      </div>

      {!file ? (
        <EmptyState title="Sin archivo vinculado">
          <p>
            El adjunto está declarado en la ficha. Puedes vincular un archivo
            existente desde <em>Editar</em>, en la ficha del feature.
          </p>
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
            Descargalo y abrelo desde la barra de descargas: Windows lo abrira
            con el programa que tenga asociado.
          </p>
        </EmptyState>
      ) : !access.url ? (
        <Skeleton className="h-[70vh] w-full rounded-lg" />
      ) : viewer === "pdf" ? (
        <Suspense
          fallback={<Skeleton className="h-[75vh] w-full rounded-lg" />}
        >
          <PdfViewer
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
            <WebModelViewer key={`${file.id}:${file.version}`} file={file} />
          ) : (
            <ModelViewer key={`${file.id}:${file.version}`} file={file} />
          )}
        </Suspense>
      )}
    </div>
  )
}
