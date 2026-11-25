import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { Suspense, useState } from "react"
import {
  CatalogService,
  type FilePublic,
  FilesService,
  type PartCardPublic,
} from "@/client"
import { COVER_SIZE, CoverButton } from "@/components/Features/CoverButton"
import { CoverDialog } from "@/components/Features/CoverDialog"
import { CoverLoading } from "@/components/Features/CoverLoading"
import { FeatureThumbnail } from "@/components/Features/FeatureCard"
import {
  preloadStepViewer,
  StepCoverCanvas,
} from "@/components/Features/lazyStepCoverCanvas"
import { partLabel } from "@/components/Features/parts"
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useCatalogCover } from "@/hooks/useCatalogCover"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { usePrepareCover } from "@/hooks/usePrepareCover"
import { cn } from "@/lib/utils"

// Catalogue thumbnails share one worker/WebGL slot, even when several cards mount together.
let queue: Promise<unknown> = Promise.resolve()

function usePartImage(part: PartCardPublic) {
  const client = useQueryClient()
  const cad = part.cad
  const generated = useQuery({
    queryKey: [
      "part-cover",
      part.id,
      cad?.id,
      cad?.version,
      part.cad_cache_key,
    ],
    enabled: Boolean(
      (!part.image || part.cover_needs_refresh) &&
        part.cad_cache_key &&
        cad &&
        /\.(step|stp)$/i.test(cad.filename),
    ),
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
              cad_cache_key: part.cad_cache_key,
              source_sha256: sourceHash,
              image_id: uploaded.id,
            },
          })
          client.setQueryData(["features", "catalog", "cover", part.id], {
            cad,
            cad_cache_key: part.cad_cache_key,
            image: saved,
            cover_needs_refresh: false,
          })
          void client.invalidateQueries({
            queryKey: ["parts", "detail", part.id],
          })
          return saved
        })
      queue = job
      return job
    },
  })
  const renderedImage = part.cad_cache_key ? generated.data : undefined
  return {
    image: part.cover_needs_refresh
      ? (renderedImage ?? part.image)
      : (part.image ?? renderedImage),
    loading: generated.isFetching,
    error: generated.error,
    retry: generated.refetch,
  }
}

export function PartThumbnail({
  part,
  className,
  wrapperClassName = "relative shrink-0 self-center",
}: {
  part: PartCardPublic
  className?: string
  wrapperClassName?: string
}) {
  const check = useCatalogCover(part.deferred_cover_part_id)
  const { image, loading, error, retry } = usePartImage({
    ...part,
    ...check.cover,
  })
  return (
    <div
      ref={check.ref}
      className={wrapperClassName}
      title={error ? fileErrorMessage(error) : undefined}
    >
      <FeatureThumbnail
        feature={{ name: partLabel(part), image }}
        className={className}
        fit="contain"
        coverError={check.error || (!image && error)}
        checking={check.checking}
        retryCover={check.error ? check.retry : retry}
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
  const name = partLabel(part)
  usePrepareCover(cad, part.cad_cache_key)
  const fallback = (
    <FeatureThumbnail
      feature={{ name, image }}
      fit="contain"
      className="size-full"
    />
  )
  return (
    <Dialog open={expanded} onOpenChange={setExpanded}>
      <div className={cn("relative shrink-0", COVER_SIZE)}>
        {cad || image ? (
          <DialogTrigger asChild>
            <CoverButton
              image={image}
              onPointerEnter={cad ? preloadStepViewer : undefined}
              onFocus={cad ? preloadStepViewer : undefined}
              name={name}
              className="size-full sm:size-full"
            />
          </DialogTrigger>
        ) : (
          fallback
        )}
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
