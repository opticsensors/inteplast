import { AxiosError } from "axios"
import { type ApiError, OpenAPI } from "./client"

function extractErrorMessage(err: ApiError): string {
  if (err instanceof AxiosError) {
    return err.message
  }

  const errDetail = (err.body as any)?.detail
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    return errDetail[0].msg
  }
  return errDetail || "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: ApiError,
) {
  const errorMessage = extractErrorMessage(err)
  this(errorMessage)
}

/**
 * URL publica de un fichero subido. Se compone a mano porque un `<img src>` o
 * un enlace de descarga no pueden pasar por el cliente generado (no llevan la
 * cabecera Authorization); el endpoint GET /files/{id} es abierto a proposito.
 */
export const fileUrl = (fileId: string): string =>
  `${OpenAPI.BASE}/api/v1/files/${fileId}`

export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
