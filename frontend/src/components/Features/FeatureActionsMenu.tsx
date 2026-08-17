import { EllipsisVertical, Pencil } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteFeature from "./DeleteFeature"

interface FeatureActionsMenuProps {
  featureId: string
  onEdit: () => void
}

export const FeatureActionsMenu = ({
  featureId,
  onEdit,
}: FeatureActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 shrink-0"
          onClick={(event) => event.stopPropagation()}
        >
          <EllipsisVertical />
          <span className="sr-only">Acciones</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        onClick={(event) => event.stopPropagation()}
      >
        <DropdownMenuItem
          onSelect={() => {
            setOpen(false)
            onEdit()
          }}
        >
          <Pencil />
          Editar
        </DropdownMenuItem>
        <DeleteFeature featureId={featureId} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
