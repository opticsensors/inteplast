import { useQueryClient } from "@tanstack/react-query"
import { Link2, Loader2 } from "lucide-react"
import { useState } from "react"
import { type FilePublic, FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickNativePath } from "@/lib/nativePicker"
import { usePendingTask } from "./usePendingTask"

export function SourceFilePicker({
  document,
  onLinked,
  disabled = false,
  compact = false,
}: {
  document?: FilePublic
  onLinked: (file: FilePublic) => Promise<void>
  disabled?: boolean
  compact?: boolean
  initialPath?: string
}) {
  const client = useQueryClient()
  const [message, setMessage] = useState("")
  const label = document
    ? "Cambiar archivo vinculado"
    : "Vincular archivo existente"
  const linking = usePendingTask(async (_: undefined) => {
    try {
      const path = await pickNativePath("file")
      if (!path) return
      const file = await FilesService.referenceFile({ requestBody: { path } })
      await onLinked(file)
      await Promise.all(
        ["features", "file-status", "file-access"].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    } catch (error) {
      setMessage(fileErrorMessage(error))
      throw error
    }
  })
  return (
    <div className="shrink-0">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant={compact ? "ghost" : "outline"}
            size={compact ? "icon" : "sm"}
            className={compact ? "size-7" : undefined}
            aria-label={label}
            disabled={disabled || linking.pending}
            onClick={() => void linking.run(undefined)}
          >
            {linking.pending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Link2 className="size-3.5" />
            )}
            {!compact && label}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{label}</TooltipContent>
      </Tooltip>
      {linking.error && (
        <div
          role="alert"
          className="max-w-64 space-y-2 p-2 text-xs text-destructive"
        >
          <p>{message}</p>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void linking.retry()}
            >
              Reintentar
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={linking.dismissError}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
