import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  CatalogService,
  type FilePublic,
  FilesService,
  type PartCoverPublic,
} from "@/client"
import { scheduleCapture } from "./useFaceImage"

export function useGrayImage(part: PartCoverPublic & { id: string }) {
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
      return scheduleCapture(async () => {
        signal.throwIfAborted()
        const { capturePartCad } = await import(
          "@/components/Parts/capturePartCad"
        )
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
        client.setQueryData<PartCoverPublic>(
          ["features", "catalog", "cover", part.id],
          (previous) =>
            previous?.cad_cache_key &&
            previous.cad_cache_key !== part.cad_cache_key
              ? previous
              : {
                  ...previous,
                  cad,
                  cad_cache_key: part.cad_cache_key,
                  image: saved,
                  cover_needs_refresh: false,
                },
        )
        void client.invalidateQueries({
          queryKey: ["parts", "detail", part.id],
        })
        // This verified SHA can also settle older face selections for this CAD.
        void client.invalidateQueries({
          queryKey: ["features", "catalog", "cover", part.id],
        })
        return saved
      })
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
