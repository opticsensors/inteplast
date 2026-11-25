import { useQuery, useQueryClient } from "@tanstack/react-query"
import { CatalogService, FilesService, type PartCoverPublic } from "@/client"
import { coverQuery } from "./useCatalogCover"

let queue: Promise<unknown> = Promise.resolve()
export function scheduleCapture<T>(work: () => Promise<T>) {
  const job = queue.catch(() => undefined).then(work)
  queue = job
  return job
}

/** Generated PNGs are shared by catalogue, reader and editor. The original capture is preserved. */
export function useFaceImage(
  partId?: string,
  cover?: PartCoverPublic,
  featureId?: string,
) {
  const client = useQueryClient()
  const colors = cover?.face_colors
  const cad = cover?.cad
  const key = featureId ?? "part"
  const image = colors?.images[key]
  const relevant = colors?.layers.some(
    (layer) => !featureId || layer.feature_id === featureId,
  )
  const query = useQuery({
    queryKey: ["face-image", partId, colors?.key, key],
    enabled: Boolean(partId && cad && colors && relevant && !image),
    staleTime: Infinity,
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: ({ signal }) =>
      scheduleCapture(async () => {
        signal.throwIfAborted()
        if (!partId || !cad || !colors)
          throw new Error("Falta el CAD de la pieza.")
        const { capturePartCad } = await import(
          "@/components/Parts/capturePartCad"
        )
        const capture = await capturePartCad(
          cad,
          signal,
          colors.layers,
          featureId,
        )
        const png = await FilesService.uploadFile({
          formData: {
            file: new File([capture.image], "caras-cad.png", {
              type: "image/png",
            }),
          },
        })
        signal.throwIfAborted()
        const saved = await CatalogService.saveFaceImage({
          partId,
          requestBody: {
            file_id: cad.id,
            file_version: cad.version,
            source_sha256: capture.sourceHash,
            geometry_key: capture.geometryKey,
            render_key: colors.key,
            image_id: png.id,
            feature_id: capture.featureId,
          },
        })
        await client.invalidateQueries({
          queryKey: coverQuery(partId).queryKey,
        })
        return capture.featureId === featureId ? saved : null
      }),
  })
  return {
    hasLayer: relevant,
    image: image ?? (relevant ? query.data : undefined),
    loading: query.isFetching,
    error: query.error,
    retry: query.refetch,
  }
}
