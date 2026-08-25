import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { FeatureForm } from "@/components/Features/FeatureForm"

export const Route = createFileRoute("/_layout/features_/nuevo")({
  component: NewFeature,
  head: () => ({
    meta: [
      {
        title: "Nuevo feature - INTEPLAST",
      },
    ],
  }),
})

function NewFeature() {
  const navigate = useNavigate()
  const toList = () => navigate({ to: "/features" })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Nuevo feature</h1>
        <p className="text-muted-foreground">
          Guarda los datos basicos y despues podras anadirle warnings, lessons
          learned, piezas y ficheros.
        </p>
      </div>

      <FeatureForm
        featureId={null}
        // Recien creado se sigue en su ficha, ya en modo edicion: las notas y
        // los ficheros necesitan que el feature exista para colgarse de el.
        onCreated={(featureId) =>
          navigate({
            to: "/features/$featureId",
            params: { featureId },
            search: { editar: true },
          })
        }
        onSaved={toList}
        onCancel={toList}
      />
    </div>
  )
}
