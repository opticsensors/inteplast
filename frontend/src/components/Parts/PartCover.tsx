import { Loader2 } from "lucide-react"
import { Suspense, useState } from "react"
import type { PartCardPublic } from "@/client"
import { FaceReviewList } from "@/components/Catalog/CatalogWarnings"
import { COVER_SIZE, CoverButton } from "@/components/Features/CoverButton"
import { CoverDialog } from "@/components/Features/CoverDialog"
import { CoverLoading } from "@/components/Features/CoverLoading"
import { CAD_COVER_BACKGROUND } from "@/components/Features/cadCover"
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
import { useFaceImage } from "@/hooks/useFaceImage"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { useGrayImage } from "@/hooks/useGrayImage"
import { usePrepareCover } from "@/hooks/usePrepareCover"
import { cn } from "@/lib/utils"

export function PartThumbnail({
  part,
  className,
  wrapperClassName = "relative shrink-0 self-center",
}: {
  part: PartCardPublic
  className?: string
  wrapperClassName?: string
}) {
  const check = useCatalogCover(
    part.deferred_cover_part_id ?? (part.has_face_marks ? part.id : undefined),
  )
  const { image, loading, error, retry } = useGrayImage({
    ...part,
    ...check.cover,
  })
  const colored = useFaceImage(part.id, check.settledCover)
  return (
    <div
      ref={check.ref}
      className={wrapperClassName}
      title={error ? fileErrorMessage(error) : undefined}
    >
      <FeatureThumbnail
        feature={{ name: partLabel(part), image: colored.image ?? image }}
        className={className}
        fit="contain"
        coverError={check.error || colored.error || (!image && error)}
        checking={check.checking}
        retryCover={
          check.error ? check.retry : colored.error ? colored.retry : retry
        }
      />
      {(loading || colored.loading) && (
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
  const gray = useGrayImage(part)
  const check = useCatalogCover(part.has_face_marks ? part.id : undefined, true)
  const colors = check.settledCover?.face_colors
  const colored = useFaceImage(part.id, check.settledCover)
  const image = colored.image ?? gray.image
  const loading = gray.loading || colored.loading
  const cad =
    part.cad && /\.(step|stp)$/i.test(part.cad.filename) ? part.cad : undefined
  const name = partLabel(part)
  usePrepareCover(cad, part.cad_cache_key)
  const fallback = (
    <FeatureThumbnail
      feature={{ name, image }}
      fit="contain"
      className="size-full"
      style={{ backgroundColor: CAD_COVER_BACKGROUND }}
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
          <FeatureThumbnail feature={{ name, image }} className="size-full" />
        )}
        {loading && (
          <Loader2
            aria-label="Preparando portada"
            className="absolute bottom-2 left-2 size-4 animate-spin text-muted-foreground"
          />
        )}
      </div>
      <div className="order-last empty:hidden lg:col-span-2">
        <FaceReviewList review={colors?.review} />
      </div>
      {expanded && (
        <CoverDialog aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="pr-6">{name}</DialogTitle>
          </DialogHeader>
          <div data-slot="cover-surface" className="relative min-h-0 w-full">
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
                  layers={colors?.layers}
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
