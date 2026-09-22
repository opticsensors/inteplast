import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { lazy, Suspense, useState } from "react"
import {
  CatalogService,
  type FilePublic,
  FilesService,
  type PartCardPublic,
} from "@/client"
import { CoverButton } from "@/components/Features/CoverButton"
import { CoverDialog } from "@/components/Features/CoverDialog"
import { CoverLoading } from "@/components/Features/CoverLoading"
import { FeatureThumbnail } from "@/components/Features/FeatureCard"
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { fileErrorMessage } from "@/hooks/useFileAccess"

const StepCoverCanvas = lazy(
  () => import("@/components/Features/StepCoverCanvas"),
)
// Catalogue thumbnails share one worker/WebGL slot, even when several cards mount together.
let queue: Promise<unknown> = Promise.resolve()

function usePartImage(part: PartCardPublic) {
  const client = useQueryClient()
  const cad = part.cad
  const generated = useQuery({
    queryKey: ["part-cover", part.id, cad?.id, cad?.version],
    enabled: Boolean(!part.image && cad && /\.(step|stp)$/i.test(cad.filename)),
    staleTime: Infinity,
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: ({ signal }): Promise<FilePublic> => {
      const job = queue
        .catch(() => undefined)
        .then(async () => {
          signal.throwIfAborted()
          const { capturePartCad } = await import("./capturePartCad")
          const { image, sourceHash } = await capturePartCad(cad!, signal)
          const uploaded = await FilesService.uploadFile({
            formData: {
              file: new File([image], "pieza-cad.png", { type: "image/png" }),
            },
          })
          signal.throwIfAborted()
          const saved = await CatalogService.savePartCover({
            partId: part.id,
            requestBody: {
              file_id: cad!.id,
              file_version: cad!.version,
              source_sha256: sourceHash,
              image_id: uploaded.id,
            },
          })
          void client.invalidateQueries({ queryKey: ["features", "catalog"] })
          void client.invalidateQueries({
            queryKey: ["parts", "detail", part.id],
          })
          return saved
        })
      queue = job
      return job
    },
  })
  return {
    image: part.image ?? generated.data,
    loading: generated.isFetching,
    error: generated.error,
  }
}

export function PartThumbnail({
  part,
  className,
}: {
  part: PartCardPublic
  className?: string
}) {
  const { image, loading, error } = usePartImage(part)
  return (
    <div
      className="relative shrink-0 self-center"
      title={error ? fileErrorMessage(error) : undefined}
    >
      <FeatureThumbnail
        feature={{ name: part.name ?? part.code, image }}
        className={className}
        fit="contain"
      />
      {loading && (
        <Loader2
          aria-label="Preparando portada"
          className="absolute bottom-2 right-2 size-4 animate-spin text-muted-foreground"
        />
      )}
    </div>
  )
}

export function PartCover({ part }: { part: PartCardPublic }) {
  const [expanded, setExpanded] = useState(false)
  const { image, loading } = usePartImage(part)
  const cad =
    part.cad && /\.(step|stp)$/i.test(part.cad.filename) ? part.cad : undefined
  const name = part.name ?? part.code
  const fallback = (
    <FeatureThumbnail
      feature={{ name, image }}
      fit="contain"
      className="size-full"
    />
  )
  if (!cad && !image)
    return (
      <FeatureThumbnail
        feature={{ name, image }}
        className="size-32 sm:size-48"
      />
    )
  return (
    <Dialog open={expanded} onOpenChange={setExpanded}>
      <div className="relative shrink-0">
        <DialogTrigger asChild>
          <CoverButton image={image} name={name} />
        </DialogTrigger>
        {loading && (
          <Loader2
            aria-label="Preparando portada"
            className="absolute bottom-2 left-2 size-4 animate-spin text-muted-foreground"
          />
        )}
      </div>
      {expanded && (
        <CoverDialog aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="pr-6">{name}</DialogTitle>
          </DialogHeader>
          <div
            data-slot="cover-surface"
            className="relative size-[var(--cover-size)]"
          >
            {cad ? (
              <Suspense
                fallback={
                  <>
                    {fallback}
                    <CoverLoading />
                  </>
                }
              >
                <StepCoverCanvas
                  file={cad}
                  fallback={fallback}
                  className="size-full"
                  wholePart
                />
              </Suspense>
            ) : (
              fallback
            )}
          </div>
        </CoverDialog>
      )}
    </Dialog>
  )
}
