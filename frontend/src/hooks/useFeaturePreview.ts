import type { FilePublic } from "@/client"
import { useCatalogCover } from "./useCatalogCover"
import { useFaceImage } from "./useFaceImage"
import { useGrayImage } from "./useGrayImage"

/** A marked capture may be an old red PNG. Only use that archive when the
 * checked CAD has no current layer for this feature (e.g. a revision). */
export function useFeaturePreview({
  featureId,
  markedPartId,
  deferredPartId,
  original,
  immediate = false,
}: {
  featureId?: string
  markedPartId?: string | null
  deferredPartId?: string | null
  original?: FilePublic | null
  immediate?: boolean
}) {
  const check = useCatalogCover(markedPartId ?? deferredPartId, immediate)
  const cover = check.settledCover
  const colored = useFaceImage(
    markedPartId ?? undefined,
    markedPartId ? cover : undefined,
    featureId,
  )
  const gray = useGrayImage({
    ...(!markedPartId && !original && deferredPartId ? cover : undefined),
    id: deferredPartId ?? "",
  })
  const needsColor = markedPartId && (!cover || colored.hasLayer)
  const colorError = needsColor && !colored.image ? colored.error : null
  const grayError =
    !markedPartId && !original && !gray.image ? gray.error : null
  return {
    ref: check.ref,
    image: needsColor ? colored.image : (original ?? gray.image),
    review: featureId && cover?.face_colors?.review[featureId],
    checking: check.checking || colored.loading || gray.loading,
    error: check.error ?? colorError ?? grayError,
    retry: check.error
      ? check.retry
      : colorError
        ? colored.retry
        : grayError
          ? gray.retry
          : check.retry,
  }
}
