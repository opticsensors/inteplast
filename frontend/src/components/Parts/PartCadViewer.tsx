import { lazy, type ReactNode, Suspense } from "react"
import type { FilePublic, PartCardPublic } from "@/client"
import { CoverLoading } from "@/components/Features/CoverLoading"
import { FeatureThumbnail } from "@/components/Features/FeatureCard"
import { StepCoverCanvas } from "@/components/Features/lazyStepCoverCanvas"
import { usesWebPreview } from "@/components/Features/viewers"
import { useCatalogCover } from "@/hooks/useCatalogCover"
import { cn } from "@/lib/utils"

const WebModelViewer = lazy(
  () => import("@/components/Features/WebModelViewer"),
)

/** A part's STEP opens with the same prepared geometry from the cover and from Archivos. */
export function PartCadViewer({
  file,
  part,
  fallback,
  className,
}: {
  file: FilePublic
  part?: PartCardPublic
  fallback?: ReactNode
  className?: string
}) {
  const primary = part?.cad?.id === file.id && part.cad.version === file.version
  const cover = useCatalogCover(
    primary && part?.has_face_marks ? part.id : undefined,
    true,
  )
  const image =
    fallback ??
    (primary && part?.image && (
      <FeatureThumbnail
        feature={{ name: file.filename, image: part.image }}
        className="size-full"
        fit="contain"
        cadBackground
      />
    ))
  return (
    <div className={cn("relative h-[70vh] w-full", className)}>
      <Suspense
        fallback={
          <>
            {image}
            <CoverLoading />
          </>
        }
      >
        {usesWebPreview(file) ? (
          <WebModelViewer file={file} showCadEdges />
        ) : (
          <StepCoverCanvas
            key={file.id}
            file={file}
            wholePart
            layers={cover.settledCover?.face_colors?.layers}
            fallback={image}
            className="size-full"
          />
        )}
      </Suspense>
    </div>
  )
}
