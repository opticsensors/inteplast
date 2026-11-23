import { useQuery } from "@tanstack/react-query"

import { type FilePublic, FilesService } from "@/client"

/** The grid and full viewer share the same per-page orientation decision. */
export function useDrawingThumbnail(
  file: Pick<FilePublic, "id" | "version">,
  page = 1,
) {
  return useQuery({
    queryKey: ["drawing-thumbnail", file.id, file.version, page],
    queryFn: () => FilesService.prepareThumbnail({ fileId: file.id, page }),
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.state === "busy" && !query.state.error ? 1500 : false,
    staleTime: 10 * 60_000,
  })
}
