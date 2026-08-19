import { useCanGoBack, useNavigate, useRouter } from "@tanstack/react-router"
import { ArrowLeft, Package2 } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * Un feature que no existe: borrado, o un enlace mal copiado. Lo usan la ficha
 * y la pagina de edicion, que llegan al mismo sitio por caminos distintos.
 */
export function FeatureNotFound() {
  const router = useRouter()
  const navigate = useNavigate()
  const canGoBack = useCanGoBack()

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="rounded-full bg-muted p-4">
        <Package2 className="size-7 text-muted-foreground" />
      </div>
      <h1 className="text-lg font-semibold">Feature no encontrado</h1>
      <p className="text-muted-foreground">
        Puede que se haya borrado o que el enlace no sea correcto.
      </p>
      <Button
        variant="outline"
        onClick={() =>
          canGoBack ? router.history.back() : navigate({ to: "/features" })
        }
      >
        <ArrowLeft className="mr-2" />
        Volver
      </Button>
    </div>
  )
}
