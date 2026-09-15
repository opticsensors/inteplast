import type { FilePublic } from "@/client"
import { fileErrorMessage, useDocumentStatus } from "@/hooks/useFileAccess"

export function DocumentStatus({
  file,
}: {
  file: FilePublic | null | undefined
}) {
  const status = useDocumentStatus(file)
  if (file?.source !== "local") return null
  const message = status.isError
    ? fileErrorMessage(status.error)
    : status.data?.state !== "available"
      ? status.data?.message
      : null
  if (!message) return null
  return (
    <output className="block px-2 py-1 text-xs text-amber-700 dark:text-amber-400">
      {message}
    </output>
  )
}
