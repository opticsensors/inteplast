import { useQuery } from "@tanstack/react-query"

import { FilesService, OpenAPI } from "@/client"

/** Fetch a short-lived authorization URL, without fetching the file bytes. */
export const fileAccessQueryOptions = (fileId: string) => ({
  queryKey: ["file-access", fileId],
  queryFn: () => FilesService.createFileAccessUrl({ fileId }),
  staleTime: 60_000,
})

export const absoluteFileUrl = (relative: string) =>
  `${OpenAPI.BASE ?? ""}${relative}`

export function useFileAccess(fileId: string | undefined) {
  const query = useQuery({
    ...fileAccessQueryOptions(fileId ?? ""),
    enabled: Boolean(fileId),
    // Renew while displayed, well before the backend's 15-minute expiry.
    refetchInterval: 5 * 60_000,
  })
  const url = query.data ? absoluteFileUrl(query.data.url) : undefined
  return {
    ...query,
    url,
    downloadUrl: url ? `${url}&download=true` : undefined,
  }
}
