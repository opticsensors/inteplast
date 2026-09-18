import { Folder, MoreHorizontal } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { SourceBrowser } from "./SourceFilePicker"

export function PartFolderPicker({
  path,
  onSelected,
}: {
  path: string | null | undefined
  onSelected: (path: string) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const linked = path != null
  const label = linked
    ? "Cambiar carpeta de la pieza"
    : "Vincular carpeta de la pieza"
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) setOpen(next)
      }}
    >
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            aria-label="Opciones de la pieza"
          >
            <MoreHorizontal className="size-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          onCloseAutoFocus={(event) => {
            if (open) event.preventDefault()
          }}
        >
          <DropdownMenuItem
            onSelect={() => setOpen(true)}
            title={path ?? undefined}
          >
            <Folder className="size-4" />
            {label}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {open && (
        <DialogContent
          className="sm:max-w-2xl"
          showCloseButton={!busy}
          onEscapeKeyDown={(event) => {
            if (busy) event.preventDefault()
          }}
          onPointerDownOutside={(event) => event.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>
              {linked
                ? "Cambiar carpeta de la pieza"
                : "Vincular carpeta de la pieza"}
            </DialogTitle>
            <DialogDescription>
              Selecciona la carpeta que contiene los ficheros de esta pieza.
            </DialogDescription>
          </DialogHeader>
          <SourceBrowser
            initialPath={path ?? ""}
            onFolderSelected={onSelected}
            setBusy={setBusy}
            close={() => setOpen(false)}
          />
        </DialogContent>
      )}
    </Dialog>
  )
}
