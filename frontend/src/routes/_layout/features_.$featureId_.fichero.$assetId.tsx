import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Download, ExternalLink, FileQuestion } from "lucide-react"
import { lazy, Suspense } from "react"

import { ApiError } from "@/client"
import { ASSET_KIND_LABELS } from "@/components/Features/constants"
import { FeatureNotFound } from "@/components/Features/FeatureNotFound"
import { featureQueryOptions } from "@/components/Features/queries"
import { fileAction } from "@/components/Features/viewers"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { fileUrl, formatFileSize } from "@/utils"

/** El visor 3D arrastra three.js y OpenCascade: solo se descarga si hace falta. */
const ModelViewer = lazy(() => import("@/components/Features/ModelViewer"))

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
 *   STEP, IGES) se abre en el visor, que tesela en el propio navegador.
 * - **Bajarlo**: siempre, sea cual sea el formato.
 * - **Saber que necesita**: cuando no hay visor posible —Moldflow, SolidWorks,
 *   CATIA, o un ensamblaje de 247 MB— la pagina lo dice con palabras.
 *
 * 🔴 Lo que no puede hacer, y no hay forma: abrir el Explorador de Windows ni
 * lanzar el programa del PC. El navegador lo tiene prohibido.
 */
function AssetDetail() {
  const { featureId, assetId } = Route.useParams()

  const {
    data: feature,
    isPending,
    isError,
  } = useQuery({
    ...featureQueryOptions(featureId),
    retry: (failureCount, error) => !isNotFound(error) && failureCount < 3,
  })

  if (isPending) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-16 w-1/2" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    )
  }

  if (isError || !feature) return <FeatureNotFound />

  const asset = (feature.assets ?? []).find((item) => item.id === assetId)

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
  const { action, viewer, reason } = fileAction(file)

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
          <h1 className="text-2xl font-bold tracking-tight">{asset.name}</h1>
          <p className="text-sm text-muted-foreground">
            {ASSET_KIND_LABELS[asset.kind]}
            {file && ` · ${file.filename} · ${formatFileSize(file.size)}`}
          </p>
        </div>

        {file && (
          <div className="flex shrink-0 items-center gap-2">
            {viewer === "pdf" && (
              <Button variant="outline" size="sm" asChild>
                <a
                  href={fileUrl(file.id)}
                  target="_blank"
                  rel="noreferrer"
                  title="Abrir el PDF en una pestana nueva"
                >
                  <ExternalLink className="mr-2" />
                  Abrir en pestana
                </a>
              </Button>
            )}
            <Button size="sm" asChild>
              <a href={fileUrl(file.id)} download={file.filename}>
                <Download className="mr-2" />
                Descargar
              </a>
            </Button>
          </div>
        )}
      </div>

      {!file ? (
        <EmptyState title="Sin fichero subido">
          <p>
            El adjunto esta declarado en la ficha, pero nadie ha subido todavia
            el fichero. Se sube desde <em>Editar</em>, en la ficha del feature.
          </p>
        </EmptyState>
      ) : action === "download" ? (
        <EmptyState title="Este formato no se puede ver en el navegador">
          <p>
            {reason ? `${reason[0].toUpperCase()}${reason.slice(1)}. ` : ""}
            Descargalo y abrelo desde la barra de descargas: Windows lo abrira
            con el programa que tenga asociado.
          </p>
        </EmptyState>
      ) : viewer === "pdf" ? (
        <iframe
          src={fileUrl(file.id)}
          title={asset.name}
          className="h-[75vh] w-full rounded-lg border"
        />
      ) : viewer === "image" ? (
        <div className="flex justify-center rounded-lg border bg-muted/30 p-4">
          <img
            src={fileUrl(file.id)}
            alt={asset.name}
            className="max-h-[75vh] object-contain"
          />
        </div>
      ) : (
        <Suspense
          fallback={<Skeleton className="h-[70vh] w-full rounded-lg" />}
        >
          <ModelViewer file={file} />
        </Suspense>
      )}
    </div>
  )
}
