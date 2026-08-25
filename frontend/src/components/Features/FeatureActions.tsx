import { Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import DeleteFeature from "./DeleteFeature"

interface FeatureActionsProps {
  featureId: string
  onEdit: () => void
}

/**
 * Los dos botones de la tarjeta de gestion. Antes esto era un `⋯` con un menu
 * desplegable: dos clics y una lista de dos entradas para lo unico que se
 * puede hacer con una tarjeta. Ahora son los mismos dos botones —y con el
 * mismo aspecto— que tenia la ficha.
 */
export const FeatureActions = ({ featureId, onEdit }: FeatureActionsProps) => (
  <div className="flex shrink-0 items-center gap-2">
    <Button variant="outline" size="sm" onClick={onEdit}>
      <Pencil className="mr-2" />
      Editar
    </Button>
    <DeleteFeature featureId={featureId} />
  </div>
)
