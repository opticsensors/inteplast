import type { ComponentProps } from "react"

import { useFileAccess } from "@/hooks/useFileAccess"

export function FileLink({
  fileId,
  downloadFile,
  ...props
}: ComponentProps<"a"> & {
  fileId: string
  downloadFile?: boolean
}) {
  const { url, downloadUrl, isError, refetch } = useFileAccess(fileId)
  return (
    <a
      {...props}
      href={downloadFile ? downloadUrl : url}
      aria-disabled={!url}
      onClick={(event) => {
        if (!url || isError) {
          event.preventDefault()
          void refetch()
        } else props.onClick?.(event)
      }}
    />
  )
}
