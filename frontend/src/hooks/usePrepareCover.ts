import { useQuery } from "@tanstack/react-query"
import { type FilePublic, FilesService } from "@/client"

/** Start the current detail view's conversion while its saved image is visible. */
export function usePrepareCover(
  file?: FilePublic | null,
  versionKey?: string | null,
) {
  useQuery({
    queryKey: ["prepare-cover", file?.id, file?.version, versionKey],
    enabled: Boolean(file && /\.(stp|step)$/i.test(file.filename)),
    queryFn: () => FilesService.preparePreview({ fileId: file!.id }),
    staleTime: 60_000,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
