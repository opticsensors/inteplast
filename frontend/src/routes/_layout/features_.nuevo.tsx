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
      </div>

      <FeatureForm
        featureId={null}
        onCreated={(featureId) =>
          navigate({
            to: "/features/$featureId",
            params: { featureId },
            replace: true,
          })
        }
        onSaved={toList}
        onCancel={toList}
      />
    </div>
  )
}
