import { useState } from "react"
import { FileLink } from "@/components/Common/FileLink"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { useFileAccess } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import type { EvidenceSource } from "./types"

export const fmt = (value: number | null | undefined) =>
  value == null
    ? "—"
    : value.toLocaleString("es-ES", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      })
export const statusLabel = (status?: string) =>
  status === "inside"
    ? "Dentro"
    : status === "outside"
      ? "Fuera"
      : "Sin evaluar"
export const statusClass = (status?: string) =>
  status === "inside"
    ? "text-emerald-700 dark:text-emerald-400"
    : status === "outside"
      ? "text-destructive"
      : "text-muted-foreground"
export function Source({
  source,
  label,
}: {
  source: EvidenceSource | undefined
  label?: string
}) {
  return source ? (
    <FileLink
      fileId={source.file_id}
      downloadFile
      className="text-xs text-muted-foreground underline underline-offset-2"
      title={`${source.path} · ${source.locator}`}
    >
      {label || source.locator || source.path.split("/").slice(-1)[0]}
    </FileLink>
  ) : null
}
export function EvidenceImage({
  id,
  title,
  className,
}: {
  id: string
  title: string
  className?: string
}) {
  const { url, isError } = useFileAccess(id)
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`Ampliar ${title}`}
        className={cn(
          "block w-full overflow-hidden rounded-md border bg-white",
          className,
        )}
      >
        {url ? (
          <img
            src={url}
            alt={title}
            className="h-full max-h-80 w-full object-contain p-2"
            loading="lazy"
          />
        ) : (
          <span className="flex h-40 items-center justify-center text-sm text-muted-foreground">
            {isError ? "Imagen no disponible" : "Cargando imagen…"}
          </span>
        )}
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-5xl sm:max-w-5xl">
          <DialogTitle>{title}</DialogTitle>
          <img
            src={url}
            alt={title}
            className="max-h-[75vh] w-full bg-white object-contain"
          />
        </DialogContent>
      </Dialog>
    </>
  )
}
