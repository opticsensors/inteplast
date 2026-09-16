import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { FeaturesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteFeatureProps {
  featureId: string
  featureName: string
  /** Salir de la ficha que se acaba de eliminar. */
  onSuccess?: () => void
}

const DeleteFeature = ({
  featureId,
  featureName,
  onSuccess,
}: DeleteFeatureProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => FeaturesService.deleteFeature({ featureId }),
    onSuccess: () => {
      showSuccessToast("Feature eliminado")
      setIsOpen(false)
      onSuccess?.()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Button
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        onClick={() => setIsOpen(true)}
      >
        <Trash2 />
        Eliminar
      </Button>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Eliminar feature</DialogTitle>
          <DialogDescription>
            Se eliminará «{featureName}» con sus warnings, lessons learned y
            vínculos a piezas y archivos. Las piezas y los archivos se
            conservan. Esta acción no se puede deshacer.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancelar
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Eliminar
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default DeleteFeature
