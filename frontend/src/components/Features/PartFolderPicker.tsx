import { Folder, MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { pickNativePath } from "@/lib/nativePicker"
import { SaveStatus } from "./SaveStatus"
import { usePendingTask } from "./usePendingTask"

export function PartFolderPicker({
  path,
  onSelected,
}: {
  path: string | null | undefined
  onSelected: (path: string) => Promise<void>
}) {
  const selection = usePendingTask(async (_: undefined) => {
    const folder = await pickNativePath("folder")
    if (folder) await onSelected(folder)
  })
  return (
    <div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            aria-label="Opciones de la pieza"
            disabled={selection.pending}
          >
            <MoreHorizontal className="size-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => void selection.run(undefined)}>
            <Folder className="size-4" />
            {path != null
              ? "Cambiar carpeta de la pieza"
              : "Vincular carpeta de la pieza"}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <SaveStatus
        error={selection.error}
        saving={selection.pending}
        retry={selection.retry}
      />
    </div>
  )
}
