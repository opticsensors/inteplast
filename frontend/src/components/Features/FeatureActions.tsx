import { Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"

interface FeatureActionsProps {
  onEdit: () => void
  variant?: "ghost" | "outline"
}

/** Acceso directo a edicion, tanto desde el catalogo como desde la ficha. */
export const FeatureActions = ({
  onEdit,
  variant = "ghost",
}: FeatureActionsProps) => (
  <Button variant={variant} size="sm" onClick={onEdit}>
    <Pencil />
    Editar
  </Button>
)
