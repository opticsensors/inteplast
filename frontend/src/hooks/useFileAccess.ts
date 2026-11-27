import { useQuery } from "@tanstack/react-query"

import { ApiError, type FilePublic, FilesService, OpenAPI } from "@/client"

export const fileErrorMessage = (error: unknown) => {
  if (
    error instanceof ApiError &&
    error.body &&
    typeof error.body === "object" &&
    "detail" in error.body &&
    typeof error.body.detail === "string"
  )
    return error.body.detail
  return error instanceof Error
    ? error.message
    : "No se puede acceder al archivo."
}

export function useDocumentStatus(file: FilePublic | null | undefined) {
  return useQuery({
    queryKey: ["file-status", file?.id, file?.version],
    queryFn: () => FilesService.fileStatus({ fileId: file!.id }),
    enabled: file?.source === "local",
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Fetch a short-lived authorization URL, without fetching the file bytes. */
export const fileAccessQueryOptions = (fileId: string) => ({
  queryKey: ["file-access", fileId],
  queryFn: () => FilesService.createFileAccessUrl({ fileId }),
  staleTime: 60_000,
})

export const absoluteFileUrl = (relative: string) =>
  `${OpenAPI.BASE ?? ""}${relative}`

/** The stable authenticated URL lets two views revalidate the same cached GLB. */
export function fetchPreparedPreview(
  fileId: string,
  signal: AbortSignal,
  signedUrl?: string,
) {
  const path = `/api/v1/files/${encodeURIComponent(fileId)}/preview`
  const token = localStorage.getItem("access_token")
  if (token && (!signedUrl || signedUrl.split("?")[0] === path)) {
    return fetch(absoluteFileUrl(path), {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    })
  }
  return signedUrl ? fetch(absoluteFileUrl(signedUrl), { signal }) : undefined
}

export function useFileAccess(fileId: string | undefined) {
  const query = useQuery({
    ...fileAccessQueryOptions(fileId ?? ""),
    enabled: Boolean(fileId),
    // Renew while displayed, well before the backend's 15-minute expiry.
    refetchInterval: 5 * 60_000,
  })
  const url =
    query.data && !query.isError ? absoluteFileUrl(query.data.url) : undefined
  return {
    ...query,
    url,
    downloadUrl: url ? `${url}&download=true` : undefined,
  }
}
